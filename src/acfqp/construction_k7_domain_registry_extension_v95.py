"""Fresh domains for the V95 second-domain persistent sample-tax Gate."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-persistent-second-domain-{suffix}:v95"
    for key, suffix in (
        ("construction_k7_persistent_second_domain_preregistration_v95", "preregistration"),
        ("construction_k7_persistent_second_domain_meta_acquisition_v95", "meta-acquisition"),
        ("construction_k7_persistent_second_domain_no_prior_acquisition_v95", "no-prior-acquisition"),
        ("construction_k7_persistent_second_domain_occurrence_v95", "occurrence"),
        ("construction_k7_persistent_second_domain_campaign_v95", "campaign"),
        ("construction_k7_persistent_second_domain_verification_v95", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V95: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V95 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V95) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V95 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v95(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V95:
        raise ValueError("domain tag is absent from the V95 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V95",
            "K7_DOMAIN_TAG_EXTENSION_V95",
            "extension_content_id_v95",
        )
    )
)
