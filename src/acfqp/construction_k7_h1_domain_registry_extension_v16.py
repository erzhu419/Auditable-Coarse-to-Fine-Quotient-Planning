"""Additive domains for the bounded B2-C SUPERVISOR-birth slice.

V15 reserves the final actual-observed E3 V2 roles.  The process-local B2-C
companion, its one-way permit-consumption event, its bounded peak observation,
and its slice result are different artifact roles and therefore receive
different domain tags instead of reusing a V15 tag across schemas.

Domain registration alone issues no runtime or accounting authority.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN = (
    "acfqp:construction-k7-h1-supervisor-birth-companion-takeover:v1"
)
CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_PERMIT_CONSUMPTION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-supervisor-birth-permit-consumption:v1"
)
CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-bounded-supervisor-birth-peak-observation:v1"
)
CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_SLICE_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-bounded-supervisor-birth-slice-result:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V16: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_supervisor_birth_companion_takeover_v1": (
            CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN
        ),
        "construction_k7_h1_supervisor_birth_permit_consumption_v1": (
            CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_PERMIT_CONSUMPTION_V1_DOMAIN
        ),
        "construction_k7_h1_bounded_supervisor_birth_peak_observation_v1": (
            CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVATION_V1_DOMAIN
        ),
        "construction_k7_h1_bounded_supervisor_birth_slice_result_v1": (
            CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_SLICE_RESULT_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V16 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V16.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V16) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V16
):  # pragma: no cover - import-time invariant
    raise RuntimeError("K7 H1 domain extension V16 contains a duplicate domain")


def extension_content_id_v16(domain_tag: str, payload: Any) -> str:
    """Hash only one pre-registered V16 construction payload."""

    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V16
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V16 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(
                name
                for name in globals()
                if name.startswith("CONSTRUCTION_K7_H1_")
                and name.endswith("_DOMAIN")
            ),
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V16",
            "K7_H1_DOMAIN_TAG_EXTENSION_V16",
            "extension_content_id_v16",
        )
    )
)
