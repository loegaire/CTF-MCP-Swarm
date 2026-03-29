# CTF Swarm Worker MCP

An autonomous, concurrent **Agent-Directed Swarm** system for solving Capture The Flag (CTF) challenges.

This project facilitates a Model Context Protocol (MCP) server designed to empower a Lead AI Agent (such as Gemini or Copilot) to dynamically spawn, manage, and communicate with background Worker Agents. Instead of a rigid, sequential problem-solving loop, this architecture enables parallelized tasks—like fuzzing a web endpoint while simultaneously reverse-engineering a binary.

##  Aim

The primary aim of this project is to provide a lead tool with the ability to spawn worker agents and cooperatively solve complex CTF challenges. By leveraging MCP, the Lead Agent can delegate tedious, time-consuming, or isolated tasks to specialized background workers, allowing it to focus on coordinating results and constructing the final exploit logic.

## requirements
Active Copilot subscription and/or gemini subscription. Then install [gemini-cli](https://geminicli.com/) and or [copilot-cli](https://github.com/features/copilot/cli/)
##  4 Core Functions Facilitated

This project is built around four central capabilities to orchestrate the swarm:

1. **A Database of History**: Maintains a persistent SQLite database (`task_db.sqlite`) in the workspace. It records every task, its current status (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`), and its results. This ensures the Lead Agent can reliably query past actions and track the swarm's progress.
2. **A Scratchpad for Communications Between Child Workers**: The task database acts as an asynchronous scratchpad. Lead and Worker Agents communicate natively by creating tasks and posting results. Workers write their findings to the database when complete, which the Lead Agent can later read and integrate into its exploitation strategy.
3. **Read the Codebase Document and Explain the Architecture**: The structure inherently separates concerns. A background Python daemon (Orchestrator) manages process lifecycle, while the MCP server exposes the necessary tools for AI agents to comprehend the state of the swarm and architecture, managing files and context seamlessly. (For a deep dive, see [Architecture](#architecture)).
4. **Task Delegation and Spawning (Concurrency)**: The Lead Agent can dynamically spawn distinct worker agents (e.g., Copilot for rapid syntax generation, Gemini for large context analysis) to run natively on the host machine.

##  Architecture

This system implements an **Agent-Directed Swarm** paradigm designed for maximum autonomy, concurrency, and context awareness.

*   **The Lead Agent**: The primary AI session driving the CTF solution. It explores the workspace, identifies parallelizable sub-tasks (e.g., cracking a hash, fuzzing a port), and uses the MCP tools to delegate them.
*   **The Orchestrator Daemon (`mcp_server.py`)**: The `mcp_server.py` natively hosts the orchestrator logic. Upon tool invocation, it automatically invokes `ensure_daemon()` to launch a background daemon thread that continuously monitors the localized `task_db.sqlite` for changes. When a new task is created, this daemon spawns a fresh Worker Agent process to execute it, manages the output logs, and handles timeouts or crashes.
*   **The Worker Agents (`agents/gemini_wrap.py`, `agents/copilot_wrap.py`)**: Wrappers for native CLI tools (`geminicli`, `gh copilot`). They are spawned in the background with a specific prompt, run natively to leverage local tools (compilers, debuggers, network scanners), and report their findings back to the database via the `ctf_task.py` CLI.
*   **Task Manager CLI (`ctf_task.py`)**: A native command-line tool that allows agents to interact with the task database directly without relying on fragile JSON parsing. The `task_db.sqlite` file is created directly within the `workspace_dir` where the target application is being analyzed.

For more details, please refer to the `Architecture.md` file included in this repository.

##  How to Run

The MCP server handles orchestration natively, so you do not need to run a standalone orchestrator. When the Lead Agent interacts with an MCP tool (e.g., `spawn_copilot_worker`), the `mcp_server.py` automatically initializes a background daemon thread (`worker_monitor`) for the requested `workspace_dir`.

It also automatically calls `init_db()` (from `ctf_task.py`) to spawn a fresh SQLite database named `task_db.sqlite` inside the designated workspace. This ensures independent, localized task tracking for each CTF challenge.

To get started, simply configure your Lead AI Agent to connect to the MCP server.

*(Optional)* You can still run the included `orchestrator.py` if you prefer to test the pipeline in an interactive, standalone CLI mode.
   ```bash
   python orchestrator.py solve --dir ./workspace/pwn_challenge --category pwn
   ```

##  All Functionalities (MCP Tools)

The `mcp_server.py` exposes the following tools to the Lead Agent via the Model Context Protocol:

*   **`spawn_copilot_worker(workspace_dir: str, description: str)`**: Spawns an asynchronous Github Copilot worker to perform a long-running subtask. Creates a database entry and triggers the Orchestrator.
*   **`spawn_gemini_worker(workspace_dir: str, description: str)`**: Spawns an asynchronous Gemini worker to perform a long-running subtask. Creates a database entry and triggers the Orchestrator.
*   **`list_tasks(workspace_dir: str)`**: Lists all spawned worker tasks and their current statuses (e.g., `PENDING`, `COMPLETED`). Acts as the history database interface.
*   **`check_worker_status(workspace_dir: str, task_id: int)`**: Gets the detailed status and description of a single specific task.
*   **`read_worker_results(workspace_dir: str, task_id: int)`**: Reads the full description and final results of a background worker. Acts as the scratchpad communication reader.

[![Pasted-image-20260329110336.png](https://i.postimg.cc/W4k8n8FH/Pasted-image-20260329110336.png)](https://postimg.cc/wt9DxhkX)
[![image.png](https://i.postimg.cc/C51fvMrb/image.png)](https://postimg.cc/zbsBvNrf)
##  How to Set Up the MCP Server in Different AI Agents

To use this Swarm architecture, you must configure your Lead AI Agent to connect to the MCP server.

### Claude Desktop

Add the following to your `claude_desktop_config.json` (usually located at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "ctf-swarm-worker": {
      "command": "python",
      "args": [
        "/absolute/path/to/ctf-coop-solver/mcp_server.py"
      ]
    }
  }
}
```
*Note: Ensure you provide the absolute path to the `mcp_server.py` file.*

### Cursor

1. Open Cursor Settings (`Cmd/Ctrl + ,`).
2. Navigate to **Features** > **MCP Servers**.
3. Click **+ Add New MCP Server**.
4. Set the Type to `command`.
5. Name it `ctf-swarm-worker`.
6. Set the command to: `python /absolute/path/to/ctf-coop-solver/mcp_server.py`.

Once connected, your AI assistant will be able to spawn workers, list tasks, and read results directly from its chat interface, effectively becoming the Lead Agent of the Swarm.
