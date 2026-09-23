"""Reads a prepared image with a vision model on Nebius Token Factory."""

import json
import math
from dataclasses import dataclass
from typing import Any

import openai
from openai import OpenAI

from app import prompts
from app.config import check_model_config, nebius_api_key, settings
from app.instructions import TAG, wrap
from app.templates import Template


class VisionError(RuntimeError):
    pass


def output_schema(template: Template) -> dict[str, Any]:
    """Always ask for {"records": [...]} so single and multi record templates parse the same way."""
    return {
        "type": "object",
        "properties": {
            "records": {
                "type": "array",
                "items": template.schema_,
                **({} if template.multi_record else {"maxItems": 1}),
            }
        },
        "required": ["records"],
    }


def system_prompt(template: Template) -> str:
    fields = []
    for name, spec in template.schema_.get("properties", {}).items():
        field = template.fields.get(name, {})
        line = f"- {name} ({spec.get('type', 'any')})"
        if hint := field.get("hint"):
            line += f": {hint}"
        if ref := field.get("reference"):
            values = template.references.get(ref, [])
            line += f". Must be one of: {', '.join(map(str, values))}"
        fields.append(line)

    return prompts.render(
        "system",
        required=("instructions_tag", "output_schema"),
        document_type=f"{template.name}. {template.description}",
        fields="\n".join(fields),
        one_record_per="row or entry on the document." if template.multi_record else "document.",
        instructions_tag=TAG,
        output_schema=json.dumps(output_schema(template)),
    )


def _client() -> OpenAI:
    return OpenAI(base_url=settings.nebius_base_url, api_key=nebius_api_key())


@dataclass
class ReadResult:
    records: list[dict[str, Any]]
    model: str
    structured_output: bool  # False if the model fell back to plain JSON mode
    prompt_tokens: int = 0
    completion_tokens: int = 0


def parse_records(content: str) -> list[dict[str, Any]]:
    # Models without structured output sometimes wrap the JSON in prose or ``` fences.
    start, end = content.find("{"), content.rfind("}")
    try:
        records = json.loads(content[start : end + 1])["records"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise VisionError("Model did not return the expected JSON") from e
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise VisionError("Model did not return a list of records")
    return records


MAX_RECORDS = 200
MAX_STRING_CHARS = 500


def _coerce(value: Any, type_: str | None) -> Any:
    """Returns `value` as the schema type, or None if it is not one (so it gets flagged as unreadable)."""
    if value is None or type_ is None:
        return value
    # Models sometimes write "null" or "n/a" as text instead of leaving a field empty.
    if isinstance(value, str) and value.strip().lower() in {"", "null", "none", "n/a", "na", "-"}:
        return None
    if type_ in ("integer", "number") and isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            return None
    if type_ == "integer" and isinstance(value, float) and value.is_integer():
        value = int(value)
    ok = {
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
        "boolean": isinstance(value, bool),
        "string": isinstance(value, str),
    }.get(type_, True)
    if not ok:
        return None
    return value[:MAX_STRING_CHARS] if isinstance(value, str) else value


def enforce_schema(records: list[dict[str, Any]], template: Template) -> list[dict[str, Any]]:
    """Don't trust the model to follow the schema (the plain JSON fallback doesn't enforce it, and text in
    the photo may try to steer it): keep only the template's fields, with the declared types."""
    properties = template.schema_.get("properties", {})
    records = records[: 1 if not template.multi_record else MAX_RECORDS]
    return [{name: _coerce(r.get(name), spec.get("type")) for name, spec in properties.items()} for r in records]


def read_image(
    data_url: str, template: Template, model: str | None = None, instructions: str | None = None
) -> ReadResult:
    """Reads the image with `model`, or VISION_MODEL if not given.

    `instructions` must already be cleaned (app.instructions.clean_instructions). They go in the user
    message, never the system prompt.
    """
    model = model or settings.vision_model
    if not model:
        check_model_config()  # raises ConfigError with fix steps

    user_text = prompts.render("user")
    if instructions:
        user_text += "\n\n" + wrap(instructions)

    messages = [
        {"role": "system", "content": system_prompt(template)},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]
    json_schema = {
        "type": "json_schema",
        "json_schema": {"name": "extraction", "schema": output_schema(template)},
    }

    client = _client()
    structured = True
    try:
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=0, response_format=json_schema
            )
        except openai.BadRequestError:
            # Not every model supports json_schema; fall back to plain JSON mode.
            structured = False
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=0, response_format={"type": "json_object"}
            )
    except openai.AuthenticationError as e:
        raise VisionError(
            "Token Factory rejected the API key (401). Check that the key in nebius_token.env is complete "
            "and not revoked, or create a new one at https://tokenfactory.nebius.com."
        ) from e
    except openai.NotFoundError as e:
        raise VisionError(
            f"Token Factory does not know the model '{model}'. Check VISION_MODEL in engine/.env "
            "against the model list (GET /v1/models)."
        ) from e
    except openai.OpenAIError as e:
        raise VisionError(f"Token Factory call failed: {e}") from e

    usage = response.usage
    return ReadResult(
        records=enforce_schema(parse_records(response.choices[0].message.content or ""), template),
        model=model,
        structured_output=structured,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
    )
