"""
Learning Dashboard for MOKA AI - Hermes Adaptive Learning System
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

class LearningDashboard:
    """Dashboard for monitoring and managing MOKA AI learning system"""

    def __init__(self):
        self.dashboard_data = {
            'behaviors_learned': 0,
            'skills_acquired': 0,
            'profiles_tracked': 0,
            'confidence_scores': {}
        }

    def update_dashboard(self, behavior_count: int = None, skill_count: int = None, profile_count: int = None):
        """Update dashboard with new metrics"""
        if behavior_count is not None:
            self.dashboard_data['behaviors_learned'] = behavior_count
        if skill_count is not None:
            self.dashboard_data['skills_acquired'] = skill_count
        if profile_count is not None:
            self.dashboard_data['profiles_tracked'] = profile_count

    def get_learning_metrics(self) -> Dict[str, Any]:
        """Get current learning metrics"""
        return {
            'behaviors_learned': self.dashboard_data['behaviors_learned'],
            'skills_acquired': self.dashboard_data['skills_acquired'],
            'profiles_tracked': self.dashboard_data['profiles_tracked']
        }

    def display_dashboard(self):
        """Display the learning dashboard"""
        metrics = self.get_learning_metrics()
        print("=== MOKA AI Learning Dashboard ===")
        print(f"Behaviors Learned: {metrics['behaviors_learned']}")
        print(f"Skills Acquired: {metrics['skills_acquired']}")
        print(f"Profiles Tracked: {metrics['profiles_tracked']}")
        print("==================================")

    def generate_report(self) -> str:
        """Generate a report of learning activities"""
        report = "MOKA AI Learning Report\n"
        report += "======================\n"
        report += f"Behaviors Learned: {self.dashboard_data['behaviors_learned']}\n"
        report += f"Skills Acquired: {self.dashboard_data['skills_acquired']}\n"
        report += f"Profiles Tracked: {self.dashboard_data['profiles_tracked']}\n"
        return report