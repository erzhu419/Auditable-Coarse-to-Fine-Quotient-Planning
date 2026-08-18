"""Fresh domains for the V59 symmetric-prefix successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-true-bit-symmetric-{suffix}:v59"
    for key, suffix in (
        ("construction_k7_true_bit_symmetric_preregistration_v59", "preregistration"),
        ("construction_k7_true_bit_symmetric_acquisition_v59", "acquisition"),
        ("construction_k7_true_bit_symmetric_certificate_v59", "certificate"),
        ("construction_k7_true_bit_symmetric_distinction_v59", "distinction"),
        ("construction_k7_true_bit_symmetric_episode_v59", "episode"),
        ("construction_k7_true_bit_symmetric_sample_tax_v59", "sample-tax"),
        ("construction_k7_true_bit_symmetric_campaign_v59", "campaign"),
        ("construction_k7_true_bit_symmetric_verification_v59", "verification"),
    )
}

K7_DOMAIN_TAG_EXTENSION_REGISTRY_V59: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V59 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V59) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V59 domain extension contains a duplicate domain")

for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v59(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V59:
        raise ValueError("domain tag is absent from the V59 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V59",
            "K7_DOMAIN_TAG_EXTENSION_V59",
            "extension_content_id_v59",
        )
    )
)
