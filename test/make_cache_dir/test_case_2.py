#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

# Add the tools directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent / 'tools'))

from make_cache_dir import make_cache_dir

def test_case_2():
    """
    Test case 2: An existing relative path.
    """
    test_path = "existing_dir"
    cache_dir = Path("cache") / test_path

    # Create the directory first
    cache_dir.mkdir(parents=True, exist_ok=True)

    make_cache_dir(test_path)

    # Verification
    if cache_dir.exists() and cache_dir.is_dir():
        print(f"Test Case 2 Passed: Directory '{cache_dir}' still exists.")
        # Clean up
        os.rmdir(cache_dir)
    else:
        print(f"Test Case 2 Failed: Directory '{cache_dir}' was removed or not found.")
        sys.exit(1)

if __name__ == "__main__":
    test_case_2()
