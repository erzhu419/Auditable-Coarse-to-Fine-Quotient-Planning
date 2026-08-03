from __future__ import annotations

import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero
from acfqp.phase3e_model_only_executor_v1 import execute_model_only_abstract_pass_v1
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    load_phase3c_model_source_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


@pytest.fixture(scope="module")
def case():
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    execution = execute_model_only_abstract_pass_v1(source)
    report = coverage.audit_abstract_certified_accounting_coverage_v1(execution)
    closure = zero.close_abstract_certified_zero_value_subset_v1(execution, report)
    return source, execution, report, closure


def test_exact_revised_partition_closes_23_native_and_three_derived_values(
    case,
) -> None:
    _source, _execution, _report, closure = case
    document = closure.to_document()

    assert len(closure.native_zero_proofs) == 23
    assert len(closure.derived_complement_value_proofs) == 3
    assert len(closure.residual_gaps) == 176
    assert document["closed_zero_value_count"] == 26
    assert document["native_zero_proof_count"] == 23
    assert document["derived_complement_value_proof_count"] == 3
    assert document["derived_complement_proofs_are_native_zero_attestations"] is False
    assert document["all_eight_derived_reconciliations_complete"] is False
    assert document["production_completion_status"] == "BLOCKED_176_REQUIRED_PATH_GAPS"
    assert document["central_domain_registration_completed"] is True


def test_23_native_zeros_are_only_for_forbidden_route_stage_families(case) -> None:
    _source, _execution, _report, closure = case
    proofs = {row.path: row for row in closure.native_zero_proofs}
    assert all(
        row.kind is zero.ZeroValueProofKindV1.FORBIDDEN_ROUTE_STAGE_SOURCE_CLOSED
        for row in proofs.values()
    )
    assert {
        "control.cap_checks",
        "control.cap_rejections",
        "fallback.ground_steps",
        "local.materialization_ground_steps",
        "local.solver_policy_assignments",
        "rebuild.ground_steps",
    } <= set(proofs)
    assert all(
        all(
            stage in {"LOCAL_ATTEMPT", "DIRECT_FALLBACK", "REBUILD"}
            and disposition == "FORBIDDEN"
            for stage, disposition in row.stage_contexts
        )
        for row in proofs.values()
    )
    assert all(row.operation_boundary_site_ids for row in proofs.values())
    assert all(row.source_v1_record_id is not None for row in proofs.values())
    assert all(row.to_document()["missing_event_inferred_zero"] is False for row in proofs.values())
    assert all(row.to_document()["source_v1_record_relabelled_as_v6"] is False for row in proofs.values())


def test_three_failure_complements_are_not_native_zero_attestations(case) -> None:
    _source, execution, _report, closure = case
    proofs = {row.path: row for row in closure.derived_complement_value_proofs}
    assert set(proofs) == {
        "process.exit_failures",
        "route.failures",
        "solver.failures",
    }
    assert all(
        row.kind is zero.ZeroValueProofKindV1.SUCCESSFUL_COMPLETION_COMPLEMENT
        for row in proofs.values()
    )
    assert all(len(row.supporting_record_ids) == 2 for row in proofs.values())
    assert all(not row.operation_boundary_site_ids for row in proofs.values())
    record_ids = {
        row.path: row.record_id
        for row in execution.recorded_work.work_vector.records
    }
    assert set(proofs["process.exit_failures"].supporting_record_ids) == {
        record_ids["process.launches"],
        record_ids["process.exit_successes"],
    }
    assert set(proofs["route.failures"].supporting_record_ids) == {
        record_ids["route.attempts"],
        record_ids["route.successes"],
    }
    assert set(proofs["solver.failures"].supporting_record_ids) == {
        record_ids["solver.attempts"],
        record_ids["solver.successes"],
    }


def test_mounted_payload_zero_is_rejected_not_closed(case) -> None:
    _source, _execution, _report, closure = case
    assert "io.mounted_bytes_peak" not in {
        row.path for row in closure.native_zero_proofs
    }
    assert "io.mounted_bytes_peak" not in {
        row.path for row in closure.derived_complement_value_proofs
    }
    gap = next(
        row for row in closure.residual_gaps if row.path == "io.mounted_bytes_peak"
    )
    assert gap.code is zero.ResidualGapCodeV1.MOUNTED_PAYLOAD_PEAK_WAS_NOT_MEASURED
    assert gap.source_v1_value == 0
    assert closure.to_document()["mounted_payload_peak_zero_accepted"] is False


def test_160_v6_only_paths_remain_typed_blockers_without_zero_inference(case) -> None:
    _source, _execution, _report, closure = case
    required = tuple(
        row
        for row in closure.residual_gaps
        if row.code is zero.ResidualGapCodeV1.REQUIRED_STAGE_OWNER_EVIDENCE_MISSING
    )
    optional = tuple(
        row
        for row in closure.residual_gaps
        if row.code
        is zero.ResidualGapCodeV1.OPTIONAL_STAGE_REACHABILITY_AND_TRANSITIVE_SOURCE_CLOSURE_MISSING
    )
    assert len(required) == 100
    assert len(optional) == 60
    assert all(row.source_v1_record_id is None for row in (*required, *optional))
    assert all(row.source_v1_value is None for row in (*required, *optional))
    assert all(row.to_document()["missing_event_inferred_zero"] is False for row in (*required, *optional))
    assert {
        "acquisition.initial_engine_ground_draws",
        "build.initial_model_rows_built",
        "closure.reconciliation_engine_ground_draws",
    } <= {row.path for row in required}
    assert {
        "acquisition.incremental_engine_ground_draws",
        "build.open_checkpoint_model_rows_built",
        "audit.dynamic_root_rows_scanned",
    } <= {row.path for row in optional}
    assert closure.to_document()["additional_v6_only_paths_closed_as_zero"] == 0


def test_all_202_original_gap_identities_are_preserved_exactly_once(case) -> None:
    _source, _execution, report, closure = case
    original = {row.path: row.gap_id for row in report.path_gaps}
    revised = {
        row.path: row.original_path_gap_id
        for row in (
            *closure.native_zero_proofs,
            *closure.derived_complement_value_proofs,
            *closure.residual_gaps,
        )
    }
    assert revised == original
    assert len(revised) == 202


def test_execution_window_binds_real_process_route_solver_and_source(case) -> None:
    _source, execution, report, closure = case
    window = closure.execution_window
    assert window.coverage_report_id == report.report_id
    assert window.operational_execution_id == execution.operational_execution_id
    assert window.request_id == execution.request_id
    assert window.worker_output_id == execution.worker_output_id
    assert window.event_trace_id == execution.native_event_trace.event_trace_id
    assert dict(window.process_values) == {
        "process.exit_failures": 0,
        "process.exit_successes": 1,
        "process.launches": 1,
    }
    assert dict(window.route_values) == {
        "route.attempts": 1,
        "route.failures": 0,
        "route.successes": 1,
    }
    assert dict(window.solver_values) == {
        "solver.attempts": 1,
        "solver.failures": 0,
        "solver.successes": 1,
    }
    assert window.to_document()["complete_transitive_import_manifest_available"] is False


def test_formal_artifacts_terminal_and_gates_remain_locked(case) -> None:
    _source, _execution, _report, closure = case
    document = closure.to_document()
    assert document["all_nine_shared_resource_receipts_complete"] is False
    assert document["all_eight_derived_reconciliations_complete"] is False
    assert document["formal_v6_counter_records_issued"] == 0
    assert document["formal_v6_work_vector_issued"] is False
    assert document["formal_v6_comparison_vector_issued"] is False
    assert document["terminal_artifact_id"] is None
    assert document["campaign_occurrence_closure_id"] is None
    assert document["certificate_issued"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_n_break_even"] is None
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert document["workload_economics_gate_status"] == (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )


def test_independent_replay_accepts_exact_and_rejects_resigned_partition(case) -> None:
    _source, execution, report, closure = case
    accepted = zero.verify_abstract_certified_zero_value_closure_document_v1(
        closure.to_document(), execution, report
    )
    assert accepted.outcome is (
        zero.ReplayOutcomeV1.ZERO_SUBSET_CLOSED_ACCOUNTING_STILL_BLOCKED
    )
    assert accepted.closure is not None
    assert accepted.closure.closure_id == closure.closure_id
    assert accepted.to_document()["terminal_issued"] is False

    attacked = copy.deepcopy(closure.to_document())
    attacked["native_zero_proofs"][0]["proved_value"] = 1
    attacked["zero_value_closure_id"] = "0" * 64
    rejected = zero.verify_abstract_certified_zero_value_closure_document_v1(
        attacked, execution, report
    )
    assert rejected.outcome is zero.ReplayOutcomeV1.DOCUMENT_BLOCKED
    assert rejected.closure is None
    assert rejected.to_document()["terminal_issued"] is False


def test_source_archive_attack_prevents_zero_subset_issuance(case) -> None:
    _source, execution, report, _closure = case
    archive = coverage.load_official_abstract_certified_source_archive_v1()
    archive["acfqp.phase3e_model_only_runtime_v1"] += b"\n# source attack\n"
    with pytest.raises(ValueError, match="source replay is blocked"):
        zero.close_abstract_certified_zero_value_subset_v1(
            execution, report, source_archive=archive
        )


def test_zero_closure_does_not_call_planner_or_legacy_terminalizer(
    case, monkeypatch: pytest.MonkeyPatch
) -> None:
    _source, execution, report, _closure = case
    import acfqp.phase3e_abstract_pass_closure_v1 as legacy_closure
    import acfqp.phase3e_model_only_v1 as model_only
    import acfqp.phase3e_rapm_consumer_v1 as consumer

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("zero closure crossed a forbidden execution boundary")

    monkeypatch.setattr(legacy_closure, "close_model_only_abstract_pass_v1", forbidden)
    monkeypatch.setattr(model_only, "run_phase3e_model_only_from_source_v1", forbidden)
    monkeypatch.setattr(consumer, "solve_portable_pareto", forbidden)
    rebuilt = zero.close_abstract_certified_zero_value_subset_v1(execution, report)
    assert rebuilt.closure_id == _closure.closure_id
    assert rebuilt.to_document()["terminal_artifact_id"] is None


def test_caller_cannot_mint_native_or_derived_zero_value_proof(case) -> None:
    _source, _execution, _report, closure = case
    source = closure.derived_complement_value_proofs[0]
    with pytest.raises(ValueError, match="caller-minted"):
        zero.AbstractCertifiedZeroValueProofV1(
            object(),
            source.execution_window_id,
            source.coverage_report_id,
            source.original_path_gap_id,
            source.path,
            source.semantics_id,
            source.owner,
            source.scope,
            source.stage_contexts,
            source.kind,
            source.source_v1_record_id,
            source.supporting_record_ids,
            source.operation_boundary_site_ids,
        )
