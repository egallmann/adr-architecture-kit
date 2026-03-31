"""Runtime hygiene checks for deprecated APIs and dependency posture."""

from __future__ import annotations

import importlib
import json
import pkgutil
import re
import subprocess
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set


DEPRECATION_WARNING_TYPES = (DeprecationWarning, PendingDeprecationWarning, FutureWarning)


@dataclass(frozen=True)
class RuntimeHygieneFinding:
    """A single hygiene finding."""

    check: str
    target: str
    message: str


def find_import_deprecations(package_name: str = "adr_kit") -> List[RuntimeHygieneFinding]:
    """Import package modules and capture deprecation-style warnings."""
    findings: List[RuntimeHygieneFinding] = []
    package_warnings = []

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        package = importlib.import_module(package_name)
        package_warnings = list(captured)

    for warning in package_warnings:
        if issubclass(warning.category, DEPRECATION_WARNING_TYPES):
            findings.append(
                RuntimeHygieneFinding(
                    check="deprecated-import",
                    target=package_name,
                    message=str(warning.message),
                )
            )

    module_names = [package_name]
    if hasattr(package, "__path__"):
        module_names.extend(
            module_info.name
            for module_info in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}.")
        )

    for module_name in module_names:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            importlib.import_module(module_name)

        for warning in captured:
            if issubclass(warning.category, DEPRECATION_WARNING_TYPES):
                findings.append(
                    RuntimeHygieneFinding(
                        check="deprecated-import",
                        target=module_name,
                        message=str(warning.message),
                    )
                )

    return findings


def load_direct_dependency_names(
    requirements_path: Optional[Path] = None,
    pyproject_path: Optional[Path] = None,
) -> Set[str]:
    """Load direct dependency names from requirements.txt and pyproject.toml when available."""
    names: Set[str] = set()

    if requirements_path and requirements_path.exists():
        for line in requirements_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue
            match = re.match(r"^([A-Za-z0-9_.-]+)", stripped)
            if match:
                names.add(match.group(1).lower().replace("_", "-"))

    if pyproject_path and pyproject_path.exists():
        try:
            import tomllib  # Python 3.11+

            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            project = data.get("project", {})
            dependencies = project.get("dependencies", [])
            optional_dependencies = project.get("optional-dependencies", {})
            for dependency in dependencies:
                match = re.match(r"^([A-Za-z0-9_.-]+)", dependency)
                if match:
                    names.add(match.group(1).lower().replace("_", "-"))
            for dep_list in optional_dependencies.values():
                for dependency in dep_list:
                    match = re.match(r"^([A-Za-z0-9_.-]+)", dependency)
                    if match:
                        names.add(match.group(1).lower().replace("_", "-"))
        except ModuleNotFoundError:
            pass

    return names


def list_outdated_packages(
    package_names: Optional[Set[str]] = None,
    python_executable: str = sys.executable,
) -> List[dict]:
    """Return outdated packages for the current environment."""
    completed = subprocess.run(
        [python_executable, "-m", "pip", "list", "--outdated", "--format=json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout or "[]")
    if not package_names:
        return payload

    normalized = {name.lower().replace("_", "-") for name in package_names}
    return [
        item for item in payload
        if item.get("name", "").lower().replace("_", "-") in normalized
    ]


def run_pip_audit(
    requirements_path: Path,
    python_executable: str = sys.executable,
) -> subprocess.CompletedProcess[str]:
    """Run pip-audit against the given requirements file."""
    return subprocess.run(
        [python_executable, "-m", "pip_audit", "-r", str(requirements_path), "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )


def format_outdated_packages(packages: Sequence[dict]) -> List[str]:
    """Format outdated package entries for human-readable output."""
    lines = []
    for item in packages:
        name = item.get("name", "<unknown>")
        current = item.get("version", "<unknown>")
        latest = item.get("latest_version", "<unknown>")
        lines.append(f"{name}: {current} -> {latest}")
    return lines


def format_findings(findings: Iterable[RuntimeHygieneFinding]) -> List[str]:
    """Format runtime hygiene findings for human-readable output."""
    return [f"{finding.target}: {finding.message}" for finding in findings]
