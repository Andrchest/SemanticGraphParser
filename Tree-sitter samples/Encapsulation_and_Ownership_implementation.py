from pprint import pprint
import networkx as nx
import tree_sitter_python as tspython
from PIL import Image
from tree_sitter import Language, Parser

# Build the language object for Python
PY_LANGUAGE = Language(tspython.language())

# Initialize the parser with the Python language
parser = Parser(PY_LANGUAGE)

# Read the source code to analyze
with open("tmp_repo/tmp3.py", 'rb') as f:
    source_code = f.read()

# Parse the source code to create a syntax tree
tree = parser.parse(source_code)

# Define a Tree-Sitter query to capture function and class definitions
query = PY_LANGUAGE.query("""
(class_definition
    name: (identifier) @class.name
    body: (block) @class.body
)

(function_definition
    name: (identifier) @func.name
    parameters: (parameters) @func.parameters
    body: (block) @func.body
)
""")

# Capture the root node of the syntax tree
root_node = tree.root_node

# Use the query to extract relevant parts of the syntax tree
captures = query.captures(root_node)

# Print the raw captures for debugging and verification
pprint(captures)
print()

# Sort captures for functions and classes by their position in the code
for x in captures:
    captures[x].sort(key=lambda x: x.start_byte)

# Print captured function names with parameters
for i in range(len(captures["func.name"])):
    print(
        f"Function {captures['func.name'][i].text.decode('utf-8')}{captures['func.parameters'][i].text.decode('utf-8')}"
    )

# Create a directed graph to represent code structure
G = nx.DiGraph()
definitions = []

# Prepare function definitions for graph processing
for i in range(len(captures["func.name"])):
    definitions.append(
        [captures["func.name"][i].text.decode('utf-8'), captures["func.body"][i].start_byte, 0, "function"]
    )
    definitions.append(
        [captures["func.name"][i].text.decode('utf-8'), captures["func.body"][i].end_byte, 1, "function"]
    )

# Prepare class definitions for graph processing
for i in range(len(captures["class.name"])):
    definitions.append(
        [captures["class.name"][i].text.decode('utf-8'), captures["class.body"][i].start_byte, 0, "class"]
    )
    definitions.append(
        [captures["class.name"][i].text.decode('utf-8'), captures["class.body"][i].end_byte, 1, "class"]
    )

# Sort definitions by their starting byte position and entry/exit status
definitions.sort(key=lambda x: [x[1], x[2]])

# Print the sorted definitions for debugging
print()
pprint(definitions)

# Initialize the path and counter for constructing the graph hierarchy
path = ["source.py"]
counter = 0
G.add_node("/".join(path), nesting=counter, color="green")

# Construct the graph by traversing the definitions
for x in definitions:

    if x[2] == 0:  # Entering a new scope
        counter += 1
        path.append(x[0])

        # Add the new node to the graph with appropriate attributes
        if x[3] == "function":
            G.add_node("/".join(path), nesting=counter, color="orange")
        if x[3] == "class":
            G.add_node("/".join(path), nesting=counter, color="blue")

        # Add an edge indicating ownership and encapsulation in the hierarchy
        if len(path) == 2:
            G.add_edge("/".join(path[:-1]), "/".join(path), type="Encapsulation")
        else:
            G.add_edge("/".join(path[:-1]), "/".join(path), type="Ownership")

    if x[2] == 1:  # Exiting the current scope
        counter -= 1
        path.pop()

    if counter < 0:  # Sanity check for invalid nesting
        print("ERROR!")

# Extract node attributes (color, nesting) for visualization
node_labels = nx.get_node_attributes(G, 'nesting')
node_colors = nx.get_node_attributes(G, 'color')
node_names = {node: str(node) for node in G.nodes()}
edge_labels = nx.get_edge_attributes(G, 'type')

# Create a DOT (graph description) representation
dot = nx.nx_pydot.to_pydot(G)

# Set node styles, colors, and labels
for node in G.nodes():
    # Get the first node from the list returned by get_node
    pydot_node = dot.get_node(str(node))[0]
    pydot_node.set_fillcolor(node_colors[node])
    pydot_node.set_style("filled")  # Make the node visually filled
    pydot_node.set_label(node.split("/")[-1])  # Label with the last path segment

# Set edge labels (e.g., ownership relationships)
for edge in G.edges():
    pydot_edge = dot.get_edge(str(edge[0]), str(edge[1]))[0]
    pydot_edge.set_label(edge_labels[(edge[0], edge[1])])

# Save the resulting graph visualization as a PNG image
dot.write_png('graph.png')

# Optionally, display the generated graph image
img = Image.open('graph.png')
img.show()
