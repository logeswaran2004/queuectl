# queuectl/config.py
"""
Configuration management for QueueCTL.
Handles loading, saving, and accessing config, as well as file locking and JSON I/O.
"""

import json
import os
from datetime import datetime, timezone
from filelock import FileLock, Timeout
from typing import Any, Dict, List

# Constants
CONFIG_FILE = "config.json"
JOB_FILE = "jobs.json"
DLQ_FILE = "dlq.json"
LOG_DIR = "logs"
LOCK_TIMEOUT = 5  # seconds

# File locks (lazy initialized)
_job_lock = None
_dlq_lock = None
_config_lock = None

DEFAULT_CONFIG = {"max_retries": 3, "backoff_base": 2}

def get_locks():
    """Initialize and return file locks."""
    global _job_lock, _dlq_lock, _config_lock
    if _job_lock is None:
        _job_lock = FileLock(JOB_FILE + ".lock")
        _dlq_lock = FileLock(DLQ_FILE + ".lock")
        _config_lock = FileLock(CONFIG_FILE + ".lock")
    return _job_lock, _dlq_lock, _config_lock

def now_iso() -> str:
    """Return current ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()

def parse_iso(s: str) -> datetime | None:
    """Parse ISO string to datetime."""
    return datetime.fromisoformat(s) if s else None

def safe_load_json(path: str, lock: FileLock) -> List[Dict[str, Any]]:
    """Safely load JSON from file with locking."""
    try:
        with lock.acquire(timeout=LOCK_TIMEOUT):
            if not os.path.exists(path):
                return []
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
    except Timeout:
        print(f"[Warning] timeout acquiring lock for read: {path}")
        return []

def safe_write_json(path: str, data: List[Dict[str, Any]], lock: FileLock) -> None:
    """Safely write JSON to file with locking."""
    try:
        with lock.acquire(timeout=LOCK_TIMEOUT):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    except Timeout:
        print(f"[Error] timeout acquiring lock for write: {path}")

def ensure_config() -> Dict[str, Any]:
    """Ensure config file exists with defaults."""
    cfg = safe_load_json(CONFIG_FILE, get_locks()[2])
    if not cfg:
        cfg = DEFAULT_CONFIG.copy()
        safe_write_json(CONFIG_FILE, cfg, get_locks()[2])
    return cfg

def config_get(key: str = None) -> None:
    """Get and print config value or entire config."""
    cfg = ensure_config()
    if key:
        print(cfg.get(key))
    else:
        print(json.dumps(cfg, indent=2))

def config_set(key: str, value: Any) -> None:
    """Set config key-value pair."""
    cfg = ensure_config()
    cfg[key] = value
    safe_write_json(CONFIG_FILE, cfg, get_locks()[2])
    print(f"[Config] Set {key} = {value}")

def load_config() -> dict:
    """Load and return the current configuration dictionary."""
    cfg = safe_load_json(CONFIG_FILE, get_locks()[2])
    if not cfg:
        cfg = DEFAULT_CONFIG.copy()
    return cfg

# Initialize directories
os.makedirs(LOG_DIR, exist_ok=True)