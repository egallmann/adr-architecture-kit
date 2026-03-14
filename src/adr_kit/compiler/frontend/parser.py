"""Cached parser wrapper for compiler frontend flows."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ...parser import ADRParser


@dataclass(frozen=True)
class FileFingerprint:
    """Cache key for parsed files."""

    path: str
    mtime_ns: int
    size: int

    @classmethod
    def from_path(cls, path: Path | str) -> "FileFingerprint":
        resolved = Path(path).resolve()
        stat = resolved.stat()
        return cls(path=str(resolved), mtime_ns=stat.st_mtime_ns, size=stat.st_size)


@dataclass
class ParseCacheEntry:
    """Cached parse result."""

    fingerprint: FileFingerprint
    value: Any


class CachedADRParser:
    """Compiler-facing parser wrapper with metadata-keyed caching."""

    def __init__(self, parser: ADRParser | None = None) -> None:
        self.parser = parser or ADRParser()
        self._cache: dict[tuple[str, str], ParseCacheEntry] = {}

    def clear(self) -> None:
        self._cache.clear()

    def parse_yaml(self, file_path: Path | str) -> dict[str, Any]:
        return self._parse_cached("parse_yaml", file_path, self.parser.parse_yaml)

    def parse_logical_adr(self, file_path: Path | str) -> Any:
        return self._parse_cached("parse_logical_adr", file_path, self.parser.parse_logical_adr)

    def parse_physical_adr(self, file_path: Path | str) -> Any:
        return self._parse_cached("parse_physical_adr", file_path, self.parser.parse_physical_adr)

    def parse_physical_system_adr(self, file_path: Path | str) -> Any:
        return self._parse_cached("parse_physical_system_adr", file_path, self.parser.parse_physical_system_adr)

    def parse_physical_component_adr(self, file_path: Path | str) -> Any:
        return self._parse_cached(
            "parse_physical_component_adr",
            file_path,
            self.parser.parse_physical_component_adr,
        )

    def parse_invariant(self, file_path: Path | str) -> Any:
        return self._parse_cached("parse_invariant", file_path, self.parser.parse_invariant)

    def parse_project_metadata(self, file_path: Path | str) -> Any:
        return self._parse_cached("parse_project_metadata", file_path, self.parser.parse_project_metadata)

    def parse_manifest(self, file_path: Path | str) -> Any:
        return self._parse_cached("parse_manifest", file_path, self.parser.parse_manifest)

    def parse_adr(self, file_path: Path | str) -> Any:
        return self._parse_cached("parse_adr", file_path, self.parser.parse_adr)

    def _parse_cached(
        self,
        method_name: str,
        file_path: Path | str,
        parse_method: Callable[[Path | str], Any],
    ) -> Any:
        fingerprint = FileFingerprint.from_path(file_path)
        cache_key = (method_name, fingerprint.path)
        cached = self._cache.get(cache_key)
        if cached is not None and cached.fingerprint == fingerprint:
            return deepcopy(cached.value)

        parsed = parse_method(fingerprint.path)
        self._cache[cache_key] = ParseCacheEntry(fingerprint=fingerprint, value=deepcopy(parsed))
        return deepcopy(parsed)
