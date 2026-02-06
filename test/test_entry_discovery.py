import unittest
import json
import tempfile
import subprocess
import sys
import os
from pathlib import Path

# Ensure src is in path for imports if needed, but we run subprocess with PYTHONPATH
SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))

class TestEntryDiscovery(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for test artifacts."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)

    def tearDown(self):
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def test_creates_initial_discovery_file(self):
        """
        Test that a new catalog.json is created with the correct 'unknowns' entry.
        """
        discovery_file_path = self.test_path / "catalog.json"
        source_uri = "https://example.com/my-knowledge-source"

        self.assertFalse(discovery_file_path.exists()) # Ensure it doesn't exist initially

        args = [
            sys.executable, '-m', 'ragmaker.tools.entry_discovery',
            '--kb-root', str(self.test_path),
            '--uri', source_uri
        ]

        env = {**os.environ, "PYTHONPATH": SRC_PATH}
        result = subprocess.run(args, capture_output=True, text=True, check=False, encoding='utf-8', env=env)

        # For debugging
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        self.assertEqual(result.returncode, 0, "Script execution failed")
        self.assertTrue(discovery_file_path.exists(), "catalog.json was not created")

        # Verify the content of the created file
        with open(discovery_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        expected_data = {
            "source_url": source_uri,
            "unknowns": [
                {"uri": source_uri}
            ]
        }
        self.assertEqual(data, expected_data, "The content of catalog.json is incorrect")

        # Verify the success message from stdout
        output_json = json.loads(result.stdout)
        self.assertEqual(output_json['status'], 'success')
        self.assertEqual(output_json['catalog_file'], str(discovery_file_path.resolve()))

    def test_creates_discovery_with_metadata(self):
        """
        Test that catalog.json is created with top-level metadata.
        """
        # Note: entry_discovery creates "catalog.json" in kb-root.
        # We can't specify a custom filename like "catalog_meta.json" anymore via CLI easily
        # unless we use a subdir or if logic allows.
        # But for test, we can use a subdirectory "meta_test".
        meta_test_dir = self.test_path / "meta_test"
        meta_test_dir.mkdir()
        discovery_file_path = meta_test_dir / "catalog.json"

        source_uri = "https://github.com/user/repo"
        title = "My Knowledge Base"
        summary = "A test summary"
        src_type = "github"

        args = [
            sys.executable, '-m', 'ragmaker.tools.entry_discovery',
            '--kb-root', str(meta_test_dir),
            '--uri', source_uri,
            '--title', title,
            '--summary', summary,
            '--src-type', src_type
        ]

        env = {**os.environ, "PYTHONPATH": SRC_PATH}
        result = subprocess.run(args, capture_output=True, text=True, check=True, encoding='utf-8', env=env)

        with open(discovery_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertEqual(data['title'], title)
        self.assertEqual(data['summary'], summary)
        self.assertEqual(data['src_type'], src_type)
        self.assertEqual(data['source_url'], source_uri)
        self.assertEqual(data['unknowns'][0]['uri'], source_uri)

    def test_missing_required_arguments(self):
        """Test that the script fails if required arguments are missing."""
        env = {**os.environ, "PYTHONPATH": SRC_PATH}

        # Missing --uri
        args_missing_uri = [
            sys.executable, '-m', 'ragmaker.tools.entry_discovery',
            '--kb-root', str(self.test_path),
        ]
        result = subprocess.run(args_missing_uri, capture_output=True, text=True, check=False, encoding='utf-8', env=env)
        self.assertNotEqual(result.returncode, 0, "Script should fail with missing --uri")
        self.assertTrue(
            "the following arguments are required: --uri" in result.stderr or
            "Either --uri or --source-url is required" in result.stdout,
            f"Expected error message not found. Stderr: {result.stderr}, Stdout: {result.stdout}"
        )

        # Missing --kb-root
        args_missing_path = [
            sys.executable, '-m', 'ragmaker.tools.entry_discovery',
            '--uri', "some-uri",
        ]
        result = subprocess.run(args_missing_path, capture_output=True, text=True, check=False, encoding='utf-8', env=env)
        self.assertNotEqual(result.returncode, 0, "Script should fail with missing --kb-root")
        self.assertIn("the following arguments are required: --kb-root", result.stderr)

if __name__ == '__main__':
    unittest.main()
