import unittest
import os
import sys
import shutil
import json
import io
import subprocess
from pathlib import Path

class TestHtmlToMarkdown(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for each test."""
        self.test_dir = Path("./temp_html_test_dir")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()

    def tearDown(self):
        """Remove the temporary directory after each test."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _run_script(self, target_dir):
        """Helper to run the script and capture output."""
        process = subprocess.run(
            [
                "ragmaker-html-to-markdown",
                "--target-dir", str(target_dir),
                "--log-level", "DEBUG" # Use DEBUG for more detailed error info
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        try:
            output = json.loads(process.stdout)
        except json.JSONDecodeError:
            print("Failed to decode JSON from stdout:")
            print("STDOUT:", process.stdout)
            print("STDERR:", process.stderr)
            self.fail(f"JSONDecodeError: {process.stderr}")
        return output, process.stderr

    def test_successful_conversion(self):
        """
        Test case for a successful conversion of a single HTML file.
        Input discovery.json uses the 'path' key for the HTML file.
        """
        # Arrange
        discovery_data = {
            "documents": [
                {
                    "title": "Page 1",
                    "url": "http://example.com/page1",
                    "path": "page1.html"
                },
                {
                    "title": "Page 2 - Not HTML",
                    "url": "http://example.com/page2",
                    "path": "page2.txt"
                }
            ]
        }
        with open(self.test_dir / "discovery.json", 'w', encoding='utf-8') as f:
            json.dump(discovery_data, f)
        with open(self.test_dir / "page1.html", 'w', encoding='utf-8') as f:
            f.write("<html><body><h1>Title</h1><p>Content.</p></body></html>")

        # Act
        output, stderr = self._run_script(self.test_dir)

        # Assert
        self.assertEqual(output['status'], 'success', f"STDERR: {stderr}")
        self.assertEqual(len(output['converted_files']), 1)
        self.assertEqual(len(output['errors']), 0)
        self.assertEqual(output['converted_files'][0]['original_path'], 'page1.html')
        self.assertEqual(output['converted_files'][0]['converted_path'], 'page1.md')

        self.assertFalse((self.test_dir / "page1.html").exists())
        self.assertTrue((self.test_dir / "page1.md").exists())
        md_content = (self.test_dir / "page1.md").read_text()
        self.assertIn("# Title", md_content)

        with open(self.test_dir / "discovery.json", 'r', encoding='utf-8') as f:
            updated_discovery = json.load(f)
        self.assertEqual(updated_discovery['documents'][0]['path'], 'page1.md')
        self.assertEqual(updated_discovery['documents'][1]['path'], 'page2.txt') # Unchanged

    def test_no_action_needed(self):
        """
        Test case where no HTML files are found in discovery.json.
        The script should report 'no_action_needed'.
        """
        # Arrange
        discovery_data = {
            "documents": [
                {"title": "Doc 1", "path": "doc1.md"},
                {"title": "Doc 2", "path": "doc2.pdf"}
            ]
        }
        with open(self.test_dir / "discovery.json", 'w', encoding='utf-8') as f:
            json.dump(discovery_data, f)

        # Act
        output, stderr = self._run_script(self.test_dir)

        # Assert
        self.assertEqual(output['status'], 'no_action_needed', f"STDERR: {stderr}")
        self.assertEqual(len(output['converted_files']), 0)
        self.assertEqual(len(output['errors']), 0)

        # Ensure discovery.json is semantically untouched by comparing the data
        with open(self.test_dir / "discovery.json", 'r', encoding='utf-8') as f:
            final_data = json.load(f)
        self.assertEqual(discovery_data, final_data)

    def test_partial_success_with_missing_file(self):
        """
        Test case where one file converts successfully and another is missing.
        Should report 'partial_success'.
        """
        # Arrange
        discovery_data = {
            "documents": [
                {"title": "Convert Me", "path": "convert.html"},
                {"title": "Missing", "path": "missing.html"}
            ]
        }
        with open(self.test_dir / "discovery.json", 'w', encoding='utf-8') as f:
            json.dump(discovery_data, f)
        with open(self.test_dir / "convert.html", 'w', encoding='utf-8') as f:
            f.write("<html><body><p>I exist.</p></body></html>")

        # Act
        output, stderr = self._run_script(self.test_dir)

        # Assert
        self.assertEqual(output['status'], 'partial_success', f"STDERR: {stderr}")
        self.assertEqual(len(output['converted_files']), 1)
        self.assertEqual(len(output['errors']), 1)
        self.assertEqual(output['converted_files'][0]['original_path'], 'convert.html')
        self.assertEqual(output['errors'][0]['document_title'], 'Missing')

        self.assertFalse((self.test_dir / "convert.html").exists())
        self.assertTrue((self.test_dir / "convert.md").exists())

        with open(self.test_dir / "discovery.json", 'r', encoding='utf-8') as f:
            updated_discovery = json.load(f)
        self.assertEqual(updated_discovery['documents'][0]['path'], 'convert.md')
        self.assertEqual(updated_discovery['documents'][1]['path'], 'missing.html') # Unchanged on error

if __name__ == '__main__':
    unittest.main()
