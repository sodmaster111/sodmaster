"""Utility for generating markdown articles and infographics using ScriptMind."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

WORD_TARGET = 3100


@dataclass(frozen=True)
class PostSpec:
    """Specification for a blog post entry."""

    title: str
    keywords: Sequence[str]
    date: str

    def normalized_date(self) -> str:
        """Return ISO formatted date string."""
        try:
            parsed = datetime.fromisoformat(self.date)
        except ValueError as exc:  # pragma: no cover - guarded by tests
            raise ValueError(f"Invalid date format for post '{self.title}': {self.date}") from exc
        return parsed.date().isoformat()


@dataclass
class GeneratedContent:
    """Result from the ScriptMind assistant."""

    markdown_body: str
    image_bytes: bytes


class ScriptMindClient:
    """Very small stub that simulates the ScriptMind assistant."""

    def generate(self, post: PostSpec) -> GeneratedContent:
        """Generate deterministic article text and an infographic placeholder."""
        base_paragraph = (
            f"{post.title} explores the intersection of {', '.join(post.keywords)} "
            "and how modern teams can build resilient workflows. "
            "This section distills practical frameworks, success stories, and implementation details "
            "that teams can immediately apply."
        )
        words: List[str] = []
        paragraph_words = base_paragraph.split()
        while len(words) < WORD_TARGET:
            words.extend(paragraph_words)
        body_words = words[: WORD_TARGET + 50]
        paragraphs = []
        chunk = 0
        while chunk < len(body_words):
            paragraphs.append(" ".join(body_words[chunk : chunk + 120]))
            chunk += 120
        markdown_body = "\n\n".join(paragraphs)

        image_caption = (
            f"Infographic for {post.title} highlighting keywords: {', '.join(post.keywords)}"
        )
        image_bytes = image_caption.encode("utf-8")
        return GeneratedContent(markdown_body=markdown_body, image_bytes=image_bytes)


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(value: str) -> str:
    """Convert title to URL-friendly slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", value).lower()
    cleaned = re.sub(r"[\s_-]+", "-", cleaned).strip("-")
    if not cleaned:
        raise ValueError("Unable to build slug from empty title")
    if not SLUG_PATTERN.fullmatch(cleaned):
        cleaned = re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "", cleaned))
    if not SLUG_PATTERN.fullmatch(cleaned):  # pragma: no cover - defensive
        raise ValueError(f"Slug '{cleaned}' does not match expected pattern")
    return cleaned


def load_posts(path: Path) -> List[PostSpec]:
    """Load post specifications from JSON file."""
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    posts: List[PostSpec] = []
    for entry in raw:
        posts.append(
            PostSpec(
                title=entry["title"],
                keywords=tuple(entry["keywords"]),
                date=entry["date"],
            )
        )
    return posts


def build_frontmatter(post: PostSpec, slug: str) -> str:
    """Create YAML frontmatter for the generated article."""
    tags = [str(keyword) for keyword in post.keywords]
    def escape(value: str) -> str:
        return value.replace("\"", "\\\"")
    lines = ["---"]
    lines.append(f"title: \"{escape(post.title)}\"")
    lines.append(f"date: {post.normalized_date()}")
    lines.append("tags:")
    for tag in tags:
        lines.append(f"  - \"{escape(tag)}\"")
    lines.append(f"slug: {slug}")
    lines.append(f"image: infographic.png")
    lines.append("---")
    return "\n".join(lines)


def ensure_unique_slugs(posts: Iterable[PostSpec]) -> None:
    seen = set()
    for post in posts:
        slug = slugify(post.title)
        if slug in seen:
            raise ValueError(f"Duplicate slug generated for '{post.title}'")
        seen.add(slug)


def write_article(post: PostSpec, output_dir: Path, client: ScriptMindClient, overwrite: bool) -> Path:
    slug = slugify(post.title)
    destination = output_dir / slug
    article_path = destination / "article.md"
    image_path = destination / "infographic.png"

    if article_path.exists() and not overwrite:
        return article_path

    destination.mkdir(parents=True, exist_ok=True)
    generated = client.generate(post)
    frontmatter = build_frontmatter(post, slug)
    article_path.write_text(f"{frontmatter}\n\n{generated.markdown_body}\n", encoding="utf-8")
    image_path.write_bytes(generated.image_bytes)
    return article_path


def generate_all(posts: Sequence[PostSpec], output_dir: Path, overwrite: bool, dry_run: bool) -> None:
    ensure_unique_slugs(posts)
    client = ScriptMindClient()
    for post in posts:
        slug = slugify(post.title)
        if dry_run:
            print(f"[dry-run] Would generate article for {slug}")
            continue
        path = write_article(post, output_dir, client, overwrite=overwrite)
        print(f"Generated article at {path}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate blog content using ScriptMind")
    parser.add_argument(
        "--posts",
        type=Path,
        default=Path("content/blog/posts.json"),
        help="Path to posts.json file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("content/generated"),
        help="Directory where generated articles will be stored",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate existing articles if they are already present",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without writing files",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    posts = load_posts(args.posts)
    generate_all(posts, args.output_dir, overwrite=args.overwrite, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
