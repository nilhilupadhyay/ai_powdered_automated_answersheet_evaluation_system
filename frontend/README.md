# Frontend

Minimal Next.js teacher dashboard scaffold.

## Run locally

```bash
npm install
npm run dev
```

## Environment

Create `.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Current page

- `/` Teacher Analytics Dashboard
  - fetch student report by `exam_id + roll_number`
  - fetch exam class report by `exam_id`
  - render leaderboard and question averages
- `/manual-review` Manual review queue
  - load submissions needing review
  - correct roll number and verify submission
