"""Ein Abruf fuer alle Entitaeten: Liste und (wenn erlaubt) Bestand."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FamlyoApi, FamlyoAuthError, FamlyoError
from .const import DOMAIN, SCAN_INTERVAL, SCOPE_INVENTORY_READ, SCOPE_SHOPPING_READ

_LOGGER = logging.getLogger(__name__)


@dataclass
class FamlyoData:
    items: list[dict[str, Any]] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)


class FamlyoCoordinator(DataUpdateCoordinator[FamlyoData]):
    """Pollt `/v1` alle 30 s — unveraendert heisst 304, also fast kostenlos."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: FamlyoApi, me: dict[str, Any]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self.me = me
        self.scopes: set[str] = set(me.get("scopes") or [])

    @property
    def household_id(self) -> str:
        return self.me["household"]["id"]

    @property
    def household_name(self) -> str:
        return self.me["household"].get("name") or "Famlyo"

    async def _async_update_data(self) -> FamlyoData:
        try:
            data = FamlyoData()
            if SCOPE_SHOPPING_READ in self.scopes:
                data.items = (await self.api.shopping_items()).get("items", [])
            if SCOPE_INVENTORY_READ in self.scopes:
                data.inventory = (await self.api.inventory()).get("items", [])
            return data
        except FamlyoAuthError as err:
            # Widerrufen oder abgelaufen: HA fragt nach einem neuen Token.
            raise ConfigEntryAuthFailed(str(err)) from err
        except FamlyoError as err:
            raise UpdateFailed(str(err)) from err
