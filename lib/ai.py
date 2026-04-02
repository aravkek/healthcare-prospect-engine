"""
MedPort shared AI helper — Claude first, Groq fallback.
Import call_ai() from both pages/5 and pages/7.
"""

import os
import streamlit as st

MODEL = "claude-sonnet-4-6"


def _secret(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def call_ai(system: str, messages: list[dict], max_tokens: int = 2048) -> tuple[str, str]:
    """
    Claude first, Groq llama-3.3-70b fallback.
    Returns (response_text, provider_name).
    Raises RuntimeError on total failure.
    """
    anthropic_key = _secret("ANTHROPIC_API_KEY")
    groq_key = _secret("GROQ_API_KEY")
    fallback_reason = ""

    # Try Anthropic / Claude
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            resp = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            return resp.content[0].text, "Claude"
        except Exception as e:
            fallback_reason = str(e)
    else:
        fallback_reason = "ANTHROPIC_API_KEY not set"

    # Groq fallback
    if groq_key:
        try:
            import requests as _req
            groq_messages = [{"role": "system", "content": system}] + messages
            resp = _req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": groq_messages,
                    "max_tokens": min(max_tokens, 8192),
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"], "Groq (fallback)"
        except Exception as ge:
            raise RuntimeError(
                f"Both AI providers failed. Claude: {fallback_reason}. Groq: {ge}"
            )

    raise RuntimeError(
        "No AI API key configured. Add ANTHROPIC_API_KEY (or GROQ_API_KEY as fallback) to Streamlit secrets."
    )


def has_ai_configured() -> bool:
    """Returns True if at least one AI provider key is available."""
    return bool(_secret("ANTHROPIC_API_KEY") or _secret("GROQ_API_KEY"))


def ai_provider_badge() -> str:
    """Returns the name of the active AI provider for display."""
    if _secret("ANTHROPIC_API_KEY"):
        return "Claude Sonnet"
    if _secret("GROQ_API_KEY"):
        return "Groq (fallback)"
    return "No AI key"
