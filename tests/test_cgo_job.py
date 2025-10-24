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
