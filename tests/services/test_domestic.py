from datetime import date
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from material_scaleup.models.chemical import ChemicalIdentity, MaterialSpec
from material_scaleup.models.scenario import (
    LocationSpec,
    ProcessInput,
    ScaleUpScenario,
    SynthesisRoute,
)
from material_scaleup.models.trade import TradeCountry, TradeMatch, TradeProduct
from material_scaleup.providers.usgs import USGSCommodityProvider
from material_scaleup.services.availability import AvailabilityService
from material_scaleup.services.context_builder import AssessmentContextBuilder
from material_scaleup.services.domestic import DomesticProductionService
from material_scaleup.services.llm_context_builder import build_llm_context


@pytest.fixture
def domestic_provider(tmp_path):
    year = date.today().year - 1
    rows = []
    for country, period, value, detail in [
        ("United States", year - 1, "100", "Primary"),
        ("United States", year, "80", "Primary"),
        ("United States", year, "W", "Secondary"),
        ("United States", year, "0", "Other production"),
        ("China", year, "5000", "Primary"),
        ("World total", year, "6000", "Primary"),
    ]:
        rows.append(
            {
                **dict.fromkeys(USGSCommodityProvider.REQUIRED_COLUMNS, ""),
                "Commodity": "Aluminum",
                "Section": "Production",
                "Country": country,
                "Statistics": "Production",
                "Statistics_detail": detail,
                "Year": str(period),
                "Value": value,
                "Unit": "thousand metric tons",
                "Notes": "Estimated; see source",
                "Other notes": "Overlapping series",
            }
        )
    path = tmp_path / "production.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return USGSCommodityProvider(path)


def test_country_alias_scope_and_multiple_series_preserved(domestic_provider):
    result = DomesticProductionService(domestic_provider).lookup(
        ChemicalIdentity(name="sodium aluminate"), "USA"
    )
    assert result.status == "available"
    assert result.source_country == "United States"
    assert result.direct_material_status == "not_checked"
    assert result.relationship == "upstream"
    assert len(result.observations) == 3
    assert {row.raw_value for row in result.observations} == {"80", "W", "0"}
    assert all(row.country == "United States" for row in result.observations)
    assert all(row.units == "thousand metric tons" for row in result.observations)
    assert all(row.year == date.today().year - 1 for row in result.observations)
    assert all(row.notes == "Estimated; see source" for row in result.observations)
    assert any("withheld" in note for note in result.limitations)
    assert all(row.source.doi for row in result.observations)


@pytest.mark.parametrize("country", ["Canada", "Untied States", "American Samoa"])
def test_missing_country_never_uses_other_country_or_world(domestic_provider, country):
    result = DomesticProductionService(domestic_provider).lookup(
        ChemicalIdentity(name="sodium aluminate"), country
    )
    assert result.status == "not_available"
    assert not result.observations
    assert any("not evidence of zero" in note for note in result.limitations)


@pytest.mark.parametrize("material", ["sodium hydroxide", "water", "unobtainium", "urea"])
def test_unmapped_material_does_not_invent_production(domestic_provider, material):
    result = DomesticProductionService(domestic_provider).lookup(
        ChemicalIdentity(name=material), "USA"
    )
    assert result.status in ("not_checked", "not_available")
    assert not result.observations
    assert result.direct_material_status == "not_checked"


def test_missing_and_invalid_sources_explicit():
    chemical = ChemicalIdentity(name="sodium aluminate")
    assert DomesticProductionService(None).lookup(chemical, "USA").status == "not_checked"
    result = DomesticProductionService(None, source_error="Invalid dataset").lookup(chemical, "USA")
    assert result.status == "error"
    assert "Invalid dataset" in result.limitations


def test_domestic_survives_trade_failure(domestic_provider):
    from material_scaleup.providers.comtrade import ComtradeError

    provider = Mock()
    provider.available_years.side_effect = ComtradeError("Network unavailable")
    match = TradeMatch(
        requested_material="sodium aluminate",
        product=TradeProduct(code="284190", description="Broad salts category"),
        relationship="broader",
        reason="Proxy only",
    )
    result = AvailabilityService(
        provider, domestic_service=DomesticProductionService(domestic_provider)
    ).lookup(TradeCountry(code=842, name="USA"), match, confirmed=True)
    assert result.status == "error"
    assert result.domestic_supply_status == "available"
    assert result.domestic_production.observations
    assert result.domestic_production.direct_material_status == "not_checked"


def test_assessment_domestic_without_comtrade(
    domestic_provider,
    local_world_bank_provider,
):
    safety = Mock()
    safety.get_evidence.return_value = []
    resolver = Mock()
    resolver.resolve.return_value = []
    scenario = ScaleUpScenario(
        material=MaterialSpec(name="Example"),
        production_location=LocationSpec(country="USA"),
        synthesis_route=SynthesisRoute(
            name="Example",
            inputs=[
                ProcessInput(chemical=ChemicalIdentity(name="sodium aluminate")),
            ],
        ),
    )
    context = AssessmentContextBuilder(
        commodity_resolver=resolver,
        safety_provider=safety,
        usgs_provider=domestic_provider,
        world_bank_provider=local_world_bank_provider,
    ).build(scenario)
    compact = build_llm_context(context)
    assert not context.trade_availability
    assert compact.domestic_production[0].status == "available"
    assert compact.domestic_production[0].observations[0].country == "United States"
    assert any(
        row.metadata.get("observation_type") == "domestic_upstream_production"
        for row in context.evidence
    )


def test_optional_ui_dataset_absent_does_not_block_lookup():
    from material_scaleup.ui.availability import get_domestic_service

    with patch("material_scaleup.ui.availability.Path.exists", return_value=False):
        result = get_domestic_service().lookup(ChemicalIdentity(name="sodium aluminate"), "USA")
    assert result.status == "not_checked"


@pytest.mark.parametrize("value", ["W", "0", "<5"])
def test_zero_withheld_and_qualified_values_preserved(domestic_provider, value):
    record = domestic_provider.get_records(
        "Aluminum", statistic="Production", country="United States"
    )[0].model_copy(
        update={
            "year": date.today().year - 3,
            "raw_year": str(date.today().year - 3),
            "value": None if value == "W" else (0 if value == "0" else 5),
            "raw_value": value,
            "value_qualifier": "<" if value == "<5" else None,
        }
    )
    with patch.object(domestic_provider, "get_records", return_value=[record]):
        result = DomesticProductionService(domestic_provider).lookup(
            ChemicalIdentity(name="sodium aluminate"), "USA"
        )
    assert result.status == ("not_available" if value == "W" else "available")
    assert result.observations[0].raw_value == value
    assert result.observations[0].value_qualifier == ("<" if value == "<5" else None)
    assert any("does not describe current" in item for item in result.limitations)
    assert result.direct_material_status == "not_checked"


def test_current_year_and_aggregates_not_used(domestic_provider):
    record = domestic_provider.get_records(
        "Aluminum", statistic="Production", country="United States"
    )[0].model_copy(update={"year": date.today().year})
    service = DomesticProductionService(domestic_provider)
    with patch.object(domestic_provider, "get_records", return_value=[record]):
        result = service.lookup(ChemicalIdentity(name="sodium aluminate"), "USA")
    assert result.status == "not_available"
    assert not result.observations
    result = service.lookup(ChemicalIdentity(name="sodium aluminate"), "World total")
    assert result.status == "not_checked"
    assert not result.observations


def test_domestic_ui_preserves_scope_and_raw_values(domestic_provider):
    runner = pytest.importorskip("streamlit.testing.v1").AppTest
    result = DomesticProductionService(domestic_provider).lookup(
        ChemicalIdentity(name="sodium aluminate"), "USA"
    )
    with patch(
        "material_scaleup.services.domestic.DomesticProductionService.lookup",
        return_value=result,
    ):
        app = runner.from_string("""
from material_scaleup.models.chemical import ChemicalIdentity
from material_scaleup.services.domestic import DomesticProductionService
from material_scaleup.ui.availability import render_domestic_production
result = DomesticProductionService(None).lookup(ChemicalIdentity(name="sodium aluminate"), "USA")
render_domestic_production([result])
""").run()
    assert not app.exception
    assert "Direct material production: not_checked" in app.markdown[1].value
    assert set(app.dataframe[0].value["Published value"]) == {"80", "W", "0"}
    assert any("not verified production" in info.value for info in app.info)


def test_malformed_optional_dataset_is_explicit():
    from material_scaleup.ui.availability import get_domestic_service

    with (
        patch("material_scaleup.ui.availability.Path.exists", return_value=True),
        patch(
            "material_scaleup.ui.availability.USGSCommodityProvider",
            side_effect=ValueError("Missing columns"),
        ),
    ):
        result = get_domestic_service().lookup(ChemicalIdentity(name="sodium aluminate"), "USA")
    assert result.status == "error"
    assert any("Missing columns" in item for item in result.limitations)
