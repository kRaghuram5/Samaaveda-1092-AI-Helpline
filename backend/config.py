import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(Path(__file__).parent / ".env")

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- Whisper Settings ---
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# --- Guardrails ---
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
ESCALATION_EMOTIONS = ["distress", "anger", "fear"]

# --- Languages ---
SUPPORTED_LANGUAGES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent
FEEDBACK_LOG_DIR = PROJECT_ROOT / "feedback_logs"
TEMP_AUDIO_DIR = Path(__file__).parent / "temp_audio"

# Ensure directories exist
FEEDBACK_LOG_DIR.mkdir(exist_ok=True)
TEMP_AUDIO_DIR.mkdir(exist_ok=True)
