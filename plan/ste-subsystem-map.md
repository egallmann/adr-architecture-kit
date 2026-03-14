# STE Subsystem Map

## Purpose

This document identifies the repositories (subsystems) that comprise the STE
ecosystem, derived from the ADR-V vision documents, the /plan design artifacts,
the ROADMAP, and the existing codebase. It defines build order based on
dependency analysis.

---

## 1. Source Evidence

### From ADR-V Vision Documents (14 ADRs, all status: proposed)

| ADR | Capability | Subsystem Implication |
|---|---|---|
| ADR-V-0001 | Conversational Architecture System | Compiler (conversation → ADR → compiled model) |
| ADR-V-0002 | Agent Tier System | Runtime (tiered agent execution: rule-based, local LLM, foundation) |
| ADR-V-0003 | Meta-Optimization System | Runtime (self-improvement loop over agent performance) |
| ADR-V-0004 | Bidirectional Translation Layer | Compiler (ADR ↔ prompt translation) |
| ADR-V-0005 | Policy Lifecycle Management | Rules (capture → certify → apply → maintain) |
| ADR-V-0006 | Autonomous Compliance System | Runtime (ADR vs EDR validation, code vs invariants) |
| ADR-V-0007 | Compliance AI Agent | Runtime (detect → analyze → propose → implement → validate) |
| ADR-V-0008 | Provider Ecosystem | Runtime (external provider integration, proposal portal) |
| ADR-V-0009 | Proposal Security System | Runtime (PKI, signatures, trust validation) |
| ADR-V-0010 | Composable Architecture | Compiler (interface preservation, migration patterns) |
| ADR-V-0011 | Self-Evolving Infrastructure | Runtime (watchdog agents, tolerance config, global invariants) |
| ADR-V-0012 | Code Decorators (Intent Primitive) | Compiler + Runtime (decorator library in compiler, extraction in RECON) |
| ADR-V-0013 | Legacy Import Agent | Runtime (scan → infer → classify → validate → refine) |
| ADR-V-0014 | Decorator Inference Agent | Runtime (self-healing graph, detect → reason → infer → heal) |

### From /plan Design Artifacts

| Document | Subsystem Implication |
|---|---|
| architecture-compiler-overview.md | ste-architecture-compiler |
| architecture-compiler-stages.md | ste-architecture-compiler |
| architecture-compiler-internal-model.md | ste-architecture-compiler |
| kernel-interface-contract.md | ste-kernel (contract surface) |
| kernel-architecture-model.md | ste-kernel |
| kernel-query-surface.md | ste-kernel |
| super-graph-preparation.md | ste-architecture-compiler (federation subsystem) |
| multi-repo-entity-identity.md | ste-architecture-compiler (QualifiedEntityId) |
| registry-federation-model.md | ste-architecture-compiler (federation engine) |

### From ROADMAP.md

| Phase | Subsystem |
|---|---|
| Phase 0: Prompt Translator | ste-architecture-compiler |
| Phase 1: Decorator Library | ste-architecture-compiler |
| Phase 2: Rule Library | ste-rules-library |
| Phase 3: Verification System | ste-architecture-compiler |
| Phase 4: RECON Integration | ste-runtime |
| Phase 5: Rules & Signal Service | ste-rules-library (or separate service) |

### From Existing Repos

| Repo | Status |
|---|---|
| ste-spec | Exists (normative doctrine) |
| ste-runtime | Exists (public, v0.9.0 experimental) |
| adr-architecture-kit | Exists (private, renaming to ste-architecture-compiler) |

---

## 2. Subsystem Inventory

### ste-spec

**Role:** Constitution. Normative STE specification and doctrine.
**AI OS analogy:** POSIX standard / system specification.
**Status:** Exists.
**Depends on:** Nothing.
**Consumed by:** Everything.

What it contains:
- STE architectural specification (ISO-42010 aligned)
- PRIME invariants, SYS invariants
- Governance rules

### ste-architecture-compiler

**Role:** Compiler. ADR source → IR → registries. Federation engine.
**AI OS analogy:** Compiler toolchain (gcc/clang).
**Status:** Exists as `adr-architecture-kit`, rename pending.
**Depends on:** ste-spec (doctrine).
**Consumed by:** ste-kernel, ste-runtime (via registry output).

What it contains:
- ADR parser and schema validation (frontend)
- ArchModel intermediate representation (IR)
- Compilation passes (middle-end)
- Registry emitters (backend)
- Federation engine and SUPERGRAPH assembly
- Decorator library (`@implements_adr`, `@enforces_invariant`)
- Verification system (`adr verify-traceability`)
- Prompt translator (`adr generate-prompts`)
- CLI (`adr compile`, `adr validate`, `adr federate`)

Capabilities addressed:
- ADR-V-0001 (conversational architecture — compilation pipeline)
- ADR-V-0004 (bidirectional translation — prompt translator)
- ADR-V-0010 (composable architecture — interface preservation in IR)
- ADR-V-0012 (code decorators — decorator library ships here)

### ste-runtime

**Role:** Runtime graph engine. RECON extraction + RSS context queries.
**AI OS analogy:** Operating system runtime (process scheduler, memory manager).
**Status:** Exists, public, v0.9.0 experimental.
**Depends on:** ste-spec (doctrine), ste-architecture-compiler (registry output).
**Consumed by:** AI agents, developer tools, MCP clients.

What it contains:
- RECON (Reconciliation) — extracts ADRs + code + decorators into semantic graph
- RSS (Runtime Semantic Surface) — context assembly and graph queries
- MCP server — exposes graph queries to AI tools
- Agent execution framework (tiered: rule-based, local LLM, foundation)
- EDR (Embodied Design Record) — observed architecture from running systems

Capabilities addressed:
- ADR-V-0002 (agent tier system)
- ADR-V-0003 (meta-optimization)
- ADR-V-0006 (autonomous compliance — ADR vs EDR comparison)
- ADR-V-0007 (compliance AI agent)
- ADR-V-0008 (provider ecosystem)
- ADR-V-0009 (proposal security)
- ADR-V-0011 (self-evolving infrastructure — watchdog agents)
- ADR-V-0012 (code decorators — RECON extraction side)
- ADR-V-0013 (legacy import agent)
- ADR-V-0014 (decorator inference agent — self-healing graph)

### ste-kernel

**Role:** Architecture query runtime. Loads compiled registries, serves queries.
**AI OS analogy:** OS kernel (system calls, resource management).
**Status:** Planned (designed in /plan, not yet a repo).
**Depends on:** ste-architecture-compiler (registry output, contract schema).
**Consumed by:** ste-runtime, AI agents, developer tools.

What it contains:
- KernelArchitectureModel — read-only indexed graph loaded from 4 contract files
- EntityIndex, RelIndex, GapIndex — O(1) query indexes
- Query surface — 32+ typed queries across 6 categories
- Schema version negotiation
- Fingerprint-based cache invalidation

Why separate from ste-runtime:
- Different lifecycle: kernel is stable contract consumer, runtime is evolving agent platform
- Different deployment: kernel is embeddable library, runtime is service
- Different authority: kernel trusts compiled registries, runtime trusts raw sources

### ste-rules-library

**Role:** Policy store. Rule definitions, signal schema, rule activation.
**AI OS analogy:** System policy framework (/etc/security, SELinux policies).
**Status:** Planned (referenced in ROADMAP Phase 2, ADR-L-0006).
**Depends on:** ste-spec (doctrine), ste-architecture-compiler (invariant extraction).
**Consumed by:** ste-runtime (agents use rules), AI tools (via MCP).

What it contains:
- Rule schema definition
- Signal schema (claim, progress, complete, wave_complete, validation_ready)
- File-based rule loader
- Rule activator (context-aware rule selection)
- MCP server for rule delivery (Phase 2b)

Capabilities addressed:
- ADR-V-0005 (policy lifecycle management)

---

## 3. Build Order

The build order is determined by dependency analysis. A subsystem cannot be
built until its dependencies produce usable output.

```
ste-spec (exists, no changes needed)
    │
    ▼
ste-architecture-compiler (Phase 1 — core compiler)
    │
    ├──▶ ste-kernel (Phase 2 — consumes compiler output)
    │
    ├──▶ ste-rules-library (Phase 2 — consumes invariant extraction)
    │
    └──▶ ste-runtime evolution (Phase 3 — consumes registries + kernel)
```

### Phase 1: ste-architecture-compiler

**Priority: NOW**

This is the foundation. Nothing downstream works without compiled registries.

Build order within the compiler (from implementation-sequencing.md):
1. IP-0: Golden files (test safety net)
2. IP-1: Diagnostics + parse cache
3. IP-2: Intermediate representation (ArchModel) ← IR module already started
4. IP-3: Pass decomposition
5. IP-4: Compiler driver + `adr compile` CLI
6. IP-5: Kernel contract formalization (JSON Schema)
7. IP-6: Graph export + architecture analysis

After IP-4, the compiler produces deterministic registry output through the
IR pipeline. This is the minimum viable compiler.

Also in this phase (parallel with IP-0 through IP-4):
- Rename repo from `adr-architecture-kit` to `ste-architecture-compiler`
- Rename package from `adr_kit` to `ste_compiler`

### Phase 2: ste-kernel + ste-rules-library (parallel)

**Priority: After compiler IP-4 is complete.**

These two subsystems can be built in parallel because they have no dependency
on each other.

**ste-kernel:**
- Create new repository
- Implement KernelArchitectureModel (load from 4 contract files)
- Implement query surface (32+ queries)
- Implement fingerprint-based cache invalidation
- Contract conformance tests against compiler output

**ste-rules-library:**
- Create new repository
- Implement rule schema and signal schema
- Implement file-based rule loader
- Implement context-aware rule activator
- MCP server (Phase 2b)

### Phase 3: ste-runtime evolution

**Priority: After kernel exists and compiler produces stable registries.**

ste-runtime already exists and functions independently. Phase 3 evolves it to:
- Consume compiled registries via ste-kernel (instead of raw YAML parsing)
- Extract decorators from code via RECON (requires decorator library in compiler)
- Build unified semantic graph (ADRs + code + infrastructure)
- Implement ADR-V-0006 through ADR-V-0014 capabilities

### Phase 4: Federation (SUPERGRAPH)

**Priority: After Phase 2 (kernel must exist for SUPERGRAPH queries).**

Build order within federation (from implementation-sequencing.md):
1. IP-7: Super Graph preparation (namespace awareness, qualified IDs)
2. IP-8: Cross-repo references and federation engine

Federation lives in ste-architecture-compiler but produces output consumed
by ste-kernel (multi-repo KernelArchitectureModel).

---

## 4. Dependency Matrix

| Subsystem | Depends On | Produces For |
|---|---|---|
| ste-spec | — | All subsystems (doctrine) |
| ste-architecture-compiler | ste-spec | ste-kernel (registries), ste-runtime (registries + decorators), ste-rules-library (invariants) |
| ste-kernel | ste-architecture-compiler | ste-runtime (query surface), AI tools (queries) |
| ste-rules-library | ste-spec, ste-architecture-compiler | ste-runtime (rules), AI tools (rules via MCP) |
| ste-runtime | ste-spec, ste-architecture-compiler, ste-kernel, ste-rules-library | AI agents, developer tools, MCP clients |

---

## 5. What Is NOT a Separate Repo

These capabilities are features within existing repos, not separate subsystems:

| Capability | Lives In | Reason |
|---|---|---|
| Federation engine | ste-architecture-compiler | It's a compiler subsystem (`adr federate`) |
| Decorator library | ste-architecture-compiler | It ships with the compiler package |
| Verification system | ste-architecture-compiler | It's a CLI command (`adr verify-traceability`) |
| Prompt translator | ste-architecture-compiler | It's a generator (`adr generate-prompts`) |
| RECON ADR parser | ste-runtime | RECON is already in ste-runtime |
| EDR comparison | ste-runtime | It's a runtime observation capability |
| Compliance agents | ste-runtime | They run in the runtime agent framework |
| Provider ecosystem | ste-runtime | External provider integration is a runtime concern |
| Rules & Signal Service | ste-rules-library | It's the mature form of the rules library (MCP-primary) |
