# ACC 1.5 current candidate consolidation

ACC 1.5 selects exact AI 1.5 under accepted ADR-L-0039, retaining ADR-L-0037/0038
and inherited construction meaning. Accepted ADR-L-0040 classifies AI 1.5,
ACC 1.5 and NM 2.5 as candidates until explicit promotion. A new Git revision may
change candidate content and its exact SCF without incrementing these versions.
No execution or compatibility promotion follows from generation or merge.

The inventory below records the original PR #186 revision
`6ddc8c2b6d66531ff3ecefb0bba7b15616ac4f0c`, retained as migration evidence.
It is not a perpetual compatibility pin for later candidate revisions.

## Maintained inputs and integration checkpoints

AI/ACC 1.5 resources are maintained canonical inputs. Their generators now derive
exact reference closures, commitments and package mirrors without reconstructing
rules from predecessor builders. Complete independent semantic qualification of
the proposed definition precedes distribution. This first checkpoint reproduces
the original definitions exactly; no authority resource bytes changed.

The subsequent atomic checkpoint must qualify an explicit selector migration and
remove development-only lineage/byte obligations. It must preserve actual released
authority, all accepted semantic rules and independently necessary conformance.
Until that work and co-dependent consumers are qualified, consolidation is incomplete.

### Implemented validation-selector checkpoint

AI 1.5 now maintains only the validation fragments actually referenced by its
companion schemas. All eight roots move from
`architecture-interpretation/1.4/required-output-derivations.schema` into
`architecture-interpretation/1.5/required-output-derivations.schema`:

| Original selector | Current selector |
| --- | --- |
| `/properties/source_contract` | `/$defs/coverage_source_contract` |
| `/properties/output_contract` | `/$defs/coverage_output_contract` |
| `/properties/field_dispositions` | `/$defs/qualified_resource` |
| `/properties/operation` | `/$defs/coverage_operation` |
| `/properties/coverage` | `/$defs/coverage_policy` |
| `/properties/branches` | `/$defs/coverage_branches` |
| `/properties/status_scope` | `/$defs/coverage_status_scope` |
| `/properties/types/items` | `/$defs/coverage_output_type` |

All 35 migrated references preserve their complete selected constraint body.
Nested selectors retain their suffix under the mapped root. Consumers are the
AI 1.5 catalog, recipe and conformance companion schemas, plus ACC 1.5's
conformance companion schema. ACC's three qualified-record references now use
the current `qualified_resource` fragment. The catalog companion uses local
references; the other AI companions explicitly depend on that current schema.
The reference counts are 26 in the catalog companion, two in the recipe
companion, four in the AI conformance companion and three in ACC conformance.
No whole predecessor schema, rule identity or new producer is copied into the
candidate. The independent qualifier compares every selected constraint body
with the original and excludes predecessor schemas from its own evaluation
registry. Behavior tests exercise valid/invalid records and all 27 type branches;
a consistently rehashed weakened constraint still fails qualification.

At the validation-selector checkpoint the AI SCF was
`scf:v1:sha256:deabae39d62f87a890c511969ab796a21a0db2a88fe45ef7487d04aee94722f3`
(69 resources); ACC is
`scf:v1:sha256:5f058d9fada1110ab9db43f15e8104afaf33a3e39b9cef507468c4c4363eea29`
(125 resources). These describe this revision, not permanent candidate pins.
All dependent ACC closure members, qualification digests and selected-AI
fingerprints are regenerated together. Membership does not shrink in this slice:
the enclosing historical definitions still require their original resources.

Current NM 2.5 selection is derived from its maintained definition and qualified
against the exact canonical schemas, dependency graph and complete closure.
Stale distributed definitions, wrong-version resources and missing canonical
inputs cannot qualify. A test-only same-version schema annotation produces a
different qualified NM SCF; no maintained NM byte changes. This current selection
is distinct from the exact NM snapshot still required by inherited AI 1.3/1.4
authority. That enclosing-definition coupling is addressed by the following checkpoint;
no selected closure may contain different contents under a single canonical key.

### Implemented enclosing-selection checkpoint

Current selection now traverses actual resource references and declared governing
validation/conformance dependencies. It never unions predecessor manifests into
an enclosing current cohort. The AI rules name the actual AI 1.3 semantic rule
resource explicitly. Closed historical fields (`inherits`, inherited conformance
and case qualifications, compatibility historical definitions) are independently
verified evidence, not permission to import old enclosing selections. The AI
`inherits` record explicitly declares `historical_evidence_not_current_selection`
and binds its recorded source revision. Unknown or
changed evidence records fail qualification; the exclusions cannot hide arbitrary
new authority. Governing companion schemas and conformance policies remain real
selected dependencies even where fixture payloads contain no `$ref` to them.

Before: AI selected the whole AI 1.4 manifest plus its definition; ACC selected the
whole ACC 1.4 and AI 1.5 manifests plus both definitions. After: both select the
transitive graph rooted in their maintained own resources. The AI 1.4 definition,
conformance and rule aggregator are no longer active AI members; the ACC 1.4
definition, compatibility, conformance, rules and schema are no longer active ACC
members. Historical conformance still has 85 AI and 263 ACC individually verified
case references with their original assertions. No assertion is discarded.

AI now has **40 resources** at
`scf:v1:sha256:446dd62bd9f3683136351f41516a37426dee9b7f4faf1d063202a34a82c0bc5a`;
ACC has **107 resources** at
`scf:v1:sha256:43a03fec6e8cd5257184557888f61d9e4168c9af0ad2886f308d226509b53642`.
These are revision commitments, not target counts or compatibility pins. The
unchanged AI 1.4 catalog/operation and AI 1.3 disposition, ownership, context and
rules retain their actual resource identities. AI 1.3's definition remains a
selected provenance record where that catalog requires it; its manifest is not
an instruction to import a second current closure. Necessary historical ACC
ledger/schema fragments remain, with their scoped validation selected exactly.
Four small AI 1.4 policy projections are explicit current rules: complete required-output
validation, representation-only duplication, whole-ledger equality and the all-27-type
objective. Every value is compared independently with its exact original fragment;
only the already-authorized current catalog/schema selectors differ. Their actual
AI 1.4 keys, pointers and digest are retained under closed historical `policy_sources`.
This carries all substantive policy in the current closure without importing the
historical aggregator. A validly rehashed weakened projection is rejected.
No entire historical resource is copied, renamed or modified to manufacture this graph.

Historical AI 1.3/1.4, ACC 1.3/1.4 and NM 2.5 definitions and complete original
closures are independently reproduced from recorded Git revision
`6ddc8c2b6d66531ff3ecefb0bba7b15616ac4f0c`. Their original SCFs and bytes remain
unchanged. Their NM members are read from that revision, never today's NM paths.
Current NM selection separately requires the maintained definition, canonical
resources, exact discovered dependencies, SCF/closure verification and unchanged
schema constraints. Only schema annotations are excluded from that constraint
comparison; instance property names and literal values remain significant.

A full in-memory atomic cohort test revises NM 2.5 with an annotation, derives a
new NM SCF and all dependent AI/ACC integrity qualifications, and independently
qualifies both current candidates. It does not modify maintained NM bytes or
rewrite an inherited rule's fingerprint. A changed constraint or restored whole
predecessor import fails even with a valid newly computed SCF. Stale distributed
NM bytes cannot satisfy the maintained canonical source check. ACC's exact NM
closure qualification now derives the current manifest/digests/SCF rather than
freezing its predecessor's snapshot. Each current closure selects one content
per canonical key; historical reproduction is a separate operation.

No historical publication qualifier executes as an implicit current-selection
fallback. Shared Rust SCF/closure verification and existing exact Python/Node
resource discovery suffice; no Rust, WASM, runtime or public API change is needed.
The remaining target is scoped ACC ledger/schema-helper and residual historical
compatibility-resource dependencies. They are retained until their actual
selector/semantic replacements are independently demonstrated.

Actual AI 1.3 field-disposition, lifecycle/ownership and detached-context keys,
digests, rule IDs and SCFs remain normative dependencies. The one composition
row, five evidence checks and whole-ledger obligations are unchanged. The generic
Rust SCF/closure implementation and Python/Node exact loaders already support
the migrated keys; no Rust or public API change is needed. Their new-bundle
verification and package parity are exercised through the existing WASM boundary.

| Authority | Exact SCF | Resources |
| --- | --- | --- |
| ACC 1.5 | `scf:v1:sha256:4bfbffb564c8c7c8bda8b07b663a238f7396f53164e9561cd94f23473e974d19` | 125 |
| AI 1.5 | `scf:v1:sha256:e3d52d9e863cfb6008f55bbff5c7ea4e676ac6a021d9eb52126284636d0329af` | 69 |
| Historical ACC 1.4 | `scf:v1:sha256:19e267c5c77477a594414168bde9f733b1b9e547c06fc6836ad09392a248ea6d` | 108 |
| NM 2.5 | `scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7` | 7 |

## Exact resource inventory

Seven own keys under `authoring-construction/1.5/`: `schema`, `rules`,
`compatibility`, `composition-bindings`, `composition-bindings.schema`,
`conformance`, `conformance.schema`. The canonical schema is `schema.json`;
the other six files are in `resources/`. Standalone definition, flattened
canonical resources and Python mirrors follow existing distribution. Node
packaging includes the exact published data. No current selection changes.

The 125-member closure is discovered from actual dependencies: complete ACC 1.4
and AI 1.5 closures, their exact definitions, and seven own resources. The
qualifier independently checks membership, roles, digests and every edge.
Only `authoring-construction/1.5/conformance` is selected normative ACC 1.5
conformance. The definition's `frozenNormativeConformanceResources` field selects
exact content for a candidate revision; ADR-L-0040 governs when promotion freezes
compatibility. The enclosing ACC 1.5 SCF never appears inside its own closure.

## Construction and required-output authority

All inherited identity, reference, artifact, detached-source, minimal-root,
composition, lifecycle, contextual ownership, NM 2.5, ledger and outcome
requirements remain. The operation identifiers remain `validate_authoring`
and `construct_authoring_set`; publication does not advertise their successor
execution. Expected and observed ledgers retain the actual
`authoring-construction/1.3/ledger.schema` identity.

The single logical ADR/Decision `contains` row is unchanged. Its actual AI 1.3
disposition/ownership SCF, keys, digests and rule ID remain exact, alongside ADC
and Authoring qualifiers. Only the table version and its own companion-schema
qualification change. The table dependency, companion's closed dependency list,
selected schema digest and manifest edge must select the actual 1.5 validator.
Recomputing an SCF cannot authorize a predecessor validator or changed row.

AI 1.5 accounts for 27 types, six branches, 240 qualified producer definitions,
215 BLOCKED entries, 26 inherited literal-copy labels, and 54 identity recipe
definitions across 18 entity/proposition types. The nine relationship/value
types do not acquire these entity-envelope recipes or synthetic roots.

The admitted operations are `literal_alias_join`, `literal_entity_uri` and
`uuidv7_unix_milliseconds_to_rfc3339_utc`. Their complete meaning belongs to the
exact AI 1.5 recipe resources. There is no alias/namespace/time fallback,
normalization, generated owner, identity reminting or additional semantic owner.
Valid out-of-range identity time and missing provider qualification remain
Unavailable; independently invalid identity remains Rejected.

Each required-output evidence destination now identifies its producer kind,
actual rule ID and qualified rule, plus the exact catalog destination-definition
resource/digest/selector. Each unit identifies its actual source schema and
output branch. Catalog/schema, recipes/schema and inherited local-rule authority
are separately qualified. Inherited `literal_string_copy` uses the published
`local_rule` binding to actual AI 1.4 `/operation`; it is never relabeled as an
AI 1.5 operation. Other inherited rules retain their actual AI 1.3 identities.

Five independently evaluated checks remain: `source_and_identity`,
`applicability_and_context`, `inputs_and_types`, `exact_operation`,
`complete_output`. Each has exactly `verified`, `invalid`, `unavailable`,
`not_evaluated`; a caller boolean is not equivalent evidence. A complete claim
requires every check verified, every applicable destination accounted for and
no applicable BLOCKED or competing destination.

Schema acceptance checks shape and exact authority references. It cannot prove
that asserted checks actually occurred. Original sealed source, established
identity/provider, applicable branch conditions and complete output must be
independently reconstructed and compared. A schema-valid assertion does not
become an instance output or Constructed result. Whole-model NM 2.5 validation,
independent complete expected/observed ledgers and whole-ledger equality remain
separate mandatory proofs. Neither representation verification nor semantic
equality substitutes for the other. Original semantic values remain significant
once at their actual dispositions.

## Independent qualification and conformance

```powershell
python scripts/generate_semantic_contract_assets.py --publish-acc15-only
python scripts/qualify_acc15_publication.py
python -m pytest tests/test_authoring_construction_v15_publication.py
python tests/pr_scoped/qualify_acc15_publication.py --base <actual-base> --head <actual-head>
```

The independent qualifier imports no successor generator builders. It qualifies
the unchanged AI 1.5 authority, pinned historical definitions/closures and each
permitted successor edit. It checks all 240 producer alternatives individually,
actual inherited/local rule resolution, binding/schema edges and every frozen
conformance qualification. Counts are derived regression expectations, not proof.
Per-run snapshots reuse only digests of actual read resource contents and are
discarded after each audit; unverified fingerprints never establish a snapshot.

JSON Schema validation resolves only verified supplied resources. Every own
schema and transitively selected schema fragment is checked, including required
NM 2.5 and inherited ledger branches. Unused historical schemas are integrity
qualified without retroactively changing frozen historical publication criteria.
For example, an unused NM 2.3 reference does not become an NM 2.5 authority;
selecting that invalid fragment in the required graph fails closed. Evaluation
IDs are internal and do not alter published schema bytes or rule identities.

There are **555 new ACC15 authority-only cases**, with independently derived
coverage: 27 types/branches, 160 inherited producer definitions, 54 new recipe
definitions, 26 inherited labels, 215 BLOCKED destinations, nine recipe
exclusions, three recipe authorities, two exact authority selections, 43
negative qualifications and 16 independent construction obligations.

All **263 ACC14 cases** remain individually qualified historical references with
their original assertions. Historical enclosing selections and the old 269
BLOCKED entries remain historical facts; they are not relabeled successor
requests or runtime success. No frozen case claims executing construction.

Permanent candidate tests independently qualify the current definition, exact
closure, canonical/package byte parity, deterministic regeneration and mutation
rejection, including validly recomputed unauthorized SCFs. They do not freeze a
candidate's SCF or bytes at a previous development merge. The original
`6ddc8c2b6d66531ff3ecefb0bba7b15616ac4f0c` AI/ACC definitions and complete
closures are separately reproduced from Git. Released compatibility is checked
against the actual retained wheel/npm evidence by release-authority admission.

ACC selects the current maintained AI definition and requires it to match the
independently qualified definition. Its expected fingerprint is derived from
that source revision, rather than a permanent candidate compatibility constant.
A source definition, its distributed views and the selected dependency cannot
silently disagree. Missing canonical AI/ACC inputs cannot be replaced by stale
flattened outputs.

The separate PR-scoped tool takes explicit base/head and protects files outside
the declared change inventory. This is not a permanent comparison with that base.
The enclosing-selection and validation-selector migrations above are implemented.
Actual inherited rule provenance and historical snapshot verification remain
necessary; remaining ACC ledger/schema-helper dependencies are a separate target.
Removing candidate snapshots alone does not establish semantic replacements.

## Remaining boundary

All 215 static BLOCKED destinations and eleven categories remain: fingerprint
preimage, source envelope, completeness, custom lifecycle, declaring context,
shared identity, relationship branch/envelope, nonselected output, owner-local
context and custom qualification. Static authority and instance applicability
are distinct. Applicability remains Unknown, complete interpretation Unavailable.

No Rust/WASM/runtime/protocol or public capability change, NM materialization,
semantic equivalence, Constructed, persistence, admission or promotion is enabled.
Human publication acceptance and later bounded execution are separate gates.
