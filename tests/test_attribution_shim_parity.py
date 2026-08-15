"""Generated shims stay aligned with native decorators and the vocabulary."""

from __future__ import annotations

from adr_kit.attribution_shim_generator import generate_python_shim, generate_typescript_shim
from adr_kit.decorators import embodies, enforces, implements
from adr_kit.semantic_attribution.vocabulary import canonical_claims_attribute

SAMPLE_UUID = "019fee89-e615-7577-8d37-dd0df031bec9"


def test_python_shim_executes_and_composes_declared_claims() -> None:
    namespace: dict[str, object] = {}
    exec(compile(generate_python_shim(), "<shim>", "exec"), namespace)
    implements_fn = namespace["implements"]
    assert callable(implements_fn)

    @implements_fn(SAMPLE_UUID)  # type: ignore[misc]
    def sample() -> str:
        return "ok"

    assert sample() == "ok"
    claims = getattr(sample, canonical_claims_attribute())
    assert claims == (
        {
            "relationship": "implements",
            "target_entity_id": SAMPLE_UUID,
            "confidence": "declared",
        },
    )


def test_typescript_shim_exports_uuid_and_legacy_names() -> None:
    body = generate_typescript_shim()
    for name in (
        "implements_adr",
        "implements_adrs",
        "enforces_invariant",
        "enforces_invariants",
        "implements",
        "implements_uuids",
        "enforces",
        "enforces_uuids",
        "embodies",
        "embodies_uuids",
    ):
        assert f"export function {name}" in body


def test_native_uuid_decorators_do_not_set_legacy_attributes() -> None:
    @implements(SAMPLE_UUID)
    @enforces("019fee89-e615-7129-ac3e-8120e0d7c106")
    @embodies("019fee89-e618-7d04-9337-4aa2d3258507")
    def sample() -> None:
        return None

    assert not hasattr(sample, "__implements_adrs__")
    assert not hasattr(sample, "__enforces_invariants__")
    claims = getattr(sample, canonical_claims_attribute())
    assert {claim["relationship"] for claim in claims} == {"implements", "enforces", "embodies"}
    assert all(claim["confidence"] == "declared" for claim in claims)
