"""
Dead Letter Queue management for QueueCTL.
"""

from typing import Dict, Any, List
from .config import safe_load_json, safe_write_json, now_iso, get_locks
from .jobs import make_job  # for consistency if needed

DLQ_FILE = "dlq.json"
JOBS_FILE = "jobs.json"

def push_to_dlq(job: dict) -> None:
    """Move a job to the Dead Letter Queue (DLQ)."""
    dlq = safe_load_json(DLQ_FILE, get_locks()[1])
    job["state"] = "dead"
    job["run_after"] = None
    job["moved_to_dlq_at"] = now_iso()
    dlq.append(job)
    safe_write_json(DLQ_FILE, dlq, get_locks()[1])
    print(f"[DLQ] Job '{job['id']}' moved to Dead Letter Queue.")


def list_dlq() -> None:
    """List all DLQ jobs."""
    dlq = safe_load_json(DLQ_FILE, get_locks()[1])
    if not dlq:
        print("Dead Letter Queue is empty.")
        return
    print("Dead Letter Queue:")
    for j in dlq:
        if "id" in j and j["id"].strip():
            print(f" • {j['id']} | attempts={j.get('attempts', 0)} | command={j.get('command','')}")


def retry_dlq_job(job_id: str) -> None:
    """Retry a DLQ job by moving it back to the main queue."""
    dlq = safe_load_json(DLQ_FILE, get_locks()[1])
    # Filter valid jobs
    valid_jobs = [j for j in dlq if "id" in j and j["id"].strip()]
    job = next((j for j in valid_jobs if j["id"] == job_id), None)

    if not job:
        print(f"No DLQ job with id '{job_id}'.")
        return

    # reset job and move to main queue
    job["state"] = "pending"
    job["attempts"] = 0
    job["updated_at"] = now_iso()
    job["run_after"] = None

    # Remove from DLQ
    dlq = [j for j in dlq if j["id"] != job_id]
    safe_write_json(DLQ_FILE, dlq, get_locks()[1])

    # Add to main jobs
    jobs = safe_load_json(JOBS_FILE, get_locks()[0])
    jobs.append(job)
    safe_write_json(JOBS_FILE, jobs, get_locks()[0])
    print(f"[DLQ Retry] Job '{job_id}' moved back to main queue.")
