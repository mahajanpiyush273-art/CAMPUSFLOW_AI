import os
from typing import Optional
from groq import Groq


def write_answer(question: str, notice_title: str, notice_text: str) -> str:
    """
    Generate a 1-2 sentence concise student answer using Groq with gpt-oss-120b.
    Uses ONLY the verified notice text to prevent hallucinations.
    """
    api_key = os.environ.get("GROQ_API_KEY")

    # If no Groq API key is configured, provide an immediate fallback from notice text
    if not api_key:
        lines = [line.strip() for line in notice_text.splitlines() if line.strip()]
        return lines[0] if lines else notice_text[:200]

    system_prompt = (
        "You are CampusFlow AI ('Ask. Verify. Act.'), a trusted campus assistant. "
        "Answer the student's question in 1 or 2 direct, clear sentences using ONLY the verified notice text below. "
        "Do not invent any details or dates. If the information is not in the notice, say 'The verified notice does not state this.'"
    )

    user_content = (
        f"Notice Title: {notice_title}\n\n"
        f"Notice Content:\n{notice_text}\n\n"
        f"Student Question: {question}\n\n"
        f"Answer:"
    )

    # Preferred models on Groq: gpt-oss-120b, gpt-oss-20b, llama-3.1-8b-instant
    candidate_models = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.1-8b-instant",
    ]

    client = Groq(api_key=api_key)

    for model_name in candidate_models:
        try:
            chat_completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                max_tokens=300,
            )
            ans = chat_completion.choices[0].message.content
            if ans and ans.strip():
                return ans.strip()
        except Exception:
            continue

    # Fallback to the notice text directly if API calls fail
    lines = [line.strip() for line in notice_text.splitlines() if line.strip()]
    return lines[0] if lines else notice_text[:200]
