"""Tests for Czech ista recorder statistics."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

from custom_components.ecotrend_ista import czech_statistics
from custom_components.ecotrend_ista.const import DOMAIN


def test_merge_daily_history_retains_older_values_and_tracks_correction() -> None:
    """Corrections should only replace matching days and retain all other history."""
    stored = {
        "types": {
            "heating": {
                "unit": "Dílků",
                "daily": {
                    "2025-01-01": "1",
                    "2025-01-02": "2",
                    "2025-01-03": "3",
                },
            },
            "water": {
                "unit": "m³",
                "daily": {"2024-12-31": "0.5"},
            },
        }
    }
    aggregates = {
        "heating": {
            "unit": "Dílků",
            "daily": [
                {"date": "2025-01-02", "value": "2.5"},
                {"date": "2025-01-04", "value": "4"},
            ],
        }
    }

    merged, earliest_changed = czech_statistics._merge_daily_history(stored, aggregates)

    assert merged["types"]["heating"]["daily"] == {
        "2025-01-01": "1",
        "2025-01-02": "2.5",
        "2025-01-03": "3",
        "2025-01-04": "4",
    }
    assert merged["types"]["water"] == stored["types"]["water"]
    assert earliest_changed == {"heating": date(2025, 1, 2)}


def test_build_statistics_uses_complete_history_for_stable_running_sum() -> None:
    """A partial reimport should still include values preceding the changed day."""
    statistics = czech_statistics._build_statistics(
        {
            "2025-01-01": "1.5",
            "2025-01-02": "2.5",
            "2025-01-03": "3",
        },
        date(2025, 1, 2),
    )

    assert [item["state"] for item in statistics] == [2.5, 3.0]
    assert [item["sum"] for item in statistics] == [4.0, 7.0]
    assert [item["start"] for item in statistics] == [
        datetime(2025, 1, 2, 23, tzinfo=UTC),
        datetime(2025, 1, 3, 23, tzinfo=UTC),
    ]


def test_statistics_reject_values_that_cannot_be_stored_safely() -> None:
    """Exponent expansion and non-finite recorder floats are rejected."""
    assert czech_statistics._decimal_string("1e1000000") is None
    assert czech_statistics._decimal_string("1e400") is None
    assert czech_statistics._decimal_string("NaN") is None

    statistics = czech_statistics._build_statistics(
        {
            "2025-01-01": "1e400",
            "2025-01-02": "2",
        },
        date(2025, 1, 1),
    )

    assert [item["state"] for item in statistics] == [2.0]
    assert [item["sum"] for item in statistics] == [2.0]


def test_statistic_metadata_has_stable_id_and_volume_unit_class() -> None:
    """Recorder metadata should use a valid external ID and an explicit unit class."""
    metadata = czech_statistics._metadata("Český účet / 42", "warmwater", "m³")

    assert metadata == {
        "mean_type": czech_statistics.StatisticMeanType.NONE,
        "has_sum": True,
        "name": "ista EcoTrend Hot water consumption",
        "source": DOMAIN,
        "statistic_id": f"{DOMAIN}:cesky_ucet_42_warmwater_daily",
        "unit_class": "volume",
        "unit_of_measurement": "m³",
    }
    assert czech_statistics._metadata("account", "warmwater", "m³", "cs")["name"] == ("ista EcoTrend Spotřeba teplé vody")
    assert czech_statistics._metadata("account", "heating", "jednotek", "cs")["name"] == ("ista EcoTrend Spotřeba vytápění")
    assert czech_statistics._metadata("account", "heating", "Dílků")["unit_class"] is None


def test_statistics_timestamp_stays_in_the_local_calendar_day(monkeypatch) -> None:
    """A daily interval should remain in its consumed local calendar day."""
    monkeypatch.setattr(
        czech_statistics.dt_util,
        "DEFAULT_TIME_ZONE",
        timezone(timedelta(hours=2)),
    )

    timestamp = czech_statistics._statistics_timestamp(date(2025, 3, 30))

    assert timestamp == datetime(2025, 3, 30, 21, tzinfo=UTC)
    assert timestamp.minute == timestamp.second == timestamp.microsecond == 0


def test_async_sync_reimports_correction_and_future_sums(monkeypatch) -> None:
    """A correction should upsert its timestamp and every affected later cumulative sum."""

    class FakeConfig:
        components = {"recorder"}

    class FakeHass:
        config = FakeConfig()

    class FakeStore:
        loaded = {
            "types": {
                "water": {
                    "unit": "m³",
                    "daily": {
                        "2025-01-01": "1",
                        "2025-01-02": "2",
                        "2025-01-03": "3",
                    },
                }
            }
        }
        saved: dict[str, Any] | None = None
        key: str | None = None

        def __init__(self, _hass: Any, _version: int, key: str) -> None:
            type(self).key = key

        async def async_load(self) -> dict[str, Any]:  # NOSONAR - Fake mirrors Home Assistant's async Store API.
            return self.loaded

        async def async_save(  # NOSONAR - Fake mirrors Home Assistant's async Store API.
            self, data: dict[str, Any]
        ) -> None:
            type(self).saved = data

    imports: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []

    def capture_import(_hass: Any, metadata: dict[str, Any], statistics: list[dict[str, Any]]) -> None:
        imports.append((metadata, statistics))

    monkeypatch.setattr(czech_statistics, "Store", FakeStore)
    monkeypatch.setattr(czech_statistics, "async_add_external_statistics", capture_import)

    asyncio.run(
        czech_statistics.async_sync_czech_statistics(
            FakeHass(),
            "Support CZ",
            {
                "water": {
                    "unit": "m³",
                    "daily": [{"date": "2025-01-02", "value": "5"}],
                }
            },
        )
    )

    assert FakeStore.key == f"{DOMAIN}.czech_statistics_support_cz"
    assert FakeStore.saved["types"]["water"]["daily"]["2025-01-02"] == "5"
    assert len(imports) == 1
    metadata, statistics = imports[0]
    assert metadata["statistic_id"] == f"{DOMAIN}:support_cz_water_daily"
    assert [item["start"] for item in statistics] == [
        datetime(2025, 1, 2, 23, tzinfo=UTC),
        datetime(2025, 1, 3, 23, tzinfo=UTC),
    ]
    assert [item["sum"] for item in statistics] == [6.0, 9.0]


def test_async_sync_skips_when_recorder_is_not_loaded(monkeypatch) -> None:
    """Statistics synchronization should be harmless without recorder."""

    class FakeConfig:
        components: set[str] = set()

    class FakeHass:
        config = FakeConfig()

    class UnexpectedStore:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("Store must not be opened without recorder")

    monkeypatch.setattr(czech_statistics, "Store", UnexpectedStore)

    asyncio.run(czech_statistics.async_sync_czech_statistics(FakeHass(), "account", {}))
