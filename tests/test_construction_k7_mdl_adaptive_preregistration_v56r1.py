from __future__ import annotations

import hashlib

from acfqp import construction_k7_mdl_adaptive_preregistration_v56r1 as pre


def test_v56r1_preregistration_is_content_addressed_and_outcome_free():
    value = pre.freeze_mdl_adaptive_preregistration_v56r1()
    assert pre.verify_mdl_adaptive_preregistration_v56r1(value) is value
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == (
        pre.EXPECTED_CANONICAL_SHA256
    )
    document = value.to_document()
    assert document["fresh_v56r1_registered_outcome_execution_performed"] is False
    assert document["claim_boundary"]["registered_outcome_observed"] is False


def test_v56r1_freezes_failure_and_exact_frontier_successor_rule():
    document = pre.freeze_mdl_adaptive_preregistration_v56r1().to_document()
    assert document["frozen_predecessors"]["v56_failure_id"] == pre.V56_FAILURE_ID
    assert document["frozen_predecessors"]["v56_same_identity_rerun_forbidden"]
    contract = document["mdl_adaptive_successor_contract"]
    assert contract["fixed_minimum_candidate_label_floor"] is None
    assert contract["fixed_confirmation_block_size"] is None
    assert contract["exact_frontier_closure_is_a_stop_not_a_calibration_input"]
    assert contract["frontier_closure_rule_same_in_both_arms"]


def test_v56r1_source_closure_and_seeds_are_current():
    document = pre.freeze_mdl_adaptive_preregistration_v56r1().to_document()
    actual = []
    for relative in pre.BOUND_SOURCE_PATHS:
        raw = (pre.SOURCE_ROOT / relative).read_bytes()
        actual.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    assert actual == document["source_closure"]["source_facts"]
    assert document["source_closure"][
        "development_seed_identities_disjoint_from_registered_identities"
    ]


def test_v56r1_arms_and_claim_locks_are_exact():
    document = pre.freeze_mdl_adaptive_preregistration_v56r1().to_document()
    assert document["matched_single_switch_arms"]["only_switched_variable"] == (
        "REGISTERED_FACTOR_CODE_CREDIT_UNITS"
    )
    boundary = document["claim_boundary"]
    assert boundary["official_execution_allowed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["official_N_break_even"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert boundary["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
