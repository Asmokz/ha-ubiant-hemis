from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HemisConfigEntry
from .entity import HemisActuatorEntity


def _is_roller(act: dict) -> bool:
    rep = act.get("actionningRepresentation")
    factors = act.get("factors") or []
    return rep == "VERTICAL_ROLLER" or "BRIEXT" in factors


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HemisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        UbiantHemisCover(coordinator, act)
        for act in (coordinator.data.actuators if coordinator.data else [])
        if _is_roller(act)
    )


class UbiantHemisCover(HemisActuatorEntity, CoverEntity):
    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, coordinator, actuator: dict) -> None:
        super().__init__(coordinator, actuator)
        self._attr_name = f"Hemis Volet {self._actuator_id}"

    @property
    def current_cover_position(self) -> int | None:
        v = self._value
        if v is None:
            return None
        return max(0, min(100, round(v * 100)))

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_cover_position
        if pos is None:
            return None
        return pos == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._async_set_value(1.0, duration_ms=30000)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._async_set_value(0.0, duration_ms=30000)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        pos = kwargs.get(ATTR_POSITION)
        if pos is None:
            return
        value = max(0.0, min(1.0, float(pos) / 100.0))
        await self._async_set_value(value, duration_ms=30000)
