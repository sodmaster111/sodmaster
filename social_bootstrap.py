"""Bootstrap social media channels for the project.

This script loads configuration from :mod:`social.config` and either provisions
channels using the available API clients or prints a manual checklist for the
team. All API calls are intentionally simplified and designed to be easily
extended with real client integrations.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

CONFIG_PATH = Path(__file__).parent / "social" / "config.json"

REQUIRED_TOKENS = {
    "twitter": ["TWITTER_BEARER_TOKEN", "TWITTER_API_KEY", "TWITTER_API_SECRET"],
    "linkedin": ["LINKEDIN_ACCESS_TOKEN"],
    "telegram_channel": ["TELEGRAM_BOT_TOKEN"],
    "telegram_group": ["TELEGRAM_BOT_TOKEN"],
    # YouTube provisioning usually requires OAuth credentials and a refresh token.
    "youtube": ["YOUTUBE_API_KEY", "YOUTUBE_CLIENT_SECRET"],
}

CHANNEL_DOCS = {
    "twitter": "https://developer.twitter.com/en/docs/twitter-api",
    "linkedin": "https://learn.microsoft.com/linkedin/marketing/",
    "youtube": "https://developers.google.com/youtube/v3/getting-started",
    "telegram_channel": "https://core.telegram.org/bots/api",
    "telegram_group": "https://core.telegram.org/bots/api",
}


class APIClient:
    """Base class for simulated API clients."""

    def __init__(self, channel: str, token_env_vars: Iterable[str]):
        self.channel = channel
        self.token_env_vars = list(token_env_vars)
        self.tokens = {var: os.getenv(var) for var in self.token_env_vars}

    def ensure_tokens(self) -> None:
        missing = [var for var, value in self.tokens.items() if not value]
        if missing:
            raise RuntimeError(
                f"Missing credentials for {self.channel}: {', '.join(missing)}"
            )

    def create_brand_profile(self, branding: Dict[str, str]) -> None:
        LOGGER.info(
            "Applying branding for %s (logo=%s, color=%s)",
            self.channel,
            branding.get("logo", ""),
            branding.get("brand_color", ""),
        )

    def create_channel(self, branding: Dict[str, str]) -> None:
        self.ensure_tokens()
        self.create_brand_profile(branding)
        LOGGER.info("Provisioned %s channel", self.channel)

    def publish_post(self, content: str) -> None:
        self.ensure_tokens()
        snippet = content if len(content) < 120 else f"{content[:117]}..."
        LOGGER.info("Published to %s: %s", self.channel, snippet)


class TelegramAPIClient(APIClient):
    def __init__(self, channel: str, token_env_vars: Iterable[str]):
        super().__init__(channel, token_env_vars)
        self.chat_type = "channel" if channel == "telegram_channel" else "supergroup"

    def create_channel(self, branding: Dict[str, str]) -> None:
        self.ensure_tokens()
        LOGGER.info(
            "Creating Telegram %s with branding %s", self.chat_type, branding.get("logo")
        )
        LOGGER.info("Provisioned %s", self.channel)

    def publish_post(self, content: str) -> None:
        self.ensure_tokens()
        first_line = content.splitlines()[0] if content else ""
        LOGGER.info(
            "Dispatched Telegram %s message: %s",
            self.chat_type,
            first_line,
        )


CLIENT_FACTORY = {
    "twitter": lambda vars_: APIClient("twitter", vars_),
    "linkedin": lambda vars_: APIClient("linkedin", vars_),
    "youtube": lambda vars_: APIClient("youtube", vars_),
    "telegram_channel": lambda vars_: TelegramAPIClient("telegram_channel", vars_),
    "telegram_group": lambda vars_: TelegramAPIClient("telegram_group", vars_),
}


def load_config(path: Path = CONFIG_PATH) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def all_tokens_available(channels: Iterable[str]) -> bool:
    missing: Dict[str, List[str]] = {}
    for channel in channels:
        required = REQUIRED_TOKENS.get(channel, [])
        missing_vars = [var for var in required if not os.getenv(var)]
        if missing_vars:
            missing[channel] = missing_vars
    if missing:
        LOGGER.debug("Missing token mapping: %s", missing)
    return not missing


def _create_checklist(channels: Iterable[str]) -> str:
    lines = ["create manually:"]
    for channel in channels:
        doc_url = CHANNEL_DOCS.get(channel, "https://example.com")
        lines.append(f"- {channel}: {doc_url}")
    return "\n".join(lines)


def provision_channels(config: Dict[str, object]) -> None:
    branding = config.get("branding", {})
    channels = config.get("channels", [])
    for channel in channels:
        factory = CLIENT_FACTORY.get(channel)
        if not factory:
            LOGGER.warning("No client factory registered for %s", channel)
            continue
        client = factory(REQUIRED_TOKENS.get(channel, []))
        client.create_channel(branding)


def main() -> None:
    config = load_config()
    channels = config.get("channels", [])
    if all_tokens_available(channels):
        LOGGER.info("All API tokens detected. Bootstrapping channels…")
        provision_channels(config)
        LOGGER.info("Bootstrap completed successfully.")
    else:
        checklist = _create_checklist(channels)
        print(checklist)


if __name__ == "__main__":
    main()
