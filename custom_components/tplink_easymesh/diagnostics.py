"""Diagnostics deliberately omit credentials and network identities."""

from homeassistant.components.diagnostics import async_redact_data

REDACT = {"id", "name", "ip", "wan_ip", "host", "password", "ap", "location"}


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    data = coordinator.data
    # Collections are keyed by MAC-derived IDs, so export values only.
    return {
        "integration_version": "0.1.0",
        "last_update_success": coordinator.last_update_success,
        "poll_interval": coordinator.update_interval.total_seconds(),
        "router": async_redact_data(data["router"], REDACT),
        "satellites": async_redact_data(list(data["satellites"].values()), REDACT),
        "clients": async_redact_data(list(data["clients"].values()), REDACT),
        "ports": data["ports"],
        "optional_failures": data["optional_failures"],
    }
