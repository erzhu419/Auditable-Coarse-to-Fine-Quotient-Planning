from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage
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
    envelope = owner.issue_abstract_certified_query_owner_authority_v1(
        execution, report, zero_closure, retained
    )
    return source, execution, report, zero_closure, retained, envelope


def test_four_query_owner_domains_are_central_and_separated() -> None:
    assert len(owner.LOCAL_DOMAINS) == 4
    assert owner.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    payload = {"schema": "same-query-owner-payload"}
    assert len({content_id(domain, payload) for domain in owner.LOCAL_DOMAINS}) == 4


def test_exact_trace_window_and_cutoffs_are_bound(case) -> None:
    _source, execution, report, zero_closure, retained, envelope = case
    window = envelope.window
    document = window.to_document()
    assert window.retained_v1_inventory_id == retained.inventory_id
    assert window.coverage_report_id == report.report_id
    assert window.zero_value_closure_id == zero_closure.closure_id
    assert window.operational_execution_id == execution.operational_execution_id
    assert window.event_trace_id == execution.native_event_trace.event_trace_id
    assert len(window.ordered_event_rows) == 98
    assert (
        window.prefix_end_sequence,
        window.owner_start_sequence,
        window.owner_end_sequence,
        window.suffix_start_sequence,
    ) == (4, 5, 95, 96)
    assert document["complete_trace_window_bound"] is True
    assert document["stage_assignment_bound"] is True
    assert document["operational_cutoff_bound"] is True
    assert document["prefix_contains_owner_event"] is False
    assert document["owner_window_contains_nonowner_event"] is False
    assert document["suffix_contains_owner_event"] is False


def test_two_formal_v6_records_replace_only_the_owner_blockers(case) -> None:
    _source, _execution, _report, _zero_closure, retained, envelope = case
    registry = registry_v6.official_counter_registry_v6()
    candidates = {row.path: row for row in retained.owner_candidates}
    blockers = {
        row.path: row
        for row in retained.formal_blockers
        if row.code
        is inventory.FormalBlockerCodeV1
        .LEGACY_OWNER_EVENT_LACKS_HOOK_STAGE_CUTOFF_REPLAY
    }
    assert [(row.path, row.value) for row in envelope.counter_records] == [
        ("common.abstract_audit_obligations", 70),
        ("common.abstract_bellman_backups", 25),
    ]
    for resolution, record in zip(
        envelope.resolutions, envelope.counter_records, strict=True
    ):
        assert resolution.predecessor_blocker_id == blockers[resolution.path].blocker_id
        assert resolution.legacy_candidate_id == candidates[resolution.path].candidate_id
        assert record.recorder_id == resolution.resolution_id
        assert record.counter_registry_id == registry.registry_id
        assert CounterRecordV1.from_dict(record.to_dict()) == record
        record.verify_against(registry.by_path[record.path])


def test_progress_is_exactly_28_of_202_without_partial_vector_claim(case) -> None:
    document = case[-1].to_document()
    assert document["retained_prior_completion_progress_count"] == 26
    assert document["new_formal_v6_counter_record_count"] == 2
    assert document["combined_completion_progress_count"] == 28
    assert document["remaining_required_path_authority_count"] == 174
    assert document["complete_202_counter_record_chain_present"] is False
    assert document["formal_v6_work_vector_id"] is None
    assert document["formal_v6_comparison_vector_id"] is None
    assert document["terminal_artifact_id"] is None
    assert document["campaign_occurrence_closure_id"] is None
    assert document["certificate_issued"] is False


def test_all_official_gates_remain_locked(case) -> None:
    document = case[-1].to_document()
    assert document["all_nine_shared_resource_receipts_complete"] is False
    assert document["all_eight_derived_reconciliations_complete"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_n_break_even"] is None
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert document["workload_economics_gate_status"] == (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )


def test_portable_replay_rebuilds_exact_two_record_authority(case) -> None:
    _source, execution, report, zero_closure, retained, envelope = case
    replay = owner.verify_abstract_certified_query_owner_authority_bytes_v1(
        envelope.canonical_bytes,
        execution,
        report,
        zero_closure,
        retained,
    )
    assert replay.outcome is owner.QueryOwnerReplayOutcomeV1.VERIFIED
    assert replay.envelope is not None
    assert replay.envelope.envelope_id == envelope.envelope_id
    assert replay.blocker_codes == ()


@pytest.mark.parametrize(
    ("location", "key", "value"),
    (
        (("window",), "owner_start_sequence", 6),
        (("resolutions", 0), "stage_kind", "INITIAL_MODEL_BUILD"),
        (("formal_v6_counter_records", 0), "value", 71),
        ((), "complete_202_counter_record_chain_present", True),
    ),
)
def test_resigned_window_stage_value_and_claim_mutations_are_blocked(
    case, location, key, value
) -> None:
    _source, execution, report, zero_closure, retained, envelope = case
    document = deepcopy(envelope.to_document())
    target = document
    for item in location:
        target = target[item]
    target[key] = value
    payload = dict(document)
    payload.pop("query_owner_envelope_id")
    document["query_owner_envelope_id"] = content_id(owner.ENVELOPE_DOMAIN, payload)
    replay = owner.verify_abstract_certified_query_owner_authority_bytes_v1(
        canonical_json_bytes(document),
        execution,
        report,
        zero_closure,
        retained,
    )
    assert replay.outcome is owner.QueryOwnerReplayOutcomeV1.DOCUMENT_BLOCKED
    assert replay.envelope is None


def test_caller_cannot_mint_query_owner_artifacts(case) -> None:
    window = case[-1].window
    with pytest.raises(
        owner.ConstructionK7AbstractCertifiedQueryOwnerAuthorityV1Error,
        match="caller-minted",
    ):
        replace(window, _issuer=object())


def test_crossed_retained_root_is_rejected(case) -> None:
    _source, execution, report, zero_closure, retained, _envelope = case
    crossed = deepcopy(report)
    object.__setattr__(crossed, "operational_execution_id", "f" * 64)
    with pytest.raises(Exception):
        owner.issue_abstract_certified_query_owner_authority_v1(
            execution, crossed, zero_closure, retained
        )


def test_replay_does_not_reexecute_planner_or_load_ground_source(case, monkeypatch) -> None:
    _source, execution, report, zero_closure, retained, envelope = case

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
    replay = owner.verify_abstract_certified_query_owner_authority_bytes_v1(
        envelope.canonical_bytes,
        execution,
        report,
        zero_closure,
        retained,
    )
    assert replay.outcome is owner.QueryOwnerReplayOutcomeV1.VERIFIED
    assert replay.to_document()["planner_reexecution_performed"] is False
    assert replay.to_document()["ground_access_performed"] is False
