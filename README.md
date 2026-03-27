# CTF-solver

An autonomous, concurrent "Agent-Directed Swarm" system for solving Capture The Flag (CTF) challenges using AI CLI tools (`geminicli` and `copilotcli`).

Unlike rigid, sequential problem-solvers, this system allows a Lead AI Agent to dynamically spawn concurrent Worker Agents to handle parallelizable tasks (like fuzzing, reverse engineering, or brute-forcing) while it continues to build the final exploit.

## Core Philosophy

1.  **Native Execution:** Agents run directly on the host (or within a single Docker container), allowing them to write bash scripts, compile C code, run `gdb`, and execute exploits without restrictive sandbox abstractions.
2.  **The Swarm:** The AI decides when a task is too slow or independent and delegates it to background worker processes.
3.  **CLI-Native Communication:** Agents coordinate not through fragile JSON parsing, but by executing a native command-line tool (`ctf_task.py`) built directly into their environment.

## Usage

*Note: Ensure you have `geminicli` and `gh copilot` installed and authenticated on your host system before running.*

### 1. Set up the Workspace
Create a directory for your target challenge and place the relevant files inside.

```bash
mkdir -p workspace/pwn_buffer_overflow
cp vuln_bin source.c workspace/pwn_buffer_overflow/
```

*(Optional) Provide initial context to the agents:*
```bash
echo "I think there is a buffer overflow in the main() function" > workspace/pwn_buffer_overflow/notes.md
```

### 2. Launch the Orchestrator
Point the orchestrator at the workspace and provide the challenge category (e.g., pwn, web, crypto, rev).

```bash
python orchestrator.py solve --dir ./workspace/pwn_buffer_overflow --category pwn
```

### 3. Watch the Swarm
The Orchestrator will:
1. Initialize a task database in the workspace.
2. Spawn the **Lead Agent** (typically Gemini, for its large context window).
3. The Lead Agent will analyze the files and, if necessary, use the `ctf_task.py` tool to spawn background **Worker Agents** (e.g., Copilot, for rapid syntax generation or specific analysis).
4. You will see live output as the Lead Agent orchestrates the workers, compiles findings, writes the final exploit, and captures the flag.

## How it Works (Under the Hood)

The magic happens via `ctf_task.py`. The Orchestrator is a simple daemon that watches this database.

When the Lead AI runs:
`python ctf_task.py create "Run nmap against 10.10.10.5"`

The Orchestrator sees the new entry, spawns a background `copilot_wrap` process, and tells it to execute that specific prompt.

When the worker finishes, it runs:
`python ctf_task.py complete 1 "Port 80 is open."`

The Lead AI can then run:
`python ctf_task.py read 1`
...and use that information to continue the attack.

For a deep dive into the architecture, read `Architecture.md`.