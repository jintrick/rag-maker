import subprocess
import os
import shutil

relative_path = os.path.join("test_case_2_dir", "subdir")
test_dir = os.path.join("cache", relative_path)

# Clean up before the test, remove the top-level test dir
if os.path.exists(os.path.join("cache", "test_case_2_dir")):
    shutil.rmtree(os.path.join("cache", "test_case_2_dir"))

# Run the script
try:
    print(f"Running test for {relative_path}...")
    subprocess.run(
        ["python", "tools/make_cache_dir.py", "--relative-path", relative_path],
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
shutil.rmtree(os.path.join("cache", "test_case_2_dir"))