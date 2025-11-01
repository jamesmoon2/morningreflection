"""
Output validator with semantic validation and anomaly detection.

Provides advanced validation including:
- Semantic content analysis
- Statistical anomaly detection
- Response integrity verification
- Content policy enforcement
"""

import json
import logging
import re
import statistics
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()


@dataclass
class ResponseStatistics:
    """Statistics for a response."""
    char_count: int
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_word_length: float
    avg_sentence_length: float
    unique_word_ratio: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""
    is_anomaly: bool
    anomaly_score: float
    anomalies_detected: List[str]
    details: Dict[str, Any]


class ResponseAnalyzer:
    """Analyzes API responses for semantic content."""

    def analyze(self, text: str) -> ResponseStatistics:
        """
        Analyze response text and extract statistics.

        Args:
            text: Response text to analyze

        Returns:
            ResponseStatistics object
        """
        # Count characters
        char_count = len(text)

        # Count words
        words = text.split()
        word_count = len(words)

        # Count sentences (rough approximation)
        sentence_count = len(re.findall(r'[.!?]+', text))
        sentence_count = max(sentence_count, 1)  # At least 1

        # Count paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        paragraph_count = max(paragraph_count, 1)  # At least 1

        # Average word length
        if words:
            avg_word_length = sum(len(w) for w in words) / word_count
        else:
            avg_word_length = 0.0

        # Average sentence length (in words)
        avg_sentence_length = word_count / sentence_count

        # Unique word ratio
        if words:
            unique_words = set(w.lower() for w in words)
            unique_word_ratio = len(unique_words) / word_count
        else:
            unique_word_ratio = 0.0

        return ResponseStatistics(
            char_count=char_count,
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            avg_word_length=avg_word_length,
            avg_sentence_length=avg_sentence_length,
            unique_word_ratio=unique_word_ratio,
            timestamp=datetime.utcnow().isoformat()
        )


class AnomalyDetector:
    """Detects statistical anomalies in API responses."""

    def __init__(self, bucket_name: str, threshold_sigma: float = 3.0):
        """
        Initialize anomaly detector.

        Args:
            bucket_name: S3 bucket for storing historical statistics
            threshold_sigma: Number of standard deviations for anomaly threshold
        """
        self.bucket_name = bucket_name
        self.threshold_sigma = threshold_sigma
        self.s3_client = boto3.client('s3')
        self.stats_key = 'security/response_statistics.json'

    def load_historical_stats(self) -> List[ResponseStatistics]:
        """
        Load historical response statistics from S3.

        Returns:
            List of ResponseStatistics objects
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.stats_key
            )
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)

            stats_list = []
            for item in data.get('statistics', []):
                stats_list.append(ResponseStatistics(**item))

            logger.info(f"Loaded {len(stats_list)} historical statistics")
            return stats_list

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                logger.info("No historical statistics found, starting fresh")
                return []
            else:
                logger.error(f"Error loading historical statistics: {e}")
                return []

    def save_historical_stats(self, stats_list: List[ResponseStatistics]) -> None:
        """
        Save historical statistics to S3.

        Args:
            stats_list: List of ResponseStatistics to save
        """
        try:
            # Keep only last 100 entries to limit file size
            stats_to_save = stats_list[-100:]

            data = {
                'statistics': [s.to_dict() for s in stats_to_save],
                'last_updated': datetime.utcnow().isoformat()
            }

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self.stats_key,
                Body=json.dumps(data, indent=2),
                ContentType='application/json'
            )

            logger.info(f"Saved {len(stats_to_save)} historical statistics")

        except ClientError as e:
            logger.error(f"Error saving historical statistics: {e}")

    def detect_anomalies(
        self,
        current_stats: ResponseStatistics,
        min_samples: int = 10
    ) -> AnomalyResult:
        """
        Detect if current response is anomalous compared to historical data.

        Args:
            current_stats: Statistics for current response
            min_samples: Minimum historical samples needed for detection

        Returns:
            AnomalyResult object
        """
        historical_stats = self.load_historical_stats()

        # Need sufficient historical data
        if len(historical_stats) < min_samples:
            logger.info(
                f"Insufficient historical data for anomaly detection "
                f"({len(historical_stats)}/{min_samples})"
            )
            # Save current stats and return no anomaly
            historical_stats.append(current_stats)
            self.save_historical_stats(historical_stats)

            return AnomalyResult(
                is_anomaly=False,
                anomaly_score=0.0,
                anomalies_detected=[],
                details={'reason': 'insufficient_historical_data'}
            )

        # Extract metrics for comparison
        metrics = {
            'char_count': [s.char_count for s in historical_stats],
            'word_count': [s.word_count for s in historical_stats],
            'paragraph_count': [s.paragraph_count for s in historical_stats],
            'avg_word_length': [s.avg_word_length for s in historical_stats],
            'avg_sentence_length': [s.avg_sentence_length for s in historical_stats],
            'unique_word_ratio': [s.unique_word_ratio for s in historical_stats]
        }

        anomalies = []
        deviations = {}

        # Check each metric
        for metric_name, values in metrics.items():
            current_value = getattr(current_stats, metric_name)

            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0

            if stdev > 0:
                z_score = abs((current_value - mean) / stdev)
                deviations[metric_name] = {
                    'current': current_value,
                    'mean': mean,
                    'stdev': stdev,
                    'z_score': z_score
                }

                if z_score > self.threshold_sigma:
                    anomalies.append(
                        f"{metric_name}: {current_value:.2f} "
                        f"(expected {mean:.2f}±{stdev:.2f}, z={z_score:.2f})"
                    )

        # Calculate overall anomaly score
        if deviations:
            z_scores = [d['z_score'] for d in deviations.values()]
            anomaly_score = max(z_scores)
        else:
            anomaly_score = 0.0

        is_anomaly = len(anomalies) > 0

        # Save current stats to historical data
        historical_stats.append(current_stats)
        self.save_historical_stats(historical_stats)

        return AnomalyResult(
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            anomalies_detected=anomalies,
            details=deviations
        )


class ContentPolicyValidator:
    """Validates content against content policies."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def validate(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate content against content policies.

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        if not self.config.get('content_policy', {}).get('enabled', True):
            return True, []

        violations = []

        # Check paragraph structure
        if self.config.get('content_policy.required_elements.check_paragraph_structure', True):
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            para_count = len(paragraphs)

            min_para = self.config.get('content_policy.required_elements.min_paragraphs', 1)
            max_para = self.config.get('content_policy.required_elements.max_paragraphs', 10)

            if para_count < min_para:
                violations.append(f"Too few paragraphs: {para_count} (min {min_para})")
            if para_count > max_para:
                violations.append(f"Too many paragraphs: {para_count} (max {max_para})")

        # Check for forbidden topics (basic keyword matching)
        forbidden_topics = self.config.get('content_policy.forbidden_topics', [])
        text_lower = text.lower()

        for topic in forbidden_topics:
            # Convert topic to keywords
            keywords = topic.lower().split()
            if all(keyword in text_lower for keyword in keywords):
                violations.append(f"Contains forbidden topic: {topic}")

        # Check formatting
        if self.config.get('content_policy.required_elements.check_formatting', True):
            # Should not contain markdown headings (##, ###, etc.)
            if re.search(r'^#{1,6}\s', text, re.MULTILINE):
                violations.append("Contains markdown headings (not expected in reflection)")

            # Should not contain code blocks
            if '```' in text or '`' in text:
                violations.append("Contains code blocks or inline code (unexpected)")

        is_valid = len(violations) == 0
        return is_valid, violations


class OutputValidator:
    """Main output validator orchestrating all validation checks."""

    def __init__(self, bucket_name: str, config: Dict[str, Any]):
        """
        Initialize output validator.

        Args:
            bucket_name: S3 bucket for storing data
            config: Security configuration dictionary
        """
        self.bucket_name = bucket_name
        self.config = config
        self.analyzer = ResponseAnalyzer()
        self.anomaly_detector = None
        self.policy_validator = ContentPolicyValidator(config)

        # Initialize anomaly detector if enabled
        if config.get('anomaly_detection', {}).get('enabled', True):
            threshold = config.get('anomaly_detection.deviation_threshold_sigma', 3.0)
            self.anomaly_detector = AnomalyDetector(bucket_name, threshold)

    def validate(
        self,
        text: str,
        check_anomalies: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform comprehensive output validation.

        Args:
            text: API response text to validate
            check_anomalies: Whether to perform anomaly detection

        Returns:
            Tuple of (is_valid, validation_results_dict)
        """
        logger.info("Starting output validation")

        validation_results = {
            'statistics': None,
            'anomaly_detection': None,
            'content_policy': None,
            'overall_valid': True,
            'issues': []
        }

        # 1. Analyze response statistics
        stats = self.analyzer.analyze(text)
        validation_results['statistics'] = stats.to_dict()
        logger.info(
            f"Response stats: {stats.word_count} words, "
            f"{stats.paragraph_count} paragraphs"
        )

        # 2. Anomaly detection
        if check_anomalies and self.anomaly_detector:
            min_samples = self.config.get(
                'anomaly_detection.min_samples_for_detection',
                10
            )
            anomaly_result = self.anomaly_detector.detect_anomalies(
                stats,
                min_samples
            )

            validation_results['anomaly_detection'] = {
                'is_anomaly': anomaly_result.is_anomaly,
                'anomaly_score': anomaly_result.anomaly_score,
                'anomalies': anomaly_result.anomalies_detected
            }

            if anomaly_result.is_anomaly:
                logger.warning(
                    f"ANOMALY DETECTED: {len(anomaly_result.anomalies_detected)} "
                    f"metric(s) deviate significantly"
                )
                for anomaly in anomaly_result.anomalies_detected:
                    logger.warning(f"  - {anomaly}")
                    validation_results['issues'].append(f"Anomaly: {anomaly}")

        # 3. Content policy validation
        policy_valid, violations = self.policy_validator.validate(text)
        validation_results['content_policy'] = {
            'valid': policy_valid,
            'violations': violations
        }

        if not policy_valid:
            logger.warning(f"Content policy violations: {violations}")
            validation_results['issues'].extend(violations)
            validation_results['overall_valid'] = False

        # Overall validity
        # Anomalies are warnings, not failures
        validation_results['overall_valid'] = policy_valid

        return validation_results['overall_valid'], validation_results
