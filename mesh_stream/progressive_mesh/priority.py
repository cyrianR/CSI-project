from abc import ABC, abstractmethod
import random

from mesh_stream import obja
from .mesh_reader import MeshReader

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




# TODO : others priorities