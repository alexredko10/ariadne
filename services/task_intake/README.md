# Task Intake Service

Intake-only HTTP service for accepting task requests.

This service **does not execute tasks**, **does not invoke the runner**,
**does not orchestrate agents**, **does not create run records**, and
**does not write to `.ariadne/**`**.

## Quick start

```bash
# Install the service with HTTP dependencies
pip install -e services/task_intake

# Start the server
uvicorn task_intake.server:app --port 8001

# Submit a task (accepted)
curl -X POST http://localhost:8001/submit \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Fix the login bug"}'

# Expected accepted response:
# {"status":"accepted","task_id":"task_..."}

# Submit a blank prompt (rejected)
curl -X POST http://localhost:8001/submit \
  -H "Content-Type: application/json" \
  -d '{"prompt": ""}'

# Expected rejected response:
# {"status":"rejected","reason":"Prompt must not be blank.","error_code":"blank_prompt"}
```

## Endpoints

| Method | Path                     | Description               |
|--------|--------------------------|---------------------------|
| GET    | `/health`                | Health check              |
| POST   | `/submit`                | Submit a task for intake  |
| POST   | `/task-intake/submit`    | Alias for `/submit`       |

## What this service does

- Accepts a validated task prompt and returns a `task_id`
- Returns a structured rejection with `reason` and `error_code` for invalid prompts
- Provides a health check endpoint

## What this service does NOT do

- Does **not** execute tasks
- Does **not** invoke the runner
- Does **not** orchestrate agents
- Does **not** create runner requests
- Does **not** create `run_record.yml`
- Does **not** write to `.ariadne/**`
- Does **not** store data persistently
- Does **not** require Docker
