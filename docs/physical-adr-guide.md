# Physical ADR Guide

## Purpose

Physical ADRs document **implementation specifications** that operationalize logical designs. They define how the system is built, what technologies are used, and how components interact.

## When to Use Physical ADRs

Use physical ADRs to document:

- **Technology stack** - Languages, frameworks, libraries, databases
- **Architecture patterns** - Microservices, event-driven, layered
- **Component specifications** - Services, databases, queues with interfaces
- **Deployment model** - Hosting, orchestration, scaling
- **Data architecture** - Entities, storage, schemas, access patterns
- **Integration points** - System-to-system communication
- **Operational requirements** - Monitoring, logging, backup, security

## What to Include

Physical ADRs must be **implementation-ready**:

- Complete enough for AI or human implementation
- Explicit technology choices with versions
- Component specifications with interfaces
- Implementation identifiers (service names, repositories, module paths)
- Gaps explicitly tracked (blocking vs non-blocking)

## Structure

### Required Fields

```yaml
schema_version: "1.0"
adr_type: physical
id: ADR-P-0001
title: "Implementation title"
status: proposed | accepted | deprecated | superseded
created_date: "2026-03-07"
authors: ["github.handle"]
domains: ["implementation", "tooling"]

implements_logical: ["ADR-L-0001"]  # Must reference at least one logical ADR
technologies: ["python", "postgresql", "kubernetes"]

context: |
  Implementation context and technology choices

technology_stack:
  - category: language
    name: "Python"
    version: "3.10+"
    rationale: "Why this technology"

component_specifications:
  - id: COMP-0001
    name: "Component name"
    type: service
    responsibilities: "What this component does"
```

### Optional Sections

- `architecture_patterns` - Patterns applied
- `deployment_model` - Hosting and orchestration
- `data_architecture` - Data storage and access
- `implementation_decisions` - Implementation-level choices
- `integration_points` - System integrations
- `operational_requirements` - Monitoring, logging, security
- `gaps` - Unresolved implementation details

## Example: Minimal Physical ADR

```yaml
schema_version: "1.0"
adr_type: physical
id: ADR-P-0042
title: "Kong API Gateway Implementation"
status: accepted
created_date: "2026-03-07"
authors: ["alice.smith"]
domains: ["api", "infrastructure"]

implements_logical: ["ADR-L-0042"]
technologies: ["kong", "kubernetes", "postgresql"]

context: |
  Implement API gateway using Kong Gateway on Kubernetes.

technology_stack:
  - category: infrastructure
    name: "Kong Gateway"
    version: "3.x"
    rationale: |
      Open-source API gateway with plugin ecosystem. Kubernetes-native.
      Supports authentication, rate limiting, logging.

component_specifications:
  - id: COMP-0001
    name: "Kong Gateway"
    type: gateway
    responsibilities: |
      Route external traffic to internal services. Enforce authentication.
      Apply rate limiting. Log all requests.
    interfaces:
      - id: IFACE-0001
        type: REST
        specification: |
          External: HTTPS on port 443
          Internal: HTTP to backend services
    implementation_identifiers:
      service_name: "kong-gateway"
      repository: "github.com/org/infrastructure"
      deployment_name: "kong-gateway"
```

## Example: Complete Physical ADR

See `adrs/physical/ADR-P-0001-python-toolkit-implementation.yaml` for a complete example with:
- Multiple technology choices
- Architecture patterns
- Component specifications with interfaces
- Implementation decisions with alternatives
- Integration points

## Implementation Identifiers

Physical ADRs include identifiers for:

- **EDR matching** - Compare declared vs. actual architecture
- **Correction agents** - Locate code to modify
- **Blast radius analysis** - Understand dependencies

```yaml
component_specifications:
  - id: COMP-0001
    name: "Payment Service"
    implementation_identifiers:
      service_name: "payment-service"      # Kubernetes service name
      repository: "github.com/org/payments"  # Source control
      module_path: "src/services/payment"    # Code location
      deployment_name: "payment-service"     # Deployment identifier
```

## Validation

Physical ADRs are validated against:

1. **JSON Schema** - Structural validation
2. **ID pattern** - Must match `ADR-P-\d{4}`
3. **Logical reference** - Must reference at least one logical ADR (INV-0003)
4. **Required fields** - schema_version, adr_type, id, title, status, created_date, authors, domains, implements_logical, technologies, context, technology_stack, component_specifications

## Best Practices

### 1. Reference Logical ADRs

Every physical ADR must implement at least one logical ADR:

```yaml
implements_logical: ["ADR-L-0042"]
```

This creates traceability from implementation to intent.

### 2. Specify Complete Technology Stack

Include versions and rationale:

```yaml
technology_stack:
  - category: database
    name: "PostgreSQL"
    version: "15.x"
    rationale: |
      Relational data model. ACID transactions. Wide adoption.
      Excellent Python support (psycopg3).
```

### 3. Define Component Interfaces

```yaml
component_specifications:
  - id: COMP-0001
    name: "User Service"
    interfaces:
      - id: IFACE-0001
        type: REST
        specification: |
          GET /api/v1/users/{id}
          POST /api/v1/users
          
          See OpenAPI spec: docs/api/users.yaml
```

### 4. Track Implementation Gaps

```yaml
gaps:
  - id: GAP-0001
    question: "Which PostgreSQL connection pooler?"
    impact: medium
    blocking: false
    options:
      - name: "PgBouncer"
        pros: ["Lightweight", "Battle-tested"]
        cons: ["Limited features"]
      - name: "Pgpool-II"
        pros: ["Load balancing", "Query caching"]
        cons: ["More complex"]
```

### 5. Document Implementation Decisions

```yaml
implementation_decisions:
  - id: IMPL-0001
    summary: "Use FastAPI for REST API framework"
    rationale: |
      Modern async support. Automatic OpenAPI generation. Type hints.
      Excellent performance. Wide adoption.
    implements_invariants: ["INV-0001"]
    alternatives_considered:
      - name: "Flask"
        rejected_because: "No native async support. Manual OpenAPI."
      - name: "Django"
        rejected_because: "Too heavyweight for microservice."
```

## Relationship to Logical ADRs

```
ADR-L-0042: API Gateway Pattern (logical)
    ↓ implemented by
ADR-P-0042: Kong Gateway Implementation (physical)
    ↓ realized by
Kubernetes deployment + Kong config (code/infra)
```

Physical ADRs bridge intent and implementation.

## STE Compliance

Physical ADRs comply with:

- **PRIME-1**: No implicit assumptions (technology choices explicit)
- **PRIME-2**: No undeclared state (all metadata in frontmatter)
- **SYS-5**: Documentation-state precedence (ADRs precede implementation)
- **INV-0003**: Must reference logical ADRs (traceability)

## Validation Checklist

Before committing a physical ADR:

- [ ] ID matches pattern `ADR-P-\d{4}`
- [ ] References at least one logical ADR
- [ ] Technology stack includes versions and rationale
- [ ] Component specifications are complete
- [ ] Implementation identifiers present (for EDR matching)
- [ ] Gaps explicitly tracked (if any)
- [ ] Passes JSON Schema validation
- [ ] Passes pytest test suite

## Further Reading

- `docs/logical-adr-guide.md` - Writing logical ADRs
- `docs/schema-guide.md` - Complete schema reference
- `adrs/physical/ADR-P-0001.yaml` - Reference implementation
