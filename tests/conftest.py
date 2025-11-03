"""
pytest configuration and shared fixtures
"""

import pytest
import os
from datetime import datetime
from unittest.mock import MagicMock

# Set test environment variables
os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
os.environ['BUCKET_NAME'] = 'test-bucket'
os.environ['SENDER_EMAIL'] = 'test@morningreflection.com'
os.environ['DYNAMODB_USERS_TABLE'] = 'test-users'
os.environ['DYNAMODB_REFLECTIONS_TABLE'] = 'test-reflections'
os.environ['DYNAMODB_JOURNAL_TABLE'] = 'test-journal'
os.environ['WEB_APP_URL'] = 'https://test.morningreflection.com'
os.environ['ANTHROPIC_API_KEY'] = 'test-api-key'
os.environ['SECURITY_ALERT_TOPIC_ARN'] = 'arn:aws:sns:us-west-2:123456789012:test-topic'


@pytest.fixture
def sample_quote():
    """Sample stoic quote for testing"""
    return {
        "date": "2025-01-15",
        "quote": "You have power over your mind - not outside events. Realize this, and you will find strength.",
        "attribution": "Marcus Aurelius, Meditations, Book 6",
        "theme": "Inner Strength"
    }


@pytest.fixture
def sample_reflection():
    """Sample reflection text"""
    return """In the midst of life's challenges, Marcus Aurelius reminds us of a fundamental truth:
    our power lies not in controlling external circumstances, but in mastering our internal responses.
    This insight forms the cornerstone of Stoic philosophy and remains profoundly relevant today."""


@pytest.fixture
def sample_journaling_prompt():
    """Sample journaling prompt"""
    return "What external event are you trying to control that you should instead accept?"


@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "created_at": "2025-01-01T00:00:00Z",
        "preferences": {
            "email_enabled": True,
            "delivery_time": "07:00",
            "timezone": "America/New_York"
        }
    }


@pytest.fixture
def sample_journal_entry():
    """Sample journal entry"""
    return {
        "user_id": "test-user-123",
        "date": "2025-01-15",
        "entry": "Today I realized that worrying about things beyond my control only drains my energy.",
        "word_count": 15,
        "updated_at": "2025-01-15T10:30:00Z"
    }


@pytest.fixture
def api_gateway_event():
    """Sample API Gateway event"""
    def _make_event(method="GET", path="/user/profile", body=None, user_id="test-user-123"):
        return {
            "httpMethod": method,
            "path": path,
            "body": body,
            "headers": {
                "Content-Type": "application/json"
            },
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": user_id,
                        "email": "test@example.com"
                    }
                }
            },
            "queryStringParameters": None,
            "pathParameters": None
        }
    return _make_event


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = MagicMock()
    context.function_name = "test-function"
    context.function_version = "1"
    context.invoked_function_arn = "arn:aws:lambda:us-west-2:123456789012:function:test-function"
    context.memory_limit_in_mb = 128
    context.aws_request_id = "test-request-id"
    return context


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table"""
    table = MagicMock()
    table.table_name = "test-table"
    return table


@pytest.fixture
def mock_s3_client():
    """Mock S3 client"""
    return MagicMock()


@pytest.fixture
def mock_ses_client():
    """Mock SES client"""
    return MagicMock()


@pytest.fixture
def mock_sns_client():
    """Mock SNS client"""
    return MagicMock()


@pytest.fixture
def mock_secrets_client():
    """Mock Secrets Manager client"""
    client = MagicMock()
    client.get_secret_value.return_value = {
        'SecretString': '{"api_key": "test-anthropic-key"}'
    }
    return client


@pytest.fixture
def current_date():
    """Current date for testing"""
    return datetime(2025, 1, 15)


@pytest.fixture
def current_date_str():
    """Current date string"""
    return "2025-01-15"
