"""Normalized entity v2.2."""

from __future__ import annotations

from ..v2_1.normalized_entity import ExtensionPayloadV21, NormalizedEntityV21

ExtensionPayloadV22 = ExtensionPayloadV21


class NormalizedEntityV22(NormalizedEntityV21):
    schema_version: str = "2.2"
