"""Health Monitor for MOKA AI"""
import threading, time
from typing import Callable, Dict, Any, Optional
from datetime import datetime
from core.event_bus import EventBus

class HealthMonitor:
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus()
        self._components: Dict[str, Callable[[], bool]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._interval = 30

    def register_component(self, name: str, fn: Callable[[], bool]) -> None:
        self._components[name] = fn

    def check_health(self) -> Dict[str, Any]:
        results = {}
        for name, fn in self._components.items():
            try: results[name] = {"healthy": fn(), "error": None}
            except Exception as e: results[name] = {"healthy": False, "error": str(e)}
        hc = sum(1 for r in results.values() if r["healthy"])
        t = len(results)
        status = "ok" if t == 0 or hc == t else ("critical" if hc == 0 else "degraded")
        return {"status": status, "components": results, "timestamp": datetime.now().isoformat(), "total": t, "healthy_count": hc}

    def start(self) -> None:
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.event_bus.publish("health_monitor:started", {})

    def stop(self) -> None:
        self._running = False
        if self._thread: self._thread.join(timeout=5)
        self.event_bus.publish("health_monitor:stopped", {})

    def _monitor_loop(self) -> None:
        while self._running:
            r = self.check_health()
            self.event_bus.publish("health_monitor:report", r)
            if r["status"] == "critical": self.event_bus.publish("health_monitor:critical", r)
            time.sleep(self._interval)