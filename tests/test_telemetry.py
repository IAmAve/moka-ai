import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.telemetry import Telemetry, MetricType

class TestTelemetry(unittest.TestCase):
    def test_increment_counter(self):
        emitted = []
        t = Telemetry(emitter=lambda m: emitted.extend(m))
        t.increment_counter("requests")
        t.increment_counter("requests", 5)
        self.assertEqual(emitted[1].value, 6.0)

    def test_set_gauge(self):
        emitted = []
        t = Telemetry(emitter=lambda m: emitted.extend(m))
        t.set_gauge("memory_mb", 512.0)
        self.assertEqual(emitted[0].value, 512.0)
        self.assertEqual(emitted[0].type, MetricType.GAUGE)

    def test_span_timing(self):
        t = Telemetry(emitter=lambda m: None)
        span = t.start_span("test_op")
        span.add_label("key", "val")
        duration = span.end()
        self.assertGreater(duration, 0)
        self.assertEqual(len(t._traces), 1)
        self.assertEqual(t._traces[0]["labels"]["key"], "val")

if __name__ == "__main__":
    unittest.main()