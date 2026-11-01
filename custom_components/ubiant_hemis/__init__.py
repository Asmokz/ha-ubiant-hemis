from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HemisClient
from .const import (
    AUTH_BASE_URL,
    CONF_BASE_URL,
    CONF_BUILDING_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_TOKEN,
    PLATFORMS,
)
from .coordinator import HemisCoordinator

type HemisConfigEntry = ConfigEntry[HemisCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: HemisConfigEntry) -> bool:
    client = HemisClient(
        base_url=entry.data[CONF_BASE_URL],
        building_id=entry.data[CONF_BUILDING_ID],
        token=entry.data[CONF_TOKEN],
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        auth_base_url=AUTH_BASE_URL,
        session=async_get_clientsession(hass),
    )

    coordinator = HemisCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HemisConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
