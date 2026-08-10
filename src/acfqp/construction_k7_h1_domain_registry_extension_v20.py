"""Fresh additive roles for a future Guardian-V2 atomic-consume boundary.

V20 does not reinterpret any V19 artifact.  It reserves separate domains for
consumer evidence, the activation successor, an exact prebound native edge,
the consumed lease lifecycle, and one-shot slot transfers.  This registry
alone issues no permit, process, topology, resource, accounting, or official
authority.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_h1_guardian_runtime_v2_consumer_evidence_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-consumer-evidence:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_activation_successor_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-activation-successor:v1"
    ),
    "construction_k7_h1_supervisor_v2_prebound_native_edge_source_closure_v1": (
        "acfqp:construction-k7-h1-supervisor-v2-prebound-native-edge-source-closure:v1"
    ),
    "construction_k7_h1_supervisor_v2_prebound_native_edge_capsule_v1": (
        "acfqp:construction-k7-h1-supervisor-v2-prebound-native-edge-capsule:v1"
    ),
    "construction_k7_h1_supervisor_v2_prebound_native_edge_activation_v1": (
        "acfqp:construction-k7-h1-supervisor-v2-prebound-native-edge-activation:v1"
    ),
    "construction_k7_h1_supervisor_v2_prebound_native_edge_cancellation_v1": (
        "acfqp:construction-k7-h1-supervisor-v2-prebound-native-edge-cancellation:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_consumed_lease_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-consumed-lease:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_consumed_closure_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-consumed-closure:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_slot_transfer_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-slot-transfer:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_consume_failure_closure_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-consume-failure-closure:v1"
    ),
}

K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V20: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_H1_DOMAIN_TAG_EXTENSION_V20 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_H1_DOMAIN_TAG_EXTENSION_V20) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("K7 H1 domain extension V20 contains a duplicate domain")

for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v20(domain_tag: str, payload: Any) -> str:
    """Hash one registered V20 role with an exact domain separator."""

    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V20
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V20 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V20",
            "K7_H1_DOMAIN_TAG_EXTENSION_V20",
            "extension_content_id_v20",
        )
    )
)
