# Phase 1 benchmark baseline

Recorded on 2026-08-06 with Python 3.12 on Windows using:

```powershell
python benchmarks/phase0.py --corpus all --warmups 1 --repeats 3 --json-out <temporary-file>
```

All Phase 0 stage names, corpus definitions, fingerprints, and JSON fields remain.
Phase 1 adds descriptive sidecars for `sdk_validate`, `sdk_compile_preview`, and
`sdk_open_repository`. Both the original and SDK evidence were deterministic across
repeats. These timings are observations, not pass/fail SLOs.

| Corpus | ADRs | SDK stage | Cold first (ms) | Warm median (ms) | Warm samples (ms) |
|---|---:|---|---:|---:|---|
| repository | 38 | validate | 1003.719 | 1011.207 | 1011.207, 1037.129, 998.453 |
| repository | 38 | compile preview | 5680.207 | 5702.899 | 5675.157, 5702.899, 5736.975 |
| repository | 38 | open repository | 1527.654 | 1526.957 | 1522.685, 1526.957, 1539.024 |
| examples | 3 | validate | 47.958 | 48.651 | 49.596, 48.470, 48.651 |
| examples | 3 | compile preview | 264.367 | 256.882 | 256.659, 257.765, 256.882 |
| examples | 3 | open repository | 68.487 | 69.181 | 69.181, 84.385, 69.015 |
| synthetic | 10 | validate | 58.859 | 59.213 | 58.084, 59.308, 59.213 |
| synthetic | 10 | compile preview | 521.158 | 515.824 | 515.792, 515.824, 529.230 |
| synthetic | 10 | open repository | 111.627 | 112.592 | 112.592, 111.305, 112.736 |
| synthetic | 100 | validate | 421.072 | 426.047 | 431.016, 425.868, 426.047 |
| synthetic | 100 | compile preview | 4796.354 | 4765.836 | 4765.836, 4880.575, 4746.646 |
| synthetic | 100 | open repository | 903.650 | 885.009 | 885.009, 877.353, 901.303 |
| synthetic | 500 | validate | 2035.849 | 2039.775 | 2039.433, 2039.775, 2055.700 |
| synthetic | 500 | compile preview | 24377.578 | 24554.959 | 24554.959, 24505.281, 24577.354 |
| synthetic | 500 | open repository | 4900.569 | 4695.415 | 4699.928, 4695.415, 4686.737 |

The SDK adapters invoke one validator/compiler/repository path per operation; they do
not perform a duplicate validation or compilation to construct public results.
