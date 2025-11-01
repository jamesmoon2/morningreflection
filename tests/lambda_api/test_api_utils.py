"""
Tests for lambda_api/api_utils.py - API response utilities
"""

import pytest
import json


def test_success_response_default():
    """Test success response with default status code"""
    from lambda_api.api_utils import success_response

    response = success_response({'message': 'success'})

    assert response['statusCode'] == 200
    assert 'headers' in response
    assert response['headers']['Content-Type'] == 'application/json'
    assert response['headers']['Access-Control-Allow-Origin'] == '*'

    body = json.loads(response['body'])
    assert body['message'] == 'success'


def test_success_response_custom_status():
    """Test success response with custom status code"""
    from lambda_api.api_utils import success_response

    response = success_response({'data': 'test'}, status_code=201)

    assert response['statusCode'] == 201


def test_error_response_default():
    """Test error response with default status code"""
    from lambda_api.api_utils import error_response

    response = error_response('Something went wrong')

    assert response['statusCode'] == 400
    assert 'headers' in response

    body = json.loads(response['body'])
    assert body['error'] == 'Something went wrong'


def test_error_response_custom_status():
    """Test error response with custom status code"""
    from lambda_api.api_utils import error_response

    response = error_response('Not found', status_code=404)

    assert response['statusCode'] == 404

    body = json.loads(response['body'])
    assert body['error'] == 'Not found'


def test_get_user_id_from_event_success(api_gateway_event):
    """Test extracting user ID from API Gateway event"""
    from lambda_api.api_utils import get_user_id_from_event

    event = api_gateway_event(user_id='test-user-123')

    user_id = get_user_id_from_event(event)

    assert user_id == 'test-user-123'


def test_get_user_id_from_event_missing():
    """Test handling missing user ID"""
    from lambda_api.api_utils import get_user_id_from_event

    event = {
        'requestContext': {}
    }

    user_id = get_user_id_from_event(event)

    assert user_id is None


def test_get_user_id_from_event_no_context():
    """Test handling missing request context"""
    from lambda_api.api_utils import get_user_id_from_event

    event = {}

    user_id = get_user_id_from_event(event)

    assert user_id is None


def test_parse_body_json():
    """Test parsing JSON body"""
    from lambda_api.api_utils import parse_body

    event = {
        'body': json.dumps({'key': 'value'})
    }

    body = parse_body(event)

    assert body == {'key': 'value'}


def test_parse_body_empty():
    """Test parsing empty body"""
    from lambda_api.api_utils import parse_body

    event = {'body': None}

    body = parse_body(event)

    assert body == {}


def test_parse_body_invalid_json():
    """Test parsing invalid JSON"""
    from lambda_api.api_utils import parse_body

    event = {'body': 'not valid json{'}

    body = parse_body(event)

    assert body == {}


def test_get_path_parameter():
    """Test extracting path parameter"""
    from lambda_api.api_utils import get_path_parameter

    event = {
        'pathParameters': {
            'date': '2025-01-15'
        }
    }

    date = get_path_parameter(event, 'date')

    assert date == '2025-01-15'


def test_get_path_parameter_missing():
    """Test handling missing path parameter"""
    from lambda_api.api_utils import get_path_parameter

    event = {'pathParameters': None}

    value = get_path_parameter(event, 'date')

    assert value is None


def test_get_query_parameter():
    """Test extracting query string parameter"""
    from lambda_api.api_utils import get_query_parameter

    event = {
        'queryStringParameters': {
            'year': '2025',
            'month': '1'
        }
    }

    year = get_query_parameter(event, 'year')
    month = get_query_parameter(event, 'month')

    assert year == '2025'
    assert month == '1'


def test_get_query_parameter_missing():
    """Test handling missing query parameter"""
    from lambda_api.api_utils import get_query_parameter

    event = {'queryStringParameters': None}

    value = get_query_parameter(event, 'year')

    assert value is None


def test_get_query_parameter_with_default():
    """Test query parameter with default value"""
    from lambda_api.api_utils import get_query_parameter

    event = {'queryStringParameters': None}

    value = get_query_parameter(event, 'limit', default='10')

    assert value == '10'
