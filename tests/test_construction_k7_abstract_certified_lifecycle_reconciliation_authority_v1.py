from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage
from acfqp import construction_k7_abstract_certified_lifecycle_reconciliation_authority_v1 as lifecycle
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero
from acfqp import construction_k7_abstract_certified_query_owner_authority_v1 as owner
from acfqp import construction_k7_abstract_pass_production_native_accounting_v1 as inventory
from acfqp.accounting_v1 import CounterRecordV1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, content_id
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
    zero_closure = zero.close_abstract_certified_zero_value_subset_v1(
        execution, report
    )
    retained = inventory.inventory_abstract_pass_retained_v1_accounting_v1(
        execution, report, zero_closure
    )
    query_owner = owner.issue_abstract_certified_query_owner_authority_v1(
        execution, report, zero_closure, retained
    )
    envelope = lifecycle.issue_abstract_certified_lifecycle_reconciliation_authority_v1(
        source,
        execution,
        report,
        zero_closure,
        retained,
        query_owner,
    )
    return (
        source,
        execution,
        report,
        zero_closure,
        retained,
        query_owner,
        envelope,
    )


def test_four_lifecycle_domains_are_central_and_separated() -> None:
    assert len(lifecycle.LOCAL_DOMAINS) == 4
    assert lifecycle.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    payload = {"schema": "same-abstract-lifecycle-payload"}
    assert len({content_id(domain, payload) for domain in lifecycle.LOCAL_DOMAINS}) == 4


def test_nine_formal_records_close_process_route_and_solver_reconciliation(case) -> None:
    envelope = case[-1]
    registry = registry_v6.official_counter_registry_v6()
    assert [(row.path, row.value) for row in envelope.counter_records] == [
        ("process.launches", 1),
        ("process.exit_failures", 0),
        ("process.exit_successes", 1),
        ("route.attempts", 1),
        ("route.failures", 0),
        ("route.successes", 1),
        ("solver.attempts", 0),
        ("solver.failures", 0),
        ("solver.successes", 0),
    ]
    for resolution, record in zip(
        envelope.resolutions, envelope.counter_records, strict=True
    ):
        assert record.recorder_id == resolution.resolution_id
        assert record.counter_registry_id == registry.registry_id
        assert record.observed is True
        assert CounterRecordV1.from_dict(record.to_dict()) == record
        record.verify_against(registry.by_path[record.path])


def test_legacy_solver_ones_are_rejected_as_v6_profile_native_zeros(case) -> None:
    envelope = case[-1]
    resolutions = {row.path: row for row in envelope.resolutions}
    for path in ("solver.attempts", "solver.successes"):
        row = resolutions[path]
        assert row.legacy_value == 1
        assert row.formal_value == 0
        assert row.kind is (
            lifecycle.LifecycleResolutionKindV1
            .PROFILE_NATIVE_ZERO_MATERIALIZATION
        )
        assert row.stage_kinds == lifecycle.FORBIDDEN_SOLVER_STAGES
        document = row.to_document()
        assert document["legacy_solver_value_rejected"] is True
        assert document["profile_native_zero_issued"] is True
        assert document["source_v1_record_relabelled_as_v6"] is False
    solver_failure = resolutions["solver.failures"]
    assert solver_failure.legacy_value == solver_failure.formal_value == 0
    assert solver_failure.to_document()["legacy_solver_value_rejected"] is False
    assert solver_failure.to_document()["profile_native_zero_issued"] is True


def test_exact_dependency_dag_binds_successes_totals_and_failure_zeros(case) -> None:
    zero_closure, envelope = case[3], case[-1]
    resolutions = {row.path: row for row in envelope.resolutions}
    zero_proofs = {
        row.path: row.proof_id
        for row in zero_closure.derived_complement_value_proofs
    }
    assert set(resolutions["process.exit_failures"].supporting_proof_ids) == {
        resolutions["process.launches"].resolution_id,
        zero_proofs["process.exit_failures"],
    }
    assert set(resolutions["process.exit_successes"].supporting_proof_ids) == {
        resolutions["process.launches"].resolution_id,
        resolutions["process.exit_failures"].resolution_id,
    }
    assert set(resolutions["route.failures"].supporting_proof_ids) == {
        resolutions["process.exit_failures"].resolution_id,
        resolutions["process.exit_successes"].resolution_id,
        zero_proofs["route.failures"],
    }
    assert set(resolutions["route.attempts"].supporting_proof_ids) == {
        resolutions["route.failures"].resolution_id,
        resolutions["route.successes"].resolution_id,
    }
    assert set(resolutions["solver.attempts"].supporting_proof_ids) == {
        resolutions["solver.failures"].resolution_id,
        resolutions["solver.successes"].resolution_id,
    }
    assert resolutions["route.attempts"].resolution_id in set(
        resolutions["solver.successes"].supporting_proof_ids
    )
    assert {
        resolutions["route.attempts"].resolution_id,
        zero_proofs["solver.failures"],
    } <= set(resolutions["solver.failures"].supporting_proof_ids)


def test_source_window_binds_exact_fresh_process_and_abstract_terminal(case) -> None:
    source, execution, _report, _zeros, retained, query_owner, envelope = case
    document = envelope.window.to_document()
    assert document["source_lease_id"] == source.lease.source_lease_id
    assert document["operational_execution_id"] == execution.operational_execution_id
    assert document["retained_v1_inventory_id"] == retained.inventory_id
    assert document["query_owner_envelope_id"] == query_owner.envelope_id
    assert document["fresh_worker_launch_count"] == 1
    assert document["successful_worker_exit_count"] == 1
    assert document["abstract_only_route_attempt_count"] == 1
    assert document["abstract_only_route_success_count"] == 1
    assert document["local_or_fallback_solver_attempt_count"] == 0
    assert document["fresh_process_returncode_zero_bound"] is True
    assert document["abstract_route_pass_terminal_bound"] is True
    assert document["ground_access_performed"] is False


def test_progress_is_exactly_34_of_202_without_vector_or_terminal_claim(case) -> None:
    document = case[-1].to_document()
    assert document["retained_prior_completion_progress_count"] == 28
    assert document["new_formal_v6_counter_record_count"] == 9
    assert document["newly_closed_path_authority_count"] == 6
    assert document["combined_completion_progress_count"] == 34
    assert document["remaining_required_path_authority_count"] == 168
    assert document["shared_resource_path_count_closed_here"] == 1
    assert document["derived_reconciliation_path_count_closed_here"] == 5
    assert document["derived_reconciliation_formal_record_count_materialized_here"] == 8
    assert document["prior_zero_proof_materialization_count"] == 3
    assert document["remaining_shared_resource_path_count"] == 8
    assert document["remaining_derived_reconciliation_path_count"] == 0
    assert document["all_eight_derived_reconciliations_complete"] is True
    assert document["all_nine_shared_resource_receipts_complete"] is False
    assert document["complete_202_counter_record_chain_present"] is False
    assert document["formal_v6_work_vector_id"] is None
    assert document["formal_v6_comparison_vector_id"] is None
    assert document["terminal_artifact_id"] is None
    assert document["campaign_occurrence_closure_id"] is None
    assert document["certificate_issued"] is False


def test_all_official_gates_remain_locked(case) -> None:
    document = case[-1].to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_n_break_even"] is None
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert document["workload_economics_gate_status"] == (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )


def test_portable_replay_rebuilds_exact_nine_record_authority(case) -> None:
    source, execution, report, zero_closure, retained, query_owner, envelope = case
    replay = lifecycle.verify_abstract_certified_lifecycle_reconciliation_bytes_v1(
        envelope.canonical_bytes,
        source,
        execution,
        report,
        zero_closure,
        retained,
        query_owner,
    )
    assert replay.outcome is lifecycle.LifecycleReplayOutcomeV1.VERIFIED
    assert replay.envelope is not None
    assert replay.envelope.envelope_id == envelope.envelope_id
    assert replay.blocker_codes == ()


@pytest.mark.parametrize(
    ("location", "key", "value"),
    (
        (("window", "legacy_lifecycle_values", 6), "value", 0),
        (("resolutions", 4), "formal_value", 1),
        (("formal_v6_counter_records", 8), "value", 1),
        ((), "all_nine_shared_resource_receipts_complete", True),
    ),
)
def test_resigned_legacy_stage_value_and_claim_mutations_are_blocked(
    case, location, key, value
) -> None:
    source, execution, report, zero_closure, retained, query_owner, envelope = case
    document = deepcopy(envelope.to_document())
    target = document
    for item in location:
        target = target[item]
    target[key] = value
    payload = dict(document)
    payload.pop("abstract_lifecycle_envelope_id")
    document["abstract_lifecycle_envelope_id"] = content_id(
        lifecycle.ENVELOPE_DOMAIN, payload
    )
    replay = lifecycle.verify_abstract_certified_lifecycle_reconciliation_bytes_v1(
        canonical_json_bytes(document),
        source,
        execution,
        report,
        zero_closure,
        retained,
        query_owner,
    )
    assert replay.outcome is lifecycle.LifecycleReplayOutcomeV1.DOCUMENT_BLOCKED
    assert replay.envelope is None


def test_caller_cannot_mint_lifecycle_artifacts(case) -> None:
    with pytest.raises(
        lifecycle.ConstructionK7AbstractCertifiedLifecycleAuthorityV1Error,
        match="caller-minted",
    ):
        replace(case[-1].window, _issuer=object())


def test_crossed_coverage_root_is_rejected(case) -> None:
    source, execution, report, zero_closure, retained, query_owner, _envelope = case
    crossed = deepcopy(report)
    object.__setattr__(crossed, "operational_execution_id", "f" * 64)
    with pytest.raises(Exception):
        lifecycle.issue_abstract_certified_lifecycle_reconciliation_authority_v1(
            source,
            execution,
            crossed,
            zero_closure,
            retained,
            query_owner,
        )


def test_replay_does_not_reexecute_planner_or_load_ground_source(
    case, monkeypatch
) -> None:
    source, execution, report, zero_closure, retained, query_owner, envelope = case

    def forbidden(*_args, **_kwargs):
        raise AssertionError("planner/source execution is forbidden during replay")

    monkeypatch.setattr(
        "acfqp.phase3e_model_only_executor_v1.execute_model_only_abstract_pass_v1",
        forbidden,
    )
    monkeypatch.setattr(
        "acfqp.phase3e_rapm_consumer_v1.load_phase3c_model_source_v1",
        forbidden,
    )
    replay = lifecycle.verify_abstract_certified_lifecycle_reconciliation_bytes_v1(
        envelope.canonical_bytes,
        source,
        execution,
        report,
        zero_closure,
        retained,
        query_owner,
    )
    assert replay.outcome is lifecycle.LifecycleReplayOutcomeV1.VERIFIED
    assert replay.to_document()["planner_reexecution_performed"] is False
    assert replay.to_document()["ground_access_performed"] is False
