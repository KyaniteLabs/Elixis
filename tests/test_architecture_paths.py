"""The architecture inventory must identify real, owned repository paths."""
import fnmatch
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArchitecturePathsTests(unittest.TestCase):
    def test_inventory_matches_source(self):
        inventory = ROOT / 'qa/architecture-paths.json'
        self.assertTrue(inventory.is_file(), 'missing architecture inventory')
        data = json.loads(inventory.read_text())
        self.assertEqual(set(data), {'schema_version', 'repo', 'paths'})
        self.assertEqual(data['schema_version'], 1)
        self.assertEqual(data['repo'], 'github.com/KyaniteLabs/Elixis')
        self.assertTrue(data['paths'])
        files = subprocess.check_output(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
            cwd=ROOT, text=True).splitlines()
        covered = set()
        for entry in data['paths']:
            self.assertEqual(set(entry), {'pattern', 'layer', 'owner'})
            self.assertIn(entry['owner'], {'engineering', 'product'})
            self.assertTrue(entry['layer'].strip())
            pattern = entry['pattern']
            self.assertFalse(pattern.startswith('/'))
            self.assertNotIn('..', pattern.split('/'))
            matches = {name for name in files if fnmatch.fnmatchcase(name, pattern)}
            self.assertTrue(matches, f'empty pattern: {pattern}')
            covered.update(matches)
        for path in files:
            with self.subTest(path=path):
                self.assertIn(path, covered, 'unowned tracked/source path')
