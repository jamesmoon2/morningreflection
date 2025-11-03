"""
Utility functions for API Lambda handlers.

Provides helpers for:
- HTTP response formatting
- Request validation
- Error handling
- CORS headers
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def success_response(
    body: Dict[str, Any],
    status_code: int = 200,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a successful API Gateway response.

    Args:
        body: Response body dictionary
        status_code: HTTP status code (default: 200)
        headers: Additional headers

    Returns:
        API Gateway response dictionary
    """
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",  # Update to specific domain in production
        "Access-Control-Allow-Credentials": "true"
    }

    if headers:
        default_headers.update(headers)

    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body)
    }


def error_response(
    message: str,
    status_code: int = 400,
    error_code: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create an error API Gateway response.

    Args:
        message: Error message
        status_code: HTTP status code (default: 400)
        error_code: Optional error code for client handling
        headers: Additional headers

    Returns:
        API Gateway response dictionary
    """
    body = {
        "error": message,
        "status": status_code
    }

    if error_code:
        body["code"] = error_code

    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",  # Update to specific domain in production
        "Access-Control-Allow-Credentials": "true"
    }

    if headers:
        default_headers.update(headers)

    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body)
    }


def get_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user ID from Cognito authorizer claims.

    Args:
        event: API Gateway event

    Returns:
        User ID (Cognito sub claim) or None
    """
    try:
        # Cognito authorizer puts claims in requestContext.authorizer.claims
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        user_id = claims.get("sub")  # Cognito subject (user ID)

        if not user_id:
            logger.warning("No user ID found in Cognito claims")
            return None

        return user_id

    except Exception as e:
        logger.error(f"Error extracting user ID from event: {e}")
        return None


def get_user_email_from_event(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user email from Cognito authorizer claims.

    Args:
        event: API Gateway event

    Returns:
        User email or None
    """
    try:
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        email = claims.get("email")

        if not email:
            logger.warning("No email found in Cognito claims")
            return None

        return email

    except Exception as e:
        logger.error(f"Error extracting email from event: {e}")
        return None


def parse_request_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse JSON body from API Gateway event.

    Args:
        event: API Gateway event

    Returns:
        Parsed JSON dictionary or None if parsing fails
    """
    try:
        body = event.get("body")

        if not body:
            return None

        # Body might be a string or already parsed
        if isinstance(body, str):
            return json.loads(body)
        else:
            return body

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse request body: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing request body: {e}")
        return None


def get_path_parameter(event: Dict[str, Any], param_name: str) -> Optional[str]:
    """
    Get path parameter from API Gateway event.

    Args:
        event: API Gateway event
        param_name: Parameter name (e.g., "date")

    Returns:
        Parameter value or None
    """
    try:
        path_params = event.get("pathParameters", {})
        return path_params.get(param_name) if path_params else None

    except Exception as e:
        logger.error(f"Error getting path parameter '{param_name}': {e}")
        return None


def get_query_parameter(event: Dict[str, Any], param_name: str) -> Optional[str]:
    """
    Get query string parameter from API Gateway event.

    Args:
        event: API Gateway event
        param_name: Parameter name (e.g., "month")

    Returns:
        Parameter value or None
    """
    try:
        query_params = event.get("queryStringParameters", {})
        return query_params.get(param_name) if query_params else None

    except Exception as e:
        logger.error(f"Error getting query parameter '{param_name}': {e}")
        return None


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: list[str]
) -> Optional[str]:
    """
    Validate that required fields are present in data.

    Args:
        data: Data dictionary
        required_fields: List of required field names

    Returns:
        Error message if validation fails, None if successful
    """
    missing_fields = []

    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)

    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"

    return None


def validate_date_format(date_str: str) -> bool:
    """
    Validate date string is in YYYY-MM-DD format.

    Args:
        date_str: Date string

    Returns:
        True if valid, False otherwise
    """
    import re
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str))
