# queuectl/jobs.py
"""
Job management for QueueCTL.
Handles job creation, enqueuing, claiming, finalizing, listing, and clearing.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from .config import (
    ensure_config,
    safe_load_json,
    safe_write_json,
    now_iso,
    parse_iso,
    get_locks,
)

def make_job(job_id: str, command: str, max_retries: Optional[int] = None) -> Dict[str, Any]:
    """Create a new job dictionary."""
    cfg = ensure_config()
    mr = max_retries if max_retries is not None else cfg.get("max_retries", 3)
    return {
        "id": job_id,
        "command": command,
        "state": "pending",
        "attempts": 0,
        "max_retries": mr,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "run_after": None,  # iso timestamp or None
    }

def job_is_runnable(job: Dict[str, Any]) -> bool:
    """Check if a job is ready to run."""
    if job["state"] not in ("pending", "retrying"):
        return False
    if not job.get("run_after"):
        return True
    run_at = parse_iso(job["run_after"])
    return run_at <= datetime.now(timezone.utc)

def enqueue(job_id: str, command: str) -> None:
    """Enqueue a new job if it doesn't exist."""
    jobs = safe_load_json("jobs.json", get_locks()[0])
    if any(j["id"] == job_id for j in jobs):
        print(f"[Warning] Job '{job_id}' already exists.")
        return
    job = make_job(job_id, command)
    jobs.append(job)
    safe_write_json("jobs.json", jobs, get_locks()[0])
    print(f"[Success] Job '{job_id}' enqueued.")

def claim_next_job(worker_name: str) -> Optional[Dict[str, Any]]:
    """Atomically claim the next runnable job."""
    jobs = safe_load_json("jobs.json", get_locks()[0])
    for j in jobs:
        if job_is_runnable(j) and j.get("state") in ("pending", "retrying"):
            # claim
            j["state"] = "processing"
            j["updated_at"] = now_iso()
            # persist claim
            safe_write_json("jobs.json", jobs, get_locks()[0])
            return j
    return None

def finalize_job_after_run(
    job: Dict[str, Any], success: bool, stdout: str = "", stderr: str = ""
) -> None:
    """Finalize job after execution: complete, retry, or move to DLQ."""
    jobs = safe_load_json("jobs.json", get_locks()[0])
    cfg = ensure_config()
    backoff_base = cfg.get("backoff_base", 2)

    # find and update job
    found = False
    for idx, j in enumerate(jobs):
        if j["id"] == job["id"]:
            found = True
            j["attempts"] = job["attempts"]
            j["updated_at"] = now_iso()
            if success:
                j["state"] = "completed"
                j["run_after"] = None
            else:
                if job["attempts"] < j.get("max_retries", cfg.get("max_retries")):
                    # schedule retry
                    delay = (backoff_base ** job["attempts"])
                    run_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                    j["state"] = "retrying"
                    j["run_after"] = run_at.isoformat()
                else:
                    # mark dead
                    j["state"] = "dead"
                    j["run_after"] = None
            break

    if not found:
        return

    # Separate dead jobs for DLQ
    remaining = [j for j in jobs if j.get("state") != "dead"]
    dead = [j for j in jobs if j.get("state") == "dead"]

    safe_write_json("jobs.json", remaining, get_locks()[0])

    if dead:
        existing_dlq = safe_load_json("dlq.json", get_locks()[1])
        for d in dead:
            d.setdefault("moved_to_dlq_at", now_iso())
            existing_dlq.append(d)
        safe_write_json("dlq.json", existing_dlq, get_locks()[1])

def list_jobs(state: Optional[str] = None) -> None:
    """List jobs, optionally filtered by state."""
    jobs = safe_load_json("jobs.json", get_locks()[0])
    if not jobs:
        print("No jobs.")
        return
    for j in jobs:
        if state and j["state"] != state:
            continue
        ra = j.get("run_after")
        print(f"{j['id']} | {j['state']} | attempts={j['attempts']} | run_after={ra} | updated={j['updated_at']}")

def clear_completed() -> None:
    """Remove completed jobs from the queue."""
    jobs = safe_load_json("jobs.json", get_locks()[0])
    active = [j for j in jobs if j["state"] in ("pending", "retrying", "processing")]
    removed = len(jobs) - len(active)
    safe_write_json("jobs.json", active, get_locks()[0])
    print(f"Cleared {removed} completed jobs.")