"""Content domains for the V57 calibrated-confidence three-domain Gate."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_calibrated_mdl_preregistration_v57": (
        "acfqp:construction-k7-calibrated-mdl-preregistration:v57"
    ),
    "construction_k7_calibrated_mdl_acquisition_v57": (
        "acfqp:construction-k7-calibrated-mdl-acquisition:v57"
    ),
    "construction_k7_calibrated_mdl_sample_tax_v57": (
        "acfqp:construction-k7-calibrated-mdl-sample-tax:v57"
    ),
    "construction_k7_calibrated_mdl_campaign_v57": (
        "acfqp:construction-k7-calibrated-mdl-campaign:v57"
    ),
    "construction_k7_calibrated_mdl_verification_v57": (
        "acfqp:construction-k7-calibrated-mdl-verification:v57"
    ),
}

K7_DOMAIN_TAG_EXTENSION_REGISTRY_V57: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V57 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V57) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V57 domain extension contains a duplicate domain")

for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v57(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V57
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the V57 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V57",
            "K7_DOMAIN_TAG_EXTENSION_V57",
            "extension_content_id_v57",
        )
    )
)
