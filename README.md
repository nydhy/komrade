# komrade

Local-first prototype with:
- `backend/` FastAPI API
- `frontend/` Vite + React app (main UI currently used)
- `apps/web/` Next.js scaffold (secondary/legacy in this repo)

## What Is Implemented

### Backend (`backend/`)
- JWT auth:
  - `POST /auth/register`
  - `POST /auth/login`
  - `GET /auth/me`
  - `PUT /auth/me`
- Buddy workflows:
  - invite/accept/block/list buddies
- Mood check-ins:
  - create + list current user check-ins
- Presence/location:
  - update presence
  - update location
  - nearby buddies lookup
- SOS workflows + realtime support endpoints
- User settings + reporting endpoints
- AI provider abstraction:
  - Gemini + Ollama behind one structured API service
  - Internal provider selection via `AI_PROVIDER` (`gemini` or `ollama`)
- Translation Layer:
  - `POST /translate`
  - `GET /translate/history`
  - stores history in MongoDB (`komrade.translations`)
- Voice input (Phase 4):
  - `POST /stt/elevenlabs` multipart audio (`webm`/`wav`)
  - validates type/size and calls ElevenLabs STT
- AI structured test route:
  - `POST /ai/test-structured`
- Health:
  - `GET /health`

### Frontend (`frontend/`)
- Auth pages and protected app shell
- Dashboard, buddies, map, SOS history, profile, settings
- Chat page (`/translate`) labeled as **Chat**
- Chat response mode focused on empathetic personalized answer
- History panel with user label + `komradeAI` response
- Optional microphone recording:
  - record audio in browser
  - upload to `/stt/elevenlabs`
  - transcript auto-fills chat input
- Branding updates:
  - custom logo support via `frontend/public/komrade_logo.png`
  - favicon set to `komrade_logo.png`

## Repo Structure

```text
backend/      # FastAPI app (active backend)
frontend/     # Vite React app (active frontend)
apps/
  api/        # older API scaffold
  web/        # Next.js scaffold
```

## Backend Setup

```bash
cd backend
cp .env.example .env
```

Create/activate venv and install deps:

```bash
python3 -m venv ../env
source ../env/bin/activate
pip install -r requirements.txt
```

Run migrations and start API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URL: `http://localhost:8000`

## Backend Env Variables

`backend/.env`:
- `APP_NAME`
- `DEBUG`
- `DATABASE_URL`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `JWT_EXPIRE_MINUTES`
- `GEMINI_API_KEY`
- `GEMINI_MODEL` (default `gemini-1.5-flash`)
- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `OLLAMA_MODEL` (default `llama3.1`)
- `AI_PROVIDER` (`gemini` or `ollama`)
- `MONGO_URI` (default `mongodb://localhost:27017`)
- `ELEVENLABS_API_KEY` (required for `/stt/elevenlabs`)

## Frontend Setup (Vite React)

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173`

Notes:
- Vite proxies API routes to `http://localhost:8000` in `frontend/vite.config.ts`.
- If you change proxy settings, restart the frontend dev server.

## Quick API Checks

Health:
```bash
curl http://localhost:8000/health
```

STT (authenticated, sample):
```bash
curl -X POST http://localhost:8000/stt/elevenlabs \
  -H "Authorization: Bearer <TOKEN>" \
  -F "audio=@/path/to/sample.webm;type=audio/webm"
```

Translate:
```bash
curl -X POST http://localhost:8000/translate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message":"I am overwhelmed today"}'
```

## Tests

Backend:
```bash
cd backend
../env/bin/pytest -q
```

Frontend:
```bash
cd frontend
npm test -- --run
```
