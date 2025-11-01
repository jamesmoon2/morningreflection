"""
Tests for lambda/security_logging.py - Security event logging and audit trails
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


# SecurityLogEntry Tests

def test_security_log_entry_to_dict():
    """Test SecurityLogEntry to_dict conversion"""
    from security_logging import SecurityLogEntry

    entry = SecurityLogEntry(
        correlation_id='test-123',
        timestamp='2025-01-15T10:00:00Z',
        event_type='security_check',
        severity='INFO',
        action='test_action',
        result='PASS',
        details={'key': 'value'},
        request_id='req-456'
    )

    entry_dict = entry.to_dict()
    assert entry_dict['correlation_id'] == 'test-123'
    assert entry_dict['event_type'] == 'security_check'
    assert entry_dict['severity'] == 'INFO'


# ContentRedactor Tests

def test_content_redactor_redacts_api_key():
    """Test that ContentRedactor redacts API keys"""
    from security_logging import ContentRedactor

    data = {
        'api_key': 'secret-api-key-12345',
        'normal_field': 'normal value'
    }

    redacted = ContentRedactor.redact_sensitive_data(data)

    assert redacted['api_key'] == '[REDACTED]'
    assert redacted['normal_field'] == 'normal value'


def test_content_redactor_redacts_sensitive_patterns():
    """Test that all sensitive patterns are redacted"""
    from security_logging import ContentRedactor

    data = {
        'token': 'auth-token',
        'password': 'my-password',
        'secret': 'my-secret',
        'credential': 'credentials',
        'safe_field': 'value'
    }

    redacted = ContentRedactor.redact_sensitive_data(data)

    assert redacted['token'] == '[REDACTED]'
    assert redacted['password'] == '[REDACTED]'
    assert redacted['secret'] == '[REDACTED]'
    assert redacted['credential'] == '[REDACTED]'
    assert redacted['safe_field'] == 'value'


def test_content_redactor_recursive_redaction():
    """Test that ContentRedactor handles nested dictionaries"""
    from security_logging import ContentRedactor

    data = {
        'outer': 'value',
        'nested': {
            'api_key': 'secret',
            'safe': 'value'
        }
    }

    redacted = ContentRedactor.redact_sensitive_data(data)

    assert redacted['nested']['api_key'] == '[REDACTED]'
    assert redacted['nested']['safe'] == 'value'


def test_content_redactor_truncates_long_strings():
    """Test that long content is truncated"""
    from security_logging import ContentRedactor

    long_content = 'x' * 600  # Longer than MAX_CONTENT_LENGTH (500)

    data = {'reflection': long_content}
    redacted = ContentRedactor.redact_sensitive_data(data)

    assert isinstance(redacted['reflection'], dict)
    assert 'preview' in redacted['reflection']
    assert 'truncated' in redacted['reflection']
    assert redacted['reflection']['truncated'] is True
    assert redacted['reflection']['full_length'] == 600


def test_content_redactor_preserves_short_strings():
    """Test that short content is not truncated"""
    from security_logging import ContentRedactor

    short_content = 'This is a short reflection.'

    data = {'reflection': short_content}
    redacted = ContentRedactor.redact_sensitive_data(data)

    assert redacted['reflection'] == short_content


def test_content_redactor_hash_content():
    """Test content hashing"""
    from security_logging import ContentRedactor

    content = 'This is some content to hash.'
    hash1 = ContentRedactor.hash_content(content)
    hash2 = ContentRedactor.hash_content(content)

    assert hash1 == hash2  # Same content should produce same hash
    assert len(hash1) == 16  # Should be first 16 chars


# SecurityLogger Tests

@patch('security_logging.boto3.client')
def test_security_logger_initialization(mock_boto3_client):
    """Test SecurityLogger initialization"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket', correlation_id='test-123')

    assert logger.bucket_name == 'test-bucket'
    assert logger.correlation_id == 'test-123'
    assert len(logger.log_entries) == 0


@patch('security_logging.boto3.client')
def test_security_logger_generates_correlation_id(mock_boto3_client):
    """Test that SecurityLogger generates correlation ID if not provided"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket')

    assert logger.correlation_id is not None
    assert isinstance(logger.correlation_id, str)
    assert len(logger.correlation_id) > 0


@patch('security_logging.boto3.client')
def test_log_security_check_pass(mock_boto3_client):
    """Test logging a passed security check"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket', correlation_id='test-123')

    logger.log_security_check(
        check_name='xss_detection',
        passed=True,
        severity='INFO',
        details={'patterns_checked': 10}
    )

    assert len(logger.log_entries) == 1
    entry = logger.log_entries[0]
    assert entry.action == 'xss_detection'
    assert entry.result == 'PASS'
    assert entry.severity == 'INFO'


@patch('security_logging.boto3.client')
def test_log_security_check_fail(mock_boto3_client):
    """Test logging a failed security check"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket', correlation_id='test-123')

    logger.log_security_check(
        check_name='malicious_pattern',
        passed=False,
        severity='WARNING',
        details={'pattern_found': '<script>'}
    )

    assert len(logger.log_entries) == 1
    entry = logger.log_entries[0]
    assert entry.result == 'FAIL'
    assert entry.severity == 'WARNING'


@patch('security_logging.boto3.client')
def test_log_security_check_redacts_sensitive_data(mock_boto3_client):
    """Test that log_security_check redacts sensitive data"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket')

    logger.log_security_check(
        check_name='test',
        passed=True,
        severity='INFO',
        details={'api_key': 'secret-key'}
    )

    entry = logger.log_entries[0]
    assert entry.details['api_key'] == '[REDACTED]'


@patch('security_logging.boto3.client')
def test_log_validation_start(mock_boto3_client):
    """Test logging validation start"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket')

    logger.log_validation_start(
        content_type='reflection',
        content_hash='abc123'
    )

    assert len(logger.log_entries) == 1
    entry = logger.log_entries[0]
    assert entry.event_type == 'validation_start'
    assert entry.details['content_type'] == 'reflection'
    assert entry.details['content_hash'] == 'abc123'


@patch('security_logging.boto3.client')
def test_log_validation_complete(mock_boto3_client):
    """Test logging validation completion"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket')

    logger.log_validation_complete(
        passed=True,
        duration_ms=123.45,
        checks_performed=10,
        issues=[]
    )

    assert len(logger.log_entries) == 1
    entry = logger.log_entries[0]
    assert entry.event_type == 'validation_complete'
    assert entry.result == 'PASS'
    assert entry.details['duration_ms'] == 123.45
    assert entry.details['checks_performed'] == 10


@patch('security_logging.boto3.client')
def test_log_sanitization(mock_boto3_client):
    """Test logging content sanitization"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket')

    logger.log_sanitization(
        modifications=['removed_html_tags', 'escaped_quotes'],
        original_length=500,
        sanitized_length=480
    )

    assert len(logger.log_entries) == 1
    entry = logger.log_entries[0]
    assert entry.event_type == 'sanitization'
    assert entry.result == 'MODIFIED'
    assert entry.details['bytes_removed'] == 20


@patch('security_logging.boto3.client')
def test_log_anomaly_detection(mock_boto3_client):
    """Test logging anomaly detection"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket')

    logger.log_anomaly_detection(
        is_anomaly=True,
        anomaly_score=4.5,
        anomalies=['word_count too high', 'unusual characters']
    )

    assert len(logger.log_entries) == 1
    entry = logger.log_entries[0]
    assert entry.event_type == 'anomaly_detection'
    assert entry.result == 'ANOMALY_DETECTED'
    assert entry.severity == 'WARNING'
    assert entry.details['anomaly_score'] == 4.5


@patch('security_logging.boto3.client')
def test_log_security_incident(mock_boto3_client):
    """Test logging security incident"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket')

    logger.log_security_incident(
        incident_type='xss_attempt',
        severity='CRITICAL',
        description='XSS script detected in user input',
        evidence={'input': '<script>alert("xss")</script>'}
    )

    assert len(logger.log_entries) == 1
    entry = logger.log_entries[0]
    assert entry.event_type == 'security_incident'
    assert entry.action == 'xss_attempt'
    assert entry.severity == 'CRITICAL'
    assert entry.result == 'INCIDENT'


@patch('security_logging.boto3.client')
def test_save_audit_log_to_s3_success(mock_boto3_client):
    """Test saving audit log to S3"""
    from security_logging import SecurityLogger

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    logger = SecurityLogger(bucket_name='test-bucket')
    logger.log_security_check('test', True, 'INFO', {})

    result = logger.save_audit_log_to_s3()

    assert result is True
    mock_s3.put_object.assert_called_once()
    call_args = mock_s3.put_object.call_args
    assert call_args[1]['Bucket'] == 'test-bucket'
    assert 'security/audit_logs/' in call_args[1]['Key']


@patch('security_logging.boto3.client')
def test_save_audit_log_to_s3_no_bucket(mock_boto3_client):
    """Test saving audit log when no bucket configured"""
    from security_logging import SecurityLogger

    logger = SecurityLogger()  # No bucket
    logger.log_security_check('test', True, 'INFO', {})

    result = logger.save_audit_log_to_s3()

    assert result is False


@patch('security_logging.boto3.client')
def test_save_audit_log_to_s3_no_entries(mock_boto3_client):
    """Test saving audit log when no entries to save"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket')

    result = logger.save_audit_log_to_s3()

    assert result is True


@patch('security_logging.boto3.client')
def test_save_audit_log_to_s3_failure(mock_boto3_client):
    """Test saving audit log when S3 upload fails"""
    from security_logging import SecurityLogger

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3
    mock_s3.put_object.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied'}},
        'PutObject'
    )

    logger = SecurityLogger(bucket_name='test-bucket')
    logger.log_security_check('test', True, 'INFO', {})

    result = logger.save_audit_log_to_s3()

    assert result is False


@patch('security_logging.boto3.client')
def test_get_summary_no_entries(mock_boto3_client):
    """Test getting summary with no log entries"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket', correlation_id='test-123')

    summary = logger.get_summary()

    assert summary['correlation_id'] == 'test-123'
    assert summary['total_events'] == 0
    assert summary['by_type'] == {}


@patch('security_logging.boto3.client')
def test_get_summary_with_entries(mock_boto3_client):
    """Test getting summary with multiple log entries"""
    from security_logging import SecurityLogger

    logger = SecurityLogger(bucket_name='test-bucket')

    logger.log_security_check('check1', True, 'INFO', {})
    logger.log_security_check('check2', False, 'WARNING', {})
    logger.log_validation_start('reflection', 'hash123')

    summary = logger.get_summary()

    assert summary['total_events'] == 3
    assert summary['by_type']['security_check'] == 2
    assert summary['by_type']['validation_start'] == 1
    assert summary['by_severity']['INFO'] >= 1
    assert summary['by_severity']['WARNING'] == 1
    assert summary['by_result']['PASS'] == 1
    assert summary['by_result']['FAIL'] == 1
