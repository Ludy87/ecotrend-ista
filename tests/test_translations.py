"""Tests for custom integration translations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "ecotrend_ista"
TRANSLATIONS = INTEGRATION / "translations"


def _translation(language: str) -> dict[str, Any]:
    """Load one integration translation file."""
    with (TRANSLATIONS / f"{language}.json").open(encoding="utf-8") as translation_file:
        return json.load(translation_file)


def _key_paths(value: dict[str, Any], prefix: str = "") -> set[str]:
    """Return every nested translation key path."""
    paths: set[str] = set()
    for key, nested_value in value.items():
        path = f"{prefix}.{key}" if prefix else key
        paths.add(path)
        if isinstance(nested_value, dict):
            paths.update(_key_paths(nested_value, path))
    return paths


def test_english_and_czech_expose_the_same_czech_sensor_translation_keys() -> None:
    """Every Czech sensor name must be available in both supported languages."""
    english_translation = _translation("en")
    czech_translation = _translation("cs")
    assert _key_paths(english_translation) == _key_paths(czech_translation)

    english = english_translation["entity"]["sensor"]
    czech = czech_translation["entity"]["sensor"]

    assert set(english) == set(czech)
    assert len(english) == 13
    assert english["czech_heating_meter"]["name"] == "Heating meter reading – {detail}"
    assert czech["czech_heating_meter"]["name"] == "Stav měřidla topení – {detail}"
    assert english["czech_cold_water_daily"]["name"] == "Cold water – latest day"
    assert czech["czech_cold_water_daily"]["name"] == "Studená voda – poslední den"
    assert czech["czech_data_through"]["name"] == "Data dostupná do"
    assert english["czech_heating_meter"]["unit_of_measurement"] == "units"
    assert czech["czech_heating_meter"]["unit_of_measurement"] == "jednotek"


def test_login_identifier_labels_allow_email_and_username() -> None:
    """The shared login field must describe both backend identifier formats."""
    english = _translation("en")["config"]["step"]["german"]["data"]
    czech = _translation("cs")["config"]["step"]["german"]["data"]

    assert english["email"] == "Email address or username"
    assert czech["email"] == "E-mail nebo uživatelské jméno"


def test_setup_field_labels_match_base_strings_in_both_languages() -> None:
    """Every setup field must have a base, English and Czech label."""
    with (INTEGRATION / "strings.json").open(encoding="utf-8") as strings_file:
        base = json.load(strings_file)["config"]["step"]["german"]["data"]

    english = _translation("en")["config"]["step"]["german"]["data"]
    czech = _translation("cs")["config"]["step"]["german"]["data"]

    assert set(base) == set(english) == set(czech)
