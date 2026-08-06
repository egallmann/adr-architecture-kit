# Phase 0 benchmark baseline

This baseline is descriptive, not a performance threshold. CI runs the functional
smoke profile and asserts successful stage execution plus deterministic fingerprints;
timing changes remain review evidence until a later authority decision defines a
performance budget.

## Measurement context

- Captured: 2026-08-05
- Platform: Windows 11 (`Windows-11-10.0.26200-SP0`)
- Interpreter: CPython 3.12.10
- Configuration: corpus `all`, sizes `10,100,500`, one warmup, five recorded repeats
- Command: `python benchmarks/phase0.py --corpus all --sizes 10,100,500 --warmups 1 --repeats 5 --json-out <path>`
- Independent full runs: 2
- Result: both runs reported `deterministic: true`; their complete fingerprint maps
  were identical.

## Corpus identity

| Corpus | ADR count | Corpus identity |
| --- | ---: | --- |
| Repository | 38 | `32e8e5f688a9042def4fc862473ffd2aaba182c28a641bc9c0e4a072afae046b` |
| Public examples | 3 | `af0ce67d7fd9a0787cac6a7deba0e0939489b7d96022413da34b9cbb8e0ddd9b` |
| Synthetic | 10 | `5a3c522c20f39852ec4a9365ba58ee553c74df7349ddfd2c043fc9815cf711bc` |
| Synthetic | 100 | `588797bef90ff6fd811d0662e8bd3361914e3de0cba055bad2023361563f4af2` |
| Synthetic | 500 | `922741110aea9fe06b7b648d288996b3d06f2801364ac190e86fa9e67f5aa2c6` |

## Content fingerprints

| Corpus | Fingerprint |
| --- | --- |
| Repository:38 | `2da3c5175ed8b154117b9d28e542fbdd99a222e3709a18dcb3b4f094c83a9a4e` |
| Examples:3 | `d0cdbc35494d46bd2d4a475cc358e52ada1961767e6e70657f422cc0441e58c2` |
| Synthetic:10 | `1d27a082ad05178df772cab55ebfc3a8d2025ab834c134ffef1895a337b07663` |
| Synthetic:100 | `c69bcb22150ab95a3f150907b76d6736235f69a43a48c73838489524f1f1cac4` |
| Synthetic:500 | `85099b3884cab950b34d4699fb107853bbd53903e4820e85b4583c16a7c4eaf7` |

## Recorded timings

All values are milliseconds from the first full baseline run. The warm column records
all five post-warmup observations, preserving measurement spread rather than only a
summary statistic.

| Corpus | Stage | Cold first | Warm repeats |
| --- | --- | ---: | --- |
| Repository:38 | extraction | 25.950 | 26.227, 24.986, 25.255, 38.586, 25.169 |
| Repository:38 | filesystem writes | 2.821 | 2.510, 2.534, 2.693, 3.866, 2.609 |
| Repository:38 | full compilation | 2743.921 | 2731.318, 2736.946, 2756.033, 2748.276, 2739.299 |
| Repository:38 | graph generation | 9.223 | 9.326, 9.021, 9.522, 9.739, 9.282 |
| Repository:38 | normalization | 1.433 | 1.492, 1.430, 1.523, 1.447, 1.441 |
| Repository:38 | parsing | 499.112 | 520.431, 499.258, 498.789, 499.912, 498.793 |
| Repository:38 | registry generation | 10.405 | 10.669, 10.423, 10.497, 10.226, 10.983 |
| Repository:38 | relationship derivation | 4.533 | 4.816, 4.452, 4.800, 4.594, 4.502 |
| Repository:38 | repository loading | 1493.570 | 1521.795, 1482.451, 1498.071, 1482.079, 1487.566 |
| Repository:38 | representative queries | 0.166 | 0.175, 0.170, 0.168, 0.160, 0.175 |
| Repository:38 | schema validation | 908.395 | 896.980, 914.673, 903.085, 895.834, 904.497 |
| Repository:38 | serialization | 547.889 | 544.025, 540.962, 539.323, 526.949, 543.370 |
| Examples:3 | extraction | 1.944 | 1.932, 1.963, 1.881, 1.850, 1.867 |
| Examples:3 | filesystem writes | 1.562 | 1.495, 1.477, 1.494, 1.542, 1.669 |
| Examples:3 | full compilation | 115.997 | 115.542, 117.955, 116.578, 115.347, 114.739 |
| Examples:3 | graph generation | 0.166 | 0.163, 0.171, 0.162, 0.160, 0.162 |
| Examples:3 | normalization | 1.452 | 1.458, 1.494, 1.438, 1.442, 1.456 |
| Examples:3 | parsing | 21.567 | 21.342, 22.073, 21.590, 21.470, 21.532 |
| Examples:3 | registry generation | 0.301 | 0.242, 0.244, 0.245, 0.244, 0.240 |
| Examples:3 | relationship derivation | 0.839 | 0.223, 0.218, 0.216, 0.221, 0.216 |
| Examples:3 | repository loading | 67.884 | 65.998, 68.680, 66.795, 65.849, 67.177 |
| Examples:3 | representative queries | 0.031 | 0.034, 0.033, 0.033, 0.031, 0.031 |
| Examples:3 | schema validation | 29.730 | 29.552, 30.146, 29.551, 29.536, 29.507 |
| Examples:3 | serialization | 17.254 | 17.697, 17.645, 17.237, 17.122, 17.356 |
| Synthetic:10 | extraction | 5.826 | 5.838, 6.491, 5.795, 5.927, 5.903 |
| Synthetic:10 | filesystem writes | 1.546 | 1.605, 1.546, 1.546, 1.792, 1.607 |
| Synthetic:10 | full compilation | 176.060 | 187.414, 188.692, 179.567, 179.719, 178.476 |
| Synthetic:10 | graph generation | 0.330 | 0.336, 0.333, 0.332, 0.954, 0.293 |
| Synthetic:10 | normalization | 1.455 | 1.470, 1.611, 1.564, 1.536, 1.420 |
| Synthetic:10 | parsing | 23.497 | 23.677, 24.385, 24.198, 24.559, 23.881 |
| Synthetic:10 | registry generation | 0.434 | 0.419, 0.435, 0.432, 0.448, 0.468 |
| Synthetic:10 | relationship derivation | 0.319 | 0.876, 0.331, 0.318, 0.327, 0.284 |
| Synthetic:10 | repository loading | 114.813 | 118.403, 138.691, 116.434, 114.906, 118.757 |
| Synthetic:10 | representative queries | 0.043 | 0.043, 0.043, 0.043, 0.043, 0.047 |
| Synthetic:10 | schema validation | 38.829 | 37.886, 38.079, 37.884, 37.436, 37.459 |
| Synthetic:10 | serialization | 36.500 | 36.340, 37.286, 38.658, 36.853, 38.093 |
| Synthetic:100 | extraction | 57.781 | 57.566, 57.298, 70.874, 57.854, 58.750 |
| Synthetic:100 | filesystem writes | 1.748 | 1.795, 1.805, 1.711, 1.888, 1.780 |
| Synthetic:100 | full compilation | 1627.142 | 1620.950, 1620.890, 1624.755, 1628.426, 1622.737 |
| Synthetic:100 | graph generation | 4.324 | 4.001, 4.044, 3.984, 4.085, 4.069 |
| Synthetic:100 | normalization | 1.454 | 1.440, 1.431, 1.454, 1.451, 1.427 |
| Synthetic:100 | parsing | 228.074 | 229.066, 230.056, 228.351, 240.619, 226.534 |
| Synthetic:100 | registry generation | 5.196 | 5.086, 19.495, 5.053, 5.203, 4.970 |
| Synthetic:100 | relationship derivation | 2.663 | 2.958, 2.732, 2.740, 2.693, 3.156 |
| Synthetic:100 | repository loading | 873.082 | 871.454, 868.127, 867.026, 880.092, 908.903 |
| Synthetic:100 | representative queries | 0.345 | 0.374, 0.369, 0.336, 0.379, 0.418 |
| Synthetic:100 | schema validation | 367.026 | 362.781, 370.124, 360.738, 362.919, 365.485 |
| Synthetic:100 | serialization | 388.291 | 374.231, 358.924, 358.600, 357.326, 357.556 |
| Synthetic:500 | extraction | 287.071 | 285.793, 289.169, 288.365, 313.132, 305.629 |
| Synthetic:500 | filesystem writes | 3.657 | 3.878, 3.636, 3.563, 4.383, 3.377 |
| Synthetic:500 | full compilation | 8258.628 | 8289.244, 8303.632, 8252.699, 8245.950, 8340.418 |
| Synthetic:500 | graph generation | 49.864 | 83.113, 49.825, 51.684, 50.468, 50.327 |
| Synthetic:500 | normalization | 1.454 | 1.596, 1.458, 1.500, 1.460, 1.437 |
| Synthetic:500 | parsing | 1148.782 | 1154.862, 1155.013, 1134.017, 1165.154, 1141.263 |
| Synthetic:500 | registry generation | 82.775 | 55.450, 80.616, 56.047, 55.623, 56.472 |
| Synthetic:500 | relationship derivation | 16.060 | 14.616, 14.569, 41.690, 14.406, 14.471 |
| Synthetic:500 | repository loading | 4667.513 | 4481.942, 4627.793, 4529.260, 4567.146, 4521.733 |
| Synthetic:500 | representative queries | 5.440 | 5.365, 5.323, 5.327, 5.328, 5.231 |
| Synthetic:500 | schema validation | 1816.227 | 1820.458, 1827.164, 1819.332, 1847.897, 1835.992 |
| Synthetic:500 | serialization | 1880.475 | 1900.417, 1882.327, 1893.704, 1909.146, 1886.644 |

The first and second complete runs took approximately 210 and 208 seconds,
respectively. Timing variation is recorded as evidence only; Phase 0 does not add a
timing threshold.
