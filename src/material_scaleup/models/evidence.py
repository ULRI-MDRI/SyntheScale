
# src/material_scaleup/models/evidence.py

from pydantic import BaseModel, Field

from material_scaleup.models.assessment import AssessmentCategory
from material_scaleup.models.source import Source

__all__ = [
    "Evidence",
]

class Evidence(BaseModel):
    """
    A source-grounded fact used in a scale-up assessment.
    
    Attributes:
        category (AssessmentCategory):
            The category of the evidence.

        claim (str):
            The claim made by the evidence.

        value (str | int | float | bool | None):
            The value associated with the claim.

        units (str | None):
            The units of the value, if applicable.

        source (Source):
            The source from which the evidence was obtained.

        metadata (dict[str, str | int | float | bool | None]):
            Additional metadata related to the evidence.
    """
    category: AssessmentCategory
    claim: str
    value: str | int | float | bool | None = None
    units: str | None = None
    source: Source
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )
