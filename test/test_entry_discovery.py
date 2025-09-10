import unittest
import json
import tempfile
import subprocess
from pathlib import Path

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
        Test that a new discovery.json is created with the correct 'unknowns' entry.
        """
        discovery_file_path = self.test_path / "discovery.json"
        source_uri = "https://example.com/my-knowledge-source"

        self.assertFalse(discovery_file_path.exists()) # Ensure it doesn't exist initially

        args = [
            'ragmaker-entry-discovery',
            '--discovery-path', str(discovery_file_path),
            '--uri', source_uri
        ]

        result = subprocess.run(args, capture_output=True, text=True, check=False, encoding='utf-8')

        # For debugging
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        self.assertEqual(result.returncode, 0, "Script execution failed")
        self.assertTrue(discovery_file_path.exists(), "discovery.json was not created")

        # Verify the content of the created file
        with open(discovery_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        expected_data = {
            "unknowns": [
                {"uri": source_uri}
            ]
        }
        self.assertEqual(data, expected_data, "The content of discovery.json is incorrect")

        # Verify the success message from stdout
        output_json = json.loads(result.stdout)
        self.assertEqual(output_json['status'], 'success')
        self.assertEqual(output_json['discovery_file'], str(discovery_file_path.resolve()))

    def test_missing_required_arguments(self):
        """Test that the script fails if required arguments are missing."""
        # Missing --uri
        args_missing_uri = [
            'ragmaker-entry-discovery',
            '--discovery-path', str(self.test_path / "discovery.json"),
        ]
        result = subprocess.run(args_missing_uri, capture_output=True, text=True, check=False, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0, "Script should fail with missing --uri")
        self.assertIn("the following arguments are required: --uri", result.stderr)

        # Missing --discovery-path
        args_missing_path = [
            'ragmaker-entry-discovery',
            '--uri', "some-uri",
        ]
        result = subprocess.run(args_missing_path, capture_output=True, text=True, check=False, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0, "Script should fail with missing --discovery-path")
        self.assertIn("the following arguments are required: --discovery-path", result.stderr)

if __name__ == '__main__':
    unittest.main()
