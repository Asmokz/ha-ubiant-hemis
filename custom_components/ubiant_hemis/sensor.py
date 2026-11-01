from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HemisConfigEntry
from .coordinator import HemisCoordinator


def _safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@dataclass
class HemisSensorDescriptor:
    key: str
    device_class: SensorDeviceClass | None
    unit: str | None
    state_class: SensorStateClass | None = None


SUPPORTED = {
    "TMP": HemisSensorDescriptor(
        "TMP", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT
    ),
    "BATTERY_LEVEL": HemisSensorDescriptor(
        "BATTERY_LEVEL", SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT
    ),
    "SWS": HemisSensorDescriptor("SWS", None, None),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: HemisConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data

    entities: list[HemisSensor] = []
    for s in (coordinator.data.sensors if coordinator.data else []):
        state = s.get("state") or {}
        sid = state.get("id")
        if sid not in SUPPORTED:
            continue

        entities.append(HemisSensor(coordinator, s["id"], sid))

    async_add_entities(entities)


class HemisSensor(CoordinatorEntity[HemisCoordinator], SensorEntity):
    def __init__(self, coordinator: HemisCoordinator, sensor_id: str, state_id: str) -> None:
        super().__init__(coordinator)
        self._sensor_id = sensor_id
        self._state_id = state_id
        self._attr_unique_id = f"hemis_sensor_{sensor_id}_{state_id}"
        self._attr_name = f"Hemis {state_id} {sensor_id}"

        desc = SUPPORTED[state_id]
        self._attr_device_class = desc.device_class
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_state_class = desc.state_class

    @property
    def native_value(self):
        # Recherche du capteur courant dans le snapshot
        data = self.coordinator.data
        current = next((x for x in (data.sensors if data else []) if x.get("id") == self._sensor_id), None)
        if not current:
            return None
        st = current.get("state") or {}
        v = st.get("value")

        if self._state_id == "BATTERY_LEVEL":
            # souvent 0..1 -> convertir en %
            fv = _safe_float(v)
            if fv is None:
                return None
            if 0.0 <= fv <= 1.0:
                return round(fv * 100.0, 0)
            return fv

        if self._state_id == "TMP":
            fv = _safe_float(v)
            return None if fv is None else round(fv, 2)

        # SWS brut
        fv = _safe_float(v)
        return int(fv) if fv is not None else v
