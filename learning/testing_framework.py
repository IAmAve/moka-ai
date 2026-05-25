"""
Testing Framework for MOKA AI - Hermes Adaptive Learning System
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import json
import os

@dataclass
class TestResult:
    """Data class for test results"""
    test_id: str
    behavior_id: str
    test_name: str
    passed: bool
    execution_time: float
    error_message: Optional[str] = None

class BehaviorTestingFramework:
    """Testing framework for learned behaviors"""

    def __init__(self, logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.test_results: List[TestResult] = []
        self.behavior_tests: Dict[str, List[Callable]] = {}

    def add_behavior_test(self, behavior_id: str, test_function: Callable):
        """Add a test function for a specific behavior"""
        if behavior_id not in self.behavior_tests:
            self.behavior_tests[behavior_id] = []
        self.behavior_tests[behavior_id].append(test_function)

    def run_behavior_tests(self, behavior_id: str) -> List[TestResult]:
        """Run all tests for a specific behavior"""
        results = []
        if behavior_id in self.behavior_tests:
            for test_function in self.behavior_tests[behavior_id]:
                try:
                    start_time = datetime.now()
                    test_result = test_function()
                    end_time = datetime.now()
                    execution_time = (end_time - start_time).total_seconds()

                    result = TestResult(
                        test_id=f"test_{datetime.now().timestamp()}",
                        behavior_id=behavior_id,
                        test_name=test_function.__name__,
                        passed=test_result,
                        execution_time=execution_time
                    )
                    results.append(result)
                except Exception as e:
                    result = TestResult(
                        test_id=f"test_{datetime.now().timestamp()}",
                        behavior_id=behavior_id,
                        test_name=test_function.__name__,
                        passed=False,
                        execution_time=0,
                        error_message=str(e)
                    )
                    results.append(result)
        return results

    def validate_behavior_safety(self, behavior_data: Dict[str, Any]) -> bool:
        """Validate that a behavior is safe to execute"""
        # Check if behavior requires user approval
        if behavior_data.get('requires_approval', False):
            return False

        # Check confidence score threshold
        confidence_score = behavior_data.get('confidence_score', 0)
        if confidence_score < 0.8:
            return False

        # Check for potentially dangerous operations
        dangerous_patterns = ['delete', 'remove', 'destroy', 'format']
        behavior_text = str(behavior_data)
        for pattern in dangerous_patterns:
            if pattern in behavior_text.lower():
                return False

        return True

    def test_behavior_execution(self, behavior_id: str, behavior_data: Dict[str, Any]) -> bool:
        """Test the execution of a learned behavior"""
        if not self.validate_behavior_safety(behavior_data):
            return False
        is_safe = self.validate_behavior_safety(behavior_data)
        has_code = bool(behavior_data.get('code') or behavior_data.get('action'))
        has_confidence = behavior_data.get('confidence_score', 0) > 0.5
        return is_safe and (has_code or has_confidence)

    def run_comprehensive_behavior_test(self, behavior_id: str, test_cases: List[Dict]) -> Dict[str, Any]:
        """Run comprehensive tests on a behavior"""
        test_results = {
            'behavior_id': behavior_id,
            'tests_passed': 0,
            'tests_failed': 0,
            'total_tests': len(test_cases),
            'execution_time': 0.0,
            'results': []
        }

        for test_case in test_cases:
            try:
                # Run each test case
                result = self.test_behavior_execution(behavior_id, test_case)
                if result:
                    test_results['tests_passed'] += 1
                else:
                    test_results['tests_failed'] += 1
            except Exception as e:
                test_results['tests_failed'] += 1
                self._log(f"Test case failed: {e}")

        return test_results