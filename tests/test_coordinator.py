import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.tplink_easymesh.api import CannotConnect, InvalidAuth
from custom_components.tplink_easymesh.coordinator import EasyMeshCoordinator


def coordinator(executor):
    return SimpleNamespace(
        _poll_lock=asyncio.Lock(),
        hass=SimpleNamespace(async_add_executor_job=executor),
        api=SimpleNamespace(refresh=MagicMock()),
    )


@pytest.mark.asyncio
async def test_failed_update_recovers():
    obj = coordinator(AsyncMock(side_effect=[CannotConnect(), {"router": {"clients": 3}}]))
    with pytest.raises(UpdateFailed):
        await EasyMeshCoordinator._async_update_data(obj)
    assert (await EasyMeshCoordinator._async_update_data(obj))["router"]["clients"] == 3


@pytest.mark.asyncio
async def test_auth_failure_requests_reauth():
    obj = coordinator(AsyncMock(side_effect=InvalidAuth()))
    with pytest.raises(ConfigEntryAuthFailed):
        await EasyMeshCoordinator._async_update_data(obj)


@pytest.mark.asyncio
async def test_polls_do_not_overlap():
    active = 0
    maximum = 0

    async def executor(function):
        nonlocal active, maximum
        active += 1
        maximum = max(active, maximum)
        await asyncio.sleep(0.01)
        active -= 1
        return {}

    obj = coordinator(executor)
    await asyncio.gather(*(EasyMeshCoordinator._async_update_data(obj) for _ in range(3)))
    assert maximum == 1
