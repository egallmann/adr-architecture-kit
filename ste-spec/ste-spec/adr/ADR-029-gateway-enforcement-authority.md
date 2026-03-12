# ADR-029: Gateway Enforcement Authority

**Status:** Accepted  
**Date:** 2025-12-30  
**Closes Blockers:** 1.1 (Gateway Authority Class Assignment)  
**Related:** ADR-019 (Gateway Authority and Signing Model), ADR-028 (Fabric Gateway Authority Boundaries)

---

## Context

The STE-System specification initially assigned Organizational (ORG) authority class to STE-Gateway (§5.3.5), creating a contradiction with the Gateway's actual capabilities:

1. §6.1.1 defines ORG authority as requiring capability to "Sign canonical artifacts"
2. Gateway explicitly cannot sign canonical artifacts (P-GW-4 prohibition, ADR-019)
3. Gateway's role is enforcement and verification, not attestation

This contradiction was partially addressed in ADR-019, which established that Gateway operates with "ORG-scoped enforcement authority, not ORG attestation authority." However, the specification still assigns "ORG authority" to Gateway in §5.3.5, and §6.1 does not define a distinct authority class for enforcement-only capabilities.

**Gap Analysis Finding (Blocker 1.1):**
> Gateway is assigned ORG authority class but does not sign canonical artifacts (§5.3.3 P-GW-4 prohibits Gateway from publishing to ADF). ORG authority definition requires artifact signing capability.

**Specification Pressure:** If Gateway does not sign artifacts, it cannot have ORG authority class per §6.1. Spec must either redefine Gateway authority class (create new class), clarify Gateway acts "as if" ORG without being ORG, or define sub-classes of ORG authority.

This ADR formalizes Gateway's distinct authority class to eliminate the contradiction and enable deterministic Trust Registry schema design.

---

## Decision

**Gateway operates with Enforcement Authority, a distinct authority class separate from ORG authority.**

### Authority Class Definition

**Enforcement Authority** is a specialized authority class with the following characteristics:

**Capabilities:**
- Verify artifacts signed by ORG authority
- Query Trust Registry to verify identity claims
- Enforce execution eligibility based on ORG-signed canonical invariants
- Produce ephemeral, unsigned eligibility decisions
- Validate CEM envelopes and Context Bundles
- Extract canonical invariants from Fabric Attestations

**Prohibitions:**
- MUST NOT sign canonical artifacts (ADF responsibility)
- MUST NOT produce signed attestations of eligibility decisions
- MUST NOT populate or modify Trust Registry
- MUST NOT claim attestation authority over canonical state
- MUST NOT query ADF at runtime (per ADR-028)

**Scope:**
- Enforcement Authority is Gateway-specific
- No other component may claim Enforcement Authority
- Enforcement Authority does not delegate or subdivide

---

## Relationship to Existing Authority Classes

### ORG Authority (§6.1.1)
**Purpose:** Attest canonical truth that persists long-term
- Signs immutable canonical artifacts (slices, relationship artifacts, invariants)
- Populates Trust Registry with authoritative identity mappings
- Creates non-repudiable audit trail of canonical state evolution
- **Example:** AI-DOC Fabric signing canonical artifacts

### PROJECT Authority (§6.1.3)
**Purpose:** Sign workspace-scoped artifacts and proposals
- Signs Context Bundles with provisional state
- Represents project-level identity
- Cannot sign canonical artifacts
- **Example:** STE-Runtime signing Context Bundles

### Human Authority (§6.1.4)
**Purpose:** User-level signing for direct actions
- Signs user-initiated artifacts
- User-scoped signing keys
- Cannot sign canonical artifacts
- **Example:** Developer signing relationship artifacts

### Enforcement Authority (NEW - §6.1.5)
**Purpose:** Verify and enforce execution eligibility at boundary
- Verifies artifacts signed by ORG authority
- Enforces eligibility based on ORG-signed inputs
- Produces ephemeral enforcement outcomes (not signed)
- Cannot create new canonical truth
- **Example:** STE-Gateway enforcing execution eligibility

**Key Distinction:** ORG creates canonical truth; Enforcement Authority verifies and enforces canonical truth without creating new truth.

---

## Rationale

### Why Enforcement Authority Is Not ORG Authority

**ORG Authority Purpose:** Attest canonical truth
- Signs artifacts that become part of permanent canonical state
- Attestations are durable, immutable, and part of audit trail
- Authority derives from organizational governance and key management

**Gateway Enforcement Purpose:** Verify and enforce at execution boundary
- Evaluates ephemeral requests (Context Bundles with 5-15 minute TTL)
- Makes point-in-time decisions based on ORG-signed inputs
- Enforces constraints without creating new canonical truth
- Verification outcomes are logged but not attested as non-repudiable canonical truth

**False Equivalence:** Assigning ORG authority to Gateway would imply Gateway produces canonical artifacts or attestations, which violates ADR-019's verifier-only posture.

### Why Gateway Does Not Sign Eligibility Decisions

**Ephemeral Nature:** Context Bundles expire in 5-15 minutes (§9.1.5). Signing ephemeral decisions:
- Creates unnecessary cryptographic overhead for short-lived artifacts
- Implies eligibility decisions have canonical status (they do not)
- Expands signing surface area without security benefit

**Audit Without Attestation:** Gateway logs enforcement decisions with:
- Context Bundle ID (which contains signed bundle from Runtime)
- Resolved canonical invariant versions (which are ORG-signed via Fabric Attestations)
- Trust registry entry used (which is ORG-signed)
- Decision timestamp and outcome

Reconstructing "why was this request eligible" requires verifying ORG-signed inputs, not Gateway signature on outcome.

### Why Gateway-Specific Authority Class

**Specificity:** Enforcement Authority is narrowly tailored to Gateway's verification and enforcement role. Creating a general-purpose "Verification Authority" class would invite misuse by other components.

**Clarity:** Explicit class eliminates ambiguity about what Gateway can and cannot do. Trust Registry schema can enforce that only Gateway identities have Enforcement Authority.

**Evolution:** If future components require verification-only authority (e.g., audit validators, compliance checkers), new authority classes can be defined with appropriate scopes. Enforcement Authority remains Gateway-specific.

---

## Trust Registry Schema Extension

### Required Schema Changes

**Trust Registry Entry Structure (Extended):**

```yaml
Identity: gateway-prod-instance-01
PublicKey: <ed25519 public key>
ValidFrom: 2025-12-30T00:00:00Z
ValidUntil: 2026-12-30T00:00:00Z
Scope: org
Environment: prod
AuthorityClass: enforcement  # NEW FIELD
Capabilities:
  - verify_org_signed_artifacts
  - enforce_eligibility
  - query_trust_registry
Prohibitions:
  - sign_canonical_artifacts
  - populate_trust_registry
  - attest_canonical_state
```

**Authority Class Enum:**
- `org` - ORG authority (signs canonical artifacts)
- `project` - PROJECT authority (signs Context Bundles)
- `human` - Human authority (signs user artifacts)
- `enforcement` - Enforcement Authority (Gateway-specific)

### Schema Validation Rules

**R-AUTH-1: Authority Class Mandatory**
Every Trust Registry entry MUST specify exactly one `AuthorityClass` value.

**R-AUTH-2: Enforcement Authority Restrictions**
Trust Registry entries with `AuthorityClass: enforcement` MUST:
- Have scope covering enforcement domain
- Include `verify_org_signed_artifacts` capability
- Include `sign_canonical_artifacts` prohibition
- Be assigned only to Gateway identities

**R-AUTH-3: ORG Authority Signing Capability**
Trust Registry entries with `AuthorityClass: org` MUST include capability to sign canonical artifacts.

**R-AUTH-4: Cross-Authority Prohibition**
No identity may have multiple authority classes. Authority class is exclusive per identity.

---

## Component Interaction Changes

### AI-DOC Fabric
**No Changes:** ADF retains ORG authority. ADF signs canonical artifacts and Fabric Attestations with ORG authority keys.

### STE-Runtime
**No Changes:** Runtime retains PROJECT authority. Runtime signs Context Bundles with PROJECT authority keys.

### STE-Gateway
**Authority Class Update:** Gateway's Trust Registry entry MUST specify `AuthorityClass: enforcement`.

**Capabilities:**
- Verify ORG-signed Fabric Attestations (signature verification via Trust Registry)
- Extract canonical invariants from Fabric Attestations (per ADR-028)
- Enforce eligibility prerequisites (PREREQ-1 through PREREQ-6)
- Produce unsigned eligibility decisions (ALLOW | DENY with reason code)

**Prohibitions:**
- Gateway MUST NOT sign eligibility decisions or enforcement outcomes
- Gateway MUST NOT create or modify Trust Registry entries
- Gateway MUST NOT sign canonical artifacts or relationship artifacts

---

## Specification Amendments Required

### §5.3.5 Gateway Authority Assignment

**Current Text:**
> **Authority Class:** Organizational (ORG) - Gateway acts with ORG authority for eligibility decisions

**Amended Text:**
> **Authority Class:** Enforcement Authority - Gateway verifies ORG-signed artifacts and enforces execution eligibility. Gateway does not have ORG authority and cannot sign canonical artifacts. See §6.1.5 for Enforcement Authority definition.

### §6.1 Authority Classes (Add §6.1.5)

**New Section After §6.1.4 (Human Authority):**

> **§6.1.5 Enforcement Authority (Gateway-Specific)**
>
> **Purpose:** Enforcement Authority is a specialized authority class for STE-Gateway that enables verification and enforcement of execution eligibility without creating new canonical truth.
>
> **Capabilities:**
> - Verify artifacts signed by ORG authority (signature verification via Trust Registry)
> - Enforce execution eligibility based on ORG-signed canonical invariants
> - Query Trust Registry to verify identity claims
> - Produce ephemeral, unsigned eligibility decisions (ALLOW | DENY)
> - Extract canonical invariants from Fabric Attestations (per ADR-028)
>
> **Prohibitions:**
> - MUST NOT sign canonical artifacts (ORG authority responsibility)
> - MUST NOT produce signed attestations of eligibility decisions
> - MUST NOT populate or modify Trust Registry
> - MUST NOT claim attestation authority over canonical state
> - MUST NOT query AI-DOC Fabric at runtime (per ADR-028)
>
> **Scope:** Enforcement Authority is exclusive to STE-Gateway. No other component may claim Enforcement Authority.
>
> **Key Distinction:** ORG authority creates canonical truth; Enforcement Authority verifies and enforces canonical truth without creating new truth. Gateway is a pure verifier (ADR-019, ADR-028), not an attestor.

### §6.2.1 Trust Registry Structure

**Current Schema (Partial):**
```yaml
Identity: <unique identity string>
PublicKey: <cryptographic public key>
Scope: <scope definition>
```

**Amended Schema (Add AuthorityClass):**
```yaml
Identity: <unique identity string>
PublicKey: <cryptographic public key>
Scope: <scope definition>
AuthorityClass: org | project | human | enforcement
```

**Add Validation Rule:**
> **V-TR-1: Authority Class Mandatory** Every Trust Registry entry MUST specify exactly one `AuthorityClass` value from the enumeration: `org`, `project`, `human`, `enforcement`.

---

## Consequences

### Positive

**1. Eliminates Authority Class Contradiction**
Gateway no longer assigned ORG authority while lacking ORG capabilities. Authority class accurately reflects Gateway's verification and enforcement role.

**Falsifiable:** Trust Registry schema enforces that Gateway identities have `AuthorityClass: enforcement`, not `org`.

**2. Clear Separation of Concerns**
ORG authority creates canonical truth; Enforcement Authority verifies canonical truth. No component has both capabilities.

**Falsifiable:** Inspect Trust Registry entries; no identity has both `sign_canonical_artifacts` capability and `AuthorityClass: enforcement`.

**3. Trust Registry Schema Deterministic**
Authority class is explicit field in Trust Registry, enabling deterministic verification of capabilities.

**Falsifiable:** Trust Registry schema validation rejects entries without `AuthorityClass` or with invalid values.

**4. Gateway Implementation Simplified**
Gateway implementers know definitively that Gateway does not require signing keys, key rotation, or attestation logic.

**Benefit:** Reduced Gateway complexity, lower certification burden, faster implementation.

**5. Falsifiable Authority Boundaries**
Authority model is explicit and testable. Auditors can verify that Gateway verifies but does not attest.

**Verification:** Inspect Gateway code; no signing key management, no attestation creation logic.

### Negative

**1. Trust Registry Schema Breaking Change**
Existing Trust Registry entries without `AuthorityClass` field are invalid. Migration required.

**Impact:** All Trust Registry entries must be updated to include `AuthorityClass` field.

**Mitigation:** Schema migration tooling, backward compatibility period, staged rollout.

**2. Authority Model Complexity Increased**
Four authority classes instead of three. Additional class requires documentation and governance.

**Impact:** Organizations must understand Enforcement Authority scope and assignment.

**Mitigation:** Clear documentation in §6.1.5, examples, and implementation guides.

**3. No Gateway Signing Keys Required**
Gateway identities in Trust Registry have public keys for identity verification but no signing keys for attestations.

**Impact:** Trust Registry must support identities with verification-only keys (public keys for TLS/mTLS) without signing key pairs.

**Mitigation:** Trust Registry schema clarifies that Enforcement Authority identities use keys for identity verification, not artifact signing.

### Neutral

**1. ADR-019 Ratified by This ADR**
ADR-019 stated Gateway has "enforcement authority" (lowercase, descriptive). This ADR formalizes Enforcement Authority (capitalized, authority class).

**Relationship:** ADR-019 established principle; ADR-029 codifies as authority class.

**2. No Change to Gateway Responsibilities**
Gateway's enforcement responsibilities (§5.3.2, §5.3.3) remain identical. Only authority class assignment changes.

**Implication:** Existing Gateway specifications remain valid; only Trust Registry schema and authority assignment change.

---

## Alternatives Considered

| Alternative | Pros | Cons | Rejection Rationale |
|-------------|------|------|---------------------|
| **Gateway as ORG Authority (Status Quo)** | No schema changes required; simplest | Violates P-GW-4 prohibition; contradicts ADR-019; conflates attestation and enforcement | Rejected. Creates false equivalence between Gateway enforcement and ADF attestation. Contradicts existing architecture. |
| **Gateway as Sub-Class of ORG** (e.g., "ORG-Verification") | Maintains ORG lineage; shows relationship to ORG authority | Ambiguous whether sub-class inherits signing capability; complicates authority model; precedent for unlimited sub-classes | Rejected. Sub-classes introduce hierarchy and inheritance semantics. Cleaner to define distinct class. |
| **Gateway "Acts As If" ORG Without Being ORG** | Avoids schema changes; preserves existing Trust Registry entries | Non-falsifiable; introduces interpretation ("acts as if" is ambiguous); does not resolve contradiction | Rejected. "Acts as if" is not verifiable or deterministic. Authority must be explicit and falsifiable. |
| **Enforcement Authority (This ADR)** | Explicit, falsifiable; eliminates contradiction; clear separation of concerns | Requires Trust Registry schema migration; adds fourth authority class | **Accepted.** Only approach that resolves contradiction with explicit, falsifiable semantics. |

---

## Related ADRs

- **ADR-019: Gateway Authority and Signing Model** - Established Gateway as enforcer, not attestor. This ADR formalizes enforcement as distinct authority class.
- **ADR-028: Fabric Gateway Authority Boundaries** - Established Gateway as pure verifier over Fabric Attestations. This ADR provides authority class that enables verification without attestation.
- **ADR-020: ORG-Level Signing Scope** - Defined ORG authority signing scope. This ADR clarifies Gateway does not have ORG authority.
- **ADR-021: Gateway Trust Verification Model** - Defined Gateway's trust verification responsibilities. This ADR provides authority class that enables verification.

---

## Traceability

**Closes Gap:** Blocker 1.1 (Gateway Authority Class Assignment) from STE Specification Gap Assessment

**Requirements:**
- §5.3.5 Gateway Authority Assignment - Updated to reflect Enforcement Authority
- §6.1 Authority Classes - Extended with §6.1.5 Enforcement Authority
- §6.2.1 Trust Registry Structure - Extended with `AuthorityClass` field

**Stakeholders:**
- Gateway Implementers (must understand Enforcement Authority capabilities and prohibitions)
- Trust Registry Implementers (must extend schema with `AuthorityClass` field)
- Security/Compliance Teams (authority boundaries are security boundaries)
- ADF Implementers (unaffected; retain ORG authority)

---

**Last Updated:** 2025-12-30  
**Status:** Accepted  
**Next Review:** After v1 Implementation Feedback

