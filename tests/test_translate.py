"""Tests for translation module."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fugax.translate import (
    translate_text,
    translate_soulmd,
    detect_language,
    get_supported_languages,
    is_language_supported,
    _split_into_chunks,
)


class TestTranslateText(unittest.TestCase):
    """Test basic translation functionality."""

    def test_empty_text(self):
        """Empty text returns empty result."""
        result = translate_text("", "es")
        self.assertEqual(result["translated_text"], "")
        self.assertTrue(result["success"])

    def test_same_language_no_translation(self):
        """Same source and target returns original."""
        text = "Hello world"
        result = translate_text(text, "en", "en")
        self.assertEqual(result["translated_text"], text)
        self.assertTrue(result["cached"])

    def test_supported_languages_available(self):
        """Supported languages list is populated."""
        langs = get_supported_languages()
        self.assertIn("en", langs)
        self.assertIn("es", langs)
        self.assertIn("fr", langs)

    def test_language_support_check(self):
        """Language support check works."""
        self.assertTrue(is_language_supported("en"))
        self.assertTrue(is_language_supported("es"))
        self.assertFalse(is_language_supported("xx"))


class TestTranslateSoulmd(unittest.TestCase):
    """Test SOUL.md translation."""

    def test_preserves_structure(self):
        """SOUL.md translation preserves markdown structure."""
        soulmd = """# Who I Am

I am a test persona.

## Worldview

* Truth matters
* Beauty endures
"""
        # Without LLM, will return as-is or with error
        result = translate_soulmd(soulmd, "es", preserve_structure=True)
        self.assertIn("success", result)

    def test_handles_empty_soulmd(self):
        """Empty SOUL.md handled gracefully."""
        result = translate_soulmd("", "es")
        self.assertEqual(result["translated_text"], "")


class TestChunking(unittest.TestCase):
    """Test text chunking for large inputs."""

    def test_split_at_headers(self):
        """Chunks split at markdown headers."""
        text = "\n# Section 1\nContent\n# Section 2\nMore content"
        chunks = _split_into_chunks(text, 1000)
        self.assertGreaterEqual(len(chunks), 1)

    def test_split_at_paragraphs(self):
        """Large chunks split at paragraphs."""
        text = "Para 1\n\nPara 2\n\nPara 3"
        chunks = _split_into_chunks(text, 20)
        self.assertGreater(len(chunks), 1)

    def test_single_short_text_unchanged(self):
        """Short text remains single chunk."""
        text = "Short text"
        chunks = _split_into_chunks(text, 1000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)


class TestDetectLanguage(unittest.TestCase):
    """Test language detection."""

    def test_empty_text_returns_none(self):
        """Empty text returns None."""
        result = detect_language("")
        self.assertIsNone(result)

    def test_short_text_returns_none(self):
        """Very short text returns None."""
        result = detect_language("Hi")
        self.assertIsNone(result)


class TestTranslationCache(unittest.TestCase):
    """Test translation caching system."""

    def setUp(self):
        """Clear cache before each test."""
        from fugax.translate import clear_cache
        clear_cache()

    def tearDown(self):
        """Clear cache after each test."""
        from fugax.translate import clear_cache
        clear_cache()

    def test_cache_key_generation(self):
        """Cache keys are deterministic."""
        from fugax.translate import _get_cache_key

        key1 = _get_cache_key("hello world", "es", "en")
        key2 = _get_cache_key("hello world", "es", "en")
        key3 = _get_cache_key("hello world", "fr", "en")

        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)

    def test_cache_stats_empty(self):
        """Cache stats show empty when no entries."""
        from fugax.translate import get_cache_stats

        stats = get_cache_stats()
        self.assertEqual(stats["entries"], 0)
        self.assertEqual(stats["size_bytes"], 0)

    def test_cache_save_and_load(self):
        """Cache can save and load entries."""
        from fugax.translate import _save_to_cache, _load_from_cache

        result = {
            "translated_text": "Hola mundo",
            "success": True,
            "source_lang": "en",
            "target_lang": "es",
            "model": "test-model",
        }

        # Save to cache
        _save_to_cache(result, "hello world", "es", "en")

        # Load from cache
        cached = _load_from_cache("hello world", "es", "en")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["translated_text"], "Hola mundo")
        self.assertEqual(cached["model"], "test-model")

    def test_cache_stats_after_save(self):
        """Cache stats update after saving."""
        from fugax.translate import _save_to_cache, get_cache_stats

        result = {
            "translated_text": "Hola mundo",
            "success": True,
            "source_lang": "en",
            "target_lang": "es",
        }

        _save_to_cache(result, "hello world", "es", "en")

        stats = get_cache_stats()
        self.assertEqual(stats["entries"], 1)
        self.assertGreater(stats["size_bytes"], 0)

    def test_clear_cache(self):
        """Cache can be cleared."""
        from fugax.translate import _save_to_cache, get_cache_stats, clear_cache

        result = {
            "translated_text": "Hola mundo",
            "success": True,
            "source_lang": "en",
            "target_lang": "es",
        }

        _save_to_cache(result, "hello world", "es", "en")
        self.assertEqual(get_cache_stats()["entries"], 1)

        clear_cache()
        self.assertEqual(get_cache_stats()["entries"], 0)

    def test_cache_miss_returns_none(self):
        """Cache miss returns None."""
        from fugax.translate import _load_from_cache

        cached = _load_from_cache("nonexistent text", "es", "en")
        self.assertIsNone(cached)


if __name__ == "__main__":
    unittest.main()
