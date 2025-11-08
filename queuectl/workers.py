"""
Worker process management for QueueCTL.
Handles starting, stopping, and running worker loops with detailed logging.
"""

import os
import signal
import sys
import time
from multiprocessing import Process, current_process, Event
from typing import List

from .config import now_iso, ensure_config
from .jobs import claim_next_job, finalize_job_after_run
from .utils import write_job_log, run_shell_command, log_event

# Globals
worker_processes: List[Process] = []
stop_events= []

def worker_loop(stop_event) -> None:
    """Main loop for a single worker process."""
    name = current_process().name
    cfg = ensure_config()
    log_event("Worker started.", name)

    while not stop_event.is_set():
        job = claim_next_job(name)
        if not job:
            log_event("No jobs available — waiting for queue...", name)
            if stop_event.wait(2):
                break
            continue

        job["attempts"] += 1
        job["state"] = "processing"
        log_event(f"🔹 Picked up job {job['id']} (attempt {job['attempts']})", name)
        start_time = time.time()

        # Execute command
        code, out, err = run_shell_command(job)
        success = (code == 0)
        duration = time.time() - start_time

        # Write logs
        write_job_log(job, code, out, err)

        if success:
            log_event(f"Job {job['id']} completed in {duration:.2f}s", name)
            finalize_job_after_run(job, True, out, err)
        else:
            log_event(f"Job {job['id']} failed (exit {code}). Retrying logic...", name)
            finalize_job_after_run(job, False, out, err)
            if job["state"] == "retrying":
                delay = cfg.get("backoff_base", 2) ** job["attempts"]
                log_event(f"Will retry job {job['id']} in {delay}s", name)
                if stop_event.wait(delay):
                    break

        if stop_event.wait(0.2):
            break

    log_event("Worker stopped.", name)


def start_workers(count: int) -> None:
    """Start multiple worker processes."""
    global worker_processes, stop_events
    worker_processes = []
    stop_events = []
    log_event(f"[Manager] Starting {count} worker(s)...")

    def signal_handler(sig, frame):
        log_event("[Manager] Received stop signal — shutting down workers...")
        stop_all_workers()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    for i in range(count):
        ev = Event()
        p = Process(target=worker_loop, name=f"W{i+1}", args=(ev,), daemon=True)
        p.start()
        worker_processes.append(p)
        stop_events.append(ev)
        log_event(f"Worker W{i+1} started (PID={p.pid})", "MANAGER")

    try:
        while any(p.is_alive() for p in worker_processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_all_workers()


def stop_all_workers() -> None:
    """Gracefully stop all workers."""
    log_event("[Manager] Stopping workers...", "MANAGER")
    for ev in list(stop_events):
        ev.set()
    for p in list(worker_processes):
        p.join(timeout=5)
        if p.is_alive():
            p.terminate()
            p.join()
    log_event("[Manager] All workers stopped.", "MANAGER")
