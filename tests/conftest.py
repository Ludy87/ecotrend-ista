"""Test configuration and module stubs for the ecotrend_ista integration."""

from __future__ import annotations

import sys
import types
from enum import Enum
from pathlib import Path
from typing import Any


def _create_module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__dict__["__package__"] = name
    return module


def _ensure_module(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    parent_name, _, child_name = name.rpartition(".")
    module = _create_module(name)
    if parent_name:
        parent = _ensure_module(parent_name)
        setattr(parent, child_name, module)
        if not hasattr(parent, "__path__"):
            parent.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = module
    module.__path__ = []  # type: ignore[attr-defined]
    return module


# Stub homeassistant modules that are required for importing the integration.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_homeassistant = _ensure_module("homeassistant")

config_entries = _ensure_module("homeassistant.config_entries")
config_entries.SOURCE_IMPORT = "import"


class _BaseFlow:
    """Base class used for config and options flow stubs."""

    def __init_subclass__(cls, **kwargs: Any) -> None:  # type: ignore[override]
        kwargs.pop("domain", None)
        super().__init_subclass__(**kwargs)

    async def async_show_form(self, **kwargs: Any):  # pragma: no cover - helper for completeness
        return kwargs

    async def async_set_unique_id(self, _unique_id: str) -> None:  # pragma: no cover - helper for completeness
        return None

    def _abort_if_unique_id_configured(self) -> None:  # pragma: no cover - helper for completeness
        return None

    def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:  # pragma: no cover - helper for completeness
        return kwargs


class ConfigFlow(_BaseFlow):
    """Stub for ConfigFlow."""


class OptionsFlow(_BaseFlow):
    """Stub for OptionsFlow."""


class OptionsFlowWithConfigEntry(_BaseFlow):
    """Stub for OptionsFlowWithConfigEntry."""


class ConfigEntry:  # pragma: no cover - behaviour not required for tests
    """Stub for ConfigEntry."""


config_entries.ConfigFlow = ConfigFlow
config_entries.OptionsFlow = OptionsFlow
config_entries.OptionsFlowWithConfigEntry = OptionsFlowWithConfigEntry
config_entries.ConfigEntry = ConfigEntry

core = _ensure_module("homeassistant.core")


def callback(func):
    """Return the decorated function unchanged."""

    return func


class HomeAssistant:  # pragma: no cover - behaviour provided via tests
    """Placeholder HomeAssistant type used for typing."""


core.callback = callback
core.HomeAssistant = HomeAssistant

const = _ensure_module("homeassistant.const")
const.CONF_EMAIL = "email"
const.CONF_PASSWORD = "password"
const.CONF_SCAN_INTERVAL = "scan_interval"


class Platform(str, Enum):
    """Mimic Home Assistant's Platform enum with the attributes required by the integration."""

    SENSOR = "sensor"


const.Platform = Platform

helpers = _ensure_module("homeassistant.helpers")
selector = _ensure_module("homeassistant.helpers.selector")
entity_registry = _ensure_module("homeassistant.helpers.entity_registry")
helpers.entity_registry = entity_registry


class RegistryEntry:
    """Simplified registry entry used during migration tests."""

    def __init__(self, *, entity_id: str = "", unique_id: str = "", domain: str = "sensor", platform: str = "sensor") -> None:
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.domain = domain
        self.platform = platform


class _EntityRegistry:
    """Minimal entity registry implementation."""

    def async_get_entity_id(self, _domain: str, _platform: str, _unique_id: str) -> None:
        return None


async def async_migrate_entries(*_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - behaviour not exercised
    return None


def async_get(_hass: Any) -> _EntityRegistry:
    return _EntityRegistry()


entity_registry.RegistryEntry = RegistryEntry
entity_registry.async_get = async_get
entity_registry.async_migrate_entries = async_migrate_entries


class NumberSelectorMode:
    """Stub enum representing selector mode values."""

    SLIDER = "slider"


class NumberSelectorConfig:
    """Store configuration for a number selector."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs


class NumberSelector:
    """Stub for the Home Assistant NumberSelector."""

    def __init__(self, _config: NumberSelectorConfig) -> None:
        self.config = _config


class SelectSelectorMode:
    """Stub enum representing select selector modes."""

    DROPDOWN = "dropdown"


class SelectOptionDict(dict):
    """Simple dictionary implementation matching Home Assistant's structure."""

    def __init__(self, *, value: str, label: str) -> None:
        super().__init__(value=value, label=label)


class SelectSelectorConfig:
    """Configuration for a select selector."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs


class SelectSelector:
    """Stub for the SelectSelector."""

    def __init__(self, _config: SelectSelectorConfig) -> None:
        self.config = _config


class TextSelectorType:
    """Stub enum representing text selector types."""

    EMAIL = "email"
    PASSWORD = "password"
    TEXT = "text"


class TextSelectorConfig:
    """Configuration container for text selectors."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs


class TextSelector:
    """Stub for the TextSelector."""

    def __init__(self, _config: TextSelectorConfig) -> None:
        self.config = _config


selector.NumberSelector = NumberSelector
selector.NumberSelectorConfig = NumberSelectorConfig
selector.NumberSelectorMode = NumberSelectorMode
selector.SelectSelector = SelectSelector
selector.SelectSelectorConfig = SelectSelectorConfig
selector.SelectSelectorMode = SelectSelectorMode
selector.SelectOptionDict = SelectOptionDict
selector.TextSelector = TextSelector
selector.TextSelectorConfig = TextSelectorConfig
selector.TextSelectorType = TextSelectorType
helpers.selector = selector

update_coordinator = _ensure_module("homeassistant.helpers.update_coordinator")


class DataUpdateCoordinator:
    """Simplified DataUpdateCoordinator stub."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.hass = kwargs.get("hass")
        self.logger = kwargs.get("logger")
        self.name = kwargs.get("name")
        self.update_method = kwargs.get("update_method")
        self.update_interval = kwargs.get("update_interval")
        self.data: dict[str, Any] | None = None

    def async_set_updated_data(self, data: dict[str, Any]) -> None:
        """Store updated data."""

        self.data = data


update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
helpers.update_coordinator = update_coordinator

helpers_typing = _ensure_module("homeassistant.helpers.typing")
helpers_typing.ConfigType = dict[str, Any]

data_entry_flow = _ensure_module("homeassistant.data_entry_flow")
data_entry_flow.FlowResult = dict
homeassistant_data_entry_flow = data_entry_flow

helpers.selector = selector
helpers.update_coordinator = update_coordinator


_data_entry_flow = _ensure_module("homeassistant.data_entry_flow")
_data_entry_flow.FlowResult = dict


# Stub external library used by the integration.
pyecotrend_ista = _ensure_module("pyecotrend_ista")

exception_classes = _ensure_module("pyecotrend_ista.exception_classes")


class LoginError(Exception):
    """Placeholder LoginError matching the external library's API."""


exception_classes.LoginError = LoginError

helper_object_de = _ensure_module("pyecotrend_ista.helper_object_de")


class CustomRaw:
    """Lightweight stand-in for the CustomRaw helper object."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomRaw":
        return cls(data)

    def to_dict(self) -> dict[str, Any]:
        return self._data


helper_object_de.CustomRaw = CustomRaw

py_module = _ensure_module("pyecotrend_ista.pyecotrend_ista")


class PyEcotrendIsta:  # pragma: no cover - replaced by tests when required
    """Minimal stub for the external API client."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def login(self) -> None:  # pragma: no cover - replaced by monkeypatch in tests
        raise NotImplementedError

    def get_support_code(self) -> str:  # pragma: no cover - default helper
        return "SC"

    def getUUIDs(self) -> list[str]:  # pragma: no cover - not used
        return []

    def consum_raw(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:  # pragma: no cover - not used
        return {}


py_module.PyEcotrendIsta = PyEcotrendIsta

pyecotrend_ista.exception_classes = exception_classes
pyecotrend_ista.helper_object_de = helper_object_de
pyecotrend_ista.pyecotrend_ista = py_module


# Provide a light-weight voluptuous substitute used by the integration during imports.
voluptuous = _ensure_module("voluptuous")


class Invalid(Exception):
    """Exception raised when validation fails."""


def Email():
    """Return a validator checking for a simple '@' based email."""

    def _validator(value: Any) -> str:
        if value is None or "@" not in value:
            raise Invalid("invalid email")
        return value

    return _validator


def Schema(schema: Any, **_kwargs: Any) -> Any:  # pragma: no cover - behaviour not required for tests
    return schema


def Required(key: Any, default: Any | None = None) -> Any:  # pragma: no cover - helper for schema construction
    return key


def Optional(key: Any, default: Any | None = None) -> Any:  # pragma: no cover - helper for schema construction
    return key


def Remove(key: Any) -> Any:  # pragma: no cover - helper for schema construction
    return key


def Any(*values: Any) -> Any:  # pragma: no cover - helper for schema construction
    return values


voluptuous.Invalid = Invalid
voluptuous.Email = Email
voluptuous.Schema = Schema
voluptuous.Required = Required
voluptuous.Optional = Optional
voluptuous.Remove = Remove
voluptuous.Any = Any
voluptuous.ALLOW_EXTRA = object()


requests = _ensure_module("requests")


class Timeout(Exception):
    """Placeholder timeout exception."""


class ReadTimeout(Timeout):
    """Placeholder read timeout exception."""


class ConnectionError(Exception):
    """Placeholder connection error exception."""


class Session:  # pragma: no cover - only used for instantiation
    """Minimal requests Session stub."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


requests.Session = Session
requests.Timeout = Timeout
requests.ReadTimeout = ReadTimeout
requests.ConnectionError = ConnectionError
