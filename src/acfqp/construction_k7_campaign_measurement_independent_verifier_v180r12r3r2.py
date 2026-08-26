"""Producer-free independent verification of the V180r12r3r2 terminal.

The module intentionally does not import the finalizer, supervisor, worker, or
campaign-measurement ledger kernel.  It rebuilds the frozen operation/event
schedule, evidence graph, nine accounting chains, projection, and bounded
native-zero directly from the canonical bytes embedded in the pending
terminal.  Only the verification object issued here may promote the V180r12r3r2
counter gate to ``PASS``; V180r13--V180r16 remain unexecuted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import stat
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_domain_registry_extension_v180r12r3r2 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r3r2e as evidence_domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "1.0.0"
TERMINAL_SCHEMA = "acfqp.campaign_measurement_terminal.v180r12r3r2"
VERIFICATION_SCHEMA = "acfqp.campaign_measurement_verification.v180r12r3r2"
EVIDENCE_INVENTORY_BUNDLE_SCHEMA = (
    "acfqp.campaign_evidence_inventory_bundle.v180r12r3r2"
)
OS_RECEIPT_BUNDLE_SCHEMA = "acfqp.campaign_os_receipt_bundle.v180r12r3r2"
MEASUREMENT_LAUNCH_ATTEMPT_SCHEMA = (
    "acfqp.v180r12r3r2_prelaunch_launch_attempt.v1"
)
MEASUREMENT_LAUNCH_RECEIPT_SCHEMA = (
    "acfqp.v180r12r3r2_prelaunch_launch_receipt.v1"
)
MEASUREMENT_LAUNCH_ADDRESS_SPACE_HARD_CAP_BYTES = 16 * 1024 * 1024 * 1024
MEASUREMENT_LAUNCH_WALL_TIMEOUT_SECONDS = 14_400
MEASUREMENT_CAMPAIGN_CLEANUP_GRACE_SECONDS = 600
MEASUREMENT_LAUNCH_TERMINATION_GRACE_SECONDS = 10
NANOSECONDS_PER_SECOND = 1_000_000_000
SUBJECT_RESULT_BYTE_CAP = 1 * 1024 * 1024
SUBJECT_RESULT_RUNTIME_BYTE_CAP = 768 * 1024
FRAME_BYTE_CAP = 1 * 1024 * 1024
MEASUREMENT_LAUNCH_ATTEMPT_FIELDS = frozenset(
    "schema launch_rule_id target repository_root materialization_terminal_id "
    "materialization_terminal_byte_count materialization_terminal_sha256 "
    "launch_manifest_sha256 child_argv child_environment "
    "address_space_hard_cap_bytes address_space_cap_applied_before_child_exec "
    "wall_timeout_seconds attempt_lock_written_before_child_exec "
    "same_target_identity_rerun_forbidden preauthorization_supervision "
    "campaign_actual_measurement scientific_occurrence_started "
    "authorized_child_measurement_execution_attempted "
    "authorized_child_measurement_execution_completed "
    "producer_free_verification_attempted producer_free_verification_completed "
    "launch_attempt_id".split()
)
MEASUREMENT_LAUNCH_RECEIPT_FIELDS = frozenset(
    "schema launch_rule_id launch_attempt_id target return_code timed_out "
    "child_stdout child_stderr progress_observations "
    "same_target_identity_rerun_forbidden attempt_lock_preserved "
    "address_space_hard_cap_bytes wall_timeout_seconds monotonic_origin_ns "
    "hard_deadline_ns campaign_deadline_ns campaign_cleanup_grace_seconds "
    "termination_grace_seconds measurement_cgroup_cleanup_observations "
    "preauthorization_supervision "
    "campaign_actual_measurement authorized_child_measurement_execution_attempted "
    "authorized_child_measurement_execution_completed "
    "producer_free_verification_attempted producer_free_verification_completed "
    "COUNTER_COMPLETENESS_GATE WORKLOAD_ECONOMICS_GATE SCALAR_CALIBRATION_GATE "
    "BREAK_EVEN_GATE official_execution_allowed success failure_type failure_message "
    "launch_receipt_id".split()
)
MEASUREMENT_CGROUP_OBSERVATION_PHASES = (
    "BEFORE_POPEN", "CLEANUP", "AFTER_CHILD",
)
MEASUREMENT_CGROUP_OBSERVATION_FIELDS = frozenset(
    "phase applicable campaign_attempt_id root_name ownership_acquired "
    "root_state root_mode root_nlink root_device root_inode root_populated "
    "root_process_count supervisor_state worker_state kill_attempted "
    "kill_succeeded wait_empty_attempted wait_empty_succeeded "
    "remove_attempted remove_succeeded residual_tree_or_process_possible "
    "error_type error_message".split()
)
MEASUREMENT_LAUNCH_PROGRESS_NAMES = frozenset(
    {
        "attempt", "receipt", "launch_failure", "runtime_cas", "output_root",
        "terminal", "evidence_inventory", "execution_closure", "os_receipt",
        "ledger_closure", "measurement_failure", "verification",
        "verification_failure", "retained_replay",
    }
)
_EMPTY_LAUNCH_STREAM = {
    "byte_count": 0,
    "sha256": hashlib.sha256(b"").hexdigest(),
    "retained_prefix_hex": "",
    "retained_prefix_truncated": False,
}
SUCCESS_ARTIFACT_SCHEMA_ROWS = (
    (
        "evidence_inventory", EVIDENCE_INVENTORY_BUNDLE_SCHEMA,
        "campaign_evidence_inventory_bundle_id",
        "campaign_evidence_inventory_bundle",
    ),
    (
        "execution_closure", "acfqp.campaign_execution_closure.v180r12r3r2",
        "campaign_execution_closure_id", "campaign_execution_closure",
    ),
    (
        "os_receipt", OS_RECEIPT_BUNDLE_SCHEMA,
        "campaign_os_receipt_bundle_id", "campaign_os_receipt_bundle",
    ),
    (
        "ledger_closure", "acfqp.campaign_measurement_ledger_closure.v180r12r3r2",
        "campaign_ledger_closure_id", "campaign_ledger_closure",
    ),
)
EVIDENCE_INVENTORY_BUNDLE_FIELDS = frozenset(
    "schema schema_version protocol_id authorization_id attempt_id "
    "evidence_document_count evidence_document_type_counts "
    "ordered_evidence_document_ids evidence_documents "
    "campaign_evidence_inventory_bundle_id".split()
)
OS_RECEIPT_BUNDLE_FIELDS = frozenset(
    "schema schema_version protocol_id authorization_id attempt_id "
    "campaign_evidence_inventory_bundle_id os_receipt_document_count "
    "os_receipt_schema_counts ordered_os_receipt_ids os_receipt_documents "
    "campaign_os_receipt_bundle_id".split()
)
TERMINAL_FIELDS = frozenset(
    "schema schema_version scope scope_model protocol_id authorization_id "
    "authorization_evidence_id attempt_id "
    "prelaunch_materialization_terminal_id prelaunch_launch_manifest_sha256 "
    "precompiled_source_bundle_sha256 "
    "prelaunch_launch_rule_id measurement_launch_attempt_id "
    "subject_id campaign_operation_manifest_id "
    "native_zero_source_manifest_id native_zero_import_inventory_id "
    "campaign_execution_closure_id campaign_execution_closure_byte_count "
    "campaign_execution_closure_sha256 campaign_evidence_inventory_bundle_id "
    "campaign_evidence_inventory_bundle_byte_count "
    "campaign_evidence_inventory_bundle_sha256 campaign_os_receipt_bundle_id "
    "campaign_os_receipt_bundle_byte_count campaign_os_receipt_bundle_sha256 "
    "campaign_ledger_closure_id campaign_ledger_closure_byte_count "
    "campaign_ledger_closure_sha256 campaign_measurement_ledger "
    "os_receipt_documents os_receipt_ids os_receipt_schema_counts event_count "
    "evidence_document_count os_receipt_document_count "
    "campaign_path_receipt_count campaign_counter_record_count "
    "campaign_work_vector_count campaign_comparison_vector_count "
    "campaign_projection_proof_count campaign_native_zero_attestation_count "
    "predecessor_occurrence_authoritative_receipt_count "
    "successor_campaign_authoritative_receipt_count "
    "combined_successor_authoritative_receipt_count "
    "authoritative_receipt_arithmetic_90_plus_9_equals_99 "
    "raw_event_evidence_and_os_receipts_replayed route_free_campaign_accounting "
    "all_nine_campaign_paths_strictly_positive "
    "independent_native_zero_attestation_present independent_verification_present "
    "V180R12R3R2_CAMPAIGN_COUNTER_CLOSURE_STATUS COUNTER_COMPLETENESS_GATE "
    "WORKLOAD_ECONOMICS_GATE SCALAR_CALIBRATION_GATE BREAK_EVEN_GATE "
    "OFFICIAL_EXECUTION_GATE v180r13_weight_agnostic_economics_input_ready "
    "official_scalar_cost official_N_break_even official_execution_allowed "
    "scientific_success_claimed output_bytes_fixed_point "
    "campaign_measurement_terminal_id".split()
)
VERIFICATION_FIELDS = frozenset(
    "schema schema_version scope scope_model protocol_id authorization_id "
    "authorization_evidence_id attempt_id "
    "prelaunch_materialization_terminal_id prelaunch_launch_manifest_sha256 "
    "precompiled_source_bundle_sha256 "
    "prelaunch_launch_rule_id measurement_launch_attempt_id subject_id "
    "measurement_launch_receipt_id measurement_launch_receipt_byte_count "
    "measurement_launch_receipt_sha256 "
    "runtime_role_exit_origin_guard_status "
    "measurement_launch_receipt_directly_observes_origin_guard "
    "frozen_bootstrap_post_dispatch_origin_guard_transitively_supported "
    "campaign_measurement_terminal_id campaign_measurement_terminal_byte_count "
    "campaign_measurement_terminal_sha256 campaign_ledger_closure_id "
    "campaign_ledger_closure_byte_count campaign_ledger_closure_sha256 "
    "campaign_evidence_inventory_bundle_id "
    "campaign_evidence_inventory_bundle_byte_count "
    "campaign_evidence_inventory_bundle_sha256 campaign_operation_manifest_id "
    "native_zero_source_manifest_id native_zero_import_inventory_id "
    "campaign_execution_closure_id campaign_execution_closure_byte_count "
    "campaign_execution_closure_sha256 campaign_os_receipt_bundle_id "
    "campaign_os_receipt_bundle_byte_count campaign_os_receipt_bundle_sha256 "
    "campaign_receipt_set_id campaign_work_vector_id "
    "campaign_comparison_vector_id campaign_projection_proof_id "
    "campaign_native_zero_attestation_id os_receipt_ids event_count "
    "event_evidence_nonnull_count event_evidence_null_count "
    "evidence_document_count os_receipt_document_count "
    "campaign_path_receipt_count campaign_counter_record_count "
    "campaign_work_vector_count campaign_comparison_vector_count "
    "campaign_projection_proof_count campaign_native_zero_attestation_count "
    "predecessor_occurrence_authoritative_receipt_count "
    "successor_campaign_authoritative_receipt_count "
    "combined_successor_authoritative_receipt_count "
    "authoritative_receipt_arithmetic_90_plus_9_equals_99 "
    "exact_625_event_schedule_independently_replayed "
    "exact_328_evidence_inventory_independently_replayed "
    "exact_twelve_os_receipts_independently_replayed "
    "four_separate_durable_success_artifacts_independently_replayed "
    "exact_eight_io_transfer_graph_independently_replayed "
    "overlapping_mount_intervals_independently_replayed "
    "cgroup_topology_birth_reap_and_peak_independently_replayed "
    "nine_campaign_path_receipts_independently_rederived "
    "nine_campaign_counter_records_independently_rederived "
    "campaign_work_vector_independently_rederived "
    "campaign_comparison_vector_independently_rederived "
    "campaign_projection_proof_independently_rederived "
    "bounded_native_zero_attestation_independently_rederived "
    "native_zero_is_registered_planning_comparison_axis_only "
    "native_zero_is_not_an_os_syscall_count open_world_absence_claimed "
    "producer_module_imported finalizer_module_imported "
    "supervisor_module_imported worker_module_imported "
    "campaign_measurement_ledger_kernel_imported "
    "V180R12R3R2_CAMPAIGN_COUNTER_CLOSURE_STATUS COUNTER_COMPLETENESS_GATE "
    "WORKLOAD_ECONOMICS_GATE SCALAR_CALIBRATION_GATE BREAK_EVEN_GATE "
    "OFFICIAL_EXECUTION_GATE v180r13_weight_agnostic_economics_input_ready "
    "official_scalar_cost official_N_break_even official_execution_allowed "
    "scientific_success_claimed campaign_measurement_verification_id".split()
)
CAMPAIGN_SCOPE_KIND = "TEN_TERMINAL_AGGREGATION_MEASURED_REPLAY_SUCCESSOR"
CAMPAIGN_SCOPE_MODEL = "ROUTE_FREE_MEASURED_REPLAY_SUCCESSOR"
SUCCESS_EVENT_COUNT = 625
SUCCESS_NONNULL_EVIDENCE_COUNT = 317
SUCCESS_NULL_EVIDENCE_COUNT = 308
SUCCESS_EVIDENCE_DOCUMENT_COUNT = 328
MEMORY_MAX_BYTES = 16 * 1024 * 1024 * 1024
TERMINAL_INPUT_BYTE_COUNT = 199_755
VERIFICATION_INPUT_BYTE_COUNT = 2_752
TOTAL_STAGED_INPUT_BYTE_COUNT = 202_507
TERMINAL_INPUT_CONTENT_ID = (
    "aba966326ff9e245d1758c65d8c3103614dd1a5a7be96b86e5eb2306bade15f0"
)
VERIFICATION_INPUT_CONTENT_ID = (
    "551881bb9bc6baa8dfaa112228f9160986b8106572d6f3f6c85af49434ec14ee"
)
TERMINAL_INPUT_SHA256 = (
    "11c4431eb5aef1fa6d6805e38755d48ea252e7d3f26ba28f6bf9f4780029e6bf"
)
VERIFICATION_INPUT_SHA256 = (
    "95ef7a8b98ddf2ff8214c0eafef00d250430b19951184feb87b302c62dcd2c05"
)
REQUIRED_MEMFD_SEALS = (
    "F_SEAL_GROW",
    "F_SEAL_SEAL",
    "F_SEAL_SHRINK",
    "F_SEAL_WRITE",
)

CAMPAIGN_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)
SHARED_AXES = (
    "kernel_transition_calls",
    "nonkernel_compute_events",
    "output_bytes",
    "peak_mounted_bytes",
    "peak_working_bytes",
    "process_launches",
    "read_bytes",
    "staged_bytes",
)

HASH_OPERATION_FAMILIES = (
    ("SOURCE_SHA256", 2, "STAGE", "SUPERVISOR"),
    ("STAGED_SHA256", 2, "WORKER", "WORKER"),
    ("TOP_CONTENT_ID", 2, "WORKER", "WORKER"),
    ("INNER_CONTENT_ID", 129, "WORKER", "WORKER"),
    ("SUBJECT_CONTENT_ID", 1, "WORKER", "WORKER"),
    ("SUBJECT_READBACK_SHA256", 1, "COMMIT", "SUPERVISOR"),
)
INNER_CONTENT_ID_OPERATION_SUFFIXES = (
    *(f"source_receipt.{index:02d}" for index in range(5)),
    *(f"route_component_chain_receipt.{index:02d}" for index in range(12)),
    *(f"terminal_receipt.{index:02d}" for index in range(10)),
    *(f"terminal_shared_resource_receipt.{index:03d}" for index in range(90)),
    *(f"terminal_shared_resource_receipt_set.{index:02d}" for index in range(10)),
    "v180r7r1_construction_axis_receipt",
    "campaign_scope_structural_boundary",
)
SEMANTIC_HASH_OPERATION_LABELS = (
    "hash.source_file_sha256.terminal",
    "hash.source_file_sha256.verification",
    "hash.staged_file_sha256.terminal",
    "hash.staged_file_sha256.verification",
    "hash.top_content_id.terminal",
    "hash.top_content_id.verification",
    *(f"hash.inner_content_id.{suffix}" for suffix in INNER_CONTENT_ID_OPERATION_SUFFIXES),
    "hash.subject_result_id",
    "hash.subject_readback_sha256",
)
INTEGRITY_CHECK_OPERATION_LABELS = (
    "integrity.stage_source.terminal.stable_read",
    "integrity.stage_source.verification.stable_read",
    "integrity.stage_source.terminal.sha256",
    "integrity.stage_source.verification.sha256",
    "integrity.stage_source.terminal.memfd_seals",
    "integrity.stage_source.verification.memfd_seals",
    "integrity.worker_staged.terminal.sha256",
    "integrity.worker_staged.verification.sha256",
    "integrity.worker_staged.terminal.canonical_json",
    "integrity.worker_staged.verification.canonical_json",
    "integrity.worker_staged.terminal.top_content_id",
    "integrity.worker_staged.verification.top_content_id",
    *(f"integrity.worker_inner_content_id.{suffix}" for suffix in INNER_CONTENT_ID_OPERATION_SUFFIXES),
    "integrity.worker_inner_content_id.denominator_and_uniqueness",
    "integrity.worker_subject.canonical_json_and_content_id",
    "integrity.commit_subject.readback_size_and_sha256",
    "integrity.commit_subject.stable_mode_and_nlink",
)
INTEGRITY_OPERATION_FAMILIES = (
    ("STAGE_STABLE_INPUT", 2, "STAGE", "SUPERVISOR"),
    ("STAGE_SHA_MATCH", 2, "STAGE", "SUPERVISOR"),
    ("STAGE_SEAL_SET", 2, "STAGE", "SUPERVISOR"),
    ("WORKER_STAGED_SHA", 2, "WORKER", "WORKER"),
    ("WORKER_CANONICAL_JSON", 2, "WORKER", "WORKER"),
    ("WORKER_TOP_ID_MATCH", 2, "WORKER", "WORKER"),
    ("WORKER_INNER_ID_MATCH", 129, "WORKER", "WORKER"),
    ("WORKER_INNER_COUNT_AND_UNIQUENESS", 1, "WORKER", "WORKER"),
    ("WORKER_SUBJECT_CANONICAL_AND_ID", 1, "WORKER", "WORKER"),
    ("COMMIT_READBACK_SIZE_AND_SHA", 1, "COMMIT", "SUPERVISOR"),
    ("COMMIT_STABLE_MODE_AND_NLINK", 1, "COMMIT", "SUPERVISOR"),
)
PROTOCOL_CHECK_FAMILIES = (
    "TERMINAL_SCHEMA_AND_KEYSET",
    "VERIFICATION_SCHEMA_AND_KEYSET",
    "LINEAGE_IDS",
    "SOURCE_RECEIPT_ORDER",
    "ROUTE_COMPONENT_ORDER",
    "TERMINAL_RECEIPT_ORDER",
    "SHARED_SET_AND_RECEIPT_ORDER",
    "CONSTRUCTION_AXIS_SEPARATION",
    "STRUCTURAL_NINE_ZERO_ROUTE_FREE",
    "VERIFICATION_TERMINAL_BYTES_SHA_JOIN",
    "GLOBAL_DENOMINATORS",
    "PENDING_TO_PASS_TRANSITION",
    "FOUR_GATES_BLOCKER_AND_OFFICIAL",
    "SUCCESSOR_NONRETROACTIVITY_AND_IMPORT_BOUNDARY",
    "SUBJECT_SCHEMA_AND_KEYSET",
)
PROTOCOL_CHECK_OPERATION_LABELS = tuple(
    f"protocol.{family.lower()}" for family in PROTOCOL_CHECK_FAMILIES
)
SEMANTIC_RECEIPT_AUXILIARY_NAME_BY_KIND = {
    "SEMANTIC_HASH": "observed_sha256",
    "INTEGRITY_CHECK": "check_passed",
    "PROTOCOL_CHECK": "check_passed",
}
SNAPSHOT_TRANSPORT_INDEPENDENT_VERIFIER_BOUNDARY = {
    "ephemeral_transport_artifact_replayed": False,
    "resultant_stable_input_snapshot_receipt_count": 2,
    "resultant_snapshot_receipt_canonical_identity_replayed": True,
    "resultant_snapshot_role_byte_count_sha256_and_content_id_replayed": True,
    "transport_is_not_an_additional_measured_read": True,
    "transport_is_not_part_of_the_328_document_inventory": True,
}
_PRECOMPILED_SOURCE_ROW_FIELDS = {
    "source_kind", "name", "source_path", "is_package", "marshal_byte_count",
    "marshal_sha256",
}
_NATIVE_ZERO_SOURCE_FACT_FIELDS = {
    "schema", "schema_version", "prelaunch_launch_manifest_sha256",
    "precompiled_source_bundle_sha256", *_PRECOMPILED_SOURCE_ROW_FIELDS,
    "native_zero_source_fact_id",
}
_NATIVE_ZERO_OPERATION_SITE_FACT_FIELDS = {
    "schema", "schema_version", "attempt_id", "operation_id", "slot", "family",
    "ordinal", "phase", "actor_role", "instrumentation_site",
    "bound_source_fact_id", "comparison_axis_scope", "kernel_transition_calls",
    "not_an_os_syscall_count", "native_zero_operation_site_fact_id",
}
_NATIVE_ZERO_IMPORT_FACT_FIELDS = {
    "schema", "schema_version", "precompiled_source_bundle_sha256", "module",
    "source_path", "source_fact_id", "allowed_actor_roles",
    "application_precompiled_loader_only", "stdlib_runtime_boundary_excluded",
    "native_zero_import_fact_id",
}
_PRECOMPILED_TARGET_SOURCE_PATHS = {
    "measurement": "scripts/run_v180r12r3r2_campaign_measurement.py",
    "supervisor": "scripts/supervise_v180r12r3r2_campaign_measurement.py",
    "worker": "scripts/work_v180r12r3r2_campaign_measurement.py",
}
_OPERATION_SITE_TARGET_BY_ACTOR = {
    "OBSERVER": "measurement", "SUPERVISOR": "supervisor", "WORKER": "worker",
}


def _expected_semantic_receipt_auxiliary_values(
    *, kind: str, ordinal: int, subject: Mapping[str, Any]
) -> list[dict[str, str | bool]]:
    """Independently reconstruct one typed semantic receipt auxiliary row."""

    if kind == "SEMANTIC_HASH":
        if ordinal in {0, 2}:
            observed = subject.get("terminal_sha256")
        elif ordinal in {1, 3}:
            observed = subject.get("verification_sha256")
        elif ordinal == 4:
            observed = subject.get("terminal_content_id")
        elif ordinal == 5:
            observed = subject.get("verification_content_id")
        elif 6 <= ordinal < 135:
            inner = subject.get("inner_content_ids")
            if type(inner) is not list or len(inner) != 129:
                _fail("semantic hash inner-content authority changed")
            observed = inner[ordinal - 6].get("content_id")
        elif ordinal == 135:
            observed = subject.get("subject_result_id")
        elif ordinal == 136:
            observed = hashlib.sha256(canonical_json_bytes(subject)).hexdigest()
        else:  # pragma: no cover - exact schedule fixes the denominator
            _fail("semantic hash ordinal escaped its manifest")
        _cid(observed, "semantic receipt observed SHA256")
        return [{"name": "observed_sha256", "value": observed}]
    if kind in {"INTEGRITY_CHECK", "PROTOCOL_CHECK"}:
        return [{"name": "check_passed", "value": True}]
    _fail("semantic receipt kind escaped its auxiliary grammar")

_EVENT_FIELDS = {
    "schema",
    "protocol_id",
    "authorization_id",
    "attempt_id",
    "sequence",
    "phase",
    "actor_role",
    "operation_id",
    "event_kind",
    "previous_event_id",
    "monotonic_ns",
    "payload",
    "event_id",
}
_PAYLOAD_FIELDS = {
    "evidence_id",
    "outcome_code",
    "measured_value",
    "auxiliary_values",
}
_SUBJECT_RESULT_FIELDS = {
    "schema",
    "schema_version",
    "scope",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "execution_slot_id",
    "execution_nonce",
    "logical_occurrence_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
    "campaign_attempt_record_id",
    "terminal_content_id",
    "terminal_byte_count",
    "terminal_sha256",
    "verification_content_id",
    "verification_byte_count",
    "verification_sha256",
    "terminal_snapshot_id",
    "verification_snapshot_id",
    "memfd_stage_receipt_ids",
    "open_visibility_receipt_ids",
    "worker_birth_receipt_id",
    "operation_manifest_id",
    "inner_content_ids",
    "inner_content_id_count",
    "semantic_hash_operation_count",
    "integrity_check_operation_count",
    "protocol_check_operation_count",
    "route_component_counter_closure_status",
    "exact_v180r12r2_verification_replayed",
    "producer_module_imported",
    "producer_entrypoint_called",
    "v180r12r2_verifier_imported",
    "v180r12r2_verifier_called",
    "retroactive_v180r12r2_cost_claimed",
    "counter_completeness_gate",
    "workload_economics_gate",
    "scalar_calibration_gate",
    "break_even_gate",
    "official_execution_gate",
    "official_scalar_cost",
    "official_N_break_even",
    "official_execution_allowed",
    "subject_byte_count",
    "subject_result_id",
}
_OUTCOME_BY_KIND = {
    "ATTEMPT_OPEN": "OPEN",
    "INPUT_READ_INTENT": "INTENT",
    "INPUT_READ_OUTCOME": "SUCCESS",
    "STAGE_WRITE_INTENT": "INTENT",
    "STAGE_WRITE_OUTCOME": "SUCCESS",
    "MOUNT_VISIBILITY_OPEN": "OPEN",
    "MOUNT_VISIBILITY_CLOSE": "CLOSED",
    "SEMANTIC_HASH_INTENT": "INTENT",
    "SEMANTIC_HASH_OUTCOME": "SUCCESS",
    "INTEGRITY_CHECK_INTENT": "INTENT",
    "INTEGRITY_CHECK_OUTCOME": "PASS",
    "PROTOCOL_CHECK_INTENT": "INTENT",
    "PROTOCOL_CHECK_OUTCOME": "PASS",
    "PROCESS_BIRTH_INTENT": "INTENT",
    "PROCESS_BIRTH_OUTCOME": "SUCCESS",
    "PROCESS_REAP": "SUCCESS",
    "SUBJECT_WRITE_INTENT": "INTENT",
    "SUBJECT_WRITE_OUTCOME": "SUCCESS",
    "SUBJECT_COMMIT": "COMMITTED",
    "WINDOW_CLOSED": "CLOSED",
    "CGROUP_OBSERVED": "OBSERVED",
    "LEDGER_CLOSED": "CLOSED",
}
_COUNTER_PATH_BY_KIND = {
    "INPUT_READ_OUTCOME": "io.read_bytes",
    "STAGE_WRITE_OUTCOME": "io.staged_bytes",
    "MOUNT_VISIBILITY_OPEN": "io.mounted_bytes_peak",
    "SEMANTIC_HASH_OUTCOME": "common.hash_invocations",
    "INTEGRITY_CHECK_OUTCOME": "common.integrity_checks",
    "PROTOCOL_CHECK_OUTCOME": "common.protocol_checks",
    "PROCESS_BIRTH_OUTCOME": "process.launches",
    "SUBJECT_WRITE_OUTCOME": "io.output_bytes",
    "CGROUP_OBSERVED": "memory.working_bytes_peak",
}
_UNIT_KINDS = {
    "SEMANTIC_HASH_OUTCOME",
    "INTEGRITY_CHECK_OUTCOME",
    "PROTOCOL_CHECK_OUTCOME",
    "PROCESS_BIRTH_OUTCOME",
}
_DIRECT_SCHEMA_BY_KIND = {
    "ATTEMPT_OPEN": "acfqp.campaign_attempt_record.v180r12r3r2",
    "INPUT_READ_OUTCOME": "acfqp.campaign_io_transfer_receipt.v180r12r3r2",
    "STAGE_WRITE_OUTCOME": "acfqp.campaign_io_transfer_receipt.v180r12r3r2",
    "MOUNT_VISIBILITY_OPEN": "acfqp.campaign_fd_visibility_receipt.v180r12r3r2",
    "MOUNT_VISIBILITY_CLOSE": "acfqp.campaign_fd_visibility_receipt.v180r12r3r2",
    "SEMANTIC_HASH_OUTCOME": "acfqp.campaign_semantic_operation_receipt.v180r12r3r2",
    "INTEGRITY_CHECK_OUTCOME": "acfqp.campaign_semantic_operation_receipt.v180r12r3r2",
    "PROTOCOL_CHECK_OUTCOME": "acfqp.campaign_semantic_operation_receipt.v180r12r3r2",
    "PROCESS_BIRTH_OUTCOME": "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2",
    "PROCESS_REAP": "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2",
    "SUBJECT_WRITE_OUTCOME": "acfqp.campaign_io_transfer_receipt.v180r12r3r2",
    "SUBJECT_COMMIT": "acfqp.campaign_subject_commit_receipt.v180r12r3r2",
    "WINDOW_CLOSED": "acfqp.campaign_window_closure_receipt.v180r12r3r2",
    "CGROUP_OBSERVED": "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2",
}

_EVIDENCE_DESCRIPTOR = {
    "acfqp.campaign_attempt_record.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_ATTEMPT_RECORD_V180R12R3R2E_DOMAIN,
        "campaign_attempt_record_id",
        1,
    ),
    "acfqp.campaign_stable_input_snapshot.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_STABLE_INPUT_SNAPSHOT_V180R12R3R2E_DOMAIN,
        "stable_input_snapshot_id",
        2,
    ),
    "acfqp.campaign_io_transfer_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_IO_TRANSFER_RECEIPT_V180R12R3R2E_DOMAIN,
        "io_transfer_receipt_id",
        8,
    ),
    "acfqp.campaign_memfd_stage_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_MEMFD_STAGE_RECEIPT_V180R12R3R2E_DOMAIN,
        "memfd_stage_receipt_id",
        2,
    ),
    "acfqp.campaign_fd_visibility_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_FD_VISIBILITY_RECEIPT_V180R12R3R2E_DOMAIN,
        "fd_visibility_receipt_id",
        4,
    ),
    "acfqp.campaign_semantic_operation_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_SEMANTIC_OPERATION_RECEIPT_V180R12R3R2E_DOMAIN,
        "semantic_operation_receipt_id",
        297,
    ),
    "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_PIDFD_BIRTH_RECEIPT_V180R12R3R2E_DOMAIN,
        "pidfd_birth_receipt_id",
        2,
    ),
    "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_PIDFD_REAP_RECEIPT_V180R12R3R2E_DOMAIN,
        "pidfd_reap_receipt_id",
        2,
    ),
    "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_CGROUP_TOPOLOGY_RECEIPT_V180R12R3R2E_DOMAIN,
        "cgroup_topology_receipt_id",
        1,
    ),
    "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_CGROUP_OBSERVATION_RECEIPT_V180R12R3R2E_DOMAIN,
        "cgroup_observation_receipt_id",
        1,
    ),
    "acfqp.campaign_replay_subject_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_REPLAY_SUBJECT_RECEIPT_V180R12R3R2E_DOMAIN,
        "replay_subject_receipt_id",
        1,
    ),
    "acfqp.campaign_measurement_subject_result.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R3R2E_DOMAIN,
        "subject_result_id",
        1,
    ),
    "acfqp.campaign_subject_commit_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_SUBJECT_COMMIT_RECEIPT_V180R12R3R2E_DOMAIN,
        "subject_commit_receipt_id",
        1,
    ),
    "acfqp.campaign_window_closure_receipt.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_WINDOW_CLOSURE_RECEIPT_V180R12R3R2E_DOMAIN,
        "window_closure_receipt_id",
        1,
    ),
    "acfqp.campaign_execution_closure.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_EXECUTION_CLOSURE_V180R12R3R2E_DOMAIN,
        "campaign_execution_closure_id",
        1,
    ),
    "acfqp.campaign_operation_manifest.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_MANIFEST_V180R12R3R2E_DOMAIN,
        "campaign_operation_manifest_id",
        1,
    ),
    "acfqp.campaign_native_zero_source_manifest.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_MANIFEST_V180R12R3R2E_DOMAIN,
        "native_zero_source_manifest_id",
        1,
    ),
    "acfqp.campaign_native_zero_import_inventory.v180r12r3r2": (
        evidence_domains.CONSTRUCTION_K7_NATIVE_ZERO_IMPORT_INVENTORY_V180R12R3R2E_DOMAIN,
        "native_zero_import_inventory_id",
        1,
    ),
}

_EVIDENCE_FIELDS_BY_SCHEMA = {
    "acfqp.campaign_attempt_record.v180r12r3r2": frozenset(
        "schema schema_version scope protocol_id authorization_id attempt_id "
        "authorization_evidence_id prelaunch_materialization_terminal_id "
        "prelaunch_launch_manifest_sha256 prelaunch_launch_rule_id "
        "measurement_launch_attempt_id operation_id operation_manifest_id "
        "one_shot_attempt_opened "
        "campaign_attempt_record_id".split()
    ),
    "acfqp.campaign_stable_input_snapshot.v180r12r3r2": frozenset(
        "schema schema_version stable_input_fact_id role observed_byte_count "
        "observed_sha256 observed_content_id canonical_json_replayed "
        "read_from_frozen_input_only stable_input_snapshot_id".split()
    ),
    "acfqp.campaign_io_transfer_receipt.v180r12r3r2": frozenset(
        "schema schema_version scope protocol_id authorization_id attempt_id "
        "operation_id event_kind measured_value returned_chunk_byte_counts "
        "returned_chunk_count returned_byte_count source_evidence_id "
        "target_evidence_id transfer_identity transfer_complete "
        "io_transfer_receipt_id".split()
    ),
    "acfqp.campaign_memfd_stage_receipt.v180r12r3r2": frozenset(
        "schema schema_version input_snapshot_id role supervisor_fd worker_fd "
        "device inode byte_count sha256 observed_seals supervisor_cloexec "
        "worker_read_only anonymous_inode link_count write_probe_errno "
        "memfd_stage_receipt_id".split()
    ),
    "acfqp.campaign_fd_visibility_receipt.v180r12r3r2": frozenset(
        "schema schema_version attempt_id operation_id stage_receipt_id "
        "holder_process_birth_receipt_id holder_role role state "
        "designated_worker_fd expected_device expected_inode observed_device "
        "observed_inode visible read_only unexpected_stage_fds "
        "fd_visibility_receipt_id".split()
    ),
    "acfqp.campaign_semantic_operation_receipt.v180r12r3r2": frozenset(
        "schema schema_version attempt_id operation_id kind label family "
        "family_ordinal ordinal operation_manifest_id "
        "native_zero_source_manifest_id native_zero_import_inventory_id "
        "evidence_subject_id outcome_code measured_value auxiliary_values "
        "semantic_operation_receipt_id".split()
    ),
    "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2": frozenset(
        "schema schema_version cgroup_topology_receipt_id topology_receipt_id "
        "attempt_id operation_id process_role pid pidfd pidfd_device pidfd_inode "
        "clone3_flags target_cgroup_fd target_cgroup_device target_cgroup_inode "
        "target_cgroup_path proc_starttime_ticks pidfd_fdinfo_pid "
        "pidfd_fdinfo_nspid cgroup_membership_line "
        "membership_observed_before_work pidfd_cloexec pidfd_birth_receipt_id".split()
    ),
    "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2": frozenset(
        "schema schema_version pidfd_birth_receipt_id process_birth_receipt_id "
        "attempt_id operation_id process_role pid pidfd_device pidfd_inode "
        "proc_starttime_ticks waitid_idtype waitid_pidfd waitid_code "
        "waitid_status pidfd_readable leaf_populated_after_reap "
        "leaf_process_count_after_reap pidfd_reap_receipt_id".split()
    ),
    "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2": frozenset(
        "schema schema_version cgroup_parent_fact cgroup_parent_fact_sha256 "
        "delegated_parent measurement_root supervisor_leaf worker_leaf "
        "filesystem_type controllers subtree_control root_memory_max_bytes "
        "root_pids_max memory_max_bytes pids_max supervisor_leaf_pids_max "
        "worker_leaf_pids_max "
        "root_populated_before_birth root_process_count_before_birth "
        "leaf_process_counts_before_birth control_files "
        "no_internal_process_rule_satisfied sibling_leaf_topology "
        "cgroup_topology_receipt_id".split()
    ),
    "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2": frozenset(
        "schema schema_version cgroup_topology_receipt_id topology_receipt_id "
        "supervisor_reap_receipt_id worker_reap_receipt_id attempt_id "
        "operation_id memory_peak_bytes pids_peak memory_events pids_events "
        "populated_by_role process_count_by_role root_populated "
        "root_process_count supervisor_leaf_process_count "
        "worker_leaf_process_count control_file_readbacks "
        "observed_after_window_close memory_peak_is_observed_not_authorization_cap "
        "pids_peak_is_observed_not_authorization_cap "
        "cgroup_observation_receipt_id".split()
    ),
    "acfqp.campaign_replay_subject_receipt.v180r12r3r2": frozenset(
        "schema schema_version campaign_attempt_record_id operation_manifest_id "
        "native_zero_source_manifest_id native_zero_import_inventory_id "
        "terminal_snapshot_id verification_snapshot_id "
        "open_visibility_receipt_ids subject_result_id "
        "semantic_operation_receipt_ids subject_byte_count subject_sha256 "
        "producer_module_imported producer_entrypoint_called "
        "exact_v180r12r2_verification_replayed "
        "route_component_counter_closure_status fresh_replay_cost_only "
        "retroactive_v180r12r2_cost_claimed replay_subject_receipt_id".split()
    ),
    "acfqp.campaign_measurement_subject_result.v180r12r3r2": frozenset(
        _SUBJECT_RESULT_FIELDS
    ),
    "acfqp.campaign_subject_commit_receipt.v180r12r3r2": frozenset(
        "schema schema_version scope protocol_id authorization_id attempt_id "
        "operation_id subject_id replay_subject_receipt_id "
        "readback_transfer_receipt_id subject_byte_count stable_readback_verified "
        "subject_committed subject_commit_receipt_id".split()
    ),
    "acfqp.campaign_window_closure_receipt.v180r12r3r2": frozenset(
        "schema schema_version scope protocol_id authorization_id attempt_id "
        "operation_id subject_commit_receipt_id close_visibility_receipt_ids "
        "window_closed all_registered_mounts_closed window_closure_receipt_id".split()
    ),
    "acfqp.campaign_execution_closure.v180r12r3r2": frozenset(
        "schema schema_version scope scope_model protocol_id authorization_id "
        "attempt_id subject_id window_closed_event_id window_closure_receipt_id "
        "operation_manifest_id source_manifest_id import_inventory_id "
        "precompiled_source_bundle_sha256 "
        "comparison_axis kernel_transition_calls "
        "registered_planning_operation_site_fact_count "
        "kernel_transition_operation_site_fact_ids "
        "kernel_transition_import_fact_ids unregistered_operation_site_fact_ids "
        "unregistered_import_fact_ids "
        "registered_planning_comparison_ground_kernel_axis_only "
        "prelaunch_sealed_application_import_allowlist_only "
        "runtime_role_exit_origin_guard_required "
        "runtime_role_exit_origin_guard_status "
        "not_an_os_syscall_count unregistered_or_dynamic_sites_forbidden "
        "closed_registered_planning_operation_window_only "
        "open_world_absence_claimed "
        "execution_window_closed campaign_execution_closure_id".split()
    ),
    "acfqp.campaign_operation_manifest.v180r12r3r2": frozenset(
        "schema schema_version scope scope_model attempt_id operations "
        "operation_count semantic_hash_operation_count "
        "integrity_check_operation_count protocol_check_operation_count "
        "all_event_operation_ids_must_equal_manifest "
        "unregistered_operation_ids_forbidden campaign_operation_manifest_id".split()
    ),
    "acfqp.campaign_native_zero_source_manifest.v180r12r3r2": frozenset(
        "schema schema_version scope protocol_id authorization_id attempt_id "
        "operation_manifest_id prelaunch_launch_manifest_sha256 "
        "precompiled_source_bundle_sha256 source_fact_rows source_fact_ids "
        "registered_operation_site_fact_rows registered_operation_site_fact_ids "
        "unregistered_operation_site_fact_ids "
        "registered_planning_operation_site_manifest_complete "
        "unregistered_or_dynamic_sites_forbidden "
        "third_party_precompiled_sources_in_trusted_runtime_boundary "
        "open_world_operation_site_absence_claimed "
        "native_zero_source_manifest_id".split()
    ),
    "acfqp.campaign_native_zero_import_inventory.v180r12r3r2": frozenset(
        "schema schema_version scope protocol_id authorization_id attempt_id "
        "source_manifest_id precompiled_source_bundle_sha256 "
        "import_fact_rows import_fact_ids unregistered_import_fact_ids "
        "dynamic_import_fact_ids "
        "prelaunch_sealed_application_import_allowlist_complete "
        "runtime_role_exit_origin_guard_required "
        "stdlib_imports_in_trusted_runtime_boundary "
        "third_party_imports_in_trusted_runtime_boundary "
        "trusted_runtime_boundary_namespaces "
        "open_world_import_absence_claimed "
        "native_zero_import_inventory_id".split()
    ),
}

# Public, mechanically comparable schema manifest.  This is deliberately
# rebuilt here rather than imported from either runtime producer.  The order is
# worker-owned six, supervisor-owned four, then ledger-issued eight.
_EVIDENCE_FIELD_KEYSET_ROW_ORDER = (
    ("STABLE_INPUT_SNAPSHOT", "acfqp.campaign_stable_input_snapshot.v180r12r3r2"),
    ("MEMFD_STAGE_RECEIPT", "acfqp.campaign_memfd_stage_receipt.v180r12r3r2"),
    ("FD_VISIBILITY_RECEIPT", "acfqp.campaign_fd_visibility_receipt.v180r12r3r2"),
    (
        "SEMANTIC_OPERATION_RECEIPT",
        "acfqp.campaign_semantic_operation_receipt.v180r12r3r2",
    ),
    ("REPLAY_SUBJECT_RECEIPT", "acfqp.campaign_replay_subject_receipt.v180r12r3r2"),
    ("CAMPAIGN_SUBJECT_RESULT", "acfqp.campaign_measurement_subject_result.v180r12r3r2"),
    ("PIDFD_BIRTH_RECEIPT", "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2"),
    ("PIDFD_REAP_RECEIPT", "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2"),
    (
        "CGROUP_TOPOLOGY_RECEIPT",
        "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2",
    ),
    (
        "CGROUP_OBSERVATION_RECEIPT",
        "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2",
    ),
    ("CAMPAIGN_ATTEMPT_RECORD", "acfqp.campaign_attempt_record.v180r12r3r2"),
    ("IO_TRANSFER_RECEIPT", "acfqp.campaign_io_transfer_receipt.v180r12r3r2"),
    (
        "SUBJECT_COMMIT_RECEIPT",
        "acfqp.campaign_subject_commit_receipt.v180r12r3r2",
    ),
    (
        "WINDOW_CLOSURE_RECEIPT",
        "acfqp.campaign_window_closure_receipt.v180r12r3r2",
    ),
    (
        "CAMPAIGN_EXECUTION_CLOSURE",
        "acfqp.campaign_execution_closure.v180r12r3r2",
    ),
    (
        "CAMPAIGN_OPERATION_MANIFEST",
        "acfqp.campaign_operation_manifest.v180r12r3r2",
    ),
    (
        "NATIVE_ZERO_SOURCE_MANIFEST",
        "acfqp.campaign_native_zero_source_manifest.v180r12r3r2",
    ),
    (
        "NATIVE_ZERO_IMPORT_INVENTORY",
        "acfqp.campaign_native_zero_import_inventory.v180r12r3r2",
    ),
)
EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS = tuple(
    (
        evidence_type,
        schema,
        _EVIDENCE_DESCRIPTOR[schema][1],
        _EVIDENCE_FIELDS_BY_SCHEMA[schema],
    )
    for evidence_type, schema in _EVIDENCE_FIELD_KEYSET_ROW_ORDER
)

OS_EVIDENCE_SCHEMA_COUNTS = {
    "acfqp.campaign_memfd_stage_receipt.v180r12r3r2": 2,
    "acfqp.campaign_fd_visibility_receipt.v180r12r3r2": 4,
    "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2": 2,
    "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2": 2,
    "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2": 1,
    "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2": 1,
}

_LEAF_METADATA = {
    "common.hash_invocations": (
        "hash-invocation-v1",
        "content_id_layer",
        "invocations",
        "attempt",
        "sum",
        "nonkernel_compute_events",
    ),
    "common.integrity_checks": (
        "integrity-check-v1",
        "artifact_verifier",
        "checks",
        "attempt",
        "sum",
        "nonkernel_compute_events",
    ),
    "common.protocol_checks": (
        "protocol-check-v1",
        "state_machine_verifier",
        "checks",
        "attempt",
        "sum",
        "nonkernel_compute_events",
    ),
    "io.mounted_bytes_peak": (
        "mounted-byte-peak-v1",
        "sandbox_supervisor",
        "bytes",
        "decision_point",
        "max",
        "peak_mounted_bytes",
    ),
    "io.output_bytes": (
        "io-output-byte-v1",
        "artifact_writer",
        "bytes",
        "attempt",
        "sum",
        "output_bytes",
    ),
    "io.read_bytes": (
        "io-read-byte-v1",
        "io_wrapper",
        "bytes",
        "attempt",
        "sum",
        "read_bytes",
    ),
    "io.staged_bytes": (
        "io-staged-byte-v1",
        "sandbox_stager",
        "bytes",
        "attempt",
        "sum",
        "staged_bytes",
    ),
    "memory.working_bytes_peak": (
        "working-byte-peak-v1",
        "worker_supervisor_or_frozen_cap",
        "bytes",
        "transaction_or_attempt",
        "max",
        "peak_working_bytes",
    ),
    "process.launches": (
        "process-launch-v1",
        "process_supervisor",
        "launches",
        "attempt",
        "sum",
        "process_launches",
    ),
}


class ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error(
    ValueError
):
    """The pending terminal failed producer-free exact reconstruction."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256 identity")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _canonical_document(value: Any, label: str) -> tuple[bytes, dict[str, Any]]:
    if type(value) is bytes:
        try:
            document = loads_canonical_json(value)
        except (TypeError, ValueError) as error:
            raise ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error(
                f"{label} is not canonical JSON"
            ) from error
        if type(document) is not dict or canonical_json_bytes(document) != value:
            _fail(f"{label} must be one canonical JSON object")
        return value, document
    if type(value) is not dict:
        _fail(f"{label} must be canonical bytes or one exact object")
    return canonical_json_bytes(value), value


def _content_document(
    document: Mapping[str, Any],
    *,
    domain: str,
    identity_field: str,
    label: str,
) -> str:
    identity = _cid(document.get(identity_field), f"{label} identity")
    payload = dict(document)
    payload.pop(identity_field)
    if identity != evidence_domains.extension_content_id_v180r12r3r2e(domain, payload):
        _fail(f"{label} content identity changed")
    return identity


def _plain_sha256_document(
    raw: bytes,
    *,
    fields: frozenset[str],
    identity_field: str,
    label: str,
) -> tuple[dict[str, Any], str]:
    canonical, document = _canonical_document(raw, label)
    if canonical != raw or frozenset(document) != fields:
        _fail(f"{label} exact keyset changed")
    identity = _cid(document.get(identity_field), f"{label} identity")
    payload = dict(document)
    payload.pop(identity_field, None)
    if identity != hashlib.sha256(canonical_json_bytes(payload)).hexdigest():
        _fail(f"{label} plain content identity changed")
    return document, identity


def _regular_artifact_observation(raw: bytes) -> dict[str, Any]:
    return {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _validate_success_measurement_cgroup_observations(
    value: object, *, campaign_attempt_id: str
) -> None:
    if type(value) is not list or len(value) != 3:
        _fail("measurement launch cgroup observation denominator changed")
    expected_root_name = "v180r12r3r2-" + _cid(
        campaign_attempt_id, "measurement cgroup campaign attempt ID"
    )
    for index, row in enumerate(value):
        if type(row) is not dict or frozenset(row) != (
            MEASUREMENT_CGROUP_OBSERVATION_FIELDS
        ):
            _fail("measurement launch cgroup observation schema changed")
        if not (
            row.get("phase") == MEASUREMENT_CGROUP_OBSERVATION_PHASES[index]
            and row.get("applicable") is True
            and row.get("campaign_attempt_id") == campaign_attempt_id
            and row.get("root_name") == expected_root_name
            and row.get("ownership_acquired") is True
            and row.get("root_state") == "ABSENT"
            and row.get("root_mode") is None
            and row.get("root_nlink") is None
            and row.get("root_device") is None
            and row.get("root_inode") is None
            and row.get("root_populated") is None
            and row.get("root_process_count") is None
            and row.get("supervisor_state") == "ABSENT"
            and row.get("worker_state") == "ABSENT"
            and row.get("kill_attempted") is False
            and row.get("kill_succeeded") is False
            and row.get("wait_empty_attempted") is False
            and row.get("wait_empty_succeeded") is False
            and row.get("remove_attempted") is False
            and row.get("remove_succeeded") is False
            and row.get("residual_tree_or_process_possible") is False
            and row.get("error_type") is None
            and row.get("error_message") is None
        ):
            _fail("measurement success cgroup closure changed")


def _validate_measurement_launch_guard_authority(
    *,
    measurement_launch_attempt_bytes: bytes,
    measurement_launch_receipt_bytes: bytes,
    terminal_bytes: bytes,
    success_artifacts: Mapping[str, bytes],
    expected_prelaunch_materialization_terminal_id: str,
    expected_prelaunch_launch_manifest_sha256: str,
    expected_prelaunch_launch_rule_id: str,
    expected_measurement_launch_attempt_id: str,
    expected_campaign_attempt_id: str,
) -> tuple[dict[str, Any], str]:
    """Bind the post-dispatch guard to the exact successful child receipt.

    The receipt does not directly observe imports.  It transitively supports the
    guard because its exact launch attempt binds the frozen manifest and the
    frozen bootstrap fails the child if any post-dispatch origin check fails.
    """

    attempt, attempt_id = _plain_sha256_document(
        measurement_launch_attempt_bytes,
        fields=MEASUREMENT_LAUNCH_ATTEMPT_FIELDS,
        identity_field="launch_attempt_id",
        label="measurement launch attempt",
    )
    repository_root = attempt.get("repository_root")
    if type(repository_root) is not str or not repository_root.startswith("/"):
        _fail("measurement launch repository root changed")
    prelaunch_root = (
        f"{repository_root}/.tmp/exact-freeze/"
        "v180r12r3r2_campaign_measurement_prelaunch"
    )
    expected_argv = [
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-X",
        "pycache_prefix=/dev/null/v180r12r3r2",
        f"{prelaunch_root}/bootstrap.py",
        "measurement",
        repository_root,
        prelaunch_root,
        f"{prelaunch_root}/launch_manifest.json",
    ]
    if not (
        attempt.get("schema") == MEASUREMENT_LAUNCH_ATTEMPT_SCHEMA
        and attempt.get("launch_rule_id") == expected_prelaunch_launch_rule_id
        and attempt.get("target") == "measurement"
        and attempt.get("materialization_terminal_id")
        == expected_prelaunch_materialization_terminal_id
        and _positive(
            attempt.get("materialization_terminal_byte_count"),
            "measurement materialization-terminal byte count",
        )
        and _cid(
            attempt.get("materialization_terminal_sha256"),
            "measurement materialization-terminal SHA256",
        )
        and attempt.get("launch_manifest_sha256")
        == expected_prelaunch_launch_manifest_sha256
        and attempt.get("child_argv") == expected_argv
        and attempt.get("child_environment")
        == {
            "ACFQP_V180R12R3R2_LAUNCH_MANIFEST_SHA256": (
                expected_prelaunch_launch_manifest_sha256
            ),
            "LC_CTYPE": "C.UTF-8",
        }
        and attempt.get("address_space_hard_cap_bytes")
        == MEASUREMENT_LAUNCH_ADDRESS_SPACE_HARD_CAP_BYTES
        and attempt.get("address_space_cap_applied_before_child_exec") is True
        and attempt.get("wall_timeout_seconds")
        == MEASUREMENT_LAUNCH_WALL_TIMEOUT_SECONDS
        and attempt.get("attempt_lock_written_before_child_exec") is True
        and attempt.get("same_target_identity_rerun_forbidden") is True
        and attempt.get("preauthorization_supervision") is True
        and attempt.get("campaign_actual_measurement") is False
        and attempt.get("scientific_occurrence_started") is False
        and attempt.get("authorized_child_measurement_execution_attempted") is True
        and attempt.get("authorized_child_measurement_execution_completed") is False
        and attempt.get("producer_free_verification_attempted") is False
        and attempt.get("producer_free_verification_completed") is False
        and attempt_id == expected_measurement_launch_attempt_id
    ):
        _fail("measurement launch attempt/frozen bootstrap authority changed")

    receipt, receipt_id = _plain_sha256_document(
        measurement_launch_receipt_bytes,
        fields=MEASUREMENT_LAUNCH_RECEIPT_FIELDS,
        identity_field="launch_receipt_id",
        label="measurement launch receipt",
    )
    progress = receipt.get("progress_observations")
    if type(progress) is not dict or frozenset(progress) != MEASUREMENT_LAUNCH_PROGRESS_NAMES:
        _fail("measurement launch receipt progress keyset changed")
    expected_progress = {
        "attempt": _regular_artifact_observation(measurement_launch_attempt_bytes),
        "receipt": {"presence": "ABSENT"},
        "launch_failure": {"presence": "ABSENT"},
        "runtime_cas": {"presence": "ABSENT"},
        "output_root": {"presence": "DIRECTORY", "mode": 0o700},
        "terminal": _regular_artifact_observation(terminal_bytes),
        "evidence_inventory": _regular_artifact_observation(
            success_artifacts["evidence_inventory"]
        ),
        "execution_closure": _regular_artifact_observation(
            success_artifacts["execution_closure"]
        ),
        "os_receipt": _regular_artifact_observation(success_artifacts["os_receipt"]),
        "ledger_closure": _regular_artifact_observation(
            success_artifacts["ledger_closure"]
        ),
        "measurement_failure": {"presence": "ABSENT"},
        "verification": {"presence": "ABSENT"},
        "verification_failure": {"presence": "ABSENT"},
        "retained_replay": {"presence": "ABSENT"},
    }
    origin_ns = receipt.get("monotonic_origin_ns")
    hard_deadline_ns = receipt.get("hard_deadline_ns")
    campaign_deadline_ns = receipt.get("campaign_deadline_ns")
    _validate_success_measurement_cgroup_observations(
        receipt.get("measurement_cgroup_cleanup_observations"),
        campaign_attempt_id=expected_campaign_attempt_id,
    )
    if not (
        receipt.get("schema") == MEASUREMENT_LAUNCH_RECEIPT_SCHEMA
        and receipt.get("launch_rule_id") == expected_prelaunch_launch_rule_id
        and receipt.get("launch_attempt_id") == attempt_id
        and receipt.get("target") == "measurement"
        and receipt.get("return_code") == 0
        and receipt.get("timed_out") is False
        and receipt.get("child_stdout") == _EMPTY_LAUNCH_STREAM
        and receipt.get("child_stderr") == _EMPTY_LAUNCH_STREAM
        and progress == expected_progress
        and receipt.get("same_target_identity_rerun_forbidden") is True
        and receipt.get("attempt_lock_preserved") is True
        and receipt.get("address_space_hard_cap_bytes")
        == MEASUREMENT_LAUNCH_ADDRESS_SPACE_HARD_CAP_BYTES
        and receipt.get("wall_timeout_seconds")
        == MEASUREMENT_LAUNCH_WALL_TIMEOUT_SECONDS
        and type(origin_ns) is int
        and type(hard_deadline_ns) is int
        and type(campaign_deadline_ns) is int
        and 0 < origin_ns < campaign_deadline_ns < hard_deadline_ns
        and hard_deadline_ns - origin_ns
        == MEASUREMENT_LAUNCH_WALL_TIMEOUT_SECONDS * NANOSECONDS_PER_SECOND
        and hard_deadline_ns - campaign_deadline_ns
        == MEASUREMENT_CAMPAIGN_CLEANUP_GRACE_SECONDS * NANOSECONDS_PER_SECOND
        and receipt.get("campaign_cleanup_grace_seconds")
        == MEASUREMENT_CAMPAIGN_CLEANUP_GRACE_SECONDS
        and receipt.get("termination_grace_seconds")
        == MEASUREMENT_LAUNCH_TERMINATION_GRACE_SECONDS
        and receipt.get("preauthorization_supervision") is True
        and receipt.get("campaign_actual_measurement") is False
        and receipt.get("authorized_child_measurement_execution_attempted") is True
        and receipt.get("authorized_child_measurement_execution_completed") is True
        and receipt.get("producer_free_verification_attempted") is False
        and receipt.get("producer_free_verification_completed") is False
        and all(
            receipt.get(field) == "NOT_RUN"
            for field in (
                "COUNTER_COMPLETENESS_GATE",
                "WORKLOAD_ECONOMICS_GATE",
                "SCALAR_CALIBRATION_GATE",
                "BREAK_EVEN_GATE",
            )
        )
        and receipt.get("official_execution_allowed") is False
        and receipt.get("success") is True
        and receipt.get("failure_type") is None
        and receipt.get("failure_message") is None
    ):
        _fail("measurement launch receipt or post-dispatch guard support changed")
    return receipt, receipt_id


def _operation_id(attempt_id: str, slot: str, family: str, ordinal: int) -> str:
    return evidence_domains.extension_content_id_v180r12r3r2e(
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_V180R12R3R2E_DOMAIN,
        {
            "schema": "acfqp.campaign_operation_identity.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": attempt_id,
            "slot": slot,
            "family": family,
            "ordinal": ordinal,
        },
    )


def _operation_schedule(attempt_id: str) -> tuple[dict[str, Any], ...]:
    _cid(attempt_id, "campaign attempt ID")
    specifications: list[tuple[str, str, int, str, str]] = [
        ("ATTEMPT", "OPEN", 0, "ATTEMPT", "OBSERVER"),
        ("PROCESS", "SUPERVISOR", 0, "STAGE", "OBSERVER"),
        ("INPUT_READ", "FROZEN_SOURCE", 0, "STAGE", "SUPERVISOR"),
        ("INPUT_READ", "FROZEN_SOURCE", 1, "STAGE", "SUPERVISOR"),
        ("STAGE_WRITE", "SEALED_MEMFD", 0, "STAGE", "SUPERVISOR"),
        ("STAGE_WRITE", "SEALED_MEMFD", 1, "STAGE", "SUPERVISOR"),
        ("MOUNT", "SEALED_MEMFD", 0, "STAGE", "SUPERVISOR"),
        ("MOUNT", "SEALED_MEMFD", 1, "STAGE", "SUPERVISOR"),
    ]
    for slot, families in (
        ("SEMANTIC_HASH", HASH_OPERATION_FAMILIES),
        ("INTEGRITY_CHECK", INTEGRITY_OPERATION_FAMILIES),
    ):
        for family, count, phase, actor in families:
            if phase == "STAGE":
                specifications.extend(
                    (slot, family, ordinal, phase, actor)
                    for ordinal in range(count)
                )
    specifications.extend(
        (
            ("PROCESS", "WORKER", 0, "WORKER", "SUPERVISOR"),
            ("INPUT_READ", "SEALED_STAGE", 0, "WORKER", "WORKER"),
            ("INPUT_READ", "SEALED_STAGE", 1, "WORKER", "WORKER"),
        )
    )
    for slot, families in (
        ("SEMANTIC_HASH", HASH_OPERATION_FAMILIES),
        ("INTEGRITY_CHECK", INTEGRITY_OPERATION_FAMILIES),
    ):
        for family, count, phase, actor in families:
            if phase == "WORKER":
                specifications.extend(
                    (slot, family, ordinal, phase, actor)
                    for ordinal in range(count)
                )
    specifications.extend(
        ("PROTOCOL_CHECK", family, 0, "WORKER", "WORKER")
        for family in PROTOCOL_CHECK_FAMILIES
    )
    specifications.extend(
        (
            ("SUBJECT_WRITE", "SUBJECT_RESULT", 0, "WORKER", "WORKER"),
            ("INPUT_READ", "SUBJECT_READBACK", 0, "COMMIT", "SUPERVISOR"),
        )
    )
    for slot, families in (
        ("SEMANTIC_HASH", HASH_OPERATION_FAMILIES),
        ("INTEGRITY_CHECK", INTEGRITY_OPERATION_FAMILIES),
    ):
        for family, count, phase, actor in families:
            if phase == "COMMIT":
                specifications.extend(
                    (slot, family, ordinal, phase, actor)
                    for ordinal in range(count)
                )
    specifications.extend(
        (
            ("SUBJECT_COMMIT", "SUBJECT_RESULT", 0, "COMMIT", "SUPERVISOR"),
            ("WINDOW", "CLOSE", 0, "WINDOW_CLOSE", "SUPERVISOR"),
            ("CGROUP", "FINAL_OBSERVE", 0, "OS_OBSERVE", "OBSERVER"),
            ("LEDGER", "CLOSE", 0, "LEDGER_CLOSE", "OBSERVER"),
        )
    )
    result = tuple(
        {
            "slot": slot,
            "family": family,
            "ordinal": ordinal,
            "phase": phase,
            "actor_role": actor,
            "operation_id": _operation_id(attempt_id, slot, family, ordinal),
        }
        for slot, family, ordinal, phase, actor in specifications
    )
    if len(result) != 314 or len({row["operation_id"] for row in result}) != 314:
        _fail("independent operation schedule cardinality changed")
    return result


def _event_schedule(attempt_id: str) -> tuple[tuple[str, str, str, str], ...]:
    operations = _operation_schedule(attempt_id)
    by_key = {
        (row["slot"], row["family"], row["ordinal"]): row for row in operations
    }
    result: list[tuple[str, str, str, str]] = []

    def emit(kind: str, row: Mapping[str, Any], role: str | None = None,
             phase: str | None = None) -> None:
        result.append(
            (
                kind,
                role or row["actor_role"],
                phase or row["phase"],
                row["operation_id"],
            )
        )

    def pair(stem: str, row: Mapping[str, Any]) -> None:
        emit(f"{stem}_INTENT", row)
        emit(f"{stem}_OUTCOME", row)

    attempt = by_key[("ATTEMPT", "OPEN", 0)]
    supervisor = by_key[("PROCESS", "SUPERVISOR", 0)]
    worker = by_key[("PROCESS", "WORKER", 0)]
    emit("ATTEMPT_OPEN", attempt)
    pair("PROCESS_BIRTH", supervisor)
    for row in operations:
        if row["slot"] == "INPUT_READ" and row["phase"] == "STAGE":
            pair("INPUT_READ", row)
    for row in operations:
        if row["slot"] == "STAGE_WRITE":
            pair("STAGE_WRITE", row)
    for row in operations:
        if row["slot"] == "MOUNT":
            emit("MOUNT_VISIBILITY_OPEN", row)
    for slot in ("SEMANTIC_HASH", "INTEGRITY_CHECK"):
        for row in operations:
            if row["slot"] == slot and row["phase"] == "STAGE":
                pair(slot, row)
    pair("PROCESS_BIRTH", worker)
    for row in operations:
        if row["slot"] == "INPUT_READ" and row["phase"] == "WORKER":
            pair("INPUT_READ", row)
    for slot in ("SEMANTIC_HASH", "INTEGRITY_CHECK", "PROTOCOL_CHECK"):
        for row in operations:
            if row["slot"] == slot and row["phase"] == "WORKER":
                pair(slot, row)
    pair("SUBJECT_WRITE", by_key[("SUBJECT_WRITE", "SUBJECT_RESULT", 0)])
    emit("PROCESS_REAP", worker, "SUPERVISOR", "WORKER")
    pair("INPUT_READ", by_key[("INPUT_READ", "SUBJECT_READBACK", 0)])
    for slot in ("SEMANTIC_HASH", "INTEGRITY_CHECK"):
        for row in operations:
            if row["slot"] == slot and row["phase"] == "COMMIT":
                pair(slot, row)
    emit("SUBJECT_COMMIT", by_key[("SUBJECT_COMMIT", "SUBJECT_RESULT", 0)])
    for row in operations:
        if row["slot"] == "MOUNT":
            emit("MOUNT_VISIBILITY_CLOSE", row, "SUPERVISOR", "WINDOW_CLOSE")
    emit("WINDOW_CLOSED", by_key[("WINDOW", "CLOSE", 0)])
    emit("PROCESS_REAP", supervisor, "OBSERVER", "OS_OBSERVE")
    emit("CGROUP_OBSERVED", by_key[("CGROUP", "FINAL_OBSERVE", 0)])
    emit("LEDGER_CLOSED", by_key[("LEDGER", "CLOSE", 0)])
    if len(result) != SUCCESS_EVENT_COUNT:
        _fail("independent expanded event schedule cardinality changed")
    return tuple(result)


def _operation_manifest(attempt_id: str) -> dict[str, Any]:
    operations = _operation_schedule(attempt_id)
    payload = {
        "schema": "acfqp.campaign_operation_manifest.v180r12r3r2",
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "scope_model": CAMPAIGN_SCOPE_MODEL,
        "attempt_id": attempt_id,
        "operations": list(operations),
        "operation_count": 314,
        "semantic_hash_operation_count": 137,
        "integrity_check_operation_count": 145,
        "protocol_check_operation_count": 15,
        "all_event_operation_ids_must_equal_manifest": True,
        "unregistered_operation_ids_forbidden": True,
    }
    return {
        **payload,
        "campaign_operation_manifest_id": (
            evidence_domains.extension_content_id_v180r12r3r2e(
                evidence_domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_MANIFEST_V180R12R3R2E_DOMAIN,
                payload,
            )
        ),
    }


def _stable_input_fact(role: str) -> dict[str, Any]:
    if role == "TERMINAL":
        relative_path = (
            ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation/TERMINAL.json"
        )
        schema = "acfqp.ten_terminal_production_aggregation.v180r12r2"
        identity_field = "production_aggregation_bundle_id"
        content_id = TERMINAL_INPUT_CONTENT_ID
        byte_count = TERMINAL_INPUT_BYTE_COUNT
        sha256 = TERMINAL_INPUT_SHA256
    elif role == "VERIFICATION":
        relative_path = (
            ".tmp/exact-freeze/"
            "v180r12r2_ten_terminal_aggregation_verification.json"
        )
        schema = "acfqp.ten_terminal_aggregation_verification.v180r12r2"
        identity_field = "verification_id"
        content_id = VERIFICATION_INPUT_CONTENT_ID
        byte_count = VERIFICATION_INPUT_BYTE_COUNT
        sha256 = VERIFICATION_INPUT_SHA256
    else:
        _fail("campaign stable-input role changed")
    payload = {
        "schema": "acfqp.campaign_stable_input_fact.v180r12r3r2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_k7_campaign_measurement_worker_v180r12r3r2",
        "role": role,
        "relative_path": relative_path,
        "document_schema": schema,
        "identity_field": identity_field,
        "content_id": content_id,
        "byte_count": byte_count,
        "sha256": sha256,
        "fresh_replay_input": True,
        "retroactive_v180r12r2_cost_claimed": False,
    }
    return {
        **payload,
        "stable_input_fact_id": evidence_domains.extension_content_id_v180r12r3r2e(
            evidence_domains.CONSTRUCTION_K7_STABLE_INPUT_SNAPSHOT_V180R12R3R2E_DOMAIN,
            payload,
        ),
    }


def _validate_events(
    closure: Mapping[str, Any],
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
) -> tuple[dict[str, Any], ...]:
    rows = closure.get("events")
    if type(rows) is not list or len(rows) != SUCCESS_EVENT_COUNT:
        _fail("independent replay requires exactly 625 raw events")
    expected = _event_schedule(attempt_id)
    max_event_count = _positive(closure.get("max_event_count"), "event-count cap")
    max_event_bytes = _positive(
        closure.get("max_event_byte_count"), "per-event byte cap"
    )
    max_ledger_bytes = _positive(
        closure.get("max_ledger_byte_count"), "ledger byte cap"
    )
    if max_event_count < SUCCESS_EVENT_COUNT:
        _fail("successful event count exceeds its frozen cap")
    previous_id: str | None = None
    previous_clock: int | None = None
    total_bytes = 0
    nonnull = 0
    result: list[dict[str, Any]] = []
    for index, (row, signature) in enumerate(zip(rows, expected)):
        if type(row) is not dict or set(row) != _EVENT_FIELDS:
            _fail("campaign raw event field set changed")
        raw = canonical_json_bytes(row)
        if len(raw) > max_event_bytes:
            _fail("campaign raw event exceeds its per-event cap")
        total_bytes += len(raw)
        kind, actor, phase, operation_id = signature
        if (
            row.get("schema")
            != "acfqp.campaign_measurement_ledger_event.v180r12r3r2"
            or row.get("protocol_id") != protocol_id
            or row.get("authorization_id") != authorization_id
            or row.get("attempt_id") != attempt_id
            or row.get("sequence") != index
            or row.get("event_kind") != kind
            or row.get("actor_role") != actor
            or row.get("phase") != phase
            or row.get("operation_id") != operation_id
            or row.get("previous_event_id") != previous_id
        ):
            _fail("campaign raw event differs from the exact 625-position schedule")
        clock = row.get("monotonic_ns")
        if type(clock) is not int or clock < 0 or (
            previous_clock is not None and clock <= previous_clock
        ):
            _fail("campaign raw event monotonic clock changed")
        payload = row.get("payload")
        if type(payload) is not dict or set(payload) != _PAYLOAD_FIELDS:
            _fail("campaign raw event payload envelope changed")
        evidence_id = payload.get("evidence_id")
        if kind in _DIRECT_SCHEMA_BY_KIND:
            _cid(evidence_id, "campaign direct event evidence ID")
            nonnull += 1
        elif evidence_id is not None:
            _fail("intent or ledger-close event acquired evidence")
        if (
            payload.get("outcome_code") != _OUTCOME_BY_KIND[kind]
            or payload.get("auxiliary_values") != []
        ):
            _fail("campaign event outcome or auxiliary envelope changed")
        measured = payload.get("measured_value")
        if kind in _COUNTER_PATH_BY_KIND:
            _positive(measured, "successful campaign measured value")
            if kind in _UNIT_KINDS and measured != 1:
                _fail("unit campaign outcome no longer measures exactly one")
        elif measured is not None:
            _fail("non-counter campaign event acquired a measured value")
        event_id = _cid(row.get("event_id"), "campaign event ID")
        event_payload = dict(row)
        event_payload.pop("event_id")
        if event_id != evidence_domains.extension_content_id_v180r12r3r2e(
            evidence_domains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_EVENT_V180R12R3R2E_DOMAIN,
            event_payload,
        ):
            _fail("campaign raw event content identity changed")
        previous_id = event_id
        previous_clock = clock
        result.append(row)
    if (
        nonnull != SUCCESS_NONNULL_EVIDENCE_COUNT
        or SUCCESS_EVENT_COUNT - nonnull != SUCCESS_NULL_EVIDENCE_COUNT
        or total_bytes > max_ledger_bytes
        or closure.get("ledger_event_byte_count") != total_bytes
        or closure.get("ordered_event_ids") != [row["event_id"] for row in result]
        or closure.get("first_event_id") != result[0]["event_id"]
        or closure.get("last_event_id") != result[-1]["event_id"]
    ):
        _fail("campaign raw event denominator or chain summary changed")
    return tuple(result)


def _validate_evidence_documents(
    closure: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], tuple[dict[str, Any], ...]]:
    rows = closure.get("evidence_documents")
    if type(rows) is not list or len(rows) != SUCCESS_EVIDENCE_DOCUMENT_COUNT:
        _fail("independent replay requires exactly 328 evidence documents")
    ids: list[str] = []
    schemas: list[str] = []
    documents: dict[str, dict[str, Any]] = {}
    for row in rows:
        if type(row) is not dict:
            _fail("campaign evidence row must be one exact object")
        schema = row.get("schema")
        descriptor = _EVIDENCE_DESCRIPTOR.get(schema)
        if descriptor is None:
            _fail("campaign evidence schema is unregistered")
        if (
            set(row) != _EVIDENCE_FIELDS_BY_SCHEMA[schema]
            or row.get("schema_version") != SCHEMA_VERSION
        ):
            _fail("campaign evidence exact schema field set changed")
        domain, identity_field, _count = descriptor
        identity = _content_document(
            row,
            domain=domain,
            identity_field=identity_field,
            label="campaign evidence document",
        )
        if identity in documents:
            _fail("campaign evidence identity repeats")
        documents[identity] = row
        ids.append(identity)
        schemas.append(schema)
    if ids != sorted(ids):
        _fail("campaign evidence documents are not sorted by identity")
    counts = {
        schema: schemas.count(schema) for schema in _EVIDENCE_DESCRIPTOR
    }
    expected_counts = {
        schema: descriptor[2] for schema, descriptor in _EVIDENCE_DESCRIPTOR.items()
    }
    if (
        counts != expected_counts
        or closure.get("campaign_evidence_document_type_counts") != expected_counts
        or closure.get("campaign_evidence_document_count")
        != SUCCESS_EVIDENCE_DOCUMENT_COUNT
        or closure.get("direct_event_evidence_document_count")
        != SUCCESS_NONNULL_EVIDENCE_COUNT
        or closure.get("support_evidence_document_count") != 11
    ):
        _fail("campaign evidence exact typed denominator changed")
    return documents, tuple(rows)


def _one(
    documents: Mapping[str, Mapping[str, Any]], schema: str
) -> dict[str, Any]:
    rows = [dict(row) for row in documents.values() if row.get("schema") == schema]
    if len(rows) != 1:
        _fail(f"campaign evidence inventory requires exactly one {schema}")
    return rows[0]


def _leaf(path: str) -> dict[str, Any]:
    semantics, owner, unit, scope, reducer, axis = _LEAF_METADATA[path]
    return {
        "path": path,
        "semantics_id": semantics,
        "owner": owner,
        "unit": unit,
        "lane": "operational",
        "scope": scope,
        "reducer": reducer,
        "comparison_axis": axis,
        "required": True,
        "source_registry_key": registry_v6.COUNTER_REGISTRY_KEY,
        "metadata_authority": "EXACT_V6_LEAF_METADATA_EXTRACT",
    }


def _signed_subrecord(
    payload: Mapping[str, Any], *, domain: str, identity_field: str
) -> dict[str, Any]:
    return {
        **dict(payload),
        identity_field: evidence_domains.extension_content_id_v180r12r3r2e(
            domain, dict(payload)
        ),
    }


@dataclass(frozen=True, slots=True)
class _EvidenceReplay:
    subject_id: str
    subject_byte_count: int
    operation_manifest_id: str
    source_manifest_id: str
    import_inventory_id: str
    execution_closure_id: str
    window_closed_event_id: str
    mount_open_event_ids: tuple[str, str]
    mount_open_evidence_ids: tuple[str, str]
    mount_close_event_ids: tuple[str, str]
    mount_close_evidence_ids: tuple[str, str]
    memory_peak_bytes: int


def _validate_subject(
    subject: Mapping[str, Any],
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
) -> tuple[str, int]:
    subject_id = _cid(subject.get("subject_result_id"), "campaign subject ID")
    subject_raw = canonical_json_bytes(subject)
    if (
        set(subject) != _SUBJECT_RESULT_FIELDS
        or subject.get("schema")
        != "acfqp.campaign_measurement_subject_result.v180r12r3r2"
        or subject.get("schema_version") != SCHEMA_VERSION
        or subject.get("scope")
        != "FRESH_PRODUCER_FREE_POST_OUTCOME_EVIDENCE_REPLAY_SUCCESSOR"
        or subject.get("protocol_id") != protocol_id
        or subject.get("authorization_id") != authorization_id
        or subject.get("attempt_id") != attempt_id
        or subject.get("terminal_byte_count") != TERMINAL_INPUT_BYTE_COUNT
        or subject.get("verification_byte_count") != VERIFICATION_INPUT_BYTE_COUNT
        or subject.get("terminal_content_id") != TERMINAL_INPUT_CONTENT_ID
        or subject.get("verification_content_id") != VERIFICATION_INPUT_CONTENT_ID
        or subject.get("terminal_sha256") != TERMINAL_INPUT_SHA256
        or subject.get("verification_sha256") != VERIFICATION_INPUT_SHA256
        or subject.get("inner_content_id_count") != 129
        or subject.get("semantic_hash_operation_count") != 137
        or subject.get("integrity_check_operation_count") != 145
        or subject.get("protocol_check_operation_count") != 15
        or subject.get("route_component_counter_closure_status") != "PASS"
        or subject.get("exact_v180r12r2_verification_replayed") is not True
        or subject.get("producer_module_imported") is not False
        or subject.get("producer_entrypoint_called") is not False
        or subject.get("v180r12r2_verifier_imported") is not False
        or subject.get("v180r12r2_verifier_called") is not False
        or subject.get("retroactive_v180r12r2_cost_claimed") is not False
        or subject.get("counter_completeness_gate")
        != "PENDING_INDEPENDENT_REPLAY"
        or subject.get("workload_economics_gate") != "NOT_RUN"
        or subject.get("scalar_calibration_gate") != "NOT_RUN"
        or subject.get("break_even_gate") != "NOT_RUN"
        or subject.get("official_execution_gate") != "NOT_RUN"
        or subject.get("official_scalar_cost") is not None
        or subject.get("official_N_break_even") is not None
        or subject.get("official_execution_allowed") is not False
        or subject.get("subject_byte_count") != len(subject_raw)
        or len(subject_raw) > SUBJECT_RESULT_RUNTIME_BYTE_CAP
    ):
        _fail("campaign full subject-result document changed")
    for field in (
        "authorization_evidence_id",
        "execution_slot_id",
        "execution_nonce",
        "logical_occurrence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
        "campaign_attempt_record_id",
        "terminal_snapshot_id",
        "verification_snapshot_id",
        "worker_birth_receipt_id",
        "operation_manifest_id",
    ):
        _cid(subject.get(field), f"campaign subject {field}")
    for field in ("memfd_stage_receipt_ids", "open_visibility_receipt_ids"):
        values = subject.get(field)
        if type(values) is not list or len(values) != 2 or len(set(values)) != 2:
            _fail(f"campaign subject {field} changed")
        for value in values:
            _cid(value, f"campaign subject {field} identity")
    inner = subject.get("inner_content_ids")
    if (
        type(inner) is not list
        or len(inner) != 129
        or any(
            type(row) is not dict
            or set(row) != {"label", "content_id"}
            or type(row.get("label")) is not str
            for row in inner
        )
        or [row["label"] for row in inner]
        != list(INNER_CONTENT_ID_OPERATION_SUFFIXES)
        or len({_cid(row["content_id"], "inner content ID") for row in inner})
        != 129
    ):
        _fail("campaign subject inner content-ID inventory changed")
    return subject_id, _positive(
        subject.get("subject_byte_count"), "campaign subject byte count"
    )


_CGROUP_NODE_FIELDS = {
    "role",
    "path",
    "parent_path",
    "membership_path",
    "parent_membership_path",
    "directory_fd",
    "device",
    "inode",
    "mode",
    "link_count",
    "cloexec",
    "symlink_free_resolution",
}
_CGROUP_CONTROL_FIELDS = {
    "schema",
    "schema_version",
    "node_role",
    "name",
    "fd",
    "device",
    "inode",
    "mode",
    "link_count",
    "cloexec",
    "opened_before_supervisor_birth",
    "retained_through_os_observe",
    "control_file_fact_id",
}
_CGROUP_READBACK_FIELDS = {
    "control_file_fact_id",
    "node_role",
    "name",
    "fd",
    "device",
    "inode",
    "mode",
    "link_count",
    "raw_value",
    "same_open_file_description",
    "read_after_both_reaps",
    "read_before_cgroup_remove",
}
_REQUIRED_CGROUP_CONTROL_FILES = (
    ("MEASUREMENT_ROOT", "cgroup.events"),
    ("MEASUREMENT_ROOT", "cgroup.procs"),
    ("MEASUREMENT_ROOT", "memory.events"),
    ("MEASUREMENT_ROOT", "memory.max"),
    ("MEASUREMENT_ROOT", "memory.peak"),
    ("MEASUREMENT_ROOT", "pids.events"),
    ("MEASUREMENT_ROOT", "pids.max"),
    ("MEASUREMENT_ROOT", "pids.peak"),
    ("SUPERVISOR", "cgroup.events"),
    ("SUPERVISOR", "cgroup.procs"),
    ("SUPERVISOR", "pids.max"),
    ("WORKER", "cgroup.events"),
    ("WORKER", "cgroup.procs"),
    ("WORKER", "pids.max"),
)


def _validate_cgroup_topology(
    topology: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], tuple[Mapping[str, Any], ...]]:
    parent = topology.get("cgroup_parent_fact")
    node_rows = {
        "DELEGATED_PARENT": topology.get("delegated_parent"),
        "MEASUREMENT_ROOT": topology.get("measurement_root"),
        "SUPERVISOR": topology.get("supervisor_leaf"),
        "WORKER": topology.get("worker_leaf"),
    }
    if type(parent) is not dict or any(type(row) is not dict for row in node_rows.values()):
        _fail("campaign cgroup topology parent/node documents changed")
    if (
        parent.get("schema") != "acfqp.v180r12r3r2_cgroup_parent_fact.v1"
        or parent.get("mount_fstype") != "cgroup2"
        or parent.get("controllers") != ["memory", "pids"]
        or parent.get("subtree_control") != ["memory", "pids"]
        or topology.get("cgroup_parent_fact_sha256")
        != hashlib.sha256(canonical_json_bytes(parent)).hexdigest()
        or topology.get("filesystem_type") != "cgroup2"
        or topology.get("controllers") != ["memory", "pids"]
        or topology.get("subtree_control") != ["memory", "pids"]
        or topology.get("root_memory_max_bytes") != MEMORY_MAX_BYTES
        or topology.get("memory_max_bytes") != MEMORY_MAX_BYTES
        or topology.get("root_pids_max") != 2
        or topology.get("pids_max") != 2
        or topology.get("supervisor_leaf_pids_max") != 1
        or topology.get("worker_leaf_pids_max") != 1
        or topology.get("root_populated_before_birth") is not False
        or topology.get("root_process_count_before_birth") != 0
        or topology.get("leaf_process_counts_before_birth") != [0, 0]
        or topology.get("no_internal_process_rule_satisfied") is not True
        or topology.get("sibling_leaf_topology") is not True
    ):
        _fail("campaign cgroup topology root fact changed")
    for role, node in node_rows.items():
        assert type(node) is dict
        if (
            set(node) != _CGROUP_NODE_FIELDS
            or node.get("role") != role
            or type(node.get("directory_fd")) is not int
            or node.get("directory_fd") < 0
            or type(node.get("device")) is not int
            or node.get("device") <= 0
            or type(node.get("inode")) is not int
            or node.get("inode") <= 0
            or type(node.get("mode")) is not int
            or stat.S_IFMT(node["mode"]) != stat.S_IFDIR
            or type(node.get("link_count")) is not int
            or node.get("link_count") <= 0
            or node.get("cloexec") is not True
            or node.get("symlink_free_resolution") is not True
        ):
            _fail("campaign cgroup node identity changed")
    delegated = node_rows["DELEGATED_PARENT"]
    root = node_rows["MEASUREMENT_ROOT"]
    supervisor = node_rows["SUPERVISOR"]
    worker = node_rows["WORKER"]
    assert all(type(row) is dict for row in (delegated, root, supervisor, worker))
    if (
        len({(row["device"], row["inode"]) for row in node_rows.values()}) != 4
        or len({row["directory_fd"] for row in node_rows.values()}) != 4
        or len({row["device"] for row in node_rows.values()}) != 1
        or parent.get("parent_path") != delegated["path"]
        or parent.get("parent_device") != delegated["device"]
        or parent.get("parent_inode") != delegated["inode"]
        or parent.get("mode") != stat.S_IMODE(delegated["mode"])
        or root["parent_path"] != delegated["path"]
        or root["parent_membership_path"] != delegated["membership_path"]
        or supervisor["parent_path"] != root["path"]
        or worker["parent_path"] != root["path"]
        or supervisor["parent_membership_path"] != root["membership_path"]
        or worker["parent_membership_path"] != root["membership_path"]
    ):
        _fail("campaign cgroup sibling-leaf topology join changed")
    controls = topology.get("control_files")
    if type(controls) is not list or len(controls) != len(_REQUIRED_CGROUP_CONTROL_FILES):
        _fail("campaign retained cgroup control-file inventory changed")
    if tuple((row.get("node_role"), row.get("name")) for row in controls) != (
        _REQUIRED_CGROUP_CONTROL_FILES
    ):
        _fail("campaign retained cgroup control-file order changed")
    control_ids: set[str] = set()
    for row in controls:
        if type(row) is not dict or set(row) != _CGROUP_CONTROL_FIELDS:
            _fail("campaign retained cgroup control-file schema changed")
        identity = _content_document(
            row,
            domain=evidence_domains.CONSTRUCTION_K7_CGROUP_TOPOLOGY_RECEIPT_V180R12R3R2E_DOMAIN,
            identity_field="control_file_fact_id",
            label="campaign retained cgroup control-file fact",
        )
        node = node_rows[row["node_role"]]
        if (
            identity in control_ids
            or row.get("device") != node["device"]
            or type(row.get("fd")) is not int
            or row.get("fd") < 0
            or type(row.get("inode")) is not int
            or row.get("inode") <= 0
            or type(row.get("mode")) is not int
            or stat.S_IFMT(row["mode"]) != stat.S_IFREG
            or type(row.get("link_count")) is not int
            or row.get("link_count") <= 0
            or row.get("cloexec") is not True
            or row.get("opened_before_supervisor_birth") is not True
            or row.get("retained_through_os_observe") is not True
        ):
            _fail("campaign retained cgroup control-file fact changed")
        control_ids.add(identity)
    if (
        len({row["fd"] for row in controls}) != len(controls)
        or len({(row["device"], row["inode"]) for row in controls}) != len(controls)
    ):
        _fail("campaign retained cgroup control-file identities repeat")
    return node_rows, tuple(controls)


def _validate_cgroup_observation(
    document: Mapping[str, Any],
    *,
    topology_id: str,
    controls: Sequence[Mapping[str, Any]],
    attempt_id: str,
) -> int:
    memory_peak = _positive(document.get("memory_peak_bytes"), "observed memory peak")
    expected_memory_events = [
        {"name": name, "value": 0}
        for name in ("high", "low", "max", "oom", "oom_group_kill", "oom_kill")
    ]
    expected_pids_events = [{"name": "max", "value": 0}]
    empty_roles = [
        {"role": role, "value": 0}
        for role in ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
    ]
    if (
        document.get("cgroup_topology_receipt_id") != topology_id
        or document.get("topology_receipt_id") != topology_id
        or document.get("attempt_id") != attempt_id
        or memory_peak > MEMORY_MAX_BYTES
        or document.get("pids_peak") != 2
        or document.get("memory_events") != expected_memory_events
        or document.get("pids_events") != expected_pids_events
        or document.get("populated_by_role") != empty_roles
        or document.get("process_count_by_role") != empty_roles
        or document.get("root_populated") is not False
        or document.get("root_process_count") != 0
        or document.get("supervisor_leaf_process_count") != 0
        or document.get("worker_leaf_process_count") != 0
        or document.get("observed_after_window_close") is not True
        or document.get("memory_peak_is_observed_not_authorization_cap") is not True
        or document.get("pids_peak_is_observed_not_authorization_cap") is not True
    ):
        _fail("campaign final cgroup observation facts changed")
    readbacks = document.get("control_file_readbacks")
    if type(readbacks) is not list or len(readbacks) != len(controls):
        _fail("campaign final cgroup readback inventory changed")
    raw_by_key: dict[tuple[str, str], str] = {}
    for readback, control in zip(readbacks, controls):
        if (
            type(readback) is not dict
            or set(readback) != _CGROUP_READBACK_FIELDS
            or any(
                readback.get(field) != control.get(field)
                for field in (
                    "control_file_fact_id",
                    "node_role",
                    "name",
                    "fd",
                    "device",
                    "inode",
                    "mode",
                    "link_count",
                )
            )
            or readback.get("same_open_file_description") is not True
            or readback.get("read_after_both_reaps") is not True
            or readback.get("read_before_cgroup_remove") is not True
            or type(readback.get("raw_value")) is not str
        ):
            _fail("campaign final cgroup readback fact changed")
        raw_by_key[(readback["node_role"], readback["name"])] = readback["raw_value"]
    expected_raw = {
        ("MEASUREMENT_ROOT", "cgroup.events"): "populated 0\nfrozen 0\n",
        ("MEASUREMENT_ROOT", "cgroup.procs"): "",
        ("MEASUREMENT_ROOT", "memory.events"): (
            "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n"
        ),
        ("MEASUREMENT_ROOT", "memory.max"): f"{MEMORY_MAX_BYTES}\n",
        ("MEASUREMENT_ROOT", "memory.peak"): f"{memory_peak}\n",
        ("MEASUREMENT_ROOT", "pids.events"): "max 0\n",
        ("MEASUREMENT_ROOT", "pids.max"): "2\n",
        ("MEASUREMENT_ROOT", "pids.peak"): "2\n",
        ("SUPERVISOR", "cgroup.events"): "populated 0\nfrozen 0\n",
        ("SUPERVISOR", "cgroup.procs"): "",
        ("SUPERVISOR", "pids.max"): "1\n",
        ("WORKER", "cgroup.events"): "populated 0\nfrozen 0\n",
        ("WORKER", "cgroup.procs"): "",
        ("WORKER", "pids.max"): "1\n",
    }
    if raw_by_key != expected_raw:
        _fail("campaign final cgroup raw readbacks contradict counters")
    return memory_peak


def _validate_native_zero_preregistered_fact_rows(
    source_manifest: Mapping[str, Any],
    import_inventory: Mapping[str, Any],
    *,
    attempt_id: str,
    expected_prelaunch_launch_manifest_sha256: str,
    expected_precompiled_source_bundle_sha256: str,
    expected_native_zero_precompiled_source_rows: Sequence[Mapping[str, Any]],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Re-derive every nested source, operation-site, and import fact ID."""

    bundle_sha = _cid(
        source_manifest.get("precompiled_source_bundle_sha256"),
        "native-zero precompiled source-bundle SHA256",
    )
    if (
        bundle_sha != expected_precompiled_source_bundle_sha256
        or source_manifest.get("prelaunch_launch_manifest_sha256")
        != expected_prelaunch_launch_manifest_sha256
        or import_inventory.get("precompiled_source_bundle_sha256") != bundle_sha
    ):
        _fail("native-zero prelaunch source authority changed")
    source_rows = source_manifest.get("source_fact_rows")
    source_ids = source_manifest.get("source_fact_ids")
    if (
        type(source_rows) is not list
        or type(source_ids) is not list
        or isinstance(expected_native_zero_precompiled_source_rows, (str, bytes))
        or not isinstance(expected_native_zero_precompiled_source_rows, Sequence)
    ):
        _fail("native-zero source fact inventory changed")
    supplied_expected_rows = []
    for row in expected_native_zero_precompiled_source_rows:
        if type(row) is not dict or set(row) != _PRECOMPILED_SOURCE_ROW_FIELDS:
            _fail("bootstrap-verified native-zero source row schema changed")
        supplied_expected_rows.append(dict(row))
    expected_source_ids: list[str] = []
    coordinates: list[tuple[str, str]] = []
    target_source_ids: dict[str, str] = {}
    module_sources: list[Mapping[str, Any]] = []
    for row in source_rows:
        if type(row) is not dict or set(row) != _NATIVE_ZERO_SOURCE_FACT_FIELDS:
            _fail("native-zero source fact field set changed")
        payload = dict(row)
        identity = _cid(
            payload.pop("native_zero_source_fact_id", None),
            "native-zero source fact ID",
        )
        if identity != evidence_domains.extension_content_id_v180r12r3r2e(
            evidence_domains.CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_FACT_V180R12R3R2E_DOMAIN,
            payload,
        ):
            _fail("native-zero source fact content identity changed")
        kind = row.get("source_kind")
        name = row.get("name")
        source_path = row.get("source_path")
        if (
            row.get("schema") != "acfqp.campaign_native_zero_source_fact.v180r12r3r2"
            or row.get("schema_version") != SCHEMA_VERSION
            or row.get("prelaunch_launch_manifest_sha256")
            != expected_prelaunch_launch_manifest_sha256
            or row.get("precompiled_source_bundle_sha256") != bundle_sha
            or kind not in {"MODULE", "TARGET"}
            or type(name) is not str
            or not name
            or type(source_path) is not str
            or not source_path
            or source_path.startswith("/")
            or ".." in source_path.split("/")
            or type(row.get("marshal_byte_count")) is not int
            or row["marshal_byte_count"] <= 0
        ):
            _fail("native-zero source fact semantics changed")
        _cid(row.get("marshal_sha256"), "native-zero source marshal SHA256")
        if kind == "MODULE":
            if (
                type(row.get("is_package")) is not bool
                or any(not component.isidentifier() for component in name.split("."))
                or not (name == "acfqp" or name.startswith("acfqp."))
                or not source_path.startswith("src/acfqp/")
            ):
                _fail("native-zero module source fact changed")
            module_sources.append(row)
        elif (
            row.get("is_package") is not False
            or name not in _PRECOMPILED_TARGET_SOURCE_PATHS
            or source_path != _PRECOMPILED_TARGET_SOURCE_PATHS[name]
        ):
            _fail("native-zero measured-target source fact changed")
        coordinates.append((kind, name))
        expected_source_ids.append(identity)
        if kind == "TARGET":
            target_source_ids[name] = identity
    actual_normalized_rows = [
        {key: row[key] for key in _PRECOMPILED_SOURCE_ROW_FIELDS}
        for row in source_rows
    ]
    if (
        not module_sources
        or coordinates != sorted(set(coordinates))
        or set(target_source_ids) != set(_PRECOMPILED_TARGET_SOURCE_PATHS)
        or source_ids != expected_source_ids
        or actual_normalized_rows != supplied_expected_rows
    ):
        _fail("native-zero source fact order or denominator changed")

    site_rows = source_manifest.get("registered_operation_site_fact_rows")
    site_ids = source_manifest.get("registered_operation_site_fact_ids")
    schedule = _operation_schedule(attempt_id)
    if (
        type(site_rows) is not list
        or type(site_ids) is not list
        or not (len(site_rows) == len(site_ids) == len(schedule) == 314)
    ):
        _fail("native-zero operation-site fact denominator changed")
    expected_site_ids: list[str] = []
    for row, spec in zip(site_rows, schedule):
        if type(row) is not dict or set(row) != _NATIVE_ZERO_OPERATION_SITE_FACT_FIELDS:
            _fail("native-zero operation-site fact field set changed")
        target = _OPERATION_SITE_TARGET_BY_ACTOR[spec["actor_role"]]
        expected = {
            "schema": "acfqp.campaign_native_zero_operation_site_fact.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": attempt_id,
            "operation_id": spec["operation_id"],
            "slot": spec["slot"],
            "family": spec["family"],
            "ordinal": spec["ordinal"],
            "phase": spec["phase"],
            "actor_role": spec["actor_role"],
            "instrumentation_site": (
                f"{target}:{spec['phase']}:{spec['slot']}:{spec['family']}:{spec['ordinal']}"
            ),
            "bound_source_fact_id": target_source_ids[target],
            "comparison_axis_scope": (
                "REGISTERED_PLANNING_COMPARISON_GROUND_KERNEL_TRANSITION_AXIS"
            ),
            "kernel_transition_calls": 0,
            "not_an_os_syscall_count": True,
        }
        expected_id = evidence_domains.extension_content_id_v180r12r3r2e(
            evidence_domains.CONSTRUCTION_K7_NATIVE_ZERO_OPERATION_SITE_FACT_V180R12R3R2E_DOMAIN,
            expected,
        )
        if row != {**expected, "native_zero_operation_site_fact_id": expected_id}:
            _fail("native-zero operation-site fact differs from exact schedule")
        expected_site_ids.append(expected_id)
    if site_ids != expected_site_ids or len(set(site_ids)) != 314:
        _fail("native-zero operation-site fact identity order changed")

    import_rows = import_inventory.get("import_fact_rows")
    import_ids = import_inventory.get("import_fact_ids")
    if type(import_rows) is not list or type(import_ids) is not list:
        _fail("native-zero import fact inventory changed")
    expected_import_rows: list[dict[str, Any]] = []
    for source in module_sources:
        payload = {
            "schema": "acfqp.campaign_native_zero_import_fact.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "precompiled_source_bundle_sha256": bundle_sha,
            "module": source["name"],
            "source_path": source["source_path"],
            "source_fact_id": source["native_zero_source_fact_id"],
            "allowed_actor_roles": ["OBSERVER", "SUPERVISOR", "WORKER"],
            "application_precompiled_loader_only": True,
            "stdlib_runtime_boundary_excluded": True,
        }
        expected_import_rows.append(
            {
                **payload,
                "native_zero_import_fact_id": evidence_domains.extension_content_id_v180r12r3r2e(
                    evidence_domains.CONSTRUCTION_K7_NATIVE_ZERO_IMPORT_FACT_V180R12R3R2E_DOMAIN,
                    payload,
                ),
            }
        )
    expected_import_ids = [
        row["native_zero_import_fact_id"] for row in expected_import_rows
    ]
    if import_rows != expected_import_rows or import_ids != expected_import_ids:
        _fail("native-zero import facts differ from the sealed module allowlist")
    return tuple(site_ids), tuple(source_ids), tuple(import_ids)


def _validate_evidence_graph(
    events: Sequence[Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
    *,
    protocol_id: str,
    authorization_id: str,
    authorization_evidence_id: str,
    attempt_id: str,
    expected_prelaunch_materialization_terminal_id: str,
    expected_prelaunch_launch_manifest_sha256: str,
    expected_precompiled_source_bundle_sha256: str,
    expected_native_zero_precompiled_source_rows: Sequence[Mapping[str, Any]],
    expected_prelaunch_launch_rule_id: str,
    expected_measurement_launch_attempt_id: str,
    expected_subject_id: str,
    expected_source_manifest_id: str,
    expected_import_inventory_id: str,
) -> _EvidenceReplay:
    direct_events = tuple(
        row for row in events if row["payload"]["evidence_id"] is not None
    )
    direct_ids = tuple(row["payload"]["evidence_id"] for row in direct_events)
    direct_schemas = set(_DIRECT_SCHEMA_BY_KIND.values())
    direct_inventory_ids = {
        identity
        for identity, document in documents.items()
        if document.get("schema") in direct_schemas
    }
    if (
        len(direct_ids) != SUCCESS_NONNULL_EVIDENCE_COUNT
        or len(set(direct_ids)) != SUCCESS_NONNULL_EVIDENCE_COUNT
        or set(direct_ids) != direct_inventory_ids
    ):
        _fail("campaign direct event/evidence bijection changed")

    manifest = _one(documents, "acfqp.campaign_operation_manifest.v180r12r3r2")
    expected_manifest = _operation_manifest(attempt_id)
    if manifest != expected_manifest:
        _fail("campaign operation manifest differs from independent derivation")
    manifest_id = manifest["campaign_operation_manifest_id"]

    attempt_record = _one(documents, "acfqp.campaign_attempt_record.v180r12r3r2")
    attempt_record_id = _cid(
        attempt_record.get("campaign_attempt_record_id"),
        "campaign attempt record ID",
    )
    if (
        attempt_record.get("protocol_id") != protocol_id
        or attempt_record.get("authorization_id") != authorization_id
        or attempt_record.get("authorization_evidence_id")
        != authorization_evidence_id
        or attempt_record.get("attempt_id") != attempt_id
        or attempt_record.get("prelaunch_materialization_terminal_id")
        != expected_prelaunch_materialization_terminal_id
        or attempt_record.get("prelaunch_launch_manifest_sha256")
        != expected_prelaunch_launch_manifest_sha256
        or attempt_record.get("prelaunch_launch_rule_id")
        != expected_prelaunch_launch_rule_id
        or attempt_record.get("measurement_launch_attempt_id")
        != expected_measurement_launch_attempt_id
        or attempt_record.get("operation_manifest_id") != manifest_id
        or attempt_record.get("one_shot_attempt_opened") is not True
        or "cgroup_topology_receipt_id" in attempt_record
    ):
        _fail("campaign attempt record pre-cgroup authority changed")

    subject = _one(
        documents, "acfqp.campaign_measurement_subject_result.v180r12r3r2"
    )
    subject_id, subject_byte_count = _validate_subject(
        subject,
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
    )
    if (
        subject_id != expected_subject_id
        or subject.get("campaign_attempt_record_id") != attempt_record_id
        or subject.get("authorization_evidence_id")
        != authorization_evidence_id
        or subject.get("prelaunch_materialization_terminal_id")
        != expected_prelaunch_materialization_terminal_id
        or subject.get("prelaunch_launch_manifest_sha256")
        != expected_prelaunch_launch_manifest_sha256
        or subject.get("prelaunch_launch_rule_id")
        != expected_prelaunch_launch_rule_id
        or subject.get("measurement_launch_attempt_id")
        != expected_measurement_launch_attempt_id
    ):
        _fail("campaign subject provenance differs from the pre-cgroup attempt")
    independently_derived_attempt_id = (
        domains.derive_campaign_measurement_attempt_id_v180r12r3r2(
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            authorization_evidence_id=authorization_evidence_id,
            campaign_measurement_execution_slot_id=subject["execution_slot_id"],
            logical_occurrence_id=subject["logical_occurrence_id"],
            execution_nonce=subject["execution_nonce"],
        )
    )
    if independently_derived_attempt_id != attempt_id:
        _fail("campaign attempt ID differs from independent six-input derivation")

    source_manifest = _one(
        documents, "acfqp.campaign_native_zero_source_manifest.v180r12r3r2"
    )
    import_inventory = _one(
        documents, "acfqp.campaign_native_zero_import_inventory.v180r12r3r2"
    )
    source_id = source_manifest.get("native_zero_source_manifest_id")
    import_id = import_inventory.get("native_zero_import_inventory_id")
    if (
        source_id != expected_source_manifest_id
        or import_id != expected_import_inventory_id
        or source_manifest.get("scope") != CAMPAIGN_SCOPE_KIND
        or import_inventory.get("scope") != CAMPAIGN_SCOPE_KIND
        or source_manifest.get("protocol_id") != protocol_id
        or import_inventory.get("protocol_id") != protocol_id
        or source_manifest.get("authorization_id") != authorization_id
        or import_inventory.get("authorization_id") != authorization_id
        or source_manifest.get("attempt_id") != attempt_id
        or import_inventory.get("attempt_id") != attempt_id
        or source_manifest.get("operation_manifest_id") != manifest_id
        or import_inventory.get("source_manifest_id") != source_id
        or source_manifest.get("unregistered_operation_site_fact_ids") != []
        or source_manifest.get("registered_planning_operation_site_manifest_complete")
        is not True
        or source_manifest.get("unregistered_or_dynamic_sites_forbidden")
        is not True
        or source_manifest.get(
            "third_party_precompiled_sources_in_trusted_runtime_boundary"
        )
        is not True
        or source_manifest.get("open_world_operation_site_absence_claimed")
        is not False
        or import_inventory.get("unregistered_import_fact_ids") != []
        or import_inventory.get("dynamic_import_fact_ids") != []
        or import_inventory.get(
            "prelaunch_sealed_application_import_allowlist_complete"
        )
        is not True
        or import_inventory.get("runtime_role_exit_origin_guard_required") is not True
        or import_inventory.get("stdlib_imports_in_trusted_runtime_boundary")
        is not True
        or import_inventory.get("third_party_imports_in_trusted_runtime_boundary")
        is not True
        or import_inventory.get("trusted_runtime_boundary_namespaces")
        != ["packaging", "stdlib", "tomli"]
        or import_inventory.get("open_world_import_absence_claimed") is not False
    ):
        _fail("campaign native-zero source/import manifest closure changed")
    sites, sources, imports = _validate_native_zero_preregistered_fact_rows(
        source_manifest,
        import_inventory,
        attempt_id=attempt_id,
        expected_prelaunch_launch_manifest_sha256=(
            expected_prelaunch_launch_manifest_sha256
        ),
        expected_precompiled_source_bundle_sha256=(
            expected_precompiled_source_bundle_sha256
        ),
        expected_native_zero_precompiled_source_rows=(
            expected_native_zero_precompiled_source_rows
        ),
    )

    replay_subject = _one(
        documents, "acfqp.campaign_replay_subject_receipt.v180r12r3r2"
    )
    replay_subject_id = replay_subject.get("replay_subject_receipt_id")
    if (
        replay_subject.get("subject_result_id") != subject_id
        or replay_subject.get("subject_byte_count") != subject_byte_count
        or replay_subject.get("campaign_attempt_record_id") != attempt_record_id
        or replay_subject.get("operation_manifest_id") != manifest_id
        or replay_subject.get("native_zero_source_manifest_id") != source_id
        or replay_subject.get("native_zero_import_inventory_id") != import_id
    ):
        _fail("campaign replay-subject authority join changed")

    semantic_ids: list[str] = []
    semantic_ordinals = {
        "SEMANTIC_HASH": 0,
        "INTEGRITY_CHECK": 0,
        "PROTOCOL_CHECK": 0,
    }
    semantic_id_by_coordinate: dict[tuple[str, int], str] = {}
    specs = {
        row["operation_id"]: row for row in _operation_schedule(attempt_id)
    }
    io_by_operation: dict[str, dict[str, Any]] = {}
    mount_rows: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    birth_by_role: dict[str, str] = {}
    reap_by_role: dict[str, str] = {}
    window_event: Mapping[str, Any] | None = None
    cgroup_document: Mapping[str, Any] | None = None
    memory_peak = 0
    for event in direct_events:
        evidence_id = event["payload"]["evidence_id"]
        document = documents.get(evidence_id)
        if document is None or document.get("schema") != _DIRECT_SCHEMA_BY_KIND[
            event["event_kind"]
        ]:
            _fail("campaign event references unknown or mistyped evidence")
        if "operation_id" in document and document.get("operation_id") != event[
            "operation_id"
        ]:
            _fail("campaign event/evidence operation join changed")
        if "measured_value" in document and document.get("measured_value") != event[
            "payload"
        ]["measured_value"]:
            _fail("campaign event/evidence measured-value join changed")
        for field, expected in (
            ("protocol_id", protocol_id),
            ("authorization_id", authorization_id),
            ("attempt_id", attempt_id),
        ):
            if field in document and document.get(field) != expected:
                _fail("campaign event/evidence context join changed")
        kind = event["event_kind"]
        if kind == "ATTEMPT_OPEN":
            if (
                document.get("operation_manifest_id") != manifest_id
                or document.get("one_shot_attempt_opened") is not True
            ):
                _fail("campaign attempt authority changed")
        elif kind in {
            "INPUT_READ_OUTCOME",
            "STAGE_WRITE_OUTCOME",
            "SUBJECT_WRITE_OUTCOME",
        }:
            chunks = document.get("returned_chunk_byte_counts")
            measured = event["payload"]["measured_value"]
            if (
                document.get("event_kind") != kind
                or type(chunks) is not list
                or not chunks
                or any(type(value) is not int or value <= 0 for value in chunks)
                or sum(chunks) != measured
                or document.get("returned_chunk_count") != len(chunks)
                or document.get("returned_byte_count") != measured
                or document.get("transfer_complete") is not True
                or document.get("source_evidence_id") not in documents
                or document.get("target_evidence_id") not in documents
                or document.get("transfer_identity")
                != {
                    "operation_id": event["operation_id"],
                    "event_kind": kind,
                    "source_evidence_id": document.get("source_evidence_id"),
                    "target_evidence_id": document.get("target_evidence_id"),
                }
            ):
                _fail("campaign I/O transfer receipt changed")
            io_by_operation[event["operation_id"]] = dict(document)
        elif kind in {
            "SEMANTIC_HASH_OUTCOME",
            "INTEGRITY_CHECK_OUTCOME",
            "PROTOCOL_CHECK_OUTCOME",
        }:
            expected_kind = {
                "SEMANTIC_HASH_OUTCOME": "SEMANTIC_HASH",
                "INTEGRITY_CHECK_OUTCOME": "INTEGRITY_CHECK",
                "PROTOCOL_CHECK_OUTCOME": "PROTOCOL_CHECK",
            }[kind]
            global_ordinal = semantic_ordinals[expected_kind]
            labels = {
                "SEMANTIC_HASH": SEMANTIC_HASH_OPERATION_LABELS,
                "INTEGRITY_CHECK": INTEGRITY_CHECK_OPERATION_LABELS,
                "PROTOCOL_CHECK": PROTOCOL_CHECK_OPERATION_LABELS,
            }[expected_kind]
            spec = specs[event["operation_id"]]
            expected_auxiliary = _expected_semantic_receipt_auxiliary_values(
                kind=expected_kind,
                ordinal=global_ordinal,
                subject=subject,
            )
            if (
                document.get("attempt_id") != attempt_id
                or document.get("kind") != expected_kind
                or document.get("label") != labels[global_ordinal]
                or document.get("family") != spec["family"]
                or document.get("family_ordinal") != spec["ordinal"]
                or document.get("ordinal") != global_ordinal
                or document.get("operation_manifest_id") != manifest_id
                or document.get("native_zero_source_manifest_id") != source_id
                or document.get("native_zero_import_inventory_id") != import_id
                or document.get("evidence_subject_id") != attempt_record_id
                or document.get("outcome_code") != event["payload"]["outcome_code"]
                or document.get("measured_value") != 1
                or document.get("auxiliary_values") != expected_auxiliary
            ):
                _fail("campaign semantic receipt authority changed")
            semantic_ordinals[expected_kind] += 1
            semantic_ids.append(evidence_id)
            semantic_id_by_coordinate[(expected_kind, global_ordinal)] = evidence_id
        elif kind in {"MOUNT_VISIBILITY_OPEN", "MOUNT_VISIBILITY_CLOSE"}:
            stage_id = document.get("stage_receipt_id")
            stage = documents.get(stage_id)
            expected_state = "OPEN" if kind.endswith("OPEN") else "CLOSED"
            if (
                stage is None
                or stage.get("schema")
                != "acfqp.campaign_memfd_stage_receipt.v180r12r3r2"
                or document.get("state") != expected_state
            ):
                _fail("campaign mount visibility receipt changed")
            mount_rows.append((event, document))
        elif kind == "PROCESS_BIRTH_OUTCOME":
            role = (
                "SUPERVISOR"
                if (event["actor_role"], event["phase"]) == ("OBSERVER", "STAGE")
                else "WORKER"
            )
            if document.get("process_role") != role:
                _fail("campaign process-birth role changed")
            birth_by_role[role] = evidence_id
        elif kind == "PROCESS_REAP":
            role = (
                "SUPERVISOR"
                if (event["actor_role"], event["phase"])
                == ("OBSERVER", "OS_OBSERVE")
                else "WORKER"
            )
            if document.get("process_role") != role:
                _fail("campaign process-reap role changed")
            reap_by_role[role] = evidence_id
        elif kind == "CGROUP_OBSERVED":
            cgroup_document = document
        elif kind == "WINDOW_CLOSED":
            window_event = event

    if (
        len(semantic_ids) != 297
        or replay_subject.get("semantic_operation_receipt_ids")
        != [
            semantic_id_by_coordinate[(kind, ordinal)]
            for kind, count in (
                ("SEMANTIC_HASH", 137),
                ("INTEGRITY_CHECK", 145),
                ("PROTOCOL_CHECK", 15),
            )
            for ordinal in range(count)
        ]
        or semantic_ordinals
        != {"SEMANTIC_HASH": 137, "INTEGRITY_CHECK": 145, "PROTOCOL_CHECK": 15}
        or replay_subject.get("subject_sha256")
        != hashlib.sha256(canonical_json_bytes(subject)).hexdigest()
        or replay_subject.get("producer_module_imported") is not False
        or replay_subject.get("producer_entrypoint_called") is not False
        or replay_subject.get("exact_v180r12r2_verification_replayed") is not True
        or replay_subject.get("route_component_counter_closure_status") != "PASS"
        or replay_subject.get("fresh_replay_cost_only") is not True
        or replay_subject.get("retroactive_v180r12r2_cost_claimed") is not False
    ):
        _fail("campaign semantic/replay-subject denominator changed")

    topology = _one(
        documents, "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2"
    )
    topology_id = topology.get("cgroup_topology_receipt_id")
    topology_nodes, topology_controls = _validate_cgroup_topology(topology)
    if (
        set(birth_by_role) != {"SUPERVISOR", "WORKER"}
        or set(reap_by_role) != {"SUPERVISOR", "WORKER"}
    ):
        _fail("campaign cgroup topology changed")
    for role in ("SUPERVISOR", "WORKER"):
        birth = documents[birth_by_role[role]]
        reap = documents[reap_by_role[role]]
        target = topology_nodes[role]
        nspids = birth.get("pidfd_fdinfo_nspid")
        if (
            birth.get("cgroup_topology_receipt_id") != topology_id
            or birth.get("topology_receipt_id") != topology_id
            or birth.get("attempt_id") != attempt_id
            or birth.get("process_role") != role
            or birth.get("clone3_flags")
            != ["CLONE_INTO_CGROUP", "CLONE_PIDFD"]
            or birth.get("target_cgroup_fd") != target["directory_fd"]
            or birth.get("target_cgroup_device") != target["device"]
            or birth.get("target_cgroup_inode") != target["inode"]
            or birth.get("target_cgroup_path") != target["path"]
            or birth.get("pidfd_fdinfo_pid") != birth.get("pid")
            or type(nspids) is not list
            or not nspids
            or nspids[0] != birth.get("pid")
            or any(type(value) is not int or value <= 0 for value in nspids)
            or birth.get("cgroup_membership_line")
            != f"0::{target['membership_path']}"
            or birth.get("membership_observed_before_work") is not True
            or birth.get("pidfd_cloexec") is not True
            or any(
                type(birth.get(field)) is not int or birth[field] <= 0
                for field in (
                    "pid",
                    "pidfd",
                    "pidfd_device",
                    "pidfd_inode",
                    "proc_starttime_ticks",
                )
            )
            or reap.get("pidfd_birth_receipt_id") != birth_by_role[role]
            or reap.get("process_birth_receipt_id") != birth_by_role[role]
            or reap.get("attempt_id") != attempt_id
            or reap.get("operation_id") != birth.get("operation_id")
            or reap.get("process_role") != role
            or reap.get("pid") != birth.get("pid")
            or reap.get("pidfd_device") != birth.get("pidfd_device")
            or reap.get("pidfd_inode") != birth.get("pidfd_inode")
            or reap.get("proc_starttime_ticks") != birth.get("proc_starttime_ticks")
            or reap.get("waitid_idtype") != "P_PIDFD"
            or reap.get("waitid_pidfd") != birth.get("pidfd")
            or reap.get("waitid_code") != "CLD_EXITED"
            or reap.get("waitid_status") != 0
            or reap.get("pidfd_readable") is not True
            or reap.get("leaf_populated_after_reap") is not False
            or reap.get("leaf_process_count_after_reap") != 0
        ):
            _fail("campaign process birth/reap/topology chain changed")
    if (
        len({documents[value]["pid"] for value in birth_by_role.values()}) != 2
        or len({documents[value]["pidfd"] for value in birth_by_role.values()}) != 2
    ):
        _fail("campaign process identities repeat")
    if cgroup_document is None:
        _fail("campaign final cgroup observation is absent")
    memory_peak = _validate_cgroup_observation(
        cgroup_document,
        topology_id=topology_id,
        controls=topology_controls,
        attempt_id=attempt_id,
    )
    cgroup_event = next(
        event for event in direct_events if event["event_kind"] == "CGROUP_OBSERVED"
    )
    if memory_peak != cgroup_event["payload"]["measured_value"]:
        _fail("campaign cgroup event/receipt peak join changed")

    snapshots = {
        row.get("role"): row
        for row in documents.values()
        if row.get("schema") == "acfqp.campaign_stable_input_snapshot.v180r12r3r2"
    }
    stages = {
        row.get("role"): row
        for row in documents.values()
        if row.get("schema") == "acfqp.campaign_memfd_stage_receipt.v180r12r3r2"
    }
    if set(snapshots) != {"TERMINAL", "VERIFICATION"} or set(stages) != {
        "TERMINAL",
        "VERIFICATION",
    }:
        _fail("campaign input roles changed")
    for role, byte_count in (
        ("TERMINAL", TERMINAL_INPUT_BYTE_COUNT),
        ("VERIFICATION", VERIFICATION_INPUT_BYTE_COUNT),
    ):
        snapshot = snapshots[role]
        stage = stages[role]
        fact = _stable_input_fact(role)
        if (
            snapshot.get("stable_input_fact_id") != fact["stable_input_fact_id"]
            or snapshot.get("observed_byte_count") != byte_count
            or snapshot.get("observed_sha256") != fact["sha256"]
            or snapshot.get("observed_content_id") != fact["content_id"]
            or snapshot.get("canonical_json_replayed") is not True
            or snapshot.get("read_from_frozen_input_only") is not True
            or stage.get("byte_count") != byte_count
            or stage.get("input_snapshot_id")
            != snapshot.get("stable_input_snapshot_id")
            or stage.get("sha256") != snapshot.get("observed_sha256")
            or type(stage.get("supervisor_fd")) is not int
            or stage.get("supervisor_fd") < 0
            or type(stage.get("worker_fd")) is not int
            or stage.get("worker_fd") < 0
            or stage.get("supervisor_fd") == stage.get("worker_fd")
            or type(stage.get("device")) is not int
            or stage.get("device") < 0
            or type(stage.get("inode")) is not int
            or stage.get("inode") < 0
            or stage.get("observed_seals") != list(REQUIRED_MEMFD_SEALS)
            or stage.get("supervisor_cloexec") is not True
            or stage.get("worker_read_only") is not True
            or stage.get("anonymous_inode") is not True
            or stage.get("link_count") != 0
            or type(stage.get("write_probe_errno")) is not int
            or stage.get("write_probe_errno") <= 0
        ):
            _fail("campaign snapshot/stage role join changed")

    for operation_id, receipt in io_by_operation.items():
        spec = specs[operation_id]
        role = "TERMINAL" if spec["ordinal"] == 0 else "VERIFICATION"
        if spec["slot"] == "INPUT_READ" and spec["family"] == "FROZEN_SOURCE":
            expected = (manifest_id, snapshots[role]["stable_input_snapshot_id"])
        elif spec["slot"] == "STAGE_WRITE" and spec["family"] == "SEALED_MEMFD":
            expected = (
                snapshots[role]["stable_input_snapshot_id"],
                stages[role]["memfd_stage_receipt_id"],
            )
        elif spec["slot"] == "INPUT_READ" and spec["family"] == "SEALED_STAGE":
            expected = (
                stages[role]["memfd_stage_receipt_id"],
                birth_by_role["WORKER"],
            )
        elif spec["slot"] == "SUBJECT_WRITE":
            expected = (subject_id, birth_by_role["WORKER"])
        elif spec["slot"] == "INPUT_READ" and spec["family"] == "SUBJECT_READBACK":
            expected = (subject_id, birth_by_role["SUPERVISOR"])
        else:
            _fail("campaign I/O operation escaped its exact graph")
        actual = (
            receipt.get("source_evidence_id"),
            receipt.get("target_evidence_id"),
        )
        if actual != expected or actual[0] == actual[1]:
            _fail("campaign exact eight-I/O evidence graph changed")
    if len(io_by_operation) != 8:
        _fail("campaign exact eight-I/O denominator changed")

    active: dict[str, int] = {}
    seen: set[str] = set()
    open_event_ids: list[str] = []
    open_evidence_ids: list[str] = []
    close_event_ids: list[str] = []
    close_evidence_ids: list[str] = []
    peak = 0
    payload_by_operation: dict[str, str] = {}
    for event, visibility in mount_rows:
        operation_id = event["operation_id"]
        stage_id = visibility["stage_receipt_id"]
        stage = documents[stage_id]
        byte_count = stage["byte_count"]
        role = stage["role"]
        is_open = event["event_kind"] == "MOUNT_VISIBILITY_OPEN"
        if (
            visibility.get("attempt_id") != attempt_id
            or visibility.get("operation_id") != operation_id
            or visibility.get("holder_process_birth_receipt_id")
            != birth_by_role["SUPERVISOR"]
            or visibility.get("holder_role") != "SUPERVISOR"
            or visibility.get("role") != role
            or visibility.get("designated_worker_fd") != stage.get("worker_fd")
            or visibility.get("expected_device") != stage.get("device")
            or visibility.get("expected_inode") != stage.get("inode")
            or visibility.get("unexpected_stage_fds") != []
            or (
                is_open
                and (
                    visibility.get("observed_device") != stage.get("device")
                    or visibility.get("observed_inode") != stage.get("inode")
                    or visibility.get("visible") is not True
                    or visibility.get("read_only") is not True
                )
            )
            or (
                not is_open
                and (
                    visibility.get("observed_device") is not None
                    or visibility.get("observed_inode") is not None
                    or visibility.get("visible") is not False
                    or visibility.get("read_only") is not False
                )
            )
        ):
            _fail("campaign FD visibility OS facts changed")
        if event["event_kind"] == "MOUNT_VISIBILITY_OPEN":
            if stage_id in seen or operation_id in payload_by_operation:
                _fail("campaign mount payload opened twice")
            seen.add(stage_id)
            active[stage_id] = byte_count
            payload_by_operation[operation_id] = stage_id
            aggregate = sum(active.values())
            if event["payload"]["measured_value"] != aggregate:
                _fail("campaign mount OPEN aggregate changed")
            peak = max(peak, aggregate)
            open_event_ids.append(event["event_id"])
            open_evidence_ids.append(event["payload"]["evidence_id"])
        else:
            if (
                payload_by_operation.get(operation_id) != stage_id
                or stage_id not in active
            ):
                _fail("campaign mount CLOSE identity changed")
            del active[stage_id]
            del payload_by_operation[operation_id]
            close_event_ids.append(event["event_id"])
            close_evidence_ids.append(event["payload"]["evidence_id"])
    if active or peak != TOTAL_STAGED_INPUT_BYTE_COUNT:
        _fail("campaign overlapping mount interval replay changed")

    values_by_signature = {
        (event["event_kind"], event["operation_id"]): event["payload"][
            "measured_value"
        ]
        for event in events
    }
    def operation_value(slot: str, family: str, ordinal: int) -> int:
        operation = next(
            row
            for row in specs.values()
            if (row["slot"], row["family"], row["ordinal"])
            == (slot, family, ordinal)
        )
        return values_by_signature[(f"{slot}_OUTCOME", operation["operation_id"])]

    if (
        [operation_value("INPUT_READ", "FROZEN_SOURCE", ordinal) for ordinal in range(2)]
        != [TERMINAL_INPUT_BYTE_COUNT, VERIFICATION_INPUT_BYTE_COUNT]
        or [operation_value("INPUT_READ", "SEALED_STAGE", ordinal) for ordinal in range(2)]
        != [TERMINAL_INPUT_BYTE_COUNT, VERIFICATION_INPUT_BYTE_COUNT]
        or [operation_value("STAGE_WRITE", "SEALED_MEMFD", ordinal) for ordinal in range(2)]
        != [TERMINAL_INPUT_BYTE_COUNT, VERIFICATION_INPUT_BYTE_COUNT]
        or operation_value("INPUT_READ", "SUBJECT_READBACK", 0)
        != subject_byte_count
        or operation_value("SUBJECT_WRITE", "SUBJECT_RESULT", 0)
        != subject_byte_count
    ):
        _fail("campaign exact I/O arithmetic changed")

    if (
        subject.get("operation_manifest_id") != manifest_id
        or set(subject.get("memfd_stage_receipt_ids", []))
        != {row["memfd_stage_receipt_id"] for row in stages.values()}
        or set(subject.get("open_visibility_receipt_ids", []))
        != set(open_evidence_ids)
        or subject.get("terminal_snapshot_id")
        != snapshots["TERMINAL"]["stable_input_snapshot_id"]
        or subject.get("verification_snapshot_id")
        != snapshots["VERIFICATION"]["stable_input_snapshot_id"]
        or subject.get("worker_birth_receipt_id") != birth_by_role["WORKER"]
        or set(replay_subject.get("open_visibility_receipt_ids", []))
        != set(open_evidence_ids)
    ):
        _fail("campaign subject input/evidence joins changed")

    commit = _one(documents, "acfqp.campaign_subject_commit_receipt.v180r12r3r2")
    window = _one(documents, "acfqp.campaign_window_closure_receipt.v180r12r3r2")
    if window_event is None:
        _fail("campaign window-closed event is absent")
    if (
        commit.get("subject_id") != subject_id
        or commit.get("replay_subject_receipt_id") != replay_subject_id
        or commit.get("subject_byte_count") != subject_byte_count
        or commit.get("subject_committed") is not True
        or window.get("subject_commit_receipt_id")
        != commit.get("subject_commit_receipt_id")
        or set(window.get("close_visibility_receipt_ids", []))
        != set(close_evidence_ids)
        or window.get("window_closed") is not True
        or window.get("all_registered_mounts_closed") is not True
    ):
        _fail("campaign subject commit/window closure changed")

    cgroup = _one(
        documents, "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2"
    )
    if (
        cgroup.get("topology_receipt_id") != topology_id
        or cgroup.get("supervisor_reap_receipt_id") != reap_by_role["SUPERVISOR"]
        or cgroup.get("worker_reap_receipt_id") != reap_by_role["WORKER"]
    ):
        _fail("campaign cgroup topology/reap observation join changed")

    execution = _one(documents, "acfqp.campaign_execution_closure.v180r12r3r2")
    execution_id = execution.get("campaign_execution_closure_id")
    if (
        execution.get("protocol_id") != protocol_id
        or execution.get("authorization_id") != authorization_id
        or execution.get("attempt_id") != attempt_id
        or execution.get("subject_id") != subject_id
        or execution.get("window_closed_event_id") != window_event["event_id"]
        or execution.get("window_closure_receipt_id")
        != window.get("window_closure_receipt_id")
        or execution.get("operation_manifest_id") != manifest_id
        or execution.get("source_manifest_id") != source_id
        or execution.get("import_inventory_id") != import_id
        or execution.get("precompiled_source_bundle_sha256")
        != expected_precompiled_source_bundle_sha256
        or execution.get("comparison_axis") != "kernel_transition_calls"
        or execution.get("kernel_transition_calls") != 0
        or execution.get("registered_planning_operation_site_fact_count") != 314
        or execution.get("kernel_transition_operation_site_fact_ids") != []
        or execution.get("kernel_transition_import_fact_ids") != []
        or execution.get("unregistered_operation_site_fact_ids") != []
        or execution.get("unregistered_import_fact_ids") != []
        or execution.get("registered_planning_comparison_ground_kernel_axis_only")
        is not True
        or execution.get("prelaunch_sealed_application_import_allowlist_only")
        is not True
        or execution.get("runtime_role_exit_origin_guard_required") is not True
        or execution.get("runtime_role_exit_origin_guard_status")
        != "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
        or execution.get("not_an_os_syscall_count") is not True
        or execution.get("unregistered_or_dynamic_sites_forbidden") is not True
        or execution.get("closed_registered_planning_operation_window_only")
        is not True
        or execution.get("open_world_absence_claimed") is not False
        or execution.get("execution_window_closed") is not True
    ):
        _fail("campaign execution-closure native-zero authority changed")

    return _EvidenceReplay(
        subject_id,
        subject_byte_count,
        manifest_id,
        source_id,
        import_id,
        execution_id,
        window_event["event_id"],
        tuple(open_event_ids),
        tuple(open_evidence_ids),
        tuple(close_event_ids),
        tuple(close_evidence_ids),
        memory_peak,
    )


@dataclass(frozen=True, slots=True)
class _AccountingReplay:
    path_receipts: tuple[dict[str, Any], ...]
    counter_records: tuple[dict[str, Any], ...]
    receipt_set: dict[str, Any]
    work_vector: dict[str, Any]
    comparison_vector: dict[str, Any]
    projection_proof: dict[str, Any]
    native_zero_attestation: dict[str, Any]


def _derive_accounting(
    events: Sequence[Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
    facts: _EvidenceReplay,
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
) -> _AccountingReplay:
    path_receipts: list[dict[str, Any]] = []
    expected_values = {
        "common.hash_invocations": 137,
        "common.integrity_checks": 145,
        "common.protocol_checks": 15,
        "io.mounted_bytes_peak": TOTAL_STAGED_INPUT_BYTE_COUNT,
        "io.output_bytes": facts.subject_byte_count,
        "io.read_bytes": 2 * TOTAL_STAGED_INPUT_BYTE_COUNT
        + facts.subject_byte_count,
        "io.staged_bytes": TOTAL_STAGED_INPUT_BYTE_COUNT,
        "memory.working_bytes_peak": facts.memory_peak_bytes,
        "process.launches": 2,
    }
    for path in CAMPAIGN_PATHS:
        path_events = tuple(
            row for row in events if _COUNTER_PATH_BY_KIND.get(row["event_kind"]) == path
        )
        if not path_events:
            _fail("campaign accounting path has no raw event")
        if path == "io.mounted_bytes_peak":
            value = TOTAL_STAGED_INPUT_BYTE_COUNT
            counter_event_ids = list(facts.mount_open_event_ids)
            evidence_ids = list(facts.mount_open_evidence_ids)
            closure_event_ids = list(facts.mount_close_event_ids)
            closure_evidence_ids = list(facts.mount_close_evidence_ids)
        else:
            values = [row["payload"]["measured_value"] for row in path_events]
            reducer = _LEAF_METADATA[path][4]
            value = sum(values) if reducer == "sum" else max(values)
            counter_event_ids = [row["event_id"] for row in path_events]
            evidence_ids = [row["payload"]["evidence_id"] for row in path_events]
            closure_event_ids = []
            closure_evidence_ids = []
        if value != expected_values[path] or value <= 0:
            _fail("campaign nine-path arithmetic changed")
        payload = {
            "schema": "acfqp.campaign_path_receipt.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "subject_id": facts.subject_id,
            **_leaf(path),
            "value": value,
            "observed": True,
            "actual_measurement_present": True,
            "counter_event_ids": counter_event_ids,
            "evidence_ids": evidence_ids,
            "closure_event_ids": closure_event_ids,
            "closure_evidence_ids": closure_evidence_ids,
            "window_closed_event_id": facts.window_closed_event_id,
            "native_zero_observed": False,
        }
        path_receipts.append(
            _signed_subrecord(
                payload,
                domain=evidence_domains.CONSTRUCTION_K7_CAMPAIGN_PATH_RECEIPT_V180R12R3R2E_DOMAIN,
                identity_field="campaign_path_receipt_id",
            )
        )

    counter_records: list[dict[str, Any]] = []
    for receipt in path_receipts:
        path = receipt["path"]
        payload = {
            "schema": "acfqp.campaign_counter_record.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "subject_id": facts.subject_id,
            **_leaf(path),
            "value": receipt["value"],
            "observed": True,
            "campaign_path_receipt_id": receipt["campaign_path_receipt_id"],
            "native_zero_observed": False,
        }
        counter_records.append(
            _signed_subrecord(
                payload,
                domain=evidence_domains.CONSTRUCTION_K7_CAMPAIGN_COUNTER_RECORD_V180R12R3R2E_DOMAIN,
                identity_field="counter_record_id",
            )
        )

    receipt_set_payload = {
        "schema": "acfqp.campaign_receipt_set.v180r12r3r2",
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "subject_id": facts.subject_id,
        "ordered_paths": list(CAMPAIGN_PATHS),
        "ordered_campaign_path_receipt_ids": [
            row["campaign_path_receipt_id"] for row in path_receipts
        ],
        "campaign_path_receipt_count": 9,
    }
    receipt_set = _signed_subrecord(
        receipt_set_payload,
        domain=evidence_domains.CONSTRUCTION_K7_CAMPAIGN_RECEIPT_SET_V180R12R3R2E_DOMAIN,
        identity_field="campaign_receipt_set_id",
    )
    work_payload = {
        "schema": "acfqp.campaign_work_vector.v180r12r3r2",
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "scope_model": CAMPAIGN_SCOPE_MODEL,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "subject_id": facts.subject_id,
        "campaign_receipt_set_id": receipt_set["campaign_receipt_set_id"],
        "ordered_counter_record_ids": [
            row["counter_record_id"] for row in counter_records
        ],
        "counter_record_count": 9,
        "ordered_paths": list(CAMPAIGN_PATHS),
    }
    work = _signed_subrecord(
        work_payload,
        domain=evidence_domains.CONSTRUCTION_K7_CAMPAIGN_WORK_VECTOR_V180R12R3R2E_DOMAIN,
        identity_field="campaign_work_vector_id",
    )

    execution = documents[facts.execution_closure_id]
    zero_payload = {
        "schema": "acfqp.campaign_native_zero_attestation.v180r12r3r2",
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "scope_model": CAMPAIGN_SCOPE_MODEL,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "subject_id": facts.subject_id,
        "campaign_work_vector_id": work["campaign_work_vector_id"],
        "window_closed_event_id": facts.window_closed_event_id,
        "campaign_execution_closure_id": facts.execution_closure_id,
        "registered_operation_manifest_id": facts.operation_manifest_id,
        "native_zero_source_manifest_id": facts.source_manifest_id,
        "native_zero_import_inventory_id": facts.import_inventory_id,
        "comparison_axis": "kernel_transition_calls",
        "comparison_axis_value": 0,
        "axis_definition": (
            "REGISTERED_PLANNING_COMPARISON_GROUND_KERNEL_TRANSITION_AXIS"
        ),
        "not_an_os_syscall_count": True,
        "unregistered_or_dynamic_sites_forbidden": True,
        "registered_planning_operation_site_fact_count": 314,
        "prelaunch_sealed_application_import_allowlist_only": True,
        "runtime_role_exit_origin_guard_required": True,
        "runtime_role_exit_origin_guard_status": (
            "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
        ),
        "closed_registered_planning_operation_window_only": True,
        "open_world_absence_claimed": False,
        "campaign_path_zero_observation_count": 0,
        "all_nine_campaign_paths_strictly_positive": True,
        "separate_from_nine_campaign_paths": True,
    }
    if execution.get("kernel_transition_calls") != 0:
        _fail("campaign native-zero execution fact changed")
    zero = _signed_subrecord(
        zero_payload,
        domain=evidence_domains.CONSTRUCTION_K7_CAMPAIGN_NATIVE_ZERO_ATTESTATION_V180R12R3R2E_DOMAIN,
        identity_field="campaign_native_zero_attestation_id",
    )

    axis_values: dict[str, int] = {axis: 0 for axis in SHARED_AXES}
    for record in counter_records:
        _semantics, _owner, _unit, _scope, reducer, axis = _LEAF_METADATA[
            record["path"]
        ]
        if reducer == "sum":
            axis_values[axis] += record["value"]
        else:
            axis_values[axis] = max(axis_values[axis], record["value"])
    comparison_payload = {
        "schema": "acfqp.campaign_comparison_vector.v180r12r3r2",
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "scope_model": CAMPAIGN_SCOPE_MODEL,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "subject_id": facts.subject_id,
        "campaign_work_vector_id": work["campaign_work_vector_id"],
        "campaign_native_zero_attestation_id": zero[
            "campaign_native_zero_attestation_id"
        ],
        "values": [
            {
                "axis": axis,
                "value": axis_values[axis],
                "reducer": (
                    "max"
                    if axis in {"peak_mounted_bytes", "peak_working_bytes"}
                    else "sum"
                ),
            }
            for axis in SHARED_AXES
        ],
    }
    comparison = _signed_subrecord(
        comparison_payload,
        domain=evidence_domains.CONSTRUCTION_K7_CAMPAIGN_COMPARISON_VECTOR_V180R12R3R2E_DOMAIN,
        identity_field="campaign_comparison_vector_id",
    )

    terms = [
        {
            "source_path": record["path"],
            "source_counter_record_id": record["counter_record_id"],
            "source_campaign_path_receipt_id": record[
                "campaign_path_receipt_id"
            ],
            "source_semantics_id": _LEAF_METADATA[record["path"]][0],
            "source_lane": "operational",
            "target_axis": _LEAF_METADATA[record["path"]][5],
            "coefficient": 1,
            "reducer": _LEAF_METADATA[record["path"]][4],
        }
        for record in counter_records
    ]
    projection_payload = {
        "schema": "acfqp.campaign_projection_proof.v180r12r3r2",
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "scope_model": CAMPAIGN_SCOPE_MODEL,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "subject_id": facts.subject_id,
        "campaign_work_vector_id": work["campaign_work_vector_id"],
        "campaign_comparison_vector_id": comparison[
            "campaign_comparison_vector_id"
        ],
        "campaign_native_zero_attestation_id": zero[
            "campaign_native_zero_attestation_id"
        ],
        "projection_terms": terms,
        "projection_term_count": 9,
        "native_zero_projection_term": {
            "source_campaign_native_zero_attestation_id": zero[
                "campaign_native_zero_attestation_id"
            ],
            "target_axis": "kernel_transition_calls",
            "value": 0,
            "separate_from_nine_campaign_paths": True,
        },
        "native_zero_projection_term_count": 1,
        "projection_proof_references_native_zero_attestation": True,
        "all_operational_leaves_projected_once": True,
        "sum_and_max_reducers_replayed": True,
    }
    projection = _signed_subrecord(
        projection_payload,
        domain=evidence_domains.CONSTRUCTION_K7_CAMPAIGN_PROJECTION_PROOF_V180R12R3R2E_DOMAIN,
        identity_field="campaign_projection_proof_id",
    )
    return _AccountingReplay(
        tuple(path_receipts),
        tuple(counter_records),
        receipt_set,
        work,
        comparison,
        projection,
        zero,
    )


def _expected_closure(
    candidate: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    evidence_rows: Sequence[Mapping[str, Any]],
    facts: _EvidenceReplay,
    accounting: _AccountingReplay,
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
) -> dict[str, Any]:
    event_bytes = sum(len(canonical_json_bytes(row)) for row in events)
    type_counts = {
        schema: descriptor[2] for schema, descriptor in _EVIDENCE_DESCRIPTOR.items()
    }
    pending_join = {
        "counter_status": "PENDING_INDEPENDENT_REPLAY",
        "predecessor_occurrence_receipt_count": 90,
        "campaign_actual_receipt_count": 9,
        "combined_authoritative_receipt_count": 99,
    }
    pass_join = {
        "counter_status": "PASS",
        "predecessor_occurrence_receipt_count": 90,
        "campaign_actual_receipt_count": 9,
        "combined_authoritative_receipt_count": 99,
    }
    payload = {
        "schema": "acfqp.campaign_measurement_ledger_closure.v180r12r3r2",
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "scope_model": CAMPAIGN_SCOPE_MODEL,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "subject_id": facts.subject_id,
        "campaign_operation_manifest_id": facts.operation_manifest_id,
        "native_zero_source_manifest_id": facts.source_manifest_id,
        "native_zero_import_inventory_id": facts.import_inventory_id,
        "campaign_execution_closure_id": facts.execution_closure_id,
        "max_event_count": candidate.get("max_event_count"),
        "max_event_byte_count": candidate.get("max_event_byte_count"),
        "max_ledger_byte_count": candidate.get("max_ledger_byte_count"),
        "events": list(events),
        "ordered_event_ids": [row["event_id"] for row in events],
        "event_count": SUCCESS_EVENT_COUNT,
        "ledger_event_byte_count": event_bytes,
        "first_event_id": events[0]["event_id"],
        "last_event_id": events[-1]["event_id"],
        "evidence_documents": list(evidence_rows),
        "campaign_evidence_document_count": SUCCESS_EVIDENCE_DOCUMENT_COUNT,
        "direct_event_evidence_document_count": SUCCESS_NONNULL_EVIDENCE_COUNT,
        "support_evidence_document_count": 11,
        "campaign_evidence_document_type_counts": type_counts,
        "event_evidence_nonnull_count": SUCCESS_NONNULL_EVIDENCE_COUNT,
        "event_evidence_null_count": SUCCESS_NULL_EVIDENCE_COUNT,
        "path_receipts": list(accounting.path_receipts),
        "campaign_receipt_set": accounting.receipt_set,
        "counter_records": list(accounting.counter_records),
        "campaign_work_vector": accounting.work_vector,
        "campaign_comparison_vector": accounting.comparison_vector,
        "campaign_projection_proof": accounting.projection_proof,
        "campaign_native_zero_attestation": accounting.native_zero_attestation,
        "campaign_path_receipt_count": 9,
        "campaign_counter_record_count": 9,
        "campaign_work_vector_count": 1,
        "campaign_comparison_vector_count": 1,
        "campaign_projection_proof_count": 1,
        "campaign_native_zero_attestation_count": 1,
        "predecessor_occurrence_authoritative_receipt_count": 90,
        "predecessor_structural_obligation_count": 9,
        "predecessor_campaign_scope_structural_obligation_count": 9,
        "predecessor_campaign_actual_receipt_count": 0,
        "predecessor_campaign_authoritative_receipt_count": 0,
        "successor_campaign_actual_receipt_count": 9,
        "successor_campaign_counter_record_count": 9,
        "combined_successor_authoritative_receipt_count": 99,
        "successful_campaign_authoritative_receipt_count": 9,
        "successful_combined_authoritative_receipt_count": 99,
        "terminal_pending_authoritative_receipt_join": pending_join,
        "independent_verifier_pass_authoritative_receipt_join": pass_join,
        "predecessor_structural_nine_are_successor_actual_receipts": False,
        "predecessor_structural_obligations_are_not_current_measurements": True,
        "authoritative_receipt_arithmetic_90_plus_9_equals_99": True,
        "hash_chain_complete": True,
        "lifecycle_phase_order_complete": True,
        "actual_measurements_present": True,
        "all_nine_campaign_paths_strictly_positive": True,
        "independent_comparison_axis_native_zero_complete": True,
        "route_free_campaign_accounting": True,
        "independent_verification_present": False,
        "COUNTER_COMPLETENESS_GATE": "PENDING_INDEPENDENT_REPLAY",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "v180r13_weight_agnostic_economics_input_ready": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "scientific_success_claimed": False,
    }
    return _signed_subrecord(
        payload,
        domain=evidence_domains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_CLOSURE_V180R12R3R2E_DOMAIN,
        identity_field="campaign_ledger_closure_id",
    )


def _os_document_identity(document: Mapping[str, Any]) -> str:
    schema = document.get("schema")
    descriptor = _EVIDENCE_DESCRIPTOR.get(schema)
    if schema not in OS_EVIDENCE_SCHEMA_COUNTS or descriptor is None:
        _fail("terminal OS receipt escaped the exact twelve-document subset")
    return _cid(document.get(descriptor[1]), "terminal OS receipt identity")


def _validate_terminal_os_receipts(
    terminal: Mapping[str, Any],
    documents: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    rows = terminal.get("os_receipt_documents")
    if type(rows) is not list or len(rows) != sum(OS_EVIDENCE_SCHEMA_COUNTS.values()):
        _fail("terminal must embed exactly twelve OS evidence documents")
    if any(type(row) is not dict for row in rows):
        _fail("terminal OS receipt rows must be exact objects")
    identities = [_os_document_identity(row) for row in rows]
    expected = tuple(
        sorted(
            (
                dict(row)
                for row in documents.values()
                if row.get("schema") in OS_EVIDENCE_SCHEMA_COUNTS
            ),
            key=_os_document_identity,
        )
    )
    counts = {
        schema: sum(row.get("schema") == schema for row in rows)
        for schema in OS_EVIDENCE_SCHEMA_COUNTS
    }
    if (
        identities != sorted(set(identities))
        or tuple(rows) != expected
        or counts != OS_EVIDENCE_SCHEMA_COUNTS
        or terminal.get("os_receipt_ids") != identities
        or terminal.get("os_receipt_schema_counts") != OS_EVIDENCE_SCHEMA_COUNTS
        or terminal.get("os_receipt_document_count") != len(expected)
    ):
        _fail("terminal OS receipts differ from the registered evidence inventory")
    return expected


def _evidence_document_identity(document: Mapping[str, Any]) -> str:
    descriptor = _EVIDENCE_DESCRIPTOR.get(document.get("schema"))
    if descriptor is None:
        _fail("success artifact evidence schema is unregistered")
    return _cid(document.get(descriptor[1]), "success artifact evidence identity")


def _validate_separate_success_artifacts(
    *,
    inventory_bundle_bytes: bytes,
    execution_closure_bytes: bytes,
    os_receipt_bundle_bytes: bytes,
    ledger_closure_bytes: bytes,
    closure: Mapping[str, Any],
    documents: Mapping[str, Mapping[str, Any]],
    os_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, bytes]:
    supplied = {
        "evidence_inventory": inventory_bundle_bytes,
        "execution_closure": execution_closure_bytes,
        "os_receipt": os_receipt_bundle_bytes,
        "ledger_closure": ledger_closure_bytes,
    }
    if any(type(raw) is not bytes or not raw for raw in supplied.values()):
        _fail("four durable success artifacts must be nonempty canonical bytes")

    ordered_documents = [dict(row) for row in closure["evidence_documents"]]
    ordered_ids = [_evidence_document_identity(row) for row in ordered_documents]
    inventory_payload = {
        "schema": EVIDENCE_INVENTORY_BUNDLE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "protocol_id": closure["protocol_id"],
        "authorization_id": closure["authorization_id"],
        "attempt_id": closure["attempt_id"],
        "evidence_document_count": SUCCESS_EVIDENCE_DOCUMENT_COUNT,
        "evidence_document_type_counts": {
            schema: descriptor[2]
            for schema, descriptor in _EVIDENCE_DESCRIPTOR.items()
        },
        "ordered_evidence_document_ids": ordered_ids,
        "evidence_documents": ordered_documents,
    }
    inventory_document = {
        **inventory_payload,
        "campaign_evidence_inventory_bundle_id": (
            domains.extension_content_id_v180r12r3r2(
                domains.CONSTRUCTION_K7_CAMPAIGN_EVIDENCE_INVENTORY_BUNDLE_V180R12R3R2_DOMAIN,
                inventory_payload,
            )
        ),
    }
    if frozenset(inventory_document) != EVIDENCE_INVENTORY_BUNDLE_FIELDS:
        _fail("reconstructed evidence inventory bundle keyset changed")
    expected_inventory = canonical_json_bytes(inventory_document)

    execution_rows = [
        dict(row)
        for row in documents.values()
        if row.get("schema") == "acfqp.campaign_execution_closure.v180r12r3r2"
    ]
    if len(execution_rows) != 1:
        _fail("separate execution-closure denominator changed")
    expected_execution = canonical_json_bytes(execution_rows[0])

    os_payload = {
        "schema": OS_RECEIPT_BUNDLE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "protocol_id": closure["protocol_id"],
        "authorization_id": closure["authorization_id"],
        "attempt_id": closure["attempt_id"],
        "campaign_evidence_inventory_bundle_id": inventory_document[
            "campaign_evidence_inventory_bundle_id"
        ],
        "os_receipt_document_count": sum(OS_EVIDENCE_SCHEMA_COUNTS.values()),
        "os_receipt_schema_counts": dict(OS_EVIDENCE_SCHEMA_COUNTS),
        "ordered_os_receipt_ids": [
            _os_document_identity(row) for row in os_receipts
        ],
        "os_receipt_documents": [dict(row) for row in os_receipts],
    }
    os_document = {
        **os_payload,
        "campaign_os_receipt_bundle_id": domains.extension_content_id_v180r12r3r2(
            domains.CONSTRUCTION_K7_CAMPAIGN_OS_RECEIPT_BUNDLE_V180R12R3R2_DOMAIN,
            os_payload,
        ),
    }
    if frozenset(os_document) != OS_RECEIPT_BUNDLE_FIELDS:
        _fail("reconstructed OS receipt bundle keyset changed")
    expected_os = canonical_json_bytes(os_document)
    expected_ledger = canonical_json_bytes(closure)
    expected = {
        "evidence_inventory": expected_inventory,
        "execution_closure": expected_execution,
        "os_receipt": expected_os,
        "ledger_closure": expected_ledger,
    }
    for label, raw in supplied.items():
        _canonical_document(raw, f"separate {label} success artifact")
        if raw != expected[label]:
            _fail(f"separate {label} success artifact differs from reconstruction")
    return expected


def _terminal_payload(
    closure: Mapping[str, Any],
    os_receipts: Sequence[Mapping[str, Any]],
    success_artifacts: Mapping[str, bytes],
    *,
    output_bytes_fixed_point: int,
) -> dict[str, Any]:
    attempt_rows = [
        row
        for row in closure.get("evidence_documents", [])
        if type(row) is dict
        and row.get("schema") == "acfqp.campaign_attempt_record.v180r12r3r2"
    ]
    if len(attempt_rows) != 1:
        _fail("terminal reconstruction lacks one exact campaign attempt record")
    attempt_record = attempt_rows[0]
    closure_bytes = success_artifacts["ledger_closure"]
    inventory_bytes = success_artifacts["evidence_inventory"]
    _inventory_raw, inventory = _canonical_document(
        inventory_bytes, "reconstructed evidence inventory bundle"
    )
    execution_bytes = success_artifacts["execution_closure"]
    _execution_raw, execution = _canonical_document(
        execution_bytes, "reconstructed execution closure"
    )
    os_bundle_bytes = success_artifacts["os_receipt"]
    _os_raw, os_bundle = _canonical_document(
        os_bundle_bytes, "reconstructed OS receipt bundle"
    )
    return {
        "schema": TERMINAL_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "scope_model": CAMPAIGN_SCOPE_MODEL,
        "protocol_id": closure["protocol_id"],
        "authorization_id": closure["authorization_id"],
        "authorization_evidence_id": attempt_record[
            "authorization_evidence_id"
        ],
        "attempt_id": closure["attempt_id"],
        "prelaunch_materialization_terminal_id": attempt_record[
            "prelaunch_materialization_terminal_id"
        ],
        "prelaunch_launch_manifest_sha256": attempt_record[
            "prelaunch_launch_manifest_sha256"
        ],
        "precompiled_source_bundle_sha256": execution[
            "precompiled_source_bundle_sha256"
        ],
        "prelaunch_launch_rule_id": attempt_record[
            "prelaunch_launch_rule_id"
        ],
        "measurement_launch_attempt_id": attempt_record[
            "measurement_launch_attempt_id"
        ],
        "subject_id": closure["subject_id"],
        "campaign_operation_manifest_id": closure[
            "campaign_operation_manifest_id"
        ],
        "native_zero_source_manifest_id": closure[
            "native_zero_source_manifest_id"
        ],
        "native_zero_import_inventory_id": closure[
            "native_zero_import_inventory_id"
        ],
        "campaign_execution_closure_id": closure[
            "campaign_execution_closure_id"
        ],
        "campaign_execution_closure_byte_count": len(execution_bytes),
        "campaign_execution_closure_sha256": hashlib.sha256(
            execution_bytes
        ).hexdigest(),
        "campaign_evidence_inventory_bundle_id": inventory[
            "campaign_evidence_inventory_bundle_id"
        ],
        "campaign_evidence_inventory_bundle_byte_count": len(inventory_bytes),
        "campaign_evidence_inventory_bundle_sha256": hashlib.sha256(
            inventory_bytes
        ).hexdigest(),
        "campaign_os_receipt_bundle_id": os_bundle[
            "campaign_os_receipt_bundle_id"
        ],
        "campaign_os_receipt_bundle_byte_count": len(os_bundle_bytes),
        "campaign_os_receipt_bundle_sha256": hashlib.sha256(
            os_bundle_bytes
        ).hexdigest(),
        "campaign_ledger_closure_id": closure["campaign_ledger_closure_id"],
        "campaign_ledger_closure_byte_count": len(closure_bytes),
        "campaign_ledger_closure_sha256": hashlib.sha256(closure_bytes).hexdigest(),
        "campaign_measurement_ledger": dict(closure),
        "os_receipt_documents": [dict(row) for row in os_receipts],
        "os_receipt_ids": [_os_document_identity(row) for row in os_receipts],
        "os_receipt_schema_counts": dict(OS_EVIDENCE_SCHEMA_COUNTS),
        "event_count": SUCCESS_EVENT_COUNT,
        "evidence_document_count": SUCCESS_EVIDENCE_DOCUMENT_COUNT,
        "os_receipt_document_count": sum(OS_EVIDENCE_SCHEMA_COUNTS.values()),
        "campaign_path_receipt_count": 9,
        "campaign_counter_record_count": 9,
        "campaign_work_vector_count": 1,
        "campaign_comparison_vector_count": 1,
        "campaign_projection_proof_count": 1,
        "campaign_native_zero_attestation_count": 1,
        "predecessor_occurrence_authoritative_receipt_count": 90,
        "successor_campaign_authoritative_receipt_count": 9,
        "combined_successor_authoritative_receipt_count": 99,
        "authoritative_receipt_arithmetic_90_plus_9_equals_99": True,
        "raw_event_evidence_and_os_receipts_replayed": True,
        "route_free_campaign_accounting": True,
        "all_nine_campaign_paths_strictly_positive": True,
        "independent_native_zero_attestation_present": True,
        "independent_verification_present": False,
        "V180R12R3R2_CAMPAIGN_COUNTER_CLOSURE_STATUS": (
            "PENDING_INDEPENDENT_REPLAY"
        ),
        "COUNTER_COMPLETENESS_GATE": "PENDING_INDEPENDENT_REPLAY",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "v180r13_weight_agnostic_economics_input_ready": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "scientific_success_claimed": False,
        "output_bytes_fixed_point": output_bytes_fixed_point,
    }


def _expected_terminal_bytes(
    closure: Mapping[str, Any],
    os_receipts: Sequence[Mapping[str, Any]],
    success_artifacts: Mapping[str, bytes],
) -> bytes:
    fixed_point = 0
    for _iteration in range(32):
        payload = _terminal_payload(
            closure,
            os_receipts,
            success_artifacts,
            output_bytes_fixed_point=fixed_point,
        )
        document = {
            **payload,
            "campaign_measurement_terminal_id": domains.extension_content_id_v180r12r3r2(
                domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R3R2_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == fixed_point:
            return raw
        fixed_point = len(raw)
    _fail("independent terminal byte fixed point did not converge")


def _verification_payload(
    *,
    terminal_bytes: bytes,
    terminal: Mapping[str, Any],
    closure: Mapping[str, Any],
    facts: _EvidenceReplay,
    accounting: _AccountingReplay,
    os_receipts: Sequence[Mapping[str, Any]],
    success_artifacts: Mapping[str, bytes],
    measurement_launch_receipt_bytes: bytes,
    measurement_launch_receipt_id: str,
) -> dict[str, Any]:
    attempt_rows = [
        row
        for row in closure.get("evidence_documents", [])
        if type(row) is dict
        and row.get("schema") == "acfqp.campaign_attempt_record.v180r12r3r2"
    ]
    if len(attempt_rows) != 1:
        _fail("verification reconstruction lacks one exact campaign attempt record")
    attempt_record = attempt_rows[0]
    closure_bytes = success_artifacts["ledger_closure"]
    inventory_bytes = success_artifacts["evidence_inventory"]
    _inventory_raw, inventory = _canonical_document(
        inventory_bytes, "verified evidence inventory bundle"
    )
    execution_bytes = success_artifacts["execution_closure"]
    os_bundle_bytes = success_artifacts["os_receipt"]
    _os_raw, os_bundle = _canonical_document(
        os_bundle_bytes, "verified OS receipt bundle"
    )
    return {
        "schema": VERIFICATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "scope_model": CAMPAIGN_SCOPE_MODEL,
        "protocol_id": closure["protocol_id"],
        "authorization_id": closure["authorization_id"],
        "authorization_evidence_id": attempt_record[
            "authorization_evidence_id"
        ],
        "attempt_id": closure["attempt_id"],
        "prelaunch_materialization_terminal_id": attempt_record[
            "prelaunch_materialization_terminal_id"
        ],
        "prelaunch_launch_manifest_sha256": attempt_record[
            "prelaunch_launch_manifest_sha256"
        ],
        "precompiled_source_bundle_sha256": terminal[
            "precompiled_source_bundle_sha256"
        ],
        "prelaunch_launch_rule_id": attempt_record[
            "prelaunch_launch_rule_id"
        ],
        "measurement_launch_attempt_id": attempt_record[
            "measurement_launch_attempt_id"
        ],
        "measurement_launch_receipt_id": measurement_launch_receipt_id,
        "measurement_launch_receipt_byte_count": len(
            measurement_launch_receipt_bytes
        ),
        "measurement_launch_receipt_sha256": hashlib.sha256(
            measurement_launch_receipt_bytes
        ).hexdigest(),
        "runtime_role_exit_origin_guard_status": (
            "PASS_TRANSITIVE_FROZEN_BOOTSTRAP_AND_MEASUREMENT_LAUNCH_RECEIPT"
        ),
        "measurement_launch_receipt_directly_observes_origin_guard": False,
        "frozen_bootstrap_post_dispatch_origin_guard_transitively_supported": True,
        "subject_id": facts.subject_id,
        "campaign_measurement_terminal_id": terminal[
            "campaign_measurement_terminal_id"
        ],
        "campaign_measurement_terminal_byte_count": len(terminal_bytes),
        "campaign_measurement_terminal_sha256": hashlib.sha256(
            terminal_bytes
        ).hexdigest(),
        "campaign_ledger_closure_id": closure["campaign_ledger_closure_id"],
        "campaign_ledger_closure_byte_count": len(closure_bytes),
        "campaign_ledger_closure_sha256": hashlib.sha256(closure_bytes).hexdigest(),
        "campaign_evidence_inventory_bundle_id": inventory[
            "campaign_evidence_inventory_bundle_id"
        ],
        "campaign_evidence_inventory_bundle_byte_count": len(inventory_bytes),
        "campaign_evidence_inventory_bundle_sha256": hashlib.sha256(
            inventory_bytes
        ).hexdigest(),
        "campaign_operation_manifest_id": facts.operation_manifest_id,
        "native_zero_source_manifest_id": facts.source_manifest_id,
        "native_zero_import_inventory_id": facts.import_inventory_id,
        "campaign_execution_closure_id": facts.execution_closure_id,
        "campaign_execution_closure_byte_count": len(execution_bytes),
        "campaign_execution_closure_sha256": hashlib.sha256(
            execution_bytes
        ).hexdigest(),
        "campaign_os_receipt_bundle_id": os_bundle[
            "campaign_os_receipt_bundle_id"
        ],
        "campaign_os_receipt_bundle_byte_count": len(os_bundle_bytes),
        "campaign_os_receipt_bundle_sha256": hashlib.sha256(
            os_bundle_bytes
        ).hexdigest(),
        "campaign_receipt_set_id": accounting.receipt_set[
            "campaign_receipt_set_id"
        ],
        "campaign_work_vector_id": accounting.work_vector[
            "campaign_work_vector_id"
        ],
        "campaign_comparison_vector_id": accounting.comparison_vector[
            "campaign_comparison_vector_id"
        ],
        "campaign_projection_proof_id": accounting.projection_proof[
            "campaign_projection_proof_id"
        ],
        "campaign_native_zero_attestation_id": accounting.native_zero_attestation[
            "campaign_native_zero_attestation_id"
        ],
        "os_receipt_ids": [_os_document_identity(row) for row in os_receipts],
        "event_count": SUCCESS_EVENT_COUNT,
        "event_evidence_nonnull_count": SUCCESS_NONNULL_EVIDENCE_COUNT,
        "event_evidence_null_count": SUCCESS_NULL_EVIDENCE_COUNT,
        "evidence_document_count": SUCCESS_EVIDENCE_DOCUMENT_COUNT,
        "os_receipt_document_count": sum(OS_EVIDENCE_SCHEMA_COUNTS.values()),
        "campaign_path_receipt_count": 9,
        "campaign_counter_record_count": 9,
        "campaign_work_vector_count": 1,
        "campaign_comparison_vector_count": 1,
        "campaign_projection_proof_count": 1,
        "campaign_native_zero_attestation_count": 1,
        "predecessor_occurrence_authoritative_receipt_count": 90,
        "successor_campaign_authoritative_receipt_count": 9,
        "combined_successor_authoritative_receipt_count": 99,
        "authoritative_receipt_arithmetic_90_plus_9_equals_99": True,
        "exact_625_event_schedule_independently_replayed": True,
        "exact_328_evidence_inventory_independently_replayed": True,
        "exact_twelve_os_receipts_independently_replayed": True,
        "four_separate_durable_success_artifacts_independently_replayed": True,
        "exact_eight_io_transfer_graph_independently_replayed": True,
        "overlapping_mount_intervals_independently_replayed": True,
        "cgroup_topology_birth_reap_and_peak_independently_replayed": True,
        "nine_campaign_path_receipts_independently_rederived": True,
        "nine_campaign_counter_records_independently_rederived": True,
        "campaign_work_vector_independently_rederived": True,
        "campaign_comparison_vector_independently_rederived": True,
        "campaign_projection_proof_independently_rederived": True,
        "bounded_native_zero_attestation_independently_rederived": True,
        "native_zero_is_registered_planning_comparison_axis_only": True,
        "native_zero_is_not_an_os_syscall_count": True,
        "open_world_absence_claimed": False,
        "producer_module_imported": False,
        "finalizer_module_imported": False,
        "supervisor_module_imported": False,
        "worker_module_imported": False,
        "campaign_measurement_ledger_kernel_imported": False,
        "V180R12R3R2_CAMPAIGN_COUNTER_CLOSURE_STATUS": "PASS",
        "COUNTER_COMPLETENESS_GATE": "PASS",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "v180r13_weight_agnostic_economics_input_ready": True,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "scientific_success_claimed": False,
    }


@dataclass(frozen=True, slots=True)
class CampaignMeasurementVerificationV180R12R3R2:
    """Canonical independent PASS receipt; later gates remain unexecuted."""

    _canonical_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        raw, document = _canonical_document(
            self._canonical_bytes, "campaign measurement verification"
        )
        payload = dict(document)
        identity = _cid(
            payload.pop("campaign_measurement_verification_id", None),
            "campaign measurement verification ID",
        )
        if (
            raw != self._canonical_bytes
            or frozenset(document) != VERIFICATION_FIELDS
            or document.get("schema") != VERIFICATION_SCHEMA
            or identity
            != domains.extension_content_id_v180r12r3r2(
                domains.CONSTRUCTION_K7_VERIFICATION_V180R12R3R2_DOMAIN,
                payload,
            )
            or document.get("V180R12R3R2_CAMPAIGN_COUNTER_CLOSURE_STATUS")
            != "PASS"
            or document.get("COUNTER_COMPLETENESS_GATE") != "PASS"
            or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
            or document.get("SCALAR_CALIBRATION_GATE") != "NOT_RUN"
            or document.get("BREAK_EVEN_GATE") != "NOT_RUN"
            or document.get("OFFICIAL_EXECUTION_GATE") != "NOT_RUN"
            or document.get("official_scalar_cost") is not None
            or document.get("official_N_break_even") is not None
            or document.get("official_execution_allowed") is not False
        ):
            _fail("campaign measurement verification identity or gate changed")

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_bytes

    @property
    def document(self) -> dict[str, Any]:
        return _canonical_document(
            self._canonical_bytes, "campaign measurement verification"
        )[1]

    @property
    def verification_id(self) -> str:
        return self.document["campaign_measurement_verification_id"]


def verify_campaign_measurement_terminal_independently_v180r12r3r2(
    terminal_bytes: bytes,
    *,
    campaign_evidence_inventory_bundle_bytes: bytes,
    campaign_execution_closure_bytes: bytes,
    campaign_os_receipt_bundle_bytes: bytes,
    campaign_ledger_closure_bytes: bytes,
    measurement_launch_attempt_bytes: bytes,
    measurement_launch_receipt_bytes: bytes,
    expected_protocol_id: str,
    expected_authorization_id: str,
    expected_authorization_evidence_id: str,
    expected_attempt_id: str,
    expected_prelaunch_materialization_terminal_id: str,
    expected_prelaunch_launch_manifest_sha256: str,
    expected_precompiled_source_bundle_sha256: str,
    expected_native_zero_precompiled_source_rows: Sequence[Mapping[str, Any]],
    expected_prelaunch_launch_rule_id: str,
    expected_measurement_launch_attempt_id: str,
    expected_subject_id: str,
    expected_native_zero_source_manifest_id: str,
    expected_native_zero_import_inventory_id: str,
    expected_max_event_count: int,
    expected_max_event_byte_count: int,
    expected_max_ledger_byte_count: int,
) -> CampaignMeasurementVerificationV180R12R3R2:
    """Independently reconstruct a pending terminal and issue the sole PASS."""

    for value, label in (
        (expected_protocol_id, "expected protocol ID"),
        (expected_authorization_id, "expected authorization ID"),
        (
            expected_authorization_evidence_id,
            "expected authorization-evidence ID",
        ),
        (expected_attempt_id, "expected attempt ID"),
        (
            expected_prelaunch_materialization_terminal_id,
            "expected prelaunch materialization-terminal ID",
        ),
        (
            expected_prelaunch_launch_manifest_sha256,
            "expected prelaunch launch-manifest SHA-256",
        ),
        (
            expected_precompiled_source_bundle_sha256,
            "expected precompiled source-bundle SHA-256",
        ),
        (
            expected_prelaunch_launch_rule_id,
            "expected prelaunch launch-rule ID",
        ),
        (
            expected_measurement_launch_attempt_id,
            "expected measurement launch-attempt ID",
        ),
        (expected_subject_id, "expected subject ID"),
        (
            expected_native_zero_source_manifest_id,
            "expected native-zero source manifest ID",
        ),
        (
            expected_native_zero_import_inventory_id,
            "expected native-zero import inventory ID",
        ),
    ):
        _cid(value, label)
    for value, label in (
        (expected_max_event_count, "expected event-count cap"),
        (expected_max_event_byte_count, "expected per-event byte cap"),
        (expected_max_ledger_byte_count, "expected ledger byte cap"),
    ):
        _positive(value, label)

    raw_terminal, terminal = _canonical_document(
        terminal_bytes, "pending campaign measurement terminal"
    )
    if frozenset(terminal) != TERMINAL_FIELDS:
        _fail("pending campaign terminal exact keyset changed")
    closure = terminal.get("campaign_measurement_ledger")
    if type(closure) is not dict:
        _fail("pending terminal lacks one embedded campaign ledger closure")
    if (
        closure.get("protocol_id") != expected_protocol_id
        or closure.get("authorization_id") != expected_authorization_id
        or terminal.get("authorization_evidence_id")
        != expected_authorization_evidence_id
        or closure.get("attempt_id") != expected_attempt_id
        or terminal.get("prelaunch_materialization_terminal_id")
        != expected_prelaunch_materialization_terminal_id
        or terminal.get("prelaunch_launch_manifest_sha256")
        != expected_prelaunch_launch_manifest_sha256
        or terminal.get("precompiled_source_bundle_sha256")
        != expected_precompiled_source_bundle_sha256
        or terminal.get("prelaunch_launch_rule_id")
        != expected_prelaunch_launch_rule_id
        or terminal.get("measurement_launch_attempt_id")
        != expected_measurement_launch_attempt_id
        or closure.get("subject_id") != expected_subject_id
        or closure.get("native_zero_source_manifest_id")
        != expected_native_zero_source_manifest_id
        or closure.get("native_zero_import_inventory_id")
        != expected_native_zero_import_inventory_id
        or closure.get("max_event_count") != expected_max_event_count
        or closure.get("max_event_byte_count") != expected_max_event_byte_count
        or closure.get("max_ledger_byte_count") != expected_max_ledger_byte_count
    ):
        _fail("pending terminal one-shot context or frozen caps changed")

    events = _validate_events(
        closure,
        protocol_id=expected_protocol_id,
        authorization_id=expected_authorization_id,
        attempt_id=expected_attempt_id,
    )
    documents, evidence_rows = _validate_evidence_documents(closure)
    facts = _validate_evidence_graph(
        events,
        documents,
        protocol_id=expected_protocol_id,
        authorization_id=expected_authorization_id,
        authorization_evidence_id=expected_authorization_evidence_id,
        attempt_id=expected_attempt_id,
        expected_prelaunch_materialization_terminal_id=(
            expected_prelaunch_materialization_terminal_id
        ),
        expected_prelaunch_launch_manifest_sha256=(
            expected_prelaunch_launch_manifest_sha256
        ),
        expected_precompiled_source_bundle_sha256=(
            expected_precompiled_source_bundle_sha256
        ),
        expected_native_zero_precompiled_source_rows=(
            expected_native_zero_precompiled_source_rows
        ),
        expected_prelaunch_launch_rule_id=expected_prelaunch_launch_rule_id,
        expected_measurement_launch_attempt_id=expected_measurement_launch_attempt_id,
        expected_subject_id=expected_subject_id,
        expected_source_manifest_id=expected_native_zero_source_manifest_id,
        expected_import_inventory_id=expected_native_zero_import_inventory_id,
    )
    accounting = _derive_accounting(
        events,
        documents,
        facts,
        protocol_id=expected_protocol_id,
        authorization_id=expected_authorization_id,
        attempt_id=expected_attempt_id,
    )
    expected_closure = _expected_closure(
        closure,
        events,
        evidence_rows,
        facts,
        accounting,
        protocol_id=expected_protocol_id,
        authorization_id=expected_authorization_id,
        attempt_id=expected_attempt_id,
    )
    if closure != expected_closure:
        _fail("campaign ledger closure differs from independent reconstruction")
    os_receipts = _validate_terminal_os_receipts(terminal, documents)
    success_artifacts = _validate_separate_success_artifacts(
        inventory_bundle_bytes=campaign_evidence_inventory_bundle_bytes,
        execution_closure_bytes=campaign_execution_closure_bytes,
        os_receipt_bundle_bytes=campaign_os_receipt_bundle_bytes,
        ledger_closure_bytes=campaign_ledger_closure_bytes,
        closure=expected_closure,
        documents=documents,
        os_receipts=os_receipts,
    )
    if raw_terminal != _expected_terminal_bytes(
        expected_closure, os_receipts, success_artifacts
    ):
        _fail("pending terminal differs from independent byte reconstruction")
    _measurement_launch_receipt, measurement_launch_receipt_id = (
        _validate_measurement_launch_guard_authority(
            measurement_launch_attempt_bytes=measurement_launch_attempt_bytes,
            measurement_launch_receipt_bytes=measurement_launch_receipt_bytes,
            terminal_bytes=raw_terminal,
            success_artifacts=success_artifacts,
            expected_prelaunch_materialization_terminal_id=(
                expected_prelaunch_materialization_terminal_id
            ),
            expected_prelaunch_launch_manifest_sha256=(
                expected_prelaunch_launch_manifest_sha256
            ),
            expected_prelaunch_launch_rule_id=expected_prelaunch_launch_rule_id,
            expected_measurement_launch_attempt_id=(
                expected_measurement_launch_attempt_id
            ),
            expected_campaign_attempt_id=expected_attempt_id,
        )
    )

    payload = _verification_payload(
        terminal_bytes=raw_terminal,
        terminal=terminal,
        closure=expected_closure,
        facts=facts,
        accounting=accounting,
        os_receipts=os_receipts,
        success_artifacts=success_artifacts,
        measurement_launch_receipt_bytes=measurement_launch_receipt_bytes,
        measurement_launch_receipt_id=measurement_launch_receipt_id,
    )
    document = {
        **payload,
        "campaign_measurement_verification_id": domains.extension_content_id_v180r12r3r2(
            domains.CONSTRUCTION_K7_VERIFICATION_V180R12R3R2_DOMAIN,
            payload,
        ),
    }
    return CampaignMeasurementVerificationV180R12R3R2(canonical_json_bytes(document))


__all__ = (
    "CAMPAIGN_SCOPE_KIND",
    "CAMPAIGN_SCOPE_MODEL",
    "CampaignMeasurementVerificationV180R12R3R2",
    "ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error",
    "EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS",
    "EVIDENCE_INVENTORY_BUNDLE_SCHEMA",
    "EVIDENCE_INVENTORY_BUNDLE_FIELDS",
    "FRAME_BYTE_CAP",
    "MEASUREMENT_LAUNCH_ATTEMPT_FIELDS",
    "MEASUREMENT_LAUNCH_RECEIPT_FIELDS",
    "MEASUREMENT_CGROUP_OBSERVATION_FIELDS",
    "MEASUREMENT_CGROUP_OBSERVATION_PHASES",
    "OS_EVIDENCE_SCHEMA_COUNTS",
    "OS_RECEIPT_BUNDLE_SCHEMA",
    "OS_RECEIPT_BUNDLE_FIELDS",
    "SEMANTIC_RECEIPT_AUXILIARY_NAME_BY_KIND",
    "SNAPSHOT_TRANSPORT_INDEPENDENT_VERIFIER_BOUNDARY",
    "SUCCESS_ARTIFACT_SCHEMA_ROWS",
    "SUCCESS_EVIDENCE_DOCUMENT_COUNT",
    "SUCCESS_EVENT_COUNT",
    "SUBJECT_RESULT_BYTE_CAP",
    "SUBJECT_RESULT_RUNTIME_BYTE_CAP",
    "TERMINAL_SCHEMA",
    "TERMINAL_FIELDS",
    "VERIFICATION_SCHEMA",
    "VERIFICATION_FIELDS",
    "verify_campaign_measurement_terminal_independently_v180r12r3r2",
)
