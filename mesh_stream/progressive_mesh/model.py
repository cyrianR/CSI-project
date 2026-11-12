#!/usr/bin/env python

from re import L
from traceback import format_list

import numpy as np
import sys
import argparse
import random
from itertools import permutations
import copy

from mesh_stream import obja
from .priority import Priority, RandomPriority, WeightPriority
from .mesh_reader import MeshReader


def edge_collapse(vertices: list, faces: list, s: int, t: int):
    """
    Collapse an edge of the mesh and save the vertex split information. 

    Args:
        vertices (list[int]): Vertices of the mesh. 
        faces (list[obja.Face]): Faces of the mesh.
        s (int): First vertex index of the edge.
        t (int): Second vertex index of the edge.

    Returns:
        list: The vertex split information as an array of the following format [s,l,r,t,vs,vt]
            s : Kept vertex index.
            l : Neighbour vertex index of s and t. Defaults to None if (s,t) is a boundary edge.
            r : Neighbour vertex index of s and t. Defaults to None if (s,t) is a boundary edge.
            t : Removed vertex index.
            vs : First vertex of the edge.
            vt : Second vertex of the edge.
    
    Note : 
        - t and s should be a valid collapse edge.
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

    # Remove collapsed faces and save neighbour vertices r and l
    l, r = None, None
    faces_to_remove = []
    for f in faces:
        if s in list(f) and t in list(f):
            k = f.index(s)
            if f[(k + 1) % 3] == t: # if t is just after s in the ordered indexes of the face then the current face is (s,t,l)
                l = f[(k + 2) % 3]
            else:                   # otherwise t is just before s in the ordered indexes of the face and the current face is (s,r,t)
                r = f[(k + 1) % 3]
            faces_to_remove.append(f)
            
    for f in faces_to_remove:
        faces.remove(f)

    # Replace t with s in all faces
    for f in faces:
        for i in range(3):
            if f[i] == t:
                f[i] = s

    # Remove unreferenced vertex vt
    vertices.pop(t)

    # Change the index of vt to remember in the vsplit transform
    t_new = len(vertices)

    # Compact indexes
    for f in faces:
        for i in range(3):
            if f[i] > t:
                f[i] -= 1
    l_new = None if l == None else l-1 if l > t else l
    s_new = s-1 if s > t else s
    r_new = None if r == None else r-1 if r > t else r

    return [s_new, l_new, r_new, t_new, vs, vt]


def fan_traversal(faces: list, center: int, start: int, stop: int, rotation: str):
    """Fan traversal around given corner from start to stop endpoints.
    If fan is not completely continuous, traversal is only computed from start to the first cut.

    Args:
        faces (list): Faces of the mesh.
        center (int): Center of the fan.
        start (int): Start vertice index of the endpoints of the fan.
        stop (int): Stop vertice index of the endpoints of the fan.
        rotation (str): Direction of the traversal around the center.

    Returns:
        fi_list (list): Indexes of the faces found in the traversal in order.
        f_list (list): Faces found in the traversal in order.
        endpoints (list): Endpoints of the traversal in order. Note: endpoints[0] == start.
    """
    # i is the index of the last found endpoint in the current face with respect to the center modulo 3
    if rotation == "direct":
        i = 1
    elif rotation == "inverse":
        i = 2
    else:
        raise ValueError("Argument <rotation> unrecognized. Accepted values are `direct` or `inverse`.")

    f_list = []
    fi_list = []
    endpoints = [start]

    fan_end = False
    while not fan_end:
        found = False
        for (fi,f) in enumerate(faces):
            if center in f and f[(f.index(center) + i) % 3] == endpoints[-1]:
                endpoints.append(f[(f.index(center) + (i % 2) + 1) % 3])
                fi_list.append(fi)
                f_list.append(f)
                found = True
                break
        if not found:
            fan_end = True
        if not fan_end and ((stop != None and endpoints[-1] == stop) or endpoints[-1] == start):
            fan_end = True

    return fi_list, f_list, endpoints


def invalid_edges(faces: list):
    """
    Find invalid edges according to the link condition.

    Args:
        faces (list): Faces of the mesh.

    Returns:
        list(tuple): List of invalid edges.
    """
    vertex_neighbours = {}
    edge_neighbours = {}

    for f in faces:
        
        for v in (f.a, f.b, f.c):
            vertex_neighbours.setdefault(v, set())
        
        vertex_neighbours[f.a].add(f.b)
        vertex_neighbours[f.a].add(f.c)
        vertex_neighbours[f.b].add(f.c)
        vertex_neighbours[f.b].add(f.a)
        vertex_neighbours[f.c].add(f.b)
        vertex_neighbours[f.c].add(f.a)

        for u, v, neighbour in ((f.a,f.b,f.c), (f.c,f.a,f.b), (f.b,f.c,f.a)):
            edge = tuple(sorted((u,v)))
            edge_neighbours.setdefault(edge, set()).add(neighbour)
        
    invalid = []

    for (u, v), edge_neighbours in edge_neighbours.items():
        common_neighbours = vertex_neighbours[u] & vertex_neighbours[v]
        if common_neighbours != edge_neighbours:
            invalid.append((u,v))
    
    return invalid
        

class ProgressiveMesh(obja.Model):
    """
    Progressive Meshes model implementation.

    Attributes:
        vsplits (list): Vertex split transforms in reconstruction order.
                        vsplits[0] corresponds to the last edge collapse applied to the progressive mesh.
        compressed_vertices (list): The compressed vertices of the coarse mesh after collapse.
        compressed_faces (list): The compressed faces of the coarse mesh after collapse.
    """
    def __init__(self):
        super().__init__()
        self.vsplits = []
        self.compressed_vertices = None
        self.compressed_faces = None

    def _update_vsplits_indices(self, t: int, t_new: int):
        """
        Update indices in previously stored vertex splits after removing vertex t and appending it at index t_new.
        """

        def remap(index):
            if index is None:
                return None
            if index == t:
                return t_new
            if t < index <= t_new:
                return index - 1
            return index

        for vsplit in self.vsplits:
            vsplit[0] = remap(vsplit[0])
            vsplit[1] = remap(vsplit[1])
            vsplit[2] = remap(vsplit[2])

    def collapse(self, max_collapse: int, priority: Priority):
        """
        Collapse the mesh with a given maximum of iterations.
        Save transformations information in self.vsplits and compressed mesh in
        self.compressed_vertices and self.compressed_faces.

        Args:
            max_collapse (int): Maximum number of edge collapse steps.
            priority (Priority): A priority object defining the strategy to choose next edge to collapse.
        """
        self.compressed_vertices = copy.deepcopy(self.vertices)
        self.compressed_faces = copy.deepcopy(self.faces)

        priority.set_reader(MeshReader(self))

        while len(self.compressed_faces) > 0 and len(self.vsplits) < max_collapse:
            
            edge = priority.next(invalid_edges(self.compressed_faces))
            print(edge)

            if edge is None:
                break
            else:
                s, t = edge
            
            vsplit = edge_collapse(self.compressed_vertices, self.compressed_faces, s, t)

            # Update previous vsplits
            t_new = vsplit[3]
            self._update_vsplits_indices(t, t_new) 

            self.vsplits.insert(0, vsplit)


    def write(self, path):
        """
        Write the progressive transforms operations in OBJA format.

        Args:
            path (str): Path to OBJA output file.
        """
        with open(path, "w") as output:
            output_model = obja.Output(output, random_color=True)

            # Write the compressed mesh (coarser mesh)
            for (vi, v) in enumerate(self.compressed_vertices):
                output_model.add_vertex(vi, v)
            for (fi, f) in enumerate(self.compressed_faces):
                output_model.add_face(fi, face=f)

            # Write the transforms (vsplits)
            faces_buffer = copy.deepcopy(self.compressed_faces)
            for vsplit in self.vsplits:

                s, l, r, t, vs, vt = vsplit

                assert t == len(output_model.vertex_mapping)

                # Add vt to mesh
                output_model.add_vertex(t, vt)

                assert output_model.vertex_mapping[t] == t

                # Place vs to its original position
                output_model.edit_vertex(s, vs)

                # Edit the faces to reconnect to vt
                fi_list_direct, f_list_direct, endpoints_direct = [], [], []
                fi_list_inverse, f_list_inverse = [], []

                if r != None:
                    fi_list_direct, f_list_direct, endpoints_direct = fan_traversal(faces_buffer, s, r, l, "direct")
                if l != None and (r == None or endpoints_direct[-1] != l):
                    fi_list_inverse, f_list_inverse, _ = fan_traversal(faces_buffer, s, l, r, "inverse")

                fi_list = fi_list_direct + fi_list_inverse
                f_list = f_list_direct + f_list_inverse

                for fi, f in zip(fi_list, f_list):
                    new_face = f.clone()
                    k = f.index(s) # index of s in face f
                    new_face[k] = t # here maybe t_new not needed from vsplit since we always use the last index 
                    output_model.edit_face(fi, new_face) # edit face in obja model
                    faces_buffer[fi] = new_face # edit face in buffer
                
                # Add the new faces (s,t,l) and (s,r,t)
                if l != None:
                    output_model.add_face(len(faces_buffer), obja.Face(s, t, l))
                    faces_buffer.append(obja.Face(s, t, l))
                if r != None:
                    output_model.add_face(len(faces_buffer), obja.Face(s, r, t))
                    faces_buffer.append(obja.Face(s, r, t))


def main():
    """
    Runs the program on the model given as argument parameters.
    """
    parser = argparse.ArgumentParser(description="Run the progressive meshes model on a 3D OBJ file.")
    parser.add_argument("input", type=str, help="Input OBJ file")
    parser.add_argument("output", type=str, help="Output OBJA file")
    parser.add_argument("max_collapse", type=int, help="Maximum number of edge collapse steps")
    args = parser.parse_args()

    np.seterr(invalid="raise")

    model = ProgressiveMesh()
    model.parse_file(args.input)
    model.collapse(args.max_collapse, WeightPriority())
    model.write(args.output)


if __name__ == '__main__':
    main()
