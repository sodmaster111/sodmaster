# Changelog

## v0.1.0 - 2025-10-25

### Added
- Exposed `/healthz`, `/readyz`, and `/version` endpoints so operators can track service liveness and deployment metadata via HTTP health probes.
- Introduced asynchronous CGO marketing campaign jobs with dedicated background processing to keep the API responsive during long-running work.
- Added `/ops/selftest` diagnostics and surfaced job store details to streamline operational triage.
- Automated an external GitHub Actions probe to verify end-to-end availability once a deployment URL is configured.
- Hardened CGO workflow resilience with standardized retries and idempotency guarantees.
- Wired webhook alerts for CGO job failures and latency SLO breaches to keep on-call teams informed.
- Instrumented Prometheus metrics, including background execution timings, and documented the `/metrics` endpoint for observability.
- Shipped a unified `start_web.sh` entrypoint to launch the service with the correct environment initialization in production.
- Delivered the A2A gateway with background execution metrics so downstream consumers can issue asynchronous requests safely.
