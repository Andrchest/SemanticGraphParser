import json
import os
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

    colors = {'function': 'orange', 'class': 'blue', 'script': 'green'}

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
                    'start_byte': captures["func.body"][i].start_byte,
                    'nesting': 0,
                    'type': 'function',
                    'end_byte': captures["func.body"][i].end_byte,
                    'start_point': captures["func.body"][i].start_point,
                    'end_point': captures["func.body"][i].end_point,
                    'for_sorting': [captures["func.body"][i].start_byte, 0]
                }
            )
            definitions.append(
                {
                    'name': captures["func.name"][i].text.decode('utf-8'),
                    'end_byte': captures["func.body"][i].end_byte,
                    'nesting': 1,
                    'type': "function",
                    'for_sorting': [captures["func.body"][i].end_byte, 1]
                }
            )

    if "class.name" in captures.keys():
        for i in range(len(captures["class.name"])):
            definitions.append(
                {
                    'name': captures["class.name"][i].text.decode('utf-8'),
                    'start_byte': captures["class.body"][i].start_byte,
                    'nesting': 0,
                    'type': 'class',
                    'end_byte': captures["class.body"][i].end_byte,
                    'start_point': captures["class.body"][i].start_point,
                    'end_point': captures["class.body"][i].end_point,
                    'for_sorting': [captures["class.body"][i].start_byte, 0]
                }
            )
            definitions.append(
                {
                    'name': captures["class.name"][i].text.decode('utf-8'),
                    'end_byte': captures["class.body"][i].end_byte,
                    'nesting': 1,
                    'type': "class",
                    'for_sorting': [captures["class.body"][i].end_byte, 1]
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


def build_import(file_path, G):
    '''
    The function is used to connect nodes from the statement "import some_name",
    a variable source_file is the last part of "some_name" because there are no folders and, thus,
    the name Folder/file_name does not exsists. for_wildcard is optional parameter: by defolt it is false,
    hence we just build new edges, if for_wildcard is true, we need to connect all "some_name" neighbors with script
    node
    '''

    def for_import(dct, key_name, for_wildcards=False):

        for file in dct[key_name]:
            # as script names contains only file name, we take the last part of import: Folder1.smt --> smt.py
            source_file = source_code[file.start_byte: file.end_byte].replace('.', '/').split('/')[-1]
            source_file += '.py'

            # if source file is not a installed library like math and so on add an edge
            if source_file in repo_files:
                if not for_wildcards:
                    G.add_edge(connect_with, source_file, type="Import")
                else:
                    # out_edges: [(source_file, its_neighbor1), ...], so we take the second element
                    for node in G.out_edges(source_file):
                        G.add_edge(connect_with, node[1], type="Import")

    def for_import_from(dct, key_name, type):

        for instance in dct[key_name]:
            # define the name of a file or instance, and if it is file add .py
            name = source_code[instance.start_byte: instance.end_byte]
            if type == 'file':
                name = name.replace('.', '/').split('/')[-1] + '.py'

            definitions.append({'type': type,
                                'name': name,
                                'start_byte': instance.start_byte,
                                })

    PY_LANGUAGE = Language(tspython.language())
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(bytes(source_code, 'utf-8'))

    # list all files from repo to futher check if an imported file is a installed library
    # or file from repo
    repo_files = [file.split('\\')[-1] for file in files_to_parse]

    # 3 types of queries: 1st - simple import: 'import smt' or 'from smth import smt'
    # 2nd - for aliased import where 'as' exsists
    # 3rd - for 'from smt import *'
    query = PY_LANGUAGE.query("""
    (import_statement
        name: (dotted_name) @file.name
    )

    (import_from_statement
        module_name: (dotted_name) @script.name
        name: (dotted_name) @imports
    )              
    """)

    query_aliased = PY_LANGUAGE.query("""
    (import_statement
        name: (aliased_import) @file
    )

    (import_from_statement
        module_name: (dotted_name) @script.name
        name: (aliased_import) @imports
    )              
    """)

    query_wildcard = PY_LANGUAGE.query("""
    (import_from_statement
        module_name: (dotted_name) @script.name
        (wildcard_import)
    )              
    """)

    captures = query.captures(tree.root_node)
    captures_aliased = query_aliased.captures(tree.root_node)
    captures_wildcard = query_wildcard.captures(tree.root_node)

    # define a file name to which we import smth
    connect_with = file_path.split(chr(92))[-1]
    # print(connect_with)

    # define a file from which we import
    source_file = ''

    # list with all imports
    definitions = []

    # connect 1st type 'import smt'
    if 'file.name' in captures.keys():
        for_import(captures, 'file.name')

    # same for other types
    if 'file' in captures_aliased.keys():
        captures_aliased['file'] = [file.children[0] for file in captures_aliased['file']]
        for_import(captures_aliased, 'file')

    if 'script.name' in captures_wildcard.keys():
        for_import(captures_wildcard, 'script.name', for_wildcards=True)

    # add to definitions elemnets: [type(file or instance in file), name, start_byte for sorting]
    if 'script.name' in captures.keys():
        for_import_from(captures, 'imports', 'instance')
        for_import_from(captures, 'script.name', 'file')

    # same things to aliased
    if 'script.name' in captures_aliased.keys():
        # replace node with name: name_aliased with normal one
        captures_aliased['imports'] = [instance.children[0] for instance in captures_aliased['imports']]

        for_import_from(captures_aliased, 'imports', 'instance')
        for_import_from(captures_aliased, 'script.name', 'file')

    # sort the array
    definitions.sort(key=lambda x: x['start_byte'])

    # now it looks like: file, object, object, ..., new_file, new_object ...

    # pprint(definitions)
    # current_path == node name
    current_path = []

    for el in definitions:
        # if el is new file, current_path - its name
        if el['type'] == 'file':
            current_path = [el['name']]
        else:
            if current_path[0] in repo_files:
                # if el is instance and file in repo, current_path - file_name/instance_name
                current_path.append(el['name'])
                G.add_edge(connect_with, '/'.join(current_path), type='Import')
                # clear path for new instance
                current_path.pop()


def parse_name(name):
    result = name.replace('.', '/')
    result = result.replace('::', '.py/')
    result = result.replace('/(global)', '')
    return result


def build_invoke(G, debugging=0):
    with open("__temp__.json", "r") as f:
        data = json.load(f)

    nodes_to_nodes = dict()

    for x in data["graph"]["nodes"].values():
        node_name = x["name"]
        graph_node_name = parse_name(node_name)
        nodes_to_nodes[x["uid"]] = graph_node_name

    for x in data["graph"]["edges"]:
        node_1 = nodes_to_nodes[x["source"]]
        node_2 = nodes_to_nodes[x["target"]]

        if node_1 in G.nodes and node_2 in G.nodes:
            G.add_edge(node_1, node_2, type='Invoke')


# dot cant work with code snipets thus remove "body" from nodes parameters ro run
def print_graph(G):
    # Extract node attributes (color, nesting) for visualization
    node_labels = nx.get_node_attributes(G, 'nesting')
    node_colors = nx.get_node_attributes(G, 'color')
    edge_labels = nx.get_edge_attributes(G, 'type')

    # Create a DOT (graph description) representation
    dot = nx.nx_pydot.to_pydot(G)

    # Set node styles, colors, and labels
    for node in G.nodes():
        pydot_node = dot.get_node(str(node))[0]
        pydot_node.set_fillcolor(node_colors.get(node, 'white'))  # Default to white if no color
        pydot_node.set_style("filled")  # Make the node visually filled
        pydot_node.set_label(node.split("/")[-1])  # Label with the last path segment

    # Set edge labels and styles
    for edge in G.edges():
        pydot_edge = dot.get_edge(str(edge[0]), str(edge[1]))[0]
        edge_type = edge_labels.get((edge[0], edge[1]), 'Unknown')
        pydot_edge.set_label(edge_type)  # Set edge label to indicate the type

        # Apply special styling for Import edges
        if edge_type == "Import":
            pydot_edge.set_style("dashed")  # Dashed lines for imports
            pydot_edge.set_color("red")  # Red color for import edges
        elif edge_type == "Invoke":
            pydot_edge.set_style("bold")
            pydot_edge.set_color("green")
        else:
            pydot_edge.set_color("black")  # Default color for other edges

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

os.system(f"code2flow {repo_path} -o __temp__.json -q")

graph = nx.DiGraph()

for file in files_to_parse:
    with open(file, 'r') as f:
        source_code = f.read()

    build_encapsulation_and_ownership(file, graph)

for file in files_to_parse:
    with open(file, 'r') as f:
        source_code = f.read()

    build_import(file, graph)

build_invoke(graph)

print_graph(graph)
