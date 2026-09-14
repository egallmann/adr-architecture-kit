"""Guards for repository-admissible generated projection bytes."""

from __future__ import annotations

from pathlib import Path

import pytest

from adr_kit.api import CompilationRequest, compile_architecture

ROOT = Path(__file__).resolve().parents[1]

V3_TEMPLATES = (
    ROOT / "src" / "adr_kit" / "templates" / "adr-logical-v3.md.jinja2",
    ROOT / "src" / "adr_kit" / "templates" / "adr-physical-system-v3.md.jinja2",
    ROOT / "src" / "adr_kit" / "templates" / "adr-physical-component-v3.md.jinja2",
)


def _assert_no_trailing_horizontal_whitespace(text: str, *, label: str) -> None:
    for lineno, line in enumerate(text.splitlines(), start=1):
        assert line == line.rstrip(" \t"), f"{label}:{lineno} has trailing horizontal whitespace"


@pytest.mark.parametrize("template", V3_TEMPLATES, ids=lambda p: p.name)
def test_v3_projection_templates_have_no_trailing_horizontal_whitespace(
    template: Path,
) -> None:
    _assert_no_trailing_horizontal_whitespace(
        template.read_text(encoding="utf-8"),
        label=template.name,
    )


def test_compiled_human_projections_have_no_trailing_horizontal_whitespace() -> None:
    result = compile_architecture(
        CompilationRequest(project_root=ROOT, artifact_groups=("markdown",), write=False)
    )
    assert result.success, result.diagnostics
    markdown_artifacts = [
        item
        for item in result.artifacts
        if item.relative_path.replace("\\", "/").startswith("adrs/adr-projection/")
    ]
    assert markdown_artifacts, "expected adr-projection markdown artifacts"
    for item in markdown_artifacts:
        body = item.content.decode("utf-8")
        _assert_no_trailing_horizontal_whitespace(body, label=item.relative_path)
