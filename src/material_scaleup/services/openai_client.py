# src/material_scaleup/services/openai_client.py

import os

from openai import OpenAI

from material_scaleup.services.openai_assessment_generator import (
    OpenAIAssessmentGenerator,
)

__all__ = [
    "create_assessment_generator_from_environment",
]


def create_assessment_generator_from_environment() -> OpenAIAssessmentGenerator:
    """
    Create an assessment generator from environment variables.

    Returns:
        OpenAIAssessmentGenerator:
            An instance of the assessment generator initialized with the
            environment variables.

    Raises:
        RuntimeError:
            If the required environment variables are not configured.
    """

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("SYNTHE_SCALE_MODEL")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    if not model:
        raise RuntimeError("SYNTHE_SCALE_MODEL is not configured.")

    client_kwargs: dict[str, str] = {"api_key": api_key}

    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs) # pyright: ignore[reportArgumentType]

    return OpenAIAssessmentGenerator(client=client, model=model)
