from pprint import pprint
import networkx as nx
import tree_sitter_python as tspython
from PIL import Image
from tree_sitter import Language, Parser
from os import listdir
from os.path import isfile


PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

with open('C:\\Users\\danil\\Documents\\problems\\Semantic graph tests\\SemanticGraphParser\\Tree-sitter-samples\\Example\\Test3.py', 'r') as f:
    source_code = f.read()

tree = parser.parse(bytes(source_code, 'utf-8'))

query = PY_LANGUAGE.query("""
(import_statement
    name: (aliased_import) @file.name
)

(import_from_statement
    module_name: (dotted_name) @script.name
    name: (aliased_import) @imports
)              
""")

query2 = PY_LANGUAGE.query("""
    (import_statement
        name: (dotted_name) @file.name
    )

    (import_from_statement
        module_name: (dotted_name) @script.name
        name: (dotted_name) @imports
)              
""")

query3 = PY_LANGUAGE.query("""
    (import_from_statement
        module_name: (dotted_name) @script.name
        (wildcard_import)
    )              
    """)

captures = query.captures(tree.root_node)
captures2 = query2.captures(tree.root_node)
cap3 = query3.captures(tree.root_node)
pprint(cap3)

for cap in captures['file.name']:
    name = source_code[cap.children[0].start_byte : cap.children[0].end_byte]
    print(name)

for cap in captures['imports']:
    func_name = source_code[cap.children[0].start_byte : cap.children[0].end_byte]
    print(func_name)
    