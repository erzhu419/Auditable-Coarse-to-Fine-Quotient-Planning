"""Content domains for the V58 universal-mixture predictive Gate."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_universal_mixture_preregistration_v58": (
        "acfqp:construction-k7-universal-mixture-preregistration:v58"
    ),
    "construction_k7_universal_mixture_acquisition_v58": (
        "acfqp:construction-k7-universal-mixture-acquisition:v58"
    ),
    "construction_k7_universal_mixture_sample_tax_v58": (
        "acfqp:construction-k7-universal-mixture-sample-tax:v58"
    ),
    "construction_k7_universal_mixture_campaign_v58": (
        "acfqp:construction-k7-universal-mixture-campaign:v58"
    ),
    "construction_k7_universal_mixture_verification_v58": (
        "acfqp:construction-k7-universal-mixture-verification:v58"
    ),
}

K7_DOMAIN_TAG_EXTENSION_REGISTRY_V58: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V58 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V58) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V58 domain extension contains a duplicate domain")

for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v58(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V58
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the V58 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V58",
            "K7_DOMAIN_TAG_EXTENSION_V58",
            "extension_content_id_v58",
        )
    )
)
