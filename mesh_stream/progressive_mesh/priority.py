from abc import ABC, abstractmethod
import heapq
import itertools
import random
from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np

from mesh_stream import obja
from mesh_stream.progressive_mesh.model2 import MeshReader

class Priority(ABC):
    def __init__(self):
        self.mesh_reader: MeshReader | None = None

    def set_reader(self, mesh_reader: MeshReader):
        self.mesh_reader = mesh_reader

    def _check_reader(self):
        if self.mesh_reader is None:
            raise RuntimeError(f"{self.__class__.__name__}: set_reader() must be called before next()")

    @abstractmethod
    def next(self) -> tuple: 
        raise NotImplementedError


class RandomPriority(Priority):

    def next(self) -> tuple[int, int]:
        self._check_reader()
        assert self.mesh_reader is not None
        faces = self.mesh_reader.faces
        if not faces:
            raise StopIteration("No faces remain.")
        f = random.choice(faces)
        return tuple(random.sample(list(f), 2))


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

    def next(self) -> tuple: 
        self._check_reader()

        # tq le tas n'est pas vide on pop le plus petit item
        while self.min_heap:
            _, _, pair, target = heapq.heappop(self.min_heap)
            if pair in self._active_pairs:
                return pair, target.copy()

        # An empty heap means no valid contraction remains.
        raise StopIteration("No valid contraction pairs remain.")

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
            boundary_quadric = (
                self.BOUNDARY_WEIGHT
                * np.outer(boundary_plane, boundary_plane)
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
            # on remet le tas-min en place
            heapq.heappush(self.min_heap, (cost, next(self._tie_breaker), pair, target))

    # 5. Update QEM après fusion de la paire au plus petit coût
    def contract_pair(self, pair: tuple[int, int], target: np.ndarray) -> tuple[int, int]:
        s, t = pair

        # canonical pairs: s gardé doit être inférieur à t retiré.
        if s > t:
            raise ValueError("QEM pairs must be canonical (survivor < removed).")
        if not (0 <= s < t < len(self.quadrics)):
            raise IndexError(f"Invalid contraction pair: {pair}")

        # Summed QE sur le nv s est la somme des quadrics des deux pts (edgepts)
        self.quadrics[s] = self.quadrics[s] + self.quadrics[t]
        self.quadrics.pop(t)

        # maj les occurences de t pour pointer vers s
        def remap(vertex_id: int) -> int:
            mapped = s if vertex_id == t else vertex_id

            # les index au-dessus de t ont été shift down de 1
            return mapped - 1 if mapped > t else mapped

        # rediriger anciennes paires, retirer les paires malformées et doublons
        new_pairs: set[tuple[int, int]] = set()
        for u, v in self._active_pairs:
            u2 = remap(u)
            v2 = remap(v)

            if u2 == v2:
                # on skip les paires devenues (s, s)
                continue
        
            new_pairs.add((min(u2, v2), max(u2, v2)))

        self._active_pairs = new_pairs
        self.valid_pairs = new_pairs

        # on recalcule tous les couts pour maj le tas-min
        self.update_heap(sorted(new_pairs))

        return s, t
