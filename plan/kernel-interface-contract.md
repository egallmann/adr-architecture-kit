# Kernel Interface Contract

## Purpose

This document defines the stable contract between adr-architecture-kit (the compiler)
and the STE Kernel (the consumer). The kernel loads compiled architecture artifacts
without ever parsing ADR source files. This contract specifies what the compiler
guarantees, what the kernel may depend on, and how the interface evolves.

---

## 1. Contract Principles

**C1: The kernel never reads ADR source files.**
All architecture knowledge is accessed through compiled registry artifacts.
The kernel treats the compiler as a black box that produces a defined output.

**C2: The contract is the schema, not the implementation.**
The kernel depends on registry file structure and field semantics, never on
compiler internals. The compiler is free to restructure its pipeline as long
as registry output conforms to the contract schema.

**C3: Minimal surface area.**
The kernel requires the fewest registries that provide complete architecture
knowledge. Convenience subsets (capability-registry, decision-registry, etc.)
are compiler output for human ergonomics, not part of the kernel contract.

**C4: Versioned and backward-compatible.**
The contract schema carries a version. Minor versions add optional fields.
Major versions may remove or change field semantics. The kernel declares
the contract versions it supports.

**C5: Fingerprint-verifiable.**
The compiler produces a deterministic fingerprint of the registry bundle.
The kernel can detect stale or inconsistent registries by comparing fingerprints.

---

## 2. Current Registry Inventory

The compiler currently produces 10 output files:

| File | Type | Schema | Role |
|---|---|---|---|
| `architecture-index.yaml` | ArchitectureIndex | v1.1 | Bootstrap: points to all registries, summarizes compilation |
| `entity-registry.yaml` | NormalizedEntityRegistry | v1.1 | All entities (ADRs, capabilities, decisions, invariants, components, systems) |
| `relationship-registry.yaml` | RelationshipRegistry | v1.1 | All typed relationships with evidence and confidence |
| `unresolved-registry.yaml` | UnresolvedRegistry | v1.1 | Unresolved references, author-declared gaps |
| `capability-registry.yaml` | NormalizedEntityRegistry | v1.1 | Subset: entity_type=capability |
| `decision-registry.yaml` | NormalizedEntityRegistry | v1.1 | Subset: entity_type=decision |
| `invariant-registry.yaml` | NormalizedEntityRegistry | v1.1 | Subset: entity_type=invariant |
| `component-registry.yaml` | NormalizedEntityRegistry | v1.1 | Subset: entity_type=component |
| `system-registry.yaml` | NormalizedEntityRegistry | v1.1 | Subset: entity_type=system |
| `entities/registry.yaml` | EntityRegistry | v1.0 (legacy) | Legacy flat entity list |

### Which Registries Are Canonical?

The 5 subset registries (`capability-`, `decision-`, `invariant-`, `component-`,
`system-registry.yaml`) are strict filtered views of `entity-registry.yaml`.
The current `ArchitectureRepository._validate_subset_registry()` enforces that
every subset entity exists in the primary registry with matching canonical source.

The legacy `entities/registry.yaml` is a backward-compatibility artifact with
a reduced entity model (no provenance, no completeness, simplified relationships).

**Conclusion:** The canonical architecture model lives in exactly 3 files:

1. **`entity-registry.yaml`** — the entity graph (nodes)
2. **`relationship-registry.yaml`** — the relationship graph (edges)
3. **`unresolved-registry.yaml`** — known gaps and missing references

Plus one bootstrap file:

4. **`architecture-index.yaml`** — compilation metadata, registry paths, validation summary

---

## 3. Kernel Contract: Minimal Registry Set

### 3.1 Contract Registries

The kernel contract consists of exactly **4 files**:

```
adrs/index/
├── architecture-index.yaml      # REQUIRED: entry point
├── entity-registry.yaml         # REQUIRED: all architecture entities
├── relationship-registry.yaml   # REQUIRED: all architecture relationships
└── unresolved-registry.yaml     # REQUIRED: known gaps
```

The kernel loads `architecture-index.yaml` first, then follows the paths
within it to load the other three registries. This indirection allows the
compiler to relocate files without breaking the kernel (the index is the
stable entry point).

### 3.2 Non-Contract Artifacts (Compiler-Only Output)

These files are produced by the compiler but are **not part of the kernel contract**:

| File | Why Excluded |
|---|---|
| capability-registry.yaml | Derivable: `entity-registry.yaml` filtered by `entity_type=capability` |
| decision-registry.yaml | Derivable: same, filtered by `entity_type=decision` |
| invariant-registry.yaml | Derivable: same, filtered by `entity_type=invariant` |
| component-registry.yaml | Derivable: same, filtered by `entity_type=component` |
| system-registry.yaml | Derivable: same, filtered by `entity_type=system` |
| entities/registry.yaml | Legacy v1.0 format, deprecated |
| manifest.yaml | Compiler build metadata, not architecture knowledge |
| rendered/*.md | Human-readable views, not machine-consumable |

The kernel may choose to load subset registries for performance (avoiding
full entity registry scan), but it must not depend on their presence.
The contract guarantees only the 4 core files.

---

## 4. Contract Schema Definition

### 4.1 architecture-index.yaml

```yaml
# --- Kernel Contract Fields (MUST be present) ---
schema_version: "1.1"               # Contract version (semver minor)
type: "architecture_index"           # Discriminator
architecture_namespace: string       # Unique namespace for this architecture scope
generated_at: datetime               # ISO 8601 UTC, compilation timestamp
generator: string                    # Compiler identifier

# Registry paths (scope-relative, forward slashes)
entity_registry_path: string         # Path to entity-registry.yaml
relationship_registry_path: string   # Path to relationship-registry.yaml
unresolved_registry_path: string     # Path to unresolved-registry.yaml

# Compilation summary
validation_summary:
  hard_failures: int                 # 0 = clean compilation
  warnings: int
  unresolved_entries: int

source_coverage:
  logical_adrs: int
  physical_adrs: int
  physical_system_adrs: int
  physical_component_adrs: int
  standalone_invariants: int

# --- Non-Contract Fields (MAY be present, kernel MUST ignore unknown fields) ---
# decision_registry_path, capability_registry_path, etc.
```

**Kernel loading protocol:**
1. Load `architecture-index.yaml` from well-known path: `{scope_root}/adrs/index/architecture-index.yaml`
2. Verify `schema_version` is supported (kernel declares supported range)
3. Verify `type == "architecture_index"`
4. Check `validation_summary.hard_failures == 0` for kernel-managed production
   loads. Tooling may expose an explicit override for inspection-only loading.
5. Resolve registry paths relative to scope root
6. Load each contract registry

### 4.2 entity-registry.yaml

```yaml
schema_version: "1.1"
type: "normalized_entity_registry"
entities:
  - id: string                       # Unique entity ID (CAP-XXXX, DEC-XXXX, etc.)
    entity_type: string              # "adr" | "system" | "component" | "decision" | "capability" | "invariant"
    name: string                     # Human-readable name
    summary: string                  # First ~220 chars of context/description

    canonical_source:
      source_type: string            # "logical_adr" | "physical_adr" | "physical_system_adr" | "physical_component_adr" | "standalone_invariant"
      source_ref: string             # Canonical reference (e.g., "ADR-L-0001#CAP-0001")
      artifact_path: string          # Scope-relative path to source file

    source_refs:                     # Non-canonical mentions
      - source_type: string
        source_ref: string
        artifact_path: string
        mention_role: string         # "reference" | "definition"

    metadata: object                 # Type-specific metadata (varies by entity_type)

    relationships:                   # Denormalized relationship summary
      declared_in: [string]
      references: [string]
      related_to: [string]
      enforces: [string]
      enabled_by: [string]
      enables: [string]
      governs: [string]
      implemented_by: [string]
      embodied_in: [string]
      supersedes: [string]
      superseded_by: [string]
      refines: [string]

    completeness:
      status: string                 # "complete" | "partial" | "reference_only" | "conflicted"
      missing_fields: [string]

    provenance:
      source_type: string
      source_ref: string
      extraction_phase: string
      classification: string         # "explicit" | "derived" | "heuristic"
      generator: string
```

**Kernel contract guarantees:**
- Entity `id` is unique within the registry
- Every entity in a relationship summary target list exists in the registry
- Entity ordering: sorted by `(entity_type, id)` — deterministic
- `metadata` structure varies by `entity_type` but the kernel can access it as a generic dict

### 4.3 relationship-registry.yaml

```yaml
schema_version: "1.1"
type: "relationship_registry"
relationships:
  - relationship_id: string          # "{type}:{from}:{to}" — unique
    relationship_type: string        # One of the 12 defined types
    from_entity_id: string           # Must exist in entity registry
    to_entity_id: string             # Must exist in entity registry
    provenance_classification: string # "explicit" | "derived" | "heuristic"
    evidence: [string]               # Source references justifying the relationship
    canonical_source_ref: string     # Primary source reference
    confidence: float                # 0.0–1.0
    metadata: object                 # Additional context (may be empty)
```

**Kernel contract guarantees:**
- `relationship_id` is unique
- Both `from_entity_id` and `to_entity_id` exist in the entity registry
- Ordering: sorted by `relationship_id` — deterministic
- `relationship_type` is one of: `declared_in`, `references`, `related_to`, `enforces`,
  `enabled_by`, `enables`, `governs`, `implemented_by`, `embodied_in`, `supersedes`,
  `superseded_by`, `refines`

### 4.4 unresolved-registry.yaml

```yaml
schema_version: "1.1"
type: "unresolved_registry"
unresolved:
  - id: string                       # Unique gap ID
    gap_class: string                # "author_declared" | "generator_derived"
    gap_type: string                 # Specific gap classification
    source_entity_id: string         # Entity that has the unresolved reference
    related_entity_id: string?       # Target entity (if known but missing)
    expected_relationship: string?   # What relationship was expected
    severity: string                 # "critical" | "important" | "advisory"
    provenance: DiscoveryProvenance  # Same structure as entity provenance
    evidence: [string]
    suggested_resolution: string?    # Compiler suggestion (optional)
```

**Kernel contract guarantees:**
- `id` is unique
- `source_entity_id` exists in the entity registry
- Ordering: sorted by `id` — deterministic

---

## 5. Contract Invariants

These properties are guaranteed by the compiler and relied upon by the kernel:

### Referential Integrity

| Invariant | Description |
|---|---|
| **RI-1** | Every `from_entity_id` and `to_entity_id` in the relationship registry exists in the entity registry |
| **RI-2** | Every entity ID in an entity's `relationships` summary exists in the entity registry |
| **RI-3** | For every entry in an entity's relationship summary, a corresponding `RelationshipRecord` exists in the relationship registry |
| **RI-4** | Every `source_entity_id` in the unresolved registry exists in the entity registry |
| **RI-5** | No duplicate entity IDs in the entity registry |
| **RI-6** | No duplicate relationship IDs in the relationship registry |
| **RI-7** | No duplicate unresolved IDs in the unresolved registry |

### Determinism

| Invariant | Description |
|---|---|
| **DET-1** | Identical ADR source artifacts produce identical registry output (given pinned timestamp) |
| **DET-2** | Entity ordering is deterministic: `sorted by (entity_type, id)` |
| **DET-3** | Relationship ordering is deterministic: `sorted by relationship_id` |
| **DET-4** | Unresolved ordering is deterministic: `sorted by id` |

### Completeness

| Invariant | Description |
|---|---|
| **COMP-1** | Every ADR file that passed validation has a corresponding `entity_type=adr` entity |
| **COMP-2** | Every relationship type used in entity summaries appears in the relationship registry |
| **COMP-3** | `source_coverage` in the architecture index accurately reflects the source file count |

---

## 6. Contract Versioning

### Version Scheme

The contract is currently **pre-stable** and uses the `0.x` line until the
compiler/kernel boundary is intentionally frozen.

- **0.x minor** increment: additive or breaking changes allowed while the
  contract is not yet open as a stable external surface.
- **1.0**: first stable contract release.
- **1.x minor** increment: additive fields only. Kernel code that ignores
  unknown fields continues to work.
- **2.0+ major** increment: removed fields, changed field semantics, or changed
  registry file layout. Kernel must be updated.

While the contract remains in 0.x, the registry entity and relationship sets
remain intentionally constrained to the current contract surface: 6 registry
entity types and 12 relationship types. Extending those sets is a design
change, not a casual minor-version convenience.

Promotion checklist for `0.x` -> `1.0`:
1. The compiler emits the 4-file contract surface deterministically
2. `schema/kernel/` is materialized and CI-checked against Pydantic models
3. Contract validation profiles and remediation-ledger rules are implemented
4. Metadata requirements for all 6 registry entity types are validator-enforced
5. Production kernel loading is exercised against the committed contract schemas
6. No unresolved contract-surface design issues remain
7. Promotion is explicitly approved through architecture governance

### Compatibility Matrix

| Kernel Version | Supports Contract | Notes |
|---|---|---|
| kernel pre-release | 0.x | Co-evolves with compiler during integration |
| kernel 1.0 | 1.x | First stable compatibility line |
| kernel 2.0 | 2.0+ | Breaking change boundary |

### Version Negotiation Protocol

```python
# Kernel loading pseudocode
index = load_yaml("adrs/index/architecture-index.yaml")
contract_version = parse_semver(index["schema_version"])

if contract_version.major > SUPPORTED_MAJOR:
    raise IncompatibleContractError(
        f"Contract {contract_version} requires kernel upgrade"
    )
if contract_version.major < SUPPORTED_MAJOR:
    raise DeprecatedContractError(
        f"Contract {contract_version} no longer supported"
    )
# Minor version differences in 1.x: kernel ignores unknown fields
```

---

## 6A. Contract Validation Profiles

One contract schema supports multiple validation profiles. This prevents
brownfield imports from failing on target-state quality rules while still
enforcing the non-negotiable integrity invariants.

| Profile | Use Case | Reject On | Allow |
|---|---|---|---|
| `greenfield` | Net-new compiler-native architecture | Any contract violation, missing target metadata, unmet completeness requirements | Nothing beyond additive unknown fields |
| `brownfield` | Legacy import into STE structure | Referential integrity violations, duplicate IDs, invalid schema version, missing contract files | Missing legacy metadata, partial completeness, selected deprecated shapes |
| `migration` | Transitional hardening | Same core integrity violations as all profiles plus selected policy gates | Explicitly whitelisted brownfield gaps |

Reserved sentinel values may appear as field content in `brownfield` and
`migration` only:
- `__LEGACY_UNSPECIFIED__`
- `__NOT_YET_MODELED__`
- `__MIGRATION_PLACEHOLDER__`

These values are explicitly recognized by the validator. They are valid states
for structurally required sections when information could not be recovered or
has not yet been modeled.

Sentinel placement policy:
- Allowed only in structurally required narrative content fields
- Forbidden in structural, referential, and governance fields

Allowed by default:
- `summary`
- narrative description fields inside type-specific `metadata`
- required explanatory sections represented as narrative text

Forbidden:
- `id`, `relationship_id`, `from_entity_id`, `to_entity_id`, `source_entity_id`
- `entity_type`, `relationship_type`, `schema_version`, `type`
- `source_ref`, `artifact_path`, `authority_ref`, `approved_by`, `approved_at`
- relationship summary lists under `relationships`
- `completeness.status` and other enum/discriminator fields

If a field is not explicitly classified as narrative-capable, the validator
must treat sentinel usage as forbidden until the schema says otherwise.

Mandatory in all profiles:
- Contract file presence
- Supported schema version
- Entity, relationship, and unresolved uniqueness
- Relationship endpoint existence
- Unresolved source existence
- Deterministic ordering guarantees

Profile-configurable policy areas:
- Per-entity metadata schema strictness
- Completeness thresholds
- Legacy field omission tolerance
- Whether warnings are promoted to errors

Validation outcome is distinct from content value:
- `compliant`: no sentinel-backed content, all active profile rules satisfied
- `sentinel_compliant`: core contract satisfied, sentinel-backed content present
- `non_compliant`: contract violation

`greenfield` rejects sentinel values. `brownfield` and `migration` may accept
them, but they must remain queryable via completeness or missing-field tracking.

Operational semantics:
- `sentinel_compliant` is a valid validator outcome for `brownfield` and
  `migration`
- `sentinel_compliant` does not imply corrupt registries; referential integrity
  and deterministic guarantees still hold
- `sentinel_compliant` may pass CI when the selected contract profile allows it
- Production kernel loads reject `sentinel_compliant` by default
- Inspection-only or remediation tooling may load `sentinel_compliant`

Sentinel remediation is monotonic:
- `sentinel` -> approved canonical content: allowed
- approved canonical content -> `sentinel`: forbidden

The validator compares against the last approved canonical state when available.
Reintroduction of a sentinel after approved replacement is `non_compliant`
unless an explicit governance override path is invoked.

## 6B. Remediation Ledger

Monotonic remediation is enforced through a separate canonical governance
artifact rather than by embedding workflow state into ADR content.

Proposed location:
- `adrs/governance/remediation-ledger.yaml`

Minimal schema:

```yaml
schema_version: "0.1"
type: "remediation_ledger"
entries:
  - entry_ref: string
    field_ref: string
    state: "sentinel" | "pending_approval" | "approved"
    sentinel_value: string?
    authority_ref: string?
    approved_by: string?
    approved_at: datetime?
    notes: string?
```

Reference format:
- Section-level default: `{artifact_id}#{section_path}`
- Field-level optional: `{artifact_id}#{section_path}.{field_name}`

Validation behavior:
- If content is sentinel and no approved ledger entry exists, allow in
  `brownfield` and `migration`
- If content is sentinel and an approved ledger entry exists for the same
  `field_ref`, fail as regression
- If content replaces a sentinel with non-sentinel content, create or update a
  `pending_approval` entry until authority workflow marks the ledger entry
  `approved`
- If approved content changes materially, require fresh authority or fail per
  active profile

Approval requirements:
- Replacement content is not automatically approved
- Approval is staged: `sentinel` -> `pending_approval` -> `approved`
- `authority_ref` is required for `approved`
- `authority_ref` must point to canonical authority justifying the replacement
- `approved_by` and `approved_at` are required when state = `approved`
- Content protected by monotonic no-regression is content with a matching
  `approved` ledger entry, not merely any non-sentinel value
- Ledger entries may reference only fields or sections where sentinel usage is
  permitted by the placement policy

Temporary discovery folders may support human remediation work, but they are
not authoritative and are ignored by kernel consumption.

## 6C. Registry Metadata Schemas

The validator enforces the following metadata key sets for registry entities in
0.x. Unknown additive keys may be tolerated in 0.x during internal evolution,
but required keys below define the minimum contract.

| Entity Type | Required Keys | Optional Keys | Sentinel-Capable |
|---|---|---|---|
| `adr` | `status`, `domains`, `tags` | none | none |
| `capability` | `adr_id`, `domains`, `implemented_by_components`, `enabled_by_decisions` | none | none |
| `decision` | `adr_id`, `related_invariants`, `enforces_invariants`, `enables_capabilities`, `governs_components`, `supersedes`, `refines` | none | none |
| `invariant` | `scope`, `statement`, `enforcement_level`, `declaration_mode`, `upheld_by_decisions` | `adr_id`, `defined_in`, `enforced_by` | `statement` |
| `system` | `adr_id`, `implements_logical`, `technologies` | none | none |
| `component` | `adr_id`, `technologies`, `module_path`, `implements_capabilities`, `implements_system` | `legacy_component_id` | `module_path` in `brownfield` and `migration` only |

Rules:
- Required metadata keys must be present in every profile
- Sentinel-capable fields may use reserved sentinels only where explicitly listed
- Structural metadata keys remain sentinel-forbidden
- Contract tests should validate these key sets directly

The kernel consumes one contract. Validation profiles are a compiler-side and
CI-side concern, not separate runtime schemas.

## 6D. Contract Conformance Test Generator

The contract conformance test generator ensures that the committed kernel schema
surface stays aligned with the Pydantic contract models used by the compiler.

Source of truth:
- `src/adr_kit/models/architecture_discovery.py`

Committed derived artifacts:
- `schema/kernel/architecture-index.schema.json`
- `schema/kernel/entity-registry.schema.json`
- `schema/kernel/relationship-registry.schema.json`
- `schema/kernel/unresolved-registry.schema.json`

Generation and verification steps:
1. Generate JSON Schema from the four contract models with `model_json_schema()`
2. Normalize the generated JSON for deterministic comparison
3. Compare generated JSON against the committed files in `schema/kernel/`
4. Validate example or generated registry payloads against the committed schema
5. Fail CI on any divergence

CI must fail when:
- generated schema and committed schema differ
- a contract model is added or removed without corresponding schema updates
- generated registry payloads fail validation against committed kernel schema

This closes the loop:
- Pydantic contract models -> committed kernel schemas -> registry validation

---

## 7. Bundle Fingerprint

The compiler produces a deterministic SHA-256 fingerprint of the contract registries.
The kernel uses this to detect stale or inconsistent state.

### Fingerprint Computation

```python
# Current implementation in registry_loader.py
def fingerprint_payload(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(serialized.encode("utf-8")).hexdigest()

# Fingerprint includes all contract registries
fingerprint = fingerprint_payload({
    "mode": "normalized",
    "architecture_index": model_payload(index),
    "entity_registry": model_payload(entity_registry),
    "relationship_registry": model_payload(relationship_registry),
    "unresolved_registry": model_payload(unresolved_registry),
})
```

### Kernel Usage

```python
# Cache invalidation
stored_fingerprint = kernel_state.get("architecture_fingerprint")
current_fingerprint = repository.fingerprint()
if stored_fingerprint != current_fingerprint:
    kernel.reload_architecture_model(repository)
    kernel_state.set("architecture_fingerprint", current_fingerprint)
```

---

## 8. Entry Point Discovery

The kernel discovers the architecture index through a fixed convention:

```
{scope_root}/adrs/index/architecture-index.yaml
```

The scope root is determined by:
1. Explicit configuration in kernel settings
2. `PROJECT.yaml` presence (if kernel co-locates with the architecture project)
3. `ste.config.json` pointer (cross-repository reference)

The kernel does not use `ProjectScopeResolver` from adr-kit. It uses its own
configuration to find the scope root. This avoids coupling the kernel to the
compiler's scope resolution logic.

---

## 9. Error Handling

### What the Kernel Should Reject

| Condition | Response |
|---|---|
| `architecture-index.yaml` missing | Error: "Architecture not compiled — run `adr compile`" |
| `schema_version` unsupported | Error: "Contract version {v} not supported by this kernel" |
| `validation_summary.hard_failures > 0` | Reject by default for production kernel loads; tooling may offer explicit inspection override |
| Contract validation outcome = `sentinel_compliant` | Reject by default for production kernel loads; allow inspection-only or remediation-mode loading |
| Referenced registry file missing | Error: "Registry file not found: {path}" |
| Entity/relationship referential integrity violated | Error: "Corrupt registry bundle — recompile" |
| Fingerprint mismatch (if checking) | Warning: "Registry bundle changed since last load" |

### What the Kernel Should Tolerate

| Condition | Response |
|---|---|
| Unknown fields in any registry | Ignore (forward compatibility in 1.x) |
| `unresolved_entries > 0` | Normal — architecture may have known gaps |
| Subset registries missing | Normal — derive from entity registry |

---

## 10. Risks and Constraints

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Contract schema designed without kernel implementation | Contract may not serve real kernel query patterns | Iterative refinement: kernel team proposes changes based on actual usage |
| Entity `metadata` is untyped dict | Kernel can't rely on metadata structure without entity_type-specific knowledge | Define per-entity metadata schemas plus greenfield/brownfield/migration validation profiles and reserved sentinel values |
| Relationship registry grows large | Loading all relationships may be slow for large architectures | Kernel builds in-memory index on first load; future: relationship partitioning |
| Subset registries removed from contract but kernel perf needs them | Kernel must scan full entity registry | Kernel builds type index on load (same as `EntityGraph.by_type()`) |
| Schema version drift between compiler and kernel | Silent incompatibility | CI job that validates compiler output against kernel's expected schema |

### Constraints

1. **YAML format** — registries are YAML (not JSON, not binary). The kernel must parse YAML.
2. **File-based** — registries are files on disk. No network protocol, no database.
3. **Scope-local** — each scope has its own registry bundle. Cross-scope queries require loading multiple bundles.
4. **Read-only** — the kernel never writes to registry files. Only the compiler writes.
5. **No partial loading** — the kernel loads all 4 contract files or none. No streaming.
