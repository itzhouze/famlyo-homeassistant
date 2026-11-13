"""Diagnose-Download: ohne Token, ohne Namen — nur das, was beim Fehlersuchen hilft."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from . import FamlyoConfigEntry

TO_REDACT = {CONF_TOKEN, "id", "name", "first_name", "household_id", "title", "amount_text", "product_ids"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: FamlyoConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "me": async_redact_data(coordinator.me, TO_REDACT),
        "scopes": sorted(coordinator.scopes),
        "counts": {
            "items": len(data.items) if data else 0,
            "inventory": len(data.inventory) if data else 0,
        },
        "last_update_success": coordinator.last_update_success,
    }
