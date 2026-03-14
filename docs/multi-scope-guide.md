# Multi-Scope ADR Architecture Guide

**Authority**: ADR-L-0002 - Multi-Scope ADR Architecture for Sub-Module Development

## Overview

The ADR Architecture Kit supports multi-scope operation, enabling sub-modules within a workspace to maintain independent ADR directories while being developed in parallel. This guide explains how to use scope-aware ADR tools.

## Concepts

### Project Scope

A **project scope** is a boundary within which ADRs are managed independently. Each scope has:

- **Root directory**: The project's base directory
- **ADR directory**: `<root>/adrs/` containing logical and physical ADRs
- **Manifest**: `<root>/adrs/manifest.yaml` generated from ADRs in that scope
- **Marker**: File/directory that identifies the scope (e.g., `PROJECT.yaml`, `package.json`)

### Scope Hierarchy

```
adr-architecture-kit/          # Workspace root scope
├── adrs/                      # Workspace ADRs
│   ├── logical/
│   │   ├── ADR-L-0001-...
│   │   └── ADR-L-0002-...
│   └── manifest.yaml
├── ste-runtime/               # Sub-module scope
│   ├── adrs/                  # Sub-module ADRs
│   │   ├── logical/
│   │   │   ├── ADR-L-0001-...  # Independent numbering
│   │   │   └── ADR-L-0002-...
│   │   └── manifest.yaml
│   └── package.json           # Scope marker
└── future-service/            # Another sub-module scope
    ├── adrs/
    └── pyproject.toml         # Scope marker
```

## Scope Detection

The toolkit uses a **marker hierarchy** to detect project boundaries (INV-0015):

1. **Explicit `--scope` parameter** (highest priority)
2. **`ste.config.json`** in current or parent directories (authoritative)
3. **`PROJECT.yaml`** (ADR-specific marker)
4. **Standard project markers**: `package.json`, `pyproject.toml`, `.git`
5. **Current working directory** (fallback)

### Workspace Boundaries

Scope resolution **stops at workspace boundaries** to prevent scanning unintended directories (INV-0018):

- System directories (`Users`, `home`, `Documents`)
- Parent directories beyond the workspace root

## CLI Commands

### Generate Manifest

Generate `manifest.yaml` for detected or specified scope:

```bash
# Auto-detect scope from current directory
adr generate-manifest

# Explicit scope
adr generate-manifest --scope /path/to/project

# Generate for all sub-modules recursively
adr generate-manifest --recursive

# Custom output path
adr generate-manifest --output custom-manifest.yaml
```

**Examples**:

```bash
# From workspace root - generates workspace manifest
cd /path/to/adr-architecture-kit
adr generate-manifest
# → adrs/manifest.yaml

# From sub-module - generates sub-module manifest
cd /path/to/adr-architecture-kit/ste-runtime
adr generate-manifest
# → ste-runtime/adrs/manifest.yaml

# From anywhere - generate all manifests
adr generate-manifest --recursive
# → adrs/manifest.yaml
# → ste-runtime/adrs/manifest.yaml
# → future-service/adrs/manifest.yaml
```

### Validate ADRs

Validate ADRs against schema and business rules:

```bash
# Auto-detect scope
adr validate

# Explicit scope
adr validate --scope /path/to/project

# Validate all sub-modules recursively (INV-0019)
adr validate --recursive

# Include cross-reference validation
adr validate --cross-references
```

**Examples**:

```bash
# Validate workspace ADRs only
cd /path/to/adr-architecture-kit
adr validate

# Validate sub-module ADRs only
cd /path/to/adr-architecture-kit/ste-runtime
adr validate

# Validate everything
adr validate --recursive --cross-references
```

### Show Scope

Display detected project scope(s):

```bash
# Show current scope
adr scope

# Show all scopes in workspace
adr scope --recursive
```

**Example output**:

```
$ adr scope --recursive
Found 3 project scope(s):

1. adr-architecture-kit [workspace root] (via PROJECT.yaml)
   Root: /path/to/adr-architecture-kit
   ADRs: /path/to/adr-architecture-kit/adrs
   ADR count: 2 logical, 2 physical

2. ste-runtime [sub-module] (via package.json)
   Root: /path/to/adr-architecture-kit/ste-runtime
   ADRs: /path/to/adr-architecture-kit/ste-runtime/adrs
   ADR count: 6 logical, 5 physical

3. future-service [sub-module] (via pyproject.toml)
   Root: /path/to/adr-architecture-kit/future-service
   ADRs: /path/to/adr-architecture-kit/future-service/adrs
   ADR count: 3 logical, 2 physical
```

## Python API

### Scope Resolution

```python
from pathlib import Path
from adr_kit.scope import ProjectScopeResolver

# Auto-detect scope
resolver = ProjectScopeResolver()
scope = resolver.resolve()

print(f"Project: {scope.name}")
print(f"Root: {scope.root}")
print(f"ADRs: {scope.adr_dir}")
print(f"Is sub-module: {scope.is_sub_module}")

# Explicit scope
resolver = ProjectScopeResolver(explicit_scope=Path("/path/to/project"))
scope = resolver.resolve()

# Find all scopes recursively
scopes = resolver.resolve_recursive()
for scope in scopes:
    print(f"{scope.name}: {scope.root}")
```

### Scoped Manifest Generation

```python
from adr_kit.generators import ManifestGenerator
from adr_kit.scope import ProjectScopeResolver

# Generate for current scope
resolver = ProjectScopeResolver()
generator = ManifestGenerator(scope_resolver=resolver)

manifest = generator.generate_from_scope()
generator.save_manifest(manifest, scope.manifest_path)

# Generate for all scopes
manifests = generator.generate_recursive()
for scope_name, manifest in manifests.items():
    print(f"{scope_name}: {manifest.statistics.total_adrs} ADRs")
```

### Scoped Validation

```python
from adr_kit.validators import ADRValidator
from adr_kit.scope import ProjectScopeResolver

# Validate current scope
resolver = ProjectScopeResolver()
validator = ADRValidator(scope_resolver=resolver)

results = validator.validate_scope()
for file_path, result in results.items():
    if result.has_errors:
        print(f"✗ {file_path}")
        for error in result.errors:
            print(f"  {error.message}")

# Validate all scopes
all_results = validator.validate_recursive()
for scope_name, results in all_results.items():
    errors = sum(1 for r in results.values() if r.has_errors)
    print(f"{scope_name}: {errors} errors")
```

## Best Practices

### 1. Independent ADR Numbering (INV-0016)

Each scope maintains its own ADR numbering sequence:

- **Workspace**: `ADR-L-0001`, `ADR-L-0002`, ...
- **ste-runtime**: `ADR-L-0001`, `ADR-L-0002`, ...
- **future-service**: `ADR-L-0001`, `ADR-L-0002`, ...

This prevents conflicts and allows sub-modules to be extracted as independent services.

### 2. Cross-Scope References (INV-0017)

When referencing ADRs from different scopes, use fully-qualified identifiers:

```yaml
# In workspace ADR
related_adrs:
  - ste-runtime:ADR-L-0001  # References ste-runtime's ADR-L-0001
  - ADR-L-0002              # References workspace's ADR-L-0002
```

### 3. Scope Markers

Add appropriate markers to identify project boundaries:

- **`PROJECT.yaml`**: ADR-specific marker (recommended)
- **`ste.config.json`**: Authoritative for STE projects
- **Standard markers**: `package.json`, `pyproject.toml` (auto-detected)

### 4. CI/CD Integration

Use `--recursive` in CI pipelines to validate entire workspace:

```yaml
# .github/workflows/adr-governance.yml
- name: Validate ADRs
  run: |
    pip install adr-architecture-kit[cli]
    adr validate --recursive --cross-references
    adr governance-checks
    adr validate-generated-docs
```

### 5. Development Workflow

When working on a sub-module:

```bash
# Navigate to sub-module
cd ste-runtime

# Work with sub-module ADRs
adr validate
adr generate-manifest

# Or explicitly specify scope
adr validate --scope .
```

## Migration from Single-Scope

If you have an existing single-scope ADR setup:

1. **Keep workspace ADRs** in root `adrs/` directory
2. **Create sub-module ADR directories** as needed:
   ```bash
   mkdir -p ste-runtime/adrs/{logical,physical}
   ```
3. **Add scope markers** to sub-modules (e.g., `PROJECT.yaml`)
4. **Regenerate manifests** for each scope:
   ```bash
   adr generate-manifest --recursive
   ```
5. **Update cross-references** to use fully-qualified identifiers

## Troubleshooting

### Scope Not Detected

If scope detection fails:

```bash
# Check what scope is detected
adr scope

# Use explicit scope
adr validate --scope /path/to/project

# Add PROJECT.yaml marker
cat > PROJECT.yaml << EOF
schema_version: "1.0"
type: project_metadata
project:
  name: "my-project"
EOF
```

### Wrong Scope Detected

If the wrong scope is detected (e.g., parent instead of sub-module):

1. Add `PROJECT.yaml` or `ste.config.json` to the intended scope
2. Use `--scope` parameter explicitly
3. Check for conflicting markers in parent directories

### Cross-Reference Validation Failures

When ADRs reference non-existent ADRs:

```bash
# Validate with cross-references
adr validate --cross-references

# Check if referenced ADR exists in different scope
adr scope --recursive
```

## See Also

- [ADR-L-0002: Multi-Scope ADR Architecture](../adrs/logical/ADR-L-0002-multi-scope-adr-architecture.yaml)
- [Logical ADR Guide](logical-adr-guide.md)
- [Physical ADR Guide](physical-adr-guide.md)
- [Schema Guide](schema-guide.md)
