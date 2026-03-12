# ADR-022: Fail-Closed Semantics and Enforcement Scope

**Status:** Ratified  
**Date:** 2025-12-23  
**Supersedes:** None  
**Related:** ADR-019 (Gateway Authority and Signing Model), ADR-020 (ORG-Level Signing Scope), ADR-021 (Gateway Trust Verification Model)

## Context

The STE-System enforces execution eligibility and canonical promotion through deterministic validation. Multiple sections reference "fail-closed" behavior, but the specification lacked:
- Comprehensive definition of fail-closed scope and triggers
- Explicit prohibition of bypass paths
- Distinction between enforcement (correctness) and availability (operational concern)
- Clarification of what actions are halted vs. what may continue under fail-closed conditions

This ambiguity creates operational pressure to relax correctness guarantees through override mechanisms, emergency modes, or environment-specific relaxations that would undermine determinism and authority scarcity.

## Decision

### Fail-Closed Scope

Fail-closed semantics SHALL apply to:
1. **Execution Eligibility:** Model invocation cannot proceed without complete and successful validation
2. **Canonical Promotion:** Provisional state cannot transition to canonical without complete and successful validation

Fail-closed means **authoritative actions are halted**, not that the system is unavailable. Non-authoritative inspection and read-only evaluation may continue.

### Fail-Closed Triggers

Fail-closed SHALL be triggered when any of the following conditions occur:

1. **Trust Verification Failure**
   - Trust Registry unavailable or unverifiable
   - Identity not found in Trust Registry
   - Identity expired or revoked
   - Signature cryptographically invalid

2. **Signature Validation Failure**
   - Missing signatures on required artifacts
   - Unverifiable signatures (key mismatch, algorithm failure)
   - Expired signatures (ValidUntil timestamp passed)

3. **Invariant Validation Failure or Indeterminacy**
   - Required invariants unavailable from ADF
   - Invariants unsigned or signature invalid
   - Invariant conflict detected (multiple contradictory invariants)
   - Invariant evaluation indeterminate (cannot determine pass/fail)

4. **Validation Mechanism Undefined or Non-Executable**
   - Required validation mechanism not implemented
   - Validation mechanism fails to execute (error, timeout, crash)
   - Validation mechanism returns indeterminate result (neither pass nor fail)

5. **Missing or Ambiguous Evaluation Context**
   - CEM envelope incomplete or malformed
   - MVC references unresolvable
   - Provisional state mislabeled or ambiguous

If any prerequisite for execution eligibility or canonical promotion cannot be fully validated, the system MUST fail closed.

### Fail-Closed Semantics are Non-Bypassable

Fail-closed SHALL NOT be bypassable through any mechanism, including but not limited to:

- **No Operator Override:** No human operator or administrator can override fail-closed decisions
- **No Emergency Mode:** No special operational mode bypasses fail-closed requirements
- **No Environment-Specific Relaxation:** No development, staging, or production environment can relax fail-closed semantics
- **No Best-Effort Execution:** No fallback path allows execution to proceed with incomplete validation

**Rationale:** Any bypass mechanism introduces implicit trust and undermines determinism. If validation cannot be completed, the correct action is to halt, not to proceed with degraded assurance.

### Read-Only Evaluation Under Fail-Closed

Read-only evaluation MAY be permitted under fail-closed conditions to aid debugging and inspection, subject to the following restrictions:

- **Explicitly Non-Authoritative:** Results MUST be marked as non-authoritative and degraded
- **Cannot Approve Execution:** Read-only evaluation cannot transition to execution eligibility
- **Cannot Approve Promotion:** Read-only evaluation cannot enable canonical promotion
- **Degraded Status Visible:** All outputs must clearly indicate degraded/non-authoritative status
- **Audit Logging:** Use of read-only mode under fail-closed conditions must be logged

**Rationale:** Non-authoritative inspection aids debugging without compromising correctness. Operators can understand system state and validation failures without enabling unverifiable execution.

### Enforcement vs. Availability Distinction

**Enforcement (Correctness):**
- Governs whether authoritative actions (execution, promotion) may proceed
- Determined by validation completeness and success
- Never relaxed, never bypassed
- Fail-closed applies to enforcement

**Availability (Operational Concern):**
- Governs whether system components are reachable and responsive
- Affected by infrastructure, networking, dependencies
- May degrade without compromising correctness
- Fail-closed does not mean system unavailability

When Trust Registry is unavailable:
- **Enforcement:** Halted (no execution eligibility can be granted)
- **Availability:** Degraded (system responsive but cannot approve authoritative actions)
- **Outcome:** Fail-closed (execution denied, read-only inspection may continue)

This distinction ensures correctness guarantees are not weakened by availability concerns.

## Explicit Non-Goals

This ADR does NOT define:
- Operational availability targets or SLAs (99.9%, 99.99%, etc.)
- Retry or queuing mechanisms for failed requests
- Incident response or escalation procedures
- Specific validation mechanism implementations
- Caching policies or performance optimizations
- Gateway authority, signing, or trust models (covered by ADRs 019-021)

## Consequences

### Enables

1. **Unambiguous Fail-Closed Semantics:** Comprehensive trigger list and scope definition eliminate interpretation ambiguity
2. **Clear Enforcement vs. Availability Distinction:** Correctness guarantees separated from operational concerns
3. **Explicit Bypass Prevention:** No implicit trust through override mechanisms
4. **Read-Only Debugging:** Non-authoritative inspection aids troubleshooting without compromising correctness
5. **Deterministic Enforcement:** Validation completeness required; partial or best-effort execution forbidden

### Forbids

1. **Operator Override:** Human operators cannot bypass fail-closed decisions
2. **Emergency Mode:** No special operational mode relaxes fail-closed requirements
3. **Environment-Specific Relaxation:** Development, staging, and production all enforce fail-closed identically
4. **Best-Effort Execution:** Execution cannot proceed with incomplete or indeterminate validation
5. **Promotion Under Degraded Conditions:** Canonical promotion requires full validation; degraded state cannot promote
6. **Treating Validation as Advisory:** Validation failures must halt execution; cannot be warnings or post-hoc audits

## Blocker Resolution

This ADR partially resolves the following blockers from the Spec Pressure Report:

- **4.1: Merge-Time Validation Mechanisms** (partial) - Clarifies that validation indeterminacy or unavailability triggers fail-closed for canonical promotion. Validation mechanism definition remains undefined but must comply with fail-closed semantics.

This ADR also reinforces and extends:

- **1.3: Trust Registry Fail-Closed vs. Cache Policy** (extension) - Extends fail-closed beyond trust verification to all validation stages (invariants, signatures, validation mechanisms, evaluation context)

## Implementation Notes

While this ADR does not define implementation mechanisms, implementers should note:

1. **Fail-Closed Logging:** All fail-closed events must be logged with full context for debugging and audit
2. **Graceful Degradation:** Read-only mode should provide useful diagnostics while enforcing non-authoritative status
3. **Error Messaging:** Rejection responses must clearly indicate which validation stage failed and why
4. **No Silent Failures:** Fail-closed must be explicit and visible; silent failures that appear as success are forbidden

## References

- Spec Pressure Report: Blocker 4.1 (Merge-Time Validation Mechanisms)
- `specifications/ste-system.iso42010.md` §8.1.4 (Eligibility Evaluation Algorithm)
- `specifications/ste-system.iso42010.md` §8.2.2 (Enforcement Guarantees - G-ENF-4)
- `specifications/ste-system.iso42010.md` §11.1.4 (Authority Invariants - INV-AUTH-4)
- ADR-019: Gateway Authority and Signing Model
- ADR-020: ORG-Level Signing Scope
- ADR-021: Gateway Trust Verification Model

