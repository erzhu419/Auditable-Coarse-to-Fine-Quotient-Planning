#!/usr/bin/python3
"""One-shot producer-free verification runner for V180r12r4.

The retained bootstrap is the only supported entrypoint.  This runner first
replays its source/materialization/launch chain, then invokes only the
producer-free independent verifier.  It writes the verification and one
byte-identical retained replay with O_EXCL durability.  Once the exact
verification launch attempt exists, any success, failure, partial write, or
hostile exception consumes that launch identity.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import errno
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import sys
import time
import tokenize
import types
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import (
    construction_k7_campaign_measurement_independent_verifier_v180r12r4
    as independent_verifier,
)
from acfqp import construction_k7_domain_registry_extension_v180r12r4 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PROFILE_KEY = "verify_v180r12r4_campaign_measurement"
SCHEMA_VERSION = "1.0.0"
VERIFICATION_FAILURE_SCHEMA = (
    "acfqp.campaign_measurement_verification_failure.v180r12r4"
)
PRELAUNCH_MANIFEST_SCHEMA = "acfqp.v180r12r4_source_bound_launch_manifest.v1"
MATERIALIZATION_TERMINAL_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_materialization_terminal.v1"
)
LAUNCH_ATTEMPT_SCHEMA = "acfqp.v180r12r4_prelaunch_launch_attempt.v1"
LAUNCH_RECEIPT_SCHEMA = "acfqp.v180r12r4_prelaunch_launch_receipt.v1"
SERVICE_LAUNCH_ATTEMPT_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_service_launch_attempt.v1"
)
SERVICE_LAUNCH_RECEIPT_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_service_launch_receipt.v1"
)
SERVICE_LAUNCH_FAILURE_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_service_launch_failure.v1"
)
SERVICE_LAUNCH_ATTEMPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-attempt:v180r12r4"
)
SERVICE_LAUNCH_RECEIPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-receipt:v180r12r4"
)
SERVICE_LAUNCH_FAILURE_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-failure:v180r12r4"
)
SERVICE_LAUNCH_ATTEMPT_FIELDS = frozenset(
    "schema target token unit_name materialization_terminal_id "
    "materialization_terminal_sha256 launch_rule_id "
    "production_systemd_service_invocation systemd_run_argv "
    "systemd_run_environment pre_attempt_unit_absence_observation "
    "inner_launch_artifact_paths monotonic_origin_ns "
    "hard_deadline_ns campaign_deadline_ns attempt_o_excl_before_systemd_run "
    "same_target_identity_rerun_forbidden pre_scientific_outer_dispatch "
    "campaign_event_or_evidence_document service_launch_attempt_id".split()
)
SERVICE_LAUNCH_INNER_JOIN_FIELDS = frozenset(
    "inner_launch_attempt_fact inner_launch_receipt_fact "
    "inner_launch_failure_fact inner_launch_attempt_id "
    "inner_launch_terminal_kind inner_launch_terminal_id "
    "exact_attempt_terminal_join".split()
)
SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS = frozenset(
    "systemctl_argv systemctl_environment return_code timed_out stdout stderr "
    "expected_load_state unit_absent_after_wait_collect".split()
)
SERVICE_LAUNCH_RECEIPT_FIELDS = frozenset(
    (
        "schema", "target", "service_launch_attempt_id", "token", "unit_name",
        "production_systemd_service_invocation", "systemd_run_return_code",
        "systemd_run_timed_out", "systemd_run_stdout", "systemd_run_stderr",
        "collected_unit_absence_observation", *SERVICE_LAUNCH_INNER_JOIN_FIELDS,
        "attempt_lock_preserved", "same_target_identity_rerun_forbidden",
        "pre_scientific_outer_dispatch", "campaign_event_or_evidence_document",
        "success", "failure_type", "failure_message", "service_launch_receipt_id",
    )
)
SERVICE_LAUNCH_PUBLICATION_STAGES = (
    "BEFORE_PARENT_OPEN", "BEFORE_O_EXCL", "AFTER_O_EXCL",
    "AFTER_FULL_WRITE", "AFTER_FILE_FSYNC", "AFTER_PARENT_FSYNC",
    "AFTER_READBACK",
)
SERVICE_LAUNCH_PUBLICATION_STATES = (
    "ABSENT", "PRESENT_PARTIAL_OR_INVALID", "PRESENT_EXACT",
)
SERVICE_LAUNCH_FAILURE_PUBLICATION_FIELDS = frozenset(
    "publication_failure_artifact publication_failure_stage "
    "publication_failure_path_created publication_failure_completed "
    "publication_failure_observed_state".split()
)
SERVICE_LAUNCH_FAILURE_FIELDS = frozenset(
    (
        *(SERVICE_LAUNCH_RECEIPT_FIELDS - {"service_launch_receipt_id"}),
        *SERVICE_LAUNCH_FAILURE_PUBLICATION_FIELDS,
        "service_launch_failure_id",
    )
)

PYTHON_EXECUTABLE = "/usr/bin/python3"
PYCACHE_PREFIX = "/dev/null/v180r12r4"
MANIFEST_SHA256_ENV = "ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256"
PREREG_COMMIT_ENV = "ACFQP_V180R12R4_PREREG_COMMIT"
EXTERNAL_LAUNCH_CONTEXT_FD = 249
VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_verified_external_launch_context.v1"
)
ISOLATED_ARGV_PREFIX = (
    PYTHON_EXECUTABLE,
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={PYCACHE_PREFIX}",
)

EXTERNAL_LAUNCH_CONTEXT_FIELDS = (
    "schema",
    "target",
    "actor_role",
    "repository_root",
    "c_pre_root",
    "prereg_commit_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_materialization_terminal_byte_count",
    "prelaunch_materialization_terminal_sha256",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "current_launch_attempt_id",
    "current_launch_attempt_byte_count",
    "current_launch_attempt_sha256",
    "measurement_launch_attempt_id",
    "measurement_launch_attempt_byte_count",
    "measurement_launch_attempt_sha256",
    "protocol_id",
    "protocol_byte_count",
    "protocol_sha256",
    "authorization_id",
    "authorization_byte_count",
    "authorization_sha256",
    "authorization_evidence_id",
    "authorization_evidence_byte_count",
    "authorization_evidence_sha256",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
    "campaign_attempt_id",
    "monotonic_origin_ns",
    "hard_deadline_ns",
    "campaign_deadline_ns",
    "cgroup_parent_fact",
    "runtime_capability_fact",
    "production_systemd_service_invocation",
    "production_runtime_placement_t1",
    "inherited_fd_roles",
    "target_payload",
    "one_shot",
)
VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS = (
    *EXTERNAL_LAUNCH_CONTEXT_FIELDS,
    "precompiled_source_bundle_sha256",
    "native_zero_precompiled_source_rows",
    "external_launch_context_sha256",
    "context_consumed_once",
)
PRODUCTION_SYSTEMD_SERVICE_INVOCATION_SCHEMA = (
    "acfqp.v180r12r4_production_systemd_service_invocation.v1"
)
PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS = (
    "schema", "token_domain", "target", "token_input", "token",
    "unit_name", "unit_kind", "slice", "service_type", "delegate",
    "umask", "launcher_command", "systemd_run_argv",
)
PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN = (
    "acfqp:construction-k7-production-transient-service-token:v180r12r4"
)
V180R12R4R9_FAILED_PREDECESSOR_FREEZE_ID = (
    "89562134029a69da93ce1dda6e9ec70abb238050fda1f530a8c5c2f557b5eb60"
)
V180R12R4R9_FAILED_INNER_LAUNCH_FAILURE_ID = (
    "7a1b8496f89378f5b2131a096c17fb9f7ed43ac64b544eacdfb3ea2802a65e82"
)
V180R12R4R9_FAILED_OUTER_SERVICE_FAILURE_ID = (
    "aa3ee86dee489383a43a868180bd555a21978fc923c106e06e5b017adb4101bc"
)
V180R12R4_REPAIR_SCOPE = "TARGET_AWARE_RUNNER_GIT_PROCESS_CONFORMANCE"
PRODUCTION_TRANSIENT_SERVICE_TOKEN_BY_TARGET = {
    "measurement": "5bfee9fa85834621b4947c1b68d32e96b7c53e260336d0815fd18bf59522dc72",
    "verification": "6dadbbfad8eb31dd5cc524f57132952a0c3535fa3751ea55ef9e4cf95f87bb01",
}
PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t1.v1"
)
PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS = (
    "schema", "target", "token", "unit_name", "slice",
    "source_membership", "expected_source_membership", "self_pid",
    "self_pid_in_source_cgroup_procs", "cgroup_namespace_inode",
    "delegated_parent_fd_fact", "cgroup2_mount_fd_fact",
    "source_service_fd_fact", "nearest_common_ancestor_path",
    "nearest_common_ancestor_is_app_slice",
    "parent_cgroup_procs_o_wronly_openable",
    "planned_measurement_root_observation", "planned_measurement_root_absent",
    "t1_complete_before_child_popen",
)
VERIFICATION_EXTERNAL_FD_ROLE_ROWS = (
    (EXTERNAL_LAUNCH_CONTEXT_FD, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"),
)
FROZEN_AUTHORIZATION_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_frozen_authorization_context.v1"
)
FROZEN_AUTHORIZATION_CONTEXT_FIELDS = (
    "schema",
    "protocol_id",
    "protocol_byte_count",
    "protocol_sha256",
    "authorization_id",
    "authorization_byte_count",
    "authorization_sha256",
    "authorization_evidence_id",
    "authorization_evidence_byte_count",
    "authorization_evidence_sha256",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
    "campaign_attempt_id",
    "cgroup_parent_fact",
    "runtime_capability_fact",
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
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_prelaunch_failure.json"
)
MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_LAUNCH_ATTEMPT.json"
)
MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_LAUNCH_RECEIPT.json"
)
MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_measurement_launch_failure.json"
)
MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_SERVICE_LAUNCH_ATTEMPT.json"
)
MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_SERVICE_LAUNCH_RECEIPT.json"
)
MEASUREMENT_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_measurement_service_launch_failure.json"
)
VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_ATTEMPT.json"
)
VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_RECEIPT.json"
)
VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_verification_launch_failure.json"
)
OUTPUT_ROOT_RELATIVE_PATH = ".tmp/exact-freeze/v180r12r4_campaign_measurement"
EVIDENCE_INVENTORY_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/EVIDENCE_INVENTORY.json"
EXECUTION_CLOSURE_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/EXECUTION_CLOSURE.json"
OS_RECEIPT_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/OS_RECEIPT.json"
LEDGER_CLOSURE_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/LEDGER_CLOSURE.json"
TERMINAL_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/TERMINAL.json"
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
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification_failure.json"
)
RETAINED_REPLAY_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_verification_replay.json"
)
RUNTIME_CAS_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_cas"
)

ADDRESS_SPACE_HARD_CAP_BYTES = 16 * 1024 * 1024 * 1024
WALL_TIMEOUT_SECONDS = 14_400
TERMINAL_BYTE_CAP = 16 * 1024 * 1024
VERIFICATION_BYTE_CAP = 16 * 1024 * 1024
EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP = 64 * 1024 * 1024
EXECUTION_CLOSURE_BYTE_CAP = 1 * 1024 * 1024
OS_RECEIPT_BUNDLE_BYTE_CAP = 16 * 1024 * 1024
LEDGER_CLOSURE_BYTE_CAP = 64 * 1024 * 1024
LAUNCH_ARTIFACT_BYTE_CAP = 16 * 1024 * 1024
PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP = 65_536
MANIFEST_BYTE_CAP = 16 * 1024 * 1024
SOURCE_FILE_BYTE_CAP = 8 * 1024 * 1024
SOURCE_CLOSURE_FILE_CAP = 4_096
SOURCE_CLOSURE_TOTAL_BYTE_CAP = 128 * 1024 * 1024
FAILURE_EMERGENCY_RESERVE_BYTES = 4 * 1024 * 1024
FAILURE_MESSAGE_BYTE_CAP = 4_096
VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES = 64 * 1024
VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP = 4_096
VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP = 256 * 1024
VERIFICATION_FAILURE_OBSERVATION_BOUNDARY = (
    "IMMEDIATELY_BEFORE_FAILURE_WRITE"
)
CHILD_STREAM_BYTE_CAP = 1 * 1024 * 1024
CHILD_STREAM_RETAINED_PREFIX_BYTES = 4_096
MAX_EVENT_COUNT = 4_096
MAX_EVENT_BYTE_COUNT = 65_536
MAX_LEDGER_BYTE_COUNT = 64 * 1024 * 1024
SUBJECT_RESULT_BYTE_CAP = 1 * 1024 * 1024
SUBJECT_RESULT_RUNTIME_BYTE_CAP = 768 * 1024
FRAME_BYTE_CAP = 1 * 1024 * 1024
CAMPAIGN_CLEANUP_GRACE_SECONDS = 600
NANOSECONDS_PER_SECOND = 1_000_000_000

NATIVE_ZERO_PRECOMPILED_SOURCE_ROW_FIELDS = (
    "source_kind",
    "name",
    "source_path",
    "is_package",
    "marshal_byte_count",
    "marshal_sha256",
)
NATIVE_ZERO_MEASURED_TARGET_SOURCE_PATHS = {
    "measurement": "scripts/run_v180r12r4_campaign_measurement.py",
    "supervisor": "scripts/supervise_v180r12r4_campaign_measurement.py",
    "worker": "scripts/work_v180r12r4_campaign_measurement.py",
}

SOURCE_CLOSURE_REQUIRED_ROOTS = tuple(sorted((
    "scripts/bootstrap_v180r12r4_campaign_measurement.py",
    "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py",
    "scripts/materialize_v180r12r4_campaign_measurement_prelaunch.py",
    "scripts/run_v180r12r4_campaign_measurement.py",
    "scripts/supervise_v180r12r4_campaign_measurement.py",
    "scripts/verify_v180r12r4_campaign_measurement.py",
    "scripts/work_v180r12r4_campaign_measurement.py",
    "src/acfqp/construction_accounting_registry_v6.py",
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "authorization_evidence_freeze_v180r12r4.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "execution_authorization_v180r12r4.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "finalizer_v180r12r4.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "independent_verifier_v180r12r4.py"
    ),
    "src/acfqp/construction_k7_campaign_measurement_ledger_v180r12r4.py",
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "prelaunch_failure_freeze_v180r12r3.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "prelaunch_failure_freeze_v180r12r3r1.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r3r2.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r2.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r4.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r5.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r6.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r7.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r8.py"
    ),
    (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r9.py"
    ),
    "src/acfqp/construction_k7_campaign_measurement_protocol_v180r12r4.py",
    "src/acfqp/construction_k7_campaign_measurement_supervisor_v180r12r4.py",
    "src/acfqp/construction_k7_campaign_measurement_worker_v180r12r4.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r4.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r4e.py",
    (
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "production_evidence_freeze_v180r12r2.py"
    ),
)))
PROTOCOL_SOURCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_campaign_measurement_protocol_v180r12r4.py"
)
AUTHORIZATION_SOURCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_campaign_measurement_"
    "execution_authorization_v180r12r4.py"
)
AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_campaign_measurement_"
    "authorization_evidence_freeze_v180r12r4.py"
)
RUNNER_RELATIVE_PATH = "scripts/verify_v180r12r4_campaign_measurement.py"
TARGET_RUNNER_PATHS = {
    "measurement": "scripts/run_v180r12r4_campaign_measurement.py",
    "verification": RUNNER_RELATIVE_PATH,
    "supervisor": "scripts/supervise_v180r12r4_campaign_measurement.py",
    "worker": "scripts/work_v180r12r4_campaign_measurement.py",
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_CGROUP_PARENT_FACT_FIELDS = frozenset(
    {
        "schema", "mount_point", "mount_fstype", "mount_device",
        "mount_inode", "mount_options", "parent_path", "parent_device",
        "parent_inode", "owner_uid", "owner_gid", "mode", "controllers",
        "subtree_control", "cgroup_type", "cgroup_namespace_inode",
        "cgroup_events_present", "memory_events_present",
        "pids_events_present", "cgroup_kill_present", "cgroup_procs_present",
        "memory_peak_present", "pids_peak_present", "self_membership",
    }
)
_CGROUP_PARENT_FACT_FIELD_ORDER = (
    "schema",
    "mount_point",
    "mount_fstype",
    "mount_device",
    "mount_inode",
    "mount_options",
    "parent_path",
    "parent_device",
    "parent_inode",
    "owner_uid",
    "owner_gid",
    "mode",
    "controllers",
    "subtree_control",
    "cgroup_type",
    "cgroup_namespace_inode",
    "cgroup_events_present",
    "memory_events_present",
    "pids_events_present",
    "cgroup_kill_present",
    "cgroup_procs_present",
    "memory_peak_present",
    "pids_peak_present",
    "self_membership",
)
_RUNTIME_CAPABILITY_FACT_FIELDS = frozenset(
    {
        "schema", "machine_architecture", "single_threaded",
        "clone3_probe_errno", "clone3_syscall_recognized",
        "pidfd_send_signal_probe_errno", "pidfd_send_signal_recognized",
        "execveat_probe_errno", "execveat_recognized", "pidfd_wait_present",
        "landlock_abi", "uid", "gid", "effective_capability_mask",
        "admitted",
    }
)
_RUNTIME_CAPABILITY_FACT_FIELD_ORDER = (
    "schema",
    "machine_architecture",
    "single_threaded",
    "clone3_probe_errno",
    "clone3_syscall_recognized",
    "pidfd_send_signal_probe_errno",
    "pidfd_send_signal_recognized",
    "execveat_probe_errno",
    "execveat_recognized",
    "pidfd_wait_present",
    "landlock_abi",
    "uid",
    "gid",
    "effective_capability_mask",
    "admitted",
)
_SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA = (
    "acfqp.v180r12r4_socket_buffer_capability_fact.v1"
)
_SOCKET_BUFFER_CAPABILITY_FACT_FIELD_ORDER = (
    "schema", "probe_boundary", "socket_family", "socket_type",
    "endpoint_count", "buffer_request_bytes", "effective_min_bytes",
    "net_core_wmem_max_bytes", "net_core_rmem_max_bytes",
    "endpoint_0_so_sndbuf_bytes", "endpoint_0_so_rcvbuf_bytes",
    "endpoint_1_so_sndbuf_bytes", "endpoint_1_so_rcvbuf_bytes",
)
_SOCKET_BUFFER_CAPABILITY_FACT_FIELDS = set(
    _SOCKET_BUFFER_CAPABILITY_FACT_FIELD_ORDER
)
_SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS = (
    "schema", "probe_boundary", "socket_family", "socket_type",
    "endpoint_count", "buffer_request_bytes", "effective_min_bytes",
)
_SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS = (
    "net_core_wmem_max_bytes", "net_core_rmem_max_bytes",
    "endpoint_0_so_sndbuf_bytes", "endpoint_0_so_rcvbuf_bytes",
    "endpoint_1_so_sndbuf_bytes", "endpoint_1_so_rcvbuf_bytes",
)
_SOCKET_BUFFER_CAPABILITY_EXPECTED = {
    "schema": _SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA,
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
_PRE_ATTEMPT_HOST_CONFORMANCE_FIELDS = {
    "schema",
    "phase",
    "campaign_attempt_id",
    "expected",
    "observed",
    "cgroup_parent_compared_fields",
    "cgroup_parent_excluded_fields",
    "runtime_capability_compared_fields",
    "socket_buffer_capability_exact_fields",
    "socket_buffer_capability_at_least_fields",
    "mismatch_rows",
    "mismatch_count",
    "cause",
    "full_host_conformance",
    "working_tree_source_conformance_joined",
    "production_unit_ownership_t1_joined",
    "campaign_event_or_counter_record_issued",
    "campaign_attempt_created",
}
_SERVICE_CONTEXT_CAPTURE_SCHEMA = (
    "acfqp.v180r12r4r5_service_context_capture.v1"
)
_SERVICE_CONTEXT_CAPTURE_PURPOSE = (
    "BENIGN_PRE_FREEZE_SERVICE_CONTEXT_OBSERVATION_NO_CAMPAIGN_ATTEMPT"
)
_SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT = 1_459
_SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256 = (
    "53508b200ae3b0279bda887cec804a8dd06f7d800734fe3d760f1712ea866fd3"
)
_RAW_FACT_FIELDS = {"relative_path", "byte_count", "sha256"}
_MODULE_FACT_FIELDS = _RAW_FACT_FIELDS | {"module", "is_package"}
_CLOSURE_FIELDS = {"facts", "file_count", "total_byte_count", "facts_sha256"}
_NORMALIZED_WRAPPER_FIELDS = _RAW_FACT_FIELDS | {
    "binding_kind",
    "redacted_constant_names",
}
_SOURCE_CONFORMANCE_FIELDS = {
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
_SOURCE_CONFORMANCE_SNAPSHOT_FIELDS = {
    "relative_path",
    "expected",
    "observed_before",
    "observed_after",
    "observed_content",
    "mismatch_fields",
    "conformant",
}
_SOURCE_CONFORMANCE_EXPECTED_FIELDS = {
    "file_type",
    "git_mode",
    "mode",
    "st_nlink",
    "binding_kind",
    "byte_count",
    "sha256",
    "git_blob_id",
}
_SOURCE_CONFORMANCE_STAT_FIELDS = {
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
_SOURCE_CONFORMANCE_CONTENT_FIELDS = {
    "binding_kind",
    "byte_count",
    "sha256",
    "git_blob_id",
    "physical_byte_count",
    "physical_sha256",
    "physical_git_blob_id",
}
_WRAPPER_REDACTED_NAMES = (
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
_WRAPPER_STRING_NAMES = frozenset(
    {
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        "EXPECTED_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_ID",
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
        "EXPECTED_SOURCE_CLOSURE_ID",
        "EXPECTED_SOURCE_CLOSURE_SHA256",
    }
)
_WRAPPER_INTEGER_NAMES = frozenset(_WRAPPER_REDACTED_NAMES) - _WRAPPER_STRING_NAMES
_MANIFEST_FIELDS = {
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
_MATERIALIZATION_FIELDS = {
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
_EXTERNAL_ROOT_FIELDS = {
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
_STREAM_FIELDS = {
    "byte_count",
    "sha256",
    "retained_prefix_hex",
    "retained_prefix_truncated",
}
_PROGRESS_NAMES = {
    "attempt",
    "receipt",
    "launch_failure",
    "runtime_cas",
    "output_root",
    "terminal",
    "evidence_inventory",
    "execution_closure",
    "os_receipt",
    "ledger_closure",
    "measurement_failure",
    "host_conformance",
    "verification",
    "verification_failure",
    "retained_replay",
}
_FAILURE_OBSERVATION_FIELDS = {
    "relative_path",
    "kind",
    "state",
    "mode",
    "nlink",
    "byte_count",
    "sha256",
    "directory_entries",
    "read_error_type",
    "read_error_message",
}
_WATCHDOG_CLEANUP_FIELDS = {
    "cancel_attempted",
    "cancel_succeeded",
    "ignore_attempted",
    "ignore_succeeded",
    "handler_restore_attempted",
    "handler_restore_succeeded",
    "teardown_completed",
    "secondary_observations",
}
_WATCHDOG_SECONDARY_FIELDS = {"failure_type", "failure_message"}
VERIFICATION_FAILURE_FIELDS = frozenset(
    "schema schema_version protocol_id authorization_id attempt_id "
    "verification_launch_attempt_id failure_code phase operation_id "
    "last_event_id completed_event_count failure_type message message_sha256 "
    "process_may_remain output_may_exist partial_artifact_observations "
    "partial_artifact_observation_boundary "
    "cgroup_failure_observation same_identity_rerun_forbidden "
    "successful_ledger_claimed counter_records_issued "
    "failure_memory_reserve_bytes failure_memory_reserve_allocated "
    "failure_memory_reserve_released_before_failure watchdog_was_armed "
    "watchdog_cleanup_observation traceback_retained campaign_actual_measurement "
    "COUNTER_COMPLETENESS_GATE WORKLOAD_ECONOMICS_GATE SCALAR_CALIBRATION_GATE "
    "BREAK_EVEN_GATE CAMPAIGN_CLEANUP_GRACE_SECONDS OFFICIAL_EXECUTION_GATE official_scalar_cost "
    "official_N_break_even official_execution_allowed verification_failure_id".split()
)
VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS = tuple(
    sorted(
        (
            (
                EVIDENCE_INVENTORY_RELATIVE_PATH,
                "FILE",
                EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
            ),
            (
                EXECUTION_CLOSURE_RELATIVE_PATH,
                "FILE",
                EXECUTION_CLOSURE_BYTE_CAP,
            ),
            (OS_RECEIPT_RELATIVE_PATH, "FILE", OS_RECEIPT_BUNDLE_BYTE_CAP),
            (LEDGER_CLOSURE_RELATIVE_PATH, "FILE", LEDGER_CLOSURE_BYTE_CAP),
            (TERMINAL_RELATIVE_PATH, "FILE", TERMINAL_BYTE_CAP),
            (RUNTIME_CAS_ROOT_RELATIVE_PATH, "DIRECTORY", 1),
            (VERIFICATION_RELATIVE_PATH, "FILE", VERIFICATION_BYTE_CAP),
            (
                VERIFICATION_FAILURE_RELATIVE_PATH,
                "FILE",
                VERIFICATION_BYTE_CAP,
            ),
            (RETAINED_REPLAY_RELATIVE_PATH, "FILE", VERIFICATION_BYTE_CAP),
        )
    )
)
VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROW_COUNT = len(
    VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
)
_ATTEMPT_FIELDS = {
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
_RECEIPT_FIELDS = {
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
    "launch_receipt_id",
}
_LAUNCH_PUBLICATION_STAGES = (
    "BEFORE_PARENT_OPEN", "BEFORE_O_EXCL", "AFTER_O_EXCL",
    "AFTER_FULL_WRITE", "AFTER_FILE_FSYNC", "AFTER_PARENT_FSYNC",
    "AFTER_READBACK",
)
_LAUNCH_PUBLICATION_STATES = (
    "ABSENT", "PRESENT_PARTIAL_OR_INVALID", "PRESENT_EXACT",
)
_LAUNCH_FAILURE_PUBLICATION_FIELDS = {
    "publication_failure_artifact", "publication_failure_stage",
    "publication_failure_path_created", "publication_failure_completed",
    "publication_failure_observed_state",
}
_FAILURE_FIELDS = (
    (_RECEIPT_FIELDS - {"launch_receipt_id"})
    | _LAUNCH_FAILURE_PUBLICATION_FIELDS
    | {"launch_failure_id"}
)
_MEASUREMENT_CGROUP_OBSERVATION_PHASES = (
    "BEFORE_POPEN", "CLEANUP", "AFTER_CHILD",
)
_MEASUREMENT_CGROUP_OBSERVATION_FIELDS = {
    "phase", "applicable", "campaign_attempt_id", "root_name",
    "ownership_acquired", "root_state", "root_mode", "root_nlink",
    "root_device", "root_inode", "root_populated", "root_process_count",
    "supervisor_state", "worker_state", "kill_attempted", "kill_succeeded",
    "wait_empty_attempted", "wait_empty_succeeded", "remove_attempted",
    "remove_succeeded", "residual_tree_or_process_possible", "error_type",
    "error_message",
}


class V180R12R4VerificationRunnerError(RuntimeError):
    """The exact producer-free verification occurrence cannot continue."""


class V180R12R4VerificationReplayForbidden(V180R12R4VerificationRunnerError):
    """The current verification launch identity has already been consumed."""


class V180R12R4VerificationDurableWriteFailure(
    V180R12R4VerificationRunnerError
):
    """A write failed, possibly after its O_EXCL directory entry existed."""

    def __init__(self, relative_path: str, path_created: bool) -> None:
        super().__init__("durable write-once verification operation failed")
        self.relative_path = relative_path
        self.path_created = path_created


class V180R12R4VerificationTimeout(V180R12R4VerificationRunnerError):
    """The independent verification wall deadline expired."""


def _fail(message: str) -> NoReturn:
    raise V180R12R4VerificationRunnerError(message)


def _cid(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256 identity")
    return value


def _frozen_cid(value: Any, label: str) -> str:
    result = _cid(value, label)
    if result == "0" * 64:
        _fail(f"{label} remains an unfrozen zero sentinel")
    return result


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive integer")
    return value


def _relative_parts(value: Any) -> tuple[str, ...]:
    if type(value) is not str:
        _fail("verification path must be one relative string")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        _fail("verification path escaped its repository root")
    return path.parts


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty exact bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V180R12R4VerificationRunnerError(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _plain_content_document(
    document: Mapping[str, Any], *, identity_field: str, label: str
) -> str:
    identity = _cid(document.get(identity_field), f"{label} identity")
    payload = dict(document)
    payload.pop(identity_field, None)
    if identity != hashlib.sha256(canonical_json_bytes(payload)).hexdigest():
        _fail(f"{label} content identity changed")
    return identity


def _domain_content_document(
    document: Mapping[str, Any],
    *,
    identity_field: str,
    domain: str,
    label: str,
) -> str:
    identity = _cid(document.get(identity_field), f"{label} identity")
    payload = dict(document)
    payload.pop(identity_field, None)
    expected = hashlib.sha256(
        domain.encode("ascii") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    if identity != expected:
        _fail(f"{label} domain-separated content identity changed")
    return identity


def _safe_error(error: BaseException) -> tuple[str, str]:
    fallback_kind = "UNAVAILABLE_EXCEPTION_TYPE"
    fallback_message = "UNFORMATTABLE_EXCEPTION"
    try:
        kind = type.__getattribute__(type(error), "__name__")
    except BaseException:
        kind = fallback_kind
    try:
        message = str(error)
    except BaseException:
        message = fallback_message
    if type(kind) is not str:
        kind = fallback_kind
    if type(message) is not str:
        message = fallback_message
    try:
        bounded_kind = bytes(kind, "utf-8", errors="replace")[:128].decode(
            "utf-8", "ignore"
        )
    except BaseException:
        bounded_kind = fallback_kind
    try:
        bounded_message = bytes(message, "utf-8", errors="replace")[
            :FAILURE_MESSAGE_BYTE_CAP
        ].decode("utf-8", "ignore")
    except BaseException:
        bounded_message = fallback_message
    if type(bounded_kind) is not str:
        bounded_kind = fallback_kind
    if type(bounded_message) is not str:
        bounded_message = fallback_message
    return bounded_kind, bounded_message


def _safe_utf8(value: str) -> bytes:
    if type(value) is not str:
        value = "UNFORMATTABLE_EXCEPTION"
    try:
        return bytes(value, "utf-8", errors="replace")
    except BaseException:
        return b"UNFORMATTABLE_EXCEPTION"


class VerificationDurableStoreV180R12R4:
    """Symlink-free stable reads and write-once durable verification output."""

    def __init__(self, repository_root: Path) -> None:
        root = Path(repository_root)
        metadata = os.lstat(root)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            _fail("repository root is linked or non-directory")
        self.repository_root = root.absolute()
        self.root_fd = os.open(
            root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )

    def close(self) -> None:
        if self.root_fd >= 0:
            os.close(self.root_fd)
            self.root_fd = -1

    def _open_parent(self, relative_path: str) -> tuple[int, str]:
        parts = _relative_parts(relative_path)
        current = os.dup(self.root_fd)
        try:
            for part in parts[:-1]:
                successor = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=current,
                )
                os.close(current)
                current = successor
            return current, parts[-1]
        except BaseException:
            os.close(current)
            raise

    def lexists(self, relative_path: str) -> bool:
        try:
            parent_fd, name = self._open_parent(relative_path)
        except FileNotFoundError:
            return False
        try:
            try:
                os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return False
            return True
        finally:
            os.close(parent_fd)

    def read_stable(
        self,
        relative_path: str,
        *,
        byte_cap: int,
        required_mode: int | None = None,
    ) -> bytes:
        _positive(byte_cap, "stable-read byte cap")
        parent_fd = -1
        descriptor = -1
        try:
            parent_fd, name = self._open_parent(relative_path)
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size <= 0
                or before.st_size > byte_cap
                or required_mode is not None
                and stat.S_IMODE(before.st_mode) != required_mode
            ):
                _fail("stable input is not one bounded single-link regular file")
            digest = hashlib.sha256()
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    _fail("stable input ended before its exact size")
                chunks.append(chunk)
                digest.update(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                _fail("stable input grew while observed")
            after = os.fstat(descriptor)
            fields = (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_nlink",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
            if any(getattr(before, key) != getattr(after, key) for key in fields):
                _fail("stable input identity changed during read")
            raw = b"".join(chunks)
            if hashlib.sha256(raw).digest() != digest.digest():  # pragma: no cover
                raise AssertionError
            return raw
        except OSError as error:
            raise V180R12R4VerificationRunnerError(
                "stable input is absent, linked, or unreadable"
            ) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if parent_fd >= 0:
                os.close(parent_fd)

    def observe(self, relative_path: str, byte_cap: int) -> dict[str, Any]:
        try:
            parent_fd, name = self._open_parent(relative_path)
        except FileNotFoundError:
            return {"presence": "ABSENT"}
        try:
            try:
                metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return {"presence": "ABSENT"}
            if stat.S_ISLNK(metadata.st_mode):
                return {"presence": "SYMLINK"}
            if stat.S_ISDIR(metadata.st_mode):
                return {
                    "presence": "DIRECTORY",
                    "mode": stat.S_IMODE(metadata.st_mode),
                }
            if not stat.S_ISREG(metadata.st_mode):
                return {"presence": "NONREGULAR"}
        except BaseException as error:
            kind, message = _safe_error(error)
            return {
                "presence": "OBSERVATION_ERROR",
                "error_type": kind,
                "error_message": message,
            }
        finally:
            os.close(parent_fd)
        if metadata.st_size > byte_cap:
            return {
                "presence": "REGULAR_FILE",
                "mode": stat.S_IMODE(metadata.st_mode),
                "byte_count": metadata.st_size,
                "sha256": None,
                "byte_cap_exceeded": True,
            }
        try:
            raw = self.read_stable(relative_path, byte_cap=byte_cap)
            return {
                "presence": "REGULAR_FILE",
                "mode": stat.S_IMODE(metadata.st_mode),
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        except BaseException as error:
            kind, message = _safe_error(error)
            return {
                "presence": "REGULAR_FILE",
                "mode": stat.S_IMODE(metadata.st_mode),
                "byte_count": metadata.st_size,
                "sha256": None,
                "read_error_type": kind,
                "read_error_message": message,
            }

    def write_once(
        self, relative_path: str, raw: bytes, *, mode: int = 0o400
    ) -> None:
        if type(raw) is not bytes or not raw:
            _fail("durable output must be nonempty exact bytes")
        parent_fd = -1
        descriptor = -1
        path_created = False
        try:
            parent_fd, name = self._open_parent(relative_path)
            descriptor = os.open(
                name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                mode,
                dir_fd=parent_fd,
            )
            path_created = True
            remaining = memoryview(raw)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    _fail("durable verification write made no progress")
                remaining = remaining[written:]
            os.fchmod(descriptor, mode)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            os.fsync(parent_fd)
        except FileExistsError:
            raise
        except BaseException as error:
            raise V180R12R4VerificationDurableWriteFailure(
                relative_path, path_created
            ) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if parent_fd >= 0:
                os.close(parent_fd)



def _allocate_failure_memory_reserve() -> bytearray:
    """Reserve releasable RLIMIT_AS-backed memory before output progress."""

    reserve = bytearray(FAILURE_EMERGENCY_RESERVE_BYTES)
    if len(reserve) != FAILURE_EMERGENCY_RESERVE_BYTES:  # pragma: no cover
        raise AssertionError("failure memory reserve length changed")
    return reserve


def _release_failure_memory_reserve(reserve: bytearray | None) -> None:
    if reserve is not None:
        reserve.clear()


@dataclass(frozen=True, slots=True)
class _FrozenAnchors:
    protocol_id: str
    authorization_id: str
    authorization_evidence_id: str
    execution_slot_id: str
    logical_occurrence_id: str
    execution_nonce: str
    source_closure_id: str
    source_closure_rule_id: str
    materialization_rule_id: str
    launch_rule_id: str
    prereg_commit_id: str
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class _LaunchChain:
    anchors: _FrozenAnchors
    verification_launch_attempt_id: str
    terminal_raw: bytes
    terminal: dict[str, Any]


def _raw_fact(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RAW_FACT_FIELDS:
        _fail(f"{label} raw fact schema changed")
    relative = value.get("relative_path")
    _relative_parts(relative)
    _positive(value.get("byte_count"), f"{label} byte count")
    _cid(value.get("sha256"), f"{label} digest")
    return dict(value)


def _validate_fact_bytes(
    raw: bytes, fact: Mapping[str, Any], label: str
) -> None:
    if (
        len(raw) != fact.get("byte_count")
        or hashlib.sha256(raw).hexdigest() != fact.get("sha256")
    ):
        _fail(f"{label} differs from its source-bound fact")


def _validate_frozen_authorization_context_v180r12r4(
    value: Any,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(
        FROZEN_AUTHORIZATION_CONTEXT_FIELDS
    ):
        _fail("frozen authorization context schema changed")
    cgroup = value.get("cgroup_parent_fact")
    capability = value.get("runtime_capability_fact")
    if (
        value.get("schema") != FROZEN_AUTHORIZATION_CONTEXT_SCHEMA
        or type(cgroup) is not dict
        or set(cgroup) != _CGROUP_PARENT_FACT_FIELDS
        or cgroup.get("schema") != "acfqp.v180r12r4_cgroup_parent_fact.v1"
        or type(capability) is not dict
        or set(capability) != _RUNTIME_CAPABILITY_FACT_FIELDS
        or capability.get("schema")
        != "acfqp.v180r12r4_runtime_capability_fact.v1"
        or capability.get("admitted") is not True
        or cgroup.get("owner_uid") != capability.get("uid")
        or cgroup.get("owner_gid") != capability.get("gid")
        or type(cgroup.get("mode")) is not int
        or cgroup["mode"] & (stat.S_IWUSR | stat.S_IXUSR)
        != (stat.S_IWUSR | stat.S_IXUSR)
    ):
        _fail("frozen authorization cgroup/runtime fact changed")
    capture = {
        "capture_purpose": _SERVICE_CONTEXT_CAPTURE_PURPOSE,
        "cgroup_parent_fact": cgroup,
        "runtime_capability_fact": capability,
        "schema": _SERVICE_CONTEXT_CAPTURE_SCHEMA,
    }
    capture_raw = canonical_json_bytes(capture) + b"\n"
    membership = cgroup.get("self_membership")
    parent_path = cgroup.get("parent_path")
    mount_point = cgroup.get("mount_point")
    if not (
        len(capture_raw) == _SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT
        and hashlib.sha256(capture_raw).hexdigest()
        == _SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256
        and cgroup.get("controllers") == ["cpu", "memory", "pids"]
        and cgroup.get("subtree_control") == ["cpu", "memory", "pids"]
        and type(membership) is str
        and type(parent_path) is str
        and type(mount_point) is str
        and PurePosixPath(membership.removeprefix("0::")).parent
        == PurePosixPath(parent_path.removeprefix(mount_point))
        and PurePosixPath(membership).name
        == "acfqp-v180r12r4r5-freeze-capture-20260829.service"
    ):
        _fail("frozen facts do not exact-join the source-bound service capture")
    for key in (
        "protocol_id",
        "protocol_sha256",
        "authorization_id",
        "authorization_sha256",
        "authorization_evidence_id",
        "authorization_evidence_sha256",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
        "campaign_attempt_id",
    ):
        _cid(value.get(key), f"frozen authorization {key}")
    for key in (
        "protocol_byte_count",
        "authorization_byte_count",
        "authorization_evidence_byte_count",
    ):
        _positive(value.get(key), f"frozen authorization {key}")
    expected_attempt_id = domains.derive_campaign_measurement_attempt_id_v180r12r4(
        protocol_id=value["protocol_id"],
        authorization_id=value["authorization_id"],
        authorization_evidence_id=value["authorization_evidence_id"],
        campaign_measurement_execution_slot_id=value[
            "campaign_measurement_execution_slot_id"
        ],
        logical_occurrence_id=value["logical_occurrence_id"],
        execution_nonce=value["execution_nonce"],
    )
    if value["campaign_attempt_id"] != expected_attempt_id:
        _fail("frozen campaign attempt six-authority identity changed")
    return dict(value)


def _closure(value: Any, label: str) -> tuple[dict[str, Any], ...]:
    if type(value) is not dict or set(value) != _CLOSURE_FIELDS:
        _fail(f"{label} closure schema changed")
    facts = value.get("facts")
    if type(facts) is not list or not facts or len(facts) > SOURCE_CLOSURE_FILE_CAP:
        _fail(f"{label} closure denominator changed")
    if (
        value.get("file_count") != len(facts)
        or value.get("total_byte_count")
        != sum(_positive(row.get("byte_count"), f"{label} fact bytes") for row in facts)
        or value.get("total_byte_count") > SOURCE_CLOSURE_TOTAL_BYTE_CAP
        or value.get("facts_sha256")
        != hashlib.sha256(canonical_json_bytes(facts)).hexdigest()
    ):
        _fail(f"{label} closure arithmetic changed")
    return tuple(dict(row) for row in facts)


def _literal_values(raw: bytes, names: Sequence[str], label: str) -> dict[str, Any]:
    try:
        tree = ast.parse(raw, filename=label)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise V180R12R4VerificationRunnerError(
            f"{label} is not static UTF-8 Python"
        ) from error
    wanted = set(names)
    values: dict[str, Any] = {}
    for statement in tree.body:
        if not (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id in wanted
        ):
            continue
        name = statement.targets[0].id
        if name in values or not isinstance(statement.value, ast.Constant):
            _fail(f"{label} frozen anchor is duplicated or nonliteral")
        values[name] = statement.value.value
    if set(values) != wanted:
        _fail(f"{label} frozen anchor set is incomplete")
    return values


def _normalize_wrapper(raw: bytes) -> tuple[bytes, dict[str, Any]]:
    try:
        tree = ast.parse(raw, filename=AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise V180R12R4VerificationRunnerError(
            "authorization evidence wrapper is not static UTF-8 Python"
        ) from error
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    replacements: list[tuple[int, int, bytes]] = []
    values: dict[str, Any] = {}
    for statement in tree.body:
        if not (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id in _WRAPPER_REDACTED_NAMES
        ):
            continue
        name = statement.targets[0].id
        value = statement.value
        literal = value.value if isinstance(value, ast.Constant) else None
        if name in values:
            _fail("authorization evidence wrapper anchor repeats")
        if name in _WRAPPER_STRING_NAMES:
            if type(literal) is not str:
                _fail("authorization evidence string anchor is nonliteral")
            replacement = b'"' + b"0" * 64 + b'"'
            token_type = tokenize.STRING
        else:
            if type(literal) is not int:
                _fail("authorization evidence integer anchor is nonliteral")
            replacement = b"0"
            token_type = tokenize.NUMBER
        start = offsets[value.lineno - 1] + value.col_offset
        end = offsets[value.end_lineno - 1] + value.end_col_offset
        tokens = tuple(
            token
            for token in tokenize.tokenize(io.BytesIO(raw[start:end]).readline)
            if token.type
            not in {
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.NEWLINE,
                tokenize.NL,
            }
        )
        if len(tokens) != 1 or tokens[0].type != token_type:
            _fail("authorization evidence anchor is not one lexical literal")
        replacements.append((start, end, replacement))
        values[name] = literal
    if set(values) != set(_WRAPPER_REDACTED_NAMES):
        _fail("authorization evidence wrapper anchor set is incomplete")
    result = raw
    for start, end, replacement in sorted(replacements, reverse=True):
        result = result[:start] + replacement + result[end:]
    return result, values


def _zero_atomic_cgroup_birth_preflight_interface() -> dict[str, Any]:
    zero_id = "0" * 64
    return {
        "schema": (
            "acfqp.v180r12r4_atomic_cgroup_birth_preflight_"
            "receipt_interface.v1"
        ),
        "receipt_id": zero_id,
        "receipt_byte_count": 0,
        "receipt_sha256": zero_id,
        "authority_accepted": False,
        "production_launch_authorized": False,
    }


def _production_service_artifact_paths() -> dict[str, dict[str, str]]:
    verification_prefix = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION"
    return {
        "measurement": {
            "attempt": MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
            "receipt": MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
            "failure": MEASUREMENT_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH,
        },
        "verification": {
            "attempt": verification_prefix + "_SERVICE_LAUNCH_ATTEMPT.json",
            "receipt": verification_prefix + "_SERVICE_LAUNCH_RECEIPT.json",
            "failure": (
                ".tmp/exact-freeze/"
                "v180r12r4_campaign_measurement_prelaunch_"
                "verification_service_launch_failure.json"
            ),
        },
    }


def _validated_production_token_input(
    value: Any, target: str
) -> dict[str, Any]:
    fields = {
        "failed_predecessor_freeze_id",
        "failed_inner_launch_failure_id",
        "failed_outer_service_failure_id",
        "repair_scope",
        "purpose",
    }
    if type(value) is not dict or set(value) != fields:
        _fail(f"{target} production token input changed")
    for key in (
        "failed_predecessor_freeze_id",
        "failed_inner_launch_failure_id",
        "failed_outer_service_failure_id",
    ):
        _cid(value[key], f"{target} production token {key}")
    expected_token = hashlib.sha256(
        PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(value)
    ).hexdigest()
    expected_input = {
        "failed_predecessor_freeze_id": (
            V180R12R4R9_FAILED_PREDECESSOR_FREEZE_ID
        ),
        "failed_inner_launch_failure_id": (
            V180R12R4R9_FAILED_INNER_LAUNCH_FAILURE_ID
        ),
        "failed_outer_service_failure_id": (
            V180R12R4R9_FAILED_OUTER_SERVICE_FAILURE_ID
        ),
        "repair_scope": V180R12R4_REPAIR_SCOPE,
        "purpose": target.upper(),
    }
    if not (
        value == expected_input
        and expected_token == PRODUCTION_TRANSIENT_SERVICE_TOKEN_BY_TARGET[target]
    ):
        _fail(f"{target} production token lineage changed")
    return dict(value)


def _expected_production_service_contract(
    contract: Any,
) -> dict[str, Any]:
    contract_fields = {
        "schema",
        "token_domain",
        "token_input_fields",
        "target_order",
        "target_rows",
        "unit_kind",
        "slice",
        "service_type",
        "delegate",
        "umask",
        "systemd_run_executable",
        "environment_executable",
        "materialization_terminal_sha256_template",
        "repository_root_and_launcher_paths_must_be_absolute",
        "outer_dispatch_process_cwd_must_equal_repository_root",
        "service_working_directory_must_equal_repository_root",
        "service_source_cgroup_is_exact_direct_child_of_app_slice",
        "active_protocol_authorization_attempt_ids_in_token",
        "host_facts_in_token",
        "preflight_receipt_interface",
    }
    row_fields = {
        "target",
        "token_input",
        "token",
        "unit_name",
        "outer_dispatch_cwd_template",
        "outer_dispatch_argv_template",
        "launcher_command_template",
        "service_working_directory_template",
        "systemd_run_argv_template",
    }
    if type(contract) is not dict or set(contract) != contract_fields:
        _fail("production systemd service contract schema changed")
    rows = contract.get("target_rows")
    if (
        type(rows) is not list
        or len(rows) != 2
        or any(type(row) is not dict or set(row) != row_fields for row in rows)
        or [row["target"] for row in rows] != ["measurement", "verification"]
    ):
        _fail("production systemd service target rows changed")
    expected_rows = []
    digest_template = "__V180R12R4_MATERIALIZATION_TERMINAL_SHA256__"
    for row in rows:
        target = row["target"]
        token_input = _validated_production_token_input(
            row["token_input"], target
        )
        token = PRODUCTION_TRANSIENT_SERVICE_TOKEN_BY_TARGET[target]
        unit_name = f"acfqp-v180r12r4-{target}-{token}.service"
        launcher = "{repository_root}/" + LAUNCHER_RELATIVE_PATH
        service_command = [
            "/usr/bin/env",
            "-i",
            "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
            + digest_template,
            "LC_CTYPE=C.UTF-8",
            *ISOLATED_ARGV_PREFIX,
            launcher,
            "service-entry",
            target,
            "{repository_root}",
        ]
        outer_command = [
            *service_command[:-4],
            launcher,
            "dispatch",
            target,
            "{repository_root}",
        ]
        expected_rows.append(
            {
                "target": target,
                "token_input": token_input,
                "token": token,
                "unit_name": unit_name,
                "outer_dispatch_cwd_template": "{repository_root}",
                "outer_dispatch_argv_template": outer_command,
                "launcher_command_template": service_command,
                "service_working_directory_template": "{repository_root}",
                "systemd_run_argv_template": [
                    "/usr/bin/systemd-run",
                    "--user",
                    "--wait",
                    "--collect",
                    "--pipe",
                    "--quiet",
                    "--no-ask-password",
                    "--unit=" + unit_name,
                    "--slice=app.slice",
                    "--service-type=exec",
                    "--property=Delegate=yes",
                    "--property=UMask=0077",
                    "--working-directory={repository_root}",
                    *service_command,
                ],
            }
        )
    expected = {
        "schema": "acfqp.v180r12r4_production_systemd_service_contracts.v1",
        "token_domain": PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN,
        "token_input_fields": [
            "failed_predecessor_freeze_id",
            "failed_inner_launch_failure_id",
            "failed_outer_service_failure_id",
            "repair_scope",
            "purpose",
        ],
        "target_order": ["measurement", "verification"],
        "target_rows": expected_rows,
        "unit_kind": "SERVICE_NOT_SCOPE",
        "slice": "app.slice",
        "service_type": "exec",
        "delegate": True,
        "umask": "0077",
        "systemd_run_executable": "/usr/bin/systemd-run",
        "environment_executable": "/usr/bin/env",
        "materialization_terminal_sha256_template": digest_template,
        "repository_root_and_launcher_paths_must_be_absolute": True,
        "outer_dispatch_process_cwd_must_equal_repository_root": True,
        "service_working_directory_must_equal_repository_root": True,
        "service_source_cgroup_is_exact_direct_child_of_app_slice": True,
        "active_protocol_authorization_attempt_ids_in_token": False,
        "host_facts_in_token": False,
        "preflight_receipt_interface": (
            _zero_atomic_cgroup_birth_preflight_interface()
        ),
    }
    if contract != expected:
        _fail("production systemd service contract changed")
    return expected


def _validate_production_manifest_fields(
    manifest: Mapping[str, Any], repository_root: Path
) -> None:
    contract = _expected_production_service_contract(
        manifest.get("production_systemd_service_contract")
    )
    expected_templates = {
        row["target"]: [
            item.replace("{repository_root}", str(repository_root))
            for item in row["systemd_run_argv_template"]
        ]
        for row in contract["target_rows"]
    }
    if not (
        manifest.get("production_systemd_run_argv_templates")
        == expected_templates
        and manifest.get("production_service_launch_artifact_paths")
        == _production_service_artifact_paths()
        and manifest.get("production_service_launch_modes")
        == {"outer_dispatch": "dispatch", "retained_service_entry": "service-entry"}
        and manifest.get("atomic_cgroup_birth_preflight_receipt_interface")
        == _zero_atomic_cgroup_birth_preflight_interface()
    ):
        _fail("production prelaunch manifest contract changed")


def _git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    ).hexdigest()


def _validate_working_tree_source_conformance(
    value: Any,
    closure_rows: Sequence[Mapping[str, Any]],
    raw_by_path: Mapping[str, bytes],
    wrapper_normalized: bytes,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _SOURCE_CONFORMANCE_FIELDS:
        _fail("working-tree source conformance schema changed")
    snapshots = value.get("snapshots")
    if not (
        value.get("schema")
        == "acfqp.v180r12r4_working_tree_source_conformance_diagnostic.v1"
        and value.get("phase")
        == "BEFORE_PRELAUNCH_OUTPUT_AND_SCIENTIFIC_CAMPAIGN"
        and type(value.get("source_root_count")) is int
        and value["source_root_count"] == len(SOURCE_CLOSURE_REQUIRED_ROOTS)
        and type(snapshots) is list
        and len(snapshots) == len(SOURCE_CLOSURE_REQUIRED_ROOTS)
        and type(value.get("mismatch_count")) is int
        and value["mismatch_count"] == 0
        and value.get("per_field_mismatches") == []
        and value.get("unit_ownership_evaluated") is False
        and value.get("full_source_conformance") is True
        and value.get("cause") is None
    ):
        _fail("working-tree source conformance did not pass")
    if len(closure_rows) != len(snapshots):
        _fail("working-tree source conformance denominator changed")
    for index, (snapshot, closure_row) in enumerate(
        zip(snapshots, closure_rows, strict=True)
    ):
        if (
            type(snapshot) is not dict
            or set(snapshot) != _SOURCE_CONFORMANCE_SNAPSHOT_FIELDS
            or type(snapshot.get("expected")) is not dict
            or set(snapshot["expected"]) != _SOURCE_CONFORMANCE_EXPECTED_FIELDS
            or type(snapshot.get("observed_before")) is not dict
            or set(snapshot["observed_before"]) != _SOURCE_CONFORMANCE_STAT_FIELDS
            or type(snapshot.get("observed_after")) is not dict
            or set(snapshot["observed_after"]) != _SOURCE_CONFORMANCE_STAT_FIELDS
            or type(snapshot.get("observed_content")) is not dict
            or set(snapshot["observed_content"])
            != _SOURCE_CONFORMANCE_CONTENT_FIELDS
        ):
            _fail(f"working-tree source snapshot {index} schema changed")
        relative = snapshot["relative_path"]
        if relative != closure_row.get("relative_path"):
            _fail("working-tree source-conformance closure join changed")
        raw = raw_by_path.get(relative)
        if raw is None:
            _fail(f"working-tree source snapshot {index} raw source is absent")
        effective_raw = (
            wrapper_normalized
            if relative == AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH
            else raw
        )
        binding_kind = (
            "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
            if relative == AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH
            else "EXACT_C_PRE_GIT_BLOB"
        )
        expected = snapshot["expected"]
        before = snapshot["observed_before"]
        after = snapshot["observed_after"]
        content = snapshot["observed_content"]
        expected_mode = {"100644": 0o644, "100755": 0o755}.get(
            expected.get("git_mode")
        )
        if not (
            before == after
            and snapshot.get("mismatch_fields") == []
            and snapshot.get("conformant") is True
            and expected_mode is not None
            and expected.get("file_type") == before.get("file_type")
            == "REGULAR_FILE"
            and type(before.get("st_mode")) is int
            and stat.S_ISREG(before["st_mode"])
            and stat.S_IMODE(before["st_mode"]) == before.get("mode")
            == expected_mode
            and expected.get("mode") == expected_mode
            and expected.get("st_nlink") == before.get("st_nlink") == 1
            and expected.get("binding_kind") == content.get("binding_kind")
            == binding_kind
            and expected.get("byte_count") == content.get("byte_count")
            == len(effective_raw)
            and expected.get("sha256") == content.get("sha256")
            == hashlib.sha256(effective_raw).hexdigest()
            and expected.get("git_blob_id") == content.get("git_blob_id")
            == _git_blob_id(effective_raw)
            and content.get("physical_byte_count") == before.get("st_size")
            == len(raw)
            and content.get("physical_sha256")
            == hashlib.sha256(raw).hexdigest()
            and content.get("physical_git_blob_id") == _git_blob_id(raw)
            and closure_row.get("byte_count") == len(effective_raw)
            and closure_row.get("sha256")
            == hashlib.sha256(effective_raw).hexdigest()
        ):
            _fail(f"working-tree source snapshot {index} changed")
        for field in (
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
        ):
            if type(before.get(field)) is not int or before[field] < 0:
                _fail(f"working-tree source snapshot {index} stat changed")
    return dict(value)


def _validate_source_manifest(
    store: VerificationDurableStoreV180R12R4,
    manifest: dict[str, Any],
    *,
    expected_manifest_sha256: str,
    expected_prereg_commit: str,
) -> _FrozenAnchors:
    if set(manifest) != _MANIFEST_FIELDS or not (
        manifest.get("schema") == PRELAUNCH_MANIFEST_SCHEMA
        and manifest.get("repository_root") == str(store.repository_root)
        and manifest.get("c_pre_root")
        == str(store.repository_root / PRELAUNCH_ROOT_RELATIVE_PATH)
        and manifest.get("manifest_relative_path") == "launch_manifest.json"
        and manifest.get("c_pre_commit_id") == expected_prereg_commit
        and manifest.get("working_tree_mutation_after_snapshot_in_scope") is False
    ):
        _fail("source-bound launch manifest context changed")
    _cid(expected_manifest_sha256, "expected launch manifest digest")
    if _COMMIT.fullmatch(expected_prereg_commit) is None:
        _fail("expected prereg commit is not one lowercase commit identity")
    _validate_production_manifest_fields(manifest, store.repository_root)

    source_modules = manifest.get("source_modules")
    if type(source_modules) is not list or not source_modules:
        _fail("source-bound module inventory changed")
    raw_by_path: dict[str, bytes] = {}
    module_fact_by_path: dict[str, dict[str, Any]] = {}
    modules: list[str] = []
    total = 0
    for value in source_modules:
        if type(value) is not dict or set(value) != _MODULE_FACT_FIELDS:
            _fail("source-bound module fact schema changed")
        fact = _raw_fact(
            {key: value[key] for key in _RAW_FACT_FIELDS},
            "source-bound module",
        )
        module = value.get("module")
        if type(module) is not str or type(value.get("is_package")) is not bool:
            _fail("source-bound module binding changed")
        relative = fact["relative_path"]
        if relative in module_fact_by_path or module in modules:
            _fail("source-bound module inventory repeats")
        raw = store.read_stable(relative, byte_cap=SOURCE_FILE_BYTE_CAP)
        _validate_fact_bytes(raw, fact, "source-bound module")
        module_fact_by_path[relative] = fact
        raw_by_path[relative] = raw
        modules.append(module)
        total += len(raw)
    if modules != sorted(set(modules)) or total > SOURCE_CLOSURE_TOTAL_BYTE_CAP:
        _fail("source-bound module inventory is unsorted or uncapped")

    targets = manifest.get("targets")
    if type(targets) is not dict or set(targets) != set(TARGET_RUNNER_PATHS):
        _fail("source-bound runner target set changed")
    for target, relative in TARGET_RUNNER_PATHS.items():
        fact = _raw_fact(targets[target], f"{target} runner")
        if fact["relative_path"] != relative:
            _fail("source-bound runner path changed")
        raw = store.read_stable(relative, byte_cap=SOURCE_FILE_BYTE_CAP)
        _validate_fact_bytes(raw, fact, f"{target} runner")
        raw_by_path[relative] = raw

    closure_rows = _closure(
        manifest.get("authorization_source_closure"),
        "authorization source",
    )
    closure_paths = tuple(row.get("relative_path") for row in closure_rows)
    if closure_paths != SOURCE_CLOSURE_REQUIRED_ROOTS:
        _fail("authorization source closure path set changed")
    wrapper_values: dict[str, Any] | None = None
    wrapper_normalized: bytes | None = None
    for value in closure_rows:
        relative = value.get("relative_path")
        if relative == AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH:
            if type(value) is not dict or set(value) != _NORMALIZED_WRAPPER_FIELDS:
                _fail("normalized authorization wrapper fact changed")
            raw = raw_by_path.get(relative)
            if raw is None:
                _fail("authorization wrapper raw module fact is absent")
            wrapper_normalized, wrapper_values = _normalize_wrapper(raw)
            if (
                value.get("binding_kind")
                != "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
                or value.get("redacted_constant_names")
                != list(_WRAPPER_REDACTED_NAMES)
            ):
                _fail("normalized authorization wrapper binding changed")
            _validate_fact_bytes(
                wrapper_normalized,
                {key: value[key] for key in _RAW_FACT_FIELDS},
                "normalized authorization wrapper",
            )
        else:
            fact = _raw_fact(value, "authorization closure source")
            raw = raw_by_path.get(relative)
            if raw is None:
                raw = store.read_stable(
                    relative,
                    byte_cap=(
                        SOURCE_FILE_BYTE_CAP
                        if relative.startswith("src/")
                        else 4 * 1024 * 1024
                    ),
                )
                raw_by_path[relative] = raw
            _validate_fact_bytes(raw, fact, "authorization closure source")
    if wrapper_values is None or wrapper_normalized is None:
        _fail("authorization evidence wrapper closure is absent")
    _validate_working_tree_source_conformance(
        manifest.get("working_tree_source_conformance"),
        closure_rows,
        raw_by_path,
        wrapper_normalized,
    )

    protocol_raw = raw_by_path.get(PROTOCOL_SOURCE_RELATIVE_PATH)
    authorization_raw = raw_by_path.get(AUTHORIZATION_SOURCE_RELATIVE_PATH)
    if protocol_raw is None or authorization_raw is None:
        _fail("protocol or authorization source is absent from closure")
    protocol_literals = _literal_values(
        protocol_raw,
        (
            "EXPECTED_PROTOCOL_ID",
            "EXPECTED_CANONICAL_BYTE_COUNT",
            "EXPECTED_CANONICAL_SHA256",
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID",
            "LOGICAL_OCCURRENCE_ID",
            "EXECUTION_NONCE",
            "EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID",
            "EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID",
            "EXPECTED_PRELAUNCH_LAUNCH_RULE_ID",
        ),
        "campaign protocol source",
    )
    authorization_literals = _literal_values(
        authorization_raw,
        ("EXPECTED_PROTOCOL_ID", "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"),
        "execution authorization source",
    )
    protocol_id = _frozen_cid(
        protocol_literals["EXPECTED_PROTOCOL_ID"], "frozen protocol ID"
    )
    execution_slot_id = _frozen_cid(
        protocol_literals["EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"],
        "frozen execution slot ID",
    )
    logical_occurrence_id = _frozen_cid(
        protocol_literals["LOGICAL_OCCURRENCE_ID"],
        "frozen logical occurrence ID",
    )
    execution_nonce = _frozen_cid(
        protocol_literals["EXECUTION_NONCE"], "frozen execution nonce"
    )
    source_rule = _frozen_cid(
        protocol_literals["EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID"],
        "frozen source-closure rule ID",
    )
    materialization_rule = _frozen_cid(
        protocol_literals["EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID"],
        "frozen materialization rule ID",
    )
    launch_rule = _frozen_cid(
        protocol_literals["EXPECTED_PRELAUNCH_LAUNCH_RULE_ID"],
        "frozen launch rule ID",
    )
    if not (
        _positive(
            protocol_literals["EXPECTED_CANONICAL_BYTE_COUNT"],
            "frozen protocol canonical bytes",
        )
        and _frozen_cid(
            protocol_literals["EXPECTED_CANONICAL_SHA256"],
            "frozen protocol canonical digest",
        )
        and authorization_literals["EXPECTED_PROTOCOL_ID"] == protocol_id
        and authorization_literals[
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"
        ]
        == execution_slot_id
    ):
        _fail("protocol and authorization frozen anchors disagree")

    authorization_id = _frozen_cid(
        wrapper_values["EXPECTED_AUTHORIZATION_ID"],
        "frozen authorization ID",
    )
    authorization_evidence_id = _frozen_cid(
        wrapper_values["EXPECTED_AUTHORIZATION_EVIDENCE_ID"],
        "frozen authorization evidence ID",
    )
    source_closure_id = _frozen_cid(
        wrapper_values["EXPECTED_SOURCE_CLOSURE_ID"],
        "frozen authorization source closure ID",
    )
    for name in _WRAPPER_INTEGER_NAMES:
        _positive(wrapper_values[name], f"frozen wrapper {name}")
    for name in _WRAPPER_STRING_NAMES - {
        "EXPECTED_AUTHORIZATION_ID",
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        "EXPECTED_SOURCE_CLOSURE_ID",
    }:
        _frozen_cid(wrapper_values[name], f"frozen wrapper {name}")
    authorization_fact = module_fact_by_path.get(
        AUTHORIZATION_SOURCE_RELATIVE_PATH
    )
    wrapper_module_fact = module_fact_by_path.get(
        AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH
    )
    if (
        authorization_fact is None
        or wrapper_module_fact is None
        or wrapper_values["EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT"]
        != authorization_fact["byte_count"]
        or wrapper_values["EXPECTED_AUTHORIZATION_SOURCE_SHA256"]
        != authorization_fact["sha256"]
        or wrapper_module_fact["byte_count"]
        != len(raw_by_path[AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH])
        or wrapper_module_fact["sha256"]
        != hashlib.sha256(
            raw_by_path[AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH]
        ).hexdigest()
    ):
        _fail("authorization evidence/source raw-fact join changed")

    third_party = _closure(
        manifest.get("third_party_source_closure"), "third-party source"
    )
    if any(type(row) is not dict for row in third_party):
        _fail("third-party source closure changed")
    source_facts = [
        {key: row[key] for key in _RAW_FACT_FIELDS} for row in closure_rows
    ]
    source_payload = {
        "schema": "acfqp.v180r12r4_authorization_source_closure.v1",
        "source_facts": source_facts,
        "source_fact_count": len(source_facts),
        "source_total_byte_count": sum(row["byte_count"] for row in source_facts),
        "required_static_roots": list(SOURCE_CLOSURE_REQUIRED_ROOTS),
        "transitive_local_import_closure_required": True,
        "authorization_self_normalized_by_evidence_freeze": True,
    }
    source_raw = canonical_json_bytes(source_payload)
    if not (
        wrapper_values["EXPECTED_SOURCE_CLOSURE_ID"]
        == hashlib.sha256(source_raw).hexdigest()
        and wrapper_values["EXPECTED_SOURCE_CLOSURE_BYTE_COUNT"]
        == len(source_raw)
        and wrapper_values["EXPECTED_SOURCE_CLOSURE_SHA256"]
        == hashlib.sha256(source_raw).hexdigest()
        and wrapper_values["EXPECTED_SOURCE_CLOSURE_FILE_COUNT"]
        == len(source_facts)
    ):
        _fail("frozen authorization source closure identity changed")
    frozen_context = _validate_frozen_authorization_context_v180r12r4(
        manifest.get("frozen_authorization_context")
    )
    if not (
        frozen_context["protocol_id"] == protocol_id
        and frozen_context["protocol_byte_count"]
        == protocol_literals["EXPECTED_CANONICAL_BYTE_COUNT"]
        and frozen_context["protocol_sha256"]
        == protocol_literals["EXPECTED_CANONICAL_SHA256"]
        and frozen_context["authorization_id"] == authorization_id
        and frozen_context["authorization_byte_count"]
        == wrapper_values["EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT"]
        and frozen_context["authorization_sha256"]
        == wrapper_values["EXPECTED_AUTHORIZATION_CANONICAL_SHA256"]
        and frozen_context["authorization_evidence_id"]
        == authorization_evidence_id
        and frozen_context["authorization_evidence_byte_count"]
        == wrapper_values["EXPECTED_CANONICAL_BYTE_COUNT"]
        and frozen_context["authorization_evidence_sha256"]
        == wrapper_values["EXPECTED_CANONICAL_SHA256"]
        and frozen_context["campaign_measurement_execution_slot_id"]
        == execution_slot_id
        and frozen_context["logical_occurrence_id"] == logical_occurrence_id
        and frozen_context["execution_nonce"] == execution_nonce
    ):
        _fail("frozen authorization context differs from source authority")
    return _FrozenAnchors(
        protocol_id,
        authorization_id,
        authorization_evidence_id,
        execution_slot_id,
        logical_occurrence_id,
        execution_nonce,
        source_closure_id,
        source_rule,
        materialization_rule,
        launch_rule,
        expected_prereg_commit,
        expected_manifest_sha256,
    )


def _fact(
    value: Any, *, expected_path: str, label: str
) -> dict[str, Any]:
    row = _raw_fact(value, label)
    if row["relative_path"] != expected_path:
        _fail(f"{label} path changed")
    return row


def _git_blob_fact(value: Any, *, expected_path: str, label: str) -> dict[str, Any]:
    fields = {"relative_path", "git_mode", "git_blob_id", "byte_count", "sha256"}
    if type(value) is not dict or set(value) != fields:
        _fail(f"{label} Git-blob fact schema changed")
    if (
        value.get("relative_path") != expected_path
        or type(value.get("git_mode")) is not str
        or type(value.get("git_blob_id")) is not str
        or re.fullmatch(r"[0-9a-f]{40,64}", value["git_blob_id"]) is None
    ):
        _fail(f"{label} Git-blob binding changed")
    _positive(value.get("byte_count"), f"{label} Git-blob bytes")
    _cid(value.get("sha256"), f"{label} Git-blob digest")
    return dict(value)


def _validate_materialization(
    store: VerificationDurableStoreV180R12R4,
    manifest: Mapping[str, Any],
    manifest_raw: bytes,
    anchors: _FrozenAnchors,
) -> tuple[dict[str, Any], bytes]:
    if store.lexists(MATERIALIZATION_FAILURE_RELATIVE_PATH):
        raise V180R12R4VerificationReplayForbidden(
            "materialization failure already consumed this source-bound identity"
        )
    raw = store.read_stable(
        MATERIALIZATION_TERMINAL_RELATIVE_PATH,
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    document = _canonical_object(raw, "materialization terminal")
    if set(document) != _MATERIALIZATION_FIELDS:
        _fail("materialization terminal schema changed")
    identity = _plain_content_document(
        document,
        identity_field="materialization_terminal_id",
        label="materialization terminal",
    )
    booleans = {
        "launch_manifest_digest_is_runtime_supplied_not_protocol_frozen": True,
        "launch_manifest_has_no_self_digest": True,
        "external_root_created_before_authorized_measurement_execution": True,
        "external_root_required_before_authorization_issuance": False,
        "materialization_terminal_written_last": True,
        "write_once_o_excl": True,
        "write_no_follow": True,
        "close_on_exec": True,
        "file_and_directory_fsync_required": True,
        "same_materialization_identity_rerun_forbidden": True,
        "construction_only": True,
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "scientific_occurrence_executed": False,
        "v180r12r4_outcome_bytes_accessed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "official_execution_allowed": False,
        "success": True,
    }
    service_rows = manifest["production_systemd_service_contract"]["target_rows"]
    expected_transient_rows = [
        {
            "target": row["target"],
            "token": row["token"],
            "unit_name": row["unit_name"],
        }
        for row in service_rows
    ]
    if not (
        identity == document["materialization_terminal_id"]
        and document.get("schema") == MATERIALIZATION_TERMINAL_SCHEMA
        and document.get("materialization_rule_id") == anchors.materialization_rule_id
        and document.get("source_closure_rule_id") == anchors.source_closure_rule_id
        and document.get("repository_root") == str(store.repository_root)
        and document.get("materialization_terminal_relative_path")
        == MATERIALIZATION_TERMINAL_RELATIVE_PATH
        and document.get("materialization_failure_relative_path")
        == MATERIALIZATION_FAILURE_RELATIVE_PATH
        and document.get("frozen_authorization_context_sha256")
        == hashlib.sha256(
            canonical_json_bytes(manifest["frozen_authorization_context"])
        ).hexdigest()
        and document.get("output_directory_mode") == "0700"
        and document.get("output_file_mode") == "0400"
        and document.get("production_transient_service_rows")
        == expected_transient_rows
        and document.get("production_service_launch_artifact_paths")
        == manifest["production_service_launch_artifact_paths"]
        and document.get("production_service_launch_modes")
        == manifest["production_service_launch_modes"]
        and document.get("atomic_cgroup_birth_preflight_receipt_interface")
        == manifest["atomic_cgroup_birth_preflight_receipt_interface"]
        and all(document.get(key) is expected for key, expected in booleans.items())
        and all(
            document.get(key) == "NOT_RUN"
            for key in (
                "COUNTER_COMPLETENESS_GATE",
                "WORKLOAD_ECONOMICS_GATE",
                "SCALAR_CALIBRATION_GATE",
                "BREAK_EVEN_GATE",
            )
        )
    ):
        _fail("materialization terminal boundary changed")
    if document.get("working_tree_source_conformance") != manifest[
        "working_tree_source_conformance"
    ]:
        _fail("manifest/materialization source conformance join changed")

    manifest_fact = _fact(
        document.get("launch_manifest"),
        expected_path=MANIFEST_RELATIVE_PATH,
        label="materialized launch manifest",
    )
    _validate_fact_bytes(manifest_raw, manifest_fact, "materialized launch manifest")
    for key, path in (
        ("retained_bootstrap", BOOTSTRAP_RELATIVE_PATH),
        ("retained_launcher", LAUNCHER_RELATIVE_PATH),
    ):
        row = _fact(document.get(key), expected_path=path, label=key)
        retained = store.read_stable(path, byte_cap=SOURCE_FILE_BYTE_CAP, required_mode=0o400)
        _validate_fact_bytes(retained, row, key)
    bootstrap_manifest_fact = _fact(
        manifest.get("bootstrap"), expected_path="bootstrap.py", label="manifest bootstrap"
    )
    if not (
        bootstrap_manifest_fact["byte_count"] == document["retained_bootstrap"]["byte_count"]
        and bootstrap_manifest_fact["sha256"] == document["retained_bootstrap"]["sha256"]
    ):
        _fail("retained bootstrap differs from its manifest fact")

    external_fact = document.get("external_root")
    if type(external_fact) is not dict or set(external_fact) != {
        "absolute_path", "byte_count", "sha256", "immutable_mode"
    }:
        _fail("materialization external-root fact schema changed")
    if not (
        external_fact.get("absolute_path")
        == str(store.repository_root / EXTERNAL_ROOT_RELATIVE_PATH)
        and external_fact.get("immutable_mode") == "0400"
    ):
        _fail("materialization external-root path changed")
    external_raw = store.read_stable(
        EXTERNAL_ROOT_RELATIVE_PATH,
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    if not (
        external_fact.get("byte_count") == len(external_raw)
        and external_fact.get("sha256") == hashlib.sha256(external_raw).hexdigest()
    ):
        _fail("materialization external-root fact changed")
    external = _canonical_object(external_raw, "prelaunch external root")
    if set(external) != _EXTERNAL_ROOT_FIELDS or not (
        external.get("schema") == "acfqp.v180r12r4_prelaunch_external_root.v1"
        and external.get("materialization_rule_id") == anchors.materialization_rule_id
        and external.get("source_closure_rule_id") == anchors.source_closure_rule_id
        and external.get("repository_root") == str(store.repository_root)
        and external.get("git_directory") == str(store.repository_root / ".git")
        and external.get("c_pre_commit_id") == anchors.prereg_commit_id
        and type(external.get("c_pre_tree_id")) is str
        and re.fullmatch(r"[0-9a-f]{40,64}", external["c_pre_tree_id"])
        and external.get("created_before_v180r12r4_authorized_measurement_execution") is True
        and external.get("v180r12r4_outcome_bytes_accessed") is False
        and type(external.get("third_party_source_roots")) is dict
        and set(external["third_party_source_roots"]) == {"packaging", "tomli"}
        and all(
            type(value) is str and Path(value).is_absolute()
            for value in external["third_party_source_roots"].values()
        )
        and external.get("frozen_authorization_context")
        == manifest["frozen_authorization_context"]
        and external.get("atomic_cgroup_birth_preflight_receipt_interface")
        == manifest["atomic_cgroup_birth_preflight_receipt_interface"]
    ):
        _fail("prelaunch external-root authority changed")
    for terminal_key, external_key, source_path in (
        ("bootstrap_source_git_blob", "bootstrap_git_blob", SOURCE_CLOSURE_REQUIRED_ROOTS[0]),
        ("launcher_source_git_blob", "launcher_git_blob", SOURCE_CLOSURE_REQUIRED_ROOTS[1]),
        ("materializer_source_git_blob", "materializer_git_blob", SOURCE_CLOSURE_REQUIRED_ROOTS[2]),
    ):
        left = _git_blob_fact(document.get(terminal_key), expected_path=source_path, label=terminal_key)
        right = _git_blob_fact(external.get(external_key), expected_path=source_path, label=external_key)
        if left != right:
            _fail("materialization Git-blob authority join changed")

    topology = document.get("git_topology")
    topology_fields = {
        "c_pre_commit_id", "c_pre_tree_id", "empty_bridge_commit_id",
        "empty_bridge_tree_id", "literal_commit_id", "literal_commit_tree_id",
        "literal_wrapper_prior_blob_id", "literal_wrapper_blob_id",
    }
    if type(topology) is not dict or set(topology) != topology_fields or not (
        topology.get("c_pre_commit_id") == anchors.prereg_commit_id
        and topology.get("c_pre_tree_id") == external["c_pre_tree_id"]
        and topology.get("empty_bridge_tree_id") == external["c_pre_tree_id"]
        and all(
            type(topology.get(key)) is str and _COMMIT.fullmatch(topology[key])
            for key in ("c_pre_commit_id", "empty_bridge_commit_id", "literal_commit_id")
        )
    ):
        _fail("materialization Git topology changed")

    authorization = manifest["authorization_source_closure"]
    third_party = manifest["third_party_source_closure"]
    if not (
        document.get("authorization_source_closure_file_count") == authorization["file_count"]
        and document.get("authorization_source_closure_total_byte_count") == authorization["total_byte_count"]
        and document.get("authorization_source_closure_facts_sha256") == authorization["facts_sha256"]
        and document.get("third_party_source_closure_file_count") == third_party["file_count"]
        and document.get("third_party_source_closure_total_byte_count") == third_party["total_byte_count"]
        and document.get("third_party_source_closure_facts_sha256") == third_party["facts_sha256"]
    ):
        _fail("materialization source-closure summaries changed")
    wrapper_rows = [
        row for row in authorization["facts"]
        if row.get("relative_path") == AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH
    ]
    source_wrapper_rows = [
        {key: row[key] for key in _RAW_FACT_FIELDS}
        for row in manifest["source_modules"]
        if row.get("relative_path") == AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH
    ]
    if not (
        wrapper_rows == [document.get("normalized_wrapper_fact")]
        and source_wrapper_rows == [document.get("current_literal_wrapper_raw_observation")]
    ):
        _fail("materialization authorization-wrapper joins changed")
    return document, raw


def _validate_stream(value: Any, label: str) -> None:
    if type(value) is not dict or set(value) != _STREAM_FIELDS:
        _fail(f"{label} stream schema changed")
    byte_count = value.get("byte_count")
    if type(byte_count) is not int or not 0 <= byte_count <= CHILD_STREAM_BYTE_CAP:
        _fail(f"{label} stream size changed")
    _cid(value.get("sha256"), f"{label} stream digest")
    prefix = value.get("retained_prefix_hex")
    if type(prefix) is not str or re.fullmatch(r"(?:[0-9a-f]{2})*", prefix) is None:
        _fail(f"{label} retained stream prefix changed")
    prefix_bytes = len(prefix) // 2
    if prefix_bytes > CHILD_STREAM_RETAINED_PREFIX_BYTES or value.get(
        "retained_prefix_truncated"
    ) is not (byte_count > prefix_bytes):
        _fail(f"{label} retained stream truncation claim changed")


def _plain_nested_mapping(value: Any, label: str) -> dict[str, Any]:
    def thaw(item: Any) -> Any:
        if type(item) in {dict, types.MappingProxyType}:
            return {key: thaw(nested) for key, nested in item.items()}
        if type(item) in {list, tuple}:
            return [thaw(nested) for nested in item]
        if item is None or type(item) in {str, bool, int}:
            return item
        raise TypeError("unsupported immutable context value")

    try:
        plain = loads_canonical_json(canonical_json_bytes(thaw(value)))
    except (TypeError, ValueError) as error:
        raise V180R12R4VerificationRunnerError(
            label + " is not canonical JSON data"
        ) from error
    if type(plain) is not dict:
        _fail(label + " must be one mapping")
    return plain


def _validate_production_systemd_service_invocation(
    value: Any,
    *,
    target: str,
    repository_root: str,
    materialization_terminal_sha256: str,
) -> dict[str, Any]:
    invocation = _plain_nested_mapping(
        value, f"{target} production systemd service invocation"
    )
    if tuple(invocation) != tuple(sorted(PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS)):
        # Canonical JSON replay sorts object keys; compare the exact population
        # separately from construction order.
        if set(invocation) != set(PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS):
            _fail(f"{target} production systemd service invocation keyset changed")
    token_input = invocation.get("token_input")
    if type(token_input) is not dict or set(token_input) != {
        "failed_predecessor_freeze_id", "failed_inner_launch_failure_id",
        "failed_outer_service_failure_id", "repair_scope", "purpose",
    }:
        _fail(f"{target} production systemd service token input changed")
    _cid(
        token_input.get("failed_predecessor_freeze_id"),
        "failed predecessor-freeze ID",
    )
    _cid(
        token_input.get("failed_inner_launch_failure_id"),
        "failed inner launch-failure ID",
    )
    _cid(
        token_input.get("failed_outer_service_failure_id"),
        "failed outer-service-failure ID",
    )
    digest = _cid(
        materialization_terminal_sha256,
        f"{target} materialization-terminal SHA256",
    )
    token = hashlib.sha256(
        PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(token_input)
    ).hexdigest()
    unit_name = f"acfqp-v180r12r4-{target}-{token}.service"
    launcher = repository_root + "/" + LAUNCHER_RELATIVE_PATH
    command = [
        "/usr/bin/env", "-i",
        "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256=" + digest,
        "LC_CTYPE=C.UTF-8", *ISOLATED_ARGV_PREFIX, launcher,
        "service-entry", target, repository_root,
    ]
    argv = [
        "/usr/bin/systemd-run", "--user", "--wait", "--collect", "--pipe",
        "--quiet", "--no-ask-password", "--unit=" + unit_name,
        "--slice=app.slice", "--service-type=exec", "--property=Delegate=yes",
        "--property=UMask=0077",
        "--working-directory=" + repository_root,
        *command,
    ]
    if not (
        target in PRODUCTION_TRANSIENT_SERVICE_TOKEN_BY_TARGET
        and invocation.get("schema") == PRODUCTION_SYSTEMD_SERVICE_INVOCATION_SCHEMA
        and invocation.get("token_domain") == PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN
        and invocation.get("target") == target
        and token_input
        == {
            "failed_predecessor_freeze_id": (
                V180R12R4R9_FAILED_PREDECESSOR_FREEZE_ID
            ),
            "failed_inner_launch_failure_id": (
                V180R12R4R9_FAILED_INNER_LAUNCH_FAILURE_ID
            ),
            "failed_outer_service_failure_id": (
                V180R12R4R9_FAILED_OUTER_SERVICE_FAILURE_ID
            ),
            "repair_scope": V180R12R4_REPAIR_SCOPE,
            "purpose": target.upper(),
        }
        and invocation.get("token") == token
        == PRODUCTION_TRANSIENT_SERVICE_TOKEN_BY_TARGET[target]
        and invocation.get("unit_name") == unit_name
        and invocation.get("unit_kind") == "SERVICE_NOT_SCOPE"
        and invocation.get("slice") == "app.slice"
        and invocation.get("service_type") == "exec"
        and invocation.get("delegate") is True
        and invocation.get("umask") == "0077"
        and invocation.get("launcher_command") == command
        and invocation.get("systemd_run_argv") == argv
    ):
        _fail(f"{target} production systemd service invocation changed")
    return invocation


def _validate_production_runtime_placement_t1(
    value: Any,
    *,
    target: str,
    invocation: Mapping[str, Any],
) -> dict[str, Any]:
    placement = _plain_nested_mapping(value, f"{target} production T1 placement")
    service = placement.get("source_service_fd_fact")
    parent = placement.get("delegated_parent_fd_fact")
    mount = placement.get("cgroup2_mount_fd_fact")
    root = placement.get("planned_measurement_root_observation")
    fd_fields = {
        "fd", "role", "access", "path", "device", "inode", "mode",
        "owner_uid", "owner_gid", "nlink",
    }
    if not (
        set(placement) == set(PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS)
        and placement.get("schema") == PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
        and placement.get("target") == target
        and placement.get("token") == invocation.get("token")
        and placement.get("unit_name") == invocation.get("unit_name")
        and placement.get("slice") == invocation.get("slice") == "app.slice"
        and placement.get("source_membership")
        == placement.get("expected_source_membership")
        and type(placement.get("self_pid")) is int
        and placement["self_pid"] > 0
        and placement.get("self_pid_in_source_cgroup_procs") is True
        and placement.get("nearest_common_ancestor_is_app_slice") is True
        and placement.get("parent_cgroup_procs_o_wronly_openable") is True
        and placement.get("planned_measurement_root_absent") is True
        and placement.get("t1_complete_before_child_popen") is True
        and all(type(row) is dict and set(row) == fd_fields for row in (parent, mount, service))
        and (parent.get("fd"), parent.get("role"), parent.get("access"))
        == (250, "DELEGATED_CGROUP_PARENT_DIRECTORY", "O_RDONLY")
        and (mount.get("fd"), mount.get("role"), mount.get("access"))
        == (251, "CGROUP2_MOUNT_DIRECTORY", "O_PATH")
        and (service.get("fd"), service.get("role"), service.get("access"))
        == (252, "SOURCE_SYSTEMD_SERVICE_DIRECTORY", "O_RDONLY")
        and type(root) is dict
        and root.get("phase") == "BEFORE_POPEN"
        and root.get("root_state") == "ABSENT"
        and root.get("ownership_acquired") is False
        and root.get("residual_tree_or_process_possible") is False
    ):
        _fail(f"{target} production T1 placement changed")
    return placement


def _validate_attempt(
    store: VerificationDurableStoreV180R12R4,
    relative_path: str,
    *,
    target: str,
    anchors: _FrozenAnchors,
    materialization: Mapping[str, Any],
    materialization_raw: bytes,
    manifest_raw: bytes,
) -> dict[str, Any]:
    raw = store.read_stable(relative_path, byte_cap=LAUNCH_ARTIFACT_BYTE_CAP, required_mode=0o400)
    document = _canonical_object(raw, f"{target} launch attempt")
    if set(document) != _ATTEMPT_FIELDS:
        _fail(f"{target} launch-attempt schema changed")
    _plain_content_document(document, identity_field="launch_attempt_id", label=f"{target} launch attempt")
    _validate_production_systemd_service_invocation(
        document.get("production_systemd_service_invocation"),
        target=target,
        repository_root=str(store.repository_root),
        materialization_terminal_sha256=document.get(
            "materialization_terminal_sha256"
        ),
    )
    expected_argv = [
        *ISOLATED_ARGV_PREFIX,
        str(store.repository_root / BOOTSTRAP_RELATIVE_PATH),
        target,
        str(store.repository_root),
        str(store.repository_root / PRELAUNCH_ROOT_RELATIVE_PATH),
        str(store.repository_root / MANIFEST_RELATIVE_PATH),
    ]
    if not (
        document.get("schema") == LAUNCH_ATTEMPT_SCHEMA
        and document.get("launch_rule_id") == anchors.launch_rule_id
        and document.get("target") == target
        and document.get("repository_root") == str(store.repository_root)
        and document.get("materialization_terminal_id") == materialization["materialization_terminal_id"]
        and document.get("materialization_terminal_byte_count") == len(materialization_raw)
        and document.get("materialization_terminal_sha256") == hashlib.sha256(materialization_raw).hexdigest()
        and document.get("launch_manifest_sha256") == hashlib.sha256(manifest_raw).hexdigest()
        and document.get("child_argv") == expected_argv
        and document.get("child_environment")
        == {MANIFEST_SHA256_ENV: anchors.manifest_sha256, "LC_CTYPE": "C.UTF-8"}
        and document.get("address_space_hard_cap_bytes") == ADDRESS_SPACE_HARD_CAP_BYTES
        and document.get("address_space_cap_applied_before_child_exec") is True
        and document.get("wall_timeout_seconds") == WALL_TIMEOUT_SECONDS
        and document.get("attempt_lock_written_before_child_exec") is True
        and document.get("same_target_identity_rerun_forbidden") is True
        and document.get("preauthorization_supervision") is True
        and document.get("campaign_actual_measurement") is False
        and document.get("scientific_occurrence_started") is False
        and document.get("authorized_child_measurement_execution_attempted")
        is (target == "measurement")
        and document.get("authorized_child_measurement_execution_completed")
        is False
        and document.get("producer_free_verification_attempted")
        is (target == "verification")
        and document.get("producer_free_verification_completed") is False
    ):
        _fail(f"{target} launch-attempt authority changed")
    return document


def _file_observation(
    store: VerificationDurableStoreV180R12R4, relative_path: str, cap: int
) -> dict[str, Any]:
    return store.observe(relative_path, cap)


def _validate_success_measurement_cgroup_observations(
    value: object, *, campaign_attempt_id: str
) -> None:
    campaign_attempt_id = _cid(
        campaign_attempt_id, "measurement cgroup campaign attempt ID"
    )
    if type(value) is not list or len(value) != 3:
        _fail("measurement launch cgroup observation denominator changed")
    expected_root_name = f"v180r12r4-{campaign_attempt_id}"
    for index, row in enumerate(value):
        if type(row) is not dict or set(row) != (
            _MEASUREMENT_CGROUP_OBSERVATION_FIELDS
        ):
            _fail("measurement launch cgroup observation schema changed")
        if not (
            row.get("phase") == _MEASUREMENT_CGROUP_OBSERVATION_PHASES[index]
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


def _validate_pre_attempt_host_conformance(
    store: VerificationDurableStoreV180R12R4,
    *,
    frozen_context: Mapping[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    raw = store.read_stable(
        PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH,
        byte_cap=PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP,
        required_mode=0o400,
    )
    document = _canonical_object(raw, "pre-attempt host conformance")
    frozen_parent = _plain_nested_mapping(
        frozen_context.get("cgroup_parent_fact"),
        "pre-attempt frozen cgroup parent fact",
    )
    frozen_runtime = _plain_nested_mapping(
        frozen_context.get("runtime_capability_fact"),
        "pre-attempt frozen runtime capability fact",
    )
    expected = document.get("expected")
    observed = document.get("observed")
    if not (
        set(document) == _PRE_ATTEMPT_HOST_CONFORMANCE_FIELDS
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
    compared_parent_fields = [
        field
        for field in _CGROUP_PARENT_FACT_FIELD_ORDER
        if field != "self_membership"
    ]
    observed_socket_exact = (
        {
            field: observed_socket.get(field)
            for field in _SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
        }
        if type(observed_socket) is dict
        else None
    )
    expected_socket_exact = {
        field: _SOCKET_BUFFER_CAPABILITY_EXPECTED[field]
        for field in _SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
    }
    socket_minimums_met = (
        type(observed_socket) is dict
        and all(
            type(observed_socket.get(field)) is int
            and observed_socket[field]
            >= _SOCKET_BUFFER_CAPABILITY_EXPECTED[field]
            for field in _SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
        )
    )
    if not (
        type(expected_parent) is dict
        and set(expected_parent) == _CGROUP_PARENT_FACT_FIELDS
        and type(observed_parent) is dict
        and set(observed_parent) == _CGROUP_PARENT_FACT_FIELDS
        and type(expected_runtime) is dict
        and set(expected_runtime) == _RUNTIME_CAPABILITY_FACT_FIELDS
        and type(observed_runtime) is dict
        and set(observed_runtime) == _RUNTIME_CAPABILITY_FACT_FIELDS
        and type(expected_socket) is dict
        and set(expected_socket) == _SOCKET_BUFFER_CAPABILITY_FACT_FIELDS
        and type(observed_socket) is dict
        and set(observed_socket) == _SOCKET_BUFFER_CAPABILITY_FACT_FIELDS
        and canonical_json_bytes(expected_parent)
        == canonical_json_bytes(frozen_parent)
        and canonical_json_bytes(expected_runtime)
        == canonical_json_bytes(frozen_runtime)
        and canonical_json_bytes(
            {field: observed_parent[field] for field in compared_parent_fields}
        )
        == canonical_json_bytes(
            {field: expected_parent[field] for field in compared_parent_fields}
        )
        and type(observed_parent.get("self_membership")) is str
        and observed_parent["self_membership"].startswith("0::/")
        and canonical_json_bytes(observed_runtime)
        == canonical_json_bytes(expected_runtime)
        and canonical_json_bytes(expected_socket)
        == canonical_json_bytes(_SOCKET_BUFFER_CAPABILITY_EXPECTED)
        and canonical_json_bytes(observed_socket_exact)
        == canonical_json_bytes(expected_socket_exact)
        and socket_minimums_met
        and document.get("schema") == PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA
        and document.get("phase") == "PRE_CAMPAIGN_ATTEMPT_HOST_CONFORMANCE"
        and document.get("campaign_attempt_id")
        == frozen_context.get("campaign_attempt_id")
        and document.get("cgroup_parent_compared_fields")
        == compared_parent_fields
        and document.get("cgroup_parent_excluded_fields")
        == ["self_membership"]
        and document.get("runtime_capability_compared_fields")
        == list(_RUNTIME_CAPABILITY_FACT_FIELD_ORDER)
        and document.get("socket_buffer_capability_exact_fields")
        == list(_SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS)
        and document.get("socket_buffer_capability_at_least_fields")
        == list(_SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS)
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
        _fail("pre-attempt host conformance success authority changed")
    return raw, document


def _validate_measurement_receipt(
    store: VerificationDurableStoreV180R12R4,
    *,
    attempt: Mapping[str, Any],
    terminal_raw: bytes,
    campaign_attempt_id: str,
) -> dict[str, Any]:
    raw = store.read_stable(
        MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    document = _canonical_object(raw, "measurement launch receipt")
    if set(document) != _RECEIPT_FIELDS:
        _fail("measurement launch-receipt schema changed")
    _plain_content_document(document, identity_field="launch_receipt_id", label="measurement launch receipt")
    invocation = _validate_production_systemd_service_invocation(
        document.get("production_systemd_service_invocation"),
        target="measurement",
        repository_root=str(store.repository_root),
        materialization_terminal_sha256=attempt.get(
            "materialization_terminal_sha256"
        ),
    )
    placement_t1 = _validate_production_runtime_placement_t1(
        document.get("production_runtime_placement_t1"),
        target="measurement",
        invocation=invocation,
    )
    _validate_stream(document.get("child_stdout"), "measurement stdout")
    _validate_stream(document.get("child_stderr"), "measurement stderr")
    empty_stream = {
        "byte_count": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "retained_prefix_hex": "",
        "retained_prefix_truncated": False,
    }
    progress = document.get("progress_observations")
    if type(progress) is not dict or set(progress) != _PROGRESS_NAMES:
        _fail("measurement launch progress schema changed")
    attempt_observation = _file_observation(
        store, MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH, LAUNCH_ARTIFACT_BYTE_CAP
    )
    terminal_observation = _file_observation(store, TERMINAL_RELATIVE_PATH, TERMINAL_BYTE_CAP)
    host_conformance_observation = _file_observation(
        store,
        PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH,
        PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP,
    )
    success_artifact_observations = {
        "evidence_inventory": _file_observation(
            store,
            EVIDENCE_INVENTORY_RELATIVE_PATH,
            EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
        ),
        "execution_closure": _file_observation(
            store,
            EXECUTION_CLOSURE_RELATIVE_PATH,
            EXECUTION_CLOSURE_BYTE_CAP,
        ),
        "os_receipt": _file_observation(
            store, OS_RECEIPT_RELATIVE_PATH, OS_RECEIPT_BUNDLE_BYTE_CAP
        ),
        "ledger_closure": _file_observation(
            store, LEDGER_CLOSURE_RELATIVE_PATH, LEDGER_CLOSURE_BYTE_CAP
        ),
    }
    origin_ns = document.get("monotonic_origin_ns")
    hard_deadline_ns = document.get("hard_deadline_ns")
    campaign_deadline_ns = document.get("campaign_deadline_ns")
    _validate_success_measurement_cgroup_observations(
        document.get("measurement_cgroup_cleanup_observations"),
        campaign_attempt_id=campaign_attempt_id,
    )
    if not (
        document.get("schema") == LAUNCH_RECEIPT_SCHEMA
        and document.get("launch_rule_id") == attempt["launch_rule_id"]
        and document.get("launch_attempt_id") == attempt["launch_attempt_id"]
        and document.get("target") == "measurement"
        and document.get("return_code") == 0
        and document.get("timed_out") is False
        and document.get("same_target_identity_rerun_forbidden") is True
        and document.get("attempt_lock_preserved") is True
        and document.get("address_space_hard_cap_bytes") == ADDRESS_SPACE_HARD_CAP_BYTES
        and document.get("wall_timeout_seconds") == WALL_TIMEOUT_SECONDS
        and type(origin_ns) is int
        and type(hard_deadline_ns) is int
        and type(campaign_deadline_ns) is int
        and 0 < origin_ns < campaign_deadline_ns < hard_deadline_ns
        and hard_deadline_ns - origin_ns
        == WALL_TIMEOUT_SECONDS * NANOSECONDS_PER_SECOND
        and hard_deadline_ns - campaign_deadline_ns
        == CAMPAIGN_CLEANUP_GRACE_SECONDS * NANOSECONDS_PER_SECOND
        and document.get("campaign_cleanup_grace_seconds")
        == CAMPAIGN_CLEANUP_GRACE_SECONDS
        and document.get("termination_grace_seconds") == 10
        and invocation == attempt.get("production_systemd_service_invocation")
        and placement_t1.get("planned_measurement_root_observation", {}).get(
            "campaign_attempt_id"
        )
        == campaign_attempt_id
        and document.get("preauthorization_supervision") is True
        and document.get("campaign_actual_measurement") is False
        and document.get("authorized_child_measurement_execution_attempted")
        is True
        and document.get("authorized_child_measurement_execution_completed")
        is True
        and document.get("producer_free_verification_attempted") is False
        and document.get("producer_free_verification_completed") is False
        and document.get("child_stdout") == empty_stream
        and document.get("child_stderr") == empty_stream
        and all(document.get(key) == "NOT_RUN" for key in (
            "COUNTER_COMPLETENESS_GATE", "WORKLOAD_ECONOMICS_GATE",
            "SCALAR_CALIBRATION_GATE", "BREAK_EVEN_GATE",
        ))
        and document.get("official_execution_allowed") is False
        and document.get("success") is True
        and document.get("failure_type") is None
        and document.get("failure_message") is None
        and progress.get("attempt") == attempt_observation
        and progress.get("receipt") == {"presence": "ABSENT"}
        and progress.get("launch_failure") == {"presence": "ABSENT"}
        and progress.get("runtime_cas") == {"presence": "ABSENT"}
        and progress.get("output_root") == {"presence": "DIRECTORY", "mode": 0o700}
        and progress.get("terminal") == terminal_observation
        and all(
            progress.get(name) == observation
            for name, observation in success_artifact_observations.items()
        )
        and progress.get("measurement_failure") == {"presence": "ABSENT"}
        and progress.get("host_conformance") == host_conformance_observation
        and host_conformance_observation.get("presence") == "REGULAR_FILE"
        and host_conformance_observation.get("mode") == 0o400
        and progress.get("verification") == {"presence": "ABSENT"}
        and progress.get("verification_failure") == {"presence": "ABSENT"}
        and progress.get("retained_replay") == {"presence": "ABSENT"}
        and terminal_observation.get("byte_count") == len(terminal_raw)
        and terminal_observation.get("sha256") == hashlib.sha256(terminal_raw).hexdigest()
    ):
        _fail("measurement launch receipt or streaming observations changed")
    return document


def _validate_exact_service_unit_absence(
    value: Any,
    *,
    unit_name: str,
    client_environment: Mapping[str, str],
    label: str,
) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS:
        _fail(f"{label} keyset changed")
    empty_stream = {
        "byte_count": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "retained_prefix_hex": "",
        "retained_prefix_truncated": False,
    }
    not_found_stream = {
        "byte_count": len(b"not-found\n"),
        "sha256": hashlib.sha256(b"not-found\n").hexdigest(),
        "retained_prefix_hex": b"not-found\n".hex(),
        "retained_prefix_truncated": False,
    }
    for stream, stream_label in (
        (value.get("stdout"), f"{label} stdout"),
        (value.get("stderr"), f"{label} stderr"),
    ):
        _validate_stream(stream, stream_label)
    expected_systemctl_argv = [
        "/usr/bin/systemctl", "--user", "show", "--property=LoadState",
        "--value", unit_name,
    ]
    if not (
        value.get("systemctl_argv") == expected_systemctl_argv
        and value.get("systemctl_environment") == dict(client_environment)
        and value.get("return_code") == 0
        and value.get("timed_out") is False
        and value.get("stdout") == not_found_stream
        and value.get("stderr") == empty_stream
        and value.get("expected_load_state") == "not-found"
        and value.get("unit_absent_after_wait_collect") is True
    ):
        _fail(f"{label} changed")
    return value


def _validate_measurement_service_launch_join(
    store: VerificationDurableStoreV180R12R4,
    *,
    materialization: Mapping[str, Any],
    measurement_attempt: Mapping[str, Any],
    measurement_receipt: Mapping[str, Any],
) -> tuple[bytes, dict[str, Any], bytes, dict[str, Any]]:
    attempt_raw = store.read_stable(
        MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    attempt = _canonical_object(
        attempt_raw, "measurement outer service-launch attempt"
    )
    if frozenset(attempt) != SERVICE_LAUNCH_ATTEMPT_FIELDS:
        _fail("measurement outer service-launch attempt keyset changed")
    attempt_id = _domain_content_document(
        attempt,
        identity_field="service_launch_attempt_id",
        domain=SERVICE_LAUNCH_ATTEMPT_DOMAIN,
        label="measurement outer service-launch attempt",
    )
    invocation = _validate_production_systemd_service_invocation(
        attempt.get("production_systemd_service_invocation"),
        target="measurement",
        repository_root=str(store.repository_root),
        materialization_terminal_sha256=measurement_attempt.get(
            "materialization_terminal_sha256"
        ),
    )
    client_environment = attempt.get("systemd_run_environment")
    runtime_root = (
        client_environment.get("XDG_RUNTIME_DIR")
        if type(client_environment) is dict
        else None
    )
    expected_paths = {
        "attempt": MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
        "receipt": MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
        "launch_failure": MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH,
    }
    origin_ns = attempt.get("monotonic_origin_ns")
    hard_deadline_ns = attempt.get("hard_deadline_ns")
    campaign_deadline_ns = attempt.get("campaign_deadline_ns")
    if not (
        attempt.get("schema") == SERVICE_LAUNCH_ATTEMPT_SCHEMA
        and attempt.get("target") == "measurement"
        and attempt.get("token") == invocation.get("token")
        and attempt.get("unit_name") == invocation.get("unit_name")
        and attempt.get("materialization_terminal_id")
        == materialization.get("materialization_terminal_id")
        and attempt.get("materialization_terminal_sha256")
        == measurement_attempt.get("materialization_terminal_sha256")
        and attempt.get("launch_rule_id")
        == measurement_attempt.get("launch_rule_id")
        and attempt.get("production_systemd_service_invocation")
        == measurement_attempt.get("production_systemd_service_invocation")
        and attempt.get("systemd_run_argv") == invocation.get("systemd_run_argv")
        and type(client_environment) is dict
        and set(client_environment)
        == {"DBUS_SESSION_BUS_ADDRESS", "LC_CTYPE", "XDG_RUNTIME_DIR"}
        and type(runtime_root) is str
        and runtime_root.startswith("/run/user/")
        and runtime_root.removeprefix("/run/user/").isdigit()
        and client_environment.get("DBUS_SESSION_BUS_ADDRESS")
        == f"unix:path={runtime_root}/bus"
        and client_environment.get("LC_CTYPE") == "C.UTF-8"
        and attempt.get("inner_launch_artifact_paths") == expected_paths
        and type(origin_ns) is int
        and type(hard_deadline_ns) is int
        and type(campaign_deadline_ns) is int
        and 0 < origin_ns < campaign_deadline_ns < hard_deadline_ns
        and hard_deadline_ns - origin_ns
        == WALL_TIMEOUT_SECONDS * NANOSECONDS_PER_SECOND
        and hard_deadline_ns - campaign_deadline_ns
        == CAMPAIGN_CLEANUP_GRACE_SECONDS * NANOSECONDS_PER_SECOND
        and attempt.get("attempt_o_excl_before_systemd_run") is True
        and attempt.get("same_target_identity_rerun_forbidden") is True
        and attempt.get("pre_scientific_outer_dispatch") is True
        and attempt.get("campaign_event_or_evidence_document") is False
    ):
        _fail("measurement outer service-launch attempt authority changed")
    _validate_exact_service_unit_absence(
        attempt.get("pre_attempt_unit_absence_observation"),
        unit_name=invocation["unit_name"],
        client_environment=client_environment,
        label="measurement outer pre-attempt service-unit absence",
    )

    receipt_raw = store.read_stable(
        MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    receipt = _canonical_object(
        receipt_raw, "measurement outer service-launch receipt"
    )
    if frozenset(receipt) != SERVICE_LAUNCH_RECEIPT_FIELDS:
        _fail("measurement outer service-launch receipt keyset changed")
    _domain_content_document(
        receipt,
        identity_field="service_launch_receipt_id",
        domain=SERVICE_LAUNCH_RECEIPT_DOMAIN,
        label="measurement outer service-launch receipt",
    )
    unit_absence = receipt.get("collected_unit_absence_observation")
    if (
        type(unit_absence) is not dict
        or frozenset(unit_absence) != SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS
    ):
        _fail("measurement outer service-launch unit-absence keyset changed")
    for stream, label in (
        (receipt.get("systemd_run_stdout"), "systemd-run stdout"),
        (receipt.get("systemd_run_stderr"), "systemd-run stderr"),
        (unit_absence.get("stdout"), "systemctl stdout"),
        (unit_absence.get("stderr"), "systemctl stderr"),
    ):
        _validate_stream(stream, label)
    empty_stream = {
        "byte_count": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "retained_prefix_hex": "",
        "retained_prefix_truncated": False,
    }
    not_found_stream = {
        "byte_count": len(b"not-found\n"),
        "sha256": hashlib.sha256(b"not-found\n").hexdigest(),
        "retained_prefix_hex": b"not-found\n".hex(),
        "retained_prefix_truncated": False,
    }
    measurement_attempt_raw = canonical_json_bytes(measurement_attempt)
    measurement_receipt_raw = canonical_json_bytes(measurement_receipt)
    regular_attempt = {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": len(measurement_attempt_raw),
        "sha256": hashlib.sha256(measurement_attempt_raw).hexdigest(),
    }
    regular_receipt = {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": len(measurement_receipt_raw),
        "sha256": hashlib.sha256(measurement_receipt_raw).hexdigest(),
    }
    expected_systemctl_argv = [
        "/usr/bin/systemctl", "--user", "show", "--property=LoadState",
        "--value", invocation["unit_name"],
    ]
    if not (
        receipt.get("schema") == SERVICE_LAUNCH_RECEIPT_SCHEMA
        and receipt.get("target") == "measurement"
        and receipt.get("service_launch_attempt_id") == attempt_id
        and receipt.get("token") == invocation.get("token")
        and receipt.get("unit_name") == invocation.get("unit_name")
        and receipt.get("production_systemd_service_invocation") == invocation
        and receipt.get("systemd_run_return_code") == 0
        and receipt.get("systemd_run_timed_out") is False
        and receipt.get("systemd_run_stdout") == empty_stream
        and receipt.get("systemd_run_stderr") == empty_stream
        and unit_absence.get("systemctl_argv") == expected_systemctl_argv
        and unit_absence.get("systemctl_environment") == client_environment
        and unit_absence.get("return_code") == 0
        and unit_absence.get("timed_out") is False
        and unit_absence.get("stdout") == not_found_stream
        and unit_absence.get("stderr") == empty_stream
        and unit_absence.get("expected_load_state") == "not-found"
        and unit_absence.get("unit_absent_after_wait_collect") is True
        and receipt.get("inner_launch_attempt_fact") == regular_attempt
        and receipt.get("inner_launch_receipt_fact") == regular_receipt
        and receipt.get("inner_launch_failure_fact") == {"presence": "ABSENT"}
        and receipt.get("inner_launch_attempt_id")
        == measurement_attempt.get("launch_attempt_id")
        and receipt.get("inner_launch_terminal_kind") == "RECEIPT"
        and receipt.get("inner_launch_terminal_id")
        == measurement_receipt.get("launch_receipt_id")
        and measurement_receipt.get("launch_attempt_id")
        == measurement_attempt.get("launch_attempt_id")
        and measurement_receipt.get("target") == "measurement"
        and measurement_receipt.get("success") is True
        and receipt.get("exact_attempt_terminal_join") is True
        and receipt.get("attempt_lock_preserved") is True
        and receipt.get("same_target_identity_rerun_forbidden") is True
        and receipt.get("pre_scientific_outer_dispatch") is True
        and receipt.get("campaign_event_or_evidence_document") is False
        and receipt.get("success") is True
        and receipt.get("failure_type") is None
        and receipt.get("failure_message") is None
    ):
        _fail("measurement outer service-launch receipt/inner join changed")
    return attempt_raw, attempt, receipt_raw, receipt


def _validate_terminal(
    raw: bytes,
    anchors: _FrozenAnchors,
    *,
    expected_materialization_terminal_id: str,
    expected_measurement_launch_attempt_id: str,
    expected_precompiled_source_bundle_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    terminal = _canonical_object(raw, "pending campaign terminal")
    if frozenset(terminal) != independent_verifier.TERMINAL_FIELDS:
        _fail("pending campaign terminal exact keyset changed")
    payload = dict(terminal)
    identity = _cid(payload.pop("campaign_measurement_terminal_id", None), "campaign terminal ID")
    if identity != domains.extension_content_id_v180r12r4(
        domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R4_DOMAIN, payload
    ):
        _fail("pending campaign terminal content identity changed")
    closure = terminal.get("campaign_measurement_ledger")
    if type(closure) is not dict:
        _fail("pending campaign terminal lacks its embedded ledger")
    closure_raw = canonical_json_bytes(closure)
    if not (
        terminal.get("schema") == independent_verifier.TERMINAL_SCHEMA
        and terminal.get("schema_version") == SCHEMA_VERSION
        and terminal.get("protocol_id") == anchors.protocol_id
        and terminal.get("authorization_id") == anchors.authorization_id
        and terminal.get("authorization_evidence_id")
        == anchors.authorization_evidence_id
        and terminal.get("prelaunch_materialization_terminal_id")
        == expected_materialization_terminal_id
        and terminal.get("prelaunch_launch_manifest_sha256")
        == anchors.manifest_sha256
        and terminal.get("precompiled_source_bundle_sha256")
        == expected_precompiled_source_bundle_sha256
        and terminal.get("prelaunch_launch_rule_id") == anchors.launch_rule_id
        and terminal.get("measurement_launch_attempt_id")
        == expected_measurement_launch_attempt_id
        and terminal.get("attempt_id") == closure.get("attempt_id")
        and terminal.get("subject_id") == closure.get("subject_id")
        and terminal.get("campaign_ledger_closure_id") == closure.get("campaign_ledger_closure_id")
        and terminal.get("campaign_ledger_closure_byte_count") == len(closure_raw)
        and terminal.get("campaign_ledger_closure_sha256") == hashlib.sha256(closure_raw).hexdigest()
        and terminal.get("event_count") == 625
        and terminal.get("evidence_document_count") == 328
        and terminal.get("os_receipt_document_count") == 12
        and terminal.get("campaign_path_receipt_count") == 9
        and terminal.get("campaign_counter_record_count") == 9
        and terminal.get("campaign_work_vector_count") == 1
        and terminal.get("campaign_comparison_vector_count") == 1
        and terminal.get("campaign_projection_proof_count") == 1
        and terminal.get("campaign_native_zero_attestation_count") == 1
        and terminal.get("predecessor_occurrence_authoritative_receipt_count") == 90
        and terminal.get("successor_campaign_authoritative_receipt_count") == 9
        and terminal.get("combined_successor_authoritative_receipt_count") == 99
        and terminal.get("authoritative_receipt_arithmetic_90_plus_9_equals_99") is True
        and terminal.get("independent_verification_present") is False
        and terminal.get("V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS") == "PENDING_INDEPENDENT_REPLAY"
        and terminal.get("COUNTER_COMPLETENESS_GATE") == "PENDING_INDEPENDENT_REPLAY"
        and all(terminal.get(key) == "NOT_RUN" for key in (
            "WORKLOAD_ECONOMICS_GATE", "SCALAR_CALIBRATION_GATE",
            "BREAK_EVEN_GATE", "OFFICIAL_EXECUTION_GATE",
        ))
        and terminal.get("v180r13_weight_agnostic_economics_input_ready") is False
        and terminal.get("official_scalar_cost") is None
        and terminal.get("official_N_break_even") is None
        and terminal.get("official_execution_allowed") is False
        and terminal.get("scientific_success_claimed") is False
        and terminal.get("output_bytes_fixed_point") == len(raw)
        and closure.get("protocol_id") == anchors.protocol_id
        and closure.get("authorization_id") == anchors.authorization_id
        and closure.get("max_event_count") == MAX_EVENT_COUNT
        and closure.get("max_event_byte_count") == MAX_EVENT_BYTE_COUNT
        and closure.get("max_ledger_byte_count") == MAX_LEDGER_BYTE_COUNT
    ):
        _fail("pending terminal one-shot context, denominator, or gate changed")
    documents = closure.get("evidence_documents")
    if type(documents) is not list:
        _fail("pending terminal evidence inventory changed")
    subjects = [
        row for row in documents
        if type(row) is dict
        and row.get("schema") == "acfqp.campaign_measurement_subject_result.v180r12r4"
    ]
    if len(subjects) != 1:
        _fail("pending terminal subject-result denominator changed")
    subject = subjects[0]
    if not (
        subject.get("subject_result_id") == terminal.get("subject_id")
        and subject.get("protocol_id") == anchors.protocol_id
        and subject.get("authorization_id") == anchors.authorization_id
        and subject.get("authorization_evidence_id")
        == anchors.authorization_evidence_id
        and subject.get("attempt_id") == terminal.get("attempt_id")
        and subject.get("execution_slot_id") == anchors.execution_slot_id
        and subject.get("logical_occurrence_id") == anchors.logical_occurrence_id
        and subject.get("execution_nonce") == anchors.execution_nonce
        and subject.get("prelaunch_materialization_terminal_id")
        == expected_materialization_terminal_id
        and subject.get("prelaunch_launch_manifest_sha256")
        == anchors.manifest_sha256
        and subject.get("prelaunch_launch_rule_id") == anchors.launch_rule_id
        and subject.get("measurement_launch_attempt_id")
        == expected_measurement_launch_attempt_id
    ):
        _fail("pending terminal subject execution context changed")
    return terminal, subject


def _validate_success_artifact_facts(
    terminal: Mapping[str, Any],
    artifacts: Mapping[str, bytes],
) -> None:
    expected_keys = {
        "evidence_inventory", "execution_closure", "os_receipt", "ledger_closure"
    }
    if set(artifacts) != expected_keys:
        _fail("verification success-artifact keyset changed")
    parsed = {
        key: _canonical_object(raw, f"separate {key} artifact")
        for key, raw in artifacts.items()
    }
    inventory = parsed["evidence_inventory"]
    inventory_payload = dict(inventory)
    inventory_id = _cid(
        inventory_payload.pop("campaign_evidence_inventory_bundle_id", None),
        "evidence inventory bundle ID",
    )
    os_bundle = parsed["os_receipt"]
    os_payload = dict(os_bundle)
    os_bundle_id = _cid(
        os_payload.pop("campaign_os_receipt_bundle_id", None),
        "OS receipt bundle ID",
    )
    execution = parsed["execution_closure"]
    ledger_closure = parsed["ledger_closure"]
    if not (
        frozenset(inventory) == independent_verifier.EVIDENCE_INVENTORY_BUNDLE_FIELDS
        and inventory.get("schema") == independent_verifier.EVIDENCE_INVENTORY_BUNDLE_SCHEMA
        and inventory_id == domains.extension_content_id_v180r12r4(
            domains.CONSTRUCTION_K7_CAMPAIGN_EVIDENCE_INVENTORY_BUNDLE_V180R12R4_DOMAIN,
            inventory_payload,
        )
        and frozenset(os_bundle) == independent_verifier.OS_RECEIPT_BUNDLE_FIELDS
        and os_bundle.get("schema") == independent_verifier.OS_RECEIPT_BUNDLE_SCHEMA
        and os_bundle_id == domains.extension_content_id_v180r12r4(
            domains.CONSTRUCTION_K7_CAMPAIGN_OS_RECEIPT_BUNDLE_V180R12R4_DOMAIN,
            os_payload,
        )
        and execution.get("schema") == "acfqp.campaign_execution_closure.v180r12r4"
        and ledger_closure.get("schema")
        == "acfqp.campaign_measurement_ledger_closure.v180r12r4"
    ):
        _fail("verification separate success-artifact schema or identity changed")
    context = (
        terminal.get("protocol_id"), terminal.get("authorization_id"),
        terminal.get("attempt_id"),
    )
    if any(
        (document.get("protocol_id"), document.get("authorization_id"), document.get("attempt_id"))
        != context
        for document in parsed.values()
    ):
        _fail("verification separate success-artifact context changed")
    facts = (
        ("campaign_evidence_inventory_bundle", inventory_id, artifacts["evidence_inventory"]),
        ("campaign_execution_closure", execution.get("campaign_execution_closure_id"), artifacts["execution_closure"]),
        ("campaign_os_receipt_bundle", os_bundle_id, artifacts["os_receipt"]),
        ("campaign_ledger_closure", ledger_closure.get("campaign_ledger_closure_id"), artifacts["ledger_closure"]),
    )
    if any(
        terminal.get(f"{prefix}_id") != _cid(identity, f"{prefix} identity")
        or terminal.get(f"{prefix}_byte_count") != len(raw)
        or terminal.get(f"{prefix}_sha256") != hashlib.sha256(raw).hexdigest()
        for prefix, identity, raw in facts
    ):
        _fail("verification terminal-to-separate-artifact fact join changed")


class _VerificationWatchdog:
    __slots__ = (
        "seconds",
        "absolute_deadline_ns",
        "_previous_handler",
        "armed",
        "cancel_attempted",
        "cancel_succeeded",
        "ignore_attempted",
        "ignore_succeeded",
        "handler_restore_attempted",
        "handler_restore_succeeded",
        "_cleanup_error_0",
        "_cleanup_error_1",
        "_cleanup_error_2",
    )

    def __init__(self, seconds: int) -> None:
        self.seconds = _positive(seconds, "verification watchdog seconds")
        self.absolute_deadline_ns: int | None = None
        self._previous_handler: Any = None
        self.armed = False
        self.cancel_attempted = False
        self.cancel_succeeded = False
        self.ignore_attempted = False
        self.ignore_succeeded = False
        self.handler_restore_attempted = False
        self.handler_restore_succeeded = False
        # These slots are allocated before the emergency reserve.  The signal
        # neutralization path only stores references into them: it does not
        # append to a growing container or format an exception while memory is
        # still constrained.
        self._cleanup_error_0: BaseException | None = None
        self._cleanup_error_1: BaseException | None = None
        self._cleanup_error_2: BaseException | None = None

    @staticmethod
    def _expired(_signum: int, _frame: Any) -> NoReturn:
        raise V180R12R4VerificationTimeout(
            "producer-free independent verification exceeded its wall deadline"
        )

    def bind_absolute_deadline(self, deadline_ns: int) -> None:
        if (
            self.armed
            or self.absolute_deadline_ns is not None
            or type(deadline_ns) is not int
            or deadline_ns <= 0
        ):
            _fail("verification watchdog absolute deadline changed")
        self.absolute_deadline_ns = deadline_ns

    def arm(self) -> None:
        if self.armed or self.handler_restore_attempted:
            _fail("verification watchdog lifecycle was reused")
        before = signal.getitimer(signal.ITIMER_REAL)
        if before != (0.0, 0.0):
            _fail("verification runner inherited an active real-time timer")
        self._previous_handler = signal.getsignal(signal.SIGALRM)
        duration = float(self.seconds)
        if self.absolute_deadline_ns is not None:
            remaining_ns = self.absolute_deadline_ns - time.clock_gettime_ns(
                time.CLOCK_MONOTONIC
            )
            if remaining_ns <= 0:
                raise V180R12R4VerificationTimeout(
                    "producer-free independent verification reached its shared "
                    "campaign deadline before watchdog arm"
                )
            duration = min(duration, remaining_ns / NANOSECONDS_PER_SECOND)
        signal.signal(signal.SIGALRM, self._expired)
        signal.setitimer(signal.ITIMER_REAL, duration)
        self.armed = True

    def _first_cleanup_error(self) -> BaseException | None:
        if self._cleanup_error_0 is not None:
            return self._cleanup_error_0
        if self._cleanup_error_1 is not None:
            return self._cleanup_error_1
        return self._cleanup_error_2

    def neutralize(self) -> None:
        """Cancel the timer and ignore SIGALRM before any failure formatting."""

        if self._previous_handler is None and not self.armed:
            self.cancel_attempted = True
            self.cancel_succeeded = True
            self.ignore_attempted = True
            self.ignore_succeeded = True
            return
        if not self.cancel_attempted:
            self.cancel_attempted = True
            try:
                signal.setitimer(signal.ITIMER_REAL, 0.0)
                self.cancel_succeeded = True
            except BaseException as error:  # hostile platform observation
                if self._cleanup_error_0 is None:
                    self._cleanup_error_0 = error
                elif self._cleanup_error_1 is None:
                    self._cleanup_error_1 = error
                elif self._cleanup_error_2 is None:
                    self._cleanup_error_2 = error
        if not self.ignore_attempted:
            self.ignore_attempted = True
            try:
                signal.signal(signal.SIGALRM, signal.SIG_IGN)
                self.ignore_succeeded = True
            except BaseException as error:  # hostile platform observation
                if self._cleanup_error_0 is None:
                    self._cleanup_error_0 = error
                elif self._cleanup_error_1 is None:
                    self._cleanup_error_1 = error
                elif self._cleanup_error_2 is None:
                    self._cleanup_error_2 = error
        self.armed = False

    def restore(self) -> None:
        if not self.cancel_attempted or not self.ignore_attempted:
            self.neutralize()
        if not self.handler_restore_attempted:
            self.handler_restore_attempted = True
            try:
                if self._previous_handler is not None:
                    signal.signal(signal.SIGALRM, self._previous_handler)
                self.handler_restore_succeeded = True
            except BaseException as error:  # hostile platform observation
                if self._cleanup_error_0 is None:
                    self._cleanup_error_0 = error
                elif self._cleanup_error_1 is None:
                    self._cleanup_error_1 = error
                elif self._cleanup_error_2 is None:
                    self._cleanup_error_2 = error

    @property
    def teardown_completed(self) -> bool:
        return (
            self.cancel_succeeded
            and self.ignore_succeeded
            and self.handler_restore_succeeded
        )

    def teardown(self) -> None:
        self.neutralize()
        self.restore()
        error = self._first_cleanup_error()
        if error is not None:
            raise V180R12R4VerificationRunnerError(
                "verification watchdog teardown failed"
            ) from error

    def cleanup_observation(self) -> dict[str, Any]:
        bounded: list[dict[str, str]] = []
        for error in (
            self._cleanup_error_0,
            self._cleanup_error_1,
            self._cleanup_error_2,
        ):
            if error is None:
                continue
            try:
                BaseException.__setattr__(error, "__traceback__", None)
            except BaseException:
                pass
            kind, message = _safe_error(error)
            bounded.append(
                {
                    "failure_type": kind,
                    "failure_message": message or "UNAVAILABLE_ERROR",
                }
            )
        return {
            "cancel_attempted": self.cancel_attempted,
            "cancel_succeeded": self.cancel_succeeded,
            "ignore_attempted": self.ignore_attempted,
            "ignore_succeeded": self.ignore_succeeded,
            "handler_restore_attempted": self.handler_restore_attempted,
            "handler_restore_succeeded": self.handler_restore_succeeded,
            "teardown_completed": self.teardown_completed,
            "secondary_observations": bounded,
        }


def _failure_observation(
    store: VerificationDurableStoreV180R12R4,
    relative_path: str,
    *,
    byte_cap: int,
    kind: str,
) -> dict[str, Any]:
    if kind not in {"FILE", "DIRECTORY"}:
        _fail("failure observation kind changed")
    _positive(byte_cap, "failure observation byte cap")
    row: dict[str, Any] = {
        "relative_path": relative_path,
        "kind": kind,
        "state": "ABSENT",
        "mode": None,
        "nlink": None,
        "byte_count": None,
        "sha256": None,
        "directory_entries": None,
        "read_error_type": None,
        "read_error_message": None,
    }
    parent_fd = -1
    try:
        parent_fd, name = store._open_parent(relative_path)
        try:
            metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return row
        row["mode"] = metadata.st_mode
        row["nlink"] = metadata.st_nlink
        expected_type = stat.S_ISREG if kind == "FILE" else stat.S_ISDIR
        if stat.S_ISLNK(metadata.st_mode) or not expected_type(metadata.st_mode):
            row["state"] = "LINKED_OR_NONREGULAR"
            return row
        if kind == "DIRECTORY":
            directory_fd = -1
            try:
                directory_fd = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=parent_fd,
                )
                directory_before = os.fstat(directory_fd)
                names: list[str] = []
                total_name_bytes = 0
                cap_exceeded = False
                with os.scandir(directory_fd) as iterator:
                    for entry in iterator:
                        entry_name = entry.name
                        if type(entry_name) is not str:
                            _fail("failure directory entry name type changed")
                        encoded_name = entry_name.encode("utf-8")
                        if (
                            len(names)
                            >= VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP
                            or total_name_bytes + len(encoded_name)
                            > VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP
                        ):
                            cap_exceeded = True
                            break
                        names.append(entry_name)
                        total_name_bytes += len(encoded_name)
                directory_after = os.fstat(directory_fd)
                fields = (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_nlink",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
                if any(
                    getattr(directory_before, field)
                    != getattr(directory_after, field)
                    for field in fields
                ):
                    _fail("failure directory identity changed during observation")
            except BaseException as error:
                error_type, message = _safe_error(error)
                row["state"] = "READ_ERROR"
                row["read_error_type"] = error_type
                row["read_error_message"] = message[:512] or "UNAVAILABLE_ERROR"
                return row
            finally:
                if directory_fd >= 0:
                    os.close(directory_fd)
            if cap_exceeded:
                row["state"] = "READ_ERROR"
                row["read_error_type"] = "DIRECTORY_OBSERVATION_CAP_EXCEEDED"
                row["read_error_message"] = "bounded directory observation exceeded"
                return row
            names.sort()
            row["state"] = "PRESENT"
            row["directory_entries"] = names
            return row
        if metadata.st_nlink != 1:
            row["state"] = "LINKED_OR_NONREGULAR"
            return row
        row["byte_count"] = metadata.st_size
        if metadata.st_size > byte_cap:
            row["state"] = "READ_ERROR"
            row["read_error_type"] = "ARTIFACT_BYTE_CAP_EXCEEDED"
            row["read_error_message"] = (
                "failure artifact exceeds its preregistered observation byte cap"
            )
            return row
        descriptor = -1
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
            before = os.fstat(descriptor)
            fields = (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_nlink",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size > byte_cap
                or any(
                    getattr(metadata, field) != getattr(before, field)
                    for field in fields
                )
            ):
                _fail("failure artifact identity changed before streaming read")
            digest = hashlib.sha256()
            observed_byte_count = 0
            remaining = before.st_size
            while remaining:
                chunk = os.read(
                    descriptor,
                    min(
                        VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES,
                        remaining,
                    ),
                )
                if not chunk:
                    _fail("failure artifact ended before its observed exact size")
                digest.update(chunk)
                observed_byte_count += len(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                _fail("failure artifact grew during streaming observation")
            after = os.fstat(descriptor)
            if any(
                getattr(before, field) != getattr(after, field)
                for field in fields
            ):
                _fail("failure artifact identity changed during streaming read")
        except BaseException as error:
            error_type, message = _safe_error(error)
            row["state"] = "READ_ERROR"
            row["read_error_type"] = error_type
            row["read_error_message"] = message[:512] or "UNAVAILABLE_ERROR"
            return row
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        row["state"] = "PRESENT"
        row["byte_count"] = observed_byte_count
        row["sha256"] = digest.hexdigest()
        return row
    except FileNotFoundError:
        return row
    except BaseException as error:
        kind, message = _safe_error(error)
        row["state"] = "READ_ERROR"
        row["read_error_type"] = kind
        row["read_error_message"] = message[:512] or "UNAVAILABLE_ERROR"
        return row
    finally:
        if parent_fd >= 0:
            os.close(parent_fd)


def _verification_failure_bytes(
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str | None,
    verification_launch_attempt_id: str,
    error: BaseException,
    observations: Sequence[Mapping[str, Any]],
    reserve_allocated: bool,
    reserve_released: bool,
    watchdog_armed: bool,
    watchdog_cleanup_observation: Mapping[str, Any],
) -> bytes:
    _cid(protocol_id, "verification failure protocol ID")
    _cid(authorization_id, "verification failure authorization ID")
    error_type, message = _safe_error(error)
    rows = [dict(row) for row in observations]
    expected_paths = [
        row[0] for row in VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
    ]
    if (
        any(set(row) != _FAILURE_OBSERVATION_FIELDS for row in rows)
        or [row["relative_path"] for row in rows]
        != expected_paths
        or len(rows) != VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROW_COUNT
    ):
        _fail("verification failure observation closure changed")
    failure_path_rows = [
        row
        for row in rows
        if row["relative_path"] == VERIFICATION_FAILURE_RELATIVE_PATH
    ]
    if len(failure_path_rows) != 1 or failure_path_rows[0]["state"] != "ABSENT":
        _fail("verification failure path was not absent at its observation boundary")
    if attempt_id is not None:
        _cid(attempt_id, "observed campaign attempt ID")
    _cid(verification_launch_attempt_id, "verification launch-attempt ID")
    watchdog_row = dict(watchdog_cleanup_observation)
    secondary_rows = watchdog_row.get("secondary_observations")
    if not (
        set(watchdog_row) == _WATCHDOG_CLEANUP_FIELDS
        and type(secondary_rows) is list
        and len(secondary_rows) <= 3
        and all(
            type(row) is dict and set(row) == _WATCHDOG_SECONDARY_FIELDS
            for row in secondary_rows
        )
    ):
        _fail("watchdog cleanup observation schema changed")
    safe_message = message or "UNAVAILABLE_ERROR"
    payload = {
        "schema": VERIFICATION_FAILURE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "verification_launch_attempt_id": verification_launch_attempt_id,
        "failure_code": "INDEPENDENT_VERIFICATION_FAILURE",
        "phase": "INDEPENDENT_VERIFICATION",
        "operation_id": verification_launch_attempt_id,
        "last_event_id": None,
        "completed_event_count": 0,
        "failure_type": error_type,
        "message": safe_message,
        "message_sha256": hashlib.sha256(_safe_utf8(safe_message)).hexdigest(),
        "process_may_remain": False,
        "output_may_exist": any(row["state"] != "ABSENT" for row in rows),
        "partial_artifact_observations": rows,
        "partial_artifact_observation_boundary": (
            VERIFICATION_FAILURE_OBSERVATION_BOUNDARY
        ),
        "cgroup_failure_observation": None,
        "same_identity_rerun_forbidden": True,
        "successful_ledger_claimed": False,
        "counter_records_issued": False,
        "failure_memory_reserve_bytes": FAILURE_EMERGENCY_RESERVE_BYTES,
        "failure_memory_reserve_allocated": reserve_allocated,
        "failure_memory_reserve_released_before_failure": reserve_released,
        "watchdog_was_armed": watchdog_armed,
        "watchdog_cleanup_observation": watchdog_row,
        "traceback_retained": False,
        "campaign_actual_measurement": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "CAMPAIGN_CLEANUP_GRACE_SECONDS": CAMPAIGN_CLEANUP_GRACE_SECONDS,
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "verification_failure_id": domains.extension_content_id_v180r12r4(
            domains.CONSTRUCTION_K7_FAILURE_V180R12R4_DOMAIN, payload
        ),
    }
    if frozenset(document) != VERIFICATION_FAILURE_FIELDS:
        _fail("verification failure exact keyset changed")
    raw = canonical_json_bytes(document)
    if not 0 < len(raw) <= FAILURE_EMERGENCY_RESERVE_BYTES:
        _fail("verification failure exceeds its emergency-memory envelope")
    return raw


def _assert_verification_document(document: Mapping[str, Any]) -> None:
    payload = dict(document)
    identity = _cid(
        payload.pop("campaign_measurement_verification_id", None),
        "campaign measurement verification ID",
    )
    if not (
        frozenset(document) == independent_verifier.VERIFICATION_FIELDS
        and document.get("schema") == independent_verifier.VERIFICATION_SCHEMA
        and identity
        == domains.extension_content_id_v180r12r4(
            domains.CONSTRUCTION_K7_VERIFICATION_V180R12R4_DOMAIN,
            payload,
        )
        and document.get("V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS") == "PASS"
        and document.get("COUNTER_COMPLETENESS_GATE") == "PASS"
        and document.get(
            "production_systemd_service_invocation_independently_replayed"
        )
        is True
        and document.get(
            "production_runtime_placement_t1_t2_t3_independently_replayed"
        )
        is True
        and document.get(
            "pre_scientific_outer_service_launch_join_independently_replayed"
        )
        is True
        and document.get(
            "pre_attempt_host_conformance_independently_replayed"
        )
        is True
        and document.get(
            "pre_attempt_host_conformance_is_campaign_event_or_counter_record"
        )
        is False
        and all(document.get(key) == "NOT_RUN" for key in (
            "WORKLOAD_ECONOMICS_GATE", "SCALAR_CALIBRATION_GATE",
            "BREAK_EVEN_GATE", "OFFICIAL_EXECUTION_GATE",
        ))
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
        and document.get("scientific_success_claimed") is False
    ):
        _fail("independent verification gate boundary changed")


def _require_current_precreate_matrix(
    store: VerificationDurableStoreV180R12R4,
) -> None:
    for relative in (
        VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH,
        VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH,
        VERIFICATION_RELATIVE_PATH,
        VERIFICATION_FAILURE_RELATIVE_PATH,
        RETAINED_REPLAY_RELATIVE_PATH,
    ):
        if store.lexists(relative):
            raise V180R12R4VerificationReplayForbidden(
                "verification identity already has receipt, failure, or output progress"
            )
    required = (
        VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH,
        MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
        MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
        MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
        MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
        MATERIALIZATION_TERMINAL_RELATIVE_PATH,
        EVIDENCE_INVENTORY_RELATIVE_PATH,
        EXECUTION_CLOSURE_RELATIVE_PATH,
        OS_RECEIPT_RELATIVE_PATH,
        LEDGER_CLOSURE_RELATIVE_PATH,
        TERMINAL_RELATIVE_PATH,
    )
    if any(not store.lexists(relative) for relative in required):
        _fail("VERIFICATION_ATTEMPT_PRECREATE prerequisite is absent")
    if (
        store.lexists(MEASUREMENT_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH)
        or store.lexists(MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH)
        or store.lexists(MEASUREMENT_FAILURE_RELATIVE_PATH)
    ):
        _fail("verification predecessor has one durable failure")
    if store.lexists(RUNTIME_CAS_ROOT_RELATIVE_PATH):
        _fail("runtime CAS is present at VERIFICATION_ATTEMPT_PRECREATE")
    output = store.observe(OUTPUT_ROOT_RELATIVE_PATH, TERMINAL_BYTE_CAP)
    if output != {"presence": "DIRECTORY", "mode": 0o700}:
        _fail("verification output root is absent, linked, or mode-drifting")


def _validate_native_zero_precompiled_source_rows_v180r12r4(
    value: Any,
) -> tuple[dict[str, Any], ...]:
    """Thaw only the exact bootstrap-derived measured application projection."""

    if type(value) is not tuple or not value:
        _fail("verification bootstrap native-zero source rows changed")
    rows: list[dict[str, Any]] = []
    for supplied in value:
        if (
            type(supplied) is not types.MappingProxyType
            or tuple(supplied) != NATIVE_ZERO_PRECOMPILED_SOURCE_ROW_FIELDS
        ):
            _fail("verification bootstrap native-zero source row schema changed")
        row = {key: supplied[key] for key in NATIVE_ZERO_PRECOMPILED_SOURCE_ROW_FIELDS}
        kind = row["source_kind"]
        name = row["name"]
        source_path = row["source_path"]
        if (
            kind not in {"MODULE", "TARGET"}
            or type(name) is not str
            or not name
            or type(source_path) is not str
            or not source_path
            or source_path.startswith("/")
            or "\\" in source_path
            or any(part in {"", ".", ".."} for part in source_path.split("/"))
            or type(row["is_package"]) is not bool
            or type(row["marshal_byte_count"]) is not int
            or row["marshal_byte_count"] <= 0
            or type(row["marshal_sha256"]) is not str
            or _SHA256.fullmatch(row["marshal_sha256"]) is None
        ):
            _fail("verification bootstrap native-zero source row value changed")
        if kind == "MODULE":
            if (
                name != "acfqp"
                and not name.startswith("acfqp.")
            ) or not source_path.startswith("src/acfqp/"):
                _fail("verification bootstrap application-module scope changed")
        elif (
            name not in NATIVE_ZERO_MEASURED_TARGET_SOURCE_PATHS
            or source_path != NATIVE_ZERO_MEASURED_TARGET_SOURCE_PATHS[name]
            or row["is_package"] is not False
        ):
            _fail("verification bootstrap measured-target scope changed")
        rows.append(row)
    coordinates = [(row["source_kind"], row["name"]) for row in rows]
    if (
        coordinates != sorted(set(coordinates))
        or not any(row["source_kind"] == "MODULE" for row in rows)
        or {
            row["name"] for row in rows if row["source_kind"] == "TARGET"
        }
        != set(NATIVE_ZERO_MEASURED_TARGET_SOURCE_PATHS)
    ):
        _fail("verification bootstrap native-zero source population changed")
    return tuple(rows)


def _validate_verified_external_context_v180r12r4(
    value: Mapping[str, Any],
) -> types.MappingProxyType:
    """Accept only the immutable context already consumed by the bootstrap."""

    if (
        type(value) is not types.MappingProxyType
        or tuple(value) != VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS
    ):
        _fail("verification requires the exact bootstrap-verified immutable context")
    repository_text = value["repository_root"]
    c_pre_text = value["c_pre_root"]
    if (
        type(repository_text) is not str
        or not Path(repository_text).is_absolute()
        or str(Path(repository_text)) != repository_text
        or c_pre_text != str(Path(repository_text) / PRELAUNCH_ROOT_RELATIVE_PATH)
        or value["schema"] != VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA
        or value["target"] != "verification"
        or value["actor_role"] != "VERIFIER"
        or type(value["production_systemd_service_invocation"])
        is not types.MappingProxyType
        or type(value["production_runtime_placement_t1"])
        is not types.MappingProxyType
        or type(value["production_systemd_service_invocation"].get("token_input"))
        is not types.MappingProxyType
        or any(
            type(value["production_runtime_placement_t1"].get(field_name))
            is not types.MappingProxyType
            for field_name in (
                "delegated_parent_fd_fact", "cgroup2_mount_fd_fact",
                "source_service_fd_fact", "planned_measurement_root_observation",
            )
        )
        or value["inherited_fd_roles"] != VERIFICATION_EXTERNAL_FD_ROLE_ROWS
        or type(value["target_payload"]) is not types.MappingProxyType
        or dict(value["target_payload"])
        or value["one_shot"] is not True
        or value["context_consumed_once"] is not True
    ):
        _fail("verification bootstrap context role/path/FD boundary changed")
    for key in (
        "prelaunch_materialization_terminal_id",
        "prelaunch_materialization_terminal_sha256",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "current_launch_attempt_id",
        "current_launch_attempt_sha256",
        "measurement_launch_attempt_id",
        "measurement_launch_attempt_sha256",
        "protocol_id",
        "protocol_sha256",
        "authorization_id",
        "authorization_sha256",
        "authorization_evidence_id",
        "authorization_evidence_sha256",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
        "campaign_attempt_id",
        "precompiled_source_bundle_sha256",
        "external_launch_context_sha256",
    ):
        _cid(value[key], f"verified external context {key}")
    for key in (
        "prelaunch_materialization_terminal_byte_count",
        "current_launch_attempt_byte_count",
        "measurement_launch_attempt_byte_count",
        "protocol_byte_count",
        "authorization_byte_count",
        "authorization_evidence_byte_count",
    ):
        _positive(value[key], f"verified external context {key}")
    origin_ns = value["monotonic_origin_ns"]
    hard_deadline_ns = value["hard_deadline_ns"]
    campaign_deadline_ns = value["campaign_deadline_ns"]
    if not (
        type(origin_ns) is int
        and type(hard_deadline_ns) is int
        and type(campaign_deadline_ns) is int
        and 0 < origin_ns < campaign_deadline_ns < hard_deadline_ns
        and hard_deadline_ns - origin_ns
        == WALL_TIMEOUT_SECONDS * NANOSECONDS_PER_SECOND
        and hard_deadline_ns - campaign_deadline_ns
        == CAMPAIGN_CLEANUP_GRACE_SECONDS * NANOSECONDS_PER_SECOND
    ):
        _fail("verification bootstrap shared monotonic deadlines changed")
    prereg_commit = value["prereg_commit_id"]
    _validate_native_zero_precompiled_source_rows_v180r12r4(
        value["native_zero_precompiled_source_rows"]
    )
    context_invocation = _validate_production_systemd_service_invocation(
        value["production_systemd_service_invocation"],
        target="verification",
        repository_root=repository_text,
        materialization_terminal_sha256=value[
            "prelaunch_materialization_terminal_sha256"
        ],
    )
    _validate_production_runtime_placement_t1(
        value["production_runtime_placement_t1"],
        target="verification",
        invocation=context_invocation,
    )
    cgroup = value["cgroup_parent_fact"]
    capability = value["runtime_capability_fact"]
    if (
        type(prereg_commit) is not str
        or _COMMIT.fullmatch(prereg_commit) is None
        or type(cgroup) is not types.MappingProxyType
        or set(cgroup) != _CGROUP_PARENT_FACT_FIELDS
        or cgroup.get("schema") != "acfqp.v180r12r4_cgroup_parent_fact.v1"
        or type(capability) is not types.MappingProxyType
        or set(capability) != _RUNTIME_CAPABILITY_FACT_FIELDS
        or capability.get("schema")
        != "acfqp.v180r12r4_runtime_capability_fact.v1"
        or capability.get("admitted") is not True
    ):
        _fail("verification bootstrap context frozen fact boundary changed")
    expected_attempt_id = domains.derive_campaign_measurement_attempt_id_v180r12r4(
        protocol_id=value["protocol_id"],
        authorization_id=value["authorization_id"],
        authorization_evidence_id=value["authorization_evidence_id"],
        campaign_measurement_execution_slot_id=value[
            "campaign_measurement_execution_slot_id"
        ],
        logical_occurrence_id=value["logical_occurrence_id"],
        execution_nonce=value["execution_nonce"],
    )
    if (
        value["campaign_attempt_id"] != expected_attempt_id
        or value["current_launch_attempt_id"]
        == value["measurement_launch_attempt_id"]
    ):
        _fail("verification bootstrap context attempt identity changed")
    try:
        os.fstat(EXTERNAL_LAUNCH_CONTEXT_FD)
    except OSError as error:
        if error.errno != errno.EBADF:
            raise
    else:
        _fail("verification external context FD remained open at runner dispatch")
    return value


def _validate_verified_external_context_artifact_joins_v180r12r4(
    store: VerificationDurableStoreV180R12R4,
    context: types.MappingProxyType,
    *,
    manifest: Mapping[str, Any],
    manifest_raw: bytes,
    anchors: _FrozenAnchors,
    materialization: Mapping[str, Any],
    materialization_raw: bytes,
    verification_attempt: Mapping[str, Any],
    measurement_attempt: Mapping[str, Any],
) -> None:
    frozen = manifest.get("frozen_authorization_context")
    if type(frozen) is not dict:
        _fail("verified external context lacks its frozen manifest authority")
    frozen_fields = (
        "protocol_id",
        "protocol_byte_count",
        "protocol_sha256",
        "authorization_id",
        "authorization_byte_count",
        "authorization_sha256",
        "authorization_evidence_id",
        "authorization_evidence_byte_count",
        "authorization_evidence_sha256",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
        "campaign_attempt_id",
    )
    current_raw = store.read_stable(
        VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH,
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    measurement_raw = store.read_stable(
        MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
        byte_cap=LAUNCH_ARTIFACT_BYTE_CAP,
        required_mode=0o400,
    )
    if not (
        all(context[key] == frozen.get(key) for key in frozen_fields)
        and _plain_nested_mapping(
            context["cgroup_parent_fact"],
            "verified external context cgroup parent fact",
        )
        == frozen.get("cgroup_parent_fact")
        and _plain_nested_mapping(
            context["runtime_capability_fact"],
            "verified external context runtime capability fact",
        )
        == frozen.get("runtime_capability_fact")
        and context["repository_root"] == str(store.repository_root)
        and context["c_pre_root"]
        == str(store.repository_root / PRELAUNCH_ROOT_RELATIVE_PATH)
        and context["prereg_commit_id"] == anchors.prereg_commit_id
        and context["prelaunch_materialization_terminal_id"]
        == materialization.get("materialization_terminal_id")
        and context["prelaunch_materialization_terminal_byte_count"]
        == len(materialization_raw)
        and context["prelaunch_materialization_terminal_sha256"]
        == hashlib.sha256(materialization_raw).hexdigest()
        and context["prelaunch_launch_manifest_sha256"]
        == hashlib.sha256(manifest_raw).hexdigest()
        == anchors.manifest_sha256
        and context["prelaunch_launch_rule_id"] == anchors.launch_rule_id
        and context["current_launch_attempt_id"]
        == verification_attempt.get("launch_attempt_id")
        and context["current_launch_attempt_byte_count"] == len(current_raw)
        and context["current_launch_attempt_sha256"]
        == hashlib.sha256(current_raw).hexdigest()
        and loads_canonical_json(current_raw) == dict(verification_attempt)
        and _plain_nested_mapping(
            context["production_systemd_service_invocation"],
            "verified external context production invocation",
        )
        == verification_attempt.get("production_systemd_service_invocation")
        and context["measurement_launch_attempt_id"]
        == measurement_attempt.get("launch_attempt_id")
        and context["measurement_launch_attempt_byte_count"]
        == len(measurement_raw)
        and context["measurement_launch_attempt_sha256"]
        == hashlib.sha256(measurement_raw).hexdigest()
        and loads_canonical_json(measurement_raw) == dict(measurement_attempt)
    ):
        _fail("verified external context artifact/provenance join changed")


def verify_retained_campaign_measurement_once_v180r12r4(
    repository_root: Path,
    *,
    expected_manifest_sha256: str,
    expected_prereg_commit: str,
    watchdog_seconds: int = WALL_TIMEOUT_SECONDS,
    verified_external_context: types.MappingProxyType | None = None,
) -> dict[str, Any]:
    """Consume one exact verification launch attempt and durably retain PASS."""

    store = VerificationDurableStoreV180R12R4(repository_root)
    anchors: _FrozenAnchors | None = None
    verification_attempt: dict[str, Any] | None = None
    reserve: bytearray | None = None
    reserve_allocated = False
    reserve_released = False
    watchdog = _VerificationWatchdog(watchdog_seconds)
    watchdog_was_armed = False
    identity_owned = False
    campaign_attempt_id: str | None = None
    failure_protocol_id: str | None = None
    failure_authorization_id: str | None = None
    try:
        # Reserve bounded heap before any stable input allocation.  If this
        # allocation itself fails no verified launch identity has yet been
        # adopted; once identity_owned becomes true the full reserve is
        # guaranteed to be available for first-action release on failure.
        reserve = _allocate_failure_memory_reserve()
        reserve_allocated = True
        if verified_external_context is not None:
            verified_external_context = (
                _validate_verified_external_context_v180r12r4(
                    verified_external_context
                )
            )
            identity_owned = True
            failure_protocol_id = verified_external_context["protocol_id"]
            failure_authorization_id = verified_external_context[
                "authorization_id"
            ]
            verification_attempt = {
                "launch_attempt_id": verified_external_context[
                    "current_launch_attempt_id"
                ]
            }
            watchdog.bind_absolute_deadline(
                verified_external_context["campaign_deadline_ns"]
            )
            watchdog.arm()
            watchdog_was_armed = True
        manifest_raw = store.read_stable(
            MANIFEST_RELATIVE_PATH, byte_cap=MANIFEST_BYTE_CAP, required_mode=0o400
        )
        expected_manifest_sha256 = _cid(
            expected_manifest_sha256, "bootstrap-supplied manifest digest"
        )
        if hashlib.sha256(manifest_raw).hexdigest() != expected_manifest_sha256:
            _fail("bootstrap-supplied manifest digest changed")
        manifest = _canonical_object(manifest_raw, "source-bound launch manifest")
        anchors = _validate_source_manifest(
            store,
            manifest,
            expected_manifest_sha256=expected_manifest_sha256,
            expected_prereg_commit=expected_prereg_commit,
        )
        materialization, materialization_raw = _validate_materialization(
            store, manifest, manifest_raw, anchors
        )
        verification_attempt = _validate_attempt(
            store,
            VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH,
            target="verification",
            anchors=anchors,
            materialization=materialization,
            materialization_raw=materialization_raw,
            manifest_raw=manifest_raw,
        )
        identity_owned = True
        failure_protocol_id = anchors.protocol_id
        failure_authorization_id = anchors.authorization_id
        _require_current_precreate_matrix(store)
        if not watchdog_was_armed:
            watchdog.arm()
            watchdog_was_armed = True

        measurement_attempt = _validate_attempt(
            store,
            MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
            target="measurement",
            anchors=anchors,
            materialization=materialization,
            materialization_raw=materialization_raw,
            manifest_raw=manifest_raw,
        )
        if verified_external_context is None:
            _fail("verification requires bootstrap-rebuilt source-bundle authority")
        _validate_verified_external_context_artifact_joins_v180r12r4(
            store,
            verified_external_context,
            manifest=manifest,
            manifest_raw=manifest_raw,
            anchors=anchors,
            materialization=materialization,
            materialization_raw=materialization_raw,
            verification_attempt=verification_attempt,
            measurement_attempt=measurement_attempt,
        )
        (
            pre_attempt_host_conformance_raw,
            pre_attempt_host_conformance,
        ) = _validate_pre_attempt_host_conformance(
            store,
            frozen_context=verified_external_context,
        )

        terminal_raw = store.read_stable(
            TERMINAL_RELATIVE_PATH,
            byte_cap=TERMINAL_BYTE_CAP,
            required_mode=0o400,
        )
        terminal, subject = _validate_terminal(
            terminal_raw,
            anchors,
            expected_materialization_terminal_id=materialization[
                "materialization_terminal_id"
            ],
            expected_measurement_launch_attempt_id=measurement_attempt[
                "launch_attempt_id"
            ],
            expected_precompiled_source_bundle_sha256=verified_external_context[
                "precompiled_source_bundle_sha256"
            ],
        )
        campaign_attempt_id = terminal["attempt_id"]
        success_artifacts = {
            "evidence_inventory": store.read_stable(
                EVIDENCE_INVENTORY_RELATIVE_PATH,
                byte_cap=EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
                required_mode=0o400,
            ),
            "execution_closure": store.read_stable(
                EXECUTION_CLOSURE_RELATIVE_PATH,
                byte_cap=EXECUTION_CLOSURE_BYTE_CAP,
                required_mode=0o400,
            ),
            "os_receipt": store.read_stable(
                OS_RECEIPT_RELATIVE_PATH,
                byte_cap=OS_RECEIPT_BUNDLE_BYTE_CAP,
                required_mode=0o400,
            ),
            "ledger_closure": store.read_stable(
                LEDGER_CLOSURE_RELATIVE_PATH,
                byte_cap=LEDGER_CLOSURE_BYTE_CAP,
                required_mode=0o400,
            ),
        }
        _validate_success_artifact_facts(terminal, success_artifacts)
        measurement_receipt = _validate_measurement_receipt(
            store,
            attempt=measurement_attempt,
            terminal_raw=terminal_raw,
            campaign_attempt_id=terminal["attempt_id"],
        )
        if (
            pre_attempt_host_conformance["observed"]["cgroup_parent_fact"]
            ["self_membership"]
            != measurement_receipt["production_runtime_placement_t1"]
            ["source_membership"]
        ):
            _fail("pre-attempt host membership does not join measurement T1")
        measurement_attempt_raw = canonical_json_bytes(measurement_attempt)
        measurement_receipt_raw = canonical_json_bytes(measurement_receipt)
        (
            measurement_service_attempt_raw,
            measurement_service_attempt,
            measurement_service_receipt_raw,
            measurement_service_receipt,
        ) = _validate_measurement_service_launch_join(
            store,
            materialization=materialization,
            measurement_attempt=measurement_attempt,
            measurement_receipt=measurement_receipt,
        )
        native_zero_precompiled_source_rows = (
            _validate_native_zero_precompiled_source_rows_v180r12r4(
                verified_external_context["native_zero_precompiled_source_rows"]
            )
        )
        result = (
            independent_verifier.
            verify_campaign_measurement_terminal_independently_v180r12r4(
                terminal_raw,
                campaign_evidence_inventory_bundle_bytes=success_artifacts[
                    "evidence_inventory"
                ],
                campaign_execution_closure_bytes=success_artifacts[
                    "execution_closure"
                ],
                campaign_os_receipt_bundle_bytes=success_artifacts["os_receipt"],
                campaign_ledger_closure_bytes=success_artifacts["ledger_closure"],
                measurement_service_launch_attempt_bytes=(
                    measurement_service_attempt_raw
                ),
                measurement_service_launch_receipt_bytes=(
                    measurement_service_receipt_raw
                ),
                measurement_launch_attempt_bytes=measurement_attempt_raw,
                measurement_launch_receipt_bytes=measurement_receipt_raw,
                pre_attempt_host_conformance_bytes=(
                    pre_attempt_host_conformance_raw
                ),
                expected_cgroup_parent_fact=_plain_nested_mapping(
                    verified_external_context["cgroup_parent_fact"],
                    "independent verifier frozen cgroup parent fact",
                ),
                expected_runtime_capability_fact=_plain_nested_mapping(
                    verified_external_context["runtime_capability_fact"],
                    "independent verifier frozen runtime capability fact",
                ),
                expected_protocol_id=anchors.protocol_id,
                expected_authorization_id=anchors.authorization_id,
                expected_authorization_evidence_id=(
                    anchors.authorization_evidence_id
                ),
                expected_attempt_id=terminal["attempt_id"],
                expected_prelaunch_materialization_terminal_id=(
                    materialization["materialization_terminal_id"]
                ),
                expected_prelaunch_launch_manifest_sha256=anchors.manifest_sha256,
                expected_prelaunch_launch_rule_id=anchors.launch_rule_id,
                expected_measurement_launch_attempt_id=measurement_attempt[
                    "launch_attempt_id"
                ],
                expected_precompiled_source_bundle_sha256=(
                    verified_external_context["precompiled_source_bundle_sha256"]
                ),
                expected_native_zero_precompiled_source_rows=(
                    native_zero_precompiled_source_rows
                ),
                expected_subject_id=terminal["subject_id"],
                expected_native_zero_source_manifest_id=terminal[
                    "native_zero_source_manifest_id"
                ],
                expected_native_zero_import_inventory_id=terminal[
                    "native_zero_import_inventory_id"
                ],
                expected_max_event_count=MAX_EVENT_COUNT,
                expected_max_event_byte_count=MAX_EVENT_BYTE_COUNT,
                expected_max_ledger_byte_count=MAX_LEDGER_BYTE_COUNT,
            )
        )
        verification_raw = result.canonical_bytes
        verification_document = result.document
        if type(verification_raw) is not bytes or not (
            0 < len(verification_raw) <= VERIFICATION_BYTE_CAP
            and canonical_json_bytes(verification_document) == verification_raw
            and verification_document.get("protocol_id") == anchors.protocol_id
            and verification_document.get("authorization_id") == anchors.authorization_id
            and verification_document.get("authorization_evidence_id")
            == anchors.authorization_evidence_id
            and verification_document.get("attempt_id") == terminal["attempt_id"]
            and verification_document.get("prelaunch_materialization_terminal_id")
            == materialization["materialization_terminal_id"]
            and verification_document.get("prelaunch_launch_manifest_sha256")
            == anchors.manifest_sha256
            and verification_document.get("precompiled_source_bundle_sha256")
            == verified_external_context["precompiled_source_bundle_sha256"]
            and verification_document.get("prelaunch_launch_rule_id")
            == anchors.launch_rule_id
            and verification_document.get("measurement_launch_attempt_id")
            == measurement_attempt["launch_attempt_id"]
            and verification_document.get("measurement_service_launch_attempt_id")
            == measurement_service_attempt["service_launch_attempt_id"]
            and verification_document.get(
                "measurement_service_launch_attempt_byte_count"
            )
            == len(measurement_service_attempt_raw)
            and verification_document.get(
                "measurement_service_launch_attempt_sha256"
            )
            == hashlib.sha256(measurement_service_attempt_raw).hexdigest()
            and verification_document.get("measurement_service_launch_receipt_id")
            == measurement_service_receipt["service_launch_receipt_id"]
            and verification_document.get(
                "measurement_service_launch_receipt_byte_count"
            )
            == len(measurement_service_receipt_raw)
            and verification_document.get(
                "measurement_service_launch_receipt_sha256"
            )
            == hashlib.sha256(measurement_service_receipt_raw).hexdigest()
            and verification_document.get("measurement_launch_receipt_id")
            == measurement_receipt["launch_receipt_id"]
            and verification_document.get("measurement_launch_receipt_byte_count")
            == len(measurement_receipt_raw)
            and verification_document.get("measurement_launch_receipt_sha256")
            == hashlib.sha256(measurement_receipt_raw).hexdigest()
            and verification_document.get(
                "pre_attempt_host_conformance_relative_path"
            )
            == PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH
            and verification_document.get(
                "pre_attempt_host_conformance_byte_count"
            )
            == len(pre_attempt_host_conformance_raw)
            and verification_document.get("pre_attempt_host_conformance_sha256")
            == hashlib.sha256(pre_attempt_host_conformance_raw).hexdigest()
            and verification_document.get("pre_attempt_host_conformance_mode")
            == 0o400
            and verification_document.get(
                "pre_attempt_host_conformance_expected_frozen_context_joined"
            )
            is True
            and verification_document.get(
                "pre_attempt_host_conformance_cgroup_runtime_exact_except_self_membership"
            )
            is True
            and verification_document.get(
                "pre_attempt_host_conformance_socket_buffer_minimums_met"
            )
            is True
            and verification_document.get(
                "pre_attempt_host_conformance_independently_replayed"
            )
            is True
            and verification_document.get(
                "pre_attempt_host_conformance_is_campaign_event_or_counter_record"
            )
            is False
            and verification_document.get("runtime_role_exit_origin_guard_status")
            == "PASS_TRANSITIVE_FROZEN_BOOTSTRAP_AND_MEASUREMENT_LAUNCH_RECEIPT"
            and verification_document.get(
                "measurement_launch_receipt_directly_observes_origin_guard"
            )
            is False
            and verification_document.get(
                "frozen_bootstrap_post_dispatch_origin_guard_transitively_supported"
            )
            is True
            and verification_document.get(
                "production_systemd_service_invocation_independently_replayed"
            )
            is True
            and verification_document.get(
                "production_runtime_placement_t1_t2_t3_independently_replayed"
            )
            is True
            and verification_document.get(
                "pre_scientific_outer_service_launch_join_independently_replayed"
            )
            is True
            and verification_document.get("subject_id") == subject["subject_result_id"]
            and verification_document.get("campaign_measurement_terminal_id")
            == terminal["campaign_measurement_terminal_id"]
        ):
            _fail("independent verifier returned a context-drifting receipt")
        _assert_verification_document(verification_document)

        store.write_once(VERIFICATION_RELATIVE_PATH, verification_raw, mode=0o400)
        if store.read_stable(
            VERIFICATION_RELATIVE_PATH,
            byte_cap=VERIFICATION_BYTE_CAP,
            required_mode=0o400,
        ) != verification_raw:
            _fail("durable verification readback changed")
        store.write_once(RETAINED_REPLAY_RELATIVE_PATH, verification_raw, mode=0o400)
        if store.read_stable(
            RETAINED_REPLAY_RELATIVE_PATH,
            byte_cap=VERIFICATION_BYTE_CAP,
            required_mode=0o400,
        ) != verification_raw:
            _fail("byte-identical retained replay readback changed")
        watchdog.teardown()
        _release_failure_memory_reserve(reserve)
        reserve_released = True
        reserve = None
        return dict(verification_document)
    except BaseException as error:
        # This path must survive a second near-deadline SIGALRM and a prior
        # MemoryError.  Neutralization only updates preallocated slots; release
        # the 4 MiB reserve before handler restoration or any formatting.
        watchdog.neutralize()
        _release_failure_memory_reserve(reserve)
        reserve_released = reserve_allocated
        reserve = None
        watchdog.restore()
        if (
            not identity_owned
            or verification_attempt is None
            or failure_protocol_id is None
            or failure_authorization_id is None
        ):
            try:
                BaseException.__setattr__(error, "__traceback__", None)
            except BaseException:
                pass
            raise error
        primary = error
        try:
            BaseException.__setattr__(primary, "__traceback__", None)
        except BaseException:
            pass
        if isinstance(primary, V180R12R4VerificationReplayForbidden):
            raise primary
        observations = tuple(
            _failure_observation(
                store, relative, byte_cap=cap, kind=kind
            )
            for relative, kind, cap in (
                VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
            )
        )
        failure_raw = _verification_failure_bytes(
            protocol_id=failure_protocol_id,
            authorization_id=failure_authorization_id,
            attempt_id=campaign_attempt_id,
            verification_launch_attempt_id=verification_attempt["launch_attempt_id"],
            error=primary,
            observations=observations,
            reserve_allocated=reserve_allocated,
            reserve_released=reserve_released,
            watchdog_armed=watchdog_was_armed,
            watchdog_cleanup_observation=watchdog.cleanup_observation(),
        )
        secondary: BaseException | None = None
        try:
            store.write_once(VERIFICATION_FAILURE_RELATIVE_PATH, failure_raw, mode=0o400)
        except BaseException as failure_write_error:
            secondary = failure_write_error
            try:
                BaseException.__setattr__(secondary, "__traceback__", None)
            except BaseException:
                pass
        if secondary is not None:
            raise primary from secondary
        raise primary
    finally:
        _release_failure_memory_reserve(reserve)
        try:
            watchdog.neutralize()
            watchdog.restore()
        except BaseException:
            pass
        store.close()


def bootstrap_entrypoint_v180r12r4(
    verified_context: Mapping[str, Any],
) -> None:
    context = _validate_verified_external_context_v180r12r4(verified_context)
    verify_retained_campaign_measurement_once_v180r12r4(
        Path(context["repository_root"]),
        expected_manifest_sha256=context["prelaunch_launch_manifest_sha256"],
        expected_prereg_commit=context["prereg_commit_id"],
        verified_external_context=context,
    )


def main() -> int:
    raise V180R12R4VerificationRunnerError(
        "direct verification invocation is forbidden; the retained bootstrap "
        "must supply its consumed immutable external launch context"
    )


__all__ = (
    "FAILURE_EMERGENCY_RESERVE_BYTES",
    "FRAME_BYTE_CAP",
    "NATIVE_ZERO_MEASURED_TARGET_SOURCE_PATHS",
    "NATIVE_ZERO_PRECOMPILED_SOURCE_ROW_FIELDS",
    "PROFILE_KEY",
    "SUBJECT_RESULT_BYTE_CAP",
    "SUBJECT_RESULT_RUNTIME_BYTE_CAP",
    "VerificationDurableStoreV180R12R4",
    "V180R12R4VerificationDurableWriteFailure",
    "V180R12R4VerificationReplayForbidden",
    "V180R12R4VerificationRunnerError",
    "V180R12R4VerificationTimeout",
    "VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROW_COUNT",
    "VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS",
    "VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP",
    "VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP",
    "VERIFICATION_FAILURE_FIELDS",
    "VERIFICATION_FAILURE_OBSERVATION_BOUNDARY",
    "VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES",
    "VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS",
    "VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA",
    "VERIFICATION_EXTERNAL_FD_ROLE_ROWS",
    "bootstrap_entrypoint_v180r12r4",
    "main",
    "verify_retained_campaign_measurement_once_v180r12r4",
)


if __name__ == "__main__":
    raise SystemExit(main())
