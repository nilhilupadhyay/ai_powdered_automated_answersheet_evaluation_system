# Backend

FastAPI backend for the answer sheet evaluation system.

## Run locally

```bash
pip install -e .[dev]
uvicorn app.main:app --reload
```

## Implemented endpoints

- `GET /health`
- `POST /api/v1/sheets/generate`
- `POST /api/v1/capture/upload`
- `POST /api/v1/capture/{submission_id}/process`
- `GET /api/v1/capture/manual-review`
- `POST /api/v1/capture/{submission_id}/manual-review/verify`
- `POST /api/v1/grading/{submission_id}/exact`
- `POST /api/v1/grading/{submission_id}/llm`
- `GET /api/v1/grading/{submission_id}`
- `GET /api/v1/grading/report/student?exam_id=<id>&roll_number=<roll>`
- `GET /api/v1/grading/report/exam?exam_id=<id>`

## Notes

- Uses SQLAlchemy with SQLite by default (`app.db`).
- Uploaded sheet images are stored in `backend/uploads`.
- QR decode uses OpenCV `QRCodeDetector`.
- OCR is provider-based in `app/services/capture_pipeline.py`:
  - `ocr_provider=local` (default fallback)
  - `ocr_provider=google_vision` (requires `google_vision_api_key`)
- Submissions with low confidence or missing QR/roll number move to `needs_manual_review`.
- Teacher verification endpoint records reviewer audit metadata in `submission_reviews`.
- Grading only runs for `verified` submissions.
- LLM grading supports:
  - `llm_provider=claude` with `ANTHROPIC_API_KEY`
  - `llm_provider=gemini` with `GEMINI_API_KEY`
- If provider credentials are missing or API call fails, grading falls back to a liberality-aware similarity heuristic.
- Each grade stores audit metadata: `llm_provider`, `llm_model`, `prompt_version`, `llm_response_id`, and `llm_fallback_used`.
