"""
Tests for lambda_api/user_api.py - User API endpoints
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables"""
    monkeypatch.setenv('USER_POOL_ID', 'us-east-1_TEST123')
    monkeypatch.setenv('DYNAMODB_USERS_TABLE', 'test-users')


@patch('lambda_api.user_api.get_user_by_id')
@patch('lambda_api.user_api.get_user_id_from_event')
def test_get_profile_existing_user(mock_get_user_id, mock_get_user, mock_env, api_gateway_event, sample_user):
    """Test GET /user/profile for existing user"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_user.return_value = sample_user

    event = api_gateway_event(method='GET', path='/user/profile')
    event['resource'] = '/user/profile'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert body['user_id'] == 'test-user-123'
    assert body['email'] == 'test@example.com'


@patch('lambda_api.user_api.create_user')
@patch('lambda_api.user_api.get_user_by_id')
@patch('lambda_api.user_api.get_user_id_from_event')
@patch('lambda_api.user_api.get_user_email_from_event')
def test_get_profile_new_user_creates_record(
    mock_get_email, mock_get_user_id, mock_get_user, mock_create_user,
    mock_env, api_gateway_event, sample_user
):
    """Test GET /user/profile creates user if not exists"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'new-user-123'
    mock_get_email.return_value = 'newuser@example.com'
    mock_get_user.side_effect = [None, sample_user]  # First call: not found, second: found after creation
    mock_create_user.return_value = True

    event = api_gateway_event(method='GET', path='/user/profile', user_id='new-user-123')
    event['resource'] = '/user/profile'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    mock_create_user.assert_called_once()


@patch('lambda_api.user_api.get_user_by_id')
@patch('lambda_api.user_api.get_user_id_from_event')
def test_get_profile_unauthorized(mock_get_user_id, mock_get_user, mock_env, api_gateway_event):
    """Test GET /user/profile without authentication"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = None

    event = api_gateway_event(method='GET', path='/user/profile')
    event['resource'] = '/user/profile'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 401


@patch('lambda_api.user_api.update_user')
@patch('lambda_api.user_api.get_user_by_id')
@patch('lambda_api.user_api.get_user_id_from_event')
def test_update_profile_subscription_status(
    mock_get_user_id, mock_get_user, mock_update_user,
    mock_env, api_gateway_event, sample_user
):
    """Test PUT /user/profile to update subscription status"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_user.return_value = sample_user
    mock_update_user.return_value = True

    event = api_gateway_event(
        method='PUT',
        path='/user/profile',
        body={'subscription_status': 'paused'}
    )
    event['resource'] = '/user/profile'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    mock_update_user.assert_called_once()
    call_args = mock_update_user.call_args
    assert call_args[0][1]['subscription_status'] == 'paused'


@patch('lambda_api.user_api.get_user_id_from_event')
def test_update_profile_invalid_status(mock_get_user_id, mock_env, api_gateway_event):
    """Test PUT /user/profile with invalid subscription status"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(
        method='PUT',
        path='/user/profile',
        body={'subscription_status': 'invalid-status'}
    )
    event['resource'] = '/user/profile'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.user_api.get_user_id_from_event')
def test_update_profile_no_valid_fields(mock_get_user_id, mock_env, api_gateway_event):
    """Test PUT /user/profile with no valid fields"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(
        method='PUT',
        path='/user/profile',
        body={'unknown_field': 'value'}
    )
    event['resource'] = '/user/profile'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.user_api.update_user')
@patch('lambda_api.user_api.get_user_by_id')
@patch('lambda_api.user_api.get_user_id_from_event')
def test_update_preferences_success(
    mock_get_user_id, mock_get_user, mock_update_user,
    mock_env, api_gateway_event, sample_user
):
    """Test PUT /user/preferences"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_user.return_value = sample_user
    mock_update_user.return_value = True

    event = api_gateway_event(
        method='PUT',
        path='/user/preferences',
        body={
            'delivery_time': '09:00',
            'timezone': 'America/Los_Angeles',
            'email_enabled': False
        }
    )
    event['resource'] = '/user/preferences'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    mock_update_user.assert_called_once()


@patch('lambda_api.user_api.get_user_by_id')
@patch('lambda_api.user_api.get_user_id_from_event')
def test_update_preferences_user_not_found(
    mock_get_user_id, mock_get_user, mock_env, api_gateway_event
):
    """Test PUT /user/preferences for non-existent user"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_user.return_value = None

    event = api_gateway_event(
        method='PUT',
        path='/user/preferences',
        body={'email_enabled': False}
    )
    event['resource'] = '/user/preferences'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 404


@patch('lambda_api.user_api.cognito_client')
@patch('lambda_api.user_api.delete_user')
@patch('lambda_api.user_api.get_user_id_from_event')
def test_delete_account_success(
    mock_get_user_id, mock_delete_user, mock_cognito_client,
    mock_env, api_gateway_event
):
    """Test DELETE /user/account"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_delete_user.return_value = True
    mock_cognito_client.admin_delete_user.return_value = {}

    event = api_gateway_event(method='DELETE', path='/user/account')
    event['resource'] = '/user/account'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert body['dynamodb_deleted'] is True
    assert body['cognito_deleted'] is True


@patch('lambda_api.user_api.cognito_client')
@patch('lambda_api.user_api.delete_user')
@patch('lambda_api.user_api.get_user_id_from_event')
def test_delete_account_cognito_failure(
    mock_get_user_id, mock_delete_user, mock_cognito_client,
    mock_env, api_gateway_event
):
    """Test DELETE /user/account with Cognito failure"""
    from lambda_api.user_api import lambda_handler
    from botocore.exceptions import ClientError

    mock_get_user_id.return_value = 'test-user-123'
    mock_delete_user.return_value = True
    mock_cognito_client.admin_delete_user.side_effect = ClientError(
        {'Error': {'Code': 'UserNotFoundException', 'Message': 'User not found'}},
        'AdminDeleteUser'
    )

    event = api_gateway_event(method='DELETE', path='/user/account')
    event['resource'] = '/user/account'

    response = lambda_handler(event, {})

    # Should still succeed even if Cognito fails
    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert body['dynamodb_deleted'] is True
    assert body['cognito_deleted'] is False


@patch('lambda_api.user_api.delete_user')
@patch('lambda_api.user_api.get_user_id_from_event')
def test_delete_account_dynamodb_failure(
    mock_get_user_id, mock_delete_user, mock_env, api_gateway_event
):
    """Test DELETE /user/account with DynamoDB failure"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_delete_user.return_value = False

    event = api_gateway_event(method='DELETE', path='/user/account')
    event['resource'] = '/user/account'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 500


@patch('lambda_api.user_api.get_user_id_from_event')
def test_unknown_endpoint(mock_get_user_id, mock_env, api_gateway_event):
    """Test unknown endpoint returns 404"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='GET', path='/user/unknown')
    event['resource'] = '/user/unknown'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 404


@patch('lambda_api.user_api.get_user_id_from_event')
def test_handler_exception(mock_get_user_id, mock_env, api_gateway_event):
    """Test handler handles unexpected exceptions"""
    from lambda_api.user_api import lambda_handler

    mock_get_user_id.side_effect = Exception("Unexpected error")

    event = api_gateway_event(method='GET', path='/user/profile')
    event['resource'] = '/user/profile'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 500
