import pytest
from app.site.helpers.content import (
    PageArtifact,
    ensure_page_path,
    render_astro_page,
    render_markdown_page,
)


def test_render_astro_page_builds_frontmatter(tmp_path):
    project_root = tmp_path / "site"
    pages_root = project_root / "src" / "pages"
    layout_root = project_root / "src" / "layouts"
    layout_root.mkdir(parents=True)
    pages_root.mkdir(parents=True)

    target_path = ensure_page_path(pages_root, "docs/getting-started")
    artifact = PageArtifact(slug="docs/getting-started", title="Getting Started", body="## Hello")
    content = render_astro_page(artifact, target_path)

    assert "import BaseLayout from '../../layouts/BaseLayout.astro';" in content
    assert "const page = {" in content
    assert "<BaseLayout {...page}>" in content
    assert "## Hello" in content


def test_ensure_page_path_blocks_traversal(tmp_path):
    base = tmp_path / "pages"
    base.mkdir()
    with pytest.raises(ValueError):
        ensure_page_path(base, "../secrets")


def test_render_markdown_page_emits_frontmatter(tmp_path):
    project_root = tmp_path / "site"
    pages_root = project_root / "src" / "pages"
    layout_root = project_root / "src" / "layouts"
    layout_root.mkdir(parents=True)
    pages_root.mkdir(parents=True)

    target_path = ensure_page_path(pages_root, "blog/update", expected_extension=".md")
    artifact = PageArtifact(
        slug="blog/update",
        title="Quarterly Update",
        body="## Highlights\n- Revenue up",
        extension=".md",
    )
    content = render_markdown_page(artifact, target_path)

    assert content.startswith("---\n")
    assert "layout:" in content
    assert "Quarterly Update" in content
