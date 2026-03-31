"""Tests for runtime hygiene checks."""

import sys

from adr_kit.validators.runtime_hygiene import (
    find_import_deprecations,
    format_outdated_packages,
    load_direct_dependency_names,
)


def test_load_direct_dependency_names_reads_requirements_and_pyproject(tmp_path):
    requirements = tmp_path / "requirements.txt"
    pyproject = tmp_path / "pyproject.toml"

    requirements.write_text("pydantic>=2.0\n# comment\npyyaml>=6.0\n", encoding="utf-8")
    pyproject.write_text(
        """
[project]
dependencies = ["jsonschema>=4.0", "jinja2>=3.1"]

[project.optional-dependencies]
dev = ["pytest>=7.0"]
""".strip(),
        encoding="utf-8",
    )

    names = load_direct_dependency_names(requirements, pyproject)

    assert {"pydantic", "pyyaml"}.issubset(names)
    if sys.version_info >= (3, 11):
        assert {"jsonschema", "jinja2", "pytest"}.issubset(names)


def test_find_import_deprecations_detects_warning_emitting_package(tmp_path, monkeypatch):
    package_root = tmp_path / "warnpkg"
    package_root.mkdir()
    (package_root / "__init__.py").write_text(
        "import warnings\nwarnings.warn('deprecated package import', DeprecationWarning)\n",
        encoding="utf-8",
    )
    (package_root / "module.py").write_text(
        "import warnings\nwarnings.warn('deprecated module import', PendingDeprecationWarning)\n",
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("warnpkg", None)
    sys.modules.pop("warnpkg.module", None)

    findings = find_import_deprecations("warnpkg")

    messages = [finding.message for finding in findings]
    assert any("deprecated package import" in message for message in messages)
    assert any("deprecated module import" in message for message in messages)


def test_format_outdated_packages_is_readable():
    lines = format_outdated_packages(
        [{"name": "pydantic", "version": "2.8.0", "latest_version": "2.9.0"}]
    )

    assert lines == ["pydantic: 2.8.0 -> 2.9.0"]
