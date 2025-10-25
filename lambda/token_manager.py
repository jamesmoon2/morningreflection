"""
Token management utilities for subscription confirmation and unsubscribe links.

Provides secure token generation and validation for email subscription workflows.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict


class TokenManager:
    """Manages tokens for email confirmation and unsubscribe links."""

    @staticmethod
    def generate_confirmation_token() -> str:
        """
        Generate a secure random token for email confirmation.

        Returns:
            URL-safe random token (32 bytes)
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_unsubscribe_token(email: str) -> str:
        """
        Generate a consistent unsubscribe token for an email address.

        The token is deterministic based on email + secret, allowing
        us to verify unsubscribe requests without storing tokens.

        Args:
            email: Email address to generate token for

        Returns:
            URL-safe token derived from email
        """
        # In production, use a secret key from environment
        # For now, using a simple hash. IMPORTANT: Add secret in production!
        secret = "CHANGE_ME_IN_PRODUCTION_USE_ENV_VAR"

        # Create deterministic token from email + secret
        combined = f"{email.lower().strip()}:{secret}"
        token_hash = hashlib.sha256(combined.encode()).hexdigest()

        return token_hash[:32]  # Return first 32 chars for readability

    @staticmethod
    def verify_unsubscribe_token(email: str, token: str) -> bool:
        """
        Verify that an unsubscribe token matches the email.

        Args:
            email: Email address to verify
            token: Token to validate

        Returns:
            True if token is valid for the email, False otherwise
        """
        expected_token = TokenManager.generate_unsubscribe_token(email)
        return secrets.compare_digest(token, expected_token)

    @staticmethod
    def is_confirmation_expired(created_at: str, hours: int = 24) -> bool:
        """
        Check if a confirmation token has expired.

        Args:
            created_at: ISO 8601 timestamp when token was created
            hours: Hours until expiration (default: 24)

        Returns:
            True if expired, False if still valid
        """
        try:
            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            expiration_time = created_time + timedelta(hours=hours)
            return datetime.utcnow() > expiration_time
        except (ValueError, AttributeError):
            # If we can't parse the date, treat as expired
            return True

    @staticmethod
    def create_subscriber_tokens() -> Dict[str, str]:
        """
        Create both confirmation and unsubscribe tokens for a new subscriber.

        Returns:
            Dictionary with 'confirmation_token' key
        """
        return {
            'confirmation_token': TokenManager.generate_confirmation_token()
        }


def generate_confirmation_token() -> str:
    """
    Convenience function to generate confirmation token.

    Returns:
        URL-safe random token
    """
    return TokenManager.generate_confirmation_token()


def generate_unsubscribe_token(email: str) -> str:
    """
    Convenience function to generate unsubscribe token.

    Args:
        email: Email address

    Returns:
        Unsubscribe token for the email
    """
    return TokenManager.generate_unsubscribe_token(email)


def verify_unsubscribe_token(email: str, token: str) -> bool:
    """
    Convenience function to verify unsubscribe token.

    Args:
        email: Email address
        token: Token to verify

    Returns:
        True if valid, False otherwise
    """
    return TokenManager.verify_unsubscribe_token(email, token)
