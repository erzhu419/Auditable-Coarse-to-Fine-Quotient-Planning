import hashlib

import pytest

from acfqp import construction_k7_standard_2048_fresh_terminal_preregistration_v42 as pre


def test_v42_preregistration_is_exact_and_outcome_free() -> None:
    frozen = pre.freeze_standard_2048_fresh_terminal_preregistration_v42()
    checked = pre.verify_standard_2048_fresh_terminal_preregistration_v42(frozen)
    document = checked.to_document()

    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert document["formal_execution_protocol"] == {
        "source_commit_required_before_execution": True,
        "committed_prepare_receipt_required_before_launch": True,
        "fixed_authority_and_evidence_roots_required": True,
        "fixed_parent_prepare_and_launch_journals_required": True,
        "one_shot_fixed_evidence_root_required": True,
        "o_excl_artifact_publication_required": True,
        "outer_supervisor_required": True,
        "isolated_producer_and_independent_verifier_processes_required": True,
        "isolated_python_flags": ["-I", "-S", "-B"],
        "durable_secret_bound_worker_authorization_required": True,
        "durable_one_shot_authority_consumption_required": True,
        "committed_repository_python_source_closure_required": True,
        "source_closure_scope": "COMMITTED_REPOSITORY_PYTHON_SOURCE_ONLY",
        "stdlib_and_interpreter_sources_excluded": True,
        "external_python_distributions_excluded": True,
        "non_python_resources_excluded": True,
        "runtime_unmanifested_repository_modules_forbidden": True,
        "campaign_outcome_or_terminal_fields_present": False,
        "formal_execution_performed": False,
    }
    assert document["frozen_predecessors"]["v41_evidence_scope"] == (
        "DECISION_768_CHECKPOINT_CONTINUATION_ONLY"
    )
    assert document["frozen_predecessors"][
        "v41_fresh_from_initial_or_full_game_evidence"
    ] is False


def test_v42_registers_only_fresh_two_tile_decision_zero_starts() -> None:
    document = pre.freeze_standard_2048_fresh_terminal_preregistration_v42().to_document()
    workload = document["fresh_workload"]

    assert workload["decision_index_starts_at"] == 0
    assert workload["maximum_decisions_per_episode"] == 2048
    assert workload["midgame_or_checkpoint_initial_state_allowed"] is False
    assert workload["active_state_at_decision_cap_is_fail_closed"] is True
    assert len(workload["initial_boards"]) == 2
    assert all(sum(rank != 0 for rank in board) == 2 for board in workload["initial_boards"])
    manifest = workload["complete_git_history_freshness_manifest"]
    assert manifest["all_candidates_fresh"] is True
    assert manifest["freshness_scope"] == (
        "GIT_RETAINED_SOURCE_VISIBLE_PRE_V42_CLOSURE_ONLY"
    )
    assert manifest["unretained_external_or_deleted_history_excluded"] is True
    assert manifest["universal_never_run_claimed"] is False
    assert manifest["live_tmp_diagnostic_used_as_replay_authority"] is False


def test_v42_freezes_one_model_planner_and_zero_new_labels() -> None:
    document = pre.freeze_standard_2048_fresh_terminal_preregistration_v42().to_document()
    model = document["single_frozen_world_model"]
    boundary = document["sample_and_persistence_boundary"]

    assert model["adaptive_expression_overlay_id"] == pre.ADAPTIVE_EXPRESSION_OVERLAY_ID
    assert model["adaptive_expression_proof_id"] == pre.ADAPTIVE_EXPRESSION_PROOF_ID
    assert model["adaptive_expression_model_id"] == pre.ADAPTIVE_EXPRESSION_MODEL_ID
    assert model["planner_id"] == pre.PLANNER_ID
    assert boundary["additional_model_label_budget"] == 0
    assert boundary[
        "cache_reuse_claim_must_equal_positive_cross_decision_hit_count"
    ] is True
    assert boundary["zero_cross_decision_hit_count_requires_cache_reused_false"] is True
    assert boundary["crash_resume_supported"] is False
    assert boundary["cache_persistence_may_not_be_described_as_crash_resume"] is True
    assert document["claim_boundary"]["broad_iid_sample_efficiency_claimed"] is False
    assert document["claim_boundary"]["total_operational_work_saving_claimed"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False


def test_v42_preregistration_rejects_foreign_values() -> None:
    with pytest.raises(pre.ConstructionK7Standard2048FreshTerminalPreregistrationV42Error):
        pre.verify_standard_2048_fresh_terminal_preregistration_v42(object())  # type: ignore[arg-type]
