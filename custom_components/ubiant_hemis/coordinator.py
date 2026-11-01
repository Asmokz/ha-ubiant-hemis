from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HemisApiError, HemisAuthError, HemisClient
from .const import CONF_TOKEN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class HemisData:
    sensors: list[dict[str, Any]]
    actuators: list[dict[str, Any]]


class HemisCoordinator(DataUpdateCoordinator[HemisData]):
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: HemisClient) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Ubiant Hemis Coordinator",
            config_entry=entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> HemisData:
        try:
            sensors = await self.client.get_sensors()
            actuators = await self.client.get_actuators()
        except HemisAuthError as e:
            # Déclenche le flux de ré-authentification dans l'UI
            raise ConfigEntryAuthFailed(str(e)) from e
        except HemisApiError as e:
            raise UpdateFailed(str(e)) from e

        self._persist_token()
        return HemisData(sensors=sensors, actuators=actuators)

    def _persist_token(self) -> None:
        """Sauvegarde le token renouvelé pour éviter un re-login à chaque redémarrage."""
        entry = self.config_entry
        if self.client.token and entry.data.get(CONF_TOKEN) != self.client.token:
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_TOKEN: self.client.token}
            )
