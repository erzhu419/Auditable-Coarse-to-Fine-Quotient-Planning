"""Fresh domains for the sequence-wide agreement-shield successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-sequence-wide-agreement-shielded-{suffix}:v100"
    for key, suffix in (
        ("construction_k7_sequence_wide_agreement_shielded_preregistration_v100", "preregistration"),
        ("construction_k7_sequence_wide_agreement_shielded_occurrence_v100", "occurrence"),
        ("construction_k7_sequence_wide_agreement_shielded_campaign_v100", "campaign"),
        ("construction_k7_sequence_wide_agreement_shielded_verification_v100", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V100: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V100 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V100) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V100 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v100(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V100
    ):
        raise ValueError("domain tag is absent from the V100 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V100",
            "K7_DOMAIN_TAG_EXTENSION_V100",
            "extension_content_id_v100",
        )
    )
)
