"""Fresh domains for the totalized V63r1 residual sample-tax successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-total-residual-sample-tax-{suffix}:v63r1"
    for key, suffix in (
        ("construction_k7_total_residual_sample_tax_preregistration_v63r1", "preregistration"),
        ("construction_k7_total_residual_sample_tax_raw_query_pool_v63r1", "raw-query-pool"),
        ("construction_k7_total_residual_sample_tax_acquisition_v63r1", "acquisition"),
        ("construction_k7_total_residual_sample_tax_safety_episode_v63r1", "safety-episode"),
        ("construction_k7_total_residual_sample_tax_summary_v63r1", "summary"),
        ("construction_k7_total_residual_sample_tax_campaign_v63r1", "campaign"),
        ("construction_k7_total_residual_sample_tax_verification_v63r1", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V63R1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V63R1 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V63R1) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V63r1 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v63r1(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V63R1:
        raise ValueError("domain tag is absent from the V63r1 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V63R1",
            "K7_DOMAIN_TAG_EXTENSION_V63R1",
            "extension_content_id_v63r1",
        )
    )
)
