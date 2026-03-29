"""
Groq API wrapper.
All LLM calls go through here — swap the model in one place if needed.
"""

import json
import os
from groq import Groq

# Fallback to env var if config isn't set up yet
try:
    from config import GROQ_API_KEY, GROQ_MODEL
except ImportError:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = "llama-3.3-70b-versatile"

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def call_llm(system_prompt: str, user_message: str, temperature: float = 0.2) -> str:
    """
    Basic LLM call. Returns the raw string content.
    Low temperature keeps the agent deterministic and consistent.
    """
    client = get_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content


def call_llm_json(system_prompt: str, user_message: str, temperature: float = 0.1) -> dict:
    """
    LLM call that enforces JSON output.
    Retries once if the first response isn't valid JSON.
    """
    client = get_client()

    # Ask Groq to return JSON via response_format
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        # Retry: strip markdown code fences and try again
        raw = call_llm(system_prompt, user_message + "\n\nRespond with valid JSON only. No markdown, no code fences.", temperature)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
