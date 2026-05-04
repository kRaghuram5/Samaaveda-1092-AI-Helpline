# 🎙️ Samaaveda — 1092 Helpline AI Voice Assistant

AI-assisted voice-to-voice prototype for multilingual citizen helpline conversations.

## Features

- **Real-time voice capture** via browser microphone
- **Multilingual STT** (Kannada, Hindi, English) using faster-whisper
- **Semantic extraction** via Google Gemini (intent, issue, location, impact)
- **Emotion & urgency detection** (hybrid keyword + LLM)
- **Verification loop** — citizen confirms AI understanding
- **Guardrails** — auto-escalation on low confidence or high distress
- **Agent dashboard** with editable AI suggestions
- **Feedback logging** for learning signals

## Quick Start

### 1. Prerequisites

- **Python 3.11+**
- **FFmpeg** installed and on PATH ([download](https://ffmpeg.org/download.html))
- **Google Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey)
- **A microphone** and **Chrome browser**

### 2. Setup

```bash
# Create and activate virtual environment
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure API key
copy .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### 3. Run

```bash
cd backend
python main.py
```

Open **http://localhost:8000** in Chrome.

### 4. Demo Flow

1. Select language (or leave on Auto)
2. Click the microphone to start speaking
3. Click again to stop — audio is processed
4. See live transcript + structured summary on Agent Dashboard
5. Verify understanding on Citizen Panel (Correct / Partial / Incorrect)
6. Agent can edit any field and confirm or escalate

## Architecture

```
Frontend (HTML/JS) ←→ WebSocket ←→ FastAPI Backend
                                      ├── Whisper STT
                                      ├── Gemini LLM
                                      ├── Emotion Detector
                                      ├── Verification Engine
                                      ├── Guardrails
                                      └── Feedback Store
```
