# tests/services/test_assessment_prompts.py

from material_scaleup.models.llm_context import LLMContext, LLMScenarioSummary
from material_scaleup.services.assessment_prompts import build_assessment_prompt


def test_prompt_contains_context_and_cost_guardrail():
    context = LLMContext(
        scenario=LLMScenarioSummary(
            material_name="Zeolite 13X",
            production_location="Illinois, United States",
        ),
        assumptions=["Commodity prices are market proxies."],
        data_gaps=["Direct precursor pricing is unavailable."],
    )

    prompt = build_assessment_prompt(context)

    assert "Zeolite 13X" in prompt
    assert "Illinois, United States" in prompt
    assert "Direct precursor pricing is unavailable" in prompt

    assert "Do not estimate total manufacturing cost" in prompt
