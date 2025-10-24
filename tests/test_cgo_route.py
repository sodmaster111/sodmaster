from fastapi.testclient import TestClient

from app.cgo import routes
from app.main import app
from app.services.tasks import task_results


def test_run_marketing_campaign(monkeypatch):
    task_results.clear()
    calls = {}

    def fake_run_crew_task(crew, task_id, inputs):
        calls["task_id"] = task_id
        calls["inputs"] = inputs
        task_results[task_id] = {"status": "complete"}

    monkeypatch.setattr(routes, "run_crew_task", fake_run_crew_task)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cgo/run-marketing-campaign",
            json={"campaign_name": "Launch", "parameters": {"region": "EU"}},
        )

    assert response.status_code in (200, 202)
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data
    assert data["job_id"].startswith("cgo_job_")
    assert calls["task_id"] == data["job_id"]
    assert calls["inputs"] == {"campaign_name": "Launch", "parameters": {"region": "EU"}}
    assert task_results[data["job_id"]]["status"] in {"queued", "complete"}
