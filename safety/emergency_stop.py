from dataclasses import dataclass
from typing import Callable, List
from datetime import datetime
import time
import threading


@dataclass
class EmergencyStopEvent:
    triggered_at: datetime
    action_id: str = "unknown"


class EmergencyStop:
    _instance = None
    _stopped = False
    _callbacks: List[Callable] = []
    _fallback_thread: threading.Thread = None

    def __new__(cls, logger: Callable = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._logger = logger
            cls._instance._log = logger.info if logger else lambda m: None
            cls._instance._stopped = False
            cls._instance._callbacks = []
            cls._instance._fallback_thread = None
        return cls._instance

    def trigger(self, action_id: str = "unknown"):
        EmergencyStop._stopped = True
        event = EmergencyStopEvent(triggered_at=datetime.now(), action_id=action_id)
        self._log(f"Emergency stop triggered by '{action_id}'")
        for callback in list(EmergencyStop._callbacks):
            try:
                callback(event)
            except Exception as e:
                if self._logger:
                    self._logger.error(f"Emergency stop callback error: {e}")

    @staticmethod
    def is_stopped() -> bool:
        return EmergencyStop._stopped

    @classmethod
    def reset(cls):
        cls._stopped = False
        cls._callbacks = []
        if cls._fallback_thread and cls._fallback_thread.is_alive():
            cls._stopped = True  # signal the thread to stop
            cls._fallback_thread = None

    def register_callback(self, callback: Callable):
        EmergencyStop._callbacks.append(callback)

    def clear_callbacks(self):
        EmergencyStop._callbacks = []

    def start_listening(self):
        """Start listening for CTRL+ALT+M hotkey. Blocks until stop_hotkeys() called."""
        try:
            import keyboard
            keyboard.add_hotkey("ctrl+alt+m", self._hotkey_handler)
            self._log("Emergency stop hotkey registered: CTRL+ALT+M")
            keyboard.wait()
        except ImportError:
            self._log("keyboard module not available — using fallback listener")
            self._start_fallback_listener()

    def _hotkey_handler(self):
        self.trigger("ctrl+alt+m")

    def stop_hotkeys(self):
        """Stop listening for hotkeys."""
        try:
            import keyboard
            keyboard.unhook_all()
            self._log("Emergency stop hotkeys unregistered")
        except ImportError:
            if self._logger:
                self._logger.warning("keyboard module not available, nothing to unhook")
        EmergencyStop._stopped = True
        if EmergencyStop._fallback_thread and EmergencyStop._fallback_thread.is_alive():
            EmergencyStop._fallback_thread = None

    def _start_fallback_listener(self):
        """Fallback listener using a background thread with periodic checks."""
        def poll():
            while not EmergencyStop._stopped:
                time.sleep(0.1)
        EmergencyStop._fallback_thread = threading.Thread(target=poll, daemon=True)
        EmergencyStop._fallback_thread.start()