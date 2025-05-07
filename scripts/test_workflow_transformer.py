#!/usr/bin/env python3
"""
Script to test the Google Workflow Transformer with n8n workflow JSON files.

This script takes an n8n workflow JSON file as input, transforms it using the
GoogleWorkflowTransformer, and outputs the transformed workflow to a file.

Usage:
    python test_workflow_transformer.py --input <input_file> --output <output_file> [--verbose]

Example:
    python test_workflow_transformer.py --input tests/fixtures/test_workflow.json --output transformed_workflow.json --verbose
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, Any, Optional

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


def save_workflow(workflow: Dict[str, Any], file_path: str) -> None:
    """
    Save a workflow JSON file.
    
    Args:
        workflow: The workflow JSON data
        file_path: Path to save the workflow JSON file
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(workflow, f, indent=2)
        logger.info(f"Transformed workflow saved to: {file_path}")
    except Exception as e:
        logger.error(f"Error saving workflow: {str(e)}")
        sys.exit(1)


def print_workflow_summary(workflow: Dict[str, Any]) -> None:
    """
    Print a summary of the workflow.
    
    Args:
        workflow: The workflow JSON data
    """
    print("\n=== Workflow Summary ===")
    print(f"Name: {workflow.get('name', 'Unnamed Workflow')}")
    
    nodes = workflow.get('nodes', [])
    print(f"Nodes: {len(nodes)}")
    
    # Group nodes by type
    node_types = {}
    for node in nodes:
        node_type = node.get('type', 'unknown')
        if node_type not in node_types:
            node_types[node_type] = 0
        node_types[node_type] += 1
    
    print("\nNode Types:")
    for node_type, count in node_types.items():
        print(f"  - {node_type}: {count}")
    
    connections = workflow.get('connections', {})
    print(f"\nConnections: {len(connections)}")
    print("======================\n")


def transform_workflow(workflow: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """
    Transform a workflow using the GoogleWorkflowTransformer.
    
    Args:
        workflow: The workflow JSON data
        verbose: Whether to print verbose output
        
    Returns:
        Dict[str, Any]: The transformed workflow
    """
    try:
        transformer = GoogleWorkflowTransformer()
        transformed = transformer.transform_workflow(workflow)
        
        if verbose:
            print_workflow_summary(transformed)
            
        return transformed
    except Exception as e:
        logger.error(f"Error transforming workflow: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Test the Google Workflow Transformer with n8n workflow JSON files.')
    parser.add_argument('--input', '-i', required=True, help='Path to the input workflow JSON file')
    parser.add_argument('--output', '-o', required=True, help='Path to save the transformed workflow JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print verbose output')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Loading workflow from: {args.input}")
    workflow = load_workflow(args.input)
    
    logger.info("Transforming workflow...")
    transformed = transform_workflow(workflow, args.verbose)
    
    logger.info(f"Saving transformed workflow to: {args.output}")
    save_workflow(transformed, args.output)
    
    logger.info("Transformation complete!")


if __name__ == '__main__':
    main()
