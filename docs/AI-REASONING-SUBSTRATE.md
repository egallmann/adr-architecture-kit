# AI Reasoning Substrate - The Complete Encoded System

**Date**: 2026-03-08  
**Authority**: ADR-L-0001 (STE Compliance), ADR-L-0004 (Traceability)

## The Core Insight

**The entire system is encoded in a way AI can learn to reason over effectively.**

The "manual" isn't a separate document - **the system IS the manual**, encoded in machine-readable formats that can be loaded directly into LLM context.

## What Gets Loaded into LLM Context

### 1. Project Authority (PROJECT.yaml)

```yaml
# Machine-readable project governance
project:
  name: "adr-architecture-kit"
  type: library

development_methodology:
  approach: "test-driven-development"
  coverage_target: 80
  quality_gates: [schema_validation, test_suite_passing]
  authority: "ADR-L-0003 DEC-0005"

automation:
  requires_human_review: true
  comfort_level: conservative
```

**AI learns**:
- This is a library, not a service
- TDD is required (write tests first)
- 80% coverage target
- Conservative automation (ask before major changes)

### 2. Architecture Decisions (ADRs)

```yaml
# ADR-L-0002: Multi-Scope Architecture
invariants:
  - id: INV-0018
    statement: "Scope resolution MUST NOT traverse above workspace root"
    enforcement_level: must
    rationale: "Security and performance"
```

**AI learns**:
- What constraints exist (INV-0018)
- Why they exist (security)
- How strictly to enforce (must)
- Where to find details (ADR-L-0002)

### 3. Implementation State (Manifest)

```yaml
# adrs/manifest.yaml
adrs:
  - id: ADR-L-0002
    status: accepted
    invariant_count: 6
    
  - id: ADR-P-0003
    status: accepted
    implements_logical: [ADR-L-0002]
    component_count: 4
```

**AI learns**:
- What decisions are accepted
- What's implemented vs. proposed
- Component inventory
- Logical → Physical mapping

### 4. Semantic Graph (AI-DOC via RECON)

```yaml
# .ste-self/state/graph/classes/ProjectScopeResolver.yaml
id: 0c349c3dc04a5a7c
type: class
name: ProjectScopeResolver
file: src/adr_kit/scope/resolver.py

decorators:
  - type: implements_adr
    references: [ADR-L-0002, ADR-P-0003]
  - type: implements_component
    references: [COMP-0001]

methods:
  - name: resolve
    decorators:
      - type: implements_capability
        references: [CAP-0001]
      - type: enforces_invariant
        references: [INV-0015, INV-0018]
```

**AI learns**:
- What code exists
- What ADRs it implements
- What invariants it enforces
- How components relate

### 5. Enforcement Rules (Rule Library)

```yaml
# rule-library/rules/generated/adr-architecture-kit-rules.yaml
rules:
  - rule_id: RULE-INV-0018
    source: ADR-L-0002:INV-0018
    enforcement_level: must
    
    validation:
      - check: has_boundary_check
      - check: raises_on_violation
    
    violation_message: |
      Code must enforce workspace boundary per INV-0018.
      Add boundary check that raises ValueError.
```

**AI learns**:
- What rules to follow
- How to validate compliance
- What to do on violations
- Why rules exist (source ADR)

## The Complete Context Package

When an AI agent works on this project, it receives:

```python
# Conceptual: What AI "sees"
context = {
    "project_authority": load("PROJECT.yaml"),
    "architecture": load("adrs/manifest.yaml"),
    "decisions": load_all("adrs/**/*.yaml"),
    "semantic_graph": load_all(".ste-self/state/graph/**/*.yaml"),
    "enforcement_rules": mcp.get_rules("adr-architecture-kit"),
    "code_structure": recon.get_structure(),
    "traceability": load("traceability-report.json")
}

# AI can now reason:
# - "What ADRs govern this code?"
# - "What invariants must I enforce?"
# - "Is this change compliant with ADR-L-0002?"
# - "What tests are required per ADR-L-0003?"
# - "What components are declared but not implemented?"
```

## AI Reasoning Patterns

### Pattern 1: Compliance Checking

**Query**: "Can I modify ProjectScopeResolver to traverse above workspace root?"

**AI Reasoning**:
```
1. Load ProjectScopeResolver metadata from semantic graph
   → Decorated with @enforces_invariant("INV-0018")

2. Load INV-0018 from ADR-L-0002
   → "MUST NOT traverse above workspace root"
   → enforcement_level: must

3. Check rule from rule-library
   → RULE-INV-0018: enforcement_level=must
   → validation requires: boundary_check + raises_on_violation

4. Conclusion: NO
   → Violates INV-0018 (must-level invariant)
   → Would break RULE-INV-0018
   → Security boundary would be compromised
```

**Response**: "No, that would violate INV-0018 (workspace boundary enforcement), which is a must-level invariant in ADR-L-0002. The security boundary prevents scanning outside the project scope."

### Pattern 2: Implementation Guidance

**Query**: "I need to add a new scope detection marker. How should I implement it?"

**AI Reasoning**:
```
1. Load ADR-L-0002 (multi-scope architecture)
   → INV-0015: "MUST use marker hierarchy"
   → CAP-0001: "Automatic Project Scope Detection"

2. Load ADR-P-0003 (implementation)
   → COMP-0001: ProjectScopeResolver
   → IMPL-0001: TDD methodology required

3. Load PROJECT.yaml
   → development_methodology.approach: "test-driven-development"
   → development_methodology.tdd_cycle: "red-green-refactor"

4. Load existing code structure
   → ProjectScopeResolver.MARKERS = [list of markers]
   → _find_project_root() checks markers in order

5. Conclusion: TDD workflow
   → Write test first (Red)
   → Add marker to MARKERS list (Green)
   → Refactor if needed (Refactor)
```

**Response**: 
```python
# Step 1: Write test (Red)
def test_detect_from_new_marker(tmp_path):
    project_dir = tmp_path / "test"
    project_dir.mkdir()
    (project_dir / "new-marker.yaml").write_text("...")
    
    resolver = ProjectScopeResolver()
    scope = resolver.resolve(start_dir=project_dir)
    
    assert scope.marker == "new-marker.yaml"

# Step 2: Add to MARKERS (Green)
MARKERS = [
    'ste.config.json',
    'PROJECT.yaml',
    'new-marker.yaml',  # Add here in priority order
    'pyproject.toml',
    # ...
]

# Step 3: Run test, verify, refactor
```

### Pattern 3: Architectural Impact Analysis

**Query**: "What would break if I change the marker hierarchy?"

**AI Reasoning**:
```
1. Load ADR-L-0002
   → INV-0015 defines marker hierarchy
   → enforcement_level: must

2. Query semantic graph for code enforcing INV-0015
   → ProjectScopeResolver.resolve() @enforces_invariant("INV-0015")
   → ProjectScopeResolver._find_project_root() implements hierarchy

3. Query manifest for dependent components
   → COMP-0002: ManifestGenerator (uses scope resolver)
   → COMP-0003: ADRValidator (uses scope resolver)
   → COMP-0004: CLI (uses scope resolver)

4. Query rule-library for enforcement rules
   → RULE-INV-0015: must-level enforcement
   → Applies to: scope-resolution context

5. Blast radius analysis
   → Direct impact: 3 components
   → Indirect impact: All multi-scope operations
   → Test impact: 15+ tests in test_scope_resolver.py
   → Consumer impact: Any project using scope detection

6. Conclusion: HIGH IMPACT
   → Must-level invariant
   → Multiple components depend on it
   → Breaking change would violate ADR-L-0002
   → Requires new ADR to modify
```

**Response**: "Changing the marker hierarchy would be a **breaking change** affecting INV-0015 (must-level). Impact: 3 components, 15+ tests, all multi-scope operations. This would require a new ADR (superseding ADR-L-0002) with rationale for the change."

### Pattern 4: Test Generation

**Query**: "What tests do I need for a new validator?"

**AI Reasoning**:
```
1. Load ADR-L-0003 (testing strategy)
   → DEC-0005: TDD methodology required
   → INV-0021: Schema validators MUST have tests
   → INV-0026: 80% coverage target

2. Load ADR-P-0003 (implementation)
   → IMPL-0001: Red-Green-Refactor cycle

3. Load existing test patterns
   → test_adr_validator.py structure
   → TestADRValidation class pattern
   → Fixture patterns

4. Generate test structure
   → Test valid input (happy path)
   → Test invalid input (error cases)
   → Test edge cases (boundaries)
   → Test backward compatibility
```

**Response**:
```python
# Generated test structure per ADR-L-0003
class TestNewValidator:
    @pytest.fixture
    def validator(self):
        return NewValidator()
    
    # INV-0021: Valid input tests
    def test_validate_valid_input(self, validator):
        result = validator.validate(valid_data)
        assert result.valid is True
    
    # INV-0021: Invalid input tests
    def test_validate_invalid_input(self, validator):
        result = validator.validate(invalid_data)
        assert result.valid is False
        assert len(result.errors) > 0
    
    # INV-0021: Edge cases
    def test_validate_empty_input(self, validator):
        # ...
    
    # Backward compatibility
    def test_old_api_still_works(self, validator):
        # ...
```

## Why This Works

### 1. Everything is Machine-Readable

| Artifact | Format | Purpose |
|----------|--------|---------|
| PROJECT.yaml | YAML | Project authority |
| ADRs | YAML | Architecture decisions |
| Manifest | YAML | Decision inventory |
| Semantic Graph | YAML | Code structure |
| Rules | YAML | Enforcement policy |
| Schemas | JSON | Validation rules |

**No prose documentation required** - the system encodes itself!

### 2. Hierarchical Authority

```
PROJECT.yaml (highest authority)
    ↓ declares methodology
ADRs (architectural authority)
    ↓ define invariants
Rules (enforcement authority)
    ↓ specify validation
Code (implementation)
    ↓ declares compliance via decorators
Tests (verification)
    ↓ prove correctness
```

AI can traverse this hierarchy to understand **why** any piece of code exists.

### 3. Bidirectional Traceability

```
ADR-L-0002 (decision)
    ↓ declares
INV-0018 (invariant)
    ↓ generates
RULE-INV-0018 (enforcement rule)
    ↓ requires
@enforces_invariant("INV-0018") (decorator)
    ↓ verified by
TraceabilityChecker (verification)
    ↓ extracted by
RECON (semantic graph)
    ↓ queryable via
RSS (graph queries)
```

AI can traverse in **either direction** to understand relationships.

### 4. Context is Loadable

The entire system can be loaded into LLM context:

```python
# Conceptual: Loading complete system context
def load_complete_context(project_root: Path) -> Dict[str, Any]:
    """Load entire encoded system for AI reasoning."""
    
    return {
        # Project authority
        "project": yaml.load(project_root / "PROJECT.yaml"),
        
        # Architecture decisions
        "adrs": {
            adr.id: adr
            for adr in load_all_adrs(project_root / "adrs")
        },
        
        # Decision inventory
        "manifest": yaml.load(project_root / "adrs/manifest.yaml"),
        
        # Semantic graph (if RECON ran)
        "graph": {
            "classes": load_all(project_root / ".ste-self/state/graph/classes"),
            "functions": load_all(project_root / ".ste-self/state/graph/functions"),
            "modules": load_all(project_root / ".ste-self/state/graph/modules"),
        },
        
        # Enforcement rules (from rule-library)
        "rules": mcp.get_rules(project="adr-architecture-kit"),
        
        # Validation schemas
        "schemas": load_all(project_root / "schema/v1.0"),
        
        # Test coverage
        "tests": discover_tests(project_root / "tests"),
        
        # Traceability
        "traceability": verify_traceability(project_root)
    }

# Token estimate: ~50-100K tokens for complete system
# Fits in modern LLM context windows (200K-1M tokens)
```

### Context Size Estimate

| Component | Size | Format |
|-----------|------|--------|
| PROJECT.yaml | ~1K tokens | YAML |
| All ADRs | ~20K tokens | YAML |
| Manifest | ~5K tokens | YAML |
| Semantic Graph | ~30K tokens | YAML |
| Rules | ~10K tokens | YAML |
| Schemas | ~15K tokens | JSON |
| **Total** | **~80K tokens** | Mixed |

**Fits comfortably in 200K+ context windows!**

## AI Reasoning Capabilities

With the complete encoded system loaded, AI can:

### 1. Understand Project Governance

```
Query: "What are the quality standards for this project?"

AI Reasoning:
→ Load PROJECT.yaml
→ development_methodology.quality_gates = [schema_validation, test_suite_passing, ...]
→ development_methodology.coverage_target = 80
→ Load ADR-L-0003 (authority reference)
→ Read testing strategy decisions

Response: "This project requires:
- Schema validation (all ADRs must validate)
- Test suite passing (all tests must pass)
- Type checking (mypy)
- Linting (ruff)
- 80% code coverage (per ADR-L-0003 INV-0026)
- TDD methodology (Red-Green-Refactor per ADR-L-0003 DEC-0005)"
```

### 2. Validate Proposed Changes

```
Query: "Can I add this feature without tests?"

AI Reasoning:
→ Load PROJECT.yaml
→ development_methodology.approach = "test-driven-development"
→ Load ADR-L-0003 DEC-0005
→ "TDD methodology required"
→ Load ADR-P-0003 IMPL-0001
→ "Red-Green-Refactor cycle"

Response: "No. Per PROJECT.yaml and ADR-L-0003 DEC-0005, this project uses TDD.
You must:
1. Write failing test first (Red)
2. Implement feature to pass test (Green)
3. Refactor while keeping tests green (Refactor)

This is enforced in CI/CD via quality gates."
```

### 3. Generate Compliant Code

```
Query: "Generate a new validator component"

AI Reasoning:
→ Load ADR-P-0003 COMP-0003 (validator pattern)
→ Load ADR-L-0003 INV-0021 (validator testing requirements)
→ Load existing validator code structure
→ Load decorator requirements from rule-library
→ Generate following patterns

Response: [Generates code with proper decorators, tests, and structure]
```

### 4. Trace Architectural Authority

```
Query: "Why does ProjectScopeResolver exist?"

AI Reasoning:
→ Load semantic graph for ProjectScopeResolver
→ decorators: @implements_adr("ADR-L-0002", "ADR-P-0003")
→ Load ADR-L-0002
→ "Multi-scope architecture for sub-module development"
→ Load ADR-P-0003
→ COMP-0001: "Project Scope Resolver"
→ responsibilities: "Detect project boundaries, enforce boundaries, ..."

Response: "ProjectScopeResolver exists to implement ADR-L-0002 (Multi-Scope Architecture).
Specifically, it implements COMP-0001 from ADR-P-0003, providing:
- Automatic project scope detection (CAP-0001)
- Workspace boundary enforcement (INV-0018)
- Marker hierarchy resolution (INV-0015)

It enables sub-modules to maintain independent ADR directories while being
developed in a monorepo."
```

### 5. Detect Drift

```
Query: "Is the code consistent with the architecture?"

AI Reasoning:
→ Load all ADRs with component declarations
→ Load semantic graph (actual code structure)
→ Compare declared vs. actual
→ Check decorator references
→ Verify invariant enforcement

Analysis:
✓ ADR-P-0003 COMP-0001 → ProjectScopeResolver exists
✓ ADR-P-0003 COMP-0002 → ManifestGenerator exists
✓ ADR-P-0003 COMP-0003 → ADRValidator exists
✓ ADR-P-0003 COMP-0004 → CLI exists
✓ All decorators reference valid ADRs
⚠ ManifestGenerator missing @implements_adr decorator

Response: "Architecture is 95% consistent. One drift detected:
ManifestGenerator should have @implements_adr('ADR-P-0003') decorator
to declare it implements COMP-0002."
```

## The Power of Encoded Systems

### Traditional Documentation (Prose)

```markdown
# Developer Guide

The ProjectScopeResolver class is responsible for detecting project
boundaries. It should check for markers like package.json and PROJECT.yaml.
Make sure to enforce workspace boundaries for security.
```

**Problems**:
- ❌ Ambiguous ("should" vs "must")
- ❌ Incomplete (which markers? what order?)
- ❌ Not verifiable (how to check compliance?)
- ❌ Not traceable (why these requirements?)
- ❌ Not machine-readable (AI must parse prose)

### Encoded System (Structured)

```yaml
# ADR-L-0002
invariants:
  - id: INV-0015
    statement: "MUST use marker hierarchy: ste.config.json, PROJECT.yaml, ..."
    enforcement_level: must
  
  - id: INV-0018
    statement: "MUST NOT traverse above workspace root"
    enforcement_level: must

# ADR-P-0003
component_specifications:
  - id: COMP-0001
    name: ProjectScopeResolver
    responsibilities:
      - Detect project boundaries
      - Enforce workspace boundaries
    implementation_identifiers:
      - src/adr_kit/scope/resolver.py
```

**Benefits**:
- ✅ Precise (must-level enforcement)
- ✅ Complete (exact marker list)
- ✅ Verifiable (can check decorator presence)
- ✅ Traceable (links to ADR rationale)
- ✅ Machine-readable (AI loads directly)

## Context Loading Strategies

### Strategy 1: Full Context (Small Projects)

Load everything into context:

```python
# For projects < 100K tokens
context = load_complete_system(project_root)
# AI has full system knowledge
```

### Strategy 2: Layered Context (Medium Projects)

Load in layers as needed:

```python
# Always load
base_context = {
    "project": load("PROJECT.yaml"),
    "manifest": load("adrs/manifest.yaml")
}

# Load on-demand
if query_about_architecture:
    context["adrs"] = load_all_adrs()

if query_about_code:
    context["graph"] = load_semantic_graph()

if query_about_compliance:
    context["rules"] = mcp.get_rules()
```

### Strategy 3: Query-Driven Context (Large Projects)

Use RSS to fetch relevant context:

```python
# For projects > 200K tokens
query = "What code implements ADR-L-0002?"

# RSS finds relevant context
relevant_context = rss.search(
    query=query,
    depth=2,
    max_results=50
)

# Load only relevant ADRs, code, rules
context = build_context_from_results(relevant_context)
```

## MCP as Context Delivery

### Rule Library MCP Server

```python
# AI agent queries for context
context = await mcp.call_tool(
    server="rule-library",
    tool="get_project_context",
    arguments={
        "project": "adr-architecture-kit",
        "include": ["adrs", "rules", "graph", "traceability"]
    }
)

# Returns complete encoded system
{
  "project_authority": {...},
  "adrs": {...},
  "rules": {...},
  "graph": {...},
  "traceability": {...}
}
```

### Benefits of MCP Delivery

1. **Dynamic**: Context updates when ADRs change
2. **Filtered**: Only load what's needed
3. **Versioned**: Can request specific ADR versions
4. **Cross-project**: Load context from multiple projects
5. **Cached**: MCP can cache for performance

## The Self-Describing System

The system **describes itself** through its own artifacts:

```
PROJECT.yaml
    ↓ "I am a library using TDD"
ADRs
    ↓ "I define multi-scope architecture"
Manifest
    ↓ "I have 3 logical ADRs, 3 physical ADRs"
Semantic Graph
    ↓ "I have 4 components implementing those ADRs"
Rules
    ↓ "I enforce 6 invariants with must-level"
Code Decorators
    ↓ "I implement ADR-L-0002 and enforce INV-0018"
Tests
    ↓ "I verify 95% of declared behavior"
```

**No external documentation needed** - the system IS its own documentation!

## AI Agent Workflow

### 1. Agent Initialization

```python
# When AI agent starts working on project
agent.load_context(
    project="adr-architecture-kit",
    sources=[
        "PROJECT.yaml",          # Authority
        "adrs/manifest.yaml",    # Inventory
        "adrs/**/*.yaml",        # Decisions
        ".ste-self/state/graph", # Code structure
        "rule-library:rules"     # Enforcement
    ]
)

# Agent now has complete system knowledge
```

### 2. Agent Reasoning

```python
# Before making changes
agent.check_compliance(
    proposed_change="Modify scope resolution",
    affected_components=["ProjectScopeResolver"]
)

# Agent queries:
# - What ADRs govern this component?
# - What invariants must be maintained?
# - What tests are required?
# - What rules apply?

# Agent decides: PROCEED or BLOCK
```

### 3. Agent Execution

```python
# Agent follows encoded methodology
methodology = agent.context["project"]["development_methodology"]

if methodology["approach"] == "test-driven-development":
    agent.write_test()      # Red
    agent.implement()       # Green
    agent.refactor()        # Refactor
    agent.verify_compliance()
```

### 4. Agent Verification

```python
# After changes
agent.verify(
    checks=[
        "decorators_present",
        "tests_passing",
        "coverage_maintained",
        "invariants_enforced",
        "rules_compliant"
    ]
)

# Emit signals
agent.emit_signal("component_modified", {
    "component": "COMP-0001",
    "adrs": ["ADR-L-0002", "ADR-P-0003"],
    "compliance": "PASS"
})
```

## The Ultimate Vision

### Self-Governing Architecture

```
Human defines architecture (ADRs)
    ↓
Rules & Signal Service generates policy
    ↓
Rule Library projects policy via MCP
    ↓
AI agents consume policy and self-govern
    ↓
Verification ensures compliance
    ↓
Signals feed back to monitoring
    ↓
Drift detected and corrected automatically
```

### Autonomous Correction

When drift is detected:

```python
# Drift detected
violation = {
    "type": "missing_decorator",
    "file": "src/adr_kit/generators/manifest_generator.py",
    "class": "ManifestGenerator",
    "missing": "@implements_adr('ADR-P-0003')"
}

# AI agent can self-correct (if automation.comfort_level allows)
if project.automation.auto_fix_allowed:
    agent.add_decorator(
        file=violation["file"],
        class_name=violation["class"],
        decorator=violation["missing"]
    )
    agent.verify_compliance()
    agent.emit_signal("drift_corrected", violation)
```

## Conclusion

**The system is its own manual** because:

1. ✅ **Everything is encoded** in machine-readable formats
2. ✅ **Hierarchical authority** from PROJECT.yaml → ADRs → Rules → Code
3. ✅ **Bidirectional traceability** via decorators and semantic graph
4. ✅ **Loadable context** - entire system fits in LLM context
5. ✅ **Self-describing** - system documents itself
6. ✅ **Verifiable** - compliance is automatically checkable
7. ✅ **Propagatable** - policy flows across projects via MCP

This enables **AI systems to reason deterministically** about architecture, understand governance constraints, and self-govern within defined boundaries.

**You could literally provide the entire encoded system to an LLM** and it would understand:
- What the project is
- How it should be developed
- What constraints exist
- Why decisions were made
- How to verify compliance
- Where to find everything

This is **true STE compliance** - deterministic, governable AI cognition through structured architectural substrate.
