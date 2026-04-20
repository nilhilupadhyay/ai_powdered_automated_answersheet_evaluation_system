# Architecture Notes (MVP)

## Modules

1. Sheet generation service
2. Capture and OCR pipeline
3. Grading engine (exact + LLM mode)
4. Teacher/student dashboards

## Current Implementation

- Implemented module 1 initial API:
  - `POST /api/v1/sheets/generate`
- Output includes:
  - QR payload string
  - Base64 encoded PDF containing answer template and embedded QR

## Next Build Slice

1. Persist sheet sessions in PostgreSQL
2. Add file upload endpoint for captured sheet images
3. Integrate OCR provider abstraction with confidence scores
4. Add manual verification queue for low-confidence roll numbers
