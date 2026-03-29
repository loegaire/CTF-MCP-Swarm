import sqlite3
import argparse
import sys
import os

DB_FILE = "task_db.sqlite"

def init_db(workspace_dir="."):
    db_path = os.path.join(workspace_dir, DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scratchpad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    return db_path

def create_task(description, workspace_dir="."):
    db_path = os.path.join(workspace_dir, DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (description) VALUES (?)", (description,))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"Task #{task_id} created successfully.")

def get_status(workspace_dir="."):
    db_path = os.path.join(workspace_dir, DB_FILE)
    if not os.path.exists(db_path):
        print("No task database found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, description FROM tasks")
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        print("No tasks found.")
        return

    for task_id, status, description in tasks:
        # Truncate description for status display
        desc_short = description[:50] + "..." if len(description) > 50 else description
        print(f"Task #{task_id} [{status}]: {desc_short}")

def complete_task(task_id, result, workspace_dir="."):
    db_path = os.path.join(workspace_dir, DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if task exists and is not already completed
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        print(f"Error: Task #{task_id} not found.")
        conn.close()
        sys.exit(1)

    cursor.execute("UPDATE tasks SET status = 'COMPLETED', result = ? WHERE id = ?", (result, task_id))
    conn.commit()
    conn.close()
    print(f"Task #{task_id} marked as COMPLETED.")

def fail_task(task_id, error_msg, workspace_dir="."):
    db_path = os.path.join(workspace_dir, DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = 'FAILED', result = ? WHERE id = ?", (error_msg, task_id))
    conn.commit()
    conn.close()
    print(f"Task #{task_id} marked as FAILED.")

def read_task(task_id, workspace_dir="."):
    db_path = os.path.join(workspace_dir, DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT description, status, result FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        print(f"Error: Task #{task_id} not found.")
        sys.exit(1)

    if not row:
        print(f"Error: Task #{task_id} not found.")
        sys.exit(1)

    description, status, result = row
    print(f"--- Task #{task_id} ---")
    print(f"Status: {status}")
    print(f"Description:\n{description}")
    if result:
        print(f"\nResult:\n{result}")
    else:
        print("\nResult: (No result yet)")

def append_scratchpad(note, workspace_dir="."):
    db_path = os.path.join(workspace_dir, DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scratchpad (note) VALUES (?)", (note,))
    conn.commit()
    conn.close()
    print("Note appended to scratchpad.")

def read_scratchpad(workspace_dir="."):
    db_path = os.path.join(workspace_dir, DB_FILE)
    if not os.path.exists(db_path):
        return "No task database found."
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT created_at, note FROM scratchpad ORDER BY created_at ASC")
    notes = cursor.fetchall()
    conn.close()
    
    if not notes:
        return "Scratchpad is empty."
        
    out = "--- Swarm Scratchpad ---\n"
    for ts, note in notes:
        out += f"[{ts}] {note}\n"
    return out

def set_in_progress(task_id, workspace_dir="."):
     # This is mainly for the orchestrator to use, not the agents
    db_path = os.path.join(workspace_dir, DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = 'IN_PROGRESS' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def get_pending_tasks(workspace_dir="."):
    # This is mainly for the orchestrator to use
    db_path = os.path.join(workspace_dir, DB_FILE)
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, description FROM tasks WHERE status = 'PENDING'")
    tasks = cursor.fetchall()
    conn.close()
    return tasks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CTF Task Manager CLI for Swarm Agents")
    parser.add_argument("--workspace", default=".", help="Path to the workspace directory containing the task DB.")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create Task
    parser_create = subparsers.add_parser("create", help="Create a new task")
    parser_create.add_argument("description", help="Description of the task for the worker agent")

    # Status
    parser_status = subparsers.add_parser("status", help="List all tasks and their current status")

    # Complete Task
    parser_complete = subparsers.add_parser("complete", help="Mark a task as complete and provide the results")
    parser_complete.add_argument("task_id", type=int, help="ID of the task to complete")
    parser_complete.add_argument("result", help="The results or findings from the task")

    # Read Task
    parser_read = subparsers.add_parser("read", help="Read the full description and results of a task")
    parser_read.add_argument("task_id", type=int, help="ID of the task to read")

    # Fail Task (Internal)
    parser_fail = subparsers.add_parser("fail", help="Mark a task as failed with an error message")
    parser_fail.add_argument("task_id", type=int, help="ID of the task to fail")
    parser_fail.add_argument("error", help="The error message")

    # Internal Init
    parser_init = subparsers.add_parser("init", help="Initialize the database (used by Orchestrator)")

    # Scratchpad
    parser_scratch = subparsers.add_parser("scratchpad", help="Interact with the shared memory scratchpad")
    scratch_subs = parser_scratch.add_subparsers(dest="scratch_cmd", help="Scratchpad command (append or read)")
    
    scratch_append = scratch_subs.add_parser("append", help="Append a note")
    scratch_append.add_argument("note", help="The note to append")
    
    scratch_read = scratch_subs.add_parser("read", help="Read notes")

    args = parser.parse_args()

    # Create workspace if it doesn't exist just in case
    os.makedirs(args.workspace, exist_ok=True)

    if args.command == "init":
        init_db(args.workspace)
        print("Database initialized.")
    elif args.command == "create":
        init_db(args.workspace) # ensure it exists
        create_task(args.description, args.workspace)
    elif args.command == "status":
        get_status(args.workspace)
    elif args.command == "complete":
        complete_task(args.task_id, args.result, args.workspace)
    elif args.command == "fail":
        fail_task(args.task_id, args.error, args.workspace)
    elif args.command == "read":
        read_task(args.task_id, args.workspace)
    elif args.command == "scratchpad":
        init_db(args.workspace)
        if args.scratch_cmd == "append":
            append_scratchpad(args.note, args.workspace)
        elif args.scratch_cmd == "read":
            print(read_scratchpad(args.workspace))
        else:
            parser_scratch.print_help()
    else:
        parser.print_help()
