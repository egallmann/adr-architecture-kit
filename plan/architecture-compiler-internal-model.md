# Architecture Compiler Internal Model

## Purpose

This document defines the normalized architecture representation used during
compilation — the Intermediate Representation (IR). All compilation passes
read from and write to this model. Backend emitters serialize it to output.

---

## 1. Design Principles

**P1: Single source of truth during compilation.**
Once the frontend populates the IR, no pass reads source files.
All analysis and transformation operates on the IR exclusively.

**P2: Mutable with append-only semantics.**
Passes add entities, relationships, and diagnostics. Passes do not
remove entities (only mark them). This makes pass ordering less fragile.

**P3: Pydantic-compatible.**
The IR uses dataclasses for containers but Pydantic models for entities
and relationships (matching existing model definitions). This allows
direct serialization to output without conversion.

**P4: Provenance is first-class.**
Every entity, relationship, and diagnostic records where it came from
(source file, extraction pass, classification). This enables traceability
back to source artifacts.

**P5: Diagnostics are accumulated, not thrown.**
Passes append diagnostics to the shared log. The driver decides when
to halt based on configuration (strict vs lenient).

---

## 2. Top-Level IR Structure

```python
@dataclass
class ArchModel:
    """Central intermediate representation for architecture compilation."""

    # --- Populated by frontend ---
    corpus: ParsedCorpus
    scope: ProjectScope
    namespace: str

    # --- Populated by passes ---
    entities: EntityGraph
    relationships: RelGraph
    unresolved: UnresolvedList

    # --- Cross-cutting ---
    diagnostics: DiagnosticLog
    metadata: CompilationMeta
```

### Lifecycle

```
            Frontend                    Passes                     Backend
               │                          │                          │
  ArchModel    │                          │                          │
  created with │                          │                          │
  empty graphs │                          │                          │
       │       │                          │                          │
       ▼       │                          │                          │
  ┌─────────┐  │  ┌──────────────────┐    │                          │
  │ corpus   │──┼─>│ entities grows    │   │                          │
  │ scope    │  │  │ relationships    │   │                          │
  │ namespace│  │  │   grows          │   │                          │
  │ empty    │  │  │ unresolved grows │   │                          │
  │  graphs  │  │  │ diagnostics      │   │                          │
  └─────────┘  │  │   accumulates    │   │                          │
               │  └──────────────────┘   │                          │
               │           │              │  ┌────────────────────┐  │
               │           ▼              │  │ Read-only access   │  │
               │    ┌──────────────┐      │  │ Serialize to YAML  │  │
               │    │ Fully        │──────┼─>│ Emit files         │  │
               │    │ populated    │      │  └────────────────────┘  │
               │    │ ArchModel    │      │                          │
               │    └──────────────┘      │                          │
```

---

## 3. ParsedCorpus

The corpus is the typed AST forest — all successfully parsed source artifacts.

```python
@dataclass
class SourceLocation:
    """Where a source artifact lives on disk."""
    absolute_path: Path
    scope_relative: str       # forward-slash path relative to scope root
    file_size: int
    mtime: float              # last-modified timestamp for cache key

@dataclass
class ParsedCorpus:
    """All parsed source artifacts within scope."""

    logical_adrs: list[tuple[LogicalADR, SourceLocation]]
    physical_adrs: list[tuple[PhysicalADR, SourceLocation]]      # legacy ADR-P
    system_adrs: list[tuple[PhysicalSystemADR, SourceLocation]]
    component_adrs: list[tuple[PhysicalComponentADR, SourceLocation]]
    invariants: list[tuple[StandaloneInvariant, SourceLocation]]
    project_metadata: Optional[ProjectMetadata]

    @property
    def all_adrs(self) -> Iterable[tuple[ADRFrontmatter, SourceLocation]]:
        """Iterate all ADRs regardless of type."""
        yield from self.logical_adrs
        yield from self.physical_adrs
        yield from self.system_adrs
        yield from self.component_adrs

    @property
    def source_coverage(self) -> SourceCoverageSummary:
        """Current model: SourceCoverageSummary for architecture index."""
        return SourceCoverageSummary(
            logical_adrs=len(self.logical_adrs),
            physical_adrs=len(self.physical_adrs),
            physical_system_adrs=len(self.system_adrs),
            physical_component_adrs=len(self.component_adrs),
            standalone_invariants=len(self.invariants),
        )

    def lookup_adr(self, adr_id: str) -> Optional[tuple[ADRFrontmatter, SourceLocation]]:
        """Find ADR by ID across all types."""
        for adr, loc in self.all_adrs:
            if adr.id == adr_id:
                return adr, loc
        return None
```

**Relationship to current code:** Today each generator independently calls
`parser.parse_logical_adr()`, `parser.parse_adr()`, etc. The `ParsedCorpus`
replaces this with a single pass that populates a shared collection.

---

## 4. EntityGraph

The entity graph is an indexed collection of architecture entities.

```python
class EntityGraph:
    """Mutable, indexed collection of architecture entities."""

    def __init__(self):
        self._entities: dict[str, NormalizedEntity] = {}    # keyed by entity ID
        self._by_type: dict[str, list[str]] = {}            # entity_type -> [entity_ids]
        self._by_adr: dict[str, list[str]] = {}             # adr_id -> [entity_ids]

    # --- Mutation (used by extraction passes) ---

    def add(self, entity: NormalizedEntity, allow_reference_merge: bool = False) -> None:
        """Add entity. Raises on duplicate ID unless allow_reference_merge."""
        ...

    def update_completeness(self, entity_id: str, completeness: Completeness) -> None:
        """Update completeness metadata."""
        ...

    def append_source_ref(self, entity_id: str, ref: SourceRef) -> None:
        """Add a non-canonical source reference."""
        ...

    # --- Query (used by relationship derivation, backend emitters) ---

    def get(self, entity_id: str) -> Optional[NormalizedEntity]:
        ...

    def contains(self, entity_id: str) -> bool:
        ...

    def by_type(self, entity_type: str) -> list[NormalizedEntity]:
        """All entities of given type, sorted by ID."""
        ...

    def by_adr(self, adr_id: str) -> list[NormalizedEntity]:
        """All entities declared in given ADR."""
        ...

    def all_sorted(self) -> list[NormalizedEntity]:
        """All entities sorted by (entity_type, id) — deterministic."""
        ...

    @property
    def ids(self) -> set[str]:
        ...

    def __len__(self) -> int:
        ...

    def __iter__(self) -> Iterator[NormalizedEntity]:
        """Iterate in deterministic order."""
        yield from self.all_sorted()
```

**Entity model:** Uses the existing `NormalizedEntity` Pydantic model from
`models/architecture_discovery.py`. No changes to the model itself.

**Type index:** Maintained on insertion for O(1) type-filtered queries.
This replaces the current `_filtered()` method that does a full scan.

**ADR index:** Maps ADR ID → entity IDs declared within it. Built during
extraction (M3, M4) when entities are added with their canonical source.

---

## 5. RelGraph

The relationship graph is an indexed edge collection.

```python
class RelGraph:
    """Mutable, indexed collection of architecture relationships."""

    def __init__(self):
        self._relationships: dict[str, RelationshipRecord] = {}  # keyed by relationship_id
        self._from_index: dict[str, list[str]] = {}              # entity_id -> [rel_ids] outbound
        self._to_index: dict[str, list[str]] = {}                # entity_id -> [rel_ids] inbound
        self._by_type: dict[str, list[str]] = {}                 # rel_type -> [rel_ids]

    # --- Mutation ---

    def add(
        self,
        entities: EntityGraph,
        relationship_type: str,
        from_id: str,
        to_id: str,
        source_ref: str,
        evidence: Iterable[str],
        classification: str = "explicit",
        confidence: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> Optional[RelationshipRecord]:
        """
        Add a relationship. Returns None if from_id or to_id not in entities.
        Updates the entity's relationship summary automatically.
        Deduplicates by relationship_id = "{type}:{from}:{to}".
        """
        ...

    # --- Query ---

    def get(self, relationship_id: str) -> Optional[RelationshipRecord]:
        ...

    def outbound(self, entity_id: str) -> list[RelationshipRecord]:
        """All relationships where entity_id is the source."""
        ...

    def inbound(self, entity_id: str) -> list[RelationshipRecord]:
        """All relationships where entity_id is the target."""
        ...

    def by_type(self, relationship_type: str) -> list[RelationshipRecord]:
        ...

    def between(self, from_id: str, to_id: str) -> list[RelationshipRecord]:
        """All relationships between two entities (any type)."""
        ...

    def all_sorted(self) -> list[RelationshipRecord]:
        """All relationships sorted by relationship_id — deterministic."""
        ...

    # --- Analysis (used by graph analysis pass) ---

    def adjacency_list(self) -> dict[str, list[str]]:
        """Entity ID -> list of target entity IDs (all relationship types)."""
        ...

    def typed_adjacency(self, relationship_type: str) -> dict[str, list[str]]:
        """Adjacency list for a specific relationship type."""
        ...

    def __len__(self) -> int:
        ...
```

**Relationship model:** Uses the existing `RelationshipRecord` Pydantic model.

**Automatic summary update:** When `add()` creates a relationship, it also
updates the source entity's `EntityRelationshipSummary`. This mirrors the
current behavior in `_add_relationship()` (line 150-153) where the entity's
relationship summary list is appended.

**Deduplication:** Relationship identity is `"{type}:{from}:{to}"`. Adding
a duplicate is a no-op (current behavior).

---

## 6. UnresolvedList

```python
class UnresolvedList:
    """Collection of unresolved architecture signals."""

    def __init__(self):
        self._records: dict[str, UnresolvedRecord] = {}  # keyed by unresolved ID

    def add(
        self,
        gap_id: str,
        gap_class: str,
        gap_type: str,
        source_entity_id: str,
        severity: str,
        source_ref: str,
        evidence: list[str],
        provenance: DiscoveryProvenance,
        related_entity_id: Optional[str] = None,
        expected_relationship: Optional[str] = None,
    ) -> None:
        """Add an unresolved record. Raises on duplicate ID."""
        ...

    def all_sorted(self) -> list[UnresolvedRecord]:
        """Sorted by ID — deterministic."""
        ...

    def by_source(self, source_entity_id: str) -> list[UnresolvedRecord]:
        ...

    def __len__(self) -> int:
        ...
```

**Model:** Uses existing `UnresolvedRecord` Pydantic model.

---

## 7. DiagnosticLog

```python
class DiagnosticLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass(frozen=True)
class Diagnostic:
    """Structured compilation diagnostic."""
    level: DiagnosticLevel
    stage: str                    # e.g., "frontend.parse", "pass.validate", "backend.registry"
    code: str                     # machine-readable, e.g., "E001", "W002"
    message: str
    source: Optional[str] = None  # file path, entity ID, or ADR ID
    field: Optional[str] = None   # specific field within source

class DiagnosticLog:
    """Append-only diagnostic accumulator."""

    def __init__(self):
        self._items: list[Diagnostic] = []

    def error(self, stage: str, code: str, message: str, **kwargs) -> None:
        self._items.append(Diagnostic(DiagnosticLevel.ERROR, stage, code, message, **kwargs))

    def warning(self, stage: str, code: str, message: str, **kwargs) -> None:
        self._items.append(Diagnostic(DiagnosticLevel.WARNING, stage, code, message, **kwargs))

    def info(self, stage: str, code: str, message: str, **kwargs) -> None:
        self._items.append(Diagnostic(DiagnosticLevel.INFO, stage, code, message, **kwargs))

    @property
    def has_errors(self) -> bool:
        return any(d.level == DiagnosticLevel.ERROR for d in self._items)

    @property
    def error_count(self) -> int:
        return sum(1 for d in self._items if d.level == DiagnosticLevel.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self._items if d.level == DiagnosticLevel.WARNING)

    def all_sorted(self) -> list[Diagnostic]:
        """Deterministic ordering: (level desc, stage, source, code)."""
        return sorted(self._items, key=lambda d: (d.level.value, d.stage, d.source or "", d.code))

    def summary(self) -> str:
        """Human-readable summary line."""
        return f"{self.error_count} errors, {self.warning_count} warnings"
```

**Relationship to current code:** Replaces:
- `ValidationError` / `ValidationResult` in `adr_validator.py`
- `print()` statements for warnings in generators
- `ValueError` exceptions for bundle consistency failures

---

## 8. CompilationMeta

```python
@dataclass
class CompilationMeta:
    """Metadata about the compilation run itself."""
    compiler_version: str             # from package version
    generator_id: str = "adr-architecture-compiler"
    started_at: datetime              # UTC
    completed_at: Optional[datetime] = None
    scope_root: Path
    scope_name: str
    namespace: str
    pinned_timestamp: Optional[datetime] = None  # for reproducible builds
    config: CompilerConfig

    @property
    def generated_at(self) -> datetime:
        """Timestamp for output artifacts. Uses pinned if set."""
        return self.pinned_timestamp or self.completed_at or self.started_at
```

---

## 9. CompilerConfig

```python
@dataclass
class CompilerConfig:
    """Configuration for a compilation run."""
    strict: bool = False              # halt on first error
    lenient: bool = False             # exclude invalid artifacts, continue
    emit: set[str] = field(default_factory=lambda: {
        "registries", "manifest", "legacy", "index", "markdown"
    })
    lint: bool = False                # enable M10
    analyze: bool = False             # enable M11
    timestamp: Optional[datetime] = None  # pin generated_at for reproducibility
    output_dir: Optional[Path] = None     # override output location
```

---

## 10. CompilationResult

The final output of the compiler driver.

```python
@dataclass
class OutputArtifact:
    """A single output file produced by the compiler."""
    path: Path                  # relative to output root
    content: bytes              # serialized content
    kind: str                   # "registry", "manifest", "markdown", "index", "legacy"
    integrity_header: Optional[str] = None

@dataclass
class CompilationStatistics:
    """Summary statistics for the compilation."""
    source_files: int
    parse_errors: int
    entities_extracted: int
    relationships_derived: int
    unresolved_detected: int
    artifacts_emitted: int

@dataclass
class CompilationResult:
    """Complete result of an architecture compilation."""
    success: bool
    artifacts: list[OutputArtifact]
    diagnostics: DiagnosticLog
    statistics: CompilationStatistics
    model: ArchModel                   # retained for programmatic consumers
    duration_ms: int
```

---

## 11. Entity Type Map

The normalized entity types and their properties in the IR:

### Core Entity Types (currently emitted to registries)

| Type | ID Pattern | Extracted From | Key Metadata Fields |
|---|---|---|---|
| `adr` | ADR-{L,V,P,PS,PC}-XXXX | All ADR files | status, domains, tags |
| `capability` | CAP-XXXX | LogicalADR.capabilities | adr_id, implemented_by_components, enabled_by_decisions |
| `decision` | DEC-XXXX | LogicalADR.decisions | adr_id, related_invariants, enforces_invariants, enables_capabilities, governs_components, supersedes, refines |
| `invariant` | INV-XXXX | LogicalADR.invariants + StandaloneInvariant | adr_id/defined_in, scope, statement, enforcement_level, declaration_mode, upheld_by_decisions |
| `component` | COMP-XXXX / COMP-{NAME} | PhysicalComponentADR.component_specs | adr_id, technologies, module_path, implements_capabilities, implements_system |
| `system` | SYS-XXXX | PhysicalSystemADR (derived) | adr_id, implements_logical, technologies |

### Extended Entity Types (in IR but not currently emitted to separate registries)

| Type | ID Pattern | Extracted From | Key Metadata Fields |
|---|---|---|---|
| `constraint` | CONST-XXXX | LogicalADR.constraints | type, description, rationale |
| `boundary` | BOUND-XXXX | LogicalADR.boundaries | name, description, rationale |
| `nfr` | NFR-XXXX | LogicalADR.nfrs | category, requirement, acceptance_criteria |
| `contract` | CONTRACT-XXXX | LogicalADR.contracts | parties, protocol, guarantees |
| `gap` | GAP-XXXX | LogicalADR.gaps | question, impact, blocking |
| `interface` | IFACE-XXXX | ComponentSpec.interfaces | type, specification |
| `integration` | INTEG-XXXX | PhysicalComponentADR.integration_points | systems, protocol |
| `impl_decision` | IMPL-XXXX | PhysicalComponentADR.impl_decisions | summary, rationale, implements_invariants |

**Note:** The current system only extracts core types into `NormalizedEntity`.
The extended types exist in the Pydantic models but are not surfaced in
registries. The IR should capture all types to support future analysis passes
(e.g., lint rules about orphan constraints) and future backend emitters
(e.g., interface registry, constraint registry).

The `NormalizedEntity.entity_type` Literal currently restricts to:
`"adr" | "system" | "component" | "decision" | "capability" | "invariant"`

For the compiler IR, this should be extended to include all entity types.
The backend registry emitter can continue filtering to the current subset.

---

## 12. Relationship Type System in the IR

```python
RELATIONSHIP_TYPES = {
    # Structural (entity containment)
    "declared_in":     {"from": "any",        "to": "adr",        "inverse": None},

    # ADR-level references
    "references":      {"from": "adr",        "to": "adr",        "inverse": None},

    # Capability realization
    "implemented_by":  {"from": "capability",  "to": "component",  "inverse": None},
    "enabled_by":      {"from": "capability",  "to": "decision",   "inverse": "enables"},
    "enables":         {"from": "decision",    "to": "capability",  "inverse": "enabled_by"},

    # Governance
    "enforces":        {"from": "decision|invariant", "to": "invariant|any", "inverse": None},
    "governs":         {"from": "decision",    "to": "component",   "inverse": None},

    # Physical realization
    "embodied_in":     {"from": "component",   "to": "system",      "inverse": None},

    # Evolution
    "supersedes":      {"from": "any",         "to": "any",         "inverse": "superseded_by"},
    "superseded_by":   {"from": "any",         "to": "any",         "inverse": "supersedes"},
    "refines":         {"from": "decision",    "to": "decision",    "inverse": None},

    # General
    "related_to":      {"from": "any",         "to": "any",         "inverse": None},
}
```

### Provenance Classification

| Classification | Meaning | Confidence |
|---|---|---|
| `explicit` | Directly declared in source artifact field | 1.0 |
| `derived` | Computed as inverse of an explicit relationship | 1.0 |
| `heuristic` | Inferred from indirect evidence (e.g., component dependencies) | 0.8 |

### Evidence Model

Each relationship carries an `evidence` list — strings identifying the
source references that justify the relationship. Format:
- ADR ID: `"ADR-L-0001"`
- Entity reference: `"ADR-L-0001#CAP-0001"`
- Component reference: `"ADR-PC-0001#COMP-SCHEMA-VALIDATOR"`

---

## 13. Multi-Scope Compilation Model

When compiling a workspace with multiple scopes (INV-0019):

```python
@dataclass
class WorkspaceModel:
    """Multi-scope compilation result."""
    scopes: dict[str, ArchModel]        # scope_name -> ArchModel
    cross_scope_refs: list[CrossScopeRef]  # references between scopes

@dataclass
class CrossScopeRef:
    from_scope: str
    from_entity_id: str
    to_scope: str
    to_entity_id: str
    relationship_type: str
```

**Current behavior:** Each scope compiles independently. The compiler
should detect cross-scope references (an ADR in scope A referencing
an entity in scope B) and emit them as cross-scope refs rather than
unresolved records.

**This is a future extension.** The initial compiler compiles one scope at a time.

---

## 14. IR Invariants

These properties must hold for any valid `ArchModel` after compilation:

1. **Entity uniqueness:** No two entities share the same ID
2. **Relationship endpoints exist:** Every relationship's from/to entity exists in the entity graph
3. **Relationship summary consistency:** For every entry in an entity's relationship summary, a corresponding RelationshipRecord exists
4. **Unresolved source exists:** Every unresolved record's source_entity_id exists in the entity graph
5. **Provenance completeness:** Every entity has non-empty provenance with valid source_ref
6. **Canonical source validity:** Every entity's canonical_source.artifact_path points to a file in the corpus
7. **Deterministic ordering:** `all_sorted()` on any collection returns the same order for the same data
8. **Type consistency:** Entity ID prefix matches entity_type (CAP-XXXX is capability, DEC-XXXX is decision, etc.)

These invariants are enforced by M9 (Validate Bundle Consistency).

---

## 15. Mapping: Current Code → IR Components

| Current Code | IR Component | Notes |
|---|---|---|
| `entities: Dict[str, NormalizedEntity]` (line 289) | `EntityGraph._entities` | Same dict, wrapped with index |
| `relationships: Dict[str, RelationshipRecord]` (line 290) | `RelGraph._relationships` | Same dict, wrapped with index |
| `unresolved: List[UnresolvedRecord]` (line 291) | `UnresolvedList._records` | Promoted to dict for dedup |
| `invariant_mentions: Dict[str, List[...]]` (line 292) | Pass-local state in M5 | Not in IR; intermediate to invariant resolution |
| `system_ids: Dict[str, str]` (line 293) | Pass-local state in M4 | Maps ADR-PS-XXXX → SYS-XXXX; not in IR |
| `add_entity()` closure (line 295) | `EntityGraph.add()` | Same logic, method instead of closure |
| `_add_relationship()` (line 122) | `RelGraph.add()` | Same logic including entity summary update |
| `_unresolved()` (line 155) | `UnresolvedList.add()` | Same logic |
| `_validate_bundle()` (line 190) | M9 pass | Same checks, diagnostics instead of ValueError |
| `_filtered()` (line 106) | `EntityGraph.by_type()` | O(1) via type index vs O(n) scan |

---

## 16. Risks and Constraints

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| IR data structures add overhead vs current flat dicts | Negligible for current scale; could matter at 10K entities | Profile early; keep index structures lightweight |
| EntityGraph mutation by passes makes debugging hard | Difficult to trace which pass added/modified an entity | Each entity records `provenance.extraction_phase`; add pass-level logging |
| Pydantic model changes affect IR serialization | Backend emitters depend on stable model fields | Keep using existing Pydantic models; IR containers are plain Python |
| Multi-scope WorkspaceModel complexity | Cross-scope resolution is non-trivial | Defer to future; single-scope first |

### Constraints

1. **IR uses existing Pydantic models:** `NormalizedEntity`, `RelationshipRecord`, `UnresolvedRecord` are unchanged. The IR wraps them in indexed containers, not replaces them.
2. **No serialization of IR itself:** The IR is ephemeral — it exists only during compilation. Only backend emitters serialize output. The IR is never written to disk (except potentially as a compilation cache in Phase 7).
3. **Thread safety not required:** Compilation is single-threaded. The IR is not concurrent-safe.
4. **Memory budget:** The IR holds all entities + relationships + diagnostics in memory. For the current 31 ADRs producing ~150 entities and ~90 relationships, this is trivial. For projected scale (1000 ADRs, ~5000 entities), still well within memory budget (<100MB).
