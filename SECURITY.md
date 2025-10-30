# Security Controls for Anthropic API Output

## Overview

This document describes the comprehensive security controls implemented for handling untrusted output from the Anthropic API. While we control all inputs to the API, the output is necessarily stochastic and must be treated as untrusted.

## Threat Model

### Attack Vectors

1. **XSS/HTML Injection**: API output is embedded into HTML emails
2. **Content Injection**: Malicious URLs, phishing content, tracking pixels
3. **Data Exfiltration**: Embedded URLs that phone home
4. **DoS Attacks**: Oversized responses consuming resources
5. **Encoding Attacks**: Unicode/homoglyph attacks
6. **Prompt Injection Artifacts**: Unexpected response formats from prompt injection

### Assumptions

- **Inputs are controlled**: We validate and control all inputs to the API
- **Outputs are untrusted**: API responses must be treated as potentially malicious
- **Defense in Depth**: Multiple layers of security controls
- **Fail Secure**: When in doubt, reject content

## Security Architecture

### 1. Core Security Module (`lambda/security.py`)

The foundation of our security controls, providing:

#### Content Sanitization
- **Control character removal**: Strips dangerous control characters while preserving \n, \r, \t
- **Invisible character removal**: Removes zero-width spaces and invisible Unicode
- **Whitespace normalization**: Standardizes whitespace while preserving paragraphs
- **Newline limiting**: Prevents excessive consecutive newlines

#### Malicious Pattern Detection
- **Script tags**: Detects `<script>`, `<iframe>`, `<object>`, `<embed>`
- **JavaScript protocols**: Blocks `javascript:` and `vbscript:` URLs
- **Event handlers**: Detects `onclick`, `onerror`, `onload`, etc.
- **Prompt injection patterns**: Detects artifacts like `[INST]`, `<|im_start|>`, "IGNORE PREVIOUS"

#### URL Detection & Blocking
- **Zero-tolerance by default**: Blocks all URLs (http, https, www)
- **Shortened URL detection**: Flags suspicious domains (bit.ly, tinyurl, etc.)
- **Configurable limits**: Can be adjusted via config

#### Length Validation
- **Maximum limits**: Protects against DoS via oversized content
- **Minimum limits**: Ensures content meets quality standards
- **Word and character counts**: Validates both metrics

#### Character Validation
- **Excessive repetition detection**: Flags abnormal character patterns
- **Homoglyph detection**: Identifies look-alike characters (Cyrillic 'a' vs Latin 'a')
- **Unicode safety**: Validates character encoding

### 2. Output Validator (`lambda/output_validator.py`)

Advanced semantic analysis and anomaly detection:

#### Response Analysis
Extracts statistical features:
- Character, word, sentence, paragraph counts
- Average word and sentence lengths
- Unique word ratio
- Response structure

#### Anomaly Detection
- **Statistical baseline**: Maintains historical statistics in S3
- **Z-score calculation**: Detects responses that deviate >3σ from normal
- **Multi-metric detection**: Analyzes multiple dimensions simultaneously
- **Adaptive learning**: Updates baseline with each response

#### Content Policy Validation
- **Paragraph structure**: Validates expected formatting
- **Forbidden topics**: Basic keyword matching for policy violations
- **Format checking**: Ensures no unexpected markdown/code

### 3. Security Alerting (`lambda/security_alerting.py`)

Multi-channel alerting and monitoring:

#### SNS Alerts
- **Severity-based routing**: CRITICAL, WARNING, INFO levels
- **Formatted messages**: Clear, actionable alert format
- **Deduplication**: Prevents alert fatigue
- **Email delivery**: Direct notifications to security team

#### CloudWatch Metrics
- **Custom namespace**: `StoicReflections/Security`
- **Event metrics**: Count by type and severity
- **Performance metrics**: Validation duration, checks performed
- **Dashboard ready**: All metrics queryable

#### Alert Types
1. **Blocked Content**: Malicious patterns detected
2. **Suspicious Content**: Warning-level detections
3. **Validation Failures**: Content policy violations
4. **Anomalies Detected**: Statistical outliers

### 4. Security Logging (`lambda/security_logging.py`)

Comprehensive audit trail:

#### Structured Logging
- **Correlation IDs**: Track requests end-to-end
- **Event types**: Categorized security events
- **Severity levels**: Consistent severity taxonomy
- **CloudWatch integration**: Searchable logs

#### PII Redaction
- **Automatic redaction**: Removes API keys, tokens, secrets
- **Content truncation**: Limits logged content length
- **Hash generation**: Provides verification without exposing data

#### Audit Trail
- **S3 persistence**: Long-term storage of security events
- **JSON format**: Machine-readable audit logs
- **Encrypted storage**: AES256 server-side encryption
- **Retention**: Configurable retention policies

### 5. Configuration (`config/security_config.json`)

Centralized security policy:

```json
{
  "content_limits": {
    "max_reflection_length_chars": 10000,
    "max_reflection_length_words": 2000,
    "min_reflection_length_chars": 100,
    "min_reflection_length_words": 50
  },
  "malicious_patterns": {
    "enabled": true,
    "patterns": ["<script>", "javascript:", ...]
  },
  "url_detection": {
    "enabled": true,
    "block_all_urls": true,
    "max_urls_allowed": 0
  },
  "anomaly_detection": {
    "enabled": true,
    "deviation_threshold_sigma": 3.0
  }
}
```

## API Integration

### Secure Generation Function

```python
reflection, security_report = generate_reflection_secure(
    quote=quote,
    attribution=attribution,
    theme=theme_name,
    api_key=api_key,
    bucket_name=bucket_name,
    sns_topic_arn=sns_topic_arn
)
```

### Security Report Structure

```python
{
    'success': True,
    'security_status': 'PASSED',  # PASSED, REJECTED, ERROR
    'sanitized': False,  # True if content was modified
    'validation_duration_ms': 125.5,
    'checks_performed': 5,
    'check_results': [
        {
            'check': 'malicious_patterns',
            'passed': True,
            'severity': 'INFO',
            'details': 'No malicious patterns detected'
        },
        # ... more checks
    ],
    'validation_results': {
        'statistics': {...},
        'anomaly_detection': {...},
        'content_policy': {...}
    },
    'correlation_id': 'uuid',
    'alert_summary': {...}
}
```

## Security Guarantees

### What We Guarantee

1. **All output is sanitized** before use
2. **Known malicious patterns are blocked** (XSS, scripts, etc.)
3. **URLs are detected and blocked by default**
4. **Oversized content is rejected**
5. **All security events are logged**
6. **Critical failures trigger alerts**
7. **Audit trail maintained in S3**

### What We Don't Guarantee

1. **Zero-day attacks**: New attack vectors may emerge
2. **Semantic attacks**: Sophisticated social engineering content
3. **Perfect anomaly detection**: Statistical models have false negatives
4. **Content quality**: Security ≠ quality assurance

## Monitoring & Response

### CloudWatch Dashboards

Monitor these key metrics:
- `ValidationResult`: Success rate (target: >99%)
- `ValidationDuration`: Performance (target: <500ms)
- `blocked_content`: Critical security events (investigate all)
- `suspicious_content`: Warning events (review regularly)
- `anomaly_detected`: Statistical outliers (monitor trends)

### Alert Response

#### CRITICAL Alerts
- **Blocked Content**: Investigate immediately
- **Action**: Review logs, check for attack patterns
- **Timeline**: Respond within 1 hour

#### WARNING Alerts
- **Suspicious Content**: Review within 24 hours
- **Anomalies**: Investigate trends, may indicate prompt changes
- **Timeline**: Respond within 24 hours

#### INFO Alerts
- **Validation Metrics**: For trend analysis
- **Timeline**: Weekly review

### Incident Response

1. **Identify**: Alert triggers, check correlation ID
2. **Investigate**: Review audit logs in S3 (`security/audit_logs/{timestamp}_{correlation_id}.json`)
3. **Analyze**: Examine blocked patterns, validation results
4. **Respond**: Update security config if needed
5. **Document**: Record findings and actions taken

## Testing

Run security tests:

```bash
python -m pytest tests/test_security.py -v
```

Test coverage:
- Content sanitization (control chars, zero-width, whitespace)
- Malicious pattern detection (XSS, scripts, injection)
- URL detection (http, https, shortened URLs)
- Length validation (min/max bounds)
- Character validation (repetition, homoglyphs)
- Integration scenarios (multiple threats)

## Configuration Management

### Updating Security Policies

1. Edit `config/security_config.json`
2. Test changes locally
3. Deploy via CDK
4. Monitor alerts for false positives

### Adding Detection Patterns

To add new malicious patterns:

```json
{
  "malicious_patterns": {
    "patterns": [
      "(?i)<your-new-pattern>",
      "(?i)another-pattern"
    ]
  }
}
```

Patterns use Python regex syntax with `re.IGNORECASE` flag.

### Tuning Anomaly Detection

Adjust sensitivity:

```json
{
  "anomaly_detection": {
    "deviation_threshold_sigma": 3.0,  // Lower = more sensitive
    "min_samples_for_detection": 10
  }
}
```

## Infrastructure

### AWS Resources

- **SNS Topic**: `StoicReflections-SecurityAlerts`
- **S3 Paths**:
  - `security/audit_logs/` - Security event logs
  - `security/response_statistics.json` - Anomaly detection baseline
- **CloudWatch Namespace**: `StoicReflections/Security`

### IAM Permissions Required

Lambda function needs:
- `s3:GetObject`, `s3:PutObject` on security paths
- `sns:Publish` to security alert topic
- `cloudwatch:PutMetricData` for metrics

### Deployment

```bash
cdk deploy --context security_alert_email=security@example.com
```

## Best Practices

### For Security Engineers

1. **Review alerts daily**: Don't ignore warnings
2. **Update patterns regularly**: Stay current with threats
3. **Test changes thoroughly**: Security bugs are critical
4. **Monitor trends**: Anomalies may indicate emerging issues
5. **Document incidents**: Build institutional knowledge

### For Developers

1. **Always use `generate_reflection_secure()`**: Never bypass security
2. **Never suppress security logs**: They're there for a reason
3. **Test with malicious inputs**: Verify controls work
4. **Report false positives**: Help tune the system
5. **Respect correlation IDs**: Essential for debugging

## Limitations & Future Work

### Current Limitations

1. **Pattern-based detection**: May miss novel attacks
2. **No ML-based classification**: Relies on rules and stats
3. **Limited semantic analysis**: Can't understand intent
4. **Single-language support**: Optimized for English

### Future Enhancements

1. **ML-based anomaly detection**: More sophisticated models
2. **Content classification**: Sentiment, topic, tone analysis
3. **Multi-language support**: Extend to other languages
4. **Automated threat intelligence**: Integrate threat feeds
5. **Real-time dashboards**: Enhanced monitoring UI

## References

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **Content Security Policy**: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
- **AWS Security Best Practices**: https://aws.amazon.com/security/
- **Anthropic Safety**: https://www.anthropic.com/safety

## Support

For security issues or questions:
- Review CloudWatch logs: `/aws/lambda/DailyStoicSender`
- Check audit logs in S3: `s3://{bucket}/security/audit_logs/`
- Examine security metrics in CloudWatch

For security incidents:
1. Check SNS alerts
2. Review correlation ID in audit logs
3. Analyze security report in CloudWatch logs
4. Document findings

## Version History

- **v1.0** (2024): Initial comprehensive security implementation
  - Defense-in-depth architecture
  - Sanitization, detection, validation
  - Alerting and logging
  - Anomaly detection
  - Full audit trail
