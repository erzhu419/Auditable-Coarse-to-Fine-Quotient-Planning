from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_accounted_shared_authority_v2 as shared
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage
from acfqp import construction_k7_abstract_certified_lifecycle_reconciliation_authority_v1 as lifecycle
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero
from acfqp import construction_k7_abstract_certified_query_owner_authority_v1 as owner
from acfqp import construction_k7_abstract_pass_production_native_accounting_v1 as retained
from acfqp import construction_k7_abstract_query_native_zero_authority_v1 as authority
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, content_id
from acfqp.phase3e_model_only_accounted_executor_v2 import (
    ACCOUNTED_RUNTIME_SOURCE_PATHS,
    execute_model_only_accounted_query_v2,
    prepare_model_only_accounted_runtime_v2,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    load_phase3c_model_source_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    preparation = prepare_model_only_accounted_runtime_v2(
        source_root=ROOT / "src",
        runtime_cas_root=tmp_path_factory.mktemp("abstract-query-zero-cas"),
    )
    source = load_phase3c_model_source_v1(
        PHASE3C, query_key=ABSTRACT_QUERY_KEY
    )
    accounted = execute_model_only_accounted_query_v2(source, preparation)
    execution = accounted.execution
    report = coverage.audit_abstract_certified_accounting_coverage_v1(execution)
    zeros = zero.close_abstract_certified_zero_value_subset_v1(execution, report)
    inventory = retained.inventory_abstract_pass_retained_v1_accounting_v1(
        execution, report, zeros
    )
    query_owner = owner.issue_abstract_certified_query_owner_authority_v1(
        execution, report, zeros, inventory
    )
    lifecycle_envelope = (
        lifecycle.issue_abstract_certified_lifecycle_reconciliation_authority_v1(
            source, execution, report, zeros, inventory, query_owner
        )
    )
    shared_envelope = shared.issue_abstract_accounted_shared_authority_v2(
        source,
        accounted,
        report,
        zeros,
        inventory,
        query_owner,
        lifecycle_envelope,
    )
    envelope = authority.issue_abstract_query_native_zero_authority_v1(
        source,
        accounted,
        report,
        zeros,
        inventory,
        query_owner,
        lifecycle_envelope,
        shared_envelope,
    )
    return (
        source,
        accounted,
        report,
        zeros,
        inventory,
        query_owner,
        lifecycle_envelope,
        shared_envelope,
        envelope,
    )


def test_four_domains_are_central_and_role_separated() -> None:
    assert len(authority.LOCAL_DOMAINS) == 4
    assert authority.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    payload = {"schema": "same-abstract-query-zero-payload"}
    assert len(
        {content_id(domain, payload) for domain in authority.LOCAL_DOMAINS}
    ) == 4


def test_private_runtime_excludes_all_optional_construction_sources(case) -> None:
    window = case[-1].runtime_window
    assert tuple(row.relative_path for row in window.runtime_sources) == (
        ACCOUNTED_RUNTIME_SOURCE_PATHS
    )
    assert len(window.runtime_sources) == authority.EXPECTED_RUNTIME_SOURCE_COUNT
    assert all(row.operation_gateway_call_count == 0 for row in window.runtime_sources)
    assert window.runtime_counter_allowlist == (
        authority.MODEL_ONLY_RUNTIME_COUNTER_ALLOWLIST
    )
    assert len(window.excluded_operation_modules) == 10
    runtime_modules = {
        path[:-3].replace("/", ".") for path in ACCOUNTED_RUNTIME_SOURCE_PATHS
    }
    assert not runtime_modules.intersection(window.excluded_operation_modules)
    document = window.to_document()
    assert document["python_isolated_flag_required"] is True
    assert document["private_regular_package_runtime_required"] is True
    assert document["missing_event_used_as_zero_evidence"] is False


def test_exact_23_plus_60_zero_records_are_observed_v6_records(case) -> None:
    envelope = case[-1]
    registry = registry_v6.official_counter_registry_v6()
    assert len(envelope.resolutions) == len(envelope.counter_records) == 83
    assert sum(row.value for row in envelope.counter_records) == 0
    kinds = [row.proof_kind for row in envelope.resolutions]
    assert kinds.count(authority.QueryZeroProofKindV1.FORBIDDEN_ROUTE_PREDECESSOR) == 23
    assert kinds.count(
        authority.QueryZeroProofKindV1.OPTIONAL_STAGE_PRIVATE_RUNTIME_EXCLUSION
    ) == 60
    for resolution, record in zip(
        envelope.resolutions, envelope.counter_records, strict=True
    ):
        record.verify_against(registry.by_path[record.path])
        assert record.observed is True
        assert record.value == 0
        assert record.recorder_id == resolution.resolution_id
        assert record.counter_registry_id == registry.registry_id


def test_forbidden_zeros_bind_predecessor_and_optional_zeros_bind_runtime(case) -> None:
    envelope = case[-1]
    predecessor = {row.path: row for row in case[3].native_zero_proofs}
    for resolution in envelope.resolutions:
        if resolution.path in predecessor:
            assert resolution.proof_kind is (
                authority.QueryZeroProofKindV1.FORBIDDEN_ROUTE_PREDECESSOR
            )
            assert resolution.predecessor_zero_proof_id == (
                predecessor[resolution.path].proof_id
            )
            assert resolution.operation_boundary_ids
            assert not resolution.excluded_source_modules
        else:
            assert resolution.proof_kind is (
                authority.QueryZeroProofKindV1
                .OPTIONAL_STAGE_PRIVATE_RUNTIME_EXCLUSION
            )
            assert resolution.predecessor_zero_proof_id is None
            assert resolution.excluded_source_modules
            assert all(
                disposition == "OPTIONAL_REPEATABLE"
                for _stage, disposition in resolution.stage_contexts
            )


def test_required_build_epoch_sample_tax_is_not_zeroed(case) -> None:
    envelope = case[-1]
    document = envelope.to_document()
    required = tuple(document["required_build_epoch_paths_remaining"])
    record_paths = {row.path for row in envelope.counter_records}
    assert len(required) == 100
    assert not record_paths.intersection(required)
    assert all(
        path.startswith(("acquisition.", "build.", "closure."))
        for path in required
    )
    assert document["combined_formal_v6_counter_record_count"] == 101
    assert document["remaining_required_path_authority_count"] == 101
    assert document["required_initial_acquisition_build_reconciliation_zeroed"] is False
    assert document["build_epoch_cost_authority_present"] is False
    assert document["sample_tax_erased_by_model_reuse"] is False
    assert document["complete_202_counter_record_chain_present"] is False
    assert document["certificate_issued"] is False
    assert document["official_execution_allowed"] is False
    assert document["counter_completeness_gate_status"].endswith("NOT_RUN")


def test_exact_bytes_replay_rescans_private_runtime(case) -> None:
    replay = authority.verify_abstract_query_native_zero_authority_bytes_v1(
        source=case[0],
        accounted_execution=case[1],
        coverage_report=case[2],
        zero_closure=case[3],
        retained_inventory=case[4],
        query_owner_envelope=case[5],
        lifecycle_envelope=case[6],
        shared_envelope=case[7],
        raw=case[8].canonical_bytes,
    )
    assert replay.outcome is authority.QueryZeroReplayOutcomeV1.VERIFIED
    assert replay.envelope_id == case[8].envelope_id
    assert replay.to_document()["runtime_tree_rescanned"] is True


def test_document_tamper_fails_before_root_reexecution(case) -> None:
    forged = deepcopy(case[-1].to_document())
    forged["sample_tax_erased_by_model_reuse"] = True
    replay = authority.verify_abstract_query_native_zero_authority_bytes_v1(
        source=case[0],
        accounted_execution=case[1],
        coverage_report=case[2],
        zero_closure=case[3],
        retained_inventory=case[4],
        query_owner_envelope=case[5],
        lifecycle_envelope=case[6],
        shared_envelope=case[7],
        raw=canonical_json_bytes(forged),
    )
    assert replay.outcome is authority.QueryZeroReplayOutcomeV1.DOCUMENT_BLOCKED
    assert replay.envelope_id is None

