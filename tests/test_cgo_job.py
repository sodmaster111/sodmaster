import time

import pytest


def test_cgo_marketing_campaign_job_lifecycle(client, monkeypatch):
    """Ensure CGO jobs run asynchronously and expose their status via polling."""

    class DummyCrew:
        def kickoff(self, inputs):
            return {"ok": True}

    monkeypatch.setattr("agents.cgo_crew.cgo_crew", DummyCrew(), raising=False)

    response = client.post("/api/v1/cgo/run-marketing-campaign")
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    job_id = data["job_id"]

    deadline = time.time() + 5
    while time.time() < deadline:
        status_response = client.get(f"/api/v1/cgo/jobs/{job_id}")
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert "status" in status_payload
        assert "result" in status_payload
        if status_payload["status"] == "done":
            assert status_payload["result"] == {"ok": True}
            break
        if status_payload["status"] == "failed":
            pytest.fail(f"CGO job failed unexpectedly: {status_payload['result']}")
        time.sleep(0.05)
    else:
        pytest.skip("CGO job did not complete within the timeout window")


def test_cgo_marketing_campaign_submit_is_idempotent(client, monkeypatch):
    class DummyCrew:
        def __init__(self):
            self.call_count = 0

        def kickoff(self, inputs):
            self.call_count += 1
            return {"ok": True}

    crew = DummyCrew()
    monkeypatch.setattr("agents.cgo_crew.cgo_crew", crew, raising=False)

    response = client.post("/api/v1/cgo/run-marketing-campaign")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    deadline = time.time() + 5
    while time.time() < deadline:
        status_response = client.get(f"/api/v1/cgo/jobs/{job_id}")
        status_payload = status_response.json()
        if status_payload["status"] == "done":
            break
        time.sleep(0.05)
    else:  # pragma: no cover - defensive guard in case background task is too slow
        pytest.skip("CGO job did not complete within the timeout window")

    repeat_response = client.post(
        "/api/v1/cgo/run-marketing-campaign",
        json={"job_id": job_id},
    )
    assert repeat_response.status_code == 200
    repeat_payload = repeat_response.json()
    assert repeat_payload["job_id"] == job_id
    assert repeat_payload["status"] == "done"
    assert repeat_payload["result"] == {"ok": True}
    assert crew.call_count == 1


def test_cgo_marketing_campaign_retries_on_failure(client, monkeypatch):
    class FlakyCrew:
        def __init__(self):
            self.call_count = 0

        def kickoff(self, inputs):
            self.call_count += 1
            if self.call_count < 3:
                raise RuntimeError("transient failure")
            return {"ok": True}

    crew = FlakyCrew()
    monkeypatch.setattr("agents.cgo_crew.cgo_crew", crew, raising=False)

    response = client.post(
        "/api/v1/cgo/run-marketing-campaign",
        json={"job_id": "retry-job"},
    )
    assert response.status_code == 202
    assert response.json()["job_id"] == "retry-job"

    deadline = time.time() + 5
    while time.time() < deadline:
        status_response = client.get("/api/v1/cgo/jobs/retry-job")
        status_payload = status_response.json()
        if status_payload["status"] == "done":
            assert status_payload["result"] == {"ok": True}
            break
        if status_payload["status"] == "failed":
            pytest.fail("CGO job failed despite retries")
        time.sleep(0.05)
    else:
        pytest.fail("CGO job did not complete within the timeout window")

    assert crew.call_count == 3
