"""
Unit tests for token_manager module.
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from token_manager import (
    TokenManager,
    generate_confirmation_token,
    generate_unsubscribe_token,
    verify_unsubscribe_token
)


class TestTokenManager(unittest.TestCase):
    """Test cases for TokenManager class."""

    def test_generate_confirmation_token(self):
        """Test confirmation token generation."""
        token1 = TokenManager.generate_confirmation_token()
        token2 = TokenManager.generate_confirmation_token()

        # Tokens should be non-empty strings
        self.assertIsInstance(token1, str)
        self.assertTrue(len(token1) > 0)

        # Tokens should be unique
        self.assertNotEqual(token1, token2)

    def test_generate_unsubscribe_token(self):
        """Test unsubscribe token generation."""
        email = "test@example.com"

        token1 = TokenManager.generate_unsubscribe_token(email)
        token2 = TokenManager.generate_unsubscribe_token(email)

        # Tokens should be deterministic for same email
        self.assertEqual(token1, token2)

        # Token should be non-empty string
        self.assertIsInstance(token1, str)
        self.assertTrue(len(token1) > 0)

    def test_unsubscribe_token_case_insensitive(self):
        """Test that unsubscribe tokens are case-insensitive for email."""
        email_lower = "test@example.com"
        email_upper = "TEST@EXAMPLE.COM"

        token_lower = TokenManager.generate_unsubscribe_token(email_lower)
        token_upper = TokenManager.generate_unsubscribe_token(email_upper)

        # Tokens should be the same regardless of case
        self.assertEqual(token_lower, token_upper)

    def test_verify_unsubscribe_token_valid(self):
        """Test verification of valid unsubscribe token."""
        email = "test@example.com"
        token = TokenManager.generate_unsubscribe_token(email)

        # Should verify successfully
        self.assertTrue(TokenManager.verify_unsubscribe_token(email, token))

    def test_verify_unsubscribe_token_invalid(self):
        """Test verification of invalid unsubscribe token."""
        email = "test@example.com"
        invalid_token = "invalid_token_12345"

        # Should fail verification
        self.assertFalse(TokenManager.verify_unsubscribe_token(email, invalid_token))

    def test_verify_unsubscribe_token_wrong_email(self):
        """Test verification with mismatched email."""
        email1 = "test1@example.com"
        email2 = "test2@example.com"

        token1 = TokenManager.generate_unsubscribe_token(email1)

        # Should fail when verifying with different email
        self.assertFalse(TokenManager.verify_unsubscribe_token(email2, token1))

    def test_is_confirmation_expired_not_expired(self):
        """Test confirmation token expiration check for non-expired token."""
        # Token created 1 hour ago
        created_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + 'Z'

        # Should not be expired (default 24 hours)
        self.assertFalse(TokenManager.is_confirmation_expired(created_time))

    def test_is_confirmation_expired_expired(self):
        """Test confirmation token expiration check for expired token."""
        # Token created 25 hours ago
        created_time = (datetime.utcnow() - timedelta(hours=25)).isoformat() + 'Z'

        # Should be expired (default 24 hours)
        self.assertTrue(TokenManager.is_confirmation_expired(created_time))

    def test_is_confirmation_expired_custom_duration(self):
        """Test confirmation token expiration with custom duration."""
        # Token created 2 hours ago
        created_time = (datetime.utcnow() - timedelta(hours=2)).isoformat() + 'Z'

        # Should be expired with 1-hour limit
        self.assertTrue(TokenManager.is_confirmation_expired(created_time, hours=1))

        # Should not be expired with 3-hour limit
        self.assertFalse(TokenManager.is_confirmation_expired(created_time, hours=3))

    def test_is_confirmation_expired_invalid_format(self):
        """Test confirmation expiration check with invalid date format."""
        invalid_date = "not-a-date"

        # Should treat as expired
        self.assertTrue(TokenManager.is_confirmation_expired(invalid_date))

    def test_create_subscriber_tokens(self):
        """Test creation of subscriber tokens."""
        tokens = TokenManager.create_subscriber_tokens()

        # Should contain confirmation_token
        self.assertIn('confirmation_token', tokens)
        self.assertIsInstance(tokens['confirmation_token'], str)
        self.assertTrue(len(tokens['confirmation_token']) > 0)

    def test_convenience_functions(self):
        """Test convenience wrapper functions."""
        # Test generate_confirmation_token
        token = generate_confirmation_token()
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        # Test generate_unsubscribe_token
        email = "test@example.com"
        unsub_token = generate_unsubscribe_token(email)
        self.assertIsInstance(unsub_token, str)
        self.assertTrue(len(unsub_token) > 0)

        # Test verify_unsubscribe_token
        self.assertTrue(verify_unsubscribe_token(email, unsub_token))
        self.assertFalse(verify_unsubscribe_token(email, "invalid"))


if __name__ == '__main__':
    unittest.main()
