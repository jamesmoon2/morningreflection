"""
Tests for lambda_api/reflections_api.py - Reflections API endpoints
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables"""
    monkeypatch.setenv('DYNAMODB_REFLECTIONS_TABLE', 'test-reflections')


@pytest.fixture
def sample_reflection():
    """Sample reflection data"""
    return {
        'date': '2025-01-15',
        'quote': 'You have power over your mind - not outside events.',
        'attribution': 'Marcus Aurelius, Meditations, Book 6',
        'theme': 'Inner Strength',
        'reflection': 'This quote reminds us that true power lies within.',
        'journaling_prompt': 'What areas of your life do you have control over?',
        'generated_at': '2025-01-15T06:00:00Z'
    }


@patch('lambda_api.reflections_api.get_reflection_by_date')
@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_today_success(
    mock_get_user_id, mock_get_reflection, mock_env, api_gateway_event, sample_reflection
):
    """Test GET /reflections/today with available reflection"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_reflection.return_value = sample_reflection

    event = api_gateway_event(method='GET', path='/reflections/today')
    event['resource'] = '/reflections/today'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert body['date'] == '2025-01-15'
    assert 'quote' in body
    assert 'reflection' in body


@patch('lambda_api.reflections_api.get_reflection_by_date')
@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_today_not_found(mock_get_user_id, mock_get_reflection, mock_env, api_gateway_event):
    """Test GET /reflections/today when reflection not generated yet"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_reflection.return_value = None

    event = api_gateway_event(method='GET', path='/reflections/today')
    event['resource'] = '/reflections/today'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 404


@patch('lambda_api.reflections_api.get_reflection_by_date')
@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_by_date_success(
    mock_get_user_id, mock_get_reflection, mock_env, api_gateway_event, sample_reflection
):
    """Test GET /reflections/{date} with valid date"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_reflection.return_value = sample_reflection

    event = api_gateway_event(method='GET', path='/reflections/2025-01-15')
    event['resource'] = '/reflections/{date}'
    event['pathParameters'] = {'date': '2025-01-15'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert body['date'] == '2025-01-15'


@patch('lambda_api.reflections_api.get_reflection_by_date')
@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_by_date_not_found(mock_get_user_id, mock_get_reflection, mock_env, api_gateway_event):
    """Test GET /reflections/{date} when reflection doesn't exist"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_reflection.return_value = None

    event = api_gateway_event(method='GET', path='/reflections/2025-01-15')
    event['resource'] = '/reflections/{date}'
    event['pathParameters'] = {'date': '2025-01-15'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 404


@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_by_date_invalid_format(mock_get_user_id, mock_env, api_gateway_event):
    """Test GET /reflections/{date} with invalid date format"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='GET', path='/reflections/invalid-date')
    event['resource'] = '/reflections/{date}'
    event['pathParameters'] = {'date': 'invalid-date'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_by_date_missing_parameter(mock_get_user_id, mock_env, api_gateway_event):
    """Test GET /reflections/{date} without date parameter"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='GET', path='/reflections/')
    event['resource'] = '/reflections/{date}'
    event['pathParameters'] = {}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.reflections_api.get_reflections_for_month')
@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_calendar_current_month(
    mock_get_user_id, mock_get_reflections, mock_env, api_gateway_event
):
    """Test GET /reflections/calendar without parameters (current month)"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_reflections.return_value = [
        {'date': '2025-01-01'},
        {'date': '2025-01-15'},
    ]

    event = api_gateway_event(method='GET', path='/reflections/calendar')
    event['resource'] = '/reflections/calendar'
    event['queryStringParameters'] = None

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert 'year' in body
    assert 'month' in body
    assert 'days' in body
    assert len(body['days']) >= 28  # At least 28 days in any month


@patch('lambda_api.reflections_api.get_reflections_for_month')
@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_calendar_specific_month(
    mock_get_user_id, mock_get_reflections, mock_env, api_gateway_event
):
    """Test GET /reflections/calendar with specific month"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_reflections.return_value = [
        {'date': '2025-01-01'},
        {'date': '2025-01-15'},
    ]

    event = api_gateway_event(method='GET', path='/reflections/calendar')
    event['resource'] = '/reflections/calendar'
    event['queryStringParameters'] = {'month': '2025-01'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert body['year'] == 2025
    assert body['month'] == 1
    assert len(body['days']) == 31  # January has 31 days

    # Verify dates with reflections are marked
    jan_1 = next((d for d in body['days'] if d['date'] == '2025-01-01'), None)
    assert jan_1 is not None
    assert jan_1['has_reflection'] is True

    # Verify dates without reflections are not marked
    jan_2 = next((d for d in body['days'] if d['date'] == '2025-01-02'), None)
    assert jan_2 is not None
    assert jan_2['has_reflection'] is False


@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_calendar_invalid_month_format(mock_get_user_id, mock_env, api_gateway_event):
    """Test GET /reflections/calendar with invalid month format"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='GET', path='/reflections/calendar')
    event['resource'] = '/reflections/calendar'
    event['queryStringParameters'] = {'month': 'invalid-month'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_calendar_invalid_month_range(mock_get_user_id, mock_env, api_gateway_event):
    """Test GET /reflections/calendar with month out of range"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='GET', path='/reflections/calendar')
    event['resource'] = '/reflections/calendar'
    event['queryStringParameters'] = {'month': '2025-13'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.reflections_api.get_reflections_for_month')
@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_get_calendar_february_leap_year(
    mock_get_user_id, mock_get_reflections, mock_env, api_gateway_event
):
    """Test GET /reflections/calendar for February in leap year"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_reflections.return_value = []

    event = api_gateway_event(method='GET', path='/reflections/calendar')
    event['resource'] = '/reflections/calendar'
    event['queryStringParameters'] = {'month': '2024-02'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert len(body['days']) == 29  # February 2024 has 29 days (leap year)


@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_unauthorized_access(mock_get_user_id, mock_env, api_gateway_event):
    """Test API endpoints without authentication"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = None

    event = api_gateway_event(method='GET', path='/reflections/today')
    event['resource'] = '/reflections/today'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 401


@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_unknown_endpoint(mock_get_user_id, mock_env, api_gateway_event):
    """Test unknown endpoint returns 404"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='POST', path='/reflections/unknown')
    event['resource'] = '/reflections/unknown'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 404


@patch('lambda_api.reflections_api.get_user_id_from_event')
def test_handler_exception(mock_get_user_id, mock_env, api_gateway_event):
    """Test handler handles unexpected exceptions"""
    from lambda_api.reflections_api import lambda_handler

    mock_get_user_id.side_effect = Exception("Unexpected error")

    event = api_gateway_event(method='GET', path='/reflections/today')
    event['resource'] = '/reflections/today'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 500
