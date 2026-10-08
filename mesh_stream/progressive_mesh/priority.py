from abc import ABC, abstractmethod

from mesh_stream import obja

class PriorityComputer(ABC):

    @abstractmethod
    def compute(self, model: obja.Model):
        pass


class RandomPriority(PriorityComputer):

    def compute(self, model: obja.Model):
        # TODO
        pass


# TODO : others priorities