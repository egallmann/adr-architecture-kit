# ADR-Kit 0.11.0 — Approved Semantic Design Lock (R1)

Review date: 2026-09-09  
Primary owner: adr-architecture-kit  
Upstream semantic owner: ste-spec  
Downstream integration owner: ste-runtime-private  
Disposition: **APPROVED DESIGN LOCK. The supplied plan is superseded where refined by R1. Repository-local ADR and contract promotion remains required before implementation authority exists.**

This is the approved design-state authority for planning the ADR-Kit 0.11.0 promotion and implementation slices. It locks the architectural decisions and boundaries stated here. It does not itself amend an ADR, allocate canonical NP identities, change an executable contract, authorize publication, or assert that implementation conformance has been demonstrated. The three supplied artifacts remain unchanged and are subordinate to this R1 refinement where they differ.

## 1. Executive judgment

The proposed release has a coherent purpose: make structured architectural intent first-class, exactly interpretable, historically qualified, and consumable through peer host SDKs.

Its strongest architectural choice is the separation of source authority, interpretation, retained realization, and downstream binding. Keep that choice. First-class NormativeProposition, exact semantic-contract sets, and detached materialization belong in one architectural target, implemented through bounded slices.

The supplied promotion-ready plan was not lock-complete unchanged. Several details labelled as implementation matters determine observable meaning. R1 closes those details so that two diligent implementers are not permitted to produce incompatible results while each appears to follow the design.

The material corrections are:

1. Pin the rules that turn source into meaning, not only the output model and force vocabulary.
2. Distinguish deterministic structural validation from judgment about natural-language normative meaning.
3. Give NP a normalized representation that cannot acquire an independent lifecycle through the shared entity envelope.
4. Preserve complete source acquisition, artifact-to-contract bindings, identity maps, and source capability coverage.
5. Define exactly what fingerprints compare, and distinguish contract conformance from reproduction of an earlier implementation's result.
6. Separate immutable semantic definitions from changing lifecycle and compatibility qualification.
7. Make attribution validation consume the pinned materialization rather than reopening mutable source.
8. State the release's deliberate limit: first-class NP representation is not automatically NP-target attribution support.

R1 needs no new deployed system, Runtime ontology, universal predicate language, general conflict solver, or new physical component. It recommends one additional **semantic contract family**, architecture-interpretation, because the transformation rules need an exact identity of their own.

### Plain-language reading

Keep the exact ingredients, the exact recipe, and the result separately. A recipe identifier is not proof that yesterday's cook followed it correctly. A new cook producing a different result must not overwrite yesterday's record.

## 2. Evidence and authority baseline

### 2.1 Supplied design artifacts

| Reference | Artifact | Review role |
|---|---|---|
| P | ADR-Kit Semantic Authority and Materialization — Promotion-Ready Design Plan | Lead design. Explicitly targets 0.11.0, authoring 1.6, normalized 2.3, normative-semantics 1.0, and slices A–I. |
| J | ste-runtime-adr-kit-authority-materialization-design-journal | Refined PD-01–PD-18 direction, historical materialization, contract-set assembly, and remaining physical-topology decision. |
| O | Cross-Repository Architectural Authority Materialization Design Journal | Original seam rationale, artifact-contract mapping, explicit failure/coverage semantics, and materialization-aware binding integration. |

P refines the earlier 2.2 consumer target to 2.3. It also changes the treatment of source-only revision changes: semantic payload reuse does not make two differently sourced historical realizations the same record. Where P omits a protection present in O, omission is not evidence that the protection was intentionally rejected.

### 2.2 Repository facts observed

| Repository / line | Observed basis | Relevant result |
|---|---|---|
| ADR-Kit released 0.10.1 | a580f034a54f74d283490650a90bd85258b3fa15 | Published compatibility baseline identified by the release tag. |
| ADR-Kit develop | 2b4bfeb8ece639ecaa8026a0f68e354c07157165 | Contains the 0.10.1 post-release synchronization and guard; it is four commits ahead of the 0.10.1 tag and is the observed base for the first 0.11.0 slice. |
| STE-SPEC develop | a096e4e7aa7ec7283583af9a1e6fdc65e74a713b | Does not contain the new governed-reasoning foundation ADR. |
| STE-SPEC semantic-rebaseline feature | e21b8409f09d01be419db09d979ce924a92e3777 | Contains ADR-L-0044 with status accepted, promoting FD-01/FD-01-R1 and SD-01–SD-05. It explicitly does not promote CE-01. Branch admission remains distinct from an accepted marker in a feature file. |
| Runtime develop | 741c8ad87b5b87a2d3e90edbf47de5b585a0affd | Existing authority already separates external validation, Runtime mapping, binding admission, and immutable Snapshot history. |

These are review snapshots, not an assurance that branches cannot subsequently move. Re-resolve branch heads before promotion.

Primary repository evidence used:

- [ADR-Kit ADR-L-0013: repository/model boundary](https://github.com/egallmann/adr-architecture-kit/blob/f1df12cb1cdb63b444f9cf80715241800096948d/adrs/logical/ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.yaml)
- [ADR-L-0019: canonical identity, fingerprints, and sealed migration](https://github.com/egallmann/adr-architecture-kit/blob/f1df12cb1cdb63b444f9cf80715241800096948d/adrs/logical/ADR-L-0019-canonical-entity-identity.yaml)
- [ADR-L-0025: contract succession](https://github.com/egallmann/adr-architecture-kit/blob/f1df12cb1cdb63b444f9cf80715241800096948d/adrs/logical/ADR-L-0025-topology-and-contract-succession-authority.yaml)
- [ADR-L-0026: ADC discovery authority and explicit unresolved topology issue](https://github.com/egallmann/adr-architecture-kit/blob/f1df12cb1cdb63b444f9cf80715241800096948d/adrs/logical/ADR-L-0026-authoring-domain-contract-discovery-authority.yaml)
- [ADR-L-0027: peer-host construction and release parity](https://github.com/egallmann/adr-architecture-kit/blob/f1df12cb1cdb63b444f9cf80715241800096948d/adrs/logical/ADR-L-0027-public-binding-construction-and-release-parity.yaml)
- [Normalized 2.2 entity schema](https://github.com/egallmann/adr-architecture-kit/blob/f1df12cb1cdb63b444f9cf80715241800096948d/schema/normalized-model/v2.2/normalized-entity.schema.json)
- [Node linkage implementation](https://github.com/egallmann/adr-architecture-kit/blob/f1df12cb1cdb63b444f9cf80715241800096948d/packages/node/src/node/linkage.ts)
- [Evidence-attribution 1.6 vocabulary](https://github.com/egallmann/adr-architecture-kit/blob/f1df12cb1cdb63b444f9cf80715241800096948d/schema/evidence-attribution/v1.6/semantic-attribution-vocabulary.json)
- [Semantic-core 1.0 boundary](https://github.com/egallmann/adr-architecture-kit/blob/f1df12cb1cdb63b444f9cf80715241800096948d/contracts/semantic-core/v1.0/README.md)
- [STE-SPEC ADR-L-0044 on the promotion branch](https://github.com/egallmann/ste-spec/blob/e21b8409f09d01be419db09d979ce924a92e3777/adrs/logical/ADR-L-0044-governed-semantic-reasoning-foundation.yaml)
- [Runtime ADR-L-0008](https://github.com/egallmann/ste-runtime-private/blob/741c8ad87b5b87a2d3e90edbf47de5b585a0affd/adrs/logical/ADR-L-0008-external-intent-binding-and-authority-composition.yaml)
- [Runtime ADR-PC-0006](https://github.com/egallmann/ste-runtime-private/blob/741c8ad87b5b87a2d3e90edbf47de5b585a0affd/adrs/physical-component/ADR-PC-0006-adr-kit-authority-integration-and-external-binding.yaml)

The review read all three supplied design artifacts and a bounded selection of current authority, schema, and implementation surfaces. It is not a comprehensive audit of either codebase, nor a release-certification run.

## 3. Findings that change the lock

Severity here means impact on this design's promises, not a production incident classification.

| ID | Finding and concrete failure | Evidence | Required disposition |
|---|---|---|---|
| F01 — Critical | The proposed SCS contains normalized-model and normative-semantics, but does not explicitly commit to source decoding, normalization adapters, source selection, or materialization interpretation rules. The same set can otherwise acquire different meaning when an adapter changes. | P §§8, 10–12, 14 | Close interpretation authority transitively; recommended third family in §5. |
| F02 — Critical | SourceBasis contains an identity and revision but no closed acquisition manifest. Dirty working files, ignored configuration, missing files, or a changed identity map can affect output without changing the claimed revision. | P §15; O PD-04 | Introduce a verified, sealed source bundle and per-artifact qualification, §8. |
| F03 — Critical | Historical recovery assumes exact source plus SCS is sufficient even after a nonconforming implementation is corrected. A fixed implementation can correctly produce a different result under the same contract. | P §§16–18; J PD-14/PD-17 | Separate semantic conformance from realization replay; require retained-result comparison, §11. |
| F04 — High | NP forbids an independent lifecycle, while the existing normalized envelope requires lifecycle_stage. Blind envelope reuse would reintroduce precisely the semantics being excluded. | P §§5–6; normalized 2.2 schema | Discriminated NP representation; no synthetic active status, §6. |
| F05 — High | Materiality and unchanged natural-language meaning are presented as admission obligations without saying who decides them. A validator cannot infer these judgments merely from structured fields. | P §§5, 7; ADR-L-0044 INV-4403 | Separate semantic author review from mechanical validation; no silent NLP admission, §6. |
| F06 — High | sourceContractClosure loses O's artifact-to-contract mapping. Limitations identify a source version but not which declaration or covered source region is affected. | P §15; O PD-04/§6 | Restore artifact bindings and coverage-qualified capability facts, §§8–9. |
| F07 — High | The authority-state fingerprint has no fixed projection/preimage. Including paths/provenance prevents intended reuse; excluding all metadata can discard actual intent or epistemic limitations. | P §16; O §9 | Promote a new fingerprint contract and a separate semantic-payload digest, §10. |
| F08 — High | Compatibility is included in immutable semantic definitions but is expected to evolve. Pairwise compatibility also does not establish whole-set compatibility. Lifecycle-based test exclusions contradict the separate newUsePolicy axis. | P §§8, 12–13, conformance item 19 | Separate immutable semantics, explicit tuple qualification, and current-use policy, §7. |
| F09 — High | The materialization result has neither a success discriminant nor an explicit coverage contract. Invalid, unavailable, unresolved, and legitimately undeclared states could all become an empty model. | P §15; O §13 | Restore typed outcomes and preserve epistemic dimensions, §9. |
| F10 — High | Legacy source often lacks canonical UUIDv7 identities. Detached deterministic materialization cannot safely mint those identities on each call. | O reference corpus; P historical support; ADR-L-0019 | Require existing canonical identity or an exact sealed provider-authoritative map, §8. |
| F11 — High | Existing linkage calls openRepository(project_root), not the retained materialization. A run could bind against source that changed after acquisition. | P §20; O implementation slice 4; Node linkage implementation | Include a pinned-materialization evaluation seam, §12. |
| F12 — High | Current evidence-attribution 1.6 excludes normative_proposition from permitted targets; enforces is invariant-specific. First-class NP therefore does not automatically become a linkage target. | Released attribution vocabulary/schema | Explicit release decision, §12. No silent mutation of 1.6. |
| F13 — High | Host-native YAML parsing can change facts before the shared core receives them. A shared WASM binary alone does not prove end-to-end semantic parity. | P §14; current core boundary | Pin parsing/adaptation semantics and test from raw source, §13. |
| F14 — High | Promotion could require authoring 1.6 before the released tooling can validate it. Also, an accepted feature-file marker does not itself resolve upstream branch admission. | P §§2, 27–28; current STE-SPEC branches | Explicit bootstrap and promotion sequence, §15. |
| F15 — Medium | “MAY(P) implies no applicable MUST NOT(P)” can be misread as permission to erase an observed prohibition. It is not a rewrite rule for conflicting declarations. | ADR-L-0044 DEC-4406/INV-4406 | Preserve conflicting declarations; scope the claim to coherent authoritative interpretation; no precedence inference, §6. |

### 3.1 Two bounded baseline corrections

These do not justify reopening the wider STE semantic re-baseline:

- STE-SPEC ADR-L-0044 INV-4405 and INV-4406 each place the containing ADR UUID in upheld_by_decisions. A read-only comparison with that ADR's decision IDs confirmed those two non-decision references. Correct the intended decision targets during the upstream admission review; do not guess replacement targets from position.
- ADR-Kit ADR-L-0026 records ADC-RECON-001 for consumes_interface. The 0.11.0 materialization qualification must not silently decide that unresolved authoring/derived distinction. Give exercised cases an explicit supported/rejected disposition, or make a bounded owning-authority correction if release fixtures require it.

## 4. R1 release objective and authority boundary

### Proposed release objective

ADR-Kit 0.11.0 shall provide first-class ADR-scoped NormativeProposition representation and a source-grounded, detached materialization contract whose exact interpretation basis, canonical identities, limitations, and historical realization can be verified through equivalent Python and Node host operations.

The release shall also provide the supported boundary needed to validate existing attribution semantics against that immutable materialization.

### Authority is not a single upward precedence ladder

| Responsibility | Owner | This release must not imply |
|---|---|---|
| STE-wide force, NP/Invariant distinction, authority/effectivity/applicability separation | Accepted STE-SPEC authority | ADR-Kit invented or owns global normative theory. |
| Concrete project intent | The competent, effective project ADR source for its boundary | A package's successful parser confers governance competence. |
| ADR representation, interpretation contracts, and canonical executable interpretation | ADR-Kit | Runtime or independent host implementations can redefine ADR meaning. |
| Retention identity, reconstruction, binding admission, Snapshot publication, composite queries | Runtime | Copying or traversing intent transfers its authority. |
| Semantic materiality or meaning-preserving editorial judgment | Competent author/reviewer under the governing process | A schema validator or content hash proves natural-language equivalence. |
| Broader implementation conformance assessment | Its separately designated authority | Materialization or linkage success is a conformance verdict. |

The Rust/WASM core is the canonical executable realization of promoted ADR-Kit semantics, not a source capable of overriding those semantics. A conflict between implementation and governing contract is a defect to classify, not automatic contract evolution.

## 5. Close the interpretation recipe

### 5.1 Recommended contract inventory

| Contract | Role | SCS membership |
|---|---|---|
| authoring-contract 1.6 and explicitly qualified historical source contracts | Source representation and source-local meaning | Not one top-level member; exact supported dependencies and encountered artifact bindings remain pinned. |
| normalized-model 2.3 | Consumer record shapes, type rules, relationships, semantic field projections | Yes |
| normative-semantics 1.0 | ADR-Kit's faithful representation of the accepted STE normative model | Yes |
| **architecture-interpretation 1.0** | Source interpretation/adaptation, identity-map use, declaration qualification, absence/coverage handling, and materialization rules | **Yes, recommended addition** |
| architecture-materialization 1.0 | Public request/result envelope | No; recorded separately. Any meaning-affecting behavior must reside in a participating semantic contract. |
| semantic-core transport 1.1 | Shared execution request/response transport | No; recorded as execution provenance. |
| architecture-materialization@1.0 profile | Participating-family constraints and explicit current selection | Not a second source of interpretation rules. |
| Existing attribution/evidence contracts | Claim vocabulary and validation meaning | Separate linkage-evaluation basis, not silently folded into the architecture SCS. |

The extra family is a versioned contract value, not a new canonical semantic entity or physical component. It does not require UUID identity.

### 5.2 Interpretation closure law

Every behavior capable of changing a successful normalized semantic result, its governed diagnostics, or its knowledge qualification must be determined by:

1. exact participating semantic definitions and their immutable dependencies; or
2. an explicit, retained input in the source/request basis.

No third source of meaning is allowed through host defaults, mutable registry policy, current selection, local configuration, directory traversal order, or undocumented decoder behavior.

The interpretation contract pins the supported source-contract references and mappings. Encountered sourceContractClosure is the actual subset used, not a substitute for the rules that interpret that subset.

For historical source labels whose exact meaning was not uniquely identified by a version string, qualification must explicitly choose the imported contract artifact. A source document's schema_version is not retrospectively proof of which historical bytes were used.

### 5.3 Design alternatives

| Option | Benefit | Cost / risk | Recommendation |
|---|---|---|---|
| Add architecture-interpretation as an SCS member | Names a real semantic responsibility; mapping changes can evolve without pretending the output shape changed | One additional contract family and qualification axis | **Adopt** |
| Put the complete immutable interpretation closure inside normalized-model 2.3's fingerprinted definition | Fewer named families | Couples model shape to every source adapter and materialization behavior; future changes may force misleading model succession | Valid only if explicitly chosen and fully specified |
| Leave interpretation in implementation/profile defaults outside all fingerprints | Small initial artifact surface | Exact recipe promise is false | Reject |

The ambiguity is closed. The separate architecture-interpretation family is approved by this lock.

### 5.4 Pure profiles

Profiles may govern supported composition and current selection. They must not alter interpretation of an already identified set.

If a future profile would change output under the same members, its semantic rules must become a fingerprint-covered contract constituent or require a successor identity scheme before publication.

There must be at most one member per participating family, with no missing or undeclared extra member in the initial profile.

## 6. NormativeProposition without hidden semantic inference

### 6.1 Preserve the proposed authoring fields

Keep the bounded authoring shape:

    id: UUIDv7
    alias_id: NP-####
    alias_name: governed semantic alias
    statement: non-empty normative statement
    normative_force: MUST | MUST NOT | SHOULD | SHOULD NOT | MAY
    scope: non-empty declared scope
    rationale: optional explanatory text

Keep ADR-L, ADR-PS, and ADR-PC as permitted declaring parents. Do not broaden Invariant parentage or invent a promotion lifecycle between NP and Invariant.

NP and Invariant remain peer semantic entity types. Force, importance, scope, or an implementation's interpretation must not convert one into the other.

Do not add NP status, independent effectivity, applicability, waiver, exception, polarity, materiality flags, or compulsory lineage fields.

### 6.2 Two different acceptance responsibilities

**Semantic authoring review** establishes whether the statement is independently material, the force matches the intended meaning, and an edit preserves or changes meaning.

**Deterministic validation** establishes the promised mechanical properties: field shape, permitted force, UUID/alias grammar, parent kind, uniqueness, ownership, declared references, and absence of forbidden fields.

A successful deterministic validation must not be reported as proof of semantic materiality, consistency of arbitrary prose, or equivalence of two wordings. Existing review/promotion evidence is sufficient; this release need not invent a generic assessment subsystem or a per-NP self-certification field.

The distinction is already supported by STE-SPEC ADR-L-0044 INV-4403, which assigns materiality verification to design/manual review.

### 6.3 Statement and force are not two operators

The statement carries the normative text; normative_force classifies its intended force. It is not a machine-applied logical operator over an executable string predicate.

For example:

    normative_force: MUST NOT
    statement: Runtime MUST NOT independently parse ADR source contracts.

This must not be interpreted as double negation. Conversely, if text and force conflict, schema success does not settle the semantic disagreement. The author/reviewer must correct it. Independently meaningful clauses with different forces should be authored as separate propositions.

### 6.4 Identity and declaration ownership

Within one provider materialization, one NP UUID has one canonical declaring ADR. Duplicate canonical definitions are an error even when their text happens to match. References do not constitute duplicate definitions.

An editorial move may preserve identity only when governed meaning is preserved. Moving a proposition to a parent with different competence, scope, or effectivity is not automatically editorial. Cross-provider relocation must preserve the distinction between the old and new qualified identities.

A materially changed normative meaning requires a new NP identity. An editorially changed statement may preserve UUID only when competent review establishes meaning preservation, while still changing its content fingerprint. A stable UUID does not certify unchanged content.

### 6.5 Discriminated normalized envelope

Normalized model 2.3 must admit an NP-specific variant. It must not require or synthesize lifecycle_stage on that variant.

The NP variant preserves:

- canonical identity, authoritative type, governed aliases;
- statement, canonical force, and declared scope;
- qualified declaring ADR identity;
- exact source artifact/contract qualification and structural provenance;
- applicable common identity/provenance fields whose meaning genuinely applies.

The declaring ADR's source lifecycle remains available through the referenced ADR record. It is not copied into an independently mutable NP lifecycle.

Existing normalized entity variants retain their existing semantics. A blanket redesign of every entity's lifecycle is not required. If a uniform read view exposes an inherited declaration qualification, its name and contract must explicitly identify the parent-derived basis rather than presenting an NP lifecycle.

Where common presentation fields are required, their derivation must be fixed and non-inferential. UUID-derived creation time follows existing identity authority; the materializer must not insert wall-clock creation time.

### 6.6 Governing participation and applicability

Presence in a model is not proof of current governing authority. Proposed, historical, superseded, and effective declaring source states must remain distinguishable. Do not silently filter source into a supposedly authoritative subset without a promoted selection rule.

For the initial scope representation:

- global means the whole *already bounded declaring authority scope*, not all repositories, all systems, or all time;
- other scope strings remain opaque declared values;
- unknown scope interpretation is not global and not DOES_NOT_APPLY;
- missing required scope is a validation error, not an invitation to invent inherited scope;
- no contextual applicability evaluator is advertised in 0.11.0 unless separately promoted.

The accepted tri-state applicability distinction is preserved for future contextual evaluations. Materialization itself has not evaluated a context merely because it can carry scope.

### 6.7 Conflict posture

Representing MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY does not authorize a universal theorem prover or precedence engine.

MAY must not erase a retained MUST NOT. Neither document order nor modal strength chooses the winner. Any mechanically detected conflict must be qualified by the comparison actually performed; arbitrary prose that was not assessed remains unassessed.

The upstream permission implication is a consistency characterization of a coherent governing interpretation, not an instruction to suppress contradictory input. If the owning upstream wording is judged ambiguous, clarify it in that owner rather than redefining MAY inside ADR-Kit.

## 7. Contract registry, fingerprints, and qualification

### 7.1 Immutable definition versus changing policy

Use an immutable SemanticContractVersion definition and a separately revisioned catalog/policy record. A returned public view may compose them, but its mutable catalog portion must remain visibly outside semantic identity.

| Change | Definition fingerprint | Existing SCS | Current-use policy |
|---|---|---|---|
| New normative meaning or changed normalization rule | New semantic contract version/fingerprint | New set if selected | Explicit decision |
| Deprecation label | Unchanged | Unchanged | May remain allowed |
| newUsePolicy becomes prohibited | Unchanged | Existing historical set retained | Excluded from new use as explicitly defined |
| Additional test demonstrating existing meaning | Unchanged | Unchanged | Additional qualification evidence |
| New support qualification for an already defined exact combination | Definitions unchanged | Determined by composition | New explicit qualification record |
| Correct an implementation that violated the frozen contract | Unchanged unless meaning is also changed | Unchanged | New execution qualification; historical mismatch handled explicitly |

Do not encode “deprecated implies prohibited.” The supplied plan's conformance item 19 must be corrected to test newUsePolicy separately from lifecycle.

### 7.2 Semantic-definition closure

Fingerprint-covered resources must be enumerated, content-addressed, and closed over exact dependencies. Unversioned URLs, live schema fetches, current aliases, implicit imports, and unresolved resource references cannot determine historical meaning.

Avoid self-referential hashes and cycles in the digest dependency closure. Define canonical resource keys and a deterministic dependency closure. Do not hash a generated artifact that contains its own final digest. This does not prohibit cycles in authored semantic relationships where their own contract allows them.

Define which assertions are frozen normative conformance content. New regression fixtures and test-run evidence that demonstrate already-defined meaning belong outside the immutable semantic definition. Otherwise adding a useful test would force a fictitious semantic version change.

Historical authoring 1.0 had a backward-compatible evolution policy. Registry bootstrap must explicitly reconcile that policy with new immutable interpretation references. Do not claim every historical artifact carrying the same source version label had identical bytes or an already-existing SCS.

### 7.3 Canonical hash mechanics

Retain the proposed scf:v1:sha256 and scs:v1:sha256 schemes, but give each preimage a closed schema and a distinct domain marker.

For SCS, retain composition-only identity:

    {
      "scheme": "adr-kit.semantic-contract-set/v1",
      "contracts": [
        {
          "semanticContractFamily": "...",
          "semanticContractVersion": "...",
          "semanticContractFingerprint": "..."
        }
      ]
    }

Use exact lower-case ASCII family identifiers, recommended grammar `^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$`, and lexicographic ASCII ordering by family. Version strings and fingerprints are exact qualified values, not ranges; do not infer compatibility from SemVer. Reject duplicate families before construction of a map can overwrite one. Canonical JSON then handles object-property ordering; it does not make an unordered array canonical.

RFC 8785 preserves array order, orders object keys using UTF-16 code units, does not perform Unicode normalization, and constrains input including duplicate names and number representation. Sorted dictionaries plus ordinary JSON serialization are not a complete implementation. Use conformance vectors for these cases. [RFC 8785, §§3.1–3.2](https://www.rfc-editor.org/rfc/rfc8785.html#section-3.1)

Reject unsafe numeric coercion before information is lost. Use existing contract-authorized representations for large values; do not silently convert a number into a string. Treat Unicode normalization as an explicit semantic decision, never an incidental hashing cleanup.

Digest equality is an integrity mechanism under the collision-resistance assumption, not proof of authority or philosophical semantic equivalence. If different canonical preimages are detected under one identity, fail integrity validation rather than choosing a winner.

### 7.4 Compatibility is an explicitly qualified relation

Compatibility must be directional and operation-qualified where direction or operation matters.

For the initial small profile, use explicit **whole-tuple qualification**, including exact fingerprints. Missing qualification means unsupported, not probably compatible. Pairwise compatibility of A/B, B/C, and A/C does not establish compatibility of A/B/C.

Interpretation rules belong inside the semantic closure. Permission to publish/use a particular exact combination is a separate governed qualification record. A later registry policy must not rewrite an old tuple's meaning.

Assembly may be specified as a Cartesian product filtered by authoritative declarations, but implementations may evaluate an equivalent deterministic join over qualified tuples. Do not require constructing an exponentially large intermediate collection merely to comply with the prose.

Repeated assembly with identical authoritative inputs must leave an empty repository diff. Emit only missing, qualified immutable artifacts; validate the full retained corpus for duplicate identities/compositions, conflicting definitions, dangling references, and integrity failures. Do not rewrite historical artifacts merely to refresh formatting or generation timestamps.

### 7.5 Historical corpus and current selection

Validate historical sets against their exact semantic definitions and retained qualification, not against today's new-composition policy.

Once a set is published for durable reference, conservatively treat it as externally used. The producer cannot reliably discover every downstream reference before deleting historical support.

Expose separately:

- catalogued;
- executable by this installed release;
- permitted for new use;
- supported for historical interpretation.

An explicit current pointer resolves to one exact, executable, qualified set. Resolve it before materialization/reconstruction and retain that ID. A pointer change during a run cannot change the run's basis.

Historical addressability is not a promise that every arbitrary schema tuple will execute. A release must advertise the exact supported domain honestly.

## 8. Exact source basis and identity

### 8.1 Sealed source acquisition

The semantic operation consumes a sealed source bundle. A filesystem-oriented convenience API may acquire it, but successful output must be based on one verified bundle, not a moving sequence of file reads.

The basis must identify:

    provider qualification
    source selection / scope definition
    source acquisition kind
    exact source revision when applicable
    source bundle digest
    artifact manifest
    pinned configuration and identity-map inputs

The manifest records every interpretation-relevant input's logical locator, content digest, role, and relevant boundaries. Project metadata, source selection configuration, referenced contract inputs, and sealed identity maps cannot remain invisible side inputs.

Read-only means no source mutation, identity allocation, implicit migration, generated-bundle rewrite, or arbitrary code execution. Temporary host buffering is not canonical output.

### 8.2 Revision truthfulness

A branch name is a selector, not an immutable revision. A Git commit is a sufficient source reference only for the content actually verified against it.

For an uncommitted workspace, retain a sealed content-bundle identity and label the acquisition accordingly; do not claim it was exactly the Git commit at HEAD. For a historical Git acquisition, read a consistent immutable tree or verify all selected bytes against the declared revision.

If acquisition detects drift, missing declared inputs, symlink escape, provider mismatch, or an incomplete selection, fail explicitly. An in-memory DTO assembled from unrelated source moments is not a verified repository revision.

This release need not implement a Git clone service or universal source store. The caller/host may provide an already pinned workspace or bundle.

### 8.3 Artifact-to-contract bindings

Retain, for every interpreted source artifact:

    artifact locator and content digest
    exact qualified source contract reference
    declaration/entity provenance as applicable
    source capability qualification

sourceContractClosure is the canonically ordered unique set of encountered source contract references, derived from those artifact bindings. It must not be populated from the package's entire supported-version inventory.

### 8.4 Legacy identity boundary

Detached materialization must not mint canonical UUIDv7 identity.

UUID-native source can be materialized directly. Legacy identity-bearing source can enter a canonical 2.3 materialization only when a complete, unambiguous, sealed provider-authoritative identity map supplies the required identities. The exact map belongs in the source basis.

If no such map exists, return a typed identity-qualification failure. Do not generate a new UUID per run, disguise a hash as a UUIDv7, infer identity from a path, or let Runtime repair the problem.

This qualifies the earlier “no migration required merely for consumption” statement: a complete source rewrite is not inherently required, but authority for canonical identity is required. Preparing that authority is a separate governed authoring/migration action.

### 8.5 Provider qualification

Provider kind and architecture namespace must be checked against the configured provider qualification. Namespace syntax and hash validity do not authenticate ownership.

Independent providers retain separate qualified identities even when UUID bytes overlap. A workspace basis cannot contain two competing selections for one provider namespace and silently choose by path or discovery order.

## 9. Materialization outcomes and epistemic coverage

### 9.1 Result algebra

The semantic result is a discriminated union:

    Materialized
      exact source and interpretation basis
      normalized model
      artifact contract bindings
      coverage and capability qualification
      governed diagnostics
      semantic fingerprints / payload digest

    Rejected
      requested basis
      structured validation/support/identity diagnostics
      no snapshot-eligible materialization

    Unavailable
      requested basis
      operational acquisition/execution reason
      no fabricated empty model

Ordinary I/O or transport exceptions may remain idiomatic host errors with a documented mapping. An unsupported semantic combination must not become an indistinguishable generic exception.

### 9.2 Qualified completeness

Successful materialization means the complete *selected and declared* source boundary was processed according to the contract. It is not proof that all architecture has been documented.

A valid normalized model may contain contract-authorized unresolved references. Those remain first-class unknown/unresolved state; they do not automatically invalidate the materialization or become admitted relationships.

Invalid source, unsupported source semantics, incomplete acquisition, or silent loss of an input cannot produce a success-shaped partial authority model. A diagnostic preview, if exposed, must be structurally ineligible for retention as a successful authority basis.

### 9.3 Preserve separate epistemic dimensions

| Dimension | Examples | Inference prohibited |
|---|---|---|
| Acquisition | complete, unavailable, incomplete | Missing input means empty architecture. |
| Source expressiveness | expressible, not expressible | A legacy source asserts that a future concept does not exist. |
| Declaration within verified coverage | declared, not declared | Supported but undeclared means explicitly forbidden or absent in reality. |
| Reference resolution | resolved, unresolved | An unresolved endpoint is a negative implementation claim. |
| Governing participation | parent-qualified source state; contextual eligibility not evaluated where unknown | Inclusion in a materialization means effective, competent, applicable authority. |
| Assessment | unassessed unless a separately identified assessment exists | Schema validation proves conformance or semantic consistency. |

Expressiveness must be qualified at the source artifact/type/region where relevant, not flattened to a provider-wide yes/no label. A mixed 1.5/1.6 corpus can contain declared NPs in one source region and NP-inexpressible history in another.

For a valid 1.6 source, an omitted optional NP collection and an empty collection may both mean “no NP declared in this covered source,” according to the source contract. Neither is an assertion that the whole system has no normative obligations.

## 10. Fingerprints with explicit equivalence boundaries

### 10.1 Separate values

| Value | Answers |
|---|---|
| SemanticContractFingerprint | Which immutable semantic contract definition? |
| SemanticContractSetId | Which exact qualified contract composition? |
| SourceBundleDigest | Which verified interpretation inputs were actually read? |
| AuthorityStateFingerprint | Which basis-qualified canonical semantic-state projection? |
| SemanticPayloadDigest | Which complete deterministic public semantic payload, including explanatory provenance/coverage? |
| Execution artifact digest and release provenance | Which implementation actually produced the result? |
| Runtime materialization UUID | Which retained realization record? |
| Runtime storage-integrity digest | Are the retained storage bytes intact under that storage contract? |

These values may be grouped in existing DTOs. They are not eight new entities.

### 10.2 New authority-state fingerprint contract

Promote a new explicitly named portable scheme, for example asf:v1:sha256. Do not change the meaning of existing binding-local fingerprints in place.

Recommended preimage:

    {
      "scheme": "adr-kit.authority-state/v1",
      "provider": <canonical qualified provider>,
      "semanticContractSetId": <exact SCS>,
      "state": <closed canonical semantic-state projection>
    }

The projection must preserve all governed semantic content, canonical declaration ownership, source lifecycle information relevant to participation, unresolved semantic content, consumer semantic extension values, and capability/coverage qualifications that affect permissible inference.

Exclude only explicitly classified nonsemantic or occurrence-only fields: host absolute paths, acquisition timestamps, package provenance, source revision labels, raw source coordinates where they are only locators, and the output fingerprint fields themselves.

Do not delete all fields named metadata, provenance, or path. An authored implementation path or authority qualifier can be semantic. Every new field needs an explicit projection classification before the schema ships.

Order identity-keyed collections canonically using their promoted keys. Preserve authored sequences and multiplicity where they carry meaning. Existing entity-fingerprint rules are not rewritten by this new aggregate scheme.

Including SCS deliberately bounds comparison: a changed SCS changes this fingerprint even if visible statements look identical. That signals a changed interpretation basis, not proof that the project itself changed.

### 10.3 Content identity is not semantic equivalence of prose

Equivalent canonical state under the same provider/set derives the same fingerprint. A YAML comment edit can change SourceBundleDigest without changing the authority-state fingerprint. A code-only commit changes the exact revision-bearing source basis but need not change the source bundle digest when none of the selected interpretation inputs changed. The complete source-qualified payload still distinguishes those revisions.

Rewording a statement may legitimately preserve its UUID after review but change the fingerprint. The materializer must not use NLP to collapse paraphrases into one fingerprint.

### 10.4 Complete semantic payload digest

Define a separate deterministic projection containing the successful public semantic result, including exact source basis, artifact bindings, coverage, semantic diagnostics, and normalized payload. Exclude execution-specific provenance and the digest field itself.

Record the exact materialization/result contract and payload-projection scheme separately from SCS and include their qualification in this digest's domain-separated preimage. Recovery compares the retained result contract/projection, not an arbitrarily newer response envelope. A new envelope version does not silently redefine an old payload digest.

Define the diagnostic projection explicitly: stable code, severity, canonical affected identities/logical locations, structured parameters, and governed ordering. Host-local display messages, absolute paths, elapsed time, and execution timestamps remain in an excluded presentation/execution envelope. If human-readable text is included in the semantic projection, that text must itself be contract-governed and cross-host deterministic. Do not promise byte-equivalent payloads while permitting unspecified display text inside their digest.

This digest is the stronger test for lossless payload deduplication or historical result reproduction. AuthorityStateFingerprint alone is not sufficient to reuse provenance-bearing payload from a different source revision.

Runtime may internally deduplicate a canonical state chunk across realizations, but each retained realization must keep its own source-qualified envelope.

## 11. Historical conformance versus historical realization

### 11.1 The critical distinction

For a fixed materialization/result contract and its observable projection, let:

    B = sealed source basis, including exact auxiliary inputs
    S = exact SCS and its immutable interpretation closure
    M_S(B) = semantic result prescribed by the promoted contracts
    E = identified executable implementation
    R_E(B,S) = semantic result actually produced by E

A conforming execution satisfies R_E(B,S) = M_S(B) within the contract's stated observable equivalence. This is a normative obligation, not a claim that every released implementation has always satisfied it.

If E1 contained a defect and E2 corrects it, it is possible that:

    R_E1(B,S) != R_E2(B,S)

without S changing. Changing the contract merely to preserve an erroneous implementation would invert the authority boundary.

### 11.2 Historical recovery rule

Recovery requires exact source/provider/set and result-contract qualification, and comparison with the retained historical semantic payload digest and authority-state fingerprint.

- Exact qualified match: a new realization may be associated as an equivalent recovery.
- Correct contract execution but mismatch with historical output: report historical reproduction mismatch; do not silently replace the old result.
- Historical source or necessary identity map unavailable: report unrecoverable input basis; do not synthesize it.
- Same source under a different SCS: new interpretation, never recovery of the old one.

Record the actual shared-core artifact digest and package/host provenance. These explain which execution occurred; they do not become semantic-contract identity.

The contract-preserving path should support historical interpretation through current conformant releases. Archived executables are not the primary authority mechanism. Retained payloads remain essential when exact earlier *nonconforming* behavior cannot or should not be replayed.

### 11.3 Retention and equivalence association

Payload pruning must be governed by recoverability of source, semantic closure, and qualification evidence. Do not promise recoverability merely because a set ID was retained.

Recommended initial retention posture: preserve the last canonical payload referenced by a committed Snapshot; allow deduplication, cache eviction, and removal of redundant copies. Any later policy that discards that last payload must explicitly accept the possibility of unrecoverable historical realization after a discovered implementation defect. Source-plus-contract availability alone cannot justify a promise of lossless historical result recovery.

The original materialization identity and Snapshot reference remain immutable. Equivalent-realization associations are append-only records outside the immutable Snapshot body; queries expose both the original reference and the recovery used.

Source-only revision change produces a distinct source-qualified acquisition/realization envelope under R1, even where canonical state storage is reused. Multiple Snapshots may still reference the same already retained realization when that is the exact selected basis.

Historical observation/commit time and the source state's governing time are different concepts. Neither package release time nor query wall-clock time silently changes effectivity.

## 12. Close the materialization-to-binding seam

### 12.1 Required ADR-Kit capability

Existing attribution semantics must be evaluable through a supported public operation against a retained immutable materialization or an equivalently sealed supported model view, without reopening current project files.

The capability may extend the existing linkage facade. Exact method naming is not the architectural decision. Its input authority basis is.

It must:

- accept and validate the exact materialization basis;
- consume separately supplied evidence under its explicit evidence/attribution contract;
- execute existing claim semantics through the shared core;
- preserve per-claim valid, warning, and rejected outcomes;
- report the materialization and attribution interpretation basis used;
- remain distinct from Runtime embodiment identity mapping and binding admission.

Evidence contract/version, attribution vocabulary qualification, and linkage profile are retained separately from SCS. A legacy binding-local architecture_fingerprint must not be silently relabelled as the new portable authority-state fingerprint.

Old repository-based API calls may remain compatible convenience routes. Runtime's exact-history path must not depend on recreating a writable adrs/index tree or on accessing the present-day checkout.

### 12.2 First-class NP is not yet an attribution target

The released 1.5/1.6 vocabulary does not permit normative_proposition targets. In particular, enforces names Invariant enforcement.

**Approved 0.11.0 boundary:** ship NP authoring, representation, materialization, and querying; preserve current attribution target semantics; advertise NP-target attribution as unsupported.

This is an explicit deferral, not an implementation oversight. If directly attributing code to NP identity is part of the desired 0.11.0 acceptance demonstration, promote a successor attribution vocabulary/evidence contract and its exact verb-to-target matrix before implementation. That is a conscious scope addition, not a parser fix.

### 12.3 Runtime obligations preserved

Runtime observes attribution declarations independently of architectural intent. It evaluates them against the pinned materialization only afterward.

ADR-Kit validation does not resolve Runtime identity. Runtime mapping does not manufacture external validity. Successful binding does not prove conformance. A binding from an earlier Snapshot cannot bootstrap current binding admission.

The SDK release need not wait for the entire Runtime graph/facade implementation, but the ADR-Kit acceptance corpus must demonstrate this pinned-input capability from an external consumer.

## 13. Shared-core and public-boundary conformance

### 13.1 Shared core is not sufficient by itself

Semantic parity begins at the raw source boundary.

Preferred implementation posture: hosts acquire bytes and the shared execution boundary owns canonical source interpretation. If host-side YAML decoding is retained, its permitted conversion must be lossless for the declared syntax contract and qualified by raw-source conformance vectors.

Pin duplicate-key handling, scalar typing, numeric limits, tags/aliases, document selection, null/missing distinctions, and unsupported constructs. Reject unqualified lossy conversion rather than allowing two hosts to submit different facts to the same core.

This specifies behavior without choosing a new parser library in the design.

### 13.2 Equivalent semantic observations

Both Python and Node must agree on:

- supported source/set combinations and exact registry identities;
- normalized results, canonical fingerprints, and semantic payload digests;
- artifact contract mappings and source capability coverage;
- stable diagnostic codes, severity, affected identity/location, and governed ordering;
- rejection versus unavailability classification at equivalent semantic boundaries;
- historical lookup, current-set resolution, and materialization-aware linkage.

Idiomatic object APIs, exception classes, and operational host paths may differ only where explicitly outside semantic equivalence. Human-readable diagnostic text is not a hidden comparison oracle.

### 13.3 Execution security and trust

Treat source ADRs, contract contents, and extension payloads as data. Do not execute user-supplied callbacks, custom source tags, imports, or code to interpret architectural intent.

Resolve semantic sets from the configured trusted ADR-Kit registry. Hash correctness alone does not authorize an arbitrary caller-supplied contract.

No implicit network schema fetching, Node-to-Python subprocess, source mutation, or cross-provider path escape is introduced. Bound acquisition and execution resources; resource exhaustion is operational failure, not an empty semantic result.

### 13.4 Package evidence

Test the retained wheel and npm tarball, not only repository source imports.

Qualification must verify the shipped core artifact, schemas, registry, profiles, historical sets, source adapters, supported API exports, and immutable resources. A package that advertises a set but omits its executable support fails release qualification.

Preserve existing Node model 2.1/2.2 support. Update browser-safe model/schema capabilities where promoted, while keeping filesystem materialization host-only. Do not imply all Python authoring/compilation operations became Node capabilities merely because this new read-only operation has parity.

## 14. Proposed promotion obligations

The following are design-local obligation labels, not preallocated canonical NP aliases or UUIDs. Promotion assigns appropriate representations under the owning repository's current authoring contract. Do not turn every procedural sentence in this review into a new NP.

Verification classes: M = mechanical; D = design/semantic review; I = cross-boundary integration.

| Obligation | Normative statement proposed for owning authority | Owner | Verification |
|---|---|---|---|
| R1-AUTH-01 | Interpretation and representation MUST NOT manufacture competence, effectivity, applicability, or conformance authority. | STE-SPEC foundation; ADR-Kit normative ADR; Runtime L-0008 | D + I |
| R1-NP-01 | NP MUST retain first-class identity, declaring authority provenance, scope, and canonical force without an independent governance lifecycle. | New ADR-Kit normative ADR; L-0019 as needed | M + D |
| R1-NP-02 | NP materiality and semantic identity-continuity decisions MUST be made through competent semantic review; materially changed meaning MUST receive new identity, and mechanical validation MUST NOT claim to prove meaning preservation. | New normative ADR; PC-0002 | D + M |
| R1-NP-03 | Inclusion of an NP in a normalized model MUST NOT imply that it governs a concrete context. | New normative ADR; L-0013 | M + D |
| R1-NP-04 | NP normalization MUST NOT synthesize lifecycle, applicability, force, identity, or authority from prose, location, current time, or host defaults. | New normative ADR; PC-0004 | M |
| R1-INT-01 | Every meaning-affecting interpretation input and rule MUST be covered by an exact semantic definition or retained explicit input. | L-0025; L-0013 | M + D |
| R1-INT-02 | A profile MUST NOT change the meaning of an identified SCS independently of its constituent semantic definitions. | L-0025; PC-0003 | M + D |
| R1-SCV-01 | Released semantic definitions MUST remain immutable; lifecycle and current-use policy MUST remain outside their identity. | L-0025 | M |
| R1-SCV-02 | Semantic fingerprints MUST cover a closed, deterministic resource/dependency definition and MUST NOT depend on executable build bytes or mutable selection metadata. | L-0025; PC-0002/0005 | M |
| R1-SCS-01 | SCS identity MUST be derived from canonically ordered exact qualified constituents; duplicate families and conflicting preimages MUST fail. | L-0025; PC-0003 | M |
| R1-SCS-02 | New-set qualification MUST use explicit operation-qualified whole-combination declarations; missing support MUST NOT be inferred. | L-0025; PC-0003 | M + D |
| R1-SCS-03 | Historical sets MUST retain exact definitions and qualification independently of subsequent new-use prohibition. | L-0025; PC-0005 | M |
| R1-SCS-04 | Current selection MUST resolve to one explicit supported set before use and MUST NOT be stored as a floating historical basis. | L-0013; Runtime L-0008/0009 | M + I |
| R1-SRC-01 | Successful materialization MUST identify the complete sealed set of source and auxiliary inputs actually interpreted. | L-0013; PC-0004/0008 | M |
| R1-SRC-02 | Each interpreted artifact MUST retain its exact source-contract qualification; encountered closure MUST derive from actual inputs. | L-0013; PC-0004 | M |
| R1-SRC-03 | Detached materialization MUST NOT allocate identity; legacy canonicalization MUST consume an exact sealed provider-authoritative mapping or fail. | L-0019/0022; PC-0006/0004 | M |
| R1-RES-01 | Rejection, unavailability, complete acquisition, unresolved semantics, and historical inexpressibility MUST remain mechanically distinguishable. | L-0013; materialization contract | M + I |
| R1-RES-02 | Unsupported, invalid, or incompletely acquired authority input MUST NOT yield a success-shaped empty or partial authority model. | L-0013 | M |
| R1-RES-03 | Undeclared meaning within capable covered source MUST NOT be strengthened into a negative architectural assertion. | New normative ADR; L-0013 | M + D |
| R1-FP-01 | Portable state fingerprinting MUST use one closed, versioned semantic projection and MUST NOT replace source basis or retained realization identity. | L-0013/0019 as applicable; PC-0004 | M |
| R1-FP-02 | Payload deduplication and historical equivalence MUST preserve provenance and compare the complete qualified payload required by their contracts. | L-0013; Runtime PC-0004 | M + I |
| R1-HIST-01 | A corrected implementation MUST NOT rewrite historical state or redefine a contract merely to make an earlier defective realization appear conformant. | L-0025/0027; Runtime L-0010 | D + I |
| R1-HIST-02 | Historical recovery MUST verify the retained basis and result qualification; mismatch MUST remain explicit and MUST NOT replace the original reference. | L-0013; Runtime L-0009/PC-0004 | M + I |
| R1-LINK-01 | External attribution evaluation for an exact-history path MUST consume the pinned materialization, not implicitly reopen current authority source. | L-0020/0013; PC-0007; Runtime PC-0006 | M + I |
| R1-LINK-02 | New NP representation MUST NOT silently extend the allowed target matrix of a released attribution contract. | L-0020; PC-0007 | M |
| R1-HOST-01 | Host parity MUST be demonstrated from equivalent raw source and exact semantic bases, including parsing, diagnostics, coverage, and fingerprints. | L-0027 | M + I |
| R1-PUB-01 | Every publicly advertised set and capability MUST have installed-package support and shared conformance evidence in both host distributions. | L-0027; release qualification | M + I |
| R1-RUN-01 | Runtime MUST preserve provider-qualified intent, Runtime binding, and embodiment as separate typed planes under exact materialization/Snapshot bases. | Runtime L-0008/0009; PC-0006/0011 | M + I |

These obligations refine and concretize the supplied plan. Existing identity, attribution, and Runtime authority continues to apply where not explicitly amended through the owning process.

## 15. Promotion, bootstrap, and release slices

### 15.1 Immediate preflight

1. Re-resolve current branch heads and preserve any work in flight.
2. Confirm the 0.10.1 post-release synchronization remains present in ADR-Kit develop. It was present at reviewed commit `2b4bfeb8ece639ecaa8026a0f68e354c07157165`; do not redo it.
3. Use the locked STE-SPEC semantic design and existing ADR-L-0044 feature-branch promotion as qualified directional design input. Do not represent its `accepted` marker as admission to STE-SPEC develop and do not recreate the promotion from the older journal.
4. Defer promotion of the accumulated STE-SPEC tranche until ADR-Kit 0.11.0 can correctly validate `project.type: specification`. The later stabilization must correct INV-4405/INV-4406 decision traceability, update stale corpus status, regenerate derived artifacts, and pass the complete governance gate before admission.
5. Record this bounded sequencing exception in the ADR-Kit promotion evidence: ADR-Kit may refine representation, materialization, registry, and SDK mechanics from locked direction, but MUST NOT redefine STE-wide normative force, authority, effectivity, applicability, epistemic boundaries, or the NP/Invariant distinction.
6. CE-01 promotion is not a hidden prerequisite for this slice; use already-owned ADR-Kit identity authority for the NP encoding. Requirements remain a future distinct semantic family and MUST NOT be absorbed into NormativeProposition.

ADR-Kit 0.11.0 must add a backward-compatible, contract-governed `specification` project type so STE-SPEC can truthfully identify itself and pass project-metadata validation. Do not misclassify STE-SPEC as a library, system, platform, service, or tool merely to satisfy the older enum.

No part of this review merges branches, edits accepted sources, or waives CI.

### 15.2 Avoid the self-hosting promotion cycle

The architecture can be promoted using the currently supported ADR authoring representation. Place approved decisions and normative contract text in supported decision/specification structures. Do not add unsupported normative_propositions fields and then weaken validation to accept them.

Promote successor contract definitions and their ownership before implementing production behavior. Once 1.6 support is verified, a separately explicit authoring migration may realize appropriate approved propositions as native NP entities, preserving their decision provenance.

That authoring migration does not create new semantic authority by itself. It also does not require relabelling every existing Invariant as NP.

### 15.3 Revised ADR-Kit promotion map

| Owning surface | R1 responsibility |
|---|---|
| New logical normative-semantic ADR | NP shape/lifecycle/force/scope; distinction between author review and deterministic validation; parent-qualified governing meaning; inexpressibility. |
| L-0025 | SCV and SCS identity; interpretation closure; lifecycle/policy separation; explicit tuple qualification; historical support and release identity rules. |
| L-0013 | Sealed source basis; detached result; typed outcomes; artifact qualification; canonical fingerprint and materialization-aware consumer boundary. |
| L-0027 | Raw-source-to-result peer-host parity, core transport succession, registry support, installed-package qualification. |
| L-0019 / L-0022, only where needed | NP envelope compatibility, no read-time identity creation, exact legacy map qualification, old versus new fingerprint contracts. |
| L-0020 and PC-0007 | Bounded materialization-aware attribution evaluation; explicit preservation of the released target matrix. No new attribution vocabulary unless separately selected. |
| L-0026 | Discovery-only status preserved; explicit existing topology reconciliation retained. |
| PS-0002 | Public system responsibilities and interaction flow, without a new system. |
| PC-0002 | Structural/semantic contract validation boundaries and precise validation claims. |
| PC-0003 | Deterministic governed assembly and immutable artifact emission. |
| PC-0004 | Registry serving, source/materialization boundary, normalized state and exact consumer views. |
| PC-0005 | Corpus, dependency, fingerprint, and regeneration integrity. |
| PC-0006 | Existing brownfield/identity normalization responsibility where sealed legacy map consumption requires amendment. |
| PC-0008 | Source selection/scope and acquisition boundary; no accidental filesystem authority policy in hosts. |

Do not create a new ADR-PS or ADR-PC merely for these responsibilities. Amend an existing owner only where the reviewed rule materially changes its contract.

### 15.4 Implementation sequence

| Slice | Deliverable | Exit condition |
|---|---|---|
| A | Authoring 1.6 and normalized 2.3 NP contracts/realization, including the NP envelope discriminator | Positive/negative identity, force, parent, lifecycle, and legacy-regression fixtures pass. |
| B | normative-semantics 1.0, architecture-interpretation 1.0, immutable definitions/resource closure, SCV fingerprints | Every interpretation rule has a named owner; canonicalization and closure fixtures pass. |
| C | Profile, explicit tuple qualification, SCS assembly, corpus retention, current pointer | Repeated assembly is no-op; lifecycle does not rewrite history; missing support fails. |
| D | Sealed source boundary and shared-core materialization under transport 1.1 | Source bytes/maps/contracts are pinned; typed success/failure and coverage are reproducible. |
| E | Peer public registry/materialization operations and pinned-materialization attribution evaluation | Python and Node agree from raw source; existing attribution semantics remain exact. |
| F | Historical/mixed-source corpus, adversarial fixtures, installed artifacts, docs, release certification | All ADR-Kit release obligations have evidence; no Runtime-private implementation dependency is required to consume the package. |
| G | Runtime-local ADR/contract promotion | Uses the concrete ADR-Kit package contract and exact basis semantics. |
| H | Runtime acquisition, retention, pinned linkage evaluation, and reconstruction references | Lossless retained basis and immutable history are proven. |
| I | Snapshot-qualified recovery, intent queries, and typed composite projection | The original Snapshot never mutates; projection exposes exact authority planes and degradation. |

Shared-core semantics apply from the first production behavior added. Slice E is not permission to create temporary independent Python and TypeScript semantic implementations in earlier slices.

### 15.5 What 0.11.0 does not promise

- A general NP truth, consistency, applicability, or conformance evaluator.
- Automatic semantic equivalence of natural-language statements.
- New NP-to-code attribution under existing evidence 1.5/1.6.
- Unqualified legacy canonicalization without identity authority.
- Reproduction of every historical pre-registry package's behavior.
- General Node compilation/mutation parity beyond the operations actually promoted.
- Complete Runtime implementation, all extractors, graph infrastructure, EDR promotion, Requirement semantics, waiver machinery, or CE-01/Architecture-IR redefinition.

### 15.6 Documentation and CI

Update root/PyPI and npm documentation from the qualified package inventory, distinguishing host capabilities, browser-safe consumption, semantic contract versions, and package versions. Explain both the NP capability and the explicit attribution limitation.

Keep the existing CI stratification. Run targeted semantic and regression vectors in feature feedback, full cross-host/OS assurance at integration, and installed-package/historical/reproducibility qualification at release. Do not move every release proof into every fast feedback loop.

Release notes should describe an exact semantic interpretation and materialization capability, not claim the package can prove architectural correctness.

## 16. Adversarial conformance and review corpus

These are **required future evidence cases**, not claims of tests executed in this review. Each fixture must name its exact input basis, expected outcome, and owning obligation. A negative test passes by demonstrating the specified rejection or preserved uncertainty, not by suppressing the input.

Mechanical cases belong in shared contract/core fixtures and public-boundary tests as appropriate. Semantic-review cases belong in promotion evidence; they must not be disguised as executable natural-language proofs. Runtime-owned cases become gates for slices G–I, not a dependency on completing Runtime before publishing ADR-Kit.

### 16.1 NP representation and meaning

| Case | Adversarial input / comparison | Required result | Obligations |
|---|---|---|---|
| A01 | Valid 1.6 NP in each of ADR-L, ADR-PS, ADR-PC | All three preserve canonical identity, statement, force, scope, declaring ADR, and qualified provenance in 2.3. | R1-NP-01, R1-NP-04 |
| A02 | Unknown force; positive force plus separate polarity; missing required scope | Reject each invalid representation; do not repair it by inference. | R1-NP-04 |
| A03 | NP status/lifecycle in source or normalized output | Reject independent NP lifecycle; common-envelope validation cannot force one back in. | R1-NP-01, R1-NP-04 |
| A04 | MUST-valued Invariant; MAY-valued NP; Invariant placed in a forbidden parent | Preserve peer types and existing parent restrictions; do not cast by modal strength. | R1-NP-01, R1-AUTH-01 |
| A05 | Ordinary ADR prose containing MUST but no explicit NP declaration | Do not invent NP entities. Mechanical success makes no materiality claim. | R1-NP-02, R1-NP-04 |
| A06 | Editorial paraphrase versus materially different meaning | Review evidence justifies retained identity only for the former; the latter requires new identity. A content hash is not the reviewer. | R1-NP-02 |
| A07 | MUST NOT text with MUST NOT classifier; conflicting force/text; mixed-force clauses | No double-negation interpretation. Semantic disagreements remain review issues; split independently material mixed-force clauses. | R1-NP-02, R1-AUTH-01 |
| A08 | global scope in a bounded ADR; unrecognized scope; insufficient contextual facts | No authority broadening, no invented applicability, no UNKNOWN-to-false conversion. | R1-NP-03, R1-AUTH-01 |
| A09 | NP declared by proposed, historical, and effective source variants | Preserve parent qualification; model presence alone never yields a current governing verdict. | R1-NP-03 |
| A10 | Same NP UUID defined by two ADRs in one provider; separate references to one declaration | Reject competing canonical owners; permit valid references without treating them as definitions. | R1-NP-01 |

### 16.2 Contracts, sets, and policy

| Case | Adversarial input / comparison | Required result | Obligations |
|---|---|---|---|
| B01 | Same semantic definition across repeated generation and both hosts | Identical canonical preimage and SCV fingerprint. | R1-SCV-02 |
| B02 | Change an adapter's normative default without changing normalized output schema | Existing interpretation definition cannot change in place; changed meaning requires a successor and a newly qualified set. | R1-INT-01, R1-SCV-01 |
| B03 | Mutable import URL, missing resource, wrong dependency digest, digest dependency cycle | Reject nonclosed definition; never silently use current remote bytes. | R1-SCV-02, R1-INT-01 |
| B04 | UTF-16 key-order edge, authored array reorder, duplicate JSON names, unsafe number, Unicode-equivalent strings | Follow the exact canonicalization contract; reject lossy inputs; do not normalize Unicode or arrays incidentally. | R1-SCV-02, R1-SCS-01 |
| B05 | Permuted member order; changed family/version/fingerprint; duplicate family | Same composition has same ID; changed qualified constituent has different ID; duplicate family fails before overwrite. | R1-SCS-01 |
| B06 | All pairwise relations allowed but whole tuple undeclared; allowed forward operation but undeclared reverse | Reject unqualified combination/operation; infer neither transitivity nor symmetry. | R1-SCS-02 |
| B07 | Two profiles select the same exact members but attempt different interpretation defaults | Reject hidden semantic difference; profile cannot redefine an existing SCS. | R1-INT-02 |
| B08 | Deprecated-and-allowed, deprecated-and-prohibited, active-and-prohibited | Eligibility follows explicit new-use policy; lifecycle alone changes neither identity nor historical interpretation. | R1-SCV-01, R1-SCS-03 |
| B09 | Repeat assembly; then add one new qualified tuple | First run is zero diff; second adds only required immutable artifacts without rewriting old sets. | R1-SCS-01, R1-SCS-03 |
| B10 | Dangling SCV reference, conflicting same ID, duplicate stored composition, explicit incompatibility | Complete-corpus validation fails with typed integrity/qualification diagnostics. | R1-SCS-01, R1-SCV-02 |
| B11 | Current pointer changes after a run resolves it | Run retains the earlier exact ID; historical records contain no floating current selector. | R1-SCS-04 |
| B12 | Previously evolving source label; historical set later prohibited for new use; set catalogued but not executable | Preserve exact imported qualification and history; disclose executable support honestly; do not invent historical registry identity. | R1-SCV-01, R1-SCS-03, R1-PUB-01 |

### 16.3 Acquisition, identity, and knowledge limits

| Case | Adversarial input / comparison | Required result | Obligations |
|---|---|---|---|
| C01 | Fixed Git tree or sealed caller-supplied bundle | Successful basis accounts for every selected interpretation input and verifies the claimed acquisition kind. | R1-SRC-01 |
| C02 | Dirty file claimed as committed bytes; source changes during acquisition | Do not certify the claimed commit or a mixed-time bundle; use honest content-bundle qualification or fail. | R1-SRC-01, R1-RES-02 |
| C03 | Change selection config, referenced metadata, or sealed identity map while ADR text stays unchanged | Changed auxiliary basis remains observable; no invisible interpretation side input. | R1-SRC-01, R1-INT-01 |
| C04 | Legacy corpus with complete sealed provider-authoritative UUID map | Repeated runs preserve exact UUIDv7 identities and retain the map digest; no source rewrite occurs. | R1-SRC-03 |
| C05 | Legacy corpus without a map; conflicting, partial, or foreign-provider map | Typed identity-qualification failure; no read-time UUID generation or Runtime repair. | R1-SRC-03, R1-RES-01 |
| C06 | Mixed 1.5 and 1.6 artifacts, only one declaring NP | Retain each artifact's qualified contract, exact encountered closure, and region-specific NP capability. | R1-SRC-02, R1-RES-01 |
| C07 | Valid capable source with absent/empty optional NP collection | Report no declaration within that covered source, not absence of all system obligations. | R1-RES-03 |
| C08 | Empty valid selected corpus versus missing required file versus unavailable provider | Distinct results; missing or incomplete acquisition cannot masquerade as successful emptiness. | R1-RES-01, R1-RES-02 |
| C09 | Contract-authorized unresolved reference in otherwise valid source | Successful qualified model preserves unresolved state, without admitting the relationship or claiming a negative fact. | R1-RES-01 |
| C10 | One unsupported or invalid artifact among otherwise valid selected inputs | Reject the authority materialization; no silently truncated success. | R1-RES-02, R1-INT-01 |
| C11 | Same UUID bytes under different providers; namespace mismatch; duplicate provider selections | Preserve separate qualified identities; reject ambiguous or falsely qualified acquisition. | R1-AUTH-01, R1-SRC-01 |
| C12 | Custom executable YAML tag, path escape, untrusted contract registry, exhausted resource budget | Execute no source code, accept no self-authorized contract, mutate no source, and classify operational failure explicitly. | R1-INT-01, R1-RES-01 |

### 16.4 Fingerprints and historical realization

| Case | Adversarial input / comparison | Required result | Obligations |
|---|---|---|---|
| D01 | Existing binding-local fingerprint alongside new portable fingerprint | Both retain their own scheme, projection, and meaning; no relabelling shortcut. | R1-FP-01 |
| D02 | YAML comment edit or source-only revision change under the same SCS | Canonical state may remain equal; changed source-qualified provenance remains distinct in the complete payload. | R1-FP-01, R1-FP-02 |
| D03 | Change force, statement, declaring owner, governing source state, unresolved content, or relevant coverage | Changed canonical state projection changes its fingerprint under the fixed scheme. | R1-FP-01 |
| D04 | Move host checkout path versus change an authored implementation path | Host relocation alone does not change state; an authored semantic path is not discarded as incidental metadata. | R1-FP-01 |
| D05 | Same canonical state, different artifact provenance or covered source revision | State chunk may deduplicate; provenance-bearing payload and realization envelopes do not collapse. | R1-FP-02 |
| D06 | Permute identity-keyed set order; reorder an authored semantic sequence; alter display-only diagnostics | Respect each collection's order semantics and the closed diagnostic projection across hosts. | R1-FP-01, R1-HOST-01 |
| D07 | Reproduce exact basis under a qualified conforming implementation | Match required state and payload digests before accepting an equivalent recovery. | R1-HIST-02, R1-FP-02 |
| D08 | E1 has a known defect; E2 fixes it under unchanged contracts | Report historical reproduction mismatch; change neither old Snapshot nor semantic contract to conceal the defect. | R1-HIST-01, R1-HIST-02 |
| D09 | Same historical source interpreted using a different SCS | Record a new interpretation, never replacement or recovery of the old basis. | R1-HIST-02 |
| D10 | Missing historical source/map; pruned cache; proposed deletion of last Snapshot-referenced payload | Distinguish cache recovery from unrecoverable realization; default retention preserves the last canonical payload. | R1-HIST-02, R1-RES-01 |

### 16.5 Public SDK and attribution seam

| Case | Adversarial input / comparison | Required result | Obligations |
|---|---|---|---|
| E01 | Identical raw YAML across Python/Node: scalar, null/missing, tags/aliases, duplicate keys, numbers, document boundaries | Same interpretation or governed rejection before lossy host conversion can diverge. | R1-HOST-01 |
| E02 | Equivalent semantic error through both public hosts | Same governed diagnostic fields/order and semantic digest treatment; presentation-only differences remain outside that projection. | R1-HOST-01, R1-FP-02 |
| E03 | Node package on a host without Python | Promoted peer operations run through the shared core without Python subprocess or hidden CLI dependency. | R1-HOST-01 |
| E04 | External consumer uses public requests/results only | No compiler-internal types, writable repository staging requirement, or private imports leak across the public boundary. | R1-PUB-01 |
| E05 | Install retained wheel and npm tarball into clean consumers | Advertised core, schema, registry, profile, resources, APIs, and exact historical support are present and usable. | R1-PUB-01 |
| E06 | Existing Node 2.1/2.2 consumers; browser-safe imports; host-only materialization | Preserve promised compatibility and host/profile distinctions; no accidental promise of full compile/mutate parity. | R1-PUB-01 |
| E07 | Acquire materialization, change/delete current checkout, then evaluate existing attribution claims | Evaluation uses the retained materialization and explicit evidence, without reopening present-day authority source. | R1-LINK-01 |
| E08 | NP target supplied under released evidence 1.5/1.6; existing Invariant enforcement claim | NP target remains unsupported; valid existing target/verb semantics remain unchanged and correctly qualified. | R1-LINK-02 |
| E09 | Change current SCS or attribution profile after basis selection; attempt reuse of an unqualified cached linkage result | Evaluation retains both exact bases; cached results cannot silently cross them. | R1-LINK-01, R1-SCS-04 |
| E10 | Unsupported set, validation rejection, host I/O failure, and resource exhaustion through public calls | Documented, distinguishable outcome/error mappings; no generic success-shaped fallback. | R1-RES-01, R1-HOST-01 |

### 16.6 Runtime-owned integration

| Case | Adversarial input / comparison | Required result | Obligations |
|---|---|---|---|
| F01 | Runtime retains canonical ADR-Kit entities and later constructs its own projection | No reminted external entity identity, local ADR interpretation, or newly manufactured authority. | R1-RUN-01, R1-AUTH-01 |
| F02 | Equivalent recovery creates another materialization record | Original Runtime identity and Snapshot remain immutable; append-only association exposes the recovery used. | R1-HIST-02, R1-RUN-01 |
| F03 | External validation passes but Runtime embodiment mapping fails; old binding exists | Preserve separate outcomes; do not admit a new binding from old binding state or external validation alone. | R1-RUN-01 |
| F04 | Extract attribution declarations while intent is unavailable, then obtain materialization | Observation remains independent; later validation uses the explicit pinned authority basis. | R1-LINK-01, R1-RUN-01 |
| F05 | Composite traversal includes intent, binding, embodiment, and unresolved/degraded branches | Preserve typed planes, exact Snapshot/materialization basis, and visible knowledge limitations. | R1-RUN-01, R1-RES-01 |
| F06 | Successful materialization and binding presented to a conformance consumer | Return no implementation-conformance verdict without separately competent assessment. | R1-AUTH-01, R1-RUN-01 |

## 17. Traceability to the supplied promotion-ready plan

### 17.1 Existing normative groups are retained, not replaced accidentally

| Original obligations | R1 disposition | Governing sections / evidence |
|---|---|---|
| P NP-01–NP-03 | Preserve first-class NP, declaring authority, and no independent lifecycle; close normalized-envelope conflict. | §§4, 6; A01, A03, A05, A09 |
| P NP-04–NP-05 | Preserve meaning-based identity and materiality; explicitly separate author review from machine checks. | §6.2–6.4; A06–A07 |
| P NP-06–NP-08 | Preserve peer taxonomy, complete force vocabulary, and no independent polarity. | §6.1, §6.3; A02, A04 |
| P NP-09–NP-11 | Preserve dimension separation and tri-state applicability; do not claim this release evaluates arbitrary contexts. | §§4, 6.6–6.7, 9.3; A08–A09 |
| P NP-12 | Preserve historical inexpressibility with source-local coverage. | §§8.3, 9.3; C06–C07 |
| P SCS-INV-01–SCS-INV-04 | Preserve stable composition identity, sensitivity to qualified constituents, lifecycle independence, and order independence. | §7; B01, B04–B05, B08 |
| P SCS-INV-05–SCS-INV-06 | Preserve zero-diff regeneration and full-corpus integrity; add explicit whole-tuple qualification. | §7.4; B06, B09–B10 |
| P SCS-INV-07–SCS-INV-09 | Preserve new-use exclusion and append-only historical identities; distinguish policy from deprecation. | §7.1, §7.5; B08–B12 |
| P MAT-NP-01 | Strengthen exact recipe by closing source interpretation and all meaning-affecting dependencies. | §5; B02–B03, B07, C03 |
| P MAT-NP-02–MAT-NP-03 | Preserve no authority creation and no conformance inference. | §§4, 9, 12; F01, F06 |
| P MAT-NP-04–MAT-NP-05 | Preserve separate source/SCS axes and heterogeneous source closure; restore per-artifact qualification. | §§8–10; C01, C03, C06 |
| P MAT-NP-06 | Clarify that capable-but-undeclared is not an open-world negative assertion; preserve any explicitly authored semantic absence only under its own contract. | §9.3; C06–C09 |
| P MAT-NP-07 | Refine recoverability: conformant historical interpretation is distinct from reproducing a past defective realization. Pin result evidence and retain the historical payload. | §11; D07–D10 |
| P MAT-NP-08–MAT-NP-09 | Preserve distinct reinterpretations and provider-qualified identity. | §§8.5, 11–12; C11, D09, F01–F02 |

### 17.2 Original conformance corpus coverage

| P §24 case numbers | R1 evidence cases | Correction / qualification |
|---|---|---|
| 1–3 | A01 | Test each permitted parent separately. |
| 4–7 | A02–A04 | Validate both authoring and normalized NP lifecycle exclusion. |
| 8–11 | A01, C04–C07, E06 | Preserve frozen supported contracts; legacy identity qualification is explicit. |
| 12–14 | B01–B04, B08 | Distinguish semantic-definition changes from policy and additional regression evidence. |
| 15–18 | B05, B09 | Preserve exact preimages and zero-diff artifact generation. |
| 19 | B08 | Correct the original conflation: deprecated is not automatically prohibited. |
| 20–24 | B10–B12, C10, E10 | Addressability, executable support, and new-use permission are separate. |
| 25–29 | D01–D06, E01–E06 | Parity starts from raw source, not only pre-parsed JSON. |
| 30–32 | D07–D10, F02 | Exact historical result requires retained-result verification, not only recipe availability. |
| 33–36 | E07–E09, F01–F06 | Preserve independent observation, separate binding, typed composition, and no conformance inference. |

No original conformance case is intentionally dropped. The original case 19 and unconditional reading of historical realization recovery are corrected, not silently carried forward.

## 18. Lock decisions and closure criteria

### 18.1 Four approved decisions

| Decision | Approved lock | Benefit | Accepted boundary |
|---|---|---|---|
| LD-01 — Interpretation identity | Add architecture-interpretation 1.0 as the third semantic family in the initial materialization SCS. | Source-to-meaning rules acquire independently evolvable exact identity. | Accept the additional family rather than coupling all interpretation evolution to normalized-model 2.3. |
| LD-02 — Exact-history consumer seam | Include public evaluation of existing attribution semantics against the pinned materialization in ADR-Kit 0.11.0. | The package can actually support Runtime's exact-history promise. | The seam validates existing attribution semantics only and remains separate from Runtime mapping, binding admission, and conformance assessment. |
| LD-03 — NP attribution boundary | Defer direct NP-target attribution; preserve released evidence 1.5/1.6 verb/target semantics. | Keeps this substantial release bounded around representation and exact interpretation. | Direct code-to-NP attribution is intentionally unsupported until separately promoted through successor attribution contracts. |
| LD-04 — Historical result retention | Initially retain the last canonical payload referenced by a committed Snapshot, verify recovery, and expose mismatches. | Historical truth survives later implementation corrections. | Accept bounded storage cost; deduplication and cache eviction remain allowed, but the last Snapshot-referenced canonical payload is retained. |

The four decisions and the remaining R1 corrections are approved. Sealed acquisition, source-local coverage, canonical identity qualification, discriminated outcomes, field-precise hashing, immutable definitions, and raw-source parity are required to make the stated promises coherent; they are not optional implementation shortcuts.

### 18.2 Architectural lock versus implementation specification

The architecture is ready for bounded repository-local promotion. This is a **design lock**, not evidence that the wire contracts, implementation, or release already conform.

Before production implementation, the promotion/contract slice must settle and review:

1. Exact SCV definition/resource manifests, qualification records, and profile/SCS schemas, including digest domain separation and canonical values.
2. Authoring 1.6 and normalized 2.3 schemas, including NP discriminator, parent relationship, stable common-field derivations, and semantic-field projection classification.
3. Sealed source/request/result schemas, source selection rules, artifact/contract binding, legacy map qualification, and the exact initially supported source domain.
4. State and semantic-payload preimages, source/diagnostic projections, collection ordering rules, and golden canonicalization vectors.
5. Public/core operation contracts, error taxonomy, evidence/linkage basis qualification, and precise host/profile capability inventory.
6. Runtime-local retention/recovery and append-only association contracts before implementing those downstream behaviors.

These are bounded artifact obligations of the chosen architecture. A public method's spelling or an internal parser choice need not reopen the architecture if it meets them. A decision that changes permissible inference, identity, history, or ownership does require an explicit design amendment.

### 18.3 Promotion acceptance gate

Promotion is complete only when:

- the bounded STE-SPEC sequencing exception and exact locked directional basis are recorded without claiming branch admission;
- each R1 obligation is represented or explicitly traced to existing accepted authority in its owning repository;
- the exact contract artifacts implement the locked choices without contradictory defaults;
- implementation work is sequenced behind that authority, with clear evidence ownership;
- deliberate unsupported capabilities are visible in the public contract and release documentation.

Implementation may then progress slice by slice. Do not wait for every Runtime test before developing the ADR-Kit package, and do not publish the ADR-Kit release until its own promoted obligations are evidenced.

### 18.4 Approved lock statement

> ADR-Kit 0.11.0 will represent ADR-scoped NormativePropositions without manufacturing independent lifecycle, authority, applicability, or conformance. Materialization will interpret one sealed, provider-qualified source basis under one exact, transitively closed semantic-contract set, preserve source-local knowledge limitations and canonical identity, and return a detached result with explicit semantic equivalence boundaries. Python and Node will expose equivalent shared-core behavior, including evaluation of existing attribution semantics against that pinned result. Runtime will retain the distinction between source, interpretation, realization, and binding; historical recovery will verify retained results and will not rewrite Snapshot history. Direct NP-target attribution remains outside the initial release unless separately promoted through successor attribution contracts.

This statement is **accepted as the ADR-Kit 0.11.0 R1 design lock**. Repository-local promotion remains the next authority-creating action.

## 19. Review evidence, limits, and handoff

### Completed in this review

- Read and reconciled all three supplied artifacts.
- Inspected bounded governing ADRs, concrete schemas, the linkage boundary, the semantic-core boundary, and relevant repository baselines.
- Distinguished the existing upstream promotion branch from its absence on STE-SPEC develop.
- Mechanically confirmed the two ADR-L-0044 invariant-to-decision reference mismatches.
- Produced 28 design-local normative obligations, 60 evidence cases, original-plan traceability, and explicit lock/release boundaries.
- Checked that every design-local obligation has at least one proposed evidence case, that obligation/case identifiers are consistent, and that the ten cited public repository file paths exist at their pinned commits. These are document integrity checks, not execution of the proposed product tests.
- Kept the input artifacts and repository contents unchanged.

### Not claimed

- No comprehensive code audit, production conformance run, release certification, benchmark, or installed-package validation was performed here.
- The detailed successor schemas, DTOs, fingerprint manifests, and golden vectors are not yet implemented or promoted by this document.
- Repository baselines can move; the promotion workflow must re-resolve them.
- Semantic materiality and natural-language meaning preservation cannot be certified by this document's mechanical traceability checks.

### Recommended next action

Execute the bounded **ADR authority-promotion slice** in ADR-Kit from the reconciled 0.10.1 develop baseline. Use the locked STE-SPEC direction and the existing ADR-L-0044 feature artifact as qualified design input without claiming that its accumulated branch has been admitted. Promote ownership, decisions, invariants, boundaries, and explicit deferrals using the currently supported authoring representation; do not implement successor schemas, registries, fingerprints, or SDK behavior in that first slice. The contract-definition slice follows the promoted ADR-Kit authority, and production implementation follows the promoted contracts. No additional conceptual subsystem is needed to start.
