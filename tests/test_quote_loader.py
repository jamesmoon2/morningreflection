"""
Tests for lambda/quote_loader.py - Quote loading from S3 database
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from botocore.exceptions import ClientError

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))


@pytest.fixture
def sample_quotes_database():
    """Sample quotes database structure"""
    return {
        'january': [
            {
                'day': 1,
                'quote': 'You have power over your mind - not outside events.',
                'attribution': 'Marcus Aurelius, Meditations, Book 6',
                'theme': 'Inner Strength'
            },
            {
                'day': 2,
                'quote': 'The impediment to action advances action.',
                'attribution': 'Marcus Aurelius, Meditations, Book 5',
                'theme': 'Inner Strength'
            }
        ],
        'february': [
            {
                'day': 1,
                'quote': 'First say to yourself what you would be.',
                'attribution': 'Epictetus, Discourses',
                'theme': 'Virtue and Character'
            },
            {
                'day': 28,
                'quote': 'It is not that we have a short time to live.',
                'attribution': 'Seneca, On the Shortness of Life',
                'theme': 'Virtue and Character'
            }
        ]
    }


# QuoteLoader Tests

@patch('quote_loader.boto3.client')
def test_quote_loader_load_database_success(mock_boto3_client, sample_quotes_database):
    """Test successful loading of quotes database from S3"""
    from quote_loader import QuoteLoader

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(sample_quotes_database).encode())
    }

    loader = QuoteLoader('test-bucket')
    quotes = loader.load_quotes_database()

    assert quotes == sample_quotes_database
    assert 'january' in quotes
    assert len(quotes['january']) == 2
    mock_s3.get_object.assert_called_once_with(
        Bucket='test-bucket',
        Key='config/stoic_quotes_365_days.json'
    )


@patch('quote_loader.boto3.client')
def test_quote_loader_database_caching(mock_boto3_client, sample_quotes_database):
    """Test that quotes database is cached after first load"""
    from quote_loader import QuoteLoader

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(sample_quotes_database).encode())
    }

    loader = QuoteLoader('test-bucket')

    # First call should load from S3
    quotes1 = loader.load_quotes_database()

    # Second call should use cache
    quotes2 = loader.load_quotes_database()

    # S3 should only be called once
    assert mock_s3.get_object.call_count == 1
    assert quotes1 == quotes2


@patch('quote_loader.boto3.client')
def test_quote_loader_database_not_found(mock_boto3_client):
    """Test loading when database file doesn't exist in S3"""
    from quote_loader import QuoteLoader

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey'}},
        'GetObject'
    )

    loader = QuoteLoader('test-bucket')

    with pytest.raises(Exception) as exc_info:
        loader.load_quotes_database()

    assert 'not found in S3 bucket' in str(exc_info.value)


@patch('quote_loader.boto3.client')
def test_quote_loader_invalid_json(mock_boto3_client):
    """Test loading when database contains invalid JSON"""
    from quote_loader import QuoteLoader

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: b'{ invalid json }')
    }

    loader = QuoteLoader('test-bucket')

    with pytest.raises(Exception) as exc_info:
        loader.load_quotes_database()

    assert 'invalid JSON' in str(exc_info.value)


@patch('quote_loader.boto3.client')
def test_get_quote_for_date_success(mock_boto3_client, sample_quotes_database):
    """Test getting quote for a specific date"""
    from quote_loader import QuoteLoader

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(sample_quotes_database).encode())
    }

    loader = QuoteLoader('test-bucket')
    date = datetime(2025, 1, 1)

    quote = loader.get_quote_for_date(date)

    assert quote['quote'] == 'You have power over your mind - not outside events.'
    assert quote['attribution'] == 'Marcus Aurelius, Meditations, Book 6'
    assert quote['theme'] == 'Inner Strength'


@patch('quote_loader.boto3.client')
def test_get_quote_for_date_february_29_leap_year(mock_boto3_client, sample_quotes_database):
    """Test getting quote for February 29 (leap year) uses February 28"""
    from quote_loader import QuoteLoader

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(sample_quotes_database).encode())
    }

    loader = QuoteLoader('test-bucket')
    date = datetime(2024, 2, 29)  # Leap year

    quote = loader.get_quote_for_date(date)

    # Should return Feb 28 quote
    assert quote['quote'] == 'It is not that we have a short time to live.'


@patch('quote_loader.boto3.client')
def test_get_quote_for_date_month_not_found(mock_boto3_client):
    """Test getting quote when month doesn't exist in database"""
    from quote_loader import QuoteLoader

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    # Database with missing month
    incomplete_db = {'january': []}

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(incomplete_db).encode())
    }

    loader = QuoteLoader('test-bucket')
    date = datetime(2025, 2, 1)  # February not in database

    with pytest.raises(Exception) as exc_info:
        loader.get_quote_for_date(date)

    assert 'not found in quotes database' in str(exc_info.value)


@patch('quote_loader.boto3.client')
def test_get_quote_for_date_day_not_found(mock_boto3_client, sample_quotes_database):
    """Test getting quote when day doesn't exist in month"""
    from quote_loader import QuoteLoader

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(sample_quotes_database).encode())
    }

    loader = QuoteLoader('test-bucket')
    date = datetime(2025, 1, 31)  # January 31 not in sample database

    with pytest.raises(Exception) as exc_info:
        loader.get_quote_for_date(date)

    assert 'No quote found for' in str(exc_info.value)


@patch('quote_loader.boto3.client')
def test_validate_database_completeness_complete(mock_boto3_client):
    """Test validation of complete 365-day database"""
    from quote_loader import QuoteLoader

    # Create complete database (all 365 days)
    complete_db = {}
    months = {
        'january': 31, 'february': 28, 'march': 31, 'april': 30,
        'may': 31, 'june': 30, 'july': 31, 'august': 31,
        'september': 30, 'october': 31, 'november': 30, 'december': 31
    }

    for month, days in months.items():
        complete_db[month] = [
            {
                'day': day,
                'quote': f'Quote for {month} {day}',
                'attribution': 'Test Attribution',
                'theme': 'Test Theme'
            }
            for day in range(1, days + 1)
        ]

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(complete_db).encode())
    }

    loader = QuoteLoader('test-bucket')
    result = loader.validate_database_completeness()

    assert result['complete'] is True
    assert result['total_quotes'] == 365
    assert result['expected_quotes'] == 365
    assert len(result['missing_days']) == 0
    assert len(result['duplicate_days']) == 0


@patch('quote_loader.boto3.client')
def test_validate_database_completeness_missing_days(mock_boto3_client):
    """Test validation detects missing days"""
    from quote_loader import QuoteLoader

    # Database missing some days
    incomplete_db = {
        'january': [
            {'day': 1, 'quote': 'Quote 1', 'attribution': 'Test', 'theme': 'Test'}
            # Missing days 2-31
        ],
        'february': [
            {'day': 1, 'quote': 'Quote 1', 'attribution': 'Test', 'theme': 'Test'}
            # Missing days 2-28
        ]
    }

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(incomplete_db).encode())
    }

    loader = QuoteLoader('test-bucket')
    result = loader.validate_database_completeness()

    assert result['complete'] is False
    assert result['total_quotes'] < 365
    assert len(result['missing_days']) > 0


@patch('quote_loader.boto3.client')
def test_validate_database_completeness_duplicate_days(mock_boto3_client):
    """Test validation detects duplicate days"""
    from quote_loader import QuoteLoader

    # Database with duplicate day
    duplicate_db = {
        'january': [
            {'day': 1, 'quote': 'Quote 1', 'attribution': 'Test', 'theme': 'Test'},
            {'day': 1, 'quote': 'Duplicate Quote 1', 'attribution': 'Test', 'theme': 'Test'}  # Duplicate
        ]
    }

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(duplicate_db).encode())
    }

    loader = QuoteLoader('test-bucket')
    result = loader.validate_database_completeness()

    assert result['complete'] is False
    assert len(result['duplicate_days']) > 0
    assert ('january', 1) in result['duplicate_days']


@patch('quote_loader.boto3.client')
def test_validate_database_completeness_missing_month(mock_boto3_client):
    """Test validation detects missing months"""
    from quote_loader import QuoteLoader

    # Database missing entire month
    incomplete_db = {
        'january': [
            {'day': i, 'quote': f'Quote {i}', 'attribution': 'Test', 'theme': 'Test'}
            for i in range(1, 32)
        ]
        # Missing february through december
    }

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(incomplete_db).encode())
    }

    loader = QuoteLoader('test-bucket')
    result = loader.validate_database_completeness()

    assert result['complete'] is False
    assert result['total_quotes'] == 31
    assert len(result['missing_days']) == 365 - 31  # Missing 334 days


# Convenience Function Tests

@patch('quote_loader.boto3.client')
def test_convenience_function_get_quote_for_date(mock_boto3_client, sample_quotes_database):
    """Test convenience function get_quote_for_date"""
    from quote_loader import get_quote_for_date

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(sample_quotes_database).encode())
    }

    date = datetime(2025, 1, 2)
    quote = get_quote_for_date('test-bucket', date)

    assert quote['quote'] == 'The impediment to action advances action.'
    assert quote['attribution'] == 'Marcus Aurelius, Meditations, Book 5'
