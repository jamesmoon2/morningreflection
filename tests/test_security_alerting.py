"""
Tests for lambda/security_alerting.py - Security alerting and CloudWatch metrics
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


# SecurityEvent Tests

def test_security_event_to_dict():
    """Test SecurityEvent to_dict conversion"""
    from security_alerting import SecurityEvent

    event = SecurityEvent(
        event_type='xss_detected',
        severity='CRITICAL',
        message='XSS pattern detected',
        details={'pattern': '<script>'},
        timestamp='2025-01-15T10:00:00Z',
        source='test'
    )

    event_dict = event.to_dict()
    assert event_dict['event_type'] == 'xss_detected'
    assert event_dict['severity'] == 'CRITICAL'


# CloudWatchMetrics Tests

@patch('security_alerting.boto3.client')
def test_cloudwatch_metrics_publish_security_event(mock_boto3_client):
    """Test publishing security event to CloudWatch"""
    from security_alerting import CloudWatchMetrics

    mock_cloudwatch = MagicMock()
    mock_boto3_client.return_value = mock_cloudwatch

    metrics = CloudWatchMetrics()
    metrics.publish_security_event(
        event_type='xss_detected',
        severity='CRITICAL',
        value=1.0
    )

    mock_cloudwatch.put_metric_data.assert_called_once()
    call_args = mock_cloudwatch.put_metric_data.call_args
    assert call_args[1]['Namespace'] == 'StoicReflections/Security'


@patch('security_alerting.boto3.client')
def test_cloudwatch_metrics_with_custom_dimensions(mock_boto3_client):
    """Test publishing metrics with custom dimensions"""
    from security_alerting import CloudWatchMetrics

    mock_cloudwatch = MagicMock()
    mock_boto3_client.return_value = mock_cloudwatch

    metrics = CloudWatchMetrics()
    metrics.publish_security_event(
        event_type='test_event',
        severity='INFO',
        dimensions={'environment': 'test'}
    )

    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]['MetricData'][0]
    assert len(metric_data['Dimensions']) == 2  # Severity + custom


@patch('security_alerting.boto3.client')
def test_cloudwatch_metrics_publish_validation_metrics(mock_boto3_client):
    """Test publishing validation performance metrics"""
    from security_alerting import CloudWatchMetrics

    mock_cloudwatch = MagicMock()
    mock_boto3_client.return_value = mock_cloudwatch

    metrics = CloudWatchMetrics()
    metrics.publish_validation_metrics(
        passed=True,
        duration_ms=123.45,
        checks_performed=10
    )

    mock_cloudwatch.put_metric_data.assert_called_once()
    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]['MetricData']
    assert len(metric_data) == 3  # Duration, Result, ChecksPerformed


# SNSAlerting Tests

@patch('security_alerting.boto3.client')
def test_sns_alerting_send_alert_success(mock_boto3_client):
    """Test sending alert via SNS"""
    from security_alerting import SNSAlerting, SecurityEvent

    mock_sns = MagicMock()
    mock_boto3_client.return_value = mock_sns
    mock_sns.publish.return_value = {'MessageId': 'msg-123'}

    alerting = SNSAlerting(topic_arn='arn:aws:sns:us-east-1:123456789:test')

    event = SecurityEvent(
        event_type='test_event',
        severity='WARNING',
        message='Test alert',
        details={},
        timestamp=datetime.utcnow().isoformat()
    )

    result = alerting.send_alert(event)

    assert result is True
    mock_sns.publish.assert_called_once()


@patch('security_alerting.boto3.client')
def test_sns_alerting_no_topic_arn(mock_boto3_client):
    """Test sending alert without configured topic ARN"""
    from security_alerting import SNSAlerting, SecurityEvent

    alerting = SNSAlerting()  # No topic ARN

    event = SecurityEvent(
        event_type='test',
        severity='INFO',
        message='Test',
        details={},
        timestamp=datetime.utcnow().isoformat()
    )

    result = alerting.send_alert(event)

    assert result is False


@patch('security_alerting.boto3.client')
def test_sns_alerting_format_subject(mock_boto3_client):
    """Test alert subject formatting"""
    from security_alerting import SNSAlerting, SecurityEvent

    alerting = SNSAlerting(topic_arn='arn:aws:sns:test')

    critical_event = SecurityEvent(
        event_type='xss',
        severity='CRITICAL',
        message='Test',
        details={},
        timestamp=datetime.utcnow().isoformat()
    )

    subject = alerting._format_subject(critical_event)
    assert 'CRITICAL' in subject
    assert 'xss' in subject


@patch('security_alerting.boto3.client')
def test_sns_alerting_failure(mock_boto3_client):
    """Test handling SNS publish failure"""
    from security_alerting import SNSAlerting, SecurityEvent

    mock_sns = MagicMock()
    mock_boto3_client.return_value = mock_sns
    mock_sns.publish.side_effect = ClientError(
        {'Error': {'Code': 'InvalidParameter'}},
        'Publish'
    )

    alerting = SNSAlerting(topic_arn='arn:aws:sns:test')

    event = SecurityEvent(
        event_type='test',
        severity='INFO',
        message='Test',
        details={},
        timestamp=datetime.utcnow().isoformat()
    )

    result = alerting.send_alert(event)

    assert result is False


# SecurityAlertManager Tests

@patch('security_alerting.boto3.client')
def test_security_alert_manager_alert(mock_boto3_client):
    """Test creating and processing an alert"""
    from security_alerting import SecurityAlertManager, Severity

    config = {'alerting': {'enabled': True}}

    manager = SecurityAlertManager(config)
    manager.alert(
        event_type='test_event',
        severity=Severity.WARNING,
        message='Test alert message',
        details={'key': 'value'}
    )

    assert len(manager.alert_history) == 1
    assert manager.alert_history[0].event_type == 'test_event'


@patch('security_alerting.boto3.client')
def test_security_alert_manager_alerting_disabled(mock_boto3_client):
    """Test that alerts are suppressed when disabled"""
    from security_alerting import SecurityAlertManager, Severity

    config = {'alerting': {'enabled': False}}

    manager = SecurityAlertManager(config)
    manager.alert(
        event_type='test',
        severity=Severity.INFO,
        message='Test',
        details={}
    )

    assert len(manager.alert_history) == 0


@patch('security_alerting.boto3.client')
def test_alert_blocked_content(mock_boto3_client):
    """Test alert_blocked_content method"""
    from security_alerting import SecurityAlertManager

    config = {'alerting': {'enabled': True, 'alert_on_blocked_content': True}}

    manager = SecurityAlertManager(config)
    manager.alert_blocked_content(
        check_name='xss_check',
        reason='Script tag detected',
        blocked_patterns=['<script>']
    )

    assert len(manager.alert_history) == 1
    event = manager.alert_history[0]
    assert event.event_type == 'blocked_content'
    assert event.severity == 'CRITICAL'


@patch('security_alerting.boto3.client')
def test_alert_suspicious_content(mock_boto3_client):
    """Test alert_suspicious_content method"""
    from security_alerting import SecurityAlertManager

    config = {'alerting': {'enabled': True}}

    manager = SecurityAlertManager(config)
    manager.alert_suspicious_content(
        check_name='pattern_check',
        reason='Unusual patterns',
        patterns=['unusual-pattern']
    )

    assert len(manager.alert_history) == 1
    event = manager.alert_history[0]
    assert event.event_type == 'suspicious_content'
    assert event.severity == 'WARNING'


@patch('security_alerting.boto3.client')
def test_alert_validation_failure(mock_boto3_client):
    """Test alert_validation_failure method"""
    from security_alerting import SecurityAlertManager

    config = {'alerting': {'enabled': True}}

    manager = SecurityAlertManager(config)
    manager.alert_validation_failure(
        reason='Content policy violation',
        validation_results={'issues': ['too_long']}
    )

    assert len(manager.alert_history) == 1
    event = manager.alert_history[0]
    assert event.event_type == 'validation_failure'


@patch('security_alerting.boto3.client')
def test_alert_anomaly_detected(mock_boto3_client):
    """Test alert_anomaly_detected method"""
    from security_alerting import SecurityAlertManager

    config = {'alerting': {'enabled': True}}

    manager = SecurityAlertManager(config)
    manager.alert_anomaly_detected(
        anomalies=['word_count high'],
        anomaly_score=4.5
    )

    assert len(manager.alert_history) == 1
    event = manager.alert_history[0]
    assert event.event_type == 'anomaly_detected'


@patch('security_alerting.boto3.client')
def test_get_alert_summary(mock_boto3_client):
    """Test get_alert_summary method"""
    from security_alerting import SecurityAlertManager, Severity

    config = {'alerting': {'enabled': True}}

    manager = SecurityAlertManager(config)
    manager.alert('event1', Severity.WARNING, 'Test 1', {})
    manager.alert('event2', Severity.CRITICAL, 'Test 2', {})

    summary = manager.get_alert_summary()

    assert summary['total_alerts'] == 2
    assert summary['by_severity']['WARNING'] == 1
    assert summary['by_severity']['CRITICAL'] == 1


@patch('security_alerting.boto3.client')
def test_get_alert_summary_empty(mock_boto3_client):
    """Test get_alert_summary with no alerts"""
    from security_alerting import SecurityAlertManager

    config = {'alerting': {'enabled': True}}

    manager = SecurityAlertManager(config)
    summary = manager.get_alert_summary()

    assert summary['total_alerts'] == 0
    assert summary['by_severity'] == {}


@patch('security_alerting.boto3.client')
def test_severity_enum():
    """Test Severity enum"""
    from security_alerting import Severity

    assert Severity.INFO.value == 'INFO'
    assert Severity.WARNING.value == 'WARNING'
    assert Severity.CRITICAL.value == 'CRITICAL'
