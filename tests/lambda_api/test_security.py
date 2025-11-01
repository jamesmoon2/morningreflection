"""
Tests for lambda_api/security.py - API security module
"""

import pytest
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add lambda_api directory to path
lambda_api_dir = Path(__file__).parent.parent.parent / "lambda_api"
sys.path.insert(0, str(lambda_api_dir))


# SecurityConfig Tests

def test_security_config_default():
    """Test SecurityConfig with default configuration"""
    from security import SecurityConfig

    # Use non-existent path to force default config
    config = SecurityConfig(config_path='/nonexistent/path.json')

    assert config.get('content_limits.max_reflection_length_chars') == 10000
    assert config.get('malicious_patterns.enabled') is True


def test_security_config_get_nested():
    """Test SecurityConfig get with nested keys"""
    from security import SecurityConfig

    config = SecurityConfig(config_path='/nonexistent/path.json')

    value = config.get('content_limits.max_reflection_length_chars')
    assert value == 10000

    default = config.get('nonexistent.key', 'default_value')
    assert default == 'default_value'


# ContentSanitizer Tests

def test_content_sanitizer_remove_control_chars():
    """Test sanitizer removes control characters"""
    from security import SecurityConfig, ContentSanitizer

    config = SecurityConfig(config_path='/nonexistent/path.json')
    sanitizer = ContentSanitizer(config)

    text_with_control = "Hello\x00World\x01Test"
    sanitized, mods = sanitizer.sanitize(text_with_control)

    assert '\x00' not in sanitized
    assert 'Removed control characters' in mods


def test_content_sanitizer_normalize_whitespace():
    """Test sanitizer normalizes whitespace"""
    from security import SecurityConfig, ContentSanitizer

    config = SecurityConfig(config_path='/nonexistent/path.json')
    sanitizer = ContentSanitizer(config)

    text = "Hello    World\r\nTest"
    sanitized, mods = sanitizer.sanitize(text)

    assert '    ' not in sanitized  # Multiple spaces reduced
    assert '\r\n' not in sanitized   # Windows line endings normalized


def test_content_sanitizer_limit_newlines():
    """Test sanitizer limits consecutive newlines"""
    from security import SecurityConfig, ContentSanitizer

    config = SecurityConfig(config_path='/nonexistent/path.json')
    sanitizer = ContentSanitizer(config)

    text = "Hello\n\n\n\n\n\n\nWorld"  # 7 newlines
    sanitized, mods = sanitizer.sanitize(text)

    # Should be limited to 3 consecutive newlines
    assert '\n\n\n\n' not in sanitized


# MaliciousPatternDetector Tests

def test_malicious_pattern_detector_xss():
    """Test detection of XSS patterns"""
    from security import SecurityConfig, MaliciousPatternDetector

    config = SecurityConfig(config_path='/nonexistent/path.json')
    detector = MaliciousPatternDetector(config)

    text = 'This contains <script>alert("xss")</script> tag'
    result = detector.check(text)

    assert result.passed is False
    assert result.severity == 'CRITICAL'
    assert len(result.blocked_patterns) > 0


def test_malicious_pattern_detector_javascript():
    """Test detection of javascript: protocol"""
    from security import SecurityConfig, MaliciousPatternDetector

    config = SecurityConfig(config_path='/nonexistent/path.json')
    detector = MaliciousPatternDetector(config)

    text = 'This contains javascript:alert("xss") link'
    result = detector.check(text)

    assert result.passed is False
    assert result.severity == 'CRITICAL'


def test_malicious_pattern_detector_clean_text():
    """Test detection with clean text"""
    from security import SecurityConfig, MaliciousPatternDetector

    config = SecurityConfig(config_path='/nonexistent/path.json')
    detector = MaliciousPatternDetector(config)

    text = 'This is a clean reflection about stoic philosophy.'
    result = detector.check(text)

    assert result.passed is True
    assert result.severity == 'INFO'


# URLDetector Tests

def test_url_detector_blocks_urls():
    """Test URL detection blocks URLs when configured"""
    from security import SecurityConfig, URLDetector

    config = SecurityConfig(config_path='/nonexistent/path.json')
    detector = URLDetector(config)

    text = 'Check out this link: https://example.com'
    result = detector.check(text)

    assert result.passed is False  # URLs blocked by default
    assert result.severity == 'CRITICAL'


def test_url_detector_no_urls():
    """Test URL detection with no URLs"""
    from security import SecurityConfig, URLDetector

    config = SecurityConfig(config_path='/nonexistent/path.json')
    detector = URLDetector(config)

    text = 'This is a clean reflection with no URLs.'
    result = detector.check(text)

    assert result.passed is True


# ContentLengthValidator Tests

def test_content_length_validator_too_long_chars():
    """Test content length validator detects content too long"""
    from security import SecurityConfig, ContentLengthValidator

    config = SecurityConfig(config_path='/nonexistent/path.json')
    validator = ContentLengthValidator(config)

    text = 'x' * 11000  # Exceeds default max of 10000
    result = validator.check(text)

    assert result.passed is False
    assert result.severity == 'CRITICAL'
    assert 'too long' in result.details


def test_content_length_validator_too_short():
    """Test content length validator detects content too short"""
    from security import SecurityConfig, ContentLengthValidator

    config = SecurityConfig(config_path='/nonexistent/path.json')
    validator = ContentLengthValidator(config)

    text = 'Short'  # Below minimum
    result = validator.check(text)

    assert result.passed is False
    assert result.severity == 'WARNING'
    assert 'too short' in result.details


def test_content_length_validator_acceptable():
    """Test content length validator with acceptable content"""
    from security import SecurityConfig, ContentLengthValidator

    config = SecurityConfig(config_path='/nonexistent/path.json')
    validator = ContentLengthValidator(config)

    # Create text with ~60 words (between min 50 and max 2000)
    text = ' '.join(['word'] * 60)
    result = validator.check(text)

    assert result.passed is True
    assert result.severity == 'INFO'


# CharacterValidator Tests

def test_character_validator_excessive_consecutive():
    """Test detection of excessive consecutive characters"""
    from security import SecurityConfig, CharacterValidator

    config = SecurityConfig(config_path='/nonexistent/path.json')
    validator = CharacterValidator(config)

    text = 'a' * 100  # Exceeds default max consecutive of 50
    result = validator.check(text)

    assert result.passed is False
    assert result.severity == 'WARNING'


def test_character_validator_homoglyphs():
    """Test detection of homoglyph characters"""
    from security import SecurityConfig, CharacterValidator

    config = SecurityConfig(config_path='/nonexistent/path.json')
    validator = CharacterValidator(config)

    # Use Cyrillic 'a' instead of Latin 'a'
    text = 'This contains \u0430 cyrillic character'
    result = validator.check(text)

    assert result.passed is False
    assert 'homoglyph' in result.details.lower()


def test_character_validator_clean_text():
    """Test character validator with clean text"""
    from security import SecurityConfig, CharacterValidator

    config = SecurityConfig(config_path='/nonexistent/path.json')
    validator = CharacterValidator(config)

    text = 'This is a normal reflection with standard characters.'
    result = validator.check(text)

    assert result.passed is True


# SecurityValidator Integration Tests

def test_security_validator_validates_clean_content():
    """Test full validation with clean content"""
    from security import SecurityValidator

    validator = SecurityValidator(config_path='/nonexistent/path.json')

    text = """You have power over your mind - not outside events.

This profound insight from Marcus Aurelius reminds us of the fundamental distinction between what we can control and what we cannot. In our daily lives, we often expend enormous energy worrying about external circumstances."""

    is_safe, sanitized, results = validator.validate_and_sanitize(text)

    assert is_safe is True
    assert len(results) > 0
    assert all(r.passed or r.severity != 'CRITICAL' for r in results)


def test_security_validator_blocks_xss():
    """Test full validation blocks XSS"""
    from security import SecurityValidator

    validator = SecurityValidator(config_path='/nonexistent/path.json')

    text = 'This contains <script>alert("xss")</script> malicious code'
    is_safe, sanitized, results = validator.validate_and_sanitize(text)

    assert is_safe is False
    assert any(not r.passed and r.severity == 'CRITICAL' for r in results)


def test_security_validator_blocks_urls():
    """Test full validation blocks URLs"""
    from security import SecurityValidator

    validator = SecurityValidator(config_path='/nonexistent/path.json')

    text = 'Check out this site: https://malicious.com with more text to meet length requirements. ' * 20
    is_safe, sanitized, results = validator.validate_and_sanitize(text)

    assert is_safe is False


def test_security_validator_sanitizes_content():
    """Test that validation sanitizes content"""
    from security import SecurityValidator

    validator = SecurityValidator(config_path='/nonexistent/path.json')

    text = "Hello    World\r\nTest"  # Multiple spaces and Windows line endings
    is_safe, sanitized, results = validator.validate_and_sanitize(text)

    # Should be sanitized
    assert '    ' not in sanitized
    assert '\r\n' not in sanitized


def test_security_validator_blocks_too_long_content():
    """Test validation blocks content that's too long"""
    from security import SecurityValidator

    validator = SecurityValidator(config_path='/nonexistent/path.json')

    text = 'x' * 11000  # Exceeds max length
    is_safe, sanitized, results = validator.validate_and_sanitize(text)

    assert is_safe is False
    assert any(r.check_name == 'content_length' and not r.passed for r in results)


def test_security_check_result_dataclass():
    """Test SecurityCheckResult dataclass"""
    from security import SecurityCheckResult

    result = SecurityCheckResult(
        passed=False,
        severity='WARNING',
        check_name='test_check',
        details='Test details',
        blocked_patterns=['pattern1']
    )

    assert result.passed is False
    assert result.severity == 'WARNING'
    assert len(result.blocked_patterns) == 1


def test_security_check_result_default_patterns():
    """Test SecurityCheckResult with default blocked_patterns"""
    from security import SecurityCheckResult

    result = SecurityCheckResult(
        passed=True,
        severity='INFO',
        check_name='test',
        details='Test'
    )

    assert result.blocked_patterns == []
