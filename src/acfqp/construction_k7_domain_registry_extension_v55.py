"""Immutable additive content domains for the V55 adaptive joint campaign.

V55 deliberately does not append to the historical monolithic Phase 3E
registry.  Earlier preregistrations hashed that file as source, so extending it
would invalidate their source replay.  Generic V4--V9 sub-artifacts retain
their already-registered generic domains; only new V55 semantic roles use this
closed extension.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_adaptive_joint_preregistration_v55": (
        "acfqp:construction-k7-adaptive-joint-preregistration:v55"
    ),
    "construction_k7_adaptive_joint_candidate_v55": (
        "acfqp:construction-k7-adaptive-joint-candidate:v55"
    ),
    "construction_k7_adaptive_joint_acquisition_v55": (
        "acfqp:construction-k7-adaptive-joint-acquisition:v55"
    ),
    "construction_k7_adaptive_joint_failed_certificate_v55": (
        "acfqp:construction-k7-adaptive-joint-failed-certificate:v55"
    ),
    "construction_k7_adaptive_joint_local_distinction_v55": (
        "acfqp:construction-k7-adaptive-joint-local-distinction:v55"
    ),
    "construction_k7_adaptive_joint_episode_v55": (
        "acfqp:construction-k7-adaptive-joint-episode:v55"
    ),
    "construction_k7_adaptive_joint_isolated_validation_v55": (
        "acfqp:construction-k7-adaptive-joint-isolated-validation:v55"
    ),
    "construction_k7_adaptive_joint_ood_rejection_v55": (
        "acfqp:construction-k7-adaptive-joint-ood-rejection:v55"
    ),
    "construction_k7_adaptive_joint_sample_tax_v55": (
        "acfqp:construction-k7-adaptive-joint-sample-tax:v55"
    ),
    "construction_k7_adaptive_joint_campaign_v55": (
        "acfqp:construction-k7-adaptive-joint-campaign:v55"
    ),
    "construction_k7_adaptive_joint_verification_v55": (
        "acfqp:construction-k7-adaptive-joint-verification:v55"
    ),
}

K7_DOMAIN_TAG_EXTENSION_REGISTRY_V55: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V55 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V55) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V55 domain extension contains a duplicate domain")

for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v55(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V55
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the V55 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V55",
            "K7_DOMAIN_TAG_EXTENSION_V55",
            "extension_content_id_v55",
        )
    )
)
