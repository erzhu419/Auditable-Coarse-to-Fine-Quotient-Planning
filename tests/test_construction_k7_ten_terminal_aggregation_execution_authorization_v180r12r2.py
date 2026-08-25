from pathlib import Path

import pytest

from acfqp import (
    construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2
    as authorization,
)
from acfqp import construction_k7_ten_terminal_aggregation_protocol_v180r12r2 as protocol


def test_v180r12r2_authorization_input_facts_bind_all_ten_retained_files() -> None:
    facts = authorization._retained_source_input_facts()  # noqa: SLF001
    assert len(facts) == 10
    assert sum(row["byte_count"] for row in facts) == 15_496_039
    assert [row["role"] for row in facts] == [
        "TERMINAL",
        "INDEPENDENT_VERIFICATION",
    ] * 5
    assert len({row["relative_path"] for row in facts}) == 10
    assert all(len(row["content_id"]) == 64 for row in facts)
    assert all(len(row["sha256"]) == 64 for row in facts)


def test_v180r12r2_authorization_document_is_outcome_free_with_stubbed_source_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub = [
        {
            "relative_path": "src/acfqp/stub.py",
            "byte_count": 1,
            "sha256": "1" * 64,
        }
    ]
    monkeypatch.setattr(authorization, "_source_facts", lambda: stub)
    document = authorization.build_ten_terminal_aggregation_execution_authorization_v180r12r2()
    assert document["logical_occurrence_id"] == protocol.LOGICAL_OCCURRENCE_ID
    assert document["execution_nonce"] == protocol.EXECUTION_NONCE
    assert document["stale_v180r12r1_authorization_reused"] is False
    assert document["same_stale_authorization_execution_forbidden"] is True
    assert document["retained_source_input_fact_count"] == 10
    assert document["retained_source_input_total_byte_count"] == 15_496_039
    assert document["source_facts"] == stub
    assert (
        "scripts/launch_v180r12r2_ten_terminal_aggregation_prelaunch.py"
        in document["contract_source_fact_static_import_roots"]
    )
    assert document["source_fact_exclusions"] == list(
        authorization._SOURCE_FACT_EXCLUSIONS  # noqa: SLF001
    )
    assert document["authorization_self_source_bound_by_post_prereg_freeze"] is False
    assert document["post_prereg_authorization_evidence_freeze_required"] is True
    assert document["authorization_evidence_source_boundary_commit_required"] is True
    assert document["authorization_evidence_empty_bridge_commit_required"] is True
    assert document[
        "authorization_evidence_empty_bridge_must_preserve_entire_tree"
    ] is True
    assert document[
        "authorization_evidence_bridge_then_wrapper_eight_literal_commit_"
        "sequence_required"
    ] is True
    assert document[
        "authorization_evidence_candidate_build_may_relax_only_literal_commit_"
        "presence"
    ] is True
    assert document[
        "authorization_evidence_runtime_freeze_requires_committed_wrapper_literals"
    ] is True
    assert document[
        "authorization_evidence_candidate_and_runtime_payload_identity_must_match"
    ] is True
    assert document[
        "authorization_evidence_post_literal_bound_history_touch_forbidden"
    ] is True
    assert document["authorization_evidence_source_boundary_git_process_count"] == 6
    assert document[
        "authorization_evidence_source_boundary_git_processes_are_"
        "preauthorization_not_campaign_actual_measurements"
    ] is True
    assert document["prelaunch_contract"] == protocol.prelaunch_contract_v180r12r2()
    assert document[
        "authorization_evidence_verification_is_first_action_inside_runner_"
        "main_after_prelaunch_dispatch"
    ] is True
    assert document[
        "authorization_evidence_verification_precedes_scientific_output_"
        "inspection_or_creation_inside_runner"
    ] is True
    assert document[
        "authorization_evidence_verification_is_process_first_action"
    ] is False
    assert document[
        "resource_caps_apply_to_producer_and_producer_free_verifier"
    ] is True
    assert document["producer_runner_enforces_sigalrm_timeout"] is True
    assert document["producer_runner_enforces_rlimit_as"] is True
    assert document[
        "producer_free_verifier_runner_enforces_sigalrm_timeout"
    ] is True
    assert document["producer_free_verifier_runner_enforces_rlimit_as"] is True
    assert document["resource_caps"]["applies_to"] == [
        "PRODUCTION_AGGREGATION",
        "PRODUCER_FREE_VERIFICATION_AND_RETAINED_REPLAY",
    ]
    assert document["resource_caps"]["wall_timeout_mechanism"] == "SIGALRM"
    assert document["resource_caps"]["address_space_cap_mechanism"] == "RLIMIT_AS"
    assert document["resource_caps"]["address_space_hard_cap_bytes"] == (
        16 * 1024 * 1024 * 1024
    )
    assert document["rejected_preprereg_address_space_cap_bytes"] == (
        6 * 1024 * 1024 * 1024
    )
    assert document["rejected_preprereg_max_rss_kib"] == 6_216_640
    assert document["rejected_preprereg_elapsed_seconds"] == "1908.72"
    assert document["rejected_preprereg_failure_stage"] == (
        "V180R10R1_TO_V36_TO_V35_PLANNER_FROZENSET_CACHE"
    )
    assert document["rejected_preprereg_failure_type"] == "MemoryError"
    assert document["rejected_preprereg_kind"] == (
        "PRE_PREREG_NONFROZEN_DEVELOPMENT_RESOURCE_PREFLIGHT"
    )
    assert document["rejected_preprereg_test"] == (
        "test_v180r12r2_loads_compact_real_groups_under_explicit_6gib_rlimit"
    )
    assert document["rejected_preprereg_dummy_aggregation_protocol_id"] == (
        "a" * 64
    )
    assert document["rejected_preprereg_dummy_execution_authorization_id"] == (
        "b" * 64
    )
    assert document["rejected_preprereg_scientific_output_created"] is False
    assert document["rejected_preprereg_production_artifact_written"] is False
    assert document["rejected_preprereg_failure_artifact_written"] is False
    assert document["rejected_preprereg_runtime_cas_created"] is False
    assert document[
        "rejected_preprereg_authorized_production_aggregation_execution_attempted"
    ] is False
    assert document[
        "rejected_preprereg_development_resource_preflight_computation_attempted"
    ] is True
    assert document[
        "rejected_preprereg_development_resource_preflight_completed"
    ] is False
    assert document["rejected_preprereg_scientific_authority"] is False
    assert document["rejected_preprereg_official_authority"] is False
    assert document["rejected_preprereg_cap_was_frozen_authorization"] is False
    assert document[
        "address_space_cap_selected_before_v180r12r2_authorization"
    ] is True
    assert document["resource_caps"]["glibc_malloc_trim_required_fail_closed"] is True
    assert document["resource_caps"][
        "glibc_malloc_trim_allowed_return_statuses"
    ] == [0, 1]
    assert document["resource_caps"][
        "linux_proc_self_statm_current_vms_proof_required_before_rlimit_as"
    ] is True
    assert document["resource_caps"][
        "current_vms_must_not_exceed_address_space_cap_before_rlimit_as"
    ] is True
    assert document["resource_caps"][
        "finalizer_transient_heap_release_phase_count"
    ] == 7
    assert document["resource_caps"][
        "independent_verifier_transient_heap_release_phase_count_per_replay"
    ] == 10
    assert document["resource_caps"][
        "producer_runner_precap_heap_release_phase_count"
    ] == 1
    assert document["resource_caps"][
        "producer_total_transient_heap_release_phase_count"
    ] == 8
    assert document["resource_caps"][
        "verification_runner_external_heap_release_phase_count"
    ] == 2
    assert document["resource_caps"]["verification_replay_count"] == 2
    assert document["resource_caps"][
        "verification_total_transient_heap_release_phase_count"
    ] == 22
    assert document["resource_caps"]["transient_heap_release_authority_class"] == (
        "PREAUTHORIZATION_MEMORY_LIFECYCLE_STRUCTURAL_OBLIGATION"
    )
    assert document["resource_caps"][
        "transient_heap_release_is_preauthorization_resource_schedule"
    ] is True
    assert document["resource_caps"][
        "transient_heap_release_is_campaign_actual_measurement"
    ] is False
    assert document["resource_caps"]["failure_emergency_reserve_bytes"] == 4 * 1024 * 1024
    assert document["resource_caps"][
        "failure_emergency_reserve_allocated_before_rlimit_as"
    ] is True
    assert document["resource_caps"][
        "failure_emergency_reserve_counted_inside_address_space_cap"
    ] is True
    assert document["resource_caps"]["failure_message_byte_cap"] == 4_096
    assert document["resource_caps"]["failure_type_byte_cap"] == 128
    assert document["resource_caps"]["failure_message_utf8_formatting_fail_safe"] is True
    assert document["resource_caps"][
        "failure_traceback_detach_and_child_frame_clear_required"
    ] is True
    assert document["resource_caps"][
        "alarm_teardown_inside_protected_terminal_boundary"
    ] is True
    assert document["resource_caps"][
        "alarm_cancel_or_ignore_before_primary_failure_formatting"
    ] is True
    assert document["resource_caps"][
        "alarm_neutralization_precedes_failure_reserve_release"
    ] is True
    assert document["resource_caps"][
        "alarm_previous_handler_restore_after_failure_reserve_release"
    ] is True
    assert document["resource_caps"][
        "failure_reserve_release_precedes_failure_formatting"
    ] is True
    assert document["resource_caps"][
        "alarm_teardown_failure_typed_observation_required"
    ] is True
    assert document["resource_caps"]["failure_path_heap_release_best_effort"] is True
    assert document["resource_caps"][
        "failure_path_heap_release_is_not_fail_closed_phase"
    ] is True
    assert document["resource_caps"][
        "failure_path_heap_release_is_campaign_actual_measurement"
    ] is False
    assert document["resource_caps"][
        "failure_progress_observation_streaming_sha256_required"
    ] is True
    assert document["resource_caps"]["failure_observation_stream_buffer_bytes"] == 1024 * 1024
    assert document["resource_caps"]["producer_progress_path_count"] == 6
    assert document["resource_caps"][
        "producer_all_progress_paths_absent_before_execution_required"
    ] is True
    assert document["resource_caps"][
        "verification_runtime_cas_absent_before_execution_required"
    ] is True
    assert document["resource_caps"]["verification_terminal_input_byte_cap"] == 1024 * 1024 * 1024
    assert document["resource_caps"][
        "verification_terminal_input_cap_checked_before_and_during_read"
    ] is True
    assert document["source_group_count"] == 5
    assert document["terminal_code_count"] == 10
    assert document["route_component_chain_count"] == 12
    assert document["logical_terminal_representative_record_count"] == 2_690
    assert document["unique_route_component_record_count"] == 3_228
    assert document["terminal_shared_resource_receipt_count"] == 90
    assert document["campaign_scope_structural_obligation_count"] == 9
    assert document["campaign_scope_actual_counter_record_count"] == 0
    assert document["campaign_scope_actual_shared_resource_receipt_count"] == 0
    assert document["campaign_scope_actual_work_vector_count"] == 0
    assert document["campaign_scope_actual_comparison_vector_count"] == 0
    assert document["campaign_scope_actual_projection_proof_count"] == 0
    assert document["campaign_scope_actual_native_zero_attestation_count"] == 0
    assert document["campaign_scope_authoritative_receipt_count"] == 0
    assert document["total_authoritative_shared_resource_receipt_count"] == 90
    assert document["typed_campaign_scope_structural_boundary_required"] is True
    assert document["typed_campaign_scope_actual_accounting_chain_present"] is False
    assert document["v180r12r2_aggregation_execution_started"] is False
    assert document["v180r12r2_aggregation_execution_count"] == 0
    assert document["v180r12r2_outcome_bytes_accessed"] is False
    assert document["authorization_frozen_before_any_v180r12r2_outcome"] is True
    assert document["COUNTER_COMPLETENESS_BLOCKER"] == (
        "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
    )
    assert document["fresh_v180r12r3_actual_measurement_ledger_required"] is True
    assert document["fresh_v180r12r3_authorization_and_execution_required"] is True
    assert document["v180r12r2_counter_completeness_claimed"] is False
    assert document["v180r12r2_workload_economics_claimed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False


def test_v180r12r2_authorization_rejects_mutated_prelaunch_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen_protocol = protocol.freeze_ten_terminal_aggregation_protocol_v180r12r2()
    assert frozen_protocol.to_document()["prelaunch_contract"] == (
        protocol.prelaunch_contract_v180r12r2()
    )
    mutated = protocol.prelaunch_contract_v180r12r2()
    mutated["source_closure_rule_id"] = "f" * 64
    monkeypatch.setattr(
        protocol,
        "prelaunch_contract_v180r12r2",
        lambda: mutated,
    )
    with pytest.raises(
        authorization.TenTerminalAggregationExecutionAuthorizationV180R12R2Error,
        match="protocol or slot changed",
    ):
        authorization.build_ten_terminal_aggregation_execution_authorization_v180r12r2()


def test_v180r12r2_authorization_has_exact_paths_and_finite_caps() -> None:
    assert authorization.WORKER_PROCESS_COUNT == 1
    assert authorization.TIMEOUT_SECONDS == 14_400
    assert authorization.ADDRESS_SPACE_HARD_CAP_BYTES == 16 * 1024 * 1024 * 1024
    assert authorization.OUTPUT_TOTAL_BYTE_CAP == 1024 * 1024 * 1024
    assert authorization.OUTPUT_ROOT_RELATIVE_PATH == (
        ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation"
    )
    assert authorization.TERMINAL_RELATIVE_PATH.endswith("/TERMINAL.json")
    assert authorization.FAILURE_RELATIVE_PATH == (
        ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation_failure.json"
    )
    assert not authorization.FAILURE_RELATIVE_PATH.startswith(
        f"{authorization.OUTPUT_ROOT_RELATIVE_PATH}/"
    )
    assert authorization.VERIFICATION_RELATIVE_PATH.endswith(
        "v180r12r2_ten_terminal_aggregation_verification.json"
    )
    assert authorization.RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH.endswith(
        "v180r12r2_ten_terminal_aggregation_verification_replay.json"
    )


def test_v180r12r2_authorization_binds_known_dynamic_import_targets() -> None:
    document = (
        authorization.build_ten_terminal_aggregation_execution_authorization_v180r12r2()
    )
    paths = {row["relative_path"] for row in document["source_facts"]}
    assert "src/acfqp/abstraction/behavioral.py" in paths
    assert "src/acfqp/v075_production_semantic_authority_registry_v2.py" in paths


def test_v180r12r2_authorization_closure_is_complete_when_all_roots_land() -> None:
    root = Path(__file__).resolve().parents[1]
    all_roots = (
        *authorization._PRODUCTION_SOURCE_ROOTS,  # noqa: SLF001
        *authorization._VERIFICATION_SOURCE_ROOTS,  # noqa: SLF001
        *authorization._CONTRACT_SOURCE_ROOTS,  # noqa: SLF001
    )
    if not all((root / relative_path).is_file() for relative_path in all_roots):
        pytest.skip("V180r12r2 runner/verifier source roots have not landed yet")
    frozen = authorization.freeze_ten_terminal_aggregation_execution_authorization_v180r12r2()
    document = frozen.to_document()
    replayed = authorization.replay_authorization_source_facts_v180r12r2(document)
    paths = {row["relative_path"] for row in replayed}
    assert set(all_roots) <= paths
    assert not set(authorization._SOURCE_FACT_EXCLUSIONS) & paths  # noqa: SLF001
    assert document["source_fact_byte_count"] <= (
        authorization.SOURCE_CATALOG_TOTAL_BYTE_CAP
    )
