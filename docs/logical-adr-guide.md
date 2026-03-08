# Logical ADR Guide

## Purpose

Logical ADRs document **conceptual architecture decisions** without implementation details. They define what the system should do, not how it does it.

## When to Use Logical ADRs

Use logical ADRs to document:

- **Capabilities** - What the system must be able to do
- **Architectural boundaries** - Separation of concerns, module boundaries
- **Interaction contracts** - Agreements between components
- **Constraints** - Technical, business, regulatory, performance limits
- **Invariants** - What must always be true
- **Non-functional requirements** - Performance, security, scalability goals

## What to Exclude

Logical ADRs must NOT contain:

- Technology choices (Python, PostgreSQL, Kubernetes)
- Implementation patterns (microservices, event-driven)
- Component specifications (services, databases, queues)
- Deployment details (cloud provider, orchestration)
- Operational procedures (monitoring, logging)

These belong in Physical ADRs.

## Structure

### Required Fields

```yaml
schema_version: "1.0"
adr_type: logical
id: ADR-L-0001
title: "Human-readable title"
status: proposed | accepted | deprecated | superseded
created_date: "2026-03-07"
authors: ["github.handle"]
domains: ["api", "infrastructure"]

context: |
  Problem space, business drivers, constraints (markdown)

decisions:
  - id: DEC-0001
    summary: "Decision statement"
    rationale: |
      Why this decision was made
```

### Optional Sections

- `capabilities` - System capabilities
- `architectural_boundaries` - Boundaries and separation
- `interaction_contracts` - Component contracts
- `constraints` - Constraints that shape architecture
- `invariants` - What must always be true
- `non_functional_requirements` - NFRs
- `gaps` - Unresolved questions

### Metadata Fields

- `domains` - Architectural domains (for discovery)
- `tags` - Cross-domain tags
- `related_adrs` - Related ADRs
- `supersedes` - ADRs this supersedes
- `ownership` - Architecture authority and implementation owners

## Example: Minimal Logical ADR

```yaml
schema_version: "1.0"
adr_type: logical
id: ADR-L-0042
title: "API Gateway Pattern for External Traffic"
status: accepted
created_date: "2026-03-07"
authors: ["alice.smith"]
domains: ["api", "security"]
tags: ["gateway", "authentication"]

context: |
  All external traffic must pass through a single entry point for:
  - Authentication and authorization
  - Rate limiting and throttling
  - Request logging and monitoring
  - API versioning and routing

decisions:
  - id: DEC-0001
    summary: "All external traffic must route through API gateway"
    rationale: |
      Centralized control point for security, monitoring, and routing.
      Prevents direct access to internal services.
    alternatives_considered:
      - name: "Direct service access"
        rejected_because: |
          No centralized security. Difficult to monitor. No rate limiting.
    consequences:
      positive:
        - "Centralized security enforcement"
        - "Unified monitoring and logging"
        - "Rate limiting at gateway"
      negative:
        - "Single point of failure (mitigated by HA)"
        - "Additional latency (minimal)"

invariants:
  - id: INV-0042
    statement: "All external traffic must pass through API gateway"
    scope: global
    enforcement_level: must
    enforcement_mechanism: design
    verification_method: automated
    rationale: |
      Security requirement. No direct service access from internet.
```

## Example: Complete Logical ADR

See `adrs/logical/ADR-L-0001-ste-compliant-adr-system.yaml` for a complete example with:
- Multiple capabilities
- Architectural boundaries
- Interaction contracts
- Constraints
- Invariants
- Non-functional requirements
- Multiple decisions with alternatives

## Validation

Logical ADRs are validated against:

1. **JSON Schema** - Structural validation
2. **ID pattern** - Must match `ADR-L-\d{4}`
3. **No implementation details** - Manual review (INV-0002)
4. **Required fields** - schema_version, adr_type, id, title, status, created_date, authors, domains, context, decisions

## Best Practices

### 1. Focus on Intent, Not Implementation

**Good:**
```yaml
decisions:
  - id: DEC-0001
    summary: "User data must be encrypted at rest"
    rationale: "Regulatory compliance (GDPR, SOC2)"
```

**Bad:**
```yaml
decisions:
  - id: DEC-0001
    summary: "Use AWS KMS for encryption"  # Too specific!
    rationale: "Encrypt data with AES-256"  # Implementation detail!
```

### 2. Define Clear Boundaries

```yaml
architectural_boundaries:
  - id: BOUND-0001
    name: "API Layer vs Business Logic"
    description: |
      API layer handles HTTP concerns only. Business logic is separate.
    rationale: |
      Enables testing business logic without HTTP. Supports multiple
      API protocols (REST, gRPC) for same business logic.
```

### 3. Make Invariants Explicit

```yaml
invariants:
  - id: INV-0001
    statement: "All user data must be encrypted at rest"
    scope: global
    enforcement_level: must
    enforcement_mechanism: design
    verification_method: automated
    rationale: "Regulatory compliance requirement"
```

### 4. Track Gaps Explicitly

```yaml
gaps:
  - id: GAP-0001
    question: "How do we handle multi-tenancy?"
    impact: high
    blocking: true
    decision_required_from: "Architecture team"
```

## Relationship to Physical ADRs

Logical ADRs define **what** and **why**.  
Physical ADRs define **how** and reference logical ADRs via `implements_logical`.

```
Logical ADR (intent)
    ↓ implemented by
Physical ADR (specification)
    ↓ realized by
Code/Infrastructure (embodiment)
```

## STE Compliance

Logical ADRs comply with:

- **PRIME-1**: No implicit assumptions (all architecture explicit)
- **PRIME-2**: No undeclared state (all metadata in frontmatter)
- **SYS-5**: Documentation-state precedence (ADRs precede implementation)
- **SYS-13**: Graph completeness (explicit relationships)

## Further Reading

- `docs/physical-adr-guide.md` - Writing physical ADRs
- `docs/schema-guide.md` - Complete schema reference
- `adrs/logical/ADR-L-0001.yaml` - Reference implementation
