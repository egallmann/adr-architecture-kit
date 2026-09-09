"""Normalized-model v2.3 entities."""

from __future__ import annotations

from pydantic import model_validator

from ..v2_2.normalized_entity import ExtensionPayloadV22, NormalizedEntityV22
from .normative_proposition import NormativePropositionEntityV23


class NormalizedEntityV23(NormalizedEntityV22):
    """Existing normalized entities retain v2.2 lifecycle semantics in v2.3."""

    @model_validator(mode="after")
    def reject_normative_proposition_discriminator(self) -> "NormalizedEntityV23":
        if self.entity_type == "normative_proposition":
            raise ValueError("normative_proposition requires the lifecycle-free v2.3 NP variant")
        return self


NormalizedEntityVariantV23 = NormativePropositionEntityV23 | NormalizedEntityV23
ExtensionPayloadV23 = ExtensionPayloadV22
