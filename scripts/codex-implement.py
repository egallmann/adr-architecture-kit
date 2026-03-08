#!/usr/bin/env python3
"""
CODEX Implementation Workflow Script

Generates implementation plans from Physical ADRs for AI agent execution.

Usage:
    python scripts/codex-implement.py ADR-P-0004
    python scripts/codex-implement.py ADR-P-0004 --component COMP-0005
    python scripts/codex-implement.py ADR-P-0004 --plan-only

Authority: ADR-L-0005, ADR-P-0004
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import click
except ImportError:
    print("❌ Error: click not installed")
    print("   Install with: pip install click")
    sys.exit(1)


def find_adr(adr_id: str) -> Optional[Path]:
    """Find Physical ADR file by ID."""
    adrs_dir = Path("adrs/physical")
    if not adrs_dir.exists():
        return None
    
    for adr_file in adrs_dir.glob("*.yaml"):
        try:
            with open(adr_file) as f:
                data = yaml.safe_load(f)
                if data.get("id") == adr_id:
                    return adr_file
        except Exception:
            continue
    
    return None


def load_adr(adr_path: Path) -> dict:
    """Load ADR YAML file."""
    with open(adr_path) as f:
        return yaml.safe_load(f)


def load_logical_adr(logical_id: str) -> Optional[dict]:
    """Load Logical ADR by ID."""
    adrs_dir = Path("adrs/logical")
    if not adrs_dir.exists():
        return None
    
    for adr_file in adrs_dir.glob("*.yaml"):
        try:
            with open(adr_file) as f:
                data = yaml.safe_load(f)
                if data.get("id") == logical_id:
                    return data
        except Exception:
            continue
    
    return None


def generate_implementation_plan(
    physical: dict,
    logical: Optional[dict],
    component_filter: Optional[str] = None
) -> str:
    """Generate implementation plan from ADRs."""
    
    components = physical.get("component_specifications", [])
    
    if component_filter:
        components = [c for c in components if c["id"] == component_filter]
    
    invariants = logical.get("invariants", []) if logical else []
    capabilities = logical.get("capabilities", []) if logical else []
    impl_decisions = physical.get("implementation_decisions", [])
    
    # Build plan
    plan = f"""# Implementation Plan: {physical['id']}

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Status**: pending  
**Progress**: 0/{len(components)} components complete

## ADR Summary

**Physical**: {physical['id']} - {physical['title']}
"""
    
    if logical:
        plan += f"**Logical**: {logical['id']} - {logical['title']}\n"
    
    plan += f"""
**Goal**: {physical.get('context', '').split('.')[0]}

**Components**: {len(components)} ({', '.join(c['id'] for c in components)})

## Invariants to Enforce

"""
    
    for inv in invariants:
        plan += f"- [ ] **{inv['id']}**: {inv['statement']} ({inv['enforcement_level']})\n"
    
    plan += "\n## Capabilities to Deliver\n\n"
    
    for cap in capabilities:
        plan += f"- [ ] **{cap['id']}**: {cap['name']}\n"
    
    plan += "\n## Implementation Decisions\n\n"
    
    for impl in impl_decisions:
        plan += f"- **{impl['id']}**: {impl['title']}\n"
    
    plan += "\n## Execution Plan\n\n"
    
    # Simple dependency analysis (can be enhanced with COMP-0008)
    wave_num = 1
    for component in components:
        plan += f"### Wave {wave_num}: {component['name']} ({component['id']})\n\n"
        plan += f"- **Status**: ⏳ pending\n"
        plan += f"- **Type**: {component['type']}\n"
        plan += f"- **Files**:\n"
        for file in component.get("implementation_identifiers", []):
            plan += f"  - {file}\n"
        plan += f"- **Tests**: tests/test_{component['name'].lower().replace(' ', '_')}.py\n"
        plan += f"- **Test Requirements**:\n"
        for test in component.get("testing_requirements", []):
            plan += f"  - [ ] {test}\n"
        plan += "\n"
        wave_num += 1
    
    plan += """## TDD Workflow

For each component:

1. **Red**: Write failing tests
   - Read test requirements from component spec
   - Write test cases that specify expected behavior
   - Run tests (should fail - code doesn't exist yet)

2. **Green**: Implement to pass tests
   - Write minimum code to make tests pass
   - Follow interface specifications exactly
   - Enforce invariants in implementation

3. **Refactor**: Improve design
   - Clean up code while keeping tests green
   - Extract common logic
   - Improve naming and structure

4. **Update Progress**: Mark component complete in this plan

## Validation Checklist

After implementation:

"""
    
    for component in components:
        plan += f"### {component['id']}: {component['name']}\n\n"
        plan += "- [ ] Files exist\n"
        plan += "- [ ] All methods implemented\n"
        plan += "- [ ] All tests passing\n"
        plan += "- [ ] Type hints complete\n"
        plan += "- [ ] Docstrings present\n\n"
    
    plan += """## Self-Validation

Before reporting completion:

- [ ] Run: `pytest tests/ -v` (all tests pass)
- [ ] Check: All invariants enforced
- [ ] Check: All interfaces match specs
- [ ] Check: Type hints complete
- [ ] Check: Documentation complete

## Completion Report

Generate report in `.codex/reports/{adr_id}-completion.md` with:
- Summary of what was implemented
- Test results
- Invariant compliance
- Issues encountered
- Ready for Cursor validation
"""
    
    return plan


@click.command()
@click.argument('adr_id')
@click.option('--component', help='Specific component ID to implement')
@click.option('--plan-only', is_flag=True, help='Generate plan without implementing')
@click.option('--output', default='.codex/plans', help='Output directory for plan')
def implement(adr_id: str, component: Optional[str], plan_only: bool, output: str):
    """
    Generate implementation plan from Physical ADR.
    
    This script reads a Physical ADR and generates a structured implementation
    plan for CODEX to follow. The plan includes:
    - Component specifications
    - Invariants to enforce
    - Test requirements
    - TDD workflow guidance
    - Validation checklist
    
    Example:
        python scripts/codex-implement.py ADR-P-0004
    """
    
    click.echo(f"Looking for {adr_id}...")
    
    # Find Physical ADR
    adr_path = find_adr(adr_id)
    if not adr_path:
        click.echo(f"ERROR: Physical ADR {adr_id} not found in adrs/physical/", err=True)
        return 1
    
    click.echo(f"Found: {adr_path}")
    
    # Load Physical ADR
    physical = load_adr(adr_path)
    
    # Load related Logical ADR
    logical = None
    if "implements_logical" in physical and physical["implements_logical"]:
        logical_id = physical["implements_logical"][0]
        logical = load_logical_adr(logical_id)
        if logical:
            click.echo(f"Loaded Logical ADR: {logical_id}")
    
    # Generate plan
    click.echo(f"Generating implementation plan...")
    plan = generate_implementation_plan(physical, logical, component)
    
    # Create output directory
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write plan
    plan_path = output_dir / f"{adr_id}.md"
    plan_path.write_text(plan, encoding="utf-8")
    
    # Summary
    components = physical.get("component_specifications", [])
    if component:
        components = [c for c in components if c["id"] == component]
    
    invariants = logical.get("invariants", []) if logical else []
    
    click.echo()
    click.echo(f"SUCCESS: Plan generated: {plan_path}")
    click.echo(f"   Components: {len(components)}")
    click.echo(f"   Invariants: {len(invariants)}")
    click.echo(f"   Tests required: {sum(len(c.get('testing_requirements', [])) for c in components)}+")
    click.echo()
    
    if plan_only:
        click.echo("Plan contents:")
        click.echo()
        click.echo(plan)
        click.echo()
    
    click.echo("Ready for CODEX implementation")
    click.echo(f"   CODEX should read: {plan_path}")
    click.echo()
    click.echo("Next steps:")
    click.echo("   1. Review the plan")
    click.echo("   2. Hand to CODEX: 'Implement following .codex/plans/{}.md'".format(adr_id))
    click.echo("   3. CODEX implements following TDD methodology")
    click.echo("   4. CODEX self-validates and reports completion")
    click.echo("   5. Cursor validates against ADR")
    
    return 0


if __name__ == '__main__':
    sys.exit(implement())
