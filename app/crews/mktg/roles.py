"""Role specifications for the Marketing crew."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class RoleSpec:
    """Human friendly description of a marketing crew role."""

    name: str
    focus: str
    responsibilities: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)

    def as_bullet_points(self) -> List[str]:
        """Render the role as a nested bullet list for planning notes."""

        bullets: List[str] = [f"**{self.name}** — {self.focus}"]
        if self.responsibilities:
            bullets.append("  * Responsibilities:")
            bullets.extend([f"    - {item}" for item in self.responsibilities])
        if self.deliverables:
            bullets.append("  * Deliverables:")
            bullets.extend([f"    - {item}" for item in self.deliverables])
        return bullets


STRATEGIST = RoleSpec(
    name="Strategist",
    focus="Translate business goals into ICP-led messaging and KPIs",
    responsibilities=[
        "Identify the primary ICP segments and their pain points",
        "Maintain a ToFu/MoFu/BoFu content matrix mapped to funnel stages",
        "Align every campaign with measurable KPIs and guardrails",
        "Prepare briefs for downstream execution teams",
    ],
    deliverables=[
        "Audience snapshots with JTBD summary",
        "Content matrix grouped by funnel stage",
        "Campaign KPI dashboard definition",
    ],
)

CONTENT_LEAD = RoleSpec(
    name="ContentLead",
    focus="Turn briefs into publishable content packages",
    responsibilities=[
        "Produce briefs for articles, posts, and landing pages",
        "Coordinate with WebDev crew for landing page builds",
        "Bundle copy, assets, and CTAs into reusable packages",
        "Ensure content cadence meets the strategist expectations",
    ],
    deliverables=[
        "Markdown drafts in docs/content/",
        "Landing page outlines for WebDev",
        "Editorial calendar with owners and deadlines",
    ],
)

DISTRIBUTION = RoleSpec(
    name="Distribution",
    focus="Own multi-channel distribution across owned and earned media",
    responsibilities=[
        "Select channels including Telegram Mini App, dev.to, X, and HackerNews",
        "Adapt key messages per channel nuances and CTA",
        "Schedule posts according to requested cadence",
        "Coordinate with Analyst on UTM conventions",
    ],
    deliverables=[
        "Channel-specific copy blocks",
        "Publishing checklist with deadlines",
        "Distribution tracker with owners",
    ],
)

ANALYST = RoleSpec(
    name="Analyst",
    focus="Instrument campaigns for attribution and closed-loop reporting",
    responsibilities=[
        "Define UTM parameters and conversion events",
        "Monitor cgo_jobs_total metrics for marketing crew throughput",
        "Summarise conversion metrics back to Strategist",
        "Maintain dashboards for retention of learnings",
    ],
    deliverables=[
        "UTM taxonomy reference",
        "Metrics snapshot with conversion funnel",
        "Post-mortem template for each campaign",
    ],
)


ALL_ROLES: List[RoleSpec] = [STRATEGIST, CONTENT_LEAD, DISTRIBUTION, ANALYST]


__all__ = [
    "ALL_ROLES",
    "ANALYST",
    "CONTENT_LEAD",
    "DISTRIBUTION",
    "RoleSpec",
    "STRATEGIST",
]
