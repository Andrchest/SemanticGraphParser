import json

import tree_sitter_python as tspython
from tree_sitter import Language, Parser
import networkx as nx
import matplotlib.pyplot as plt

PY_LANGUAGE = Language(tspython.language())

parser = Parser(PY_LANGUAGE)

# Sample Python source code
source_code = b"""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""

# Parse the source code
tree = parser.parse(source_code)

# Define a query to find function definitions
query = PY_LANGUAGE.query("""
(function_definition
  name: (identifier) @my_name)
""")

# Get the root node of the tree
root_node = tree.root_node

# Execute the query
captures = query.captures(root_node)

print(captures)

# Print the results
for capture in captures["my_name"]:
    node = capture
    print(f"Function name: {node.text.decode('utf-8')}")
