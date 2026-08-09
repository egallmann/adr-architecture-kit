"""Payload/schema bindings and ROADMAP rule validation."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, cast

from .ste_contract import sha256_prefixed


def fingerprint_bytes(data: bytes) -> str:
    return sha256_prefixed(data)


def fingerprint_text(text: str) -> str:
    return fingerprint_bytes(text.encode("utf-8"))


@lru_cache(maxsize=1)
def roadmap_rules_document() -> dict[str, Any]:
    root = resources.files("adr_kit.promotion.rules")
    return cast(
        dict[str, Any],
        json.loads((root / "roadmap_file_rules_v1.json").read_text(encoding="utf-8")),
    )


def roadmap_rules_fingerprint() -> str:
    raw = json.dumps(roadmap_rules_document(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return fingerprint_bytes(raw)


def validate_roadmap_content(content: str) -> list[str]:
    errors: list[str] = []
    if not content.strip():
        errors.append("ROADMAP.md is empty")
    try:
        content.encode("utf-8")
    except UnicodeError:
        errors.append("ROADMAP.md is not UTF-8 encodable")
    if not re.search(r"(?m)^#", content):
        errors.append("ROADMAP.md missing markdown heading")
    if not re.search(r"(?im)^##\s+Phase\b", content):
        errors.append("ROADMAP.md missing Phase section")
    return errors


def authorized_adr_schema_fingerprint(project_root: Path) -> tuple[str, str]:
    candidates = [
        ("1.2", project_root / "schema" / "v1.2" / "adr-logical.schema.json"),
        ("1.1", project_root / "schema" / "v1.1" / "adr-logical.schema.json"),
        ("1.0", project_root / "schema" / "v1.0" / "adr-logical.schema.json"),
    ]
    for version, path in candidates:
        if path.is_file():
            return f"schema:adr-logical-v{version}", fingerprint_bytes(path.read_bytes())
    package = resources.files("adr_kit.schema.v1_2")
    data = (package / "adr-logical.schema.json").read_bytes()
    return "schema:adr-logical-v1.2", fingerprint_bytes(data)


def binding_dict(*, ref: str, fingerprint: str) -> dict[str, str]:
    return {"ref": ref, "fingerprint": fingerprint}


def evidence_dict(
    *,
    payload_fingerprint: str,
    schema_binding_fingerprint: str,
    result: str,
    evidence_ref: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "payload_fingerprint": payload_fingerprint,
        "schema_binding_fingerprint": schema_binding_fingerprint,
        "result": result,
    }
    if evidence_ref is not None:
        payload["evidence_ref"] = evidence_ref
    return payload
