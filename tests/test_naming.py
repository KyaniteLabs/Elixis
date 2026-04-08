"""Tests for naming research module."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soulcraft.naming import (
    research_name,
    format_research_report,
    _default_semantics,
)


class TestDefaultSemantics(unittest.TestCase):
    """Test default semantics structure."""

    def test_structure(self):
        """Default semantics has required fields."""
        result = _default_semantics()
        self.assertIn("themes", result)
        self.assertIn("pronounceability", result)
        self.assertIn("memorability", result)
        self.assertIn("uniqueness", result)


class TestResearchName(unittest.TestCase):
    """Test naming research pipeline."""

    def test_returns_report_structure(self):
        """Research returns proper report structure."""
        report = research_name("TestName", context="tech", generate_variants=False)

        self.assertIn("input_name", report)
        self.assertIn("context", report)
        self.assertIn("semantics", report)
        self.assertIn("recommendations", report)
        self.assertEqual(report["input_name"], "TestName")

    def test_semantics_populated(self):
        """Report includes semantic analysis."""
        report = research_name("Kyanite", context="AI platform")

        semantics = report.get("semantics", {})
        # Should have some analysis fields
        self.assertIn("themes", semantics)


class TestFormatResearchReport(unittest.TestCase):
    """Test report formatting."""

    def test_includes_name(self):
        """Formatted report includes input name."""
        report = {
            "input_name": "TestCorp",
            "context": "startup",
            "semantics": {
                "themes": ["innovation", "speed"],
                "pronounceability": 0.9,
                "memorability": 0.8,
                "uniqueness": 0.7,
                "positive_connotations": ["modern", "fast"],
                "negative_connotations": [],
            },
            "variants": [],
            "recommendations": ["Good choice"],
        }

        formatted = format_research_report(report)
        self.assertIn("TestCorp", formatted)
        self.assertIn("innovation", formatted)
        self.assertIn("Good choice", formatted)


if __name__ == "__main__":
    unittest.main()
