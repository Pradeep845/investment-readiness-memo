import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.anakin_client import AnakinClient
from app.services.gemini_polish import polish_memo
from app.services.holocron_wire import run_wire_signals
from app.services.scoring import build_investability_report
from app.services.stock_client import fetch_stock_trend

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    level_name = (settings.log_level or "info").upper()
    level = getattr(logging, level_name, logging.INFO)
    for name in (
        "app",
        "app.services",
        "app.services.anakin_client",
        "app.services.holocron_wire",
        "app.services.gemini_polish",
        "app.services.stock_client",
    ):
        logging.getLogger(name).setLevel(level)
    logger.info("logging_configured level=%s", level_name)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

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

    t0 = time.perf_counter()
    logger.info(
        "analyze_start company=%r website=%r ticker=%r",
        payload.company_name,
        str(payload.website_url),
        payload.ticker,
    )

    client = AnakinClient()
    diagnostics: dict = {}
    timings: dict[str, float] = {}
    stages: dict[str, dict[str, Any]] = {
        "map": {"status": "skipped"},
        "scrape": {"status": "skipped"},
        "agentic": {"status": "skipped"},
        "holocron": {"status": "skipped"},
        "stock": {"status": "skipped"},
        "gemini": {"status": "skipped"},
    }

    total_deadline = max(30, settings.analyze_total_deadline_seconds)
    map_budget = max(10, min(settings.analyze_map_deadline_seconds, total_deadline - 20))

    t_map = time.perf_counter()
    try:
        urls = await asyncio.wait_for(
            client.discover_urls(str(payload.website_url)),
            timeout=map_budget,
        )
        diagnostics["discovered_url_count"] = len(urls)
        stages["map"] = {"status": "ok", "urls_found": len(urls)}
        logger.info(
            "map_done url_count=%d elapsed_s=%.2f sample_urls=%s",
            len(urls),
            time.perf_counter() - t0,
            urls[:3],
        )
    except asyncio.TimeoutError:
        urls = [str(payload.website_url)]
        diagnostics["map_error"] = f"map_timeout_after_{map_budget}s"
        stages["map"] = {"status": "timeout", "fallback": "homepage_only"}
        logger.warning("map_timeout fallback=homepage_only budget_s=%s", map_budget)
    except Exception as exc:
        urls = [str(payload.website_url)]
        diagnostics["map_error"] = str(exc)
        stages["map"] = {"status": "failed", "error": str(exc)[:120], "fallback": "homepage_only"}
        logger.warning("map_failed fallback=homepage_only error=%r", exc)
    timings["map_s"] = round(time.perf_counter() - t_map, 2)

    scrape_payload: dict = {}
    research_payload: dict = {}

    elapsed_pre_parallel = time.perf_counter() - t0
    parallel_budget = max(15, total_deadline - elapsed_pre_parallel)
    t_parallel = time.perf_counter()
    logger.info(
        "parallel_phase_start scrape_url_count=%d budget_s=%.1f (url-scraper + agentic-search + holocron-wire)",
        len(urls),
        parallel_budget,
    )

    scrape_task = asyncio.create_task(client.scrape_urls(urls), name="scrape")
    research_task = asyncio.create_task(
        client.agentic_search(payload.company_name, str(payload.website_url)),
        name="agentic",
    )
    wire_task = asyncio.create_task(
        run_wire_signals(
            company_name=payload.company_name,
            website_url=str(payload.website_url),
            ticker=payload.ticker,
        ),
        name="holocron",
    )
    tasks = {scrape_task, research_task, wire_task}
    done, pending = await asyncio.wait(tasks, timeout=parallel_budget, return_when=asyncio.ALL_COMPLETED)

    deadline_hit = bool(pending)
    cancelled_names: list[str] = []
    for t in pending:
        cancelled_names.append(t.get_name())
        t.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    def _result_or_exc(t: asyncio.Task) -> Any:
        if t in done and not t.cancelled():
            try:
                return t.result()
            except Exception as exc:  # propagate as exception
                return exc
        return asyncio.TimeoutError(f"deadline_exceeded_after_{int(parallel_budget)}s")

    scrape_result = _result_or_exc(scrape_task)
    research_result = _result_or_exc(research_task)
    wire_result = _result_or_exc(wire_task)

    timings["parallel_s"] = round(time.perf_counter() - t_parallel, 2)

    if deadline_hit:
        diagnostics["partial"] = True
        diagnostics["deadline_seconds"] = total_deadline
        diagnostics["cancelled_phases"] = cancelled_names
        logger.warning(
            "analyze_deadline_hit cancelled=%s elapsed_s=%.2f",
            cancelled_names,
            time.perf_counter() - t0,
        )
    logger.info("parallel_phase_done elapsed_s=%.2f", time.perf_counter() - t_parallel)

    wire_rows: list = []
    if isinstance(wire_result, Exception):
        diagnostics["holocron_error"] = str(wire_result)
        stages["holocron"] = {
            "status": "cancelled" if "deadline_exceeded" in str(wire_result) else "failed",
            "error": str(wire_result)[:120],
        }
        logger.warning("holocron_phase_failed error=%r", wire_result)
    else:
        wire_rows = wire_result
        ok_slugs = [r.get("catalog_slug") for r in wire_rows if r.get("ok")]
        diagnostics["holocron"] = wire_rows
        diagnostics["holocron_ok_count"] = len(ok_slugs)
        stages["holocron"] = {
            "status": "ok" if ok_slugs else "empty",
            "ok_slugs": ok_slugs,
            "total_rows": len(wire_rows),
        }
        logger.info("holocron_phase_done ok_slugs=%s", ok_slugs)

    if isinstance(scrape_result, Exception):
        diagnostics["scrape_error"] = str(scrape_result)
        scrape_payload = {"results": []}
        stages["scrape"] = {
            "status": "cancelled" if "deadline_exceeded" in str(scrape_result) else "failed",
            "error": str(scrape_result)[:120],
        }
        logger.warning(
            "scrape_skipped error=%r (memo will use agentic + holocron only)",
            scrape_result,
        )
    else:
        scrape_payload = scrape_result
        n_results = len(scrape_payload.get("results") or [])
        stages["scrape"] = {"status": "ok", "pages_scraped": n_results}
        logger.info("scrape_ok result_rows=%d", n_results)

    if isinstance(research_result, Exception):
        diagnostics["agentic_search_error"] = str(research_result)
        research_payload = {}
        stages["agentic"] = {
            "status": "cancelled" if "deadline_exceeded" in str(research_result) else "failed",
            "error": str(research_result)[:120],
        }
        logger.warning("agentic_skipped error=%r (memo will use website scrape only)", research_result)
    else:
        research_payload = research_result
        has_summary = bool((research_payload.get("generatedJson") or {}).get("summary"))
        stages["agentic"] = {"status": "ok" if has_summary else "empty"}
        logger.info("agentic_ok has_summary=%s", has_summary)

    stock_signal = None
    if payload.ticker:
        t_stock = time.perf_counter()
        try:
            stock_signal = await fetch_stock_trend(payload.ticker)
            diagnostics["stock_available"] = bool(stock_signal)
            stages["stock"] = {
                "status": "ok" if stock_signal else "no_data",
                "ticker": payload.ticker.upper(),
            }
            logger.info("stock_ticker=%r ok=%s", payload.ticker, bool(stock_signal))
        except Exception as exc:
            diagnostics["stock_error"] = str(exc)
            stages["stock"] = {"status": "failed", "ticker": payload.ticker.upper(), "error": str(exc)[:120]}
            logger.warning("stock_failed ticker=%r error=%r", payload.ticker, exc)
        timings["stock_s"] = round(time.perf_counter() - t_stock, 2)
    else:
        stages["stock"] = {"status": "not_requested"}

    report = build_investability_report(
        company_name=payload.company_name,
        website_url=str(payload.website_url),
        scrape_payload=scrape_payload,
        research_payload=research_payload,
        stock_signal=stock_signal,
        wire_results=wire_rows,
    )

    if settings.gemini_enabled and settings.gemini_api_key:
        t_gemini = time.perf_counter()
        try:
            polished = await polish_memo(
                company_name=payload.company_name,
                website_url=str(payload.website_url),
                base_summary=report.get("summary") or "",
                base_risks=list(report.get("risk_flags") or []),
                base_catalysts=list(report.get("growth_catalysts") or []),
                scrape_payload=scrape_payload,
                research_payload=research_payload,
                wire_rows=wire_rows,
            )
        except Exception as exc:
            polished = None
            diagnostics["gemini_error"] = str(exc)
            logger.warning("gemini_polish_failed error=%r", exc)
        if polished:
            report["summary"] = polished["summary"]
            if polished.get("risk_flags"):
                report["risk_flags"] = polished["risk_flags"]
            if polished.get("growth_catalysts"):
                report["growth_catalysts"] = polished["growth_catalysts"]
            if polished.get("key_facts"):
                report["key_facts"] = polished["key_facts"]
            diagnostics["gemini_polished"] = True
            stages["gemini"] = {"status": "ok", "key_facts": len(polished.get("key_facts") or [])}
            logger.info("gemini_polished facts=%d", len(polished.get("key_facts") or []))
        else:
            diagnostics.setdefault("gemini_polished", False)
            stages["gemini"] = {"status": "failed" if diagnostics.get("gemini_error") else "empty"}
        timings["gemini_s"] = round(time.perf_counter() - t_gemini, 2)
    else:
        stages["gemini"] = {"status": "disabled"}

    timings["total_s"] = round(time.perf_counter() - t0, 2)
    diagnostics["timings"] = timings
    diagnostics["stages"] = stages
    report["diagnostics"] = diagnostics

    logger.info(
        "analyze_done total_elapsed_s=%.2f score=%s diagnostics_keys=%s",
        time.perf_counter() - t0,
        report.get("score"),
        list(diagnostics.keys()),
    )

    return AnalyzeResponse(**report)
