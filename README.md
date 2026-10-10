# TP-Link EasyMesh Monitor

<img src="custom_components/tplink_easymesh/brand/icon.png" alt="EasyMesh Monitor icon" width="96" height="96">

[![Validate](https://github.com/Uriel1010/ha-tplink-easymesh/actions/workflows/validate.yml/badge.svg)](https://github.com/Uriel1010/ha-tplink-easymesh/actions/workflows/validate.yml)

Local, **read-only** router and EasyMesh monitoring for Home Assistant.
No cloud account, reboot buttons, Wi-Fi switches or configuration writes.

Verified hardware: **Archer AX10 v1.0** with **Archer C64 Ethernet-backhaul
satellites**. AX10 firmware tested: 1.3.12 Build 20250828. Other models or firmware
may expose different APIs; compatibility with them is not guaranteed.

## Install through HACS

Requires Home Assistant **2026.10.0 or newer** and HACS.

1. Open HACS → menu → **Custom repositories**.
2. Add `https://github.com/Uriel1010/ha-tplink-easymesh`, category **Integration**.
3. Download **TP-Link EasyMesh Monitor** and restart Home Assistant.
4. Settings → Devices & services → Add integration → **TP-Link EasyMesh Monitor**.
5. Enter the main router address and its **local admin password** (not Wi-Fi
   password and not TP-Link ID). Satellites are read through the main router.

Manual installation: copy `custom_components/tplink_easymesh` into your
Home Assistant `config/custom_components/` folder and restart.

## What appears

| Device | Monitoring |
| --- | --- |
| Main router | WAN connection/uptime, CPU, memory, wired/wireless/total clients |
| Ethernet ports | Connection, negotiated speed, duplex for each reported port |
| Mesh satellites | Connection, IP, configured location, backhaul type/speed, client count |
| Network clients | Connection, IP, connection type, access point, RSSI when supplied |

Per-client TX/RX link-rate sensors are created **disabled by default**; enable
them in the entity settings if needed. WAN IP is also disabled by default.
Client entities are connectivity observations, not Home Assistant presence
trackers. Phones using randomized MAC addresses can appear as different devices.
Discovered client devices remain in the registry after disconnecting; their
connectivity sensor turns off after a successful poll no longer lists them.

Wi-Fi PHY rates and negotiated Ethernet speed are **not Internet speed tests**.
TX/RX names preserve the router's reported direction. A configured satellite
location is a label, not geolocation. Missing measurements remain unknown;
unsupported mesh/port reads do not disable successful main-router measurements.

## Configuration and privacy

The default update interval is **60 seconds**, configurable from 30–3600 seconds
under integration options. One serialized poll serves all entities; network I/O
runs outside Home Assistant's event loop. Router login/logout may replace an
active web-admin session on some firmware.

Use Reconfigure to update the router address or password. Authentication failures
request reauthentication; a temporary transport failure makes entities unavailable
and polling recovers when connectivity returns. A different physical router must
be configured as a new integration rather than replacing an existing router ID.

Credentials stay in Home Assistant's local config-entry storage. This integration
does not send telemetry to its author. Downloadable diagnostics redact addresses,
MAC-derived IDs, device names and credentials. Local entity states intentionally
include device names/IPs so you can monitor your own LAN.

## Development and isolated testing

`docker compose up -d` starts only `ha-tplink-easymesh-test` on
`http://127.0.0.1:18123`, with a dedicated Docker bridge and config directory.
It does not use host networking or existing Home Assistant config directories.
Automatic discovery/default integrations are not enabled in the test config.
Create `.dev/ha/configuration.yaml` before starting:

```yaml
homeassistant:
  name: EasyMesh isolated test
http:
frontend:
config:
api:
websocket_api:
logger:
  default: warning
```

Run synthetic tests inside that container:

```sh
docker exec ha-tplink-easymesh-test python -m pip install tplinkrouterc6u==5.36.0 pytest pytest-asyncio ruff
docker exec -w /workspace ha-tplink-easymesh-test python -m pytest -q -p no:cacheprovider
docker exec -w /workspace ha-tplink-easymesh-test python -m ruff check . --no-cache
```

The optional `scripts/smoke.py` targets only the fixed loopback test URL; it
cannot be pointed at production HA. Run with a Python environment containing
`requests` and `python-dotenv`, passing a local credentials-file path for setup.
It loads secrets internally and saves an ephemeral test token under Git-ignored
`.dev/`. The current smoke assertions are tailored to three wired satellites.

Clean up after testing: `docker compose down`, then remove this project's private
`.dev/ha` and `.dev/smoke-session.json`. Never delete or mount production configs.
The GitHub checks run pytest, Ruff, hassfest, HACS validation and Gitleaks using
synthetic data only. The brand check is skipped because this custom repository
does not submit a logo to the Home Assistant brands catalog.

## התקנה בעברית

ב־HACS הוסף את כתובת המאגר כ־Custom repository מסוג Integration, הורד והפעל
מחדש את Home Assistant. לאחר מכן הוסף **TP-Link EasyMesh Monitor** דרך
הגדרות → מכשירים ושירותים. הזן את כתובת הראוטר הראשי וסיסמת הניהול שלו.
האינטגרציה קוראת נתונים בלבד; היא אינה משנה הגדרות או מבצעת אתחול לראוטר.

## License and support

GPL-3.0. Uses the [tplinkrouterc6u](https://github.com/AlexandrErohin/TP-Link-Archer-C6U)
transport library and an AX10-specific, read-only mesh endpoint adapter.
Not affiliated with TP-Link, Home Assistant or HACS.
Report issues with **redacted diagnostics**, router hardware version and firmware.
