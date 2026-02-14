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
  - `POST /dev/users`
  - `GET /dev/users`
  - `POST /dev/mood_checkins`
  - `GET /dev/mood_checkins?user_id=...`

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

Create a user:
```bash
curl -X POST http://localhost:8000/dev/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Alex Carter","email":"alex@example.com","lat":38.8895,"lng":-77.0353}'
```

List users:
```bash
curl http://localhost:8000/dev/users
```

Create mood check-in (replace `<USER_ID>`):
```bash
curl -X POST http://localhost:8000/dev/mood_checkins \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<USER_ID>","mood_score":4,"note":"Tough day"}'
```

List mood check-ins for a user:
```bash
curl "http://localhost:8000/dev/mood_checkins?user_id=<USER_ID>"
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
