import logging
import re
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}


def _normalize_company_name(raw: str) -> str:
    if not raw:
        return ""
    cleaned = raw.strip()
    cleaned = re.sub(r"\b(inc|inc\.|corp|corp\.|corporation|ltd|ltd\.|llc|plc|s\.a\.|co\.|company|holdings|group)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\s&.-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


async def resolve_ticker(company_name: str) -> str | None:
    """Best-effort ticker lookup via Yahoo Finance search.

    Returns a canonical ticker symbol for an equity match, or None when no
    confident match is found. Never raises.
    """
    query = _normalize_company_name(company_name)
    if not query:
        return None

    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": query, "quotesCount": 5, "newsCount": 0, "lang": "en-US"}

    try:
        async with httpx.AsyncClient(headers=_BROWSER_HEADERS, timeout=8.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.info("ticker_search_non_200 q=%r status=%s", query, resp.status_code)
                return None
            payload = resp.json() or {}
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("ticker_search_failed q=%r error=%r", query, exc)
        return None

    quotes = payload.get("quotes") or []
    lower_q = query.lower()
    first_word = lower_q.split()[0] if lower_q else ""
    candidates: list[tuple[int, int, str]] = []

    for idx, q in enumerate(quotes):
        if not isinstance(q, dict):
            continue
        if q.get("quoteType") != "EQUITY":
            continue
        symbol = (q.get("symbol") or "").strip()
        if not symbol:
            continue

        shortname = (q.get("shortname") or "").lower()
        longname = (q.get("longname") or "").lower()
        name_parts = f"{shortname} {longname}"

        score = 0
        # exact full-query match (highest weight)
        if lower_q == shortname or lower_q == longname:
            score += 80
        elif lower_q in name_parts:
            score += 35
        # first-word match (e.g., query "apple" matches "Apple Inc.")
        if first_word and (shortname.startswith(first_word) or longname.startswith(first_word)):
            score += 25
        # US major exchanges
        if (q.get("exchange") or "") in {"NMS", "NYQ", "NGM", "NCM"}:
            score += 18
        if (q.get("exchDisp") or "") in {"NASDAQ", "NYSE"}:
            score += 10
        # plain symbol (no foreign suffix) → strong preference
        if "." in symbol:
            score -= 25
        else:
            score += 18
        # Yahoo relevance bonus (earlier results tend to be canonical)
        score += max(0, 10 - idx * 2)
        candidates.append((score, -idx, symbol))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    best_score, _neg_idx, best_symbol = candidates[0]
    if best_score < 35:
        return None
    logger.info("ticker_resolved q=%r symbol=%s score=%d", query, best_symbol, best_score)
    return best_symbol.upper()


def _build_points_from_yahoo(data: dict) -> tuple[list[dict], dict]:
    """Returns (points, meta) where meta carries currency and live-quote fields when present."""
    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"][-settings.stock_history_days :]
        closes = result["indicators"]["quote"][0]["close"][-settings.stock_history_days :]
    except (KeyError, IndexError, TypeError):
        return [], {}

    points = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        points.append(
            {
                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat(),
                "close": round(float(close), 2),
            }
        )

    raw_meta = (data.get("chart", {}).get("result") or [{}])[0].get("meta") or {}
    meta = {
        "currency": raw_meta.get("currency") or "USD",
        "exchange": raw_meta.get("exchangeName"),
        "regular_market_price": raw_meta.get("regularMarketPrice"),
        "previous_close": raw_meta.get("previousClose"),
    }
    return points, meta


def _build_points_from_stooq(csv_text: str) -> list[dict]:
    lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
    if len(lines) < 3:
        return []

    points: list[dict] = []
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 5:
            continue
        date = parts[0]
        close = parts[4]
        if close in {"", "N/D"}:
            continue
        try:
            points.append({"timestamp": date, "close": round(float(close), 2)})
        except ValueError:
            continue

    return points[-settings.stock_history_days :]


async def fetch_stock_trend(ticker: str) -> dict | None:
    normalized = ticker.strip().upper()
    if not normalized:
        return None

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{normalized}"
    params = {"range": "1mo", "interval": "1d"}

    meta: dict = {}
    async with httpx.AsyncClient(headers=_BROWSER_HEADERS) as client:
        resp = await client.get(url, params=params, timeout=30.0)
        if resp.status_code != 200:
            logger.info("stock_yahoo_non_200 ticker=%r status=%s", normalized, resp.status_code)
            points: list[dict] = []
        else:
            points, meta = _build_points_from_yahoo(resp.json())

        if not points:
            stooq_symbol = f"{normalized.lower()}.us"
            stooq_url = "https://stooq.com/q/d/l/"
            stooq_resp = await client.get(stooq_url, params={"s": stooq_symbol, "i": "d"}, timeout=20.0)
            if stooq_resp.status_code == 200:
                points = _build_points_from_stooq(stooq_resp.text)
                logger.info("stock_stooq_points ticker=%r count=%d", normalized, len(points))
            else:
                logger.info("stock_stooq_skip ticker=%r status=%s", normalized, stooq_resp.status_code)

    if len(points) < 2:
        logger.info("stock_insufficient_points ticker=%r count=%d", normalized, len(points))
        return None

    first_close = points[0]["close"]
    last_close = points[-1]["close"]
    if first_close == 0:
        return None

    change_percent = round(((last_close - first_close) / first_close) * 100, 2)
    direction = "up" if change_percent > 1 else "down" if change_percent < -1 else "flat"

    current_price = meta.get("regular_market_price") or last_close
    previous_close = meta.get("previous_close")
    if not previous_close and len(points) >= 2:
        previous_close = points[-2]["close"]
    try:
        today_change_percent = (
            round(((current_price - previous_close) / previous_close) * 100, 2) if previous_close else 0.0
        )
    except (TypeError, ZeroDivisionError):
        today_change_percent = 0.0

    out = {
        "ticker": normalized,
        "direction": direction,
        "change_percent": change_percent,
        "current_price": round(float(current_price), 2),
        "previous_close": round(float(previous_close), 2) if previous_close else None,
        "today_change_percent": today_change_percent,
        "currency": meta.get("currency") or "USD",
        "exchange": meta.get("exchange"),
        "points": points,
    }
    logger.info(
        "stock_ok ticker=%r direction=%s change_pct=%s points=%d",
        normalized,
        direction,
        change_percent,
        len(points),
    )
    return out
