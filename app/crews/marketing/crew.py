"""Crew orchestrator for the autonomous marketing department."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .agents import AnalystAI, CopyAI, DesignAI, StrategyAI
from .tools import (
    CHANNEL_CLIENTS,
    a_b_winner_metric,
    collect_metrics,
    flush_scheduled,
    post_to_channel,
)

logger = logging.getLogger(__name__)

CHANNEL_ALIASES = {
    "x": "twitter",
    "twitter": "twitter",
    "linkedin": "linkedin",
    "telegram": "telegram",
    "tg": "telegram",
    "youtube": "youtube",
    "yt": "youtube",
}


class MarketingCrew:
    """High-level orchestration of the marketing agents pipeline."""

    def __init__(
        self,
        *,
        plan_path: Optional[Path] = None,
        templates_path: Optional[Path] = None,
        reports_root: Optional[Path] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parents[3]
        self.plan_path = plan_path or base_dir / "content" / "marketing_plan_en.json"
        self.templates_path = templates_path or base_dir / "templates" / "ads_en.mdx"
        self.reports_root = reports_root or base_dir / "reports" / "marketing"
        self.reports_root.mkdir(parents=True, exist_ok=True)

        self.strategy_ai = StrategyAI()
        self.copy_ai = CopyAI(self.templates_path)
        self.design_ai = DesignAI()
        self.analyst_ai = AnalystAI()

        self._plan_index = self._load_plan(self.plan_path)
        self._latest_report: Optional[Dict[str, Any]] = None

    def _load_plan(self, path: Path) -> Dict[int, Dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Marketing plan file not found: {path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        index: Dict[int, Dict[str, Any]] = {}
        for entry in raw:
            week = int(entry["week"])
            index[week] = entry
        return index

    def orchestrate_weekly_cycle(self, week: int, *, year: Optional[int] = None) -> Dict[str, Any]:
        if week not in self._plan_index:
            raise ValueError(f"Week {week} is not configured in marketing plan")
        iso_year = year or datetime.utcnow().isocalendar().year
        week_plan = self._plan_index[week]
        week_start = datetime.fromisocalendar(iso_year, week, 1)
        week_end = week_start + timedelta(days=6, hours=23, minutes=45)

        strategy = self.strategy_ai.develop_strategy(week_plan=week_plan, week=week)
        copy_assets = self.copy_ai.generate_assets(
            week=week, strategy=strategy, week_plan=week_plan
        )
        creatives = self.design_ai.generate_creatives(
            copy_assets=copy_assets, strategy=strategy
        )

        creative_index = {
            creative["asset_id"]: creative
            for channel_creatives in creatives.values()
            for creative in channel_creatives
        }

        publish_log: List[Dict[str, Any]] = []
        scheduled: List[Dict[str, Any]] = []
        for channel, assets in copy_assets.items():
            canonical_channel = CHANNEL_ALIASES.get(channel.lower(), channel.lower())
            if canonical_channel not in CHANNEL_CLIENTS:
                logger.warning(
                    "marketing_channel_skipped", extra={"channel": channel}
                )
                continue
            for offset, asset in enumerate(assets):
                schedule_at = self._resolve_schedule(asset.get("scheduled_for"), week_start, offset)
                payload = {
                    "headline": asset.get("headline"),
                    "body": asset.get("body"),
                    "cta": asset.get("cta"),
                    "variant": asset.get("variant"),
                    "experiment": asset.get("experiment"),
                    "creative": creative_index.get(asset["id"], {}),
                    "asset_id": asset["id"],
                }
                result = post_to_channel(
                    canonical_channel, payload, schedule_at=schedule_at
                )
                record = {
                    "channel": channel,
                    "canonical_channel": canonical_channel,
                    "asset_id": asset["id"],
                    "variant": asset["variant"],
                    "status": result.get("status", "posted"),
                    "post_id": result.get("post_id"),
                    "scheduled_for": result.get("scheduled_for"),
                }
                if record["status"] == "scheduled":
                    scheduled.append(record)
                else:
                    publish_log.append(record)

        flushed = flush_scheduled(until=week_end)
        for entry in flushed:
            payload = entry.get("payload", {})
            publish_log.append(
                {
                    "channel": entry["channel"].title(),
                    "canonical_channel": entry["channel"],
                    "asset_id": payload.get("asset_id"),
                    "variant": payload.get("variant"),
                    "status": entry.get("status", "posted"),
                    "post_id": entry.get("post_id"),
                    "scheduled_for": entry.get("scheduled_for"),
                }
            )

        metrics = collect_metrics()
        for experiment, winner in self._derive_ab_winners(copy_assets, metrics).items():
            a_b_winner_metric.labels(experiment=experiment).set(1 if winner == "A" else 2)

        insights = self.analyst_ai.analyse(
            week=week,
            metrics=metrics,
            strategy=strategy,
            copy_assets=copy_assets,
        )

        report = {
            "meta": {
                "year": iso_year,
                "week": week,
                "generated_at": datetime.utcnow().isoformat(),
            },
            "plan": week_plan,
            "strategy": strategy,
            "copy": copy_assets,
            "creatives": creatives,
            "publishing": {
                "published": publish_log,
                "scheduled": scheduled,
            },
            "metrics": metrics,
            "insights": insights,
        }
        self._latest_report = report
        self.save_reports(week=week, report=report, year=iso_year)
        logger.info("marketing_weekly_cycle_complete", extra={"week": week})
        return report

    def _resolve_schedule(
        self, scheduled_for: Optional[str], week_start: datetime, offset: int
    ) -> Optional[datetime]:
        if scheduled_for:
            try:
                return datetime.fromisoformat(scheduled_for)
            except ValueError:
                logger.debug("marketing_schedule_parse_failed", extra={"value": scheduled_for})
        return week_start + timedelta(days=min(offset * 2, 6), hours=10)

    def _derive_ab_winners(
        self,
        copy_assets: Dict[str, List[Dict[str, Any]]],
        metrics: Dict[str, Any],
    ) -> Dict[str, str]:
        winners: Dict[str, str] = {}
        for channel, assets in copy_assets.items():
            channel_metrics = metrics.get("channels", {}).get(channel, {})
            if not channel_metrics:
                channel_metrics = metrics.get("channels", {}).get(channel.title(), {})
            if not channel_metrics:
                continue
            a_ctr = channel_metrics.get("variant_a_ctr", 0.0)
            b_ctr = channel_metrics.get("variant_b_ctr", 0.0)
            experiment = assets[0].get("experiment", channel.lower()) if assets else channel.lower()
            winners[experiment] = "A" if a_ctr >= b_ctr else "B"
        return winners

    def save_reports(self, *, week: int, report: Dict[str, Any], year: Optional[int] = None) -> Path:
        iso_year = year or datetime.utcnow().isocalendar().year
        path = self.reports_root / f"{iso_year}-{week:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def latest_insights(self) -> Dict[str, Any]:
        if self._latest_report:
            return self._latest_report.get("insights", {})
        return self.analyst_ai.latest()


__all__ = ["MarketingCrew"]
