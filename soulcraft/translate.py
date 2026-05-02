"""On-the-fly translation for SoulCraft using local LLM inference.

Translates SOUL.md output to any language user selects.
Uses local inference servers (VPS + fallback) for zero external API costs.
"""

import hashlib
import json
import os
import re
from typing import Optional, Dict, List, Generator
from .llm import chat, chat_stream, is_available


# Cache configuration — use project-local directory so it persists in Docker
_PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".soulcraft")
CACHE_DIR = os.environ.get("SOULCRAFT_CACHE_DIR", os.path.join(_PROJECT_DIR, "translations"))
CACHE_MAX_AGE_DAYS = 30  # Cache entries expire after 30 days
CACHE_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB max total cache size
MAX_TRANSLATE_TEXT_LENGTH = 50000  # 50K chars max for translation input


def _get_cache_key(text: str, target_lang: str, source_lang: str) -> str:
    """Generate a cache key from translation parameters."""
    content = f"{source_lang}:{target_lang}:{text}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _get_cache_path(cache_key: str) -> str:
    """Get the file path for a cache key."""
    return os.path.join(CACHE_DIR, f"{cache_key}.json")


def _load_from_cache(text: str, target_lang: str, source_lang: str) -> Optional[Dict]:
    """Load translation result from cache if it exists and is not expired."""
    cache_key = _get_cache_key(text, target_lang, source_lang)
    cache_path = _get_cache_path(cache_key)

    if not os.path.exists(cache_path):
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)

        # Check if cache is expired
        import time
        cache_time = cached.get("cached_at", 0)
        age_days = (time.time() - cache_time) / (24 * 3600)

        if age_days > CACHE_MAX_AGE_DAYS:
            os.remove(cache_path)
            return None

        return cached
    except (json.JSONDecodeError, OSError):
        return None


def _save_to_cache(result: Dict, text: str, target_lang: str, source_lang: str):
    """Save translation result to cache."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        _evict_cache_if_needed()
        cache_key = _get_cache_key(text, target_lang, source_lang)
        cache_path = _get_cache_path(cache_key)

        import time
        cache_entry = {
            **result,
            "cached_at": time.time(),
            "cache_hit": True,
        }

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_entry, f, ensure_ascii=False)
    except OSError:
        pass


def _evict_cache_if_needed():
    """Remove oldest cache entries if total size exceeds limit."""
    if not os.path.exists(CACHE_DIR):
        return
    try:
        entries = []
        total_size = 0
        for filename in os.listdir(CACHE_DIR):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(CACHE_DIR, filename)
            try:
                stat = os.stat(filepath)
                entries.append((filepath, stat.st_mtime, stat.st_size))
                total_size += stat.st_size
            except OSError:
                continue

        if total_size <= CACHE_MAX_SIZE_BYTES:
            return

        # Sort by modification time (oldest first) and evict until under limit
        entries.sort(key=lambda e: e[1])
        for filepath, _, size in entries:
            if total_size <= CACHE_MAX_SIZE_BYTES * 0.8:  # Evict to 80% of limit
                break
            try:
                os.remove(filepath)
                total_size -= size
            except OSError:
                pass
    except OSError:
        pass


def get_cache_stats() -> Dict:
    """Get statistics about the translation cache."""
    if not os.path.exists(CACHE_DIR):
        return {"entries": 0, "size_bytes": 0}

    total_size = 0
    entries = 0

    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CACHE_DIR, filename)
            try:
                total_size += os.path.getsize(filepath)
                entries += 1
            except OSError:
                pass

    return {
        "entries": entries,
        "size_bytes": total_size,
        "size_human": f"{total_size / 1024:.1f} KB" if total_size < 1024*1024 else f"{total_size / (1024*1024):.1f} MB",
    }


def clear_cache() -> Dict:
    """Clear all cached translations."""
    if not os.path.exists(CACHE_DIR):
        return {"removed": 0}

    removed = 0
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".json"):
            try:
                os.remove(os.path.join(CACHE_DIR, filename))
                removed += 1
            except OSError:
                pass

    return {"removed": removed}


# Common language codes mapped to human-readable names
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "cs": "Czech",
    "el": "Greek",
    "he": "Hebrew",
    "id": "Indonesian",
    "ms": "Malay",
    "uk": "Ukrainian",
    "ro": "Romanian",
    "hu": "Hungarian",
}


def translate_text(
    text: str,
    target_lang: str,
    source_lang: str = "en",
    max_tokens: int = 4096
) -> Dict:
    """Translate text using local LLM inference.

    Args:
        text: Text to translate
        target_lang: Target language code (e.g., "es", "fr")
        source_lang: Source language (default "en")
        max_tokens: Maximum output tokens

    Returns:
        Dict with translated_text, success flag, and metadata
    """
    if not text or not text.strip():
        return {
            "translated_text": "",
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "model": None,
        }

    if len(text) > MAX_TRANSLATE_TEXT_LENGTH:
        return {
            "translated_text": "",
            "success": False,
            "error": f"Text too long ({len(text)} chars, max {MAX_TRANSLATE_TEXT_LENGTH})",
            "source_lang": source_lang,
            "target_lang": target_lang,
        }

    if target_lang == source_lang:
        return {
            "translated_text": text,
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "cached": True,
        }

    # Check cache first
    cached = _load_from_cache(text, target_lang, source_lang)
    if cached:
        return {
            "translated_text": cached["translated_text"],
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "cached": True,
            "model": cached.get("model"),
        }

    # Check if LLM is available
    if not is_available():
        return {
            "translated_text": text,
            "success": False,
            "error": "LLM inference unavailable",
            "source_lang": source_lang,
            "target_lang": target_lang,
        }

    target_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)

    system_prompt = (
        f"You are a professional translator. Translate the following text to {target_name}. "
        f"Preserve all markdown formatting, headers, and structure. "
        f"Maintain the tone and voice of the original. "
        f"Respond with ONLY the translated text, no explanations."
    )

    # Split long text into chunks if needed
    max_chunk_size = 3000  # Characters per chunk
    if len(text) > max_chunk_size:
        return _translate_large_text(text, target_lang, source_lang, max_chunk_size)

    try:
        result = chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            max_tokens=max_tokens,
            think=False,  # Faster translation without thinking
        )

        translated = result.get("content", "").strip()

        # Clean up any code blocks if the model wraps output
        if translated.startswith("```"):
            translated = re.sub(r"^```[\w]*\n?", "", translated)
            translated = re.sub(r"\n?```$", "", translated)

        result_dict = {
            "translated_text": translated,
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "model": result.get("model"),
            "tokens_in": result.get("tokens_in"),
            "tokens_out": result.get("tokens_out"),
            "latency_ms": result.get("latency_ms"),
            "fallback_used": result.get("fallback", False),
        }

        # Save to cache
        _save_to_cache(result_dict, text, target_lang, source_lang)

        return result_dict

    except Exception as e:
        return {
            "translated_text": text,
            "success": False,
            "error": str(e),
            "source_lang": source_lang,
            "target_lang": target_lang,
        }


def _translate_large_text(
    text: str,
    target_lang: str,
    source_lang: str,
    chunk_size: int
) -> Dict:
    """Translate large text in chunks and reassemble."""
    chunks = _split_into_chunks(text, chunk_size)
    translated_chunks = []
    total_latency = 0
    total_tokens_in = 0
    total_tokens_out = 0
    any_fallback = False

    for chunk in chunks:
        result = translate_text(chunk, target_lang, source_lang)
        if result["success"]:
            translated_chunks.append(result["translated_text"])
            total_latency += result.get("latency_ms", 0)
            total_tokens_in += result.get("tokens_in", 0)
            total_tokens_out += result.get("tokens_out", 0)
            if result.get("fallback_used"):
                any_fallback = True
        else:
            # If translation fails, keep original chunk
            translated_chunks.append(chunk)

    return {
        "translated_text": "\n\n".join(translated_chunks),
        "success": True,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "chunks": len(chunks),
        "latency_ms": total_latency,
        "tokens_in": total_tokens_in,
        "tokens_out": total_tokens_out,
        "fallback_used": any_fallback,
    }


def _split_into_chunks(text: str, max_size: int) -> List[str]:
    """Split text into chunks at logical boundaries."""
    # Try to split at section boundaries first
    sections = re.split(r"\n(?=#+ )", text)

    chunks = []
    current_chunk = ""

    for section in sections:
        if len(current_chunk) + len(section) < max_size:
            current_chunk += section + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = section + "\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    # If any chunk is still too big, split at paragraph boundaries
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > max_size:
            paragraphs = chunk.split("\n\n")
            current = ""
            for para in paragraphs:
                if len(current) + len(para) < max_size:
                    current += para + "\n\n"
                else:
                    if current:
                        final_chunks.append(current.strip())
                    current = para + "\n\n"
            if current:
                final_chunks.append(current.strip())
        else:
            final_chunks.append(chunk)

    return final_chunks if final_chunks else [text]


def translate_soulmd(
    soulmd: str,
    target_lang: str,
    preserve_structure: bool = True
) -> Dict:
    """Translate a SOUL.md document to target language.

    Args:
        soulmd: The SOUL.md content
        target_lang: Target language code
        preserve_structure: Whether to preserve markdown structure

    Returns:
        Translation result dict
    """
    if not preserve_structure:
        return translate_text(soulmd, target_lang)

    # For SOUL.md, we want to translate content while preserving:
    # - Headers (# ## ###)
    # - List markers (- *)
    # - Bold/italic markers

    result = translate_text(soulmd, target_lang)

    if result["success"]:
        # Post-process to fix any markdown issues
        translated = result["translated_text"]

        # Ensure headers have space after #
        translated = re.sub(r"^(#{1,6})([^ #])", r"\1 \2", translated, flags=re.MULTILINE)

        # Ensure list items have space after marker
        translated = re.sub(r"^([-*])([^ ])", r"\1 \2", translated, flags=re.MULTILINE)

        result["translated_text"] = translated

    return result


def detect_language(text: str) -> Optional[str]:
    """Attempt to detect language of input text using LLM.

    Args:
        text: Text to analyze

    Returns:
        Language code or None if detection fails
    """
    if not text or len(text) < 10:
        return None

    if not is_available():
        return None

    sample = text[:500]  # Use first 500 chars for detection

    try:
        result = chat(
            [
                {
                    "role": "system",
                    "content": "You are a language detector. Respond with ONLY the ISO 639-1 language code (e.g., 'en', 'es', 'fr') of the text."
                },
                {"role": "user", "content": f"What language is this?\n\n{sample}"},
            ],
            max_tokens=10,
            think=False,
        )

        lang = result.get("content", "").strip().lower()
        # Extract just the code
        match = re.search(r"\b([a-z]{2})\b", lang)
        if match:
            return match.group(1)
        return None

    except Exception:
        return None


def get_supported_languages() -> Dict[str, str]:
    """Get list of supported languages."""
    return SUPPORTED_LANGUAGES.copy()


def is_language_supported(lang_code: str) -> bool:
    """Check if a language code is supported."""
    return lang_code in SUPPORTED_LANGUAGES


def translate_text_stream(
    text: str,
    target_lang: str,
    source_lang: str = "en"
) -> Generator[Dict, None, None]:
    """Stream translation tokens as they arrive from LLM.

    Args:
        text: Text to translate
        target_lang: Target language code
        source_lang: Source language (default "en")

    Yields:
        Dict events: {"type": "token", "content": "..."} or {"type": "done", ...}
    """
    if not text or not text.strip():
        yield {"type": "done", "translated_text": "", "success": True}
        return

    if target_lang == source_lang:
        yield {"type": "token", "content": text}
        yield {"type": "done", "translated_text": text, "success": True, "cached": True}
        return

    # Check cache first
    cached = _load_from_cache(text, target_lang, source_lang)
    if cached:
        # Yield cached result as a single token for instant response
        translated_text = cached["translated_text"]
        yield {"type": "token", "content": translated_text}
        yield {
            "type": "done",
            "translated_text": translated_text,
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "cached": True,
            "model": cached.get("model"),
        }
        return

    if not is_available():
        yield {"type": "error", "error": "LLM inference unavailable"}
        yield {"type": "done", "translated_text": text, "success": False}
        return

    target_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)

    system_prompt = (
        f"You are a professional translator. Translate the following text to {target_name}. "
        f"Preserve all markdown formatting, headers, and structure. "
        f"Maintain the tone and voice of the original. "
        f"Respond with ONLY the translated text, no explanations."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]

    translated_parts = []

    try:
        for event in chat_stream(messages):
            if event["type"] == "token":
                translated_parts.append(event["content"])
                yield {"type": "token", "content": event["content"]}
            elif event["type"] == "done":
                full_text = "".join(translated_parts)
                # Clean up code blocks if present
                if full_text.startswith("```"):
                    full_text = re.sub(r"^```[\w]*\n?", "", full_text)
                    full_text = re.sub(r"\n?```$", "", full_text)

                result_dict = {
                    "type": "done",
                    "translated_text": full_text,
                    "success": True,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "model": event.get("model"),
                    "latency_ms": event.get("latency_ms"),
                    "tokens_in": event.get("tokens_in"),
                    "tokens_out": event.get("tokens_out"),
                }

                # Save to cache
                _save_to_cache({
                    "translated_text": full_text,
                    "success": True,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "model": event.get("model"),
                }, text, target_lang, source_lang)

                yield result_dict
            elif event["type"] == "thinking":
                # Skip thinking tokens for translation
                continue
    except Exception as e:
        yield {"type": "error", "error": str(e)}
        yield {"type": "done", "translated_text": text, "success": False}
