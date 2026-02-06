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
        """Set up temporary directories for each test."""
        self.base_dir = Path(tempfile.mkdtemp(prefix="html_test_base_"))
        self.input_dir = self.base_dir / "input"
        self.input_dir.mkdir()

    def tearDown(self):
        """Remove the temporary directories after each test."""
        shutil.rmtree(self.base_dir)

    def _run_script(self, discovery_path: Path, input_dir: Path):
        """
        Helper to run the script as a subprocess and capture the output.
        """
        command = [
            "ragmaker-html-to-markdown",
            "--discovery-path", str(discovery_path),
            "--input-dir", str(input_dir),
            "--verbose"
        ]

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        try:
            output_json = json.loads(process.stdout) if process.stdout else None
        except json.JSONDecodeError:
            output_json = None

        return output_json, process.stderr

    def test_successful_conversion(self):
        """
        Test that the script correctly converts HTML, updates the discovery JSON in stdout,
        and modifies files in the input directory.
        """
        # Arrange
        discovery_path = self.base_dir / "discovery.json"
        original_discovery_data = {
            "documents": [
                {"title": "Page 1", "url": "http://example.com/page1", "path": "page1.html"},
                {"title": "Page 2 - Not HTML", "url": "http://example.com/page2", "path": "page2.txt"}
            ]
        }
        discovery_path.write_text(json.dumps(original_discovery_data), encoding='utf-8')
        (self.input_dir / "page1.html").write_text("<html><body><h1>Title</h1><p>Content.</p></body></html>", encoding='utf-8')
        (self.input_dir / "page2.txt").write_text("This is a text file.", encoding='utf-8')

        # Act
        output_json, stderr = self._run_script(discovery_path=discovery_path, input_dir=self.input_dir)

        # Assert JSON output
        self.assertIsNotNone(output_json, f"Script produced non-JSON output. STDERR: {stderr}")
        self.assertEqual(len(output_json['documents']), 2)
        self.assertEqual(output_json['documents'][0]['path'], 'page1.md')
        self.assertEqual(output_json['documents'][1]['path'], 'page2.txt')

        # Assert file system changes
        self.assertFalse((self.input_dir / "page1.html").exists(), "Original HTML file should be deleted")
        self.assertTrue((self.input_dir / "page1.md").exists(), "Markdown file should be created")
        md_content = (self.input_dir / "page1.md").read_text(encoding='utf-8')
        self.assertIn("# Title", md_content, "Markdown content is incorrect")

        # Assert original discovery file is untouched
        untouched_discovery_data = json.loads(discovery_path.read_text(encoding='utf-8'))
        self.assertEqual(original_discovery_data, untouched_discovery_data, "Original discovery file should not be modified")

    def test_no_html_to_convert(self):
        """
        Test that the script correctly handles a discovery file with no HTML entries.
        """
        # Arrange
        discovery_path = self.base_dir / "discovery.json"
        original_discovery_data = {
            "documents": [{"title": "Doc 1", "path": "doc1.md"}]
        }
        discovery_path.write_text(json.dumps(original_discovery_data), encoding='utf-8')

        # Act
        output_json, stderr = self._run_script(discovery_path=discovery_path, input_dir=self.input_dir)

        # Assert
        self.assertIsNotNone(output_json, f"Script produced non-JSON output. STDERR: {stderr}")
        self.assertEqual(output_json, original_discovery_data, "Output JSON should be identical to input when no action is needed")

    def test_missing_html_file(self):
        """
        Test that the script logs an error for a missing file but still returns
        the discovery data with the missing path unchanged.
        """
        # Arrange
        discovery_path = self.base_dir / "discovery.json"
        original_discovery_data = {
            "documents": [
                {"title": "Convert Me", "path": "convert.html"},
                {"title": "Missing", "path": "missing.html"}
            ]
        }
        discovery_path.write_text(json.dumps(original_discovery_data), encoding='utf-8')
        (self.input_dir / "convert.html").write_text("<html><body><p>I exist.</p></body></html>", encoding='utf-8')

        # Act
        output_json, stderr = self._run_script(discovery_path=discovery_path, input_dir=self.input_dir)

        # Assert JSON output
        self.assertIsNotNone(output_json, f"Script produced non-JSON output. STDERR: {stderr}")
        self.assertEqual(len(output_json['documents']), 2)
        self.assertEqual(output_json['documents'][0]['path'], 'convert.md')
        self.assertEqual(output_json['documents'][1]['path'], 'missing.html', "Path for the missing file should remain unchanged")

        # Assert file system changes
        self.assertFalse((self.input_dir / "convert.html").exists(), "Existing HTML file should be deleted")
        self.assertTrue((self.input_dir / "convert.md").exists(), "Markdown file for existing HTML should be created")
        self.assertIn("HTML source file not found, skipping", stderr, "An error for the missing file should be logged to stderr")

if __name__ == '__main__':
    unittest.main()
