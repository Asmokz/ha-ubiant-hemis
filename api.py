from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
import urllib.parse

import aiohttp


class HemisApiError(Exception):
    pass


@dataclass
class HemisClient:
    # HEMIS API (devices)
    base_url: str              # ex: https://.../hemis/rest
    building_id: str           # header Building-Id
    token: str                 # Bearer token

    # AUTH (hemisphere.ubiant.com)
    email: str
    password: str
    auth_base_url: str         # https://hemisphere.ubiant.com

    session: aiohttp.ClientSession

    # lock pour éviter que 10 calls 401 re-auth en même temps
    _auth_lock: asyncio.Lock = asyncio.Lock()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Building-Id": self.building_id,
            "Accept": "application/json",
        }

    async def _request_json(self, method: str, url: str, *, headers=None, json_body=None) -> Any:
        try:
            async with self.session.request(
                method,
                url,
                headers=headers,
                json=json_body,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise HemisApiError(f"{method} {url} -> {resp.status}: {text[:300]}")
                return await resp.json(content_type=None)
        except asyncio.TimeoutError as e:
            raise HemisApiError(f"Timeout calling {url}") from e
        except aiohttp.ClientError as e:
            raise HemisApiError(f"HTTP error calling {url}: {e}") from e

    async def _authenticate(self) -> None:
        """Re-login sur hemisphere.ubiant.com et met à jour self.token."""
        async with self._auth_lock:
            # Si un autre call a déjà refresh, on évite un second login.
            # (Optionnel: tu peux mémoriser un timestamp)
            signin_url = f"{self.auth_base_url.rstrip('/')}/users/signin"
            payload = {"email": self.email, "password": self.password}

            data = await self._request_json(
                "POST",
                signin_url,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json_body=payload,
            )

            token = data.get("token")
            if not token:
                raise HemisApiError("Signin succeeded but no token found in response")
            self.token = token

    async def discover_building_and_base_url(self) -> tuple[str, str]:
        """Retourne (building_id, hemis_base_url) depuis /buildings/mine/infos."""
        infos_url = f"{self.auth_base_url.rstrip('/')}/buildings/mine/infos"
        data = await self._request_json(
            "GET",
            infos_url,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
        )

        # Réponse = liste
        if not isinstance(data, list) or not data:
            raise HemisApiError("buildings/mine/infos returned an empty list")

        first = data[0]
        building_id = first.get("buildingId")
        base_url = first.get("hemis_base_url")

        if not building_id or not base_url:
            raise HemisApiError("Missing buildingId or hemis_base_url in buildings/mine/infos response")

        return building_id, base_url

    async def _get_json(self, path: str) -> Any:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            async with self.session.get(url, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=20)) as resp:
                text = await resp.text()

                if resp.status == 401:
                    await self._authenticate()
                    return await self._get_json(path)

                if resp.status >= 400:
                    raise HemisApiError(f"GET {url} -> {resp.status}: {text[:300]}")
                return await resp.json(content_type=None)
        except asyncio.TimeoutError as e:
            raise HemisApiError(f"Timeout calling {url}") from e
        except aiohttp.ClientError as e:
            raise HemisApiError(f"HTTP error calling {url}: {e}") from e

    async def get_sensors(self) -> list[dict[str, Any]]:
        return await self._get_json("/intelligent-things/sensors")

    async def get_actuators(self) -> list[dict[str, Any]]:
        return await self._get_json("/intelligent-things/actuators")

    async def set_actuator_value(self, it_id: str, actuator_id: str, value: float, duration_ms: int = 30000) -> None:
        it_enc = urllib.parse.quote(it_id, safe="")
        path = f"/intelligent-things/{it_enc}/actuator/{actuator_id}/state"
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

        payload = {"value": float(value), "duration": int(duration_ms)}

        try:
            async with self.session.put(
                url,
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()

                if resp.status == 401:
                    await self._authenticate()
                    return await self.set_actuator_value(it_id, actuator_id, value, duration_ms)

                if resp.status >= 400:
                    raise HemisApiError(f"PUT {url} -> {resp.status}: {text[:300]}")
        except asyncio.TimeoutError as e:
            raise HemisApiError(f"Timeout calling {url}") from e
        except aiohttp.ClientError as e:
            raise HemisApiError(f"HTTP error calling {url}: {e}") from e
