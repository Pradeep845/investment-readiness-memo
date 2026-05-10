import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.anakin_client import AnakinClient
from app.services.scoring import build_investability_report
from app.services.stock_client import fetch_stock_trend

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    if not settings.anakin_api_key:
        raise HTTPException(status_code=500, detail="ANAKIN_API_KEY is missing in backend environment")

    client = AnakinClient()
    diagnostics: dict = {}

    try:
        urls = await client.discover_urls(str(payload.website_url))
        diagnostics["discovered_url_count"] = len(urls)
    except Exception as exc:
        urls = [str(payload.website_url)]
        diagnostics["map_error"] = str(exc)

    try:
        scrape_payload, research_payload = await asyncio.gather(
            client.scrape_urls(urls),
            client.agentic_search(payload.company_name, str(payload.website_url)),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Anakin data: {exc}") from exc

    stock_signal = None
    if payload.ticker:
        try:
            stock_signal = await fetch_stock_trend(payload.ticker)
            diagnostics["stock_available"] = bool(stock_signal)
        except Exception as exc:
            diagnostics["stock_error"] = str(exc)

    report = build_investability_report(
        company_name=payload.company_name,
        website_url=str(payload.website_url),
        scrape_payload=scrape_payload,
        research_payload=research_payload,
        stock_signal=stock_signal,
    )
    report["diagnostics"] = diagnostics

    return AnalyzeResponse(**report)
