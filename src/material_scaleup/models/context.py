# src/material_scaleup/models/context.py

from pydantic import BaseModel, Field

from .evidence import Evidence
from .scenario import ScaleUpScenario
from .trade import AvailabilityResult

__all__ = [
    "AssessmentContext",
]


class AssessmentContext(BaseModel):
    """
    Complete evidence packet supplied to an assessment workflow.

    Attributes:
        scenario (ScaleUpScenario):
            The scale-up scenario being assessed.

        evidence (list[Evidence]):
            The list of evidence related to the scale-up assessment.

        assumptions (list[str]):
            List of assumptions made in the scale-up assessment.

        data_gaps (list[str]):
            List of identified data gaps in the scale-up assessment.
    """

    scenario: ScaleUpScenario
    evidence: list[Evidence] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    trade_availability: list[AvailabilityResult] = Field(default_factory=list)
