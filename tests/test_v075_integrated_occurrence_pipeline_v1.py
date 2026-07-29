from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import v075_adaptive_acquisition_round_bundle_authority_v1 as bundle
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_integrated_occurrence_pipeline_v1 as pipeline
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_batch_native_statistical_backend_v1 as fixture


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-integrated-occurrence-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _open(
    marker: str,
    *,
    occurrence_ordinal: int,
    lifecycle_occurrence_id: str | None = None,
):
    namespace = fixture._namespace("integrated-" + marker)
    context = namespace.family.replicate_contexts[0]
    arm = worker.V075WorkerArmV1.NO_PRIOR
    caps = worker.V075WorkerCapProfileV1()
    identity = backend.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=namespace,
        context=context,
        arm=arm,
        occurrence_ordinal=occurrence_ordinal,
        threshold_profile=worker.V075WorkerThresholdProfileV1(),
        cap_profile=caps,
        source_prior_transport=None,
    )
    private_authority = fixture._fixture(
        namespace,
        "integrated-" + marker,
    )
    private_environment = fixture._synthetic_environment()
    private_salt = fixture._salt("integrated-" + marker)
    session = observer.open_construction_private_observer_fixture_v1(
        authority=private_authority,
        private_salt=private_salt,
        private_environment=private_environment,
        observer_signer=fixture._ConstructionSigner(),
        session_external_id=_id("session-" + marker),
    )
    wrapped = batched.wrap_v075_construction_batched_observer_session_v1(
        session
    )
    controller = lifecycle.open_v075_parent_owned_multistage_lifecycle_v1(
        batched_session=wrapped,
        occurrence_id=(
            identity.occurrence_id
            if lifecycle_occurrence_id is None
            else lifecycle_occurrence_id
        ),
        context_id=context.context_id,
        arm=arm,
        route_cap_profile=caps,
    )
    replay_environment = (
        batched.issue_v075_construction_batch_replay_environment_fixture_v1(
            namespace=namespace,
            private_salt=private_salt,
            private_environment=private_environment,
        )
    )
    return (
        namespace,
        context,
        arm,
        identity,
        private_authority,
        replay_environment,
        controller,
    )


@pytest.fixture(scope="module")
def completed_pipeline():
    (
        namespace,
        context,
        arm,
        identity,
        private_authority,
        replay_environment,
        controller,
    ) = _open("positive", occurrence_ordinal=701)
    result = pipeline.run_v075_integrated_adaptive_occurrence_pipeline_v1(
        controller=controller,
        namespace=namespace,
        context=context,
        arm=arm,
        occurrence_ordinal=701,
    )
    return (
        result,
        identity,
        private_authority,
        replay_environment,
        controller,
    )


def test_real_signed_observer_runs_complete_adaptive_preclose_pipeline(
    completed_pipeline,
) -> None:
    result, identity, _authority, _environment, controller = (
        completed_pipeline
    )
    verification = (
        pipeline.verify_v075_integrated_occurrence_preclose_result_v1(result)
    )
    assert verification.result_id == result.result_id
    assert result.occurrence_identity == identity
    assert result.open_lifecycle_binding.occurrence_id == identity.occurrence_id
    assert {
        item.batch_id for item in result.final_backend_result.request.batches
    } == {item.batch_id for item in controller.batches}
    assert result.initial_planner_result.status.value == (
        "NO_RISK_FEASIBLE_POLICY"
    )
    assert len(result.rounds) == 2
    assert all(
        item.authorization.status
        is bundle.V075BundleAuthorizationStatusV1.AUTHORIZED
        and item.execution is not None
        for item in result.rounds
    )
    assert result.terminal_code is (
        pipeline.V075IntegratedOccurrenceTerminalCodeV1
        .ADAPTIVE_ROUND_LIMIT_REACHED
    )
    assert result.counters.incremental_draws <= 160_960
    assert result.counters.child_action_rows_materialized <= 19
    assert result.counters.process_launches == 0
    assert result.to_document()["scientific_plan_certificate"] is False
    assert result.to_document()["occurrence_closed"] is False


def test_authorized_rounds_bind_and_follow_the_support_phase_barrier(
    completed_pipeline,
) -> None:
    result = completed_pipeline[0]
    for round_result in result.rounds:
        authorization = round_result.authorization
        if (
            authorization.status
            is not bundle.V075BundleAuthorizationStatusV1.AUTHORIZED
        ):
            continue
        discoveries = tuple(
            item
            for item in authorization.intents
            if item.kind
            is bundle.V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY
        )
        extensions = tuple(
            item
            for item in authorization.intents
            if item.kind
            is bundle.V075BundleIntentKindV1
            .EXISTING_VALIDATION_PREFIX_EXTENSION
        )
        validations = tuple(
            item
            for item in authorization.intents
            if item.kind
            is bundle.V075BundleIntentKindV1.NEW_CHILD_ROW_VALIDATION
        )
        assert authorization.intents == (
            *discoveries,
            *extensions,
            *validations,
        )
        assert round_result.to_document()[
            "support_freeze_register_phase_barrier_after_intent_ids"
        ] == [item.intent_id for item in discoveries]
        round_events = tuple(
            item
            for item in result.lifecycle_events
            if item.adaptive_round_index == round_result.round_index
        )
        phases = []
        for event in round_events:
            if event.kind in {
                lifecycle.V075LifecycleEventKindV1.ADAPTIVE_DISCOVERY_BATCH,
            }:
                phases.append(0)
            elif event.kind in {
                lifecycle.V075LifecycleEventKindV1.ADAPTIVE_SUPPORT_FREEZE,
            }:
                phases.append(1)
            else:
                phases.append(2)
        assert phases == sorted(phases)


def test_preclose_result_can_close_the_same_signed_lifecycle(
    completed_pipeline,
) -> None:
    result, _identity, authority, environment, controller = completed_pipeline
    sealed = controller.close_construction_v1(
        authority=authority,
        private_environment=environment,
        process_launches=result.counters.process_launches,
        child_intent_count=result.counters.child_action_rows_materialized,
        terminal_code=(
            lifecycle.V075LifecycleTerminalCodeV1
            .COMPLETE_REGISTERED_CHECKPOINT_CLOSED
        ),
    )
    assert sealed.closure.occurrence_id == result.occurrence_identity.occurrence_id
    assert sealed.closure.batch_ids == tuple(
        item.batch_id for item in controller.batches
    )
    assert sealed.closure.accepted_draw_count == result.counters.accepted_draws


def test_wrong_lifecycle_occurrence_is_rejected_before_first_draw() -> None:
    (
        namespace,
        context,
        arm,
        _identity,
        _authority,
        _environment,
        controller,
    ) = _open(
        "occurrence-transplant",
        occurrence_ordinal=702,
        lifecycle_occurrence_id=_id("wrong-occurrence"),
    )
    with pytest.raises(
        pipeline.V075IntegratedOccurrencePipelineInvariantViolation,
        match="frozen occurrence identity",
    ):
        pipeline.run_v075_integrated_adaptive_occurrence_pipeline_v1(
            controller=controller,
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=702,
        )
    assert controller.batches == ()
    assert controller.events == ()


def test_terminal_and_round_order_tampering_fail_closed(
    completed_pipeline,
) -> None:
    result = completed_pipeline[0]
    other = next(
        item
        for item in pipeline.V075IntegratedOccurrenceTerminalCodeV1
        if item is not result.terminal_code
    )
    with pytest.raises(
        pipeline.V075IntegratedOccurrencePipelineInvariantViolation,
        match="terminal code",
    ):
        replace(result, terminal_code=other)
    if len(result.rounds) == 2:
        with pytest.raises(
            pipeline.V075IntegratedOccurrencePipelineInvariantViolation,
            match="round chain|reordered",
        ):
            replace(result, rounds=tuple(reversed(result.rounds)))
