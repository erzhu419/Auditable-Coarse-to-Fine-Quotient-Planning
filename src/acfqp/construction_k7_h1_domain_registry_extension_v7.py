"""Seventh additive domain registry for H1 cleanup-budget admission.

The V4 cleanup envelope, V5 Owner sidecar, and V6 native-receipt domains are
frozen inputs.  A prospective V5 baseline and the pre-ordinal-1 cleanup budget
admission therefore receive disjoint domains here.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_PROSPECTIVE_OWNER_CLEANUP_SIDECAR_BASELINE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-prospective-owner-cleanup-sidecar-baseline:v1"
)
CONSTRUCTION_K7_H1_FAILED_PREFIX_CLEANUP_BUDGET_ADMISSION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-failed-prefix-cleanup-budget-admission:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V7: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_prospective_owner_cleanup_sidecar_baseline_v1": (
            CONSTRUCTION_K7_H1_PROSPECTIVE_OWNER_CLEANUP_SIDECAR_BASELINE_V1_DOMAIN
        ),
        "construction_k7_h1_failed_prefix_cleanup_budget_admission_v1": (
            CONSTRUCTION_K7_H1_FAILED_PREFIX_CLEANUP_BUDGET_ADMISSION_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V7 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V7.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V7) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V7
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V7 contains a duplicate domain")


def extension_content_id_v7(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V7
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V7 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_FAILED_PREFIX_CLEANUP_BUDGET_ADMISSION_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_PROSPECTIVE_OWNER_CLEANUP_SIDECAR_BASELINE_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V7",
    "K7_H1_DOMAIN_TAG_EXTENSION_V7",
    "extension_content_id_v7",
)
