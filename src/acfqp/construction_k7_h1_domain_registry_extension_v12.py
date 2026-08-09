"""Twelfth additive domains for the E5A route-wide cgroup admission.

V12 is construction-only and does not relabel any V10 exclusive-broker or
V11 output-continuation object.  Its prelaunch envelope is an enforced
allowed-cap witness, not a post-run peak, CounterRecord, WorkVector or formal
route upper.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-route-wide-cgroup-profile:v1"
)
CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_TOPOLOGY_PLAN_V1_DOMAIN = (
    "acfqp:construction-k7-h1-route-wide-cgroup-topology-plan:v1"
)
CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_HIERARCHY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-route-wide-cgroup-hierarchy:v1"
)
CONSTRUCTION_K7_H1_ROUTE_WIDE_PRELAUNCH_ALLOWED_CAP_V1_DOMAIN = (
    "acfqp:construction-k7-h1-route-wide-prelaunch-allowed-cap:v1"
)
CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_CLEANUP_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-route-wide-cgroup-cleanup-closure:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V12: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_route_wide_cgroup_profile_v1": (
            CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_route_wide_cgroup_topology_plan_v1": (
            CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_TOPOLOGY_PLAN_V1_DOMAIN
        ),
        "construction_k7_h1_route_wide_cgroup_hierarchy_v1": (
            CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_HIERARCHY_V1_DOMAIN
        ),
        "construction_k7_h1_route_wide_prelaunch_allowed_cap_v1": (
            CONSTRUCTION_K7_H1_ROUTE_WIDE_PRELAUNCH_ALLOWED_CAP_V1_DOMAIN
        ),
        "construction_k7_h1_route_wide_cgroup_cleanup_closure_v1": (
            CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_CLEANUP_CLOSURE_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V12 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V12.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V12) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V12
):  # pragma: no cover - import-time invariant
    raise RuntimeError("K7 H1 domain extension V12 contains a duplicate domain")


def extension_content_id_v12(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V12
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V12 registry")
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
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V12",
            "K7_H1_DOMAIN_TAG_EXTENSION_V12",
            "extension_content_id_v12",
        )
    )
)
