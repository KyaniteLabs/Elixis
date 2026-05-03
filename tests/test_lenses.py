"""Tests for output lenses (fugax.lenses).

Covers __init__.py (registry), brand.py, and design.py.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fugax.lenses import LENS_REGISTRY, AVAILABLE_LENSES
from fugax.lenses.brand import generate_brand
from fugax.lenses.design import (
    generate_design,
    _hex_to_hsl,
    _hsl_to_hex,
    _derive_palette,
)


def _make_good_pattern():
    return {
        "id": "transformation",
        "name": "Metamorphosis",
        "color": "#e74c3c",
        "supporting_entities": 3,
        "themes": ["power", "transformation"],
        "probability": 0.3,
    }


def _make_graph(*patterns):
    return {
        "patterns": list(patterns),
        "emergent_topic": "Test Topic",
        "consensus_score": 0.8,
        "entity_scores": {},
    }


# ---------------------------------------------------------------------------
# Lens registry tests
# ---------------------------------------------------------------------------

class TestLensRegistry(unittest.TestCase):
    """LENS_REGISTRY and AVAILABLE_LENSES from __init__.py."""

    def test_registry_has_identity(self):
        self.assertIn("identity", LENS_REGISTRY)

    def test_registry_has_brand(self):
        self.assertIn("brand", LENS_REGISTRY)

    def test_registry_has_design(self):
        self.assertIn("design", LENS_REGISTRY)

    def test_available_lenses_is_sorted(self):
        self.assertEqual(AVAILABLE_LENSES, sorted(AVAILABLE_LENSES))

    def test_available_lenses_matches_registry_keys(self):
        self.assertEqual(set(AVAILABLE_LENSES), set(LENS_REGISTRY.keys()))


# ---------------------------------------------------------------------------
# Brand lens tests
# ---------------------------------------------------------------------------

class TestGenerateBrandFallback(unittest.TestCase):
    """generate_brand with empty/missing patterns."""

    def test_empty_patterns_returns_fallback(self):
        result = generate_brand([], {"patterns": []})
        self.assertIn("Unknown", result)
        self.assertIn("Insufficient", result)

    def test_no_patterns_key_returns_fallback(self):
        result = generate_brand([], {})
        self.assertIn("Unknown", result)


class TestGenerateBrandValid(unittest.TestCase):
    """generate_brand with valid pattern data."""

    def test_returns_markdown_with_expected_sections(self):
        p = _make_good_pattern()
        result = generate_brand([], _make_graph(p))
        expected_sections = [
            "Core Identity",
            "Voice Attributes",
            "Tone Spectrum",
            "Vocabulary",
            "Anti-Vocabulary",
            "Color Direction",
            "Typography",
        ]
        for section in expected_sections:
            self.assertIn(
                section,
                result,
                f"Missing section: {section}",
            )

    def test_uses_pattern_topic(self):
        p = _make_good_pattern()
        result = generate_brand([], _make_graph(p))
        self.assertIn("Test Topic", result)

    def test_uses_pattern_colors(self):
        p = _make_good_pattern()
        result = generate_brand([], _make_graph(p))
        self.assertIn("#e74c3c", result)

    def test_brand_output_is_string(self):
        p = _make_good_pattern()
        result = generate_brand([], _make_graph(p))
        self.assertIsInstance(result, str)


class TestGenerateBrandToneVariants(unittest.TestCase):
    """generate_brand for different archetype IDs."""

    def test_power_archetype(self):
        p = {"id": "power", "name": "Dominion", "color": "#2c3e50"}
        result = generate_brand([], _make_graph(p))
        self.assertIn("Core Identity", result)
        # "power" archetype vocabulary includes "dominion"
        self.assertIn("dominion", result.lower())
        # Uses the graph's emergent_topic as the brand title
        self.assertIn("Test Topic", result)
        self.assertIn("#2c3e50", result)

    def test_unknown_archetype_uses_default(self):
        p = {"id": "nonexistent", "name": "Mystery", "color": "#aaaaaa"}
        result = generate_brand([], _make_graph(p))
        # Should still produce a valid brand doc (falls back to wisdom default)
        self.assertIn("Core Identity", result)


# ---------------------------------------------------------------------------
# Design lens tests
# ---------------------------------------------------------------------------

class TestGenerateDesignFallback(unittest.TestCase):
    """generate_design with empty/missing patterns."""

    def test_empty_patterns_returns_fallback(self):
        result = generate_design([], {"patterns": []})
        self.assertIn("Unknown", result)
        self.assertIn("Insufficient", result)

    def test_no_patterns_key_returns_fallback(self):
        result = generate_design([], {})
        self.assertIn("Unknown", result)


class TestGenerateDesignValid(unittest.TestCase):
    """generate_design with valid pattern data."""

    def test_returns_css_custom_properties(self):
        p = _make_good_pattern()
        result = generate_design([], _make_graph(p))
        self.assertIn("--color-primary:", result)
        self.assertIn("--font-hero:", result)
        self.assertIn("--spacing-xs:", result)
        self.assertIn("--radius-sm:", result)
        self.assertIn("--shadow-sm:", result)

    def test_contains_expected_sections(self):
        p = _make_good_pattern()
        result = generate_design([], _make_graph(p))
        expected = [
            "Color Palette",
            "Typography Scale",
            "Spacing Scale",
            "Border Radius",
            "Shadow System",
            "Design Principles",
        ]
        for section in expected:
            self.assertIn(section, result, f"Missing section: {section}")

    def test_design_output_is_string(self):
        p = _make_good_pattern()
        result = generate_design([], _make_graph(p))
        self.assertIsInstance(result, str)


class TestGenerateDesignEdgeCases(unittest.TestCase):
    """Edge cases for generate_design."""

    def test_pattern_without_color_uses_default(self):
        p = {"id": "transformation", "name": "No Color"}
        result = generate_design([], _make_graph(p))
        # Default color #666666 should appear
        self.assertIn("#666666", result)

    def test_pattern_without_id_uses_name(self):
        p = {"name": "wisdom", "color": "#3498db"}
        result = generate_design([], _make_graph(p))
        self.assertIn("Color Palette", result)


# ---------------------------------------------------------------------------
# Color utility tests
# ---------------------------------------------------------------------------

class TestDerivePalette(unittest.TestCase):
    """_derive_palette produces valid 5-color palettes."""

    def test_returns_five_colors(self):
        patterns = [{"color": "#e74c3c"}]
        palette = _derive_palette(patterns)
        self.assertEqual(len(palette), 5)
        for key in ("primary", "secondary", "accent", "background", "text"):
            self.assertIn(key, palette)

    def test_all_colors_are_valid_hex(self):
        patterns = [{"color": "#3498db"}]
        palette = _derive_palette(patterns)
        for key, color in palette.items():
            self.assertRegex(
                color,
                r"^#[0-9a-f]{6}$",
                f"Invalid hex color for {key}: {color}",
            )

    def test_primary_matches_input(self):
        patterns = [{"color": "#e74c3c"}]
        palette = _derive_palette(patterns)
        self.assertEqual(palette["primary"], "#e74c3c")


class TestHexToHsl(unittest.TestCase):
    """_hex_to_hsl conversion correctness."""

    def test_black(self):
        h, s, lum = _hex_to_hsl("#000000")
        self.assertAlmostEqual(h, 0.0)
        self.assertAlmostEqual(s, 0.0)
        self.assertAlmostEqual(lum, 0.0)

    def test_white(self):
        h, s, lum = _hex_to_hsl("#ffffff")
        self.assertAlmostEqual(lum, 100.0)

    def test_red(self):
        h, s, lum = _hex_to_hsl("#ff0000")
        self.assertAlmostEqual(h, 0.0)
        self.assertAlmostEqual(s, 100.0)
        self.assertAlmostEqual(lum, 50.0)


class TestHslToHex(unittest.TestCase):
    """_hsl_to_hex conversion correctness."""

    def test_black(self):
        self.assertEqual(_hsl_to_hex(0, 0, 0), "#000000")

    def test_white(self):
        self.assertEqual(_hsl_to_hex(0, 0, 100), "#ffffff")

    def test_red(self):
        self.assertEqual(_hsl_to_hex(0, 100, 50), "#ff0000")

    def test_green(self):
        self.assertEqual(_hsl_to_hex(120, 100, 50), "#00ff00")

    def test_blue(self):
        self.assertEqual(_hsl_to_hex(240, 100, 50), "#0000ff")


class TestHslRoundtrip(unittest.TestCase):
    """_hex_to_hsl -> _hsl_to_hex should reproduce the original color."""

    def _assert_roundtrip(self, hex_color):
        h, s, lum = _hex_to_hsl(hex_color)
        result = _hsl_to_hex(h, s, lum)
        self.assertEqual(result, hex_color, f"Roundtrip failed for {hex_color}")

    def test_red(self):
        self._assert_roundtrip("#ff0000")

    def test_blue(self):
        self._assert_roundtrip("#0000ff")

    def test_green(self):
        self._assert_roundtrip("#00ff00")

    def test_gray(self):
        self._assert_roundtrip("#808080")

    def test_dark_blue(self):
        self._assert_roundtrip("#1a3a5c")

    def test_bright_orange(self):
        self._assert_roundtrip("#ff8c00")

    def test_purple(self):
        self._assert_roundtrip("#9b59b6")

    def test_teal(self):
        self._assert_roundtrip("#1abc9c")


if __name__ == "__main__":
    unittest.main()
