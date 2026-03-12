# ste-rules-library

STE rules activation and cooperative signal hub for AI governance.

**Authority**: adr-architecture-kit ADR-L-0006, ste-rules-library ADR-L-0001

## Purpose

- **Cooperative signals**: Canonical schema for agent coordination (claim, progress, complete, wave_complete, validation_ready)
- **Rule activation**: Three-layer model (organizational, project, runtime projection)
- **Integration**: Consumed by adr-architecture-kit, ste-runtime

## Structure

```
ste-rules-library/
├── PROJECT.yaml
├── adrs/logical/
├── schema/
│   ├── signal.schema.json   # Cooperative signals
│   └── rule.schema.json    # Rule structure
├── governance/manifest.yaml
├── rules/                   # ADR-derived rules (future)
└── scripts/
    ├── bootstrap.py        # Consumer workspace bootstrap
    └── emit-signal.py      # Signal emission CLI
```

## Usage (Consumer Project)

```bash
# Clone as a sibling workspace repository
git clone https://github.com/egallmann/ste-rules-library.git ste-rules-library

# Bootstrap from the consumer project root
python ste-rules-library/scripts/bootstrap.py

# Emit signal (from consumer project root)
python ste-rules-library/scripts/emit-signal.py claim ADR-P-0004 --component COMP-0005 --agent codex
```

## Signal Schema

See `schema/signal.schema.json`. Types: claim, progress, complete, wave_complete, validation_ready.
