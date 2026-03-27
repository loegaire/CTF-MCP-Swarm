import sys
import subprocess
import time

def run_copilot(prompt):
    """
    Mock Worker Agent. This simulates an AI that receives a prompt from the orchestrator,
    executes a shell command to solve the task, and then reports the result via ctf_task.py.
    """
    print(f"[Worker Simulation] Received prompt:\n{prompt}")

    # Simulating LLM parsing the prompt
    # The prompt looks like:
    # "You are a Worker Agent. Your task is: Run strings on vuln_bin
    # You have full access to workspace/dummy_chal.
    # When finished, execute: `python ctf_task.py --workspace workspace/dummy_chal complete 1 '[your results]'`"

    task_id = "1"
    workspace = "workspace/dummy_chal"

    # 1. Execute the actual task (Run strings on the binary)
    print(f"[Worker Simulation] Running 'strings workspace/dummy_chal/vuln_bin'...")
    time.sleep(1)

    try:
        result = subprocess.run(["strings", f"{workspace}/vuln_bin"], capture_output=True, text=True, check=True)

        # AI looks for the flag in the output
        flag = None
        for line in result.stdout.splitlines():
            if "CTF{" in line:
                flag = line.strip()
                break

        if flag:
            findings = f"I ran strings and found the flag: {flag}"
        else:
            findings = "I ran strings but didn't find the flag."

    except Exception as e:
        findings = f"Failed to run strings: {e}"

    # 2. Complete the task using the CLI tool
    print(f"[Worker Simulation] Reporting results: {findings}")
    subprocess.run(["python", "ctf_task.py", "--workspace", workspace, "complete", task_id, findings])
    print("[Worker Simulation] Exiting.")

if __name__ == "__main__":
    prompt = sys.argv[1]
    run_copilot(prompt)
