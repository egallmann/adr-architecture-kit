# ADR-021: Gateway Trust Verification Model

**Status:** Ratified  
**Date:** 2025-12-23  
**Supersedes:** None  
**Related:** ADR-019 (Gateway Authority and Signing Model), ADR-020 (ORG-Level Signing Scope)

## Context

The STE-Gateway enforces execution eligibility by verifying cryptographic signatures on Context Bundles and canonical artifacts. This verification depends on a Trust Registry that maps signing identities to allowed scopes and artifact types.

Prior to this ADR, the specification contained ambiguities regarding:
- Whether the Gateway itself is a Trust Registry principal
- When trust verification occurs (startup vs. per-request)
- Whether cached trust material can be used to approve execution
- How the Gateway obtains initial trust verification material
- What happens when the Trust Registry is unavailable

These ambiguities create operational pressure to relax fail-closed guarantees and introduce implicit trust relationships that undermine the authority scarcity principle.

## Decision

### Gateway is Not a Trust Registry Principal

The Gateway SHALL NOT appear as a principal in the Trust Registry. The Gateway:
- Holds no delegated authority
- Does not sign canonical artifacts
- Does not attest to truth
- Does not require a Trust Registry entry for its own identity

**Rationale:** The Gateway enforces eligibility decisions but does not create or attest to canonical truth. Authority must remain scarce and limited to principals that produce or ratify canonical artifacts (ORG, Domain, PROJECT, Human authorities).

### Trust Verification is Per-Request

Trust verification SHALL occur per eligibility evaluation request (or per evaluation cycle). The Gateway SHALL NOT rely solely on startup-time trust verification.

**Rationale:** Contemporaneous trust evaluation ensures that:
- Revocations are respected immediately
- Expired credentials cannot be used
- Trust decisions reflect current registry state
- Deterministic enforcement is maintained

### Trust Registry Unavailability Fails Execution Closed

If the Trust Registry is unavailable or unverifiable during eligibility evaluation, the Gateway SHALL fail closed:
- Execution eligibility MUST be denied
- Canonical promotion MUST be blocked
- Read-only evaluation MAY be allowed but MUST be explicitly marked as non-authoritative

**Rationale:** Failing open (approving execution when trust cannot be verified) allows bypass. Fail-closed behavior ensures no reasoning occurs without verifiable authority.

### Bootstrap Trust Root Provides Verification Material Only

The Gateway SHALL obtain initial trust verification material through a minimal static bootstrap trust root. This bootstrap material:
- Contains only public verification keys or certificates
- Is used solely to verify the Trust Registry itself
- MUST NOT authorize execution on its own
- Provides the minimal trust surface required to validate the registry

**Rationale:** Bootstrap trust must be minimal to reduce attack surface. The bootstrap validates the Trust Registry, which in turn validates all other identities. Bootstrap material alone cannot authorize execution.

### Cached Trust is Non-Authoritative for Execution

Cached trust material SHALL NOT be used to approve execution eligibility. Cached trust MAY be used only for:
- Read-only evaluation (explicitly marked non-authoritative)
- Performance optimization of non-critical queries
- Degraded-mode operations that cannot modify canonical state

If cached trust is used, the Gateway MUST:
- Mark results as non-authoritative
- Prevent canonical promotion
- Log the use of cached trust for audit

**Rationale:** Cached trust introduces staleness risk. A cached identity might be revoked, expired, or have reduced scope. Using stale trust to approve execution violates contemporaneous verification and enables bypass through timing attacks.

## Explicit Non-Goals

This ADR does NOT define:
- Trust Registry implementation mechanism (DynamoDB, PostgreSQL, etc.)
- Cryptographic algorithms for trust material (RSA, ECDSA, etc.)
- Operational availability targets or SLAs for the Trust Registry
- Specific TTL values or cache eviction policies
- Key management procedures for bootstrap material
- Gateway authority or signing semantics (covered by ADR-019)
- ORG-level signing scope (covered by ADR-020)

## Consequences

### Enables

1. **Clear Trust Verification Boundary:** No ambiguity about Gateway's role in the trust model; Gateway verifies but does not create trust
2. **Contemporaneous Trust Evaluation:** Revocations and expirations are respected immediately, not after cache expiry
3. **Deterministic Fail-Closed Enforcement:** Trust verification failures always block execution; no operational pressure to fail open
4. **Minimal Bootstrap Trust Surface:** Only the Trust Registry itself is trusted via bootstrap; all other trust is derived
5. **Explicit Cache Policy:** Cached trust cannot be misused to approve execution; degraded operations are clearly labeled

### Forbids

1. **Gateway as Trust Registry Principal:** Gateway cannot appear in the registry; no self-attestation or circular trust
2. **Startup-Only Trust Verification:** Trust must be verified per-request; startup caching cannot replace live verification
3. **Cached Trust Approving Execution:** Stale trust cannot authorize reasoning; cache is read-only only
4. **Bootstrap Material Authorizing Execution:** Bootstrap alone is insufficient; full Trust Registry verification required
5. **Failing Open When Registry Unavailable:** Registry unavailability always blocks execution; no bypass path

## Blocker Resolution

This ADR fully resolves the following blocker from the Spec Pressure Report:

- **1.3: Trust Registry Fail-Closed vs. Cache Policy** - Clarifies that cached trust cannot approve execution and live Trust Registry access is required for eligibility decisions

This ADR also reinforces decisions from Axis 1 (ADR-019):
- **1.1: Gateway Authority Class** (partial) - Reinforces that Gateway is not a registry principal
- **1.2: Gateway Signing Model** (partial) - Reinforces that Gateway holds no delegated authority

## Implementation Notes

While this ADR does not define implementation mechanisms, implementers should note:

1. **Bootstrap Material Management:** Bootstrap trust material must be distributed securely and updated through a separate, controlled process
2. **Cache Semantics:** If caching is implemented, it must enforce read-only restrictions programmatically
3. **Failure Logging:** Trust verification failures must be logged with sufficient context for debugging and audit
4. **Performance Considerations:** Per-request verification may require Trust Registry performance optimization (replication, read replicas, etc.)

## References

- Spec Pressure Report: Blocker 1.3 (Trust Registry Fail-Closed vs. Cache Policy)
- `specifications/ste-system.iso42010.md` §6.2 (Authority and Trust Model)
- `specifications/ste-system.iso42010.md` §8.1.4 (Eligibility Evaluation Algorithm)
- `specifications/ste-system.iso42010.md` §11.1.4 (Authority Invariants)
- ADR-019: Gateway Authority and Signing Model
- ADR-020: ORG-Level Signing Scope

