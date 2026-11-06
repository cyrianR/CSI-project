#!/usr/bin/env python

import numpy as np
import sys
import argparse
import random
from itertools import permutations
import copy

from mesh_stream import obja
from .priority import Priority, RandomPriority


def edge_collapse(vertices: list, faces: list, s: int, t: int):
    """
    Collapse an edge of the mesh and save the vertex split information. 

    Args:
        vertices (list[int]): Vertices of the mesh. 
        faces (list[obja.Face]): Faces of the mesh
        s (int): First vertex index of the edge.
        t (int): Second vertex index of the edge.

    Returns:
        list: The vertex split information as an array of the following format [s,l,r,t,vs,vt]
            s : Kept vertex index.
            l : Neighbour vertex index of s and t. Defaults to None if (s,t,r) is a boundary face.
            r : Neighbour vertex index of s and t. Defaults to None if (s,t,l) is a boundary face.
            t : Removed vertex index.
            vs : First vertex of the edge.
            vt : Second vertex of the edge.
    
    Note : 
        - vertices and faces are expected to form a coherent 3D mesh.
        - obja format add a constraint to the vsplit information to save as it only supports to add 
          vertices in a queue. Therefore, the removed vertice at index t should be remembered as the last
          vertice of the current mesh (t -> t_new and t_new = max(indexes)).
    """
    if s == t:
        raise ValueError("Edge vertices s and t should differ.")
    
    edge_valid = any(s in f and t in f for f in faces)
    if not edge_valid:
        raise ValueError(f"Edge ({s}, {t}) do not exist in mesh.")

    # Save original vertices
    vs = vertices[s]
    vt = vertices[t]

    # Make vs the single vertex as midpoint of the edge
    vertices[s] = (vertices[s] + vertices[t]) / 2 

    # Replace t with s in all faces
    faces = [[s if v == t else v for v in f] for f in faces]

    # Remove collapsed faces and save neighbour vertices
    l, r = None, None
    for f in faces:
        for (i,j,k) in permutations([0,1,2]):
            if (f[i] == s and f[j] == s):
                if l == None:
                    l = k
                else:
                    r = k
                faces.remove(f)

    # Remove unreferenced vertex vt
    vertices.pop(t)

    # Change the index of vt to remember in the vsplit transform
    t_new = len(vertices)

    # Compact indexes
    faces = [[v-1 if v > t else v for v in f] for f in faces]
    l_new = l-1 if l > t else l
    s_new = s-1 if s > t else s
    r_new = r-1 if r > t else r

    return [s_new, l_new, r_new, t_new, vs, vt]


class ProgressiveMesh(obja.Model):
    """
    Progressive Meshes model implementation.

    Attributes:
        vsplits (list): Vertex split transforms in reconstruction order.
                        vsplits[0] corresponds to the last edge collapse applied to the progressive mesh.
    """
    def __init__(self):
        super().__init__()
        self.vsplits = []

    def collapse(self, max_collapse: int, priority: Priority):
        """
        Collapse the mesh with a given maximum of iterations.
        Save transformations information in self.vsplits.

        Args:
            max_collapse (int): Maximum number of edge collapse steps.
            priority (Priority): A priority object defining the strategy to choose next edge to collapse.
        """
        priority.set_reader(MeshReader(self))
        while len(self.faces) >= 2 and len(self.vsplits) < max_collapse:
            s, t = priority.next()
            vsplit = edge_collapse(self.vertices, self.faces, s, t)
            self.vsplits.insert(0, vsplit)

    def _vsplit_to_obja(output_model: obja.Output, vsplit: list):
        # Add vt to mesh
        output_model.add_vertex(vsplit[5])

        # Place vs to its original position
        output_model.edit_vertex(vsplit[0], vsplit[4])

        # TODO : finish
        
        return

    def write(self, path):
        """
        Write the progressive transforms operations in OBJA format.

        Args:
            path (str): Path to OBJA output file.
        """
        with open(path, "w") as output:
            output_model = obja.Output(output, random_color=True)

            # Write the compressed mesh (coarser mesh)
            for (vi, v) in enumerate(self.vertices):
                output_model.add_vertex(vi, v)
            for (fi, f) in enumerate(self.faces):
                output_model.add_face(fi, f)

            # Write the transforms (vsplits)
            for vsplit in self.vsplits:
                _vsplit_to_obja(output_model, vsplit)


class MeshReader:
    def __init__(self, mesh: ProgressiveMesh):
        self._mesh = mesh

    @property
    def faces(self):
        return copy.deepcopy(self._mesh.faces)

    @property
    def vertices(self):
        return copy.deepcopy(self._mesh.vertices)

    @property
    def vsplits(self):
        return copy.deepcopy(self._mesh.vsplits)


def main():
    """
    Runs the program on the model given as argument parameters.
    """
    parser = argparse.ArgumentParser(description="Run the progressive meshes model on a 3D OBJ file.")
    parser.add_argument("input", help="Input OBJ file")
    parser.add_argument("output", help="Output OBJA file")
    parser.add_argument("max_collapse", help="Maximum number of edge collapse steps")
    args = parser.parse_args()

    np.seterr(invalid="raise")

    model = ProgressiveMesh()
    model.parse_file(args.input)
    model.collapse(args.max_collapse, RandomPriority())
    model.write(args.output)


if __name__ == '__main__':
    main()
