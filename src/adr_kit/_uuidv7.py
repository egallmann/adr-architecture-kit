"""Dependency-neutral lowercase RFC 9562 UUIDv7 pattern.

Identity and decorators both need this check. Keep the primitive here so
``identity`` can import decorators for dogfooding without a circular import.
"""

from __future__ import annotations

import re

UUIDV7_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
