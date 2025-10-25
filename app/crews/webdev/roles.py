"""Role specifications for the Web Development crew."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class RoleSpec:
    """Lightweight description of a CrewAI role.

    The repository does not instantiate real CrewAI agents in tests, but the
    orchestration layer relies on a structured definition of responsibilities
    to build planning notes and audit trails.  The dataclass keeps the module
    import friendly for environments where the heavy CrewAI dependencies might
    be missing while still providing rich documentation for humans.
    """

    name: str
    focus: str
    responsibilities: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)

    def as_bullet_points(self) -> List[str]:
        """Return a markdown bullet list representing the role."""

        bullets: List[str] = [f"**{self.name}** — {self.focus}"]
        if self.responsibilities:
            bullets.append("  * Responsibilities:")
            bullets.extend([f"    - {item}" for item in self.responsibilities])
        if self.deliverables:
            bullets.append("  * Deliverables:")
            bullets.extend([f"    - {item}" for item in self.deliverables])
        return bullets


WEB_ARCHITECT = RoleSpec(
    name="WebArch",
    focus="Front-end architecture, IA, routing strategy, SEO foundations",
    responsibilities=[
        "Curate information architecture and URL structure for generated pages",
        "Define canonical metadata, OpenGraph defaults, and sitemap coverage",
        "Establish performance budgets (LCP, TBT, CLS) for Astro builds",
        "Review component hierarchy and enforce accessibility heuristics",
    ],
    deliverables=[
        "Navigation map with route ownership",
        "SEO checklist per page (title, description, canonical, robots)",
        "Performance budget document with target metrics",
    ],
)

FULLSTACK = RoleSpec(
    name="Fullstack",
    focus="Astro/React implementation and content generation pipeline",
    responsibilities=[
        "Transform JSON/Markdown payloads into Astro pages and collections",
        "Wire API bindings or static data loaders when components request data",
        "Ensure incremental builds remain idempotent and reproducible",
        "Document any new components or layouts referenced by generated pages",
    ],
    deliverables=[
        "Generated `.astro` or `.mdx` files under `src/pages/`",
        "Structured data outputs in `src/data/`",
        "Implementation notes describing how payload fields map to templates",
    ],
)

INFRA = RoleSpec(
    name="Infra",
    focus="Render Static deployment hygiene and web performance operations",
    responsibilities=[
        "Recommend cache-control headers and CDN hints (Cloudflare, Render)",
        "Verify `robots.txt` / sitemap coherence and static asset hashing",
        "Provide guidance for deploying static exports with immutable caching",
        "Surface environment toggles for CI site builds (ENABLE_SITE_CI)",
    ],
    deliverables=[
        "Infra checklist summarising cache, CDN, and build triggers",
        "Suggested headers for Render static site hosting",
        "Sitemap/robots diffs when new routes are introduced",
    ],
)

QA = RoleSpec(
    name="QA",
    focus="Quality, linting, and link validation for generated output",
    responsibilities=[
        "Run markdown linting and Astro `npm run check` when enabled",
        "Execute link checking over the built `dist/` artifacts",
        "Trigger Lighthouse CI or record TODO when the tooling is disabled",
        "Report anomalies with actionable reproduction steps",
    ],
    deliverables=[
        "Validation report with pass/fail status for each check",
        "List of broken links or skipped audits",
        "Summary of quality gates executed for the job",
    ],
)


ALL_ROLES: List[RoleSpec] = [WEB_ARCHITECT, FULLSTACK, INFRA, QA]


__all__ = [
    "ALL_ROLES",
    "FULLSTACK",
    "INFRA",
    "QA",
    "RoleSpec",
    "WEB_ARCHITECT",
]
