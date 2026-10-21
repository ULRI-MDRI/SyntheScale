# tests/providers/test_pubchem_safety.py

import pytest

from material_scaleup.models.categories import AssessmentCategory, RouteOrigin
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


def test_parse_ghs_evidence():
    provider = PubChemSafetyProvider()

    chemical = ChemicalIdentity(
        pubchem_cid=180,
        name="acetone",
        formula="C3H6O",
    )

    payload = {
        "Record": {
            "Section": [
                {
                    "TOCHeading": "Safety and Hazards",
                    "Section": [
                        {
                            "TOCHeading": "Hazards Identification",
                            "Section": [
                                {
                                    "TOCHeading": "GHS Classification",
                                    "Information": [
                                        {
                                            "Name": "Pictogram(s)",
                                            "Value": {
                                                "StringWithMarkup": [
                                                    {
                                                        "String": "  ",
                                                        "Markup": [
                                                            {"Extra": "Flammable"},
                                                            {"Extra": "Irritant"},
                                                        ],
                                                    }
                                                ]
                                            },
                                        },
                                        {
                                            "Name": "Signal",
                                            "Value": {"StringWithMarkup": [{"String": "Danger"}]},
                                        },
                                        {
                                            "Name": "GHS Hazard Statements",
                                            "Value": {
                                                "StringWithMarkup": [
                                                    {
                                                        "String": (
                                                            "H225: Highly flammable "
                                                            "liquid and vapor"
                                                        )
                                                    },
                                                    {
                                                        "String": (
                                                            "H319: Causes serious eye irritation"
                                                        )
                                                    },
                                                ]
                                            },
                                        },
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }

    evidence = provider._parse_ghs_evidence(
        chemical=chemical,
        payload=payload,
        source_url=("https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/180/JSON"),
    )

    assert len(evidence) == 5

    assert all(item.category == AssessmentCategory.SAFETY for item in evidence)

    values = {item.reported_value.value for item in evidence if item.reported_value is not None}

    assert values == {
        "Flammable",
        "Irritant",
        "Danger",
        "H225: Highly flammable liquid and vapor",
        "H319: Causes serious eye irritation",
    }


def test_missing_pubchem_cid_returns_not_found_evidence():
    provider = PubChemSafetyProvider()

    chemical = ChemicalIdentity(
        name="Computational candidate",
        formula="Li2AB4",
    )

    evidence = provider.get_chemical_evidence(chemical)

    assert len(evidence) == 1
    assert evidence[0].status.value == "not_found"


@pytest.mark.integration
def test_pubchem_safety_resolves_sodium_hydroxide():
    identity_provider = PubChemProvider()
    safety_provider = PubChemSafetyProvider()

    chemical = identity_provider.get_by_name("sodium hydroxide")

    evidence = safety_provider.get_chemical_evidence(chemical)

    assert evidence

    assert all(item.category == AssessmentCategory.SAFETY for item in evidence)

    assert any(item.reported_value is not None for item in evidence)


@pytest.mark.integration
def test_pubchem_safety_collects_route_input_evidence():
    identity_provider = PubChemProvider()
    safety_provider = PubChemSafetyProvider()

    sodium_silicate = identity_provider.get_by_name("sodium silicate")
    sodium_aluminate = identity_provider.get_by_name("sodium aluminate")
    sodium_hydroxide = identity_provider.get_by_name("sodium hydroxide")
    water = identity_provider.get_by_name("water")

    scenario = ScaleUpScenario(
        material=MaterialSpec(
            name="Zeolite 13X",
        ),
        production_location=LocationSpec(
            country="United States",
        ),
        production_target=ProductionTarget(
            amount=1.0,
            units="kg",
        ),
        synthesis_route=SynthesisRoute(
            name="Example hydrothermal synthesis",
            origin=RouteOrigin.USER_PROVIDED,
            inputs=[
                ProcessInput(
                    chemical=sodium_silicate,
                    role="silicon source",
                ),
                ProcessInput(
                    chemical=sodium_aluminate,
                    role="aluminum source",
                ),
                ProcessInput(
                    chemical=sodium_hydroxide,
                    role="mineralizer",
                ),
                ProcessInput(
                    chemical=water,
                    role="solvent",
                ),
            ],
        ),
    )

    evidence = safety_provider.get_evidence(scenario)

    assert evidence

    assert all(item.category == AssessmentCategory.SAFETY for item in evidence)

    chemicals = {item.metadata.get("chemical") for item in evidence}

    assert chemicals
