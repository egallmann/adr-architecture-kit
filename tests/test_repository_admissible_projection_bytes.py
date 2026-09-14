"""Guards for repository-admissible generated projection bytes.

Proves both:
- no inadmissible trailing horizontal whitespace in projections/templates
- authored Markdown hard-break semantics are preserved (not deleted)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from adr_kit.api import CompilationRequest, compile_architecture
from adr_kit.compiler.backend.markdown_rendering import (
    render_adr_markdown,
    template_path_for_adr,
)
from adr_kit.parser import ADRParser
from adr_kit.projection_markdown import (
    canonicalize_authored_markdown_hard_breaks,
    finalize_repository_admissible_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
VALID = FIXTURES / "valid"

PROJECTION_TEMPLATES = (
    ROOT / "src" / "adr_kit" / "templates" / "adr-logical.md.jinja2",
    ROOT / "src" / "adr_kit" / "templates" / "adr-physical.md.jinja2",
    ROOT / "src" / "adr_kit" / "templates" / "adr-logical-v3.md.jinja2",
    ROOT / "src" / "adr_kit" / "templates" / "adr-physical-system-v3.md.jinja2",
    ROOT / "src" / "adr_kit" / "templates" / "adr-physical-component-v3.md.jinja2",
)

HARD_BREAK_CONTEXT = "alpha  \nbeta"
HARD_BREAK_MARKER = "alpha<br>"
ABSENT_SOFT_BREAK = "alpha\nbeta"


def _assert_no_trailing_horizontal_whitespace(text: str, *, label: str) -> None:
    for lineno, line in enumerate(text.splitlines(), start=1):
        assert line == line.rstrip(" \t"), f"{label}:{lineno} has trailing horizontal whitespace"


def _assert_hard_break_preserved(body: str, *, label: str) -> None:
    assert HARD_BREAK_MARKER in body, f"{label}: missing admissible hard-break marker"
    assert ABSENT_SOFT_BREAK not in body.replace(HARD_BREAK_MARKER, ""), (
        f"{label}: hard break collapsed to soft break"
    )
    _assert_no_trailing_horizontal_whitespace(body, label=label)


@pytest.mark.parametrize("template", PROJECTION_TEMPLATES, ids=lambda p: p.name)
def test_projection_templates_have_no_trailing_horizontal_whitespace(
    template: Path,
) -> None:
    _assert_no_trailing_horizontal_whitespace(
        template.read_text(encoding="utf-8"),
        label=template.name,
    )


def test_canonicalize_hard_break_preserves_meaning_without_trailing_spaces() -> None:
    result = canonicalize_authored_markdown_hard_breaks(HARD_BREAK_CONTEXT)
    assert result == "alpha<br>\nbeta"
    assert "alpha  " not in result
    assert ABSENT_SOFT_BREAK not in result


def test_canonicalize_hard_break_leaves_fenced_trailing_spaces_intact() -> None:
    fenced = "intro\n```\ncode  \nline\n```\nout  \nside"
    result = canonicalize_authored_markdown_hard_breaks(fenced)
    assert "code  " in result
    assert "out<br>\nside" in result


def test_finalize_does_not_blanket_rstrip_authored_hard_breaks() -> None:
    # Regression: the prior finalizer joined line.rstrip() over the whole body.
    flawed = "\n".join(line.rstrip(" \t") for line in HARD_BREAK_CONTEXT.splitlines())
    assert flawed == ABSENT_SOFT_BREAK
    fixed = finalize_repository_admissible_markdown(HARD_BREAK_CONTEXT)
    assert fixed == "alpha<br>\nbeta"
    assert fixed != flawed


@pytest.mark.parametrize(
    ("fixture", "expected_template"),
    [
        (VALID / "logical-minimal.yaml", "adr-logical.md.jinja2"),
        (VALID / "physical-minimal.yaml", "adr-physical.md.jinja2"),
        (
            FIXTURES
            / "adr-l-human-projection"
            / "adrs"
            / "logical"
            / "ADR-L-9001-maximal-logical-authority.yaml",
            "adr-logical-v3.md.jinja2",
        ),
        (
            FIXTURES
            / "adr-ps-human-projection"
            / "adrs"
            / "physical-system"
            / "ADR-PS-9101-maximal-physical-system.yaml",
            "adr-physical-system-v3.md.jinja2",
        ),
        (
            FIXTURES
            / "adr-pc-human-projection"
            / "adrs"
            / "physical-component"
            / "ADR-PC-9001-maximal-physical-component.yaml",
            "adr-physical-component-v3.md.jinja2",
        ),
    ],
    ids=[
        "adr-logical",
        "adr-physical",
        "adr-logical-v3",
        "adr-physical-system-v3",
        "adr-physical-component-v3",
    ],
)
def test_render_preserves_authored_hard_break_across_template_families(
    fixture: Path,
    expected_template: str,
) -> None:
    adr = ADRParser().parse_adr(fixture)
    assert template_path_for_adr(adr).name == expected_template
    adr = adr.model_copy(update={"context": HARD_BREAK_CONTEXT})
    body = render_adr_markdown(adr)
    _assert_hard_break_preserved(body, label=expected_template)
    assert "## Context" in body


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
