# src/material_scaleup/services/openai_assessment_generator.py

from typing import Any

from material_scaleup.models.generated_assessment import GeneratedAssessment
from material_scaleup.models.llm_context import LLMContext
from material_scaleup.services.assessment_generator import AssessmentGenerator
from material_scaleup.services.assessment_prompts import (
    SYSTEM_INSTRUCTIONS,
    build_assessment_prompt,
)

__all__ = [
    "AssessmentGenerationError",
    "OpenAIAssessmentGenerator",
]


class AssessmentGenerationError(RuntimeError):
    """Raised when an AI assessment cannot be generated."""


class OpenAIAssessmentGenerator(AssessmentGenerator):
    """Generate assessments using an OpenAI-compatible client."""

    def __init__(self, *, client: Any, model: str) -> None:
        if not model.strip():
            raise ValueError("model must not be empty.")

        self.client = client
        self.model = model

    def generate(self, context: LLMContext) -> GeneratedAssessment:
        """
        Generate and validate a structured assessment.

        Args:
            context (LLMContext):
                The context for generating the assessment.

        Returns:
            GeneratedAssessment:
                The generated and validated assessment.

        Raises:
            AssessmentGenerationError:
                If the assessment could not be generated or validated.
        """

        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": SYSTEM_INSTRUCTIONS,
                    },
                    {
                        "role": "user",
                        "content": build_assessment_prompt(context),
                    },
                ],
                text_format=GeneratedAssessment,
            )

        except Exception as error:
            raise AssessmentGenerationError("The language-model request failed.") from error

        parsed = response.output_parsed

        if parsed is None:
            raise AssessmentGenerationError(
                "The language model did not return a parsed assessment. "
                "The response may have been refused or incomplete."
            )

        if not isinstance(parsed, GeneratedAssessment):
            raise AssessmentGenerationError(
                "The language model returned an unexpected structured-output type."
            )

        return parsed
