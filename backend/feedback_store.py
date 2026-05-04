"""
Feedback Store — logs corrections, agent edits, and session data as JSON for learning signals.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from config import FEEDBACK_LOG_DIR

logger = logging.getLogger(__name__)


class FeedbackStore:
    def __init__(self):
        self.log_dir = Path(FEEDBACK_LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_session(self, session_id: str, session_data: dict):
        """Persist full session data as a JSON file."""
        entry = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transcript": session_data.get("transcript", ""),
            "structured_data": session_data.get("structured_data"),
            "emotion_data": session_data.get("emotion_data"),
            "final_state": session_data.get("state"),
            "confidence": session_data.get("confidence"),
            "verification_attempts": session_data.get("verification_attempts", 0),
            "corrections": session_data.get("corrections", []),
            "agent_edits": session_data.get("agent_edits", []),
        }

        filename = f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.log_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
            logger.info(f"Session logged: {filepath}")
        except Exception as e:
            logger.error(f"Failed to log session: {e}")

    def log_correction(self, session_id: str, original: dict, corrected: dict, source: str):
        """Log individual correction events for training data."""
        entry = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,  # "citizen" or "agent"
            "original": original,
            "corrected": corrected,
        }

        filepath = self.log_dir / "corrections.jsonl"
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to log correction: {e}")

    def get_session_logs(self, limit: int = 20) -> list:
        """Retrieve recent session logs."""
        files = sorted(self.log_dir.glob("session_*.json"), reverse=True)[:limit]
        logs = []
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    logs.append(json.load(f))
            except Exception:
                pass
        return logs
