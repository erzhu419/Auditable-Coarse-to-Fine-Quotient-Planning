from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_campaign_measurement_execution_authorization_v180r12r4
    as authorization,
)
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r12r4 as domains

from test_construction_k7_campaign_measurement_protocol_v180r12r4 import (
    cgroup_parent_fact,
    runtime_capability_fact,
)


_ROOT = Path(__file__).resolve().parents[1]
_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_authorization_evidence_freeze_"
    "v180r12r4.py"
)


def frozen(*, source_facts=None):
    return authorization.freeze_campaign_measurement_execution_authorization_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact(),
        runtime_capability_fact=runtime_capability_fact(),
        source_facts=source_facts,
    )


def _evidence_wrapper_raw() -> bytes:
    return (_ROOT / _EVIDENCE_RELATIVE_PATH).read_bytes()


def _literal_phase_wrapper(raw: bytes) -> bytes:
    result = raw
    for name, (start, end, _replacement) in sorted(
        authorization._authorization_evidence_literal_spans(  # noqa: SLF001
            raw
        ).items(),
        key=lambda item: item[1][0],
        reverse=True,
    ):
        replacement = (
            b'"1111111111111111111111111111111111111111111111111111111111111111"'
            if name in authorization._AUTHORIZATION_EVIDENCE_STRING_CONSTANTS  # noqa: SLF001
            else b"123456"
        )
        result = result[:start] + replacement + result[end:]
    return result


def _populate_replay_root(destination: Path, wrapper_raw: bytes) -> None:
    for relative_path in authorization.SOURCE_CLOSURE_REQUIRED_ROOTS:
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = (_ROOT / relative_path).read_bytes()
        target.write_bytes(
            wrapper_raw if relative_path == _EVIDENCE_RELATIVE_PATH else raw
        )


def test_authorization_binds_protocol_predecessor_and_exact_fresh_scope() -> None:
    document = frozen().to_document()
    protocol_document = protocol.freeze_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact(),
        runtime_capability_fact=runtime_capability_fact(),
    ).to_document()
    assert document["campaign_measurement_protocol_id"] == (
        protocol_document["campaign_measurement_protocol_id"]
    )
    assert document["campaign_measurement_execution_slot_id"] == (
        protocol_document["campaign_measurement_execution_slot"][
            "campaign_measurement_execution_slot_id"
        ]
    )
    assert document["authorized_subject"] == (
        "TEN_TERMINAL_AGGREGATION_MEASURED_REPLAY_SUCCESSOR"
    )
    assert document["authorized_attempt_count"] == 1
    assert document["planned_authorized_attempt_count"] == 1
    assert document["execution_authorization_effective"] is False
    assert document["zero_sentinel_draft_is_executable_authorization"] is False
    assert document["campaign_measurement_authorization_issued"] is False
    assert document["source_bound_prelaunch_required_before_real_outcome_execution"] is True
    assert document["old_v180r12r2_authorization_reused"] is False
    assert document["v180r12r2_producer_or_verifier_rerun_authorized"] is False
    predecessor = protocol_document["predecessor_evidence"]
    assert predecessor["all_five_source_independent_verifiers_replayed"] is True
    assert predecessor[
        "all_ten_occurrence_shared_resource_receipt_sets_present"
    ] is True
    assert predecessor["all_twelve_route_component_chains_present"] is True
    assert predecessor["producer_bundle_independently_replayed"] is False
    assert document["predecessor_production_aggregation_bundle_id"] == (
        "aba966326ff9e245d1758c65d8c3103614dd1a5a7be96b86e5eb2306bade15f0"
    )
    assert document["predecessor_verification_id"] == (
        "551881bb9bc6baa8dfaa112228f9160986b8106572d6f3f6c85af49434ec14ee"
    )
    assert document["measured_scope_is_fresh_replay_successor_overhead"] is True
    assert document["measured_scope_is_retroactive_v180r12r2_aggregation_cost"] is False
    assert document["work_scope_kind"] == "ROUTE_FREE_MEASURED_REPLAY_SUCCESSOR"
    assert document["counter_registry_reference"] == "acfqp_counter_registry_v6"
    assert document["campaign_measurement_attempt_identity_contract"] == (
        protocol.campaign_measurement_attempt_identity_contract_v180r12r4()
    )
    assert document["campaign_measurement_attempt_identity_contract"][
        "attempt_domain"
    ] == domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_ATTEMPT_V180R12R4_DOMAIN
    assert document["cgroup_parent_owner_uid_equals_runtime_uid"] is True
    assert document["cgroup_parent_owner_gid_equals_runtime_gid"] is True
    assert document["cgroup_parent_owner_write_and_execute_required"] is True


def test_authorization_rejects_foreign_cgroup_owner_even_when_fact_is_resigned() -> None:
    parent = cgroup_parent_fact()
    parent["owner_uid"] = 999
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="owner/runtime identity",
    ):
        authorization.build_campaign_measurement_execution_authorization_v180r12r4(
            cgroup_parent_fact=parent,
            runtime_capability_fact=runtime_capability_fact(),
        )


def test_authorization_freezes_latest_caps_and_exact_625_event_denominator() -> None:
    document = frozen().to_document()
    caps = document["resource_caps"]
    assert caps["wall_timeout_seconds"] == 14_400
    assert caps["memory_max_bytes"] == 16 * 1024 * 1024 * 1024
    assert caps["address_space_hard_cap_bytes"] == 16 * 1024 * 1024 * 1024
    assert caps["pids_max"] == 2
    assert caps["input_file_byte_cap"] == 1 * 1024 * 1024
    assert caps["input_total_byte_cap"] == 2 * 1024 * 1024
    assert caps["subject_result_byte_cap"] == 1 * 1024 * 1024
    assert caps["terminal_byte_cap"] == caps["verification_byte_cap"] == 16 * 1024 * 1024
    assert caps["evidence_inventory_bundle_byte_cap"] == 64 * 1024 * 1024
    assert caps["execution_closure_byte_cap"] == 1 * 1024 * 1024
    assert caps["os_receipt_bundle_byte_cap"] == 16 * 1024 * 1024
    assert caps["ledger_closure_byte_cap"] == 64 * 1024 * 1024
    assert caps["stdout_byte_cap"] == caps["stderr_byte_cap"] == 1 * 1024 * 1024
    assert caps["failure_emergency_reserve_bytes"] == 4 * 1024 * 1024
    assert caps["max_event_count"] == 4_096
    assert caps["max_event_byte_count"] == 65_536
    assert caps["max_ledger_byte_count"] == 64 * 1024 * 1024
    assert document["successful_semantic_hash_pair_count"] == 137
    assert document["successful_integrity_check_pair_count"] == 145
    assert document["successful_protocol_check_pair_count"] == 15
    assert document["successful_exact_event_count"] == 625
    assert document["successful_extra_events_forbidden"] is True
    assert document["event_grammar"]["successful_event_schedule_template_count"] == 625
    assert document["fallible_paired_operation_count"] == 307
    assert document[
        "every_fallible_paired_operation_emits_exact_intent_then_outcome"
    ] is True
    assert document["process_birth_operations_emit_intent_outcome_then_reap"] is True
    assert document["mount_interval_operations_emit_open_then_close"] is True
    assert document["singleton_operation_count"] == 5
    assert document["unqualified_every_operation_intent_outcome_claim"] is False
    assert document["fallible_paired_operation_scope"] == (
        "EXACT_REGISTERED_IO_SEMANTIC_HASH_INTEGRITY_PROTOCOL_PROCESS_"
        "AND_SUBJECT_WRITE_SITES"
    )
    assert document[
        "all_307_fallible_paired_operation_sites_require_durable_intent_ack_before_listed_operation"
    ] is True
    assert document[
        "mount_interval_operations_use_open_close_not_intent_outcome"
    ] is True
    assert document[
        "singleton_operations_are_post_effect_atomic_observations_without_intent_claim"
    ] is True
    manifest = document["actual_operation_manifest"]
    assert manifest["fallible_paired_operation_count"] == 307
    assert manifest[
        "every_fallible_paired_operation_requires_one_intent_and_one_success_or_pass_outcome"
    ] is True
    assert manifest["mount_interval_operation_count"] == 2
    assert manifest["singleton_operation_count"] == 5
    assert manifest["unqualified_every_operation_intent_outcome_claim"] is False
    assert document[
        "deterministic_local_parse_shape_and_subject_computation_emits_separate_ledger_event"
    ] is False
    assert document[
        "failure_between_registered_hooks_preserves_current_phase_typed_failure_and_exact_durable_prefix"
    ] is True
    assert document["semantic_hash_counter_scope_contract"] == (
        protocol.semantic_hash_counter_scope_contract_v180r12r4()
    )


def test_authorization_freezes_empty_root_two_sibling_leaf_pidfd_topology() -> None:
    document = frozen().to_document()
    caps = document["resource_caps"]
    assert caps["clone3_clone_into_cgroup_required"] is True
    assert caps["clone3_leaf_directory_fd_required"] is True
    assert caps["pidfd_required_for_both_births"] is True
    assert caps["measurement_root_pids_max_exact"] == 2
    assert caps["measurement_root_is_process_empty"] is True
    assert caps["supervisor_and_worker_sibling_leaves_required"] is True
    assert document["measurement_root_child_roles"] == ["SUPERVISOR", "WORKER"]
    assert document["measurement_root_and_leaf_role_fact_count"] == 3
    assert document["measurement_root_and_leaf_dev_inode_receipts_required"] is True
    assert document["no_internal_process_rule_required"] is True
    assert document["supervisor_birth_phase"] == "STAGE"
    assert document["worker_birth_phase"] == "WORKER"
    assert document["worker_reap_phase"] == "WORKER"
    assert document["supervisor_reap_phase"] == "OS_OBSERVE"
    assert document["process_birth_reap_chain_count"] == 2
    assert document["root_and_both_leaf_populated_zero_before_cgroup_observed"] is True


def test_authorization_freezes_five_reads_separate_subject_and_instrumentation_boundary() -> None:
    document = frozen().to_document()
    assert document["source_input_read_chain_count"] == 2
    assert document["staged_worker_input_read_chain_count"] == 2
    assert document["subject_readback_chain_count"] == 1
    assert document["total_input_read_chain_count"] == 5
    assert document["stage_write_mount_chain_count"] == 2
    assert document["mount_close_count"] == 2
    assert document["subject_result_preopened_o_excl_by_supervisor"] is True
    assert document["subject_write_phase"] == "WORKER"
    assert document["subject_write_actor_role"] == "WORKER"
    assert document["subject_commit_phase"] == "COMMIT"
    assert document["subject_commit_actor_role"] == "SUPERVISOR"
    assert document["subject_result_is_separate_from_ledger_and_outer_terminal"] is True
    assert document["journal_ipc_ledger_hashing_storage_is_instrumentation_overhead"] is True
    assert document["instrumentation_overhead_is_campaign_actual_measurement"] is False
    assert document["instrumentation_memory_inside_children_remains_in_cgroup_peak"] is True


def test_authorization_source_closure_is_explicitly_placeholder_before_literal_freeze() -> None:
    document = frozen().to_document()
    contract = document["source_closure_contract"]
    assert contract["placeholder_only"] is True
    assert contract["expected_source_closure_id"] == "0" * 64
    assert contract["expected_source_closure_sha256"] == "0" * 64
    assert contract["expected_source_closure_file_count"] == 0
    assert contract["source_closure_identity_frozen"] is False
    assert document["source_closure_facts_supplied"] is False
    assert document["source_closure_identity_frozen"] is False
    assert document["source_closure_placeholder_only"] is True
    assert document["authorization_evidence_freeze_required_before_execution"] is True
    assert document["authorization_self_source_bound_by_post_prereg_freeze"] is False
    assert tuple(contract["required_static_roots"]) == tuple(
        sorted(protocol.SOURCE_CLOSURE_REQUIRED_ROOTS)
    )
    assert contract["required_static_root_count"] == 22
    assert len(set(contract["required_static_roots"])) == 22
    assert protocol.V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH in contract[
        "required_static_roots"
    ]


def test_source_closure_candidate_validates_sorted_unique_exact_facts() -> None:
    facts = [
        {"relative_path": "a.py", "byte_count": 1, "sha256": "1" * 64},
        {"relative_path": "b.py", "byte_count": 2, "sha256": "2" * 64},
    ]
    first = authorization.source_closure_candidate_v180r12r4(facts)
    second = authorization.source_closure_candidate_v180r12r4(facts)
    assert first == second
    assert first["source_fact_count"] == 2
    assert first["source_total_byte_count"] == 3
    assert first["source_closure_id"] == first["source_closure_sha256"]
    with pytest.raises(
        authorization.CampaignMeasurementExecutionAuthorizationV180R12R4Error
    ):
        authorization.source_closure_candidate_v180r12r4(list(reversed(facts)))


def test_authorization_rejects_supplied_closure_that_omits_static_roots() -> None:
    with pytest.raises(
        authorization.CampaignMeasurementExecutionAuthorizationV180R12R4Error,
        match="omits",
    ):
        authorization.build_campaign_measurement_execution_authorization_v180r12r4(
            cgroup_parent_fact=cgroup_parent_fact(),
            runtime_capability_fact=runtime_capability_fact(),
            source_facts=[
                {"relative_path": "a.py", "byte_count": 1, "sha256": "1" * 64}
            ],
        )


def test_source_fact_replay_rejects_symlink_and_reads_regular_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(authorization, "_ROOT", tmp_path)
    source = tmp_path / "a.py"
    source.write_bytes(b"x")
    facts = authorization.replay_authorization_source_facts_v180r12r4(("a.py",))
    assert facts == [
        {
            "relative_path": "a.py",
            "byte_count": 1,
            "sha256": hashlib.sha256(b"x").hexdigest(),
        }
    ]
    source.unlink()
    source.symlink_to(tmp_path / "missing.py")
    with pytest.raises(
        authorization.CampaignMeasurementExecutionAuthorizationV180R12R4Error
    ):
        authorization.replay_authorization_source_facts_v180r12r4(("a.py",))


def test_independent_wrapper_normalizer_is_two_phase_and_cpre_idempotent() -> None:
    c_pre = authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
        _evidence_wrapper_raw()
    )
    literal = _literal_phase_wrapper(c_pre)
    assert len(authorization.AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS) == 12
    assert (
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
            c_pre
        )
        == c_pre
    )
    assert literal != c_pre
    assert (
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
            literal
        )
        == c_pre
    )


def test_post_literal_replay_restores_exact_cpre_fact_and_authorization_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    c_pre = authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
        _evidence_wrapper_raw()
    )
    literal = _literal_phase_wrapper(c_pre)
    _populate_replay_root(tmp_path, c_pre)
    monkeypatch.setattr(authorization, "_ROOT", tmp_path)

    c_pre_facts = authorization.replay_authorization_source_facts_v180r12r4()
    c_pre_authorization = frozen(source_facts=c_pre_facts)
    (tmp_path / _EVIDENCE_RELATIVE_PATH).write_bytes(literal)
    literal_facts = authorization.replay_authorization_source_facts_v180r12r4()
    literal_authorization = frozen(source_facts=literal_facts)

    expected_wrapper_fact = {
        "relative_path": _EVIDENCE_RELATIVE_PATH,
        "byte_count": len(c_pre),
        "sha256": hashlib.sha256(c_pre).hexdigest(),
    }
    assert next(
        row for row in c_pre_facts if row["relative_path"] == _EVIDENCE_RELATIVE_PATH
    ) == expected_wrapper_fact
    assert literal_facts == c_pre_facts
    assert literal_authorization.execution_authorization_id == (
        c_pre_authorization.execution_authorization_id
    )
    assert literal_authorization.canonical_bytes == c_pre_authorization.canonical_bytes


def test_wrapper_normalizer_rejects_missing_duplicate_alias_expression_and_mixed_phase(
) -> None:
    c_pre = authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
        _evidence_wrapper_raw()
    )
    spans = authorization._authorization_evidence_literal_spans(c_pre)  # noqa: SLF001
    start, end, _replacement = spans["EXPECTED_AUTHORIZATION_ID"]
    line_start = c_pre.rfind(b"\n", 0, start) + 1
    line_end = c_pre.find(b"\n", end) + 1
    missing = c_pre[:line_start] + c_pre[line_end:]
    duplicate = c_pre + (
        b'\nEXPECTED_AUTHORIZATION_ID = "22222222222222222222222222222222'
        b'22222222222222222222222222222222"\n'
    )
    alias = c_pre[:start] + b"ZERO_ID" + c_pre[end:]
    expression = c_pre[:start] + b'"0" * 64' + c_pre[end:]
    adjacent = (
        c_pre[:start]
        + b'"00000000000000000000000000000000" '
        + b'"00000000000000000000000000000000"'
        + c_pre[end:]
    )
    mixed = c_pre[:start] + b'"' + b"1" * 64 + b'"' + c_pre[end:]
    for hostile in (missing, duplicate, alias, expression, adjacent, mixed):
        with pytest.raises(
            authorization.CampaignMeasurementExecutionAuthorizationV180R12R4Error
        ):
            authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
                hostile
            )


def test_nonallowlisted_wrapper_drift_cannot_pass_exact_external_auth_join(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    c_pre = authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
        _evidence_wrapper_raw()
    )
    drifted = c_pre.replace(
        b"External, non-bootstrapping evidence",
        b"External non-bootstrapping evidence",
        1,
    )
    assert drifted != c_pre
    assert (
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
            drifted
        )
        != c_pre
    )

    _populate_replay_root(tmp_path, c_pre)
    monkeypatch.setattr(authorization, "_ROOT", tmp_path)
    expected_facts = authorization.replay_authorization_source_facts_v180r12r4()
    expected = frozen(source_facts=expected_facts)
    (tmp_path / _EVIDENCE_RELATIVE_PATH).write_bytes(drifted)
    observed_facts = authorization.replay_authorization_source_facts_v180r12r4()
    observed = frozen(source_facts=observed_facts)

    assert observed_facts != expected_facts
    expected_exact_join = (
        expected.execution_authorization_id,
        len(expected.canonical_bytes),
        hashlib.sha256(expected.canonical_bytes).hexdigest(),
    )
    observed_exact_join = (
        observed.execution_authorization_id,
        len(observed.canonical_bytes),
        hashlib.sha256(observed.canonical_bytes).hexdigest(),
    )
    assert observed_exact_join != expected_exact_join


def test_authorization_one_shot_failure_and_gate_boundaries_are_exact() -> None:
    document = frozen().to_document()
    assert set(document["campaign_subject_result_fields"]) == (
        protocol.CAMPAIGN_SUBJECT_RESULT_FIELDS
    )
    assert document[
        "campaign_subject_result_echoes_authorization_evidence_and_transport_provenance"
    ] is True
    assert document["successful_campaign_counter_record_count"] == 9
    assert document["successful_campaign_work_vector_count"] == 1
    assert document["successful_campaign_comparison_vector_count"] == 1
    assert document["successful_campaign_projection_proof_count"] == 1
    assert document["successful_campaign_native_zero_attestation_count"] == 1
    assert document["native_zero_required_for_each_zero_valued_path"] is False
    assert document["native_zero_comparison_axis"] == "kernel_transition_calls"
    assert document["projection_proof_references_native_zero_attestation"] is True
    assert document[
        "attempt_record_o_excl_and_fsync_before_cgroup_creation_or_authorized_measured_subject_input_read"
    ] is True
    assert document["attempt_record_excludes_cgroup_topology_receipt_id"] is True
    assert document["terminal_evidence_causal_join_rules"] == list(
        protocol.EVIDENCE_CAUSAL_JOIN_RULES
    )
    assert document[
        "final_subject_references_campaign_attempt_record_not_semantic_receipts"
    ] is True
    assert document["semantic_receipt_evidence_subject_is_campaign_attempt_record"]
    assert document["semantic_receipt_evidence_subject_is_future_final_subject"] is False
    assert document["semantic_receipt_count_bound_to_attempt_record"] == 297
    assert document[
        "replay_subject_binds_attempt_final_subject_and_exact_297_semantic_receipts"
    ] is True
    assert document["subject_write_io_receipt_source_evidence_type"] == (
        "CAMPAIGN_SUBJECT_RESULT"
    )
    assert document["subject_write_io_receipt_target_evidence_type"] == (
        "WORKER_PIDFD_BIRTH_RECEIPT"
    )
    assert document["subject_write_io_receipt_references_future_replay_subject"] is False
    assert document["replay_subject_first_consumer_event_kind"] == "SUBJECT_COMMIT"
    assert document["subject_readback_io_receipt_source_evidence_type"] == (
        "CAMPAIGN_SUBJECT_RESULT"
    )
    assert document["subject_readback_io_receipt_target_evidence_type"] == (
        "SUPERVISOR_PIDFD_BIRTH_RECEIPT"
    )
    assert document["successful_event_evidence_id_issued_before_event_append_required"]
    assert document["successful_event_future_evidence_reference_forbidden"]
    assert document["attempt_identity_is_concurrency_and_replay_lock"] is True
    assert document[
        "success_failure_timeout_cap_violation_or_crash_consumes_attempt_identity"
    ] is True
    assert document["same_attempt_identity_rerun_forbidden"] is True
    assert document["terminal_failure_and_runtime_cas_mutually_exclusive"] is True
    assert document[
        "campaign_failure_forbidden_at_terminal_publication_attempt_entry"
    ] is True
    assert document[
        "terminal_publication_attempt_entry_precedes_open_parent_and_o_excl"
    ] is True
    assert document["post_terminal_child_or_bootstrap_error_is_outer_launch_failure"] is True
    assert document["pending_terminal_requires_measurement_launch_receipt_for_acceptance"] is True
    assert document["failure_prefix_event_chain_must_be_retained"] is True
    assert document["V180R12R2_COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["terminal_counter_closure_status_on_success"] == (
        "PENDING_INDEPENDENT_REPLAY"
    )
    assert document["independent_verifier_is_only_counter_pass_authority"] is True
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert document["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert document["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False


def test_authorization_identity_phase_and_content_identity_are_replayable() -> None:
    first = frozen()
    second = frozen()
    assert first.canonical_bytes == second.canonical_bytes
    document = first.to_document()
    protocol_anchor_phase = (
        authorization.EXPECTED_PROTOCOL_ID != authorization.ZERO_ID
    )
    self_identity_phase = (
        authorization.EXPECTED_AUTHORIZATION_ID != authorization.ZERO_ID
    )
    assert document["identity_literals_frozen"] is self_identity_phase
    if protocol_anchor_phase:
        assert all(
            value != authorization.ZERO_ID
            for value in (
                authorization.EXPECTED_PROTOCOL_ID,
                authorization.EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID,
            )
        )
    else:
        assert authorization.EXPECTED_PROTOCOL_ID == authorization.ZERO_ID
        assert (
            authorization.EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID
            == authorization.ZERO_ID
        )
    if self_identity_phase:
        assert authorization.EXPECTED_CANONICAL_BYTE_COUNT > 0
        assert authorization.EXPECTED_SOURCE_CLOSURE_BYTE_COUNT > 0
        assert authorization.EXPECTED_SOURCE_CLOSURE_FILE_COUNT > 0
        assert all(
            value != authorization.ZERO_ID
            for value in (
                authorization.EXPECTED_CANONICAL_SHA256,
                authorization.EXPECTED_SOURCE_CLOSURE_ID,
                authorization.EXPECTED_SOURCE_CLOSURE_SHA256,
            )
        )
    else:
        assert authorization.EXPECTED_CANONICAL_BYTE_COUNT == 0
        assert authorization.EXPECTED_SOURCE_CLOSURE_BYTE_COUNT == 0
        assert authorization.EXPECTED_SOURCE_CLOSURE_FILE_COUNT == 0
        assert all(
            value == authorization.ZERO_ID
            for value in (
                authorization.EXPECTED_CANONICAL_SHA256,
                authorization.EXPECTED_SOURCE_CLOSURE_ID,
                authorization.EXPECTED_SOURCE_CLOSURE_SHA256,
            )
        )
    payload = dict(document)
    identity = payload.pop("execution_authorization_id")
    assert identity == domains.extension_content_id_v180r12r4(
        domains.CONSTRUCTION_K7_EXECUTION_AUTHORIZATION_V180R12R4_DOMAIN,
        payload,
    )


def test_authorization_rejects_foreign_wrapper_and_capability_drift() -> None:
    value = frozen()
    with pytest.raises(
        authorization.CampaignMeasurementExecutionAuthorizationV180R12R4Error
    ):
        authorization.CampaignMeasurementExecutionAuthorizationV180R12R4(
            object(), value.canonical_bytes, value.execution_authorization_id
        )
    capability = runtime_capability_fact()
    capability["pidfd_wait_present"] = False
    with pytest.raises(protocol.CampaignMeasurementProtocolV180R12R4Error):
        authorization.build_campaign_measurement_execution_authorization_v180r12r4(
            cgroup_parent_fact=cgroup_parent_fact(),
            runtime_capability_fact=capability,
        )


def test_authorization_echoes_prelaunch_evidence_durable_and_arithmetic_contracts() -> None:
    document = frozen().to_document()
    assert document["prelaunch_contract"] == protocol.prelaunch_contract_v180r12r4()
    assert document["failed_dispatch_repair_lineage"] == (
        protocol.failed_dispatch_repair_lineage_contract_v180r12r4()
    )
    assert document["failed_external_replay_repair_lineage"] == (
        protocol.failed_external_replay_repair_lineage_contract_v180r12r4()
    )
    assert document["failed_scientific_birth_repair_lineage"] == (
        protocol.failed_scientific_birth_repair_lineage_contract_v180r12r4()
    )
    failed_external_replay = document["failed_external_replay_repair_lineage"]
    failed_scientific_birth = document[
        "failed_scientific_birth_repair_lineage"
    ]
    assert failed_external_replay["scientific_attempt_record_present"] is False
    assert failed_external_replay["scientific_occurrence_started"] is False
    assert failed_external_replay["campaign_actual_measurement"] is False
    assert failed_external_replay["measurement_cgroup_created"] is False
    assert failed_external_replay["same_campaign_attempt_rerun_forbidden"] is True
    assert failed_external_replay["same_launch_attempt_rerun_forbidden"] is True
    assert failed_external_replay[
        "source_bound_authorization_replay_must_use_c_pre_normalized_sources"
    ] is True
    assert failed_external_replay[
        "raw_post_literal_wrapper_authorization_replay_forbidden"
    ] is True
    assert document["source_bound_runner_execution_envelope_contract"] == (
        protocol.source_bound_runner_execution_envelope_contract_v180r12r4()
    )
    assert document["prelaunch_contract"]["precompiled_runner_module_contract"] == (
        document["source_bound_runner_execution_envelope_contract"]
    )
    assert document["failed_v180r12r3_identity_rerun_forbidden"] is True
    assert document["failed_v180r12r3r1_identity_rerun_forbidden"] is True
    assert document["failed_v180r12r3r2_identity_rerun_forbidden"] is True
    assert document["fresh_v180r12r4_physical_paths_and_identities_required"]
    assert document["repair_scope"] == protocol.V180R12R4_REPAIR_SCOPE
    assert document["repair_scope"] == failed_scientific_birth["repair_scope"]
    assert failed_external_replay["repair_scope"] == (
        "AUTHORIZATION_EVIDENCE_WRAPPER_SOURCE_FACT_NORMALIZATION_ONLY"
    )
    assert failed_scientific_birth["scientific_attempt_record_present"] is True
    assert failed_scientific_birth["scientific_occurrence_started"] is True
    assert failed_scientific_birth["campaign_counter_records_issued"] is False
    assert document[
        "repair_changes_campaign_path_roles_event_schedule_evidence_cardinality_or_reducers"
    ] is False
    assert len(document["source_closure_contract"]["required_static_roots"]) == 22
    assert protocol.V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH in document[
        "source_closure_contract"
    ]["required_static_roots"]
    assert protocol.V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH in document[
        "source_closure_contract"
    ]["required_static_roots"]
    assert protocol.V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH in document[
        "source_closure_contract"
    ]["required_static_roots"]
    assert (
        document["resource_caps"]["sock_seqpacket_buffer_request_bytes"]
        == authorization.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        == protocol.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        == 1_048_576
    )
    assert (
        document["resource_caps"]["sock_seqpacket_effective_min_bytes"]
        == authorization.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        == protocol.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        == 2_097_152
    )
    assert document["resource_caps"][
        "sock_seqpacket_buffer_applies_to_both_endpoints_of_both_pairs"
    ] is True
    assert document["terminal_evidence_inventory_contract"] == (
        protocol.evidence_inventory_contract_v180r12r4()
    )
    assert document["durable_artifact_contract"] == (
        protocol.durable_artifact_contract_v180r12r4()
    )
    assert document["success_durable_artifact_contract"] == (
        protocol.success_durable_artifact_contract_v180r12r4()
    )
    assert document["success_durable_artifact_contract"]["producer_write_order"] == [
        "EVIDENCE_INVENTORY",
        "EXECUTION_CLOSURE",
        "OS_RECEIPT",
        "LEDGER_CLOSURE",
        "TERMINAL",
    ]
    assert len(document["success_durable_artifact_contract"]["artifact_rows"]) == 4
    assert document["failure_observation_contract"] == (
        protocol.failure_observation_contract_v180r12r4()
    )
    assert document["failure_observation_contract"][
        "failure_artifact_observation_row_cap"
    ] == 4_112
    assert document["failure_observation_contract"][
        "failure_artifact_metadata_byte_cap"
    ] == 2 * 1024 * 1024
    assert document["failure_observation_contract"][
        "failure_directory_entry_name_total_byte_cap"
    ] == 256 * 1024
    assert authorization.FAILURE_CGROUP_OBSERVATION_FIELDS == (
        protocol.FAILURE_CGROUP_OBSERVATION_FIELDS
    )
    assert authorization.FAILURE_CGROUP_NODE_OBSERVATION_FIELDS == (
        protocol.FAILURE_CGROUP_NODE_OBSERVATION_FIELDS
    )
    assert authorization.FAILURE_CGROUP_NODE_ROLES == (
        protocol.FAILURE_CGROUP_NODE_ROLES
    ) == ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
    assert authorization.FAILURE_CGROUP_NODE_STATES == (
        protocol.FAILURE_CGROUP_NODE_STATES
    ) == ("ABSENT", "LINKED_OR_NONDIR", "PRESENT", "READ_ERROR")
    assert document["failure_observation_contract"][
        "failure_cgroup_node_observation_fields"
    ] == list(protocol.FAILURE_CGROUP_NODE_OBSERVATION_FIELDS)
    assert document["failure_observation_contract"][
        "failure_worst_case_names_plus_bounded_metadata_fit_emergency_reserve"
    ] is True
    assert document["failure_observations_in_success_evidence_inventory"] is False
    assert document[
        "failure_artifact_observations_are_campaign_success_authority"
    ] is False
    assert document[
        "failure_cgroup_observation_is_campaign_success_receipt"
    ] is False
    assert authorization.VERIFICATION_FAILURE_SCHEMA == (
        protocol.VERIFICATION_FAILURE_SCHEMA
    )
    assert authorization.VERIFICATION_FAILURE_FIELDS == (
        protocol.VERIFICATION_FAILURE_FIELDS
    )
    assert authorization.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS == (
        protocol.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
    )
    assert authorization.VERIFICATION_FAILURE_OBSERVATION_BOUNDARY == (
        "IMMEDIATELY_BEFORE_FAILURE_WRITE"
    )
    assert document["terminal_evidence_inventory_contract"]["typed_document_count"] == 328
    assert document["terminal_evidence_inventory_contract"][
        "nonnull_event_evidence_count"
    ] == 317
    assert document["terminal_evidence_inventory_contract"][
        "null_event_evidence_count"
    ] == 308
    assert document["successful_measurement_arithmetic"]["input_total_byte_count"] == 202_507
    assert document["trusted_observer_owns_all_durable_event_files_and_acks"] is True
    assert document["measured_children_append_durable_event_files"] is False


def test_authorization_echoes_exact_90_plus_9_equals_99_and_positive_scope() -> None:
    document = frozen().to_document()
    assert document["predecessor_occurrence_authoritative_receipt_count"] == 90
    assert document["predecessor_campaign_authoritative_receipt_count"] == 0
    assert document["predecessor_campaign_scope_structural_obligation_count"] == 9
    assert document["successful_campaign_authoritative_receipt_count"] == 9
    assert document["successful_combined_authoritative_receipt_count"] == 99
    assert document["terminal_pending_authoritative_receipt_join"] == {
        "counter_status": "PENDING_INDEPENDENT_REPLAY",
        "predecessor_occurrence_receipt_count": 90,
        "campaign_actual_receipt_count": 9,
        "combined_authoritative_receipt_count": 99,
    }
    assert document["independent_verifier_pass_authoritative_receipt_join"] == {
        **document["terminal_pending_authoritative_receipt_join"],
        "counter_status": "PASS",
    }
    assert document["predecessor_structural_nine_are_successor_actual_receipts"] is False
    assert document["successful_campaign_path_values_strictly_positive"] is True
    assert document["successful_zero_valued_campaign_path_receipt_count"] == 0
    assert document[
        "zero_valued_campaign_path_receipts_if_present_are_observations"
    ] is True
    assert document["native_zero_observed_false_for_all_nine_campaign_paths"] is True
    assert document["kernel_transition_calls_is_linux_syscall_count"] is False
    assert document["native_zero_is_open_world_no_kernel_call_claim"] is False


def test_authorization_attempt_boundary_excludes_only_trusted_preauthorization_reads(
) -> None:
    document = frozen().to_document()
    assert document[
        "attempt_record_o_excl_and_fsync_before_cgroup_creation_or_authorized_measured_subject_input_read"
    ] is True
    assert document[
        "preauthorization_predecessor_and_source_validation_reads_are_trusted_excluded_overhead"
    ] is True
    assert document["preauthorization_validation_reads_are_campaign_actual_measurement"] is False
    assert document["supervisor_first_measured_source_reads_occur_after_attempt_open"] is True
    freshness = document["durable_artifact_contract"]
    assert freshness[
        "any_preexisting_blocker_in_corresponding_precreate_matrix_forbids_same_identity"
    ] is True
    matrices = {
        row["stage"]: row for row in freshness["freshness_stage_matrices"]
    }
    measurement_child = matrices["MEASUREMENT_ATTEMPT_PRECREATE"]
    assert protocol.PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH in (
        measurement_child["must_be_present_exact"]
    )
    assert protocol.PRELAUNCH_MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH in (
        measurement_child["must_be_absent"]
    )
    verification_child = matrices["VERIFICATION_ATTEMPT_PRECREATE"]
    assert protocol.PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH in (
        verification_child["must_be_present_exact"]
    )
    assert protocol.PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH in (
        verification_child["must_be_absent"]
    )
    assert freshness[
        "old_launch_failure_cannot_be_superseded_by_direct_child_invocation"
    ] is True
    assert freshness["resume_from_partial_state_forbidden"] is True
