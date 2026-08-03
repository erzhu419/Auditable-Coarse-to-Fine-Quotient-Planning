from __future__ import annotations

import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage
from acfqp import construction_k7_all_path_accounting_profile_v1 as all_path
from acfqp import construction_k7_all_path_operation_boundary_manifest_v1 as boundary
from acfqp import construction_shared_resource_receipts_v1 as shared
from acfqp import construction_k7_derived_reconciliation_v2 as derived
from acfqp.phase3e_model_only_executor_v1 import (
    ModelOnlyQueryExecutionArtifactV1,
    execute_model_only_abstract_pass_v1,
    execute_model_only_query_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    LOCAL_QUERY_KEY,
    load_phase3c_model_source_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


@pytest.fixture(scope="module")
def pass_case():
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    return source, execute_model_only_abstract_pass_v1(source)


@pytest.fixture(scope="module")
def report(pass_case):
    _source, execution = pass_case
    return coverage.audit_abstract_certified_accounting_coverage_v1(execution)


def test_exact_source_bound_pass_is_blocked_at_202_path_v6_coverage(
    pass_case, report
) -> None:
    _source, execution = pass_case
    document = report.to_document()

    assert report.operational_execution_id == execution.operational_execution_id
    assert report.model_only_result_id == execution.model_only_result.result_id
    assert document["terminal_code_assessed"] == "ABSTRACT_CERTIFIED"
    assert document["production_completion_status"] == (
        "BLOCKED_INCOMPLETE_V6_SOURCE_EVIDENCE"
    )
    assert len(report.path_gaps) == 202
    counts = {
        code: sum(row.code is code for row in report.path_gaps)
        for code in coverage.PathGapCodeV1
    }
    assert counts == {
        coverage.PathGapCodeV1.NO_V1_COUNTER_LEAF_OR_EMISSION: 160,
        coverage.PathGapCodeV1.POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE: 15,
        coverage.PathGapCodeV1.ZERO_V1_RECORD_LACKS_V6_PROFILE_NATIVE_ZERO_EVIDENCE: 27,
    }
    assert document["counter_records_issued"] == 0
    assert document["work_vectors_issued"] == 0
    assert document["comparison_vectors_issued"] == 0
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


def test_report_exposes_minimum_missing_paths_and_real_selected_hook_sites(
    report,
) -> None:
    document = report.to_document()
    missing = document["minimum_missing_runtime_hook_paths"]
    upgrades = document["minimum_v6_occurrence_stage_cutoff_upgrade_paths"]
    zeros = document["minimum_v6_profile_native_zero_proof_paths"]

    assert len(missing) == 160
    assert len(upgrades) == 15
    assert len(zeros) == 27
    assert len(set(missing) | set(upgrades) | set(zeros)) == 202
    assert not (set(missing) & set(upgrades))
    assert not (set(missing) & set(zeros))
    assert not (set(upgrades) & set(zeros))
    assert {
        (row["module_name"], row["symbol_qualname"], row["call_target"])
        for row in document["existing_selected_hook_sites"]
    } >= {
        (
            "acfqp.phase3e_model_only_executor_v1",
            "execute_model_only_query_v1",
            "subprocess.run",
        ),
        (
            "acfqp.phase3e_model_only_executor_v1",
            "execute_model_only_query_v1",
            "recorder.add",
        ),
        (
            "acfqp.phase3e_abstract_pass_closure_v1",
            "close_model_only_abstract_pass_v1",
            "TerminalArtifactV1",
        ),
    }


def test_positive_legacy_records_are_retained_but_not_promoted(report) -> None:
    positive = {
        row.path: row
        for row in report.path_gaps
        if row.code
        is coverage.PathGapCodeV1.POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE
    }
    assert set(positive) == coverage._POSITIVE_V1_PATHS  # noqa: SLF001
    assert all(row.legacy_v1_record_id is not None for row in positive.values())
    assert all(row.legacy_v1_value > 0 for row in positive.values())
    assert all(row.to_document()["v6_counter_record_authorized"] is False for row in positive.values())
    assert all(row.to_document()["missing_event_inferred_zero"] is False for row in positive.values())


def test_v1_zeros_are_never_reinterpreted_as_v6_native_zero_proofs(report) -> None:
    zeros = tuple(
        row
        for row in report.path_gaps
        if row.code
        is coverage.PathGapCodeV1.ZERO_V1_RECORD_LACKS_V6_PROFILE_NATIVE_ZERO_EVIDENCE
    )
    assert len(zeros) == 27
    assert all(row.legacy_v1_record_id is not None for row in zeros)
    assert all(row.legacy_v1_value == 0 for row in zeros)
    assert {
        "local.materialization_ground_steps",
        "fallback.ground_steps",
        "rebuild.ground_steps",
        "io.mounted_bytes_peak",
        "process.exit_failures",
    } <= {row.path for row in zeros}
    assert all(row.to_document()["missing_event_inferred_zero"] is False for row in zeros)


def test_stage_contexts_preserve_required_optional_and_forbidden_semantics(report) -> None:
    gaps = {row.path: row for row in report.path_gaps}
    initial = dict(gaps["acquisition.initial_engine_ground_draws"].stage_contexts)
    local = dict(gaps["local.materialization_ground_steps"].stage_contexts)
    common = dict(gaps["common.hash_invocations"].stage_contexts)

    assert initial == {"INITIAL_ACQUISITION": "REQUIRED_ONCE"}
    assert local == {"LOCAL_ATTEMPT": "FORBIDDEN"}
    assert common["PREOPEN_COMMON_PREFIX"] == "REQUIRED_ONCE"
    assert common["OPEN_INCREMENTAL_ACQUISITION"] == "OPTIONAL_REPEATABLE"
    assert common["LOCAL_ATTEMPT"] == "FORBIDDEN"
    assert common["DIRECT_FALLBACK"] == "FORBIDDEN"
    assert common["REBUILD"] == "FORBIDDEN"


def test_all_eight_evidence_roles_fail_closed_before_terminal(report) -> None:
    statuses = {row.role: row.coverage_status for row in report.evidence_coverage}
    assert len(statuses) == 8
    assert statuses["ABSTRACT_AUDIT"] is (
        coverage.EvidenceCoverageStatusV1
        .PASS_VALUE_PRESENT_BUT_NO_PRODUCTION_TYPED_ATTESTATION
    )
    assert statuses["COUNTER_RECORD_SET"] is (
        coverage.EvidenceCoverageStatusV1.MISSING_COMPLETE_V6_COUNTER_RECORD_SET
    )
    assert statuses["WORK_VECTOR"] is (
        coverage.EvidenceCoverageStatusV1.LEGACY_V1_VECTOR_NOT_V6
    )
    assert statuses["ACTUAL_PROJECTION"] is (
        coverage.EvidenceCoverageStatusV1.LEGACY_V1_VECTOR_NOT_V6
    )
    assert statuses["TERMINAL_CLASSIFICATION"] is (
        coverage.EvidenceCoverageStatusV1.FORBIDDEN_UNTIL_V6_ACCOUNTING_CLOSES
    )
    assert statuses["OCCURRENCE_TERMINAL"] is (
        coverage.EvidenceCoverageStatusV1.FORBIDDEN_UNTIL_V6_ACCOUNTING_CLOSES
    )


def test_shared_and_derived_obligations_are_exact_not_generic(report) -> None:
    document = report.to_document()
    assert tuple(document["missing_shared_resource_paths"]) == (
        shared.SHARED_RESOURCE_PATHS
    )
    assert tuple(document["missing_derived_reconciliation_paths"]) == (
        derived.V1_BASE_PATHS + derived.ROUTE_PATHS
    )
    assert len(document["missing_shared_resource_paths"]) == 9
    assert len(document["missing_derived_reconciliation_paths"]) == 8


def test_report_binds_exact_all_path_profile_boundary_manifest_and_sources(report) -> None:
    profile = all_path.freeze_construction_k7_all_path_accounting_profile_v1()
    manifest = boundary.freeze_construction_k7_all_path_operation_boundary_manifest_v1()
    assert report.all_path_accounting_profile_id == profile.profile_id
    assert report.operation_boundary_manifest_id == manifest.manifest_id
    assert len(report.source_members) == 7
    assert all(row["source_byte_count"] > 0 for row in report.source_members)
    assert all(len(row["source_sha256"]) == 64 for row in report.source_members)


def test_independent_document_replay_accepts_exact_and_rejects_resigned_attack(
    pass_case, report
) -> None:
    _source, execution = pass_case
    exact = coverage.verify_abstract_certified_accounting_coverage_document_v1(
        report.to_document(), execution
    )
    assert exact.outcome is coverage.ReplayOutcomeV1.ACCOUNTING_BLOCKED
    assert exact.report is not None
    assert exact.report.report_id == report.report_id
    assert exact.to_document()["terminal_issued"] is False

    attacked = copy.deepcopy(report.to_document())
    attacked["path_gaps"][0]["legacy_v1_value"] = 0
    attacked["coverage_report_id"] = "0" * 64
    rejected = coverage.verify_abstract_certified_accounting_coverage_document_v1(
        attacked, execution
    )
    assert rejected.outcome is coverage.ReplayOutcomeV1.DOCUMENT_BLOCKED
    assert rejected.report is None
    assert rejected.blockers[0].code is (
        coverage.SourceBlockerCodeV1.REPORT_DOCUMENT_CHANGED
    )


def test_complete_source_byte_attack_returns_typed_source_blocker(pass_case) -> None:
    _source, execution = pass_case
    archive = coverage.load_official_abstract_certified_source_archive_v1()
    module = "acfqp.phase3e_model_only_runtime_v1"
    archive[module] += b"\n# re-signed source attack\n"
    replay = coverage.replay_abstract_certified_accounting_coverage_v1(
        execution, source_archive=archive
    )
    assert replay.outcome is coverage.ReplayOutcomeV1.SOURCE_BLOCKED
    assert replay.report is None
    assert any(
        row.module_name == module
        and row.code is coverage.SourceBlockerCodeV1.SOURCE_BYTES_CHANGED
        for row in replay.blockers
    )
    assert replay.to_document()["terminal_issued"] is False


def test_missing_source_member_is_not_inferred_from_imported_module(pass_case) -> None:
    _source, execution = pass_case
    archive = coverage.load_official_abstract_certified_source_archive_v1()
    archive.pop("acfqp.portable_planner")
    replay = coverage.replay_abstract_certified_accounting_coverage_v1(
        execution, source_archive=archive
    )
    assert replay.outcome is coverage.ReplayOutcomeV1.SOURCE_BLOCKED
    assert {row.code for row in replay.blockers} >= {
        coverage.SourceBlockerCodeV1.SOURCE_MEMBER_SET_CHANGED,
        coverage.SourceBlockerCodeV1.SOURCE_MEMBER_NOT_BYTES,
    }


def test_coverage_replay_never_calls_planner_ground_or_legacy_terminalizer(
    pass_case, monkeypatch: pytest.MonkeyPatch
) -> None:
    _source, execution = pass_case
    import acfqp.phase3e_abstract_pass_closure_v1 as closure
    import acfqp.phase3e_model_only_v1 as model_only
    import acfqp.phase3e_rapm_consumer_v1 as consumer
    import acfqp.portable_planner as portable_planner

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("coverage audit executed a forbidden semantic boundary")

    monkeypatch.setattr(closure, "close_model_only_abstract_pass_v1", forbidden)
    monkeypatch.setattr(model_only, "run_phase3e_model_only_from_source_v1", forbidden)
    monkeypatch.setattr(consumer, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(portable_planner, "solve_portable_pareto", forbidden)
    replay = coverage.replay_abstract_certified_accounting_coverage_v1(execution)
    assert replay.outcome is coverage.ReplayOutcomeV1.ACCOUNTING_BLOCKED
    assert replay.to_document()["terminal_issued"] is False


def test_failed_model_only_prefix_and_serialized_pass_copy_cannot_enter_authority(
    pass_case,
) -> None:
    source, execution = pass_case
    copied = ModelOnlyQueryExecutionArtifactV1.from_dict(
        execution.to_dict(), source=source
    )
    with pytest.raises(ValueError, match="executor-owned"):
        coverage.audit_abstract_certified_accounting_coverage_v1(copied)  # type: ignore[arg-type]

    local_source = load_phase3c_model_source_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    failed = execute_model_only_query_v1(local_source)
    with pytest.raises(ValueError, match="PASS|failed-prefix"):
        coverage.audit_abstract_certified_accounting_coverage_v1(failed)


def test_caller_cannot_mint_path_gap_or_coverage_report(report) -> None:
    source = report.path_gaps[0]
    with pytest.raises(ValueError, match="caller-minted"):
        coverage.RequiredPathCoverageGapV1(
            object(),
            source.path,
            source.semantics_id,
            source.owner,
            source.lane,
            source.scope,
            source.reducer,
            source.comparison_axis,
            source.stage_contexts,
            source.code,
            source.legacy_v1_record_id,
            source.legacy_v1_value,
        )
