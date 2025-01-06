import json  # For handling JSON data
import os  # For interacting with the operating system
from pprint import pprint  # For pretty-printing data structures
import networkx as nx  # For creating and manipulating networks
import tree_sitter_python as tspython  # Tree-sitter parser for Python
from PIL import Image  # For image processing
from fontTools.feaLib.builder import Builder  # For font building
from tree_sitter import Language, Parser  # For parsing
from os import listdir  # To list files in a directory
from os.path import isfile  # To check if a path is a file
from code2flow import code2flow  # To generate call graph

SUPPORTED_LANGAGUES = [".py"]  # Supported programming languages

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
    'Invoke': 'green'
}

# Edge styles for the graph
EDGES_STYLES = {
    'Encapsulation': 'bold',
    'Ownership': 'bold',
    'Import': 'dashed',
    'Invoke': 'bold'
}


class SemanticGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()  # Initialize a directed graph
        self.py_language = Language(tspython.language())  # Set up the Python language for parsing
        self.parser = Parser(self.py_language)  # Create a parser for the Python language

    def build_from_repos(self, path_to_repos, *args, **kwargs):
        # Build the graph from multiple repositories
        for file in listdir(path_to_repos):
            self.path_to_repo = file  # Set the current repository path
            self.build(*args, **kwargs)  # Build the graph

    def build_from_one(self, path_to_repo, *args, **kwargs):
        # Build the graph from a single repository
        self.path_to_repo = path_to_repo  # Set the repository path
        self.build(*args, **kwargs)  # Build the graph

    def build(self, gprint=False):
        # Build the semantic graph
        # os.system(f"code2flow {self.path_to_repo} -o __temp__.json -q")  # Generate a flow graph
        code2flow([self.path_to_repo], '__temp__.json', language="py", skip_parse_errors=True)
        self.files_to_parse = self.find_files(self.path_to_repo)  # Find files to parse
        self.build_encapsulation_and_ownership()  # Build encapsulation and ownership relationships
        self.build_import()  # Build import relationships
        self.build_invoke()  # Build invoke relationships
        if gprint:
            self.print_graph()  # Print the graph if requested

    def find_files(self, path):
        # Find all supported files in the given path
        files = []

        for file in listdir(path):
            current_instance = path + "\\" + file  # Construct the full file path

            if isfile(current_instance) and file[-3:] in SUPPORTED_LANGAGUES:
                files.append(current_instance)  # Add supported files to the list
            elif not isfile(current_instance):
                files.extend(self.find_files(current_instance))  # Recursively find files in subdirectories

        return files  # Return the list of found files

    def build_encapsulation_and_ownership(self):
        # Build encapsulation and ownership relationships from parsed files
        for file in self.files_to_parse:
            with open(file, 'r') as f:
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

            for x in captures:
                captures[x].sort(key=lambda x: x.start_byte)  # Sort captures by start byte

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

        path_to_object = [source.split(chr(92))[-1]]  # Get the source file name
        self.graph.add_node(path_to_object[0], nesting=counter, color=NODES_COLORS['script'])  # Add the script node

        # Construct the graph by traversing the definitions
        for x in definitions:
            if x['nesting'] == 0:  # Entering a new scope
                counter += 1  # Increase nesting level
                path_to_object.append(x['name'])  # Add the current definition name to the path

                # Add a node for the current definition
                self.graph.add_node(
                    "/".join(path_to_object), nesting=counter, color=NODES_COLORS[x['type']],
                    start_byte=x['start_byte'], end_byte=x['end_byte'],
                    start_point=x['start_point'], end_point=x['end_point'],
                )

                # Add an edge indicating ownership and encapsulation in the hierarchy
                if len(path_to_object) == 2:
                    self.graph.add_edge("/".join(path_to_object[:-1]), "/".join(path_to_object), type="Encapsulation")
                else:
                    self.graph.add_edge("/".join(path_to_object[:-1]), "/".join(path_to_object), type="Ownership")

            if x['nesting'] == 1:  # Exiting the current scope
                counter -= 1  # Decrease nesting level
                path_to_object.pop()  # Remove the last definition from the path

            if counter < 0:  # Sanity check for invalid nesting
                print("ERROR!")  # Print an error message if nesting is invalid

    def build_import(self):
        # Build import relationships from parsed files
        for file in self.files_to_parse:
            with open(file, 'r') as f:
                source_code = f.read()  # Read the source code from the file
            tree = self.parser.parse(bytes(source_code, 'utf-8'))  # Parse the source code
            repo_files = [file.split('\\')[-1] for file in self.files_to_parse]  # Get the list of repository files

            # Define queries to capture import statements
            query = self.py_language.query("""
            (import_statement
                name: (dotted_name) @file.name
            )

            (import_from_statement
                module_name: (dotted_name) @script.name
                name: (dotted_name) @imports
            )              
            """)

            query_aliased = self.py_language.query("""
            (import_statement
                name: (aliased_import) @file
            )

            (import_from_statement
                module_name: (dotted_name) @script.name
                name: (aliased_import) @imports
            )              
            """)

            query_wildcard = self.py_language.query("""
            (import_from_statement
                module_name: (dotted_name) @script.name
                (wildcard_import)
            )              
            """)

            # Execute the queries on the parsed tree
            captures = query.captures(tree.root_node)
            captures_aliased = query_aliased.captures(tree.root_node)
            captures_wildcard = query_wildcard.captures(tree.root_node)

            connect_with = file.split(chr(92))[-1]  # Get the current file name
            source_file = ''  # Initialize source file variable

            definitions = []  # Initialize definitions list

            # Process standard import statements
            if 'file.name' in captures.keys():
                self.for_import(captures, 'file.name', source_code, repo_files, connect_with)

            # Process aliased import statements
            if 'file' in captures_aliased.keys():
                captures_aliased['file'] = [file.children[0] for file in captures_aliased['file']]
                self.for_import(captures_aliased, 'file', source_code, repo_files, connect_with)

            # Process wildcard import statements
            if 'script.name' in captures_wildcard.keys():
                self.for_import(captures_wildcard, 'script.name', source_code, repo_files, connect_with,
                                for_wildcards=True)

            # Process imports from specific modules
            if 'script.name' in captures.keys():
                self.for_import_from(captures, 'imports', 'instance', source_code, definitions)
                self.for_import_from(captures, 'script.name', 'file', source_code, definitions)

            # Process imports from aliased modules
            if 'script.name' in captures_aliased.keys():
                captures_aliased['imports'] = [instance.children[0] for instance in captures_aliased['imports']]
                self.for_import_from(captures_aliased, 'imports', 'instance', source_code, definitions)
                self.for_import_from(captures_aliased, 'script.name', 'file', source_code, definitions)

            definitions.sort(key=lambda x: x['start_byte'])  # Sort definitions by start byte

            current_path = []  # Initialize current path for imports

            for el in definitions:
                # If el is a new file, set current_path to its name
                if el['type'] == 'file':
                    current_path = [el['name']]
                else:
                    if current_path[0] in repo_files:
                        # If el is an instance and the file is in the repo, update current_path
                        current_path.append(el['name'])
                        self.graph.add_edge(connect_with, '/'.join(current_path), type='Import')  # Add import edge
                        current_path.pop()  # Clear path for new instance

    def for_import(self, dct, key_name, source_code, repo_files, connect_with, for_wildcards=False):
        # Process import statements and add edges to the graph
        for file in dct[key_name]:
            # Extract the source file name from the import statement
            source_file = source_code[file.start_byte: file.end_byte].replace('.', '/').split('/')[-1]
            source_file += '.py'  # Append .py extension

            # If the source file is in the repository files, add an edge
            if source_file in repo_files:
                if not for_wildcards:
                    self.graph.add_edge(connect_with, source_file, type="Import")  # Add import edge
                else:
                    # For wildcard imports, connect to all out edges of the source file
                    for node in self.graph.out_edges(source_file):
                        self.graph.add_edge(connect_with, node[1], type="Import")  # Add import edge to neighbors

    def for_import_from(self, dct, key_name, type, source_code, definitions):
        # Process imports from specific modules and add to definitions
        for instance in dct[key_name]:
            # Define the name of a file or instance, and add .py if it's a file
            name = source_code[instance.start_byte: instance.end_byte]
            if type == 'file':
                name = name.replace('.', '/').split('/')[-1] + '.py'  # Format the file name

            # Append the definition to the definitions list
            definitions.append({
                'type': type,
                'name': name,
                'start_byte': instance.start_byte,
            })

    def parse_name(self, name):
        # Convert a name into a format suitable for the graph
        result = name.replace('.', '/')  # Replace dots with slashes
        result = result.replace('::', '.py/')  # Replace '::' with '.py/'
        result = result.replace('/(global)', '')  # Remove '(global)' from the path
        return result  # Return the formatted name

    def build_invoke(self, debugging=0):
        # Build invoke relationships from a temporary JSON file
        with open("__temp__.json", "r") as f:
            data = json.load(f)  # Load the JSON data

        nodes_to_nodes = dict()  # Dictionary to map node UIDs to graph node names

        # Map each node in the JSON data to its corresponding graph node name
        for x in data["graph"]["nodes"].values():
            node_name = x["name"]
            graph_node_name = self.parse_name(node_name)  # Parse the node name
            nodes_to_nodes[x["uid"]] = graph_node_name  # Store the mapping

        # Create edges in the graph based on the invoke relationships in the JSON data
        for x in data["graph"]["edges"]:
            node_1 = nodes_to_nodes[x["source"]]  # Get the source node name
            node_2 = nodes_to_nodes[x["target"]]  # Get the target node name

            # Add an edge if both nodes exist in the graph
            if node_1 in self.graph.nodes and node_2 in self.graph.nodes:
                self.graph.add_edge(node_1, node_2, type='Invoke')  # Add invoke edge

    def print_graph(self):
        # Extract node attributes (color, nesting) for visualization
        node_labels = nx.get_node_attributes(self.graph, 'nesting')  # Get nesting levels of nodes
        node_colors = nx.get_node_attributes(self.graph, 'color')  # Get colors of nodes
        edge_labels = nx.get_edge_attributes(self.graph, 'type')  # Get types of edges

        # Create a DOT (graph description) representation
        dot = nx.nx_pydot.to_pydot(self.graph)  # Convert the graph to a DOT format

        # Set node styles, colors, and labels
        for node in self.graph.nodes():
            pydot_node = dot.get_node(str(node))[0]  # Get the corresponding node in the DOT representation
            pydot_node.set_fillcolor(node_colors.get(node, 'white'))  # Set fill color, default to white
            pydot_node.set_style("filled")  # Make the node visually filled
            pydot_node.set_label(node.split("/")[-1])  # Label with the last path segment

        # Set edge labels and styles
        for edge in self.graph.edges():
            pydot_edge = dot.get_edge(str(edge[0]), str(edge[1]))[
                0]  # Get the corresponding edge in the DOT representation
            edge_type = edge_labels.get((edge[0], edge[1]), 'Unknown')  # Get the edge type

            pydot_edge.set_label(edge_type)  # Set edge label to indicate the type

            # Apply special styling for different edge types
            if edge_type == "Encapsulation":
                pydot_edge.set_style(EDGES_STYLES["Encapsulation"])  # Set style for encapsulation edges
                pydot_edge.set_color(EDGES_COLORS["Encapsulation"])  # Set color for encapsulation edges
            elif edge_type == "Ownership":
                pydot_edge.set_style(EDGES_STYLES["Ownership"])  # Set style for ownership edges
                pydot_edge.set_color(EDGES_COLORS["Ownership"])  # Set color for ownership edges
            elif edge_type == "Import":
                pydot_edge.set_style(EDGES_STYLES["Import"])  # Set style for import edges
                pydot_edge.set_color(EDGES_COLORS["Import"])  # Set color for import edges
            elif edge_type == "Invoke":
                pydot_edge.set_style(EDGES_STYLES["Invoke"])  # Set style for invoke edges
                pydot_edge.set_color(EDGES_COLORS["Invoke"])  # Set color for invoke edges
            else:
                pydot_edge.set_color("black")  # Default color for other edges

        # Save the resulting graph visualization as a PNG image
        png_name = f'{self.path_to_repo.split(chr(92))[-1]}.png'  # Generate PNG file name

        dot.write_png(png_name)  # Write the DOT representation to a PNG file

        # Optionally, display the generated graph image
        img = Image.open(png_name)  # Open the generated PNG image
        img.show()  # Display the image

    def print_nodes(self):
        # Print each node and its attributes in the graph
        for node in self.graph.nodes:
            print(node, '-------------------->', self.graph.nodes[node])  # Print node and its attributes


if __name__ == "__main__":
    # Main entry point for the script.
    builder = SemanticGraphBuilder()  # Create an instance of the SemanticGraphBuilder
    # Build the semantic graph from a user-provided repository path and display the graph
    builder.build_from_one(input(), gprint=True)  # Call the build method with user input and enable graph printing
