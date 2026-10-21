
# src/material_scaleup/models/evidence.py

from datetime import date

from pydantic import BaseModel, Field, model_validator

from material_scaleup.models.categories import (
    AssessmentCategory,
    EvidenceStatus,
)
from material_scaleup.models.source import Source

__all__ = [
    "Evidence",
    "EvidenceScope",
    "EvidenceValue",
]

class EvidenceValue(BaseModel):
    """
    A typed value reported by a source.
    
    Attributes:
        value (str | int | float | bool):
            The value reported by the source.

        units (str | None):
            The units of the value, if applicable.
    """
    value: str | int | float | bool
    units: str | None = None

class EvidenceScope(BaseModel):
    """
    Geographic, temporal, and market scope of a piece of evidence.
    
    Attributes:
        country (str | None):
            The country relevant to the evidence.

        region (str | None):
            The region relevant to the evidence.

        effective_date (date | None):
            The date when the evidence is effective.

        period_start (date | None):
            The start date of the period covered by the evidence.

        period_end (date | None):
            The end date of the period covered by the evidence.

        market_basis (str | None):
            The market context for the evidence.

        scale_basis (str | None):
            The scale context for the evidence.
    """
    country: str | None = None
    region: str | None = None
    effective_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    market_basis: str | None = None
    scale_basis: str | None = None

class Evidence(BaseModel):
    """
    A source-grounded fact used in a scale-up assessment.
    
    Attributes:
        category (AssessmentCategory):
            The category of the evidence.

        claim (str):
            The claim made by the evidence.

        status (EvidenceStatus):
            The status of the evidence.

        reported_value (EvidenceValue | None):
            The value reported by the evidence, if applicable.

        source (Source | None):
            The source of the evidence, if available.

        scope (EvidenceScope | None):
            The scope of the evidence, if applicable.

        confidence (float | None):
            The confidence level of the evidence, between 0 and 1.

        notes (str | None):
            Additional notes about the evidence.

        metadata (dict[str, str | int | float | bool | None]):
            Additional metadata associated with the evidence.
    """
    category: AssessmentCategory
    claim: str
    status: EvidenceStatus = EvidenceStatus.AVAILABLE
    reported_value: EvidenceValue | None = None
    source: Source | None = None
    scope: EvidenceScope | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None
    metadata: dict[
        str,
        str | int | float | bool | None,
    ] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_available_evidence(self) -> "Evidence":
        """Require a source when evidence is reported as available."""

        if self.status == EvidenceStatus.AVAILABLE and self.source is None:
            raise ValueError(
                "Available evidence must identify its source."
            )

        return self
    