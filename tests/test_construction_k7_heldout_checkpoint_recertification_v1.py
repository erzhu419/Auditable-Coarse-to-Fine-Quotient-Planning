from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as subject
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
        yield subject.run_heldout_checkpoint_recertification_v1()
    finally:
        patcher.undo()


def test_domains_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 7
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "BASE_CHECKPOINT",
        "COUNTER_COMPLETENESS_GATE_STATUS",
        "ConstructionK7HeldoutCheckpointRecertificationV1Error",
        "HeldoutCausalRowEvidenceV1",
        "HeldoutCheckpointPreregistrationV1",
        "HeldoutCheckpointRecertificationResultV1",
        "HeldoutCheckpointTransactionV1",
        "HeldoutCoordinateCheckpointV1",
        "HeldoutOverlayEpochV1",
        "HeldoutRecoveryRequestV1",
        "HeldoutValidationDeltaV1",
        "LOCAL_DOMAINS",
        "OFFICIAL_EXECUTION_ALLOWED",
        "RECOVERY_CHECKPOINT",
        "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
        "WORKLOAD_ECONOMICS_GATE_STATUS",
        "run_heldout_checkpoint_recertification_v1",
        "verify_heldout_checkpoint_recertification_v1",
    }


def test_heldout_coordinate_checkpoint_is_complete_and_failed(result) -> None:
    preregistration = result.preregistration.to_document()
    checkpoint = result.checkpoint.to_document()
    assert preregistration["source_vertex_counts"] == [4]
    assert preregistration["target_vertex_count"] == 5
    assert preregistration["validation_checkpoints"] == [2_048, 4_096]
    assert preregistration["max_local_transactions"] == 2
    assert preregistration["full_target_closure_authorized"] is False
    assert checkpoint["candidate_ordinal"] == 1
    assert checkpoint["candidate_count"] == 12
    assert len(checkpoint["failed_candidate_audit_ids"]) == 12
    assert checkpoint["base_outcome"] == "FAILED_PROOF_FRONTIER"
    assert checkpoint["refinement_outcome"] == "NO_SOUND_COVER"
    assert checkpoint["selected_using_future_checkpoint_data"] is False


def test_two_requests_are_frozen_before_two_single_row_extensions(result) -> None:
    first, second = result.transactions
    assert first.evidence.selected.remaining_horizon == 2
    assert second.evidence.selected.remaining_horizon == 1
    assert first.evidence.selected.row_binding_id != second.evidence.selected.row_binding_id
    assert second.evidence.excluded_row_binding_ids == (
        first.evidence.selected.row_binding_id,
    )
    for transaction in result.transactions:
        request = transaction.request.to_document()
        delta = transaction.delta.to_document()
        assert request["request_frozen_before_new_observation"] is True
        assert request["single_row_only"] is True
        assert request["authorized_incremental_draws"] == 2_048
        assert delta["request_id"] == request["request_id"]
        assert delta["incremental_observer_draws"] == 2_048
        assert delta["predecessor_is_exact_prefix"] is True
        assert delta["request_frozen_before_new_observation"] is True


def test_first_overlay_fails_and_second_abstract_replan_certifies(result) -> None:
    first, second = (item.overlay for item in result.transactions)
    assert first.audit.status is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    assert second.audit.status is robust.RobustAuditStatus.CERTIFIED
    assert first.audit.root_failure_upper == Fraction(436_452_637, 8_589_934_592)
    assert first.audit.normalized_regret_upper == Fraction(
        497_841_463, 12_884_901_888
    )
    assert second.audit.root_failure_upper == Fraction(420_251_141, 8_589_934_592)
    assert second.audit.normalized_regret_upper == Fraction(
        481_639_967, 12_884_901_888
    )
    assert first.to_document()["ground_solver_invocations"] == 0
    assert second.to_document()["evaluation_exact_kernel_calls"] == 0


def test_only_two_ground_rows_change_and_six_remain_at_2048(result) -> None:
    document = result.to_document()
    assert document["base_observer_draw_count"] == 8 * (64 + 2_048)
    assert document["incremental_local_ground_draw_count"] == 4_096
    assert document["changed_row_count"] == 2
    assert document["preserved_row_count"] == 6
    assert document["rows_retained_at_base_checkpoint"] == 6
    assert document["full_4096_row_closure_built"] is False
    assert len(document["changed_row_binding_ids"]) == 2
    assert len(document["preserved_row_binding_ids"]) == 6


def test_result_stays_on_the_abstract_world_model_mainline(result) -> None:
    document = result.to_document()
    assert document["multi_step_plan_formed_in_abstract_model"] is True
    assert document["local_ground_restoration_only_after_certificate_failure"] is True
    assert document["query_neutral_overlay_reusable"] is True
    assert document["construction_certificate_status"] == (
        "CONDITIONAL_STATISTICAL_ABSTRACT_PLAN_CERTIFIED"
    )
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
    verification = subject.verify_heldout_checkpoint_recertification_v1(result)
    assert verification["valid"] is True
    assert verification["result_id"] == result.result_id
    assert verification["replayed_final_overlay_id"] == result.final_overlay.overlay_id
    assert verification["new_observer_draws_during_verification"] == 0
    assert verification["evaluation_exact_kernel_calls"] == 0
    assert verification["ground_solver_invocations"] == 0
    assert verification["independent_implementation_claimed"] is False


def test_caller_cannot_replace_or_mint_the_result(result) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(result, transactions=tuple(reversed(result.transactions)))
    document = result.to_document()
    document["changed_row_binding_ids"].clear()
    assert len(result.to_document()["changed_row_binding_ids"]) == 2
    with pytest.raises(subject.ConstructionK7HeldoutCheckpointRecertificationV1Error):
        subject.HeldoutCheckpointRecertificationResultV1(
            object(),
            result.preregistration,
            result.checkpoint,
            result.context,
            result.root_catalogue,
            result.child_catalogues,
            result.coordinate_profile,
            result.threshold,
            result.base_bridge,
            result.base_audit,
            result.base_rows,
            result.transactions,
        )
