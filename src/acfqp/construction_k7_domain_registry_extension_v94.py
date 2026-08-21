"""Fresh domains for the V94 total-label meta-prior campaign."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-total-label-meta-prior-{suffix}:v94"
    for key, suffix in (
        ("construction_k7_total_label_meta_prior_preregistration_v94", "preregistration"),
        ("construction_k7_total_label_meta_prior_on_acquisition_v94", "meta-prior-on-acquisition"),
        ("construction_k7_total_label_meta_prior_off_acquisition_v94", "meta-prior-off-acquisition"),
        ("construction_k7_total_label_meta_prior_occurrence_v94", "occurrence"),
        ("construction_k7_total_label_meta_prior_campaign_v94", "campaign"),
        ("construction_k7_total_label_meta_prior_verification_v94", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V94: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V94 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V94) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V94 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v94(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V94:
        raise ValueError("domain tag is absent from the V94 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V94",
            "K7_DOMAIN_TAG_EXTENSION_V94",
            "extension_content_id_v94",
        )
    )
)
