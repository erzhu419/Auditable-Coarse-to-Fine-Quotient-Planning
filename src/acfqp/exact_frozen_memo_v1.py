"""Context-local switch for exact transaction-local replay reuse.

Persistent content-ID, profile, and registry caches are intentionally not
authorized: Python's dynamic serializer, hashing, enum, and descriptor
dependency graph cannot be closed by a finite process-local guard.  The
remaining switch is used only by bounded child/broker verification
transactions; disabling it always forces the same authoritative raw replay.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator


_EXACT_FROZEN_MEMO_ENABLED: ContextVar[bool] = ContextVar(
    "acfqp_exact_frozen_memo_enabled_v1",
    default=True,
)


def exact_frozen_memoization_enabled_v1() -> bool:
    """Return whether this context may reuse one transaction-local replay."""

    return _EXACT_FROZEN_MEMO_ENABLED.get()


def exact_callable_guard_v1(
    *functions: object,
) -> tuple[tuple[object, ...], ...]:
    """Bind transaction-local replay facts to their current callables."""

    result: list[tuple[object, ...]] = []
    for function in functions:
        code = getattr(function, "__code__", None)
        result.append(
            (
                id(function),
                None if code is None else id(code),
                getattr(function, "__module__", type(function).__module__),
                getattr(function, "__qualname__", type(function).__qualname__),
            )
        )
    return tuple(result)


@contextmanager
def disable_exact_frozen_memoization_v1() -> Iterator[None]:
    """Force authoritative replay in the current execution context."""

    token: Token[bool] = _EXACT_FROZEN_MEMO_ENABLED.set(False)
    try:
        yield
    finally:
        _EXACT_FROZEN_MEMO_ENABLED.reset(token)


__all__ = (
    "disable_exact_frozen_memoization_v1",
    "exact_callable_guard_v1",
    "exact_frozen_memoization_enabled_v1",
)
