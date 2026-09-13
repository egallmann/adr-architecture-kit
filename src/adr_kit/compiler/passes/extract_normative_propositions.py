"""Extract explicit authoring 1.6 normative propositions into compiler IR."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Iterable

from ...models import SourceRef
from ..ir import IREntity
from ..frontend.support import make_canonical, make_completeness, make_provenance, summarize_text


@lru_cache(maxsize=None)
def _source_contract_fingerprint(schema_name: str) -> str:
    """Return the governed authoring-schema content digest for one ADR kind."""
    package = resources.files("adr_kit.semantic_contract.v1_0")
    definition = json.loads(
        package.joinpath("architecture-interpretation.json").read_text(encoding="utf-8")
    )
    key = f"authoring/1.6/schema/{schema_name}.schema"
    for entry in definition["resourceManifest"]:
        if entry["canonicalResourceKey"] == key:
            return str(entry["contentDigest"])
    raise LookupError(f"Governed source schema digest is missing: {key}")


def _artifact_digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def extract_normative_propositions(
    adrs: Iterable[tuple[object, Path]],
    *,
    scope_root: Path,
    namespace: str,
) -> list[IREntity]:
    """Extract only explicitly authored v1.6 propositions.

    Normative propositions are deliberately represented as a compiler IR type of
    their own.  This keeps the lifecycle-bearing historical normalized entity
    model out of the v2.3 lifecycle-free NP projection.
    """

    entities: list[IREntity] = []
    provider = f"adr-kit:{namespace}"

    for adr, path in adrs:
        if getattr(adr, "schema_version", None) != "1.6":
            continue
        propositions = getattr(adr, "normative_propositions", []) or []
        if not propositions:
            continue
        artifact_path = str(path.resolve().relative_to(scope_root.resolve())).replace("\\", "/")
        artifact_digest = _artifact_digest(path)
        adr_id = str(getattr(adr, "id"))
        adr_alias_id = str(getattr(adr, "alias_id"))
        adr_alias_name = str(getattr(adr, "alias_name"))
        raw_source_type = getattr(adr, "adr_type", "logical")
        source_type = str(getattr(raw_source_type, "value", raw_source_type))
        source_type = {
            "logical": "logical_adr",
            "physical-system": "physical_system_adr",
            "physical-component": "physical_component_adr",
        }.get(source_type, source_type)
        schema_name = {
            "logical_adr": "adr-logical",
            "physical_system_adr": "adr-physical-system",
            "physical_component_adr": "adr-physical-component",
        }[source_type]
        source_contract = {
            "family": "authoring",
            "version": "1.6",
            "fingerprint": _source_contract_fingerprint(schema_name),
        }
        declaring_adr = {
            "provider": provider,
            "id": adr_id,
            "alias_id": adr_alias_id,
            "alias_name": adr_alias_name,
        }
        source_artifact = {
            "source_type": "authoring_adr",
            "source_ref": adr_id,
            "artifact_path": artifact_path,
            "content_digest": artifact_digest,
        }
        for proposition in propositions:
            proposition_id = str(proposition.id)
            source_ref = f"{adr_id}#{proposition_id}"
            metadata = {
                "alias_id": proposition.alias_id,
                "alias_name": proposition.alias_name,
                "statement": proposition.statement,
                "normative_force": proposition.normative_force,
                "scope": proposition.scope,
                "rationale": proposition.rationale,
                "declaring_adr": declaring_adr,
                "source_artifact": source_artifact,
                "source_contract": source_contract,
            }
            entities.append(
                IREntity(
                    id=proposition_id,
                    entity_type="normative_proposition",
                    name=proposition.alias_name,
                    summary=summarize_text(proposition.statement),
                    canonical_source=make_canonical(source_type, source_ref, artifact_path),
                    source_refs=[
                        SourceRef(
                            source_type="authoring_adr",
                            source_ref=adr_id,
                            artifact_path=artifact_path,
                            mention_role="declaration",
                        )
                    ],
                    metadata=metadata,
                    completeness=make_completeness(),
                    provenance=make_provenance(
                        "authoring_adr", source_ref, "extract_normative_proposition", "explicit"
                    ),
                )
            )
    return entities
