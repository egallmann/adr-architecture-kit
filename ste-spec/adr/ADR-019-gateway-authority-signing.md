# ADR-019: Gateway Authority and Signing Model

**Status:** Accepted  
**Date:** 2025-12-23  
**Closes Blockers:** 1.1 (Gateway Authority Class Assignment), 1.2 (Context Bundle Signing Authority)

---

## Context

The STE-System specification (ste-system.iso42010.md) initially assigned Organizational (ORG) authority class to STE-Gateway, creating contradictions:

1. Section 6.1.1 defines ORG authority as requiring capability to "Sign canonical artifacts"
2. Gateway explicitly cannot sign canonical artifacts (P-GW-4 prohibition)
3. Section 9.2.3 stated "Gateway signs the payload," implying Gateway produces signed attestations
4. Gateway's role is enforcement and verification, not attestation

This created ambiguity about:
- Whether Gateway holds signing keys
- Whether eligibility decisions are canonical artifacts requiring signatures
- Whether Gateway operates with ORG authority or different authority

## Decision

**Gateway operates with ORG-scoped enforcement authority, not ORG attestation authority.**

### Authority Model

**Gateway Enforcement Authority:**
- Verifies artifacts signed by ORG authority
- Enforces execution eligibility based on ORG-signed invariants
- Queries trust registry to verify identity claims
- Produces ephemeral, unsigned eligibility decisions

**Gateway Does NOT:**
- Sign canonical artifacts (ORG responsibility via ADF)
- Produce signed attestations of eligibility decisions
- Populate or modify trust registry
- Claim attestation authority over canonical state

### Execution Eligibility Semantics

**Eligibility decisions are ephemeral enforcement outcomes, not canonical truth:**
- Short-lived (Context Bundles have 5-15 minute TTL)
- Point-in-time verification results (prerequisites satisfied at evaluation time)
- Not persisted as canonical artifacts
- Not cryptographically signed by Gateway
- Logged for audit but not attested as non-repudiable truth

## Rationale

### Why Enforcement Authority Is Not ORG Authority

**ORG Authority Purpose:** Attest canonical truth that persists long-term
- Signs immutable artifacts (slices, relationship artifacts, invariants)
- Populates trust registry with authoritative identity mappings
- Creates non-repudiable audit trail of canonical state evolution

**Gateway Enforcement Purpose:** Verify and enforce at execution boundary
- Evaluates ephemeral requests (Context Bundles with TTL)
- Makes point-in-time decisions based on ORG-signed inputs
- Enforces constraints without creating new canonical truth
- Verification outcome does not require long-term non-repudiation

**Key Distinction:** Signing eligibility decisions would create false equivalence with canonical artifacts, suggesting eligibility is persistent truth rather than ephemeral enforcement.

### Why Gateway Does Not Sign Eligibility Proofs

**Ephemeral Nature:** Context Bundles expire in 5-15 minutes (§9.1.5). Signing ephemeral decisions:
- Creates unnecessary cryptographic overhead for short-lived artifacts
- Implies eligibility decisions have canonical status (they do not)
- Expands signing surface area without security benefit

**Audit Without Attestation:** Gateway logs enforcement decisions with:
- Context Bundle ID (which contains signed bundle from Runtime)
- Resolved canonical invariant versions (which are ORG-signed)
- Trust registry entry used (which is ORG-signed)
- Decision timestamp and outcome

Reconstructing "why was this request eligible" requires verifying ORG-signed inputs, not Gateway signature on outcome.

### Determinism Preserved

Gateway enforcement remains deterministic:
- Signature verification: deterministic (cryptographic validation)
- Invariant resolution: deterministic (query ADF for ORG-signed artifacts)
- Eligibility evaluation: deterministic (algorithm in §8.1.4)
- Decision: deterministic (eligible/rejected based on prerequisites)

Not signing outcomes does not weaken determinism. Gateway produces same decision for same inputs regardless of signing.

## Explicit Non-Goals

This decision explicitly does NOT:

1. **Define Gateway key management** - Gateway has no signing keys; non-goal
2. **Specify audit log signing** - Audit logs may be signed by separate audit service; Gateway does not sign logs
3. **Touch trust registry semantics** - Trust registry population remains ORG responsibility
4. **Define model invocation protocol** - Payload authentication between Gateway and model provider is implementation-specific
5. **Introduce general-purpose enforcement authority class** - Enforcement Authority is Gateway-specific; other components may not claim this authority

## Consequences

### Enables

**Clear Authority Separation:**
- ORG authority: Signs canonical truth (artifacts, invariants, trust registry)
- Gateway authority: Enforces eligibility using ORG-signed truth (verifies, does not attest)

**Minimal Signing Surface:**
- Only entities that create canonical artifacts require signing keys
- Gateway operates without signing keys, reducing key management complexity

**Ephemeral Enforcement:**
- Eligibility decisions are point-in-time verifications, not persistent state
- No false equivalence between eligibility outcomes and canonical artifacts

### Forbids

**Gateway Attestation:**
- Gateway cannot be used to attest canonical state
- Gateway cannot produce signed audit trails claiming "this request was eligible"
- Gateway cannot sign relationship artifacts, slices, or invariants

**Eligibility as Canonical Truth:**
- Eligibility decisions cannot be persisted as canonical artifacts
- Eligibility proofs cannot be treated as non-repudiable attestations
- Model invocation payload is not a signed artifact; it is ephemeral request metadata

### Trade-offs

**Audit Complexity:** Without Gateway signatures on eligibility decisions, audit reconstruction requires:
- Verifying Context Bundle signature (signed by Human/PROJECT authority)
- Verifying canonical invariant signatures (signed by ORG authority)
- Trusting Gateway logs recorded decision correctly

**Mitigation:** Gateway logs are append-only and MAY be signed by separate audit system. Gateway enforcement logic is deterministic and auditable (given same inputs, reproduce same decision).

**Model Provider Trust:** Model provider receives unsigned eligibility proof from Gateway. Provider must:
- Trust Gateway identity (mutual TLS or equivalent)
- Trust Gateway enforced eligibility before forwarding payload
- Not treat eligibility proof as cryptographic attestation

**Mitigation:** Gateway-to-model-provider channel is secured via transport-level authentication (mutual TLS). Eligibility proof is protected by channel security, not artifact-level signing.

## Blocker Resolution Mapping

### Blocker 1.1: Gateway Authority Class Assignment

**Problem:** Gateway assigned ORG authority class but lacks ORG capabilities (cannot sign canonical artifacts).

**Resolution:**
- System spec §5.3.5 amended to state "Enforcement Authority (ORG-scoped)" instead of "ORG authority"
- System spec §6.1.5 added, defining Enforcement Authority as Gateway-specific class
- Enforcement Authority capabilities explicitly exclude canonical artifact signing

**Result:** No reasonable reader will expect Gateway to sign canonical artifacts after amendments.

### Blocker 1.2: Context Bundle Signing Authority

**Problem:** Ambiguity about whether Gateway signs eligibility proofs with ORG authority or different authority.

**Resolution:**
- System spec §9.2.3 amended to clarify "eligibility decision metadata (unsigned)"
- Added explicit non-goal: Gateway does not sign eligibility proofs
- Clarified eligibility proofs are ephemeral assertions, not cryptographic attestations

**Result:** No ambiguity remains about Gateway signing eligibility outcomes.

## Related ADRs

**ADR-008 (Correctness and Consistency Contract):** Established provenance requirements for canonical artifacts. This ADR clarifies Gateway does not produce canonical artifacts, thus does not require signing keys.

**Future ADR (Trust Registry Semantics):** Will define trust registry population mechanism (ORG responsibility). This ADR establishes Gateway queries but does not populate trust registry.

## Implementation Notes

### System Spec Amendments Required

1. §5.3.5 "Authority and Trust" - Replace "ORG authority" with "Enforcement Authority (ORG-scoped)"
2. §6.1.5 - Add "Enforcement Authority (Gateway-Specific)" section after Human Authority
3. §9.2.3 - Replace "Gateway signs the payload" with "Gateway includes eligibility decision metadata (unsigned)"
4. §9.2.3 - Add "Eligibility Proof Semantics" clarification after payload structure
5. §8.2.6 AUD-3 - Replace "Gateway can prove identity claimed authority" with "Gateway verifies input authority"

### Verification Steps

After amendments, verify:
- No section assigns ORG authority class to Gateway
- No section claims Gateway signs eligibility decisions or proofs
- ORG authority remains exclusive to entities signing canonical artifacts
- Gateway determinism claims remain intact
- Ephemeral nature of eligibility decisions is explicit

## Status

**Accepted:** 2025-12-23

**Supersedes:** No prior ADRs

**Blocks Closed:**
- Blocker 1.1 (Gateway Authority Class Assignment)
- Blocker 1.2 (Context Bundle Signing Authority)

**Open Questions (Deferred):**
- Trust registry fail-closed vs. cache policy (Blocker 1.3)
- Scope semantics definition (Blocker 1.4)
- Context Bundle transmission protocol (Blocker 2.3)

