import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = json.loads((ROOT / "holocron_catalog_snapshot.json").read_text(encoding="utf-8"))
out = ROOT / "holocron_catalog_snapshot.md"
lines = [
    "# Wire (Holocron) catalogs — snapshot from GET /v1/holocron/catalog",
    "",
    f"**Count:** {len(rows)}",
    "",
    "| slug | name | domain | actions | catalog_auth_required |",
    "| --- | --- | --- | --: | --- |",
]
for r in rows:
    lines.append(
        f"| {r.get('slug','')} | {r.get('name','')} | {r.get('domain','')} | "
        f"{r.get('action_count','')} | {r.get('auth_required','')} |"
    )
out.write_text("\n".join(lines), encoding="utf-8")
print(out)
