# Implementation Guide

## Purpose

This file is the master instruction for AI-assisted implementation sessions.
Pass this file (or its path) to any AI tool to resume work at the correct
point in the build sequence.

**PLACEMENT NOTE FOR AI:** When the user is on a machine where implementation
can begin, move this file to the repository root as `CLAUDE.md`. This makes
it automatically loaded by Claude Code at session start. The command:

```bash
cp plan/IMPLEMENTATION-GUIDE.md CLAUDE.md
```

Until then, it lives in `/plan` as a design artifact.

---

## 1. Project Identity

**Repository:** `adr-architecture-kit` (renaming to `ste-architecture-compiler`)
**Package:** `src/adr_kit/` (renaming to `src/ste_compiler/`)
**CLI:** `adr` (command name stays — it's the user-facing verb)
**Branch:** `feature/kernel-integration`

The rename has not been executed yet. When it happens, update:
- `pyproject.toml` → name, package dir, entry point
- `PROJECT.yaml` → project.name, architecture_namespace, repository.url
- All internal imports
- CI workflow (`.github/workflows/adr-governance.yml`)
- README.md, SYSTEM-OVERVIEW.md

---

## 2. What Exists

### Compiler IR (built, not wired in)

```
src/adr_kit/compiler/
├── __init__.py
├── config.py                    — CompilationMode, CompilerConfig
├── diagnostics.py               — DiagnosticLevel, Diagnostic, DiagnosticLog
├── frontend/
│   └── __init__.py
└── ir/
    ├── __init__.py
    ├── arch_model.py            — ArchModel (6 fields), CompilationMeta
    ├── entity_graph.py          — IREntityType (14), IREntity, EntityGraph
    ├── identity.py              — QualifiedEntityId
    ├── parsed_corpus.py         — ParsedCorpus
    ├── rel_graph.py             — RelationshipType (12), IRRelationship, RelGraph
    └── unresolved_list.py       — IRUnresolved, UnresolvedList
```

**Status:** All modules import and pass smoke tests. Nothing calls them yet.
The existing `ArchitectureIndexGenerator` still operates on raw Pydantic
models and flat dicts.

### Existing Working System

```
src/adr_kit/
├── generators/architecture_index_generator.py  — the "implicit compiler" (632 lines)
├── models/architecture_discovery.py            — NormalizedEntity (6 types), RelationshipRecord (12 types)
├── models/entity_registry.py                   — legacy Entity model (v1.0)
├── parser/yaml_parser.py                       — YAML→Pydantic with JSON Schema validation
├── validators/                                 — ADR + entity validators
├── repository/                                 — registry loading + queries
├── scope/                                      — project scope resolution
└── cli/main.py                                 — all CLI commands
```

### Plan Documents (16 files in /plan)

Authoritative design references:
- `architecture-canonical-model.md` — single source of truth for types and structure
- `implementation-sequencing.md` — IP-0 through IP-9 build order
- `design-readiness-review.md` — readiness assessment, blockers, required ADRs
- `ste-subsystem-map.md` — ecosystem repo inventory and build order

---

## 3. Current Phase

**Active:** IP-0 and IP-1 are ready to implement. IP-2 IR module is started.

**Blockers for IP-2 completion:**
- ADR-REQUIRED-1 (IR Entity Model Design) — decision made (separate IR entity
  model, Option 2), needs formal ADR. The IR module already implements this
  decision (`IREntity` with 14 types, separate from `NormalizedEntity` with 6).
- ADR-REQUIRED-3 (Compiler Architecture Decision) — content is fully defined
  in plan docs, needs formal ADR.

**What to build next (in order):**

### Step A: Golden Files (IP-0)

Capture all 10 registry files + manifest as golden snapshots.
- Semantic diff (parse YAML, compare dicts) for tolerance
- Strict byte-identical mode with pinned timestamp
- CI integration: run on every commit

Exit criteria: `pytest tests/golden/` passes.

### Step B: IR→Registry Projection Function

Build `compiler/backend/projection.py`:
- `project_entity(entity: IREntity) -> Optional[NormalizedEntity]`
- `project_relationship(rel: IRRelationship) -> RelationshipRecord`
- `project_unresolved(item: IRUnresolved) -> UnresolvedRecord`
- `build_relationship_summary(entity_id: str, rel_graph: RelGraph) -> EntityRelationshipSummary`

This is the contract boundary between IR and registry output.
Test it by: build ArchModel from generator output, project back, compare
to golden files.

### Step C: Wire Diagnostics (IP-1)

Replace `print()` warnings with `DiagnosticLog.warning()`.
Replace `ValueError` in `_validate_bundle()` with `DiagnosticLog.error()`.
Introduce parse cache (key: path + mtime + size).

### Step D: Frontend — Build ArchModel from Parser (IP-2)

Create `compiler/frontend/builder.py`:
- Discover source files (reuse `_discover_source_files`)
- Parse into ParsedCorpus
- Extract entities into EntityGraph (all 14 types)
- Derive relationships into RelGraph
- Collect unresolved into UnresolvedList
- Assemble ArchModel

Exit criteria: ArchModel built from source, projected to registries,
matches golden files exactly.

### Step E: Pass Extraction (IP-3)

Extract in this order (from implementation-sequencing.md):
1. M9: validate_bundle (simplest, direct port)
2. M8: score_completeness
3. M3: extract_logical_entities
4. M4: extract_physical_entities
5. M5: resolve_invariant_canonical
6. M6: derive_relationships
7. M7: detect_unresolved
8. M1: validate (wraps existing validator)
9. M2: validate_cross_refs
10. PassManager (fixed linear ordering, not DAG)

Golden-file tests after each extraction.

### Step F: Compiler Driver (IP-4)

`compiler/driver.py` — `ArchitectureCompiler.compile()`.
Backend emitters extracted from generators.
CLI: `adr compile`.
Existing commands as aliases.

---

## 4. Sequencing Rules

These rules govern implementation order:

1. **Golden files first.** Before any refactoring, capture current output.
   Every subsequent change must produce identical output until intentional
   format changes are introduced.

2. **No big-bang rewrite.** The compiler grows alongside existing packages.
   Existing generators thin gradually as compiler subsystems take over.

3. **IR before passes.** The intermediate representation must exist before
   passes can be extracted.

4. **Projection before passes.** The IR→Registry projection must be tested
   against golden files before passes populate the IR.

5. **Passes before driver.** The compiler driver orchestrates passes. Passes
   must exist before the driver can compose them.

6. **Contract before federation.** The kernel contract must be stable before
   federation extends it with qualified IDs.

7. **Each step must leave all tests green.** No step may break existing
   behavior.

---

## 5. Authoritative Type References

When writing code, these are the canonical types. Do not invent new types
or deviate from these definitions.

**Entity types (14 IR, 6 registry):**
See `architecture-canonical-model.md` §2.

**Relationship types (12, closed set):**
declared_in, references, related_to, enforces, enabled_by, enables,
governs, implemented_by, embodied_in, supersedes, superseded_by, refines.

**ArchModel (6 fields):**
corpus, entities, relationships, unresolved, diagnostics, metadata.

**Compilation modes:**
NORMAL (continue, report), STRICT (halt on error), LENIENT (exclude invalid).

**Diagnostic levels (3):**
ERROR (ordinal 0), WARNING (ordinal 1), INFO (ordinal 2).

**Error code ranges:**
E0xx frontend, E1xx validation, E2xx extraction, E3xx resolution, E4xx backend.

---

## 6. Hard Constraints

1. Python 3.11+
2. No new runtime dependencies (pydantic, pyyaml, jsonschema, jinja2, click)
3. Deterministic output (bit-identical for identical input with pinned timestamp)
4. Multi-scope support (INV-0019 scope boundaries)
5. Pydantic v2 for all models; dataclasses for IR containers
6. Backward compatibility — existing CLI commands and output formats preserved
7. Tests must pass after every change

---

## 7. File Naming Conventions

- Plan documents: `plan/*.md` (design artifacts, not committed instructions)
- ADR source: `adrs/logical/ADR-{L,V}-XXXX-*.yaml`, `adrs/physical*/ADR-{P,PS,PC}-XXXX-*.yaml`
- Compiler modules: `src/adr_kit/compiler/**/*.py`
- Tests: `tests/test_*.py`
- Golden files: `tests/golden/*.yaml` (after IP-0)

---

## 8. Session Startup Checklist

When starting a new implementation session:

1. Read this file.
2. Check `git status` and `git log --oneline -5` for current state.
3. Run `pytest tests/ -q` to confirm green baseline.
4. Identify the next step from §3 above.
5. If a step is complete, move to the next one.
6. After completing work, run `pytest` to confirm green.
7. Do not commit unless asked.

---

## 9. Continuation Topics

These design items were intentionally left as follow-up work. Resolve them
before or during IP-5/IP-4 as noted.

### Contract + Validation

1. Implement the contract conformance test generator:
   - source of truth: `src/adr_kit/models/architecture_discovery.py`
   - derived artifacts: `schema/kernel/*.schema.json`
   - CI failure on model/schema divergence or payload/schema mismatch

### Compiler Semantics

7. Document canonical `CompilationMode` behavior fully:
   - `NORMAL`
   - `STRICT`
   - `LENIENT`
8. Finalize IR mutation rules:
   - `ParsedCorpus` immutability
   - `RelGraph.add()` responsibility for relationship summaries
   - post-M9 IR freeze behavior
9. Define the formal `BackendEmitter` protocol.
10. Map completeness-policy thresholds to `greenfield`, `brownfield`, and
    `migration` profiles.

### Remediation Ledger

Canonical location:
- `adrs/governance/remediation-ledger.yaml`

Current agreed model:
- Separate governance artifact, not embedded in ADR content
- Section-level `field_ref` by default, field-level when needed
- Staged approval workflow:
  - `sentinel` -> `pending_approval` -> `approved`
  - `authority_ref` required for `approved`
  - replacement content is not automatically approved
- Reserved sentinels:
  - `__LEGACY_UNSPECIFIED__`
  - `__NOT_YET_MODELED__`
  - `__MIGRATION_PLACEHOLDER__`
- Sentinel placement:
  - allowed only in narrative fields/sections
  - forbidden in IDs, relationship structure, schema/type discriminators,
    paths, and governance fields
- 0.x metadata baseline:
  - `adr`: `status`, `domains`, `tags`
  - `capability`: `adr_id`, `domains`, `implemented_by_components`,
    `enabled_by_decisions`
  - `decision`: `adr_id`, `related_invariants`, `enforces_invariants`,
    `enables_capabilities`, `governs_components`, `supersedes`, `refines`
  - `invariant`: `scope`, `statement`, `enforcement_level`,
    `declaration_mode`, `upheld_by_decisions`
  - `system`: `adr_id`, `implements_logical`, `technologies`
  - `component`: `adr_id`, `technologies`, `module_path`,
    `implements_capabilities`, `implements_system`
- Monotonic remediation:
  - `sentinel` -> approved canonical content: allowed
  - approved canonical content -> `sentinel`: forbidden unless explicit
    governance override
- Temporary discovery folders may help humans, but are not authoritative
- 1.0 promotion gate requires:
  - stable 4-file contract behavior
  - committed `schema/kernel/` with CI conformance checks
  - validator-enforced metadata/profile/sentinel rules
  - exercised kernel consumer
  - governance sign-off

Recommended next session order:
1. Refine the metadata baseline into validator-enforced schema checks.
2. Materialize `schema/kernel/` and the conformance test generator.
3. Write ADR-REQUIRED-2 and ADR-RECOMMENDED-5 using the settled rules.
4. Start implementing the validator/schema tooling behind the plan.
