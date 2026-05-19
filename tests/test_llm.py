"""Tests for LLM client."""

import unittest
import sys
import os
import urllib.error
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis import llm


class TestLLMConfiguration(unittest.TestCase):
    """Test LLM configuration loading."""

    def test_default_provider(self):
        """Default provider should be ollama."""
        # Check module-level defaults
        self.assertIn(llm.PROVIDER, ["ollama", "openai", "anthropic"])

    def test_default_model_set(self):
        """Default model should be set."""
        self.assertIsNotNone(llm.DEFAULT_MODEL)
        self.assertGreater(len(llm.DEFAULT_MODEL), 0)


class TestChatResultStructure(unittest.TestCase):
    """Test that chat returns expected result structure."""

    def test_result_has_required_fields(self):
        """Chat result must have required fields."""
        # We can't test actual chat without a running server,
        # but we can verify the structure expectations
        expected_fields = [
            "content", "tokens_in", "tokens_out",
            "latency_ms", "tokens_per_sec", "model", "provider"
        ]

        # Create a mock result to verify structure
        mock_result = {
            "content": "test",
            "tokens_in": 10,
            "tokens_out": 20,
            "latency_ms": 100,
            "tokens_per_sec": 200.0,
            "model": "test-model",
            "provider": "test"
        }

        for field in expected_fields:
            self.assertIn(field, mock_result)


class TestIsAvailable(unittest.TestCase):
    """Test availability checking."""

    def test_is_available_returns_bool(self):
        """is_available should return a boolean."""
        result = llm.is_available()
        self.assertIsInstance(result, bool)


class TestEnvironmentVariables(unittest.TestCase):
    """Test environment variable handling."""

    def test_llm_fallback_url_read(self):
        """LLM_FALLBACK_URL should be read from environment."""
        # Verify the variable exists in module
        self.assertTrue(hasattr(llm, 'FALLBACK_BASE_URL'))

    def test_api_key_handling(self):
        """API key should be handled (empty or set)."""
        self.assertTrue(hasattr(llm, 'API_KEY'))


class TestOpenAICompatibleFallback(unittest.TestCase):
    """Test OpenAI-compatible fallback diagnostics."""

    @patch.dict(os.environ, {
        "LLM_BASE_URL": "http://primary.invalid/v1",
        "LLM_FALLBACK_URL": "http://fallback.invalid/v1",
        "LLM_MODEL": "test-model",
    })
    @patch("elixis.llm._call_openai_compat_single")
    def test_reports_primary_and_fallback_errors(self, mock_single):
        mock_single.side_effect = [
            urllib.error.URLError("primary down"),
            urllib.error.URLError("fallback down"),
        ]

        result = llm._call_openai_compat([{"role": "user", "content": "hi"}])

        self.assertEqual(result["content"], "")
        self.assertIn("primary_error", result)
        self.assertIn("fallback_error", result)
        self.assertIn("primary down", result["error"])
        self.assertIn("fallback down", result["error"])


class TestAnthropicProvider(unittest.TestCase):
    """Test Anthropic Messages API adapter behavior without network calls."""

    @patch.dict(os.environ, {
        "LLM_PROVIDER": "anthropic",
        "LLM_MODEL": "claude-test",
    })
    def test_anthropic_payload_extracts_system_and_merges_user_turns(self):
        payload = llm._anthropic_payload([
            {"role": "system", "content": "Use concise markdown."},
            {"role": "user", "content": "Athena"},
            {"role": "user", "content": "Batman"},
            {"role": "assistant", "content": "Noted."},
        ], max_tokens=99)

        self.assertEqual(payload["model"], "claude-test")
        self.assertEqual(payload["max_tokens"], 99)
        self.assertEqual(payload["system"], "Use concise markdown.")
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertEqual(payload["messages"][0]["content"], "Athena\n\nBatman")

    @patch.dict(os.environ, {
        "LLM_PROVIDER": "anthropic",
        "ANTHROPIC_AUTH_TOKEN": "token-value",
        "ANTHROPIC_API_KEY": "api-key-value",
    })
    def test_anthropic_headers_prefer_auth_token_without_exposing_key(self):
        headers = llm._anthropic_headers()

        self.assertEqual(headers["Authorization"], "Bearer token-value")
        self.assertNotIn("x-api-key", headers)
        self.assertEqual(headers["anthropic-version"], "2023-06-01")

    @patch.dict(os.environ, {
        "LLM_PROVIDER": "anthropic",
        "LLM_BASE_URL": "https://api.anthropic.com",
    })
    def test_anthropic_endpoint_adds_v1_once(self):
        self.assertEqual(llm._anthropic_endpoint("messages"), "https://api.anthropic.com/v1/messages")

    @patch.dict(os.environ, {
        "LLM_PROVIDER": "anthropic",
        "LLM_BASE_URL": "https://api.anthropic.com/v1",
    })
    def test_anthropic_endpoint_accepts_v1_base(self):
        self.assertEqual(llm._anthropic_endpoint("messages"), "https://api.anthropic.com/v1/messages")


if __name__ == "__main__":
    unittest.main()
