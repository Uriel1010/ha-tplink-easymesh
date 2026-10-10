"""One serialized poll shared by every entity."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, RouterAPI
from .const import CONF_INTERVAL, DEFAULT_INTERVAL, DOMAIN


class EasyMeshCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
            always_update=False,
        )
        self.api = RouterAPI(entry.data["host"], entry.data["password"])
        self._poll_lock = asyncio.Lock()
        self.root_id = entry.unique_id

    async def _async_update_data(self):
        async with self._poll_lock:
            try:
                return await self.hass.async_add_executor_job(self.api.refresh)
            except InvalidAuth:
                raise ConfigEntryAuthFailed("Local router authentication failed") from None
            except CannotConnect:
                raise UpdateFailed("Unable to read router") from None
