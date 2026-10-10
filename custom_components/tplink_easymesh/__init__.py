"""TP-Link EasyMesh Monitor."""

from homeassistant.helpers import device_registry as dr

from .const import PLATFORMS
from .coordinator import EasyMeshCoordinator


async def async_setup_entry(hass, entry):
    coordinator = EasyMeshCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    root = coordinator.data["router"]
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("tplink_easymesh", root["id"])},
        name=root["name"],
        manufacturer="TP-Link",
        model=root.get("model"),
        sw_version=root.get("firmware"),
        hw_version=root.get("hardware"),
    )
    coordinator.root_device_id = device.id
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_options_updated))
    return True


async def async_options_updated(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
