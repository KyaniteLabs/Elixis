"""Tests for entity extraction pipeline."""

import unittest
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soulcraft.entities import (
    _parse_line_entity,
    _heuristic_extract,
    extract_entities,
)


class TestParseLineEntity(unittest.TestCase):
    """Test line-by-line entity parsing."""

    def test_simple_name(self):
        """Parse a simple name."""
        result = _parse_line_entity("Kyan")
        self.assertIsNotNone(result)
        self.assertEqual(result["canonical"], "Kyan")
        self.assertEqual(result["type"], "concept")

    def test_name_with_source_paren(self):
        """Parse name with source in parentheses."""
        result = _parse_line_entity("Arthur Dent (Hitchhiker's Guide)")
        self.assertIsNotNone(result)
        self.assertEqual(result["canonical"], "Arthur Dent")
        self.assertEqual(result["source"], "Hitchhiker's Guide")
        self.assertEqual(result["type"], "character")

    def test_name_with_source_from(self):
        """Parse name with 'from' source."""
        result = _parse_line_entity("Frodo from Lord of the Rings")
        self.assertIsNotNone(result)
        self.assertEqual(result["canonical"], "Frodo")
        self.assertEqual(result["source"], "Lord of the Rings")

    def test_name_with_source_dash(self):
        """Parse name with dash separator."""
        result = _parse_line_entity("Sherlock Holmes - detective stories")
        self.assertIsNotNone(result)
        self.assertEqual(result["canonical"], "Sherlock Holmes")
        self.assertEqual(result["source"], "detective stories")

    def test_name_with_source_slash(self):
        """Parse name with slash separator."""
        result = _parse_line_entity("Batman / DC Comics")
        self.assertIsNotNone(result)
        self.assertEqual(result["canonical"], "Batman")
        self.assertEqual(result["source"], "DC Comics")

    def test_quoted_name(self):
        """Parse quoted name."""
        result = _parse_line_entity('"The Joker"')
        self.assertIsNotNone(result)
        self.assertEqual(result["canonical"], "The Joker")

    def test_empty_line(self):
        """Empty line returns None."""
        result = _parse_line_entity("")
        self.assertIsNone(result)

    def test_whitespace_only(self):
        """Whitespace-only line returns None."""
        result = _parse_line_entity("   ")
        self.assertIsNone(result)

    def test_too_short(self):
        """Single character returns None."""
        result = _parse_line_entity("A")
        self.assertIsNone(result)


class TestHeuristicExtract(unittest.TestCase):
    """Test heuristic entity extraction."""

    def test_multi_line_input(self):
        """Extract entities from multi-line text."""
        text = """Kyan - AI builder
Arthur Dent (Hitchhiker's Guide)
The concept of emergence
"""
        entities = _heuristic_extract(text)
        self.assertEqual(len(entities), 3)

        names = [e["canonical"] for e in entities]
        self.assertIn("Kyan", names)
        self.assertIn("Arthur Dent", names)
        self.assertIn("The concept of emergence", names)

    def test_capitalized_phrases_fallback(self):
        """Extract capitalized phrases when no line entities."""
        # Use a text where capitalized words stand alone
        text = "Sherlock Holmes. Hercule Poirot. detectives."
        entities = _heuristic_extract(text)
        # Should find some capitalized entities
        names = [e["canonical"] for e in entities]
        # At least one capitalized name should be found
        self.assertGreater(len(names), 0)
        # Check that common starters are filtered
        for name in names:
            self.assertNotIn(name.lower(), ["the", "this", "that", "i", "we"])

    def test_excludes_common_starters(self):
        """Common sentence starters are excluded."""
        text = "The quick brown fox jumps over the lazy dog."
        entities = _heuristic_extract(text)
        # "The" should not be extracted
        for e in entities:
            self.assertNotEqual(e["canonical"].lower(), "the")


class TestExtractEntities(unittest.TestCase):
    """Test main entity extraction pipeline."""

    def test_empty_input(self):
        """Empty input returns empty list."""
        result = extract_entities("")
        self.assertEqual(result, [])

    def test_whitespace_input(self):
        """Whitespace-only input returns empty list."""
        result = extract_entities("   \n\t  ")
        self.assertEqual(result, [])

    def test_basic_extraction(self):
        """Basic entity extraction works."""
        text = """Kyan builds AI
The concept of flow states
Miyamoto Musashi - Book of Five Rings"""
        entities = extract_entities(text)
        # Should extract something (LLM or heuristic)
        self.assertGreater(len(entities), 0)


class TestEntityStructure(unittest.TestCase):
    """Test that extracted entities have required fields."""

    def test_entity_has_required_fields(self):
        """All entities must have required fields."""
        text = "Test Entity (Source Work)"
        entities = _heuristic_extract(text)

        for entity in entities:
            self.assertIn("original", entity)
            self.assertIn("canonical", entity)
            self.assertIn("source", entity)
            self.assertIn("type", entity)
            self.assertIn("themes", entity)
            self.assertIn("traits", entity)
            self.assertIn("confidence", entity)


if __name__ == "__main__":
    unittest.main()
