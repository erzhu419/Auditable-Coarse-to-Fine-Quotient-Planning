from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp import construction_accounting_owned_runtime_v1 as runtime_v1
from acfqp import construction_accounting_partial_native_v1 as partial_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_derived_reconciliation_v1 as reconciliation_v1
from acfqp import construction_shared_resource_verified_envelope_v1 as verified_v1
from acfqp.v075_k7_root_cap_operation_boundary_manifest_v3 import (
    official_k7_root_cap_operation_boundary_manifest_v3,
)
from tests import test_construction_shared_resource_verified_envelope_v1 as verified_test


def _cid(index: int) -> str:
    return f"{index:064x}"


def _verified_nine(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> verified_v1.K7VerifiedNineSharedResourceEnvelopeV1:
    root.mkdir(parents=True, exist_ok=True)
    source = verified_test._real_envelope(root, monkeypatch)  # noqa: SLF001
    return verified_v1.verify_k7_production_shared_resource_envelope_exact_v1(
        source
    )


def _completed_root_cap_transcript(
    occurrence_id: str,
) -> partial_v1.PartialNativeOccurrenceTranscriptV1:
    registry = registry_v6.official_counter_registry_v6()
    stages = registry_v6.official_stage_profile_v6(registry)
    boundary = official_k7_root_cap_operation_boundary_manifest_v3()
    with runtime_v1.activate_owned_construction_accounting_v1(
        occurrence_id=occurrence_id,
        recorder_id="trusted-derived-reconciliation-test-recorder-v1",
        counter_registry=registry,
        stage_profile=stages,
        boundary_profile=boundary,
        _allow_low_level_test_api=True,
    ):
        for stage in partial_v1.ROOT_CAP_FIVE_STAGE_PLAN_V1:
            runtime_v1.enter_owned_stage_v1(stage)
            runtime_v1.exit_owned_stage_v1(stage)
        transcript = runtime_v1.complete_owned_occurrence_v1()
    assert transcript is not None
    partial_v1.verify_partial_native_occurrence_transcript_v1(transcript)
    return transcript


def _official_external_values() -> dict[str, int]:
    return {
        "process_reaps.exit_failures": 0,
        "process_reaps.exit_successes": 2,
        "root_stage_profile.solver_failures": 0,
        "root_stage_profile.solver_successes": 0,
        "root_terminal.route_failures": 1,
        "root_terminal.route_successes": 0,
    }


def test_eight_formulas_are_exact_v6_authorities_and_replay_arithmetic_only() -> None:
    formulas = reconciliation_v1.official_k7_reconciliation_formulas_v1()
    registry = registry_v6.official_counter_registry_v6()
    assert tuple(row.path for row in formulas) == reconciliation_v1.DERIVED_PATHS
    assert len({row.formula_id for row in formulas}) == 8
    assert all(
        registry.by_path[row.path].semantics_id == row.semantics_id
        and registry.by_path[row.path].lane.value == "derived_only"
        and registry.by_path[row.path].reducer.value == "sum"
        for row in formulas
    )
    assert {row.path: row.closure_dependency_paths for row in formulas} == {
        "process.exit_failures": ("process.launches",),
        "process.exit_successes": ("process.launches",),
        "route.attempts": ("route.failures", "route.successes"),
        "route.failures": (
            "process.exit_failures",
            "process.exit_successes",
        ),
        "route.successes": (
            "process.exit_failures",
            "process.exit_successes",
        ),
        "solver.attempts": ("solver.failures", "solver.successes"),
        "solver.failures": ("route.attempts",),
        "solver.successes": ("route.attempts",),
    }
    assert set(reconciliation_v1._topological_closure_order(formulas)) == set(  # noqa: SLF001
        reconciliation_v1.DERIVED_PATHS
    )

    replay = reconciliation_v1.evaluate_official_k7_reconciliation_arithmetic_v1(
        _official_external_values()
    )
    assert dict(replay.derived_values) == {
        "process.exit_failures": 0,
        "process.exit_successes": 2,
        "route.attempts": 1,
        "route.failures": 1,
        "route.successes": 0,
        "solver.attempts": 0,
        "solver.failures": 0,
        "solver.successes": 0,
    }
    document = replay.to_document()
    assert document["arithmetic_only"] is True
    assert document["external_values_semantically_verified"] is False
    assert document["counter_record_materialization_eligible"] is False
    assert document["counter_records_issued"] is False


@pytest.mark.parametrize(
    "mutate",
    (
        lambda values: values.pop("root_terminal.route_failures"),
        lambda values: values.update({"unknown": 0}),
        lambda values: values.update({"root_terminal.route_failures": -1}),
        lambda values: values.update({"root_terminal.route_failures": True}),
    ),
)
def test_arithmetic_replay_rejects_missing_extra_negative_and_bool_values(
    mutate,
) -> None:
    values = _official_external_values()
    mutate(values)
    with pytest.raises(
        reconciliation_v1.ConstructionK7DerivedReconciliationV1Error,
        match="missing or forged",
    ):
        reconciliation_v1.evaluate_official_k7_reconciliation_arithmetic_v1(
            values
        )


def test_formula_set_validator_rejects_missing_and_circular_graphs() -> None:
    formulas = reconciliation_v1.official_k7_reconciliation_formulas_v1()
    with pytest.raises(
        reconciliation_v1.ConstructionK7DerivedReconciliationV1Error,
        match="missing, duplicated, or forged",
    ):
        reconciliation_v1._topological_formula_order(formulas[:-1])  # noqa: SLF001

    rows = [
        SimpleNamespace(path=row.path, derived_dependencies=row.derived_dependencies)
        for row in formulas
    ]
    route_index = next(
        index for index, row in enumerate(rows) if row.path == "route.attempts"
    )
    solver_index = next(
        index for index, row in enumerate(rows) if row.path == "solver.attempts"
    )
    rows[route_index] = SimpleNamespace(
        path="route.attempts", derived_dependencies=("solver.attempts",)
    )
    rows[solver_index] = SimpleNamespace(
        path="solver.attempts", derived_dependencies=("route.attempts",)
    )
    with pytest.raises(
        reconciliation_v1.ConstructionK7DerivedReconciliationV1Error,
        match="circular",
    ):
        reconciliation_v1._topological_formula_order(tuple(rows))  # noqa: SLF001


def test_no_outer_context_retains_one_typed_all_path_blocker() -> None:
    readiness = reconciliation_v1.derive_k7_eight_path_reconciliation_v1(
        verified_nine=None
    )
    assert readiness.status is (
        reconciliation_v1.ReconciliationReadinessStatusV1.INCOMPLETE_TYPED
    )
    assert readiness.resolved_paths == ()
    assert readiness.unresolved_paths == reconciliation_v1.DERIVED_PATHS
    assert tuple(row.code for row in readiness.blockers) == (
        reconciliation_v1.ReconciliationBlockerCodeV1
        .VERIFIED_NINE_CONTEXT_NOT_AVAILABLE,
    )
    document = readiness.to_document()
    assert document["counter_record_materialization_eligible"] is False
    assert document["counter_records_issued"] is False
    assert document["formal_vector_authorized"] is False


def test_verified_process_and_exact_stage_closure_resolve_five_paths_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = _verified_nine(tmp_path, monkeypatch)
    transcript = _completed_root_cap_transcript(verified.source_envelope.occurrence_id)
    readiness = reconciliation_v1.derive_k7_eight_path_reconciliation_v1(
        verified_nine=verified,
        owner_transcript=transcript,
    )
    assert {row.path: row.value for row in readiness.proofs} == {
        "process.exit_failures": 0,
        "process.exit_successes": 2,
        "solver.attempts": 0,
        "solver.failures": 0,
        "solver.successes": 0,
    }
    assert readiness.unresolved_paths == (
        "route.attempts",
        "route.failures",
        "route.successes",
    )
    assert tuple(row.code for row in readiness.blockers) == (
        reconciliation_v1.ReconciliationBlockerCodeV1
        .ROUTE_TERMINAL_SEMANTIC_AUTHORITY_UNAVAILABLE,
    )
    document = readiness.to_document()
    assert document["all_eight_exact"] is False
    assert document["counter_record_materialization_eligible"] is False
    assert document["counter_records_issued"] is False


def test_verified_without_owner_closure_retains_solver_and_route_blockers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = _verified_nine(tmp_path, monkeypatch)
    readiness = reconciliation_v1.derive_k7_eight_path_reconciliation_v1(
        verified_nine=verified
    )
    assert {row.path: row.value for row in readiness.proofs} == {
        "process.exit_failures": 0,
        "process.exit_successes": 2,
    }
    assert {row.code for row in readiness.blockers} == {
        reconciliation_v1.ReconciliationBlockerCodeV1
        .ROOT_CAP_OWNER_STAGE_CLOSURE_NOT_AVAILABLE,
        reconciliation_v1.ReconciliationBlockerCodeV1
        .ROUTE_TERMINAL_SEMANTIC_AUTHORITY_UNAVAILABLE,
    }


def test_owner_transcript_context_transplant_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = _verified_nine(tmp_path, monkeypatch)
    transcript = _completed_root_cap_transcript(_cid(999_999))
    with pytest.raises(
        reconciliation_v1.ConstructionK7DerivedReconciliationV1Error,
        match="cannot prove solver exclusion",
    ):
        reconciliation_v1.derive_solver_stage_exclusion_dependency_v1(
            verified=verified,
            transcript=transcript,
        )


def test_status_hash_or_owned_result_shape_cannot_resolve_route_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = _verified_nine(tmp_path, monkeypatch)
    with pytest.raises(
        reconciliation_v1.ConstructionK7DerivedReconciliationV1Error,
        match="status.*not admissible",
    ):
        reconciliation_v1.derive_k7_eight_path_reconciliation_v1(
            verified_nine=verified,
            route_terminal_semantic_authority=object(),
        )


def test_process_source_mutation_and_postissuance_proof_mutation_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = _verified_nine(tmp_path / "process", monkeypatch)
    source = verified.by_path["process.launches"].bound_source.source
    lifecycle = next(
        row
        for row in source.components
        if row.component_key == "process_lifecycle_journal"
    )
    object.__setattr__(lifecycle, "raw_bytes", b"{}")
    with pytest.raises(Exception, match="mutated|transplanted|replay"):
        reconciliation_v1.derive_process_reap_dependency_v1(verified)

    verified = _verified_nine(tmp_path / "proof", monkeypatch)
    readiness = reconciliation_v1.derive_k7_eight_path_reconciliation_v1(
        verified_nine=verified
    )
    object.__setattr__(readiness.proofs[0], "value", 999)
    with pytest.raises(
        reconciliation_v1.ConstructionK7DerivedReconciliationV1Error,
        match="proof changed",
    ):
        readiness.to_document()


def test_authority_objects_are_not_caller_mintable_and_emit_no_records() -> None:
    formula = reconciliation_v1.official_k7_reconciliation_formulas_v1()[0]
    with pytest.raises(
        reconciliation_v1.ConstructionK7DerivedReconciliationV1Error,
        match="caller-minted|exact V6",
    ):
        reconciliation_v1.K7ReconciliationFormulaAuthorityV1(
            object(),
            formula.path,
            formula.semantics_id,
            formula.operation,
            formula.external_key,
            formula.derived_dependencies,
        )
    assert not any(
        "CounterRecord" in name for name in reconciliation_v1.__dict__
    )
