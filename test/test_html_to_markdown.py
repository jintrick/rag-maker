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
        """Set up a temporary directory with a discovery.json and dummy HTML files."""
        self.test_dir = Path("./temp_html_test_dir")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()

        self.discovery_data = {
            "documents": [
                {
                    "title": "Page 1",
                    "url": "http://example.com/page1",
                    "html_path": "page1.html",
                    "path": "page1.md"
                },
                {
                    "title": "Page 2",
                    "url": "http://example.com/page2",
                    "html_path": "page2_nonexistent.html",
                    "path": "page2.md"
                },
                {
                    "title": "Page 3 - Already Markdown",
                    "url": "http://example.com/page3",
                    "path": "page3.md"
                }
            ]
        }

        # Create discovery.json
        with open(self.test_dir / "discovery.json", 'w', encoding='utf-8') as f:
            json.dump(self.discovery_data, f, indent=2)

        # Create dummy HTML file for the valid entry
        with open(self.test_dir / "page1.html", 'w', encoding='utf-8') as f:
            f.write("<html><body><h1>Hello World</h1><p>This is page 1.</p></body></html>")

    def tearDown(self):
        """Remove the temporary directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_conversion_and_discovery_update(self):
        """
        Test that the script converts HTML, deletes the source,
        and updates discovery.json correctly.
        """
        # Act: Run the script's main function
        process = subprocess.run(
            [
                "ragmaker-html-to-markdown",
                "--target-dir", str(self.test_dir)
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
            self.fail("JSONDecodeError was raised")

        # Assert 1: Check the script's output report
        self.assertEqual(output['status'], 'partial_success')
        self.assertEqual(len(output['converted_files']), 1)
        self.assertEqual(len(output['errors']), 1)
        self.assertEqual(output['converted_files'][0]['original_path'], 'page1.html')
        self.assertEqual(output['errors'][0]['document_title'], 'Page 2')

        # Assert 2: Check the file system state
        self.assertFalse((self.test_dir / "page1.html").exists(), "Original HTML file should be deleted")
        self.assertTrue((self.test_dir / "page1.md").exists(), "Markdown file should be created")

        # Check content of created markdown file
        md_content = (self.test_dir / "page1.md").read_text(encoding='utf-8')
        self.assertIn("# Hello World", md_content)

        # Assert 3: Check the updated discovery.json
        with open(self.test_dir / "discovery.json", 'r', encoding='utf-8') as f:
            updated_discovery = json.load(f)

        doc1 = updated_discovery['documents'][0]
        doc2 = updated_discovery['documents'][1]
        doc3 = updated_discovery['documents'][2]

        self.assertNotIn("html_path", doc1, "html_path should be removed from converted entry")
        self.assertEqual(doc1['path'], 'page1.md')

        # Ensure the entry that caused an error was not modified
        self.assertIn("html_path", doc2)
        # Ensure the entry that was skipped was not modified
        self.assertNotIn("html_path", doc3)


if __name__ == '__main__':
    unittest.main()
