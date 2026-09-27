"""Authoring v1.7 canonical resource lookup."""

from __future__ import annotations

from adr_kit.semantic_contract import load_semantic_resource


def test_authoring_v17_schema_resources_are_closure_loadable() -> None:
    resource = load_semantic_resource("authoring/1.7/schema/adr-common.schema")
    assert resource["$id"].endswith("/authoring/v1.7/adr-common.schema.json")
    assert resource["properties"]["schema_version"]["const"] == "1.7"
