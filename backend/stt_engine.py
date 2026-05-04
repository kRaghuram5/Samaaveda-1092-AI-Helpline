"""
Speech-to-Text Engine using faster-whisper.
Handles multilingual transcription for Kannada, Hindi, and English.
"""
import os
import tempfile
import logging
from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, TEMP_AUDIO_DIR

logger = logging.getLogger(__name__)


class STTEngine:
    """Singleton Speech-to-Text engine wrapping faster-whisper."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._model = None

    def load_model(self):
        """Lazy-load the Whisper model on first use."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {WHISPER_MODEL_SIZE} on {WHISPER_DEVICE} ({WHISPER_COMPUTE_TYPE})")
            self._model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            logger.info("Whisper model loaded successfully")

    def transcribe(self, audio_bytes: bytes, language: str = None) -> dict:
        """
        Transcribe audio bytes (webm/opus format) to text.
        Returns dict with text, language, confidence, segments, duration.
        """
        self.load_model()

        # Write audio to a temp file for Whisper to read
        tmp_path = os.path.join(str(TEMP_AUDIO_DIR), f"chunk_{id(audio_bytes)}.webm")
        try:
            with open(tmp_path, "wb") as f:
                f.write(audio_bytes)

            lang_arg = language if language and language != "auto" else None
            logger.info(f"Transcribing with language arg: {lang_arg}")
            segments_gen, info = self._model.transcribe(
                tmp_path,
                language=lang_arg,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=1000), # Increased from 500
                # --- Stability Parameters ---
                condition_on_previous_text=False, 
                repetition_penalty=1.1,           
                no_repeat_ngram_size=3,
                initial_prompt="Helpline call in Kannada: Mysore, Bangalore, water supply, electricity, days." 
            )

            segments_list = []
            full_text = ""
            total_confidence = 0.0
            count = 0

            for seg in segments_gen:
                segments_list.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                    "avg_logprob": round(seg.avg_logprob, 4),
                })
                full_text += seg.text
                # Convert log-prob to a 0-1 confidence
                confidence = min(1.0, max(0.0, 1.0 + seg.avg_logprob))
                total_confidence += confidence
                count += 1

            avg_confidence = total_confidence / max(count, 1)

            return {
                "text": full_text.strip(),
                "language": info.language,
                "language_probability": round(info.language_probability, 3),
                "segments": segments_list,
                "confidence": round(avg_confidence, 3),
                "duration": round(info.duration, 2),
            }
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                "text": "",
                "language": "unknown",
                "language_probability": 0.0,
                "segments": [],
                "confidence": 0.0,
                "duration": 0.0,
                "error": str(e),
            }
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
