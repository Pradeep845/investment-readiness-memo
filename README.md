# Investment Readiness Memo

Investment Readiness Memo is a hackathon MVP that drafts a structured, evidence-backed view of whether a company looks ready for serious investment consideration, using Anakin as the data layer.

## What it does

- Discovers important company pages using Anakin Map
- Scrapes website content using Anakin URL Scraper (batch)
- Pulls external research signals using Anakin Agentic Search
- Adds an optional stock trend snapshot (Yahoo chart API)
- Produces an explainable readiness memo:
  - score (0-100)
  - risk flags
  - growth catalysts
  - evidence links

## Project structure

- `frontend/` - React (Vite) UI
- `backend/` - FastAPI API and scoring engine

## Prerequisites

- Node.js 18+ (tested with latest LTS)
- Python 3.12+
- Anakin API key

## Environment setup

1. Copy root env template:

```bash
cp .env.example .env
```

2. Copy service env files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

3. Fill `ANAKIN_API_KEY` in `backend/.env`.

## Run backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend defaults to `http://localhost:5173` and calls backend at `http://localhost:8000`.

## API endpoint

- `GET /health` - health check
- `POST /analyze` - runs full investability analysis

Sample payload:

```json
{
  "company_name": "NVIDIA",
  "website_url": "https://www.nvidia.com",
  "ticker": "NVDA"
}
```

## Notes for demo

- If Anakin jobs are slow, keep the loading state visible and retry.
- If ticker is not provided, stock module is omitted.
- Wire integration is intentionally optional for the MVP timeline.
