from pprint import pprint
import networkx as nx
import tree_sitter_python as tspython
from PIL import Image
from tree_sitter import Language, Parser
from os import listdir
from os.path import isfile


def find_files(path):

    files = []

    for file in listdir(path):

        current_instance = path + "\\" + file

        if isfile(current_instance) and file[-3:] in SUPPORTED_LANGAGUES:
            files.append(current_instance)
        elif not isfile(current_instance):
            files.extend(find_files(current_instance))

    return files


def build_encapsulation_and_ownership(repo_path, G):

    PY_LANGUAGE = Language(tspython.language())
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(bytes(source_code, 'utf-8'))

    colors = {'function' : 'orange', 'class' : 'blue', 'script' : 'green'}

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

    captures = query.captures(tree.root_node)


    for x in captures:
        captures[x].sort(key=lambda x: x.start_byte)

    definitions = []

    if "func.name" in captures.keys():
        for i in range(len(captures["func.name"])):
            definitions.append(
                {
                'name': captures["func.name"][i].text.decode('utf-8'),
                'start_byte' : captures["func.body"][i].start_byte,
                'nesting' : 0,
                'type': 'function',
                'end_byte' : captures["func.body"][i].end_byte,
                'start_point' : captures["func.body"][i].start_point,
                'end_point' : captures["func.body"][i].end_point,
                'for_sorting' : [captures["func.body"][i].start_byte, 0]
                }
            )
            definitions.append(
                {
                'name' : captures["func.name"][i].text.decode('utf-8'),
                'end_byte' : captures["func.body"][i].end_byte,
                'nesting' : 1,
                'type' : "function",
                'for_sorting' : [captures["func.body"][i].end_byte, 1]
                }
            )

    if "class.name" in captures.keys():
        for i in range(len(captures["class.name"])):
            definitions.append(
                {
                'name': captures["class.name"][i].text.decode('utf-8'),
                'start_byte' : captures["class.body"][i].start_byte,
                'nesting' : 0,
                'type': 'class',
                'end_byte' : captures["class.body"][i].end_byte,
                'start_point' : captures["class.body"][i].start_point,
                'end_point' : captures["class.body"][i].end_point,
                'for_sorting' : [captures["class.body"][i].start_byte, 0]
                }
            )
            definitions.append(
                {
                'name' : captures["class.name"][i].text.decode('utf-8'),
                'end_byte' : captures["class.body"][i].end_byte,
                'nesting' : 1,
                'type' : "class",
                'for_sorting' : [captures["class.body"][i].end_byte, 1]
                }
            )

    # Sort definitions by their starting byte position and entry/exit status
    definitions.sort(key=lambda x: x['for_sorting'])

    # Initialize the path and counter for constructing the graph hierarchy
    # path - the name of a current file (only name, but not a full path)
    path = [repo_path.split(chr(92))[-1]] 
    counter = 0
    G.add_node(path[0], nesting=counter, color=colors['script'])

    # Construct the graph by traversing the definitions
    for x in definitions:

        if x['nesting'] == 0:  # Entering a new scope
            counter += 1
            path.append(x['name'])
            # body=source_code[x[1] : x[4]]
            G.add_node(
                    "/".join(path), nesting=counter, color=colors[x['type']],
                    start_byte=x['start_byte'], end_byte=x['end_byte'],
                    start_point=x['start_point'], end_point=x['end_point'],
                    body=source_code[x['start_byte'] : x['end_byte']]
                    )

            # Add an edge indicating ownership and encapsulation in the hierarchy
            if len(path) == 2:
                G.add_edge("/".join(path[:-1]), "/".join(path), type="Encapsulation")
            else:
                G.add_edge("/".join(path[:-1]), "/".join(path), type="Ownership")

        if x['nesting'] == 1:  # Exiting the current scope
            counter -= 1
            path.pop()

        if counter < 0:  # Sanity check for invalid nesting
            print("ERROR!")


# dot cant work with code snipets thus remove "body" from nodes parameters ro run
def print_graph(G):

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


# for testing/debugging
def print_nodes(G):
    for node in G.nodes:
        print(node, '-------------------->', G.nodes[node])


SUPPORTED_LANGAGUES = ['.py']

repo_path = input()

files_to_parse = find_files(repo_path)

graph = nx.DiGraph()

for file in files_to_parse:

    with open(file, 'r') as f:
        source_code = f.read()

    build_encapsulation_and_ownership(file, graph)

print_graph(graph)
print_nodes(graph)