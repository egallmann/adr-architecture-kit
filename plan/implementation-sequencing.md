# Implementation Sequencing

## Purpose

This document defines the correct build order for evolving adr-architecture-kit
from its current monolithic generator into the architecture compiler described
in the plan documents. It resolves the phase numbering divergence between the
evolution and roadmap documents (see convergence-review SI-1) and specifies
concrete entry/exit criteria for each step.

---

## 1. Sequencing Principles

1. **Golden files first.** Before any refactoring, capture current output as
   golden files. Every subsequent change must produce identical output until
   intentional format changes are introduced.

2. **No big-bang rewrite.** The compiler grows alongside the existing packages.
   Existing generators thin gradually as compiler subsystems take over.

3. **IR before passes.** The intermediate representation must exist before
   passes can be extracted — passes operate on the IR.

4. **Passes before driver.** The compiler driver orchestrates passes. Passes
   must exist before the driver can compose them.

5. **Contract before federation.** The kernel contract must be stable before
   federation extends it with qualified IDs.

6. **Each step must leave all tests green.** No step may break existing
   behavior. If a step changes output format, it must also update golden files.

---

## 2. Implementation Phases

### IP-0: Test Harness and Golden Files

**Prerequisite:** None (first step)
**Risk:** Low
**Breaking changes:** None

**Objective:** Establish the safety net that protects against output regression
during all subsequent refactoring.

**Deliverables:**
1. Golden-file test suite: snapshot all 10 registry files + manifest
2. Comparison uses semantic diff (parse YAML, compare dicts) to tolerate
   whitespace/ordering changes, with optional strict byte-identical mode
3. CI integration: golden-file tests run on every commit

**Exit criteria:**
- `pytest tests/golden/` passes
- Golden files checked into version control
- Any change to generator output is immediately detected

---

### IP-1: Diagnostics Model and Parse Cache

**Prerequisite:** IP-0
**Risk:** Low
**Breaking changes:** None

**Objective:** Introduce `DiagnosticLog` and a shared parse cache, replacing
print statements and redundant file reads.

**Deliverables:**
1. `compiler/diagnostics.py` — `DiagnosticLevel` (3 levels: ERROR, WARNING, INFO),
   `Diagnostic` dataclass, `DiagnosticLog` class with severity-ordinal sorting
2. `compiler/config.py` — `CompilationMode` enum, `CompilerConfig` dataclass
3. `compiler/frontend/parser.py` — cached ADR parser (key: path + mtime + size)
4. Refactor existing generators to use shared parse cache
5. Replace `print()` warnings with `DiagnosticLog.warning()`
6. Replace `ValueError` exceptions in `_validate_bundle()` with `DiagnosticLog.error()`

**Exit criteria:**
- All golden-file tests pass (output unchanged)
- `DiagnosticLog` used by all generators
- Parse cache eliminates redundant file reads
- No `print()` calls remain for warnings in generators

**Error code allocation:** E0xx/W0xx for frontend diagnostics.

---

### IP-2: Intermediate Representation

**Prerequisite:** IP-1
**Risk:** Medium (core structural change)
**Breaking changes:** None (internal refactoring)

**Objective:** Introduce `ArchModel` as the unified in-memory representation
with all 6 canonical fields.

**Deliverables:**
1. `compiler/ir/arch_model.py` — ArchModel dataclass (corpus, entities,
   relationships, unresolved, diagnostics, metadata)
2. `compiler/ir/entity_graph.py` — EntityGraph with type and ADR indexes
3. `compiler/ir/rel_graph.py` — RelGraph with adjacency and type indexes
4. `compiler/ir/unresolved_list.py` — UnresolvedList with source index
5. `compiler/ir/parsed_corpus.py` — ParsedCorpus container
6. Refactor `ArchitectureIndexGenerator` to build ArchModel from parsed ADRs,
   then extract entities into EntityGraph, build relationships into RelGraph,
   collect unresolved into UnresolvedList, and emit registries from IR

**Exit criteria:**
- ArchModel exists and is populated during generation
- `ArchitectureIndexGenerator` operates through IR
- All golden-file tests pass
- IR is unit-testable independently (synthetic ArchModel tests)
- EntityGraph.by_type() replaces _filtered() method

---

### IP-3: Pass Decomposition

**Prerequisite:** IP-2
**Risk:** Medium
**Breaking changes:** None (internal refactoring)

**Objective:** Extract compilation logic from `ArchitectureIndexGenerator` into
discrete, testable, composable passes.

**Deliverables:**
1. `compiler/passes/` — CompilationPass protocol (name, required, depends_on,
   halts_on_error, run method)
2. **M1:** `validate.py` — wraps ADRValidator + EntityValidator
3. **M2:** `validate_cross_refs.py` — wraps validate_cross_references()
4. **M3:** `extract_logical_entities.py` — from lines 313-390 of generator
5. **M4:** `extract_physical_entities.py` — from lines 439-484
6. **M5:** `resolve_invariant_canonical.py` — from lines 362-437
7. **M6:** `derive_relationships.py` — from lines 486-553
8. **M7:** `detect_unresolved.py` — from inline code in M6 area
9. **M8:** `score_completeness.py` — from _complete() helper
10. **M9:** `validate_bundle.py` — from _validate_bundle() (replaces it entirely)
11. `compiler/pass_manager.py` — PassManager with dependency resolution

**Extraction order within this phase:**
```
M9 first (simplest: direct port of _validate_bundle)
  → M8 (score_completeness: standalone, no complex dependencies)
  → M3 (extract_logical: largest, most entity types)
  → M4 (extract_physical: smaller, depends on M3 patterns)
  → M5 (invariant_canonical: complex, benefits from M3/M4 being stable)
  → M6 (derive_relationships: depends on M3+M4+M5 output)
  → M7 (detect_unresolved: tightly coupled with M6)
  → M1 (validate: wraps existing validator, low risk)
  → M2 (validate_cross_refs: wraps existing validator)
  → PassManager (orchestrator: registers and runs all passes)
```

**Exit criteria:**
- Each pass independently unit-testable with synthetic ArchModel
- PassManager runs all passes in correct dependency order
- Full pipeline through passes produces identical output (golden-file tests)
- `ArchitectureIndexGenerator.generate_from_directory()` is now:
  build corpus → create ArchModel → run passes → emit registries

---

### IP-4: Unified Compiler Driver and CLI

**Prerequisite:** IP-3
**Risk:** Low (composition of existing parts)
**Breaking changes:** None (new command; existing commands preserved)

**Objective:** Single `adr compile` entry point.

**Deliverables:**
1. `compiler/driver.py` — `ArchitectureCompiler.compile(scope, config) -> CompilationResult`
2. `CompilationResult` with 6 canonical fields
3. Backend emitters extracted from generators:
   - `compiler/backend/registry_emitter.py` (B1 + B3 + B4: 10 registry files)
   - `compiler/backend/manifest_emitter.py` (B2)
   - `compiler/backend/markdown_emitter.py` (B5)
4. CLI: `adr compile [--scope PATH] [--strict] [--lenient] [--emit LIST] [--timestamp ISO] [--dry-run] [--check]`
5. Existing commands as aliases:
   - `adr generate-architecture-index` → compiler with registries-only backend
   - `adr generate-manifest` → compiler with manifest-only backend
   - `adr validate` → compiler frontend + validate pass only

**Exit criteria:**
- `adr compile` produces all artifacts in one invocation
- Existing commands still work (backward compatible)
- Compilation report printed to stdout
- `--strict` halts on any ERROR
- `--check` exits non-zero on output drift (CI gate)
- Determinism test: two runs with pinned timestamp produce identical output

---

### IP-5: Kernel Contract Formalization

**Prerequisite:** IP-4
**Risk:** High (requires alignment with ste-kernel)
**Breaking changes:** None (additive)

**Objective:** Formalize the contract between compiler output and kernel
consumption. Validate compliance automatically.

**Deliverables:**
1. JSON Schema definitions for the 4 contract files, published in `schema/kernel/`
2. Contract ADR (new logical ADR documenting the contract decision, including
   pre-stable 0.x versioning and the transition criteria for 1.0)
3. `compiler/backend/contract_validator.py` (B7) — validates registry output
   against kernel contract JSON Schema
4. Validation profiles in contract validator: `greenfield`, `brownfield`,
   `migration`
5. Reserved sentinel handling in validator:
   `__LEGACY_UNSPECIFIED__`, `__NOT_YET_MODELED__`,
   `__MIGRATION_PLACEHOLDER__`, with `sentinel_compliant` outcome for allowed
   profiles
6. Remediation ledger:
   `adrs/governance/remediation-ledger.yaml`, with section-level field
   references by default and field-level references where needed
7. Monotonic remediation checks: once approved canonical content replaces a
   sentinel, validator rejects regression back to sentinel without explicit
   governance override
8. Approval workflow for remediation ledger:
   staged `sentinel` -> `pending_approval` -> `approved`, with canonical
   `authority_ref` required for `approved`
9. Sentinel placement policy:
   allowed only in narrative fields/sections; forbidden in identifiers,
   relationship structure, schema/type discriminators, and governance fields
10. `sentinel_compliant` semantics:
   successful compile under allowed profiles, CI-pass behavior tied to active
   profile, production kernel loads rejected by default, inspection-only loads
   allowed
11. Contract conformance test generator:
   Pydantic contract models are source of truth, `schema/kernel/` files are
   derived and compared deterministically in CI
12. Contract tests: validate compiler output against schema without ste-kernel present
13. CLI: `adr compile --validate-contract [--contract-profile PROFILE]` runs
   contract validation after emission
14. `0.x` -> `1.0` promotion gate:
   all contract boundary checks implemented, CI green, kernel consumer exercised,
   and governance sign-off recorded

**What B7 is NOT:** B7 does not produce a separate "kernel bundle" file. The
kernel loads the 4 existing registry files. B7 only validates contract compliance.

**Exit criteria:**
- JSON Schema published for all 4 contract files
- Contract validator runs as part of `adr compile` (optional, off by default)
- Brownfield profile accepts legacy-shaped imports that satisfy core integrity
- Greenfield profile enforces target metadata and completeness expectations
- Sentinel-backed sections are accepted only in brownfield/migration and are
  reported as `sentinel_compliant`
- Remediation ledger exists and validator uses it for no-regression checks
- Approved remediation requires staged ledger promotion with canonical
  `authority_ref`
- Sentinel usage is restricted to narrative fields and forbidden in structural
  and governance fields
- Contract conformance tests fail CI if Pydantic models and committed
  `schema/kernel/` files diverge
- `sentinel_compliant` is successful under allowed profiles but not admitted to
  production kernel loads by default
- `1.0` promotion requires explicit gate completion rather than elapsed time or
  informal confidence
- Approved canonical content cannot regress back to sentinel state without
  explicit override
- Contract tests pass in adr-kit CI
- Documentation for ste-kernel integration

---

### IP-6: Graph Export and Architecture Analysis

**Prerequisite:** IP-4 (parallel with IP-5)
**Risk:** Low
**Breaking changes:** None (additive)

**Objective:** Graph export and quality analysis passes.

**Deliverables:**
1. **M10:** `compiler/passes/lint.py` — architecture quality warnings
   (orphan entities, missing descriptions, naming violations, excessive fan-out)
2. **M11:** `compiler/passes/graph_analysis.py` — structural analysis
   (cycle detection, connected components, reachability, layer violations)
3. `compiler/backend/graph_emitter.py` (B6) — DOT and JSON-LD export
4. CLI extensions: `--lint`, `--analyze`, `--emit graph --format dot|json-ld`
5. `adr graph stats` command for quick entity/relationship summary

**Exit criteria:**
- Lint pass produces actionable warnings (tested with current repo)
- Graph analysis detects cycles and orphans
- DOT export renders in Graphviz
- M10 and M11 are optional (disabled by default, enabled via flags)

---

### IP-7: Super Graph Preparation (SP-0 + SP-1)

**Prerequisite:** IP-5
**Risk:** Medium
**Breaking changes:** Schema 1.2 (additive)

**Objective:** Make entities namespace-aware; emit qualified IDs in registries.

**Deliverables:**
1. `QualifiedEntityId` value type in compiler IR
2. Compiler attaches namespace to all entities at load time (from PROJECT.yaml)
3. IR uses `QualifiedEntityId` internally for all entity references
4. Registry output adds `namespace`, `qualified_id`, `from_namespace`,
   `to_namespace`, `cross_repository` fields
5. Schema version bumped to 1.2
6. Bare `id` fields preserved (backward compatible)

**Exit criteria:**
- Golden-file tests updated for schema 1.2 (new fields present)
- Old consumers (ignoring unknown fields) unaffected
- `architecture_namespace` validated as required in PROJECT.yaml
- All existing tests pass

---

### IP-8: Cross-Repo References and Federation (SP-2 + SP-3)

**Prerequisite:** IP-7
**Risk:** High
**Breaking changes:** ADR source schema change (reference fields accept qualified IDs)

**Objective:** Support cross-repo references in source ADRs and implement the
federation engine.

**Deliverables:**
1. Relax Pydantic patterns on reference fields to accept `namespace:bare_id`
2. Compiler detects cross-repo references and emits `cross_repository` unresolved records
3. Federation manifest schema and loader
4. Federation engine (FF-1 through FF-8)
5. Super Graph query extensions (namespace-scoped queries, cross-repo analysis)
6. CLI: `adr federate --manifest PATH`

**Exit criteria:**
- Cross-repo references parseable in ADR source
- Federation engine merges 2+ registries without collision
- Cross-repo unresolved records resolved at federation time
- Federation health report generated

---

### IP-9: Incremental Compilation (Future)

**Prerequisite:** IP-4
**Risk:** Medium
**Breaking changes:** None

**Objective:** Only recompile what changed since last compilation.

**Deliverables:**
1. Compilation cache (IR + source fingerprints)
2. Incremental pass execution (invalidate derived entities for changed sources)
3. Cache invalidation rules (schema change → full, source change → incremental)
4. `--clean` flag for forced full recompile

**Exit criteria:**
- Incremental compile ≥3x faster than full compile for single-file change
- Output identical to full compile (golden-file tests)

---

## 3. Dependency Graph

```
IP-0: Golden Files
  └──> IP-1: Diagnostics + Parse Cache
         └──> IP-2: Intermediate Representation
                └──> IP-3: Pass Decomposition
                       └──> IP-4: Compiler Driver + CLI
                              ├──> IP-5: Kernel Contract ──> IP-7: Super Graph Prep ──> IP-8: Federation
                              ├──> IP-6: Graph + Analysis (parallel with IP-5)
                              └──> IP-9: Incremental (future, parallel with IP-5/6)
```

### Critical Path

```
IP-0 → IP-1 → IP-2 → IP-3 → IP-4 → IP-5 → IP-7 → IP-8
```

IP-6 and IP-9 are off the critical path and can proceed in parallel once
IP-4 is complete.

---

## 4. Phase-to-Phase Mapping

This table reconciles the phase schemes across documents:

| Implementation Phase | Evolution Phase | Roadmap Phase | Super Graph Phase |
|---|---|---|---|
| IP-0 | — | Phase 0 | — |
| IP-1 | AP-1 (Foundation) | Phase 1 | — |
| IP-2 | AP-1 (Foundation) | Phase 2 | — |
| IP-3 | AP-1 (Foundation) | Phase 3 | — |
| IP-4 | AP-2 (Compiler) | Phase 4 | — |
| IP-5 | AP-3 (Kernel) | Phase 5 | — |
| IP-6 | AP-4 (Graph) | Phase 6 | — |
| IP-7 | AP-5 (Federation) | — | SP-0, SP-1 |
| IP-8 | AP-5 (Federation) | — | SP-2, SP-3 |
| IP-9 | — | Phase 7 | — |

---

## 5. Risk-Ordered Implementation Notes

### Highest Risk: IP-3 (Pass Decomposition)

The generator's `generate_from_directory()` method (~330 lines) contains 8+
interleaved stages. Decomposing into 9 required passes is the riskiest step.

**Mitigation:**
- Extract M9 first (simplest, direct port of _validate_bundle)
- Extract one pass at a time, running golden-file tests after each
- Use the extraction order specified in IP-3 deliverables
- Never extract two tightly-coupled passes simultaneously

### Second Highest Risk: IP-5 (Kernel Contract)

The contract is being designed without the kernel team's input. It may not
serve real kernel query patterns.

**Mitigation:**
- Define contract schema as JSON Schema (machine-verifiable)
- Implement contract validation in adr-kit CI
- Iterate with kernel team once they begin integration
- Keep contract surface minimal (4 files, 6 entity types)

### Third Highest Risk: IP-8 (Federation)

Cross-repo references and federation introduce a new subsystem with complex
merge semantics.

**Mitigation:**
- IP-7 (namespace awareness) is a prerequisite that de-risks IP-8
- Federation is a separate tool/subsystem, not embedded in the compiler
- Start with 2-repo federation testing before scaling

---

## 6. Module Layout Evolution

### After IP-4 (target layout):

```
src/adr_kit/
├── cli/main.py                          (existing + compile command)
├── compiler/
│   ├── driver.py                         (IP-4)
│   ├── config.py                         (IP-1)
│   ├── diagnostics.py                    (IP-1)
│   ├── pass_manager.py                   (IP-3)
│   ├── ir/
│   │   ├── arch_model.py                 (IP-2)
│   │   ├── entity_graph.py               (IP-2)
│   │   ├── rel_graph.py                  (IP-2)
│   │   ├── unresolved_list.py            (IP-2)
│   │   └── parsed_corpus.py              (IP-2)
│   ├── frontend/
│   │   ├── discovery.py                  (IP-2)
│   │   └── parser.py                     (IP-1)
│   ├── passes/
│   │   ├── validate.py                   (IP-3: M1)
│   │   ├── validate_cross_refs.py        (IP-3: M2)
│   │   ├── extract_logical_entities.py   (IP-3: M3)
│   │   ├── extract_physical_entities.py  (IP-3: M4)
│   │   ├── resolve_invariant_canonical.py (IP-3: M5)
│   │   ├── derive_relationships.py       (IP-3: M6)
│   │   ├── detect_unresolved.py          (IP-3: M7)
│   │   ├── score_completeness.py         (IP-3: M8)
│   │   ├── validate_bundle.py            (IP-3: M9)
│   │   ├── lint.py                       (IP-6: M10)
│   │   └── graph_analysis.py             (IP-6: M11)
│   └── backend/
│       ├── registry_emitter.py           (IP-4: B1+B3+B4)
│       ├── manifest_emitter.py           (IP-4: B2)
│       ├── markdown_emitter.py           (IP-4: B5)
│       ├── graph_emitter.py              (IP-6: B6)
│       └── contract_validator.py         (IP-5: B7)
├── generators/                           (existing — gradually delegates to compiler/)
├── validators/                           (existing — wrapped by compiler/passes/)
├── models/                               (existing — unchanged)
├── integrity/                            (existing — unchanged)
├── parser/                               (existing — wrapped by compiler/frontend/)
├── repository/                           (existing — reads compiler output)
├── scope/                                (existing — used by compiler/frontend/)
├── migrators/                            (existing — unchanged)
└── templates/                            (existing — used by backend/markdown_emitter)
```

### Migration strategy:

New `compiler/` package grows alongside existing packages. Existing generators
are gradually thinned to delegate to compiler subsystems. No big-bang rewrite.
Each IP step moves one responsibility from `generators/` into `compiler/`.
