# tests/providers/test_world_bank.py

from datetime import date

import pytest

from material_scaleup.calculations.market_evidence import (
    commodity_market_evidence,
)
from material_scaleup.calculations.volatility import (
    annualized_price_volatility,
    price_change,
)
from material_scaleup.models.categories import AssessmentCategory
from material_scaleup.models.cost import CommodityPriceObservation
from material_scaleup.models.source import Source
from material_scaleup.providers.world_bank import WorldBankCommodityProvider

WORLD_BANK_PATH = "data/raw/world_bank/CMO-Historical-Data-Monthly.xlsx"


@pytest.fixture
def provider() -> WorldBankCommodityProvider:
    return WorldBankCommodityProvider(WORLD_BANK_PATH)


@pytest.mark.integration
def test_world_bank_lists_key_material_commodities(
    provider: WorldBankCommodityProvider,
):
    commodities = provider.commodities()

    assert "Aluminum" in commodities
    assert "Copper" in commodities
    assert "Nickel" in commodities
    assert "Zinc" in commodities
    assert "Phosphate rock" in commodities


@pytest.mark.integration
@pytest.mark.parametrize(
    "commodity",
    [
        "Aluminum",
        "Copper",
        "Nickel",
        "Zinc",
        "Phosphate rock",
        "Urea",
    ],
)
def test_world_bank_gets_price_history(
    provider: WorldBankCommodityProvider,
    commodity: str,
):
    observations = provider.get_price_history(commodity, months=60)

    assert observations
    assert len(observations) <= 60
    assert all(observation.price > 0 for observation in observations)


@pytest.mark.integration
def test_world_bank_gets_latest_nickel_price(
    provider: WorldBankCommodityProvider,
):
    observation = provider.get_latest_price("Nickel")

    assert observation.commodity == "Nickel"
    assert observation.price > 0
    assert observation.currency == "USD"
    assert observation.units == "$/mt"


def test_price_change():
    source = Source(name="Test")

    observations = [
        CommodityPriceObservation(
            commodity="Testium",
            date=date(2026, 1, 1),
            price=100,
            units="$/mt",
            source=source,
        ),
        CommodityPriceObservation(
            commodity="Testium",
            date=date(2026, 2, 1),
            price=125,
            units="$/mt",
            source=source,
        ),
    ]

    assert price_change(observations) == pytest.approx(0.25)


def test_annualized_volatility():
    source = Source(name="Test")

    observations = [
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

    volatility = annualized_price_volatility(observations)

    assert volatility is not None
    assert volatility > 0


@pytest.mark.integration
def test_world_bank_history_converts_to_evidence(
    provider: WorldBankCommodityProvider,
):
    history = provider.get_price_history("Nickel", months=60)

    evidence = commodity_market_evidence(history)

    assert len(evidence) == 3

    categories = {item.category for item in evidence}

    assert AssessmentCategory.COST in categories
    assert AssessmentCategory.MARKET_VOLATILITY in categories

    assert all(item.source is not None for item in evidence)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (" aluminum ", "Aluminum"),
        (" GOLD ", "Gold"),
        (" Phosphate \t rock ", "Phosphate rock"),
        ("Phosphate rocck", "Phosphate rock"),
        ("silicon", None),
        ("silicone", None),
        ("copper", None),
        ("", None),
    ],
)
def test_world_bank_resolves_loaded_catalog(local_world_bank_provider, query, expected):
    assert local_world_bank_provider.resolve_commodity_name(query) == expected
    if expected is not None:
        history = local_world_bank_provider.get_price_history(expected)
        assert len(history) == 3
        assert all(observation.commodity == expected for observation in history)
