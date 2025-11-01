"""
Tests for lambda/output_validator.py - Output validation and anomaly detection
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from botocore.exceptions import ClientError

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))


@pytest.fixture
def sample_reflection_text():
    """Sample reflection text for testing"""
    return """You have power over your mind - not outside events. Realize this, and you will find strength.

This profound insight from Marcus Aurelius reminds us of the fundamental distinction between what we can control and what we cannot. In our daily lives, we often expend enormous energy worrying about external circumstances, other people's opinions, or events beyond our influence.

The Stoic path to inner peace begins with this recognition: while we may not control what happens to us, we have absolute authority over how we respond. Our judgments, reactions, and interpretations remain within our power, no matter how chaotic the external world becomes."""


@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing"""
    return MagicMock()


# ResponseAnalyzer Tests

def test_response_analyzer_basic_analysis(sample_reflection_text):
    """Test basic text analysis"""
    from output_validator import ResponseAnalyzer

    analyzer = ResponseAnalyzer()
    stats = analyzer.analyze(sample_reflection_text)

    assert stats.word_count > 0
    assert stats.char_count == len(sample_reflection_text)
    assert stats.paragraph_count == 3
    assert stats.sentence_count > 0
    assert stats.avg_word_length > 0
    assert 0 < stats.unique_word_ratio <= 1.0


def test_response_analyzer_empty_text():
    """Test analysis of empty text"""
    from output_validator import ResponseAnalyzer

    analyzer = ResponseAnalyzer()
    stats = analyzer.analyze("")

    assert stats.word_count == 0
    assert stats.char_count == 0
    assert stats.avg_word_length == 0.0
    assert stats.unique_word_ratio == 0.0


def test_response_analyzer_single_sentence():
    """Test analysis of single sentence"""
    from output_validator import ResponseAnalyzer

    analyzer = ResponseAnalyzer()
    stats = analyzer.analyze("This is a simple test sentence.")

    assert stats.sentence_count == 1
    assert stats.paragraph_count == 1
    assert stats.word_count == 6


def test_response_statistics_to_dict():
    """Test ResponseStatistics to_dict conversion"""
    from output_validator import ResponseStatistics

    stats = ResponseStatistics(
        char_count=100,
        word_count=20,
        sentence_count=3,
        paragraph_count=2,
        avg_word_length=5.0,
        avg_sentence_length=6.67,
        unique_word_ratio=0.85,
        timestamp="2025-01-15T10:00:00Z"
    )

    stats_dict = stats.to_dict()
    assert stats_dict['word_count'] == 20
    assert stats_dict['paragraph_count'] == 2


# AnomalyDetector Tests

@patch('output_validator.boto3.client')
def test_anomaly_detector_no_historical_data(mock_boto3_client, sample_reflection_text):
    """Test anomaly detection with no historical data"""
    from output_validator import AnomalyDetector, ResponseStatistics

    # Mock S3 client to return NoSuchKey error
    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    from botocore.exceptions import ClientError
    mock_s3.get_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey'}},
        'GetObject'
    )

    detector = AnomalyDetector('test-bucket')

    current_stats = ResponseStatistics(
        char_count=500,
        word_count=100,
        sentence_count=5,
        paragraph_count=3,
        avg_word_length=5.0,
        avg_sentence_length=20.0,
        unique_word_ratio=0.8,
        timestamp=datetime.utcnow().isoformat()
    )

    result = detector.detect_anomalies(current_stats, min_samples=10)

    assert result.is_anomaly is False
    assert result.anomaly_score == 0.0
    assert result.details['reason'] == 'insufficient_historical_data'


@patch('output_validator.boto3.client')
def test_anomaly_detector_with_historical_data(mock_boto3_client):
    """Test anomaly detection with sufficient historical data"""
    from output_validator import AnomalyDetector, ResponseStatistics

    # Mock S3 client with historical data
    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    # Create historical stats (15 normal samples)
    historical_data = {
        'statistics': [
            {
                'char_count': 500 + i*10,
                'word_count': 100 + i,
                'sentence_count': 5,
                'paragraph_count': 3,
                'avg_word_length': 5.0,
                'avg_sentence_length': 20.0,
                'unique_word_ratio': 0.8,
                'timestamp': '2025-01-15T10:00:00Z'
            }
            for i in range(15)
        ]
    }

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(historical_data).encode())
    }

    detector = AnomalyDetector('test-bucket', threshold_sigma=2.0)

    # Create a normal current stat (within range)
    normal_stats = ResponseStatistics(
        char_count=550,
        word_count=105,
        sentence_count=5,
        paragraph_count=3,
        avg_word_length=5.0,
        avg_sentence_length=20.0,
        unique_word_ratio=0.8,
        timestamp=datetime.utcnow().isoformat()
    )

    result = detector.detect_anomalies(normal_stats, min_samples=10)
    assert result.is_anomaly is False


@patch('output_validator.boto3.client')
def test_anomaly_detector_detects_outlier(mock_boto3_client):
    """Test anomaly detection with outlier data"""
    from output_validator import AnomalyDetector, ResponseStatistics

    # Mock S3 client with historical data
    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    # Create historical stats (normal range: 100-110 words)
    historical_data = {
        'statistics': [
            {
                'char_count': 500,
                'word_count': 105,
                'sentence_count': 5,
                'paragraph_count': 3,
                'avg_word_length': 5.0,
                'avg_sentence_length': 21.0,
                'unique_word_ratio': 0.8,
                'timestamp': '2025-01-15T10:00:00Z'
            }
            for _ in range(15)
        ]
    }

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(historical_data).encode())
    }

    detector = AnomalyDetector('test-bucket', threshold_sigma=2.0)

    # Create an outlier stat (1000 words instead of ~105)
    outlier_stats = ResponseStatistics(
        char_count=5000,
        word_count=1000,
        sentence_count=5,
        paragraph_count=3,
        avg_word_length=5.0,
        avg_sentence_length=200.0,
        unique_word_ratio=0.8,
        timestamp=datetime.utcnow().isoformat()
    )

    result = detector.detect_anomalies(outlier_stats, min_samples=10)

    assert result.is_anomaly is True
    assert result.anomaly_score > 2.0
    assert len(result.anomalies_detected) > 0


@patch('output_validator.boto3.client')
def test_anomaly_detector_saves_statistics(mock_boto3_client):
    """Test that anomaly detector saves statistics to S3"""
    from output_validator import AnomalyDetector, ResponseStatistics

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3
    mock_s3.get_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey'}},
        'GetObject'
    )

    detector = AnomalyDetector('test-bucket')

    current_stats = ResponseStatistics(
        char_count=500,
        word_count=100,
        sentence_count=5,
        paragraph_count=3,
        avg_word_length=5.0,
        avg_sentence_length=20.0,
        unique_word_ratio=0.8,
        timestamp=datetime.utcnow().isoformat()
    )

    detector.detect_anomalies(current_stats, min_samples=10)

    # Verify put_object was called to save stats
    mock_s3.put_object.assert_called_once()
    call_args = mock_s3.put_object.call_args
    assert call_args[1]['Bucket'] == 'test-bucket'
    assert 'security/response_statistics.json' in call_args[1]['Key']


# ContentPolicyValidator Tests

def test_content_policy_validator_valid_content():
    """Test content policy validation with valid content"""
    from output_validator import ContentPolicyValidator

    config = {
        'content_policy': {
            'enabled': True,
            'required_elements': {
                'check_paragraph_structure': True,
                'min_paragraphs': 1,
                'max_paragraphs': 10
            },
            'forbidden_topics': []
        }
    }

    validator = ContentPolicyValidator(config)

    text = "This is a valid reflection.\n\nIt has multiple paragraphs.\n\nAll within policy."
    is_valid, violations = validator.validate(text)

    assert is_valid is True
    assert len(violations) == 0


def test_content_policy_validator_too_few_paragraphs():
    """Test content policy validation with too few paragraphs"""
    from output_validator import ContentPolicyValidator

    config = {
        'content_policy': {
            'enabled': True,
            'required_elements': {
                'check_paragraph_structure': True,
                'min_paragraphs': 3,
                'max_paragraphs': 10
            }
        }
    }

    validator = ContentPolicyValidator(config)

    text = "This is too short."
    is_valid, violations = validator.validate(text)

    assert is_valid is False
    assert any('Too few paragraphs' in v for v in violations)


def test_content_policy_validator_forbidden_topics():
    """Test content policy validation with forbidden topics"""
    from output_validator import ContentPolicyValidator

    config = {
        'content_policy': {
            'enabled': True,
            'forbidden_topics': ['politics', 'religion'],
            'required_elements': {
                'check_paragraph_structure': False
            }
        }
    }

    validator = ContentPolicyValidator(config)

    text = "This reflection discusses politics and controversial topics."
    is_valid, violations = validator.validate(text)

    assert is_valid is False
    assert any('forbidden topic' in v.lower() for v in violations)


def test_content_policy_validator_markdown_headings():
    """Test content policy validation rejects markdown headings"""
    from output_validator import ContentPolicyValidator

    config = {
        'content_policy': {
            'enabled': True,
            'required_elements': {
                'check_formatting': True,
                'check_paragraph_structure': False
            }
        }
    }

    validator = ContentPolicyValidator(config)

    text = "## This is a heading\n\nThis is content."
    is_valid, violations = validator.validate(text)

    assert is_valid is False
    assert any('markdown heading' in v.lower() for v in violations)


def test_content_policy_validator_code_blocks():
    """Test content policy validation rejects code blocks"""
    from output_validator import ContentPolicyValidator

    config = {
        'content_policy': {
            'enabled': True,
            'required_elements': {
                'check_formatting': True,
                'check_paragraph_structure': False
            }
        }
    }

    validator = ContentPolicyValidator(config)

    text = "This reflection contains ```code``` which is unexpected."
    is_valid, violations = validator.validate(text)

    assert is_valid is False
    assert any('code block' in v.lower() for v in violations)


# OutputValidator Integration Tests

@patch('output_validator.boto3.client')
def test_output_validator_valid_content(mock_boto3_client, sample_reflection_text):
    """Test full output validation with valid content"""
    from output_validator import OutputValidator

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3
    mock_s3.get_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey'}},
        'GetObject'
    )

    config = {
        'anomaly_detection': {
            'enabled': True,
            'deviation_threshold_sigma': 3.0,
            'min_samples_for_detection': 10
        },
        'content_policy': {
            'enabled': True,
            'required_elements': {
                'check_paragraph_structure': True,
                'min_paragraphs': 1,
                'max_paragraphs': 10,
                'check_formatting': True
            },
            'forbidden_topics': []
        }
    }

    validator = OutputValidator('test-bucket', config)
    is_valid, results = validator.validate(sample_reflection_text)

    assert is_valid is True
    assert results['statistics'] is not None
    assert results['content_policy']['valid'] is True
    assert len(results['issues']) == 0


@patch('output_validator.boto3.client')
def test_output_validator_invalid_content(mock_boto3_client):
    """Test full output validation with invalid content"""
    from output_validator import OutputValidator

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    config = {
        'anomaly_detection': {
            'enabled': False
        },
        'content_policy': {
            'enabled': True,
            'required_elements': {
                'check_formatting': True,
                'check_paragraph_structure': False
            },
            'forbidden_topics': []
        }
    }

    validator = OutputValidator('test-bucket', config)

    # Content with markdown heading (invalid)
    invalid_text = "## Heading\n\nThis is invalid."
    is_valid, results = validator.validate(invalid_text, check_anomalies=False)

    assert is_valid is False
    assert results['content_policy']['valid'] is False
    assert len(results['issues']) > 0


@patch('output_validator.boto3.client')
def test_output_validator_disabled_anomaly_detection(mock_boto3_client, sample_reflection_text):
    """Test output validator with anomaly detection disabled"""
    from output_validator import OutputValidator

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    config = {
        'anomaly_detection': {
            'enabled': False
        },
        'content_policy': {
            'enabled': True,
            'required_elements': {
                'check_paragraph_structure': False
            }
        }
    }

    validator = OutputValidator('test-bucket', config)
    assert validator.anomaly_detector is None

    is_valid, results = validator.validate(sample_reflection_text)
    assert is_valid is True
    assert results['anomaly_detection'] is None


def test_anomaly_result_dataclass():
    """Test AnomalyResult dataclass"""
    from output_validator import AnomalyResult

    result = AnomalyResult(
        is_anomaly=True,
        anomaly_score=4.5,
        anomalies_detected=['word_count: too high'],
        details={'word_count': {'z_score': 4.5}}
    )

    assert result.is_anomaly is True
    assert result.anomaly_score == 4.5
    assert len(result.anomalies_detected) == 1
