"""Additive domains for the V182r2 total-machine successor.

V182r1 remains frozen as a failed predecessor.  These tags are deliberately
disjoint: no V182r1 record can be reinterpreted as a totality certificate or
as a V182r2 campaign artifact.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAINS = {
    key: f"acfqp:{role}:v182r2"
    for key, role in (
        ("totality_certificate", "open-world-machine-totality-certificate"),
        ("total_compiled_model", "open-world-total-machine-compiled-model"),
        ("total_plan_certificate", "open-world-total-machine-plan-certificate"),
        ("protocol", "open-world-total-machine-protocol"),
        ("manifest_reveal", "open-world-total-machine-manifest-reveal"),
        ("execution_preregistration", "open-world-total-machine-execution-preregistration"),
        ("progress_checkpoint", "open-world-total-machine-progress-checkpoint"),
        ("campaign", "open-world-total-machine-campaign"),
        ("verification", "open-world-total-machine-independent-verification"),
        ("failure", "open-world-total-machine-campaign-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V182R2: Mapping[str, str] = MappingProxyType(
    _DOMAINS
)
K7_DOMAIN_TAG_EXTENSION_V182R2 = frozenset(_DOMAINS.values())
for _key, _domain in _DOMAINS.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V182R2_DOMAIN"] = _domain


def extension_content_id_v182r2(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V182R2
    ):
        raise ValueError("domain tag is absent from V182r2")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V182R2",
    "K7_DOMAIN_TAG_EXTENSION_V182R2",
    "extension_content_id_v182r2",
)
