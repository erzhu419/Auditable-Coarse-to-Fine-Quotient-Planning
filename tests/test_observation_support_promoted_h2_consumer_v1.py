from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib

import pytest

import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.observation_support_h2_closure_v1 as h2_closure
import acfqp.observation_support_promoted_h2_consumer_v1 as consumer
import acfqp.observation_support_relational_adapter_v1 as relational
import acfqp.partial_support_expansion_authority_v1 as expansion
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _Fixture:
    context: observer.PublicGraphContextV1
    parent_closure: h2_closure.ObservationSupportH2ClosureV1
    parent_bridge: graph_model.ObservationSupportGraphModelBridgeV1
    threshold: robust.RobustThresholdProfileV1
    parent_audit: robust.RobustPlanAuditV1
    replacement: expansion.PartialSupportPromotedRowReplacementV1
    result: consumer.ObservationSupportPromotedH2ConsumerV1


@pytest.fixture(scope="module")
def built() -> _Fixture:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    parent_closure = h2_closure.acquire_observation_support_h2_closure_v1(
        context,
        2048,
        max_workers=8,
    )
    parent_bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=parent_closure.root_catalogue,
        catalogues=(
            parent_closure.root_catalogue,
            *parent_closure.child_catalogues,
        ),
        partial_rows=parent_closure.all_rows,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        parent_bridge.reward_ceiling,
    )
    parent_audit = robust.solve_ground_direct_robust_h2_v1(
        parent_bridge.direct_model,
        threshold,
    )
    authorization = expansion.authorize_partial_support_expansion_v1(
        bridge=parent_bridge,
        audit=parent_audit,
        threshold=threshold,
        partial_rows=parent_closure.all_rows,
        checkpoint_draw_count=parent_closure.validation_checkpoint,
    )
    replacement = expansion.promote_authorized_partial_support_row_v1(
        bridge=parent_bridge,
        audit=parent_audit,
        threshold=threshold,
        partial_rows=parent_closure.all_rows,
        authorization=authorization,
    )
    result = consumer.consume_partial_support_promoted_row_replacement_v1(
        context=context,
        parent_closure=parent_closure,
        parent_bridge=parent_bridge,
        parent_audit=parent_audit,
        threshold=threshold,
        replacement=replacement,
        max_workers=8,
    )
    return _Fixture(
        context,
        parent_closure,
        parent_bridge,
        threshold,
        parent_audit,
        replacement,
        result,
    )


def test_root_promotion_builds_complete_mixed_epoch_and_replans(
    built: _Fixture,
) -> None:
    result = built.result
    closure = result.promoted_closure
    counters = result.counters

    assert built.replacement.authorization.selected_remaining_horizon == 2
    assert len(closure.newly_admitted_child_catalogue_ids) == 3
    assert len(closure.newly_acquired_child_partial_row_ids) == 14
    assert len(closure.child_catalogues) == 6
    assert len(closure.all_rows) == 22
    assert sum(row.support_epoch_index == 2 for row in closure.all_rows) == 1
    assert counters.retained_parent_row_count == 7
    assert counters.promoted_row_fresh_validation_draws == 2048
    assert counters.new_child_discovery_draws == 14 * 64
    assert counters.new_child_validation_draws == 14 * 2048
    assert counters.incremental_observer_draws == 31616
    assert counters.selected_replan_policy_assignment_count == len(
        result.audit.assignments
    )
    assert "replan_policy_assignment_count" not in counters.to_document()
    assert result.bridge.source_partial_row_ids == tuple(
        sorted(row.partial_row_id for row in closure.all_rows)
    )
    assert result.audit.model_id == result.bridge.direct_model.model_id
    assert result.audit_replay.audit_id == result.audit.audit_id
    assert result.bridge_replay.bridge_id == result.bridge.bridge_id


def test_parent_is_immutable_and_only_authorized_row_is_replaced(
    built: _Fixture,
) -> None:
    closure = built.result.promoted_closure
    parent_before = built.parent_closure.to_document()
    parent_by_binding = {
        row.binding.row_id: row for row in built.parent_closure.all_rows
    }
    result_by_binding = {
        row.binding.row_id: row for row in closure.all_rows
    }
    selected = built.replacement.parent_row.binding.row_id

    assert built.parent_closure.to_document() == parent_before
    assert built.parent_closure.closure_id == closure.parent_closure.closure_id
    assert (
        result_by_binding[selected].partial_row_id
        == built.replacement.promoted_row.partial_row_id
    )
    for binding_id, row in parent_by_binding.items():
        if binding_id != selected:
            assert result_by_binding[binding_id].partial_row_id == (
                row.partial_row_id
            )


def test_promoted_mixed_epoch_quotient_upper_matches_ground_product(
    built: _Fixture,
) -> None:
    model = built.result.bridge.quotient_model
    enumerated_upper = max(
        item.reward_upper
        for item in robust._direct_policy_evaluations(
            model,
            built.threshold,
        )
    )

    quotient = robust.solve_quotient_robust_h2_v1(
        model,
        built.threshold,
    )

    assert quotient.unrestricted_reward_upper == enumerated_upper
    assert robust.verify_robust_plan_audit_v1(
        model,
        built.threshold,
        quotient,
    ).valid


def test_consumer_never_calls_evaluation_exact_authorities(
    built: _Fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("evaluation-only exact authority was called")

    monkeypatch.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    monkeypatch.setattr(observer, "evaluation_exact_ground_search_v1", forbidden)
    replayed = consumer.consume_partial_support_promoted_row_replacement_v1(
        context=built.context,
        parent_closure=built.parent_closure,
        parent_bridge=built.parent_bridge,
        parent_audit=built.parent_audit,
        threshold=built.threshold,
        replacement=built.replacement,
        max_workers=1,
    )

    assert replayed.consumer_id == built.result.consumer_id
    assert replayed.operational_exact_support_queries == 0
    assert replayed.operational_exact_probability_queries == 0
    assert replayed.evaluation_exact_atom_calls == 0
    assert replayed.exact_iid_implementation_claimed is False
    assert replayed.formal_exact_iid_plan_certificate is False
    assert replayed.statistical_claim_scope == observer.STATISTICAL_CLAIM_SCOPE


def test_parallel_schedule_is_identity_invariant_and_replayable(
    built: _Fixture,
) -> None:
    serial = consumer.consume_partial_support_promoted_row_replacement_v1(
        context=built.context,
        parent_closure=built.parent_closure,
        parent_bridge=built.parent_bridge,
        parent_audit=built.parent_audit,
        threshold=built.threshold,
        replacement=built.replacement,
        max_workers=1,
    )
    verification = consumer.verify_partial_support_promoted_h2_consumer_v1(
        context=built.context,
        parent_closure=built.parent_closure,
        parent_bridge=built.parent_bridge,
        parent_audit=built.parent_audit,
        threshold=built.threshold,
        replacement=built.replacement,
        claimed=built.result,
        max_workers=8,
    )

    assert serial.consumer_id == built.result.consumer_id
    assert serial.to_document() == built.result.to_document()
    assert verification.consumer_id == built.result.consumer_id
    assert verification.replayed_incremental_observer_draws == 31616
    assert verification.independent_algorithm_implementation is False
    assert verification.exact_iid_implementation_claimed is False


def test_stale_pending_epoch_and_coordinate_profile_fail_closed(
    built: _Fixture,
) -> None:
    pending = built.replacement.pending_model_epoch
    stale_rows = tuple(
        sorted((*pending.parent_source_partial_row_ids, _id("foreign-row")))
    )
    stale_pending = replace(
        pending,
        parent_source_partial_row_ids=stale_rows,
    )
    stale_replacement = replace(
        built.replacement,
        pending_model_epoch=stale_pending,
    )
    with pytest.raises(
        consumer.ObservationSupportPromotedH2ConsumerInvariantViolation,
        match="stale",
    ):
        consumer.consume_partial_support_promoted_row_replacement_v1(
            context=built.context,
            parent_closure=built.parent_closure,
            parent_bridge=built.parent_bridge,
            parent_audit=built.parent_audit,
            threshold=built.threshold,
            replacement=stale_replacement,
        )

    base = relational.base_coordinate_profile_v1()
    foreign_profile = replace(
        base,
        refinement_generation_id=_id("foreign-generation"),
        proposal_only_refinement=True,
    )
    with pytest.raises(
        consumer.ObservationSupportPromotedH2ConsumerInvariantViolation,
        match="stale",
    ):
        consumer.consume_partial_support_promoted_row_replacement_v1(
            context=built.context,
            parent_closure=built.parent_closure,
            parent_bridge=built.parent_bridge,
            parent_audit=built.parent_audit,
            threshold=built.threshold,
            replacement=built.replacement,
            coordinate_profile=foreign_profile,
        )


def test_closure_rejects_missing_new_child_row_and_overclaim(
    built: _Fixture,
) -> None:
    closure = built.result.promoted_closure
    with pytest.raises(
        consumer.ObservationSupportPromotedH2ConsumerInvariantViolation
    ):
        replace(closure, child_rows=closure.child_rows[:-1])
    with pytest.raises(
        consumer.ObservationSupportPromotedH2ConsumerInvariantViolation
    ):
        replace(closure, exact_iid_implementation_claimed=True)
    with pytest.raises(
        consumer.ObservationSupportPromotedH2ConsumerInvariantViolation
    ):
        replace(built.result, evaluation_exact_atom_calls=1)

    stale_pending = replace(
        built.replacement.pending_model_epoch,
        fresh_validation_observation_ids=(
            _id("unrelated-fresh-validation"),
        ),
    )
    stale_replacement = replace(
        built.replacement,
        pending_model_epoch=stale_pending,
    )
    with pytest.raises(
        consumer.ObservationSupportPromotedH2ConsumerInvariantViolation,
        match="stale",
    ):
        replace(closure, replacement=stale_replacement)
