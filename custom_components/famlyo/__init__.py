"""Famlyo — Einkaufsliste und Bestand eines Famlyo-Haushalts in Home Assistant.

Spricht ausschliesslich die oeffentliche Famlyo API (`/v1`) mit einem API-Token
aus der App (Einstellungen → Meine Integrationen → API-Zugriff).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .api import FamlyoApi, FamlyoAuthError, FamlyoError
from .const import (
    ATTR_QUERY,
    CONF_BASE_URL,
    DEFAULT_BASE_URL,
    DOMAIN,
    SCOPE_INVENTORY_READ,
    SERVICE_GET_STOCK,
)
from .coordinator import FamlyoCoordinator

PLATFORMS: list[Platform] = [Platform.TODO, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type FamlyoConfigEntry = ConfigEntry[FamlyoCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Aktionen einmal registrieren — sie waehlen den Eintrag selbst."""

    async def get_stock(call: ServiceCall) -> ServiceResponse:
        entries = [
            e for e in hass.config_entries.async_loaded_entries(DOMAIN)
            if SCOPE_INVENTORY_READ in e.runtime_data.scopes
        ]
        wanted = call.data.get("config_entry_id")
        if wanted:
            entries = [e for e in entries if e.entry_id == wanted]
        if not entries:
            raise HomeAssistantError("Kein Famlyo-Eintrag mit dem Recht „Bestand lesen“.")
        coordinator: FamlyoCoordinator = entries[0].runtime_data
        query = call.data.get(ATTR_QUERY)
        try:
            if query:
                return await coordinator.api.lookup(query)
            return {"items": coordinator.data.inventory if coordinator.data else []}
        except FamlyoError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_STOCK,
        get_stock,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_QUERY): cv.string,
                vol.Optional("config_entry_id"): cv.string,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FamlyoConfigEntry) -> bool:
    api = FamlyoApi(
        async_get_clientsession(hass),
        entry.data[CONF_TOKEN],
        entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
    )
    try:
        me = await api.me()
    except FamlyoAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except FamlyoError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = FamlyoCoordinator(hass, entry, api, me)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FamlyoConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
