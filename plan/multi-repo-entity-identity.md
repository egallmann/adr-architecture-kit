# Multi-Repository Entity Identity

## Purpose

This document defines the globally unique entity identification scheme for
the STE Super Graph. It specifies how bare, scope-local entity IDs evolve
into globally addressable identifiers that support federation across
repositories without collisions.

---

## 1. The Collision Problem

### Current ID Format

Every entity ID in adr-architecture-kit is a bare type-prefix + numeric suffix:

| Entity Type | Pattern | Example |
|---|---|---|
| Capability | `^CAP-\d{4}$` | `CAP-0001` |
| Decision | `^DEC-\d{4}$` | `DEC-0001` |
| Invariant | `^INV-\d{4}$` | `INV-0001` |
| Component | `^COMP-\d{4}$` or `^COMP-[A-Z0-9-]+$` | `COMP-0010`, `COMP-SCHEMA-VALIDATOR` |
| System | `SYS-\d{4}` (derived) | `SYS-0001` |
| ADR | `^ADR-(L\|V\|P\|PS\|PC)-\d{4}$` | `ADR-L-0001` |
| Boundary | `^BOUND-\d{4}$` | `BOUND-0001` |
| NFR | `^NFR-\d{4}$` | `NFR-0001` |
| Constraint | `^CONST-\d{4}$` | `CONST-0001` |
| Contract | `^CONTRACT-\d{4}$` | `CONTRACT-0001` |
| Gap | `^GAP-\d{4}$` | `GAP-0001` |
| Interface | `^IFACE-\d{4}$` | `IFACE-0001` |
| Integration | `^INTEG-\d{4}$` | `INTEG-0001` |
| Impl Decision | `^IMPL-\d{4}$` | `IMPL-0001` |

### Collision Scenario

```
Repository: ste-kernel                Repository: adr-architecture-kit
namespace: ste-kernel                 namespace: adr-architecture-kit

  ADR-L-0001                            ADR-L-0001
  ├── CAP-0001  (Kernel reasoning)      ├── CAP-0001  (Machine-verifiable docs)
  ├── DEC-0001  (Use graph DB)          ├── DEC-0001  (Use YAML not markdown)
  └── INV-0001  (No stale cache)        └── INV-0001  (Schema validation required)

  ADR-PS-0001                           ADR-PS-0001
  └── SYS-0001  (Kernel runtime)        └── SYS-0001  (Discovery system)
```

Every ID collides. Naively merging these registries produces an entity graph
where `CAP-0001` is both "Kernel reasoning" and "Machine-verifiable docs" —
semantically meaningless.

### Why Numeric Counters Guarantee Collisions

Each repo starts its counters at 0001. The first capability in every repo
is `CAP-0001`. The first decision is `DEC-0001`. Collisions are not edge cases;
they are **inevitable** in any multi-repo scenario.

---

## 2. Qualified Entity ID Design

### 2.1 Composite Identifier Structure

```
┌──────────────────┬─────────────┐
│    namespace      │   bare_id   │
├──────────────────┼─────────────┤
│ adr-architecture │  CAP-0001   │
│     -kit         │             │
└──────────────────┴─────────────┘
         │                │
         └───────┬────────┘
                 ▼
   adr-architecture-kit:CAP-0001
```

**Format:** `{namespace}:{bare_id}`

**Examples:**
```
adr-architecture-kit:CAP-0001
adr-architecture-kit:DEC-0001
adr-architecture-kit:ADR-L-0001
adr-architecture-kit:ADR-L-0001#CAP-0001    (compound ref)
ste-kernel:CAP-0001
ste-kernel:COMP-GRAPH-ENGINE
ste-runtime:SYS-0001
```

### 2.2 Namespace Rules

| Rule | Description |
|---|---|
| **Source** | From `PROJECT.yaml` → `architecture_documentation.architecture_namespace` |
| **Format** | Lowercase alphanumeric + hyphens: `^[a-z][a-z0-9-]*$` |
| **Length** | 2–64 characters |
| **Uniqueness** | Globally unique across all federated repos (enforced by federation manifest) |
| **Stability** | Must not change after first federation registration (breaking change) |
| **Convention** | Use repository name or `{org}-{repo}` for disambiguation |

**Examples of valid namespaces:**
```
adr-architecture-kit
ste-kernel
ste-runtime
payment-service
acme-auth-gateway
```

**Invalid:**
```
ADR-Architecture-Kit     (uppercase)
adr_architecture_kit     (underscores)
a                        (too short)
```

### 2.3 Bare ID Resolution Rule

Within a single repository, entity IDs remain bare:

```yaml
# In adr-architecture-kit's ADR-L-0001:
capabilities:
  - id: CAP-0001                           # bare — resolves to local namespace
    implemented_by_components:
      - COMP-0010                          # bare — local
```

The qualified form is only used for **cross-repo references**:

```yaml
# In ste-kernel's ADR-L-0005:
decisions:
  - id: DEC-0042
    enables_capabilities:
      - CAP-0003                           # bare — local (ste-kernel:CAP-0003)
      - adr-architecture-kit:CAP-0001      # qualified — cross-repo
```

**Resolution algorithm:**
1. If ID contains `:` → parse as `namespace:bare_id`
2. If ID is bare → qualify with current repository's namespace

This means authors never need to qualify local references. Cross-repo
references are the only place qualified IDs appear in source artifacts.

### 2.4 QualifiedEntityId Value Type

```python
@dataclass(frozen=True, order=True)
class QualifiedEntityId:
    """Globally unique entity identifier."""
    namespace: str
    bare_id: str

    def __str__(self) -> str:
        return f"{self.namespace}:{self.bare_id}"

    @property
    def entity_type_prefix(self) -> str:
        """Extract type prefix: 'CAP' from 'CAP-0001'."""
        return self.bare_id.split("-")[0]

    @classmethod
    def parse(cls, raw: str, default_namespace: str = "") -> "QualifiedEntityId":
        """Parse a raw ID string, using default_namespace for bare IDs."""
        if ":" in raw:
            namespace, bare_id = raw.split(":", 1)
            return cls(namespace=namespace, bare_id=bare_id)
        return cls(namespace=default_namespace, bare_id=raw)

    @classmethod
    def local(cls, bare_id: str, namespace: str) -> "QualifiedEntityId":
        """Create a qualified ID for a local entity."""
        return cls(namespace=namespace, bare_id=bare_id)
```

**Properties:**
- Frozen (immutable, hashable — usable as dict key)
- Ordered (sortable — `(namespace, bare_id)` tuple ordering)
- String-serializable: `str(qid)` → `"adr-architecture-kit:CAP-0001"`
- Parseable: `QualifiedEntityId.parse("adr-architecture-kit:CAP-0001")`

### 2.5 Qualified Compound References

The current compound reference format `ADR-L-0001#CAP-0001` extends naturally:

| Scope | Format | Example |
|---|---|---|
| Local | `{bare_adr_id}#{bare_entity_id}` | `ADR-L-0001#CAP-0001` |
| Cross-repo | `{namespace}:{bare_adr_id}#{bare_entity_id}` | `ste-kernel:ADR-L-0001#CAP-0001` |
| Fully qualified | `{ns}:{bare_adr_id}#{ns}:{bare_entity_id}` | Not needed — namespace of fragment matches parent |

**Rule:** In a compound reference `ns:ADR-L-0001#CAP-0001`, the namespace
applies to both the ADR and the entity within it. An entity is always
in the same namespace as its parent ADR.

### 2.6 Qualified Relationship IDs

Current format: `{type}:{from_bare}:{to_bare}`

Qualified format: `{type}:{from_qualified}:{to_qualified}`

```
# Local (within same namespace)
declared_in:adr-architecture-kit:CAP-0001:adr-architecture-kit:ADR-L-0001

# Cross-repo
implements:ste-kernel:COMP-GRAPH-ENGINE:adr-architecture-kit:CAP-0001
```

**Readability note:** Qualified relationship IDs are long. This is acceptable
because relationship IDs are machine-generated identifiers, never typed by
humans. They serve as dedup keys and log references.

---

## 3. Registry Format Changes

### 3.1 Entity Registry (Schema 1.2)

```yaml
schema_version: "1.2"
type: normalized_entity_registry
namespace: adr-architecture-kit           # NEW: registry-level namespace

entities:
  - id: CAP-0001                          # bare ID (unchanged)
    namespace: adr-architecture-kit       # NEW: entity-level namespace
    qualified_id: adr-architecture-kit:CAP-0001  # NEW: convenience field
    entity_type: capability
    name: Machine-Verifiable Architecture Documentation
    summary: ...
    canonical_source:
      source_type: logical_adr
      source_ref: ADR-L-0001#CAP-0001     # local refs remain bare
      artifact_path: adrs/logical/ADR-L-0001-ste-compliant-adr-system.yaml
    ...
```

**New fields:**
- `namespace` (registry-level): declares the namespace for all entities in this file
- `namespace` (entity-level): redundant with registry-level but explicit per-entity for federation (when entities from multiple namespaces coexist in a merged registry)
- `qualified_id`: precomputed `namespace:bare_id` for convenience

**Backward compatibility:** `id` field keeps the bare value. Consumers that
ignore unknown fields see no change.

### 3.2 Relationship Registry (Schema 1.2)

```yaml
schema_version: "1.2"
type: relationship_registry
namespace: adr-architecture-kit           # NEW

relationships:
  - relationship_id: declared_in:adr-architecture-kit:CAP-0001:adr-architecture-kit:ADR-L-0001
    relationship_type: declared_in
    from_entity_id: CAP-0001              # bare (unchanged for local)
    to_entity_id: ADR-L-0001              # bare (unchanged for local)
    from_qualified_id: adr-architecture-kit:CAP-0001   # NEW
    to_qualified_id: adr-architecture-kit:ADR-L-0001   # NEW
    from_namespace: adr-architecture-kit               # NEW
    to_namespace: adr-architecture-kit                 # NEW
    cross_repository: false                            # NEW
    ...
```

**Cross-repo example (in ste-kernel's registry):**
```yaml
  - relationship_id: implements:ste-kernel:COMP-GRAPH-ENGINE:adr-architecture-kit:CAP-0001
    relationship_type: implements
    from_entity_id: COMP-GRAPH-ENGINE
    to_entity_id: adr-architecture-kit:CAP-0001   # qualified (cross-repo target)
    from_qualified_id: ste-kernel:COMP-GRAPH-ENGINE
    to_qualified_id: adr-architecture-kit:CAP-0001
    from_namespace: ste-kernel
    to_namespace: adr-architecture-kit
    cross_repository: true
    ...
```

### 3.3 Unresolved Registry (Schema 1.2)

```yaml
  - id: GAP-XREF-COMP-GRAPH-ENGINE-adr-architecture-kit:CAP-0001
    gap_class: cross_repository                        # NEW gap class
    gap_type: unresolved_cross_repo_reference
    source_entity_id: COMP-GRAPH-ENGINE
    source_namespace: ste-kernel                       # NEW
    related_entity_id: adr-architecture-kit:CAP-0001   # qualified target
    related_namespace: adr-architecture-kit             # NEW
    expected_relationship: implements
    severity: important
    ...
```

**Lifecycle:** Cross-repo unresolved records are created at compile time
(single repo) and resolved at federation time (Super Graph assembly).

---

## 4. ID Lifecycle

### 4.1 At Authoring Time (ADR Source)

Authors use bare IDs for local references, qualified IDs for cross-repo:

```yaml
# Local reference (99% of cases)
capabilities:
  - id: CAP-0001
    implemented_by_components:
      - COMP-0010

# Cross-repo reference (rare, intentional)
decisions:
  - id: DEC-0042
    enables_capabilities:
      - ste-runtime:CAP-0003
```

### 4.2 At Compile Time (adr-kit compiler)

The compiler:
1. Reads `architecture_namespace` from `PROJECT.yaml`
2. Qualifies all local entities: `CAP-0001` → `QualifiedEntityId("adr-architecture-kit", "CAP-0001")`
3. Parses cross-repo references: `ste-runtime:CAP-0003` → `QualifiedEntityId("ste-runtime", "CAP-0003")`
4. For cross-repo targets: emits `cross_repository` unresolved record (target not in local registry)
5. Emits both `id` (bare) and `qualified_id` (full) in registry output

### 4.3 At Federation Time (Super Graph Assembly)

The federation engine:
1. Loads registries from all repos
2. Indexes entities by `qualified_id` (globally unique)
3. Resolves cross-repo unresolved records: if `ste-runtime:CAP-0003` exists in ste-runtime's registry, promote from unresolved to resolved relationship
4. Detects remaining unresolved: cross-repo refs to entities that don't exist in any loaded registry

### 4.4 At Query Time (Kernel)

The kernel accepts both bare and qualified IDs:

```python
# Bare ID resolves to default namespace (must be unambiguous)
entity = model.get_entity("CAP-0001")  # works if only one CAP-0001 across all namespaces

# Qualified ID always unambiguous
entity = model.get_entity("adr-architecture-kit:CAP-0001")

# In single-repo mode, bare IDs always work (no collision possible)
# In Super Graph mode, bare IDs require disambiguation
```

---

## 5. Migration Path

### Step 1: Validate Namespace Presence (Now)

Ensure every `PROJECT.yaml` has `architecture_namespace`. This is already
required by the compiler (`_load_namespace()` raises on missing). No change.

### Step 2: Namespace Convention (Now)

Establish naming convention for namespaces across the STE ecosystem.
Document in a governance ADR.

**Recommended convention:** repository name (e.g., `adr-architecture-kit`,
`ste-kernel`, `ste-runtime`). If ambiguous, prefix with org: `acme-payment-service`.

### Step 3: QualifiedEntityId in Compiler IR (Phase S0)

Introduce `QualifiedEntityId` as the internal representation. The compiler's
`ArchModel` uses qualified IDs internally, even though registry output
still uses bare IDs. This enables the compiler to detect cross-repo references
and emit proper unresolved records.

### Step 4: Qualified Fields in Registry Output (Phase S1)

Add `namespace`, `qualified_id`, `from_namespace`, `to_namespace`,
`cross_repository` fields to registry schemas. Bump to schema 1.2.

**Bare fields remain unchanged.** This is an additive schema change.

### Step 5: Cross-Repo Reference Syntax in ADR Source (Phase S2)

Allow `namespace:bare_id` syntax in ADR YAML fields that accept entity
references (`implements_capabilities`, `related_adrs`, `enforces_invariants`, etc.).

**Schema change:** Relax Pydantic patterns to accept optional namespace prefix:
```python
# Current
id: str = Field(..., pattern=r"^CAP-\d{4}$")

# Extended (for reference fields, not id fields)
# Reference fields accept: "CAP-0001" or "other-repo:CAP-0001"
```

**Entity definition IDs stay bare.** Only reference fields (pointing to other
entities) accept qualified IDs.

### Step 6: Federation Protocol (Phase S3)

Implement the Super Graph assembly engine.
(Detailed in `registry-federation-model.md`)

---

## 6. Symbolic Component IDs

### Special Case: COMP-{NAME}

Components support two ID patterns:
- Numeric: `^COMP-\d{4}$` (e.g., `COMP-0010`)
- Symbolic: `^COMP-[A-Z0-9-]+$` (e.g., `COMP-SCHEMA-VALIDATOR`)

Symbolic IDs have higher collision risk because meaningful names are
more likely to coincide across repos (e.g., `COMP-API-GATEWAY`).

**Mitigation:** Namespace qualification resolves this:
```
alpha:COMP-API-GATEWAY ≠ beta:COMP-API-GATEWAY
```

**Recommendation for authors:** Prefer symbolic IDs that include
domain context: `COMP-PAYMENT-API-GATEWAY` rather than `COMP-API-GATEWAY`.

---

## 7. System-Derived IDs

### Special Case: SYS-XXXX

System IDs are derived from ADR-PS IDs:
```python
def _system_entity_id(self, adr_id: str) -> str:
    return f"SYS-{adr_id.replace('ADR-PS-', '')}"
    # ADR-PS-0001 → SYS-0001
```

In the Super Graph, derived IDs follow their source ADR's namespace:
```
adr-architecture-kit:ADR-PS-0001 → adr-architecture-kit:SYS-0001
ste-kernel:ADR-PS-0001 → ste-kernel:SYS-0001
```

No special handling needed — namespace qualification resolves the derivation.

---

## 8. Unresolved Gap ID Patterns

### Current Gap IDs

| Pattern | Source |
|---|---|
| `UGAP-{adr_id}-{gap_id}` | Author-declared gap |
| `GAP-IMPL-{cap_id}-{comp_id}` | Missing implementing component |
| `GAP-INV-{dec_id}-{inv_id}` | Missing invariant target |
| `GAP-CAP-{dec_id}-{cap_id}` | Missing capability target |
| `GAP-MISSING-CAP-{comp_id}-{cap_id}` | Missing capability in component |
| `GAP-MISSING-SYS-{comp_id}-{sys_id}` | Missing system target |

### Qualified Gap IDs

Gap IDs embed entity IDs. When those entity IDs are qualified, gap IDs become:

```
# Local gap (unchanged in single-repo)
GAP-IMPL-CAP-0001-COMP-0010

# Cross-repo gap (new)
GAP-XREF-COMP-GRAPH-ENGINE-adr-architecture-kit:CAP-0001
```

**Convention for cross-repo gaps:** Prefix with `GAP-XREF-` to distinguish
from intra-repo gaps.

---

## 9. Risks and Constraints

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Namespace rename breaks all qualified IDs | Every cross-repo reference to this namespace becomes invalid | Namespace is immutable after federation registration; rename requires migration |
| Colon in qualified ID conflicts with relationship ID format | `{type}:{from}:{to}` parsing becomes ambiguous | Relationship IDs use the full qualified form; parse from left: type is before first `:`, rest parsed by `QualifiedEntityId.parse()` which splits on first `:` within each segment. Alternatively, use `/` as namespace separator. |
| Authors forget to qualify cross-repo references | Reference resolves to local (wrong) entity or becomes unresolved | Compiler warns when a bare reference matches both a local and a known cross-repo entity |
| Qualified IDs are verbose in YAML source | Author friction | Bare IDs are the default; qualification is opt-in for cross-repo only |

### Separator Character Analysis

The `:` separator in `namespace:bare_id` creates ambiguity with the
relationship ID format `type:from:to`. This requires careful parsing.

**Option A: Colon separator with structured parsing**
```
Relationship ID: declared_in:adr-architecture-kit:CAP-0001:adr-architecture-kit:ADR-L-0001
Parse: split on first colon → type = "declared_in"
       remainder: "adr-architecture-kit:CAP-0001:adr-architecture-kit:ADR-L-0001"
       QualifiedEntityId.parse each segment
```
This works because entity bare IDs never contain colons.

**Option B: Slash separator**
```
adr-architecture-kit/CAP-0001
```
Avoids colon ambiguity entirely. Resembles URL paths.

**Option C: Double-colon separator**
```
adr-architecture-kit::CAP-0001
```
Visually distinct from the relationship ID colons.

**Recommendation:** Use **colon** (Option A). It is the most natural separator,
matches URI conventions, and the parsing ambiguity is resolvable because
namespace format (`^[a-z][a-z0-9-]*$`) and bare ID format (`^[A-Z]+-`) have
non-overlapping character classes. A namespace always starts lowercase;
a bare ID always starts uppercase. This makes the split point deterministic.

### Constraints

1. **Bare IDs unchanged in source.** Entity definition IDs remain `^CAP-\d{4}$` etc.
2. **Namespace never embedded in the bare ID itself.** It is a separate field.
3. **Additive schema changes only.** Old consumers see bare IDs unchanged.
4. **No central ID authority.** Namespaces are self-assigned. Uniqueness enforced at federation time.
5. **Cross-repo references are opt-in.** Repos with no external dependencies never use qualified IDs.
