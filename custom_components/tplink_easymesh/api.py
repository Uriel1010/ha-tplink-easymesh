"""Read-only, synchronous adapter. Never expose raw API responses to HA."""

import logging
from threading import Lock
from urllib.parse import parse_qs, urlsplit

from requests.exceptions import RequestException
from tplinkrouterc6u import TplinkRouter
from tplinkrouterc6u.common.exception import ClientException


class CannotConnect(Exception):
    """Transport or incompatible firmware."""


class InvalidAuth(Exception):
    """Local authentication failed."""


def mac_id(value):
    return str(value or "").replace(":", "").replace("-", "").lower()


def validate_host(value):
    value = value.strip().rstrip("/")
    if "://" not in value:
        value = "http://" + value
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Invalid router URL")
    return value


class ReadOnlyRouter(TplinkRouter):
    """Allow only reviewed reads and exact session logout."""

    def request(self, path, data, ignore_response=False, ignore_errors=False):
        parsed = urlsplit(path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        body = parse_qs(data, keep_blank_values=True)
        ops = query.get("operation", []) + body.get("operation", [])
        logout = parsed.path == "admin/system" and query == {"form": ["logout"]} and body == {"operation": ["write"]}
        if not logout and (not ops or any(op not in {"read", "load"} for op in ops)):
            raise ValueError("Configuration operation blocked")
        return super().request(path, data, ignore_response, ignore_errors)


class RouterAPI:
    def __init__(self, host, password):
        self.host = validate_host(host)
        self.password = password
        self._lock = Lock()

    def refresh(self):
        with self._lock:
            return self._refresh()

    def _refresh(self):
        # Library errors may contain decrypted responses; never log them.
        quiet = logging.Logger("tplink_easymesh.transport")
        quiet.addHandler(logging.NullHandler())
        router = ReadOnlyRouter(self.host, self.password, logger=quiet, timeout=10)
        router._url_easymesh_device_list = "admin/easymesh_network?form=mesh_sclient_list_all&operation=read"
        optional_failures = []

        def optional(name, path):
            try:
                return router.request(path, "operation=read")
            except Exception:
                optional_failures.append(name)
                return None

        try:
            try:
                if not router.supports():
                    raise CannotConnect()
            except RequestException:
                raise CannotConnect() from None
            try:
                router.authorize()
            except RequestException:
                raise CannotConnect() from None
            except ClientException:
                raise InvalidAuth() from None
            try:
                firmware = router.get_firmware()
                status = router.get_status()
                ipv4 = router.get_ipv4_status()
            except Exception:
                raise CannotConnect() from None

            root_id = mac_id(status.lan_macaddr)
            if not root_id:
                raise CannotConnect()
            root = {
                "id": root_id,
                "name": firmware.model or "TP-Link Router",
                "model": firmware.model,
                "firmware": firmware.firmware_version,
                "hardware": firmware.hardware_version,
                "ip": status.lan_ipv4_addr,
                "wan_connected": status.ewan_connected,
                "uptime": status.wan_ipv4_uptime,
                "cpu": None if status.cpu_usage is None else round(float(status.cpu_usage) * 100, 1),
                "memory": None if status.mem_usage is None else round(float(status.mem_usage) * 100, 1),
                "clients": status.clients_total,
                "wired_clients": status.wired_total,
                "wifi_clients": status.wifi_clients_total,
                "wan_ip": ipv4.wan_ipv4_ipaddr,
            }
            clients = {}
            for device in status.devices:
                ident = mac_id(device.macaddr)
                if not ident:
                    continue
                clients[ident] = {
                    "id": ident,
                    "name": device.hostname or "Network client",
                    "ip": device.ipaddr,
                    "connected": device.active,
                    "connection": device.type.name,
                    "ap": device.ap_name,
                    "signal": device.signal,
                    "tx_rate": device.tx_rate,
                    "rx_rate": device.rx_rate,
                }
            topology = optional("mesh", "admin/easymesh_network?form=mesh_topology")
            satellites = {}

            def walk(nodes):
                if not isinstance(nodes, list):
                    return
                for node in nodes:
                    ident = mac_id(node.get("mac"))
                    if not ident:
                        continue
                    speed = node.get("link_speed_wire")
                    satellites[ident] = {
                        "id": ident,
                        "name": node.get("name") or node.get("model") or "Mesh satellite",
                        "model": node.get("model"),
                        "ip": node.get("ip"),
                        "location": node.get("location"),
                        "connected": node.get("status") == "connected",
                        "backhaul": node.get("connect_type"),
                        "backhaul_speed": float(speed) / 1024
                        if speed is not None and node.get("connect_type") == "wire"
                        else None,
                        "clients": node.get("mesh_nclient_num"),
                    }
                    for item in node.get("mesh_nclient_list") or []:
                        cid = mac_id(item.get("mac"))
                        if not cid:
                            continue
                        clients[cid] = {
                            "id": cid,
                            "name": item.get("name") or "Network client",
                            "ip": item.get("ip"),
                            "connected": satellites[ident]["connected"],
                            "connection": item.get("connection_type"),
                            "ap": satellites[ident]["name"],
                            "signal": item.get("signal_strength"),
                            "tx_rate": item.get("txrate"),
                            "rx_rate": item.get("rxrate"),
                        }
                    walk(node.get("mesh_sclient_list"))

            if isinstance(topology, dict):
                walk(topology.get("mesh_sclient_list"))
                for item in topology.get("mesh_nclient_list") or []:
                    cid = mac_id(item.get("mac"))
                    if cid in clients:
                        clients[cid]["ap"] = root["name"]
            raw_ports = optional("ports", "admin/status?form=router")
            ports = {}
            if isinstance(raw_ports, list):
                for port in raw_ports:
                    if port.get("name"):
                        ports[port["name"]] = {
                            "connected": port.get("status") == "connected",
                            "speed": port.get("speed"),
                            "duplex": port.get("duplex"),
                        }
            return {
                "router": root,
                "satellites": satellites,
                "clients": clients,
                "ports": ports,
                "mesh_available": topology is not None,
                "ports_available": raw_ports is not None,
                "optional_failures": optional_failures,
            }
        finally:
            if getattr(router, "_logged", False):
                try:
                    router.logout()
                except Exception:
                    pass
