import copy

class MeshReader:
    def __init__(self, mesh):
        self._mesh = mesh

    @property
    def faces(self):
        return copy.deepcopy(self._mesh.compressed_faces)

    @property
    def vertices(self):
        return copy.deepcopy(self._mesh.compressed_vertices)

    @property
    def vsplits(self):
        return copy.deepcopy(self._mesh.vsplits)