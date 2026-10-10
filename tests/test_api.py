"""Synthetic fixtures only: no home-network identifiers or secrets."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError
from tplinkrouterc6u import Connection, TplinkRouter
from tplinkrouterc6u.common.exception import ClientException

from custom_components.tplink_easymesh.api import (
    CannotConnect,
    InvalidAuth,
    ReadOnlyRouter,
    RouterAPI,
    mac_id,
    validate_host,
)


@pytest.fixture
def fake_router():
    router = MagicMock()
    router.supports.return_value = True
    router._logged = True
    router.get_firmware.return_value = SimpleNamespace(
        model="Archer AX10", firmware_version="test", hardware_version="v1"
    )
    router.get_ipv4_status.return_value = SimpleNamespace(wan_ipv4_ipaddr="198.51.100.1")
    device = SimpleNamespace(
        macaddr="02-00-00-00-00-10",
        hostname="Test phone",
        ipaddr="192.0.2.10",
        active=True,
        type=Connection.HOST_5G,
        signal=None,
        tx_rate=None,
        rx_rate=None,
        ap_name=None,
    )
    router.get_status.return_value = SimpleNamespace(
        lan_macaddr="02-00-00-00-00-01",
        lan_ipv4_addr="192.0.2.1",
        ewan_connected=True,
        wan_ipv4_uptime=123,
        cpu_usage=0.08,
        mem_usage=0.52,
        clients_total=1,
        wired_total=0,
        wifi_clients_total=1,
        devices=[device],
    )
    nodes = [
        {
            "mac": f"02-00-00-00-00-0{i}",
            "model": "Archer C64",
            "name": f"Satellite {i}",
            "ip": f"192.0.2.{i}",
            "location": "office",
            "status": "connected",
            "connect_type": "wire",
            "link_speed_wire": 1024000,
            "mesh_nclient_num": 1 if i == 2 else 0,
            "mesh_nclient_list": (
                [
                    {
                        "mac": device.macaddr,
                        "name": "Test phone",
                        "ip": device.ipaddr,
                        "connection_type": "5G",
                        "signal_strength": -55,
                        "txrate": 300,
                        "rxrate": 360,
                    }
                ]
                if i == 2
                else []
            ),
            "mesh_sclient_list": {},
        }
        for i in range(2, 5)
    ]

    def request(path, data):
        if "mesh_topology" in path:
            return {"mesh_sclient_list": nodes, "mesh_nclient_list": []}
        return [{"name": "wan", "status": "connected", "speed": 1000, "duplex": "FULL"}]

    router.request.side_effect = request
    return router


def test_normalization_and_logout(fake_router):
    with patch("custom_components.tplink_easymesh.api.ReadOnlyRouter", return_value=fake_router):
        data = RouterAPI("192.0.2.1", "test-only").refresh()
    assert len(data["satellites"]) == 3
    assert data["router"]["cpu"] == 8
    assert data["router"]["memory"] == 52
    assert all(n["backhaul_speed"] == 1000 for n in data["satellites"].values())
    assert data["clients"]["020000000010"]["ap"] == "Satellite 2"
    assert data["clients"]["020000000010"]["signal"] == -55
    assert data["ports"]["wan"]["speed"] == 1000
    fake_router.logout.assert_called_once()


def test_optional_mesh_failure_preserves_router(fake_router):
    def request(path, data):
        if "mesh_topology" in path:
            raise ClientException("sensitive raw response")
        return []

    fake_router.request.side_effect = request
    with patch("custom_components.tplink_easymesh.api.ReadOnlyRouter", return_value=fake_router):
        data = RouterAPI("192.0.2.1", "test-only").refresh()
    assert data["router"]["wan_connected"]
    assert not data["mesh_available"]
    assert data["optional_failures"] == ["mesh"]
    assert data["clients"]["020000000010"]["ap"] is None


def test_auth_failure_is_sanitized(fake_router):
    fake_router._logged = False
    fake_router.authorize.side_effect = ClientException("password=test-secret raw response")
    with patch("custom_components.tplink_easymesh.api.ReadOnlyRouter", return_value=fake_router):
        with pytest.raises(InvalidAuth) as error:
            RouterAPI("192.0.2.1", "test-only").refresh()
    assert "secret" not in str(error.value)
    fake_router.authorize.assert_called_once()


def test_transport_error(fake_router):
    fake_router.supports.side_effect = ConnectionError()
    fake_router._logged = False
    with patch("custom_components.tplink_easymesh.api.ReadOnlyRouter", return_value=fake_router):
        with pytest.raises(CannotConnect):
            RouterAPI("192.0.2.1", "test-only").refresh()


@pytest.mark.parametrize(
    "path,data",
    [
        ("admin/system?form=reboot", "operation=write"),
        ("admin/wireless?form=wireless_2g", "operation=write&enable=off"),
        ("admin/status?operation=write", "operation=read"),
        ("admin/status", ""),
        ("admin/system?form=logout", "operation=write&extra=1"),
        ("admin/firmware?form=slave_cmd", "operation=slave_upgrade_firmware"),
    ],
)
def test_mutations_blocked(path, data):
    router = ReadOnlyRouter("http://192.0.2.1", "test-only")
    with patch.object(TplinkRouter, "request") as send:
        with pytest.raises(ValueError):
            router.request(path, data)
        send.assert_not_called()


def test_read_and_exact_logout_allowed():
    router = ReadOnlyRouter("http://192.0.2.1", "test-only")
    with patch.object(TplinkRouter, "request", return_value={}) as send:
        router.request("admin/status?form=router", "operation=read")
        router.request("admin/system?form=logout", "operation=write", True)
        assert send.call_count == 2


@pytest.mark.parametrize(
    "host", ["http://user:secret@192.0.2.1", "http://192.0.2.1/path", "ftp://router", "http://router?token=secret"]
)
def test_invalid_host(host):
    with pytest.raises(ValueError):
        validate_host(host)


def test_stable_mac():
    assert mac_id("02-AB-00-00-00-01") == mac_id("02:ab:00:00:00:01")
