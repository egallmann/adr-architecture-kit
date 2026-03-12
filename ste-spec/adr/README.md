# Architectural Decision Records

## Purpose

This directory contains architectural ADRs that define the STE system-of-interest, authority boundaries, and execution semantics.

**Operational ADRs are intentionally excluded**. Additional decision records exist in the private working repository covering infrastructure, deployment, and runtime implementation. Those decisions are implementation-specific and subject to change without affecting the architectural specification.

**Included ADRs** define converged architectural commitments where alternatives have been explicitly rejected and reversal would be expensive or destabilizing.

## Decision Record Taxonomy

This repository distinguishes between two classes of decision records:

### ADR — Binding Architectural Decision

ADRs represent converged, long-term architectural commitments:

- Alternatives have been explicitly rejected
- Reversal is expensive or destabilizing
- Governs future work and enforcement behavior
- Architecturally binding on all components

### E-ADR — Exploratory Architectural Decision

E-ADRs are provisional execution mandates for learning:

- Explicitly reversible and expected to evolve
- Exists to force execution and generate pressure
- Surfaces friction, conflicts, and learning
- Operationally binding but architecturally non-binding
- Does NOT define system truth or correctness

**Important**: E-ADRs are not published in this specification. Only converged, binding ADRs are included.

## Included Architectural Decisions

The following 16 ADRs define architectural principles and boundaries for the STE system:

### Foundational Architectural Principles (3)

- **ADR-001**: Deterministic Extraction Over ML-Based Inference — Establishes foundational commitment to determinism over heuristics
- **ADR-006**: Explicit Unknowns Over Inference — Defines how the system handles uncertainty architecturally
- **ADR-008**: Correctness and Consistency Contract — Defines canonical state guarantees and truth model

### Canonical Identity and State (2)

- **ADR-007**: Slice Identity Strategy — Defines canonical identity model for architectural elements
- **ADR-009**: Assertion Precedence Model — Defines extraction vs assertion conflict surfacing policy

### STE Authority and Enforcement Model (8)

- **ADR-019**: Gateway Authority and Signing Model — Defines Gateway authority posture and responsibilities
- **ADR-020**: ORG-Level Signing Scope — Defines what requires ORG signing vs ephemeral outcomes
- **ADR-021**: Gateway Trust Verification Model — Defines trust verification semantics and fail-closed behavior
- **ADR-022**: Fail-Closed Enforcement Scope — Defines fail-closed triggers and bypass prohibition
- **ADR-023**: Validation Timing and Responsibility — Defines validation authority across lifecycle stages
- **ADR-024**: Cross-Component Contracts — Defines Gateway pure validator posture and request/response contracts
- **ADR-025**: Environment Semantics — Defines environment as canonical dimension with exact-match semantics
- **ADR-026**: Invariant Conflict Detection Semantics — Defines conflict detection authority and attestation schema
- **ADR-027**: Scope Semantics and Versioning — Defines scope as canonical dimension with versioned matching

### System Architecture and Authority Boundaries (2)

- **ADR-028**: AI-DOC Fabric and Gateway Authority Boundaries — Defines Fabric-Gateway-Runtime authority separation
- **ADR-029**: Gateway Enforcement Authority — Defines Gateway enforcement model and cryptographic trust

## Exclusion Rationale

ADRs focused on the following are not included in this published specification:

- Infrastructure technology choices (ECS vs Lambda, DynamoDB vs RDS, SNS vs EventBridge, ALB vs API Gateway)
- Deployment topology and network architecture
- Runtime component contracts and service boundaries
- Operational optimization strategies
- Implementation-specific patterns

These operational decisions exist in the working repository and may change without affecting the architectural specification.

## ADR Format

Each ADR follows this structure:

```markdown
# ADR-NNN: Decision Title

## Status

[Proposed | Accepted | Superseded | Deprecated]

## Context

Background and problem statement

## Decision

The architectural choice made

## Consequences

Positive and negative implications
```

## Relationship to Working Repository

This is a curated subset of the complete ADR corpus. The full set of decision records, including operational ADRs and exploratory E-ADRs, remains in the private working repository and informs implementation without defining architectural truth.

