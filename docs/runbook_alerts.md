# Alerts SLO Runbook

This runbook covers the operational workflow for job failure and latency alerts.

## Alert feed

Alerts are sent to the webhook configured via the `ALERT_WEBHOOK` environment
variable. If the variable is empty or unset, alerts are skipped.

### Events

| Event                 | Trigger condition                                    | Payload fields                                                    |
| --------------------- | ----------------------------------------------------- | ----------------------------------------------------------------- |
| `job_failed`          | CGO job execution raises an exception                 | `job_id`, `reason`                                                |
| `latency_slo_miss`    | Job runtime exceeds the `SLO_JOB_SEC` latency target | `job_id`, `duration_sec`, `threshold_sec`                         |
| `guardrail_violation` | Guardrail breach (`cgo-job-failure`, `a2a-command-failure`) | `guardrail_id`, `reason`, `event`, `subject`                       |

## Triage checklist

1. Confirm the alert details in the receiving system (Slack, PagerDuty, etc.).
2. Retrieve the job metadata:
   ```bash
   http GET "$API_BASE_URL/ops/cgo/jobs/<job_id>"
   ```
3. Review application logs for correlated events:
   ```bash
   kubectl logs deploy/sodmaster-app -c api --since=30m | rg "job_id=<job_id>"
   ```
4. Inspect metrics in the monitoring dashboard:
   * `cgo_job_duration_seconds` histogram (latency trends)
   * `cgo_job_status_total` counter (job success/failure rates)

## Remediation playbooks

### Job failure (`job_failed`)

1. Verify whether the failure is transient (network, upstream API) or
   deterministic (validation, code error).
2. For transient issues, retry the job:
   ```bash
   http POST "$API_BASE_URL/ops/cgo/run-marketing-campaign" job_id=<job_id>
   ```
3. For deterministic issues, file or update an incident ticket and coordinate
   with the owning team for a code fix.

### Latency SLO breach (`latency_slo_miss`)

1. Check concurrent job load and worker resource utilization.
2. Review downstream integrations for increased response times.
3. If the latency spike is due to a single job, re-run it to confirm whether the
   delay reproduces.
4. Escalate to the platform team when multiple jobs breach consecutively or the
   median latency stays above target for 15 minutes.

## Configuration changes

* `SLO_JOB_SEC` (default: `60` seconds) controls the latency SLO threshold.
  Update the deployment environment variable and redeploy to change the target.
* `ALERT_WEBHOOK` controls where alerts are delivered. Update the environment
  variable with the desired HTTPS endpoint. Leave it empty to disable alerts in
  non-production environments.

Always document changes in the service change log and notify on-call operators
about threshold adjustments.
