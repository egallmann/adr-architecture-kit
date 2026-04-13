# schema/kernel — Repository Kernel-Compatibility Schemas

This directory contains JSON Schema documents generated from the Pydantic
models for the repository-normalized discovery artifacts:

- `architecture-index.schema.json`
- `entity-registry.schema.json`
- `relationship-registry.schema.json`
- `unresolved-registry.schema.json`

## Authority Boundary

These schemas describe the shape of artifacts **this repository produces**.
They are the kernel-compatibility subset of the repository's output surface.

They are **not** the normative cross-repo Architecture IR contract. That
authority belongs to **ste-spec** (`contracts/architecture-ir/`).

## Generation

Regenerate these schemas from source models by running:

```bash
python scripts/generate_repository_schemas.py
```

## Sync Rule

These schemas are generated artifacts. They must be regenerated and committed
whenever the underlying Pydantic models change. CI validates that the committed
schemas match the generated output.
