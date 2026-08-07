"""Supported exception hierarchy for the public ADR Kit SDK."""


class SDKError(Exception):
    """Base class for supported SDK operation errors."""


class InvalidRequestError(SDKError, ValueError):
    """Raised before an operation starts when a request is invalid."""


class OperationError(SDKError):
    """Raised when an operation cannot produce a completed result."""


class RepositoryError(OperationError):
    """Raised when the stable architecture repository cannot be opened."""
