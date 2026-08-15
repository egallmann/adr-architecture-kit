# Universal UUIDv7 — Human Gate Review

Checkpoint: `20a79f7ed848ea304142e6d06c66d63f28d857b0`  
Branch: `feature/uuidv7-identity-schema-taxonomy`  
Package version: `0.4.1`

This is a bounded review packet for the final pre-migration gates. It is not a
schema authority and it does not approve any gate. The accepted authorities are
ADR-L-0019, ADR-L-0021, and ADR-L-0022; the implementation detail is recorded in
`2026-universal-uuidv7-entity-identity.md`.

## Gate 1 — Alias collision dispositions

The scan covered canonical ADR YAML, generated manifests/registries, migration
and allocation ledgers, retirement history, tests, and fixtures. No accepted
authority establishes an incumbent for any of these five collisions. The
current architecture graph contains no direct legacy-alias node or edge for
these child records; generated manifests and unresolved registries are
projections, not ownership authority. No canonical created/admitted timestamp
is present on the child records, so chronology cannot resolve ownership.

The mechanically supported default is: a human selects one claimant to retain
the legacy alias, fresh monotonic aliases are assigned to every other claimant,
legacy alias/path/pointer facts remain migration provenance, and UUID identity
never changes because an alias changes. Candidate values are collision-free
review proposals only; they are not allocated.

### `CONST-0001`

| Claimant | Context | Authority evidence |
|---|---|---|
| `adrs/logical/ADR-L-0001-ste-compliant-adr-system.yaml#/constraints/0` | ADR-L-0001, “STE-Compliant Machine-Verifiable Architecture Decision Record System”; technical constraint: YAML embeds Markdown rather than using Markdown frontmatter, for deterministic structure and validation. | No CONST entry in the canonical ID allocation/remap ledgers establishes ownership. |
| `adrs/logical/ADR-L-0007-deterministic-documentation-projection.yaml#/constraints/0` | ADR-L-0007, “Deterministic Documentation Projection”; technical constraint: human documentation must be projected from structured authority rather than maintained independently. | No CONST entry in the canonical ID allocation/remap ledgers establishes ownership. |

Graph participation: neither child alias is a graph node/edge alias at this
checkpoint. Generated manifest/projection occurrences are not ownership proof.

Candidate final aliases: `CONST-0025`, `CONST-0026` (one or both may be used
only after the human selects an incumbent and approves the exact mapping).

Decision: [ ] APPROVE / [ ] MODIFY  
Human decision requested: select the claimant, if any, that retains
`CONST-0001`; approve the replacement alias for the other claimant.

### `GAP-0001`

| Claimant | Context | Authority evidence |
|---|---|---|
| `adrs/logical/ADR-L-0004-adr-to-code-traceability-via-decorators.yaml#/gaps/0` | ADR-L-0004; decorator library gap is classified closed because `adr_kit.decorators` exists, while UUID claim APIs are staged under ADR-L-0020/ADR-PC-0007. | No GAP allocation/remap or retirement authority selects this claimant. |
| `adrs/physical/ADR-P-0004-prompt-translator-implementation.yaml#/gaps/0` | ADR-P-0004; unresolved question about the base prompt-template hierarchy, medium impact, non-blocking. | No GAP allocation/remap or retirement authority selects this claimant. |

Graph participation: no direct legacy-alias graph node/edge; unresolved registry
entries are generated projections.

Candidate final aliases: `GAP-0020`, `GAP-0021`.  
Decision: [ ] APPROVE / [ ] MODIFY  
Human decision requested: select the claimant, if any, that retains
`GAP-0001`; approve the replacement alias for the other claimant.

### `GAP-0002`

| Claimant | Context | Authority evidence |
|---|---|---|
| `adrs/logical/ADR-L-0004-adr-to-code-traceability-via-decorators.yaml#/gaps/1` | ADR-L-0004; broader extractor coverage for downstream implementation attribution remains staged. | No GAP allocation/remap or retirement authority selects this claimant. |
| `adrs/logical/ADR-L-0005-adr-to-prompt-translation.yaml#/gaps/0` | ADR-L-0005; production prompt-template set is not implemented in this repository. | No GAP allocation/remap or retirement authority selects this claimant. |
| `adrs/physical/ADR-P-0004-prompt-translator-implementation.yaml#/gaps/1` | ADR-P-0004; agent-specific prompt-formatting rules remain to be standardized, medium impact, non-blocking. | No GAP allocation/remap or retirement authority selects this claimant. |

Graph participation: no direct legacy-alias graph node/edge; unresolved registry
entries are generated projections.

Candidate final aliases: `GAP-0022`, `GAP-0023`, `GAP-0024`.  
Decision: [ ] APPROVE / [ ] MODIFY  
Human decision requested: select the claimant, if any, that retains
`GAP-0002`; approve replacement aliases for the other two claimants.

### `GAP-0003`

| Claimant | Context | Authority evidence |
|---|---|---|
| `adrs/logical/ADR-L-0004-adr-to-code-traceability-via-decorators.yaml#/gaps/2` | ADR-L-0004; whole-repository onboarding has not started, with selective high-authority dogfood already in place. | No GAP allocation/remap or retirement authority selects this claimant. |
| `adrs/logical/ADR-L-0005-adr-to-prompt-translation.yaml#/gaps/1` | ADR-L-0005; per-agent formatters remain deferred while core prompt generation can proceed. | No GAP allocation/remap or retirement authority selects this claimant. |
| `adrs/physical/ADR-P-0004-prompt-translator-implementation.yaml#/gaps/2` | ADR-P-0004; integration of generated prompts with validation remains a high-impact, non-blocking question. | No GAP allocation/remap or retirement authority selects this claimant. |

Graph participation: no direct legacy-alias graph node/edge; unresolved registry
entries are generated projections.

Candidate final aliases: `GAP-0025`, `GAP-0026`, `GAP-0027`.  
Decision: [ ] APPROVE / [ ] MODIFY  
Human decision requested: select the claimant, if any, that retains
`GAP-0003`; approve replacement aliases for the other two claimants.

### `GAP-0004`

| Claimant | Context | Authority evidence |
|---|---|---|
| `adrs/logical/ADR-L-0004-adr-to-code-traceability-via-decorators.yaml#/gaps/3` | ADR-L-0004; ste-rules-library activation for intent-attribution enforcement remains staged. | No GAP allocation/remap or retirement authority selects this claimant. |
| `adrs/logical/ADR-L-0005-adr-to-prompt-translation.yaml#/gaps/2` | ADR-L-0005; CI/CD automation for implementation is deferred downstream workflow work. | No GAP allocation/remap or retirement authority selects this claimant. |

Graph participation: no direct legacy-alias graph node/edge; unresolved registry
entries are generated projections.

Candidate final aliases: `GAP-0028`, `GAP-0029`.  
Decision: [ ] APPROVE / [ ] MODIFY  
Human decision requested: select the claimant, if any, that retains
`GAP-0004`; approve the replacement alias for the other claimant.

Candidate validation evidence is recorded in
`2026-universal-uuidv7-alias-collision-disposition.yaml`: candidates are after
the observed/retired high-water marks (`CONST-0024`, `GAP-0019`), unique across
groups, not found in the scanned repository surfaces, and remain unallocated.

## Gate 2 — Family-scoped vNext schema contract

Repository evidence confirms the current families and compatibility surfaces:
authoring `v1.2`/`v1.3`, normalized-model `v1.1`/`v2.0`,
architecture-discovery `v1.1`, governance `v1.1`, evidence-attribution `v1.1`/
`v1.5`, and the existing migrations `v1.0` map. Package mirrors remain under
the established `src/adr_kit/schema/v*_*` namespaces. The current generated
architecture graph carries an artifact-local `schema_version: '1.0'`; the
architecture-index family authority is `architecture-discovery/v1.1`. This
projection labeling must be made explicit when the graph v2 contract is
embodied.

| Family / current contract | Proposed vNext | Why semantically required | Compatibility disposition |
|---|---|---|---|
| Authoring `v1.3` | `authoring/v2.0` | Required UUIDv7/alias envelope for every newly promoted graph-eligible authoring record changes required fields and canonical reference semantics. | v1.0 remains frozen; v1.2/v1.3 remain readable; v2 is additive and future package mapping is `src/adr_kit/schema/authoring/v2_0/`. |
| Normalized-model `v2.0` | `normalized-model/v3.0` | Effective relationships and assertions become independently identified entities, with persisted UUID endpoints and source-owner identity. | v1.1/v2.0 remain readable; future package mapping is `src/adr_kit/schema/normalized_model/v3_0/`. |
| Architecture-discovery/index and graph compatibility | `architecture-discovery/v2.0` / graph v2 | Projections must expose persisted relationship/assertion identity and distinguish fingerprints from canonical identity. | Current index/graph outputs remain compatibility surfaces; v1 is not removed implicitly. |
| Governance `v1.1` | `governance/v2.0` | Requirements, ledgers, reviews, objections, overrides, remediation records become UUID-bearing entities. | v1.1 remains readable; future package mapping is `src/adr_kit/schema/governance/v2_0/`. |
| Evidence-attribution `v1.1`/`v1.5` | `evidence-attribution/v2.0` | Evidence claims and source-owner bindings become UUID-bearing graph-eligible entities. v1.5 remains semantic attribution evidence, not authoring/model v1.5. | v1.1/v1.5 remain readable; future package mapping is `src/adr_kit/schema/evidence_attribution/v2_0/`. |
| Existing migrations map `v1.0` | migrations v2.0 universal map | Universal UUID allocation adds immutable allocation keys, collision dispositions, lifecycle, and sealing beyond the existing v1.3 map. | Existing sealed v1.3 map remains separate and readable; universal map is a new authority only after approval/sealing. |

Each proposal is a breaking/additive contract boundary, not an in-place edit.
The recommendation is `VNEXT_RECOMMENDATION=APPROVE_AS_DESIGNED`, subject to
human approval and the graph-version labeling clarification above.

`VNEXT_CONTRACT_APPROVED: [ ] YES / [ ] NO`

## Gate 3 — Graph vNext ontology

- An effective relationship is a canonical ENTITY with UUIDv7 `id`, governed
  `alias_id`/`alias_name`, relationship type, and UUID source/target endpoints.
- An assertion is a separate canonical ENTITY with its own identity envelope,
  effective-relationship UUID, source-owner UUID, source pointer, provenance,
  evidence, confidence, and metadata.
- Graph edges expose persisted relationship identity and assertion identity when
  represented. `relationship_id` and `assertion_id` remain fingerprints only.
- Generated inverses reuse the effective relationship UUID and do not receive a
  second canonical UUID. An independently authored inverse is a new entity.
- Graph v1 remains a compatibility surface until a separately approved removal.

Current compiler inverse/derived inventory (checkpoint graph counts in
parentheses):

| Authored/effective type | Generated type | Canonical entity? | Current evidence |
|---|---|---:|---|
| `enables` | `enabled_by` | No | `derive_relationships.py`; 1 derived edge currently emitted. |
| `supersedes` | `superseded_by` | No | Logical/decision/invariant/physical branches; 1 derived edge currently emitted. |
| `superseded_by` | `supersedes` | No | Physical `superseded_by` branch; 2 derived edges currently emitted. |
| component dependency / system component reference | derived `related_to` | No; derived relation, not an inverse pair | 6 derived edges currently emitted. |

The current compiler stores relationships in a dictionary keyed only by
`relationship_id` (`type:source:target`) and returns early on a duplicate key.
This can collapse multiple source assertions that share one effective endpoint
pair. Future embodiment must separate effective relationship identity from
assertion identity and preserve all source assertions explicitly.

`GRAPH_VNEXT_CONTRACT_APPROVED: [ ] YES / [ ] NO`

## Gate 4 — Allocation-map sealing contract

The proposed future authority is
`adrs/migrations/universal-uuidv7-allocation.yaml`, validated by a future
family-scoped migrations v2.0 schema. It is deliberately not created in this
pass. The existing sealed
`adrs/migrations/canonical-identity-v13-map.yaml` is a prior v1.3 identity map
and must not be treated as the universal map.

- Immutable lookup key: `canonical owner path + structural pointer + entity
  type`; it is independent of the UUID being allocated.
- Each entry records entity type, canonical path/pointer, legacy local key and
  alias, final alias, alias name, UUIDv7, source/checkpoint fingerprint,
  collision disposition, migration state, and sealing state.
- UUIDs are minted exactly once at `SEALED`, never during generation or graph
  compilation.
- Every collision must have a reviewed disposition before sealing.
- Seal is an explicit transition (`DRAFT` → `PREVIEW` → `REVIEWED` → `SEALED`);
  `APPLIED` follows only after an atomic migration write.
- Migration reads the sealed map, preflights all references and parity, applies
  atomically, and is idempotent against the same sealed map.
- Abandoned previews may be regenerated before sealing; post-seal allocations
  and identities are immutable.
- Generators and compilers cannot mutate or silently reseal the map.

`ALLOCATION_MAP_CONTRACT_APPROVED: [ ] YES / [ ] NO`

## ADR amendment assessment

ADR-L-0022 already normatively binds graph-eligible records to UUIDv7 identity,
declares value-object/projection boundaries, requires versioned migration and a
sealed map, and preserves ADR-L-0019/L-0021 authority. The relationship/assertion
split, inverse projection details, candidate aliases, and exact vNext mappings
remain implementation closure until human approval. No redundant ADR amendment
is prepared in this pass; copying the journal would create authority churn.

## Human-gate status

These values are intentionally derived from the unchecked decisions above; an
agent recommendation is not approval.

ALIAS_COLLISIONS_APPROVED=NO  
VNEXT_CONTRACT_APPROVED=NO  
GRAPH_VNEXT_CONTRACT_APPROVED=NO  
ALLOCATION_MAP_CONTRACT_APPROVED=NO  
UUID_ALLOCATION_MAP_SEALED=NO  
UNIVERSAL_IDENTITY_MIGRATION_READY=NO
