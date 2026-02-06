import unittest
import subprocess
import tempfile
import json
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

class TestEnrichDiscovery(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.discovery_path = Path(self.test_dir.name) / "discovery.json"
        
        # Create a sample discovery.json
        self.sample_data = {
            "documents": [
                {"path": "page_0.md", "url": "http://example.com/0"},
                {"path": "page_1.md", "url": "http://example.com/1"}
            ],
            "metadata": {"source": "test"}
        }
        with open(self.discovery_path, 'w', encoding='utf-8') as f:
            json.dump(self.sample_data, f)

    def tearDown(self):
        self.test_dir.cleanup()

    def run_script(self, updates_json):
        result = subprocess.run(
            [sys.executable, "-m", "src.ragmaker.tools.enrich_discovery",
             "--discovery-path", str(self.discovery_path),
             "--updates", updates_json],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result

    def test_enrich_with_json_string(self):
        """Test enrichment using a JSON string."""
        updates = [
            {"path": "page_0.md", "title": "New Title 0", "summary": "New Summary 0"},
            {"path": "page_1.md", "title": "New Title 1", "summary": "New Summary 1"}
        ]
        updates_json = json.dumps(updates)

        result = self.run_script(updates_json)
        self.assertEqual(result.returncode, 0)

        with open(self.discovery_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data["documents"][0]["title"], "New Title 0")
        self.assertEqual(data["documents"][1]["summary"], "New Summary 1")

    def test_enrich_with_file(self):
        """Test enrichment using a JSON file path."""
        updates = [
            {"path": "page_0.md", "title": "File Title 0", "summary": "File Summary 0"}
        ]
        updates_file = Path(self.test_dir.name) / "updates.json"
        with open(updates_file, 'w', encoding='utf-8') as f:
            json.dump(updates, f)

        result = self.run_script(str(updates_file))
        self.assertEqual(result.returncode, 0)

        with open(self.discovery_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data["documents"][0]["title"], "File Title 0")

    def test_path_not_found_error(self):
        """Test that the script returns a warning (but code 0) if a path is not found."""
        updates = [
            {"path": "page_0.md", "title": "Title A", "summary": "Summary A"},
            {"path": "non_existent_page.md", "title": "Title C", "summary": "Summary C"}
        ]
        updates_json = json.dumps(updates)

        result = self.run_script(updates_json)

        self.assertEqual(result.returncode, 0)
        # Check that a warning was printed to stderr
        self.assertIn("warning", result.stderr)
        self.assertIn("non_existent_page.md", result.stderr)

    def test_invalid_json_format(self):
        """Test that the script fails with invalid JSON."""
        result = self.run_script("invalid json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid JSON format", result.stderr)

if __name__ == '__main__':
    unittest.main()