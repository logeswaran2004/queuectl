#!/usr/bin/env bash
# ==========================================================
# QueueCTL Core Flow Test Script
# Validates enqueue, worker, retry, DLQ, persistence.
# ==========================================================

set -e

# Auto-detect Python
if command -v python3 &>/dev/null; then
  PYTHON=python3
else
  PYTHON=python
fi

echo "Running QueueCTL Tests with $PYTHON"
echo "=========================================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Project Root: $ROOT_DIR"
echo "Python Version:"
$PYTHON --version
echo "----------------------------------------------------------"

# Clean up old test files
rm -f jobs.json dlq.json config.json logs/*.log 2>/dev/null || true
mkdir -p logs

# ----------------------------------------------------------
echo "[1] Initialize config and show defaults..."
$PYTHON -m queuectl config get || true
echo "----------------------------------------------------------"

# ----------------------------------------------------------
echo "[2] Enqueue test jobs..."
$PYTHON -m queuectl enqueue job_ok "echo Hello World"
$PYTHON -m queuectl enqueue job_fail "bash -c 'exit 1'"
$PYTHON -m queuectl list
echo "----------------------------------------------------------"

# ----------------------------------------------------------
echo "[3] Start worker (should process both jobs)..."
$PYTHON -m queuectl worker start --count 1 &
WORKER_PID=$!
sleep 5
kill $WORKER_PID 2>/dev/null || true
sleep 1
echo "----------------------------------------------------------"

# ----------------------------------------------------------
echo "[4] Check status after worker run..."
$PYTHON -m queuectl status
$PYTHON -m queuectl list
echo "----------------------------------------------------------"

# ----------------------------------------------------------
echo "[5] Simulate retries (wait and re-run worker)..."
$PYTHON -m queuectl worker start --count 1 &
WORKER_PID=$!
sleep 10
kill $WORKER_PID 2>/dev/null || true
sleep 1
echo "----------------------------------------------------------"

# ----------------------------------------------------------
echo "[6] Check DLQ (failed jobs should appear if retries exceeded)..."
$PYTHON -m queuectl dlq list || true
echo "----------------------------------------------------------"

# ----------------------------------------------------------
echo "[7] Retry a DLQ job (if exists)..."
DLQ_ID=$($PYTHON -m queuectl dlq list | grep 'job_fail' | awk '{print $2}' || true)
if [ -n "$DLQ_ID" ]; then
  echo "Retrying DLQ job $DLQ_ID..."
  $PYTHON -m queuectl dlq retry job_fail
  $PYTHON -m queuectl list
else
  echo "No DLQ jobs to retry."
fi
echo "----------------------------------------------------------"

# ----------------------------------------------------------
echo "[8] Show job logs..."
$PYTHON -m queuectl logs job_ok || true
$PYTHON -m queuectl logs job_fail || true
echo "----------------------------------------------------------"

# ----------------------------------------------------------
echo "[9] Verify persistence (restart test)..."
$PYTHON -m queuectl status
$PYTHON -m queuectl list
echo "----------------------------------------------------------"

echo "All tests executed. Check logs and DLQ output for details."
