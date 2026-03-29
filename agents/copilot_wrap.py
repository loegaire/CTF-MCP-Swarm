import sys
import subprocess
import time
import os
import re

def run_copilot(prompt):
    """
    Generic wrapper for gh copilot cli.
    It takes the prompt from the orchestrator, runs the actual CLI tool natively,
    and returns the output.
    """
    print(f"[Copilot Wrap Worker] Running gh copilot with prompt...")

    try:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # We use --yolo to automatically accept actions
                # and -p for non-interactive execution.
                result = subprocess.run(
                    ["copilot", "--yolo", "-p", prompt],
                    check=True
                )
                break
            except subprocess.CalledProcessError as e:
                if attempt < max_retries - 1:
                    sleep_time = 4 * (2 ** attempt)
                    print(f"[Copilot Wrap Error] gh copilot failed with exit code {e.returncode}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    print(f"[Copilot Wrap Error] gh copilot failed after {max_retries} attempts.")
                    sys.exit(e.returncode)

    except FileNotFoundError:
        print("[Copilot Wrap Error] 'copilot' command not found. Please ensure it is installed and in your PATH.")
        print(f"[Simulated Output for Prompt]: {prompt}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python copilot_wrap.py '<prompt>'")
        sys.exit(1)

    prompt = sys.argv[1]
    run_copilot(prompt)
