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
import time
import urllib.request
import urllib.error

OLLAMA_BASE = os.environ.get("LLM_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "gemma4")
PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
API_KEY = os.environ.get("LLM_API_KEY", "")


def _call_ollama(messages, model=None):
    """Call Ollama's chat API."""
    from .traces import save_trace

    url = f"{OLLAMA_BASE}/api/chat"
    payload = json.dumps({
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": 4096},
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            content = data.get("message", {}).get("content", "").strip()
            latency_ms = int((time.time() - start) * 1000)
            prompt_text = messages[-1].get("content", "") if messages else ""
            save_trace(
                prompt=prompt_text,
                response=content,
                latency_ms=latency_ms,
                model=model or DEFAULT_MODEL,
            )
            return content
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


def chat_stream(messages, model=None):
    """Stream a chat completion from Ollama, yielding tokens as they arrive.

    Yields dicts:
      {"type": "token", "content": "..."} — each token
      {"type": "thinking", "content": "..."} — model reasoning (if present)
      {"type": "done", "latency_ms": N} — final event

    If Ollama is unavailable, yields nothing.
    """
    url = f"{OLLAMA_BASE}/api/chat"
    payload = json.dumps({
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "stream": True,
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    start = time.time()
    full_response = []
    in_thinking = False
    thinking_buffer = []

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                content = chunk.get("message", {}).get("content", "")
                done = chunk.get("done", False)

                if not done and content:
                    # Detect thinking tags
                    if "<think" in content and ">" in content:
                        in_thinking = True
                        # Get content after the think tag
                        after = content.split(">", 1)[-1]
                        if after:
                            thinking_buffer.append(after)
                            yield {"type": "thinking", "content": after}
                        continue

                    if in_thinking:
                        if "</think" in content:
                            in_thinking = False
                            before = content.split("</think", 1)[0]
                            if before:
                                thinking_buffer.append(before)
                                yield {"type": "thinking", "content": before}
                            after = content.split(">", 1)[-1] if ">" in content else ""
                            if after:
                                full_response.append(after)
                                yield {"type": "token", "content": after}
                            continue
                        thinking_buffer.append(content)
                        yield {"type": "thinking", "content": content}
                        continue

                    full_response.append(content)
                    yield {"type": "token", "content": content}

                if done:
                    latency_ms = int((time.time() - start) * 1000)
                    full_text = "".join(full_response)
                    prompt_text = messages[-1].get("content", "") if messages else ""

                    from .traces import save_trace
                    save_trace(
                        prompt=prompt_text,
                        response=full_text,
                        latency_ms=latency_ms,
                        model=model or DEFAULT_MODEL,
                        extra={"thinking": "".join(thinking_buffer)} if thinking_buffer else None,
                    )
                    yield {"type": "done", "latency_ms": latency_ms}

    except (urllib.error.URLError, OSError):
        return
