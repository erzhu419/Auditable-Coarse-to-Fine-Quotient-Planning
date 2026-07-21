from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    RouteKindEnum,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.phase3e_abstract_pass_closure_v1 import (
    Phase3EAbstractPassClosureV1Error,
    close_model_only_abstract_pass_v1,
)
from acfqp.phase3e_model_only_executor_v1 import (
    COUNTER_COVERAGE_BLOCKERS,
    ModelOnlyNoncertificateOutcomeV1,
    ModelOnlyQueryExecutionArtifactV1,
    ModelOnlyQueryExecutionV1,
    ModelOnlyProcessFailedV1,
    execute_model_only_abstract_pass_v1,
    execute_model_only_query_v1,
    model_only_execution_request_v1,
    verify_model_only_failed_prefix_execution_v1,
    verify_model_only_query_execution_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    LOCAL_QUERY_KEY,
    load_phase3c_model_source_v1,
)
from acfqp.routing_v1 import TerminalCode, TypedNotApplicable
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    semantic_verifier_spec_v1,
    verify_abstract_plan_audit_semantics_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


def _record(role: SemanticRole) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    return CounterRecordV1.observe(
        registry,
        semantic_verifier_spec_v1(role).counter_path_for_lane(LaneEnum.EVALUATION),
        1,
        recorder_id=f"model-only-executor-{role.value.lower()}-evaluation-v1",
    )


def _authority(execution: ModelOnlyQueryExecutionV1, source):
    result = execution.model_only_result
    return verify_abstract_plan_audit_semantics_v1(
        result.audit,
        source=source,
        model_only_result=result,
        binding=AttestationContextV1(
            result.route_context,
            TypedNotApplicable("abstract audit precedes route decision"),
            TypedNotApplicable("abstract audit precedes local transaction"),
            4,
            LaneEnum.EVALUATION,
        ),
        verification_work_record=_record(SemanticRole.ABSTRACT_AUDIT),
    )


def test_fresh_process_emits_replayable_native_pass_work_and_keeps_gates_locked() -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    execution = execute_model_only_abstract_pass_v1(source)
    vector = execution.recorded_work.work_vector

    assert execution.model_only_result.outcome.value == "PASS"
    assert vector.subject_id == execution.model_only_result.route_attempt.route_attempt_id
    assert vector.value("common.abstract_bellman_backups") > 0
    assert vector.value("common.abstract_audit_obligations") > 0
    assert vector.value("common.integrity_checks") > 0
    assert vector.value("common.protocol_checks") > 0
    assert vector.value("common.hash_invocations") > 0
    assert vector.value("process.launches") == 1
    assert vector.value("process.exit_successes") == 1
    assert vector.value("solver.attempts") == 1
    assert vector.value("solver.successes") == 1
    assert vector.value("solver.failures") == 0
    assert vector.value("io.read_bytes") > 0
    assert vector.value("io.staged_bytes") > 0
    assert vector.value("io.output_bytes") > 0
    assert vector.value("memory.working_bytes_peak") > 0
    assert all(
        value == 0
        for path, value in vector.values.items()
        if path.startswith(("local.", "fallback.", "rebuild."))
    )
    assert set(COUNTER_COVERAGE_BLOCKERS).issubset(execution.counter_coverage_blockers)
    assert (
        "VISIBLE_RUNTIME_MOUNT_AND_IMPORT_BYTES_NOT_FULLY_ACCOUNTED"
        in execution.counter_coverage_blockers
    )
    assert execution.official_execution_allowed is False
    assert execution.official_scalar_cost is None
    assert execution.official_N_break_even is None

    replayed = ModelOnlyQueryExecutionArtifactV1.from_dict(
        execution.to_dict(), source=source
    )
    assert replayed == execution.artifact
    assert replayed.recorded_work.comparison_vector.work_vector_id == vector.work_vector_id
    with pytest.raises(ValueError, match="executor-minted"):
        verify_model_only_query_execution_v1(replayed)


def test_host_never_replans_and_fresh_process_imports_no_ground_local_or_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    import acfqp.phase3e_model_only_v1 as model_only
    import acfqp.phase3e_rapm_consumer_v1 as consumer
    import acfqp.portable_planner as portable_planner

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("host replayed the model-only planner")

    monkeypatch.setattr(consumer, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(model_only, "run_phase3e_model_only_from_source_v1", forbidden)
    monkeypatch.setattr(portable_planner, "solve_portable_pareto", forbidden)
    before = set(sys.modules)
    execution = execute_model_only_abstract_pass_v1(source)
    imported = set(sys.modules) - before

    assert execution.model_only_result.outcome.value == "PASS"
    forbidden_prefixes = (
        "acfqp.domains",
        "acfqp.frozen_phase3c",
        "acfqp.phase3d",
        "acfqp.phase3e_fallback",
        "acfqp.phase3e_ground_handoff",
        "acfqp.phase3e_local_",
        "acfqp.general_local",
        "acfqp.local_",
        "acfqp.planning.ground",
    )
    assert not any(name.startswith(forbidden_prefixes) for name in imported)


def test_h2_fresh_worker_runs_once_without_host_replanning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    import acfqp.phase3e_model_only_executor_v1 as executor
    import acfqp.phase3e_model_only_v1 as model_only
    import acfqp.phase3e_rapm_consumer_v1 as consumer

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("host replanned the H2 failed prefix")

    monkeypatch.setattr(consumer, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(model_only, "run_phase3e_model_only_from_source_v1", forbidden)
    real_run = executor.subprocess.run
    launches = 0

    def counted_run(*args: object, **kwargs: object):
        nonlocal launches
        launches += 1
        return real_run(*args, **kwargs)

    monkeypatch.setattr(executor.subprocess, "run", counted_run)
    execution = execute_model_only_query_v1(source)
    assert launches == 1
    assert verify_model_only_failed_prefix_execution_v1(execution) is execution


def test_producer_output_needs_external_audit_authority_then_closes_strict_pass() -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    execution = execute_model_only_abstract_pass_v1(source)
    result = execution.model_only_result

    with pytest.raises(
        Phase3EAbstractPassClosureV1Error,
        match="retained semantic authority",
    ):
        close_model_only_abstract_pass_v1(
            execution,
            execution,  # type: ignore[arg-type]
            work_verification_record=_record(SemanticRole.WORK_VECTOR),
            terminal_verification_record=_record(
                SemanticRole.TERMINAL_CLASSIFICATION
            ),
        )

    closure = close_model_only_abstract_pass_v1(
        execution,
        _authority(execution, source),
        work_verification_record=_record(SemanticRole.WORK_VECTOR),
        terminal_verification_record=_record(SemanticRole.TERMINAL_CLASSIFICATION),
    )
    assert closure.terminal_artifact.terminal_code is TerminalCode.ABSTRACT_CERTIFIED
    assert (
        closure.terminal_artifact.actual_work_vector_id
        == execution.recorded_work.work_vector.work_vector_id
    )
    assert closure.official_execution_allowed is False


def test_failed_audit_mints_honest_common_prefix_but_never_pass_authority() -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    execution = execute_model_only_query_v1(source)
    verified = verify_model_only_failed_prefix_execution_v1(execution)
    vector = verified.recorded_work.work_vector
    assert verified is execution
    assert execution.model_only_result.outcome.value == "FAIL"
    assert execution.model_only_result.ground_binding_required is True
    assert vector.route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
    assert execution.recorded_work.actual_projection_proof.work_scope is (
        ActualWorkScope.COMMON_PREFIX
    )
    assert vector.value("common.abstract_bellman_backups") > 0
    assert all(
        value == 0
        for path, value in vector.values.items()
        if path.startswith(("local.", "fallback.", "rebuild."))
    )
    assert "FAILED_MODEL_ONLY_PREFIX_HAS_NO_DISTINCT_ROUTE_KIND" not in (
        execution.counter_coverage_blockers
    )
    with pytest.raises(
        Phase3EAbstractPassClosureV1Error, match="failed-prefix"
    ):
        close_model_only_abstract_pass_v1(
            execution,
            _authority(execution, source),
            work_verification_record=_record(SemanticRole.WORK_VECTOR),
            terminal_verification_record=_record(
                SemanticRole.TERMINAL_CLASSIFICATION
            ),
        )

    with pytest.raises(ModelOnlyNoncertificateOutcomeV1) as raised:
        execute_model_only_abstract_pass_v1(source)

    error = raised.value
    assert error.result.outcome.value == "FAIL"
    assert error.result.ground_binding_required is True
    assert error.event_trace.totals["common.abstract_bellman_backups"] > 0
    assert error.recorded_work.work_vector.route_kind is (
        RouteKindEnum.ABSTRACT_FAILED_PREFIX
    )


def test_process_failure_retains_noncertificate_boundary_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    import acfqp.phase3e_model_only_executor_v1 as executor

    monkeypatch.setattr(
        executor.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=("python",), returncode=19, stdout="", stderr="worker failed"
        ),
    )
    with pytest.raises(ModelOnlyProcessFailedV1) as raised:
        execute_model_only_abstract_pass_v1(source)
    evidence = raised.value.evidence
    assert evidence.returncode == 19
    assert evidence.staged_bytes > 0
    assert evidence.output_bytes_observed == 0
    assert evidence.official_execution_allowed is False


def test_resigned_trace_or_lock_attack_fails_roundtrip() -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    execution = execute_model_only_abstract_pass_v1(source)
    document = execution.to_dict()
    document["native_event_trace"]["events"][0]["amount"] += 1
    with pytest.raises((ValueError, TypeError), match="event trace ID mismatch"):
        ModelOnlyQueryExecutionArtifactV1.from_dict(document, source=source)

    document = execution.to_dict()
    document["official_execution_allowed"] = True
    with pytest.raises(ValueError, match="non-official lock fields changed"):
        ModelOnlyQueryExecutionArtifactV1.from_dict(document, source=source)


def test_runtime_deny_finder_blocks_real_versioned_ground_module_imports() -> None:
    names = (
        "acfqp.phase3e_fallback_v1",
        "acfqp.phase3e_ground_handoff_v1",
        "acfqp.phase3e_local_semantics_v1",
    )
    script = f"""
import importlib
import sys
sys.path.insert(0, {str(ROOT / 'src')!r})
from acfqp.phase3e_model_only_runtime_v1 import _GroundImportDenyFinder
sys.meta_path.insert(0, _GroundImportDenyFinder())
failed = []
for name in {names!r}:
    try:
        importlib.import_module(name)
    except ImportError:
        continue
    failed.append(name)
if failed:
    raise SystemExit('forbidden imports succeeded: ' + repr(failed))
"""
    completed = subprocess.run(
        (sys.executable, "-I", "-B", "-c", script),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr

    # Suffix matching is deliberately constrained to _v<digits>, not a raw
    # prefix rule that could block an unrelated safe module name.
    from acfqp.phase3e_model_only_runtime_v1 import _is_forbidden_module_v1

    assert not _is_forbidden_module_v1("acfqp.phase3e_fallback_victim")
    assert not _is_forbidden_module_v1("acfqp.phase3e_fallback_version")


def test_executor_rejects_source_copy_that_lost_loader_authority() -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    lost_authority = copy.copy(source)
    with pytest.raises(ValueError, match="live source authority"):
        model_only_execution_request_v1(lost_authority)
    with pytest.raises(ValueError, match="live source authority"):
        execute_model_only_abstract_pass_v1(lost_authority)


def test_execution_copy_constructor_and_roundtrip_never_mint_live_authority() -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    execution = execute_model_only_query_v1(source)
    transport = ModelOnlyQueryExecutionArtifactV1.from_dict(
        execution.to_dict(), source=source
    )
    with pytest.raises(ValueError, match="executor-minted"):
        verify_model_only_failed_prefix_execution_v1(transport)
    with pytest.raises(ValueError, match="not minted"):
        ModelOnlyQueryExecutionV1(transport, object())
    with pytest.raises(AttributeError, match="immutable"):
        copy.copy(execution)
