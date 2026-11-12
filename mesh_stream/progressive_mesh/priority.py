from abc import ABC, abstractmethod
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
    
    def __init__(self, K: float = 1.0, crep: float = 1.0, nb_iter: int = 100):
        """initialise energy priority

        Args:
            K (float, optional): spring constant. Defaults to 1.0.
            crep (float, optional): representation constant. Defaults to 1.0.
            nb_iter (int, optional): number of iterations for optimization. Defaults to 100.
        """
        super().__init__()
        self.K = K # spring constant
        self.crep = crep # representation constant
        self.nb_iter = nb_iter # number of iterations for optimization
        
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
        arretes = { (min(f.a, f.b), max(f.a, f.b)) for f in faces} | { (min(f.b, f.c), max(f.b, f.c)) for f in faces} | { (min(f.c, f.a), max(f.c, f.a)) for f in faces} # compute edges of the mesh
        d = cKDTree(V).query(self.X)[0] # d[i] = distance from X[i] the original mesh to its nearest vertex
        # distance energy
        edist = np.sum(d ** 2)
        # representation energy
        erep = self.crep * len(V)
        # spring energy
        espring = self.K * sum(np.linalg.norm(V[a] - V[b]) ** 2 for a, b in arretes)
        # total energy
        energy = edist + erep + espring
        
        return energy
    
    def next(self):
        """ select the next edge to collapse based on the energy function
        Returns:
            tuple: the edge to collapse
        """
        self._check_reader()
        faces = self.mesh_reader.faces
        V = self.mesh_reader.vertices
        
        # compute the energy of each edge and select the one with the minimum energy
        min_energy = float('inf')
        best_edge = None
        ite = 0
        while ite < self.nb_iter:
            f = random.choice(faces)
            edge = tuple(random.sample(f,2))
            
            # compute the energy of the edge collapse
            V_new, faces_new = self.simulate_edge_collapse(V, faces, edge)
            energy = self.energy(V_new, faces_new)
            if energy < min_energy:
                min_energy = energy
                best_edge = edge
            ite += 1
        
        
        return best_edge
    
    

        ### self.arretes = [] # list of edges in the mesh # ATTENTION : this is not updated when the mesh is modified, so it may be wrong after some collapses
        ### for f in self.mesh_reader.faces:
        ###     for u, v in ((f.a, f.b), (f.b, f.c), (f.c, f.a)):
        ###         arete = (min(u, v), max(u, v))
        ###         if arete not in self.arretes:
        ###             self.arretes.append(arete)