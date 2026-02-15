"""Business logic for Journey feature."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.challenge import Challenge
from app.models.journey_progress import JourneyProgress
from app.core.config import settings
from app.services.ai_service import AIServiceError, generate_structured

logger = logging.getLogger(__name__)

CRISIS_KEYWORDS = {
    "suicide",
    "kill myself",
    "end my life",
    "self harm",
    "hurt myself",
    "i want to die",
    "i don't want to live",
    "overdose",
}

_JOURNEY_CACHE_TTL_SECONDS = 60 * 60 * 24
_JOURNEY_CACHE: dict[str, tuple[float, dict[str, Any], str]] = {}
OLLAMA_JOURNEY_MODEL = "gemini-3-flash-preview:latest"


JOURNEY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["challenges"],
    "properties": {
        "challenges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "challenge_number",
                    "title",
                    "duration",
                    "recommended_times",
                    "suggested_locations",
                    "interaction_required",
                    "comfort_zone",
                    "what_this_builds",
                    "why_this_works",
                    "exit_strategy",
                    "you_can_also",
                    "modifications",
                ],
                "properties": {
                    "challenge_number": {"type": "integer"},
                    "title": {"type": "string"},
                    "duration": {"type": "string"},
                    "recommended_times": {"type": "array", "items": {"type": "string"}},
                    "suggested_locations": {"type": "array", "items": {"type": "string"}},
                    "interaction_required": {"type": "string"},
                    "comfort_zone": {"type": "string"},
                    "what_this_builds": {"type": "string"},
                    "why_this_works": {"type": "string"},
                    "exit_strategy": {"type": "string"},
                    "you_can_also": {"type": "array", "items": {"type": "string"}},
                    "modifications": {
                        "type": "object",
                        "required": ["if_easier_needed", "if_ready_for_more"],
                        "properties": {
                            "if_easier_needed": {"type": "string"},
                            "if_ready_for_more": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}

JOURNEY_INSIGHTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "modal_subtitle",
        "success_timeline",
        "what_you_built",
        "memory_quote",
        "full_breakdown",
        "what_youll_build_skill",
        "what_youll_build_prepares_for",
        "practical_best_time",
        "practical_duration",
        "practical_near_you",
        "exit_strategy",
        "modification_easier",
        "modification_harder",
    ],
    "properties": {
        "modal_subtitle": {"type": "string"},
        "success_timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["date_label", "feeling", "xp"],
                "properties": {
                    "date_label": {"type": "string"},
                    "feeling": {"type": "string"},
                    "xp": {"type": "integer"},
                },
            },
        },
        "what_you_built": {"type": "array", "items": {"type": "string"}},
        "memory_quote": {"type": "string"},
        "full_breakdown": {"type": "array", "items": {"type": "string"}},
        "what_youll_build_skill": {"type": "string"},
        "what_youll_build_prepares_for": {"type": "string"},
        "practical_best_time": {"type": "string"},
        "practical_duration": {"type": "string"},
        "practical_near_you": {"type": "string"},
        "exit_strategy": {"type": "string"},
        "modification_easier": {"type": "string"},
        "modification_harder": {"type": "string"},
    },
}


def get_or_create_progress(db: Session, user_id: int) -> JourneyProgress:
    progress = db.execute(select(JourneyProgress).where(JourneyProgress.user_id == user_id)).scalar_one_or_none()
    if progress:
        return progress

    progress = JourneyProgress(user_id=user_id, xp_total=0, level=1, current_streak=0, best_streak=0, avoidance_list=[])
    db.add(progress)
    try:
        db.flush()
        return progress
    except IntegrityError:
        # Concurrent request created the row first; load and return it.
        db.rollback()
        existing = db.execute(select(JourneyProgress).where(JourneyProgress.user_id == user_id)).scalar_one_or_none()
        if existing:
            return existing
        raise


def generate_challenges_for_user(
    db: Session,
    user_id: int,
    *,
    anxiety_level: int,
    interests: list[str],
    triggers: list[str],
    time_since_comfortable: str | None,
    end_goal: str | None,
    energy_times: list[str],
    location: str | None,
    avoid_situations: str | None,
    challenge_count: int,
) -> tuple[list[Challenge], list[str], str]:
    debug_steps: list[str] = []
    _trace(debug_steps, "start", user_id=user_id)
    provider = _get_internal_provider()
    _trace(debug_steps, "provider_selected", provider=provider)
    progress = get_or_create_progress(db, user_id)

    if _contains_blocked_text(" ".join(interests + triggers), CRISIS_KEYWORDS):
        _trace(debug_steps, "blocked_crisis_keywords", triggers=triggers, interests=interests)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Journey intake includes crisis-related keywords. Please use immediate support resources.",
        )

    # Only explicit avoidance items should be hard-blocked.
    requested_avoidance = _parse_avoid_situations(avoid_situations)
    combined_avoidance = _dedupe_terms((progress.avoidance_list or []) + requested_avoidance)
    progress.avoidance_list = combined_avoidance
    _trace(debug_steps, "avoidance_ready", combined_avoidance=combined_avoidance)

    intake_data = {
        "anxiety_level": anxiety_level,
        "triggers": triggers,
        "time_since_comfortable": time_since_comfortable or "unknown",
        "end_goal": end_goal or "general improvement",
        "interests": interests,
        "energy_times": energy_times,
        "location": location or "your area",
        "avoid_situations": avoid_situations or (", ".join(combined_avoidance) if combined_avoidance else "none specified"),
    }
    computed_count = calculate_challenge_count(intake_data)
    # Optional caller override: honor UI request while keeping absolute safety bounds.
    if challenge_count:
        computed_count = min(max(challenge_count, 1), 12)
    _trace(debug_steps, "count_computed", computed_count=computed_count, requested_count=challenge_count)
    prompt = _build_personalized_ladder_prompt(intake_data, computed_count)
    payload = {
        "intake_data": intake_data,
        "challenge_count": computed_count,
    }

    cache_key = _journey_cache_key(
        user_id=user_id,
        provider=provider,
        intake_data=intake_data,
        challenge_count=computed_count,
    )
    cached = _journey_cache_get(cache_key)
    if cached is not None:
        result, provider_used = cached
        _trace(debug_steps, "cache_hit", provider=provider_used)
    else:
        if settings.journey_force_local:
            result = _build_local_fallback_ladder(intake_data=intake_data, challenge_count=computed_count)
            provider_used = "local-fallback"
            _trace(debug_steps, "force_local_enabled", provider=provider)
        else:
            provider_used = "ollama"
            try:
                _trace(debug_steps, "provider_request_start", provider="ollama-python")
                result = generate_personalized_ladder(intake_data=intake_data, challenge_count=computed_count)
                _trace(debug_steps, "provider_request_ok", provider="ollama-python")
            except Exception as exc:  # noqa: BLE001
                logger.exception("Journey ollama-python generation failed", extra={"user_id": user_id})
                _trace(debug_steps, "provider_request_failed", provider="ollama-python", error=str(exc))
                result = _build_local_fallback_ladder(intake_data=intake_data, challenge_count=computed_count)
                provider_used = "local-fallback"
                _trace(debug_steps, "provider_fallback_local", provider="ollama-python")

        _journey_cache_set(cache_key, result, provider_used)
        _trace(debug_steps, "cache_set", provider=provider_used)

    blocked_terms = set(_normalize_terms(combined_avoidance)) | set(_normalize_terms(CRISIS_KEYWORDS))
    generated = result.get("challenges", [])
    if not isinstance(generated, list) or not generated:
        _trace(debug_steps, "generated_empty_or_invalid")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid challenges generated.")
    generated = generated[:computed_count]
    _trace(debug_steps, "generated_candidates", count=len(generated), provider=provider_used)

    start_order = db.execute(
        select(func.coalesce(func.max(Challenge.sort_order), 0)).where(Challenge.user_id == user_id)
    ).scalar_one()

    saved: list[Challenge] = []
    next_order = int(start_order)
    skipped_missing = 0
    skipped_blocked = 0
    for item in generated:
        if not isinstance(item, dict):
            skipped_missing += 1
            continue
        title = str(item.get("title", "")).strip()
        challenge_number = int(item.get("challenge_number", next_order + 1))
        description = _compose_challenge_description(item)
        difficulty = _difficulty_from_number(challenge_number, computed_count)
        xp_reward = _xp_from_number(challenge_number, computed_count)
        text_blob = f"{title} {description}".lower()

        if not title or not description:
            skipped_missing += 1
            _trace(debug_steps, "candidate_skipped_missing", challenge_number=challenge_number, title=title)
            continue
        if _contains_blocked_text(text_blob, blocked_terms):
            skipped_blocked += 1
            _trace(debug_steps, "candidate_skipped_blocked", challenge_number=challenge_number, title=title[:80])
            continue

        next_order += 1
        challenge = Challenge(
            user_id=user_id,
            title=title[:255],
            description=description,
            difficulty=difficulty,
            xp_reward=max(5, min(xp_reward, 200)),
            is_completed=False,
            sort_order=next_order,
        )
        db.add(challenge)
        saved.append(challenge)

    if not saved:
        _trace(
            debug_steps,
            "all_candidates_filtered",
            generated=len(generated),
            skipped_missing=skipped_missing,
            skipped_blocked=skipped_blocked,
            blocked_terms_sample=list(blocked_terms)[:8],
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "All generated challenges were removed by safety filters. "
                f"generated={len(generated)} skipped_missing={skipped_missing} skipped_blocked={skipped_blocked}. "
                "Enable backend logs to view step trace."
            ),
        )

    db.flush()
    if progress.active_challenge_id is None:
        progress.active_challenge_id = saved[0].id
    db.commit()

    for challenge in saved:
        db.refresh(challenge)

    _trace(debug_steps, "completed", saved=len(saved), provider=provider_used)
    return saved, combined_avoidance, provider_used


def generate_personalized_ladder(*, intake_data: dict[str, Any], challenge_count: int) -> dict[str, Any]:
    """Generate personalized journey challenges via Ollama Python client."""
    try:
        import ollama
    except ImportError as exc:  # pragma: no cover - runtime env dependent
        raise RuntimeError("Missing 'ollama' package. Install with: pip install ollama") from exc

    anxiety = intake_data.get("anxiety_level", 5)
    triggers = intake_data.get("triggers", [])
    time_since = intake_data.get("time_since_comfortable", "unknown")
    goal = intake_data.get("end_goal", "general improvement")
    interests = intake_data.get("interests", [])
    energy_times = intake_data.get("energy_times", [])
    location = intake_data.get("location", "your area")
    avoid = intake_data.get("avoid_situations", "none specified")

    prompt = f"""You are a clinical psychologist specializing in veteran reintegration and exposure therapy.

Generate FLEXIBLE, OPTION-RICH challenges that respect user autonomy and choice.

VETERAN PROFILE:
- Anxiety about public spaces: {anxiety}/10
- Specific triggers: {', '.join(triggers) if triggers else 'none specified'}
- Time since last comfort: {time_since}
- End goal: {goal}
- Interests: {', '.join(interests) if interests else 'none specified'}
- Best energy times: {', '.join(energy_times) if energy_times else 'flexible'}
- Location: {location}
- Must avoid: {avoid}

CRITICAL PRINCIPLES:
1. Suggest OPTIONS, never mandate one specific thing
2. Give 3-4 suggestions per field + "or your own choice"
3. Provide time WINDOWS (9-10am) not exact times (9:15am)
4. Title must be SHORT (4-7 words), plain language, and non-clinical
5. Offer modifications for flexibility
6. Explain WHY something works, let them choose HOW to do it
7. If they said avoid something (bars, alcohol, etc), NEVER suggest it
8. Never use specific business names or addresses
9. Use gentle, supportive language: "you could", "when you're ready", "if it feels right"
10. Avoid pushy language: "must", "should", "required", "need to"
11. Respect all veterans with neutral, steady language (no branch stereotypes)

TITLE RULES:
- Use an action phrase in sentence case, 4-7 words maximum.
- Keep it warm and practical; no clinical jargon.
- Do NOT use words like: habituation, exposure, protocol, reintegration, functional scripted, environmental adaptation.
- Good examples:
  - "Try a quiet coffee stop"
  - "Practice one brief hello"
  - "Take a short bookstore pause"
  - "Spend 10 calm minutes"

Generate exactly {challenge_count} challenges in this JSON structure.

Return ONLY valid JSON. No markdown code blocks. No explanations before or after. Just the JSON object.

JSON structure to return:
{{
  "challenges": [
    {{
      "challenge_number": 1,
      "title": "short activity title (4-7 words, gentle and practical)",
      "duration": "time range with flexibility",
      "recommended_times": ["time window 1", "time window 2", "Whenever works for you"],
      "suggested_locations": ["location type 1", "location type 2", "location type 3", "Or anywhere you feel comfortable"],
      "interaction_required": "what interaction is needed",
      "comfort_zone": "quiet_solo",
      "what_this_builds": "psychological skill being developed",
      "why_this_works": "reasoning based on triggers: {', '.join(triggers) if triggers else 'general anxiety'}",
      "exit_strategy": "how to leave without shame",
      "you_can_also": ["alternative 1", "alternative 2", "alternative 3"],
      "modifications": {{
        "if_easier_needed": "simpler version",
        "if_ready_for_more": "harder version"
      }}
    }}
  ]
}}"""

    model_name = settings.ollama_model.strip() or OLLAMA_JOURNEY_MODEL
    client = ollama.Client(host=settings.ollama_base_url)

    def _request_ollama(request_prompt: str) -> dict[str, Any]:
        response = client.chat(
            model=model_name,
            messages=[{"role": "user", "content": request_prompt}],
            format="json",
            options={"temperature": 0.7, "num_predict": 4000},
        )
        response_text = _clean_json_text(str(response.get("message", {}).get("content", "")))
        parsed = json.loads(response_text)
        if "challenges" not in parsed:
            raise ValueError("Missing 'challenges' key in response")
        return parsed

    try:
        data = _request_ollama(prompt)
    except (json.JSONDecodeError, ValueError):
        retry_prompt = (
            prompt
            + "\n\nYour previous response was invalid JSON. "
            + "Return ONLY the JSON object. No text before or after. Start with { and end with }."
        )
        data = _request_ollama(retry_prompt)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Ollama challenge generation failed: {exc}") from exc

    if len(data.get("challenges", [])) != challenge_count:
        logger.warning(
            "journey_ollama_count_mismatch expected=%s actual=%s model=%s",
            challenge_count,
            len(data.get("challenges", [])),
            model_name,
        )
    return data


def save_progress_for_user(
    db: Session,
    user_id: int,
    *,
    challenge_id: int | None,
    completed: bool,
    xp_earned: int,
    current_feeling: str | None,
    next_step: str | None,
    avoidance_list: list[str] | None,
) -> JourneyProgress:
    progress = get_or_create_progress(db, user_id)

    if avoidance_list is not None:
        progress.avoidance_list = _dedupe_terms(avoidance_list)
    if current_feeling is not None:
        progress.current_feeling = current_feeling
    if next_step is not None:
        progress.next_step = next_step

    challenge: Challenge | None = None
    newly_completed = False
    if challenge_id is not None:
        challenge = db.get(Challenge, challenge_id)
        if not challenge or challenge.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
        progress.active_challenge_id = challenge.id

        if completed and not challenge.is_completed:
            challenge.is_completed = True
            challenge.completed_at = datetime.now(timezone.utc)
            newly_completed = True
            if xp_earned == 0:
                xp_earned = challenge.xp_reward

    progress.xp_total += xp_earned
    progress.level = max(1, (progress.xp_total // 100) + 1)

    if newly_completed:
        progress.current_streak += 1
        progress.best_streak = max(progress.best_streak, progress.current_streak)

        next_challenge = db.execute(
            select(Challenge)
            .where(Challenge.user_id == user_id, Challenge.is_completed.is_(False))
            .order_by(Challenge.sort_order.asc(), Challenge.id.asc())
            .limit(1)
        ).scalar_one_or_none()
        progress.active_challenge_id = next_challenge.id if next_challenge else None

    db.commit()
    db.refresh(progress)
    return progress


def list_challenges_for_user(db: Session, user_id: int) -> list[Challenge]:
    result = db.execute(
        select(Challenge)
        .where(Challenge.user_id == user_id)
        .order_by(Challenge.sort_order.asc(), Challenge.id.asc())
    )
    return list(result.scalars().all())


def calculate_challenge_count(intake_data: dict[str, Any]) -> int:
    challenge_count = 6
    anxiety = int(intake_data.get("anxiety_level", 5) or 5)
    if anxiety >= 8:
        challenge_count += 2
    time_since = str(intake_data.get("time_since_comfortable", "")).lower()
    if "6+" in time_since or "deployment" in time_since:
        challenge_count += 1
    goal = str(intake_data.get("end_goal", "")).lower()
    if "networking" in goal or "events" in goal:
        challenge_count += 2
    elif "leaving" in goal:
        challenge_count -= 1
    return min(max(challenge_count, 5), 12)


def _build_personalized_ladder_prompt(intake_data: dict[str, Any], challenge_count: int) -> str:
    return f"""You are a clinical psychologist specializing in veteran reintegration and exposure therapy.

Generate FLEXIBLE, OPTION-RICH challenges that respect user autonomy and choice.

VETERAN PROFILE:
- Anxiety about public spaces: {intake_data.get('anxiety_level', 5)}/10
- Specific triggers: {', '.join(intake_data.get('triggers', [])) if intake_data.get('triggers') else 'none specified'}
- Time since last comfort: {intake_data.get('time_since_comfortable', 'unknown')}
- End goal: {intake_data.get('end_goal', 'general improvement')}
- Interests: {', '.join(intake_data.get('interests', [])) if intake_data.get('interests') else 'none specified'}
- Best energy times: {', '.join(intake_data.get('energy_times', [])) if intake_data.get('energy_times') else 'flexible'}
- Location: {intake_data.get('location', 'not specified')}
- Must avoid: {intake_data.get('avoid_situations', 'none specified')}

CRITICAL PRINCIPLES:
1. Suggest OPTIONS, never mandate one specific thing
2. Give 3-4 suggestions per field + "or your own choice"
3. Provide time WINDOWS (9-10am) not exact times (9:15am)
4. Offer modifications for flexibility
5. Explain WHY something works, let them choose HOW to do it
6. If they said avoid something (bars, alcohol, etc), NEVER suggest it
7. Never use specific business names or addresses
8. Use gentle, supportive language: "you could", "when you're ready", "if it feels right"
9. Avoid pushy language: "must", "should", "required", "need to"
10. Respect all veterans with neutral, steady language (no branch stereotypes)

TITLE RULES:
- Use an action phrase in sentence case, 4-7 words maximum.
- Keep it warm and practical; no clinical jargon.
- Do NOT use words like: habituation, exposure, protocol, reintegration, functional scripted, environmental adaptation.
- Good examples:
  - "Try a quiet coffee stop"
  - "Practice one brief hello"
  - "Take a short bookstore pause"
  - "Spend 10 calm minutes"

GOOD EXAMPLE OF FLEXIBILITY:
"Visit a quiet coffee shop or cafe"
Duration: "10-15 minutes (or however long feels right)"
Recommended times: ["9-10am (post-rush)", "2-3pm (afternoon quiet)", "Whenever your energy is good"]
Suggested locations: [
  "Small indie coffee shops - usually quieter, more personal",
  "Bookstore cafes - people focused on reading, not watching",
  "Chain coffee shops - familiar layout, predictable",
  "Or any cafe where you feel comfortable"
]

BAD EXAMPLE (too prescriptive):
"Go to Starbucks at 123 Main St on Tuesday at 9:15am, stay exactly 10 minutes"

PROGRESSION RULES:
- Start BELOW their anxiety level (if anxiety=7, first challenge should feel like difficulty 4)
- Each challenge 10-15% harder than previous
- Build from: presence -> observation -> brief interaction -> sustained interaction -> group settings
- Use their INTERESTS to make challenges relevant (if they like fitness, include gym; if coffee, start with cafes)
- Reference their SPECIFIC TRIGGERS in explanations

Generate exactly {challenge_count} challenges.

Return ONLY valid JSON in this exact structure (no markdown, no code blocks):

{{
  "challenges": [
    {{
      "challenge_number": 1,
      "title": "Flexible activity description (not specific place name)",
      "duration": "Time range with flexibility (e.g., 10-15 minutes, stay longer if comfortable)",
      "recommended_times": [
        "Time window 1 with reason",
        "Time window 2 with reason",
        "Whenever works for you"
      ],
      "suggested_locations": [
        "Location type 1 with why it's good",
        "Location type 2 with why it's good",
        "Location type 3 with why it's good",
        "Or anywhere you feel comfortable"
      ],
      "interaction_required": "What interaction is needed (or 'none required')",
      "comfort_zone": "quiet_solo",
      "what_this_builds": "Specific psychological skill being developed",
      "why_this_works": "Personal reasoning based on THEIR specific triggers: {', '.join(intake_data.get('triggers', [])) if intake_data.get('triggers') else 'general anxiety'}",
      "exit_strategy": "How they can leave without shame or guilt",
      "you_can_also": [
        "Easier modification they can try",
        "Alternative approach",
        "Support option (bring friend, etc)"
      ],
      "modifications": {{
        "if_easier_needed": "Simpler version if struggling",
        "if_ready_for_more": "Harder version if they're ready"
      }}
    }}
  ]
}}

LANGUAGE TO USE:
✓ "Suggestions near you"
✓ "Best times (but whenever works)"
✓ "You can also..."
✓ "Or anywhere that feels right"

LANGUAGE TO AVOID:
✗ "You must go to..."
✗ "Visit exactly at..."
✗ Specific addresses, exact times, business names"""


def _compose_challenge_description(item: dict[str, Any]) -> str:
    duration = str(item.get("duration", "")).strip()
    interaction_required = str(item.get("interaction_required", "")).strip()
    comfort_zone = str(item.get("comfort_zone", "")).strip()
    what_this_builds = str(item.get("what_this_builds", "")).strip()
    why_this_works = str(item.get("why_this_works", "")).strip()
    exit_strategy = str(item.get("exit_strategy", "")).strip()

    recommended_times = [str(v).strip() for v in item.get("recommended_times", []) if str(v).strip()]
    suggested_locations = [str(v).strip() for v in item.get("suggested_locations", []) if str(v).strip()]
    you_can_also = [str(v).strip() for v in item.get("you_can_also", []) if str(v).strip()]
    modifications = item.get("modifications", {}) if isinstance(item.get("modifications"), dict) else {}
    easier = str(modifications.get("if_easier_needed", "")).strip()
    harder = str(modifications.get("if_ready_for_more", "")).strip()

    lines: list[str] = []
    if duration:
        lines.append(f"Duration: {duration}")
    if recommended_times:
        lines.append("Best times (but whenever works): " + "; ".join(recommended_times[:4]))
    if suggested_locations:
        lines.append("Suggestions near you: " + "; ".join(suggested_locations[:4]))
    if interaction_required:
        lines.append(f"Interaction required: {interaction_required}")
    if comfort_zone:
        lines.append(f"Comfort zone: {comfort_zone}")
    if what_this_builds:
        lines.append(f"What this builds: {what_this_builds}")
    if why_this_works:
        lines.append(f"Why this works: {why_this_works}")
    if exit_strategy:
        lines.append(f"Exit strategy: {exit_strategy}")
    if you_can_also:
        lines.append("You can also: " + "; ".join(you_can_also[:4]))
    if easier:
        lines.append(f"If easier needed: {easier}")
    if harder:
        lines.append(f"If ready for more: {harder}")

    return "\n".join(lines).strip() or "Flexible challenge with options tailored to your pace."


def _difficulty_from_number(challenge_number: int, total: int) -> str:
    if total <= 1:
        return "EASY"
    ratio = challenge_number / total
    if ratio <= 0.4:
        return "EASY"
    if ratio <= 0.75:
        return "MEDIUM"
    return "HARD"


def _xp_from_number(challenge_number: int, total: int) -> int:
    if total <= 1:
        return 25
    ratio = challenge_number / total
    if ratio <= 0.4:
        return 25
    if ratio <= 0.75:
        return 40
    return 60


def _build_local_fallback_ladder(*, intake_data: dict[str, Any], challenge_count: int) -> dict[str, Any]:
    interests = [str(v).strip() for v in intake_data.get("interests", []) if str(v).strip()]
    triggers = [str(v).strip() for v in intake_data.get("triggers", []) if str(v).strip()]
    trigger_text = ", ".join(triggers) if triggers else "general social anxiety"

    avoid_terms = [t.strip().lower() for t in str(intake_data.get("avoid_situations", "")).split(",") if t.strip()]
    energy_times = [str(v).strip() for v in intake_data.get("energy_times", []) if str(v).strip()]
    recommended_times_base = energy_times[:2] if energy_times else ["9-10am (quieter window)", "2-3pm (lower rush)"]
    recommended_times = [*recommended_times_base, "Whenever works for you"]

    interest_hint = interests[0] if interests else "a familiar public setting"
    stages = ["presence", "observation", "brief interaction", "sustained interaction", "small-group exposure"]

    challenges: list[dict[str, Any]] = []
    for idx in range(challenge_count):
        n = idx + 1
        stage = stages[min(idx, len(stages) - 1)]
        comfort_zone = "quiet_solo" if idx < 2 else ("small_groups" if idx < 4 else "active_social")

        location_options = [
            f"Quiet places related to {interest_hint} where people are focused on their own activity",
            "Predictable public spaces with clear entry/exit routes",
            "Low-pressure venues with short, optional interactions",
            "Or anywhere you feel comfortable",
        ]
        location_options = _remove_avoided_options(location_options, avoid_terms)

        interaction_required = (
            "None required - just be present"
            if idx == 0
            else "One brief optional interaction (for example, a short greeting)"
            if idx < 3
            else "A short, natural back-and-forth conversation if it feels okay"
        )

        challenge = {
            "challenge_number": n,
            "title": f"Stage {n}: {stage.title()} in a setting that feels manageable",
            "duration": "10-15 minutes (or however long feels right)",
            "recommended_times": recommended_times,
            "suggested_locations": location_options,
            "interaction_required": interaction_required,
            "comfort_zone": comfort_zone,
            "what_this_builds": f"Confidence with {stage} while staying in control of pace and exits.",
            "why_this_works": f"This targets your stated stressors ({trigger_text}) through gradual, repeatable reps.",
            "exit_strategy": "You can leave at any point. Choosing to pause is a strategy, not a failure.",
            "you_can_also": [
                "Start with half the duration and build up over repeats",
                "Bring a trusted person for the first attempt",
                "Choose a quieter nearby option or a familiar route",
            ],
            "modifications": {
                "if_easier_needed": "Shorten time and remove interaction; focus on just arriving and staying present.",
                "if_ready_for_more": "Add one extra social rep or stay a bit longer while keeping the same setting.",
            },
        }
        challenges.append(challenge)

    return {"challenges": challenges}


def _remove_avoided_options(options: list[str], avoid_terms: list[str]) -> list[str]:
    if not avoid_terms:
        return options
    filtered = [opt for opt in options if not any(term and term in opt.lower() for term in avoid_terms)]
    return filtered or ["Or anywhere you feel comfortable"]


def _parse_avoid_situations(value: str | None) -> list[str]:
    if not value:
        return []
    ignored = {"none", "none specified", "n/a", "na", "no", "nothing"}
    parsed = [part.strip() for part in re.split(r"[,;\n]", value) if part.strip()]
    return [item for item in parsed if item.lower() not in ignored]


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _journey_cache_key(*, user_id: int, provider: str, intake_data: dict[str, Any], challenge_count: int) -> str:
    payload = {
        "user_id": user_id,
        "provider": provider,
        "intake_data": intake_data,
        "challenge_count": challenge_count,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _journey_cache_get(key: str) -> tuple[dict[str, Any], str] | None:
    record = _JOURNEY_CACHE.get(key)
    if record is None:
        return None
    stored_at, data, provider = record
    if monotonic() - stored_at > _JOURNEY_CACHE_TTL_SECONDS:
        _JOURNEY_CACHE.pop(key, None)
        return None
    return json.loads(json.dumps(data, ensure_ascii=True)), f"cache-{provider}"


def _journey_cache_set(key: str, data: dict[str, Any], provider: str) -> None:
    _JOURNEY_CACHE[key] = (monotonic(), json.loads(json.dumps(data, ensure_ascii=True)), provider)


def _trace(steps: list[str], stage: str, **details: Any) -> None:
    detail_parts = [f"{k}={details[k]}" for k in sorted(details.keys())]
    msg = stage if not detail_parts else f"{stage} | " + ", ".join(detail_parts)
    steps.append(msg)
    if settings.journey_debug:
        logger.info("journey_trace %s", msg)


def generate_challenge_insights_for_user(db: Session, user_id: int, challenge_id: int) -> dict[str, Any]:
    provider = _get_internal_provider()
    challenge = db.get(Challenge, challenge_id)
    if not challenge or challenge.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    progress = get_or_create_progress(db, user_id)

    timeline: list[dict[str, Any]] = [
        {
            "date_label": challenge.created_at.strftime("%b %d") if challenge.created_at else "Started",
            "feeling": "Challenge created",
            "xp": 0,
        }
    ]
    if challenge.completed_at is not None:
        timeline.append(
            {
                "date_label": challenge.completed_at.strftime("%b %d"),
                "feeling": "Completed and logged",
                "xp": challenge.xp_reward,
            }
        )

    task = (
        "You are a Peer Support Assistant. You are non-medical and should use supportive, practical language. "
        "Generate concise challenge detail content for a UI modal. "
        "Do not include crisis guidance, diagnosis, or treatment advice. "
        "Do not mention any phrases in avoidance_list or trigger list."
    )
    payload = {
        "challenge": {
            "title": challenge.title,
            "description": challenge.description or "",
            "difficulty": challenge.difficulty,
            "xp_reward": challenge.xp_reward,
            "is_completed": challenge.is_completed,
            "created_at": challenge.created_at.isoformat() if challenge.created_at else None,
            "completed_at": challenge.completed_at.isoformat() if challenge.completed_at else None,
            "sort_order": challenge.sort_order,
        },
        "progress": {
            "xp_total": progress.xp_total,
            "level": progress.level,
            "current_streak": progress.current_streak,
            "best_streak": progress.best_streak,
            "current_feeling": progress.current_feeling,
            "next_step": progress.next_step,
            "avoidance_list": progress.avoidance_list or [],
        },
        "timeline_seed": timeline,
    }

    if settings.journey_force_local:
        result = _build_local_fallback_insights(challenge=challenge, timeline=timeline)
    else:
        try:
            result = generate_structured(
                provider=provider,
                task=task,
                payload=payload,
                schema=JOURNEY_INSIGHTS_SCHEMA,
            )
        except AIServiceError as exc:
            logger.exception("Journey insights provider failed", extra={"user_id": user_id, "challenge_id": challenge_id, "provider": provider})
            result = _build_local_fallback_insights(challenge=challenge, timeline=timeline)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Journey insights unexpected error", extra={"user_id": user_id, "challenge_id": challenge_id})
            result = _build_local_fallback_insights(challenge=challenge, timeline=timeline)

    generated_timeline = result.get("success_timeline")
    if not isinstance(generated_timeline, list) or not generated_timeline:
        result["success_timeline"] = timeline
    else:
        result["success_timeline"] = generated_timeline[:4]

    result["challenge_id"] = challenge_id
    return result


def _build_local_fallback_insights(*, challenge: Challenge, timeline: list[dict[str, Any]]) -> dict[str, Any]:
    description = challenge.description or "Build confidence through gradual, repeatable social reps."
    return {
        "modal_subtitle": "Challenge Details",
        "success_timeline": timeline,
        "what_you_built": [description],
        "memory_quote": "Progress counts even when a session feels imperfect.",
        "full_breakdown": [description],
        "what_youll_build_skill": "Steady confidence in social environments at your own pace.",
        "what_youll_build_prepares_for": "Longer and more natural interactions over time.",
        "practical_best_time": "A low-traffic window when you feel most steady.",
        "practical_duration": "10-20 minutes, adjust based on comfort.",
        "practical_near_you": "A familiar, low-pressure nearby location.",
        "exit_strategy": "You can pause or leave at any point and try again later.",
        "modification_easier": "Shorten duration and remove interaction for this attempt.",
        "modification_harder": "Add one extra interaction or stay slightly longer.",
    }


def _get_internal_provider() -> str:
    provider = settings.ai_provider.strip().lower()
    if provider not in {"gemini", "ollama"}:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid AI_PROVIDER setting. Use 'gemini' or 'ollama'.",
        )
    return provider


def _normalize_terms(terms: list[str] | set[str]) -> list[str]:
    normalized: list[str] = []
    for term in terms:
        t = term.strip().lower()
        if t:
            normalized.append(t)
    return normalized


def _dedupe_terms(terms: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        clean = term.strip()
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            deduped.append(clean)
    return deduped


def _contains_blocked_text(text: str, blocked_terms: set[str] | list[str]) -> bool:
    lowered = text.lower()
    for term in _normalize_terms(blocked_terms):
        if not term:
            continue
        # Phrase terms use substring matching; single-token terms require word boundary match.
        if " " in term:
            if term in lowered:
                return True
            continue
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            return True
    return False
