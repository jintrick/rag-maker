import unittest
import subprocess
import tempfile
import shutil
from pathlib import Path
import os
import json
import sys

class TestFileSyncWithConversion(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory and fixtures for testing."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.source_dir = Path(self.test_dir.name) / "source"
        self.dest_dir = Path(self.test_dir.name) / "destination"

        # Create source directory and fixtures
        self.source_dir.mkdir()

        # Create a subdirectory to test recursive processing
        sub_dir = self.source_dir / "subdir"
        sub_dir.mkdir()

        # Create fixture files from the project's test/fixtures/file_sync directory
        fixture_source_dir = Path("test/fixtures/file_sync")

        # Ensure the fixture directory exists
        if not fixture_source_dir.is_dir():
            self.fail(f"Fixture directory not found at {fixture_source_dir}")

        for item in fixture_source_dir.iterdir():
            if item.is_file():
                shutil.copy(item, self.source_dir / item.name)

        # Create dummy docx/pdf with some text content, as they might not be in fixtures
        (self.source_dir / "document.docx").write_text("dummy docx content for testing")
        (self.source_dir / "presentation.pdf").write_text("dummy pdf content for testing")


    def tearDown(self):
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def test_sync_and_convert(self):
        """
        Test the full file sync and conversion process.
        """
        # Run the file_sync.py tool
        script_path = Path("src/ragmaker/tools/file_sync.py").resolve()

        # Add src to PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path("src").resolve()) + os.pathsep + env.get('PYTHONPATH', '')

        process = subprocess.run(
            [
                sys.executable, str(script_path),
                "--source-dir", str(self.source_dir),
                "--dest-dir", str(self.dest_dir)
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=env
        )

        # Check for errors
        if process.returncode != 0:
            print("FileSync STDERR:", process.stderr)
        self.assertEqual(process.returncode, 0, "file_sync.py script failed")

        # --- Assertions for file existence ---

        # 1. Converted files
        self.assertTrue((self.dest_dir / "sample.html").with_suffix('.md').exists(), "HTML file was not converted to .md")

        # Markitdown should handle these, so we expect them to be converted
        self.assertTrue((self.dest_dir / "document.docx").with_suffix('.md').exists(), "DOCX file was not converted to .md")
        self.assertTrue((self.dest_dir / "presentation.pdf").with_suffix('.md').exists(), "PDF file was not converted to .md")

        # 2. Copied files
        self.assertTrue((self.dest_dir / "readme.md").exists(), "Markdown file was not copied")
        self.assertTrue((self.dest_dir / "notes.txt").exists(), "Text file was not copied")

        # 3. Ignored files
        self.assertFalse((self.dest_dir / "image.jpg").exists(), "Unsupported .jpg file was copied")

        # --- Assertions for file content ---
        expected_md_content = "# Readme\n\nThis is a markdown file. It should be copied as is."
        expected_txt_content = "Just a plain text file.\nShould also be copied directly."
        self.assertEqual((self.dest_dir / "readme.md").read_text().strip(), expected_md_content.strip())
        self.assertEqual((self.dest_dir / "notes.txt").read_text().strip(), expected_txt_content.strip())

        # Check that converted HTML contains the core content
        converted_html_content = (self.dest_dir / "sample.html").with_suffix('.md').read_text()
        self.assertIn("Test HTML", converted_html_content)
        self.assertIn("Hello World", converted_html_content)

        # --- Assertions for JSON output ---
        try:
            output_json = json.loads(process.stdout)
        except json.JSONDecodeError:
            self.fail(f"STDOUT was not valid JSON. Output:\n{process.stdout}")

        self.assertEqual(output_json.get("metadata", {}).get("source"), "file_sync")

        documents = output_json.get("documents", [])
        paths = {doc["path"] for doc in documents}

        expected_paths = {
            "sample.md",
            "document.md",
            "presentation.md",
            "readme.md",
            "notes.txt",
        }

        self.assertSetEqual(paths, expected_paths)


if __name__ == '__main__':
    unittest.main()
