"""Entité de base commune aux actionneurs Hemis (volets, lumières, chauffage)."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import HemisApiError
from .coordinator import HemisCoordinator


def get_actuator_value(act: dict[str, Any], key: str = "value") -> float | None:
    """Lit une valeur numérique en préférant hardwareState, puis state, puis targetState."""
    for k in ("hardwareState", "state", "targetState"):
        v = (act.get(k) or {}).get(key)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    return None


class HemisActuatorEntity(CoordinatorEntity[HemisCoordinator]):
    """Entité liée à un actionneur (itId + actuatorId)."""

    def __init__(self, coordinator: HemisCoordinator, actuator: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._actuator_id: str = actuator["actuatorId"]
        self._it_id: str = actuator["itId"]
        # Ne pas modifier : changer ce format recréerait toutes les entités existantes
        self._attr_unique_id = f"{self._it_id}_{self._actuator_id}".replace(":", "_").replace("%", "_")

    def _get_actuator_live(self) -> dict[str, Any]:
        data = self.coordinator.data
        for act in (data.actuators if data else []):
            if act.get("actuatorId") == self._actuator_id and act.get("itId") == self._it_id:
                return act
        return {}

    @property
    def _value(self) -> float | None:
        return get_actuator_value(self._get_actuator_live())

    @property
    def available(self) -> bool:
        return super().available and self._value is not None

    async def _async_set_value(self, value: float, duration_ms: int = 0) -> None:
        try:
            await self.coordinator.client.set_actuator_value(
                it_id=self._it_id,
                actuator_id=self._actuator_id,
                value=value,
                duration_ms=duration_ms,
            )
        except HemisApiError as e:
            raise HomeAssistantError(f"Ubiant Hemis: {e}") from e
        await self.coordinator.async_request_refresh()
