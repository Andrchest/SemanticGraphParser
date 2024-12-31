import ast
import os

def find_classes_in_file(file_path):
    """
    Parse a Python file and extract class definitions, their parents, and line numbers.
    """
    with open(file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            parent_classes = [base.id for base in node.bases if isinstance(base, ast.Name)]
            classes[node.name] = {
                "parents": parent_classes,
                "line_number": node.lineno,
                "file_path": file_path,
            }
    return classes


def analyze_repository(repo_path):
    """
    Analyze all Python files in a repository and build a mapping of classes.
    """
    all_classes = {}

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                classes_in_file = find_classes_in_file(file_path)
                all_classes.update(classes_in_file)

    return all_classes


def find_parent_details(class_name, all_classes):
    """
    Find the details of the parent class for a given class.
    """
    if class_name not in all_classes:
        return None, None, None

    class_info = all_classes[class_name]
    if not class_info["parents"]:
        return None, None, None  # No parent class

    # Assume single inheritance for simplicity
    parent_class = class_info["parents"][0]
    if parent_class in all_classes:
        parent_info = all_classes[parent_class]
        return parent_class, parent_info["file_path"], parent_info["line_number"]

    return parent_class, "Unknown (not found in repo)", None


# Specify your repository path
repo_path = "/path/to/your/repository"

# Analyze the repository
all_classes = analyze_repository(repo_path)

# Query parent details for a specific class
queried_class = "ClassName"
parent_class, file_name, line_number = find_parent_details(queried_class, all_classes)

if parent_class:
    print(f"Parent Class: {parent_class}")
    print(f"Defined in: {file_name}")
    print(f"Line number: {line_number}")
else:
    print(f"No parent class found for {queried_class}, or it is a base object class.")
