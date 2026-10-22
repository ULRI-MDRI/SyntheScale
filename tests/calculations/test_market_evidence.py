# tests/calculations/test_market_evidence.py

from datetime import date

import pytest

from material_scaleup.calculations.market_evidence import (
    commodity_market_evidence,
)
from material_scaleup.models.categories import AssessmentCategory
from material_scaleup.models.cost import CommodityPriceObservation
from material_scaleup.models.source import Source


@pytest.fixture
def observations() -> list[CommodityPriceObservation]:
    source = Source(
        name="World Bank Commodity Price Data (Pink Sheet)",
        publisher="World Bank",
    )

    return [
        CommodityPriceObservation(
            commodity="Testium",
            date=date(2026, month, 1),
            price=price,
            units="$/mt",
            source=source,
        )
        for month, price in [
            (1, 100),
            (2, 110),
            (3, 105),
            (4, 120),
            (5, 115),
        ]
    ]


def test_market_evidence_returns_three_records(
    observations: list[CommodityPriceObservation],
):
    evidence = commodity_market_evidence(observations)
    assert len(evidence) == 3


def test_market_evidence_contains_latest_price(
    observations: list[CommodityPriceObservation],
):
    evidence = commodity_market_evidence(observations)

    cost_evidence = [item for item in evidence if item.category == AssessmentCategory.COST]

    assert len(cost_evidence) == 1

    item = cost_evidence[0]

    assert item.reported_value is not None
    assert item.reported_value.value == 115
    assert item.reported_value.units == "$/mt"

    assert item.scope is not None
    assert item.scope.effective_date == date(2026, 5, 1)


def test_market_evidence_contains_price_change(
    observations: list[CommodityPriceObservation],
):
    evidence = commodity_market_evidence(observations)

    change_evidence = [
        item for item in evidence if item.metadata.get("observation_type") == "price_change"
    ]

    assert len(change_evidence) == 1

    item = change_evidence[0]

    assert item.reported_value is not None
    assert item.reported_value.value == pytest.approx(15.0)
    assert item.reported_value.units == "%"


def test_market_evidence_contains_volatility(
    observations: list[CommodityPriceObservation],
):
    evidence = commodity_market_evidence(observations)

    volatility_evidence = [
        item
        for item in evidence
        if item.metadata.get("observation_type") == "annualized_volatility"
    ]

    assert len(volatility_evidence) == 1

    item = volatility_evidence[0]

    assert item.category == AssessmentCategory.MARKET_VOLATILITY

    assert item.reported_value is not None
    assert float(item.reported_value.value) > 0


def test_market_evidence_empty_input_returns_empty():
    assert commodity_market_evidence([]) == []


def test_market_evidence_rejects_mixed_commodities(
    observations: list[CommodityPriceObservation],
):
    mixed = [
        *observations,
        CommodityPriceObservation(
            commodity="Otherium",
            date=date(2026, 6, 1),
            price=100,
            units="$/mt",
            source=Source(name="Test"),
        ),
    ]

    with pytest.raises(ValueError, match="exactly one commodity"):
        commodity_market_evidence(mixed)
