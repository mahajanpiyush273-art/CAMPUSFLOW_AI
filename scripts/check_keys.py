"""
CampusFlow AI - API Keys Validation Script
Tests all configured API keys and models with a lightweight prompt.
Outputs ASCII-only test results.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

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


def test_groq_key(key: str, label: str) -> None:
    if not key:
        print(f"[{label}] NOT CONFIGURED")
        return

    from groq import Groq
    client = Groq(api_key=key, timeout=10.0)
    for model in GROQ_TEXT_MODELS:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Respond with the single word: OK"}],
                max_tokens=10,
            )
            ans = resp.choices[0].message.content.strip()
            print(f"[{label} - {model}] OK: {ans}")
            return
        except Exception as e:
            print(f"[{label} - {model}] FAIL: {str(e)[:120]}")


def test_gemini_key(key: str, label: str) -> None:
    if not key:
        print(f"[{label}] NOT CONFIGURED")
        return

    import httpx
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = {"contents": [{"parts": [{"text": "Respond with the single word: OK"}]}]}
        try:
            resp = httpx.post(url, json=payload, timeout=10.0)
            if resp.status_code == 200:
                print(f"[{label} - {model}] OK")
                return
            else:
                print(f"[{label} - {model}] FAIL: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[{label} - {model}] FAIL: {str(e)[:120]}")


def main():
    print("=" * 60)
    print("CampusFlow AI - Key and Model Checker")
    print("=" * 60)

    test_groq_key(GROQ_API_KEY, "Groq Key 1")
    test_groq_key(GROQ_API_KEY_2, "Groq Key 2")
    test_gemini_key(GEMINI_API_KEY, "Gemini Key 1")
    test_gemini_key(GEMINI_API_KEY_2, "Gemini Key 2")

    if EXTRA_LLM_BASE_URL and EXTRA_LLM_API_KEY:
        import httpx
        url = f"{EXTRA_LLM_BASE_URL.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {EXTRA_LLM_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": EXTRA_LLM_MODEL or "default",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10,
        }
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=10.0)
            if resp.status_code == 200:
                print(f"[Extra LLM] OK")
            else:
                print(f"[Extra LLM] FAIL: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[Extra LLM] FAIL: {str(e)[:120]}")
    else:
        print("[Extra LLM] NOT CONFIGURED")

    print("=" * 60)
    print("Check complete. If all keys are unconfigured, app operates in OFFLINE MODE.")
    print("=" * 60)


if __name__ == "__main__":
    main()
