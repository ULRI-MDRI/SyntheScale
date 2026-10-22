# tests/services/test_openai_assessment_generator.py

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from material_scaleup.models.generated_assessment import GeneratedAssessment
from material_scaleup.models.llm_context import (
    LLMContext,
    LLMScenarioSummary,
)
from material_scaleup.services.openai_assessment_generator import (
    AssessmentGenerationError,
    OpenAIAssessmentGenerator,
)


@pytest.fixture
def llm_context() -> LLMContext:
    return LLMContext(
        scenario=LLMScenarioSummary(material_name="Zeolite 13X"),
        assumptions=["Commodity prices are upstream market proxies."],
        data_gaps=["Direct precursor pricing is unavailable."],
    )


def test_generator_returns_parsed_assessment(llm_context: LLMContext):
    generated = GeneratedAssessment(
        category_assessments=[],
        major_barriers=[],
        strengths=[],
        validation_actions=[],
        assumptions=[],
        data_gaps=["Direct precursor pricing is unavailable."],
        overall_score=None,
        overall_confidence=0.4,
        executive_summary=("The available evidence supports only a preliminary assessment."),
    )

    parse = Mock(return_value=SimpleNamespace(output_parsed=generated))

    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))

    generator = OpenAIAssessmentGenerator(client=client, model="test-model")

    result = generator.generate(llm_context)

    assert result == generated

    parse.assert_called_once()

    call = parse.call_args.kwargs

    assert call["model"] == "test-model"
    assert call["text_format"] is GeneratedAssessment

    messages = call["input"]

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    assert "Zeolite 13X" in messages[1]["content"]


def test_generator_rejects_missing_parsed_output(llm_context: LLMContext):
    client = SimpleNamespace(
        responses=SimpleNamespace(parse=Mock(return_value=SimpleNamespace(output_parsed=None)))
    )

    generator = OpenAIAssessmentGenerator(client=client, model="test-model")

    with pytest.raises(
        AssessmentGenerationError,
        match="did not return a parsed assessment",
    ):
        generator.generate(llm_context)


def test_generator_wraps_client_error(llm_context: LLMContext):
    client = SimpleNamespace(
        responses=SimpleNamespace(parse=Mock(side_effect=RuntimeError("API unavailable")))
    )

    generator = OpenAIAssessmentGenerator(client=client, model="test-model")

    with pytest.raises(AssessmentGenerationError, match="request failed"):
        generator.generate(llm_context)


def test_generator_rejects_empty_model_name():
    with pytest.raises(ValueError, match="model must not be empty"):
        OpenAIAssessmentGenerator(client=object(), model=" ")
