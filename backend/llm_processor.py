"""
LLM Processor using the NEW google-genai SDK with Auto-Model Detection.
"""
import json
import logging
from google import genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)


class LLMProcessor:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_id = "gemini-1.5-flash" # Default
        
        try:
            # Auto-detect which model your API key has access to
            available = []
            for m in self.client.models.list():
                name = m.name.split('/')[-1]
                available.append(name)
            
            logger.info(f"Your API key has access to: {available}")
            
            # Priority list for a selection demo
            priority = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-pro"]
            found = False
            for p in priority:
                if p in available:
                    self.model_id = p
                    found = True
                    break
            
            if not found and available:
                self.model_id = available[0] # Pick whatever is there!
            
            logger.info(f"Auto-selected model: {self.model_id}")
            
        except Exception as e:
            logger.error(f"Model Detection Error: {e}")

    async def process_transcript(self, transcript: str, language: str = "en") -> dict:
        lang_name = {"en": "English", "hi": "Hindi", "kn": "Kannada", "ta": "Tamil/Kannada"}.get(language, language)

        prompt = f"""You are an AI assistant for India's 1092 citizen helpline.
Analyze the following citizen's spoken message and extract structured information.

IMPORTANT: The transcript might be in the WRONG script (e.g., Telugu script instead of Kannada). 
If you see Telugu characters but the context is Mangaluru/Karnataka, convert it to CLEAN KANNADA script for the normalized_text and confirmation_sentence.

URGENCY GUIDELINE: If water is flooding/entering a house or children are at risk, set urgency_level to 'critical' or 'high' even if the tone is calm.
Correct phonetic errors like 'Mayskalli' to 'Mysore'.

Transcript: "{transcript}"
Language Context: {lang_name}

Return ONLY JSON with these fields:
{{
  "intent": "Short summary of request",
  "issue_type": "water_supply, electricity, health, sanitation, or other",
  "location": "Extract city/area name",
  "duration": "How long has this been happening?",
  "impact": "low, medium, high",
  "language_detected": "kn, hi, or en",
  "dialect_notes": "Note any phonetic oddities here",
  "normalized_text": "The full corrected text in standard script",
  "emotion": {{
    "primary": "neutral, anger, distress, fear, or frustration",
    "urgency_level": "low, medium, high, or critical",
    "distress_indicators": ["list", "any", "urgent", "words"]
  }},
  "confirmation_sentence": "A polite 1-sentence confirmation of understanding in {lang_name}"
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            
            text = response.text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"): text = text[4:].strip()
            
            return json.loads(text)
        
        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            status = "Quota Exceeded" if "429" in str(e) else "API Error"
            return self._fallback(transcript, status)

    def _fallback(self, transcript: str, error_status: str) -> dict:
        return {
            "intent": error_status,
            "issue_type": "other",
            "duration": "not_specified",
            "location": "not_specified",
            "impact": "medium",
            "language_detected": "unknown",
            "dialect_notes": "System Error",
            "normalized_text": transcript,
            "emotion": {"primary": "neutral", "urgency_level": "medium", "distress_indicators": []},
            "confirmation_sentence": f"Status: {error_status}. Original: {transcript}",
        }

    async def regenerate_confirmation(self, structured_data: dict, language: str) -> str:
        """Regenerate a confirmation sentence after manual edits."""
        prompt = f"""Based on this structured info, write a polite 1-sentence confirmation 
        in {language} for a citizen helpline. 
        Info: {json.dumps(structured_data)}
        Return ONLY the sentence."""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Regeneration Error: {e}")
            return "Understanding updated."
