"""Orchestration pipeline for the Web Development crew."""

from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.crews.webdev.roles import ALL_ROLES, RoleSpec
from app.crews.webdev.tools import LinkCheckTool, MetricsPush, RepoWriterTool, SiteBuildTool
from app.site.helpers.content import PageArtifact

logger = logging.getLogger(__name__)


class PageInput(BaseModel):
    slug: str
    title: str
    body: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    layout: str = "BaseLayout"
    format: str = "astro"

    @field_validator("format")
    @classmethod
    def _validate_format(cls, value: str) -> str:
        supported = {"astro", "md", "markdown"}
        if value.lower() not in supported:
            raise ValueError(f"Unsupported format '{value}'. Allowed: {sorted(supported)}")
        return value.lower()

    def to_artifact(self) -> PageArtifact:
        extension = ".astro" if self.format == "astro" else ".md"
        return PageArtifact(
            slug=self.slug,
            title=self.title,
            body=self.body,
            description=self.description,
            tags=list(self.tags),
            canonical_url=self.canonical_url,
            layout=self.layout,
            extension=extension,
        )


class WebDevPayload(BaseModel):
    pages: List[PageInput] = Field(default_factory=list)
    components: List[Dict[str, Any]] = Field(default_factory=list)
    layout_prefs: Dict[str, Any] = Field(default_factory=dict)


class WebDevCrew:
    """Execute the deterministic pipeline for the webdev department."""

    def __init__(
        self,
        project_root: Path = Path("app/site"),
        dist_root: Path = Path("app/site/dist"),
        roles: Optional[List[RoleSpec]] = None,
    ) -> None:
        self.project_root = project_root
        self.repo_writer = RepoWriterTool(project_root)
        self.site_builder = SiteBuildTool(project_root)
        self.link_checker = LinkCheckTool(dist_root)
        self.metrics = MetricsPush(crew="webdev")
        self.roles = roles or list(ALL_ROLES)

    def kickoff(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        payload = WebDevPayload.model_validate(inputs)
        start = perf_counter()
        self.metrics.job_started()
        try:
            plan = self._plan(payload)
            artifacts = self._implement(payload)
            validation = self._validate()
            report = self._summarise(plan, artifacts, validation)
        except Exception:
            duration = perf_counter() - start
            self.metrics.job_failed(duration)
            logger.exception("WebDev crew pipeline failed")
            raise

        duration = perf_counter() - start
        self.metrics.job_succeeded(duration)
        report["duration_seconds"] = duration
        return report

    def _plan(self, payload: WebDevPayload) -> Dict[str, Any]:
        navigation = [
            {
                "slug": page.slug,
                "title": page.title,
                "format": page.format,
            }
            for page in payload.pages
        ]
        role_notes = [role.as_bullet_points() for role in self.roles]
        return {"navigation": navigation, "roles": role_notes}

    def _implement(self, payload: WebDevPayload) -> Dict[str, Any]:
        generated_pages: List[str] = []
        for page in payload.pages:
            artifact = page.to_artifact()
            path = self.repo_writer.write_page(artifact)
            generated_pages.append(str(path.relative_to(self.project_root)))

        data_manifest: Dict[str, Any] = {
            "components": payload.components,
            "layout": payload.layout_prefs,
        }
        data_path = self.repo_writer.write_json("generated/webdev-manifest.json", data_manifest)
        return {
            "pages": generated_pages,
            "data_files": [str(data_path.relative_to(self.project_root))],
        }

    def _validate(self) -> Dict[str, Any]:
        build_result = self.site_builder.run()
        link_results = self.link_checker.run()
        broken_links = [
            {
                "file": str(result.file),
                "links": result.broken_links,
            }
            for result in link_results
        ]
        return {"build": build_result, "broken_links": broken_links}

    def _summarise(
        self,
        plan: Dict[str, Any],
        artifacts: Dict[str, Any],
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        summary_lines = [
            "WebDev crew execution completed",
            f"Pages generated: {len(artifacts['pages'])}",
            f"Data files updated: {len(artifacts['data_files'])}",
        ]
        if validation["broken_links"]:
            summary_lines.append(
                f"Link checker found {len(validation['broken_links'])} issues"
            )
        else:
            summary_lines.append("Link checker passed with no issues")
        return {
            "plan": plan,
            "artifacts": artifacts,
            "validation": validation,
            "summary": "\n".join(summary_lines),
        }


def build_webdev_crew() -> WebDevCrew:
    """Factory to construct the crew with repository defaults."""

    project_root = Path("app/site").resolve()
    dist_root = project_root / "dist"
    return WebDevCrew(project_root=project_root, dist_root=dist_root)


__all__ = [
    "WebDevCrew",
    "WebDevPayload",
    "build_webdev_crew",
]
