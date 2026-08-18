"""Domains for V60 raw-evidence and query-local residual planning."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-query-local-{suffix}:v60"
    for key, suffix in (
        ("construction_k7_query_local_preregistration_v60", "preregistration"),
        ("construction_k7_query_local_acquisition_v60", "acquisition"),
        ("construction_k7_query_local_raw_evidence_v60", "raw-evidence"),
        ("construction_k7_query_local_certificate_v60", "certificate"),
        ("construction_k7_query_local_distinction_v60", "distinction"),
        ("construction_k7_query_local_episode_v60", "episode"),
        ("construction_k7_query_local_sample_tax_v60", "sample-tax"),
        ("construction_k7_query_local_campaign_v60", "campaign"),
        ("construction_k7_query_local_verification_v60", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V60: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V60 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V60) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V60 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v60(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V60:
        raise ValueError("domain tag is absent from the V60 extension")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(sorted((*(name for name in globals() if name.endswith("_DOMAIN")), "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V60", "K7_DOMAIN_TAG_EXTENSION_V60", "extension_content_id_v60")))
