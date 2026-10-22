# tests/services/test_llm_context_builder.py

from material_scaleup.models.categories import AssessmentCategory
from material_scaleup.models.chemical import (
    ChemicalIdentity,
    MaterialSpec,
)
from material_scaleup.models.context import AssessmentContext
from material_scaleup.models.evidence import Evidence, EvidenceValue
from material_scaleup.models.scenario import (
    ProcessInput,
    ScaleUpScenario,
    SynthesisRoute,
)
from material_scaleup.models.source import Source
from material_scaleup.services.llm_context_builder import build_llm_context


def test_llm_context_deduplicates_safety_evidence():
    source = Source(
        name="PubChem",
        publisher="National Library of Medicine",
    )

    chemical = ChemicalIdentity(
        name="sodium hydroxide",
        formula="HNaO",
        pubchem_cid=14798,
    )

    scenario = ScaleUpScenario(
        material=MaterialSpec(name="Example material"),
        synthesis_route=SynthesisRoute(
            name="Example route",
            inputs=[ProcessInput(chemical=chemical, role="mineralizer")],
        ),
    )

    evidence = [
        Evidence(
            category=AssessmentCategory.SAFETY,
            claim="GHS signal word for sodium hydroxide",
            reported_value=EvidenceValue(value="Danger"),
            source=source,
            metadata={"chemical": "sodium hydroxide", "pubchem_cid": 14798},
        ),
        Evidence(
            category=AssessmentCategory.SAFETY,
            claim="GHS signal word for sodium hydroxide",
            reported_value=EvidenceValue(value="Danger"),
            source=source,
            metadata={"chemical": "sodium hydroxide", "pubchem_cid": 14798},
        ),
        Evidence(
            category=AssessmentCategory.SAFETY,
            claim="GHS hazard statement for sodium hydroxide",
            reported_value=EvidenceValue(
                value=(
                    "H314 (> 99.9%): Causes severe skin burns and eye damage "
                    "[Danger Skin corrosion/irritation]"
                )
            ),
            source=source,
            metadata={"chemical": "sodium hydroxide", "pubchem_cid": 14798},
        ),
        Evidence(
            category=AssessmentCategory.SAFETY,
            claim="GHS hazard statement for sodium hydroxide",
            reported_value=EvidenceValue(
                value=(
                    "H314: Causes severe skin burns and eye damage "
                    "[Danger Skin corrosion/irritation]"
                )
            ),
            source=source,
            metadata={"chemical": "sodium hydroxide", "pubchem_cid": 14798},
        ),
    ]

    full_context = AssessmentContext(scenario=scenario, evidence=evidence)

    llm_context = build_llm_context(full_context)

    assert len(llm_context.safety) == 1

    summary = llm_context.safety[0]

    assert summary.chemical == "sodium hydroxide"
    assert summary.formula == "HNaO"
    assert summary.signal_words == ["Danger"]

    assert summary.hazard_statements == ["H314: Causes severe skin burns and eye damage"]

    assert len(summary.sources) == 1


def test_llm_context_uses_compact_scenario():
    chemical = ChemicalIdentity(
        name="sodium aluminate",
        formula="AlNaO2",
        canonical_smiles="O=[Al-]=O.[Na+]",
        inchi="InChI=1S/Al.Na.2O/q-1;+1;;",
        inchikey="IYJYQHRNMMNLRH-UHFFFAOYSA-N",
    )

    scenario = ScaleUpScenario(
        material=MaterialSpec(name="Zeolite 13X"),
        synthesis_route=SynthesisRoute(
            name="Example hydrothermal synthesis",
            inputs=[ProcessInput(chemical=chemical, role="aluminum source")],
        ),
    )

    context = AssessmentContext(scenario=scenario)

    llm_context = build_llm_context(context)

    assert llm_context.scenario.material_name == "Zeolite 13X"

    chemical_input = llm_context.scenario.chemical_inputs[0]

    assert chemical_input.name == "sodium aluminate"
    assert chemical_input.formula == "AlNaO2"

    dumped = llm_context.model_dump()

    assert "canonical_smiles" not in str(dumped)
    assert "inchikey" not in str(dumped)
