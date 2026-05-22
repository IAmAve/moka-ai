"""
Tests for Hermes Adaptive Learning System
"""

import unittest
import os
import sys
import json
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learning.behavior_database import BehaviorDatabase, BehaviorPattern
from learning.skill_database import SkillDatabase, Skill
from learning.software_profile_database import SoftwareProfileDatabase, SoftwareProfile
from learning.confidence_scoring import ConfidenceScoringSystem
from learning.testing_framework import BehaviorTestingFramework
from learning.dashboard import LearningDashboard
from learning.hermes_learning_system import HermesAdaptiveLearningSystem


class TestBehaviorDatabase(unittest.TestCase):
    def setUp(self):
        self.db_path = tempfile.mktemp(suffix='.json')
        self.db = BehaviorDatabase(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_and_get_behavior_pattern(self):
        pattern = BehaviorPattern(
            pattern_id='test-1',
            behavior_type='coding',
            frequency=5,
            last_observed=datetime.now(),
            context_data={'file': 'test.py'},
            confidence_score=0.8
        )
        self.assertTrue(self.db.add_behavior_pattern(pattern))
        retrieved = self.db.get_behavior_pattern('test-1')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.pattern_id, 'test-1')
        self.assertEqual(retrieved.behavior_type, 'coding')

    def test_get_patterns_by_type(self):
        pattern = BehaviorPattern(
            pattern_id='test-2',
            behavior_type='refactoring',
            frequency=3,
            last_observed=datetime.now(),
            context_data={},
            confidence_score=0.7
        )
        self.db.add_behavior_pattern(pattern)
        patterns = self.db.get_patterns_by_type('refactoring')
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern_id, 'test-2')

    def test_remove_behavior_pattern(self):
        pattern = BehaviorPattern(
            pattern_id='test-3',
            behavior_type='testing',
            frequency=2,
            last_observed=datetime.now(),
            context_data={},
            confidence_score=0.9
        )
        self.db.add_behavior_pattern(pattern)
        self.assertTrue(self.db.remove_behavior_pattern('test-3'))
        self.assertIsNone(self.db.get_behavior_pattern('test-3'))


class TestSkillDatabase(unittest.TestCase):
    def setUp(self):
        self.db_path = tempfile.mktemp(suffix='.json')
        self.db = SkillDatabase(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_and_get_skill(self):
        skill = Skill(
            skill_id='skill-1',
            name='Test Skill',
            description='A test skill',
            code='print("hello")',
            is_approved=False,
            confidence_score=0.8
        )
        self.assertTrue(self.db.add_skill(skill))
        retrieved = self.db.get_skill('skill-1')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, 'Test Skill')

    def test_get_approved_skills(self):
        skill1 = Skill(
            skill_id='skill-2',
            name='Approved Skill',
            description='Approved',
            code='',
            is_approved=True,
            confidence_score=0.9
        )
        skill2 = Skill(
            skill_id='skill-3',
            name='Unapproved Skill',
            description='Not approved',
            code='',
            is_approved=False,
            confidence_score=0.5
        )
        self.db.add_skill(skill1)
        self.db.add_skill(skill2)
        approved = self.db.get_approved_skills()
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved['skill-2'].name, 'Approved Skill')


class TestConfidenceScoringSystem(unittest.TestCase):
    def setUp(self):
        self.system = ConfidenceScoringSystem()

    def test_calculate_confidence_with_outcomes(self):
        pattern = {
            'outcomes': [
                {'success': True},
                {'success': True},
                {'success': False}
            ]
        }
        score = self.system.calculate_confidence_score(pattern)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1)

    def test_calculate_confidence_with_frequency(self):
        pattern = {
            'frequency': 10,
            'expected_frequency': 5
        }
        score = self.system.calculate_confidence_score(pattern)
        self.assertGreaterEqual(score, 0)

    def test_should_learn_behavior(self):
        self.assertTrue(self.system.should_learn_behavior(0.9))
        self.assertTrue(self.system.should_learn_behavior(0.8))
        self.assertFalse(self.system.should_learn_behavior(0.7))


class TestBehaviorTestingFramework(unittest.TestCase):
    def setUp(self):
        self.framework = BehaviorTestingFramework()

    def test_validate_behavior_safety_approved(self):
        behavior = {'requires_approval': False, 'confidence_score': 0.9, 'code': 'print(1)'}
        self.assertTrue(self.framework.validate_behavior_safety(behavior))

    def test_validate_behavior_safety_requires_approval(self):
        behavior = {'requires_approval': True, 'confidence_score': 0.9}
        self.assertFalse(self.framework.validate_behavior_safety(behavior))

    def test_validate_behavior_safety_low_confidence(self):
        behavior = {'requires_approval': False, 'confidence_score': 0.5}
        self.assertFalse(self.framework.validate_behavior_safety(behavior))

    def test_validate_behavior_safety_dangerous(self):
        behavior = {'requires_approval': False, 'confidence_score': 0.9, 'action': 'delete_file'}
        self.assertFalse(self.framework.validate_behavior_safety(behavior))


class TestHermesAdaptiveLearningSystem(unittest.TestCase):
    def setUp(self):
        self.hermes = HermesAdaptiveLearningSystem()

    def test_observe_behavior(self):
        behavior_data = {
            'type': 'coding',
            'frequency': 5,
            'context': {'file': 'test.py'}
        }
        self.assertTrue(self.hermes.observe_behavior(behavior_data))

    def test_draft_behavior(self):
        pattern = {
            'type': 'refactoring',
            'frequency': 3,
            'context': {}
        }
        pattern_id = self.hermes.draft_behavior(pattern)
        self.assertIsNotNone(pattern_id)

    def test_test_behavior(self):
        behavior = {
            'pattern_id': 'test-pattern',
            'type': 'safe-action',
            'confidence_score': 0.9,
            'code': 'print("test")'
        }
        result = self.hermes.test_behavior(behavior)
        self.assertIsInstance(result, bool)

    def test_learn_and_adapt_rejects_low_confidence(self):
        behavior = {
            'pattern_id': 'low-confidence'
        }
        self.assertFalse(self.hermes.learn_and_adapt(behavior))

    def tearDown(self):
        for f in ['behavior_memory.json', 'skill_database.json', 'software_profiles.json']:
            if os.path.exists(f):
                os.remove(f)


if __name__ == '__main__':
    unittest.main()