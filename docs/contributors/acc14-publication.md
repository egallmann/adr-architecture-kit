# ACC 1.4 authority publication

ACC 1.4 is a standalone immutable construction authority authorized by accepted
ADR-L-0038 (DEC-9009–9016, INV-0301–0308). It selects exact AI 1.4 and unchanged
NM 2.5. Publication does not execute construction or interpretation.

| Authority | Exact SCF | Resources |
| --- | --- | --- |
| ACC 1.4 | `scf:v1:sha256:19e267c5c77477a594414168bde9f733b1b9e547c06fc6836ad09392a248ea6d` | 108 |
| AI 1.4 | `scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7` | 60 |
| NM 2.5 | `scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7` | 7 |
| Historical ACC 1.3 | `scf:v1:sha256:5828fe0c3b1692240726152f57ca6de037a1e07f38bb8f9ecda223af105d1b49` | 94 |

## Exact publication inventory

The seven successor-specific canonical resource keys are:

- `authoring-construction/1.4/schema`
- `authoring-construction/1.4/rules`
- `authoring-construction/1.4/compatibility`
- `authoring-construction/1.4/composition-bindings`
- `authoring-construction/1.4/composition-bindings.schema`
- `authoring-construction/1.4/conformance`
- `authoring-construction/1.4/conformance.schema`

Their canonical files are under `contracts/authoring-construction/v1.4/`, with
byte-identical flattened canonical and Python resources. The standalone
definition is mirrored through the established semantic-contract definition
and Python package paths. Node's existing asset packaging includes these files.

The full AI 1.4 and historical ACC 1.3 resource closures are included, alongside
their exact definitions, Authoring 1.7, ADC 1.1, CEC 1.0 and NM 2.5 dependencies.
Historical conformance may be a qualified dependency; only
`authoring-construction/1.4/conformance` is frozen normative ACC 1.4 conformance.
The enclosing ACC 1.4 SCF is not embedded in its own resource closure.

## Inherited meaning and exact selection

ACC 1.3 identity, references, artifact bytes, minimal roots, detached context,
composition ownership/order/preservation, lifecycle semantics, outcomes and
diagnostic aggregation are inherited. The semantic ledger retains the exact
`authoring-construction/1.3/ledger.schema` resource and version. Its
`ai13_semantic_tuple` identity kind continues to name actual inherited meaning;
it is not renamed to imply an unpublished rule.

The single composition row is unchanged: logical ADR → Decision, `contains`,
compiler-owned `/decisions`, exact same-request create/prepared endpoints and
authored integer ordering. Its disposition and ownership qualifications remain
actual AI 1.3 keys, digests, SCF and rule identities, including
`declaring-lifecycle.adr-logical.decisions`. Enclosing request, interpretation and
construction evidence independently qualify ACC 1.4 and AI 1.4. Rewriting an old
receipt's version or fingerprint never qualifies successor execution.

The table's governing validation schema is
`authoring-construction/1.4/composition-bindings.schema`, not the predecessor
validator, whose version constraint rejects a 1.4 table. The declaration,
companion schema's closed dependency expectation, selected schema digest and
table manifest edge must all agree. This versioned validation dependency is
independent of the row's deliberately inherited AI 1.3 semantic-rule authority.
Publication qualification verifies the schema edge independently of generated
templates and SCF integrity; recomputing an SCF cannot conceal the wrong edge.
Resource preflight precedes generation; the assembled manifest is checked before
writing, and ordinary qualification verifies the published definition/closure.

## Required outputs and independent equality

The exact AI 1.4 catalog accounts for 27 types, 186 qualified producer
definitions, 269 BLOCKED entries and 26 literal-copy label rules. These are
definition counts, not completed instance outputs or 27 independently
constructible roots. Every applicable destination requires one qualified
producer after exact schema-branch, identity, source and context qualification.

Construction qualification adds `required_output` evidence. It identifies the
enclosing AI authority/catalog, each unit/branch, selected destination and actual
producer rule, independent checks, and blocked/competing destinations. The
schema excludes BLOCKED entries from the producer alternatives. A complete
claim requires independently verified inputs/types, source/identity,
applicability/context, exact operation and output, with no blocked or competing
destinations. Schema-valid flags or counts do not prove those facts: independent
reconstruction from original sealed sources and established identities remains
mandatory, as does validation of the actual complete NM 2.5 result.

Representation-only copies do not create second semantic values. Original
authored values remain at their governed destinations, including typed semantic
extensions. Complete expected/observed semantic ledgers are independently
derived and compared. A correct label cannot excuse a missing extension; a
correct extension cannot excuse a changed label. Schema validity, digests,
fingerprints, proof receipts and replay copies prove neither obligation.

Literal lifecycle, independently qualified declaring ownership and
`context/declaring_adr_lifecycle#` retain their actual inherited AI 1.3 authority.
The first-class lifecycle value is never duplicated in the contextual carrier.

All 14 AI blocker categories remain explicit: alias-ref and URI recipes,
creation-time encoding, fingerprint preimage, source envelope, completeness,
custom lifecycle, declaring context, shared identity, relationship branch and
envelope, unqualified conditional output, owner-local context and custom
qualification. Any applicable unresolved prerequisite prevents complete
materialization and Constructed. Unsupported authority/capability is
Unavailable; established violations are Rejected; Unresolved requires a
governed unresolved dependency. Independent diagnostics are retained with
Rejected > Unavailable > Unresolved > Constructed precedence.

## Frozen conformance inventory

All **263 ACC14 cases are authority-only**, not runtime construction coverage.

| Cases | Publication obligation |
| --- | --- |
| ACC14-001–159 | Individual qualified references/reviews of all 159 ACC13 cases; no rewritten historical fixtures |
| ACC14-160–186 | All 27 exact type/output branches and BLOCKED accounting |
| ACC14-187–212 | All 26 representation-only literal-copy rules and original semantic preservation |
| ACC14-213–226 | All 14 explicit blocker categories |
| ACC14-227–254 | Wrong authorities, closure corruption, fabricated inherited rules, forged proof, competing producers, semantic loss, relationship/custom boundaries and mixed outcomes |
| ACC14-255–263 | Binding cardinality, complete NM/ledger requirements, permutations, historical preservation and publication/runtime exclusions |

Inherited assertions are retained by exact case resource/digest/pointer. The
review for each case states its successor selection and additional output
prerequisites. Only the exact-selection assertion changes from enclosing AI 1.3
to AI 1.4; wrong-version/SCF cases retain their Unavailable oracle. Lifecycle,
ownership, context and structural fixtures remain historical case evidence,
never relabeled as executable successor requests or full Constructed examples.

## Qualification and durable tests

```powershell
python scripts/generate_semantic_contract_assets.py --publish-acc14-only
python -m scripts.qualify_acc14_publication
python -m pytest tests/test_authoring_construction_v14_publication.py
python tests/pr_scoped/qualify_acc14_publication.py --base <actual-base> --head <actual-head>
```

Generation qualifies resources before writing manifests/mirrors and uses the
existing canonical dependency discovery, RFC 8785 fingerprinting and Rust-backed
closure verification. It never invokes ordinary historical/SCS generation.

Permanent tests pin immutable SCF/closure/bytes, package parity, negative
mutations and deterministic generation against a snapshot of the current tree.
They do not pin future work to this PR's Git base or require perpetual
nonselection/unavailability of successor versions. The explicit base/head gate
owns this publication PR's file boundary, historical Git-blob and selected-set
preservation. Narrow historical ACC 1.3 discovery assertions use a genuinely
missing version rather than forbidding ACC 1.4 forever.

No Rust/WASM, protocol, capability, current SCS, persistence, admission or
promotion changes occur here. Complete interpretation, materialization, expected
and observed ledger execution, semantic equivalence and Constructed remain
unimplemented by this publication. The next work must qualify the remaining
exact output recipes/semantic prerequisites before claiming complete execution.
