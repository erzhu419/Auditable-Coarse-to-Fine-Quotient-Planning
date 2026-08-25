#!/usr/bin/python3
"""Launch one source-bound V180r12r3 target under the frozen whole-child cap.

This stdlib-only supervisor is materialized from the preregistration commit.
It validates the retained prelaunch receipt, writes a target-specific attempt
lock before spawning Python, applies RLIMIT_AS before exec, enforces the wall
timeout outside the worker, and writes exactly one terminal launch receipt or
typed launch failure.  Its work is preauthorization supervision and is never a
campaign-scope CounterRecord or scientific WorkVector.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import selectors
import signal
import stat
import subprocess
import sys
import time
from typing import Any, Mapping, NoReturn


LAUNCH_RULE_SCHEMA = "acfqp.v180r12r3_prelaunch_launch_rule.v1"
LAUNCH_ATTEMPT_SCHEMA = "acfqp.v180r12r3_prelaunch_launch_attempt.v1"
LAUNCH_RECEIPT_SCHEMA = "acfqp.v180r12r3_prelaunch_launch_receipt.v1"
LAUNCH_FAILURE_SCHEMA = "acfqp.v180r12r3_prelaunch_launch_failure.v1"
MATERIALIZATION_TERMINAL_SCHEMA = (
    "acfqp.v180r12r3_prelaunch_materialization_terminal.v1"
)
EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "0e67ab386900adb177a8bb153acbe9c4fb9efc256b5ca53fa001d1aeb04de0e3"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "f4016b26c95351d1712a6528d7306635797231964d57a32af71ab35832331d6f"
)
EXPECTED_LAUNCH_RULE_ID = (
    "1700936d9145bfa7bcd858128548fd57f003ccf86a63dfdd43d6487f3aae4572"
)
SOURCE_CLOSURE_RULE_ID = EXPECTED_SOURCE_CLOSURE_RULE_ID
MATERIALIZATION_RULE_ID = EXPECTED_MATERIALIZATION_RULE_ID

PYTHON_EXECUTABLE = "/usr/bin/python3"
PYCACHE_PREFIX = "/dev/null/v180r12r3"
MANIFEST_SHA256_ENV = "ACFQP_V180R12R3_LAUNCH_MANIFEST_SHA256"
MATERIALIZATION_TERMINAL_SHA256_ENV = (
    "ACFQP_V180R12R3_MATERIALIZATION_TERMINAL_SHA256"
)
ISOLATED_ARGV_PREFIX = (
    PYTHON_EXECUTABLE,
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={PYCACHE_PREFIX}",
)

PRELAUNCH_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r3_campaign_measurement_prelaunch"
)
EXTERNAL_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r3_campaign_measurement_prelaunch_external_root.json"
)
BOOTSTRAP_RELATIVE_PATH = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/bootstrap.py"
LAUNCHER_RELATIVE_PATH = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/launcher.py"
MANIFEST_RELATIVE_PATH = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/launch_manifest.json"
MATERIALIZATION_TERMINAL_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MATERIALIZATION_TERMINAL.json"
)
MATERIALIZATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r3_campaign_measurement_prelaunch_failure.json"
)
SOURCE_BOOTSTRAP_RELATIVE_PATH = (
    "scripts/bootstrap_v180r12r3_campaign_measurement.py"
)
SOURCE_LAUNCHER_RELATIVE_PATH = (
    "scripts/launch_v180r12r3_campaign_measurement_prelaunch.py"
)
SOURCE_MATERIALIZER_RELATIVE_PATH = (
    "scripts/materialize_v180r12r3_campaign_measurement_prelaunch.py"
)
AUTHORIZATION_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_campaign_measurement_"
    "authorization_evidence_freeze_v180r12r3.py"
)
NORMALIZED_WRAPPER_BINDING_KIND = "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
WRAPPER_REDACTED_CONSTANT_NAMES = (
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    "EXPECTED_SOURCE_CLOSURE_ID",
    "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
    "EXPECTED_SOURCE_CLOSURE_SHA256",
    "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
)

MEASUREMENT_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_LAUNCH_ATTEMPT.json"
)
MEASUREMENT_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_LAUNCH_RECEIPT.json"
)
MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r3_campaign_measurement_prelaunch_measurement_launch_failure.json"
)
VERIFICATION_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_ATTEMPT.json"
)
VERIFICATION_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_RECEIPT.json"
)
VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r3_campaign_measurement_prelaunch_verification_launch_failure.json"
)

RUNTIME_CAS_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r3_campaign_measurement_cas"
)
OUTPUT_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r3_campaign_measurement"
)
TERMINAL_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/TERMINAL.json"
EVIDENCE_INVENTORY_RELATIVE_PATH = (
    f"{OUTPUT_ROOT_RELATIVE_PATH}/EVIDENCE_INVENTORY.json"
)
EXECUTION_CLOSURE_RELATIVE_PATH = (
    f"{OUTPUT_ROOT_RELATIVE_PATH}/EXECUTION_CLOSURE.json"
)
OS_RECEIPT_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/OS_RECEIPT.json"
LEDGER_CLOSURE_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/LEDGER_CLOSURE.json"
MEASUREMENT_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r3_campaign_measurement_failure.json"
)
VERIFICATION_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r3_campaign_measurement_verification.json"
)
VERIFICATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r3_campaign_measurement_verification_failure.json"
)
RETAINED_REPLAY_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r3_campaign_measurement_verification_replay.json"
)

ADDRESS_SPACE_HARD_CAP_BYTES = 16 * 1024 * 1024 * 1024
WALL_TIMEOUT_SECONDS = 14_400
TERMINATION_GRACE_SECONDS = 10
CAMPAIGN_CLEANUP_GRACE_SECONDS = 600
NANOSECONDS_PER_SECOND = 1_000_000_000
MATERIALIZATION_TERMINAL_BYTE_CAP = 16 * 1024 * 1024
EXTERNAL_ROOT_BYTE_CAP = 1024 * 1024
BOOTSTRAP_BYTE_CAP = 1024 * 1024
LAUNCHER_BYTE_CAP = 1024 * 1024
MANIFEST_BYTE_CAP = 16 * 1024 * 1024
CHILD_STREAM_BYTE_CAP = 1 * 1024 * 1024
CHILD_STREAM_RETAINED_PREFIX_BYTES = 4096
EMPTY_STREAM_SHA256 = hashlib.sha256(b"").hexdigest()
STREAM_BUFFER_BYTES = 1024 * 1024
FAILURE_MESSAGE_BYTE_CAP = 4096
LAUNCH_ARTIFACT_BYTE_CAP = 16 * 1024 * 1024
SCIENTIFIC_ARTIFACT_BYTE_CAP = 16 * 1024 * 1024
EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP = 64 * 1024 * 1024
EXECUTION_CLOSURE_BYTE_CAP = 1 * 1024 * 1024
OS_RECEIPT_BUNDLE_BYTE_CAP = 16 * 1024 * 1024
LEDGER_CLOSURE_BYTE_CAP = 64 * 1024 * 1024
EXTERNAL_LAUNCH_CONTEXT_BYTE_CAP = 2 * 1024 * 1024
EXTERNAL_LAUNCH_CONTEXT_FD = 249
DELEGATED_CGROUP_PARENT_FD = 250
CGROUP2_MOUNT_FD = 251
CGROUP_CONTROL_BYTE_CAP = 64 * 1024
MEASUREMENT_CGROUP_OBSERVATION_PHASES = (
    "BEFORE_POPEN",
    "CLEANUP",
    "AFTER_CHILD",
)
MEASUREMENT_CGROUP_OBSERVATION_FIELDS = frozenset(
    {
        "phase",
        "applicable",
        "campaign_attempt_id",
        "root_name",
        "ownership_acquired",
        "root_state",
        "root_mode",
        "root_nlink",
        "root_device",
        "root_inode",
        "root_populated",
        "root_process_count",
        "supervisor_state",
        "worker_state",
        "kill_attempted",
        "kill_succeeded",
        "wait_empty_attempted",
        "wait_empty_succeeded",
        "remove_attempted",
        "remove_succeeded",
        "residual_tree_or_process_possible",
        "error_type",
        "error_message",
    }
)
EXTERNAL_LAUNCH_CONTEXT_SCHEMA = (
    "acfqp.v180r12r3_external_launch_context.v1"
)
FROZEN_AUTHORIZATION_CONTEXT_SCHEMA = (
    "acfqp.v180r12r3_frozen_authorization_context.v1"
)
FROZEN_AUTHORIZATION_CONTEXT_FIELDS = (
    "schema", "protocol_id", "protocol_byte_count", "protocol_sha256",
    "authorization_id", "authorization_byte_count", "authorization_sha256",
    "authorization_evidence_id", "authorization_evidence_byte_count",
    "authorization_evidence_sha256", "campaign_measurement_execution_slot_id",
    "logical_occurrence_id", "execution_nonce", "campaign_attempt_id",
    "cgroup_parent_fact", "runtime_capability_fact",
)
EXTERNAL_LAUNCH_CONTEXT_FIELDS = (
    "schema", "target", "actor_role", "repository_root", "c_pre_root",
    "prereg_commit_id", "prelaunch_materialization_terminal_id",
    "prelaunch_materialization_terminal_byte_count",
    "prelaunch_materialization_terminal_sha256",
    "prelaunch_launch_manifest_sha256", "prelaunch_launch_rule_id",
    "current_launch_attempt_id", "current_launch_attempt_byte_count",
    "current_launch_attempt_sha256", "measurement_launch_attempt_id",
    "measurement_launch_attempt_byte_count", "measurement_launch_attempt_sha256",
    "protocol_id", "protocol_byte_count", "protocol_sha256",
    "authorization_id", "authorization_byte_count", "authorization_sha256",
    "authorization_evidence_id", "authorization_evidence_byte_count",
    "authorization_evidence_sha256", "campaign_measurement_execution_slot_id",
    "logical_occurrence_id", "execution_nonce", "campaign_attempt_id",
    "monotonic_origin_ns", "hard_deadline_ns", "campaign_deadline_ns",
    "cgroup_parent_fact", "runtime_capability_fact", "inherited_fd_roles",
    "target_payload", "one_shot",
)
EXTERNAL_FD_ROLE_ROWS = {
    "measurement": (
        (249, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"),
        (250, "DELEGATED_CGROUP_PARENT_DIRECTORY"),
        (251, "CGROUP2_MOUNT_DIRECTORY"),
    ),
    "verification": ((249, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"),),
}
CGROUP_PARENT_FACT_FIELDS = frozenset(
    {
        "schema", "mount_point", "mount_fstype", "mount_device", "mount_inode",
        "mount_options", "parent_path", "parent_device", "parent_inode",
        "owner_uid", "owner_gid", "mode", "controllers", "subtree_control",
        "cgroup_type", "cgroup_namespace_inode", "cgroup_events_present",
        "memory_events_present", "pids_events_present", "cgroup_kill_present",
        "cgroup_procs_present", "memory_peak_present", "pids_peak_present",
        "self_membership",
    }
)
RUNTIME_CAPABILITY_FACT_FIELDS = frozenset(
    {
        "schema", "machine_architecture", "single_threaded",
        "clone3_probe_errno", "clone3_syscall_recognized",
        "pidfd_send_signal_probe_errno", "pidfd_send_signal_recognized",
        "execveat_probe_errno", "execveat_recognized", "pidfd_wait_present",
        "landlock_abi", "uid", "gid", "effective_capability_mask", "admitted",
    }
)

EVIDENCE_INVENTORY_BUNDLE_SCHEMA = (
    "acfqp.campaign_evidence_inventory_bundle.v180r12r3"
)
EXECUTION_CLOSURE_SCHEMA = "acfqp.campaign_execution_closure.v180r12r3"
OS_RECEIPT_BUNDLE_SCHEMA = "acfqp.campaign_os_receipt_bundle.v180r12r3"
LEDGER_CLOSURE_SCHEMA = "acfqp.campaign_measurement_ledger_closure.v180r12r3"
TERMINAL_SCHEMA = "acfqp.campaign_measurement_terminal.v180r12r3"
EVIDENCE_INVENTORY_BUNDLE_DOMAIN = (
    "acfqp:construction-k7-campaign-evidence-inventory-bundle:v180r12r3"
)
EXECUTION_CLOSURE_DOMAIN = (
    "acfqp:construction-k7-campaign-execution-closure:v180r12r3e"
)
OS_RECEIPT_BUNDLE_DOMAIN = (
    "acfqp:construction-k7-campaign-os-receipt-bundle:v180r12r3"
)
LEDGER_CLOSURE_DOMAIN = (
    "acfqp:construction-k7-campaign-ledger-closure:v180r12r3e"
)
TERMINAL_DOMAIN = (
    "acfqp:construction-k7-campaign-measurement-terminal-bundle:v180r12r3"
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_TARGETS = {
    "measurement": {
        "attempt": MEASUREMENT_ATTEMPT_RELATIVE_PATH,
        "receipt": MEASUREMENT_RECEIPT_RELATIVE_PATH,
        "launch_failure": MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH,
    },
    "verification": {
        "attempt": VERIFICATION_ATTEMPT_RELATIVE_PATH,
        "receipt": VERIFICATION_RECEIPT_RELATIVE_PATH,
        "launch_failure": VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH,
    },
}
MANIFEST_TARGET_RUNNER_PATHS = {
    "measurement": "scripts/run_v180r12r3_campaign_measurement.py",
    "verification": "scripts/verify_v180r12r3_campaign_measurement.py",
    "supervisor": "scripts/supervise_v180r12r3_campaign_measurement.py",
    "worker": "scripts/work_v180r12r3_campaign_measurement.py",
}
INTERNAL_TARGETS = ("supervisor", "worker")
PRECOMPILED_BUNDLE_FD = 240
INTERNAL_IPC_FD = 241
INTERNAL_MAC_KEY_FD = 242
INTERNAL_CONTEXT_FD = 243
SUPERVISOR_REPOSITORY_ROOT_FD = 244
SUPERVISOR_WORKER_CGROUP_FD = 245
WORKER_TERMINAL_STAGE_FD = 246
WORKER_VERIFICATION_STAGE_FD = 247
WORKER_SUBJECT_RESULT_FD = 248
SOCK_SEQPACKET_BUFFER_REQUEST_BYTES = 1 * 1024 * 1024
SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES = 2 * SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
INTERNAL_FD_ROLE_MAP = {
    "supervisor": (
        (PRECOMPILED_BUNDLE_FD, "PRECOMPILED_SOURCE_BUNDLE_MEMFD"),
        (INTERNAL_IPC_FD, "OBSERVER_SUPERVISOR_SOCK_SEQPACKET"),
        (INTERNAL_MAC_KEY_FD, "PARENT_TO_CHILD_MAC_KEY_MEMFD"),
        (INTERNAL_CONTEXT_FD, "INTERNAL_LAUNCH_CONTEXT_MEMFD"),
        (SUPERVISOR_REPOSITORY_ROOT_FD, "REPOSITORY_ROOT_O_PATH_DIRECTORY"),
        (SUPERVISOR_WORKER_CGROUP_FD, "WORKER_CGROUP_DIRECTORY"),
    ),
    "worker": (
        (PRECOMPILED_BUNDLE_FD, "PRECOMPILED_SOURCE_BUNDLE_MEMFD"),
        (INTERNAL_IPC_FD, "SUPERVISOR_WORKER_SOCK_SEQPACKET"),
        (INTERNAL_MAC_KEY_FD, "PARENT_TO_CHILD_MAC_KEY_MEMFD"),
        (INTERNAL_CONTEXT_FD, "INTERNAL_LAUNCH_CONTEXT_MEMFD"),
        (WORKER_TERMINAL_STAGE_FD, "TERMINAL_STAGE_READ_ONLY_MEMFD"),
        (WORKER_VERIFICATION_STAGE_FD, "VERIFICATION_STAGE_READ_ONLY_MEMFD"),
        (WORKER_SUBJECT_RESULT_FD, "SUBJECT_RESULT_WRITE_ONLY_FD"),
    ),
}
_INTERNAL_FD_RULES = {
    "PRECOMPILED_SOURCE_BUNDLE_MEMFD": ("SEALED_MEMFD", "READ_ONLY", "0400", True),
    "OBSERVER_SUPERVISOR_SOCK_SEQPACKET": ("SOCK_SEQPACKET", "READ_WRITE", None, False),
    "SUPERVISOR_WORKER_SOCK_SEQPACKET": ("SOCK_SEQPACKET", "READ_WRITE", None, False),
    "PARENT_TO_CHILD_MAC_KEY_MEMFD": ("SEALED_MEMFD", "READ_ONLY", "0400", True),
    "INTERNAL_LAUNCH_CONTEXT_MEMFD": ("SEALED_MEMFD", "READ_ONLY", "0400", True),
    "REPOSITORY_ROOT_O_PATH_DIRECTORY": ("DIRECTORY", "O_PATH", None, False),
    "WORKER_CGROUP_DIRECTORY": ("DIRECTORY", "READ_ONLY", None, False),
    "TERMINAL_STAGE_READ_ONLY_MEMFD": ("SEALED_MEMFD", "READ_ONLY", "0400", True),
    "VERIFICATION_STAGE_READ_ONLY_MEMFD": ("SEALED_MEMFD", "READ_ONLY", "0400", True),
    "SUBJECT_RESULT_WRITE_ONLY_FD": ("REGULAR_FILE", "WRITE_ONLY", "0600_PRECOMMIT", False),
}
INTERNAL_TARGET_CONTRACT = {
    "schema": "acfqp.v180r12r3_internal_bootstrap_target_contract.v1",
    "target_order": ["supervisor", "worker"],
    "initial_environment_keys": [MANIFEST_SHA256_ENV, "LC_CTYPE"],
    "injected_environment_key": "ACFQP_V180R12R3_PREREG_COMMIT",
    "dynamic_identity_in_argv_or_environment": False,
    "context_schema": "acfqp.v180r12r3_internal_launch_context.v1",
    "context_mac_algorithm": "BLAKE2S_KEYED_256",
    "context_mac_direction": "PARENT_TO_CHILD_ONLY",
    "context_required_authority_fields": [
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "attempt_id",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
        "prelaunch_materialization_terminal_id",
        "launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
    ],
    "precompiled_bundle_schema": (
        "acfqp.v180r12r3_precompiled_source_bundle.v1"
    ),
    "precompiled_before_campaign_attempt": True,
    "internal_target_reads_working_tree_source": False,
    "sock_seqpacket_buffer_request_bytes": (
        SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
    ),
    "sock_seqpacket_effective_min_bytes": (
        SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
    ),
    "sock_seqpacket_buffer_pair_roles": [
        "OBSERVER_SUPERVISOR_SOCK_SEQPACKET",
        "SUPERVISOR_WORKER_SOCK_SEQPACKET",
    ],
    "sock_seqpacket_so_sndbuf_and_so_rcvbuf_required_on_both_endpoints": True,
    "sock_seqpacket_buffers_configured_and_read_back_before_clone_or_send": True,
    "sock_seqpacket_insufficient_effective_buffer_fails_before_child_creation": True,
    "fd_numbers_are_protocol_fixed": True,
    "target_rows": [
        {
            "target": target,
            "runner_relative_path": MANIFEST_TARGET_RUNNER_PATHS[target],
            "actor_role": {"supervisor": "SUPERVISOR", "worker": "WORKER"}[target],
            "parent_actor_role": {"supervisor": "OBSERVER", "worker": "SUPERVISOR"}[target],
            "inherited_fd_roles": [
                {
                    "fd": descriptor,
                    "role": role,
                    "kind": _INTERNAL_FD_RULES[role][0],
                    "access": _INTERNAL_FD_RULES[role][1],
                    "mode": _INTERNAL_FD_RULES[role][2],
                    "required_seals": (
                        ["F_SEAL_SEAL", "F_SEAL_SHRINK", "F_SEAL_GROW", "F_SEAL_WRITE"]
                        if _INTERNAL_FD_RULES[role][3]
                        else []
                    ),
                    "inheritable_at_bootstrap_exec": True,
                    "closed_before_runner_dispatch": role
                    in {"PARENT_TO_CHILD_MAC_KEY_MEMFD", "INTERNAL_LAUNCH_CONTEXT_MEMFD"},
                    "cloexec_at_runner_dispatch": role
                    not in {"PARENT_TO_CHILD_MAC_KEY_MEMFD", "INTERNAL_LAUNCH_CONTEXT_MEMFD"},
                }
                for descriptor, role in INTERNAL_FD_ROLE_MAP[target]
            ],
        }
        for target in INTERNAL_TARGETS
    ],
    "inherited_descriptors_must_be_non_cloexec_at_bootstrap_exec": True,
    "bootstrap_entry_open_fd_inventory_is_exact": True,
    "key_and_context_descriptors_closed_before_runner_dispatch": True,
    "operational_descriptors_set_cloexec_before_runner_dispatch": True,
    "unlisted_internal_target_or_fd_role_forbidden": True,
}

EVIDENCE_INVENTORY_BUNDLE_FIELDS = frozenset(
    {
        "schema", "schema_version", "protocol_id", "authorization_id",
        "attempt_id", "evidence_document_count", "evidence_document_type_counts",
        "ordered_evidence_document_ids", "evidence_documents",
        "campaign_evidence_inventory_bundle_id",
    }
)
EXECUTION_CLOSURE_FIELDS = frozenset(
    {
        "schema", "schema_version", "scope", "scope_model", "protocol_id",
        "authorization_id", "attempt_id", "subject_id", "window_closed_event_id",
        "window_closure_receipt_id", "operation_manifest_id", "source_manifest_id",
        "import_inventory_id", "precompiled_source_bundle_sha256",
        "comparison_axis", "kernel_transition_calls",
        "registered_planning_operation_site_fact_count",
        "kernel_transition_operation_site_fact_ids",
        "kernel_transition_import_fact_ids", "unregistered_operation_site_fact_ids",
        "unregistered_import_fact_ids",
        "registered_planning_comparison_ground_kernel_axis_only",
        "prelaunch_sealed_application_import_allowlist_only",
        "runtime_role_exit_origin_guard_required",
        "runtime_role_exit_origin_guard_status",
        "not_an_os_syscall_count", "unregistered_or_dynamic_sites_forbidden",
        "closed_registered_planning_operation_window_only",
        "open_world_absence_claimed",
        "execution_window_closed", "campaign_execution_closure_id",
    }
)
OS_RECEIPT_BUNDLE_FIELDS = frozenset(
    {
        "schema", "schema_version", "protocol_id", "authorization_id",
        "attempt_id", "campaign_evidence_inventory_bundle_id",
        "os_receipt_document_count", "os_receipt_schema_counts",
        "ordered_os_receipt_ids", "os_receipt_documents",
        "campaign_os_receipt_bundle_id",
    }
)
LEDGER_CLOSURE_FIELDS = frozenset(
    {
        "schema", "schema_version", "scope", "scope_model", "protocol_id",
        "authorization_id", "attempt_id", "subject_id",
        "campaign_operation_manifest_id", "native_zero_source_manifest_id",
        "native_zero_import_inventory_id", "campaign_execution_closure_id",
        "max_event_count", "max_event_byte_count", "max_ledger_byte_count",
        "events", "ordered_event_ids", "event_count", "ledger_event_byte_count",
        "first_event_id", "last_event_id", "evidence_documents",
        "campaign_evidence_document_count", "direct_event_evidence_document_count",
        "support_evidence_document_count", "campaign_evidence_document_type_counts",
        "event_evidence_nonnull_count", "event_evidence_null_count", "path_receipts",
        "campaign_receipt_set", "counter_records", "campaign_work_vector",
        "campaign_comparison_vector", "campaign_projection_proof",
        "campaign_native_zero_attestation", "campaign_path_receipt_count",
        "campaign_counter_record_count", "campaign_work_vector_count",
        "campaign_comparison_vector_count", "campaign_projection_proof_count",
        "campaign_native_zero_attestation_count",
        "predecessor_occurrence_authoritative_receipt_count",
        "predecessor_structural_obligation_count",
        "predecessor_campaign_scope_structural_obligation_count",
        "predecessor_campaign_actual_receipt_count",
        "predecessor_campaign_authoritative_receipt_count",
        "successor_campaign_actual_receipt_count",
        "successor_campaign_counter_record_count",
        "combined_successor_authoritative_receipt_count",
        "successful_campaign_authoritative_receipt_count",
        "successful_combined_authoritative_receipt_count",
        "terminal_pending_authoritative_receipt_join",
        "independent_verifier_pass_authoritative_receipt_join",
        "predecessor_structural_nine_are_successor_actual_receipts",
        "predecessor_structural_obligations_are_not_current_measurements",
        "authoritative_receipt_arithmetic_90_plus_9_equals_99", "hash_chain_complete",
        "lifecycle_phase_order_complete", "actual_measurements_present",
        "all_nine_campaign_paths_strictly_positive",
        "independent_comparison_axis_native_zero_complete",
        "route_free_campaign_accounting", "independent_verification_present",
        "COUNTER_COMPLETENESS_GATE", "WORKLOAD_ECONOMICS_GATE",
        "SCALAR_CALIBRATION_GATE", "BREAK_EVEN_GATE", "OFFICIAL_EXECUTION_GATE",
        "v180r13_weight_agnostic_economics_input_ready", "official_scalar_cost",
        "official_N_break_even", "official_execution_allowed",
        "scientific_success_claimed", "campaign_ledger_closure_id",
    }
)
TERMINAL_FIELDS = frozenset(
    {
        "schema", "schema_version", "scope", "scope_model", "protocol_id",
        "authorization_id", "authorization_evidence_id", "attempt_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256", "precompiled_source_bundle_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id", "subject_id",
        "campaign_operation_manifest_id", "native_zero_source_manifest_id",
        "native_zero_import_inventory_id", "campaign_execution_closure_id",
        "campaign_execution_closure_byte_count", "campaign_execution_closure_sha256",
        "campaign_evidence_inventory_bundle_id",
        "campaign_evidence_inventory_bundle_byte_count",
        "campaign_evidence_inventory_bundle_sha256", "campaign_os_receipt_bundle_id",
        "campaign_os_receipt_bundle_byte_count", "campaign_os_receipt_bundle_sha256",
        "campaign_ledger_closure_id", "campaign_ledger_closure_byte_count",
        "campaign_ledger_closure_sha256", "campaign_measurement_ledger",
        "os_receipt_documents", "os_receipt_ids", "os_receipt_schema_counts",
        "event_count", "evidence_document_count", "os_receipt_document_count",
        "campaign_path_receipt_count", "campaign_counter_record_count",
        "campaign_work_vector_count", "campaign_comparison_vector_count",
        "campaign_projection_proof_count", "campaign_native_zero_attestation_count",
        "predecessor_occurrence_authoritative_receipt_count",
        "successor_campaign_authoritative_receipt_count",
        "combined_successor_authoritative_receipt_count",
        "authoritative_receipt_arithmetic_90_plus_9_equals_99",
        "raw_event_evidence_and_os_receipts_replayed", "route_free_campaign_accounting",
        "all_nine_campaign_paths_strictly_positive",
        "independent_native_zero_attestation_present", "independent_verification_present",
        "V180R12R3_CAMPAIGN_COUNTER_CLOSURE_STATUS", "COUNTER_COMPLETENESS_GATE",
        "WORKLOAD_ECONOMICS_GATE", "SCALAR_CALIBRATION_GATE", "BREAK_EVEN_GATE",
        "OFFICIAL_EXECUTION_GATE", "v180r13_weight_agnostic_economics_input_ready",
        "official_scalar_cost", "official_N_break_even", "official_execution_allowed",
        "scientific_success_claimed", "output_bytes_fixed_point",
        "campaign_measurement_terminal_id",
    }
)
EVIDENCE_DOCUMENT_TYPE_COUNTS = {
    "acfqp.campaign_attempt_record.v180r12r3": 1,
    "acfqp.campaign_stable_input_snapshot.v180r12r3": 2,
    "acfqp.campaign_io_transfer_receipt.v180r12r3": 8,
    "acfqp.campaign_memfd_stage_receipt.v180r12r3": 2,
    "acfqp.campaign_fd_visibility_receipt.v180r12r3": 4,
    "acfqp.campaign_semantic_operation_receipt.v180r12r3": 297,
    "acfqp.campaign_pidfd_birth_receipt.v180r12r3": 2,
    "acfqp.campaign_pidfd_reap_receipt.v180r12r3": 2,
    "acfqp.campaign_cgroup_topology_receipt.v180r12r3": 1,
    "acfqp.campaign_cgroup_observation_receipt.v180r12r3": 1,
    "acfqp.campaign_replay_subject_receipt.v180r12r3": 1,
    "acfqp.campaign_measurement_subject_result.v180r12r3": 1,
    "acfqp.campaign_subject_commit_receipt.v180r12r3": 1,
    "acfqp.campaign_window_closure_receipt.v180r12r3": 1,
    EXECUTION_CLOSURE_SCHEMA: 1,
    "acfqp.campaign_operation_manifest.v180r12r3": 1,
    "acfqp.campaign_native_zero_source_manifest.v180r12r3": 1,
    "acfqp.campaign_native_zero_import_inventory.v180r12r3": 1,
}
EVIDENCE_IDENTITY_FIELD_BY_SCHEMA = {
    "acfqp.campaign_attempt_record.v180r12r3": "campaign_attempt_record_id",
    "acfqp.campaign_stable_input_snapshot.v180r12r3": "stable_input_snapshot_id",
    "acfqp.campaign_io_transfer_receipt.v180r12r3": "io_transfer_receipt_id",
    "acfqp.campaign_memfd_stage_receipt.v180r12r3": "memfd_stage_receipt_id",
    "acfqp.campaign_fd_visibility_receipt.v180r12r3": "fd_visibility_receipt_id",
    "acfqp.campaign_semantic_operation_receipt.v180r12r3": (
        "semantic_operation_receipt_id"
    ),
    "acfqp.campaign_pidfd_birth_receipt.v180r12r3": "pidfd_birth_receipt_id",
    "acfqp.campaign_pidfd_reap_receipt.v180r12r3": "pidfd_reap_receipt_id",
    "acfqp.campaign_cgroup_topology_receipt.v180r12r3": (
        "cgroup_topology_receipt_id"
    ),
    "acfqp.campaign_cgroup_observation_receipt.v180r12r3": (
        "cgroup_observation_receipt_id"
    ),
    "acfqp.campaign_replay_subject_receipt.v180r12r3": "replay_subject_receipt_id",
    "acfqp.campaign_measurement_subject_result.v180r12r3": "subject_result_id",
    "acfqp.campaign_subject_commit_receipt.v180r12r3": "subject_commit_receipt_id",
    "acfqp.campaign_window_closure_receipt.v180r12r3": "window_closure_receipt_id",
    EXECUTION_CLOSURE_SCHEMA: "campaign_execution_closure_id",
    "acfqp.campaign_operation_manifest.v180r12r3": "campaign_operation_manifest_id",
    "acfqp.campaign_native_zero_source_manifest.v180r12r3": (
        "native_zero_source_manifest_id"
    ),
    "acfqp.campaign_native_zero_import_inventory.v180r12r3": (
        "native_zero_import_inventory_id"
    ),
}
OS_EVIDENCE_SCHEMA_COUNTS = {
    "acfqp.campaign_memfd_stage_receipt.v180r12r3": 2,
    "acfqp.campaign_fd_visibility_receipt.v180r12r3": 4,
    "acfqp.campaign_pidfd_birth_receipt.v180r12r3": 2,
    "acfqp.campaign_pidfd_reap_receipt.v180r12r3": 2,
    "acfqp.campaign_cgroup_topology_receipt.v180r12r3": 1,
    "acfqp.campaign_cgroup_observation_receipt.v180r12r3": 1,
}
SUCCESS_ARTIFACT_ORDER = (
    "evidence_inventory", "execution_closure", "os_receipt", "ledger_closure"
)
SUCCESS_DURABLE_WRITE_ORDER = (
    "EVIDENCE_INVENTORY", "EXECUTION_CLOSURE", "OS_RECEIPT",
    "LEDGER_CLOSURE", "TERMINAL",
)
SUCCESS_ARTIFACT_ROWS = (
    (
        "EVIDENCE_INVENTORY", "evidence_inventory",
        EVIDENCE_INVENTORY_RELATIVE_PATH, EVIDENCE_INVENTORY_BUNDLE_SCHEMA,
        EVIDENCE_INVENTORY_BUNDLE_DOMAIN,
        "campaign_evidence_inventory_bundle_id", "campaign_evidence_inventory_bundle",
        EVIDENCE_INVENTORY_BUNDLE_FIELDS, EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
    ),
    (
        "EXECUTION_CLOSURE", "execution_closure", EXECUTION_CLOSURE_RELATIVE_PATH,
        EXECUTION_CLOSURE_SCHEMA, EXECUTION_CLOSURE_DOMAIN,
        "campaign_execution_closure_id", "campaign_execution_closure",
        EXECUTION_CLOSURE_FIELDS, EXECUTION_CLOSURE_BYTE_CAP,
    ),
    (
        "OS_RECEIPT", "os_receipt", OS_RECEIPT_RELATIVE_PATH,
        OS_RECEIPT_BUNDLE_SCHEMA, OS_RECEIPT_BUNDLE_DOMAIN,
        "campaign_os_receipt_bundle_id", "campaign_os_receipt_bundle",
        OS_RECEIPT_BUNDLE_FIELDS, OS_RECEIPT_BUNDLE_BYTE_CAP,
    ),
    (
        "LEDGER_CLOSURE", "ledger_closure", LEDGER_CLOSURE_RELATIVE_PATH,
        LEDGER_CLOSURE_SCHEMA, LEDGER_CLOSURE_DOMAIN,
        "campaign_ledger_closure_id", "campaign_ledger_closure",
        LEDGER_CLOSURE_FIELDS, LEDGER_CLOSURE_BYTE_CAP,
    ),
)


LAUNCH_RULE_DOCUMENT = {
    "schema": LAUNCH_RULE_SCHEMA,
    "source_closure_rule_id": SOURCE_CLOSURE_RULE_ID,
    "materialization_rule_id": MATERIALIZATION_RULE_ID,
    "materialization_terminal_schema": MATERIALIZATION_TERMINAL_SCHEMA,
    "python_executable": PYTHON_EXECUTABLE,
    "isolated_argv_prefix": list(ISOLATED_ARGV_PREFIX),
    "prelaunch_root_relative_path": PRELAUNCH_ROOT_RELATIVE_PATH,
    "external_root_relative_path": EXTERNAL_ROOT_RELATIVE_PATH,
    "bootstrap_relative_path": BOOTSTRAP_RELATIVE_PATH,
    "launcher_relative_path": LAUNCHER_RELATIVE_PATH,
    "manifest_relative_path": MANIFEST_RELATIVE_PATH,
    "materialization_terminal_relative_path": (
        MATERIALIZATION_TERMINAL_RELATIVE_PATH
    ),
    "materialization_failure_relative_path": MATERIALIZATION_FAILURE_RELATIVE_PATH,
    "measurement_attempt_relative_path": MEASUREMENT_ATTEMPT_RELATIVE_PATH,
    "measurement_receipt_relative_path": MEASUREMENT_RECEIPT_RELATIVE_PATH,
    "measurement_launch_failure_relative_path": (
        MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    ),
    "verification_attempt_relative_path": VERIFICATION_ATTEMPT_RELATIVE_PATH,
    "verification_receipt_relative_path": VERIFICATION_RECEIPT_RELATIVE_PATH,
    "verification_launch_failure_relative_path": (
        VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH
    ),
    "runtime_cas_root_relative_path": RUNTIME_CAS_ROOT_RELATIVE_PATH,
    "output_root_relative_path": OUTPUT_ROOT_RELATIVE_PATH,
    "terminal_relative_path": TERMINAL_RELATIVE_PATH,
    "evidence_inventory_relative_path": EVIDENCE_INVENTORY_RELATIVE_PATH,
    "execution_closure_relative_path": EXECUTION_CLOSURE_RELATIVE_PATH,
    "os_receipt_relative_path": OS_RECEIPT_RELATIVE_PATH,
    "ledger_closure_relative_path": LEDGER_CLOSURE_RELATIVE_PATH,
    "measurement_failure_relative_path": MEASUREMENT_FAILURE_RELATIVE_PATH,
    "verification_relative_path": VERIFICATION_RELATIVE_PATH,
    "verification_failure_relative_path": VERIFICATION_FAILURE_RELATIVE_PATH,
    "retained_replay_relative_path": RETAINED_REPLAY_RELATIVE_PATH,
    "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
    "address_space_cap_mechanism": "RLIMIT_AS_BEFORE_CHILD_EXEC",
    "wall_timeout_seconds": WALL_TIMEOUT_SECONDS,
    "wall_timeout_mechanism": (
        "ONE_POST_ATTEMPT_CLOCK_MONOTONIC_ORIGIN_SHARED_BY_INNER_AND_OUTER"
    ),
    "campaign_cleanup_grace_seconds": CAMPAIGN_CLEANUP_GRACE_SECONDS,
    "termination_grace_seconds": TERMINATION_GRACE_SECONDS,
    "outer_sigterm_deadline_seconds_before_hard": TERMINATION_GRACE_SECONDS,
    "outer_sigkill_at_hard_deadline": True,
    "post_sigkill_reap_check_is_single_bounded_observation": True,
    "unreaped_or_residual_process_state_is_typed_launch_failure": True,
    "measurement_cgroup_root_name_template": "v180r12r3-{campaign_attempt_id}",
    "measurement_cgroup_absence_checked_via_inherited_fd_250_before_popen": True,
    "measurement_cgroup_cleanup_ownership_requires_pre_popen_absence": True,
    "delegated_parent_is_cooperative_exclusive_for_the_single_authorized_attempt": True,
    "nonconcurrent_external_delegated_parent_mutation_is_a_preregistered_assumption": True,
    "unowned_or_root_identity_drifted_cgroup_is_observed_not_removed": True,
    "leaf_name_race_is_within_cooperative_exclusive_parent_assumption": True,
    "owned_measurement_cgroup_empty_wait_uses_same_hard_deadline": True,
    "no_cleanup_syscall_is_started_after_sampled_hard_deadline": True,
    "individual_cgroupfs_syscall_completion_before_hard_deadline_claimed": False,
    "cgroupfs_syscall_blocking_is_trusted_runtime_boundary": True,
    "measurement_cgroup_cleanup_observation_phases": list(
        MEASUREMENT_CGROUP_OBSERVATION_PHASES
    ),
    "measurement_cgroup_cleanup_observation_fields": sorted(
        MEASUREMENT_CGROUP_OBSERVATION_FIELDS
    ),
    "measurement_success_requires_exact_cgroup_root_absence_after_child": True,
    "sock_seqpacket_buffer_request_bytes": (
        SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
    ),
    "sock_seqpacket_effective_min_bytes": (
        SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
    ),
    "sock_seqpacket_buffer_applies_to_both_endpoints_of_both_pairs": True,
    "sock_seqpacket_buffers_configured_and_read_back_before_clone_or_send": True,
    "sock_seqpacket_insufficient_effective_buffer_fails_before_child_creation": True,
    "materialization_terminal_byte_cap": MATERIALIZATION_TERMINAL_BYTE_CAP,
    "external_root_byte_cap": EXTERNAL_ROOT_BYTE_CAP,
    "bootstrap_byte_cap": BOOTSTRAP_BYTE_CAP,
    "launcher_byte_cap": LAUNCHER_BYTE_CAP,
    "manifest_byte_cap": MANIFEST_BYTE_CAP,
    "child_stream_byte_cap": CHILD_STREAM_BYTE_CAP,
    "child_stream_retained_prefix_bytes": CHILD_STREAM_RETAINED_PREFIX_BYTES,
    "failure_message_byte_cap": FAILURE_MESSAGE_BYTE_CAP,
    "launch_artifact_byte_cap": LAUNCH_ARTIFACT_BYTE_CAP,
    "scientific_artifact_byte_cap": SCIENTIFIC_ARTIFACT_BYTE_CAP,
    "success_artifact_rows": [
        {
            "artifact_name": artifact_name,
            "mapping_key": mapping_key,
            "relative_path": relative_path,
            "schema": schema,
            "content_id_domain": domain,
            "identity_field": identity_field,
            "terminal_fact_prefix": terminal_prefix,
            "exact_field_keyset": sorted(fields),
            "byte_cap": byte_cap,
            "required_mode": "0400",
        }
        for (
            artifact_name, mapping_key, relative_path, schema, domain,
            identity_field, terminal_prefix, fields, byte_cap,
        ) in SUCCESS_ARTIFACT_ROWS
    ],
    "success_artifact_mapping_order": list(SUCCESS_ARTIFACT_ORDER),
    "success_durable_write_order": list(SUCCESS_DURABLE_WRITE_ORDER),
    "terminal_schema": TERMINAL_SCHEMA,
    "terminal_exact_field_keyset": sorted(TERMINAL_FIELDS),
    "terminal_byte_cap": SCIENTIFIC_ARTIFACT_BYTE_CAP,
    "success_artifacts_written_o_excl_mode_0400_file_and_directory_fsynced": True,
    "success_artifact_byte_cap_checked_before_create": True,
    "success_artifact_stable_exact_readback_required": True,
    "terminal_written_after_all_four_success_artifacts": True,
    "measurement_success_requires_exact_four_artifact_terminal_join": True,
    "verification_predecessor_rejoins_current_exact_four_artifact_bytes": True,
    "attempt_lock_written_before_child_exec": True,
    "attempt_and_terminal_distinguish_launcher_overhead_from_authorized_child_"
    "measurement_or_verification": True,
    "measurement_target_marks_measurement_attempted_at_launch_lock": True,
    "measurement_target_marks_measurement_completed_only_on_exact_success": True,
    "verification_target_marks_verification_attempted_at_launch_lock": True,
    "verification_target_marks_verification_completed_only_on_exact_success": True,
    "partial_attempt_or_receipt_observed_in_typed_failure": True,
    "primary_failure_preserved_when_failure_write_fails": True,
    "concurrent_attempt_lock_loser_is_clean_replay_without_failure_write": True,
    "success_receipt_forbidden_when_launch_failure_exists": True,
    "materialization_failure_sibling_forbids_any_launch": True,
    "retained_bootstrap_and_launcher_equal_c_pre_git_blob_facts": True,
    "source_bound_child_cwd_is_exact_repository_root": True,
    "measurement_predecessor_attempt_receipt_and_terminal_exact_replay": True,
    "runtime_cas_absent_at_measurement_success_and_verification_start": True,
    "same_target_identity_rerun_forbidden_after_any_progress": True,
    "materialization_reused_without_rematerialization": True,
    "preauthorization_supervision": True,
    "campaign_actual_measurement": False,
    "successful_child_stdout_and_stderr_must_be_exactly_empty": True,
}
LAUNCH_RULE_ID = EXPECTED_LAUNCH_RULE_ID


class V180r12r3PrelaunchLaunchError(RuntimeError):
    """The materialization, launch state, cap, or child terminal changed."""


class V180r12r3PrelaunchLaunchReplayForbidden(V180r12r3PrelaunchLaunchError):
    """The target-specific launch identity already has durable progress."""


def _fail(message: str) -> NoReturn:
    raise V180r12r3PrelaunchLaunchError(message)


def _require_rule_identities_frozen() -> None:
    """Reject the outcome path before any attempt write while IDs are sentinels."""

    if (
        SOURCE_CLOSURE_RULE_ID == "0" * 64
        or MATERIALIZATION_RULE_ID == "0" * 64
        or LAUNCH_RULE_ID == "0" * 64
    ):
        _fail("prelaunch launch rule identities remain zero sentinels")
    computed_launch_rule_id = hashlib.sha256(
        json.dumps(
            LAUNCH_RULE_DOCUMENT,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if not (
        _SHA256.fullmatch(SOURCE_CLOSURE_RULE_ID)
        and _SHA256.fullmatch(MATERIALIZATION_RULE_ID)
        and _SHA256.fullmatch(LAUNCH_RULE_ID)
        and LAUNCH_RULE_DOCUMENT["source_closure_rule_id"]
        == SOURCE_CLOSURE_RULE_ID
        and LAUNCH_RULE_DOCUMENT["materialization_rule_id"]
        == MATERIALIZATION_RULE_ID
        and computed_launch_rule_id == LAUNCH_RULE_ID
    ):
        _fail("prelaunch launch rule identity binding changed")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _require_sha256(value: object, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _fail(f"{label} is not one lowercase SHA-256 digest")
    return value


def _require_nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} is not one nonnegative integer")
    return value


def _require_object_id(value: object, label: str) -> str:
    if (
        type(value) is not str
        or re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", value) is None
    ):
        _fail(f"{label} is not one lowercase Git object ID")
    return value


def _require_relative(value: object, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        _fail(f"{label} is not one POSIX relative path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        _fail(f"{label} escapes its fixed root")
    return relative.as_posix()


def _require_root(path: Path) -> Path:
    if not path.is_absolute() or str(path) != str(path.resolve(strict=True)):
        _fail("repository root is not one exact existing absolute path")
    metadata = os.lstat(path)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        _fail("repository root is linked or non-directory")
    return path


def _open_regular_no_follow(path: Path, *, byte_cap: int) -> tuple[int, os.stat_result]:
    if not path.is_absolute():
        _fail("stable read path is not absolute")
    current = Path(path.anchor)
    for part in path.parts[1:-1]:
        current /= part
        metadata = os.lstat(current)
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            _fail("stable read ancestor is linked or non-directory")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as error:
        raise V180r12r3PrelaunchLaunchError("stable read open failed") from error
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        os.close(descriptor)
        _fail("stable read target is not one singly linked regular file")
    if before.st_size < 0 or before.st_size > byte_cap:
        os.close(descriptor)
        _fail("stable read target exceeds its byte cap")
    return descriptor, before


def _stable_read(
    path: Path,
    *,
    byte_cap: int,
    required_mode: int | None = None,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> bytes:
    descriptor, before = _open_regular_no_follow(path, byte_cap=byte_cap)
    chunks: list[bytes] = []
    remaining = before.st_size
    try:
        while remaining:
            chunk = os.read(descriptor, min(STREAM_BUFFER_BYTES, remaining))
            if not chunk:
                _fail("stable read ended before its registered size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("stable read grew beyond its registered size")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    compared = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in compared):
        _fail("stable read metadata changed")
    raw = b"".join(chunks)
    if required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode:
        _fail("stable read immutable mode changed")
    if expected_size is not None and len(raw) != expected_size:
        _fail("stable read byte count changed")
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
        _fail("stable read digest changed")
    return raw


def _parse_canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V180r12r3PrelaunchLaunchError(f"{label} is invalid JSON") from error
    if type(value) is not dict or _canonical_json_bytes(value) != raw:
        _fail(f"{label} is noncanonical or not one object")
    return value


def _fact(document: dict[str, Any], key: str, expected_path: str) -> dict[str, Any]:
    value = document.get(key)
    if type(value) is not dict or set(value) != {"relative_path", "byte_count", "sha256"}:
        _fail(f"materialization {key} fact schema changed")
    if _require_relative(value["relative_path"], f"{key} path") != expected_path:
        _fail(f"materialization {key} path changed")
    if type(value["byte_count"]) is not int or value["byte_count"] < 0:
        _fail(f"materialization {key} byte count changed")
    _require_sha256(value["sha256"], f"{key} digest")
    return value


def _require_raw_fact(
    value: object, label: str, *, expected_path: str | None = None
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RAW_FACT_KEYS:
        _fail(f"{label} raw fact schema changed")
    path = _require_relative(value["relative_path"], f"{label} path")
    if expected_path is not None and path != expected_path:
        _fail(f"{label} path changed")
    _require_nonnegative_int(value["byte_count"], f"{label} byte count")
    _require_sha256(value["sha256"], f"{label} digest")
    return value


def _require_git_blob_fact(
    value: object, label: str, *, expected_path: str
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _GIT_BLOB_FACT_KEYS:
        _fail(f"{label} Git blob fact schema changed")
    if (
        _require_relative(value["relative_path"], f"{label} path")
        != expected_path
        or value["git_mode"] not in {"100644", "100755"}
    ):
        _fail(f"{label} Git path or mode changed")
    _require_object_id(value["git_blob_id"], f"{label} blob ID")
    _require_nonnegative_int(value["byte_count"], f"{label} byte count")
    _require_sha256(value["sha256"], f"{label} digest")
    return value


def _require_closure_summary(value: object, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _CLOSURE_KEYS:
        _fail(f"{label} closure schema changed")
    facts = value["facts"]
    if type(facts) is not list:
        _fail(f"{label} facts are not one list")
    count = _require_nonnegative_int(value["file_count"], f"{label} file count")
    total = _require_nonnegative_int(
        value["total_byte_count"], f"{label} total byte count"
    )
    if count != len(facts):
        _fail(f"{label} file count changed")
    if total != sum(
        _require_nonnegative_int(row.get("byte_count"), f"{label} fact bytes")
        if type(row) is dict
        else _fail(f"{label} fact is not one object")
        for row in facts
    ):
        _fail(f"{label} total byte count changed")
    if (
        _require_sha256(value["facts_sha256"], f"{label} facts digest")
        != hashlib.sha256(_canonical_json_bytes(facts)).hexdigest()
    ):
        _fail(f"{label} facts digest changed")
    return value


_MATERIALIZATION_REQUIRED_KEYS = {
    "schema",
    "materialization_rule_id",
    "source_closure_rule_id",
    "repository_root",
    "external_root",
    "git_topology",
    "bootstrap_source_git_blob",
    "materializer_source_git_blob",
    "launcher_source_git_blob",
    "retained_bootstrap",
    "retained_launcher",
    "launch_manifest",
    "materialization_terminal_relative_path",
    "materialization_failure_relative_path",
    "authorization_source_closure_file_count",
    "authorization_source_closure_total_byte_count",
    "authorization_source_closure_facts_sha256",
    "third_party_source_closure_file_count",
    "third_party_source_closure_total_byte_count",
    "third_party_source_closure_facts_sha256",
    "normalized_wrapper_fact",
    "current_literal_wrapper_raw_observation",
    "launch_manifest_digest_is_runtime_supplied_not_protocol_frozen",
    "launch_manifest_has_no_self_digest",
    "frozen_authorization_context_sha256",
    "external_root_created_before_authorized_measurement_execution",
    "external_root_required_before_authorization_issuance",
    "materialization_terminal_written_last",
    "write_once_o_excl",
    "write_no_follow",
    "close_on_exec",
    "output_directory_mode",
    "output_file_mode",
    "file_and_directory_fsync_required",
    "same_materialization_identity_rerun_forbidden",
    "construction_only",
    "preauthorization_supervision",
    "campaign_actual_measurement",
    "scientific_occurrence_executed",
    "v180r12r3_outcome_bytes_accessed",
    "counter_records_issued",
    "work_vectors_issued",
    "comparison_vectors_issued",
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
    "official_execution_allowed",
    "success",
    "materialization_terminal_id",
}

_EXTERNAL_ROOT_KEYS = {
    "schema",
    "materialization_rule_id",
    "source_closure_rule_id",
    "repository_root",
    "git_directory",
    "c_pre_commit_id",
    "c_pre_tree_id",
    "bootstrap_git_blob",
    "launcher_git_blob",
    "materializer_git_blob",
    "third_party_source_roots",
    "frozen_authorization_context",
    "created_before_v180r12r3_authorized_measurement_execution",
    "v180r12r3_outcome_bytes_accessed",
}
_GIT_BLOB_FACT_KEYS = {
    "relative_path",
    "git_mode",
    "git_blob_id",
    "byte_count",
    "sha256",
}
_RAW_FACT_KEYS = {"relative_path", "byte_count", "sha256"}
_NORMALIZED_WRAPPER_FACT_KEYS = _RAW_FACT_KEYS | {
    "binding_kind",
    "redacted_constant_names",
}
_CLOSURE_KEYS = {"facts", "file_count", "total_byte_count", "facts_sha256"}
_MANIFEST_KEYS = {
    "schema",
    "repository_root",
    "c_pre_root",
    "manifest_relative_path",
    "c_pre_commit_id",
    "bootstrap",
    "runtime",
    "git",
    "authorization_source_closure_kind",
    "authorization_self_module",
    "authorization_raw_source_modules",
    "authorization_source_closure",
    "source_modules",
    "third_party_source_closure",
    "targets",
    "internal_target_contract",
    "frozen_authorization_context",
    "working_tree_mutation_after_snapshot_in_scope",
}
_ATTEMPT_KEYS = {
    "schema",
    "launch_rule_id",
    "target",
    "repository_root",
    "materialization_terminal_id",
    "materialization_terminal_byte_count",
    "materialization_terminal_sha256",
    "launch_manifest_sha256",
    "child_argv",
    "child_environment",
    "address_space_hard_cap_bytes",
    "address_space_cap_applied_before_child_exec",
    "wall_timeout_seconds",
    "attempt_lock_written_before_child_exec",
    "same_target_identity_rerun_forbidden",
    "preauthorization_supervision",
    "campaign_actual_measurement",
    "scientific_occurrence_started",
    "authorized_child_measurement_execution_attempted",
    "authorized_child_measurement_execution_completed",
    "producer_free_verification_attempted",
    "producer_free_verification_completed",
    "launch_attempt_id",
}
_TERMINAL_KEYS = {
    "schema",
    "launch_rule_id",
    "launch_attempt_id",
    "target",
    "return_code",
    "timed_out",
    "child_stdout",
    "child_stderr",
    "progress_observations",
    "same_target_identity_rerun_forbidden",
    "attempt_lock_preserved",
    "address_space_hard_cap_bytes",
    "wall_timeout_seconds",
    "monotonic_origin_ns",
    "hard_deadline_ns",
    "campaign_deadline_ns",
    "campaign_cleanup_grace_seconds",
    "termination_grace_seconds",
    "measurement_cgroup_cleanup_observations",
    "preauthorization_supervision",
    "campaign_actual_measurement",
    "authorized_child_measurement_execution_attempted",
    "authorized_child_measurement_execution_completed",
    "producer_free_verification_attempted",
    "producer_free_verification_completed",
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
    "official_execution_allowed",
    "success",
    "failure_type",
    "failure_message",
}


def _validated_frozen_authorization_context(value: object) -> dict[str, Any]:
    if type(value) is not dict or tuple(value) != FROZEN_AUTHORIZATION_CONTEXT_FIELDS:
        if type(value) is not dict or set(value) != set(FROZEN_AUTHORIZATION_CONTEXT_FIELDS):
            _fail("frozen authorization context schema changed")
    if value["schema"] != FROZEN_AUTHORIZATION_CONTEXT_SCHEMA:
        _fail("frozen authorization context schema changed")
    for key in (
        "protocol_id", "protocol_sha256", "authorization_id",
        "authorization_sha256", "authorization_evidence_id",
        "authorization_evidence_sha256", "campaign_measurement_execution_slot_id",
        "logical_occurrence_id", "execution_nonce", "campaign_attempt_id",
    ):
        _require_sha256(value[key], f"frozen authorization {key}")
    for key in (
        "protocol_byte_count", "authorization_byte_count",
        "authorization_evidence_byte_count",
    ):
        if _require_nonnegative_int(value[key], f"frozen authorization {key}") <= 0:
            _fail(f"frozen authorization {key} must be positive")
    cgroup = value["cgroup_parent_fact"]
    runtime = value["runtime_capability_fact"]
    if (
        type(cgroup) is not dict
        or set(cgroup) != CGROUP_PARENT_FACT_FIELDS
        or cgroup.get("schema") != "acfqp.v180r12r3_cgroup_parent_fact.v1"
        or type(runtime) is not dict
        or set(runtime) != RUNTIME_CAPABILITY_FACT_FIELDS
        or runtime.get("schema")
        != "acfqp.v180r12r3_runtime_capability_fact.v1"
        or runtime.get("admitted") is not True
        or cgroup.get("owner_uid") != runtime.get("uid")
        or cgroup.get("owner_gid") != runtime.get("gid")
        or type(cgroup.get("mode")) is not int
        or cgroup["mode"] & (stat.S_IWUSR | stat.S_IXUSR)
        != (stat.S_IWUSR | stat.S_IXUSR)
    ):
        _fail("frozen authorization cgroup or runtime fact changed")
    attempt_payload = {
        "schema": "acfqp.campaign_measurement_attempt.v180r12r3",
        "protocol_id": value["protocol_id"],
        "authorization_id": value["authorization_id"],
        "authorization_evidence_id": value["authorization_evidence_id"],
        "campaign_measurement_execution_slot_id": value[
            "campaign_measurement_execution_slot_id"
        ],
        "logical_occurrence_id": value["logical_occurrence_id"],
        "execution_nonce": value["execution_nonce"],
    }
    expected_attempt = hashlib.sha256(
        b"acfqp:construction-k7-campaign-measurement-attempt:v180r12r3\x00"
        + _canonical_json_bytes(attempt_payload)
    ).hexdigest()
    if value["campaign_attempt_id"] != expected_attempt:
        _fail("frozen campaign attempt six-authority identity changed")
    return value


def _load_materialization(
    repository_root: Path, expected_sha256: str
) -> tuple[dict[str, Any], bytes]:
    if _lexists(repository_root / MATERIALIZATION_FAILURE_RELATIVE_PATH):
        raise V180r12r3PrelaunchLaunchReplayForbidden(
            "materialization failure already exists; launch identity is ineligible"
        )
    path = repository_root / MATERIALIZATION_TERMINAL_RELATIVE_PATH
    raw = _stable_read(
        path,
        byte_cap=MATERIALIZATION_TERMINAL_BYTE_CAP,
        required_mode=0o400,
        expected_sha256=expected_sha256,
    )
    document = _parse_canonical_object(raw, "materialization terminal")
    if set(document) != _MATERIALIZATION_REQUIRED_KEYS:
        _fail("materialization terminal schema changed")
    terminal_id = document["materialization_terminal_id"]
    payload = dict(document)
    del payload["materialization_terminal_id"]
    if not (
        document["schema"] == MATERIALIZATION_TERMINAL_SCHEMA
        and document["materialization_rule_id"] == MATERIALIZATION_RULE_ID
        and document["source_closure_rule_id"] == SOURCE_CLOSURE_RULE_ID
        and document["repository_root"] == str(repository_root)
        and _require_sha256(terminal_id, "materialization terminal ID")
        == hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
        and document["success"] is True
        and document["construction_only"] is True
        and document["preauthorization_supervision"] is True
        and document["campaign_actual_measurement"] is False
        and document["scientific_occurrence_executed"] is False
        and document["v180r12r3_outcome_bytes_accessed"] is False
        and document[
            "external_root_created_before_authorized_measurement_execution"
        ]
        is True
        and document["external_root_required_before_authorization_issuance"]
        is False
        and document["materialization_terminal_relative_path"]
        == MATERIALIZATION_TERMINAL_RELATIVE_PATH
        and document["materialization_failure_relative_path"]
        == MATERIALIZATION_FAILURE_RELATIVE_PATH
        and document["launch_manifest_digest_is_runtime_supplied_not_protocol_frozen"]
        is True
        and document["launch_manifest_has_no_self_digest"] is True
        and document["materialization_terminal_written_last"] is True
        and document["write_once_o_excl"] is True
        and document["write_no_follow"] is True
        and document["close_on_exec"] is True
        and document["output_directory_mode"] == "0700"
        and document["output_file_mode"] == "0400"
        and document["file_and_directory_fsync_required"] is True
        and document["same_materialization_identity_rerun_forbidden"] is True
        and document["counter_records_issued"] is False
        and document["work_vectors_issued"] is False
        and document["comparison_vectors_issued"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
        and document["BREAK_EVEN_GATE"] == "NOT_RUN"
        and document["official_execution_allowed"] is False
    ):
        _fail("materialization terminal boundary changed")

    external_fact = document["external_root"]
    if type(external_fact) is not dict or set(external_fact) != {
        "absolute_path",
        "byte_count",
        "sha256",
        "immutable_mode",
    }:
        _fail("materialization external root fact schema changed")
    external_path = repository_root / EXTERNAL_ROOT_RELATIVE_PATH
    if not (
        external_fact["absolute_path"] == str(external_path)
        and external_fact["immutable_mode"] == "0400"
    ):
        _fail("materialization external root path or mode changed")
    external_size = _require_nonnegative_int(
        external_fact["byte_count"], "materialization external root byte count"
    )
    external_sha256 = _require_sha256(
        external_fact["sha256"], "materialization external root digest"
    )
    external_raw = _stable_read(
        external_path,
        byte_cap=EXTERNAL_ROOT_BYTE_CAP,
        required_mode=0o400,
        expected_size=external_size,
        expected_sha256=external_sha256,
    )
    external = _parse_canonical_object(external_raw, "materialization external root")
    if set(external) != _EXTERNAL_ROOT_KEYS or not (
        external["schema"] == "acfqp.v180r12r3_prelaunch_external_root.v1"
        and external["materialization_rule_id"] == MATERIALIZATION_RULE_ID
        and external["source_closure_rule_id"] == SOURCE_CLOSURE_RULE_ID
        and external["repository_root"] == str(repository_root)
        and external["git_directory"] == str(repository_root / ".git")
        and external["created_before_v180r12r3_authorized_measurement_execution"]
        is True
        and external["v180r12r3_outcome_bytes_accessed"] is False
    ):
        _fail("materialization external root boundary changed")
    c_pre = external["c_pre_commit_id"]
    if type(c_pre) is not str or _COMMIT.fullmatch(c_pre) is None:
        _fail("materialization external C_pre commit changed")
    c_pre_tree = _require_object_id(
        external["c_pre_tree_id"], "materialization external C_pre tree"
    )
    source_git_facts = (
        (
            "bootstrap_source_git_blob",
            "bootstrap_git_blob",
            SOURCE_BOOTSTRAP_RELATIVE_PATH,
        ),
        (
            "launcher_source_git_blob",
            "launcher_git_blob",
            SOURCE_LAUNCHER_RELATIVE_PATH,
        ),
        (
            "materializer_source_git_blob",
            "materializer_git_blob",
            SOURCE_MATERIALIZER_RELATIVE_PATH,
        ),
    )
    for terminal_key, external_key, expected_path in source_git_facts:
        terminal_fact = _require_git_blob_fact(
            document[terminal_key], terminal_key, expected_path=expected_path
        )
        external_git_fact = _require_git_blob_fact(
            external[external_key], external_key, expected_path=expected_path
        )
        if terminal_fact != external_git_fact:
            _fail(f"materialization {terminal_key} external-root join changed")
    roots = external["third_party_source_roots"]
    if type(roots) is not dict or set(roots) != {"packaging", "tomli"}:
        _fail("materialization external third-party roots changed")
    for root in roots.values():
        if type(root) is not str or not Path(root).is_absolute():
            _fail("materialization external third-party root is not absolute")
    frozen_context = _validated_frozen_authorization_context(
        external["frozen_authorization_context"]
    )
    if document["frozen_authorization_context_sha256"] != hashlib.sha256(
        _canonical_json_bytes(frozen_context)
    ).hexdigest():
        _fail("materialization frozen authorization context join changed")

    topology = document["git_topology"]
    topology_keys = {
        "c_pre_commit_id",
        "c_pre_tree_id",
        "empty_bridge_commit_id",
        "empty_bridge_tree_id",
        "literal_commit_id",
        "literal_commit_tree_id",
        "literal_wrapper_prior_blob_id",
        "literal_wrapper_blob_id",
    }
    if type(topology) is not dict or set(topology) != topology_keys:
        _fail("materialization terminal C_pre topology changed")
    for key in (
        "c_pre_commit_id",
        "empty_bridge_commit_id",
        "literal_commit_id",
    ):
        if type(topology[key]) is not str or _COMMIT.fullmatch(topology[key]) is None:
            _fail(f"materialization topology {key} changed")
    for key in topology_keys - {
        "c_pre_commit_id",
        "empty_bridge_commit_id",
        "literal_commit_id",
    }:
        _require_object_id(topology[key], f"materialization topology {key}")
    if not (
        topology["c_pre_commit_id"] == c_pre
        and topology["c_pre_tree_id"] == c_pre_tree
        and topology["empty_bridge_tree_id"] == c_pre_tree
        and len(
            {
                topology["c_pre_commit_id"],
                topology["empty_bridge_commit_id"],
                topology["literal_commit_id"],
            }
        )
        == 3
    ):
        _fail("materialization topology join changed")

    normalized = document["normalized_wrapper_fact"]
    if type(normalized) is not dict or set(normalized) != _NORMALIZED_WRAPPER_FACT_KEYS:
        _fail("materialization normalized wrapper schema changed")
    _require_raw_fact(
        {key: normalized[key] for key in _RAW_FACT_KEYS},
        "materialization normalized wrapper",
        expected_path=AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
    )
    if not (
        normalized["binding_kind"] == NORMALIZED_WRAPPER_BINDING_KIND
        and normalized["redacted_constant_names"]
        == list(WRAPPER_REDACTED_CONSTANT_NAMES)
    ):
        _fail("materialization normalized wrapper boundary changed")
    _require_raw_fact(
        document["current_literal_wrapper_raw_observation"],
        "materialization current wrapper",
        expected_path=AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
    )
    authorization_count = _require_nonnegative_int(
        document["authorization_source_closure_file_count"],
        "materialization authorization closure file count",
    )
    authorization_total = _require_nonnegative_int(
        document["authorization_source_closure_total_byte_count"],
        "materialization authorization closure bytes",
    )
    third_party_count = _require_nonnegative_int(
        document["third_party_source_closure_file_count"],
        "materialization third-party closure file count",
    )
    third_party_total = _require_nonnegative_int(
        document["third_party_source_closure_total_byte_count"],
        "materialization third-party closure bytes",
    )
    if not (
        0 < authorization_count <= 4096
        and 0 < authorization_total <= 128 * 1024 * 1024
        and 0 < third_party_count <= 4096
        and 0 < third_party_total <= 128 * 1024 * 1024
    ):
        _fail("materialization source closure denominator changed")
    _require_sha256(
        document["authorization_source_closure_facts_sha256"],
        "materialization authorization closure digest",
    )
    _require_sha256(
        document["third_party_source_closure_facts_sha256"],
        "materialization third-party closure digest",
    )
    return document, raw


def _verify_materialized_files(
    repository_root: Path, document: dict[str, Any]
) -> tuple[Path, Path, Path, str, dict[str, Any]]:
    bootstrap_fact = _fact(document, "retained_bootstrap", BOOTSTRAP_RELATIVE_PATH)
    launcher_fact = _fact(document, "retained_launcher", LAUNCHER_RELATIVE_PATH)
    manifest_fact = _fact(document, "launch_manifest", MANIFEST_RELATIVE_PATH)
    for retained_fact, source_fact, label in (
        (
            bootstrap_fact,
            document["bootstrap_source_git_blob"],
            "bootstrap",
        ),
        (
            launcher_fact,
            document["launcher_source_git_blob"],
            "launcher",
        ),
    ):
        if not (
            retained_fact["byte_count"] == source_fact["byte_count"]
            and retained_fact["sha256"] == source_fact["sha256"]
        ):
            _fail(f"retained {label} differs from its C_pre Git blob fact")
    bootstrap = repository_root / BOOTSTRAP_RELATIVE_PATH
    launcher = repository_root / LAUNCHER_RELATIVE_PATH
    manifest = repository_root / MANIFEST_RELATIVE_PATH
    _stable_read(
        bootstrap,
        byte_cap=BOOTSTRAP_BYTE_CAP,
        required_mode=0o400,
        expected_size=bootstrap_fact["byte_count"],
        expected_sha256=bootstrap_fact["sha256"],
    )
    _stable_read(
        launcher,
        byte_cap=LAUNCHER_BYTE_CAP,
        required_mode=0o400,
        expected_size=launcher_fact["byte_count"],
        expected_sha256=launcher_fact["sha256"],
    )
    manifest_raw = _stable_read(
        manifest,
        byte_cap=MANIFEST_BYTE_CAP,
        required_mode=0o400,
        expected_size=manifest_fact["byte_count"],
        expected_sha256=manifest_fact["sha256"],
    )
    manifest_document = _parse_canonical_object(manifest_raw, "launch manifest")
    if set(manifest_document) != _MANIFEST_KEYS or not (
        manifest_document["schema"]
        == "acfqp.v180r12r3_source_bound_launch_manifest.v1"
        and manifest_document["repository_root"] == str(repository_root)
        and manifest_document["c_pre_root"]
        == str(repository_root / PRELAUNCH_ROOT_RELATIVE_PATH)
        and manifest_document["manifest_relative_path"] == "launch_manifest.json"
        and manifest_document["c_pre_commit_id"]
        == document["git_topology"]["c_pre_commit_id"]
        and manifest_document["working_tree_mutation_after_snapshot_in_scope"]
        is False
    ):
        _fail("launch manifest boundary changed")
    manifest_context = _validated_frozen_authorization_context(
        manifest_document["frozen_authorization_context"]
    )
    if hashlib.sha256(_canonical_json_bytes(manifest_context)).hexdigest() != (
        document["frozen_authorization_context_sha256"]
    ):
        _fail("launch manifest frozen authorization context join changed")
    manifest_bootstrap = _require_raw_fact(
        manifest_document["bootstrap"],
        "manifest bootstrap",
        expected_path="bootstrap.py",
    )
    if not (
        manifest_bootstrap["byte_count"] == bootstrap_fact["byte_count"]
        and manifest_bootstrap["sha256"] == bootstrap_fact["sha256"]
    ):
        _fail("manifest retained bootstrap join changed")
    authorization = _require_closure_summary(
        manifest_document["authorization_source_closure"],
        "manifest authorization source",
    )
    third_party = _require_closure_summary(
        manifest_document["third_party_source_closure"],
        "manifest third-party source",
    )
    if not (
        authorization["file_count"]
        == document["authorization_source_closure_file_count"]
        and authorization["total_byte_count"]
        == document["authorization_source_closure_total_byte_count"]
        and authorization["facts_sha256"]
        == document["authorization_source_closure_facts_sha256"]
        and third_party["file_count"]
        == document["third_party_source_closure_file_count"]
        and third_party["total_byte_count"]
        == document["third_party_source_closure_total_byte_count"]
        and third_party["facts_sha256"]
        == document["third_party_source_closure_facts_sha256"]
    ):
        _fail("manifest closure summary join changed")
    wrapper_rows = [
        row
        for row in authorization["facts"]
        if type(row) is dict
        and row.get("relative_path") == AUTHORIZATION_EVIDENCE_RELATIVE_PATH
    ]
    if wrapper_rows != [document["normalized_wrapper_fact"]]:
        _fail("manifest normalized wrapper join changed")
    source_modules = manifest_document["source_modules"]
    if type(source_modules) is not list:
        _fail("manifest source modules changed")
    wrapper_source_rows = [
        {
            key: row[key]
            for key in _RAW_FACT_KEYS
        }
        for row in source_modules
        if type(row) is dict
        and row.get("relative_path") == AUTHORIZATION_EVIDENCE_RELATIVE_PATH
        and _RAW_FACT_KEYS <= set(row)
    ]
    if wrapper_source_rows != [document["current_literal_wrapper_raw_observation"]]:
        _fail("manifest current wrapper join changed")
    targets = manifest_document["targets"]
    if type(targets) is not dict or set(targets) != set(MANIFEST_TARGET_RUNNER_PATHS):
        _fail("manifest runner target set changed")
    for target, expected_path in MANIFEST_TARGET_RUNNER_PATHS.items():
        _require_raw_fact(
            targets[target], f"manifest {target} runner", expected_path=expected_path
        )
    if manifest_document["internal_target_contract"] != INTERNAL_TARGET_CONTRACT:
        _fail("manifest internal target contract changed")
    if Path(__file__).absolute() != launcher or sys.argv[0] != str(launcher):
        _fail("executing retained launcher path changed")
    return (
        bootstrap,
        launcher,
        manifest,
        manifest_fact["sha256"],
        manifest_context,
    )


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _state_paths(repository_root: Path, target: str) -> dict[str, Path]:
    target_paths = _TARGETS[target]
    return {
        "attempt": repository_root / target_paths["attempt"],
        "receipt": repository_root / target_paths["receipt"],
        "launch_failure": repository_root / target_paths["launch_failure"],
        "runtime_cas": repository_root / RUNTIME_CAS_ROOT_RELATIVE_PATH,
        "output_root": repository_root / OUTPUT_ROOT_RELATIVE_PATH,
        "terminal": repository_root / TERMINAL_RELATIVE_PATH,
        "evidence_inventory": repository_root / EVIDENCE_INVENTORY_RELATIVE_PATH,
        "execution_closure": repository_root / EXECUTION_CLOSURE_RELATIVE_PATH,
        "os_receipt": repository_root / OS_RECEIPT_RELATIVE_PATH,
        "ledger_closure": repository_root / LEDGER_CLOSURE_RELATIVE_PATH,
        "measurement_failure": repository_root / MEASUREMENT_FAILURE_RELATIVE_PATH,
        "verification": repository_root / VERIFICATION_RELATIVE_PATH,
        "verification_failure": repository_root / VERIFICATION_FAILURE_RELATIVE_PATH,
        "retained_replay": repository_root / RETAINED_REPLAY_RELATIVE_PATH,
    }


def _require_fresh_target_state(
    repository_root: Path, target: str, materialization_terminal_id: str
) -> dict[str, Path]:
    paths = _state_paths(repository_root, target)
    if any(_lexists(paths[name]) for name in ("attempt", "receipt", "launch_failure")):
        raise V180r12r3PrelaunchLaunchReplayForbidden(
            "target launch attempt, receipt, or failure already exists"
        )
    if target == "measurement":
        other = _state_paths(repository_root, "verification")
        forbidden = {
            *paths.values(),
            other["attempt"],
            other["receipt"],
            other["launch_failure"],
        }
        if any(_lexists(path) for path in forbidden):
            raise V180r12r3PrelaunchLaunchReplayForbidden(
                "measurement launch is not at one fresh zero-progress boundary"
            )
    else:
        measurement = _state_paths(repository_root, "measurement")
        if not (
            _lexists(measurement["attempt"])
            and _lexists(measurement["receipt"])
            and not _lexists(measurement["launch_failure"])
            and _lexists(paths["terminal"])
            and not _lexists(paths["measurement_failure"])
        ):
            raise V180r12r3PrelaunchLaunchReplayForbidden(
                "verification launch lacks one successful measurement predecessor"
            )
        _require_successful_measurement_launch(
            repository_root, materialization_terminal_id
        )
        for name in ("verification", "verification_failure", "retained_replay"):
            if _lexists(paths[name]):
                raise V180r12r3PrelaunchLaunchReplayForbidden(
                    "verification scientific progress already exists"
                )
    return paths


def _open_output_parent(path: Path) -> tuple[int, str]:
    parent = path.parent
    current = Path(parent.anchor)
    for part in parent.parts[1:]:
        current /= part
        metadata = os.lstat(current)
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            _fail("write-once ancestor is linked or non-directory")
    metadata = os.lstat(parent)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        _fail("write-once parent is linked or non-directory")
    descriptor = os.open(
        parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    return descriptor, path.name


def _write_once(path: Path, raw: bytes) -> None:
    parent_fd, name = _open_output_parent(path)
    descriptor: int | None = None
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o400,
            dir_fd=parent_fd,
        )
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                _fail("write-once launch artifact made no progress")
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.fsync(parent_fd)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)
    _stable_read(
        path,
        byte_cap=max(len(raw), 1),
        required_mode=0o400,
        expected_size=len(raw),
        expected_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _stream_regular_fact(path: Path, byte_cap: int) -> dict[str, Any]:
    descriptor, before = _open_regular_no_follow(path, byte_cap=byte_cap)
    digest = hashlib.sha256()
    remaining = before.st_size
    try:
        while remaining:
            chunk = os.read(descriptor, min(STREAM_BUFFER_BYTES, remaining))
            if not chunk:
                _fail("streaming observation ended before its registered size")
            digest.update(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("streaming observation grew beyond its registered size")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    compared = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(before, field) != getattr(after, field) for field in compared):
        _fail("streaming observation metadata changed")
    return {
        "presence": "REGULAR_FILE",
        "mode": stat.S_IMODE(before.st_mode),
        "byte_count": before.st_size,
        "sha256": digest.hexdigest(),
    }


def _fact_for_path(path: Path, byte_cap: int) -> dict[str, Any]:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return {"presence": "ABSENT"}
    except OSError as error:
        error_type, error_message = _bounded_error(error)
        return {
            "presence": "OBSERVATION_ERROR",
            "error_type": error_type,
            "error_message": error_message,
        }
    if stat.S_ISLNK(metadata.st_mode):
        return {"presence": "SYMLINK"}
    if stat.S_ISDIR(metadata.st_mode):
        return {"presence": "DIRECTORY", "mode": stat.S_IMODE(metadata.st_mode)}
    if not stat.S_ISREG(metadata.st_mode):
        return {"presence": "NONREGULAR"}
    result: dict[str, Any] = {
        "presence": "REGULAR_FILE",
        "mode": stat.S_IMODE(metadata.st_mode),
        "byte_count": metadata.st_size,
    }
    if metadata.st_size <= byte_cap:
        try:
            return _stream_regular_fact(path, byte_cap)
        except BaseException as error:
            error_type, error_message = _bounded_error(error)
            result["read_error_type"] = error_type
            result["read_error_message"] = error_message
    else:
        result["byte_cap_exceeded"] = True
        result["sha256"] = None
    return result


def _progress_observations(paths: dict[str, Path]) -> dict[str, Any]:
    caps = {
        "evidence_inventory": EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
        "execution_closure": EXECUTION_CLOSURE_BYTE_CAP,
        "os_receipt": OS_RECEIPT_BUNDLE_BYTE_CAP,
        "ledger_closure": LEDGER_CLOSURE_BYTE_CAP,
    }
    return {
        name: _fact_for_path(
            path,
            caps.get(
                name,
                SCIENTIFIC_ARTIFACT_BYTE_CAP
                if name
                in {
                    "terminal",
                    "measurement_failure",
                    "verification",
                    "verification_failure",
                    "retained_replay",
                }
                else LAUNCH_ARTIFACT_BYTE_CAP
            ),
        )
        for name, path in sorted(paths.items())
    }


def _load_launch_document(path: Path, schema: str, id_key: str) -> dict[str, Any]:
    raw = _stable_read(
        path,
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    document = _parse_canonical_object(raw, path.name)
    expected_keys = (
        _ATTEMPT_KEYS
        if schema == LAUNCH_ATTEMPT_SCHEMA
        else _TERMINAL_KEYS | {id_key}
    )
    if set(document) != expected_keys:
        _fail(f"{path.name} schema changed")
    identifier = document.get(id_key)
    payload = dict(document)
    payload.pop(id_key, None)
    if not (
        document.get("schema") == schema
        and document.get("launch_rule_id") == LAUNCH_RULE_ID
        and _require_sha256(identifier, f"{path.name} ID")
        == hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    ):
        _fail(f"{path.name} identity changed")
    if schema in {LAUNCH_RECEIPT_SCHEMA, LAUNCH_FAILURE_SCHEMA}:
        target = document.get("target")
        if target not in _TARGETS:
            _fail(f"{path.name} target changed")
        _validate_measurement_cgroup_observations(
            document.get("measurement_cgroup_cleanup_observations"),
            target=target,
            require_success_absence=(
                schema == LAUNCH_RECEIPT_SCHEMA
                and target == "measurement"
                and document.get("success") is True
            ),
        )
    return document


def _require_stream_document(value: object, label: str) -> None:
    if type(value) is not dict or set(value) != {
        "byte_count",
        "sha256",
        "retained_prefix_hex",
        "retained_prefix_truncated",
    }:
        _fail(f"{label} stream observation changed")
    byte_count = _require_nonnegative_int(value["byte_count"], f"{label} bytes")
    _require_sha256(value["sha256"], f"{label} digest")
    prefix = value["retained_prefix_hex"]
    if type(prefix) is not str or re.fullmatch(r"(?:[0-9a-f]{2})*", prefix) is None:
        _fail(f"{label} retained prefix changed")
    if len(prefix) // 2 > CHILD_STREAM_RETAINED_PREFIX_BYTES:
        _fail(f"{label} retained prefix exceeded its cap")
    if value["retained_prefix_truncated"] is not (
        byte_count > len(prefix) // 2
    ):
        _fail(f"{label} truncation claim changed")


def _empty_stream_document() -> dict[str, Any]:
    return {
        "byte_count": 0,
        "sha256": EMPTY_STREAM_SHA256,
        "retained_prefix_hex": "",
        "retained_prefix_truncated": False,
    }


def _require_domain_document_identity(
    document: dict[str, Any],
    *,
    identity_field: str,
    domain: str,
    label: str,
) -> str:
    identity = _require_sha256(document.get(identity_field), f"{label} identity")
    payload = dict(document)
    payload.pop(identity_field, None)
    expected = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + _canonical_json_bytes(payload)
    ).hexdigest()
    if identity != expected:
        _fail(f"{label} registered content identity changed")
    return identity


def _evidence_document_identity(document: object) -> str:
    if type(document) is not dict:
        _fail("success evidence inventory contains a non-object document")
    schema = document.get("schema")
    identity_field = EVIDENCE_IDENTITY_FIELD_BY_SCHEMA.get(schema)
    if identity_field is None:
        _fail("success evidence inventory contains an unregistered schema")
    return _require_sha256(
        document.get(identity_field), "success evidence document identity"
    )


def _schema_counts(documents: list[dict[str, Any]]) -> dict[str, int]:
    return {
        schema: sum(document.get("schema") == schema for document in documents)
        for schema in EVIDENCE_DOCUMENT_TYPE_COUNTS
    }


def _require_success_artifact_population(
    repository_root: Path,
    *,
    expected_terminal_provenance: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Rejoin exact immutable artifacts; this does not replay scientific claims."""

    documents: dict[str, dict[str, Any]] = {}
    raw_by_key: dict[str, bytes] = {}
    facts: dict[str, dict[str, Any]] = {}
    for (
        _artifact_name,
        mapping_key,
        relative_path,
        schema,
        domain,
        identity_field,
        _terminal_prefix,
        exact_fields,
        byte_cap,
    ) in SUCCESS_ARTIFACT_ROWS:
        path = repository_root / relative_path
        raw = _stable_read(path, byte_cap=byte_cap, required_mode=0o400)
        document = _parse_canonical_object(raw, mapping_key)
        if set(document) != exact_fields or not (
            document.get("schema") == schema
            and document.get("schema_version") == "1.0.0"
        ):
            _fail(f"{mapping_key} exact schema or keyset changed")
        _require_domain_document_identity(
            document,
            identity_field=identity_field,
            domain=domain,
            label=mapping_key,
        )
        documents[mapping_key] = document
        raw_by_key[mapping_key] = raw
        facts[mapping_key] = {
            "presence": "REGULAR_FILE",
            "mode": 0o400,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    terminal_raw = _stable_read(
        repository_root / TERMINAL_RELATIVE_PATH,
        byte_cap=SCIENTIFIC_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    terminal = _parse_canonical_object(terminal_raw, "measurement terminal")
    if set(terminal) != TERMINAL_FIELDS or not (
        terminal.get("schema") == TERMINAL_SCHEMA
        and terminal.get("schema_version") == "1.0.0"
        and terminal.get("output_bytes_fixed_point") == len(terminal_raw)
    ):
        _fail("measurement terminal exact schema, keyset, or size changed")
    _require_domain_document_identity(
        terminal,
        identity_field="campaign_measurement_terminal_id",
        domain=TERMINAL_DOMAIN,
        label="measurement terminal",
    )
    expected_provenance_fields = {
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "attempt_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
    }
    if set(expected_terminal_provenance) != expected_provenance_fields or any(
        terminal.get(field) != expected_terminal_provenance[field]
        for field in expected_provenance_fields
    ):
        _fail("measurement terminal authorization or transport provenance changed")
    facts["terminal"] = {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": len(terminal_raw),
        "sha256": hashlib.sha256(terminal_raw).hexdigest(),
    }

    inventory = documents["evidence_inventory"]
    evidence_documents = inventory.get("evidence_documents")
    ordered_evidence_ids = inventory.get("ordered_evidence_document_ids")
    if type(evidence_documents) is not list or type(ordered_evidence_ids) is not list:
        _fail("evidence inventory population schema changed")
    evidence_ids = [_evidence_document_identity(row) for row in evidence_documents]
    if not (
        inventory.get("evidence_document_count") == 328
        and len(evidence_documents) == 328
        and len(ordered_evidence_ids) == 328
        and inventory.get("evidence_document_type_counts")
        == EVIDENCE_DOCUMENT_TYPE_COUNTS
        and _schema_counts(evidence_documents) == EVIDENCE_DOCUMENT_TYPE_COUNTS
        and evidence_ids == sorted(set(evidence_ids))
        and ordered_evidence_ids == evidence_ids
    ):
        _fail("evidence inventory exact denominator, order, or type counts changed")

    execution = documents["execution_closure"]
    execution_matches = [
        row
        for row in evidence_documents
        if row.get("schema") == EXECUTION_CLOSURE_SCHEMA
    ]
    if execution_matches != [execution]:
        _fail("execution closure is not the exact registered inventory document")

    os_bundle = documents["os_receipt"]
    os_documents = os_bundle.get("os_receipt_documents")
    ordered_os_ids = os_bundle.get("ordered_os_receipt_ids")
    if type(os_documents) is not list or type(ordered_os_ids) is not list:
        _fail("OS receipt bundle population schema changed")
    os_ids = [_evidence_document_identity(row) for row in os_documents]
    expected_os_documents = sorted(
        (
            row
            for row in evidence_documents
            if row.get("schema") in OS_EVIDENCE_SCHEMA_COUNTS
        ),
        key=_evidence_document_identity,
    )
    os_counts = {
        schema: sum(row.get("schema") == schema for row in os_documents)
        for schema in OS_EVIDENCE_SCHEMA_COUNTS
    }
    if not (
        os_bundle.get("campaign_evidence_inventory_bundle_id")
        == inventory["campaign_evidence_inventory_bundle_id"]
        and os_bundle.get("os_receipt_document_count") == 12
        and len(os_documents) == 12
        and os_bundle.get("os_receipt_schema_counts") == OS_EVIDENCE_SCHEMA_COUNTS
        and os_counts == OS_EVIDENCE_SCHEMA_COUNTS
        and os_ids == sorted(set(os_ids))
        and ordered_os_ids == os_ids
        and os_documents == expected_os_documents
    ):
        _fail("OS receipt bundle exact inventory subset join changed")

    ledger_closure = documents["ledger_closure"]
    if not (
        ledger_closure.get("evidence_documents") == evidence_documents
        and ledger_closure.get("campaign_evidence_document_count") == 328
        and ledger_closure.get("direct_event_evidence_document_count") == 317
        and ledger_closure.get("support_evidence_document_count") == 11
        and ledger_closure.get("campaign_evidence_document_type_counts")
        == EVIDENCE_DOCUMENT_TYPE_COUNTS
        and ledger_closure.get("event_count") == 625
        and ledger_closure.get("event_evidence_nonnull_count") == 317
        and ledger_closure.get("event_evidence_null_count") == 308
        and ledger_closure.get("max_event_count") == 4_096
        and ledger_closure.get("max_event_byte_count") == 65_536
        and ledger_closure.get("max_ledger_byte_count") == 64 * 1024 * 1024
        and ledger_closure.get("campaign_execution_closure_id")
        == execution["campaign_execution_closure_id"]
    ):
        _fail("ledger closure exact evidence and event denominator join changed")

    common_identity = (
        inventory.get("protocol_id"),
        inventory.get("authorization_id"),
        inventory.get("attempt_id"),
    )
    if any(
        _SHA256.fullmatch(value) is None if type(value) is str else True
        for value in common_identity
    ) or any(
        (
            document.get("protocol_id"),
            document.get("authorization_id"),
            document.get("attempt_id"),
        )
        != common_identity
        for document in (execution, os_bundle, ledger_closure, terminal)
    ):
        _fail("success artifacts do not share one exact protocol authorization attempt")

    for (
        _artifact_name,
        mapping_key,
        _relative_path,
        _schema,
        _domain,
        identity_field,
        terminal_prefix,
        _exact_fields,
        _byte_cap,
    ) in SUCCESS_ARTIFACT_ROWS:
        raw = raw_by_key[mapping_key]
        if not (
            terminal.get(f"{terminal_prefix}_id")
            == documents[mapping_key][identity_field]
            and terminal.get(f"{terminal_prefix}_byte_count") == len(raw)
            and terminal.get(f"{terminal_prefix}_sha256")
            == hashlib.sha256(raw).hexdigest()
        ):
            _fail(f"terminal {mapping_key} identity/byte/SHA join changed")
    if not (
        terminal.get("campaign_measurement_ledger") == ledger_closure
        and terminal.get("os_receipt_documents") == os_documents
        and terminal.get("os_receipt_ids") == os_ids
        and terminal.get("os_receipt_schema_counts") == OS_EVIDENCE_SCHEMA_COUNTS
        and terminal.get("event_count") == 625
        and terminal.get("evidence_document_count") == 328
        and terminal.get("os_receipt_document_count") == 12
        and terminal.get("predecessor_occurrence_authoritative_receipt_count") == 90
        and terminal.get("successor_campaign_authoritative_receipt_count") == 9
        and terminal.get("combined_successor_authoritative_receipt_count") == 99
        and terminal.get("authoritative_receipt_arithmetic_90_plus_9_equals_99")
        is True
        and terminal.get("V180R12R3_CAMPAIGN_COUNTER_CLOSURE_STATUS")
        == "PENDING_INDEPENDENT_REPLAY"
        and terminal.get("COUNTER_COMPLETENESS_GATE")
        == "PENDING_INDEPENDENT_REPLAY"
        and terminal.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and terminal.get("SCALAR_CALIBRATION_GATE") == "NOT_RUN"
        and terminal.get("BREAK_EVEN_GATE") == "NOT_RUN"
        and terminal.get("OFFICIAL_EXECUTION_GATE") == "NOT_RUN"
        and terminal.get("official_execution_allowed") is False
        and terminal.get("independent_verification_present") is False
    ):
        _fail("terminal embedded artifact population or pending gates changed")
    return facts


def _require_successful_measurement_launch(
    repository_root: Path, materialization_terminal_id: str
) -> None:
    attempt = _load_launch_document(
        repository_root / MEASUREMENT_ATTEMPT_RELATIVE_PATH,
        LAUNCH_ATTEMPT_SCHEMA,
        "launch_attempt_id",
    )
    receipt = _load_launch_document(
        repository_root / MEASUREMENT_RECEIPT_RELATIVE_PATH,
        LAUNCH_RECEIPT_SCHEMA,
        "launch_receipt_id",
    )
    materialization_raw = _stable_read(
        repository_root / MATERIALIZATION_TERMINAL_RELATIVE_PATH,
        byte_cap=MATERIALIZATION_TERMINAL_BYTE_CAP,
        required_mode=0o400,
    )
    manifest_raw = _stable_read(
        repository_root / MANIFEST_RELATIVE_PATH,
        byte_cap=MANIFEST_BYTE_CAP,
        required_mode=0o400,
    )
    manifest_document = _parse_canonical_object(
        manifest_raw, "verification predecessor launch manifest"
    )
    frozen_context = _validated_frozen_authorization_context(
        manifest_document.get("frozen_authorization_context")
    )
    expected_child_argv = [
        *ISOLATED_ARGV_PREFIX,
        str(repository_root / BOOTSTRAP_RELATIVE_PATH),
        "measurement",
        str(repository_root),
        str(repository_root / PRELAUNCH_ROOT_RELATIVE_PATH),
        str(repository_root / MANIFEST_RELATIVE_PATH),
    ]
    expected_child_environment = {
        MANIFEST_SHA256_ENV: hashlib.sha256(manifest_raw).hexdigest(),
        "LC_CTYPE": "C.UTF-8",
    }
    if not (
        attempt["target"] == "measurement"
        and attempt["repository_root"] == str(repository_root)
        and attempt["materialization_terminal_id"] == materialization_terminal_id
        and attempt["materialization_terminal_byte_count"]
        == len(materialization_raw)
        and attempt["materialization_terminal_sha256"]
        == hashlib.sha256(materialization_raw).hexdigest()
        and attempt["launch_manifest_sha256"]
        == hashlib.sha256(manifest_raw).hexdigest()
        and attempt["child_argv"] == expected_child_argv
        and attempt["child_environment"] == expected_child_environment
        and attempt["address_space_hard_cap_bytes"]
        == ADDRESS_SPACE_HARD_CAP_BYTES
        and attempt["address_space_cap_applied_before_child_exec"] is True
        and attempt["wall_timeout_seconds"] == WALL_TIMEOUT_SECONDS
        and attempt["attempt_lock_written_before_child_exec"] is True
        and attempt["same_target_identity_rerun_forbidden"] is True
        and attempt["preauthorization_supervision"] is True
        and attempt["campaign_actual_measurement"] is False
        and attempt["scientific_occurrence_started"] is False
        and attempt["authorized_child_measurement_execution_attempted"] is True
        and attempt["authorized_child_measurement_execution_completed"] is False
        and attempt["producer_free_verification_attempted"] is False
        and attempt["producer_free_verification_completed"] is False
    ):
        _fail("verification predecessor launch attempt changed")
    _require_stream_document(receipt["child_stdout"], "measurement child stdout")
    _require_stream_document(receipt["child_stderr"], "measurement child stderr")
    progress = receipt["progress_observations"]
    expected_progress_names = set(_state_paths(repository_root, "measurement"))
    if (
        type(progress) is not dict
        or set(progress) != expected_progress_names
        or not all(type(value) is dict for value in progress.values())
    ):
        _fail("verification predecessor progress schema changed")
    success_artifact_facts = _require_success_artifact_population(
        repository_root,
        expected_terminal_provenance={
            "protocol_id": frozen_context["protocol_id"],
            "authorization_id": frozen_context["authorization_id"],
            "authorization_evidence_id": frozen_context[
                "authorization_evidence_id"
            ],
            "attempt_id": frozen_context["campaign_attempt_id"],
            "prelaunch_materialization_terminal_id": materialization_terminal_id,
            "prelaunch_launch_manifest_sha256": hashlib.sha256(
                manifest_raw
            ).hexdigest(),
            "prelaunch_launch_rule_id": LAUNCH_RULE_ID,
            "measurement_launch_attempt_id": attempt["launch_attempt_id"],
        },
    )
    expected_terminal = success_artifact_facts["terminal"]
    expected_attempt = _fact_for_path(
        repository_root / MEASUREMENT_ATTEMPT_RELATIVE_PATH,
        LAUNCH_ARTIFACT_BYTE_CAP,
    )
    current_runtime_cas = _fact_for_path(
        repository_root / RUNTIME_CAS_ROOT_RELATIVE_PATH,
        SCIENTIFIC_ARTIFACT_BYTE_CAP,
    )
    current_output_root = _fact_for_path(
        repository_root / OUTPUT_ROOT_RELATIVE_PATH,
        SCIENTIFIC_ARTIFACT_BYTE_CAP,
    )
    _validate_launch_deadlines_v180r12r3(
        {
            "monotonic_origin_ns": receipt["monotonic_origin_ns"],
            "hard_deadline_ns": receipt["hard_deadline_ns"],
            "campaign_deadline_ns": receipt["campaign_deadline_ns"],
        }
    )
    _validate_measurement_cgroup_observations(
        receipt["measurement_cgroup_cleanup_observations"],
        target="measurement",
        campaign_attempt_id=frozen_context["campaign_attempt_id"],
        require_success_absence=True,
    )
    if not (
        receipt["target"] == "measurement"
        and receipt["launch_attempt_id"] == attempt["launch_attempt_id"]
        and receipt["return_code"] == 0
        and receipt["timed_out"] is False
        and receipt["same_target_identity_rerun_forbidden"] is True
        and receipt["attempt_lock_preserved"] is True
        and receipt["address_space_hard_cap_bytes"] == ADDRESS_SPACE_HARD_CAP_BYTES
        and receipt["wall_timeout_seconds"] == WALL_TIMEOUT_SECONDS
        and receipt["campaign_cleanup_grace_seconds"]
        == CAMPAIGN_CLEANUP_GRACE_SECONDS
        and receipt["termination_grace_seconds"] == TERMINATION_GRACE_SECONDS
        and receipt["preauthorization_supervision"] is True
        and receipt["campaign_actual_measurement"] is False
        and receipt["authorized_child_measurement_execution_attempted"] is True
        and receipt["authorized_child_measurement_execution_completed"] is True
        and receipt["producer_free_verification_attempted"] is False
        and receipt["producer_free_verification_completed"] is False
        and receipt["child_stdout"] == _empty_stream_document()
        and receipt["child_stderr"] == _empty_stream_document()
        and receipt["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and receipt["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and receipt["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
        and receipt["BREAK_EVEN_GATE"] == "NOT_RUN"
        and receipt["official_execution_allowed"] is False
        and receipt["success"] is True
        and receipt["failure_type"] is None
        and receipt["failure_message"] is None
        and progress["attempt"] == expected_attempt
        and progress["terminal"] == expected_terminal
        and progress["evidence_inventory"]
        == success_artifact_facts["evidence_inventory"]
        and progress["execution_closure"]
        == success_artifact_facts["execution_closure"]
        and progress["os_receipt"] == success_artifact_facts["os_receipt"]
        and progress["ledger_closure"]
        == success_artifact_facts["ledger_closure"]
        and progress["receipt"] == {"presence": "ABSENT"}
        and progress["launch_failure"] == {"presence": "ABSENT"}
        and progress["measurement_failure"] == {"presence": "ABSENT"}
        and progress["verification"] == {"presence": "ABSENT"}
        and progress["verification_failure"] == {"presence": "ABSENT"}
        and progress["retained_replay"] == {"presence": "ABSENT"}
        and progress["runtime_cas"] == {"presence": "ABSENT"}
        and progress["output_root"].get("presence") == "DIRECTORY"
        and current_runtime_cas == {"presence": "ABSENT"}
        and current_output_root.get("presence") == "DIRECTORY"
    ):
        _fail("verification predecessor launch receipt changed")


def _bounded_error(error: BaseException) -> tuple[str, str]:
    try:
        error_type = type.__getattribute__(type(error), "__name__")
    except BaseException:
        error_type = "UNAVAILABLE_EXCEPTION_TYPE"
    try:
        message = str(error)
    except BaseException:
        message = "UNFORMATTABLE_EXCEPTION"
    if type(error_type) is not str:
        error_type = "UNAVAILABLE_EXCEPTION_TYPE"
    if type(message) is not str:
        message = "UNFORMATTABLE_EXCEPTION"
    bounded_type = str.encode(error_type, "utf-8", errors="replace")[:128].decode(
        "utf-8", errors="ignore"
    )
    bounded_message = str.encode(message, "utf-8", errors="replace")[
        :FAILURE_MESSAGE_BYTE_CAP
    ].decode("utf-8", errors="ignore")
    return bounded_type, bounded_message


def _base_traceback(error: BaseException) -> Any:
    try:
        return BaseException.__getattribute__(error, "__traceback__")
    except BaseException:
        return None


def _raise_preserved_primary(
    primary: BaseException,
    traceback_value: Any,
    *,
    secondary: BaseException | None = None,
) -> NoReturn:
    try:
        restored = BaseException.with_traceback(primary, traceback_value)
    except BaseException:
        restored = primary
    if secondary is not None:
        raise restored from secondary
    raise restored


def _attempt_document(
    *,
    target: str,
    repository_root: Path,
    materialization: dict[str, Any],
    materialization_raw: bytes,
    manifest_sha256: str,
    child_argv: list[str],
) -> tuple[dict[str, Any], bytes]:
    payload = {
        "schema": LAUNCH_ATTEMPT_SCHEMA,
        "launch_rule_id": LAUNCH_RULE_ID,
        "target": target,
        "repository_root": str(repository_root),
        "materialization_terminal_id": materialization["materialization_terminal_id"],
        "materialization_terminal_byte_count": len(materialization_raw),
        "materialization_terminal_sha256": hashlib.sha256(materialization_raw).hexdigest(),
        "launch_manifest_sha256": manifest_sha256,
        "child_argv": child_argv,
        "child_environment": {MANIFEST_SHA256_ENV: manifest_sha256, "LC_CTYPE": "C.UTF-8"},
        "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "address_space_cap_applied_before_child_exec": True,
        "wall_timeout_seconds": WALL_TIMEOUT_SECONDS,
        "attempt_lock_written_before_child_exec": True,
        "same_target_identity_rerun_forbidden": True,
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "scientific_occurrence_started": False,
        "authorized_child_measurement_execution_attempted": (
            target == "measurement"
        ),
        "authorized_child_measurement_execution_completed": False,
        "producer_free_verification_attempted": target == "verification",
        "producer_free_verification_completed": False,
    }
    attempt_id = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    document = {**payload, "launch_attempt_id": attempt_id}
    return document, _canonical_json_bytes(document)


def _freeze_launch_deadlines_v180r12r3() -> dict[str, int]:
    """Take the sole post-attempt monotonic origin for both watchdog layers."""

    origin_ns = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    hard_deadline_ns = origin_ns + int(
        WALL_TIMEOUT_SECONDS * NANOSECONDS_PER_SECOND
    )
    campaign_deadline_ns = hard_deadline_ns - int(
        CAMPAIGN_CLEANUP_GRACE_SECONDS * NANOSECONDS_PER_SECOND
    )
    if not (
        type(origin_ns) is int
        and 0 < origin_ns < campaign_deadline_ns < hard_deadline_ns
        and hard_deadline_ns - origin_ns
        == int(WALL_TIMEOUT_SECONDS * NANOSECONDS_PER_SECOND)
        and hard_deadline_ns - campaign_deadline_ns
        == int(CAMPAIGN_CLEANUP_GRACE_SECONDS * NANOSECONDS_PER_SECOND)
    ):
        _fail("shared monotonic launch deadline arithmetic changed")
    return {
        "monotonic_origin_ns": origin_ns,
        "hard_deadline_ns": hard_deadline_ns,
        "campaign_deadline_ns": campaign_deadline_ns,
    }


def _validate_launch_deadlines_v180r12r3(
    value: Mapping[str, Any],
) -> dict[str, int]:
    fields = {
        "monotonic_origin_ns",
        "hard_deadline_ns",
        "campaign_deadline_ns",
    }
    if type(value) is not dict or set(value) != fields:
        _fail("shared monotonic launch deadline schema changed")
    result = {key: value[key] for key in fields}
    if not (
        all(type(item) is int and item > 0 for item in result.values())
        and result["monotonic_origin_ns"] < result["campaign_deadline_ns"]
        < result["hard_deadline_ns"]
        and result["hard_deadline_ns"] - result["monotonic_origin_ns"]
        == int(WALL_TIMEOUT_SECONDS * NANOSECONDS_PER_SECOND)
        and result["hard_deadline_ns"] - result["campaign_deadline_ns"]
        == int(CAMPAIGN_CLEANUP_GRACE_SECONDS * NANOSECONDS_PER_SECOND)
    ):
        _fail("shared monotonic launch deadline values changed")
    return result


def _open_bound_directory_descriptor(
    path_text: object,
    *,
    destination: int,
    access_flags: int,
    expected_device: object,
    expected_inode: object,
    expected_uid: object | None = None,
    expected_gid: object | None = None,
    expected_mode: object | None = None,
    label: str,
) -> int:
    if type(path_text) is not str:
        _fail(f"{label} path changed")
    path = Path(path_text)
    if not path.is_absolute() or str(path) != path_text:
        _fail(f"{label} path changed")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        metadata = os.lstat(current)
        if stat.S_ISLNK(metadata.st_mode):
            _fail(f"{label} path contains a symlink")
    source = os.open(
        path,
        access_flags | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        metadata = os.fstat(source)
        if not (
            stat.S_ISDIR(metadata.st_mode)
            and metadata.st_dev == expected_device
            and metadata.st_ino == expected_inode
            and (expected_uid is None or metadata.st_uid == expected_uid)
            and (expected_gid is None or metadata.st_gid == expected_gid)
            and (
                expected_mode is None
                or stat.S_IMODE(metadata.st_mode) == expected_mode
            )
        ):
            _fail(f"{label} descriptor differs from frozen fact")
        os.dup2(source, destination, inheritable=True)
    finally:
        if source != destination:
            os.close(source)
    return destination


def _seal_external_context_memfd(raw: bytes) -> int:
    if type(raw) is not bytes or not raw or len(raw) > EXTERNAL_LAUNCH_CONTEXT_BYTE_CAP:
        _fail("external launch context exceeds its exact byte cap")
    descriptor = os.memfd_create(
        "v180r12r3-external-launch-context",
        getattr(os, "MFD_CLOEXEC", 0x0001) | getattr(os, "MFD_ALLOW_SEALING", 0x0002),
    )
    read_descriptor = -1
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                _fail("external launch context memfd write made no progress")
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        seals = (
            fcntl.F_SEAL_SEAL
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_WRITE
        )
        fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, seals)
        read_descriptor = os.open(
            f"/proc/self/fd/{descriptor}", os.O_RDONLY | os.O_CLOEXEC
        )
        metadata = os.fstat(read_descriptor)
        if not (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_nlink == 0
            and stat.S_IMODE(metadata.st_mode) == 0o400
            and metadata.st_size == len(raw)
            and fcntl.fcntl(read_descriptor, fcntl.F_GET_SEALS) == seals
        ):
            _fail("sealed external launch context descriptor changed")
        os.dup2(read_descriptor, EXTERNAL_LAUNCH_CONTEXT_FD, inheritable=True)
    finally:
        if read_descriptor >= 0 and read_descriptor != EXTERNAL_LAUNCH_CONTEXT_FD:
            os.close(read_descriptor)
        if descriptor != EXTERNAL_LAUNCH_CONTEXT_FD:
            os.close(descriptor)
    return EXTERNAL_LAUNCH_CONTEXT_FD


def _build_external_launch_context(
    *,
    target: str,
    repository_root: Path,
    materialization: dict[str, Any],
    materialization_raw: bytes,
    manifest_sha256: str,
    frozen_context: dict[str, Any],
    current_attempt: dict[str, Any],
    current_attempt_raw: bytes,
    measurement_attempt: dict[str, Any],
    measurement_attempt_raw: bytes,
    launch_deadlines: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    deadlines = _validate_launch_deadlines_v180r12r3(dict(launch_deadlines))
    context = {
        "schema": EXTERNAL_LAUNCH_CONTEXT_SCHEMA,
        "target": target,
        "actor_role": {"measurement": "OBSERVER", "verification": "VERIFIER"}[target],
        "repository_root": str(repository_root),
        "c_pre_root": str(repository_root / PRELAUNCH_ROOT_RELATIVE_PATH),
        "prereg_commit_id": materialization["git_topology"]["c_pre_commit_id"],
        "prelaunch_materialization_terminal_id": materialization[
            "materialization_terminal_id"
        ],
        "prelaunch_materialization_terminal_byte_count": len(materialization_raw),
        "prelaunch_materialization_terminal_sha256": hashlib.sha256(
            materialization_raw
        ).hexdigest(),
        "prelaunch_launch_manifest_sha256": manifest_sha256,
        "prelaunch_launch_rule_id": LAUNCH_RULE_ID,
        "current_launch_attempt_id": current_attempt["launch_attempt_id"],
        "current_launch_attempt_byte_count": len(current_attempt_raw),
        "current_launch_attempt_sha256": hashlib.sha256(current_attempt_raw).hexdigest(),
        "measurement_launch_attempt_id": measurement_attempt["launch_attempt_id"],
        "measurement_launch_attempt_byte_count": len(measurement_attempt_raw),
        "measurement_launch_attempt_sha256": hashlib.sha256(
            measurement_attempt_raw
        ).hexdigest(),
        "protocol_id": frozen_context["protocol_id"],
        "protocol_byte_count": frozen_context["protocol_byte_count"],
        "protocol_sha256": frozen_context["protocol_sha256"],
        "authorization_id": frozen_context["authorization_id"],
        "authorization_byte_count": frozen_context["authorization_byte_count"],
        "authorization_sha256": frozen_context["authorization_sha256"],
        "authorization_evidence_id": frozen_context["authorization_evidence_id"],
        "authorization_evidence_byte_count": frozen_context[
            "authorization_evidence_byte_count"
        ],
        "authorization_evidence_sha256": frozen_context[
            "authorization_evidence_sha256"
        ],
        "campaign_measurement_execution_slot_id": frozen_context[
            "campaign_measurement_execution_slot_id"
        ],
        "logical_occurrence_id": frozen_context["logical_occurrence_id"],
        "execution_nonce": frozen_context["execution_nonce"],
        "campaign_attempt_id": frozen_context["campaign_attempt_id"],
        "monotonic_origin_ns": deadlines["monotonic_origin_ns"],
        "hard_deadline_ns": deadlines["hard_deadline_ns"],
        "campaign_deadline_ns": deadlines["campaign_deadline_ns"],
        "cgroup_parent_fact": frozen_context["cgroup_parent_fact"],
        "runtime_capability_fact": frozen_context["runtime_capability_fact"],
        "inherited_fd_roles": [list(row) for row in EXTERNAL_FD_ROLE_ROWS[target]],
        "target_payload": (
            {
                "delegated_cgroup_parent_fd": DELEGATED_CGROUP_PARENT_FD,
                "cgroup2_mount_fd": CGROUP2_MOUNT_FD,
            }
            if target == "measurement"
            else {}
        ),
        "one_shot": True,
    }
    if tuple(context) != EXTERNAL_LAUNCH_CONTEXT_FIELDS:
        raise AssertionError("external launch context construction order changed")
    raw = _canonical_json_bytes(context)
    if target == "measurement" and (
        context["current_launch_attempt_id"]
        != context["measurement_launch_attempt_id"]
        or current_attempt_raw != measurement_attempt_raw
    ):
        _fail("measurement current and measurement launch attempts differ")
    return context, raw


def _prepare_external_launch_descriptors(
    *, target: str, context_raw: bytes, frozen_context: dict[str, Any]
) -> tuple[int, ...]:
    descriptors: list[int] = []
    try:
        if target == "measurement":
            fact = frozen_context["cgroup_parent_fact"]
            descriptors.append(
                _open_bound_directory_descriptor(
                    fact["parent_path"],
                    destination=DELEGATED_CGROUP_PARENT_FD,
                    access_flags=os.O_RDONLY,
                    expected_device=fact["parent_device"],
                    expected_inode=fact["parent_inode"],
                    expected_uid=fact["owner_uid"],
                    expected_gid=fact["owner_gid"],
                    expected_mode=fact["mode"],
                    label="delegated cgroup parent",
                )
            )
            descriptors.append(
                _open_bound_directory_descriptor(
                    fact["mount_point"],
                    destination=CGROUP2_MOUNT_FD,
                    access_flags=os.O_PATH,
                    expected_device=fact["mount_device"],
                    expected_inode=fact["mount_inode"],
                    label="cgroup2 mount",
                )
            )
        descriptors.insert(0, _seal_external_context_memfd(context_raw))
        expected = tuple(fd for fd, _role in EXTERNAL_FD_ROLE_ROWS[target])
        if tuple(descriptors) != expected:
            _fail("external inherited descriptor order changed")
        return tuple(descriptors)
    except BaseException:
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise


def _measurement_cgroup_root_name(campaign_attempt_id: object) -> str:
    return "v180r12r3-" + _require_sha256(
        campaign_attempt_id, "measurement cgroup campaign attempt ID"
    )


def _blank_measurement_cgroup_observation(
    *,
    phase: str,
    applicable: bool,
    campaign_attempt_id: str,
    root_state: str,
    ownership_acquired: bool,
) -> dict[str, Any]:
    if phase not in MEASUREMENT_CGROUP_OBSERVATION_PHASES:
        _fail("measurement cgroup observation phase changed")
    root_name = _measurement_cgroup_root_name(campaign_attempt_id)
    return {
        "phase": phase,
        "applicable": applicable,
        "campaign_attempt_id": campaign_attempt_id,
        "root_name": root_name,
        "ownership_acquired": ownership_acquired,
        "root_state": root_state,
        "root_mode": None,
        "root_nlink": None,
        "root_device": None,
        "root_inode": None,
        "root_populated": None,
        "root_process_count": None,
        "supervisor_state": root_state,
        "worker_state": root_state,
        "kill_attempted": False,
        "kill_succeeded": False,
        "wait_empty_attempted": False,
        "wait_empty_succeeded": False,
        "remove_attempted": False,
        "remove_succeeded": False,
        "residual_tree_or_process_possible": root_state not in {
            "ABSENT",
            "NOT_APPLICABLE",
        },
        "error_type": None,
        "error_message": None,
    }


def _initial_measurement_cgroup_observations(
    target: str, campaign_attempt_id: str
) -> list[dict[str, Any]]:
    applicable = target == "measurement"
    state = "NOT_OBSERVED" if applicable else "NOT_APPLICABLE"
    return [
        _blank_measurement_cgroup_observation(
            phase=phase,
            applicable=applicable,
            campaign_attempt_id=campaign_attempt_id,
            root_state=state,
            ownership_acquired=False,
        )
        for phase in MEASUREMENT_CGROUP_OBSERVATION_PHASES
    ]


def _read_cgroup_control_at(directory_fd: int, name: str) -> str:
    if name not in {"cgroup.events", "cgroup.procs"}:
        _fail("launcher cgroup control read name changed")
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=directory_fd,
    )
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(
                descriptor,
                min(4096, CGROUP_CONTROL_BYTE_CAP + 1 - total),
            )
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > CGROUP_CONTROL_BYTE_CAP:
                _fail("launcher cgroup control observation exceeded its cap")
        return b"".join(chunks).decode("ascii")
    finally:
        os.close(descriptor)


def _cgroup_child_state(directory_fd: int, name: str) -> str:
    try:
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return "ABSENT"
    except BaseException:
        return "READ_ERROR"
    return "PRESENT" if stat.S_ISDIR(metadata.st_mode) else "LINKED_OR_NONDIR"


def _set_cgroup_observation_error(
    observation: dict[str, Any], error: BaseException
) -> None:
    error_type, error_message = _bounded_error(error)
    observation["error_type"] = error_type
    observation["error_message"] = error_message
    observation["residual_tree_or_process_possible"] = True


def _observe_measurement_cgroup_root(
    *,
    parent_fd: int,
    campaign_attempt_id: str,
    phase: str,
    ownership_acquired: bool,
) -> dict[str, Any]:
    observation = _blank_measurement_cgroup_observation(
        phase=phase,
        applicable=True,
        campaign_attempt_id=campaign_attempt_id,
        root_state="NOT_OBSERVED",
        ownership_acquired=ownership_acquired,
    )
    root_name = observation["root_name"]
    try:
        metadata = os.stat(
            root_name, dir_fd=parent_fd, follow_symlinks=False
        )
    except FileNotFoundError:
        observation.update(
            {
                "root_state": "ABSENT",
                "supervisor_state": "ABSENT",
                "worker_state": "ABSENT",
                "residual_tree_or_process_possible": False,
            }
        )
        return observation
    except BaseException as error:
        observation.update(
            {
                "root_state": "READ_ERROR",
                "supervisor_state": "READ_ERROR",
                "worker_state": "READ_ERROR",
            }
        )
        _set_cgroup_observation_error(observation, error)
        return observation
    observation.update(
        {
            "root_mode": stat.S_IMODE(metadata.st_mode),
            "root_nlink": metadata.st_nlink,
            "root_device": metadata.st_dev,
            "root_inode": metadata.st_ino,
        }
    )
    if not stat.S_ISDIR(metadata.st_mode):
        observation.update(
            {
                "root_state": "LINKED_OR_NONDIR",
                "supervisor_state": "READ_ERROR",
                "worker_state": "READ_ERROR",
            }
        )
        return observation
    root_fd = -1
    try:
        root_fd = os.open(
            root_name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        reopened = os.fstat(root_fd)
        if (
            reopened.st_mode != metadata.st_mode
            or reopened.st_nlink != metadata.st_nlink
            or reopened.st_dev != metadata.st_dev
            or reopened.st_ino != metadata.st_ino
        ):
            _fail("measurement cgroup root identity drifted during observation")
        events = dict(
            line.split(" ", 1)
            for line in _read_cgroup_control_at(root_fd, "cgroup.events").splitlines()
            if line
        )
        process_lines = tuple(
            line
            for line in _read_cgroup_control_at(root_fd, "cgroup.procs").splitlines()
            if line
        )
        if events.get("populated") not in {"0", "1"}:
            _fail("measurement cgroup populated observation changed")
        observation.update(
            {
                "root_state": "PRESENT",
                "root_populated": int(events["populated"]),
                "root_process_count": len(process_lines),
                "supervisor_state": _cgroup_child_state(root_fd, "SUPERVISOR"),
                "worker_state": _cgroup_child_state(root_fd, "WORKER"),
                "residual_tree_or_process_possible": True,
            }
        )
    except BaseException as error:
        observation.update(
            {
                "root_state": "READ_ERROR",
                "supervisor_state": "READ_ERROR",
                "worker_state": "READ_ERROR",
            }
        )
        _set_cgroup_observation_error(observation, error)
    finally:
        if root_fd >= 0:
            try:
                os.close(root_fd)
            except OSError:
                pass
    return observation


def _validate_measurement_cgroup_observations(
    value: object,
    *,
    target: str,
    campaign_attempt_id: str | None = None,
    require_success_absence: bool = False,
) -> tuple[dict[str, Any], ...]:
    if type(value) is not list or len(value) != 3:
        _fail("measurement cgroup cleanup observation denominator changed")
    rows = tuple(value)
    if tuple(row.get("phase") for row in rows if type(row) is dict) != (
        MEASUREMENT_CGROUP_OBSERVATION_PHASES
    ):
        _fail("measurement cgroup cleanup observation order changed")
    expected_applicable = target == "measurement"
    allowed_states = {
        "NOT_APPLICABLE",
        "NOT_OBSERVED",
        "ABSENT",
        "PRESENT",
        "LINKED_OR_NONDIR",
        "READ_ERROR",
    }
    for row in rows:
        if type(row) is not dict or set(row) != MEASUREMENT_CGROUP_OBSERVATION_FIELDS:
            _fail("measurement cgroup cleanup observation schema changed")
        if (
            row["applicable"] is not expected_applicable
            or type(row["campaign_attempt_id"]) is not str
            or _SHA256.fullmatch(row["campaign_attempt_id"]) is None
            or row["root_name"]
            != _measurement_cgroup_root_name(row["campaign_attempt_id"])
            or type(row["ownership_acquired"]) is not bool
            or row["root_state"] not in allowed_states
            or any(
                type(row[name]) is not bool
                for name in (
                    "kill_attempted",
                    "kill_succeeded",
                    "wait_empty_attempted",
                    "wait_empty_succeeded",
                    "remove_attempted",
                    "remove_succeeded",
                    "residual_tree_or_process_possible",
                )
            )
            or row["kill_succeeded"] and not row["kill_attempted"]
            or row["wait_empty_succeeded"] and not row["wait_empty_attempted"]
            or row["remove_succeeded"] and not row["remove_attempted"]
            or (row["error_type"] is None) is not (row["error_message"] is None)
        ):
            _fail("measurement cgroup cleanup observation value changed")
        for name in (
            "root_mode",
            "root_nlink",
            "root_device",
            "root_inode",
            "root_populated",
            "root_process_count",
        ):
            if row[name] is not None and (type(row[name]) is not int or row[name] < 0):
                _fail("measurement cgroup numeric observation changed")
        if row["root_populated"] not in {None, 0, 1}:
            _fail("measurement cgroup populated value changed")
        if row["supervisor_state"] not in allowed_states or row[
            "worker_state"
        ] not in allowed_states:
            _fail("measurement cgroup leaf observation changed")
        if row["error_type"] is not None and (
            type(row["error_type"]) is not str
            or type(row["error_message"]) is not str
            or len(row["error_type"].encode("utf-8")) > 128
            or len(row["error_message"].encode("utf-8")) > FAILURE_MESSAGE_BYTE_CAP
        ):
            _fail("measurement cgroup typed error observation changed")
        if campaign_attempt_id is not None and row["campaign_attempt_id"] != (
            campaign_attempt_id
        ):
            _fail("measurement cgroup campaign attempt join changed")
        if not expected_applicable and (
            row["root_state"] != "NOT_APPLICABLE"
            or row["ownership_acquired"] is not False
            or row["residual_tree_or_process_possible"] is not False
        ):
            _fail("verification launch claimed measurement cgroup cleanup")
    if require_success_absence and not (
        rows[0]["root_state"] == "ABSENT"
        and rows[0]["ownership_acquired"] is True
        and rows[1]["root_state"] == "ABSENT"
        and rows[1]["kill_attempted"] is False
        and rows[1]["remove_attempted"] is False
        and rows[2]["root_state"] == "ABSENT"
        and rows[2]["residual_tree_or_process_possible"] is False
    ):
        _fail("measurement success cgroup root closure changed")
    return rows


def _write_cgroup_kill(root_fd: int) -> None:
    descriptor = os.open(
        "cgroup.kill",
        os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=root_fd,
    )
    try:
        if os.write(descriptor, b"1") != 1:
            _fail("measurement cgroup.kill made partial progress")
    finally:
        os.close(descriptor)


def _cleanup_owned_measurement_cgroup(
    *,
    parent_fd: int,
    campaign_attempt_id: str,
    hard_deadline_ns: int,
    ownership_acquired: bool,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    def deadline_residual(phase: str) -> dict[str, Any]:
        row = _blank_measurement_cgroup_observation(
            phase=phase,
            applicable=True,
            campaign_attempt_id=campaign_attempt_id,
            root_state="NOT_OBSERVED",
            ownership_acquired=ownership_acquired,
        )
        _set_cgroup_observation_error(
            row,
            V180r12r3PrelaunchLaunchError(
                "measurement cgroup cleanup reached the outer hard deadline"
            ),
        )
        return row

    if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
        return (
            deadline_residual("CLEANUP"),
            deadline_residual("AFTER_CHILD"),
            True,
        )
    cleanup = _observe_measurement_cgroup_root(
        parent_fd=parent_fd,
        campaign_attempt_id=campaign_attempt_id,
        phase="CLEANUP",
        ownership_acquired=ownership_acquired,
    )
    cleanup_required = cleanup["root_state"] != "ABSENT"
    if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
        _set_cgroup_observation_error(
            cleanup,
            V180r12r3PrelaunchLaunchError(
                "measurement cgroup observation reached the outer hard deadline"
            ),
        )
        return cleanup, deadline_residual("AFTER_CHILD"), cleanup_required
    if not cleanup_required or not ownership_acquired:
        after = _observe_measurement_cgroup_root(
            parent_fd=parent_fd,
            campaign_attempt_id=campaign_attempt_id,
            phase="AFTER_CHILD",
            ownership_acquired=ownership_acquired,
        )
        return cleanup, after, cleanup_required
    if cleanup["root_state"] != "PRESENT":
        after = _observe_measurement_cgroup_root(
            parent_fd=parent_fd,
            campaign_attempt_id=campaign_attempt_id,
            phase="AFTER_CHILD",
            ownership_acquired=ownership_acquired,
        )
        return cleanup, after, cleanup_required
    root_name = _measurement_cgroup_root_name(campaign_attempt_id)
    root_fd = -1
    try:
        if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
            _fail("measurement cgroup cleanup reached hard deadline before open")
        root_fd = os.open(
            root_name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        metadata = os.fstat(root_fd)
        if (
            metadata.st_dev != cleanup["root_device"]
            or metadata.st_ino != cleanup["root_inode"]
        ):
            _fail("owned measurement cgroup identity drifted before cleanup")
        if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
            _fail("measurement cgroup cleanup reached hard deadline before kill")
        cleanup["kill_attempted"] = True
        _write_cgroup_kill(root_fd)
        cleanup["kill_succeeded"] = True
        cleanup["wait_empty_attempted"] = True
        while True:
            if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
                break
            events = dict(
                line.split(" ", 1)
                for line in _read_cgroup_control_at(
                    root_fd, "cgroup.events"
                ).splitlines()
                if line
            )
            process_lines = tuple(
                line
                for line in _read_cgroup_control_at(
                    root_fd, "cgroup.procs"
                ).splitlines()
                if line
            )
            if events.get("populated") == "0" and not process_lines:
                cleanup["wait_empty_succeeded"] = True
                break
            if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
                break
            time.sleep(
                min(
                    0.05,
                    max(
                        0,
                        hard_deadline_ns
                        - time.clock_gettime_ns(time.CLOCK_MONOTONIC),
                    )
                    / NANOSECONDS_PER_SECOND,
                )
            )
        if cleanup["wait_empty_succeeded"]:
            if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
                _fail("measurement cgroup cleanup reached hard deadline before rmdir")
            cleanup["remove_attempted"] = True
            for leaf_name in ("SUPERVISOR", "WORKER"):
                if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
                    _fail(
                        "measurement cgroup cleanup reached hard deadline during rmdir"
                    )
                try:
                    leaf = os.stat(
                        leaf_name, dir_fd=root_fd, follow_symlinks=False
                    )
                except FileNotFoundError:
                    continue
                if not stat.S_ISDIR(leaf.st_mode):
                    _fail("owned measurement cgroup leaf became non-directory")
                os.rmdir(leaf_name, dir_fd=root_fd)
            if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
                _fail("measurement cgroup cleanup reached hard deadline before root rmdir")
            current = os.stat(
                root_name, dir_fd=parent_fd, follow_symlinks=False
            )
            if current.st_dev != metadata.st_dev or current.st_ino != metadata.st_ino:
                _fail("owned measurement cgroup identity drifted before rmdir")
            os.rmdir(root_name, dir_fd=parent_fd)
            cleanup["remove_succeeded"] = True
    except BaseException as error:
        _set_cgroup_observation_error(cleanup, error)
    finally:
        if root_fd >= 0:
            try:
                os.close(root_fd)
            except OSError as error:
                _set_cgroup_observation_error(cleanup, error)
    after = (
        deadline_residual("AFTER_CHILD")
        if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns
        else _observe_measurement_cgroup_root(
            parent_fd=parent_fd,
            campaign_attempt_id=campaign_attempt_id,
            phase="AFTER_CHILD",
            ownership_acquired=ownership_acquired,
        )
    )
    cleanup["residual_tree_or_process_possible"] = (
        after["root_state"] != "ABSENT"
    )
    return cleanup, after, cleanup_required


def _child_preexec() -> None:
    os.setsid()
    resource.setrlimit(
        resource.RLIMIT_AS,
        (ADDRESS_SPACE_HARD_CAP_BYTES, ADDRESS_SPACE_HARD_CAP_BYTES),
    )


def _terminate_process_group(
    process: subprocess.Popen[bytes], *, hard_deadline_ns: int
) -> None:
    """Terminate without allowing a group member past the frozen hard cap."""

    if time.clock_gettime_ns(time.CLOCK_MONOTONIC) < hard_deadline_ns:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    while time.clock_gettime_ns(time.CLOCK_MONOTONIC) < hard_deadline_ns:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        remaining_ns = hard_deadline_ns - time.clock_gettime_ns(
            time.CLOCK_MONOTONIC
        )
        if remaining_ns <= 0:
            break
        time.sleep(min(0.05, remaining_ns / NANOSECONDS_PER_SECOND))
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


class _StreamObservation:
    def __init__(self) -> None:
        self.byte_count = 0
        self.sha256 = hashlib.sha256()
        self.prefix = bytearray()

    def add(self, raw: bytes) -> None:
        self.byte_count += len(raw)
        self.sha256.update(raw)
        if len(self.prefix) < CHILD_STREAM_RETAINED_PREFIX_BYTES:
            self.prefix.extend(raw[: CHILD_STREAM_RETAINED_PREFIX_BYTES - len(self.prefix)])
        if self.byte_count > CHILD_STREAM_BYTE_CAP:
            _fail("child diagnostic stream exceeded its byte cap")

    def document(self) -> dict[str, Any]:
        return {
            "byte_count": self.byte_count,
            "sha256": self.sha256.hexdigest(),
            "retained_prefix_hex": bytes(self.prefix).hex(),
            "retained_prefix_truncated": self.byte_count > len(self.prefix),
        }


def _run_child(
    child_argv: list[str],
    child_environment: dict[str, str],
    pass_fds: tuple[int, ...] = (),
    *,
    hard_deadline_ns: int | None = None,
) -> tuple[int, bool, dict[str, Any], dict[str, Any]]:
    if hard_deadline_ns is None:
        hard_deadline_ns = time.clock_gettime_ns(time.CLOCK_MONOTONIC) + int(
            WALL_TIMEOUT_SECONDS * NANOSECONDS_PER_SECOND
        )
    if type(hard_deadline_ns) is not int or hard_deadline_ns <= 0:
        _fail("outer hard deadline changed")
    termination_deadline_ns = hard_deadline_ns - int(
        TERMINATION_GRACE_SECONDS * NANOSECONDS_PER_SECOND
    )
    process = subprocess.Popen(
        child_argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # The final four arguments are target, repository, C_pre root, and
        # manifest.  Git and all relative runner observations are rooted at the
        # exact repository argument.
        cwd=child_argv[-3],
        env=child_environment,
        close_fds=True,
        pass_fds=pass_fds,
        preexec_fn=_child_preexec,
    )
    assert process.stdout is not None and process.stderr is not None
    os.set_blocking(process.stdout.fileno(), False)
    os.set_blocking(process.stderr.fileno(), False)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    observations = {"stdout": _StreamObservation(), "stderr": _StreamObservation()}
    timed_out = False
    termination_started = False
    try:
        while selector.get_map() or process.poll() is None:
            remaining_ns = termination_deadline_ns - time.clock_gettime_ns(
                time.CLOCK_MONOTONIC
            )
            if remaining_ns <= 0 and not termination_started:
                timed_out = True
                termination_started = True
                _terminate_process_group(
                    process, hard_deadline_ns=hard_deadline_ns
                )
            events = (
                selector.select(
                    timeout=max(
                        0.0,
                        min(1.0, remaining_ns / NANOSECONDS_PER_SECOND),
                    )
                )
                if selector.get_map()
                else []
            )
            if (
                not selector.get_map()
                and process.poll() is None
                and remaining_ns > 0
            ):
                time.sleep(
                    min(0.05, remaining_ns / NANOSECONDS_PER_SECOND)
                )
            for key, _mask in events:
                stream = key.fileobj
                try:
                    chunk = os.read(stream.fileno(), 64 * 1024)
                except BlockingIOError:
                    continue
                if chunk:
                    observations[key.data].add(chunk)
                else:
                    selector.unregister(stream)
                    stream.close()
            if (
                termination_started
                and time.clock_gettime_ns(time.CLOCK_MONOTONIC)
                >= hard_deadline_ns
            ):
                # SIGKILL has been issued by _terminate_process_group.  One
                # WNOHANG-backed poll is the complete post-hard reap budget;
                # a residual becomes typed launch failure rather than an
                # unbounded wait or a false liveness claim.
                if process.poll() is None:
                    raise V180r12r3PrelaunchLaunchError(
                        "child remained unreaped after hard-deadline SIGKILL"
                    )
                break
            if timed_out and process.poll() is not None and not selector.get_map():
                break
        return_code = process.poll()
        if return_code is None:
            if timed_out:
                raise V180r12r3PrelaunchLaunchError(
                    "child reap state remained unknown after hard deadline"
                )
            return_code = process.wait()
    except BaseException as primary_error:
        primary_traceback = _base_traceback(primary_error)
        cleanup_errors: list[str] = []
        try:
            _terminate_process_group(
                process, hard_deadline_ns=hard_deadline_ns
            )
        except BaseException as cleanup_error:
            cleanup_errors.append(
                f"terminate:{_bounded_error(cleanup_error)[0]}:"
                f"{_bounded_error(cleanup_error)[1]}"
            )
        try:
            remaining = max(
                0.0,
                (
                    hard_deadline_ns
                    - time.clock_gettime_ns(time.CLOCK_MONOTONIC)
                )
                / NANOSECONDS_PER_SECOND,
            )
            process.wait(timeout=remaining)
        except BaseException as cleanup_error:
            cleanup_errors.append(
                f"wait:{_bounded_error(cleanup_error)[0]}:"
                f"{_bounded_error(cleanup_error)[1]}"
            )
        if cleanup_errors:
            secondary = V180r12r3PrelaunchLaunchError(
                "child cleanup secondary observations: "
                + " | ".join(cleanup_errors)
            )
            _raise_preserved_primary(
                primary_error, primary_traceback, secondary=secondary
            )
        _raise_preserved_primary(primary_error, primary_traceback)
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except BaseException:
                pass
    return (
        return_code,
        timed_out,
        observations["stdout"].document(),
        observations["stderr"].document(),
    )


def _expected_success(
    target: str, progress: dict[str, Any]
) -> bool:
    if target == "measurement":
        return (
            progress["attempt"]["presence"] == "REGULAR_FILE"
            and progress["receipt"]["presence"] == "ABSENT"
            and progress["launch_failure"]["presence"] == "ABSENT"
            and progress["runtime_cas"]["presence"] == "ABSENT"
            and progress["output_root"]["presence"] == "DIRECTORY"
            and progress["terminal"]["presence"] == "REGULAR_FILE"
            and progress["evidence_inventory"]["presence"] == "REGULAR_FILE"
            and progress["execution_closure"]["presence"] == "REGULAR_FILE"
            and progress["os_receipt"]["presence"] == "REGULAR_FILE"
            and progress["ledger_closure"]["presence"] == "REGULAR_FILE"
            and progress["measurement_failure"]["presence"] == "ABSENT"
            and progress["verification"]["presence"] == "ABSENT"
            and progress["verification_failure"]["presence"] == "ABSENT"
            and progress["retained_replay"]["presence"] == "ABSENT"
        )
    return (
        progress["attempt"]["presence"] == "REGULAR_FILE"
        and progress["receipt"]["presence"] == "ABSENT"
        and progress["launch_failure"]["presence"] == "ABSENT"
        and progress["runtime_cas"]["presence"] == "ABSENT"
        and progress["output_root"]["presence"] == "DIRECTORY"
        and progress["terminal"]["presence"] == "REGULAR_FILE"
        and progress["evidence_inventory"]["presence"] == "REGULAR_FILE"
        and progress["execution_closure"]["presence"] == "REGULAR_FILE"
        and progress["os_receipt"]["presence"] == "REGULAR_FILE"
        and progress["ledger_closure"]["presence"] == "REGULAR_FILE"
        and progress["measurement_failure"]["presence"] == "ABSENT"
        and progress["verification"]["presence"] == "REGULAR_FILE"
        and progress["retained_replay"]["presence"] == "REGULAR_FILE"
        and progress["verification_failure"]["presence"] == "ABSENT"
    )


def _terminal_document(
    *,
    schema: str,
    id_key: str,
    target: str,
    attempt: dict[str, Any],
    return_code: int | None,
    timed_out: bool,
    stdout: dict[str, Any],
    stderr: dict[str, Any],
    progress: dict[str, Any],
    error: BaseException | None,
    launch_deadlines: Mapping[str, Any],
    measurement_cgroup_cleanup_observations: list[dict[str, Any]],
) -> tuple[dict[str, Any], bytes]:
    deadlines = _validate_launch_deadlines_v180r12r3(dict(launch_deadlines))
    success = error is None and return_code == 0 and not timed_out
    cgroup_rows = _validate_measurement_cgroup_observations(
        measurement_cgroup_cleanup_observations,
        target=target,
        require_success_absence=(success and target == "measurement"),
    )
    payload: dict[str, Any] = {
        "schema": schema,
        "launch_rule_id": LAUNCH_RULE_ID,
        "launch_attempt_id": attempt["launch_attempt_id"],
        "target": target,
        "return_code": return_code,
        "timed_out": timed_out,
        "child_stdout": stdout,
        "child_stderr": stderr,
        "progress_observations": progress,
        "same_target_identity_rerun_forbidden": True,
        "attempt_lock_preserved": True,
        "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "wall_timeout_seconds": WALL_TIMEOUT_SECONDS,
        "monotonic_origin_ns": deadlines["monotonic_origin_ns"],
        "hard_deadline_ns": deadlines["hard_deadline_ns"],
        "campaign_deadline_ns": deadlines["campaign_deadline_ns"],
        "campaign_cleanup_grace_seconds": CAMPAIGN_CLEANUP_GRACE_SECONDS,
        "termination_grace_seconds": TERMINATION_GRACE_SECONDS,
        "measurement_cgroup_cleanup_observations": [
            dict(row) for row in cgroup_rows
        ],
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "authorized_child_measurement_execution_attempted": (
            target == "measurement"
        ),
        "authorized_child_measurement_execution_completed": (
            target == "measurement" and success
        ),
        "producer_free_verification_attempted": target == "verification",
        "producer_free_verification_completed": (
            target == "verification" and success
        ),
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_execution_allowed": False,
        "success": success,
    }
    if error is None:
        payload["failure_type"] = None
        payload["failure_message"] = None
    else:
        payload["failure_type"], payload["failure_message"] = _bounded_error(error)
    document = {
        **payload,
        id_key: hashlib.sha256(_canonical_json_bytes(payload)).hexdigest(),
    }
    return document, _canonical_json_bytes(document)


def launch_prelaunch_target_v180r12r3(
    target: str,
    repository_root: Path,
    expected_materialization_terminal_sha256: str,
) -> dict[str, Any]:
    _require_rule_identities_frozen()
    if target not in _TARGETS:
        _fail("prelaunch target is not measurement or verification")
    repository_root = _require_root(repository_root)
    expected_materialization_terminal_sha256 = _require_sha256(
        expected_materialization_terminal_sha256,
        "materialization terminal environment digest",
    )
    materialization, materialization_raw = _load_materialization(
        repository_root, expected_materialization_terminal_sha256
    )
    (
        bootstrap,
        _launcher,
        manifest,
        manifest_sha256,
        frozen_context,
    ) = _verify_materialized_files(repository_root, materialization)
    paths = _require_fresh_target_state(
        repository_root,
        target,
        materialization["materialization_terminal_id"],
    )
    child_argv = [
        *ISOLATED_ARGV_PREFIX,
        str(bootstrap),
        target,
        str(repository_root),
        str(repository_root / PRELAUNCH_ROOT_RELATIVE_PATH),
        str(manifest),
    ]
    attempt, attempt_raw = _attempt_document(
        target=target,
        repository_root=repository_root,
        materialization=materialization,
        materialization_raw=materialization_raw,
        manifest_sha256=manifest_sha256,
        child_argv=child_argv,
    )
    return_code: int | None = None
    timed_out = False
    stdout = _StreamObservation().document()
    stderr = _StreamObservation().document()
    attempt_lock_acquired = False
    launch_deadlines: dict[str, int] | None = None
    measurement_cgroup_cleanup_observations = (
        _initial_measurement_cgroup_observations(
            target, frozen_context["campaign_attempt_id"]
        )
    )
    try:
        try:
            _write_once(paths["attempt"], attempt_raw)
        except FileExistsError as error:
            raise V180r12r3PrelaunchLaunchReplayForbidden(
                "target launch attempt lock was acquired concurrently"
            ) from error
        except BaseException:
            attempt_lock_acquired = _lexists(paths["attempt"])
            raise
        attempt_lock_acquired = True
        launch_deadlines = _freeze_launch_deadlines_v180r12r3()
        current_attempt_raw = _stable_read(
            paths["attempt"],
            byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
            required_mode=0o400,
            expected_size=len(attempt_raw),
            expected_sha256=hashlib.sha256(attempt_raw).hexdigest(),
        )
        if current_attempt_raw != attempt_raw:
            _fail("current launch attempt differs from just-created exact bytes")
        if target == "measurement":
            measurement_attempt = attempt
            measurement_attempt_raw = current_attempt_raw
        else:
            measurement_attempt = _load_launch_document(
                repository_root / MEASUREMENT_ATTEMPT_RELATIVE_PATH,
                LAUNCH_ATTEMPT_SCHEMA,
                "launch_attempt_id",
            )
            measurement_attempt_raw = _stable_read(
                repository_root / MEASUREMENT_ATTEMPT_RELATIVE_PATH,
                byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
                required_mode=0o400,
            )
        _external_context, external_context_raw = _build_external_launch_context(
            target=target,
            repository_root=repository_root,
            materialization=materialization,
            materialization_raw=materialization_raw,
            manifest_sha256=manifest_sha256,
            frozen_context=frozen_context,
            current_attempt=attempt,
            current_attempt_raw=current_attempt_raw,
            measurement_attempt=measurement_attempt,
            measurement_attempt_raw=measurement_attempt_raw,
            launch_deadlines=launch_deadlines,
        )
        external_descriptors = _prepare_external_launch_descriptors(
            target=target,
            context_raw=external_context_raw,
            frozen_context=frozen_context,
        )
        measurement_cgroup_cleanup_required = False
        try:
            if target == "measurement":
                before = _observe_measurement_cgroup_root(
                    parent_fd=DELEGATED_CGROUP_PARENT_FD,
                    campaign_attempt_id=frozen_context["campaign_attempt_id"],
                    phase="BEFORE_POPEN",
                    ownership_acquired=False,
                )
                measurement_cgroup_cleanup_observations[0] = before
                if before["root_state"] != "ABSENT":
                    measurement_cgroup_cleanup_observations[1] = (
                        _observe_measurement_cgroup_root(
                            parent_fd=DELEGATED_CGROUP_PARENT_FD,
                            campaign_attempt_id=frozen_context["campaign_attempt_id"],
                            phase="CLEANUP",
                            ownership_acquired=False,
                        )
                    )
                    measurement_cgroup_cleanup_observations[2] = (
                        _observe_measurement_cgroup_root(
                            parent_fd=DELEGATED_CGROUP_PARENT_FD,
                            campaign_attempt_id=frozen_context["campaign_attempt_id"],
                            phase="AFTER_CHILD",
                            ownership_acquired=False,
                        )
                    )
                    _fail(
                        "measurement cgroup root existed before Popen; cleanup "
                        "ownership was not acquired"
                    )
                before["ownership_acquired"] = True
            try:
                return_code, timed_out, stdout, stderr = _run_child(
                    child_argv,
                    {MANIFEST_SHA256_ENV: manifest_sha256, "LC_CTYPE": "C.UTF-8"},
                    external_descriptors,
                    hard_deadline_ns=launch_deadlines["hard_deadline_ns"],
                )
            except BaseException:
                if target == "measurement":
                    cleanup, after, measurement_cgroup_cleanup_required = (
                        _cleanup_owned_measurement_cgroup(
                            parent_fd=DELEGATED_CGROUP_PARENT_FD,
                            campaign_attempt_id=frozen_context["campaign_attempt_id"],
                            hard_deadline_ns=launch_deadlines["hard_deadline_ns"],
                            ownership_acquired=True,
                        )
                    )
                    measurement_cgroup_cleanup_observations[1:] = [cleanup, after]
                raise
            if target == "measurement":
                cleanup, after, measurement_cgroup_cleanup_required = (
                    _cleanup_owned_measurement_cgroup(
                        parent_fd=DELEGATED_CGROUP_PARENT_FD,
                        campaign_attempt_id=frozen_context["campaign_attempt_id"],
                        hard_deadline_ns=launch_deadlines["hard_deadline_ns"],
                        ownership_acquired=True,
                    )
                )
                measurement_cgroup_cleanup_observations[1:] = [cleanup, after]
        finally:
            for descriptor in external_descriptors:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if target == "measurement" and (
            measurement_cgroup_cleanup_required
            or measurement_cgroup_cleanup_observations[2]["root_state"] != "ABSENT"
        ):
            _fail(
                "measurement child did not leave its exact owned cgroup root absent"
            )
        progress = _progress_observations(paths)
        if (
            return_code != 0
            or timed_out
            or stdout != _empty_stream_document()
            or stderr != _empty_stream_document()
            or not _expected_success(target, progress)
        ):
            _fail("source-bound child did not reach its exact durable success state")
        success_artifact_facts = _require_success_artifact_population(
            repository_root,
            expected_terminal_provenance={
                "protocol_id": frozen_context["protocol_id"],
                "authorization_id": frozen_context["authorization_id"],
                "authorization_evidence_id": frozen_context[
                    "authorization_evidence_id"
                ],
                "attempt_id": frozen_context["campaign_attempt_id"],
                "prelaunch_materialization_terminal_id": materialization[
                    "materialization_terminal_id"
                ],
                "prelaunch_launch_manifest_sha256": manifest_sha256,
                "prelaunch_launch_rule_id": LAUNCH_RULE_ID,
                "measurement_launch_attempt_id": measurement_attempt[
                    "launch_attempt_id"
                ],
            },
        )
        if any(
            progress[name] != fact
            for name, fact in success_artifact_facts.items()
        ):
            _fail("source-bound child success artifacts changed during exact readback")
        receipt, receipt_raw = _terminal_document(
            schema=LAUNCH_RECEIPT_SCHEMA,
            id_key="launch_receipt_id",
            target=target,
            attempt=attempt,
            return_code=return_code,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            progress=progress,
            error=None,
            launch_deadlines=launch_deadlines,
            measurement_cgroup_cleanup_observations=(
                measurement_cgroup_cleanup_observations
            ),
        )
        _write_once(paths["receipt"], receipt_raw)
        return receipt
    except BaseException as primary_error:
        if not attempt_lock_acquired:
            raise
        if launch_deadlines is None:
            launch_deadlines = _freeze_launch_deadlines_v180r12r3()
        primary_traceback = _base_traceback(primary_error)
        try:
            failure, failure_raw = _terminal_document(
                schema=LAUNCH_FAILURE_SCHEMA,
                id_key="launch_failure_id",
                target=target,
                attempt=attempt,
                return_code=return_code,
                timed_out=timed_out,
                stdout=stdout,
                stderr=stderr,
                progress=_progress_observations(paths),
                error=primary_error,
                launch_deadlines=launch_deadlines,
                measurement_cgroup_cleanup_observations=(
                    measurement_cgroup_cleanup_observations
                ),
            )
            if not _lexists(paths["launch_failure"]):
                _write_once(paths["launch_failure"], failure_raw)
        except BaseException as secondary_error:
            _raise_preserved_primary(
                primary_error, primary_traceback, secondary=secondary_error
            )
        _raise_preserved_primary(primary_error, primary_traceback)


def _require_launcher_startup(target: str, repository_root: Path) -> str:
    if set(os.environ) != {MATERIALIZATION_TERMINAL_SHA256_ENV, "LC_CTYPE"}:
        _fail("trusted launcher environment is not sanitized")
    if os.environ.get("LC_CTYPE") != "C.UTF-8":
        _fail("trusted launcher locale changed")
    if sys.executable != PYTHON_EXECUTABLE:
        _fail("trusted launcher executable changed")
    flags = {
        "isolated": 1,
        "no_site": 1,
        "no_user_site": 1,
        "ignore_environment": 1,
        "dont_write_bytecode": 1,
    }
    if {name: getattr(sys.flags, name) for name in flags} != flags:
        _fail("trusted launcher Python flags changed")
    if sys.pycache_prefix != PYCACHE_PREFIX or sys.dont_write_bytecode is not True:
        _fail("trusted launcher pycache boundary changed")
    repository_root = _require_root(repository_root)
    if Path.cwd() != repository_root:
        _fail("trusted launcher current working directory changed")
    expected = [
        *ISOLATED_ARGV_PREFIX,
        str(Path(__file__).absolute()),
        target,
        str(repository_root),
    ]
    if sys.orig_argv != expected or sys.argv != expected[len(ISOLATED_ARGV_PREFIX) :]:
        _fail("trusted launcher exact argv changed")
    return _require_sha256(
        os.environ[MATERIALIZATION_TERMINAL_SHA256_ENV],
        "materialization terminal environment digest",
    )


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in _TARGETS:
        _fail("trusted launcher API is target and exact repository root")
    target = sys.argv[1]
    repository_root = Path(sys.argv[2])
    expected = _require_launcher_startup(target, repository_root)
    launch_prelaunch_target_v180r12r3(target, repository_root, expected)


__all__ = (
    "ADDRESS_SPACE_HARD_CAP_BYTES",
    "CHILD_STREAM_BYTE_CAP",
    "EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP",
    "EVIDENCE_INVENTORY_RELATIVE_PATH",
    "EXECUTION_CLOSURE_BYTE_CAP",
    "EXECUTION_CLOSURE_RELATIVE_PATH",
    "EXPECTED_LAUNCH_RULE_ID",
    "EXPECTED_MATERIALIZATION_RULE_ID",
    "EXPECTED_SOURCE_CLOSURE_RULE_ID",
    "LAUNCH_ATTEMPT_SCHEMA",
    "LAUNCH_FAILURE_SCHEMA",
    "LAUNCH_RECEIPT_SCHEMA",
    "LAUNCH_RULE_DOCUMENT",
    "LAUNCH_RULE_ID",
    "MATERIALIZATION_TERMINAL_SHA256_ENV",
    "MEASUREMENT_ATTEMPT_RELATIVE_PATH",
    "MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH",
    "MEASUREMENT_RECEIPT_RELATIVE_PATH",
    "LEDGER_CLOSURE_BYTE_CAP",
    "LEDGER_CLOSURE_RELATIVE_PATH",
    "OS_RECEIPT_BUNDLE_BYTE_CAP",
    "OS_RECEIPT_RELATIVE_PATH",
    "SUCCESS_ARTIFACT_ORDER",
    "SUCCESS_ARTIFACT_ROWS",
    "SUCCESS_DURABLE_WRITE_ORDER",
    "VERIFICATION_ATTEMPT_RELATIVE_PATH",
    "VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH",
    "VERIFICATION_RECEIPT_RELATIVE_PATH",
    "V180r12r3PrelaunchLaunchError",
    "V180r12r3PrelaunchLaunchReplayForbidden",
    "WALL_TIMEOUT_SECONDS",
    "launch_prelaunch_target_v180r12r3",
)


if __name__ == "__main__":
    main()
