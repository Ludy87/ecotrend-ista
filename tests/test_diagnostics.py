"""Tests for privacy-safe integration diagnostics."""

from __future__ import annotations

from custom_components.ecotrend_ista.diagnostics import _czech_diagnostics


def test_czech_diagnostics_omit_meter_identifiers_rooms_values_and_history() -> None:
    """Czech diagnostics must expose structure without household consumption data."""
    diagnostics = _czech_diagnostics(
        {
            "meters": [
                {
                    "id": "secret-meter-id",
                    "type": "heating",
                    "meter_number": "123456",
                    "installation_number": "987654",
                    "room": "Bedroom",
                    "value": "428",
                }
            ],
            "aggregates": {
                "heating": {
                    "unit": "jednotek",
                    "daily": [{"date": "2026-07-10", "value": "1"}],
                    "monthly": [{"year": 2026, "month": 7, "value": "20"}],
                    "daily_value": "1",
                    "monthly_value": "20",
                }
            },
        }
    )

    assert diagnostics == {
        "meter_count": 1,
        "meter_types": ["heating"],
        "aggregates": {
            "heating": {
                "unit": "jednotek",
                "daily_reading_count": 1,
                "monthly_reading_count": 1,
                "has_latest_daily_value": True,
                "has_latest_monthly_value": True,
            }
        },
    }
    serialized = repr(diagnostics)
    assert "secret-meter-id" not in serialized
    assert "123456" not in serialized
    assert "987654" not in serialized
    assert "Bedroom" not in serialized
    assert "2026-07-10" not in serialized
    assert "428" not in serialized
