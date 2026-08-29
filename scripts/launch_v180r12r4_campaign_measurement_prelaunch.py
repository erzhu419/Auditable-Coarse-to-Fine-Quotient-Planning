#!/usr/bin/python3
"""Launch one source-bound V180r12r4 target under the frozen whole-child cap.

This stdlib-only supervisor is materialized from the preregistration commit.
It validates the retained prelaunch receipt, writes a target-specific attempt
lock before spawning Python, applies RLIMIT_AS before exec, enforces the wall
timeout outside the worker, and writes a scoped terminal outcome: receipt-only
for normal or durably recovered success, failure-only before receipt creation,
or receipt plus typed failure when receipt publication cannot be recovered.
Its work is preauthorization supervision and is never a
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


LAUNCH_RULE_SCHEMA = "acfqp.v180r12r4_prelaunch_launch_rule.v1"
LAUNCH_ATTEMPT_SCHEMA = "acfqp.v180r12r4_prelaunch_launch_attempt.v1"
LAUNCH_RECEIPT_SCHEMA = "acfqp.v180r12r4_prelaunch_launch_receipt.v1"
LAUNCH_FAILURE_SCHEMA = "acfqp.v180r12r4_prelaunch_launch_failure.v1"
SERVICE_LAUNCH_ATTEMPT_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_service_launch_attempt.v1"
)
SERVICE_LAUNCH_RECEIPT_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_service_launch_receipt.v1"
)
SERVICE_LAUNCH_FAILURE_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_service_launch_failure.v1"
)
SERVICE_LAUNCH_ATTEMPT_FIELDS = {
    "schema", "target", "token", "unit_name",
    "materialization_terminal_id", "materialization_terminal_sha256",
    "launch_rule_id", "production_systemd_service_invocation",
    "systemd_run_argv", "systemd_run_environment",
    "pre_attempt_unit_absence_observation",
    "inner_launch_artifact_paths", "monotonic_origin_ns",
    "hard_deadline_ns", "campaign_deadline_ns",
    "attempt_o_excl_before_systemd_run",
    "same_target_identity_rerun_forbidden", "pre_scientific_outer_dispatch",
    "campaign_event_or_evidence_document", "service_launch_attempt_id",
}
SERVICE_LAUNCH_INNER_JOIN_FIELDS = {
    "inner_launch_attempt_fact", "inner_launch_receipt_fact",
    "inner_launch_failure_fact", "inner_launch_attempt_id",
    "inner_launch_terminal_kind", "inner_launch_terminal_id",
    "exact_attempt_terminal_join",
}
SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS = {
    "systemctl_argv", "systemctl_environment", "return_code", "timed_out",
    "stdout", "stderr", "expected_load_state",
    "unit_absent_after_wait_collect",
}
SERVICE_LAUNCH_TERMINAL_COMMON_FIELDS = {
    "schema", "target", "service_launch_attempt_id", "token", "unit_name",
    "production_systemd_service_invocation", "systemd_run_return_code",
    "systemd_run_timed_out", "systemd_run_stdout", "systemd_run_stderr",
    "collected_unit_absence_observation", "inner_launch_attempt_fact",
    "inner_launch_receipt_fact", "inner_launch_failure_fact",
    "inner_launch_attempt_id", "inner_launch_terminal_kind",
    "inner_launch_terminal_id", "exact_attempt_terminal_join",
    "attempt_lock_preserved", "same_target_identity_rerun_forbidden",
    "pre_scientific_outer_dispatch", "campaign_event_or_evidence_document",
    "success", "failure_type", "failure_message",
}
SERVICE_LAUNCH_RECEIPT_FIELDS = {
    "schema", "target", "service_launch_attempt_id", "token", "unit_name",
    "production_systemd_service_invocation", "systemd_run_return_code",
    "systemd_run_timed_out", "systemd_run_stdout", "systemd_run_stderr",
    "collected_unit_absence_observation", "inner_launch_attempt_fact",
    "inner_launch_receipt_fact", "inner_launch_failure_fact",
    "inner_launch_attempt_id", "inner_launch_terminal_kind",
    "inner_launch_terminal_id", "exact_attempt_terminal_join",
    "attempt_lock_preserved", "same_target_identity_rerun_forbidden",
    "pre_scientific_outer_dispatch", "campaign_event_or_evidence_document",
    "success", "failure_type", "failure_message", "service_launch_receipt_id",
}
SERVICE_LAUNCH_FAILURE_FIELDS = {
    "schema", "target", "service_launch_attempt_id", "token", "unit_name",
    "production_systemd_service_invocation", "systemd_run_return_code",
    "systemd_run_timed_out", "systemd_run_stdout", "systemd_run_stderr",
    "collected_unit_absence_observation", "inner_launch_attempt_fact",
    "inner_launch_receipt_fact", "inner_launch_failure_fact",
    "inner_launch_attempt_id", "inner_launch_terminal_kind",
    "inner_launch_terminal_id", "exact_attempt_terminal_join",
    "attempt_lock_preserved", "same_target_identity_rerun_forbidden",
    "pre_scientific_outer_dispatch", "campaign_event_or_evidence_document",
    "success", "failure_type", "failure_message",
    "publication_failure_artifact", "publication_failure_stage",
    "publication_failure_path_created",
    "publication_failure_completed", "publication_failure_observed_state",
    "service_launch_failure_id",
}
MATERIALIZATION_TERMINAL_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_materialization_terminal.v1"
)
EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "e5f6f8aaa6a196011d0a64686fe9df743e995f4e66d14119116870a40d9c0530"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "584a47eec792b577314cbdc3ae8e1e50d44d892c402e48de86369087c7e0bc74"
)
EXPECTED_LAUNCH_RULE_ID = (
    "30f0656ce92e74c2b60e8ba95b11f4833f7ebe89756e5303a8e1aa4322ec4008"
)
SOURCE_CLOSURE_RULE_ID = EXPECTED_SOURCE_CLOSURE_RULE_ID
MATERIALIZATION_RULE_ID = EXPECTED_MATERIALIZATION_RULE_ID

PYTHON_EXECUTABLE = "/usr/bin/python3"
PYCACHE_PREFIX = "/dev/null/v180r12r4"
MANIFEST_SHA256_ENV = "ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256"
MATERIALIZATION_TERMINAL_SHA256_ENV = (
    "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256"
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
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_prelaunch"
)
EXTERNAL_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_external_root.json"
)
BOOTSTRAP_RELATIVE_PATH = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/bootstrap.py"
LAUNCHER_RELATIVE_PATH = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/launcher.py"
MANIFEST_RELATIVE_PATH = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/launch_manifest.json"
MATERIALIZATION_TERMINAL_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MATERIALIZATION_TERMINAL.json"
)
MATERIALIZATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_failure.json"
)
SOURCE_BOOTSTRAP_RELATIVE_PATH = (
    "scripts/bootstrap_v180r12r4_campaign_measurement.py"
)
SOURCE_LAUNCHER_RELATIVE_PATH = (
    "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py"
)
SOURCE_MATERIALIZER_RELATIVE_PATH = (
    "scripts/materialize_v180r12r4_campaign_measurement_prelaunch.py"
)
AUTHORIZATION_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_campaign_measurement_"
    "authorization_evidence_freeze_v180r12r4.py"
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
    "v180r12r4_campaign_measurement_prelaunch_measurement_launch_failure.json"
)
VERIFICATION_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_ATTEMPT.json"
)
VERIFICATION_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_RECEIPT.json"
)
VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_verification_launch_failure.json"
)
MEASUREMENT_SERVICE_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_SERVICE_LAUNCH_ATTEMPT.json"
)
MEASUREMENT_SERVICE_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_SERVICE_LAUNCH_RECEIPT.json"
)
MEASUREMENT_SERVICE_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_measurement_service_launch_failure.json"
)
VERIFICATION_SERVICE_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_SERVICE_LAUNCH_ATTEMPT.json"
)
VERIFICATION_SERVICE_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_SERVICE_LAUNCH_RECEIPT.json"
)
VERIFICATION_SERVICE_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_verification_service_launch_failure.json"
)
PRODUCTION_SERVICE_LAUNCH_ARTIFACT_PATHS = {
    "measurement": {
        "attempt": MEASUREMENT_SERVICE_ATTEMPT_RELATIVE_PATH,
        "receipt": MEASUREMENT_SERVICE_RECEIPT_RELATIVE_PATH,
        "failure": MEASUREMENT_SERVICE_FAILURE_RELATIVE_PATH,
    },
    "verification": {
        "attempt": VERIFICATION_SERVICE_ATTEMPT_RELATIVE_PATH,
        "receipt": VERIFICATION_SERVICE_RECEIPT_RELATIVE_PATH,
        "failure": VERIFICATION_SERVICE_FAILURE_RELATIVE_PATH,
    },
}
PRODUCTION_SERVICE_LAUNCH_MODES = {
    "outer_dispatch": "dispatch",
    "retained_service_entry": "service-entry",
}

RUNTIME_CAS_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_cas"
)
OUTPUT_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement"
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
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_failure.json"
)
PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_pre_attempt_host_conformance.json"
)
PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA = (
    "acfqp.v180r12r4_pre_attempt_host_conformance.v2"
)
VERIFICATION_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification.json"
)
VERIFICATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_verification_failure.json"
)
RETAINED_REPLAY_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_verification_replay.json"
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
PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP = 65_536
EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP = 64 * 1024 * 1024
EXECUTION_CLOSURE_BYTE_CAP = 1 * 1024 * 1024
OS_RECEIPT_BUNDLE_BYTE_CAP = 16 * 1024 * 1024
LEDGER_CLOSURE_BYTE_CAP = 64 * 1024 * 1024
EXTERNAL_LAUNCH_CONTEXT_BYTE_CAP = 2 * 1024 * 1024
EXTERNAL_LAUNCH_CONTEXT_FD = 249
DELEGATED_CGROUP_PARENT_FD = 250
CGROUP2_MOUNT_FD = 251
SOURCE_SYSTEMD_SERVICE_FD = 252
CGROUP_CONTROL_BYTE_CAP = 64 * 1024
CGROUP2_SUPER_MAGIC = 0x63677270
ZERO_ID = "0000000000000000000000000000000000000000000000000000000000000000"
PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN = (
    "acfqp:construction-k7-production-transient-service-token:v180r12r4"
)
PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN = (
    "5bfee9fa85834621b4947c1b68d32e96b7c53e260336d0815fd18bf59522dc72"
)
PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME = (
    "acfqp-v180r12r4-measurement-"
    "5bfee9fa85834621b4947c1b68d32e96b7c53e260336d0815fd18bf59522dc72.service"
)
PRODUCTION_TRANSIENT_SERVICE_SLICE = "app.slice"
MATERIALIZATION_TERMINAL_SHA256_TEMPLATE = (
    "__V180R12R4_MATERIALIZATION_TERMINAL_SHA256__"
)
PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t1.v1"
)
ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA = (
    "acfqp.v180r12r4_atomic_cgroup_birth_preflight_receipt_interface.v1"
)
PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN_INPUT = {
    "failed_predecessor_freeze_id": (
        "89562134029a69da93ce1dda6e9ec70abb238050fda1f530a8c5c2f557b5eb60"
    ),
    "failed_inner_launch_failure_id": (
        "7a1b8496f89378f5b2131a096c17fb9f7ed43ac64b544eacdfb3ea2802a65e82"
    ),
    "failed_outer_service_failure_id": (
        "aa3ee86dee489383a43a868180bd555a21978fc923c106e06e5b017adb4101bc"
    ),
    "repair_scope": "TARGET_AWARE_RUNNER_GIT_PROCESS_CONFORMANCE",
    "purpose": "MEASUREMENT",
}
PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN = (
    "6dadbbfad8eb31dd5cc524f57132952a0c3535fa3751ea55ef9e4cf95f87bb01"
)
PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME = (
    "acfqp-v180r12r4-verification-"
    "6dadbbfad8eb31dd5cc524f57132952a0c3535fa3751ea55ef9e4cf95f87bb01.service"
)
PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN_INPUT = {
    "failed_predecessor_freeze_id": (
        "89562134029a69da93ce1dda6e9ec70abb238050fda1f530a8c5c2f557b5eb60"
    ),
    "failed_inner_launch_failure_id": (
        "7a1b8496f89378f5b2131a096c17fb9f7ed43ac64b544eacdfb3ea2802a65e82"
    ),
    "failed_outer_service_failure_id": (
        "aa3ee86dee489383a43a868180bd555a21978fc923c106e06e5b017adb4101bc"
    ),
    "repair_scope": "TARGET_AWARE_RUNNER_GIT_PROCESS_CONFORMANCE",
    "purpose": "VERIFICATION",
}
PRODUCTION_TRANSIENT_SERVICE_ROWS = {
    "measurement": (
        PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN_INPUT,
        PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN,
        PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME,
    ),
    "verification": (
        PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN_INPUT,
        PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN,
        PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME,
    ),
}
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
    "acfqp.v180r12r4_external_launch_context.v1"
)
FROZEN_AUTHORIZATION_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_frozen_authorization_context.v1"
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
    "cgroup_parent_fact", "runtime_capability_fact",
    "production_systemd_service_invocation", "production_runtime_placement_t1",
    "inherited_fd_roles", "target_payload", "one_shot",
)
EXTERNAL_FD_ROLE_ROWS = {
    "measurement": (
        (249, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"),
        (250, "DELEGATED_CGROUP_PARENT_DIRECTORY"),
        (251, "CGROUP2_MOUNT_DIRECTORY"),
        (252, "SOURCE_SYSTEMD_SERVICE_DIRECTORY"),
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
CGROUP_PARENT_FACT_FIELD_ORDER = (
    "schema", "mount_point", "mount_fstype", "mount_device", "mount_inode",
    "mount_options", "parent_path", "parent_device", "parent_inode",
    "owner_uid", "owner_gid", "mode", "controllers", "subtree_control",
    "cgroup_type", "cgroup_namespace_inode", "cgroup_events_present",
    "memory_events_present", "pids_events_present", "cgroup_kill_present",
    "cgroup_procs_present", "memory_peak_present", "pids_peak_present",
    "self_membership",
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
RUNTIME_CAPABILITY_FACT_FIELD_ORDER = (
    "schema", "machine_architecture", "single_threaded", "clone3_probe_errno",
    "clone3_syscall_recognized", "pidfd_send_signal_probe_errno",
    "pidfd_send_signal_recognized", "execveat_probe_errno",
    "execveat_recognized", "pidfd_wait_present", "landlock_abi", "uid", "gid",
    "effective_capability_mask", "admitted",
)
SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA = (
    "acfqp.v180r12r4_socket_buffer_capability_fact.v1"
)
SOCKET_BUFFER_CAPABILITY_FACT_FIELD_ORDER = (
    "schema", "probe_boundary", "socket_family", "socket_type",
    "endpoint_count", "buffer_request_bytes", "effective_min_bytes",
    "net_core_wmem_max_bytes", "net_core_rmem_max_bytes",
    "endpoint_0_so_sndbuf_bytes", "endpoint_0_so_rcvbuf_bytes",
    "endpoint_1_so_sndbuf_bytes", "endpoint_1_so_rcvbuf_bytes",
)
SOCKET_BUFFER_CAPABILITY_FACT_FIELDS = frozenset(
    SOCKET_BUFFER_CAPABILITY_FACT_FIELD_ORDER
)
SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS = (
    "schema", "probe_boundary", "socket_family", "socket_type",
    "endpoint_count", "buffer_request_bytes", "effective_min_bytes",
)
SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS = (
    "net_core_wmem_max_bytes", "net_core_rmem_max_bytes",
    "endpoint_0_so_sndbuf_bytes", "endpoint_0_so_rcvbuf_bytes",
    "endpoint_1_so_sndbuf_bytes", "endpoint_1_so_rcvbuf_bytes",
)
SOCKET_BUFFER_CAPABILITY_EXPECTED = {
    "schema": SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA,
    "probe_boundary": "PRE_CAMPAIGN_ATTEMPT_O_EXCL",
    "socket_family": "AF_UNIX",
    "socket_type": "SOCK_SEQPACKET|SOCK_CLOEXEC",
    "endpoint_count": 2,
    "buffer_request_bytes": 1_048_576,
    "effective_min_bytes": 2_097_152,
    "net_core_wmem_max_bytes": 1_048_576,
    "net_core_rmem_max_bytes": 1_048_576,
    "endpoint_0_so_sndbuf_bytes": 2_097_152,
    "endpoint_0_so_rcvbuf_bytes": 2_097_152,
    "endpoint_1_so_sndbuf_bytes": 2_097_152,
    "endpoint_1_so_rcvbuf_bytes": 2_097_152,
}
PRE_ATTEMPT_HOST_CONFORMANCE_FIELDS = {
    "schema", "phase", "campaign_attempt_id", "expected", "observed",
    "cgroup_parent_compared_fields", "cgroup_parent_excluded_fields",
    "runtime_capability_compared_fields",
    "socket_buffer_capability_exact_fields",
    "socket_buffer_capability_at_least_fields",
    "mismatch_rows", "mismatch_count",
    "cause", "full_host_conformance", "working_tree_source_conformance_joined",
    "production_unit_ownership_t1_joined",
    "campaign_event_or_counter_record_issued", "campaign_attempt_created",
}
SERVICE_CONTEXT_CAPTURE_SCHEMA = (
    "acfqp.v180r12r4r5_service_context_capture.v1"
)
SERVICE_CONTEXT_CAPTURE_PURPOSE = (
    "BENIGN_PRE_FREEZE_SERVICE_CONTEXT_OBSERVATION_NO_CAMPAIGN_ATTEMPT"
)
SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT = 1_459
SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256 = (
    "53508b200ae3b0279bda887cec804a8dd06f7d800734fe3d760f1712ea866fd3"
)

EVIDENCE_INVENTORY_BUNDLE_SCHEMA = (
    "acfqp.campaign_evidence_inventory_bundle.v180r12r4"
)
EXECUTION_CLOSURE_SCHEMA = "acfqp.campaign_execution_closure.v180r12r4"
OS_RECEIPT_BUNDLE_SCHEMA = "acfqp.campaign_os_receipt_bundle.v180r12r4"
LEDGER_CLOSURE_SCHEMA = "acfqp.campaign_measurement_ledger_closure.v180r12r4"
TERMINAL_SCHEMA = "acfqp.campaign_measurement_terminal.v180r12r4"
EVIDENCE_INVENTORY_BUNDLE_DOMAIN = (
    "acfqp:construction-k7-campaign-evidence-inventory-bundle:v180r12r4"
)
EXECUTION_CLOSURE_DOMAIN = (
    "acfqp:construction-k7-campaign-execution-closure:v180r12r4e"
)
OS_RECEIPT_BUNDLE_DOMAIN = (
    "acfqp:construction-k7-campaign-os-receipt-bundle:v180r12r4"
)
LEDGER_CLOSURE_DOMAIN = (
    "acfqp:construction-k7-campaign-ledger-closure:v180r12r4e"
)
TERMINAL_DOMAIN = (
    "acfqp:construction-k7-campaign-measurement-terminal-bundle:v180r12r4"
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
    "measurement": "scripts/run_v180r12r4_campaign_measurement.py",
    "verification": "scripts/verify_v180r12r4_campaign_measurement.py",
    "supervisor": "scripts/supervise_v180r12r4_campaign_measurement.py",
    "worker": "scripts/work_v180r12r4_campaign_measurement.py",
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
    "schema": "acfqp.v180r12r4_internal_bootstrap_target_contract.v1",
    "target_order": ["supervisor", "worker"],
    "initial_environment_keys": [MANIFEST_SHA256_ENV, "LC_CTYPE"],
    "injected_environment_key": "ACFQP_V180R12R4_PREREG_COMMIT",
    "dynamic_identity_in_argv_or_environment": False,
    "context_schema": "acfqp.v180r12r4_internal_launch_context.v1",
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
        "acfqp.v180r12r4_precompiled_source_bundle.v1"
    ),
    "precompiled_before_campaign_attempt": True,
    "internal_target_reads_working_tree_source": False,
    "precompiled_runner_module_contract": {
        "module_type": "types.ModuleType",
        "target_order": [
            "measurement",
            "verification",
            "supervisor",
            "worker",
        ],
        "target_rows": [
            {
                "target": "measurement",
                "module_name": (
                    "_acfqp_v180r12r4_precompiled_runner_measurement"
                ),
            },
            {
                "target": "verification",
                "module_name": (
                    "_acfqp_v180r12r4_precompiled_runner_verification"
                ),
            },
            {
                "target": "supervisor",
                "module_name": (
                    "_acfqp_v180r12r4_precompiled_runner_supervisor"
                ),
            },
            {
                "target": "worker",
                "module_name": "_acfqp_v180r12r4_precompiled_runner_worker",
            },
        ],
        "exact_metadata_fields": [
            "__name__",
            "__file__",
            "__package__",
            "__cached__",
            "__loader__",
            "__spec__",
        ],
        "registered_before_runner_exec": True,
        "registration_spans_exec_entrypoint_and_postchecks": True,
        "preexisting_registration_fails_before_mutation": True,
        "preexisting_registration_is_preserved": True,
        "replaced_deleted_or_metadata_drifted_registration_fails": True,
        "registration_removed_after_postchecks_on_success_or_failure": True,
        "runner_module_registration_leak_forbidden": True,
        "runner_primary_error_precedes_registration_secondary": True,
    },
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
        "V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS", "COUNTER_COMPLETENESS_GATE",
        "WORKLOAD_ECONOMICS_GATE", "SCALAR_CALIBRATION_GATE", "BREAK_EVEN_GATE",
        "OFFICIAL_EXECUTION_GATE", "v180r13_weight_agnostic_economics_input_ready",
        "official_scalar_cost", "official_N_break_even", "official_execution_allowed",
        "scientific_success_claimed", "output_bytes_fixed_point",
        "campaign_measurement_terminal_id",
    }
)
EVIDENCE_DOCUMENT_TYPE_COUNTS = {
    "acfqp.campaign_attempt_record.v180r12r4": 1,
    "acfqp.campaign_stable_input_snapshot.v180r12r4": 2,
    "acfqp.campaign_io_transfer_receipt.v180r12r4": 8,
    "acfqp.campaign_memfd_stage_receipt.v180r12r4": 2,
    "acfqp.campaign_fd_visibility_receipt.v180r12r4": 4,
    "acfqp.campaign_semantic_operation_receipt.v180r12r4": 297,
    "acfqp.campaign_pidfd_birth_receipt.v180r12r4": 2,
    "acfqp.campaign_pidfd_reap_receipt.v180r12r4": 2,
    "acfqp.campaign_cgroup_topology_receipt.v180r12r4": 1,
    "acfqp.campaign_cgroup_observation_receipt.v180r12r4": 1,
    "acfqp.campaign_replay_subject_receipt.v180r12r4": 1,
    "acfqp.campaign_measurement_subject_result.v180r12r4": 1,
    "acfqp.campaign_subject_commit_receipt.v180r12r4": 1,
    "acfqp.campaign_window_closure_receipt.v180r12r4": 1,
    EXECUTION_CLOSURE_SCHEMA: 1,
    "acfqp.campaign_operation_manifest.v180r12r4": 1,
    "acfqp.campaign_native_zero_source_manifest.v180r12r4": 1,
    "acfqp.campaign_native_zero_import_inventory.v180r12r4": 1,
}
EVIDENCE_IDENTITY_FIELD_BY_SCHEMA = {
    "acfqp.campaign_attempt_record.v180r12r4": "campaign_attempt_record_id",
    "acfqp.campaign_stable_input_snapshot.v180r12r4": "stable_input_snapshot_id",
    "acfqp.campaign_io_transfer_receipt.v180r12r4": "io_transfer_receipt_id",
    "acfqp.campaign_memfd_stage_receipt.v180r12r4": "memfd_stage_receipt_id",
    "acfqp.campaign_fd_visibility_receipt.v180r12r4": "fd_visibility_receipt_id",
    "acfqp.campaign_semantic_operation_receipt.v180r12r4": (
        "semantic_operation_receipt_id"
    ),
    "acfqp.campaign_pidfd_birth_receipt.v180r12r4": "pidfd_birth_receipt_id",
    "acfqp.campaign_pidfd_reap_receipt.v180r12r4": "pidfd_reap_receipt_id",
    "acfqp.campaign_cgroup_topology_receipt.v180r12r4": (
        "cgroup_topology_receipt_id"
    ),
    "acfqp.campaign_cgroup_observation_receipt.v180r12r4": (
        "cgroup_observation_receipt_id"
    ),
    "acfqp.campaign_replay_subject_receipt.v180r12r4": "replay_subject_receipt_id",
    "acfqp.campaign_measurement_subject_result.v180r12r4": "subject_result_id",
    "acfqp.campaign_subject_commit_receipt.v180r12r4": "subject_commit_receipt_id",
    "acfqp.campaign_window_closure_receipt.v180r12r4": "window_closure_receipt_id",
    EXECUTION_CLOSURE_SCHEMA: "campaign_execution_closure_id",
    "acfqp.campaign_operation_manifest.v180r12r4": "campaign_operation_manifest_id",
    "acfqp.campaign_native_zero_source_manifest.v180r12r4": (
        "native_zero_source_manifest_id"
    ),
    "acfqp.campaign_native_zero_import_inventory.v180r12r4": (
        "native_zero_import_inventory_id"
    ),
}
OS_EVIDENCE_SCHEMA_COUNTS = {
    "acfqp.campaign_memfd_stage_receipt.v180r12r4": 2,
    "acfqp.campaign_fd_visibility_receipt.v180r12r4": 4,
    "acfqp.campaign_pidfd_birth_receipt.v180r12r4": 2,
    "acfqp.campaign_pidfd_reap_receipt.v180r12r4": 2,
    "acfqp.campaign_cgroup_topology_receipt.v180r12r4": 1,
    "acfqp.campaign_cgroup_observation_receipt.v180r12r4": 1,
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
    "pre_attempt_host_conformance_relative_path": (
        PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH
    ),
    "pre_attempt_host_conformance_schema": PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA,
    "pre_attempt_host_conformance_byte_cap": (
        PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP
    ),
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
    "measurement_cgroup_root_name_template": "v180r12r4-{campaign_attempt_id}",
    "production_transient_service_token_domain": (
        PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN
    ),
    "production_transient_service_target_rows": [
        {
            "target": "measurement",
            "token_input": PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN_INPUT,
            "token": PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN,
            "unit_name": PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME,
        },
        {
            "target": "verification",
            "token_input": PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN_INPUT,
            "token": PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN,
            "unit_name": PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME,
        },
    ],
    "production_systemd_run_common_option_order": [
        "--user", "--wait", "--collect", "--pipe", "--quiet",
        "--no-ask-password", f"--slice={PRODUCTION_TRANSIENT_SERVICE_SLICE}",
        "--service-type=exec", "--property=Delegate=yes",
        "--property=UMask=0077",
        "--working-directory={repository_root}",
    ],
    "production_systemd_unit_kind": "SERVICE_NOT_SCOPE",
    "production_systemd_slice": PRODUCTION_TRANSIENT_SERVICE_SLICE,
    "production_systemd_service_type": "exec",
    "production_systemd_delegate": True,
    "production_systemd_command_starts_with_absolute_env_i": True,
    "production_systemd_launcher_command_paths_are_absolute": True,
    "production_source_cgroup_is_exact_unit_direct_child_of_app_slice": True,
    "production_runtime_placement_t1_schema": (
        PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
    ),
    "source_systemd_service_fd": SOURCE_SYSTEMD_SERVICE_FD,
    "atomic_cgroup_birth_preflight_receipt_interface_schema": (
        ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA
    ),
    "atomic_cgroup_birth_preflight_receipt_has_zero_authority_pending_audit": True,
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
    "measurement_success_requires_pre_attempt_host_conformance_mode_0400": True,
    "measurement_success_replays_pre_attempt_host_conformance_canonical_"
    "semantics": True,
    "pre_attempt_host_conformance_expected_facts_equal_frozen_context": True,
    "pre_attempt_host_conformance_observed_facts_exact_except_self_membership": (
        True
    ),
    "pre_attempt_host_conformance_self_membership_joins_measurement_t1": True,
    "pre_attempt_host_conformance_mismatch_rows_empty_cause_null_full_true": True,
    "measurement_failure_progress_preserves_pre_attempt_host_conformance": True,
    "verification_predecessor_rejoins_current_exact_four_artifact_bytes": True,
    "verification_predecessor_rejoins_same_pre_attempt_host_conformance_fact": (
        True
    ),
    "pre_attempt_host_conformance_is_campaign_event_or_counter_record": False,
    "attempt_lock_written_before_child_exec": True,
    "attempt_and_terminal_distinguish_launcher_overhead_from_authorized_child_"
    "measurement_or_verification": True,
    "measurement_target_marks_measurement_attempted_at_launch_lock": True,
    "measurement_target_marks_measurement_completed_only_on_exact_success": True,
    "verification_target_marks_verification_attempted_at_launch_lock": True,
    "verification_target_marks_verification_completed_only_on_exact_success": True,
    "partial_attempt_or_receipt_observed_in_typed_failure": True,
    "launch_publication_stages": [
        "BEFORE_PARENT_OPEN",
        "BEFORE_O_EXCL",
        "AFTER_O_EXCL",
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_PARENT_FSYNC",
        "AFTER_READBACK",
    ],
    "launch_publication_states": [
        "ABSENT",
        "PRESENT_PARTIAL_OR_INVALID",
        "PRESENT_EXACT",
    ],
    "inner_launch_attempt_publication_is_tracked_before_parent_open": True,
    "inner_launch_attempt_path_creation_allows_typed_failure": True,
    "inner_exact_receipt_publication_error_requires_file_parent_fsync_readback_"
    "recovery": True,
    "inner_partial_or_unrecoverable_receipt_allows_typed_failure_coexistence": True,
    "inner_receipt_consumers_recover_exact_bytes_and_reject_failure_coexistence": True,
    "inner_launch_failure_partial_publication_preserves_primary": True,
    "service_launch_pre_attempt_exact_unit_absence_is_no_spend_gate": True,
    "service_launch_no_spend_check_to_manager_claim_race_is_typed_failure": True,
    "service_launch_publication_token_precedes_parent_open_and_o_excl": True,
    "service_launch_exact_receipt_publication_error_requires_file_parent_fsync_"
    "readback_recovery": True,
    "service_launch_partial_or_unrecoverable_receipt_allows_typed_failure_"
    "coexistence": True,
    "service_launch_receipt_consumers_recover_exact_bytes_and_reject_failure_"
    "coexistence": True,
    "service_launch_partial_terminal_publication_is_progress_classifiable": True,
    "primary_failure_preserved_when_failure_write_fails": True,
    "concurrent_attempt_lock_loser_is_clean_replay_without_failure_write": True,
    "success_receipt_construction_forbidden_when_prior_launch_failure_exists": True,
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


class V180r12r4PrelaunchLaunchError(RuntimeError):
    """The materialization, launch state, cap, or child terminal changed."""


class V180r12r4PrelaunchLaunchReplayForbidden(V180r12r4PrelaunchLaunchError):
    """The target-specific launch identity already has durable progress."""


class ServiceLaunchPublicationTokenV180R12R4:
    """One retained token spanning launch publication through exact readback."""

    def __init__(self, artifact: str) -> None:
        if artifact not in {
            "LAUNCH_ATTEMPT",
            "LAUNCH_RECEIPT",
            "LAUNCH_FAILURE",
            "SERVICE_LAUNCH_ATTEMPT",
            "SERVICE_LAUNCH_RECEIPT",
            "SERVICE_LAUNCH_FAILURE",
        }:
            raise TypeError("launch publication artifact changed")
        self.artifact = artifact
        self.started = False
        self.path_created = False
        self.completed = False
        self.recovered = False
        self.stage = "BEFORE_PARENT_OPEN"


class V180r12r4DurableWriteError(V180r12r4PrelaunchLaunchError):
    """A tracked O_EXCL publication failed after its exact entry boundary."""

    def __init__(
        self,
        path: Path,
        token: ServiceLaunchPublicationTokenV180R12R4,
    ) -> None:
        super().__init__("tracked launch artifact publication failed")
        self.path = path
        self.artifact = token.artifact
        self.stage = token.stage
        self.path_created = token.path_created
        self.completed = token.completed
        self.recovered = token.recovered
        self.observed_state: str | None = None


def _fail(message: str) -> NoReturn:
    raise V180r12r4PrelaunchLaunchError(message)


def _require_rule_identities_frozen() -> None:
    """Reject the outcome path before any attempt write while IDs are sentinels."""

    for token_input, token, _unit_name in PRODUCTION_TRANSIENT_SERVICE_ROWS.values():
        if hashlib.sha256(
            PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN.encode("ascii")
            + b"\x00"
            + _canonical_json_bytes(token_input)
        ).hexdigest() != token:
            _fail("production transient-service lineage token changed")
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


def _require_source_bound_service_context_capture(
    cgroup_parent_fact: dict[str, Any],
    runtime_capability_fact: dict[str, Any],
) -> None:
    capture = {
        "capture_purpose": SERVICE_CONTEXT_CAPTURE_PURPOSE,
        "cgroup_parent_fact": cgroup_parent_fact,
        "runtime_capability_fact": runtime_capability_fact,
        "schema": SERVICE_CONTEXT_CAPTURE_SCHEMA,
    }
    raw = _canonical_json_bytes(capture) + b"\n"
    membership = cgroup_parent_fact.get("self_membership")
    parent_path = cgroup_parent_fact.get("parent_path")
    mount_point = cgroup_parent_fact.get("mount_point")
    if not (
        len(raw) == SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest()
        == SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256
        and cgroup_parent_fact.get("controllers")
        == ["cpu", "memory", "pids"]
        and cgroup_parent_fact.get("subtree_control")
        == ["cpu", "memory", "pids"]
        and type(membership) is str
        and type(parent_path) is str
        and type(mount_point) is str
        and PurePosixPath(membership.removeprefix("0::")).parent
        == PurePosixPath(parent_path.removeprefix(mount_point))
        and PurePosixPath(membership).name
        == "acfqp-v180r12r4r5-freeze-capture-20260829.service"
    ):
        _fail(
            "frozen facts do not exact-join the source-bound service capture"
        )


def _zero_preflight_receipt_interface() -> dict[str, Any]:
    return {
        "schema": ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA,
        "receipt_id": ZERO_ID,
        "receipt_byte_count": 0,
        "receipt_sha256": ZERO_ID,
        "authority_accepted": False,
        "production_launch_authorized": False,
    }


def _production_systemd_service_invocation(
    repository_root: Path,
    materialization_terminal_sha256: str,
    target: str,
) -> dict[str, Any]:
    digest = _require_sha256(
        materialization_terminal_sha256,
        "production service materialization terminal digest",
    )
    launcher = repository_root / LAUNCHER_RELATIVE_PATH
    if not (
        repository_root.is_absolute()
        and launcher.is_absolute()
        and str(launcher) == str(repository_root / LAUNCHER_RELATIVE_PATH)
    ):
        _fail("production systemd service launcher paths are not absolute")
    if target not in PRODUCTION_TRANSIENT_SERVICE_ROWS:
        _fail("production systemd service target changed")
    token_input, token, unit_name = PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
    command = [
        "/usr/bin/env",
        "-i",
        MATERIALIZATION_TERMINAL_SHA256_ENV + "=" + digest,
        "LC_CTYPE=C.UTF-8",
        *ISOLATED_ARGV_PREFIX,
        str(launcher),
        "service-entry",
        target,
        str(repository_root),
    ]
    argv = [
        "/usr/bin/systemd-run",
        "--user",
        "--wait",
        "--collect",
        "--pipe",
        "--quiet",
        "--no-ask-password",
        "--unit=" + unit_name,
        "--slice=" + PRODUCTION_TRANSIENT_SERVICE_SLICE,
        "--service-type=exec",
        "--property=Delegate=yes",
        "--property=UMask=0077",
        "--working-directory=" + str(repository_root),
        *command,
    ]
    return {
        "schema": "acfqp.v180r12r4_production_systemd_service_invocation.v1",
        "token_domain": PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN,
        "target": target,
        "token_input": dict(token_input),
        "token": token,
        "unit_name": unit_name,
        "unit_kind": "SERVICE_NOT_SCOPE",
        "slice": PRODUCTION_TRANSIENT_SERVICE_SLICE,
        "service_type": "exec",
        "delegate": True,
        "umask": "0077",
        "launcher_command": command,
        "systemd_run_argv": argv,
    }


def _production_systemd_run_argv_template(
    repository_root: Path, target: str
) -> list[str]:
    invocation = _production_systemd_service_invocation(
        repository_root, ZERO_ID, target
    )
    argv = list(invocation["systemd_run_argv"])
    environment_row = MATERIALIZATION_TERMINAL_SHA256_ENV + "=" + ZERO_ID
    expected = MATERIALIZATION_TERMINAL_SHA256_ENV + "=" + (
        MATERIALIZATION_TERMINAL_SHA256_TEMPLATE
    )
    if argv.count(environment_row) != 1:
        _fail("production systemd invocation digest row changed")
    argv[argv.index(environment_row)] = expected
    return argv


def _production_systemd_service_contract() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for target in ("measurement", "verification"):
        token_input, token, unit_name = PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
        systemd_template = _production_systemd_run_argv_template(
            Path("/{repository_root}"), target
        )
        if systemd_template.count("/usr/bin/env") != 1:
            _fail("production systemd launcher command boundary changed")
        command = systemd_template[systemd_template.index("/usr/bin/env") :]
        # Normalize the synthetic absolute placeholder to the protocol-level
        # textual template used before a host root is selected.
        command = [value.replace("/{repository_root}", "{repository_root}") for value in command]
        rows.append(
            {
                "target": target,
                "token_input": dict(token_input),
                "token": token,
                "unit_name": unit_name,
                "outer_dispatch_cwd_template": "{repository_root}",
                "outer_dispatch_argv_template": [
                    "/usr/bin/env", "-i",
                    MATERIALIZATION_TERMINAL_SHA256_ENV + "="
                    + MATERIALIZATION_TERMINAL_SHA256_TEMPLATE,
                    "LC_CTYPE=C.UTF-8", *ISOLATED_ARGV_PREFIX,
                    "{repository_root}/" + LAUNCHER_RELATIVE_PATH,
                    "dispatch", target, "{repository_root}",
                ],
                "launcher_command_template": command,
                "service_working_directory_template": "{repository_root}",
                "systemd_run_argv_template": [
                    "/usr/bin/systemd-run", "--user", "--wait", "--collect",
                    "--pipe", "--quiet", "--no-ask-password",
                    "--unit=" + unit_name,
                    "--slice=" + PRODUCTION_TRANSIENT_SERVICE_SLICE,
                    "--service-type=exec", "--property=Delegate=yes",
                    "--property=UMask=0077",
                    "--working-directory={repository_root}",
                    *command,
                ],
            }
        )
    return {
        "schema": "acfqp.v180r12r4_production_systemd_service_contracts.v1",
        "token_domain": PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN,
        "token_input_fields": [
            "failed_predecessor_freeze_id", "failed_inner_launch_failure_id",
            "failed_outer_service_failure_id", "repair_scope", "purpose",
        ],
        "target_order": ["measurement", "verification"],
        "target_rows": rows,
        "unit_kind": "SERVICE_NOT_SCOPE",
        "slice": PRODUCTION_TRANSIENT_SERVICE_SLICE,
        "service_type": "exec",
        "delegate": True,
        "umask": "0077",
        "systemd_run_executable": "/usr/bin/systemd-run",
        "environment_executable": "/usr/bin/env",
        "materialization_terminal_sha256_template": (
            MATERIALIZATION_TERMINAL_SHA256_TEMPLATE
        ),
        "repository_root_and_launcher_paths_must_be_absolute": True,
        "outer_dispatch_process_cwd_must_equal_repository_root": True,
        "service_working_directory_must_equal_repository_root": True,
        "service_source_cgroup_is_exact_direct_child_of_app_slice": True,
        "active_protocol_authorization_attempt_ids_in_token": False,
        "host_facts_in_token": False,
        "preflight_receipt_interface": _zero_preflight_receipt_interface(),
    }


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
        raise V180r12r4PrelaunchLaunchError("stable read open failed") from error
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
        raise V180r12r4PrelaunchLaunchError(f"{label} is invalid JSON") from error
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
    "production_transient_service_rows",
    "production_service_launch_artifact_paths",
    "production_service_launch_modes",
    "atomic_cgroup_birth_preflight_receipt_interface",
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
    "working_tree_source_conformance",
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
    "v180r12r4_outcome_bytes_accessed",
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
    "atomic_cgroup_birth_preflight_receipt_interface",
    "created_before_v180r12r4_authorized_measurement_execution",
    "v180r12r4_outcome_bytes_accessed",
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
_SOURCE_CONFORMANCE_KEYS = {
    "schema",
    "phase",
    "source_root_count",
    "snapshots",
    "mismatch_count",
    "per_field_mismatches",
    "unit_ownership_evaluated",
    "full_source_conformance",
    "cause",
}
_SOURCE_CONFORMANCE_SNAPSHOT_KEYS = {
    "relative_path",
    "expected",
    "observed_before",
    "observed_after",
    "observed_content",
    "mismatch_fields",
    "conformant",
}
_SOURCE_CONFORMANCE_EXPECTED_KEYS = {
    "file_type",
    "git_mode",
    "mode",
    "st_nlink",
    "binding_kind",
    "byte_count",
    "sha256",
    "git_blob_id",
}
_SOURCE_CONFORMANCE_STAT_KEYS = {
    "file_type",
    "st_dev",
    "st_ino",
    "st_mode",
    "mode",
    "st_nlink",
    "st_uid",
    "st_gid",
    "st_size",
    "st_mtime_ns",
    "st_ctime_ns",
}
_SOURCE_CONFORMANCE_CONTENT_KEYS = {
    "binding_kind",
    "byte_count",
    "sha256",
    "git_blob_id",
    "physical_byte_count",
    "physical_sha256",
    "physical_git_blob_id",
}
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
    "working_tree_source_conformance",
    "source_modules",
    "third_party_source_closure",
    "targets",
    "internal_target_contract",
    "production_systemd_service_contract",
    "production_systemd_run_argv_templates",
    "production_service_launch_artifact_paths",
    "production_service_launch_modes",
    "atomic_cgroup_birth_preflight_receipt_interface",
    "frozen_authorization_context",
    "working_tree_mutation_after_snapshot_in_scope",
}


def _validated_working_tree_source_conformance(
    value: object,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _SOURCE_CONFORMANCE_KEYS:
        _fail("working-tree source conformance schema changed")
    snapshots = value["snapshots"]
    count = value["source_root_count"]
    if not (
        value["schema"]
        == "acfqp.v180r12r4_working_tree_source_conformance_diagnostic.v1"
        and value["phase"] == "BEFORE_PRELAUNCH_OUTPUT_AND_SCIENTIFIC_CAMPAIGN"
        and type(count) is int
        and count > 0
        and type(snapshots) is list
        and len(snapshots) == count
        and value["mismatch_count"] == 0
        and value["per_field_mismatches"] == []
        and value["unit_ownership_evaluated"] is False
        and value["full_source_conformance"] is True
        and value["cause"] is None
    ):
        _fail("working-tree source conformance did not pass")
    paths: list[str] = []
    for index, snapshot in enumerate(snapshots):
        if (
            type(snapshot) is not dict
            or set(snapshot) != _SOURCE_CONFORMANCE_SNAPSHOT_KEYS
            or type(snapshot["expected"]) is not dict
            or set(snapshot["expected"]) != _SOURCE_CONFORMANCE_EXPECTED_KEYS
            or type(snapshot["observed_before"]) is not dict
            or set(snapshot["observed_before"]) != _SOURCE_CONFORMANCE_STAT_KEYS
            or type(snapshot["observed_after"]) is not dict
            or set(snapshot["observed_after"]) != _SOURCE_CONFORMANCE_STAT_KEYS
            or type(snapshot["observed_content"]) is not dict
            or set(snapshot["observed_content"])
            != _SOURCE_CONFORMANCE_CONTENT_KEYS
        ):
            _fail(f"working-tree source snapshot {index} schema changed")
        expected = snapshot["expected"]
        before = snapshot["observed_before"]
        after = snapshot["observed_after"]
        content = snapshot["observed_content"]
        relative = _require_relative(
            snapshot["relative_path"],
            f"working-tree source snapshot {index} path",
        )
        if not (
            before == after
            and snapshot["mismatch_fields"] == []
            and snapshot["conformant"] is True
            and expected["file_type"] == before["file_type"] == "REGULAR_FILE"
            and expected["git_mode"] in {"100644", "100755"}
            and expected["mode"] == before["mode"]
            and expected["st_nlink"] == before["st_nlink"] == 1
            and expected["binding_kind"] == content["binding_kind"]
            and expected["byte_count"] == content["byte_count"]
            and expected["sha256"] == content["sha256"]
            and expected["git_blob_id"] == content["git_blob_id"]
            and content["physical_byte_count"] == before["st_size"]
        ):
            _fail(f"working-tree source snapshot {index} changed")
        _require_sha256(expected["sha256"], "working-tree expected digest")
        _require_object_id(expected["git_blob_id"], "working-tree expected blob")
        _require_sha256(content["physical_sha256"], "working-tree physical digest")
        _require_object_id(
            content["physical_git_blob_id"], "working-tree physical blob"
        )
        paths.append(relative)
    if len(set(paths)) != len(paths):
        _fail("working-tree source snapshot path repeated")
    return value


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
    "production_systemd_service_invocation",
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
    "production_systemd_service_invocation",
    "production_runtime_placement_t1",
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
_LAUNCH_FAILURE_PUBLICATION_KEYS = {
    "publication_failure_artifact",
    "publication_failure_stage",
    "publication_failure_path_created",
    "publication_failure_completed",
    "publication_failure_observed_state",
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
        or cgroup.get("schema") != "acfqp.v180r12r4_cgroup_parent_fact.v1"
        or type(runtime) is not dict
        or set(runtime) != RUNTIME_CAPABILITY_FACT_FIELDS
        or runtime.get("schema")
        != "acfqp.v180r12r4_runtime_capability_fact.v1"
        or runtime.get("admitted") is not True
        or cgroup.get("owner_uid") != runtime.get("uid")
        or cgroup.get("owner_gid") != runtime.get("gid")
        or type(cgroup.get("mode")) is not int
        or cgroup["mode"] & (stat.S_IWUSR | stat.S_IXUSR)
        != (stat.S_IWUSR | stat.S_IXUSR)
    ):
        _fail("frozen authorization cgroup or runtime fact changed")
    _require_source_bound_service_context_capture(cgroup, runtime)
    attempt_payload = {
        "schema": "acfqp.campaign_measurement_attempt.v180r12r4",
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
        b"acfqp:construction-k7-campaign-measurement-attempt:v180r12r4\x00"
        + _canonical_json_bytes(attempt_payload)
    ).hexdigest()
    if value["campaign_attempt_id"] != expected_attempt:
        _fail("frozen campaign attempt six-authority identity changed")
    return value


def _validate_pre_attempt_host_conformance(
    repository_root: Path,
    *,
    frozen_context: Mapping[str, Any],
    expected_source_membership: str | None = None,
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    """Replay the canonical pre-ATTEMPT host fact before accepting success."""

    path = repository_root / PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH
    raw = _stable_read(
        path,
        byte_cap=PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP,
        required_mode=0o400,
    )
    document = _parse_canonical_object(raw, "pre-attempt host conformance")
    expected = document.get("expected")
    observed = document.get("observed")
    compared_parent_fields = [
        field for field in CGROUP_PARENT_FACT_FIELD_ORDER
        if field != "self_membership"
    ]
    if not (
        set(document) == PRE_ATTEMPT_HOST_CONFORMANCE_FIELDS
        and type(expected) is dict
        and set(expected)
        == {
            "cgroup_parent_fact",
            "runtime_capability_fact",
            "socket_buffer_capability",
        }
        and type(observed) is dict
        and set(observed)
        == {
            "cgroup_parent_fact",
            "runtime_capability_fact",
            "socket_buffer_capability",
        }
    ):
        _fail("pre-attempt host conformance schema changed")
    expected_parent = expected["cgroup_parent_fact"]
    expected_runtime = expected["runtime_capability_fact"]
    expected_socket = expected["socket_buffer_capability"]
    observed_parent = observed["cgroup_parent_fact"]
    observed_runtime = observed["runtime_capability_fact"]
    observed_socket = observed["socket_buffer_capability"]
    socket_exact = {
        field: observed_socket.get(field)
        for field in SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
    } if type(observed_socket) is dict else None
    expected_socket_exact = {
        field: SOCKET_BUFFER_CAPABILITY_EXPECTED[field]
        for field in SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
    }
    socket_minimums_met = (
        type(observed_socket) is dict
        and all(
            type(observed_socket.get(field)) is int
            and observed_socket[field] >= SOCKET_BUFFER_CAPABILITY_EXPECTED[field]
            for field in SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
        )
    )
    if not (
        type(expected_parent) is dict
        and set(expected_parent) == CGROUP_PARENT_FACT_FIELDS
        and type(observed_parent) is dict
        and set(observed_parent) == CGROUP_PARENT_FACT_FIELDS
        and type(expected_runtime) is dict
        and set(expected_runtime) == RUNTIME_CAPABILITY_FACT_FIELDS
        and type(observed_runtime) is dict
        and set(observed_runtime) == RUNTIME_CAPABILITY_FACT_FIELDS
        and type(expected_socket) is dict
        and set(expected_socket) == SOCKET_BUFFER_CAPABILITY_FACT_FIELDS
        and type(observed_socket) is dict
        and set(observed_socket) == SOCKET_BUFFER_CAPABILITY_FACT_FIELDS
        and _canonical_json_bytes(expected_parent)
        == _canonical_json_bytes(frozen_context.get("cgroup_parent_fact"))
        and _canonical_json_bytes(expected_runtime)
        == _canonical_json_bytes(frozen_context.get("runtime_capability_fact"))
        and _canonical_json_bytes(
            {field: observed_parent[field] for field in compared_parent_fields}
        )
        == _canonical_json_bytes(
            {field: expected_parent[field] for field in compared_parent_fields}
        )
        and type(observed_parent.get("self_membership")) is str
        and observed_parent["self_membership"].startswith("0::/")
        and (
            expected_source_membership is None
            or observed_parent["self_membership"] == expected_source_membership
        )
        and _canonical_json_bytes(observed_runtime)
        == _canonical_json_bytes(expected_runtime)
        and _canonical_json_bytes(expected_socket)
        == _canonical_json_bytes(SOCKET_BUFFER_CAPABILITY_EXPECTED)
        and _canonical_json_bytes(socket_exact)
        == _canonical_json_bytes(expected_socket_exact)
        and socket_minimums_met
        and document.get("schema") == PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA
        and document.get("phase") == "PRE_CAMPAIGN_ATTEMPT_HOST_CONFORMANCE"
        and document.get("campaign_attempt_id")
        == frozen_context.get("campaign_attempt_id")
        and document.get("cgroup_parent_compared_fields")
        == compared_parent_fields
        and document.get("cgroup_parent_excluded_fields") == ["self_membership"]
        and document.get("runtime_capability_compared_fields")
        == list(RUNTIME_CAPABILITY_FACT_FIELD_ORDER)
        and document.get("socket_buffer_capability_exact_fields")
        == list(SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS)
        and document.get("socket_buffer_capability_at_least_fields")
        == list(SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS)
        and document.get("mismatch_rows") == []
        and type(document.get("mismatch_count")) is int
        and document.get("mismatch_count") == 0
        and document.get("cause") is None
        and document.get("full_host_conformance") is True
        and document.get("working_tree_source_conformance_joined") is False
        and document.get("production_unit_ownership_t1_joined") is False
        and document.get("campaign_event_or_counter_record_issued") is False
        and document.get("campaign_attempt_created") is False
    ):
        _fail("pre-attempt host conformance success semantics changed")
    fact = _fact_for_path(path, PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP)
    if fact != {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }:
        _fail("pre-attempt host conformance raw publication fact changed")
    return raw, document, fact


def _load_materialization(
    repository_root: Path, expected_sha256: str
) -> tuple[dict[str, Any], bytes]:
    if _lexists(repository_root / MATERIALIZATION_FAILURE_RELATIVE_PATH):
        raise V180r12r4PrelaunchLaunchReplayForbidden(
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
        and document["v180r12r4_outcome_bytes_accessed"] is False
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
        and document["production_transient_service_rows"]
        == [
            {
                "target": target,
                "token": PRODUCTION_TRANSIENT_SERVICE_ROWS[target][1],
                "unit_name": PRODUCTION_TRANSIENT_SERVICE_ROWS[target][2],
            }
            for target in ("measurement", "verification")
        ]
        and document["production_service_launch_artifact_paths"]
        == PRODUCTION_SERVICE_LAUNCH_ARTIFACT_PATHS
        and document["production_service_launch_modes"]
        == PRODUCTION_SERVICE_LAUNCH_MODES
        and document["atomic_cgroup_birth_preflight_receipt_interface"]
        == _zero_preflight_receipt_interface()
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
    materialization_source_conformance = (
        _validated_working_tree_source_conformance(
            document["working_tree_source_conformance"]
        )
    )

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
        external["schema"] == "acfqp.v180r12r4_prelaunch_external_root.v1"
        and external["materialization_rule_id"] == MATERIALIZATION_RULE_ID
        and external["source_closure_rule_id"] == SOURCE_CLOSURE_RULE_ID
        and external["repository_root"] == str(repository_root)
        and external["git_directory"] == str(repository_root / ".git")
        and external["created_before_v180r12r4_authorized_measurement_execution"]
        is True
        and external["v180r12r4_outcome_bytes_accessed"] is False
        and external["atomic_cgroup_birth_preflight_receipt_interface"]
        == _zero_preflight_receipt_interface()
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
        == "acfqp.v180r12r4_source_bound_launch_manifest.v1"
        and manifest_document["repository_root"] == str(repository_root)
        and manifest_document["c_pre_root"]
        == str(repository_root / PRELAUNCH_ROOT_RELATIVE_PATH)
        and manifest_document["manifest_relative_path"] == "launch_manifest.json"
        and manifest_document["c_pre_commit_id"]
        == document["git_topology"]["c_pre_commit_id"]
        and manifest_document["working_tree_mutation_after_snapshot_in_scope"]
        is False
        and manifest_document["production_systemd_service_contract"]
        == _production_systemd_service_contract()
        and manifest_document["production_systemd_run_argv_templates"]
        == {
            target: _production_systemd_run_argv_template(
                repository_root, target
            )
            for target in ("measurement", "verification")
        }
        and manifest_document["production_service_launch_artifact_paths"]
        == PRODUCTION_SERVICE_LAUNCH_ARTIFACT_PATHS
        and manifest_document["production_service_launch_modes"]
        == PRODUCTION_SERVICE_LAUNCH_MODES
        and manifest_document[
            "atomic_cgroup_birth_preflight_receipt_interface"
        ]
        == _zero_preflight_receipt_interface()
    ):
        _fail("launch manifest boundary changed")
    manifest_source_conformance = _validated_working_tree_source_conformance(
        manifest_document["working_tree_source_conformance"]
    )
    if manifest_source_conformance != document["working_tree_source_conformance"]:
        _fail("manifest/materialization source conformance join changed")
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
    if [
        snapshot["relative_path"]
        for snapshot in manifest_source_conformance["snapshots"]
    ] != [row.get("relative_path") for row in authorization["facts"]]:
        _fail("manifest source-conformance path join changed")
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
        "host_conformance": (
            repository_root / PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH
        ),
        "verification": repository_root / VERIFICATION_RELATIVE_PATH,
        "verification_failure": repository_root / VERIFICATION_FAILURE_RELATIVE_PATH,
        "retained_replay": repository_root / RETAINED_REPLAY_RELATIVE_PATH,
    }


def _require_fresh_target_state(
    repository_root: Path, target: str, materialization_terminal_id: str
) -> dict[str, Path]:
    paths = _state_paths(repository_root, target)
    if any(_lexists(paths[name]) for name in ("attempt", "receipt", "launch_failure")):
        raise V180r12r4PrelaunchLaunchReplayForbidden(
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
            raise V180r12r4PrelaunchLaunchReplayForbidden(
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
            raise V180r12r4PrelaunchLaunchReplayForbidden(
                "verification launch lacks one successful measurement predecessor"
            )
        _require_successful_measurement_launch(
            repository_root, materialization_terminal_id
        )
        for name in ("verification", "verification_failure", "retained_replay"):
            if _lexists(paths[name]):
                raise V180r12r4PrelaunchLaunchReplayForbidden(
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


def _write_once(
    path: Path,
    raw: bytes,
    *,
    publication_token: ServiceLaunchPublicationTokenV180R12R4 | None = None,
    publication_fault_injector: Any = None,
) -> None:
    if type(raw) is not bytes:
        _fail("write-once launch artifact requires exact bytes")
    if publication_token is not None and not (
        type(publication_token) is ServiceLaunchPublicationTokenV180R12R4
        and publication_token.started
        and not publication_token.path_created
        and not publication_token.completed
        and not publication_token.recovered
        and publication_token.stage == "BEFORE_PARENT_OPEN"
    ):
        _fail("tracked launch publication token changed")
    if publication_fault_injector is not None and not (
        publication_token is not None
        and callable(publication_fault_injector)
    ):
        _fail("launch publication fault injector changed")

    def publication_checkpoint(stage: str) -> None:
        if publication_token is None:
            return
        if stage not in SERVICE_LAUNCH_PUBLICATION_STAGES:
            _fail("launch publication stage changed")
        publication_token.stage = stage
        if publication_fault_injector is not None:
            publication_fault_injector(stage)

    parent_fd = -1
    descriptor = -1
    try:
        publication_checkpoint("BEFORE_PARENT_OPEN")
        parent_fd, name = _open_output_parent(path)
        publication_checkpoint("BEFORE_O_EXCL")
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o400,
            dir_fd=parent_fd,
        )
        if publication_token is not None:
            publication_token.path_created = True
        publication_checkpoint("AFTER_O_EXCL")
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                _fail("write-once launch artifact made no progress")
            view = view[written:]
        publication_checkpoint("AFTER_FULL_WRITE")
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
        publication_checkpoint("AFTER_FILE_FSYNC")
        closing = descriptor
        descriptor = -1
        os.close(closing)
        os.fsync(parent_fd)
        publication_checkpoint("AFTER_PARENT_FSYNC")
        closing = parent_fd
        parent_fd = -1
        os.close(closing)
        _stable_read(
            path,
            byte_cap=max(len(raw), 1),
            required_mode=0o400,
            expected_size=len(raw),
            expected_sha256=hashlib.sha256(raw).hexdigest(),
        )
        publication_checkpoint("AFTER_READBACK")
        if publication_token is not None:
            publication_token.completed = True
    except FileExistsError:
        raise
    except BaseException as error:
        if publication_token is not None:
            raise V180r12r4DurableWriteError(
                path, publication_token
            ) from error
        raise
    finally:
        active_error = sys.exc_info()[0] is not None
        for open_descriptor in (descriptor, parent_fd):
            if open_descriptor >= 0:
                try:
                    os.close(open_descriptor)
                except BaseException:
                    if not active_error:
                        raise


def _recover_exact_receipt_publication(path: Path, expected_raw: bytes) -> None:
    """Establish file+directory durability before accepting an exact receipt."""

    if type(expected_raw) is not bytes:
        _fail("receipt publication recovery requires exact bytes")
    parent_fd = -1
    descriptor = -1
    try:
        parent_fd, name = _open_output_parent(path)
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        before = os.fstat(descriptor)
        named_before = os.stat(
            name, dir_fd=parent_fd, follow_symlinks=False
        )

        def identity(metadata: os.stat_result) -> tuple[int, ...]:
            return (
                metadata.st_dev,
                metadata.st_ino,
                stat.S_IFMT(metadata.st_mode),
                stat.S_IMODE(metadata.st_mode),
                metadata.st_nlink,
                metadata.st_uid,
                metadata.st_gid,
                metadata.st_size,
                metadata.st_mtime_ns,
                metadata.st_ctime_ns,
            )

        if not (
            stat.S_ISREG(before.st_mode)
            and stat.S_IMODE(before.st_mode) == 0o400
            and before.st_nlink == 1
            and before.st_size == len(expected_raw)
            and identity(named_before) == identity(before)
        ):
            _fail("receipt publication recovery metadata changed")
        os.fsync(descriptor)
        def require_exact_fd_bytes() -> None:
            offset = 0
            recovered = bytearray()
            while offset < len(expected_raw):
                chunk = os.pread(
                    descriptor,
                    min(1024 * 1024, len(expected_raw) - offset),
                    offset,
                )
                if not chunk:
                    _fail("receipt publication recovery read ended early")
                recovered.extend(chunk)
                offset += len(chunk)
            if bytes(recovered) != expected_raw:
                _fail("receipt publication recovery exact bytes changed")

        require_exact_fd_bytes()
        after = os.fstat(descriptor)
        named_after = os.stat(
            name, dir_fd=parent_fd, follow_symlinks=False
        )
        if not (
            identity(after) == identity(before)
            and identity(named_after) == identity(before)
        ):
            _fail("receipt publication recovery inode changed")
        os.fsync(parent_fd)
        require_exact_fd_bytes()
        final = os.fstat(descriptor)
        named_final = os.stat(
            name, dir_fd=parent_fd, follow_symlinks=False
        )
        if not (
            identity(final) == identity(before)
            and identity(named_final) == identity(before)
        ):
            _fail("receipt publication recovery inode changed after parent fsync")
        closing = descriptor
        descriptor = -1
        os.close(closing)
        closing = parent_fd
        parent_fd = -1
        os.close(closing)
    finally:
        active_error = sys.exc_info()[0] is not None
        for open_descriptor in (descriptor, parent_fd):
            if open_descriptor >= 0:
                try:
                    os.close(open_descriptor)
                except BaseException:
                    if not active_error:
                        raise


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
        "host_conformance": PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP,
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
    expected_keys = _ATTEMPT_KEYS
    if schema == LAUNCH_RECEIPT_SCHEMA:
        expected_keys = _TERMINAL_KEYS | {id_key}
    elif schema == LAUNCH_FAILURE_SCHEMA:
        expected_keys = (
            _TERMINAL_KEYS | _LAUNCH_FAILURE_PUBLICATION_KEYS | {id_key}
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
        and terminal.get("V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS")
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
    if not (
        _lexists(repository_root / MEASUREMENT_ATTEMPT_RELATIVE_PATH)
        and _lexists(repository_root / MEASUREMENT_RECEIPT_RELATIVE_PATH)
        and not _lexists(
            repository_root / MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
        )
    ):
        _fail("measurement launch receipt/failure terminal coexistence changed")
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
    _recover_exact_receipt_publication(
        repository_root / MEASUREMENT_RECEIPT_RELATIVE_PATH,
        _canonical_json_bytes(receipt),
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
    measurement_placement_t1 = receipt.get("production_runtime_placement_t1")
    if (
        type(measurement_placement_t1) is not dict
        or type(measurement_placement_t1.get("source_membership")) is not str
    ):
        _fail("measurement receipt production T1 source membership changed")
    _host_raw, _host_document, expected_host_conformance = (
        _validate_pre_attempt_host_conformance(
            repository_root,
            frozen_context=frozen_context,
            expected_source_membership=measurement_placement_t1[
                "source_membership"
            ],
        )
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
    _validate_launch_deadlines_v180r12r4(
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
        and progress["host_conformance"] == expected_host_conformance
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
    production_systemd_service_invocation: dict[str, Any],
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
        "production_systemd_service_invocation": (
            production_systemd_service_invocation
        ),
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


def _freeze_launch_deadlines_v180r12r4() -> dict[str, int]:
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


def _validate_launch_deadlines_v180r12r4(
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


def _canonical_fd_path(descriptor: int, label: str) -> str:
    value = os.readlink(f"/proc/self/fd/{descriptor}")
    path = PurePosixPath(value)
    if (
        not path.is_absolute()
        or path.as_posix() != value
        or value.endswith(" (deleted)")
        or any(part in {"", ".", ".."} for part in path.parts[1:])
    ):
        _fail(f"{label} descriptor path changed")
    return value


def _directory_fd_fact(descriptor: int, role: str, access: str) -> dict[str, Any]:
    metadata = os.fstat(descriptor)
    flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
    expected_access = os.O_PATH if access == "O_PATH" else os.O_RDONLY
    access_valid = (
        flags & os.O_PATH == os.O_PATH
        if access == "O_PATH"
        else flags & os.O_ACCMODE == expected_access
    )
    if not stat.S_ISDIR(metadata.st_mode) or not access_valid:
        _fail(f"{role} FD metadata or access changed")
    return {
        "fd": descriptor,
        "role": role,
        "access": access,
        "path": _canonical_fd_path(descriptor, role),
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mode": stat.S_IMODE(metadata.st_mode),
        "owner_uid": metadata.st_uid,
        "owner_gid": metadata.st_gid,
        "nlink": metadata.st_nlink,
    }


def _self_cgroup_membership() -> str:
    raw = Path("/proc/self/cgroup").read_text(encoding="ascii")
    rows = raw.splitlines()
    if len(rows) != 1 or not rows[0].startswith("0::/"):
        _fail("launcher source membership is not one cgroup-v2 row")
    return rows[0]


def _prepare_and_observe_production_runtime_placement_t1(
    *,
    target: str,
    frozen_context: dict[str, Any],
) -> tuple[tuple[int, int, int], dict[str, Any]]:
    """Open FD250/251/252 and seal the pre-child source placement facts."""

    if target not in PRODUCTION_TRANSIENT_SERVICE_ROWS:
        _fail("T1 production placement target changed")
    fact = frozen_context["cgroup_parent_fact"]
    opened: list[int] = []
    try:
        opened.append(
            _open_bound_directory_descriptor(
                fact["parent_path"], destination=DELEGATED_CGROUP_PARENT_FD,
                access_flags=os.O_RDONLY, expected_device=fact["parent_device"],
                expected_inode=fact["parent_inode"], expected_uid=fact["owner_uid"],
                expected_gid=fact["owner_gid"], expected_mode=fact["mode"],
                label="delegated cgroup parent",
            )
        )
        opened.append(
            _open_bound_directory_descriptor(
                fact["mount_point"], destination=CGROUP2_MOUNT_FD,
                access_flags=os.O_PATH, expected_device=fact["mount_device"],
                expected_inode=fact["mount_inode"], label="cgroup2 mount",
            )
        )
        _token_input, token, unit_name = PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
        source = os.open(
            unit_name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=DELEGATED_CGROUP_PARENT_FD,
        )
        try:
            os.dup2(source, SOURCE_SYSTEMD_SERVICE_FD, inheritable=True)
        finally:
            if source != SOURCE_SYSTEMD_SERVICE_FD:
                os.close(source)
        opened.append(SOURCE_SYSTEMD_SERVICE_FD)
        parent_fact = _directory_fd_fact(
            DELEGATED_CGROUP_PARENT_FD,
            "DELEGATED_CGROUP_PARENT_DIRECTORY",
            "O_RDONLY",
        )
        mount_fact = _directory_fd_fact(
            CGROUP2_MOUNT_FD, "CGROUP2_MOUNT_DIRECTORY", "O_PATH"
        )
        service_fact = _directory_fd_fact(
            SOURCE_SYSTEMD_SERVICE_FD,
            "SOURCE_SYSTEMD_SERVICE_DIRECTORY",
            "O_RDONLY",
        )
        expected_service_path = str(Path(fact["parent_path"]) / unit_name)
        membership = _self_cgroup_membership()
        mount_relative_parent = PurePosixPath(fact["parent_path"]).relative_to(
            PurePosixPath(fact["mount_point"])
        )
        expected_membership = "0::/" + (
            mount_relative_parent / unit_name
        ).as_posix()
        pids = tuple(
            int(row)
            for row in _read_cgroup_control_at(
                SOURCE_SYSTEMD_SERVICE_FD, "cgroup.procs"
            ).splitlines()
            if row
        )
        writable = os.open(
            "cgroup.procs",
            os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=DELEGATED_CGROUP_PARENT_FD,
        )
        try:
            writable_metadata = os.fstat(writable)
            writable_flags = fcntl.fcntl(writable, fcntl.F_GETFL)
            if not (
                stat.S_ISREG(writable_metadata.st_mode)
                and writable_flags & os.O_ACCMODE == os.O_WRONLY
            ):
                _fail("delegated app.slice cgroup.procs is not O_WRONLY-openable")
        finally:
            os.close(writable)
        planned_root = _observe_measurement_cgroup_root(
            parent_fd=DELEGATED_CGROUP_PARENT_FD,
            campaign_attempt_id=frozen_context["campaign_attempt_id"],
            phase="BEFORE_POPEN",
            ownership_acquired=False,
        )
        if not (
            PurePosixPath(fact["parent_path"]).name
            == PRODUCTION_TRANSIENT_SERVICE_SLICE
            and service_fact["path"] == expected_service_path
            and membership == expected_membership
            and os.getpid() in pids
            and parent_fact["device"] == fact["parent_device"]
            and parent_fact["inode"] == fact["parent_inode"]
            and mount_fact["device"] == fact["mount_device"]
            and mount_fact["inode"] == fact["mount_inode"]
            and service_fact["device"] == parent_fact["device"]
            and planned_root["root_state"] == "ABSENT"
        ):
            _fail("T1 production source placement or planned-root absence changed")
        return (
            (
                DELEGATED_CGROUP_PARENT_FD,
                CGROUP2_MOUNT_FD,
                SOURCE_SYSTEMD_SERVICE_FD,
            ),
            {
                "schema": PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA,
                "target": target,
                "token": token,
                "unit_name": unit_name,
                "slice": PRODUCTION_TRANSIENT_SERVICE_SLICE,
                "source_membership": membership,
                "expected_source_membership": expected_membership,
                "self_pid": os.getpid(),
                "self_pid_in_source_cgroup_procs": True,
                "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
                "delegated_parent_fd_fact": parent_fact,
                "cgroup2_mount_fd_fact": mount_fact,
                "source_service_fd_fact": service_fact,
                "nearest_common_ancestor_path": fact["parent_path"],
                "nearest_common_ancestor_is_app_slice": True,
                "parent_cgroup_procs_o_wronly_openable": True,
                "planned_measurement_root_observation": planned_root,
                "planned_measurement_root_absent": True,
                "t1_complete_before_child_popen": True,
            },
        )
    except BaseException:
        for descriptor in reversed(opened):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise


def _seal_external_context_memfd(raw: bytes) -> int:
    if type(raw) is not bytes or not raw or len(raw) > EXTERNAL_LAUNCH_CONTEXT_BYTE_CAP:
        _fail("external launch context exceeds its exact byte cap")
    descriptor = os.memfd_create(
        "v180r12r4-external-launch-context",
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
    production_systemd_service_invocation: dict[str, Any],
    production_runtime_placement_t1: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    deadlines = _validate_launch_deadlines_v180r12r4(dict(launch_deadlines))
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
        "production_systemd_service_invocation": (
            production_systemd_service_invocation
        ),
        "production_runtime_placement_t1": production_runtime_placement_t1,
        "inherited_fd_roles": [list(row) for row in EXTERNAL_FD_ROLE_ROWS[target]],
        "target_payload": (
            {
                "delegated_cgroup_parent_fd": DELEGATED_CGROUP_PARENT_FD,
                "cgroup2_mount_fd": CGROUP2_MOUNT_FD,
                "source_systemd_service_fd": SOURCE_SYSTEMD_SERVICE_FD,
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
    *,
    target: str,
    context_raw: bytes,
    placement_descriptors: tuple[int, int, int],
) -> tuple[int, ...]:
    if placement_descriptors != (
        DELEGATED_CGROUP_PARENT_FD,
        CGROUP2_MOUNT_FD,
        SOURCE_SYSTEMD_SERVICE_FD,
    ):
        _fail("T1 placement descriptor inventory changed")
    descriptors: list[int] = list(placement_descriptors)
    try:
        descriptors.insert(0, _seal_external_context_memfd(context_raw))
        if target == "verification":
            for descriptor in placement_descriptors:
                os.close(descriptor)
            descriptors = [EXTERNAL_LAUNCH_CONTEXT_FD]
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
    return "v180r12r4-" + _require_sha256(
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
            V180r12r4PrelaunchLaunchError(
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
            V180r12r4PrelaunchLaunchError(
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
    cwd: Path | None = None,
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
        cwd=str(Path(child_argv[-3]) if cwd is None else cwd),
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
                    raise V180r12r4PrelaunchLaunchError(
                        "child remained unreaped after hard-deadline SIGKILL"
                    )
                break
            if timed_out and process.poll() is not None and not selector.get_map():
                break
        return_code = process.poll()
        if return_code is None:
            if timed_out:
                raise V180r12r4PrelaunchLaunchError(
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
            secondary = V180r12r4PrelaunchLaunchError(
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
            and progress["host_conformance"]["presence"] == "REGULAR_FILE"
            and progress["host_conformance"]["mode"] == 0o400
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
        and progress["host_conformance"]["presence"] == "REGULAR_FILE"
        and progress["host_conformance"]["mode"] == 0o400
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
    production_systemd_service_invocation: dict[str, Any],
    production_runtime_placement_t1: dict[str, Any] | None,
) -> tuple[dict[str, Any], bytes]:
    deadlines = _validate_launch_deadlines_v180r12r4(dict(launch_deadlines))
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
        "production_systemd_service_invocation": (
            production_systemd_service_invocation
        ),
        "production_runtime_placement_t1": production_runtime_placement_t1,
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
    if schema == LAUNCH_FAILURE_SCHEMA:
        publication_error = (
            error
            if isinstance(error, V180r12r4DurableWriteError)
            else None
        )
        if publication_error is not None and (
            publication_error.artifact not in {
                "LAUNCH_ATTEMPT",
                "LAUNCH_RECEIPT",
            }
            or publication_error.stage not in SERVICE_LAUNCH_PUBLICATION_STAGES
            or type(publication_error.path_created) is not bool
            or type(publication_error.completed) is not bool
            or publication_error.completed and not publication_error.path_created
            or publication_error.observed_state
            not in SERVICE_LAUNCH_PUBLICATION_STATES
        ):
            _fail("typed inner launch publication failure changed")
        payload.update(
            {
                "publication_failure_artifact": (
                    None
                    if publication_error is None
                    else publication_error.artifact
                ),
                "publication_failure_stage": (
                    None
                    if publication_error is None
                    else publication_error.stage
                ),
                "publication_failure_path_created": (
                    None
                    if publication_error is None
                    else publication_error.path_created
                ),
                "publication_failure_completed": (
                    None
                    if publication_error is None
                    else publication_error.completed
                ),
                "publication_failure_observed_state": (
                    None
                    if publication_error is None
                    else publication_error.observed_state
                ),
            }
        )
    document = {
        **payload,
        id_key: hashlib.sha256(_canonical_json_bytes(payload)).hexdigest(),
    }
    return document, _canonical_json_bytes(document)


SERVICE_LAUNCH_ATTEMPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-attempt:v180r12r4"
)
SERVICE_LAUNCH_RECEIPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-receipt:v180r12r4"
)
SERVICE_LAUNCH_FAILURE_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-failure:v180r12r4"
)
SYSTEMCTL_EXECUTABLE = "/usr/bin/systemctl"
SERVICE_LAUNCH_PUBLICATION_STATES = (
    "ABSENT",
    "PRESENT_PARTIAL_OR_INVALID",
    "PRESENT_EXACT",
)
SERVICE_LAUNCH_PUBLICATION_STAGES = (
    "BEFORE_PARENT_OPEN",
    "BEFORE_O_EXCL",
    "AFTER_O_EXCL",
    "AFTER_FULL_WRITE",
    "AFTER_FILE_FSYNC",
    "AFTER_PARENT_FSYNC",
    "AFTER_READBACK",
)


def _launch_publication_observation(
    paths: Mapping[str, Path],
) -> dict[str, str]:
    """Classify the retained inner ATTEMPT/RECEIPT/FAILURE namespaces."""

    specifications = {
        "attempt": (
            paths["attempt"], LAUNCH_ATTEMPT_SCHEMA, "launch_attempt_id"
        ),
        "receipt": (
            paths["receipt"], LAUNCH_RECEIPT_SCHEMA, "launch_receipt_id"
        ),
        "failure": (
            paths["launch_failure"],
            LAUNCH_FAILURE_SCHEMA,
            "launch_failure_id",
        ),
    }
    observation: dict[str, str] = {}
    for name, (path, schema, identity_field) in specifications.items():
        if not _lexists(path):
            observation[name] = "ABSENT"
            continue
        try:
            _load_launch_document(path, schema, identity_field)
        except BaseException:
            observation[name] = "PRESENT_PARTIAL_OR_INVALID"
        else:
            observation[name] = "PRESENT_EXACT"
    return observation


def _attach_launch_publication_observation(
    primary: BaseException, observation: Mapping[str, str]
) -> None:
    if not (
        type(observation) is dict
        and set(observation) == {"attempt", "receipt", "failure"}
        and all(
            state in SERVICE_LAUNCH_PUBLICATION_STATES
            for state in observation.values()
        )
    ):
        _fail("inner launch publication observation changed")
    try:
        BaseException.__setattr__(
            primary,
            "launch_publication_observation",
            dict(observation),
        )
    except BaseException:
        pass


def _service_state_paths(repository_root: Path, target: str) -> dict[str, Path]:
    if target not in PRODUCTION_SERVICE_LAUNCH_ARTIFACT_PATHS:
        _fail("production service launch target changed")
    service_rows = PRODUCTION_SERVICE_LAUNCH_ARTIFACT_PATHS[target]
    inner_rows = _TARGETS[target]
    return {
        "service_attempt": repository_root / service_rows["attempt"],
        "service_receipt": repository_root / service_rows["receipt"],
        "service_failure": repository_root / service_rows["failure"],
        "inner_attempt": repository_root / inner_rows["attempt"],
        "inner_receipt": repository_root / inner_rows["receipt"],
        "inner_failure": repository_root / inner_rows["launch_failure"],
    }


def _service_launch_publication_observation(
    repository_root: Path, target: str
) -> dict[str, str]:
    """Classify every outer publication namespace without trusting its JSON."""

    paths = _service_state_paths(repository_root, target)
    specifications = {
        "attempt": (
            paths["service_attempt"],
            SERVICE_LAUNCH_ATTEMPT_SCHEMA,
            SERVICE_LAUNCH_ATTEMPT_FIELDS,
            "service_launch_attempt_id",
            SERVICE_LAUNCH_ATTEMPT_DOMAIN,
        ),
        "receipt": (
            paths["service_receipt"],
            SERVICE_LAUNCH_RECEIPT_SCHEMA,
            SERVICE_LAUNCH_RECEIPT_FIELDS,
            "service_launch_receipt_id",
            SERVICE_LAUNCH_RECEIPT_DOMAIN,
        ),
        "failure": (
            paths["service_failure"],
            SERVICE_LAUNCH_FAILURE_SCHEMA,
            SERVICE_LAUNCH_FAILURE_FIELDS,
            "service_launch_failure_id",
            SERVICE_LAUNCH_FAILURE_DOMAIN,
        ),
    }
    observation: dict[str, str] = {}
    for name, (path, schema, fields, identity_field, domain) in specifications.items():
        if not _lexists(path):
            observation[name] = "ABSENT"
            continue
        try:
            raw = _stable_read(
                path,
                byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
                required_mode=0o400,
            )
            document = _parse_canonical_object(raw, path.name)
            identity = document.get(identity_field)
            payload = dict(document)
            payload.pop(identity_field, None)
            if not (
                set(document) == fields
                and document.get("schema") == schema
                and _require_sha256(identity, path.name + " identity")
                == hashlib.sha256(
                    domain.encode("ascii")
                    + b"\x00"
                    + _canonical_json_bytes(payload)
                ).hexdigest()
            ):
                _fail("service launch publication identity changed")
        except BaseException:
            observation[name] = "PRESENT_PARTIAL_OR_INVALID"
        else:
            observation[name] = "PRESENT_EXACT"
    return observation


def _attach_service_launch_publication_observation(
    primary: BaseException, observation: Mapping[str, str]
) -> None:
    if not (
        type(observation) is dict
        and set(observation) == {"attempt", "receipt", "failure"}
        and all(
            state in SERVICE_LAUNCH_PUBLICATION_STATES
            for state in observation.values()
        )
    ):
        _fail("service launch publication observation changed")
    try:
        BaseException.__setattr__(
            primary,
            "service_launch_publication_observation",
            dict(observation),
        )
    except BaseException:
        pass


def _systemd_client_environment_v180r12r4() -> dict[str, str]:
    uid = os.getuid()
    runtime_root = f"/run/user/{uid}"
    return {
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime_root}/bus",
        "LC_CTYPE": "C.UTF-8",
        "XDG_RUNTIME_DIR": runtime_root,
    }


def _service_launch_attempt_document(
    *,
    target: str,
    materialization: Mapping[str, Any],
    materialization_sha256: str,
    invocation: Mapping[str, Any],
    client_environment: Mapping[str, str],
    deadlines: Mapping[str, int],
    pre_attempt_unit_absence: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    _token_input, token, unit_name = PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
    _require_exact_unit_absence_observation(
        pre_attempt_unit_absence,
        unit_name=unit_name,
        client_environment=client_environment,
        require_absent=True,
    )
    payload = {
        "schema": SERVICE_LAUNCH_ATTEMPT_SCHEMA,
        "target": target,
        "token": token,
        "unit_name": unit_name,
        "materialization_terminal_id": materialization[
            "materialization_terminal_id"
        ],
        "materialization_terminal_sha256": materialization_sha256,
        "launch_rule_id": LAUNCH_RULE_ID,
        "production_systemd_service_invocation": dict(invocation),
        "systemd_run_argv": list(invocation["systemd_run_argv"]),
        "systemd_run_environment": dict(client_environment),
        "pre_attempt_unit_absence_observation": dict(
            pre_attempt_unit_absence
        ),
        "inner_launch_artifact_paths": dict(_TARGETS[target]),
        "monotonic_origin_ns": deadlines["monotonic_origin_ns"],
        "hard_deadline_ns": deadlines["hard_deadline_ns"],
        "campaign_deadline_ns": deadlines["campaign_deadline_ns"],
        "attempt_o_excl_before_systemd_run": True,
        "same_target_identity_rerun_forbidden": True,
        "pre_scientific_outer_dispatch": True,
        "campaign_event_or_evidence_document": False,
    }
    document = {
        **payload,
        "service_launch_attempt_id": hashlib.sha256(
            SERVICE_LAUNCH_ATTEMPT_DOMAIN.encode("ascii")
            + b"\x00"
            + _canonical_json_bytes(payload)
        ).hexdigest(),
    }
    if set(document) != SERVICE_LAUNCH_ATTEMPT_FIELDS:
        _fail("service launch attempt field set changed")
    return document, _canonical_json_bytes(document)


def _collected_unit_absence_observation(
    *,
    repository_root: Path,
    unit_name: str,
    client_environment: dict[str, str],
    hard_deadline_ns: int,
    process_runner: Any,
) -> dict[str, Any]:
    if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= hard_deadline_ns:
        _fail("unit absence observation started after the hard deadline")
    argv = [
        SYSTEMCTL_EXECUTABLE,
        "--user",
        "show",
        "--property=LoadState",
        "--value",
        unit_name,
    ]
    return_code, timed_out, stdout, stderr = process_runner(
        argv,
        client_environment,
        (),
        hard_deadline_ns=hard_deadline_ns,
        cwd=repository_root,
    )
    if type(return_code) is not int or type(timed_out) is not bool:
        _fail("systemctl unit absence process result changed")
    _require_stream_document(stdout, "systemctl stdout")
    _require_stream_document(stderr, "systemctl stderr")
    expected_stdout = b"not-found\n"
    absent = (
        return_code == 0
        and timed_out is False
        and bytes.fromhex(stdout["retained_prefix_hex"]) == expected_stdout
        and stdout["byte_count"] == len(expected_stdout)
        and stdout["sha256"] == hashlib.sha256(expected_stdout).hexdigest()
        and stdout["retained_prefix_truncated"] is False
        and stderr == _empty_stream_document()
    )
    observation = {
        "systemctl_argv": argv,
        "systemctl_environment": dict(client_environment),
        "return_code": return_code,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
        "expected_load_state": "not-found",
        "unit_absent_after_wait_collect": absent,
    }
    if set(observation) != SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS:
        _fail("service unit absence observation field set changed")
    _require_exact_unit_absence_observation(
        observation,
        unit_name=unit_name,
        client_environment=client_environment,
        require_absent=False,
    )
    return observation


def _require_exact_unit_absence_observation(
    value: object,
    *,
    unit_name: str,
    client_environment: Mapping[str, str],
    require_absent: bool,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS:
        _fail("exact service unit absence observation field set changed")
    stdout = value.get("stdout")
    stderr = value.get("stderr")
    _require_stream_document(stdout, "systemctl LoadState stdout")
    _require_stream_document(stderr, "systemctl LoadState stderr")
    expected_stdout = b"not-found\n"
    expected_stdout_document = {
        "byte_count": len(expected_stdout),
        "sha256": hashlib.sha256(expected_stdout).hexdigest(),
        "retained_prefix_hex": expected_stdout.hex(),
        "retained_prefix_truncated": False,
    }
    exact_absence = (
        value.get("systemctl_argv")
        == [
            SYSTEMCTL_EXECUTABLE,
            "--user",
            "show",
            "--property=LoadState",
            "--value",
            unit_name,
        ]
        and value.get("systemctl_environment") == dict(client_environment)
        and value.get("return_code") == 0
        and value.get("timed_out") is False
        and stdout == expected_stdout_document
        and stderr == _empty_stream_document()
        and value.get("expected_load_state") == "not-found"
        and value.get("unit_absent_after_wait_collect") is True
    )
    if require_absent and not exact_absence:
        _fail("exact service unit absence observation did not prove absence")
    if value.get("unit_absent_after_wait_collect") is not exact_absence:
        _fail("service unit absence result disagrees with its exact subprocess facts")
    return dict(value)


def _inner_launch_join_observation(
    repository_root: Path,
    target: str,
    *,
    materialization_terminal_id: str | None = None,
) -> dict[str, Any]:
    paths = _service_state_paths(repository_root, target)
    attempt_fact = _fact_for_path(paths["inner_attempt"], LAUNCH_ARTIFACT_BYTE_CAP)
    receipt_fact = _fact_for_path(paths["inner_receipt"], LAUNCH_ARTIFACT_BYTE_CAP)
    failure_fact = _fact_for_path(paths["inner_failure"], LAUNCH_ARTIFACT_BYTE_CAP)
    attempt_id: str | None = None
    terminal_id: str | None = None
    terminal_kind = "ABSENT"
    exact_join = False
    if attempt_fact.get("presence") == "REGULAR_FILE":
        attempt = _load_launch_document(
            paths["inner_attempt"], LAUNCH_ATTEMPT_SCHEMA, "launch_attempt_id"
        )
        attempt_id = attempt["launch_attempt_id"]
        if (
            receipt_fact.get("presence") == "REGULAR_FILE"
            and failure_fact.get("presence") == "ABSENT"
        ):
            terminal = _load_launch_document(
                paths["inner_receipt"], LAUNCH_RECEIPT_SCHEMA, "launch_receipt_id"
            )
            _recover_exact_receipt_publication(
                paths["inner_receipt"], _canonical_json_bytes(terminal)
            )
            terminal_id = terminal["launch_receipt_id"]
            terminal_kind = "RECEIPT"
            base_join = (
                terminal["launch_attempt_id"] == attempt_id
                and terminal["target"] == target
                and terminal["success"] is True
            )
            if base_join and materialization_terminal_id is not None:
                _require_successful_measurement_launch(
                    repository_root, materialization_terminal_id
                )
                exact_join = True
        elif (
            failure_fact.get("presence") == "REGULAR_FILE"
            and receipt_fact.get("presence") == "ABSENT"
        ):
            terminal = _load_launch_document(
                paths["inner_failure"], LAUNCH_FAILURE_SCHEMA, "launch_failure_id"
            )
            terminal_id = terminal["launch_failure_id"]
            terminal_kind = "FAILURE"
            exact_join = (
                terminal["launch_attempt_id"] == attempt_id
                and terminal["target"] == target
                and terminal["success"] is False
            )
    return {
        "inner_launch_attempt_fact": attempt_fact,
        "inner_launch_receipt_fact": receipt_fact,
        "inner_launch_failure_fact": failure_fact,
        "inner_launch_attempt_id": attempt_id,
        "inner_launch_terminal_kind": terminal_kind,
        "inner_launch_terminal_id": terminal_id,
        "exact_attempt_terminal_join": exact_join,
    }


def _service_launch_terminal_document(
    *,
    success: bool,
    target: str,
    attempt: Mapping[str, Any],
    return_code: int | None,
    timed_out: bool,
    stdout: Mapping[str, Any],
    stderr: Mapping[str, Any],
    unit_absence: Mapping[str, Any] | None,
    inner_join: Mapping[str, Any],
    error: BaseException | None,
) -> tuple[dict[str, Any], bytes]:
    schema = (
        SERVICE_LAUNCH_RECEIPT_SCHEMA
        if success
        else SERVICE_LAUNCH_FAILURE_SCHEMA
    )
    domain = (
        SERVICE_LAUNCH_RECEIPT_DOMAIN
        if success
        else SERVICE_LAUNCH_FAILURE_DOMAIN
    )
    id_key = (
        "service_launch_receipt_id"
        if success
        else "service_launch_failure_id"
    )
    failure_type: str | None = None
    failure_message: str | None = None
    if error is not None:
        failure_type, failure_message = _bounded_error(error)
    payload = {
        "schema": schema,
        "target": target,
        "service_launch_attempt_id": attempt["service_launch_attempt_id"],
        "token": attempt["token"],
        "unit_name": attempt["unit_name"],
        "production_systemd_service_invocation": attempt[
            "production_systemd_service_invocation"
        ],
        "systemd_run_return_code": return_code,
        "systemd_run_timed_out": timed_out,
        "systemd_run_stdout": dict(stdout),
        "systemd_run_stderr": dict(stderr),
        "collected_unit_absence_observation": (
            None if unit_absence is None else dict(unit_absence)
        ),
        **dict(inner_join),
        "attempt_lock_preserved": True,
        "same_target_identity_rerun_forbidden": True,
        "pre_scientific_outer_dispatch": True,
        "campaign_event_or_evidence_document": False,
        "success": success,
        "failure_type": failure_type,
        "failure_message": failure_message,
    }
    if not success:
        publication_error = (
            error
            if isinstance(error, V180r12r4DurableWriteError)
            else None
        )
        if publication_error is not None and (
            publication_error.artifact
            not in {
                "SERVICE_LAUNCH_ATTEMPT",
                "SERVICE_LAUNCH_RECEIPT",
            }
            or publication_error.stage
            not in SERVICE_LAUNCH_PUBLICATION_STAGES
            or type(publication_error.path_created) is not bool
            or type(publication_error.completed) is not bool
            or publication_error.completed
            and not publication_error.path_created
            or publication_error.observed_state
            not in SERVICE_LAUNCH_PUBLICATION_STATES
        ):
            _fail("typed service launch publication failure changed")
        payload.update(
            {
                "publication_failure_artifact": (
                    None
                    if publication_error is None
                    else publication_error.artifact
                ),
                "publication_failure_stage": (
                    None
                    if publication_error is None
                    else publication_error.stage
                ),
                "publication_failure_path_created": (
                    None
                    if publication_error is None
                    else publication_error.path_created
                ),
                "publication_failure_completed": (
                    None
                    if publication_error is None
                    else publication_error.completed
                ),
                "publication_failure_observed_state": (
                    None
                    if publication_error is None
                    else publication_error.observed_state
                ),
            }
        )
    document = {
        **payload,
        id_key: hashlib.sha256(
            domain.encode("ascii") + b"\x00" + _canonical_json_bytes(payload)
        ).hexdigest(),
    }
    expected_fields = (
        SERVICE_LAUNCH_RECEIPT_FIELDS
        if success
        else SERVICE_LAUNCH_FAILURE_FIELDS
    )
    if set(document) != expected_fields:
        _fail("service launch terminal field set changed")
    if unit_absence is not None and (
        set(unit_absence) != SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS
    ):
        _fail("service launch terminal unit absence field set changed")
    if set(inner_join) != SERVICE_LAUNCH_INNER_JOIN_FIELDS:
        _fail("service launch terminal inner join field set changed")
    return document, _canonical_json_bytes(document)


def dispatch_production_service_v180r12r4(
    target: str,
    repository_root: Path,
    expected_materialization_terminal_sha256: str,
    *,
    process_runner: Any = None,
) -> dict[str, Any]:
    """Own the outer systemd-run attempt and close it with exact bounded facts."""

    _require_rule_identities_frozen()
    repository_root = _require_root(repository_root)
    expected_digest = _require_sha256(
        expected_materialization_terminal_sha256,
        "outer service materialization terminal digest",
    )
    materialization, materialization_raw = _load_materialization(
        repository_root, expected_digest
    )
    _verify_materialized_files(repository_root, materialization)
    if target not in _TARGETS:
        _fail("outer service dispatch target changed")
    _require_fresh_target_state(
        repository_root, target, materialization["materialization_terminal_id"]
    )
    if target == "measurement":
        verification_service_paths = _service_state_paths(
            repository_root, "verification"
        )
        if any(
            _lexists(verification_service_paths[name])
            for name in ("service_attempt", "service_receipt", "service_failure")
        ):
            raise V180r12r4PrelaunchLaunchReplayForbidden(
                "verification service progress predates measurement dispatch"
            )
    else:
        _require_successful_measurement_service_launch_v180r12r4(
            repository_root, expected_digest
        )
    paths = _service_state_paths(repository_root, target)
    if any(
        _lexists(paths[name])
        for name in ("service_attempt", "service_receipt", "service_failure")
    ):
        raise V180r12r4PrelaunchLaunchReplayForbidden(
            "production service launch triad already exists"
        )
    invocation = _production_systemd_service_invocation(
        repository_root, expected_digest, target
    )
    client_environment = _systemd_client_environment_v180r12r4()
    deadlines = _freeze_launch_deadlines_v180r12r4()
    runner = _run_child if process_runner is None else process_runner
    pre_attempt_unit_absence = _collected_unit_absence_observation(
        repository_root=repository_root,
        unit_name=PRODUCTION_TRANSIENT_SERVICE_ROWS[target][2],
        client_environment=client_environment,
        hard_deadline_ns=deadlines["hard_deadline_ns"],
        process_runner=runner,
    )
    if pre_attempt_unit_absence["unit_absent_after_wait_collect"] is not True:
        _fail("production service unit already exists before outer ATTEMPT")
    attempt, attempt_raw = _service_launch_attempt_document(
        target=target,
        materialization=materialization,
        materialization_sha256=hashlib.sha256(materialization_raw).hexdigest(),
        invocation=invocation,
        client_environment=client_environment,
        deadlines=deadlines,
        pre_attempt_unit_absence=pre_attempt_unit_absence,
    )
    attempt_publication = ServiceLaunchPublicationTokenV180R12R4(
        "SERVICE_LAUNCH_ATTEMPT"
    )
    receipt_publication = ServiceLaunchPublicationTokenV180R12R4(
        "SERVICE_LAUNCH_RECEIPT"
    )
    failure_publication = ServiceLaunchPublicationTokenV180R12R4(
        "SERVICE_LAUNCH_FAILURE"
    )
    attempt_lock_lost = False
    return_code: int | None = None
    timed_out = False
    stdout = _empty_stream_document()
    stderr = _empty_stream_document()
    unit_absence: dict[str, Any] | None = None
    inner_join = _inner_launch_join_observation(repository_root, target)
    service_receipt: dict[str, Any] | None = None
    service_receipt_raw: bytes | None = None
    try:
        # The outer try is active before publication entry.  There is no
        # caller-to-try gap in which O_EXCL progress could escape closure.
        attempt_publication.started = True
        try:
            _write_once(
                paths["service_attempt"],
                attempt_raw,
                publication_token=attempt_publication,
            )
        except FileExistsError as error:
            attempt_lock_lost = True
            raise V180r12r4PrelaunchLaunchReplayForbidden(
                "production service launch attempt was acquired concurrently"
            ) from error
        return_code, timed_out, stdout, stderr = runner(
            list(invocation["systemd_run_argv"]),
            client_environment,
            (),
            hard_deadline_ns=deadlines["hard_deadline_ns"],
            cwd=repository_root,
        )
        if type(return_code) is not int or type(timed_out) is not bool:
            _fail("systemd-run process result changed")
        _require_stream_document(stdout, "systemd-run stdout")
        _require_stream_document(stderr, "systemd-run stderr")
        unit_absence = _collected_unit_absence_observation(
            repository_root=repository_root,
            unit_name=attempt["unit_name"],
            client_environment=client_environment,
            hard_deadline_ns=deadlines["hard_deadline_ns"],
            process_runner=runner,
        )
        inner_join = _inner_launch_join_observation(
            repository_root,
            target,
            materialization_terminal_id=materialization[
                "materialization_terminal_id"
            ],
        )
        success = (
            return_code == 0
            and timed_out is False
            and stdout == _empty_stream_document()
            and stderr == _empty_stream_document()
            and unit_absence["unit_absent_after_wait_collect"] is True
            and inner_join["inner_launch_terminal_kind"] == "RECEIPT"
            and inner_join["exact_attempt_terminal_join"] is True
        )
        if not success:
            _fail("production systemd service did not reach its exact inner receipt")
        service_receipt, service_receipt_raw = _service_launch_terminal_document(
            success=True,
            target=target,
            attempt=attempt,
            return_code=return_code,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            unit_absence=unit_absence,
            inner_join=inner_join,
            error=None,
        )
        if _lexists(paths["service_failure"]):
            _fail("service launch failure appeared before receipt publication")
        receipt_publication.started = True
        _write_once(
            paths["service_receipt"],
            service_receipt_raw,
            publication_token=receipt_publication,
        )
        return service_receipt
    except BaseException as primary:
        primary_traceback = _base_traceback(primary)
        publication_observation = _service_launch_publication_observation(
            repository_root, target
        )
        _attach_service_launch_publication_observation(
            primary, publication_observation
        )
        if isinstance(primary, V180r12r4DurableWriteError):
            publication_name = {
                "SERVICE_LAUNCH_ATTEMPT": "attempt",
                "SERVICE_LAUNCH_RECEIPT": "receipt",
                "SERVICE_LAUNCH_FAILURE": "failure",
            }[primary.artifact]
            primary.observed_state = publication_observation[
                publication_name
            ]
            if (
                primary.artifact == "SERVICE_LAUNCH_RECEIPT"
                and primary.observed_state == "PRESENT_EXACT"
                and service_receipt is not None
                and service_receipt_raw is not None
            ):
                try:
                    _recover_exact_receipt_publication(
                        paths["service_receipt"], service_receipt_raw
                    )
                except BaseException as recovery_error:
                    recovery_type, recovery_message = _bounded_error(
                        recovery_error
                    )
                    BaseException.__setattr__(
                        primary,
                        "publication_recovery_error_type",
                        recovery_type,
                    )
                    BaseException.__setattr__(
                        primary,
                        "publication_recovery_error_message",
                        recovery_message,
                    )
                else:
                    receipt_publication.completed = True
                    receipt_publication.recovered = True
                    primary.completed = True
                    primary.recovered = True
                    return service_receipt
        if attempt_lock_lost:
            raise
        if publication_observation["attempt"] == "ABSENT":
            # No outer identity was consumed; a parent-open failure remains
            # outcome-free and cannot authorize a FAILURE namespace.
            raise
        try:
            inner_join = _inner_launch_join_observation(repository_root, target)
            failure, raw = _service_launch_terminal_document(
                success=False,
                target=target,
                attempt=attempt,
                return_code=return_code,
                timed_out=timed_out,
                stdout=stdout,
                stderr=stderr,
                unit_absence=unit_absence,
                inner_join=inner_join,
                error=primary,
            )
            if publication_observation["failure"] != "ABSENT":
                _fail("service launch failure namespace changed before publication")
            failure_publication.started = True
            _write_once(
                paths["service_failure"],
                raw,
                publication_token=failure_publication,
            )
        except BaseException as secondary:
            final_observation = _service_launch_publication_observation(
                repository_root, target
            )
            if isinstance(secondary, V180r12r4DurableWriteError):
                publication_name = {
                    "SERVICE_LAUNCH_ATTEMPT": "attempt",
                    "SERVICE_LAUNCH_RECEIPT": "receipt",
                    "SERVICE_LAUNCH_FAILURE": "failure",
                }[secondary.artifact]
                secondary.observed_state = final_observation[
                    publication_name
                ]
            _attach_service_launch_publication_observation(
                primary, final_observation
            )
            _raise_preserved_primary(
                primary, primary_traceback, secondary=secondary
            )
        _raise_preserved_primary(primary, primary_traceback)


def launch_prelaunch_target_v180r12r4(
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
    production_systemd_service_invocation = (
        _production_systemd_service_invocation(
            repository_root,
            expected_materialization_terminal_sha256,
            target,
        )
    )
    attempt, attempt_raw = _attempt_document(
        target=target,
        repository_root=repository_root,
        materialization=materialization,
        materialization_raw=materialization_raw,
        manifest_sha256=manifest_sha256,
        child_argv=child_argv,
        production_systemd_service_invocation=(
            production_systemd_service_invocation
        ),
    )
    return_code: int | None = None
    timed_out = False
    stdout = _StreamObservation().document()
    stderr = _StreamObservation().document()
    attempt_publication = ServiceLaunchPublicationTokenV180R12R4(
        "LAUNCH_ATTEMPT"
    )
    receipt_publication = ServiceLaunchPublicationTokenV180R12R4(
        "LAUNCH_RECEIPT"
    )
    failure_publication = ServiceLaunchPublicationTokenV180R12R4(
        "LAUNCH_FAILURE"
    )
    attempt_lock_lost = False
    launch_deadlines: dict[str, int] | None = None
    production_runtime_placement_t1: dict[str, Any] | None = None
    launch_receipt: dict[str, Any] | None = None
    launch_receipt_raw: bytes | None = None
    measurement_cgroup_cleanup_observations = (
        _initial_measurement_cgroup_observations(
            target, frozen_context["campaign_attempt_id"]
        )
    )
    try:
        # The closure try is active before parent traversal and O_EXCL.
        attempt_publication.started = True
        try:
            _write_once(
                paths["attempt"],
                attempt_raw,
                publication_token=attempt_publication,
            )
        except FileExistsError as error:
            attempt_lock_lost = True
            raise V180r12r4PrelaunchLaunchReplayForbidden(
                "target launch attempt lock was acquired concurrently"
            ) from error
        launch_deadlines = _freeze_launch_deadlines_v180r12r4()
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
        placement_descriptors, production_runtime_placement_t1 = (
            _prepare_and_observe_production_runtime_placement_t1(
                target=target,
                frozen_context=frozen_context,
            )
        )
        try:
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
                production_systemd_service_invocation=(
                    production_systemd_service_invocation
                ),
                production_runtime_placement_t1=(
                    production_runtime_placement_t1
                ),
            )
            external_descriptors = _prepare_external_launch_descriptors(
                target=target,
                context_raw=external_context_raw,
                placement_descriptors=placement_descriptors,
            )
        except BaseException:
            for descriptor in placement_descriptors:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise
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
        launch_receipt, launch_receipt_raw = _terminal_document(
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
            production_systemd_service_invocation=(
                production_systemd_service_invocation
            ),
            production_runtime_placement_t1=production_runtime_placement_t1,
        )
        receipt_publication.started = True
        _write_once(
            paths["receipt"],
            launch_receipt_raw,
            publication_token=receipt_publication,
        )
        return launch_receipt
    except BaseException as primary_error:
        primary_traceback = _base_traceback(primary_error)
        publication_observation = _launch_publication_observation(paths)
        _attach_launch_publication_observation(
            primary_error, publication_observation
        )
        if isinstance(primary_error, V180r12r4DurableWriteError):
            publication_name = {
                "LAUNCH_ATTEMPT": "attempt",
                "LAUNCH_RECEIPT": "receipt",
                "LAUNCH_FAILURE": "failure",
            }[primary_error.artifact]
            primary_error.observed_state = publication_observation[
                publication_name
            ]
            if (
                primary_error.artifact == "LAUNCH_RECEIPT"
                and primary_error.observed_state == "PRESENT_EXACT"
                and launch_receipt is not None
                and launch_receipt_raw is not None
            ):
                try:
                    _recover_exact_receipt_publication(
                        paths["receipt"], launch_receipt_raw
                    )
                except BaseException as recovery_error:
                    recovery_type, recovery_message = _bounded_error(
                        recovery_error
                    )
                    BaseException.__setattr__(
                        primary_error,
                        "publication_recovery_error_type",
                        recovery_type,
                    )
                    BaseException.__setattr__(
                        primary_error,
                        "publication_recovery_error_message",
                        recovery_message,
                    )
                else:
                    receipt_publication.completed = True
                    receipt_publication.recovered = True
                    primary_error.completed = True
                    primary_error.recovered = True
                    return launch_receipt
        if attempt_lock_lost:
            raise
        if publication_observation["attempt"] == "ABSENT":
            # No inner identity was consumed before O_EXCL.
            raise
        if launch_deadlines is None:
            launch_deadlines = _freeze_launch_deadlines_v180r12r4()
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
                production_systemd_service_invocation=(
                    production_systemd_service_invocation
                ),
                production_runtime_placement_t1=(
                    production_runtime_placement_t1
                ),
            )
            if publication_observation["failure"] != "ABSENT":
                _fail("inner launch failure namespace changed before publication")
            failure_publication.started = True
            _write_once(
                paths["launch_failure"],
                failure_raw,
                publication_token=failure_publication,
            )
        except BaseException as secondary_error:
            final_observation = _launch_publication_observation(paths)
            if isinstance(secondary_error, V180r12r4DurableWriteError):
                publication_name = {
                    "LAUNCH_ATTEMPT": "attempt",
                    "LAUNCH_RECEIPT": "receipt",
                    "LAUNCH_FAILURE": "failure",
                }[secondary_error.artifact]
                secondary_error.observed_state = final_observation[
                    publication_name
                ]
            _attach_launch_publication_observation(
                primary_error, final_observation
            )
            _raise_preserved_primary(
                primary_error, primary_traceback, secondary=secondary_error
            )
        _raise_preserved_primary(primary_error, primary_traceback)


def _require_launcher_startup(
    mode: str, target: str, repository_root: Path
) -> str:
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
        mode,
        target,
        str(repository_root),
    ]
    if sys.orig_argv != expected or sys.argv != expected[len(ISOLATED_ARGV_PREFIX) :]:
        _fail("trusted launcher exact argv changed")
    return _require_sha256(
        os.environ[MATERIALIZATION_TERMINAL_SHA256_ENV],
        "materialization terminal environment digest",
    )


def _require_current_service_attempt_v180r12r4(
    target: str,
    repository_root: Path,
    materialization_terminal_sha256: str,
) -> dict[str, Any]:
    path = _service_state_paths(repository_root, target)["service_attempt"]
    raw = _stable_read(
        path,
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    document = _parse_canonical_object(raw, "service launch attempt")
    if set(document) != SERVICE_LAUNCH_ATTEMPT_FIELDS:
        _fail("retained service launch attempt field set changed")
    identity = document.get("service_launch_attempt_id")
    payload = dict(document)
    payload.pop("service_launch_attempt_id", None)
    expected_invocation = _production_systemd_service_invocation(
        repository_root, materialization_terminal_sha256, target
    )
    pre_attempt_unit_absence = document.get(
        "pre_attempt_unit_absence_observation"
    )
    _require_exact_unit_absence_observation(
        pre_attempt_unit_absence,
        unit_name=PRODUCTION_TRANSIENT_SERVICE_ROWS[target][2],
        client_environment=_systemd_client_environment_v180r12r4(),
        require_absent=True,
    )
    if not (
        document.get("schema") == SERVICE_LAUNCH_ATTEMPT_SCHEMA
        and document.get("target") == target
        and document.get("token")
        == PRODUCTION_TRANSIENT_SERVICE_ROWS[target][1]
        and document.get("unit_name")
        == PRODUCTION_TRANSIENT_SERVICE_ROWS[target][2]
        and document.get("materialization_terminal_sha256")
        == materialization_terminal_sha256
        and document.get("production_systemd_service_invocation")
        == expected_invocation
        and document.get("systemd_run_argv")
        == expected_invocation["systemd_run_argv"]
        and document.get("systemd_run_environment")
        == _systemd_client_environment_v180r12r4()
        and document.get("inner_launch_artifact_paths") == _TARGETS[target]
        and document.get("attempt_o_excl_before_systemd_run") is True
        and document.get("same_target_identity_rerun_forbidden") is True
        and document.get("pre_scientific_outer_dispatch") is True
        and document.get("campaign_event_or_evidence_document") is False
        and identity
        == hashlib.sha256(
            SERVICE_LAUNCH_ATTEMPT_DOMAIN.encode("ascii")
            + b"\x00"
            + _canonical_json_bytes(payload)
        ).hexdigest()
    ):
        _fail("retained service entry lacks its exact outer attempt")
    return document


def _require_successful_measurement_service_launch_v180r12r4(
    repository_root: Path,
    materialization_terminal_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = _service_state_paths(repository_root, "measurement")
    if not (
        _lexists(paths["service_attempt"])
        and _lexists(paths["service_receipt"])
        and not _lexists(paths["service_failure"])
    ):
        raise V180r12r4PrelaunchLaunchReplayForbidden(
            "verification service lacks one successful measurement service predecessor"
        )
    attempt = _require_current_service_attempt_v180r12r4(
        "measurement", repository_root, materialization_terminal_sha256
    )
    raw = _stable_read(
        paths["service_receipt"],
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    receipt = _parse_canonical_object(raw, "measurement service launch receipt")
    if set(receipt) != SERVICE_LAUNCH_RECEIPT_FIELDS:
        _fail("measurement service launch receipt field set changed")
    identity = receipt.get("service_launch_receipt_id")
    payload = dict(receipt)
    payload.pop("service_launch_receipt_id", None)
    unit_absence = receipt.get("collected_unit_absence_observation")
    _recover_exact_receipt_publication(
        paths["service_receipt"], _canonical_json_bytes(receipt)
    )
    _require_exact_unit_absence_observation(
        unit_absence,
        unit_name=attempt["unit_name"],
        client_environment=_systemd_client_environment_v180r12r4(),
        require_absent=True,
    )
    current_join = _inner_launch_join_observation(
        repository_root,
        "measurement",
        materialization_terminal_id=attempt["materialization_terminal_id"],
    )
    receipt_join = {
        name: receipt[name] for name in SERVICE_LAUNCH_INNER_JOIN_FIELDS
    }
    if not (
        receipt.get("schema") == SERVICE_LAUNCH_RECEIPT_SCHEMA
        and receipt.get("target") == "measurement"
        and receipt.get("service_launch_attempt_id")
        == attempt["service_launch_attempt_id"]
        and receipt.get("token") == attempt["token"]
        and receipt.get("unit_name") == attempt["unit_name"]
        and receipt.get("production_systemd_service_invocation")
        == attempt["production_systemd_service_invocation"]
        and receipt.get("systemd_run_return_code") == 0
        and receipt.get("systemd_run_timed_out") is False
        and receipt.get("systemd_run_stdout") == _empty_stream_document()
        and receipt.get("systemd_run_stderr") == _empty_stream_document()
        and receipt.get("inner_launch_terminal_kind") == "RECEIPT"
        and receipt.get("exact_attempt_terminal_join") is True
        and receipt_join == current_join
        and receipt.get("attempt_lock_preserved") is True
        and receipt.get("same_target_identity_rerun_forbidden") is True
        and receipt.get("pre_scientific_outer_dispatch") is True
        and receipt.get("campaign_event_or_evidence_document") is False
        and receipt.get("success") is True
        and receipt.get("failure_type") is None
        and receipt.get("failure_message") is None
        and _require_sha256(identity, "measurement service launch receipt ID")
        == hashlib.sha256(
            SERVICE_LAUNCH_RECEIPT_DOMAIN.encode("ascii")
            + b"\x00"
            + _canonical_json_bytes(payload)
        ).hexdigest()
    ):
        _fail("measurement service launch predecessor join changed")
    return attempt, receipt


def main() -> None:
    if (
        len(sys.argv) != 4
        or sys.argv[1] not in {"dispatch", "service-entry"}
        or sys.argv[2] not in _TARGETS
    ):
        _fail(
            "trusted launcher API is mode, target, and exact repository root"
        )
    mode = sys.argv[1]
    target = sys.argv[2]
    repository_root = Path(sys.argv[3])
    expected = _require_launcher_startup(mode, target, repository_root)
    if mode == "dispatch":
        dispatch_production_service_v180r12r4(
            target, repository_root, expected
        )
        return
    _require_current_service_attempt_v180r12r4(
        target, repository_root, expected
    )
    if target == "verification":
        _require_successful_measurement_service_launch_v180r12r4(
            repository_root, expected
        )
    launch_prelaunch_target_v180r12r4(target, repository_root, expected)


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
    "SERVICE_LAUNCH_ATTEMPT_FIELDS",
    "SERVICE_LAUNCH_ATTEMPT_SCHEMA",
    "SERVICE_LAUNCH_FAILURE_FIELDS",
    "SERVICE_LAUNCH_FAILURE_SCHEMA",
    "SERVICE_LAUNCH_INNER_JOIN_FIELDS",
    "SERVICE_LAUNCH_PUBLICATION_STAGES",
    "SERVICE_LAUNCH_PUBLICATION_STATES",
    "SERVICE_LAUNCH_RECEIPT_FIELDS",
    "SERVICE_LAUNCH_RECEIPT_SCHEMA",
    "SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS",
    "LAUNCH_RULE_DOCUMENT",
    "LAUNCH_RULE_ID",
    "MATERIALIZATION_TERMINAL_SHA256_ENV",
    "MEASUREMENT_ATTEMPT_RELATIVE_PATH",
    "MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH",
    "MEASUREMENT_RECEIPT_RELATIVE_PATH",
    "PRODUCTION_SERVICE_LAUNCH_ARTIFACT_PATHS",
    "PRODUCTION_SERVICE_LAUNCH_MODES",
    "LEDGER_CLOSURE_BYTE_CAP",
    "LEDGER_CLOSURE_RELATIVE_PATH",
    "OS_RECEIPT_BUNDLE_BYTE_CAP",
    "OS_RECEIPT_RELATIVE_PATH",
    "PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP",
    "PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH",
    "PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA",
    "SUCCESS_ARTIFACT_ORDER",
    "SUCCESS_ARTIFACT_ROWS",
    "SUCCESS_DURABLE_WRITE_ORDER",
    "VERIFICATION_ATTEMPT_RELATIVE_PATH",
    "VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH",
    "VERIFICATION_RECEIPT_RELATIVE_PATH",
    "V180r12r4PrelaunchLaunchError",
    "V180r12r4PrelaunchLaunchReplayForbidden",
    "V180r12r4DurableWriteError",
    "ServiceLaunchPublicationTokenV180R12R4",
    "WALL_TIMEOUT_SECONDS",
    "launch_prelaunch_target_v180r12r4",
    "dispatch_production_service_v180r12r4",
)


if __name__ == "__main__":
    main()
