"""
LLM Processor - Simplified version for basic API calls.
"""
import json
import logging
import asyncio
from google import genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)


class LLMProcessor:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        # Default to most stable and cost-effective model
        self.model_id = "gemini-1.5-flash"
        
        try:
            # Optionally check if gemini-1.5-flash is indeed available
            available = [m.name.split('/')[-1] for m in self.client.models.list()]
            logger.info(f"Connected to Gemini API. Available: {available[:5]}...")
            
            if "gemini-1.5-flash" not in available and available:
                self.model_id = available[0]
                logger.warning(f"gemini-1.5-flash not found. Using fallback: {self.model_id}")
                
        except Exception as e:
            logger.error(f"Model verification failed: {e}. Using default: {self.model_id}")
        
        logger.info(f"LLM Engine ready. Model: {self.model_id}")


    
    async def process_transcript(self, transcript: str, language: str = "en") -> dict:
        """Simple direct API call with basic retry for 503 errors."""
        
        # Basic simple prompt
        prompt = f"""Analyze this request:
"{transcript}"

Return JSON:
{{
  "intent": "Summary",
  "issue_type": "water_supply|electricity|health|sanitation|other",
  "location": "City/area",
  "impact": "low|medium|high",
  "urgency_level": "low|medium|high|critical",
  "confirmation_sentence": "Simple confirmation"
}}"""
        
        # Retry logic only for 503 (service unavailable)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # Direct API call
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_id,
                    contents=prompt
                )
                
                text = response.text.strip()
                
                # Clean JSON if wrapped in markdown
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:].strip()
                
                result = json.loads(text)
                return result
                
            except Exception as e:
                error_str = str(e)
                
                # Retry on 503 (service unavailable)
                if "503" in error_str and attempt < max_retries:
                    delay = 3 * (attempt + 1)  # 3s, 6s
                    logger.warning(f"Service temporarily unavailable (503). Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                
                # Any other error - return fallback
                logger.error(f"API Error: {e}")
                return self._fallback(transcript, str(e))


    def _fallback(self, transcript: str, error: str) -> dict:
        """Return fallback response on error."""
        return {
            "intent": f"Error: {error}",
            "issue_type": "other",
            "location": "not_specified",
            "impact": "medium",
            "urgency_level": "medium",
            "confirmation_sentence": transcript
        }

    async def regenerate_confirmation(self, structured_data: dict, language: str) -> str:
        """Simple regeneration without retry."""
        prompt = f"Write 1 sentence confirmation for: {json.dumps(structured_data)}"
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_id,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Regeneration error: {e}")
            return "Updated."
