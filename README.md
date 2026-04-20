# Automated AI Powdered Evaluation System

Initial scaffold for an AI-powered answer sheet evaluation platform.

## Monorepo Layout

- `backend`: FastAPI service for sheet generation and evaluation pipeline APIs.
- `frontend`: Placeholder for Next.js teacher/student dashboards.
- `docs`: Architecture and planning notes.

## Current Status

This first slice includes:

- FastAPI app scaffold
- Health endpoint
- Sheet generation endpoint (`/api/v1/sheets/generate`)
- QR code creation and PDF rendering via HTML template

## Quick Start (Backend)

1. Create and activate a Python virtual environment.
2. Install dependencies:
   - `pip install -e .[dev]` (from `backend`)
3. Run:
   - `uvicorn app.main:app --reload`

API will start at `http://127.0.0.1:8000`.

## Deploy (Recommended)

### Backend (Railway)

1. Create a new Railway project from this GitHub repository.
2. Railway will use `railway.json` automatically.
3. Add environment variables:
   - `DATABASE_URL` (Postgres connection string)
   - `GEMINI_API_KEY`
   - `LLM_PROVIDER=gemini`
   - `LLM_MODEL=gemini-2.5-flash`
   - `CORS_ALLOW_ORIGINS=https://<your-vercel-domain>`
4. Deploy and confirm `GET /health` returns `{"status":"ok"}`.

### Frontend (Vercel)

1. Import this repository in Vercel.
2. Set Root Directory to `frontend`.
3. Add environment variable:
   - `NEXT_PUBLIC_API_BASE_URL=https://<your-railway-backend-domain>`
4. Deploy.

### Notes

- Avoid using SQLite in production; set `DATABASE_URL` to Postgres.
- `.env` files are ignored by git; keep API keys there locally or in provider secrets.
