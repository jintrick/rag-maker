
import pytest
import subprocess
import time
import json
import os
import sys
from pathlib import Path

WRITER_SCRIPT = """
import sys
import os
import json
import time
from pathlib import Path

# Add src to path if needed (assuming run from root)
sys.path.insert(0, os.getcwd() + "/src")

from ragmaker.utils import LockedJsonWriter

def main():
    path = Path(".tmp/test_locking.json")
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    for i in range(50):
        try:
            with LockedJsonWriter(path) as data:
                count = data.get("count", 0)
                data["count"] = count + 1
                # Small delay to keep lock held longer
                # time.sleep(0.001)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
"""

def test_catalog_locking():
    # Write script to file
    script_path = Path("test_stress_writer.py")
    with open(script_path, "w") as f:
        f.write(WRITER_SCRIPT)

    path = Path(".tmp/test_locking.json")
    if path.exists():
        path.unlink()

    procs = []
    # Launch 5 concurrent writers
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + "/src"

    for i in range(5):
        p = subprocess.Popen([sys.executable, "test_stress_writer.py"], env=env)
        procs.append(p)

    for p in procs:
        p.wait()
        assert p.returncode == 0

    # Check result
    if not path.exists():
        pytest.fail("Test file not created")

    with open(path, "r") as f:
        data = json.load(f)

    # 5 procs * 50 writes = 250
    print(f"Final count: {data.get('count')}")
    assert data["count"] == 250

    # Cleanup
    if script_path.exists():
        script_path.unlink()
    if path.exists():
        path.unlink()

if __name__ == "__main__":
    test_catalog_locking()
