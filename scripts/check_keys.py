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


def _mask_key(key: str) -> str:
    if not key:
        return "EMPTY"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]} (len: {len(key)})"


def test_groq_key(key: str, label: str) -> None:
    if not key:
        print(f"[{label}] NOT CONFIGURED (Key is empty)")
        return

    print(f"[{label}] Key detected: {_mask_key(key)}. Testing models...")
    from groq import Groq
    client = Groq(api_key=key, timeout=10.0)
    success = False
    for model in GROQ_TEXT_MODELS:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello! Reply with: CampusFlow AI OK"}],
                max_tokens=80,
            )
            msg = resp.choices[0].message
            ans = (msg.content or "").strip()
            if not ans and getattr(msg, "reasoning", None):
                ans = "OK (Reasoning model)"
            print(f"  + [{model}] SUCCESS: {ans or 'OK'}")
            success = True
            break
        except Exception as e:
            print(f"  x [{model}] FAILED: {str(e)[:120]}")

    if success:
        print(f"[{label}] STATUS: READY FOR AI CHAT & EXTRACTION\n")
    else:
        print(f"[{label}] STATUS: FAILED (Check if key is valid or rate limited)\n")


def test_gemini_key(key: str, label: str) -> None:
    if not key:
        print(f"[{label}] NOT CONFIGURED (Key is empty)")
        return

    print(f"[{label}] Key detected: {_mask_key(key)}. Testing models...")
    import httpx
    success = False
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = {"contents": [{"parts": [{"text": "Respond with the single word: OK"}]}]}
        try:
            resp = httpx.post(url, json=payload, timeout=10.0)
            if resp.status_code == 200:
                print(f"  + [{model}] SUCCESS: HTTP 200 OK")
                success = True
                break
            else:
                err_text = ""
                try:
                    err_text = resp.json().get("error", {}).get("message", "")
                except Exception:
                    err_text = resp.text[:100]
                print(f"  x [{model}] FAILED (HTTP {resp.status_code}): {err_text[:120]}")
        except Exception as e:
            print(f"  x [{model}] FAILED: {str(e)[:120]}")

    if success:
        print(f"[{label}] STATUS: READY FOR AI CHAT & EXTRACTION\n")
    else:
        print(f"[{label}] STATUS: FAILED (Check if key is valid or Google Generative Language API is enabled)\n")


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
