# ADR Architecture Kit - Implementation Roadmap

**Last Updated**: 2026-03-08

## Vision

Transform architecture decisions into **enforceable, propagatable policy** across the STE ecosystem through a multi-tier governance architecture.

## Current State (2026-03-08)

### ✅ Completed (MVP)

**Core ADR System**:
- ✅ JSON Schema v1.0 for ADRs
- ✅ Python toolkit (parser, models, generators)
- ✅ Manifest generation (SYS-14 compliance)
- ✅ Schema validation (INV-0001)
- ✅ Markdown view generation

**Multi-Scope Architecture** (NEW):
- ✅ ADR-L-0002: Multi-scope logical architecture
- ✅ ADR-P-0003: Python implementation
- ✅ ADR-L-0003: Quality assurance strategy
- ✅ Scope resolver with auto-detection
- ✅ Scope-aware generators and validators
- ✅ CLI with --scope and --recursive
- ✅ Comprehensive test suite
- ✅ TDD methodology in PROJECT.yaml

**Documentation**:
- ✅ Multi-scope guide
- ✅ TDD workflow guide
- ✅ Testing implementation docs

### 🎯 Current Focus

**AI-Driven Development Automation**:
- ✅ ADR-L-0005: ADR-to-Prompt Translation (logical design)
- ✅ ADR-P-0004: Prompt Translator Implementation (physical design)
- ⏳ Prompt translator implementation (COMP-0005 through COMP-0008)

**ADR Traceability Foundation**:
- ✅ ADR-L-0004: Traceability via decorators (logical design)
- ⏳ Decorator library implementation (after prompt translator)
- ⏳ Rule-library sub-module scaffolding

## Roadmap

### Phase 0: Prompt Translator (Foundation)

**Goal**: Automate generation of implementation prompts from ADRs

**Deliverables**:
- [x] **ADR-L-0005**: ADR-to-Prompt Translation (Logical)
- [x] **ADR-P-0004**: Prompt Translator Implementation (Physical)
- [ ] `src/adr_kit/prompts/__init__.py`
- [ ] `src/adr_kit/prompts/parser.py` - ComponentParser
- [ ] `src/adr_kit/prompts/generator.py` - PromptGenerator
- [ ] `src/adr_kit/prompts/dependencies.py` - DependencyAnalyzer
- [ ] `src/adr_kit/prompts/templates/implementation-prompt.md.jinja2`
- [ ] `src/adr_kit/prompts/templates/validation-checklist.md.jinja2`
- [ ] `src/adr_kit/prompts/templates/execution-plan.md.jinja2`
- [ ] CLI: `adr generate-prompts ADR-P-XXXX`
- [ ] Tests for all components
- [ ] Documentation with examples

**Success Criteria**:
- Parse Physical ADRs and extract component specs
- Generate implementation prompts with all invariants
- Generate validation checklists
- Generate execution plans with dependency ordering
- Deterministic generation (same ADR → same prompts)
- CLI works: `adr generate-prompts ADR-P-0003`

**Why First**:
- Enables automated prompt generation for ALL future work
- Self-referential: Can generate prompts for decorator library
- Scales to any number of ADRs/components
- Reduces manual prompt crafting effort

**Example**:
```bash
# Generate prompts from Physical ADR
adr generate-prompts ADR-P-0003 --target codex --output prompts/

# Generates:
# - prompts/COMP-0001-scope-resolver.md
# - prompts/COMP-0002-manifest-generator.md
# - prompts/COMP-0003-validator.md
# - prompts/COMP-0004-cli.md
# - prompts/validation-checklist.md
# - prompts/execution-plan.md
```

### Phase 1: Decorator Library

**Goal**: Enable code annotation with ADR references

**Deliverables**:
- [ ] **ADR-P-0004**: Physical ADR for decorator library
- [ ] `src/adr_kit/decorators/__init__.py`
- [ ] `@implements_adr()` decorator
- [ ] `@enforces_invariant()` decorator
- [ ] `@implements_capability()` decorator
- [ ] `@implements_component()` decorator
- [ ] `get_traceability()` helper
- [ ] Tests for decorator functionality
- [ ] Documentation with examples

**Success Criteria**:
- Decorators don't affect runtime behavior
- Metadata extractable via `__adr_traceability__`
- Tests prove decorator composition works
- Can annotate existing code

**Example**:
```python
@implements_adr("ADR-L-0002", "ADR-P-0003")
@implements_component("COMP-0001")
class ProjectScopeResolver:
    pass
```

### Phase 2: Rule Library Sub-Module

**Goal**: Create MCP service for rule activation and projection

**Deliverables**:
- [ ] **ADR-P-0005**: Physical ADR for rule-library sub-module
- [ ] `rule-library/` sub-module structure
- [ ] `rule-library/PROJECT.yaml`
- [ ] `rule-library/adrs/` (sub-module's own ADRs)
- [ ] Rule schema definition
- [ ] File-based rule loader
- [ ] Rule activator (context-aware)
- [ ] MCP server implementation
- [ ] MCP tools: `get_rules`, `validate_decorator`, `check_traceability`
- [ ] Tests for rule loading and activation
- [ ] Integration with adr-architecture-kit

**Success Criteria**:
- Can load rules from YAML files
- MCP server responds to tool calls
- Rules can be filtered by context
- File-based fallback works offline
- Independent package (can be extracted)

**Dependencies**: Phase 1 (decorators needed for verification)

**MCP Integration**:
```bash
# Start MCP server
cd rule-library
python -m rule_library.mcp_server

# Query from consumer
adr-verify get-rules --project adr-architecture-kit --mcp
```

### Phase 3: Verification System

**Goal**: Automated bidirectional traceability verification

**Deliverables**:
- [ ] **ADR-P-0006**: Physical ADR for verification system
- [ ] `src/adr_kit/verification/traceability_checker.py`
- [ ] AST-based decorator extraction
- [ ] Forward traceability (ADR → Code)
- [ ] Reverse traceability (Code → ADR)
- [ ] Orphaned code detection
- [ ] Phantom declaration detection
- [ ] CLI: `adr verify-traceability`
- [ ] CI/CD integration examples
- [ ] Violation reporting

**Success Criteria**:
- Detects missing decorators
- Detects invalid ADR references
- Detects unimplemented components
- Generates actionable reports
- CI/CD can enforce traceability

**Dependencies**: Phase 1 (needs decorators to verify)

**Usage**:
```bash
adr verify-traceability --strict
# ✓ 95% traceability (19/20 verified)
# ⚠ 1 warning: ManifestGenerator missing decorator
```

### Phase 4: RECON Integration

**Goal**: Extract decorator metadata into semantic graph

**Deliverables** (in ste-runtime):
- [ ] **ste-runtime ADR**: RECON decorator extraction
- [ ] Python extractor enhancement
- [ ] Decorator metadata in AI-DOC slices
- [ ] Graph edges: `implements`, `enforces`
- [ ] RSS queries by ADR reference
- [ ] RSS queries by invariant
- [ ] Traceability visualization

**Success Criteria**:
- RECON extracts `@implements_adr` decorators
- AI-DOC slices include traceability metadata
- Can query: "What code implements ADR-L-0002?"
- Can query: "What code enforces INV-0018?"
- Graph shows bidirectional links

**Dependencies**: Phase 1 (decorators must exist in code)

**Graph Query Example**:
```bash
rss search "implements ADR-L-0002"
# Results:
# - src/adr_kit/scope/resolver.py:ProjectScopeResolver
# - src/adr_kit/generators/manifest_generator.py:ManifestGenerator
```

### Phase 5: Rules & Signal Service

**Goal**: Automated rule generation from ADRs

**Deliverables** (separate service):
- [ ] **Service ADRs**: Rules & Signal Service design
- [ ] ADR parser and analyzer
- [ ] Rule generator from invariants
- [ ] Signal generator from capabilities
- [ ] Rule publisher to rule-library
- [ ] Compliance monitoring
- [ ] Conflict detection
- [ ] Dashboard for governance

**Success Criteria**:
- Parses ADRs from multiple projects
- Generates rules automatically
- Publishes to rule-library MCP service
- Monitors compliance across projects
- Detects conflicting invariants

**Dependencies**: Phase 2 (rule-library must exist), Phase 4 (RECON for semantic analysis)

**Architecture**:
```
Rules & Signal Service
├── ADR Parser
├── Rule Generator (Invariants → Rules)
├── Signal Generator (Capabilities → Signals)
├── Rule Publisher (→ rule-library MCP)
├── Compliance Monitor
└── Conflict Detector
```

## Sub-Module Evolution

### Current Sub-Modules

1. **ste-runtime** (exists)
   - RECON semantic extraction
   - RSS graph queries
   - MCP server
   - Status: Active development

2. **ste-spec** (exists)
   - Normative STE specification
   - Status: Governance

### New Sub-Modules

3. **rule-library** (Phase 2)
   - Rule activation and projection
   - MCP service for rule delivery
   - Status: Planned

4. **Rules & Signal Service** (Phase 5)
   - Rule generation from ADRs
   - Compliance monitoring
   - Status: Future (separate service)

## Integration Points

### adr-architecture-kit ↔ rule-library

```python
# adr-architecture-kit provides decorators
from adr_kit.decorators import implements_adr

# rule-library provides verification
from rule_library import TraceabilityChecker

checker = TraceabilityChecker(project_root, adr_dir)
violations = checker.check_forward_traceability()
```

### rule-library ↔ ste-runtime

```python
# ste-runtime RECON extracts decorators
# rule-library verifies decorator references

# MCP integration
rules = await mcp.call_tool(
    server="rule-library",
    tool="get_rules",
    arguments={"project": "adr-architecture-kit"}
)
```

### rule-library ↔ Rules & Signal Service

```python
# Rules & Signal Service publishes rules
await rule_library.publish_rules(
    project="adr-architecture-kit",
    rules=generated_rules
)

# rule-library activates and serves rules
rules = rule_library.get_rules(
    project="adr-architecture-kit",
    context="scope-resolution"
)
```

## Migration Strategy

### Existing Code Annotation

**Gradual adoption** - don't require immediate annotation:

1. **New code**: Must have decorators (enforced in PR review)
2. **Modified code**: Add decorators when touching files
3. **Critical code**: Annotate validators, generators first
4. **Utility code**: Annotate as time permits

**Coverage tracking**:
```bash
adr verify-traceability --report
# Traceability: 45% (9/20 components)
# Target: 80% by end of quarter
```

### Rule Library Transition

**File-based → MCP-based**:

1. **Phase 2**: File-based rules (development)
   ```yaml
   # rule-library/rules/traceability/rules.yaml
   ```

2. **Phase 3**: Hybrid (file-based + MCP)
   ```python
   # Try MCP first, fallback to files
   rules = await get_rules_mcp() or load_rules_file()
   ```

3. **Phase 5**: MCP-primary (with Rules & Signal Service)
   ```python
   # Rules generated dynamically from ADRs
   rules = await mcp.get_rules(project, context)
   ```

## Success Metrics

### Phase 1 (Decorators)
- ✅ Decorator library implemented
- ✅ 10+ code files annotated
- ✅ Tests prove decorators work
- ✅ Documentation with examples

### Phase 2 (Rule Library)
- ✅ MCP server operational
- ✅ Can serve rules to consumers
- ✅ File-based rules loaded
- ✅ Context-aware activation works

### Phase 3 (Verification)
- ✅ Bidirectional verification works
- ✅ CI/CD enforcement active
- ✅ 80%+ traceability coverage
- ✅ Zero critical violations

### Phase 4 (RECON)
- ✅ Decorators in semantic graph
- ✅ Can query by ADR reference
- ✅ Graph shows traceability
- ✅ RSS integration complete

### Phase 5 (Rules & Signal Service)
- ✅ Generates rules from ADRs
- ✅ Publishes to rule-library
- ✅ Monitors 3+ projects
- ✅ Detects policy conflicts

## Component Dependencies

```
adr-architecture-kit (this project)
    ↓ provides decorators
rule-library (sub-module)
    ↓ provides MCP service
ste-runtime (sub-module)
    ↓ extracts decorators
Rules & Signal Service (future)
    ↓ generates rules
```

## Questions to Resolve

1. **Rule generation algorithm**: How exactly does Rules & Signal Service generate rules from invariants?
2. **Signal semantics**: What signals are emitted and what do they mean?
3. **Conflict resolution**: How to handle conflicting invariants across projects?
4. **Rule versioning**: How to version rules when ADRs change?
5. **Performance**: Can rule-library scale to 100+ projects?

## Next Actions

1. Create **ADR-P-0004** for decorator library implementation
2. Implement decorator library with TDD
3. Annotate existing code (starting with scope resolver)
4. Create **rule-library/** sub-module structure
5. Design Rules & Signal Service interface

---

This roadmap transforms the ADR Architecture Kit from a **documentation tool** into the foundation of a **self-governing architectural system**.
