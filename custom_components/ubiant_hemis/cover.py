from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    ATTR_POSITION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def _is_roller(act: dict) -> bool:
    rep = act.get("actionningRepresentation")
    factors = act.get("factors") or []
    return rep == "VERTICAL_ROLLER" or "BRIEXT" in factors


def _get_value(act: dict) -> float | None:
    # On préfère hardwareState.value puis targetState/state
    for k in ("hardwareState", "state", "targetState"):
        v = (act.get(k) or {}).get("value")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[UbiantHemisCover] = []

    for act in (coordinator.data.actuators if coordinator.data else []):
        if _is_roller(act):
            entities.append(UbiantHemisCover(coordinator, entry, act))

    async_add_entities(entities)


class UbiantHemisCover(CoordinatorEntity, CoverEntity):
    _attr_supported_features = CoverEntityFeature.SET_POSITION
    _attr_device_class = "shutter"

    def __init__(self, coordinator, entry, actuator: dict):
        super().__init__(coordinator)
        self._entry = entry
        self._actuator_id = actuator["actuatorId"]
        self._it_id = actuator["itId"]

        self._attr_name = f"Hemis Volet {self._actuator_id}"
        self._attr_unique_id = f"{self._it_id}_{self._actuator_id}".replace(":", "_").replace("%", "_")

    def _get_actuator_live(self) -> dict:
        for act in (self.coordinator.data.actuators if self.coordinator.data else []):
            if act.get("actuatorId") == self._actuator_id and act.get("itId") == self._it_id:
                return act
        return {}

    @property
    def available(self) -> bool:
        return _get_value(self._get_actuator_live()) is not None

    @property
    def current_cover_position(self) -> int | None:
        v = _get_value(self._get_actuator_live())
        if v is None:
            return None
        return max(0, min(100, round(v * 100)))

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_cover_position
        if pos is None:
            return None
        return pos == 0

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        pos = kwargs.get(ATTR_POSITION)
        if pos is None:
            return

        value = max(0.0, min(1.0, float(pos) / 100.0))

        client = self.hass.data[DOMAIN][self._entry.entry_id]["client"]
        # duration optionnel : tu peux le laisser, ou passer un truc court
        await client.set_actuator_value(
            it_id=self._it_id,
            actuator_id=self._actuator_id,
            value=value,
            duration_ms=30000,
        )

        await self.coordinator.async_request_refresh()
