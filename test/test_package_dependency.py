import unittest
import subprocess
import sys
import json
import os
from pathlib import Path

class TestPackageDependency(unittest.TestCase):
    def run_tool_without_package(self, tool_path, args=None):
        if args is None:
            args = []

        # Ensure PYTHONPATH does NOT include src
        env = os.environ.copy()
        if 'PYTHONPATH' in env:
            del env['PYTHONPATH']

        cmd = [sys.executable, str(tool_path)] + args
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return result

    def test_file_sync_requires_package(self):
        tool_path = Path("src/ragmaker/tools/file_sync.py").resolve()
        result = self.run_tool_without_package(tool_path, ["--source-dir", ".", "--dest-dir", "."])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("The 'ragmaker' package is required", result.stderr)

    def test_install_kb_requires_package(self):
        tool_path = Path("src/ragmaker/tools/install_kb.py").resolve()
        result = self.run_tool_without_package(tool_path, ["--source", ".", "--target-kb-root", "."])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("The 'ragmaker' package is required", result.stderr)

    def test_init_cache_requires_package(self):
        tool_path = Path("src/ragmaker/tools/init_cache.py").resolve()
        result = self.run_tool_without_package(tool_path)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("The 'ragmaker' package is required", result.stderr)

if __name__ == '__main__':
    unittest.main()
