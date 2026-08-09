"""Child DEC/INV allocation and candidate post-image helpers."""

from __future__ import annotations

import re
from pathlib import Path

from ..repository.architecture_repository import AdrIdAllocationBands

_DEC_RE = re.compile(r"(?m)^\s*-\s*id:\s*[\"']?(DEC-\d{4})[\"']?\s*$")
_INV_RE = re.compile(r"(?m)^\s*-\s*id:\s*[\"']?(INV-\d{4})[\"']?\s*$")
_ID_NUM = re.compile(r"^(?:DEC|INV)-(\d{4})$")


def _scan_ids(project_root: Path, prefix: str) -> set[str]:
    found: set[str] = set()
    pattern = _DEC_RE if prefix == "DEC-" else _INV_RE
    adrs = project_root / "adrs"
    if not adrs.is_dir():
        return found
    for path in adrs.rglob("*.yaml"):
        if "index" in path.parts or path.parent.name in {"entities", "rendered"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        found.update(pattern.findall(text))
    return found


def _next_normal_band(used: set[str], prefix: str, bands: AdrIdAllocationBands) -> str:
    occupied: set[int] = set()
    for item in used:
        match = _ID_NUM.match(item)
        if not match:
            continue
        occupied.add(int(match.group(1)))
    for number in range(bands.normal_start, bands.normal_end + 1):
        if number in occupied:
            continue
        if bands.reserved_start <= number <= bands.reserved_end:
            continue
        candidate = f"{prefix}{number:04d}"
        if candidate not in used:
            return candidate
    raise RuntimeError(f"allocation band exhausted for {prefix}")


def allocate_child_ids(
    project_root: Path,
    *,
    dec_count: int,
    inv_count: int,
) -> tuple[list[str], list[str]]:
    bands = AdrIdAllocationBands()
    used_dec = _scan_ids(project_root, "DEC-")
    used_inv = _scan_ids(project_root, "INV-")
    decs: list[str] = []
    invs: list[str] = []
    for _ in range(dec_count):
        allocated = _next_normal_band(used_dec, "DEC-", bands)
        used_dec.add(allocated)
        decs.append(allocated)
    for _ in range(inv_count):
        allocated = _next_normal_band(used_inv, "INV-", bands)
        used_inv.add(allocated)
        invs.append(allocated)
    return decs, invs


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text_atomic_preview(content: str) -> bytes:
    return content.encode("utf-8")
