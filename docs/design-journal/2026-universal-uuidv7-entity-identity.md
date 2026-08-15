# Universal UUIDv7 Entity Identity — Implementation Design Closure

Status: implementation-ready design checkpoint; no corpus migration has been applied.

This journal is the implementation-oriented companion to accepted ADR-L-0019,
ADR-L-0021, and ADR-L-0022. It is committed authority for the migration design
gates described here. It does not replace the accepted ADRs, canonical schemas, or
the non-authoritative verification fixture.

## Locked architecture

- ADR-L-0019 remains authoritative for immutable UUIDv7 identity, repository-local
  aliases, alias uniqueness and retirement, UUID references, collision handling,
  sealed preflight maps, deterministic alias-name proposals, semantic parity, and
  compatibility gates.
- ADR-L-0021 remains authoritative for family-first canonical schema placement.
  Canonical `schema/...` bytes are semantic authority; installed package resources
  remain compatibility mirrors.
- ADR-L-0022 expands ADR-L-0019's old closed entity allowlist: every record that
  participates or may participate as a graph node or edge is an ENTITY before graph
  admission and must carry persisted UUIDv7 `id`, governed `alias_id`, and governed
  `alias_name`. Uncertainty resolves to ENTITY.
- Owner-local VALUE_OBJECT records are explicitly prohibited from present and future
  graph participation, have no independent lifecycle or authority, and use `key` or
  `<role>_key`, never entity `id`.
- DERIVED_PROJECTION records are generated views. They may expose canonical UUIDs and
  aliases but never mint or own them.
- Content hashes, relationship fingerprints, assertion hashes, paths, array order,
  local structural keys, and derived relationship identifiers are verification or
  lookup values only; none is canonical identity.
- Package version remains 0.4.1 for this checkpoint. No schema bytes, package
  resources, parser behavior, CLI behavior, SDK behavior, or corpus references are
  changed here.

## Identity classification matrix

The following matrix is the exhaustive implementation planning inventory for the
currently discoverable ADR-domain surfaces. A future schema promotion must update
this matrix before changing a contract. `current` is the admitted family-scoped
version or `nested-v1.3` for authoring subrecords. `next` is a proposed semantic
version, not an applied file change.

| Surface / record kind | Family; current | Owning contract or location | Class | Graph eligible | Independent lifecycle / reference | Canonical authority | Migration | Next | Notes |
|---|---|---|---|---|---|---|---|---|---|
| ADR documents | authoring; v1.3 | `schema/authoring/v1.3/adr-*.schema.json`; `adrs/*/ADR-*.yaml` | ENTITY | yes | yes / yes | canonical ADR YAML | yes | authoring v2.0 | Existing UUIDv7 envelope is retained; all nested promoted records follow this matrix. |
| decisions | authoring; nested-v1.3 | `adr-common` decisions | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve DEC aliases; UUID is canonical. |
| capabilities | authoring; nested-v1.3 | `adr-logical` capabilities | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve CAP namespace. |
| invariants | authoring; nested-v1.3 | `adr-common` invariants | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve INV namespace. |
| architectural boundaries | authoring; nested-v1.3 | `adr-common` boundaries | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve BOUND namespace. |
| interaction contracts | authoring; nested-v1.3 | `adr-logical` / physical contracts | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve CONTRACT namespace. |
| components | authoring; nested-v1.3 | physical ADR component specifications | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve COMP namespace. |
| interfaces | authoring; nested-v1.3 | physical component interfaces | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve IFACE namespace. |
| implementation decisions | authoring; nested-v1.3 | physical ADR implementation decisions | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve IMPL namespace. |
| authored systems | authoring; nested-v1.3 | physical-system ADRs | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve SYS namespace. |
| constraints | authoring; nested-v1.3 | `adr-common` constraints | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Historical CONST aliases require disposition. |
| non-functional requirements | authoring; nested-v1.3 | `adr-common` NFRs | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve NFR namespace; do not treat prose position as identity. |
| gaps | authoring; nested-v1.3 | `adr-common` gaps | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Historical GAP aliases require disposition. |
| system boundaries | authoring; nested-v1.3 | physical-system `system_boundaries` | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | Preserve SYSBOUND namespace. |
| integrations | authoring; nested-v1.3 | integration records where present | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | New namespace `INTEGRATION-####`. |
| data flows | authoring; nested-v1.3 | data-flow records where present | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | New namespace `FLOW-####`. |
| topology components | authoring; nested-v1.3 | `component_topology.components` | ENTITY | yes | yes / yes | owning physical ADR | yes | authoring v2.0 | New `TOPOCOMP-####`; current local IDs become historical keys. |
| topology relationships | authoring; nested-v1.3 | `component_topology.relationships` | ENTITY | yes | yes | owning physical ADR | yes | authoring v2.0 | New `TOPOREL-####`; relationship semantics use the ontology below. |
| evidence expectations | authoring; nested-v1.3 | `evidence_expectations` | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | New `EVIDEXP-####`; graph edge admission requires identity. |
| substrate bindings | authoring; nested-v1.3 | `substrate_bindings` | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | New `BIND-####`; external artifact IDs remain attributes. |
| rule bindings | authoring; nested-v1.3 | `rule_bindings` | ENTITY | yes | yes / yes | owning ADR YAML | yes | authoring v2.0 | New `RULEBIND-####`. |
| alternatives | authoring; nested-v1.3 | alternatives where present | VALUE_OBJECT | no | no / no | owning ADR YAML | no | authoring v2.0 | Owner-local only; use `alternative_key`; promotion is required before graph use. |
| consequences | authoring; nested-v1.3 | consequences where present | VALUE_OBJECT | no | no / no | owning ADR YAML | no | authoring v2.0 | Owner-local narrative/value data; use `consequence_key` if keyed. |
| technology choices | authoring; nested-v1.3 | technology-choice-like structures | VALUE_OBJECT | no | no / no | owning ADR YAML | no | authoring v2.0 | No independent authority; promotion required before reference. |
| requirements snapshots | governance; v1.1 | `schema/governance/v1.1/requirements-snapshot.schema.json` | ENTITY | yes | yes / yes | canonical snapshot YAML | yes | governance v2.0 | `REQSNAP-####`; `snapshot_id` is not a canonical UUID. |
| requirement items | governance; v1.1 | snapshot items | ENTITY | yes | yes / yes | canonical snapshot YAML | yes | governance v2.0 | `REQITEM-####`; legacy REQ keys are historical metadata. |
| decision ledgers | governance; v1.1 | `decision-ledger.schema.json` | ENTITY | yes | yes / yes | canonical ledger YAML | yes | governance v2.0 | `LEDGER-####`. |
| ledger decisions | governance; v1.1 | ledger decision entries | ENTITY | yes | yes / yes | canonical ledger YAML | yes | governance v2.0 | `LEDGERENTRY-####`; preserve legacy entry keys as metadata. |
| steelman reviews | governance; v1.1 | `steelman-review.schema.json` | ENTITY | yes | yes / yes | canonical review YAML | yes | governance v2.0 | Preserve REVIEW namespace. |
| review objections | governance; v1.1 | review `objections` | ENTITY | yes | yes / yes | canonical review YAML | yes | governance v2.0 | `OBJECTION-####`. |
| objection overrides | governance; v1.1 | `objection-override.schema.json` | ENTITY | yes | yes / yes | canonical override YAML | yes | governance v2.0 | `OVERRIDE-####`; references objection UUID. |
| remediation ledgers | governance; v1.1 | `remediation-ledger.schema.json` | ENTITY | yes | yes / yes | canonical remediation YAML | yes | governance v2.0 | `REMEDLEDGER-####`. |
| remediation entries | governance; v1.1 | remediation ledger entries | ENTITY | yes | yes / yes | canonical remediation YAML | yes | governance v2.0 | `REMED-####`. |
| unresolved findings | normalized-model; v1.1 | `unresolved-registry.schema.json` | ENTITY | yes | yes / yes | canonical unresolved source | yes | normalized-model v3.0 | `UNRES-####`; diagnostics are separate. |
| evidence claims | evidence-attribution; v1.5 | implementation attribution evidence | ENTITY | yes | yes / yes | canonical evidence YAML | yes | evidence-attribution v2.0 | `EVID-####`; UUID source-owner reference required. |
| effective relationships | normalized-model; v2.0 | relationship record/registry | ENTITY | yes | yes / yes | canonical relationship source | yes | normalized-model v3.0 | `REL-####`; canonical relationship UUID is not `relationship_id`. |
| relationship assertions | normalized-model; v2.0 | relationship provenance/evidence | ENTITY | yes | yes / yes | canonical assertion source | yes | normalized-model v3.0 | `ASSERT-####`; canonical assertion UUID is not `assertion_id`. |
| generated registry records | architecture-discovery; v1.1 | `adrs/index/*-registry.yaml` | DERIVED_PROJECTION | n/a | no / no | canonical source artifacts | no | architecture-discovery v2.0 | Reuse source UUID/aliases; never mint. |
| graph nodes | architecture-discovery; v1.1 | `adrs/index/architecture-graph.yaml` | DERIVED_PROJECTION | n/a | no / no | canonical source artifacts | no | graph v2.0 | Expose canonical node UUID/aliases. |
| graph edges | architecture-discovery; v1.1 | `adrs/index/architecture-graph.yaml` | DERIVED_PROJECTION | n/a | no / no | canonical relationships/assertions | no | graph v2.0 | Expose persisted relationship/assertion UUIDs; fingerprints remain non-authoritative. |
| effective inverse traversal | architecture-discovery; v1.1 | compiler graph projection | DERIVED_PROJECTION | n/a | no / no | canonical effective relationship | no | graph v2.0 | Never mint a second relationship entity. |
| diagnostics | runtime/projection; current | compiler diagnostics and unresolved messages | VALUE_OBJECT | no | no / no | owning execution result | no | runtime contract vNext only if promoted | Use `diagnostic_key`; graph admission requires explicit promotion. |
| local helper structures | implementation; current | parser/compiler internal objects | VALUE_OBJECT | no | no / no | implementation code | no | none | No persisted identity or cross-owner reference. |

## Relationship and assertion ontology

An independently addressable effective relationship is an ENTITY with UUIDv7 `id`,
`alias_id`, `alias_name`, relationship type, UUID source endpoint, and UUID target
endpoint. The existing deterministic `relationship_id` remains an optional semantic
key/fingerprint and deduplication key only.

An independently attributable relationship assertion is a second ENTITY with its own
UUIDv7 identity envelope, UUID reference to the effective relationship, UUID
source-owner, source pointer, evidence, confidence, and metadata. The existing
content-derived `assertion_id` remains an optional fingerprint/deduplication key.
One effective relationship may therefore have multiple assertions.

Mechanically reversible inverse traversal (`superseded_by`, `enabled_by`, and similar)
is a DERIVED_PROJECTION of the canonical authored/effective relationship. It does not
receive a second canonical UUID. An independently authored or governed inverse
statement is a separate effective relationship entity and must be allocated normally.
The later embodiment phase must make missing/ambiguous bindings diagnostic and must
never mint an authoritative edge during compilation.

## Alias namespaces and collision policy

Existing admitted prefixes remain unchanged: `ADR-*`, `DEC-*`, `INV-*`, `CAP-*`,
`BOUND-*`, `CONTRACT-*`, `COMP-*`, `IFACE-*`, `IMPL-*`, `SYS-*`, `SYSBOUND-*`,
`GAP-*`, `NFR-*`, `CONST-*`, and `REVIEW-*`. Newly promoted kinds use the explicit
prefixes in the matrix: `INTEGRATION-*`, `FLOW-*`, `TOPOCOMP-*`, `TOPOREL-*`,
`EVIDEXP-*`, `BIND-*`, `RULEBIND-*`, `REQSNAP-*`, `REQITEM-*`, `LEDGER-*`,
`LEDGERENTRY-*`, `OBJECTION-*`, `OVERRIDE-*`, `REMEDLEDGER-*`, `REMED-*`,
`UNRES-*`, `EVID-*`, `REL-*`, and `ASSERT-*`.

All prefixes use a repository-local, monotonic, non-reusable four-digit allocator
unless a future accepted contract defines a narrower pattern. `alias_name` must
match ADR-L-0019's lowercase kebab-case rule (`^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$`,
3–96 characters). A legacy alias is historical evidence, not an automatic final
alias. The collision disposition is recorded in
`docs/design-journal/2026-universal-uuidv7-alias-collision-disposition.yaml`.
Any unresolved disposition blocks map sealing.

## Family-scoped semantic version map

These are additive vNext targets only. Existing versions remain frozen and readable;
no version is modified in place by this refinement.

| Family / contract | Current | vNext | Canonical repository path | Future package mirror | Parser/model mapping | Migration and compatibility |
|---|---|---|---|---|---|---|
| Stable authoring compatibility | v1.0 | frozen | `schema/v1.0/` | existing `src/adr_kit/schema/v1_0/` | existing v1.0 parser | Read-only compatibility; never rewritten. |
| Authoring | v1.3 | v2.0 | `schema/authoring/v2.0/` | `src/adr_kit/schema/authoring/v2_0/` | authoring v2 model | v1.2/v1.3 remain readable; v2 is additive identity-bearing input/output. |
| Normalized model | v2.0 | v3.0 | `schema/normalized-model/v3.0/` | `src/adr_kit/schema/normalized_model/v3_0/` | normalized model v3 | v2 remains frozen/readable; relationship/assertion UUIDs are additive semantic change. |
| Architecture discovery indexes | v1.1 | v2.0 | `schema/architecture-discovery/v2.0/` | `src/adr_kit/schema/architecture_discovery/v2_0/` | discovery v2 | v1.1 remains compatibility input. |
| Graph projection | v1.1 compatibility surface | v2.0 | `schema/architecture-discovery/v2.0/architecture-graph.schema.json` | same discovery v2 package family | graph v2 renderer | v1 graph remains generated/readable in transition if required; parity is semantic, not byte identity. |
| Governance | v1.1 | v2.0 | `schema/governance/v2.0/` | `src/adr_kit/schema/governance/v2_0/` | governance v2 | v1.1 remains readable; requirements, reviews, ledgers, and remediation entities gain identity. |
| Evidence and attribution | v1.1 / v1.5 | v2.0 | `schema/evidence-attribution/v2.0/` | `src/adr_kit/schema/evidence_attribution/v2_0/` | evidence v2 | v1.1/v1.5 remain readable; UUID source-owner and claim identity are additive. |
| Migration allocation map | v1.0 | v2.0 | `schema/migrations/v2.0/` | `src/adr_kit/schema/migrations/v2_0/` | sealed-map v2 | Existing v1 map remains readable; universal UUID map is a separate authority. |

The package paths above are future mappings, not current files. They deliberately do
not alter existing `src/adr_kit/schema/v*_*` resources or package version 0.4.1.

## Graph/projection vNext contract

Graph v2 is additive. Nodes expose persisted canonical `id`, `alias_id`, and
`alias_name`. Canonical edges expose persisted effective-relationship UUID and aliases;
when an assertion is represented they also expose persisted assertion UUID and aliases,
plus the UUID source-owner and source pointer. `relationship_id` and `assertion_id`
remain fingerprints/keys only. `source_entity_id` and `target_entity_id` are UUIDs.
Inverse traversal is represented as a derived direction or traversal marker linked to
the same effective relationship UUID, never as a minted second entity.

Graph v1 remains a compatibility output during transition if consumers require it.
Semantic parity means preservation of relationship type, UUID endpoint meaning,
canonical source, provenance, evidence, confidence, and metadata—not byte-level
equality of legacy assertion fingerprints. Existing assertion-ID divergence between
architecture graph and normalized relationship registry is therefore explicitly
non-authoritative and must be reported, not silently normalized.

## Sealed universal UUID allocation-map contract

The universal map is distinct from `adrs/migrations/canonical-id-allocation.yaml`
(legacy alias allocation) and from the taxonomy verification fixture. Its v2 contract
will contain: `schema_version`, architecture namespace, source checkpoint/corpus
fingerprint, entity type, canonical owner path, structural pointer, legacy alias,
final alias, alias name, UUIDv7, collision disposition, migration status, historical
local key, immutable allocation key, and sealing metadata.

States are `DRAFT`, `PREVIEW`, `REVIEWED`, `SEALED`, and `APPLIED`. UUIDs are minted
exactly once at `SEALED`; an abandoned preview may be regenerated only before sealing.
After sealing or applying, identities are never silently reminted. Generators and
compilers never mutate the map. Migration reads the sealed map, requires all collision
dispositions to be complete, and applies the defined canonical write set atomically.
The map becomes migration authority only at the explicit seal transition.

## Migration gates and non-goals

Before embodiment: human review must resolve every collision disposition, approve the
namespace table and vNext version map, define package-resource additions, approve the
graph v2 schema, and seal the complete map. The migration must then preflight all
canonical references, topology records, relationship/assertion bindings, alias
uniqueness, and semantic parity before any write.

This refinement does not mint UUIDs, rewrite corpus references, migrate topology,
relationship, assertion, governance, evidence, or requirements records, change
existing schemas in place, change runtime/compiler behavior, remove compatibility
surfaces, bump package version, tag, publish, release, merge, promote, or open a PR.

The verification fixture remains a `NON-AUTHORITATIVE VERIFICATION SNAPSHOT` and is
used only to prove that current semantic corpus output is preserved while universal
identity remains unimplemented.
