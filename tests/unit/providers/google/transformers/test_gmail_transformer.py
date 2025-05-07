"""Tests for Gmail node transformer"""

import pytest
from src.providers.google.transformers.gmail_transformer import GmailTransformer

def test_transform_get_all_node():
    """Test transforming a Gmail 'getAll' node"""
    # Test input node
    node = {
        'id': 'test123',
        'name': 'Gmail Test',
        'type': 'n8n-nodes-base.gmail',
        'position': [100, 200],
        'parameters': {
            'operation': 'getAll',
            'returnAll': True,
            'filters': {
                'q': 'after:2024/01/01'
            }
        }
    }
    
    # Transform node
    transformed = GmailTransformer.transform_node(node, {})
    
    # Should return error handler, token node and operation node
    assert len(transformed) == 3
    
    # Check error handler node
    error_handler = transformed[0]
    assert error_handler['id'] == 'test123_error_handler'
    assert error_handler['type'] == 'n8n-nodes-base.function'
    assert 'functionCode' in error_handler['parameters']
    
    # Check token node
    token_node = transformed[1]
    assert token_node['id'] == 'test123_token'
    assert token_node['type'] == 'n8n-nodes-base.httpRequest'
    assert token_node['parameters']['url'] == 'https://oauth2.googleapis.com/token'
    
    # Check operation node
    operation_node = transformed[2]
    assert operation_node['id'] == 'test123'  # Should preserve original ID
    assert operation_node['type'] == 'n8n-nodes-base.httpRequest'
    assert operation_node['parameters']['url'] == 'https://gmail.googleapis.com/gmail/v1/users/me/messages'

def test_transform_send_node():
    """Test transforming a Gmail 'send' node"""
    # Test input node
    node = {
        'id': 'send123',
        'name': 'Gmail Send',
        'type': 'n8n-nodes-base.gmail',
        'position': [100, 200],
        'parameters': {
            'operation': 'send',
            'sendTo': 'test@example.com',
            'subject': 'Test Email',
            'message': '<p>Test message</p>',
            'options': {
                'ccList': 'cc@example.com'
            }
        }
    }
    
    # Transform node
    transformed = GmailTransformer.transform_node(node, {})
    
    # Should return error handler, token node, MIME node and operation node
    assert len(transformed) == 4
    
    # Check error handler node
    error_handler = transformed[0]
    assert error_handler['id'] == 'send123_error_handler'
    assert error_handler['type'] == 'n8n-nodes-base.function'
    
    # Check token node
    token_node = transformed[1]
    assert token_node['id'] == 'send123_token'
    assert token_node['type'] == 'n8n-nodes-base.httpRequest'
    
    # Check MIME node
    mime_node = transformed[2]
    assert mime_node['id'] == 'send123_mime'
    assert mime_node['type'] == 'n8n-nodes-base.function'
    assert 'functionCode' in mime_node['parameters']
    
    # Check operation node
    operation_node = transformed[3]
    assert operation_node['id'] == 'send123'  # Should preserve original ID
    assert operation_node['type'] == 'n8n-nodes-base.httpRequest'
    assert operation_node['parameters']['url'] == 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'

def test_transform_get_node():
    """Test transforming a Gmail 'get' node"""
    # Test input node
    node = {
        'id': 'test789',
        'name': 'Gmail Get',
        'type': 'n8n-nodes-base.gmail',
        'position': [100, 200],
        'parameters': {
            'operation': 'get',
            'messageId': '12345'
        }
    }
    
    # Transform node
    transformed = GmailTransformer.transform_node(node, {})
    
    # Should return error handler, token node and operation node
    assert len(transformed) == 3
    
    # Check error handler
    error_node = transformed[0]
    assert error_node['type'] == 'n8n-nodes-base.function'
    
    # Check token node
    token_node = transformed[1]
    assert token_node['type'] == 'n8n-nodes-base.httpRequest'
    assert token_node['parameters']['url'] == 'https://oauth2.googleapis.com/token'
    assert token_node['continueOnFail'] == True
    
    # Check operation node
    operation_node = transformed[2]
    assert operation_node['type'] == 'n8n-nodes-base.httpRequest'
    assert operation_node['parameters']['url'] == 'https://gmail.googleapis.com/gmail/v1/users/me/messages/{{$parameter[\'messageId\']}}'
    assert operation_node['parameters']['method'] == 'GET'
    assert operation_node['continueOnFail'] == True
    assert any(p['name'] == 'format' and p['value'] == 'full'
              for p in operation_node['parameters']['queryParameters']['parameters']) 