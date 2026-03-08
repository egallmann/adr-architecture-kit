# ADR-to-Code Traceability Design

**Authority**: ADR-L-0004 - ADR-to-Code Traceability via Decorators

## Vision

Create **bidirectional, machine-verifiable traceability** between architecture decisions (ADRs) and implementation (code) using Python decorators.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ADR Architecture Kit                      │
│  ┌────────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │   Decorators   │  │  Verification   │  │  Rule Library │ │
│  │   @implements  │→ │   Bidirectional │← │  Traceability │ │
│  │   _adr()       │  │   Checker       │  │  Rules        │ │
│  └────────────────┘  └─────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │    ste-runtime      │
                    │  ┌───────────────┐  │
                    │  │  RECON        │  │
                    │  │  Extract      │  │
                    │  │  Decorators   │  │
                    │  └───────────────┘  │
                    └─────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │   Semantic Graph    │
                    │  Code ←→ ADR Links  │
                    └─────────────────────┘
```

## Component 1: Decorator Library

### Module: `adr_kit.decorators`

```python
"""ADR traceability decorators (ADR-L-0004: CAP-0001)."""

from functools import wraps
from typing import Callable, List, Optional, Any
import inspect


class ADRTraceability:
    """Metadata container for ADR traceability."""
    
    def __init__(self):
        self.implements_adrs: List[str] = []
        self.enforces_invariants: List[str] = []
        self.implements_capabilities: List[str] = []
        self.implements_components: List[str] = []
        self.rationale: Optional[str] = None


def implements_adr(*adr_ids: str, rationale: Optional[str] = None):
    """Declare that this code implements specific ADR(s).
    
    Args:
        *adr_ids: ADR identifiers (e.g., "ADR-L-0002", "ADR-P-0003")
        rationale: Optional explanation of how this implements the ADR
    
    Example:
        @implements_adr("ADR-L-0002", "ADR-P-0003")
        class ProjectScopeResolver:
            pass
    
    Authority: ADR-L-0004 DEC-0001
    """
    def decorator(target: Any) -> Any:
        if not hasattr(target, '__adr_traceability__'):
            target.__adr_traceability__ = ADRTraceability()
        
        target.__adr_traceability__.implements_adrs.extend(adr_ids)
        if rationale:
            target.__adr_traceability__.rationale = rationale
        
        return target
    
    return decorator


def enforces_invariant(*inv_ids: str):
    """Declare that this code enforces specific invariant(s).
    
    Args:
        *inv_ids: Invariant identifiers (e.g., "INV-0015", "INV-0018")
    
    Example:
        @enforces_invariant("INV-0018")
        def _is_workspace_boundary(self, path: Path) -> bool:
            # Enforcement logic here
            pass
    
    Authority: ADR-L-0004 DEC-0001
    """
    def decorator(target: Any) -> Any:
        if not hasattr(target, '__adr_traceability__'):
            target.__adr_traceability__ = ADRTraceability()
        
        target.__adr_traceability__.enforces_invariants.extend(inv_ids)
        return target
    
    return decorator


def implements_capability(cap_id: str):
    """Declare that this code implements a specific capability.
    
    Args:
        cap_id: Capability identifier (e.g., "CAP-0001")
    
    Example:
        @implements_capability("CAP-0001")
        def resolve(self, start_dir: Optional[Path] = None) -> ProjectScope:
            pass
    
    Authority: ADR-L-0004 DEC-0001
    """
    def decorator(target: Any) -> Any:
        if not hasattr(target, '__adr_traceability__'):
            target.__adr_traceability__ = ADRTraceability()
        
        target.__adr_traceability__.implements_capabilities.append(cap_id)
        return target
    
    return decorator


def implements_component(comp_id: str):
    """Declare that this code implements a specific component.
    
    Args:
        comp_id: Component identifier (e.g., "COMP-0001")
    
    Example:
        @implements_component("COMP-0001")
        class ProjectScopeResolver:
            pass
    
    Authority: ADR-L-0004 DEC-0001
    """
    def decorator(target: Any) -> Any:
        if not hasattr(target, '__adr_traceability__'):
            target.__adr_traceability__ = ADRTraceability()
        
        target.__adr_traceability__.implements_components.append(comp_id)
        return target
    
    return decorator


def get_traceability(target: Any) -> Optional[ADRTraceability]:
    """Extract traceability metadata from decorated object.
    
    Args:
        target: Class, function, or method to inspect
    
    Returns:
        ADRTraceability metadata or None if not decorated
    """
    return getattr(target, '__adr_traceability__', None)
```

### Usage Example

```python
from pathlib import Path
from typing import Optional
from adr_kit.decorators import (
    implements_adr,
    implements_component,
    implements_capability,
    enforces_invariant
)

@implements_adr("ADR-L-0002", "ADR-P-0003")
@implements_component("COMP-0001")
class ProjectScopeResolver:
    """Resolve project scope for ADR operations.
    
    Authority: ADR-L-0002 CAP-0001, ADR-P-0003 COMP-0001
    """
    
    @implements_capability("CAP-0001")
    @enforces_invariant("INV-0015")
    def resolve(self, start_dir: Optional[Path] = None) -> ProjectScope:
        """Auto-detect project boundaries.
        
        Implements: ADR-L-0002 CAP-0001 (Automatic Project Scope Detection)
        Enforces: INV-0015 (Marker hierarchy)
        """
        # Implementation...
        pass
    
    @enforces_invariant("INV-0018")
    def _is_workspace_boundary(self, path: Path) -> bool:
        """Check if path is workspace boundary.
        
        Enforces: INV-0018 (Workspace boundary enforcement)
        """
        # Boundary enforcement logic
        pass
```

## Component 2: Rule Library Sub-Module

### Structure

```
rule-library/
├── README.md
├── pyproject.toml
├── rules/
│   ├── traceability/
│   │   ├── decorator-requirements.yaml
│   │   ├── verification-rules.yaml
│   │   └── enforcement-levels.yaml
│   └── quality/
│       ├── coverage-rules.yaml
│       └── testing-rules.yaml
├── src/
│   └── rule_library/
│       ├── __init__.py
│       ├── loader.py          # File-based rule loading
│       ├── evaluator.py       # Rule evaluation logic
│       └── mcp_server.py      # MCP-based rule serving
└── tests/
    └── test_rule_loading.py
```

### Rule Schema

```yaml
# rules/traceability/decorator-requirements.yaml
schema_version: "1.0"
type: traceability_rules
authority: "ADR-L-0004"

rules:
  - id: RULE-001
    name: "Public Classes Must Declare ADR Authority"
    description: |
      All public classes (not starting with _) must be decorated with
      @implements_adr referencing the ADR(s) that justify their existence.
    
    applies_to:
      - type: class
        visibility: public
    
    requires:
      decorator: implements_adr
      min_references: 1
    
    enforcement_level: should
    rationale: "INV-0027: Public APIs need architectural justification"
    
    violation_message: |
      Class {class_name} is public but has no @implements_adr decorator.
      Add @implements_adr("ADR-X-NNNN") to declare architectural authority.
  
  - id: RULE-002
    name: "Decorator References Must Be Valid"
    description: |
      All ADR references in decorators must point to existing, accepted ADRs.
    
    applies_to:
      - decorator: implements_adr
      - decorator: enforces_invariant
      - decorator: implements_capability
      - decorator: implements_component
    
    validation:
      - check: adr_exists
      - check: adr_status_accepted
    
    enforcement_level: must
    rationale: "INV-0028: Cannot reference non-existent ADRs"
    
    violation_message: |
      {decorator} references {reference_id} which does not exist or is not accepted.
  
  - id: RULE-003
    name: "Invariant Enforcement Must Have Logic"
    description: |
      Code decorated with @enforces_invariant must contain validation logic
      that actually enforces the invariant.
    
    applies_to:
      - decorator: enforces_invariant
    
    validation:
      - check: has_validation_logic
      - check: raises_on_violation
    
    enforcement_level: must
    rationale: "INV-0030: Claiming enforcement without implementation is drift"
    
    violation_message: |
      {target} claims to enforce {invariant_id} but contains no validation logic.
```

### Rule Loader

```python
# src/rule_library/loader.py
"""Load traceability rules from files (ADR-L-0004: CAP-0003)."""

from pathlib import Path
from typing import List, Dict, Any
import yaml


class TraceabilityRule:
    """Traceability rule definition."""
    
    def __init__(self, rule_data: Dict[str, Any]):
        self.id = rule_data['id']
        self.name = rule_data['name']
        self.description = rule_data['description']
        self.applies_to = rule_data['applies_to']
        self.enforcement_level = rule_data['enforcement_level']
        self.rationale = rule_data['rationale']
        self.violation_message = rule_data['violation_message']
        self.requires = rule_data.get('requires')
        self.validation = rule_data.get('validation', [])


class RuleLoader:
    """Load rules from file system (ADR-L-0004: INV-0031)."""
    
    def __init__(self, rules_dir: Path):
        self.rules_dir = Path(rules_dir)
    
    def load_traceability_rules(self) -> List[TraceabilityRule]:
        """Load all traceability rules."""
        rules = []
        
        rules_file = self.rules_dir / "traceability" / "decorator-requirements.yaml"
        if rules_file.exists():
            with open(rules_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                for rule_data in data.get('rules', []):
                    rules.append(TraceabilityRule(rule_data))
        
        return rules
```

## Component 3: Verification System

### Bidirectional Checker

```python
# src/adr_kit/verification/traceability_checker.py
"""Bidirectional ADR traceability verification (ADR-L-0004: CAP-0002)."""

import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

from ..decorators import get_traceability
from ..parser import ADRParser
from ..models import LogicalADR, PhysicalADR


@dataclass
class TraceabilityViolation:
    """Traceability violation."""
    
    type: str  # "orphaned_code", "phantom_declaration", "invalid_reference"
    severity: str  # "error", "warning"
    location: str  # File path or ADR ID
    message: str
    rule_id: Optional[str] = None


class TraceabilityChecker:
    """Verify bidirectional ADR-to-code traceability (ADR-L-0004)."""
    
    def __init__(self, project_root: Path, adr_dir: Path):
        self.project_root = Path(project_root)
        self.adr_dir = Path(adr_dir)
        self.parser = ADRParser()
    
    def check_forward_traceability(self) -> List[TraceabilityViolation]:
        """Check ADR → Code traceability (INV-0029).
        
        Verify that ADRs declaring implementation_identifiers have
        corresponding code with matching decorators.
        """
        violations = []
        
        # Parse all ADRs
        physical_adrs = self._load_physical_adrs()
        
        for adr in physical_adrs:
            for comp in adr.component_specifications:
                if comp.implementation_identifiers:
                    for impl_id in comp.implementation_identifiers:
                        # Check if code exists
                        code_path = self.project_root / impl_id
                        if not code_path.exists():
                            violations.append(TraceabilityViolation(
                                type="phantom_declaration",
                                severity="error",
                                location=f"{adr.id} {comp.id}",
                                message=f"ADR declares {impl_id} but code not found",
                                rule_id="INV-0029"
                            ))
                            continue
                        
                        # Check if code has matching decorator
                        if not self._has_matching_decorator(code_path, adr.id, comp.id):
                            violations.append(TraceabilityViolation(
                                type="missing_decorator",
                                severity="warning",
                                location=impl_id,
                                message=f"Code exists but missing @implements_adr('{adr.id}')",
                                rule_id="INV-0029"
                            ))
        
        return violations
    
    def check_reverse_traceability(self) -> List[TraceabilityViolation]:
        """Check Code → ADR traceability (INV-0028).
        
        Verify that code decorators reference valid, accepted ADRs.
        """
        violations = []
        
        # Load all ADRs for validation
        valid_adrs = self._load_all_adr_ids()
        
        # Find all Python files
        for py_file in self.project_root.glob("**/*.py"):
            if self._should_skip(py_file):
                continue
            
            # Extract decorators
            decorators = self._extract_decorators(py_file)
            
            for decorator in decorators:
                if decorator.type == "implements_adr":
                    for adr_id in decorator.references:
                        if adr_id not in valid_adrs:
                            violations.append(TraceabilityViolation(
                                type="invalid_reference",
                                severity="error",
                                location=f"{py_file}:{decorator.line}",
                                message=f"References non-existent ADR: {adr_id}",
                                rule_id="INV-0028"
                            ))
        
        return violations
    
    def check_orphaned_code(self) -> List[TraceabilityViolation]:
        """Find code with no ADR justification (INV-0027)."""
        violations = []
        
        for py_file in self.project_root.glob("**/*.py"):
            if self._should_skip(py_file):
                continue
            
            # Check public classes
            public_classes = self._find_public_classes(py_file)
            
            for cls in public_classes:
                if not cls.has_adr_decorator:
                    violations.append(TraceabilityViolation(
                        type="orphaned_code",
                        severity="warning",
                        location=f"{py_file}:{cls.line}",
                        message=f"Public class {cls.name} has no @implements_adr decorator",
                        rule_id="INV-0027"
                    ))
        
        return violations
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive traceability report."""
        forward = self.check_forward_traceability()
        reverse = self.check_reverse_traceability()
        orphaned = self.check_orphaned_code()
        
        all_violations = forward + reverse + orphaned
        
        return {
            "total_violations": len(all_violations),
            "errors": len([v for v in all_violations if v.severity == "error"]),
            "warnings": len([v for v in all_violations if v.severity == "warning"]),
            "forward_traceability": {
                "violations": len(forward),
                "details": [self._violation_to_dict(v) for v in forward]
            },
            "reverse_traceability": {
                "violations": len(reverse),
                "details": [self._violation_to_dict(v) for v in reverse]
            },
            "orphaned_code": {
                "violations": len(orphaned),
                "details": [self._violation_to_dict(v) for v in orphaned]
            }
        }
```

## Component 4: MCP Integration (Future)

### MCP Server for Rule Delivery

```python
# rule-library/src/rule_library/mcp_server.py
"""MCP server for rule delivery (ADR-L-0004: INV-0032)."""

from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("rule-library")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_traceability_rules",
            description="Get ADR traceability rules for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "rule_type": {"type": "string", "enum": ["traceability", "quality", "all"]}
                }
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
                    "adr_directory": {"type": "string"}
                },
                "required": ["decorator_type", "reference_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_traceability_rules":
        # Load and return rules
        rules = load_rules(arguments.get("project_name"), arguments.get("rule_type"))
        return [TextContent(type="text", text=yaml.dump(rules))]
    
    elif name == "validate_decorator":
        # Validate decorator reference
        is_valid = validate_reference(
            arguments["decorator_type"],
            arguments["reference_id"],
            arguments.get("adr_directory")
        )
        return [TextContent(type="text", text=f"Valid: {is_valid}")]
```

## Usage Workflow

### 1. Annotate Code

```python
@implements_adr("ADR-L-0002", "ADR-P-0003")
@implements_component("COMP-0001")
class ProjectScopeResolver:
    pass
```

### 2. Run Verification

```bash
# Check traceability
adr verify-traceability

# Output:
# Checking forward traceability (ADR → Code)...
# ✓ ADR-P-0003 COMP-0001 → src/adr_kit/scope/resolver.py
#
# Checking reverse traceability (Code → ADR)...
# ✓ ProjectScopeResolver @implements_adr("ADR-L-0002") → Valid
# ✓ ProjectScopeResolver @implements_adr("ADR-P-0003") → Valid
#
# Checking for orphaned code...
# ⚠ ManifestGenerator has no @implements_adr decorator
#
# Traceability: 95% (19/20 verified)
# Errors: 0
# Warnings: 1
```

### 3. CI/CD Enforcement

```yaml
# .github/workflows/adr-governance.yml
- name: Verify ADR Traceability
  run: |
    adr verify-traceability --strict
    # Fails if errors > 0
```

## Benefits

1. **Machine-Verifiable**: Automated verification of ADR implementation
2. **Drift Detection**: Immediate detection when code diverges from ADRs
3. **Audit Trail**: Provable link from code to architectural authority
4. **AI Understanding**: AI agents can trace code to ADR rationale
5. **Embodied Design**: Code becomes living documentation of architecture
6. **Governance**: Enforceable traceability requirements

## Next Steps

1. **ADR-P-0004**: Physical ADR for decorator library implementation
2. **ADR-P-0005**: Physical ADR for rule library sub-module
3. **ADR-P-0006**: Physical ADR for verification system
4. **ste-runtime ADR**: RECON integration for decorator extraction
5. **rule-library ADR**: MCP server for rule delivery
