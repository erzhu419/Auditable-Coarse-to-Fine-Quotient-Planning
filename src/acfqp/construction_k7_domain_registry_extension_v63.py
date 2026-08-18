"""Fresh content domains for the V63 residual-factor sample-tax campaign."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-residual-sample-tax-{suffix}:v63"
    for key, suffix in (
        ("construction_k7_residual_sample_tax_preregistration_v63", "preregistration"),
        ("construction_k7_residual_sample_tax_raw_query_pool_v63", "raw-query-pool"),
        ("construction_k7_residual_sample_tax_acquisition_v63", "acquisition"),
        ("construction_k7_residual_sample_tax_safety_episode_v63", "safety-episode"),
        ("construction_k7_residual_sample_tax_summary_v63", "summary"),
        ("construction_k7_residual_sample_tax_campaign_v63", "campaign"),
        ("construction_k7_residual_sample_tax_verification_v63", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V63: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V63 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V63) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V63 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v63(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V63:
        raise ValueError("domain tag is absent from the V63 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V63",
            "K7_DOMAIN_TAG_EXTENSION_V63",
            "extension_content_id_v63",
        )
    )
)
