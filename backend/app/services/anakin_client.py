import asyncio
from urllib.parse import urlparse

import httpx

from app.config import settings


class AnakinClient:
    def __init__(self) -> None:
        self.base_url = settings.anakin_base_url.rstrip("/")
        self.headers = {
            "X-API-Key": settings.anakin_api_key,
            "Content-Type": "application/json",
        }

    async def _poll_job(self, client: httpx.AsyncClient, endpoint: str) -> dict:
        elapsed = 0
        timeout = settings.anakin_poll_timeout_seconds

        while elapsed <= timeout:
            resp = await client.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=45.0)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "").lower()

            if status in {"completed", "done", "success"}:
                return data
            if status in {"failed", "error"}:
                raise RuntimeError(data.get("message", "Anakin job failed"))

            await asyncio.sleep(settings.anakin_poll_seconds)
            elapsed += settings.anakin_poll_seconds

        raise TimeoutError(f"Polling timeout for {endpoint}")

    async def discover_urls(self, website_url: str) -> list[str]:
        parsed = urlparse(website_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        payload = {"url": base, "useBrowser": True}
        async with httpx.AsyncClient() as client:
            submit = await client.post(
                f"{self.base_url}/map",
                headers=self.headers,
                json=payload,
                timeout=60.0,
            )
            submit.raise_for_status()
            submitted = submit.json()
            job_id = submitted.get("jobId") or submitted.get("job_id") or submitted.get("id")

            if not job_id:
                return [base]

            result = await self._poll_job(client, f"/map/{job_id}")

        candidates = result.get("urls") or result.get("result", {}).get("urls") or []
        selected = [
            url
            for url in candidates
            if any(token in url.lower() for token in ["about", "team", "pricing", "privacy", "terms", "blog", "careers"])
        ][:8]

        if base not in selected:
            selected.insert(0, base)
        return selected[:10]

    async def scrape_urls(self, urls: list[str]) -> dict:
        payload = {
            "urls": urls[:10],
            "useBrowser": True,
            "onlyMainContent": True,
            "generateJson": True,
            "prompt": (
                "Extract business-relevant facts: product summary, pricing clues, team signals, "
                "customer/social proof, legal/compliance snippets, and growth indicators."
            ),
        }
        async with httpx.AsyncClient() as client:
            submit = await client.post(
                f"{self.base_url}/url-scraper/batch",
                headers=self.headers,
                json=payload,
                timeout=90.0,
            )
            submit.raise_for_status()
            submitted = submit.json()
            job_id = submitted.get("jobId") or submitted.get("job_id") or submitted.get("id")
            if not job_id:
                raise RuntimeError("No URL scraper job id returned")

            return await self._poll_job(client, f"/url-scraper/{job_id}")

    async def agentic_search(self, company_name: str, website_url: str) -> dict:
        prompt = (
            f"Create an investability brief for {company_name} ({website_url}). "
            "Include recent reputation signals, risk indicators, positive catalysts, "
            "and provide citation-worthy points."
        )
        async with httpx.AsyncClient() as client:
            submit = await client.post(
                f"{self.base_url}/agentic-search",
                headers=self.headers,
                json={"prompt": prompt},
                timeout=60.0,
            )
            submit.raise_for_status()
            submitted = submit.json()
            job_id = submitted.get("job_id") or submitted.get("jobId") or submitted.get("id")
            if not job_id:
                raise RuntimeError("No agentic search job id returned")

            return await self._poll_job(client, f"/agentic-search/{job_id}")
