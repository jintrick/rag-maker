import subprocess
import os
import shutil

# Define the path we are testing with
relative_path = ""
cache_dir = "cache"

# Clean up cache dir before test
if os.path.exists(cache_dir):
    # Recreate a clean empty cache directory
    shutil.rmtree(cache_dir)
os.makedirs(cache_dir)

# Run the script
try:
    print(f"Running test for empty string path...")
    subprocess.run(
        ["python", "tools/make_cache_dir.py", "--relative-path", relative_path],
        check=True, # Should succeed with exit code 0
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
except subprocess.CalledProcessError as e:
    print(f"Test failed: Script returned non-zero exit code {e.returncode}.")
    print(f"Stdout: {e.stdout}")
    print(f"Stderr: {e.stderr}")
    exit(1)

# Verify that the cache directory is still empty
assert len(os.listdir(cache_dir)) == 0, f"Assertion Failed: Directory '{cache_dir}' should be empty but is not."

print(f"Test passed: Script handled empty string correctly and created no directory.")

# Clean up after the test
shutil.rmtree(cache_dir)