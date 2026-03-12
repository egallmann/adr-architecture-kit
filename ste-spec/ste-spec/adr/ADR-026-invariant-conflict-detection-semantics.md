# ADR-026: Invariant Conflict Detection Semantics

**Status:** Accepted  
**Date:** 2025-12-29  
**Closes Gap:** GAP-3 (Invariant Conflict Detection Algorithm / Blocker 2.3)

---

## Context

The STE-System specification requires conflict detection as a prerequisite for eligibility evaluation (§8.1.2 PREREQ-4: "Resolved invariants MUST NOT contain internal contradictions or unresolved conflicts"). The eligibility algorithm explicitly checks for conflicts (§8.1.4 STEP 4). The denial classification schema includes an `INVARIANT_CONFLICT` category. However, the specification does not define what constitutes a conflict, how conflicts are detected, or who performs detection.

This ambiguity creates critical correctness risks:

1. **Non-Determinism Across Implementations:** Without a normative conflict detection algorithm, different Gateway implementations could produce different eligibility decisions for identical inputs. One Gateway might detect a conflict and deny execution; another might miss the conflict and allow execution. This violates the determinism claim (§8.1.4: eligibility evaluation is deterministic).

2. **Incorrect Conformance Claims:** If conflict semantics are undefined, an implementation could claim conformance while permitting contradictory invariants to authorize execution. Two invariants asserting incompatible constraints (e.g., `PRIME-1` with different content) could both be "resolved" without triggering rejection, undermining canonical state guarantees (§7.1.1: "For any given environment and element identity, canonical state is unambiguous").

3. **Unenforced Prerequisites:** PREREQ-4 normatively requires "no invariant conflicts," but without defining conflicts, this requirement cannot be verified or enforced. Implementations must guess what "conflict" means, leading to divergent interpretations and enforcement gaps.

4. **Ambiguous Authority Boundaries:** ADR-023 establishes that Gateway performs normative conflict detection during eligibility evaluation, while ADF performs preventative conflict detection during merge-time validation. However, without defining the detection algorithm, implementations cannot determine what to detect or how to report conflicts consistently.

5. **Inconsistent Denial Classification:** The `INVARIANT_CONFLICT` denial category exists but cannot be applied consistently without defining which conditions trigger it. What distinguishes a conflict from a validation failure? When does Gateway return `INVARIANT_CONFLICT` versus `CONTEXT_INCOMPLETE`?

**Conflict detection is not optional metadata validation.** Conflicts represent violations of canonical state integrity: the same invariant identifier with differing content undermines the unambiguous canonical state guarantee that defines the STE-System correctness model.

### Architectural Foundations (Established by Prior ADRs)

**AI-DOC Fabric Authority (§7.1, §6.1.1):**  
AI-DOC Fabric is the exclusive authoritative source for canonical state. Fabric publishes canonical invariants, signs Fabric Attestations, and determines which invariants are canonical for a given (scope, environment). No other component has authority to establish canonical truth.

**Gateway Verifier-Only Posture (ADR-019, ADR-024):**  
Gateway enforces attestations but does not create them. Gateway verifies signatures, checks prerequisites, and validates structural correctness. Gateway does NOT perform state discovery, content interpretation, or semantic reasoning. Gateway is a pure verifier: it validates claims made by authoritative signers, but does not generate those claims.

**Fail-Closed Enforcement (ADR-022):**  
Ambiguous or unverifiable conditions result in denial, never partial execution or best-effort enforcement. If a prerequisite cannot be deterministically verified, execution is denied. No "maybe" states.

**Conflict Surfacing, Not Resolution (ADR-009):**  
The STE-System surfaces conflicts for human investigation; it does not automatically resolve them. No precedence rules, no conflict resolution algorithms, no policy interpretation. When extracted and asserted facts conflict, both are preserved with provenance, and the conflict is reported. Automatic resolution would hide contradictions and undermine audit transparency.

### Existing Responsibility Allocation (ADR-023)

ADR-023 established timing and responsibility for conflict detection:

- **Gateway (Normative):** Gateway SHALL execute deterministic invariant conflict detection during eligibility evaluation (§8.1.4 eligibility algorithm, PREREQ-4). Conflict detection is mandatory for execution eligibility. Gateway conflict detection is the authoritative enforcement boundary.

- **ADF (Preventative):** ADF MAY execute the same conflict detection algorithm during merge-time validation (§10.1.3). Purpose: prevent conflicts from entering canonical stores (fail fast at merge, before publication). ADF conflict detection is preventative optimization, not authoritative enforcement.

However, ADR-023 does not define the detection algorithm itself. It establishes **who** detects and **when**, but not **what** to detect or **how** to report it. GAP-3 exists because the algorithm remains undefined.

### Why Gateway-Side Detection is Architecturally Forbidden

The Gateway verifier-only posture (ADR-019) prohibits Gateway from implementing conflict detection algorithms that parse, compare, or evaluate invariant content:

- **Content Parsing Violates Verifier Posture:** If Gateway parses invariant YAML/JSON to extract keys and values, Gateway is no longer a pure verifier. Gateway would need invariant schema knowledge, content interpretation logic, and comparison algorithms. This introduces implementation variation: different Gateways might parse differently, compare differently, or handle edge cases differently.

- **Comparison Logic Introduces Non-Determinism:** If Gateway compares invariant content digests fetched from ADF, Gateway must cache or fetch canonical artifacts. This reintroduces state discovery (explicitly prohibited) and creates cache invalidation, network failure, and staleness concerns. Determinism depends on cache behavior, which varies by implementation.

- **Algorithm Variation Breaks Interoperability:** If each Gateway implements its own conflict detection algorithm, different Gateways produce different decisions for identical Context Bundles. A Context Bundle denied by Gateway A might be allowed by Gateway B. This violates the fundamental determinism requirement.

The only deterministic, implementation-neutral approach is: **Fabric detects conflicts and attests to conflict status; Gateway verifies the attestation.**

## Problem Statement

The specification must answer the following questions to enable deterministic, verifiable conflict enforcement:

1. **What is a conflict?** Is it a syntactic duplicate (same invariant ID, different content hash)? A semantic contradiction (logical incompatibility)? A key-value mismatch within invariant structure?

2. **What is the conflict detection scope?** Per attestation? Across multiple attestations? Across environments? Across time (temporal conflicts)?

3. **Who performs conflict detection?** Fabric, Gateway, Runtime, or a combination? If multiple components detect, which is authoritative?

4. **How is conflict detection performed?** What algorithm compares invariants? Exact string match? Digest comparison? Semantic analysis?

5. **How are conflicts reported?** Does Gateway response include conflict details (which invariants conflicted, provenance)? Or minimal response surface (decision + category only)?

6. **What guarantees determinism?** How do we ensure identical Context Bundles produce identical decisions across all compliant Gateway implementations?

7. **What is the denial category?** When does Gateway return `INVARIANT_CONFLICT` versus `CONTEXT_INCOMPLETE` versus `INVARIANT_VALIDATION_FAILURE`?

These questions have **no answers** in the current specification. ADR-023 assigns responsibility (Gateway normative, ADF preventative) but does not define the algorithm. §8.1.2 PREREQ-4 requires conflict detection but does not define conflicts. GAP-3 exists because every implementer must invent conflict semantics, breaking determinism and interoperability.

**Explicit Constraint:**  
Gateway-side conflict detection algorithms are **forbidden** by the verifier-only posture (ADR-019, ADR-024). Gateway MUST NOT parse invariant content, compare invariant values, compute content digests, or implement any conflict detection logic beyond verifying attestation signatures and required fields.

## Decision

**Conflict detection is Fabric-authoritative; Gateway enforces via attestation verification.**

### v1 Baseline

For STE-System v1, conflict detection is defined as:

**Fabric performs conflict detection during attestation creation and attests to conflict status as a required field. Gateway verifies the attestation signature and enforces based on the attested conflict status. Gateway does not implement conflict detection algorithms or parse invariant content.**

Conflict detection semantics live in **AI-DOC Fabric**, not in Gateway logic, Runtime logic, or implementation-specific heuristics. Fabric defines whether conflicts exist for a given (scope, environment) and signs that determination into the Fabric Attestation. Gateway enforces exact matching on the `conflict_status` field. No component interprets conflict semantics beyond Fabric's attested claim.

This decision intentionally restricts v1 to the minimal correctness-preserving definition. Features that introduce Gateway-side detection, semantic analysis, or cross-attestation conflict detection are explicitly deferred to future work.

### Mechanism

**Fabric Attestation Structure Extension:**  
Every Fabric Attestation MUST include a `conflict_status` field with value `"none"` or `"detected"`. This field is part of the signed attestation envelope.

**Gateway Enforcement:**  
Gateway verifies attestation signature (which covers `conflict_status`) and enforces as follows:
- If `conflict_status: "none"` → continue eligibility evaluation
- If `conflict_status: "detected"` → return DENY with category `INVARIANT_CONFLICT`
- If `conflict_status` field is missing, malformed, or contains any value other than `"none"` or `"detected"` → return DENY with category `CONTEXT_INCOMPLETE`

**Fabric Detection Algorithm (Normative for Fabric, Opaque to Gateway):**  
Fabric scans all invariant arrays within the attestation (prime_invariants, system_invariants, domain_invariants) and detects conflicts as defined below. Gateway does NOT implement this algorithm; Gateway verifies Fabric's attested determination.

## Normative Definitions

### Conflict (v1)

A **conflict** exists when two or more canonical invariants within a single Fabric Attestation for a given (scope, environment) have identical canonical identifiers but different content digests.

**Formal Definition:**  
Given a Fabric Attestation for (scope S, environment E) containing invariants `I = {i₁, i₂, ..., iₙ}` where each invariant `iⱼ` has:
- `invariant_id`: canonical identifier (string)
- `content_hash`: content digest (string, e.g., "sha256:abc123...")

A conflict exists if and only if:  
∃ i, j ∈ I : (i.invariant_id = j.invariant_id) ∧ (i.content_hash ≠ j.content_hash)

**Scope:** Conflicts are detected per attestation. Cross-attestation conflicts (different scopes, different timestamps) are out of scope for v1.

**Environment Isolation:** Conflicts are detected within one environment. Cross-environment conflicts (e.g., `prod` invariant conflicting with `staging` invariant) are out of scope per ADR-025 environment partitioning.

### Canonical Identifier

**Canonical Identifier** is the Fabric-issued identifier for an invariant.

**Format:** Non-empty string, typically hierarchical (e.g., `PRIME-1`, `SYS-ARCH-3`, `INV-custom-001`).

**Comparison:** Exact string equality only. Case-sensitive. No pattern matching, no hierarchy interpretation, no normalization.

**Examples (Illustrative):**
- `PRIME-1` (Prime Invariant)
- `SYS-ENF-4` (System Enforcement Invariant)
- `AWS-IAM-LEAST-PRIVILEGE` (Domain Invariant)

**Non-Examples (Do Not Match):**
- `PRIME-1` ≠ `prime-1` (case mismatch)
- `PRIME-1` ≠ `PRIME-01` (string inequality)
- `SYS-ENF-4` ≠ `SYS-*` (no wildcard matching)

### Content Digest

**Content Digest** is the Fabric-issued cryptographic hash of the canonicalized invariant content.

**Format:** Algorithm prefix + colon + hexadecimal digest (e.g., `sha256:abc123def456...`).

**Comparison:** Exact byte equality. No normalization, no algorithm conversion.

**Purpose:** Content digest enables conflict detection without requiring Gateway to fetch or parse invariant content. If two invariants have the same canonical identifier but different content digests, they conflict.

**Example:**
```yaml
invariant_id: PRIME-1
content_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

If another invariant in the same attestation has:
```yaml
invariant_id: PRIME-1
content_hash: sha256:d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592
```

This is a conflict: same `invariant_id`, different `content_hash`.

### Detection Scope (Per Attestation)

Conflicts are detected per attestation across all invariant arrays combined:
- `prime_invariants`
- `system_invariants`
- `domain_invariants`

Fabric scans these arrays for duplicate canonical identifiers with differing content digests. If any conflict is found, Fabric sets `conflict_status: "detected"`.

**Cross-Attestation Conflicts (Out of Scope for v1):**  
Conflicts between invariants in different attestations (different scopes, different timestamps, different environments) are NOT detected in v1. Each attestation is evaluated independently.

**Rationale:** Cross-attestation conflict detection requires aggregation, precedence rules, and temporal ordering semantics. These introduce complexity and interpretation that are deferred to v2+.

## Authoritative Rules (Normative)

The following requirements apply to all compliant STE-System implementations:

### R-CONF-1: Fabric Conflict Detection Mandatory

AI-DOC Fabric MUST perform conflict detection during attestation creation for the (scope, environment) being attested.

**Detection Algorithm (Fabric Responsibility):**
1. Collect all invariants from `prime_invariants`, `system_invariants`, `domain_invariants` arrays
2. For each pair of invariants (i, j):
   - If `i.invariant_id == j.invariant_id` (exact string equality)
   - And `i.content_hash != j.content_hash` (exact string inequality)
   - Then conflict detected
3. If any conflict detected, set `conflict_status: "detected"`
4. If no conflicts detected, set `conflict_status: "none"`

**Rationale:** Fabric is authoritative for canonical state. Only Fabric can definitively determine whether invariants conflict within a given (scope, environment). Fabric detection ensures consistency across all Gateway implementations.

**Prohibition:** Fabric MUST NOT issue attestations without performing conflict detection. Omitting detection violates canonical state integrity guarantees.

### R-CONF-2: Conflict Status Field Mandatory

Every Fabric Attestation MUST include a `conflict_status` field with value `"none"` or `"detected"`.

**Field Location:** Top-level field in attestation envelope (sibling to `scope`, `environment`, `prime_invariants`, etc.).

**Field Type:** String enum with exactly two permitted values: `"none"` | `"detected"`.

**Rationale:** Conflict status is a required prerequisite for eligibility evaluation (PREREQ-4). Omitting the field makes attestation incomplete and unverifiable.

**Prohibition:** Fabric MUST NOT issue attestations that omit `conflict_status`. Gateway MUST reject attestations without `conflict_status` (see R-CONF-5).

### R-CONF-3: Conflict Status Mutually Exclusive

Fabric MUST assert exactly one status: `conflict_status: "none"` OR `conflict_status: "detected"`.

**Malformed Examples:**
```yaml
# Invalid: both values
conflict_status: "none"
conflict_status: "detected"

# Invalid: array of values
conflict_status: ["none", "detected"]

# Invalid: boolean instead of string
conflict_status: false

# Invalid: unrecognized value
conflict_status: "unknown"
```

**Rationale:** Conflict status is binary: conflicts exist or they do not. Ambiguous or contradictory status values violate fail-closed enforcement (ADR-022).

**Prohibition:** Gateway MUST reject attestations with malformed `conflict_status` (see R-CONF-5).

### R-CONF-4: Gateway Enforcement on Conflict Present

If `conflict_status: "detected"`, Gateway MUST return decision DENY with category `INVARIANT_CONFLICT`. No exceptions.

**Enforcement Logic:**
```
if attestation.conflict_status == "detected":
    return DENY(category=INVARIANT_CONFLICT)
```

**Rationale:** Conflicts violate canonical state unambiguity (§7.1.1). Permitting execution when conflicts exist would authorize execution based on contradictory invariants, undermining correctness guarantees.

**Prohibition:** Gateway MUST NOT permit execution when `conflict_status: "detected"`. No conditional logic, no override mechanisms, no best-effort execution.

### R-CONF-5: Gateway Denial on Missing Status

If `conflict_status` field is missing, malformed, or contains a value other than `"none"` or `"detected"`, Gateway MUST return DENY with category `CONTEXT_INCOMPLETE`.

**Triggering Conditions:**
- `conflict_status` field absent from attestation
- `conflict_status` is null or empty string
- `conflict_status` has value other than `"none"` or `"detected"` (e.g., `"unknown"`, `"indeterminate"`, `"pending"`)
- `conflict_status` is non-string type (boolean, number, array, object)

**Enforcement Logic:**
```
if attestation.conflict_status not in ["none", "detected"]:
    return DENY(category=CONTEXT_INCOMPLETE)
```

**Rationale:** Missing or malformed conflict status makes attestation incomplete. Gateway cannot verify PREREQ-4 compliance without explicit conflict status. Fail-closed enforcement requires denial on ambiguity.

**Prohibition:** Gateway MUST NOT infer, default, or compute conflict status. Conflict status is an explicit attestation field, not a computed value.

### R-CONF-6: Gateway Prohibition on Content Parsing

Gateway MUST NOT parse invariant content, compare invariant values, compute content digests, or implement any conflict detection algorithm.

**Prohibited Operations:**
- Parsing invariant YAML/JSON structure
- Extracting keys or values from invariant content
- Comparing invariant content digests to cached or fetched artifacts
- Fetching canonical invariant content from ADF
- Implementing conflict detection logic (scanning for duplicates, comparing hashes)
- Inferring conflict status from invariant structure

**Permitted Operations:**
- Verifying attestation signature (includes `conflict_status` field)
- Extracting `conflict_status` field from signed attestation
- String equality comparison: `attestation.conflict_status == "detected"`

**Rationale:** Gateway is a pure verifier (ADR-019). Content parsing, comparison, and detection introduce implementation variation and violate verifier-only posture. Determinism requires Gateway to verify Fabric's attested claim, not recompute it.

**Prohibition:** Any Gateway implementation that parses invariant content or implements conflict detection is non-compliant.

### R-CONF-7: Conflict Status Cryptographically Bound

The `conflict_status` field MUST be included in the signed portion of Fabric Attestation. Tampering with conflict status MUST invalidate signature verification.

**Signature Coverage:**  
Fabric Attestation signature covers:
- Attestation metadata (attestation_id, issued_at, expires_at, ttl)
- Scope and environment
- Invariant arrays (prime_invariants, system_invariants, domain_invariants)
- **`conflict_status` field**
- Provenance (attested_by, adf_query_timestamp)

**Rationale:** If `conflict_status` is not signed, an attacker could modify attestation from `conflict_status: "detected"` to `conflict_status: "none"`, bypassing enforcement. Cryptographic binding ensures tamper-evidence.

**Verification:** Gateway signature verification MUST fail if `conflict_status` is modified post-signing.

### R-CONF-8: Ambiguity Causes Denial

Any ambiguous, unverifiable, or contradictory condition regarding conflict status results in DENY.

**Examples:**
- Attestation claims `conflict_status: "none"` but signature verification fails → DENY (SIGNATURE_INVALID)
- Attestation has multiple `conflict_status` fields with different values → DENY (CONTEXT_INCOMPLETE)
- Attestation `conflict_status` is a non-string type → DENY (CONTEXT_INCOMPLETE)
- Attestation signature is valid but `conflict_status` value is `"unknown"` → DENY (CONTEXT_INCOMPLETE)

**Rationale:** Fail-closed enforcement (ADR-022) requires rejection when prerequisites cannot be deterministically verified. Ambiguity in conflict status prevents reliable enforcement.

**Prohibition:** Gateway MUST NOT attempt to resolve ambiguity, guess conflict status, or fall back to "best available" attestation. Ambiguity results in immediate denial.

## What This Guarantees

When conflict semantics are correctly implemented per this ADR, the STE-System provides:

### 1. Deterministic Gateway Enforcement

Given identical Fabric Attestation with identical `conflict_status` value, all compliant Gateway implementations produce identical eligibility decisions.

**Falsifiable:** Submit same attestation to different Gateway instances; decisions must match. Replay same attestation at different times; decision must be identical (within attestation TTL).

**Mechanism:** Gateway performs signature verification + field extraction only. No content parsing, no algorithm variation, no implementation-specific logic. Determinism follows from cryptographic verification.

### 2. Deterministic Conflict Semantics (Fabric-Attested)

Fabric attests to conflict status based on canonical identifier + content digest comparison. Conflict definition is explicit, falsifiable, and implementation-neutral.

**Falsifiable:** Inspect attestation `prime_invariants`, `system_invariants`, `domain_invariants` arrays. If duplicate canonical identifiers with differing content digests exist, `conflict_status` MUST be `"detected"`. If no duplicates exist, `conflict_status` MUST be `"none"`.

**Mechanism:** Fabric detection algorithm is normative (defined in R-CONF-1). Fabric signs the result. Gateway trusts signed attestation without recomputation.

### 3. Falsifiability via Attestation Inspection

Conflict status is explicitly declared in signed attestation. Auditors, operators, and implementers can verify conflict determination by inspecting attestation structure.

**Falsifiable:**
1. Extract `conflict_status` field from attestation
2. Verify signature covers `conflict_status`
3. If `conflict_status: "detected"`, expect Gateway to deny
4. If `conflict_status: "none"`, expect Gateway to continue evaluation (no automatic denial)

**No Hidden Logic:** Conflict status is not inferred, computed, or derived. It is an explicit signed field.

### 4. Fail-Closed on Ambiguity

Missing, malformed, or unverifiable `conflict_status` results in denial. No best-effort execution, no partial enforcement, no "maybe" states.

**Falsifiable:** Submit attestation without `conflict_status` field → Gateway MUST return DENY with CONTEXT_INCOMPLETE. Modify `conflict_status` without re-signing → Gateway MUST return DENY with SIGNATURE_INVALID.

### 5. Minimal Response Surface Preserved

Gateway response contains decision (ALLOW | DENY), denial category (if DENY), and timestamp. No conflict details, no invariant identifiers, no provenance, no evaluation trace.

**Falsifiable:** Inspect Gateway response structure. Response MUST NOT include:
- Which invariants conflicted
- Conflicting canonical identifiers
- Content hashes of conflicting invariants
- Provenance of conflicting invariants
- Resolution recommendations

**Rationale:** Minimal response surface reduces information leakage and prevents reconnaissance attacks (Threat Model section).

## What This Explicitly Does NOT Guarantee

Conflict detection is a **structural correctness check**, not a semantic reasoning capability. The following properties are **not** guaranteed by v1 conflict semantics:

### 1. Semantic Contradiction Detection (v1)

V1 detects **syntactic conflicts** only: same canonical identifier with different content digest.

**Not Detected (v1):**
- Logical contradictions across different invariants (e.g., `max_retries: 5` in PRIME-1 vs `max_retries: 3` in SYS-2)
- Overlapping constraints (e.g., `allowed_regions: [us-east-1, us-west-2]` vs `denied_regions: [us-east-1]`)
- Incompatible policies (e.g., `encryption: required` vs `encryption: optional`)

**Rationale:** Semantic analysis requires reasoning engines, schema knowledge, and interpretation logic. This introduces non-determinism and cannot be verified by signature alone. Deferred to v2+.

**Implication:** Two invariants may be logically incompatible but not trigger v1 conflict detection if they have different canonical identifiers.

### 2. Cross-Attestation Conflict Detection (v1)

Conflicts between invariants in different attestations are not detected.

**Not Detected (v1):**
- Invariant in attestation A (scope `project:backend`, timestamp T1) conflicts with invariant in attestation B (scope `project:frontend`, timestamp T2)
- Same invariant identifier appearing in multiple attestations with different content hashes

**Rationale:** Cross-attestation conflict detection requires aggregation, precedence rules (which attestation is authoritative?), and temporal ordering (which is newer?). These introduce interpretation and complexity. Deferred to v2+.

**Implication:** Each attestation is evaluated independently. Conflicts across attestations are not surfaced by v1 mechanism.

### 3. Cross-Environment Conflict Detection (v1)

Conflicts between invariants in different environments are not detected.

**Not Detected (v1):**
- Invariant PRIME-1 in environment `prod` has different content than PRIME-1 in environment `staging`

**Rationale:** Environments are isolated canonical state partitions per ADR-025. Each environment has independent canonical state. Cross-environment consistency is not enforced by conflict detection.

**Implication:** `prod` and `staging` may have divergent invariants. This is permitted by design (environments partition state).

### 4. Conflict Resolution or Precedence

The system surfaces conflicts; it never resolves them.

**Not Provided:**
- Automatic conflict resolution based on recency, precedence, or policy
- Selection of "winning" invariant when conflicts exist
- Merging or aggregating conflicting invariants

**Rationale:** Conflict resolution requires precedence rules, trust models, and policy interpretation. ADR-009 establishes coexistence with conflict surfacing, not automatic resolution. Humans investigate and resolve conflicts.

**Implication:** When `conflict_status: "detected"`, execution is denied. Conflicts must be resolved at the source (Fabric canonical state) before attestation can claim `conflict_status: "none"`.

### 5. Conflict Provenance or Detail in Responses

Gateway responses do not include conflict detail.

**Not Included in Response:**
- Which invariants conflicted (canonical identifiers)
- Content hashes of conflicting invariants
- Provenance of conflicting invariants (extracted vs asserted, source files, timestamps)
- Resolution recommendations or debugging guidance

**Rationale:** Minimal response surface (threat model). Including conflict detail expands response payload, increases parsing complexity, and enables reconnaissance attacks.

**Implication:** Operators must inspect Fabric Attestation directly to diagnose which invariants conflicted. Gateway response contains only: DENY + INVARIANT_CONFLICT.

### 6. Hierarchical or Pattern-Based Conflict Detection

V1 uses exact canonical identifier matching only.

**Not Supported (v1):**
- Wildcard matching (e.g., `PRIME-*` conflicts with `PRIME-1`)
- Prefix matching (e.g., `SYS-ENF` conflicts with `SYS-ENF-4`)
- Hierarchical conflict detection (e.g., parent scope invariant conflicts with child scope invariant)

**Rationale:** Pattern matching and hierarchy interpretation introduce ambiguity and implementation variation. Exact string matching is deterministic and falsifiable.

**Implication:** Only invariants with exactly matching canonical identifiers can conflict. `PRIME-1` does not conflict with `PRIME-01` or `prime-1`.

## Alternatives Considered

| Alternative | Pros | Cons | Rejection Rationale |
|-------------|------|------|---------------------|
| **Gateway-side conflict detection** (Gateway implements algorithm to scan invariants and detect conflicts) | Gateway can independently verify conflicts; no dependency on Fabric attestation accuracy; conflict detection guaranteed at enforcement boundary | Violates verifier-only posture (ADR-019); requires Gateway to parse/compare invariant content; introduces implementation variation (different Gateways might detect differently); breaks determinism guarantee; requires Gateway to fetch or cache invariant content; reintroduces state discovery | **REJECTED:** Gateway MUST NOT implement detection algorithms. Parsing invariant content, comparing digests, and implementing detection logic violate architectural constraints. Implementation variation breaks determinism. This alternative contradicts the verifier-only posture that defines Gateway's role. |
| **Fabric authoritative with attested status** (Fabric detects conflicts and signs status into attestation; Gateway verifies signature and enforces) | Gateway remains pure verifier (signature + field extraction only); conflict detection centralized in Fabric (single source of truth); deterministic via cryptographic verification; falsifiable via attestation inspection; no implementation variation at Gateway; clear separation of concerns (Fabric detects, Gateway enforces) | Fabric must perform detection (Fabric complexity increases); attestation schema expands (new required field); no cross-attestation conflict detection in v1 (deferred); Fabric becomes critical path for conflict detection (single point of failure) | **ACCEPTED:** Aligns with verifier-only Gateway posture, Fabric authoritative model, and fail-closed enforcement. Determinism achieved through cryptographic binding. Falsifiability preserved through explicit attestation field. This is the only approach that satisfies all architectural constraints. |
| **Semantic conflict detection (v1)** (Detect logical contradictions, overlapping constraints, incompatible policies) | Detects broader class of conflicts; higher correctness assurance; prevents logically incompatible invariants from coexisting | Requires reasoning engine (LLM or rule engine); non-deterministic (reasoning may vary); cannot be verified by signature alone (semantic interpretation varies); significant complexity (schema knowledge, constraint modeling); deferred work substantial | **DEFERRED to v2+:** V1 requires simplest deterministic semantics. Semantic analysis introduces interpretation, non-determinism, and complexity. Syntactic conflict detection (canonical ID + content digest) is sufficient for v1 correctness guarantees. Semantic detection requires separate ADR defining reasoning model, determinism guarantees, and falsifiability criteria. |
| **No conflict detection** (Omit conflict detection entirely; rely on Fabric canonical state consistency) | Simplest implementation; no attestation schema changes; no detection algorithm required; reduces Fabric complexity | Breaks determinism claims (different Gateways might or might not detect); permits incorrect conformance (contradictory invariants can authorize execution); violates existing PREREQ-4 requirement (§8.1.2 normatively requires conflict detection); allows ambiguous canonical state; undermines correctness guarantees; Gap exists precisely because conflict detection is required but undefined | **REJECTED:** Gap exists because PREREQ-4 normatively requires conflict detection. Omitting detection violates specification requirements and permits contradictory invariants to authorize execution, breaking canonical state unambiguity (§7.1.1). This alternative fails to satisfy the problem statement. |

## Component Interaction

### AI-DOC Fabric Behavior (Normative)

**Responsibilities:**

1. **Conflict Detection During Attestation Creation:**
   - When producing Fabric Attestation for (scope S, environment E)
   - Collect all invariants: `prime_invariants`, `system_invariants`, `domain_invariants`
   - Apply detection algorithm (R-CONF-1): scan for duplicate canonical identifiers with differing content digests
   - Set `conflict_status: "detected"` if any conflict found, `"none"` otherwise

2. **Attestation Signing:**
   - Include `conflict_status` field in attestation envelope (top-level field)
   - Sign attestation including `conflict_status` (cryptographic binding per R-CONF-7)
   - Ensure signature covers all attestation fields

3. **Attestation Publication:**
   - Provide signed attestation to Runtime upon request
   - Attestation includes all invariant arrays, `conflict_status`, and signature

**Prohibited:**
- Fabric MUST NOT issue attestations without `conflict_status` field
- Fabric MUST NOT issue attestations without performing conflict detection
- Fabric MUST NOT sign attestations where `conflict_status` is malformed

**No New Authority:** Fabric already has ORG authority to sign canonical artifacts and attestations (§6.1.1). Conflict detection does not introduce new authority; it exercises existing canonical state authority.

### STE-Runtime Behavior (Normative)

**Responsibilities:**

1. **Attestation Request:**
   - Request Fabric Attestation from AI-DOC Fabric Intelligence Service
   - Specify (scope, environment) for attestation

2. **Attestation Inclusion:**
   - Receive signed attestation from Fabric (includes `conflict_status`)
   - Include attestation **verbatim** in Eligibility Proposal
   - No modification, no recomputation, no override

3. **No Conflict Override:**
   - Runtime MUST NOT modify `conflict_status` field
   - Runtime MUST NOT remove or replace attestation
   - Runtime MUST NOT compute conflict status independently

**Prohibited:**
- Runtime MUST NOT implement conflict detection algorithm
- Runtime MUST NOT override or recompute `conflict_status`
- Runtime MUST NOT provide multiple attestations with conflicting `conflict_status` values

**No New Authority:** Runtime already has PROJECT authority to sign Context Bundles (§6.1.3). Including Fabric Attestation does not grant Runtime authority to attest; Runtime conveys Fabric's attestation, signed by Fabric.

### STE-Gateway Behavior (Normative)

**Responsibilities:**

1. **Attestation Signature Verification:**
   - Verify Fabric Attestation signature per Trust Registry
   - Signature verification MUST cover `conflict_status` field
   - If signature invalid → DENY (SIGNATURE_INVALID)

2. **Conflict Status Extraction:**
   - Extract `conflict_status` field from verified attestation
   - No parsing of invariant content, identifiers, or digests

3. **Conflict Status Enforcement:**
   ```
   if conflict_status not in ["none", "detected"]:
       return DENY(category=CONTEXT_INCOMPLETE)
   
   if conflict_status == "detected":
       return DENY(category=INVARIANT_CONFLICT)
   
   if conflict_status == "none":
       continue eligibility evaluation  # Proceed to next prerequisite
   ```

4. **Response Generation:**
   - If denied, return: decision=DENY, category=INVARIANT_CONFLICT or CONTEXT_INCOMPLETE, timestamp
   - No conflict detail, no invariant identifiers, no provenance

**Prohibited:**
- Gateway MUST NOT parse invariant content, identifiers, or digests
- Gateway MUST NOT implement conflict detection algorithm
- Gateway MUST NOT compare content hashes to cached or fetched artifacts
- Gateway MUST NOT include conflict detail in responses

**No New Authority:** Gateway already has Enforcement Authority (ADR-019). Conflict status verification is part of eligibility evaluation, not new enforcement scope.

### Trust Registry (No Changes)

Trust Registry is unchanged. `conflict_status` verification does not introduce new trust dimensions.

**Clarification:** Trust Registry validates that Fabric has ORG authority to sign attestations. The fact that attestations include `conflict_status` does not change trust validation logic. Signature verification inherently covers `conflict_status` as part of signed attestation envelope.

## Threat Model Implications

### Attacks This Prevents

**1. Ambiguity Exploitation**

**Attack:** Attacker exploits undefined conflict semantics to craft Context Bundle with contradictory invariants, bypassing enforcement by relying on implementation-specific interpretation.

**Prevention:** Conflict semantics are explicit and deterministic. Fabric attests to conflict status; Gateway enforces based on signed attestation. No ambiguity exists for attacker to exploit.

**2. Inconsistent Enforcement Across Gateways**

**Attack:** Attacker submits Context Bundle to multiple Gateway instances, expecting different decisions due to implementation variation. One Gateway detects conflict (DENY); another misses conflict (ALLOW).

**Prevention:** Gateway enforcement is deterministic. All compliant Gateways verify attestation signature and extract `conflict_status` identically. Same attestation = same decision, always.

**3. Conflict Status Tampering**

**Attack:** Attacker intercepts Fabric Attestation with `conflict_status: "detected"`, modifies to `conflict_status: "none"`, submits to Gateway to bypass conflict enforcement.

**Prevention:** `conflict_status` is cryptographically bound into signed attestation (R-CONF-7). Modifying `conflict_status` without re-signing invalidates signature. Gateway signature verification detects tampering.

**4. Gateway Probing for Conflict Detail**

**Attack:** Attacker submits multiple Context Bundles with crafted invariants, probing Gateway responses to extract conflict detection logic, invariant structure, or provenance.

**Prevention:** Minimal response surface. Gateway response contains only decision + category. No conflict detail, no invariant identifiers, no evaluation trace. Attacker gains no information beyond binary outcome (ALLOW | DENY).

### Attacks This Does NOT Prevent

**1. Compromised Fabric Signing Key**

**Scenario:** Attacker gains access to Fabric ORG signing key, issues attestation with incorrect `conflict_status` (claims `"none"` when conflicts exist).

**Not Prevented:** Attestation signature is valid; Gateway trusts signed attestation. Gateway cannot detect that Fabric's conflict detection was incorrect or malicious.

**Mitigation (Out of Scope):** Key management, hardware security modules (HSMs), attestation audit logs, revocation mechanisms. Conflict semantics assume Fabric signing key integrity; compromised keys are a separate threat.

**2. DoS via Conflict Injection**

**Scenario:** Attacker with Fabric access (or compromised ADF merge authority) introduces contradictory invariants into canonical state, causing all attestations to have `conflict_status: "detected"`, denying all execution.

**Not Prevented:** If conflicts exist in canonical state, Fabric correctly attests `conflict_status: "detected"`, and Gateway correctly denies execution. This is correct behavior, not a bypass.

**Mitigation (Out of Scope):** Operational monitoring, Fabric access controls, merge-time conflict detection (ADF preventative per ADR-023), audit trails. Conflict semantics enforce correctness; DoS via legitimate conflict detection is an operational concern.

**3. Semantic Contradictions Not Syntactically Detectable**

**Scenario:** Two invariants with different canonical identifiers assert logically incompatible constraints. V1 conflict detection does not detect semantic contradictions.

**Not Prevented:** V1 detects syntactic conflicts only (same ID, different digest). Logical contradictions (different IDs, incompatible semantics) are not detected.

**Mitigation (Deferred to v2+):** Semantic conflict detection requires reasoning engine, schema knowledge, and interpretation model. Separate ADR required.

**4. Cross-Attestation Conflicts**

**Scenario:** Invariant in attestation A conflicts with invariant in attestation B (different scopes, different timestamps). Gateway evaluates each attestation independently; cross-attestation conflicts are not detected.

**Not Prevented:** V1 conflict detection is per attestation. Cross-attestation conflicts require aggregation and precedence rules (deferred to v2+).

**Mitigation (Deferred to v2+):** Cross-attestation conflict detection requires separate ADR defining aggregation model, precedence, and temporal ordering.

### Minimal Response Surface Benefit

Gateway response contains only:
- `decision`: "ALLOW" | "DENY"
- `category`: "INVARIANT_CONFLICT" | "CONTEXT_INCOMPLETE" | ... (if DENY)
- `timestamp`: ISO 8601 timestamp

**Not Included:**
- Which invariants conflicted (canonical identifiers)
- Content hashes of conflicting invariants
- Provenance (extracted vs asserted, source files, timestamps)
- Evaluation trace or intermediate results
- Resolution recommendations

**Security Benefit:**
- **Reduces information leakage:** Attacker cannot extract invariant structure, canonical identifiers, or provenance
- **Prevents reconnaissance:** Attacker cannot probe Gateway to map canonical state or invariant relationships
- **Simplifies response parsing:** Smaller response surface reduces parsing vulnerabilities
- **Consistent with verifier-only posture:** Gateway provides verification outcome only, not evaluation detail

## Consequences

### Positive

**1. Deterministic Gateway Enforcement**

Gateway enforcement is deterministic across implementations and time. Given identical attestation with identical `conflict_status`, all compliant Gateways produce identical decisions.

**Benefit:** Interoperability, reproducibility, auditing confidence. Organizations can deploy multiple Gateway instances with confidence that decisions are consistent.

**Falsifiable:** Replay eligibility evaluation on different Gateway instances; outcomes must match.

**2. Falsifiable Conflict Semantics**

Conflict status is explicitly declared in signed attestation. Auditors, operators, and implementers can verify conflict determination by inspecting attestation structure.

**Benefit:** Auditability, transparency, debugging. Operators can diagnose conflicts by inspecting attestation, not by reverse-engineering Gateway logic.

**Falsifiable:** Extract `conflict_status` from attestation, verify signature coverage, inspect invariant arrays for duplicate canonical identifiers.

**3. Gateway Implementation Simplicity**

Gateway performs signature verification + field extraction only. No content parsing, no comparison logic, no algorithm variation risk.

**Benefit:** Reduced Gateway complexity, fewer implementation bugs, lower maintenance burden, easier certification.

**Impact:** Gateway implementation does not require invariant schema knowledge, content parsing libraries, or digest computation logic.

**4. Fail-Closed on Ambiguity**

Missing, malformed, or unverifiable `conflict_status` results in denial. No best-effort execution, no "maybe" states.

**Benefit:** Correctness prioritized over availability. Ambiguity cannot be exploited to bypass enforcement.

**Impact:** Operators must ensure Fabric produces well-formed attestations. Attestation schema validation becomes critical.

**5. Minimal Response Surface Maintained**

Gateway responses contain decision + category only. No conflict detail, no invariant provenance, no evaluation trace.

**Benefit:** Reduced information leakage, simpler response parsing, consistent with verifier-only posture.

**Impact:** Debugging requires inspecting attestations directly, not Gateway responses.

**6. Clear Component Separation**

Fabric detects conflicts (authoritative). Gateway enforces conflict status (verifier). Runtime conveys attestations (transport).

**Benefit:** Clear responsibility allocation, no ambiguity about who determines conflicts, easier to reason about system behavior.

**Impact:** Fabric becomes critical path for conflict detection; Fabric failures block attestation issuance.

### Negative

**1. Fabric Critical Path for Conflict Detection**

Fabric must perform conflict detection for every attestation. Fabric failures, performance bottlenecks, or bugs in detection algorithm block all attestation issuance.

**Impact:** Fabric availability becomes critical for execution eligibility. Fabric outage prevents all execution (fail-closed).

**Mitigation (Operational):** Fabric redundancy, caching, monitoring, alerting. Conflict detection algorithm must be highly reliable.

**2. Attestation Schema Expansion**

Fabric Attestations must include `conflict_status` field. Existing attestations without this field are invalid.

**Impact:** Migration required for existing deployments. Attestation schema versioning, backward compatibility concerns.

**Mitigation (Implementation):** Attestation schema version field, migration tooling, staged rollout.

**3. No Semantic Conflict Detection in v1**

V1 detects syntactic conflicts only (same ID, different digest). Logical contradictions (different IDs, incompatible semantics) are not detected.

**Impact:** Two invariants may be logically incompatible but not trigger conflict detection. Users must ensure semantic consistency through governance, reviews, and validation tooling.

**Mitigation (Future Work):** V2+ semantic conflict detection (separate ADR). V1 establishes deterministic foundation for syntactic conflicts.

**4. No Cross-Attestation Conflict Detection in v1**

Conflicts between invariants in different attestations (different scopes, different timestamps) are not detected.

**Impact:** Users cannot rely on system to detect conflicts across scope boundaries or over time. Governance and tooling must ensure cross-scope consistency.

**Mitigation (Future Work):** V2+ cross-attestation conflict detection (separate ADR). V1 establishes per-attestation conflict semantics.

**5. No Conflict Detail in Gateway Responses**

Gateway responses contain only decision + category. Operators must inspect attestations to diagnose which invariants conflicted.

**Impact:** Debugging harder; operators cannot diagnose conflicts from Gateway responses alone. Must fetch and inspect attestations.

**Mitigation (Operational):** Tooling to fetch and parse attestations, conflict visualization, audit log correlation.

**6. Operators Must Inspect Attestations Directly**

Conflict diagnosis requires fetching attestation from Fabric or Runtime, parsing structure, identifying duplicate canonical identifiers.

**Impact:** Operational burden increases. Operators need access to attestation storage, parsing tools, and Fabric APIs.

**Mitigation (Operational):** CLI tools, attestation inspection UIs, troubleshooting guides.

### Neutral

**1. Conflict Status is Binary**

Conflicts either exist or do not. No gradations (minor vs major conflict), no severity levels, no partial conflicts.

**Implication:** All conflicts are treated equally. Single conflict causes denial, same as multiple conflicts.

**Rationale:** Simplicity, determinism. Severity classification would require interpretation and policy.

**2. Conflict Detection is Per Attestation**

Each attestation is evaluated independently. Cross-attestation state is not aggregated.

**Implication:** Organizations cannot rely on system to detect conflicts across multiple attestations in a single Eligibility Proposal.

**Rationale:** V1 simplicity. Cross-attestation aggregation deferred to v2+.

**3. Environment Isolation Preserved**

Conflicts are not detected across environments. `prod` and `staging` may have divergent invariants without triggering conflict detection.

**Implication:** Organizations must ensure cross-environment consistency through governance, not conflict detection.

**Rationale:** Environments partition canonical state (ADR-025). Cross-environment consistency is a governance concern, not a conflict detection concern.

## Future Work (Explicitly Deferred to v2+)

The following features are **intentionally omitted from v1** and deferred to future ADRs:

### 1. Semantic Conflict Detection

**Deferred Capability:** Detect logical contradictions, overlapping constraints, incompatible policies beyond syntactic ID+digest comparison.

**Examples:**
- `max_retries: 5` in PRIME-1 vs `max_retries: 3` in SYS-2 (contradiction)
- `allowed_regions: [us-east-1]` vs `denied_regions: [us-east-1]` (overlap)
- `encryption: required` vs `encryption: optional` (incompatibility)

**Why Deferred:** Semantic analysis requires reasoning engine (LLM or rule engine), schema knowledge, constraint modeling, and interpretation logic. Non-deterministic reasoning introduces variability. Cannot be verified by signature alone.

**Future ADR Required:** Define reasoning model, determinism guarantees (how to ensure identical reasoning across implementations), falsifiability criteria (how to verify semantic conflict detection), and schema knowledge requirements.

### 2. Cross-Attestation Conflict Detection

**Deferred Capability:** Detect conflicts between invariants in different attestations (different scopes, different timestamps, different environments).

**Examples:**
- Attestation A (scope `project:backend`, timestamp T1) has PRIME-1 with content hash H1
- Attestation B (scope `project:frontend`, timestamp T2) has PRIME-1 with content hash H2
- Conflict: same canonical ID across attestations with different hashes

**Why Deferred:** Cross-attestation conflict detection requires:
- Aggregation model (how to collect invariants from multiple attestations)
- Precedence rules (which attestation is authoritative when conflicts exist?)
- Temporal ordering (does newer attestation override older?)
- Scope relationships (does parent scope attestation override child scope?)

**Future ADR Required:** Define aggregation algorithm, precedence model, temporal ordering semantics, and scope hierarchy resolution.

### 3. Hierarchical Scope Conflict Detection

**Deferred Capability:** Detect conflicts across scope hierarchy (parent scope invariant conflicts with child scope invariant).

**Examples:**
- Parent scope `project:myapp` has PRIME-1 with content hash H1
- Child scope `project:myapp:payments` has PRIME-1 with content hash H2
- Conflict: same canonical ID at different scope levels

**Why Deferred:** Requires scope resolution algorithm (how to traverse hierarchy), inheritance semantics (does child inherit parent invariants?), and override rules (can child override parent?).

**Future ADR Required:** Define scope hierarchy model, traversal algorithm, inheritance semantics, and override precedence.

### 4. Cross-Environment Conflict Detection

**Deferred Capability:** Detect conflicts across environments (e.g., `prod` invariant conflicts with `staging` invariant).

**Examples:**
- Environment `prod` has PRIME-1 with content hash H1
- Environment `staging` has PRIME-1 with content hash H2
- Potential concern: environments diverged

**Why Deferred:** Environments partition canonical state per ADR-025. Cross-environment consistency is governance concern, not conflict detection concern. Requires environment relationship model (are environments independent? hierarchical? synchronized?).

**Future ADR Required:** Define environment relationship model, synchronization semantics, and divergence tolerance. Deferred pending ADR-025 hierarchy features (if any).

### 5. Conflict Detail in Gateway Responses

**Deferred Capability:** Include conflicting invariant identifiers, provenance, or resolution guidance in Gateway responses.

**Examples:**
- Response includes: `"conflicts": [{"invariant_id": "PRIME-1", "hash_1": "sha256:abc...", "hash_2": "sha256:def..."}]`
- Response includes resolution recommendation: `"Resolve by updating canonical state in AI-DOC Fabric"`

**Why Deferred:** Expanding response surface increases information leakage, enables reconnaissance attacks, and complicates response parsing. Security analysis required to determine acceptable detail level.

**Future ADR Required:** Define response schema expansion, security analysis (what detail is safe to expose), and client parsing requirements. Requires justification for departing from minimal response surface.

### 6. Conflict Severity or Classification

**Deferred Capability:** Classify conflicts by severity (minor, major, critical) or type (syntactic, semantic, temporal).

**Examples:**
- Minor conflict: invariant metadata differs (description, evidence URL)
- Major conflict: invariant constraint differs (max_retries value)
- Critical conflict: invariant purpose differs (enforcement vs advisory)

**Why Deferred:** Severity classification requires interpretation, policy, and domain knowledge. Different organizations may have different severity criteria. V1 treats all conflicts equally (binary: exist or not).

**Future ADR Required:** Define classification taxonomy, severity criteria, and enforcement implications (does minor conflict still deny execution?).

### 7. Gateway Content Evaluation Beyond Signature Verification

**Deferred Capability:** Any mechanism where Gateway parses, compares, or evaluates invariant content beyond verifying attestation signature and extracting `conflict_status` field.

**Examples:**
- Gateway fetches canonical invariant content from ADF to compare with attestation hashes
- Gateway parses invariant YAML to extract keys and values for validation
- Gateway implements conflict detection algorithm independent of Fabric attestation

**Why Permanently Rejected (Not Merely Deferred):** Violates verifier-only posture (ADR-019). Gateway is a pure verifier; content evaluation introduces state discovery, parsing complexity, and implementation variation. If Gateway-side content evaluation becomes necessary, verifier-only posture must be revised via separate ADR challenging ADR-019.

**Condition for Reconsideration:** Requires architectural redesign challenging verifier-only posture. Not incremental enhancement; fundamental posture change.

All deferred features require **separate ADRs** and **must preserve determinism, falsifiability, and explicit semantics**. Convenience features that introduce ambiguity, hidden logic, or interpretation are **permanently rejected**, not merely deferred.

## Final Validation Clause

A compliant STE-System implementation and a reasonable reader of this ADR **must not** infer or conclude that:

### Prohibited Inferences

- [ ] **Gateway detects conflicts** by parsing invariant content, comparing invariant identifiers, or computing content digests
- [ ] **Gateway compares invariant content** by fetching canonical artifacts from ADF, caching invariant content, or implementing digest comparison
- [ ] **Gateway implements conflict detection algorithm** beyond extracting `conflict_status` field from signed attestation
- [ ] **Conflict semantics are implementation-specific at Gateway** rather than Fabric-attested and cryptographically bound
- [ ] **Conflict details are returned in Gateway responses** including invariant identifiers, content hashes, provenance, or resolution recommendations
- [ ] **Cross-environment conflicts are detected in v1** rather than environments being isolated canonical state partitions per ADR-025
- [ ] **Cross-attestation conflicts are detected in v1** rather than each attestation being evaluated independently
- [ ] **Semantic contradictions are detected in v1** rather than only syntactic conflicts (same ID, different digest)
- [ ] **INDETERMINATE decision state exists for conflict status** rather than binary ALLOW | DENY based on `conflict_status` field
- [ ] **Conflict status can be inferred or defaulted** if missing, rather than missing status causing DENY with CONTEXT_INCOMPLETE
- [ ] **Gateway response includes evaluation detail** beyond decision (ALLOW | DENY), category (if DENY), and timestamp

### Required Falsifiable Behaviors

A compliant implementation **must** exhibit the following testable, observable behaviors:

1. **Reject attestation without conflict_status:**  
   Submit Fabric Attestation missing `conflict_status` field → Gateway returns DENY with category CONTEXT_INCOMPLETE.

2. **Deny when conflict_status="detected":**  
   Submit Fabric Attestation with `conflict_status: "detected"` → Gateway returns DENY with category INVARIANT_CONFLICT.

3. **Allow when conflict_status="none":**  
   Submit Fabric Attestation with `conflict_status: "none"` → Gateway continues eligibility evaluation (no automatic denial based on conflict status).

4. **Signature verification failure on tampering:**  
   Submit Fabric Attestation, modify `conflict_status` field without re-signing → Gateway signature verification fails → Gateway returns DENY with category SIGNATURE_INVALID.

5. **Deterministic replay:**  
   Submit same Fabric Attestation to multiple Gateway instances → All Gateways produce identical decision. Submit same attestation at different times (within TTL) → Gateway produces identical decision.

6. **No content parsing:**  
   Gateway implementation does not parse invariant content, extract invariant identifiers (beyond attestation structure), or compute content digests. Gateway extracts `conflict_status` field from attestation envelope only.

7. **Minimal response:**  
   Gateway response contains: `decision` (ALLOW | DENY), `category` (if DENY), `timestamp`. Response does NOT contain: conflicting invariant identifiers, content hashes, provenance, evaluation trace, or resolution recommendations.

These behaviors are **testable, observable, and falsifiable** by inspection, replay, or conformance testing.

## Related Decisions

- **ADR-025: Environment Semantics** - Establishes environment as canonical dimension with partitioning rules. This ADR establishes environment isolation for conflict detection (cross-environment conflicts not detected).

- **ADR-007: Slice Identity Strategy** - Defines canonical identity for slices. This ADR applies identity to invariants: canonical identifier uniqueness enables conflict detection.

- **ADR-008: Correctness and Consistency Contract** - Defines canonical state guarantees. This ADR enforces those guarantees by preventing contradictory invariants (same ID, different content) from coexisting in attestations.

- **ADR-009: Assertion Precedence Model** - Establishes coexistence with conflict surfacing for extracted vs asserted facts. This ADR extends conflict surfacing to invariants: conflicts are surfaced, never resolved.

- **ADR-019: Gateway Authority and Signing Model** - Establishes Gateway enforces but does not attest. This ADR implements that posture: Gateway verifies Fabric attestation, does not compute conflict status.

- **ADR-022: Fail-Closed Enforcement Scope** - Defines fail-closed triggers. This ADR establishes `conflict_status: "detected"` and missing/malformed `conflict_status` as fail-closed triggers (DENY).

- **ADR-023: Validation Timing and Responsibility** - Establishes Gateway normative conflict detection timing, ADF preventative. This ADR defines the detection algorithm and enforcement mechanism.

- **ADR-024: Cross-Component Contracts** - Defines component interaction contracts. This ADR specifies Fabric, Runtime, and Gateway behavior for conflict status attestation and enforcement.

- **ADR-025: Environment Semantics** - Defines environment as explicit, mandatory, exact-match string identifier. This ADR applies environment isolation to conflict detection: conflicts are per (scope, environment); cross-environment conflicts not detected.

## Traceability

**Closes Gap:** GAP-3 (Invariant Conflict Detection Algorithm / Blocker 2.3) from STE Specification Gap Analysis

**Requirements:**
- §8.1.2 PREREQ-4 (No Invariant Conflicts) - Now defined: conflicts are duplicate canonical identifier with different content digest
- §8.1.4 STEP 4 (Check for conflicts) - Now defined: Gateway extracts `conflict_status` from attestation and enforces
- §8.4.3 (Invariant Conflict Detection Timing) - Implemented: Fabric normative detection, Gateway signature verification enforcement

**Views:**
- `specifications/ste-system.iso42010.md` §8.1.2 (Prerequisites for Eligibility Evaluation)
- `specifications/ste-system.iso42010.md` §8.1.4 (Eligibility Evaluation Algorithm)
- `specifications/ste-system.iso42010.md` §8.4.3 (Invariant Conflict Detection Timing)

**Stakeholders:**
- Fabric Implementers (must implement conflict detection algorithm and attest to status)
- Gateway Implementers (must verify attestation and enforce based on `conflict_status`)
- Runtime Implementers (must include attestations verbatim, no modification)
- Security/Compliance Teams (conflict detection prevents contradictory invariants from authorizing execution)

---

**Last Updated:** 2025-12-29  
**Status:** Accepted  
**Next Review:** After v1 Implementation Feedback


