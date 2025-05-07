#!/usr/bin/env python3
"""
Script to analyze the Google Workflow Transformer and identify potential issues.

This script:
1. Loads and transforms a sample n8n workflow
2. Analyzes the transformation process
3. Identifies potential duplicate implementations or issues
4. Generates a report of the analysis

Usage:
    python analyze_workflow_transformer.py --input <input_file> [--output <output_file>] [--verbose]

Example:
    python analyze_workflow_transformer.py --input tests/fixtures/test_workflow.json --output analysis_report.json --verbose
"""

import argparse
import json
import logging
import os
import sys
import inspect
from typing import Dict, Any, List, Set, Tuple
import importlib
import pkgutil
from collections import defaultdict

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.providers.google.transformers.workflow_transformer import GoogleWorkflowTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_workflow(file_path: str) -> Dict[str, Any]:
    """
    Load a workflow JSON file.
    
    Args:
        file_path: Path to the workflow JSON file
        
    Returns:
        Dict[str, Any]: The workflow JSON data
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Handle the case where the workflow is nested in a 'workflow_json' field
        if 'workflow_json' in data:
            return data['workflow_json']
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading workflow: {str(e)}")
        sys.exit(1)


def save_report(report: Dict[str, Any], file_path: str) -> None:
    """
    Save an analysis report to a JSON file.
    
    Args:
        report: The analysis report
        file_path: Path to save the report
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Analysis report saved to: {file_path}")
    except Exception as e:
        logger.error(f"Error saving report: {str(e)}")
        sys.exit(1)


def find_similar_methods(transformer_class) -> List[Tuple[str, str, float]]:
    """
    Find methods in the transformer class that might be similar.
    
    Args:
        transformer_class: The transformer class to analyze
        
    Returns:
        List[Tuple[str, str, float]]: List of similar method pairs with similarity score
    """
    methods = []
    similar_pairs = []
    
    # Get all methods in the class
    for name, method in inspect.getmembers(transformer_class, predicate=inspect.isfunction):
        if not name.startswith('_') or name.startswith('_transform_'):
            methods.append((name, inspect.getsource(method)))
    
    # Compare method implementations for similarity
    for i, (name1, source1) in enumerate(methods):
        for name2, source2 in methods[i+1:]:
            # Simple similarity metric: ratio of common lines
            lines1 = set(source1.split('\n'))
            lines2 = set(source2.split('\n'))
            common_lines = lines1.intersection(lines2)
            
            if len(common_lines) > 5:  # At least 5 common lines
                similarity = len(common_lines) / min(len(lines1), len(lines2))
                if similarity > 0.3:  # At least 30% similar
                    similar_pairs.append((name1, name2, similarity))
    
    return similar_pairs


def find_potential_duplicates() -> List[Dict[str, Any]]:
    """
    Find potential duplicate implementations in the codebase.
    
    Returns:
        List[Dict[str, Any]]: List of potential duplicate implementations
    """
    duplicates = []
    
    # Check for duplicate transformer implementations
    transformers = []
    
    # Look for classes with 'transformer' in the name
    for module_info in pkgutil.iter_modules([os.path.join('src', 'providers')]):
        if module_info.ispkg:
            provider_path = os.path.join('src', 'providers', module_info.name)
            for submodule_info in pkgutil.iter_modules([provider_path]):
                if submodule_info.ispkg and submodule_info.name == 'transformers':
                    transformers_path = os.path.join(provider_path, 'transformers')
                    for transformer_module in pkgutil.iter_modules([transformers_path]):
                        if 'workflow' in transformer_module.name:
                            module_path = f"src.providers.{module_info.name}.transformers.{transformer_module.name}"
                            try:
                                module = importlib.import_module(module_path)
                                for name, obj in inspect.getmembers(module):
                                    if inspect.isclass(obj) and 'workflow' in name.lower():
                                        transformers.append((name, module_path, obj))
                            except ImportError as e:
                                logger.warning(f"Could not import module {module_path}: {str(e)}")
    
    # If we found multiple workflow transformers, they might be duplicates
    if len(transformers) > 1:
        duplicates.append({
            'type': 'multiple_transformers',
            'description': 'Multiple workflow transformer implementations found',
            'transformers': [{'name': name, 'module': module} for name, module, _ in transformers]
        })
    
    return duplicates


def analyze_node_transformations(transformer: GoogleWorkflowTransformer, workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze how nodes are transformed by the workflow transformer.
    
    Args:
        transformer: The workflow transformer instance
        workflow: The workflow to transform
        
    Returns:
        Dict[str, Any]: Analysis of node transformations
    """
    analysis = {
        'node_types': defaultdict(int),
        'transformed_nodes': defaultdict(int),
        'node_mapping': {},
        'potential_issues': []
    }
    
    # Count node types in the original workflow
    for node in workflow.get('nodes', []):
        node_type = node.get('type', '').lower()
        analysis['node_types'][node_type] += 1
    
    # Transform the workflow
    transformed = transformer.transform_workflow(workflow)
    
    # Count node types in the transformed workflow
    for node in transformed.get('nodes', []):
        node_type = node.get('type', '').lower()
        analysis['transformed_nodes'][node_type] += 1
    
    # Check for potential issues
    
    # 1. Check if any Google nodes weren't transformed
    for node in workflow.get('nodes', []):
        node_type = node.get('type', '').lower()
        node_type_base = node_type.replace('n8n-nodes-base.', '')
        
        if any(service in node_type_base for service in transformer.supported_nodes.keys()):
            # This should be transformed
            node_name = node.get('name', '')
            found = False
            
            for transformed_node in transformed.get('nodes', []):
                if transformed_node.get('name', '') == node_name:
                    found = True
                    break
            
            if not found:
                analysis['potential_issues'].append({
                    'type': 'untransformed_node',
                    'description': f"Google node not transformed: {node_name} ({node_type})"
                })
    
    # 2. Check for connections that might be lost
    original_connections = set()
    for source, targets in workflow.get('connections', {}).items():
        for target_list in targets.get('main', []):
            for target in target_list:
                original_connections.add((source, target['node']))
    
    transformed_connections = set()
    for source, targets in transformed.get('connections', {}).items():
        for target_list in targets.get('main', []):
            for target in target_list:
                transformed_connections.add((source, target['node']))
    
    # If we have fewer connections in the transformed workflow, some might be lost
    if len(transformed_connections) < len(original_connections):
        analysis['potential_issues'].append({
            'type': 'lost_connections',
            'description': f"Potential lost connections: {len(original_connections)} original, {len(transformed_connections)} transformed"
        })
    
    return analysis


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Analyze the Google Workflow Transformer and identify potential issues.')
    parser.add_argument('--input', '-i', required=True, help='Path to the input workflow JSON file')
    parser.add_argument('--output', '-o', help='Path to save the analysis report JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print verbose output')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Loading workflow from: {args.input}")
    workflow = load_workflow(args.input)
    
    logger.info("Analyzing workflow transformer...")
    
    # Initialize the transformer
    transformer = GoogleWorkflowTransformer()
    
    # Find similar methods in the transformer class
    logger.info("Looking for similar methods in the transformer class...")
    similar_methods = find_similar_methods(GoogleWorkflowTransformer)
    
    # Find potential duplicate implementations
    logger.info("Looking for potential duplicate implementations...")
    potential_duplicates = find_potential_duplicates()
    
    # Analyze node transformations
    logger.info("Analyzing node transformations...")
    node_analysis = analyze_node_transformations(transformer, workflow)
    
    # Compile the report
    report = {
        'similar_methods': [
            {
                'method1': method1,
                'method2': method2,
                'similarity': similarity
            }
            for method1, method2, similarity in similar_methods
        ],
        'potential_duplicates': potential_duplicates,
        'node_analysis': node_analysis
    }
    
    # Print the report
    if args.verbose:
        print("\n=== Analysis Report ===")
        print(f"Similar methods found: {len(similar_methods)}")
        for method1, method2, similarity in similar_methods:
            print(f"  - {method1} and {method2}: {similarity:.2f} similarity")
        
        print(f"\nPotential duplicate implementations: {len(potential_duplicates)}")
        for duplicate in potential_duplicates:
            print(f"  - {duplicate['description']}")
            if 'transformers' in duplicate:
                for transformer in duplicate['transformers']:
                    print(f"    - {transformer['name']} in {transformer['module']}")
        
        print("\nNode analysis:")
        print(f"  - Original node types: {dict(node_analysis['node_types'])}")
        print(f"  - Transformed node types: {dict(node_analysis['transformed_nodes'])}")
        print(f"  - Potential issues: {len(node_analysis['potential_issues'])}")
        for issue in node_analysis['potential_issues']:
            print(f"    - {issue['description']}")
        
        print("======================\n")
    
    # Save the report if an output file was specified
    if args.output:
        save_report(report, args.output)
    
    logger.info("Analysis complete!")


if __name__ == '__main__':
    main()
