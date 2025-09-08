# -*- coding: utf-8 -*-
"""
test_enrich_discovery.py - Unit tests for the enrich_discovery tool.
"""

import unittest
import os
import json
import subprocess
import tempfile

class TestEnrichDiscovery(unittest.TestCase):
    def setUp(self):
        """Set up a temporary directory and a sample discovery.json file."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.discovery_path = os.path.join(self.test_dir.name, 'discovery.json')

        self.sample_data = {
            "documents": [
                {
                    "path": "page_0.md",
                    "title": "",
                    "summary": ""
                },
                {
                    "path": "page_1.md",
                    "title": "Old Title",
                    "summary": "Old Summary"
                },
                {
                    "path": "page_2.md",
                    "title": "Untouched",
                    "summary": "This should not be changed."
                }
            ]
        }

        with open(self.discovery_path, 'w', encoding='utf-8') as f:
            json.dump(self.sample_data, f, indent=2)

    def tearDown(self):
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def run_script(self, updates_json):
        """Helper function to run the enrich_discovery script."""
        script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'ragmaker', 'tools', 'enrich_discovery.py')

        result = subprocess.run(
            [
                'python',
                script_path,
                '--discovery-path', self.discovery_path,
                '--updates', updates_json
            ],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result

    def test_successful_update(self):
        """Test that the script correctly updates titles and summaries."""
        updates = [
            {"path": "page_0.md", "title": "New Title A", "summary": "New Summary A"},
            {"path": "page_1.md", "title": "New Title B", "summary": "New Summary B"}
        ]
        updates_json = json.dumps(updates)

        result = self.run_script(updates_json)

        self.assertEqual(result.returncode, 0, f"Script failed with stderr: {result.stderr}")
        self.assertIn("success", result.stdout)

        with open(self.discovery_path, 'r', encoding='utf-8') as f:
            updated_data = json.load(f)

        doc0 = updated_data['documents'][0]
        self.assertEqual(doc0['title'], "New Title A")
        self.assertEqual(doc0['summary'], "New Summary A")

        doc1 = updated_data['documents'][1]
        self.assertEqual(doc1['title'], "New Title B")
        self.assertEqual(doc1['summary'], "New Summary B")

        doc2 = updated_data['documents'][2]
        self.assertEqual(doc2['title'], "Untouched")
        self.assertEqual(doc2['summary'], "This should not be changed.")

    def test_path_not_found_error(self):
        """Test that the script returns an error if a path is not found."""
        updates = [
            {"path": "page_0.md", "title": "Title A", "summary": "Summary A"},
            {"path": "non_existent_page.md", "title": "Title C", "summary": "Summary C"}
        ]
        updates_json = json.dumps(updates)

        result = self.run_script(updates_json)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error", result.stderr)
        self.assertIn("non_existent_page.md", result.stderr)
        self.assertIn("not found", result.stderr)

        # Verify that no changes were made to the original file
        with open(self.discovery_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        self.assertEqual(self.sample_data, original_data)


if __name__ == '__main__':
    unittest.main()
