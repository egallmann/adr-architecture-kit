# Rule Library Design

**Date**: 2026-03-08  
**Authority**: ADR-L-0004, STE Governance Architecture  
**Purpose**: Design ste-rules-library from POC principles, with cooperative signals

---

## Assessment

Building ste-rules-library from POC principles, extended with cooperative signals, is a sound approach.

### Design Approach

1. **POC structure differs** - POC has different layout than STE ecosystem
2. **Authority model** - POC Layer 1/2/3 maps to STE Tiers 1-4 with ADR-derived rules
3. **Signal semantics** - POC: context signals; STE adds cooperative signals (claim, progress, wave_complete)
4. **Integration** - Must work with adr-architecture-kit, ste-runtime, prompt translator

### What to Adopt from POC

| POC Concept | Adopt? | STE Adaptation |
|-------------|--------|----------------|
| Three-layer activation | Yes | Map to STE Tiers 1-4 |
| Signal-driven rule selection | Yes | Add cooperative signals |
| Rule index + projection | Yes | ADR-derived rules, not manual |
| Submodule protocol | Yes | Git submodule, bootstrap |
| Rule schema (YAML frontmatter) | Yes | Extend for ADR traceability |
| Conflict detection (escalate) | Yes | No auto-resolve |
| Meta-governance (ADRs > rules) | Yes | ADR-L-0004 already defines |
| .mdc / index.rule.mdc | Evaluate | May use .yaml for STE consistency |

### What to Add (STE-Specific)

| Capability | Source | Purpose |
|------------|--------|---------|
| Cooperative signals | Prompt translator, ADR-P-0004 | Agent coordination (claim, progress, wave_complete) |
| ADR-derived rules | Rules & Signal Service (future) | Rules from invariants, not manual |
| File-based signal hub | docs/COOPERATIVE-SIGNALS.md | Until RSS built, ste-rules-library reads/writes signals |
| Prompt translator integration | ADR-P-0004 | ste-rules-library provides signal schema for prompts |
| Decorator validation | ADR-L-0004 | validate_decorator, check_traceability |

---

## Architecture: Rule Library in STE Ecosystem

```
                    STE Ecosystem
                    =============

adr-architecture-kit          ste-runtime
(ADRs, decorators,            (RECON, MCP)
 prompt translator)
        |                            |
        | ADR-derived rules         | semantic graph
        v                            v
        +--------+  +----------------+
        |        |  |                |
        v        v  v                v
   +------------------------------------------+
   |         ste-rules-library (sub-module)   |
   |                                          |
   |  - Rule activation (context signals)     |
   |  - Cooperative signals (agent coord)     |
   |  - MCP: get_rules, emit_signal           |
   |  - File-based fallback                   |
   +------------------------------------------+
        |                |                |
        v                v                v
   Cursor/CODEX     ste-runtime      Other consumers
   (via prompts)    (via MCP)       (via submodule)
```

---

## Cooperative Signals Integration

### Signal Types (Two Categories)

**1. Context Signals** (rule selection)
- `file_pattern`: `**/*.py`, `**/adrs/**`
- `language`: `python`, `typescript`
- `domain`: `security`, `scope-resolution`, `traceability`

**2. Cooperative Signals** (agent coordination)
- `claim`: Agent claims component
- `progress`: Agent reports status
- `complete`: Component done
- `wave_complete`: Wave finished
- `validation_ready`: Ready for validator

### ste-rules-library Role

**Phase 1 (Now)**: File-based cooperative signals
- ste-rules-library **defines** signal schema (authoritative)
- ste-rules-library **reads** signals from `.codex/signals/`, `.cursor/signals/`
- Prompt translator **generates** signal instructions from schema
- Agents **emit** signals per prompt instructions

**Phase 2 (RSS built)**: ste-rules-library receives rules from RSS
- RSS parses ADRs, generates rules
- RSS publishes to ste-rules-library
- ste-rules-library activates and projects

**Phase 3 (Full)**: ste-rules-library emits/consumes via MCP
- `emit_signal(signal_type, metadata)` - MCP tool
- `read_signals(adr_id, component_id)` - MCP tool
- File-based remains fallback for offline

---

## Design Decisions for Logical ADR

### DEC-1: Build from POC Principles

Adopt POC design principles (three-layer activation, signal-driven selection, meta-governance). Build for STE ecosystem integration.

### DEC-2: Cooperative Signals as First-Class

ste-rules-library defines and supports cooperative signals (claim, progress, complete, wave_complete, validation_ready) alongside context signals. File-based until RSS/MCP.

### DEC-3: Prompt Translator Integration

ste-rules-library provides signal schema and emission patterns. Prompt translator (adr-architecture-kit) generates signal instructions in prompts from this schema.

### DEC-4: Dual Signal Semantics

- **Context signals**: Drive rule selection (what rules apply)
- **Cooperative signals**: Drive agent coordination (who does what, when)

Both are "signals" but different purposes. ste-rules-library handles both.

### DEC-5: File-Based First, MCP Later

Phase 1: File-based rules and signals. No server required. Works with existing prompt translator, codex-implement.py, bootstrap prompts.

Phase 2: MCP server for rule projection. File-based remains fallback.

### DEC-6: Submodule Consumption

ste-rules-library consumed as Git submodule. Bootstrap script generates project config. Compatible with POC ADR-008 protocol (adapted for STE).

---

## Summary

**Sound approach**: Yes. Build from POC principles, extended with cooperative signals.

**Key integration**: ste-rules-library provides signal schema; prompt translator generates signal instructions; agents emit; ste-rules-library (or monitor) consumes.
