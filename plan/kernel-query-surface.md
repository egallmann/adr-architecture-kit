# Kernel Query Surface

## Purpose

This document defines the query operations the STE Kernel uses to interrogate
the compiled architecture model. All queries operate against in-memory indexes
built from the 4 contract registries. No query touches ADR source files.

---

## 1. Query Design Principles

**Q1: Queries are pure reads.**
No query mutates the model. The model is frozen after construction.

**Q2: Queries return domain objects, not raw YAML.**
Every query returns typed Python objects (`NormalizedEntity`, `RelationshipRecord`,
or derived result types). The kernel never processes raw dicts from registries.

**Q3: Missing data returns None or empty, never raises.**
A query for a nonexistent entity returns `None`. A traversal with no matches
returns an empty list. Errors are reserved for model corruption (contract violations).

**Q4: Traversals are bounded.**
Any query that follows relationships has a configurable depth limit to prevent
unbounded graph walks. Default max depth: 10.

**Q5: Results are deterministic.**
All list-returning queries return results in deterministic order (sorted by entity ID
or relationship ID) matching the registry ordering guarantees.

---

## 2. Query Categories

```
┌─────────────────────────────────────────────────┐
│              Kernel Query Surface                 │
│                                                   │
│  ENTITY QUERIES          GRAPH QUERIES            │
│  ─────────────           ────────────             │
│  get_entity              trace_relationships      │
│  get_system              trace_decision            │
│  get_component           trace_capability          │
│  get_capability          impact_of                 │
│  get_decision            dependencies_of           │
│  get_invariant           path_between              │
│                                                   │
│  COLLECTION QUERIES      GAP QUERIES              │
│  ─────────────────       ───────────              │
│  list_entities           get_unresolved            │
│  list_by_type            unresolved_for            │
│  list_by_domain          critical_gaps             │
│  list_by_status          coverage_gaps             │
│  list_relationships                               │
│                                                   │
│  INTROSPECTION           AGGREGATE QUERIES        │
│  ──────────────          ─────────────────        │
│  model_metadata          architecture_summary      │
│  entity_count            invariant_coverage        │
│  relationship_count      capability_realization    │
│  fingerprint             decision_impact_map       │
│                                                   │
└─────────────────────────────────────────────────┘
```

---

## 3. Entity Queries

### get_entity

Retrieve any entity by ID, regardless of type.

```python
def get_entity(entity_id: str) -> Optional[NormalizedEntity]:
    """
    Lookup a single entity by its unique ID.

    Args:
        entity_id: Entity identifier (e.g., "CAP-0001", "COMP-0010", "ADR-L-0001")

    Returns:
        NormalizedEntity if found, None otherwise.

    Example:
        entity = model.get_entity("CAP-0001")
        # entity.name == "Machine-Verifiable Architecture Documentation"
        # entity.entity_type == "capability"
        # entity.canonical_source.source_ref == "ADR-L-0001#CAP-0001"
    """
```

**Implementation:** `EntityIndex._by_id[entity_id]` — O(1)

---

### get_system

Retrieve a system entity with its topology context.

```python
@dataclass
class SystemView:
    """System entity with resolved topology."""
    entity: NormalizedEntity
    source_adr: Optional[NormalizedEntity]       # The ADR-PS that defines this system
    components: list[NormalizedEntity]            # Components embodied_in this system
    implements_logical: list[NormalizedEntity]    # Logical ADRs this system implements
    technologies: list[str]                       # From metadata

def get_system(system_id: str) -> Optional[SystemView]:
    """
    Retrieve a system entity with resolved components and source ADR.

    Args:
        system_id: System identifier (e.g., "SYS-0001")

    Returns:
        SystemView if found, None if system_id doesn't exist or isn't a system.

    Example:
        sys = model.get_system("SYS-0001")
        # sys.entity.name == "ADR Architecture Kit Discovery and Indexing System"
        # sys.components == [COMP-0010, ...]
        # sys.technologies == ["python", "pyyaml", "click"]
    """
```

**Implementation:**
1. `EntityIndex._systems[system_id]` — O(1)
2. `RelIndex._inbound_typed[(system_id, "embodied_in")]` → component IDs — O(1)
3. Resolve each component ID → `EntityIndex.get()` — O(k) for k components
4. Resolve `metadata.adr_id` → source ADR — O(1)
5. Resolve `metadata.implements_logical` → logical ADRs — O(m)

---

### get_component

Retrieve a component entity with its architectural context.

```python
@dataclass
class ComponentView:
    """Component entity with resolved context."""
    entity: NormalizedEntity
    source_adr: Optional[NormalizedEntity]         # The ADR-PC that defines this component
    system: Optional[NormalizedEntity]              # System this component is embodied in
    implements_capabilities: list[NormalizedEntity]  # Capabilities this component realizes
    governed_by_decisions: list[NormalizedEntity]    # Decisions that govern this component
    dependencies: list[NormalizedEntity]             # Components this depends on (related_to)
    module_path: Optional[str]                       # From metadata
    technologies: list[str]                          # From metadata

def get_component(component_id: str) -> Optional[ComponentView]:
    """
    Retrieve a component with its full architectural context.

    Args:
        component_id: Component identifier (e.g., "COMP-0010", "COMP-SCHEMA-VALIDATOR")

    Returns:
        ComponentView if found, None otherwise.

    Example:
        comp = model.get_component("COMP-0010")
        # comp.entity.name == "Entity Registry Generator and Query Surface"
        # comp.system.entity.name == "ADR Architecture Kit Discovery and Indexing System"
        # comp.module_path == "src/adr_kit/generators/entity_registry_generator.py"
        # comp.implements_capabilities == [CAP-0018]
    """
```

**Implementation:**
1. `EntityIndex._components[component_id]` — O(1)
2. `RelIndex._outbound_typed[(component_id, "embodied_in")]` → system — O(1)
3. `RelIndex._inbound_typed[(component_id, "implemented_by")]` → capabilities (inverted: capabilities → implemented_by → this component) — O(1)
4. `RelIndex._inbound_typed[(component_id, "governs")]` → decisions — O(1)
5. `RelIndex._outbound_typed[(component_id, "related_to")]` → dependencies — O(1)

---

### get_capability

Retrieve a capability entity with its realization and enablement chain.

```python
@dataclass
class CapabilityView:
    """Capability entity with realization context."""
    entity: NormalizedEntity
    source_adr: Optional[NormalizedEntity]          # Logical ADR defining this capability
    implemented_by: list[NormalizedEntity]           # Components realizing this capability
    enabled_by_decisions: list[NormalizedEntity]     # Decisions enabling this capability
    domains: list[str]                               # From metadata
    realization_status: str                          # "realized" | "unrealized" | "partial"

def get_capability(capability_id: str) -> Optional[CapabilityView]:
    """
    Retrieve a capability with its realization chain.

    Args:
        capability_id: Capability identifier (e.g., "CAP-0001")

    Returns:
        CapabilityView if found, None otherwise.

    Example:
        cap = model.get_capability("CAP-0018")
        # cap.entity.name == "Entity Lifecycle Registry"
        # cap.implemented_by == [COMP-0010]
        # cap.realization_status == "realized"
    """
```

**Realization status derivation:**
- `"realized"`: `implemented_by` is non-empty
- `"unrealized"`: `implemented_by` is empty AND no unresolved `implemented_by` gap exists
- `"partial"`: some implementing components exist but unresolved gaps remain

---

### get_decision

Retrieve a decision entity with its governance scope.

```python
@dataclass
class DecisionView:
    """Decision entity with governance context."""
    entity: NormalizedEntity
    source_adr: Optional[NormalizedEntity]
    enforces_invariants: list[NormalizedEntity]
    enables_capabilities: list[NormalizedEntity]
    governs_components: list[NormalizedEntity]
    supersedes: list[NormalizedEntity]
    superseded_by: list[NormalizedEntity]
    refines: list[NormalizedEntity]
    is_current: bool                                 # True if not superseded

def get_decision(decision_id: str) -> Optional[DecisionView]:
    """
    Retrieve a decision with its full governance scope.

    Args:
        decision_id: Decision identifier (e.g., "DEC-0001")

    Returns:
        DecisionView if found, None otherwise.
    """
```

**`is_current` derivation:** True if `superseded_by` is empty.

---

### get_invariant

Retrieve an invariant entity with its enforcement chain.

```python
@dataclass
class InvariantView:
    """Invariant entity with enforcement context."""
    entity: NormalizedEntity
    statement: str                                   # From metadata.statement
    scope: str                                       # From metadata.scope
    enforcement_level: str                           # "must" | "should" | "may"
    enforced_by_decisions: list[NormalizedEntity]     # Decisions that enforce this invariant
    source_adrs: list[NormalizedEntity]               # All ADRs mentioning this invariant
    is_enforced: bool                                 # True if at least one decision enforces it

def get_invariant(invariant_id: str) -> Optional[InvariantView]:
    """
    Retrieve an invariant with its enforcement chain.

    Args:
        invariant_id: Invariant identifier (e.g., "INV-0001")

    Returns:
        InvariantView if found, None otherwise.
    """
```

---

## 4. Graph Queries

### trace_relationships

Follow relationships from an entity, optionally filtering by type and direction.

```python
@dataclass
class RelationshipTrace:
    """Result of a relationship traversal."""
    origin: NormalizedEntity
    edges: list[RelationshipRecord]
    targets: list[NormalizedEntity]

def trace_relationships(
    entity_id: str,
    relationship_type: Optional[str] = None,
    direction: str = "outbound",         # "outbound" | "inbound" | "both"
    max_depth: int = 1,
) -> Optional[RelationshipTrace]:
    """
    Trace relationships from an entity.

    Args:
        entity_id: Starting entity
        relationship_type: Filter to specific type (None = all types)
        direction: "outbound" (entity→targets), "inbound" (sources→entity), "both"
        max_depth: How many hops to follow (1 = direct neighbors only)

    Returns:
        RelationshipTrace with edges and resolved target entities.
        None if entity_id doesn't exist.

    Examples:
        # Direct capabilities of a decision
        trace = model.trace_relationships("DEC-0015", "enables", "outbound")
        # trace.targets == [CAP-0012, ...]

        # Everything that references ADR-L-0001
        trace = model.trace_relationships("ADR-L-0001", "references", "inbound")
        # trace.targets == [ADR-L-0002, ADR-L-0005, ...]

        # Multi-hop: decision → capability → component (depth 2)
        trace = model.trace_relationships("DEC-0015", direction="outbound", max_depth=2)
    """
```

**Implementation for depth > 1:**
BFS from origin. At each level, follow relationships matching type/direction filter.
Collect unique entities and edges. Stop at `max_depth` or when no new entities discovered.
Cycle-safe: visited set prevents revisiting entities.

---

### trace_decision

Trace the full impact scope of a decision: what it enforces, enables, governs,
and transitively affects.

```python
@dataclass
class DecisionTrace:
    """Complete impact trace of a decision."""
    decision: NormalizedEntity
    enforced_invariants: list[NormalizedEntity]
    enabled_capabilities: list[NormalizedEntity]
    governed_components: list[NormalizedEntity]
    implementing_components: list[NormalizedEntity]  # Components realizing enabled capabilities
    affected_systems: list[NormalizedEntity]          # Systems containing governed/implementing components
    supersession_chain: list[NormalizedEntity]        # This decision's supersession history
    all_affected_entities: list[NormalizedEntity]      # Union of all above

def trace_decision(decision_id: str) -> Optional[DecisionTrace]:
    """
    Trace the complete architectural impact of a decision.

    This performs a multi-hop traversal:
      decision --[enforces]--> invariants
      decision --[enables]--> capabilities --[implemented_by]--> components
      decision --[governs]--> components
      components --[embodied_in]--> systems
      decision --[superseded_by/supersedes]--> other decisions

    Args:
        decision_id: Decision identifier (e.g., "DEC-0015")

    Returns:
        DecisionTrace with all affected entities, None if not found.

    Example:
        trace = model.trace_decision("DEC-0001")
        # trace.enforced_invariants == [INV-0001]
        # trace.enabled_capabilities == []
        # trace.governed_components == []
    """
```

**Implementation:**
1. Get decision entity
2. `outbound_typed(decision_id, "enforces")` → invariants
3. `outbound_typed(decision_id, "enables")` → capabilities
4. For each capability: `outbound_typed(cap_id, "implemented_by")` → components
5. `outbound_typed(decision_id, "governs")` → directly governed components
6. Union components from steps 4 + 5
7. For each component: `outbound_typed(comp_id, "embodied_in")` → systems
8. Walk `supersedes` / `superseded_by` chain

---

### trace_capability

Trace a capability's full realization path: from logical intent to physical implementation.

```python
@dataclass
class CapabilityTrace:
    """Full realization trace of a capability."""
    capability: NormalizedEntity
    source_adr: NormalizedEntity                     # Logical ADR defining this capability
    enabling_decisions: list[NormalizedEntity]        # Decisions that enable it
    implementing_components: list[NormalizedEntity]   # Components that realize it
    hosting_systems: list[NormalizedEntity]           # Systems containing those components
    governing_invariants: list[NormalizedEntity]      # Invariants enforced by enabling decisions
    unresolved_gaps: list[UnresolvedRecord]           # Gaps related to this capability
    realization_complete: bool                        # True if fully realized with no gaps

def trace_capability(capability_id: str) -> Optional[CapabilityTrace]:
    """
    Trace a capability from logical intent to physical realization.

    Traversal:
      capability <--[enables]-- decisions --[enforces]--> invariants
      capability --[implemented_by]--> components --[embodied_in]--> systems
      check unresolved for gaps referencing this capability

    Args:
        capability_id: Capability identifier (e.g., "CAP-0018")

    Returns:
        CapabilityTrace, None if not found.
    """
```

---

### impact_of

Determine the blast radius of a change to an entity: what other entities
would be affected if this entity changes?

```python
@dataclass
class ImpactAnalysis:
    """Blast radius of a potential change to an entity."""
    entity: NormalizedEntity
    directly_affected: list[NormalizedEntity]    # 1-hop dependents
    transitively_affected: list[NormalizedEntity] # 2+ hop dependents
    affected_adrs: list[NormalizedEntity]         # ADRs that would need review
    affected_invariants: list[NormalizedEntity]    # Invariants that might be violated

def impact_of(
    entity_id: str,
    max_depth: int = 3,
) -> Optional[ImpactAnalysis]:
    """
    Analyze the impact of changing an entity.

    Follows all INBOUND relationships (things that depend on this entity)
    transitively up to max_depth.

    Args:
        entity_id: Entity to analyze
        max_depth: Maximum traversal depth

    Returns:
        ImpactAnalysis, None if entity not found.

    Example:
        impact = model.impact_of("INV-0001")
        # impact.directly_affected == [DEC-0001, ...]
        # impact.affected_adrs == [ADR-L-0001, ...]
    """
```

**Implementation:**
1. BFS over inbound relationships from entity, up to max_depth
2. Collect all unique entities reached
3. Filter to ADRs (by following `declared_in` from affected entities)
4. Filter to invariants (affected entities with entity_type=invariant)

---

### dependencies_of

What does this entity depend on? (Outbound traversal.)

```python
@dataclass
class DependencyAnalysis:
    """What an entity depends on."""
    entity: NormalizedEntity
    direct_dependencies: list[NormalizedEntity]
    transitive_dependencies: list[NormalizedEntity]
    required_invariants: list[NormalizedEntity]       # Invariants this entity must uphold
    source_adrs: list[NormalizedEntity]               # ADRs this entity traces to

def dependencies_of(
    entity_id: str,
    max_depth: int = 3,
) -> Optional[DependencyAnalysis]:
    """
    Trace what an entity depends on.

    Follows all OUTBOUND relationships transitively.

    Args:
        entity_id: Entity to analyze
        max_depth: Maximum traversal depth

    Returns:
        DependencyAnalysis, None if entity not found.
    """
```

---

### path_between

Find the shortest relationship path between two entities.

```python
@dataclass
class GraphPath:
    """A path through the architecture graph."""
    steps: list[tuple[NormalizedEntity, RelationshipRecord, NormalizedEntity]]
    length: int

def path_between(
    from_id: str,
    to_id: str,
    max_depth: int = 10,
    relationship_types: Optional[set[str]] = None,
) -> Optional[GraphPath]:
    """
    Find the shortest path between two entities.

    Args:
        from_id: Starting entity
        to_id: Target entity
        max_depth: Maximum path length
        relationship_types: Restrict to these relationship types (None = all)

    Returns:
        GraphPath if reachable within max_depth, None otherwise.

    Example:
        path = model.path_between("CAP-0001", "COMP-0010")
        # path.steps == [(CAP-0001, implemented_by, COMP-0010)]
        # path.length == 1
    """
```

**Implementation:** Bidirectional BFS. Treat relationship graph as undirected
for pathfinding (both outbound and inbound edges are traversable).

---

## 5. Collection Queries

### list_entities

```python
def list_entities(
    entity_type: Optional[str] = None,
    domain: Optional[str] = None,
    status: Optional[str] = None,
) -> list[NormalizedEntity]:
    """
    List entities with optional filters.

    All filters are AND-combined.

    Args:
        entity_type: Filter by type ("capability", "component", etc.)
        domain: Filter by domain membership
        status: Filter by status ("accepted", "proposed", etc.)

    Returns:
        List of matching entities, sorted by (entity_type, id).
    """
```

### list_relationships

```python
def list_relationships(
    relationship_type: Optional[str] = None,
    from_type: Optional[str] = None,
    to_type: Optional[str] = None,
    min_confidence: float = 0.0,
) -> list[RelationshipRecord]:
    """
    List relationships with optional filters.

    Args:
        relationship_type: Filter by type ("enforces", "enables", etc.)
        from_type: Filter by source entity type
        to_type: Filter by target entity type
        min_confidence: Minimum confidence threshold

    Returns:
        List of matching relationships, sorted by relationship_id.
    """
```

---

## 6. Gap Queries

### get_unresolved

```python
def get_unresolved(gap_id: str) -> Optional[UnresolvedRecord]:
    """Retrieve a specific unresolved record by ID."""
```

### unresolved_for

```python
def unresolved_for(entity_id: str) -> list[UnresolvedRecord]:
    """
    Get all unresolved records sourced from this entity.

    Example:
        gaps = model.unresolved_for("ADR-L-0004")
        # [UGAP-ADR-L-0004-GAP-0001, UGAP-ADR-L-0004-GAP-0002, ...]
    """
```

### critical_gaps

```python
def critical_gaps() -> list[UnresolvedRecord]:
    """Return all unresolved records with severity 'critical' or 'important'."""
```

### coverage_gaps

```python
@dataclass
class CoverageGap:
    """A capability without full implementation coverage."""
    capability: NormalizedEntity
    missing_components: bool         # No implementing component at all
    partial_realization: bool        # Some components but unresolved gaps remain
    related_gaps: list[UnresolvedRecord]

def coverage_gaps() -> list[CoverageGap]:
    """
    Find capabilities that lack full component realization.

    Checks:
    1. Capabilities with no `implemented_by` relationships
    2. Capabilities with unresolved `implemented_by` gaps

    Returns:
        List of CoverageGap records.
    """
```

---

## 7. Aggregate Queries

### architecture_summary

```python
@dataclass
class ArchitectureSummary:
    """High-level architecture statistics."""
    namespace: str
    generated_at: datetime
    entity_counts: dict[str, int]        # {"adr": 29, "capability": 20, ...}
    relationship_counts: dict[str, int]  # {"declared_in": 60, "enforces": 12, ...}
    unresolved_count: int
    critical_gap_count: int
    capability_realization_rate: float   # fraction of capabilities with ≥1 component
    invariant_enforcement_rate: float    # fraction of invariants with ≥1 enforcing decision
    domains: list[str]                   # All domains across all entities

def architecture_summary() -> ArchitectureSummary:
    """Compute high-level architecture health metrics."""
```

### invariant_coverage

```python
@dataclass
class InvariantCoverage:
    """Invariant enforcement analysis."""
    invariant: NormalizedEntity
    enforcement_level: str           # "must" | "should" | "may"
    enforcing_decisions: list[NormalizedEntity]
    is_enforced: bool
    is_must_and_unenforced: bool     # True if enforcement_level=must and not enforced

def invariant_coverage() -> list[InvariantCoverage]:
    """
    Analyze enforcement coverage across all invariants.

    Returns every invariant with its enforcement status.
    Flags MUST-level invariants that have no enforcing decision.
    """
```

### capability_realization

```python
@dataclass
class CapabilityRealization:
    """Capability implementation status."""
    capability: NormalizedEntity
    status: str                      # "realized" | "unrealized" | "partial"
    components: list[NormalizedEntity]
    gaps: list[UnresolvedRecord]

def capability_realization() -> list[CapabilityRealization]:
    """
    Analyze realization status of every capability.

    Returns each capability with its implementing components and any gaps.
    """
```

### decision_impact_map

```python
def decision_impact_map() -> dict[str, DecisionTrace]:
    """
    Build a complete map of every decision's architectural impact.

    Returns a dict mapping decision_id → DecisionTrace for every decision.
    Useful for governance dashboards and change-impact analysis.
    """
```

---

## 8. Introspection Queries

```python
def model_metadata() -> ModelMetadata:
    """Return metadata about the loaded architecture model."""

def entity_count() -> int:
    """Total number of entities in the model."""

def relationship_count() -> int:
    """Total number of relationships in the model."""

def fingerprint() -> str:
    """SHA-256 fingerprint of the loaded registry bundle."""

def relationship_types() -> set[str]:
    """All relationship types present in the model."""

def entity_types() -> set[str]:
    """All entity types present in the model."""

def domains() -> set[str]:
    """All domains mentioned across all entities."""
```

---

## 9. Query Implementation Strategy

### Index-First Design

Every query is backed by a pre-built hash index. No query scans the full
entity or relationship list.

| Query Pattern | Index Used |
|---|---|
| By entity ID | `EntityIndex._by_id` |
| By entity type | `EntityIndex._adrs`, `._components`, etc. |
| By domain | `EntityIndex._by_domain` |
| By status | `EntityIndex._by_status` |
| Outbound relationships | `RelIndex._outbound` |
| Inbound relationships | `RelIndex._inbound` |
| Typed traversal | `RelIndex._outbound_typed`, `._inbound_typed` |
| Gap by source | `GapIndex._by_source` |

### View Objects

Entity queries (`get_system`, `get_component`, etc.) return View objects
that bundle the entity with resolved context. Views are computed on-demand,
not cached, because:
1. The model is read-only (no invalidation needed)
2. Construction is O(degree) per entity (fast for typical architectures)
3. Caching views would double memory usage with little benefit

For the aggregate queries (`architecture_summary`, `decision_impact_map`),
results can be cached on first call since the model is immutable.

### Mapping to Current ArchitectureRepository

The existing `ArchitectureRepository` class provides primitive versions of
some of these queries:

| Current Method | Kernel Query | Gap |
|---|---|---|
| `get_entities()` | `list_entities()` | No type/domain/status filtering |
| `get_components()` | `list_entities(entity_type="component")` | Equivalent |
| `get_capabilities()` | `list_entities(entity_type="capability")` | Equivalent |
| `get_decisions()` | `list_entities(entity_type="decision")` | Equivalent |
| `get_invariants()` | `list_entities(entity_type="invariant")` | Equivalent |
| `get_systems()` | `list_entities(entity_type="system")` | Equivalent |
| `get_relationships()` | `list_relationships()` | No filtering |
| `find_entity(id)` | `get_entity(id)` | Equivalent |
| — | `get_system(id)` | **New:** resolved topology context |
| — | `get_component(id)` | **New:** resolved architectural context |
| — | `trace_relationships()` | **New:** graph traversal |
| — | `trace_decision()` | **New:** decision impact analysis |
| — | `trace_capability()` | **New:** realization tracing |
| — | `impact_of()` | **New:** change blast radius |
| — | `path_between()` | **New:** shortest path |
| — | `architecture_summary()` | **New:** aggregate statistics |
| — | `invariant_coverage()` | **New:** enforcement analysis |
| — | `coverage_gaps()` | **New:** capability gap analysis |

The kernel query surface extends the current repository API with graph
traversals, contextual views, and aggregate analysis — the operations
that make the compiled architecture model useful for reasoning.

---

## 10. Risks and Constraints

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| View objects become stale if model reloads | Callers hold references to old data | Views are ephemeral (not cached); model reload creates new model instance |
| Graph traversals on cyclic relationships never terminate | Infinite loop | Visited-set in all BFS/DFS traversals; max_depth hard limit |
| Aggregate queries expensive on large models | Slow first call | Cache on first computation; model is immutable so cache is always valid |
| `metadata` dict access is error-prone | KeyError at runtime | View objects extract known metadata fields with `.get()` defaults; type-specific metadata documented per entity type |
| Query surface grows unbounded | API maintenance burden | Limit to operations that the kernel actually needs; resist adding convenience queries that can be composed from primitives |

### Constraints

1. **No mutation** — all queries are pure reads
2. **No external I/O** — queries operate on in-memory indexes only
3. **Deterministic ordering** — list results sorted by ID
4. **Bounded traversals** — all graph walks have max_depth (default 10)
5. **View objects are transient** — not stored, not serialized, recomputed per call
6. **Thread-safe reads** — the immutable model supports concurrent query access
