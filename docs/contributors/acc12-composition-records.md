# Internal ACC 1.2 composition records

`authoring_construction_v12::records` assembles and qualifies the complete
published `composition_record` objects. `RecordsQualified` is internal evidence;
it is not a constructed result, source-basis seal or public capability.

## Evidence producers

The assembler replays insertion's private established-request receipt,
preservation proof and exact ACC 1.2 closure qualification. Dependency
qualification independently recomputes and compares the supplied artifact/root
accounting, then checks every supported reference and explicit empty collection.
The entire recomputed dependency result must equal the supplied result.
Caller-set success flags cannot replace these checks.

Canonical identity assertions are reconciled across the candidate and sealed
reference bases. Consistent reuse through multiple reference selectors is valid;
conflicting types, qualifications or existing-target states fail closed. Candidate
create state is not an assertion of active repository existence.

## Record partitions

- Semantic: established parent/child UUIDs, exact bound types, relation, field,
  binding ID, authoring property, authored ordering and request resolution.
- Integrity: exact request keys, source refs/digests, binding key/digest,
  prepared-property absence, exact subtree, retained child artifact, child-root
  omission, induced sequence index and original identity dispositions.
- Qualification: exact ACC SCF and binding selector, ADC contract digest,
  AI closure, Authoring closure, NM closure and CEC contract closure.

The four flags come from replayed insertion and accounting evidence, not from
the required schema constants. Every intent must have exactly one record. Record
ordering is exclusively parent UUID, authored ordering, child UUID. Qualification
resource arrays are sets and are normalized without changing source bytes.

CEC qualification describes the immutable CEC contract resources supplied by the
verified ACC closure. It does not select a consumer registry or custom definition.
A null request `custom_entity` remains null; no registry or CECF is invented.

## Independent qualification and atomicity

`qualify_records` validates the exact sealed ACC 1.2 schema fragment and compares
the complete record set with independently assembled expectations. Schema-valid
wrong IDs, ordering, refs, digests, dispositions, resource sets or sequence indexes
are rejected. Missing, duplicate and fabricated records cannot qualify. Failure
releases no records. Diagnostics retain governed precedence and deterministic
ordering; no partial success is exposed.

## Coverage and remaining obligations

Tests exercise ACC12-01/02 record properties, request/resource-set permutation,
all semantic/integrity fields, missing partitions and proof flags, incomplete
qualification, CEC corruption, source/proof tampering and forged dependency
completion. They do not relabel full frozen construction cases as passed.
Historical contracts, protocol 1.5, host capabilities and current SCS remain
unchanged.

The [internal composed-source sealing gate](acc12-composed-source-sealing.md)
now replays these records before sealing and deriving detached context.
Pending relationships, retired/custom/owner-local references and additional
membership ownership still block records. After all applicable dependencies and
records qualify, the sealing gate may seal the complete source basis. NM 2.4
interpretation, ledgers/equality and complete construction remain deferred.
