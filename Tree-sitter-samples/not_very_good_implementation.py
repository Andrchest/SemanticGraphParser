# use full path to the repo to run. For instance, "Path to repo: /home/danil/PycharmProjects/SemanticGraphParser/Tree-sitter samples/Example"
import os
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import networkx as nx
import matplotlib.pyplot as plt


def search(name, file_name=None):
    result = None
    for node in graph.nodes:
        print(node['name'])
        # if node['name'] == name:
        #     result = node
        #     break
    return result


def add_nodes(node, connect_with):

    to_connect = connect_with

    if node.type == 'module':
        to_connect = current_ID
        add_script_node()
    elif node.type == 'class_definition':
        to_connect = current_ID
        add_class_node(node, connect_with)
    elif node.type == 'function_definition':
        to_connect = current_ID
        add_function_node(node, connect_with)

    for child in node.children:
        add_nodes(child, to_connect)


def common_parts(node, connect_with):
    global current_ID, content

    graph.add_node(current_ID)
    graph.nodes[current_ID]['name'] = content[node.children[1].start_byte : node.children[1].end_byte]
    graph.nodes[current_ID]['body'] = content[node.children[-1].start_byte : node.children[-1].end_byte]

    if connect_with is not None:
        graph.add_edge(current_ID, connect_with)
        attrs = nx.get_node_attributes(graph, 'type')
        graph[current_ID][connect_with]['connection_type'] = dict_with_weights['Encapsulation'] \
            if attrs[connect_with] == 'Script' else dict_with_weights['Ownership']


def add_script_node():
    global current_ID

    graph.add_node(current_ID)
    graph.nodes[current_ID]['name'] = file
    graph.nodes[current_ID]['type'] = 'Script'

    current_ID += 1


def add_class_node(node, connect_with):
    global current_ID, content

    common_parts(node, connect_with)
    graph.nodes[current_ID]['type'] = 'Class'

    current_ID += 1


def add_function_node(node, connect_with):
    global current_ID, content

    common_parts(node, connect_with)
    graph.nodes[current_ID]['parameters'] = []

    for child in node.children[2].children:
        if child.type == 'identifier':
            graph.nodes[current_ID]['parameters'].append(content[child.start_byte: child.end_byte])

    graph.nodes[current_ID]['type'] = 'Function'

    current_ID += 1


def add_import_edges(node, to_which_file):
    global content

    origin = search(to_which_file)
    imported_names_nodes = []

    for child in node.children:
        if child.type == 'dotted_name':
            imported_names_nodes.apppend(content[child.start_byte : child.end_byte])

    if len(imported_names_nodes) == 1:
        graph.add_edge(origin, search(imported_names_nodes[0]))
    else:
        from_which_file = search(imported_names_nodes[0])
        for i in range(1, len(imported_names_nodes)):
            graph.add_edge(origin, search(imported_names_nodes[i], file_name=from_which_file))


PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

repo = input("Path to repo: ")
# user friendly interface
repo += '/' if repo[-1] != '/' else ''
files = os.listdir(repo)

graph = nx.Graph()
current_ID = 1
content = ""

dict_with_weights = {'Ownership' : 1, 'Encapsulation' : 2}

for file in files:

    with open(repo + file, 'r') as f:
        content = f.read()

    tree = parser.parse(bytes(content, 'utf-8'))
    add_nodes(tree.root_node, None)

for data in graph.edges.data():
    print(*data)
for data in graph.nodes.data():
    print(*data)

nx.draw(graph, with_labels=True)
plt.show()