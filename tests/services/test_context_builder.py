# tests/services/test_context_builder.py

from pathlib import Path

import pytest

from material_scaleup.models.categories import (
    AssessmentCategory,
    RouteOrigin,
)
from material_scaleup.models.chemical import MaterialSpec
from material_scaleup.models.scenario import (
    LocationSpec,
    ProcessInput,
    ProductionTarget,
    ScaleUpScenario,
    SynthesisRoute,
)
from material_scaleup.providers.pubchem import PubChemProvider
from material_scaleup.providers.pubchem_safety import (
    PubChemSafetyProvider,
)
from material_scaleup.providers.usgs import USGSCommodityProvider
from material_scaleup.providers.world_bank import (
    WorldBankCommodityProvider,
)
from material_scaleup.resolvers.commodity import (
    CuratedCommodityResolver,
)
from material_scaleup.services.context_builder import (
    AssessmentContextBuilder,
)

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

    assert any("water" in gap.casefold() for gap in context.data_gaps)
