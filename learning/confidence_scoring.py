"""
Confidence Scoring System for MOKA AI - Hermes Adaptive Learning System
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ConfidenceMetrics:
    """Data class for confidence metrics"""
    accuracy: float
    consistency: float
    frequency: float
    recency: float
    context_match: float

class ConfidenceScoringSystem:
    """Confidence scoring system for MOKA AI adaptive learning"""

    def __init__(self):
        self.metrics: Dict[str, ConfidenceMetrics] = {}
        self.learning_threshold = 0.8

    def calculate_confidence_score(self, behavior_pattern: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on multiple factors
        """
        # Calculate weighted confidence score
        accuracy_score = self._calculate_accuracy(behavior_pattern)
        consistency_score = self._calculate_consistency(behavior_pattern)
        frequency_score = self._calculate_frequency(behavior_pattern)
        recency_score = self._calculate_recency(behavior_pattern)
        context_match_score = self._calculate_context_match(behavior_pattern)

        # Weighted average of all factors
        weights = {
            'accuracy': 0.25,
            'consistency': 0.2,
            'frequency': 0.2,
            'recency': 0.2,
            'context_match': 0.15
        }

        confidence = (
            weights['accuracy'] * accuracy_score +
            weights['consistency'] * consistency_score +
            weights['frequency'] * frequency_score +
            weights['recency'] * recency_score +
            weights['context_match'] * context_match_score
        )

        return min(confidence, 1.0)  # Cap at 1.0

    def _calculate_accuracy(self, behavior_pattern: Dict[str, Any]) -> float:
        """Calculate accuracy based on historical outcomes"""
        outcomes = behavior_pattern.get('outcomes', [])
        if not outcomes:
            return 0.5  # No history = neutral
        successful = sum(1 for o in outcomes if o.get('success', False))
        return successful / len(outcomes)

    def _calculate_consistency(self, behavior_pattern: Dict[str, Any]) -> float:
        """Calculate consistency based on time distribution of observations"""
        timestamps = behavior_pattern.get('observation_times', [])
        if len(timestamps) < 2:
            return 0.5  # Need multiple observations for consistency
        # Calculate standard deviation of intervals between observations
        # Shorter intervals = more consistent
        intervals = []
        for i in range(1, len(timestamps)):
            try:
                t1 = datetime.fromisoformat(timestamps[i-1]) if isinstance(timestamps[i-1], str) else timestamps[i-1]
                t2 = datetime.fromisoformat(timestamps[i]) if isinstance(timestamps[i], str) else timestamps[i]
                intervals.append(abs((t2 - t1).total_seconds()))
            except (ValueError, TypeError):
                continue
        if not intervals:
            return 0.5
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval == 0:
            return 1.0
        # Coefficient of variation - lower = more consistent
        variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
        std_dev = variance ** 0.5
        cv = std_dev / avg_interval
        # Convert CV to 0-1 score (low variance = high score)
        return max(0.0, min(1.0, 1.0 - cv))

    def _calculate_frequency(self, behavior_pattern: Dict[str, Any]) -> float:
        """Calculate frequency based on how often pattern occurs vs expected"""
        observed_count = behavior_pattern.get('frequency', 0)
        expected_count = behavior_pattern.get('expected_frequency', 1)
        if expected_count <= 0:
            expected_count = 1
        ratio = observed_count / expected_count
        # Cap at 1.0 (more than expected is still good)
        return min(ratio, 1.0)

    def _calculate_recency(self, behavior_pattern: Dict[str, Any]) -> float:
        """Calculate recency score based on how recently the behavior was observed"""
        last_observed = behavior_pattern.get('last_observed')
        if not last_observed:
            return 0.0

        # Convert to datetime if it's a string
        if isinstance(last_observed, str):
            try:
                last_observed = datetime.fromisoformat(last_observed)
            except ValueError:
                return 0.0

        # Calculate time difference in hours
        time_diff = datetime.now() - last_observed
        hours_diff = time_diff.total_seconds() / 3600

        # Apply exponential decay: score = e^(-hours/half_life)
        # Using 168 hours (1 week) as half-life for meaningful decay
        half_life_hours = 168.0
        recency_score = pow(0.5, hours_diff / half_life_hours)

        return max(0.0, min(1.0, recency_score))

    def _calculate_context_match(self, behavior_pattern: Dict[str, Any]) -> float:
        """Calculate context match score based on similarity to current context"""
        # For now, return a neutral score since we don't have current context
        # In a full implementation, this would compare behavior_pattern['context_data']
        # with the current operational context
        context_data = behavior_pattern.get('context_data', {})
        if not context_data:
            # No context data = neutral score
            return 0.5

        # Simple implementation: if we have context data, assume moderate match
        # A full implementation would compare with current context
        return 0.6  # Slightly positive for having context data

    def update_confidence_based_on_feedback(self, pattern_id: str, feedback: str, metrics: Dict[str, float]):
        """Update confidence metrics based on user feedback"""
        if pattern_id not in self.metrics:
            self.metrics[pattern_id] = ConfidenceMetrics(0.5, 0.5, 0.5, 0.5, 0.5)
        m = self.metrics[pattern_id]
        delta = 0.1
        if feedback == "positive":
            m.accuracy = min(1.0, m.accuracy + delta)
            m.consistency = min(1.0, m.consistency + delta * 0.5)
        elif feedback == "negative":
            m.accuracy = max(0.0, m.accuracy - delta)
            m.consistency = max(0.0, m.consistency - delta * 0.5)
        if metrics:
            self.metrics[pattern_id] = ConfidenceMetrics(
                metrics.get('accuracy', m.accuracy),
                metrics.get('consistency', m.consistency),
                metrics.get('frequency', m.frequency),
                metrics.get('recency', m.recency),
                metrics.get('context_match', m.context_match)
            )

    def should_learn_behavior(self, confidence_score: float) -> bool:
        """
        Determine if a behavior should be learned based on confidence score
        """
        return confidence_score >= self.learning_threshold