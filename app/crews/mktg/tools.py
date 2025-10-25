"""Utility helpers used by the Marketing crew pipeline."""

from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from app.metrics import record_crew_job_duration, record_crew_job_status

logger = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return cleaned or "draft"


class ContentRepoTool:
    """Persist markdown drafts and posts manifest for marketing content."""

    def __init__(self, content_root: Path, posts_manifest: Path) -> None:
        self.content_root = content_root
        self.posts_manifest = posts_manifest
        self.content_root.mkdir(parents=True, exist_ok=True)
        self.posts_manifest.parent.mkdir(parents=True, exist_ok=True)

    def write_drafts(
        self,
        packages: Sequence[Dict[str, str]],
        goals: Sequence[str],
        audiences: Sequence[str],
    ) -> List[Dict[str, str]]:
        """Write markdown drafts and update the posts manifest."""

        records: List[Dict[str, str]] = []
        manifest = self._load_manifest()
        existing_posts = {item["slug"]: item for item in manifest.get("posts", [])}

        for package in packages:
            topic = package["topic"]
            stage = package["stage"]
            format_hint = package.get("format", "article")
            title = f"{topic.title()} — {stage}"
            slug = _slugify(f"{topic}-{stage}")
            filename = f"{slug}.md"
            path = self.content_root / filename
            body = self._render_markdown(
                title=title,
                stage=stage,
                topic=topic,
                format_hint=format_hint,
                channels=package.get("channels", []),
                goals=goals,
                audiences=audiences,
            )
            path.write_text(body, encoding="utf-8")
            logger.info(
                "ContentRepoTool | wrote draft",
                extra={"slug": slug, "path": str(path)},
            )

            record = {
                "slug": slug,
                "title": title,
                "stage": stage,
                "channels": package.get("channels", []),
                "format": format_hint,
                "status": "draft",
                "path": str(path),
            }
            records.append(record)
            existing_posts[slug] = {
                "slug": slug,
                "title": title,
                "stage": stage,
                "channels": package.get("channels", []),
                "format": format_hint,
                "status": "draft",
            }

        manifest["posts"] = sorted(existing_posts.values(), key=lambda item: item["slug"])
        self._write_manifest(manifest)
        return records

    def _load_manifest(self) -> Dict[str, List[Dict[str, str]]]:
        if self.posts_manifest.exists():
            try:
                return json.loads(self.posts_manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning(
                    "ContentRepoTool | corrupt manifest, recreating",
                    extra={"path": str(self.posts_manifest)},
                )
        return {"posts": []}

    def _write_manifest(self, payload: Dict[str, List[Dict[str, str]]]) -> None:
        self.posts_manifest.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _render_markdown(
        self,
        *,
        title: str,
        stage: str,
        topic: str,
        format_hint: str,
        channels: Iterable[str],
        goals: Sequence[str],
        audiences: Sequence[str],
    ) -> str:
        frontmatter = ["---"]
        frontmatter.append(f"title: {title}")
        frontmatter.append(f"stage: {stage}")
        frontmatter.append(f"format: {format_hint}")
        if channels:
            frontmatter.append("channels:")
            frontmatter.extend([f"  - {channel}" for channel in channels])
        if goals:
            frontmatter.append("goals:")
            frontmatter.extend([f"  - {goal}" for goal in goals])
        if audiences:
            frontmatter.append("audiences:")
            frontmatter.extend([f"  - {aud}" for aud in audiences])
        frontmatter.append("---")
        body = [
            "## Narrative",
            f"Focus topic: **{topic}**",
            "",
            "## Key Points",
            "- Draft key point placeholder",
            "- CTA placeholder",
        ]
        return "\n".join(frontmatter + [""] + body) + "\n"


class CampaignPlanner:
    """Create a structured campaign JSON payload."""

    def create_campaign(
        self,
        *,
        crew_roles: Sequence[Sequence[str]],
        tasks: Sequence[Dict[str, object]],
        payload: Dict[str, object],
        content_packages: Sequence[Dict[str, str]],
    ) -> Dict[str, object]:
        today = date.today()
        cadence = str(payload.get("cadence", "weekly"))
        timeline = [
            {
                "week": index + 1,
                "start_date": (today + timedelta(weeks=index)).isoformat(),
                "focus": package["topic"],
                "stage": package["stage"],
            }
            for index, package in enumerate(content_packages)
        ]
        channels = sorted({channel for package in content_packages for channel in package.get("channels", [])})
        campaign = {
            "goals": list(payload.get("goals", [])),
            "audiences": list(payload.get("audiences", [])),
            "cadence": cadence,
            "channels": channels,
            "timeline": timeline,
            "roles": [list(bullets) for bullets in crew_roles],
            "tasks": list(tasks),
        }
        return campaign


class SEOAuditor:
    """Derive simple metadata fields for marketing drafts."""

    def generate_metadata(self, drafts: Sequence[Dict[str, str]]) -> Dict[str, Dict[str, object]]:
        metadata: Dict[str, Dict[str, object]] = {}
        for draft in drafts:
            slug = draft["slug"]
            title = draft["title"]
            description = f"{title} — actionable insights for {', '.join(draft.get('channels', []) or ['core audience'])}."
            tags = [draft.get("stage", "funnel"), draft.get("format", "content")] + [
                channel.replace(" ", "-").lower() for channel in draft.get("channels", [])
            ]
            metadata[slug] = {
                "title": title,
                "description": description,
                "og": {
                    "title": title,
                    "description": description,
                },
                "tags": sorted(set(tags)),
            }
        return metadata


class MetricsPush:
    """Prometheus helper for marketing crew executions."""

    def __init__(self, crew: str = "mktg") -> None:
        self.crew = crew

    def job_started(self) -> None:
        record_crew_job_status(self.crew, "running")

    def job_succeeded(self, duration_seconds: float) -> None:
        record_crew_job_status(self.crew, "done")
        record_crew_job_duration(self.crew, duration_seconds)

    def job_failed(self, duration_seconds: float) -> None:
        record_crew_job_status(self.crew, "failed")
        record_crew_job_duration(self.crew, duration_seconds)


__all__ = [
    "CampaignPlanner",
    "ContentRepoTool",
    "MetricsPush",
    "SEOAuditor",
]
