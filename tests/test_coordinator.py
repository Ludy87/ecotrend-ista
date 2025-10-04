"""Tests for coordinator helpers."""

from __future__ import annotations

import json
import os
import asyncio
from pathlib import Path
from typing import Any


from custom_components.ecotrend_ista.coordinator import create_directory_file


class DummyConfig:
    """Provide a minimal config object with a path helper."""

    def __init__(self, base: str) -> None:
        self._base = base

    def path(self, *paths: str) -> str:
        return os.path.join(self._base, *paths)


class DummyHass:
    """Simplified hass object for coordinator tests."""

    def __init__(self, base: str) -> None:
        self.config = DummyConfig(base)

    async def async_add_executor_job(self, func, *args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)


class DummyRaw:
    """Minimal replacement for the CustomRaw object."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, Any]:
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
