import json
import time
from pathlib import Path
from typing import Any, Dict

import pytest

from app.crews.webdev.crew import WebDevCrew
from app.webdev import routes as webdev_routes


@pytest.fixture()
def temp_site(tmp_path):
    site_root = tmp_path / "site"
    (site_root / "src" / "pages").mkdir(parents=True)
    (site_root / "src" / "layouts").mkdir(parents=True)
    (site_root / "src" / "data").mkdir(parents=True)
    (site_root / "dist").mkdir(parents=True)
    (site_root / "src" / "layouts" / "BaseLayout.astro").write_text(
        "---\nconst page = Astro.props;\n---\n<slot />\n"
    )
    return site_root


def wait_for_job(client, job_id: str, timeout: float = 3.0) -> Dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/v1/webdev/jobs/{job_id}")
        payload = response.json()
        if payload["status"] in {"done", "failed"}:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} did not complete in time")


def test_generate_site_pipeline(client, monkeypatch, temp_site):
    crew = WebDevCrew(project_root=temp_site, dist_root=temp_site / "dist")
    monkeypatch.setattr(webdev_routes, "build_webdev_crew", lambda: crew)
    monkeypatch.delenv("ENABLE_SITE_CI", raising=False)

    payload = {
        "pages": [
            {
                "slug": "press/launch",
                "title": "Launch",
                "body": "# Launch\nThis is the launch announcement.",
            },
            {
                "slug": "press/briefing",
                "title": "Briefing",
                "body": "# Briefing\nAgenda soon.",
                "format": "md",
            },
        ],
        "components": [{"name": "PressHero", "status": "beta"}],
        "layout_prefs": {"cta": {"href": "/contact/"}},
    }

    response = client.post("/api/v1/webdev/generate-site", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job_payload = wait_for_job(client, job_id)
    assert job_payload["status"] == "done"
    result = job_payload["result"]
    assert "summary" in result
    assert result["artifacts"]["pages"]
    assert result["scaffold"]["pages"][0]["slug"] == "press/launch"

    generated = temp_site / "src" / "pages" / "press" / "launch.astro"
    assert generated.exists()
    markdown = temp_site / "src" / "pages" / "press" / "briefing.md"
    assert markdown.exists()
    assert "layout:" in markdown.read_text()
    manifest = temp_site / "src" / "data" / "generated" / "webdev-manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text())
    assert data["components"][0]["name"] == "PressHero"


def test_sync_content_reads_repo_docs(client):
    doc_path = Path("docs/webdev-sync-smoke.md")
    doc_path.write_text("# Sync Smoke\nBody")
    try:
        response = client.post("/api/v1/webdev/sync-content")
        assert response.status_code == 200
        payload = response.json()
        titles = {page["title"] for page in payload["pages"]}
        assert "Sync Smoke" in titles
    finally:
        doc_path.unlink(missing_ok=True)
