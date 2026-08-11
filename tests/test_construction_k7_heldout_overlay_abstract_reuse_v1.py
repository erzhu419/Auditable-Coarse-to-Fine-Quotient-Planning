from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as subject
from acfqp import observation_support_graph_acquisition_v1 as acquisition
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def fresh_result():
    source = source_v1.run_heldout_checkpoint_recertification_v1()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("fresh abstract occurrence attempted ground access")

    patcher = pytest.MonkeyPatch()
    patcher.setattr(acquisition, "open_graph_partial_support_prefix_v1", forbidden)
    patcher.setattr(observer, "open_target_local_transition_stream_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_ground_search_v1", forbidden)
    try:
        result = subject.run_heldout_overlay_abstract_reuse_v1(
            source,
            logical_occurrence_id=_id("heldout-overlay-fresh-occurrence-v1"),
            occurrence_ordinal=2,
        )
        yield source, result
    finally:
        patcher.undo()


def test_domains_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 3
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "COUNTER_COMPLETENESS_GATE_STATUS",
        "ConstructionK7HeldoutOverlayAbstractReuseV1Error",
        "HeldoutOverlayAbstractPlanV1",
        "HeldoutOverlayAbstractReuseResultV1",
        "HeldoutOverlayQueryV1",
        "LOCAL_DOMAINS",
        "OFFICIAL_EXECUTION_ALLOWED",
        "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
        "WORKLOAD_ECONOMICS_GATE_STATUS",
        "complete_heldout_overlay_abstract_reuse_v1",
        "freeze_heldout_overlay_query_v1",
        "run_heldout_overlay_abstract_reuse_v1",
        "verify_heldout_overlay_abstract_reuse_v1",
    }


def test_fresh_query_is_bound_before_planning_and_has_no_ground_input(
    fresh_result,
) -> None:
    source, result = fresh_result
    query = result.query.to_document()
    assert query["logical_occurrence_id"] != source.result_id
    assert query["occurrence_ordinal"] == 2
    assert query["source_result_id"] == source.result_id
    assert query["source_overlay_id"] == source.final_overlay.overlay_id
    assert query["quotient_model_id"] == source.final_overlay.bridge.quotient_model.model_id
    assert query["query_frozen_before_planner_invocation"] is True
    assert query["observer_or_ground_input_present"] is False
    assert query["exact_evaluation_input_present"] is False


def test_fresh_occurrence_calls_only_the_abstract_planner(fresh_result) -> None:
    source, result = fresh_result
    plan = result.plan.to_document()
    assert result.plan.audit.status is robust.RobustAuditStatus.CERTIFIED
    assert result.plan.audit.audit_id == source.final_overlay.audit.audit_id
    assert plan["fresh_query_identity_outside_model_proof"] is True
    assert plan["abstract_planner_invocations"] == 1
    assert plan["model_build_invocations"] == 0
    assert plan["new_ground_draw_count"] == 0
    assert plan["observer_call_count"] == 0
    assert plan["ground_solver_invocations"] == 0
    assert plan["evaluation_exact_kernel_calls"] == 0
    assert plan["multi_step_plan_formed_in_abstract_model"] is True


def test_source_recovery_is_reused_without_recovery_on_fresh_query(
    fresh_result,
) -> None:
    _source, result = fresh_result
    document = result.to_document()
    assert document["fresh_occurrence_directly_abstract_certified"] is True
    assert document["certificate_failure_triggered_local_recovery"] is False
    assert document["source_local_recovery_reused_as_query_neutral_overlay"] is True
    assert document["fresh_occurrence_new_ground_draw_count"] == 0
    assert document["fresh_occurrence_observer_call_count"] == 0
    assert document["fresh_occurrence_abstract_planner_invocations"] == 1
    assert document["construction_certificate_status"] == (
        "CONDITIONAL_STATISTICAL_ABSTRACT_PLAN_CERTIFIED"
    )


def test_portable_payload_contains_model_threshold_and_parent_chain(
    fresh_result,
) -> None:
    source, result = fresh_result
    document = result.to_document()
    assert document["source_result"]["result_id"] == source.result_id
    assert document["final_quotient_model"]["model_id"] == (
        source.final_overlay.bridge.quotient_model.model_id
    )
    assert document["threshold"]["threshold_profile_id"] == (
        source.threshold.threshold_profile_id
    )
    assert document["plan"]["audit"]["audit_id"] == result.plan.audit.audit_id


def test_same_implementation_replay_adds_no_ground_work(fresh_result) -> None:
    _source, result = fresh_result
    verification = subject.verify_heldout_overlay_abstract_reuse_v1(result)
    assert verification["valid"] is True
    assert verification["result_id"] == result.result_id
    assert verification["new_ground_draw_count"] == 0
    assert verification["observer_call_count"] == 0
    assert verification["ground_solver_invocations"] == 0
    assert verification["evaluation_exact_kernel_calls"] == 0
    assert verification["independent_implementation_claimed"] is False


def test_official_and_scientific_claims_remain_locked(fresh_result) -> None:
    document = fresh_result[-1].to_document()
    assert document["formal_exact_iid_plan_certificate"] is False
    assert document["official_execution_allowed"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_invalid_occurrence_identity_is_rejected(fresh_result) -> None:
    source, _result = fresh_result
    with pytest.raises(subject.ConstructionK7HeldoutOverlayAbstractReuseV1Error):
        subject.run_heldout_overlay_abstract_reuse_v1(
            source,
            logical_occurrence_id="not-a-content-id",
            occurrence_ordinal=3,
        )
