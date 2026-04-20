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
