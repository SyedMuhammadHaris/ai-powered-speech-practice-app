# CLAUDE.md

This file provides guidance to Claude Code when working on this repository.

## Project Overview

**SpeakPractice** — an AI-powered English speaking practice app. The user picks a topic (or a preset), speaks into their mic, and has a real-time voice conversation with an AI partner that keeps the discussion on-topic, asks follow-up questions, and gently corrects grammar/vocabulary along the way. At the end of a session, it generates a short feedback report (mistakes, filler words, vocabulary suggestions).

Primary goal: give the user maximum speaking time and natural back-and-forth, not a quiz format.

## Tech Stack

- **Backend**: FastAPI (Python 3.11+), WebSockets for real-time audio/text streaming
- **STT**: faster-whisper (local, free) — `small` or `base` model
- **LLM**: Groq API (cloud, requires `GROQ_API_KEY`) — `llama-3.3-70b-versatile` via Groq's OpenAI-compatible `/chat/completions` endpoint; conversation logic driven entirely by system prompt
- **TTS**: edge-tts (free, no API key, natural voices, multiple English accents)
- **VAD**: silero-vad — detect when user stops talking (no push-to-talk)
- **DB**: PostgreSQL via SQLAlchemy (`psycopg` v3 driver) — used for local dev too since it's already installed
- **Frontend**: React + Web Audio API / MediaRecorder, WebSocket client
- **Auth**: keep minimal for v1 (single-user/local), can add later

## Architecture

```
Browser (mic capture, WebSocket client, audio playback)
   │  audio chunks (WebSocket)
   ▼
FastAPI WebSocket endpoint
   │
   ├─► silero-vad → detects end of user turn
   ├─► faster-whisper → transcribes user audio to text
   ├─► Groq API (cloud LLM) → generates next conversational reply
   │       (system prompt = topic + difficulty + tutor persona rules)
   ├─► edge-tts → synthesizes reply audio
   ▼
Stream synthesized audio back to browser over WebSocket
```

Session state (topic, difficulty, full message history) is kept server-side per session and passed to Claude on each turn so it has full context.

## Data Model (minimal v1)

- `Session`: id, topic, difficulty, created_at, ended_at
- `Message`: id, session_id, role (user/assistant), text, timestamp
- `SessionFeedback`: session_id, summary_text, common_mistakes (json), vocab_suggestions (json)

## Progression System (auto difficulty advancement)

Difficulty is not manually picked each time — it's driven by how long the user has been practicing:

- **Week 1**: Beginner
- **Weeks 2–3**: Intermediate
- **Weeks 4–5**: Advanced
- **Week 6+**: stay Advanced (or add a "review/mixed" mode later)

Implementation approach:
- `User` (or a simple `Profile` table for v1 single-user) stores `program_start_date`
- On each `/session/start` call, compute `current_week = (today - program_start_date).days // 7 + 1`
- Map `current_week` → difficulty via a simple lookup function, e.g.:
  ```python
  def get_difficulty(week: int) -> str:
      if week == 1:
          return "beginner"
      elif week in (2, 3):
          return "intermediate"
      else:
          return "advanced"
  ```
- Difficulty is auto-injected into the session (no dropdown needed for v1), but still store it on the `Session` row for tracking/analytics
- Allow an optional manual override param (e.g. `?override_difficulty=intermediate`) for testing/flexibility, but auto mode is the default behavior

### Data Model Addition
- `Profile`: id, program_start_date, current_streak (optional), created_at

## Frontend (React)

Single-page app, no need for routing complexity in v1 — a few views/states is enough.

**Views/States:**
1. **Home / Start screen** — topic input (preset buttons + custom text field), "Start Session" button. Difficulty is shown (read-only, auto-computed) so the user knows what level they're on.
2. **Conversation screen** — mic button (hold-to-talk or tap-to-toggle, your call), live transcript of both sides scrolling up, AI audio auto-plays when it arrives, simple "speaking..." / "listening..." status indicator.
3. **Feedback screen** — shown after "End Session": summary text, list of mistakes, vocabulary suggestions, "Start New Session" button.

**Key frontend responsibilities:**
- Capture mic audio via `MediaRecorder` / Web Audio API, chunk it, send over WebSocket to `/session/{id}/talk`
- Receive streamed text (live transcript) + audio (AI reply) over the same WebSocket, play audio back
- Handle WebSocket connection lifecycle (connect on session start, reconnect logic if dropped, close on session end)
- Basic loading/error states (mic permission denied, WebSocket disconnected, Groq API not responding)

**Suggested structure:**
```
frontend/
  src/
    components/
      TopicSelector.jsx
      ConversationView.jsx
      FeedbackReport.jsx
      MicButton.jsx
    hooks/
      useWebSocketSession.js   // handles WS connect/send/receive
      useMicRecorder.js        // handles MediaRecorder + audio chunking
    App.jsx
```

Keep it plain React (Vite for dev server — fast, free, minimal config) — no need for Next.js here since there's no SSR/routing requirement for a single-page tool like this.

## Key Endpoints (planned)

- `POST /session/start` — body: `{topic}` (difficulty auto-computed from `program_start_date`, optional `override_difficulty` param) → creates session, returns session_id + difficulty used + AI's opening line (+ opening audio)
- `WS /session/{id}/talk` — bidirectional: client streams audio in, server streams transcript + AI audio reply out
- `POST /session/{id}/end` — closes session, triggers feedback generation
- `GET /session/{id}/feedback` — returns feedback report

## System Prompt Rules (conversation persona)

- Stay on the given topic but flow naturally, not like a quiz
- Ask follow-up questions to maximize user speaking time
- Keep AI responses short (2-4 sentences)
- Correct mistakes gently and inline, without breaking conversational flow
- Adapt vocabulary/complexity to the selected difficulty level (beginner/intermediate/advanced)
- Steer back gently if user goes off-topic for too long

## Development Conventions

- Use Python type hints everywhere; Pydantic models for all request/response schemas
- Keep STT/LLM/TTS calls in separate service modules (`services/stt.py`, `services/llm.py`, `services/tts.py`) — not inline in route handlers. `services/llm.py` should wrap Groq's OpenAI-compatible `/chat/completions` endpoint via raw HTTP calls (`httpx`) to `GROQ_BASE_URL`, authenticated with `GROQ_API_KEY`
- WebSocket handler should be thin: delegate to services, handle only connection/streaming logic
- Async/await throughout — avoid blocking calls in the event loop (run faster-whisper in a thread pool executor since it isn't natively async; edge-tts and the Groq HTTP calls are natively async)
- Environment variables for config (`.env`, never commit secrets) — e.g. `GROQ_API_KEY` (required, no default), `GROQ_BASE_URL` (default `https://api.groq.com/openai/v1`), `GROQ_MODEL` (default `llama-3.3-70b-versatile`)
- Write docstrings for service functions since this is a learning-oriented side project

## Out of Scope for v1

- Multi-user auth/accounts (add later if needed)
- Payment/subscription logic
- Mobile app (web only for now)
- Multiple simultaneous languages (English only for v1)

## Current Status

Backend scaffolded on FastAPI + uv (Python 3.12): DB models, difficulty logic, `/session/start`, the `/session/{id}/talk` WebSocket, `/session/{id}/end`, and `/session/{id}/feedback` are all wired to real services (faster-whisper STT, Groq LLM, edge-tts TTS, silero-vad). LLM provider is Groq (cloud), not Ollama — requires `GROQ_API_KEY` in `backend/.env`. DB is PostgreSQL (local instance) — requires `DATABASE_URL` in `backend/.env` pointing at an existing database. Frontend not yet scaffolded.