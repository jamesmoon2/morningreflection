"""
Core security module for handling untrusted API output.

Provides defense-in-depth security controls including:
- Content sanitization
- Malicious pattern detection
- URL detection and validation
- Character encoding validation
- Size/DoS protection
"""

import re
import json
import logging
import unicodedata
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger()


@dataclass
class SecurityCheckResult:
    """Result of a security check operation."""
    passed: bool
    severity: str  # INFO, WARNING, CRITICAL
    check_name: str
    details: str
    blocked_patterns: List[str] = None

    def __post_init__(self):
        if self.blocked_patterns is None:
            self.blocked_patterns = []


class SecurityConfig:
    """Loads and manages security configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize security configuration.

        Args:
            config_path: Path to security config JSON file
        """
        if config_path is None:
            # Default to config directory relative to lambda directory
            config_path = '/var/task/config/security_config.json'

        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
                logger.info(f"Loaded security config from {config_path}")
        except FileNotFoundError:
            logger.warning(f"Security config not found at {config_path}, using defaults")
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default security configuration."""
        return {
            "content_limits": {
                "max_reflection_length_chars": 10000,
                "max_reflection_length_words": 2000,
                "min_reflection_length_chars": 100,
                "min_reflection_length_words": 50
            },
            "malicious_patterns": {
                "enabled": True,
                "patterns": [
                    r"(?i)<script[^>]*>",
                    r"(?i)javascript:",
                    r"(?i)on(?:load|error|click|mouse|key)\s*="
                ]
            },
            "url_detection": {
                "enabled": True,
                "max_urls_allowed": 0,
                "block_all_urls": True
            },
            "sanitization": {
                "enabled": True,
                "html_escape_all": True,
                "remove_control_chars": True
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value if value is not None else default


class ContentSanitizer:
    """Sanitizes untrusted API output."""

    def __init__(self, config: SecurityConfig):
        self.config = config

    def sanitize(self, text: str) -> Tuple[str, List[str]]:
        """
        Sanitize untrusted text content.

        Args:
            text: Raw text to sanitize

        Returns:
            Tuple of (sanitized_text, list_of_modifications)
        """
        if not self.config.get('sanitization.enabled', True):
            return text, []

        modifications = []
        sanitized = text

        # Remove control characters (except newline, carriage return, tab)
        if self.config.get('sanitization.remove_control_chars', True):
            original_len = len(sanitized)
            sanitized = self._remove_control_chars(sanitized)
            if len(sanitized) != original_len:
                modifications.append("Removed control characters")

        # Remove invisible/zero-width characters
        if self.config.get('sanitization.strip_invisible_chars', True):
            original_len = len(sanitized)
            sanitized = self._remove_invisible_chars(sanitized)
            if len(sanitized) != original_len:
                modifications.append("Removed invisible characters")

        # Normalize whitespace
        if self.config.get('sanitization.normalize_whitespace', True):
            original_len = len(sanitized)
            sanitized = self._normalize_whitespace(sanitized)
            if len(sanitized) != original_len:
                modifications.append("Normalized whitespace")

        # Limit consecutive newlines
        max_newlines = self.config.get('sanitization.max_consecutive_newlines', 3)
        if max_newlines:
            pattern = r'\n{' + str(max_newlines + 1) + r',}'
            if re.search(pattern, sanitized):
                sanitized = re.sub(pattern, '\n' * max_newlines, sanitized)
                modifications.append(f"Limited consecutive newlines to {max_newlines}")

        return sanitized.strip(), modifications

    def _remove_control_chars(self, text: str) -> str:
        """Remove control characters except newline, carriage return, tab."""
        return ''.join(
            char for char in text
            if not unicodedata.category(char).startswith('C')
            or char in '\n\r\t'
        )

    def _remove_invisible_chars(self, text: str) -> str:
        """Remove zero-width and invisible characters."""
        invisible_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\u2060',  # Word joiner
            '\ufeff',  # Zero-width no-break space / BOM
            '\u180e',  # Mongolian vowel separator
        ]
        for char in invisible_chars:
            text = text.replace(char, '')
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving paragraph breaks."""
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Replace Windows line endings
        text = text.replace('\r\n', '\n')
        # Remove trailing whitespace from lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        return text


class MaliciousPatternDetector:
    """Detects malicious patterns in API output."""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        patterns = self.config.get('malicious_patterns.patterns', [])
        self.malicious_patterns = [re.compile(p) for p in patterns]

        suspicious = self.config.get('malicious_patterns.suspicious_patterns', [])
        self.suspicious_patterns = [re.compile(p) for p in suspicious]

    def check(self, text: str) -> SecurityCheckResult:
        """
        Check text for malicious patterns.

        Args:
            text: Text to check

        Returns:
            SecurityCheckResult indicating if check passed
        """
        if not self.config.get('malicious_patterns.enabled', True):
            return SecurityCheckResult(
                passed=True,
                severity='INFO',
                check_name='malicious_patterns',
                details='Check disabled'
            )

        # Check for critical malicious patterns
        blocked = []
        for pattern in self.malicious_patterns:
            matches = pattern.findall(text)
            if matches:
                blocked.extend(matches[:3])  # Limit to first 3 matches

        if blocked:
            return SecurityCheckResult(
                passed=False,
                severity='CRITICAL',
                check_name='malicious_patterns',
                details=f'Detected {len(blocked)} malicious pattern(s)',
                blocked_patterns=blocked
            )

        # Check for suspicious patterns
        suspicious = []
        for pattern in self.suspicious_patterns:
            matches = pattern.findall(text)
            if matches:
                suspicious.extend(matches[:3])

        if suspicious:
            return SecurityCheckResult(
                passed=True,  # Don't block, just warn
                severity='WARNING',
                check_name='malicious_patterns',
                details=f'Detected {len(suspicious)} suspicious pattern(s)',
                blocked_patterns=suspicious
            )

        return SecurityCheckResult(
            passed=True,
            severity='INFO',
            check_name='malicious_patterns',
            details='No malicious patterns detected'
        )


class URLDetector:
    """Detects and validates URLs in content."""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.url_pattern = re.compile(
            self.config.get('url_detection.url_pattern',
                          r'(?:https?://|www\.)\S+'),
            re.IGNORECASE
        )

    def check(self, text: str) -> SecurityCheckResult:
        """
        Check text for URLs and validate against policy.

        Args:
            text: Text to check

        Returns:
            SecurityCheckResult indicating if check passed
        """
        if not self.config.get('url_detection.enabled', True):
            return SecurityCheckResult(
                passed=True,
                severity='INFO',
                check_name='url_detection',
                details='Check disabled'
            )

        urls = self.url_pattern.findall(text)

        if not urls:
            return SecurityCheckResult(
                passed=True,
                severity='INFO',
                check_name='url_detection',
                details='No URLs detected'
            )

        max_allowed = self.config.get('url_detection.max_urls_allowed', 0)
        block_all = self.config.get('url_detection.block_all_urls', True)

        if block_all or len(urls) > max_allowed:
            return SecurityCheckResult(
                passed=False,
                severity='CRITICAL',
                check_name='url_detection',
                details=f'Detected {len(urls)} URL(s), policy allows {max_allowed}',
                blocked_patterns=urls[:5]  # Show first 5 URLs
            )

        # Check for suspicious domains
        suspicious_domains = self.config.get('url_detection.suspicious_domains', [])
        suspicious_urls = []
        for url in urls:
            for domain in suspicious_domains:
                if domain.lower() in url.lower():
                    suspicious_urls.append(url)
                    break

        if suspicious_urls:
            return SecurityCheckResult(
                passed=False,
                severity='WARNING',
                check_name='url_detection',
                details=f'Detected {len(suspicious_urls)} suspicious URL(s)',
                blocked_patterns=suspicious_urls
            )

        return SecurityCheckResult(
            passed=True,
            severity='INFO',
            check_name='url_detection',
            details=f'Detected {len(urls)} allowed URL(s)'
        )


class ContentLengthValidator:
    """Validates content length to prevent DoS."""

    def __init__(self, config: SecurityConfig):
        self.config = config

    def check(self, text: str) -> SecurityCheckResult:
        """
        Check if content length is within acceptable bounds.

        Args:
            text: Text to validate

        Returns:
            SecurityCheckResult indicating if check passed
        """
        char_count = len(text)
        word_count = len(text.split())

        max_chars = self.config.get('content_limits.max_reflection_length_chars', 10000)
        max_words = self.config.get('content_limits.max_reflection_length_words', 2000)
        min_chars = self.config.get('content_limits.min_reflection_length_chars', 100)
        min_words = self.config.get('content_limits.min_reflection_length_words', 50)

        if char_count > max_chars:
            return SecurityCheckResult(
                passed=False,
                severity='CRITICAL',
                check_name='content_length',
                details=f'Content too long: {char_count} chars (max {max_chars})'
            )

        if word_count > max_words:
            return SecurityCheckResult(
                passed=False,
                severity='CRITICAL',
                check_name='content_length',
                details=f'Content too long: {word_count} words (max {max_words})'
            )

        if char_count < min_chars:
            return SecurityCheckResult(
                passed=False,
                severity='WARNING',
                check_name='content_length',
                details=f'Content too short: {char_count} chars (min {min_chars})'
            )

        if word_count < min_words:
            return SecurityCheckResult(
                passed=False,
                severity='WARNING',
                check_name='content_length',
                details=f'Content too short: {word_count} words (min {min_words})'
            )

        return SecurityCheckResult(
            passed=True,
            severity='INFO',
            check_name='content_length',
            details=f'Content length acceptable: {char_count} chars, {word_count} words'
        )


class CharacterValidator:
    """Validates character encoding and detects anomalies."""

    def __init__(self, config: SecurityConfig):
        self.config = config

    def check(self, text: str) -> SecurityCheckResult:
        """
        Check for character encoding issues and anomalies.

        Args:
            text: Text to validate

        Returns:
            SecurityCheckResult indicating if check passed
        """
        if not self.config.get('character_validation.enabled', True):
            return SecurityCheckResult(
                passed=True,
                severity='INFO',
                check_name='character_validation',
                details='Check disabled'
            )

        issues = []

        # Check for excessive consecutive same character (potential DoS)
        max_consecutive = self.config.get('character_validation.max_consecutive_same_char', 50)
        consecutive_pattern = re.compile(r'(.)\1{' + str(max_consecutive) + r',}')
        if consecutive_pattern.search(text):
            issues.append(f'Excessive consecutive characters (>{max_consecutive})')

        # Check for homoglyph attacks if enabled
        if self.config.get('character_validation.block_homoglyphs', True):
            if self._contains_homoglyphs(text):
                issues.append('Potential homoglyph characters detected')

        if issues:
            return SecurityCheckResult(
                passed=False,
                severity='WARNING',
                check_name='character_validation',
                details='; '.join(issues)
            )

        return SecurityCheckResult(
            passed=True,
            severity='INFO',
            check_name='character_validation',
            details='Character validation passed'
        )

    def _contains_homoglyphs(self, text: str) -> bool:
        """
        Check for potential homoglyph attacks.

        Looks for Cyrillic or Greek characters that look like Latin.
        """
        # Common homoglyphs: Cyrillic/Greek chars that look like ASCII
        homoglyphs = [
            '\u0430',  # Cyrillic 'a'
            '\u0435',  # Cyrillic 'e'
            '\u043e',  # Cyrillic 'o'
            '\u0440',  # Cyrillic 'p'
            '\u0441',  # Cyrillic 'c'
            '\u0445',  # Cyrillic 'x'
            '\u0391',  # Greek 'A'
            '\u0392',  # Greek 'B'
            '\u039f',  # Greek 'O'
        ]
        return any(char in text for char in homoglyphs)


class SecurityValidator:
    """Main security validator orchestrating all checks."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize security validator.

        Args:
            config_path: Path to security config file
        """
        self.config = SecurityConfig(config_path)
        self.sanitizer = ContentSanitizer(self.config)
        self.pattern_detector = MaliciousPatternDetector(self.config)
        self.url_detector = URLDetector(self.config)
        self.length_validator = ContentLengthValidator(self.config)
        self.char_validator = CharacterValidator(self.config)

    def validate_and_sanitize(
        self,
        text: str,
        content_type: str = 'reflection'
    ) -> Tuple[bool, str, List[SecurityCheckResult]]:
        """
        Perform comprehensive security validation and sanitization.

        Args:
            text: Untrusted text to validate
            content_type: Type of content (for logging)

        Returns:
            Tuple of (is_safe, sanitized_text, list_of_check_results)
        """
        logger.info(f"Starting security validation for {content_type}")

        results = []

        # 1. Sanitize first
        sanitized_text, modifications = self.sanitizer.sanitize(text)
        if modifications:
            logger.info(f"Sanitization modifications: {', '.join(modifications)}")

        # 2. Run all security checks on sanitized text
        results.append(self.length_validator.check(sanitized_text))
        results.append(self.pattern_detector.check(sanitized_text))
        results.append(self.url_detector.check(sanitized_text))
        results.append(self.char_validator.check(sanitized_text))

        # 3. Determine overall safety
        critical_failures = [r for r in results if not r.passed and r.severity == 'CRITICAL']
        warning_failures = [r for r in results if not r.passed and r.severity == 'WARNING']

        is_safe = len(critical_failures) == 0

        # Log results
        for result in results:
            level = logging.ERROR if not result.passed and result.severity == 'CRITICAL' else \
                    logging.WARNING if not result.passed else \
                    logging.INFO
            logger.log(level, f"Security check '{result.check_name}': {result.details}")
            if result.blocked_patterns:
                logger.log(level, f"  Blocked patterns: {result.blocked_patterns}")

        if critical_failures:
            logger.error(f"SECURITY VIOLATION: {len(critical_failures)} critical failure(s) detected")
        if warning_failures:
            logger.warning(f"SECURITY WARNING: {len(warning_failures)} warning(s) detected")

        return is_safe, sanitized_text, results
