# Architecture Canonical Model

## Purpose

This document is the single authoritative reference for the adr-architecture-kit
architecture. Where plan documents diverge, this document resolves the conflict.
It incorporates all amendments from `architecture-convergence-review.md`.

---

## 1. System Identity

**adr-architecture-kit** is an architecture compiler. It reads ADR source
artifacts (YAML), builds an intermediate representation, runs analysis passes,
and emits compiled registries consumable by the STE Kernel and human readers.

### Compilation Model

```
ADR Source (YAML)  ──>  Frontend  ──>  IR (ArchModel)  ──>  Passes  ──>  Backend  ──>  Registries (YAML)
                                                                                         │
                                                                                         ├─ entity-registry.yaml
                                                                                         ├─ relationship-registry.yaml
                                                                                         ├─ unresolved-registry.yaml
                                                                                         ├─ architecture-index.yaml
                                                                                         ├─ 5 subset registries
                                                                                         ├─ 1 legacy registry
                                                                                         ├─ manifest.yaml
                                                                                         └─ rendered/*.md
```

---

## 2. Entity Type System

### 2.1 ID Patterns (18 patterns, 14 entity types)

| Prefix | Entity Type | Regex | Source |
|---|---|---|---|
| ADR-L-XXXX | adr (logical) | `^ADR-L-\d{4}$` | File identity |
| ADR-V-XXXX | adr (vision) | `^ADR-V-\d{4}$` | File identity |
| ADR-P-XXXX | adr (physical, legacy) | `^ADR-P-\d{4}$` | File identity |
| ADR-PS-XXXX | adr (physical-system) | `^ADR-PS-\d{4}$` | File identity |
| ADR-PC-XXXX | adr (physical-component) | `^ADR-PC-\d{4}$` | File identity |
| CAP-XXXX | capability | `^CAP-\d{4}$` | LogicalADR.capabilities |
| DEC-XXXX | decision | `^DEC-\d{4}$` | LogicalADR.decisions |
| INV-XXXX | invariant | `^INV-\d{4}$` | LogicalADR.invariants / Standalone |
| COMP-XXXX | component | `^COMP-\d{4}$` or `^COMP-[A-Z0-9-]+$` | ComponentSpec |
| SYS-XXXX | system | `SYS-\d{4}` (derived from ADR-PS) | PhysicalSystemADR |
| CONST-XXXX | constraint | `^CONST-\d{4}$` | LogicalADR.constraints |
| BOUND-XXXX | boundary | `^BOUND-\d{4}$` | LogicalADR.boundaries |
| NFR-XXXX | nfr | `^NFR-\d{4}$` | LogicalADR.nfrs |
| CONTRACT-XXXX | contract | `^CONTRACT-\d{4}$` | LogicalADR.contracts |
| GAP-XXXX | gap | `^GAP-\d{4}$` | LogicalADR.gaps |
| IFACE-XXXX | interface | `^IFACE-\d{4}$` | ComponentSpec.interfaces |
| INTEG-XXXX | integration | `^INTEG-\d{4}$` | PhysicalComponentADR.integration_points |
| IMPL-XXXX | impl_decision | `^IMPL-\d{4}$` | PhysicalComponentADR.impl_decisions |

### 2.2 Entity Type Scopes

| Scope | Count | Types | Used By |
|---|---|---|---|
| **Registry types** | 6 | adr, capability, decision, invariant, component, system | Registry output, kernel contract |
| **IR types** | 14 | Registry 6 + constraint, boundary, nfr, contract, gap, interface, integration, impl_decision | Compiler IR, analysis passes |
| **ID patterns** | 18 | IR 14 with ADR subtypes counted separately | ID validation |

The compiler IR (ArchModel.entities) stores all 14 types. The backend registry
emitter filters to 6 types for registry output. Extended types (constraint,
boundary, nfr, contract, gap, interface, integration, impl_decision) are
available in the IR for lint passes and graph analysis but are **not** part of
the kernel contract.

---

## 3. Relationship Type System

### 3.1 Canonical Relationship Types (12)

| Type | From | To | Inverse | Provenance |
|---|---|---|---|---|
| declared_in | any entity | adr | — | explicit |
| references | adr | adr | — | explicit |
| implemented_by | capability | component | — | explicit |
| enables | decision | capability | enabled_by | explicit |
| enabled_by | capability | decision | enables | derived |
| enforces | decision or invariant | invariant or any | — | explicit |
| governs | decision | component | — | explicit |
| embodied_in | component | system | — | explicit |
| supersedes | any | any | superseded_by | explicit |
| superseded_by | any | any | supersedes | derived |
| refines | decision | decision | — | explicit |
| related_to | any | any | — | derived or heuristic |

**Closed set.** No additional relationship types are introduced by federation
or any other subsystem. The `implements` type referenced in some federation
examples does not exist — use `implemented_by` with the correct direction
(capability → component).

### 3.2 Provenance Classification

| Classification | Confidence | Meaning |
|---|---|---|
| explicit | 1.0 | Directly declared in source artifact |
| derived | 1.0 | Computed as inverse of explicit relationship |
| heuristic | 0.8 | Inferred from indirect evidence |

### 3.3 Relationship Identity

Format: `{type}:{from_id}:{to_id}`

Within a single scope, IDs are bare: `declared_in:CAP-0001:ADR-L-0001`

In federation context, IDs are qualified:
`declared_in:adr-architecture-kit:CAP-0001:adr-architecture-kit:ADR-L-0001`

Parsing rule: split on first `:` for type. Remaining segments parsed by
`QualifiedEntityId.parse()`, which uses the character class heuristic
(namespace=lowercase, bare_id=uppercase) for deterministic splitting.

---

## 4. Compiler Pipeline

### 4.1 Pipeline Structure

```
FRONTEND                      MIDDLE-END (PASSES)              BACKEND
──────────                    ──────────────────               ───────
F1: Discover                  M1:  Validate Business Rules     B1: Registry Emission (9 files)
F2: Parse                     M2:  Validate Cross-References   B2: Manifest Emission
F3: Schema Gate               M3:  Extract Logical Entities    B3: Legacy Registry Emission (1 file)
F4: Scope Resolution          M4:  Extract Physical Entities   B5: Markdown Emission
                              M5:  Resolve Invariant Canon     B6: Graph Emission (future)
IR CONSTRUCTION               M6:  Derive Relationships        B7: Kernel Contract Validation (future)
───────────────               M7:  Detect Unresolved
Assemble ArchModel            M8:  Score Completeness
                              M9:  Validate Bundle
                              M10: Lint (optional)
                              M11: Graph Analysis (optional)

FINALIZATION
────────────
Compute integrity headers
Write to disk
Emit CompilationResult
```

### 4.2 Pass Dependency Chain

```
M1 → M2 → M3 → M4 → M5 → M6 → M7 (from M6)
                                  → M8 (from M6) → M9 → M10 (optional)
                                                      → M11 (optional)
                                                         → Backend
```

All passes are strictly sequential. No parallelism in the middle-end.

### 4.3 Pass Protocol

```python
class CompilationPass(Protocol):
    name: str
    required: bool                      # False = optional (M10, M11)
    depends_on: tuple[str, ...]         # Passes that must run first
    halts_on_error: bool                # True = errors stop pipeline

    def run(self, model: ArchModel, config: CompilerConfig) -> None:
        """Mutate model in place. Append diagnostics to model.diagnostics."""
        ...
```

---

## 5. Intermediate Representation (ArchModel)

### 5.1 Canonical Structure

```python
@dataclass
class ArchModel:
    corpus: ParsedCorpus
    entities: EntityGraph
    relationships: RelGraph
    unresolved: UnresolvedList
    diagnostics: DiagnosticLog
    metadata: CompilationMeta
```

**6 fields. This is authoritative.** Earlier drafts with 5 fields (missing
`unresolved`) are superseded.

### 5.2 Component Types

| Component | Type | Role |
|---|---|---|
| `corpus` | `ParsedCorpus` | Typed AST forest — all parsed source artifacts |
| `entities` | `EntityGraph` | Indexed mutable entity collection (add/get/query) |
| `relationships` | `RelGraph` | Indexed mutable edge collection with adjacency indexes |
| `unresolved` | `UnresolvedList` | Unresolved reference records |
| `diagnostics` | `DiagnosticLog` | Append-only structured diagnostic accumulator |
| `metadata` | `CompilationMeta` | Compiler version, scope, namespace, timestamps, config |

### 5.3 IR Invariants

These properties hold for any valid ArchModel after compilation:

1. **Entity uniqueness:** No two entities share the same ID
2. **Relationship endpoint existence:** Every from/to ID exists in EntityGraph
3. **Relationship summary consistency:** Entity summaries and RelGraph are mutually consistent
4. **Unresolved source existence:** Every unresolved record's source_entity_id exists in EntityGraph
5. **Provenance completeness:** Every entity has non-empty provenance
6. **Canonical source validity:** Every entity's artifact_path points to a corpus file
7. **Deterministic ordering:** `all_sorted()` returns consistent order
8. **Type consistency:** Entity ID prefix matches entity_type

Enforced by M9 (Validate Bundle Consistency).

---

## 6. Diagnostics

### 6.1 Diagnostic Levels

| Level | Enum Value | Severity Ordinal | Meaning |
|---|---|---|---|
| ERROR | `"error"` | 0 | Compilation failure; halt in strict mode |
| WARNING | `"warning"` | 1 | Potential issue; does not halt |
| INFO | `"info"` | 2 | Informational; tracing/audit |

**3 levels. HINT is deferred.** Sort by severity ordinal (not alphabetical
enum value).

### 6.2 Diagnostic Structure

```python
@dataclass(frozen=True)
class Diagnostic:
    level: DiagnosticLevel
    stage: str            # "frontend.parse", "pass.validate", "backend.registry"
    code: str             # Machine-readable: "E001", "W002"
    message: str
    source: Optional[str] # File path, entity ID, or ADR ID
    field: Optional[str]  # Specific field within source
```

### 6.3 Error Code Ranges

| Range | Stage | Examples |
|---|---|---|
| E0xx / W0xx / I0xx | Frontend (parse, schema, scope) | E001: YAML syntax error, E002: Schema validation failure |
| E1xx / W1xx / I1xx | Validation (M1, M2) | E100: Missing implements_logical, W101: ADR has no decisions |
| E2xx / W2xx / I2xx | Extraction (M3, M4, M5) | E200: Duplicate entity ID, E201: Duplicate standalone invariant |
| E3xx / W3xx / I3xx | Resolution (M6, M7, M8, M9) | E300: Dangling relationship endpoint, W300: Unresolved reference |
| E4xx / W4xx / I4xx | Backend (B1–B7) | E400: Serialization failure |

---

## 7. Compilation Output

### 7.1 CompilationResult

```python
@dataclass
class CompilationResult:
    success: bool
    artifacts: list[OutputArtifact]
    diagnostics: DiagnosticLog
    statistics: CompilationStatistics
    model: ArchModel
    duration_ms: int
```

**6 fields. This is authoritative.** The `model` field retains the IR for
programmatic consumers. The `ir` name from earlier drafts is superseded.

### 7.2 CompilerConfig

```python
class CompilationMode(Enum):
    NORMAL = "normal"
    STRICT = "strict"       # Halt on first ERROR
    LENIENT = "lenient"     # Exclude invalid artifacts, continue

@dataclass
class CompilerConfig:
    mode: CompilationMode = CompilationMode.NORMAL
    emit: set[str] = field(default_factory=lambda: {
        "registries", "manifest", "legacy", "index", "markdown"
    })
    lint: bool = False
    analyze: bool = False
    timestamp: Optional[datetime] = None
    output_dir: Optional[Path] = None
```

**Mode is a single enum, not two bools.** The `strict`/`lenient` bool pair
from earlier drafts is superseded.

### 7.3 Output Artifacts

| Artifact | Emitter | Files | Phase Introduced |
|---|---|---|---|
| Primary registries | B1 | architecture-index.yaml, entity-registry.yaml, relationship-registry.yaml, unresolved-registry.yaml | IP-4 |
| Subset registries | B1 | capability-, decision-, invariant-, component-, system-registry.yaml | IP-4 |
| Legacy registry | B3 | entities/registry.yaml | IP-4 |
| Manifest | B2 | manifest.yaml | IP-4 |
| Markdown views | B5 | rendered/*.md | IP-4 |
| Graph export | B6 | architecture-graph.dot, architecture-graph.json | IP-6 |
| Contract validation | B7 | (validation report, no new file) | IP-5 |

**Total files produced:** 10 registry files + 1 manifest + N markdown files.

---

## 8. Kernel Contract

### 8.1 Contract Files

The kernel consumes exactly **4 files**:

1. `adrs/index/architecture-index.yaml` — entry point, metadata, registry paths
2. `adrs/index/entity-registry.yaml` — all entities (6 registry types)
3. `adrs/index/relationship-registry.yaml` — all relationships (12 types)
4. `adrs/index/unresolved-registry.yaml` — gaps and unresolved references

**There is no separate "kernel bundle."** The kernel loads these 4 standard
registry files. The compiler's B7 stage validates that registry output conforms
to the kernel contract schema — it does not produce a separate artifact.

### 8.2 Contract Invariants

| ID | Category | Guarantee |
|---|---|---|
| RI-1 | Referential integrity | Every relationship endpoint exists in entity registry |
| RI-2 | Referential integrity | Every entity relationship summary target exists in entity registry |
| RI-3 | Referential integrity | Every relationship summary entry has a corresponding RelationshipRecord |
| RI-4 | Referential integrity | Every unresolved source_entity_id exists in entity registry |
| RI-5 | Uniqueness | No duplicate entity IDs |
| RI-6 | Uniqueness | No duplicate relationship IDs |
| RI-7 | Uniqueness | No duplicate unresolved IDs |
| DET-1 | Determinism | Identical source → identical output (pinned timestamp) |
| DET-2 | Determinism | Entities sorted by (entity_type, id) |
| DET-3 | Determinism | Relationships sorted by relationship_id |
| DET-4 | Determinism | Unresolved sorted by id |
| COMP-1 | Completeness | Every validated ADR has a corresponding entity |
| COMP-2 | Completeness | Every relationship type in summaries appears in relationship registry |
| COMP-3 | Completeness | source_coverage in index matches actual source count |

### 8.3 Contract Versioning

The kernel contract is **pre-stable** until the compiler/kernel boundary is
implemented and intentionally frozen. Current contract line: **0.x**.

- Minor bump within 0.x may be additive or breaking while the contract remains
  internal and not yet opened as a stable external surface.
- `1.0` marks the first stable kernel contract.
- Minor bump within 1.x is additive only. Kernel ignores unknown fields.
- Major bump after 1.0 is for breaking changes and requires kernel update.

Schema 0.2 (planned) adds: `namespace`, `qualified_id`, `from_namespace`,
`to_namespace`, `cross_repository` fields for Super Graph preparation. This
becomes schema 1.1 only after the contract is declared stable.

Promotion checklist for `0.x` -> `1.0`:
1. The four contract files and their semantics are unchanged across at least one
   complete implementation cycle
2. `schema/kernel/` exists and matches the Pydantic contract models in CI
3. Generated registry payloads validate against the committed kernel schemas in CI
4. The metadata key baseline for all 6 registry entity types is enforced by validation
5. Sentinel placement policy, validation profiles, and remediation-ledger rules
   are implemented rather than plan-only
6. `sentinel_compliant` behavior is enforced consistently across compiler, CI,
   and kernel loading
7. At least one kernel consumer loads the contract using the committed schema
   surface rather than ad hoc assumptions
8. No open design blockers remain on the contract boundary
9. Promotion is recorded by ADR/governance decision, not inferred informally

### 8.4 Contract Validation Profiles

Contract validation is profile-based. The registry schema remains one contract
surface, but validation strictness varies by adoption context.

| Profile | Intended Use | Core Integrity | Metadata / Completeness |
|---|---|---|---|
| `greenfield` | Net-new compiler-native architectures | Strict | Enforce target metadata schemas and completeness expectations |
| `brownfield` | Legacy import into STE structure | Strict | Allow missing legacy metadata and partial completeness |
| `migration` | Transitional cleanup between brownfield and greenfield | Strict | Enforce selected target rules while tolerating known legacy gaps |

Reserved sentinel values may appear as field content in `brownfield` and
`migration` profiles only:
- `__LEGACY_UNSPECIFIED__`
- `__NOT_YET_MODELED__`
- `__MIGRATION_PLACEHOLDER__`

These are valid machine-recognized states, not free-form filler. They preserve
schema structure when the architectural intent is known but the source evidence
or modeled detail is still unavailable.

Sentinel placement policy:
- Allowed by default only in structurally required narrative content fields
- Forbidden in identifiers, relationship endpoints, type discriminators, path
  fields, authority/governance references, timestamps, and enumerated status
  fields

Allowed classes of fields:
- Human-readable summaries and descriptions
- Type-specific narrative metadata fields explicitly designated by schema
- Required explanatory sections that would otherwise be blank in brownfield or
  migration states

Forbidden classes of fields:
- `id`, `relationship_id`, `from_entity_id`, `to_entity_id`, `source_entity_id`
- `entity_type`, `relationship_type`, `schema_version`, `type`
- `source_ref`, `artifact_path`, `authority_ref`, `approved_by`, `approved_at`
- relationship summary target lists
- completeness status enums and other structural discriminators

The following invariants are mandatory in all profiles:
- RI-1 through RI-7
- DET-1 through DET-4
- Contract file presence and schema version validity

Profile-specific rules may vary:
- Per-entity metadata completeness
- Allowed completeness statuses and thresholds
- Legacy field omissions
- Warning-to-error promotion policy

Validation status is separate from content value. A bundle using reserved
sentinel values may be classified as `sentinel_compliant` under `brownfield`
or `migration`. `greenfield` rejects any sentinel occurrence. `compliant`
remains reserved for bundles that satisfy the contract without sentinel-backed
content.

Operational semantics:
- `CompilationResult.success = true` when the bundle satisfies the active
  profile, even if the outcome is `sentinel_compliant`
- `sentinel_compliant` is therefore a successful but incomplete contract state,
  not a failure state
- `non_compliant` sets `CompilationResult.success = false`
- Production kernel admission requires `compliant` unless an explicit policy
  override is configured
- Inspection-only tooling may load `sentinel_compliant` bundles

Sentinel remediation is monotonic:
- `sentinel` -> approved canonical content: allowed
- approved canonical content -> `sentinel`: forbidden

Once a sentinel-backed field is replaced by correct content approved through
canonical authority, that field may not regress to a sentinel state except via
an explicit governance override outside normal validation.

### 8.5 Remediation Ledger

Monotonic remediation is enforced through a separate canonical governance
artifact: the remediation ledger.

Proposed location:
- `adrs/governance/remediation-ledger.yaml`

Purpose:
- Preserve remediation state separately from architecture content
- Record authority-backed replacement of sentinel values
- Detect regression from approved content back to sentinel values

Minimal entry model:
- `entry_ref`: stable ledger entry ID
- `field_ref`: section-level by default, field-level when needed
- `state`: `sentinel` | `pending_approval` | `approved`
- `sentinel_value`: optional, one of the reserved sentinels
- `authority_ref`: canonical authority reference approving replacement
- `approved_by`: approver identity
- `approved_at`: timestamp
- `notes`: optional audit context

Reference format:
- Section-level default: `{artifact_id}#{section_path}`
- Field-level optional: `{artifact_id}#{section_path}.{field_name}`

Validation rules:
- Sentinel present and no approved ledger entry: allowed in `brownfield` and
  `migration`
- Sentinel present and approved ledger entry exists: `non_compliant`
- Non-sentinel replacing sentinel: allowed, but creates or updates a
  `pending_approval` ledger state until authority-backed approval is recorded
- Approved content changing materially without updated authority: profile-level
  warning or error

Approval workflow:
- Replacement content is **not** considered approved merely because it is
  non-sentinel
- Approval is staged, not immediate
- `authority_ref` is required to move a ledger entry from `pending_approval`
  to `approved`
- `authority_ref` must reference canonical authority, typically an ADR,
  invariant, or other governance-approved artifact that justifies the content
- `approved_by` records the approving actor; `approved_at` records when the
  approval occurred
- Without `authority_ref`, replacement content may remain usable in
  `brownfield` or `migration`, but it is not protected by the no-regression rule

Sentinel placement is evaluated against the field class:
- Section-level `field_ref` may point at a narrative section that is sentinel-backed
- Field-level `field_ref` is required when only a specific narrative subfield is
  sentinel-backed
- Ledger entries must never authorize sentinel use in forbidden structural fields

Temporary discovery folders may aid remediation, but they are not authoritative
and do not replace the remediation ledger or canonical artifacts.

### 8.6 Registry Metadata Schemas

The 0.x contract defines metadata expectations for the 6 registry entity types.
These schemas are part of the contract surface even though `metadata` remains a
dictionary in the serialized model.

#### ADR metadata
- Required:
  - `status: str`
  - `domains: list[str]`
  - `tags: list[str]`
- Optional:
  - none in 0.x
- Sentinel-capable:
  - none

#### Capability metadata
- Required:
  - `adr_id: str`
  - `domains: list[str]`
  - `implemented_by_components: list[str]`
  - `enabled_by_decisions: list[str]`
- Optional:
  - none in 0.x
- Sentinel-capable:
  - none

#### Decision metadata
- Required:
  - `adr_id: str`
  - `related_invariants: list[str]`
  - `enforces_invariants: list[str]`
  - `enables_capabilities: list[str]`
  - `governs_components: list[str]`
  - `supersedes: list[str]`
  - `refines: list[str]`
- Optional:
  - none in 0.x
- Sentinel-capable:
  - none

#### Invariant metadata
- Required:
  - `scope: str`
  - `statement: str`
  - `enforcement_level: str`
  - `declaration_mode: str`
  - `upheld_by_decisions: list[str]`
- Optional:
  - `adr_id: str`
  - `defined_in: str`
  - `enforced_by: list[str]`
- Sentinel-capable:
  - `statement`

#### System metadata
- Required:
  - `adr_id: str`
  - `implements_logical: list[str]`
  - `technologies: list[str]`
- Optional:
  - none in 0.x
- Sentinel-capable:
  - none

#### Component metadata
- Required:
  - `adr_id: str`
  - `technologies: list[str]`
  - `module_path: str`
  - `implements_capabilities: list[str]`
  - `implements_system: list[str]`
- Optional:
  - `legacy_component_id: str`
- Sentinel-capable:
  - `module_path` only in `brownfield` and `migration`

Rules:
- Required metadata keys must always be present, even in `brownfield`
- Sentinel-capable fields may use reserved sentinel values only where noted
- Non-narrative metadata fields remain sentinel-forbidden
- Adding or removing required keys is a contract change

### 8.7 Schema Authority

```
Compiler registry schema (full) ⊇ Kernel contract schema (subset)
```

The compiler owns the registry schema. The kernel contract specifies which
fields the kernel may rely on. The compiler may add fields freely (minor bump).

### 8.8 Contract Conformance Test Generator

Source of truth:
- Pydantic contract models in `src/adr_kit/models/architecture_discovery.py`

Derived artifacts:
- Committed kernel-facing JSON Schemas in `schema/kernel/`

Generation flow:
1. Load the four contract models:
   - `ArchitectureIndex`
   - `NormalizedEntityRegistry`
   - `RelationshipRegistry`
   - `UnresolvedRegistry`
2. Generate JSON Schema from each model using `model_json_schema()`
3. Normalize generated schema output for deterministic comparison:
   - stable key ordering
   - UTF-8 encoding
   - no non-deterministic titles or descriptions added outside the model source
4. Compare normalized generated schemas against committed files in
   `schema/kernel/`
5. Fail if generated and committed schemas differ

CI failure conditions:
- Pydantic-generated schema differs from committed kernel schema
- A committed kernel schema exists without a corresponding contract model
- A contract model exists without a committed kernel schema
- Registry output produced in tests does not validate against the committed
  kernel schemas

Rules:
- The generated schemas are derived state, not canonical authority
- Changes to contract models require regenerating the committed schemas
- Regenerating committed schemas may require a contract version decision
- CI must enforce this loop continuously

---

## 9. Kernel Architecture Model

### 9.1 Model Structure

```python
class KernelArchitectureModel:
    entities: EntityIndex       # O(1) lookup by id, type, domain, status
    relationships: RelIndex     # O(1) traversal by entity, type, direction
    unresolved: GapIndex        # O(1) lookup by id, source, severity
    metadata: ModelMetadata     # namespace, version, fingerprint
```

Read-only, immutable after construction. Loaded from the 4 contract files.

### 9.2 Query Surface Categories

| Category | Examples | Count |
|---|---|---|
| Entity queries | get_entity, get_system, get_component, get_capability, get_decision, get_invariant | 6 |
| Graph queries | trace_relationships, trace_decision, trace_capability, impact_of, dependencies_of, path_between | 6 |
| Collection queries | list_entities, list_by_type, list_by_domain, list_by_status, list_relationships | 5 |
| Gap queries | get_unresolved, unresolved_for, critical_gaps, coverage_gaps | 4 |
| Aggregate queries | architecture_summary, invariant_coverage, capability_realization, decision_impact_map | 4 |
| Introspection | model_metadata, entity_count, relationship_count, fingerprint, relationship_types, entity_types, domains | 7 |

All queries are pure reads. All graph traversals are bounded by `max_depth`
(default: 10). All list results are deterministically ordered.

---

## 10. Super Graph (Federation)

### 10.1 Identity Model

```
QualifiedEntityId = {namespace}:{bare_id}
```

- **Namespace:** from `PROJECT.yaml` → `architecture_namespace`. Format: `^[a-z][a-z0-9-]{1,63}$`.
- **Bare ID:** existing entity ID (e.g., `CAP-0001`). Format: `^[A-Z]+-`.
- **Separator:** colon (`:`). Deterministic parsing via character class heuristic (namespace starts lowercase, bare ID starts uppercase).
- **Bare IDs remain the default** in source artifacts. Qualified IDs only for cross-repo references.

### 10.2 Hierarchy

```
Repository (git repo)
  └── Scope (PROJECT.yaml boundary, INV-0019)
        └── Namespace (architecture_namespace, globally unique)
```

A repository may contain multiple scopes. Each scope has its own namespace.
Federation operates on namespaces (scopes), not repositories.

### 10.3 Preparation Phases

| Phase | Goal | Impact |
|---|---|---|
| SP-0 | Namespace awareness in IR (QualifiedEntityId) | Internal only |
| SP-1 | Qualified fields in registry output (schema 1.2) | Additive fields |
| SP-2 | Cross-repo reference syntax in ADR source | Author-facing change |
| SP-3 | Federation engine implementation | New subsystem |

### 10.4 Federation Engine Stages

| Stage | Name | Input | Output |
|---|---|---|---|
| FF-1 | Load and Validate | Federation manifest | Loaded registry bundles |
| FF-2 | Qualify Entity IDs | Loaded registries | All entities/rels carry qualified IDs |
| FF-3 | Merge Entity Graphs | Qualified entities | Global EntityIndex |
| FF-4 | Merge Relationship Graphs | Qualified relationships | Global RelIndex |
| FF-5 | Resolve Cross-Repo Refs | Unresolved + global index | Resolved cross-repo rels |
| FF-6 | Detect Conflicts | Global graph | Federation diagnostics |
| FF-7 | Validate Global Integrity | Complete super graph | Pass/fail |
| FF-8 | Build Super Graph Model | Validated data | SuperGraph instance |

---

## 11. Determinism Guarantees

| Guarantee | Mechanism |
|---|---|
| Entity ordering | Sorted by `(entity_type, id)` |
| Relationship ordering | Sorted by `relationship_id` |
| Unresolved ordering | Sorted by `id` |
| YAML serialization | `yaml.safe_dump(sort_keys=False)`, field-order preservation, UTF-8, LF line endings |
| Timestamp pinning | `--timestamp` flag overrides `generated_at` |
| Fingerprint | SHA-256 of JSON-serialized registry bundle |
| Reproducibility test | Bit-identical output for identical input with pinned timestamp |

---

## 12. Hard Constraints

1. **Python 3.11+** — project baseline, non-negotiable
2. **No new runtime dependencies** — pydantic, pyyaml, jsonschema, jinja2, click only
3. **Deterministic output** — bit-identical for identical input (pinned timestamp)
4. **Multi-scope support** — respects INV-0019 scope boundaries
5. **STE governance** — architectural changes traceable to ADRs (PRIME-1/PRIME-2)
6. **Backward compatibility** — existing CLI commands and output formats preserved
7. **Pydantic v2** — all models use Pydantic v2; IR containers are plain Python wrapping Pydantic models
