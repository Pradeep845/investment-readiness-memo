import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.stock_client import fetch_stock_trend, resolve_ticker  # noqa: E402


NAMES = ["Apple Inc", "NVIDIA", "Tesla", "Stripe"]


async def main() -> None:
    for name in NAMES:
        ticker = await resolve_ticker(name)
        if not ticker:
            print(f"{name:25s} -> no public match")
            continue
        trend = await fetch_stock_trend(ticker)
        if not trend:
            print(f"{name:25s} -> {ticker} (trend unavailable)")
            continue
        print(
            f"{name:25s} -> {ticker:6s} price={trend.get('current_price')} "
            f"today={trend.get('today_change_percent')}% 30d={trend.get('change_percent')}%"
        )


if __name__ == "__main__":
    asyncio.run(main())
