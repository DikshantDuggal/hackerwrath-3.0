"""A detector that runs somewhere else, in any language: we POST the context, it answers.

Request:  POST DETECTOR_URL, JSON body = AssessmentContext, header Authorization: Bearer DETECTOR_TOKEN
Response: 200 with an Assessment JSON, or 204 when it has nothing to add.

The body holds the caller's words, so the URL must be HTTPS (plain HTTP only to this machine),
and the service must not store or log what it receives. The engine applies the timeout.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from ..adapter import PluginOptions, detector
from ..schemas import AssessmentContext

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@detector("http")
class HttpDetector:
    def __init__(self, options: PluginOptions) -> None:
        url = urlparse(options.detector_url)
        if not url.hostname:
            raise ValueError("DETECTOR_URL must be set for the http detector")
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in LOCAL_HOSTS):
            raise ValueError("DETECTOR_URL must use https (http only for localhost)")
        self._url = options.detector_url
        self._headers = {"Authorization": f"Bearer {options.detector_token}"} if options.detector_token else {}
        self._client = httpx.AsyncClient(follow_redirects=False)

    async def assess(self, context: AssessmentContext) -> dict[str, Any] | None:
        res = await self._client.post(self._url, json=context.model_dump(mode="json"), headers=self._headers)
        if res.status_code == 204:
            return None
        res.raise_for_status()
        return res.json()
