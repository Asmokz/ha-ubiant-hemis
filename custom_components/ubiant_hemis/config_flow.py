from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HemisApiError, HemisAuthError, HemisClient
from .const import (
    AUTH_BASE_URL,
    CONF_BASE_URL,
    CONF_BUILDING_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_TOKEN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)
STEP_REAUTH = vol.Schema({vol.Required(CONF_PASSWORD): str})


class HemisConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _async_login(self, email: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
        """Teste les identifiants. Retourne (data, None) ou (None, code_erreur)."""
        client = HemisClient(
            base_url="",
            building_id="",
            token="",
            email=email,
            password=password,
            auth_base_url=AUTH_BASE_URL,
            session=async_get_clientsession(self.hass),
        )
        try:
            await client.authenticate()
            building_id, base_url = await client.discover_building_and_base_url()
        except HemisAuthError:
            return None, "auth_failed"
        except HemisApiError:
            _LOGGER.exception("Error while connecting to Ubiant Hemis")
            return None, "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error while connecting to Ubiant Hemis")
            return None, "unknown"

        return {
            CONF_EMAIL: email,
            CONF_PASSWORD: password,
            CONF_TOKEN: client.token,
            CONF_BUILDING_ID: building_id,
            CONF_BASE_URL: base_url,
        }, None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            data, error = await self._async_login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            if error:
                errors["base"] = error
            else:
                assert data is not None
                building_id = data[CONF_BUILDING_ID]
                # Eviter multiples instances
                await self.async_set_unique_id(f"{DOMAIN}_{building_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Ubiant Hemis ({building_id[-6:]})", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            data, error = await self._async_login(entry.data[CONF_EMAIL], user_input[CONF_PASSWORD])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH,
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )
