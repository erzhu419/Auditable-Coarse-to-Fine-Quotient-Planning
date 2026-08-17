"""New semantic domains for the V56r1 exact-frontier successor.

Only roles whose meaning changes receive a new domain.  Candidate, episode,
certificate, distinction, validation, and OOD roles retain their frozen V56
domains because V56r1 changes only acquisition termination and its enclosing
accounting/campaign roots.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_mdl_adaptive_preregistration_v56r1": (
        "acfqp:construction-k7-mdl-adaptive-preregistration:v56r1"
    ),
    "construction_k7_mdl_adaptive_acquisition_v56r1": (
        "acfqp:construction-k7-mdl-adaptive-acquisition:v56r1"
    ),
    "construction_k7_mdl_adaptive_sample_tax_v56r1": (
        "acfqp:construction-k7-mdl-adaptive-sample-tax:v56r1"
    ),
    "construction_k7_mdl_adaptive_campaign_v56r1": (
        "acfqp:construction-k7-mdl-adaptive-campaign:v56r1"
    ),
    "construction_k7_mdl_adaptive_verification_v56r1": (
        "acfqp:construction-k7-mdl-adaptive-verification:v56r1"
    ),
}

K7_DOMAIN_TAG_EXTENSION_REGISTRY_V56R1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V56R1 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V56R1) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V56r1 domain extension contains a duplicate domain")

for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v56r1(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V56R1
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the V56r1 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V56R1",
            "K7_DOMAIN_TAG_EXTENSION_V56R1",
            "extension_content_id_v56r1",
        )
    )
)
