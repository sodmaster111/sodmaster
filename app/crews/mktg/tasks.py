"""Task definitions for the Marketing crew pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TaskSpec:
    """Structured descriptor of a deterministic crew task."""

    id: str
    owner: str
    summary: str
    outputs: List[str]

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serialisable representation of the task."""

        return {
            "id": self.id,
            "owner": self.owner,
            "summary": self.summary,
            "outputs": list(self.outputs),
        }


PLAN_CONTENT = TaskSpec(
    id="plan.content",
    owner="Strategist",
    summary="Define ICP narrative, funnel stages, and KPI expectations",
    outputs=[
        "ICP briefs with JTBD per segment",
        "Content matrix spanning ToFu/MoFu/BoFu",
        "Success metrics per campaign objective",
    ],
)

CREATE_PACKAGES = TaskSpec(
    id="create.packages",
    owner="ContentLead",
    summary="Produce draft assets and landing briefs",
    outputs=[
        "docs/content/*.md drafts",
        "Landing outline for /webdev integration",
        "Editorial calendar entries",
    ],
)

PREPARE_DISTRIBUTION = TaskSpec(
    id="distribution.plan",
    owner="Distribution",
    summary="Map channels to content assets and CTA",
    outputs=[
        "Channel-by-channel copy blocks",
        "Distribution calendar with owners",
        "CTA/UTM alignment matrix",
    ],
)

INSTRUMENT_ANALYTICS = TaskSpec(
    id="analytics.instrument",
    owner="Analyst",
    summary="Attach measurement plans and monitor conversions",
    outputs=[
        "UTM parameter schema",
        "Conversion goal checklist",
        "Weekly performance snapshot",
    ],
)


ALL_TASKS: List[TaskSpec] = [
    PLAN_CONTENT,
    CREATE_PACKAGES,
    PREPARE_DISTRIBUTION,
    INSTRUMENT_ANALYTICS,
]


__all__ = [
    "ALL_TASKS",
    "CREATE_PACKAGES",
    "INSTRUMENT_ANALYTICS",
    "PLAN_CONTENT",
    "PREPARE_DISTRIBUTION",
    "TaskSpec",
]
