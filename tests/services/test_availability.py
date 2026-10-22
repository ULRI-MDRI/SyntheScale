from unittest.mock import Mock, create_autospec

import pytest

from material_scaleup.models.chemical import ChemicalIdentity, MaterialSpec
from material_scaleup.models.scenario import (
    LocationSpec,
    ProcessInput,
    ScaleUpScenario,
    SynthesisRoute,
)
from material_scaleup.models.trade import TradeCountry, TradeMatch, TradeObservation, TradeProduct
from material_scaleup.providers.comtrade import ComtradeError, ComtradeProvider
from material_scaleup.services.availability import AvailabilityService
from material_scaleup.services.context_builder import AssessmentContextBuilder
from material_scaleup.services.llm_context_builder import build_llm_context

COUNTRY = TradeCountry(code=842, name="USA")
MATCH = TradeMatch(
    requested_material="sodium hydroxide",
    product=TradeProduct(code="281511", description="Sodium hydroxide, solid"),
    relationship="broader",
    reason="Solid form only; verify grade.",
)


def provider_with_data():
    provider = create_autospec(ComtradeProvider, instance=True)
    provider.available_years.return_value = [2024, 2023]

    def observations(country, product, year):
        value = 1000 if year == 2024 else 500
        return [
            TradeObservation(
                year=year,
                partner_code=partner,
                partner_name=str(partner),
                value_usd=value,
                net_weight_kg=100,
                reported_classification="H6",
            )
            for partner in [0, 156]
        ]

    provider.observations.side_effect = observations
    return provider


def test_confirmation_required_before_any_request():
    provider = provider_with_data()
    with pytest.raises(ValueError, match="Confirm"):
        AvailabilityService(provider).lookup(COUNTRY, MATCH)
    provider.available_years.assert_not_called()


def test_result_has_provenance_nominal_trend_and_explicit_unchecked_states():
    result = AvailabilityService(provider_with_data()).lookup(COUNTRY, MATCH, confirmed=True)
    assert result.status == "available"
    assert result.value_change_percent == 100
    assert result.trend_period == "2023-2024 (nominal USD, not quantity)"
    assert result.score is None
    assert result.restrictions_status == "not_checked"
    assert result.domestic_supply_status == "not_checked"
    assert result.logistics_status == "not_checked"
    assert result.source.url == "https://comtradeplus.un.org/"
    assert result.observations
    assert result.match.relationship == "broader"
    assert any("Only 2" in gap for gap in result.data_gaps)


def test_partial_year_failure_preserves_other_period():
    provider = provider_with_data()
    valid = provider.observations(COUNTRY, MATCH.product, 2024)
    provider.observations.side_effect = [valid, ComtradeError("incomplete response")]
    result = AvailabilityService(provider).lookup(COUNTRY, MATCH, confirmed=True)
    assert result.status == "available"
    assert result.years[1].status == "error"
    assert result.value_change_percent is None
    assert any("failed" in gap for gap in result.data_gaps)


@pytest.mark.parametrize("revision", [None, "H5"])
def test_unverified_or_other_revision_is_preserved_without_hs2022_claims(revision):
    provider = provider_with_data()
    records = [
        row.model_copy(update={"reported_classification": revision})
        for row in provider.observations(COUNTRY, MATCH.product, 2024)
    ]
    provider.available_years.return_value = [2024, 2023]
    provider.observations.side_effect = [
        records,
        [row.model_copy(update={"year": 2023}) for row in records],
    ]
    result = AvailabilityService(provider).lookup(COUNTRY, MATCH, confirmed=True)
    assert result.status == "available"
    assert result.query_classification == "HS"
    assert result.years[0].import_value_usd == 1000
    assert not result.years[0].classification_matches_catalog
    assert result.years[0].reported_classifications == ([revision] if revision else [])
    assert result.value_change_percent is None
    assert any("equivalence" in gap for gap in result.data_gaps)
    assert "HS2022" not in result.source.name


def test_no_reporting_and_service_failure_are_not_zero_trade():
    provider = provider_with_data()
    provider.available_years.return_value = []
    assert (
        AvailabilityService(provider).lookup(COUNTRY, MATCH, confirmed=True).status
        == "insufficient_data"
    )
    provider.available_years.side_effect = ComtradeError("unreachable")
    result = AvailabilityService(provider).lookup(COUNTRY, MATCH, confirmed=True)
    assert result.status == "error"
    assert "unreachable" in result.data_gaps
    provider.available_years.side_effect = None
    provider.available_years.return_value = [2024]
    provider.observations.side_effect = ComtradeError("failed")
    assert AvailabilityService(provider).lookup(COUNTRY, MATCH, confirmed=True).status == "error"


@pytest.mark.parametrize("revision", ["H6", None, "H5"])
def test_full_and_compact_context_carry_trade_scope_and_warnings(
    local_world_bank_provider,
    local_usgs_provider,
    revision,
):
    provider = provider_with_data()
    records = [
        row.model_copy(update={"reported_classification": revision})
        for row in provider.observations(COUNTRY, MATCH.product, 2024)
    ]
    provider.available_years.return_value = [2024]
    provider.observations.side_effect = [records]
    result = AvailabilityService(provider).lookup(COUNTRY, MATCH, confirmed=True)
    scenario = ScaleUpScenario(
        material=MaterialSpec(name="Example"),
        production_location=LocationSpec(country="USA"),
        synthesis_route=SynthesisRoute(
            name="Example route",
            inputs=[ProcessInput(chemical=ChemicalIdentity(name="sodium hydroxide"))],
        ),
    )
    safety = Mock()
    safety.get_evidence.return_value = []
    resolver = Mock()
    resolver.resolve.return_value = []
    builder = AssessmentContextBuilder(
        commodity_resolver=resolver,
        safety_provider=safety,
        world_bank_provider=local_world_bank_provider,
        usgs_provider=local_usgs_provider,
    )
    full = builder.build(scenario, trade_availability=[result])
    compact = build_llm_context(full)
    assert full.trade_availability[0].observations
    assert not compact.trade_availability[0].observations
    assert compact.trade_availability[0].match == MATCH
    assert compact.trade_availability[0].years[0].unit_value_usd_per_kg == 10
    assert compact.trade_availability[0].years[0].warnings
    assert compact.trade_availability[0].years[0].reported_classifications == (
        [revision] if revision else []
    )
    trade_evidence = next(
        item for item in full.evidence if item.metadata.get("hs_code") == "281511"
    )
    assert trade_evidence.metadata["reported_classifications"] == revision
    assert trade_evidence.metadata["classification_matches_catalog"] == (revision == "H6")
    assert all(item.source is not None for item in full.evidence)
    assert any(item.metadata.get("hs_code") == "281511" for item in full.evidence)
    scenario.production_location.country = "Canada"
    with pytest.raises(ValueError, match="country"):
        builder.build(scenario, trade_availability=[result])
    scenario.production_location.country = "USA"
    scenario.synthesis_route.inputs[0].chemical.name = "unrelated chemical"
    with pytest.raises(ValueError, match="material"):
        builder.build(scenario, trade_availability=[result])
