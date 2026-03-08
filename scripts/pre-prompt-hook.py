#!/usr/bin/env python3
"""
Pre-Prompt Hook for AI Agent Implementation

Automatically generates implementation plans before AI agent execution.

Usage:
    # As pre-prompt hook (automatic)
    python scripts/pre-prompt-hook.py "Implement ADR-P-0004"
    
    # Manual invocation
    python scripts/pre-prompt-hook.py --adr ADR-P-0004 --agent cursor

Authority: ADR-L-0005, ADR-P-0004
"""

import sys
import re
import subprocess
from pathlib import Path
from typing import Optional

try:
    import click
except ImportError:
    print("ERROR: click not installed")
    print("Install with: pip install click")
    sys.exit(1)


def extract_adr_id(prompt: str) -> Optional[str]:
    """
    Extract ADR ID from user prompt.
    
    Patterns:
    - "Implement ADR-P-0004"
    - "Implement ADR-P-0004 COMP-0005"
    - "Build ADR-P-0004"
    - "Code ADR-P-0004"
    """
    patterns = [
        r'ADR-P-(\d{4})',
        r'ADR-L-(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            # Reconstruct full ID
            if 'P-' in prompt.upper() or 'p-' in prompt:
                return f"ADR-P-{match.group(1)}"
            else:
                return f"ADR-L-{match.group(1)}"
    
    return None


def extract_component_id(prompt: str) -> Optional[str]:
    """Extract component ID if specified."""
    match = re.search(r'COMP-(\d{4})', prompt, re.IGNORECASE)
    if match:
        return f"COMP-{match.group(1)}"
    return None


def detect_agent() -> str:
    """Auto-detect which AI agent is running."""
    import os
    
    # Check environment variables
    if os.getenv("CODEX_SESSION"):
        return "codex"
    
    if os.getenv("CURSOR_SESSION") or Path.cwd().name == "cursor":
        return "cursor"
    
    if os.getenv("CLAUDE_API_KEY"):
        return "claude"
    
    if os.getenv("OPENAI_API_KEY"):
        return "gpt"
    
    # Default to cursor (most capable)
    return "cursor"


def should_generate_plan(prompt: str) -> bool:
    """Check if prompt is requesting ADR implementation."""
    keywords = [
        'implement adr',
        'build adr',
        'code adr',
        'create adr',
        'develop adr',
        'implement following',
    ]
    
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in keywords)


@click.command()
@click.argument('prompt', required=False)
@click.option('--adr', help='ADR ID to implement (overrides extraction)')
@click.option('--agent', default=None, help='Target agent (auto-detect if not specified)')
@click.option('--component', help='Specific component ID')
@click.option('--force', is_flag=True, help='Force plan regeneration even if exists')
def hook(prompt: Optional[str], adr: Optional[str], agent: Optional[str], component: Optional[str], force: bool):
    """
    Pre-prompt hook for AI agent implementation.
    
    Automatically generates implementation plans when user requests ADR implementation.
    
    Examples:
        # From user prompt
        python scripts/pre-prompt-hook.py "Implement ADR-P-0004"
        
        # Explicit ADR
        python scripts/pre-prompt-hook.py --adr ADR-P-0004 --agent cursor
    """
    
    # Extract ADR ID
    adr_id = adr
    if not adr_id and prompt:
        adr_id = extract_adr_id(prompt)
    
    if not adr_id:
        click.echo("No ADR ID found in prompt")
        return 0
    
    # Check if this is an implementation request
    if prompt and not should_generate_plan(prompt):
        click.echo(f"Prompt doesn't request implementation, skipping plan generation")
        return 0
    
    # Extract component if specified
    if not component and prompt:
        component = extract_component_id(prompt)
    
    # Auto-detect agent
    if agent is None:
        agent = detect_agent()
    
    # Check if plan already exists
    plan_path = Path(f".codex/plans/{adr_id}.md")
    if plan_path.exists() and not force:
        click.echo(f"Plan already exists: {plan_path}")
        click.echo(f"Use --force to regenerate")
        return 0
    
    # Generate plan
    click.echo(f"Generating implementation plan for {adr_id}...")
    click.echo(f"Target agent: {agent}")
    
    # Build command
    cmd = [
        sys.executable,
        "scripts/codex-implement.py",
        adr_id,
        "--agent", agent
    ]
    
    if component:
        cmd.extend(["--component", component])
    
    # Run plan generator
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        click.echo(result.stdout)
        
        click.echo()
        click.echo("=" * 60)
        click.echo("PRE-PROMPT HOOK COMPLETE")
        click.echo("=" * 60)
        click.echo()
        click.echo(f"Implementation plan ready: {plan_path}")
        click.echo(f"Agent should read this plan before implementing")
        click.echo()
        
        return 0
        
    except subprocess.CalledProcessError as e:
        click.echo(f"ERROR: Failed to generate plan", err=True)
        click.echo(e.stderr, err=True)
        return 1


if __name__ == '__main__':
    sys.exit(hook())
