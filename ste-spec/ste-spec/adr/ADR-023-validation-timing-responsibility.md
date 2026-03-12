# ADR-023: Validation Timing and Responsibility

**Status:** Ratified  
**Date:** 2025-12-23  
**Supersedes:** None  
**Related:** ADR-019 (Gateway Authority and Signing Model), ADR-020 (ORG-Level Signing Scope), ADR-021 (Gateway Trust Verification Model), ADR-022 (Fail-Closed Semantics and Enforcement Scope)

## Context

The STE-System performs validation at multiple lifecycle stages (workspace preflight, merge-time, pre-execution), but the specification lacked:
- Explicit assignment of validation authority by lifecycle stage
- Clear statement that only Gateway can approve execution
- Normalized validation outcomes across all stages
- Clarification of when validation is blocking vs. advisory
- Definition of who executes invariant conflict detection and when

This ambiguity creates risk that Runtime self-validation could be misinterpreted as authoritative, that merge-time validation could be bypassed, or that indeterminate validation results could weaken enforcement.

## Decision

### Validation Authority by Lifecycle Stage

**ADF (Ingestion/Merge-Time Validation):**
- Validates artifacts for admissibility and canonical promotion
- MAY accept provisional artifacts with warnings (WARN outcome)
- MUST NOT promote artifacts to canonical without passing required deterministic validation
- MAY execute invariant conflict detection to prevent conflicts entering canonical stores (preventative, fail-fast at merge)
- Validates schema conformance, reference existence, and artifact-specific rules
- Blocking authority: Can block canonical promotion only (not execution)

**Gateway (Pre-Execution Eligibility Validation):**
- Sole authority for execution approval (only Gateway can authorize execution)
- Performs mandatory validation before any execution
- Verifies trust (§6.2.6), signatures (§8.1.2 PREREQ-2), invariants (§8.1.2 PREREQ-3), and context completeness (§8.1.2 PREREQ-1)
- SHALL execute normative invariant conflict detection during eligibility evaluation
- Is the final blocking gate for execution
- Blocking authority: Can block execution eligibility

**Runtime (Local Preflight Validation):**
- MAY perform local coherence checks (self-validation, divergence detection, local consistency checks)
- Results are advisory only with respect to execution eligibility
- MUST NOT override Gateway decisions
- MAY report validation status in Context Bundle as informational metadata
- Provides fail-fast feedback to agents (optimize for compliant agents)
- Blocking authority: None with respect to execution (advisory only)

**Rationale:** Validation authority must be explicitly assigned to prevent bypass through Runtime self-approval or confusion about who can authorize execution. Gateway is the sole enforcement point (INV-ARCH-2); ADF is preventative; Runtime is advisory.

### Normalized Validation Outcomes

All validation stages MUST use normalized outcomes:

**Blocking Outcomes:**
- **PASS** - All checks succeeded; proceed with execution or promotion
- **FAIL** - One or more checks failed definitively; block execution or promotion
- **INDETERMINATE** - Validation could not be completed or result is ambiguous; MUST be treated as FAIL for execution eligibility and canonical promotion (§8.3 fail-closed semantics)

**Advisory Outcomes:**
- **WARN** - Validation passed but with warnings; execution or promotion may proceed with caution
- **INFO** - Informational message only; does not affect execution or promotion decisions

**INDETERMINATE Handling:**
- INDETERMINATE MUST block execution eligibility (treated as FAIL per §8.3)
- INDETERMINATE MUST block canonical promotion (treated as FAIL per §8.3)
- INDETERMINATE is not a "maybe" state; it is a definitive block due to inability to validate

**Rationale:** Normalizing validation outcomes eliminates "maybe" states that could weaken enforcement. INDETERMINATE must behave as FAIL to comply with fail-closed semantics (ADR-022); allowing INDETERMINATE to proceed would violate fail-closed guarantees.

### Invariant Conflict Detection Timing

**Gateway (Normative):**
- Gateway SHALL execute deterministic invariant conflict detection during eligibility evaluation (§8.1.4 eligibility algorithm, PREREQ-3)
- Conflict detection is mandatory for execution eligibility
- If conflict detection cannot be executed deterministically, execution MUST fail closed (§8.3)

**ADF (Preventative):**
- ADF MAY execute the same conflict detection algorithm during merge-time validation
- Purpose: Prevent conflicts from entering canonical stores (fail fast at merge, before publication)
- Conflict detection at merge-time is optional but recommended

**Rationale:** Gateway conflict detection is normative (definitive authority); ADF conflict detection is preventative (fail fast). Separating normative from preventative validation clarifies that Gateway is the authoritative enforcement boundary.

### Merge-Time Validation Mandatory for Canonical Promotion

**Promotion Requirements:**
- Promotion from provisional → canonical MUST pass required deterministic validation
- Validation outcomes of FAIL or INDETERMINATE MUST block canonical promotion (§8.3 fail-closed for promotion)
- Provisional artifacts MAY exist without passing merge-time validation (workspace proposals need not be validated immediately)
- Provisional artifacts MUST NOT enable authoritative execution unless explicitly permitted by policy and results marked non-authoritative

**Validation Strictness:**
- Merge-time validation MUST be deterministic (no LLM-based approval, per §10.1.4 C-ENR-1)
- Merge-time validation MUST not mutate slices (per §10.1.4 C-ENR-3)
- Merge-time validation executes after merge to develop/master, before canonical publication and ORG signing

**Rationale:** Prevents unvalidated truth from becoming canonical. Provisional state may exist for workspace experimentation, but canonical promotion requires deterministic validation to preserve ADR-001 determinism guarantees.

### Canonical vs Provisional State Validation Strictness

**Execution Claiming Deterministic Correctness:**
- MUST reference signed canonical inputs (§7.1.1 canonical state definition)
- MUST NOT reference provisional inputs unless explicitly permitted by policy

**Provisional Input Evaluation:**
- Provisional inputs MAY be evaluated only when ALL of the following conditions are met:
  - Explicitly permitted by organizational policy
  - Results are marked non-authoritative and degraded
  - Evaluation cannot trigger canonical promotion
- Provisional input evaluation is non-deterministic (workspace state may change)
- Provisional input evaluation results MUST be clearly labeled as non-canonical

**Rationale:** Deterministic execution requires canonical inputs. Allowing provisional inputs for authoritative execution would undermine reproducibility and auditability guarantees (§7.1.1 G-CAN-2, G-CAN-3).

## Explicit Non-Goals

This ADR does NOT define:
- Specific validation mechanism implementations (algorithms, schemas, execution models)
- Retry or queuing mechanisms for failed validations
- Trust, signing, or authority models (covered by ADRs 019-021)
- Fail-closed semantics (covered by ADR-022)
- Operational availability targets or SLAs
- Validation result schema structure (blocker 4.3 remains open)
- Detailed conflict detection algorithm (blocker 2.3 partially open; responsibility now clear)

## Consequences

### Enables

1. **Unambiguous Execution Authority:** Only Gateway can approve execution; eliminates bypass risk through Runtime self-approval
2. **Clear Validation Layering:** ADF validates for canonicalization, Gateway validates for execution, Runtime optimizes but doesn't authorize
3. **Normalized Validation Outcomes:** PASS, FAIL, INDETERMINATE, WARN, INFO apply consistently across all stages
4. **Explicit INDETERMINATE Handling:** Treated as FAIL for execution and promotion; eliminates "maybe" states
5. **Layered Conflict Detection:** Gateway normative (authoritative), ADF preventative (fail fast at merge)
6. **Canonical Promotion Rigor:** Merge-time validation blocks promotion; prevents unvalidated truth from becoming canonical

### Forbids

1. **Runtime or ADF Authorizing Execution:** Only Gateway has execution approval authority
2. **Treating INDETERMINATE as PASS:** INDETERMINATE must block execution and promotion (fail-closed)
3. **Promoting Without Validation:** Provisional → canonical transition requires deterministic validation
4. **Authoritative Execution with Provisional Inputs:** Execution claiming determinism requires canonical inputs
5. **Self-Validation Affecting Eligibility:** Runtime self-validation is informational metadata only
6. **Divergence Detection Affecting Eligibility:** Runtime divergence detection is informational metadata only
7. **Treating Runtime Validation as Blocking:** Runtime validation is advisory with respect to execution eligibility

## Blocker Resolution

This ADR fully or partially resolves the following blockers from the Spec Pressure Report:

- **2.1 Self-Validation Semantics** (Fully Resolved) - Self-validation is advisory only; Gateway treats as informational metadata; does not affect eligibility decisions
- **2.2 Divergence Detection Integration** (Fully Resolved) - Divergence detection is advisory only; Gateway treats as informational metadata; does not affect eligibility decisions
- **2.3 Invariant Conflict Detection Algorithm** (Partially Resolved) - Responsibility clear: Gateway SHALL execute during eligibility (normative); ADF MAY execute during merge (preventative); must be deterministic or fail closed. Algorithm definition remains undefined.
- **4.1 Merge-Time Validation Mechanisms** (Partially Resolved) - Timing and blocking semantics clear: merge-time validation blocks canonical promotion; outcomes normalized (INDETERMINATE treated as FAIL). Mechanism implementation remains undefined.
- **4.2 Validation Execution Model** (Partially Resolved) - Responsibility and timing clear: validation layered by lifecycle stage (ADF merge, Gateway execution, Runtime advisory). Execution model implementation remains undefined.

**Note:** This ADR defines **who validates what, when, and with what authority**. Specific validation algorithms, execution models, and mechanism implementations remain undefined but must comply with validation timing and responsibility model (§8.4).

## Implementation Notes

While this ADR does not define implementation mechanisms, implementers should note:

1. **Gateway Must Execute Conflict Detection:** Implementations must provide deterministic conflict detection at Gateway; cannot rely solely on Runtime or ADF conflict detection
2. **Runtime Validation is Optimization:** Runtime validation provides fail-fast feedback but does not replace Gateway enforcement
3. **Merge-Time Validation is Preventative:** ADF validation prevents invalid artifacts from becoming canonical but does not authorize execution
4. **INDETERMINATE is a Block:** Validation frameworks must treat INDETERMINATE as FAIL for execution and promotion
5. **Provisional Evaluation Requires Policy:** Allowing provisional inputs for evaluation requires explicit organizational policy and non-authoritative result marking

## References

- Spec Pressure Report: Blockers 2.1, 2.2, 2.3, 4.1, 4.2
- `specifications/ste-system.iso42010.md` §8.1.2 (Execution Eligibility Prerequisites)
- `specifications/ste-system.iso42010.md` §8.2.4 (Hard vs Soft Enforcement)
- `specifications/ste-system.iso42010.md` §8.3 (Fail-Closed Semantics and Enforcement Scope)
- `specifications/ste-system.iso42010.md` §10.1.3 (Deterministic Validation Mechanisms)
- `specifications/ste-system.iso42010.md` §10.2.4 (Enriched Artifact Publication)
- ADR-001: Deterministic Extraction
- ADR-019: Gateway Authority and Signing Model
- ADR-020: ORG-Level Signing Scope
- ADR-021: Gateway Trust Verification Model
- ADR-022: Fail-Closed Semantics and Enforcement Scope

