import os
import subprocess
import time
import sys

# This script simulates what a real LLM (Lead Agent) would do when running the orchestrator.
# It acts as a wrapper around the orchestrator's environment to test the full Swarm pipeline.

def main():
    print("\n" + "="*50)
    print("🚀 Starting Custom ELF Swarm Simulation 🚀")
    print("="*50 + "\n")

    workspace = "workspace/dummy_chal"

    # Clean up previous runs
    subprocess.run(["rm", "-rf", workspace], check=False)
    os.makedirs(workspace, exist_ok=True)

    # 1. Create a dummy C program with a hidden flag
    print("[1] Generating custom ELF challenge...")
    source_code = """
#include <stdio.h>
int main() {
    printf("Welcome to the challenge!\\n");
    // The flag is hidden in this binary!
    char* flag = "CTF{Swarm_C0ncurr3ncy_W0rks_992}";
    return 0;
}
"""
    with open(f"{workspace}/source.c", "w") as f:
        f.write(source_code)

    subprocess.run(["gcc", f"{workspace}/source.c", "-o", f"{workspace}/vuln_bin"], check=True)
    print("    -> Compilation successful. vuln_bin created.")

    # 2. Start the Orchestrator daemon in the background
    print("\n[2] Starting Orchestrator Daemon (simulating 'python orchestrator.py solve')...")
    # We use the WORKER_SCRIPT environment variable to tell the orchestrator to spawn
    # our intelligent mock worker instead of the generic wrapper that just calls `gh copilot`
    env = os.environ.copy()
    env["WORKER_SCRIPT"] = "agents/copilot_mock.py"
    env["KEEP_ALIVE"] = "1"

    orchestrator_proc = subprocess.Popen(
        ["python", "orchestrator.py", "solve", "--dir", workspace, "--category", "pwn"],
        env=env,
        stdout=subprocess.DEVNULL, # Suppress the orchestrator's foreground output for clarity
        stderr=subprocess.DEVNULL
    )

    time.sleep(2) # Give the daemon a moment to initialize the DB and start watching

    # 3. Simulate Lead Agent Action: Create a task for a worker to find the flag
    print("\n[3] 🤖 [Lead Agent]: 'I see a binary. I will delegate static analysis to a Swarm Worker.'")
    print("    -> Executing native command: `python ctf_task.py create 'Run strings on vuln_bin'`")

    create_result = subprocess.run(
        ["python", "ctf_task.py", "--workspace", workspace, "create", "Run strings on vuln_bin"],
        capture_output=True, text=True
    )
    print(f"    -> System response: {create_result.stdout.strip()}")

    # 4. Wait for the Orchestrator to detect the task, spawn the worker, and for the worker to complete
    print("\n[4] ⏳ Waiting for Orchestrator to detect task and spawn Worker...")

    found_flag = False
    for i in range(15):
        time.sleep(1)
        # The Lead Agent periodically checks status
        status_result = subprocess.run(
            ["python", "ctf_task.py", "--workspace", workspace, "status"],
            capture_output=True, text=True
        )

        if "COMPLETED" in status_result.stdout:
            print("\n    -> Task status changed to COMPLETED!")
            found_flag = True
            break
        print(".", end="", flush=True)

    if not found_flag:
        print("\n❌ Simulation Failed: Worker did not complete the task in time.")
        orchestrator_proc.terminate()
        sys.exit(1)

    # 5. Simulate Lead Agent Action: Read the results
    print("\n[5] 🤖 [Lead Agent]: 'The worker finished! Let's read the results.'")
    print("    -> Executing native command: `python ctf_task.py read 1`")

    read_result = subprocess.run(
        ["python", "ctf_task.py", "--workspace", workspace, "read", "1"],
        capture_output=True, text=True
    )

    print("\n=== Output from Worker ===")
    print(read_result.stdout)
    print("==========================\n")

    # 6. Verify the flag was found
    if "CTF{Swarm_C0ncurr3ncy_W0rks_992}" in read_result.stdout:
        print("✅ Simulation Successful! The Orchestrator successfully spawned a concurrent worker to execute the task and find the custom flag.")
    else:
        print("❌ Simulation Failed: The flag was not in the worker's output.")

    # Clean up the orchestrator daemon
    orchestrator_proc.terminate()

if __name__ == "__main__":
    main()
