from dataclasses import dataclass
from difflib import SequenceMatcher
import json

import requests

from app.core.config import settings
from app.models.entities import Liberality


@dataclass
class GradeResult:
    awarded_marks: float
    feedback: str
    llm_provider: str | None = None
    llm_model: str | None = None
    prompt_version: str | None = None
    llm_response_id: str | None = None
    llm_fallback_used: bool = False


PROMPT_VERSION = "v1"


def grade_exact_match(*, student_answer: str, model_answer: str, max_marks: float) -> GradeResult:
    ratio = SequenceMatcher(None, student_answer.strip().lower(), model_answer.strip().lower()).ratio()
    awarded = round(max_marks * ratio, 2)
    feedback = f"Exact-match similarity: {ratio:.2f}"
    return GradeResult(awarded_marks=awarded, feedback=feedback)


def grade_with_llm(
    *,
    student_answer: str,
    model_answer: str,
    max_marks: float,
    liberality: Liberality,
) -> GradeResult:
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        try:
            return _grade_with_gemini(
                student_answer=student_answer,
                model_answer=model_answer,
                max_marks=max_marks,
                liberality=liberality,
            )
        except Exception:
            pass
    if settings.llm_provider == "claude" and settings.anthropic_api_key:
        try:
            return _grade_with_claude(
                student_answer=student_answer,
                model_answer=model_answer,
                max_marks=max_marks,
                liberality=liberality,
            )
        except Exception:
            # Falls back to heuristic scoring to keep pipeline available.
            pass
    return _heuristic_llm_fallback(
        student_answer=student_answer,
        model_answer=model_answer,
        max_marks=max_marks,
        liberality=liberality,
    )


def _grade_with_gemini(
    *,
    student_answer: str,
    model_answer: str,
    max_marks: float,
    liberality: Liberality,
) -> GradeResult:
    rubric_instruction = {
        Liberality.strict: "Be strict. Award marks only for highly accurate and complete points.",
        Liberality.moderate: "Be moderate. Award partial credit for materially correct points.",
        Liberality.liberal: "Be liberal. Generously award partial credit when intent is correct.",
    }[liberality]

    prompt = (
        "You are an exam evaluator. Return only valid JSON with keys "
        '`awarded_marks` (number) and `feedback` (string). '
        f"Maximum marks are {max_marks}. Never exceed this limit and never go below 0.\n\n"
        f"{rubric_instruction}\n\n"
        f"Model Answer:\n{model_answer}\n\n"
        f"Student Answer:\n{student_answer}\n"
    )

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{settings.llm_model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    response = requests.post(
        endpoint,
        headers={"content-type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        },
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("No candidates from Gemini API")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    parsed = _extract_json_object(text)

    awarded = float(parsed["awarded_marks"])
    awarded = max(0.0, min(max_marks, round(awarded, 2)))
    feedback = str(parsed.get("feedback", "LLM grading completed."))
    return GradeResult(
        awarded_marks=awarded,
        feedback=feedback,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        prompt_version=PROMPT_VERSION,
        llm_response_id=candidates[0].get("id"),
        llm_fallback_used=False,
    )


def _grade_with_claude(
    *,
    student_answer: str,
    model_answer: str,
    max_marks: float,
    liberality: Liberality,
) -> GradeResult:
    rubric_instruction = {
        Liberality.strict: "Be strict. Award marks only for highly accurate and complete points.",
        Liberality.moderate: "Be moderate. Award partial credit for materially correct points.",
        Liberality.liberal: "Be liberal. Generously award partial credit when intent is correct.",
    }[liberality]

    system_prompt = (
        "You are an exam evaluator. Grade answers fairly and consistently.\n"
        "Return only valid JSON with keys: awarded_marks (number), feedback (string).\n"
        f"Maximum marks are {max_marks}. Never exceed this limit and never go below 0."
    )
    user_prompt = (
        f"{rubric_instruction}\n"
        f"Model Answer:\n{model_answer}\n\n"
        f"Student Answer:\n{student_answer}\n\n"
        "Output format example: {\"awarded_marks\": 3.5, \"feedback\": \"...\"}"
    )

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.llm_model,
            "max_tokens": 300,
            "temperature": 0,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()

    content_blocks = data.get("content", [])
    if not content_blocks:
        raise ValueError("No content from Claude API")
    text = "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text").strip()
    parsed = _extract_json_object(text)

    awarded = float(parsed["awarded_marks"])
    awarded = max(0.0, min(max_marks, round(awarded, 2)))
    feedback = str(parsed.get("feedback", "LLM grading completed."))
    return GradeResult(
        awarded_marks=awarded,
        feedback=feedback,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        prompt_version=PROMPT_VERSION,
        llm_response_id=data.get("id"),
        llm_fallback_used=False,
    )


def _extract_json_object(raw_text: str) -> dict:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Could not parse JSON from Claude response") from None
        return json.loads(raw_text[start : end + 1])


def _heuristic_llm_fallback(
    *,
    student_answer: str,
    model_answer: str,
    max_marks: float,
    liberality: Liberality,
) -> GradeResult:
    base_ratio = SequenceMatcher(None, student_answer.strip().lower(), model_answer.strip().lower()).ratio()
    modifier = {"strict": 0.9, "moderate": 1.0, "liberal": 1.1}[liberality.value]
    awarded = round(min(max_marks, max_marks * base_ratio * modifier), 2)
    feedback = (
        f"LLM fallback grading ({liberality.value}) used similarity proxy. "
        "Configure ANTHROPIC_API_KEY or GEMINI_API_KEY for live LLM grading."
    )
    return GradeResult(
        awarded_marks=awarded,
        feedback=feedback,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        prompt_version=PROMPT_VERSION,
        llm_response_id=None,
        llm_fallback_used=True,
    )
