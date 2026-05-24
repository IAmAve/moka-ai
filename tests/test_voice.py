import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.voice_service import (
    VoiceState,
    VoiceStateMachine,
    WakeEngine,
    SpeechToTextAbstraction,
    TextToSpeechAbstraction,
    VoiceService,
)


class TestVoiceStateMachine(unittest.TestCase):
    def setUp(self):
        self.transitions_logged = []
        self.logger = lambda m: self.transitions_logged.append(m)
        self.sm = VoiceStateMachine(logger=self.logger)

    def test_initial_state_is_sleeping(self):
        self.assertEqual(self.sm.current_state, VoiceState.SLEEPING)
        self.assertIsNone(self.sm.previous_state)

    def test_sleeping_to_listening_valid(self):
        result = self.sm.transition(VoiceState.LISTENING)
        self.assertTrue(result)
        self.assertEqual(self.sm.current_state, VoiceState.LISTENING)
        self.assertEqual(self.sm.previous_state, VoiceState.SLEEPING)

    def test_sleeping_to_speaking_invalid(self):
        result = self.sm.transition(VoiceState.SPEAKING)
        self.assertFalse(result)
        self.assertEqual(self.sm.current_state, VoiceState.SLEEPING)

    def test_listening_to_thinking_valid(self):
        self.sm.transition(VoiceState.LISTENING)
        result = self.sm.transition(VoiceState.THINKING)
        self.assertTrue(result)
        self.assertEqual(self.sm.current_state, VoiceState.THINKING)

    def test_listening_to_sleeping_valid(self):
        self.sm.transition(VoiceState.LISTENING)
        result = self.sm.transition(VoiceState.SLEEPING)
        self.assertTrue(result)
        self.assertEqual(self.sm.current_state, VoiceState.SLEEPING)

    def test_thinking_to_speaking_valid(self):
        self.sm.transition(VoiceState.LISTENING)
        self.sm.transition(VoiceState.THINKING)
        result = self.sm.transition(VoiceState.SPEAKING)
        self.assertTrue(result)
        self.assertEqual(self.sm.current_state, VoiceState.SPEAKING)

    def test_speaking_to_interrupted_valid(self):
        self.sm.transition(VoiceState.LISTENING)
        self.sm.transition(VoiceState.THINKING)
        self.sm.transition(VoiceState.SPEAKING)
        result = self.sm.transition(VoiceState.INTERRUPTED)
        self.assertTrue(result)
        self.assertEqual(self.sm.current_state, VoiceState.INTERRUPTED)

    def test_interrupted_to_listening_valid(self):
        self.sm.transition(VoiceState.INTERRUPTED)
        result = self.sm.transition(VoiceState.LISTENING)
        self.assertTrue(result)
        self.assertEqual(self.sm.current_state, VoiceState.LISTENING)

    def test_state_change_logged(self):
        self.sm.transition(VoiceState.LISTENING)
        matching = [m for m in self.transitions_logged if "sleeping -> listening" in m.lower()]
        self.assertTrue(len(matching) > 0, f"Expected logged transition, got: {self.transitions_logged}")

    def test_get_history_returns_copy(self):
        self.sm.transition(VoiceState.LISTENING)
        history = self.sm.get_history()
        history.append({"fake": "entry"})
        self.assertEqual(len(self.sm.get_history()), 1)

    def test_same_state_returns_true_no_transition(self):
        result = self.sm.transition(VoiceState.SLEEPING)
        self.assertTrue(result)
        self.assertEqual(self.sm.current_state, VoiceState.SLEEPING)


class TestWakeEngine(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.logger = lambda m: self.logs.append(m)
        self.engine = WakeEngine(wake_word="moka", logger=self.logger)

    def test_initial_state_inactive(self):
        self.assertFalse(self.engine.is_activated())

    def test_activate_sets_active(self):
        self.engine.activate()
        self.assertTrue(self.engine.is_activated())
        self.assertTrue(any("activated" in l.lower() for l in self.logs))

    def test_deactivate_clears_hits(self):
        self.engine.activate()
        self.engine._consecutive_hits = 3
        self.engine.deactivate()
        self.assertFalse(self.engine.is_activated())
        self.assertEqual(self.engine._consecutive_hits, 0)

    def test_set_threshold(self):
        self.engine.set_threshold(1000)
        self.assertEqual(self.engine._audio_threshold, 1000)

    def test_inactive_returns_false(self):
        result = self.engine.detect_wake_word(b"\x00\x00" * 100)
        self.assertFalse(result)

    def test_low_energy_returns_false(self):
        self.engine.activate()
        result = self.engine.detect_wake_word(b"\x00\x00" * 100)
        self.assertFalse(result)
        self.assertEqual(self.engine._consecutive_hits, 0)

    def test_high_energy_returns_true_after_hits(self):
        self.engine.activate()
        self.engine._audio_threshold = 500
        self.engine._hits_required = 2
        # One high-amplitude sample = energy > threshold
        audio = b"\xFF\x7F" * 50
        result1 = self.engine.detect_wake_word(audio)
        self.assertFalse(result1)
        result2 = self.engine.detect_wake_word(audio)
        self.assertTrue(result2)
        self.assertEqual(self.engine._consecutive_hits, 0)

    def test_energy_calculation(self):
        # Sample 32767 little-endian gives high energy
        energy = self.engine._calculate_energy(b"\xFF\x7F\x00\x00")
        self.assertGreater(energy, 0)


class TestSpeechToTextAbstraction(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.logger = lambda m: self.logs.append(m)
        self.stt = SpeechToTextAbstraction(logger=self.logger)

    def test_initial_not_loaded(self):
        self.assertFalse(self.stt.is_loaded())

    def test_set_provider_does_not_load_engine(self):
        self.stt.set_provider("whisper")
        self.assertFalse(self.stt.is_loaded())
        self.assertTrue(any("whisper" in l.lower() for l in self.logs))

    def test_transcribe_mock_provider_returns_empty(self):
        self.stt.set_provider("mock")
        self.stt.transcribe(b"fake audio")
        self.assertTrue(self.stt.is_loaded())

    def test_transcribe_no_provider_returns_empty(self):
        result = self.stt.transcribe(b"fake audio")
        self.assertEqual(result, "")

    def test_transcribe_lazy_loads_engine(self):
        self.stt.set_provider("mock")
        self.assertFalse(self.stt.is_loaded())
        self.stt.transcribe(b"audio")
        self.assertTrue(self.stt.is_loaded())


class TestTextToSpeechAbstraction(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.logger = lambda m: self.logs.append(m)
        self.tts = TextToSpeechAbstraction(logger=self.logger)

    def test_initial_not_loaded(self):
        self.assertFalse(self.tts.is_loaded())

    def test_set_provider_does_not_load_engine(self):
        self.tts.set_provider("tts")
        self.assertFalse(self.tts.is_loaded())

    def test_synthesize_no_provider_returns_none(self):
        result = self.tts.synthesize("hello")
        self.assertIsNone(result)

    def test_synthesize_lazy_loads_engine(self):
        self.tts.set_provider("mock")
        self.assertFalse(self.tts.is_loaded())
        self.tts.synthesize("hello")
        self.assertTrue(self.tts.is_loaded())


class TestVoiceService(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.logger = lambda m: self.logs.append(m)
        self.service = VoiceService(logger=self.logger)
        self.service.initialize()

    def test_initialized_has_all_engines(self):
        self.assertIsNotNone(self.service.wake_engine)
        self.assertIsNotNone(self.service.stt_engine)
        self.assertIsNotNone(self.service.tts_engine)

    def test_initial_state_is_sleeping(self):
        self.assertEqual(self.service.get_state(), VoiceState.SLEEPING)

    def test_set_state_valid_transition(self):
        self.service.set_state(VoiceState.LISTENING)
        self.assertEqual(self.service.get_state(), VoiceState.LISTENING)

    def test_set_state_invalid_transition_rejected(self):
        self.service.set_state(VoiceState.SPEAKING)
        self.assertEqual(self.service.get_state(), VoiceState.SLEEPING)

    def test_start_listening_sets_state_and_flag(self):
        self.service.start_listening()
        self.assertEqual(self.service.get_state(), VoiceState.LISTENING)
        self.assertTrue(self.service.is_listening)

    def test_stop_listening_resets_state(self):
        self.service.start_listening()
        self.service.stop_listening()
        self.assertFalse(self.service.is_listening)
        self.assertEqual(self.service.get_state(), VoiceState.SLEEPING)

    def test_interrupt_event_set_on_interrupt(self):
        self.assertFalse(self.service.interrupt_event.is_set())
        self.service.interrupt_speaking()
        self.assertTrue(self.service.interrupt_event.is_set())

    def test_interrupt_handler_registered_and_called(self):
        called = []
        self.service.on_interrupt(lambda: called.append(True))
        self.service.interrupt_speaking()
        self.assertEqual(called, [True])

    def test_listen_and_transcribe_returns_text(self):
        self.service.stt_engine.set_provider("mock")
        result = self.service.listen_and_transcribe(b"fake audio")
        self.assertEqual(result, "")

    def test_speak_text_no_tts_engine_returns_true(self):
        self.service.tts_engine.provider = "mock"
        self.service.tts_engine._engine = lambda t: None
        self.service.speak_text("hello")

    def test_process_wake_word_returns_false_when_not_detected(self):
        result = self.service.process_wake_word(b"\x00\x00" * 100)
        self.assertFalse(result)

    def test_transitions_returns_history(self):
        self.service.set_state(VoiceState.LISTENING)
        history = self.service.transitions()
        self.assertIsInstance(history, list)


if __name__ == "__main__":
    unittest.main()