from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_live_batched_causal_child_execution_v3 as execution
from acfqp import v075_live_batched_causal_promotion_v3 as promotion
from acfqp import v075_live_batched_causal_accounted_occurrence_v1 as accounted
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from tests import test_v075_private_observer_boundary_v2 as observer_fixture
from tests.test_v075_observer_signed_multiround_occurrence_runner_v2 import (
    _exact_schedule,
    _id,
)


@pytest.fixture(scope="module")
def executed_causal_child_union():
    generated, salt, namespace, authority, signer = observer_fixture._fixture(
        "observer-signed-multiround-capped"
    )
    schedule, schedule_verification = _exact_schedule(
        namespace,
        context_index=0,
    )
    result = accounted.run_v075_live_batched_causal_accounted_occurrence_v1(
        namespace=namespace,
        schedule=schedule,
        schedule_verification=schedule_verification,
        authority=authority,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id("live-batched-causal-execution-session"),
    )
    root_execution = result.root_execution
    root_epoch = result.root_epoch
    authorization = result.child_authorization
    authorization_verification = result.child_authorization_verification
    bundle = result.child_execution
    promotion_bundle = result.promotion_bundle
    closed_occurrence = result.budget_closure
    closed_verification = result.budget_closure_verification
    closed = closed_occurrence.observer_closure
    return {
        "namespace": namespace,
        "schedule": schedule,
        "schedule_verification": schedule_verification,
        "root_execution": root_execution,
        "root_epoch": root_epoch,
        "authorization": authorization,
        "authorization_verification": authorization_verification,
        "bundle": bundle,
        "promotion_bundle": promotion_bundle,
        "budget_closure": closed_occurrence,
        "budget_closure_verification": closed_verification,
        "accounted_occurrence": result,
        "accounting_result": result.accounting_result,
        "closed": closed,
    }


def test_signed_execution_adds_every_authorized_row_once(
    executed_causal_child_union,
) -> None:
    values = executed_causal_child_union
    authorization = values["authorization"]
    bundle = values["bundle"]
    ledger = bundle.ledger
    assert len(authorization.selected_row_binding_ids) == 16
    assert len(ledger.executed_rows) == len(
        authorization.selected_row_binding_ids
    )
    assert tuple(item.row_binding_id for item in ledger.executed_rows) == (
        authorization.selected_row_binding_ids
    )
    assert len({item.discovery_batch_id for item in ledger.executed_rows}) == 16
    assert len({item.validation_batch_id for item in ledger.executed_rows}) == 16
    assert len({item.support_freeze_id for item in ledger.executed_rows}) == 16
    assert ledger.source_head_id == values["root_epoch"].head_id
    assert ledger.resulting_head_id == bundle.resulting_epoch.head_id
    assert bundle.to_document()["observer_closed"] is False
    assert values["closed"].control_closure.final_head_id == (
        values["promotion_bundle"].final_epoch.head_id
    )


def test_child_epoch_is_exact_append_only_world_model_successor(
    executed_causal_child_union,
) -> None:
    values = executed_causal_child_union
    source = values["root_epoch"]
    authorization = values["authorization"]
    result = values["bundle"].resulting_epoch
    barrier = values["bundle"].barrier
    assert result.parent_epoch is source
    assert result.route is planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
    assert result.proof.outcome is planning.V075NumericalOutcomeV2.FAILED_FRONTIER
    assert result.proof.policy is None
    assert result.proof.failed_frontier is not None
    obligations = result.proof.failed_frontier.obligations
    assert all(
        obligation.unmaterialized_successor_ids == ()
        and obligation.current_validation_draw_count in {2_048, 8_192}
        and obligation.next_registered_checkpoint
        == obligation.current_validation_draw_count + 2_048
        for obligation in obligations
    )
    assert {item.current_validation_draw_count for item in obligations} == {
        2_048,
        8_192,
    }
    assert result.changed_row_binding_ids == (
        authorization.selected_row_binding_ids
    )
    assert result.reused_row_binding_ids == tuple(
        sorted(item.row_binding_id for item in source.model.rows)
    )
    assert len(result.model.rows) == (
        len(source.model.rows) + len(authorization.selected_row_binding_ids)
    )
    assert barrier.authorized_row_binding_ids == (
        authorization.selected_row_binding_ids
    )
    assert barrier.resulting_outcome is result.proof.outcome
    assert barrier.resulting_proof_id == result.proof.proof_id
    assert barrier.to_document()["replanning_allowed"] is True
    assert barrier.to_document()["plan_certificate"] is False


def test_execution_ledger_and_barrier_replay_from_signed_prefix(
    executed_causal_child_union,
) -> None:
    values = executed_causal_child_union
    bundle = values["bundle"]
    ledger, ledger_verification = (
        execution.verify_v075_live_batched_causal_execution_ledger_bytes_v3(
            authorization=values["authorization"],
            authorization_verification=values["authorization_verification"],
            open_prefix_verification=(
                bundle.resulting_epoch.open_prefix_verification
            ),
            claimed_bytes=bundle.ledger.canonical_bytes,
        )
    )
    barrier, barrier_verification = (
        execution.verify_v075_live_batched_causal_replanning_barrier_bytes_v3(
            authorization=values["authorization"],
            authorization_verification=values["authorization_verification"],
            execution_ledger=ledger,
            execution_verification=ledger_verification,
            resulting_epoch=bundle.resulting_epoch,
            claimed_bytes=bundle.barrier.canonical_bytes,
        )
    )
    assert ledger.ledger_id == bundle.ledger.ledger_id
    assert ledger_verification.verification_id == (
        bundle.ledger_verification.verification_id
    )
    assert barrier.barrier_id == bundle.barrier.barrier_id
    assert barrier_verification.verification_id == (
        bundle.barrier_verification.verification_id
    )


def test_replay_rejects_row_or_barrier_identity_drift(
    executed_causal_child_union,
) -> None:
    values = executed_causal_child_union
    bundle = values["bundle"]
    shortened = replace(
        bundle.ledger,
        executed_rows=bundle.ledger.executed_rows[:-1],
    )
    with pytest.raises(
        execution.V075LiveBatchedCausalExecutionV3InvariantViolation,
        match="differs from exact replay",
    ):
        execution.verify_v075_live_batched_causal_execution_ledger_bytes_v3(
            authorization=values["authorization"],
            authorization_verification=values["authorization_verification"],
            open_prefix_verification=(
                bundle.resulting_epoch.open_prefix_verification
            ),
            claimed_bytes=shortened.canonical_bytes,
        )
    document = loads_canonical_json(bundle.barrier.canonical_bytes)
    assert isinstance(document, dict)
    document["resulting_proof_id"] = "f" * 64
    with pytest.raises(
        execution.V075LiveBatchedCausalExecutionV3InvariantViolation,
        match="differs from exact replay",
    ):
        execution.verify_v075_live_batched_causal_replanning_barrier_bytes_v3(
            authorization=values["authorization"],
            authorization_verification=values["authorization_verification"],
            execution_ledger=bundle.ledger,
            execution_verification=bundle.ledger_verification,
            resulting_epoch=bundle.resulting_epoch,
            claimed_bytes=canonical_json_bytes(document),
        )


def test_execution_bundle_remains_preterminal_and_unaccounted(
    executed_causal_child_union,
) -> None:
    document = executed_causal_child_union["bundle"].to_document()
    assert document["outcome"] == "CHILD_MODEL_READY_FOR_VERIFIED_REPLANNING"
    assert document["observer_closed"] is False
    assert document["semantic_terminal_issued"] is False
    assert document["counter_records_issued"] == 0
    assert document["production_integration_ready"] is False
    assert document["official_execution_allowed"] is False
    assert execution.PRODUCTION_INTEGRATION_READY is False


def test_failed_child_frontier_executes_only_registered_2048_promotions(
    executed_causal_child_union,
) -> None:
    values = executed_causal_child_union
    child_epoch = values["bundle"].resulting_epoch
    promoted = values["promotion_bundle"]
    assert 1 <= len(promoted.barriers) <= 2
    assert len(promoted.resulting_epochs) == len(promoted.barriers)
    assert len(promoted.decisions) == len(promoted.decision_verifications)
    first = promoted.decisions[0]
    assert first.status is (
        promotion.V075LiveBatchedCausalPromotionDecisionStatusV3.AUTHORIZED
    )
    assert first.source_epoch is child_epoch
    assert first.intent is not None
    selected_source = child_epoch.row_source_for_binding_v2(
        first.intent.row_binding_id
    )
    assert first.intent.accepted_draw_start == (
        selected_source.validation_prefix_end + 1
    )
    assert first.intent.accepted_draw_count == 2_048
    assert first.intent.accepted_draw_cap == selected_source.validation_draw_cap
    assert first.intent.accepted_draw_start in {2_049, 8_193}
    assert first.intent.accepted_draw_cap in {6_144, 12_288}
    frontier = child_epoch.proof.failed_frontier
    assert frontier is not None
    expected = sorted(
        frontier.obligations,
        key=lambda item: (
            -item.interval_width_sum,
            -item.other_upper,
            item.row_id,
        ),
    )[0]
    assert first.intent.numerical_row_id == expected.row_id
    assert first.intent.to_document()["schema"] == (
        "acfqp.v075_live_promotion_authorization.v2"
    )
    assert first.intent.to_document()["profile_key"] == (
        "v075_live_dynamic_acquisition_authority_v2"
    )
    v2_projection = dynamic.V075LivePromotionIntentV2(
        dynamic._PROMOTION_INTENT_ISSUER,  # noqa: SLF001
        first.intent.source_model_epoch_id,
        first.intent.source_numerical_model_id,
        first.intent.source_proof_id,
        first.intent.source_frontier_id,
        first.intent.source_head_id,
        first.intent.occurrence_id,
        first.intent.context_id,
        first.source_epoch.arm,
        first.intent.round_index,
        first.intent.previous_decision_id,
        first.intent.numerical_row_id,
        first.intent.row_binding_id,
        first.intent.row_source_binding_id,
        first.intent.stage,
        first.intent.support_freeze_id,
        first.intent.stream_identity,
        first.intent.accepted_draw_start,
        first.intent.accepted_draw_count,
        first.intent.accepted_draw_cap,
    )
    assert first.intent.intent_id == v2_projection.intent_id
    assert first.intent.to_document() == v2_projection.to_document()
    assert first.child_execution_bundle_id == values["bundle"].bundle_id
    assert first.child_replanning_barrier_id == values["bundle"].barrier.barrier_id


def test_each_promotion_is_one_signed_append_and_one_changed_model_row(
    executed_causal_child_union,
) -> None:
    values = executed_causal_child_union
    promoted = values["promotion_bundle"]
    source = values["bundle"].resulting_epoch
    previous_barrier = None
    for index, (decision, result, barrier) in enumerate(
        zip(promoted.decisions, promoted.resulting_epochs, promoted.barriers),
        start=1,
    ):
        assert decision.round_index == index
        assert decision.intent is not None
        assert result.parent_epoch is source
        assert len(result.append_receipt_ids) == len(source.append_receipt_ids) + 1
        assert result.changed_row_binding_ids == (
            decision.intent.row_binding_id,
        )
        assert barrier.row_binding_id == decision.intent.row_binding_id
        assert barrier.source_model_epoch_id == source.model_epoch_id
        assert barrier.resulting_model_epoch_id == result.model_epoch_id
        assert barrier.resulting_proof_id == result.proof.proof_id
        assert barrier.previous_replanning_barrier_id == (
            None if previous_barrier is None else previous_barrier.barrier_id
        )
        assert set(barrier.reused_row_binding_ids) == {
            item.row_binding_id for item in source.model.rows
        } - {decision.intent.row_binding_id}
        previous_barrier = barrier
        source = result
    assert promoted.final_epoch is source


def test_promotion_result_is_honestly_candidate_or_budget_exhausted(
    executed_causal_child_union,
) -> None:
    values = executed_causal_child_union
    promoted = values["promotion_bundle"]
    final = promoted.final_epoch
    assert final.proof.outcome is planning.V075NumericalOutcomeV2.FAILED_FRONTIER
    assert promoted.outcome is (
        promotion.V075LiveBatchedCausalPromotionOutcomeV3
        .PROMOTION_BUDGET_EXHAUSTED
    )
    assert len(promoted.barriers) == 2
    document = promoted.to_document()
    assert document["observer_closed"] is False
    assert document["semantic_terminal_issued"] is False
    assert document["counter_records_issued"] == 0
    assert document["official_execution_allowed"] is False


def test_budget_exhaustion_closes_observer_without_minting_terminal_authority(
    executed_causal_child_union,
) -> None:
    values = executed_causal_child_union
    promoted = values["promotion_bundle"]
    occurrence = values["budget_closure"]
    verification = values["budget_closure_verification"]
    document = occurrence.to_document()
    replay = occurrence.budget_replay
    assert occurrence.observer_closure is values["closed"]
    assert replay.executed_round_count == 2
    assert replay.executed_promotion_draw_count == 4_096
    assert replay.final_model_epoch_id == promoted.final_epoch.model_epoch_id
    assert replay.final_proof_id == promoted.final_epoch.proof.proof_id
    assert document["observer_closed_and_exactly_reconciled"] is True
    assert document["selected_terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["selected_terminal_code"] == "ATTEMPT_BUDGET_EXHAUSTED"
    assert document["semantic_terminal_verifier_status"] == (
        "TRUSTED_BUDGET_REPLAY_NOT_IMPLEMENTED"
    )
    assert document["terminal_artifact_issued"] is False
    assert document["counter_records_issued"] == 0
    assert document["work_vector_issued"] is False
    assert verification.closure_id == occurrence.closure_id
    assert verification.trusted_budget_replay_id == replay.replay_id


def test_accounted_occurrence_materializes_exact_stage_local_vectors(
    executed_causal_child_union,
) -> None:
    result = executed_causal_child_union["accounted_occurrence"]
    accounting = executed_causal_child_union["accounting_result"]
    stages = accounting.recorded_stages
    assert result.accounting_result is accounting
    assert len(stages) == 12
    assert Counter(row.stage_start.stage_kind.value for row in stages) == {
        "PREOPEN_COMMON_PREFIX": 1,
        "INITIAL_ACQUISITION": 1,
        "INITIAL_MODEL_BUILD": 1,
        "FAILED_ABSTRACT_PREFIX": 1,
        "OPEN_INCREMENTAL_ACQUISITION": 3,
        "OPEN_CHECKPOINT_REPLANNING": 4,
        "CLOSED_RECONCILIATION_AND_TERMINALIZATION": 1,
    }
    assert all(len(row.work_vector.records) == 202 for row in stages)
    assert sum(len(row.work_vector.records) for row in stages) == 2_424
    assert sum(
        row.work_vector.values["audit.dynamic_child_closure_attestations"]
        for row in stages
    ) == 1
    assert all(
        row.work_vector.values["audit.dynamic_root_rows_scanned"] == 0
        for row in stages
        if row.stage_start.stage_kind.value
        == "OPEN_CHECKPOINT_REPLANNING"
    )
    document = accounting.to_document()
    assert document["stage_local_counter_record_count"] == 2_424
    assert document["stage_local_vectors_only"] is True
    assert document["occurrence_work_vector_issued"] is False
    assert document["shared_resource_fixed_point_complete"] is False
    assert document["all_site_completeness_claimed"] is False
    assert document["official_execution_allowed"] is False
