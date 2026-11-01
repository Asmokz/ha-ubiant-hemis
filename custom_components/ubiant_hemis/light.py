from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HemisConfigEntry
from .entity import HemisActuatorEntity


def _is_relay_light(act: dict) -> bool:
    """
    Relais EnOcean typiques:
    - factors contient "BRI"
    - actionningRepresentation est souvent None
    - maxActionValue souvent 500 (on s'en sert juste comme indice)
    - state.value 0/1
    """
    factors = act.get("factors") or []
    if "BRI" not in factors:
        return False
    # on évite d'attraper des trucs "spéciaux"
    return act.get("actionningRepresentation") is None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HemisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        UbiantHemisRelayLight(coordinator, act)
        for act in (coordinator.data.actuators if coordinator.data else [])
        if _is_relay_light(act)
    )


class UbiantHemisRelayLight(HemisActuatorEntity, LightEntity):
    # Obligatoire depuis HA 2024.x : déclarer les modes couleur supportés
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator, actuator: dict) -> None:
        super().__init__(coordinator, actuator)
        self._attr_name = f"Hemis Light {self._actuator_id}"

    @property
    def is_on(self) -> bool | None:
        v = self._value
        if v is None:
            return None
        # la majorité des relais: 0/1 (parfois float)
        return v >= 0.5

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_value(1.0, duration_ms=0)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_value(0.0, duration_ms=0)
