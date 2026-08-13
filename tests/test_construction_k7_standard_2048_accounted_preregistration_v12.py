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
    assert document["maximum_decisions_per_episode"] == 64
    assert len(set(document["preregistered_episode_seeds"])) == 4


def test_accounting_topology_binds_all_nine_shared_paths_and_v8_profiles() -> None:
    document = p.freeze_standard_2048_accounted_preregistration_v12().to_document()
    profiles = document["accounting_profiles"]
    assert profiles == {
        "counter_registry_id": (
            "829b6b18c3e94e4e36ff145ac8bee55be3bed9697dfa9d618016942b1565c49e"
        ),
        "comparison_profile_id": (
            "564bb8018190fbc4cb4b7d882242c1e37e9ae7e3421e5a3e664e437b524ccc2b"
        ),
        "actual_projection_profile_id": (
            "3196248a681554d2b821ba4c40d985fa0ebefbe19257fd681b5fbf6765999037"
        ),
        "stage_profile_id": (
            "9c11abec500e356668ffc242c5e8d1b56fdf0be8cbe77d82ba58b901d21a04a6"
        ),
        "required_counter_path_count": 235,
        "operational_counter_path_count": 203,
    }
    shared = document["shared_resource_receipt_contract"]["required_paths"]
    assert len(shared) == 9
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
