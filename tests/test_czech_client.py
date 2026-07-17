"""Tests for the Czech/Nordic ista client adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from custom_components.ecotrend_ista.czech_client import (
    CZECH_METERS_URL,
    CZECH_READING_URL,
    CZECH_TOKEN_URL,
    CzechPyEcotrendIsta,
    _login_proofs,
)


class FakeResponse:
    """Minimal requests response used by the adapter tests."""

    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        """Store a JSON payload and HTTP status."""
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        """Return the configured JSON body."""
        return self._payload

    def raise_for_status(self) -> None:
        """Raise when the configured status represents an error."""
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Return deterministic token, meter and reading responses."""

    def __init__(self) -> None:
        """Initialize request capture collections."""
        self.headers: dict[str, str] = {}
        self.post_calls: list[tuple[str, dict[str, Any]]] = []
        self.get_calls: list[tuple[str, dict[str, str]]] = []

    def post(self, url: str, *, data: dict[str, Any], timeout: int) -> FakeResponse:
        """Return a successful Czech token response."""
        self.post_calls.append((url, data))
        assert timeout == 30
        return FakeResponse(
            {
                "access_token": "access-token",
                "InstanceId": 42,
                "FirstName": "Test",
                "Email": "test@example.com",
                "Language": "cs-CZ",
            }
        )

    def get(self, url: str, *, headers: dict[str, str], timeout: int) -> FakeResponse:
        """Return meters or chart readings for the requested URL."""
        self.get_calls.append((url, headers))
        assert timeout == 30
        if url == CZECH_METERS_URL:
            return FakeResponse(
                {
                    "Meters": {
                        "Value": [
                            {
                                "MeterType": "HCA",
                                "Unit": "díl",
                                "METER_ID": 101.0,
                                "METER_NO": "H-1",
                                "INST_NO": 1,
                                "ROOM_DESCR": "Obývací pokoj",
                                "Headline": "Topení",
                                "METCAT_LABEL": "Rozdělovač topných nákladů",
                                "Last_Meter_Reading": "120,5",
                                "Last_Meter_Consumption": "8,5",
                                "Reading_date": "2026-07-10",
                            },
                            {
                                "MeterType": "HCA",
                                "Unit": "díl",
                                "METER_ID": 102,
                                "METER_NO": "H-2",
                                "INST_NO": 2,
                                "ROOM_DESCR": "Ložnice",
                                "Headline": "Topení",
                                "Last_Meter_Reading": 80,
                                "Last_Meter_Consumption": 4,
                                "Reading_date": "2026-07-10",
                            },
                            {
                                "MeterType": "HCA",
                                "Unit": "díl",
                                "METER_ID": 103,
                                "METER_NO": "H-3",
                                "INST_NO": 3,
                                "ROOM_DESCR": "Pokoj",
                                "Headline": "Topení",
                                "Last_Meter_Reading": 60,
                                "Last_Meter_Consumption": 3,
                                "Reading_date": "2026-07-10",
                            },
                            {
                                "MeterType": "HW",
                                "Unit": "m3",
                                "METER_ID": 201,
                                "METER_NO": "TV-1",
                                "INST_NO": 4,
                                "ROOM_DESCR": "Koupelna",
                                "Headline": "Teplá voda",
                                "Last_Meter_Reading": "12,3",
                                "Last_Meter_Consumption": "0,75",
                                "Reading_date": "2026-07-10",
                            },
                            {
                                "MeterType": "CW",
                                "Unit": "m3",
                                "METER_ID": 202,
                                "METER_NO": "SV-1",
                                "INST_NO": 5,
                                "ROOM_DESCR": "Koupelna",
                                "Headline": "Studená voda",
                                "Last_Meter_Reading": 24,
                                "Last_Meter_Consumption": 2,
                                "Reading_date": "2026-07-10",
                            },
                        ]
                    }
                }
            )
        if url.endswith("/hca"):
            if "/4/" in url:
                return FakeResponse(
                    {
                        "readingsList": {
                            "Value": {
                                "Unit": "díl",
                                "Readings": [
                                    {
                                        "Date": "2026-07-01T00:00:00",
                                        "Value": "1,25",
                                        "AkkumulativValue": "100,0",
                                    },
                                    {
                                        "Date": "2026-07-02T00:00:00",
                                        "Value": "2,75",
                                        "AkkumulativValue": "102,75",
                                    },
                                ],
                            }
                        }
                    }
                )
            return FakeResponse(
                {
                    "readingsList": {
                        "Value": {
                            "Unit": "díl",
                            "Readings": [{"Date": "2026-07-01T00:00:00", "Value": "8,5"}],
                        }
                    }
                }
            )
        if url.endswith("/hw"):
            if "/4/" in url:
                return FakeResponse(
                    {
                        "readingsList": {
                            "Value": {
                                "Unit": "m³",
                                "Readings": [
                                    {
                                        "Date": "2026-07-01T00:00:00",
                                        "Value": "0,1",
                                        "AkkumulativValue": "10,1",
                                    },
                                    {
                                        "Date": "2026-07-02T00:00:00",
                                        "Value": "0,2",
                                        "AkkumulativValue": "10,3",
                                    },
                                ],
                            }
                        }
                    }
                )
            return FakeResponse(
                {
                    "readingsList": {
                        "Value": {
                            "Unit": "m3",
                            "Readings": [{"Date": "2026-07-01T00:00:00", "Value": "0,75"}],
                        }
                    }
                }
            )
        if url.endswith("/cw"):
            if "/4/" in url:
                return FakeResponse(
                    {
                        "readingsList": {
                            "Value": {
                                "Unit": "m³",
                                "Readings": [
                                    {
                                        "Date": "2026-07-01T00:00:00",
                                        "Value": 1,
                                        "AkkumulativValue": 20,
                                    },
                                    {
                                        "Date": "2026-07-02T00:00:00",
                                        "Value": 2,
                                        "AkkumulativValue": 22,
                                    },
                                ],
                            }
                        }
                    }
                )
            return FakeResponse(
                {
                    "readingsList": {
                        "Value": {
                            "Unit": "m³",
                            "Readings": [{"Date": "/Date(1782864000000)/", "Value": 2}],
                        }
                    }
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")


def test_login_proofs_match_captured_web_client_request() -> None:
    """The implementation must stay byte-compatible with the public WebGL client."""

    value1, value2 = _login_proofs(
        "codex-invalid-user",
        "invalid-password",
        datetime(2026, 7, 16, 12, 52, 16),
    )

    assert value1 == (
        "_29_52_239_8_77_180_114_223_83_241_34_104_193_176_21_187"
        "_62_46_46_224_141_159_219_13_137_15_254_249_205_176_109_42"
        "_123_135_165_8_55_27_122_174_165_10_243_102_97_93_135_24"
    )
    assert value2 == (
        "_117_59_26_69_252_242_214_228_128_238_132_124_149_96_74_154"
        "_102_222_40_40_212_151_205_51_51_128_143_51_21_208_18_58"
        "_205_162_56_12_7_238_110_252_71_130_245_72_5_101_22_81"
    )


def test_login_and_normalize_readings() -> None:
    """Token, meters and chart data are translated to the existing consumption shape."""

    session = FakeSession()
    client = CzechPyEcotrendIsta("tenant-login", "secret", session=session)

    client.login()
    consumption_data = client.get_consumption_data()

    assert session.post_calls[0][0] == CZECH_TOKEN_URL
    token_form = session.post_calls[0][1]
    assert set(token_form) == {"grant_type", "username", "password", "value1", "value2"}
    assert token_form["username"] == "tenant-login"
    assert client.access_token == "access-token"
    assert client.get_uuids() == ["cz-42"]
    assert all(headers == {"Authorization": "bearer access-token"} for _, headers in session.get_calls)
    assert all(
        url == CZECH_METERS_URL or url.startswith(f"{CZECH_READING_URL}/")
        for url, _ in session.get_calls
    )
    assert all("/2/" in url for url, _ in session.get_calls if url != CZECH_METERS_URL)

    readings = {reading["type"]: reading for reading in consumption_data["consumptions"][0]["readings"]}
    assert readings["heating"]["value"] == "8.5"
    assert readings["heating"]["unit"] == "díl"
    assert readings["warmwater"]["value"] == "0.75"
    assert readings["warmwater"]["unit"] == "m³"
    assert readings["water"]["value"] == "2"
    assert readings["water"]["unit"] == "m³"


def test_home_assistant_data_exposes_five_meters_and_aggregate_periods() -> None:
    """The Czech account exposes physical meters plus daily and monthly aggregate sensors."""

    session = FakeSession()
    client = CzechPyEcotrendIsta("tenant-login", "secret", session=session)

    client.login()
    home_data = client.get_home_assistant_data()

    assert len(home_data["meters"]) == 5
    assert [meter["id"] for meter in home_data["meters"]] == ["101", "102", "103", "201", "202"]
    assert [meter["type"] for meter in home_data["meters"]] == [
        "heating",
        "heating",
        "heating",
        "warmwater",
        "water",
    ]
    assert home_data["meters"][0]["room"] == "Obývací pokoj"
    assert home_data["meters"][0]["value"] == "120.5"
    assert home_data["meters"][3]["last_consumption"] == "0.75"

    aggregates = home_data["aggregates"]
    assert aggregates["heating"]["daily_value"] == "2.75"
    assert aggregates["heating"]["monthly_value"] == "4"
    assert aggregates["warmwater"]["monthly_value"] == "0.3"
    assert aggregates["water"]["monthly_value"] == "3"
    assert aggregates["water"]["daily"][-1] == {
        "date": "2026-07-02",
        "value": "2",
        "cumulative_value": "22",
    }

    daily_urls = [
        url
        for url, _headers in session.get_calls
        if url.startswith(f"{CZECH_READING_URL}/") and "/4/" in url
    ]
    assert len(daily_urls) == 3
    assert sum(url.endswith("/hca") for url in daily_urls) == 1

    monthly_data = client.get_consumption_data()
    assert not any(
        url.startswith(f"{CZECH_READING_URL}/") and "/2/" in url
        for url, _headers in session.get_calls
    )
    monthly_readings = {
        reading["type"]: reading
        for reading in monthly_data["consumptions"][0]["readings"]
    }
    assert monthly_readings["heating"]["value"] == "4"
    assert monthly_readings["warmwater"]["value"] == "0.3"
    assert monthly_readings["water"]["value"] == "3"
