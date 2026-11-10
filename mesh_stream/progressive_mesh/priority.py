from abc import ABC, abstractmethod
import heapq
import random
from collections.abc import Sequence
import numpy as np

from mesh_stream import obja

from .mesh_reader import MeshReader


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

########################### Priorité basé sur les poids du 2ème papier ########################
# Section 3 : "the difference of the two endpoints' scalar attributes is called the weight of the edge"
# Section 4.1 : "we use a priority queue and put removable edges with its weight as its priority into it, which has been described in Section 3 and has
#                   been calculated during finding the base edges. Therefore, the edge with smaller weight will be removed earlier"

# (Il faudra utiliser le 'Half Edge Collapse'pour la fusion de 2 sommets)
# Le poids d'une arête est la différence entre les attributs scalaire  (entre les normale ?) de ces 2 sommets
# Section 3 : "S is the set of scalar attributes [..] like the normal vectors"

        # Calcul des normales de chaque face
        # Savoir quelle face on attribue à quel sommet
        # Calcul le poids de chaque sommet (le plus petit poids en 1er) (differnce entre les normales (?))
 
        

###################"######## Priorité basé sur QEM (Quadric Error Metric) du 3eme papier ##############################
# Section 4.1 : Algorithme
# On associe une matrice symétrique 4*4 Q à chaque sommet et l'erreur au sommet v : v^T Q v
# Pour une contraction : Q = Q1 + Q2 et l'erreur v^T (Q1+Q2) v

# 1. Calcul matrices Q initiales pour chaque sommet. Q = somme des Kp  (voir section 5)
# 2. Sélection des paires valides :  arêtes directes ou distance < t (section 3.2)
# 3. Calculer leur coût (erreur) optimale (?)
# 4. On place toutes les paires dans un tas classé par coût (= l'erreur), avec la paire au plus bas coût en haut
# 5. Fusionne la paire au plus petit coût


###################"######## Priorité basé  Mesh Saliency 4eme papier ###########################################
# On mesure l'importance visuelle
# score de saillance élevée quand une zone est variée et complexes (il y a bcp d'info)
# score de saillancé élevée ie entropie haute => forte priorité

# Section 3 : l'Algo
#   1. Calcul de la courbure locale pour chaque sommet + son voisinage de rayon r
#   2. les "bins" 
#   3. Pondération par les aires avec les cellules de Voronoï (section 3.2) 
#   4. Calcul de "l'entropie de la courbure locale" (LCE) (section 3.1) : + le score est élevé, + la zone est impt (forte saillance)
#   5. Approche multi-echelle : On fait varier le rayon (rmax = 0.08 √AM)

class SaliencyPriority(Priority):
    """
    blabla
    """
    def __init__(self):
        super().__init__()
        

    def next(self) -> tuple:
        self._check_reader()
        assert self.mesh_reader is not None
        
        vertices = self.mesh_reader.vertices
        faces = self.mesh_reader.faces
        
        # 1. Calculer la saillance (LCE) pour chaque sommet (Rayon max rmax = 0.08 * sqrt(Aire), 
        #    multi-échelle, discrétisation en bins, pondération Voronoï, entropie de Shannon).
        # 2. Utiliser ces scores de saillance pour une file de priorité (heap).
        # 3. Retourner la prochaine arête / paire à simplifier sous forme de tuple, 
        pass
    
    
    # Calcul de la surface totale AM du maillage (Section 4)
    def surface_totale(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face]) -> float:
        aire_tot = 0
        for f in faces :
            p0, p1, p2 = vertices[f[0]], vertices[f[1]], vertices[f[2]]
            prod = np.cross(p1 - p0, p2 - p0)
            aire_tot +=  np.linalg.norm(prod)/2
        return aire_tot

            
    #Calcul de la courbure locale pour chaque sommet (Section 3.1)
    def curvature(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face]) -> np.ndarray:
        # utilise la bibliotheque libigl
        V = np.array(vertices, dtype=np.float64)
        F = np.array(faces, dtype=np.int32)
        _, _, k1, k2 = igl.principal_curvature(V, F)
        courb= (k1+k2)/2
        return np.abs(courb) # abs ou pas ?

    # faire un graph pour la fonction lce
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
    def lce(self, vertex_idx: int, radius: float, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face]) -> float:
        """
        - Discrétisation en bins (256 bins) (Section 3.1 & 4)
        - Pondération par les cellules de Voronoï / aires (Section 3.2)
        - Calcul de l'entropie de Shannon H(vi) = -sum(p * log2(p)) (Section 3.1)
        """
        n = len(vertices)
        V = np.array(vertices, dtype=np.float64)
        F = np.array(faces, dtype=np.int32)

        courb =  self.curvature(vertices, faces)
        distances = dijkstra(csgraph=graphe, directed=False, indices=vertex_idx)

        # Récup les voisins dans le rayon `radius`
        vois = np.where(distances <= radius)[0]
        if len(vois) <= 1:
            return 0.0

         # les courbures et aires du voisinage
        courb = courb[vois]
        aires = vertex_areas[vois]

        #  256 bins (Section 3.1 et 4)

        #  Pondération par les cellules de Voronoï / aires (Section 3.2)
        poids, _ = np.histogram( courb,256, aires)
        total = np.sum(poids)
        
        probabilities = poids / total

        # entropie de Shannon (Section 3.1)
        probabilities = probabilities[probabilities > 0]
        entropy = -np.sum(probabilities * np.log2(probabilities))

        return float(entropy)
        


    # Approche multi-échelle : rayon max rmax = 0.08 * sqrt(AM) et combinaison sur 5 niveaux (Section 3.3 & 4)
    def saliency(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face], total_area: float) -> np.ndarray:
        curvatures = self.curvature(vertices, faces)
        rmax = 0.08 * np.sqrt(total_area)
        scores = np.zeros()
        for i in range(n_vertices):
                scores[i] += self.lce(i,radius,V, F,curvatures, vertex_areas=vertex_areas)
        return scores


    # Remplissage du tas avc la saillance 
    def initialize_heap(self, vertices: Sequence[np.ndarray], faces: Sequence[obja.Face], saliencies: np.ndarray):
        self.min_heap = []
        edges = set()
        
        # Les arêtes uniques
        for f in faces:
            edges.add(tuple(sorted((f[0], f[1]))))
            edges.add(tuple(sorted((f[1], f[2]))))
            edges.add(tuple(sorted((f[2], f[0]))))
            
        # les arêtes dans le tas
        for u, v in edges:
            prio = (saliencies[u] + saliencies[v]) / 2.0
            heapq.heappush(self.min_heap, (prio, (u, v)))
            
   