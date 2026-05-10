from datetime import datetime, timezone

import httpx

from app.config import settings


def _build_points_from_yahoo(data: dict) -> list[dict]:
    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"][-settings.stock_history_days :]
        closes = result["indicators"]["quote"][0]["close"][-settings.stock_history_days :]
    except (KeyError, IndexError, TypeError):
        return []

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
    return points


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

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=30.0)
        points = _build_points_from_yahoo(resp.json()) if resp.status_code == 200 else []

        if not points:
            stooq_symbol = f"{normalized.lower()}.us"
            stooq_url = "https://stooq.com/q/d/l/"
            stooq_resp = await client.get(stooq_url, params={"s": stooq_symbol, "i": "d"}, timeout=20.0)
            if stooq_resp.status_code == 200:
                points = _build_points_from_stooq(stooq_resp.text)

    if len(points) < 2:
        return None

    first_close = points[0]["close"]
    last_close = points[-1]["close"]
    if first_close == 0:
        return None

    change_percent = round(((last_close - first_close) / first_close) * 100, 2)
    direction = "up" if change_percent > 1 else "down" if change_percent < -1 else "flat"

    return {
        "ticker": normalized,
        "direction": direction,
        "change_percent": change_percent,
        "points": points,
    }
