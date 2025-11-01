"""
Tests for lambda_api/journal_api.py - Journal API endpoints
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables"""
    monkeypatch.setenv('DYNAMODB_JOURNAL_TABLE', 'test-journal')


@pytest.fixture
def mock_security_available(monkeypatch):
    """Mock security modules availability"""
    monkeypatch.setattr('lambda_api.journal_api.SECURITY_MODULES_AVAILABLE', True)


@patch('lambda_api.journal_api.create_or_update_journal_entry')
@patch('lambda_api.journal_api.get_journal_entry')
@patch('lambda_api.journal_api.get_user_id_from_event')
@patch('lambda_api.journal_api.validate_journal_entry')
def test_create_journal_entry_success(
    mock_validate, mock_get_user_id, mock_get_entry, mock_create_entry,
    mock_env, api_gateway_event, sample_journal_entry
):
    """Test POST /journal to create new entry"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_validate.return_value = {
        'valid': True,
        'sanitized_entry': 'This is my journal entry for today.'
    }
    mock_create_entry.return_value = True
    mock_get_entry.return_value = sample_journal_entry

    event = api_gateway_event(
        method='POST',
        path='/journal',
        body={
            'date': '2025-01-15',
            'entry': 'This is my journal entry for today.'
        }
    )
    event['resource'] = '/journal'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 201
    body = eval(response['body'])
    assert 'entry' in body
    assert body['entry']['date'] == '2025-01-15'


@patch('lambda_api.journal_api.get_user_id_from_event')
def test_create_journal_entry_missing_fields(mock_get_user_id, mock_env, api_gateway_event):
    """Test POST /journal without required fields"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(
        method='POST',
        path='/journal',
        body={'date': '2025-01-15'}  # Missing 'entry'
    )
    event['resource'] = '/journal'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.journal_api.get_user_id_from_event')
def test_create_journal_entry_invalid_date_format(mock_get_user_id, mock_env, api_gateway_event):
    """Test POST /journal with invalid date format"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(
        method='POST',
        path='/journal',
        body={
            'date': '01/15/2025',  # Invalid format
            'entry': 'Test entry'
        }
    )
    event['resource'] = '/journal'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.journal_api.get_user_id_from_event')
@patch('lambda_api.journal_api.validate_journal_entry')
def test_create_journal_entry_validation_failure(
    mock_validate, mock_get_user_id, mock_env, api_gateway_event
):
    """Test POST /journal with content that fails validation"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_validate.return_value = {
        'valid': False,
        'error_message': 'Journal entry contains prohibited content'
    }

    event = api_gateway_event(
        method='POST',
        path='/journal',
        body={
            'date': '2025-01-15',
            'entry': '<script>alert("xss")</script>'
        }
    )
    event['resource'] = '/journal'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.journal_api.create_or_update_journal_entry')
@patch('lambda_api.journal_api.get_user_id_from_event')
@patch('lambda_api.journal_api.validate_journal_entry')
def test_create_journal_entry_save_failure(
    mock_validate, mock_get_user_id, mock_create_entry,
    mock_env, api_gateway_event
):
    """Test POST /journal when save fails"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_validate.return_value = {
        'valid': True,
        'sanitized_entry': 'Test entry'
    }
    mock_create_entry.return_value = False

    event = api_gateway_event(
        method='POST',
        path='/journal',
        body={
            'date': '2025-01-15',
            'entry': 'Test entry'
        }
    )
    event['resource'] = '/journal'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 500


@patch('lambda_api.journal_api.get_journal_entry')
@patch('lambda_api.journal_api.get_user_id_from_event')
def test_get_journal_entry_success(
    mock_get_user_id, mock_get_entry, mock_env, api_gateway_event, sample_journal_entry
):
    """Test GET /journal/{date}"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_entry.return_value = sample_journal_entry

    event = api_gateway_event(method='GET', path='/journal/2025-01-15')
    event['resource'] = '/journal/{date}'
    event['pathParameters'] = {'date': '2025-01-15'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert body['date'] == '2025-01-15'
    assert 'entry' in body


@patch('lambda_api.journal_api.get_journal_entry')
@patch('lambda_api.journal_api.get_user_id_from_event')
def test_get_journal_entry_not_found(mock_get_user_id, mock_get_entry, mock_env, api_gateway_event):
    """Test GET /journal/{date} when entry doesn't exist"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_entry.return_value = None

    event = api_gateway_event(method='GET', path='/journal/2025-01-15')
    event['resource'] = '/journal/{date}'
    event['pathParameters'] = {'date': '2025-01-15'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 404


@patch('lambda_api.journal_api.get_user_id_from_event')
def test_get_journal_entry_invalid_date(mock_get_user_id, mock_env, api_gateway_event):
    """Test GET /journal/{date} with invalid date"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='GET', path='/journal/invalid-date')
    event['resource'] = '/journal/{date}'
    event['pathParameters'] = {'date': 'invalid-date'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.journal_api.delete_journal_entry')
@patch('lambda_api.journal_api.get_journal_entry')
@patch('lambda_api.journal_api.get_user_id_from_event')
def test_delete_journal_entry_success(
    mock_get_user_id, mock_get_entry, mock_delete_entry,
    mock_env, api_gateway_event, sample_journal_entry
):
    """Test DELETE /journal/{date}"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_entry.return_value = sample_journal_entry
    mock_delete_entry.return_value = True

    event = api_gateway_event(method='DELETE', path='/journal/2025-01-15')
    event['resource'] = '/journal/{date}'
    event['pathParameters'] = {'date': '2025-01-15'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert body['date'] == '2025-01-15'


@patch('lambda_api.journal_api.get_journal_entry')
@patch('lambda_api.journal_api.get_user_id_from_event')
def test_delete_journal_entry_not_found(
    mock_get_user_id, mock_get_entry, mock_env, api_gateway_event
):
    """Test DELETE /journal/{date} when entry doesn't exist"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_entry.return_value = None

    event = api_gateway_event(method='DELETE', path='/journal/2025-01-15')
    event['resource'] = '/journal/{date}'
    event['pathParameters'] = {'date': '2025-01-15'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 404


@patch('lambda_api.journal_api.delete_journal_entry')
@patch('lambda_api.journal_api.get_journal_entry')
@patch('lambda_api.journal_api.get_user_id_from_event')
def test_delete_journal_entry_failure(
    mock_get_user_id, mock_get_entry, mock_delete_entry,
    mock_env, api_gateway_event, sample_journal_entry
):
    """Test DELETE /journal/{date} when delete fails"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_entry.return_value = sample_journal_entry
    mock_delete_entry.return_value = False

    event = api_gateway_event(method='DELETE', path='/journal/2025-01-15')
    event['resource'] = '/journal/{date}'
    event['pathParameters'] = {'date': '2025-01-15'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 500


@patch('lambda_api.journal_api.get_journal_entries_for_user')
@patch('lambda_api.journal_api.get_user_id_from_event')
def test_list_journal_entries_default(
    mock_get_user_id, mock_get_entries, mock_env, api_gateway_event
):
    """Test GET /journal/list with default parameters"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_entries.return_value = [
        {
            'date': '2025-01-15',
            'word_count': 150,
            'created_at': '2025-01-15T10:00:00Z',
            'updated_at': '2025-01-15T10:00:00Z'
        },
        {
            'date': '2025-01-14',
            'word_count': 200,
            'created_at': '2025-01-14T10:00:00Z',
            'updated_at': '2025-01-14T10:00:00Z'
        }
    ]

    event = api_gateway_event(method='GET', path='/journal/list')
    event['resource'] = '/journal/list'
    event['queryStringParameters'] = None

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = eval(response['body'])
    assert body['count'] == 2
    assert len(body['entries']) == 2


@patch('lambda_api.journal_api.get_journal_entries_for_user')
@patch('lambda_api.journal_api.get_user_id_from_event')
def test_list_journal_entries_with_date_range(
    mock_get_user_id, mock_get_entries, mock_env, api_gateway_event
):
    """Test GET /journal/list with date range"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_entries.return_value = []

    event = api_gateway_event(method='GET', path='/journal/list')
    event['resource'] = '/journal/list'
    event['queryStringParameters'] = {
        'from': '2025-01-01',
        'to': '2025-01-31',
        'limit': '50'
    }

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    mock_get_entries.assert_called_once()
    call_args = mock_get_entries.call_args[1]
    assert call_args['start_date'] == '2025-01-01'
    assert call_args['end_date'] == '2025-01-31'
    assert call_args['limit'] == 50


@patch('lambda_api.journal_api.get_user_id_from_event')
def test_list_journal_entries_invalid_limit(mock_get_user_id, mock_env, api_gateway_event):
    """Test GET /journal/list with invalid limit"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='GET', path='/journal/list')
    event['resource'] = '/journal/list'
    event['queryStringParameters'] = {'limit': 'not-a-number'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


@patch('lambda_api.journal_api.get_journal_entries_for_user')
@patch('lambda_api.journal_api.get_user_id_from_event')
def test_list_journal_entries_limit_max(
    mock_get_user_id, mock_get_entries, mock_env, api_gateway_event
):
    """Test GET /journal/list respects maximum limit"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'
    mock_get_entries.return_value = []

    event = api_gateway_event(method='GET', path='/journal/list')
    event['resource'] = '/journal/list'
    event['queryStringParameters'] = {'limit': '1000'}  # Over max

    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    call_args = mock_get_entries.call_args[1]
    assert call_args['limit'] == 500  # Capped at 500


@patch('lambda_api.journal_api.get_user_id_from_event')
def test_list_journal_entries_invalid_date_format(mock_get_user_id, mock_env, api_gateway_event):
    """Test GET /journal/list with invalid date format"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='GET', path='/journal/list')
    event['resource'] = '/journal/list'
    event['queryStringParameters'] = {'from': 'invalid-date'}

    response = lambda_handler(event, {})

    assert response['statusCode'] == 400


def test_validate_journal_entry_without_security_modules(mock_env):
    """Test journal validation when security modules aren't available"""
    from lambda_api.journal_api import validate_journal_entry

    # Temporarily disable security modules
    import lambda_api.journal_api as journal_api
    original_value = journal_api.SECURITY_MODULES_AVAILABLE
    journal_api.SECURITY_MODULES_AVAILABLE = False

    try:
        # Valid entry
        result = validate_journal_entry("This is a valid journal entry.")
        assert result['valid'] is True
        assert result['sanitized_entry'] == "This is a valid journal entry."

        # Too long entry
        long_entry = "x" * 10001
        result = validate_journal_entry(long_entry)
        assert result['valid'] is False
        assert "exceeds 10,000 character limit" in result['error_message']

    finally:
        journal_api.SECURITY_MODULES_AVAILABLE = original_value


@patch('lambda_api.journal_api.ContentSanitizer')
@patch('lambda_api.journal_api.MaliciousPatternDetector')
@patch('lambda_api.journal_api.CharacterValidator')
def test_validate_journal_entry_with_security_modules(
    mock_char_validator, mock_pattern_detector, mock_sanitizer, mock_env, mock_security_available
):
    """Test journal validation with security modules"""
    from lambda_api.journal_api import validate_journal_entry

    # Set up mocks
    mock_sanitizer_instance = MagicMock()
    mock_sanitizer_instance.sanitize.return_value = "Sanitized entry"
    mock_sanitizer.return_value = mock_sanitizer_instance

    mock_pattern_instance = MagicMock()
    mock_pattern_instance.check_content.return_value = {
        'has_malicious_patterns': False,
        'patterns_found': []
    }
    mock_pattern_detector.return_value = mock_pattern_instance

    mock_char_instance = MagicMock()
    mock_char_instance.validate.return_value = {'valid': True}
    mock_char_validator.return_value = mock_char_instance

    result = validate_journal_entry("Test entry")

    assert result['valid'] is True
    assert result['sanitized_entry'] == "Sanitized entry"


@patch('lambda_api.journal_api.ContentSanitizer')
@patch('lambda_api.journal_api.MaliciousPatternDetector')
def test_validate_journal_entry_malicious_patterns(
    mock_pattern_detector, mock_sanitizer, mock_env, mock_security_available
):
    """Test journal validation detects malicious patterns"""
    from lambda_api.journal_api import validate_journal_entry

    # Set up mocks
    mock_sanitizer_instance = MagicMock()
    mock_sanitizer_instance.sanitize.return_value = '<script>alert("xss")</script>'
    mock_sanitizer.return_value = mock_sanitizer_instance

    mock_pattern_instance = MagicMock()
    mock_pattern_instance.check_content.return_value = {
        'has_malicious_patterns': True,
        'patterns_found': ['<script>']
    }
    mock_pattern_detector.return_value = mock_pattern_instance

    result = validate_journal_entry('<script>alert("xss")</script>')

    assert result['valid'] is False
    assert 'prohibited content' in result['error_message']


@patch('lambda_api.journal_api.get_user_id_from_event')
def test_unauthorized_access(mock_get_user_id, mock_env, api_gateway_event):
    """Test API endpoints without authentication"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = None

    event = api_gateway_event(method='GET', path='/journal/list')
    event['resource'] = '/journal/list'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 401


@patch('lambda_api.journal_api.get_user_id_from_event')
def test_unknown_endpoint(mock_get_user_id, mock_env, api_gateway_event):
    """Test unknown endpoint returns 404"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.return_value = 'test-user-123'

    event = api_gateway_event(method='GET', path='/journal/unknown')
    event['resource'] = '/journal/unknown'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 404


@patch('lambda_api.journal_api.get_user_id_from_event')
def test_handler_exception(mock_get_user_id, mock_env, api_gateway_event):
    """Test handler handles unexpected exceptions"""
    from lambda_api.journal_api import lambda_handler

    mock_get_user_id.side_effect = Exception("Unexpected error")

    event = api_gateway_event(method='POST', path='/journal')
    event['resource'] = '/journal'

    response = lambda_handler(event, {})

    assert response['statusCode'] == 500
