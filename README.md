# KOMRADE (Local MVP)

Phase 1 + Phase 2 scaffolding for a local-first web app where a Next.js frontend calls a FastAPI backend on `localhost` and the API persists data in local PostgreSQL.

## Repo Structure

```text
apps/
  api/   # FastAPI backend
  web/   # Next.js frontend (TypeScript + Tailwind + shadcn-style setup)
```

## Backend (FastAPI)

### What is implemented

- `GET /health` returns:
  ```json
  { "status": "ok" }
  ```
- CORS enabled for `http://localhost:3000`
- Settings loaded via `pydantic-settings` from `.env`
- SQLAlchemy 2.0 models + Alembic migrations for:
  - `users`
  - `mood_checkins`
  - `buddy_links`
  - `alerts`
  - `ladder_plans`
  - `ladder_challenges`
  - `checkins`
- Dev endpoints (no auth):
- Auth endpoints:
  - `POST /auth/register`
  - `POST /auth/login`
- AI endpoints (protected):
  - `POST /ai/ladder`
  - `POST /ai/translate`
- Ladder endpoints (protected):
  - `POST /ladder/plans`
  - `GET /ladder/plans/latest`
  - `POST /ladder/challenges/{id}/complete`
- Dev endpoints:
  - `POST /dev/users`
  - `GET /dev/users`
  - `POST /dev/mood_checkins`
  - `GET /dev/mood_checkins?user_id=...`
  - `POST /dev/seed` (public for demo seeding)

### Run locally

1. Create env file:
   ```bash
   cd apps/api
   cp .env.example .env
   ```
2. Create and activate Python virtual environment (Python 3.11+):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Apply the included initial migration:
   ```bash
   alembic upgrade head
   ```
5. (For future schema changes) generate a new migration:
   ```bash
   alembic revision --autogenerate -m "describe your change"
   ```
6. Run backend:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

Backend URL: `http://localhost:8000`  
Health check: `http://localhost:8000/health`

### Dev endpoint verification (`curl`)

Register:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"OwnerPass123!","name":"Owner"}'
```

Login (save token):
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"OwnerPass123!"}' | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')
```

AI ladder (requires `GEMINI_API_KEY` in `.env`):
```bash
curl -X POST http://localhost:8000/ai/ladder \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"intake":{"social_comfort":"low","goals":["meet people","attend community event"],"constraints":"evenings only"}}'
```

AI translate:
```bash
curl -X POST http://localhost:8000/ai/translate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"I feel like ending my life","context":{"recent_stress":"job transition"}}'
```

### Local model option (Ollama)

If Gemini quota blocks requests, switch to local inference:

1. Install Ollama (macOS):
```bash
brew install ollama
```

2. Start Ollama server:
```bash
ollama serve
```

3. Pull a model (new terminal):
```bash
ollama pull llama3.1:8b
```

4. Update `apps/api/.env`:
```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1:8b
```

5. Restart API:
```bash
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Seed demo users (public):
```bash
curl -X POST http://localhost:8000/dev/seed
```

Create a user:
```bash
curl -X POST http://localhost:8000/dev/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Alex Carter","email":"alex@example.com","lat":38.8895,"lng":-77.0353}'
```

List users:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/dev/users
```

Create mood check-in (replace `<USER_ID>`):
```bash
curl -X POST http://localhost:8000/dev/mood_checkins \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<USER_ID>","mood_score":4,"note":"Tough day"}'
```

List mood check-ins for a user:
```bash
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/dev/mood_checkins?user_id=<USER_ID>"
```

## Frontend (Next.js)

### What is implemented

- `apps/web` Next.js TypeScript app
- Tailwind CSS configured
- Minimal shadcn-compatible setup (`cn` util + `Button` component)
- Home page button that calls backend `/health` and shows status

### Run locally

1. Create env file:
   ```bash
   cd apps/web
   cp .env.example .env.local
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run frontend:
   ```bash
   npm run dev
   ```

Frontend URL: `http://localhost:3000`

## Phase 5 UI

- Open `http://localhost:3000/ladder`
- Paste JWT token from `/auth/login`
- Fill intake form and click `Generate Ladder`
- Click `Save Plan`
- Mark weekly challenges as `Complete`
- XP and streak are computed client-side from completion state
