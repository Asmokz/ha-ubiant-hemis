from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
import urllib.parse

import aiohttp

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)


class HemisApiError(Exception):
    """Erreur générique de l'API Hemis."""


class HemisAuthError(HemisApiError):
    """Identifiants refusés par hemisphere.ubiant.com."""


@dataclass
class HemisClient:
    # HEMIS API (devices)
    base_url: str              # ex: https://.../hemis/rest
    building_id: str           # header Building-Id
    token: str                 # Bearer token

    # AUTH (hemisphere.ubiant.com)
    email: str
    password: str = field(repr=False)
    auth_base_url: str = ""    # https://hemisphere.ubiant.com

    session: aiohttp.ClientSession | None = field(default=None, repr=False)

    # Un lock par instance pour éviter que 10 appels en 401 se ré-authentifient en même temps
    _auth_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Building-Id": self.building_id,
            "Accept": "application/json",
        }

    async def _raw_request(
        self, method: str, url: str, *, headers: dict[str, str], json_body: Any = None
    ) -> tuple[int, str, Any]:
        """Effectue la requête et retourne (status, texte, json|None)."""
        assert self.session is not None
        try:
            async with self.session.request(
                method, url, headers=headers, json=json_body, timeout=REQUEST_TIMEOUT
            ) as resp:
                text = await resp.text()
                data: Any = None
                if text:
                    try:
                        data = await resp.json(content_type=None)
                    except ValueError:
                        data = None
                return resp.status, text, data
        except asyncio.TimeoutError as e:
            raise HemisApiError(f"Timeout calling {url}") from e
        except aiohttp.ClientError as e:
            raise HemisApiError(f"HTTP error calling {url}: {e}") from e

    async def authenticate(self, expired_token: str | None = None) -> None:
        """Re-login sur hemisphere.ubiant.com et met à jour self.token.

        Si `expired_token` est fourni et qu'un autre appel a déjà renouvelé le
        token entre-temps, on ne refait pas de login.
        """
        async with self._auth_lock:
            if expired_token is not None and self.token and self.token != expired_token:
                return

            signin_url = f"{self.auth_base_url.rstrip('/')}/users/signin"
            status, text, data = await self._raw_request(
                "POST",
                signin_url,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json_body={"email": self.email, "password": self.password},
            )
            if status in (400, 401, 403):
                raise HemisAuthError(f"Signin refused ({status}): {text[:300]}")
            if status >= 400:
                raise HemisApiError(f"POST {signin_url} -> {status}: {text[:300]}")

            token = data.get("token") if isinstance(data, dict) else None
            if not token:
                raise HemisApiError("Signin succeeded but no token found in response")
            self.token = token

    async def discover_building_and_base_url(self) -> tuple[str, str]:
        """Retourne (building_id, hemis_base_url) depuis /buildings/mine/infos."""
        infos_url = f"{self.auth_base_url.rstrip('/')}/buildings/mine/infos"
        status, text, data = await self._raw_request(
            "GET",
            infos_url,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
        )
        if status >= 400:
            raise HemisApiError(f"GET {infos_url} -> {status}: {text[:300]}")

        # Réponse = liste
        if not isinstance(data, list) or not data:
            raise HemisApiError("buildings/mine/infos returned an empty list")

        first = data[0]
        building_id = first.get("buildingId")
        base_url = first.get("hemis_base_url")

        if not building_id or not base_url:
            raise HemisApiError("Missing buildingId or hemis_base_url in buildings/mine/infos response")

        return building_id, base_url

    async def _hemis_request(self, method: str, path: str, json_body: Any = None) -> Any:
        """Appel à l'API Hemis avec une seule ré-authentification en cas de 401."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

        for attempt in range(2):
            headers = self._headers()
            if json_body is not None:
                headers["Content-Type"] = "application/json"
            used_token = self.token

            status, text, data = await self._raw_request(method, url, headers=headers, json_body=json_body)

            if status == 401 and attempt == 0:
                await self.authenticate(expired_token=used_token)
                continue
            if status == 401:
                raise HemisAuthError(f"{method} {url} -> 401 after re-authentication")
            if status >= 400:
                raise HemisApiError(f"{method} {url} -> {status}: {text[:300]}")
            return data

        raise HemisApiError(f"{method} {url} failed")  # pragma: no cover

    async def get_sensors(self) -> list[dict[str, Any]]:
        return await self._hemis_request("GET", "/intelligent-things/sensors") or []

    async def get_actuators(self) -> list[dict[str, Any]]:
        return await self._hemis_request("GET", "/intelligent-things/actuators") or []

    async def set_actuator_value(self, it_id: str, actuator_id: str, value: float, duration_ms: int = 30000) -> None:
        it_enc = urllib.parse.quote(it_id, safe="")
        actuator_enc = urllib.parse.quote(actuator_id, safe="")  # <-- IMPORTANT

        path = f"/intelligent-things/{it_enc}/actuator/{actuator_enc}/state"
        payload = {"value": float(value), "duration": int(duration_ms)}
        await self._hemis_request("PUT", path, json_body=payload)
