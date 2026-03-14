"""Structured compiler diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


class DiagnosticLevel(IntEnum):
    """Diagnostic severity ordering."""

    INFO = 10
    WARNING = 20
    ERROR = 30


@dataclass(frozen=True)
class Diagnostic:
    """Single compiler diagnostic."""

    level: DiagnosticLevel
    code: str
    message: str
    path: str | None = None
    source_ref: str | None = None

    def sort_key(self) -> tuple[int, str, str, str, str]:
        return (
            int(self.level),
            self.path or "",
            self.source_ref or "",
            self.code,
            self.message,
        )


class DiagnosticLog:
    """Deterministic diagnostic accumulator."""

    def __init__(self) -> None:
        self._diagnostics: list[Diagnostic] = []

    def add(
        self,
        level: DiagnosticLevel,
        code: str,
        message: str,
        *,
        path: str | Path | None = None,
        source_ref: str | None = None,
    ) -> Diagnostic:
        diagnostic = Diagnostic(
            level=level,
            code=code,
            message=message,
            path=str(path).replace("\\", "/") if path is not None else None,
            source_ref=source_ref,
        )
        self._diagnostics.append(diagnostic)
        return diagnostic

    def info(self, code: str, message: str, **kwargs: object) -> Diagnostic:
        return self.add(DiagnosticLevel.INFO, code, message, **kwargs)

    def warning(self, code: str, message: str, **kwargs: object) -> Diagnostic:
        return self.add(DiagnosticLevel.WARNING, code, message, **kwargs)

    def error(self, code: str, message: str, **kwargs: object) -> Diagnostic:
        return self.add(DiagnosticLevel.ERROR, code, message, **kwargs)

    @property
    def has_errors(self) -> bool:
        return any(item.level == DiagnosticLevel.ERROR for item in self._diagnostics)

    def clear(self) -> None:
        self._diagnostics.clear()

    def extend(self, diagnostics: list[Diagnostic]) -> None:
        self._diagnostics.extend(diagnostics)

    def as_list(self) -> list[Diagnostic]:
        return sorted(self._diagnostics, key=lambda item: item.sort_key())

