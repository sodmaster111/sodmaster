"""Utility tools used by the Web Development crew pipeline."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.metrics import (
    record_crew_job_duration,
    record_crew_job_status,
    record_http_request,
)
from app.site.helpers.content import (
    PageArtifact,
    ensure_page_path,
    render_page_source,
)

logger = logging.getLogger(__name__)


class RepoWriterTool:
    """Write generated content into the Astro project structure."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.pages_root = project_root / "src" / "pages"
        self.data_root = project_root / "src" / "data"

    def scaffold_page(self, artifact: PageArtifact) -> Path:
        """Ensure directories for a page exist and report the target path."""

        target_path = ensure_page_path(
            self.pages_root, artifact.slug, artifact.extension
        )
        logger.info(
            "WebdevRepoWriter | scaffold page",
            extra={"slug": artifact.slug, "path": str(target_path)},
        )
        return target_path

    def write_page(self, artifact: PageArtifact) -> Path:
        """Create or update an Astro page based on the provided artifact."""

        target_path = ensure_page_path(
            self.pages_root, artifact.slug, artifact.extension
        )
        target_path.write_text(
            render_page_source(artifact, target_path), encoding="utf-8"
        )
        logger.info("WebdevRepoWriter | wrote page", extra={"path": str(target_path)})
        return target_path

    def write_json(self, relative_path: str, payload: Dict[str, Any]) -> Path:
        """Write structured data under ``src/data`` preserving indentation."""

        target = ensure_page_path(
            self.data_root, relative_path, expected_extension=".json"
        )
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logger.info("WebdevRepoWriter | wrote data", extra={"path": str(target)})
        return target


class SiteBuildTool:
    """Execute the Astro build pipeline when explicitly enabled."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def run(self) -> Dict[str, Any]:
        enable_ci = os.getenv("ENABLE_SITE_CI", "0").lower() in {"1", "true", "yes"}
        if not enable_ci:
            logger.info("WebdevSiteBuild | skipped", extra={"reason": "ci_disabled"})
            return {"status": "skipped", "reason": "ENABLE_SITE_CI not set"}

        record_http_request("/site/build")
        npm_cmd = ["npm", "ci"]
        build_cmd = ["npm", "run", "build"]
        env = os.environ.copy()

        logger.info("WebdevSiteBuild | running npm ci", extra={"cwd": str(self.project_root)})
        subprocess.run(npm_cmd, cwd=self.project_root, check=True, env=env)
        logger.info("WebdevSiteBuild | running npm run build", extra={"cwd": str(self.project_root)})
        subprocess.run(build_cmd, cwd=self.project_root, check=True, env=env)
        return {"status": "built"}


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.links.append(value)


@dataclass
class LinkCheckResult:
    file: Path
    broken_links: List[str]


class LinkCheckTool:
    """Perform a conservative link validation over the built site."""

    def __init__(self, dist_root: Path) -> None:
        self.dist_root = dist_root

    def _is_external(self, href: str) -> bool:
        normalized = href.strip()
        if not normalized:
            return True
        return normalized.startswith("http://") or normalized.startswith("https://") or normalized.startswith("mailto:")

    def run(self) -> List[LinkCheckResult]:
        if not self.dist_root.exists():
            logger.info("WebdevLinkCheck | skipped", extra={"reason": "dist_missing"})
            return []

        results: List[LinkCheckResult] = []
        for path in self.dist_root.rglob("*.html"):
            parser = _LinkCollector()
            parser.feed(path.read_text(encoding="utf-8"))
            broken: List[str] = []
            for href in parser.links:
                if self._is_external(href) or href.startswith("#"):
                    continue
                if href.startswith("/"):
                    candidate = (self.dist_root / href.lstrip("/")).resolve()
                else:
                    candidate = (path.parent / href).resolve()
                if not candidate.exists():
                    broken.append(href)
            if broken:
                results.append(LinkCheckResult(file=path, broken_links=broken))
        logger.info(
            "WebdevLinkCheck | completed",
            extra={"checked": len(results), "dist_root": str(self.dist_root)},
        )
        return results


class MetricsPush:
    """Prometheus-friendly metric helper for crew jobs."""

    def __init__(self, crew: str = "webdev") -> None:
        self.crew = crew

    def job_started(self) -> None:
        record_crew_job_status(self.crew, "running")

    def job_succeeded(self, duration: float) -> None:
        record_crew_job_status(self.crew, "done")
        record_crew_job_duration(self.crew, duration)

    def job_failed(self, duration: float) -> None:
        record_crew_job_status(self.crew, "failed")
        record_crew_job_duration(self.crew, duration)
