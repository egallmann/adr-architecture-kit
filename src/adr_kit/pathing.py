"""Path utilities for scope-safe ADR operations."""

from pathlib import Path


def ensure_within_scope(scope_root: Path, path: Path) -> Path:
    """Resolve a path and ensure it stays within the provided scope root."""
    scope_root = Path(scope_root).resolve()
    path = Path(path).resolve()
    path.relative_to(scope_root)
    return path


def manifest_relative_path(scope_root: Path, file_path: Path) -> str:
    """Return a manifest-safe relative path from a scope root."""
    scope_root = Path(scope_root).resolve()
    file_path = ensure_within_scope(scope_root, file_path)
    return file_path.relative_to(scope_root).as_posix()


def scope_temp_dir(scope_root: Path, purpose: str = "pytest") -> Path:
    """Return a scope-owned temporary directory path."""
    scope_root = Path(scope_root).resolve()
    safe_purpose = purpose.replace("\\", "-").replace("/", "-").strip() or "pytest"
    return scope_root / "tests" / ".tmp" / safe_purpose
