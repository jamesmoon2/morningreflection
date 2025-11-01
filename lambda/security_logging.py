"""
Security logging module for comprehensive audit trails.

Provides:
- Structured security event logging
- PII/sensitive data redaction
- Audit trail maintenance
- Correlation ID tracking
- Log aggregation to S3
"""

import json
import logging
import os
import hashlib
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()


@dataclass
class SecurityLogEntry:
    """Structured security log entry."""
    correlation_id: str
    timestamp: str
    event_type: str
    severity: str
    action: str
    result: str
    details: Dict[str, Any]
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class ContentRedactor:
    """Redacts sensitive information from logs."""

    # Patterns that might contain sensitive data
    SENSITIVE_PATTERNS = [
        'api_key',
        'token',
        'password',
        'secret',
        'credential'
    ]

    # Maximum content length to log (characters)
    MAX_CONTENT_LENGTH = 500

    @staticmethod
    def redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive information from data dictionary.

        Args:
            data: Dictionary potentially containing sensitive data

        Returns:
            Dictionary with sensitive data redacted
        """
        redacted = {}

        for key, value in data.items():
            key_lower = key.lower()

            # Check if key indicates sensitive data
            if any(pattern in key_lower for pattern in ContentRedactor.SENSITIVE_PATTERNS):
                redacted[key] = '[REDACTED]'
            elif isinstance(value, dict):
                # Recursively redact nested dicts
                redacted[key] = ContentRedactor.redact_sensitive_data(value)
            elif isinstance(value, str):
                # Truncate long strings and hash them
                redacted[key] = ContentRedactor._truncate_and_hash(value, key)
            else:
                redacted[key] = value

        return redacted

    @staticmethod
    def _truncate_and_hash(content: str, field_name: str) -> Any:
        """
        Truncate long content and provide hash for verification.

        Args:
            content: Content to process
            field_name: Name of the field

        Returns:
            Truncated content or hash info
        """
        # For certain fields, include truncated preview
        if field_name in ['reflection', 'quote', 'text', 'content', 'message']:
            if len(content) > ContentRedactor.MAX_CONTENT_LENGTH:
                preview = content[:ContentRedactor.MAX_CONTENT_LENGTH]
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                return {
                    'preview': preview + '...',
                    'full_length': len(content),
                    'hash': content_hash,
                    'truncated': True
                }

        return content

    @staticmethod
    def hash_content(content: str) -> str:
        """
        Create SHA256 hash of content for tracking.

        Args:
            content: Content to hash

        Returns:
            Hex digest of hash (first 16 chars)
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class SecurityLogger:
    """Structured security logger with audit trail."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """
        Initialize security logger.

        Args:
            bucket_name: S3 bucket for log aggregation
            correlation_id: Correlation ID for request tracking
        """
        self.bucket_name = bucket_name
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.s3_client = boto3.client('s3') if bucket_name else None
        self.log_entries: List[SecurityLogEntry] = []
        self.redactor = ContentRedactor()

    def log_security_check(
        self,
        check_name: str,
        passed: bool,
        severity: str,
        details: Dict[str, Any]
    ) -> None:
        """
        Log a security check result.

        Args:
            check_name: Name of the security check
            passed: Whether check passed
            severity: Severity level (INFO, WARNING, CRITICAL)
            details: Additional details about the check
        """
        # Redact sensitive data
        safe_details = self.redactor.redact_sensitive_data(details)

        entry = SecurityLogEntry(
            correlation_id=self.correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            event_type='security_check',
            severity=severity,
            action=check_name,
            result='PASS' if passed else 'FAIL',
            details=safe_details,
            request_id=os.environ.get('AWS_REQUEST_ID')
        )

        self.log_entries.append(entry)

        # Log to CloudWatch via standard logger
        log_level = {
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'CRITICAL': logging.ERROR
        }.get(severity, logging.INFO)

        logger.log(
            log_level,
            f"[{self.correlation_id}] Security Check: {check_name} - "
            f"{'PASSED' if passed else 'FAILED'}",
            extra={'security_log': entry.to_dict()}
        )

    def log_validation_start(
        self,
        content_type: str,
        content_hash: str
    ) -> None:
        """
        Log start of validation process.

        Args:
            content_type: Type of content being validated
            content_hash: Hash of content for tracking
        """
        entry = SecurityLogEntry(
            correlation_id=self.correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            event_type='validation_start',
            severity='INFO',
            action='begin_validation',
            result='STARTED',
            details={
                'content_type': content_type,
                'content_hash': content_hash
            },
            request_id=os.environ.get('AWS_REQUEST_ID')
        )

        self.log_entries.append(entry)
        logger.info(
            f"[{self.correlation_id}] Starting validation for {content_type}",
            extra={'security_log': entry.to_dict()}
        )

    def log_validation_complete(
        self,
        passed: bool,
        duration_ms: float,
        checks_performed: int,
        issues: List[str]
    ) -> None:
        """
        Log completion of validation process.

        Args:
            passed: Whether validation passed overall
            duration_ms: Duration in milliseconds
            checks_performed: Number of checks performed
            issues: List of issues found
        """
        entry = SecurityLogEntry(
            correlation_id=self.correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            event_type='validation_complete',
            severity='INFO' if passed else 'WARNING',
            action='complete_validation',
            result='PASS' if passed else 'FAIL',
            details={
                'duration_ms': duration_ms,
                'checks_performed': checks_performed,
                'issues_count': len(issues),
                'issues': issues[:10]  # First 10 issues
            },
            request_id=os.environ.get('AWS_REQUEST_ID')
        )

        self.log_entries.append(entry)
        logger.info(
            f"[{self.correlation_id}] Validation complete: "
            f"{'PASSED' if passed else 'FAILED'} "
            f"({duration_ms:.2f}ms, {checks_performed} checks)",
            extra={'security_log': entry.to_dict()}
        )

    def log_sanitization(
        self,
        modifications: List[str],
        original_length: int,
        sanitized_length: int
    ) -> None:
        """
        Log content sanitization.

        Args:
            modifications: List of modifications made
            original_length: Original content length
            sanitized_length: Sanitized content length
        """
        entry = SecurityLogEntry(
            correlation_id=self.correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            event_type='sanitization',
            severity='INFO',
            action='sanitize_content',
            result='MODIFIED' if modifications else 'UNCHANGED',
            details={
                'modifications': modifications,
                'original_length': original_length,
                'sanitized_length': sanitized_length,
                'bytes_removed': original_length - sanitized_length
            },
            request_id=os.environ.get('AWS_REQUEST_ID')
        )

        self.log_entries.append(entry)

        if modifications:
            logger.info(
                f"[{self.correlation_id}] Content sanitized: "
                f"{', '.join(modifications)}",
                extra={'security_log': entry.to_dict()}
            )

    def log_anomaly_detection(
        self,
        is_anomaly: bool,
        anomaly_score: float,
        anomalies: List[str]
    ) -> None:
        """
        Log anomaly detection results.

        Args:
            is_anomaly: Whether anomaly was detected
            anomaly_score: Numeric anomaly score
            anomalies: List of anomalies detected
        """
        entry = SecurityLogEntry(
            correlation_id=self.correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            event_type='anomaly_detection',
            severity='WARNING' if is_anomaly else 'INFO',
            action='detect_anomalies',
            result='ANOMALY_DETECTED' if is_anomaly else 'NORMAL',
            details={
                'anomaly_score': anomaly_score,
                'anomalies': anomalies
            },
            request_id=os.environ.get('AWS_REQUEST_ID')
        )

        self.log_entries.append(entry)

        if is_anomaly:
            logger.warning(
                f"[{self.correlation_id}] Anomaly detected: "
                f"score={anomaly_score:.2f}, anomalies={len(anomalies)}",
                extra={'security_log': entry.to_dict()}
            )

    def log_security_incident(
        self,
        incident_type: str,
        severity: str,
        description: str,
        evidence: Dict[str, Any]
    ) -> None:
        """
        Log a security incident.

        Args:
            incident_type: Type of incident
            severity: Severity level
            description: Description of incident
            evidence: Evidence data
        """
        safe_evidence = self.redactor.redact_sensitive_data(evidence)

        entry = SecurityLogEntry(
            correlation_id=self.correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            event_type='security_incident',
            severity=severity,
            action=incident_type,
            result='INCIDENT',
            details={
                'description': description,
                'evidence': safe_evidence
            },
            request_id=os.environ.get('AWS_REQUEST_ID')
        )

        self.log_entries.append(entry)

        logger.error(
            f"[{self.correlation_id}] SECURITY INCIDENT [{severity}]: "
            f"{incident_type} - {description}",
            extra={'security_log': entry.to_dict()}
        )

    def save_audit_log_to_s3(self) -> bool:
        """
        Save accumulated audit log to S3.

        Returns:
            True if successful, False otherwise
        """
        if not self.bucket_name or not self.s3_client:
            logger.debug("S3 bucket not configured, skipping audit log save")
            return False

        if not self.log_entries:
            logger.debug("No log entries to save")
            return True

        try:
            # Create log file with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            key = f"security/audit_logs/{timestamp}_{self.correlation_id}.json"

            # Prepare log data
            log_data = {
                'correlation_id': self.correlation_id,
                'timestamp': datetime.utcnow().isoformat(),
                'entry_count': len(self.log_entries),
                'entries': [entry.to_dict() for entry in self.log_entries]
            }

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(log_data, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )

            logger.info(
                f"[{self.correlation_id}] Saved audit log to S3: {key} "
                f"({len(self.log_entries)} entries)"
            )
            return True

        except ClientError as e:
            logger.error(f"Error saving audit log to S3: {e}")
            return False

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of logged events.

        Returns:
            Dictionary with event statistics
        """
        if not self.log_entries:
            return {
                'correlation_id': self.correlation_id,
                'total_events': 0,
                'by_type': {},
                'by_severity': {},
                'by_result': {}
            }

        by_type = {}
        by_severity = {}
        by_result = {}

        for entry in self.log_entries:
            by_type[entry.event_type] = by_type.get(entry.event_type, 0) + 1
            by_severity[entry.severity] = by_severity.get(entry.severity, 0) + 1
            by_result[entry.result] = by_result.get(entry.result, 0) + 1

        return {
            'correlation_id': self.correlation_id,
            'total_events': len(self.log_entries),
            'by_type': by_type,
            'by_severity': by_severity,
            'by_result': by_result
        }
