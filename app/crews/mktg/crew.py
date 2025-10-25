"""Marketing crew orchestration pipeline."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field, field_validator

from app.crews.mktg.roles import ALL_ROLES, RoleSpec
from app.crews.mktg.tasks import ALL_TASKS, TaskSpec
from app.crews.mktg.tools import CampaignPlanner, ContentRepoTool, MetricsPush, SEOAuditor

logger = logging.getLogger(__name__)


class MarketingPayload(BaseModel):
    """Input payload describing the marketing brief."""

    goals: List[str] = Field(default_factory=list)
    audiences: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    cadence: str = "bi-weekly"
    channels: List[str] = Field(default_factory=list)

    @field_validator("cadence")
    @classmethod
    def _normalize_cadence(cls, value: str) -> str:
        return value.strip() or "bi-weekly"

    @field_validator("channels", mode="before")
    @classmethod
    def _ensure_channels(cls, value: Any) -> Sequence[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)


class MarketingCrew:
    """Deterministic execution of the marketing workflow."""

    def __init__(
        self,
        *,
        content_root: Path = Path("docs/content"),
        posts_manifest: Path = Path("app/site/src/data/posts.json"),
        campaign_output: Path = Path("docs/campaign.json"),
        roles: Optional[List[RoleSpec]] = None,
        tasks: Optional[List[TaskSpec]] = None,
    ) -> None:
        self.roles = roles or list(ALL_ROLES)
        self.tasks = tasks or list(ALL_TASKS)
        self.content_repo = ContentRepoTool(content_root, posts_manifest)
        self.campaign_output = campaign_output
        self.campaign_output.parent.mkdir(parents=True, exist_ok=True)
        self.campaign_planner = CampaignPlanner()
        self.seo_auditor = SEOAuditor()
        self.metrics = MetricsPush(crew="mktg")

    def kickoff(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        payload = MarketingPayload.model_validate(inputs)
        start = perf_counter()
        self.metrics.job_started()
        logger.info("MarketingCrew | kickoff", extra={"topics": payload.topics})

        try:
            matrix = self._build_content_matrix(payload)
            drafts = self.content_repo.write_drafts(matrix, payload.goals, payload.audiences)
            metadata = self.seo_auditor.generate_metadata(drafts)
            campaign = self.campaign_planner.create_campaign(
                crew_roles=[role.as_bullet_points() for role in self.roles],
                tasks=[task.to_dict() for task in self.tasks],
                payload=payload.model_dump(),
                content_packages=matrix,
            )
            campaign_path = self._write_campaign(campaign)
            summary = self._summarise(payload, drafts, campaign_path)
        except Exception:
            duration = perf_counter() - start
            self.metrics.job_failed(duration)
            logger.exception("MarketingCrew | pipeline failed")
            raise

        duration = perf_counter() - start
        self.metrics.job_succeeded(duration)
        summary["duration_seconds"] = duration
        summary["metadata"] = metadata
        summary["campaign"] = campaign
        summary["content_matrix"] = matrix
        return summary

    def _build_content_matrix(self, payload: MarketingPayload) -> List[Dict[str, str]]:
        stages = [
            ("ToFu", "article"),
            ("MoFu", "playbook"),
            ("BoFu", "case-study"),
        ]
        matrix: List[Dict[str, str]] = []
        channels = payload.channels or [
            "Telegram Mini App",
            "Site Blog",
            "dev.to",
            "X",
            "HackerNews",
        ]
        for topic in payload.topics or ["product-update"]:
            for index, (stage, format_hint) in enumerate(stages):
                package_channels = list(channels)
                if stage == "BoFu":
                    package_channels = [channel for channel in channels if channel not in {"HackerNews"}] or list(channels)
                matrix.append(
                    {
                        "topic": topic,
                        "stage": stage,
                        "format": format_hint,
                        "channels": package_channels,
                        "sequence": index + 1,
                    }
                )
        return matrix

    def _write_campaign(self, campaign: Dict[str, Any]) -> Path:
        self.campaign_output.write_text(json.dumps(campaign, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logger.info(
            "MarketingCrew | wrote campaign",
            extra={"path": str(self.campaign_output)},
        )
        return self.campaign_output

    def _summarise(
        self,
        payload: MarketingPayload,
        drafts: Sequence[Dict[str, str]],
        campaign_path: Path,
    ) -> Dict[str, Any]:
        branch = f"web/content-{date.today().strftime('%Y%m%d')}"
        return {
            "plan": {
                "goals": payload.goals,
                "audiences": payload.audiences,
                "cadence": payload.cadence,
                "roles": [role.as_bullet_points() for role in self.roles],
                "tasks": [task.to_dict() for task in self.tasks],
            },
            "drafts": [
                {
                    "slug": draft["slug"],
                    "path": draft["path"],
                    "stage": draft["stage"],
                    "channels": draft["channels"],
                }
                for draft in drafts
            ],
            "campaign_file": str(campaign_path),
            "pr_branch": branch,
        }


def build_marketing_crew() -> MarketingCrew:
    """Factory constructing the marketing crew with repo defaults."""

    content_root = Path("docs/content").resolve()
    posts_manifest = Path("app/site/src/data/posts.json").resolve()
    campaign_output = Path("docs/campaign.json").resolve()
    return MarketingCrew(
        content_root=content_root,
        posts_manifest=posts_manifest,
        campaign_output=campaign_output,
    )


__all__ = [
    "MarketingCrew",
    "MarketingPayload",
    "build_marketing_crew",
]
