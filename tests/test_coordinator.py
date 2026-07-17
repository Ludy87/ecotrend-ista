"""Tests for coordinator helpers."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from custom_components.ecotrend_ista import coordinator
from custom_components.ecotrend_ista.coordinator import IstaDataUpdateCoordinator, create_directory_file


class DummyConfig:
    """Provide a minimal config object with a path helper."""

    def __init__(self, base: str) -> None:
        """Store the temporary base path."""
        self._base = base

    def path(self, *paths: str) -> str:
        """Build a path relative to the temporary base."""
        return os.path.join(self._base, *paths)


class DummyHass:
    """Simplified hass object for coordinator tests."""

    def __init__(self, base: str) -> None:
        """Initialize the fake Home Assistant configuration."""
        self.config = DummyConfig(base)

    async def async_add_executor_job(self, func, *args: Any, **kwargs: Any) -> Any:
        """Run a synchronous callable immediately."""
        return func(*args, **kwargs)


class DummyRaw:
    """Minimal replacement for the CustomRaw object."""

    def __init__(self, payload: dict[str, Any]) -> None:
        """Store the payload returned by ``to_dict``."""
        self._payload = payload

    def to_dict(self) -> dict[str, Any]:
        """Return the stored payload."""
        return self._payload


def test_create_directory_file_writes_expected_json(tmp_path: Path) -> None:
    """The helper should create the target folder and write the JSON representation."""

    hass = DummyHass(str(tmp_path))
    payload = {"value": 42}
    consum_raw = DummyRaw(payload)

    asyncio.run(create_directory_file(hass, consum_raw, "support"))

    target_file = tmp_path / "www" / "ecotrend_ista_support.json"
    assert target_file.exists()

    with target_file.open(encoding="utf-8") as file:
        data = json.load(file)

    assert data == payload


def test_set_controller_passes_selected_backend(monkeypatch) -> None:
    """The coordinator must not discard the URL stored in config-entry options."""

    class DummyEntry:
        entry_id = "entry"
        data = {"email": "tenant-login", "password": "secret", "mfa_code": ""}
        options = {"URL": "cz_url", "update_interval": 24}

    class CoordinatorHass:
        pass

    captured: dict[str, Any] = {}
    expected_controller = object()

    def fake_login_account(_hass, data, demo=False):
        captured.update(data)
        assert demo is False
        return expected_controller

    monkeypatch.setattr(coordinator, "login_account", fake_login_account)
    data_coordinator = IstaDataUpdateCoordinator(CoordinatorHass(), DummyEntry())

    data_coordinator.set_controller()

    assert data_coordinator.controller is expected_controller
    assert captured["URL"] == "cz_url"


def test_czech_update_uses_home_assistant_payload_and_syncs_statistics(monkeypatch) -> None:
    """Czech updates should avoid the legacy German consumption parser."""

    class DummyEntry:
        entry_id = "entry"
        data = {"email": "tenant-login", "password": "secret", "mfa_code": ""}
        options = {"URL": "cz_url", "update_interval": 24}

    class CoordinatorHass:
        async def async_add_executor_job(self, func, *args: Any) -> Any:
            return func(*args)

    payload = {
        "meters": [{"id": "meter-1", "type": "heating", "value": "10"}],
        "aggregates": {"heating": {"unit": "díl", "daily": []}},
    }

    class CzechController:
        def __init__(self) -> None:
            self.home_data_calls = 0

        def get_home_assistant_data(self) -> dict[str, Any]:
            self.home_data_calls += 1
            return payload

        def get_support_code(self) -> str:
            return "cz-account"

        def consum_raw(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
            raise AssertionError("The Czech path must not use consum_raw")

    controller_instance = CzechController()
    data_coordinator = IstaDataUpdateCoordinator(CoordinatorHass(), DummyEntry())

    async def fake_init() -> None:
        data_coordinator.controller = controller_instance

    synced: dict[str, Any] = {}

    async def fake_sync(_hass, account_id: str, aggregates: dict[str, Any]) -> None:
        synced["account_id"] = account_id
        synced["aggregates"] = aggregates

    monkeypatch.setattr(data_coordinator, "init", fake_init)
    monkeypatch.setattr(coordinator, "async_sync_czech_statistics", fake_sync)

    result = asyncio.run(data_coordinator._async_update_data())

    assert result == payload
    assert data_coordinator.czech_data == payload
    assert controller_instance.home_data_calls == 1
    assert synced == {
        "account_id": "cz-account",
        "aggregates": payload["aggregates"],
    }


def test_german_update_keeps_legacy_consumption_path(monkeypatch, tmp_path: Path) -> None:
    """The Czech branch must not change the existing German update behavior."""

    class DummyEntry:
        entry_id = "entry"
        data = {"email": "user@example.com", "password": "secret", "mfa_code": ""}
        options = {"URL": "de_url", "update_interval": 24}

    hass = DummyHass(str(tmp_path))
    data_coordinator = IstaDataUpdateCoordinator(hass, DummyEntry())

    class GermanController:
        def get_uuids(self) -> list[str]:
            return ["unit-1"]

        def consum_raw(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return {"last_value": {"heating": 12}}

        def get_support_code(self) -> str:
            return "support"

    async def fake_init() -> None:
        data_coordinator.controller = GermanController()

    monkeypatch.setattr(data_coordinator, "init", fake_init)

    result = asyncio.run(data_coordinator._async_update_data())

    assert result is not None
    assert result["unit-1"].to_dict() == {"last_value": {"heating": 12}}
    assert data_coordinator.czech_data is None


def test_czech_first_refresh_reuses_setup_login(monkeypatch) -> None:
    """The first refresh should not immediately repeat a successful Czech login."""

    class DummyEntry:
        entry_id = "entry"
        data = {"email": "tenant-login", "password": "secret", "mfa_code": ""}
        options = {"URL": "cz_url", "update_interval": 24}

    class CoordinatorHass:
        async def async_add_executor_job(self, func, *args: Any) -> Any:
            return func(*args)

    class LoggedInController:
        access_token = "token"

        def get_home_assistant_data(self) -> dict[str, Any]:
            return {"meters": [], "aggregates": {}}

        def get_support_code(self) -> str:
            return "cz-account"

    data_coordinator = IstaDataUpdateCoordinator(CoordinatorHass(), DummyEntry())
    data_coordinator.controller = LoggedInController()

    async def unexpected_init() -> None:
        raise AssertionError("The initial Czech login should be reused")

    async def fake_sync(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(data_coordinator, "init", unexpected_init)
    monkeypatch.setattr(coordinator, "async_sync_czech_statistics", fake_sync)

    result = asyncio.run(data_coordinator._async_update_data())

    assert result == {"meters": [], "aggregates": {}}
