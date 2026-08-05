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

## Phase 1 — narrow consumer-facade decision

Entry requires Phase 0 closure. Decide, through a new or amended ADR, whether a small
facade over `ArchitectureRepository` and `NormalizedArchitectureModel` is warranted.
This phase also owns migrating runtime version reporting to `importlib.metadata`.
No facade may expose `ArchModel`, compiler passes, raw ADR parsing, or file layout.

## Phase 2 — contract and identity promotion review

Entry requires a stable Phase 1 consumer boundary. Review provisional v1.1 schema,
assertion identity, entity expansion, topology identity, bindings, graph-bundle, ledger,
and attribution material individually. Promotion requires `ste-spec` authority where
the contract is cross-repository and explicit migration evidence; nothing is promoted
by roadmap text alone.

## Phase 3 — transactional authoring decision

Entry requires approved Phase 2 contracts. Evaluate bounded authoring transactions,
rollback, conflict handling, and deterministic regeneration as authoring concerns.
This phase must not absorb runtime extraction, rules execution, substrate, or admission.

## Phase 4 — Assembler boundary decision

Entry requires an approved authoring transaction and consumer facade. Decide whether an
Assembler belongs in this repository or elsewhere. Any implementation must use supported
interfaces only and may not couple to compiler IR, internal passes, or generated paths.

## Phase 5 — ecosystem integration review

Entry requires all earlier gates. Evaluate MCP, LLM-assisted flows, runtime/rules
integration, substrate, and admission only as explicit cross-repository architecture
decisions. Authority boundaries and fail-closed governance remain prerequisites; Phase 5
is not authorization to implement those concerns in the kit.
