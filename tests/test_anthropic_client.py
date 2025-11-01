"""
Tests for lambda/anthropic_client.py - Anthropic API integration
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))


@patch('anthropic_client.Anthropic')
def test_generate_reflection_success(mock_anthropic_class, sample_quote, sample_reflection):
    """Test successful reflection generation"""
    from anthropic_client import generate_reflection

    # Mock Anthropic client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=sample_reflection)]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic_class.return_value = mock_client

    result = generate_reflection(
        quote=sample_quote['quote'],
        attribution=sample_quote['attribution'],
        theme=sample_quote['theme'],
        api_key='test-api-key'
    )

    assert result == sample_reflection
    mock_client.messages.create.assert_called_once()

    # Verify API call parameters
    call_args = mock_client.messages.create.call_args
    assert call_args[1]['model'] == 'claude-sonnet-4-5-20250929'
    assert call_args[1]['max_tokens'] == 2000
    assert call_args[1]['temperature'] == 1.0


@patch('anthropic_client.Anthropic')
def test_generate_reflection_timeout(mock_anthropic_class, sample_quote):
    """Test reflection generation with timeout"""
    from anthropic_client import generate_reflection

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("Timeout")
    mock_anthropic_class.return_value = mock_client

    result = generate_reflection(
        quote=sample_quote['quote'],
        attribution=sample_quote['attribution'],
        theme=sample_quote['theme'],
        api_key='test-api-key',
        timeout=5
    )

    assert result is None


@patch('anthropic_client.Anthropic')
def test_generate_reflection_empty_response(mock_anthropic_class, sample_quote):
    """Test handling of empty response"""
    from anthropic_client import generate_reflection

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic_class.return_value = mock_client

    result = generate_reflection(
        quote=sample_quote['quote'],
        attribution=sample_quote['attribution'],
        theme=sample_quote['theme'],
        api_key='test-api-key'
    )

    assert result is None


@patch('anthropic_client.Anthropic')
def test_generate_reflection_too_short(mock_anthropic_class, sample_quote):
    """Test handling of too-short response"""
    from anthropic_client import generate_reflection

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Too short")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic_class.return_value = mock_client

    result = generate_reflection(
        quote=sample_quote['quote'],
        attribution=sample_quote['attribution'],
        theme=sample_quote['theme'],
        api_key='test-api-key'
    )

    assert result is None


@patch('anthropic_client.Anthropic')
def test_generate_journaling_prompt_success(
    mock_anthropic_class,
    sample_quote,
    sample_reflection,
    sample_journaling_prompt
):
    """Test successful journaling prompt generation"""
    from anthropic_client import generate_journaling_prompt

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=sample_journaling_prompt)]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic_class.return_value = mock_client

    result = generate_journaling_prompt(
        reflection=sample_reflection,
        quote=sample_quote['quote'],
        theme=sample_quote['theme'],
        api_key='test-api-key'
    )

    assert result == sample_journaling_prompt
    mock_client.messages.create.assert_called_once()

    # Verify API call parameters
    call_args = mock_client.messages.create.call_args
    assert call_args[1]['model'] == 'claude-sonnet-4-5-20250929'
    assert call_args[1]['max_tokens'] == 200
    assert call_args[1]['temperature'] == 0.8


@patch('anthropic_client.Anthropic')
def test_generate_journaling_prompt_timeout(
    mock_anthropic_class,
    sample_quote,
    sample_reflection
):
    """Test journaling prompt generation with timeout"""
    from anthropic_client import generate_journaling_prompt

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("Timeout")
    mock_anthropic_class.return_value = mock_client

    result = generate_journaling_prompt(
        reflection=sample_reflection,
        quote=sample_quote['quote'],
        theme=sample_quote['theme'],
        api_key='test-api-key',
        timeout=5
    )

    assert result is None


@patch('anthropic_client.Anthropic')
def test_generate_journaling_prompt_too_short(
    mock_anthropic_class,
    sample_quote,
    sample_reflection
):
    """Test handling of too-short prompt"""
    from anthropic_client import generate_journaling_prompt

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Short")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic_class.return_value = mock_client

    result = generate_journaling_prompt(
        reflection=sample_reflection,
        quote=sample_quote['quote'],
        theme=sample_quote['theme'],
        api_key='test-api-key'
    )

    assert result is None


def test_build_reflection_prompt(sample_quote):
    """Test reflection prompt construction"""
    from anthropic_client import build_reflection_prompt

    prompt = build_reflection_prompt(
        quote=sample_quote['quote'],
        attribution=sample_quote['attribution'],
        theme=sample_quote['theme']
    )

    assert isinstance(prompt, str)
    assert sample_quote['quote'] in prompt
    assert sample_quote['attribution'] in prompt
    assert sample_quote['theme'] in prompt
    assert len(prompt) > 100  # Should be substantial


def test_build_journaling_prompt_request(sample_quote, sample_reflection):
    """Test journaling prompt request construction"""
    from anthropic_client import build_journaling_prompt_request

    prompt = build_journaling_prompt_request(
        reflection=sample_reflection,
        quote=sample_quote['quote'],
        theme=sample_quote['theme']
    )

    assert isinstance(prompt, str)
    assert sample_reflection in prompt
    assert sample_quote['quote'] in prompt
    assert sample_quote['theme'] in prompt
