"""Domains for the matched unified-synthesizer sample-tax ablation V129."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-unified-factor-prior-ablation-{suffix}:v129"
    for key, suffix in (
        ("construction_k7_unified_factor_prior_ablation_preregistration_v129", "preregistration"),
        ("construction_k7_unified_factor_candidate_v129", "candidate"),
        ("construction_k7_unified_factor_acquisition_arm_v129", "acquisition-arm"),
        ("construction_k7_unified_factor_prior_ablation_occurrence_v129", "occurrence"),
        ("construction_k7_unified_factor_prior_ablation_campaign_v129", "campaign"),
        ("construction_k7_unified_factor_prior_ablation_verification_v129", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V129: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V129 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v129(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V129:
        raise ValueError("domain tag is absent from V129")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V129",
            "K7_DOMAIN_TAG_EXTENSION_V129",
            "extension_content_id_v129",
        )
    )
)
