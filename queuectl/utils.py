"""
Utility functions for QueueCTL.
Includes logging, command execution, and status reporting.
"""

import os
import subprocess
import json
import datetime
from typing import Dict, Any

from .config import safe_load_json, get_locks, now_iso
from .jobs import list_jobs, clear_completed


# =========================================================
#  Logging helpers
# =========================================================
def log_event(message: str, worker_name: str = "MAIN") -> None:
    """Print a timestamped log line for human-readable worker progress."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{worker_name}] {message}")


def write_job_log(
    job: Dict[str, Any], result_code: int, stdout: str, stderr: str
) -> None:
    """Append job execution log to file."""
    os.makedirs("logs", exist_ok=True)
    path = os.path.join("logs", f"{job['id']}.log")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"=== Run at {now_iso()} ===\n")
        f.write(f"Command: {job['command']}\n")
        f.write(f"Return code: {result_code}\n")
        f.write(f"Attempts: {job['attempts']}\n")
        if stdout:
            f.write("STDOUT:\n")
            f.write(stdout + "\n")
        if stderr:
            f.write("STDERR:\n")
            f.write(stderr + "\n")
        f.write("\n")


# =========================================================
#  Core utility functions
# =========================================================
def run_shell_command(job: Dict[str, Any], timeout: int = 60) -> tuple[int, str, str]:
    """Run the job's shell command with timeout."""
    try:
        proc = subprocess.run(
            job["command"], shell=True, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as e:
        return 1, e.stdout or "", f"Timeout after {timeout}s"


def status() -> None:
    """Print overall queue status."""
    jobs = safe_load_json("jobs.json", get_locks()[0])
    dlq = safe_load_json("dlq.json", get_locks()[1])
    counts: Dict[str, int] = {}
    for j in jobs:
        counts[j["state"]] = counts.get(j["state"], 0) + 1
    print("=== STATUS ===")
    print(f"Main queue: {len(jobs)} jobs")
    for state, cnt in counts.items():
        print(f"  {state}: {cnt}")
    print(f"DLQ: {len(dlq)} jobs")


def show_logs(job_id: str) -> None:
    """Display logs for a specific job."""
    path = os.path.join("logs", f"{job_id}.log")
    if not os.path.exists(path):
        print("No logs.")
        return
    with open(path, "r", encoding="utf-8") as f:
        print(f.read())
