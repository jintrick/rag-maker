import unittest
import os
import sys
import shutil
import json
import subprocess
import tempfile
from pathlib import Path

class TestHtmlToMarkdown(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for each test."""
        # Create a unique temporary directory for the test run
        self.test_dir = Path(tempfile.mkdtemp(prefix="html_test_"))

    def tearDown(self):
        """Remove the temporary directory after each test."""
        shutil.rmtree(self.test_dir)

    def _run_script(self, target_dir):
        """
        Helper to run the script as a subprocess and capture the output.
        """
        command = [
            "ragmaker-html-to-markdown",
            "--target-dir", str(target_dir),
            "--verbose"
        ]

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        # It's better to return the parsed JSON and the raw stderr
        # for easier debugging in the tests.
        try:
            output_json = json.loads(process.stdout)
        except json.JSONDecodeError:
            output_json = None # Or handle as a test failure right away

        return output_json, process.stderr

    def test_successful_conversion(self):
        """
        Test case for a successful conversion of a single HTML file.
        """
        # Arrange
        discovery_data = {
            "documents": [
                {"title": "Page 1", "url": "http://example.com/page1", "path": "page1.html"},
                {"title": "Page 2 - Not HTML", "url": "http://example.com/page2", "path": "page2.txt"}
            ]
        }
        (self.test_dir / "discovery.json").write_text(json.dumps(discovery_data), encoding='utf-8')
        (self.test_dir / "page1.html").write_text("<html><body><h1>Title</h1><p>Content.</p></body></html>", encoding='utf-8')

        # Act
        output, stderr = self._run_script(self.test_dir)

        # Assert
        self.assertIsNotNone(output, f"Script produced non-JSON output. STDERR: {stderr}")
        self.assertEqual(output['status'], 'success', f"STDERR: {stderr}")
        self.assertEqual(len(output['converted_files']), 1)
        self.assertEqual(len(output['errors']), 0)
        self.assertEqual(output['converted_files'][0]['original_path'], 'page1.html')
        self.assertEqual(output['converted_files'][0]['converted_path'], 'page1.md')

        self.assertFalse((self.test_dir / "page1.html").exists())
        self.assertTrue((self.test_dir / "page1.md").exists())
        md_content = (self.test_dir / "page1.md").read_text(encoding='utf-8')
        self.assertIn("# Title", md_content)

        updated_discovery = json.loads((self.test_dir / "discovery.json").read_text(encoding='utf-8'))
        self.assertEqual(updated_discovery['documents'][0]['path'], 'page1.md')
        self.assertEqual(updated_discovery['documents'][1]['path'], 'page2.txt')

    def test_no_action_needed(self):
        """
        Test case where no HTML files are found in discovery.json.
        """
        # Arrange
        discovery_data = {
            "documents": [{"title": "Doc 1", "path": "doc1.md"}]
        }
        (self.test_dir / "discovery.json").write_text(json.dumps(discovery_data), encoding='utf-8')

        # Act
        output, stderr = self._run_script(self.test_dir)

        # Assert
        self.assertIsNotNone(output, f"Script produced non-JSON output. STDERR: {stderr}")
        self.assertEqual(output['status'], 'no_action_needed', f"STDERR: {stderr}")
        self.assertEqual(len(output['converted_files']), 0)
        self.assertEqual(len(output['errors']), 0)

        final_data = json.loads((self.test_dir / "discovery.json").read_text(encoding='utf-8'))
        self.assertEqual(discovery_data, final_data)

    def test_partial_success_with_missing_file(self):
        """
        Test case where one file converts successfully and another is missing.
        """
        # Arrange
        discovery_data = {
            "documents": [
                {"title": "Convert Me", "path": "convert.html"},
                {"title": "Missing", "path": "missing.html"}
            ]
        }
        (self.test_dir / "discovery.json").write_text(json.dumps(discovery_data), encoding='utf-8')
        (self.test_dir / "convert.html").write_text("<html><body><p>I exist.</p></body></html>", encoding='utf-8')

        # Act
        output, stderr = self._run_script(self.test_dir)

        # Assert
        self.assertIsNotNone(output, f"Script produced non-JSON output. STDERR: {stderr}")
        self.assertEqual(output['status'], 'partial_success', f"STDERR: {stderr}")
        self.assertEqual(len(output['converted_files']), 1)
        self.assertEqual(len(output['errors']), 1)
        self.assertEqual(output['converted_files'][0]['original_path'], 'convert.html')
        self.assertEqual(output['errors'][0]['document_title'], 'Missing')

        self.assertFalse((self.test_dir / "convert.html").exists())
        self.assertTrue((self.test_dir / "convert.md").exists())

        updated_discovery = json.loads((self.test_dir / "discovery.json").read_text(encoding='utf-8'))
        self.assertEqual(updated_discovery['documents'][0]['path'], 'convert.md')
        self.assertEqual(updated_discovery['documents'][1]['path'], 'missing.html')

if __name__ == '__main__':
    unittest.main()
