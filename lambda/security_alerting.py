"""
Security alerting system for monitoring and notification.

Provides:
- SNS-based alerting for security events
- CloudWatch metrics publishing
- Severity-based routing
- Alert aggregation and deduplication
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()


class Severity(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_type: str
    severity: str
    message: str
    details: Dict[str, Any]
    timestamp: str
    source: str = "api_output_validator"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class CloudWatchMetrics:
    """Publishes security metrics to CloudWatch."""

    def __init__(self, namespace: str = "StoicReflections/Security"):
        """
        Initialize CloudWatch metrics publisher.

        Args:
            namespace: CloudWatch metrics namespace
        """
        self.namespace = namespace
        self.cloudwatch = boto3.client('cloudwatch')

    def publish_security_event(
        self,
        event_type: str,
        severity: str,
        value: float = 1.0,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Publish a security event metric to CloudWatch.

        Args:
            event_type: Type of security event
            severity: Event severity (INFO, WARNING, CRITICAL)
            value: Metric value (default 1.0 for count)
            dimensions: Additional metric dimensions
        """
        try:
            metric_data = [{
                'MetricName': event_type,
                'Value': value,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow(),
                'Dimensions': [
                    {'Name': 'Severity', 'Value': severity}
                ]
            }]

            # Add custom dimensions
            if dimensions:
                for key, value in dimensions.items():
                    metric_data[0]['Dimensions'].append({
                        'Name': key,
                        'Value': str(value)
                    })

            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )

            logger.info(f"Published CloudWatch metric: {event_type} ({severity})")

        except ClientError as e:
            logger.error(f"Error publishing CloudWatch metric: {e}")

    def publish_validation_metrics(
        self,
        passed: bool,
        duration_ms: float,
        checks_performed: int
    ) -> None:
        """
        Publish validation performance metrics.

        Args:
            passed: Whether validation passed
            duration_ms: Validation duration in milliseconds
            checks_performed: Number of checks performed
        """
        try:
            metric_data = [
                {
                    'MetricName': 'ValidationDuration',
                    'Value': duration_ms,
                    'Unit': 'Milliseconds',
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'ValidationResult',
                    'Value': 1.0 if passed else 0.0,
                    'Unit': 'None',
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'SecurityChecksPerformed',
                    'Value': float(checks_performed),
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                }
            ]

            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )

            logger.info("Published validation performance metrics")

        except ClientError as e:
            logger.error(f"Error publishing validation metrics: {e}")


class SNSAlerting:
    """Sends security alerts via SNS."""

    def __init__(self, topic_arn: Optional[str] = None):
        """
        Initialize SNS alerting.

        Args:
            topic_arn: SNS topic ARN (defaults to env var SECURITY_ALERT_TOPIC_ARN)
        """
        self.topic_arn = topic_arn or os.environ.get('SECURITY_ALERT_TOPIC_ARN')
        self.sns_client = boto3.client('sns')

    def send_alert(
        self,
        event: SecurityEvent,
        include_details: bool = True
    ) -> bool:
        """
        Send security alert via SNS.

        Args:
            event: SecurityEvent to send
            include_details: Whether to include full details in message

        Returns:
            True if alert sent successfully
        """
        if not self.topic_arn:
            logger.warning("SNS topic ARN not configured, alert not sent")
            return False

        try:
            # Format message
            subject = self._format_subject(event)
            message = self._format_message(event, include_details)

            # Send to SNS
            response = self.sns_client.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message,
                MessageAttributes={
                    'severity': {
                        'DataType': 'String',
                        'StringValue': event.severity
                    },
                    'event_type': {
                        'DataType': 'String',
                        'StringValue': event.event_type
                    }
                }
            )

            logger.info(
                f"Sent security alert via SNS: {event.event_type} "
                f"(MessageId: {response['MessageId']})"
            )
            return True

        except ClientError as e:
            logger.error(f"Error sending SNS alert: {e}")
            return False

    def _format_subject(self, event: SecurityEvent) -> str:
        """Format alert subject line."""
        emoji = {
            'CRITICAL': '🚨',
            'WARNING': '⚠️',
            'INFO': 'ℹ️'
        }.get(event.severity, '')

        return f"{emoji} Security Alert [{event.severity}]: {event.event_type}"

    def _format_message(self, event: SecurityEvent, include_details: bool) -> str:
        """Format alert message body."""
        lines = [
            "SECURITY ALERT",
            "=" * 70,
            f"Event Type: {event.event_type}",
            f"Severity: {event.severity}",
            f"Timestamp: {event.timestamp}",
            f"Source: {event.source}",
            "",
            "Message:",
            event.message,
        ]

        if include_details and event.details:
            lines.extend([
                "",
                "Details:",
                json.dumps(event.details, indent=2)
            ])

        lines.extend([
            "",
            "=" * 70,
            "This is an automated security alert from the Stoic Reflections system."
        ])

        return "\n".join(lines)


class SecurityAlertManager:
    """Manages security alerts with deduplication and routing."""

    def __init__(
        self,
        config: Dict[str, Any],
        sns_topic_arn: Optional[str] = None
    ):
        """
        Initialize security alert manager.

        Args:
            config: Security configuration dictionary
            sns_topic_arn: SNS topic ARN for alerts
        """
        self.config = config
        self.metrics = CloudWatchMetrics()
        self.sns = SNSAlerting(sns_topic_arn)
        self.alert_history: List[SecurityEvent] = []

    def alert(
        self,
        event_type: str,
        severity: Severity,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Process and send a security alert.

        Args:
            event_type: Type of security event
            severity: Event severity
            message: Human-readable message
            details: Additional event details
        """
        # Check if alerting is enabled
        if not self.config.get('alerting', {}).get('enabled', True):
            logger.info(f"Alerting disabled, suppressing {event_type} alert")
            return

        # Create event
        event = SecurityEvent(
            event_type=event_type,
            severity=severity.value,
            message=message,
            details=details or {},
            timestamp=datetime.utcnow().isoformat()
        )

        # Store in history
        self.alert_history.append(event)

        # Log the event
        log_level = {
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'CRITICAL': logging.ERROR
        }.get(severity.value, logging.INFO)

        logger.log(log_level, f"SECURITY EVENT [{severity.value}]: {message}")

        # Publish to CloudWatch
        self.metrics.publish_security_event(
            event_type=event_type,
            severity=severity.value,
            dimensions={'event': event_type}
        )

        # Send SNS alert if configured for this severity
        should_alert = self._should_send_sns_alert(event_type, severity)
        if should_alert:
            self.sns.send_alert(event)

    def _should_send_sns_alert(
        self,
        event_type: str,
        severity: Severity
    ) -> bool:
        """
        Determine if SNS alert should be sent based on configuration.

        Args:
            event_type: Type of event
            severity: Event severity

        Returns:
            True if alert should be sent
        """
        alerting_config = self.config.get('alerting', {})

        # Check if this event type should trigger alerts
        if event_type == 'blocked_content':
            return alerting_config.get('alert_on_blocked_content', True)
        elif event_type == 'suspicious_content':
            return alerting_config.get('alert_on_suspicious_content', True)
        elif event_type == 'validation_failure':
            return alerting_config.get('alert_on_validation_failure', False)
        elif event_type == 'anomaly_detected':
            return alerting_config.get('alert_on_anomaly', True)

        # Default: send for WARNING and CRITICAL
        return severity in [Severity.WARNING, Severity.CRITICAL]

    def alert_blocked_content(
        self,
        check_name: str,
        reason: str,
        blocked_patterns: Optional[List[str]] = None
    ) -> None:
        """
        Alert for blocked malicious content.

        Args:
            check_name: Name of security check that failed
            reason: Reason for blocking
            blocked_patterns: List of detected malicious patterns
        """
        self.alert(
            event_type='blocked_content',
            severity=Severity.CRITICAL,
            message=f"Blocked malicious content in {check_name}: {reason}",
            details={
                'check_name': check_name,
                'reason': reason,
                'blocked_patterns': blocked_patterns or [],
                'action_taken': 'Content rejected'
            }
        )

    def alert_suspicious_content(
        self,
        check_name: str,
        reason: str,
        patterns: Optional[List[str]] = None
    ) -> None:
        """
        Alert for suspicious but not blocked content.

        Args:
            check_name: Name of security check
            reason: Reason for suspicion
            patterns: List of suspicious patterns
        """
        self.alert(
            event_type='suspicious_content',
            severity=Severity.WARNING,
            message=f"Suspicious content detected in {check_name}: {reason}",
            details={
                'check_name': check_name,
                'reason': reason,
                'patterns': patterns or [],
                'action_taken': 'Content allowed with warning'
            }
        )

    def alert_validation_failure(
        self,
        reason: str,
        validation_results: Dict[str, Any]
    ) -> None:
        """
        Alert for validation failures.

        Args:
            reason: Reason for failure
            validation_results: Full validation results
        """
        self.alert(
            event_type='validation_failure',
            severity=Severity.WARNING,
            message=f"Content validation failed: {reason}",
            details=validation_results
        )

    def alert_anomaly_detected(
        self,
        anomalies: List[str],
        anomaly_score: float
    ) -> None:
        """
        Alert for statistical anomalies.

        Args:
            anomalies: List of detected anomalies
            anomaly_score: Numeric anomaly score
        """
        self.alert(
            event_type='anomaly_detected',
            severity=Severity.WARNING,
            message=f"Statistical anomaly detected in API response",
            details={
                'anomalies': anomalies,
                'anomaly_score': anomaly_score,
                'action_taken': 'Content allowed but flagged'
            }
        )

    def publish_validation_metrics(
        self,
        passed: bool,
        duration_ms: float,
        checks_performed: int
    ) -> None:
        """
        Publish validation performance metrics to CloudWatch.

        Args:
            passed: Whether validation passed
            duration_ms: Validation duration
            checks_performed: Number of checks performed
        """
        self.metrics.publish_validation_metrics(
            passed=passed,
            duration_ms=duration_ms,
            checks_performed=checks_performed
        )

    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get summary of alerts from current session.

        Returns:
            Dictionary with alert statistics
        """
        if not self.alert_history:
            return {
                'total_alerts': 0,
                'by_severity': {},
                'by_type': {}
            }

        by_severity = {}
        by_type = {}

        for event in self.alert_history:
            # Count by severity
            by_severity[event.severity] = by_severity.get(event.severity, 0) + 1

            # Count by type
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1

        return {
            'total_alerts': len(self.alert_history),
            'by_severity': by_severity,
            'by_type': by_type,
            'events': [e.to_dict() for e in self.alert_history[-10:]]  # Last 10
        }
