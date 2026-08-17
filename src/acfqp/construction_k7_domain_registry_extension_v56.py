"""Immutable additive content domains for the V56 MDL campaign.

The V56 extension is intentionally separate from both the historical Phase 3E
registry and the frozen V55 extension.  Adding these domains therefore cannot
change any predecessor source byte or predecessor content identity.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_mdl_adaptive_preregistration_v56": (
        "acfqp:construction-k7-mdl-adaptive-preregistration:v56"
    ),
    "construction_k7_mdl_adaptive_candidate_v56": (
        "acfqp:construction-k7-mdl-adaptive-candidate:v56"
    ),
    "construction_k7_mdl_adaptive_acquisition_v56": (
        "acfqp:construction-k7-mdl-adaptive-acquisition:v56"
    ),
    "construction_k7_mdl_adaptive_failed_certificate_v56": (
        "acfqp:construction-k7-mdl-adaptive-failed-certificate:v56"
    ),
    "construction_k7_mdl_adaptive_local_distinction_v56": (
        "acfqp:construction-k7-mdl-adaptive-local-distinction:v56"
    ),
    "construction_k7_mdl_adaptive_episode_v56": (
        "acfqp:construction-k7-mdl-adaptive-episode:v56"
    ),
    "construction_k7_mdl_adaptive_isolated_validation_v56": (
        "acfqp:construction-k7-mdl-adaptive-isolated-validation:v56"
    ),
    "construction_k7_mdl_adaptive_ood_rejection_v56": (
        "acfqp:construction-k7-mdl-adaptive-ood-rejection:v56"
    ),
    "construction_k7_mdl_adaptive_sample_tax_v56": (
        "acfqp:construction-k7-mdl-adaptive-sample-tax:v56"
    ),
    "construction_k7_mdl_adaptive_campaign_v56": (
        "acfqp:construction-k7-mdl-adaptive-campaign:v56"
    ),
    "construction_k7_mdl_adaptive_verification_v56": (
        "acfqp:construction-k7-mdl-adaptive-verification:v56"
    ),
}

K7_DOMAIN_TAG_EXTENSION_REGISTRY_V56: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V56 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V56) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V56 domain extension contains a duplicate domain")

for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v56(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V56
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the V56 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V56",
            "K7_DOMAIN_TAG_EXTENSION_V56",
            "extension_content_id_v56",
        )
    )
)
