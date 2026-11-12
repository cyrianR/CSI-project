from abc import ABC, abstractmethod
import copy
import random

from mesh_stream import obja
from .mesh_reader import MeshReader
import numpy as np
from scipy.spatial import cKDTree

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




# TODO : others priorities

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
