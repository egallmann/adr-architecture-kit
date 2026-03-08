# STE Governance Architecture - Complete System Design

**Date**: 2026-03-08  
**Authority**: ADR-L-0004 - ADR-to-Code Traceability via Decorators

## The Complete Vision

A **multi-tier governance system** where architectural decisions flow through automated rule generation, activation, and enforcement across projects.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1: PROJECT AUTHORITY (Source of Truth)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Project: adr-architecture-kit                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ ADRs (Architecture Decisions)                           │    │
│  │  - ADR-L-0002: Multi-scope architecture                 │    │
│  │  - ADR-P-0003: Python implementation                    │    │
│  │                                                          │    │
│  │  Declares:                                               │    │
│  │  - INV-0015: Marker hierarchy MUST be followed          │    │
│  │  - INV-0018: Workspace boundaries MUST be enforced      │    │
│  │  - COMP-0001: ProjectScopeResolver component            │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ↓                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               ↓
┌──────────────────────────────┼───────────────────────────────────┐
│ TIER 2: RULE GENERATION (Policy Synthesis)                      │
├──────────────────────────────┼───────────────────────────────────┤
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Rules & Signal Service (Future)                         │    │
│  │                                                          │    │
│  │  Parses ADRs and generates:                             │    │
│  │                                                          │    │
│  │  From INV-0015:                                          │    │
│  │    → RULE-001: "Scope resolution must check markers     │    │
│  │                 in priority order"                       │    │
│  │    → SIGNAL: scope_marker_checked(marker, priority)     │    │
│  │                                                          │    │
│  │  From INV-0018:                                          │    │
│  │    → RULE-002: "Scope resolution must enforce           │    │
│  │                 workspace boundaries"                    │    │
│  │    → SIGNAL: boundary_enforced(path, boundary_type)     │    │
│  │                                                          │    │
│  │  From COMP-0001:                                         │    │
│  │    → RULE-003: "ProjectScopeResolver must exist at      │    │
│  │                 src/adr_kit/scope/resolver.py"          │    │
│  │    → SIGNAL: component_implemented(comp_id, path)       │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ↓                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               ↓
┌──────────────────────────────┼───────────────────────────────────┐
│ TIER 3: RULE ACTIVATION (Service Layer)                         │
├──────────────────────────────┼───────────────────────────────────┤
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ rule-library/ (MCP Service Sub-Module)                  │    │
│  │                                                          │    │
│  │  Receives rules from Rules & Signal Service             │    │
│  │  Activates rules for specific contexts                  │    │
│  │  Projects rules via MCP to consumers                    │    │
│  │                                                          │    │
│  │  MCP Tools:                                              │    │
│  │  - get_rules(project, context)                          │    │
│  │  - validate_decorator(decorator_type, reference)        │    │
│  │  - check_traceability(code_path, adr_id)                │    │
│  │  - emit_signal(signal_type, metadata)                   │    │
│  │                                                          │    │
│  │  Storage:                                                │    │
│  │  - File-based: rules/*.yaml (development)               │    │
│  │  - MCP-based: Dynamic from Rules & Signal Service       │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ↓                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               ↓
┌──────────────────────────────┼───────────────────────────────────┐
│ TIER 4: ENFORCEMENT (Consumer Projects)                         │
├──────────────────────────────┼───────────────────────────────────┤
│                              ↓                                   │
│  Consumer Project: ste-runtime, other-service, etc.             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Code with Decorators                                    │    │
│  │                                                          │    │
│  │  @implements_adr("ADR-L-0002", "ADR-P-0003")           │    │
│  │  @enforces_invariant("INV-0015", "INV-0018")           │    │
│  │  class ProjectScopeResolver:                            │    │
│  │      @implements_capability("CAP-0001")                 │    │
│  │      def resolve(self, start_dir):                      │    │
│  │          # Boundary check per INV-0018                  │    │
│  │          if self._is_workspace_boundary(start_dir):     │    │
│  │              raise ValueError("Boundary violation")     │    │
│  │          # Marker check per INV-0015                    │    │
│  │          for marker in MARKERS:                         │    │
│  │              if (start_dir / marker).exists():          │    │
│  │                  return self._create_scope(start_dir)   │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Verification (CI/CD)                                    │    │
│  │                                                          │    │
│  │  1. Query rule-library via MCP:                         │    │
│  │     rules = mcp.get_rules("adr-architecture-kit")       │    │
│  │                                                          │    │
│  │  2. Verify decorators match rules:                      │    │
│  │     verify_traceability(code, rules)                    │    │
│  │                                                          │    │
│  │  3. Emit signals for compliance:                        │    │
│  │     emit_signal("invariant_enforced", "INV-0018")       │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. ADR Definition (Project Authority)

**File**: `adrs/logical/ADR-L-0002-multi-scope-adr-architecture.yaml`

```yaml
invariants:
  - id: INV-0018
    statement: |
      Scope resolution MUST NOT traverse above workspace root
    enforcement_level: must
    rationale: Security and performance
```

### 2. Rule Generation (Rules & Signal Service)

**Generated Rule**:

```yaml
# Generated by Rules & Signal Service
rule_id: RULE-INV-0018
source_adr: ADR-L-0002
source_invariant: INV-0018
rule_type: enforcement
enforcement_level: must

rule:
  description: "Scope resolution MUST NOT traverse above workspace root"
  
  requires:
    decorator: enforces_invariant
    reference: INV-0018
    
  validation:
    - check: has_boundary_check_logic
    - check: raises_on_violation
    
  signals:
    - on_enforcement: boundary_enforced
    - on_violation: boundary_violated

applies_to:
  - component: COMP-0001
    methods: ["resolve", "_find_project_root"]
```

### 3. Rule Activation (Rule Library MCP Service)

**MCP Tool Call**:

```python
# AI agent or verification tool queries rule-library
rules = await mcp.call_tool(
    server="rule-library",
    tool="get_rules",
    arguments={
        "project": "adr-architecture-kit",
        "context": "scope-resolution"
    }
)

# Returns:
{
  "rules": [
    {
      "rule_id": "RULE-INV-0018",
      "requires_decorator": "enforces_invariant",
      "reference": "INV-0018",
      "enforcement_level": "must"
    }
  ]
}
```

### 4. Code Annotation (Consumer Project)

**File**: `src/adr_kit/scope/resolver.py`

```python
from adr_kit.decorators import implements_adr, enforces_invariant

@implements_adr("ADR-L-0002", "ADR-P-0003")
@implements_component("COMP-0001")
class ProjectScopeResolver:
    """Resolve project scope per ADR-L-0002."""
    
    @enforces_invariant("INV-0018")
    def _is_workspace_boundary(self, path: Path) -> bool:
        """Enforce workspace boundary per INV-0018."""
        # This method enforces the invariant
        return path.name in self.SYSTEM_BOUNDARIES
    
    def resolve(self, start_dir: Optional[Path] = None) -> ProjectScope:
        """Auto-detect project boundaries."""
        current = start_dir or Path.cwd()
        
        while current != Path(current.anchor):
            # Enforcement of INV-0018
            if self._is_workspace_boundary(current):
                raise ValueError(f"Cannot traverse above workspace boundary: {current}")
            # ...
```

### 5. Verification (Enforcement)

**CI/CD Pipeline**:

```bash
# Step 1: Get rules from rule-library MCP service
rules=$(adr-verify get-rules --project adr-architecture-kit)

# Step 2: Verify code matches rules
adr-verify check-traceability \
  --code src/adr_kit/ \
  --adrs adrs/ \
  --rules "$rules"

# Output:
# ✓ ProjectScopeResolver has @implements_adr("ADR-L-0002", "ADR-P-0003")
# ✓ _is_workspace_boundary has @enforces_invariant("INV-0018")
# ✓ INV-0018 enforcement logic verified
# ✓ All 15 components have valid decorators
#
# Traceability: 100%
# Policy Compliance: PASS
```

## Sub-Module Design: rule-library

### Purpose

**Rule Library** is a **service sub-module** that:
1. Receives rules from Rules & Signal Service (or loads from files)
2. Activates rules for specific project contexts
3. Projects rules via MCP to consumers
4. Provides rule evaluation and validation logic

### Structure

```
rule-library/
├── README.md
├── pyproject.toml                    # Independent package
├── PROJECT.yaml                      # Sub-module project metadata
├── adrs/                             # rule-library's own ADRs
│   ├── logical/
│   │   └── ADR-L-0001-rule-activation-service.yaml
│   └── physical/
│       └── ADR-P-0001-mcp-rule-server.yaml
├── rules/                            # File-based rules (fallback)
│   ├── traceability/
│   │   └── decorator-requirements.yaml
│   └── generated/                    # Rules from Rules & Signal Service
│       └── adr-architecture-kit-rules.yaml
├── src/
│   └── rule_library/
│       ├── __init__.py
│       ├── loader.py                 # Load rules from files
│       ├── activator.py              # Activate rules for context
│       ├── evaluator.py              # Evaluate rules against code
│       ├── mcp_server.py             # MCP service implementation
│       └── signals.py                # Signal emission
└── tests/
    └── test_rule_activation.py
```

### MCP Server Interface

```python
# rule-library/src/rule_library/mcp_server.py
"""MCP server for rule projection (ADR-L-0004: CAP-0003)."""

from mcp.server import Server
from mcp.types import Tool, TextContent
from .loader import RuleLoader
from .activator import RuleActivator

app = Server("rule-library")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_rules",
            description="Get activated rules for a project/context",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Project name"},
                    "context": {"type": "string", "description": "Context (e.g., 'scope-resolution')"},
                    "rule_type": {"type": "string", "enum": ["traceability", "quality", "all"]}
                },
                "required": ["project"]
            }
        ),
        Tool(
            name="validate_decorator",
            description="Validate an ADR decorator reference",
            inputSchema={
                "type": "object",
                "properties": {
                    "decorator_type": {"type": "string"},
                    "reference_id": {"type": "string"},
                    "project": {"type": "string"}
                },
                "required": ["decorator_type", "reference_id", "project"]
            }
        ),
        Tool(
            name="check_traceability",
            description="Check bidirectional traceability for code",
            inputSchema={
                "type": "object",
                "properties": {
                    "code_path": {"type": "string"},
                    "adr_directory": {"type": "string"},
                    "project": {"type": "string"}
                },
                "required": ["code_path", "project"]
            }
        ),
        Tool(
            name="emit_signal",
            description="Emit compliance signal",
            inputSchema={
                "type": "object",
                "properties": {
                    "signal_type": {"type": "string"},
                    "metadata": {"type": "object"}
                },
                "required": ["signal_type"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    loader = RuleLoader()
    activator = RuleActivator()
    
    if name == "get_rules":
        # Load rules for project
        rules = loader.load_rules_for_project(
            arguments["project"],
            context=arguments.get("context"),
            rule_type=arguments.get("rule_type", "all")
        )
        
        # Activate rules for context
        activated = activator.activate(rules, arguments.get("context"))
        
        return [TextContent(
            type="text",
            text=yaml.dump({"rules": activated})
        )]
    
    elif name == "validate_decorator":
        # Validate decorator reference
        is_valid = await validate_decorator_reference(
            arguments["decorator_type"],
            arguments["reference_id"],
            arguments["project"]
        )
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "valid": is_valid,
                "reference": arguments["reference_id"]
            })
        )]
    
    elif name == "check_traceability":
        # Check bidirectional traceability
        result = await check_code_traceability(
            arguments["code_path"],
            arguments.get("adr_directory"),
            arguments["project"]
        )
        
        return [TextContent(
            type="text",
            text=json.dumps(result)
        )]
    
    elif name == "emit_signal":
        # Emit compliance signal
        signal_id = emit_compliance_signal(
            arguments["signal_type"],
            arguments.get("metadata", {})
        )
        
        return [TextContent(
            type="text",
            text=json.dumps({"signal_id": signal_id})
        )]
```

## Integration with Rules & Signal Service

### Rules & Signal Service Responsibilities

**NOT part of this project** - separate future service that:

1. **Parses ADRs** from multiple projects
2. **Generates enforcement rules** from invariants
3. **Generates signals** for capability implementation
4. **Publishes rules** to rule-library
5. **Monitors compliance** across projects
6. **Detects conflicts** between ADRs

### Rule Generation Example

**Input** (ADR invariant):
```yaml
# ADR-L-0002
invariants:
  - id: INV-0018
    statement: "Scope resolution MUST NOT traverse above workspace root"
    enforcement_level: must
    rationale: "Security and performance"
```

**Output** (Generated rule):
```yaml
# Generated by Rules & Signal Service
rule_id: RULE-INV-0018
generated_from:
  adr: ADR-L-0002
  invariant: INV-0018
  project: adr-architecture-kit
generated_date: 2026-03-08T10:00:00Z

enforcement:
  level: must
  type: runtime_validation
  
decorator_requirement:
  decorator: enforces_invariant
  reference: INV-0018
  applies_to:
    - component: COMP-0001
      methods: ["resolve", "_find_project_root", "_is_workspace_boundary"]

validation_logic:
  must_contain:
    - boundary_check: true
    - exception_on_violation: true
  
  code_patterns:
    - pattern: "if.*boundary.*raise"
      description: "Must raise exception on boundary violation"

signals:
  on_success:
    signal: boundary_enforced
    metadata:
      path: "{{path}}"
      boundary_type: "{{boundary}}"
  
  on_violation:
    signal: boundary_violated
    severity: critical
    metadata:
      path: "{{path}}"
      attempted_traversal: "{{target}}"
```

## Rule Library Activation

### Context-Aware Rule Activation

```python
# rule-library/src/rule_library/activator.py
"""Activate rules for specific contexts (ADR-L-0004)."""

class RuleActivator:
    """Activate rules based on context."""
    
    def activate(self, rules: List[Rule], context: Optional[str] = None) -> List[Rule]:
        """Activate rules for context.
        
        Args:
            rules: All available rules
            context: Context filter (e.g., "scope-resolution", "validation")
        
        Returns:
            Activated rules applicable to context
        """
        if not context:
            return rules
        
        activated = []
        for rule in rules:
            if self._applies_to_context(rule, context):
                activated.append(rule)
        
        return activated
    
    def _applies_to_context(self, rule: Rule, context: str) -> bool:
        """Check if rule applies to context."""
        # Check rule metadata for context tags
        if hasattr(rule, 'contexts'):
            return context in rule.contexts
        
        # Check component associations
        if hasattr(rule, 'applies_to'):
            for target in rule.applies_to:
                if context in target.get('contexts', []):
                    return True
        
        return True  # Default: all rules apply
```

## Consumer Workflow

### For Consumer Projects (e.g., ste-runtime)

#### Step 1: Install Dependencies

```bash
pip install adr-architecture-kit[decorators]
# Includes decorator library
```

#### Step 2: Annotate Code

```python
from adr_kit.decorators import implements_adr, enforces_invariant

@implements_adr("adr-architecture-kit:ADR-L-0002")  # Cross-project reference!
@enforces_invariant("adr-architecture-kit:INV-0018")
class MyComponent:
    """Component that follows adr-architecture-kit patterns."""
    pass
```

#### Step 3: Verify Traceability

```bash
# Query rule-library for rules
adr-verify get-rules --project adr-architecture-kit --output rules.yaml

# Verify code against rules
adr-verify check-traceability \
  --code src/ \
  --rules rules.yaml \
  --emit-signals
```

#### Step 4: CI/CD Enforcement

```yaml
# .github/workflows/governance.yml
- name: Verify ADR Traceability
  run: |
    # Get rules from rule-library MCP service
    adr-verify get-rules --project adr-architecture-kit --mcp
    
    # Verify code compliance
    adr-verify check-traceability --strict
    
    # Emit compliance signals
    adr-verify emit-signals
```

## Cross-Project Policy Propagation

### Scenario: Shared Architectural Standards

**Project A** (adr-architecture-kit) defines:
```yaml
# ADR-L-0002
invariants:
  - id: INV-0015
    statement: "Project scope resolution MUST use marker hierarchy"
    enforcement_level: must
```

**Rules & Signal Service** generates rule:
```yaml
rule_id: RULE-INV-0015
source: adr-architecture-kit:ADR-L-0002:INV-0015
enforcement_level: must
```

**Rule Library** projects rule via MCP:
```python
# Available to all consumers
rules = mcp.get_rules("adr-architecture-kit")
```

**Project B** (ste-runtime) consumes rule:
```python
# ste-runtime can follow adr-architecture-kit's patterns
@implements_adr("adr-architecture-kit:ADR-L-0002")
@enforces_invariant("adr-architecture-kit:INV-0015")
class MyConfigLoader:
    """Follows adr-architecture-kit scope resolution pattern."""
    pass
```

**Verification** ensures compliance:
```bash
adr-verify check-traceability --project ste-runtime
# ✓ MyConfigLoader follows adr-architecture-kit:INV-0015
# ✓ Policy propagation verified
```

## Implementation Phases

### Phase 1: Decorator Library (Immediate)
- **ADR-P-0004**: Physical ADR for decorator implementation
- Create `adr_kit.decorators` module
- Implement core decorators
- Add to adr-architecture-kit

### Phase 2: Rule Library Sub-Module (Near-term)
- **ADR-P-0005**: Physical ADR for rule-library
- Create `rule-library/` sub-module
- File-based rule loading
- Basic MCP server
- Independent package

### Phase 3: Verification System (Near-term)
- **ADR-P-0006**: Physical ADR for verification
- Bidirectional traceability checker
- AST-based decorator extraction
- CI/CD integration

### Phase 4: RECON Integration (Medium-term)
- **ste-runtime ADR**: RECON decorator extraction
- Add decorator metadata to AI-DOC slices
- Enable graph queries by ADR
- Semantic traceability

### Phase 5: Rules & Signal Service (Long-term)
- **Separate service** (not in this project)
- Parse ADRs and generate rules
- Publish to rule-library
- Monitor cross-project compliance
- Detect policy conflicts

## Benefits

### For This Project (adr-architecture-kit)

- ✅ **Provable correctness**: Code provably implements ADRs
- ✅ **Drift detection**: Automatic detection of divergence
- ✅ **Living documentation**: Code IS the architecture
- ✅ **AI understanding**: Agents know why code exists

### For Consumer Projects (ste-runtime, etc.)

- ✅ **Policy consumption**: Receive architectural standards via MCP
- ✅ **Compliance verification**: Automated checking
- ✅ **Cross-project consistency**: Follow shared patterns
- ✅ **Traceability**: Link code to upstream ADRs

### For the Ecosystem

- ✅ **Policy propagation**: Decisions flow across projects
- ✅ **Governance at scale**: Automated enforcement
- ✅ **Architectural consistency**: Shared standards
- ✅ **Audit trail**: Provable compliance chain

## Conclusion

This multi-tier architecture transforms ADRs from **documentation** into **enforceable policy** that propagates across projects:

1. **Projects define** architecture (ADRs)
2. **Rules & Signal Service generates** enforcement rules
3. **Rule Library projects** rules via MCP
4. **Consumers enforce** via decorators + verification
5. **System verifies** compliance automatically

This is **true architectural governance** - decisions become executable policy.
