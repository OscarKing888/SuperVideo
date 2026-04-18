"""API client for communicating with the central SuperVideo server."""

import json
from typing import Optional
from urllib import request, error


class SuperVideoAPIClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _request(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data else None

        req = request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("X-API-Key", self.api_key)

        try:
            with request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {body}") from e
        except error.URLError as e:
            raise ConnectionError(f"Connection failed: {e.reason}") from e

    def test_connection(self) -> bool:
        try:
            self._request("GET", "/ping")
            return True
        except Exception:
            return False

    def upload(self, payload: dict) -> dict:
        return self._request("POST", "/api/v1/upload", payload)

    def get_videos(self, limit: int = 100, offset: int = 0) -> dict:
        return self._request("GET", f"/api/v1/videos?limit={limit}&offset={offset}")

    def get_species_stats(self) -> dict:
        return self._request("GET", "/api/v1/species")
