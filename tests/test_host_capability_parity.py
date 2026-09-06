from __future__ import annotations

import json
from pathlib import Path

from adr_kit.api import capabilities


def test_declared_peer_host_capabilities_match_compatibility_contract() -> None:
    contract = json.loads(
        Path("contracts/compatibility/host-capabilities.json").read_text(encoding="utf-8")
    )
    manifest = capabilities()
    assert list(manifest.host_operations) == contract["peer_host_operations"]
    assert list(manifest.pending_host_operations) == contract["pending_host_operations"]
    assert list(manifest.browser_operations) == contract["browser_operations"]
