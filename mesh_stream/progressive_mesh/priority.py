from abc import ABC, abstractmethod
import random

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

    def next(self):
        self._check_reader()
        faces = self.mesh_reader.faces
        f = random.choice(faces)
        return tuple(random.sample(f,2))




# TODO : others priorities