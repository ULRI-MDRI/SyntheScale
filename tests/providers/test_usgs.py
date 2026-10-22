# tests/providers/test_usgs.py

from pathlib import Path

import pytest

from material_scaleup.calculations.supply_evidence import usgs_supply_evidence
from material_scaleup.models.categories import AssessmentCategory
from material_scaleup.providers.usgs import USGSCommodityProvider

USGS_PATH = Path("data/raw/usgs/mcs2026/MCS2026_Commodities_Data.csv")


@pytest.fixture
def provider() -> USGSCommodityProvider:
    return USGSCommodityProvider(USGS_PATH)


@pytest.mark.integration
def test_usgs_lists_expected_commodities(
    provider: USGSCommodityProvider,
):
    commodities = provider.commodities()

    assert "Aluminum" in commodities
    assert "Cobalt" in commodities
    assert "Nickel" in commodities
    assert "Phosphate Rock" in commodities
    assert "Silicon" in commodities
    assert "Zinc" in commodities


@pytest.mark.integration
def test_usgs_gets_latest_nickel_world_production(
    provider: USGSCommodityProvider,
):
    observation = provider.get_latest_world_production("Nickel")

    assert observation is not None
    assert observation.year == 2025
    assert observation.country == "World total"
    assert observation.value == pytest.approx(3_900_000)
    assert observation.units == "metric tons"


@pytest.mark.integration
def test_usgs_preserves_qualified_reserve_value(
    provider: USGSCommodityProvider,
):
    observation = provider.get_latest_world_reserves("Nickel")

    assert observation is not None
    assert observation.raw_value == ">140,000,000"
    assert observation.value == pytest.approx(140_000_000)


@pytest.mark.integration
def test_usgs_identifies_nickel_as_critical(
    provider: USGSCommodityProvider,
):
    assert provider.is_critical_mineral("Nickel") is True


@pytest.mark.integration
def test_usgs_gets_nickel_country_production(
    provider: USGSCommodityProvider,
):
    observations = provider.get_latest_country_production("Nickel")

    countries = {observation.country for observation in observations}

    assert "Indonesia" in countries
    assert "Australia" in countries
    assert "World total" not in countries


@pytest.mark.integration
def test_usgs_converts_nickel_to_supply_evidence(
    provider: USGSCommodityProvider,
):
    evidence = usgs_supply_evidence(provider, "Nickel")

    assert evidence

    categories = {item.category for item in evidence}

    assert AssessmentCategory.AVAILABILITY in categories
    assert AssessmentCategory.SUPPLY_CHAIN in categories

    concentration = next(
        item
        for item in evidence
        if item.metadata.get("observation_type") == "largest_country_production_share"
    )

    assert concentration.reported_value is not None
    assert concentration.reported_value.value == pytest.approx(66.67, rel=0.01)


@pytest.mark.integration
def test_usgs_preserves_silicon_import_reliance_qualifiers(
    provider: USGSCommodityProvider,
):
    records = provider.get_latest_net_import_reliance("Silicon")

    by_detail = {record.statistic_detail: record for record in records}

    silicon_metal = next(
        record
        for detail, record in by_detail.items()
        if detail is not None and detail.endswith("Silicon metal")
    )

    assert silicon_metal.raw_value == ">50"
    assert silicon_metal.value == pytest.approx(50)
    assert silicon_metal.value_qualifier == ">"


@pytest.mark.integration
def test_usgs_preserves_nonnumeric_zinc_value(
    provider: USGSCommodityProvider,
):
    records = provider.get_latest_net_import_reliance("Zinc")

    ores = next(
        record
        for record in records
        if record.statistic_detail is not None
        and record.statistic_detail.endswith("Ores and concentrates")
    )

    assert ores.raw_value == "E"
    assert ores.value is None
    assert ores.value_qualifier is None


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (" aluminum ", "Aluminum"),
        (" GOLD ", "Gold"),
        (" Phosphate \t rock ", "Phosphate Rock"),
        ("Phosphate rocck", "Phosphate Rock"),
        ("silicon", "Silicon"),
        ("silicone", None),
        ("nickel", None),
        ("", None),
    ],
)
def test_usgs_resolves_loaded_catalog(local_usgs_provider, query, expected):
    assert local_usgs_provider.resolve_commodity_name(query) == expected
    if expected is not None:
        records = local_usgs_provider.get_records(expected)
        assert len(records) == 1
        assert records[0].commodity == expected
        assert records[0].value == 1_000
