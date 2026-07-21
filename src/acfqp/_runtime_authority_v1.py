"""Process-local, owner-bound mint records for opaque runtime authorities.

The public Phase-3E artifacts are immutable dataclasses, but ``copy.copy`` and
``dataclasses.replace`` can still duplicate their private fields.  A shared
module token therefore proves only that *some* instance was minted; it does
not prove that the object currently presented is that exact instance.

``RuntimeAuthorityMintV1`` closes that gap without a process-global strong
registry.  A trusted constructor creates an unbound mint, constructs exactly
one authority object, and then binds the mint to that object's identity.
Copies retain the original mint and consequently fail the owner check.
Fingerprints additionally make field or retained-live-member replacement
fail closed.

This module is private implementation machinery.  It does not turn a
serializable artifact into authority and it deliberately exposes no
deserialization path.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any


class RuntimeAuthorityMintV1:
    """Single-owner process-local mint with an immutable expected fingerprint."""

    __slots__ = ("_issuer", "_fingerprint", "_owner_id")

    def __init__(self, issuer: object, fingerprint: Any) -> None:
        self._issuer = issuer
        self._fingerprint = fingerprint
        self._owner_id: int | None = None

    def validate_construction(
        self,
        owner: object,
        *,
        issuer: object,
        fingerprint: Any,
    ) -> None:
        """Validate a fresh construction or reject a copied/replaced owner."""

        if self._issuer is not issuer or self._fingerprint != fingerprint:
            raise ValueError("runtime authority mint issuer/fingerprint mismatch")
        if self._owner_id is not None and self._owner_id != id(owner):
            raise ValueError("runtime authority mint belongs to another live object")

    def bind(
        self,
        owner: object,
        *,
        issuer: object,
        fingerprint: Any,
    ) -> None:
        """Bind an unbound mint exactly once to its trusted constructor result."""

        self.validate_construction(
            owner,
            issuer=issuer,
            fingerprint=fingerprint,
        )
        if self._owner_id is not None:
            raise ValueError("runtime authority mint is already bound")
        self._owner_id = id(owner)

    def require(
        self,
        owner: object,
        *,
        issuer: object,
        fingerprint: Any,
    ) -> None:
        """Require the exact bound object and its current fingerprint."""

        self.validate_construction(
            owner,
            issuer=issuer,
            fingerprint=fingerprint,
        )
        if self._owner_id is None:
            raise ValueError("runtime authority mint was never bound")


def runtime_authority_fingerprint_v1(owner: object) -> tuple[Any, ...]:
    """Fingerprint every public dataclass field, retaining live-member identity.

    Scalars are retained by value.  Tuples are traversed recursively.  Other
    objects are represented by exact type and identity; their own authority or
    schema replay remains the responsibility of the consuming verifier.
    """

    if not dataclasses.is_dataclass(owner) or isinstance(owner, type):
        raise ValueError("runtime authority fingerprint requires a dataclass instance")

    def component(value: Any) -> Any:
        if value is None or type(value) in {str, int, bool, bytes}:
            return value
        if isinstance(value, Enum):
            return (type(value), value.value)
        if type(value) is tuple:
            return tuple(component(row) for row in value)
        return (type(value), id(value))

    return tuple(
        (row.name, component(getattr(owner, row.name)))
        for row in dataclasses.fields(owner)
        if not row.name.startswith("_")
    )


def bind_runtime_authority_v1(
    authority: Any,
    /,
    *,
    issuer: object,
    mint_field: str = "_instance_mint",
) -> Any:
    """Attach and bind a fresh mint after a private token-gated construction."""

    fingerprint = runtime_authority_fingerprint_v1(authority)
    mint = RuntimeAuthorityMintV1(issuer, fingerprint)
    object.__setattr__(authority, mint_field, mint)
    mint.bind(authority, issuer=issuer, fingerprint=fingerprint)
    return authority


def require_runtime_authority_v1(
    authority: Any,
    /,
    *,
    issuer: object,
    mint_field: str = "_instance_mint",
) -> Any:
    """Require an exact owner-bound authority and its current public fields."""

    mint = getattr(authority, mint_field, None)
    if type(mint) is not RuntimeAuthorityMintV1:
        raise ValueError("runtime authority lacks its owner-bound mint")
    mint.require(
        authority,
        issuer=issuer,
        fingerprint=runtime_authority_fingerprint_v1(authority),
    )
    return authority


def mint_runtime_authority_v1(
    authority_type: type,
    /,
    *args: Any,
    issuer: object,
    fingerprint: Any,
    mint_field: str = "_instance_mint",
    **kwargs: Any,
) -> Any:
    """Construct and owner-bind one authority dataclass.

    ``authority_type`` remains responsible for checking the module-specific
    issuer token and for recomputing the same fingerprint in ``__post_init__``.
    """

    mint = RuntimeAuthorityMintV1(issuer, fingerprint)
    kwargs[mint_field] = mint
    result = authority_type(*args, **kwargs)
    mint.bind(result, issuer=issuer, fingerprint=fingerprint)
    return result
