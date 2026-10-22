# Internal ACC 1.2 non-composition dependencies

`authoring_construction_v12::dependencies::qualify_dependencies` is a read-only
crate-internal seam. It consumes insertion and root-accounting results, not a
request DTO claiming successful construction. It adds no protocol operation,
host capability, identity allocation, source rewriting or sealing.

## Verified prerequisites and authority

The insertion receipt is independently rechecked under the exact ACC 1.2 closure.
`RootsAccounted` results are recomputed using the existing artifact/root gate and
compared completely, including proof sets, bytes and outstanding obligations.
An unavailable root stage blocks usable dependency evidence. Independently
inspectable references, relationships and memberships are still checked using
the verified insertion receipt. Unverified failed-root diagnostics are not
accepted as semantic authority.

Authority remains accepted ADR-L-0035, exact ACC 1.2 and its inherited ACC 1.1
reference/result schema, exact ADC 1.1 reference policies, AI 1.2 field
dispositions and Authoring 1.7. Runtime history supplies implementation reuse,
not replacement authority. ADC `input_contract` is not a prepared-field list.

## Supported references

Explicit fragment `references` use inherited `reference_kind`:

- `request`: exactly one same-request fragment `request_key`, using its already
  established canonical UUIDv7 and exact type/qualification.
- `existing`: exactly one `reference_id` in the request's sealed reference basis,
  reusing its active canonical UUIDv7 and exact type/qualification.

Supported targets are built-in ADR/entity types uniquely present in both ADC
and AI, owned by `adr_kit`, with canonical UUIDv7 reference policy and allowed
reference posture. No lookup uses aliases, canonical UUID fallback, paths,
source references, ambient registries, existing-source basis, or composition
endpoint resolution. Reference keys are unique within each source semantic unit.

The coordinator qualifies candidates/expectations independently, then reuses
the unchanged ACC 1.1 resolver through a narrow wrapper to emit inherited
`resolved_reference` records. Each record is checked against the sealed ACC 1.1
schema fragment. Enclosing typed evidence retains the source UUID, exact target
basis, ACC fingerprint, ADC/AI resource identities and reference policy. No
parallel reference-result model or normalized representation is introduced.

Resource-set qualification arrays are normalized only in resolver/evidence
copies; exact keys and digests still have to match. Original requests, identities,
artifacts, serialized bytes and root proofs are untouched. Optional source
descriptors in the bounded reference basis use the existing digest verifier,
including unused entries. Descriptors provide integrity, never lookup fallback.

## Outcomes and explicitly unavailable cases

Duplicate reference keys and independent type/qualification expectations are
Rejected. Missing or non-unique targets are genuinely Unresolved, preserving
the inherited ACC 1.1 resolver's classification. Target authority outside the
exact selected Authoring set or an unimplemented target policy is Unavailable.
Malformed identities/state/basis shape fail the prerequisite request schema.
Independent violations are retained even when another check is unavailable;
precedence is Rejected, Unavailable, Unresolved.

Retired entries are valid schema states but are outside this active-target
capability. Their reuse remains Unavailable: no active-only prohibition or
retirement interpretation is invented. Custom/CEC-qualified and owner-local
reference targets also remain unavailable in this slice.

Every request relationship is inspected against exact ADC/AI type authority and
its declared Authoring qualification. Known authority is reported separately
from missing construction capability. No relationship source or endpoint identity
is manufactured. Unknown/custom authority and complete relationship execution
remain explicitly unavailable.

Additional memberships reuse the source-accounting stage's exact AI inspection.
A nonselected field is not a new composition binding. Nonempty values retain a
qualified field disposition plus an unavailable ownership dependency, even when
root accounting cannot finish. This inspection does not insert or count new
semantic units.

AI dispositions are authoritative for field meaning. For example,
`entity/decision#/related_invariants` is `complete_typed_json` matched by
`member_value`, not an implicit fragment-reference request. UUID-looking strings
are not scanned into references or synthesized relationships.

## Evidence, empties and atomicity

Each source has a checked reference collection, including explicit empty
evidence. Empty relationship and nonselected-membership collections are checked
separately. Success is the internal `DependenciesQualified` status; it removes
only the non-composition dependency obligation. Complete composition records,
composed-source sealing, interpretation, ledgers/equality and complete
construction qualification remain outstanding.

Failure clears usable reference collections and empty-success flags. Typed
pending obligations and deterministic diagnostics remain available to explain
blocked authority/capability. Sorting uses established source identity, stable
reference/relationship/field keys and canonical payload digests, never discovery
positions. Tests permute fragments, compositions, references, basis entries and
qualification resource arrays without changing evidence or diagnostic order.

## Remaining slice

The [internal composition-record gate](acc12-composition-records.md) now assembles
and validates all required published semantic, integrity and qualification fields
against these independently verified inputs. It replays dependency qualification
rather than trusting this stage's status or a caller's completion flag.
Requests with pending relationship construction, custom/retired reference
handling or additional membership ownership still cannot qualify a complete
basis. Only after every applicable dependency is executable and proven may a
separately authorized slice seal the composed source basis and detached context.
This dependency stage itself emits no composition record, sealed basis, NM model
or Constructed outcome.
Historical ACC 1.0/1.1 operations, frozen authorities, protocol 1.5 and current
SCS selection remain unchanged.
