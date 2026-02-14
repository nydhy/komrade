from __future__ import annotations

import json
import re
from urllib import request
from typing import Any, Type, TypeVar

import google.generativeai as genai
from pydantic import BaseModel, ValidationError

from app.schemas import LadderResult, TranslateResult
from app.settings import settings

T = TypeVar("T", bound=BaseModel)

SELF_HARM_PATTERNS = [
    "suicide",
    "kill myself",
    "end my life",
    "self harm",
    "hurt myself",
    "don't want to live",
    "do not want to live",
    "want to die",
]


def has_self_harm_keywords(message: str) -> bool:
    lowered = message.lower()
    return any(pattern in lowered for pattern in SELF_HARM_PATTERNS)


def crisis_safe_response() -> TranslateResult:
    return TranslateResult(
        generic_answer=(
            "I'm really glad you reached out. If you might be in immediate danger, "
            "please call 911 now."
        ),
        empathetic_personalized_answer=(
            "You don't have to carry this alone. If you're in the U.S., call or text 988 "
            "for the Suicide & Crisis Lifeline (24/7). Veterans can press 1 after dialing 988, "
            "or text 838255 to reach the Veterans Crisis Line. If you can, contact a trusted "
            "friend, buddy, or family member and stay with them right now."
        ),
        safety_flag="crisis",
    )


class GeminiService:
    def __init__(self) -> None:
        configured_provider = settings.ai_provider.lower().strip()
        if configured_provider in {"auto", ""}:
            self.provider = "gemini" if settings.gemini_api_key else "ollama"
        elif configured_provider == "gemini":
            self.provider = "gemini"
        elif configured_provider == "ollama":
            self.provider = "ollama"
        else:
            raise ValueError("Unsupported AI_PROVIDER. Use 'auto', 'gemini', or 'ollama'.")

        if self.provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is missing in environment.")
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
        elif self.provider == "ollama":
            self.model = None

    def generate_ladder(self, intake: dict[str, Any]) -> LadderResult:
        prompt = (
            "You are creating a veteran social exposure ladder.\n"
            "Return STRICT JSON with this exact structure:\n"
            '{ "weeks": [ {"week":1,"title":"...","difficulty":"low|med|high","rationale":"...","suggested_time":"..."} ] }\n'
            "Requirements:\n"
            "- Exactly 8 week objects, week values 1..8 in order.\n"
            "- Progressive and practical challenges.\n"
            "- No markdown, no explanation outside JSON.\n\n"
            f"Intake JSON:\n{json.dumps(intake)}"
        )
        return self._generate_and_validate(prompt, LadderResult)

    def translate_context(self, message: str, context: dict[str, Any] | None) -> TranslateResult:
        prompt = (
            "You are a veteran-to-civilian communication assistant.\n"
            "Return STRICT JSON with this exact shape:\n"
            '{ "generic_answer":"...", "empathetic_personalized_answer":"...", "safety_flag":"none|crisis" }\n'
            "Rules:\n"
            "- generic_answer: plain, clear civilian-friendly explanation.\n"
            "- empathetic_personalized_answer: warm, validating, personalized using context.\n"
            "- safety_flag must be crisis if there are self-harm/suicide warning signs, else none.\n"
            "- No markdown, no extra keys, no text outside JSON.\n\n"
            f"Message:\n{message}\n\n"
            f"Context JSON:\n{json.dumps(context or {})}"
        )
        return self._generate_and_validate(prompt, TranslateResult)

    def _generate_and_validate(self, prompt: str, schema: Type[T]) -> T:
        text = self._call_model(prompt)
        parsed = self._try_parse_json(text, schema)
        if parsed is not None:
            return parsed

        retry_prompt = (
            prompt
            + "\n\nVALID JSON ONLY. Do not include markdown, commentary, or code fences."
        )
        retry_text = self._call_model(retry_prompt)
        retry_parsed = self._try_parse_json(retry_text, schema)
        if retry_parsed is not None:
            return retry_parsed
        raise ValueError("Model returned invalid JSON after one retry.")

    def _call_model(self, prompt: str) -> str:
        if self.provider == "gemini":
            response = self.model.generate_content(prompt)
            return getattr(response, "text", "") or ""
        if self.provider == "ollama":
            return self._call_ollama(prompt)
        raise ValueError("Unsupported AI provider.")

    def _call_ollama(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2},
            }
        ).encode("utf-8")
        req = request.Request(
            f"{settings.ollama_base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body)
        text = data.get("response", "")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Ollama returned empty response.")
        return text

    def _try_parse_json(self, text: str, schema: Type[T]) -> T | None:
        candidate = text.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
            candidate = re.sub(r"\s*```$", "", candidate)

        try:
            data = json.loads(candidate)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            pass

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(candidate[start : end + 1])
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError):
                return None
        return None
