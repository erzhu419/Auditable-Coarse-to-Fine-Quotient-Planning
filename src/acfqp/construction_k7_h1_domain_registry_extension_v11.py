"""Eleventh additive domains for the E3-bound H1 output continuation.

V11 is a construction-only namespace.  It is deliberately disjoint from the
V8 process-local Guardian, V9 cleanup journal and V10 exclusive broker.  The
two joint output/read domains were pre-registered in :mod:`phase3e_ids`; V11
uses those exact meanings and does not mint aliases for them.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_ITERATION_V1_DOMAIN,
    canonical_json_bytes,
)


CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_CONTINUATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-continuation-profile:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_LIFECYCLE_SNAPSHOT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-lifecycle-snapshot:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_LIFECYCLE_PROGRAM_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-lifecycle-program:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_CONTINUATION_CONTEXT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-continuation-context:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_ALLOCATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-writer-allocation:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_WITNESS_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-role-witness:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-role-commit:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ORDINAL_EVENT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-ordinal-event:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_FINALIZATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-finalization:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_CLOSE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-writer-close:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_COMPLETION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-completion:v1"
)
CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_PARTIAL_NONCERTIFICATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e3-bound-output-partial-noncertificate:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V11: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_e3_bound_output_continuation_profile_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_CONTINUATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_lifecycle_snapshot_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_LIFECYCLE_SNAPSHOT_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_lifecycle_program_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_LIFECYCLE_PROGRAM_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_continuation_context_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_CONTINUATION_CONTEXT_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_writer_allocation_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_ALLOCATION_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_role_witness_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_WITNESS_V1_DOMAIN
        ),
        "construction_k7_h1_joint_output_read_iteration_v1": (
            CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_ITERATION_V1_DOMAIN
        ),
        "construction_k7_h1_joint_output_read_fixed_point_v1": (
            CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_role_commit_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_COMMIT_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_ordinal_event_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ORDINAL_EVENT_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_finalization_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_FINALIZATION_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_writer_close_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_CLOSE_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_completion_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_COMPLETION_V1_DOMAIN
        ),
        "construction_k7_h1_e3_bound_output_partial_noncertificate_v1": (
            CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_PARTIAL_NONCERTIFICATE_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V11 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V11.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V11) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V11
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V11 contains a duplicate domain")


def extension_content_id_v11(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V11
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V11 registry")
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
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V11",
            "K7_H1_DOMAIN_TAG_EXTENSION_V11",
            "extension_content_id_v11",
        )
    )
)
