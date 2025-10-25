from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import content_generator as cg


class DummyClient(cg.ScriptMindClient):
    def __init__(self, body: str, image: bytes = b"image") -> None:
        self._body = body
        self._image = image

    def generate(self, post: cg.PostSpec) -> cg.GeneratedContent:  # type: ignore[override]
        return cg.GeneratedContent(markdown_body=self._body, image_bytes=self._image)


@pytest.fixture()
def sample_post() -> cg.PostSpec:
    return cg.PostSpec(
        title="Sample Article",
        keywords=("testing", "automation"),
        date="2024-07-01",
    )


def test_frontmatter_contains_required_fields(tmp_path: Path, sample_post: cg.PostSpec) -> None:
    body = "Lorem ipsum " * 200
    client = DummyClient(body=body)
    article_path = cg.write_article(sample_post, tmp_path, client, overwrite=True)
    text = article_path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    frontmatter, _ = text.split("---\n", 2)[1:]
    data = {}
    for line in frontmatter.strip().splitlines():
        if line.strip() == "tags:":
            data["tags"] = []
            continue
        if line.startswith("  - "):
            data.setdefault("tags", []).append(line[4:].strip().strip("'\""))
        elif ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip("'\"")
    for field in ("title", "date", "tags", "slug"):
        assert field in data
    assert data["slug"] == cg.slugify(sample_post.title)
    assert isinstance(data["tags"], list)


def test_slug_pattern_matches_posts_file() -> None:
    posts_file = Path("content/blog/posts.json")
    with posts_file.open("r", encoding="utf-8") as fp:
        raw_posts = json.load(fp)
    pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    for entry in raw_posts:
        slug = cg.slugify(entry["title"])
        assert pattern.fullmatch(slug), f"Slug {slug} did not match pattern"
