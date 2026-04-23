"""Exceptions for the multi-source adapter framework."""
from __future__ import annotations


class SourceError(Exception):
    """Base class for all adapter framework errors."""


class InvalidSaleRecord(SourceError):
    """Registry rejected a record that violated a NormalizedSale invariant."""


class AdapterNotConfigured(SourceError):
    """Adapter is feature-flagged off or missing credentials."""


class AdapterTimeout(SourceError):
    """Adapter exceeded its per-call timeout budget."""
