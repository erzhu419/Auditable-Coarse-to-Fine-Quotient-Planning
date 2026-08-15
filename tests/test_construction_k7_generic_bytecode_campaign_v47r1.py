from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_generic_bytecode_campaign_v47r1 as campaign
from acfqp import construction_k7_generic_bytecode_successor_preregistration_v47r1 as pre


@pytest.fixture(scope="module")
def frozen():
    return campaign.freeze_generic_bytecode_campaign_v47r1()


def test_v47r1_campaign_identity_and_two_generic_programs(frozen) -> None:
    assert frozen.campaign_id == campaign.CAMPAIGN_ID
    assert len(frozen.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    document = frozen.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert [row["selected_template_opcode"] for row in document["programs"]] == ["T00", "T01"]
    assert document["one_generic_synthesizer_two_programs"] is True
    assert document["lmb_named_primitive_in_compiled_bytecode"] is False
    assert "lmb" not in repr([row["compiled_bytecode"] for row in document["programs"]]).lower()


def test_v47r1_planning_uses_compiled_vm_and_failure_only_local_labels(frozen) -> None:
    document = frozen.to_document()
    assert len(document["episodes"]) == len(pre.LMB_TARGET_SEEDS) + len(pre.ROUTING_TARGET_SEEDS)
    assert all(row["terminal_status"] == "SUCCESS" for row in document["episodes"])
    assert all(row["typed_adapter_abstract_state_consumed_by_planner"] is False for row in document["episodes"])
    assert all(decision["meta_local_ground_labels"] == 0 for row in document["episodes"] for decision in row["decisions"])
    assert document["all_local_ground_labels_follow_failed_certificates"] is True
    assert document["successful_certificate_local_ground_label_count"] == 0
    assert all(signature["predeclared_semantic_support_names"] == [] for signature in document["dependency_support_signatures"])


def test_v47r1_partial_dynamics_and_strict_ood_are_honest(frozen) -> None:
    document = frozen.to_document()
    partial = document["stochastic_partial_model"]
    assert partial["support_complete_on_registered_source"] is True
    assert partial["exact_probability_authority"] is False
    assert all(row["conservative_probability_interval"] == [0, 1] for row in partial["support_rows"])
    ood = document["strict_ood_control"]
    assert ood["decision"] == "OOD_SCHEMA_REJECTED_NO_TRANSFER"
    assert ood["prior_access_count"] == 0
    assert ood["environment_outcome_count"] == 0
    assert ood["environment_step_count"] == 0


def test_v47r1_sample_tax_reduction_and_separate_axes(frozen) -> None:
    document = frozen.to_document()
    sample = document["sample_tax"]
    assert sample["meta_total_labels_including_offline"] == 312
    assert sample["strict_target_ground_labels"] == 1212
    assert sample["registered_label_saving"] == 900
    assert sample["diagnostic_episode_break_even"] == 3
    assert sample["positive_registered_condition_passed"] is True
    assert sample["broad_cross_domain_sample_efficiency_claimed"] is False
    accounting = document["accounting_axes"]
    assert accounting["labels_steps_compute_and_peak_kept_separate"] is True
    assert accounting["offline_source_labels"] == 312
    assert accounting["target_local_labels_meta"] == 0
    assert accounting["target_ground_labels_strict"] == 1212
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
