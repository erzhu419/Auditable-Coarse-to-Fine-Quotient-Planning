from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import construction_k7_heldout_k6_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_k6_overlay_abstract_reuse_v1 as subject
from acfqp import observation_support_graph_acquisition_v1 as acquisition
from acfqp import observation_support_graph_model_v1 as graph_model
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def fresh_results():
    source = source_v1.run_heldout_k6_checkpoint_recertification_v1()
    original_planner = robust.solve_quotient_robust_h2_v1
    planner_calls: list[str] = []

    def counted_planner(model, threshold):
        planner_calls.append(model.model_id)
        return original_planner(model, threshold)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("fresh K6 abstract occurrence attempted non-planner work")

    patcher = pytest.MonkeyPatch()
    patcher.setattr(source_v1, "run_heldout_k6_checkpoint_recertification_v1", forbidden)
    patcher.setattr(acquisition, "open_graph_partial_support_prefix_v1", forbidden)
    patcher.setattr(observer, "open_target_local_transition_stream_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_ground_search_v1", forbidden)
    patcher.setattr(graph_model, "build_observation_support_graph_models_v1", forbidden)
    patcher.setattr(robust, "solve_ground_direct_robust_h2_v1", forbidden)
    patcher.setattr(robust, "solve_quotient_robust_h2_v1", counted_planner)
    try:
        first = subject.run_heldout_k6_overlay_abstract_reuse_v1(
            source,
            logical_occurrence_id=_id("k6-overlay-fresh-occurrence-1"),
            occurrence_ordinal=1,
        )
        second = subject.run_heldout_k6_overlay_abstract_reuse_v1(
            source,
            logical_occurrence_id=_id("k6-overlay-fresh-occurrence-2"),
            occurrence_ordinal=2,
        )
    finally:
        patcher.undo()
    yield source, first, second, tuple(planner_calls)


def test_domains_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 3
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "COUNTER_COMPLETENESS_GATE_STATUS",
        "ConstructionK7HeldoutK6OverlayAbstractReuseV1Error",
        "K6OverlayAbstractPlanV1",
        "K6OverlayAbstractReuseResultV1",
        "K6OverlayQueryV1",
        "LOCAL_DOMAINS",
        "OFFICIAL_EXECUTION_ALLOWED",
        "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
        "WORKLOAD_ECONOMICS_GATE_STATUS",
        "complete_heldout_k6_overlay_abstract_reuse_v1",
        "freeze_heldout_k6_overlay_query_v1",
        "run_heldout_k6_overlay_abstract_reuse_v1",
        "verify_heldout_k6_overlay_abstract_reuse_v1",
    }


def test_each_fresh_occurrence_invokes_only_one_abstract_planner(fresh_results) -> None:
    source, first, second, planner_calls = fresh_results
    expected_model_id = source.overlay.bridge.quotient_model.model_id
    assert planner_calls == (expected_model_id, expected_model_id)
    assert first.plan.audit.status is robust.RobustAuditStatus.CERTIFIED
    assert second.plan.audit.status is robust.RobustAuditStatus.CERTIFIED
    assert first.plan.audit.audit_id == source.overlay.audit.audit_id
    assert second.plan.audit.audit_id == source.overlay.audit.audit_id


def test_query_identity_changes_but_world_model_and_certificate_are_reused(
    fresh_results,
) -> None:
    source, first, second, _calls = fresh_results
    assert first.query.query_id != second.query.query_id
    assert first.result_id != second.result_id
    assert first.query.logical_occurrence_id != second.query.logical_occurrence_id
    assert first.query.quotient_model_id == second.query.quotient_model_id
    assert first.query.quotient_model_id == source.overlay.bridge.quotient_model.model_id
    assert first.plan.audit.audit_id == second.plan.audit.audit_id
    assert first.query.source_overlay_id == source.overlay.overlay_id
    assert second.query.source_overlay_id == source.overlay.overlay_id


def test_fresh_query_is_frozen_before_planning_and_accepts_no_ground_input(
    fresh_results,
) -> None:
    _source, first, _second, _calls = fresh_results
    query = first.query.to_document()
    assert query["query_frozen_before_planner_invocation"] is True
    assert query["observer_or_ground_input_present"] is False
    assert query["exact_evaluation_input_present"] is False
    assert query["model_construction_input_present"] is False
    assert query["horizon"] == 2


def test_fresh_occurrence_reuses_recovery_without_new_recovery(fresh_results) -> None:
    _source, first, _second, _calls = fresh_results
    document = first.to_document()
    assert document["fresh_occurrence_directly_abstract_certified"] is True
    assert document["certificate_failure_triggered_local_recovery"] is False
    assert document["source_local_recovery_reused_as_query_neutral_overlay"] is True
    assert document["fresh_occurrence_new_ground_draw_count"] == 0
    assert document["fresh_occurrence_observer_call_count"] == 0
    assert document["fresh_occurrence_model_build_invocations"] == 0
    assert document["fresh_occurrence_ground_solver_invocations"] == 0
    assert document["fresh_occurrence_evaluation_exact_kernel_calls"] == 0
    assert document["fresh_occurrence_abstract_planner_invocations"] == 1
    assert document["source_target_vertex_count"] == 6


def test_portable_payload_contains_source_model_threshold_and_plan(fresh_results) -> None:
    source, first, _second, _calls = fresh_results
    document = first.to_document()
    assert document["source_result"]["result_id"] == source.result_id
    assert document["final_quotient_model"]["model_id"] == (
        source.overlay.bridge.quotient_model.model_id
    )
    assert document["threshold"]["threshold_profile_id"] == (
        source.threshold.threshold_profile_id
    )
    assert document["plan"]["audit"]["audit_id"] == first.plan.audit.audit_id


def test_same_implementation_replay_is_evaluation_only(fresh_results) -> None:
    _source, first, _second, _calls = fresh_results
    verification = subject.verify_heldout_k6_overlay_abstract_reuse_v1(first)
    assert verification["valid"] is True
    assert verification["result_id"] == first.result_id
    assert verification["new_ground_draw_count"] == 0
    assert verification["observer_call_count"] == 0
    assert verification["model_build_invocations"] == 0
    assert verification["ground_solver_invocations"] == 0
    assert verification["evaluation_exact_kernel_calls"] == 0
    assert verification["independent_implementation_claimed"] is False


def test_claim_boundaries_remain_locked(fresh_results) -> None:
    document = fresh_results[1].to_document()
    assert document["formal_exact_iid_plan_certificate"] is False
    assert document["broad_cross_domain_generalization_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_caller_mint_tamper_and_bad_occurrence_are_rejected(fresh_results) -> None:
    source, first, _second, _calls = fresh_results
    with pytest.raises(subject.ConstructionK7HeldoutK6OverlayAbstractReuseV1Error):
        subject.run_heldout_k6_overlay_abstract_reuse_v1(
            source,
            logical_occurrence_id="not-an-id",
            occurrence_ordinal=3,
        )
    with pytest.raises((TypeError, ValueError)):
        replace(first.query, occurrence_ordinal=0)
    with pytest.raises(subject.ConstructionK7HeldoutK6OverlayAbstractReuseV1Error):
        subject.K6OverlayQueryV1(
            object(),
            _id("minted"),
            3,
            source.result_id,
            source.overlay.overlay_id,
            source.context.context_id,
            source.overlay.bridge.quotient_model.model_id,
            source.threshold.threshold_profile_id,
        )
