import base64
import os
import httpx
from groq import Groq


def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Extract text from a notice image using Groq Vision or Gemini Flash."""
    groq_api_key = os.environ.get("GROQ_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    if not groq_api_key and not gemini_api_key:
        raise ValueError(
            "No API key found. Please set $env:GROQ_API_KEY (or $env:GEMINI_API_KEY) in your terminal."
        )

    # 1. Try Groq Vision first if GROQ_API_KEY is available
    if groq_api_key:
        try:
            client = Groq(api_key=groq_api_key)
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            # Active multimodal vision model on Groq
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Extract all readable text from this campus notice image accurately. "
                                    "Preserve all headings, dates, announcements, rules, and contact info. "
                                    "Return only the extracted text without introductory or concluding remarks."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except Exception as e:
            # If Groq fails and Gemini key is available, fallback to Gemini
            if not gemini_api_key:
                raise e

    # 2. Use Gemini Flash API if GEMINI_API_KEY is available
    if gemini_api_key:
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        prompt_text = (
            "Extract all readable text from this campus notice image accurately. "
            "Preserve all headings, dates, announcements, rules, and contact info. "
            "Return only the extracted text without introductory or concluding remarks."
        )
        for gemini_model in ["gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt_text},
                                {
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": base64_image,
                                    }
                                },
                            ]
                        }
                    ]
                }
                res = httpx.post(url, json=payload, timeout=30.0)
                res.raise_for_status()
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text_result = "".join(p.get("text", "") for p in parts)
                    if text_result:
                        return text_result.strip()
            except Exception:
                continue

    raise ValueError("Failed to extract text from image.")
