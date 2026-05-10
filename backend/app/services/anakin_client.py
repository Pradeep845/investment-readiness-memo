import asyncio
import logging
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AnakinClient:
    def __init__(self) -> None:
        self.base_url = settings.anakin_base_url.rstrip("/")
        self.headers = {
            "X-API-Key": settings.anakin_api_key,
            "Content-Type": "application/json",
        }

    async def _poll_job(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        *,
        job_label: str,
        job_id: str | None,
        timeout_seconds: int | None = None,
        poll_seconds: int | None = None,
    ) -> dict:
        elapsed = 0
        timeout = timeout_seconds if timeout_seconds is not None else settings.anakin_poll_timeout_seconds
        interval = poll_seconds if poll_seconds is not None else settings.anakin_poll_seconds
        last_status: str | None = None
        poll_index = 0

        logger.info(
            "[%s] poll_begin job_id=%r endpoint=%s timeout_s=%s interval_s=%s",
            job_label,
            job_id,
            endpoint,
            timeout,
            interval,
        )

        while elapsed <= timeout:
            resp = await client.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=45.0)
            resp.raise_for_status()
            data = resp.json()
            status = (data.get("status") or "").lower()
            poll_index += 1

            if status != last_status:
                logger.info(
                    "[%s] poll #%d status=%r elapsed_s=%d job_id=%r",
                    job_label,
                    poll_index,
                    data.get("status"),
                    elapsed,
                    job_id,
                )
                last_status = status
            elif poll_index % 6 == 0:
                logger.info(
                    "[%s] poll_heartbeat #%d status=%r elapsed_s=%d job_id=%r",
                    job_label,
                    poll_index,
                    data.get("status"),
                    elapsed,
                    job_id,
                )
            else:
                logger.debug(
                    "[%s] poll #%d status=%r elapsed_s=%d job_id=%r",
                    job_label,
                    poll_index,
                    data.get("status"),
                    elapsed,
                    job_id,
                )

            if status in {"completed", "done", "success"}:
                logger.info(
                    "[%s] poll_done job_id=%r total_elapsed_s=%d polls=%d",
                    job_label,
                    job_id,
                    elapsed,
                    poll_index,
                )
                return data
            if status in {"failed", "error"}:
                logger.error("[%s] job_failed job_id=%r message=%r", job_label, job_id, data.get("message"))
                raise RuntimeError(data.get("message", "Anakin job failed"))

            await asyncio.sleep(interval)
            elapsed += interval

        logger.warning(
            "[%s] poll_timeout job_id=%r endpoint=%s waited_s=%s last_status=%r polls=%d "
            "(Anakin may still finish this job server-side; we stopped waiting client-side.)",
            job_label,
            job_id,
            endpoint,
            timeout,
            last_status,
            poll_index,
        )
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
                logger.info("[map] no_job_id returned using base_url only base=%s", base)
                return [base]

            logger.info("[map] submitted job_id=%r", job_id)
            result = await self._poll_job(
                client,
                f"/map/{job_id}",
                job_label="map",
                job_id=job_id,
            )

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

            logger.info("[url-scraper] submitted job_id=%r url_count=%d", job_id, len(urls[:10]))
            return await self._poll_job(
                client,
                f"/url-scraper/{job_id}",
                job_label="url-scraper",
                job_id=job_id,
            )

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

            logger.info(
                "[agentic-search] submitted job_id=%r (multi-stage job: expect many polls; "
                "each GET returns quickly with status=processing until completed)",
                job_id,
            )
            return await self._poll_job(
                client,
                f"/agentic-search/{job_id}",
                job_label="agentic-search",
                job_id=job_id,
                timeout_seconds=settings.anakin_agentic_poll_timeout_seconds,
                poll_seconds=settings.anakin_agentic_poll_seconds,
            )
