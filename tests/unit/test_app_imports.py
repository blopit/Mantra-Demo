"""
Unit tests for verifying imports in app.py
"""

import pytest
import importlib
import ast
from pathlib import Path

def get_imports_from_file(file_path: str) -> list:
    """Extract all imports from a Python file."""
    with open(file_path, 'r') as file:
        tree = ast.parse(file.read())
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.append(name.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module if node.module else ''
            for name in node.names:
                full_name = f"{module}.{name.name}" if module else name.name
                imports.append(full_name)
    return imports

def test_app_imports():
    """Test that all imports in app.py are valid."""
    app_path = Path('app.py')
    assert app_path.exists(), "app.py not found"
    
    imports = get_imports_from_file('app.py')
    
    for import_path in imports:
        try:
            if '.' in import_path:
                # For from-imports, try importing the specific item
                module_path, item = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                assert hasattr(module, item), f"Cannot import {item} from {module_path}"
            else:
                # For direct imports, just try importing the module
                importlib.import_module(import_path)
        except ImportError as e:
            pytest.fail(f"Failed to import {import_path}: {str(e)}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing {import_path}: {str(e)}") 