import json  # For handling JSON data
import os  # For interacting with the operating system
from pprint import pprint  # For pretty-printing data structures
import networkx as nx  # For creating and manipulating networks
import tree_sitter_python as tspython  # Tree-sitter parser for Python
from PIL import Image  # For image processing
from fontTools.feaLib.builder import Builder  # For font building
from tree_sitter import Language, Parser  # For parsing
from os import listdir  # To list files in a directory
from os.path import isfile, exists  # To check if a path is a file
from code2flow import code2flow  # To generate call graph

SUPPORTED_LANGUAGES = [".py"]  # Supported programming languages

# Node colors for the graph
NODES_COLORS = {
    'function': 'orange',
    'class': 'blue',
    'script': 'green'
}

# Edge colors for the graph
EDGES_COLORS = {
    'Encapsulation': 'blue',
    'Ownership': 'gold',
    'Import': 'red',
    'Invoke': 'green',
    'Class Hierarchy': 'pink'
}

# Edge styles for the graph
EDGES_STYLES = {
    'Encapsulation': 'bold',
    'Ownership': 'bold',
    'Import': 'dashed',
    'Invoke': 'bold',
    'Class Hierarchy': 'dashed'
}


class SemanticGraphBuilder:
    def __init__(self):
        self.graph = nx.MultiDiGraph()  # Initialize a directed graph
        self.py_language = Language(tspython.language())  # Set up the Python language for parsing
        self.parser = Parser(self.py_language)  # Create a parser for the Python language

    def build_from_repos(self, path_to_repos, save_folder, *args, **kwargs):
        # Build the graph from multiple repositories
        folders = [f for f in os.listdir(path_to_repos) if os.path.isdir(os.path.join(path_to_repos, f))]
        for dir in folders:
            self.path_to_repo = path_to_repos + "\\" + dir  # Set the current repository path
            self.build(save_folder, *args, **kwargs)  # Build the graph

    def build_from_one(self, path_to_repo, save_folder, *args, **kwargs):
        # Build the graph from a single repository
        self.path_to_repo = path_to_repo  # Set the repository path
        self.build(save_folder, *args, **kwargs)  # Build the graph

    def define_files_for_check(self):
        dct = {}
        for file in self.files_to_parse:
            dct[file] = 0
        return dct

    def build(self, save_folder, gsave=False, gprint=False):
        # Build the semantic graph
        # os.system(f"code2flow {self.path_to_repo} -o __temp__.json -q")  # Generate a flow graph
        code2flow([self.path_to_repo], '__temp__.json', language="py", skip_parse_errors=True)
        self.files_to_parse = self.find_files(self.path_to_repo)
        self.already_checked = self.define_files_for_check()  # Find files to parse
        self.build_encapsulation_and_ownership()  # Build encapsulation and ownership relationships
        self.build_import()  # Build import relationships
        self.build_invoke()  # Build invoke relationships
        self.build_class_hierarchy()  # Build class hierarchy relationships
        self.delete_duplicate_edges()
        if gsave:
            self.save_graph(save_folder)
        if gprint:
            self.print_graph()  # Print the graph if requested
        self.end()

    def find_files(self, path):
        # Find all supported files in the given path
        files = []

        for file in listdir(path):
            current_instance = path + "\\" + file  # Construct the full file path

            if isfile(current_instance) and file[-3:] in SUPPORTED_LANGUAGES:
                files.append(current_instance)  # Add supported files to the list
            elif not isfile(current_instance):
                files.extend(self.find_files(current_instance))  # Recursively find files in subdirectories

        return files  # Return the list of found files

    def build_encapsulation_and_ownership(self):
        # Build encapsulation and ownership relationships from parsed files
        for file in self.files_to_parse:
            with open(file, 'r', errors='ignore') as f:
                source_code = f.read()  # Read the source code from the file
            tree = self.parser.parse(bytes(source_code, 'utf-8'))  # Parse the source code

            # Define a query to capture class and function definitions
            query = self.py_language.query("""
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

            captures = query.captures(tree.root_node)  # Execute the query on the parsed tree

            for el in captures:
                captures[el].sort(key=lambda x: x.start_byte)  # Sort captures by start byte

            definitions = []  # Initialize a list to hold definitions

            # Find function and class names and add them to definitions
            definitions = self.find_function_names(captures, definitions)
            definitions = self.find_class_names(captures, definitions)

            definitions.sort(key=lambda x: x['for_sorting'])  # Sort definitions for processing

            self.construct_graph(definitions, file)  # Construct the graph with the definitions

    def find_function_names(self, captures, definitions):
        # Find function names from captures and add them to definitions
        if "func.name" in captures.keys():
            for i in range(len(captures["func.name"])):
                definitions.append(
                    {
                        'name': captures["func.name"][i].text.decode('utf-8'),  # Function name
                        'start_byte': captures["func.body"][i].start_byte,  # Start byte of the function body
                        'nesting': 0,  # Nesting level
                        'type': 'function',  # Type of definition
                        'end_byte': captures["func.body"][i].end_byte,  # End byte of the function body
                        'start_point': captures["func.body"][i].start_point,  # Start point of the function body
                        'end_point': captures["func.body"][i].end_point,  # End point of the function body
                        'for_sorting': [captures["func.body"][i].start_byte, 0]  # For sorting purposes
                    }
                )
                definitions.append(
                    {
                        'name': captures["func.name"][i].text.decode('utf-8'),  # Function name
                        'end_byte': captures["func.body"][i].end_byte,  # End byte of the function body
                        'nesting': 1,  # Nesting level
                        'type': "function",  # Type of definition
                        'for_sorting': [captures["func.body"][i].end_byte, 1]  # For sorting purposes
                    }
                )
        return definitions  # Return the updated definitions list

    def find_class_names(self, captures, definitions):
        # Find class names from captures and add them to definitions
        if "class.name" in captures.keys():
            for i in range(len(captures["class.name"])):
                definitions.append(
                    {
                        'name': captures["class.name"][i].text.decode('utf-8'),  # Class name
                        'start_byte': captures["class.body"][i].start_byte,  # Start byte of the class body
                        'nesting': 0,  # Nesting level
                        'type': 'class',  # Type of definition
                        'end_byte': captures["class.body"][i].end_byte,  # End byte of the class body
                        'start_point': captures["class.body"][i].start_point,  # Start point of the class body
                        'end_point': captures["class.body"][i].end_point,  # End point of the class body
                        'for_sorting': [captures["class.body"][i].start_byte, 0]  # For sorting purposes
                    }
                )
                definitions.append(
                    {
                        'name': captures["class.name"][i].text.decode('utf-8'),  # Class name
                        'end_byte': captures["class.body"][i].end_byte,  # End byte of the class body
                        'nesting': 1,  # Nesting level
                        'type': "class",  # Type of definition
                        'for_sorting': [captures["class.body"][i].end_byte, 1]  # For sorting purposes
                    }
                )
        return definitions  # Return the updated definitions list

    def construct_graph(self, definitions, source):
        # Construct the semantic graph from definitions
        counter = 0  # Initialize nesting counter

        path_to_object = [source.replace('\\', '/').replace(':', '.')]  # Get the source file name
        self.graph.add_node(path_to_object[0], nesting=counter, color=NODES_COLORS['script'])  # Add the script node

        # Construct the graph by traversing the definitions
        for object in definitions:
            if object['nesting'] == 0:  # Entering a new scope
                counter += 1  # Increase nesting level
                path_to_object.append(object['name'])  # Add the current definition name to the path

                # Add a node for the current definition
                self.graph.add_node(
                    "/".join(path_to_object), nesting=counter, color=NODES_COLORS[object['type']],
                    start_byte=object['start_byte'], end_byte=object['end_byte'],
                    start_point=object['start_point'], end_point=object['end_point'],
                    # body ????
                )

                # Add an edge indicating ownership and encapsulation in the hierarchy
                if len(path_to_object) == 2:
                    self.graph.add_edge("/".join(path_to_object[:-1]), "/".join(path_to_object), type="Encapsulation")
                else:
                    self.graph.add_edge("/".join(path_to_object[:-1]), "/".join(path_to_object), type="Ownership")

            if object['nesting'] == 1:  # Exiting the current scope
                counter -= 1  # Decrease nesting level
                path_to_object.pop()  # Remove the last definition from the path

            if counter < 0:  # Sanity check for invalid nesting
                print("ERROR!")  # Print an error message if nesting is invalid

    def build_import(self):
        for file in self.files_to_parse:
            # Set the status of the current file as 1(in progress)
            self.already_checked[file] = 1
            # Construnct import edges for the file
            self.construct_import_for_file(file)

    def construct_import_for_file(self, file):
        # Initialize array to collect all imports of a current file and imports of the "imported" files 
        # (nested imports)
        instances_to_connect = []

        # Read the code and then parse it
        with open(file, 'r', errors='ignore') as f:
            source_code = f.read()

        tree = self.parser.parse(bytes(source_code, 'utf-8'))

        # Initialize the list of all files with rewritten names
        repo_files = [file.replace("\\", '/').replace(':', '.') for file in
                      self.files_to_parse]

        # Define queries: 
        # query - standart "import" or "from smt import smt" 
        query = self.py_language.query("""
        (import_statement
            name: (dotted_name) @file.name
        )

        (import_from_statement
            module_name: (dotted_name) @script.name
            name: (dotted_name) @imports
        )              
        """)

        # query_aliased - "import smth1 as smth2" or "from smth1 import smth2 as smth3" 
        query_aliased = self.py_language.query("""
        (import_statement
            name: (aliased_import) @file
        )

        (import_from_statement
            module_name: (dotted_name) @script.name
            name: (aliased_import) @imports
        )              
        """)

        # query_wildcard - "from smth import *"
        query_wildcard = self.py_language.query("""
        (import_from_statement
            module_name: (dotted_name) @script.name
            (wildcard_import)
        )              
        """)

        # query_with_dots - "from ...smth import smt"
        query_with_dots = self.py_language.query("""
        (import_from_statement
            module_name: (relative_import) @script.name
            name: (dotted_name) @imports
        )              
        """)

        # Execute the queries on the parsed tree
        captures = query.captures(tree.root_node)
        captures_aliased = query_aliased.captures(tree.root_node)
        captures_wildcard = query_wildcard.captures(tree.root_node)
        captures_with_dots = query_with_dots.captures(tree.root_node)

        # Define a name of the current file
        connect_with = file.replace('\\', '/').replace(':', '.')

        definitions = []

        # For each type of captures build import edges and extened array of imports
        if 'file.name' in captures.keys():
            instances_to_connect += self.for_import(captures, 'file.name',
                                                    source_code, repo_files, connect_with)

        if 'file' in captures_aliased.keys():
            captures_aliased['file'] = [file.children[0] for file in captures_aliased['file']]
            instances_to_connect += self.for_import(captures_aliased, 'file',
                                                    source_code, repo_files, connect_with)

        if 'script.name' in captures_wildcard.keys():
            instances_to_connect += self.for_import(captures_wildcard, 'script.name',
                                                    source_code, repo_files, connect_with, for_wildcards=True)

        if 'script.name' in captures.keys():
            instances_to_connect += self.for_import_from(captures,
                                                         'imports', 'instance', source_code, definitions, file)
            instances_to_connect += self.for_import_from(captures,
                                                         'script.name', 'file', source_code, definitions, file)

        if 'script.name' in captures_aliased.keys():
            captures_aliased['imports'] = [instance.children[0] for instance in captures_aliased['imports']]
            instances_to_connect += self.for_import_from(captures_aliased,
                                                         'imports', 'instance', source_code, definitions, file)
            instances_to_connect += self.for_import_from(captures_aliased,
                                                         'script.name', 'file', source_code, definitions, file)

        if 'script.name' in captures_with_dots.keys():
            instances_to_connect += self.for_import_from(captures_with_dots,
                                                         'imports', 'instance', source_code, definitions, file)
            instances_to_connect += self.for_import_from(captures_with_dots,
                                                         'script.name', 'file', source_code, definitions, file)

        definitions.sort(key=lambda x: x['start_byte'])  # Sort definitions by start byte

        current_path = []  # Initialize current path for imports

        # Define file names and objects form these files
        for object in definitions:
            # If object's type - file, current_path should contain only its name
            if object['type'] == 'file':
                current_path = [object['name']]
            else:
                # Check if file is from repo
                if current_path[0] in repo_files:
                    # If object's type is instance, concatenate the the current_path
                    current_path.append(object['name'])
                    # Find the appropriate file from which the instance is imported (nested imports) and add
                    # an edge
                    self.additional_imports(object['name'], connect_with,
                                            instances_to_connect, namespace=current_path[0])
                    # Delete the instance name
                    current_path.pop()

        # Set file status as 2 (already checked)
        self.already_checked[file] = 2

        # Add edges from the nested imports
        for object in instances_to_connect:
            self.graph.add_edge(connect_with, object, type='Import')

        # Pass the list of current file imports for the next file, if the func was called recursively
        return instances_to_connect

    def define_file_path(self, name, current_path):
        # Define a path to folder in which file is located (file means "file to which we import)
        folder = '\\'.join(current_path.split('\\')[:-1]).replace('.', ':')

        # If the file name contain dots, go tho the upper folders from the current one
        while len(name) != 0 and name[0] == '.':
            # Delete one dot form the name
            name = name[1:]
            # Go upper on one level from the folder
            folder = '\\'.join(folder.split('\\')[:-1])

        # Check if in the file name exsists on the current folder level
        if exists(folder + '\\' + name + '.py'):
            # If it exsists, connect it
            return folder.replace('\\', '/').replace(':', '.') + '/' + name.replace('\\', '/') + '.py'

        # Check if the file name exsists on a higher level
        if exists('\\'.join(folder.split('\\')[:-1]) + '\\' + name + '.py'):
            return '/'.join(folder.split('\\')[:-1]).replace(':', '.') + '/' + name.replace('\\', '/') + '.py'

        # In other case it should be located at the highest level
        return self.path_to_repo.replace('\\', '/').replace(':', '.') + '/' + name.replace('\\', '/') + '.py'

    def for_import(self, dct, key_name, source_code, repo_files, connect_with, for_wildcards=False):
        # Process import statements and add edges to the graph
        for_future_connection = []  # Initialize the list of imports

        for file in dct[key_name]:
            # Extract the source file name from the import statement
            name = source_code[file.start_byte: file.end_byte]
            source_file = self.define_file_path(name.replace('.', '\\'),
                                                connect_with)

            # If the source file is in the repository files, add an edge
            if source_file in repo_files:
                # Define a name of the file
                file_name = source_file.replace('.', ':').replace('/', chr(92))[:-3] + '.py'
                # Check its status
                if self.already_checked[file_name] == 0:
                    # If the file haven't been checked, set its status to 1(in progress) and check it
                    self.already_checked[file_name] = 1
                    for_future_connection += self.construct_import_for_file(file_name)
                # If its status is "in progress" rise an error of circular import
                elif self.already_checked[file_name] == 1:
                    # Define the last two names of the circle
                    raise RuntimeError(str(connect_with) + " " + str(file_name))

                # If file is imported with wildcard, connect all its instances with the current file
                if not for_wildcards:
                    self.graph.add_edge(connect_with, source_file, type="Import")
                    for_future_connection.append(source_file)
                else:
                    # For wildcard imports, connect to all out edges of the source file
                    for node in self.graph.out_edges(source_file):
                        self.graph.add_edge(connect_with, node[1], type="Import")
                        for_future_connection.append(node[1])
                self.additional_imports(source_file, connect_with, [])

        return for_future_connection

    def for_import_from(self, dct, key_name, type, source_code, definitions, path):
        for_future_connection = []
        # Process imports from specific modules and add to definitions
        for instance in dct[key_name]:
            # Define the name of a file or instance, and add .py if it's a file
            name = source_code[instance.start_byte: instance.end_byte]

            if type == 'file':
                # Define the dots count before the file name and delete them for the appropriate work
                prefix_dots_count = 0
                while len(name) != 0 and name[0] == '.':
                    prefix_dots_count += 1
                    name = name[1:]

                # Define the path to the file and its "normal name" in the system
                name = self.define_file_path('.' * (prefix_dots_count - 1) + (name.replace('.', '\\')), path)
                file_name = name.replace('.', ':').replace('/', chr(92))[:-3] + '.py'
                # Check its status and rise an error in the case of circular import
                if file_name in self.files_to_parse and self.already_checked[file_name] == 0:
                    self.already_checked[file_name] = 1
                    for_future_connection += self.construct_import_for_file(file_name)
                elif file_name in self.files_to_parse and self.already_checked[file_name] == 1:
                    # If the file does not import itself rise an error
                    if path != file_name: raise RecursionError(str(path) + " " + str(file_name))

            # Append the definition to the definitions list
            definitions.append({
                'type': type,
                'name': name,
                'start_byte': instance.start_byte,
            })

        return for_future_connection

    def additional_imports(self, name, connect_with, to_connect, namespace=None):
        # If name is file connect all its imports with the current file
        if name.split('/')[-1][-3:] == '.py':
            # Define all "Import" edges and reconnect them
            for edge in self.graph.out_edges(name, data=True):
                if edge[2]['type'] == 'Import':
                    self.graph.add_edge(connect_with, edge[1], type='Import')
        else:
            # Initialize import and encapsuled edges
            imported = []
            encapsuled = []
            for edge in self.graph.out_edges(namespace, data=True):
                if edge[2]['type'] == 'Import':
                    imported.append(edge[1])
                elif edge[2]['type'] == 'Encapsulation':
                    encapsuled.append(edge[1])
            # Check if the name exsists in the file
            if namespace + '/' + name in encapsuled:
                self.graph.add_edge(connect_with, namespace + '/' + name, type="Import")
                to_connect.append(namespace + '/' + name)
            else:
                # If the name is not in encapsuled find a file in which it is encapsuled
                for imp in imported:
                    # Check if it is imported or encapsuled
                    if name == imp.split('/')[-1]:
                        self.graph.add_edge(connect_with, imp, type="Import")
                    elif imp[-3:] == '.py':
                        self.additional_imports(name, connect_with, to_connect, namespace=imp)

    def parse_name(self, name):
        result = []  # List to store matching node names
        # Format the name for the graph
        partial_name = name.replace('.', '/')  # Replace dots with slashes
        partial_name = partial_name.replace('::', '.py/')  # Replace '::' with '.py/'
        partial_name = partial_name.replace('/(global)', '')  # Remove '(global)'

        for element in self.graph.nodes:
            if element.endswith("/" + partial_name):  # Check if node matches the formatted name
                result.append(element)  # Add matching node to the result

        return result  # Return the list of matching nodes

    def find_file_in_path(self, full_name):
        path = full_name.split("/")  # Split the full name into components
        for i in range(len(path) - 1, -1, -1):
            if "." in path[i]:  # Check for a file component
                return "/".join(path[:i + 1])  # Return the path up to the file

    def build_invoke(self, debugging=0):
        # Build invoke relationships from a temporary JSON file
        with open("__temp__.json", "r", errors='ignore') as f:
            data = json.load(f)  # Load the JSON data

        nodes_to_nodes = dict()  # Dictionary to map node UIDs to graph node names

        if debugging:
            pprint(data)  # Print the loaded JSON data if debugging is enabled

        # Map each node in the JSON data to its corresponding graph node name
        for node in data["graph"]["nodes"].values():
            node_name = node["name"]  # Get the node name from JSON
            graph_node_name = self.parse_name(node_name)  # Parse the node name
            nodes_to_nodes[node["uid"]] = graph_node_name  # Store the mapping

        if debugging:
            pprint(nodes_to_nodes)  # Print the mapping of UIDs to node names if debugging is enabled

        # Create edges in the graph based on the invoke relationships in the JSON data
        for node in data["graph"]["edges"]:
            node_1_names = nodes_to_nodes[node["source"]]  # Get the source node name(s)
            node_2_names = nodes_to_nodes[node["target"]]  # Get the target node name(s)

            if debugging:
                pprint(node_1_names)  # Print source node names if debugging
                pprint(node_2_names)  # Print target node names if debugging
                pprint(self.graph.nodes)  # Print current graph nodes if debugging
                print("------------------------------------------------------")

            # Add an edge if both nodes exist in the graph
            for node_1 in node_1_names:
                for node_2 in node_2_names:
                    if debugging:
                        pprint(self.find_file_in_path(node_1))  # Print the file path for node_1 if debugging
                        pprint(nx.ancestors(self.graph, node_2))  # Print ancestors of node_2 if debugging
                        print("<<<------------------------------------------------>>>")
                    # Check if node_1 is an ancestor of node_2
                    if self.find_file_in_path(node_1) in nx.ancestors(self.graph, node_2):
                        # Add an edge if both nodes exist in the graph
                        if node_1 in self.graph.nodes and node_2 in self.graph.nodes:
                            self.graph.add_edge(node_1, node_2, type='Invoke')  # Add invoke edge

    def build_class_hierarchy(self):
        for file in self.files_to_parse:
            with open(file, 'r', errors='ignore') as f:
                source_code = f.read()  # Read the source code from the file
            tree = self.parser.parse(bytes(source_code, 'utf-8'))  # Parse the source code

            # Define a query to capture class and function definitions
            query = self.py_language.query("""
            (class_definition
                name: (identifier) @class.name
                superclasses: (argument_list (identifier) @class.parents)?
                body: (block) @class.body
            )
            """)

            captures = query.captures(tree.root_node)  # Execute the query on the parsed tree

            for el in captures:
                captures[el].sort(key=lambda x: x.start_point)  # Sort captures by start byte

            # if there are child classes in current file, extract their parents
            if "class.parents" in captures.keys():
                name_body = dict()  # dict to store the parameters of body of each class

                for i in range(len(captures["class.name"])):
                    name_body[captures["class.name"][i]] = captures["class.body"][i]

                # use Two pointers technique to break up the list of all parent classes and
                # match parent class with child class
                i, j = 0, 0

                while j < len(captures["class.parents"]):
                    if captures["class.name"][i].start_byte < captures["class.parents"][j].start_byte \
                            < name_body[captures["class.name"][i]].start_byte:
                        child_name = captures["class.name"][i].text.decode('utf-8')
                        parent_name = captures["class.parents"][j].text.decode('utf-8')

                        child_path = f"{file.replace(':', '.')}/{child_name}".replace('\\', '/')
                        parent_path = self.parse_name(parent_name)
                        if parent_path:
                            # Add edges to represent class hierarchy
                            self.graph.add_edge(child_path, parent_path[-1], type='Class Hierarchy')

                        j += 1
                    else:
                        i += 1

    def delete_duplicate_edges(self):
        # Create a list of unique edges by converting them to a set
        new_edges = list(set([(a, b, tuple(c.values())) for a, b, c in list(self.graph.edges(data=True))]))

        # Convert the unique edges back to the required format with a dictionary
        new_edges = [(a, b, dict(zip(["type"], c))) for a, b, c in new_edges]

        # Clear all existing edges from the graph
        self.graph.clear_edges()

        # Add the unique edges back to the graph
        self.graph.add_edges_from(new_edges)

    def print_graph(self):
        # Extract node attributes (color, nesting) for visualization
        node_colors = nx.get_node_attributes(self.graph, 'color')  # Get colors of nodes

        # Create a DOT (graph description) representation
        dot = nx.nx_pydot.to_pydot(self.graph)  # Convert the graph to a DOT format

        # Set node styles, colors, and labels
        for node in self.graph.nodes():
            pydot_node = dot.get_node(str(node))[0]  # Get the corresponding node in the DOT representation
            pydot_node.set_fillcolor(node_colors.get(node, 'white'))  # Set fill color, default to white
            pydot_node.set_style("filled")  # Make the node visually filled
            pydot_node.set_label(node.split("/")[-1])  # Label with the last path segment

        # Set edge labels and styles
        for edge in self.graph.edges(keys=True):
            source, target, key = edge  # Extract source, target, and key for MultiDiGraph edges
            edge_type = self.graph.edges[source, target, key].get('type', 'Unknown')  # Get the edge type
            edge_color = EDGES_COLORS.get(edge_type, "black")  # Get the edge color based on the type
            edge_style = EDGES_STYLES.get(edge_type, "solid")  # Get the edge style based on the type

            # Get the corresponding edge in the DOT representation
            pydot_edge = dot.get_edge(str(source), str(target))[key]

            # Apply attributes to the edge
            pydot_edge.set_label(edge_type)  # Set edge label to indicate the type
            pydot_edge.set_style(edge_style)  # Set style for the edge
            pydot_edge.set_color(edge_color)  # Set color for the edge

        # Save the resulting graph visualization as a PNG image
        png_name = f'{self.path_to_repo.split(chr(92))[-1]}.png'  # Generate PNG file name
        dot.write_png(png_name)  # Write the DOT representation to a PNG file
        #
        # Optionally, display the generated graph image
        img = Image.open(png_name)  # Open the generated PNG image
        img.show()  # Display the image

    def save_graph(self, save_folder):
        name = f'{self.path_to_repo.split(chr(92))[-1]}.gml'
        nx.write_gml(self.graph, save_folder + "//" + name)

    def print_nodes(self):
        # Print each node and its attributes in the graph
        for node in self.graph.nodes:
            print(node, '-------------------->', self.graph.nodes[node])  # Print node and its attributes

    def end(self):
        os.remove("__temp__.json")


if __name__ == "__main__":
    # Main entry point for the script.
    builder = SemanticGraphBuilder()  # Create an instance of the SemanticGraphBuilder
    # Build the semantic graph from a user-provided repository path and display the graph
    builder.build_from_one(input("input path to your repo"), "graphs", gsave=False,
                           gprint=True)  # Call the build method with user input and enable graph printing
