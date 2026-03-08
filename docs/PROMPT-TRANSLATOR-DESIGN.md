# Prompt Translator Design

**Date**: 2026-03-08  
**Authority**: ADR-L-0005, ADR-P-0004  
**Purpose**: Automate implementation prompt generation from ADRs

---

## Vision

**Transform ADRs into executable AI instructions automatically.**

```
Physical ADR (YAML)
    ↓ parse
ComponentParser
    ↓ extract
ComponentSpec (structured data)
    ↓ render
PromptGenerator (Jinja2 templates)
    ↓ output
Implementation Prompts (markdown)
    ↓ execute
AI Agent (CODEX, Cursor, etc.)
    ↓ validate
Validation Checklist (generated)
```

---

## Architecture

### Component 1: ComponentParser (COMP-0005)

**Purpose**: Extract component specifications from Physical ADRs

**Input**: Physical ADR YAML file
```yaml
# ADR-P-0003
component_specifications:
  - id: COMP-0001
    name: Project Scope Resolver
    type: module
    responsibilities: [...]
    interfaces: [...]
    testing_requirements: [...]
```

**Output**: Structured ComponentSpec
```python
@dataclass
class ComponentSpec:
    id: str                              # COMP-0001
    name: str                            # Project Scope Resolver
    type: str                            # module
    description: str
    responsibilities: List[str]
    interfaces: List[InterfaceSpec]
    implementation_identifiers: List[str]
    dependencies: List[str]
    testing_requirements: List[str]
    related_invariants: List[InvariantRef]     # From Logical ADR
    related_capabilities: List[CapabilityRef]  # From Logical ADR
    implementation_decisions: List[ImplDecisionRef]
```

**Key Methods**:
```python
class ComponentParser:
    def parse_physical_adr(self, adr_path: Path) -> List[ComponentSpec]:
        """Parse Physical ADR and extract all components."""
        
    def load_logical_adr(self, logical_id: str) -> LogicalADR:
        """Load related Logical ADR for invariants/capabilities."""
        
    def extract_related_invariants(
        self, 
        component: ComponentSpec, 
        logical: LogicalADR
    ) -> List[InvariantRef]:
        """Find invariants relevant to this component."""
        # Match by keywords in component responsibilities
        # Match by explicit references in testing_requirements
```

### Component 2: PromptGenerator (COMP-0006)

**Purpose**: Render implementation prompts from templates

**Input**: ComponentSpec + Context
```python
component = ComponentSpec(id="COMP-0001", name="Project Scope Resolver", ...)
context = {
    "adr_id": "ADR-P-0003",
    "logical_adr_id": "ADR-L-0002",
    "target_agent": "codex",
    "methodology": "test-driven-development"
}
```

**Output**: Markdown prompt
```markdown
# Implementation Prompt: Project Scope Resolver (COMP-0001)

## Context
You are implementing the Project Scope Resolver for the ADR Architecture Kit...

## Constraints (MUST enforce)
**INV-0015**: Use this exact marker hierarchy...
**INV-0018**: MUST NOT traverse above workspace root...

## Component Specification
**File**: src/adr_kit/scope/resolver.py
...

## Test Requirements
Required tests:
1. test_explicit_scope_overrides_detection
...

## Implementation Strategy (TDD)
Red-Green-Refactor cycle:
...

## Validation Criteria
I will verify:
- ✅ All tests pass
- ✅ Marker hierarchy matches INV-0015
...
```

**Template Structure**:
```jinja2
{# implementation-prompt.md.jinja2 #}
# Implementation Prompt: {{ component.name }} ({{ component.id }})

## Context
You are implementing {{ component.name }} for {{ project_name }}.
{{ component.description }}

## Constraints (MUST enforce)
{% for invariant in component.related_invariants %}
**{{ invariant.id }}**: {{ invariant.statement }}
- Enforcement level: {{ invariant.enforcement_level }}
- Rationale: {{ invariant.rationale }}
{% endfor %}

## Component Specification ({{ component.id }})
**Type**: {{ component.type }}
**Files**: 
{% for file in component.implementation_identifiers %}
- {{ file }}
{% endfor %}

**Responsibilities**:
{% for resp in component.responsibilities %}
- {{ resp }}
{% endfor %}

**Interfaces**:
{% for interface in component.interfaces %}
### {{ interface.name }}
Type: {{ interface.type }}
{% if interface.methods %}
Methods:
{% for method in interface.methods %}
- `{{ method.signature }}`
  {{ method.description }}
{% endfor %}
{% endif %}
{% endfor %}

## Test Requirements
Required tests:
{% for test in component.testing_requirements %}
- {{ test }}
{% endfor %}

## Implementation Strategy
{% if methodology == "test-driven-development" %}
**Red-Green-Refactor Cycle** (per ADR-L-0003):
1. **Red**: Write failing test
2. **Green**: Implement to pass test
3. **Refactor**: Improve design
{% endif %}

## Dependencies
```python
{% for dep in component.dependencies %}
{{ dep }}
{% endfor %}
```

## Validation Criteria
I will verify:
{% for invariant in component.related_invariants %}
- ✅ {{ invariant.id }} enforced
{% endfor %}
{% for test in component.testing_requirements %}
- ✅ Test exists: {{ test }}
{% endfor %}
- ✅ All tests pass
- ✅ Type hints complete
- ✅ Docstrings present
```

### Component 3: CLI Command (COMP-0007)

**Command**: `adr generate-prompts`

**Usage**:
```bash
# Generate prompts for all components in Physical ADR
adr generate-prompts ADR-P-0003 --output prompts/

# Generate prompt for specific component
adr generate-prompts ADR-P-0003 --component COMP-0001 --output prompts/

# Generate for different target agent
adr generate-prompts ADR-P-0003 --target cursor --output prompts/

# Generate with execution plan
adr generate-prompts ADR-P-0003 --output prompts/ --with-plan
```

**Output Structure**:
```
prompts/
├── ADR-P-0003/
│   ├── COMP-0001-scope-resolver.md
│   ├── COMP-0002-manifest-generator.md
│   ├── COMP-0003-validator.md
│   ├── COMP-0004-cli.md
│   ├── validation-checklist.md
│   └── execution-plan.md
```

### Component 4: DependencyAnalyzer (COMP-0008)

**Purpose**: Determine implementation order

**Input**: List of ComponentSpecs
```python
components = [
    ComponentSpec(id="COMP-0001", dependencies=[]),
    ComponentSpec(id="COMP-0002", dependencies=["adr_kit.scope.ProjectScopeResolver"]),
    ComponentSpec(id="COMP-0003", dependencies=["adr_kit.scope.ProjectScopeResolver"]),
    ComponentSpec(id="COMP-0004", dependencies=["COMP-0002", "COMP-0003"])
]
```

**Output**: Execution plan
```markdown
# Execution Plan for ADR-P-0003

## Dependency Graph
```
COMP-0001 (Scope Resolver)
    ↓
COMP-0002 (Manifest Generator) ← Can parallelize
COMP-0003 (Validator)           ← Can parallelize
    ↓
COMP-0004 (CLI)
```

## Implementation Order

### Wave 1 (no dependencies)
- **COMP-0001**: Project Scope Resolver
  - File: `src/adr_kit/scope/resolver.py`
  - Prompt: `prompts/ADR-P-0003/COMP-0001-scope-resolver.md`

### Wave 2 (depends on Wave 1) - **Can parallelize**
- **COMP-0002**: Manifest Generator
  - File: `src/adr_kit/generators/manifest_generator.py`
  - Prompt: `prompts/ADR-P-0003/COMP-0002-manifest-generator.md`
  - Depends on: COMP-0001

- **COMP-0003**: ADR Validator
  - File: `src/adr_kit/validators/adr_validator.py`
  - Prompt: `prompts/ADR-P-0003/COMP-0003-validator.md`
  - Depends on: COMP-0001

### Wave 3 (depends on Wave 2)
- **COMP-0004**: CLI
  - File: `src/adr_kit/cli/main.py`
  - Prompt: `prompts/ADR-P-0003/COMP-0004-cli.md`
  - Depends on: COMP-0002, COMP-0003
```

---

## Implementation Example

### Input: ADR-P-0003

```yaml
# adrs/physical/ADR-P-0003-multi-scope-python-implementation.yaml
component_specifications:
  - id: COMP-0001
    name: Project Scope Resolver
    type: module
    responsibilities:
      - Detect project boundaries using marker files
      - Enforce workspace boundaries (INV-0018)
    interfaces:
      - name: ProjectScope
        type: dataclass
        fields:
          - root: Path
          - adr_dir: Path
          - marker: str
      - name: ProjectScopeResolver
        type: class
        methods:
          - resolve(start_dir: Path) -> ProjectScope
    testing_requirements:
      - test_explicit_scope_overrides_detection
      - test_marker_priority_order
      - test_stops_at_git_directory
```

### Output: Implementation Prompt

```markdown
# Implementation Prompt: Project Scope Resolver (COMP-0001)

**Authority**: ADR-P-0003 COMP-0001  
**Logical ADR**: ADR-L-0002  
**Target Agent**: CODEX

## Context
You are implementing the Project Scope Resolver for the ADR Architecture Kit.
This module detects project boundaries in a monorepo by searching for marker files.

## Constraints (MUST enforce)

**INV-0015** (from ADR-L-0002):
Use this exact marker hierarchy (highest to lowest priority):
1. Explicit `--scope` parameter (if provided)
2. `ste.config.json` in current or parent directories
3. `PROJECT.yaml` in current or parent directories
4. `pyproject.toml` (Python projects)
5. `package.json` (Node projects)
6. `.git` directory (repository root)

**INV-0018** (from ADR-L-0002):
MUST NOT traverse above workspace root. Stop at:
- First `.git` directory found
- System boundaries: `Users`, `Documents`, `home`, `/`

## Component Specification (COMP-0001)

**File**: `src/adr_kit/scope/resolver.py`

**Dataclass**: `ProjectScope`
```python
@dataclass(frozen=True)
class ProjectScope:
    root: Path              # Project root directory
    adr_dir: Path           # ADRs directory (root/adrs)
    marker: str             # Detection marker used
```

**Class**: `ProjectScopeResolver`

**Methods**:
1. `resolve(start_dir: Path = None) -> ProjectScope`
   - Auto-detect single scope from start_dir
   - Return ProjectScope with detected metadata

## Test Requirements

**File**: `tests/test_scope_resolver.py`

Required tests:
1. `test_explicit_scope_overrides_detection` - INV-0014
2. `test_marker_priority_order` - INV-0015 hierarchy
3. `test_stops_at_git_directory` - INV-0018 boundary

## Implementation Strategy (IMPL-0001: TDD)

**Red-Green-Refactor Cycle**:
1. **Red**: Write failing test for marker detection
2. **Green**: Implement `_find_project_root()` to pass
3. **Refactor**: Extract boundary checking
4. Continue for all methods...

## Dependencies
```python
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
```

## Validation Criteria

I will verify:
- ✅ All 3 tests pass
- ✅ Marker hierarchy matches INV-0015 exactly
- ✅ Workspace boundary enforcement (INV-0018)
- ✅ Type hints complete
- ✅ Docstrings present
```

---

## Template Design

### Prompt Template Sections

1. **Header**
   - Component name and ID
   - Authority (source ADR)
   - Target agent

2. **Context**
   - What is being built
   - Why it's needed
   - How it fits in the system

3. **Constraints**
   - All relevant invariants
   - Enforcement levels (MUST/SHOULD/MAY)
   - Rationale for each

4. **Component Specification**
   - Type (module, class, enhancement)
   - File paths
   - Responsibilities
   - Interfaces (classes, methods, parameters)
   - Return types

5. **Test Requirements**
   - Required test names
   - What each test verifies
   - Test file location

6. **Implementation Strategy**
   - Methodology (TDD, etc.)
   - Step-by-step guidance
   - Code patterns to follow

7. **Dependencies**
   - External packages
   - Internal modules
   - Import statements

8. **Validation Criteria**
   - Checklist of what will be verified
   - Success criteria
   - How correctness is determined

### Validation Checklist Template

```markdown
# Validation Checklist - {{ adr_id }}

## Component {{ component.id }}: {{ component.name }}

### Code Review
- [ ] File exists: {{ component.implementation_identifiers[0] }}
- [ ] Class/module structure matches spec
{% for interface in component.interfaces %}
- [ ] {{ interface.type }} exists: {{ interface.name }}
{% endfor %}

### Invariant Enforcement
{% for invariant in component.related_invariants %}
- [ ] **{{ invariant.id }}**: {{ invariant.statement }}
{% endfor %}

### Test Coverage
- [ ] File exists: tests/test_{{ component.name|slugify }}.py
{% for test in component.testing_requirements %}
- [ ] Test: {{ test }}
{% endfor %}
- [ ] All tests pass

### Integration Testing
- [ ] Works with real workspace
- [ ] Error messages clear
- [ ] Documentation complete
```

---

## Usage Workflow

### 1. Generate Prompts from ADR

```bash
# Generate all prompts for ADR-P-0003
adr generate-prompts ADR-P-0003 --output prompts/

# Output:
# ✓ Generated prompts/ADR-P-0003/COMP-0001-scope-resolver.md
# ✓ Generated prompts/ADR-P-0003/COMP-0002-manifest-generator.md
# ✓ Generated prompts/ADR-P-0003/COMP-0003-validator.md
# ✓ Generated prompts/ADR-P-0003/COMP-0004-cli.md
# ✓ Generated prompts/ADR-P-0003/validation-checklist.md
# ✓ Generated prompts/ADR-P-0003/execution-plan.md
```

### 2. Review Generated Prompts

```bash
# Review prompts before handing to AI
cat prompts/ADR-P-0003/COMP-0001-scope-resolver.md

# Verify:
# - All invariants included
# - Component spec complete
# - Test requirements clear
# - Validation criteria explicit
```

### 3. Execute with AI Agent

```bash
# Hand prompt to CODEX
# CODEX reads: prompts/ADR-P-0003/COMP-0001-scope-resolver.md
# CODEX implements following TDD methodology
# CODEX runs tests to verify
```

### 4. Validate Implementation

```bash
# Use generated checklist
# Check off each item systematically
# Report compliance status
```

---

## Self-Referential Bootstrap

**The prompt translator can generate prompts for itself!**

### Bootstrap Process

1. **Manual Phase** (current):
   - Hand-craft prompts for prompt translator (COMP-0005 through COMP-0008)
   - Implement prompt translator following manual prompts

2. **Automated Phase** (after implementation):
   - Use prompt translator to generate prompts for future components
   - Example: Generate prompts for decorator library from ADR-P-0005

3. **Self-Improvement Phase** (future):
   - Use prompt translator to generate prompts for enhancing itself
   - Example: Add new template sections, improve formatting

### Example: Generate Decorator Library Prompts

```bash
# After prompt translator is implemented
adr generate-prompts ADR-P-0005 --output prompts/

# Generates prompts for decorator library components
# Hand to CODEX for implementation
# Validate using generated checklist
```

---

## Prompt Quality Metrics

### Completeness
- ✅ All invariants from Logical ADR included
- ✅ All component specifications included
- ✅ All test requirements included
- ✅ All dependencies listed
- ✅ Validation criteria explicit

### Clarity
- ✅ Context explains what and why
- ✅ Constraints are explicit with enforcement levels
- ✅ Specifications are unambiguous
- ✅ Examples provided where helpful

### Traceability
- ✅ References source ADR ID
- ✅ References specific invariant IDs
- ✅ References component ID
- ✅ Links to related ADRs

### Executability
- ✅ Self-contained (no external references needed)
- ✅ Implementation strategy clear
- ✅ Success criteria measurable
- ✅ Validation criteria actionable

---

## Integration with Existing Tools

### With Manifest Generator
```python
# Prompt translator uses ADRParser (same as manifest generator)
from adr_kit.parser import ADRParser

parser = ADRParser()
physical_adr = parser.parse_physical_adr(adr_path)
```

### With Validator
```python
# Validation checklist references validator capabilities
# Generated checklist can be executed by validator

adr validate-implementation ADR-P-0003 --checklist prompts/validation-checklist.md
```

### With CLI
```python
# New CLI command added to existing CLI
@cli.command('generate-prompts')
def generate_prompts(adr_id, component, target, output):
    # Implementation...
```

---

## Example: Real Prompt Generation

### Input ADR
```yaml
# ADR-P-0004 (this ADR!)
component_specifications:
  - id: COMP-0005
    name: ADR Component Parser
    type: module
    interfaces:
      - name: ComponentParser
        type: class
        methods:
          - parse_physical_adr(adr_path: Path) -> List[ComponentSpec]
    testing_requirements:
      - test_parse_adr_p_0003
      - test_extract_components
```

### Generated Prompt
```markdown
# Implementation Prompt: ADR Component Parser (COMP-0005)

**Authority**: ADR-P-0004 COMP-0005
**Logical ADR**: ADR-L-0005

## Context
You are implementing the ADR Component Parser for the ADR Architecture Kit.
This module parses Physical ADRs to extract component specifications.

## Constraints (MUST enforce)
**INV-0027**: Generated prompts MUST include all invariants from source ADR
**INV-0028**: Generated prompts MUST include complete interface definitions
**INV-0032**: Prompt generator MUST be deterministic

## Component Specification (COMP-0005)
**File**: `src/adr_kit/prompts/parser.py`

**Class**: `ComponentParser`
**Methods**:
- `parse_physical_adr(adr_path: Path) -> List[ComponentSpec]`

## Test Requirements
Required tests:
1. `test_parse_adr_p_0003` - Parse real Physical ADR
2. `test_extract_components` - Extract all components

## Implementation Strategy (TDD)
1. **Red**: Write test for parsing ADR-P-0003
2. **Green**: Implement ComponentParser.parse_physical_adr()
3. **Refactor**: Extract component extraction logic

## Validation Criteria
- ✅ Parses ADR-P-0003 successfully
- ✅ Extracts all 4 components
- ✅ All tests pass
```

---

## Benefits

### For Architects
- ✅ Write ADRs, get prompts automatically
- ✅ No manual prompt crafting
- ✅ Consistent prompt quality
- ✅ Easy to update (change ADR → regenerate prompts)

### For AI Agents
- ✅ Receive complete specifications
- ✅ All constraints explicit
- ✅ Clear validation criteria
- ✅ Traceable to authority

### For Validation
- ✅ Automated checklist generation
- ✅ Verify against original ADR
- ✅ Systematic verification
- ✅ No missed requirements

### For Scale
- ✅ Works for any number of ADRs
- ✅ Works for any number of components
- ✅ Parallel prompt generation
- ✅ Automated implementation pipeline

---

## Next Steps

1. **Implement prompt translator** (COMP-0005 through COMP-0008)
2. **Test with ADR-P-0003** (generate prompts for multi-scope)
3. **Validate generated prompts** (compare to hand-crafted)
4. **Use for decorator library** (generate prompts for ADR-P-0005)
5. **Iterate on templates** based on AI agent feedback

---

**This transforms ADRs from passive specs into active AI instructions!**
