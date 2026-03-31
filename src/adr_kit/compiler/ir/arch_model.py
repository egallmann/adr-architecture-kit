"""Top-level compiler IR model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .entity_graph import EntityGraph
from .parsed_corpus import ParsedCorpus
from .rel_graph import RelGraph
from .unresolved_list import UnresolvedList


@dataclass
class CompilationMeta:
    """Metadata attached to a compilation run."""

    generated_at: datetime | None = None
    generator: str = "adr-compiler"
    scope_root: str | None = None


@dataclass
class ArchModel:
    """Canonical in-memory compilation model."""

    corpus: ParsedCorpus = field(default_factory=ParsedCorpus)
    entities: EntityGraph = field(default_factory=EntityGraph)
    relationships: RelGraph = field(default_factory=RelGraph)
    unresolved: UnresolvedList = field(default_factory=UnresolvedList)
    diagnostics: list[object] = field(default_factory=list)
    metadata: CompilationMeta = field(default_factory=CompilationMeta)
