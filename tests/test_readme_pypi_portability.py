"""PyPI package-description README must use portable Markdown link targets.

The file declared as ``project.readme`` becomes the PyPI long description.
Repository-relative links resolve on GitHub but break under pypi.org.
Enforces INV-0083 / CAP-0046 package-description portability.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Inline links/images: ![alt](target) or [text](target). Title after target ignored.
_INLINE_LINK_RE = re.compile(
    r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|"
    r"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)"
)
# Reference definitions: [id]: target
_REF_DEF_RE = re.compile(
    r"^\[([^\]]+)\]:\s*(\S+)",
    re.MULTILINE,
)


def _package_readme_path(root: Path) -> Path:
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    readme = payload["project"]["readme"]
    if isinstance(readme, dict):
        readme = readme["file"]
    path = root / str(readme)
    if not path.is_file():
        raise FileNotFoundError(f"project.readme missing: {path}")
    return path


def _is_portable_target(target: str) -> bool:
    if target.startswith("#"):
        return True
    if target.startswith("mailto:"):
        return True
    if target.startswith("https://"):
        return True
    return False


def _collect_markdown_targets(text: str) -> list[tuple[str, str]]:
    """Return (label, target) pairs in document order, then callers sort for reports."""
    found: list[tuple[str, str]] = []
    for match in _INLINE_LINK_RE.finditer(text):
        if match.group(1) is not None:
            found.append((match.group(1) or "", match.group(2)))
        else:
            found.append((match.group(3), match.group(4)))
    for match in _REF_DEF_RE.finditer(text):
        found.append((match.group(1), match.group(2)))
    return found


def readme_portability_violations(text: str) -> list[str]:
    """Return deterministic sorted violation lines: `` `label` -> `target` ``."""
    violations: list[str] = []
    for label, target in _collect_markdown_targets(text):
        if not _is_portable_target(target):
            violations.append(f"`{label}` -> `{target}`")
    return sorted(set(violations))


def test_pyproject_readme_is_readme_md() -> None:
    path = _package_readme_path(REPO_ROOT)
    assert path.name == "README.md"
    assert path.resolve() == (REPO_ROOT / "README.md").resolve()


def test_portable_https_link_passes() -> None:
    text = "See [docs](https://example.com/docs/public-sdk.md)."
    assert readme_portability_violations(text) == []


def test_same_document_anchor_passes() -> None:
    text = "Jump to [Who Owns What](#who-owns-what)."
    assert readme_portability_violations(text) == []


def test_https_with_fragment_passes() -> None:
    text = (
        "[x](https://github.com/egallmann/adr-architecture-kit/blob/main/README.md#who-owns-what)"
    )
    assert readme_portability_violations(text) == []


def test_mailto_passes() -> None:
    text = "Contact [maintainers](mailto:maintainers@example.com)."
    assert readme_portability_violations(text) == []


def test_path_like_non_link_text_ignored() -> None:
    text = "The path docs/public-sdk.md is mentioned without a Markdown link."
    assert readme_portability_violations(text) == []


def test_absolute_https_image_passes() -> None:
    text = '![logo](https://example.com/logo.png "Logo")'
    assert readme_portability_violations(text) == []


def test_relative_docs_link_fails() -> None:
    text = "See the [public SDK guide](docs/public-sdk.md)."
    assert readme_portability_violations(text) == [
        "`public SDK guide` -> `docs/public-sdk.md`",
    ]


def test_relative_src_link_fails() -> None:
    text = "See [`decorators.py`](src/adr_kit/decorators.py)."
    assert readme_portability_violations(text) == [
        "``decorators.py`` -> `src/adr_kit/decorators.py`",
    ]


def test_relative_adrs_link_fails() -> None:
    text = "See [ADR-L-0004](adrs/logical/ADR-L-0004-example.yaml)."
    assert readme_portability_violations(text) == [
        "`ADR-L-0004` -> `adrs/logical/ADR-L-0004-example.yaml`",
    ]


def test_relative_schema_link_fails() -> None:
    text = "See [schema](schema/v1.0/README.md)."
    assert readme_portability_violations(text) == [
        "`schema` -> `schema/v1.0/README.md`",
    ]


def test_relative_examples_dir_fails() -> None:
    text = "See [`examples/public-v1/`](examples/public-v1/)."
    assert readme_portability_violations(text) == [
        "``examples/public-v1/`` -> `examples/public-v1/`",
    ]


def test_parent_traversal_fails() -> None:
    text = "See [parent](../something)."
    assert readme_portability_violations(text) == [
        "`parent` -> `../something`",
    ]


def test_http_scheme_fails() -> None:
    text = "See [insecure](http://example.com/docs)."
    assert readme_portability_violations(text) == [
        "`insecure` -> `http://example.com/docs`",
    ]


def test_relative_image_fails() -> None:
    text = "![badge](docs/badge.svg)"
    assert readme_portability_violations(text) == [
        "`badge` -> `docs/badge.svg`",
    ]


def test_reference_style_relative_fails() -> None:
    text = "[label][ref]\n\n[ref]: docs/public-sdk.md\n"
    assert readme_portability_violations(text) == [
        "`ref` -> `docs/public-sdk.md`",
    ]


def test_violation_ordering_is_deterministic() -> None:
    text = "[z](src/z.py) and [a](docs/a.md) and [m](examples/m/)\n" "[a](docs/a.md)\n"
    assert readme_portability_violations(text) == [
        "`a` -> `docs/a.md`",
        "`m` -> `examples/m/`",
        "`z` -> `src/z.py`",
    ]


def test_repository_readme_is_pypi_portable() -> None:
    readme = _package_readme_path(REPO_ROOT).read_text(encoding="utf-8")
    violations = readme_portability_violations(readme)
    assert not violations, (
        "package README has non-portable Markdown link/image targets "
        "(INV-0083; use absolute https:// GitHub blob/tree URLs or #anchors):\n  "
        + "\n  ".join(violations)
    )
