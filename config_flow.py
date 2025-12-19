from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_BASE_URL, CONF_BUILDING_ID, CONF_TOKEN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_BASE_URL): str,
                        vol.Required(CONF_BUILDING_ID): str,
                        vol.Required(CONF_TOKEN): str,
                        vol.Required("email"): str,
                        vol.Required("password"): str,
                    }
                ),
            )

        # Optionnel: tu peux ajouter un test d'auth ici plus tard
        return self.async_create_entry(title="Ubiant Hemis (Flexom)", data=user_input)