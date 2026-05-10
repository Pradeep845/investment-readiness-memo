from urllib.parse import quote

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


def _strip_search_highlights(text: str) -> str:
    return text.replace('<span class="searchmatch">', "").replace("</span>", "")


def _clean_markdown_snippet(markdown: str, limit: int = 220) -> str:
    if not markdown:
        return ""
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    cleaned: list[str] = []
    for line in lines:
        if line.startswith(("#", "*", "-", "|", "[", "!")):
            line = line.lstrip("#*-| ").strip()
        if not line or line.startswith("http"):
            continue
        cleaned.append(line)
        if sum(len(c) for c in cleaned) > limit:
            break
    text = " ".join(cleaned)
    return text[:limit].rstrip()


def _readable_page_title(url: str, markdown: str) -> str:
    for line in (markdown or "").splitlines():
        s = line.strip()
        if s.startswith("#"):
            t = s.lstrip("#").strip()
            if t:
                return t[:90]
    if not url:
        return "Website Evidence"
    path = url.rsplit("/", 1)[-1] or url
    return path[:80] or "Website Evidence"


def _wikipedia_url(title: str, pageid: int | None) -> str:
    if pageid:
        return f"https://en.wikipedia.org/?curid={pageid}"
    safe = quote((title or "").replace(" ", "_"))
    return f"https://en.wikipedia.org/wiki/{safe}"


def _expand_wikipedia(data: dict, *, limit: int) -> list[dict[str, str]]:
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return []
    out: list[dict[str, str]] = []
    for r in results[:limit]:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or "").strip()
        if not title:
            continue
        snip = _strip_search_highlights((r.get("snippet") or "").strip())
        out.append(
            {
                "title": title[:80],
                "snippet": snip[:220] or "Reference page on Wikipedia.",
                "url": _wikipedia_url(title, r.get("pageid")),
            }
        )
    return out


def _expand_google_news(data: dict, *, limit: int) -> list[dict[str, str]]:
    items: list = []
    if isinstance(data, dict):
        for key in ("data", "results", "articles", "stories"):
            v = data.get(key)
            if isinstance(v, list):
                items = v
                break
    out: list[dict[str, str]] = []
    for r in items[:limit]:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or r.get("headline") or "").strip()
        url = (r.get("url") or r.get("link") or "").strip()
        publisher = r.get("publisher") or r.get("source") or ""
        if not title or not url:
            continue
        snippet_parts = [str(publisher)] if publisher else []
        if r.get("published_at"):
            snippet_parts.append(str(r["published_at"]))
        out.append(
            {
                "title": title[:120],
                "snippet": " · ".join(snippet_parts)[:200] or "News article.",
                "url": url,
            }
        )
    return out


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
    pillars: list[dict] = []

    has_legal = any(term in all_text for term in ["privacy", "terms", "gdpr", "policy"])
    if has_legal:
        score += 8
        catalysts.append("Public legal/compliance pages are available.")
        pillars.append({"key": "legal", "label": "Legal & Compliance", "score": 80, "note": "Privacy / terms pages discoverable."})
    else:
        score -= 10
        risk_flags.append("Legal/compliance visibility appears weak.")
        pillars.append({"key": "legal", "label": "Legal & Compliance", "score": 30, "note": "No clear privacy/terms footprint."})

    has_team = any(term in all_text for term in ["team", "founder", "leadership", "careers"])
    if has_team:
        score += 6
        catalysts.append("Organization footprint suggests operating team visibility.")
        pillars.append({"key": "team", "label": "Team Visibility", "score": 75, "note": "Team / leadership content present."})
    else:
        score -= 5
        risk_flags.append("Limited visible team or leadership proof.")
        pillars.append({"key": "team", "label": "Team Visibility", "score": 35, "note": "Sparse team / leadership signals."})

    has_validation = any(term in all_text for term in ["case study", "customer", "testimonial", "partners"])
    if has_validation:
        score += 8
        catalysts.append("Market validation signals detected (customers/case studies).")
        pillars.append({"key": "validation", "label": "Market Validation", "score": 80, "note": "Customers, case studies, or partners cited."})
    else:
        pillars.append({"key": "validation", "label": "Market Validation", "score": 50, "note": "Limited explicit customer or partner proof."})

    has_adverse = any(term in all_text for term in ["lawsuit", "fraud", "investigation", "breach", "penalty"])
    if has_adverse:
        score -= 15
        risk_flags.append("Potential adverse external signals detected.")
        pillars.append({"key": "adverse", "label": "Reputation Risk", "score": 25, "note": "Adverse keywords surfaced (lawsuit / breach / penalty)."})
    else:
        pillars.append({"key": "adverse", "label": "Reputation Risk", "score": 85, "note": "No adverse keywords in scanned evidence."})

    if stock_signal:
        if stock_signal["direction"] == "up":
            score += 6
            catalysts.append("Recent stock trend is positive.")
            pillars.append({"key": "market", "label": "Market Trend", "score": 78, "note": f"30-day trend up {stock_signal.get('change_percent', 0)}%."})
        elif stock_signal["direction"] == "down":
            score -= 6
            risk_flags.append("Recent stock trend is negative.")
            pillars.append({"key": "market", "label": "Market Trend", "score": 35, "note": f"30-day trend down {stock_signal.get('change_percent', 0)}%."})
        else:
            pillars.append({"key": "market", "label": "Market Trend", "score": 55, "note": "30-day trend flat."})
    else:
        pillars.append({"key": "market", "label": "Market Trend", "score": 50, "note": "No ticker provided."})

    wire_ok = [w for w in wire_rows if w.get("ok") and w.get("data") is not None]
    if wire_ok:
        score += min(6, 3 * len(wire_ok))
        catalysts.append("Wire (Holocron) returned structured public-source signals.")
        pillars.append({"key": "external", "label": "External Signals", "score": min(85, 60 + 8 * len(wire_ok)), "note": f"{len(wire_ok)} catalogs returned data."})
    else:
        pillars.append({"key": "external", "label": "External Signals", "score": 45, "note": "No external Wire signals returned."})

    score = max(0, min(100, score))

    evidence: list[EvidenceItem] = []
    for item in scrape_payload.get("results", [])[:6]:
        src = item.get("url") or item.get("result", {}).get("url") or website_url
        markdown = item.get("markdown") or item.get("result", {}).get("markdown") or ""
        title = _readable_page_title(src, markdown)
        evidence.append(
            EvidenceItem(
                title=title,
                source="url-scraper",
                url=src,
                snippet=_clean_markdown_snippet(markdown),
            )
        )

    for row in wire_ok:
        slug = row.get("catalog_slug") or "holocron"
        aid = row.get("action_id") or "wire"
        data = row.get("data") or {}
        if slug == "wikipedia":
            for w in _expand_wikipedia(data, limit=3):
                evidence.append(
                    EvidenceItem(
                        title=f"Wikipedia · {w['title']}",
                        source=f"holocron:{aid}",
                        url=w["url"],
                        snippet=w["snippet"],
                    )
                )
        elif slug == "google_news":
            for n in _expand_google_news(data, limit=4):
                evidence.append(
                    EvidenceItem(
                        title=f"News · {n['title']}",
                        source=f"holocron:{aid}",
                        url=n["url"],
                        snippet=n["snippet"],
                    )
                )
        else:
            evidence.append(
                EvidenceItem(
                    title=f"Wire · {slug}",
                    source=f"holocron:{aid}",
                    url=website_url,
                    snippet=snippet_from_wire_data(data, slug=slug, limit=260),
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
        "score_breakdown": pillars,
        "financial_snapshot": {},
        "evidence": [item.model_dump() for item in evidence],
        "stock_trend": stock_signal,
    }
