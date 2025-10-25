"""Helpers for generating Astro-friendly source files."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import List, Optional

_SLUG_PATTERN = re.compile(r"[^a-z0-9\-/]")


@dataclass
class PageArtifact:
    """Normalized representation of a page that will be emitted to Astro."""

    slug: str
    title: str
    body: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    canonical_url: Optional[str] = None
    layout: str = "BaseLayout"
    extension: str = ".astro"

    def summary(self) -> str:
        if self.description:
            return self.description.strip()
        collapsed = " ".join(self.body.strip().split())
        return collapsed[:157] + "…" if len(collapsed) > 160 else collapsed


def _normalize_slug(slug: str) -> str:
    raw = slug.strip().lower().strip("/")
    raw = raw.replace(" ", "-")
    sanitized = _SLUG_PATTERN.sub("-", raw)
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized.strip("-")


def ensure_page_path(base_dir: Path, slug: str, expected_extension: Optional[str] = None) -> Path:
    """Return an absolute path for the given slug ensuring directory safety."""

    normalized_input = slug.replace("\\", "/")
    if any(part == ".." for part in normalized_input.split("/")):
        raise ValueError("Slug cannot contain parent directory traversal")

    normalized_slug = _normalize_slug(slug)
    if not normalized_slug:
        raise ValueError("Slug must contain at least one alphanumeric character")

    relative_path = Path(normalized_slug)
    if any(part == ".." for part in relative_path.parts):
        raise ValueError("Slug cannot traverse outside of the pages directory")

    if relative_path.suffix:
        path = base_dir / relative_path
        extension = relative_path.suffix
    else:
        extension = expected_extension or ".astro"
        path = (base_dir / relative_path).with_suffix(extension)

    if expected_extension and extension != expected_extension:
        raise ValueError(
            f"Expected extension {expected_extension} but received {extension} for slug {slug}"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _layout_import_for(target_path: Path, layout_name: str) -> str:
    try:
        src_index = target_path.parts.index("src")
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError("Target path must live under an Astro src directory") from exc

    src_root = Path(*target_path.parts[: src_index + 1])
    layouts_root = src_root / "layouts" / f"{layout_name}.astro"
    relative = Path(os.path.relpath(layouts_root, target_path.parent))
    return str(relative).replace("\\", "/")


def _format_tags(tags: List[str]) -> str:
    if not tags:
        return "[]"
    values = ", ".join(f'"{tag}"' for tag in tags)
    return f"[{values}]"


def _page_metadata_lines(artifact: PageArtifact) -> List[str]:
    meta_lines = [
        f"title: \"{artifact.title}\"",
        f"description: \"{artifact.summary()}\"",
    ]
    if artifact.canonical_url:
        meta_lines.append(f"canonical: \"{artifact.canonical_url}\"")
    if artifact.tags:
        meta_lines.append(f"tags: {_format_tags(artifact.tags)}")
    return meta_lines


def render_markdown_page(artifact: PageArtifact, target_path: Path) -> str:
    """Render Markdown content with Astro frontmatter."""

    layout_import = _layout_import_for(target_path, artifact.layout)
    frontmatter_lines = ["---"]
    frontmatter_lines.extend(_page_metadata_lines(artifact))
    frontmatter_lines.append(f"layout: '{layout_import}'")
    frontmatter_lines.append("---")
    frontmatter = "\n".join(frontmatter_lines)
    body = artifact.body.strip() + "\n"
    return f"{frontmatter}\n\n{body}"


def render_astro_page(artifact: PageArtifact, target_path: Path) -> str:
    """Render the Astro source for the provided artifact."""

    layout_import = _layout_import_for(target_path, artifact.layout)
    meta_lines = ["const page = {"]
    for line in _page_metadata_lines(artifact):
        meta_lines.append(f"  {line}")
    meta_lines.append("};")
    meta_block = "\n".join(meta_lines)

    frontmatter = dedent(
        f"""
        ---
        import {artifact.layout} from '{layout_import}';
        {meta_block}
        ---
        """
    ).strip()

    body = artifact.body.strip() + "\n"
    return (
        f"{frontmatter}\n"
        f"<{artifact.layout} {{...page}}>\n"
        f"  <section class=\"generated-content\">\n{indent_markdown(body)}\n  </section>\n"
        f"</{artifact.layout}>\n"
    )


def render_page_source(artifact: PageArtifact, target_path: Path) -> str:
    """Render Astro or Markdown source depending on the artifact extension."""

    extension = artifact.extension.lower()
    if extension == ".astro":
        return render_astro_page(artifact, target_path)
    if extension in {".md", ".markdown"}:
        return render_markdown_page(artifact, target_path)
    raise ValueError(f"Unsupported page extension '{artifact.extension}'")


def indent_markdown(markdown: str, prefix: str = "    ") -> str:
    """Indent multiline markdown blocks for Astro child content."""

    lines = markdown.splitlines()
    return "\n".join(prefix + line if line.strip() else prefix for line in lines)


__all__ = [
    "PageArtifact",
    "ensure_page_path",
    "indent_markdown",
    "render_astro_page",
    "render_markdown_page",
    "render_page_source",
]
