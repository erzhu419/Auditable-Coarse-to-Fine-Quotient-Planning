"""Domains for the certificate-local recovery-union successor V145."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v145"
    for key, tag in (
        ("occurrence", "construction-k7-certificate-local-recovery-union-occurrence"),
        ("campaign", "construction-k7-certificate-local-recovery-union-campaign"),
        ("preregistration", "construction-k7-certificate-local-recovery-union-preregistration"),
        ("verification", "construction-k7-certificate-local-recovery-union-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V145: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V145 = frozenset(_DOMAIN_BY_KEY.values())
CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_OCCURRENCE_V145_DOMAIN = _DOMAIN_BY_KEY["occurrence"]
CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_CAMPAIGN_V145_DOMAIN = _DOMAIN_BY_KEY["campaign"]
CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_PREREGISTRATION_V145_DOMAIN = _DOMAIN_BY_KEY["preregistration"]
CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_VERIFICATION_V145_DOMAIN = _DOMAIN_BY_KEY["verification"]


def extension_content_id_v145(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V145:
        raise ValueError("domain tag is absent from V145")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V145",
    "K7_DOMAIN_TAG_EXTENSION_V145",
    "extension_content_id_v145",
)
