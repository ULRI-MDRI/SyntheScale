# src/material_scaleup/services/assessment_generator.py

from abc import ABC, abstractmethod

from material_scaleup.models.generated_assessment import GeneratedAssessment
from material_scaleup.models.llm_context import LLMContext

__all__ = [
    "AssessmentGenerator",
]


class AssessmentGenerator(ABC):
    """Generate an assessment from compact, grounded context."""

    @abstractmethod
    def generate(self, context: LLMContext) -> GeneratedAssessment:
        """
        Generate a structured assessment.

        Args:
            context (LLMContext):
                The compact, grounded context to generate the assessment from.

        Returns:
            GeneratedAssessment:
                The structured assessment generated from the context.
        """
        raise NotImplementedError
