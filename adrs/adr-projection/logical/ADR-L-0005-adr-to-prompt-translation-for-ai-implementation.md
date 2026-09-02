<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: fc0af7c0351cdcbbe95bd516e5eaae4318c73ad22bbfd3a2de4fd3c7f61f30b2
rendered_hash: 9a195159ae2fac358bbf27d9d8a39904d209a83dd99dd3f3cd1c1031374a64c8
-->

# ADR-L-0005: ADR-to-Prompt Translation for AI Implementation

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0005  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-08  
**Modified:** 2026-03-08  
**Authors:** adr-architecture-kit  
**Domains:** adr, automation, ai-tooling, code-generation  
**Tags:** prompt-engineering, adr, automation, ai-agents, code-generation, llm  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0005 |
| Status | accepted |
| Decisions | 4 |
| Capabilities | 5 |
| Invariants | 6 |
| Boundaries | 1 |
| Interaction contracts | 3 |


## Context

The ADR Architecture Kit encodes architectural decisions in machine-readable YAML
format with explicit invariants, capabilities, and component specifications. These
structured ADRs contain all the information needed to guide AI implementation:

- **Invariants** define constraints (MUST/SHOULD/MAY enforcement levels)
- **Capabilities** define acceptance criteria
- **Component specifications** define interfaces, methods, parameters
- **Implementation decisions** define technology choices and patterns
- **Testing requirements** define verification strategy

Currently, translating ADRs into implementation prompts for AI agents (CODEX, Cursor,
etc.) is a manual process. A human reads the ADR and crafts prompts that capture
the constraints and specifications.

This manual translation has several problems:
1. **Inconsistent**: Different humans extract different information
2. **Incomplete**: Easy to miss invariants or requirements
3. **Time-consuming**: Requires careful reading and synthesis
4. **Error-prone**: Constraints may be misinterpreted
5. **Not scalable**: Doesn't scale to 100+ ADRs

Since ADRs are machine-readable, we can **automate prompt generation** from ADR
specifications. This creates a direct pipeline:

```
ADR (machine-readable spec)
    ↓ parse
Prompt Translator
    ↓ generate
Implementation Prompt (for AI agent)
    ↓ execute
AI Implementation
    ↓ validate
Validation (against original ADR)
```

This aligns with STE principles:
- **SYS-2 (Deterministic Cognition)**: Prompts generated deterministically from ADRs
- **PRIME-1 (No Implicit Assumptions)**: All constraints explicit in prompt
- **SYS-4 (Drift Prevention)**: Prompts always match current ADR state

The prompt translator becomes a **code generator for AI instructions**, ensuring
AI agents receive complete, accurate specifications.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0010 | Create ADR-to-Prompt Translator | — |
| DEC-0017 | Generate Prompts Per Component | — |
| DEC-0024 | Include Validation Criteria in Prompts | — |
| DEC-0030 | Support Multiple Target Agents | — |

### DEC-0010 — Create ADR-to-Prompt Translator

**Rationale**

Automate the generation of implementation prompts from ADR specifications
to ensure consistency, completeness, and scalability.

Benefits:
- **Consistency**: Same ADR always generates same prompt structure
- **Completeness**: All invariants, capabilities, and specs included
- **Traceability**: Prompt explicitly references source ADR
- **Maintainability**: Update ADR → regenerate prompt automatically
- **Scalability**: Works for any number of ADRs
- **Quality**: Reduces human error in translation

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Manual prompt crafting | Not scalable, error-prone |
| Template-based generation | Less flexible, hard to maintain |
| LLM-based translation | Non-deterministic, requires validation |

**Consequences**

Positive:
- Prompts are generated, not hand-crafted
- ADR changes automatically propagate to prompts
- AI agents receive consistent, complete specifications
- Reduces cognitive load on architects
- Enables automated implementation pipelines

### DEC-0017 — Generate Prompts Per Component

**Rationale**

Physical ADRs contain multiple component specifications (COMP-*). Each
component should have its own implementation prompt to enable:
- Focused implementation (one component at a time)
- Parallel implementation (multiple agents)
- Incremental validation (per component)
- Clear scope boundaries

**Consequences**

Positive:
- One Physical ADR → Multiple prompts (one per component)
- Prompts reference parent ADR for context
- Prompts can be executed independently or sequentially

### DEC-0024 — Include Validation Criteria in Prompts

**Rationale**

Each prompt should include explicit validation criteria so the implementing
agent knows when it's done and how to verify correctness. This enables
self-validation and reduces iteration cycles.

**Consequences**

Positive:
- Prompts are self-contained with success criteria
- AI agents can self-validate before handoff
- Reduces back-and-forth between design and implementation

### DEC-0030 — Support Multiple Target Agents

**Rationale**

Different AI agents (CODEX, Cursor, Claude, GPT) have different capabilities
and prompt formats. The translator should support generating prompts optimized
for specific target agents.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Single universal prompt | May not leverage agent-specific features |
| Manual per-agent prompts | Not scalable |

**Consequences**

Positive:
- Translator has agent-specific formatters
- Can optimize for agent strengths
- Maintains core content consistency across formats


## Capabilities

### CAP-0031 — Parse Physical ADR Components

Parse Physical ADRs to extract component specifications, including:
- Component ID, name, type, description
- Responsibilities
- Interface definitions (methods, parameters, types)
- Implementation identifiers (file paths)
- Dependencies
- Testing requirements

**Acceptance criteria**
- Extracts all COMP-* sections from Physical ADR
- Parses interface definitions into structured data
- Validates component specification completeness
- Returns structured component metadata

### CAP-0032 — Generate Implementation Prompt

Generate implementation prompt for a specific component that includes:
- Context (what is being built and why)
- Constraints (invariants to enforce)
- Specifications (what to build)
- Test requirements (what to verify)
- Implementation strategy (how to build)
- Validation criteria (how to verify correctness)

**Acceptance criteria**
- Prompt includes all relevant invariants
- Prompt includes complete component spec
- Prompt includes test requirements
- Prompt references source ADR
- Prompt is self-contained and executable

### CAP-0033 — Generate Validation Checklist

Generate validation checklist for verifying implementation against ADR,
including checks for:
- Code structure (files, classes, methods exist)
- Invariant enforcement (constraints are enforced)
- Test coverage (all required tests exist)
- Integration testing (works in real environment)
- Documentation (docstrings, type hints)

**Acceptance criteria**
- Checklist covers all invariants
- Checklist covers all capabilities
- Checklist covers all components
- Checklist is actionable (clear pass/fail)

### CAP-0008 — Multi-Agent Prompt Generation

Generate prompts for multiple components that can be executed in parallel
by different AI agents, with clear dependency ordering

**Acceptance criteria**
- Identifies component dependencies
- Generates execution order
- Prompts can be executed independently
- Dependency information included

### CAP-0009 — Prompt Format Adaptation

Adapt prompt format for different target AI agents (CODEX, Cursor, Claude, GPT)
while maintaining core content consistency

**Acceptance criteria**
- Supports multiple target formats
- Core content identical across formats
- Format optimized for target agent
- Easy to add new formats


## Architectural Boundaries

### BOUND-0004 — Prompt Translator

**Boundary**

Translates ADRs into implementation prompts

**Why this boundary exists**

Separates ADR parsing from prompt generation for single responsibility.


## Interaction Contracts

### CONTRACT-0004

**Parties:** ADR Parser, Prompt Generator

**Protocol:** Structured component data transfer

**Guarantees**

Parser extracts component specifications.
Parser validates ADR completeness.
Generator receives validated component data.
Generator produces structured prompt.

### CONTRACT-0005

**Parties:** Prompt Generator, AI Agent

**Protocol:** Self-contained prompt delivery

**Guarantees**

Prompt is self-contained (no external references needed).
Prompt includes validation criteria.
Prompt references source ADR for traceability.
Agent can execute prompt independently.

### CONTRACT-0003

**Parties:** AI Implementation, Validator

**Protocol:** Checklist-based validation

**Guarantees**

Validator uses generated checklist.
Validator verifies against ADR invariants.
Validator reports compliance status.
- Validator references specific ADR sections


## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0046 | Generated prompts MUST include all invariants from the source ADR with their enforcement levels (must/should/may) | MUST / design | automated |
| INV-0047 | Generated prompts MUST include component specifications with complete interface definitions (methods, parameters,… | MUST / design | automated |
| INV-0048 | Generated prompts MUST reference the source ADR ID and specific sections (invariant IDs, component IDs) for traceability | MUST / design | automated |
| INV-0049 | Generated prompts MUST include test requirements from the ADR | MUST / design | automated |
| INV-0050 | Generated prompts SHOULD include implementation strategy guidance (e.g., TDD cycle, dependency injection patterns) | SHOULD / design | automated |
| INV-0051 | Prompt generator MUST be deterministic - same ADR input always produces same prompt output | MUST / design | automated |

### INV-0046

**Statement**

Generated prompts MUST include all invariants from the source ADR with
their enforcement levels (must/should/may)

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Invariants are architectural constraints that MUST be enforced in implementation.
Missing invariants in prompts leads to non-compliant code.

### INV-0047

**Statement**

Generated prompts MUST include component specifications with complete
interface definitions (methods, parameters, return types)

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Component specs define what to build. Incomplete specs lead to incorrect
implementations that don't match the architecture.

### INV-0048

**Statement**

Generated prompts MUST reference the source ADR ID and specific sections
(invariant IDs, component IDs) for traceability

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Traceability enables validation of implementation against original ADR
and helps AI agents understand authority chain.

### INV-0049

**Statement**

Generated prompts MUST include test requirements from the ADR

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Tests are part of the specification. Per ADR-L-0003, TDD methodology
requires tests to be specified before implementation.

### INV-0050

**Statement**

Generated prompts SHOULD include implementation strategy guidance
(e.g., TDD cycle, dependency injection patterns)

**Scope:** global

**Enforcement:** SHOULD (design)
**Verification:** automated

**Rationale**

Implementation patterns help AI agents produce consistent, high-quality
code that follows project conventions.

### INV-0051

**Statement**

Prompt generator MUST be deterministic - same ADR input always produces
same prompt output

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Non-deterministic generation violates SYS-2 (Deterministic Cognition).
Prompts must be reproducible for validation and debugging.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0003](ADR-L-0003-quality-assurance-and-testing-strategy.md)
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)
- [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md)

**References**
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-L-0003](ADR-L-0003-quality-assurance-and-testing-strategy.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)
- [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md)
- [ADR-L-0006](ADR-L-0006-rule-library-sub-module-with-cooperative-signals.md)




## Known Gaps

### GAP-0002: Prompt template design needed

**Context:** Classification: real gap. Prompt generation exists architecturally, but the production prompt-template set is not implemented in this repo yet.
**Impact:** medium
**Blocking:** false

### GAP-0003: Agent-specific formatters need definition

**Context:** Classification: deferred gap. Core prompt generation can proceed before per-agent optimizations are added.
**Impact:** medium
**Blocking:** false

### GAP-0004: Integration with CI/CD for automated implementation

**Context:** Classification: deferred gap. This is downstream workflow automation, not a blocker for the architecture-index subsystem.
**Impact:** medium
**Blocking:** false


## Notes

This capability transforms ADRs from passive documentation into **active
specifications** that directly drive AI implementation.

The prompt translator is itself a component that should be:
- Specified in permanent physical-component ADR authority (ADR-PC-*)
- Implemented following TDD methodology (ADR-L-0003)
- Annotated with decorators (ADR-L-0004)
- Tested comprehensively

Future enhancement: Integrate with Rules & Signal Service to generate
enforcement rules alongside implementation prompts, creating a complete
"specification → implementation → verification" pipeline.

Example workflow:
```bash
# Generate prompts from Physical ADR
adr generate-prompts ADR-PC-0008 --target codex --output prompts/

# Generates:
# - prompts/COMP-0001-scope-resolver.md
# - prompts/COMP-0002-manifest-generator.md
# - prompts/COMP-0003-validator.md
# - prompts/COMP-0004-cli.md
# - prompts/validation-checklist.md

# Hand to CODEX for implementation
# CODEX implements following prompts

# Validate implementation
adr validate-implementation ADR-PC-0008 --checklist prompts/validation-checklist.md
```

This creates a **closed-loop system** where ADRs drive implementation and
validation automatically.


---

*Generated from ADR-L-0005 by ADR Architecture Kit (projection v3)*