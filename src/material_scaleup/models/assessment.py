
# src/material_scaleup/models/assessment.py

from pydantic import BaseModel, Field, model_validator

from material_scaleup.models.categories import (
    AssessmentCategory,
    AssessmentStatus,
    Priority,
)
from material_scaleup.models.evidence import Evidence
from material_scaleup.models.scenario import ScaleUpScenario

__all__ = [
    "Barrier",
    "RiskAssessment",
    "ScaleUpAssessment",
    "ValidationAction",
]

class RiskAssessment(BaseModel):
    """
    Assessment of one scale-up risk category.
    
    Attributes:
        category (AssessmentCategory):
            The risk category being assessed.

        status (AssessmentStatus):
            The current status of the assessment.

        score (float | None):
            The numerical score of the assessment, if available.

        confidence (float | None):
            The confidence level in the assessment score.

        summary (str):
            A brief summary of the assessment findings.

        evidence (list[Evidence]):
            Supporting evidence for the assessment.

        assumptions (list[str]):
            Assumptions made during the assessment.

        data_gaps (list[str]):
            Identified gaps in the available data.

        recommendations (list[str]):
            Recommended actions based on the assessment.
    """
    category: AssessmentCategory
    status: AssessmentStatus = AssessmentStatus.ASSESSED
    score: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    summary: str
    evidence: list[Evidence] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_assessment_status(self) -> "RiskAssessment":
        """Keep score semantics consistent with assessment status."""
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
            raise ValueError(
                f"Assessment status '{self.status}' must not include a score."
            )

        return self

class Barrier(BaseModel):
    """
    A major barrier to scaling the proposed production scenario.
    
    Attributes:
        title (str):
            The title of the barrier.

        description (str):
            A detailed description of the barrier.

        severity (float):
            The severity of the barrier, on a scale from 0 to 100.

        confidence (float | None):
            The confidence level in the severity assessment.

        affected_categories (list[AssessmentCategory]):
            The risk categories affected by this barrier.

        evidence (list[Evidence]):
            Supporting evidence for the barrier.
    """
    title: str
    description: str
    severity: float = Field(ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    affected_categories: list[AssessmentCategory] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)

class ValidationAction(BaseModel):
    """
    A recommended experiment, analysis, or data-gathering action.
    
    Attributes:
        question (str):
            The question that the validation action aims to address.

        rationale (str):
            The reasoning behind why this validation action is recommended.

        priority (Priority):
            The priority level of the validation action.

        suggested_method (str | None):
            The suggested method for carrying out the validation action.

        expected_decision_impact (str | None):
            The expected impact of the validation action on decision-making.

        affected_categories (list[AssessmentCategory]):
            The risk categories affected by this validation action.
    """
    question: str
    rationale: str
    priority: Priority
    suggested_method: str | None = None
    expected_decision_impact: str | None = None
    affected_categories: list[AssessmentCategory] = Field(default_factory=list)

class ScaleUpAssessment(BaseModel):
    """
    Overall assessment of a specific scale-up scenario.
    
    Attributes:
        scenario (ScaleUpScenario):
            The scale-up scenario being assessed.

        category_assessments (list[RiskAssessment]):
            Assessments for each risk category.

        major_barriers (list[Barrier]):
            The major barriers identified in the assessment.

        strengths (list[str]):
            The strengths identified in the assessment.

        validation_actions (list[ValidationAction]):
            Recommended validation actions.

        assumptions (list[str]):
            Assumptions made during the assessment.

        data_gaps (list[str]):
            Identified data gaps.

        overall_score (float | None):
            The overall score for the scale-up scenario.

        overall_confidence (float | None):
            The overall confidence in the assessment.

        executive_summary (str | None):
            A summary of the assessment for executive review.
    """
    scenario: ScaleUpScenario
    category_assessments: list[RiskAssessment] = Field(default_factory=list)
    major_barriers: list[Barrier] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    validation_actions: list[ValidationAction] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    overall_score: float | None = Field(default=None, ge=0, le=100)
    overall_confidence: float | None = Field(default=None, ge=0, le=1)
    executive_summary: str | None = None

    @model_validator(mode="after")
    def require_assessment_for_overall_score(self) -> "ScaleUpAssessment":
        if self.overall_score is not None and not self.category_assessments:
            raise ValueError(
                "An overall score requires at least one category assessment."
            )

        return self

    def get_category(self, category: AssessmentCategory) -> RiskAssessment | None:
        """
        Return the assessment for a category, if present.
        
        Args:
            category (AssessmentCategory):
                The category for which to retrieve the assessment.

        Returns:
            RiskAssessment | None:
                The assessment for the specified category, or None if not present.
        """
        return next(
            (
                assessment
                for assessment in self.category_assessments
                if assessment.category == category
            ),
            None,
        )
    