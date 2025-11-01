"""
DynamoDB operations for Morning Reflection.

Provides functions for interacting with DynamoDB tables:
- Users
- Reflections
- Journal Entries
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Get table names from environment
USERS_TABLE = os.environ.get('DYNAMODB_USERS_TABLE')
REFLECTIONS_TABLE = os.environ.get('DYNAMODB_REFLECTIONS_TABLE')
JOURNAL_TABLE = os.environ.get('DYNAMODB_JOURNAL_TABLE')


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to float/int for JSON serialization."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


# ===== User Operations =====

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by user_id (Cognito sub).

    Args:
        user_id: Cognito user ID (sub claim)

    Returns:
        User dictionary or None if not found
    """
    try:
        table = dynamodb.Table(USERS_TABLE)
        response = table.get_item(Key={'user_id': user_id})

        if 'Item' not in response:
            logger.info(f"User not found: {user_id}")
            return None

        return response['Item']

    except ClientError as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email using GSI.

    Args:
        email: User email address

    Returns:
        User dictionary or None if not found
    """
    try:
        table = dynamodb.Table(USERS_TABLE)
        response = table.query(
            IndexName='Email-index',
            KeyConditionExpression='email = :email',
            ExpressionAttributeValues={':email': email}
        )

        items = response.get('Items', [])
        if not items:
            logger.info(f"User not found by email: {email}")
            return None

        return items[0]  # Should only be one user per email

    except ClientError as e:
        logger.error(f"Error getting user by email {email}: {e}")
        return None


def create_user(
    user_id: str,
    email: str,
    email_verified: bool = False,
    preferences: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Create a new user in DynamoDB.

    Args:
        user_id: Cognito user ID (sub claim)
        email: User email address
        email_verified: Email verification status
        preferences: User preferences dictionary

    Returns:
        True if successful, False otherwise
    """
    try:
        table = dynamodb.Table(USERS_TABLE)

        # Default preferences
        default_preferences = {
            'delivery_time': '06:00',
            'timezone': 'America/Los_Angeles',
            'email_enabled': True,
            'web_only': False,
            'reminder_enabled': False,
            'weekly_digest': False
        }

        if preferences:
            default_preferences.update(preferences)

        item = {
            'user_id': user_id,
            'email': email,
            'email_verified': email_verified,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'preferences': default_preferences,
            'subscription_status': 'active',
            'timezone': default_preferences['timezone'],
            'delivery_time': default_preferences['delivery_time'],
            'last_login': datetime.utcnow().isoformat() + 'Z'
        }

        table.put_item(Item=item)
        logger.info(f"Created user: {user_id}")
        return True

    except ClientError as e:
        logger.error(f"Error creating user {user_id}: {e}")
        return False


def update_user(user_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update user attributes.

    Args:
        user_id: Cognito user ID
        updates: Dictionary of attributes to update

    Returns:
        True if successful, False otherwise
    """
    try:
        table = dynamodb.Table(USERS_TABLE)

        # Build update expression
        update_expr = "SET "
        expr_attr_values = {}
        expr_attr_names = {}

        for i, (key, value) in enumerate(updates.items()):
            attr_name = f"#attr{i}"
            attr_value = f":val{i}"
            update_expr += f"{attr_name} = {attr_value}, "
            expr_attr_names[attr_name] = key
            expr_attr_values[attr_value] = value

        # Remove trailing comma and space
        update_expr = update_expr.rstrip(", ")

        table.update_item(
            Key={'user_id': user_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )

        logger.info(f"Updated user {user_id}: {list(updates.keys())}")
        return True

    except ClientError as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return False


def delete_user(user_id: str) -> bool:
    """
    Delete a user (hard delete).

    Args:
        user_id: Cognito user ID

    Returns:
        True if successful, False otherwise
    """
    try:
        table = dynamodb.Table(USERS_TABLE)
        table.delete_item(Key={'user_id': user_id})

        logger.info(f"Deleted user: {user_id}")
        return True

    except ClientError as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False


# ===== Reflection Operations =====

def get_reflection_by_date(date: str) -> Optional[Dict[str, Any]]:
    """
    Get reflection for a specific date.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        Reflection dictionary or None if not found
    """
    try:
        table = dynamodb.Table(REFLECTIONS_TABLE)
        response = table.get_item(Key={'date': date})

        if 'Item' not in response:
            logger.info(f"Reflection not found for date: {date}")
            return None

        return response['Item']

    except ClientError as e:
        logger.error(f"Error getting reflection for {date}: {e}")
        return None


def create_reflection(
    date: str,
    quote: str,
    attribution: str,
    theme: str,
    reflection: str,
    journaling_prompt: str,
    model_version: str = "claude-sonnet-4-5-20250929",
    security_report: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Create a new reflection in DynamoDB.

    Args:
        date: Date in YYYY-MM-DD format
        quote: Stoic quote
        attribution: Quote attribution
        theme: Monthly theme
        reflection: Generated reflection text
        journaling_prompt: Generated journaling prompt
        model_version: Claude model used
        security_report: Security validation report

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
            'journaling_prompt': journaling_prompt,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'model_version': model_version
        }

        if security_report:
            item['security_report'] = security_report

        table.put_item(Item=item)
        logger.info(f"Created reflection for date: {date}")
        return True

    except ClientError as e:
        logger.error(f"Error creating reflection for {date}: {e}")
        return False


def get_reflections_for_month(year: int, month: int) -> List[Dict[str, Any]]:
    """
    Get all reflections for a specific month (for calendar view).

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        List of reflection dictionaries
    """
    try:
        table = dynamodb.Table(REFLECTIONS_TABLE)

        # Build date range
        start_date = f"{year}-{month:02d}-01"
        # Handle month wraparound
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        end_date = f"{next_year}-{next_month:02d}-01"

        # Scan table (since we don't have a GSI on month)
        # For production, consider adding a GSI on year-month
        response = table.scan(
            FilterExpression='#d >= :start_date AND #d < :end_date',
            ExpressionAttributeNames={'#d': 'date'},
            ExpressionAttributeValues={
                ':start_date': start_date,
                ':end_date': end_date
            }
        )

        return response.get('Items', [])

    except ClientError as e:
        logger.error(f"Error getting reflections for {year}-{month}: {e}")
        return []


# ===== Journal Entry Operations =====

def get_journal_entry(user_id: str, date: str) -> Optional[Dict[str, Any]]:
    """
    Get journal entry for a specific user and date.

    Args:
        user_id: Cognito user ID
        date: Date in YYYY-MM-DD format

    Returns:
        Journal entry dictionary or None if not found
    """
    try:
        table = dynamodb.Table(JOURNAL_TABLE)
        response = table.get_item(
            Key={
                'user_id': user_id,
                'date': date
            }
        )

        if 'Item' not in response:
            logger.info(f"Journal entry not found for user {user_id}, date {date}")
            return None

        return response['Item']

    except ClientError as e:
        logger.error(f"Error getting journal entry for {user_id}/{date}: {e}")
        return None


def create_or_update_journal_entry(
    user_id: str,
    date: str,
    entry: str
) -> bool:
    """
    Create or update a journal entry.

    Args:
        user_id: Cognito user ID
        date: Date in YYYY-MM-DD format
        entry: Journal entry text

    Returns:
        True if successful, False otherwise
    """
    try:
        table = dynamodb.Table(JOURNAL_TABLE)

        # Calculate word count
        word_count = len(entry.split())

        # Check if entry exists
        existing_entry = get_journal_entry(user_id, date)

        item = {
            'user_id': user_id,
            'date': date,
            'entry': entry,
            'word_count': word_count,
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }

        # Add created_at only for new entries
        if not existing_entry:
            item['created_at'] = datetime.utcnow().isoformat() + 'Z'

        table.put_item(Item=item)
        logger.info(f"Created/updated journal entry for {user_id}/{date}")
        return True

    except ClientError as e:
        logger.error(f"Error creating/updating journal entry for {user_id}/{date}: {e}")
        return False


def delete_journal_entry(user_id: str, date: str) -> bool:
    """
    Delete a journal entry.

    Args:
        user_id: Cognito user ID
        date: Date in YYYY-MM-DD format

    Returns:
        True if successful, False otherwise
    """
    try:
        table = dynamodb.Table(JOURNAL_TABLE)
        table.delete_item(
            Key={
                'user_id': user_id,
                'date': date
            }
        )

        logger.info(f"Deleted journal entry for {user_id}/{date}")
        return True

    except ClientError as e:
        logger.error(f"Error deleting journal entry for {user_id}/{date}: {e}")
        return False


def get_journal_entries_for_user(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get journal entries for a user, optionally filtered by date range.

    Args:
        user_id: Cognito user ID
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        limit: Maximum number of entries to return

    Returns:
        List of journal entry dictionaries
    """
    try:
        table = dynamodb.Table(JOURNAL_TABLE)

        query_kwargs = {
            'KeyConditionExpression': 'user_id = :user_id',
            'ExpressionAttributeValues': {':user_id': user_id},
            'Limit': limit,
            'ScanIndexForward': False  # Sort in descending order (newest first)
        }

        # Add date range filtering if provided
        if start_date and end_date:
            query_kwargs['KeyConditionExpression'] += ' AND #d BETWEEN :start_date AND :end_date'
            query_kwargs['ExpressionAttributeNames'] = {'#d': 'date'}
            query_kwargs['ExpressionAttributeValues'][':start_date'] = start_date
            query_kwargs['ExpressionAttributeValues'][':end_date'] = end_date
        elif start_date:
            query_kwargs['KeyConditionExpression'] += ' AND #d >= :start_date'
            query_kwargs['ExpressionAttributeNames'] = {'#d': 'date'}
            query_kwargs['ExpressionAttributeValues'][':start_date'] = start_date
        elif end_date:
            query_kwargs['KeyConditionExpression'] += ' AND #d <= :end_date'
            query_kwargs['ExpressionAttributeNames'] = {'#d': 'date'}
            query_kwargs['ExpressionAttributeValues'][':end_date'] = end_date

        response = table.query(**query_kwargs)
        return response.get('Items', [])

    except ClientError as e:
        logger.error(f"Error getting journal entries for {user_id}: {e}")
        return []
