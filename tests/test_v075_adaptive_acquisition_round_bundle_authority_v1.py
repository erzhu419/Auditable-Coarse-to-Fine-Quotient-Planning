from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import ast
import hashlib
import inspect

import pytest

from acfqp import v075_adaptive_acquisition_proposal_authority_v1 as proposal
from acfqp import v075_adaptive_acquisition_round_bundle_authority_v1 as bundles
from acfqp import v075_batch_native_statistical_backend_v1 as native
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as backend
from tests import test_v075_batch_native_statistical_backend_v1 as batch_fixture
from tests import test_v075_learned_support_quotient_planners_v1 as support_fixture


def _open_observer(marker: str):
    namespace = batch_fixture._namespace(marker)
    private_authority = batch_fixture._fixture(namespace, marker)
    session = observer.open_construction_private_observer_fixture_v1(
        authority=private_authority,
        private_salt=batch_fixture._salt(marker),
        private_environment=batch_fixture._synthetic_environment(),
        observer_signer=batch_fixture._ConstructionSigner(),
        session_external_id=batch_fixture._id("session-" + marker),
    )
    return (
        namespace,
        batched.wrap_v075_construction_batched_observer_session_v1(session),
    )


def _observe_catalogue_row(
    *,
    namespace,
    wrapped,
    catalogue,
    action,
    validation_draw_count: int,
    validation_draw_cap: int,
):
    binding = graph.observation_row_binding_v1(
        catalogue.context,
        catalogue,
        action,
    )
    root_epoch, discovery_stream = batch_fixture._bootstrap_stream(
        namespace,
        binding,
        worker.V075WorkerArmV1.NO_PRIOR,
    )
    discovery = wrapped.execute_request_v1(
        wrapped.issue_request_v1(
            stream_identity=discovery_stream,
            accepted_draw_start=1,
            accepted_draw_count=64,
            accepted_draw_cap=64,
        )
    )
    selected = batch_fixture._observed_support_outcome(
        discovery,
        needs_child=catalogue.remaining_horizon == 2,
    )
    evidence = batched.freeze_v075_batch_aggregate_support_evidence_v1(
        batched_session=wrapped,
        discovery_batch=discovery,
        selected_outcome_ids=(selected.outcome_id,),
    )
    validation_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=binding,
        epoch_index=1,
        evidence=evidence,
        parent=root_epoch,
    )
    validation_chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=binding,
        epochs=(root_epoch, validation_epoch),
    )
    validation_pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=binding,
        support_chain=validation_chain,
    )
    validation_stream = graph.derive_transition_stream_identity_v1(
        pairing_authority=validation_pairing,
        arm=worker.V075WorkerArmV1.NO_PRIOR.value,
    )
    validation = wrapped.execute_request_v1(
        wrapped.issue_request_v1(
            stream_identity=validation_stream,
            accepted_draw_start=1,
            accepted_draw_count=validation_draw_count,
            accepted_draw_cap=validation_draw_cap,
        )
    )
    return discovery, validation


def _manual_batch_result(
    request: native.V075BatchNativeBackendRequestV1,
) -> native.V075BatchNativeBackendResultV1:
    grouped: dict[str, list[object]] = {}
    bindings = {}
    for item in request.batches:
        binding = item.request.stream_identity.row_binding
        grouped.setdefault(binding.row_binding_id, []).append(item)
        bindings[binding.row_binding_id] = binding
    rows = []
    for row_binding_id in sorted(grouped):
        binding = bindings[row_binding_id]
        values = grouped[row_binding_id]
        descriptor = support_fixture._descriptor(
            binding.context,
            binding.catalogue.state,
            binding.action,
            binding.remaining_horizon,
        )
        discovery_ids = tuple(
            sorted(
                item.batch_id
                for item in values
                if item.request.stream_identity.lane
                is graph.V075ObservationLaneV1.DISCOVERY
            )
        )
        validation = tuple(
            item
            for item in values
            if item.request.stream_identity.lane
            is graph.V075ObservationLaneV1.VALIDATION
        )
        validation_ids = tuple(sorted(item.batch_id for item in validation))
        support_interval, other_interval = support_fixture._intervals(
            descriptor
        )
        uncertain_intervals = (
            replace(
                support_interval,
                lower_probability=Fraction(0),
                upper_probability=Fraction(1),
            ),
            replace(
                other_interval,
                lower_probability=Fraction(0),
                upper_probability=Fraction(1),
            ),
        )
        rows.append(
            backend.V075StatisticalRowV1(
                binding.context_id,
                binding.row_binding_id,
                binding.state_id,
                binding.remaining_horizon,
                binding.action,
                discovery_ids,
                validation_ids,
                (descriptor,),
                uncertain_intervals,
                max(
                    item.request.stream_identity.observer_epoch_index
                    for item in validation
                ),
                "BATCH_NATIVE_PUBLIC_AGGREGATES_VERIFIED",
            )
        )
    rows = tuple(sorted(rows, key=lambda item: item.row_id))
    schedule = native._schedule(request)
    proposal_basis = native._proposal(request)
    model = backend.V075StatisticalModelV1(
        request.request_id,
        request.occurrence_id,
        request.arm,
        proposal_basis.proposal_id,
        schedule.schedule_id,
        rows,
        True,
        True,
        (),
    )
    status = (
        backend.V075BackendCandidateStatusV1
        .NOT_READY_TYPED_SUPPORT_GRAPH_BINDER
    )
    root_state_id = graph.root_catalogue_v1(request.context).state.state_id
    policy = backend.V075PolicyCandidateV1(
        model.model_id,
        request.arm,
        status,
        tuple(
            sorted(
                item.row_id
                for item in rows
                if item.source_state_id == root_state_id
            )
        ),
    )
    envelope = backend.V075EnvelopeCandidateV1(
        model.model_id,
        policy.policy_candidate_id,
        status,
    )
    selected_batch_ids = tuple(
        sorted(item.batch_id for item in request.batches)
    )
    total_lift = backend.V075TotalLiftCandidateInputV1(
        request.occurrence_id,
        model.model_id,
        policy.policy_candidate_id,
        envelope.envelope_candidate_id,
        status,
        tuple(item.row_id for item in rows),
        selected_batch_ids,
    )
    route_result = backend.V075RouteNativeBackendResultV1(
        request.request_id,
        request.occurrence_id,
        request.arm,
        schedule,
        proposal_basis,
        model,
        policy,
        envelope,
        total_lift,
        native._route_projection_work(
            request,
            rows,
            selected_batch_ids,
        ),
    )
    return native.V075BatchNativeBackendResultV1(
        request,
        route_result,
        native._aggregate_support_evidence_ids(request),
        selected_batch_ids,
        (),
        native._native_work(
            request=request,
            rows=rows,
            superseded_validation_draws=0,
        ),
    )


def _execute_authorized_intents(
    *,
    authorization: bundles.V075AdaptiveRoundBundleAuthorizationV1,
    prior_result: native.V075BatchNativeBackendResultV1,
    namespace,
    wrapped,
) -> tuple[object, ...]:
    appended = []
    discoveries = {}
    for intent in authorization.intents:
        if intent.kind is (
            bundles.V075BundleIntentKindV1
            .EXISTING_VALIDATION_PREFIX_EXTENSION
        ):
            stream = next(
                item.request.stream_identity
                for item in prior_result.request.batches
                if item.request.stream_identity.stream_id
                == intent.existing_stream_id
            )
            appended.append(
                wrapped.execute_request_v1(
                    wrapped.issue_request_v1(
                        stream_identity=stream,
                        accepted_draw_start=intent.accepted_draw_start,
                        accepted_draw_count=intent.accepted_draw_count,
                        accepted_draw_cap=intent.accepted_draw_cap,
                    )
                )
            )
        elif intent.kind is (
            bundles.V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY
        ):
            root_epoch, stream = batch_fixture._bootstrap_stream(
                namespace,
                intent.row_binding,
                authorization.frontier.arm,
            )
            discovery = wrapped.execute_request_v1(
                wrapped.issue_request_v1(
                    stream_identity=stream,
                    accepted_draw_start=intent.accepted_draw_start,
                    accepted_draw_count=intent.accepted_draw_count,
                    accepted_draw_cap=intent.accepted_draw_cap,
                )
            )
            appended.append(discovery)
            discoveries[intent.intent_id] = (root_epoch, discovery)
        else:
            root_epoch, discovery = discoveries[
                intent.dependency_intent_id
            ]
            selected = batch_fixture._observed_support_outcome(
                discovery,
                needs_child=False,
            )
            evidence = (
                batched.freeze_v075_batch_aggregate_support_evidence_v1(
                    batched_session=wrapped,
                    discovery_batch=discovery,
                    selected_outcome_ids=(selected.outcome_id,),
                )
            )
            validation_epoch = graph.derive_shared_support_epoch_v1(
                namespace=namespace,
                row_binding=intent.row_binding,
                epoch_index=1,
                evidence=evidence,
                parent=root_epoch,
            )
            chain = graph.freeze_shared_support_chain_v1(
                namespace=namespace,
                row_binding=intent.row_binding,
                epochs=(root_epoch, validation_epoch),
            )
            pairing = graph.freeze_five_arm_pairing_authority_v1(
                namespace=namespace,
                row_binding=intent.row_binding,
                support_chain=chain,
            )
            stream = graph.derive_transition_stream_identity_v1(
                pairing_authority=pairing,
                arm=authorization.frontier.arm.value,
            )
            appended.append(
                wrapped.execute_request_v1(
                    wrapped.issue_request_v1(
                        stream_identity=stream,
                        accepted_draw_start=intent.accepted_draw_start,
                        accepted_draw_count=intent.accepted_draw_count,
                        accepted_draw_cap=intent.accepted_draw_cap,
                    )
                )
            )
    return tuple(appended)


@pytest.fixture(scope="module")
def root_only_failure():
    marker = "round-bundle-root-only"
    namespace, wrapped = _open_observer(marker)
    context = namespace.family.replicate_contexts[0]
    root = graph.root_catalogue_v1(context)
    root_batches = tuple(
        batch
        for action in root.actions
        for batch in _observe_catalogue_row(
            namespace=namespace,
            wrapped=wrapped,
            catalogue=root,
            action=action,
            validation_draw_count=2_048,
            validation_draw_cap=6_144,
        )
    )
    request = native.freeze_v075_batch_native_backend_request_v1(
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        occurrence_ordinal=71,
        batches=root_batches,
    )
    batch_result = _manual_batch_result(request)
    planner_result = native.plan_v075_batch_native_route_v1(batch_result)
    assert planner_result.status.value == "NO_RISK_FEASIBLE_POLICY"
    return batch_result, planner_result, namespace, wrapped


def test_root_cold_draws_are_excluded_and_child_catalogue_bundle_is_frozen(
    root_only_failure,
) -> None:
    batch_result, planner_result, _namespace, _wrapped = root_only_failure
    source_view = proposal.freeze_v075_source_proposal_view_v1(
        arm=worker.V075WorkerArmV1.NO_PRIOR,
    )
    frontier = bundles.freeze_v075_adaptive_round_bundle_frontier_v1(
        batch_result=batch_result,
        planner_result=planner_result,
        source_view=source_view,
        round_index=1,
    )
    assert frontier.accounting.cold_root_draws == 2 * (64 + 2_048)
    assert frontier.accounting.incremental_draws_used == 0
    assert frontier.accounting.new_child_action_row_ids == ()
    assert frontier.candidates
    assert all(
        item.kind
        is bundles.V075BundleCandidateKindV1
        .MISSING_CHILD_COMPLETE_CATALOGUE
        for item in frontier.candidates
    )
    authorization = bundles.authorize_v075_adaptive_round_bundle_v1(
        frontier
    )
    assert authorization.status is (
        bundles.V075BundleAuthorizationStatusV1.AUTHORIZED
    )
    selected = next(
        item
        for item in frontier.candidates
        if item.candidate_id == authorization.selected_candidate_id
    )
    assert selected.child_catalogue is not None
    discoveries = tuple(
        item
        for item in authorization.intents
        if item.kind
        is bundles.V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY
    )
    validations = tuple(
        item
        for item in authorization.intents
        if item.kind
        is bundles.V075BundleIntentKindV1.NEW_CHILD_ROW_VALIDATION
    )
    assert len(discoveries) == len(selected.child_catalogue.actions)
    assert len(validations) == len(discoveries)
    assert tuple(item.dependency_intent_id for item in validations) == (
        tuple(item.intent_id for item in discoveries)
    )
    assert sum(item.accepted_draw_count for item in authorization.intents) == (
        len(discoveries) * (64 + 8_192) + 2_048
    )
    assert selected.root_promotion_included is True
    extensions = tuple(
        item
        for item in authorization.intents
        if item.kind
        is bundles.V075BundleIntentKindV1
        .EXISTING_VALIDATION_PREFIX_EXTENSION
    )
    assert len(extensions) == 1
    assert extensions[0].accepted_draw_count == 2_048
    assert authorization.intents == (
        *discoveries,
        *extensions,
        *validations,
    )
    assert authorization.to_document()[
        "support_freeze_register_barrier_after_intent_ids"
    ] == [item.intent_id for item in discoveries]
    with pytest.raises(
        bundles.V075AdaptiveRoundBundleInvariantViolation,
        match="phase order",
    ):
        replace(
            authorization,
            intents=(*extensions, *discoveries, *validations),
        )
    assert selected.source_row_binding_id == (
        selected.source_row_binding.row_binding_id
    )


def test_exact_incremental_row_and_draw_caps_cannot_be_bypassed(
    root_only_failure,
) -> None:
    batch_result, planner_result, _namespace, _wrapped = root_only_failure
    source_view = proposal.freeze_v075_source_proposal_view_v1(
        arm=worker.V075WorkerArmV1.NO_PRIOR,
    )
    frontier = bundles.freeze_v075_adaptive_round_bundle_frontier_v1(
        batch_result=batch_result,
        planner_result=planner_result,
        source_view=source_view,
        round_index=1,
    )
    selected = frontier.candidates[0]
    fake_rows = tuple(
        sorted(
            hashlib.sha256(f"accounted-child-{index}".encode()).hexdigest()
            for index in range(19)
        )
    )
    accounting = bundles.V075AdaptiveIncrementalAccountingV1(
        batch_result.result_id,
        batch_result.request.occurrence_id,
        batch_result.request.context.context_id,
        batch_result.request.arm,
        frontier.accounting.cold_root_draws,
        fake_rows,
        19 * bundles.CHILD_ROW_INITIAL_DRAWS,
        0,
        19 * bundles.CHILD_ROW_INITIAL_DRAWS,
        19,
        160_960,
        worker.V075WorkerCapProfileV1().cap_profile_id,
    )
    over_cap = replace(
        selected,
        accounting_id=accounting.accounting_id,
        cap_eligible=False,
    )
    attacked = replace(
        frontier,
        accounting=accounting,
        candidates=(over_cap,),
        ranked_candidate_ids=(over_cap.candidate_id,),
    )
    authorization = bundles.authorize_v075_adaptive_round_bundle_v1(
        attacked
    )
    assert authorization.status is (
        bundles.V075BundleAuthorizationStatusV1.INCREMENTAL_CAP_EXHAUSTED
    )
    with pytest.raises(
        bundles.V075AdaptiveRoundBundleInvariantViolation,
        match="inconsistent or over cap",
    ):
        replace(
            accounting,
            new_child_action_row_ids=(
                *fake_rows,
                hashlib.sha256(b"twentieth-child").hexdigest(),
            ),
            new_child_materialization_draws=(
                20 * bundles.CHILD_ROW_INITIAL_DRAWS
            ),
            incremental_draws_used=(
                20 * bundles.CHILD_ROW_INITIAL_DRAWS
            ),
        )


def test_round_cap_and_exact_previous_execution_are_mandatory(
    root_only_failure,
) -> None:
    batch_result, planner_result, _namespace, _wrapped = root_only_failure
    source_view = proposal.freeze_v075_source_proposal_view_v1(
        arm=worker.V075WorkerArmV1.NO_PRIOR,
    )
    with pytest.raises(
        bundles.V075AdaptiveRoundBundleInvariantViolation,
        match="two-round cap",
    ):
        bundles.freeze_v075_adaptive_round_bundle_frontier_v1(
            batch_result=batch_result,
            planner_result=planner_result,
            source_view=source_view,
            round_index=3,
        )
    with pytest.raises(
        bundles.V075AdaptiveRoundBundleInvariantViolation,
        match="round-one execution",
    ):
        bundles.freeze_v075_adaptive_round_bundle_frontier_v1(
            batch_result=batch_result,
            planner_result=planner_result,
            source_view=source_view,
            round_index=2,
        )


def test_exact_append_execution_and_round_two_dependency(
    root_only_failure,
) -> None:
    batch_result, planner_result, namespace, wrapped = root_only_failure
    source_view = proposal.freeze_v075_source_proposal_view_v1(
        arm=worker.V075WorkerArmV1.NO_PRIOR,
    )
    frontier = bundles.freeze_v075_adaptive_round_bundle_frontier_v1(
        batch_result=batch_result,
        planner_result=planner_result,
        source_view=source_view,
        round_index=1,
    )
    authorization = bundles.authorize_v075_adaptive_round_bundle_v1(
        frontier
    )
    appended = _execute_authorized_intents(
        authorization=authorization,
        prior_result=batch_result,
        namespace=namespace,
        wrapped=wrapped,
    )
    request = native.freeze_v075_batch_native_backend_request_v1(
        arm=batch_result.request.arm,
        occurrence_ordinal=batch_result.request.occurrence_ordinal,
        batches=tuple((*batch_result.request.batches, *appended)),
    )
    resulting = _manual_batch_result(request)
    execution = bundles.verify_v075_adaptive_round_bundle_execution_v1(
        authorization=authorization,
        resulting_batch_result=resulting,
    )
    selected = next(
        item
        for item in frontier.candidates
        if item.candidate_id == authorization.selected_candidate_id
    )
    assert execution.resulting_accounting.incremental_draws_used == (
        selected.incremental_draw_count
    )
    assert execution.resulting_accounting.validation_promotion_draws == (
        2_048
    )
    assert len(execution.resulting_accounting.new_child_action_row_ids) == (
        selected.new_child_action_row_count
    )

    next_plan = native.plan_v075_batch_native_route_v1(resulting)
    assert next_plan.status.value in {
        "NO_RISK_FEASIBLE_POLICY",
        "STATISTICAL_ENVELOPE_NOT_CERTIFIED",
    }
    second = bundles.freeze_v075_adaptive_round_bundle_frontier_v1(
        batch_result=resulting,
        planner_result=next_plan,
        source_view=source_view,
        round_index=2,
        previous_execution=execution,
    )
    assert second.previous_execution_id == execution.execution_id
    assert second.accounting == execution.resulting_accounting

    other_root_stream = next(
        values[0].request.stream_identity
        for values in resulting.request.batches_by_stream.values()
        if (
            values[0].request.stream_identity.row_binding.remaining_horizon
            == 2
            and values[0].request.stream_identity.lane
            is graph.V075ObservationLaneV1.VALIDATION
            and values[0].request.stream_identity.row_binding_id
            != selected.source_row_binding_id
        )
    )
    extra = wrapped.execute_request_v1(
        wrapped.issue_request_v1(
            stream_identity=other_root_stream,
            accepted_draw_start=2_049,
            accepted_draw_count=2_048,
            accepted_draw_cap=6_144,
        )
    )
    attacked_request = native.freeze_v075_batch_native_backend_request_v1(
        arm=batch_result.request.arm,
        occurrence_ordinal=batch_result.request.occurrence_ordinal,
        batches=tuple((*request.batches, extra)),
    )
    attacked = _manual_batch_result(attacked_request)
    with pytest.raises(
        bundles.V075AdaptiveRoundBundleInvariantViolation,
        match="unauthorized row or reordered bundle",
    ):
        bundles.verify_v075_adaptive_round_bundle_execution_v1(
            authorization=authorization,
            resulting_batch_result=attacked,
        )


def test_bundle_authority_has_no_process_cache_or_direct_target_access() -> None:
    source = inspect.getsource(bundles)
    assert "_FRONTIER_GRAPH_CACHE" not in source
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(
        token in name
        for name in imported
        for token in (
            "private_observer",
            "private_environment",
            "kernel",
            "exact_lift",
        )
    )
