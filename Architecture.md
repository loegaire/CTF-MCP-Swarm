# Cooperative CLI-Driven CTF Solver (Native Execution)

## 1. Project Architecture & Philosophy

This system implements an **Agent-Directed Swarm** paradigm designed for maximum autonomy, concurrency, and context awareness.

Instead of a rigid turn-taking structure, this architecture empowers the primary AI agent (`geminicli` or `copilotcli`) to act as the "Lead Investigator." By running natively alongside the target binaries, the agents aren't restricted by a strict sandbox bridge. They can generate scripts that interact directly with the local filesystem, memory, and networking stack.

**The Swarm Concept:**
If a challenge requires multiple slow or independent tasks (e.g., fuzzing a web endpoint while simultaneously reverse-engineering a binary), the Lead Agent can dynamically spawn concurrent "Worker Agents" to handle those tasks.

**The Orchestrator's Role:**
The Orchestrator (Python) is *not* a problem solver. It is a background daemon—a dumb process manager and context router. It monitors a specialized Task Database. When the Lead Agent requests a new task, the Orchestrator spawns a fresh Worker Agent process to execute it, manages the output, and feeds the results back to the Lead Agent when requested.

## 2. Directory Structure

```
ctf-coop-solver/
├── orchestrator.py      # Background daemon: Spawns workers and manages the swarm
├── ctf_task.py          # The vital CLI tool used by agents to manage concurrent tasks
├── agents/
│   ├── gemini_wrap.py   # Wrapper for `geminicli` subprocesses
│   └── copilot_wrap.py  # Wrapper for `gh copilot` subprocesses
├── workspace/           
│   └── [challenge_name]/
│       ├── vuln_bin         # The challenge files...
│       ├── source.c         # ...
│       ├── notes.md         # (Optional) User's initial findings/hints
│       ├── task_db.sqlite   # The local database managing the swarm's tasks
│       └── active_tasks/    # Directory for Orchestrator to track running agent PIDs
└── templates/           # System prompts to guide the CLIs per category
```

## 3. The Core Components

### A. The User Entry Point

The Orchestrator operates directly on the local workspace directories.

**Command:** `python orchestrator.py solve --dir ./workspace/pwn_buffer_overflow --category pwn`

**Action:** The Orchestrator scans the directory, catalogs all files, reads `notes.md`, initializes the local Task Database (`task_db.sqlite`), and spawns the Lead Agent in an interactive session.

### B. The Task Manager CLI (`ctf_task.py`)

This is the most critical innovation for reliable concurrency. Relying on an LLM to consistently format valid JSON for an Orchestrator to parse is brittle. Instead, we give the AI agents a native command-line tool.

The AI agents interact with the Swarm exactly like they interact with `ls` or `cat`.

*   **Lead Agent creates a task:** `python ctf_task.py create "Fuzz the login endpoint at http://localhost:8080/login"`
    *   *Result:* Task added to DB. Orchestrator sees it and spawns a Worker.
*   **Lead Agent checks status:** `python ctf_task.py status`
    *   *Result:* `Task 1: IN_PROGRESS. Task 2: PENDING.`
*   **Worker Agent reports results:** `python ctf_task.py complete 1 "Fuzzing complete. Found vulnerable parameter 'username'."`
    *   *Result:* Task marked complete. Worker process terminates.
*   **Lead Agent reads results:** `python ctf_task.py read 1`

### C. Tool Integrations (The Wrappers)

Python wrappers (`gemini_wrap.py`, `copilot_wrap.py`) manage the I/O for the underlying CLI agents. Because they run natively, agents can write and execute arbitrary scripts.

*   **Lead Agent Wrapper:** Runs continuously in the foreground, maintaining the main reasoning loop and conversation history with the user/system.
*   **Worker Agent Wrapper:** Spawned by the Orchestrator in the background. It is given a specific task prompt (e.g., "You are Worker #1. Execute this task: [Task Desc]. When finished, run `ctf_task.py complete 1 '[results]'`"). It runs until the task is complete or it times out.

## 4. The Cooperative Execution Flow (The Swarm Lifecycle)

**Phase 1: The Briefing**
1.  **Orchestrator Start:** Initializes the workspace and DB.
2.  **Lead Agent Spawn:** Spawns the Lead Agent with a category-specific prompt instructing it on its role and how to use `ctf_task.py`.
3.  **Initial Analysis:** The Lead Agent explores the workspace.

**Phase 2: Delegation & The Swarm (Concurrent)**
1.  **Delegation:** If the Lead Agent identifies independent sub-tasks (e.g., cracking a hash, fuzzing a port, reverse engineering a binary), it runs `ctf_task.py create "[Task]"`.
2.  **Background Spawning:** The Orchestrator's watcher thread detects the new task, updates the status, and spawns a concurrent Worker Agent (e.g., `copilot_wrap.py`) in the background.
3.  **Lead Continues:** The Lead Agent does *not* block. It continues its own interactive session, analyzing other files or writing exploit scaffolding while the Worker crunches the heavy task.

**Phase 3: Aggregation & Exploitation**
1.  **Worker Completion:** The Worker Agent finishes its task, runs `ctf_task.py complete`, and its process terminates.
2.  **Notification:** The Lead Agent periodically runs `ctf_task.py status` or is injected with a prompt by the Orchestrator ("System Update: Task #1 Complete").
3.  **Integration:** The Lead Agent reads the results (`ctf_task.py read 1`) and integrates the findings (e.g., the cracked password, the buffer overflow offset) into the final exploit script.
4.  **Victory:** The Lead Agent executes the final exploit. If it prints the flag format (e.g., `CTF{...}`), the Orchestrator halts the entire Swarm and declares victory.

## 5. Handling Edge Cases & Orchestrator Logic

*   **Timeouts:** If a Worker Agent runs for more than 10 minutes without completing its task, the Orchestrator kills the process, marks the task as `FAILED` in the database, and logs an error for the Lead Agent to investigate.
*   **Infinite Loops:** The Orchestrator limits the total number of worker tasks that can be spawned to prevent runaway recursive task creation by a confused Lead Agent.
*   **Security Warning:** Running untrusted CTF binaries bare-metal on your primary machine carries significant risk. If you choose to sandbox later, run this entire architecture inside a single Docker VM.