from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_accounted_shared_authority_v2 as authority
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage
from acfqp import construction_k7_abstract_certified_lifecycle_reconciliation_authority_v1 as lifecycle
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero
from acfqp import construction_k7_abstract_certified_query_owner_authority_v1 as owner
from acfqp import construction_k7_abstract_pass_production_native_accounting_v1 as retained
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, content_id
from acfqp.phase3e_model_only_accounted_executor_v2 import (
    ACCOUNTED_RUNTIME_SOURCE_PATHS,
    FORMAL_SHARED_PATHS,
    PENDING_SHARED_PATH,
    execute_model_only_accounted_query_v2,
    prepare_model_only_accounted_runtime_v2,
    require_accounted_model_only_execution_v2,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    load_phase3c_model_source_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    cas_root = tmp_path_factory.mktemp("accounted-runtime-cas")
    preparation = prepare_model_only_accounted_runtime_v2(
        source_root=ROOT / "src",
        runtime_cas_root=cas_root,
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
        lifecycle
        .issue_abstract_certified_lifecycle_reconciliation_authority_v1(
            source,
            execution,
            report,
            zeros,
            inventory,
            query_owner,
        )
    )
    envelope = authority.issue_abstract_accounted_shared_authority_v2(
        source,
        accounted,
        report,
        zeros,
        inventory,
        query_owner,
        lifecycle_envelope,
    )
    return (
        source,
        accounted,
        report,
        zeros,
        inventory,
        query_owner,
        lifecycle_envelope,
        envelope,
    )


def test_six_accounted_domains_are_central_and_role_separated() -> None:
    from acfqp.phase3e_model_only_accounted_executor_v2 import LOCAL_DOMAINS as executor_domains

    domains = authority.LOCAL_DOMAINS | executor_domains
    assert len(domains) == 6
    assert domains <= PHASE3E_DOMAIN_TAGS
    payload = {"schema": "same-accounted-abstract-payload"}
    assert len({content_id(domain, payload) for domain in domains}) == 6


def test_runtime_preparation_is_exact_private_lease_source_closure(case) -> None:
    preparation = case[1].preparation
    document = preparation.to_document()
    assert preparation.source_paths == ACCOUNTED_RUNTIME_SOURCE_PATHS
    assert preparation.manifest.file_count == len(ACCOUNTED_RUNTIME_SOURCE_PATHS)
    assert tuple(
        row["relative_path"]
        for row in document["runtime_manifest"]["entries"]
    ) == ACCOUNTED_RUNTIME_SOURCE_PATHS
    assert document["private_runtime_lease_required"] is True
    assert document["runtime_tree_build_charged_to_occurrence"] is False
    assert document["official_execution_allowed"] is False


def test_live_accounted_execution_has_exact_eight_path_inventory(case) -> None:
    accounted = require_accounted_model_only_execution_v2(case[1])
    measurement = accounted.measurement
    values = measurement.values
    assert tuple(values) == FORMAL_SHARED_PATHS
    assert all(values[path] > 0 for path in FORMAL_SHARED_PATHS)
    assert values["process.launches"] == 1
    assert values["common.hash_invocations"] > 6
    assert values["io.staged_bytes"] == (
        measurement.runtime_total_bytes + measurement.request_bytes
    )
    assert values["io.mounted_bytes_peak"] == (
        measurement.runtime_total_bytes
        + measurement.request_bytes
        + measurement.accounted_worker_output_bytes
    )
    assert values["memory.working_bytes_peak"] == (
        measurement.child_wait4_peak_bytes
    )
    assert PENDING_SHARED_PATH not in values


def test_seven_new_records_and_existing_launch_form_one_shared_union(case) -> None:
    envelope = case[-1]
    registry = registry_v6.official_counter_registry_v6()
    assert tuple(row.path for row in envelope.counter_records) == (
        authority.NEW_FORMAL_SHARED_PATHS
    )
    assert tuple(row.value for row in envelope.counter_records) == tuple(
        case[1].measurement.values[path]
        for path in authority.NEW_FORMAL_SHARED_PATHS
    )
    for resolution, record in zip(
        envelope.resolutions, envelope.counter_records, strict=True
    ):
        assert record.recorder_id == resolution.resolution_id
        assert record.counter_registry_id == registry.registry_id
        assert record.observed is True
        record.verify_against(registry.by_path[record.path])
        resolution_document = resolution.to_document()
        assert resolution_document["aggregate_stage_kinds"] == [
            stage.value for stage in authority.AGGREGATE_STAGES
        ]
        assert resolution_document["occurrence_total_only"] is True
        assert resolution_document["per_stage_numeric_split_claimed"] is False
        assert resolution_document["source_v1_record_relabelled_as_v6"] is False
    lifecycle_launch = next(
        row for row in case[-2].counter_records if row.path == "process.launches"
    )
    assert lifecycle_launch.record_id == envelope.lifecycle_process_launch_record_id
    assert lifecycle_launch.value == case[1].measurement.values["process.launches"] == 1


def test_read_is_upper_but_other_seven_values_are_exact(case) -> None:
    by_path = {row.path: row for row in case[-1].resolutions}
    assert by_path["io.read_bytes"].value_kind == "VERIFIED_UPPER_BOUND"
    assert all(
        row.value_kind == "EXACT"
        for path, row in by_path.items()
        if path != "io.read_bytes"
    )
    assert by_path["memory.working_bytes_peak"].measurement_method == (
        "PARENT_WAIT4_RUSAGE_PEAK"
    )


def test_progress_is_honestly_41_of_202_with_only_output_shared_pending(case) -> None:
    document = case[-1].to_document()
    assert document["retained_prior_completion_progress_count"] == 34
    assert document["new_formal_v6_counter_record_count"] == 7
    assert document["combined_completion_progress_count"] == 41
    assert document["remaining_required_path_authority_count"] == 161
    assert document["shared_resource_path_count_closed_before_here"] == 1
    assert document["shared_resource_path_count_closed_here"] == 7
    assert document["remaining_shared_resource_path_count"] == 1
    assert document["pending_shared_resource_path"] == "io.output_bytes"
    assert document["all_nine_shared_resource_receipts_complete"] is False
    assert document["formal_v6_work_vector_id"] is None
    assert document["formal_v6_comparison_vector_id"] is None


def test_portable_replay_rebuilds_the_same_seven_records_without_replanning(case) -> None:
    (
        source,
        accounted,
        report,
        zeros,
        inventory,
        query_owner,
        lifecycle_envelope,
        envelope,
    ) = case
    replay = authority.verify_abstract_accounted_shared_authority_bytes_v2(
        envelope.canonical_bytes,
        source,
        accounted,
        report,
        zeros,
        inventory,
        query_owner,
        lifecycle_envelope,
    )
    assert replay.outcome is authority.AccountedSharedReplayOutcomeV2.VERIFIED
    assert replay.envelope is not None
    assert replay.envelope.envelope_id == envelope.envelope_id
    assert replay.to_document()["planner_reexecution_performed"] is False
    assert replay.to_document()["ground_access_performed"] is False


def test_resigned_measurement_or_gate_claim_is_rejected(case) -> None:
    (
        source,
        accounted,
        report,
        zeros,
        inventory,
        query_owner,
        lifecycle_envelope,
        envelope,
    ) = case
    document = deepcopy(envelope.to_document())
    document["formal_v6_counter_records"][0]["value"] += 1
    payload = dict(document)
    payload.pop("abstract_accounted_shared_envelope_id")
    document["abstract_accounted_shared_envelope_id"] = content_id(
        authority.ENVELOPE_DOMAIN, payload
    )
    replay = authority.verify_abstract_accounted_shared_authority_bytes_v2(
        canonical_json_bytes(document),
        source,
        accounted,
        report,
        zeros,
        inventory,
        query_owner,
        lifecycle_envelope,
    )
    assert replay.outcome is authority.AccountedSharedReplayOutcomeV2.DOCUMENT_BLOCKED
    assert replay.envelope is None


def test_caller_cannot_mint_resolution(case) -> None:
    with pytest.raises(
        authority.ConstructionK7AbstractAccountedSharedAuthorityV2Error,
        match="caller-minted",
    ):
        replace(case[-1].resolutions[0], _issuer=object())


def test_all_official_claims_remain_locked(case) -> None:
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
