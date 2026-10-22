# tests/services/test_context_builder.py

from pathlib import Path
from unittest.mock import create_autospec, patch

import pytest

from material_scaleup.models.categories import (
    AssessmentCategory,
    RouteOrigin,
)
from material_scaleup.models.chemical import ChemicalIdentity, MaterialSpec
from material_scaleup.models.scenario import (
    LocationSpec,
    ProcessInput,
    ProductionTarget,
    ScaleUpScenario,
    SynthesisRoute,
)
from material_scaleup.providers.pubchem import PubChemProvider
from material_scaleup.providers.pubchem_safety import PubChemSafetyProvider
from material_scaleup.providers.usgs import USGSCommodityProvider
from material_scaleup.providers.world_bank import WorldBankCommodityProvider
from material_scaleup.resolvers.commodity import CuratedCommodityResolver
from material_scaleup.services.context_builder import (
    AssessmentContextBuilder,
)
from material_scaleup.services.llm_context_builder import build_llm_context

WORLD_BANK_PATH = Path("data/raw/world_bank/CMO-Historical-Data-Monthly.xlsx")

USGS_PATH = Path("data/raw/usgs/mcs2026/MCS2026_Commodities_Data.csv")


@pytest.mark.integration
def test_context_builder_assembles_zeolite_evidence():
    identity_provider = PubChemProvider()

    sodium_aluminate = identity_provider.get_by_name("sodium aluminate")
    sodium_silicate = identity_provider.get_by_name("sodium silicate")
    sodium_hydroxide = identity_provider.get_by_name("sodium hydroxide")
    water = identity_provider.get_by_name("water")

    scenario = ScaleUpScenario(
        material=MaterialSpec(
            name="Zeolite 13X",
            description=(
                "Example aluminosilicate material used to test the SyntheScale evidence pipeline."
            ),
        ),
        production_location=LocationSpec(
            country="United States",
            region="Illinois",
        ),
        production_target=ProductionTarget(amount=1.0, units="kg"),
        synthesis_route=SynthesisRoute(
            name="Example hydrothermal synthesis",
            origin=RouteOrigin.USER_PROVIDED,
            inputs=[
                ProcessInput(chemical=sodium_aluminate, role="aluminum source"),
                ProcessInput(chemical=sodium_silicate, role="silicon source"),
                ProcessInput(chemical=sodium_hydroxide, role="mineralizer"),
                ProcessInput(chemical=water, role="solvent"),
            ],
        ),
    )

    builder = AssessmentContextBuilder(
        commodity_resolver=CuratedCommodityResolver(),
        safety_provider=PubChemSafetyProvider(),
        world_bank_provider=WorldBankCommodityProvider(WORLD_BANK_PATH),
        usgs_provider=USGSCommodityProvider(USGS_PATH),
        market_history_months=60,
    )

    context = builder.build(scenario)

    llm_context = build_llm_context(context)

    assert llm_context.safety
    assert llm_context.markets
    assert llm_context.supply

    assert len(llm_context.model_dump_json(exclude_none=True)) < len(
        context.model_dump_json(exclude_none=True)
    )

    assert context.scenario == scenario
    assert context.evidence

    categories = {item.category for item in context.evidence}

    assert AssessmentCategory.SAFETY in categories
    assert AssessmentCategory.COST in categories
    assert AssessmentCategory.MARKET_VOLATILITY in categories
    assert AssessmentCategory.AVAILABILITY in categories
    assert AssessmentCategory.SUPPLY_CHAIN in categories

    assert all(
        item.source is not None for item in context.evidence if item.status.value == "available"
    )

    observation_types = {item.metadata.get("observation_type") for item in context.evidence}

    assert "latest_price" in observation_types
    assert "price_change" in observation_types
    assert "annualized_volatility" in observation_types
    assert "world_production" in observation_types
    assert "largest_country_production_share" in observation_types

    assert context.assumptions

    assert any(
        "commodity-market prices" in assumption.casefold() for assumption in context.assumptions
    )

    assert any("sodium hydroxide" in gap.casefold() for gap in context.data_gaps)

    assert not any("water" in gap.casefold() for gap in context.data_gaps)


@pytest.mark.parametrize(
    ("commodity", "world_bank_name", "usgs_name"),
    [
        ("Phosphate rocck", "Phosphate rock", "Phosphate Rock"),
        ("gold", "Gold", "Gold"),
        ("silicon", None, "Silicon"),
        ("silicone", None, None),
        ("unobtainium", None, None),
    ],
)
def test_context_builder_resolves_provider_catalogs_offline(
    local_world_bank_provider,
    local_usgs_provider,
    monkeypatch,
    commodity,
    world_bank_name,
    usgs_name,
):
    resolver = CuratedCommodityResolver()
    monkeypatch.setattr(resolver, "MAPPING", {"test precursor": [commodity]})
    safety_provider = create_autospec(PubChemSafetyProvider, instance=True)
    safety_provider.get_evidence.return_value = []
    scenario = ScaleUpScenario(
        material=MaterialSpec(name="Test material"),
        production_location=LocationSpec(country="United States"),
        production_target=ProductionTarget(amount=1, units="kg"),
        synthesis_route=SynthesisRoute(
            name="Offline test route",
            origin=RouteOrigin.USER_PROVIDED,
            inputs=[ProcessInput(chemical=ChemicalIdentity(name="test precursor"))],
        ),
    )
    builder = AssessmentContextBuilder(
        commodity_resolver=resolver,
        safety_provider=safety_provider,
        world_bank_provider=local_world_bank_provider,
        usgs_provider=local_usgs_provider,
    )
    with (
        patch.object(
            local_world_bank_provider,
            "get_price_history",
            wraps=local_world_bank_provider.get_price_history,
        ) as market_lookup,
        patch.object(
            local_usgs_provider, "get_records", wraps=local_usgs_provider.get_records
        ) as supply_lookup,
    ):
        context = builder.build(scenario)

    if world_bank_name is None:
        market_lookup.assert_not_called()
        assert (
            f"No World Bank commodity-price series is mapped for {commodity}." in context.data_gaps
        )
    else:
        market_lookup.assert_called_once_with(world_bank_name, months=60)
        assert any(
            item.metadata.get("commodity") == world_bank_name
            and item.metadata.get("observation_type") == "latest_price"
            for item in context.evidence
        )

    if usgs_name is None:
        supply_lookup.assert_not_called()
        assert f"No USGS commodity mapping is available for {commodity}." in context.data_gaps
    else:
        assert supply_lookup.called
        assert all(call.args[0] == usgs_name for call in supply_lookup.call_args_list)
        assert any(
            item.metadata.get("commodity") == usgs_name
            and item.metadata.get("observation_type") == "world_production"
            for item in context.evidence
        )

    assert len(context.data_gaps) == int(world_bank_name is None) + int(usgs_name is None)
    assert any("lexical matching" in assumption for assumption in context.assumptions)
