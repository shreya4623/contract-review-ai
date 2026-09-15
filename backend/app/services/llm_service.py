"""Wraps the OpenAI API so every call returns data validated against a
Pydantic model. This is the only place in the codebase that talks to OpenAI.

Design choices relevant to the "do not let the LLM invent evidence" and
"validate before accepting" requirements:
  - We always pass the OpenAI structured-output feature (`response_format`
    with a JSON schema) so the model cannot return free text.
  - Callers are responsible for cross-checking any returned "evidence" string
    against the actual source text (see reviewer_agent.py) - this service
    only guarantees *shape*, not *truthfulness*.
"""
import json
import logging
from typing import Type, TypeVar

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T", bound=BaseModel)


class LLMServiceError(Exception):
    """Raised when the LLM call fails or returns data that can't be validated."""


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise LLMServiceError(
            "OPENAI_API_KEY is not set. Add it to your .env file before running reviews."
        )
    return OpenAI(api_key=settings.openai_api_key)


def call_structured(
    system_prompt: str,
    user_prompt: str,
    response_model: Type[T],
    temperature: float = 0.0,
) -> T:
    """Call the OpenAI chat completions API and parse the response into
    `response_model`. Raises LLMServiceError on any failure so callers can
    handle it gracefully instead of crashing the workflow."""
    schema = response_model.model_json_schema()

    try:
        client = _client()
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"{user_prompt}\n\n"
                        "Respond with ONLY a single JSON object that matches this JSON "
                        f"schema exactly, no prose, no markdown fences:\n{json.dumps(schema)}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )
    except OpenAIError as exc:
        logger.error("OpenAI API call failed: %s", exc)
        raise LLMServiceError(f"OpenAI API call failed: {exc}") from exc

    raw_content = response.choices[0].message.content or "{}"

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", raw_content[:500])
        raise LLMServiceError("LLM returned a response that was not valid JSON.") from exc

    try:
        return response_model.model_validate(data)
    except ValidationError as exc:
        logger.error("LLM JSON failed schema validation: %s", exc)
        raise LLMServiceError(f"LLM output failed schema validation: {exc}") from exc
