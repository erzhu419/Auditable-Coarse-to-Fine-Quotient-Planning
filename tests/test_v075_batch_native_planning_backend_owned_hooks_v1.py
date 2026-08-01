from __future__ import annotations

import ast
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import inspect
from types import SimpleNamespace

import pytest

from acfqp import construction_accounting_owned_runtime_v1 as runtime
from acfqp import construction_accounting_partial_native_v1 as partial
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp.v075_k7_root_cap_operation_boundary_manifest_v3 import (
    official_k7_root_cap_operation_boundary_manifest_v3,
)
from tests import test_v075_batch_native_planning_backend_v2 as fixture


_OWNER = "acfqp.v075_batch_native_planning_backend_v2"


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-backend-owned-hook-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def manual_models():
    _context, partial_model, complete_model = (
        fixture.manual_models.__wrapped__()
    )
    return partial_model, complete_model


def _activation(label: str):
    registry = registry_v6.official_counter_registry_v6()
    return runtime.activate_owned_construction_accounting_v1(
        occurrence_id=_id(label),
        recorder_id="v075-backend-owned-hook-test-recorder-v1",
        counter_registry=registry,
        stage_profile=registry_v6.official_stage_profile_v6(registry),
        boundary_profile=(
            official_k7_root_cap_operation_boundary_manifest_v3()
        ),
    )


def _enter_stage(target: partial.PartialNativeStageV1) -> None:
    for stage in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1:
        runtime.enter_owned_stage_v1(stage)
        if stage is target:
            return
        runtime.exit_owned_stage_v1(stage)
    raise AssertionError("target stage is outside the root-cap plan")


def _complete_stage(
    target: partial.PartialNativeStageV1,
) -> partial.PartialNativeOccurrenceTranscriptV1:
    runtime.exit_owned_stage_v1(target)
    index = partial.ROOT_CAP_FIVE_STAGE_PLAN_V1.index(target)
    for stage in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1[index + 1 :]:
        runtime.enter_owned_stage_v1(stage)
        runtime.exit_owned_stage_v1(stage)
    transcript = runtime.complete_owned_occurrence_v1()
    assert transcript is not None
    return transcript


def _path_counts(
    transcript: partial.PartialNativeOccurrenceTranscriptV1,
) -> Counter[str]:
    return Counter(
        node.path
        for node in transcript.nodes
        if type(node) is partial.PartialNativeOperationEventV1
        for _ in range(node.amount)
    )


def _dispatch_counts(
    transcript: partial.PartialNativeOccurrenceTranscriptV1,
) -> Counter[str]:
    manifest = official_k7_root_cap_operation_boundary_manifest_v3()
    dispatch_by_site = {
        row.boundary_key: row.dispatch_key for row in manifest.boundaries
    }
    return Counter(
        dispatch_by_site[node.site_id]
        for node in transcript.nodes
        if type(node) is partial.PartialNativeOperationEventV1
        for _ in range(node.amount)
    )


class _DispatchVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.by_key: dict[str, set[str]] = defaultdict(set)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        function = node.func
        if (
            isinstance(function, ast.Attribute)
            and function.attr == "emit_owned_operation_v1"
            and isinstance(function.value, ast.Name)
            and function.value.id == "accounting_runtime"
        ):
            assert self.stack
            assert node.args
            key = node.args[0]
            assert isinstance(key, ast.Constant)
            assert type(key.value) is str
            self.by_key[key.value].add(self.stack[-1])
        self.generic_visit(node)


def test_every_active_manifest_dispatch_is_called_by_its_exact_owner_symbol() -> None:
    document = official_k7_root_cap_operation_boundary_manifest_v3()
    expected: dict[str, set[str]] = defaultdict(set)
    for row in document.boundaries:
        row_document = row.to_document()
        if (
            row.operation_source_module == _OWNER
            and row_document["emittable_in_this_fixture"] is True
        ):
            expected[row.dispatch_key].add(row.operation_source_symbol)

    tree = ast.parse(inspect.getsource(planning))
    visitor = _DispatchVisitor()
    visitor.visit(tree)

    assert len(expected) == 27
    assert visitor.by_key == expected


def test_inactive_hooks_preserve_exact_planning_bytes(manual_models) -> None:
    _partial_model, complete_model = manual_models
    first = planning.plan_v075_construction_numerical_model_v2(
        model=complete_model,
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    second = planning.plan_v075_construction_numerical_model_v2(
        model=complete_model,
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    assert runtime.owned_accounting_active_v1() is False
    assert first.canonical_bytes == second.canonical_bytes
    assert first.proof_id == second.proof_id


@pytest.mark.parametrize(
    ("route", "expected"),
    (
        (
            planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
            {
                "build.initial_batch_v2_typed_record_replays": 31,
                "build.initial_batch_v2_replay_interval_reconstructions": 12,
                "build.initial_batch_v2_row_behaviors_compiled": 6,
                "build.initial_batch_v2_quotient_cells_compiled": 2,
                "build.initial_batch_v2_semantic_options_compiled": 2,
                "build.initial_batch_v2_concretizer_ground_actions_bound": 6,
                "build.initial_batch_v2_interval_greedy_allocation_steps": 20,
                "build.initial_batch_v2_option_metric_evaluations": 2,
                "build.initial_batch_v2_policy_assignment_cap_checks": 1,
                "build.initial_policy_assignments_evaluated": 1,
            },
        ),
        (
            planning.V075PlanningRouteV2.MATCHED_DIRECT_GROUND,
            {
                "build.initial_batch_v2_typed_record_replays": 31,
                "build.initial_batch_v2_replay_interval_reconstructions": 12,
                "build.initial_batch_v2_row_behaviors_compiled": 6,
                "build.initial_batch_v2_semantic_options_compiled": 6,
                "build.initial_batch_v2_concretizer_ground_actions_bound": 6,
                "build.initial_batch_v2_interval_greedy_allocation_steps": 26,
                "build.initial_batch_v2_option_metric_evaluations": 8,
                "build.initial_batch_v2_policy_assignment_cap_checks": 4,
                "build.initial_policy_assignments_evaluated": 4,
                "build.initial_batch_v2_policy_order_comparisons": 6,
            },
        ),
    ),
)
def test_exact_planning_primitives_are_counted_at_owner_boundaries(
    manual_models,
    route: planning.V075PlanningRouteV2,
    expected: dict[str, int],
) -> None:
    _partial_model, complete_model = manual_models
    with _activation(f"exact-planning-{route.value}"):
        stage = partial.PartialNativeStageV1.INITIAL_MODEL_BUILD
        _enter_stage(stage)
        proof = planning.plan_v075_construction_numerical_model_v2(
            model=complete_model,
            route=route,
        )
        transcript = _complete_stage(stage)

    assert proof.outcome is planning.V075NumericalOutcomeV2.CANDIDATE
    assert _path_counts(transcript) == Counter(expected)
    dispatches = _dispatch_counts(transcript)
    assert dispatches["batch-planning.interval-greedy.extreme"] == 2
    assert dispatches[
        "batch-planning.interval-greedy.extreme-bounds"
    ] == (
        18
        if route is planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        else 24
    )
    assert dispatches["batch-planning.policy-order.diagnostic"] == (
        0
        if route is planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        else 3
    )
    assert dispatches["batch-planning.policy-order.feasible-best"] == (
        0
        if route is planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        else 3
    )


def test_frontier_counts_each_successfully_constructed_obligation(
    manual_models,
) -> None:
    partial_model, _complete_model = manual_models
    selected = tuple(row.row_id for row in partial_model.rows)
    with _activation("frontier-obligations"):
        stage = partial.PartialNativeStageV1.INITIAL_MODEL_BUILD
        _enter_stage(stage)
        frontier = planning._frontier(  # noqa: SLF001
            model=partial_model,
            route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
            reason=planning.V075FailedProofReasonV2.RISK_BOUND_FAILED,
            row_ids=selected,
        )
        transcript = _complete_stage(stage)

    assert len(frontier.obligations) == len(selected) == 2
    assert _path_counts(transcript) == Counter(
        {"build.initial_batch_v2_frontier_obligations_built": 2}
    )


def test_confidence_entry_is_counted_but_failed_interval_is_not() -> None:
    with _activation("invalid-confidence-event"):
        stage = partial.PartialNativeStageV1.INITIAL_MODEL_BUILD
        _enter_stage(stage)
        with pytest.raises(
            planning.V075BatchNativePlanningV2InvariantViolation,
            match="not a registered checkpoint",
        ):
            planning._checkpoint_interval(  # noqa: SLF001
                descriptor=None,
                draw_count=2,
                success_count=0,
                event_count=1,
                checkpoints=(1,),
            )
        transcript = _complete_stage(stage)

    assert _path_counts(transcript) == Counter(
        {"build.initial_confidence_event_evaluations": 1}
    )


def test_successful_interval_constructor_is_counted_after_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkpoint = SimpleNamespace(
        empirical_probability=Fraction(1, 4),
        lower_probability=Fraction(0),
        upper_probability=Fraction(1),
        exact_likelihood_comparisons=0,
        log_search_evaluations=0,
    )
    monkeypatch.setattr(
        planning,
        "build_anytime_bernoulli_checkpoint_v1",
        lambda *_args, **_kwargs: checkpoint,
    )
    with _activation("valid-confidence-event"):
        stage = partial.PartialNativeStageV1.INITIAL_MODEL_BUILD
        _enter_stage(stage)
        interval = planning._checkpoint_interval(  # noqa: SLF001
            descriptor=None,
            draw_count=4,
            success_count=1,
            event_count=1,
            checkpoints=(4,),
        )
        transcript = _complete_stage(stage)

    assert interval.success_count == 1
    assert _path_counts(transcript) == Counter(
        {
            "build.initial_confidence_event_evaluations": 1,
            "build.initial_interval_row_evaluations": 1,
        }
    )


def test_closed_aggregate_primitives_count_rows_not_draw_multiplicity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row_id = _id("aggregate-row")
    evidence_id = _id("aggregate-evidence")
    row_binding = SimpleNamespace(
        context_id=_id("aggregate-context"),
        row_binding_id=row_id,
        state_id=_id("aggregate-state"),
        catalogue=SimpleNamespace(state=SimpleNamespace(ranks=(1, 1, 2, 0))),
        remaining_horizon=2,
        action=(0, 1, 0),
    )
    discovery_stream = SimpleNamespace(
        row_binding_id=row_id,
        row_binding=row_binding,
        lane=SimpleNamespace(value="DISCOVERY"),
        observer_epoch_index=0,
        stream_id=_id("discovery-stream"),
    )
    validation_stream = SimpleNamespace(
        row_binding_id=row_id,
        row_binding=row_binding,
        lane=SimpleNamespace(value="VALIDATION"),
        observer_epoch_index=1,
        stream_id=_id("validation-stream"),
    )
    discovery = SimpleNamespace(
        batch_id=_id("discovery-batch"),
        request=SimpleNamespace(stream_identity=discovery_stream),
    )
    outcome = SimpleNamespace(
        next_ranks=(2, 1, 2, 0),
        failure=False,
        terminal=False,
        realized_row_reward=Fraction(1),
        reward_sum=Fraction(7),
        count=7,
    )
    validation = SimpleNamespace(
        batch_id=_id("validation-batch"),
        request=SimpleNamespace(
            stream_identity=validation_stream,
            accepted_draw_start=1,
            accepted_draw_end=7,
            accepted_draw_cap=7,
        ),
        outcomes=(outcome,),
    )
    lineage = SimpleNamespace(
        batches=(discovery, validation),
        occurrence_identity=SimpleNamespace(
            arm=worker.V075WorkerArmV1.NO_PRIOR
        ),
    )
    lifecycle = SimpleNamespace(
        support_freezes=(
            SimpleNamespace(
                row_binding_id=row_id,
                validation_epoch_index=1,
                support_evidence_ids=(evidence_id,),
                freeze_id=_id("freeze"),
                source_discovery_batch_ids=(discovery.batch_id,),
            ),
        ),
        support_evidence=(
            SimpleNamespace(
                evidence_id=evidence_id,
                next_ranks=outcome.next_ranks,
                failure=False,
                terminal=False,
            ),
        ),
        closure_id=_id("closure"),
    )

    monkeypatch.setattr(planning, "_allowed_checkpoints", lambda **_kwargs: (7,))
    monkeypatch.setattr(
        planning,
        "_structural_state",
        lambda *_args, **_kwargs: SimpleNamespace(state_id=_id("next-state")),
    )
    monkeypatch.setattr(planning, "_merge_reward", lambda _row: Fraction(1))
    monkeypatch.setattr(
        planning,
        "V075SupportDescriptorV2",
        lambda _issuer, _context, _state, ranks, failure, terminal: (
            SimpleNamespace(
                descriptor_id=_id("descriptor"),
                next_ranks=ranks,
                failure=failure,
                terminal=terminal,
            )
        ),
    )
    monkeypatch.setattr(
        planning,
        "_checkpoint_interval",
        lambda **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        planning,
        "V075NumericalRowV2",
        lambda *_args: SimpleNamespace(row_id=_id("numerical-row")),
    )
    monkeypatch.setattr(
        planning,
        "V075RowEvidenceBindingV2",
        lambda _issuer, numerical_row_id, *_args: SimpleNamespace(
            numerical_row_id=numerical_row_id
        ),
    )

    with _activation("closed-aggregate-primitives"):
        stage = (
            partial.PartialNativeStageV1
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        )
        _enter_stage(stage)
        rows, bindings = planning._compile_aggregate_rows(  # noqa: SLF001
            lineage=lineage,
            lifecycle=lifecycle,
        )
        transcript = _complete_stage(stage)

    assert len(rows) == len(bindings) == 1
    assert _path_counts(transcript) == Counter(
        {
            "closure.reconciliation_batch_v2_support_descriptors_compiled": 1,
            "closure.reconciliation_outcome_projections": 1,
            "closure.reconciliation_batch_v2_model_rows_built": 1,
            "closure.reconciliation_batch_v2_row_evidence_bindings_built": 1,
        }
    )
