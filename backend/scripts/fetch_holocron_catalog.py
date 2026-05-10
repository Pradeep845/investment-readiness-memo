"""One-off: list Wire (Holocron) catalogs using ANAKIN_API_KEY from backend/.env."""
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
    print("ANAKIN_API_KEY not found in .env", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    key = load_key()
    url = "https://api.anakin.io/v1/holocron/catalog"
    r = httpx.get(url, headers={"X-API-Key": key}, timeout=60.0)
    print("status", r.status_code)
    if r.status_code != 200:
        print(r.text[:2000])
        sys.exit(1)
    data = r.json()
    cats = data.get("catalog") or data.get("catalogs") or []
    rows = []
    for c in cats:
        if isinstance(c, dict):
            rows.append(
                {
                    "slug": c.get("slug"),
                    "name": c.get("name"),
                    "domain": c.get("domain"),
                    "action_count": c.get("action_count"),
                    "auth_required": c.get("auth_required"),
                }
            )
    rows.sort(key=lambda x: (x.get("slug") or ""))
    print("catalog_count", len(rows))
    out_path = ROOT / "holocron_catalog_snapshot.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("wrote", out_path)
    for row in rows:
        print(
            f"{row.get('slug')}\tactions={row.get('action_count')}\t"
            f"domain={row.get('domain')}\tauth_any={row.get('auth_required')}\tname={row.get('name')}"
        )


if __name__ == "__main__":
    main()
