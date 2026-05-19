"""LLM client for Elixis synthesis.

Uses the Ollama API (localhost:11434) by default.
Configurable via environment variables:
  LLM_BASE_URL  — API base URL (default: http://localhost:11434)
  LLM_MODEL     — Model name (default: gemma-4b)
  LLM_PROVIDER  — "ollama" (default), "openai" for OpenAI-compatible APIs,
                  or "anthropic" for Claude Messages API
  LLM_API_KEY   — API key (not needed for Ollama, required for cloud providers)
"""

import json
import os
import time
import urllib.error
import urllib.request


class _Config:
    """Live configuration that reads env vars on each access."""

    @property
    def base_url(self):
        return os.environ.get("LLM_BASE_URL", "http://localhost:11434")

    @property
    def fallback_url(self):
        return os.environ.get("LLM_FALLBACK_URL", "")

    @property
    def default_model(self):
        if os.environ.get("LLM_MODEL"):
            return os.environ["LLM_MODEL"]
        if self.provider == "anthropic":
            return (
                os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
                or os.environ.get("ANTHROPIC_DEFAULT_HAIKU_MODEL")
                or "claude-sonnet-4-5"
            )
        return "gemma-4b"

    @property
    def classify_model(self):
        return os.environ.get("LLM_CLASSIFY_MODEL", "")

    @property
    def provider(self):
        return os.environ.get("LLM_PROVIDER", "ollama")

    @property
    def api_key(self):
        return os.environ.get("LLM_API_KEY", "")

    @property
    def anthropic_api_key(self):
        return os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LLM_API_KEY", "")

    @property
    def anthropic_auth_token(self):
        return os.environ.get("ANTHROPIC_AUTH_TOKEN", "")


cfg = _Config()

# Module-level __getattr__ resolves backward-compatible aliases live.
# This ensures `from elixis.llm import DEFAULT_MODEL` always returns
# the current env var value, not the import-time snapshot.
_ALIASES = {
    "OLLAMA_BASE": "base_url",
    "FALLBACK_BASE_URL": "fallback_url",
    "DEFAULT_MODEL": "default_model",
    "CLASSIFY_MODEL": "classify_model",
    "PROVIDER": "provider",
    "API_KEY": "api_key",
}


def __getattr__(name):
    prop = _ALIASES.get(name)
    if prop is not None:
        return getattr(cfg, prop)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Cached availability check (avoids hammering Ollama on every call)
_availability_cache = {"result": None, "expires": 0}
_AVAILABILITY_TTL = 10  # seconds


def _call_ollama(messages, model=None, max_tokens=4096, think=True):
    """Call Ollama's chat API. Returns a result dict with content + telemetry."""
    from .traces import save_trace

    url = f"{cfg.base_url}/api/chat"
    payload = json.dumps({
        "model": model or cfg.default_model,
        "messages": messages,
        "stream": False,
        "think": think,
        "options": {"num_predict": max_tokens},
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
            content = data.get("message", {}).get("content", "").strip()
            latency_ms = int((time.time() - start) * 1000)
            tokens_in = data.get("prompt_eval_count", 0) or 0
            tokens_out = data.get("eval_count", 0) or 0
            tps = round(tokens_out / (latency_ms / 1000), 1) if latency_ms > 0 and tokens_out > 0 else 0
            prompt_text = messages[-1].get("content", "") if messages else ""
            used_model = model or cfg.default_model
            save_trace(
                prompt=prompt_text,
                response=content,
                latency_ms=latency_ms,
                model=used_model,
                extra={"tokens_in": tokens_in, "tokens_out": tokens_out, "tokens_per_sec": tps},
            )
            return {
                "content": content,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": latency_ms,
                "tokens_per_sec": tps,
                "model": used_model,
                "provider": cfg.provider,
            }
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        import logging
        logging.getLogger("elixis.llm").warning(f"Ollama call failed: {e}")
        return {"content": "", "error": str(e), "tokens_in": 0, "tokens_out": 0, "latency_ms": 0, "tokens_per_sec": 0, "model": model or cfg.default_model, "provider": cfg.provider}


def _call_openai_compat_single(base_url, messages, model=None, max_tokens=2048):
    """Call a single OpenAI-compatible endpoint."""
    url = f"{base_url}/chat/completions"
    used_model = model or cfg.default_model
    payload = json.dumps({
        "model": used_model,
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg.api_key}",
    }
    req = urllib.request.Request(url, data=payload, headers=headers)
    start = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
        msg = data["choices"][0]["message"]
        # Qwen models may put content in reasoning_content when thinking
        content = msg.get("content", "").strip()
        if not content:
            content = msg.get("reasoning_content", "").strip()
        latency_ms = int((time.time() - start) * 1000)
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        tps = round(tokens_out / (latency_ms / 1000), 1) if latency_ms > 0 and tokens_out > 0 else 0
        return {
            "content": content,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "tokens_per_sec": tps,
            "model": used_model,
            "provider": "openai",
        }


def _call_openai_compat(messages, model=None, max_tokens=2048):
    """Call an OpenAI-compatible API with fallback to secondary server."""
    primary_base = cfg.base_url
    fallback_base = cfg.fallback_url

    # Try primary first
    try:
        return _call_openai_compat_single(primary_base, messages, model, max_tokens)
    except (urllib.error.URLError, OSError, KeyError, TimeoutError, json.JSONDecodeError) as e:
        # Primary failed - try fallback if configured
        if fallback_base:
            try:
                result = _call_openai_compat_single(fallback_base, messages, model, max_tokens)
                # Mark as fallback in result
                result["fallback"] = True
                result["primary_error"] = str(e)
                return result
            except (urllib.error.URLError, OSError, KeyError, TimeoutError, json.JSONDecodeError) as fallback_error:
                used_model = model or cfg.default_model
                import logging
                logging.getLogger("elixis.llm").warning(
                    "OpenAI-compatible call failed (primary: %s; fallback: %s)",
                    e,
                    fallback_error,
                )
                return {
                    "content": "",
                    "error": f"Primary failed: {e}; fallback failed: {fallback_error}",
                    "primary_error": str(e),
                    "fallback_error": str(fallback_error),
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "latency_ms": 0,
                    "tokens_per_sec": 0,
                    "model": used_model,
                    "provider": "openai",
                }
        # Both failed or no fallback
        used_model = model or cfg.default_model
        import logging
        logging.getLogger("elixis.llm").warning(f"OpenAI-compatible call failed (primary): {e}")
        return {"content": "", "error": str(e), "tokens_in": 0, "tokens_out": 0, "latency_ms": 0, "tokens_per_sec": 0, "model": used_model, "provider": "openai"}


def _anthropic_endpoint(path):
    """Build an Anthropic endpoint from either a root URL or a /v1 base URL."""
    base_url = cfg.base_url.rstrip("/") if cfg.base_url else "https://api.anthropic.com"
    if base_url.endswith("/v1"):
        return f"{base_url}/{path.lstrip('/')}"
    return f"{base_url}/v1/{path.lstrip('/')}"


def _anthropic_headers():
    """Return Anthropic request headers without leaking credentials into callers."""
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    if cfg.anthropic_auth_token:
        headers["Authorization"] = f"Bearer {cfg.anthropic_auth_token}"
    elif cfg.anthropic_api_key:
        headers["x-api-key"] = cfg.anthropic_api_key
    return headers


def _anthropic_payload(messages, model=None, max_tokens=2048, stream=False):
    """Convert chat-style messages into Anthropic Messages API payload."""
    system_parts = []
    converted = []
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", ""))
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
            continue
        role = "assistant" if role == "assistant" else "user"
        if converted and converted[-1]["role"] == role:
            converted[-1]["content"] = f"{converted[-1]['content']}\n\n{content}"
        else:
            converted.append({"role": role, "content": content})

    if not converted or converted[0]["role"] != "user":
        converted.insert(0, {"role": "user", "content": "Continue."})

    payload = {
        "model": model or cfg.default_model,
        "messages": converted,
        "max_tokens": max_tokens,
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)
    if stream:
        payload["stream"] = True
    return payload


def _call_anthropic(messages, model=None, max_tokens=2048):
    """Call Anthropic's Messages API. Returns a result dict with content + telemetry."""
    url = _anthropic_endpoint("messages")
    used_model = model or cfg.default_model
    payload = json.dumps(_anthropic_payload(messages, used_model, max_tokens)).encode()
    req = urllib.request.Request(url, data=payload, headers=_anthropic_headers())
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        parts = [
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        content = "".join(parts).strip()
        latency_ms = int((time.time() - start) * 1000)
        usage = data.get("usage", {})
        tokens_in = usage.get("input_tokens", 0) or 0
        tokens_out = usage.get("output_tokens", 0) or 0
        tps = round(tokens_out / (latency_ms / 1000), 1) if latency_ms > 0 and tokens_out > 0 else 0
        prompt_text = messages[-1].get("content", "") if messages else ""

        from .traces import save_trace
        save_trace(
            prompt=prompt_text,
            response=content,
            latency_ms=latency_ms,
            model=used_model,
            extra={"tokens_in": tokens_in, "tokens_out": tokens_out, "tokens_per_sec": tps},
        )
        return {
            "content": content,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "tokens_per_sec": tps,
            "model": used_model,
            "provider": "anthropic",
        }
    except (urllib.error.URLError, OSError, TimeoutError, KeyError, json.JSONDecodeError) as e:
        import logging
        logging.getLogger("elixis.llm").warning(f"Anthropic call failed: {e}")
        return {
            "content": "",
            "error": str(e),
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0,
            "tokens_per_sec": 0,
            "model": used_model,
            "provider": "anthropic",
        }


def chat(messages, model=None, max_tokens=None, think=True):
    """Send a chat completion request. Returns a result dict.

    Args:
        messages: list of {"role": "system"|"user"|"assistant", "content": "..."}
        model: optional model override
        max_tokens: optional max output tokens (default 4096 for ollama, 2048 for openai)
        think: whether to allow model reasoning (default True; set False for fast classification)

    Returns:
        Dict with keys: content, tokens_in, tokens_out, latency_ms,
        tokens_per_sec, model, provider.
    """
    if cfg.provider == "anthropic":
        kw = {"max_tokens": max_tokens} if max_tokens else {}
        return _call_anthropic(messages, model, **kw)
    if cfg.provider == "openai":
        kw = {"max_tokens": max_tokens} if max_tokens else {}
        return _call_openai_compat(messages, model, **kw)
    kw = {}
    if max_tokens:
        kw["max_tokens"] = max_tokens
    if not think:
        kw["think"] = False
    return _call_ollama(messages, model, **kw)


def is_available():
    """Check if the LLM service is reachable. Results cached for 10s."""
    now = time.time()
    if _availability_cache["result"] is not None and now < _availability_cache["expires"]:
        return _availability_cache["result"]
    try:
        if cfg.provider == "ollama":
            url = f"{cfg.base_url}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                result = resp.status == 200
        elif cfg.provider == "anthropic":
            req = urllib.request.Request(_anthropic_endpoint("models"), headers=_anthropic_headers())
            with urllib.request.urlopen(req, timeout=3) as resp:
                result = resp.status == 200
        else:
            # OpenAI-compatible: hit /models or /v1/models
            url = f"{cfg.base_url}/models"
            headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=3) as resp:
                result = resp.status == 200
    except Exception:
        result = False
    _availability_cache["result"] = result
    _availability_cache["expires"] = now + _AVAILABILITY_TTL
    return result


def chat_stream(messages, model=None):
    """Stream a chat completion, yielding tokens as they arrive.

    Supports both Ollama and OpenAI-compatible APIs (selected by LLM_PROVIDER).

    Yields dicts:
      {"type": "token", "content": "..."} — each token
      {"type": "thinking", "content": "..."} — model reasoning (if present)
      {"type": "done", "latency_ms": N} — final event

    If unavailable, yields nothing.
    """
    if cfg.provider == "anthropic":
        yield from _chat_stream_anthropic(messages, model)
    elif cfg.provider == "openai":
        yield from _chat_stream_openai(messages, model)
    else:
        yield from _chat_stream_ollama(messages, model)


def _chat_stream_openai(messages, model=None):
    """Stream from an OpenAI-compatible API (/v1/chat/completions with stream=true)."""
    url = f"{cfg.base_url}/chat/completions"
    used_model = model or cfg.default_model
    payload = json.dumps({
        "model": used_model,
        "messages": messages,
        "stream": True,
        "max_tokens": 2048,
    }).encode()
    headers = {
        "Content-Type": "application/json",
    }
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    req = urllib.request.Request(url, data=payload, headers=headers)
    start = time.time()
    full_response = []

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")

                if content:
                    full_response.append(content)
                    yield {"type": "token", "content": content}

        latency_ms = int((time.time() - start) * 1000)
        prompt_text = messages[-1].get("content", "") if messages else ""
        full_text = "".join(full_response)

        from .traces import save_trace
        save_trace(
            prompt=prompt_text,
            response=full_text,
            latency_ms=latency_ms,
            model=used_model,
            extra={"provider": "openai-stream"},
        )
        yield {
            "type": "done",
            "latency_ms": latency_ms,
            "tokens_in": 0,
            "tokens_out": len(full_response),
            "tokens_per_sec": round(len(full_response) / (latency_ms / 1000), 1) if latency_ms > 0 else 0,
            "model": used_model,
            "provider": "openai",
        }
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        import logging
        logging.getLogger("elixis.llm").warning(f"OpenAI stream failed: {e}")
        yield {"type": "error", "error": str(e), "provider": "openai", "model": used_model}
        yield {
            "type": "done",
            "success": False,
            "error": str(e),
            "latency_ms": int((time.time() - start) * 1000),
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_per_sec": 0,
            "model": used_model,
            "provider": "openai",
        }


def _chat_stream_anthropic(messages, model=None):
    """Stream from Anthropic's Messages API."""
    url = _anthropic_endpoint("messages")
    used_model = model or cfg.default_model
    payload = json.dumps(_anthropic_payload(messages, used_model, 2048, stream=True)).encode()
    req = urllib.request.Request(url, data=payload, headers=_anthropic_headers())
    start = time.time()
    full_response = []
    usage = {"input_tokens": 0, "output_tokens": 0}

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data: "):
                    continue
                try:
                    chunk = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                if chunk.get("type") == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        content = delta["text"]
                        full_response.append(content)
                        yield {"type": "token", "content": content}
                elif chunk.get("type") == "message_delta":
                    usage.update(chunk.get("usage", {}))

        latency_ms = int((time.time() - start) * 1000)
        full_text = "".join(full_response)
        prompt_text = messages[-1].get("content", "") if messages else ""
        tokens_in = usage.get("input_tokens", 0) or 0
        tokens_out = usage.get("output_tokens", 0) or len(full_response)
        tps = round(tokens_out / (latency_ms / 1000), 1) if latency_ms > 0 and tokens_out > 0 else 0

        from .traces import save_trace
        save_trace(
            prompt=prompt_text,
            response=full_text,
            latency_ms=latency_ms,
            model=used_model,
            extra={"provider": "anthropic-stream", "tokens_in": tokens_in, "tokens_out": tokens_out},
        )
        yield {
            "type": "done",
            "latency_ms": latency_ms,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_per_sec": tps,
            "model": used_model,
            "provider": "anthropic",
        }
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        import logging
        logging.getLogger("elixis.llm").warning(f"Anthropic stream failed: {e}")
        yield {"type": "error", "error": str(e), "provider": "anthropic", "model": used_model}
        yield {
            "type": "done",
            "success": False,
            "error": str(e),
            "latency_ms": int((time.time() - start) * 1000),
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_per_sec": 0,
            "model": used_model,
            "provider": "anthropic",
        }


def _chat_stream_ollama(messages, model=None):
    """Stream from Ollama's native API (/api/chat with stream=true)."""
    url = f"{cfg.base_url}/api/chat"
    payload = json.dumps({
        "model": model or cfg.default_model,
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
                    used_model = model or cfg.default_model
                    tokens_in = chunk.get("prompt_eval_count", 0) or 0
                    tokens_out = chunk.get("eval_count", 0) or 0
                    tps = round(tokens_out / (latency_ms / 1000), 1) if latency_ms > 0 and tokens_out > 0 else 0

                    from .traces import save_trace
                    save_trace(
                        prompt=prompt_text,
                        response=full_text,
                        latency_ms=latency_ms,
                        model=used_model,
                        extra={
                            "thinking": "".join(thinking_buffer) if thinking_buffer else None,
                            "tokens_in": tokens_in,
                            "tokens_out": tokens_out,
                            "tokens_per_sec": tps,
                        },
                    )
                    yield {
                        "type": "done",
                        "latency_ms": latency_ms,
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "tokens_per_sec": tps,
                        "model": used_model,
                        "provider": cfg.provider,
                    }

    except (urllib.error.URLError, OSError, TimeoutError) as e:
        yield {"type": "error", "error": str(e)}
        yield {
            "type": "done",
            "success": False,
            "error": str(e),
            "latency_ms": int((time.time() - start) * 1000),
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_per_sec": 0,
            "model": model or cfg.default_model,
            "provider": cfg.provider,
        }
        return
