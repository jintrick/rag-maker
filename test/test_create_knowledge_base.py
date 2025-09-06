import unittest
import tempfile
import subprocess
import sys
import json
from pathlib import Path

class TestCreateKnowledgeBase(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for the test."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.kb_root = Path(self.test_dir.name) / "my_test_kb"

    def tearDown(self):
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def test_knowledge_base_creation(self):
        """
        Test that the create_knowledge_base tool correctly creates the
        directory structure and initial files.
        """
        script_path = Path(__file__).resolve().parent.parent / "tools" / "create_knowledge_base.py"

        # Execute the script
        result = subprocess.run(
            [sys.executable, str(script_path), "--kb-root", str(self.kb_root)],
            capture_output=True,
            text=True,
            check=False
        )

        # Print stdout/stderr for debugging
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        self.assertEqual(result.returncode, 0, "Script execution failed")
        self.assertIn("success", result.stdout, "Success message not in stdout")

        # 1. Verify .gemini/commands directory and ask.toml were created
        gemini_dir = self.kb_root / ".gemini"
        self.assertTrue(gemini_dir.exists(), ".gemini directory not created")
        self.assertTrue(gemini_dir.is_dir(), ".gemini is not a directory")
        # Check that only the necessary files were copied, not the whole directory.
        self.assertTrue((gemini_dir / "commands" / "ask.toml").exists(), "ask.toml not found in copied .gemini dir")
        self.assertFalse((gemini_dir / "commands" / "rag.md").exists(), "rag.md should not be copied to new KB")


        # 2. Verify cache directory was created
        cache_dir = self.kb_root / "cache"
        self.assertTrue(cache_dir.exists(), "cache directory not created")
        self.assertTrue(cache_dir.is_dir(), "cache is not a directory")

        # 3. Verify discovery.json was created and has correct content
        discovery_file = self.kb_root / "discovery.json"
        self.assertTrue(discovery_file.exists(), "discovery.json not created")
        self.assertTrue(discovery_file.is_file(), "discovery.json is not a file")

        with open(discovery_file, 'r', encoding='utf-8') as f:
            generated_data = json.load(f)

        # Load the root discovery.json to get the expected content for tools and handles.
        project_root = Path(__file__).resolve().parent.parent
        with open(project_root / "discovery.json", 'r', encoding='utf-8') as f:
            root_data = json.load(f)

        # a. Verify that the 'documents' list is empty.
        self.assertEqual(generated_data.get('documents'), [], "The 'documents' list should be empty.")

        # b. Verify that 'tools' and 'handles' are correctly copied from the root.
        self.assertEqual(generated_data.get('tools'), root_data.get('tools'), "The 'tools' list does not match the root discovery.json.")
        self.assertEqual(generated_data.get('handles'), root_data.get('handles'), "The 'handles' object does not match the root discovery.json.")

        # c. Verify that no extra project-specific keys were copied.
        # The set of keys in the new discovery.json should be exactly {'documents', 'handles', 'tools'}.
        self.assertEqual(
            set(generated_data.keys()),
            {'documents', 'handles', 'tools'},
            "The discovery.json contains unexpected top-level keys."
        )

if __name__ == '__main__':
    unittest.main()
