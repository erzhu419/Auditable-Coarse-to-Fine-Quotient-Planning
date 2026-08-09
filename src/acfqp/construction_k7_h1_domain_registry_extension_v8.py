"""Eighth additive domain registry for the H1 native-capability guardian.

The V6 receipt journal and V7 cleanup-budget admission remain immutable
inputs.  The process-local guardian specification and its live slot bindings
therefore use domains that are disjoint from every earlier construction
artifact.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-capability-guardian-spec:v1"
)
CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-capability-guardian-binding:v1"
)
CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_INIT_MARKER_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-capability-guardian-init-marker:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V8: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_native_capability_guardian_spec_v1": (
            CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_SPEC_V1_DOMAIN
        ),
        "construction_k7_h1_native_capability_guardian_binding_v1": (
            CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_BINDING_V1_DOMAIN
        ),
        "construction_k7_h1_native_capability_guardian_init_marker_v1": (
            CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_INIT_MARKER_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V8 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V8.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V8) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V8
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V8 contains a duplicate domain")


def extension_content_id_v8(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V8
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V8 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_BINDING_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_INIT_MARKER_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_SPEC_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V8",
    "K7_H1_DOMAIN_TAG_EXTENSION_V8",
    "extension_content_id_v8",
)
