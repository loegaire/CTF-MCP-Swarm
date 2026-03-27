import sys
import subprocess
import os

def run_gemini(prompt):
    """
    Generic wrapper for geminicli.
    It takes the prompt from the orchestrator, runs the actual CLI tool natively,
    and returns the output.
    """
    print(f"[Gemini Wrap] Running geminicli with prompt...")
    try:
        # In a real setup, this runs the actual geminicli command.
        # Assuming the CLI takes the prompt as a command-line argument or via stdin.
        # Example: geminicli prompt "<prompt>"

        # We use the actual CLI invocation based on the provided help docs.
        # We use --yolo to automatically accept actions and --prompt for headless mode.
        result = subprocess.run(
            ["gemini", prompt],
            check=True
        )

    except FileNotFoundError:
        print("[Gemini Wrap Error] 'gemini' command not found. Please ensure it is installed and in your PATH.")
        # Fallback for demonstration/simulation if the user runs this without the tool installed
        print(f"[Simulated Output for Prompt]: {prompt}")
    except subprocess.CalledProcessError as e:
        print(f"[Gemini Wrap Error] geminicli failed with error: {e.stderr}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gemini_wrap.py '<prompt>'")
        sys.exit(1)

    prompt = sys.argv[1]
    run_gemini(prompt)
