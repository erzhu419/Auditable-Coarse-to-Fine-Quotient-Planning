from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_layout_factorization_preregistration_v50r1 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, content_id


def test_v50r1_preregistration_is_outcome_free_content_addressed_and_fresh() -> None:
    frozen = pre.freeze_layout_factorization_preregistration_v50r1()
    assert pre.verify_layout_factorization_preregistration_v50r1(frozen) is frozen
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    document = frozen.to_document()
    assert document["fresh_v50r1_registered_outcome_execution_performed"] is False
    assert document["frozen_failed_predecessor"]["v50_failure_id"] == pre.V50_FAILURE_ID
    assert document["frozen_failed_predecessor"]["same_v50_identity_rerun_forbidden"] is True
    assert document["source_closure"]["frozen_before_any_v50r1_registered_source_or_target_outcome"] is True


def test_v50r1_preregisters_safe_terminal_correction_and_fresh_workload() -> None:
    document = pre.freeze_layout_factorization_preregistration_v50r1().to_document()
    correction = document["single_dependency_correction"]
    assert correction["rebound_dependency_count"] == 1
    assert correction["terminal_next_status_column_candidates_excluded"] is True
    assert correction["terminal_self_next_dependency_count"] == 0
    workload = document["fresh_workload"]
    seeds = (
        workload["modular_source_seeds"]
        + workload["modular_target_seeds"]
        + workload["inventory_source_seeds"]
        + workload["inventory_target_seeds"]
    )
    assert len(seeds) == len(set(seeds)) == 22
    assert all(seed // 1_000 == 502 for seed in seeds)
    assert workload["matched_target_occurrence_count"] == 16


def test_v50r1_source_closure_domains_and_claim_locks_are_exact() -> None:
    document = pre.freeze_layout_factorization_preregistration_v50r1().to_document()
    facts = document["source_closure"]["source_facts"]
    assert [row["relative_path"] for row in facts] == list(pre.BOUND_SOURCE_PATHS)
    for row in facts:
        raw = (pre.SOURCE_ROOT / row["relative_path"]).read_bytes()
        assert len(raw) == row["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    domains = list(pre.FUTURE_DOMAINS.values())
    assert len(domains) == len(set(domains)) == 12
    assert set(domains) <= PHASE3E_DOMAIN_TAGS
    assert len({content_id(domain, {"v": 1}) for domain in domains}) == 12
    boundary = document["claim_boundary"]
    assert boundary == {
        "finite_integer_relation_meta_grammar": True,
        "bounded_source_derived_structural_meta_prior": True,
        "arbitrary_tensor_or_open_world_perception_claimed": False,
        "unbounded_domain_general_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def test_v50r1_preregistration_rejects_foreign_values_and_mutation() -> None:
    frozen = pre.freeze_layout_factorization_preregistration_v50r1()
    with pytest.raises(pre.ConstructionK7LayoutFactorizationPreregistrationV50R1Error):
        pre.LayoutFactorizationPreregistrationV50R1(
            object(), frozen.canonical_bytes, frozen.preregistration_id
        )
    object.__setattr__(frozen, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7LayoutFactorizationPreregistrationV50R1Error):
        pre.verify_layout_factorization_preregistration_v50r1(frozen)
