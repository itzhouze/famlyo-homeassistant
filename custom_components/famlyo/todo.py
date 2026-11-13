"""Die Einkaufsliste als HA-Todo-Liste.

Damit funktioniert Assist ohne eigene Saetze: „Fuege Milch zur Einkaufsliste
hinzu" ist der eingebaute Intent `HassListAddItem` — auch ueber lokale Echos.

Offen = *needs_action*, heute abgehakt = *completed*. Ein abgehakter Artikel
wartet in Famlyo aufs Einraeumen; „Erledigte entfernen" in HA lehnt der
Server deshalb ab (409) — der Einraeum-Stapel der Familie bleibt stehen.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FamlyoConfigEntry
from .api import FamlyoError
from .const import SCOPE_SHOPPING_READ, SCOPE_SHOPPING_WRITE
from .coordinator import FamlyoCoordinator
from .entity import FamlyoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FamlyoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if SCOPE_SHOPPING_READ in coordinator.scopes:
        async_add_entities([FamlyoShoppingList(coordinator)])


def _description(item: dict[str, Any]) -> str | None:
    parts = [item.get("amount_text") or None]
    parts += item.get("specification") or []
    store = (item.get("store") or {}).get("name")
    if store:
        parts.append(store)
    text = " · ".join(p for p in parts if p)
    return text or None


class FamlyoShoppingList(FamlyoEntity, TodoListEntity):
    _attr_translation_key = "shopping_list"
    _attr_icon = "mdi:cart-outline"

    def __init__(self, coordinator: FamlyoCoordinator) -> None:
        super().__init__(coordinator, "shopping_list")
        if SCOPE_SHOPPING_WRITE in coordinator.scopes:
            self._attr_supported_features = (
                TodoListEntityFeature.CREATE_TODO_ITEM
                | TodoListEntityFeature.UPDATE_TODO_ITEM
                | TodoListEntityFeature.DELETE_TODO_ITEM
            )

    def _items(self) -> list[dict[str, Any]]:
        return self.coordinator.data.items if self.coordinator.data else []

    @property
    def todo_items(self) -> list[TodoItem]:
        return [
            TodoItem(
                uid=item["id"],
                summary=item["title"],
                status=TodoItemStatus.COMPLETED if item.get("status") == "done" else TodoItemStatus.NEEDS_ACTION,
                description=_description(item),
            )
            for item in self._items()
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        # Freitext wie ein Diktat: „2 Liter Milch, Brot" wird zu zwei Artikeln.
        try:
            await self.coordinator.api.add_text(item.summary or "")
        except FamlyoError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        current = next((i for i in self._items() if i["id"] == item.uid), None)
        if current is None:
            raise HomeAssistantError("Den Artikel gibt es nicht mehr.")
        if item.summary is not None and item.summary != current["title"]:
            raise HomeAssistantError("Umbenennen geht nur in der Famlyo-App.")
        was_done = current.get("status") == "done"
        is_done = item.status == TodoItemStatus.COMPLETED
        if was_done != is_done:
            try:
                await self.coordinator.api.set_checked(item.uid, is_done)
            except FamlyoError as err:
                raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        refused: list[str] = []
        for uid in uids:
            try:
                await self.coordinator.api.delete_item(uid)
            except FamlyoError as err:
                if err.code == "awaiting_putaway":
                    refused.append(uid)
                    continue
                raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
        if refused:
            raise HomeAssistantError(
                "Abgehakte Artikel warten aufs Einräumen — bitte in der Famlyo-App einräumen."
            )
