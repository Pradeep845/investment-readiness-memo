"""One-off: print shapes of holocron catalog actions (uses backend/.env)."""
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"


def load_key() -> str:
    if not ENV.is_file():
        print("Missing backend/.env", file=sys.stderr)
        sys.exit(1)
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("ANAKIN_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    print("ANAKIN_API_KEY not found", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    key = load_key()
    base = "https://api.anakin.io/v1"
    for slug in ("wikipedia", "google_news"):
        r = httpx.get(f"{base}/holocron/catalog/{slug}", headers={"X-API-Key": key}, timeout=60.0)
        print(slug, "http", r.status_code)
        data = r.json()
        acts = data.get("actions") or []
        print("  actions_len", len(acts))
        if not acts:
            continue
        a0 = acts[0]
        print("  first_action_keys", list(a0.keys())[:15])
        prm = a0.get("parameters")
        print("  parameters_python_type", type(prm).__name__)
        if isinstance(prm, list):
            print("  parameters_list_len", len(prm))
            if prm:
                print("  parameters[0]_type", type(prm[0]).__name__)
                if isinstance(prm[0], dict):
                    print("  parameters[0]_keys", list(prm[0].keys())[:10])
        elif isinstance(prm, dict):
            print("  parameters.type", prm.get("type"))
            print("  parameters.required", (prm.get("required") or [])[:5])


if __name__ == "__main__":
    main()
