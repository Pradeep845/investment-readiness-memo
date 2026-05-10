import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.stock_client import resolve_ticker  # noqa: E402


NAMES = [
    "NVIDIA",
    "Apple Inc",
    "Tesla",
    "Microsoft",
    "OpenAI",
    "Stripe",
    "Google",
    "Berkshire Hathaway",
    "Coca-Cola",
    "Adobe Systems Incorporated",
    "Anakin",
]


async def main() -> None:
    results = await asyncio.gather(*[resolve_ticker(n) for n in NAMES])
    for name, ticker in zip(NAMES, results):
        print(f"{name:35s} -> {ticker}")


if __name__ == "__main__":
    asyncio.run(main())
