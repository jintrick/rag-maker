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
        directory structure.
        """
        # Execute the script
        result = subprocess.run(
            ["ragmaker-create-knowledge-base", "--kb-root", str(self.kb_root)],
            capture_output=True,
            text=True,
            check=False
        )

        # Print stdout/stderr for debugging
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        self.assertEqual(result.returncode, 0, "Script execution failed")
        self.assertIn("success", result.stdout, "Success message not in stdout")

        # 1. Verify .gemini/commands directory was created
        gemini_dir = self.kb_root / ".gemini"
        self.assertTrue(gemini_dir.exists(), ".gemini directory not created")
        self.assertTrue((gemini_dir / "commands").exists(), ".gemini/commands directory not created")

        # 2. Verify catalog.json and discovery.json were NOT created
        self.assertFalse((self.kb_root / "catalog.json").exists(), "catalog.json should NOT be created")
        self.assertFalse((self.kb_root / "discovery.json").exists(), "discovery.json should NOT be created")

if __name__ == '__main__':
    unittest.main()
