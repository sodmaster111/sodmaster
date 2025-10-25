import json
import time
from pathlib import Path

import pytest

from app.crews.mktg.crew import MarketingCrew
from app.mktg import routes as mktg_routes


@pytest.fixture()
def temp_marketing(tmp_path):
    content_root = tmp_path / "docs" / "content"
    posts_manifest = tmp_path / "app" / "site" / "src" / "data" / "posts.json"
    campaign_output = tmp_path / "docs" / "campaign.json"
    crew = MarketingCrew(
        content_root=content_root,
        posts_manifest=posts_manifest,
        campaign_output=campaign_output,
    )
    return crew


def wait_for_job(client, job_id: str, timeout: float = 3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/v1/mktg/jobs/{job_id}")
        payload = response.json()
        if payload["status"] in {"done", "failed"}:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} did not complete in time")


def test_marketing_plan_and_publish_pipeline(client, monkeypatch, temp_marketing):
    monkeypatch.setattr(mktg_routes, "build_marketing_crew", lambda: temp_marketing)

    payload = {
        "goals": ["Grow pipeline"],
        "audiences": ["Founders", "DevOps"],
        "topics": ["launch"],
        "cadence": "weekly",
        "channels": ["X", "dev.to", "Site Blog"],
    }

    response = client.post("/api/v1/mktg/plan", json=payload)
    assert response.status_code == 202
    plan_job_id = response.json()["job_id"]

    plan_record = wait_for_job(client, plan_job_id)
    assert plan_record["status"] == "done"
    result = plan_record["result"]
    assert result["drafts"]
    assert result["plan"]["roles"]

    campaign_file = Path(result["campaign_file"])
    assert campaign_file.exists()
    manifest_path = temp_marketing.content_repo.posts_manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["posts"]

    publish_response = client.post(
        "/api/v1/mktg/publish",
        json={"plan_job_id": plan_job_id, "trigger_webdev": True},
    )
    assert publish_response.status_code == 202
    publish_job_id = publish_response.json()["job_id"]

    publish_record = wait_for_job(client, publish_job_id)
    assert publish_record["status"] == "done"
    assert publish_record["result"]["status"] == "queued"
    assert publish_record["result"]["plan_job_id"] == plan_job_id
