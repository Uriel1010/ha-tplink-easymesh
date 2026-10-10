"""Connectivity observations, not presence trackers."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import EasyMeshEntity, add_dynamic_entities


class EasyMeshConnectivity(EasyMeshEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, kind, ident):
        key = "wan_connected" if kind == "router" else "connected"
        name = "WAN connected" if kind == "router" else "Connected"
        if kind == "port":
            name = ident.upper() + " connected"
        super().__init__(coordinator, kind, ident, key, name)

    @property
    def is_on(self):
        value = self.item.get(self.key)
        if value is None and self.kind in {"client", "satellite"} and not self.item:
            return False
        return value


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    add_dynamic_entities(
        coordinator, entry, async_add_entities, lambda kind, ident: [EasyMeshConnectivity(coordinator, kind, ident)]
    )
