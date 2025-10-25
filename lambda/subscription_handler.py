"""
Lambda function handler for subscription management API.

Handles subscribe, unsubscribe, and confirm endpoints.
"""

import json
import logging
import os
import re
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
from subscriber_manager import SubscriberManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SES client
ses_client = boto3.client('ses')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for subscription API.

    Routes requests to appropriate handler based on HTTP method and path.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Get environment variables
        table_name = os.environ.get('TABLE_NAME')
        sender_email = os.environ.get('SENDER_EMAIL')
        website_url = os.environ.get('WEBSITE_URL', 'https://jamescmooney.com')

        if not table_name:
            return error_response(500, "Missing TABLE_NAME configuration")

        # Initialize subscriber manager
        manager = SubscriberManager(table_name)

        # Get HTTP method and path
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', ''))
        path = event.get('path', event.get('rawPath', ''))

        logger.info(f"Method: {http_method}, Path: {path}")

        # Route to appropriate handler
        if path.endswith('/subscribe') and http_method == 'POST':
            return handle_subscribe(event, manager, sender_email, website_url)

        elif path.endswith('/confirm') and http_method == 'GET':
            return handle_confirm(event, manager, website_url)

        elif path.endswith('/unsubscribe') and http_method == 'GET':
            return handle_unsubscribe_page(event, manager)

        elif path.endswith('/unsubscribe') and http_method == 'POST':
            return handle_unsubscribe(event, manager)

        else:
            return error_response(404, "Endpoint not found")

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return error_response(500, "Internal server error")


def handle_subscribe(
    event: Dict[str, Any],
    manager: SubscriberManager,
    sender_email: str,
    website_url: str
) -> Dict[str, Any]:
    """
    Handle POST /api/subscribe - Create new subscription.

    Args:
        event: API Gateway event
        manager: SubscriberManager instance
        sender_email: Email address to send confirmation from
        website_url: Base website URL for confirmation links

    Returns:
        API Gateway response
    """
    try:
        # Parse request body
        body = parse_body(event)
        email = body.get('email', '').strip()

        if not email:
            return error_response(400, "Email is required")

        # Validate email format
        if not is_valid_email(email):
            return error_response(400, "Invalid email format")

        # Create subscriber
        subscriber = manager.create_subscriber(email, source='web')

        # Send confirmation email
        confirmation_url = f"{website_url}/confirm.html?token={subscriber['confirmation_token']}"

        send_confirmation_email(
            sender=sender_email,
            recipient=email,
            confirmation_url=confirmation_url
        )

        logger.info(f"Successfully created subscription for: {email}")

        return success_response({
            'success': True,
            'message': 'Please check your email to confirm your subscription.',
            'email': email
        })

    except ValueError as e:
        # Email already subscribed or other validation error
        return error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error in handle_subscribe: {e}", exc_info=True)
        return error_response(500, "Failed to process subscription")


def handle_confirm(
    event: Dict[str, Any],
    manager: SubscriberManager,
    website_url: str
) -> Dict[str, Any]:
    """
    Handle GET /api/confirm - Confirm email subscription.

    Args:
        event: API Gateway event
        manager: SubscriberManager instance
        website_url: Base website URL

    Returns:
        API Gateway response with HTML
    """
    try:
        # Get token from query parameters
        params = event.get('queryStringParameters') or {}
        token = params.get('token', '').strip()

        if not token:
            return html_response(400, render_error_page(
                "Invalid Link",
                "No confirmation token provided. Please use the link from your confirmation email."
            ))

        # Confirm subscriber
        subscriber = manager.confirm_subscriber(token)

        if not subscriber:
            return html_response(404, render_error_page(
                "Invalid or Expired Link",
                "This confirmation link is invalid or has expired. Please try subscribing again."
            ))

        logger.info(f"Successfully confirmed subscription: {subscriber['email']}")

        return html_response(200, render_success_page(
            "Successfully Subscribed!",
            "You will receive your first Daily Stoic Reflection tomorrow morning at 6 AM PT.",
            website_url
        ))

    except Exception as e:
        logger.error(f"Error in handle_confirm: {e}", exc_info=True)
        return html_response(500, render_error_page(
            "Error",
            "An error occurred while confirming your subscription. Please try again later."
        ))


def handle_unsubscribe_page(
    event: Dict[str, Any],
    manager: SubscriberManager
) -> Dict[str, Any]:
    """
    Handle GET /api/unsubscribe - Display unsubscribe confirmation page.

    Args:
        event: API Gateway event
        manager: SubscriberManager instance

    Returns:
        API Gateway response with HTML form
    """
    try:
        params = event.get('queryStringParameters') or {}
        email = params.get('email', '').strip()
        token = params.get('token', '').strip()

        if not email or not token:
            return html_response(400, render_error_page(
                "Invalid Link",
                "Missing email or token. Please use the unsubscribe link from your email."
            ))

        return html_response(200, render_unsubscribe_page(email, token))

    except Exception as e:
        logger.error(f"Error in handle_unsubscribe_page: {e}", exc_info=True)
        return html_response(500, render_error_page(
            "Error",
            "An error occurred. Please try again later."
        ))


def handle_unsubscribe(
    event: Dict[str, Any],
    manager: SubscriberManager
) -> Dict[str, Any]:
    """
    Handle POST /api/unsubscribe - Process unsubscribe request.

    Args:
        event: API Gateway event
        manager: SubscriberManager instance

    Returns:
        API Gateway response
    """
    try:
        # Parse request body
        body = parse_body(event)
        email = body.get('email', '').strip()
        token = body.get('token', '').strip()

        if not email or not token:
            return error_response(400, "Email and token are required")

        # Unsubscribe
        success = manager.unsubscribe(email, token)

        if not success:
            return error_response(400, "Invalid email or token")

        logger.info(f"Successfully unsubscribed: {email}")

        return success_response({
            'success': True,
            'message': 'You have been successfully unsubscribed.',
            'email': email
        })

    except Exception as e:
        logger.error(f"Error in handle_unsubscribe: {e}", exc_info=True)
        return error_response(500, "Failed to process unsubscribe request")


def send_confirmation_email(sender: str, recipient: str, confirmation_url: str) -> None:
    """
    Send confirmation email to new subscriber.

    Args:
        sender: Sender email address
        recipient: Recipient email address
        confirmation_url: URL to confirm subscription

    Raises:
        ClientError: If SES send fails
    """
    subject = "Confirm Your Daily Stoic Reflection Subscription"

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Confirm Your Subscription</title>
</head>
<body style="font-family: Georgia, 'Times New Roman', serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h1 style="color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 20px;">
            Daily Stoic Reflection
        </h1>

        <p style="font-size: 16px; margin: 20px 0;">
            Thank you for subscribing to Daily Stoic Reflection!
        </p>

        <p style="font-size: 16px; margin: 20px 0;">
            To confirm your subscription and start receiving daily stoic wisdom at 6 AM PT, please click the button below:
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{confirmation_url}"
               style="background-color: #3498db; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-size: 16px;">
                Confirm Subscription
            </a>
        </div>

        <p style="font-size: 14px; color: #7f8c8d; margin: 20px 0;">
            Or copy and paste this link into your browser:<br>
            <a href="{confirmation_url}" style="color: #3498db; word-break: break-all;">{confirmation_url}</a>
        </p>

        <p style="font-size: 14px; color: #7f8c8d; margin: 30px 0 0 0; border-top: 1px solid #ecf0f1; padding-top: 20px; text-align: center;">
            If you didn't request this subscription, you can safely ignore this email.
        </p>
    </div>
</body>
</html>"""

    text_body = f"""Daily Stoic Reflection - Confirm Your Subscription

Thank you for subscribing to Daily Stoic Reflection!

To confirm your subscription and start receiving daily stoic wisdom at 6 AM PT, please click this link:

{confirmation_url}

If you didn't request this subscription, you can safely ignore this email.

---
Daily Stoic Reflection • Powered by Claude
"""

    try:
        response = ses_client.send_email(
            Source=sender,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                    'Text': {'Data': text_body, 'Charset': 'UTF-8'}
                }
            }
        )
        logger.info(f"Sent confirmation email to {recipient}: {response['MessageId']}")
    except ClientError as e:
        logger.error(f"Error sending confirmation email to {recipient}: {e}")
        raise


# Utility functions

def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse request body from event."""
    body = event.get('body', '{}')
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            # Try parsing as form data
            if '=' in body:
                return dict(param.split('=') for param in body.split('&'))
            return {}
    return body


def is_valid_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def success_response(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
    """Create a successful JSON response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(data)
    }


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create an error JSON response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }


def html_response(status_code: int, html: str) -> Dict[str, Any]:
    """Create an HTML response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*'
        },
        'body': html
    }


def render_success_page(title: str, message: str, website_url: str) -> str:
    """Render a success page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #27ae60;
            font-size: 28px;
            margin-bottom: 20px;
        }}
        p {{
            font-size: 16px;
            margin: 20px 0;
        }}
        .checkmark {{
            font-size: 48px;
            color: #27ae60;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="checkmark">✓</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <p><a href="{website_url}">Return to Website</a></p>
    </div>
</body>
</html>"""


def render_error_page(title: str, message: str) -> str:
    """Render an error page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #e74c3c;
            font-size: 28px;
            margin-bottom: 20px;
        }}
        p {{
            font-size: 16px;
            margin: 20px 0;
        }}
        .error-icon {{
            font-size: 48px;
            color: #e74c3c;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">⚠</div>
        <h1>{title}</h1>
        <p>{message}</p>
    </div>
</body>
</html>"""


def render_unsubscribe_page(email: str, token: str) -> str:
    """Render the unsubscribe confirmation page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unsubscribe from Daily Stoic Reflections</title>
    <style>
        body {{
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            font-size: 28px;
            margin-bottom: 20px;
            text-align: center;
        }}
        p {{
            font-size: 16px;
            margin: 20px 0;
        }}
        .email {{
            font-weight: bold;
            color: #3498db;
        }}
        button {{
            background-color: #e74c3c;
            color: white;
            padding: 15px 30px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            display: block;
            margin: 30px auto;
        }}
        button:hover {{
            background-color: #c0392b;
        }}
        #message {{
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            display: none;
        }}
        .success {{
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .error {{
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Unsubscribe from Daily Stoic Reflections</h1>
        <p>Are you sure you want to unsubscribe <span class="email">{email}</span> from Daily Stoic Reflections?</p>
        <p>You will no longer receive daily stoic wisdom and reflections.</p>

        <form id="unsubscribeForm">
            <button type="submit">Confirm Unsubscribe</button>
        </form>

        <div id="message"></div>
    </div>

    <script>
        document.getElementById('unsubscribeForm').addEventListener('submit', async function(e) {{
            e.preventDefault();

            const button = this.querySelector('button');
            button.disabled = true;
            button.textContent = 'Processing...';

            try {{
                const response = await fetch('/api/unsubscribe', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        email: '{email}',
                        token: '{token}'
                    }})
                }});

                const data = await response.json();
                const messageDiv = document.getElementById('message');

                if (data.success) {{
                    messageDiv.className = 'success';
                    messageDiv.textContent = 'You have been successfully unsubscribed.';
                    button.style.display = 'none';
                }} else {{
                    messageDiv.className = 'error';
                    messageDiv.textContent = 'Error: ' + (data.error || 'Unknown error');
                    button.disabled = false;
                    button.textContent = 'Confirm Unsubscribe';
                }}

                messageDiv.style.display = 'block';
            }} catch (error) {{
                const messageDiv = document.getElementById('message');
                messageDiv.className = 'error';
                messageDiv.textContent = 'Network error. Please try again.';
                messageDiv.style.display = 'block';

                button.disabled = false;
                button.textContent = 'Confirm Unsubscribe';
            }}
        }});
    </script>
</body>
</html>"""
