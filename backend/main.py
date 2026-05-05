"""
Main FastAPI application — WebSocket server for the 1092 Helpline AI Assistant.
Serves the frontend and handles real-time audio processing.
"""
import asyncio
import json
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import GEMINI_API_KEY, SUPPORTED_LANGUAGES
from stt_engine import STTEngine
from llm_processor import LLMProcessor
from emotion_detector import EmotionDetector
from verification import VerificationEngine
from guardrails import Guardrails
from feedback_store import FeedbackStore

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("samaaveda")

# --- App ---
app = FastAPI(title="Samaaveda — 1092 Helpline AI Assistant")

# --- Singletons ---
stt = STTEngine.get_instance()
llm = LLMProcessor()
emotion_detector = EmotionDetector()
verifier = VerificationEngine()
guardrails = Guardrails()
feedback = FeedbackStore()

# --- Serve Frontend ---
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "gemini_configured": bool(GEMINI_API_KEY),
            "languages": SUPPORTED_LANGUAGES}


# --- Preload Whisper on startup ---
@app.on_event("startup")
async def startup():
    logger.info("Samaaveda backend starting...")
    logger.info("Whisper model will load on first transcription request.")
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set! LLM features will use fallbacks.")


# --- WebSocket handler ---
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = str(uuid.uuid4())[:8]
    logger.info(f"[{session_id}] WebSocket connected")

    # Session state
    audio_buffer = bytearray()
    language = "auto"
    recording = False
    processing_lock = asyncio.Lock()

    # Create verification session
    verifier.create_session(session_id)

    await _send(ws, "status", {"message": "Connected to Samaaveda AI", "session_id": session_id})

    try:
        while True:
            if ws.client_state.value == 2: # DISCONNECTED
                break
            message = await ws.receive()

            # --- Binary frame: audio chunk ---
            if "bytes" in message:
                if recording:
                    audio_buffer.extend(message["bytes"])
                    await _send(ws, "audio_received", {
                        "buffer_size": len(audio_buffer),
                    })
                continue

            # --- Text frame: JSON command ---
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    await _send(ws, "error", {"message": "Invalid JSON"})
                    continue

                msg_type = data.get("type", "")

                # -- Start recording --
                if msg_type == "start_session":
                    language = data.get("language", "auto")
                    logger.info(f"[{session_id}] Start session received. Language: {language}")
                    audio_buffer = bytearray()
                    recording = True
                    verifier.create_session(session_id)
                    await _send(ws, "status", {"message": f"Recording started — language: {language}",
                                               "state": "recording"})

                # -- Stop recording & process --
                elif msg_type == "stop_recording":
                    recording = False
                    if len(audio_buffer) < 1000:
                        await _send(ws, "error", {"message": "Audio too short"})
                        continue

                    await _send(ws, "status", {"message": "Processing audio...", "state": "processing"})

                    async with processing_lock:
                        await _process_audio(ws, session_id, bytes(audio_buffer), language)

                    audio_buffer = bytearray()

                # -- Citizen verification response --
                elif msg_type == "verification_response":
                    resp = data.get("response", "")
                    correction = data.get("correction", "")
                    result = verifier.process_citizen_response(session_id, resp, correction)
                    await _send(ws, "verification_result", result)

                    # If correction provided, re-process with correction context
                    if result.get("action") == "re_process" and correction:
                        session = verifier.get_session(session_id)
                        original = session.get("transcript", "")
                        combined = f"{original} [Citizen correction: {correction}]"
                        await _send(ws, "status", {"message": "Re-processing with correction...",
                                                   "state": "processing"})
                        await _run_llm_pipeline(ws, session_id, combined, language,
                                                stt_confidence=session.get("confidence", 0.5))

                    if result.get("action") == "escalate":
                        await _send(ws, "escalation_alert", {
                            "reason": "Verification failed after multiple attempts",
                            "level": "critical"})

                    # Log feedback
                    session_data = verifier.get_full_session_data(session_id)
                    if session_data:
                        feedback.log_session(session_id, session_data)

                # -- Agent edit --
                elif msg_type == "agent_edit":
                    field = data.get("field", "")
                    value = data.get("value", "")
                    old_data = dict(verifier.get_session(session_id).get("structured_data", {}))
                    success = verifier.agent_edit(session_id, field, value)
                    if success:
                        new_data = verifier.get_session(session_id)["structured_data"]
                        feedback.log_correction(session_id, old_data, new_data, "agent")
                        # Regenerate confirmation
                        confirmation = await llm.regenerate_confirmation(new_data, language)
                        new_data["confirmation_sentence"] = confirmation
                        await _send(ws, "structured_summary", {"data": new_data})
                        await _send(ws, "verification_prompt", {
                            "message": confirmation,
                            "summary_text": new_data.get("normalized_text", ""),
                        })

                # -- Agent confirm --
                elif msg_type == "agent_confirm":
                    result = verifier.agent_confirm(session_id)
                    await _send(ws, "agent_action_result", result)
                    session_data = verifier.get_full_session_data(session_id)
                    if session_data:
                        feedback.log_session(session_id, session_data)

                # -- Agent escalate --
                elif msg_type == "agent_escalate":
                    reason = data.get("reason", "Agent requested escalation")
                    result = verifier.agent_escalate(session_id, reason)
                    await _send(ws, "agent_action_result", result)
                    await _send(ws, "escalation_alert", {"reason": reason, "level": "critical"})
                    session_data = verifier.get_full_session_data(session_id)
                    if session_data:
                        feedback.log_session(session_id, session_data)

    except WebSocketDisconnect:
        logger.info(f"[{session_id}] WebSocket disconnected")
    except Exception as e:
        logger.error(f"[{session_id}] Error: {e}", exc_info=True)
        try:
            await _send(ws, "error", {"message": str(e)})
        except Exception:
            pass


async def _process_audio(ws: WebSocket, session_id: str, audio_bytes: bytes, language: str):
    """Full pipeline: STT → LLM → Emotion → Guardrails."""

    # 1. Speech-to-Text
    await _send(ws, "status", {"message": "Transcribing speech...", "state": "transcribing"})
    stt_result = await asyncio.to_thread(stt.transcribe, audio_bytes, language if language != "auto" else None)

    transcript = stt_result.get("text", "")
    stt_confidence = stt_result.get("confidence", 0.0)
    detected_lang = stt_result.get("language", "unknown")

    if not transcript:
        await _send(ws, "error", {"message": "Could not transcribe audio. Please try again."})
        return

    # Send transcript
    verifier.update_transcript(session_id, transcript)
    await _send(ws, "transcript_update", {
        "text": transcript,
        "language": detected_lang,
        "language_probability": stt_result.get("language_probability", 0),
        "confidence": stt_confidence,
        "duration": stt_result.get("duration", 0),
        "is_final": True,
    })

    # 2. LLM + Emotion pipeline
    await _run_llm_pipeline(ws, session_id, transcript, detected_lang, stt_confidence)


async def _run_llm_pipeline(ws: WebSocket, session_id: str, transcript: str,
                            language: str, stt_confidence: float):
    """LLM semantic extraction + emotion + guardrails."""

    # LLM processing
    await _send(ws, "status", {"message": "Analyzing meaning & emotion...", "state": "analyzing"})
    llm_result = await llm.process_transcript(transcript, language)

    # Store structured data
    verifier.update_structured_data(session_id, llm_result)
    await _send(ws, "structured_summary", {"data": llm_result})

    # Emotion scoring
    kw_analysis = emotion_detector.analyze_keywords(transcript)
    llm_emotion = llm_result.get("emotion", {})
    emotion_scores = emotion_detector.combine_scores(llm_emotion, kw_analysis, stt_confidence)

    verifier.update_emotion(session_id, emotion_scores)
    await _send(ws, "emotion", emotion_scores)

    # Guardrails check
    session = verifier.get_session(session_id)
    guard_result = guardrails.evaluate(
        emotion_scores, stt_confidence, session.get("state", "pending"))
    await _send(ws, "confidence_update", {
        "score": emotion_scores["overall_confidence"],
        "guard_level": guard_result["level"],
        "alerts": guard_result["alerts"],
    })

    if guard_result["should_escalate"]:
        await _send(ws, "escalation_alert", {
            "reason": "; ".join(guard_result["alerts"]),
            "level": "critical",
        })

    # Verification prompt
    confirmation = llm_result.get("confirmation_sentence", f"You said: {transcript}")
    await _send(ws, "verification_prompt", {
        "message": confirmation,
        "summary_text": llm_result.get("normalized_text", transcript),
    })

    await _send(ws, "status", {"message": "Ready for verification", "state": "awaiting_verification"})


async def _send(ws: WebSocket, msg_type: str, data: dict):
    """Send a typed JSON message over WebSocket."""
    try:
        await ws.send_json({"type": msg_type, **data})
    except Exception as e:
        logger.error(f"Send error: {e}")


# --- Run with uvicorn ---
if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
    except KeyboardInterrupt:
        logger.info("Samaaveda server stopped by user. Goodbye!")
