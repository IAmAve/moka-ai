"""
Communication Styles Module for MOKA AI Personality System
"""

class CommunicationStyles:
    """Communication styles manager for MOKA AI"""

    def __init__(self):
        self.styles = {
            "formal": self.formal_style,
            "informal": self.informal_style,
            "teaching": self.teaching_style,
            "encouraging": self.encouraging_style,
            "instructive": self.instructive_style
        }

    def formal_style(self, content):
        """Formal communication style"""
        # Implementation for formal style
        return f"Formal response: {content}"

    def informal_style(self, content):
        """Informal communication style"""
        # Implementation for informal style
        return f"Kamusta! {content}"

    def teaching_style(self, content):
        """Teaching communication style"""
        # Implementation for teaching style
        return f"Learning mode: {content}"

    def encouraging_style(self, content):
        """Encouraging communication style"""
        # Implementation for encouraging style
        return f"Keep it up! {content}"

    def instructive_style(self, content):
        """Instructive communication style"""
        # Implementation for instructive style
        return f"Follow these instructions: {content}"

    def get_style_response(self, style_type, content):
        """Get response based on communication style"""
        if style_type in self.styles:
            return self.styles[style_type](content)
        return content