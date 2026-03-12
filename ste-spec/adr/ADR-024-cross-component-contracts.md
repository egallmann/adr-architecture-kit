# ADR-024: Cross-Component Contracts and Execution Eligibility Interface

**Status:** Ratified  
**Date:** 2025-12-23  
**Supersedes:** None  
**Related:** ADR-019 (Gateway Authority and Signing Model), ADR-020 (ORG-Level Signing Scope), ADR-021 (Gateway Trust Verification Model), ADR-022 (Fail-Closed Semantics and Enforcement Scope), ADR-023 (Validation Timing and Responsibility)

## Context

The STE-System requires Runtime (context proposer) and Gateway (eligibility evaluator) to interact synchronously for execution eligibility evaluation. However, the specification lacked:
- Explicit statement that Gateway is a pure validator that does not modify requests
- Clear assignment of CEM completeness responsibility to Runtime/ADF
- Normative definition of execution eligibility request and response contracts
- Explicit prohibition of Gateway enrichment, inference, or repair of incomplete requests
- Clarification of canonical vs provisional execution posture declaration
- Machine-actionable error handling with stable reason codes

This ambiguity creates risk that implementations might "helpfully" have Gateway complete or repair incomplete requests, undermining determinism and auditability, or that Runtime might rely on Gateway to fix incomplete context.

## Decision

### Gateway is a Pure Validator

**The Gateway SHALL NOT modify, enrich, normalize, infer, or complete any execution eligibility request.**

The Gateway is a pure validator and evaluator over a complete CEM (Cognitive Execution Model). All required context MUST be provided by the caller (STE-Runtime or STE-Runtime + ADF).

Any missing, ambiguous, or inconsistent input MUST result in fail-closed denial (INDETERMINATE).

**Rationale:** Gateway as pure validator ensures determinism and reproducibility. If Gateway infers or repairs requests, eligibility evaluation becomes non-deterministic and audit trails become incomplete.

### Runtime/ADF Constructs Complete CEM

**STE-Runtime (or STE-Runtime + ADF) is solely responsible for constructing a complete, self-contained execution eligibility request (Context Bundle).**

The Gateway SHALL assume the Context Bundle is complete. If the Gateway cannot verify completeness (missing required fields, unresolvable references, ambiguous inputs), it MUST fail closed (INDETERMINATE denial).

**Rationale:** Clear responsibility assignment prevents Gateway from being blamed for incomplete context and prevents Runtime from relying on Gateway to "fix" incomplete bundles.

### Execution Eligibility Request Contract

**Request Structure:**

The execution eligibility request is a deterministic, declarative envelope structured as a Context Bundle (per §9.1.2 Context Bundle Structure).

**Required Fields:**
- **Principal Identity Reference:** Identity of requester (user, project, workspace)
- **Authority Chain Reference:** Reference to trust registry entry for identity verification
- **Environment Identifier:** Target environment (prod, staging, dev)
- **Scope Identifier:** Scope of execution (domain, service, operation)
- **Action Intent:** Declared reasoning intent
- **Context Bundle Reference:** Self-reference or hash of bundle for audit
- **Integrity Bindings:** Hashes of all referenced canonical artifacts
- **Execution Posture Declaration:** `canonical-only` (default) or `provisional-allowed` (explicit)

**Request Semantics:**
- Request MUST use references and hashes, not inline canonical artifacts
- Gateway resolves references from authoritative sources (Trust Registry, ADF canonical stores, invariant sources)
- Missing or ambiguous fields MUST result in INDETERMINATE denial (fail-closed)
- Request MUST be signed by Human or PROJECT authority (per §9.1.4 Context Bundle Signing)

**Execution Posture:**
- **canonical-only (default):** All references must be signed canonical artifacts; deterministic execution
- **provisional-allowed (explicit):** Permits evaluation using provisional inputs (per §7.2.7 policy requirements); results marked degraded and non-authoritative

**Rationale:** Normative contract eliminates ambiguity about what crosses component boundaries. Reference-based design enables Gateway to verify artifacts independently. Explicit posture declaration prevents accidental use of provisional state for authoritative execution.

### Gateway Resolves References from Authoritative Sources

**The Gateway SHALL resolve all references from authoritative sources:**
- Trust Registry for identity and authority verification (per §6.2.6 Gateway Trust Verification Model)
- ADF canonical artifact stores for canonical slices, invariants, policies
- Invariant sources for canonical invariants

**If any required reference cannot be resolved or verified, execution MUST fail closed (INDETERMINATE).**

Reference resolution failures include:
- Trust Registry unavailable
- Referenced artifact not found
- Referenced artifact signature invalid
- Referenced artifact revoked or expired

**Rationale:** Gateway-controlled reference resolution ensures Gateway validates all inputs independently. Gateway does not trust caller's inline artifacts or ADF validation results blindly.

### Execution Eligibility Response Contract

**Response Structure:**

The execution eligibility response is a structured, machine-actionable envelope containing:
- **Decision:** `ALLOW` | `DENY` | `INDETERMINATE`
- **Reason Code:** Stable machine-readable code indicating reason for decision
- **Echo of Evaluated References:** Hashes and identifiers of all references evaluated (for audit)
- **Degradation Indicator:** Boolean indicating if execution uses degraded posture (provisional-allowed)

**Decision Semantics:**
- **ALLOW:** All validation passed; execution may proceed
- **DENY:** Validation failed definitively (e.g., trust verification failure, invariant violation)
- **INDETERMINATE:** Validation could not be completed or result is ambiguous; MUST be treated as DENY for execution (per §8.4.2 Normalized Validation Outcomes)

**Stable Reason Codes:**
- `MISSING_REQUIRED_FIELD` - Required field missing from request (maps to INDETERMINATE)
- `UNRESOLVABLE_REFERENCE` - Referenced artifact cannot be resolved (maps to INDETERMINATE)
- `TRUST_VERIFICATION_FAILURE` - Trust Registry unavailable or identity verification failed (maps to DENY per §6.2.6)
- `INVARIANT_VALIDATION_FAILURE` - Invariant validation failed or indeterminate (maps to DENY or INDETERMINATE based on failure type)
- `CONTEXT_INCOMPLETE` - Context Bundle incomplete or ambiguous (maps to INDETERMINATE)
- `SIGNATURE_INVALID` - Bundle or artifact signature verification failed (maps to DENY)
- `BUNDLE_EXPIRED` - Context Bundle TTL expired (maps to DENY per §9.1.5)
- `EXECUTION_ELIGIBLE` - All checks passed (maps to ALLOW)

**Response Semantics:**
- Response MUST be structured (not free text)
- Response MUST echo input references for audit trail and reconstruction
- Response MUST NOT be signed by Gateway (Gateway does not attest authority per ADR-019)
- Response includes eligibility decision metadata (unsigned, ephemeral) for audit purposes

**Rationale:** Stable reason codes enable machine-actionable error handling and deterministic retry logic. Echo of references enables audit reconstruction. INDETERMINATE treated as DENY ensures fail-closed semantics.

### Synchronous Blocking Interaction

**Runtime → Gateway interaction SHALL be synchronous and blocking for execution.**

**Execution MUST NOT begin until the Gateway returns an ALLOW decision.** Optimistic execution (starting reasoning before Gateway response) is forbidden. Asynchronous eligibility evaluation with eventual consistency is prohibited (per INV-ARCH-6).

**Rationale:** Synchronous blocking prevents time-of-check-to-time-of-use (TOCTOU) attacks where state changes between eligibility check and execution. Prohibits speculative execution that might bypass enforcement.

### Error Handling Contract

**Error classes defined with deterministic mappings:**

| Error Class | Decision Code | Reason Code | Meaning |
|-------------|---------------|-------------|---------|
| Missing required field | INDETERMINATE | MISSING_REQUIRED_FIELD | Request incomplete; cannot validate |
| Unresolvable reference | INDETERMINATE | UNRESOLVABLE_REFERENCE | Referenced artifact not found or unverifiable |
| Trust verification failure | DENY | TRUST_VERIFICATION_FAILURE | Trust Registry unavailable or identity verification failed |
| Invariant validation failure (definitive) | DENY | INVARIANT_VALIDATION_FAILURE | Invariant explicitly violated |
| Invariant validation indeterminate | INDETERMINATE | INVARIANT_VALIDATION_FAILURE | Invariant validation could not complete |
| Context incomplete or ambiguous | INDETERMINATE | CONTEXT_INCOMPLETE | Bundle structure or content ambiguous |
| Signature invalid | DENY | SIGNATURE_INVALID | Cryptographic signature verification failed |
| Bundle expired | DENY | BUNDLE_EXPIRED | TTL exceeded |

**Rationale:** Deterministic error mapping enables reproducible failures. INDETERMINATE used when validation cannot complete (fail-closed). DENY used when validation completes with definitive negative result.

### ADF Integration by Artifact Production

**ADF produces canonical artifacts and validation results by reference:**
- ADF publishes canonical slices, invariants, relationship artifacts to canonical stores
- Gateway resolves these artifacts by reference during eligibility evaluation
- Gateway verifies artifact signatures independently (does not trust ADF validation results blindly)

**Gateway execution-time validation remains authoritative** (per ADR-023 Validation Timing and Responsibility). ADF merge-time validation is preventative (blocks canonical promotion) but does not replace Gateway enforcement.

**Rationale:** ADF and Gateway validation are layered (merge-time preventative, execution-time authoritative). Gateway maintains authority over execution eligibility decisions.

## Explicit Non-Goals

This ADR does NOT define:
- **Transport protocols** (HTTP, gRPC, message queues) - implementation-specific
- **Serialization formats** (YAML, JSON, protobuf) - implementation-specific unless required for determinism
- **Gateway internal algorithms** (trust verification logic, invariant resolution mechanisms)
- **Authority, trust, signing, validation, or fail-closed models** (covered by ADRs 019-023; not modified)
- **Retry, queuing, or circuit breaker patterns** - operational concerns outside contract definition
- **Gateway scalability characteristics** (single instance vs distributed) - deployment-specific
- **Model provider selection or routing** - Gateway responsibility outside contract scope

## Consequences

### Enables

1. **Unambiguous Runtime-Gateway Contract Boundaries:** Request and response contracts are normatively defined; no room for "helpful" modifications
2. **Independent Implementation and Testing:** Runtime and Gateway can be implemented and tested independently against contract specification
3. **Deterministic, Reproducible Eligibility Evaluation:** Pure validator semantics ensure same request always produces same result
4. **Clear Failure Semantics:** No silent inference or repair; all failures explicit with stable reason codes
5. **Machine-Actionable Responses:** Structured responses with stable reason codes enable automated error handling and retry logic
6. **Execution Posture Explicitness:** Canonical-only vs provisional-allowed is explicit declaration, preventing accidental use of provisional state
7. **Audit Trail Completeness:** Echo of evaluated references enables full audit reconstruction

### Forbids

1. **Gateway Modifying, Enriching, or Completing Requests:** Gateway SHALL NOT infer, normalize, or repair missing fields
2. **Runtime Relying on Gateway to "Fix" Incomplete Bundles:** Runtime MUST provide complete context; Gateway assumes completeness
3. **Optimistic or Asynchronous Execution Before Gateway Decision:** Execution MUST block until Gateway returns ALLOW
4. **Ambiguous or Inconsistent Input Handling:** Missing or ambiguous fields MUST result in INDETERMINATE (fail-closed)
5. **Treating Missing Fields as "Optional" or Inferring Defaults:** All required fields MUST be present; no implicit defaults
6. **Gateway Trusting ADF Validation Blindly:** Gateway MUST verify all artifacts independently
7. **Execution with Unverified References:** All references MUST be resolved and verified before execution proceeds

## Blocker Resolution

This ADR fully or partially resolves the following blockers from the Spec Pressure Report:

- **3.1 Deterministic YAML Serialization** (Partially Resolved) - Context Bundle structure is normatively defined as execution eligibility request contract; serialization format (YAML vs JSON vs protobuf) remains implementation-specific as it does not affect contract correctness
- **3.2 Context Bundle Transmission Protocol** (Acknowledged as Undefined) - Transport protocol (HTTP, gRPC, MQ) is implementation-specific and does not affect contract correctness; contract is transport-agnostic
- **3.3 Gateway Model Invocation Payload Structure** (Fully Resolved) - Gateway forwards MVC as-is after verification; does not construct from scratch; eligibility metadata included unsigned for audit
- **2.4 Context Bundle TTL Enforcement** (Fully Resolved) - TTL is part of request contract (§9.1.5); Gateway MUST reject expired bundles with DENY decision and BUNDLE_EXPIRED reason code

**Note:** This ADR defines **what crosses component boundaries and who is responsible**. Transport protocols and serialization formats are implementation-specific and do not affect contract correctness as long as they preserve request/response structure and semantics.

## Implementation Notes

While this ADR does not define implementation mechanisms, implementers should note:

1. **Gateway Must Fail Closed on Incomplete Input:** Implementations must treat missing or ambiguous fields as INDETERMINATE (fail-closed), not attempt repair
2. **Runtime Must Construct Complete Bundles:** Runtime implementations must include all required fields; cannot rely on Gateway defaults or inference
3. **Reference Resolution is Gateway Responsibility:** Gateway must resolve all references from authoritative sources independently
4. **Stable Reason Codes Enable Retry Logic:** Implementations should use reason codes to determine retry strategy (e.g., UNRESOLVABLE_REFERENCE may be transient; SIGNATURE_INVALID is not)
5. **Execution Posture Must Be Explicit:** Runtime must explicitly declare canonical-only vs provisional-allowed; default is canonical-only for safety

## References

- Spec Pressure Report: Blockers 3.1, 3.2, 3.3, 2.4
- `specifications/ste-system.iso42010.md` §5.2.1 (Runtime Purpose and Scope)
- `specifications/ste-system.iso42010.md` §5.3.1 (Gateway Purpose and Scope)
- `specifications/ste-system.iso42010.md` §8.1 (Execution Eligibility Contract)
- `specifications/ste-system.iso42010.md` §8.2.1 (Synchronous Enforcement)
- `specifications/ste-system.iso42010.md` §9.1 (Context Bundle)
- `specifications/ste-system.iso42010.md` §9.2 (Gateway Handling of Context Bundles)
- ADR-019: Gateway Authority and Signing Model
- ADR-020: ORG-Level Signing Scope
- ADR-021: Gateway Trust Verification Model
- ADR-022: Fail-Closed Semantics and Enforcement Scope
- ADR-023: Validation Timing and Responsibility



