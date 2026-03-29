import os
import subprocess
import sqlite3
import time
import threading
import atexit

from mcp.server.fastmcp import FastMCP
from ctf_task import get_pending_tasks, set_in_progress, init_db, fail_task, DB_FILE, read_scratchpad as db_read_scratchpad, append_scratchpad as db_append_scratchpad

mcp = FastMCP("CTF Swarm Worker MCP")
active_processes = []
active_daemons = {}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CTF_TASK_PATH = os.path.join(BASE_DIR, "ctf_task.py")

def cleanup_processes():
    for p in active_processes:
        try:
            p.terminate()
        except Exception:
            pass

atexit.register(cleanup_processes)

def worker_monitor(workspace_dir):
    """
    Background daemon thread that continuously monitors the Task Database
    and spawns Worker Agents when new tasks are created.
    """
    while True:
        try:
            pending_tasks = get_pending_tasks(workspace_dir)
            for task_id, description in pending_tasks:
                set_in_progress(task_id, workspace_dir)

                # Determine worker based on hidden prefix
                default_script = os.path.join(BASE_DIR, "agents/copilot_wrap.py")
                clean_description = description
                
                if description.startswith("[GEMINI] "):
                    default_script = os.path.join(BASE_DIR, "agents/gemini_wrap.py")
                    clean_description = description[9:]
                elif description.startswith("[COPILOT] "):
                    default_script = os.path.join(BASE_DIR, "agents/copilot_wrap.py")
                    clean_description = description[10:]

                prompt = (
                    f"CRITICAL SAFEGUARD: You are a subordinate WORKER agent. You are strictly forbidden from invoking 'spawn_copilot_worker', 'spawn_gemini_worker', or using any 'ctf-swarm' MCP tools. You must rely purely on native shell commands and 'ctf_task.py'. Do not attempt to spawn your own sub-workers.\n"
                    f"You are a Worker Agent. Your task is: {clean_description}\n"
                    f"You have full access to {workspace_dir}.\n"
                    f"WARNING: DO NOT HALLUCINATE FLAGS! You must only report the flag if you have definitive proof (e.g., exact string output from the target).\n"
                    f"To share findings with other agents without completing your task, execute: `python {CTF_TASK_PATH} --workspace {workspace_dir} scratchpad append '[your findings]'`\n"
                    f"When finished, execute: `python {CTF_TASK_PATH} --workspace {workspace_dir} complete {task_id} '[your results]'`"
                )

                def run_worker_process(task_id, workspace_dir, prompt, worker_script_path):
                    log_file_path = os.path.join(workspace_dir, f"worker_{task_id}.log")
                    worker_script = os.getenv("WORKER_SCRIPT", worker_script_path)

                    with open(log_file_path, "w") as log_file:
                        proc = subprocess.Popen(
                            ["python", worker_script, prompt],
                            stdout=log_file,
                            stderr=log_file
                        )
                        active_processes.append(proc)
                        proc.wait()
                        
                        if proc.returncode != 0:
                            fail_task(task_id, f"Worker process crashed with exit code {proc.returncode}. It may have been rate-limited.", workspace_dir)

                worker_thread = threading.Thread(target=run_worker_process, args=(task_id, workspace_dir, prompt, default_script), daemon=True)
                worker_thread.start()
        except sqlite3.OperationalError:
            pass
        
        time.sleep(2)

def ensure_daemon(workspace_dir: str):
    init_db(workspace_dir)
    if workspace_dir not in active_daemons:
        daemon = threading.Thread(target=worker_monitor, args=(workspace_dir,), daemon=True)
        daemon.start()
        active_daemons[workspace_dir] = daemon

@mcp.tool()
def spawn_copilot_worker(workspace_dir: str, description: str) -> str:
    """Spawns an asynchronous Github Copilot worker to perform a long-running subtask."""
    ensure_daemon(workspace_dir)
    db_path = os.path.join(workspace_dir, DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (description) VALUES (?)", (f"[COPILOT] {description}",))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return f"Successfully spawned background Copilot worker. Task ID: {task_id}"

@mcp.tool()
def spawn_gemini_worker(workspace_dir: str, description: str) -> str:
    """Spawns an asynchronous Gemini worker to perform a long-running subtask."""
    ensure_daemon(workspace_dir)
    db_path = os.path.join(workspace_dir, DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (description) VALUES (?)", (f"[GEMINI] {description}",))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return f"Successfully spawned background Gemini worker. Task ID: {task_id}"

@mcp.tool()
def check_worker_status(workspace_dir: str, task_id: int) -> str:
    """Gets the status and description of a single task."""
    ensure_daemon(workspace_dir)
    db_path = os.path.join(workspace_dir, DB_FILE)
    if not os.path.exists(db_path):
        return f"Database not found in {workspace_dir}."
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT status, description FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return f"Error: Task #{task_id} not found."
    status, desc = row
    return f"Task #{task_id} [{status}]: {desc}"

@mcp.tool()
def read_worker_results(workspace_dir: str, task_id: int) -> str:
    """Reads the full description and final results of a background worker."""
    ensure_daemon(workspace_dir)
    db_path = os.path.join(workspace_dir, DB_FILE)
    if not os.path.exists(db_path):
        return f"Database not found in {workspace_dir}."
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT description, status, result FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return f"Error: Task #{task_id} not found."
    description, status, result = row
    
    out = f"--- Task #{task_id} ---\nStatus: {status}\nDescription:\n{description}\n\nResult:\n"
    if result:
        out += result
    else:
        out += "(No result yet)"
    return out

@mcp.tool()
def list_tasks(workspace_dir: str) -> str:
    """Lists all spawned worker tasks and their current statuses."""
    ensure_daemon(workspace_dir)
    db_path = os.path.join(workspace_dir, DB_FILE)
    if not os.path.exists(db_path):
        return f"No tasks found in {workspace_dir}."
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, description FROM tasks")
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        return "No tasks found."

    out = ""
    for tid, status, desc in tasks:
        desc_short = desc[:50] + "..." if len(desc) > 50 else desc
        out += f"Task #{tid} [{status}]: {desc_short}\n"
    return out

@mcp.tool()
def append_scratchpad(workspace_dir: str, note: str) -> str:
    """Appends a note to the shared Swarm scratchpad memory for all agents to see."""
    ensure_daemon(workspace_dir)
    db_append_scratchpad(note, workspace_dir)
    return "Note successfully appended to shared scratchpad."

@mcp.tool()
def read_scratchpad(workspace_dir: str) -> str:
    """Reads all notes currently inside the shared Swarm scratchpad memory."""
    ensure_daemon(workspace_dir)
    return db_read_scratchpad(workspace_dir)

if __name__ == "__main__":
    mcp.run()
