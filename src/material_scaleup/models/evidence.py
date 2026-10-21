
# src/material_scaleup/models/evidence.py

from datetime import datetime

from pydantic import BaseModel, Field

from material_scaleup.models.assessment import AssessmentCategory

__all__ = [
    "EvidenceSource",
    "Evidence",
]

class EvidenceSource(BaseModel):
    """
    Source from which a piece of evidence was obtained.
    
    Attributes:
        name (str):
            The name of the source.

        url (str | None):
            The URL of the source, if available.

        accessed_at (datetime | None):
            The date and time when the source was accessed.
    """
    name: str
    url: str | None = None
    accessed_at: datetime | None = None

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

        source (EvidenceSource):
            The source from which the evidence was obtained.

        metadata (dict[str, str | int | float | bool | None]):
            Additional metadata related to the evidence.
    """
    category: AssessmentCategory
    claim: str
    value: str | int | float | bool | None = None
    units: str | None = None
    source: EvidenceSource
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )
