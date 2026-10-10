from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.tplink_easymesh.api import InvalidAuth
from custom_components.tplink_easymesh.config_flow import EasyMeshConfigFlow


@pytest.mark.asyncio
async def test_config_flow_auth_error():
    flow = EasyMeshConfigFlow()
    flow.hass = SimpleNamespace(async_add_executor_job=AsyncMock(side_effect=InvalidAuth()))
    flow.async_show_form = MagicMock(return_value="form")
    assert await flow.async_step_user({"host": "192.0.2.1", "password": "test-only"}) == "form"
    assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_config_flow_invalid_url():
    flow = EasyMeshConfigFlow()
    flow.async_show_form = MagicMock(return_value="form")
    await flow.async_step_user({"host": "http://router/private", "password": "test-only"})
    assert flow.async_show_form.call_args.kwargs["errors"] == {"host": "invalid_host"}


@pytest.mark.asyncio
async def test_config_flow_success():
    flow = EasyMeshConfigFlow()
    flow.hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(return_value={"router": {"id": "020000000001", "name": "Test router"}})
    )
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(return_value="created")
    assert await flow.async_step_user({"host": "192.0.2.1", "password": "test-only"}) == "created"
    flow.async_set_unique_id.assert_awaited_once_with("020000000001")
    assert flow.async_create_entry.call_args.kwargs["data"]["host"] == "http://192.0.2.1"
