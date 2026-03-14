# CODEX Implementation Workflow

**Date**: 2026-03-08  
**Authority**: ADR-L-0005 (Prompt Translation), ADR-L-0003 (TDD)  
**Purpose**: Autonomous implementation workflow for AI agents

---

## Vision

**CODEX reads ADRs, generates its own plan, implements, and validates.**

```
Human: "Implement ADR-P-0004"
    ↓
CODEX: Reads ADR-P-0004 + ADR-L-0005
    ↓
CODEX: Generates implementation plan
    ↓
CODEX: Persists plan to .codex/plans/ADR-P-0004.md
    ↓
CODEX: Follows plan (TDD cycle)
    ↓
CODEX: Self-validates against ADR
    ↓
CODEX: Reports completion
    ↓
Cursor: Validates CODEX's work
```

---

## Command Interface

### Simple Command

```bash
# Implement a Physical ADR
codex implement ADR-P-0004

# CODEX:
# 1. Reads adrs/physical/ADR-P-0004-prompt-translator-implementation.yaml
# 2. Reads adrs/logical/ADR-L-0005-adr-to-prompt-translation.yaml
# 3. Generates implementation plan
# 4. Persists to .codex/plans/ADR-P-0004.md
# 5. Implements following plan (TDD)
# 6. Validates against ADR
# 7. Reports results
```

### With Options

```bash
# Implement specific component only
codex implement ADR-P-0004 --component COMP-0005

# Resume from existing plan
codex implement ADR-P-0004 --resume

# Generate plan only (no implementation)
codex implement ADR-P-0004 --plan-only

# Validate existing implementation
codex implement ADR-P-0004 --validate-only
```

---

## Implementation Plan Structure

### Plan File: `.codex/plans/ADR-P-0004.md`

```markdown
# Implementation Plan: ADR-P-0004

**Generated**: 2026-03-08 14:32:00  
**Status**: in_progress  
**Progress**: 2/4 components complete

## ADR Summary

**Logical**: ADR-L-0005 - ADR-to-Prompt Translation  
**Physical**: ADR-P-0004 - Prompt Translator Implementation

**Goal**: Automate generation of implementation prompts from ADRs

**Components**: 4 (COMP-0005 through COMP-0008)

## Invariants to Enforce

- [x] **INV-0027**: Include all invariants in prompts (must)
- [x] **INV-0028**: Include complete interface definitions (must)
- [x] **INV-0029**: Reference source ADR ID (must)
- [ ] **INV-0030**: Include test requirements (must)
- [ ] **INV-0032**: Deterministic generation (must)

## Execution Plan

### Wave 1: Foundation (no dependencies)

#### COMP-0005: ADR Component Parser
- **Status**: ✅ complete
- **Files**: 
  - src/adr_kit/prompts/__init__.py
  - src/adr_kit/prompts/parser.py
- **Tests**: tests/test_component_parser.py (5 tests, all passing)
- **Validated**: 2026-03-08 14:15:00

#### COMP-0008: Dependency Analyzer
- **Status**: ✅ complete
- **Files**: src/adr_kit/prompts/dependencies.py
- **Tests**: tests/test_dependency_analyzer.py (4 tests, all passing)
- **Validated**: 2026-03-08 14:20:00

### Wave 2: Generation (depends on Wave 1)

#### COMP-0006: Prompt Generator
- **Status**: 🔄 in_progress
- **Files**:
  - src/adr_kit/prompts/generator.py
  - src/adr_kit/prompts/templates/*.jinja2
- **Tests**: tests/test_prompt_generator.py (0/6 tests passing)
- **Current Step**: Implementing template rendering
- **Next**: Test deterministic generation (INV-0032)

### Wave 3: CLI (depends on Wave 2)

#### COMP-0007: Prompt CLI
- **Status**: ⏳ pending
- **Files**: src/adr_kit/cli/main.py (modify)
- **Tests**: tests/test_prompt_cli.py (not started)
- **Blocked by**: COMP-0006

## TDD Progress

### Red-Green-Refactor Cycles

**Cycle 1**: ComponentParser.parse_physical_adr()
- ✅ Red: test_parse_adr_p_0003 (failed)
- ✅ Green: Implemented parser (passed)
- ✅ Refactor: Extracted component extraction logic

**Cycle 2**: ComponentParser.load_logical_adr()
- ✅ Red: test_load_logical_adr (failed)
- ✅ Green: Implemented loader (passed)
- ✅ Refactor: Added caching

**Cycle 3**: ComponentParser.extract_related_invariants()
- ✅ Red: test_extract_related_invariants (failed)
- ✅ Green: Implemented extraction (passed)
- ✅ Refactor: Improved matching logic

**Cycle 4**: PromptGenerator.generate_implementation_prompt()
- 🔄 Red: test_generate_implementation_prompt (failing)
- ⏳ Green: Implementing template rendering
- ⏳ Refactor: Pending

## Issues Encountered

1. **Issue**: Template not found error
   - **Resolution**: Created templates/ directory, added __init__.py
   - **Status**: Resolved

2. **Issue**: Invariant matching too broad
   - **Resolution**: Added keyword filtering in extract_related_invariants()
   - **Status**: Resolved

## Next Actions

1. Complete PromptGenerator implementation
2. Write remaining tests for PromptGenerator
3. Implement CLI command
4. Run full test suite
5. Self-validate: Generate prompts for ADR-P-0004 itself
6. Report completion

## Validation Checklist

- [x] COMP-0005 implemented and tested
- [x] COMP-0008 implemented and tested
- [ ] COMP-0006 implemented and tested
- [ ] COMP-0007 implemented and tested
- [ ] All invariants enforced
- [ ] All tests passing (target: 20+ tests)
- [ ] CLI works from any directory
- [ ] Self-validation successful
```

---

## CODEX Workflow Steps

### Step 1: Read ADRs

```
CODEX reads:
1. adrs/physical/ADR-P-0004-prompt-translator-implementation.yaml
2. adrs/logical/ADR-L-0005-adr-to-prompt-translation.yaml
3. adrs/logical/ADR-L-0003-quality-assurance-and-testing-strategy.yaml (for TDD)
4. PROJECT.yaml (for methodology)
```

### Step 2: Generate Plan

```
CODEX analyzes:
- 4 components (COMP-0005 through COMP-0008)
- 5 invariants (INV-0027 through INV-0032)
- Dependencies between components
- Test requirements

CODEX generates:
- Execution order (waves)
- TDD cycles per component
- Validation checklist
- Success criteria
```

### Step 3: Persist Plan

```
CODEX writes:
- .codex/plans/ADR-P-0004.md (implementation plan)
- .codex/plans/ADR-P-0004-progress.json (machine-readable progress)
```

### Step 4: Execute Plan

```
For each component in execution order:
  1. Red: Write failing tests
  2. Green: Implement to pass tests
  3. Refactor: Improve design
  4. Update plan with progress
  5. Move to next component
```

### Step 5: Self-Validate

```
CODEX validates:
- All invariants enforced (check against ADR)
- All components implemented (check file existence)
- All tests passing (run pytest)
- All interfaces match spec (check signatures)

CODEX generates:
- Validation report
- Coverage report
- Compliance summary
```

### Step 6: Report Completion

```
CODEX reports:
- ✅ 4/4 components implemented
- ✅ 20/20 tests passing
- ✅ 5/5 invariants enforced
- ✅ Self-validation successful
- ⚠ 2 warnings (non-blocking)

Ready for Cursor validation.
```

---

## Plan Persistence Format

### Human-Readable: `.codex/plans/ADR-P-0004.md`

Markdown format (as shown above) for human review.

### Machine-Readable: `.codex/plans/ADR-P-0004-progress.json`

```json
{
  "adr_id": "ADR-P-0004",
  "logical_adr": "ADR-L-0005",
  "status": "in_progress",
  "started": "2026-03-08T14:00:00Z",
  "last_updated": "2026-03-08T14:30:00Z",
  "components": [
    {
      "id": "COMP-0005",
      "name": "ADR Component Parser",
      "status": "complete",
      "files_created": [
        "src/adr_kit/prompts/__init__.py",
        "src/adr_kit/prompts/parser.py"
      ],
      "tests_created": [
        "tests/test_component_parser.py"
      ],
      "tests_passing": 5,
      "tests_total": 5,
      "completed": "2026-03-08T14:15:00Z"
    },
    {
      "id": "COMP-0006",
      "name": "Prompt Generator",
      "status": "in_progress",
      "files_created": [
        "src/adr_kit/prompts/generator.py"
      ],
      "tests_created": [
        "tests/test_prompt_generator.py"
      ],
      "tests_passing": 2,
      "tests_total": 6,
      "current_step": "Implementing template rendering"
    }
  ],
  "invariants": [
    {"id": "INV-0027", "enforced": true},
    {"id": "INV-0028", "enforced": true},
    {"id": "INV-0029", "enforced": true},
    {"id": "INV-0030", "enforced": false, "status": "in_progress"},
    {"id": "INV-0032", "enforced": false, "status": "pending"}
  ],
  "test_summary": {
    "total": 20,
    "passing": 9,
    "failing": 0,
    "pending": 11
  }
}
```

---

## Command Implementation

### Script: `scripts/codex-implement.py`

```python
#!/usr/bin/env python3
"""
CODEX implementation workflow script.

Usage:
    python scripts/codex-implement.py ADR-P-0004
    python scripts/codex-implement.py ADR-P-0004 --component COMP-0005
    python scripts/codex-implement.py ADR-P-0004 --validate-only
"""

import click
from pathlib import Path
from adr_kit.parser import ADRParser
from adr_kit.prompts import ComponentParser, PromptGenerator

@click.command()
@click.argument('adr_id')
@click.option('--component', help='Specific component to implement')
@click.option('--plan-only', is_flag=True, help='Generate plan without implementing')
@click.option('--resume', is_flag=True, help='Resume from existing plan')
@click.option('--validate-only', is_flag=True, help='Validate existing implementation')
def implement(adr_id, component, plan_only, resume, validate_only):
    """
    Implement a Physical ADR with CODEX workflow.
    
    This command:
    1. Reads the Physical ADR
    2. Generates implementation plan
    3. Persists plan to .codex/plans/
    4. Provides structured guidance for CODEX
    """
    
    # Find Physical ADR
    adr_path = find_adr(adr_id)
    if not adr_path:
        click.echo(f"❌ ADR {adr_id} not found", err=True)
        return 1
    
    # Parse ADR
    parser = ComponentParser()
    components = parser.parse_physical_adr(adr_path)
    
    if component:
        components = [c for c in components if c.id == component]
    
    # Generate plan
    plan = generate_implementation_plan(components, adr_id)
    
    # Persist plan
    plan_dir = Path(".codex/plans")
    plan_dir.mkdir(parents=True, exist_ok=True)
    
    plan_path = plan_dir / f"{adr_id}.md"
    plan_path.write_text(plan)
    
    click.echo(f"✓ Generated implementation plan: {plan_path}")
    click.echo(f"✓ Components: {len(components)}")
    click.echo(f"✓ Invariants: {count_invariants(components)}")
    click.echo(f"✓ Tests required: {count_tests(components)}")
    click.echo()
    click.echo("📋 Plan contents:")
    click.echo(plan)
    click.echo()
    click.echo("🤖 Ready for CODEX implementation")
    click.echo(f"   CODEX should read: {plan_path}")

if __name__ == '__main__':
    implement()
```

### Usage

```bash
# Generate implementation plan for ADR-P-0004
python scripts/codex-implement.py ADR-P-0004

# Output:
# ✓ Generated implementation plan: .codex/plans/ADR-P-0004.md
# ✓ Components: 4
# ✓ Invariants: 5
# ✓ Tests required: 20+
# 
# 📋 Plan contents:
# [Shows the plan...]
# 
# 🤖 Ready for CODEX implementation
#    CODEX should read: .codex/plans/ADR-P-0004.md
```

---

## CODEX Instructions

### Instruction File: `.codex/INSTRUCTIONS.md`

```markdown
# CODEX Implementation Instructions

## Your Role

You are CODEX, an AI implementation agent. Your job is to implement Physical ADRs
following the specifications and constraints defined in the ADRs.

## Workflow

### 1. Read the Plan

When you receive a command like "Implement ADR-P-0004", you should:

1. Read `.codex/plans/ADR-P-0004.md` (implementation plan)
2. Read `adrs/physical/ADR-P-0004-*.yaml` (Physical ADR)
3. Read `adrs/logical/ADR-L-00XX-*.yaml` (related Logical ADR)
4. Read `PROJECT.yaml` (project authority, methodology)

### 2. Understand Constraints

Extract and internalize:
- **Invariants** (INV-*): MUST/SHOULD/MAY constraints
- **Capabilities** (CAP-*): What the system must be able to do
- **Components** (COMP-*): What to build
- **Implementation Decisions** (IMPL-*): How to build

### 3. Follow TDD Methodology

Per `PROJECT.yaml` and ADR-L-0003:

**Red-Green-Refactor Cycle**:
1. **Red**: Write failing test first
2. **Green**: Implement minimum code to pass
3. **Refactor**: Improve design while keeping tests green

**For each component**:
```
For each test requirement:
  1. Write test (Red)
  2. Run test (should fail)
  3. Implement feature (Green)
  4. Run test (should pass)
  5. Refactor if needed
  6. Update plan progress
```

### 4. Update Plan Progress

After completing each component:

1. Update `.codex/plans/ADR-P-0004.md`:
   - Mark component as complete
   - Update test counts
   - Note any issues

2. Update `.codex/plans/ADR-P-0004-progress.json`:
   - Set component status to "complete"
   - Update test counts
   - Update timestamp

### 5. Self-Validate

Before reporting completion:

1. **Run governance bundle**: `adr governance-checks`
2. **Check invariants**: Verify each INV-* is enforced
3. **Check interfaces**: Verify all methods exist with correct signatures
4. **Check files**: Verify all implementation_identifiers exist
5. **Check types**: Verify type hints complete
6. **Check docs**: Verify docstrings present
7. **Commit at the boundary**: Once the slice is verified and reviewable, create a commit before continuing

### 6. Report Completion

Generate completion report:

```markdown
# Implementation Report: ADR-P-0004

**Status**: ✅ Complete
**Completed**: 2026-03-08 15:45:00
**Duration**: 1h 45m

## Summary
- ✅ 4/4 components implemented
- ✅ 20/20 tests passing
- ✅ 5/5 invariants enforced
- ✅ All interfaces match specifications
- ✅ Type hints complete
- ✅ Documentation complete

## Components Implemented
- ✅ COMP-0005: ADR Component Parser (5 tests)
- ✅ COMP-0006: Prompt Generator (6 tests)
- ✅ COMP-0007: Prompt CLI (4 tests)
- ✅ COMP-0008: Dependency Analyzer (5 tests)

## Validation Results
- ✅ All invariants enforced
- ✅ All capabilities delivered
- ✅ TDD methodology followed
- ✅ Backward compatibility maintained

## Self-Validation Test
✅ Generated prompts for ADR-P-0004 itself
✅ Compared to bootstrap prompts
✅ Structural match confirmed

## Ready for Cursor Validation
Plan: .codex/plans/ADR-P-0004.md
Report: .codex/reports/ADR-P-0004-completion.md
```

---

## Example: CODEX Session

### Human Command
```
Implement ADR-P-0004
```

### CODEX Response
```
I'll implement ADR-P-0004 (Prompt Translator Implementation).

Let me start by reading the ADRs and generating an implementation plan.

[Reads ADR-P-0004]
[Reads ADR-L-0005]
[Reads PROJECT.yaml]

I see this requires:
- 4 components (COMP-0005 through COMP-0008)
- 5 invariants to enforce (INV-0027 through INV-0032)
- TDD methodology (Red-Green-Refactor)
- 20+ tests

Generating implementation plan...

✓ Plan generated: .codex/plans/ADR-P-0004.md

Execution order:
Wave 1: COMP-0005 (Parser), COMP-0008 (Dependencies) - Can parallelize
Wave 2: COMP-0006 (Generator) - Depends on Wave 1
Wave 3: COMP-0007 (CLI) - Depends on Wave 2

Starting implementation with TDD...

[Implements following the plan...]

✓ Implementation complete!
✓ 20/20 tests passing
✓ 5/5 invariants enforced
✓ Self-validation successful

Report: .codex/reports/ADR-P-0004-completion.md
```

### Human Response
```
Great! Let me validate your work.
```

### Cursor Validation
```
[Reads .codex/reports/ADR-P-0004-completion.md]
[Reads .codex/plans/ADR-P-0004.md]
[Runs validation checklist]

Validating against ADR-P-0004...

✅ COMP-0005: ComponentParser
   - All methods present
   - All tests passing
   - INV-0027, INV-0028, INV-0029 enforced

✅ COMP-0006: PromptGenerator
   - Templates exist
   - Deterministic generation (INV-0032)
   - All tests passing

✅ COMP-0007: CLI
   - Command works
   - Help text clear
   - All tests passing

✅ COMP-0008: DependencyAnalyzer
   - Topological sort correct
   - Circular detection works
   - All tests passing

✅ Overall: PASS
   - 20/20 tests passing
   - 5/5 invariants enforced
   - 4/4 components complete

Ready to commit!
```

---

## Plan Generation Algorithm

### Pseudo-code

```python
def generate_implementation_plan(adr_id: str) -> str:
    """Generate implementation plan from Physical ADR."""
    
    # 1. Parse Physical ADR
    physical = parse_physical_adr(adr_id)
    logical = load_logical_adr(physical.implements_logical[0])
    
    # 2. Extract components
    components = physical.component_specifications
    
    # 3. Analyze dependencies
    analyzer = DependencyAnalyzer()
    waves = analyzer.get_execution_order(components)
    
    # 4. Extract invariants
    invariants = logical.invariants
    
    # 5. Extract capabilities
    capabilities = logical.capabilities
    
    # 6. Build plan structure
    plan = {
        "adr_summary": {...},
        "invariants": invariants,
        "capabilities": capabilities,
        "execution_waves": waves,
        "tdd_cycles": generate_tdd_cycles(components),
        "validation_checklist": generate_checklist(components, invariants)
    }
    
    # 7. Render plan template
    return render_plan_template(plan)
```

---

## Directory Structure

```
.codex/
├── INSTRUCTIONS.md           # Instructions for CODEX
├── plans/                    # Implementation plans
│   ├── ADR-P-0004.md        # Human-readable plan
│   └── ADR-P-0004-progress.json  # Machine-readable progress
├── reports/                  # Completion reports
│   └── ADR-P-0004-completion.md
└── templates/                # Plan templates
    ├── implementation-plan.md.jinja2
    └── completion-report.md.jinja2
```

---

## Integration with Prompt Translator

Once the prompt translator is implemented, the workflow becomes:

```bash
# Option 1: Use script to generate plan
python scripts/codex-implement.py ADR-P-0005
# Generates plan in .codex/plans/ADR-P-0005.md
# CODEX reads plan and implements

# Option 2: Use prompt translator directly
adr generate-prompts ADR-P-0005 --output prompts/
# Generates detailed prompts per component
# CODEX reads prompts and implements

# Option 3: Hybrid (best of both)
python scripts/codex-implement.py ADR-P-0005 --with-prompts
# Generates both plan AND detailed prompts
# CODEX has complete guidance
```

---

## Benefits of This Workflow

### For CODEX
- ✅ Clear, structured plan to follow
- ✅ All constraints explicit
- ✅ Progress tracking built-in
- ✅ Self-validation criteria clear
- ✅ Can resume from interruption

### For Human Oversight
- ✅ Can review plan before implementation
- ✅ Can monitor progress in real-time
- ✅ Can validate against original ADR
- ✅ Clear audit trail

### For Validation (Cursor)
- ✅ Plan shows what was intended
- ✅ Progress shows what was done
- ✅ Report shows validation results
- ✅ Easy to verify compliance

### For Scale
- ✅ Works for any Physical ADR
- ✅ Handles complex multi-component ADRs
- ✅ Supports parallel implementation
- ✅ Enables automated pipelines

---

## Next Steps

1. **Create script**: `scripts/codex-implement.py`
2. **Create instructions**: `.codex/INSTRUCTIONS.md`
3. **Test workflow**: Generate plan for ADR-P-0004
4. **Hand to CODEX**: Let CODEX implement following plan
5. **Validate**: Use checklist to verify
6. **Iterate**: Improve plan generation based on feedback

---

**This creates a closed-loop, autonomous implementation system!**

Human defines architecture (ADRs) → System generates plan → AI implements → System validates → Human approves
