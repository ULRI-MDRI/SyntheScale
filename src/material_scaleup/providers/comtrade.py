"""Bounded authenticated access to UN Comtrade reported annual HS data."""

import os
import socket
import time
from datetime import date
from typing import Any

import requests
from pydantic import ValidationError

from material_scaleup.models.trade import TradeCountry, TradeObservation, TradeProduct


class ComtradeError(RuntimeError):
    """An explicit configuration, retrieval, or response-integrity failure."""


def _is_dns_failure(error: BaseException) -> bool:
    pending: list[BaseException] = [error]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        if isinstance(current, socket.gaierror):
            return True
        for nested in (
            current.__cause__,
            current.__context__,
            getattr(current, "reason", None),
            *current.args,
        ):
            if isinstance(nested, BaseException):
                pending.append(nested)
    return False


def _flag(value: object) -> bool:
    if value in (True, 1, "1", "true", "True", "Yes", "yes"):
        return True
    if value in (False, 0, "0", "false", "False", "No", "no", None):
        return False
    raise ComtradeError("UN Comtrade returned an unrecognized boolean flag.")


class ComtradeProvider:
    BASE_URL = "https://comtradeapi.un.org"
    MAX_RECORDS = 1000

    def __init__(self, api_key: str) -> None:
        if not api_key.strip():
            raise ComtradeError("UN_COMTRADE_API_KEY is not configured.")
        self._api_key = api_key.strip()
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @classmethod
    def from_environment(cls) -> "ComtradeProvider":
        return cls(os.getenv("UN_COMTRADE_API_KEY", ""))

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        cache_key = f"{path}:{sorted((params or {}).items())}"
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < 3600:
            return cached[1]
        for attempt in range(3):
            try:
                response = requests.get(
                    self.BASE_URL + path,
                    params=params,
                    headers={"Ocp-Apim-Subscription-Key": self._api_key},
                    timeout=(5, 30),
                    allow_redirects=False,
                )
            except requests.exceptions.SSLError:
                raise ComtradeError(
                    "TLS certificate verification failed for comtradeapi.un.org. "
                    "Check your system clock and trusted certificates or contact your "
                    "network administrator. Do not disable certificate verification."
                ) from None
            except requests.exceptions.ProxyError:
                raise ComtradeError(
                    "Cannot connect to UN Comtrade through the configured proxy. "
                    "Check HTTPS_PROXY/HTTP_PROXY and your network or VPN settings."
                ) from None
            except (requests.Timeout, requests.ConnectionError) as error:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                if isinstance(error, requests.Timeout):
                    raise ComtradeError(
                        "UN Comtrade connection or response timed out. "
                        "Check network/VPN/firewall access to comtradeapi.un.org and retry."
                    ) from None
                if _is_dns_failure(error):
                    raise ComtradeError(
                        "DNS lookup failed for comtradeapi.un.org, before API-key validation. "
                        "Check with `nslookup comtradeapi.un.org` and "
                        "`nslookup comtrade.azure-api.net`. Check your DNS/VPN/network "
                        "or contact your network administrator; "
                        "the API service may be unavailable. "
                        "Changing the API key will not fix a DNS failure."
                    ) from None
                raise ComtradeError(
                    "Cannot connect to comtradeapi.un.org, before API-key validation. "
                    "Check network/VPN/firewall access and retry; "
                    "the API service may be unavailable."
                ) from None
            except requests.RequestException:
                raise ComtradeError("UN Comtrade request failed.") from None
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                retry_after = response.headers.get("Retry-After", "")
                delay = min(int(retry_after), 10) if retry_after.isdigit() else 2**attempt
                time.sleep(delay)
                continue
            if response.status_code in (401, 403):
                raise ComtradeError("UN Comtrade rejected the API key or account entitlement.")
            if response.status_code != 200:
                raise ComtradeError(
                    f"UN Comtrade returned HTTP {response.status_code}. Retry later."
                )
            try:
                payload = response.json()
            except requests.exceptions.JSONDecodeError:
                raise ComtradeError("UN Comtrade returned invalid JSON.") from None
            if not isinstance(payload, dict):
                raise ComtradeError("UN Comtrade returned an unexpected response structure.")
            if payload.get("error") or payload.get("errorMessage"):
                raise ComtradeError("UN Comtrade reported an API error; no results were accepted.")
            validation = payload.get("validation")
            if isinstance(validation, dict) and str(validation.get("status", "ok")).lower() != "ok":
                raise ComtradeError("UN Comtrade rejected the query; no results were accepted.")
            if len(self._cache) >= 256:
                self._cache.clear()
            self._cache[cache_key] = (time.monotonic(), payload)
            return payload
        raise ComtradeError("UN Comtrade retry budget exhausted.")

    def countries(self) -> list[TradeCountry]:
        payload = self._get("/files/v1/app/reference/Reporters.json")
        try:
            countries = [
                TradeCountry(code=int(row["id"]), name=row["text"])
                for row in payload["results"]
                if str(row["id"]).isdigit() and int(row["id"]) > 0 and not _flag(row.get("isGroup"))
            ]
        except (KeyError, TypeError, ValueError, ValidationError):
            raise ComtradeError("UN Comtrade reporter catalog is invalid.") from None
        if not countries:
            raise ComtradeError("UN Comtrade returned an empty reporter catalog.")
        if len({country.code for country in countries}) != len(countries):
            raise ComtradeError("UN Comtrade reporter catalog contains ambiguous duplicate codes.")
        return sorted(countries, key=lambda item: item.name)

    def products(self) -> list[TradeProduct]:
        payload = self._get("/files/v1/app/reference/H6.json")
        try:
            products = [
                TradeProduct(code=str(row["id"]), description=row["text"])
                for row in payload["results"]
                if len(str(row["id"])) == 6 and str(row["id"]).isdigit()
            ]
        except (KeyError, TypeError, ValidationError):
            raise ComtradeError("UN Comtrade HS2022 catalog is invalid.") from None
        if not products:
            raise ComtradeError("UN Comtrade returned an empty HS2022 catalog.")
        if len({product.code for product in products}) != len(products):
            raise ComtradeError("UN Comtrade HS2022 catalog contains ambiguous duplicate codes.")
        return products

    def available_years(self, country: TradeCountry) -> list[int]:
        payload = self._get("/data/v1/getDa/C/A/HS", {"reporterCode": str(country.code)})
        try:
            rows = payload["data"]
            if not isinstance(rows, list) or len(rows) >= self.MAX_RECORDS:
                raise ComtradeError("UN Comtrade data-availability response may be incomplete.")
            years = {
                int(row["period"])
                for row in rows
                if int(row["reporterCode"]) == country.code
                and 1992 <= int(row["period"]) < date.today().year
            }
        except (KeyError, TypeError, ValueError):
            raise ComtradeError("UN Comtrade data-availability metadata is invalid.") from None
        return sorted(years, reverse=True)[:5]

    def observations(
        self, country: TradeCountry, product: TradeProduct, year: int
    ) -> list[TradeObservation]:
        params = {
            "reporterCode": str(country.code),
            "period": str(year),
            "cmdCode": product.code,
            "flowCode": "M",
            "partner2Code": "0",
            "customsCode": "C00",
            "motCode": "0",
        }
        path = "/data/v1/get/C/A/HS"
        try:
            count_payload = self._get(path, {**params, "countOnly": "true"})
        except ComtradeError as error:
            raise ComtradeError(f"Record-count request for {year} failed: {error}") from None
        expected = count_payload.get("count")
        if type(expected) is not int or not 0 <= expected < self.MAX_RECORDS:
            raise ComtradeError(
                "UN Comtrade record count is missing or exceeds the safe query limit."
            )
        try:
            payload = self._get(
                path,
                {
                    **params,
                    "includeDesc": "true",
                    "maxRecords": str(self.MAX_RECORDS),
                    "format": "JSON",
                },
            )
        except ComtradeError as error:
            raise ComtradeError(f"Trade-data request for {year} failed: {error}") from None
        rows = payload.get("data")
        if not isinstance(rows, list) or len(rows) != expected:
            raise ComtradeError(
                "UN Comtrade response is incomplete; indicators were not calculated."
            )
        observations: list[TradeObservation] = []
        seen: set[int] = set()
        try:
            for row in rows:
                if (
                    int(row["reporterCode"]) != country.code
                    or int(row["period"]) != year
                    or row["cmdCode"] != product.code
                    or row["flowCode"] != "M"
                    or int(row["partner2Code"]) != 0
                    or row["customsCode"] != "C00"
                    or int(row["motCode"]) != 0
                ):
                    raise ComtradeError("UN Comtrade returned unexpected query dimensions.")
                classifications = {
                    value
                    for value in (row.get("classificationCode"), row.get("clCode"))
                    if value is not None and value != "HS"
                }
                if (
                    any(
                        value not in {f"H{index}" for index in range(7)}
                        for value in classifications
                    )
                    or len(classifications) > 1
                ):
                    raise ComtradeError("UN Comtrade returned invalid classification metadata.")
                reported_classification = next(iter(classifications), None)
                partner = int(row["partnerCode"])
                if partner in seen or (partner != 0 and _flag(row.get("isAggregate"))):
                    raise ComtradeError("UN Comtrade returned aggregate or duplicate records.")
                seen.add(partner)
                observations.append(
                    TradeObservation(
                        year=year,
                        partner_code=partner,
                        partner_name=row["partnerDesc"],
                        value_usd=row["primaryValue"],
                        net_weight_kg=row.get("netWgt"),
                        weight_estimated=_flag(row["isNetWgtEstimated"]),
                        reported_classification=reported_classification,
                    )
                )
        except (KeyError, TypeError, ValueError, ValidationError):
            raise ComtradeError("UN Comtrade trade records failed schema validation.") from None
        return observations
