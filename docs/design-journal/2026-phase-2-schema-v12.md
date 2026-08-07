# Phase 2 schema v1.2 and normalized semantic foundation

Status: implementation authorized
Authority baseline: `0912c75e93a25a2f7f107ac0b09ffc87d58ab2c2`

## Problem

Phase 1 established a narrow installed-package facade without expanding the ADR
encoding or normalized semantic model. The repository already authors boundaries,
interaction contracts, component interfaces, implementation decisions, and name-keyed
physical topology, but only six entity types reach the normalized model and semantic
relationships retain only endpoint-based identity. External substrate, rule, and
evidence intent has no bounded authoring representation.

The roadmap requires every deferred contract to be reviewed separately. Roadmap text
does not itself authorize schema promotion, identity changes, or external authority
semantics, so Phase 2 needs an explicit accepted ADR before production implementation.

## Evidence considered

- ADR schema v1.0 is frozen and already contains the existing authoring shapes.
- Schema v1.1 is a provisional discovery, ledger, remediation, and attribution line;
  it is not the next ADR authoring encoding.
- `NormalizedArchitectureModel` reports `1.0`, while the generated normalized registries
  report provisional schema `1.1` and currently admit six entity types.
- Compiler IR already recognizes boundary, contract, interface, and
  implementation-decision entities, but the normalized projection does not.
- Existing relationship IDs are endpoint-derived and collapse identical semantic edges;
  changing them would break compatibility.
- Physical-system topology components and their references are name-keyed.
- ADR-L-0012 already requires explicit cross-repository qualification and
  provider-authoritative federation.

## Decisions locked by ADR-L-0018

1. Introduce provisional ADR authoring schema v1.2 as an additive line. Keep v1.0
   byte-frozen and keep v1.1 in its existing provisional role.
2. Keep local authoring references bare. Represent external references as bounded
   objects and derive their display qualification as `namespace:id`.
3. Add bind-only substrate, rule, and evidence-expectation records. They neither load
   nor execute external authority and never become observed evidence.
4. Promote exactly boundary, contract, interface, and implementation decision into
   the normalized model. Keep constraint, NFR, gap, and integration embedded.
5. Version the expanded `NormalizedArchitectureModel` as additive `1.1`.
6. Preserve `relationship_id` and add source-sensitive `assertion_id` using the exact
   canonical algorithm in ADR-L-0018. Do not implement GraphProjectionBundle or
   multi-assertion replacement semantics.
7. Add optional topology IDs and a deterministic, dry-run-first migrator that allocates
   first-free `TOPO-0001` style IDs in canonical component order and refuses ambiguous
   name rewrites.
8. Keep the relationship vocabulary closed. Phase 2 may emit only the six newly
   authorized verbs when an actual authored extraction path exists.

## Alternatives rejected

- Editing v1.0 in place: rejected because v1.0 is the stable encoding promise.
- Repurposing v1.1 as authoring vNext: rejected because it already identifies a
  provisional discovery/ledger family.
- Replacing historical relationship IDs: rejected because additive assertion identity
  is sufficient for Phase 2 and preserves consumers.
- Materializing external bindings as local entities: rejected because that absorbs
  authority owned by another namespace.
- Hash-derived topology IDs: rejected because a migration must produce reviewable,
  human-stable identifiers that persist in canonical source after allocation.
- Implementing GraphProjectionBundle: deferred to Phase 3.

## Authority and write boundary

Only ADR Kit tooling may regenerate authoring projections inside this repository.
External tools may inspect supported contracts read-only. Runtime or workspace-derived
state remains under workspace-root `.ste-workspace/` and is not a Phase 2 output.

## Implementation boundary

Phase 2 includes schema/model/parser support, normalized extraction, assertion identity,
binding projection, topology migration, repository queries, package data, installed-
wheel proof, deterministic goldens, documentation, and benchmark observation. It
excludes GraphProjectionBundle, graph persistence, runtime evidence, rule execution,
substrate ingestion, assembler behavior, admission, MCP, LLM behavior, and changes to
any sibling repository.
