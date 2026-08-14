from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_lmb_difference_grammar_preregistration_v44 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v44_preregistration_is_outcome_free_and_has_no_numeric_program_grid() -> None:
    frozen = pre.freeze_lmb_difference_grammar_preregistration_v44()
    document = frozen.to_document()
    acquisition = document["source_acquisition"]
    grammar = document["typed_expression_grammar"]
    assert document["outcome_fields_present"] is False
    assert document["campaign_executed"] is False
    assert acquisition["source_generation_witness_access_allowed"] is False
    assert acquisition["hidden_solution_sequence_access_allowed"] is False
    assert acquisition["candidate_predictions_used_for_action_selection"] is False
    assert grammar["candidate_program_registry_present"] is False
    assert grammar["preenumerated_rewrite_thresholds"] == []
    assert grammar["preenumerated_capacity_offsets"] == []
    assert grammar["numeric_literals_must_be_derived_from_observed_integer_equalities"] is True


def test_v44_freezes_cross_capacity_workload_protocol_and_claims() -> None:
    document = pre.freeze_lmb_difference_grammar_preregistration_v44().to_document()
    target = document["heldout_target"]
    protocol = document["planning_and_recovery_protocol"]
    assert pre.SOURCE_SPEC == {
        "tile_count": 15,
        "type_count": 5,
        "capacity": 5,
        "max_layers": 3,
    }
    assert pre.TARGET_SPEC == {
        "tile_count": 18,
        "type_count": 6,
        "capacity": 6,
        "max_layers": 4,
    }
    assert target["tile_count_changed"] is True
    assert target["type_count_changed"] is True
    assert target["capacity_changed"] is True
    assert target["layer_depth_changed"] is True
    assert target["target_outcome_observed_before_registration"] is False
    assert protocol["kernel_step_during_planning_allowed"] is False
    assert protocol["ground_distinction_requires_prior_failed_certificate"] is True
    assert protocol["successful_certificate_forbids_ground_acquisition"] is True
    assert document["open_ended_grammar_invention_claimed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_v44_preregistration_identity_domains_and_mutation_rejection() -> None:
    frozen = pre.freeze_lmb_difference_grammar_preregistration_v44()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert len(set(pre.FUTURE_DOMAINS.values())) == len(pre.FUTURE_DOMAINS)
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    forged = copy.copy(frozen)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7LMBDifferenceGrammarPreregistrationV44Error):
        pre.verify_lmb_difference_grammar_preregistration_v44(forged)
