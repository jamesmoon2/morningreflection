"""
Tests for lambda_api/dynamodb_operations.py - DynamoDB CRUD operations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables"""
    monkeypatch.setenv('DYNAMODB_USERS_TABLE', 'test-users')
    monkeypatch.setenv('DYNAMODB_REFLECTIONS_TABLE', 'test-reflections')
    monkeypatch.setenv('DYNAMODB_JOURNAL_TABLE', 'test-journal')


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_get_user_by_id_success(mock_dynamodb, mock_env, sample_user):
    """Test retrieving user by ID"""
    from lambda_api.dynamodb_operations import get_user_by_id

    mock_table = MagicMock()
    mock_table.get_item.return_value = {'Item': sample_user}
    mock_dynamodb.Table.return_value = mock_table

    user = get_user_by_id('test-user-123')

    assert user == sample_user
    mock_table.get_item.assert_called_once_with(Key={'user_id': 'test-user-123'})


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_get_user_by_id_not_found(mock_dynamodb, mock_env):
    """Test user not found"""
    from lambda_api.dynamodb_operations import get_user_by_id

    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_dynamodb.Table.return_value = mock_table

    user = get_user_by_id('nonexistent-user')

    assert user is None


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_create_or_update_user(mock_dynamodb, mock_env):
    """Test creating or updating user"""
    from lambda_api.dynamodb_operations import create_or_update_user

    mock_table = MagicMock()
    mock_dynamodb.Table.return_value = mock_table

    result = create_or_update_user(
        user_id='test-user-123',
        email='test@example.com',
        profile={'display_name': 'Test User'}
    )

    assert result is True
    mock_table.put_item.assert_called_once()


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_update_user_preferences(mock_dynamodb, mock_env):
    """Test updating user preferences"""
    from lambda_api.dynamodb_operations import update_user_preferences

    mock_table = MagicMock()
    mock_dynamodb.Table.return_value = mock_table

    preferences = {
        'email_enabled': True,
        'delivery_time': '08:00',
        'timezone': 'America/New_York'
    }

    result = update_user_preferences('test-user-123', preferences)

    assert result is True
    mock_table.update_item.assert_called_once()


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_delete_user(mock_dynamodb, mock_env):
    """Test deleting user"""
    from lambda_api.dynamodb_operations import delete_user

    mock_table = MagicMock()
    mock_dynamodb.Table.return_value = mock_table

    result = delete_user('test-user-123')

    assert result is True
    mock_table.delete_item.assert_called_once_with(Key={'user_id': 'test-user-123'})


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_get_reflection_by_date_success(mock_dynamodb, mock_env):
    """Test retrieving reflection by date"""
    from lambda_api.dynamodb_operations import get_reflection_by_date

    reflection = {
        'date': '2025-01-15',
        'quote': 'Test quote',
        'reflection': 'Test reflection'
    }

    mock_table = MagicMock()
    mock_table.get_item.return_value = {'Item': reflection}
    mock_dynamodb.Table.return_value = mock_table

    result = get_reflection_by_date('2025-01-15')

    assert result == reflection


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_get_reflection_by_date_not_found(mock_dynamodb, mock_env):
    """Test reflection not found"""
    from lambda_api.dynamodb_operations import get_reflection_by_date

    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_dynamodb.Table.return_value = mock_table

    result = get_reflection_by_date('2025-01-15')

    assert result is None


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_get_calendar_metadata(mock_dynamodb, mock_env):
    """Test retrieving calendar metadata"""
    from lambda_api.dynamodb_operations import get_calendar_metadata

    # Mock reflections for January 2025
    mock_reflections_table = MagicMock()
    mock_reflections_table.scan.return_value = {
        'Items': [
            {'date': '2025-01-01'},
            {'date': '2025-01-15'},
        ]
    }

    # Mock journal entries
    mock_journal_table = MagicMock()
    mock_journal_table.query.return_value = {
        'Items': [
            {'date': '2025-01-01', 'word_count': 100},
            {'date': '2025-01-02', 'word_count': 150},
        ]
    }

    def table_side_effect(name):
        if 'reflections' in name.lower():
            return mock_reflections_table
        return mock_journal_table

    mock_dynamodb.Table.side_effect = table_side_effect

    metadata = get_calendar_metadata(user_id='test-user-123', year=2025, month=1)

    assert isinstance(metadata, list)
    assert len(metadata) == 31  # January has 31 days

    # Check that dates with data are marked
    jan_1 = next((d for d in metadata if d['date'] == '2025-01-01'), None)
    assert jan_1 is not None
    assert jan_1['hasReflection'] is True
    assert jan_1['hasJournal'] is True


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_create_or_update_journal_entry(mock_dynamodb, mock_env):
    """Test creating or updating journal entry"""
    from lambda_api.dynamodb_operations import create_or_update_journal_entry

    mock_table = MagicMock()
    mock_dynamodb.Table.return_value = mock_table

    result = create_or_update_journal_entry(
        user_id='test-user-123',
        date='2025-01-15',
        entry='This is my journal entry for today.'
    )

    assert result is True
    mock_table.put_item.assert_called_once()

    # Verify word count is calculated
    call_args = mock_table.put_item.call_args
    item = call_args[1]['Item']
    assert item['word_count'] == 7  # "This is my journal entry for today" = 7 words


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_get_journal_entry_success(mock_dynamodb, mock_env, sample_journal_entry):
    """Test retrieving journal entry"""
    from lambda_api.dynamodb_operations import get_journal_entry

    mock_table = MagicMock()
    mock_table.get_item.return_value = {'Item': sample_journal_entry}
    mock_dynamodb.Table.return_value = mock_table

    entry = get_journal_entry(user_id='test-user-123', date='2025-01-15')

    assert entry == sample_journal_entry


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_get_journal_entry_not_found(mock_dynamodb, mock_env):
    """Test journal entry not found"""
    from lambda_api.dynamodb_operations import get_journal_entry

    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_dynamodb.Table.return_value = mock_table

    entry = get_journal_entry(user_id='test-user-123', date='2025-01-15')

    assert entry is None


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_delete_journal_entry(mock_dynamodb, mock_env):
    """Test deleting journal entry"""
    from lambda_api.dynamodb_operations import delete_journal_entry

    mock_table = MagicMock()
    mock_dynamodb.Table.return_value = mock_table

    result = delete_journal_entry(user_id='test-user-123', date='2025-01-15')

    assert result is True
    mock_table.delete_item.assert_called_once()


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_get_journal_list(mock_dynamodb, mock_env):
    """Test retrieving journal entry list"""
    from lambda_api.dynamodb_operations import get_journal_list

    mock_table = MagicMock()
    mock_table.query.return_value = {
        'Items': [
            {
                'user_id': 'test-user-123',
                'date': '2025-01-15',
                'entry': 'This is a test entry with some content.',
                'word_count': 8,
                'updated_at': '2025-01-15T10:00:00Z'
            },
            {
                'user_id': 'test-user-123',
                'date': '2025-01-14',
                'entry': 'Another entry.',
                'word_count': 2,
                'updated_at': '2025-01-14T10:00:00Z'
            }
        ]
    }
    mock_dynamodb.Table.return_value = mock_table

    entries = get_journal_list(user_id='test-user-123')

    assert len(entries) == 2
    assert entries[0]['date'] == '2025-01-15'
    assert 'preview' in entries[0]
    assert len(entries[0]['preview']) <= 100


@patch('lambda_api.dynamodb_operations.dynamodb')
def test_get_journal_list_with_limit(mock_dynamodb, mock_env):
    """Test retrieving journal entries with limit"""
    from lambda_api.dynamodb_operations import get_journal_list

    mock_table = MagicMock()
    mock_table.query.return_value = {'Items': []}
    mock_dynamodb.Table.return_value = mock_table

    get_journal_list(user_id='test-user-123', limit=10)

    # Verify limit was passed to query
    call_args = mock_table.query.call_args
    assert call_args[1]['Limit'] == 10
