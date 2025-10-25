"""Agent definitions for the autonomous marketing crew."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Sequence

from tools.search_tools import exa_search_tool, serper_tool

logger = logging.getLogger(__name__)


def _safe_tool_run(tool: Any, query: str) -> Dict[str, Any]:
    """Execute a CrewAI tool defensively and normalise the output."""

    tool_name = getattr(tool, "name", tool.__class__.__name__)
    try:
        result = tool(query=query)
    except TypeError:
        try:
            result = tool(query)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("marketing_tool_invocation_failed", extra={"tool": tool_name})
            return {"tool": tool_name, "status": "error", "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("marketing_tool_invocation_failed", extra={"tool": tool_name})
        return {"tool": tool_name, "status": "error", "error": str(exc)}

    if isinstance(result, str):
        payload: Dict[str, Any] = {"tool": tool_name, "status": "ok", "result": result}
    else:
        payload = {
            "tool": tool_name,
            "status": "ok",
            "result": result,
        }
    return payload


@dataclass
class StrategyAI:
    """Agent responsible for deriving the weekly marketing strategy."""

    trend_tools: Sequence[Any] = field(
        default_factory=lambda: (exa_search_tool, serper_tool)
    )

    def develop_strategy(self, *, week_plan: Dict[str, Any], week: int) -> Dict[str, Any]:
        """Synthesize positioning, key messages and activation plan for the week."""

        queries = [
            f"Growth marketing trends for {channel} audience"
            for channel in week_plan.get("target_channels", [])
        ]
        queries.append(
            f"B2B SaaS marketing benchmarks for conversion target {week_plan.get('goals', {}).get('conversion', '')}"
        )

        research: List[Dict[str, Any]] = []
        for query in queries:
            for tool in self.trend_tools:
                payload = _safe_tool_run(tool, query)
                payload["query"] = query
                research.append(payload)

        campaign_theme = week_plan.get("core_messages", ["Growth loops"])[0]
        positioning = {
            "week": week,
            "theme": campaign_theme,
            "audience": week_plan.get("audience", "builders"),
            "goals": week_plan.get("goals", {}),
            "call_to_action": week_plan.get("call_to_action", []),
        }
        timeline: List[Dict[str, Any]] = []
        base_start = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
        messages = week_plan.get("core_messages", ["Narrative"])
        for offset, touchpoint in enumerate(["Awareness", "Activation", "Conversion"]):
            timeline.append(
                {
                    "touchpoint": touchpoint,
                    "scheduled_for": (base_start + timedelta(days=offset * 2)).isoformat(),
                    "focus": messages[offset % len(messages)],
                }
            )

        strategy = {
            "positioning": positioning,
            "research": research,
            "target_channels": week_plan.get("target_channels", []),
            "timeline": timeline,
        }
        logger.info(
            "marketing_strategy_generated",
            extra={"week": week, "channels": strategy["target_channels"]},
        )
        return strategy


@dataclass
class CopyAI:
    """Agent generating English-language marketing copy."""

    templates_path: Path
    templates: List[Dict[str, Any]] = field(init=False)

    def __post_init__(self) -> None:
        self.templates = self._load_templates(self.templates_path)

    @staticmethod
    def _load_templates(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            logger.warning("marketing_copy_templates_missing", extra={"path": str(path)})
            return []
        templates: List[Dict[str, Any]] = []
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("<!--"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("marketing_copy_template_parse_failed", extra={"line": line})
                continue
            templates.append(payload)
        return templates

    def generate_assets(
        self,
        *,
        week: int,
        strategy: Dict[str, Any],
        week_plan: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:
        channels = strategy.get("target_channels", [])
        assets: Dict[str, List[Dict[str, Any]]] = {}
        timeline = strategy.get("timeline", [])
        for index, channel in enumerate(channels):
            channel_templates = [
                template
                for template in self.templates
                if channel.lower() in [c.lower() for c in template.get("channels", [])]
            ]
            if not channel_templates:
                channel_templates = self.templates
            selected_templates = channel_templates[:2]
            channel_assets: List[Dict[str, Any]] = []
            for variation, template in enumerate(selected_templates, start=1):
                schedule_info = timeline[(index + variation - 1) % len(timeline)] if timeline else {}
                asset = {
                    "id": f"{channel[:2].upper()}-{week:02d}-{variation}",
                    "variant": "A" if variation == 1 else "B",
                    "headline": template.get("headline"),
                    "body": template.get("body"),
                    "cta": template.get("cta", week_plan.get("call_to_action", ["subscribe"])[0]),
                    "channels": template.get("channels", [channel]),
                    "scheduled_for": schedule_info.get("scheduled_for"),
                    "experiment": f"week-{week:02d}-{channel.lower()}",
                    "message_focus": schedule_info.get("focus"),
                }
                channel_assets.append(asset)
            assets[channel] = channel_assets
        logger.info(
            "marketing_copy_generated", extra={"week": week, "channels": list(assets.keys())}
        )
        return assets


@dataclass
class DesignAI:
    """Agent responsible for creative prompts for visual assets."""

    default_provider: str = "leonardo"

    def generate_creatives(
        self,
        *,
        copy_assets: Dict[str, List[Dict[str, Any]]],
        strategy: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:
        creatives: Dict[str, List[Dict[str, Any]]] = {}
        theme = strategy.get("positioning", {}).get("theme", "Autonomous marketing")
        for channel, assets in copy_assets.items():
            channel_creatives: List[Dict[str, Any]] = []
            for asset in assets:
                provider = "dalle" if channel.lower() == "youtube" else self.default_provider
                prompt = (
                    f"{theme} | {channel} spotlight on {asset.get('message_focus', 'product launch')} "
                    f"with CTA {asset.get('cta', 'discover')}"
                )
                channel_creatives.append(
                    {
                        "asset_id": asset["id"],
                        "provider": provider,
                        "prompt": prompt,
                        "style": "vivid gradients with bold typography",
                    }
                )
            creatives[channel] = channel_creatives
        logger.info("marketing_creatives_prepared", extra={"channels": list(creatives.keys())})
        return creatives


@dataclass
class AnalystAI:
    """Agent that interprets performance metrics and recommends actions."""

    history: List[Dict[str, Any]] = field(default_factory=list)

    def analyse(
        self,
        *,
        week: int,
        metrics: Dict[str, Any],
        strategy: Dict[str, Any],
        copy_assets: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        totals = metrics.get("totals", {})
        ctr = totals.get("ctr", 0.0)
        conversion_rate = totals.get("conversion_rate", 0.0)
        strongest_channel = max(
            metrics.get("channels", {}).items(),
            key=lambda item: item[1].get("ctr", 0.0),
            default=(None, {}),
        )[0]
        recommendations: List[str] = []
        if ctr < 0.025:
            recommendations.append(
                "Double-down on narrative hooks; current CTR is below target 2.5%"
            )
        if conversion_rate < strategy.get("positioning", {}).get("goals", {}).get("conversion", 0.03):
            recommendations.append("Introduce deeper product proof in B-variant copy next week")
        if strongest_channel:
            recommendations.append(f"Extend retargeting on {strongest_channel} where CTR is leading")

        ab_results: Dict[str, str] = {}
        for channel, assets in copy_assets.items():
            channel_metrics = metrics.get("channels", {}).get(channel, {})
            variant_winner = "A" if channel_metrics.get("variant_a_ctr", 0) >= channel_metrics.get("variant_b_ctr", 0) else "B"
            ab_results[channel] = variant_winner

        insights = {
            "week": week,
            "summary": {
                "ctr": ctr,
                "conversion_rate": conversion_rate,
                "strongest_channel": strongest_channel,
            },
            "recommendations": recommendations,
            "ab_results": ab_results,
        }
        self.history.append(insights)
        logger.info("marketing_analysis_complete", extra={"week": week})
        return insights

    def latest(self) -> Dict[str, Any]:
        return self.history[-1] if self.history else {
            "summary": {},
            "recommendations": [
                "Run orchestrate_weekly_cycle before requesting insights",
            ],
        }
