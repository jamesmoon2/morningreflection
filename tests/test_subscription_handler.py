"""
Unit tests for subscription_handler module.
"""

import unittest
import sys
import os
import json

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from subscription_handler import (
    parse_body,
    is_valid_email,
    success_response,
    error_response,
    html_response
)


class TestSubscriptionHandler(unittest.TestCase):
    """Test cases for subscription handler utility functions."""

    def test_parse_body_json(self):
        """Test parsing JSON request body."""
        event = {
            'body': '{"email": "test@example.com", "name": "Test User"}'
        }

        body = parse_body(event)

        self.assertEqual(body['email'], 'test@example.com')
        self.assertEqual(body['name'], 'Test User')

    def test_parse_body_form_data(self):
        """Test parsing form-encoded request body."""
        event = {
            'body': 'email=test@example.com&name=Test+User'
        }

        body = parse_body(event)

        self.assertIn('email', body)
        self.assertIn('name', body)

    def test_parse_body_empty(self):
        """Test parsing empty request body."""
        event = {'body': ''}

        body = parse_body(event)

        self.assertEqual(body, {})

    def test_parse_body_dict(self):
        """Test parsing when body is already a dict."""
        event = {
            'body': {'email': 'test@example.com'}
        }

        body = parse_body(event)

        self.assertEqual(body['email'], 'test@example.com')

    def test_is_valid_email_valid(self):
        """Test email validation with valid emails."""
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'first+last@company.org',
            '123@test.com',
            'test_email@domain-name.com'
        ]

        for email in valid_emails:
            with self.subTest(email=email):
                self.assertTrue(is_valid_email(email))

    def test_is_valid_email_invalid(self):
        """Test email validation with invalid emails."""
        invalid_emails = [
            '',
            'not-an-email',
            '@example.com',
            'test@',
            'test @example.com',
            'test@example',
            'test..double@example.com'
        ]

        for email in invalid_emails:
            with self.subTest(email=email):
                self.assertFalse(is_valid_email(email))

    def test_success_response(self):
        """Test creation of success response."""
        data = {'success': True, 'message': 'Operation successful'}

        response = success_response(data)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Content-Type', response['headers'])
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertIn('Access-Control-Allow-Origin', response['headers'])

        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertEqual(body['message'], 'Operation successful')

    def test_success_response_custom_status(self):
        """Test success response with custom status code."""
        data = {'data': 'test'}

        response = success_response(data, status_code=201)

        self.assertEqual(response['statusCode'], 201)

    def test_error_response(self):
        """Test creation of error response."""
        response = error_response(400, "Bad request")

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Content-Type', response['headers'])

        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertEqual(body['error'], 'Bad request')

    def test_error_response_server_error(self):
        """Test error response for server errors."""
        response = error_response(500, "Internal server error")

        self.assertEqual(response['statusCode'], 500)

        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertEqual(body['error'], 'Internal server error')

    def test_html_response(self):
        """Test creation of HTML response."""
        html_content = '<html><body><h1>Test</h1></body></html>'

        response = html_response(200, html_content)

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['headers']['Content-Type'], 'text/html')
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        self.assertEqual(response['body'], html_content)

    def test_html_response_error_page(self):
        """Test HTML response for error page."""
        html_content = '<html><body><h1>Error</h1></body></html>'

        response = html_response(404, html_content)

        self.assertEqual(response['statusCode'], 404)
        self.assertEqual(response['body'], html_content)


if __name__ == '__main__':
    unittest.main()
