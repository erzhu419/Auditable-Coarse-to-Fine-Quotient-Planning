"""Fresh content domains for V61 persistent query-local proof overlays."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-persistent-overlay-{suffix}:v61"
    for key, suffix in (
        ("construction_k7_persistent_overlay_preregistration_v61", "preregistration"),
        ("construction_k7_persistent_overlay_raw_evidence_v61", "raw-evidence"),
        ("construction_k7_persistent_overlay_acquisition_v61", "acquisition"),
        ("construction_k7_persistent_overlay_certificate_v61", "certificate"),
        ("construction_k7_persistent_overlay_distinction_v61", "distinction"),
        ("construction_k7_persistent_overlay_episode_v61", "episode"),
        ("construction_k7_persistent_overlay_run_v61", "run"),
        ("construction_k7_persistent_overlay_sample_tax_v61", "sample-tax"),
        ("construction_k7_persistent_overlay_campaign_v61", "campaign"),
        ("construction_k7_persistent_overlay_verification_v61", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V61: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V61 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V61) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V61 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v61(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V61:
        raise ValueError("domain tag is absent from the V61 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V61",
            "K7_DOMAIN_TAG_EXTENSION_V61",
            "extension_content_id_v61",
        )
    )
)
