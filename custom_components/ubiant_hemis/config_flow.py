from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HemisClient, HemisApiError
from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_BASE_URL,
    CONF_BUILDING_ID,
    CONF_TOKEN,
    AUTH_BASE_URL,
)

STEP_USER = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER, errors=errors)

        email = user_input[CONF_EMAIL]
        password = user_input[CONF_PASSWORD]

        session = async_get_clientsession(self.hass)

        # client "temporaire" : base_url/building_id placeholders, on les découvrira
        client = HemisClient(
            base_url="",
            building_id="",
            token="",
            email=email,
            password=password,
            auth_base_url=AUTH_BASE_URL,
            session=session,
        )

        try:
            await client._authenticate()
            building_id, base_url = await client.discover_building_and_base_url()
        except HemisApiError:
            errors["base"] = "auth_failed"
            return self.async_show_form(step_id="user", data_schema=STEP_USER, errors=errors)
        except Exception:
            errors["base"] = "unknown"
            return self.async_show_form(step_id="user", data_schema=STEP_USER, errors=errors)

        # Eviter multiples instances
        await self.async_set_unique_id(f"{DOMAIN}_{building_id}")
        self._abort_if_unique_id_configured()

        data = {
            CONF_EMAIL: email,
            CONF_PASSWORD: password,
            CONF_TOKEN: client.token,
            CONF_BUILDING_ID: building_id,
            CONF_BASE_URL: base_url,
        }

        title = f"Ubiant Hemis ({building_id[-6:]})"
        return self.async_create_entry(title=title, data=data)
