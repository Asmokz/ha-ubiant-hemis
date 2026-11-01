from __future__ import annotations

from homeassistant.components.climate import (
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HemisConfigEntry
from .entity import HemisActuatorEntity, get_actuator_value

PRESETS = [PRESET_AWAY, PRESET_ECO, PRESET_COMFORT]


def _is_pilot_wire(act: dict) -> bool:
    return act.get("actionningRepresentation") == "PILOT_WIRE_THERMOSTAT_THREE_LEVELS"


def _uses_unit_scale(act: dict) -> bool:
    """True si l'actionneur travaille en 0.0 / 0.5 / 1.0 plutôt qu'en 0 / 1 / 2."""
    maxv = get_actuator_value(act, "maxActionValue")
    return maxv is not None and maxv <= 1.0


def _preset_to_value(act: dict, preset: str) -> float:
    if _uses_unit_scale(act):
        mapping = {PRESET_AWAY: 0.0, PRESET_ECO: 0.5, PRESET_COMFORT: 1.0}
    else:
        mapping = {PRESET_AWAY: 0.0, PRESET_ECO: 1.0, PRESET_COMFORT: 2.0}
    return mapping[preset]


def _value_to_preset(act: dict, value: float) -> str:
    low, high = (0.25, 0.75) if _uses_unit_scale(act) else (0.5, 1.5)
    if value < low:
        return PRESET_AWAY
    if value < high:
        return PRESET_ECO
    return PRESET_COMFORT


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HemisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        UbiantHemisPilotWireClimate(coordinator, act)
        for act in (coordinator.data.actuators if coordinator.data else [])
        if _is_pilot_wire(act)
    )


class UbiantHemisPilotWireClimate(HemisActuatorEntity, ClimateEntity):
    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = PRESETS
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, actuator: dict) -> None:
        super().__init__(coordinator, actuator)
        self._attr_name = f"Hemis Heating {self._actuator_id}"

    @property
    def preset_mode(self) -> str | None:
        v = self._value
        if v is None:
            return None
        return _value_to_preset(self._get_actuator_live(), v)

    @property
    def hvac_mode(self) -> HVACMode | None:
        preset = self.preset_mode
        if preset is None:
            return None
        # away = "OFF" côté HA (plus logique visuellement)
        return HVACMode.OFF if preset == PRESET_AWAY else HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        mode = self.hvac_mode
        if mode is None:
            return None
        return HVACAction.OFF if mode == HVACMode.OFF else HVACAction.HEATING

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # OFF -> away, HEAT -> eco par défaut
        target = PRESET_AWAY if hvac_mode == HVACMode.OFF else PRESET_ECO
        await self.async_set_preset_mode(target)

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in PRESETS:
            return
        value = _preset_to_value(self._get_actuator_live(), preset_mode)
        await self._async_set_value(value, duration_ms=0)
