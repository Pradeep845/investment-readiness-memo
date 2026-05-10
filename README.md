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

From the `backend` folder:

```powershell
cd backend
python -m venv .venv
```

Install and start the API **without** activating the venv (works even when PowerShell blocks `Activate.ps1`):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### Windows troubleshooting

**1. `Activate.ps1` cannot be loaded (execution policy)**  
You do **not** need activation if you use `.\.venv\Scripts\python.exe` as above.

Optional fix so `Activate.ps1` works in PowerShell (current user only):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Alternative: open **Command Prompt** (`cmd.exe`) and use the batch activator:

```cmd
cd backend
.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**2. `python` opens the Microsoft Store or “Python was not found”**  
Windows “App execution aliases” can hijack `python`. Either:

- Settings → Apps → Advanced app settings → App execution aliases → turn **off** aliases for `python.exe` and `python3.exe`, then reopen the terminal, or  
- Call the real interpreter by full path (example, adjust version if yours differs):

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" -m venv .venv
```

**3. Prefer Python 3.12 for parity with the original dev setup**  
If you use **Python 3.14**, dependencies should still install; if anything fails, install [Python 3.12](https://www.python.org/downloads/) and recreate the venv with that binary.

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend defaults to `http://localhost:5173` and calls backend at `http://localhost:8000`.

## API endpoint

- `GET /health` - health check
- `POST /analyze` - runs full readiness memo analysis

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
