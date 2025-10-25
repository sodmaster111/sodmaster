"""Utility functions and clients powering the autonomous marketing crew."""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from app.prometheus import Counter, Gauge

logger = logging.getLogger(__name__)


marketing_posts_total = Counter(
    "marketing_posts_total",
    "Number of marketing posts published to each channel",
    labelnames=("channel",),
)
marketing_clicks_total = Counter(
    "marketing_clicks_total",
    "Total number of clicks generated per channel",
    labelnames=("channel",),
)
conversion_rate_metric = Gauge(
    "conversion_rate",
    "Overall conversion rate across all marketing channels",
)
a_b_winner_metric = Gauge(
    "a_b_winner",
    "Winning variant for the current A/B experiment (1=A, 2=B)",
    labelnames=("experiment",),
)


@dataclass
class SocialChannelClient:
    """Base social channel API client with deterministic metric estimation."""

    channel: str
    base_click_rate: float
    base_conversion_rate: float
    posts: List[Dict[str, Any]] = field(default_factory=list)
    _reported_clicks: int = 0
    _reported_conversions: int = 0

    def post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = payload.get("scheduled_for") or datetime.utcnow().isoformat()
        engagement = self._estimate_engagement(payload)
        post_id = f"{self.channel}-{len(self.posts) + 1:03d}"
        record = {
            "id": post_id,
            "timestamp": timestamp,
            "payload": payload,
            "engagement": engagement,
        }
        self.posts.append(record)
        marketing_posts_total.labels(channel=self.channel).inc()
        logger.info(
            "marketing_post_published",
            extra={"channel": self.channel, "post_id": post_id},
        )
        return {
            "channel": self.channel,
            "post_id": post_id,
            "scheduled_for": timestamp,
        }

    def _estimate_engagement(self, payload: Dict[str, Any]) -> Dict[str, float]:
        headline = payload.get("headline", "")
        body = payload.get("body", "")
        text_length = len(headline) * 2 + len(body)
        variant_modifier = 1.15 if payload.get("variant") == "B" else 1.0
        impressions = max(900, int(800 + text_length * (0.6 + self.base_click_rate)))
        clicks = int(impressions * (0.018 + (self.base_click_rate * 0.6)))
        clicks = int(clicks * variant_modifier)
        conversions = max(1, int(clicks * (self.base_conversion_rate + 0.02 * variant_modifier)))
        return {
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
        }

    def collect(self) -> Dict[str, Any]:
        total_impressions = sum(post["engagement"]["impressions"] for post in self.posts)
        total_clicks = sum(post["engagement"]["clicks"] for post in self.posts)
        total_conversions = sum(post["engagement"]["conversions"] for post in self.posts)
        if total_clicks > self._reported_clicks:
            marketing_clicks_total.labels(channel=self.channel).inc(
                total_clicks - self._reported_clicks
            )
            self._reported_clicks = total_clicks
        if total_conversions > self._reported_conversions:
            self._reported_conversions = total_conversions
        ctr = total_clicks / total_impressions if total_impressions else 0.0
        return {
            "channel": self.channel,
            "posts": len(self.posts),
            "impressions": total_impressions,
            "clicks": total_clicks,
            "conversions": total_conversions,
            "ctr": ctr,
        }


class TwitterClient(SocialChannelClient):
    def __init__(self) -> None:
        super().__init__("twitter", base_click_rate=0.7, base_conversion_rate=0.08)


class LinkedInClient(SocialChannelClient):
    def __init__(self) -> None:
        super().__init__("linkedin", base_click_rate=0.55, base_conversion_rate=0.11)


class TelegramClient(SocialChannelClient):
    def __init__(self) -> None:
        super().__init__("telegram", base_click_rate=0.5, base_conversion_rate=0.09)


class YouTubeClient(SocialChannelClient):
    def __init__(self) -> None:
        super().__init__("youtube", base_click_rate=0.65, base_conversion_rate=0.07)


CHANNEL_CLIENTS: Dict[str, SocialChannelClient] = {
    "twitter": TwitterClient(),
    "linkedin": LinkedInClient(),
    "telegram": TelegramClient(),
    "youtube": YouTubeClient(),
}


@dataclass(order=True)
class _ScheduledPost:
    run_at: datetime
    client: SocialChannelClient = field(compare=False)
    payload: Dict[str, Any] = field(compare=False)


class Scheduler:
    """Simple in-memory scheduler storing delayed posts."""

    def __init__(self) -> None:
        self._queue: List[_ScheduledPost] = []

    def schedule(self, client: SocialChannelClient, payload: Dict[str, Any], *, run_at: datetime) -> None:
        heapq.heappush(self._queue, _ScheduledPost(run_at, client, payload))
        logger.info(
            "marketing_post_scheduled",
            extra={"channel": client.channel, "scheduled_for": run_at.isoformat()},
        )

    def flush(self, *, until: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if until is None:
            until = datetime.utcnow()
        published: List[Dict[str, Any]] = []
        while self._queue and self._queue[0].run_at <= until:
            item = heapq.heappop(self._queue)
            payload = dict(item.payload)
            payload["scheduled_for"] = item.run_at.isoformat()
            flushed = item.client.post(payload)
            flushed.update({"status": "posted", "payload": payload})
            published.append(flushed)
        return published

    def pending(self) -> List[Dict[str, Any]]:
        return [
            {
                "channel": item.client.channel,
                "scheduled_for": item.run_at.isoformat(),
                "headline": item.payload.get("headline"),
            }
            for item in sorted(self._queue, key=lambda entry: entry.run_at)
        ]


scheduler = Scheduler()


def post_to_channel(
    channel: str, payload: Dict[str, Any], *, schedule_at: Optional[datetime] = None
) -> Dict[str, Any]:
    client = CHANNEL_CLIENTS.get(channel.lower())
    if client is None:
        raise ValueError(f"Unsupported channel: {channel}")
    if schedule_at and schedule_at > datetime.utcnow():
        scheduler.schedule(client, payload, run_at=schedule_at)
        return {
            "channel": client.channel,
            "status": "scheduled",
            "scheduled_for": schedule_at.isoformat(),
            "payload": payload,
        }
    payload = dict(payload)
    payload.setdefault("scheduled_for", datetime.utcnow().isoformat())
    result = client.post(payload)
    result.update({"status": "posted", "payload": payload})
    return result


def flush_scheduled(*, until: Optional[datetime] = None) -> List[Dict[str, Any]]:
    return scheduler.flush(until=until)


def collect_metrics(channels: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    if channels is None:
        channels = list(CHANNEL_CLIENTS.keys())
    selected = [CHANNEL_CLIENTS[channel.lower()] for channel in channels if channel.lower() in CHANNEL_CLIENTS]
    channel_metrics: Dict[str, Dict[str, Any]] = {}
    total_impressions = 0
    total_clicks = 0
    total_conversions = 0
    for client in selected:
        metrics = client.collect()
        variant_stats = _variant_breakdown(client.posts)
        metrics.update(variant_stats)
        channel_metrics[client.channel.title()] = metrics
        total_impressions += metrics["impressions"]
        total_clicks += metrics["clicks"]
        total_conversions += metrics["conversions"]
    ctr = total_clicks / total_impressions if total_impressions else 0.0
    conversion_rate = total_conversions / total_clicks if total_clicks else 0.0
    conversion_rate_metric.set(conversion_rate)
    return {
        "channels": channel_metrics,
        "totals": {
            "impressions": total_impressions,
            "clicks": total_clicks,
            "conversions": total_conversions,
            "ctr": ctr,
            "conversion_rate": conversion_rate,
        },
    }


def _variant_breakdown(posts: List[Dict[str, Any]]) -> Dict[str, float]:
    variant_clicks = {"A": 0, "B": 0}
    for post in posts:
        variant = post["payload"].get("variant", "A").upper()
        if variant not in variant_clicks:
            variant_clicks[variant] = 0
        variant_clicks[variant] += post["engagement"]["clicks"]
    impressions = sum(post["engagement"]["impressions"] for post in posts) or 1
    return {
        "variant_a_ctr": variant_clicks.get("A", 0) / impressions,
        "variant_b_ctr": variant_clicks.get("B", 0) / impressions,
    }


__all__ = [
    "CHANNEL_CLIENTS",
    "Scheduler",
    "a_b_winner_metric",
    "collect_metrics",
    "conversion_rate_metric",
    "flush_scheduled",
    "marketing_clicks_total",
    "marketing_posts_total",
    "post_to_channel",
    "scheduler",
]
