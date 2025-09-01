import subprocess
import os
import shutil

# Define the path for the test directory
# Note: The script creates this inside the 'cache' directory
test_dir = os.path.join("cache", "test_case_1_dir")

# Clean up before the test
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)

# Run the script with the new argument format and check for success
try:
    print("Running test for test_case_1_dir...")
    subprocess.run(
        ["python", "tools/make_cache_dir.py", "--relative-path", "test_case_1_dir"],
        check=True,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
except subprocess.CalledProcessError as e:
    print(f"Test failed: Script returned non-zero exit code {e.returncode}.")
    print(f"Stdout: {e.stdout}")
    print(f"Stderr: {e.stderr}")
    exit(1)


# Verify that the directory was created
assert os.path.isdir(test_dir), f"Assertion Failed: Directory '{test_dir}' was not created."

print(f"Test passed: Directory '{test_dir}' was created successfully.")

# Clean up after the test
shutil.rmtree(os.path.join("cache", "test_case_1_dir").split(os.path.sep)[0])