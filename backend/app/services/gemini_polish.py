"""Optional Gemini polish layer: rewrite memo summary/flags/catalysts in analyst tone.

Pure additive: if disabled, key missing, or call fails, the caller keeps the
deterministic memo built from scrape/agentic/holocron.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "risk_flags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "growth_catalysts": {"type": "ARRAY", "items": {"type": "STRING"}},
        "key_facts": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["summary", "risk_flags", "growth_catalysts"],
}

_SYSTEM_PROMPT = (
    "You are a neutral pre-investment analyst. Using ONLY the evidence below, "
    "produce a concise readiness memo. Do not invent funding rounds, valuations, "
    "or numbers that are not in the evidence. Avoid marketing language. "
    "Return strictly JSON matching the requested schema."
)


def _build_prompt(
    *,
    company_name: str,
    website_url: str,
    base_summary: str,
    scrape_excerpt: str,
    research_excerpt: str,
    wikipedia_lines: list[str],
    news_lines: list[str],
    base_risks: list[str],
    base_catalysts: list[str],
) -> str:
    parts = [
        _SYSTEM_PROMPT,
        f"\nCompany: {company_name}",
        f"Website: {website_url}",
        f"\nDeterministic baseline summary: {base_summary[:600]}",
    ]
    if base_risks:
        parts.append("Baseline risk signals: " + " | ".join(base_risks[:5]))
    if base_catalysts:
        parts.append("Baseline catalysts: " + " | ".join(base_catalysts[:5]))
    if scrape_excerpt:
        parts.append(f"\nWebsite excerpt:\n{scrape_excerpt[:1800]}")
    if research_excerpt:
        parts.append(f"\nExternal research summary:\n{research_excerpt[:1800]}")
    if wikipedia_lines:
        parts.append("\nWikipedia hits:\n- " + "\n- ".join(wikipedia_lines[:5]))
    if news_lines:
        parts.append("\nRecent news headlines:\n- " + "\n- ".join(news_lines[:6]))
    parts.append(
        "\nWrite:\n"
        "- summary: 2-3 sentences, neutral analyst tone.\n"
        "- risk_flags: 1-5 short bullets (<=120 chars each), grounded in evidence.\n"
        "- growth_catalysts: 1-5 short bullets (<=120 chars each), grounded in evidence.\n"
        "- key_facts: 1-5 factual statements (<=120 chars each), no opinions."
    )
    return "\n".join(parts)


def _wikipedia_lines(wire_rows: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in wire_rows or []:
        if not isinstance(row, dict) or row.get("catalog_slug") != "wikipedia" or not row.get("ok"):
            continue
        data = row.get("data") or {}
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            continue
        for r in results[:5]:
            if not isinstance(r, dict):
                continue
            title = (r.get("title") or "").strip()
            snippet = (r.get("snippet") or "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
            if title:
                out.append(f"{title} — {snippet[:160]}".strip(" — "))
    return out


def _google_news_lines(wire_rows: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in wire_rows or []:
        if not isinstance(row, dict) or row.get("catalog_slug") != "google_news" or not row.get("ok"):
            continue
        data = row.get("data") or {}
        # gn_related typically returns {"data": [...]} or "data": {"results":[...]}
        items: list[Any] = []
        if isinstance(data, dict):
            for key in ("data", "results", "articles", "stories"):
                v = data.get(key)
                if isinstance(v, list):
                    items = v
                    break
        for r in items[:6]:
            if isinstance(r, dict):
                title = (r.get("title") or r.get("headline") or "").strip()
                pub = r.get("publisher") or r.get("source") or ""
                if title:
                    out.append(f"{title}{(' — ' + str(pub)) if pub else ''}")
    return out


def _scrape_excerpt(scrape_payload: dict) -> str:
    chunks: list[str] = []
    for item in (scrape_payload.get("results") or [])[:3]:
        md = item.get("markdown") or item.get("result", {}).get("markdown") or ""
        if md:
            chunks.append(md[:1200])
    return "\n\n".join(chunks).strip()


async def polish_memo(
    *,
    company_name: str,
    website_url: str,
    base_summary: str,
    base_risks: list[str],
    base_catalysts: list[str],
    scrape_payload: dict,
    research_payload: dict,
    wire_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not settings.gemini_enabled or not settings.gemini_api_key:
        return None

    prompt = _build_prompt(
        company_name=company_name,
        website_url=website_url,
        base_summary=base_summary,
        scrape_excerpt=_scrape_excerpt(scrape_payload),
        research_excerpt=str((research_payload or {}).get("generatedJson", {}).get("summary") or "")[:1800],
        wikipedia_lines=_wikipedia_lines(wire_rows),
        news_lines=_google_news_lines(wire_rows),
        base_risks=base_risks,
        base_catalysts=base_catalysts,
    )

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "responseMimeType": "application/json",
            "responseSchema": _RESPONSE_SCHEMA,
        },
    }

    url = f"{_GEMINI_BASE}/models/{settings.gemini_model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": settings.gemini_api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.gemini_timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            logger.warning("gemini_http_error status=%s body=%s", resp.status_code, resp.text[:300])
            return None
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return None
        text_parts = candidates[0].get("content", {}).get("parts") or []
        if not text_parts:
            return None
        raw_text = text_parts[0].get("text") or ""
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("gemini_json_decode_failed error=%r", exc)
        return None
    except httpx.HTTPError as exc:
        logger.warning("gemini_http_failed error=%r", exc)
        return None
    except Exception as exc:
        logger.warning("gemini_unexpected_failure error=%r", exc)
        return None

    summary = (parsed.get("summary") or "").strip()
    risks = [str(x).strip() for x in (parsed.get("risk_flags") or []) if str(x).strip()]
    catalysts = [str(x).strip() for x in (parsed.get("growth_catalysts") or []) if str(x).strip()]
    facts = [str(x).strip() for x in (parsed.get("key_facts") or []) if str(x).strip()]

    if not summary:
        return None

    return {
        "summary": summary,
        "risk_flags": risks[:5],
        "growth_catalysts": catalysts[:5],
        "key_facts": facts[:5],
    }
