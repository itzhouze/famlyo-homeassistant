"""Schlanker Client fuer die Famlyo Public API (`/v1`).

Spricht ausschliesslich die dokumentierte oeffentliche API — dieselbe, die
jedes andere Skript mit einem API-Token benutzen kann. Keine internen Routen.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import DEFAULT_BASE_URL


class FamlyoError(Exception):
    """Fehler mit der Meldung des Servers (deutsch, fuer Menschen lesbar)."""

    def __init__(self, message: str, status: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class FamlyoAuthError(FamlyoError):
    """Token ungueltig, abgelaufen oder widerrufen (401)."""


class FamlyoPremiumError(FamlyoError):
    """Der Haushalt hat kein Premium (402)."""


class FamlyoConnectionError(FamlyoError):
    """Server nicht erreichbar."""


@dataclass
class Cached:
    etag: str | None = None
    data: Any = None


class FamlyoApi:
    """Ein API-Token, ein Haushalt."""

    def __init__(self, session: aiohttp.ClientSession, token: str, base_url: str = DEFAULT_BASE_URL) -> None:
        self._session = session
        self._token = token
        self._base = base_url.rstrip("/")
        self._cache: dict[str, Cached] = {}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        etag_key: str | None = None,
        idempotent: bool = False,
    ) -> Any:
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        cached = self._cache.get(etag_key) if etag_key else None
        if cached and cached.etag:
            headers["If-None-Match"] = cached.etag
        if idempotent:
            # Wiederholt HA nach einer Zeitueberschreitung, bekommt es die erste
            # Antwort zurueck statt einen zweiten Artikel.
            headers["Idempotency-Key"] = str(uuid.uuid4())
        try:
            async with self._session.request(
                method,
                f"{self._base}{path}",
                params=params,
                json=json,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 304 and cached:
                    return cached.data
                try:
                    body = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError):
                    body = None
                if resp.status >= 400:
                    message = (body or {}).get("message") if isinstance(body, dict) else None
                    code = (body or {}).get("code") if isinstance(body, dict) else None
                    message = message or f"Famlyo antwortet mit {resp.status}."
                    if resp.status == 401:
                        raise FamlyoAuthError(message, resp.status, code)
                    if resp.status == 402:
                        raise FamlyoPremiumError(message, resp.status, code)
                    raise FamlyoError(message, resp.status, code)
                if etag_key:
                    self._cache[etag_key] = Cached(resp.headers.get("ETag"), body)
                return body
        except (aiohttp.ClientError, TimeoutError) as err:
            raise FamlyoConnectionError(f"Famlyo ist nicht erreichbar: {err}") from err

    async def me(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/me")

    async def shopping_items(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/shopping/items", etag_key="items")

    async def add_text(self, text: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/shopping/items", json={"text": text}, idempotent=True)

    async def set_checked(self, item_id: str, checked: bool) -> dict[str, Any]:
        return await self._request("PATCH", f"/v1/shopping/items/{item_id}", json={"checked": checked})

    async def delete_item(self, item_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/v1/shopping/items/{item_id}")

    async def inventory(self) -> dict[str, Any]:
        return await self._request(
            "GET", "/v1/inventory", params={"include_empty": "true"}, etag_key="inventory"
        )

    async def lookup(self, query: str) -> dict[str, Any]:
        return await self._request("GET", "/v1/inventory/lookup", params={"q": query})
