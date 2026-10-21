
# src/material_scaleup/models/assessment.py

from pydantic import BaseModel, Field

__all__ = [
    "Source",
    "RiskAssessment",
    "ScaleUpAssessment",
]

class Source(BaseModel):
    """
    Represents the source of information for an assessment.

    Attributes:
        title (str):
            The title of the source.

        url (str | None):
            The URL of the source, if available.

        provider (str | None):
            The provider of the source, if available.
    """
    title: str
    url: str | None = None
    provider: str | None = None

class RiskAssessment(BaseModel):
    """
    Represents a risk assessment for a particular aspect of a material.

    Attributes:
        score (float | None):
            The risk score, ranging from 0 to 100.

        summary (str):
            A brief summary of the assessment.

        evidence (list[str]):
            A list of evidence supporting the assessment.

        sources (list[Source]):
            A list of sources for the assessment.
    """
    score: float | None = Field(default=None, ge=0, le=100)
    summary: str
    evidence: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)

class ScaleUpAssessment(BaseModel):
    """
    Represents a scale-up assessment for a material.

    Attributes:
        material (str):
            The name of the material being assessed.

        availability (RiskAssessment | None):
            The risk assessment for material availability.

        cost (RiskAssessment | None):
            The risk assessment for material cost.

        market_volatility (RiskAssessment | None):
            The risk assessment for market volatility.

        supply_chain (RiskAssessment | None):
            The risk assessment for the supply chain.

        safety (RiskAssessment | None):
            The risk assessment for safety.

        regulatory (RiskAssessment | None):
            The risk assessment for regulatory compliance.

        overall_score (float | None):
            The overall risk score, ranging from 0 to 100.

        summary (str | None):
            A brief summary of the assessment.

        recommendations (list[str]):
            A list of recommendations based on the assessment.
    """
    material: str
    availability: RiskAssessment | None = None
    cost: RiskAssessment | None = None
    market_volatility: RiskAssessment | None = None
    supply_chain: RiskAssessment | None = None
    safety: RiskAssessment | None = None
    regulatory: RiskAssessment | None = None
    overall_score: float | None = Field(default=None, ge=0, le=100)
    summary: str | None = None
    recommendations: list[str] = Field(default_factory=list)
