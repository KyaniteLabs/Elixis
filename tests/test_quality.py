"""Tests for output validation (elixis.quality)."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis.quality import validate_output, sanitize_output


def _make_good_identity_output():
    """Build a valid identity lens output that should pass."""
    return (
        "# Who I Am\n\nI am a thoughtful entity with a clear purpose.\n\n"
        "# Worldview\n\nThe world is interconnected and full of meaning.\n\n"
        "# Voice\n\nMy voice is calm, precise, and direct.\n\n"
        "# Operating Principles\n\nI operate with integrity and clarity.\n\n"
        "# Response Patterns\n\nI respond thoughtfully and thoroughly.\n\n"
        "# Boundaries\n\nI maintain clear boundaries around harmful content.\n\n"
        "# Pet Peeves\n\nI dislike vague instructions and unclear goals.\n\n"
        "This section adds length to ensure we pass the minimum character "
        "threshold for a valid output. The content here is substantive and "
        "well-structured to demonstrate quality output."
    )


class TestValidateOutputBasic(unittest.TestCase):
    """Basic validation: empty, None, and type checks."""

    def test_none_output_fails(self):
        result = validate_output(None)
        self.assertFalse(result["pass"])
        self.assertEqual(result["score"], 0.0)
        self.assertIn("Empty or invalid output", result["issues"])

    def test_empty_string_fails(self):
        result = validate_output("")
        self.assertFalse(result["pass"])
        self.assertEqual(result["score"], 0.0)
        self.assertTrue(len(result["issues"]) > 0)

    def test_non_string_fails(self):
        result = validate_output(12345)
        self.assertFalse(result["pass"])
        self.assertEqual(result["score"], 0.0)


class TestValidateOutputPassing(unittest.TestCase):
    """Valid outputs should pass with high scores."""

    def test_valid_identity_output_passes(self):
        output = _make_good_identity_output()
        result = validate_output(output, lens="identity")
        self.assertTrue(result["pass"])
        self.assertGreaterEqual(result["score"], 0.5)
        self.assertEqual(result["issues"], [])

    def test_good_output_has_high_score(self):
        output = _make_good_identity_output()
        result = validate_output(output, lens="identity")
        self.assertGreaterEqual(result["score"], 0.7)


class TestValidateOutputMissingSections(unittest.TestCase):
    """Outputs missing required sections should report them."""

    def test_missing_sections_reported(self):
        output = (
            "# Who I Am\n\nSome content.\n\n"
            "# Worldview\n\nMore content.\n\n"
            "# Voice\n\nVoice content.\n\n"
            "Padding to exceed two hundred characters for the length check. "
            "Adding more text here so the output is long enough to not fail "
            "the short-output check but still missing several sections."
        )
        result = validate_output(output, lens="identity")
        self.assertFalse(result["pass"])
        missing_text = result["issues"]
        self.assertTrue(
            any("Missing sections" in i for i in missing_text),
            f"Expected 'Missing sections' issue, got: {missing_text}",
        )


class TestValidateOutputPromptLeakage(unittest.TestCase):
    """Prompt leakage patterns should cause failure."""

    def test_as_an_ai_fails(self):
        output = _make_good_identity_output().replace(
            "I am a thoughtful", "As an AI, I am a thoughtful"
        )
        result = validate_output(output, lens="identity")
        self.assertFalse(result["pass"])
        self.assertTrue(
            any("leakage" in i.lower() for i in result["issues"])
        )

    def test_im_sorry_fails(self):
        output = _make_good_identity_output().replace(
            "I am a thoughtful", "I'm sorry, I am a thoughtful"
        )
        result = validate_output(output, lens="identity")
        self.assertFalse(result["pass"])

    def test_i_cannot_fails(self):
        output = _make_good_identity_output() + "\n\nI cannot fulfill that request."
        result = validate_output(output, lens="identity")
        self.assertFalse(result["pass"])


class TestValidateOutputPII(unittest.TestCase):
    """PII detection should produce warnings."""

    def test_ssn_like_pattern_warns(self):
        output = _make_good_identity_output() + "\n\nContact: 123-45-6789"
        result = validate_output(output, lens="identity")
        self.assertTrue(
            any("PII" in w for w in result["warnings"]),
            f"Expected PII warning, got: {result['warnings']}",
        )

    def test_email_warns(self):
        output = _make_good_identity_output() + "\n\nEmail: test@example.com"
        result = validate_output(output, lens="identity")
        self.assertTrue(
            any("PII" in w for w in result["warnings"]),
            f"Expected PII warning, got: {result['warnings']}",
        )

    def test_credit_card_warns(self):
        output = _make_good_identity_output() + "\n\nCard: 1234567890123456"
        result = validate_output(output, lens="identity")
        self.assertTrue(
            any("PII" in w for w in result["warnings"]),
            f"Expected PII warning, got: {result['warnings']}",
        )


class TestValidateOutputLength(unittest.TestCase):
    """Length checks: too short, medium, and adequate."""

    def test_short_output_fails(self):
        output = "Too short."
        result = validate_output(output, lens="identity")
        self.assertFalse(result["pass"])
        self.assertTrue(
            any("too short" in i.lower() for i in result["issues"])
        )

    def test_medium_output_gets_warning(self):
        output = "x" * 300
        result = validate_output(output, lens="identity")
        self.assertTrue(
            any("short" in w.lower() for w in result["warnings"]),
            f"Expected short warning, got: {result['warnings']}",
        )

    def test_adequate_length_no_warning(self):
        output = _make_good_identity_output()
        result = validate_output(output, lens="identity")
        short_warnings = [w for w in result["warnings"] if "short" in w.lower()]
        self.assertEqual(short_warnings, [])


class TestValidateOutputHeaders(unittest.TestCase):
    """Structural quality: section headers."""

    def test_good_output_has_section_headers(self):
        output = _make_good_identity_output()
        result = validate_output(output, lens="identity")
        # Good identity output has 7 headers, should not get "Few headers" warning
        few_header_warnings = [w for w in result["warnings"] if "Few" in w]
        self.assertEqual(few_header_warnings, [])

    def test_output_with_few_headers_warns(self):
        # Only 1 header, well under the threshold of 3
        output = "# Only Header\n\n" + "word " * 200
        result = validate_output(output, lens="identity")
        self.assertTrue(
            any("Few section headers" in w for w in result["warnings"]),
            f"Expected 'Few section headers' warning, got: {result['warnings']}",
        )


class TestValidateOutputLenses(unittest.TestCase):
    """Lens-specific section checks."""

    def test_brand_lens_checks_brand_sections(self):
        output = (
            "# Source Anchors\n\nInput anchors.\n\n"
            "# Pattern Rationale\n\nPattern support.\n\n"
            "# Core Identity\n\nBrand identity here.\n\n"
            "# Voice Attributes\n\nVoice details.\n\n"
            "# Tone Spectrum\n\nTone info.\n\n"
            "# Vocabulary\n\nWord list.\n\n"
            "Additional padding text to reach the two hundred character minimum "
            "required for passing validation. More content here to ensure length."
        )
        result = validate_output(output, lens="brand")
        missing_issues = [i for i in result["issues"] if "Missing sections" in i]
        self.assertEqual(missing_issues, [])

    def test_design_lens_checks_design_sections(self):
        output = (
            "# Source Anchors\n\nInput anchors.\n\n"
            "# Pattern Rationale\n\nPattern support.\n\n"
            "# Color Palette\n\nColors.\n\n"
            "# Typography\n\nType.\n\n"
            "# Spacing\n\nSpace.\n\n"
            "# Design Principles\n\nPrinciples.\n\n"
            "Additional padding text to reach the two hundred character minimum "
            "required for passing validation. More content here to ensure length."
        )
        result = validate_output(output, lens="design")
        missing_issues = [i for i in result["issues"] if "Missing sections" in i]
        self.assertEqual(missing_issues, [])

    def test_unknown_lens_uses_empty_required_sections(self):
        output = "word " * 200
        result = validate_output(output, lens="nonexistent")
        missing_issues = [i for i in result["issues"] if "Missing sections" in i]
        self.assertEqual(missing_issues, [])


class TestSanitizeOutput(unittest.TestCase):
    """sanitize_output removes prompt leakage artifacts."""

    def test_removes_as_an_ai_line(self):
        text = "Good line.\nAs an AI, I think this.\nAnother good line."
        result = sanitize_output(text)
        self.assertNotIn("As an AI", result)
        self.assertIn("Good line.", result)
        self.assertIn("Another good line.", result)

    def test_removes_code_blocks(self):
        text = "Before.\n```markdown\n## leaked\n```\nAfter."
        result = sanitize_output(text)
        self.assertNotIn("```", result)
        self.assertIn("Before.", result)
        self.assertIn("After.", result)

    def test_returns_stripped_result(self):
        text = "\n\n  Good content here.  \n\n"
        result = sanitize_output(text)
        self.assertEqual(result, "Good content here.")

    def test_removes_generate_a_line(self):
        text = "Good.\nGenerate a brand voice document.\nAlso good."
        result = sanitize_output(text)
        self.assertNotIn("Generate a", result)

    def test_removes_respond_with_only(self):
        text = "Good.\nRespond with ONLY JSON.\nAlso good."
        result = sanitize_output(text)
        self.assertNotIn("Respond with ONLY", result)


if __name__ == "__main__":
    unittest.main()
