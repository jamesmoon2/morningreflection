"""
Anthropic API client for generating daily stoic reflections.

Handles prompt construction, API calls to Claude, and response parsing.
Includes comprehensive security controls for untrusted API output.
"""

import json
import logging
import re
import os
import time
from typing import Dict, List, Optional, Tuple, Any
from anthropic import Anthropic

# Import security modules
from security import SecurityValidator
from output_validator import OutputValidator
from security_alerting import SecurityAlertManager, Severity
from security_logging import SecurityLogger, ContentRedactor

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def build_reflection_prompt(quote: str, attribution: str, theme: str) -> str:
    """
    Build the prompt for Claude to generate a reflection based on a provided quote.

    Args:
        quote: The stoic quote to reflect upon
        attribution: The quote's attribution (e.g., "Marcus Aurelius - Meditations 5.1")
        theme: Monthly theme (e.g., "Discipline and Self-Improvement")

    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a thoughtful teacher of stoic philosophy. Your task is to write a daily reflection for someone interested in applying stoic wisdom to modern life.

You have been given this stoic quote to reflect upon:

"{quote}"
— {attribution}

Current Month's Theme: {theme}

Write a reflection (250-450 words) that:
- Explains the quote's meaning in accessible language
- Connects it to modern life with a concrete, relatable example
- Offers practical, actionable guidance the reader can apply today
- Uses a warm, conversational tone (imagine speaking to a thoughtful friend)
- Avoids academic jargon or overly formal language
- Feels personal and encouraging, not preachy or didactic

Format your response as JSON:
{{
  "reflection": "Your full reflection text here"
}}

Write the reflection now."""

    return prompt


def call_anthropic_api(prompt: str, api_key: str, timeout: int = 25) -> str:
    """
    Call the Anthropic API to generate a stoic reflection.

    Args:
        prompt: The formatted prompt
        api_key: Anthropic API key
        timeout: API call timeout in seconds (default: 25)

    Returns:
        The reflection text

    Raises:
        Exception: If API call fails or response is invalid
    """
    try:
        client = Anthropic(api_key=api_key)

        logger.info("Calling Anthropic API to generate reflection")

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=1.0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            timeout=timeout
        )

        # Extract text from response
        response_text = response.content[0].text

        logger.info(f"Received response from Anthropic API ({len(response_text)} chars)")

        # Parse the response
        reflection = parse_reflection_response(response_text)

        return reflection

    except Exception as e:
        logger.error(f"Error calling Anthropic API: {e}")
        raise


def parse_reflection_response(response_text: str) -> str:
    """
    Parse Claude's response and extract the reflection text.

    Handles both raw JSON and JSON wrapped in markdown code blocks.

    Args:
        response_text: Raw response text from Claude

    Returns:
        The reflection text string

    Raises:
        ValueError: If response is invalid or missing reflection field
    """
    try:
        # Try to extract JSON from markdown code blocks first
        json_match = re.search(
            r'```(?:json)?\s*(\{.*?\})\s*```',
            response_text,
            re.DOTALL
        )

        if json_match:
            json_str = json_match.group(1)
            logger.info("Found JSON in markdown code block")
        else:
            # Try to parse the entire response as JSON
            json_str = response_text.strip()
            logger.info("Attempting to parse response as raw JSON")

        # Parse JSON
        data = json.loads(json_str)

        # Validate reflection field
        if 'reflection' not in data:
            raise ValueError("Missing required field: reflection")
        if not data['reflection'] or not isinstance(data['reflection'], str):
            raise ValueError("Invalid value for field: reflection")

        logger.info("Successfully parsed Anthropic response")
        reflection_length = len(data['reflection'])
        logger.info(f"Reflection length: {reflection_length} characters")

        return data['reflection'].strip()

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from response: {e}")
        logger.error(f"Response text: {response_text[:500]}...")
        raise ValueError(f"Invalid JSON in API response: {e}")

    except Exception as e:
        logger.error(f"Error parsing Anthropic response: {e}")
        raise


def validate_attribution_format(attribution: str) -> bool:
    """
    Validate that attribution follows expected format.

    Expected format: "Author - Work Section" or "Author - Work"

    Args:
        attribution: Attribution string to validate

    Returns:
        True if valid format, False otherwise
    """
    # Should contain author name and work separated by dash
    if ' - ' not in attribution:
        return False

    parts = attribution.split(' - ')
    if len(parts) < 2:
        return False

    # Check for known authors
    known_authors = [
        'Marcus Aurelius',
        'Epictetus',
        'Seneca',
        'Musonius Rufus'
    ]

    author = parts[0].strip()
    return any(known in author for known in known_authors)


def generate_reflection_only(
    quote: str,
    attribution: str,
    theme: str,
    api_key: str
) -> Optional[str]:
    """
    Generate a reflection based on a provided quote.

    DEPRECATED: Use generate_reflection_secure() instead for enhanced security.

    Args:
        quote: The stoic quote to reflect upon
        attribution: The quote's attribution (e.g., "Marcus Aurelius - Meditations 5.1")
        theme: Monthly theme name
        api_key: Anthropic API key

    Returns:
        The reflection text, or None if generation fails
    """
    logger.warning(
        "Using deprecated generate_reflection_only(). "
        "Consider using generate_reflection_secure() for enhanced security controls."
    )

    try:
        # Validate attribution format
        if not validate_attribution_format(attribution):
            logger.warning(
                f"Attribution format may be unusual: {attribution}"
            )
            # Don't fail, just log warning

        prompt = build_reflection_prompt(quote, attribution, theme)
        reflection = call_anthropic_api(prompt, api_key)

        return reflection

    except Exception as e:
        logger.error(f"Failed to generate reflection: {e}")
        return None


def generate_reflection_secure(
    quote: str,
    attribution: str,
    theme: str,
    api_key: str,
    bucket_name: Optional[str] = None,
    config_path: Optional[str] = None,
    sns_topic_arn: Optional[str] = None
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Generate a reflection with comprehensive security controls.

    This function provides defense-in-depth security for untrusted API output:
    - Content sanitization
    - Malicious pattern detection
    - URL detection and blocking
    - Size/DoS protection
    - Statistical anomaly detection
    - Security alerting and logging

    Args:
        quote: The stoic quote to reflect upon
        attribution: The quote's attribution
        theme: Monthly theme name
        api_key: Anthropic API key
        bucket_name: S3 bucket for logging/stats (optional)
        config_path: Path to security config (optional)
        sns_topic_arn: SNS topic for alerts (optional)

    Returns:
        Tuple of (sanitized_reflection_text_or_None, security_report_dict)

    Security guarantees:
        - All output is sanitized (HTML-escaped, control chars removed)
        - Malicious patterns are blocked (XSS, scripts, etc.)
        - URLs are detected and blocked by default
        - Anomalous responses are flagged
        - All security events are logged and alerted
    """
    start_time = time.time()

    # Initialize security components
    security_logger = SecurityLogger(
        bucket_name=bucket_name,
        correlation_id=None  # Will auto-generate
    )

    try:
        # Load security configuration
        if config_path is None:
            # Try multiple paths
            for path in ['/var/task/config/security_config.json',
                        './config/security_config.json',
                        '../config/security_config.json']:
                if os.path.exists(path):
                    config_path = path
                    break

        # Initialize security validator
        security_validator = SecurityValidator(config_path)
        config = security_validator.config.config

        # Initialize alert manager
        alert_manager = SecurityAlertManager(
            config=config,
            sns_topic_arn=sns_topic_arn
        )

        # Initialize output validator
        output_validator = None
        if bucket_name and config.get('anomaly_detection', {}).get('enabled', True):
            output_validator = OutputValidator(bucket_name, config)

        logger.info(
            f"[{security_logger.correlation_id}] Starting secure reflection generation"
        )

        # Validate inputs (defense in depth - even though we control inputs)
        if not quote or not attribution or not theme:
            raise ValueError("Missing required input parameters")

        # Validate attribution format
        if not validate_attribution_format(attribution):
            logger.warning(f"Attribution format may be unusual: {attribution}")

        # Build prompt and call API
        prompt = build_reflection_prompt(quote, attribution, theme)

        logger.info("Calling Anthropic API...")
        raw_reflection = call_anthropic_api(prompt, api_key)

        if not raw_reflection:
            raise ValueError("API returned empty reflection")

        # Hash content for tracking
        content_hash = ContentRedactor.hash_content(raw_reflection)
        security_logger.log_validation_start('reflection', content_hash)

        logger.info("Starting security validation...")

        # 1. Core Security Validation & Sanitization
        is_safe, sanitized_reflection, check_results = \
            security_validator.validate_and_sanitize(
                raw_reflection,
                content_type='reflection'
            )

        # Log each security check
        for result in check_results:
            security_logger.log_security_check(
                check_name=result.check_name,
                passed=result.passed,
                severity=result.severity,
                details={
                    'message': result.details,
                    'blocked_patterns': result.blocked_patterns
                }
            )

        # Log sanitization
        if len(raw_reflection) != len(sanitized_reflection):
            modifications = ['Content sanitized']
            security_logger.log_sanitization(
                modifications=modifications,
                original_length=len(raw_reflection),
                sanitized_length=len(sanitized_reflection)
            )

        # Alert on critical failures
        critical_failures = [r for r in check_results
                           if not r.passed and r.severity == 'CRITICAL']

        for failure in critical_failures:
            alert_manager.alert_blocked_content(
                check_name=failure.check_name,
                reason=failure.details,
                blocked_patterns=failure.blocked_patterns
            )
            security_logger.log_security_incident(
                incident_type='blocked_content',
                severity='CRITICAL',
                description=f"Security check failed: {failure.check_name}",
                evidence={
                    'check': failure.check_name,
                    'details': failure.details,
                    'patterns': failure.blocked_patterns
                }
            )

        # Alert on warnings
        warning_failures = [r for r in check_results
                          if not r.passed and r.severity == 'WARNING']

        for warning in warning_failures:
            alert_manager.alert_suspicious_content(
                check_name=warning.check_name,
                reason=warning.details,
                patterns=warning.blocked_patterns
            )

        # Check if content is safe to use
        if not is_safe:
            logger.error(
                "SECURITY VIOLATION: Content failed security validation. "
                "Content has been REJECTED."
            )

            # Create security report
            duration_ms = (time.time() - start_time) * 1000
            security_logger.log_validation_complete(
                passed=False,
                duration_ms=duration_ms,
                checks_performed=len(check_results),
                issues=[r.details for r in check_results if not r.passed]
            )

            # Save audit log
            security_logger.save_audit_log_to_s3()

            # Publish metrics
            alert_manager.publish_validation_metrics(
                passed=False,
                duration_ms=duration_ms,
                checks_performed=len(check_results)
            )

            return None, {
                'success': False,
                'security_status': 'REJECTED',
                'reason': 'Failed security validation',
                'check_results': [
                    {
                        'check': r.check_name,
                        'passed': r.passed,
                        'severity': r.severity,
                        'details': r.details
                    }
                    for r in check_results
                ],
                'correlation_id': security_logger.correlation_id,
                'alert_summary': alert_manager.get_alert_summary()
            }

        # 2. Advanced Output Validation (anomaly detection, content policy)
        validation_issues = []

        if output_validator:
            logger.info("Performing advanced output validation...")
            is_valid, validation_results = output_validator.validate(
                sanitized_reflection,
                check_anomalies=True
            )

            # Log anomaly detection
            if validation_results.get('anomaly_detection'):
                anomaly_info = validation_results['anomaly_detection']
                if anomaly_info.get('is_anomaly'):
                    security_logger.log_anomaly_detection(
                        is_anomaly=True,
                        anomaly_score=anomaly_info.get('anomaly_score', 0.0),
                        anomalies=anomaly_info.get('anomalies', [])
                    )

                    alert_manager.alert_anomaly_detected(
                        anomalies=anomaly_info.get('anomalies', []),
                        anomaly_score=anomaly_info.get('anomaly_score', 0.0)
                    )

            # Collect validation issues
            if not is_valid:
                validation_issues.extend(
                    validation_results.get('issues', [])
                )

            if validation_issues:
                alert_manager.alert_validation_failure(
                    reason='; '.join(validation_issues),
                    validation_results=validation_results
                )

        # 3. Complete validation logging
        duration_ms = (time.time() - start_time) * 1000
        all_issues = [r.details for r in check_results if not r.passed] + validation_issues

        security_logger.log_validation_complete(
            passed=True,  # Passed security checks, warnings are OK
            duration_ms=duration_ms,
            checks_performed=len(check_results) + (1 if output_validator else 0),
            issues=all_issues
        )

        # Save audit log to S3
        security_logger.save_audit_log_to_s3()

        # Publish metrics
        alert_manager.publish_validation_metrics(
            passed=True,
            duration_ms=duration_ms,
            checks_performed=len(check_results)
        )

        # 4. Return sanitized, validated content
        logger.info(
            f"[{security_logger.correlation_id}] "
            f"Security validation PASSED ({duration_ms:.2f}ms)"
        )

        return sanitized_reflection, {
            'success': True,
            'security_status': 'PASSED',
            'sanitized': len(raw_reflection) != len(sanitized_reflection),
            'validation_duration_ms': duration_ms,
            'checks_performed': len(check_results),
            'check_results': [
                {
                    'check': r.check_name,
                    'passed': r.passed,
                    'severity': r.severity,
                    'details': r.details
                }
                for r in check_results
            ],
            'validation_results': validation_results if output_validator else None,
            'correlation_id': security_logger.correlation_id,
            'alert_summary': alert_manager.get_alert_summary()
        }

    except Exception as e:
        logger.error(
            f"[{security_logger.correlation_id}] "
            f"Error in secure reflection generation: {e}",
            exc_info=True
        )

        security_logger.log_security_incident(
            incident_type='generation_error',
            severity='CRITICAL',
            description=f"Failed to generate reflection: {str(e)}",
            evidence={'error': str(e)}
        )

        security_logger.save_audit_log_to_s3()

        return None, {
            'success': False,
            'security_status': 'ERROR',
            'error': str(e),
            'correlation_id': security_logger.correlation_id
        }


def build_journaling_prompt_request(reflection: str, quote: str, theme: str) -> str:
    """
    Build the prompt for Claude to generate a journaling prompt based on the reflection.

    Args:
        reflection: The generated reflection text
        quote: The stoic quote
        theme: Monthly theme

    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a thoughtful journaling coach. Based on the following Stoic reflection, create a single, thought-provoking journaling prompt that helps the reader apply the wisdom to their own life.

Reflection:
{reflection}

Quote: "{quote}"
Theme: {theme}

Generate a journaling prompt that:
1. Connects to the reflection's core message
2. Is personal and introspective
3. Is actionable (encourages concrete reflection)
4. Is 1-2 sentences long
5. Uses "you" language to make it personal

Return ONLY the journaling prompt text, no other commentary or formatting."""

    return prompt


def generate_journaling_prompt(
    reflection: str,
    quote: str,
    theme: str,
    api_key: str,
    timeout: int = 15
) -> Optional[str]:
    """
    Generate a journaling prompt based on the daily reflection.

    This is the second Anthropic API call for dual-generation.

    Args:
        reflection: The generated reflection text
        quote: The stoic quote
        theme: Monthly theme
        api_key: Anthropic API key
        timeout: API call timeout in seconds (default: 15)

    Returns:
        The journaling prompt text, or None if generation fails
    """
    try:
        logger.info("Generating journaling prompt (2nd Anthropic API call)")

        # Build prompt
        prompt = build_journaling_prompt_request(reflection, quote, theme)

        # Call API with shorter token limit
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=200,  # Shorter than reflection
            temperature=0.8,  # Slightly less random
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            timeout=timeout
        )

        # Extract text from response
        prompt_text = response.content[0].text.strip()

        logger.info(f"Generated journaling prompt ({len(prompt_text)} chars)")

        # Basic validation
        if len(prompt_text) < 20:
            logger.warning(f"Journaling prompt is very short: {len(prompt_text)} chars")
            return None

        if len(prompt_text) > 500:
            logger.warning(f"Journaling prompt is very long: {len(prompt_text)} chars, truncating")
            prompt_text = prompt_text[:500]

        return prompt_text

    except Exception as e:
        logger.error(f"Error generating journaling prompt: {e}")
        # Don't fail the entire reflection generation if prompt fails
        return None

