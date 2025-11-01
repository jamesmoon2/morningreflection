"""
Lambda handler for User API endpoints.

Handles:
- GET /user/profile - Get user profile
- PUT /user/profile - Update user profile
- PUT /user/preferences - Update user preferences
- DELETE /user/account - Delete user account
"""

import json
import logging
import os
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from api_utils import (
    success_response,
    error_response,
    get_user_id_from_event,
    get_user_email_from_event,
    parse_request_body,
    validate_required_fields
)
from dynamodb_operations import (
    get_user_by_id,
    create_user,
    update_user,
    delete_user
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = os.environ.get('USER_POOL_ID')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for User API.

    Routes requests based on HTTP method and resource path.
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Extract HTTP method and resource
        http_method = event.get('httpMethod')
        resource = event.get('resource')

        logger.info(f"Method: {http_method}, Resource: {resource}")

        # Get user ID from Cognito authorizer
        user_id = get_user_id_from_event(event)
        if not user_id:
            return error_response("Unauthorized: No user ID in token", status_code=401)

        # Route to appropriate handler
        if resource == '/user/profile':
            if http_method == 'GET':
                return handle_get_profile(user_id, event)
            elif http_method == 'PUT':
                return handle_update_profile(user_id, event)

        elif resource == '/user/preferences':
            if http_method == 'PUT':
                return handle_update_preferences(user_id, event)

        elif resource == '/user/account':
            if http_method == 'DELETE':
                return handle_delete_account(user_id, event)

        # Unknown endpoint
        return error_response(
            f"Endpoint not found: {http_method} {resource}",
            status_code=404
        )

    except Exception as e:
        logger.error(f"Unexpected error in user_api handler: {e}", exc_info=True)
        return error_response(
            "Internal server error",
            status_code=500
        )


def handle_get_profile(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /user/profile.

    Returns user profile information from DynamoDB.
    If user doesn't exist in DynamoDB, creates a new record.
    """
    try:
        logger.info(f"Getting profile for user: {user_id}")

        # Get user from DynamoDB
        user = get_user_by_id(user_id)

        # If user doesn't exist in DynamoDB, create them
        if not user:
            logger.info(f"User not found in DynamoDB, creating: {user_id}")

            # Get email from Cognito claims
            email = get_user_email_from_event(event)
            if not email:
                return error_response("Unable to retrieve user email", status_code=500)

            # Create user in DynamoDB
            success = create_user(
                user_id=user_id,
                email=email,
                email_verified=True  # If they have a valid token, email is verified
            )

            if not success:
                return error_response("Failed to create user profile", status_code=500)

            # Fetch the newly created user
            user = get_user_by_id(user_id)

        # Return user profile
        return success_response({
            "user_id": user['user_id'],
            "email": user['email'],
            "email_verified": user.get('email_verified', False),
            "created_at": user.get('created_at'),
            "last_login": user.get('last_login'),
            "subscription_status": user.get('subscription_status', 'active'),
            "timezone": user.get('timezone'),
            "delivery_time": user.get('delivery_time'),
            "preferences": user.get('preferences', {})
        })

    except Exception as e:
        logger.error(f"Error getting profile for user {user_id}: {e}", exc_info=True)
        return error_response("Failed to retrieve user profile", status_code=500)


def handle_update_profile(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle PUT /user/profile.

    Updates user profile information (currently only email and subscription_status).
    """
    try:
        logger.info(f"Updating profile for user: {user_id}")

        # Parse request body
        body = parse_request_body(event)
        if not body:
            return error_response("Invalid request body", status_code=400)

        # Extract allowed fields
        updates = {}

        if 'subscription_status' in body:
            status = body['subscription_status']
            if status not in ['active', 'paused', 'cancelled']:
                return error_response(
                    "Invalid subscription_status. Must be: active, paused, or cancelled",
                    status_code=400
                )
            updates['subscription_status'] = status

        # Note: Email updates should be handled through Cognito, not here
        # We'll keep email read-only from DynamoDB perspective

        if not updates:
            return error_response("No valid fields to update", status_code=400)

        # Update user in DynamoDB
        success = update_user(user_id, updates)
        if not success:
            return error_response("Failed to update user profile", status_code=500)

        # Return updated profile
        return handle_get_profile(user_id, event)

    except Exception as e:
        logger.error(f"Error updating profile for user {user_id}: {e}", exc_info=True)
        return error_response("Failed to update user profile", status_code=500)


def handle_update_preferences(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle PUT /user/preferences.

    Updates user preferences (delivery time, timezone, email settings).
    """
    try:
        logger.info(f"Updating preferences for user: {user_id}")

        # Parse request body
        body = parse_request_body(event)
        if not body:
            return error_response("Invalid request body", status_code=400)

        # Ensure user exists
        user = get_user_by_id(user_id)
        if not user:
            return error_response("User not found", status_code=404)

        # Get current preferences
        current_prefs = user.get('preferences', {})

        # Update preferences with new values
        allowed_pref_keys = [
            'delivery_time',
            'timezone',
            'email_enabled',
            'web_only',
            'reminder_enabled',
            'weekly_digest'
        ]

        for key in allowed_pref_keys:
            if key in body:
                current_prefs[key] = body[key]

        # Update top-level fields for easier querying
        updates = {
            'preferences': current_prefs
        }

        if 'delivery_time' in current_prefs:
            updates['delivery_time'] = current_prefs['delivery_time']
        if 'timezone' in current_prefs:
            updates['timezone'] = current_prefs['timezone']

        # Save to DynamoDB
        success = update_user(user_id, updates)
        if not success:
            return error_response("Failed to update preferences", status_code=500)

        # Return updated profile
        return handle_get_profile(user_id, event)

    except Exception as e:
        logger.error(f"Error updating preferences for user {user_id}: {e}", exc_info=True)
        return error_response("Failed to update preferences", status_code=500)


def handle_delete_account(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle DELETE /user/account.

    Deletes user account from both Cognito and DynamoDB.
    This is a permanent action for GDPR compliance.
    """
    try:
        logger.info(f"Deleting account for user: {user_id}")

        # Delete user from DynamoDB
        dynamodb_success = delete_user(user_id)

        # Delete user from Cognito
        cognito_success = False
        try:
            # Get username from user pool (Cognito sub = user_id)
            cognito_client.admin_delete_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            cognito_success = True
            logger.info(f"Deleted user from Cognito: {user_id}")
        except ClientError as e:
            logger.error(f"Error deleting user from Cognito: {e}")
            # Continue even if Cognito deletion fails

        # Journal entries will remain in DynamoDB (can be deleted separately if needed)
        # For complete GDPR compliance, you might want to delete journal entries too

        if dynamodb_success:
            return success_response({
                "message": "Account deleted successfully",
                "dynamodb_deleted": dynamodb_success,
                "cognito_deleted": cognito_success
            })
        else:
            return error_response(
                "Failed to delete account from database",
                status_code=500
            )

    except Exception as e:
        logger.error(f"Error deleting account for user {user_id}: {e}", exc_info=True)
        return error_response("Failed to delete account", status_code=500)
