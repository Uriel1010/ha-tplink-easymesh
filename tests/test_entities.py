from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.tplink_easymesh.binary_sensor import EasyMeshConnectivity
from custom_components.tplink_easymesh.diagnostics import async_get_config_entry_diagnostics
from custom_components.tplink_easymesh.entity import add_dynamic_entities
from custom_components.tplink_easymesh.sensor import DESCRIPTIONS, EasyMeshSensor


@pytest.fixture
def coordinator():
    value = MagicMock()
    value.root_id = "020000000001"
    value.root_device_id = "test-parent-device"
    value.last_update_success = True
    value.update_interval = timedelta(seconds=60)
    value.data = {
        "router": {"id": value.root_id, "name": "Test router", "ip": "192.0.2.1", "cpu": 8},
        "clients": {
            "020000000010": {
                "id": "020000000010",
                "name": "Test client",
                "ip": "192.0.2.10",
                "connected": True,
                "signal": -55,
            }
        },
        "satellites": {},
        "ports": {},
        "mesh_available": True,
        "ports_available": True,
        "optional_failures": [],
    }
    return value


def test_client_ip_change_and_disconnect(coordinator):
    ent = EasyMeshConnectivity(coordinator, "client", "020000000010")
    ident = ent.unique_id
    assert ent.is_on
    coordinator.data["clients"]["020000000010"]["ip"] = "192.0.2.11"
    assert ent.unique_id == ident
    coordinator.data["clients"] = {}
    assert ent.is_on is False


def test_unavailable_not_disconnected(coordinator):
    ent = EasyMeshConnectivity(coordinator, "client", "020000000010")
    coordinator.last_update_success = False
    assert not ent.available


def test_rate_entities_disabled_by_default(coordinator):
    for description in DESCRIPTIONS["client"]:
        entity = EasyMeshSensor(coordinator, "client", "020000000010", description)
        if description[0] in {"tx_rate", "rx_rate"}:
            assert not entity.entity_registry_enabled_default


def test_roaming_preserves_entity_id(coordinator):
    description = next(d for d in DESCRIPTIONS["client"] if d[0] == "ap")
    entity = EasyMeshSensor(coordinator, "client", "020000000010", description)
    ident = entity.unique_id
    coordinator.data["clients"]["020000000010"]["ap"] = "Satellite A"
    assert entity.native_value == "Satellite A"
    coordinator.data["clients"]["020000000010"]["ap"] = "Satellite B"
    assert entity.native_value == "Satellite B"
    assert entity.unique_id == ident


def test_dynamic_clients_added_only_once(coordinator):
    entry, add = MagicMock(), MagicMock()

    def factory(kind, ident):
        return [(kind, ident)]

    add_dynamic_entities(coordinator, entry, add, factory)
    callback = coordinator.async_add_listener.call_args.args[0]
    callback()
    assert add.call_count == 1
    coordinator.data["clients"]["020000000020"] = {"name": "New client"}
    callback()
    assert add.call_count == 2


@pytest.mark.asyncio
async def test_diagnostics_redact_identifiers(coordinator):
    data = await async_get_config_entry_diagnostics(None, SimpleNamespace(runtime_data=coordinator))
    assert "020000000010" not in str(data)
    assert "192.0.2.1" not in str(data)
    assert "Test client" not in str(data)
    assert "password" not in data
