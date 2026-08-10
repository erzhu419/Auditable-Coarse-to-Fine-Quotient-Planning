from __future__ import annotations

from copy import deepcopy

import pytest

from acfqp import construction_k7_terminal_accounting_coverage_matrix_v1 as coverage_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes
from acfqp.routing_v1 import TerminalCode


@pytest.fixture(scope="module")
def matrix():
    return coverage_v1.freeze_k7_terminal_accounting_coverage_matrix_v1()


def test_coverage_domains_are_unique_and_central() -> None:
    assert len(coverage_v1.LOCAL_DOMAINS) == 4
    assert coverage_v1.LOCAL_DOMAINS.issubset(PHASE3E_DOMAIN_TAGS)


def test_matrix_assesses_every_terminal_code_exactly_once(matrix) -> None:
    document = matrix.to_document()
    assert [row["terminal_code"] for row in document["rows"]] == [
        code.value for code in TerminalCode
    ]
    assert document["terminal_code_count"] == 10
    assert document["source_member_count"] == 13
    assert document["formal_202_path_implementation_count"] == 3
    assert document["production_site_formal_implementation_count"] == 2
    assert document["registered_fixture_formal_implementation_only_count"] == 1
    assert document["partial_or_readiness_only_count"] == 2
    assert document["missing_terminal_specific_formal_implementation_count"] == 5
    assert document["all_terminal_codes_assessed_exactly_once"] is True


def test_matrix_keeps_capability_and_observed_campaign_evidence_separate(matrix) -> None:
    rows = {row.terminal_code: row for row in matrix.rows}
    abstract = rows[TerminalCode.ABSTRACT_CERTIFIED].to_document()
    integrity = rows[TerminalCode.INTEGRITY_FAILURE].to_document()
    protocol = rows[TerminalCode.PROTOCOL_FAILURE].to_document()
    attempt = rows[TerminalCode.ATTEMPT_BUDGET_EXHAUSTED].to_document()
    exact_infeasible = rows[TerminalCode.FULL_GROUND_EXACT_INFEASIBLE].to_document()

    assert abstract["closed_required_path_count"] == 41
    assert abstract["open_required_path_count"] == 161
    assert abstract["blocker_code"] == (
        "ABSTRACT_CERTIFIED_REQUIRES_161_ADDITIONAL_V6_PATH_AUTHORITIES"
    )
    assert abstract["complete_202_counter_record_to_work_vector_to_comparison_vector_present"] is False
    assert exact_infeasible["closed_required_path_count"] == 0
    assert exact_infeasible["blocker_code"] == (
        "LEGACY_42_ROW_VECTOR_IS_NOT_A_202_ROW_V6_CHAIN"
    )
    assert integrity["production_site_implementation_present"] is True
    assert attempt["production_site_implementation_present"] is True
    assert protocol["complete_202_counter_record_to_work_vector_to_comparison_vector_present"] is True
    assert protocol["production_site_implementation_present"] is False
    assert protocol["blocker_code"] == "PRODUCTION_PROTOCOL_SITE_AUTHORITY_NOT_BOUND"
    assert all(
        row.to_document()["observed_campaign_occurrence_bound_by_this_matrix"] is False
        for row in matrix.rows
    )


def test_matrix_replays_exact_current_sources(matrix) -> None:
    replay = coverage_v1.verify_k7_terminal_accounting_coverage_matrix_bytes_v1(
        matrix.canonical_bytes
    )
    assert replay.matrix_id == matrix.matrix_id
    assert replay.to_document()["exact_current_source_replay_passed"] is True
    assert replay.to_document()["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )


@pytest.mark.parametrize(
    ("location", "key", "value"),
    (
        (("rows", 0), "closed_required_path_count", 202),
        (("rows", 5), "production_site_implementation_present", False),
        (("rows", 6), "blocker_code", None),
        ((), "all_path_native_accounting_complete", True),
    ),
)
def test_resigned_semantic_changes_are_rejected(matrix, location, key, value) -> None:
    document = deepcopy(matrix.to_document())
    target = document
    for item in location:
        target = target[item]
    target[key] = value
    with pytest.raises(
        coverage_v1.ConstructionK7TerminalAccountingCoverageMatrixV1Error
    ):
        coverage_v1.verify_k7_terminal_accounting_coverage_matrix_bytes_v1(
            canonical_json_bytes(document)
        )


def test_caller_cannot_mint_coverage_rows(matrix) -> None:
    row = matrix.rows[0]
    with pytest.raises(
        coverage_v1.ConstructionK7TerminalAccountingCoverageMatrixV1Error,
        match="caller-minted",
    ):
        coverage_v1.K7TerminalAccountingCoverageRowV1(
            object(),
            row.terminal_code,
            row.terminal_class,
            row.state,
            row.evidence_source_id,
            row.evidence_module,
            row.closed_required_path_count,
            row.complete_formal_chain_present,
            row.terminal_specific_verifier_present,
            row.production_site_implementation_present,
            row.blocker_code,
        )


def test_all_official_gates_remain_locked(matrix) -> None:
    document = matrix.to_document()
    assert document["all_path_native_accounting_complete"] is False
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert document["workload_economics_gate_status"] == (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
