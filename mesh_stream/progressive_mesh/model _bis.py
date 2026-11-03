#!/usr/bin/env python

import numpy as np
import sys
import argparse
import random
from itertools import permutations
import copy
from collections.abc import MutableSequence, Sequence
import numpy as np

from mesh_stream import obja
from .priority import Priority, RandomPriority


def edge_collapse(vertices: MutableSequence[np.ndarray], faces: MutableSequence[obja.Face],
    s: int, t: int, target: np.ndarray) -> list:
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
    if not (0 <= s < len(vertices) and 0 <= t < len(vertices)):
        raise IndexError(f"Vertex indices out of range: ({s}, {t})")

    incident = [f for f in faces if s in f and t in f]
    if not incident:
        raise ValueError(f"Edge ({s}, {t}) does not exist.")
    if len(incident) > 2:
        raise ValueError(
            f"Edge ({s}, {t}) has {len(incident)} incident faces; "
            "the current vertex-split record supports at most two."
        )

    # Save original positions before changing either vertex.
    vs = vertices[s].copy()
    vt = vertices[t].copy()

    # The face(s) removed by the collapse encode the two opposite vertices.
    opposite = []
    for face in incident:
        opposite.append(next(v for v in face if v != s and v != t))

    # Record the removed vertex's neighbors in a stable order.
    l = opposite[0] if len(opposite) >= 1 else None
    r = opposite[1] if len(opposite) >= 2 else None

    # Move the survivor to the QEM-selected target.
    vertices[s] = np.asarray(target, dtype=vertices[s].dtype).copy()

    # Replace t by s, and discard degenerate triangles.
    kept_faces = []
    for face in faces:
        a, b, c = face
        remapped = [s if v == t else v for v in (a, b, c)]

        if len(set(remapped)) < 3:
            continue

        kept_faces.append(obja.Face(*remapped, visible=face.visible))

    # Keep the removed vertex's original ID as the final vertex in the
    # vertex-split record, then compact all indices above t.
    vertices.pop(t)
    t_new = len(vertices)

    def compact(index):
        return index - 1 if index is not None and index > t else index

    s_new = compact(s)
    l_new = compact(l)
    r_new = compact(r)

    compacted_faces = []
    for face in kept_faces:
        compacted_faces.append(
            obja.Face(
                *(compact(v) for v in face),
                visible=face.visible,
            )
        )

    # This updates the caller's list rather than rebinding a local name.
    faces[:] = compacted_faces

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

    def _vsplit_to_obja(self, output_model: obja.Output, vsplit: list):
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
