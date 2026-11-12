from __future__ import annotations
from abc import ABC, abstractmethod
import copy
import heapq
import itertools
import random
from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np
from mesh_stream import obja
from .mesh_reader import MeshReader

from abc import ABC, abstractmethod
import random
from typing import TYPE_CHECKING

from mesh_stream import obja

from collections import defaultdict

import numpy as np




from scipy.spatial import cKDTree

import igl
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra


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

        edges = set()
        for f in faces:
            for u, v in ((f.a, f.b), (f.c, f.a), (f.b, f.c)):
                edges.add(tuple(sorted((u, v))))

        valid_edges = edges - set(invalid_edges)

        if not valid_edges:
            return None

        return random.choice(tuple(valid_edges))

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


###################"######## Priorité basé sur QEM (Quadric Error Metric) du 3eme papier ##############################
# Section 4.1 : Algorithme
# On associe une matrice symétrique 4*4 Q à chaque sommet et l'erreur au sommet v : v^T Q v
# Pour une contraction : Q = Q1 + Q2 et l'erreur v^T (Q1+Q2) v
class QuadricErrorPriority(Priority):

    # Scalaire pour les plans de Kp
    BOUNDARY_WEIGHT = 1000.0

    def __init__(self):
        super().__init__()
        # tas min de la forme (cout, tie_breaker, paire, cible) avec tie_breaker
        # une méthode d'itertools pour éviter de recomparer des ndarrays au coût égal
        # On utilisera la classe heapq de Python pour y faire des opérations
        self.min_heap:  list[tuple[float, int, tuple[int, int], np.ndarray]] = []
        self._tie_breaker = itertools.count()

        # On laisse à 0 pour ne contracter que les edges existants
        # Le papier de base permet de faire des contractions de paires non liées (avec dist positives du coup)
        # Notre model.py le permet pas pour l'instant.
        self.distance_threshold = 0.0

        # listes des quadrics Q avec donc quadrics[i] la matrice 4x4 d'erreurs pour le vertex i.
        self.quadrics: list[np.ndarray] = []

        # On init les ensembles de candidats
        # Ils seront maj à chaque contraction
        self.valid_pairs: set[tuple[int, int]] = set()
        self._active_pairs: set[tuple[int, int]] = set()


    def set_reader(self, mesh_reader: MeshReader):
        """Init les quadrics, candidats et leur cout dans le tas min."""

        super().set_reader(mesh_reader)
        assert self.mesh_reader is not None

        # On récupère la vue du mesh courant.
        vertices = self.mesh_reader.vertices
        faces = self.mesh_reader.faces

        # Etape 1
        self.quadrics = self.compute_Q(vertices, faces)

        # Etape 2
        self.valid_pairs = self.select_valid_pairs(vertices, faces, self.distance_threshold)
        self._active_pairs = set(self.valid_pairs)

        # Etape 3-4
        self.update_heap(sorted(self._active_pairs))

    def next(self, invalid_edges: list[tuple[int, int]]) -> tuple[int, int] | None:
        self._check_reader()
        assert self.mesh_reader is not None

        vertices = self.mesh_reader.vertices
        faces = self.mesh_reader.faces
        invalid = set(invalid_edges)

        self.quadrics = self.compute_Q(vertices, faces)

        pairs = self.select_valid_pairs(vertices, faces, self.distance_threshold)

        pairs = sorted(pair for pair in pairs if pair not in invalid)
        if not pairs:
            return None

        self.update_heap(pairs)

        while self.min_heap:
            _, _, pair, _ = heapq.heappop(self.min_heap)
            if pair not in invalid:
                return pair

        return None

    # 1. Calcul matrices Q initiales pour chaque sommet. Q = somme des Kp  (voir section 5)
    def compute_Q(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face]) -> list[np.ndarray]:

        # initialisation des matrices Q pour chaque vertex
        quadrics = [np.zeros((4, 4), dtype=float) for v in vertices]

        # dico des faces/plans incidents à chaque edge
        edge_faces: dict[tuple[int, int], list[tuple[np.ndarray, np.ndarray]]] = {}

        for face in faces:
            # p =[a b c d ].T représente le plan défini par
            # ax + by + cz + d = 0 avec  a^2 + b^2 + c^2 = 1
            a, b, c = (int(i) for i in face)
            # chaque triangle contribue un plan des quadrics
            p0 = np.asarray(vertices[a], dtype=float)
            p1 = np.asarray(vertices[b], dtype=float)
            p2 = np.asarray(vertices[c], dtype=float)

            # on calcule la normale du triangle par prod vect
            normal = np.cross(p1 - p0, p2 - p0)
            normal_length = np.linalg.norm(normal)

            # on satinize les zero-area faces même si réalistiquement on en
            # croisera probablement pas
            if normal_length <= 1e-15:
                continue

            # on normalist
            normal /= normal_length
            d = -float(normal @ p0)
            # tjrs p =[a b c d ].T
            plane = np.array([normal[0], normal[1], normal[2], d],dtype=float)

            # pour v = [x,y,z,1] la section 5 donne comme somme des distances
            # au carrée à p : (plane.T @ v)^2.
            # ie v.T @ (plane * plane.T) @ v.
            # donc pour avoir la sum(plane * plane.T) aka Kp sous forme quadratique on peut faire ca:
            plane_quadric = np.outer(plane, plane)
            # Ca donne la grande matrice de la section 5 là appelée fundamental error quadric 

            # on attribue l'erreur quadrique du plan p à chacun de ses vertices
            for vertex_id in (a, b, c):
                quadrics[vertex_id] += plane_quadric

            # on map chaque edge à toutes les faces où elles sont
            for u, v in ((a, b), (b, c), (c, a)):
                # Une même clé pour l'edge (a, b) et (b, a) en prenant le plus petit en 1er.
                edge = (min(u, v), max(u, v))
                # retourne la valeur de edge si elle existe
                # sinon on insert (edge, [])
                # et on append à edge_faces[edge] (normal.copy(, p0.copy()))
                # copy pour pas qu'on save les réfs aux originales
                edge_faces.setdefault(edge, []).append((normal.copy(), p0.copy()))

        # Une face incidente pour un edge c'est un open boundary edge.
        # On ajoute un plan perpendiculaire à la face incidente pour.
        # pénaliser les mouvements hors de la boundary curve.
        for (u, v), incident_faces in edge_faces.items():
            if len(incident_faces) != 1:
                # 2 faces => edge intérieur.
                # faces > 2 => non-manifold
                continue

            # normal à la face perpendiculaire au triangle/plan incident
            face_normal, point_on_face = incident_faces[0]
            # v - u direction le long du boundary edge
            edge_direction = (
                np.asarray(vertices[v], dtype=float)
                - np.asarray(vertices[u], dtype=float)
            )
            edge_length = np.linalg.norm(edge_direction)
            if edge_length <= 1e-15:
                continue

            # on normalise
            edge_direction /= edge_length

            # normale de la boundary plane. 
            # Dans la face et perpendiculaire au edge.
            boundary_normal = np.cross(edge_direction, face_normal)
            boundary_length = np.linalg.norm(boundary_normal)
            if boundary_length <= 1e-15:
                continue

            # on normalise
            boundary_normal /= boundary_length
            d = -float(boundary_normal @ point_on_face)
            # ce plan contient la boundary edge et sert de "mur" le long de la bordure du mesh
            boundary_plane = np.array([*boundary_normal, d],dtype=float)

            # On ajoute la pondération pour que ca soit plus couter de casser cette boundary
            boundary_quadric = (self.BOUNDARY_WEIGHT * np.outer(boundary_plane, boundary_plane)
            )
            # on attribue l'erreur quadrique du boundary plane aux deux bouts
            quadrics[u] += boundary_quadric
            quadrics[v] += boundary_quadric

        return quadrics

    # 2. Sélection des paires valides :  arêtes directes ou distance < t (section 3.2)
    def select_valid_pairs(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face], distance_threshold: float) -> set[tuple[int, int]]:
        if distance_threshold < 0:
            raise ValueError("distance_threshold must not be negative")

        pairs: set[tuple[int, int]] = set()

        # tous les edges du mesh sont des candidats valides
        for face in faces:
            # 3 vertex de la face
            a, b, c = (int(i) for i in face)
            for u, v in ((a, b), (b, c), (c, a)):
                if u != v:
                    # # Une même entrée pour l'edge (a, b) et (b, a) en prenant le plus petit en 1er.
                    pairs.add((min(u, v), max(u, v)))

        # Si on permet les contractions non-edges (c'est O(n2) par contre comme ca explore double tous les vertex...)
        if distance_threshold > 0:
            for u in range(len(vertices)):
                pu = np.asarray(vertices[u], dtype=float)
                for v in range(u + 1, len(vertices)):
                    pv = np.asarray(vertices[v], dtype=float)
                    if np.linalg.norm(pu - pv) < distance_threshold:
                        pairs.add((u, v))

        return pairs


    # 3. Calculer leur coût (erreur) optimale (?)
    def compute_contraction(self, pair: tuple[int, int], quadrics: Sequence[np.ndarray], vertices: Sequence[np.ndarray]) -> tuple[np.ndarray, float]:
        """Return target position and its summed-quadric error."""

        s, t = pair

        # Q = Q1 + Q2
        Q = quadrics[s] + quadrics[t]

        # Notre contraction est solution de Ax = -b donc on partitionne Q pour
        # avoir A le bloc 3x3 et le vecteur b.
        A = Q[:3, :3]
        b = Q[:3, 3]

        p0 = np.asarray(vertices[s], dtype=float)
        p1 = np.asarray(vertices[t], dtype=float)

        def evaluate(point: np.ndarray) -> float:
            # on convertit en coord homogènes v =[x, y, z, 1]
            v = np.append(np.asarray(point, dtype=float), 1.0)
            return float(v @ Q @ v)

        # optimum sans contrainte si cond(A) (norme de A * norme de A^-1)
        # est suffisamment bien pour que linalg.solve ne fasse pas de /0.
        try:
            if np.linalg.cond(A) < 1e12:
                # résout Ax = -b
                optimum = np.linalg.solve(A, -b)
                # si x fini
                if np.all(np.isfinite(optimum)):
                    # on renvoie donc x et sa summed QE
                    return optimum, evaluate(optimum)
        except np.linalg.LinAlgError:
            # Si matrice singulière
            pass


        # si la résolution par opti sans contrainte rate,
        # on minimise sur le segment [p0, p1]. 
        # u  le position parameter est clamped sur [0,1] pour que le candidat reste sur le segment.
        direction = p1 - p0
        denominator = float(direction @ A @ direction)

        # Le dernier fallback du papier compare les endpoints et le midpoint.
        candidates = [p0, p1, (p0 + p1) / 2.0]

        # on évite la divison par 0
        if denominator > 1e-15:
            # un pt sur le segment est p = p0 + u * (p1 - p0)
            # u = 0 => p = p0
            # u = 1 => p = p1
            u = -float(direction @ (A @ p0 + b)) / denominator
            # clamp sur [0, 1]
            u = min(1.0, max(0.0, u))
            # on ajoute le meilleur point trouvé sur le segment
            candidates.append(p0 + u * direction)

        # On choisit le candidat qui minimise son summed QE entre p0, p1, le milieu et le nv candidat.
        target = min(candidates, key=evaluate)
        return np.asarray(target, dtype=float), evaluate(target)


    # 4. On place toutes les paires dans un tas classé par coût (= l'erreur), avec la paire au plus bas coût en haut
    def update_heap(self, pairs: list[tuple[int, int]]):
        ''' Update costs and rebuild min-heap for pairs in arg'''

        self.min_heap = []
        assert self.mesh_reader is not None

        vertices = self.mesh_reader.vertices
        # faces = self.mesh_reader.faces

        for pair in pairs:
            # On ignore les mauvaises paires
            s, t = pair
            if s == t:
                continue
            # et indices out of range
            if not (0 <= s < len(vertices) and 
                    0 <= t < len(vertices) 
                    and t < len(self.quadrics)):
                continue

            # un item du tas-min garde la paire-cible et son cout.
            target, cost = self.compute_contraction(pair, self.quadrics, vertices)
            # if not self._preserves_local_orientation(pair, target, vertices,
                                                    #  faces):
                # continue
            # on remet le tas-min en place
            heapq.heappush(self.min_heap, (cost, next(self._tie_breaker), pair, target))


###################"######## Priorité basé  Mesh Saliency 4eme papier ###########################################
class SaliencyPriority(Priority):
    """
    Stratégie de simplification de maillage basée sur la saillance géométrique
    des sommets (Local Curvature Entropy: LCE).
    Le but est de mesurer l'importance visuelle
    On a un score de saillance élevée lq une zone est variée et complexes (il y a bcp d'info)
    score de saillancé élevée ie entropie haute => forte priorité

    Section 3 : l'Algo
       1. Calcul de la courbure locale pour chaque sommet + son voisinage de rayon r
       2. les "bins" 
       3. Pondération par les aires avec les cellules de Voronoï (section 3.2) 
       4. Calcul de "l'entropie de la courbure locale" (LCE) (section 3.1) : + le score est élevé, + la zone est impt (forte saillance)
       5. Approche multi-echelle : On fait varier le rayon (rmax = 0.08 √AM)
    """
    def __init__(self):
        super().__init__()
        

    def next(self, invalid_edges) -> tuple | None:
        # 1. Calculer la saillance (LCE) pour chaque sommet (Rayon max rmax = 0.08 * sqrt(Aire), 
        #    multi-échelle, discrétisation en bins, pondération Voronoï, entropie de Shannon).
        # 2. Utiliser ces scores de saillance pour une file de priorité (heap).
        # 3. Retourner la prochaine arête paire à simplifier sous forme de tuple
        self._check_reader()
        assert self.mesh_reader is not None

        vertices = self.mesh_reader.vertices
        faces = self.mesh_reader.faces

        if not faces:
            return None

        total_area = self.surface_totale(vertices, faces)
        saliencies = self.saliency(vertices, faces, total_area)

        self.initialize_heap(vertices, faces, saliencies)

        # Exclure les arêtes invalides
        invalid_edges = {tuple(sorted(edge)) for edge in invalid_edges}

        while self.min_heap:
            _, (u, v) = heapq.heappop(self.min_heap)
            if (u, v) not in invalid_edges:
                return u, v
            
        return None

   
    def vertex_areas(self, vertices: Sequence[np.ndarray],
                     faces: Sequence[obja.Face]) -> np.ndarray:
        areas = np.zeros(len(vertices), dtype=np.float64)
        for f in faces:
            p0, p1, p2 = vertices[f.a], vertices[f.b], vertices[f.c]
            triangle_area = np.linalg.norm(
                np.cross(p1 - p0, p2 - p0)
            ) / 2.0
            # Chaque sommet reçoit un tiers de l'aire du triangle
            for vertex in (f.a, f.b, f.c):
                areas[vertex] += triangle_area / 3.0
        return areas
    
    
    # Calcul de la surface totale AM du maillage (Section 4)
    def surface_totale(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face]) -> float:
        aire_tot = 0
        for f in faces :
            p0, p1, p2 = vertices[f.a], vertices[f.b], vertices[f.c]
            prod = np.cross(p1 - p0, p2 - p0)
            aire_tot +=  np.linalg.norm(prod)/2
        return aire_tot

            
    #Calcul de la courbure locale pour chaque sommet (Section 3.1)
    def curvature(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face]) -> np.ndarray:
        V = np.array(vertices, dtype=np.float64)
        F = np.array([(f.a, f.b, f.c) for f in faces],dtype=np.int32)
        _, _, k1, k2, _ = igl.principal_curvature(V, F)
        courb= (k1+k2)/2
        return np.abs(courb) 


    # Graph pour la lce
    def graphe(self, V: np.ndarray, F: np.ndarray):
        n_vertices = len(V)
        edges = set()

        for a, b, c in F:
            edges.add(tuple(sorted((a, b))))
            edges.add(tuple(sorted((b, c))))
            edges.add(tuple(sorted((c, a))))
        lign, cols, data = [], [], []

        for u, v in edges:
            distance = np.linalg.norm(V[u] - V[v])
            lign.extend([u, v])
            cols.extend([v, u])
            data.extend([distance, distance])

        graph = csr_matrix( (data, (lign, cols)), shape=(n_vertices, n_vertices) )
        return graph
    
    
    # Entropie de la courbure locale (LCE) dans un voisinage de rayon r
    def lce( self,vertex_idx: int,radius: float,graph: csr_matrix,curvatures: np.ndarray,areas: np.ndarray) -> float:
        """
        Discrétisation en bins (256 bins) (Section 3.1 & 4)
        Pondération par les cellules de Voronoï / aires (Section 3.2)
        Calcul de l'entropie de Shannon H(vi) = -sum(p * log2(p)) (Section 3.1)
        """
        distances = dijkstra(csgraph=graph, directed=False, indices=vertex_idx)

        # Récup les voisins dans le rayon 
        vois = np.where(distances <= radius)[0]
        if len(vois) <= 1:
            return 0.0

        # les courbures et aires du voisinage
        courb = curvatures[vois]
        aires = areas[vois]
        if np.sum(aires) == 0:
            return 0.0

        #  256 bins (Section 3.1 et 4)
        #  Pondération par les cellules de Voronoï / aires (Section 3.2)
        poids, _ = np.histogram( courb, bins=256, weights=aires)
        total = np.sum(poids)
        if total == 0:
            return 0.0
        probabilities = poids / total

        # entropie de Shannon (Section 3.1)
        probabilities = probabilities[probabilities > 0]
        entropy = -np.sum(probabilities * np.log2(probabilities))

        return float(entropy)
        

    # Approche multi-échelle : rayon max rmax = 0.08 * sqrt(AM) et combinaison sur 5 niveaux (Section 3.3 & 4)
    def saliency(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face], total_area: float) -> np.ndarray:
        n_vertices = len(vertices)
        curvatures = self.curvature(vertices, faces)  
        areas = self.vertex_areas(vertices, faces)  # aires associées aux sommets
        # Construction du graphe
        V = np.array(vertices, dtype=np.float64)
        F = np.array(faces, dtype=np.int32)
        graph = self.graphe(V, F)
        rmax = 0.08 * np.sqrt(total_area) # le ray maxi
        scores = np.zeros(n_vertices)
        for i in range(n_vertices):
            for k in range(1, 6):
                radius = k * rmax / 5
                scores[i] += self.lce(i, radius, graph, curvatures, areas)
        return scores/5


    # Remplissage du tas avc la saillance 
    def initialize_heap(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face], saliencies: np.ndarray):
        self.min_heap = []
        edges = set()
        
        # Les arêtes uniques
        for f in faces:
            edges.add(tuple(sorted((f.a, f.b))))
            edges.add(tuple(sorted((f.b, f.c))))
            edges.add(tuple(sorted((f.c, f.a))))
            
        # les arêtes dans le tas
        for u, v in edges:
            prio = (saliencies[u] + saliencies[v]) / 2.0
            heapq.heappush(self.min_heap, (prio, (u, v)))
            
   

class EnergyPriority(Priority):
    """ A priority that selects the next edge to collapse based on an energy function.
    The energy function takes into account the distance from the original mesh,
    the representation of the mesh, and the spring energy of the edges. The edge with the minimum energy is selected for collapse."""
    
    def __init__(self, K: float = 1.0):
        """initialise energy priority

        Args:
            K (float, optional): spring constant. Defaults to 1.0.
            crep (float, optional): representation constant. Defaults to 1.0.
            nb_iter (int, optional): number of iterations for optimization. Defaults to 100.
        """
        super().__init__()
        self.K = K # spring constant
        
    def set_reader(self, mesh_reader: MeshReader):
            super().set_reader(mesh_reader)
            self.X = np.array(self.mesh_reader.vertices, copy=True) # original vertices to compare with
            
    def energy(self,V: np.ndarray,faces: list) -> float:
        """ energy function that calculate the total energy

        Args:
            V (np.ndarray): all the vertices of the mesh
            faces (list): all the faces of the mesh

        Returns:
            float: the total energy of the mesh
        """
        # data of the mesh
        # compute edges of the mesh all with min value first so no doubles
        arretes = { (min(f.a, f.b), max(f.a, f.b)) for f in faces} | { (min(f.b, f.c), max(f.b, f.c)) for f in faces} | { (min(f.c, f.a), max(f.c, f.a)) for f in faces}
        # d[i] = distance from X[i] the original mesh to its nearest vertex
        d = cKDTree(V).query(self.X)[0]
        # distance energy
        edist = np.sum(d ** 2)
        # spring energy
        espring = self.K * sum(np.linalg.norm(V[a] - V[b]) ** 2 for a, b in arretes)
        # total energy
        energy = edist + espring
        
        return energy

    @staticmethod
    def _simulate_edge_collapse(vertices, faces, edge):
        """ simulate the collapse of an edge and return the new vertices and faces, allows to calculate the energy of the new mesh without modifying the original mesh
        Args:
            vertices (list): list of vertices
            faces (list): list of faces
            edge (tuple): edge to collapse
        Returns:
            tuple: new vertices and faces after the collapse
        """
        vertices = copy.deepcopy(vertices)
        faces = copy.deepcopy(faces)
        s, t = edge

        vertices[s] = (vertices[s] + vertices[t]) / 2
        faces = [f for f in faces if not (s in f and t in f)]

        for f in faces:
            for i in range(3):
                if f[i] == t:
                    f[i] = s

        vertices.pop(t)
        for f in faces:
            for i in range(3):
                if f[i] > t:
                    f[i] -= 1

        return vertices, faces
    
    def next(self, invalid_edges):
        """ select the next edge to collapse based on the energy function
        Returns:
            tuple: the edge to collapse
        """
        self._check_reader()
        faces = self.mesh_reader.faces
        V = self.mesh_reader.vertices
        
        # compute the energy of candidate edges and select the minimum
        candidate_edges = { (min(f.a, f.b), max(f.a, f.b)) for f in faces} | { (min(f.b, f.c), max(f.b, f.c)) for f in faces} | { (min(f.c, f.a), max(f.c, f.a)) for f in faces}
        # remove invalid edges from candidate edges
        candidate_edges = list(candidate_edges - set(invalid_edges))
        
        if not candidate_edges:
            return None

        return min(candidate_edges, key=lambda e: self.energy(*self._simulate_edge_collapse(V, faces, e)))



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