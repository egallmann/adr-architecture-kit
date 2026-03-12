# ADR-028: AI-DOC Fabric and Gateway Authority Boundaries

**Status:** Accepted  
**Date:** 2025-12-29  
**Closes Gap:** Implicit tribal knowledge about Fabric/Gateway roles  
**Related:** ADR-019 (Gateway Authority and Signing Model), ADR-022 (Fail-Closed Enforcement Scope), ADR-024 (Cross-Component Contracts), ADR-026 (Invariant Conflict Detection Semantics), ADR-027 (Scope Semantics)

---

## Context

The STE-System specification defines AI-DOC Fabric as the canonical state authority (§7.1), STE Gateway as the execution enforcement boundary (§5.3), and STE Runtime as the context assembly layer (§5.2). These roles have been referenced across multiple ADRs and specification sections. However, critical aspects of the authority model remain implicit, relying on tribal knowledge rather than falsifiable specification text:

1. **Gateway's relationship to Fabric during execution**: The specification prohibits Gateway from signing canonical artifacts (P-GW-4, ADR-019) and requires Gateway to resolve canonical invariants "from ADF" (R-GW-3, §5.3.2). However, the specification does not explicitly state whether Gateway queries Fabric synchronously during eligibility evaluation or whether canonical state is provided via attestations.

2. **Fabric's authoritative vs advisory status**: ADR-026 establishes that Fabric detects conflicts and attests to conflict status, with Gateway verifying the attestation. However, the specification does not explicitly prohibit Gateway from recomputing or challenging Fabric's determinations. This creates a loophole where implementations might "helpfully" double-check Fabric's work.

3. **Runtime's authority boundaries**: The specification assigns Runtime the responsibility to "construct proposed MVC context" (§5.2.2) and "produce CEM envelopes" (R-RT-4). However, it does not explicitly prohibit Runtime from inferring canonical state, defaulting missing invariants, or substituting Runtime judgment for Fabric authority. This creates ambiguity about whether Runtime can "fill gaps" when Fabric attestations are incomplete.

4. **Knowledge flow directionality**: The specification describes components and their responsibilities but does not explicitly define the one-way knowledge flow from Fabric → Runtime → Gateway. This allows implementations to infer that Gateway might query Fabric, cache Fabric responses, or reconstruct canonical state from historical data.

5. **Canonical vs operational knowledge boundary**: The specification distinguishes canonical state (§7.1) from provisional workspace state (§5.2.1) but does not explicitly define the boundary rules that prevent Gateway from treating operational knowledge as canonical or Runtime from treating provisional knowledge as authoritative.

These ambiguities create critical correctness risks:

**Non-Deterministic Enforcement:** If Gateway can query Fabric at execution time, eligibility decisions depend on Fabric availability, network latency, and cache state. Different Gateway instances with different cache configurations could produce different eligibility decisions for identical Context Bundles, violating the determinism guarantee (§8.1.4: "Eligibility evaluation is deterministic").

**Semantic Drift Across Implementations:** Without explicit prohibition of Gateway content parsing and conflict detection, implementers might create "enhanced" Gateways that recompute conflict status, compare invariant content hashes against cached values, or perform semantic validation. These enhancements introduce implementation variation that breaks interoperability.

**Authority Boundary Violations:** If Runtime can sign Fabric Attestations, construct canonical claims, or override Fabric's conflict determinations, the canonical authority model collapses. Fabric becomes advisory rather than authoritative, undermining the correctness guarantees that define the STE-System.

**Gateway Probing and Reconnaissance:** If Gateway responses include invariant content, conflict details, or evaluation traces, attackers can probe Gateway to map canonical state, discover invariant structure, or extract organizational topology. Minimal response surface is a security property, not an implementation detail.

**"Helpful" Non-Determinism:** Implementations might "helpfully" fill gaps when Fabric attestations are incomplete, infer environment from deployment metadata, or fall back to cached canonical state when fresh attestations are unavailable. These behaviors seem helpful but introduce non-determinism and break the fail-closed enforcement model.

This ADR exists to make explicit what was previously implicit: the canonical roles, authority boundaries, and prohibited behaviors of AI-DOC Fabric, STE Gateway, and STE Runtime. After this ADR, no compliant implementation can treat Fabric as a runtime query service, Gateway as a reasoning component, or Runtime as a canonical authority.

**Note on ADR Purpose:** This ADR is specification reconciliation, not architectural redesign. It codifies decisions already embedded in ADR-019, ADR-024, ADR-026, and other specification sections. This ADR does not introduce new capabilities or relax existing enforcement; it makes existing constraints explicit and falsifiable.

---

## Decision

**AI-DOC Fabric is the sole canonical authority; STE Gateway is a pure verifier; STE Runtime is a transport layer. No component substitutes for another.**

### Authority Boundaries Are Correctness Boundaries

Authority boundaries defined in this ADR are correctness boundaries; violating them produces architecturally incorrect behavior, not alternative implementations. A Gateway that queries Fabric at execution time is not a "variant implementation"; it is a non-conformant implementation. A Runtime that signs Fabric Attestations is not "enhanced"; it is architecturally invalid.

### One-Way Knowledge Flow

Knowledge flows forward only:

```
Human/Agent → Runtime → Fabric (resolution, signing) → Runtime → Gateway (verification) → Model Provider
```

- Knowledge flows forward, never backward
- Gateway never queries Fabric during eligibility evaluation
- Gateway never enriches knowledge from external sources
- Gateway never fills gaps in attestations
- Runtime never substitutes for Fabric authority

### Component Role Summary

**AI-DOC Fabric:**
- Sole canonical state authority
- Only resolver of invariants from canonical stores
- Only detector of invariant conflicts
- Only signer of Fabric Attestations
- Provides attestations to Runtime upon request (off execution hot path)

**STE Gateway:**
- Pure verifier of cryptographically signed attestations
- Binary enforcement point (ALLOW | DENY, no partial execution)
- Stateless eligibility gate
- Does NOT query Fabric, reason over content, or detect conflicts

**STE Runtime:**
- Context assembly and transport layer
- Requests attestations from Fabric
- Transports attestations verbatim to Gateway
- Does NOT infer canonical state, sign attestations, or override Fabric

---

## Canonical Role of AI-DOC Fabric (Normative)

### Fabric IS

**R-FAB-ROLE-1: Sole Canonical State Authority**

AI-DOC Fabric is the sole authoritative source for canonical state as defined in §7.1. No other component has authority to establish, attest to, or override canonical truth.

**R-FAB-ROLE-2: Only Resolver of Invariants**

AI-DOC Fabric is the only component that resolves canonical Prime, System, and Domain invariants from canonical stores. Gateway, Runtime, and other components MUST NOT resolve invariants independently.

**R-FAB-ROLE-3: Only Detector of Invariant Conflicts**

AI-DOC Fabric is the only component that detects invariant conflicts per ADR-026. Fabric performs conflict detection during attestation creation and attests to conflict status in signed Fabric Attestations.

**R-FAB-ROLE-4: Only Signer of Fabric Attestations**

Fabric Attestations MUST be produced and cryptographically signed exclusively by AI-DOC Fabric or a Fabric-controlled signing service. No other component has authority to sign Fabric Attestations.

**R-FAB-ROLE-5: Source of Time-Bounded, Cryptographically Verifiable Truth**

AI-DOC Fabric provides time-bounded (TTL-scoped), cryptographically signed attestations that convey canonical state for a specific (scope, environment) at a specific timestamp. Attestations are authoritative, not advisory.

### Fabric IS NOT

**P-FAB-1: NOT a Runtime Dependency for Gateway**

AI-DOC Fabric is NOT a runtime dependency for Gateway eligibility evaluation. Gateway MUST NOT query Fabric synchronously during execution eligibility evaluation. Fabric resolution occurs off the execution hot path via Runtime requests.

**P-FAB-2: NOT a Query Service During Execution**

AI-DOC Fabric is NOT a query service that Gateway calls to discover canonical state. Canonical state is conveyed via signed Fabric Attestations provided by Runtime, not discovered via Gateway queries.

**P-FAB-3: NOT a Reconciliation Engine at Execution Time**

AI-DOC Fabric does NOT perform reconciliation, conflict resolution, or semantic reasoning during execution eligibility evaluation. Fabric resolves and attests to state; it does not reconcile divergent claims at execution time.

**P-FAB-4: NOT Advisory or Best-Effort**

Fabric Attestations are NOT advisory, suggestive, or best-effort. Attestations are authoritative assertions of canonical state. Gateway MUST treat attestations as binding truth, not hints or recommendations.

### Explicit Rules

**R-FAB-1: Fabric Attestations MUST Be Signed Exclusively by Fabric**

Fabric Attestations MUST be produced and cryptographically signed exclusively by AI-DOC Fabric. Runtime MUST NOT construct, sign, co-sign, or delegate-sign Fabric Attestations.

**Rationale:** Fabric is the canonical authority. Allowing Runtime or other components to sign attestations would collapse the authority model, making Fabric attestations non-authoritative.

**Falsifiable:** Verify attestation signature against Trust Registry; signing identity MUST resolve to Fabric ORG authority, not Runtime PROJECT authority.

**R-FAB-2: Fabric MUST Perform Conflict Detection Before Signing**

AI-DOC Fabric MUST perform invariant conflict detection per ADR-026 before signing Fabric Attestations. Fabric MUST include `conflict_status` field in every attestation with value `"none"` or `"detected"`.

**Rationale:** Conflict detection is a canonical determination. Only Fabric has authority to determine whether conflicts exist within a given (scope, environment).

**Falsifiable:** Inspect attestation structure; `conflict_status` field MUST be present and signed as part of attestation envelope.

**R-FAB-3: Fabric MUST Include All Required Fields**

Fabric Attestations MUST include all required fields: `attestation_id`, `issued_at`, `expires_at`, `ttl`, `scope`, `environment`, `conflict_status`, `prime_invariants`, `system_invariants`, `signature`, `signing_identity`.

**Rationale:** Incomplete attestations cannot be verified deterministically. Required fields enable Gateway to perform structural verification without content parsing.

**Falsifiable:** Parse attestation structure (not content); verify all required fields are present.

**R-FAB-4: Fabric MUST NOT Delegate Attestation Signing**

AI-DOC Fabric MUST NOT delegate attestation signing authority to Runtime, Gateway, or other components. Attestation signing is non-delegable.

**Rationale:** Delegation would create ambiguity about canonical authority. If Runtime could sign on Fabric's behalf, Runtime becomes a co-authority, undermining Fabric's sole authority.

**Falsifiable:** Inspect Trust Registry; no identity other than Fabric ORG authority has capability to sign attestations.

### Prohibitions

**P-FAB-1: No Component Other Than Fabric May Sign Attestations**

No component other than AI-DOC Fabric may produce, sign, or modify Fabric Attestations. This prohibition is absolute and non-negotiable.

**P-FAB-2: Attestations Are Not Advisory**

Fabric Attestations are authoritative, not advisory. Gateway MUST treat attestations as binding canonical truth, not suggestions or hints that can be overridden or recomputed.

---

## Canonical Role of STE Gateway (Normative)

### Gateway IS

**R-GW-ROLE-1: Pure Verifier of Cryptographically Signed Attestations**

STE Gateway is a pure verifier over cryptographically signed Fabric Attestations. Gateway verifies attestation signatures, extracts required fields, and enforces binary eligibility decisions. Gateway does NOT parse, compare, or interpret invariant content.

**R-GW-ROLE-2: Binary Enforcement Point**

STE Gateway is a binary enforcement point that produces ALLOW or DENY decisions. Gateway does NOT produce INDETERMINATE for execution; ambiguous conditions result in DENY. No partial execution states exist.

**R-GW-ROLE-3: Stateless Eligibility Gate**

STE Gateway is stateless. Gateway maintains no session state, no request history, no retry awareness. Each eligibility evaluation is independent; Gateway treats resubmitted requests as new proposals with no memory of prior denials.

**R-GW-ROLE-4: Execution Blocker, Not Reasoner**

STE Gateway blocks execution when prerequisites fail. Gateway does NOT reason about why prerequisites failed, suggest remediation, or perform discovery to satisfy prerequisites. Gateway verifies explicit claims; it does not infer implicit claims.

### Gateway IS NOT

**P-GW-ROLE-1: NOT a Reasoning Engine**

STE Gateway is NOT a reasoning engine or inference system. Gateway does NOT perform semantic validation, policy interpretation, or logical reasoning over invariant content.

**P-GW-ROLE-2: NOT a Discovery System for Canonical State**

STE Gateway is NOT a discovery system. Gateway does NOT query AI-DOC Fabric to discover canonical state, fetch invariant content, or resolve missing attestations.

**P-GW-ROLE-3: NOT a Semantic Validator**

STE Gateway is NOT a semantic validator of invariant content. Gateway does NOT parse invariant YAML/JSON, extract keys/values, or validate semantic correctness of invariant structure.

**P-GW-ROLE-4: NOT a Conflict Detector**

STE Gateway is NOT a conflict detector. Gateway validates Fabric's attested `conflict_status` field but does NOT implement conflict detection algorithms, compare invariant content, or recompute conflict determinations.

**P-GW-ROLE-5: NOT a Fallback Mechanism**

STE Gateway is NOT a fallback mechanism or compensating control. Gateway does NOT provide alternate execution paths, cached attestations, or best-effort enforcement when Fabric attestations are missing or invalid.

**P-GW-ROLE-6: NOT a Cache or Proxy for Fabric**

STE Gateway is NOT a cache or proxy for AI-DOC Fabric. Gateway does NOT cache invariant content, attestations, or Fabric responses for later reuse.

### Explicit Rules

**R-GW-1: Gateway MUST NOT Query AI-DOC Fabric During Eligibility Evaluation**

STE Gateway MUST NOT query AI-DOC Fabric during eligibility evaluation. All required canonical state MUST be provided by Runtime via signed Fabric Attestations included in the Eligibility Proposal.

**Rationale:** Querying Fabric at execution creates latency, availability coupling, and cache consistency problems. Fabric resolution occurs off the hot path via Runtime requests.

**Falsifiable:** Network trace Gateway process during eligibility evaluation; no outbound connections to Fabric services.

**R-GW-2: Gateway MUST Treat Canonical Assertions as Opaque Signed Blobs**

STE Gateway MUST treat canonical assertions (invariant identifiers, content hashes, conflict_status) as opaque signed data. Gateway extracts required fields from attestation structure but does NOT interpret field values semantically.

**Rationale:** Treating assertions as opaque ensures Gateway remains a pure verifier. If Gateway interprets values, Gateway becomes a reasoning system, violating the verifier-only posture.

**Falsifiable:** Inspect Gateway implementation; no invariant parsing libraries, no YAML/JSON deserializers for invariant content, no semantic validation logic.

**R-GW-3: Gateway MUST NOT Parse Invariant Content Beyond Attestation Structure**

STE Gateway MUST NOT parse invariant content beyond the attestation structure. Gateway extracts attestation fields (`scope`, `environment`, `conflict_status`, `prime_invariants`, etc.) but does NOT parse the content of individual invariants.

**Rationale:** Parsing invariant content introduces implementation variation and violates the verifier-only posture. Different parsers might handle edge cases differently, breaking determinism.

**Falsifiable:** Gateway code review; no YAML/JSON parsing of `invariant.content` fields, only extraction of `invariant_id` and `content_hash` strings.

**R-GW-4: Gateway MUST NOT Compare, Interpret, or Recompute Canonical Claims**

STE Gateway MUST NOT compare invariant content hashes to cached values, interpret invariant semantics, or recompute canonical determinations (e.g., conflict status, scope coverage).

**Rationale:** Comparison and recomputation introduce non-determinism. If Gateway fetches canonical invariants to compare hashes, Gateway's decision depends on cache state and network availability, breaking determinism.

**Falsifiable:** Gateway does NOT fetch invariant content from Fabric or caches; Gateway does NOT compute digests of cached invariants for comparison.

**R-GW-5: Gateway MUST Verify Attestation Signatures, Temporal Validity, and Required Fields Only**

STE Gateway's verification responsibilities are limited to:
- Attestation signature verification (cryptographic integrity)
- Temporal validity (current time ≤ expires_at)
- Required field presence (all fields per R-FAB-3 are present)
- Field format validation (e.g., `conflict_status` is `"none"` or `"detected"`)

Gateway MUST NOT perform semantic validation, content comparison, or policy interpretation beyond these structural checks.

**R-GW-6: Gateway MUST Evaluate Eligibility Based Solely on Attestation Presence and Validity**

STE Gateway evaluates eligibility based on whether a valid, signed, non-expired Fabric Attestation is present. Gateway does NOT evaluate the correctness, completeness, or semantic validity of invariant content.

**Rationale:** Semantic evaluation requires reasoning, which violates the verifier-only posture. Gateway enforces structural correctness; Fabric ensures semantic correctness.

**R-GW-7: Gateway MUST Treat Fabric-Signed conflict_status as Authoritative and Final**

STE Gateway MUST treat Fabric-signed `conflict_status` as authoritative and final. Gateway MUST NOT recompute, reinterpret, or challenge conflict assertions made by Fabric.

**Rationale:** Fabric is the canonical authority for conflict detection (ADR-026). Allowing Gateway to dispute Fabric creates a "double validation" loophole where Gateway overrides canonical determinations, collapsing the authority model.

**Falsifiable:** If attestation has `conflict_status: "detected"`, Gateway MUST return DENY with INVARIANT_CONFLICT, regardless of whether Gateway "thinks" conflicts exist. Gateway has zero authority to dispute Fabric.

### Prohibitions

**P-GW-1: Gateway MUST NOT Discover Canonical State**

STE Gateway MUST NOT discover, query, fetch, or resolve canonical state from any source. Canonical state is provided via Fabric Attestations; Gateway verifies, never discovers.

**P-GW-2: Gateway MUST NOT Enrich Knowledge from External Sources**

STE Gateway MUST NOT enrich eligibility evaluation with knowledge from external sources (Trust Registry, environment variables, configuration files, third-party services). Gateway verifies explicit claims in attestations only.

**P-GW-3: Gateway MUST NOT Fill Gaps in Attestations**

STE Gateway MUST NOT fill gaps when attestations are incomplete. Missing fields, invalid formats, or ambiguous values result in DENY. No default values, no inference, no "best available" fallback.

**P-GW-4: Gateway MUST NOT Cache or Fetch Invariant Content for Comparison**

STE Gateway MUST NOT cache invariant content, fetch invariant content from Fabric, or compare attestation content hashes against cached invariants. Gateway treats content hashes as opaque strings, never as digests to be recomputed or verified.

**P-GW-5: Gateway MUST NOT Compensate for Missing Fabric Attestations**

STE Gateway MUST NOT compensate for missing or invalid Fabric Attestations by falling back to cached attestations, historical state, or Runtime-provided defaults. Missing attestation results in DENY with ATTESTATION_MISSING.

---

## Canonical Role of STE Runtime (Focused Prohibitions)

### Runtime MAY (Permitted Behaviors)

**Runtime Assembly and Transport Capabilities:**

STE Runtime MAY perform the following operations as part of its context assembly and transport responsibilities:

1. **Assemble MVC from Workspace AI-DOC:** Runtime MAY read workspace AI-DOC (feature-branch state), apply RSS (Runtime State-Slicing), and assemble Minimum Viable Context (MVC) for tasks.

2. **Construct Context Bundles with Provisional State:** Runtime MAY construct Context Bundles containing MVC, CEM envelopes, and provisional state markers. Context Bundles are explicitly labeled as provisional and never claim canonical authority.

3. **Request Fabric Attestations:** Runtime MAY request Fabric Attestations from AI-DOC Fabric Intelligence Service by specifying (scope, environment). Runtime requests attestations; Fabric produces and signs them.

4. **Transport Attestations Verbatim:** Runtime MAY transport Fabric Attestations from Fabric to Gateway without modification. Attestations remain cryptographically signed by Fabric; Runtime does not re-sign.

5. **Include Attestations in Eligibility Proposals:** Runtime MAY include Fabric Attestations in Eligibility Proposals submitted to Gateway. Attestations are included verbatim, unchanged from Fabric-provided format.

### Runtime MUST NOT (Prohibited Behaviors)

**Runtime Authority Prohibitions:**

STE Runtime MUST NOT perform the following operations, as they violate the authority boundaries between Runtime and Fabric:

1. **Infer or Derive Canonical State:** Runtime MUST NOT infer canonical state from workspace metadata, git branches, deployment tags, or historical data. Canonical state is explicitly provided by Fabric Attestations, never inferred by Runtime.

2. **Default Missing Invariants or Fill Gaps:** Runtime MUST NOT default missing invariants, fill gaps in Fabric Attestations, or substitute placeholder values when attestations are incomplete. Incomplete attestations result in fail-closed denial at Gateway.

3. **Reconstruct Fabric Output:** Runtime MUST NOT reconstruct Fabric output from cached data, historical attestations, or previous responses. Each execution requires a fresh Fabric Attestation; historical knowledge does not confer authority.

4. **Modify, Enhance, or Reinterpret Attested Content:** Runtime MUST NOT modify attestation fields, enhance attestations with additional data, or reinterpret attestation semantics. Attestations are transported verbatim, unchanged from Fabric-provided format.

5. **Resolve Invariant Conflicts Independently:** Runtime MUST NOT resolve invariant conflicts, determine conflict status, or override Fabric's `conflict_status` field. Conflict resolution is Fabric authority only.

6. **Substitute Runtime Judgment for Fabric Authority:** Runtime MUST NOT substitute Runtime judgment, heuristics, or policies for Fabric authority. Canonical determinations (conflict status, invariant resolution, scope coverage) are Fabric-exclusive.

7. **Sign or Co-Sign Fabric Attestations:** Runtime MUST NOT sign, co-sign, or delegate-sign Fabric Attestations. Fabric Attestations are signed exclusively by Fabric (R-FAB-1).

8. **Override conflict_status or Other Attestation Fields:** Runtime MUST NOT override, recompute, or modify the `conflict_status` field or any other attestation field. Attestations are transported as-provided by Fabric.

### Explicit Rules

**R-RT-1: Runtime MUST Include Fabric Attestations Verbatim**

STE Runtime MUST include Fabric Attestations in Eligibility Proposals exactly as received from Fabric. No modification, no enhancement, no reinterpretation.

**Rationale:** Any modification would invalidate the attestation signature. Fabric signs the entire attestation envelope; changing any field breaks cryptographic integrity.

**Falsifiable:** Verify attestation signature after Runtime inclusion; signature MUST remain valid (no tampering).

**R-RT-2: Runtime MUST NOT Construct or Sign Fabric Attestations**

STE Runtime MUST NOT construct Fabric Attestations, sign attestation envelopes, or claim attestation authority. Attestation construction and signing are Fabric-exclusive operations.

**Rationale:** Runtime has PROJECT authority (§6.1.3), not ORG authority. Only Fabric (ORG authority, §6.1.1) can attest to canonical state.

**Falsifiable:** Inspect attestation signatures; signing identity MUST resolve to Fabric ORG authority, never Runtime PROJECT authority.

**R-RT-3: Runtime MUST Request Attestations from Fabric, Not Compute Them**

STE Runtime MUST request attestations from Fabric Intelligence Service. Runtime MUST NOT compute attestations locally, derive attestations from cached data, or reconstruct attestations from historical state.

**Rationale:** Attestation computation requires canonical authority. Runtime lacks authority to determine canonical state; only Fabric has this authority.

**Falsifiable:** Network trace Runtime process; Runtime MUST send attestation request to Fabric service, not compute locally.

**R-RT-4: Runtime MUST NOT Override or Recompute conflict_status Field**

STE Runtime MUST NOT override, recompute, or modify the `conflict_status` field in Fabric Attestations. Conflict status is a canonical determination made by Fabric only.

**Rationale:** Conflict detection is Fabric authority (ADR-026). If Runtime could override conflict status, Runtime would become a co-authority for conflict determinations, violating the sole authority model.

**Falsifiable:** Inspect attestation `conflict_status` field; value MUST match Fabric-provided value exactly.

**R-RT-5: Runtime Assembly MUST Be Mechanically Compositional Only**

STE Runtime assembly of MVC and Context Bundles MUST be mechanically compositional only. Runtime MUST NOT perform normalization, reconciliation, semantic interpretation, or transformation of canonical data.

**Rationale:** Normalization, reconciliation, and interpretation are reasoning operations that introduce non-determinism. Runtime is a transport layer, not a reasoning layer. Semantic operations violate the "mechanically compositional" constraint.

**Falsifiable:** Inspect Runtime context assembly logic; no semantic normalization (e.g., converting `prod` to `production`), no conflict reconciliation (e.g., choosing between contradictory invariants), no value transformation (e.g., canonicalizing URLs or IDs).

---

## Knowledge Flow Model (Normative)

### One-Way Flow Diagram

```
┌─────────────┐
│Human / Agent│
└──────┬──────┘
       ↓
┌─────────────┐
│   Runtime   │ ← Assembles MVC, constructs Context Bundle
└──────┬──────┘
       ↓ (requests attestation: scope, environment)
┌─────────────┐
│ AI-DOC      │ ← Resolution, conflict detection, signing
│   Fabric    │
└──────┬──────┘
       ↓ (signed attestation)
┌─────────────┐
│   Runtime   │ ← Transports attestation verbatim
└──────┬──────┘
       ↓ (Eligibility Proposal with attestation)
┌─────────────┐
│   Gateway   │ ← Verification ONLY (signature, fields, TTL)
└──────┬──────┘
       ↓ (ALLOW decision + payload)
┌─────────────┐
│Model Provider│
└─────────────┘
```

### Flow Invariants

**INV-FLOW-1: Knowledge Flows Forward Only**

Knowledge flows forward through the system. There is no backward knowledge flow from Gateway to Fabric, Gateway to Runtime (for canonical state discovery), or Runtime to Fabric (for canonical determinations).

**Rationale:** Backward flow reintroduces discovery, which violates the verifier-only posture and creates availability coupling.

**Falsifiable:** Network trace; Gateway does NOT make outbound connections to Fabric or Runtime during eligibility evaluation.

**INV-FLOW-2: Gateway Never Enriches Knowledge**

STE Gateway never enriches knowledge from external sources. Gateway verifies explicit claims in attestations; Gateway does NOT augment attestations with Trust Registry data, environment metadata, or third-party information.

**Rationale:** Enrichment introduces reasoning, which violates the verifier-only posture. Gateway verifies, never enhances.

**INV-FLOW-3: Gateway Never Fills Gaps in Attestations**

STE Gateway never fills gaps when attestations are incomplete. Missing fields, invalid formats, or expired TTLs result in DENY. No default values, no inference, no substitution.

**Rationale:** Gap-filling introduces non-determinism. Different Gateway instances might fill gaps differently, breaking determinism.

**INV-FLOW-4: Gateway Never Compensates for Missing Fabric Output**

STE Gateway never compensates for missing or invalid Fabric Attestations by using cached attestations, historical state, or Runtime-provided defaults. Missing attestation results in immediate DENY.

**Rationale:** Compensation introduces fallback paths, which violate fail-closed enforcement (ADR-022).

**INV-FLOW-5: Runtime Never Substitutes for Fabric Authority**

STE Runtime never substitutes Runtime judgment, heuristics, or cached data for Fabric authority. Canonical state is provided by Fabric Attestations only, never inferred by Runtime.

**Rationale:** Substitution collapses the authority model. If Runtime can act as Fabric, Fabric becomes optional, undermining canonical authority.

**INV-FLOW-6: Canonical Knowledge MUST NOT Be Replayed, Cached, or Reused Outside Validity Window**

Canonical knowledge conveyed via Fabric Attestations MUST NOT be replayed, cached, or reused outside the validity window of the attestation (defined by `issued_at`, `expires_at`, TTL). Historical knowledge does not confer authority.

**Rationale:** Reusing expired attestations introduces staleness and violates the time-bounded nature of canonical truth. Attestations include TTL precisely because canonical state evolves; historical attestations do not reflect current canonical state.

**Falsifiable:** Submit Eligibility Proposal with expired attestation (`current_time > expires_at`); Gateway MUST return DENY with ATTESTATION_EXPIRED. Gateway MUST NOT accept cached attestations from previous requests.

---

## Canonical vs Operational Knowledge Boundary

### Canonical Knowledge (Fabric Authority)

**Canonical Knowledge Definition:**

Canonical knowledge is authoritative truth about system state, invariants, and relationships as determined by AI-DOC Fabric. Canonical knowledge has the following properties:

1. **Owned Exclusively by AI-DOC Fabric:** Only Fabric has authority to establish canonical knowledge. No other component can create, override, or dispute canonical determinations.

2. **Cryptographically Signed by Fabric:** Canonical knowledge is conveyed via Fabric Attestations signed with Fabric ORG authority keys. Signatures provide cryptographic proof of authorship and integrity.

3. **Time-Bounded:** Canonical knowledge is valid within a specific time window (TTL). Attestations include `issued_at`, `expires_at`, and `ttl` fields that bound temporal validity. Expired attestations do not convey canonical authority.

4. **Falsifiable:** Canonical knowledge is falsifiable via signature verification, content hash comparison, and attestation structure inspection. Claims are verifiable, not subjective.

5. **Authoritative, Not Advisory:** Canonical knowledge is binding truth, not suggestions or hints. Gateway treats attestations as authoritative assertions that MUST be enforced, not recommendations that MAY be followed.

### Operational Knowledge (Runtime Assembly)

**Operational Knowledge Definition:**

Operational knowledge is workspace state, provisional context, and execution metadata assembled by Runtime. Operational knowledge has the following properties:

1. **Assembled by Runtime from Workspace State:** Runtime reads feature-branch AI-DOC, applies RSS, and assembles MVC. Operational knowledge reflects workspace state, not canonical state.

2. **Transported to Gateway in Eligibility Proposals:** Runtime includes operational knowledge (MVC, CEM envelope, provenance) in Eligibility Proposals. Operational knowledge provides execution context but does not claim canonical authority.

3. **Never Authoritative on Its Own:** Operational knowledge is never authoritative without accompanying Fabric Attestations. Workspace state is provisional; only Fabric-attested state is canonical.

4. **Never Self-Validating:** Operational knowledge does not self-validate. Runtime cannot attest to the correctness, completeness, or consistency of workspace state. Validation requires Fabric authority.

5. **Explicitly Provisional:** Operational knowledge is explicitly marked as provisional (via provisional state markers in Context Bundle). Runtime clearly distinguishes workspace state from canonical state.

### Boundary Rules

**R-BOUND-1: Gateway MUST Treat Canonical Assertions as Opaque**

STE Gateway MUST treat canonical assertions (invariant identifiers, content hashes, conflict_status, scope, environment) as opaque signed data. Gateway extracts fields for verification but does NOT interpret field semantics.

**Rationale:** Treating assertions as opaque ensures Gateway remains a verifier, not an interpreter. Semantic interpretation introduces reasoning, which violates the verifier-only posture.

**R-BOUND-2: Gateway MUST NOT Reinterpret or Recompute Canonical Claims**

STE Gateway MUST NOT reinterpret canonical claims (e.g., treating `conflict_status: "none"` as "maybe conflicts exist but tolerable") or recompute canonical determinations (e.g., recomputing conflict status by fetching invariants and comparing hashes).

**Rationale:** Reinterpretation and recomputation substitute Gateway judgment for Fabric authority, collapsing the authority model.

**R-BOUND-3: Canonical State Cannot Be Inferred, Defaulted, or Reconstructed**

Canonical state cannot be inferred from operational metadata, defaulted when attestations are missing, or reconstructed from historical data. Canonical state is explicitly provided by Fabric Attestations only.

**Rationale:** Inference, defaulting, and reconstruction introduce non-determinism and violate the fail-closed enforcement model.

**R-BOUND-4: Only Fabric-Signed Attestations Convey Canonical Authority**

Only Fabric-signed attestations convey canonical authority. Runtime-provided claims, workspace metadata, and third-party data do NOT convey canonical authority, regardless of format or content.

**Rationale:** Authority derives from Fabric signing keys verified via Trust Registry. Only Fabric ORG authority can attest to canonical state.

---

## Explicit Failure Semantics (Reinforcement)

### Fail-Closed Triggers (No Exceptions)

The following conditions trigger fail-closed denial with no exceptions, no fallbacks, no partial execution:

- **Missing Fabric attestation** → DENY (ATTESTATION_MISSING)
- **Malformed attestation structure** → DENY (CONTEXT_INCOMPLETE)
- **Invalid attestation signature** → DENY (SIGNATURE_INVALID)
- **Expired attestation** (current_time > expires_at) → DENY (ATTESTATION_EXPIRED)
- **Conflict asserted by Fabric** (conflict_status: "detected") → DENY (INVARIANT_CONFLICT)
- **Scope mismatch** (attestation scope ≠ claimed scope) → DENY (SCOPE_MISMATCH)
- **Environment mismatch** (attestation environment ≠ claimed environment) → DENY (ENVIRONMENT_MISMATCH)
- **Any ambiguity in attestation fields** (invalid conflict_status, missing required fields) → DENY (CONTEXT_INCOMPLETE)

### Prohibited Behaviors

**No Soft Failures:**

The system does NOT support soft failures or partial execution. Eligibility evaluation produces binary outcomes: ALLOW or DENY. No INDETERMINATE for execution; ambiguous conditions result in DENY.

**No Partial Execution States Exist:**

There are no partial execution states where some prerequisites pass and others fail. All prerequisites MUST pass for ALLOW decision. Any prerequisite failure results in DENY.

**No Fallback Paths:**

The system does NOT provide fallback paths when attestations are missing or invalid. No "best available" attestation, no cached historical state, no degraded execution mode. Missing attestation results in immediate DENY.

**No Retry Awareness at Gateway:**

Gateway is stateless; Gateway does NOT track retry attempts, maintain request history, or apply retry-specific logic. Each request is evaluated independently. Resubmitted requests receive identical treatment to initial requests.

**No Compensating Controls:**

Missing or invalid Fabric Attestations cannot be worked around via compensating controls, alternate verification paths, or Runtime-provided defaults. Attestations are non-negotiable prerequisites.

---

## Threat Model Alignment

### Why These Boundaries Exist

**1. Prevents Semantic Drift Across Implementations**

Explicit boundaries prevent implementation variation. If Gateway can parse invariant content, different parsers might handle edge cases differently, breaking determinism. By prohibiting content parsing, all compliant Gateways verify attestations identically.

**2. Prevents Gateway Probing and Reconnaissance Attacks**

Minimal response surface prevents attackers from probing Gateway to extract canonical state structure, invariant identifiers, or organizational topology. Gateway responses contain decision + category only, no evaluation traces or invariant details.

**3. Prevents Runtime Coupling to Canonical State**

Requiring attestations in Eligibility Proposals (rather than Gateway queries to Fabric) decouples Gateway from Fabric availability. Fabric resolution occurs off the execution hot path, preventing Fabric outages from blocking all execution.

**4. Prevents "Helpful" Non-Deterministic Behavior**

Prohibiting gap-filling, inference, and defaulting prevents implementations from "helpfully" compensating for incomplete attestations. "Helpful" behavior introduces non-determinism and breaks fail-closed enforcement.

### What This Does NOT Protect Against

**Fabric Compromise:**

If Fabric signing keys are compromised, attackers can issue fraudulent attestations that Gateway will accept as valid. This ADR assumes Fabric signing key integrity; key compromise is a separate threat addressed by key management, HSMs, and revocation mechanisms.

**Denial-of-Service:**

Fail-closed enforcement may deny legitimate execution when attestations are unavailable, expired, or malformed. This is correct behavior (availability is subordinate to correctness), but creates DoS risk if Fabric is unreliable.

**Organizational Misuse:**

If organizational governance populates Trust Registry incorrectly (e.g., granting ORG authority to untrusted identities), the authority model remains intact but organizational policy is violated. This ADR assumes proper Trust Registry governance.

**Stale Attestations Within TTL:**

Attestations remain valid for their entire TTL, even if canonical state evolves. If Fabric publishes new invariants after issuing an attestation, the attestation remains valid until expiry. TTL bounds staleness but does not eliminate it.

---

## Component Interaction Summary

### AI-DOC Fabric

**Responsibilities:**
- Resolve invariants from canonical stores (Prime, System, Domain)
- Detect conflicts per ADR-026 (scan for duplicate invariant_id with different content_hash)
- Sign Fabric Attestations exclusively with Fabric ORG authority
- Provide attestations to Runtime upon request (via Intelligence Service API)
- Include all required fields in attestations (scope, environment, conflict_status, invariants, TTL, signature)

**Interaction Model:**
- Runtime requests attestations (scope, environment)
- Fabric resolves invariants, detects conflicts, constructs attestation envelope
- Fabric signs attestation with ORG authority keys
- Fabric returns signed attestation to Runtime
- Fabric does NOT interact with Gateway directly

### STE Runtime

**Responsibilities:**
- Assemble MVC from workspace AI-DOC via RSS
- Construct Context Bundles with provisional state markers
- Request attestations from Fabric Intelligence Service
- Receive signed attestations from Fabric
- Include attestations verbatim in Eligibility Proposals
- Transport Eligibility Proposals to Gateway

**Interaction Model:**
- Runtime queries Fabric for attestations (off hot path)
- Runtime receives signed attestations
- Runtime includes attestations unchanged in proposals
- Runtime submits proposals to Gateway for verification
- Runtime does NOT sign, modify, or override attestations

### STE Gateway

**Responsibilities:**
- Receive Eligibility Proposals from Runtime
- Verify attestation signatures via Trust Registry
- Extract attestation fields (scope, environment, conflict_status)
- Verify temporal validity (current_time ≤ expires_at)
- Verify required field presence and format
- Enforce binary eligibility decision (ALLOW | DENY)
- Return decision + category (if DENY) to Runtime

**Interaction Model:**
- Gateway receives proposals containing attestations
- Gateway verifies signatures (Trust Registry lookup)
- Gateway extracts fields for structural validation only
- Gateway returns decision to Runtime
- Gateway does NOT query Fabric, fetch invariant content, or parse invariant semantics

---

## Final Validation Clause

### This Specification is INCORRECT if a Reader Can Reasonably Conclude That

The following inferences are explicitly prohibited. A specification-compliant reader MUST NOT conclude that:

- [ ] Gateway queries AI-DOC Fabric at execution time
- [ ] Gateway reasons over invariant content or semantics
- [ ] Gateway parses, compares, or interprets invariant values beyond attestation structure
- [ ] Gateway implements conflict detection algorithms or recomputes conflict_status
- [ ] Gateway can dispute, challenge, or override Fabric's canonical determinations
- [ ] Fabric is advisory rather than authoritative
- [ ] Fabric attestations can be signed by Runtime or other components
- [ ] Runtime can substitute for Fabric authority or sign attestations
- [ ] Canonical state can be inferred, defaulted, or reconstructed from historical data
- [ ] Eligibility evaluation includes discovery, reconciliation, or semantic reasoning
- [ ] Gateway fills gaps or compensates for missing attestations via fallback mechanisms
- [ ] Knowledge flows backward (Gateway → Fabric queries for canonical state)
- [ ] Attestations are best-effort, advisory, or suggestive rather than cryptographically bound authoritative truth
- [ ] Fail-closed can be bypassed via alternate paths, cached state, or degraded execution modes
- [ ] Gateway caches or replays expired attestations outside their validity window
- [ ] Runtime performs normalization, reconciliation, or semantic interpretation during assembly

### Required Falsifiable Behaviors

A compliant implementation MUST exhibit the following testable, observable behaviors:

1. **Gateway never queries Fabric at runtime:**
   - Network trace Gateway process during eligibility evaluation
   - MUST show zero outbound connections to Fabric services
   - Attestations are provided via Eligibility Proposals, not fetched

2. **Attestations signed by Fabric only:**
   - Verify attestation signature against Trust Registry
   - Signing identity MUST resolve to Fabric ORG authority (§6.1.1)
   - Signing identity MUST NOT resolve to Runtime PROJECT authority (§6.1.3)

3. **Gateway verifies signatures, not content:**
   - Gateway calls signature verification API (Trust Registry)
   - Gateway extracts attestation fields (scope, environment, conflict_status)
   - Gateway MUST NOT parse invariant content (YAML/JSON deserializers forbidden)
   - Gateway MUST NOT fetch invariant content for hash comparison

4. **Missing attestation causes denial:**
   - Submit Eligibility Proposal without Fabric Attestation
   - Gateway MUST return DENY with category ATTESTATION_MISSING
   - No fallback to cached attestations or default state

5. **Malformed attestation causes denial:**
   - Submit attestation with invalid conflict_status (e.g., "unknown")
   - Gateway MUST return DENY with category CONTEXT_INCOMPLETE
   - No inference or defaulting of conflict_status

6. **Runtime transports attestations verbatim:**
   - Runtime receives signed attestation from Fabric
   - Runtime includes attestation in Eligibility Proposal
   - Attestation signature MUST remain valid after Runtime inclusion
   - Tampering detection: modify attestation field → signature verification fails

7. **Fail-closed on ambiguity:**
   - Any ambiguous condition (missing field, expired TTL, invalid format)
   - Gateway MUST return DENY, never partial execution or INDETERMINATE
   - No "best effort" enforcement or degraded execution modes

8. **Gateway treats Fabric conflict_status as final:**
   - Submit attestation with conflict_status: "detected"
   - Gateway MUST return DENY with INVARIANT_CONFLICT
   - Gateway MUST NOT recompute conflicts, even if Gateway "thinks" no conflicts exist
   - Gateway has zero authority to dispute Fabric's determination

9. **Expired attestations are rejected:**
   - Submit attestation where current_time > expires_at
   - Gateway MUST return DENY with ATTESTATION_EXPIRED
   - Gateway MUST NOT cache or reuse expired attestations from prior requests

10. **Runtime assembly is mechanically compositional:**
    - Inspect Runtime context assembly logic
    - MUST show mechanical composition (read AI-DOC, apply RSS, construct bundle)
    - MUST NOT show normalization (e.g., `prod` → `production` conversion)
    - MUST NOT show reconciliation (choosing between contradictory values)
    - MUST NOT show semantic interpretation (inferring missing fields from context)

---

## Consequences

### Positive

**1. Deterministic Eligibility Enforcement**

Given identical Eligibility Proposal (with identical Fabric Attestation), all compliant Gateway implementations produce identical eligibility decisions. No implementation variation, no cache-dependent behavior, no non-deterministic reasoning.

**Benefit:** Interoperability, reproducibility, auditing confidence. Organizations can deploy multiple Gateway instances with certainty that decisions are consistent.

**2. Falsifiable Authority Boundaries**

Authority boundaries are explicit and testable. Auditors, operators, and implementers can verify that Gateway never queries Fabric, Runtime never signs attestations, and Fabric is the sole canonical authority.

**Benefit:** Auditability, compliance verification, security assurance. Authority violations are detectable via inspection or replay.

**3. Minimal Gateway Implementation Complexity**

Gateway performs signature verification and field extraction only. No invariant parsing, no conflict detection, no semantic validation, no content comparison. Simplified implementation reduces bugs and certification burden.

**Benefit:** Faster Gateway development, easier security review, lower maintenance costs.

**4. Fabric Resolution Off Hot Path**

Fabric attestations are requested by Runtime before execution eligibility evaluation, not by Gateway during evaluation. Fabric outages do not block execution eligibility decisions (assuming valid attestations exist).

**Benefit:** Gateway latency independent of Fabric availability. Execution hot path decoupled from canonical state resolution latency.

**5. No Semantic Drift Across Implementations**

Prohibiting Gateway content parsing and conflict detection prevents implementation variation. All compliant Gateways verify attestations identically; no "enhanced" or "improved" Gateways that introduce non-standard behavior.

**Benefit:** Interoperability, determinism, specification stability. Gateway implementations are fungible.

**6. Minimal Response Surface Maintained**

Gateway responses contain decision (ALLOW | DENY) and category (if DENY) only. No invariant identifiers, no conflict details, no evaluation traces, no provenance. Attackers gain no reconnaissance information from Gateway probing.

**Benefit:** Reduced information leakage, limited reconnaissance surface, simpler response parsing.

### Negative

**1. Fabric Becomes Critical Dependency for Attestations**

Runtime depends on Fabric to provide attestations. If Fabric is unavailable, Runtime cannot obtain attestations, and Gateway denies execution. Fabric availability is critical for execution eligibility.

**Impact:** Fabric outages block new execution. Existing valid attestations (within TTL) continue to work, but fresh attestations cannot be obtained.

**Mitigation:** Fabric redundancy, high-availability deployment, attestation caching within TTL (Runtime-side, not Gateway-side).

**2. No Cross-Component Redundancy**

Fabric is sole canonical authority; no component can substitute for Fabric. If Fabric signing keys are lost, canonical authority is lost. No backup authority exists.

**Impact:** Fabric key management is critical. Key loss is catastrophic; no recovery path without re-establishing canonical state.

**Mitigation:** HSM-based key storage, key backup procedures, disaster recovery planning.

**3. Gateway Cannot Provide Debugging Detail**

Gateway responses contain minimal information (decision + category). Operators cannot diagnose eligibility failures from Gateway responses alone; must inspect attestations directly.

**Impact:** Debugging harder; operators need access to attestation storage, parsing tools, and Fabric APIs to diagnose denials.

**Mitigation:** CLI tools for attestation inspection, Gateway audit logs with request IDs for correlation, troubleshooting documentation.

**4. Runtime Must Request Attestations Explicitly**

Runtime must explicitly request attestations from Fabric for each (scope, environment) combination. No implicit attestation discovery; Runtime must know what to request.

**Impact:** Runtime complexity increases; Runtime must manage attestation requests, cache attestations within TTL, and handle Fabric request failures.

**Mitigation:** Runtime attestation caching (within TTL), clear attestation request patterns in Runtime specification.

**5. No "Best Available" Execution Mode**

When attestations are missing, invalid, or expired, Gateway denies execution with no fallback. No degraded execution mode, no cached historical state, no provisional execution.

**Impact:** Fail-closed enforcement prioritizes correctness over availability. Legitimate execution may be denied when attestations are unavailable.

**Mitigation:** Attestation TTL tuning (balance freshness vs. availability), Fabric high-availability design, operational monitoring of attestation issuance.

### Neutral

**1. Authority Boundaries Are Policy Decisions**

This ADR codifies authority boundaries as architectural constraints, not organizational policy. Organizations cannot choose alternate authority models without violating STE-System conformance.

**Implication:** Organizations adopting STE-System must accept that Fabric is sole canonical authority, Gateway is pure verifier, and Runtime is transport layer. No organizational flexibility on these boundaries.

**2. Attestation TTL Tuning Is Organizational Concern**

Specification defines attestation TTL semantics (time-bounded validity) but does not prescribe TTL values. Organizations choose TTL values based on staleness tolerance and availability requirements.

**Implication:** Short TTL (e.g., 5 minutes) provides freshness but increases Fabric load and denial risk. Long TTL (e.g., 1 hour) reduces Fabric load but permits stale attestations.

**3. No Gateway-Side Caching**

Gateway does not cache attestations, invariant content, or canonical state. Each eligibility evaluation is independent, relying solely on attestation provided in request.

**Implication:** Gateway is stateless and horizontally scalable but cannot amortize verification costs across requests. Runtime-side attestation caching (within TTL) is recommended.

---

## Related Decisions

- **ADR-019: Gateway Authority and Signing Model** - Establishes Gateway operates with enforcement authority, not attestation authority. This ADR codifies Gateway as pure verifier, never attesting to canonical state.

- **ADR-022: Fail-Closed Enforcement Scope** - Defines fail-closed triggers and denial semantics. This ADR reinforces fail-closed behavior: missing/invalid attestations result in DENY, no fallbacks.

- **ADR-024: Cross-Component Contracts** - Defines Gateway as pure validator that does not modify requests. This ADR extends: Gateway not only doesn't modify requests, Gateway also doesn't query Fabric or reason over content.

- **ADR-026: Invariant Conflict Detection Semantics** - Establishes Fabric detects conflicts and attests to conflict_status; Gateway verifies attestation. This ADR codifies Gateway MUST treat Fabric's conflict_status as authoritative and final, with zero authority to dispute.

- **ADR-027: Scope Semantics** - Defines scope as explicit, mandatory dimension with versioned matching. This ADR applies scope matching to attestation verification: Gateway verifies attestation scope matches claimed scope per ADR-027 algorithms.

---

## Traceability

**Closes Gap:** Implicit tribal knowledge about Fabric/Gateway/Runtime roles and authority boundaries

**Requirements:**
- §7.1 Canonical State (G-CAN-1: "For any given environment and element identity, canonical state is unambiguous") - Fabric is sole authority for canonical state
- §5.3.2 Gateway Responsibilities (R-GW-3: "Resolving canonical Prime and System invariants from ADF") - Now clarified: via attestations, not runtime queries
- §5.2.2 Runtime Responsibilities (R-RT-4: "Produce CEM envelopes") - Now clarified: Runtime transports attestations, does not sign them
- §8.1.2 Eligibility Prerequisites (PREREQ-3: "Canonical Invariant Availability") - Now clarified: via Fabric Attestations in Eligibility Proposal
- §8.1.4 Eligibility Evaluation Algorithm (STEP 4: "Check for conflicts") - Now clarified: Gateway verifies Fabric's attested conflict_status, does not recompute

**Stakeholders:**
- ADF Implementers (must sign attestations exclusively, perform conflict detection)
- Gateway Implementers (must verify attestations, MUST NOT query Fabric or parse invariant content)
- Runtime Implementers (must request and transport attestations, MUST NOT sign attestations)
- Security/Compliance Teams (authority boundaries are security boundaries)
- Enterprise Architects (authority boundaries define system correctness)

---

**Last Updated:** 2025-12-29  
**Status:** Accepted  
**Next Review:** After v1 Implementation Feedback


