# Design Journal Promotion Provider

`adr_kit.api` exposes a durable Design Journal / Promotion Contract provider:

- `prepare_promotion`
- `check_promotion`
- `apply_promotion`

## Artifact authority model

```text
DESIGN_JOURNAL_DURABLE_AUTHORITY=NO
DESIGN_JOURNAL_VERSIONED_HISTORY=NO

PREPARED_PROMOTION_CONTRACT_DURABLE_AUTHORITY=NO
PREPARED_PROMOTION_CONTRACT_DEFAULT_PERSISTENCE=LOCAL_TRANSIENT_HANDOFF

PROMOTION_EXECUTION_EVIDENCE=PROVENANCE_NOT_INTENT_AUTHORITY

PROMOTED_SUBSTRATE_DURABLE_AUTHORITY=YES
PROMOTED_SUBSTRATE_VERSIONED=YES
```

Design Journals are local convergence artifacts while understanding is changing:

```text
explore → evaluate → decide → lock readiness → prepare promotion
```

They are not durable architecture authority. Promotion persists resolved intent
into the governed substrate (`adrs/**`, DEC/INV content therein, `ROADMAP.md`,
and other promoted authority). After promotion succeeds, current intent is
reconstructed from that substrate and its Git history — not from the Design
Journal.

## Lifecycle

```text
Design Journal (local / mutable / non-authoritative)
  → prepared Promotion Contract (local mechanical handoff)
  → human lock
  → promotion apply
  → ADR / DEC / INV / ROADMAP / other governed substrate
       (durable / authoritative / versioned)
```

Provider mechanical lifecycle:

```text
prepare → bind → validate mechanical readiness
→ explicit human lock on the exact prepared PC
→ atomic authority apply (all targets or none)
→ append successful apply execution evidence
→ regenerate ADR Kit-owned derived artifacts
→ complete corpus validation
→ deterministic freshness / zero-diff verification
```

## Capability discovery

Promotion operations appear in `capabilities().operations` only when the
behavioral contract is implemented. The provider also reports
`ste.design_journal.promotion_contract/v0.1` in
`capabilities().supported_promotion_contract_versions`. This Promotion
Contract version is independent of ADR authoring schema versions and the
normalized model version; ADR schema 1.3 and normalized model 2.0 are **not**
advertised by this provider.

## Prepared PC handoff

When `prepared_contract_output_path` is omitted, `prepare_promotion` writes the
exact prepared Promotion Contract under the existing ignored kit state root:

```text
.adr-kit/promotion/prepared-promotion-contract.json
```

That location is outside governed authority, gitignored by default, inspectable
for human review/lock, and eligible for local cleanup after successful
promotion. An explicit caller-selected path remains supported and must still
resolve outside `adrs/**` and `ROADMAP.md`.

A prepared PC may persist locally long enough for deterministic review and lock;
that does **not** imply it should be committed to Git or treated as durable
intent authority.

## Post-promotion hygiene

After successful promotion:

- ADR/DEC/INV/ROADMAP substrate is the durable architectural memory
- the Design Journal is no longer required to establish current intent
- the prepared PC is no longer current intent authority
- execution evidence may be retained per evidence/provenance policy (not as
  intent authority)
- local journal / handoff / prepared artifacts may be archived locally or removed
- future change begins a new convergence cycle and promotes amendments into
  substrate

Do not maintain historical Design Journals as parallel truth beside ADR authority.

## Human lock

The provider never fabricates `human_lock`. After Leg A preparation, stop at
`HUMAN_PROMOTION_LOCK_REQUIRED` and wait for an explicit human-supplied lock
before `apply_promotion(..., commit=True)`.

## CLI

Thin adapters:

```bash
adr promote prepare --contract path/to/pc.json
adr promote prepare --contract path/to/pc.json --output path/outside/authority.json
adr promote check --contract path/to/prepared-or-locked.json
adr promote apply --contract path/to/locked.json
adr promote apply --contract path/to/locked.json --commit
```

CLI delegates to the same application service as `adr_kit.api`.
