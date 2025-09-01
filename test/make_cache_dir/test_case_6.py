import subprocess
import os
import shutil

def run_test(test_name, input_path, expected_dir_name):
    """A helper function to run a single test case."""
    print(f"--- Running test: {test_name} ---")
    
    if not expected_dir_name:
        print("Testing for no-op. No directory should be created.")
        cache_dir = "cache"
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        initial_contents = set(os.listdir(cache_dir))
    else:
        test_dir = os.path.join("cache", expected_dir_name)
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    try:
        subprocess.run(
            ["python", "tools/make_cache_dir.py", "--relative-path", input_path],
            check=True, capture_output=True, text=True, encoding='utf-8'
        )
    except subprocess.CalledProcessError as e:
        print(f"Test failed for input '{input_path}'. Exit code: {e.returncode}.")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        exit(1)

    if not expected_dir_name:
        final_contents = set(os.listdir("cache"))
        assert final_contents == initial_contents, "Assertion Failed: Directory should not have been created."
        print("Test passed: No directory was created, as expected.")
    else:
        assert os.path.isdir(test_dir), f"Assertion Failed: Directory '{test_dir}' was not created."
        print(f"Test passed: Directory '{expected_dir_name}' was created successfully.")
        shutil.rmtree(test_dir)
    
    print(f"--- Test '{test_name}' finished ---")
    print()


if __name__ == "__main__":
    cache_base = "cache"
    if not os.path.exists(cache_base):
        os.makedirs(cache_base)

    # Case 1: Multiple wrapping quotes -> Should become 'path'
    run_test("Multiple wrapping quotes", '""path""', 'path')
    
    # Case 2: Quotes with surrounding spaces -> Should become 'path'
    run_test("Quotes with surrounding spaces", ' \"path\" ', "path")

    # Case 3: Just quotes and spaces -> Should become empty
    run_test("Just quotes and spaces", ' \" \" ', "")
    
    print("\nAll stripping logic tests passed successfully!")
