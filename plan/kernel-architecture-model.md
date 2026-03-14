# Kernel Architecture Model

## Purpose

This document defines the in-memory architecture model that the STE Kernel
builds from compiled registry artifacts. It specifies the data structures,
indexing strategy, and loading protocol that the kernel uses to answer
architecture queries without parsing ADR source files.

---

## 1. Model Identity

The kernel architecture model is a **read-only, indexed, in-memory graph**
derived from the 4 contract registries. It provides O(1) entity lookup,
O(1) relationship traversal, and typed entity access.

The model is loaded once, cached, and invalidated only when the registry
fingerprint changes.

```
                    ┌──────────────────────────┐
                    │   Compiled Registries     │
                    │   (YAML files on disk)    │
                    └─────────┬────────────────┘
                              │ load
                              ▼
                    ┌──────────────────────────┐
                    │  KernelArchitectureModel  │
                    │                           │
                    │  entities: EntityIndex     │
                    │  relationships: RelIndex   │
                    │  unresolved: GapIndex      │
                    │  metadata: ModelMetadata   │
                    └──────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────┐
                    │     Query Surface         │
                    │                           │
                    │  get_entity()              │
                    │  get_system()              │
                    │  get_component()           │
                    │  trace_decision()          │
                    │  trace_relationships()     │
                    │  ...                       │
                    └──────────────────────────┘
```

---

## 2. Entity Index

### Structure

```python
class EntityIndex:
    """Indexed entity collection for O(1) lookup."""

    # Primary index
    _by_id: dict[str, NormalizedEntity]

    # Type indexes
    _adrs: dict[str, NormalizedEntity]          # entity_type == "adr"
    _systems: dict[str, NormalizedEntity]        # entity_type == "system"
    _components: dict[str, NormalizedEntity]     # entity_type == "component"
    _capabilities: dict[str, NormalizedEntity]   # entity_type == "capability"
    _decisions: dict[str, NormalizedEntity]      # entity_type == "decision"
    _invariants: dict[str, NormalizedEntity]     # entity_type == "invariant"

    # Secondary indexes
    _by_domain: dict[str, list[str]]            # domain -> [entity_ids]
    _by_status: dict[str, list[str]]            # status -> [entity_ids]
    _by_source_adr: dict[str, list[str]]        # adr_id -> [entity_ids declared in it]
```

### Construction (from entity-registry.yaml)

```python
def build_entity_index(registry: NormalizedEntityRegistry) -> EntityIndex:
    index = EntityIndex()
    type_map = {
        "adr": index._adrs,
        "system": index._systems,
        "component": index._components,
        "capability": index._capabilities,
        "decision": index._decisions,
        "invariant": index._invariants,
    }
    for entity in registry.entities:
        index._by_id[entity.id] = entity

        type_dict = type_map.get(entity.entity_type)
        if type_dict is not None:
            type_dict[entity.id] = entity

        # Domain index (from metadata.domains or entity parent ADR domains)
        for domain in entity.metadata.get("domains", []):
            index._by_domain.setdefault(domain, []).append(entity.id)

        # Status index (from metadata.status)
        status = entity.metadata.get("status")
        if status:
            index._by_status.setdefault(status, []).append(entity.id)

        # Source ADR index (from canonical_source.source_ref)
        adr_id = entity.canonical_source.source_ref.split("#")[0]
        if adr_id != entity.id:  # non-ADR entity declared in an ADR
            index._by_source_adr.setdefault(adr_id, []).append(entity.id)

    return index
```

### Access Patterns

| Method | Return | Complexity |
|---|---|---|
| `get(entity_id)` | `NormalizedEntity` or None | O(1) |
| `contains(entity_id)` | bool | O(1) |
| `all_adrs()` | list of ADR entities | O(1) return cached |
| `all_systems()` | list of system entities | O(1) |
| `all_components()` | list of component entities | O(1) |
| `all_capabilities()` | list of capability entities | O(1) |
| `all_decisions()` | list of decision entities | O(1) |
| `all_invariants()` | list of invariant entities | O(1) |
| `by_domain(domain)` | list of entity IDs | O(1) |
| `by_status(status)` | list of entity IDs | O(1) |
| `declared_in(adr_id)` | list of entity IDs | O(1) |
| `count()` | int | O(1) |
| `entity_types()` | set of type strings | O(1) |

---

## 3. Relationship Index

### Structure

```python
class RelIndex:
    """Indexed relationship collection for graph traversal."""

    # Primary index
    _by_id: dict[str, RelationshipRecord]

    # Adjacency indexes
    _outbound: dict[str, list[RelationshipRecord]]  # from_entity_id -> [records]
    _inbound: dict[str, list[RelationshipRecord]]    # to_entity_id -> [records]

    # Type index
    _by_type: dict[str, list[RelationshipRecord]]    # relationship_type -> [records]

    # Combined index for typed traversal
    _outbound_typed: dict[tuple[str, str], list[RelationshipRecord]]
        # (from_entity_id, relationship_type) -> [records]
    _inbound_typed: dict[tuple[str, str], list[RelationshipRecord]]
        # (to_entity_id, relationship_type) -> [records]
```

### Construction (from relationship-registry.yaml)

```python
def build_rel_index(registry: RelationshipRegistry) -> RelIndex:
    index = RelIndex()
    for rel in registry.relationships:
        index._by_id[rel.relationship_id] = rel
        index._outbound.setdefault(rel.from_entity_id, []).append(rel)
        index._inbound.setdefault(rel.to_entity_id, []).append(rel)
        index._by_type.setdefault(rel.relationship_type, []).append(rel)
        index._outbound_typed.setdefault(
            (rel.from_entity_id, rel.relationship_type), []
        ).append(rel)
        index._inbound_typed.setdefault(
            (rel.to_entity_id, rel.relationship_type), []
        ).append(rel)
    return index
```

### Access Patterns

| Method | Return | Complexity |
|---|---|---|
| `get(relationship_id)` | `RelationshipRecord` or None | O(1) |
| `outbound(entity_id)` | list of RelationshipRecords | O(1) |
| `inbound(entity_id)` | list of RelationshipRecords | O(1) |
| `outbound_typed(entity_id, rel_type)` | list of RelationshipRecords | O(1) |
| `inbound_typed(entity_id, rel_type)` | list of RelationshipRecords | O(1) |
| `by_type(rel_type)` | list of RelationshipRecords | O(1) |
| `neighbors(entity_id)` | set of connected entity IDs | O(degree) |
| `typed_neighbors(entity_id, rel_type)` | set of target entity IDs | O(out-degree for type) |
| `count()` | int | O(1) |

---

## 4. Gap Index

### Structure

```python
class GapIndex:
    """Indexed unresolved record collection."""

    _by_id: dict[str, UnresolvedRecord]
    _by_source: dict[str, list[UnresolvedRecord]]    # source_entity_id -> [records]
    _by_severity: dict[str, list[UnresolvedRecord]]   # severity -> [records]
    _by_class: dict[str, list[UnresolvedRecord]]      # gap_class -> [records]
```

### Access Patterns

| Method | Return | Complexity |
|---|---|---|
| `get(gap_id)` | `UnresolvedRecord` or None | O(1) |
| `for_entity(entity_id)` | list of gaps sourced from this entity | O(1) |
| `by_severity(severity)` | list of gaps | O(1) |
| `critical()` | list of critical gaps | O(1) |
| `author_declared()` | list of author-declared gaps | O(1) |
| `generator_derived()` | list of compiler-detected gaps | O(1) |
| `count()` | int | O(1) |

---

## 5. Model Metadata

```python
@dataclass(frozen=True)
class ModelMetadata:
    """Metadata about the loaded architecture model."""
    namespace: str                    # From architecture_index.architecture_namespace
    schema_version: str               # Contract schema version
    generated_at: datetime            # When registries were compiled
    generator: str                    # Compiler identifier
    fingerprint: str                  # SHA-256 of registry bundle
    source_coverage: SourceCoverageSummary
    validation_summary: ValidationSummary

    @property
    def clean(self) -> bool:
        """True if compilation had no hard failures."""
        return self.validation_summary.hard_failures == 0

    @property
    def total_sources(self) -> int:
        sc = self.source_coverage
        return (sc.logical_adrs + sc.physical_adrs + sc.physical_system_adrs
                + sc.physical_component_adrs + sc.standalone_invariants)
```

---

## 6. Top-Level Model

```python
class KernelArchitectureModel:
    """Read-only architecture model for kernel consumption."""

    entities: EntityIndex
    relationships: RelIndex
    unresolved: GapIndex
    metadata: ModelMetadata

    @classmethod
    def load(cls, scope_root: Path) -> "KernelArchitectureModel":
        """Load from compiled registry artifacts on disk."""
        index_path = scope_root / "adrs" / "index" / "architecture-index.yaml"
        ...

    @classmethod
    def load_from_repository(cls, repo: ArchitectureRepository) -> "KernelArchitectureModel":
        """Load from an already-populated ArchitectureRepository."""
        ...
```

### Loading Protocol

```python
@classmethod
def load(cls, scope_root: Path) -> "KernelArchitectureModel":
    # 1. Load architecture index
    index_path = scope_root / "adrs" / "index" / "architecture-index.yaml"
    if not index_path.exists():
        raise ArchitectureNotCompiledError(scope_root)

    index = yaml_load(index_path)
    version = index["schema_version"]
    if not is_supported_version(version):
        raise IncompatibleContractError(version)

    # 2. Load contract registries
    entity_reg = yaml_load(scope_root / index["entity_registry_path"])
    rel_reg = yaml_load(scope_root / index["relationship_registry_path"])
    unresolved_reg = yaml_load(scope_root / index["unresolved_registry_path"])

    # 3. Validate to Pydantic models
    entity_registry = NormalizedEntityRegistry(**entity_reg)
    rel_registry = RelationshipRegistry(**rel_reg)
    unresolved_registry = UnresolvedRegistry(**unresolved_reg)

    # 4. Build indexes
    entities = build_entity_index(entity_registry)
    relationships = build_rel_index(rel_registry)
    gaps = build_gap_index(unresolved_registry)

    # 5. Compute fingerprint
    fingerprint = compute_fingerprint(index, entity_reg, rel_reg, unresolved_reg)

    # 6. Assemble model
    metadata = ModelMetadata(
        namespace=index["architecture_namespace"],
        schema_version=version,
        generated_at=index["generated_at"],
        generator=index["generator"],
        fingerprint=fingerprint,
        source_coverage=SourceCoverageSummary(**index["source_coverage"]),
        validation_summary=ValidationSummary(**index["validation_summary"]),
    )

    return cls(
        entities=entities,
        relationships=relationships,
        unresolved=gaps,
        metadata=metadata,
    )
```

### Memory Layout

For the current repository (31 source artifacts):

| Component | Items | Estimated Memory |
|---|---|---|
| EntityIndex | ~150 entities | ~200 KB |
| RelIndex | ~90 relationships | ~120 KB |
| GapIndex | ~9 unresolved | ~10 KB |
| Index overhead | hash maps | ~50 KB |
| **Total** | | **~400 KB** |

For projected scale (1000 ADRs, ~5000 entities, ~3000 relationships):

| Component | Items | Estimated Memory |
|---|---|---|
| EntityIndex | ~5000 entities | ~7 MB |
| RelIndex | ~3000 relationships | ~4 MB |
| GapIndex | ~100 unresolved | ~100 KB |
| Index overhead | hash maps | ~2 MB |
| **Total** | | **~13 MB** |

Well within acceptable bounds for an in-memory model.

---

## 7. Entity Type Semantics

The kernel interprets entity types with the following semantics:

### ADR (`entity_type: "adr"`)

An architecture decision record — the primary authored artifact.
ADRs are containers: they introduce capabilities, decisions, invariants, etc.

**Key metadata fields:**
- `status`: "proposed" | "accepted" | "deprecated" | "superseded"
- `domains`: list of business/technical domains
- `tags`: list of classification tags

**Key relationships:**
- Other entities → `declared_in` → this ADR
- This ADR → `references` → other ADRs

### System (`entity_type: "system"`)

A top-level system design defined by a physical-system ADR.

**Key metadata fields:**
- `adr_id`: parent ADR-PS-XXXX
- `implements_logical`: list of logical ADR IDs this system implements
- `technologies`: list of technology names

**Key relationships:**
- Components → `embodied_in` → this system
- This system → `declared_in` → parent ADR

### Component (`entity_type: "component"`)

A concrete implementation unit defined by a physical-component ADR.

**Key metadata fields:**
- `adr_id`: parent ADR-PC-XXXX
- `module_path`: code location
- `technologies`: list of technology names
- `implements_capabilities`: list of CAP-XXXX IDs
- `implements_system`: list of ADR-PS-XXXX IDs

**Key relationships:**
- Capabilities → `implemented_by` → this component
- This component → `embodied_in` → system
- This component → `declared_in` → parent ADR
- Decisions → `governs` → this component

### Capability (`entity_type: "capability"`)

A system capability defined at the logical level.

**Key metadata fields:**
- `adr_id`: parent ADR-L-XXXX
- `domains`: inherited from parent ADR
- `implemented_by_components`: list of COMP-XXXX IDs
- `enabled_by_decisions`: list of DEC-XXXX IDs

**Key relationships:**
- This capability → `implemented_by` → components
- Decisions → `enables` → this capability
- This capability → `enabled_by` → decisions
- This capability → `declared_in` → parent ADR

### Decision (`entity_type: "decision"`)

An architectural decision made within a logical ADR.

**Key metadata fields:**
- `adr_id`: parent ADR-L-XXXX
- `related_invariants`: list of INV-XXXX IDs
- `enforces_invariants`: list of INV-XXXX IDs
- `enables_capabilities`: list of CAP-XXXX IDs
- `governs_components`: list of COMP-XXXX IDs
- `supersedes`: list of DEC-XXXX IDs
- `refines`: list of DEC-XXXX IDs

**Key relationships:**
- This decision → `enforces` → invariants
- This decision → `enables` → capabilities
- This decision → `governs` → components
- This decision → `supersedes` → other decisions
- This decision → `refines` → other decisions
- This decision → `declared_in` → parent ADR

### Invariant (`entity_type: "invariant"`)

A property that must always hold, defined standalone or within an ADR.

**Key metadata fields:**
- `defined_in` or `adr_id`: origin ADR
- `scope`: "global" | domain name | component name
- `statement`: the invariant statement
- `enforcement_level`: "must" | "should" | "may"
- `declaration_mode`: "canonical" | "local" | "reference"
- `upheld_by_decisions`: list of DEC-XXXX IDs

**Key relationships:**
- Decisions → `enforces` → this invariant
- This invariant → `declared_in` → source ADR or standalone file

---

## 8. Graph Traversal Patterns

The kernel model supports the following traversal patterns through
the relationship index:

### Upward: Entity → Source ADR

```
component COMP-0010
  --[declared_in]--> ADR-PC-0001
    --[declared_in is entity_type=adr]--> (stop: reached ADR)
```

### Downward: ADR → Declared Entities

```
ADR-L-0001
  <--[declared_in]-- CAP-0001, CAP-0002, ..., DEC-0001, DEC-0002, ..., INV-0003, ...
```

### Lateral: Capability → Component

```
CAP-0018
  --[implemented_by]--> COMP-0010
    --[embodied_in]--> SYS-0001
```

### Governance: Decision → What it governs

```
DEC-0015
  --[enforces]--> INV-0009
  --[enables]--> CAP-0012
  --[governs]--> COMP-0010
```

### Impact: What depends on this entity?

```
entity X
  <--[all inbound relationships]-- dependents
  --[all outbound relationships]--> dependencies
```

### Evolution: Supersession chain

```
DEC-0001
  --[superseded_by]--> DEC-0015
    --[superseded_by]--> DEC-0022
      (no superseded_by: current decision)
```

---

## 9. Risks and Constraints

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Entity `metadata` is untyped | Kernel code must handle missing keys defensively | Document per-type metadata contracts; use `.get()` with defaults |
| Large relationship index for complex architectures | Memory and load time | Lazy loading option: load entity index first, relationship index on first graph query |
| Stale registries served to kernel | Kernel reasons over outdated architecture | Fingerprint check on load; CI gate that recompiles and checks for drift |
| Multiple scopes loaded simultaneously | Cross-scope entity ID collisions | Namespace-prefix entity IDs in multi-scope model, or load scopes into isolated models |

### Constraints

1. **Read-only** — the kernel model is immutable after construction
2. **Single-scope** — one model instance per scope (multi-scope is multiple instances)
3. **Full load** — all 4 contract registries loaded at once (no lazy file loading)
4. **In-memory** — no database, no disk cache for the model itself
5. **Pydantic models** — entity and relationship records are Pydantic objects (shared with compiler via `adr_kit.models`)
