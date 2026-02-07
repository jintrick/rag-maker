import unittest
import subprocess
import sys
import json
import os
import shutil
import tempfile
from pathlib import Path

class TestPackageDependency(unittest.TestCase):
    def run_tool_isolated(self, tool_path, args=None):
        if args is None:
            args = []

        # Create a temporary directory to isolate the script
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            script_name = tool_path.name
            target_script_path = temp_path / script_name

            # Copy the script to the temporary directory
            shutil.copy2(tool_path, target_script_path)

            # Prepare the environment: remove PYTHONPATH
            env = os.environ.copy()
            if 'PYTHONPATH' in env:
                del env['PYTHONPATH']

            # Run the script from the temporary directory
            # Use -S to disable site-packages, ensuring strict isolation
            cmd = [sys.executable, "-S", str(target_script_path)] + args
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=temp_path)
            return result

    def test_tools_require_package(self):
        tools = [
            ("file_sync.py", ["--source-dir", ".", "--dest-dir", "."]),
            ("install_kb.py", ["--source", ".", "--target-kb-root", "."]),
            ("init_cache.py", []),
        ]

        base_tool_path = Path("src/ragmaker/tools").resolve()

        for tool_name, args in tools:
            with self.subTest(tool=tool_name):
                tool_path = base_tool_path / tool_name

                # Verify tool exists before running
                self.assertTrue(tool_path.exists(), f"Tool {tool_name} not found at {tool_path}")

                result = self.run_tool_isolated(tool_path, args)

                # Expect failure
                self.assertNotEqual(result.returncode, 0, f"Tool {tool_name} should fail without package")

                # Expect JSON output on stderr
                try:
                    error_data = json.loads(result.stderr)
                except json.JSONDecodeError:
                    self.fail(f"Tool {tool_name} stderr is not valid JSON: {result.stderr}")

                self.assertIsInstance(error_data, dict, "Error data should be a dictionary")
                self.assertEqual(error_data.get("status"), "error")
                # We check for generic error message because some tools might fail on other imports first
                # But ideally it should be "The 'ragmaker' package is required"
                # file_sync.py checks ragmaker first. install_kb.py checks ragmaker first. init_cache.py checks ragmaker first.
                self.assertIn("The 'ragmaker' package is required", error_data.get("message", ""))

if __name__ == '__main__':
    unittest.main()
