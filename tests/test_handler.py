"""
Tests for lambda/handler.py - Main Lambda function handler
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables"""
    monkeypatch.setenv('BUCKET_NAME', 'test-bucket')
    monkeypatch.setenv('SENDER_EMAIL', 'test@morningreflection.com')
    monkeypatch.setenv('DYNAMODB_USERS_TABLE', 'test-users')
    monkeypatch.setenv('DYNAMODB_REFLECTIONS_TABLE', 'test-reflections')
    monkeypatch.setenv('WEB_APP_URL', 'https://test.morningreflection.com')


@patch('handler.boto3')
@patch('handler.get_anthropic_api_key')
@patch('handler.load_quote_for_date')
@patch('handler.generate_reflection')
@patch('handler.generate_journaling_prompt')
@patch('handler.get_all_active_users')
@patch('handler.save_reflection_to_dynamodb')
@patch('handler.send_email')
def test_handler_success(
    mock_send_email,
    mock_save_reflection,
    mock_get_users,
    mock_gen_prompt,
    mock_gen_reflection,
    mock_load_quote,
    mock_get_api_key,
    mock_boto3,
    mock_env,
    lambda_context,
    sample_quote,
    sample_reflection,
    sample_journaling_prompt
):
    """Test successful execution of daily Lambda handler"""
    import handler

    # Mock API key retrieval
    mock_get_api_key.return_value = 'test-api-key'

    # Mock quote loading
    mock_load_quote.return_value = sample_quote

    # Mock reflection generation
    mock_gen_reflection.return_value = sample_reflection

    # Mock journaling prompt generation
    mock_gen_prompt.return_value = sample_journaling_prompt

    # Mock user retrieval
    mock_get_users.return_value = [
        {'user_id': 'user-1', 'email': 'user1@example.com'},
        {'user_id': 'user-2', 'email': 'user2@example.com'}
    ]

    # Mock DynamoDB save
    mock_save_reflection.return_value = True

    # Mock email sending
    mock_send_email.return_value = {'MessageId': 'test-message-id'}

    # Execute handler
    event = {}
    result = handler.handler(event, lambda_context)

    # Assertions
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert 'success' in body
    assert body['success'] is True

    # Verify quote was loaded
    mock_load_quote.assert_called_once()

    # Verify reflection was generated
    mock_gen_reflection.assert_called_once()

    # Verify journaling prompt was generated
    mock_gen_prompt.assert_called_once()

    # Verify users were retrieved
    mock_get_users.assert_called_once()

    # Verify DynamoDB save
    mock_save_reflection.assert_called_once()

    # Verify emails were sent (2 users)
    assert mock_send_email.call_count == 2


@patch('handler.boto3')
@patch('handler.get_anthropic_api_key')
@patch('handler.load_quote_for_date')
@patch('handler.generate_reflection')
def test_handler_reflection_generation_failure(
    mock_gen_reflection,
    mock_load_quote,
    mock_get_api_key,
    mock_boto3,
    mock_env,
    lambda_context,
    sample_quote
):
    """Test handler when reflection generation fails"""
    import handler

    mock_get_api_key.return_value = 'test-api-key'
    mock_load_quote.return_value = sample_quote
    mock_gen_reflection.return_value = None  # Simulation failure

    event = {}
    result = handler.handler(event, lambda_context)

    # Should return error
    assert result['statusCode'] == 500
    body = json.loads(result['body'])
    assert 'error' in body


@patch('handler.boto3')
@patch('handler.get_anthropic_api_key')
def test_handler_missing_api_key(
    mock_get_api_key,
    mock_boto3,
    mock_env,
    lambda_context
):
    """Test handler when API key is missing"""
    import handler

    mock_get_api_key.side_effect = ValueError("API key not found")

    event = {}
    result = handler.handler(event, lambda_context)

    assert result['statusCode'] == 500
    body = json.loads(result['body'])
    assert 'error' in body


@patch('handler.boto3')
@patch('handler.get_anthropic_api_key')
@patch('handler.load_quote_for_date')
@patch('handler.generate_reflection')
@patch('handler.generate_journaling_prompt')
@patch('handler.get_all_active_users')
def test_handler_no_users(
    mock_get_users,
    mock_gen_prompt,
    mock_gen_reflection,
    mock_load_quote,
    mock_get_api_key,
    mock_boto3,
    mock_env,
    lambda_context,
    sample_quote,
    sample_reflection
):
    """Test handler when no users are found"""
    import handler

    mock_get_api_key.return_value = 'test-api-key'
    mock_load_quote.return_value = sample_quote
    mock_gen_reflection.return_value = sample_reflection
    mock_gen_prompt.return_value = "Test prompt"
    mock_get_users.return_value = []  # No users

    event = {}
    result = handler.handler(event, lambda_context)

    # Should still succeed but send no emails
    assert result['statusCode'] == 200


@patch('handler.boto3')
def test_get_anthropic_api_key_from_secrets_manager(mock_boto3, mock_env, monkeypatch):
    """Test retrieving API key from Secrets Manager"""
    import handler

    monkeypatch.setenv('ANTHROPIC_API_KEY_SECRET_NAME', 'test-secret')

    mock_secrets_client = MagicMock()
    mock_secrets_client.get_secret_value.return_value = {
        'SecretString': json.dumps({'api_key': 'secret-api-key'})
    }
    mock_boto3.client.return_value = mock_secrets_client

    api_key = handler.get_anthropic_api_key()

    assert api_key == 'secret-api-key'
    mock_secrets_client.get_secret_value.assert_called_once()


@patch('handler.boto3')
def test_get_anthropic_api_key_from_env(mock_boto3, mock_env, monkeypatch):
    """Test retrieving API key from environment variable"""
    import handler

    monkeypatch.delenv('ANTHROPIC_API_KEY_SECRET_NAME', raising=False)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'env-api-key')

    api_key = handler.get_anthropic_api_key()

    assert api_key == 'env-api-key'


def test_get_anthropic_api_key_missing(mock_env, monkeypatch):
    """Test error when API key is completely missing"""
    import handler

    monkeypatch.delenv('ANTHROPIC_API_KEY_SECRET_NAME', raising=False)
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
        handler.get_anthropic_api_key()
