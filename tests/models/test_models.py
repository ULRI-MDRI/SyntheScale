
import pytest
from pydantic import ValidationError

from material_scaleup.models.chemical import (
    ChemicalIdentity,
    MaterialSpec,
)
from material_scaleup.models.evidence import Evidence
from material_scaleup.models.scenario import (
    ScaleUpScenario,
    ApplicationSpec,
    LocationSpec,
    ProductionTarget,
)
from material_scaleup.models.assessment import RiskAssessment
from material_scaleup.models.categories import (
    AssessmentCategory,
    AssessmentStatus,
    EvidenceStatus,
)
from material_scaleup.models.source import Source

def test_chemical_does_not_require_cas_rn():
    chemical = ChemicalIdentity(
        name="Computational candidate A",
        formula="Li2AB4",
    )

    assert chemical.cas_rn is None


def test_chemical_requires_some_identifier():
    with pytest.raises(ValidationError):
        ChemicalIdentity()


def test_scenario_represents_location_and_scale():
    scenario = ScaleUpScenario(
        material=MaterialSpec(
            name="Candidate cathode material",
            formula="LiFePO4",
        ),
        application=ApplicationSpec(
            name="Lithium-ion battery cathode",
        ),
        production_location=LocationSpec(
            country="United States",
            region="Illinois",
        ),
        production_target=ProductionTarget(
            amount=1_000,
            units="kg",
            period="year",
        ),
    )

    assert scenario.production_target is not None
    assert scenario.production_target.amount == 1_000


def test_available_evidence_requires_source():
    with pytest.raises(ValidationError):
        Evidence(
            category=AssessmentCategory.COST,
            claim="Bulk price is available.",
            status=EvidenceStatus.AVAILABLE,
        )


def test_not_found_evidence_does_not_require_source():
    evidence = Evidence(
        category=AssessmentCategory.COST,
        claim="No suitable bulk price record was found.",
        status=EvidenceStatus.NOT_FOUND,
    )

    assert evidence.source is None


def test_assessed_risk_requires_score():
    with pytest.raises(ValidationError):
        RiskAssessment(
            category=AssessmentCategory.COST,
            status=AssessmentStatus.ASSESSED,
            summary="Cost was assessed.",
        )


def test_insufficient_data_must_not_have_score():
    with pytest.raises(ValidationError):
        RiskAssessment(
            category=AssessmentCategory.COST,
            status=AssessmentStatus.INSUFFICIENT_DATA,
            score=50,
            summary="Insufficient pricing data.",
        )


def test_assessed_risk_accepts_evidence():
    source = Source(name="Example authoritative source")

    evidence = Evidence(
        category=AssessmentCategory.AVAILABILITY,
        claim="Feedstock is commercially available.",
        source=source,
    )

    assessment = RiskAssessment(
        category=AssessmentCategory.AVAILABILITY,
        score=25,
        confidence=0.8,
        summary="Availability risk is relatively low.",
        evidence=[evidence],
    )

    assert assessment.evidence == [evidence]
