"""AI provider service (Gemini + Ollama) for structured output."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings


class AIServiceError(Exception):
    """Raised when structured generation fails."""


def generate_structured(provider: str, task: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Generate schema-constrained JSON from the selected provider.

    Retries once with a correction prompt when JSON parsing or schema validation fails.
    """
    provider_name = provider.strip().lower()
    if provider_name not in {"gemini", "ollama"}:
        raise AIServiceError(f"Unsupported provider '{provider}'. Use 'gemini' or 'ollama'.")

    prompt = _build_prompt(task=task, payload=payload, schema=schema)
    last_error: Exception | None = None

    for attempt in range(2):
        raw = _call_provider(provider_name, prompt, schema)

        try:
            parsed = _parse_provider_output(raw)
            _validate_against_schema(parsed, schema)
            return parsed
        except Exception as exc:  # noqa: BLE001 - return useful provider failure
            last_error = exc
            if attempt == 0:
                prompt = _build_correction_prompt(task=task, payload=payload, schema=schema, bad_output=raw, error=exc)
                continue
            break

    raise AIServiceError(
        f"{provider_name} failed to return valid structured JSON after 2 attempts: {last_error}"
    )


def _call_provider(provider: str, prompt: str, schema: dict[str, Any]) -> str | dict[str, Any]:
    if provider == "gemini":
        return _call_gemini(prompt, schema)
    return _call_ollama(prompt, schema)


def _call_gemini(prompt: str, schema: dict[str, Any]) -> str | dict[str, Any]:
    if not settings.gemini_api_key:
        raise AIServiceError("GEMINI_API_KEY is not configured")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise AIServiceError("Gemini SDK is not installed. Add 'google-genai' to dependencies.") from exc

    client = genai.Client(api_key=settings.gemini_api_key)

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )

    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, dict):
        return parsed

    text = getattr(response, "text", None)
    if not text:
        raise AIServiceError("Gemini returned an empty response")
    return text


def _call_ollama(prompt: str, schema: dict[str, Any]) -> str | dict[str, Any]:
    url = settings.ollama_base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "format": schema,
    }

    try:
        response = httpx.post(url, json=payload, timeout=45.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AIServiceError(f"Ollama request failed: {exc}") from exc

    data = response.json()
    if "response" not in data:
        raise AIServiceError("Ollama response missing 'response' field")

    return data["response"]


def _parse_provider_output(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw

    if not isinstance(raw, str):
        raise ValueError(f"Provider returned non-string/non-object output: {type(raw).__name__}")

    normalized = _strip_code_fences(raw)

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("JSON must be an object")

    return parsed


def _strip_code_fences(text: str) -> str:
    """Normalize fenced markdown JSON to plain JSON text."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()

    return stripped


def _build_prompt(task: str, payload: dict[str, Any], schema: dict[str, Any]) -> str:
    return (
        "You are a structured-output engine. "
        "Return only JSON that matches the provided schema exactly.\n\n"
        f"Task:\n{task}\n\n"
        f"Input payload:\n{json.dumps(payload, ensure_ascii=True)}\n\n"
        f"JSON schema:\n{json.dumps(schema, ensure_ascii=True)}"
    )


def _build_correction_prompt(
    task: str,
    payload: dict[str, Any],
    schema: dict[str, Any],
    bad_output: str | dict[str, Any],
    error: Exception,
) -> str:
    return (
        "Your previous output was invalid. Fix it and return only valid JSON.\n\n"
        f"Validation error:\n{error}\n\n"
        f"Previous invalid output:\n{bad_output}\n\n"
        + _build_prompt(task=task, payload=payload, schema=schema)
    )


def _validate_against_schema(data: dict[str, Any], schema: dict[str, Any], path: str = "$") -> None:
    schema_type = schema.get("type")
    if schema_type and not _is_type(data, schema_type):
        raise ValueError(f"{path}: expected type '{schema_type}'")

    if schema_type == "object":
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                raise ValueError(f"{path}: missing required field '{key}'")

        properties = schema.get("properties", {})
        for key, value in data.items():
            if key in properties:
                _validate_value(value, properties[key], f"{path}.{key}")


def _validate_value(value: Any, schema: dict[str, Any], path: str) -> None:
    schema_type = schema.get("type")
    if schema_type and not _is_type(value, schema_type):
        raise ValueError(f"{path}: expected type '{schema_type}'")

    if schema_type == "object" and isinstance(value, dict):
        _validate_against_schema(value, schema, path)
        return

    if schema_type == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(value):
                _validate_value(item, item_schema, f"{path}[{idx}]")


def _is_type(value: Any, schema_type: str) -> bool:
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "null":
        return value is None
    return True
