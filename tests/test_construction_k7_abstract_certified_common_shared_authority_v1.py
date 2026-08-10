from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage
from acfqp import construction_k7_abstract_certified_common_shared_authority_v1 as common
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
    lifecycle_envelope = (
        lifecycle.issue_abstract_certified_lifecycle_reconciliation_authority_v1(
            source,
            execution,
            report,
            zero_closure,
            retained,
            query_owner,
        )
    )
    envelope = common.issue_abstract_certified_common_shared_authority_v1(
        source,
        execution,
        report,
        zero_closure,
        retained,
        query_owner,
        lifecycle_envelope,
    )
    return (
        source,
        execution,
        report,
        zero_closure,
        retained,
        query_owner,
        lifecycle_envelope,
        envelope,
    )


def test_four_common_shared_domains_are_central_and_separated() -> None:
    assert len(common.LOCAL_DOMAINS) == 4
    assert common.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    payload = {"schema": "same-abstract-common-shared-payload"}
    assert len({content_id(domain, payload) for domain in common.LOCAL_DOMAINS}) == 4


def test_two_exact_common_shared_records_are_formal_v6_records(case) -> None:
    registry = registry_v6.official_counter_registry_v6()
    envelope = case[-1]
    assert [(row.path, row.value) for row in envelope.counter_records] == [
        ("common.integrity_checks", 12),
        ("common.protocol_checks", 7),
    ]
    for resolution, record in zip(
        envelope.resolutions, envelope.counter_records, strict=True
    ):
        assert record.recorder_id == resolution.resolution_id
        assert record.counter_registry_id == registry.registry_id
        assert record.observed is True
        assert CounterRecordV1.from_dict(record.to_dict()) == record
        record.verify_against(registry.by_path[record.path])


def test_runtime_trace_and_direct_supervisor_sites_are_both_bound(case) -> None:
    document = case[-1].window.to_document()
    assert document["runtime_trace_rows"] == [
        {"sequence": 1, "path": "common.protocol_checks", "amount": 1},
        {"sequence": 2, "path": "common.hash_invocations", "amount": 1},
        {"sequence": 3, "path": "common.hash_invocations", "amount": 2},
        {"sequence": 4, "path": "common.integrity_checks", "amount": 5},
        {"sequence": 96, "path": "common.integrity_checks", "amount": 1},
        {"sequence": 97, "path": "common.protocol_checks", "amount": 1},
        {"sequence": 98, "path": "common.hash_invocations", "amount": 1},
    ]
    assert len(document["source_site_rows"]) == 10
    assert sum(
        row["amount"]
        for row in document["source_site_rows"]
        if row["module_name"] == common.EXECUTOR_MODULE
    ) == 13
    assert document["complete_runtime_trace_bound"] is True
    assert document["direct_literal_supervisor_sites_bound"] is True
    assert document["measurement_window_start_observed"] is True
    assert document["complete_through_operational_cutoff"] is True
    assert document["stage_assignment_replayed"] is True
    assert document["selected_hash_event_value"] == 6
    assert document["global_content_id_hash_meter_present"] is False
    assert document["hash_counter_record_issued"] is False
    assert document["hash_blocker_code"] == (
        "CONTENT_ID_HASH_INVOCATIONS_NOT_GLOBALLY_HOOKED"
    )


def test_stage_splits_sum_to_exact_path_values(case) -> None:
    resolutions = {row.path: row for row in case[-1].resolutions}
    assert "common.hash_invocations" not in resolutions
    assert resolutions["common.integrity_checks"].stage_values == (
        ("PREOPEN_COMMON_PREFIX", 5),
        ("CLOSED_RECONCILIATION_AND_TERMINALIZATION", 7),
    )
    assert resolutions["common.protocol_checks"].stage_values == (
        ("PREOPEN_COMMON_PREFIX", 1),
        ("CLOSED_RECONCILIATION_AND_TERMINALIZATION", 6),
    )
    for row in resolutions.values():
        assert row.value == row.runtime_value + row.supervisor_value
        assert row.value == sum(value for _stage, value in row.stage_values)


def test_each_resolution_replaces_only_its_exact_shared_claim_blocker(case) -> None:
    retained, envelope = case[4], case[-1]
    claims = {row.path: row for row in retained.shared_claims}
    blockers = {row.path: row for row in retained.formal_blockers}
    for row in envelope.resolutions:
        assert row.predecessor_claim_id == claims[row.path].claim_id
        assert row.predecessor_blocker_id == blockers[row.path].blocker_id
        document = row.to_document()
        assert document["source_v1_record_relabelled_as_v6"] is False
        assert document["runtime_events_replayed"] is True
        assert document["supervisor_source_sites_replayed"] is True


def test_progress_is_exactly_36_of_202_without_partial_vector_claim(case) -> None:
    document = case[-1].to_document()
    assert document["retained_prior_completion_progress_count"] == 34
    assert document["new_formal_v6_counter_record_count"] == 2
    assert document["combined_completion_progress_count"] == 36
    assert document["remaining_required_path_authority_count"] == 166
    assert document["shared_resource_path_count_closed_here"] == 2
    assert document["remaining_shared_resource_path_count"] == 6
    assert document["all_nine_shared_resource_receipts_complete"] is False
    assert document["all_eight_derived_reconciliations_complete"] is True
    assert document["complete_202_counter_record_chain_present"] is False
    assert document["formal_v6_work_vector_id"] is None
    assert document["formal_v6_comparison_vector_id"] is None
    assert document["terminal_artifact_id"] is None
    assert document["campaign_occurrence_closure_id"] is None
    assert document["certificate_issued"] is False
    assert document["common_hash_invocations_counter_record_id"] is None
    assert document["common_hash_invocations_blocker_code"] == (
        "CONTENT_ID_HASH_INVOCATIONS_NOT_GLOBALLY_HOOKED"
    )


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


def test_portable_replay_rebuilds_exact_two_record_authority(case) -> None:
    source, execution, report, zeros, retained, owner_envelope, life, envelope = case
    replay = common.verify_abstract_certified_common_shared_authority_bytes_v1(
        envelope.canonical_bytes,
        source,
        execution,
        report,
        zeros,
        retained,
        owner_envelope,
        life,
    )
    assert replay.outcome is common.CommonSharedReplayOutcomeV1.VERIFIED
    assert replay.envelope is not None
    assert replay.envelope.envelope_id == envelope.envelope_id
    assert replay.blocker_codes == ()


@pytest.mark.parametrize(
    ("location", "key", "value"),
    (
        (("window", "runtime_trace_rows", 0), "amount", 2),
        (("window", "source_site_rows", 0), "stage_kind", "FAILED_ABSTRACT_PREFIX"),
        (("resolutions", 0), "value", 7),
        (("formal_v6_counter_records", 1), "value", 13),
        ((), "all_nine_shared_resource_receipts_complete", True),
    ),
)
def test_resigned_trace_site_value_and_claim_mutations_are_blocked(
    case, location, key, value
) -> None:
    source, execution, report, zeros, retained, owner_envelope, life, envelope = case
    document = deepcopy(envelope.to_document())
    target = document
    for item in location:
        target = target[item]
    target[key] = value
    payload = dict(document)
    payload.pop("abstract_common_shared_envelope_id")
    document["abstract_common_shared_envelope_id"] = content_id(
        common.ENVELOPE_DOMAIN, payload
    )
    replay = common.verify_abstract_certified_common_shared_authority_bytes_v1(
        canonical_json_bytes(document),
        source,
        execution,
        report,
        zeros,
        retained,
        owner_envelope,
        life,
    )
    assert replay.outcome is common.CommonSharedReplayOutcomeV1.DOCUMENT_BLOCKED
    assert replay.envelope is None


def test_caller_cannot_mint_common_shared_artifacts(case) -> None:
    with pytest.raises(
        common.ConstructionK7AbstractCertifiedCommonSharedAuthorityV1Error,
        match="caller-minted",
    ):
        replace(case[-1].window, _issuer=object())


def test_crossed_lifecycle_root_is_rejected(case) -> None:
    source, execution, report, zeros, retained, owner_envelope, life, _envelope = case
    crossed = deepcopy(life)
    object.__setattr__(crossed, "_envelope_id", "f" * 64)
    with pytest.raises(Exception):
        common.issue_abstract_certified_common_shared_authority_v1(
            source,
            execution,
            report,
            zeros,
            retained,
            owner_envelope,
            crossed,
        )


def test_replay_does_not_reexecute_planner_or_load_ground_source(
    case, monkeypatch
) -> None:
    source, execution, report, zeros, retained, owner_envelope, life, envelope = case

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
    replay = common.verify_abstract_certified_common_shared_authority_bytes_v1(
        envelope.canonical_bytes,
        source,
        execution,
        report,
        zeros,
        retained,
        owner_envelope,
        life,
    )
    assert replay.outcome is common.CommonSharedReplayOutcomeV1.VERIFIED
    assert replay.to_document()["planner_reexecution_performed"] is False
    assert replay.to_document()["ground_access_performed"] is False
