"""UI setup, reconfiguration and authentication repair."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import CannotConnect, InvalidAuth, RouterAPI, validate_host
from .const import CONF_INTERVAL, DEFAULT_INTERVAL, DOMAIN


def schema(default_host=""):
    return vol.Schema(
        {
            vol.Required("host", default=default_host): str,
            vol.Required("password"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


class EasyMeshConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _submit(self, user_input, step):
        errors = {}
        if user_input is not None:
            try:
                host = validate_host(user_input["host"])
                data = await self.hass.async_add_executor_job(RouterAPI(host, user_input["password"]).refresh)
            except ValueError:
                errors["host"] = "invalid_host"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                unique_id = data["router"]["id"]
                values = {"host": host, "password": user_input["password"]}
                if step != "user":
                    entry = self._get_reauth_entry() if step == "reauth_confirm" else self._get_reconfigure_entry()
                    if unique_id != entry.unique_id:
                        return self.async_abort(reason="wrong_router")
                    return self.async_update_reload_and_abort(entry, data_updates=values)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data["router"]["name"], data=values)
        default_host = ""
        if step != "user":
            entry = self._get_reauth_entry() if step == "reauth_confirm" else self._get_reconfigure_entry()
            default_host = entry.data["host"]
        return self.async_show_form(step_id=step, data_schema=schema(default_host), errors=errors)

    async def async_step_user(self, user_input=None):
        return await self._submit(user_input, "user")

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._submit(user_input, "reauth_confirm")

    async def async_step_reconfigure(self, user_input=None):
        return await self._submit(user_input, "reconfigure")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EasyMeshOptionsFlow()


class EasyMeshOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_INTERVAL, default=self.config_entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600))
                }
            ),
        )
