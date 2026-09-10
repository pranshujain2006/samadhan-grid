"""Thin, resilient wrapper around the Groq API.

Every AI service in SAMADHAN GRID goes through here. If no API key is present
(or a call fails) the caller falls back to a deterministic rule-based path, so
the platform keeps working end-to-end during a demo without network access.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..config import GROQ_API_KEY, GROQ_MODEL, GROQ_STT_MODEL

log = logging.getLogger("samadhan.groq")

_client: Any = None
_active_model: str | None = None

# Tried in order if the configured model is not available on this account.
FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "groq/compound",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


def available() -> bool:
    return bool(GROQ_API_KEY)


def _get_client():
    global _client
    if _client is None:
        from groq import AsyncGroq
        _client = AsyncGroq(api_key=GROQ_API_KEY)
    return _client


async def resolve_model() -> str | None:
    """Pick a chat model this account can actually use.

    Groq rotates its catalogue and accounts differ, so a hard-coded model id goes
    stale. We ask the account what it has, prefer the configured model, then fall
    back through a preference list.
    """
    global _active_model
    if _active_model or not available():
        return _active_model
    try:
        client = _get_client()
        listing = await client.models.list()
        ids = {m.id for m in listing.data}
        # Exclude non-chat models (speech, guard, TTS).
        chat = {i for i in ids if not any(
            x in i for x in ("whisper", "prompt-guard", "orpheus", "tts", "safeguard"))}
        for candidate in [GROQ_MODEL, *FALLBACK_MODELS]:
            if candidate in chat:
                _active_model = candidate
                break
        else:
            _active_model = next(iter(sorted(chat)), None)
        if _active_model and _active_model != GROQ_MODEL:
            log.warning("Groq model %r unavailable on this account; using %r instead. "
                        "Set GROQ_MODEL=%s in .env to silence this.",
                        GROQ_MODEL, _active_model, _active_model)
        else:
            log.info("Groq chat model: %s", _active_model)
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not list Groq models: %s", exc)
        _active_model = GROQ_MODEL
    return _active_model


def active_model() -> str | None:
    return _active_model or (GROQ_MODEL if available() else None)


def _extract_json(text: str) -> dict[str, Any] | None:
    """LLMs sometimes wrap JSON in prose or fences. Dig it out."""
    if not text:
        return None
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        val = json.loads(text)
        return val if isinstance(val, dict) else {"result": val}
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


async def json_call(system: str, user: str, *, temperature: float = 0.2,
                    max_tokens: int = 2400, model: str | None = None
                    ) -> dict[str, Any] | None:
    """Ask Groq for a JSON object. Returns None on any failure."""
    if not available():
        return None
    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=model or await resolve_model() or GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _extract_json(resp.choices[0].message.content or "")
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash a request
        log.warning("Groq json_call failed: %s", exc)
        return None


async def text_call(system: str, user: str, *, temperature: float = 0.3,
                    max_tokens: int = 900) -> str | None:
    if not available():
        return None
    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=await resolve_model() or GROQ_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("Groq text_call failed: %s", exc)
        return None


async def transcribe(data: bytes, filename: str, language: str | None = None
                     ) -> dict[str, Any] | None:
    """Speech-to-text via Groq Whisper. Handles Hindi and other Indian languages."""
    if not available():
        return None
    try:
        client = _get_client()
        kwargs: dict[str, Any] = {
            "file": (filename, data),
            "model": GROQ_STT_MODEL,
            "response_format": "verbose_json",
        }
        if language and language != "auto":
            kwargs["language"] = language
        resp = await client.audio.transcriptions.create(**kwargs)
        text = getattr(resp, "text", "") or ""
        detected = getattr(resp, "language", None)
        return {"text": text.strip(), "language": detected}
    except Exception as exc:  # noqa: BLE001
        log.warning("Groq transcription failed: %s", exc)
        return None


def status() -> dict[str, Any]:
    return {
        "groq_configured": available(),
        "chat_model": active_model(),
        "configured_model": GROQ_MODEL if available() else None,
        "stt_model": GROQ_STT_MODEL if available() else None,
        "mode": "groq" if available() else "rule-based fallback",
    }
