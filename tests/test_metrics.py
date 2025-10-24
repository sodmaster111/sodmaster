import time

def test_metrics_endpoint_exports_prometheus_counters(client, monkeypatch):
    class DummyCrew:
        def kickoff(self, inputs):
            return {"ok": True}

    monkeypatch.setattr("agents.cgo_crew.cgo_crew", DummyCrew(), raising=False)

    response = client.post("/api/v1/cgo/run-marketing-campaign")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    deadline = time.time() + 5
    while time.time() < deadline:
        status_response = client.get(f"/api/v1/cgo/jobs/{job_id}")
        if status_response.json()["status"] == "done":
            break
        time.sleep(0.05)
    else:  # pragma: no cover - defensive guard for slow CI environments
        raise AssertionError("CGO job did not finish in time for metrics test")

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    body = metrics_response.text

    assert body.strip(), "Metrics payload should not be empty"
    assert "cgo_jobs_total" in body
    assert 'status="accepted"' in body
    assert "cgo_job_duration_seconds_count" in body
    assert "http_requests_total" in body
    assert "app_info" in body
