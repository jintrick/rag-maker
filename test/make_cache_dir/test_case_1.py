#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

# Add the tools directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent / 'tools'))

from make_cache_dir import make_cache_dir

def test_case_1():
    """
    Test case 1: A relative path with spaces.
    """
    test_path = "test dir with spaces"
    make_cache_dir(test_path)

    # Verification
    cache_dir = Path("cache") / test_path
    if cache_dir.exists() and cache_dir.is_dir():
        print(f"Test Case 1 Passed: Directory '{cache_dir}' created successfully.")
        # Clean up
        os.rmdir(cache_dir)
    else:
        print(f"Test Case 1 Failed: Directory '{cache_dir}' was not created.")
        sys.exit(1)

if __name__ == "__main__":
    test_case_1()
