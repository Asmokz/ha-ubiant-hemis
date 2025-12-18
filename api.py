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
    base_url: str              # ex: https://.../hemis/rest
    building_id: str           # header Building-Id
    token: str                 # Bearer token
    session: aiohttp.ClientSession

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Building-Id": self.building_id,
            "Accept": "application/json",
        }

    async def _get_json(self, path: str) -> Any:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            async with self.session.get(url, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=20)) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise HemisApiError(f"GET {url} -> {resp.status}: {text[:300]}")
                # Certains endpoints peuvent renvoyer text/plain; on force json
                return await resp.json(content_type=None)
        except asyncio.TimeoutError as e:
            raise HemisApiError(f"Timeout calling {url}") from e
        except aiohttp.ClientError as e:
            raise HemisApiError(f"HTTP error calling {url}: {e}") from e

    async def get_sensors(self) -> list[dict[str, Any]]:
        return await self._get_json("/intelligent-things/sensors")

    async def get_actuators(self) -> list[dict[str, Any]]:
        return await self._get_json("/intelligent-things/actuators")

    # ⚠️ ACTIONS: on met un stub propre, à compléter quand tu confirmes l’endpoint.
    async def set_actuator_value(self, it_id: str, actuator_id: str, value: float, duration_ms: int = 30000) -> None:
        """
        PUT /intelligent-things/{itId}/actuator/{actuatorId}/state
        - itId doit être URL-encodé (contient : et %)
        - value: pour volets Hemis chez toi => 0..1
        """
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
                if resp.status >= 400:
                    raise HemisApiError(f"PUT {url} -> {resp.status}: {text[:300]}")
        except asyncio.TimeoutError as e:
            raise HemisApiError(f"Timeout calling {url}") from e
        except aiohttp.ClientError as e:
            raise HemisApiError(f"HTTP error calling {url}: {e}") from e
