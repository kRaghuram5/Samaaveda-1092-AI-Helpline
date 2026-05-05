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
           "flooding", "flowing", "entering", "kids", "children", "broken pipe",
           "water", "electricity", "power", "current", "no supply", "unpleasant", "overflow",
           "sewage", "dirty", "filthy"],
    "hi": ["madad", "bachao", "jaldi", "mushkil", "takleef", "pareshani",
           "dar", "khatra", "madat", "sahayata", "khatarnak", "baadh", "paani ghus raha",
           "bijli", "paani", "current nahi", "asahiya", "gandha", "sulag"],
    "kn": ["sahaya", "bega", "tumba", "kashta", "sankate", "bhaya", "apaaya",
           "doddadu", "tondare", "neeru nuuguttide", "makkalu", "manege",
           "current", "vidyut", "neeru", "illa", "jaldi", "asahiya", "gandha",
           "harialikka", "tetri", "tetry", "hariali"],  # Added Kannada variants
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
        for pat in [r"!{2,}", r"\b(immediately|right now|asap|today|now|soon|urgent|emergency|die|death)\b",
                     r"\b(jaldi|abhi|turant|bega|tumba bega|sattoguttare|apaaya)\b",
                     r"\b(flowing|flooding|entering|nuuguttide)\b"]:
            if re.search(pat, text_lower):
                urgency_score += 1

        return {
            "distress_score": min(distress_score / 5.0, 1.0),
            "anger_score": min(anger_score / 5.0, 1.0),
            "urgency_score": min(urgency_score / 3.0, 1.0),
            "matched_keywords": list(set(matched)),
            "raw_text": text_lower,
        }

    def combine_scores(self, llm_emotion: dict, keyword_analysis: dict,
                       stt_confidence: float) -> dict:
        """Weighted combination of LLM emotion + keyword heuristics + STT confidence."""

        severity_map = {
            "neutral": 0.1, "concern": 0.4, "confusion": 0.3, "frustration": 0.6,
            "sadness": 0.5, "anger": 0.7, "fear": 0.8, "distress": 0.9, 
            "urgency": 0.85, "panic": 0.95,
        }
        urgency_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}

        # Get emotion - could be "emotion" key or "primary" key
        primary = (llm_emotion.get("emotion") or llm_emotion.get("primary") or "neutral").lower()
        llm_sev = severity_map.get(primary, 0.3)
        
        # Get urgency level from LLM
        llm_urg_str = (llm_emotion.get("urgency_level") or "medium").lower()
        llm_urg = urgency_map.get(llm_urg_str, 0.5)

        logger.info(f"Emotion: {primary}, Severity: {llm_sev}, Urgency: {llm_urg_str}")

        # Boost if LLM already detected high urgency
        if llm_urg >= 0.8:  # If LLM says CRITICAL or HIGH
            combined_urgency = 1.0 if llm_urg >= 0.9 else 0.85
        else:
            combined_urgency = llm_urg * 0.6 + keyword_analysis["urgency_score"] * 0.4

        # Also boost emotion if keywords show distress
        if keyword_analysis["distress_score"] > 0.5:
            combined_severity = max(llm_sev, 0.7)  # At least HIGH severity
        else:
            combined_severity = (llm_sev * 0.6
                                 + keyword_analysis["distress_score"] * 0.2
                                 + keyword_analysis["anger_score"] * 0.2)

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

        # Convert score back to level for UI
        if combined_urgency >= 0.9:
            urgency_level = "critical"
        elif combined_urgency >= 0.6:
            urgency_level = "high"
        elif combined_urgency >= 0.3:
            urgency_level = "medium"
        else:
            urgency_level = "low"

        return {
            "primary_emotion": primary,
            "secondary_emotion": llm_emotion.get("secondary_emotion"),
            "severity_score": round(combined_severity, 3),
            "urgency_score": round(combined_urgency, 3),
            "urgency_level": urgency_level,
            "overall_confidence": round(overall_confidence, 3),
            "needs_escalation": needs_escalation,
            "escalation_reason": "; ".join(reasons) if reasons else None,
            "distress_indicators": list(set(
                llm_emotion.get("distress_indicators", [])
                + keyword_analysis.get("matched_keywords", [])
            )),
        }
