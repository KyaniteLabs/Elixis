"""Static landing page checks for GitHub Pages."""

from html.parser import HTMLParser
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class LandingParser(HTMLParser):
    """Collect landing page metadata without external parser dependencies."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.ids = set()
        self.links = []
        self.meta = {}
        self.json_ld = []
        self.in_json_ld = False
        self._script = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "link":
            self.links.append(attrs)
        if tag == "meta":
            key = attrs.get("name") or attrs.get("property")
            if key:
                self.meta[key] = attrs.get("content", "")
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.in_json_ld = True
            self._script = []

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_json_ld:
            self._script.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "script" and self.in_json_ld:
            self.json_ld.append("".join(self._script))
            self.in_json_ld = False


class TestDocsLanding(unittest.TestCase):
    def test_stale_working_names_are_not_exposed(self):
        checked_suffixes = {".md", ".txt", ".html", ".yaml", ".toml", ".py", ".yml"}
        for path in ROOT.rglob("*"):
            if ".git" in path.parts or not path.is_file() or path.suffix not in checked_suffixes:
                continue
            text = path.read_text(errors="ignore")
            stale_working_name = "soul" + "craft"
            prior_package_name = "fu" + "gax"
            self.assertNotIn(stale_working_name, text.lower(), str(path))
            self.assertNotIn(prior_package_name, text.lower(), str(path))

    def test_pages_landing_has_current_about_scope_and_metadata(self):
        html = (ROOT / "docs" / "index.html").read_text()
        legacy_scope = " ".join(("Glass", "Bead", "Game"))
        self.assertNotIn(legacy_scope, html)
        self.assertIn("SOUL.md is one compatibility lens, not the whole product", html)

        parser = LandingParser()
        parser.feed(html)

        self.assertIn("AI Pattern Synthesis", parser.title)
        self.assertIn("about", parser.ids)
        self.assertIn("outputs", parser.ids)
        self.assertIn("llms.txt", parser.meta["description"] + html)
        self.assertTrue(any(link.get("rel") == "canonical" for link in parser.links))

        data = json.loads(parser.json_ld[0])
        graph = data["@graph"]
        self.assertTrue(any("SoftwareApplication" in node.get("@type", []) for node in graph))
        self.assertTrue(any(node.get("@type") == "FAQPage" for node in graph))

    def test_pages_crawler_files_and_asset_are_valid(self):
        llms = (ROOT / "docs" / "llms.txt").read_text()
        self.assertIn("AI pattern synthesis engine", llms)
        self.assertIn("Landing page: https://kyanitelabs.github.io/Elixis/", llms)

        robots = (ROOT / "docs" / "robots.txt").read_text()
        self.assertIn("Sitemap: https://kyanitelabs.github.io/Elixis/sitemap.xml", robots)

        ET.fromstring((ROOT / "docs" / "sitemap.xml").read_text())
        ET.fromstring((ROOT / "docs" / "static" / "og-image.svg").read_text())


if __name__ == "__main__":
    unittest.main()
