from dataclasses import dataclass
from typing import List, Callable
from datetime import datetime

@dataclass
class EmergencyStopEvent:
    triggered_at: datetime
    action_id: str = "unknown"

class EmergencyStop:
    _instance = None
    _stopped = False  # class-level shared state
    _callbacks = []  # class-level shared callbacks

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def trigger(self, action_id: str = "unknown"):
        EmergencyStop._stopped = True
        event = EmergencyStopEvent(triggered_at=datetime.now(), action_id=action_id)
        for callback in EmergencyStop._callbacks:
            try:
                callback(event)
            except Exception:
                pass

    @staticmethod
    def is_stopped() -> bool:
        return EmergencyStop._stopped

    @classmethod
    def reset(cls):
        cls._stopped = False
        cls._callbacks = []

    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def clear_callbacks(self):
        self._callbacks = []