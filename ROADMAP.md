# ADR Architecture Kit roadmap

The roadmap is gate-based. Passing a phase authorizes evaluation of the next phase; it
does not silently introduce that phase's capability. `ste-spec` remains normative for
shared schemas, `ste-runtime` for runtime observation/evidence, and `ste-kernel` for
admission.

## Phase 0 — production hardening

Gate: the existing `0.1.0` authoring/compiler package is releaseable without adding a
new SDK, schema, graph, normalized model, authoring transaction, Assembler, MCP,
runtime, rules, substrate, or admission capability.

- canonical imports and truthful coverage at 80% or greater;
- frozen Python/CLI compatibility inventory and version drift guard;
- Ruff, strict-mypy, and Black no-regression ratchets;
- supported source and retained-wheel execution on Python 3.11–3.14;
- one wheel and one sdist built once, manifested, tested, and promoted without rebuild;
- reproducibility, metadata, dependency-audit, installed-consumer, and benchmark gates;
- ADR-first authority, deterministic generated artifacts, and complete documentation.

## Phase 1 — narrow consumer facade (implemented)

Implemented after Phase 0 closure: the exact `adr_kit.api` facade covers validation,
restricted authoring compilation, `ArchitectureRepository`, and
`NormalizedArchitectureModel`. Runtime version reporting now uses installed
distribution metadata with a bounded direct-source fallback. The facade exposes no
`ArchModel`, compiler pass, raw parser, graph/IR emission, recursive runtime behavior,
or repository file-layout dependency. Source, editable, and retained-wheel consumers
and deterministic SDK benchmark sidecars close the gate. Package release remains a
separate decision.

## Phase 2 — schema v1.2 and normalized semantic foundation (implemented)

Implemented after ADR-L-0018 authorization: provisional additive ADR authoring schema
v1.2, normalized model 1.1 with four promoted entity families, source-sensitive
assertion IDs, bind-only substrate/rule/evidence contracts, stable topology identity
and migration, and ADR Kit-owned canonical collision repair. V1.0 remains frozen,
external authority remains external, and runtime state remains outside repositories.
GraphProjectionBundle and multi-source assertion replacement remain Phase 3 concerns.

## Phase 2.5 — canonical entity identity and promotion provider

Promote the closed v1.3 identity Design Journal through the ADR Kit promotion provider before schema/model v1.3 embodiment and corpus migration.

Keep canonical updated_at and general transactional authoring in Phase 3. Phase 3 consumes, and does not redefine, v1.3 entity identity.

Semantic implementation attribution (evidence schema v1.5, ADR-L-0020) is a
provisional evidence line on top of v1.3 identity. It does **not** open Phase 3
GraphProjectionBundle, multi-source assertion replacement, or transactional authoring.

## Phase 3 — graph bundle and transactional authoring decisions

Entry requires approved Phase 2 contracts. First evaluate GraphProjectionBundle,
multi-source assertion lifecycle, and snapshot replacement without redefining Phase 2
identity. Separately evaluate bounded authoring transactions, rollback, conflict
handling, and deterministic regeneration as authoring concerns. This phase must not
absorb runtime extraction, rules execution, substrate, or admission.

## Phase 4 — Assembler boundary decision

Entry requires an approved authoring transaction and consumer facade. Decide whether an
Assembler belongs in this repository or elsewhere. Any implementation must use supported
interfaces only and may not couple to compiler IR, internal passes, or generated paths.

## Phase 5 — ecosystem integration review

Entry requires all earlier gates. Evaluate MCP, LLM-assisted flows, runtime/rules
integration, substrate, and admission only as explicit cross-repository architecture
decisions. Authority boundaries and fail-closed governance remain prerequisites; Phase 5
is not authorization to implement those concerns in the kit.

## Post-release follow-up

- **Capture validated release protocol as reusable contributor skill**
  (`capture-release-protocol`): use the completed `0.3.0` execution trace as the
  evidence base for a repository-owned release-promotion skill. Skill implementation
  remains separate future work. Required evidence to consume includes the `0.3.0`
  PyPI README link-portability finding and resulting control (`INV-0083` /
  package-description portability as release qualification)—see
  [phase-0-controls.md](docs/production-hardening/phase-0-controls.md).
