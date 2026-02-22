
import pytest
import subprocess
import time
import json
import os
import sys
from pathlib import Path

def test_browser_persistence():
    # Set PYTHONPATH to include src
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + "/src"

    # Cleanup first
    python_cmd = "python3"
    if Path(".tmp/browser_cdp.json").exists():
        subprocess.run([python_cmd, "src/ragmaker/tools/browser_close.py"], env=env, check=False)

    # Open
    print("Launching browser...")
    proc = subprocess.run([python_cmd, "src/ragmaker/tools/browser_open.py"], env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Browser open failed: {proc.stderr}")
    assert proc.returncode == 0
    output = json.loads(proc.stdout)
    assert output["status"] == "success"
    pid = output.get("pid")
    assert pid is not None

    cdp_file = Path(".tmp/browser_cdp.json")
    assert cdp_file.exists()

    # Navigate 1
    print("Navigating to example.com...")
    proc = subprocess.run([python_cmd, "src/ragmaker/tools/browser_navigate.py", "--url", "http://example.com"], env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Navigate 1 failed: {proc.stderr}")
    assert proc.returncode == 0
    output = json.loads(proc.stdout)
    assert output["status"] == "success"
    # example.com might redirect or strip slash
    assert "example.com" in output["url"]

    # Navigate 2
    print("Navigating to example.org...")
    proc = subprocess.run([python_cmd, "src/ragmaker/tools/browser_navigate.py", "--url", "http://example.org"], env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Navigate 2 failed: {proc.stderr}")
    assert proc.returncode == 0
    output = json.loads(proc.stdout)
    assert output["status"] == "success"
    assert "example.org" in output["url"]

    # Verify PID is still running
    try:
        os.kill(pid, 0)
    except OSError:
        pytest.fail("Browser process died")

    # Extract
    print("Extracting from example.com...")
    output_dir = Path(".tmp/test_output")
    # Clean output dir
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    proc = subprocess.run([python_cmd, "src/ragmaker/tools/browser_extract.py", "--url", "http://example.com", "--output-dir", str(output_dir)], env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Extract failed: {proc.stderr}")
    assert proc.returncode == 0
    output = json.loads(proc.stdout)
    assert output["status"] == "success"
    assert "markdown_content" in output
    assert "extracted_path" in output
    assert Path(output["extracted_path"]).exists()

    # Close
    print("Closing browser...")
    proc = subprocess.run([python_cmd, "src/ragmaker/tools/browser_close.py"], env=env, capture_output=True, text=True)
    assert proc.returncode == 0

    # Verify PID is gone (give it a moment)
    time.sleep(1)
    with pytest.raises(OSError):
        os.kill(pid, 0)

    assert not cdp_file.exists()
