"""Fresh content domains for the V42 full standard-2048 successor.

The V41 checkpoint continuation remains immutable.  V42 uses disjoint tags so
that a fresh-from-initial-board step can never be confused with a V41
decision-768 continuation record.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{role}:v42"
    for key, role in (
        ("preregistration", "construction-k7-standard-2048-fresh-terminal-preregistration"),
        ("history_manifest", "construction-k7-standard-2048-history-freshness-manifest"),
        ("planner_identity", "construction-k7-standard-2048-fresh-terminal-planner-identity"),
        ("source_manifest", "construction-k7-standard-2048-fresh-terminal-source-manifest"),
        ("prepare_receipt", "construction-k7-standard-2048-fresh-terminal-prepare-receipt"),
        ("prepare_journal", "construction-k7-standard-2048-fresh-terminal-prepare-journal"),
        ("launch_journal", "construction-k7-standard-2048-fresh-terminal-launch-journal"),
        ("source_binding", "construction-k7-standard-2048-fresh-terminal-source-binding"),
        ("worker_start", "construction-k7-standard-2048-fresh-terminal-worker-start"),
        ("authority_consumption", "construction-k7-standard-2048-fresh-terminal-authority-consumption"),
        ("plan_certificate", "construction-k7-standard-2048-fresh-terminal-plan-certificate"),
        ("transition_step", "construction-k7-standard-2048-fresh-terminal-transition-step"),
        ("episode", "construction-k7-standard-2048-fresh-terminal-episode"),
        ("campaign", "construction-k7-standard-2048-fresh-terminal-campaign"),
        ("verification", "construction-k7-standard-2048-fresh-terminal-independent-verification"),
        ("runner_attempt", "construction-k7-standard-2048-fresh-terminal-runner-attempt"),
        ("runner_terminal", "construction-k7-standard-2048-fresh-terminal-runner-terminal"),
        ("runner_failure", "construction-k7-standard-2048-fresh-terminal-runner-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V42: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V42 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V42_DOMAIN"] = _domain


def extension_content_id_v42(domain_tag: str, payload: Any) -> str:
    """Return a domain-separated ID only for a registered V42 tag."""

    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V42:
        raise ValueError("domain tag is absent from V42")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V42",
    "K7_DOMAIN_TAG_EXTENSION_V42",
    "extension_content_id_v42",
)
