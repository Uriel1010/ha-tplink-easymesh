# TP-Link EasyMesh integration

This is the public, read-only Home Assistant custom integration. Do not add
router write operations, controls, device_tracker, or host-service monitoring.

Use the isolated container defined in compose.yaml for HA runtime and tests.
Never mount, modify, restart or test on existing Home Assistant installations.
The test container is ha-tplink-easymesh-test on loopback port 18123 with its
own configuration under .dev/ha. Watchtower updates are explicitly disabled.

The private credentials file remains in the separate router-tools project.
Programs may load it, but never print, source, copy or commit its contents.
Real-router verification is permitted only through read methods. Prefer
synthetic fixtures in tests. Public fixtures must not contain real home-network
addresses, MACs, hostnames, identifiers or credentials. Diagnostics export
projected fields and redact identities, including dictionary-key identities.

Tests run inside the isolated HA image with pytest. Use ruff and hassfest.
After changes, check config setup/reload/unload, optional endpoint failure,
authentication repair, stable client IDs and mutation blocking as relevant.

Each coordinator update runs the synchronous transport in the HA executor;
both a coordinator lock and transport lock prevent overlapping reads.
The AX10 firmware uses mesh_sclient_list_all, not the dependency's default
get_mesh_device_list_all. Raw firmware backhaul Kbps are converted by /1024.

Clean only this project's temporary test resources. Release only after local
tests and public validation jobs pass. A HACS custom repository does not need
inclusion in the default HACS catalog. Minimum HA version is 2026.10.0.
