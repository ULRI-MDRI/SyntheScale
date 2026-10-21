
# src/material_scaleup/models/context.py

from pydantic import BaseModel, Field

from .chemical import ChemicalIdentity
from .evidence import Evidence

__all__ = [
    "AssessmentContext",
]

class AssessmentContext(BaseModel):
    """
    Assessment context for a scale-up evaluation.

    Attributes:
        chemical (ChemicalIdentity):
            The chemical being assessed.

        evidence (list[Evidence]):
            The list of evidence related to the chemical.
    """
    chemical: ChemicalIdentity
    evidence: list[Evidence] = Field(default_factory=list)
