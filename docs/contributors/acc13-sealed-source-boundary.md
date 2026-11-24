# Internal ACC 1.3 sealed-source handoff

This implementation is an internal Rust prerequisite. It adds no protocol
operation, public capability, normalized model or ACC construction outcome.

## Authority and trust boundary

The closed `Acc12`/`Acc13` profile selects expectations. It never grants
authority. Every qualification and receipt replay verifies the definition and
complete manifest closure using the existing semantic-contract implementation.
The ACC 1.3 boundary also independently verifies the enclosed AI 1.3 definition
and the explicitly supplied NM 2.5 definition against their pinned SCFs and
exact resource subsets. Extra supplied resources do not confer authority.

| Profile | ACC | AI | NM | Source authorities |
| --- | --- | --- | --- | --- |
| Historical | 1.2 | 1.2 | 2.4 | Authoring 1.7, ADC 1.1, CEC 1.0 |
| Successor | 1.3 | 1.3 | 2.5 | Authoring 1.7, ADC 1.1, CEC 1.0 |

ACC 1.3 SCF:
`scf:v1:sha256:5828fe0c3b1692240726152f57ca6de037a1e07f38bb8f9ecda223af105d1b49`.
AI 1.3 SCF:
`scf:v1:sha256:d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167`.
NM 2.5 SCF:
`scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7`.

The selected binding remains table-owned: logical ADR to Decision, `contains`,
compiler-owned `/decisions`, prepared/create same-request endpoints and authored
integer ordering. Its AI ownership resource, unique rule, schema selectors,
identity selectors and status-source authority are qualified without executing
lifecycle inheritance.

```text
exact ACC/AI/NM closures + exact request
  -> binding/disposition/ownership authority
  -> insertion + private established-identity receipt
  -> complete retained artifacts + exact-subtree minimal roots
  -> supported dependency qualification + complete composition records
  -> native candidate-source sealer
  -> exact AI 1.3 detached root contexts
  -> independent replay against request and private receipts
```

Existing ACC 1.2 entry points remain fixed to their historical profile. Shared
producer mechanics take an explicit closed profile. Private receipts commit to
that profile, the verified definition, original request, established identities
and identity dispositions. Cross-version receipt reuse fails closed.

Reusable predecessor primitives have explicit, bounded roles:

- `candidate_source` remains the native Authoring serializer, artifact verifier,
  minimal-root primitive and sole basis descriptor/sealer.
- The basis-v1.1 UUID predicate, exact resource-set checks, qualified-reference
  resolver and basis-to-JSON projection operate on explicitly supplied inputs.
  Successor callers qualify those inputs against the successor closure first.
- `authoring-construction/1.1/schema` supplies the unchanged resolved-reference
  shape as an explicit ACC 1.3 manifest dependency. It does not select ACC 1.1
  execution.
- The historical interpreter's source/output-context structs are data carriers
  only. No AI 1.1 interpretation function is invoked.

Version-dependent binding, disposition, record-schema and detached-context
selection always use the verified profile's exact keys.

## Producer and verifier

`authoring_construction_v13::prepare` accepts ACC definition/resources, the NM
definition, request, exact opaque source-reference assignments and the existing
identity-minter interface. Each authorized missing create identity is allocated
once. Supplied identities are preserved.

`verify` has no minter. It independently rechecks authority and replays the
producer chain using established identities. It compares preservation, exact
bytes, complete artifact membership, minimal roots, records, source assignments,
basis commitment and detached contexts. Rewritten bytes with recalculated
digests cannot replace original request/identity commitments.

The native `adr-kit.candidate-source-basis/v1` descriptor and sealer remain the
sole commitment implementation. Child artifacts remain retained independently
of child-root omission. Detached contexts select only the AI 1.3 resource and
carry exact AI/NM qualifications; opaque locators imply no repository placement.

`Sealed` is intermediate source evidence. `Rejected`, `Unavailable` and
`Unresolved` retain their governed meanings and precedence. Failure releases no
sealed evidence or composition records. Unsupported execution is unavailable;
missing governed references become unresolved only through actual resolution.

## Executable coverage and deferred obligations

Tests exercise source-preservation, retained-child, minimal-root, composition
record and permutation properties of ACC13-001/002, and authority failure
properties of ACC13-030/031. They do not execute all assertions of those cases:
normalized lifecycle/context and full construction assertions remain deferred.
The remaining frozen cases remain authority oracles, not claimed runtime
coverage. Additional tests cover multiple parent roots, supported local/active
existing references, tampering, dialects, cross-version receipts and atomicity.

Historical parity is pinned to independently captured outputs from baseline
`5ab992a0a3aecbac654fd2250f1935affae36f09`: two complete fixed-identity producer
commitments and five complete qualification/diagnostic commitments. These cover
qualified results, source bytes/commitments, records, contexts, invalid relations,
missing targets, unsupported mode, duplicate identity and mixed diagnostics.

Supported producer inputs remain fully participating prepared-create logical
ADR/Decision compositions. Native standalone fragments are never wrapped;
unsupported aggregation stays unavailable. Retired/custom/owner-local reference
execution, relationship construction and additional membership ownership remain
blocked. No new binding row is introduced.

Next: independently qualified AI 1.3 field-disposition execution, literal
lifecycle placement and declaring-owner/context qualification. Complete NM 2.5
assembly, expected/observed ledgers, whole-ledger equality and `Constructed`
remain subsequent obligations. No current contract selection changes.
