from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib

import pytest

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    PEAK_WORKING_BYTES,
    READ_BYTES,
    ReducerEnum,
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    official_actual_projection_profile_v1,
)
from acfqp.native_recorder_v1 import NativeCounterRecorderV1, RecordedWorkV1
from acfqp.marginal_accounting_v1 import (
    AggregatedMarginalWorkV1,
    derive_marginal_work_aggregate_v1,
)
from acfqp.phase3e_occurrence_accounting_v1 import (
    OccurrenceRawEvidenceKind,
    OccurrenceWorkComponentEvidenceV1,
    OccurrenceWorkComponentKind,
    OccurrenceWorkComponentRefV1,
    Phase3EOccurrenceAccountingV1Error,
    Phase3EOccurrenceWorkAggregateV1,
    RunnerCommonAccountingEvidenceV1,
    RunnerMarginalWorkEvidenceV1,
    RunnerPartialCommonAccountingEvidenceV1,
    derive_phase3e_occurrence_work_aggregate_v1,
    derive_runner_partial_common_accounting_v1,
    verify_phase3e_occurrence_work_aggregate_v1,
)
from acfqp.phase3e_ids import OCCURRENCE_WORK_AGGREGATE_DOMAIN, content_id
from tests.test_phase3e_two_stage_accounting_v1 import (
    _reverify_with_binding as _reverify_two_stage_with_binding,
    _world as _two_stage_world,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteDecisionContextV1,
    TransactionV1,
    TypedNotApplicable,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(
    *,
    label: str,
    subject_id: str,
    route_kind: RouteKindEnum,
    scope: ActualWorkScope,
    values: dict[str, int],
) -> RecordedWorkV1:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    recorder = NativeCounterRecorderV1(
        subject_id=subject_id,
        route_kind=route_kind,
        work_scope=scope,
        registry=registry,
        comparison_profile=profile,
        recorder_id=f"phase3e-occurrence-test-{label}",
    )
    for path, value in values.items():
        if registry.by_path[path].reducer is ReducerEnum.MAX:
            recorder.observe_peak(path, value)
        else:
            recorder.add(path, value)
    return recorder.seal()


def _context(
    *,
    label: str,
    logical_occurrence_id: str,
    route_attempt_id: str,
    selected_plan_id: str,
) -> RouteDecisionContextV1:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    return RouteDecisionContextV1(
        _id(f"{label}-preregistration"),
        _id(f"{label}-protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _id(f"{label}-structural"),
        _id(f"{label}-query"),
        selected_plan_id,
        _id(f"{label}-threshold"),
        _id(f"{label}-epoch"),
        logical_occurrence_id,
        route_attempt_id,
    )


def _next_context(
    previous: RouteDecisionContextV1, *, selected_plan_id: str
) -> RouteDecisionContextV1:
    return RouteDecisionContextV1(
        previous.preregistration_id,
        previous.protocol_id,
        previous.comparison_profile_id,
        previous.counter_registry_id,
        previous.structural_id,
        previous.query_id,
        selected_plan_id,
        previous.threshold_profile_id,
        previous.build_epoch_id,
        previous.logical_occurrence_id,
        previous.route_attempt_id,
    )


@dataclass(frozen=True)
class _World:
    logical_occurrence_id: str
    context1: RouteDecisionContextV1
    context2: RouteDecisionContextV1
    prefix1: RecordedWorkV1
    decision1: DecisionPointV1
    transaction1: TransactionV1
    local1_execution: RecordedWorkV1
    local1_verification: RecordedWorkV1
    prefix2: RecordedWorkV1
    decision2: DecisionPointV1
    transaction2: TransactionV1
    local2_execution: RecordedWorkV1
    local2_verification: RecordedWorkV1
    local2_aggregate: AggregatedMarginalWorkV1
    fallback_prefix: RecordedWorkV1
    fallback_decision: DecisionPointV1
    fallback_execution: RecordedWorkV1
    fallback_verification: RecordedWorkV1
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...]


def _world() -> _World:
    occurrence_id = _id("multiwork-occurrence")
    attempt_id = _id("multiwork-route-attempt")
    context1 = _context(
        label="multiwork",
        logical_occurrence_id=occurrence_id,
        route_attempt_id=attempt_id,
        selected_plan_id=_id("multiwork-plan-1"),
    )
    context2 = _next_context(
        context1, selected_plan_id=_id("multiwork-plan-2")
    )

    prefix1 = _record(
        label="prefix-1",
        subject_id=attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        scope=ActualWorkScope.COMMON_PREFIX,
        values={
            "common.protocol_checks": 1,
            "io.read_bytes": 10,
            "memory.working_bytes_peak": 10,
        },
    )
    decision1 = DecisionPointV1(
        context1.route_decision_context_id,
        1,
        _id("multiwork-frontier-1"),
        _id("multiwork-causal-1"),
        prefix1.work_vector.work_vector_id,
    )
    transaction1 = TransactionV1(
        occurrence_id,
        attempt_id,
        decision1.decision_point_id,
        1,
        decision1.frontier_snapshot_id,
        _id("multiwork-local-cap"),
    )
    local1_execution = _record(
        label="local-1-execution",
        subject_id=transaction1.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        values={
            "local.materialization_ground_steps": 2,
            "local.solver_policy_assignments": 3,
            "io.read_bytes": 20,
            "memory.working_bytes_peak": 20,
        },
    )
    local1_verification = _record(
        label="local-1-verification",
        subject_id=transaction1.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        values={
            "common.protocol_checks": 2,
            "memory.working_bytes_peak": 25,
        },
    )

    prefix2 = _record(
        label="prefix-2",
        subject_id=attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        scope=ActualWorkScope.COMMON_PREFIX,
        values={
            "common.abstract_audit_obligations": 3,
            "io.read_bytes": 30,
            "memory.working_bytes_peak": 15,
        },
    )
    decision2 = DecisionPointV1(
        context2.route_decision_context_id,
        2,
        _id("multiwork-frontier-2"),
        _id("multiwork-causal-2"),
        prefix2.work_vector.work_vector_id,
    )
    transaction2 = TransactionV1(
        occurrence_id,
        attempt_id,
        decision2.decision_point_id,
        2,
        decision2.frontier_snapshot_id,
        _id("multiwork-local-cap"),
    )
    local2_execution = _record(
        label="local-2-execution",
        subject_id=transaction2.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        values={
            "local.materialization_ground_steps": 4,
            "local.solver_policy_assignments": 5,
            "io.read_bytes": 40,
            "memory.working_bytes_peak": 30,
        },
    )
    local2_verification = _record(
        label="local-2-verification",
        subject_id=transaction2.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        values={
            "common.integrity_checks": 1,
            "memory.working_bytes_peak": 35,
        },
    )
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual_profile = official_actual_projection_profile_v1(registry, profile)
    local2_aggregate = derive_marginal_work_aggregate_v1(
        subject_id=transaction2.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        execution=(
            local2_execution.work_vector,
            local2_execution.comparison_vector,
            local2_execution.actual_projection_proof,
        ),
        verification_suffix=(
            local2_verification.work_vector,
            local2_verification.comparison_vector,
            local2_verification.actual_projection_proof,
        ),
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual_profile,
    )

    fallback_prefix = _record(
        label="fallback-prefix",
        subject_id=attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        scope=ActualWorkScope.COMMON_PREFIX,
        values={
            "common.protocol_checks": 4,
            "io.read_bytes": 50,
            "memory.working_bytes_peak": 12,
        },
    )
    fallback_decision = DecisionPointV1(
        context2.route_decision_context_id,
        TypedNotApplicable("fallback has no local transaction"),
        TypedNotApplicable("fallback has no local frontier"),
        TypedNotApplicable("fallback has no causal evidence"),
        fallback_prefix.work_vector.work_vector_id,
    )
    fallback_execution = _record(
        label="fallback-execution",
        subject_id=attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        values={
            "fallback.ground_steps": 6,
            "fallback.actions_evaluated": 7,
            "io.read_bytes": 60,
            "memory.working_bytes_peak": 40,
        },
    )
    fallback_verification = _record(
        label="fallback-verification",
        subject_id=attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        values={
            "common.hash_invocations": 2,
            "memory.working_bytes_peak": 50,
        },
    )

    # Transaction 1 and fallback exercise direct RecordedWorkV1 replay.  The
    # transaction-2 component exercises the runner aggregate path while
    # retaining both native sources and their aggregation proof.
    components = (
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.COMMON_PREFIX,
            context1,
            decision1,
            None,
            (prefix1,),
        ),
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.LOCAL_TRANSACTION,
            context1,
            decision1,
            transaction1,
            (local1_execution, local1_verification),
        ),
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.COMMON_PREFIX,
            context2,
            decision2,
            None,
            (prefix2,),
        ),
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.LOCAL_TRANSACTION,
            context2,
            decision2,
            transaction2,
            (
                RunnerMarginalWorkEvidenceV1(
                    local2_aggregate,
                    local2_execution,
                    local2_verification,
                ),
            ),
        ),
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.COMMON_PREFIX,
            context2,
            fallback_decision,
            None,
            (fallback_prefix,),
        ),
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.DIRECT_FALLBACK,
            context2,
            fallback_decision,
            None,
            (fallback_execution, fallback_verification),
        ),
    )
    return _World(
        occurrence_id,
        context1,
        context2,
        prefix1,
        decision1,
        transaction1,
        local1_execution,
        local1_verification,
        prefix2,
        decision2,
        transaction2,
        local2_execution,
        local2_verification,
        local2_aggregate,
        fallback_prefix,
        fallback_decision,
        fallback_execution,
        fallback_verification,
        components,
    )


def _derive(world: _World) -> Phase3EOccurrenceWorkAggregateV1:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)
    return derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=world.logical_occurrence_id,
        components=world.components,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    )


def test_two_local_transactions_and_fresh_fallback_replay_without_provenance_loss() -> None:
    world = _world()
    aggregate = _derive(world)
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)

    assert tuple(row.component_kind for row in aggregate.component_refs) == (
        OccurrenceWorkComponentKind.COMMON_PREFIX,
        OccurrenceWorkComponentKind.LOCAL_TRANSACTION,
        OccurrenceWorkComponentKind.COMMON_PREFIX,
        OccurrenceWorkComponentKind.LOCAL_TRANSACTION,
        OccurrenceWorkComponentKind.COMMON_PREFIX,
        OccurrenceWorkComponentKind.DIRECT_FALLBACK,
    )
    values = dict(aggregate.aggregate_values)
    assert values[KERNEL_TRANSITION_CALLS] == 2 + 4 + 6
    assert values[READ_BYTES] == 10 + 20 + 30 + 40 + 50 + 60
    assert values[PEAK_WORKING_BYTES] == 50
    assert values[NONKERNEL_COMPUTE_EVENTS] == 1 + 3 + 2 + 3 + 5 + 1 + 4 + 7 + 2

    expected_raw_work_ids = {
        row.work_vector.work_vector_id
        for row in (
            world.prefix1,
            world.local1_execution,
            world.local1_verification,
            world.prefix2,
            world.fallback_prefix,
            world.fallback_execution,
            world.fallback_verification,
        )
    }
    expected_raw_work_ids.add(
        world.local2_aggregate.aggregate_work_vector.work_vector_id
    )
    raw_refs = tuple(
        raw for component in aggregate.component_refs for raw in component.raw_work_refs
    )
    assert {row.work_vector_id for row in raw_refs} == expected_raw_work_ids
    assert all(
        not isinstance(row.native_zero_attestation_id, TypedNotApplicable)
        for row in raw_refs
        if row.evidence_kind is OccurrenceRawEvidenceKind.RECORDED_WORK
    )
    assert all(
        isinstance(row.native_zero_attestation_id, TypedNotApplicable)
        for row in raw_refs
        if row.evidence_kind
        is OccurrenceRawEvidenceKind.AGGREGATED_MARGINAL_WORK
    )
    aggregate_ref = next(
        row
        for row in raw_refs
        if row.evidence_kind
        is OccurrenceRawEvidenceKind.AGGREGATED_MARGINAL_WORK
    )
    assert aggregate_ref.marginal_work_aggregation_proof_id == (
        world.local2_aggregate.aggregation_proof.marginal_work_aggregation_proof_id
    )
    assert {row.work_vector_id for row in aggregate_ref.aggregation_source_refs} == {
        world.local2_execution.work_vector.work_vector_id,
        world.local2_verification.work_vector.work_vector_id,
    }

    assert Phase3EOccurrenceWorkAggregateV1.from_dict(
        aggregate.to_dict()
    ) == aggregate
    assert all(
        OccurrenceWorkComponentRefV1.from_dict(row.to_dict()) == row
        for row in aggregate.component_refs
    )
    assert verify_phase3e_occurrence_work_aggregate_v1(
        aggregate,
        logical_occurrence_id=world.logical_occurrence_id,
        components=world.components,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    ) == aggregate


def test_deeper_marginal_decision_can_select_fallback_without_creating_tx2() -> None:
    world = _world()
    components = (
        *world.components[:3],
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.DIRECT_FALLBACK,
            world.context2,
            world.decision2,
            None,
            (world.fallback_execution, world.fallback_verification),
        ),
    )
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)

    aggregate = derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=world.logical_occurrence_id,
        components=components,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    )

    fallback_ref = aggregate.component_refs[-1]
    assert fallback_ref.component_kind is OccurrenceWorkComponentKind.DIRECT_FALLBACK
    assert isinstance(fallback_ref.transaction_id, TypedNotApplicable)
    assert isinstance(fallback_ref.transaction_index, TypedNotApplicable)
    assert fallback_ref.decision_point_id == world.decision2.decision_point_id
    assert verify_phase3e_occurrence_work_aggregate_v1(
        aggregate,
        logical_occurrence_id=world.logical_occurrence_id,
        components=components,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    ) == aggregate


def test_deeper_marginal_fallback_rejects_fake_or_stale_tx2_identity() -> None:
    world = _world()
    wrong_index_point = DecisionPointV1(
        world.context2.route_decision_context_id,
        1,
        world.decision2.frontier_snapshot_id,
        world.decision2.causal_evidence_id,
        world.prefix2.work_vector.work_vector_id,
    )
    components = (
        *world.components[:2],
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.COMMON_PREFIX,
            world.context2,
            wrong_index_point,
            None,
            (world.prefix2,),
        ),
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.DIRECT_FALLBACK,
            world.context2,
            wrong_index_point,
            None,
            (world.fallback_execution, world.fallback_verification),
        ),
    )
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="candidate index",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=components,
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )

    stale_point = DecisionPointV1(
        world.context1.route_decision_context_id,
        2,
        world.decision2.frontier_snapshot_id,
        world.decision2.causal_evidence_id,
        world.prefix2.work_vector.work_vector_id,
    )
    stale_components = (
        *world.components[:2],
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.COMMON_PREFIX,
            world.context1,
            stale_point,
            None,
            (world.prefix2,),
        ),
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.DIRECT_FALLBACK,
            world.context1,
            stale_point,
            None,
            (world.fallback_execution, world.fallback_verification),
        ),
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="fresh stitched-plan",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=stale_components,
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )


def test_duplicate_or_third_local_transaction_is_rejected() -> None:
    world = _world()
    third_prefix = world.components[2]
    third_local = world.components[3]
    components = (
        *world.components[:4],
        third_prefix,
        third_local,
        *world.components[4:],
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="two-local-transaction budget",
    ):
        registry = official_counter_registry_v1()
        profile = official_comparison_profile_v1(registry)
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=components,
            registry=registry,
            comparison_profile=profile,
            actual_profile=official_actual_projection_profile_v1(
                registry, profile
            ),
        )


def test_spliced_transaction_and_subject_are_rejected() -> None:
    world = _world()
    spliced = replace(world.components[3], transaction=world.transaction1)
    components = (*world.components[:3], spliced, *world.components[4:])
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="transaction identity chain",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=components,
            registry=registry,
            comparison_profile=profile,
            actual_profile=official_actual_projection_profile_v1(
                registry, profile
            ),
        )

    wrong_subject = _record(
        label="wrong-local-subject",
        subject_id=world.context1.route_attempt_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        values={"local.materialization_ground_steps": 1},
    )
    wrong_verification = _record(
        label="wrong-local-verification-subject",
        subject_id=world.context1.route_attempt_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        values={"common.protocol_checks": 1},
    )
    wrong_local = replace(
        world.components[1], raw_work=(wrong_subject, wrong_verification)
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="transaction subject",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(world.components[0], wrong_local),
            registry=registry,
            comparison_profile=profile,
            actual_profile=official_actual_projection_profile_v1(
                registry, profile
            ),
        )


@pytest.mark.parametrize(
    "component_index",
    (1, 5),
    ids=("local", "fallback"),
)
def test_route_component_cannot_omit_verification_suffix(
    component_index: int,
) -> None:
    world = _world()
    route = world.components[component_index]
    execution_only = replace(route, raw_work=(route.raw_work[0],))
    prefix = world.components[component_index - 1]
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)

    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="must retain MARGINAL_ROUTE_VERIFICATION",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(prefix, execution_only),
            registry=registry,
            comparison_profile=profile,
            actual_profile=official_actual_projection_profile_v1(
                registry, profile
            ),
        )


def test_stale_context_attempt_and_fallback_decision_are_rejected() -> None:
    world = _world()
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)

    # A local component cannot merely relabel the context while retaining a
    # decision point from another plan/context.
    stale_context_local = replace(
        world.components[3], route_context=world.context1
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="spliced from another common-prefix decision",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(
                *world.components[:3],
                stale_context_local,
                *world.components[4:],
            ),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )

    foreign_context = RouteDecisionContextV1(
        world.context2.preregistration_id,
        world.context2.protocol_id,
        world.context2.comparison_profile_id,
        world.context2.counter_registry_id,
        world.context2.structural_id,
        world.context2.query_id,
        world.context2.selected_plan_id,
        world.context2.threshold_profile_id,
        world.context2.build_epoch_id,
        world.context2.logical_occurrence_id,
        _id("foreign-route-attempt"),
    )
    foreign_decision = replace(
        world.fallback_decision,
        route_decision_context_id=foreign_context.route_decision_context_id,
    )
    foreign_prefix = replace(
        world.components[4],
        route_context=foreign_context,
        decision_point=foreign_decision,
    )
    foreign_fallback = replace(
        world.components[5],
        route_context=foreign_context,
        decision_point=foreign_decision,
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error, match="occurrence or route attempt"
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(*world.components[:4], foreign_prefix, foreign_fallback),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )

    stale_fallback_decision = DecisionPointV1(
        world.context1.route_decision_context_id,
        TypedNotApplicable("fallback has no local transaction"),
        TypedNotApplicable("fallback has no local frontier"),
        TypedNotApplicable("fallback has no causal evidence"),
        world.fallback_prefix.work_vector.work_vector_id,
    )
    stale_prefix = replace(
        world.components[4],
        route_context=world.context1,
        decision_point=stale_fallback_decision,
    )
    stale_fallback = replace(
        world.components[5],
        route_context=world.context1,
        decision_point=stale_fallback_decision,
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="stale route-decision context",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(*world.components[:4], stale_prefix, stale_fallback),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )


def test_component_ref_and_total_tampering_fail_replay() -> None:
    world = _world()
    aggregate = _derive(world)
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)

    first = aggregate.component_refs[0]
    forged_first = replace(
        first,
        decision_point_id=_id("forged-occurrence-decision-point"),
    )
    forged_refs = (forged_first, *aggregate.component_refs[1:])
    forged = replace(aggregate, component_refs=forged_refs)
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error, match="differs from reducer-aware"
    ):
        verify_phase3e_occurrence_work_aggregate_v1(
            forged,
            logical_occurrence_id=world.logical_occurrence_id,
            components=world.components,
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )

    values = dict(aggregate.aggregate_values)
    values[READ_BYTES] += 1
    forged_total = replace(aggregate, aggregate_values=tuple(sorted(values.items())))
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error, match="differs from reducer-aware"
    ):
        verify_phase3e_occurrence_work_aggregate_v1(
            forged_total,
            logical_occurrence_id=world.logical_occurrence_id,
            components=world.components,
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )

    document = aggregate.to_dict()
    document["component_refs"][0]["raw_work_refs"][0]["work_vector_id"] = _id(
        "forged-raw-work"
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="component reference content ID mismatch",
    ):
        Phase3EOccurrenceWorkAggregateV1.from_dict(document)


def test_duplicate_raw_work_cannot_be_hidden_in_one_component() -> None:
    world = _world()
    duplicated = replace(
        world.components[1],
        raw_work=(world.local1_execution, world.local1_execution),
    )
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    with pytest.raises(Phase3EOccurrenceAccountingV1Error):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(world.components[0], duplicated),
            registry=registry,
            comparison_profile=profile,
            actual_profile=official_actual_projection_profile_v1(
                registry, profile
            ),
        )


def test_bare_actual_triple_and_orphan_aggregate_are_rejected() -> None:
    world = _world()
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)

    bare_triple = replace(
        world.components[3],
        raw_work=(
            (
                world.local2_execution.work_vector,
                world.local2_execution.comparison_vector,
                world.local2_execution.actual_projection_proof,
            ),
        ),
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="RecordedWorkV1 or complete runner marginal evidence",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(*world.components[:3], bare_triple),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )

    orphan_aggregate = replace(
        world.components[3], raw_work=(world.local2_aggregate,)
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="RecordedWorkV1 or complete runner marginal evidence",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(*world.components[:3], orphan_aggregate),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )


def test_two_stage_common_binds_decision_to_core_but_charges_aggregate() -> None:
    two_stage = _two_stage_world("occurrence-common")
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)
    point = DecisionPointV1(
        two_stage.context.route_decision_context_id,
        TypedNotApplicable("control prefix has no transaction"),
        TypedNotApplicable("control prefix has no frontier"),
        TypedNotApplicable("control prefix has no causal evidence"),
        two_stage.core_work.work_vector.work_vector_id,
    )
    common = RunnerCommonAccountingEvidenceV1(
        two_stage.core_work,
        two_stage.closure,
        two_stage.results,
        (),
        two_stage.context,
    )
    component = OccurrenceWorkComponentEvidenceV1(
        OccurrenceWorkComponentKind.COMMON_PREFIX,
        two_stage.context,
        point,
        None,
        (common,),
    )
    aggregate = derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=two_stage.context.logical_occurrence_id,
        components=(component,),
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    )
    ref = aggregate.component_refs[0].raw_work_refs[0]
    assert ref.evidence_kind is OccurrenceRawEvidenceKind.TWO_STAGE_ACCOUNTED_COMMON
    assert ref.work_vector_id == (
        two_stage.closure.aggregate_work.work_vector.work_vector_id
    )
    assert ref.work_vector_id != point.common_prefix_work_id
    assert ref.marginal_work_aggregation_proof_id == (
        two_stage.closure.receipt.verification_charge_receipt_id
    )

    forged_point = replace(
        point,
        common_prefix_work_id=ref.work_vector_id,
    )
    forged_component = replace(component, decision_point=forged_point)
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="stale for its decision point",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=two_stage.context.logical_occurrence_id,
            components=(forged_component,),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )


def _partial_common_sequence_fixture():
    two_stage = _two_stage_world("occurrence-partial-placement")
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)
    point = DecisionPointV1(
        two_stage.context.route_decision_context_id,
        TypedNotApplicable("rejected package has no transaction"),
        TypedNotApplicable("rejected package has no frontier"),
        TypedNotApplicable("rejected package has no causal evidence"),
        two_stage.core_work.work_vector.work_vector_id,
    )
    partial = derive_runner_partial_common_accounting_v1(
        core=two_stage.core_work,
        semantic_results=_reverify_two_stage_with_binding(
            two_stage,
            decision_point_id=point.decision_point_id,
        ),
        nonsemantic_records=(),
        route_context=two_stage.context,
        decision_point_id=point.decision_point_id,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    )
    partial_prefix = OccurrenceWorkComponentEvidenceV1(
        OccurrenceWorkComponentKind.COMMON_PREFIX,
        two_stage.context,
        point,
        None,
        (partial,),
    )
    full_prefix = replace(partial_prefix, raw_work=(two_stage.core_work,))
    fallback_execution = _record(
        label="partial-placement-fallback-execution",
        subject_id=two_stage.context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        values={"fallback.ground_steps": 1},
    )
    fallback_verification = _record(
        label="partial-placement-fallback-verification",
        subject_id=two_stage.context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        values={"common.protocol_checks": 1},
    )
    fallback = OccurrenceWorkComponentEvidenceV1(
        OccurrenceWorkComponentKind.DIRECT_FALLBACK,
        two_stage.context,
        point,
        None,
        (fallback_execution, fallback_verification),
    )
    return (
        two_stage,
        registry,
        profile,
        actual,
        partial_prefix,
        full_prefix,
        fallback,
    )


def test_partial_common_is_only_a_final_unpaired_rejected_prefix() -> None:
    (
        two_stage,
        registry,
        profile,
        actual,
        partial_prefix,
        full_prefix,
        fallback,
    ) = _partial_common_sequence_fixture()
    legal = derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=two_stage.context.logical_occurrence_id,
        components=(partial_prefix,),
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    )
    assert legal.component_refs[0].raw_work_refs[0].evidence_kind is (
        OccurrenceRawEvidenceKind.PARTIAL_ACCOUNTED_COMMON
    )

    for attacked in (
        (partial_prefix, fallback),
        (partial_prefix, full_prefix),
        (partial_prefix, fallback, full_prefix),
    ):
        with pytest.raises(
            Phase3EOccurrenceAccountingV1Error,
            match="PARTIAL_ACCOUNTED_COMMON.*final unpaired",
        ):
            derive_phase3e_occurrence_work_aggregate_v1(
                logical_occurrence_id=two_stage.context.logical_occurrence_id,
                components=attacked,
                registry=registry,
                comparison_profile=profile,
                actual_profile=actual,
            )

    paired = derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=two_stage.context.logical_occurrence_id,
        components=(full_prefix, fallback),
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    )
    document = legal.to_dict()
    document["component_refs"] = [
        legal.component_refs[0].to_dict(),
        paired.component_refs[1].to_dict(),
    ]
    payload = {
        key: value
        for key, value in document.items()
        if key != "phase3e_occurrence_work_aggregate_id"
    }
    document["phase3e_occurrence_work_aggregate_id"] = content_id(
        OCCURRENCE_WORK_AGGREGATE_DOMAIN,
        payload,
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="PARTIAL_ACCOUNTED_COMMON.*final unpaired",
    ):
        Phase3EOccurrenceWorkAggregateV1.from_dict(document)

def test_forged_smaller_aggregate_cannot_hide_native_source_work() -> None:
    world = _world()
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)

    # Relabel the execution-only vector as the aggregate while retaining the
    # real execution/verification sources.  Its comparison is smaller because
    # it omits the verification suffix, but the aggregation proof cannot replay.
    forged_smaller = AggregatedMarginalWorkV1(
        world.local2_execution.work_vector,
        world.local2_execution.comparison_vector,
        world.local2_execution.actual_projection_proof,
        world.local2_aggregate.aggregation_proof,
    )
    forged_component = replace(
        world.components[3],
        raw_work=(
            RunnerMarginalWorkEvidenceV1(
                forged_smaller,
                world.local2_execution,
                world.local2_verification,
            ),
        ),
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="runner marginal aggregate replay failed",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(*world.components[:3], forged_component),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )


def test_aggregate_source_splicing_and_serialized_source_tampering_fail() -> None:
    world = _world()
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)
    wrong_execution = _record(
        label="smaller-spliced-execution",
        subject_id=world.transaction2.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        values={"local.materialization_ground_steps": 1},
    )
    spliced_component = replace(
        world.components[3],
        raw_work=(
            RunnerMarginalWorkEvidenceV1(
                world.local2_aggregate,
                wrong_execution,
                world.local2_verification,
            ),
        ),
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="runner marginal aggregate replay failed",
    ):
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=world.logical_occurrence_id,
            components=(*world.components[:3], spliced_component),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual,
        )

    aggregate = _derive(world)
    document = aggregate.to_dict()
    aggregate_raw_ref = document["component_refs"][3]["raw_work_refs"][0]
    aggregate_raw_ref["aggregation_source_refs"][0]["work_vector_id"] = _id(
        "forged-aggregate-source-work"
    )
    with pytest.raises(
        Phase3EOccurrenceAccountingV1Error,
        match="component reference content ID mismatch",
    ):
        Phase3EOccurrenceWorkAggregateV1.from_dict(document)
