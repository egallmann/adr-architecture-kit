# Methodology as Project Authority Declaration

**Date**: 2026-03-08  
**Question**: Should methodology be considered a project declaration like other project authority metadata?  
**Answer**: **YES** - Methodology is project-level authority

## Rationale

Development methodology is **project authority** because it:

1. **Governs how the project evolves** - like automation permissions and compliance requirements
2. **Affects all contributors** - everyone must follow the methodology
3. **Determines quality standards** - defines what "done" means
4. **Enables automation** - AI agents need to know the methodology to contribute correctly
5. **Is stable across the project** - doesn't change per-feature or per-file

## Where It Belongs

### ✅ PROJECT.yaml (Project Authority)

Methodology belongs in `PROJECT.yaml` alongside:
- **Ownership**: Who has authority over the project
- **Automation**: What agents are allowed to do
- **Compliance**: What standards must be met
- **Integrations**: How the project connects to systems

### ❌ Not in ADRs (Decision Records)

ADRs document **why** we chose TDD (ADR-L-0003 DEC-0005), but `PROJECT.yaml` declares **that we use it** as project authority.

## Implementation

### Schema Extension

**File**: `schema/v1.0/project-metadata.schema.json`

Added `development_methodology` field:

```json
{
  "development_methodology": {
    "type": "object",
    "properties": {
      "approach": {
        "enum": ["test-driven-development", "behavior-driven-development", "test-after", "exploratory"]
      },
      "testing_framework": {"type": "string"},
      "coverage_target": {"type": "number", "minimum": 0, "maximum": 100},
      "quality_gates": {"type": "array"},
      "tdd_cycle": {"enum": ["red-green-refactor", "test-first", "test-after"]},
      "rationale": {"type": "string"},
      "authority": {"type": "string"}
    }
  }
}
```

### Pydantic Model

**File**: `src/adr_kit/models/project_metadata.py`

Added `DevelopmentMethodology` class:

```python
class DevelopmentMethodology(BaseModel):
    """Development methodology and quality practices (project authority)."""
    
    approach: str
    testing_framework: Optional[str] = None
    coverage_target: Optional[int] = Field(None, ge=0, le=100)
    quality_gates: Optional[List[str]] = None
    tdd_cycle: Optional[str] = None
    rationale: Optional[str] = None
    authority: Optional[str] = None
```

### PROJECT.yaml Declaration

**File**: `PROJECT.yaml`

```yaml
development_methodology:
  approach: "test-driven-development"
  testing_framework: "pytest"
  coverage_target: 80
  quality_gates:
    - schema_validation
    - test_suite_passing
    - type_checking
    - linting
  tdd_cycle: "red-green-refactor"
  rationale: |
    TDD is architecturally aligned with STE principles (SYS-2, SYS-4, PRIME-1).
    As a governance tool that validates architecture decisions, provable
    correctness is required. Tests serve as executable specifications.
  authority: "ADR-L-0003 DEC-0005, ADR-P-0003 IMPL-0001"
```

## Why This Matters

### For Human Contributors

When a developer joins the project, `PROJECT.yaml` tells them:
- **Who** owns the project (ownership)
- **How** to develop (development_methodology)
- **What** standards to meet (compliance)
- **What** automation is allowed (automation)

### For AI Agents

When an AI agent contributes, `PROJECT.yaml` provides:
- **Methodology constraints**: Must write tests first (TDD)
- **Quality gates**: Must pass schema validation, tests, linting
- **Coverage requirements**: Must maintain 80% coverage
- **Authority reference**: Can read ADR-L-0003 for detailed rationale

### For Governance

`PROJECT.yaml` is **machine-readable project authority**:
- CI/CD can enforce methodology compliance
- Code review tools can check against quality gates
- Automation can verify coverage targets
- Audits can trace methodology to authoritative ADRs

## Comparison with Other Authority

| Authority Type | Location | Purpose |
|----------------|----------|---------|
| **Ownership** | PROJECT.yaml | Who has decision authority |
| **Automation** | PROJECT.yaml | What agents can do |
| **Methodology** | PROJECT.yaml | How development happens |
| **Compliance** | PROJECT.yaml | What standards apply |
| **Architecture** | ADRs | Why decisions were made |

## Pattern: Authority vs. Rationale

### PROJECT.yaml: Authority (WHAT)
```yaml
development_methodology:
  approach: "test-driven-development"
  coverage_target: 80
  authority: "ADR-L-0003 DEC-0005"
```

**Declares**: "This project uses TDD with 80% coverage"

### ADR-L-0003: Rationale (WHY)
```yaml
decisions:
  - id: DEC-0005
    title: Adopt Test-Driven Development (TDD) Methodology
    rationale: |
      TDD is architecturally aligned with STE principles...
```

**Explains**: "We chose TDD because..."

## Benefits

### 1. Single Source of Truth

Contributors know where to look for project methodology - it's in `PROJECT.yaml` alongside other project authority.

### 2. Machine-Readable

AI agents can parse `PROJECT.yaml` to understand:
- What methodology to follow
- What quality gates to meet
- What coverage to maintain

### 3. Traceable

The `authority` field links to ADRs explaining the decision, providing full traceability from declaration to rationale.

### 4. Enforceable

CI/CD can validate:
```python
# In CI pipeline
project = ProjectMetadata.parse_file('PROJECT.yaml')

if project.development_methodology.approach == 'test-driven-development':
    # Enforce TDD requirements
    check_tests_exist_for_new_code()
    check_coverage_meets_target(project.development_methodology.coverage_target)
```

### 5. Consistent Pattern

Follows same pattern as other project authority:
- `automation.comfort_level` → declares automation boundaries
- `compliance.security_level` → declares security requirements
- `development_methodology.approach` → declares development approach

## Example: Multi-Project Workspace

### Workspace Root (adr-architecture-kit)
```yaml
# PROJECT.yaml
development_methodology:
  approach: "test-driven-development"
  coverage_target: 80
  authority: "ADR-L-0003 DEC-0005"
```

### Sub-Module (ste-runtime)
```yaml
# ste-runtime/PROJECT.yaml
development_methodology:
  approach: "test-driven-development"
  coverage_target: 85  # Higher for runtime system
  authority: "ADR-L-0008"  # ste-runtime's own testing ADR
```

Each scope declares its own methodology as project authority.

## Validation

Validate PROJECT.yaml:

```bash
python validate_project.py
```

Output:
```
PROJECT.yaml is valid

Project: adr-architecture-kit
Type: library

Development Methodology:
  Approach: test-driven-development
  Framework: pytest
  Coverage Target: 80%
  TDD Cycle: red-green-refactor
  Quality Gates: schema_validation, test_suite_passing, type_checking, linting
  Authority: ADR-L-0003 DEC-0005, ADR-P-0003 IMPL-0001
```

## Conclusion

**Methodology IS project authority** and belongs in `PROJECT.yaml` because:

- ✅ It governs project evolution
- ✅ It affects all contributors
- ✅ It determines quality standards
- ✅ It enables AI agent compliance
- ✅ It follows the same pattern as other authority declarations

This provides a **machine-readable, traceable, enforceable** declaration of how the project is developed, consistent with STE principles of explicit, verifiable governance.
