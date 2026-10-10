"""Exercise only the isolated test HA. Never accepts a production HA URL."""

import argparse
import json
import os
import secrets
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

BASE = "http://127.0.0.1:18123"
ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / ".dev" / "smoke-session.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["setup", "check", "reload", "remove"])
    parser.add_argument("--credentials-file", type=Path)
    args = parser.parse_args()
    session = requests.Session()
    if args.command == "setup" and not SESSION.exists():
        response = session.post(
            BASE + "/api/onboarding/users",
            json={
                "name": "Isolated Test",
                "username": "isolated_test",
                "password": secrets.token_urlsafe(32),
                "client_id": BASE + "/",
                "language": "en",
            },
            timeout=60,
        )
        response.raise_for_status()
        token = session.post(
            BASE + "/auth/token",
            data={"grant_type": "authorization_code", "code": response.json()["auth_code"], "client_id": BASE + "/"},
            timeout=20,
        )
        token.raise_for_status()
        data = {"access_token": token.json()["access_token"]}
        with os.fdopen(os.open(SESSION, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as file:
            json.dump(data, file)
    data = json.loads(SESSION.read_text())
    session.headers["Authorization"] = "Bearer " + data["access_token"]
    if args.command == "setup" and "entry_id" not in data:
        if args.credentials_file is None:
            parser.error("--credentials-file is required for setup")
        values = dotenv_values(args.credentials_file, interpolate=False)
        response = session.post(
            BASE + "/api/config/config_entries/flow",
            json={"handler": "tplink_easymesh", "show_advanced_options": False},
            timeout=20,
        )
        response.raise_for_status()
        flow = response.json()
        response = session.post(
            BASE + "/api/config/config_entries/flow/" + flow["flow_id"],
            json={"host": values["ROUTER_HOST"], "password": values["ROUTER_PASSWORD"]},
            timeout=90,
        )
        response.raise_for_status()
        result = response.json()
        if result["type"] != "create_entry":
            raise RuntimeError("Isolated config flow failed: " + str(result.get("errors", result["type"])))
        data["entry_id"] = result["result"]["entry_id"]
        SESSION.write_text(json.dumps(data))
    if args.command in {"reload", "remove"}:
        method = session.post if args.command == "reload" else session.delete
        url = BASE + "/api/config/config_entries/entry/" + data["entry_id"]
        if args.command == "reload":
            url += "/reload"
        response = method(url, timeout=90)
        response.raise_for_status()
        print("Isolated integration " + args.command + " completed.")
        return
    for _ in range(30):
        response = session.get(BASE + "/api/states", timeout=10)
        response.raise_for_status()
        states = response.json()
        satellite_locations = [
            s for s in states if s.get("attributes", {}).get("friendly_name", "").endswith("Configured location")
        ]
        backhaul_speeds = [
            s for s in states if s.get("attributes", {}).get("friendly_name", "").endswith("Wired link speed")
        ]
        port_speeds = [
            s
            for s in states
            if any(s["entity_id"].endswith("_" + p + "_link_speed") for p in ["wan", "lan1", "lan2", "lan3", "lan4"])
        ]
        if len(port_speeds) == 5:
            break
        time.sleep(2)
    assert len(satellite_locations) == 3, "Mesh satellite entities missing"
    assert len(backhaul_speeds) == 3 and all(float(s["state"]) == 1000 for s in backhaul_speeds)
    assert len(port_speeds) == 5, "Ethernet port entities missing"
    assert all(float(s["state"]) == 1000 for s in port_speeds), "Unexpected port speed"
    assert not any(s["entity_id"].startswith(("switch.", "button.", "device_tracker.")) for s in states)
    print(
        json.dumps(
            {
                "isolated_ha": True,
                "states": len(states),
                "satellites": len(satellite_locations),
                "ethernet_ports": len(port_speeds),
                "all_ports_gigabit": True,
                "control_entities": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
