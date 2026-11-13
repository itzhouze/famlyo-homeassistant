"""Gemeinsame Basis: ein Geraet „Famlyo · <Haushalt>" je Eintrag."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FamlyoCoordinator


class FamlyoEntity(CoordinatorEntity[FamlyoCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: FamlyoCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.household_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.household_id)},
            name=f"Famlyo · {coordinator.household_name}",
            manufacturer="Famlyo",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://famlyo.de",
        )
