#!/usr/bin/env python3

import sys
import numpy as np
import random

"""
obja model for python.
"""


class Face:
    """
    The class that holds a, b, and c, the indices of the vertices of the face.
    """

    def __init__(self, a, b, c, visible=True):
        self.a = a
        self.b = b
        self.c = c
        self.visible = visible

    def from_array(array):
        """
        Initializes a face from an array of strings representing vertex indices (starting at 1)
        """
        face = Face(0, 0, 0)
        face.set(array)
        face.visible = True
        return face

    def set(self, array):
        """
        Sets a face from an array of strings representing vertex indices (starting at 1)
        """
        self.a = int(array[0].split('/')[0]) - 1
        self.b = int(array[1].split('/')[0]) - 1
        self.c = int(array[2].split('/')[0]) - 1
        return self

    def clone(self):
        """
        Clones a face from another face
        """
        return Face(self.a, self.b, self.c, self.visible)

    def copy(self, other):
        """
        Sets a face from another face
        """
        self.a = other.a
        self.b = other.b
        self.c = other.c
        self.visible = other.visible
        return self

    def test(self, vertices, line="unknown"):
        """
        Tests if a face references only vertices that exist when the face is declared.
        """
        if self.a >= len(vertices):
            raise VertexError(self.a + 1, line)
        if self.b >= len(vertices):
            raise VertexError(self.b + 1, line)
        if self.c >= len(vertices):
            raise VertexError(self.c + 1, line)

    def __str__(self):
        return "Face({}, {}, {})".format(self.a, self.b, self.c)

    def __repr__(self):
        return str(self)


class VertexError(Exception):
    """
    An operation references a vertex that does not exist.
    """

    def __init__(self, index, line):
        """
        Creates the error from index of the referenced vertex and the line where the error occured.
        """
        self.line = line
        self.index = index
        super().__init__()

    def __str__(self):
        """
        Pretty prints the error.
        """
        return f"There is no vertex {self.index} (line {self.line})"


class FaceError(Exception):
    """
    An operation references a face that does not exist.
    """

    def __init__(self, index, line):
        """
        Creates the error from index of the referenced face and the line where the error occurred.
        """
        self.line = line
        self.index = index
        super().__init__()

    def __str__(self):
        """
        Pretty prints the error.
        """
        return f'There is no face {self.index} (line {self.line})'


class FaceVertexError(Exception):
    """
    An operation references a face vertex that does not exist.
    """

    def __init__(self, index, line):
        """
        Creates the error from index of the referenced face vertex and the line where the error occured.
        """
        self.line = line
        self.index = index
        super().__init__()

    def __str__(self):
        """
        Pretty prints the error.
        """
        return f'Face has no vertex {self.index} (line {self.line})'


class UnknownInstruction(Exception):
    """
    An instruction is unknown.
    """

    def __init__(self, instruction, line):
        """
        Creates the error from instruction and the line where the error occured.
        """
        self.line = line
        self.instruction = instruction
        super().__init__()

    def __str__(self):
        """
        Pretty prints the error.
        """
        return f'Instruction {self.instruction} unknown (line {self.line})'


class Model:
    """
    The OBJA model.
    """

    def __init__(self):
        """
        Initializes an empty model.
        """
        self.vertices = []
        self.faces = []
        self.line = 0

    def get_vertex_from_string(self, string):
        """
        Gets a vertex from a string representing the index of the vertex, starting at 1.

        To get the vertex from its index, simply use model.vertices[i].
        """
        index = int(string) - 1
        if index >= len(self.vertices):
            raise FaceError(index + 1, self.line)
        return self.vertices[index]

    def get_face_from_string(self, string):
        """
        Gets a face from a string representing the index of the face, starting at 1.

        To get the face from its index, simply use model.faces[i].
        """
        index = int(string) - 1
        if index >= len(self.faces):
            raise FaceError(index + 1, self.line)
        return self.faces[index]

    def parse_file(self, path):
        """
        Parses an OBJA file.
        """
        with open(path, "r") as file:
            for line in file.readlines():
                self.parse_line(line)

    def parse_line(self, line):
        """
        Parses a line of obja file.
        """
        self.line += 1

        split = line.split()

        if len(split) == 0:
            return

        if split[0] == "v":
            self.vertices.append(np.array(split[1:], np.double))

        elif split[0] == "ev":
            self.get_vertex_from_string(split[1]).set(split[2:])

        elif split[0] == "tv":
            self.get_vertex_from_string(split[1]).translate(split[2:])

        elif split[0] == "f" or split[0] == "tf":
            for i in range(1, len(split) - 2):
                face = Face.from_array(split[i:i + 3])
                face.test(self.vertices, self.line)
                self.faces.append(face)

        elif split[0] == "ts":
            for i in range(1, len(split) - 2):
                if i % 2 == 1:
                    face = Face.from_array([split[i], split[i + 1], split[i + 2]])
                else:
                    face = Face.from_array([split[i], split[i + 2], split[i + 1]])
                face.test(self.vertices, self.line)
                self.faces.append(face)

        elif split[0] == "ef":
            self.get_face_from_string(split[1]).set(split[2:])

        elif split[0] == "efv":
            face = self.get_face_from_string(split[1])
            vertex = int(split[2])
            new_index = int(split[3]) - 1
            if vertex == 1:
                face.a = new_index
            elif vertex == 2:
                face.b = new_index
            elif vertex == 3:
                face.c = new_index
            else:
                raise FaceVertexError(vertex, self.line)

        elif split[0] == "df":
            self.get_face_from_string(split[1]).visible = False

        elif split[0] == "#":
            return

        else:
            return
            # raise UnknownInstruction(split[0], self.line)


def parse_file(path):
    """
    Parses a file and returns the model.
    """
    model = Model()
    model.parse_file(path)
    return model


class Output:
    """
    The type for a model that outputs as obja.
    """

    def __init__(self, output, random_color=False):
        """
        Initializes the index mapping dictionaries.
        """
        self.vertex_mapping = dict()
        self.face_mapping = dict()
        self.output = output
        self.random_color = random_color

    def add_vertex(self, index, vertex):
        """
        Adds a new vertex to the model with the specified index.
        """
        self.vertex_mapping[index] = len(self.vertex_mapping)
        print('v {} {} {}'.format(vertex[0], vertex[1], vertex[2]), file=self.output)

    def edit_vertex(self, index, vertex):
        """
        Changes the coordinates of a vertex.
        """
        if len(self.vertex_mapping) == 0:
            print('ev {} {} {} {}'.format(index, vertex[0], vertex[1], vertex[2]), file=self.output)
        else:
            print('ev {} {} {} {}'.format(self.vertex_mapping[index] + 1, vertex[0], vertex[1], vertex[2]),
                  file=self.output)

    def add_face(self, index, face):
        """
        Adds a face to the model.
        """
        self.face_mapping[index] = len(self.face_mapping)
        print('f {} {} {}'.format(
            self.vertex_mapping[face.a] + 1,
            self.vertex_mapping[face.b] + 1,
            self.vertex_mapping[face.c] + 1,
        ),
            file=self.output
        )

        if self.random_color:
            print('fc {} {} {} {}'.format(
                len(self.face_mapping),
                random.uniform(0, 1),
                random.uniform(0, 1),
                random.uniform(0, 1)),
                file=self.output
            )

    def edit_face(self, index, face):
        """
        Changes the indices of the vertices of the specified face.
        """
        print('ef {} {} {} {}'.format(
            self.face_mapping[index] + 1,
            self.vertex_mapping[face.a] + 1,
            self.vertex_mapping[face.b] + 1,
            self.vertex_mapping[face.c] + 1
        ),
            file=self.output
        )


def main():
    if len(sys.argv) == 1:
        print("obja needs a path to an obja file")
        return

    model = parse_file(sys.argv[1])
    print(model.vertices)
    print(model.faces)


if __name__ == "__main__":
    main()
