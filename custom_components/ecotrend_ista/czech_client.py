"""Client adapter for the Czech/Nordic ista EcoTrend service."""

from __future__ import annotations

from collections import defaultdict
import copy
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import logging
import re
from typing import Any
from urllib.parse import quote

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pyecotrend_ista.exception_classes import LoginError
from pyecotrend_ista.pyecotrend_ista import PyEcotrendIsta
import requests

_LOGGER = logging.getLogger(__name__)

CZECH_API_BASE_URL = "https://prod.istaonlinebeta.dk/"
CZECH_TOKEN_URL = f"{CZECH_API_BASE_URL}token"
CZECH_METERS_URL = f"{CZECH_API_BASE_URL}api/Meters"
CZECH_READING_URL = f"{CZECH_API_BASE_URL}api/GetReadingData"
CZECH_APP_VERSION = "3.2.1"

_REQUEST_TIMEOUT = 30
_PERIOD_MONTHLY_HISTORY = 2
_PERIOD_DAILY_HISTORY = 4
_DOTNET_DATE = re.compile(r"^/Date\((?P<milliseconds>-?\d+)")
_LOGIN_KDF_PASSWORD = "P@%5w0r]>3mll04##22"
_LOGIN_KDF_SALT = "(&(HBB%J&Y*B1-3mll04##22"
_CUBIC_METRE_UNITS = {"cbm", "cubicmeter", "cubicmetre", "m3", "m³"}


def _value_case_insensitive(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Return a dictionary value without relying on server-side key casing."""
    wanted = key.casefold()
    for current_key, value in data.items():
        if current_key.casefold() == wanted:
            return value
    return default


def _unwrap_value(payload: Any, key: str) -> Any:
    """Unwrap the ``Type<T>.Value`` structure used by the Nordic API."""
    if not isinstance(payload, dict):
        return payload

    value = _value_case_insensitive(payload, key, payload)
    if isinstance(value, dict):
        for wrapper_key in ("Value", "_value"):
            unwrapped = _value_case_insensitive(value, wrapper_key)
            if unwrapped is not None:
                return unwrapped
    return value


def _add_months(value: date, months: int) -> date:
    """Add whole months while keeping the date valid."""
    month_index = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(month_index, 12)
    month = month_index + 1
    month_lengths = (
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    return date(year, month, min(value.day, month_lengths[month - 1]))


def _dotnet_timestamp(value: datetime) -> str:
    """Match the invariant-style ``DateTime.Now.ToString()`` used by the WebGL build."""
    hour = value.hour % 12 or 12
    suffix = "AM" if value.hour < 12 else "PM"
    return f"{value.month}/{value.day}/{value.year} {hour}:{value.minute:02}:{value.second:02} {suffix}"


def _login_proofs(username: str, password: str, now: datetime | None = None) -> tuple[str, str]:
    """Build the two encrypted form values required by the current Czech login endpoint."""
    key_material = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=96,
        salt=_LOGIN_KDF_SALT.encode("ascii"),
        iterations=1000,
    ).derive(_LOGIN_KDF_PASSWORD.encode("ascii"))

    # The Unity client first consumes one Rijndael key/IV pair, then uses the
    # second pair for AesCryptoServiceProvider and the transmitted values.
    key = key_material[48:80]
    initialization_vector = key_material[80:96]
    timestamp = _dotnet_timestamp(now or datetime.now())

    def encrypt(value: str) -> str:
        padder = padding.PKCS7(128).padder()
        padded = padder.update(f"{value}_{timestamp}".encode()) + padder.finalize()
        encryptor = Cipher(algorithms.AES(key), modes.CBC(initialization_vector)).encryptor()
        encrypted = encryptor.update(padded) + encryptor.finalize()
        return "".join(f"_{byte}" for byte in encrypted)

    return encrypt(username), encrypt(password)


def _parse_reading_date(value: Any) -> datetime | None:
    """Parse date formats emitted by the ASP.NET/Unity API."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None

    raw = value.strip()
    dotnet_match = _DOTNET_DATE.match(raw)
    if dotnet_match:
        return datetime.fromtimestamp(int(dotnet_match.group("milliseconds")) / 1000, tz=UTC)

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        pass

    for date_format in ("%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%m-%Y", "%m/%Y"):
        try:
            return datetime.strptime(raw, date_format)
        except ValueError:
            continue
    return None


def _as_decimal(value: Any) -> Decimal | None:
    """Convert API numbers, including comma-decimal strings, to Decimal."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if not isinstance(value, str):
        return None

    normalized = value.strip().replace("\u00a0", "").replace(" ", "")
    if not normalized:
        return None
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _decimal_string(value: Decimal) -> str:
    """Return a representation compatible with the existing German parser."""
    result = format(value, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return result or "0"


def _identifier_string(value: Any) -> str:
    """Return stable text for string and numeric meter identifiers."""
    if isinstance(value, str):
        return value.strip()
    decimal_value = _as_decimal(value)
    if decimal_value is not None:
        return _decimal_string(decimal_value)
    return str(value)


def _normalize_unit(value: Any, sensor_type: str) -> str:
    """Normalize water volume aliases to the Home Assistant cubic-metre unit."""
    unit = str(value or "").strip()
    compact = re.sub(r"[\s._-]+", "", unit.casefold())
    if sensor_type in {"warmwater", "water"} and compact in _CUBIC_METRE_UNITS:
        return "m³"
    return unit


def _classify_meter(meter: dict[str, Any], meter_type: str) -> str | None:
    """Map Nordic meter labels to the three sensor types supported by this integration."""
    labels = [
        meter_type,
        str(_value_case_insensitive(meter, "METTYPE_CODE", "")),
        str(_value_case_insensitive(meter, "METCAT_LABEL", "")),
        str(_value_case_insensitive(meter, "Headline", "")),
    ]
    normalized = " ".join(labels).casefold()
    compact_type = re.sub(r"[^a-z0-9]", "", meter_type.casefold())

    if compact_type in {"hw", "hotwater", "warmwater"} or (
        ("tepl" in normalized or "hot water" in normalized) and "vod" in normalized
    ):
        return "warmwater"
    if compact_type in {"cw", "coldwater", "water"} or "studen" in normalized or "cold water" in normalized:
        return "water"
    if compact_type in {"heat", "heating", "hca", "energy"} or any(
        label in normalized for label in ("teplo", "topen", "heat", "radiator")
    ):
        return "heating"
    return None


class CzechPyEcotrendIsta(PyEcotrendIsta):
    """Expose the Czech/Nordic service through the interface used by the integration."""

    def __init__(
        self,
        email: str,
        password: str,
        totp: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """Initialize the Czech client; TOTP is currently not used by this service."""
        del totp
        self._email = email.strip()
        self._password = password
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                ),
            }
        )
        self._access_token: str | None = None
        self._account: dict[str, Any] = {}
        self._meters: list[dict[str, Any]] = []
        self._consumption_cache: dict[str, Any] | None = None
        self._uuid = ""
        self._support_code = ""

    @property
    def access_token(self) -> str | None:
        """Return the current bearer token."""
        return self._access_token

    def login(self, **kwargs: Any) -> None:
        """Authenticate and load the meters available to the Czech account."""
        del kwargs
        self._consumption_cache = None
        value1, value2 = _login_proofs(self._email, self._password)
        response = self.session.post(
            CZECH_TOKEN_URL,
            data={
                "grant_type": "password",
                "username": self._email,
                "password": self._password,
                "value1": value1,
                "value2": value2,
            },
            timeout=_REQUEST_TIMEOUT,
        )
        if response.status_code in (400, 401):
            try:
                error = response.json().get("error_description", "Invalid username or password")
            except (ValueError, AttributeError):
                error = "Invalid username or password"
            raise LoginError(error)
        response.raise_for_status()

        token_data = response.json()
        access_token = _value_case_insensitive(token_data, "access_token")
        if not access_token:
            raise LoginError("The Czech ista service did not return an access token")
        self._access_token = str(access_token)

        instance_id = _value_case_insensitive(token_data, "InstanceId")
        if instance_id in (None, "", 0, "0"):
            instance_id = hashlib.sha256(self._email.encode()).hexdigest()[:12]
        self._uuid = f"cz-{instance_id}"
        self._support_code = self._uuid
        self._account = {
            "firstName": _value_case_insensitive(token_data, "FirstName", ""),
            "email": _value_case_insensitive(token_data, "Email", self._email),
            "country": "CZ",
            "locale": _value_case_insensitive(token_data, "Language", "cz"),
            "tosUpdated": None,
            "supportCode": self._support_code,
            "consumptionUnitUuids": [self._uuid],
            "residentAndConsumptionUuidsMap": {self._uuid: self._uuid},
        }
        self._meters = self._get_meters()

    def logout(self) -> None:
        """Discard the local token; the Nordic service exposes no logout call."""
        self._access_token = None

    def get_uuids(self) -> list[str]:
        """Return one account-scoped consumption unit."""
        return [self._uuid] if self._uuid else []

    def get_support_code(self) -> str:
        """Return a stable identifier for filenames and the device title."""
        return self._support_code

    def get_version(self) -> str:
        """Return the Czech web application version used to derive this adapter."""
        return f"CZ Nordic {CZECH_APP_VERSION}"

    def get_account(self) -> dict[str, Any]:
        """Return normalized account metadata expected by the entity code."""
        return self._account

    def _authorization_headers(self) -> dict[str, str]:
        if not self._access_token:
            raise LoginError("The Czech ista account is not authenticated")
        return {"Authorization": f"bearer {self._access_token}"}

    def _get_meters(self) -> list[dict[str, Any]]:
        response = self.session.get(
            CZECH_METERS_URL,
            headers=self._authorization_headers(),
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        meters = _unwrap_value(response.json(), "Meters")
        if meters is None:
            return []
        if isinstance(meters, dict):
            meters = _value_case_insensitive(meters, "meters", [])
        if not isinstance(meters, list):
            _LOGGER.warning("Unexpected Czech ista meter response: %s", type(meters).__name__)
            return []
        return [meter for meter in meters if isinstance(meter, dict)]

    def _get_readings(
        self,
        meter_type: str,
        start: date,
        end: date,
        period: int = _PERIOD_MONTHLY_HISTORY,
    ) -> dict[str, Any] | None:
        url = (
            f"{CZECH_READING_URL}/{start:%d-%m-%Y}/{end:%d-%m-%Y}/"
            f"{period}/{quote(meter_type, safe='')}"
        )
        response = self.session.get(
            url,
            headers=self._authorization_headers(),
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        readings = _unwrap_value(response.json(), "readingsList")
        return readings if isinstance(readings, dict) else None

    def get_home_assistant_data(self) -> dict[str, Any]:
        """Return physical meters and daily/monthly aggregate histories for Home Assistant."""
        if not self._meters:
            self._meters = self._get_meters()

        normalized_meters: list[dict[str, Any]] = []
        meter_types: dict[str, tuple[str, dict[str, Any]]] = {}
        for index, meter in enumerate(self._meters, start=1):
            meter_type = str(_value_case_insensitive(meter, "MeterType", "")).strip().lower()
            sensor_type = _classify_meter(meter, meter_type)
            if not meter_type or not sensor_type:
                continue
            meter_types.setdefault(meter_type.casefold(), (sensor_type, meter))

            meter_id = _value_case_insensitive(meter, "METER_ID")
            if not meter_id:
                meter_number = _value_case_insensitive(meter, "METER_NO")
                installation_number = _value_case_insensitive(meter, "INST_NO")
                fallback_parts = [
                    _identifier_string(part)
                    for part in (meter_number, installation_number)
                    if part not in (None, "")
                ]
                meter_id = "-".join(fallback_parts) or f"{meter_type}-{index}"
            reading_date = _parse_reading_date(_value_case_insensitive(meter, "Reading_date"))
            last_reading = _as_decimal(_value_case_insensitive(meter, "Last_Meter_Reading"))
            last_consumption = _as_decimal(_value_case_insensitive(meter, "Last_Meter_Consumption"))
            unit = _normalize_unit(_value_case_insensitive(meter, "Unit", ""), sensor_type)
            normalized_meters.append(
                {
                    "id": _identifier_string(meter_id),
                    "type": sensor_type,
                    "meter_type": meter_type,
                    "meter_number": str(_value_case_insensitive(meter, "METER_NO", "") or ""),
                    "installation_number": _identifier_string(
                        _value_case_insensitive(meter, "INST_NO", "") or ""
                    ),
                    "room": str(_value_case_insensitive(meter, "ROOM_DESCR", "") or ""),
                    "label": str(
                        _value_case_insensitive(
                            meter,
                            "Headline",
                            _value_case_insensitive(meter, "MeterText", ""),
                        )
                        or ""
                    ),
                    "category": str(_value_case_insensitive(meter, "METCAT_LABEL", "") or ""),
                    "unit": unit,
                    "value": _decimal_string(last_reading) if last_reading is not None else None,
                    "last_consumption": (
                        _decimal_string(last_consumption) if last_consumption is not None else None
                    ),
                    "reading_date": reading_date.isoformat() if reading_date is not None else None,
                    "activation_date": _value_case_insensitive(meter, "Activation_date"),
                    "deactivation_date": _value_case_insensitive(meter, "Deactivation_date"),
                }
            )

        today = date.today()
        start = _add_months(today, -12)
        grouped_daily: dict[str, dict[date, dict[str, Any]]] = defaultdict(dict)

        for meter_type, (sensor_type, meter) in meter_types.items():
            readings_list = self._get_readings(meter_type, start, today, _PERIOD_DAILY_HISTORY)
            if not readings_list:
                continue
            unit = _normalize_unit(
                _value_case_insensitive(
                    readings_list,
                    "Unit",
                    _value_case_insensitive(meter, "Unit", ""),
                ),
                sensor_type,
            )
            readings = _value_case_insensitive(readings_list, "Readings", [])
            if not isinstance(readings, list):
                continue

            for reading in readings:
                if not isinstance(reading, dict):
                    continue
                reading_date = _parse_reading_date(_value_case_insensitive(reading, "Date"))
                value = _as_decimal(_value_case_insensitive(reading, "Value"))
                cumulative_value = _as_decimal(_value_case_insensitive(reading, "AkkumulativValue"))
                if reading_date is None or value is None:
                    continue

                day = reading_date.date()
                current = grouped_daily[sensor_type].get(day)
                if current is None:
                    grouped_daily[sensor_type][day] = {
                        "value": value,
                        "cumulative_value": cumulative_value,
                        "unit": unit,
                    }
                elif current["unit"] == unit:
                    current["value"] += value
                    if cumulative_value is not None:
                        current["cumulative_value"] = (
                            (current["cumulative_value"] or Decimal("0")) + cumulative_value
                        )
                else:
                    _LOGGER.debug(
                        "Skipping Czech ista %s daily value with incompatible units %s/%s",
                        sensor_type,
                        current["unit"],
                        unit,
                    )

        aggregates: dict[str, dict[str, Any]] = {}
        monthly_consumptions: dict[tuple[int, int], dict[str, tuple[Decimal, str]]] = defaultdict(dict)
        for sensor_type, values_by_day in grouped_daily.items():
            daily: list[dict[str, Any]] = []
            monthly_values: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
            unit = ""
            for day, values in sorted(values_by_day.items()):
                unit = str(values["unit"])
                value = values["value"]
                cumulative_value = values["cumulative_value"]
                daily.append(
                    {
                        "date": day.isoformat(),
                        "value": _decimal_string(value),
                        "cumulative_value": (
                            _decimal_string(cumulative_value) if cumulative_value is not None else None
                        ),
                    }
                )
                monthly_values[(day.year, day.month)] += value

            monthly = [
                {
                    "year": year,
                    "month": month,
                    "value": _decimal_string(value),
                }
                for (year, month), value in sorted(monthly_values.items())
            ]
            for (year, month), value in monthly_values.items():
                monthly_consumptions[(year, month)][sensor_type] = (value, unit)

            aggregates[sensor_type] = {
                "unit": unit,
                "daily": daily,
                "monthly": monthly,
                "daily_value": daily[-1]["value"] if daily else None,
                "daily_date": daily[-1]["date"] if daily else None,
                "monthly_value": monthly[-1]["value"] if monthly else None,
                "monthly_year": monthly[-1]["year"] if monthly else None,
                "monthly_month": monthly[-1]["month"] if monthly else None,
                "cumulative_value": daily[-1]["cumulative_value"] if daily else None,
            }

        consumptions: list[dict[str, Any]] = []
        for (year, month), values in sorted(monthly_consumptions.items(), reverse=True):
            consumptions.append(
                {
                    "date": {"month": month, "year": year},
                    "readings": [
                        {
                            "type": sensor_type,
                            "value": _decimal_string(value),
                            "unit": unit,
                            "additionalValue": None,
                            "additionalUnit": unit,
                            "estimated": False,
                            "comparedConsumption": None,
                            "comparedCost": None,
                            "averageConsumption": None,
                        }
                        for sensor_type, (value, unit) in values.items()
                    ],
                }
            )
        self._consumption_cache = {"consumptions": consumptions, "costs": []}

        return {
            "meters": normalized_meters,
            "aggregates": aggregates,
        }

    def get_consumption_data(self, obj_uuid: str | None = None) -> dict[str, Any]:
        """Normalize Czech chart readings to the German API shape reused by ``consum_raw``."""
        del obj_uuid
        if self._consumption_cache is not None:
            return copy.deepcopy(self._consumption_cache)
        if not self._meters:
            self._meters = self._get_meters()

        today = date.today()
        start = _add_months(today, -12)
        grouped: dict[tuple[int, int], dict[str, tuple[Decimal, str]]] = defaultdict(dict)
        requested_types: set[str] = set()

        for meter in self._meters:
            meter_type = str(_value_case_insensitive(meter, "MeterType", "")).strip().lower()
            sensor_type = _classify_meter(meter, meter_type)
            if not meter_type or not sensor_type or meter_type.casefold() in requested_types:
                continue
            requested_types.add(meter_type.casefold())

            readings_list = self._get_readings(meter_type, start, today)
            if not readings_list:
                continue
            unit = _normalize_unit(
                _value_case_insensitive(
                    readings_list,
                    "Unit",
                    _value_case_insensitive(meter, "Unit", ""),
                ),
                sensor_type,
            )
            readings = _value_case_insensitive(readings_list, "Readings", [])
            if not isinstance(readings, list):
                continue

            for reading in readings:
                if not isinstance(reading, dict):
                    continue
                reading_date = _parse_reading_date(
                    _value_case_insensitive(reading, "Date", _value_case_insensitive(reading, "Name"))
                )
                value = _as_decimal(_value_case_insensitive(reading, "Value"))
                if reading_date is None or value is None:
                    continue

                values_for_month = grouped[(reading_date.year, reading_date.month)]
                current = values_for_month.get(sensor_type)
                if current is None:
                    values_for_month[sensor_type] = (value, unit)
                elif current[1] == unit:
                    values_for_month[sensor_type] = (current[0] + value, unit)
                else:
                    _LOGGER.debug(
                        "Skipping duplicate Czech ista %s value with incompatible units %s/%s",
                        sensor_type,
                        current[1],
                        unit,
                    )

        consumptions: list[dict[str, Any]] = []
        for (year, month), values in sorted(grouped.items(), reverse=True):
            normalized_readings = [
                {
                    "type": sensor_type,
                    "value": _decimal_string(value),
                    "unit": unit,
                    "additionalValue": None,
                    "additionalUnit": unit,
                    "estimated": False,
                    "comparedConsumption": None,
                    "comparedCost": None,
                    "averageConsumption": None,
                }
                for sensor_type, (value, unit) in values.items()
            ]
            consumptions.append(
                {
                    "date": {"month": month, "year": year},
                    "readings": normalized_readings,
                }
            )

        result = {
            "consumptions": consumptions,
            "costs": [],
        }
        self._consumption_cache = result
        return copy.deepcopy(result)
