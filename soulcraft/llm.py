"""LLM client for Soulcraft synthesis.

Uses the Ollama API (localhost:11434) by default.
Configurable via environment variables:
  LLM_BASE_URL  — API base URL (default: http://localhost:11434)
  LLM_MODEL     — Model name (default: qwen3.5:0.8b)
  LLM_PROVIDER  — "ollama" (default) or "openai" for OpenAI-compatible APIs
  LLM_API_KEY   — API key (not needed for Ollama, required for cloud providers)
"""

import json
import os
import urllib.request
import urllib.error

OLLAMA_BASE = os.environ.get("LLM_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "gemma4")
PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
API_KEY = os.environ.get("LLM_API_KEY", "")


def _call_ollama(messages, model=None):
    """Call Ollama's chat API."""
    url = f"{OLLAMA_BASE}/api/chat"
    payload = json.dumps({
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get("message", {}).get("content", "").strip()
    except urllib.error.URLError:
        return ""


def _call_openai_compat(messages, model=None):
    """Call an OpenAI-compatible API (Together, Groq, etc.)."""
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    url = f"{base}/chat/completions"
    payload = json.dumps({
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "max_tokens": 2048,
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError):
        return ""


def chat(messages, model=None):
    """Send a chat completion request. Returns the assistant's reply text.

    Args:
        messages: list of {"role": "system"|"user"|"assistant", "content": "..."}
        model: optional model override

    Returns:
        String with the assistant's response, or empty string on failure.
    """
    if PROVIDER == "openai":
        return _call_openai_compat(messages, model)
    return _call_ollama(messages, model)


def is_available():
    """Check if the LLM service is reachable."""
    try:
        url = f"{OLLAMA_BASE}/api/tags" if PROVIDER == "ollama" else None
        if not url:
            return bool(API_KEY)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False
