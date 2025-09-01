#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import shutil
from pathlib import Path

# Add the tools directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent / 'tools'))

from make_cache_dir import make_cache_dir

def test_case_4():
    """
    Test case 4: An empty path.
    """
    test_path = ""
    cache_dir = Path("cache")

    # Ensure the cache directory does not exist before the test
    if cache_dir.exists():
        # Get a list of contents to see if anything changes
        # This is safer than deleting the whole cache dir
        before_contents = list(cache_dir.iterdir())
    else:
        before_contents = []

    make_cache_dir(test_path)

    # Verification
    # The function should not create the cache directory or change its contents.
    if cache_dir.exists():
        after_contents = list(cache_dir.iterdir())
    else:
        after_contents = []

    if before_contents == after_contents:
        print(f"Test Case 4 Passed: No directory was created for an empty path.")
    else:
        print(f"Test Case 4 Failed: The cache directory contents changed for an empty path.")
        sys.exit(1)

if __name__ == "__main__":
    test_case_4()
