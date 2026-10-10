"""Stable entity identifiers and per-device hierarchy."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class EasyMeshEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, kind, ident, key, name):
        super().__init__(coordinator)
        self.kind, self.ident, self.key = kind, ident, key
        self._attr_unique_id = f"{coordinator.root_id}_{kind}_{ident}_{key}"
        self._attr_name = name
        root = coordinator.data["router"]
        if kind in {"router", "port"}:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, root["id"])},
                name=root["name"],
                manufacturer="TP-Link",
                model=root.get("model"),
                sw_version=root.get("firmware"),
                hw_version=root.get("hardware"),
            )
        else:
            item = coordinator.data["satellites" if kind == "satellite" else "clients"][ident]
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.root_id}_{kind}_{ident}")},
                name=item["name"],
                manufacturer="TP-Link" if kind == "satellite" else None,
                model=item.get("model"),
                via_device_id=coordinator.root_device_id,
            )

    @property
    def available(self):
        if not super().available:
            return False
        if self.kind == "satellite" and not self.coordinator.data["mesh_available"]:
            return False
        if self.kind == "port" and not self.coordinator.data["ports_available"]:
            return False
        return True

    @property
    def item(self):
        data = self.coordinator.data
        if self.kind == "router":
            return data["router"]
        collection = {"port": "ports", "satellite": "satellites", "client": "clients"}[self.kind]
        return data[collection].get(self.ident, {})


def targets(data):
    yield "router", data["router"]["id"]
    for kind, collection in (("port", "ports"), ("satellite", "satellites"), ("client", "clients")):
        for ident in data[collection]:
            yield kind, ident


def add_dynamic_entities(coordinator, entry, async_add_entities, factory):
    known = set()

    def update():
        entities = []
        for kind, ident in targets(coordinator.data):
            if (kind, ident) not in known:
                known.add((kind, ident))
                entities.extend(factory(kind, ident))
        if entities:
            async_add_entities(entities)

    update()
    entry.async_on_unload(coordinator.async_add_listener(update))
