<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 5ec789f07e8bc8d7e767f1e2995e731c75c60ed8f0222263d8a220969906a20e
rendered_hash: 4a340bd95c69ddf17a413f507d3ec18668b6bd767061e7cd50a9693f0ef61f85
-->

# ADR-L-0006: Rule Library Sub-Module with Cooperative Signals

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0006  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-08  
**Modified:** 2026-03-08  
**Authors:** adr-architecture-kit  
**Domains:** governance, rules, signals, integration  
**Tags:** rule-library, cooperative-signals, submodule, mcp  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0006 |
| Status | accepted |
| Decisions | 5 |
| Capabilities | 4 |
| Invariants | 4 |


## Context

ADR-L-0004 defines a multi-tier governance architecture where a rule-library
sub-module activates and projects rules via MCP. The Rules & Signal Service
(Tier 2) parses ADRs and generates enforcement rules; the rule-library (Tier 3)
receives, activates, and serves those rules to consumers.

A proof-of-concept rules-library exists at _poc_rules-library with a three-layer
activation model, signal-driven rule selection, and submodule protocol. The POC
solves the "activation problem": rules exist but aren't applied consistently.

Separately, the prompt translator (ADR-L-0005) generates cooperative
signals for parallel AI agent coordination: claim, progress, complete,
wave_complete, validation_ready. These file-based signals enable agents to
coordinate without a server until the Rules & Signal Service is built.

## The Opportunity

The rule-library can serve as the **coordination hub** for file-based tooling:
- Define canonical signal schema (cooperative + context)
- Provide signal emission patterns for prompt translator
- Read/validate signals from agent workspaces
- Eventually receive rules from Rules & Signal Service

Building from POC principles allows:
1. Correct integration with STE ecosystem (adr-architecture-kit, ste-runtime)
2. Cooperative signals as first-class capability
3. Prompt translator integration (signal instructions in generated prompts)
4. Independent repo and submodule for reuse across projects

## Problems Solved

1. **Activation problem**: Rules exist but aren't applied (POC insight)
2. **Coordination gap**: Agents need signals to coordinate (prompt translator)
3. **Schema authority**: Who defines signal format? (rule-library)
4. **Integration**: Prompt translator, decorators, ste-runtime need shared hub
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0011 | Build from POC Principles | — |
| DEC-0018 | Cooperative Signals as First-Class | — |
| DEC-0025 | Prompt Translator Integration | — |
| DEC-0031 | Standalone Repo, Submodule Consumption | — |
| DEC-0034 | File-Based First, MCP Later | — |

### DEC-0011 — Build from POC Principles

**Rationale**

Build ste-rules-library from POC design principles.

Adopt from POC:
- Three-layer activation (context signals drive rule selection)
- Signal-driven projection (only relevant rules)
- Submodule protocol with bootstrap
- Meta-governance (ADRs govern rules, not self-governed)
- Conflict detection (escalate, never auto-resolve)

Adapt for STE:
- ADR-derived rules (from Rules & Signal Service when built)
- Cooperative signals (agent coordination)
- Integration with adr-architecture-kit decorators
- Integration with prompt translator

**Consequences**

Positive:
- New standalone rule-library repo
- Design doc: docs/RULE-LIBRARY-DESIGN.md

### DEC-0018 — Cooperative Signals as First-Class

**Rationale**

rule-library defines and supports cooperative signals alongside context
signals. Two signal semantics:

**Context signals** (from POC): Drive rule selection
- file_pattern, language, domain
- "What rules apply to this context?"

**Cooperative signals** (from prompt translator): Agent coordination
- claim, progress, complete, wave_complete, validation_ready
- "Who is doing what? When can I start?"

rule-library provides:
- Canonical signal schema (schema/signal.schema.json)
- Signal emission CLI for agents
- Signal read/validate for monitoring

**Consequences**

Positive:
- schema/signal.schema.json in rule-library
- scripts/emit-signal.py for agents
- File-based until MCP/RSS

### DEC-0025 — Prompt Translator Integration

**Rationale**

Prompt translator (adr-architecture-kit) generates implementation prompts
that include signal emission instructions. rule-library is the schema
authority for those instructions.

Flow:
1. rule-library defines signal.schema.json
2. Prompt translator templates reference schema
3. Generated prompts include "emit claim", "emit complete" instructions
4. Agents emit to .codex/signals/, .cursor/signals/
5. rule-library (or monitor) reads signals

This makes the prompt translator the "code generator" for cooperative
flow control until proper Rules & Signal Service exists.

**Consequences**

Positive:
- rule-library schema consumed by prompt translator
- prompt translator templates include signal instructions when implemented
- docs/COOPERATIVE-SIGNALS.md aligns with rule-library schema

### DEC-0031 — Standalone Repo, Submodule Consumption

**Rationale**

rule-library as standalone repo enables:
- Independent versioning
- Clean dependency boundary
- Submodule into adr-architecture-kit, ste-runtime, any STE project
- No monorepo coupling

Consumption:
- git submodule add <rule-library-url> rule-library
- python rule-library/scripts/bootstrap.py
- Project gets rule index, signal schema, integration snippet

**Consequences**

Positive:
- New GitHub/GitLab repo: rule-library
- Submodule protocol (adapted from POC ADR-008)
- Bootstrap generates project config

### DEC-0034 — File-Based First, MCP Later

**Rationale**

Phase 1: File-based rules and signals. No server. Works with existing
prompt translator, codex-implement.py, bootstrap prompts.

Phase 2: MCP server for rule projection. get_rules, emit_signal tools.
File-based remains fallback for offline/development.

This allows incremental adoption without blocking on infrastructure.

**Consequences**

Positive:
- No MCP required for initial use
- MCP is enhancement, not dependency
- Offline/air-gapped scenarios supported


## Capabilities

### CAP-0010 — Signal Schema Authority

rule-library defines canonical schema for context and cooperative signals.

### CAP-0011 — Signal Emission CLI

CLI for agents to emit cooperative signals without writing JSON manually.

### CAP-0012 — Rule Activation and Projection

Context signals drive rule selection; rules projected for consumption.

### CAP-0013 — Submodule Bootstrap

Bootstrap script for projects adding rule-library as submodule.




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0033 | rule-library MUST define canonical schema for cooperative signals | MUST / design | automated |
| INV-0034 | rule-library MUST support file-based rule and signal handling | MUST / design | automated |
| INV-0035 | rule-library MUST NOT self-govern; it is governed by ADRs | MUST / policy | manual |
| INV-0036 | Cooperative signal schema MUST include claim, progress, complete, wave_complete, validation_ready types | MUST / design | automated |

### INV-0033

**Statement**

rule-library MUST define canonical schema for cooperative signals

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Signal format must be authoritative. Prompt translator and agents
consume this schema. Single source of truth.

### INV-0034

**Statement**

rule-library MUST support file-based rule and signal handling

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Works without Rules & Signal Service or MCP. Enables development
and offline scenarios.

### INV-0035

**Statement**

rule-library MUST NOT self-govern; it is governed by ADRs

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** manual

**Rationale**

Meta-governance: rules can be wrong. ADRs (in consuming project or
rule-library itself) define correctness. Aligns with POC ADR-003.

### INV-0036

**Statement**

Cooperative signal schema MUST include claim, progress, complete,
wave_complete, validation_ready types

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

These types enable parallel agent coordination per docs/COOPERATIVE-SIGNALS.md.
Prompt translator generates instructions for these.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-L-0005](ADR-L-0005-adr-to-prompt-translation-for-ai-implementation.md)

**References**
- [ADR-L-0005](ADR-L-0005-adr-to-prompt-translation-for-ai-implementation.md)
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)




## Known Gaps

### GAP-0006: Prompt translator COMP-0009 (SignalGenerator) not implemented

**Context:** Classification: real gap. Prompt translator signal-emission integration is still not implemented in adr-architecture-kit.
**Impact:** medium
**Blocking:** false

### GAP-0007: Rules & Signal Service not built

**Context:** Classification: deferred gap. This remains a later workspace-level service, outside the current repo-local discovery implementation.
**Impact:** medium
**Blocking:** false


## Notes

Implementation order:

1. Create rule-library repo (standalone)
2. Add PROJECT.yaml, schema/signal.schema.json
3. Add scripts/emit-signal.py
4. Add bootstrap script
5. Add rule activation logic (file-based)
6. adr-architecture-kit: add rule-library submodule
7. Prompt translator: consume signal schema, generate instructions
8. MCP server (Phase 2)

POC reference: _poc_rules-library/ai-rules-library/ai-rules-library/
Design doc: docs/RULE-LIBRARY-DESIGN.md


---

*Generated from ADR-L-0006 by ADR Architecture Kit (projection v3)*