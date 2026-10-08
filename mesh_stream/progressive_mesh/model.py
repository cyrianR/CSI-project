#!/usr/bin/env python

import numpy as np
import sys
import argparse

from mesh_stream import obja
from .priority import PriorityComputer, RandomPriority

class ProgressiveMesh(obja.Model):
    """
    Progressive Meshes model implementation. 
    """
    def __init__(self):
        super().__init__()
        self.operations = []
        self.edges_priority = []
        

    def build(self, priority: PriorityComputer):
        """
        Construct the progressive mesh of the model.
        """
        self.edges_priority = priority.compute(self);

        # Apply edge collapses and save what we need (vsplits, ..) in operations or in others attributes
        # TODO


    def write(self, path):
        """
        Write the operations for in OBJA format.
        """
        with open(path, "w") as output:
            output_model = obja.Output(output, random_color=True)

            # Certainly reverse operations here, depends on what we do in build()
            # TODO

            for op in self.operations:
                # TODO
                pass


def main():
    """
    Runs the program on the model given as argument parameters.
    """
    parser = argparse.ArgumentParser(description="Run the progressive meshes model on a 3D OBJ file.")
    parser.add_argument("input", help="Input OBJ file")
    parser.add_argument("output", help="Output OBJA file")
    args = parser.parse_args()

    np.seterr(invalid="raise")

    model = ProgressiveMesh()
    model.parse_file(args.input)
    model.build(RandomPriority())
    model.write(args.output)


if __name__ == '__main__':
    main()
