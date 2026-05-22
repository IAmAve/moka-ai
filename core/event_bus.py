"""
Event Bus implementation for MOKA AI
"""

class EventBus:
    def __init__(self):
        self._listeners = {}

    def subscribe(self, event_type, callback):
        """Subscribe to an event"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def publish(self, event_type, data):
        """Publish an event to all subscribers"""
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                callback(data)

    def notify(self, event_type, data):
        """Notify all subscribers of a specific event type"""
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                callback(data)