from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as p
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_accounted_preregistration_is_outcome_free_and_frozen() -> None:
    value = p.freeze_standard_2048_accounted_preregistration_v12()
    assert p.verify_standard_2048_accounted_preregistration_v12(value) is value
    document = value.to_document()
    assert value.preregistration_id == p.PREREGISTRATION_ID
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["native_counter_records_issued"] is False
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False


def test_fresh_long_boards_and_identity_are_preregistered() -> None:
    document = p.freeze_standard_2048_accounted_preregistration_v12().to_document()
    assert document["initial_boards_are_fresh_and_d4_disjoint_from_v169"] is True
    assert document["episode_count"] == 4
    assert document["maximum_decision_count"] == 256
    assert document["episode_worker_working_bytes_peak_upper"] == 2**31
    assert document["campaign_parent_working_bytes_peak_upper"] == 2**32
    assert document["maximum_decisions_per_episode"] == 64
    assert len(set(document["preregistered_episode_seeds"])) == 4


def test_accounting_topology_binds_all_nine_shared_paths_and_v8_profiles() -> None:
    document = p.freeze_standard_2048_accounted_preregistration_v12().to_document()
    profiles = document["accounting_profiles"]
    assert profiles == {
        "counter_registry_id": (
            "c85bc3bc127f2c64ae6010db7eb44f9f79a5b37843da1b641e0f06f2f3c9a519"
        ),
        "comparison_profile_id": (
            "3ed1f6367dcfdbab2f5d9a893b505cd17e109e9d758ba188d1b5a547d8f1ad6b"
        ),
        "actual_projection_profile_id": (
            "bed3454cd28806e222b0e2c7bba5dccbac0af4cf313c094d7196d8400b9f7d76"
        ),
        "stage_profile_id": (
            "3a5628c312c0c81a2f9f62e6536da5e51055e93244f69aaa928b94d42dfe56f9"
        ),
        "required_counter_path_count": 246,
        "operational_counter_path_count": 205,
    }
    shared = document["shared_resource_receipt_contract"]["required_paths"]
    assert len(shared) == 9
    contract = document["shared_resource_receipt_contract"]
    assert contract["post_cutoff_accounting_provenance_hashes_excluded"] is True
    assert contract["accounting_hash_exclusion_avoids_recursive_self_charging"] is True
    assert set(document["future_content_domains"]) == {
        "preregistration",
        "measurement",
        "counter_bundle",
        "decision",
        "episode",
        "campaign",
        "verification",
        "output_renderer",
        "output_commit",
    }
    assert len(set(shared)) == 9
    topology = document["native_accounting_topology"]
    assert topology["failed_certificate_common_and_fallback_vectors_are_distinct"]
    assert topology["all_required_counter_paths_explicit_in_every_work_vector"]
    assert topology["required_native_zero_observed_not_inferred"]


def test_future_domains_are_registered_and_unique() -> None:
    assert len(set(p.FUTURE_DOMAINS.values())) == len(p.FUTURE_DOMAINS)
    assert set(p.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS


def test_tampered_or_caller_minted_value_is_rejected() -> None:
    value = p.freeze_standard_2048_accounted_preregistration_v12()
    forged = copy.copy(value)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(p.ConstructionK7Standard2048AccountedPreregistrationV12Error):
        p.verify_standard_2048_accounted_preregistration_v12(forged)
    with pytest.raises(p.ConstructionK7Standard2048AccountedPreregistrationV12Error):
        p.Standard2048AccountedPreregistrationV12(
            object(), value.canonical_bytes, value.preregistration_id
        )
