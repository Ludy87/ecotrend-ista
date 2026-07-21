"""Tests for the config flow helper utilities."""

from __future__ import annotations

import asyncio
from types import MappingProxyType
from typing import Any

from custom_components.ecotrend_ista import config_flow
from custom_components.ecotrend_ista.config_flow import NotSupportedURL, validate_input, validate_options_input
import pytest


class DummyHass:
    """Lightweight HomeAssistant stand-in for tests."""

    async def async_add_executor_job(self, func, *args: Any, **kwargs: Any) -> Any:
        """Run a synchronous callable immediately."""
        return func(*args, **kwargs)


@pytest.fixture
def valid_user_input() -> dict[str, Any]:
    """Provide a baseline of valid user input values."""

    return {
        "email": "user@example.com",
        "password": "secret",
        "URL": "de_url",
        "mfa_code": "123456",
        "update_interval": 12,
    }


def test_validate_input_success(monkeypatch: pytest.MonkeyPatch, valid_user_input: dict[str, Any]) -> None:
    """A successful validation should return the title provided by the API client."""

    hass = DummyHass()

    class DummyAccount:
        def login(self) -> str:
            return "Demo"

        def get_support_code(self) -> str:
            return "SC123"

    def fake_login_account(_hass, data: MappingProxyType[str, Any], demo: bool = False) -> DummyAccount:
        assert demo is False
        assert data["email"] == valid_user_input["email"]
        return DummyAccount()

    monkeypatch.setattr(config_flow, "login_account", fake_login_account)

    result = asyncio.run(validate_input(hass, valid_user_input))

    assert result == {"title": "Ista SC123 Demo"}


def test_validate_input_rejects_unknown_url(valid_user_input: dict[str, Any]) -> None:
    """An unsupported URL value should raise NotSupportedURL."""

    hass = DummyHass()
    invalid_input = dict(valid_user_input)
    invalid_input["URL"] = "invalid"

    with pytest.raises(NotSupportedURL):
        asyncio.run(validate_input(hass, invalid_input))


def test_validate_input_propagates_login_error(monkeypatch: pytest.MonkeyPatch, valid_user_input: dict[str, Any]) -> None:
    """Errors from the API login should bubble up for the flow to handle."""

    hass = DummyHass()

    class DummyAccount:
        def login(self) -> None:
            raise config_flow.LoginError("bad credentials")

    monkeypatch.setattr(config_flow, "login_account", lambda *args, **kwargs: DummyAccount())

    with pytest.raises(config_flow.LoginError):
        asyncio.run(validate_input(hass, valid_user_input))


def test_validate_input_accepts_czech_username(monkeypatch: pytest.MonkeyPatch, valid_user_input: dict[str, Any]) -> None:
    """The Czech backend accepts account names that are not email addresses."""

    class DummyAccount:
        def login(self) -> None:
            return None

        def get_support_code(self) -> str:
            return "cz-123"

    czech_input = dict(valid_user_input, email="tenant-login", URL="cz_url")
    monkeypatch.setattr(config_flow, "login_account", lambda *args, **kwargs: DummyAccount())

    result = asyncio.run(validate_input(DummyHass(), czech_input))

    assert result == {"title": "Ista cz-123 "}


def test_login_account_uses_czech_client(monkeypatch: pytest.MonkeyPatch, valid_user_input: dict[str, Any]) -> None:
    """The selected URL must control which client implementation is created."""

    captured: dict[str, Any] = {}

    class DummyCzechClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(config_flow, "CzechPyEcotrendIsta", DummyCzechClient)
    czech_input = dict(valid_user_input, email="tenant-login", URL="cz_url")

    account = config_flow.login_account(DummyHass(), czech_input)

    assert isinstance(account, DummyCzechClient)
    assert captured["email"] == "tenant-login"
    assert captured["password"] == "secret"


def test_validate_options_input_returns_no_errors(valid_user_input: dict[str, Any]) -> None:
    """The option validation should accept the supported URL."""

    assert validate_options_input({"URL": "de_url"}) == {}
    assert validate_options_input({"URL": "cz_url"}) == {}


def test_validate_options_input_rejects_invalid_url() -> None:
    """An unsupported URL produces an error message."""

    assert validate_options_input({"URL": "other"}) == {"base": "not_allowed"}


def test_options_flow_preserves_portal_without_offering_a_backend_switch() -> None:
    """Changing the refresh interval must preserve the validated login portal."""
    flow = config_flow.IstaOptionsFlowHandler()
    flow.options = {"URL": "cz_url", "update_interval": 24}

    result = asyncio.run(flow.async_step_init({"update_interval": 12}))

    assert result["data"] == {"URL": "cz_url", "update_interval": 12}
