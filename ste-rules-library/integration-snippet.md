# ste-rules-library Integration

## Signal Emission

Agents can emit cooperative signals via:

```bash
python ste-rules-library/scripts/emit-signal.py claim ADR-P-0004 --component COMP-0005 --agent codex
python ste-rules-library/scripts/emit-signal.py complete ADR-P-0004 --component COMP-0005 --agent codex
```

## Signal Schema

Schema: `ste-rules-library/schema/signal.schema.json`

Types: claim, progress, complete, wave_complete, validation_ready
