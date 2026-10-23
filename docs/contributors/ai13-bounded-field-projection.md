# Internal AI 1.3 field and declaring-lifecycle projection

This seam is private Rust code. It exposes no protocol operation or capability.
`DispositionsQualified` describes bounded facts, while
`complete_interpretation` remains `Unavailable`. It is neither an NM 2.5 model
nor ACC construction, a ledger, or semantic equivalence.

## Authority and trust boundary

| Authority | Version | Exact SCF suffix |
| --- | --- | --- |
| ACC | 1.3 | `5828fe0c3b1692240726152f57ca6de037a1e07f38bb8f9ecda223af105d1b49` |
| AI | 1.3 | `d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167` |
| NM | 2.5 | `bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7` |

Each suffix uses `scf:v1:sha256:`. Original definitions and resource bytes
remain authoritative. The ACC closure contains the independent 52-resource AI
closure and seven-resource NM authority, plus Authoring 1.7 and ADC/CEC.

The boundary is:

1. Independently qualify exact ACC/AI/NM definitions and resource closures.
2. Qualify the five-class field catalog, all 27 types, source selectors,
   schema coverage boundaries, destination and identity references,
   deterministic derivations, ownership and contextual catalogs.
3. Call ACC 1.3 `verify` with the original request, source references and
   producer receipts. This rechecks identities, bytes, roots, dependencies,
   records and detached context without a minter or insertion producer.
4. Decode only verified minimal root artifacts.
5. Derive field placements and independently prove Decision ownership.
6. Independently replay the complete projection when consuming supplied
   projection evidence.

The existing schema evaluator is reused. AI schema `semanticDependencies`
annotations are explicitly checked against the verified closure before
projecting schema documents into that evaluator. No validation keyword is
removed. Original resources remain the digest authority, and unknown keywords
still fail closed. Historical schema evaluation is unchanged.

## Executed and deferred surface

| Surface | Execution |
| --- | --- |
| Full published 27-type catalog | Authority/schema coverage qualification only |
| `adr/logical` fields | Canonical placements, complete typed semantic extensions, deterministic ceremony and child identity membership |
| `entity/decision` fields | Canonical placements and complete typed semantic extensions |
| All three ADR root status domains | Complete source-schema qualification and literal destination-domain inclusion; physical root lifecycle fixtures do not expand ACC construction |
| `declaring-lifecycle.adr-logical.decisions` | Independently qualified containment, owner/child identities, authored status, carrier and contextual value |
| Other nonempty child memberships | Unavailable; no partial projection released |
| Standalone Decision | Native representation retained; current ACC producer cannot release its seal, so interpretation remains unavailable |
| Shared physical-system descriptor ownership | Not executed; no second unit manufactured |
| Other ownership, relationships, custom and owner-local types | Not executed; no implicit inheritance |
| Complete NM assembly, ledgers, equality, construction | Unavailable |

Field coverage stores the selected disposition, source value and destination
as proof. Parent child-membership semantic values contain UUIDs in authored
order, with no child payload. Complete child payload remains child-owned.
Optional fields are preserved only when present. Structured JSON is not
stringified, coerced, truncated or reordered.

## Declaring ownership and contextual facts

The exact selected ownership rule must resolve the Authoring schema containment
to the Decision definition. The parent must contain exactly one exact child
subtree with that canonical UUID. This is cross-checked against the separately
retained child artifact and the independently verified composition association.
An association record alone cannot establish ownership.

The six-field carrier is independently derived and validated against the exact
`lifecycle-provenance.schema`. Its contextual fact value is also validated
against `contextual-facts.schema#/$defs/contextual_fact_value`. The stable
contextual key is `context/declaring_adr_lifecycle#`, under the child's canonical
identity. Neither carrier nor contextual value duplicates `lifecycle_stage`.

Future semantic comparison must use the contextual catalog's declared equality
fields and exact governing rule meaning, separately from integrity qualifiers.
This slice performs no whole-result equality. Source commitments, schema
qualifications, coverage snapshots and digests are evidence, not semantic owner
identities. Source locations never select owners or mint identities.

## Failure and conformance accounting

Findings sort deterministically with Rejected > Unavailable > Unresolved.
Only predecessor verification can establish an unresolved dependency. An
unsealed producer supplies no interpretation prerequisite; falsely claiming a
seal with missing receipts is rejected. Failures expose no units or source
commitment. Reverification blocked by missing authority is unavailable, rather
than a fabricated semantic mismatch.

Executed frozen assertions:

- AI13-022–033: twelve literal root status/domain assertions using complete,
  schema-qualified source fixtures.
- AI13-046–049: the Decision ownership row for four literal statuses using
  verified ACC 1.3 composed sources.

These are bounded assertions. Other AI13 assertions remain publication-only or
deferred, including remaining ownership selectors and complete interpretation.
No frozen case is relabeled as complete end-to-end construction coverage.

Tests additionally cover typed child fields, ordered membership, exact authority
substitution/corruption, missing schema dependencies, unknown validation keywords,
duplicate/unknown fields, forged contextual meaning, missing/extra facts,
changed placement and coverage, changed source bytes with recalculated digests,
context/root tampering, native standalone blocking, request/resource permutations,
atomic failure and deterministic diagnostic precedence. Existing ACC 1.2 full
fixture commitments and ACC 1.3 producer/replay tests remain unchanged.

Next prerequisites are the remaining AI-owned semantic/ownership execution
obligations and full detached multi-root NM 2.5 assembly. Whole-result ledgers
and equality remain separately required before construction qualification.
