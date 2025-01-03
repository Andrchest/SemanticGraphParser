import json

import tree_sitter_python as tspython
from tree_sitter import Language, Parser
import networkx as nx
import matplotlib.pyplot as plt

PY_LANGUAGE = Language(tspython.language())

parser = Parser(PY_LANGUAGE)

tree = parser.parse(
    bytes(
        """
from Tree import sqrt, own_srt

class Point:

    def __init__(self, val1, val2):
        self.x = val1
        self.y = val2

    def print_point(self):
        print(self.x, self.y)

    def decor():
        print("decorator")
        def func():
            return "func"


def foo(a, b, c):
    return max(a, b, c)

a = Point(1, 1)
a.print_point()
""",
        "utf8"
    )
)

def tree_to_dict(node):
    return {
        'type': node.type,
        'start_byte': node.start_byte,
        'end_byte': node.end_byte,
        'children': [tree_to_dict(child) for child in node.children]
    }

# Convert the root node to a dictionary
tree_dict = tree_to_dict(tree.root_node)

# Save the dictionary to a JSON file
with open('parsed_tree1.json', 'w') as json_file:
    json.dump(tree_dict, json_file, indent=4)

print("Syntax tree saved to parsed_tree.json")
