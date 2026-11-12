from abc import ABC, abstractmethod
import random

from mesh_stream import obja
from .mesh_reader import MeshReader

from abc import ABC, abstractmethod
import random
from typing import TYPE_CHECKING

from mesh_stream import obja

from collections import defaultdict

import numpy as np





class Priority(ABC):
    def __init__(self):
        self.mesh_reader: MeshReader | None = None

    def set_reader(self, mesh_reader: MeshReader):
        self.mesh_reader = mesh_reader

    def _check_reader(self):
        if self.mesh_reader is None:
            raise RuntimeError(f"{self.__class__.__name__}: set_reader() must be called before next()")

    @abstractmethod
    def next(self, invalid_edges) -> tuple | None: 
        return ()


class RandomPriority(Priority):

    def next(self, invalid_edges):
        self._check_reader()
        faces = self.mesh_reader.faces
        f = random.choice(faces)
        edge = tuple(sorted(random.sample(list(f),2)))
        while edge in invalid_edges:
            edge = tuple(sorted(random.sample(list(f),2)))
        return edge


class ChoosePriority(Priority):

    def __init__(self, edges):
        super().__init__()
        self.edges = edges
        self.iteration = 0

    def next(self, invalid_edges):
        self.iteration += 1
        if self.edges[self.iteration - 1] in invalid_edges:
            raise RuntimeError(f"Chosen edge collapse {self.edges[self.iteration - 1]} is invalid.")
        else:
            return tuple(self.edges[self.iteration - 1])




class WeightPriority(Priority):
    """
    Plus courte arête d'abord. Renvoie (s, t) : s gardé, t supprimé,
    ou None quand plus aucune arête n'est supprimable.

    - poids d'une arête = sa longueur
    - base edges = arêtes à une seule face (boundary), extrémités protégées
    - seuil de l'étape : eps = ratio * moyenne des longueurs de toutes les
      arêtes restantes. Une arête plus longue que eps n'est pas collapsée
      à cette étape.
    """

    def __init__(self, ratio: float = 1.0):
        super().__init__()
        self.ratio = ratio
        self.rejected = set()  # arêtes refusées (topologie / flipping)

    # return : le poids d'une edge a b
    @staticmethod
    def edge_weight(vertices, a, b):
        return float(np.linalg.norm(np.asarray(vertices[a], dtype=float)
                                    - np.asarray(vertices[b], dtype=float)))



    @staticmethod
    def _normal(vertices, f):
        p = [np.asarray(vertices[i], dtype=float) for i in f]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        norm = np.linalg.norm(n)
        return n / norm if norm > 1e-12 else None

    # return : la normale d'une face telle qu'elle serait après le collapse ou None si trop petit
    # f : tous les sommets de la face
    # moved : les sommets qui vont bouger
    # new_pos : leur nouvelles positions
    @staticmethod
    def _normal_moved(vertices, f, moved, new_pos):
        p = [np.asarray(new_pos if i in moved else vertices[i], dtype=float) for i in f]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        norm = np.linalg.norm(n)
        return n / norm if norm > 1e-12 else None

    # pour décider lequel des deux sommet d'un edge on supprime
    # on calcule l'aire de toutes les faces adjacente
    # return : le plus angle trouvé en radian
    # utile pour une arrête ou aucun des deux sommets n'est protegé
    # faces_of_v : face dans laquelel est v
    def _deviation(self, vertices, faces_of_v):
        ns = [self._normal(vertices, f) for f in faces_of_v]
        ns = [n for n in ns if n is not None]
        if len(ns) < 2:
            return 0.0
        return max(np.arccos(np.clip(np.dot(a, b), -1, 1))
                   for i, a in enumerate(ns) for b in ns[i + 1:])



    # return : True si on peut collapse l'edge (s,t)
    def _collapse_ok(self, vertices, adj, s, t):
        # on ne peut pas collapse un sommet appartement à une arrête d'un base edge car sinon on modifie les bords
        

        fs, ft = adj[s], adj[t]

        # Faces contenant s et t : elles disparaissent (1 pour un bord, 2 pour une arête interne)
        shared = [f for f in ft if s in f]
        if not 1 <= len(shared) <= 2:
            return False

        # Condition du lien : les seuls voisins communs sont les sommets opposés des faces partagées
        nb_s = {v for f in fs for v in f} - {s}
        nb_t = {v for f in ft for v in f} - {t}
        opposite = {v for f in shared for v in f if v not in (s, t)}
        if (nb_s & nb_t) != opposite:
            return False

        # Nouvelle position du sommet fusionné
        m = (np.asarray(vertices[s], dtype=float) + np.asarray(vertices[t], dtype=float)) / 2

        # Flipping error : toutes les faces survivantes de s ET de t, avec s et t placés en m
        for f in fs + ft:
            if s in f and t in f:
                continue  # face qui disparaît
            n0 = self._normal(vertices, f)                       # normale avant
            n1 = self._normal_moved(vertices, f, {s, t}, m)      # normale après
            if n0 is None or n1 is None or np.dot(n0, n1) <= 0:
                return False

        return True


    # return la prochaine arrête à split
    def next(self, invalid_edges):
        
        self._check_reader()
        faces = self.mesh_reader.faces
        vertices = self.mesh_reader.vertices

        # on compte les arrêtes
        adj = defaultdict(list)
        edge_count = defaultdict(int)
        for f in faces:
            for v in f:
                adj[v].append(f)
            for i in range(3):
                edge_count[tuple(sorted((f[i], f[(i + 1) % 3])))] += 1
        if not edge_count:
            return None

        # cacul des poids
        weights = {e: self.edge_weight(vertices, *e) for e in edge_count}
        eps = self.ratio * (sum(weights.values()) / len(weights))

        # les sommets protégés sont les ceux des base edge
        protected = {v for e, c in edge_count.items() if c == 1 for v in e}

        # on trie selon le poids
        candidates = sorted(
            (e for e in edge_count
            if e not in invalid_edges       
            and edge_count[e] == 2          
            and weights[e] <= eps),         
            key=weights.get,
        )

        # on retourne le premier valide
        for e in candidates:
            a, b = e
            if a in protected or b in protected:
                continue
            if self._collapse_ok(vertices, adj, a, b):
                return e                    

        return None