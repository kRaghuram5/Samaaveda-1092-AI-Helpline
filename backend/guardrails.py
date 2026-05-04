"""
Guardrails — confidence-aware escalation and safety checks.
"""
import logging
from config import CONFIDENCE_THRESHOLD, ESCALATION_EMOTIONS

logger = logging.getLogger(__name__)


class Guardrails:
    """Evaluates whether a session should be escalated to a human agent."""

    def __init__(self, threshold: float = None):
        self.threshold = threshold or CONFIDENCE_THRESHOLD

    def evaluate(self, emotion_data: dict, stt_confidence: float,
                 verification_state: str) -> dict:
        """
        Returns escalation recommendation based on multiple signals.
        """
        alerts = []
        level = "normal"  # normal | warning | critical

        overall = emotion_data.get("overall_confidence", 1.0)
        primary = emotion_data.get("primary_emotion", "neutral")
        severity = emotion_data.get("severity_score", 0.0)
        urgency = emotion_data.get("urgency_score", 0.0)

        # Low STT confidence
        if stt_confidence < 0.4:
            alerts.append("Speech recognition confidence very low")
            level = "critical"
        elif stt_confidence < self.threshold:
            alerts.append("Speech recognition confidence below threshold")
            level = max_level(level, "warning")

        # High-distress emotion
        if primary in ESCALATION_EMOTIONS:
            alerts.append(f"Detected high-risk emotion: {primary}")
            level = max_level(level, "warning")
        if severity > 0.7:
            alerts.append("High emotional severity score")
            level = max_level(level, "critical")

        # Urgency
        if urgency > 0.8:
            alerts.append("Critical urgency detected")
            level = max_level(level, "critical")

        # Verification failures
        if verification_state in ("denied", "escalated"):
            alerts.append("Citizen verification failed")
            level = max_level(level, "critical")
        elif verification_state == "partially_confirmed":
            alerts.append("Only partial verification achieved")
            level = max_level(level, "warning")

        # Overall confidence
        if overall < 0.5:
            alerts.append("Overall understanding confidence low")
            level = max_level(level, "critical")

        return {
            "level": level,
            "should_escalate": level == "critical",
            "alerts": alerts,
            "confidence_score": round(overall, 3),
        }


def max_level(current: str, candidate: str) -> str:
    order = {"normal": 0, "warning": 1, "critical": 2}
    return candidate if order.get(candidate, 0) > order.get(current, 0) else current
