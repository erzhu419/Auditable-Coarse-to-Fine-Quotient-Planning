from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero
from acfqp import construction_k7_abstract_pass_production_native_accounting_v1 as inventory
from acfqp import construction_shared_resource_receipts_v1 as shared
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, content_id
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
    zero_closure = zero.close_abstract_certified_zero_value_subset_v1(execution, report)
    result = inventory.inventory_abstract_pass_retained_v1_accounting_v1(
        execution, report, zero_closure
    )
    return source, execution, report, zero_closure, result


def test_contract_is_retained_v1_inventory_not_production_native_closure(case) -> None:
    _source, execution, report, zero_closure, result = case
    document = result.to_document()
    assert result.context.operational_execution_id == execution.operational_execution_id
    assert result.context.coverage_report_id == report.report_id
    assert result.context.zero_value_closure_id == zero_closure.closure_id
    assert document["legacy_evidence_inventory_only"] is True
    assert document["production_native_accounting_closed"] is False
    assert document["formal_blocker_count"] == 202
    assert document["external_gap_partition_count"] == 192
    assert document["legacy_candidate_formal_blocker_count"] == 10
    assert document["central_domain_registration_pending"] is False


def test_seven_inventory_roles_are_central_and_domain_separated() -> None:
    assert len(inventory.LOCAL_DOMAINS) == 7
    assert inventory.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    payload = {"schema": "same-retained-v1-inventory-payload"}
    assert len({content_id(domain, payload) for domain in inventory.LOCAL_DOMAINS}) == 7


def test_context_retains_legacy_ids_but_mints_no_production_stage_cutoff_authority(
    case,
) -> None:
    _source, _execution, _report, _zero_closure, result = case
    document = result.context.to_document()
    assert document["logical_occurrence_id"]
    assert document["route_attempt_id"]
    assert document["decision_point_id"]
    assert document["production_occurrence_authority_id"] is None
    assert document["production_stage_assignment_id"] is None
    assert document["production_measurement_window_id"] is None
    assert document["production_operational_cutoff_id"] is None
    assert document["legacy_identity_values_retained_only"] is True
    assert document["production_identity_stage_cutoff_authority_complete"] is False


def test_eight_shared_values_are_legacy_aggregates_with_true_source_bytes(case) -> None:
    _source, execution, _report, _zero_closure, result = case
    rows = {row.path: row for row in result.shared_claims}
    vector = execution.recorded_work.work_vector
    expected_digest = hashlib.sha256(
        canonical_json_bytes(vector.to_dict())
    ).hexdigest()
    assert tuple(rows) == shared.SHARED_RESOURCE_PATHS
    for path in set(rows) - {"io.mounted_bytes_peak"}:
        row = rows[path]
        assert row.status is inventory.LegacyClaimStatusV1.LEGACY_AGGREGATE_NOT_VERIFIED
        assert row.reported_value == vector.value(path) > 0
        assert row.source_artifact_id == vector.work_vector_id
        assert row.source_bytes_sha256 == expected_digest
        document = row.to_document()
        assert document["measurement_window_start_observed"] is False
        assert document["complete_through_operational_cutoff"] is False
        assert document["stage_assignment_replayed"] is False
        assert document["source_semantics_verified"] is False
        assert document["numeric_projection_authorized"] is False


def test_mounted_payload_is_typed_unavailable_not_legacy_zero(case) -> None:
    _source, _execution, _report, _zero_closure, result = case
    row = next(
        item for item in result.shared_claims
        if item.path == "io.mounted_bytes_peak"
    )
    assert row.status is inventory.LegacyClaimStatusV1.NOT_AVAILABLE
    assert row.legacy_placeholder_value == 0
    assert row.reported_value is None
    assert row.source_artifact_id is None
    assert row.source_bytes_sha256 is None


def test_two_owner_rows_are_only_legacy_source_event_candidates(case) -> None:
    _source, execution, _report, _zero_closure, result = case
    rows = {row.path: row for row in result.owner_candidates}
    expected_trace_digest = hashlib.sha256(
        canonical_json_bytes(execution.native_event_trace.to_dict())
    ).hexdigest()
    assert set(rows) == {
        "common.abstract_audit_obligations",
        "common.abstract_bellman_backups",
    }
    for path, row in rows.items():
        events = tuple(
            (event.sequence, event.amount)
            for event in execution.native_event_trace.events
            if event.path == path
        )
        assert row.event_rows == events
        assert row.candidate_value == sum(amount for _sequence, amount in events) > 0
        assert row.legacy_event_trace_sha256 == expected_trace_digest
        document = row.to_document()
        assert document["production_hook_semantics_replayed"] is False
        assert document["production_stage_assignment_replayed"] is False
        assert document["production_occurrence_cutoff_replayed"] is False
        assert document["formal_owner_event_authority"] is False
        assert document["v6_counter_record_issued"] is False


def test_eight_derived_rows_are_legacy_internal_claims_not_source_closure(case) -> None:
    _source, execution, _report, _zero_closure, result = case
    rows = {row.path: row for row in result.reconciliation_claims}
    values = {path: row.claimed_value for path, row in rows.items()}
    proof = execution.recorded_work.reconciliation_proof
    expected_digest = hashlib.sha256(
        canonical_json_bytes(proof.to_dict())
    ).hexdigest()
    assert values == {
        "process.exit_failures": 0,
        "process.exit_successes": 1,
        "route.attempts": 1,
        "route.failures": 0,
        "route.successes": 1,
        "solver.attempts": 1,
        "solver.failures": 0,
        "solver.successes": 1,
    }
    assert values["route.attempts"] == values["route.failures"] + values["route.successes"]
    assert values["solver.attempts"] == values["solver.failures"] + values["solver.successes"]
    for row in rows.values():
        assert row.legacy_reconciliation_proof_id == proof.reconciliation_proof_id
        assert row.legacy_reconciliation_proof_sha256 == expected_digest
        document = row.to_document()
        assert document["legacy_internal_arithmetic_replayed"] is True
        assert document["production_semantic_dependencies_replayed"] is False
        assert document["source_level_reconciliation_complete"] is False
        assert document["formal_v6_dependency_records_complete"] is False
        assert document["formal_reconciliation_authority"] is False


def test_six_blocker_sets_are_pairwise_disjoint_and_union_official_202(case) -> None:
    _source, _execution, _report, _zero_closure, result = case
    sets = {
        code: {row.path for row in result.formal_blockers if row.code is code}
        for code in inventory.FormalBlockerCodeV1
    }
    assert {code: len(paths) for code, paths in sets.items()} == {
        inventory.FormalBlockerCodeV1.NO_V1_COUNTER_OR_EVENT: 160,
        inventory.FormalBlockerCodeV1.ZERO_VALUE_IS_NOT_PROFILE_NATIVE_ZERO: 23,
        inventory.FormalBlockerCodeV1.LEGACY_SHARED_AGGREGATE_LACKS_WINDOW_STAGE_CUTOFF_REPLAY: 8,
        inventory.FormalBlockerCodeV1.MOUNTED_PAYLOAD_NOT_MEASURED_FROM_WINDOW_START: 1,
        inventory.FormalBlockerCodeV1.LEGACY_OWNER_EVENT_LACKS_HOOK_STAGE_CUTOFF_REPLAY: 2,
        inventory.FormalBlockerCodeV1.LEGACY_INTERNAL_RECONCILIATION_LACKS_FORMAL_DEPENDENCIES: 8,
    }
    for left_index, left in enumerate(sets.values()):
        for right_index, right in enumerate(sets.values()):
            if left_index < right_index:
                assert not (left & right)
    official = set(registry_v6.official_counter_registry_v6().required_paths)
    assert set().union(*sets.values()) == official
    assert len(result.formal_blockers) == len(official) == 202


def test_192_external_partition_and_ten_legacy_candidates_are_exact(case) -> None:
    _source, _execution, _report, _zero_closure, result = case
    external_codes = {
        inventory.FormalBlockerCodeV1.NO_V1_COUNTER_OR_EVENT,
        inventory.FormalBlockerCodeV1.ZERO_VALUE_IS_NOT_PROFILE_NATIVE_ZERO,
        inventory.FormalBlockerCodeV1.LEGACY_SHARED_AGGREGATE_LACKS_WINDOW_STAGE_CUTOFF_REPLAY,
        inventory.FormalBlockerCodeV1.MOUNTED_PAYLOAD_NOT_MEASURED_FROM_WINDOW_START,
    }
    candidate_codes = {
        inventory.FormalBlockerCodeV1.LEGACY_OWNER_EVENT_LACKS_HOOK_STAGE_CUTOFF_REPLAY,
        inventory.FormalBlockerCodeV1.LEGACY_INTERNAL_RECONCILIATION_LACKS_FORMAL_DEPENDENCIES,
    }
    assert sum(row.code in external_codes for row in result.formal_blockers) == 192
    assert sum(row.code in candidate_codes for row in result.formal_blockers) == 10


def test_value_proofs_cap_terminal_vectors_and_all_gates_remain_locked(case) -> None:
    _source, _execution, _report, zero_closure, result = case
    document = result.to_document()
    assert set(result.retained_zero_value_proof_ids) == {
        row.proof_id for row in zero_closure.native_zero_proofs
    }
    assert document["retained_23_value_proofs_promoted_to_profile_native_zero"] is False
    assert document["formal_materialization_allowed"] is False
    assert document["formal_v6_counter_records_issued"] == 0
    assert document["formal_v6_work_vector_id"] is None
    assert document["formal_v6_comparison_vector_id"] is None
    assert document["cap_outcome"] is None
    assert document["cap_authority_id"] is None
    assert document["terminal_candidate_code"] == "ABSTRACT_CERTIFIED"
    assert document["terminal_artifact_id"] is None
    assert document["certificate_issued"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_n_break_even"] is None
    assert document["counter_completeness_gate_status"] == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert document["workload_economics_gate_status"] == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"


@pytest.mark.parametrize(
    "path",
    (
        "common.hash_invocations",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
        "process.launches",
    ),
)
def test_legacy_hash_io_process_claim_attacks_fail_exact_replay(case, path) -> None:
    _source, execution, report, zero_closure, result = case
    attacked = copy.deepcopy(result.to_document())
    row = next(
        item for item in attacked["legacy_shared_resource_claims"]
        if item["path"] == path
    )
    row["reported_value"] += 1
    row["legacy_shared_aggregate_claim_id"] = "0" * 64
    replay = inventory.verify_abstract_pass_retained_v1_inventory_document_v1(
        attacked, execution, report, zero_closure
    )
    assert replay.outcome is inventory.ReplayOutcomeV1.DOCUMENT_BLOCKED
    assert replay.inventory is None


def test_mounted_unavailable_to_zero_attack_fails(case) -> None:
    _source, execution, report, zero_closure, result = case
    attacked = copy.deepcopy(result.to_document())
    row = next(
        item for item in attacked["legacy_shared_resource_claims"]
        if item["path"] == "io.mounted_bytes_peak"
    )
    row["status"] = "LEGACY_AGGREGATE_NOT_VERIFIED"
    row["reported_value"] = 0
    row["source_artifact_id"] = "0" * 64
    row["source_bytes_sha256"] = "0" * 64
    replay = inventory.verify_abstract_pass_retained_v1_inventory_document_v1(
        attacked, execution, report, zero_closure
    )
    assert replay.outcome is inventory.ReplayOutcomeV1.DOCUMENT_BLOCKED


def test_blocker_partition_overlap_and_omission_attacks_fail(case) -> None:
    _source, execution, report, zero_closure, result = case
    for mutation in ("overlap", "omit"):
        attacked = copy.deepcopy(result.to_document())
        if mutation == "overlap":
            attacked["formal_blockers"][0]["path"] = attacked["formal_blockers"][1]["path"]
        else:
            attacked["formal_blockers"].pop()
        attacked["retained_v1_evidence_inventory_id"] = "0" * 64
        replay = inventory.verify_abstract_pass_retained_v1_inventory_document_v1(
            attacked, execution, report, zero_closure
        )
        assert replay.outcome is inventory.ReplayOutcomeV1.DOCUMENT_BLOCKED


@pytest.mark.parametrize(
    ("field", "forged"),
    (
        ("production_native_accounting_closed", True),
        ("source_level_derived_reconciliation_complete", True),
        ("formal_materialization_allowed", True),
        ("cap_outcome", "BUDGET_REMAINS"),
        ("terminal_artifact_id", "0" * 64),
        ("certificate_issued", True),
        ("retained_23_value_proofs_promoted_to_profile_native_zero", True),
    ),
)
def test_production_cap_terminal_and_zero_promotion_overclaims_fail(
    case, field, forged
) -> None:
    _source, execution, report, zero_closure, result = case
    attacked = copy.deepcopy(result.to_document())
    attacked[field] = forged
    attacked["retained_v1_evidence_inventory_id"] = "0" * 64
    replay = inventory.verify_abstract_pass_retained_v1_inventory_document_v1(
        attacked, execution, report, zero_closure
    )
    assert replay.outcome is inventory.ReplayOutcomeV1.DOCUMENT_BLOCKED
    assert replay.to_document()["production_native_accounting_closed"] is False
    assert replay.to_document()["formal_materialization_allowed"] is False
    assert replay.to_document()["terminal_issued"] is False


def test_independent_replay_accepts_inventory_while_formal_accounting_stays_blocked(
    case,
) -> None:
    _source, execution, report, zero_closure, result = case
    replay = inventory.verify_abstract_pass_retained_v1_inventory_document_v1(
        result.to_document(), execution, report, zero_closure
    )
    assert replay.outcome is (
        inventory.ReplayOutcomeV1.RETAINED_V1_INVENTORY_VERIFIED_FORMAL_ACCOUNTING_BLOCKED
    )
    assert replay.inventory is not None
    assert replay.inventory.inventory_id == result.inventory_id
    assert replay.to_document()["legacy_evidence_inventory_only"] is True
    assert replay.to_document()["production_native_accounting_closed"] is False


def test_inventory_replay_never_calls_planner_ground_or_root_cap_materializer(
    case, monkeypatch: pytest.MonkeyPatch
) -> None:
    _source, execution, report, zero_closure, result = case
    import acfqp.construction_k7_formal_accounting_materializer_v1 as materializer
    import acfqp.domains.g2048 as g2048
    import acfqp.phase3e_model_only_v1 as model_only
    import acfqp.phase3e_rapm_consumer_v1 as consumer

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("inventory crossed a forbidden execution boundary")

    monkeypatch.setattr(model_only, "run_phase3e_model_only_from_source_v1", forbidden)
    monkeypatch.setattr(consumer, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(g2048.G2048Kernel, "step", forbidden)
    monkeypatch.setattr(materializer, "materialize_k7_formal_accounting_v1", forbidden)
    rebuilt = inventory.inventory_abstract_pass_retained_v1_accounting_v1(
        execution, report, zero_closure
    )
    assert rebuilt.inventory_id == result.inventory_id
    assert rebuilt.to_document()["ground_access_performed"] is False
    assert rebuilt.to_document()["root_cap_materializer_invoked"] is False


def test_caller_cannot_mint_owner_or_reconciliation_candidate(case) -> None:
    _source, _execution, _report, _zero_closure, result = case
    owner = result.owner_candidates[0]
    with pytest.raises(ValueError, match="caller-minted"):
        inventory.LegacyOwnerEventCandidateV1(
            object(),
            owner.context_id,
            owner.path,
            owner.semantics_id,
            owner.owner,
            owner.scope,
            owner.legacy_v1_record_id,
            owner.legacy_event_trace_id,
            owner.legacy_event_trace_sha256,
            owner.candidate_value,
            owner.event_rows,
        )
    claim = result.reconciliation_claims[0]
    with pytest.raises(ValueError, match="caller-minted"):
        inventory.LegacyInternalReconciliationClaimV1(
            object(),
            claim.context_id,
            claim.path,
            claim.claimed_value,
            claim.formula_id,
            claim.dependency_paths,
            claim.legacy_path_record_id,
            claim.supporting_record_ids,
            claim.legacy_reconciliation_proof_id,
            claim.legacy_reconciliation_proof_sha256,
        )
