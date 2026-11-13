"""
Optional LLM layer (any OpenAI-compatible endpoint: Groq, OpenAI, Gemini's
OpenAI-compatible endpoint, or a local Ollama). Set in .env:

  LLM_BASE_URL=https://api.groq.com/openai/v1
  LLM_API_KEY=your_key
  LLM_MODEL=llama-3.3-70b-versatile

If not configured, everything still works with the rule-based advisory.
"""
from __future__ import annotations

import os

import requests


def enabled() -> bool:
    url = os.getenv("LLM_BASE_URL", "")
    return bool(url and os.getenv("LLM_MODEL") and (os.getenv("LLM_API_KEY") or "localhost" in url))


def chat(messages: list[dict], max_tokens: int = 400, temperature: float = 0.3) -> str | None:
    if not enabled():
        return None
    try:
        r = requests.post(
            os.environ["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY', '')}"},
            json=dict(model=os.environ["LLM_MODEL"], messages=messages,
                      max_tokens=max_tokens, temperature=temperature),
            timeout=25,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
