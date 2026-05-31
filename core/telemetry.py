"""
Telemetry Abstraction for MOKA AI
"""

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    TRACE = "trace"

@dataclass
class Metric:
    name: str
    value: float
    type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class Telemetry:
    def __init__(self, emitter: Optional[Callable[[List[Metric]], None]] = None):
        self.emitter = emitter or self._default_emit
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._traces: List[Dict[str, Any]] = []
        self._pending: List[Metric] = []

    def _default_emit(self, metrics: List[Metric]) -> None:
        for m in metrics:
            print(f"[TELEMETRY] {m.type.value} {m.name}={m.value} labels={m.labels}")

    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + value
            metric = Metric(name, self._counters[name], MetricType.COUNTER, labels or {})
            self._pending.append(metric)
            # Flush immediately to make metric available to test emitter
            self.emitter(list(self._pending))
            self._pending.clear()

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            self._gauges[name] = value
            metric = Metric(name, value, MetricType.GAUGE, labels or {})
            self._pending.append(metric)
            # Flush immediately to make metric available to test emitter
            self.emitter(list(self._pending))
            self._pending.clear()

    def start_span(self, name: str) -> "Span":
        return Span(self, name)

    def flush(self) -> None:
        with self._lock:
            if self._pending:
                self.emitter(list(self._pending))
                self._pending.clear()

class Span:
    def __init__(self, telemetry: Telemetry, name: str):
        self.telemetry = telemetry
        self.name = name
        self.start_time = time.perf_counter()
        self.labels: Dict[str, str] = {}

    def add_label(self, key: str, value: str) -> "Span":
        self.labels[key] = value
        return self

    def end(self) -> float:
        duration = time.perf_counter() - self.start_time
        self.telemetry._traces.append({
            "name": self.name,
            "duration_ms": duration * 1000,
            "labels": self.labels,
            "timestamp": datetime.now().isoformat()
        })
        return duration