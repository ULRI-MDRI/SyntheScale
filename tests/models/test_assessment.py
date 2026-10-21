
# tests/models/test_assessment.py

import pytest
from pydantic import ValidationError

from material_scaleup.models.assessment import RiskAssessment

def test_risk_score_within_range():
    assessment = RiskAssessment(
        score=50,
        summary="Moderate risk.",
    )

    assert assessment.score == 50

def test_risk_score_cannot_exceed_100():
    with pytest.raises(ValidationError):
        RiskAssessment(
            score=101,
            summary="Invalid.",
        )
