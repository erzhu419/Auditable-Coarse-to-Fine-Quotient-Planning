"""Typed failure domain for the frozen V76 pre-target execution."""

from __future__ import annotations

import hashlib
from typing import Any

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_THREE_FAMILY_FAILURE_V76_DOMAIN = (
    "acfqp:construction-k7-three-family-source-abstention-failure:v76"
)


def extension_content_id_v76f(payload: Any) -> str:
    return hashlib.sha256(
        CONSTRUCTION_K7_THREE_FAMILY_FAILURE_V76_DOMAIN.encode()
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_THREE_FAMILY_FAILURE_V76_DOMAIN",
    "extension_content_id_v76f",
)
