"""
Lambda handler for Reflections API endpoints.

Handles:
- GET /reflections/today - Get today's reflection
- GET /reflections/{date} - Get reflection for specific date
- GET /reflections/calendar - Get calendar metadata for a month
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List
import calendar

from api_utils import (
    success_response,
    error_response,
    get_user_id_from_event,
    get_path_parameter,
    get_query_parameter,
    validate_date_format
)
from dynamodb_operations import (
    get_reflection_by_date,
    get_reflections_for_month
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Reflections API.

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
        if resource == '/reflections/today' and http_method == 'GET':
            return handle_get_today(user_id, event)

        elif resource == '/reflections/{date}' and http_method == 'GET':
            return handle_get_by_date(user_id, event)

        elif resource == '/reflections/calendar' and http_method == 'GET':
            return handle_get_calendar(user_id, event)

        # Unknown endpoint
        return error_response(
            f"Endpoint not found: {http_method} {resource}",
            status_code=404
        )

    except Exception as e:
        logger.error(f"Unexpected error in reflections_api handler: {e}", exc_info=True)
        return error_response(
            "Internal server error",
            status_code=500
        )


def handle_get_today(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /reflections/today.

    Returns today's reflection and journaling prompt.
    """
    try:
        # Get today's date in YYYY-MM-DD format
        today = datetime.utcnow().strftime('%Y-%m-%d')

        logger.info(f"Getting today's reflection for user {user_id}, date: {today}")

        # Get reflection from DynamoDB
        reflection = get_reflection_by_date(today)

        if not reflection:
            return error_response(
                "Today's reflection has not been generated yet. Please check back later.",
                status_code=404,
                error_code="REFLECTION_NOT_FOUND"
            )

        # Return reflection
        return success_response({
            "date": reflection['date'],
            "quote": reflection['quote'],
            "attribution": reflection['attribution'],
            "theme": reflection['theme'],
            "reflection": reflection['reflection'],
            "journaling_prompt": reflection.get('journaling_prompt', ''),
            "generated_at": reflection.get('generated_at')
        })

    except Exception as e:
        logger.error(f"Error getting today's reflection for user {user_id}: {e}", exc_info=True)
        return error_response("Failed to retrieve today's reflection", status_code=500)


def handle_get_by_date(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /reflections/{date}.

    Returns reflection for a specific date.
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

        logger.info(f"Getting reflection for user {user_id}, date: {date}")

        # Get reflection from DynamoDB
        reflection = get_reflection_by_date(date)

        if not reflection:
            return error_response(
                f"No reflection found for date: {date}",
                status_code=404,
                error_code="REFLECTION_NOT_FOUND"
            )

        # Return reflection
        return success_response({
            "date": reflection['date'],
            "quote": reflection['quote'],
            "attribution": reflection['attribution'],
            "theme": reflection['theme'],
            "reflection": reflection['reflection'],
            "journaling_prompt": reflection.get('journaling_prompt', ''),
            "generated_at": reflection.get('generated_at')
        })

    except Exception as e:
        logger.error(f"Error getting reflection for user {user_id}, date {date}: {e}", exc_info=True)
        return error_response("Failed to retrieve reflection", status_code=500)


def handle_get_calendar(user_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /reflections/calendar?month=YYYY-MM.

    Returns calendar metadata showing which dates have reflections.
    This is used for the calendar view in the frontend.
    """
    try:
        # Get month parameter (format: YYYY-MM)
        month_param = get_query_parameter(event, 'month')

        if not month_param:
            # Default to current month
            now = datetime.utcnow()
            year = now.year
            month = now.month
        else:
            # Parse month parameter
            try:
                year, month = month_param.split('-')
                year = int(year)
                month = int(month)

                if month < 1 or month > 12:
                    return error_response(
                        "Invalid month. Must be between 1 and 12",
                        status_code=400
                    )

            except ValueError:
                return error_response(
                    "Invalid month format. Use YYYY-MM",
                    status_code=400
                )

        logger.info(f"Getting calendar for user {user_id}, month: {year}-{month:02d}")

        # Get all reflections for this month
        reflections = get_reflections_for_month(year, month)

        # Build calendar data
        days_in_month = calendar.monthrange(year, month)[1]
        calendar_days = []

        # Create a set of dates that have reflections
        reflection_dates = {r['date'] for r in reflections}

        # Build response for each day
        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"

            calendar_days.append({
                "date": date_str,
                "has_reflection": date_str in reflection_dates,
                # has_journal_entry will be added in Phase 3 when we integrate with journal API
            })

        return success_response({
            "year": year,
            "month": month,
            "days": calendar_days
        })

    except Exception as e:
        logger.error(f"Error getting calendar for user {user_id}: {e}", exc_info=True)
        return error_response("Failed to retrieve calendar data", status_code=500)
