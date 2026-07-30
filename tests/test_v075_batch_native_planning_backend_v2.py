from __future__ import annotations

from dataclasses import fields, replace
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle
from acfqp import v075_batched_observer_authority_v2 as batched
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_batch_occurrence_lifecycle_authority_v2 as life_fixture
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-batch-planning-v2-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _post_spawn(
    binding: graph.V075ObservationRowBindingV1,
    *,
    spawn_cell: int,
    spawn_rank: int,
) -> tuple[tuple[int, ...], bool, bool]:
    board = list(binding.catalogue.state.ranks)
    first, second, survivor = binding.action
    rank = board[first]
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, binding.context.rank_cap)
    assert board[spawn_cell] == 0
    board[spawn_cell] = spawn_rank
    ranks = tuple(board)
    failure = not graph.legal_action_triples_v1(
        binding.context,
        ranks,
        False,
    )
    terminal = failure or binding.remaining_horizon == 1
    return ranks, failure, terminal


def _safe_successor(
    binding: graph.V075ObservationRowBindingV1,
) -> tuple[tuple[int, ...], bool, bool]:
    board = list(binding.catalogue.state.ranks)
    first, second, survivor = binding.action
    rank = board[first]
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, binding.context.rank_cap)
    for cell, value in enumerate(board):
        if value != 0:
            continue
        for spawn_rank in range(1, binding.context.rank_cap + 1):
            candidate = _post_spawn(
                binding,
                spawn_cell=cell,
                spawn_rank=spawn_rank,
            )
            if not candidate[1]:
                return candidate
    raise AssertionError("fixture row has no safe structural successor")


def _exact_row(
    binding: graph.V075ObservationRowBindingV1,
    successor: tuple[tuple[int, ...], bool, bool],
) -> planning.V075NumericalRowV2:
    return planning.freeze_v075_manual_construction_row_v2(
        row_binding=binding,
        draw_count=100,
        support_events=(
            (
                successor[0],
                successor[1],
                successor[2],
                100,
                Fraction(1),
                Fraction(1),
            ),
        ),
        other_count=0,
        other_lower=Fraction(0),
        other_upper=Fraction(0),
    )


@pytest.fixture(scope="module")
def manual_models():
    context = (
        observer_fixture.public.freeze_v075_public_family_generation_v1()
        .replicate_contexts[0]
    )
    root = graph.root_catalogue_v1(context)
    root_rows = []
    child_states = {}
    for action in root.actions:
        binding = graph.observation_row_binding_v1(context, root, action)
        successor = _safe_successor(binding)
        root_rows.append(_exact_row(binding, successor))
        state = graph.V075SymbolicGraphStateV1(
            context,
            successor[0],
            successor[1],
        )
        child_states[state.state_id] = state
    child_rows = []
    for state_id in sorted(child_states):
        state = child_states[state_id]
        catalogue = graph.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            graph.legal_action_triples_v1(
                context,
                state.ranks,
                state.failure,
            ),
        )
        for action in catalogue.actions:
            binding = graph.observation_row_binding_v1(
                context,
                catalogue,
                action,
            )
            child_rows.append(_exact_row(binding, _safe_successor(binding)))
    partial = planning.freeze_v075_manual_construction_model_v2(
        context=context,
        rows=tuple(root_rows),
    )
    complete = planning.freeze_v075_manual_construction_model_v2(
        context=context,
        rows=tuple((*root_rows, *child_rows)),
    )
    return context, partial, complete


@pytest.fixture(scope="module")
def signed_root_graph():
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture("batch-planning-v2")
    )
    context = namespace.family.replicate_contexts[0]
    arm = worker.V075WorkerArmV1.NO_PRIOR
    occurrence = (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=acquisition.ARM_ORDER.index(arm),
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )
    schedule = acquisition.freeze_v075_occurrence_initial_acquisition_schedule_v2(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        occurrence=occurrence,
    )
    binding = observer._require_exact_v2_binding(
        authority=authorization,
        namespace=namespace,
    )
    session = observer._open_private_observer_from_verified_gate_v2(
        authority=authorization,
        namespace=namespace,
        binding=binding,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id("signed-root"),
    )
    adapter = batched.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=occurrence,
    )
    catalogue = graph.root_catalogue_v1(context)
    discoveries = tuple(
        life_fixture._discovery_stream(namespace, catalogue, action)
        for action in catalogue.actions
    )
    discovery_batches = tuple(
        adapter.observe_batch_v2(
            stream_identity=stream,
            accepted_draw_start=1,
            accepted_draw_count=64,
            accepted_draw_cap=64,
        )
        for stream in discoveries
    )
    validations = tuple(
        life_fixture._validation_stream(
            namespace,
            stream,
            life_fixture._support_evidence(
                namespace,
                signer,
                stream,
                batch,
            ),
        )
        for stream, batch in zip(discoveries, discovery_batches)
    )
    validation_batches = tuple(
        adapter.observe_batch_v2(
            stream_identity=stream,
            accepted_draw_start=1,
            accepted_draw_count=2_048,
            accepted_draw_cap=6_144,
        )
        for stream in validations
    )
    closure = adapter.close_v2()
    streams = (*discoveries, *validations)
    lineage_value = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=occurrence,
        closure=closure,
        authority=authorization,
        namespace=namespace,
        known_stream_identities=streams,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    lifecycle_value = lifecycle.freeze_v075_construction_batch_occurrence_lifecycle_v2(
        lineage=lineage_value,
        lineage_bytes=lineage_value.canonical_bytes,
        batch_closure_bytes=closure.canonical_bytes,
    )
    return {
        "namespace": namespace,
        "occurrence": occurrence,
        "schedule": schedule,
        "streams": streams,
        "discovery_batches": discovery_batches,
        "validation_batches": validation_batches,
        "lineage": lineage_value,
        "lifecycle": lifecycle_value,
    }


@pytest.fixture(scope="module")
def signed_planning_bundle(signed_root_graph):
    planning_input = planning.compile_v075_construction_planning_input_v2(
        repository_root=REPOSITORY_ROOT,
        schedule=signed_root_graph["schedule"],
        lineage=signed_root_graph["lineage"],
        lifecycle=signed_root_graph["lifecycle"],
    )
    return (
        planning_input,
        planning.plan_v075_construction_aggregate_input_v2(planning_input),
    )


def _walk_keys(value: Any) -> tuple[str, ...]:
    if isinstance(value, dict):
        return tuple(value) + tuple(
            key
            for child in value.values()
            for key in _walk_keys(child)
        )
    if isinstance(value, list):
        return tuple(
            key for child in value for key in _walk_keys(child)
        )
    return ()


def test_manual_zero_count_support_is_retained(manual_models) -> None:
    context, _partial, _complete = manual_models
    root = graph.root_catalogue_v1(context)
    binding = graph.observation_row_binding_v1(
        context,
        root,
        root.actions[0],
    )
    observed = _safe_successor(binding)
    alternate = None
    board = list(binding.catalogue.state.ranks)
    first, second, survivor = binding.action
    rank = board[first]
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, binding.context.rank_cap)
    for cell, value in enumerate(board):
        if value == 0:
            candidate = _post_spawn(
                binding,
                spawn_cell=cell,
                spawn_rank=2,
            )
            if candidate[0] != observed[0]:
                alternate = candidate
                break
    assert alternate is not None
    row = planning.freeze_v075_manual_construction_row_v2(
        row_binding=binding,
        draw_count=100,
        support_events=(
            (
                observed[0],
                observed[1],
                observed[2],
                100,
                Fraction(9, 10),
                Fraction(1),
            ),
            (
                alternate[0],
                alternate[1],
                alternate[2],
                0,
                Fraction(0),
                Fraction(1, 10),
            ),
        ),
        other_count=0,
        other_lower=Fraction(0),
        other_upper=Fraction(1, 10),
    )
    assert len(row.support) == 2
    assert sorted(item.success_count for item in row.intervals) == [0, 0, 100]
    assert row.to_document()["zero_count_support_retained"] is True


def test_v1_abort_comparator_regression_is_closed(manual_models) -> None:
    _context, partial, _complete = manual_models
    ceiling = worker.V075WorkerThresholdProfileV1().reward_ceiling
    immediate = partial.rows[0].immediate_reward
    assert immediate < ceiling
    assert planning._unrestricted_ground_reward_upper(partial) == ceiling
    proof = planning.plan_v075_construction_numerical_model_v2(
        model=partial,
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    assert proof.outcome is planning.V075NumericalOutcomeV2.FAILED_FRONTIER
    assert proof.failed_frontier is not None
    assert any(
        item.unmaterialized_successor_ids
        for item in proof.failed_frontier.obligations
    )


def test_complete_adaptive_and_direct_numerical_planning(manual_models) -> None:
    _context, _partial, complete = manual_models
    adaptive = planning.plan_v075_construction_numerical_model_v2(
        model=complete,
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    direct = planning.plan_v075_construction_numerical_model_v2(
        model=complete,
        route=planning.V075PlanningRouteV2.MATCHED_DIRECT_GROUND,
    )
    assert adaptive.outcome is planning.V075NumericalOutcomeV2.CANDIDATE
    assert direct.outcome is planning.V075NumericalOutcomeV2.CANDIDATE
    assert adaptive.quotient is not None
    assert direct.quotient is None
    assert adaptive.envelope is not None
    assert direct.envelope is not None
    assert adaptive.envelope.selected_failure_upper == 0
    assert direct.envelope.selected_failure_upper == 0
    assert adaptive.envelope.unrestricted_ground_reward_upper == Fraction(3, 64)
    assert direct.envelope.unrestricted_ground_reward_upper == Fraction(3, 64)
    assert adaptive.envelope.normalized_regret_upper == 0
    assert direct.envelope.normalized_regret_upper == 0
    assert all(
        len(choice.ground_actions) == 1
        for decision in direct.policy.decisions
        for choice in decision.state_choices
    )


def test_stale_cached_numerical_ids_cannot_change_planner_arithmetic(
    manual_models,
) -> None:
    _context, _partial, complete = manual_models
    row = complete.rows[0]
    original_reward = row.immediate_reward
    original_row_id = row.row_id
    object.__setattr__(row, "immediate_reward", Fraction(0))
    try:
        assert row.row_id == original_row_id
        with pytest.raises(
            planning.V075BatchNativePlanningV2InvariantViolation,
            match="numerical row differs from exact semantic replay",
        ):
            planning.plan_v075_construction_numerical_model_v2(
                model=complete,
                route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
            )
    finally:
        object.__setattr__(row, "immediate_reward", original_reward)


def test_numerical_proof_is_prior_and_occurrence_free(manual_models) -> None:
    _context, _partial, complete = manual_models
    first = planning.plan_v075_construction_numerical_model_v2(
        model=complete,
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    second = planning.plan_v075_construction_numerical_model_v2(
        model=complete,
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    assert first.canonical_bytes == second.canonical_bytes
    document = first.to_document()
    keys = _walk_keys(document)
    assert "arm" not in keys
    assert "proposal_id" not in keys
    assert "source_transport_id" not in keys
    assert "occurrence_id" not in keys
    assert document["arm_field_present"] is False
    assert document["proposal_field_present"] is False
    assert document["source_provenance_field_present"] is False


def test_familywise_bound_is_fixed_not_actual_row_count(manual_models) -> None:
    _context, partial, complete = manual_models
    assert len(partial.rows) != len(complete.rows)
    for model in (partial, complete):
        document = model.to_document()
        assert document["maximum_validated_rows"] == 21
        assert planning.FAMILYWISE_CONFIDENCE_ERROR_UPPER == Fraction(
            21,
            300_000,
        )
        assert document["familywise_confidence_error_upper"] == {
            "numerator": 7,
            "denominator": 100_000,
        }


def test_model_cannot_exceed_registered_familywise_row_budget(
    manual_models,
    monkeypatch,
) -> None:
    context, _partial, complete = manual_models
    monkeypatch.setattr(
        planning,
        "MAX_VALIDATED_ROWS",
        len(complete.rows) - 1,
    )
    with pytest.raises(
        planning.V075BatchNativePlanningV2InvariantViolation,
        match="numerical model is malformed",
    ):
        planning.freeze_v075_manual_construction_model_v2(
            context=context,
            rows=complete.rows,
        )


def test_manual_intervals_cannot_claim_signed_aggregate_authority(
    manual_models,
) -> None:
    context, _partial, complete = manual_models
    with pytest.raises(
        planning.V075BatchNativePlanningV2InvariantViolation,
        match="evidence kind differs",
    ):
        planning.V075NumericalModelV2(
            planning._MODEL_ISSUER,  # noqa: SLF001
            context,
            complete.rows,
            "SIGNED_V2_AGGREGATES",
        )


def test_signed_interval_endpoints_are_recomputed_from_counts(
    manual_models,
) -> None:
    context, _partial, complete = manual_models

    def forged_interval(item):
        return planning.V075EventIntervalV2(
            planning._INTERVAL_ISSUER,  # noqa: SLF001
            item.event_key,
            item.descriptor,
            item.draw_count,
            item.success_count,
            item.empirical_probability,
            item.empirical_probability,
            item.empirical_probability,
            item.event_alpha,
            0,
            0,
            planning.EXACT_BERNOULLI_METHOD_ID,
        )

    def forged_row(row):
        return planning.V075NumericalRowV2(
            planning._ROW_ISSUER,  # noqa: SLF001
            row.context_id,
            row.row_binding_id,
            row.source_state_id,
            row.source_ranks,
            row.remaining_horizon,
            row.action,
            row.immediate_reward,
            row.support,
            tuple(forged_interval(item) for item in row.intervals),
        )

    rows = tuple(
        sorted(
            (forged_row(row) for row in complete.rows),
            key=lambda row: row.row_id,
        )
    )
    model = planning.V075NumericalModelV2(
        planning._MODEL_ISSUER,  # noqa: SLF001
        context,
        rows,
        "SIGNED_V2_AGGREGATES",
    )
    with pytest.raises(
        planning.V075BatchNativePlanningV2InvariantViolation,
        match="event interval differs from exact semantic replay",
    ):
        planning.plan_v075_construction_numerical_model_v2(
            model=model,
            route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
        )


def test_signed_aggregate_compiler_replays_schedule_lineage_and_lifecycle(
    signed_planning_bundle,
) -> None:
    value, result = signed_planning_bundle
    assert value.model.evidence_kind == "SIGNED_V2_AGGREGATES"
    assert len(value.model.rows) == 2
    assert all(item.validation_draw_count == 2_048 for item in value.model.rows)
    assert all(
        sum(interval.success_count for interval in item.intervals) == 2_048
        for item in value.model.rows
    )
    assert all(
        item.latest_validation_epoch_index == 1
        for item in value.evidence_bindings
    )
    assert value.to_document()["per_draw_record_count"] == 0
    assert value.to_document()["preregistered_schedule_coverage_verified"] is False
    assert result.numerical_proof.outcome is (
        planning.V075NumericalOutcomeV2.FAILED_FRONTIER
    )
    assert result.numerical_proof.failed_frontier is not None
    assert result.to_document()["plan_certificate"] is False


def test_independent_validation_epoch_reuse_is_rejected(
    signed_planning_bundle,
) -> None:
    value, _result = signed_planning_bundle
    with pytest.raises(
        planning.V075BatchNativePlanningV2InvariantViolation,
        match="row evidence binding is malformed",
    ):
        replace(
            value.evidence_bindings[0],
            latest_validation_epoch_index=2,
        )


def test_stale_cached_input_evidence_id_is_rejected(
    signed_planning_bundle,
) -> None:
    value, _result = signed_planning_bundle
    binding = value.evidence_bindings[0]
    original_lifecycle_id = binding.lifecycle_closure_id
    object.__setattr__(
        binding,
        "lifecycle_closure_id",
        _id("stale-input-lifecycle"),
    )
    try:
        with pytest.raises(
            planning.V075BatchNativePlanningV2InvariantViolation,
            match="row evidence differs from exact semantic replay",
        ):
            planning.plan_v075_construction_aggregate_input_v2(value)
    finally:
        object.__setattr__(
            binding,
            "lifecycle_closure_id",
            original_lifecycle_id,
        )


def test_signed_compiler_rejects_transplants_and_direct_proposal(
    signed_root_graph,
) -> None:
    schedule = signed_root_graph["schedule"]
    direct_occurrence = replace(
        schedule.occurrence,
        arm=worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
    )
    forged = object.__new__(acquisition.V075InitialAcquisitionScheduleV2)
    for name in (
        "_issuer",
        "profile",
        "occurrence",
        "proposal_view",
        "proposal_use_rule",
        "intents",
        "_schedule_id",
    ):
        object.__setattr__(
            forged,
            name,
            (
                direct_occurrence
                if name == "occurrence"
                else getattr(schedule, name)
            ),
        )
    with pytest.raises(planning.V075BatchNativePlanningV2InvariantViolation):
        planning.compile_v075_construction_planning_input_v2(
            repository_root=REPOSITORY_ROOT,
            schedule=forged,
            lineage=signed_root_graph["lineage"],
            lifecycle=signed_root_graph["lifecycle"],
        )
    with pytest.raises(planning.V075BatchNativePlanningV2InvariantViolation):
        planning.compile_v075_construction_planning_input_v2(
            repository_root=REPOSITORY_ROOT,
            schedule=schedule,
            lineage=signed_root_graph["lineage"],
            lifecycle=replace(
                signed_root_graph["lifecycle"],
                occurrence_id=_id("foreign-occurrence"),
            ),
        )


def test_signed_compiler_rejects_object_new_invalid_closure_signature(
    signed_root_graph,
) -> None:
    lineage = signed_root_graph["lineage"]
    closure = lineage.closure
    forged_closure = object.__new__(
        observer.V075ObserverBatchJournalClosureV2
    )
    for item in fields(observer.V075ObserverBatchJournalClosureV2):
        object.__setattr__(
            forged_closure,
            item.name,
            (
                "00" * (len(closure.observer_signature_hex) // 2)
                if item.name == "observer_signature_hex"
                else getattr(closure, item.name)
            ),
        )
    forged_lineage = object.__new__(
        batched.V075BatchOccurrenceLineageV2
    )
    for item in fields(batched.V075BatchOccurrenceLineageV2):
        object.__setattr__(
            forged_lineage,
            item.name,
            (
                forged_closure
                if item.name == "closure"
                else getattr(lineage, item.name)
            ),
        )
    with pytest.raises(
        planning.V075BatchNativePlanningV2InvariantViolation,
        match="exact typed replay failed",
    ):
        planning.compile_v075_construction_planning_input_v2(
            repository_root=REPOSITORY_ROOT,
            schedule=signed_root_graph["schedule"],
            lineage=forged_lineage,
            lifecycle=signed_root_graph["lifecycle"],
        )


def test_result_bytes_replay_and_tamper_rejection(
    signed_planning_bundle,
) -> None:
    value, result = signed_planning_bundle
    replayed, verification = (
        planning.verify_v075_construction_planning_result_bytes_v2(
            planning_input=value,
            claimed_bytes=result.canonical_bytes,
        )
    )
    assert replayed == result
    assert verification.result_id == result.result_id
    with pytest.raises(planning.V075BatchNativePlanningV2InvariantViolation):
        planning.verify_v075_construction_planning_result_bytes_v2(
            planning_input=value,
            claimed_bytes=result.canonical_bytes + b" ",
        )


def test_production_entry_is_structurally_locked(monkeypatch) -> None:
    monkeypatch.setattr(planning, "OFFICIAL_EXECUTION_ALLOWED", True)
    with pytest.raises(
        planning.V075BatchNativePlanningV2NotReady,
        match="DYNAMIC_ACQUISITION_TERMINAL",
    ):
        planning.execute_v075_production_planning_bytes_v2(
            private_salt=b"forbidden",
            private_environment=object(),
        )
    assert planning.PER_DRAW_RECORDS_ALLOWED is False
    assert planning.PRIVATE_LAW_ACCESS_ALLOWED is False
    assert planning.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
