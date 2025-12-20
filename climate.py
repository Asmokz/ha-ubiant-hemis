from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HemisCoordinator


PRESET_AWAY = "away"
PRESET_ECO = "eco"
PRESET_COMFORT = "comfort"

PRESETS = [PRESET_AWAY, PRESET_ECO, PRESET_COMFORT]


def _is_pilot_wire(act: dict) -> bool:
    return act.get("actionningRepresentation") == "PILOT_WIRE_THERMOSTAT_THREE_LEVELS"


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


def _get_max_action_value(act: dict) -> float | None:
    for k in ("hardwareState", "state", "targetState"):
        v = (act.get(k) or {}).get("maxActionValue")
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    return None


def _preset_to_value(act: dict, preset: str) -> float:
    """
    Mapping intelligent:
    - si maxActionValue <= 1 : on suppose 0.0 / 0.5 / 1.0
    - sinon : 0 / 1 / 2
    """
    maxv = _get_max_action_value(act)
    if maxv is not None and maxv <= 1.0:
        mapping = {PRESET_AWAY: 0.0, PRESET_ECO: 0.5, PRESET_COMFORT: 1.0}
    else:
        mapping = {PRESET_AWAY: 0.0, PRESET_ECO: 1.0, PRESET_COMFORT: 2.0}
    return mapping[preset]


def _value_to_preset(act: dict, value: float) -> str:
    maxv = _get_max_action_value(act)
    if maxv is not None and maxv <= 1.0:
        # 0 / 0.5 / 1
        if value < 0.25:
            return PRESET_AWAY
        if value < 0.75:
            return PRESET_ECO
        return PRESET_COMFORT
    else:
        # 0 / 1 / 2 (ou approchant)
        if value < 0.5:
            return PRESET_AWAY
        if value < 1.5:
            return PRESET_ECO
        return PRESET_COMFORT


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HemisCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[UbiantHemisPilotWireClimate] = []
    for act in coordinator.data.actuators:
        if _is_pilot_wire(act):
            entities.append(UbiantHemisPilotWireClimate(coordinator, entry, act))

    async_add_entities(entities)


class UbiantHemisPilotWireClimate(CoordinatorEntity[HemisCoordinator], ClimateEntity):
    _attr_supported_features = ClimateEntityFeature.PRESET_MODE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = PRESETS

    def __init__(self, coordinator: HemisCoordinator, entry: ConfigEntry, actuator: dict) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._actuator_id = actuator["actuatorId"]
        self._it_id = actuator["itId"]

        self._attr_name = f"Hemis Heating {self._actuator_id}"
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
    def hvac_mode(self) -> HVACMode | None:
        v = _get_value(self._get_actuator_live())
        if v is None:
            return None
        # away = "OFF" côté HA (plus logique visuellement)
        preset = _value_to_preset(self._get_actuator_live(), v)
        return HVACMode.OFF if preset == PRESET_AWAY else HVACMode.HEAT

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # OFF -> away, HEAT -> eco par défaut
        target = PRESET_AWAY if hvac_mode == HVACMode.OFF else PRESET_ECO
        await self.async_set_preset_mode(target)

    @property
    def preset_mode(self) -> str | None:
        v = _get_value(self._get_actuator_live())
        if v is None:
            return None
        return _value_to_preset(self._get_actuator_live(), v)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in PRESETS:
            return

        act_live = self._get_actuator_live()
        value = _preset_to_value(act_live, preset_mode)

        client = self.hass.data[DOMAIN][self._entry.entry_id]["client"]
        await client.set_actuator_value(
            it_id=self._it_id,
            actuator_id=self._actuator_id,
            value=value,
            duration_ms=0,
        )
        await self.coordinator.async_request_refresh()
