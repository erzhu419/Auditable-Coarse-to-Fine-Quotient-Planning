"""Sub-record domains for the V180r12r3r1 measurement-ledger closure."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r12r3r1e"
    for key, tag in (
        (
            "stable_input_snapshot",
            "construction-k7-campaign-stable-input-snapshot",
        ),
        ("io_transfer_receipt", "construction-k7-campaign-io-transfer-receipt"),
        ("memfd_stage_receipt", "construction-k7-campaign-memfd-stage-receipt"),
        (
            "fd_visibility_receipt",
            "construction-k7-campaign-fd-visibility-receipt",
        ),
        (
            "semantic_operation_receipt",
            "construction-k7-campaign-semantic-operation-receipt",
        ),
        ("campaign_operation", "construction-k7-campaign-operation"),
        (
            "campaign_operation_manifest",
            "construction-k7-campaign-operation-manifest",
        ),
        ("campaign_attempt_record", "construction-k7-campaign-attempt-record"),
        ("pidfd_birth_receipt", "construction-k7-campaign-pidfd-birth-receipt"),
        ("pidfd_reap_receipt", "construction-k7-campaign-pidfd-reap-receipt"),
        (
            "cgroup_topology_receipt",
            "construction-k7-campaign-cgroup-topology-receipt",
        ),
        (
            "cgroup_observation_receipt",
            "construction-k7-campaign-cgroup-observation-receipt",
        ),
        (
            "replay_subject_receipt",
            "construction-k7-campaign-replay-subject-receipt",
        ),
        ("campaign_subject_result", "construction-k7-campaign-subject-result"),
        (
            "subject_commit_receipt",
            "construction-k7-campaign-subject-commit-receipt",
        ),
        (
            "window_closure_receipt",
            "construction-k7-campaign-window-closure-receipt",
        ),
        ("failure_state_receipt", "construction-k7-campaign-failure-state-receipt"),
        (
            "campaign_execution_closure",
            "construction-k7-campaign-execution-closure",
        ),
        (
            "native_zero_source_manifest",
            "construction-k7-campaign-native-zero-source-manifest",
        ),
        (
            "native_zero_source_fact",
            "construction-k7-campaign-native-zero-source-fact",
        ),
        (
            "native_zero_operation_site_fact",
            "construction-k7-campaign-native-zero-operation-site-fact",
        ),
        (
            "native_zero_import_inventory",
            "construction-k7-campaign-native-zero-import-inventory",
        ),
        (
            "native_zero_import_fact",
            "construction-k7-campaign-native-zero-import-fact",
        ),
        ("campaign_ledger_event", "construction-k7-campaign-ledger-event"),
        ("campaign_path_receipt", "construction-k7-campaign-path-receipt"),
        (
            "campaign_counter_record",
            "construction-k7-campaign-counter-record",
        ),
        ("campaign_receipt_set", "construction-k7-campaign-receipt-set"),
        ("campaign_work_vector", "construction-k7-campaign-work-vector"),
        (
            "campaign_comparison_vector",
            "construction-k7-campaign-comparison-vector",
        ),
        (
            "campaign_projection_proof",
            "construction-k7-campaign-projection-proof",
        ),
        (
            "campaign_native_zero_attestation",
            "construction-k7-campaign-native-zero-attestation",
        ),
        ("campaign_ledger_closure", "construction-k7-campaign-ledger-closure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R3R1E: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R12R3R1E = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R12R3R1E_DOMAIN"] = _domain


def extension_content_id_v180r12r3r1e(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R12R3R1E
    ):
        raise ValueError("domain tag is absent from V180r12r3r1e")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R3R1E",
    "K7_DOMAIN_TAG_EXTENSION_V180R12R3R1E",
    "extension_content_id_v180r12r3r1e",
)
