from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import ast
import hashlib
import inspect
import os
from types import SimpleNamespace

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_integrated_direct_occurrence_pipeline_v1 as pipeline
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_batch_native_total_lift_e2e_v1 as e2e_fixture


_DIRECT_ARM = worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-integrated-direct-pipeline-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _open(marker: str, ordinal: int):
    namespace = e2e_fixture._namespace()
    context = namespace.family.replicate_contexts[1]
    authority = observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1(
        namespace,
        _id("authority-" + marker),
    )
    session = observer.open_construction_private_observer_fixture_v1(
        authority=authority,
        private_salt=e2e_fixture._salt(),
        private_environment=e2e_fixture._construction_environment(),
        observer_signer=e2e_fixture._ConstructionSigner(),
        session_external_id=_id("session-" + marker),
    )
    wrapped = batched.wrap_v075_construction_batched_observer_session_v1(
        session
    )
    caps = worker.V075WorkerCapProfileV1()
    identity = backend.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=namespace,
        context=context,
        arm=_DIRECT_ARM,
        occurrence_ordinal=ordinal,
        threshold_profile=worker.V075WorkerThresholdProfileV1(),
        cap_profile=caps,
        source_prior_transport=None,
    )
    controller = (
        lifecycle.open_v075_parent_owned_multistage_lifecycle_v1(
            batched_session=wrapped,
            occurrence_id=identity.occurrence_id,
            context_id=context.context_id,
            arm=_DIRECT_ARM,
            route_cap_profile=caps,
        )
    )
    return namespace, context, identity, controller


def _point_checkpoint(
    draw_count: int,
    success_count: int,
    _event_count: int,
    _checkpoints: tuple[int, ...],
) -> SimpleNamespace:
    """Fast exact-typed mechanics fixture, not a confidence certificate."""

    empirical = Fraction(success_count, draw_count)
    return SimpleNamespace(
        empirical_probability=empirical,
        lower_probability=empirical,
        upper_probability=empirical,
        exact_likelihood_comparisons=0,
        log_search_evaluations=0,
    )


def _typed_mechanics_ready_planner(
    result: backend.V075BatchNativeBackendResultV1,
) -> planners.V075SupportPlannerResultV1:
    """Build a typed ready object without running the full policy search.

    The fixture exercises only pipeline causality, identity binding, public
    replay, and attack rejection.  The opt-in smoke below retains the
    canonical confidence construction and exact matched-direct planner.
    """

    support_graph = backend.compile_v075_batch_native_support_graph_v1(
        result
    )
    route = planners.V075PlannerRouteV1.MATCHED_DIRECT_GROUND
    decisions = []
    for node in support_graph.nodes:
        selected = node.rows[0]
        choice = planners.V075PolicyStateChoiceV1(
            node.state_id,
            (selected.action,),
            (selected.row_id,),
            (Fraction(1),),
        )
        decisions.append(
            planners.V075DeterministicPolicyDecisionV1(
                route,
                node.remaining_horizon,
                node.state_id,
                selected.row_id,
                (choice,),
            )
        )
    policy = planners.V075DeterministicH2PolicyV1(
        support_graph.graph_id,
        route,
        None,
        tuple(
            sorted(
                decisions,
                key=lambda item: (
                    -item.remaining_horizon,
                    item.decision_domain_id,
                ),
            )
        ),
    )
    envelope = planners.V075RobustH2EnvelopeV1(
        policy,
        Fraction(0),
        Fraction(0),
        Fraction(0),
        Fraction(0),
        Fraction(0),
        support_graph.familywise_confidence_error_upper,
    )
    values = {path: 0 for path in planners.PLANNER_COUNTER_PATHS}
    values.update(
        {
            "common.learned_support_graph_checks": 1,
            "direct.planner_calls": 1,
            "direct.ground_states_considered": len(support_graph.nodes),
            "direct.ground_actions_considered": sum(
                len(item.rows) for item in support_graph.nodes
            ),
            "common.total_lift_candidate_emissions": 1,
        }
    )
    work = planners.V075SupportPlannerWorkV1(
        support_graph.graph_id,
        route,
        tuple(
            planners.V075SupportPlannerCounterV1(path, values[path])
            for path in planners.PLANNER_COUNTER_PATHS
        ),
    )
    return planners.V075SupportPlannerResultV1(
        support_graph,
        route,
        None,
        (
            planners.V075PlannerStatusV1
            .CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT
        ),
        policy,
        envelope,
        (),
        work,
        planners.MAX_EXACT_POLICY_ASSIGNMENTS,
    )


@pytest.fixture(scope="module")
def mechanics_result():
    patcher = pytest.MonkeyPatch()
    patcher.setattr(backend, "_cached_checkpoint", _point_checkpoint)
    patcher.setattr(
        backend,
        "plan_v075_batch_native_route_v1",
        _typed_mechanics_ready_planner,
    )
    try:
        _namespace, context, identity, controller = _open(
            "mechanics",
            75_401,
        )
        result = (
            pipeline.execute_v075_integrated_direct_occurrence_preclose_v1(
                occurrence_identity=identity,
                observer_lifecycle=controller,
            )
        )
        verification = (
            pipeline.verify_v075_integrated_direct_occurrence_preclose_v1(
                result
            )
        )
    finally:
        patcher.undo()
    return context, identity, controller, result, verification


def test_direct_preclose_mechanics_replay_and_identity(
    mechanics_result,
) -> None:
    _context, identity, controller, result, verification = mechanics_result
    assert result.occurrence_identity == identity
    assert result.open_binding == controller.open_binding
    assert result.terminal is (
        pipeline.V075IntegratedDirectTerminalV1
        .READY_FOR_EXACT_TOTAL_LIFT
    )
    assert len(result.checkpoint_history) == 1
    assert result.checkpoint_history[0].checkpoint == 2_048
    assert verification.result_id == result.result_id
    assert verification.work_id == result.work.work_id
    assert verification.to_document()["verifier_target_accessed"] is False
    assert verification.to_document()[
        "occurrence_target_batches_present"
    ] is True
    assert result.to_document()["scientific_plan_certificate"] is False
    assert result.to_document()["lifecycle_closed"] is False


def test_direct_pipeline_keeps_the_global_phase_barriers(
    mechanics_result,
) -> None:
    _context, _identity, _controller, result, _verification = (
        mechanics_result
    )
    phases = []
    for event in result.events:
        if event.kind is lifecycle.V075LifecycleEventKindV1.DISCOVERY_BATCH:
            phases.append(0)
        elif event.kind is lifecycle.V075LifecycleEventKindV1.SUPPORT_FREEZE:
            phases.append(1)
        elif event.kind is lifecycle.V075LifecycleEventKindV1.VALIDATION_BATCH:
            phases.append(2)
        else:
            pytest.fail(f"unexpected direct lifecycle event: {event.kind}")
    assert phases == sorted(phases)
    assert phases.count(0) == result.work.values["support.rows_frozen"]
    assert phases.count(1) == result.work.values["support.rows_frozen"]
    assert phases.count(2) == result.work.values["validation.rows"]


def test_every_observed_root_child_gets_its_complete_action_catalogue(
    mechanics_result,
) -> None:
    context, _identity, _controller, result, _verification = mechanics_result
    root_batches = tuple(
        item
        for item in result.batches
        if (
            item.request.stream_identity.lane
            is graph.V075ObservationLaneV1.DISCOVERY
            and item.request.stream_identity.row_binding.remaining_horizon
            == 2
        )
    )
    observed = {}
    expected_by_batch = {}
    for batch in root_batches:
        state_ids = set()
        for outcome in batch.outcomes:
            state = graph.V075SymbolicGraphStateV1(
                context,
                outcome.next_ranks,
                outcome.failure,
            )
            if not state.failure:
                state_ids.add(state.state_id)
                observed[state.state_id] = state
        expected_by_batch[batch.batch_id] = tuple(sorted(state_ids))
    assert {
        item.root_batch_id: item.distinct_nonfailure_child_state_ids
        for item in result.root_child_bindings
    } == expected_by_batch
    assert tuple(
        item.state.state_id for item in result.child_catalogue_bindings
    ) == tuple(sorted(observed))
    for item in result.child_catalogue_bindings:
        assert item.catalogue.actions == graph.legal_action_triples_v1(
            context,
            item.state.ranks,
            item.state.failure,
        )
        assert tuple(row.action for row in item.row_bindings) == (
            item.catalogue.actions
        )


def test_all_rows_use_one_checkpoint_prefix_and_counter_vector(
    mechanics_result,
) -> None:
    _context, _identity, _controller, result, _verification = (
        mechanics_result
    )
    checkpoint = result.checkpoint_history[0]
    validation_groups = tuple(
        values
        for values in checkpoint.request.batches_by_stream.values()
        if (
            values[0].request.stream_identity.lane
            is graph.V075ObservationLaneV1.VALIDATION
        )
    )
    assert validation_groups
    assert {
        sum(item.request.accepted_draw_count for item in values)
        for values in validation_groups
    } == {2_048}
    values = result.work.values
    assert tuple(values) == pipeline.DIRECT_PIPELINE_COUNTER_PATHS
    assert values["common.per_draw_capabilities_materialized"] == 0
    assert values["planning.checkpoints_evaluated"] == 1
    assert values["planning.backend_compilations"] == 1
    assert values["planning.matched_direct_planner_invocations"] == 1
    assert values["planning.ready_checkpoint_count"] == 1


def test_reused_lifecycle_is_rejected_before_any_new_draw(
    mechanics_result,
) -> None:
    _context, identity, controller, _result, _verification = mechanics_result
    before = tuple(item.batch_id for item in controller.batches)
    with pytest.raises(
        pipeline.V075IntegratedDirectPipelineInvariantViolation,
        match="used, transplanted, non-direct, or not pre-sampling",
    ):
        pipeline.execute_v075_integrated_direct_occurrence_preclose_v1(
            occurrence_identity=identity,
            observer_lifecycle=controller,
        )
    assert tuple(item.batch_id for item in controller.batches) == before


def test_occurrence_identity_transplant_is_rejected() -> None:
    _namespace, _context, identity, controller = _open(
        "identity-transplant-base",
        75_402,
    )
    other_namespace, other_context, _other_identity, _other_controller = _open(
        "identity-transplant-other",
        75_403,
    )
    foreign = backend.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=other_namespace,
        context=other_context,
        arm=_DIRECT_ARM,
        occurrence_ordinal=75_404,
        threshold_profile=worker.V075WorkerThresholdProfileV1(),
        cap_profile=worker.V075WorkerCapProfileV1(),
        source_prior_transport=None,
    )
    with pytest.raises(
        pipeline.V075IntegratedDirectPipelineInvariantViolation,
        match="used, transplanted, non-direct, or not pre-sampling",
    ):
        pipeline.execute_v075_integrated_direct_occurrence_preclose_v1(
            occurrence_identity=foreign,
            observer_lifecycle=controller,
        )
    assert identity.occurrence_id == controller.open_binding.occurrence_id
    assert controller.batches == ()


def test_public_replay_rejects_child_omission_and_reordering(
    mechanics_result,
) -> None:
    _context, _identity, _controller, result, _verification = (
        mechanics_result
    )
    omitted = replace(
        result,
        child_catalogue_bindings=result.child_catalogue_bindings[:-1],
    )
    with pytest.raises(
        pipeline.V075IntegratedDirectPipelineInvariantViolation,
        match="root/child closure differs",
    ):
        pipeline.verify_v075_integrated_direct_occurrence_preclose_v1(
            omitted
        )
    reordered = replace(
        result,
        child_catalogue_bindings=tuple(
            reversed(result.child_catalogue_bindings)
        ),
    )
    with pytest.raises(
        pipeline.V075IntegratedDirectPipelineInvariantViolation,
        match="root/child closure differs",
    ):
        pipeline.verify_v075_integrated_direct_occurrence_preclose_v1(
            reordered
        )


def test_public_replay_rejects_batch_and_checkpoint_reordering(
    mechanics_result,
) -> None:
    _context, _identity, _controller, result, _verification = (
        mechanics_result
    )
    discovery_count = result.work.values["support.rows_frozen"]
    attacked_batches = (
        *result.batches[:discovery_count],
        *reversed(result.batches[discovery_count:]),
    )
    attacked = replace(result, batches=tuple(attacked_batches))
    with pytest.raises(
        pipeline.V075IntegratedDirectPipelineInvariantViolation,
        match="checkpoint was reordered or re-capped",
    ):
        pipeline.verify_v075_integrated_direct_occurrence_preclose_v1(
            attacked
        )
    with pytest.raises(
        pipeline.V075IntegratedDirectPipelineInvariantViolation,
        match="do not share one exact prefix",
    ):
        replace(result.checkpoint_history[0], checkpoint=4_096)


def test_terminal_and_physical_cap_attacks_are_typed(
    mechanics_result,
) -> None:
    _context, identity, _controller, result, _verification = mechanics_result
    with pytest.raises(
        pipeline.V075IntegratedDirectPipelineInvariantViolation,
        match="terminal disagrees",
    ):
        replace(
            result,
            terminal=(
                pipeline.V075IntegratedDirectTerminalV1
                .DIRECT_CHECKPOINT_CAP_EXHAUSTED
            ),
        )
    failure = pipeline.V075IntegratedDirectPhysicalRowCapExceeded(
        occurrence_id=identity.occurrence_id,
        observed_physical_rows=20,
        maximum_physical_rows=19,
        retained_root_batch_ids=tuple(
            sorted(
                item.root_batch_id for item in result.root_child_bindings
            )
        ),
    )
    document = failure.to_document()
    assert document["terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["terminal_code"] == (
        "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED"
    )
    assert document["lifecycle_close_required"] is True
    assert document["root_work_retained"] is True
    assert document["scientific_plan_certificate"] is False


def test_production_pipeline_has_no_private_or_per_draw_dependency() -> None:
    tree = ast.parse(inspect.getsource(pipeline))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(
        "private_observer" in name
        or "kernel" in name
        or "per_draw" in name
        for name in imported
    )
    execute_source = inspect.getsource(
        pipeline.execute_v075_integrated_direct_occurrence_preclose_v1
    )
    assert "compile_v075_batch_native_statistical_backend_v1" not in (
        execute_source
    )
    checkpoint_source = inspect.getsource(pipeline._checkpoint)
    assert "compile_v075_batch_native_statistical_backend_v1" in (
        checkpoint_source
    )
    assert "plan_v075_batch_native_route_v1" in checkpoint_source
    assert pipeline.PER_DRAW_CAPABILITY_EXPANSION_ALLOWED is False
    assert pipeline.PRODUCTION_INTEGRATION_READY is False


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_V075_INTEGRATED_DIRECT_REAL") != "1",
    reason=(
        "canonical confidence + exact matched-direct checkpoint is opt-in; "
        "set ACFQP_RUN_V075_INTEGRATED_DIRECT_REAL=1"
    ),
)
def test_opt_in_real_canonical_checkpoint_and_public_replay() -> None:
    _namespace, _context, _identity, controller = _open(
        "real-canonical",
        75_499,
    )
    result = pipeline.execute_v075_integrated_direct_occurrence_preclose_v1(
        occurrence_identity=_identity,
        observer_lifecycle=controller,
    )
    verification = (
        pipeline.verify_v075_integrated_direct_occurrence_preclose_v1(result)
    )
    assert verification.result_id == result.result_id
    assert result.checkpoint_history[0].checkpoint == 2_048
    assert all(
        item.request.occurrence_identity == _identity
        for item in result.checkpoint_history
    )
