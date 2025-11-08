# queuectl/cli.py
"""
CLI entry point for QueueCTL.
Uses argparse to handle commands and dispatch to appropriate modules.
"""

import argparse
import sys

from .config import ensure_config, config_get, config_set
from .jobs import enqueue, list_jobs, clear_completed
from .utils import status, show_logs
from .dlq import list_dlq, retry_dlq_job
from .workers import start_workers

def main() -> None:
    """Main CLI handler."""
    # Ensure config exists
    ensure_config()

    parser = argparse.ArgumentParser(prog="queuectl", description="QueueCTL - job queue")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # enqueue
    en = sub.add_parser("enqueue", help="enqueue a job")
    en.add_argument("id")
    en.add_argument("command", nargs="+", help="command (shell)")

    # worker
    w = sub.add_parser("worker", help="worker control")
    ws = w.add_subparsers(dest="worker_cmd", required=True)
    start = ws.add_parser("start", help="start workers")
    start.add_argument("--count", type=int, default=1)
    ws.add_parser("stop", help="stop (not implemented for external processes)")

    # list / status / logs / clear
    ls = sub.add_parser("list", help="list jobs")
    ls.add_argument("--state", help="filter by state", choices=["pending", "processing", "completed", "retrying"], default=None)
    sub.add_parser("status", help="show status")
    lg = sub.add_parser("logs", help="show job logs")
    lg.add_argument("job_id")
    sub.add_parser("clear", help="clear completed jobs")

    # dlq
    d = sub.add_parser("dlq", help="dead letter queue")
    ds = d.add_subparsers(dest="dlq_cmd", required=True)
    ds.add_parser("list", help="list dlq")
    dr = ds.add_parser("retry", help="retry dlq job")
    dr.add_argument("job_id")

    # config
    c = sub.add_parser("config", help="configuration")
    cs = c.add_subparsers(dest="config_cmd", required=True)
    cget = cs.add_parser("get", help="get config or key")
    cget.add_argument("--key", help="key name", default=None)
    cset = cs.add_parser("set", help="set config key")
    cset.add_argument("key")
    cset.add_argument("value")

    if len(sys.argv) == 1:
        print("queuectl — run with --help to see commands.")
        return

    args = parser.parse_args()

    if args.cmd == "enqueue":
        enqueue(args.id, " ".join(args.command))
    elif args.cmd == "worker":
        if args.worker_cmd == "start":
            start_workers(args.count)
        else:
            print("Use manager process to stop (Ctrl+C).")
    elif args.cmd == "list":
        list_jobs(state=args.state)
    elif args.cmd == "status":
        status()
    elif args.cmd == "logs":
        show_logs(args.job_id)
    elif args.cmd == "clear":
        clear_completed()
    elif args.cmd == "dlq":
        if args.dlq_cmd == "list":
            list_dlq()
        elif args.dlq_cmd == "retry":
            retry_dlq_job(args.job_id)
    elif args.cmd == "config":
        if args.config_cmd == "get":
            config_get(args.key)
        elif args.config_cmd == "set":
            # try to cast to int/float if appropriate
            val = args.value
            try:
                v = int(val)
            except ValueError:
                try:
                    v = float(val)
                except ValueError:
                    v = val
            config_set(args.key, v)