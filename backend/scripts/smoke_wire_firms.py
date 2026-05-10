"""Run Holocron Wire for a few firms (uses backend/.env). For manual smoke testing."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main() -> None:
    from app.services.holocron_wire import run_wire_signals

    firms = [
        ("Stripe", "https://stripe.com", None),
        ("Razorpay", "https://razorpay.com", None),
        ("Apple Inc.", "https://www.apple.com", "AAPL"),
    ]
    for name, url, ticker in firms:
        rows = await run_wire_signals(name, url, ticker)
        print("===", name, "===")
        print(json.dumps(rows, indent=2, default=str)[:3500])
        print()


if __name__ == "__main__":
    asyncio.run(main())
