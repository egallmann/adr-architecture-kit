"""Packaged compatibility contract resources."""

from __future__ import annotations

import importlib.resources
import json
from typing import Any


def load_cli_surface_snapshot() -> dict[str, Any]:
    """Load the governed CLI surface snapshot from the installed package bundle."""
    resource = importlib.resources.files("adr_kit.compatibility").joinpath("cli-surface.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("cli-surface.json must contain a JSON object")
    commands = payload.get("commands")
    if not isinstance(commands, dict):
        raise ValueError("cli-surface.json must contain a commands mapping")
    return payload


def load_host_capabilities_snapshot() -> dict[str, Any]:
    """Load the cross-language host capability contract from the package bundle."""
    resource = importlib.resources.files("adr_kit.compatibility").joinpath("host-capabilities.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("host-capabilities.json must contain a JSON object")
    for field in ("peer_host_operations", "pending_host_operations", "browser_operations"):
        if not isinstance(payload.get(field), list):
            raise ValueError(f"host-capabilities.json must contain a {field} list")
    return payload
