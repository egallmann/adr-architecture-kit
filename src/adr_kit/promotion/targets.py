"""Provider target resolution for adr: and file: refs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..api._errors import OperationError

_ADR_REF = re.compile(r"^adr:(ADR-(?:L|PS|PC)-\d{4})$")
_FILE_REF = re.compile(r"^file:(.+)$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class ResolvedTarget:
    provider_target_ref: str
    operation: str
    relative_path: str
    absolute_path: Path
    exists: bool
    adr_id: str | None = None


def slugify_title(title: str, *, max_length: int = 50) -> str:
    slug = _SLUG_RE.sub("-", title.strip().lower()).strip("-")
    if not slug:
        slug = "untitled"
    return slug[:max_length].rstrip("-")


def _find_adr_files(project_root: Path, adr_id: str) -> list[Path]:
    adrs = project_root / "adrs"
    if not adrs.is_dir():
        return []
    matches: list[Path] = []
    for path in sorted(adrs.rglob("*.yaml")) + sorted(adrs.rglob("*.yml")):
        if "index" in path.parts or path.parent.name == "entities":
            continue
        if path.name.startswith(f"{adr_id}-") or path.stem == adr_id:
            matches.append(path)
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(rf"(?m)^id:\s*[\"']?{re.escape(adr_id)}[\"']?\s*$", text):
            matches.append(path)
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in matches:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def resolve_target(
    project_root: Path,
    provider_target_ref: str,
    *,
    operation: str,
    create_title: str | None = None,
) -> ResolvedTarget:
    root = project_root.resolve()
    adr_match = _ADR_REF.match(provider_target_ref)
    file_match = _FILE_REF.match(provider_target_ref)

    if file_match:
        relative = file_match.group(1)
        if ".." in Path(relative).parts or relative.startswith(("/", "\\")):
            raise OperationError(
                f"PROMOTION_UNSAFE_TARGET: unsafe file reference {provider_target_ref}"
            )
        if relative != "ROADMAP.md":
            raise OperationError(
                f"PROMOTION_UNSUPPORTED_TARGET: unsupported file target {provider_target_ref}"
            )
        absolute = (root / relative).resolve()
        try:
            absolute.relative_to(root)
        except ValueError as exc:
            raise OperationError(
                f"PROMOTION_UNSAFE_TARGET: path escapes project root for {provider_target_ref}"
            ) from exc
        exists = absolute.is_file()
        if operation in {"amend", "supersede"} and not exists:
            raise OperationError(f"PROMOTION_TARGET_MISSING: {provider_target_ref}")
        return ResolvedTarget(
            provider_target_ref=provider_target_ref,
            operation=operation,
            relative_path=relative,
            absolute_path=absolute,
            exists=exists,
        )

    if not adr_match:
        raise OperationError(
            f"PROMOTION_UNSUPPORTED_TARGET: unsupported provider_target_ref {provider_target_ref}"
        )

    adr_id = adr_match.group(1)
    matches = _find_adr_files(root, adr_id)
    if operation == "create":
        if matches:
            raise OperationError(f"PROMOTION_TARGET_EXISTS: {provider_target_ref}")
        if not create_title:
            raise OperationError(
                f"PROMOTION_CREATE_TITLE_REQUIRED: create of {provider_target_ref} requires title"
            )
        family = (
            "logical"
            if adr_id.startswith("ADR-L-")
            else ("physical-system" if adr_id.startswith("ADR-PS-") else "physical-component")
        )
        relative = f"adrs/{family}/{adr_id}-{slugify_title(create_title)}.yaml"
        absolute = (root / relative).resolve()
        if absolute.exists():
            raise OperationError(f"PROMOTION_TARGET_COLLISION: {relative}")
        return ResolvedTarget(
            provider_target_ref=provider_target_ref,
            operation=operation,
            relative_path=relative,
            absolute_path=absolute,
            exists=False,
            adr_id=adr_id,
        )

    if not matches:
        raise OperationError(f"PROMOTION_TARGET_MISSING: {provider_target_ref}")
    if len(matches) > 1:
        raise OperationError(f"PROMOTION_AMBIGUOUS_TARGET: {provider_target_ref}")
    absolute = matches[0].resolve()
    relative = absolute.relative_to(root).as_posix()
    return ResolvedTarget(
        provider_target_ref=provider_target_ref,
        operation=operation,
        relative_path=relative,
        absolute_path=absolute,
        exists=True,
        adr_id=adr_id,
    )
