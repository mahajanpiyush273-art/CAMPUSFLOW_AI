"""
CampusFlow AI - Multi-Provider LLM Router & Resilience Engine
Routes requests across Groq, Gemini, and OpenAI-compatible providers with
circuit breaking, model fallback, robust JSON extraction, vision support,
and graceful offline mode.
"""

import base64
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from groq import Groq

from backend.config import (
    EXTRA_LLM_API_KEY,
    EXTRA_LLM_BASE_URL,
    EXTRA_LLM_MODEL,
    GEMINI_API_KEY,
    GEMINI_API_KEY_2,
    GEMINI_MODELS,
    GROQ_API_KEY,
    GROQ_API_KEY_2,
    GROQ_TEXT_MODELS,
    GROQ_VISION_MODELS,
)

# Circuit breaker state: provider -> failure timestamp
_circuit_breakers: Dict[str, float] = {}
CIRCUIT_TIMEOUT = 60.0  # seconds to skip a failing provider


def _is_breaker_active(provider_id: str) -> bool:
    """Check if circuit breaker is currently open (skipping) for a provider."""
    last_failure = _circuit_breakers.get(provider_id)
    if last_failure and (time.time() - last_failure < CIRCUIT_TIMEOUT):
        return True
    return False


def _record_failure(provider_id: str) -> None:
    """Record a failure for the provider to pause requests for 60 seconds."""
    _circuit_breakers[provider_id] = time.time()


def _record_success(provider_id: str) -> None:
    """Clear circuit breaker on successful response."""
    _circuit_breakers.pop(provider_id, None)


def parse_json_from_llm(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extract and parse a JSON object from raw LLM output,
    handling markdown code fences and conversational preamble.
    """
    if not raw_text:
        return None

    cleaned = raw_text.strip()
    # Remove markdown code fences if present
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()

    # Find the outermost curly braces
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_candidate = cleaned[start_idx : end_idx + 1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(cleaned)
    except Exception:
        return None


def chat_text(
    system_prompt: str,
    user_prompt: str,
    timeout: float = 20.0,
    temperature: float = 0.1,
) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Query configured LLM providers in sequence with automatic fallback.
    Returns (response_text, provider_name, model_name).
    If all fail or no keys are set, returns (None, 'offline', None).
    """
    providers_queue = []

    if GROQ_API_KEY and not _is_breaker_active("groq_1"):
        providers_queue.append(("groq_1", "groq", GROQ_API_KEY, GROQ_TEXT_MODELS))
    if GROQ_API_KEY_2 and not _is_breaker_active("groq_2"):
        providers_queue.append(("groq_2", "groq", GROQ_API_KEY_2, GROQ_TEXT_MODELS))

    if GEMINI_API_KEY and not _is_breaker_active("gemini_1"):
        providers_queue.append(("gemini_1", "gemini", GEMINI_API_KEY, GEMINI_MODELS))
    if GEMINI_API_KEY_2 and not _is_breaker_active("gemini_2"):
        providers_queue.append(("gemini_2", "gemini", GEMINI_API_KEY_2, GEMINI_MODELS))

    if EXTRA_LLM_BASE_URL and EXTRA_LLM_API_KEY and not _is_breaker_active("extra_llm"):
        providers_queue.append(("extra_llm", "extra", EXTRA_LLM_API_KEY, [EXTRA_LLM_MODEL or "default"]))

    for p_id, p_type, p_key, models in providers_queue:
        for model in models:
            try:
                if p_type == "groq":
                    client = Groq(api_key=p_key, timeout=timeout)
                    completion = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=temperature,
                        max_tokens=800,
                    )
                    content = completion.choices[0].message.content
                    if content and content.strip():
                        _record_success(p_id)
                        return content.strip(), "groq", model

                elif p_type == "gemini":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={p_key}"
                    payload = {
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"parts": [{"text": user_prompt}]}],
                        "generationConfig": {"temperature": temperature, "maxOutputTokens": 800},
                    }
                    resp = httpx.post(url, json=payload, timeout=timeout)
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                        if text and text.strip():
                            _record_success(p_id)
                            return text.strip(), "gemini", model

                elif p_type == "extra":
                    headers = {"Authorization": f"Bearer {p_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": 800,
                    }
                    url = f"{EXTRA_LLM_BASE_URL.rstrip('/')}/chat/completions"
                    resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    if content and content.strip():
                        _record_success(p_id)
                        return content.strip(), "extra", model

            except Exception:
                # Try next model before tripping breaker
                continue

        # If all models for this provider failed, trip breaker
        _record_failure(p_id)

    # Clean offline fallback
    return None, "offline", None


def chat_json(
    system_prompt: str,
    user_prompt: str,
    timeout: float = 20.0,
    retry_once: bool = True,
) -> Tuple[Optional[Dict[str, Any]], str, Optional[str]]:
    """Query LLM and parse output as JSON with at most one retry on malformed JSON."""
    raw_text, provider, model = chat_text(system_prompt, user_prompt, timeout=timeout)
    if not raw_text:
        return None, provider, model

    parsed = parse_json_from_llm(raw_text)
    if parsed is not None:
        return parsed, provider, model

    if retry_once:
        retry_prompt = f"{user_prompt}\n\nIMPORTANT: Return ONLY valid, well-formed JSON object without markdown or code fences."
        raw_text_2, provider_2, model_2 = chat_text(system_prompt, retry_prompt, timeout=timeout)
        if raw_text_2:
            parsed_2 = parse_json_from_llm(raw_text_2)
            if parsed_2 is not None:
                return parsed_2, provider_2, model_2

    return None, provider, model


def chat_vision(
    prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    timeout: float = 40.0,
) -> Tuple[Optional[str], str, Optional[str]]:
    """Extract information from image using Groq Vision or Gemini."""
    base64_img = base64.b64encode(image_bytes).decode("utf-8")

    # 1. Try Groq Vision first
    groq_keys = [k for k in [GROQ_API_KEY, GROQ_API_KEY_2] if k]
    for key in groq_keys:
        for model in GROQ_VISION_MODELS:
            try:
                client = Groq(api_key=key, timeout=timeout)
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{mime_type};base64,{base64_img}"},
                                },
                            ],
                        }
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                )
                content = resp.choices[0].message.content
                if content and content.strip():
                    return content.strip(), "groq_vision", model
            except Exception:
                continue

    # 2. Try Gemini Vision fallback
    gemini_keys = [k for k in [GEMINI_API_KEY, GEMINI_API_KEY_2] if k]
    for key in gemini_keys:
        for model in GEMINI_MODELS:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": base64_img,
                                    }
                                },
                            ]
                        }
                    ]
                }
                res = httpx.post(url, json=payload, timeout=timeout)
                res.raise_for_status()
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    extracted = "".join(p.get("text", "") for p in parts)
                    if extracted and extracted.strip():
                        return extracted.strip(), "gemini_vision", model
            except Exception:
                continue

    return None, "offline", None


def get_provider_health() -> Dict[str, Any]:
    """Check health and availability of configured LLM providers without revealing keys."""
    providers_info = []

    # Groq Check
    has_groq = bool(GROQ_API_KEY or GROQ_API_KEY_2)
    groq_status = "unconfigured"
    if has_groq:
        groq_status = "active" if not _is_breaker_active("groq_1") else "circuit_open"
    providers_info.append({
        "name": "Groq",
        "configured": has_groq,
        "models": GROQ_TEXT_MODELS,
        "vision_models": GROQ_VISION_MODELS,
        "status": groq_status
    })

    # Gemini Check
    has_gemini = bool(GEMINI_API_KEY or GEMINI_API_KEY_2)
    gemini_status = "unconfigured"
    if has_gemini:
        gemini_status = "active" if not _is_breaker_active("gemini_1") else "circuit_open"
    providers_info.append({
        "name": "Google Gemini",
        "configured": has_gemini,
        "models": GEMINI_MODELS,
        "status": gemini_status
    })

    # Extra OpenAI-compatible Check
    has_extra = bool(EXTRA_LLM_BASE_URL and EXTRA_LLM_API_KEY)
    providers_info.append({
        "name": "Custom LLM (OpenAI-compatible)",
        "configured": has_extra,
        "models": [EXTRA_LLM_MODEL] if EXTRA_LLM_MODEL else [],
        "status": "active" if has_extra else "unconfigured"
    })

    is_any_active = any(p["configured"] and p["status"] == "active" for p in providers_info)

    return {
        "status": "online" if is_any_active else "offline_mode",
        "providers": providers_info,
        "timestamp": time.time()
    }
