from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from acfqp import construction_k7_heldout_k6_checkpoint_recertification_v1 as subject
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


@pytest.fixture(scope="module")
def result():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("evaluation-only exact access is forbidden")

    patcher = pytest.MonkeyPatch()
    patcher.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_ground_search_v1", forbidden)
    try:
        yield subject.run_heldout_k6_checkpoint_recertification_v1()
    finally:
        patcher.undo()


def test_domains_and_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 7
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "BASE_CHECKPOINT",
        "COUNTER_COMPLETENESS_GATE_STATUS",
        "ConstructionK7HeldoutK6CheckpointRecertificationV1Error",
        "K6CausalRowCandidateV1",
        "K6CausalRowEvidenceV1",
        "K6CheckpointPreregistrationV1",
        "K6CheckpointRecertificationResultV1",
        "K6CoordinateCheckpointV1",
        "K6OverlayEpochV1",
        "K6RecoveryRequestV1",
        "K6ValidationDeltaV1",
        "LOCAL_DOMAINS",
        "OFFICIAL_EXECUTION_ALLOWED",
        "RECOVERY_CHECKPOINT",
        "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
        "WORKLOAD_ECONOMICS_GATE_STATUS",
        "run_heldout_k6_checkpoint_recertification_v1",
        "verify_heldout_k6_checkpoint_recertification_v1",
    }


def test_k6_checkpoint_and_coordinate_search_are_frozen_before_recovery(result) -> None:
    preregistration = result.preregistration.to_document()
    checkpoint = result.checkpoint.to_document()

    assert preregistration["source_vertex_counts"] == [4]
    assert preregistration["target_vertex_count"] == 6
    assert preregistration["validation_checkpoints"] == [8_192, 16_384]
    assert preregistration["max_local_transactions"] == 1
    assert preregistration["full_target_closure_authorized"] is False
    assert checkpoint["base_audit_status"] == "FAILED_PROOF_FRONTIER"
    assert checkpoint["refinement_outcome"] == "NO_SOUND_COVER"
    assert len(checkpoint["candidate_spec_ids"]) == 10
    assert checkpoint["selected_ordinal"] == 0
    assert checkpoint["selected_using_future_checkpoint_data"] is False
    assert checkpoint["observer_draws_during_coordinate_selection"] == 0


def test_complete_current_model_causal_screen_selects_one_h2_row(result) -> None:
    evidence = result.causal_evidence
    selected = evidence.selected

    assert len(evidence.candidates) == 20
    assert selected == evidence.candidates[0]
    assert selected.remaining_horizon == 2
    assert selected.planner_row_id == (
        "a768a24274c1de4f959340e111122bc76df54cf7d7d96235ab60baaed8892386"
    )
    assert selected.row_binding_id == (
        "b338551711470bc188d64f0ac667ba29760cc5c8ff829cc46f700212ff501e26"
    )
    assert selected.minimum_certificate_slack == Fraction(
        1_066_798_811, 85_899_345_920
    )
    assert selected.certified
    document = evidence.to_document()
    assert document["counterfactual_scope"] == "CURRENT_FAILED_MODEL_ONLY"
    assert document["counterfactual_observer_draws"] == 0
    assert document["future_checkpoint_data_accesses"] == 0
    assert document["minimum_authorized_cardinality"] == 1
    assert document["zero_row_baseline_failed"] is True
    assert document["global_candidate_uniqueness_claimed"] is False


def test_request_precedes_exactly_one_8192_draw_suffix(result) -> None:
    request = result.request.to_document()
    delta = result.delta.to_document()

    assert request["causal_evidence_id"] == result.causal_evidence.evidence_id
    assert request["request_frozen_before_new_observation"] is True
    assert request["single_row_only"] is True
    assert request["from_validation_checkpoint"] == 8_192
    assert request["to_validation_checkpoint"] == 16_384
    assert request["authorized_incremental_draws"] == 8_192
    assert delta["request_id"] == request["request_id"]
    assert delta["incremental_observer_draws"] == 8_192
    assert delta["predecessor_is_exact_prefix"] is True
    assert delta["request_frozen_before_new_observation"] is True


def test_one_row_overlay_certifies_and_nineteen_rows_stay_at_base(result) -> None:
    document = result.to_document()

    assert result.base_audit.status is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    assert result.overlay.audit.status is robust.RobustAuditStatus.CERTIFIED
    assert result.overlay.audit.root_failure_upper == Fraction(
        418_521_617, 8_589_934_592
    )
    assert result.overlay.audit.normalized_regret_upper == Fraction(
        58_845_161, 1_610_612_736
    )
    assert document["base_observer_draw_count"] == 20 * (64 + 8_192)
    assert document["incremental_local_ground_draw_count"] == 8_192
    assert document["changed_row_count"] == 1
    assert document["preserved_row_count"] == 19
    assert document["minimum_recovery_cardinality_within_registered_screen"] == 1
    assert document["global_row_choice_uniqueness_claimed"] is False
    assert document["rows_retained_at_base_checkpoint"] == 19
    assert document["full_16384_row_closure_built"] is False


def test_result_remains_on_world_model_mainline_without_overclaim(result) -> None:
    document = result.to_document()

    assert document["multi_step_plan_formed_in_abstract_model"] is True
    assert document["local_ground_restoration_only_after_certificate_failure"] is True
    assert document["query_neutral_overlay_reusable"] is True
    assert document["coordinate_candidates_observation_driven"] is True
    assert document["coordinate_primitive_invention_count"] == 0
    assert document["evaluation_exact_kernel_calls"] == 0
    assert document["ground_solver_invocations"] == 0
    assert document["formal_exact_iid_plan_certificate"] is False
    assert document["broad_cross_domain_generalization_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_semantic_replay_uses_no_new_observations(result) -> None:
    verification = subject.verify_heldout_k6_checkpoint_recertification_v1(result)

    assert verification["valid"] is True
    assert verification["result_id"] == result.result_id
    assert verification["replayed_causal_evidence_id"] == (
        result.causal_evidence.evidence_id
    )
    assert verification["replayed_final_overlay_id"] == result.overlay.overlay_id
    assert verification["changed_row_count"] == 1
    assert verification["preserved_row_count"] == 19
    assert verification["new_observer_draws_during_verification"] == 0
    assert verification["evaluation_exact_kernel_calls"] == 0
    assert verification["ground_solver_invocations"] == 0
    assert verification["independent_implementation_claimed"] is False


def test_caller_cannot_mint_or_rewrite_result(result) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(result, base_rows=tuple(reversed(result.base_rows)))
    document = result.to_document()
    document["preserved_row_binding_ids"].clear()
    assert len(result.to_document()["preserved_row_binding_ids"]) == 19
    with pytest.raises(
        subject.ConstructionK7HeldoutK6CheckpointRecertificationV1Error
    ):
        subject.K6CheckpointRecertificationResultV1(
            object(),
            result.preregistration,
            result.checkpoint,
            result.causal_evidence,
            result.request,
            result.delta,
            result.overlay,
            result.context,
            result.root_catalogue,
            result.child_catalogues,
            result.coordinate_profile,
            result.threshold,
            result.base_bridge,
            result.base_audit,
            result.base_rows,
        )
