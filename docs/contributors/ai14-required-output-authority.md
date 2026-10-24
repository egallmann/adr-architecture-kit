# AI 1.4 required-output authority publication

AI 1.4 selects Authoring 1.7 and NM 2.5. This is publication authority, not an interpreter or a schema-complete materializer. ACC 1.4 is not published by this change.

## Exact closure

`scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7` commits 60 resources: the unchanged 52-member AI 1.3 closure, its exact definition, ADC 1.1 contract/schema, and five new resources. Only `architecture-interpretation/1.4/conformance` is a frozen normative conformance member.

New canonical resources under `contracts/architecture-interpretation/v1.4/resources/`:

- `required-output-derivations.json` and its closed companion schema.
- `rules.json`, importing the actual AI 1.3 authority and precisely refining representation duplication.
- `conformance.json` and its closed envelope schema: 85 authority-only cases.

Unchanged field dispositions, lifecycle ownership, contextual facts, detached context, source decoding/mapping and their dependencies retain their existing resource identities and digests. An inherited ownership rule continues to carry its actual AI 1.3 rule qualification; the enclosing AI 1.4 definition is qualified separately. There is no version rewriting or self-referential SCF.

## Accounting

The table counts publication entries, including conditional destinations. It does not count completed semantic units. A qualified producer definition contributes no instance coverage until all schema, identity, source and contextual prerequisites independently qualify. An inapplicable conditional field is not manufactured. BLOCKED has no producer. Nested required members belong to their complete parent value producer once; their exact selectors are separately audited.

| Semantic type | Output branch | Qualified producer definitions | BLOCKED destination entries |
|---|---|---:|---:|
| `adr/logical` | regular | 8 | 13 |
| `adr/physical-component` | regular | 8 | 13 |
| `adr/physical-system` | regular | 8 | 13 |
| `entity/boundary` | regular | 10 | 12 |
| `entity/capability` | regular | 10 | 12 |
| `entity/component` | regular | 9 | 13 |
| `entity/contract` | regular | 9 | 13 |
| `entity/data_flow` | regular | 14 | 10 |
| `entity/decision` | regular | 9 | 13 |
| `entity/evidence_expectation` | regular | 11 | 10 |
| `entity/extension` | regular | 10 | 14 |
| `entity/gap` | regular | 9 | 13 |
| `entity/implementation_decision` | regular | 9 | 13 |
| `entity/interface` | regular | 9 | 13 |
| `entity/invariant` | regular | 9 | 13 |
| `entity/normative_proposition` | normative-proposition | 10 | 10 |
| `entity/system` | regular | 8 | 13 |
| `entity/system_boundary` | regular | 11 | 12 |
| `relationship/calls` | compatibility-relationship | 1 | 7 |
| `relationship/depends_on` | compatibility-relationship | 1 | 7 |
| `relationship/extension` | canonical-relationship | 7 | 4 |
| `relationship/publishes_to` | compatibility-relationship | 1 | 7 |
| `relationship/reads_from` | compatibility-relationship | 1 | 7 |
| `relationship/subscribes_to` | compatibility-relationship | 1 | 7 |
| `relationship/writes_to` | compatibility-relationship | 1 | 7 |
| `value/normative_force` | proposition-owned-value | 1 | 0 |
| `value/topology_component` | owner-local-value | 1 | 0 |

**Totals: 186 qualified producer definitions; 269 BLOCKED entries.** The 26 new type-scoped label rules all use the single `literal_string_copy` operation. Existing authored title/name/summary placements are retained. System summary is alias-name label duplication only, without substantive narrative.

Every output branch retains its exact schema, required and conditional constraints, local/relative reference closure and nested requirements. Canonical relationships, compatibility records, proposition-owned values and owner-local values have distinct branches. Catalog membership never authorizes independent root construction.

## Blocker register

| Prerequisite | Missing qualification |
|---|---|
| `alias_ref_recipe` | Exact alias_ref composition format is not uniquely selected by accepted forward authority. |
| `uri_recipe` | Exact generated entity URI template/encoding is not uniquely selected; detached locators are not entity URIs. |
| `created_at_encoding` | UUIDv7-derived time is authorized in principle; exact NM created_at encoding/precision is not uniquely selected. |
| `fingerprint_preimage` | Exact entity_fingerprint canonical preimage and exclusion domain require qualified authority; historical hashes do not select it. |
| `source_envelope_recipe` | Source facts are governed, but this complete NM envelope field has no uniquely selected representation recipe. |
| `completeness_recipe` | Entity-specific completeness representation/criteria need an exact qualified recipe, not model-complete assertion. |
| `custom_lifecycle` | No accepted custom-entity lifecycle owner/value rule exists; existence_state is not lifecycle_stage. |
| `declaring_context` | Native standalone representation does not supply unique declaring ADR lifecycle provenance. |
| `shared_identity` | Coalesced shared system identity cannot activate competing producers; exact applicability must resolve first. |
| `relationship_branch` | Entity-named inherited placement does not by itself qualify the canonical-relationship output branch. |
| `relationship_envelope` | Complete relationship record/envelope or generated identifier recipe is not selected by forward authority. |
| `nonselected_output` | No qualified producer for this conditional destination under this type/source branch. |
| `owner_local_context` | Governed owner identity, topology key and multiplicity must be independently qualified; no independent root. |
| `custom_qualification` | Exact selected CEC registry/custom contract and properties must qualify; CEC closure is not registry selection. |

A successor catalog may close a blocker only through exact existing authority or an accepted narrow refinement. Missing owners remain unavailable; references, paths and traversal order do not establish ownership. CEC closure is not custom registry selection. Proposition lifecycle remains absent.

## Independent obligations

- Source-field coverage remains the unchanged five-class inventory. Required-output coverage is separate.
- Exact label reconstruction detects changed output even with intact source semantics. Complete semantic equality must also detect missing/changed original values; neither verification substitutes for the other.
- Qualified context requires independently verified declaring ownership, source status and the original lifecycle carrier schema. Carrier assertions are not proof.
- Generated URI/time/fingerprint/envelope recipes remain BLOCKED where exact forward authority does not select a unique operation. Historical fallback implementations are not authority.
- Complete NM entity/record validation, sealed source verification, interpretation and whole-ledger equality remain future execution obligations.

## Qualification and regeneration

```powershell
python -m scripts.qualify_ai14_publication
python scripts/generate_semantic_contract_assets.py --publish-ai14-only
python -m pytest tests/test_architecture_interpretation_v14_publication.py
python scripts/run_pr_feedback.py
```

The isolated generator verifies historical closures before assembling this successor. It writes only AI 1.4 definition/resource mirrors. Python exact lookup and Node packaged lookup expose authority without altering the selected SCS or capability handshake. Publication tests include installed-wheel discovery, mutation failures, deterministic regeneration and historical Git preservation. No frozen authority or runtime resource is regenerated.

## Next boundary

After human publication review, ACC 1.4 publication may select this exact authority and unchanged NM 2.5. Runtime materialization is a separate slice and must honor every unresolved prerequisite; no Constructed or semantic_equivalent capability is enabled here.
