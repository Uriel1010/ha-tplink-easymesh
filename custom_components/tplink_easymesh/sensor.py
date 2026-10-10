"""Read-only router, mesh and client measurements."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass

from .entity import EasyMeshEntity, add_dynamic_entities

# key, display name, unit, device class, enabled by default
DESCRIPTIONS = {
    "router": [
        ("cpu", "CPU usage", "%", None, True),
        ("memory", "Memory usage", "%", None, True),
        ("uptime", "WAN uptime", "s", SensorDeviceClass.DURATION, True),
        ("clients", "Connected clients", None, None, True),
        ("wired_clients", "Wired clients", None, None, True),
        ("wifi_clients", "Wireless clients", None, None, True),
        ("wan_ip", "WAN IP", None, None, False),
    ],
    "port": [
        ("speed", "Link speed", "Mbit/s", SensorDeviceClass.DATA_RATE, True),
        ("duplex", "Duplex", None, None, True),
    ],
    "satellite": [
        ("ip", "IP address", None, None, True),
        ("location", "Configured location", None, None, True),
        ("backhaul", "Backhaul type", None, None, True),
        ("backhaul_speed", "Wired link speed", "Mbit/s", SensorDeviceClass.DATA_RATE, True),
        ("clients", "Connected clients", None, None, True),
    ],
    "client": [
        ("ip", "IP address", None, None, True),
        ("connection", "Connection type", None, None, True),
        ("ap", "Access point", None, None, True),
        ("signal", "Signal strength", "dBm", SensorDeviceClass.SIGNAL_STRENGTH, True),
        ("tx_rate", "TX link rate", "Mbit/s", SensorDeviceClass.DATA_RATE, False),
        ("rx_rate", "RX link rate", "Mbit/s", SensorDeviceClass.DATA_RATE, False),
    ],
}
TEXT_KEYS = {"wan_ip", "ip", "location", "backhaul", "connection", "ap", "duplex"}


class EasyMeshSensor(EasyMeshEntity, SensorEntity):
    def __init__(self, coordinator, kind, ident, description):
        key, name, unit, device_class, enabled = description
        if kind == "port":
            name = ident.upper() + " " + name
        super().__init__(coordinator, kind, ident, key, name)
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_entity_registry_enabled_default = enabled
        if key not in TEXT_KEYS:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.item.get(self.key)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    add_dynamic_entities(
        coordinator,
        entry,
        async_add_entities,
        lambda kind, ident: [
            EasyMeshSensor(coordinator, kind, ident, description) for description in DESCRIPTIONS[kind]
        ],
    )
