from app.models.schemas import EvidenceItem
from app.services.holocron_wire import snippet_from_wire_data


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _extract_scraped_text(scrape_payload: dict) -> str:
    results = scrape_payload.get("results", [])
    chunks: list[str] = []

    for item in results:
        markdown = item.get("markdown") or item.get("result", {}).get("markdown")
        generated = item.get("generatedJson") or item.get("result", {}).get("generatedJson")
        if markdown:
            chunks.append(markdown[:3000])
        if generated:
            chunks.append(str(generated))
    return "\n".join(chunks).lower()


def _confidence_from_evidence(evidence_count: int, has_research: bool, has_scrape: bool) -> str:
    if evidence_count >= 6 and has_research and has_scrape:
        return "high"
    if evidence_count >= 3:
        return "medium"
    return "low"


def build_investability_report(
    company_name: str,
    website_url: str,
    scrape_payload: dict,
    research_payload: dict,
    stock_signal: dict | None,
    wire_results: list[dict] | None = None,
) -> dict:
    wire_rows = wire_results or []

    text_blob = _extract_scraped_text(scrape_payload)
    research_blob = _safe_text(research_payload.get("generatedJson", {}).get("summary"))
    all_text = f"{text_blob}\n{research_blob}"

    score = 50
    risk_flags: list[str] = []
    catalysts: list[str] = []

    if any(term in all_text for term in ["privacy", "terms", "gdpr", "policy"]):
        score += 8
        catalysts.append("Public legal/compliance pages are available.")
    else:
        score -= 10
        risk_flags.append("Legal/compliance visibility appears weak.")

    if any(term in all_text for term in ["team", "founder", "leadership", "careers"]):
        score += 6
        catalysts.append("Organization footprint suggests operating team visibility.")
    else:
        score -= 5
        risk_flags.append("Limited visible team or leadership proof.")

    if any(term in all_text for term in ["case study", "customer", "testimonial", "partners"]):
        score += 8
        catalysts.append("Market validation signals detected (customers/case studies).")

    if any(term in all_text for term in ["lawsuit", "fraud", "investigation", "breach", "penalty"]):
        score -= 15
        risk_flags.append("Potential adverse external signals detected.")

    if stock_signal:
        if stock_signal["direction"] == "up":
            score += 6
            catalysts.append("Recent stock trend is positive.")
        elif stock_signal["direction"] == "down":
            score -= 6
            risk_flags.append("Recent stock trend is negative.")

    wire_ok = [w for w in wire_rows if w.get("ok") and w.get("data") is not None]
    if wire_ok:
        score += min(6, 3 * len(wire_ok))
        catalysts.append("Wire (Holocron) returned structured public-source signals.")

    score = max(0, min(100, score))

    evidence: list[EvidenceItem] = []
    for item in scrape_payload.get("results", [])[:5]:
        src = item.get("url") or item.get("result", {}).get("url") or website_url
        evidence.append(
            EvidenceItem(
                title="Website Evidence",
                source="url-scraper",
                url=src,
                snippet=(item.get("markdown", "") or "")[:160],
            )
        )

    for row in wire_ok[:4]:
        slug = row.get("catalog_slug") or "holocron"
        aid = row.get("action_id") or "wire"
        evidence.append(
            EvidenceItem(
                title=f"Wire: {slug}",
                source=f"holocron:{aid}",
                url=website_url,
                snippet=snippet_from_wire_data(row.get("data"), slug=slug, limit=260),
            )
        )

    summary_text = (
        research_payload.get("generatedJson", {}).get("summary")
        or "Investment readiness memo generated from public footprint, external research, and optional market trend signals."
    )

    return {
        "company_name": company_name,
        "website_url": website_url,
        "score": score,
        "confidence": _confidence_from_evidence(
            evidence_count=len(evidence),
            has_research=bool((research_payload.get("generatedJson") or {}).get("summary")),
            has_scrape=bool(scrape_payload.get("results")),
        ),
        "risk_flags": risk_flags[:5],
        "growth_catalysts": catalysts[:5],
        "summary": summary_text,
        "key_facts": [],
        "evidence": [item.model_dump() for item in evidence],
        "stock_trend": stock_signal,
    }
