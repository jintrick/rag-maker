#!/usr/bin/env python3
"""
Tool to launch a persistent Chromium process and expose CDP.
"""

import sys
import argparse
import asyncio
import logging
import json
import time
import subprocess
import os
import requests
from pathlib import Path

# Suppress logging for clean JSON output
logging.disable(logging.CRITICAL)

try:
    from ragmaker.io_utils import (
        ArgumentParsingError,
        GracefulArgumentParser,
        eprint_error,
        handle_argument_parsing_error,
        handle_unexpected_error,
        print_json_stdout,
    )
    from playwright.async_api import async_playwright
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

logger = logging.getLogger(__name__)

async def get_executable_path():
    async with async_playwright() as p:
        return p.chromium.executable_path

def main():
    # Re-enable logging for execution
    logging.disable(logging.NOTSET)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Launch a persistent browser session.")
    parser.add_argument("--no-headless", action="store_true", help="Launch browser visibly.")

    try:
        args = parser.parse_args()

        cdp_file = Path(".tmp/browser_cdp.json")
        port = 9222

        # Check if already running
        if cdp_file.exists():
            try:
                with open(cdp_file, 'r') as f:
                    data = json.load(f)
                    pid = data.get("pid")
                    try:
                        # Check process existence
                        os.kill(pid, 0)
                        # Check if port is responding
                        resp = requests.get(f"http://localhost:{port}/json/version", timeout=1)
                        if resp.status_code == 200:
                            print_json_stdout({
                                "status": "success",
                                "message": "Browser already running.",
                                "cdp_file": str(cdp_file),
                                "ws_endpoint": data.get("ws_endpoint")
                            })
                            return
                    except (OSError, requests.RequestException):
                        logger.warning(f"Stale CDP file or process {pid} not responding. Cleaning up.")
                        cdp_file.unlink()
            except Exception as e:
                logger.warning(f"Error checking existing browser: {e}")
                if cdp_file.exists():
                    try:
                        cdp_file.unlink()
                    except:
                        pass

        # Find Chromium executable
        try:
            chromium_path = asyncio.run(get_executable_path())
        except Exception as e:
            eprint_error({"status": "error", "message": f"Failed to locate Chromium executable: {e}"})
            sys.exit(1)

        user_data_dir = Path(".tmp/cache/browser_profile").resolve()
        user_data_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            chromium_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ]

        if not args.no_headless:
            # New headless mode
            cmd.append("--headless=new")

        logger.info(f"Launching browser: {' '.join(str(c) for c in cmd)}")

        # Launch process detached
        if os.name == 'nt':
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            process = subprocess.Popen(
                cmd,
                start_new_session=True, # Detach from terminal session
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        # Wait for readiness
        ws_endpoint = None
        for i in range(20): # Wait up to 10 seconds
            try:
                resp_ver = requests.get(f"http://localhost:{port}/json/version", timeout=1)
                if resp_ver.status_code == 200:
                    data = resp_ver.json()
                    ws_endpoint = data.get("webSocketDebuggerUrl")
                    if ws_endpoint:
                        break
            except requests.RequestException:
                pass
            time.sleep(0.5)

        if not ws_endpoint:
            try:
                process.kill()
            except:
                pass
            eprint_error({"status": "error", "message": "Failed to connect to browser CDP endpoint after launch."})
            sys.exit(1)

        # Save CDP info
        info = {
            "pid": process.pid,
            "ws_endpoint": ws_endpoint,
            "port": port
        }

        with open(cdp_file, 'w') as f:
            json.dump(info, f)

        print_json_stdout({
            "status": "success",
            "message": "Browser launched successfully.",
            "pid": process.pid,
            "ws_endpoint": ws_endpoint
        })

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
