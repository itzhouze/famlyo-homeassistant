"""Einrichtung: API-Token eingeben, `/v1/me` fragt, wem er gehoert."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import FamlyoApi, FamlyoAuthError, FamlyoConnectionError, FamlyoError, FamlyoPremiumError
from .const import DOMAIN

TOKEN_SCHEMA = vol.Schema({vol.Required(CONF_TOKEN): str})


class FamlyoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, token: str) -> tuple[dict[str, Any] | None, dict[str, str]]:
        api = FamlyoApi(async_get_clientsession(self.hass), token.strip())
        try:
            return await api.me(), {}
        except FamlyoAuthError:
            return None, {"base": "invalid_auth"}
        except FamlyoPremiumError:
            return None, {"base": "premium_required"}
        except FamlyoConnectionError:
            return None, {"base": "cannot_connect"}
        except FamlyoError:
            return None, {"base": "unknown"}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            me, errors = await self._validate(token)
            if me:
                # Ein Eintrag je Token — derselbe Token zweimal waere doppelt gepollt.
                await self.async_set_unique_id(me["token"]["id"] if me.get("token") else me["user"]["id"])
                self._abort_if_unique_id_configured()
                household = me["household"].get("name") or "Famlyo"
                return self.async_create_entry(title=f"Famlyo · {household}", data={CONF_TOKEN: token})
        return self.async_show_form(step_id="user", data_schema=TOKEN_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            me, errors = await self._validate(token)
            if me:
                # Ein neuer Token hat eine neue ID — der Eintrag bleibt derselbe.
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data_updates={CONF_TOKEN: token}
                )
        return self.async_show_form(step_id="reauth_confirm", data_schema=TOKEN_SCHEMA, errors=errors)
