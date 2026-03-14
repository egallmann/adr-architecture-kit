# Architecture Compiler Stages

## Purpose

This document specifies each compilation stage in detail — inputs, outputs,
algorithms, error semantics, and mapping to current implementation.

---

## Stage Reference

```
FRONTEND                    MIDDLE-END                           BACKEND
┌─────────────────┐   ┌─────────────────────────────────┐   ┌──────────────────┐
│ F1: Discover     │   │ M1: Validate Business Rules      │   │ B1: Registry     │
│ F2: Parse        │──>│ M2: Validate Cross-References    │──>│ B2: Manifest     │
│ F3: Schema Gate  │   │ M3: Extract Logical Entities     │   │ B3: Legacy       │
│ F4: Scope Resolve│   │ M4: Extract Physical Entities    │   │ B4: Index        │
└─────────────────┘   │ M5: Resolve Invariant Canonical  │   │ B5: Markdown     │
                       │ M6: Derive Relationships         │   │ B6: Graph        │
                       │ M7: Detect Unresolved            │   │ B7: Kernel       │
                       │ M8: Score Completeness           │   └──────────────────┘
                       │ M9: Validate Bundle Consistency  │
                       │ M10: Lint (optional)             │
                       │ M11: Graph Analysis (optional)   │
                       └─────────────────────────────────┘
```

---

## Frontend Stages

### F1: Source Discovery

**Purpose:** Enumerate all compilable source artifacts within scope.

**Input:**
- `scope: ProjectScope` — project root, ADR directory, namespace

**Output:**
```python
@dataclass
class SourceManifest:
    logical_files: list[Path]           # adrs/logical/*.yaml
    physical_files: list[Path]          # adrs/physical/*.yaml (legacy)
    physical_system_files: list[Path]   # adrs/physical-system/*.yaml
    physical_component_files: list[Path] # adrs/physical-component/*.yaml
    invariant_files: list[Path]         # adrs/invariants/*.yaml
    project_metadata: Optional[Path]    # PROJECT.yaml
```

**Algorithm:**
1. Resolve scope via `ProjectScopeResolver` (current `scope/resolver.py`)
2. Walk each known subdirectory of `scope.adr_dir`
3. Classify files by directory name
4. Sort deterministically by resolved path
5. Deduplicate physical files (current code handles symlink/overlap dedup)

**Error semantics:**
- Missing ADR directory → ERROR: "No ADR directory found at {path}"
- Missing PROJECT.yaml → ERROR: "No PROJECT.yaml found (required for namespace)"
- Empty directories → INFO: "No {type} ADRs found"

**Current implementation:** `ArchitectureIndexGenerator._discover_source_files()` (lines 66-75)
and `ADRValidator._discover_adr_files()` (lines 63-78). These are duplicated — the compiler
should have exactly one discovery implementation.

---

### F2: Source Parsing

**Purpose:** Parse each source file into a typed AST (Pydantic model).

**Input:** `SourceManifest`

**Output:**
```python
@dataclass
class ParsedCorpus:
    logical_adrs: list[tuple[LogicalADR, SourceLocation]]
    physical_adrs: list[tuple[PhysicalADR, SourceLocation]]
    system_adrs: list[tuple[PhysicalSystemADR, SourceLocation]]
    component_adrs: list[tuple[PhysicalComponentADR, SourceLocation]]
    invariants: list[tuple[StandaloneInvariant, SourceLocation]]
    metadata: Optional[ProjectMetadata]
    parse_errors: list[Diagnostic]   # files that failed parsing

@dataclass
class SourceLocation:
    path: Path          # absolute path
    relative: str       # scope-relative path (forward slashes)
    mtime: float        # for cache invalidation
```

**Algorithm:**
1. For each file in SourceManifest:
   a. Read YAML (`yaml.safe_load`)
   b. Determine type from `adr_type` frontmatter field
   c. Validate against JSON Schema (structural mode for first pass)
   d. Construct Pydantic model
   e. On success: add to corpus
   f. On failure: emit Diagnostic, exclude from corpus
2. Physical subtype discrimination by frontmatter `adr_type`, not directory

**Error semantics:**
- YAML syntax error → ERROR diagnostic, file skipped
- Schema validation failure → ERROR diagnostic, file skipped
- Pydantic validation failure → ERROR diagnostic, file skipped
- In `--strict` mode: any parse error halts pipeline

**Current implementation:** `ADRParser.parse_adr()` with type discrimination,
`parse_logical_adr()`, `parse_invariant()`. Called independently by each generator.

---

### F3: Schema Gate

**Purpose:** Full schema validation (complete mode) on parsed models.

**Note:** This is integrated into F2 but described separately because the
current system has two validation modes (`structural` and `complete`).
The compiler should use `structural` during initial parse (F2) to build
the corpus, then optionally run `complete` validation as part of M1.

**Current implementation:** `ADRParser.validate_against_schema()` with
`mode` parameter.

---

### F4: Scope Resolution

**Purpose:** Resolve project boundaries, namespace, and multi-scope hierarchy.

**Input:** Working directory or explicit `--scope` path

**Output:** `ProjectScope` (root, adr_dir, name, namespace)

**Algorithm (priority order per INV-0015):**
1. Explicit `--scope` parameter
2. `ste.config.json` in current or ancestor directory
3. `PROJECT.yaml` in current or ancestor directory
4. Standard markers (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `.git`)
5. Current working directory

**Boundary:** Never traverse above system boundaries (`Users/`, `home/`, `Documents/`)

**Current implementation:** `scope/resolver.py` — fully functional, no changes needed.

---

## Middle-End Stages (Compilation Passes)

### Pass Architecture

```python
class CompilationPass(Protocol):
    """Interface for all compilation passes."""
    name: str
    required: bool                    # False = optional pass
    depends_on: tuple[str, ...]       # passes that must run first
    halts_on_error: bool              # True = errors stop pipeline

    def run(self, model: ArchModel, config: CompilerConfig) -> None:
        """Mutate model in place. Append diagnostics to model.diagnostics."""
        ...
```

All passes operate on the shared `ArchModel` (see internal-model document).

---

### M1: Validate Business Rules

**Purpose:** Validate each ADR against type-specific business rules.

**Depends on:** (none — first pass)

**Input:** `model.corpus` (parsed ADRs)

**Output:** Diagnostics appended to `model.diagnostics`

**Rules (from current `ADRValidator`):**

| Rule | Applies To | Severity | Description |
|---|---|---|---|
| INV-0002 | LogicalADR | WARNING | Must not contain implementation keywords in context |
| completeness | LogicalADR | WARNING | ADR-L should have decisions |
| INV-0005 | LogicalADR | ERROR | No duplicate invariant IDs |
| INV-0003 | PhysicalADR | ERROR | Must reference ≥1 logical ADR |
| completeness | PhysicalADR | WARNING | Should have component specifications |
| physical_system_logical_ref | PhysicalSystemADR | ERROR | Must reference ≥1 logical ADR |
| completeness | PhysicalSystemADR | WARNING | Should define system boundaries |
| physical_component_system_ref | PhysicalComponentADR | ERROR | Must reference ≥1 system ADR |
| physical_component_logical_ref | PhysicalComponentADR | ERROR | Must reference ≥1 logical ADR |
| completeness | PhysicalComponentADR | ERROR | Must have ≥1 component specification |
| ai_generation_readiness | ComponentSpec | ERROR | Must have interfaces, impl_identifiers, generation_context, impl_requirements |
| granularity | PhysicalComponentADR | WARNING | >10 components needs justification |

**Error semantics in strict mode:**
- Any ERROR → halt pipeline
- In lenient mode → exclude offending ADR from corpus, continue

**Current implementation:** `validators/adr_validator.py` methods `_validate_logical_adr()`,
`_validate_physical_adr()`, `_validate_physical_system_adr()`, `_validate_physical_component_adr()`

---

### M2: Validate Cross-References

**Purpose:** Verify all inter-ADR references resolve to existing artifacts.

**Depends on:** M1

**Input:** `model.corpus`

**Output:** Diagnostics

**Checks:**
1. Physical ADR `implements_logical` → logical ADR must exist in corpus
2. Physical-System ADR `implements_logical` → logical ADR must exist
3. Physical-System ADR `references_components` → component ADR must exist
4. Physical-Component ADR `implements_system` → system ADR must exist
5. Physical-Component ADR `implements_logical` → logical ADR must exist
6. All ADRs `related_adrs` → target ADR must exist (WARNING if not)
7. No duplicate ADR IDs across all types (INV-0005)

**Error semantics:**
- Missing `implements_logical` target → ERROR
- Missing `related_adrs` target → WARNING
- Duplicate IDs → ERROR

**Current implementation:** `ADRValidator.validate_cross_references()` (lines 463-592)

---

### M3: Extract Logical Entities

**Purpose:** Walk each logical ADR's sections and create entity nodes in the EntityGraph.

**Depends on:** M2

**Input:** `model.corpus.logical_adrs`

**Output:** Entities added to `model.entities`

**Extraction rules:**

| Source Section | Entity Type | ID Pattern | Fields Extracted |
|---|---|---|---|
| ADR itself | adr | ADR-L-XXXX | title, context (→summary), status, domains, tags |
| .capabilities[] | capability | CAP-XXXX | name, description (→summary), implemented_by_components, enabled_by_decisions |
| .decisions[] | decision | DEC-XXXX | summary (→name), rationale (→summary), related_invariants, enforces_invariants, enables_capabilities, governs_components, supersedes, refines |
| .invariants[] | invariant | INV-XXXX | statement (→summary), scope, enforcement_level, upheld_by_decisions |
| .constraints[] | constraint | CONST-XXXX | description, type, rationale |
| .boundaries[] | boundary | BOUND-XXXX | name, description, rationale |
| .nfrs[] | nfr | NFR-XXXX | category, requirement, acceptance_criteria |
| .contracts[] | contract | CONTRACT-XXXX | parties, protocol, guarantees |
| .gaps[] | gap | GAP-XXXX | question, impact, blocking |

**Note:** Currently, only ADR, capability, decision, and invariant entities are
extracted into the normalized registry. Constraints, boundaries, NFRs, contracts,
and gaps are either omitted or handled as unresolved records. The compiler should
extract all entity types into the IR for completeness, even if not all are emitted
to registries in the initial backend.

**Provenance:** Each entity records:
- `source_type`: "logical_adr"
- `source_ref`: "{adr_id}" or "{adr_id}#{entity_id}"
- `extraction_phase`: "extract_logical"
- `classification`: "explicit"

**Current implementation:** Lines 313-390 of `generate_from_directory()`

---

### M4: Extract Physical Entities

**Purpose:** Extract system and component entities from physical ADRs.

**Depends on:** M3

**Input:** `model.corpus.system_adrs`, `model.corpus.component_adrs`, `model.corpus.physical_adrs`

**Output:** Entities added to `model.entities`

**Extraction rules:**

| Source | Entity Type | ID Pattern | Fields Extracted |
|---|---|---|---|
| PhysicalSystemADR | adr | ADR-PS-XXXX | title, context, status, domains |
| PhysicalSystemADR | system | SYS-XXXX (derived) | title (→name), context (→summary), implements_logical, technologies |
| PhysicalComponentADR | adr | ADR-PC-XXXX | title, context, status, domains |
| PhysicalComponentADR.component_specs[] | component | COMP-XXXX | name, responsibilities (→summary), technologies, module_path, implements_capabilities |
| PhysicalADR (legacy) | adr | ADR-P-XXXX | title, context, status, domains |

**System ID derivation:** `SYS-{XXXX}` from `ADR-PS-{XXXX}` (current `_system_entity_id()`)

**Component ID:** Uses `component_id` field if present (e.g., `COMP-SCHEMA-VALIDATOR`),
falls back to `id` field (e.g., `COMP-0001`).

**Current implementation:** Lines 439-484 of `generate_from_directory()`

---

### M5: Resolve Invariant Canonical Sources

**Purpose:** Invariants can be defined in multiple locations (standalone file + ADR-local).
This pass determines the canonical source for each invariant ID and merges mentions.

**Depends on:** M3 (invariants collected from logical ADRs)

**Input:** Invariant entities from M3 + `model.corpus.invariants` (standalone files)

**Output:** Deduplicated invariant entities with canonical source assignment

**Algorithm:**
1. Collect all invariant mentions: `{inv_id: [(payload, artifact, source_ref), ...]}`
2. Classify each mention as `standalone` (source_ref == inv_id) or `local` (ADR-embedded)
3. Priority: standalone canonical > first local mention
4. If duplicate standalone definitions → ERROR
5. If multiple local definitions with no standalone → use first, ERROR if >1
6. For non-canonical mentions: add as `source_refs` with `mention_role: "reference"`

**Current implementation:** Lines 362-437 of `generate_from_directory()`. This is one
of the most complex stages and benefits significantly from being an explicit pass.

---

### M6: Derive Relationships

**Purpose:** Build the relationship graph from entity cross-references.

**Depends on:** M4, M5 (all entities must be extracted first)

**Input:** `model.entities` + parsed ADR cross-reference fields

**Output:** Relationships added to `model.relationships`

**Derivation rules:**

| Source | Relationship | From | To | Classification |
|---|---|---|---|---|
| Any non-ADR entity | declared_in | entity | parent ADR | explicit |
| LogicalADR.related_adrs | references | ADR | target ADR | explicit |
| Capability.implemented_by_components | implemented_by | capability | component | explicit |
| Decision.enforces_invariants + related_invariants | enforces | decision | invariant | explicit |
| Decision.enables_capabilities | enables | decision | capability | explicit |
| Decision.enables_capabilities (inverse) | enabled_by | capability | decision | derived |
| Decision.governs_components | governs | decision | component | explicit |
| Decision.supersedes | supersedes | decision | target | explicit |
| Decision.supersedes (inverse) | superseded_by | target | decision | derived |
| Decision.refines | refines | decision | target | explicit |
| StandaloneInvariant.enforced_by | enforces | invariant | target | explicit |
| ComponentSpec.implements_capabilities | implemented_by | capability | component | explicit |
| ComponentSpec → implements_system | embodied_in | component | system | explicit |
| ComponentSpec.dependencies | related_to | component | dep | derived (0.8 confidence) |
| PhysicalSystemADR.references_components | related_to | system ADR | component ADR | derived (0.8 confidence) |

**Relationship identity:** `"{type}:{from_id}:{to_id}"` — no duplicates.

**Evidence:** Each relationship records the source reference(s) that justify it.

**Confidence:**
- Explicit relationships: 1.0
- Derived (inverse): 1.0
- Heuristic (dependencies, references_components): 0.8

**Current implementation:** Lines 486-553 of `generate_from_directory()`

---

### M7: Detect Unresolved References

**Purpose:** Identify entity references that don't resolve to known entities.

**Depends on:** M6

**Input:** Relationship derivation failures (targets not in entity graph)

**Output:** Unresolved records added to `model.unresolved`

**Unresolved types:**

| Gap ID Pattern | Gap Class | Gap Type | Source | Severity |
|---|---|---|---|---|
| UGAP-{adr}-{gap} | author_declared | author_declared_*_gap | LogicalADR.gaps | blocking → important, else advisory |
| GAP-IMPL-{cap}-{comp} | generator_derived | capability_without_implementing_component | Capability.implemented_by_components target missing | important |
| GAP-INV-{dec}-{inv} | generator_derived | unresolved_reference | Decision.enforces/related_invariants target missing | important |
| GAP-CAP-{dec}-{cap} | generator_derived | unresolved_reference | Decision.enables_capabilities target missing | important |
| GAP-MISSING-CAP-{comp}-{cap} | generator_derived | unresolved_reference | ComponentSpec.implements_capabilities target missing | important |
| GAP-MISSING-SYS-{comp}-{sys} | generator_derived | component_without_system | ComponentSpec → system target missing | important |

**Author-declared gap subtyping:**
- context contains "classification: deferred" → `author_declared_deferred_gap`
- context contains "classification: resolved" → `author_declared_resolved_gap`
- otherwise → `author_declared_real_gap`

**Current implementation:** Inline within relationship derivation (lines 500-546, 379-390)

---

### M8: Score Completeness

**Purpose:** Evaluate each entity's field coverage and assign completeness status.

**Depends on:** M6

**Input:** `model.entities`

**Output:** Completeness metadata updated on each entity

**Scoring algorithm:**
```
For each entity:
  missing = []
  if not entity.summary: missing.append("summary")
  if not entity.source_refs: missing.append("source_refs")
  # Type-specific checks:
  if entity is capability and not entity.metadata.implemented_by_components:
      missing.append("implemented_by_components")
  if entity is decision and not entity.metadata.enables_capabilities:
      missing.append("enables_capabilities")
  ...
  status = "complete" if not missing
           else "partial" if entity has canonical source
           else "reference_only"
```

**Current implementation:** `_complete()` helper (lines 99-101) — currently only
checks if missing_fields list is empty. The compiler should implement richer scoring.

---

### M9: Validate Bundle Consistency

**Purpose:** Post-compilation consistency check — verify no dangling references
in the relationship graph or unresolved registry.

**Depends on:** M8

**Input:** `model.entities`, `model.relationships`, `model.unresolved`

**Output:** Pass/fail diagnostics

**Checks:**
1. Every relationship's `from_entity_id` and `to_entity_id` exist in entity graph
2. Every entity's relationship summary entries have corresponding relationship records
3. Every unresolved record's `source_entity_id` exists in entity graph
4. No duplicate unresolved IDs
5. Entity relationship summary and relationship registry are mutually consistent

**Error semantics:** Failures here indicate a compiler bug (internal consistency
violation). These should be ERROR level and always halt.

**Current implementation:** `_validate_bundle()` (lines 190-229) — raises ValueError.

---

### M10: Lint (Optional)

**Purpose:** Architecture quality analysis — soft warnings that don't affect
compilation output but flag potential issues.

**Depends on:** M9

**Input:** Complete `ArchModel`

**Output:** Diagnostics (WARNING/INFO level only)

**Lint rules (proposed):**

| Rule | Description |
|---|---|
| orphan-entity | Entity with no relationships (not declared_in any ADR) |
| sink-entity | Entity with only inbound relationships (nothing depends on it and it depends on nothing) |
| missing-description | Entity with empty or very short summary (<20 chars) |
| naming-convention | Entity ID doesn't match expected pattern for its type |
| excessive-fan-out | Entity with >15 outbound relationships |
| undocumented-domain | ADR domain not appearing in any other ADR |
| stale-supersedes | Superseded entity still has active dependents |

**Current implementation:** None — this is a new pass.

---

### M11: Graph Analysis (Optional)

**Purpose:** Structural analysis of the architecture graph.

**Depends on:** M9

**Input:** `model.entities`, `model.relationships`

**Output:** Diagnostics + graph metadata attached to `model.metadata`

**Analyses (proposed):**

| Analysis | Output |
|---|---|
| Cycle detection | WARNING for each cycle in non-supersedes relationships |
| Connected components | INFO: number of disconnected subgraphs |
| Critical path | Entities that, if removed, would disconnect the graph |
| Layer violation | Physical entities referencing logical internals (not via public entities) |
| Coverage gaps | Capabilities with no implementing component |
| Decision coverage | Invariants with no enforcing decision |

**Current implementation:** None — this is a new pass.

---

## Backend Stages

### B1: Registry Emission

**Purpose:** Serialize entity graph and relationship graph into registry YAML files.

**Input:** Finalized `ArchModel`

**Output:**
| File | Content |
|---|---|
| architecture-index.yaml | Top-level index with paths, validation summary, coverage |
| entity-registry.yaml | All normalized entities (sorted by type, then ID) |
| relationship-registry.yaml | All relationships (sorted by relationship_id) |
| unresolved-registry.yaml | All unresolved records (sorted by ID) |
| capability-registry.yaml | Entities filtered to type=capability |
| decision-registry.yaml | Entities filtered to type=decision |
| invariant-registry.yaml | Entities filtered to type=invariant |
| component-registry.yaml | Entities filtered to type=component |
| system-registry.yaml | Entities filtered to type=system |

**Serialization guarantees:**
- `yaml.safe_dump(sort_keys=False)` — key order matches model field order
- Entities sorted by `(entity_type, id)`
- Relationships sorted by `relationship_id`
- Unresolved sorted by `id`
- All strings UTF-8, line endings LF
- No anchors or aliases in output

**Current implementation:** `save_bundle()` + `render_yaml()` (lines 598-632)

---

### B2: Manifest Emission

**Purpose:** Produce manifest.yaml with source statistics and integrity.

**Input:** `model.corpus` + `model.entities` (for entity counts)

**Output:** `adrs/manifest.yaml`

**Current implementation:** `ManifestGenerator` — currently independent.
In compiler model, shares corpus and entity counts from IR.

---

### B3: Legacy Registry Emission

**Purpose:** Produce v1.0 entity-registry.yaml for backward compatibility.

**Input:** `model.entities`

**Output:** `adrs/entities/registry.yaml`

**Mapping:** NormalizedEntity → Entity (v1.0). Only capability, component,
decision, invariant types are mapped. System/ADR types excluded.

**Current implementation:** `_legacy_entity()` method (lines 231-269)

---

### B4: Architecture Index Emission

**Purpose:** Produce the top-level architecture-index.yaml.

**Input:** Full `ArchModel`

**Output:** `adrs/index/architecture-index.yaml`

**Content:** Registry paths, validation summary, source coverage, namespace, timestamp.

---

### B5: Markdown Emission

**Purpose:** Render human-readable markdown views of ADRs.

**Input:** `model.corpus`

**Output:** `adrs/rendered/*.md`

**Current implementation:** `generators/views/markdown.py` with Jinja2 templates.

---

### B6: Graph Emission (Future)

**Purpose:** Export architecture graph in standard formats.

**Input:** `model.entities`, `model.relationships`

**Output:**
- `architecture-graph.dot` (Graphviz)
- `architecture-graph.json` (JSON-LD or adjacency list)

---

### B7: Kernel Bundle Emission (Future)

**Purpose:** Produce kernel-consumable artifact bundle.

**Input:** Full `ArchModel`

**Output:** Kernel contract bundle (format TBD with ste-kernel team)

---

## Pass Dependency Graph

```
F1: Discover
  └──> F2: Parse
         └──> F4: Scope Resolve
                └──> IR Construction
                       └──> M1: Validate Business Rules
                              └──> M2: Validate Cross-References
                                     └──> M3: Extract Logical Entities
                                            └──> M4: Extract Physical Entities
                                                   └──> M5: Resolve Invariant Canonical
                                                          └──> M6: Derive Relationships
                                                                 ├──> M7: Detect Unresolved
                                                                 └──> M8: Score Completeness
                                                                        └──> M9: Validate Bundle
                                                                               ├──> M10: Lint
                                                                               └──> M11: Graph Analysis
                                                                                      └──> Backend Emitters
```

All passes are strictly sequential. No parallelism in the middle-end
(determinism requires fixed ordering). Backend emitters are independent
and could theoretically run in parallel, but the performance benefit
is negligible for YAML serialization.

---

## Risks and Constraints

### Risks

| Risk | Stage | Mitigation |
|---|---|---|
| Entity extraction logic diverges from current output during decomposition | M3, M4 | Golden-file tests for every extraction stage |
| Invariant canonical resolution edge cases in multi-source scenarios | M5 | Exhaustive unit tests with all combinations (standalone-only, local-only, both, duplicates) |
| Relationship derivation ordering affects duplicate suppression | M6 | Current code uses dict-based dedup; preserve exact same ordering in pass |
| Bundle validation is too strict (false positives) | M9 | Keep exact same checks as current `_validate_bundle()` initially |
| Optional passes (M10, M11) add noise without actionable guidance | M10, M11 | Ship disabled by default; enable via `--lint` / `--analyze` flags |

### Constraints

1. Each pass must be independently unit-testable with a synthetic `ArchModel`
2. No pass may read source files directly — only access `model.corpus`
3. Pass output must be deterministic given identical input
4. Pass ordering is strictly sequential (no parallel passes)
5. All diagnostics use structured `Diagnostic` objects (no prints, no exceptions for expected conditions)
