"""
Verification Engine — manages the confirmation loop per session.
"""
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class VerificationState(str, Enum):
    PENDING = "pending"
    AWAITING = "awaiting_verification"
    CONFIRMED = "confirmed"
    PARTIAL = "partially_confirmed"
    DENIED = "denied"
    ESCALATED = "escalated"
    AGENT_CONFIRMED = "agent_confirmed"


class VerificationEngine:
    def __init__(self):
        self.sessions: dict[str, dict] = {}

    def create_session(self, session_id: str) -> dict:
        self.sessions[session_id] = {
            "state": VerificationState.PENDING,
            "transcript": "",
            "structured_data": None,
            "emotion_data": None,
            "confidence": 0.0,
            "verification_attempts": 0,
            "corrections": [],
            "agent_edits": [],
        }
        return self.sessions[session_id]

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    def update_transcript(self, sid: str, transcript: str):
        if sid in self.sessions:
            self.sessions[sid]["transcript"] = transcript

    def update_structured_data(self, sid: str, data: dict):
        if sid in self.sessions:
            self.sessions[sid]["structured_data"] = data
            self.sessions[sid]["state"] = VerificationState.AWAITING

    def update_emotion(self, sid: str, emotion_data: dict):
        if sid in self.sessions:
            self.sessions[sid]["emotion_data"] = emotion_data
            self.sessions[sid]["confidence"] = emotion_data.get("overall_confidence", 0.0)

    def process_citizen_response(self, sid: str, response: str, correction: str = None) -> dict:
        session = self.sessions.get(sid)
        if not session:
            return {"error": "Session not found"}

        session["verification_attempts"] += 1

        if response == "correct":
            session["state"] = VerificationState.CONFIRMED
            return {"state": "confirmed", "message": "Understanding verified ✓", "action": "proceed"}

        if response == "partial":
            session["state"] = VerificationState.PARTIAL
            if correction:
                session["corrections"].append(correction)
            return {"state": "partial", "message": "Partial — correction noted",
                    "action": "re_process", "correction": correction}

        if response == "incorrect":
            session["state"] = VerificationState.DENIED
            if correction:
                session["corrections"].append(correction)
            if session["verification_attempts"] >= 2:
                return {"state": "denied", "message": "Verification failed — escalation recommended",
                        "action": "escalate", "correction": correction}
            return {"state": "denied", "message": "Not verified — re-processing",
                    "action": "re_process", "correction": correction}

        return {"error": "Invalid response type"}

    def agent_edit(self, sid: str, field: str, value: str) -> bool:
        session = self.sessions.get(sid)
        if not session or not session["structured_data"]:
            return False
        session["agent_edits"].append({
            "field": field,
            "old": session["structured_data"].get(field),
            "new": value,
        })
        session["structured_data"][field] = value
        return True

    def agent_confirm(self, sid: str) -> dict:
        session = self.sessions.get(sid)
        if not session:
            return {"error": "Session not found"}
        session["state"] = VerificationState.AGENT_CONFIRMED
        return {"state": "agent_confirmed", "message": "Agent confirmed understanding"}

    def agent_escalate(self, sid: str, reason: str = "") -> dict:
        session = self.sessions.get(sid)
        if not session:
            return {"error": "Session not found"}
        session["state"] = VerificationState.ESCALATED
        return {"state": "escalated", "message": f"Escalated to human agent: {reason}"}

    def get_full_session_data(self, sid: str) -> dict | None:
        return self.sessions.get(sid)
