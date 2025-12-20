from __future__ import annotations

from typing import Any

from homeassistant.components.light import LightEntity, LightEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HemisCoordinator


def _is_relay_light(act: dict) -> bool:
    """
    Relais EnOcean typiques:
    - factors contient "BRI"
    - actionningRepresentation est souvent None
    - maxActionValue souvent 500 (on s'en sert juste comme indice)
    - state.value 0/1
    """
    factors = act.get("factors") or []
    rep = act.get("actionningRepresentation")
    if "BRI" not in factors:
        return False
    if rep is not None:
        # on évite d’attraper des trucs “spéciaux”
        return False
    return True


def _get_value(act: dict) -> float | None:
    for k in ("hardwareState", "state", "targetState"):
        v = (act.get(k) or {}).get("value")
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HemisCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[UbiantHemisRelayLight] = []
    for act in coordinator.data.actuators:
        if _is_relay_light(act):
            entities.append(UbiantHemisRelayLight(coordinator, entry, act))

    async_add_entities(entities)


class UbiantHemisRelayLight(CoordinatorEntity[HemisCoordinator], LightEntity):
    _attr_supported_features = LightEntityFeature.ONOFF

    def __init__(self, coordinator: HemisCoordinator, entry: ConfigEntry, actuator: dict) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._actuator_id = actuator["actuatorId"]
        self._it_id = actuator["itId"]

        # Nom “propre” si possible
        self._attr_name = f"Hemis Light {self._actuator_id}"
        self._attr_unique_id = f"{self._it_id}_{self._actuator_id}".replace(":", "_").replace("%", "_")

    def _get_actuator_live(self) -> dict:
        for act in self.coordinator.data.actuators:
            if act.get("actuatorId") == self._actuator_id and act.get("itId") == self._it_id:
                return act
        return {}

    @property
    def available(self) -> bool:
        return _get_value(self._get_actuator_live()) is not None

    @property
    def is_on(self) -> bool | None:
        v = _get_value(self._get_actuator_live())
        if v is None:
            return None
        # la majorité des relais: 0/1 (parfois float)
        return v >= 0.5

    async def async_turn_on(self, **kwargs: Any) -> None:
        client = self.hass.data[DOMAIN][self._entry.entry_id]["client"]
        await client.set_actuator_value(
            it_id=self._it_id,
            actuator_id=self._actuator_id,
            value=1.0,
            duration_ms=0,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        client = self.hass.data[DOMAIN][self._entry.entry_id]["client"]
        await client.set_actuator_value(
            it_id=self._it_id,
            actuator_id=self._actuator_id,
            value=0.0,
            duration_ms=0,
        )
        await self.coordinator.async_request_refresh()
