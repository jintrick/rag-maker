import unittest
import json
import tempfile
import subprocess
from pathlib import Path

class TestEntryDiscovery(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory to act as a knowledge base root."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.kb_root = Path(self.test_dir.name)
        # The tool itself should create the cache directory if it doesn't exist
        # self.cache_dir = self.kb_root / "cache"
        # self.cache_dir.mkdir()

    def tearDown(self):
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def test_create_new_discovery_file(self):
        """
        Test that a new discovery.json is created in the cache directory
        with the correct header and an empty documents list.
        """
        discovery_file_path = self.kb_root / "cache" / "discovery.json"
        self.assertFalse(discovery_file_path.exists()) # Ensure it doesn't exist initially

        args = [
            'ragmaker-entry-discovery',
            '--kb-root', str(self.kb_root),
            '--title', 'Test KB',
            '--summary', 'A test knowledge base.',
            '--src-type', 'web',
            '--source-url', 'https://example.com'
        ]

        result = subprocess.run(args, capture_output=True, text=True, check=False, encoding='utf-8')

        # For debugging
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        self.assertEqual(result.returncode, 0, "Script execution failed")
        self.assertTrue(discovery_file_path.exists(), "discovery.json was not created in the cache directory")

        with open(discovery_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn("header", data)
        self.assertIn("documents", data)
        self.assertEqual(len(data["documents"]), 0) # Should have an empty documents list
        self.assertEqual(data["header"]["title"], "Test KB")
        self.assertEqual(data["header"]["source_url"], "https://example.com")

        output_json = json.loads(result.stdout)
        self.assertEqual(output_json['status'], 'success')
        self.assertEqual(output_json['header']['summary'], 'A test knowledge base.')

    def test_update_existing_discovery_header(self):
        """
        Test that the header of an existing discovery.json is updated
        without affecting other keys (like 'documents').
        """
        cache_dir = self.kb_root / "cache"
        cache_dir.mkdir()
        discovery_file_path = cache_dir / "discovery.json"

        # Create a pre-existing discovery.json with some content
        initial_data = {
            "header": {
                "title": "Old Title",
                "summary": "Old Summary",
                "src_type": "local",
                "source_url": "./old/path",
                "fetched_at": "2023-01-01T00:00:00Z"
            },
            "documents": [
                {"path": "doc1.md", "title": "Document 1"}
            ]
        }
        with open(discovery_file_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2)

        args = [
            'ragmaker-entry-discovery',
            '--kb-root', str(self.kb_root),
            '--title', 'New Title',
            '--summary', 'New Summary',
            '--src-type', 'github',
            '--source-url', 'https://github.com/user/repo.git'
        ]

        result = subprocess.run(args, capture_output=True, text=True, check=False, encoding='utf-8')

        self.assertEqual(result.returncode, 0, "Script execution failed")

        with open(discovery_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check that the header is updated
        self.assertEqual(data["header"]["title"], "New Title")
        self.assertEqual(data["header"]["src_type"], "github")
        self.assertNotEqual(data["header"]["fetched_at"], "2023-01-01T00:00:00Z")

        # Check that other keys are untouched
        self.assertIn("documents", data)
        self.assertEqual(len(data["documents"]), 1)
        self.assertEqual(data["documents"][0]["title"], "Document 1")

    def test_missing_required_arguments(self):
        """Test that the script fails if required arguments are missing."""
        args = [
            'ragmaker-entry-discovery',
            '--kb-root', str(self.kb_root),
            # Missing --title, --summary, etc.
        ]

        result = subprocess.run(args, capture_output=True, text=True, check=False, encoding='utf-8')

        self.assertNotEqual(result.returncode, 0, "Script should fail with missing arguments")
        self.assertIn("the following arguments are required", result.stderr)

if __name__ == '__main__':
    unittest.main()
