from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_domain_registry_extension_v180r12r4e as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r3e as predecessor_domains
from acfqp import (
    construction_k7_domain_registry_extension_v180r12r3r1e
    as immediate_predecessor_domains,
)
from acfqp.phase3e_ids import canonical_json_bytes


EXPECTED_KEYS = (
    "stable_input_snapshot",
    "io_transfer_receipt",
    "memfd_stage_receipt",
    "fd_visibility_receipt",
    "semantic_operation_receipt",
    "campaign_operation",
    "campaign_operation_manifest",
    "campaign_attempt_record",
    "pidfd_birth_receipt",
    "pidfd_reap_receipt",
    "cgroup_topology_receipt",
    "cgroup_observation_receipt",
    "replay_subject_receipt",
    "campaign_subject_result",
    "subject_commit_receipt",
    "window_closure_receipt",
    "failure_state_receipt",
    "campaign_execution_closure",
    "native_zero_source_manifest",
    "native_zero_source_fact",
    "native_zero_operation_site_fact",
    "native_zero_import_inventory",
    "native_zero_import_fact",
    "campaign_ledger_event",
    "campaign_path_receipt",
    "campaign_counter_record",
    "campaign_receipt_set",
    "campaign_work_vector",
    "campaign_comparison_vector",
    "campaign_projection_proof",
    "campaign_native_zero_attestation",
    "campaign_ledger_closure",
)


def test_subrecord_registry_has_exact_fresh_unique_domains() -> None:
    registry = domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4E
    assert tuple(registry) == EXPECTED_KEYS
    assert len(registry) == len(set(registry.values())) == len(EXPECTED_KEYS)
    assert all(value.startswith("acfqp:construction-k7-campaign-") for value in registry.values())
    assert all(value.endswith(":v180r12r4e") for value in registry.values())
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R12R4E == frozenset(registry.values())
    for key, value in registry.items():
        assert getattr(domains, f"CONSTRUCTION_K7_{key.upper()}_V180R12R4E_DOMAIN") == value


def test_subrecord_domains_are_fresh_and_disjoint_from_failed_predecessor() -> None:
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R12R4E.isdisjoint(
        predecessor_domains.K7_DOMAIN_TAG_EXTENSION_V180R12R3E
    )
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R12R4E.isdisjoint(
        immediate_predecessor_domains.K7_DOMAIN_TAG_EXTENSION_V180R12R3R1E
    )
    assert tuple(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4E) == (
        tuple(predecessor_domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R3E)
    )
    assert tuple(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4E) == (
        tuple(
            immediate_predecessor_domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R3R1E
        )
    )


def test_subrecord_content_id_is_domain_separated_and_canonical() -> None:
    registry = domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4E
    payload = {"b": 2, "a": 1}
    domain = registry["campaign_ledger_event"]
    expected = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    assert domains.extension_content_id_v180r12r4e(domain, payload) == expected
    assert domains.extension_content_id_v180r12r4e(
        registry["campaign_ledger_closure"], payload
    ) != expected


def test_subrecord_registry_rejects_mutation_and_foreign_domains() -> None:
    with pytest.raises(TypeError):
        domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4E["extra"] = "x"
    with pytest.raises(ValueError, match="absent from V180r12r4e"):
        domains.extension_content_id_v180r12r4e("foreign", {})
