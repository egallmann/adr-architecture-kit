"""Fixed lowercase UUIDv7 fixtures and sequential mint helpers for tests."""

from __future__ import annotations

from collections.abc import Callable, Sequence

# Prevalidated lowercase RFC 9562 UUIDv7 values (stdlib-compatible).
# First 48 bits of UUIDV7_TIMESTAMP_FIXTURE decode to 1723334400123 ms
# → 2024-08-11T00:00:00.123Z
UUIDV7_TIMESTAMP_FIXTURE = "01913ebc-187b-7def-8a00-112233445566"
UUIDV7_TIMESTAMP_MS = 1723334400123
UUIDV7_CREATED_AT = "2024-08-11T00:00:00.123Z"

UUIDV7_A = "019109a0-b1c2-7def-8a00-112233445566"
UUIDV7_B = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
UUIDV7_C = "019109a0-d5e6-7f78-8c00-aabb00112233"

# Deterministic sequence for migrator / planner tests (distinct lowercase UUIDv7s).
UUIDV7_SEQUENCE: tuple[str, ...] = (
    "01913ebc-187b-7def-8a00-112233445501",
    "01913ebc-187b-7def-8a00-112233445502",
    "01913ebc-187b-7def-8a00-112233445503",
    "01913ebc-187b-7def-8a00-112233445504",
    "01913ebc-187b-7def-8a00-112233445505",
    "01913ebc-187b-7def-8a00-112233445506",
    "01913ebc-187b-7def-8a00-112233445507",
    "01913ebc-187b-7def-8a00-112233445508",
    "01913ebc-187b-7def-8a00-112233445509",
    "01913ebc-187b-7def-8a00-11223344550a",
    "01913ebc-187b-7def-8a00-11223344550b",
    "01913ebc-187b-7def-8a00-11223344550c",
    "01913ebc-187b-7def-8a00-11223344550d",
    "01913ebc-187b-7def-8a00-11223344550e",
    "01913ebc-187b-7def-8a00-11223344550f",
    "01913ebc-187b-7def-8a00-112233445510",
    "01913ebc-187b-7def-8a00-112233445511",
    "01913ebc-187b-7def-8a00-112233445512",
    "01913ebc-187b-7def-8a00-112233445513",
    "01913ebc-187b-7def-8a00-112233445514",
    "01913ebc-187b-7def-8a00-112233445515",
    "01913ebc-187b-7def-8a00-112233445516",
    "01913ebc-187b-7def-8a00-112233445517",
    "01913ebc-187b-7def-8a00-112233445518",
    "01913ebc-187b-7def-8a00-112233445519",
    "01913ebc-187b-7def-8a00-11223344551a",
    "01913ebc-187b-7def-8a00-11223344551b",
    "01913ebc-187b-7def-8a00-11223344551c",
    "01913ebc-187b-7def-8a00-11223344551d",
    "01913ebc-187b-7def-8a00-11223344551e",
)


def sequential_mint(values: Sequence[str]) -> Callable[[], str]:
    """Return a zero-arg mint callable that yields *values* in order."""

    iterator = iter(values)

    def mint() -> str:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise RuntimeError("sequential_mint exhausted fixed UUIDv7 fixtures") from exc

    return mint
