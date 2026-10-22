import socket
from datetime import date
from unittest.mock import Mock, patch

import pytest
import requests
from urllib3.connection import HTTPSConnection
from urllib3.exceptions import MaxRetryError, NameResolutionError

from material_scaleup.models.trade import TradeCountry, TradeProduct
from material_scaleup.providers.comtrade import ComtradeError, ComtradeProvider

COUNTRY = TradeCountry(code=842, name="USA")
PRODUCT = TradeProduct(code="281511", description="Sodium hydroxide, solid")


def response(payload, status=200):
    return Mock(status_code=status, headers={}, json=Mock(return_value=payload))


def record(**changes):
    return {
        "reporterCode": 842,
        "period": "2024",
        "classificationCode": "H6",
        "cmdCode": "281511",
        "flowCode": "M",
        "partner2Code": 0,
        "customsCode": "C00",
        "motCode": 0,
        "partnerCode": 0,
        "partnerDesc": "World",
        "primaryValue": 1000,
        "netWgt": 100,
        "isNetWgtEstimated": False,
        "isAggregate": False,
        **changes,
    }


def test_requires_environment_key(monkeypatch):
    monkeypatch.delenv("UN_COMTRADE_API_KEY", raising=False)
    with pytest.raises(ComtradeError, match="UN_COMTRADE_API_KEY"):
        ComtradeProvider.from_environment()


def test_authenticated_dimensions_cache_and_no_secret_in_url():
    with patch(
        "material_scaleup.providers.comtrade.requests.get",
        side_effect=[response({"count": 1}), response({"data": [record()]})],
    ) as get:
        provider = ComtradeProvider("private-test-key")
        rows = provider.observations(COUNTRY, PRODUCT, 2024)
        assert provider.observations(COUNTRY, PRODUCT, 2024) == rows
    assert get.call_count == 2
    for call in get.call_args_list:
        assert call.args[0].endswith("/data/v1/get/C/A/HS")
        assert call.kwargs["headers"] == {"Ocp-Apim-Subscription-Key": "private-test-key"}
        assert "private-test-key" not in str(call.args) + str(call.kwargs["params"])
        assert call.kwargs["params"]["partner2Code"] == "0"
        assert call.kwargs["params"]["customsCode"] == "C00"
        assert call.kwargs["allow_redirects"] is False
    assert rows[0].value_usd == 1000
    count_params = get.call_args_list[0].kwargs["params"]
    assert count_params["countOnly"] == "true"
    assert not {"maxRecords", "includeDesc", "format", "breakdownMode"} & count_params.keys()
    data_params = get.call_args_list[1].kwargs["params"]
    assert "countOnly" not in data_params
    assert "breakdownMode" not in data_params
    assert data_params["format"] == "JSON"
    assert rows[0].reported_classification == "H6"


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({}, None),
        ({"classificationCode": None}, None),
        ({"clCode": "H5"}, "H5"),
        ({"classificationCode": "H6"}, "H6"),
        ({"clCode": "HS"}, None),
    ],
)
def test_classification_metadata_is_optional_and_never_defaulted(metadata, expected):
    row = record()
    del row["classificationCode"]
    row.update(metadata)
    with patch(
        "material_scaleup.providers.comtrade.requests.get",
        side_effect=[response({"count": 1}), response({"data": [row]})],
    ):
        rows = ComtradeProvider("key").observations(COUNTRY, PRODUCT, 2024)
    assert rows[0].reported_classification == expected


@pytest.mark.parametrize(
    "metadata",
    [
        {"classificationCode": "S4"},
        {"classificationCode": "H6", "clCode": "H5"},
    ],
)
def test_invalid_or_conflicting_classification_metadata_is_rejected(metadata):
    with (
        patch(
            "material_scaleup.providers.comtrade.requests.get",
            side_effect=[response({"count": 1}), response({"data": [record(**metadata)]})],
        ),
        pytest.raises(ComtradeError, match="classification metadata"),
    ):
        ComtradeProvider("key").observations(COUNTRY, PRODUCT, 2024)


@pytest.mark.parametrize("stage", ["Record-count", "Trade-data"])
def test_http_errors_identify_the_failing_operation(stage):
    replies = [response({}, 500)] * 3
    if stage == "Trade-data":
        replies.insert(0, response({"count": 1}))
    with (
        patch("material_scaleup.providers.comtrade.requests.get", side_effect=replies),
        patch("material_scaleup.providers.comtrade.time.sleep"),
        pytest.raises(ComtradeError, match=f"{stage} request for 2024 failed: .*HTTP 500"),
    ):
        ComtradeProvider("key").observations(COUNTRY, PRODUCT, 2024)


@pytest.mark.parametrize("status", [401, 403, 404, 302])
def test_errors_never_include_response_body_or_credentials(status):
    with (
        patch(
            "material_scaleup.providers.comtrade.requests.get",
            return_value=response({"error": "private-test-key"}, status),
        ),
        pytest.raises(ComtradeError) as error,
    ):
        ComtradeProvider("private-test-key").countries()
    assert "private-test-key" not in str(error.value)


def test_bounded_transient_retries():
    with (
        patch("material_scaleup.providers.comtrade.requests.get") as get,
        patch("material_scaleup.providers.comtrade.time.sleep") as sleep,
    ):
        get.side_effect = [requests.Timeout(), response({}, 429), response({"results": []})]
        with pytest.raises(ComtradeError, match="empty reporter"):
            ComtradeProvider("key").countries()
    assert get.call_count == 3
    assert sleep.call_count == 2


def test_dns_failure_is_identified_through_requests_exception_chain():
    dns_error = socket.gaierror(socket.EAI_NONAME, "private-test-key")
    resolution_error = NameResolutionError(
        "comtradeapi.un.org", HTTPSConnection("comtradeapi.un.org"), dns_error
    )
    resolution_error.__cause__ = dns_error
    error = requests.ConnectionError(
        MaxRetryError(None, "/private-test-key", reason=resolution_error)
    )
    with (
        patch("material_scaleup.providers.comtrade.requests.get", side_effect=error) as get,
        patch("material_scaleup.providers.comtrade.time.sleep"),
        pytest.raises(ComtradeError, match="DNS lookup failed") as raised,
    ):
        ComtradeProvider("private-test-key").countries()
    assert get.call_count == 3
    assert "before API-key validation" in str(raised.value)
    assert "private-test-key" not in str(raised.value)


@pytest.mark.parametrize(
    ("error", "message", "attempts"),
    [
        (requests.Timeout("private-test-key"), "timed out", 3),
        (requests.ConnectionError("private-test-key"), "Cannot connect", 3),
        (requests.exceptions.SSLError("private-test-key"), "TLS certificate", 1),
        (requests.exceptions.ProxyError("private-test-key"), "configured proxy", 1),
    ],
)
def test_actionable_transport_errors_do_not_expose_exception_details(error, message, attempts):
    with (
        patch("material_scaleup.providers.comtrade.requests.get", side_effect=error) as get,
        patch("material_scaleup.providers.comtrade.time.sleep"),
        pytest.raises(ComtradeError, match=message) as raised,
    ):
        ComtradeProvider("private-test-key").countries()
    assert get.call_count == attempts
    assert "private-test-key" not in str(raised.value)

@pytest.mark.parametrize("payload", [{"count": 1000}, {"count": -1}, {"count": None}])
def test_unsafe_record_count_is_rejected(payload):
    with (
        patch("material_scaleup.providers.comtrade.requests.get", return_value=response(payload)),
        pytest.raises(ComtradeError, match="record count"),
    ):
        ComtradeProvider("key").observations(COUNTRY, PRODUCT, 2024)


@pytest.mark.parametrize(
    ("rows", "count", "message"),
    [
        ([record()], 2, "incomplete"),
        ([record(), record()], 2, "duplicate"),
        ([record(flowCode="X")], 1, "dimensions"),
        ([record(netWgt=-1)], 1, "schema"),
        ([record(primaryValue=float("nan"))], 1, "schema"),
        ([record(partnerCode=156, isAggregate=True)], 1, "aggregate"),
    ],
)
def test_response_integrity(rows, count, message):
    with (
        patch(
            "material_scaleup.providers.comtrade.requests.get",
            side_effect=[response({"count": count}), response({"data": rows})],
        ),
        pytest.raises(ComtradeError, match=message),
    ):
        ComtradeProvider("key").observations(COUNTRY, PRODUCT, 2024)


def test_reference_catalogs_exclude_world_groups_and_non_leaf_products():
    with patch(
        "material_scaleup.providers.comtrade.requests.get",
        side_effect=[
            response(
                {
                    "results": [
                        {"id": "0", "text": "World"},
                        {"id": "999", "text": "Group", "isGroup": "true"},
                        {"id": "842", "text": "USA", "isGroup": "false"},
                    ]
                }
            ),
            response(
                {
                    "results": [
                        {"id": "28", "text": "Chemicals"},
                        {"id": "281511", "text": "Sodium hydroxide, solid"},
                    ]
                }
            ),
        ],
    ):
        provider = ComtradeProvider("key")
        assert provider.countries() == [COUNTRY]
        assert provider.products() == [PRODUCT]


def test_available_years_exclude_current_and_foreign_reporting_periods():
    current = date.today().year
    payload = {
        "data": [{"period": year, "reporterCode": 842} for year in range(current - 7, current + 1)]
        + [{"period": current - 1, "reporterCode": 156}]
    }
    with patch("material_scaleup.providers.comtrade.requests.get", return_value=response(payload)):
        assert ComtradeProvider("key").available_years(COUNTRY) == list(
            range(current - 1, current - 6, -1)
        )


def test_http_success_with_failed_validation_is_an_error():
    with (
        patch(
            "material_scaleup.providers.comtrade.requests.get",
            return_value=response({"validation": {"status": "Error"}, "data": [], "count": 0}),
        ),
        pytest.raises(ComtradeError, match="rejected the query"),
    ):
        ComtradeProvider("key").observations(COUNTRY, PRODUCT, 2024)


def test_missing_weight_quality_flag_is_not_assumed_reported():
    row = record()
    del row["isNetWgtEstimated"]
    with (
        patch(
            "material_scaleup.providers.comtrade.requests.get",
            side_effect=[response({"count": 1}), response({"data": [row]})],
        ),
        pytest.raises(ComtradeError, match="schema"),
    ):
        ComtradeProvider("key").observations(COUNTRY, PRODUCT, 2024)


@pytest.mark.integration
def test_live_authenticated_trade_contract():
    import os

    if not os.getenv("UN_COMTRADE_API_KEY"):
        pytest.skip("UN_COMTRADE_API_KEY is not configured")
    provider = ComtradeProvider.from_environment()
    assert any(country.code == COUNTRY.code for country in provider.countries())
    assert any(product.code == PRODUCT.code for product in provider.products())
    years = provider.available_years(COUNTRY)
    assert years
    rows = provider.observations(COUNTRY, PRODUCT, years[0])
    assert rows
