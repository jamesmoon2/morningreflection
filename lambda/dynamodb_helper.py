"""
Helper functions for DynamoDB operations in the daily reflection Lambda.

Provides functions for:
- Writing reflections to DynamoDB
- Querying users by delivery time
- Creating magic links (JWT tokens)
"""

import os
import json
import logging
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB and Secrets Manager clients
dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')

# Get environment variables
USERS_TABLE = os.environ.get('DYNAMODB_USERS_TABLE', 'MorningReflection-Users')
REFLECTIONS_TABLE = os.environ.get('DYNAMODB_REFLECTIONS_TABLE', 'MorningReflection-Reflections')
WEB_APP_URL = os.environ.get('WEB_APP_URL', 'https://app.morningreflection.com')


def save_reflection_to_dynamodb(
    date: str,
    quote: str,
    attribution: str,
    theme: str,
    reflection: str,
    journaling_prompt: Optional[str] = None,
    model_version: str = "claude-sonnet-4-5-20250929",
    security_report: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Save a reflection to DynamoDB Reflections table.

    Args:
        date: Date in YYYY-MM-DD format
        quote: Stoic quote
        attribution: Quote attribution
        theme: Monthly theme
        reflection: Generated reflection text
        journaling_prompt: Generated journaling prompt (optional)
        model_version: Claude model used
        security_report: Security validation report (optional)

    Returns:
        True if successful, False otherwise
    """
    try:
        table = dynamodb.Table(REFLECTIONS_TABLE)

        item = {
            'date': date,
            'quote': quote,
            'attribution': attribution,
            'theme': theme,
            'reflection': reflection,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'model_version': model_version
        }

        if journaling_prompt:
            item['journaling_prompt'] = journaling_prompt

        if security_report:
            # Store security report as JSON string to avoid DynamoDB nested depth issues
            item['security_report'] = json.dumps(security_report)

        table.put_item(Item=item)
        logger.info(f"Successfully saved reflection to DynamoDB for date: {date}")
        return True

    except ClientError as e:
        logger.error(f"Error saving reflection to DynamoDB: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving reflection to DynamoDB: {e}")
        return False


def get_users_for_delivery_time(
    delivery_time: str,
    timezone: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all active users who want email delivery at a specific time.

    For Phase 3, we'll do a simple scan. In production with many users,
    you'd want to add a GSI on delivery_time or use a more sophisticated approach.

    Args:
        delivery_time: Time in HH:MM format (e.g., "06:00")
        timezone: Optional timezone filter

    Returns:
        List of user dictionaries
    """
    try:
        table = dynamodb.Table(USERS_TABLE)

        # Build filter expression
        filter_expression = "subscription_status = :active AND delivery_time = :time"
        expression_values = {
            ':active': 'active',
            ':time': delivery_time
        }

        if timezone:
            filter_expression += " AND timezone = :tz"
            expression_values[':tz'] = timezone

        # Scan table with filter
        # NOTE: Scan is inefficient for large tables. Consider adding GSI in production.
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_values
        )

        users = response.get('Items', [])
        logger.info(f"Found {len(users)} users for delivery time {delivery_time}")

        return users

    except ClientError as e:
        logger.error(f"Error querying users for delivery time: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error querying users: {e}")
        return []


def get_all_active_users() -> List[Dict[str, Any]]:
    """
    Get all active users who have email enabled.

    Returns:
        List of user dictionaries
    """
    try:
        table = dynamodb.Table(USERS_TABLE)

        # Scan for active users
        response = table.scan(
            FilterExpression="subscription_status = :active",
            ExpressionAttributeValues={':active': 'active'}
        )

        users = response.get('Items', [])

        # Filter for users with email enabled
        email_users = [
            u for u in users
            if u.get('preferences', {}).get('email_enabled', True)
        ]

        logger.info(f"Found {len(email_users)} active users with email enabled")
        return email_users

    except ClientError as e:
        logger.error(f"Error getting active users: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting users: {e}")
        return []


def get_jwt_secret() -> str:
    """
    Get JWT secret from Secrets Manager or generate a consistent one.

    For production, store this in Secrets Manager.
    For now, we'll use a hash of the Anthropic API key as the JWT secret.

    Returns:
        JWT secret string
    """
    try:
        # Try to get from Secrets Manager
        secret_name = "morningreflection/jwt-secret"

        try:
            response = secrets_client.get_secret_value(SecretId=secret_name)
            if 'SecretString' in response:
                logger.info("Retrieved JWT secret from Secrets Manager")
                return response['SecretString']
        except secrets_client.exceptions.ResourceNotFoundException:
            logger.warning(f"JWT secret not found in Secrets Manager: {secret_name}")
            pass

        # Fallback: Use Anthropic API key hash
        # This is not ideal but works for Phase 3
        api_key_secret_name = os.environ.get('ANTHROPIC_API_KEY_SECRET_NAME')
        if api_key_secret_name:
            response = secrets_client.get_secret_value(SecretId=api_key_secret_name)
            api_key = response['SecretString']
            # Create a deterministic secret from API key
            jwt_secret = hashlib.sha256(api_key.encode()).hexdigest()
            logger.info("Generated JWT secret from API key hash")
            return jwt_secret

        # Last resort: use environment-based secret (not secure)
        logger.warning("Using environment-based JWT secret (not secure for production)")
        return hashlib.sha256(b"morningreflection-fallback-secret").hexdigest()

    except Exception as e:
        logger.error(f"Error getting JWT secret: {e}")
        # Return a fallback (not secure, but prevents crashes)
        return hashlib.sha256(b"emergency-fallback-secret").hexdigest()


def generate_magic_link(user_id: str, email: str, date: str) -> str:
    """
    Generate a magic link (JWT token in URL) for email click-through.

    The magic link allows users to access the daily reflection without logging in.

    Args:
        user_id: User ID (Cognito sub)
        email: User email
        date: Date of the reflection (YYYY-MM-DD)

    Returns:
        Full URL with magic link token
    """
    try:
        # Get JWT secret
        jwt_secret = get_jwt_secret()

        # Create JWT payload
        payload = {
            'user_id': user_id,
            'email': email,
            'date': date,
            'action': 'daily_reflection',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=60)  # 1-hour expiration
        }

        # Sign token
        token = jwt.encode(payload, jwt_secret, algorithm='HS256')

        # Build URL
        magic_link = f"{WEB_APP_URL}/daily/{date}?token={token}"

        logger.info(f"Generated magic link for user {user_id}, date {date}")
        return magic_link

    except Exception as e:
        logger.error(f"Error generating magic link: {e}")
        # Return a fallback URL without token
        return f"{WEB_APP_URL}/daily/{date}"
