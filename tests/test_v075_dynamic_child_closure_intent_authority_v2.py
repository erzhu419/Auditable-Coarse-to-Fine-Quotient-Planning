from __future__ import annotations

from dataclasses import fields, replace
import hashlib
from pathlib import Path

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle_v2
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_dynamic_child_closure_intent_authority_v2 as child_v2
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition_v2
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_schedule_bound_acquisition_lifecycle_v2 as initial_v2
from acfqp import v075_schedule_bound_sound_planning_authority_v2 as bridge_v2
from tests import test_v075_private_observer_boundary_v2 as observer_fixture
from tests import (
    test_v075_schedule_bound_acquisition_lifecycle_v2 as lifecycle_fixture,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-dynamic-child-intent-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _clone(value):
    forged = object.__new__(type(value))
    for item in fields(type(value)):
        if hasattr(value, item.name):
            object.__setattr__(forged, item.name, getattr(value, item.name))
    return forged


def _occurrence(namespace, *, context_index, arm):
    context = namespace.family.replicate_contexts[context_index]
    return (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=(
                context_index * len(acquisition_v2.ARM_ORDER)
                + acquisition_v2.ARM_ORDER.index(arm)
            ),
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )


def _build_upstream(values, *, context_index, arm, marker):
    namespace = values["namespace"]
    context = namespace.family.replicate_contexts[context_index]
    occurrence = _occurrence(
        namespace,
        context_index=context_index,
        arm=arm,
    )
    schedule = (
        acquisition_v2
        .freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            occurrence=occurrence,
        )
    )
    profile = schedule.profile
    slot = profile.occurrence_slot_for(
        context_id=context.context_id,
        arm=arm,
    )
    catalogue = graph.root_catalogue_v1(context)
    rows = tuple(
        graph.observation_row_binding_v1(
            context,
            catalogue,
            action,
        )
        for action in catalogue.actions
    )
    discoveries = tuple(
        lifecycle_fixture._discovery_stream(namespace, row, arm)
        for row in rows
    )
    adapter = lifecycle_fixture._open_adapter(values, occurrence, marker)
    discovery_batches = tuple(
        adapter.observe_batch_v2(
            stream_identity=stream,
            accepted_draw_start=1,
            accepted_draw_count=64,
            accepted_draw_cap=64,
        )
        for stream in discoveries
    )
    validations = ()
    if arm is not acquisition_v2.DIRECT_ARM:
        validations = tuple(
            lifecycle_fixture._validation_stream(
                namespace,
                stream,
                lifecycle_fixture._support_evidence(
                    namespace,
                    values["signer"],
                    stream,
                    batch,
                ),
                arm,
            )
            for stream, batch in zip(discoveries, discovery_batches)
        )
        for stream in validations:
            adapter.observe_batch_v2(
                stream_identity=stream,
                accepted_draw_start=1,
                accepted_draw_count=2_048,
                accepted_draw_cap=6_144,
            )
    closure = adapter.close_v2()
    lineage = batched_v2.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=occurrence,
        closure=closure,
        authority=values["authorization"],
        namespace=namespace,
        known_stream_identities=(*discoveries, *validations),
        private_salt=values["salt"],
        private_environment=values["generated"].secret_laws_for_commitment(),
    )
    if arm is acquisition_v2.DIRECT_ARM:
        current = (
            initial_v2.freeze_v075_direct_initial_lifecycle_not_applicable_v2(
                profile=profile,
                expected_slot=slot,
                schedule=schedule,
            )
        )
    else:
        current = (
            lifecycle_v2
            .freeze_v075_construction_batch_occurrence_lifecycle_v2(
                lineage=lineage,
                lineage_bytes=lineage.canonical_bytes,
                batch_closure_bytes=closure.canonical_bytes,
            )
        )
    initial = (
        initial_v2
        .freeze_v075_schedule_bound_initial_acquisition_lifecycle_v2(
            repository_root=REPOSITORY_ROOT,
            profile=profile,
            expected_slot=slot,
            schedule=schedule,
            lineage=lineage,
            construction_authority=values["authorization"],
            current_lifecycle=current,
        )
    )
    planning = (
        bridge_v2.freeze_v075_schedule_bound_sound_planning_authority_v2(
            repository_root=REPOSITORY_ROOT,
            profile=profile,
            expected_slot=slot,
            schedule=schedule,
            lineage=lineage,
            construction_authority=values["authorization"],
            current_lifecycle=current,
            initial_lifecycle=initial,
        )
    )
    return {
        "profile": profile,
        "expected_slot": slot,
        "schedule": schedule,
        "lineage": lineage,
        "construction_authority": values["authorization"],
        "current_lifecycle": current,
        "initial_lifecycle": initial,
        "planning_result": planning,
    }


def _freeze(arguments):
    return (
        child_v2.freeze_v075_dynamic_child_closure_intent_authority_v2(
            repository_root=REPOSITORY_ROOT,
            **arguments,
        )
    )


@pytest.fixture(scope="module")
def exact_graph():
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture("count-all-contexts")
    )
    return {
        "generated": generated,
        "salt": salt,
        "namespace": namespace,
        "authorization": authorization,
        "signer": signer,
    }


@pytest.fixture(scope="module")
def adaptive_authorized(exact_graph):
    arguments = _build_upstream(
        exact_graph,
        context_index=1,
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        marker="ctx-1",
    )
    return arguments, _freeze(arguments)


@pytest.fixture(scope="module")
def direct_authorized(exact_graph):
    arguments = _build_upstream(
        exact_graph,
        context_index=1,
        arm=worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        marker="ctx-1-direct",
    )
    return arguments, _freeze(arguments)


@pytest.fixture(scope="module")
def adaptive_cap(exact_graph):
    arguments = _build_upstream(
        exact_graph,
        context_index=0,
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        marker="ctx-0",
    )
    return arguments, _freeze(arguments)


def test_contract_and_production_flags_remain_locked():
    assert child_v2.PROPOSED_CONTRACT_VERSION == "1.51.0"
    assert child_v2.MAXIMUM_DISTINCT_CHILD_ACTION_ROWS == 19
    assert child_v2.CHILD_DISCOVERY_DRAWS == 64
    assert child_v2.OFFICIAL_EXECUTION_ALLOWED is False
    assert child_v2.PRODUCTION_AUTHORIZING is False
    assert child_v2.OBSERVER_ACCESS_ALLOWED is False
    assert child_v2.KERNEL_ACCESS_ALLOWED is False
    assert child_v2.WORKER_LAUNCH_ALLOWED is False
    assert child_v2.PROMOTION_ROUND_EXECUTION_ALLOWED is False
    assert child_v2.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert child_v2.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False


def test_adaptive_child_closure_is_complete_deterministic_d64_barrier(
    adaptive_authorized,
):
    arguments, result = adaptive_authorized
    planning = arguments["planning_result"]
    assert planning.terminal_code in {
        (
            bridge_v2.V075ScheduleBoundPlanningTerminalCodeV2
            .FAILED_FRONTIER_AWAITING_DYNAMIC_ACQUISITION
        ),
        (
            bridge_v2.V075ScheduleBoundPlanningTerminalCodeV2
            .CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT
        ),
    }
    assert result.status is (
        child_v2.V075DynamicChildClosureIntentStatusV2.AUTHORIZED
    )
    assert 0 < len(result.intents) <= 19
    assert tuple(
        item.row_binding.row_binding_id for item in result.intents
    ) == result.unresolved_action_row_ids
    assert len(result.unresolved_action_row_ids) == len(
        set(result.unresolved_action_row_ids)
    )
    assert len({item.state.state_id for item in result.child_states}) == len(
        result.child_states
    )
    for child in result.child_states:
        assert child.state.failure is False
        assert child.catalogue.remaining_horizon == 1
        assert tuple(item.action for item in child.row_bindings) == tuple(
            item.action
            for item in sorted(
                (
                    graph.observation_row_binding_v1(
                        child.catalogue.context,
                        child.catalogue,
                        action,
                    )
                    for action in child.catalogue.actions
                ),
                key=lambda item: item.row_binding_id,
            )
        )
        assert child.causal_parent_row_binding_ids
        assert child.causal_support_descriptor_ids
        assert child.causal_discovery_batch_ids
        assert child.causal_outcome_ids == ()
        assert child.causal_edges
        assert all(
            edge.source_kind == "ADAPTIVE_SUPPORT_DESCRIPTOR"
            and edge.row_evidence_binding_id is not None
            and edge.support_freeze_id is not None
            for edge in child.causal_edges
        )
    for intent in result.intents:
        document = intent.to_document()
        assert document["lane"] == "DISCOVERY"
        assert document["observer_epoch_index"] == 0
        assert document["follow_on_validation_epoch_index"] == 1
        assert document["accepted_draw_count"] == 64
        assert document["accepted_draw_cap"] == 64
        assert document["promotion_round_index"] is None
        assert document["promotion_rounds_consumed"] == 0
        assert document["observer_executed"] is False
        assert document["batch_generated"] is False
        assert intent.schedule_id == arguments["schedule"].schedule_id
        assert intent.lineage_id == arguments["lineage"].lineage_id
        assert intent.occurrence_id == (
            arguments["schedule"].occurrence.occurrence_id
        )
        assert intent.target_tape_namespace_id == (
            arguments["schedule"].occurrence.target_tape_namespace_id
        )
        assert intent.causal_parent_row_binding_ids
        assert intent.causal_edge_ids
    document = result.to_document()
    assert document["caller_provided_candidate_list_used"] is False
    assert document["other_instantiated"] is False
    assert document["promotion_rounds_consumed"] == 0
    assert document["observer_access"] is False
    assert document["kernel_access"] is False
    assert document["planner_invocations"] == 0
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False


def test_direct_typed_deferral_authorizes_same_complete_child_barrier(
    direct_authorized,
):
    arguments, result = direct_authorized
    assert arguments["planning_result"].terminal_code is (
        bridge_v2.V075ScheduleBoundPlanningTerminalCodeV2
        .PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION
    )
    assert result.status is (
        child_v2.V075DynamicChildClosureIntentStatusV2.AUTHORIZED
    )
    assert result.intents
    assert all(
        item.arm
        == worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND.value
        for item in result.intents
    )
    assert all(
        child.causal_numerical_row_ids == ()
        and child.causal_support_descriptor_ids == ()
        and child.causal_discovery_batch_ids
        and child.causal_outcome_ids
        and all(
            edge.source_kind == "DIRECT_DISCOVERY_OUTCOME"
            for edge in child.causal_edges
        )
        for child in result.child_states
    )
    observed_states = {
        graph.V075SymbolicGraphStateV1(
            batch.request.stream_identity.row_binding.context,
            outcome.next_ranks,
            False,
        ).state_id
        for batch in arguments["lineage"].batches
        for outcome in batch.outcomes
        if not outcome.failure and not outcome.terminal
    }
    assert {item.state.state_id for item in result.child_states} == (
        observed_states
    )


def test_distinct_action_row_cap_closes_without_subset_selection(
    adaptive_cap,
):
    _arguments, result = adaptive_cap
    assert len(result.unresolved_action_row_ids) > 19
    assert result.status is (
        child_v2.V075DynamicChildClosureIntentStatusV2
        .CHILD_ACTION_ROW_CAP_EXCEEDED
    )
    assert result.intents == ()
    document = result.to_document()
    assert document["cap_exceeded_without_subset_selection"] is True
    assert document["discovery_intent_count"] == 0
    assert document["terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False


def test_missing_child_catalogue_authority_is_typed_and_all_or_none(
    adaptive_authorized,
    monkeypatch,
):
    arguments, _authorized = adaptive_authorized
    planning = arguments["planning_result"]
    with monkeypatch.context() as scoped:
        def unavailable(*_args, **_kwargs):
            raise graph.V075PublicGraphSemanticsInvariantViolation(
                "catalogue authority unavailable"
            )

        scoped.setattr(
            child_v2,
            "_complete_child_action_catalogue",
            unavailable,
        )
        child_states, missing = child_v2._child_state_bindings(planning)
        assert child_states == ()
        assert missing == ("complete_public_child_action_catalogue",)

    monkeypatch.setattr(
        child_v2,
        "_child_state_bindings",
        lambda _planning: (
            (),
            ("complete_public_child_action_catalogue",),
        ),
    )
    result = _freeze(arguments)
    assert result.status is (
        child_v2.V075DynamicChildClosureIntentStatusV2
        .CHILD_ACTION_CATALOGUE_NOT_YET_BOUND
    )
    assert result.child_states == ()
    assert result.intents == ()
    assert result.missing_authority_fields == (
        "complete_public_child_action_catalogue",
    )
    document = result.to_document()
    assert document["discovery_intent_count"] == 0
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    verification = child_v2.V075DynamicChildClosureIntentVerificationV2(
        child_v2._VERIFICATION_ISSUER,
        result.result_id,
        planning.result_id,
        _id("typed-missing-verification"),
        result.status,
        0,
        0,
        0,
    )
    assert (
        verification.to_document()[
            "complete_public_child_catalogues_replayed"
        ]
        is False
    )
    assert (
        verification.to_document()[
            "typed_catalogue_authority_missing_verified"
        ]
        is True
    )


def test_intent_must_bind_exact_child_and_causal_edges(adaptive_authorized):
    _arguments, result = adaptive_authorized
    assert result.intents
    forged = _clone(result.intents[0])
    object.__setattr__(forged, "child_binding_id", _id("foreign-child"))
    with pytest.raises(
        child_v2.V075DynamicChildClosureIntentV2InvariantViolation
    ):
        child_v2.V075DynamicChildClosureIntentResultV2(
            child_v2._RESULT_ISSUER,
            result.planning_result,
            result.child_states,
            (forged, *result.intents[1:]),
            result.status,
            result.missing_authority_fields,
        )

    child = result.child_states[0]
    edge = child.causal_edges[0]
    forged_edge = replace(
        edge,
        support_descriptor_id=_id("foreign-support-descriptor"),
    )
    forged_child = replace(
        child,
        causal_edges=tuple(
            sorted(
                (forged_edge, *child.causal_edges[1:]),
                key=lambda item: item.edge_id,
            )
        ),
    )
    forged_intents = tuple(
        replace(
            item,
            child_binding_id=forged_child.binding_id,
            causal_edge_ids=forged_child.causal_edge_ids,
        )
        if item.child_state_id == forged_child.state.state_id
        else item
        for item in result.intents
    )
    forged_children = tuple(
        forged_child if item.state.state_id == forged_child.state.state_id else item
        for item in result.child_states
    )
    with pytest.raises(
        child_v2.V075DynamicChildClosureIntentV2InvariantViolation
    ):
        replace(
            result,
            child_states=forged_children,
            intents=forged_intents,
        )


@pytest.mark.parametrize(
    "fixture_name",
    ["adaptive_authorized", "direct_authorized", "adaptive_cap"],
)
def test_exact_bytes_verifier_replays_bridge_upstream_and_catalogues(
    fixture_name,
    request,
):
    arguments, result = request.getfixturevalue(fixture_name)
    replayed, verification = (
        child_v2.verify_v075_dynamic_child_closure_intent_result_bytes_v2(
            repository_root=REPOSITORY_ROOT,
            **arguments,
            claimed_bytes=result.canonical_bytes,
        )
    )
    assert replayed.result_id == result.result_id
    assert verification.result_id == result.result_id
    assert verification.planning_result_id == (
        arguments["planning_result"].result_id
    )
    assert verification.to_document()[
        "schedule_bound_planning_replayed"
    ] is True
    assert verification.to_document()[
        "complete_public_child_catalogues_replayed"
    ] is True
    with pytest.raises(
        child_v2.V075DynamicChildClosureIntentV2InvariantViolation
    ):
        child_v2.verify_v075_dynamic_child_closure_intent_result_bytes_v2(
            repository_root=REPOSITORY_ROOT,
            **arguments,
            claimed_bytes=result.canonical_bytes + b" ",
        )


def test_stale_planning_id_cross_arm_and_identity_mismatch_are_rejected(
    adaptive_authorized,
    direct_authorized,
):
    adaptive_arguments, adaptive_result = adaptive_authorized
    direct_arguments, _direct_result = direct_authorized

    forged_planning = _clone(adaptive_arguments["planning_result"])
    object.__setattr__(
        forged_planning,
        "_result_id",
        _id("stale-planning-result"),
    )
    stale = dict(adaptive_arguments)
    stale["planning_result"] = forged_planning
    with pytest.raises(
        child_v2.V075DynamicChildClosureIntentV2InvariantViolation
    ):
        _freeze(stale)

    with pytest.raises(
        child_v2.V075DynamicChildClosureIntentV2InvariantViolation
    ):
        child_v2.verify_v075_dynamic_child_closure_intent_result_bytes_v2(
            repository_root=REPOSITORY_ROOT,
            **direct_arguments,
            claimed_bytes=adaptive_result.canonical_bytes,
        )

    wrong_slot = dict(adaptive_arguments)
    wrong_slot["expected_slot"] = direct_arguments["expected_slot"]
    with pytest.raises(
        child_v2.V075DynamicChildClosureIntentV2InvariantViolation
    ):
        _freeze(wrong_slot)


def test_other_is_never_a_child_or_intent_even_when_validation_has_other(
    adaptive_authorized,
):
    arguments, result = adaptive_authorized
    model = arguments["planning_result"].compiler_output.model
    assert all(row.intervals[-1].event_key == "OTHER" for row in model.rows)
    serialized = result.canonical_bytes
    assert b'"other_instantiated":false' in serialized
    assert all(
        item.row_binding.state_id != "OTHER" for item in result.intents
    )


def test_production_entry_is_unconditionally_not_ready(monkeypatch):
    monkeypatch.setattr(child_v2, "OFFICIAL_EXECUTION_ALLOWED", True)
    monkeypatch.setattr(child_v2, "PRODUCTION_AUTHORIZING", True)
    with pytest.raises(
        child_v2.V075DynamicChildClosureIntentProductionV2NotReady
    ):
        (
            child_v2
            .open_v075_production_dynamic_child_closure_intent_authority_v2()
        )
