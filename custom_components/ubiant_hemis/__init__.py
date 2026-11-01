from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HemisClient
from .const import (
    DOMAIN, PLATFORMS,
    CONF_BASE_URL, CONF_BUILDING_ID, CONF_TOKEN,
    CONF_EMAIL, CONF_PASSWORD, AUTH_BASE_URL
)
from .coordinator import HemisCoordinator

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["yaml"] = conf

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    client = HemisClient(
    base_url=entry.data[CONF_BASE_URL],
    building_id=entry.data[CONF_BUILDING_ID],
    token=entry.data[CONF_TOKEN],
    email=entry.data[CONF_EMAIL],
    password=entry.data[CONF_PASSWORD],
    auth_base_url=AUTH_BASE_URL,
    session=session,
)

    coordinator = HemisCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
