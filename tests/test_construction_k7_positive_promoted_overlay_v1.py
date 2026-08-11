from __future__ import annotations

import hashlib
import inspect

import pytest

from acfqp import construction_k7_positive_promoted_overlay_v1 as subject
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_batch_native_total_lift_authority_v1 as total_lift_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes
from tests.test_v075_batched_causal_occurrence_successor_v1 import (
    positive_batched_occurrence,
)


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def positive_promoted(positive_batched_occurrence):
    source, _values, _sealed, lineage, exact_replay, verification = (
        positive_batched_occurrence
    )
    result = subject.run_positive_promoted_overlay_v1(
        source,
        logical_occurrence_id=_fresh_id(
            "positive-promoted-overlay-fresh-occurrence"
        ),
        query_ordinal=source.occurrence_identity.occurrence_ordinal + 1,
        lineage=lineage,
        exact_replay=exact_replay,
        source_verification=verification,
    )
    return source, lineage, exact_replay, verification, result


def test_domains_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 5
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "COUNTER_COMPLETENESS_GATE_STATUS",
        "ConstructionK7PositivePromotedOverlayV1Error",
        "LOCAL_DOMAINS",
        "OFFICIAL_EXECUTION_ALLOWED",
        "PositivePromotedAbstractPlanV1",
        "PositivePromotedExactLiftBindingV1",
        "PositivePromotedOverlayEpochV1",
        "PositivePromotedOverlayQueryV1",
        "PositivePromotedOverlayResultV1",
        "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
        "WORKLOAD_ECONOMICS_GATE_STATUS",
        "bind_positive_promoted_exact_lift_v1",
        "freeze_positive_promoted_overlay_query_v1",
        "plan_positive_promoted_overlay_query_v1",
        "promote_positive_query_neutral_overlay_v1",
        "run_positive_promoted_overlay_v1",
        "verify_positive_promoted_overlay_bytes_v1",
        "verify_positive_promoted_overlay_v1",
    }


def test_failed_source_local_distinctions_become_one_query_neutral_epoch(
    positive_promoted,
) -> None:
    source, _lineage, _exact, _verification, result = positive_promoted
    document = result.epoch.to_document()
    model = document["promoted_numerical_model"]
    assert document["source_initial_proof_status"] == "NO_RISK_FEASIBLE_POLICY"
    assert document["source_initial_failed_frontier_row_ids"]
    assert document["source_final_proof_status"] == (
        "CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT"
    )
    assert document["source_incremental_local_draw_count"] == 82_560
    assert document["source_child_action_rows_materialized"] == 10
    assert document["source_selected_causal_candidate_count"] == 5
    assert document["promoted_row_count"] == 12
    assert document["promoted_state_node_count"] == 6
    assert document["query_neutral_model_reusable_across_occurrences"] is True
    assert document["only_authorized_local_child_rows_acquired"] is True
    assert document["automatic_coordinate_invention_claimed"] is False
    assert model["occurrence_or_arm_fields_present"] is False
    assert model["private_law_access"] is False
    assert all(
        "discovery_capability_ids" not in row
        and "validation_capability_ids" not in row
        for row in model["rows"]
    )
    assert source.final_planner_result.graph.context == result.epoch.model.context


def test_fresh_h2_occurrence_plans_only_in_the_promoted_abstract_model(
    positive_promoted,
) -> None:
    source, _lineage, _exact, _verification, result = positive_promoted
    query = result.query.to_document()
    plan = result.plan.to_document()
    assert query["logical_occurrence_id"] != source.occurrence_identity.occurrence_id
    assert query["query_ordinal"] == source.occurrence_identity.occurrence_ordinal + 1
    assert query["horizon"] == 2
    assert query["observer_or_ground_input_present"] is False
    assert query["independent_random_tape_claimed"] is False
    assert plan["fresh_outcome"] == (
        "CANDIDATE_READY_FOR_INDEPENDENT_TOTAL_LIFT"
    )
    assert plan["operational_planner_call_count"] == 1
    assert plan["operational_model_build_count"] == 0
    assert plan["operational_new_ground_draw_count"] == 0
    assert plan["operational_observer_call_count"] == 0
    assert plan["operational_private_law_access_count"] == 0
    assert plan["multi_step_plan_formed_in_abstract_model"] is True
    assert result.plan.proof.outcome is planning_v2.V075NumericalOutcomeV2.CANDIDATE


def test_fresh_policy_passes_separate_construction_exact_lift(
    positive_promoted,
) -> None:
    _source, _lineage, _exact, _verification, result = positive_promoted
    document = result.exact_lift.to_document()
    assert document["source_total_lift_status"] == (
        total_lift_v1.V075BatchTotalLiftConstructionStatusV1
        .EXACT_POSITIVE_CONSTRUCTION_CONTROL.value
    )
    assert document["fresh_selected_expected_reward"] == {
        "numerator": 3,
        "denominator": 64,
    }
    assert document["fresh_selected_failure_probability"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert document["fresh_exact_normalized_regret"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert document["fresh_branch_partitions"]
    assert document["fresh_policy_was_replanned_not_replayed"] is True
    assert document["fresh_exact_lift_status"] == (
        "CONSTRUCTION_EXACT_LIFT_VALIDATED_ABSTRACT_PLAN"
    )
    assert document["exact_total_lift_execution_lane"] == (
        "STANDALONE_EVALUATION_ONLY"
    )
    assert document["construction_scope_plan_certificate_issued"] is True
    assert document["scientific_endpoint_credit_allowed"] is False


def test_result_keeps_official_accounting_and_scientific_claims_locked(
    positive_promoted,
) -> None:
    document = positive_promoted[-1].to_document()
    assert document["fresh_occurrence_new_ground_draw_count"] == 0
    assert document["fresh_occurrence_operational_planner_call_count"] == 1
    assert document["fresh_occurrence_used_promoted_model"] is True
    assert document["fresh_occurrence_multi_step_abstract_candidate"] is True
    assert document["fresh_occurrence_construction_exact_lift_validated"] is True
    assert document["local_ground_restoration_triggered_for_fresh_occurrence"] is False
    assert document["held_out_structural_family_claimed"] is False
    assert document["construction_scope_plan_certificate_count"] == 1
    assert document["scientific_plan_certificate_count"] == 0
    assert document["counter_records_issued"] == 0
    assert document["work_vector_issued"] is False
    assert document["comparison_vector_issued"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False


def test_fresh_planning_surface_accepts_no_ground_or_observer_argument() -> None:
    signature = inspect.signature(subject.plan_positive_promoted_overlay_query_v1)
    assert tuple(signature.parameters) == ("query",)


def test_typed_and_canonical_replay_reproduce_the_same_result(
    positive_promoted,
    monkeypatch,
) -> None:
    source, lineage, exact_replay, verification, result = positive_promoted

    def forbidden(*_args, **_kwargs):
        raise AssertionError("replay reopened observation or exact-replay minting")

    monkeypatch.setattr(
        total_lift_v1,
        "mint_v075_batch_native_construction_exact_replay_v1",
        forbidden,
    )
    typed = subject.verify_positive_promoted_overlay_v1(result)
    replayed = subject.verify_positive_promoted_overlay_bytes_v1(
        source=source,
        lineage=lineage,
        exact_replay=exact_replay,
        source_verification=verification,
        result_bytes=canonical_json_bytes(result.to_document()),
    )
    assert typed.result_id == result.result_id
    assert replayed.result_id == result.result_id


@pytest.mark.parametrize(
    ("path", "replacement"),
    (
        (("fresh_occurrence_new_ground_draw_count",), 1),
        (("scientific_plan_certificate_count",), 1),
        (("fresh_abstract_plan", "operational_planner_call_count"), 0),
        (("construction_exact_lift", "scientific_endpoint_credit_allowed"), True),
    ),
)
def test_resigned_identity_or_claim_changes_are_rejected(
    positive_promoted,
    path,
    replacement,
) -> None:
    source, lineage, exact_replay, verification, result = positive_promoted
    document = result.to_document()
    target = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    with pytest.raises(subject.ConstructionK7PositivePromotedOverlayV1Error):
        subject.verify_positive_promoted_overlay_bytes_v1(
            source=source,
            lineage=lineage,
            exact_replay=exact_replay,
            source_verification=verification,
            result_bytes=canonical_json_bytes(document),
        )


def test_fresh_query_and_result_are_not_caller_mintable(positive_promoted) -> None:
    _source, _lineage, _exact, _verification, result = positive_promoted
    with pytest.raises(subject.ConstructionK7PositivePromotedOverlayV1Error):
        subject.PositivePromotedOverlayQueryV1(
            object(),
            result.epoch,
            _fresh_id("caller-minted-query"),
            result.query.query_ordinal,
            result.query.threshold_profile_id,
        )
    with pytest.raises(subject.ConstructionK7PositivePromotedOverlayV1Error):
        subject.PositivePromotedOverlayResultV1(
            object(),
            result.epoch,
            result.query,
            result.plan,
            result.exact_lift,
        )
