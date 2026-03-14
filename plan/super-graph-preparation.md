# Super Graph Preparation

## Purpose

This document defines how the adr-architecture-kit registry model should evolve
to support a multi-repository architecture graph — the **Super Graph**. The Super
Graph is a federated, globally-addressable architecture knowledge model constructed
by merging compiled registries from multiple independent repositories.

---

## 1. What Is the Super Graph

The Super Graph is the union of all architecture registries across all STE-managed
repositories, queryable as a single coherent graph.

```
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│    repo-alpha     │   │    repo-beta      │   │    repo-gamma    │
│                   │   │                   │   │                  │
│  architecture-    │   │  architecture-    │   │  architecture-   │
│  index.yaml       │   │  index.yaml       │   │  index.yaml      │
│  entity-registry  │   │  entity-registry  │   │  entity-registry │
│  relationship-reg │   │  relationship-reg │   │  relationship-   │
│  unresolved-reg   │   │  unresolved-reg   │   │  unresolved-reg  │
│                   │   │                   │   │                  │
│  namespace:       │   │  namespace:       │   │  namespace:      │
│  "alpha"          │   │  "beta"           │   │  "gamma"         │
└────────┬──────────┘   └────────┬──────────┘   └────────┬─────────┘
         │                       │                        │
         └───────────┬───────────┘────────────────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │       SUPER GRAPH          │
         │                            │
         │  alpha:CAP-0001            │
         │  alpha:DEC-0001            │
         │  beta:CAP-0001             │
         │  beta:COMP-SERVICE-A       │
         │  gamma:SYS-0001            │
         │                            │
         │  cross-repo relationships: │
         │  beta:COMP-X --uses-->     │
         │    alpha:CAP-0001          │
         │                            │
         └───────────────────────────┘
```

### What It Enables

| Capability | Description |
|---|---|
| Global entity lookup | Find any entity across any repository by qualified ID |
| Cross-repo dependency tracking | "Service B depends on capabilities defined in repo A" |
| Architecture-wide impact analysis | "If we change INV-0001 in the governance repo, what breaks?" |
| Capability coverage across services | "Which repos implement CAP-0001?" |
| Invariant enforcement auditing | "Is INV-0003 enforced in every service repo?" |
| System topology visualization | Map how systems/components across repos connect |

---

## 2. Current State Analysis

### Entity IDs Are Bare

All entity IDs use type-prefix + 4-digit numeric with no namespace:

```
CAP-0001    (not alpha:CAP-0001)
DEC-0001    (not alpha:DEC-0001)
COMP-0010   (not alpha:COMP-0010)
```

Validated by Pydantic regex patterns: `^CAP-\d{4}$`, `^DEC-\d{4}$`, etc.

### Namespace Exists but Is Not Embedded

`architecture_namespace` is defined in `PROJECT.yaml` and appears in
`architecture-index.yaml` as a header field:

```yaml
architecture_namespace: adr-architecture-kit
```

It is **not** embedded in:
- Entity IDs (`CAP-0001`, not `adr-architecture-kit:CAP-0001`)
- Relationship IDs (`declared_in:CAP-0001:ADR-L-0001`)
- Source references (`ADR-L-0001#CAP-0001`)
- Artifact paths (`adrs/logical/ADR-L-0001-foo.yaml`)

### Relationship IDs Are Scope-Local

Format: `{type}:{from_id}:{to_id}` — e.g., `declared_in:CAP-0001:ADR-L-0001`

These are unique within a scope but collide immediately when two repos have
entities with the same bare IDs.

### Multi-Scope Is Independent

`resolve_recursive()` finds sub-modules within a workspace, but each scope
generates its own registries independently. There is no cross-scope entity
resolution, no merged registry, and no collision detection between scopes.

### CanonicalIdNormalizer Handles Intra-Scope Only

The normalizer detects and resolves entity ID collisions **within a single scope**
(e.g., two ADRs both defining `CAP-0001`). It does not operate across scopes
or repositories.

### Summary: What Must Change

| Aspect | Current | Super Graph Requirement |
|---|---|---|
| Entity IDs | Bare (`CAP-0001`) | Globally qualified (`alpha:CAP-0001`) |
| Relationship IDs | Scope-local triple | Globally qualified triple |
| Source references | Scope-local compound | Namespace-qualified compound |
| Namespace | Metadata header only | Structural identity component |
| Cross-repo relationships | Not supported | First-class relationship type |
| Registry merging | Not supported | Federation protocol |
| Collision detection | Intra-scope only | Cross-repo |

---

## 3. Architectural Gaps for Super Graph Support

### Gap 1: No Globally Unique Entity Identity

**Problem:** `CAP-0001` in repo-alpha and `CAP-0001` in repo-beta are
indistinguishable. Merging their registries produces a collision.

**Required:** A composite identifier scheme that qualifies bare IDs with
their origin namespace.

### Gap 2: No Cross-Repository Relationship Model

**Problem:** There is no way to express "component X in repo-beta
implements capability Y in repo-alpha." The relationship model assumes
both endpoints exist in the same entity registry.

**Required:** Relationship records that reference entities across namespaces,
with appropriate provenance.

### Gap 3: No Registry Federation Protocol

**Problem:** There is no defined process for loading multiple registries
and merging them into a unified graph. No ordering, no conflict resolution,
no incremental update.

**Required:** A federation protocol that defines how registries are discovered,
loaded, validated, and merged.

### Gap 4: No Cross-Repo Unresolved Detection

**Problem:** Unresolved references are detected within a single scope.
A reference to `CAP-0001` in repo-beta might resolve to an entity in
repo-alpha, but the current system marks it unresolved because it only
looks locally.

**Required:** Unresolved detection that can resolve references across
federated registries.

### Gap 5: No Graph Integrity Across Repos

**Problem:** The bundle consistency check (`_validate_bundle()`) verifies
that all relationship endpoints exist in the local entity registry.
In a federated graph, endpoints may exist in different registries.

**Required:** Federated integrity validation that checks referential
integrity across the merged graph.

---

## 4. Preparation Strategy: Incremental Evolution

The Super Graph requires changes to the identity model, the relationship
model, and the registry format. These changes should be introduced
incrementally to avoid a breaking migration.

### Phase S0: Namespace Awareness (Pre-Federation)

**Goal:** Make every entity and relationship namespace-aware internally,
without changing the registry file format.

1. **Qualify entities at load time.** When `ArchitectureRepository` loads
   a registry, it reads `architecture_namespace` from the index and
   attaches it to each entity as `entity.namespace`. This is in-memory only.

2. **Introduce `QualifiedEntityId`.** A value type that pairs namespace + bare ID:
   ```python
   @dataclass(frozen=True)
   class QualifiedEntityId:
       namespace: str   # "alpha", "beta", or "" for local
       bare_id: str     # "CAP-0001"

       def __str__(self) -> str:
           return f"{self.namespace}:{self.bare_id}" if self.namespace else self.bare_id

       @classmethod
       def parse(cls, s: str) -> "QualifiedEntityId":
           if ":" in s:
               ns, bare = s.split(":", 1)
               return cls(ns, bare)
           return cls("", s)
   ```

3. **Ensure namespace is always set.** Validate that every `PROJECT.yaml`
   defines `architecture_namespace`. It is currently required but not
   enforced as a uniqueness constraint. For Super Graph, namespaces
   must be globally unique (convention: use repository name or org-scoped
   identifier).

**Breaking changes:** None. Registry files unchanged. In-memory enrichment only.

### Phase S1: Qualified IDs in Registries

**Goal:** Emit qualified entity IDs in registry output.

1. **Registry format change.** Add `namespace` field to entity-registry:
   ```yaml
   entities:
     - id: CAP-0001
       namespace: adr-architecture-kit    # NEW FIELD
       qualified_id: adr-architecture-kit:CAP-0001  # NEW FIELD
       entity_type: capability
       ...
   ```

2. **Relationship format change.** Qualify relationship endpoint IDs:
   ```yaml
   relationships:
     - relationship_id: declared_in:adr-architecture-kit:CAP-0001:adr-architecture-kit:ADR-L-0001
       from_entity_id: adr-architecture-kit:CAP-0001     # qualified
       to_entity_id: adr-architecture-kit:ADR-L-0001     # qualified
       from_namespace: adr-architecture-kit               # NEW FIELD
       to_namespace: adr-architecture-kit                 # NEW FIELD
       ...
   ```

3. **Backward compatibility.** The bare `id` field remains. `namespace`
   and `qualified_id` are additive. Old consumers that ignore unknown
   fields continue to work.

**Schema version:** Bump to 1.2 (minor — additive fields).

### Phase S2: Cross-Repository Relationship Type

**Goal:** Support relationships between entities in different namespaces.

1. **New relationship classification:** `cross_repository`
   ```yaml
   - relationship_id: implements:beta:COMP-SERVICE-A:alpha:CAP-0001
     relationship_type: implements
     from_entity_id: beta:COMP-SERVICE-A
     to_entity_id: alpha:CAP-0001
     provenance_classification: explicit
     cross_repository: true              # NEW FIELD
     from_namespace: beta
     to_namespace: alpha
   ```

2. **Declared in source ADR.** Cross-repo relationships are declared in the
   ADR that introduces the "from" entity. Example: repo-beta's component ADR
   declares `implements_capabilities: ["alpha:CAP-0001"]`.

3. **Unresolved until federated.** At compile time (single repo), cross-repo
   references are recorded as unresolved with `gap_class: cross_repository`.
   At federation time (Super Graph construction), they are resolved.

### Phase S3: Registry Federation Protocol

**Goal:** Define how multiple compiled registries are merged.

(Detailed in `registry-federation-model.md`)

---

## 5. Impact on Existing Systems

### Compiler (adr-architecture-kit)

| Change | Phase | Impact |
|---|---|---|
| Attach namespace to entities at load time | S0 | Internal only |
| Emit `namespace` and `qualified_id` in registries | S1 | Schema 1.2 |
| Support qualified ID references in ADR source fields | S2 | Schema change for `implements_capabilities`, `related_adrs`, etc. |
| Detect and emit cross-repo unresolved records | S2 | New gap_class |

### Kernel (ste-kernel)

| Change | Phase | Impact |
|---|---|---|
| Use `QualifiedEntityId` in entity index | S0 | Internal model change |
| Support both bare and qualified IDs in queries | S1 | Query surface update |
| Load multiple registries into federated model | S3 | New `SuperGraphModel` |
| Resolve cross-repo relationships | S3 | Federation resolution pass |

### ADR Authors

| Change | Phase | Impact |
|---|---|---|
| None | S0-S1 | Transparent |
| Use qualified IDs for cross-repo references | S2 | `implements_capabilities: ["other-repo:CAP-0001"]` |

---

## 6. Risks and Constraints

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Namespace collisions across orgs | Two repos with same namespace create ambiguity | Convention: use `{org}/{repo}` or enforce uniqueness in federation manifest |
| Qualified IDs make ADR authoring verbose | Authors must type `alpha:CAP-0001` instead of `CAP-0001` | Bare IDs resolve to local namespace by default; qualified only for cross-repo |
| Registry format change breaks existing consumers | Kernel or other tools fail on new fields | Minor version bump (additive only); consumers ignore unknown fields |
| Super Graph becomes too large to hold in memory | Thousands of repos × thousands of entities | Lazy loading by namespace; only load registries needed for current query |
| Cross-repo relationships are fragile | Repo A renames an entity, repo B's reference breaks | Federation validation detects broken cross-repo refs; treat as unresolved |
| Circular cross-repo dependencies | Repo A depends on B, B depends on A | Allow but flag; no prohibition on cycles at the architecture level |

### Constraints

1. **Bare IDs remain valid within a single repo.** Qualification is only required for cross-repo references. Local compilation produces bare IDs with namespace metadata attached.
2. **Backward compatible.** Phase S0 and S1 are additive. Existing tools that ignore unknown fields continue working.
3. **Namespace is the repo's responsibility.** Each repo declares its own namespace in `PROJECT.yaml`. The Super Graph trusts these declarations.
4. **Federation is a separate system.** The compiler (adr-kit) produces per-repo registries. The Super Graph assembler is a separate tool or kernel capability.
5. **No centralized ID authority.** Entity IDs are locally assigned. Global uniqueness comes from namespace qualification, not a central registry.
