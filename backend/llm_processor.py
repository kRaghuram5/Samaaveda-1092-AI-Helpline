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
        self.model_id = "gemini-1.5-flash"
        
        try:
            # Get available models
            available = []
            for m in self.client.models.list():
                name = m.name.split('/')[-1]
                available.append(name)
            
            logger.info(f"Available models: {available}")
            
            # Use gemini-1.5-flash (most stable)
            if "gemini-1.5-flash" in available:
                self.model_id = "gemini-1.5-flash"
            elif available:
                self.model_id = available[0]
                
        except Exception as e:
            logger.error(f"Model detection error: {e}")
        
        logger.info(f"Using model: {self.model_id}")

    
    async def process_transcript(self, transcript: str, language: str = "en") -> dict:
        """Simple API call with better prompt to extract all details."""
        
        logger.info(f"process_transcript called with language={language}, transcript length={len(transcript)}")
        
        prompt = f"""Analyze this citizen complaint carefully:
"{transcript}"

Extract:
1. Intent: What is the main issue?
2. Issue Type: water_supply|electricity|health|sanitation|other
3. Location: Where exactly?
4. Duration: How long has this been happening? (Look for time words: hours, days, weeks, since)
5. Urgency Level: 
   - LOW: Minor inconvenience
   - MEDIUM: Affects daily life, some risk
   - HIGH: Serious problem, health/safety risk, mentions "urgent/critical"
   - CRITICAL: Immediate danger, flooding, fire, children at risk
6. Emotion: Based on tone - neutral, concern, frustration, distress, fear, anger
7. Impact: low|medium|high (based on scope and harm)

Return ONLY VALID JSON (no markdown, no extra text):
{{
  "intent": "One line summary",
  "issue_type": "category",
  "location": "specific place",
  "duration": "Extract time (e.g., '12 hours', '3 days', 'ongoing')",
  "urgency_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "emotion": "neutral|concern|frustration|distress|fear|anger",
  "impact": "low|medium|high",
  "confirmation_sentence": "1-2 sentence confirmation of the issue"
}}"""
        
        # Retry logic only for 503 (service unavailable)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"API Call attempt {attempt + 1}, model: {self.model_id}")
                
                # Direct API call with error handling
                try:
                    logger.info("Calling client.models.generate_content...")
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model_id,
                        contents=prompt
                    )
                    logger.info(f"API Response received: {type(response)}")
                except Exception as api_error:
                    logger.error(f"API call failed: {api_error}")
                    raise api_error
                
                # Extract text from response
                try:
                    logger.info(f"Response object type: {type(response)}, dir: {[x for x in dir(response) if not x.startswith('_')][:5]}")
                    
                    if isinstance(response, str):
                        text = response.strip()
                        logger.info("Response is string")
                    elif hasattr(response, 'text'):
                        text = response.text.strip()
                        logger.info("Response has .text attribute")
                    else:
                        text = str(response).strip()
                        logger.info("Converting response to string")
                    
                    logger.info(f"Extracted text ({len(text)} chars): {text[:200]}...")
                except Exception as extract_error:
                    logger.error(f"Failed to extract text from response: {extract_error}")
                    raise extract_error
                
                # Clean JSON if wrapped in markdown
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:].strip()
                
                logger.info(f"Cleaned JSON: {text[:200]}...")
                
                # Parse JSON
                try:
                    result = json.loads(text)
                    logger.info(f"LLM Parsed JSON: {result}")
                except json.JSONDecodeError as je:
                    logger.error(f"JSON Parse Error: {je}. Text was: {text[:300]}")
                    # Return structured fallback if JSON fails
                    return {
                        "intent": transcript[:100],
                        "issue_type": "other",
                        "location": "not_specified",
                        "duration": "not_specified",
                        "urgency_level": "medium",
                        "emotion": "neutral",
                        "impact": "medium",
                        "confirmation_sentence": transcript
                    }
                
                # Ensure all fields exist
                required_fields = {
                    "intent": "Issue reported",
                    "issue_type": "other",
                    "location": "not_specified",
                    "duration": "not_specified",
                    "urgency_level": "medium",
                    "emotion": "neutral",
                    "impact": "medium",
                    "confirmation_sentence": "Thank you for reporting."
                }
                
                for field, default in required_fields.items():
                    if field not in result or not result[field]:
                        logger.warning(f"Missing field '{field}', using default: {default}")
                        result[field] = default
                
                logger.info(f"Final Result: {result}")
                return result
                
            except Exception as e:
                error_str = str(e)
                logger.error(f"Process Error: {error_str}")
                
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
        logger.warning(f"[Fallback Mode] API failed ({error}). Returning mock data.")
        return {
            "intent": "Water/Sanitation Issue Reported",
            "issue_type": "sanitation",
            "location": "Demo Location",
            "duration": "12 hours",
            "impact": "high",
            "urgency_level": "HIGH",
            "emotion": "concern",
            "confirmation_sentence": "Issue with water/sanitation has been reported. Our team will assist shortly.",
            "_is_fallback": True
        }

    async def regenerate_confirmation(self, structured_data: dict, language: str) -> str:
        """Return confirmation without API call - just use the existing one."""
        # Don't make API call - use the confirmation_sentence from structured data
        if 'confirmation_sentence' in structured_data:
            return structured_data['confirmation_sentence']
        return "Understood. Thank you for reporting."
