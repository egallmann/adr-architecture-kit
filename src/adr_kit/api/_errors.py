"""Supported exception hierarchy for the public ADR Kit SDK."""


class SDKError(Exception):
    """Base class for supported SDK operation errors."""


class InvalidRequestError(SDKError, ValueError):
    """Raised before an operation starts when a request is invalid."""


class OperationError(SDKError):
    """Raised when an operation cannot produce a completed result."""


class AuthoringDiscoveryError(OperationError):
    """Raised with the canonical diagnostic when ADC selection fails."""

    def __init__(self, code: str, message: str, diagnostics: tuple[object, ...] = ()) -> None:
        super().__init__(message)
        self.code = code
        self.diagnostics = diagnostics


class RepositoryError(OperationError):
    """Raised when the stable architecture repository cannot be opened."""
