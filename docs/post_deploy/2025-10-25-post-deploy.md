# 2025-10-25 Post-deploy verification

## Endpoint checks
- `GET / -> 200`
- `HEAD / -> 200`

## Selftest snapshot
- Overall status: `ok`
- Job store backend: `memory` (redis_connected=false)
- Crew tools: `available`
- CGO flow: submit=ok → poll=ok
- A2A flow: submit=ok → poll=ok

## Runtime error check
- `RuntimeError: Response content shorter than Content-Length` not present in the captured logs.

## Log excerpt (last 100 lines)
```
  "a2a_poll": {
    "duration_ms": 1,
    "http_status": 200,
    "method": "GET",
    "path": "/a2a/jobs/2b53fa26-fe97-4a0e-9db4-bb35199858b2",
    "response": {
      "job_id": "2b53fa26-fe97-4a0e-9db4-bb35199858b2",
      "result": {
        "echo": {},
        "status": "pong"
      },
      "status": "done"
    },
    "status": "ok"
  },
  "a2a_submit": {
    "duration_ms": 166,
    "http_status": 202,
    "method": "POST",
    "path": "/a2a/command",
    "response": {
      "job_id": "2b53fa26-fe97-4a0e-9db4-bb35199858b2",
      "result": null,
      "status": "accepted"
    },
    "status": "ok"
  },
  "cgo_poll": {
    "duration_ms": 1,
    "http_status": 200,
    "method": "GET",
    "path": "/api/v1/cgo/jobs/b5990c2a-2d6f-4062-b9c5-0fe98c379b39",
    "response": {
      "job_id": "b5990c2a-2d6f-4062-b9c5-0fe98c379b39",
      "result": {
        "inputs": {},
        "origin": "selftest",
        "status": "ok"
      },
      "status": "done"
    },
    "status": "ok"
  },
  "cgo_submit": {
    "duration_ms": 3,
    "http_status": 202,
    "method": "POST",
    "path": "/api/v1/cgo/run-marketing-campaign",
    "response": {
      "job_id": "b5990c2a-2d6f-4062-b9c5-0fe98c379b39",
      "result": null,
      "status": "accepted"
    },
    "status": "ok"
  },
  "healthz": {
    "duration_ms": 6,
    "http_status": 200,
    "method": "GET",
    "path": "/healthz",
    "response": {
      "status": "ok"
    },
    "status": "ok"
  },
  "meta": {
    "crew_tools": "available",
    "duration_ms": 4150,
    "finished_at": "2025-10-25T09:33:02.454865+00:00",
    "job_store": "memory",
    "overall_status": "ok",
    "redis_connected": false,
    "started_at": "2025-10-25T09:32:58.304047+00:00"
  },
  "readyz": {
    "duration_ms": 1,
    "http_status": 200,
    "method": "GET",
    "path": "/readyz",
    "response": {
      "dependencies_ready": true,
      "status": "ok"
    },
    "status": "ok"
  },
  "redis_connected": false,
  "store": "memory",
  "version": {
    "duration_ms": 1,
    "http_status": 200,
    "method": "GET",
    "path": "/version",
    "response": {
      "build_time": "2025-10-25T09:32:58Z",
      "git_sha": "unknown",
      "python": "3.11.12"
    },
    "status": "ok"
  }
}
```
