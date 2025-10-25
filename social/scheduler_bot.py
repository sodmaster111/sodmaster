"""Automated scheduler for publishing social media content.

The SchedulerBot is intended to be executed daily by cron at 09:00 UTC. It
loads post templates, renders a message per channel, publishes it through the
corresponding API client, and records metrics for observability.
"""
from __future__ import annotations

import json
import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway

from social_bootstrap import CLIENT_FACTORY, CONFIG_PATH, REQUIRED_TOKENS, load_config

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TEMPLATE_DIR = Path(__file__).resolve().parent
TWEETS_PATH = TEMPLATE_DIR / "tweets.json"
TELEGRAM_TEMPLATES_PATH = TEMPLATE_DIR / "telegram_post_templates.md"

REGISTRY = CollectorRegistry()
POSTS_TOTAL = Counter(
    "social_posts_total",
    "Total number of social posts published",
    labelnames=("channel",),
    registry=REGISTRY,
)
FOLLOWERS_COUNT = Gauge(
    "social_followers_count",
    "Current number of followers/subscribers per channel",
    labelnames=("channel",),
    registry=REGISTRY,
)


@dataclass
class ScheduledPost:
    channel: str
    content: str
    template_name: str

    def as_payload(self) -> Dict[str, str]:
        return {
            "channel": self.channel,
            "content": self.content,
            "template": self.template_name,
            "scheduled_for": datetime.now(timezone.utc).isoformat(),
        }


def _load_tweets(path: Path = TWEETS_PATH) -> List[str]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_telegram_templates(path: Path = TELEGRAM_TEMPLATES_PATH) -> List[str]:
    content = path.read_text(encoding="utf-8")
    sections: List[str] = []
    current: List[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            if current:
                sections.append("\n".join(current).strip())
                current = []
        if line.startswith("## "):
            current = [line]
        else:
            if current:
                current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return sections


class SchedulerBot:
    """Coordinates content publishing and metrics updates."""

    def __init__(
        self,
        config: Optional[Dict[str, object]] = None,
        registry: CollectorRegistry = REGISTRY,
        pushgateway_url: Optional[str] = None,
    ) -> None:
        self.config = config or load_config(CONFIG_PATH)
        self.registry = registry
        self.pushgateway_url = pushgateway_url or os.getenv("PROMETHEUS_PUSHGATEWAY")
        self.tweet_templates = _load_tweets()
        self.telegram_templates = _load_telegram_templates()

    def _select_template(self, channel: str) -> Optional[ScheduledPost]:
        if channel == "twitter":
            template = random.choice(self.tweet_templates)
            return ScheduledPost(channel, template, "tweet")
        if channel == "telegram_channel":
            template = random.choice(self.telegram_templates)
            return ScheduledPost(channel, template, "telegram_channel")
        if channel == "telegram_group":
            template = random.choice(self.telegram_templates)
            return ScheduledPost(channel, template, "telegram_group")
        LOGGER.info("No templates configured for channel %s", channel)
        return None

    def _publish(self, scheduled_post: ScheduledPost) -> None:
        factory = CLIENT_FACTORY.get(scheduled_post.channel)
        if not factory:
            LOGGER.warning(
                "Unable to publish to %s — no API client configured", scheduled_post.channel
            )
            return
        client = factory(REQUIRED_TOKENS.get(scheduled_post.channel, []))
        LOGGER.info(
            "Publishing to %s using template %s", scheduled_post.channel, scheduled_post.template_name
        )
        LOGGER.debug("Payload: %s", scheduled_post.as_payload())
        # In a real implementation this is where the API call would happen.
        try:
            client.publish_post(scheduled_post.content)
            POSTS_TOTAL.labels(channel=scheduled_post.channel).inc()
        except RuntimeError as exc:
            LOGGER.error("Failed to publish to %s: %s", scheduled_post.channel, exc)

    def update_followers(self, metrics: Dict[str, int]) -> None:
        for channel, count in metrics.items():
            FOLLOWERS_COUNT.labels(channel=channel).set(count)

    def push_metrics(self) -> None:
        if not self.pushgateway_url:
            return
        push_to_gateway(self.pushgateway_url, job="scheduler_bot", registry=self.registry)

    def run(self) -> None:
        channels = self.config.get("channels", [])
        for channel in channels:
            scheduled_post = self._select_template(channel)
            if scheduled_post:
                self._publish(scheduled_post)
            else:
                LOGGER.info(
                    "Skipping channel %s — provide templates to enable automation",
                    channel,
                )
        self.push_metrics()


def cron_entry() -> str:
    """Return a sample cron entry for documentation purposes."""
    command = f"python {Path(__file__).resolve()}"
    return f"0 9 * * * {command}"


if __name__ == "__main__":
    bot = SchedulerBot()
    bot.run()
