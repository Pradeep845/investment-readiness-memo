"""Wire (Holocron): fetch catalog actions, pick a no-auth task, submit and poll."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_CATALOG_ACTIONS_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL_S = 45 * 60

QUERY_PARAM_NAMES = frozenset(
    {
        "query",
        "q",
        "search",
        "keyword",
        "keywords",
        "search_query",
        "term",
        "text",
        "title",
        "phrase",
    }
)
URL_PARAM_NAMES = frozenset({"url", "website", "website_url", "link", "domain", "hostname"})
TICKER_PARAM_NAMES = frozenset({"ticker", "symbol", "stock", "stock_symbol"})

_MISSING = object()


def _website_domain(website_url: str) -> str:
    host = (urlparse(website_url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _monotonic() -> float:
    return time.monotonic()


def _headers() -> dict[str, str]:
    return {
        "X-API-Key": settings.anakin_api_key,
        "Content-Type": "application/json",
    }


async def _fetch_catalog_actions(client: httpx.AsyncClient, slug: str) -> list[dict[str, Any]] | None:
    key = slug.strip().lower()
    if not key:
        return None

    cached = _CATALOG_ACTIONS_CACHE.get(key)
    if cached and (_monotonic() - cached[0]) < _CACHE_TTL_S:
        return cached[1]

    base = settings.anakin_base_url.rstrip("/")
    resp = await client.get(f"{base}/holocron/catalog/{key}", headers=_headers(), timeout=45.0)
    if resp.status_code == 404:
        logger.warning("holocron_catalog_404 slug=%s", key)
        return None
    resp.raise_for_status()
    payload = resp.json()
    actions = payload.get("actions") or []
    _CATALOG_ACTIONS_CACHE[key] = (_monotonic(), actions)
    return actions


def _fill_params_json_schema_object(
    schema: dict[str, Any],
    *,
    company_name: str,
    website_url: str,
    ticker: str | None,
) -> dict[str, Any] | None:
    """Legacy JSON Schema object shape: { type, properties, required }."""
    if schema.get("type") != "object":
        return None
    required: list[str] = list(schema.get("required") or [])
    props: dict[str, Any] = schema.get("properties") or {}
    if not required:
        return None

    out: dict[str, Any] = {}
    for name in required:
        prop = props.get(name) or {}
        if not isinstance(prop, dict):
            return None
        ptype = prop.get("type")
        enum = prop.get("enum")

        if name in QUERY_PARAM_NAMES:
            out[name] = company_name
            continue
        if name in URL_PARAM_NAMES:
            out[name] = website_url
            continue
        if name in TICKER_PARAM_NAMES:
            if not ticker:
                return None
            out[name] = ticker.strip()
            continue

        if enum:
            return None

        if ptype == "string":
            out[name] = company_name
            continue
        if ptype == "integer":
            if "default" in prop:
                out[name] = prop["default"]
            else:
                return None
            continue
        if ptype == "number":
            out[name] = prop.get("default", 0.0)
            continue
        if ptype == "boolean":
            out[name] = prop.get("default", False)
            continue
        return None

    return out


def _value_for_wire_list_field(
    fname: str,
    ftype: str,
    default: Any,
    *,
    company_name: str,
    website_url: str,
    ticker: str | None,
) -> Any:
    """Resolve one field value for Anakin's list-shaped `parameters` spec."""
    if fname in QUERY_PARAM_NAMES:
        return company_name
    if fname in URL_PARAM_NAMES:
        return website_url
    if fname == "domain":
        dom = _website_domain(website_url)
        return dom if dom else _MISSING
    if fname in TICKER_PARAM_NAMES:
        if not ticker:
            return _MISSING
        return ticker.strip()
    # Geo-specific required fields: do not guess (skip action via _MISSING).
    if fname in {"location", "latitude", "longitude", "lat", "lng"}:
        return _MISSING

    if ftype == "string":
        return company_name
    if ftype == "integer":
        return default if default is not None else _MISSING
    if ftype == "number":
        return default if default is not None else 0.0
    if ftype == "boolean":
        return default if default is not None else False
    return _MISSING


def _fill_params_wire_field_list(
    fields: list[dict[str, Any]],
    *,
    company_name: str,
    website_url: str,
    ticker: str | None,
) -> dict[str, Any] | None:
    """
    Anakin catalog shape: parameters is a list of {name, type, required, default?, description?}.
    """
    if not fields:
        return {}

    out: dict[str, Any] = {}
    for spec in fields:
        if not isinstance(spec, dict):
            return None
        fname = spec.get("name")
        if not fname:
            return None
        if not spec.get("required"):
            continue
        ftype = str(spec.get("type") or "string").lower()
        default = spec.get("default")
        val = _value_for_wire_list_field(
            str(fname),
            ftype,
            default,
            company_name=company_name,
            website_url=website_url,
            ticker=ticker,
        )
        if val is _MISSING:
            return None
        out[str(fname)] = val

    for spec in fields:
        if not isinstance(spec, dict):
            continue
        fname = spec.get("name")
        if fname is None or fname in out:
            continue
        if spec.get("required"):
            continue
        if spec.get("default") is not None:
            out[str(fname)] = spec["default"]

    return out


def _fill_task_params(
    action: dict[str, Any],
    *,
    company_name: str,
    website_url: str,
    ticker: str | None,
) -> dict[str, Any] | None:
    raw = action.get("parameters")

    if isinstance(raw, list):
        return _fill_params_wire_field_list(
            [x for x in raw if isinstance(x, dict)],
            company_name=company_name,
            website_url=website_url,
            ticker=ticker,
        )

    if isinstance(raw, dict) and raw.get("type") == "object":
        return _fill_params_json_schema_object(
            raw,
            company_name=company_name,
            website_url=website_url,
            ticker=ticker,
        )

    return None


def _required_param_count(action: dict[str, Any]) -> int:
    raw = action.get("parameters")
    if isinstance(raw, list):
        return sum(1 for item in raw if isinstance(item, dict) and item.get("required"))
    if isinstance(raw, dict) and raw.get("type") == "object":
        return len(raw.get("required") or [])
    return 999


def _search_hint_score(action: dict[str, Any]) -> int:
    blob = f"{action.get('name', '')} {action.get('description', '')}".lower()
    tags = action.get("tags") or []
    if isinstance(tags, list):
        blob += " " + " ".join(str(t) for t in tags)
    score = 0
    for w in ("search", "lookup", "article", "news", "topic", "wikipedia"):
        if w in blob:
            score += 1
    return score


def _pick_action(
    actions: list[dict[str, Any]],
    *,
    company_name: str,
    website_url: str,
    ticker: str | None,
) -> tuple[str, dict[str, Any]] | None:
    candidates: list[tuple[tuple[int, int, int], dict[str, Any]]] = []
    for action in actions:
        if action.get("auth_required"):
            continue
        if (action.get("status") or "active") != "active":
            continue
        aid = action.get("action_id")
        if not aid:
            continue
        raw_p = action.get("parameters")
        if isinstance(raw_p, list) and len(raw_p) == 0:
            continue
        if isinstance(raw_p, list) and not any(
            isinstance(x, dict) and x.get("required") for x in raw_p
        ):
            # Skip e.g. gn_trending (only optional params) so we prefer company-tied actions.
            continue
        params = _fill_task_params(
            action,
            company_name=company_name,
            website_url=website_url,
            ticker=ticker,
        )
        if params is None:
            continue
        req_n = _required_param_count(action)
        hint = _search_hint_score(action)
        # Fewer required fields first, then stronger search/article hints.
        candidates.append(((req_n, -hint, 0), action))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    chosen = candidates[0][1]
    params = _fill_task_params(
        chosen,
        company_name=company_name,
        website_url=website_url,
        ticker=ticker,
    )
    if params is None:
        return None
    return str(chosen["action_id"]), params


async def _poll_holocron_job(client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
    base = settings.anakin_base_url.rstrip("/")
    elapsed = 0
    timeout = settings.holocron_poll_timeout_seconds
    interval = settings.holocron_poll_seconds

    while elapsed <= timeout:
        resp = await client.get(f"{base}/holocron/jobs/{job_id}", headers=_headers(), timeout=45.0)
        resp.raise_for_status()
        data = resp.json()
        status = (data.get("status") or "").lower()

        if status in {"completed", "done", "success"}:
            return data
        if status in {"failed", "error"}:
            err = data.get("error") or {}
            msg = err.get("message") or data.get("message") or "Wire job failed"
            raise RuntimeError(str(msg))

        await asyncio.sleep(interval)
        elapsed += interval

    raise TimeoutError(f"Holocron job poll timeout job_id={job_id}")


async def _execute_action(client: httpx.AsyncClient, action_id: str, params: dict[str, Any]) -> dict[str, Any]:
    base = settings.anakin_base_url.rstrip("/")
    body = {"action_id": action_id, "params": params}
    resp = await client.post(f"{base}/holocron/task", headers=_headers(), json=body, timeout=90.0)

    if resp.status_code == 402:
        raise RuntimeError("INSUFFICIENT_CREDITS")
    if resp.status_code in (401, 403):
        try:
            err = resp.json().get("error") or {}
            msg = err.get("message") or resp.text
        except Exception:
            msg = resp.text
        raise RuntimeError(msg or "Holocron auth/forbidden")

    resp.raise_for_status()
    data = resp.json()

    if data.get("status") == "error":
        err = data.get("error") or {}
        raise RuntimeError(str(err.get("message") or data))

    if (data.get("status") or "").lower() in {"completed", "done", "success"} and data.get("data") is not None:
        return data

    job_id = data.get("job_id")
    if not job_id:
        raise RuntimeError("Holocron task response missing job_id")

    return await _poll_holocron_job(client, str(job_id))


def _strip_search_highlights(text: str) -> str:
    return text.replace('<span class="searchmatch">', "").replace("</span>", "")


def _readable_wikipedia(data: dict, limit: int) -> str:
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list) or not results:
        return ""
    lines: list[str] = []
    for r in results[:3]:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or "").strip()
        snip = _strip_search_highlights((r.get("snippet") or "").strip())
        if title and snip:
            lines.append(f"{title} — {snip}")
        elif title:
            lines.append(title)
    return " · ".join(lines)[:limit]


def _readable_google_news(data: dict, limit: int) -> str:
    items: list[Any] = []
    if isinstance(data, dict):
        for key in ("data", "results", "articles", "stories"):
            v = data.get(key)
            if isinstance(v, list):
                items = v
                break
    if not items:
        return ""
    lines: list[str] = []
    for r in items[:4]:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or r.get("headline") or "").strip()
        pub = r.get("publisher") or r.get("source") or ""
        if title:
            lines.append(f"{title}{(' (' + str(pub) + ')') if pub else ''}")
    return " · ".join(lines)[:limit]


def snippet_from_wire_data(data: Any, *, slug: str | None = None, limit: int = 400) -> str:
    """Format catalog payloads into a human-readable one-liner; fall back to JSON."""
    try:
        if isinstance(data, dict):
            if slug == "wikipedia":
                pretty = _readable_wikipedia(data, limit)
                if pretty:
                    return pretty
            if slug == "google_news":
                pretty = _readable_google_news(data, limit)
                if pretty:
                    return pretty
        text = json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        text = str(data)
    return text[:limit]


async def run_wire_signals(
    company_name: str,
    website_url: str,
    ticker: str | None = None,
) -> list[dict[str, Any]]:
    """Run one auto-selected Wire action per configured catalog slug."""
    if not settings.holocron_enabled:
        return []
    if not settings.anakin_api_key:
        return [{"catalog_slug": "_", "ok": False, "error": "missing_api_key"}]

    raw = settings.holocron_catalog_slugs or ""
    slugs = [s.strip().lower() for s in raw.split(",") if s.strip()]
    if not slugs:
        return []

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        for slug in slugs:
            row: dict[str, Any] = {"catalog_slug": slug, "ok": False}
            try:
                actions = await _fetch_catalog_actions(client, slug)
                if not actions:
                    row["error"] = "no_actions_or_catalog_missing"
                    results.append(row)
                    await asyncio.sleep(settings.holocron_between_catalog_seconds)
                    continue

                picked = _pick_action(
                    actions,
                    company_name=company_name,
                    website_url=website_url,
                    ticker=ticker,
                )
                if not picked:
                    row["error"] = "no_auto_fillable_action"
                    results.append(row)
                    await asyncio.sleep(settings.holocron_between_catalog_seconds)
                    continue

                action_id, params = picked
                row["action_id"] = action_id
                row["params"] = params

                finished = await _execute_action(client, action_id, params)
                row["ok"] = True
                row["data"] = finished.get("data")
                row["credits_used"] = finished.get("credits_used")
                logger.info(
                    "holocron_ok slug=%s action_id=%s credits_used=%s",
                    slug,
                    action_id,
                    finished.get("credits_used"),
                )
            except Exception as exc:
                row["error"] = str(exc)
                logger.warning("holocron_fail slug=%s error=%r", slug, exc)

            results.append(row)
            await asyncio.sleep(settings.holocron_between_catalog_seconds)

    return results
