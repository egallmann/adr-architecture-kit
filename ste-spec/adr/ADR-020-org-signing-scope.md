# ADR-020: ORG-Level Signing Scope

**Status:** Accepted  
**Date:** 2025-12-23  
**Closes:** Axis 2 Blockers (Signing Scope Ambiguity)  
**Depends On:** ADR-019 (Gateway Authority and Signing Model)

---

## Context

The STE-System specification (ste-system.iso42010.md) establishes cryptographic signing as the mechanism for authority verification and non-repudiation. However, the specification lacked explicit boundaries defining what requires ORG-level signing vs. other authority classes or no signing at all.

This created ambiguity about:
1. Whether execution eligibility decisions require ORG signing
2. Whether Gateway outputs constitute canonical artifacts
3. Whether derived state (graph indexes, query results) requires signing
4. The scope boundary between canonical truth (requires ORG signing) and ephemeral enforcement outcomes (do not require signing)

Without explicit signing scope boundaries, implementations risk:
- **Authority inflation:** Expanding ORG signing beyond canonical truth
- **False equivalence:** Treating enforcement outcomes as canonical artifacts
- **Key management complexity:** Requiring signing keys for components that verify but do not attest

## Decision

**ORG-level signing SHALL be required only for artifacts that assert or ratify canonical truth.**

### ORG Signing Required For

1. **Canonical Invariants**
   - Prime Invariants (foundational constraints)
   - System Invariants (system-wide rules)
   - Domain Invariants (domain-specific constraints)

2. **Canonical Artifacts**
   - Canonical slices (extracted from merged code)
   - Canonical relationship artifacts (validated through merge)
   - Canonical policies and assertions

3. **Trust Registry Operations**
   - Authority registrations (adding identities)
   - Delegations (granting authority to lower classes)
   - Revocations (removing authority)

4. **Canonicalization Events**
   - Promotion events (provisional → canonical transition metadata)
   - RECON completion markers (when canonical state is published)

### ORG Signing NOT Required For

1. **Ephemeral Enforcement Outcomes**
   - Execution eligibility decisions (derived from signed inputs)
   - Gateway enforcement results (point-in-time verifications)
   - CEM validation outcomes (deterministic checks)

2. **Workspace-Scoped Artifacts**
   - Context Bundles (signed by Human or PROJECT authority per ADR-019)
   - Provisional assertions (signed by Human or PROJECT authority)
   - Agent proposals (workspace-local, non-canonical)

3. **Derived State**
   - Graph indexes (derived from canonical slices)
   - Query results (computed from canonical artifacts)
   - Cache entries (derived, ephemeral)

## Rationale

### Why Limit ORG Signing to Canonical Truth

**1. Scarcity of Authority**

ORG is the root of trust in the STE-System (INV-AUTH-1). Expanding ORG signing scope dilutes authority by:
- Creating false equivalence between persistent truth and ephemeral decisions
- Requiring ORG key availability for non-attestation operations
- Weakening the semantic meaning of "ORG-signed" from "canonical truth" to "any system output"

**2. Determinism Preservation**

Ephemeral outcomes (execution eligibility decisions) are recomputable deterministically from signed inputs:
- Context Bundle (signed by Human/PROJECT) + Canonical Invariants (signed by ORG) → Eligibility Decision (unsigned)
- Same inputs → same decision (§8.1.4 deterministic algorithm)
- Signing the decision adds no security value; the decision can be re-evaluated by anyone with the same inputs

**3. Key Management Simplicity**

Only entities that attest canonical truth require signing keys:
- ADF signs canonical artifacts (extraction output)
- ORG Authority Service signs trust registry entries and invariants
- Gateway verifies signatures but does not sign (per ADR-019)

Requiring Gateway to sign eligibility decisions would necessitate key management for a component whose role is verification, not attestation.

**4. Non-Repudiation Alignment**

Long-term non-repudiation is needed only for persistent, authoritative truth:
- Canonical artifacts persist indefinitely (immutable, versioned)
- Eligibility decisions are ephemeral (Context Bundle TTL: 5-15 minutes per §9.1.5)
- Re-evaluation is always possible from signed inputs; historical eligibility decisions need not be preserved

### Why NOT Sign Execution Eligibility

**1. Ephemeral Nature**

Execution eligibility decisions are time-bounded:
- Context Bundles expire in 5-15 minutes (§9.1.5)
- Eligibility is bound to specific bundle + canonical invariants + timestamp
- After bundle expiration, eligibility decision is meaningless (bundle no longer exists)

Signing short-lived decisions creates false equivalence with canonical artifacts (which are immutable and long-lived).

**2. Derived State**

Eligibility is computed deterministically from signed inputs (§8.1.4):
- Input 1: Context Bundle signature (Human/PROJECT authority)
- Input 2: Canonical Invariant signatures (ORG authority)
- Input 3: Trust registry entries (ORG authority)
- Output: Eligible | Rejected (unsigned decision)

The decision derives its authority from the signed inputs, not from an additional signature on the decision itself.

**3. Deterministic Re-evaluation**

Gateway eligibility evaluation is deterministic (§8.1.4 STEP 1-7):
- Given same Context Bundle, same canonical invariants, same trust registry state → same decision
- Replay protection achieved by binding eligibility to signed inputs (bundle signature proves authorship, invariant signatures prove canonical truth)
- Re-evaluation is auditable without signing outcomes

**4. False Equivalence Prevention**

Signing eligibility decisions would suggest they are canonical truth:
- Canonical artifacts: Persistent, immutable, ORG-signed, represent authoritative architectural state
- Eligibility decisions: Ephemeral, recomputable, unsigned, represent point-in-time enforcement outcomes

Creating signed eligibility decisions would blur this critical distinction.

## Explicit Non-Goals

This ADR explicitly does NOT:

1. **Define cryptographic algorithms** - RSA, ECDSA, key sizes are implementation-specific
2. **Define key management** - HSM usage, rotation policies, key escrow out of scope
3. **Define audit log signing** - Separate audit system may sign logs; Gateway does not sign enforcement outcomes
4. **Touch Gateway authority** - Axis 1 (ADR-019) closed Gateway authority; this ADR defines ORG signing scope
5. **Define serialization mechanisms** - Deterministic YAML serialization remains undefined (Blocker 1.6 open)

## Consequences

### Enables

**Clear Signing Boundary**
- ORG signing limited to canonical truth (artifacts, invariants, trust registry, promotion events)
- Enforcement outcomes (eligibility decisions) explicitly unsigned
- No ambiguity about what requires ORG authority

**Minimal Signing Surface Area**
- Only entities attesting canonical truth require signing keys
- Gateway operates without signing keys (verification only)
- Reduces key management complexity and attack surface

**Deterministic Enforcement Without Attestation Overhead**
- Eligibility evaluation remains deterministic (§8.1.4)
- Re-evaluation provides replay protection without signing outcomes
- Fail-closed verification of inputs (if inputs invalid, reject) without signing outputs

**Fail-Closed Verification of Inputs**
- Gateway verifies signed inputs (bundles, invariants, trust registry)
- If any input signature invalid or unavailable, eligibility fails closed (§8.2.2 G-ENF-4)
- Output signing unnecessary; security derives from input verification

### Forbids

**Signing Execution Eligibility Decisions with ORG Authority**
- Gateway SHALL NOT sign eligibility decisions
- Eligibility proofs in model invocation payloads are unsigned metadata (per ADR-019 §9.2.3)
- ORG signing reserved for canonical truth only

**Treating Gateway Enforcement Results as Canonical Artifacts**
- Eligibility decisions are not canonical artifacts
- Eligibility decisions SHALL NOT be persisted as authoritative state
- Eligibility decisions SHALL NOT be ORG-signed

**Persisting Unsigned Eligibility Decisions as Authoritative**
- Eligibility decisions may be logged for audit (unsigned logs)
- Logged decisions are not authoritative; re-evaluation is authoritative
- Audit logs MAY be signed by separate audit system (not Gateway, not ORG)

**Authority Inflation Through Signing Scope Creep**
- ORG signing SHALL NOT expand to derived state (graph indexes, query results)
- ORG signing SHALL NOT expand to validation outcomes (merge-time validation results)
- ORG signing SHALL NOT expand to enforcement outcomes (eligibility decisions)

### Trade-offs

**Audit Reconstruction Complexity**

Without Gateway signatures on eligibility decisions, audit reconstruction requires:
- Verifying Context Bundle signature (signed by Human/PROJECT)
- Verifying canonical invariant signatures (signed by ORG)
- Verifying trust registry state at decision time (ORG-signed entries)
- Re-evaluating eligibility algorithm (deterministic, repeatable)

**Mitigation:** Gateway logs include all inputs (bundle ID, invariant versions, trust registry state, decision timestamp). Re-evaluation is deterministic; auditors can reproduce decision.

**Model Provider Trust**

Model provider receives unsigned eligibility proof from Gateway. Provider must:
- Trust Gateway identity (mutual TLS authentication)
- Trust Gateway enforced eligibility before forwarding payload
- Not treat eligibility proof as cryptographic attestation of canonical truth

**Mitigation:** Gateway-to-model-provider channel secured via transport-level authentication (mutual TLS per §9.2.6 candidate). Eligibility proof protected by channel security, not artifact-level signing.

## Related ADRs

**ADR-019 (Gateway Authority and Signing Model):**  
Established Gateway does not sign. This ADR defines what ORG DOES sign (canonical truth only).

**ADR-008 (Correctness and Consistency Contract):**  
Established provenance requirements for canonical artifacts. This ADR clarifies signing as provenance mechanism for canonical artifacts only, not for enforcement outcomes.

**ADR-001 (Deterministic Extraction):**  
**ADR-001 (Deterministic Extraction):**  
Required deterministic extraction for canonical artifacts. This ADR extends determinism to enforcement: eligibility decisions are recomputable deterministically from signed inputs without signing outputs.

## Blocker Resolution

### Axis 2 Blockers Addressed

This ADR provides signing scope clarity that enables resolution of:

**Partial Closure - Contradiction 1.6 (Deterministic Serialization Requirement):**
- **Contribution:** Clarifies serialization needed only for ORG-signed artifacts (canonical artifacts, trust registry, invariants)
- **Remaining Gap:** Serialization mechanism itself still undefined (blocker remains open for mechanism specification)

**Partial Closure - Undefined Behavior 2.2 (Merge-Time Validation Mechanisms):**
- **Contribution:** Clarifies validation outcomes are not signed; only resulting canonical artifacts are ORG-signed after validation succeeds
- **Remaining Gap:** Validation mechanisms themselves still undefined (blocker remains open for mechanism selection)

**Partial Closure - Missing Definition 5.7 (Deterministic Mechanisms Examples):**
- **Contribution:** Separates deterministic validation (deterministic checks, no signing required) from ORG signing (attestation of canonical truth post-validation)
- **Remaining Gap:** Example validation mechanisms still non-normative (blocker remains open for normative framework)

### Signing Scope Ambiguities Resolved

1. **Execution eligibility decisions:** Explicitly unsigned (ephemeral enforcement outcomes)
2. **Gateway outputs:** Explicitly unsigned (verification outcomes, not attestations)
3. **Derived state:** Explicitly unsigned (graph indexes, query results, cache)
4. **Canonical truth boundary:** Explicitly defined (artifacts, invariants, trust registry, promotion events)

## Implementation Notes

### System Spec Amendments Required

1. **§6.2.6 - ORG Signing Scope Definition** (new section) - Define ORG signing boundary
2. **§11.1.3 INV-STATE-2** - Clarify signing requirement for canonical artifacts only
3. **§10.2** - Add note clarifying ORG signing occurs during canonical publication

### Verification Steps

After spec amendments, verify:
- No section implies eligibility decisions require ORG signing
- ORG signing scope limited to canonical truth artifacts
- Gateway authority does not expand through signing semantics (Axis 1 preserved)
- Determinism claims intact and testable

## Status

**Accepted:** 2025-12-23

**Supersedes:** No prior ADRs

**Axis 2 Closed:** Signing scope boundaries defined

**Blocks Closed:**
- Signing scope ambiguity (Axis 2)
- Partial contribution to blockers 1.6, 2.2, 5.7 (serialization, validation, mechanisms - full closure requires additional ADRs)

**Open Questions (Deferred):**
- Deterministic YAML serialization mechanism (Blocker 1.6)
- Merge-time validation mechanisms (Blocker 2.2)
- Audit log signing policy (out of scope - separate system)

