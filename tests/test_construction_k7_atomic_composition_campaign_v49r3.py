from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_atomic_composition_campaign_v49r3 as campaign
from acfqp import construction_k7_atomic_composition_preregistration_v49r3 as pre
from acfqp.phase3e_ids import content_id


@pytest.fixture(scope="module")
def frozen():
    return campaign.run_atomic_composition_campaign_v49r3()


def test_v49r3_campaign_identity_and_atomic_composition_are_frozen(frozen) -> None:
    assert frozen.campaign_id == campaign.CAMPAIGN_ID
    assert len(frozen.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert campaign.verify_atomic_composition_campaign_v49r3(frozen) is frozen
    document = frozen.to_document()
    program = document["compiled_program"]
    assert program["whole_program_template_count"] == 0
    assert program["specialized_discovery_pattern_count"] == 0
    assert {"E06", "E07", "E12"} <= set(program["used_opcode_names"])
    assert document["relation_transport_dependencies"] == {
        "E00_columns": [6],
        "E03_constants": [],
    }


def test_v49r3_local_recovery_is_certificate_first_bounded_and_reused(frozen) -> None:
    document = frozen.to_document()
    assert len(document["failed_certificates"]) == 1
    assert len(document["local_distinctions"]) == 4
    failure = document["failed_certificates"][0]
    assert failure["ground_query_performed_before_failure"] is False
    assert failure["changed_E00_columns"] == [6]
    assert all(
        row["failed_certificate_id"] == failure["failed_certificate_id"]
        and row["query_after_failed_certificate"] is True
        for row in document["local_distinctions"]
    )
    assert document["adaptive_acquisition"]["overlay_reuse_count"] == 62
    assert document["relation_overlay"] == {
        "R5_3_6": [[8001, 1], [8009, 2], [8021, 4], [8039, 5]]
    }


def test_v49r3_matched_episodes_and_sample_tax_pass_without_scalar_gate(frozen) -> None:
    document = frozen.to_document()
    assert len(document["structural_episodes"]) == len(pre.TARGET_SEEDS) == 12
    assert len(document["strict_episodes"]) == 12
    assert all(row["success"] for row in document["structural_episodes"])
    assert all(row["success"] for row in document["strict_episodes"])
    sample = document["sample_tax"]
    assert sample["composed_total_registered_support_labels"] == 213
    assert sample["strict_target_support_labels"] == 617
    assert sample["registered_support_label_savings"] == 404
    assert sample["diagnostic_break_even_occurrences"] == 5
    assert document["accounting"]["all_axes_separate"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_v49r3_nested_content_ids_and_ood_lock_recompute(frozen) -> None:
    document = frozen.to_document()
    for archive in document["source_archives"]:
        payload = {key: value for key, value in archive.items() if key != "raw_observation_id"}
        assert content_id(pre.FUTURE_DOMAINS["observation"], payload) == archive["raw_observation_id"]
    for row in document["local_distinctions"]:
        payload = {key: value for key, value in row.items() if key != "local_distinction_id"}
        assert content_id(pre.FUTURE_DOMAINS["distinction"], payload) == row["local_distinction_id"]
    assert document["ood_rejection"]["prior_transfer_attempted"] is False
    assert document["ood_rejection"]["outcome_execution_performed"] is False

