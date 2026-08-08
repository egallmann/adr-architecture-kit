# Phase 2 closeout

Date: 2026-08-07  
Branch: `feature/adr-kit-schema-v12`  
Base: `0912c75e93a25a2f7f107ac0b09ffc87d58ab2c2` (`origin/develop`)  
Package version: `0.1.0`

## Outcome

Phase 2 is complete locally. The branch adds the provisional ADR authoring
schema v1.2 line and the normalized semantic foundation authorized by
ADR-L-0018. It does not implement GraphProjectionBundle, runtime evidence,
rule execution, substrate ingestion, admission, or transactional authoring.

## Authority

ADR-L-0018 was accepted and then amended to record canonical identity repair.
It introduced decisions DEC-0083 through DEC-0088, invariants INV-0077 through
INV-0082, and capabilities CAP-0048 through CAP-0052. The associated design
journal records the implementation boundary and the repository-write invariant.

Collision repair is owned exclusively by ADR Kit. The implemented workflow
selects a deterministic keeper, allocates above each prefix's historical
high-water mark, never reuses retired or remapped IDs, uses occurrence-scoped
resolution for ambiguity, rewrites typed references, validates, regenerates,
and is checked by CI/pre-push controls. The live canonical corpus repair changed
30 colliding occurrences and one uniquely resolvable reference.

## Schema and compatibility

- Canonical v1.2 authoring inventory: eight JSON Schema documents plus README.
- Byte-identical packaged resources: `adr_kit.schema.v1_2`.
- V1.0 remained frozen and its compatibility fixtures stayed green.
- V1.1 retained its provisional discovery/ledger role.
- Parser negotiation supports `1.0`, `1.1`, and `1.2`; unsupported future
  authoring versions fail closed.
- Python SDK contract version and exact 17-symbol `adr_kit.api` inventory remain
  unchanged.

## Normalized semantic model

Normalized-model contract version advanced additively from `1.0` to `1.1`.
The projectable vocabulary expanded from six to ten types:

```text
Before: adr, system, component, decision, capability, invariant
After:  adr, system, component, decision, capability, invariant,
        boundary, contract, interface, implementation_decision
```

Constraint, NFR, gap, integration, and data flow remain unpromoted. Existing
repository query semantics were retained; four explicit promoted-type queries
were added. The canonical corpus compiles to 285 entities, 373 relationships,
and 9 unresolved records.

## Relationship identity and bindings

Historical endpoint-based `relationship_id` remains unchanged. Additive
`assertion_id` is `asrt-` plus SHA-256 of the compact UTF-8 JSON array:

```text
[relationship_type, from_entity_id, to_entity_id,
 canonical_source_ref, source_pointer_or_empty]
```

New emitted verbs are `provides_interface`, `composed_of`, `binds_substrate`,
`binds_rule`, and `expects_evidence`. The authorized but unused
`consumes_interface` verb was not added because Phase 2 has no authored
extraction path for it.

Substrate bindings, rule bindings, and evidence expectations validate, parse,
project, serialize, and round trip deterministically. External entities are
qualified as `namespace:id` but are not materialized locally. Rule bodies are
not executed or ingested, and evidence expectations remain distinct from
observed evidence.

## Topology identity

V1.2 accepts optional `TOPO-*` component IDs and transitional name or ID
references when they resolve exactly once. `adr migrate-topology-ids` is
dry-run-first, preserves existing IDs, allocates first-free sequential IDs in
canonical order, rewrites relationship and data-flow references, validates the
complete candidate, and writes atomically only with `--apply`. Duplicate IDs,
ambiguous names, and dangling references block without guessed output. Applied
output is idempotent.

## Generated artifacts

ADR Kit tooling regenerated:

- repository registries and architecture graph;
- deterministic golden registries;
- CLI behavior/surface compatibility snapshots;
- repository-owned kernel-compatibility schemas;
- ADR rendered projections and manifest after authority changes.

Changes are explained by promoted entity vocabulary, additive relationship
assertion fields, canonical ID repairs, and the new CLI commands. No projection
was edited by hand.

## Verification

- Focused Phase 2 schema/entity/assertion/binding/topology tests: green.
- Full suite: 433 passed, 6 skipped.
- Coverage suite: 433 passed, 6 skipped; 85.90% total (80% required).
- Compatibility snapshots: Python, CLI surface, and CLI behavior green.
- Version consistency: every surface reports `0.1.0`.
- Quality ratchets: Ruff 58, strict mypy 337, Black 95; no regression.
- Governance: complete validation and cross-references green; two existing
  advisory logical/implementation warnings, zero errors.
- Contract validation: greenfield and zero-budget brownfield profiles compliant.
- Canonical allocation/collision check: green.
- Local pre-push suite: 60 passed; generated integrity and attribution compliant.
- Dependency audit: no known vulnerabilities.
- Distribution: wheel and sdist built; `twine check` passed.
- Installed-wheel consumer: v1.0 and v1.2 compile/validation, package schema
  resources, promoted queries, bindings, assertion IDs, SDK containment, and
  topology migrator entrypoint all passed outside the source tree.
- Fixed-epoch reproducibility: independent wheel and normalized-sdist hashes
  matched. Wheel SHA-256:
  `3D828A3D212CDCE77CF33D45245E5A947016095DAB8CE3C55E46BD6131B937DD`;
  sdist SHA-256:
  `7B70121243E7AF5CA8665F53D768DBC9EC4663400F8421A3689E78F53D75E208`.
- Phase 2 benchmark: deterministic across repeats; timings and semantic digest
  are recorded in `phase-2-benchmark-baseline.md`.

## Repository-write boundary

Only ADR Kit source, scripts, CLI, generators, and repository-local test tooling
wrote files inside `adr-architecture-kit`. No sibling repository or runtime tool
wrote or regenerated repository content. The external attribution check read its
evidence from workspace-root `.ste-workspace/`; build, benchmark, and
reproducibility scratch output also remained outside the repository.

## Deferred

GraphProjectionBundle, multi-source assertion replacement and stale-source
removal, snapshot identity, graph persistence/query, runtime extraction and
evidence ingestion, rule execution, substrate semantic loading, assembler and
kernel admission, transactional authoring, MCP/LLM integration, and all sibling
repository changes remain deferred.

## Release recommendation

Phase 2 satisfies the planned `0.3.x` capability tier and is ready for a separate
`0.3.0` release decision. The established policy keeps version changes in a
release-only step, so this branch intentionally remains at `0.1.0`. No push,
merge, tag, publication, or release was performed.
