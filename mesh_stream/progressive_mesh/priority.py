from abc import ABC, abstractmethod
import heapq
import random
from collections.abc import Sequence
import numpy as np

from mesh_stream import obja
from .model import MeshReader

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
        return ()


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

    def __init__(self):
        super().__init__()
        self.min_heap = heapq

    def next(self) -> tuple: 
        ...

    # 1. Calcul matrices Q initiales pour chaque sommet. Q = somme des Kp  (voir section 5)
    def compute_Q(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face]) -> list[np.ndarray]:
        ...

    # 2. Sélection des paires valides :  arêtes directes ou distance < t (section 3.2)
    def select_valid_pairs(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face], distance_threshold: float) -> set[tuple[int, int]]:
        ...
    
    # 3. Calculer leur coût (erreur) optimale (?)
    def compute_contraction(self, pair: tuple[int, int], quadrics: Sequence[np.ndarray], vertices: Sequence[np.ndarray]) -> tuple[np.ndarray, float]:
        """Return target position and its summed-quadric error."""
        ...

    # 4. On place toutes les paires dans un tas classé par coût (= l'erreur), avec la paire au plus bas coût en haut
    def update_heap(self, pairs: list[tuple[int, int]]):
        ...

    # 5. Fusionne la paire au plus petit coût
    def contract_pair(self, pair: tuple[int, int], target: np.ndarray) -> tuple[int, int]:
        ...