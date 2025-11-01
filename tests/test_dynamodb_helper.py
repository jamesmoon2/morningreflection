"""
Tests for lambda/dynamodb_helper.py - DynamoDB operations
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables"""
    monkeypatch.setenv('DYNAMODB_USERS_TABLE', 'test-users')
    monkeypatch.setenv('DYNAMODB_REFLECTIONS_TABLE', 'test-reflections')
    monkeypatch.setenv('WEB_APP_URL', 'https://test.morningreflection.com')


@patch('dynamodb_helper.boto3')
@patch('dynamodb_helper.dynamodb')
def test_save_reflection_to_dynamodb_success(
    mock_dynamodb_resource,
    mock_boto3,
    mock_env,
    sample_quote,
    sample_reflection,
    sample_journaling_prompt
):
    """Test successfully saving reflection to DynamoDB"""
    from dynamodb_helper import save_reflection_to_dynamodb

    mock_table = MagicMock()
    mock_dynamodb_resource.Table.return_value = mock_table
    mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

    result = save_reflection_to_dynamodb(
        date='2025-01-15',
        quote=sample_quote['quote'],
        attribution=sample_quote['attribution'],
        theme=sample_quote['theme'],
        reflection=sample_reflection,
        journaling_prompt=sample_journaling_prompt
    )

    assert result is True
    mock_table.put_item.assert_called_once()

    # Verify item structure
    call_args = mock_table.put_item.call_args
    item = call_args[1]['Item']
    assert item['date'] == '2025-01-15'
    assert item['quote'] == sample_quote['quote']
    assert item['reflection'] == sample_reflection
    assert item['journaling_prompt'] == sample_journaling_prompt


@patch('dynamodb_helper.boto3')
@patch('dynamodb_helper.dynamodb')
def test_save_reflection_to_dynamodb_failure(mock_dynamodb_resource, mock_boto3, mock_env):
    """Test handling DynamoDB save failure"""
    from dynamodb_helper import save_reflection_to_dynamodb

    mock_table = MagicMock()
    mock_dynamodb_resource.Table.return_value = mock_table
    mock_table.put_item.side_effect = Exception("DynamoDB error")

    result = save_reflection_to_dynamodb(
        date='2025-01-15',
        quote='Test quote',
        attribution='Test attribution',
        theme='Test theme',
        reflection='Test reflection'
    )

    assert result is False


@patch('dynamodb_helper.boto3')
@patch('dynamodb_helper.dynamodb')
def test_get_all_active_users_success(mock_dynamodb_resource, mock_boto3, mock_env):
    """Test retrieving all active users"""
    from dynamodb_helper import get_all_active_users

    mock_table = MagicMock()
    mock_dynamodb_resource.Table.return_value = mock_table
    mock_table.scan.return_value = {
        'Items': [
            {'user_id': 'user-1', 'email': 'user1@example.com', 'preferences': {'email_enabled': True}},
            {'user_id': 'user-2', 'email': 'user2@example.com', 'preferences': {'email_enabled': True}},
        ]
    }

    users = get_all_active_users()

    assert len(users) == 2
    assert users[0]['email'] == 'user1@example.com'
    assert users[1]['email'] == 'user2@example.com'


@patch('dynamodb_helper.boto3')
@patch('dynamodb_helper.dynamodb')
def test_get_all_active_users_filters_disabled(mock_dynamodb_resource, mock_boto3, mock_env):
    """Test that disabled users are filtered out"""
    from dynamodb_helper import get_all_active_users

    mock_table = MagicMock()
    mock_dynamodb_resource.Table.return_value = mock_table
    mock_table.scan.return_value = {
        'Items': [
            {'user_id': 'user-1', 'email': 'user1@example.com', 'preferences': {'email_enabled': True}},
            {'user_id': 'user-2', 'email': 'user2@example.com', 'preferences': {'email_enabled': False}},
            {'user_id': 'user-3', 'email': 'user3@example.com'},  # No preferences
        ]
    }

    users = get_all_active_users()

    # Should only include user-1 (explicitly enabled) and user-3 (default enabled)
    assert len(users) == 2
    emails = [u['email'] for u in users]
    assert 'user1@example.com' in emails
    assert 'user3@example.com' in emails
    assert 'user2@example.com' not in emails


@patch('dynamodb_helper.boto3')
@patch('dynamodb_helper.dynamodb')
def test_get_all_active_users_empty(mock_dynamodb_resource, mock_boto3, mock_env):
    """Test when no users exist"""
    from dynamodb_helper import get_all_active_users

    mock_table = MagicMock()
    mock_dynamodb_resource.Table.return_value = mock_table
    mock_table.scan.return_value = {'Items': []}

    users = get_all_active_users()

    assert len(users) == 0


@patch('dynamodb_helper.get_jwt_secret')
@patch('dynamodb_helper.jwt')
def test_generate_magic_link_success(mock_jwt, mock_get_secret, mock_env):
    """Test magic link generation"""
    from dynamodb_helper import generate_magic_link

    mock_get_secret.return_value = 'test-secret-key'
    mock_jwt.encode.return_value = 'test-jwt-token'

    magic_link = generate_magic_link(
        user_id='test-user-123',
        email='test@example.com',
        date='2025-01-15'
    )

    assert magic_link == 'https://test.morningreflection.com/daily/2025-01-15?token=test-jwt-token'

    # Verify JWT encoding was called
    mock_jwt.encode.assert_called_once()
    call_args = mock_jwt.encode.call_args
    payload = call_args[0][0]
    assert payload['user_id'] == 'test-user-123'
    assert payload['email'] == 'test@example.com'
    assert payload['date'] == '2025-01-15'
    assert payload['action'] == 'daily_reflection'
    assert 'exp' in payload


@patch('dynamodb_helper.boto3')
def test_get_jwt_secret_success(mock_boto3, mock_env):
    """Test retrieving JWT secret from Secrets Manager"""
    from dynamodb_helper import get_jwt_secret

    mock_secrets_client = MagicMock()
    mock_secrets_client.get_secret_value.return_value = {
        'SecretString': json.dumps({'jwt_secret': 'my-secret-key'})
    }
    mock_boto3.client.return_value = mock_secrets_client

    secret = get_jwt_secret()

    assert secret == 'my-secret-key'


@patch('dynamodb_helper.boto3')
def test_get_jwt_secret_fallback(mock_boto3, mock_env):
    """Test JWT secret fallback when not in Secrets Manager"""
    from dynamodb_helper import get_jwt_secret

    mock_secrets_client = MagicMock()
    mock_secrets_client.get_secret_value.side_effect = Exception("Secret not found")
    mock_boto3.client.return_value = mock_secrets_client

    secret = get_jwt_secret()

    # Should return a default secret (deterministic based on env vars)
    assert isinstance(secret, str)
    assert len(secret) > 0
