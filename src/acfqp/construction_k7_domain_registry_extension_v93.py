"""Fresh domains for the V93 target-terminal-overlay campaign."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-terminal-overlay-target-{suffix}:v93"
    for key, suffix in (
        ("construction_k7_terminal_overlay_target_preregistration_v93", "preregistration"),
        ("construction_k7_terminal_overlay_target_partial_acquisition_v93", "partial-acquisition"),
        ("construction_k7_terminal_overlay_target_joint_acquisition_v93", "joint-acquisition"),
        ("construction_k7_terminal_overlay_target_occurrence_v93", "occurrence"),
        ("construction_k7_terminal_overlay_target_campaign_v93", "campaign"),
        ("construction_k7_terminal_overlay_target_verification_v93", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V93: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V93 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V93) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V93 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v93(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V93
    ):
        raise ValueError("domain tag is absent from the V93 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V93",
            "K7_DOMAIN_TAG_EXTENSION_V93",
            "extension_content_id_v93",
        )
    )
)
