# Three-Level Architecture Model

## Overview

The ADR Architecture Kit supports a three-level architecture hierarchy for conversational architecture design:

1. **Logical ADRs (ADR-L-XXXX)**: Conceptual design - the "what" and "why"
2. **Physical-System ADRs (ADR-PS-XXXX)**: System view - the high-level "how"
3. **Physical-Component ADRs (ADR-PC-XXXX)**: Executable specifications - the complete "how"

## Architecture Levels

### Level 1: Logical ADRs (ADR-L-XXXX)

**Purpose**: Define capabilities, boundaries, contracts, and invariants without implementation details.

**Key Elements**:
- Capabilities (what the system must do)
- Architectural boundaries (separation of concerns)
- Interaction contracts (how components interact conceptually)
- Invariants (what must always be true)
- Non-functional requirements
- Decisions (architectural choices)

**Example**: ADR-L-0042 "User Management Capability"
- Capability: User authentication and authorization
- Boundaries: User service boundary
- Contracts: User API contract
- Invariants: "All user data must be encrypted at rest"

### Level 2: Physical-System ADRs (ADR-PS-XXXX)

**Purpose**: Define high-level system architecture with component topology and integration patterns.

**Key Elements**:
- System boundaries (what's inside/outside the system)
- Component topology (high-level component relationships)
- Integration patterns (how components integrate)
- Data flows (high-level data movement)
- Scalability strategy
- Failure modes

**Example**: ADR-PS-0012 "User Service System Architecture"
- Implements: ADR-L-0042
- Technology: Node.js, PostgreSQL, Redis
- Component Topology: API Gateway → User Service → Database
- Integration Patterns: REST API, Event-driven
- References Components: [ADR-PC-0023, ADR-PC-0024]

### Level 3: Physical-Component ADRs (ADR-PC-XXXX)

**Purpose**: Provide complete, executable specifications for autonomous code generation.

**Key Elements**:
- Generation context (AI prompt template)
- Complete interface specifications (OpenAPI, gRPC, etc.)
- Implementation requirements:
  - Algorithms (with specifications)
  - Error handling (complete strategy)
  - Observability (logging, metrics, tracing)
  - Testing requirements (coverage, test types)
  - Security requirements
  - Performance requirements
- Implementation identifiers (where code lives)
- Data architecture (schemas, migrations)

**Example**: ADR-PC-0023 "User Service API Component"
- Implements System: ADR-PS-0012
- Implements Logical: ADR-L-0042
- Component Spec: Express.js REST API
- Interfaces: Complete OpenAPI spec
- Implementation Identifiers: `module_path: src/services/user-service`
- Algorithms: Password hashing (bcrypt, cost 12), JWT generation
- Error Handling: RFC 7807 Problem Details
- Observability: Structured logging, Prometheus metrics, OpenTelemetry tracing
- Testing: >= 80% coverage, contract tests, performance tests

## Traceability Chain

```
Logical ADR (ADR-L-XXXX)
    ↓ implements_logical
Physical-System ADR (ADR-PS-XXXX)
    ↓ implements_system
Physical-Component ADR (ADR-PC-XXXX)
    ↓ generates
Production Code
```

## Conversational Architecture Workflow

### 1. Human Describes Intent
```
Human: "I need a user service with authentication"
```

### 2. Architecture Agent Creates Logical ADR
```
AI: "Creating ADR-L-0042: User Management Capability"
AI: "What authentication method?"
Human: "JWT with 1-hour expiry"
AI: "Recorded as DEC-0001"
```

### 3. Architecture Agent Creates Physical-System ADR
```
AI: "Creating ADR-PS-0012: User Service System Architecture"
AI: "Microservice or monolith?"
Human: "Microservice"
AI: "I recommend 3 components: API, Database, Cache"
Human: "Sounds good"
```

### 4. Specialist Watchdog Agent Fills Details
```
Watchdog: *detects ADR-PS-0012 created*
Watchdog: *extracts context signals: ["rest-api", "authentication", "microservice"]*
Watchdog: *activates rules: [REST-API-BEST-PRACTICES, JWT-AUTH-STANDARD]*
Watchdog: *infers technology_stack: Node.js, Express, PostgreSQL, Redis*
Watchdog: *updates ADR-PS-0012*
```

### 5. Architecture Agent Creates Physical-Component ADRs
```
AI: "Creating ADR-PC-0023: User API Component"
AI: "Rate limiting strategy?"
Human: "100 req/min per user"
AI: "Recorded. Generating complete specification..."
```

### 6. Specialist Watchdog Agent Completes Specification
```
Watchdog: *detects ADR-PC-0023 created*
Watchdog: *fills implementation_requirements from rules*
Watchdog: *adds error_handling: RFC 7807*
Watchdog: *adds observability: Prometheus metrics*
Watchdog: *adds testing_requirements: >= 80% coverage*
Watchdog: *validates completeness for code generation*
```

### 7. Ready for Implementation
```
AI: "ADR-PC-0023 is complete. Ready to implement?"
Human: "Implement"
AI: *reads ADR-PC-0023*
AI: *generates production-ready code*
```

## Composable Architecture

### Technology Migration Pattern

Physical-Component ADRs enable seamless technology migration:

```
ADR-PC-0023: User API (Node.js) ← Current
    ↓ supersedes
ADR-PC-0026: User API (Rust) ← New implementation
```

**Workflow**:
1. Human: "Migrate the API to Rust for performance"
2. AI reads ADR-PC-0023 to understand interface contracts
3. AI creates ADR-PC-0026 with **identical interfaces**
4. AI generates Rust code from ADR-PC-0026
5. Deploy: swap PC-0023 for PC-0026, zero downtime
6. History preserved: `supersedes` relationship in graph

### Polyglot Systems

Different components can use different technologies:
- ADR-PC-0023: Node.js API
- ADR-PC-0024: PostgreSQL Database
- ADR-PC-0025: Go Event Publisher
- ADR-PC-0027: Python ML Service

All specified with identical rigor, all composable through interface contracts.

## Granularity Guidelines

### Physical-System ADRs
- One per independently deployable system
- Typical: 1-3 systems per logical capability
- Example: "User Service System", "Payment Service System"

### Physical-Component ADRs
- One per independently deployable/testable unit
- Typical: 2-8 components per system
- Example: "User API Component", "User Database Component"

**Granularity Rules**:
- ✅ Good: Independently deployable units with distinct responsibilities
- ❌ Too fine: Individual functions or endpoints
- ❌ Too coarse: Entire system in one component

**AI Validation**: If proposing >10 Physical-Component ADRs for a single system, AI must justify granularity to human authority.

## Directory Structure

```
adrs/
├── logical/
│   └── ADR-L-XXXX-*.yaml
├── physical/                    # Legacy, still supported
│   └── ADR-P-XXXX-*.yaml
├── physical-system/             # New
│   └── ADR-PS-XXXX-*.yaml
└── physical-component/          # New
    └── ADR-PC-XXXX-*.yaml
```

## Schema Design Principles

### AI-First Design

Schemas are designed as **AI generation templates**, not human-written YAML:

1. **Generation Context**: Fields that prompt AI code generation
2. **Implementation Requirements**: Complete specifications for autonomous generation
3. **Conversation Metadata**: Captures decision history
4. **Inference Tolerance**: Certain fields can be inferred by Watchdog Agent

### Machine-Readable, Machine-Written, Human-Designed

- **Humans**: Describe intent conversationally
- **Architecture Agent**: Interviews and captures decisions
- **Specialist Watchdog Agent**: Infers technical details from context + rules
- **ADRs**: Machine-written, complete, executable specifications
- **Humans**: Review and refine, not write YAML

## Benefits

### 1. Clear Abstraction Levels
- Logical: Intent and capabilities
- System: Topology and patterns
- Component: Executable specifications

### 2. Semantic Clarity
- Type visible in ID alone (ADR-PS vs ADR-PC)
- Graph queries: "Show all system boundaries" vs "Find component implementations"

### 3. Composability
- Components are Lego blocks with well-defined interfaces
- Technology migrations through supersession
- Polyglot systems by design

### 4. AI Generation Readiness
- Physical-Component ADRs contain everything needed for code generation
- No additional human clarification required
- Watchdog Agent ensures completeness

### 5. Conversational Architecture
- Natural language interface
- AI interviews, not syntax
- Architecture emerges from dialogue

## Next Steps

- [Physical-System ADR Guide](physical-system-adr-guide.md) - How to write Physical-System ADRs
- [Physical-Component ADR Guide](physical-component-adr-guide.md) - How to write Physical-Component ADRs
- [Schema Guide](schema-guide.md) - Complete schema reference
