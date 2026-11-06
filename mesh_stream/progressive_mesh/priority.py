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


########################### Priorité basé sur les poids du 2ème papier ########################
# Section 3 : "the difference of the two endpoints' scalar attributes is called the weight of the edge"
# Section 4.1 : "we use a priority queue and put removable edges with its weight as its priority into it, which has been described in Section 3 and has
#                   been calculated during finding the base edges. Therefore, the edge with smaller weight will be removed earlier"

# (Il faudra utiliser le 'Half Edge Collapse'pour la fusion de 2 sommets)
# Le poids d'une arête est la différence entre les attributs scalaire  (entre les normale ?) de ces 2 sommets
# Section 3 : "S is the set of scalar attributes [..] like the normal vectors"


class WeightPriority(PriorityComputer):
    
    def compute(self, model: obja.Model):
        prio = {}
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
#   2. les "bins" ?
#   3. Pondération par les aires avec les cellules de Voronoï (section 3.2) 
#   4. Calcul de "l'entropie de la courbure locale" (LCE) (section 3.1) : + le score est élevé, + la zone est impt (forte saillance)
#   5. Approche multi-echelle : On fait varier le rayon (rmax = 0.08 √AM)

