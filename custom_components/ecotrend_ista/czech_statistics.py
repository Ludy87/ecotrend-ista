"""Persist and import Czech ista daily consumption statistics."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any
import unicodedata

from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_STORE_VERSION = 1
_MAX_DECIMAL_DIGITS = 32
_MAX_DECIMAL_ADJUSTED_EXPONENT = 18
_MIN_DECIMAL_EXPONENT = -12
_VOLUME_UNIT = "m³"
_VOLUME_UNIT_CLASS = "volume"
_STATISTIC_NAMES = {
    "en": {
        "heating": "Heating consumption",
        "warmwater": "Hot water consumption",
        "water": "Cold water consumption",
    },
    "cs": {
        "heating": "Spotřeba vytápění",
        "warmwater": "Spotřeba teplé vody",
        "water": "Spotřeba studené vody",
    },
}


def _slug(value: str, fallback: str) -> str:
    """Return a Home Assistant compatible slug."""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", ascii_value)).strip("_")
    return slug or fallback


def statistic_id(account_id: str, sensor_type: str) -> str:
    """Return the external statistic ID for an account and consumption type."""
    account_slug = _slug(account_id, "account")
    type_slug = _slug(sensor_type, "consumption")
    return f"{DOMAIN}:{account_slug}_{type_slug}_daily"


def _store_key(account_id: str) -> str:
    """Return the per-account Home Assistant storage key."""
    return f"{DOMAIN}.czech_statistics_{_slug(account_id, 'account')}"


def _decimal_string(value: Any) -> str | None:
    """Return a stable, bounded decimal representation or None."""
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not decimal_value.is_finite():
        return None

    _sign, digits, exponent = decimal_value.as_tuple()
    if (
        not isinstance(exponent, int)
        or len(digits) > _MAX_DECIMAL_DIGITS
        or exponent < _MIN_DECIMAL_EXPONENT
        or decimal_value.adjusted() > _MAX_DECIMAL_ADJUSTED_EXPONENT
    ):
        return None

    try:
        return format(decimal_value.normalize(), "f")
    except (InvalidOperation, ValueError):
        return None


def _finite_float(value: Decimal) -> float | None:
    """Convert a Decimal only when the recorder value remains finite."""
    try:
        float_value = float(value)
    except (OverflowError, ValueError):
        return None
    return float_value if math.isfinite(float_value) else None


def _normalize_store(stored: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize persisted data while discarding malformed values."""
    normalized: dict[str, Any] = {"types": {}}
    if not isinstance(stored, Mapping):
        return normalized

    stored_types = stored.get("types")
    if not isinstance(stored_types, Mapping):
        return normalized

    for sensor_type, stored_type in stored_types.items():
        if not isinstance(sensor_type, str) or not isinstance(stored_type, Mapping):
            continue

        unit = stored_type.get("unit")
        daily = stored_type.get("daily")
        normalized_daily: dict[str, str] = {}
        if isinstance(daily, Mapping):
            for day_value, consumption in daily.items():
                if not isinstance(day_value, str):
                    continue
                try:
                    date.fromisoformat(day_value)
                except ValueError:
                    continue
                if (decimal_value := _decimal_string(consumption)) is not None:
                    normalized_daily[day_value] = decimal_value

        normalized["types"][sensor_type] = {
            "unit": unit if isinstance(unit, str) else "",
            "daily": normalized_daily,
        }

    return normalized


def _merge_daily_history(
    stored: Mapping[str, Any] | None,
    aggregates: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, date]]:
    """Merge API values into stored history and return earliest changed dates."""
    merged = _normalize_store(stored)
    earliest_changed: dict[str, date] = {}

    for sensor_type, aggregate in aggregates.items():
        if not isinstance(sensor_type, str) or not isinstance(aggregate, Mapping):
            continue

        types = merged["types"]
        history = types.setdefault(sensor_type, {"unit": "", "daily": {}})
        daily_history: dict[str, str] = history["daily"]

        unit = aggregate.get("unit")
        if isinstance(unit, str) and unit != history["unit"]:
            history["unit"] = unit
            if daily_history:
                earliest_changed[sensor_type] = date.fromisoformat(min(daily_history))

        daily = aggregate.get("daily")
        if not isinstance(daily, list):
            continue

        for item in daily:
            if not isinstance(item, Mapping):
                continue
            day_value = item.get("date")
            if not isinstance(day_value, str):
                continue
            try:
                reading_day = date.fromisoformat(day_value)
            except ValueError:
                continue
            if (value := _decimal_string(item.get("value"))) is None:
                continue

            if daily_history.get(day_value) == value:
                continue

            daily_history[day_value] = value
            changed = earliest_changed.get(sensor_type)
            earliest_changed[sensor_type] = min(changed, reading_day) if changed else reading_day

    return merged, earliest_changed


def _statistics_timestamp(reading_day: date) -> datetime:
    """Return the aligned UTC endpoint within the consumed local calendar day."""
    interval_end = datetime.combine(
        reading_day,
        time(hour=23),
        tzinfo=dt_util.DEFAULT_TIME_ZONE,
    ).astimezone(UTC)

    # Recorder accepts only timestamps aligned to the top of an hour. 23:00 keeps
    # the completed daily value in its calendar day and Czech zones are aligned.
    return interval_end.replace(minute=0, second=0, microsecond=0)


def _build_statistics(
    daily_history: Mapping[str, str],
    earliest_changed: date,
) -> list[StatisticData]:
    """Build cumulative statistics, including all history in every running sum."""
    statistics: list[StatisticData] = []
    running_sum = Decimal("0")

    for day_value in sorted(daily_history):
        try:
            reading_day = date.fromisoformat(day_value)
        except ValueError:
            continue
        decimal_text = _decimal_string(daily_history[day_value])
        if decimal_text is None:
            continue

        daily_decimal = Decimal(decimal_text)
        candidate_sum = running_sum + daily_decimal
        daily_value = _finite_float(daily_decimal)
        sum_value = _finite_float(candidate_sum)
        if daily_value is None or sum_value is None:
            continue

        running_sum = candidate_sum
        if reading_day < earliest_changed:
            continue

        statistics.append(
            {
                "start": _statistics_timestamp(reading_day),
                "state": daily_value,
                "sum": sum_value,
            }
        )

    return statistics


def _metadata(
    account_id: str,
    sensor_type: str,
    unit: str,
    language: str = "en",
) -> StatisticMetaData:
    """Build recorder metadata for one daily consumption type."""
    language_code = language.replace("_", "-").partition("-")[0].casefold()
    names = _STATISTIC_NAMES.get(language_code, _STATISTIC_NAMES["en"])
    statistic_name = names.get(sensor_type, f"{sensor_type.title()} consumption")
    return {
        "mean_type": StatisticMeanType.NONE,
        "has_sum": True,
        "name": f"ista EcoTrend {statistic_name}",
        "source": DOMAIN,
        "statistic_id": statistic_id(account_id, sensor_type),
        "unit_class": _VOLUME_UNIT_CLASS if unit == _VOLUME_UNIT else None,
        "unit_of_measurement": unit or None,
    }


async def async_sync_czech_statistics(
    hass: HomeAssistant,
    account_id: str,
    aggregates: Mapping[str, Any],
) -> None:
    """Merge persisted daily values and upsert changed statistics into recorder."""
    components = getattr(getattr(hass, "config", None), "components", ())
    if "recorder" not in components:
        return
    language = str(getattr(hass.config, "language", "en"))

    store = Store(hass, _STORE_VERSION, _store_key(account_id))
    stored = await store.async_load()
    merged, earliest_changed = _merge_daily_history(stored, aggregates)
    if not earliest_changed:
        return

    for sensor_type, changed_from in earliest_changed.items():
        history = merged["types"][sensor_type]
        statistics = _build_statistics(history["daily"], changed_from)
        if statistics:
            async_add_external_statistics(
                hass,
                _metadata(account_id, sensor_type, history["unit"], language),
                statistics,
            )

    await store.async_save(merged)
