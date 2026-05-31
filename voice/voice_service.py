"""
Voice Service Module for MOKA AI

Implements a voice microservice with wake engine, speech-to-text and text-to-speech abstraction,
and a state machine with the required states.

Service isolation: STT/TTS engines are loaded lazily — no heavy AI models loaded until needed.
"""

import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Lazy imports — pyaudio and wave only loaded when voice features are actually used
_pyaudio = None
_wave = None


def _get_pyaudio():
    """Lazy-load pyaudio to avoid import errors when voice is not used."""
    global _pyaudio
    if _pyaudio is None:
        try:
            import pyaudio as _pa
            _pyaudio = _pa
        except ImportError:
            _pyaudio = None
    return _pyaudio


def _get_wave():
    """Lazy-load wave module."""
    global _wave
    if _wave is None:
        import wave as _w
        _wave = _w
    return _wave


class VoiceState(Enum):
    """Voice service states."""
    SLEEPING = "sleeping"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


class VoiceStateMachine:
    """Voice state machine with transition tracking and logging."""

    VALID_TRANSITIONS = {
        VoiceState.SLEEPING: {VoiceState.LISTENING},
        VoiceState.LISTENING: {VoiceState.THINKING, VoiceState.SLEEPING, VoiceState.INTERRUPTED},
        VoiceState.THINKING: {VoiceState.SPEAKING, VoiceState.INTERRUPTED, VoiceState.SLEEPING},
        VoiceState.SPEAKING: {VoiceState.SLEEPING, VoiceState.LISTENING, VoiceState.INTERRUPTED},
        VoiceState.INTERRUPTED: {VoiceState.LISTENING, VoiceState.SLEEPING},
    }

    def __init__(self, logger: Callable[[str], None] = None):
        self._logger = logger or (lambda m: None)
        self.current_state = VoiceState.SLEEPING
        self.previous_state: Optional[VoiceState] = None
        self._transition_history: List[Dict[str, Any]] = []

    def transition(self, new_state: VoiceState) -> bool:
        """Transition to a new state. Returns True if transition is valid."""
        if self.current_state == new_state:
            return True

        valid_next = self.VALID_TRANSITIONS.get(self.current_state, set())
        if new_state not in valid_next:
            self._logger(f"Invalid transition: {self.current_state.value} -> {new_state.value}")
            return False

        self.previous_state = self.current_state
        self.current_state = new_state
        self._transition_history.append({
            "from": self.previous_state.value,
            "to": new_state.value,
            "valid": True,
        })
        self._logger(f"[VoiceState] {self.previous_state.value} -> {new_state.value}")
        return True

    def get_history(self) -> List[Dict[str, Any]]:
        """Return transition history."""
        return self._transition_history.copy()


class WakeEngine:
    """Lightweight wake word detection engine.

    Uses energy-based detection as a lightweight fallback.
    Configurable to use Voskit or Picovoice when available.
    """

    def __init__(self, wake_word: str = "moka", logger: Callable[[str], None] = None):
        self._logger = logger or (lambda m: None)
        self.wake_word = wake_word.lower()
        self.is_active = False
        self._audio_threshold = 500
        self._consecutive_hits = 0
        self._hits_required = 2

    def detect_wake_word(self, audio_data: bytes) -> bool:
        """Detect if the wake word is present in audio.

        Uses a basic energy threshold approach. In production, replace with
        a proper wake word model (e.g., openwakeword, voskit, or picovoice).
        """
        if not self.is_active:
            return False

        try:
            energy = self._calculate_energy(audio_data)
            if energy > self._audio_threshold:
                self._consecutive_hits += 1
                if self._consecutive_hits >= self._hits_required:
                    self._logger(f"Wake word '{self.wake_word}' detected")
                    self._consecutive_hits = 0
                    return True
            else:
                self._consecutive_hits = 0
        except Exception as e:
            self._logger(f"Wake detection error: {e}")

        return False

    def _calculate_energy(self, audio_data: bytes) -> int:
        """Calculate audio energy from raw bytes (16-bit samples)."""
        if len(audio_data) < 2:
            return 0
        try:
            import struct
            num_samples = len(audio_data) // 2
            samples = struct.unpack(f"{num_samples}h", audio_data)
            return sum(abs(s) for s in samples) // num_samples if num_samples > 0 else 0
        except Exception:
            return 0

    def activate(self) -> None:
        """Activate the wake engine."""
        self.is_active = True
        self._logger("Wake engine activated")

    def deactivate(self) -> None:
        """Deactivate the wake engine."""
        self.is_active = False
        self._consecutive_hits = 0
        self._logger("Wake engine deactivated")

    def set_threshold(self, threshold: int) -> None:
        """Set the audio energy threshold for detection."""
        self._audio_threshold = threshold

    def is_activated(self) -> bool:
        """Check if wake engine is currently active."""
        return self.is_active


class XTTSEngine:
    """Coqui XTTS v2 — fully offline neural TTS, no internet ever needed.

    Language: Tagalog (tl) for Moka's bilingual Tagalog-English companion voice.

    Voice: determined entirely by the speaker reference WAV bundled in
    xttsv2-female.tar.gz (must be a female Filipino speaker, fluent Tagalog).
    This IS Moka's voice — XTTS clones it on-device, zero cloud dependency.

    XTTS v2 is multilingual: supports 17 languages including English, Spanish,
    and Filipino. It will speak Tagalog words/numbers/code-switched sentences
    naturally as long as the reference WAV is a native Tagalog speaker.

    Lazy-loads the model on first synthesis so startup is instant.
    Graceful no-op if TTS package or model files are absent.
    """

    def __init__(
        self,
        model_dir: str = "models/voice/xttsv2-female",
        ref_wav: str = "models/voice/xttsv2-female/moka_voice_ref.wav",
        logger: Callable[[str], None] = None,
    ):
        self._model_dir = model_dir
        self._ref_wav = ref_wav
        self._log = logger or (lambda m: None)
        self._tts = None
        self._sample_rate = 22050

    def _ensure_model(self):
        """Load XTTS model once, on first use."""
        if self._tts is not None:
            return
        try:
            from TTS.api import TTS
        except ImportError:
            self._log("[XTTS] TTS package not installed — pip install TTS")
            return

        gpu = False
        try:
            import torch
            gpu = torch.cuda.is_available()
        except Exception:
            pass

        try:
            self._tts = TTS(model_path=self._model_dir, gpu=gpu)
            self._log(f"[XTTS] Model loaded (gpu={gpu})")
        except Exception as e:
            self._log(f"[XTTS] Failed to load model from {self._model_dir}: {e}")
            self._tts = None

    def __call__(self, text: str) -> Optional[bytes]:
        """Synthesize text to WAV audio bytes using the speaker reference voice."""
        self._ensure_model()
        if self._tts is None:
            return None

        try:
            # XTTS v2: speaker_wav is the voice clone reference, language is ISO 639-1
            wav = self._tts.tts(text=text, speaker_wav=self._ref_wav, language="tl")
            return self._array_to_wav_bytes(wav)
        except Exception as e:
            self._log(f"[XTTS] Synthesis error: {e}")
            return None

    def _array_to_wav_bytes(self, wav) -> bytes:
        """Convert float32 numpy/audio array to 16-bit mono WAV bytes (pure stdlib)."""
        import array
        import io
        import struct

        # Clamp and convert float32 [-1, 1] → int16 PCM
        int_samples = [int(max(-1.0, min(1.0, float(x))) * 32767) for x in wav]
        samples = array.array("h", int_samples)

        buf = io.BytesIO()
        bw = 2    # bytes per sample (16-bit)
        ch = 1    # mono
        sr = self._sample_rate
        dsize = len(samples) * bw

        # RIFF header
        buf.write(struct.pack("<4sI4s", b"RIFF", 36 + dsize, b"WAVE"))
        # fmt chunk — PCM format
        buf.write(struct.pack("<4sIHHIIHH",
            b"fmt ", 16, 1, ch, sr, sr * ch * bw, ch * bw, bw))
        # data chunk
        buf.write(struct.pack("<4sI", b"data", dsize))
        buf.write(samples.tobytes())
        return buf.getvalue()


class SpeechToTextAbstraction:
    """Abstraction layer for speech-to-text providers.

    No heavy models loaded until transcribe() is called.
    """

    def __init__(self, logger: Callable[[str], None] = None):
        self._logger = logger or (lambda m: None)
        self.provider: Optional[str] = None
        self._engine = None

    def set_provider(self, provider_name: str) -> None:
        """Set the STT provider. No model loading at this point."""
        self.provider = provider_name
        self._engine = None
        self._logger(f"STT provider set to: {provider_name}")

    def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text.

        Loads the configured provider's model on first use (lazy loading).
        """
        if self.provider is None:
            self._logger("No STT provider configured, returning empty string")
            return ""

        if self._engine is None:
            self._engine = self._load_engine(self.provider)

        try:
            text = self._engine(audio_data)
            self._logger(f"Transcribed: {text[:50]}...")
            return text
        except Exception as e:
            self._logger(f"Transcription error: {e}")
            return ""

    def _load_engine(self, provider: str) -> Callable[[bytes], str]:
        """Lazy-load the STT engine. Models only loaded when transcription is needed."""
        if provider == "mock" or provider is None:
            return lambda audio: ""
        elif provider == "whisper":
            # TODO: integrate whispercpp or openai-whisper when available
            self._logger("Whisper STT not yet configured")
            return lambda audio: ""
        else:
            self._logger(f"Unknown STT provider: {provider}, using no-op")
            return lambda audio: ""

    def is_loaded(self) -> bool:
        """Check if the STT engine has been loaded."""
        return self._engine is not None


class TextToSpeechAbstraction:
    """Abstraction layer for text-to-speech providers.

    No heavy models loaded until synthesize() is called.
    """

    def __init__(self, logger: Callable[[str], None] = None):
        self._logger = logger or (lambda m: None)
        self.provider: Optional[str] = None
        self._engine = None

    def set_provider(self, provider_name: str) -> None:
        """Set the TTS provider. No model loading at this point."""
        self.provider = provider_name
        self._engine = None
        self._logger(f"TTS provider set to: {provider_name}")

    def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize text to speech audio.

        Loads the configured provider's model on first use (lazy loading).
        Returns audio bytes or None on failure.
        """
        if self.provider is None:
            self._logger("No TTS provider configured")
            return None

        if self._engine is None:
            self._engine = self._load_engine(self.provider)

        try:
            audio = self._engine(text)
            self._logger(f"TTS synthesized {len(text)} chars")
            return audio
        except Exception as e:
            self._logger(f"TTS synthesis error: {e}")
            return None

    def _load_engine(self, provider: str) -> Callable[[str], Optional[bytes]]:
        """Lazy-load the TTS engine. Models only loaded when synthesis is needed."""
        if provider == "mock" or provider is None:
            return lambda text: None
        elif provider == "tts":
            self._logger("Loading XTTS v2 TTS engine...")
            # model_dir: extracted xttsv2-female/ directory (from xttsv2-female.tar.gz).
            # This archive MUST contain the XTTS v2 model files + moka_voice_ref.wav
            # (a female Filipino speaker reading fluent Tagalog — this IS Moka's voice).
            # After install, no internet is ever needed for TTS synthesis.
            return XTTSEngine(
                model_dir="models/voice/xttsv2-female",
                ref_wav="models/voice/xttsv2-female/moka_voice_ref.wav",
                logger=self._logger,
            )
        else:
            self._logger(f"Unknown TTS provider: {provider}, using no-op")
            return lambda text: None

    def is_loaded(self) -> bool:
        """Check if the TTS engine has been loaded."""
        return self._engine is not None


class VoiceService:
    """Main voice service — coordinates wake engine, STT, TTS, and state machine."""

    def __init__(self, logger: Callable[[str], None] = None):
        # Unify logger interface: support plain callables or objects with .info()
        if logger is None:
            self._log = lambda m: None
        elif callable(logger):
            self._log = logger
        elif hasattr(logger, 'info'):
            self._log = logger.info
        else:
            self._log = lambda m: None
        self.state = VoiceState.SLEEPING
        self.wake_engine: Optional[WakeEngine] = None
        self.stt_engine: Optional[SpeechToTextAbstraction] = None
        self.tts_engine: Optional[TextToSpeechAbstraction] = None
        self.state_machine = VoiceStateMachine(logger=self._log)
        self.is_listening = False
        self.interrupt_event = threading.Event()
        self._interrupt_handlers: List[Callable[[], None]] = []

    def initialize(self) -> None:
        """Initialize voice service components (lazy — no heavy models loaded)."""
        self.wake_engine = WakeEngine(logger=self._log)
        self.stt_engine = SpeechToTextAbstraction(logger=self._log)
        self.tts_engine = TextToSpeechAbstraction(logger=self._log)
        self._log("[VoiceService] Initialized (no AI models loaded)")

    def set_state(self, new_state: VoiceState) -> None:
        """Set the voice service state, with transition validation."""
        old_state = self.state
        if self.state_machine.transition(new_state):
            self.state = new_state
            self._log(f"[VoiceService] State: {old_state.value} -> {new_state.value}")
        else:
            self._log(f"[VoiceService] Invalid state transition attempted: {old_state.value} -> {new_state.value}")

    def get_state(self) -> VoiceState:
        """Get the current voice state."""
        return self.state

    def process_wake_word(self, audio_data: bytes) -> bool:
        """Process audio data for wake word detection."""
        if self.wake_engine and self.wake_engine.detect_wake_word(audio_data):
            self.set_state(VoiceState.LISTENING)
            return True
        return False

    def start_listening(self) -> bool:
        """Start the listening process."""
        self.set_state(VoiceState.LISTENING)
        self.is_listening = True
        self.interrupt_event.clear()
        return True

    def stop_listening(self) -> bool:
        """Stop the listening process."""
        self.is_listening = False
        self.set_state(VoiceState.SLEEPING)
        return True

    def listen_and_transcribe(self, audio_data: bytes) -> str:
        """Listen and transcribe audio, transitioning through proper states."""
        self.set_state(VoiceState.LISTENING)
        if self.stt_engine:
            text = self.stt_engine.transcribe(audio_data)
        else:
            text = ""
        return text

    def interrupt_speaking(self) -> bool:
        """Interrupt current speaking and transition to INTERRUPTED state."""
        self.set_state(VoiceState.INTERRUPTED)
        self.interrupt_event.set()
        for handler in self._interrupt_handlers:
            try:
                handler()
            except Exception as e:
                self._log(f"Interrupt handler error: {e}")
        self._log("[VoiceService] Speaking interrupted")
        return True

    def speak_text(self, text: str) -> bool:
        """Synthesize and speak text through TTS engine."""
        self.set_state(VoiceState.SPEAKING)
        try:
            if self.tts_engine and self.tts_engine.is_loaded():
                audio = self.tts_engine.synthesize(text)
                if audio:
                    self._play_audio(audio)
        except Exception as e:
            self._log(f"Speaking error: {e}")
        finally:
            if not self.interrupt_event.is_set():
                self.set_state(VoiceState.SLEEPING)
        return True

    def _play_audio(self, audio_data: bytes) -> None:
        """Play audio data. Override with platform-specific implementation."""
        pa = _get_pyaudio()
        if pa is None:
            self._log("pyaudio not available, skipping audio playback")
            return

        try:
            p = pa.PyAudio()
            stream = p.open(format=p.get_format_from_width(2), channels=1, rate=22050, output=True)
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception as e:
            self._log(f"Audio playback error: {e}")

    def on_interrupt(self, handler: Callable[[], None]) -> None:
        """Register a handler to be called when speaking is interrupted."""
        self._interrupt_handlers.append(handler)

    def transitions(self) -> List[Dict[str, Any]]:
        """Return the state machine's transition history."""
        return self.state_machine.get_history()