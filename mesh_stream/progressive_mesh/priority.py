from abc import ABC, abstractmethod

from mesh_stream import obja
import random

class PriorityComputer(ABC):

    @abstractmethod
    def compute(self, model: obja.Model):
        pass


class RandomPriority(PriorityComputer):
    
    def compute(self, model: obja.Model):
        prio = {}
        edges = [] # FAUT LA LISTE DES ARETES
        for edge in edges:
            prio[edge] = random.random()
        return prio


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
 
        

########################### Priorité basé sur QEM (Quadric Error Metric) du 3eme papier ##############################
# Section 4.1 : Algorithme
# On associe une matrice symétrique 4*4 Q à chaque sommet et l'erreur au sommet v : v^T Q v
# Pour une contraction : Q = Q1 + Q2 et l'erreur v^T (Q1+Q2) v

        