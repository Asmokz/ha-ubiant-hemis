from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HemisClient, HemisApiError
from .const import DEFAULT_SCAN_INTERVAL


@dataclass
class HemisData:
    sensors: list[dict[str, Any]]
    actuators: list[dict[str, Any]]


class HemisCoordinator(DataUpdateCoordinator[HemisData]):
    def __init__(self, hass: HomeAssistant, client: HemisClient) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="Ubiant Hemis Coordinator",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> HemisData:
        try:
            sensors = await self.client.get_sensors()
            actuators = await self.client.get_actuators()
            return HemisData(sensors=sensors, actuators=actuators)
        except HemisApiError as e:
            raise UpdateFailed(str(e)) from e
