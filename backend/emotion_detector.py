"""
Emotion Detector — keyword heuristics combined with LLM emotion output.
"""
import re
import logging

logger = logging.getLogger(__name__)

# Multilingual distress / urgency keywords
DISTRESS_KEYWORDS = {
    "en": ["help", "emergency", "urgent", "dying", "please", "desperate",
           "suffering", "terrible", "worst", "dangerous", "scared", "afraid", "panic",
           "flooding", "flowing", "entering", "kids", "children", "broken pipe"],
    "hi": ["madad", "bachao", "jaldi", "mushkil", "takleef", "pareshani",
           "dar", "khatra", "madat", "sahayata", "khatarnak", "baadh", "paani ghus raha"],
    "kn": ["sahaya", "bega", "tumba", "kashta", "sankate", "bhaya", "apaaya",
           "doddadu", "tondare", "neeru nuuguttide", "makkalu", "manege"],
}

ANGER_KEYWORDS = {
    "en": ["useless", "incompetent", "nothing done", "no action", "waste",
           "corrupt", "lazy", "pathetic", "disgusting", "fed up"],
    "hi": ["bekar", "nikamma", "kuch nahi", "bhrashtachar", "thak gaya", "pareshan"],
    "kn": ["bekara", "yenu illa", "corrupt", "kelsa aagilla"],
}


class EmotionDetector:
    """Combines keyword heuristics with LLM emotion output for scoring."""

    def analyze_keywords(self, text: str) -> dict:
        text_lower = text.lower()
        distress_score = 0
        anger_score = 0
        urgency_score = 0
        matched = []

        for keywords in DISTRESS_KEYWORDS.values():
            for kw in keywords:
                if kw in text_lower:
                    distress_score += 1
                    matched.append(kw)

        for keywords in ANGER_KEYWORDS.values():
            for kw in keywords:
                if kw in text_lower:
                    anger_score += 1
                    matched.append(kw)

        # Urgency patterns
        for pat in [r"!{2,}", r"\b(immediately|right now|asap|today|now|soon)\b",
                     r"\b(jaldi|abhi|turant|bega|tumba bega)\b",
                     r"\b(flowing|flooding|entering|nuuguttide)\b"]:
            if re.search(pat, text_lower):
                urgency_score += 1

        return {
            "distress_score": min(distress_score / 5.0, 1.0),
            "anger_score": min(anger_score / 5.0, 1.0),
            "urgency_score": min(urgency_score / 3.0, 1.0),
            "matched_keywords": list(set(matched)),
        }

    def combine_scores(self, llm_emotion: dict, keyword_analysis: dict,
                       stt_confidence: float) -> dict:
        """Weighted combination of LLM emotion + keyword heuristics + STT confidence."""

        severity_map = {
            "neutral": 0.1, "confusion": 0.3, "frustration": 0.5,
            "sadness": 0.5, "anger": 0.7, "fear": 0.8,
            "distress": 0.9, "urgency": 0.85,
        }
        urgency_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}

        primary = llm_emotion.get("primary", "neutral")
        llm_sev = severity_map.get(primary, 0.3)
        llm_urg = urgency_map.get(llm_emotion.get("urgency_level", "medium"), 0.5)

        combined_severity = (llm_sev * 0.6
                             + keyword_analysis["distress_score"] * 0.2
                             + keyword_analysis["anger_score"] * 0.2)
        combined_urgency = llm_urg * 0.6 + keyword_analysis["urgency_score"] * 0.4

        # --- URGENCY BOOSTER (The Edge Case Fix) ---
        booster_words = ["nuuguttide", "nuuguttidd", "flooding", "children", "makkalu", "manege", "entering"]
        if any(word in keyword_analysis["matched_keywords"] for word in booster_words) or \
           any(word in llm_emotion.get("distress_indicators", []) for word in booster_words):
            combined_urgency = max(combined_urgency, 0.95) # Force to Critical
            logger.info("Urgency Booster triggered: Property/Safety risk detected.")

        overall_confidence = stt_confidence * 0.4 + (1 - combined_severity * 0.3) * 0.6

        needs_escalation = (combined_severity > 0.7
                            or combined_urgency > 0.8
                            or stt_confidence < 0.4
                            or overall_confidence < 0.5)

        reasons = []
        if combined_severity > 0.7:
            reasons.append("High emotional distress detected")
        if combined_urgency > 0.8:
            reasons.append("Critical urgency level")
        if stt_confidence < 0.4:
            reasons.append("Low speech recognition confidence")
        if overall_confidence < 0.5:
            reasons.append("Low overall understanding confidence")

        return {
            "primary_emotion": primary,
            "secondary_emotion": llm_emotion.get("secondary"),
            "severity_score": round(combined_severity, 3),
            "urgency_score": round(combined_urgency, 3),
            "overall_confidence": round(overall_confidence, 3),
            "needs_escalation": needs_escalation,
            "escalation_reason": "; ".join(reasons) if reasons else None,
            "distress_indicators": list(set(
                llm_emotion.get("distress_indicators", [])
                + keyword_analysis.get("matched_keywords", [])
            )),
        }
