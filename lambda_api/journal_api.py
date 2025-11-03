"""
Lambda handler for Journal API endpoints.

Handles:
- POST /journal - Create or update journal entry
- GET /journal/{date} - Get journal entry for specific date
- DELETE /journal/{date} - Delete journal entry
- GET /journal/list - Get list of journal entries (with date range filtering)
"""

import json
import logging
import sys
import os
from typing import Dict, Any

from api_utils import (
    success_response,
    error_response,
    get_user_id_from_event,
    get_path_parameter,
    get_query_parameter,
    parse_request_body,
    validate_required_fields,
    validate_date_format
)
from dynamodb_operations import (
    get_journal_entry,
    create_or_update_journal_entry,
    delete_journal_entry,
    get_journal_entries_for_user
)

# Import security validation modules
try:
    from security import (
        ContentSanitizer,
        MaliciousPatternDetector,
        CharacterValidator
    )
    SECURITY_MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Security modules not available: {e}. Journal validation will be limited.")
    SECURITY_MODULES_AVAILABLE = False

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Journal API.

    Routes requests based on HTTP method and resource path.
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Extract HTTP method and resource
        http_method = event.get('httpMethod')
        resource = event.get('resource')

        logger.info(f"Method: {http_method}, Resource: {resource}")

        # Verify user is authenticated
        user_id = get_user_id_from_event(event)
        if not user_id:
            return error_response("Unauthorized: No user ID in token", status_code=401)

        # Route to appropriate handler
        if resource == '/journal' and http_method == 'POST':
            return handle_create_or_update(user_id, event)

        elif resource == '/journal/{date}' and http_method == 'GET':
            return handle_get_entry(user_id, event)

        elif resource == '/journal/{date}' and http_method == 'DELETE':
            return handle_delete_entry(user_id, event)

        elif resource == '/journal/list' and http_method == 'GET':
            return handle_list_entries(user_id, event)

        # Unknown endpoint
        return error_response(
            f"Endpoint not found: {http_method} {resource}",
            status_code=404
        )

    except Exception as e:
        logger.error(f"Unexpected error in journal_api handler: {e}", exc_info=True)
        return error_response(
            "Internal server error",
            status_code=500
        )


def validate_journal_entry(entry: str) -> Dict[str, Any]:
    """
    Validate journal entry using security modules.

    Args:
        entry: Journal entry text

    Returns:
        Dictionary with validation results:
        - valid: bool
        - sanitized_entry: str (if valid)
        - error_message: str (if invalid)
    """
    if not SECURITY_MODULES_AVAILABLE:
        # Basic validation if security modules aren't available
        if len(entry) > 10000:
            return {
                "valid": False,
                "error_message": "Journal entry exceeds 10,000 character limit"
            }
        return {
            "valid": True,
            "sanitized_entry": entry
        }

    try:
        # 1. Sanitize content
        sanitizer = ContentSanitizer()
        sanitized = sanitizer.sanitize(entry)

        # 2. Check for malicious patterns (XSS, scripts, etc.)
        pattern_detector = MaliciousPatternDetector()
        patterns_result = pattern_detector.check_content(sanitized)

        if patterns_result["has_malicious_patterns"]:
            logger.warning(f"Malicious patterns detected in journal entry: {patterns_result['patterns_found']}")
            return {
                "valid": False,
                "error_message": "Journal entry contains prohibited content. Please remove any HTML tags, scripts, or suspicious patterns."
            }

        # 3. Check length (max 10,000 chars)
        if len(sanitized) > 10000:
            return {
                "valid": False,
                "error_message": "Journal entry exceeds 10,000 character limit"
            }

        # 4. Check minimum length (at least 1 char after sanitization)
        if len(sanitized.strip()) < 1:
            return {
                "valid": False,
                "error_message": "Journal entry cannot be empty"
            }

        # 5. Character validation (homoglyphs, excessive repetition)
        char_validator = CharacterValidator()
        char_result = char_validator.validate(sanitized)

        if not char_result["valid"]:
            logger.warning(f"Character validation failed: {char_result['reason']}")
            return {
                "valid": False,
                "error_message": f"Invalid characters in journal entry: {char_result['reason']}"
            }

        # All validations passed
        return {
            "valid": True,
            "sanitized_entry": sanitized
        }

    except Exception as e:
        logger.error(f"Error validating journal entry: {e}", exc_info=True)
        return {
            "valid": False,
            "error_message": "Failed to validate journal entry"
        }


def handle_create_or_update(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /journal.

    Creates or updates a journal entry.
    Requires: date, entry
    """
    try:
        # Parse request body
        body = parse_request_body(event)
        if not body:
            return error_response("Invalid request body", status_code=400)

        # Validate required fields
        error_msg = validate_required_fields(body, ['date', 'entry'])
        if error_msg:
            return error_response(error_msg, status_code=400)

        date = body['date']
        entry = body['entry']

        # Validate date format
        if not validate_date_format(date):
            return error_response(
                "Invalid date format. Use YYYY-MM-DD",
                status_code=400
            )

        logger.info(f"Creating/updating journal entry for user {user_id}, date: {date}")

        # Validate journal entry content
        validation_result = validate_journal_entry(entry)

        if not validation_result["valid"]:
            return error_response(
                validation_result["error_message"],
                status_code=400,
                error_code="VALIDATION_ERROR"
            )

        sanitized_entry = validation_result["sanitized_entry"]

        # Save to DynamoDB
        success = create_or_update_journal_entry(
            user_id=user_id,
            date=date,
            entry=sanitized_entry
        )

        if not success:
            return error_response("Failed to save journal entry", status_code=500)

        # Return the saved entry
        saved_entry = get_journal_entry(user_id, date)

        return success_response({
            "message": "Journal entry saved successfully",
            "entry": {
                "user_id": saved_entry['user_id'],
                "date": saved_entry['date'],
                "entry": saved_entry['entry'],
                "word_count": saved_entry.get('word_count', 0),
                "created_at": saved_entry.get('created_at'),
                "updated_at": saved_entry.get('updated_at')
            }
        }, status_code=201)

    except Exception as e:
        logger.error(f"Error creating/updating journal entry for user {user_id}: {e}", exc_info=True)
        return error_response("Failed to save journal entry", status_code=500)


def handle_get_entry(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /journal/{date}.

    Returns journal entry for a specific date.
    """
    try:
        # Get date from path parameter
        date = get_path_parameter(event, 'date')

        if not date:
            return error_response("Missing date parameter", status_code=400)

        # Validate date format
        if not validate_date_format(date):
            return error_response(
                "Invalid date format. Use YYYY-MM-DD",
                status_code=400
            )

        logger.info(f"Getting journal entry for user {user_id}, date: {date}")

        # Get entry from DynamoDB
        entry = get_journal_entry(user_id, date)

        if not entry:
            return error_response(
                f"No journal entry found for date: {date}",
                status_code=404,
                error_code="ENTRY_NOT_FOUND"
            )

        # Return entry
        return success_response({
            "user_id": entry['user_id'],
            "date": entry['date'],
            "entry": entry['entry'],
            "word_count": entry.get('word_count', 0),
            "created_at": entry.get('created_at'),
            "updated_at": entry.get('updated_at')
        })

    except Exception as e:
        logger.error(f"Error getting journal entry for user {user_id}, date {date}: {e}", exc_info=True)
        return error_response("Failed to retrieve journal entry", status_code=500)


def handle_delete_entry(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle DELETE /journal/{date}.

    Deletes journal entry for a specific date.
    """
    try:
        # Get date from path parameter
        date = get_path_parameter(event, 'date')

        if not date:
            return error_response("Missing date parameter", status_code=400)

        # Validate date format
        if not validate_date_format(date):
            return error_response(
                "Invalid date format. Use YYYY-MM-DD",
                status_code=400
            )

        logger.info(f"Deleting journal entry for user {user_id}, date: {date}")

        # Check if entry exists
        entry = get_journal_entry(user_id, date)
        if not entry:
            return error_response(
                f"No journal entry found for date: {date}",
                status_code=404,
                error_code="ENTRY_NOT_FOUND"
            )

        # Delete from DynamoDB
        success = delete_journal_entry(user_id, date)

        if not success:
            return error_response("Failed to delete journal entry", status_code=500)

        return success_response({
            "message": "Journal entry deleted successfully",
            "date": date
        })

    except Exception as e:
        logger.error(f"Error deleting journal entry for user {user_id}, date {date}: {e}", exc_info=True)
        return error_response("Failed to delete journal entry", status_code=500)


def handle_list_entries(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /journal/list?from=YYYY-MM-DD&to=YYYY-MM-DD&limit=100.

    Returns list of journal entries for the user, optionally filtered by date range.
    """
    try:
        # Get query parameters
        start_date = get_query_parameter(event, 'from')
        end_date = get_query_parameter(event, 'to')
        limit_str = get_query_parameter(event, 'limit')

        # Parse limit (default: 100, max: 500)
        limit = 100
        if limit_str:
            try:
                limit = int(limit_str)
                if limit > 500:
                    limit = 500
                elif limit < 1:
                    limit = 1
            except ValueError:
                return error_response("Invalid limit parameter. Must be an integer", status_code=400)

        # Validate date formats if provided
        if start_date and not validate_date_format(start_date):
            return error_response("Invalid 'from' date format. Use YYYY-MM-DD", status_code=400)

        if end_date and not validate_date_format(end_date):
            return error_response("Invalid 'to' date format. Use YYYY-MM-DD", status_code=400)

        logger.info(f"Listing journal entries for user {user_id}, from: {start_date}, to: {end_date}, limit: {limit}")

        # Get entries from DynamoDB
        entries = get_journal_entries_for_user(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        # Format entries for response (exclude entry content, just metadata)
        entries_list = []
        for entry in entries:
            entries_list.append({
                "date": entry['date'],
                "word_count": entry.get('word_count', 0),
                "created_at": entry.get('created_at'),
                "updated_at": entry.get('updated_at')
            })

        return success_response({
            "entries": entries_list,
            "count": len(entries_list),
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit
        })

    except Exception as e:
        logger.error(f"Error listing journal entries for user {user_id}: {e}", exc_info=True)
        return error_response("Failed to retrieve journal entries", status_code=500)
