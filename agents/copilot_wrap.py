import sys
import subprocess
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
        # We use the actual CLI invocation based on the provided help docs.
        # We use --yolo to enable all permissions (allow-all-tools, paths, urls)
        # and --prompt for non-interactive execution.
        result = subprocess.run(
            ["copilot", "--yolo", "-p", prompt],
            check=True
        )

    except FileNotFoundError:
        print("[Copilot Wrap Error] 'copilot' command not found. Please ensure it is installed and in your PATH.")
        print(f"[Simulated Output for Prompt]: {prompt}")
    except subprocess.CalledProcessError as e:
        print(f"[Copilot Wrap Error] gh copilot failed with error: {e.stderr}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python copilot_wrap.py '<prompt>'")
        sys.exit(1)

    prompt = sys.argv[1]
    run_copilot(prompt)
