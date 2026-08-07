"""ADR Architecture Kit — STE authoring subsystem for canonical ADR encoding and authoring-time validation.

This package is the STE authoring subsystem for canonical ADR encoding,
authoring-time validation, repository-normalized discovery outputs, and
ADR-to-Architecture-IR adaptation. It does not own the normative cross-repo
Architecture IR contract (that authority belongs to ste-spec) or runtime
evidence extraction (ste-runtime) or admission governance (ste-kernel).
"""

from ._version import __version__

__all__ = ["__version__"]
