#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

# Add the tools directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent / 'tools'))

from make_cache_dir import make_cache_dir

def test_case_5():
    """
    Test case 5: A path with special characters.
    """
    test_path = "!@#$%^&()"
    make_cache_dir(test_path)

    # Verification
    cache_dir = Path("cache") / test_path
    if cache_dir.exists() and cache_dir.is_dir():
        print(f"Test Case 5 Passed: Directory '{cache_dir}' created successfully.")
        # Clean up
        try:
            os.rmdir(cache_dir)
        except OSError as e:
            # Handle cases where the shell might have issues with special characters in rmdir
            import subprocess
            subprocess.run(['rm', '-rf', str(cache_dir)])
            print(f"Cleaned up with rm -rf due to {e}")

    else:
        print(f"Test Case 5 Failed: Directory '{cache_dir}' was not created.")
        sys.exit(1)

if __name__ == "__main__":
    test_case_5()
