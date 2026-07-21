from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
import pickle

import pytest

import acfqp.phase3d as phase3d
import acfqp.phase3e_local_adapter_v1 as local_adapter
import acfqp.phase3e_model_failure_occurrence_v1 as occurrence_consumer
from acfqp.access_protocol_v1 import (
    AccessRouteScope,
    PRESELECTION_READ_OPERATIONS,
)
from acfqp.domains.g2048 import G2048SafeChainKernel
from acfqp.phase3e_ground_handoff_v1 import (
    open_ground_binding_after_failed_audit_v1,
)
from acfqp.phase3e_model_failure_consumer_v1 import (
    MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS,
    MODEL_FAILURE_CONSUMER_STATUS,
    Phase3EModelFailureConsumerV1Error,
    prepare_phase3e_from_model_failure_v1,
    require_model_only_failed_prefix_accounting_authority_v1,
    run_prepared_model_failure_consumer_v1,
    verify_and_mint_model_only_failed_prefix_accounting_authority_v1,
)
from acfqp.phase3e_model_only_executor_v1 import execute_model_only_query_v1
from acfqp.phase3e_model_failure_occurrence_v1 import (
    MODEL_FAILURE_OCCURRENCE_STATUS,
    Phase3EModelFailureOccurrenceV1Error,
    require_model_failure_occurrence_closure_v1,
    run_prepared_model_failure_occurrence_v1,
)
from acfqp.phase3e_model_failure_preparation_accounting_v1 import (
    PREPARATION_EXCLUSIONS,
    PREPARATION_OCCURRENCE_CHARGE_STATUS,
    Phase3EModelFailurePreparationAccountingV1Error,
)
from acfqp.phase3e_occurrence_accounting_v1 import (
    OccurrenceWorkComponentKind,
)
from acfqp.phase3e_occurrence_runner_v1 import OccurrenceClosureCodeV1
from acfqp.phase3e_rapm_consumer_v1 import (
    LOCAL_QUERY_KEY,
    load_phase3c_model_source_v1,
)
from acfqp.phase3e_sealed_executor_v1 import (
    RuntimeFactoryCardinalityV1,
    RuntimeTreeCASV1,
)
from acfqp.routing_v1 import RouteSelection, TerminalCode
from acfqp.semantic_verification_v1 import (
    require_terminal_classification_result_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


@pytest.fixture(scope="module")
def failed_prefix_inputs(tmp_path_factory: pytest.TempPathFactory):
    source = load_phase3c_model_source_v1(
        PHASE3C, query_key=LOCAL_QUERY_KEY
    )
    execution = execute_model_only_query_v1(source)
    prefix = verify_and_mint_model_only_failed_prefix_accounting_authority_v1(
        execution, source=source
    )
    ground = open_ground_binding_after_failed_audit_v1(
        PHASE3C,
        model_only_result=execution.model_only_result,
        abstract_audit_authority=prefix.audit_authority,
    )
    cas = RuntimeTreeCASV1(
        (tmp_path_factory.mktemp("model-failure-runtime") / "cas").resolve()
    )
    manifest = cas.snapshot_build_tree(ROOT / "src")
    cardinality = RuntimeFactoryCardinalityV1.from_manifest(manifest)
    return source, execution, prefix, ground, cas, manifest, cardinality


def test_failed_prefix_is_an_accounted_opaque_authority_not_bare_work(
    failed_prefix_inputs,
) -> None:
    _source, execution, prefix, _ground, _cas, _manifest, _cardinality = (
        failed_prefix_inputs
    )
    assert prefix.execution is execution
    assert prefix.audit_authority.outcome == "FAIL"
    assert prefix.closure.plan.obligations[0].artifact_role == "ABSTRACT_AUDIT"
    assert prefix.closure.plan.obligations[0].expected_result == "FAIL"
    assert prefix.closure.core.core_work_vector_id == (
        execution.recorded_work.work_vector.work_vector_id
    )
    assert prefix.aggregate_work.work_vector.value("common.protocol_checks") == (
        execution.recorded_work.work_vector.value("common.protocol_checks") + 1
    )

    for bare in (execution.recorded_work, execution.to_dict(), prefix.metadata()):
        with pytest.raises(
            Phase3EModelFailureConsumerV1Error,
            match="retained failed-prefix accounting authority",
        ):
            require_model_only_failed_prefix_accounting_authority_v1(bare)

    for copier, message in (
        (copy.copy, "cannot be copied"),
        (copy.deepcopy, "cannot be deep-copied"),
    ):
        with pytest.raises(Phase3EModelFailureConsumerV1Error, match=message):
            copier(prefix)
    with pytest.raises(
        Phase3EModelFailureConsumerV1Error,
        match="cannot be serialized",
    ):
        pickle.dumps(prefix)
    with pytest.raises(
        Phase3EModelFailureConsumerV1Error,
        match="copied or modified live authority",
    ):
        replace(prefix)
    with pytest.raises(
        Phase3EModelFailureConsumerV1Error,
        match="copied or modified live authority",
    ):
        replace(prefix, _mint=copy.copy(prefix._mint))
    with pytest.raises(
        Phase3EModelFailureConsumerV1Error,
        match="copied or modified live authority",
    ):
        replace(prefix, aggregate_work_vector_id=prefix.model_only_result_id)


def test_production_preparation_has_no_planner_auditor_kernel_or_route_work(
    failed_prefix_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source, _execution, prefix, ground, cas, manifest, cardinality = (
        failed_prefix_inputs
    )

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("forbidden preparation-time operation")

    monkeypatch.setattr(phase3d, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(phase3d, "audit_abstract_policy", forbidden)
    monkeypatch.setattr(phase3d, "prepare_safe_chain_estimate_context", forbidden)
    monkeypatch.setattr(phase3d, "materialize_authorized_slice", forbidden)
    monkeypatch.setattr(phase3d, "compile_sparse_recovery_inputs", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "actions", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "step", forbidden)
    monkeypatch.setattr(local_adapter, "_run_fresh_general_solver", forbidden)
    monkeypatch.setattr(RuntimeTreeCASV1, "resolve", forbidden)

    prepared = prepare_phase3e_from_model_failure_v1(
        prefix,
        ground,
        runtime_manifest=manifest,
        runtime_cardinality=cardinality,
        runtime_cas=cas,
    )
    assert prepared.selected_route is RouteSelection.LOCAL
    assert prepared.selected_factory.construction_accounting is None
    assert prepared.prepared.common_prefix_work is prefix.aggregate_work
    accounting = prepared.route_preparation_accounting
    assert accounting.source_prefix is prefix.aggregate_work
    assert accounting.incremental_work is accounting.preparation_work
    assert accounting.occurrence_charge_status == (
        PREPARATION_OCCURRENCE_CHARGE_STATUS
    )
    assert accounting.trace.excluded_work == PREPARATION_EXCLUSIONS
    assert accounting.trace.post_decision_point_component is True
    assert accounting.preparation_work.work_vector.value(
        "local.causal_candidate_evaluations"
    ) == 4
    assert accounting.preparation_work.work_vector.value(
        "common.protocol_checks"
    ) == 18
    assert accounting.preparation_work.work_vector.value(
        "common.integrity_checks"
    ) == 3
    assert accounting.preparation_work.work_vector.value(
        "control.cap_checks"
    ) == 5
    assert accounting.preparation_work.work_vector.value(
        "common.hash_invocations"
    ) == 0
    assert accounting.preparation_work.work_vector.value("io.read_bytes") == 0
    assert accounting.aggregate_work.work_vector.value(
        "common.protocol_checks"
    ) == prefix.aggregate_work.work_vector.value("common.protocol_checks") + 18
    assert prepared.prepared.decision_point.common_prefix_work_id == (
        prefix.aggregate_work.work_vector.work_vector_id
    )
    assert accounting.aggregate_work.work_vector.work_vector_id != (
        prefix.aggregate_work.work_vector.work_vector_id
    )
    assert tuple(row.operation for row in prepared.prepared.preselection_reads) == (
        PRESELECTION_READ_OPERATIONS
    )
    runtime_id = cardinality.runtime_factory_cardinality_id
    assert runtime_id in prepared.route_authorities.local_bound.source_artifact_ids
    assert runtime_id in prepared.route_authorities.fallback_bound.source_artifact_ids
    assert prepared.accounting_status == MODEL_FAILURE_CONSUMER_STATUS
    assert prepared.accounting_blockers == MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS
    assert prepared.official_execution_allowed is False
    assert (
        "MODEL_FAILURE_ROUTE_PREPARATION_OPERATIONAL_WORK_NOT_NATIVE_ACCOUNTED"
        in prepared.accounting_blockers
    )


def test_runtime_cardinality_and_prefix_splices_fail_before_factory_resolution(
    failed_prefix_inputs,
) -> None:
    _source, _execution, prefix, ground, cas, manifest, cardinality = (
        failed_prefix_inputs
    )
    forged_cardinality = replace(
        cardinality,
        total_bytes=cardinality.total_bytes + 1,
    )
    with pytest.raises(
        Phase3EModelFailureConsumerV1Error,
        match="runtime cardinality differs",
    ):
        prepare_phase3e_from_model_failure_v1(
            prefix,
            ground,
            runtime_manifest=manifest,
            runtime_cardinality=forged_cardinality,
            runtime_cas=cas,
        )


def test_prepared_consumer_rejects_equal_content_live_object_splices(
    failed_prefix_inputs,
) -> None:
    _source, _execution, prefix, ground, cas, manifest, cardinality = (
        failed_prefix_inputs
    )
    prepared = prepare_phase3e_from_model_failure_v1(
        prefix,
        ground,
        runtime_manifest=manifest,
        runtime_cardinality=cardinality,
        runtime_cas=cas,
    )
    for copier, message in (
        (copy.copy, "cannot be copied"),
        (copy.deepcopy, "cannot be deep-copied"),
    ):
        with pytest.raises(Phase3EModelFailureConsumerV1Error, match=message):
            copier(prepared)
    with pytest.raises(
        Phase3EModelFailureConsumerV1Error,
        match="cannot be serialized",
    ):
        pickle.dumps(prepared)
    with pytest.raises(
        Phase3EModelFailureConsumerV1Error,
        match="copied or modified live authority",
    ):
        replace(prepared)
    attacks = (
        {
            "runtime_manifest": type(prepared.runtime_manifest).from_dict(
                prepared.runtime_manifest.to_dict()
            )
        },
        {
            "runtime_cardinality": type(prepared.runtime_cardinality).from_dict(
                prepared.runtime_cardinality.to_dict()
            )
        },
        {"route_authorities": replace(prepared.route_authorities)},
        {
            "route_preparation_accounting": replace(
                prepared.route_preparation_accounting
            )
        },
        {"prepared": replace(prepared.prepared)},
        {
            "selected_recipe": type(prepared.selected_recipe).from_dict(
                prepared.selected_recipe.to_dict()
            )
        },
    )
    for attack in attacks:
        with pytest.raises(
            Phase3EModelFailureConsumerV1Error,
            match="copied or modified live authority",
        ):
            replace(prepared, **attack)

    with pytest.raises(
        Phase3EModelFailurePreparationAccountingV1Error,
        match="event contract is missing",
    ):
        replace(
            prepared.route_preparation_accounting.trace,
            events=prepared.route_preparation_accounting.trace.events[:-1],
        )
    events = prepared.route_preparation_accounting.trace.events
    with pytest.raises(
        Phase3EModelFailurePreparationAccountingV1Error,
        match="sequence is missing, duplicated, or reordered",
    ):
        replace(
            prepared.route_preparation_accounting.trace,
            events=(events[1], events[0], *events[2:]),
        )
    with pytest.raises(
        Phase3EModelFailurePreparationAccountingV1Error,
        match="operation IDs must be unique",
    ):
        replace(
            prepared.route_preparation_accounting.trace,
            events=(
                events[0],
                replace(events[1], operation_id=events[0].operation_id),
                *events[2:],
            ),
        )
    with pytest.raises(
        Phase3EModelFailurePreparationAccountingV1Error,
        match="cannot hide exclusions",
    ):
        replace(
            prepared.route_preparation_accounting.trace,
            excluded_work=(),
        )
    with pytest.raises(
        Phase3EModelFailurePreparationAccountingV1Error,
        match="cannot claim occurrence charging",
    ):
        replace(
            prepared.route_preparation_accounting,
            occurrence_charge_status="CHARGED",
        )

    for attack in (
        {"accounting_blockers": ()},
        {"official_execution_allowed": True},
    ):
        with pytest.raises(
            Phase3EModelFailureConsumerV1Error,
            match="copied or modified live authority",
        ):
            replace(prepared, **attack)


def test_h2_failed_model_executes_only_selected_sealed_local_route(
    failed_prefix_inputs,
) -> None:
    _source, execution, prefix, ground, cas, manifest, cardinality = (
        failed_prefix_inputs
    )
    prepared = prepare_phase3e_from_model_failure_v1(
        prefix,
        ground,
        runtime_manifest=manifest,
        runtime_cardinality=cardinality,
        runtime_cas=cas,
    )
    result = run_prepared_model_failure_consumer_v1(prepared)

    assert result.selected_route is RouteSelection.LOCAL
    assert result.upper_compliance == "WITHIN_SELECTED_UPPER"
    assert result.sealed_executor_profile is True
    assert result.two_stage_accounting_profile is True
    assert result.common_two_stage_accounting is not None
    assert result.selected_two_stage_accounting is not None
    assert prepared.selected_factory.construction_accounting is not None
    assert result.selected_route_work.work_vector.value(
        "local.materialization_ground_steps"
    ) == 16
    assert result.selected_route_work.work_vector.value(
        "local.postaudit_ground_steps"
    ) == 8
    assert result.common_two_stage_accounting.core.core_work_vector_id == (
        prefix.aggregate_work.work_vector.work_vector_id
    )
    assert result.common_two_stage_accounting.aggregate_work.work_vector.value(
        "common.protocol_checks"
    ) == prefix.aggregate_work.work_vector.value("common.protocol_checks") + 6
    assert all(
        event.route_scope is AccessRouteScope.COMMON
        for event in result.access_log.events
        if event.sequence_number
        <= result.freeze_attestation.last_preselection_sequence
    )
    assert all(
        event.route_scope is not AccessRouteScope.FALLBACK
        for event in result.access_log.events
    )
    assert result.common_prefix_work.work_vector.subject_id == (
        execution.model_only_result.route_attempt.route_attempt_id
    )


def _deterministic_inprocess_local_worker(
    capability,
    ground_slice,
    request,
    *,
    operational_no_full_replay=False,
    runtime_source_root=None,
):
    """Unit-only deterministic worker result without claiming process isolation."""

    from acfqp.general_local_solver import solve_general_local_recovery

    assert operational_no_full_replay is True
    assert runtime_source_root is not None
    result = solve_general_local_recovery(
        capability, ground_slice, request
    ).to_dict()
    return result, {
        "schema": "acfqp.test_only_inprocess_runtime_attestation.v1",
        "attestation_id": "test-only-inprocess-local-worker",
        "result_id": result["result_id"],
        "working_set_limit_bytes": 256 * 1024 * 1024,
    }


def test_model_failure_occurrence_closes_certified_local_with_typed_terminal(
    failed_prefix_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source, _execution, prefix, ground, cas, manifest, cardinality = (
        failed_prefix_inputs
    )
    monkeypatch.setattr(
        local_adapter,
        "_run_fresh_general_solver",
        _deterministic_inprocess_local_worker,
    )
    prepared = prepare_phase3e_from_model_failure_v1(
        prefix,
        ground,
        runtime_manifest=manifest,
        runtime_cardinality=cardinality,
        runtime_cas=cas,
    )
    closure = run_prepared_model_failure_occurrence_v1(prepared)

    assert closure.status == MODEL_FAILURE_OCCURRENCE_STATUS
    assert closure.occurrence.closure_code is (
        OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY
    )
    assert closure.terminal_artifact.terminal_code is (
        TerminalCode.LOCAL_GROUND_RECOVERY
    )
    assert closure.terminal_artifact.terminal_scope == "LOGICAL_OCCURRENCE"
    verified_terminal, _attestation = require_terminal_classification_result_v1(
        closure.terminal_result
    )
    assert verified_terminal == closure.terminal_artifact
    assert tuple(
        row.component_kind for row in closure.occurrence.work_components
    ) == (
        OccurrenceWorkComponentKind.COMMON_PREFIX,
        OccurrenceWorkComponentKind.LOCAL_TRANSACTION,
    )
    assert len(closure.occurrence.occurrence_work.component_refs) == 2
    run = closure.occurrence.decision_runs[0]
    delegate = run.route_execution.delegate_execution_work
    assert delegate is not None
    assert (
        run.route_execution.semantic_execution.local_result.work_vector_id
        == delegate.work_vector.work_vector_id
    )
    assert delegate.work_vector.work_vector_id != (
        run.selected_route_work.work_vector.work_vector_id
    )
    marginal_source = closure.occurrence.work_components[1].raw_work[0]
    assert marginal_source.execution is run.selected_route_work
    assert marginal_source.execution.work_vector.value(
        "common.hash_invocations"
    ) > delegate.work_vector.value("common.hash_invocations")
    assert closure.accounting_blockers == MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS
    assert prepared.route_preparation_accounting.occurrence_charge_status == (
        PREPARATION_OCCURRENCE_CHARGE_STATUS
    )
    assert run.common_two_stage_accounting.aggregate_work.work_vector.value(
        "local.causal_candidate_evaluations"
    ) == 0
    assert run.aggregate_marginal_work.aggregate_work_vector.value(
        "local.causal_candidate_evaluations"
    ) == 0
    assert prepared.route_preparation_accounting.incremental_work.work_vector.value(
        "local.causal_candidate_evaluations"
    ) == 4
    assert closure.official_execution_allowed is False
    assert closure.counter_completeness_certified is False
    assert "GATE_NOT_RUN" in closure.counter_completeness_gate_status
    assert require_model_failure_occurrence_closure_v1(closure) is closure

    for copier in (copy.copy, copy.deepcopy):
        with pytest.raises(
            Phase3EModelFailureOccurrenceV1Error,
            match="cannot be copied|cannot be deep-copied",
        ):
            copier(closure)
    with pytest.raises(
        Phase3EModelFailureOccurrenceV1Error,
        match="copied or modified live authority",
    ):
        replace(closure)

    attacks = (
        {"accounting_blockers": ()},
        {"official_execution_allowed": True},
        {"counter_completeness_certified": True},
        {"occurrence": replace(closure.occurrence)},
        {
            "terminal_artifact": type(closure.terminal_artifact).from_dict(
                closure.terminal_artifact.to_dict()
            )
        },
    )
    for attack in attacks:
        with pytest.raises(
            Phase3EModelFailureOccurrenceV1Error,
            match="copied or modified|live members differ|cannot hide",
        ):
            replace(closure, **attack)


def test_model_failure_occurrence_preserves_failed_route_noncertificate_work(
    failed_prefix_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source, _execution, prefix, ground, cas, manifest, cardinality = (
        failed_prefix_inputs
    )

    def fail_after_preparation(*_args, **_kwargs):
        raise RuntimeError("injected local worker failure")

    monkeypatch.setattr(
        local_adapter, "_run_fresh_general_solver", fail_after_preparation
    )
    prepared = prepare_phase3e_from_model_failure_v1(
        prefix,
        ground,
        runtime_manifest=manifest,
        runtime_cardinality=cardinality,
        runtime_cas=cas,
    )
    closure = run_prepared_model_failure_occurrence_v1(prepared)

    assert closure.occurrence.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
    assert closure.terminal_artifact is None
    assert closure.terminal_result is None
    assert closure.occurrence.occurrence_failure_terminal is not None
    assert closure.occurrence.occurrence_terminal is not None
    assert len(closure.occurrence.work_components) == 2
    failed = closure.occurrence.work_components[-1].raw_work[0]
    assert failed.execution.work_vector.value(
        "local.materialization_ground_steps"
    ) == 16
    assert failed.execution.work_vector.value("process.exit_failures") == 1
    assert closure.accounting_blockers == MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS
    assert closure.official_execution_allowed is False


def test_model_failure_occurrence_nonselected_route_is_rejection_only(
    failed_prefix_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source, _execution, prefix, ground, cas, manifest, cardinality = (
        failed_prefix_inputs
    )
    prepared = prepare_phase3e_from_model_failure_v1(
        prefix,
        ground,
        runtime_manifest=manifest,
        runtime_cardinality=cardinality,
        runtime_cas=cas,
    )

    def attack_nonselected(
        _prepared,
        *,
        local_executor,
        fallback_executor,
        **_kwargs,
    ):
        assert prepared.selected_route is RouteSelection.LOCAL
        fallback_executor(None, None, None)

    monkeypatch.setattr(
        occurrence_consumer,
        "run_phase3e_occurrence_v1",
        attack_nonselected,
    )
    with pytest.raises(
        Phase3EModelFailureOccurrenceV1Error,
        match="nonselected model-failure route",
    ):
        run_prepared_model_failure_occurrence_v1(prepared)
