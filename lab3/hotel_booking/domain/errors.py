"""Domain exceptions used across the application.

The GUI catches :class:`DomainError` and shows ``str(exc)`` to the user, so
messages are deliberately written in business language instead of stack-trace
language.
"""


class DomainError(Exception):
    """Base class for every expected business error."""


class ValidationError(DomainError):
    """Input does not satisfy a business rule."""


class NotFoundError(DomainError):
    """A requested entity does not exist."""


class ConflictError(DomainError):
    """The operation conflicts with current data (for example sold out)."""


class PermissionDenied(DomainError):
    """The current user is not allowed to perform the operation."""


class StateTransitionError(DomainError):
    """An order status transition is not in the allowed transition table."""


class InventoryUnavailable(ConflictError):
    """At least one night of the requested stay has insufficient inventory."""

    def __init__(self, biz_date: str, remaining: int) -> None:
        self.biz_date = biz_date
        self.remaining = remaining
        super().__init__(f"{biz_date} 仅剩 {remaining} 间，无法满足预订数量")
