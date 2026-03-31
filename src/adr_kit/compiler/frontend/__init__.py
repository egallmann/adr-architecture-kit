"""Compiler frontend helpers."""

from __future__ import annotations

__all__ = [
    "ArchModelBuilder",
    "CachedADRParser",
    "FileFingerprint",
    "FrontendBuildResult",
    "ParseCacheEntry",
    "build_arch_model",
]


def __getattr__(name: str):
    if name in {"CachedADRParser", "FileFingerprint", "ParseCacheEntry"}:
        from .parser import CachedADRParser, FileFingerprint, ParseCacheEntry

        exports = {
            "CachedADRParser": CachedADRParser,
            "FileFingerprint": FileFingerprint,
            "ParseCacheEntry": ParseCacheEntry,
        }
        return exports[name]
    if name in {"ArchModelBuilder", "FrontendBuildResult", "build_arch_model"}:
        from .builder import ArchModelBuilder, FrontendBuildResult, build_arch_model

        exports = {
            "ArchModelBuilder": ArchModelBuilder,
            "FrontendBuildResult": FrontendBuildResult,
            "build_arch_model": build_arch_model,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
