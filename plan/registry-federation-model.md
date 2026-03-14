# Registry Federation Model

## Purpose

This document defines how multiple compiled architecture registries from
independent repositories are merged into the Super Graph — a single,
globally-addressable architecture knowledge model.

---

## 1. Federation Architecture

```
                  ┌─────────────────────────────────┐
                  │      Federation Manifest          │
                  │  (lists all participating repos)  │
                  └──────────────┬──────────────────┘
                                 │
            ┌────────────────────┼─────────────────────┐
            │                    │                      │
  ┌─────────▼──────┐  ┌─────────▼──────┐   ┌──────────▼─────┐
  │  repo-alpha     │  │  repo-beta      │   │  repo-gamma    │
  │  Compiled       │  │  Compiled       │   │  Compiled      │
  │  Registries     │  │  Registries     │   │  Registries    │
  └─────────┬──────┘  └─────────┬──────┘   └──────────┬─────┘
            │                    │                      │
            └────────────────────┼──────────────────────┘
                                 │
                    ┌────────────▼────────────────┐
                    │    Federation Engine          │
                    │                               │
                    │  1. Load all registries        │
                    │  2. Qualify all entity IDs     │
                    │  3. Merge entity graphs        │
                    │  4. Merge relationship graphs  │
                    │  5. Resolve cross-repo refs    │
                    │  6. Detect conflicts           │
                    │  7. Validate global integrity  │
                    │  8. Build Super Graph          │
                    │                               │
                    └────────────┬────────────────┘
                                 │
                    ┌────────────▼────────────────┐
                    │       SUPER GRAPH             │
                    │                               │
                    │  Globally-qualified entities   │
                    │  Local + cross-repo rels       │
                    │  Resolved cross-repo refs      │
                    │  Remaining unresolved          │
                    │  Federation metadata           │
                    │                               │
                    └──────────────────────────────┘
```

---

## 2. Federation Manifest

The federation manifest declares which repositories participate in the
Super Graph and where their compiled registries live.

### Format

```yaml
schema_version: "1.0"
type: federation_manifest
federation_id: ste-ecosystem
generated_at: "2026-03-13T12:00:00Z"

repositories:
  - namespace: adr-architecture-kit
    registry_root: ./repos/adr-architecture-kit
    index_path: adrs/index/architecture-index.yaml
    trust_level: authoritative           # owns its entities
    version: "1.2"                       # contract schema version

  - namespace: ste-kernel
    registry_root: ./repos/ste-kernel
    index_path: adrs/index/architecture-index.yaml
    trust_level: authoritative
    version: "1.2"

  - namespace: ste-runtime
    registry_root: ./repos/ste-runtime
    index_path: adrs/index/architecture-index.yaml
    trust_level: authoritative
    version: "1.2"

namespace_constraints:
  uniqueness: enforced                   # no two repos share a namespace
  format: "^[a-z][a-z0-9-]{1,63}$"     # namespace validation regex
```

### Fields

| Field | Description |
|---|---|
| `federation_id` | Unique ID for this federation |
| `repositories[].namespace` | The repository's `architecture_namespace` — must be unique |
| `repositories[].registry_root` | Path or URL to the repository root |
| `repositories[].index_path` | Relative path to `architecture-index.yaml` within the repo |
| `repositories[].trust_level` | `authoritative` (owns entities) or `mirror` (read-only copy) |
| `repositories[].version` | Contract schema version of the repo's registries |
| `namespace_constraints.uniqueness` | Enforcement policy for namespace uniqueness |

### Discovery

The manifest is stored at a well-known location:

```
{federation_root}/federation-manifest.yaml
```

Alternatively, in an STE config:

```json
// ste.config.json
{
  "federation": {
    "manifest": "path/to/federation-manifest.yaml"
  }
}
```

---

## 3. Federation Engine: Processing Stages

### Stage F1: Load and Validate

**Input:** Federation manifest

**Process:**
1. For each repository in manifest:
   a. Resolve `registry_root` + `index_path` to absolute path
   b. Load `architecture-index.yaml`
   c. Validate contract version compatibility
   d. Load entity-registry, relationship-registry, unresolved-registry
   e. Validate Pydantic models
2. Verify namespace uniqueness across all loaded repos
3. Verify no manifest references a missing repository

**Output:** `dict[str, RegistryBundle]` — namespace → loaded registries

**Error handling:**
- Missing repository → ERROR (halt federation)
- Unsupported schema version → ERROR (halt federation)
- Namespace collision → ERROR (halt federation)
- Registry parse error → ERROR (halt federation, identify repo)

### Stage F2: Qualify Entity IDs

**Input:** Loaded registries per namespace

**Process:**
For each registry, for each entity:
1. Attach `namespace` from the owning repository
2. Compute `qualified_id = f"{namespace}:{entity.id}"`
3. Index by `qualified_id`

For each relationship:
1. Qualify `from_entity_id` → `f"{from_namespace}:{from_entity_id}"`
2. Qualify `to_entity_id`:
   - If bare → same namespace as `from` (local relationship)
   - If already qualified → parse namespace from the ID
3. Compute qualified `relationship_id`

**Output:** All entities and relationships carry qualified IDs.

### Stage F3: Merge Entity Graphs

**Input:** Qualified entities from all repositories

**Process:**
1. Create empty Super Graph entity index
2. For each namespace, for each entity:
   a. Key = `qualified_id`
   b. Insert into global index
   c. If duplicate `qualified_id` → indicates namespace collision (caught in F1)
3. Build type indexes, domain indexes, namespace indexes

**Output:** Global `EntityIndex` with all entities from all repos

**Invariant:** No two entities share the same `qualified_id`. This is
guaranteed by per-repo entity uniqueness + namespace uniqueness.

### Stage F4: Merge Relationship Graphs

**Input:** Qualified relationships from all repositories

**Process:**
1. Create empty Super Graph relationship index
2. For each namespace, for each relationship:
   a. Compute global `relationship_id` using qualified from/to IDs
   b. Insert into global index
   c. Mark `cross_repository = true` if `from_namespace != to_namespace`
3. Build adjacency indexes (outbound, inbound, typed)

**Deduplication:** If the same cross-repo relationship is declared in
both repos (repo A says "I depend on B" and repo B says "A depends on me"),
keep one, merge evidence lists.

**Output:** Global `RelIndex` with all relationships

### Stage F5: Resolve Cross-Repository References

**Input:** Unresolved registries from all repos + global entity index

**Process:**
For each repo's unresolved records:
1. If `gap_class == "cross_repository"`:
   a. Look up `related_entity_id` (qualified) in global entity index
   b. If found: **resolve** — create a relationship in the global rel index,
      remove from unresolved
   c. If not found: **remains unresolved** — the target repo may not be
      in the federation, or the entity doesn't exist

2. If `gap_class == "generator_derived"` and `related_entity_id` is qualified:
   a. Same resolution logic as above

**Output:** Resolved cross-repo relationships added to global RelIndex.
Remaining unresolved records in global unresolved list.

### Stage F6: Detect Federation Conflicts

**Input:** Global entity index + global relationship index

**Process:**
Check for semantic conflicts that don't violate structural integrity
but indicate architectural problems:

1. **Contradictory supersession:** Entity A supersedes B in repo-alpha,
   but B supersedes A in repo-beta.

2. **Circular cross-repo dependencies:** Repo A depends on B, B depends on C,
   C depends on A.

3. **Orphan cross-repo targets:** A cross-repo relationship points to an
   entity that exists but is deprecated/superseded.

4. **Invariant scope conflicts:** The same invariant ID defined in two repos
   (different namespaces, but same semantics — e.g., both define a
   "schema validation required" invariant). Not an error, but flagged
   for human review.

**Output:** Federation diagnostics (warnings, not errors)

### Stage F7: Validate Global Integrity

**Input:** Complete Super Graph (entities, relationships, unresolved)

**Process:**
Apply the same referential integrity checks as the per-repo bundle
validation, but against the global graph:

1. Every relationship `from_qualified_id` exists in global entity index
2. Every relationship `to_qualified_id` exists in global entity index
3. Every unresolved `source_entity_id` (qualified) exists in global entity index
4. No duplicate qualified entity IDs
5. No duplicate qualified relationship IDs

**Output:** Pass/fail with diagnostics

### Stage F8: Build Super Graph Model

**Input:** Validated global entities, relationships, unresolved

**Output:**
```python
@dataclass
class SuperGraph:
    entities: GlobalEntityIndex
    relationships: GlobalRelIndex
    unresolved: GlobalGapIndex
    metadata: FederationMetadata
    diagnostics: list[FederationDiagnostic]
```

---

## 4. Super Graph Data Model

### GlobalEntityIndex

```python
class GlobalEntityIndex:
    """Entity index across all federated namespaces."""

    _by_qualified_id: dict[str, NormalizedEntity]
    _by_namespace: dict[str, dict[str, NormalizedEntity]]  # ns → {bare_id → entity}
    _by_type: dict[str, list[NormalizedEntity]]             # entity_type → [entities]
    _by_domain: dict[str, list[NormalizedEntity]]           # domain → [entities]

    def get(self, qualified_id: str) -> Optional[NormalizedEntity]:
        """Lookup by qualified ID: 'alpha:CAP-0001'."""

    def get_bare(self, bare_id: str, namespace: Optional[str] = None) -> Optional[NormalizedEntity]:
        """
        Lookup by bare ID.
        If namespace provided: resolve in that namespace.
        If namespace omitted: return entity only if bare ID is unambiguous
          (exists in exactly one namespace). Raise AmbiguousIdError if multiple.
        """

    def in_namespace(self, namespace: str) -> list[NormalizedEntity]:
        """All entities from a specific namespace."""

    def namespaces(self) -> set[str]:
        """All namespace names in the federation."""
```

### GlobalRelIndex

```python
class GlobalRelIndex:
    """Relationship index across all federated namespaces."""

    _by_id: dict[str, RelationshipRecord]
    _outbound: dict[str, list[RelationshipRecord]]  # qualified from → [rels]
    _inbound: dict[str, list[RelationshipRecord]]    # qualified to → [rels]
    _cross_repo: list[RelationshipRecord]            # cross_repository == true

    def cross_repo_relationships(self) -> list[RelationshipRecord]:
        """All relationships spanning namespace boundaries."""

    def relationships_between_namespaces(
        self, ns_a: str, ns_b: str
    ) -> list[RelationshipRecord]:
        """All relationships between two specific namespaces."""
```

### FederationMetadata

```python
@dataclass
class FederationMetadata:
    federation_id: str
    assembled_at: datetime
    namespaces: list[str]               # participating namespaces
    namespace_fingerprints: dict[str, str]  # ns → registry bundle fingerprint
    total_entities: int
    total_relationships: int
    cross_repo_relationships: int
    resolved_cross_refs: int
    remaining_unresolved: int
```

---

## 5. Federation Strategies

### 5.1 Full Merge (Primary Strategy)

All registries loaded and merged into a single in-memory Super Graph.

**When to use:** Small to medium federations (< 50 repos, < 50K entities)

**Advantages:**
- Simple implementation
- All queries work against unified index
- Cross-repo traversals are native

**Disadvantages:**
- Memory scales linearly with federation size
- Full reload on any repo change

### 5.2 Lazy Namespace Loading

Load the federation manifest and entity index headers. Load full registries
on demand when a namespace is first queried.

**When to use:** Large federations or when most queries are namespace-scoped

```python
class LazySuperGraph:
    def __init__(self, manifest: FederationManifest):
        self._manifest = manifest
        self._loaded: dict[str, RegistryBundle] = {}

    def _ensure_loaded(self, namespace: str) -> None:
        if namespace not in self._loaded:
            self._loaded[namespace] = load_registry_bundle(
                self._manifest.get_repo(namespace)
            )

    def get(self, qualified_id: str) -> Optional[NormalizedEntity]:
        qid = QualifiedEntityId.parse(qualified_id)
        self._ensure_loaded(qid.namespace)
        return self._loaded[qid.namespace].entities.get(qid.bare_id)
```

**Advantages:**
- Low initial memory footprint
- Fast startup
- Only loads what's needed

**Disadvantages:**
- Cross-repo relationship resolution requires loading both sides
- First query to a namespace has load latency

### 5.3 Index-Only Federation

Load only the architecture-index.yaml from each repo (entity counts,
namespace, validation summary). Full registries loaded on demand.

**When to use:** Federation health dashboards, monitoring

```python
@dataclass
class FederationOverview:
    namespaces: list[str]
    per_namespace: dict[str, ArchitectureIndex]  # just the index header
    total_sources: int
    total_unresolved: int
```

### 5.4 Incremental Federation

Track per-namespace fingerprints. On federation update, only reload
namespaces whose fingerprints changed since last assembly.

```python
class IncrementalSuperGraph:
    def update(self) -> FederationDelta:
        changed = []
        for ns, repo in self._manifest.repositories.items():
            current_fp = load_fingerprint(repo)
            if current_fp != self._fingerprints.get(ns):
                changed.append(ns)
                self._reload_namespace(ns)
                self._fingerprints[ns] = current_fp
        self._resolve_cross_refs()
        return FederationDelta(changed_namespaces=changed)
```

---

## 6. Cross-Repository Relationship Semantics

### 6.1 How Cross-Repo Relationships Are Declared

A cross-repo relationship originates from the **consuming** repository.
The consuming repo knows it depends on something in another repo:

```yaml
# In ste-kernel's ADR-L-0005:
decisions:
  - id: DEC-0042
    summary: Use adr-kit's compiled registries for architecture loading
    enables_capabilities:
      - CAP-0003                                # local: ste-kernel:CAP-0003
      - adr-architecture-kit:CAP-0001           # cross-repo reference
```

The compiler in ste-kernel sees `adr-architecture-kit:CAP-0001` and:
1. Recognizes the namespace prefix
2. Cannot resolve locally (different namespace)
3. Emits an unresolved record with `gap_class: cross_repository`
4. Emits a relationship with `cross_repository: true` and the target's qualified ID

### 6.2 Resolution Protocol

At federation time:

```
ste-kernel:DEC-0042 --[enables]--> adr-architecture-kit:CAP-0001

Step 1: Look up adr-architecture-kit:CAP-0001 in federation entity index
Step 2: Found → entity exists in adr-architecture-kit's registry
Step 3: Promote unresolved record to resolved relationship
Step 4: Add resolved relationship to Super Graph
```

If the target doesn't exist:

```
ste-kernel:DEC-0042 --[enables]--> nonexistent-repo:CAP-9999

Step 1: Look up nonexistent-repo:CAP-9999 in federation entity index
Step 2: Not found → namespace "nonexistent-repo" not in federation, OR
        entity doesn't exist in that namespace
Step 3: Record remains unresolved in Super Graph
Step 4: Federation diagnostic: WARNING "cross-repo reference to
        nonexistent-repo:CAP-9999 cannot be resolved"
```

### 6.3 Bidirectional Cross-Repo Relationships

When ste-kernel declares it depends on `adr-architecture-kit:CAP-0001`,
adr-architecture-kit's registry doesn't know about this dependency.
The relationship is asymmetric: declared in the consumer, unknown to the provider.

The federation engine can optionally create **derived inverse relationships**:

```yaml
# Derived during federation:
- relationship_id: enabled_by:adr-architecture-kit:CAP-0001:ste-kernel:DEC-0042
  relationship_type: enabled_by
  from_qualified_id: adr-architecture-kit:CAP-0001
  to_qualified_id: ste-kernel:DEC-0042
  provenance_classification: derived
  cross_repository: true
  federation_derived: true             # flag: this edge was created by federation
```

This makes impact analysis bidirectional: querying `impact_of("adr-architecture-kit:CAP-0001")`
finds ste-kernel's dependency even though adr-architecture-kit's own registry
doesn't mention it.

### 6.4 Cross-Repo Relationship Types

All 12 existing relationship types can be cross-repo. The most likely
cross-repo relationships:

| Type | Scenario |
|---|---|
| `enables` | Service repo's decision enables a capability defined in governance repo |
| `implemented_by` | Service component implements a capability from architecture repo |
| `enforces` | Service decision enforces an invariant from governance repo |
| `references` | Service ADR references a governance ADR |
| `embodied_in` | Component in one repo belongs to a system defined in another |
| `related_to` | General cross-repo association |

### 6.5 Trust and Authority

Each repository is **authoritative** over its own entities. In case of
conflicting metadata:

| Conflict | Resolution |
|---|---|
| Entity name differs in consumer's reference vs provider's definition | Provider's definition wins (authoritative) |
| Entity marked deprecated in provider, active in consumer's reference | Provider's status is truth |
| Relationship declared in consumer, contradicted by provider | Both edges kept; flagged as conflict |

---

## 7. Federation Query Extensions

The Super Graph extends the kernel query surface with federation-aware operations:

### Cross-Repo Queries

```python
def cross_repo_dependencies(namespace: str) -> list[RelationshipRecord]:
    """What does this namespace depend on from other namespaces?"""

def cross_repo_dependents(namespace: str) -> list[RelationshipRecord]:
    """What other namespaces depend on entities in this namespace?"""

def namespace_coupling(ns_a: str, ns_b: str) -> NamespaceCoupling:
    """Analyze the coupling between two namespaces."""

@dataclass
class NamespaceCoupling:
    relationships_a_to_b: list[RelationshipRecord]
    relationships_b_to_a: list[RelationshipRecord]
    shared_entity_types: set[str]
    coupling_strength: float     # 0.0 (independent) to 1.0 (tightly coupled)
```

### Global Analysis

```python
def global_invariant_coverage() -> dict[str, list[InvariantCoverage]]:
    """Invariant enforcement across all namespaces."""

def global_capability_realization() -> dict[str, list[CapabilityRealization]]:
    """Capability implementation across all namespaces."""

def federation_health() -> FederationHealth:
    """Overall federation health metrics."""

@dataclass
class FederationHealth:
    namespaces: int
    total_entities: int
    total_relationships: int
    cross_repo_relationships: int
    unresolved_cross_refs: int
    circular_dependencies: list[list[str]]     # [[ns_a, ns_b, ns_c], ...]
    orphan_namespaces: list[str]               # namespaces with no cross-repo edges
```

### Namespace-Scoped Queries

All existing kernel queries accept an optional `namespace` parameter to
scope results:

```python
def get_entity(entity_id: str, namespace: Optional[str] = None):
    """
    If namespace provided: look up in that namespace.
    If omitted and entity_id is qualified: parse namespace from ID.
    If omitted and entity_id is bare: return if unambiguous, error if ambiguous.
    """

def list_entities(
    entity_type: Optional[str] = None,
    namespace: Optional[str] = None,      # NEW: scope to namespace
    domain: Optional[str] = None,
    status: Optional[str] = None,
) -> list[NormalizedEntity]:
```

---

## 8. Super Graph Output Artifacts

The Super Graph can optionally be serialized to disk as a federated registry:

### Federated Architecture Index

```yaml
schema_version: "1.2"
type: federated_architecture_index
federation_id: ste-ecosystem
assembled_at: "2026-03-13T12:00:00Z"

namespaces:
  - namespace: adr-architecture-kit
    entity_count: 150
    relationship_count: 90
    fingerprint: "abc123..."
  - namespace: ste-kernel
    entity_count: 200
    relationship_count: 120
    fingerprint: "def456..."

federated_entity_registry_path: super-graph/entity-registry.yaml
federated_relationship_registry_path: super-graph/relationship-registry.yaml
federated_unresolved_registry_path: super-graph/unresolved-registry.yaml

cross_repo_summary:
  cross_repo_relationships: 15
  resolved_cross_refs: 12
  remaining_unresolved: 3
```

### Federated Entity Registry

Contains all entities from all namespaces, each with `namespace` and
`qualified_id` fields. Entities sorted by `(namespace, entity_type, id)`.

### Federated Relationship Registry

Contains all relationships (local + cross-repo + derived inverses).
Cross-repo relationships marked with `cross_repository: true` and
`federation_derived: true` (for derived inverses).

---

## 9. Risks and Constraints

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Federation manifest becomes stale | Missing or extra repos in Super Graph | CI job that validates manifest against actual repos |
| Large federation overwhelms memory | OOM during full merge | Lazy loading (Strategy 5.2); index-only federation for overview |
| Cross-repo ref resolution is slow | N repos × M unresolved = N×M lookups | Global entity index is O(1) lookup; resolution is O(total_unresolved) |
| Derived inverse relationships create noise | Bidirectional edges double relationship count | Mark as `federation_derived`; filter in queries |
| Namespace rename cascades across federation | Every cross-repo ref to old namespace breaks | Namespaces are immutable; rename is a breaking migration requiring coordination |
| Circular cross-repo dependencies | No clear dependency ordering | Detect and report; don't prohibit (architectures can be circular) |
| Schema version mismatch across repos | Repo A on 1.1, repo B on 1.2 | Federation engine normalizes to common schema version; reject incompatible majors |

### Constraints

1. **Each repo compiles independently.** Federation is a post-compilation step. Repos don't need to know about other repos at compile time (except for cross-repo references in source ADRs).
2. **No central entity authority.** Each repo assigns its own IDs. Global uniqueness comes from namespace qualification.
3. **Federation is read-only.** The federation engine never writes to per-repo registries. It only reads and merges.
4. **Cross-repo references are opt-in.** A repo with no cross-repo references participates in federation normally (all its entities are available) but declares no cross-repo edges.
5. **Federation manifest is the single source of truth** for which repos participate. Adding/removing a repo requires updating the manifest.
6. **Authoritative ownership.** Each namespace owns its entities. No namespace can modify another namespace's entities through federation.
