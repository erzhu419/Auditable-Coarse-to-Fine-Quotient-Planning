from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_live_batched_causal_child_authority_v3 as causal
from acfqp import v075_live_batched_causal_child_execution_v3 as execution
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as runner
from tests import test_v075_private_observer_boundary_v2 as observer_fixture
from tests.test_v075_observer_signed_multiround_occurrence_runner_v2 import (
    REPOSITORY_ROOT,
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
    controller = control.open_v075_construction_controlled_private_observer_v2(
        authority=authority,
        namespace=namespace,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id("live-batched-causal-execution-session"),
        occurrence_identity=schedule.occurrence,
    )
    root_execution = runner._execute_initial_root_schedule(  # noqa: SLF001
        controller=controller,
        namespace=namespace,
        schedule=schedule,
        verification=schedule_verification,
    )
    root_epoch = runner._freeze_root_epoch(  # noqa: SLF001
        controller=controller,
        schedule=schedule,
    )
    authorization = causal.authorize_v075_live_batched_causal_children_v3(
        source_epoch=root_epoch,
        namespace=namespace,
    )
    authorization, authorization_verification = (
        causal.verify_v075_live_batched_causal_child_authorization_bytes_v3(
            source_epoch=root_epoch,
            namespace=namespace,
            claimed_bytes=authorization.canonical_bytes,
        )
    )
    bundle = execution.execute_v075_live_batched_causal_children_v3(
        controller=controller,
        namespace=namespace,
        schedule=schedule,
        authorization=authorization,
        authorization_verification=authorization_verification,
    )
    closed = controller.close_and_reconcile_v2()
    return {
        "namespace": namespace,
        "schedule": schedule,
        "schedule_verification": schedule_verification,
        "root_execution": root_execution,
        "root_epoch": root_epoch,
        "authorization": authorization,
        "authorization_verification": authorization_verification,
        "bundle": bundle,
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
        ledger.resulting_head_id
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
    assert all(
        obligation.unmaterialized_successor_ids == ()
        and obligation.current_validation_draw_count == 8_192
        and obligation.next_registered_checkpoint == 10_240
        for obligation in result.proof.failed_frontier.obligations
    )
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
