# SpeakPractice

AI-powered English speaking practice app. See [Claude.md](Claude.md) for the full spec.

## Run frontend and backend locally with Docker

Docker Compose starts the frontend and backend containers, and the backend uses
the PostgreSQL instance already installed on your computer. The first backend
build is sizeable because it installs the local speech-model dependencies;
model downloads are then retained in a Docker volume.

```bash
cp .env.example .env
# edit .env and set GROQ_API_KEY
# ensure your local PostgreSQL has a speakpractice database
docker compose up --build
```

Open http://localhost:5173. The API is available at http://localhost:8000;
the backend reaches your computer's PostgreSQL at `host.docker.internal:5432`.
If your database credentials, port, or database name differ from the sample
settings, update `DATABASE_URL` in `.env`.

To apply source changes, rebuild the affected image with `docker compose up
--build`. This default setup avoids Docker Desktop bind-mount issues when the
project is stored under `/run/media`. To stop the stack, use `docker compose
down`; your local database is untouched. Downloaded Whisper models are retained
in a Docker volume. To remove the model volume too, use `docker compose down -v`.

## Deploy with Docker

Use the production Compose file for deployment. It builds static frontend files
served by Nginx and runs the backend without source mounts or auto-reload. It
does not use the local-development database address: provide a database that is
reachable from the deployment host instead.

```bash
cp .env.production.example .env.production
cp backend/.env.example backend/.env
# set GROQ_API_KEY in backend/.env and real values in .env.production
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
```

`VITE_API_BASE_URL` and `VITE_WS_BASE_URL` must be the public HTTP and WebSocket
URLs of the backend; the frontend embeds these values while it is built. Put a
TLS reverse proxy or your cloud load balancer in front of ports 80 and 8000 for
an HTTPS deployment, and use `https://` / `wss://` URLs in `.env.production`.

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
