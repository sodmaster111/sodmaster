import json
from pathlib import Path

from app.crews.mktg.tasks import PLAN_CONTENT
from app.crews.mktg.tools import CampaignPlanner, ContentRepoTool, SEOAuditor


def test_campaign_planner_creates_timeline(tmp_path):
    planner = CampaignPlanner()
    roles = [["Strategist"], ["Content"]]
    tasks = [PLAN_CONTENT.to_dict()]
    payload = {
        "goals": ["increase trials"],
        "audiences": ["founders"],
        "cadence": "weekly",
    }
    packages = [
        {"topic": "ai onboarding", "stage": "ToFu", "format": "article", "channels": ["X", "dev.to"]},
        {"topic": "ai onboarding", "stage": "MoFu", "format": "playbook", "channels": ["Site Blog"]},
    ]

    campaign = planner.create_campaign(
        crew_roles=roles,
        tasks=tasks,
        payload=payload,
        content_packages=packages,
    )

    assert campaign["timeline"][0]["week"] == 1
    assert campaign["timeline"][0]["focus"] == "ai onboarding"
    assert campaign["channels"] == ["Site Blog", "X", "dev.to"]
    assert campaign["roles"] == roles


def test_content_repo_tool_writes_manifest(tmp_path):
    content_root = tmp_path / "docs" / "content"
    posts_manifest = tmp_path / "app" / "site" / "src" / "data" / "posts.json"
    tool = ContentRepoTool(content_root, posts_manifest)

    packages = [
        {"topic": "release", "stage": "ToFu", "format": "article", "channels": ["X"]},
        {"topic": "release", "stage": "BoFu", "format": "case-study", "channels": ["Site Blog"]},
    ]

    drafts = tool.write_drafts(packages, goals=["activate"], audiences=["builders"])

    assert len(drafts) == 2
    draft_paths = [Path(draft["path"]) for draft in drafts]
    for path in draft_paths:
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "stage:" in content
        assert "audiences:" in content

    manifest = json.loads(posts_manifest.read_text(encoding="utf-8"))
    assert len(manifest["posts"]) == 2
    assert manifest["posts"][0]["status"] == "draft"

    metadata = SEOAuditor().generate_metadata(drafts)
    assert set(metadata.keys()) == {draft["slug"] for draft in drafts}
