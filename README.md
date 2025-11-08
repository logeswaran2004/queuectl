# QueueCTL – CLI-Based Background Job Queue System
Reliable and extensible command-line job queue system built in Python, allowing the users to manage background tasks efficiently, supporting multiple concurrent workers, automatic retries with exponential backoff for transient failures, and a Dead Letter Queue (DLQ) to safely store jobs that cannot be completed. With a simple CLI interface and persistent storage, QueueCTL makes it easy to enqueue, monitor, and manage jobs while ensuring robustness and traceability in your workflows.

### 1. Setup Instructions

Follow the below steps to test QueueCTL locally

#### Clone the repository
```
git clone https://github.com/logeswaran2004/queuectl.git
cd QueueCTL
```
#### Create a virtual environment - Optional
```
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```
#### Install the project in editable mode
```
pip install -e .
```
#### Verify CLI is available
```
queuectl --help
```

#### Project Structure:
```
QueueCTL/
├── queuectl/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── jobs.py
│   ├── workers.py
│   ├── dlq.py
│   └── utils.py
├── logs/
├── jobs.json
├── dlq.json
├── config.json
├── tests/
│   └── run_test.sh
└── README.md
└── setup.py
```

### 2. Usage Examples

#### Enqueue Jobs
```
$ queuectl enqueue job1 "echo Hello World"
[Success] Job 'job1' enqueued.

$ queuectl enqueue job_fail "bash -c 'exit 1'"
[Success] Job 'job_fail' enqueued.

$ queuectl enqueue job1 "echo Duplicate"
[Warning] Job 'job1' already exists.
```
#### Start Multiple Workers
```
$ queuectl worker start --count 2
[MANAGER] Starting 2 worker(s)...
[W1] Worker started.
[W2] Worker started.
[W1] Picked up job job1 (attempt 1)
[W2] Picked up job job_fail (attempt 1)
[W1] Job job1 completed in 0.02s
[W2] Job job_fail failed (exit 1). Retrying...
[W2] Will retry job job_fail in 2s
```
#### Check Status
```
$ queuectl status
=== STATUS ===
Main queue: 1 jobs
  retrying: 1
DLQ: 0 jobs
```
#### List Jobs
```
$ queuectl list
job_fail | retrying | attempts=1 | run_after=2025-11-08T15:30:03 | updated=2025-11-08T15:30:01
```
#### Dead Letter Queue
```
$ queuectl dlq list
Dead Letter Queue is empty.

$ queuectl dlq retry job_fail
No DLQ job with id 'job_fail'.
```
#### View Job Logs
```
$ queuectl logs job1
=== Run at 2025-11-08T15:30:01 ===
Command: echo Hello World
Return code: 0
Attempts: 1
STDOUT:
Hello World
STDERR:
```
#### Clear Completed Jobs
```
$ queuectl clear
Cleared 1 completed jobs.
```
#### Manage Configuration
```
$ queuectl config get
{
  "max_retries": 3,
  "backoff_base": 2
}

$ queuectl config set max_retries 5
[Config] Set max_retries = 5
```

### 3. Architecture Overview

#### Components Overview

| Component     | Responsibility                               | Key Files      |
|---------------|----------------------------------------------|----------------|
| CLI Layer     | Handles user commands (enqueue, worker, dlq)| cli.py         |
| Worker Pool   | Runs multiple workers concurrently           | workers.py     |
| Job Queue     | Stores pending/retrying jobs persistently    | jobs.py        |
| DLQ           | Holds permanently failed jobs                | dlq.py         |
| Config Manager| Manages global settings                      | config.py      |
| Logger        | Handles job-specific logs                    | utils.py       |

#### Job Lifecycle

<img width="667" height="770" alt="Architecture - QueueCTL" src="https://github.com/user-attachments/assets/f8009920-12b4-4a9d-b2e6-efae4a0b13e0" />

#### Data Persistence

- jobs.json — Main job queue
- dlq.json — Dead Letter Queue
- config.json — Global configuration
- logs/{job_id}.log — Per-job logs

#### Worker Logic

- Startup: Spawns multiple workers
- Execution: Picks and runs jobs
- Retry: Exponential backoff for failed jobs
- DLQ Handling: Moves jobs exceeding retries to DLQ
- Shutdown: Gracefully stops after current job

### 4. Assumptions & Trade-offs

| Aspect       | Assumption / Trade-off                  |
|--------------|----------------------------------------|
| Persistence  | Uses JSON files for simplicity         |
| Concurrency  | File locks ensure safe parallel access |
| Scheduling   | Only exponential backoff; no cron      |
| Security     | Commands are trusted; no sandboxing    |
| Retry Policy | DLQ retries reset attempts             |

### 5. Testing Section and Demo

#### Automated Test
```
bash tests/run_test.sh
```
This validates the below list of tasks:
- Enqueue and completion
- Worker processing
- Retry and backoff
- DLQ handling
- Data persistence

#### Manual Test
```
queuectl enqueue job1 "echo Hello"
queuectl worker start --count 2
queuectl status
queuectl list
queuectl dlq list
```

#### Demo

https://github.com/user-attachments/assets/d46c7f0a-6a10-4da3-81d8-b8475b6bb1e3
