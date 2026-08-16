# SpeakPractice

AI-powered English speaking practice app. See [Claude.md](Claude.md) for the full spec.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) (manages Python itself — no separate Python install needed)
- Node.js + npm
- A running local PostgreSQL instance with a database already created
- A [Groq API key](https://console.groq.com/keys)

## Backend setup

```bash
cd backend
cp .env.example .env
# edit .env: set GROQ_API_KEY and DATABASE_URL (postgresql+psycopg://user:password@host:port/dbname)

uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Tables are created automatically on startup. Verify with:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/session/start -H "Content-Type: application/json" -d '{"topic":"travel"}'
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The frontend expects the backend at `http://localhost:8000` / `ws://localhost:8000` by default (see `frontend/.env.example` to override via `VITE_API_BASE_URL` / `VITE_WS_BASE_URL`).

## Notes

- STT (`faster-whisper`) and VAD (`silero-vad`) download their models on first use — the first session will be slower while that happens.
- The mic capture hook (`useMicRecorder`) streams raw PCM16 mono 16kHz audio, matching the backend's VAD window size (512 samples/32ms) — this is a fixed wire protocol between frontend and backend, not just a default.
