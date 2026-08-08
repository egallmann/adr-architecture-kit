# Phase 2 benchmark baseline

Recorded on 2026-08-07 with CPython 3.12.10 on Windows 11 using:

```powershell
python benchmarks/phase0.py `
  --corpus synthetic `
  --sizes 10 `
  --warmups 1 `
  --repeats 3 `
  --json-out <workspace-root>/.ste-workspace/phase2-benchmark.json
```

Phase 2 retains every Phase 0 and Phase 1 benchmark field and adds one fixed
three-ADR v1.2 semantic corpus. The additions observe v1.2 parsing, expanded
semantic compilation, assertion-ID derivation, and topology migration planning.
They are descriptive observations, not performance SLOs.

| Phase 2 stage | Cold first (ms) | Warm median (ms) | Warm samples (ms) |
|---|---:|---:|---|
| v1.2 parsing | 24.290 | 23.720 | 23.665, 23.966, 23.720 |
| semantic compilation | 29.232 | 29.385 | 29.157, 29.385, 29.961 |
| 1,000 assertion IDs | 4.152 | 4.210 | 4.222, 4.210, 4.156 |
| topology migration plan | 3.185 | 3.178 | 3.181, 3.142, 3.178 |

The recorded semantic evidence was deterministic across all repeats:

- one projected boundary, contract, interface, and implementation decision;
- three bind-only relationship records;
- no topology migration diagnostics;
- assertion digest
  `125bb93e90f37b9e4a5b591f8eb6cf1cc20089cf9b39249932f1541f214db087`.

The JSON evidence was written outside the repository under workspace-root
`.ste-workspace/`, consistent with the repository-write boundary.
