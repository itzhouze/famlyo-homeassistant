"""Drei Zahlen, die man auf einem Dashboard sehen will — Listen als Attribute.

Bewusst KEIN Sensor je Produkt: das waeren hunderte Entitaeten, die bei jedem
neuen Produkt entstehen. Einzelne Produkte fragt man mit der Aktion
`famlyo.get_stock` ab.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FamlyoConfigEntry
from .const import EXPIRING_SOON_DAYS, SCOPE_INVENTORY_READ, SCOPE_SHOPPING_READ
from .coordinator import FamlyoCoordinator, FamlyoData
from .entity import FamlyoEntity


def _open(data: FamlyoData) -> list[dict[str, Any]]:
    return [i for i in data.items if i.get("status") != "done"]


def _shortage(data: FamlyoData) -> list[dict[str, Any]]:
    # „Nicht vorrätig" zuerst, dann „wird knapp" — wie in der App.
    rows = [i for i in data.inventory if i.get("state") in ("out", "low")]
    return sorted(rows, key=lambda i: (i.get("state") != "out", i.get("name", "")))


def _expiring(data: FamlyoData) -> list[dict[str, Any]]:
    rows = [
        i for i in data.inventory
        if i.get("quantity", 0) > 0 and i.get("days_left") is not None and i["days_left"] <= EXPIRING_SOON_DAYS
    ]
    return sorted(rows, key=lambda i: i["days_left"])


@dataclass(frozen=True, kw_only=True)
class FamlyoSensorDescription(SensorEntityDescription):
    scope: str
    rows: Callable[[FamlyoData], list[dict[str, Any]]]
    attribute: Callable[[dict[str, Any]], dict[str, Any]]


SENSORS: tuple[FamlyoSensorDescription, ...] = (
    FamlyoSensorDescription(
        key="open_items",
        translation_key="open_items",
        icon="mdi:cart",
        state_class=SensorStateClass.MEASUREMENT,
        scope=SCOPE_SHOPPING_READ,
        rows=_open,
        attribute=lambda i: {"title": i["title"], "amount": i.get("amount_text") or None},
    ),
    FamlyoSensorDescription(
        key="shortage",
        translation_key="shortage",
        icon="mdi:fridge-alert-outline",
        state_class=SensorStateClass.MEASUREMENT,
        scope=SCOPE_INVENTORY_READ,
        rows=_shortage,
        attribute=lambda i: {"name": i["name"], "state": i["state"], "amount": i.get("amount_text")},
    ),
    FamlyoSensorDescription(
        key="expiring",
        translation_key="expiring",
        icon="mdi:calendar-alert",
        state_class=SensorStateClass.MEASUREMENT,
        scope=SCOPE_INVENTORY_READ,
        rows=_expiring,
        attribute=lambda i: {"name": i["name"], "days_left": i["days_left"], "expires": i.get("next_expiry")},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FamlyoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FamlyoSensor(coordinator, description)
        for description in SENSORS
        if description.scope in coordinator.scopes
    )


class FamlyoSensor(FamlyoEntity, SensorEntity):
    entity_description: FamlyoSensorDescription

    def __init__(self, coordinator: FamlyoCoordinator, description: FamlyoSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    def _rows(self) -> list[dict[str, Any]]:
        return self.entity_description.rows(self.coordinator.data) if self.coordinator.data else []

    @property
    def native_value(self) -> int:
        return len(self._rows())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"items": [self.entity_description.attribute(r) for r in self._rows()]}
