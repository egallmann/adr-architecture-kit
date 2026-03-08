# Canonical Placement for ADRs, Manifest, and Index

**Authority**: ADR-L-0002, ProjectScopeResolver  
**Purpose**: Ensure generated ADRs, manifest, and index files are placed correctly across submodules

---

## Per-Scope Structure

Each project scope (workspace root or submodule) has its own canonical paths:

```
<scope_root>/
  adrs/
    logical/           # Logical ADRs (ADR-L-XXXX)
    physical/          # Physical ADRs (ADR-P-XXXX)
    manifest.yaml      # Index of all ADRs in this scope
```

**ProjectScope fields** (from scope resolver):

| Field | Path | Purpose |
|-------|------|---------|
| `root` | `<scope_root>` | Project root |
| `adr_dir` | `root/adrs` | ADR directory |
| `logical_dir` | `adr_dir/logical` | Place new logical ADRs |
| `physical_dir` | `adr_dir/physical` | Place new physical ADRs |
| `manifest_path` | `adr_dir/manifest.yaml` | Manifest (index) output |

---

## PROJECT.yaml Override

When `PROJECT.yaml` exists with `architecture_documentation`:

```yaml
architecture_documentation:
  adr_directory: "adrs/"
  manifest_path: "adrs/manifest.yaml"
```

Paths are resolved relative to scope root. Defaults: `adrs/`, `adrs/manifest.yaml`.

---

## Multi-Scope Placement

**Workspace**: `adr-architecture-kit/`
- `adr-architecture-kit/adrs/logical/`
- `adr-architecture-kit/adrs/physical/`
- `adr-architecture-kit/adrs/manifest.yaml`

**Submodule**: `ste-rules-library/`
- `ste-rules-library/adrs/logical/`
- `ste-rules-library/adrs/physical/`
- `ste-rules-library/adrs/manifest.yaml`

**Submodule**: `ste-runtime/`
- `ste-runtime/adrs/logical/`
- `ste-runtime/adrs/physical/`
- `ste-runtime/adrs/manifest.yaml`

---

## Generator Placement Rules

1. **Manifest**: Always write to `scope.manifest_path`
2. **New logical ADR**: Write to `scope.logical_dir`
3. **New physical ADR**: Write to `scope.physical_dir`
4. **Recursive**: Resolve scope first, then use that scope's paths

---

## Usage

```python
from adr_kit.scope import ProjectScopeResolver

resolver = ProjectScopeResolver(explicit_scope=Path("ste-rules-library"))
scope = resolver.resolve()

# Place new logical ADR
output_path = scope.logical_dir / "ADR-L-0003-new-decision.yaml"

# Place manifest
manifest_path = scope.manifest_path  # ste-rules-library/adrs/manifest.yaml
```

---

## CLI

```bash
# Generate manifest for current scope (auto-detected)
adr generate-manifest

# Generate manifest for specific scope
adr generate-manifest --scope ste-rules-library

# Generate for all scopes
adr generate-manifest --recursive
```

Output goes to each scope's `adrs/manifest.yaml`.
