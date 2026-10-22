# src/material_scaleup/models/generated_assessment.py

from pydantic import BaseModel, Field, model_validator

from material_scaleup.models.categories import (
    AssessmentCategory,
    AssessmentStatus,
    Priority,
)

__all__ = [
    "GeneratedAssessment",
    "GeneratedBarrier",
    "GeneratedCategoryAssessment",
    "GeneratedValidationAction",
]


class GeneratedCategoryAssessment(BaseModel):
    """
    AI-generated interpretation of one assessment category.

    Attributes:
        category (AssessmentCategory):
            The assessment category being interpreted.

        status (AssessmentStatus):
            The assessment status for this category.

        score (float | None):
            The numeric score for this category, if assessed.

        confidence (float | None):
            The confidence level in the assessment.

        summary (str):
            A brief summary of the assessment.

        supporting_facts (list[str]):
            List of supporting facts for the assessment.

        assumptions (list[str]):
            List of assumptions made during the assessment.

        data_gaps (list[str]):
            List of identified data gaps.

        recommendations (list[str]):
            List of recommendations based on the assessment.
    """

    category: AssessmentCategory
    status: AssessmentStatus
    score: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    summary: str
    supporting_facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_score_status(self) -> "GeneratedCategoryAssessment":
        """Keep score semantics consistent with status."""

        if self.status == AssessmentStatus.ASSESSED and self.score is None:
            raise ValueError("An assessed category must include a score.")

        if (
            self.status
            in {
                AssessmentStatus.INSUFFICIENT_DATA,
                AssessmentStatus.NOT_APPLICABLE,
                AssessmentStatus.ERROR,
            }
            and self.score is not None
        ):
            raise ValueError(f"Assessment status '{self.status}' must not include a score.")

        return self


class GeneratedBarrier(BaseModel):
    """
    Major scale-up barrier identified from supplied evidence.

    Attributes:
        title (str):
            The title of the barrier.

        description (str):
            A detailed description of the barrier.

        severity (float):
            The severity of the barrier, on a scale from 0 to 100.

        confidence (float | None):
            The confidence level in the assessment of this barrier.

        affected_categories (list[AssessmentCategory]):
            List of assessment categories affected by this barrier.

        supporting_facts (list[str]):
            List of supporting facts for the barrier.
    """

    title: str
    description: str
    severity: float = Field(ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    affected_categories: list[AssessmentCategory] = Field(default_factory=list)
    supporting_facts: list[str] = Field(default_factory=list)


class GeneratedValidationAction(BaseModel):
    """
    Recommended next experiment, lookup, or validation activity.

    Attributes:
        question (str):
            The question this validation action aims to address.

        rationale (str):
            The reasoning behind why this action is recommended.

        priority (Priority):
            The priority level of this action.

        suggested_method (str | None):
            The suggested method for carrying out this action, if any.

        expected_decision_impact (str | None):
            The expected impact of this action on decision-making, if any.

        affected_categories (list[AssessmentCategory]):
            List of assessment categories affected by this action.
    """

    question: str
    rationale: str
    priority: Priority
    suggested_method: str | None = None
    expected_decision_impact: str | None = None
    affected_categories: list[AssessmentCategory] = Field(default_factory=list)


class GeneratedAssessment(BaseModel):
    """
    Structured interpretation generated from an LLMContext.

    The trusted scenario and full evidence provenance remain outside
    this model and should be attached by application code.

    Attributes:
        category_assessments (list[GeneratedCategoryAssessment]):
            List of category assessments included in this assessment.

        major_barriers (list[GeneratedBarrier]):
            List of major barriers identified in this assessment.

        strengths (list[str]):
            List of strengths identified in this assessment.

        validation_actions (list[GeneratedValidationAction]):
            List of recommended validation actions.

        assumptions (list[str]):
            List of assumptions made in this assessment.

        data_gaps (list[str]):
            List of identified data gaps.

        overall_score (float | None):
            The overall score of the assessment, if available.

        overall_confidence (float | None):
            The overall confidence level of the assessment, if available.

        executive_summary (str):
            A summary of the key findings and conclusions of the assessment.
    """

    category_assessments: list[GeneratedCategoryAssessment] = Field(default_factory=list)

    major_barriers: list[GeneratedBarrier] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)

    validation_actions: list[GeneratedValidationAction] = Field(default_factory=list)

    assumptions: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    overall_score: float | None = Field(default=None, ge=0, le=100)
    overall_confidence: float | None = Field(default=None, ge=0, le=1)
    executive_summary: str

    @model_validator(mode="after")
    def validate_overall_score(self) -> "GeneratedAssessment":
        """Require assessed categories before returning an overall score."""

        assessed = [
            item for item in self.category_assessments if item.status == AssessmentStatus.ASSESSED
        ]

        if self.overall_score is not None and not assessed:
            raise ValueError("An overall score requires at least one assessed category.")

        return self
