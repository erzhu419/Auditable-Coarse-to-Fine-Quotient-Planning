import hashlib

import pytest

from acfqp import construction_k7_ten_terminal_aggregation_protocol_v180r12r2 as protocol


def test_v180r12r2_protocol_binds_exact_sources_denominators_and_fresh_slot() -> None:
    frozen = protocol.freeze_ten_terminal_aggregation_protocol_v180r12r2()
    document = frozen.to_document()
    assert len(frozen.aggregation_protocol_id) == 64
    assert len(frozen.aggregation_execution_slot_id) == 64
    assert document["v180r12r1_status"] == "STALE_UNEXECUTED"
    assert document["v180r12r1_same_authorization_execution_forbidden"] is True
    slot = document["aggregation_execution_slot"]
    assert slot["logical_occurrence_id"] == protocol.LOGICAL_OCCURRENCE_ID
    assert slot["execution_nonce"] == protocol.EXECUTION_NONCE
    assert slot["aggregation_execution_slot_id"] == (
        frozen.aggregation_execution_slot_id
    )
    assert slot["predecessor_v180r12r1_logical_occurrence_id"] != (
        slot["logical_occurrence_id"]
    )
    assert document["source_group_count"] == 5
    assert len(document["retained_source_groups"]) == 5
    assert document["retained_source_total_byte_count"] == 15_496_039
    assert document["retained_source_file_count"] == 10
    assert document["retained_terminal_file_count"] == 5
    assert document["retained_independent_verification_file_count"] == 5
    assert document["retained_source_paths_unique"] is True
    assert document["terminal_code_count"] == 10
    assert document["route_component_chain_count"] == 12
    assert document["logical_terminal_representative_component_count"] == 10
    assert document["nonrepresentative_v180r7r1_route_component_count"] == 2
    assert document["counter_records_per_route_component"] == 269
    assert document["logical_terminal_representative_record_count"] == 2_690
    assert document["unique_route_component_record_count"] == 3_228
    assert document["extra_nonrepresentative_v180r7r1_record_count"] == 538
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
    assert document["v180r7r1_construction_axis_separate"] is True
    assert document["campaign_orchestration_uses_typed_campaign_scope"] is True
    assert document["campaign_orchestration_route_kind"] is None
    assert document["campaign_scope_structural_boundary_required"] is True
    assert document[
        "campaign_scope_structural_declarations_are_not_counter_records"
    ] is True
    assert document[
        "campaign_scope_derived_denominators_are_not_actual_measurements"
    ] is True
    assert document["campaign_scope_actual_measurement_ledger_present"] is False
    assert document["legacy_abstract_only_campaign_route_reuse_forbidden"] is True
    assert document["completed_predecessor_outcome_bytes_accessed"] is True
    assert document[
        "retained_source_files_are_predecessor_evidence_not_v180r12r2_outcome"
    ] is True
    assert document["v180r12r2_outcome_bytes_accessed"] is False
    assert document["aggregation_execution_count"] == 0
    assert document["authorization_evidence_source_boundary_commit_required"] is True
    prelaunch = document["prelaunch_contract"]
    assert prelaunch == protocol.prelaunch_contract_v180r12r2()
    assert prelaunch["source_closure_rule_id"] == (
        "fe5036863176827c036ab5aef487b8e920896455dc684e44ae7791438dbb408c"
    )
    assert prelaunch["materialization_rule_id"] == (
        "79513bd291443fa661c05bc1ff91b6c8f3b8f51dda9aac01073ffec5376abf3d"
    )
    assert prelaunch["launch_rule_id"] == (
        "57e88919b379a3fc2150dcefea46d30488b128832601e31269d225c4de37480b"
    )
    assert prelaunch["actual_manifest_digest_preregistered"] is False
    assert prelaunch["actual_manifest_digest_is_runtime_transport_receipt"] is True
    assert prelaunch["actual_manifest_digest_is_scientific_identity"] is False
    assert prelaunch["normalized_wrapper_redacted_literal_count"] == 8
    assert prelaunch["external_root_relative_path"] == (
        ".tmp/exact-freeze/"
        "v180r12r2_ten_terminal_aggregation_prelaunch_external_root.json"
    )
    assert prelaunch[
        "created_before_v180r12r2_authorized_production_execution"
    ] is True
    assert prelaunch[
        "external_root_creation_required_before_authorization_issuance"
    ] is False
    assert prelaunch["git_process_schedule_count"] == 6
    assert prelaunch["outer_launcher_byte_caps"] == {
        "external_root": 1 * 1024 * 1024,
        "bootstrap": 1 * 1024 * 1024,
        "materializer": 2 * 1024 * 1024,
        "launcher": 1 * 1024 * 1024,
        "launch_manifest": 16 * 1024 * 1024,
        "runner": 4 * 1024 * 1024,
        "source_file": 8 * 1024 * 1024,
        "source_closure_file_count": 4_096,
        "source_closure_total_bytes": 128 * 1024 * 1024,
        "executable": 64 * 1024 * 1024,
        "git_archive": 256 * 1024 * 1024,
        "failure_message": 4_096,
        "child_stdout_or_stderr": 16 * 1024 * 1024,
        "child_stream_retained_prefix": 4_096,
        "stream_buffer": 1 * 1024 * 1024,
        "launch_artifact": 16 * 1024 * 1024,
        "scientific_artifact_observation": 1024 * 1024 * 1024,
    }
    assert prelaunch[
        "authorization_evidence_verification_first_action_scope"
    ] == (
        "FIRST_ACTION_INSIDE_RUNNER_MAIN_AFTER_PRELAUNCH_DISPATCH_"
        "BEFORE_ANY_SCIENTIFIC_OUTPUT_INSPECTION_OR_CREATION"
    )
    assert prelaunch[
        "authorization_evidence_verification_is_process_first_action"
    ] is False
    assert prelaunch["materialization_is_campaign_actual_measurement"] is False
    assert prelaunch["launch_receipts_are_campaign_actual_measurements"] is False
    assert prelaunch["production_launch_attempt_relative_path"].endswith(
        "/PRODUCTION_LAUNCH_ATTEMPT.json"
    )
    assert prelaunch["verification_launch_attempt_relative_path"].endswith(
        "/VERIFICATION_LAUNCH_ATTEMPT.json"
    )
    assert prelaunch["launch_attempt_record_written_o_excl_before_child_exec"] is True
    assert prelaunch["launch_attempt_record_is_concurrency_and_replay_lock"] is True
    assert prelaunch[
        "launch_terminal_receipt_or_failure_cannot_replace_attempt_lock"
    ] is True
    assert prelaunch[
        "launch_freshness_matrix_includes_attempt_receipt_failure_and_"
        "scientific_output_progress"
    ] is True
    assert prelaunch["whole_child_address_space_cap_bytes"] == (
        16 * 1024 * 1024 * 1024
    )
    assert prelaunch[
        "verification_launch_requires_typed_successful_production_attempt_"
        "and_receipt_join"
    ] is True
    assert prelaunch["materialization_failure_sibling_forbids_any_launch"] is True
    assert prelaunch["production_success_requires_runtime_cas_absent"] is True
    assert prelaunch["verification_start_requires_runtime_cas_absent"] is True
    assert prelaunch[
        "runtime_cas_absence_matches_production_and_verification_runner_"
        "freshness"
    ] is True
    assert document["source_boundary_empty_bridge_commit_required"] is True
    assert document["source_boundary_empty_bridge_must_preserve_entire_tree"] is True
    assert document[
        "source_boundary_bridge_then_wrapper_eight_literal_commit_sequence_required"
    ] is True
    assert document[
        "source_boundary_candidate_build_may_relax_only_literal_commit_presence"
    ] is True
    assert document[
        "source_boundary_runtime_freeze_requires_committed_wrapper_literals"
    ] is True
    assert document[
        "source_boundary_candidate_and_runtime_payload_identity_must_match"
    ] is True
    assert document[
        "source_boundary_post_literal_bound_history_touch_forbidden"
    ] is True
    assert document["address_space_hard_cap_bytes"] == 16 * 1024 * 1024 * 1024
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
    assert document["glibc_malloc_trim_required_fail_closed"] is True
    assert document["glibc_malloc_trim_allowed_return_statuses"] == [0, 1]
    assert document[
        "linux_proc_self_statm_current_vms_proof_required_before_rlimit_as"
    ] is True
    assert document[
        "current_vms_must_not_exceed_address_space_cap_before_rlimit_as"
    ] is True
    assert document["finalizer_transient_heap_release_phase_count"] == 7
    assert document[
        "independent_verifier_transient_heap_release_phase_count_per_replay"
    ] == 10
    assert document["producer_runner_precap_heap_release_phase_count"] == 1
    assert document["producer_total_transient_heap_release_phase_count"] == 8
    assert document[
        "verification_runner_external_heap_release_phase_count"
    ] == 2
    assert document["verification_replay_count"] == 2
    assert document["verification_total_transient_heap_release_phase_count"] == 22
    assert document["transient_heap_release_authority_class"] == (
        "PREAUTHORIZATION_MEMORY_LIFECYCLE_STRUCTURAL_OBLIGATION"
    )
    assert document[
        "transient_heap_release_is_preauthorization_resource_schedule"
    ] is True
    assert document["transient_heap_release_is_campaign_actual_measurement"] is False
    assert document["failure_emergency_reserve_bytes"] == 4 * 1024 * 1024
    assert document["failure_emergency_reserve_allocated_before_rlimit_as"] is True
    assert document["failure_emergency_reserve_counted_inside_address_space_cap"] is True
    assert document["failure_message_byte_cap"] == 4_096
    assert document["failure_type_byte_cap"] == 128
    assert document["failure_message_utf8_formatting_fail_safe"] is True
    assert document["failure_traceback_detach_and_child_frame_clear_required"] is True
    assert document["alarm_teardown_inside_protected_terminal_boundary"] is True
    assert document["alarm_cancel_or_ignore_before_primary_failure_formatting"] is True
    assert document["alarm_neutralization_precedes_failure_reserve_release"] is True
    assert document["alarm_previous_handler_restore_after_failure_reserve_release"] is True
    assert document["failure_reserve_release_precedes_failure_formatting"] is True
    assert document["alarm_teardown_failure_typed_observation_required"] is True
    assert document["failure_path_heap_release_best_effort"] is True
    assert document["failure_path_heap_release_is_not_fail_closed_phase"] is True
    assert document["failure_path_heap_release_is_campaign_actual_measurement"] is False
    assert document["failure_progress_observation_streaming_sha256_required"] is True
    assert document["failure_observation_stream_buffer_bytes"] == 1024 * 1024
    assert document["producer_progress_path_count"] == 6
    assert document["producer_all_progress_paths_absent_before_execution_required"] is True
    assert document["verification_runtime_cas_absent_before_execution_required"] is True
    assert document["verification_terminal_input_byte_cap"] == 1024 * 1024 * 1024
    assert document["verification_terminal_input_cap_checked_before_and_during_read"] is True
    assert document["COUNTER_COMPLETENESS_BLOCKER"] == (
        "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
    )
    assert document["fresh_v180r12r3_actual_measurement_ledger_required"] is True
    assert document[
        "fresh_v180r12r3_authorization_and_execution_required"
    ] is True
    assert document["v180r12r2_counter_completeness_claimed"] is False
    assert document["v180r12r2_workload_economics_claimed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    if protocol.EXPECTED_PROTOCOL_ID != "0" * 64:
        assert frozen.aggregation_protocol_id == protocol.EXPECTED_PROTOCOL_ID
        assert len(frozen.canonical_bytes) == protocol.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
            protocol.EXPECTED_CANONICAL_SHA256
        )


def test_v180r12r2_protocol_has_ten_representatives_and_three_r7r1_components() -> None:
    document = protocol.build_ten_terminal_aggregation_protocol_v180r12r2()
    components = document["ordered_route_components"]
    representatives = [
        row for row in components if row["logical_terminal_representative"]
    ]
    r7r1 = [
        row
        for row in components
        if row["source_kind"] == "V180R7R1_FRESH_FULL_GROUND_FALLBACK"
    ]
    assert len(representatives) == 10
    assert [(row["terminal_code"], row["route_kind"]) for row in r7r1] == [
        ("FULL_GROUND_FALLBACK", "ABSTRACT_FAILED_PREFIX"),
        ("FULL_GROUND_FALLBACK", "LOCAL_ATTEMPT"),
        ("FULL_GROUND_FALLBACK", "DIRECT_FALLBACK"),
    ]
    assert [row["logical_terminal_representative"] for row in r7r1] == [
        False,
        False,
        True,
    ]


def test_v180r12r2_protocol_rejects_changed_retained_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    original = protocol._read_regular_symlink_free  # noqa: SLF001
    target = protocol.RETAINED_SOURCE_GROUP_SPECS[0][3]

    def changed(path):
        raw = original(path)
        if path.as_posix().endswith(target):
            return raw + b" "
        return raw

    monkeypatch.setattr(protocol, "_read_regular_symlink_free", changed)
    with pytest.raises(
        protocol.TenTerminalAggregationProtocolV180R12R2Error,
        match="retained terminal or independent-verification bytes changed",
    ):
        protocol.build_ten_terminal_aggregation_protocol_v180r12r2()
