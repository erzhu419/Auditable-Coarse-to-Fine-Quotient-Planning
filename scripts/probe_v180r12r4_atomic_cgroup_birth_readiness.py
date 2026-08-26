#!/usr/bin/env python3
"""One-shot V180r12r4 atomic cgroup-birth readiness probe.

The probe is deliberately separate from the scientific campaign identity.  Its
unit name and token bind only the consumed V180r12r3r2 failure, the retained
launch failure, the bounded repair scope, ``purpose=PREFLIGHT``, and the exact
freshness ``ordinal=0``.  A
post-commit, canonical external root supplies source and host facts without a
self-referential source hash.

Importing this module is inert.  Real effects are reachable only through the
three exact, one-argument modes ``--prepare``, ``--launch``, and ``--probe``.
Focused tests inject fake adapters and therefore never create a cgroup, call
clone3, or start a transient unit.
"""

from __future__ import annotations

import ctypes
import base64
import binascii
from dataclasses import dataclass
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import select
import signal
import socket
import stat
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, NoReturn, Protocol, Sequence


FAILED_FAILURE_STATE_ID = (
    "1ff2239cd5ca71f588149e987cded8fe5b8dbf75e7d7098435fda0955fffd09d"
)
FAILED_LAUNCH_FAILURE_ID = (
    "594c08d5932d0f7188b232485f6e9a08a0d4b041aa2c9f84aa0095d2b1591935"
)
REPAIR_SCOPE = (
    "OUTER_OBSERVER_DELEGATED_SOURCE_CGROUP_PLACEMENT_AND_ATOMIC_BIRTH_"
    "PREFLIGHT_ONLY"
)
PURPOSE = "PREFLIGHT"
PREFLIGHT_ORDINAL = 0
TARGET_PURPOSE = "PREFLIGHT_TARGET"
TARGET_ORDINAL = 0

TOKEN_DOMAIN = "acfqp:v180r12r4:atomic-cgroup-birth-preflight-token:v1"
TARGET_TOKEN_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-target-token:v1"
)
EXTERNAL_ROOT_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-external-root:v1"
)
ATTEMPT_DOMAIN = "acfqp:v180r12r4:atomic-cgroup-birth-preflight-attempt:v1"
SUBSTAGE_DOMAIN = "acfqp:v180r12r4:atomic-cgroup-birth-preflight-substage:v1"
RECEIPT_DOMAIN = "acfqp:v180r12r4:atomic-cgroup-birth-preflight-receipt:v1"
FAILURE_DOMAIN = "acfqp:v180r12r4:atomic-cgroup-birth-preflight-failure:v1"
HANDSHAKE_DOMAIN = "acfqp:v180r12r4:atomic-cgroup-birth-preflight-handshake:v1"
OUTER_LAUNCH_ATTEMPT_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-outer-launch-attempt:v1"
)
OUTER_LAUNCH_RECEIPT_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-outer-launch-receipt:v1"
)
OUTER_LAUNCH_SUCCESS_SEAL_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-outer-launch-success-seal:v1"
)
OUTER_LAUNCH_FAILURE_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-outer-launch-failure:v1"
)
PREPARE_RESULT_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-prepare-result:v1"
)
PREPARE_ATTEMPT_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-prepare-attempt:v1"
)
PREPARE_RECEIPT_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-prepare-receipt:v1"
)
PREPARE_FAILURE_DOMAIN = (
    "acfqp:v180r12r4:atomic-cgroup-birth-preflight-prepare-failure:v1"
)

EXTERNAL_ROOT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_external_root.v1"
INVOCATION_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_systemd_invocation.v1"
TARGET_LIFECYCLE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_target_lifecycle.v1"
)
TOOLCHAIN_EXECUTABLE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_toolchain_executable.v1"
)
HOST_PARENT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_host_parent_fact.v1"
SOURCE_FACT_SCHEMA = "acfqp.git_source_fact.v1"
ATTEMPT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_attempt.v1"
SUBSTAGE_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_substage.v1"
RECEIPT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_receipt.v1"
FAILURE_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_failure.v1"
HANDSHAKE_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_handshake.v1"
OUTER_LAUNCH_ATTEMPT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_outer_launch_attempt.v1"
)
OUTER_LAUNCH_RECEIPT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_outer_launch_receipt.v1"
)
OUTER_LAUNCH_SUCCESS_SEAL_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_outer_launch_success_seal.v1"
)
OUTER_LAUNCH_FAILURE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_outer_launch_failure.v1"
)
PREPARE_RESULT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_prepare_result.v1"
PREPARE_ATTEMPT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_prepare_attempt.v1"
)
PREPARE_RECEIPT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_prepare_receipt.v1"
)
PREPARE_FAILURE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_prepare_failure.v1"
)

PROBE_SOURCE_RELATIVE_PATH = (
    "scripts/probe_v180r12r4_atomic_cgroup_birth_readiness.py"
)
FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_campaign_measurement_failure_freeze_"
    "v180r12r3r2.py"
)
EXTERNAL_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_atomic_birth_readiness_external_root.json"
)
ARTIFACT_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_atomic_birth_readiness"
)
ATTEMPT_NAME = "ATTEMPT.json"
RECEIPT_NAME = "RECEIPT.json"
FAILURE_NAME = "FAILURE.json"
OUTER_LAUNCH_ATTEMPT_NAME = "LAUNCH_ATTEMPT.json"
OUTER_LAUNCH_RECEIPT_NAME = "LAUNCH_RECEIPT.json"
OUTER_LAUNCH_SUCCESS_SEAL_NAME = "LAUNCH_SUCCESS_SEAL.json"
OUTER_LAUNCH_FAILURE_NAME = "LAUNCH_FAILURE.json"
PREPARE_ATTEMPT_NAME = (
    f"v180r12r4_atomic_birth_readiness_PREFLIGHT_ordinal-{PREFLIGHT_ORDINAL}_"
    "PREPARE_ATTEMPT.json"
)
PREPARE_RECEIPT_NAME = (
    f"v180r12r4_atomic_birth_readiness_PREFLIGHT_ordinal-{PREFLIGHT_ORDINAL}_"
    "PREPARE_RECEIPT.json"
)
PREPARE_FAILURE_NAME = (
    f"v180r12r4_atomic_birth_readiness_PREFLIGHT_ordinal-{PREFLIGHT_ORDINAL}_"
    "PREPARE_FAILURE.json"
)
PREPARE_JOURNAL_NAMES = frozenset(
    {PREPARE_ATTEMPT_NAME, PREPARE_RECEIPT_NAME, PREPARE_FAILURE_NAME}
)
ROOT_ARTIFACT_NAMES = frozenset(
    {
        ATTEMPT_NAME,
        RECEIPT_NAME,
        FAILURE_NAME,
        OUTER_LAUNCH_ATTEMPT_NAME,
        OUTER_LAUNCH_RECEIPT_NAME,
        OUTER_LAUNCH_SUCCESS_SEAL_NAME,
        OUTER_LAUNCH_FAILURE_NAME,
    }
)
ALL_ARTIFACT_NAMES = PREPARE_JOURNAL_NAMES | ROOT_ARTIFACT_NAMES

SYSTEMD_RUN = "/usr/bin/systemd-run"
SYSTEMCTL = "/usr/bin/systemctl"
ENV_BINARY = "/usr/bin/env"
PYTHON_BINARY = "/usr/bin/python3"
TRUE_BINARY = "/usr/bin/true"
GIT_BINARY = "/usr/bin/git"
TOOLCHAIN_EXECUTABLE_PATHS = (
    GIT_BINARY,
    SYSTEMD_RUN,
    SYSTEMCTL,
    ENV_BINARY,
    PYTHON_BINARY,
    TRUE_BINARY,
)
SERVICE_SLICE = "app.slice"
SERVICE_TYPE = "exec"
TARGET_SERVICE_TYPE = "oneshot"
EXTERNAL_ROOT_PATH_ENV = (
    "ACFQP_V180R12R4_ATOMIC_BIRTH_EXTERNAL_ROOT_PATH"
)
EXTERNAL_ROOT_SHA256_ENV = (
    "ACFQP_V180R12R4_ATOMIC_BIRTH_EXTERNAL_ROOT_SHA256"
)
EXTERNAL_ROOT_SHA256_TEMPLATE = "{EXTERNAL_ROOT_SHA256}"
STATIC_CLEAN_ENVIRONMENT = {
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
}
OUTER_BUS_ENVIRONMENT_KEYS = frozenset(
    {"XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"}
)
REQUIRED_UMASK = 0o077

CLONE_PIDFD = 0x00001000
CLONE_INTO_CGROUP = 0x200000000
CGROUP2_SUPER_MAGIC = 0x63677270
CLONE3_SYSCALL_X86_64 = 435
PIDFD_SEND_SIGNAL_SYSCALL_X86_64 = 424
GIT_CALL_TIMEOUT_SECONDS = 5
TARGET_MANAGER_CALL_TIMEOUT_SECONDS = 5
TARGET_MANAGER_MAX_POLLS = 256
TARGET_MANAGER_ABSENCE_PROPERTIES = (
    "LoadState",
    "ActiveState",
    "SubState",
    "ControlGroup",
)
TARGET_MANAGER_ACTIVE_PROPERTIES = (
    *TARGET_MANAGER_ABSENCE_PROPERTIES,
    "BindsTo",
    "After",
    "KillMode",
    "Type",
    "RemainAfterExit",
    "Delegate",
    "CollectMode",
    "Slice",
    "TimeoutStopUSec",
)
TARGET_MANAGER_ABSENCE_PROPERTY_KEYS = frozenset(
    TARGET_MANAGER_ABSENCE_PROPERTIES
)
TARGET_MANAGER_ACTIVE_PROPERTY_KEYS = frozenset(
    TARGET_MANAGER_ACTIVE_PROPERTIES
)
TARGET_MANAGER_OUTPUT_CAP_BYTES = 16 * 1024
INNER_GIT_CALL_COUNT = 6
PREPARE_GIT_CALL_COUNT = 7
OUTER_PREWORK_GIT_CALL_COUNT = 8
INNER_TOTAL_TIMEOUT_SECONDS = 70
INNER_TOTAL_TIMEOUT_NS = INNER_TOTAL_TIMEOUT_SECONDS * 1_000_000_000
UNIT_RUNTIME_MAX_SECONDS = 90
UNIT_STOP_TIMEOUT_SECONDS = 15
TARGET_UNIT_STOP_TIMEOUT_SECONDS = 10
OUTER_LAUNCH_TIMEOUT_SECONDS = 120
OUTER_POST_ABSENCE_SECONDS = 20
FORMAL_PREWORK_RESERVE_SECONDS = 65
FORMAL_DEADLINE_MARGIN_SECONDS = 10
FORMAL_TOTAL_CAP_SECONDS = 230
PREPARE_TOTAL_CAP_SECONDS = 60
MAX_EXTERNAL_ROOT_BYTES = 256 * 1024
MAX_TOOLCHAIN_EXECUTABLE_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_BYTES = 512 * 1024
MAX_HANDSHAKE_BYTES = 16 * 1024
MAX_SUBPROCESS_STDOUT_BYTES = 128 * 1024
MAX_SUBPROCESS_STDERR_BYTES = 128 * 1024
PIPE_READ_CHUNK_BYTES = 64 * 1024
MAX_PIPE_READS_PER_POLL_EVENT = 1
OUTER_TERMINATION_GRACE_SECONDS = 1
TARGET_MANAGER_PROCESS_TOTAL_BOUND_SECONDS = (
    TARGET_MANAGER_CALL_TIMEOUT_SECONDS
    + 2 * OUTER_TERMINATION_GRACE_SECONDS
)
GIT_PROCESS_TOTAL_BOUND_SECONDS = (
    GIT_CALL_TIMEOUT_SECONDS + 2 * OUTER_TERMINATION_GRACE_SECONDS
)
OUTER_PROCESS_TOTAL_BOUND_SECONDS = (
    OUTER_LAUNCH_TIMEOUT_SECONDS + 2 * OUTER_TERMINATION_GRACE_SECONDS
)
OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS = (
    OUTER_PROCESS_TOTAL_BOUND_SECONDS
    + OUTER_POST_ABSENCE_SECONDS
    + FORMAL_DEADLINE_MARGIN_SECONDS
)
OUTER_REQUIRED_AFTER_PROCESS_SECONDS = (
    OUTER_POST_ABSENCE_SECONDS + FORMAL_DEADLINE_MARGIN_SECONDS
)
MAX_ARTIFACT_INVENTORY_ENTRIES = len(ROOT_ARTIFACT_NAMES)
MAX_ARTIFACT_INVENTORY_NAME_BYTES = sum(len(name) for name in ROOT_ARTIFACT_NAMES)
MAX_GIT_STDOUT_BYTES = 2_000_000
MAX_GIT_STDERR_BYTES = 64 * 1024
MAX_OUTER_OBSERVATION_POLLS = 1024

if not (
    INNER_GIT_CALL_COUNT * GIT_PROCESS_TOTAL_BOUND_SECONDS
    < INNER_TOTAL_TIMEOUT_SECONDS
    < UNIT_RUNTIME_MAX_SECONDS
    and UNIT_RUNTIME_MAX_SECONDS + UNIT_STOP_TIMEOUT_SECONDS
    < OUTER_LAUNCH_TIMEOUT_SECONDS
    and UNIT_RUNTIME_MAX_SECONDS
    + UNIT_STOP_TIMEOUT_SECONDS
    + TARGET_UNIT_STOP_TIMEOUT_SECONDS
    < OUTER_LAUNCH_TIMEOUT_SECONDS
):
    raise RuntimeError("inner/Git/unit/outer deadline arithmetic is not strict")
if not (
    PREPARE_GIT_CALL_COUNT * GIT_PROCESS_TOTAL_BOUND_SECONDS
    < PREPARE_TOTAL_CAP_SECONDS
):
    raise RuntimeError("prepare Git calls leave no publication margin")
if not (
    OUTER_PREWORK_GIT_CALL_COUNT * GIT_PROCESS_TOTAL_BOUND_SECONDS
    < FORMAL_PREWORK_RESERVE_SECONDS
):
    raise RuntimeError("outer Git calls leave no host/source margin")
if not (
    FORMAL_PREWORK_RESERVE_SECONDS
    + OUTER_PROCESS_TOTAL_BOUND_SECONDS
    + OUTER_POST_ABSENCE_SECONDS
    + FORMAL_DEADLINE_MARGIN_SECONDS
    < FORMAL_TOTAL_CAP_SECONDS
):
    raise RuntimeError("formal deadline components leave no strict margin")

LINEAGE_FIELDS = frozenset(
    {
        "failed_failure_state_id",
        "failed_launch_failure_id",
        "repair_scope",
        "purpose",
        "ordinal",
    }
)
TARGET_LINEAGE_FIELDS = frozenset(
    {
        "failed_failure_state_id",
        "failed_launch_failure_id",
        "repair_scope",
        "purpose",
        "ordinal",
    }
)
SOURCE_FACT_FIELDS = frozenset(
    {"schema", "relative_path", "git_mode", "git_blob_id", "byte_count", "sha256"}
)
HOST_PARENT_FIELDS = frozenset(
    {
        "schema",
        "mount_point",
        "mount_device",
        "mount_inode",
        "app_slice_path",
        "app_slice_device",
        "app_slice_inode",
        "owner_uid",
        "owner_gid",
        "mode",
        "controllers",
        "subtree_control",
        "cgroup_type",
        "cgroup_namespace_inode",
        "cgroup_procs_device",
        "cgroup_procs_inode",
        "cgroup_procs_owner_uid",
        "cgroup_procs_owner_gid",
        "cgroup_procs_mode",
        "runtime_dir_path",
        "runtime_dir_device",
        "runtime_dir_inode",
        "runtime_dir_owner_uid",
        "runtime_dir_owner_gid",
        "runtime_dir_mode",
        "user_bus_path",
        "user_bus_device",
        "user_bus_inode",
        "user_bus_owner_uid",
        "user_bus_owner_gid",
        "user_bus_mode",
        "user_bus_file_type",
        "toolchain_facts",
    }
)
TOOLCHAIN_EXECUTABLE_FIELDS = frozenset(
    {
        "schema",
        "path",
        "resolved_path",
        "requested_kind",
        "requested_device",
        "requested_inode",
        "requested_mode",
        "requested_owner_uid",
        "requested_owner_gid",
        "requested_link_count",
        "requested_byte_count",
        "requested_mtime_ns",
        "requested_ctime_ns",
        "device",
        "inode",
        "mode",
        "owner_uid",
        "owner_gid",
        "link_count",
        "byte_count",
        "sha256",
    }
)
INVOCATION_FIELDS = frozenset(
    {
        "schema",
        "repository_root",
        "external_root_path",
        "artifact_root",
        "systemd_run_binary",
        "systemd_options",
        "exec_prefix",
        "clean_environment_template",
        "outer_launch_environment",
        "python_argv",
        "service_type",
        "delegate",
        "slice",
        "scope",
        "target_lifecycle_contract",
        "prepare_journal_relative_paths",
    }
)
TARGET_LIFECYCLE_FIELDS = frozenset(
    {
        "schema",
        "purpose",
        "ordinal",
        "target_token",
        "unit_name",
        "cgroup_name",
        "slice",
        "service_type",
        "remain_after_exit",
        "delegate",
        "umask",
        "collect",
        "lifecycle_authority",
        "binds_to_unit",
        "after_unit",
        "kill_mode",
        "timeout_stop_seconds",
        "environment",
        "create_argv",
        "absence_show_argv",
        "active_show_argv",
        "stop_argv",
        "executable",
        "manager_call_timeout_seconds",
        "manager_process_total_bound_seconds",
        "manager_max_polls",
        "shared_inner_absolute_deadline_seconds",
    }
)
PREPARED_SUCCESS_NAMES = frozenset(
    {PREPARE_ATTEMPT_NAME, PREPARE_RECEIPT_NAME}
)


def _root_inventory(*names: str) -> frozenset[str]:
    requested = frozenset(names)
    if not requested.issubset(ROOT_ARTIFACT_NAMES):
        raise RuntimeError("root inventory contains a foreign name")
    return requested
PREPARE_ATTEMPT_FIELDS = frozenset(
    {
        "schema",
        "purpose",
        "ordinal",
        "preflight_token",
        "external_root_id",
        "external_root_path",
        "external_root_byte_count",
        "external_root_sha256",
        "artifact_root",
        "artifact_root_absent_before_attempt",
        "prepare_journal_relative_paths",
        "c_probe_commit_id",
        "c_probe_tree_id",
        "tracked_and_index_clean",
        "untracked_files_in_authority",
        "one_shot",
        "prepare_attempt_id",
    }
)
PREPARE_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "prepare_attempt_id",
        "preflight_token",
        "ordinal",
        "external_root_id",
        "external_root_path",
        "external_root_byte_count",
        "external_root_sha256",
        "artifact_root",
        "artifact_root_device",
        "artifact_root_inode",
        "artifact_root_mode",
        "prepare_journal_relative_paths",
        "external_root_o_excl_owned",
        "external_root_canonical_0400_durable",
        "artifact_root_owned_0700",
        "tracked_and_index_clean",
        "untracked_files_in_authority",
        "prepare_receipt_id",
    }
)
PREPARE_FAILURE_FIELDS = frozenset(
    {
        "schema",
        "prepare_attempt_id",
        "preflight_token",
        "ordinal",
        "external_root_id",
        "external_root_path",
        "artifact_root",
        "prepare_attempt_observed_exact",
        "prepare_attempt_recovery_raw_byte_count",
        "prepare_attempt_recovery_raw_sha256",
        "prepare_receipt_path_present",
        "prepare_receipt_observed_exact",
        "prepare_receipt_recovery_raw_byte_count",
        "prepare_receipt_recovery_raw_sha256",
        "external_root_path_present",
        "external_root_observed_exact",
        "external_root_recovery_raw_byte_count",
        "external_root_recovery_raw_sha256",
        "artifact_root_path_present",
        "artifact_root_device",
        "artifact_root_inode",
        "artifact_root_mode",
        "artifact_root_owner_uid",
        "artifact_root_owner_gid",
        "artifact_root_inventory_empty",
        "prepare_journal_relative_paths",
        "prepare_failure_state_class",
        "scientific_occurrence_started",
        "campaign_actual_measurement",
        "prepare_failure_id",
    }
)
PREPARE_FAILURE_STATE_CLASSES = frozenset(
    {
        "ATTEMPT_EXACT_NO_RECEIPT",
        "ATTEMPT_STRICT_PREFIX_NO_RECEIPT",
        "RECEIPT_EXACT",
        "RECEIPT_STRICT_PREFIX",
    }
)
SUBSTAGE_FIELDS = frozenset(
    {
        "schema",
        "index",
        "substage",
        "status",
        "errno",
        "errno_name",
        "error_type",
        "message",
        "detail",
        "substage_record_id",
    }
)
ATTEMPT_FIELDS = frozenset(
    {
        "schema",
        "purpose",
        "ordinal",
        "preflight_token",
        "service_unit_name",
        "target_cgroup_name",
        "target_token",
        "target_unit_name",
        "target_lifecycle_authority",
        "external_root_id",
        "external_root_byte_count",
        "external_root_sha256",
        "c_probe_commit_id",
        "c_probe_tree_id",
        "probe_source_git_blob_id",
        "outer_launch_attempt_id",
        "one_shot",
        "probe_attempt_id",
    }
)
RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "probe_attempt_id",
        "preflight_token",
        "ordinal",
        "service_unit_name",
        "target_cgroup_name",
        "target_token",
        "target_unit_name",
        "target_lifecycle_authority",
        "clone3_flags",
        "source_is_exact_service_root",
        "nearest_common_ancestor_is_app_slice",
        "app_slice_cgroup_procs_write_required",
        "child_handshake_complete",
        "pidfd_identity_complete",
        "child_membership_exact",
        "child_exit_zero",
        "bounded_cleanup_complete",
        "target_absent",
        "target_manager_owned",
        "target_manager_stop_complete",
        "target_unit_absent",
        "target_claimed_inode_unlinked",
        "probe_path_deletion_calls",
        "substage_records",
        "preflight_receipt_id",
    }
)
FAILURE_FIELDS = frozenset(
    {
        "schema",
        "probe_attempt_id",
        "preflight_token",
        "ordinal",
        "service_unit_name",
        "target_cgroup_name",
        "target_token",
        "target_unit_name",
        "target_lifecycle_authority",
        "failed_substage",
        "errno",
        "errno_name",
        "error_type",
        "message",
        "child_reaped",
        "process_may_remain",
        "target_absent",
        "target_may_remain",
        "target_identity_continuous",
        "target_manager_stop_requested",
        "target_manager_absence_proven",
        "probe_path_deletion_calls",
        "substage_records",
        "scientific_occurrence_started",
        "campaign_actual_measurement",
        "preflight_failure_id",
    }
)
OUTER_LAUNCH_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "outer_launch_attempt_id",
        "preflight_token",
        "ordinal",
        "service_unit_name",
        "target_cgroup_name",
        "systemd_run_argv_sha256",
        "returncode",
        "timed_out",
        "output_limit_exceeded",
        "stdout",
        "stderr",
        "inner_observation",
        "prelaunch_absence",
        "postlaunch_absence",
        "deadline_contract",
        "unit_absent",
        "target_absent",
        "source_unit_absent",
        "source_path_absent",
        "target_unit_absent",
        "target_path_absent",
        "scientific_occurrence_started",
        "campaign_actual_measurement",
        "outer_launch_receipt_id",
    }
)
OUTER_LAUNCH_SUCCESS_SEAL_FIELDS = frozenset(
    {
        "schema",
        "outer_launch_attempt_id",
        "preflight_token",
        "ordinal",
        "outer_launch_receipt_id",
        "outer_launch_receipt_sha256",
        "decision_stage",
        "verified_monotonic_ns",
        "formal_deadline_monotonic_ns",
        "remaining_after_launch_receipt_publication_ns",
        "inventory_before_success_seal",
        "scientific_occurrence_started",
        "campaign_actual_measurement",
        "outer_launch_success_seal_id",
    }
)
OUTER_LAUNCH_FAILURE_FIELDS = frozenset(
    {
        "schema",
        "outer_launch_attempt_id",
        "preflight_token",
        "ordinal",
        "service_unit_name",
        "target_cgroup_name",
        "systemd_run_argv_sha256",
        "failure_reason",
        "launch_error",
        "failure_components",
        "launch_attempt_observed_exact",
        "launch_attempt_recovery_raw_byte_count",
        "launch_attempt_recovery_raw_sha256",
        "returncode",
        "timed_out",
        "output_limit_exceeded",
        "stdout",
        "stderr",
        "inner_observation",
        "inventory_before_launch_failure",
        "prelaunch_absence",
        "postlaunch_absence",
        "deadline_contract",
        "unit_absent",
        "target_absent",
        "source_unit_absent",
        "source_path_absent",
        "target_unit_absent",
        "target_path_absent",
        "launch_receipt_path_created",
        "launch_receipt_publication_completion_claim",
        "launch_receipt_publication_artifact",
        "launch_receipt_publication_stage_class",
        "launch_receipt_observed_exact",
        "launch_receipt_recovery_raw_byte_count",
        "launch_receipt_recovery_raw_sha256",
        "launch_receipt_recovery_error",
        "launch_receipt_decision_stage",
        "launch_receipt_verified_monotonic_ns",
        "launch_receipt_raw_sha256",
        "remaining_after_launch_receipt_publication_ns",
        "launch_success_seal_path_created",
        "launch_success_seal_publication_completion_claim",
        "launch_success_seal_publication_stage_class",
        "launch_success_seal_observed_exact",
        "launch_success_seal_recovery_raw_byte_count",
        "launch_success_seal_recovery_raw_sha256",
        "launch_success_seal_recovery_error",
        "scientific_occurrence_started",
        "campaign_actual_measurement",
        "outer_launch_failure_id",
    }
)
OUTER_FAILURE_COMPONENT_FIELDS = frozenset(
    {
        "process_adapter_error",
        "deadline_gate_error",
        "inner_observation_error",
        "postlaunch_absence_error",
    }
)
OUTER_SPECIAL_FAILURE_REASONS = frozenset(
    {
        "LAUNCH_ATTEMPT_PUBLICATION_FAILED",
        "AFTER_ATTEMPT_DEADLINE_GATE_FAILED",
        "SYSTEMD_INVOCATION_VALIDATION_FAILED",
        "LAUNCH_RECEIPT_PUBLICATION_FAILED_BEFORE_O_EXCL",
        "OUTER_RECEIPT_DURABILITY_RECOVERY_FAILED",
        "OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_FAILED",
        "OUTER_SUCCESS_SEAL_PUBLICATION_FAILED_BEFORE_O_EXCL",
        "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED",
    }
)
OUTER_RECEIPT_DURABLE_WRITE_FAILURE_STAGES = frozenset(
    {
        "AFTER_OPEN",
        "AFTER_INITIAL_FCHMOD",
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_CLOSE",
        "AFTER_ROOT_FSYNC",
        "AFTER_READBACK",
    }
)
OUTER_RECEIPT_EXACT_ONLY_FAILURE_STAGES = frozenset(
    {
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_CLOSE",
        "AFTER_ROOT_FSYNC",
        "AFTER_READBACK",
    }
)
OUTER_RECEIPT_POST_RETURN_STAGE = "OUTER_RECEIPT_POST_O_EXCL_EXCEPTION"
OUTER_RECEIPT_DECISION_STAGE = "AFTER_EXACT_RECEIPT_INVENTORY_READBACK"
OUTER_EXACT_BYTES_RECOVERY_STAGE = (
    "EXACT_RETAINED_BYTES_DURABILITY_RECOVERY_FAILED"
)
OUTER_STRICT_PREFIX_RECOVERY_STAGE = (
    "STRICT_PREFIX_RETAINED_BYTES_DURABILITY_RECOVERY_FAILED"
)
OUTPUT_FACT_FIELDS = frozenset({"byte_count", "sha256", "base64"})
ABSENCE_FACT_FIELDS = frozenset(
    {
        "unit_absent",
        "target_absent",
        "source_unit_absent",
        "source_path_absent",
        "target_unit_absent",
        "target_path_absent",
        "poll_count",
        "systemctl_argv",
        "source_path",
        "target_path",
    }
)
SUCCESS_SUBSTAGE_ORDER = (
    "ATTEMPT_PUBLICATION",
    "OUTER_CONTEXT",
    "SERVICE_PLACEMENT_AND_NCA_PERMISSION",
    "TARGET_CREATE",
    "CLONE3_ATOMIC_BIRTH",
    "CHILD_HANDSHAKE",
    "PIDFD_AND_MEMBERSHIP",
    "HANDSHAKE_MEMBERSHIP_CONSISTENCY",
    "CHILD_RELEASE",
    "CHILD_EXIT_ZERO",
    "CHILD_HANDLE_CLOSE",
    "TARGET_EMPTY",
    "TARGET_REMOVE",
    "TARGET_ABSENT",
    "SERVICE_HANDLE_CLOSE",
)
FAILURE_PRIMARY_AFTER_SUCCESS = frozenset(
    {"RECEIPT_BUILD", "RECEIPT_PUBLICATION"}
)
CLEANUP_SUBSTAGE_ORDER = (
    "CLEANUP_PIDFD_KILL",
    "CLEANUP_CHILD_REAP",
    "CLEANUP_CHILD_CLOSE",
    "CLEANUP_TARGET_REMOVE",
    "CLEANUP_TARGET_ABSENT",
    "CLEANUP_SERVICE_CLOSE",
    "CLEANUP_SERVICE_ALREADY_CLOSED",
)
WRITE_PERMISSION_FIELDS = frozenset(
    {
        "opened_for_write",
        "errno",
        "errno_name",
        "device",
        "inode",
        "mode",
        "owner_uid",
        "owner_gid",
    }
)
SERVICE_DETAIL_FIELDS = frozenset(
    {
        "pid",
        "uid",
        "gid",
        "membership_line",
        "app_slice_membership",
        "source_membership",
        "target_membership",
        "nearest_common_ancestor",
        "service_path",
        "service_device",
        "service_inode",
        "service_owner_uid",
        "service_owner_gid",
        "service_mode",
        "service_procs",
        "nca_cgroup_procs_write",
        "app_slice_cgroup_procs_write",
        "app_slice_cgroup_procs_write_required",
        "service_cgroup_procs_write",
        "service_type_from_outer_context",
        "delegate_from_outer_context",
        "fixed_target_absent_before_create",
        "target_manager_absent_before_create",
        "target_manager_precreate_properties",
        "target_lifecycle_contract",
        "target_lifecycle_unique_authority",
    }
)
TARGET_CREATE_DETAIL_FIELDS = frozenset(
    {
        "target_name",
        "target_unit_name",
        "target_token",
        "target_path",
        "target_membership",
        "target_device",
        "target_inode",
        "target_cgroup_type",
        "target_cgroup_procs_write",
        "initial_cgroup_procs",
        "manager_create_argv",
        "manager_create_environment",
        "manager_create_returncode",
        "manager_create_stdout",
        "manager_create_stderr",
        "manager_properties",
        "manager_poll_count",
        "manager_owned_lifecycle",
        "probe_path_deletion_calls",
    }
)
TARGET_REMOVAL_DETAIL_FIELDS = frozenset(
    {
        "removed",
        "already_absent",
        "owned_device",
        "owned_inode",
        "manager_stop_argv",
        "manager_stop_environment",
        "manager_stop_returncode",
        "manager_stop_stdout",
        "manager_stop_stderr",
        "manager_final_properties",
        "manager_poll_count",
        "probe_path_deletion_calls",
        "manager_absence_proven",
        "claimed_inode_unlinked",
    }
)
EXTERNAL_ROOT_FIELDS = frozenset(
    {
        "schema",
        "purpose",
        "ordinal",
        "failed_failure_state_id",
        "failed_launch_failure_id",
        "repair_scope",
        "failed_failure_freeze_source_fact",
        "c_probe_commit_id",
        "c_probe_tree_id",
        "probe_source_fact",
        "host_parent_fact",
        "preflight_token",
        "service_unit_name",
        "target_cgroup_name",
        "systemd_invocation_contract",
        "external_root_id",
    }
)


class PreflightError(RuntimeError):
    """Base error for a rejected or failed readiness probe."""


class AuthorityError(PreflightError):
    """The post-commit external authority is not exact."""


class ReplayForbidden(PreflightError):
    """The deterministic probe identity has already been consumed."""


class DurableWriteError(PreflightError):
    """An O_EXCL artifact may exist but did not reach verified durability."""

    def __init__(self, name: str, *, path_created: bool, stage: str) -> None:
        super().__init__(
            f"{name} publication failed at {stage}; path_created={path_created}"
        )
        self.name = name
        self.path_created = path_created
        self.stage = stage


class ReceiptPublicationUncertain(PreflightError):
    """Inner RECEIPT needs recovery; the outer layer must type any refusal."""


class OuterReceiptPublicationUncertain(PreflightError):
    """LAUNCH_RECEIPT recovery failed before a typed outer closure."""


class OuterLaunchFailurePublicationUncertain(PreflightError):
    """LAUNCH_FAILURE exists or was attempted but cannot be typed exactly."""


class PrepareReceiptPublicationUncertain(PreflightError):
    """PREPARE_RECEIPT recovery failed before a typed prepare closure."""


class PrepareFailurePublicationUncertain(PreflightError):
    """PREPARE_FAILURE exists or was attempted but cannot be typed exactly."""


class ForeignArtifactError(AuthorityError):
    """The artifact root contains a name outside the exact phase inventory."""


class TargetCreationError(OSError):
    """Target creation failed, optionally after a dev/inode ownership claim."""

    def __init__(
        self,
        error_number: int,
        message: str,
        *,
        target: "TargetHandle | None",
    ) -> None:
        super().__init__(error_number, message)
        self.target = target


class TargetPostClaimValidationError(OSError):
    """A continuous target claim exists but its returned detail was rejected."""

    def __init__(self, target: "TargetHandle") -> None:
        super().__init__(
            errno.EPROTO,
            "TARGET_CREATE post-claim detail validation rejected continuous "
            f"target device={target.device} inode={target.inode}",
        )
        self.target_device = target.device
        self.target_inode = target.inode


class TargetPostClaimDeadlineError(OSError):
    """A target claim was acquired before its stage crossed the deadline."""

    def __init__(self, target: "TargetHandle") -> None:
        super().__init__(
            errno.ETIMEDOUT,
            "TARGET_CREATE post-operation deadline crossed continuous "
            f"target device={target.device} inode={target.inode}",
        )
        self.target_device = target.device
        self.target_inode = target.inode


class ClonePostAcquireValidationError(OSError):
    """A concrete ChildHandle exists but its returned clone detail was rejected."""

    def __init__(self, child: "ChildHandle") -> None:
        super().__init__(
            errno.EPROTO,
            "CLONE3 post-acquire detail validation rejected child "
            f"pid={child.pid} pidfd={child.pidfd}",
        )
        self.child_pid = child.pid
        self.child_pidfd = child.pidfd


class ClonePostAcquireDeadlineError(OSError):
    """A child was acquired before its stage crossed the deadline."""

    def __init__(self, child: "ChildHandle") -> None:
        super().__init__(
            errno.ETIMEDOUT,
            "CLONE3 post-operation deadline crossed child "
            f"pid={child.pid} pidfd={child.pidfd}",
        )
        self.child_pid = child.pid
        self.child_pidfd = child.pidfd


class ProbeRunFailure(PreflightError):
    """A typed failure was durably emitted."""

    def __init__(self, failure_document: Mapping[str, Any]) -> None:
        super().__init__("atomic cgroup-birth preflight failed")
        self.failure_document = dict(failure_document)


class OuterLaunchFailure(PreflightError):
    """The outer launcher durably closed with LAUNCH_FAILURE."""

    def __init__(self, failure_document: Mapping[str, Any]) -> None:
        super().__init__("outer launch closed with a durable failure")
        self.failure_document = dict(failure_document)


class PrepareRunFailure(PreflightError):
    """Prepare closed with one durable PREPARE_FAILURE."""

    def __init__(self, failure_document: Mapping[str, Any]) -> None:
        super().__init__("prepare closed with a durable failure")
        self.failure_document = dict(failure_document)


class PrepareRootCreationError(OSError):
    """Artifact-root mkdir/open failed with an optional dev/inode claim."""

    def __init__(
        self,
        error_number: int,
        message: str,
        *,
        claimed_device: int | None,
        claimed_inode: int | None,
    ) -> None:
        super().__init__(error_number, message)
        self.claimed_device = claimed_device
        self.claimed_inode = claimed_inode


@dataclass(slots=True)
class PublicationOwnershipToken:
    name: str
    path_created: bool = False
    completed: bool = False


def _fail(message: str) -> NoReturn:
    raise AuthorityError(message)


def _is_lower_hex(value: Any, length: int) -> bool:
    return (
        type(value) is str
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical_value(value: Any, *, location: str = "$") -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) in {list, tuple}:
        return [
            _canonical_value(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value):
            if type(key) is not str or key in result:
                _fail(f"noncanonical mapping key at {location}")
            result[key] = _canonical_value(value[key], location=f"{location}.{key}")
        return result
    _fail(f"unsupported canonical value at {location}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8", errors="strict")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate key in canonical JSON")
        result[key] = value
    return result


def loads_canonical_json(raw: bytes) -> Any:
    if type(raw) is not bytes:
        _fail("canonical input must be bytes")
    try:
        parsed = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: _fail(f"forbidden JSON constant: {token}"),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthorityError("external root is not valid canonical JSON") from error
    if canonical_json_bytes(parsed) != raw:
        _fail("external root bytes are not canonical")
    return parsed


def _domain_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _self_id_document(
    domain: str, identity_field: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    if identity_field in payload:
        _fail("self-ID payload already contains its identity field")
    normalized = _canonical_value(payload)
    assert type(normalized) is dict
    return {**normalized, identity_field: _domain_id(domain, normalized)}


def preflight_lineage() -> dict[str, Any]:
    return {
        "failed_failure_state_id": FAILED_FAILURE_STATE_ID,
        "failed_launch_failure_id": FAILED_LAUNCH_FAILURE_ID,
        "repair_scope": REPAIR_SCOPE,
        "purpose": PURPOSE,
        "ordinal": PREFLIGHT_ORDINAL,
    }


def derive_preflight_token(lineage: Mapping[str, Any]) -> str:
    if set(lineage) != LINEAGE_FIELDS or dict(lineage) != preflight_lineage():
        _fail("preflight token lineage is not its exact five-field authority")
    return _domain_id(TOKEN_DOMAIN, dict(lineage))


def target_lineage() -> dict[str, Any]:
    return {
        "failed_failure_state_id": FAILED_FAILURE_STATE_ID,
        "failed_launch_failure_id": FAILED_LAUNCH_FAILURE_ID,
        "repair_scope": REPAIR_SCOPE,
        "purpose": TARGET_PURPOSE,
        "ordinal": TARGET_ORDINAL,
    }


def derive_target_token(lineage: Mapping[str, Any]) -> str:
    if set(lineage) != TARGET_LINEAGE_FIELDS or dict(lineage) != target_lineage():
        _fail("target token lineage is not its exact five-field authority")
    return _domain_id(TARGET_TOKEN_DOMAIN, dict(lineage))


PREFLIGHT_TOKEN = derive_preflight_token(preflight_lineage())
SERVICE_UNIT_NAME = f"acfqp-v180r12r4-preflight-{PREFLIGHT_TOKEN}.service"
TARGET_TOKEN = derive_target_token(target_lineage())
TARGET_SERVICE_UNIT_NAME = (
    f"acfqp-v180r12r4-preflight-target-{TARGET_TOKEN}.service"
)
TARGET_CGROUP_NAME = TARGET_SERVICE_UNIT_NAME


def _validate_relative_path(value: Any, expected: str) -> None:
    if type(value) is not str or value != expected:
        _fail("source fact relative path changed")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != value:
        _fail("source fact relative path is unsafe")


def validate_source_fact(
    value: Mapping[str, Any], *, expected_relative_path: str
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != SOURCE_FACT_FIELDS:
        _fail("source fact fields changed")
    _validate_relative_path(value["relative_path"], expected_relative_path)
    if (
        value["schema"] != SOURCE_FACT_SCHEMA
        or value["git_mode"] != "100644"
        or not _is_lower_hex(value["git_blob_id"], 40)
        or type(value["byte_count"]) is not int
        or value["byte_count"] <= 0
        or value["byte_count"] > 2_000_000
        or not _is_lower_hex(value["sha256"], 64)
    ):
        _fail("source fact values changed")
    return dict(value)


def validate_toolchain_executable_fact(
    value: Mapping[str, Any], *, expected_path: str
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != TOOLCHAIN_EXECUTABLE_FIELDS:
        _fail("toolchain executable fact fields changed")
    integer_fields = (
        "requested_device",
        "requested_inode",
        "requested_mode",
        "requested_owner_uid",
        "requested_owner_gid",
        "requested_link_count",
        "requested_byte_count",
        "requested_mtime_ns",
        "requested_ctime_ns",
        "device",
        "inode",
        "mode",
        "owner_uid",
        "owner_gid",
        "link_count",
        "byte_count",
    )
    if (
        value["schema"] != TOOLCHAIN_EXECUTABLE_SCHEMA
        or value["path"] != expected_path
        or type(value["resolved_path"]) is not str
        or not value["resolved_path"].startswith("/usr/bin/")
        or Path(value["resolved_path"]).resolve(strict=False)
        != Path(value["resolved_path"])
        or value["requested_kind"] not in {"REGULAR", "SYMLINK"}
        or value["requested_link_count"] < 1
        or value["requested_mode"] > 0o7777
        or value["requested_kind"] == "REGULAR"
        and value["resolved_path"] != expected_path
        or value["requested_kind"] == "SYMLINK"
        and value["resolved_path"] == expected_path
        or any(type(value[key]) is not int or value[key] < 0 for key in integer_fields)
        or value["link_count"] < 1
        or value["byte_count"] < 1
        or value["byte_count"] > MAX_TOOLCHAIN_EXECUTABLE_BYTES
        or value["mode"] > 0o7777
        or value["mode"] & 0o111 == 0
        or not _is_lower_hex(value["sha256"], 64)
    ):
        _fail("toolchain executable fact values changed")
    return dict(value)


def observe_toolchain_executable_fact(path_text: str) -> dict[str, Any]:
    if path_text not in TOOLCHAIN_EXECUTABLE_PATHS:
        _fail("toolchain executable path left its exact ordered set")
    path = Path(path_text)
    requested_before = os.stat(path, follow_symlinks=False)
    if stat.S_ISREG(requested_before.st_mode):
        requested_kind = "REGULAR"
    elif stat.S_ISLNK(requested_before.st_mode):
        requested_kind = "SYMLINK"
    else:
        _fail("toolchain requested path is neither regular nor symlink")
    resolved_path = path.resolve(strict=True)
    if (
        not resolved_path.is_absolute()
        or not str(resolved_path).startswith("/usr/bin/")
        or resolved_path.resolve(strict=True) != resolved_path
    ):
        _fail("toolchain executable did not resolve to one canonical /usr/bin file")
    descriptor = os.open(
        resolved_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        before = os.fstat(descriptor)
        named_before = os.stat(resolved_path, follow_symlinks=False)
        identity_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_uid",
            "st_gid",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) & 0o111 == 0
            or before.st_nlink < 1
            or before.st_size < 1
            or before.st_size > MAX_TOOLCHAIN_EXECUTABLE_BYTES
            or any(
                getattr(before, field) != getattr(named_before, field)
                for field in identity_fields
            )
        ):
            _fail("toolchain executable pre-read identity changed")
        remaining = before.st_size
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                raise OSError(errno.EIO, "toolchain executable read truncated")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise OSError(errno.EFBIG, "toolchain executable grew during read")
        after = os.fstat(descriptor)
        named_after = os.stat(resolved_path, follow_symlinks=False)
        requested_after = os.stat(path, follow_symlinks=False)
        requested_identity_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_uid",
            "st_gid",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if any(
            getattr(before, field) != getattr(after, field)
            or getattr(before, field) != getattr(named_after, field)
            for field in identity_fields
        ) or any(
            getattr(requested_before, field) != getattr(requested_after, field)
            for field in requested_identity_fields
        ) or path.resolve(strict=True) != resolved_path:
            _fail("toolchain executable identity changed during read")
        raw = b"".join(chunks)
        fact = {
            "schema": TOOLCHAIN_EXECUTABLE_SCHEMA,
            "path": path_text,
            "resolved_path": str(resolved_path),
            "requested_kind": requested_kind,
            "requested_device": requested_before.st_dev,
            "requested_inode": requested_before.st_ino,
            "requested_mode": stat.S_IMODE(requested_before.st_mode),
            "requested_owner_uid": requested_before.st_uid,
            "requested_owner_gid": requested_before.st_gid,
            "requested_link_count": requested_before.st_nlink,
            "requested_byte_count": requested_before.st_size,
            "requested_mtime_ns": requested_before.st_mtime_ns,
            "requested_ctime_ns": requested_before.st_ctime_ns,
            "device": before.st_dev,
            "inode": before.st_ino,
            "mode": stat.S_IMODE(before.st_mode),
            "owner_uid": before.st_uid,
            "owner_gid": before.st_gid,
            "link_count": before.st_nlink,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    finally:
        os.close(descriptor)
    return validate_toolchain_executable_fact(fact, expected_path=path_text)


def observe_toolchain_facts() -> list[dict[str, Any]]:
    return [
        observe_toolchain_executable_fact(path)
        for path in TOOLCHAIN_EXECUTABLE_PATHS
    ]


def validate_toolchain_facts(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != len(TOOLCHAIN_EXECUTABLE_PATHS):
        _fail("toolchain fact inventory changed")
    retained = [
        validate_toolchain_executable_fact(row, expected_path=path)
        for row, path in zip(value, TOOLCHAIN_EXECUTABLE_PATHS)
    ]
    if [row["path"] for row in retained] != list(TOOLCHAIN_EXECUTABLE_PATHS):
        _fail("toolchain fact order changed")
    return retained


def validate_live_toolchain_facts(expected: Any) -> None:
    retained = validate_toolchain_facts(expected)
    if observe_toolchain_facts() != retained:
        _fail("live six-binary toolchain drifted from external authority")


def validate_host_parent_fact(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != HOST_PARENT_FIELDS:
        _fail("host parent fact fields changed")
    integer_fields = (
        "mount_device",
        "mount_inode",
        "app_slice_device",
        "app_slice_inode",
        "owner_uid",
        "owner_gid",
        "mode",
        "cgroup_namespace_inode",
        "cgroup_procs_device",
        "cgroup_procs_inode",
        "cgroup_procs_owner_uid",
        "cgroup_procs_owner_gid",
        "cgroup_procs_mode",
        "runtime_dir_device",
        "runtime_dir_inode",
        "runtime_dir_owner_uid",
        "runtime_dir_owner_gid",
        "runtime_dir_mode",
        "user_bus_device",
        "user_bus_inode",
        "user_bus_owner_uid",
        "user_bus_owner_gid",
        "user_bus_mode",
    )
    toolchain_facts = validate_toolchain_facts(value["toolchain_facts"])
    if (
        value["schema"] != HOST_PARENT_SCHEMA
        or value["mount_point"] != "/sys/fs/cgroup"
        or type(value["app_slice_path"]) is not str
        or not value["app_slice_path"].startswith("/sys/fs/cgroup/")
        or not value["app_slice_path"].endswith("/app.slice")
        or value["cgroup_type"] != "domain"
        or any(type(value[field]) is not int or value[field] < 0 for field in integer_fields)
        or type(value["controllers"]) is not list
        or type(value["subtree_control"]) is not list
        or value["controllers"] != sorted(set(value["controllers"]))
        or value["subtree_control"] != sorted(set(value["subtree_control"]))
        or any(type(item) is not str or not item for item in value["controllers"])
        or any(type(item) is not str or not item for item in value["subtree_control"])
        or value["runtime_dir_path"] != f"/run/user/{value['owner_uid']}"
        or value["user_bus_path"] != f"/run/user/{value['owner_uid']}/bus"
        or value["runtime_dir_owner_uid"] != value["owner_uid"]
        or value["runtime_dir_owner_gid"] != value["owner_gid"]
        or value["runtime_dir_mode"] != 0o700
        or value["user_bus_owner_uid"] != value["owner_uid"]
        or value["user_bus_owner_gid"] != value["owner_gid"]
        or value["user_bus_mode"] > 0o7777
        or value["user_bus_file_type"] != "socket"
    ):
        _fail("host parent fact values changed")
    return {**dict(value), "toolchain_facts": toolchain_facts}


def expected_clean_environment(
    external_root_path: str, external_root_sha256: str
) -> dict[str, str]:
    if not Path(external_root_path).is_absolute() or not _is_lower_hex(
        external_root_sha256, 64
    ):
        _fail("external-root environment authority is malformed")
    return {
        EXTERNAL_ROOT_PATH_ENV: external_root_path,
        EXTERNAL_ROOT_SHA256_ENV: external_root_sha256,
        **STATIC_CLEAN_ENVIRONMENT,
    }


def expected_prepare_environment() -> dict[str, str]:
    return dict(STATIC_CLEAN_ENVIRONMENT)


def expected_outer_launch_environment(uid: int) -> dict[str, str]:
    if type(uid) is not int or uid < 0:
        _fail("outer launch uid is malformed")
    runtime_dir = f"/run/user/{uid}"
    return {
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime_dir}/bus",
        "LC_ALL": STATIC_CLEAN_ENVIRONMENT["LC_ALL"],
        "PATH": STATIC_CLEAN_ENVIRONMENT["PATH"],
        "PYTHONDONTWRITEBYTECODE": STATIC_CLEAN_ENVIRONMENT[
            "PYTHONDONTWRITEBYTECODE"
        ],
        "XDG_RUNTIME_DIR": runtime_dir,
    }


def prepare_journal_relative_paths() -> dict[str, str]:
    parent = PurePosixPath(ARTIFACT_ROOT_RELATIVE_PATH).parent
    return {
        "attempt": str(parent / PREPARE_ATTEMPT_NAME),
        "failure": str(parent / PREPARE_FAILURE_NAME),
        "receipt": str(parent / PREPARE_RECEIPT_NAME),
    }


def _observe_umask() -> int:
    previous = os.umask(REQUIRED_UMASK)
    os.umask(previous)
    return previous


def validate_runtime_contract(
    mode: str,
    *,
    environ: Mapping[str, str] | None = None,
    executable: str | None = None,
    flags: Any = None,
    orig_argv: Sequence[str] | None = None,
    source_path: Path | None = None,
    umask_observer: Callable[[], int] = _observe_umask,
) -> dict[str, Any]:
    if mode not in {"--prepare", "--launch", "--probe"}:
        _fail("runtime mode is not exact")
    live_environment = dict(os.environ if environ is None else environ)
    live_executable = sys.executable if executable is None else executable
    live_flags = sys.flags if flags is None else flags
    live_orig_argv = list(
        getattr(sys, "orig_argv", ()) if orig_argv is None else orig_argv
    )
    running_source = (
        Path(__file__).resolve() if source_path is None else source_path.resolve()
    )
    if Path(live_executable).resolve() != Path(PYTHON_BINARY).resolve():
        _fail("runtime executable is not realpath /usr/bin/python3")
    expected_orig_argv = [
        PYTHON_BINARY,
        "-I",
        "-S",
        "-B",
        str(running_source),
        mode,
    ]
    if live_orig_argv != expected_orig_argv:
        _fail("runtime sys.orig_argv changed")
    required_flags = {
        "isolated": 1,
        "no_site": 1,
        "no_user_site": 1,
        "dont_write_bytecode": 1,
    }
    if any(
        getattr(live_flags, name, None) != expected
        for name, expected in required_flags.items()
    ):
        _fail("runtime Python isolation flags changed")
    observed_umask = umask_observer()
    if observed_umask != REQUIRED_UMASK:
        _fail("runtime umask is not exact 0077")
    if mode == "--prepare":
        expected_environment = expected_prepare_environment()
    elif mode == "--launch":
        expected_environment = expected_outer_launch_environment(os.geteuid())
    else:
        if set(live_environment) != {
            EXTERNAL_ROOT_PATH_ENV,
            EXTERNAL_ROOT_SHA256_ENV,
            *STATIC_CLEAN_ENVIRONMENT,
        }:
            _fail("probe runtime environment keyset changed")
        expected_environment = expected_clean_environment(
            live_environment.get(EXTERNAL_ROOT_PATH_ENV, ""),
            live_environment.get(EXTERNAL_ROOT_SHA256_ENV, ""),
        )
    if live_environment != expected_environment:
        _fail("runtime environment is not its exact minimal contract")
    return {
        "mode": mode,
        "executable_realpath": str(Path(live_executable).resolve()),
        "orig_argv": live_orig_argv,
        "python_flags": required_flags,
        "umask": observed_umask,
        "environment": expected_environment,
    }


def build_target_lifecycle_contract(uid: int) -> dict[str, Any]:
    environment = expected_outer_launch_environment(uid)
    return {
        "schema": TARGET_LIFECYCLE_SCHEMA,
        "purpose": TARGET_PURPOSE,
        "ordinal": TARGET_ORDINAL,
        "target_token": TARGET_TOKEN,
        "unit_name": TARGET_SERVICE_UNIT_NAME,
        "cgroup_name": TARGET_CGROUP_NAME,
        "slice": SERVICE_SLICE,
        "service_type": TARGET_SERVICE_TYPE,
        "remain_after_exit": True,
        "delegate": True,
        "umask": REQUIRED_UMASK,
        "collect": True,
        "lifecycle_authority": "SYSTEMD_USER_MANAGER_ONLY",
        "binds_to_unit": SERVICE_UNIT_NAME,
        "after_unit": SERVICE_UNIT_NAME,
        "kill_mode": "control-group",
        "timeout_stop_seconds": TARGET_UNIT_STOP_TIMEOUT_SECONDS,
        "environment": environment,
        "create_argv": [
            SYSTEMD_RUN,
            "--user",
            "--collect",
            "--quiet",
            "--no-ask-password",
            f"--unit={TARGET_SERVICE_UNIT_NAME}",
            f"--slice={SERVICE_SLICE}",
            f"--service-type={TARGET_SERVICE_TYPE}",
            "--remain-after-exit",
            "--property=Delegate=yes",
            "--property=UMask=0077",
            "--property=KillMode=control-group",
            f"--property=BindsTo={SERVICE_UNIT_NAME}",
            f"--property=After={SERVICE_UNIT_NAME}",
            f"--property=TimeoutStopSec={TARGET_UNIT_STOP_TIMEOUT_SECONDS}s",
            "--",
            TRUE_BINARY,
        ],
        "absence_show_argv": [
            SYSTEMCTL,
            "--user",
            "--no-pager",
            "show",
            *[
                f"--property={name}"
                for name in TARGET_MANAGER_ABSENCE_PROPERTIES
            ],
            TARGET_SERVICE_UNIT_NAME,
        ],
        "active_show_argv": [
            SYSTEMCTL,
            "--user",
            "--no-pager",
            "show",
            *[
                f"--property={name}"
                for name in TARGET_MANAGER_ACTIVE_PROPERTIES
            ],
            TARGET_SERVICE_UNIT_NAME,
        ],
        "stop_argv": [
            SYSTEMCTL,
            "--user",
            "--no-block",
            "--no-ask-password",
            "stop",
            TARGET_SERVICE_UNIT_NAME,
        ],
        "executable": TRUE_BINARY,
        "manager_call_timeout_seconds": TARGET_MANAGER_CALL_TIMEOUT_SECONDS,
        "manager_process_total_bound_seconds": (
            TARGET_MANAGER_PROCESS_TOTAL_BOUND_SECONDS
        ),
        "manager_max_polls": TARGET_MANAGER_MAX_POLLS,
        "shared_inner_absolute_deadline_seconds": INNER_TOTAL_TIMEOUT_SECONDS,
    }


def validate_target_lifecycle_contract(
    value: Mapping[str, Any], *, uid: int
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != TARGET_LIFECYCLE_FIELDS:
        _fail("target lifecycle contract fields changed")
    expected = build_target_lifecycle_contract(uid)
    if dict(value) != expected:
        argv = value.get("create_argv")
        if type(argv) is list and any("--scope" == item for item in argv):
            _fail("target lifecycle --scope is forbidden")
        if type(argv) is list and any(
            item in {"--property=Delegate=no", "--property=Delegate=false"}
            for item in argv
        ):
            _fail("target lifecycle Delegate=false is forbidden")
        _fail("target lifecycle contract drifted")
    return expected


def build_systemd_invocation_contract(
    *, repository_root: Path, external_root_path: Path, artifact_root: Path
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    external_root_path = external_root_path.resolve()
    artifact_root = artifact_root.resolve()
    source_path = repository_root / PROBE_SOURCE_RELATIVE_PATH
    environment_template = {
        EXTERNAL_ROOT_PATH_ENV: str(external_root_path),
        EXTERNAL_ROOT_SHA256_ENV: EXTERNAL_ROOT_SHA256_TEMPLATE,
        **STATIC_CLEAN_ENVIRONMENT,
    }
    return {
        "schema": INVOCATION_SCHEMA,
        "repository_root": str(repository_root),
        "external_root_path": str(external_root_path),
        "artifact_root": str(artifact_root),
        "systemd_run_binary": SYSTEMD_RUN,
        "systemd_options": [
            "--user",
            "--wait",
            "--pipe",
            "--collect",
            "--quiet",
            "--no-ask-password",
            f"--unit={SERVICE_UNIT_NAME}",
            f"--slice={SERVICE_SLICE}",
            f"--service-type={SERVICE_TYPE}",
            "--property=Delegate=yes",
            "--property=UMask=0077",
            "--property=KillMode=mixed",
            f"--property=TimeoutStopSec={UNIT_STOP_TIMEOUT_SECONDS}s",
            f"--property=RuntimeMaxSec={UNIT_RUNTIME_MAX_SECONDS}s",
        ],
        "exec_prefix": [ENV_BINARY, "-i"],
        "clean_environment_template": environment_template,
        "outer_launch_environment": expected_outer_launch_environment(
            os.geteuid()
        ),
        "prepare_journal_relative_paths": prepare_journal_relative_paths(),
        "python_argv": [
            PYTHON_BINARY,
            "-I",
            "-S",
            "-B",
            str(source_path),
            "--probe",
        ],
        "service_type": SERVICE_TYPE,
        "delegate": True,
        "slice": SERVICE_SLICE,
        "scope": False,
        "target_lifecycle_contract": build_target_lifecycle_contract(
            os.geteuid()
        ),
    }


def validate_systemd_invocation_contract(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != INVOCATION_FIELDS:
        _fail("systemd invocation contract fields changed")
    try:
        repository_root = Path(value["repository_root"])
        external_root_path = Path(value["external_root_path"])
        artifact_root = Path(value["artifact_root"])
    except TypeError as error:
        raise AuthorityError("systemd invocation paths are mistyped") from error
    if not all(path.is_absolute() for path in (repository_root, external_root_path, artifact_root)):
        _fail("systemd invocation paths must be absolute")
    expected = build_systemd_invocation_contract(
        repository_root=repository_root,
        external_root_path=external_root_path,
        artifact_root=artifact_root,
    )
    if dict(value) != expected:
        options = value.get("systemd_options")
        if type(options) is list and "--scope" in options:
            _fail("--scope is forbidden; the probe requires a Type=exec service")
        if type(options) is list and "--property=Delegate=no" in options:
            _fail("Delegate=no is forbidden")
        if value.get("delegate") is not True:
            _fail("Delegate=yes is required")
        if value.get("clean_environment_template") != expected[
            "clean_environment_template"
        ]:
            _fail("clean environment template drifted")
        _fail("systemd invocation contract drifted")
    validate_target_lifecycle_contract(
        expected["target_lifecycle_contract"], uid=os.geteuid()
    )
    return expected


def build_systemd_run_command(
    invocation: Mapping[str, Any], *, external_root_sha256: str
) -> tuple[str, ...]:
    contract = validate_systemd_invocation_contract(invocation)
    if not _is_lower_hex(external_root_sha256, 64):
        _fail("external root SHA256 is malformed")
    environment = dict(contract["clean_environment_template"])
    if environment[EXTERNAL_ROOT_SHA256_ENV] != EXTERNAL_ROOT_SHA256_TEMPLATE:
        _fail("external root SHA256 template changed")
    environment[EXTERNAL_ROOT_SHA256_ENV] = external_root_sha256
    assignments = tuple(
        f"{key}={environment[key]}" for key in sorted(environment)
    )
    return (
        contract["systemd_run_binary"],
        *contract["systemd_options"],
        *contract["exec_prefix"],
        *assignments,
        *contract["python_argv"],
    )


def validate_systemd_run_command(
    argv: Sequence[str],
    invocation: Mapping[str, Any],
    *,
    external_root_sha256: str,
) -> tuple[str, ...]:
    if type(argv) not in {tuple, list} or any(type(item) is not str for item in argv):
        _fail("systemd-run argv is mistyped")
    actual = tuple(argv)
    if "--scope" in actual:
        _fail("--scope is forbidden; the probe must be a service")
    if any(item in {"--property=Delegate=no", "--property=Delegate=false"} for item in actual):
        _fail("Delegate=false is forbidden")
    expected = build_systemd_run_command(
        invocation, external_root_sha256=external_root_sha256
    )
    if actual != expected:
        _fail("systemd-run argv or clean environment drifted")
    return expected


def build_external_root_document(
    *,
    c_probe_commit_id: str,
    c_probe_tree_id: str,
    probe_source_fact: Mapping[str, Any],
    failed_failure_freeze_source_fact: Mapping[str, Any],
    host_parent_fact: Mapping[str, Any],
    systemd_invocation_contract: Mapping[str, Any],
) -> dict[str, Any]:
    if not _is_lower_hex(c_probe_commit_id, 40) or not _is_lower_hex(
        c_probe_tree_id, 40
    ):
        _fail("C_probe commit or tree ID is malformed")
    probe_fact = validate_source_fact(
        probe_source_fact, expected_relative_path=PROBE_SOURCE_RELATIVE_PATH
    )
    failure_fact = validate_source_fact(
        failed_failure_freeze_source_fact,
        expected_relative_path=FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    )
    host_fact = validate_host_parent_fact(host_parent_fact)
    invocation = validate_systemd_invocation_contract(systemd_invocation_contract)
    if invocation["outer_launch_environment"] != expected_outer_launch_environment(
        host_fact["owner_uid"]
    ):
        _fail("outer launch environment uid disagrees with the host parent")
    payload = {
        "schema": EXTERNAL_ROOT_SCHEMA,
        **preflight_lineage(),
        "failed_failure_freeze_source_fact": failure_fact,
        "c_probe_commit_id": c_probe_commit_id,
        "c_probe_tree_id": c_probe_tree_id,
        "probe_source_fact": probe_fact,
        "host_parent_fact": host_fact,
        "preflight_token": PREFLIGHT_TOKEN,
        "service_unit_name": SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        "systemd_invocation_contract": invocation,
    }
    return _self_id_document(EXTERNAL_ROOT_DOMAIN, "external_root_id", payload)


def validate_external_root_document(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != EXTERNAL_ROOT_FIELDS:
        _fail("external root fields changed")
    expected = build_external_root_document(
        c_probe_commit_id=value["c_probe_commit_id"],
        c_probe_tree_id=value["c_probe_tree_id"],
        probe_source_fact=value["probe_source_fact"],
        failed_failure_freeze_source_fact=value[
            "failed_failure_freeze_source_fact"
        ],
        host_parent_fact=value["host_parent_fact"],
        systemd_invocation_contract=value["systemd_invocation_contract"],
    )
    if dict(value) != expected:
        _fail("external root identity or fixed lineage changed")
    return expected


def _git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
    ).hexdigest()


def _read_regular_exact(path: Path, *, byte_cap: int, mode: int | None) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        named_before = os.stat(path, follow_symlinks=False)
        identity_fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size")
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > byte_cap
            or mode is not None
            and stat.S_IMODE(before.st_mode) != mode
            or any(
                getattr(before, field) != getattr(named_before, field)
                for field in identity_fields
            )
        ):
            _fail("authority input is not one bounded regular file")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                _fail("authority input ended before its exact size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("authority input grew while observed")
        after = os.fstat(descriptor)
        named_after = os.stat(path, follow_symlinks=False)
        if (
            any(
                getattr(before, field) != getattr(after, field)
                for field in identity_fields
            )
            or any(
                getattr(after, field) != getattr(named_after, field)
                for field in identity_fields
            )
        ):
            _fail("authority input identity changed while observed")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _validate_live_source_fact(repository_root: Path, fact: Mapping[str, Any]) -> None:
    path = repository_root / fact["relative_path"]
    try:
        path.relative_to(repository_root)
    except ValueError:
        _fail("source path escaped its repository root")
    if path.resolve() != path:
        _fail("source path escaped its repository root")
    raw = _read_regular_exact(path, byte_cap=2_000_000, mode=None)
    if (
        len(raw) != fact["byte_count"]
        or hashlib.sha256(raw).hexdigest() != fact["sha256"]
        or _git_blob_id(raw) != fact["git_blob_id"]
    ):
        _fail("live source bytes disagree with their C_probe fact")


@dataclass(frozen=True, slots=True)
class BoundedProcessResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool
    output_limit_exceeded: bool


def _require_before_deadline(deadline_ns: int, label: str) -> int:
    if type(deadline_ns) is not int or deadline_ns <= 0:
        _fail(f"{label} deadline is malformed")
    remaining = deadline_ns - time.monotonic_ns()
    if remaining <= 0:
        raise OSError(errno.ETIMEDOUT, f"{label} exhausted its absolute deadline")
    return remaining


def _remaining_timeout_seconds(deadline_ns: int, *, cap: int) -> int:
    if type(cap) is not int or cap <= 0:
        _fail("deadline timeout cap is malformed")
    remaining = _require_before_deadline(deadline_ns, "bounded subprocess")
    seconds = (
        remaining // 1_000_000_000
        - 2 * OUTER_TERMINATION_GRACE_SECONDS
    )
    if seconds < 1:
        raise OSError(
            errno.ETIMEDOUT,
            "less than one bounded subprocess second plus reap grace remains",
        )
    return min(cap, int(seconds))


class SubprocessAdapter(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        timeout_seconds: int,
        stdout_cap: int,
        stderr_cap: int,
        env: Mapping[str, str] | None = None,
        start_new_session: bool = False,
    ) -> BoundedProcessResult: ...


class BoundedSubprocessAdapter:
    """Drain two nonblocking pipes under byte, time, and reap bounds."""

    @staticmethod
    def _signal_process(
        process: subprocess.Popen[bytes], sig: int, start_new_session: bool
    ) -> None:
        try:
            if start_new_session:
                os.killpg(process.pid, sig)
            else:
                process.send_signal(sig)
        except ProcessLookupError:
            pass

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout_seconds: int,
        stdout_cap: int,
        stderr_cap: int,
        env: Mapping[str, str] | None = None,
        start_new_session: bool = False,
    ) -> BoundedProcessResult:
        if (
            type(argv) not in {tuple, list}
            or not argv
            or any(type(item) is not str or not item for item in argv)
            or type(timeout_seconds) is not int
            or timeout_seconds <= 0
            or type(stdout_cap) is not int
            or stdout_cap < 0
            or type(stderr_cap) is not int
            or stderr_cap < 0
        ):
            _fail("bounded subprocess contract changed")
        command = tuple(argv)
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=None if env is None else dict(env),
                close_fds=True,
                start_new_session=start_new_session,
            )
        except OSError as error:
            raise AuthorityError("bounded subprocess birth failed") from error
        assert process.stdout is not None and process.stderr is not None
        stdout_buffer = bytearray()
        stderr_buffer = bytearray()
        descriptors = {
            process.stdout.fileno(): (process.stdout, stdout_buffer, stdout_cap),
            process.stderr.fileno(): (process.stderr, stderr_buffer, stderr_cap),
        }
        poller = select.poll()
        for descriptor in descriptors:
            os.set_blocking(descriptor, False)
            poller.register(
                descriptor, select.POLLIN | select.POLLHUP | select.POLLERR
            )
        hard_deadline = time.monotonic_ns() + timeout_seconds * 1_000_000_000
        termination_deadline: int | None = None
        kill_deadline: int | None = None
        timed_out = False
        output_limit = False
        while descriptors or process.poll() is None:
            now = time.monotonic_ns()
            if termination_deadline is None and (
                now >= hard_deadline or output_limit
            ):
                timed_out = now >= hard_deadline
                self._signal_process(process, signal.SIGTERM, start_new_session)
                termination_deadline = (
                    now + OUTER_TERMINATION_GRACE_SECONDS * 1_000_000_000
                )
            elif (
                termination_deadline is not None
                and kill_deadline is None
                and now >= termination_deadline
            ):
                self._signal_process(process, signal.SIGKILL, start_new_session)
                kill_deadline = (
                    now + OUTER_TERMINATION_GRACE_SECONDS * 1_000_000_000
                )
            elif kill_deadline is not None and now >= kill_deadline:
                for descriptor, (stream, _buffer, _cap) in tuple(
                    descriptors.items()
                ):
                    poller.unregister(descriptor)
                    stream.close()
                    del descriptors[descriptor]
                if process.poll() is None:
                    raise AuthorityError(
                        "bounded subprocess did not reap after SIGKILL"
                    )
                raise AuthorityError(
                    "bounded subprocess pipes remained open after SIGKILL"
                )
            active_deadline = (
                kill_deadline
                if kill_deadline is not None
                else termination_deadline
                if termination_deadline is not None
                else hard_deadline
            )
            remaining_ns = max(0, active_deadline - now)
            timeout_ms = max(
                1, min(100, (remaining_ns + 999_999) // 1_000_000)
            )
            for descriptor, event in poller.poll(timeout_ms):
                if descriptor not in descriptors:
                    continue
                stream, buffer, cap = descriptors[descriptor]
                reads_this_event = 0
                while reads_this_event < MAX_PIPE_READS_PER_POLL_EVENT:
                    try:
                        chunk = os.read(descriptor, PIPE_READ_CHUNK_BYTES)
                    except BlockingIOError:
                        break
                    reads_this_event += 1
                    if not chunk:
                        poller.unregister(descriptor)
                        stream.close()
                        del descriptors[descriptor]
                        break
                    room = cap - len(buffer)
                    if room > 0:
                        buffer.extend(chunk[:room])
                    if len(chunk) > room:
                        output_limit = True
                        break
                    if len(chunk) < PIPE_READ_CHUNK_BYTES:
                        break
                if output_limit:
                    # Return to the outer loop immediately so TERM/KILL/reap
                    # deadlines cannot be starved by a continuously readable
                    # pipe producing full-sized chunks.
                    break
                if event & (select.POLLHUP | select.POLLERR) and descriptor in descriptors:
                    # A final zero-length read on the next iteration closes it.
                    continue
        try:
            returncode = process.wait(timeout=0)
        except subprocess.TimeoutExpired as error:
            raise AuthorityError("bounded subprocess exit status unavailable") from error
        return BoundedProcessResult(
            command,
            returncode,
            bytes(stdout_buffer),
            bytes(stderr_buffer),
            timed_out,
            output_limit,
        )


DEFAULT_SUBPROCESS_ADAPTER = BoundedSubprocessAdapter()


class OuterAbsenceObserver(Protocol):
    def observe_absence(
        self, authority: Mapping[str, Any], *, deadline_ns: int
    ) -> Mapping[str, Any]: ...


def _systemctl_absence_argv() -> tuple[str, ...]:
    return (
        SYSTEMCTL,
        "--user",
        "list-units",
        "--all",
        "--plain",
        "--no-legend",
        "--no-pager",
        SERVICE_UNIT_NAME,
        TARGET_SERVICE_UNIT_NAME,
    )


def _target_absence_path(authority: Mapping[str, Any]) -> Path:
    return (
        Path(authority["host_parent_fact"]["app_slice_path"])
        / TARGET_CGROUP_NAME
    )


def _source_absence_path(authority: Mapping[str, Any]) -> Path:
    return (
        Path(authority["host_parent_fact"]["app_slice_path"])
        / SERVICE_UNIT_NAME
    )


class SystemdCgroupAbsenceObserver:
    """Boundedly prove both transient unit and fixed target are absent."""

    def __init__(self, process_adapter: SubprocessAdapter | None = None) -> None:
        self.process_adapter = (
            DEFAULT_SUBPROCESS_ADAPTER
            if process_adapter is None
            else process_adapter
        )

    def observe_absence(
        self, authority: Mapping[str, Any], *, deadline_ns: int
    ) -> Mapping[str, Any]:
        authority = validate_external_root_document(authority)
        _require_before_deadline(deadline_ns, "outer absence observation")
        systemctl_argv = _systemctl_absence_argv()
        source_path = _source_absence_path(authority)
        target_path = _target_absence_path(authority)
        polls = 0
        last_source_unit_absent = False
        last_target_unit_absent = False
        last_source_path_absent = False
        last_target_path_absent = False
        while polls < MAX_OUTER_OBSERVATION_POLLS:
            polls += 1
            result = self.process_adapter.run(
                systemctl_argv,
                timeout_seconds=_remaining_timeout_seconds(deadline_ns, cap=5),
                stdout_cap=16 * 1024,
                stderr_cap=16 * 1024,
                env=authority["systemd_invocation_contract"][
                    "outer_launch_environment"
                ],
            )
            if (
                result.returncode != 0
                or result.timed_out
                or result.output_limit_exceeded
                or result.stderr
            ):
                raise AuthorityError("bounded systemctl absence observation failed")
            units_absent = not result.stdout.strip()
            last_source_unit_absent = units_absent
            last_target_unit_absent = units_absent
            try:
                os.stat(source_path, follow_symlinks=False)
            except FileNotFoundError:
                last_source_path_absent = True
            else:
                last_source_path_absent = False
            try:
                os.stat(target_path, follow_symlinks=False)
            except FileNotFoundError:
                last_target_path_absent = True
            else:
                last_target_path_absent = False
            if (
                last_source_unit_absent
                and last_target_unit_absent
                and last_source_path_absent
                and last_target_path_absent
            ):
                return {
                    "unit_absent": True,
                    "target_absent": True,
                    "source_unit_absent": True,
                    "source_path_absent": True,
                    "target_unit_absent": True,
                    "target_path_absent": True,
                    "poll_count": polls,
                    "systemctl_argv": list(systemctl_argv),
                    "source_path": str(source_path),
                    "target_path": str(target_path),
                }
            if time.monotonic_ns() >= deadline_ns:
                break
            time.sleep(0.025)
        raise OSError(
            errno.ETIMEDOUT,
            "unit/target absence was not jointly observed; "
            f"source_unit_absent={last_source_unit_absent}; "
            f"target_unit_absent={last_target_unit_absent}; "
            f"source_path_absent={last_source_path_absent}; "
            f"target_path_absent={last_target_path_absent}",
        )


def _git_stdout(
    repository_root: Path,
    arguments: Sequence[str],
    *,
    deadline_ns: int | None = None,
) -> bytes:
    timeout_seconds = (
        GIT_CALL_TIMEOUT_SECONDS
        if deadline_ns is None
        else _remaining_timeout_seconds(
            deadline_ns, cap=GIT_CALL_TIMEOUT_SECONDS
        )
    )
    result = DEFAULT_SUBPROCESS_ADAPTER.run(
        ["/usr/bin/git", "-C", str(repository_root), *arguments],
        timeout_seconds=timeout_seconds,
        stdout_cap=MAX_GIT_STDOUT_BYTES,
        stderr_cap=MAX_GIT_STDERR_BYTES,
        env={
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
        },
    )
    if (
        result.returncode != 0
        or result.timed_out
        or result.output_limit_exceeded
        or result.stderr
    ):
        message = result.stderr.decode("utf-8", errors="replace")[:512]
        raise AuthorityError(f"C_probe Git observation rejected: {message}")
    return result.stdout


def _deadline_git_observer(
    deadline_ns: int,
) -> Callable[[Path, Sequence[str]], bytes]:
    _require_before_deadline(deadline_ns, "Git observer construction")

    def observe(repository_root: Path, arguments: Sequence[str]) -> bytes:
        return _git_stdout(
            repository_root, arguments, deadline_ns=deadline_ns
        )

    return observe


def _canonical_repository_root(repository_root: Path) -> Path:
    if (
        not isinstance(repository_root, Path)
        or not repository_root.is_absolute()
        or repository_root.resolve() != repository_root
    ):
        _fail("repository root must be one canonical absolute path")
    metadata = os.stat(repository_root, follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode):
        _fail("repository root is not a directory")
    return repository_root


def _decode_git_hex(raw: bytes, *, length: int, label: str) -> str:
    try:
        value = raw.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise AuthorityError(f"{label} is not ASCII") from error
    if not _is_lower_hex(value, length):
        _fail(f"{label} is not one lowercase {length}-hex identity")
    if raw != (value + "\n").encode("ascii"):
        _fail(f"{label} stdout is not one exact newline-terminated identity")
    return value


def _require_tracked_index_clean(
    repository_root: Path,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes] | None = None,
) -> None:
    """Reject tracked/index drift while deliberately excluding untracked files."""

    observe_git = _git_stdout if git_stdout is None else git_stdout
    status = observe_git(
        repository_root,
        ("status", "--porcelain=v1", "--untracked-files=no"),
    )
    if status:
        _fail("tracked worktree or index differs from the C_probe HEAD")


def _source_fact_at_commit(
    repository_root: Path,
    commit_id: str,
    relative_path: str,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes] | None = None,
) -> dict[str, Any]:
    observe_git = _git_stdout if git_stdout is None else git_stdout
    _validate_relative_path(relative_path, relative_path)
    row_raw = observe_git(
        repository_root, ("ls-tree", commit_id, "--", relative_path)
    )
    try:
        row = row_raw.decode("utf-8", errors="strict").rstrip("\n")
        metadata, retained_path = row.split("\t", 1)
        git_mode, object_type, blob_id = metadata.split(" ", 2)
    except (UnicodeDecodeError, ValueError) as error:
        raise AuthorityError("C_probe tree row is not one exact blob row") from error
    if (
        retained_path != relative_path
        or git_mode != "100644"
        or object_type != "blob"
        or not _is_lower_hex(blob_id, 40)
        or "\n" in row
        or row_raw != (row + "\n").encode("utf-8")
    ):
        _fail("C_probe source tree row changed")
    blob = observe_git(repository_root, ("cat-file", "blob", blob_id))
    if not blob or len(blob) > MAX_GIT_STDOUT_BYTES:
        _fail("C_probe source blob exceeded its bounded nonempty contract")
    fact = {
        "schema": SOURCE_FACT_SCHEMA,
        "relative_path": relative_path,
        "git_mode": git_mode,
        "git_blob_id": blob_id,
        "byte_count": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
    }
    fact = validate_source_fact(fact, expected_relative_path=relative_path)
    live = _read_regular_exact(
        repository_root / relative_path,
        byte_cap=MAX_GIT_STDOUT_BYTES,
        mode=None,
    )
    if live != blob or _git_blob_id(live) != blob_id:
        _fail("live source bytes differ from the C_probe blob")
    return fact


def collect_post_c_probe_authority(
    repository_root: Path,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes] | None = None,
    host_observer: Callable[[], Mapping[str, Any]] | None = None,
    require_running_source: bool = True,
) -> dict[str, Any]:
    """Collect a source-pinned authority from an exact tracked-clean HEAD.

    Untracked paths are intentionally outside this authority.  This permits the
    independent r4 scaffold to coexist without making it a source dependency.
    """

    repository_root = _canonical_repository_root(repository_root)
    observe_git = _git_stdout if git_stdout is None else git_stdout
    observe_host = observe_host_parent_fact if host_observer is None else host_observer
    git_executable_before = observe_toolchain_executable_fact(GIT_BINARY)
    _require_tracked_index_clean(repository_root, git_stdout=observe_git)
    commit_id = _decode_git_hex(
        observe_git(repository_root, ("rev-parse", "--verify", "HEAD^{commit}")),
        length=40,
        label="C_probe HEAD commit",
    )
    tree_id = _decode_git_hex(
        observe_git(
            repository_root,
            ("rev-parse", "--verify", f"{commit_id}^{{tree}}"),
        ),
        length=40,
        label="C_probe tree",
    )
    probe_fact = _source_fact_at_commit(
        repository_root,
        commit_id,
        PROBE_SOURCE_RELATIVE_PATH,
        git_stdout=observe_git,
    )
    failure_fact = _source_fact_at_commit(
        repository_root,
        commit_id,
        FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
        git_stdout=observe_git,
    )
    if require_running_source and Path(__file__).resolve() != (
        repository_root / PROBE_SOURCE_RELATIVE_PATH
    ).resolve():
        _fail("prepare is not running the exact C_probe source path")
    external_path = repository_root / EXTERNAL_ROOT_RELATIVE_PATH
    artifact_root = repository_root / ARTIFACT_ROOT_RELATIVE_PATH
    host_fact = validate_host_parent_fact(observe_host())
    if host_fact["toolchain_facts"][0] != git_executable_before:
        _fail("Git executable changed across prepare authority collection")
    authority = build_external_root_document(
        c_probe_commit_id=commit_id,
        c_probe_tree_id=tree_id,
        probe_source_fact=probe_fact,
        failed_failure_freeze_source_fact=failure_fact,
        host_parent_fact=host_fact,
        systemd_invocation_contract=build_systemd_invocation_contract(
            repository_root=repository_root,
            external_root_path=external_path,
            artifact_root=artifact_root,
        ),
    )
    return authority


def _directory_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
    )


@dataclass(slots=True)
class PrepareParentChain:
    repository_root: Path
    descriptors: list[int]
    names: tuple[str, ...]
    identities: list[tuple[int, ...]]

    @property
    def final_fd(self) -> int:
        return self.descriptors[-1]

    @property
    def final_path(self) -> Path:
        return self.repository_root.joinpath(*self.names)

    def validate(self) -> None:
        if len(self.descriptors) != len(self.names) + 1:
            _fail("prepare parent OFD chain length changed")
        root_opened = os.fstat(self.descriptors[0])
        root_named = os.stat(self.repository_root, follow_symlinks=False)
        if (
            _directory_identity(root_opened) != self.identities[0]
            or _directory_identity(root_named) != self.identities[0]
        ):
            _fail("repository root path/OFD identity drifted")
        for index, name in enumerate(self.names, start=1):
            opened = os.fstat(self.descriptors[index])
            named = os.stat(
                name,
                dir_fd=self.descriptors[index - 1],
                follow_symlinks=False,
            )
            if (
                _directory_identity(opened) != self.identities[index]
                or _directory_identity(named) != self.identities[index]
            ):
                _fail("prepare parent path/OFD identity drifted")

    def close(self) -> None:
        while self.descriptors:
            os.close(self.descriptors.pop())

    def __enter__(self) -> "PrepareParentChain":
        self.validate()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _open_prepare_parent_chain(
    repository_root: Path, *, create: bool = True
) -> PrepareParentChain:
    repository_root = _canonical_repository_root(repository_root)
    descriptors = [
        os.open(
            repository_root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
    ]
    identities = [_directory_identity(os.fstat(descriptors[0]))]
    names = (".tmp", "exact-freeze")
    try:
        for name in names:
            parent_fd = descriptors[-1]
            if create:
                try:
                    os.mkdir(name, 0o700, dir_fd=parent_fd)
                except FileExistsError:
                    pass
                else:
                    os.fsync(parent_fd)
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
            opened = os.fstat(descriptor)
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                _directory_identity(opened) != _directory_identity(named)
                or not stat.S_ISDIR(opened.st_mode)
                or opened.st_uid != os.geteuid()
                or opened.st_gid != os.getegid()
                or stat.S_IMODE(opened.st_mode) & 0o022
            ):
                os.close(descriptor)
                _fail("prepare parent is not one private owned directory")
            descriptors.append(descriptor)
            identities.append(_directory_identity(opened))
        chain = PrepareParentChain(
            repository_root, descriptors, names, identities
        )
        chain.validate()
        return chain
    except BaseException:
        while descriptors:
            os.close(descriptors.pop())
        raise


@dataclass(frozen=True, slots=True)
class ArtifactRootClaim:
    device: int
    inode: int
    mode: int
    owner_uid: int
    owner_gid: int


@dataclass(slots=True)
class ArtifactRootOwnershipToken:
    path_created: bool = False
    path_present: bool = False
    observed_device: int | None = None
    observed_inode: int | None = None
    claim: ArtifactRootClaim | None = None
    path_matches_claim: bool = False


def _claim_artifact_root(
    parent: PrepareParentChain,
    *,
    create: bool,
    ownership: ArtifactRootOwnershipToken | None = None,
    recover_durability: bool = True,
) -> ArtifactRootClaim:
    if type(recover_durability) is not bool or (create and not recover_durability):
        _fail("artifact-root durability recovery policy changed")
    name = Path(ARTIFACT_ROOT_RELATIVE_PATH).name
    parent.validate()
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=parent.final_fd)
        except OSError as error:
            raise PrepareRootCreationError(
                error.errno or errno.EIO,
                "artifact-root mkdir failed before ownership claim",
                claimed_device=None,
                claimed_inode=None,
            ) from error
        if ownership is not None:
            ownership.path_created = True
            ownership.path_present = True
        os.fsync(parent.final_fd)
    claimed_device: int | None = None
    claimed_inode: int | None = None
    descriptor = -1
    try:
        immediate = os.stat(
            name, dir_fd=parent.final_fd, follow_symlinks=False
        )
        claimed_device, claimed_inode = immediate.st_dev, immediate.st_ino
        if ownership is not None:
            ownership.path_present = True
            ownership.observed_device = claimed_device
            ownership.observed_inode = claimed_inode
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent.final_fd,
        )
        if create:
            os.fchmod(descriptor, 0o700)
        opened = os.fstat(descriptor)
        named = os.stat(
            name, dir_fd=parent.final_fd, follow_symlinks=False
        )
        if (
            _directory_identity(opened) != _directory_identity(named)
            or opened.st_dev != claimed_device
            or opened.st_ino != claimed_inode
            or not stat.S_ISDIR(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o700
            or opened.st_nlink != 2
            or opened.st_uid != os.geteuid()
            or opened.st_gid != os.getegid()
        ):
            raise OSError(errno.ESTALE, "artifact-root ownership claim drifted")
        if recover_durability:
            os.fsync(descriptor)
            os.fsync(parent.final_fd)
        parent.validate()
        claim = ArtifactRootClaim(
            opened.st_dev,
            opened.st_ino,
            stat.S_IMODE(opened.st_mode),
            opened.st_uid,
            opened.st_gid,
        )
        if ownership is not None:
            ownership.claim = claim
            ownership.path_matches_claim = True
        return claim
    except BaseException as error:
        error_number = getattr(error, "errno", None)
        raise PrepareRootCreationError(
            error_number if type(error_number) is int else errno.EIO,
            "artifact-root initialization failed",
            claimed_device=claimed_device,
            claimed_inode=claimed_inode,
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_regular_at(
    directory_fd: int,
    name: str,
    *,
    byte_cap: int,
    mode: int,
    allow_empty: bool = False,
) -> bytes:
    descriptor = os.open(
        name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd
    )
    try:
        before = os.fstat(descriptor)
        named_before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size")
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_nlink != 1
            or before.st_size > byte_cap
            or not allow_empty
            and before.st_size == 0
            or any(
                getattr(before, field) != getattr(named_before, field)
                for field in fields
            )
        ):
            _fail("fd-relative external root is not one exact regular file")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                _fail("fd-relative external root ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("fd-relative external root grew during readback")
        after = os.fstat(descriptor)
        named_after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if any(
            getattr(before, field) != getattr(after, field)
            or getattr(after, field) != getattr(named_after, field)
            for field in fields
        ):
            _fail("fd-relative external root identity drifted")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _stabilize_exact_regular_at(
    directory_fd: int,
    name: str,
    raw: bytes,
    *,
    byte_cap: int,
) -> None:
    """Fsync and re-read exact bytes through one continuously held file OFD."""

    if type(raw) is not bytes or not raw or len(raw) > byte_cap:
        _fail("durability recovery bytes are malformed")
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=directory_fd,
    )
    try:
        before = os.fstat(descriptor)
        named_before = os.stat(
            name, dir_fd=directory_fd, follow_symlinks=False
        )
        fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_size",
            "st_uid",
            "st_gid",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if (
            any(
                getattr(before, field) != getattr(named_before, field)
                for field in fields
            )
            or not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o400
            or before.st_nlink != 1
            or before.st_size != len(raw)
        ):
            _fail("durability recovery file identity changed before fsync")

        def read_same_ofd() -> bytes:
            os.lseek(descriptor, 0, os.SEEK_SET)
            remaining = before.st_size
            chunks: list[bytes] = []
            while remaining:
                chunk = os.read(descriptor, min(64 * 1024, remaining))
                if not chunk:
                    _fail("durability recovery read ended early")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                _fail("durability recovery file grew")
            return b"".join(chunks)

        if read_same_ofd() != raw:
            _fail("durability recovery bytes are not exact before fsync")
        os.fsync(descriptor)
        os.fsync(directory_fd)
        after = os.fstat(descriptor)
        named_after = os.stat(
            name, dir_fd=directory_fd, follow_symlinks=False
        )
        if any(
            getattr(before, field) != getattr(after, field)
            or getattr(after, field) != getattr(named_after, field)
            for field in fields
        ):
            _fail("durability recovery path/OFD identity changed")
        if read_same_ofd() != raw:
            _fail("durability recovery bytes changed after parent fsync")
        final = os.fstat(descriptor)
        final_named = os.stat(
            name, dir_fd=directory_fd, follow_symlinks=False
        )
        if any(
            getattr(after, field) != getattr(final, field)
            or getattr(final, field) != getattr(final_named, field)
            for field in fields
        ):
            _fail("durability recovery final path/OFD identity changed")
    finally:
        os.close(descriptor)


class PrepareJournalStore:
    """Exact-name journal in the private parent, independent of root birth."""

    def __init__(
        self,
        parent: PrepareParentChain,
        *,
        publication_checkpoint: Callable[[str, str, int], None] | None = None,
    ) -> None:
        self.parent = parent
        self._publication_checkpoint = publication_checkpoint
        self.parent.validate()

    def inventory_names(self, *, phase: str) -> frozenset[str]:
        if type(phase) is not str or not phase:
            _fail("prepare journal phase is malformed")
        self.parent.validate()
        names: set[str] = set()
        for name in sorted(PREPARE_JOURNAL_NAMES):
            try:
                os.stat(
                    name,
                    dir_fd=self.parent.final_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                continue
            names.add(name)
        self.parent.validate()
        return frozenset(names)

    def read_exact(self, name: str, *, allow_empty: bool = False) -> bytes:
        if name not in PREPARE_JOURNAL_NAMES:
            _fail("prepare journal name left its exact namespace")
        self.parent.validate()
        raw = _read_regular_at(
            self.parent.final_fd,
            name,
            byte_cap=MAX_ARTIFACT_BYTES,
            mode=0o400,
            allow_empty=allow_empty,
        )
        self.parent.validate()
        return raw

    def stabilize_exact(self, name: str, raw: bytes) -> None:
        if name not in PREPARE_JOURNAL_NAMES:
            _fail("prepare journal stabilization name changed")
        self.parent.validate()
        _stabilize_exact_regular_at(
            self.parent.final_fd,
            name,
            raw,
            byte_cap=MAX_ARTIFACT_BYTES,
        )
        self.parent.validate()

    def require_inventory(
        self,
        expected_names: frozenset[str],
        *,
        phase: str,
        allow_partial_names: frozenset[str] = frozenset(),
    ) -> tuple[dict[str, Any], ...]:
        if (
            type(expected_names) is not frozenset
            or not expected_names.issubset(PREPARE_JOURNAL_NAMES)
            or not allow_partial_names.issubset(expected_names)
        ):
            _fail("prepare journal inventory contract changed")
        actual = self.inventory_names(phase=phase)
        if actual != expected_names:
            raise ForeignArtifactError(
                f"{phase} prepare journal mismatch: actual={sorted(actual)!r}"
            )
        rows = []
        for name in sorted(actual):
            raw = self.read_exact(
                name, allow_empty=name in allow_partial_names
            )
            rows.append(
                {
                    "name": name,
                    "byte_count": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "partial_allowed": name in allow_partial_names,
                }
            )
        if self.inventory_names(phase=f"{phase}_POST_READ") != expected_names:
            raise ForeignArtifactError(
                f"{phase} prepare journal changed during readback"
            )
        return tuple(rows)

    def write_once(
        self,
        name: str,
        raw: bytes,
        *,
        token: PublicationOwnershipToken,
        pre_open: Callable[[], None] | None = None,
    ) -> None:
        if (
            name not in PREPARE_JOURNAL_NAMES
            or type(raw) is not bytes
            or not raw
            or len(raw) > MAX_ARTIFACT_BYTES
            or type(token) is not PublicationOwnershipToken
            or token.name != name
            or token.path_created
            or token.completed
            or pre_open is not None
            and not callable(pre_open)
        ):
            _fail("prepare journal publication arguments changed")
        self.parent.validate()
        descriptor = -1
        stage = "BEFORE_OPEN"
        if pre_open is not None:
            pre_open()
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                0o400,
                dir_fd=self.parent.final_fd,
            )
            token.path_created = True
            stage = "AFTER_OPEN"
            os.fchmod(descriptor, 0o400)
            stage = "AFTER_INITIAL_FCHMOD"
            if self._publication_checkpoint is not None:
                self._publication_checkpoint(stage, name, descriptor)
            remaining = memoryview(raw)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError(errno.EIO, "journal write made no progress")
                remaining = remaining[written:]
            stage = "AFTER_FULL_WRITE"
            if self._publication_checkpoint is not None:
                self._publication_checkpoint(stage, name, descriptor)
            os.fsync(descriptor)
            stage = "AFTER_FILE_FSYNC"
            if self._publication_checkpoint is not None:
                self._publication_checkpoint(stage, name, descriptor)
            os.close(descriptor)
            descriptor = -1
            os.fsync(self.parent.final_fd)
            stage = "AFTER_PARENT_FSYNC"
            if self._publication_checkpoint is not None:
                self._publication_checkpoint(stage, name, descriptor)
            self.parent.validate()
            if self.read_exact(name) != raw:
                raise OSError(errno.EIO, "prepare journal readback changed")
            stage = "AFTER_READBACK"
            if self._publication_checkpoint is not None:
                self._publication_checkpoint(stage, name, -1)
            token.completed = True
        except FileExistsError:
            raise
        except BaseException as error:
            raise DurableWriteError(
                name, path_created=token.path_created, stage=stage
            ) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)


def _publish_external_root_once(
    parent: PrepareParentChain,
    raw: bytes,
    *,
    token: PublicationOwnershipToken,
    checkpoint: Callable[[str, str, int], None] | None = None,
) -> None:
    if not raw or len(raw) > MAX_EXTERNAL_ROOT_BYTES:
        _fail("external root exceeded its bounded nonempty contract")
    if token.path_created or token.completed:
        _fail("external-root publication token was reused")
    name = Path(EXTERNAL_ROOT_RELATIVE_PATH).name
    parent.validate()
    descriptor = -1
    stage = "BEFORE_OPEN"
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            0o400,
            dir_fd=parent.final_fd,
        )
        token.path_created = True
        stage = "AFTER_OPEN"
        os.fchmod(descriptor, 0o400)
        stage = "AFTER_INITIAL_FCHMOD"
        if checkpoint is not None:
            checkpoint(stage, name, descriptor)
        remaining = memoryview(raw)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError(errno.EIO, "external-root write made no progress")
            remaining = remaining[written:]
        stage = "AFTER_FULL_WRITE"
        if checkpoint is not None:
            checkpoint(stage, name, descriptor)
        os.fsync(descriptor)
        stage = "AFTER_FILE_FSYNC"
        if checkpoint is not None:
            checkpoint(stage, name, descriptor)
        os.close(descriptor)
        descriptor = -1
        os.fsync(parent.final_fd)
        stage = "AFTER_PARENT_FSYNC"
        if checkpoint is not None:
            checkpoint(stage, name, descriptor)
        parent.validate()
        if _read_regular_at(
            parent.final_fd,
            name,
            byte_cap=MAX_EXTERNAL_ROOT_BYTES,
            mode=0o400,
        ) != raw:
            raise OSError(errno.EIO, "external-root durable readback changed")
        token.completed = True
    except FileExistsError:
        raise
    except BaseException as error:
        raise DurableWriteError(
            "EXTERNAL_ROOT",
            path_created=token.path_created,
            stage=stage,
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def build_prepare_attempt_document(
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    authority = validate_external_root_document(authority)
    payload = {
        "schema": PREPARE_ATTEMPT_SCHEMA,
        "purpose": PURPOSE,
        "ordinal": PREFLIGHT_ORDINAL,
        "preflight_token": PREFLIGHT_TOKEN,
        "external_root_id": authority["external_root_id"],
        "external_root_path": authority["systemd_invocation_contract"][
            "external_root_path"
        ],
        "external_root_byte_count": len(external_root_raw),
        "external_root_sha256": hashlib.sha256(external_root_raw).hexdigest(),
        "artifact_root": authority["systemd_invocation_contract"][
            "artifact_root"
        ],
        "artifact_root_absent_before_attempt": True,
        "prepare_journal_relative_paths": prepare_journal_relative_paths(),
        "c_probe_commit_id": authority["c_probe_commit_id"],
        "c_probe_tree_id": authority["c_probe_tree_id"],
        "tracked_and_index_clean": True,
        "untracked_files_in_authority": False,
        "one_shot": True,
    }
    return _self_id_document(
        PREPARE_ATTEMPT_DOMAIN, "prepare_attempt_id", payload
    )


def build_prepare_receipt_document(
    prepare_attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    root_claim: ArtifactRootClaim,
) -> dict[str, Any]:
    payload = {
        "schema": PREPARE_RECEIPT_SCHEMA,
        "prepare_attempt_id": prepare_attempt["prepare_attempt_id"],
        "preflight_token": PREFLIGHT_TOKEN,
        "ordinal": PREFLIGHT_ORDINAL,
        "external_root_id": authority["external_root_id"],
        "external_root_path": prepare_attempt["external_root_path"],
        "external_root_byte_count": len(external_root_raw),
        "external_root_sha256": hashlib.sha256(external_root_raw).hexdigest(),
        "artifact_root": prepare_attempt["artifact_root"],
        "artifact_root_device": root_claim.device,
        "artifact_root_inode": root_claim.inode,
        "artifact_root_mode": root_claim.mode,
        "prepare_journal_relative_paths": prepare_attempt[
            "prepare_journal_relative_paths"
        ],
        "external_root_o_excl_owned": True,
        "external_root_canonical_0400_durable": True,
        "artifact_root_owned_0700": True,
        "tracked_and_index_clean": True,
        "untracked_files_in_authority": False,
    }
    return _self_id_document(
        PREPARE_RECEIPT_DOMAIN, "prepare_receipt_id", payload
    )


def _prepare_retained_raw_fact(
    raw: bytes, expected_raw: bytes, *, artifact: str
) -> tuple[bool, int, str]:
    if type(raw) is not bytes or type(expected_raw) is not bytes or not expected_raw:
        _fail(f"{artifact} retained-byte classification input changed")
    observed_exact = raw == expected_raw
    if not observed_exact and not (
        len(raw) < len(expected_raw) and expected_raw.startswith(raw)
    ):
        _fail(f"{artifact} retained bytes are not exact or a strict prefix")
    return observed_exact, len(raw), hashlib.sha256(raw).hexdigest()


def _prepare_failure_state_class(
    *,
    attempt_observed_exact: bool,
    receipt_path_present: bool,
    receipt_observed_exact: bool,
) -> str:
    if type(attempt_observed_exact) is not bool or type(
        receipt_path_present
    ) is not bool or type(receipt_observed_exact) is not bool:
        _fail("PREPARE_FAILURE state-class inputs changed")
    if receipt_path_present:
        if not attempt_observed_exact:
            _fail("PREPARE_RECEIPT cannot close a partial PREPARE_ATTEMPT")
        return "RECEIPT_EXACT" if receipt_observed_exact else "RECEIPT_STRICT_PREFIX"
    if receipt_observed_exact:
        _fail("absent PREPARE_RECEIPT cannot be exact")
    return (
        "ATTEMPT_EXACT_NO_RECEIPT"
        if attempt_observed_exact
        else "ATTEMPT_STRICT_PREFIX_NO_RECEIPT"
    )


def build_prepare_failure_document(
    prepare_attempt: Mapping[str, Any],
    *,
    prepare_attempt_raw: bytes,
    prepare_receipt_raw: bytes | None,
    expected_prepare_receipt_raw: bytes | None,
    retained_external_root_raw: bytes | None,
    external_root_raw: bytes,
    artifact_root_state: Mapping[str, Any],
) -> dict[str, Any]:
    expected_attempt_raw = canonical_json_bytes(prepare_attempt)
    (
        attempt_observed_exact,
        attempt_raw_byte_count,
        attempt_raw_sha256,
    ) = _prepare_retained_raw_fact(
        prepare_attempt_raw,
        expected_attempt_raw,
        artifact=PREPARE_ATTEMPT_NAME,
    )
    receipt_path_present = prepare_receipt_raw is not None
    if receipt_path_present != (expected_prepare_receipt_raw is not None):
        _fail("PREPARE_RECEIPT raw/expected presence changed")
    if receipt_path_present:
        assert prepare_receipt_raw is not None
        assert expected_prepare_receipt_raw is not None
        (
            receipt_observed_exact,
            receipt_raw_byte_count,
            receipt_raw_sha256,
        ) = _prepare_retained_raw_fact(
            prepare_receipt_raw,
            expected_prepare_receipt_raw,
            artifact=PREPARE_RECEIPT_NAME,
        )
    else:
        receipt_observed_exact = False
        receipt_raw_byte_count = None
        receipt_raw_sha256 = None
    external_path_present = retained_external_root_raw is not None
    if external_path_present:
        assert retained_external_root_raw is not None
        (
            external_observed_exact,
            external_raw_byte_count,
            external_raw_sha256,
        ) = _prepare_retained_raw_fact(
            retained_external_root_raw,
            external_root_raw,
            artifact="EXTERNAL_ROOT",
        )
    else:
        external_observed_exact = False
        external_raw_byte_count = None
        external_raw_sha256 = None
    artifact_state_fields = {
        "artifact_root_path_present",
        "artifact_root_device",
        "artifact_root_inode",
        "artifact_root_mode",
        "artifact_root_owner_uid",
        "artifact_root_owner_gid",
        "artifact_root_inventory_empty",
    }
    if set(artifact_root_state) != artifact_state_fields:
        _fail("artifact-root failure observation fields changed")
    payload = {
        "schema": PREPARE_FAILURE_SCHEMA,
        "prepare_attempt_id": prepare_attempt["prepare_attempt_id"],
        "preflight_token": PREFLIGHT_TOKEN,
        "ordinal": PREFLIGHT_ORDINAL,
        "external_root_id": prepare_attempt["external_root_id"],
        "external_root_path": prepare_attempt["external_root_path"],
        "artifact_root": prepare_attempt["artifact_root"],
        "prepare_attempt_observed_exact": attempt_observed_exact,
        "prepare_attempt_recovery_raw_byte_count": attempt_raw_byte_count,
        "prepare_attempt_recovery_raw_sha256": attempt_raw_sha256,
        "prepare_receipt_path_present": receipt_path_present,
        "prepare_receipt_observed_exact": receipt_observed_exact,
        "prepare_receipt_recovery_raw_byte_count": receipt_raw_byte_count,
        "prepare_receipt_recovery_raw_sha256": receipt_raw_sha256,
        "external_root_path_present": external_path_present,
        "external_root_observed_exact": external_observed_exact,
        "external_root_recovery_raw_byte_count": external_raw_byte_count,
        "external_root_recovery_raw_sha256": external_raw_sha256,
        **dict(artifact_root_state),
        "prepare_journal_relative_paths": prepare_attempt[
            "prepare_journal_relative_paths"
        ],
        "prepare_failure_state_class": _prepare_failure_state_class(
            attempt_observed_exact=attempt_observed_exact,
            receipt_path_present=receipt_path_present,
            receipt_observed_exact=receipt_observed_exact,
        ),
        "scientific_occurrence_started": False,
        "campaign_actual_measurement": False,
    }
    return _self_id_document(
        PREPARE_FAILURE_DOMAIN, "prepare_failure_id", payload
    )


def validate_prepare_attempt_document(
    document: Any,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    if type(document) is not dict or set(document) != PREPARE_ATTEMPT_FIELDS:
        _fail("PREPARE_ATTEMPT fields changed")
    retained = _validate_self_id(
        document,
        schema=PREPARE_ATTEMPT_SCHEMA,
        identity_field="prepare_attempt_id",
        domain=PREPARE_ATTEMPT_DOMAIN,
    )
    expected = build_prepare_attempt_document(authority, external_root_raw)
    if retained != expected:
        _fail("PREPARE_ATTEMPT/root/authority joins changed")
    return retained


def validate_prepare_receipt_document(
    document: Any,
    prepare_attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    root_claim: ArtifactRootClaim,
) -> dict[str, Any]:
    if type(document) is not dict or set(document) != PREPARE_RECEIPT_FIELDS:
        _fail("PREPARE_RECEIPT fields changed")
    retained = _validate_self_id(
        document,
        schema=PREPARE_RECEIPT_SCHEMA,
        identity_field="prepare_receipt_id",
        domain=PREPARE_RECEIPT_DOMAIN,
    )
    expected = build_prepare_receipt_document(
        prepare_attempt, authority, external_root_raw, root_claim
    )
    if retained != expected or any(
        retained[field] is not True
        for field in (
            "external_root_o_excl_owned",
            "external_root_canonical_0400_durable",
            "artifact_root_owned_0700",
            "tracked_and_index_clean",
        )
    ) or retained["untracked_files_in_authority"] is not False:
        _fail("PREPARE_RECEIPT joins or success flags changed")
    return retained


def validate_prepare_failure_document(
    document: Any, prepare_attempt: Mapping[str, Any]
) -> dict[str, Any]:
    if type(document) is not dict or set(document) != PREPARE_FAILURE_FIELDS:
        _fail("PREPARE_FAILURE fields changed")
    retained = _validate_self_id(
        document,
        schema=PREPARE_FAILURE_SCHEMA,
        identity_field="prepare_failure_id",
        domain=PREPARE_FAILURE_DOMAIN,
    )
    expected_joins = {
        "prepare_attempt_id": prepare_attempt.get("prepare_attempt_id"),
        "preflight_token": PREFLIGHT_TOKEN,
        "ordinal": PREFLIGHT_ORDINAL,
        "external_root_id": prepare_attempt.get("external_root_id"),
        "external_root_path": prepare_attempt.get("external_root_path"),
        "artifact_root": prepare_attempt.get("artifact_root"),
        "prepare_journal_relative_paths": prepare_journal_relative_paths(),
    }
    attempt_count = retained["prepare_attempt_recovery_raw_byte_count"]
    receipt_count = retained["prepare_receipt_recovery_raw_byte_count"]
    external_count = retained["external_root_recovery_raw_byte_count"]
    receipt_present = retained["prepare_receipt_path_present"]
    external_present = retained["external_root_path_present"]
    artifact_present = retained["artifact_root_path_present"]
    if (
        any(retained[key] != value for key, value in expected_joins.items())
        or type(retained["prepare_attempt_observed_exact"]) is not bool
        or type(attempt_count) is not int
        or attempt_count < 0
        or attempt_count > MAX_ARTIFACT_BYTES
        or retained["prepare_attempt_observed_exact"]
        and attempt_count == 0
        or not _is_lower_hex(
            retained["prepare_attempt_recovery_raw_sha256"], 64
        )
        or type(receipt_present) is not bool
        or type(retained["prepare_receipt_observed_exact"]) is not bool
        or receipt_present
        and (
            type(receipt_count) is not int
            or receipt_count < 0
            or receipt_count > MAX_ARTIFACT_BYTES
            or retained["prepare_receipt_observed_exact"]
            and receipt_count == 0
            or not _is_lower_hex(
                retained["prepare_receipt_recovery_raw_sha256"], 64
            )
        )
        or not receipt_present
        and (
            retained["prepare_receipt_observed_exact"] is not False
            or receipt_count is not None
            or retained["prepare_receipt_recovery_raw_sha256"] is not None
        )
        or type(external_present) is not bool
        or type(retained["external_root_observed_exact"]) is not bool
        or external_present
        and (
            type(external_count) is not int
            or external_count < 0
            or external_count > MAX_EXTERNAL_ROOT_BYTES
            or retained["external_root_observed_exact"]
            and external_count == 0
            or not _is_lower_hex(
                retained["external_root_recovery_raw_sha256"], 64
            )
        )
        or not external_present
        and (
            retained["external_root_observed_exact"] is not False
            or external_count is not None
            or retained["external_root_recovery_raw_sha256"] is not None
        )
        or type(artifact_present) is not bool
        or artifact_present
        and (
            type(retained["artifact_root_device"]) is not int
            or retained["artifact_root_device"] < 0
            or type(retained["artifact_root_inode"]) is not int
            or retained["artifact_root_inode"] <= 0
            or retained["artifact_root_mode"] != 0o700
            or type(retained["artifact_root_owner_uid"]) is not int
            or retained["artifact_root_owner_uid"] < 0
            or type(retained["artifact_root_owner_gid"]) is not int
            or retained["artifact_root_owner_gid"] < 0
            or retained["artifact_root_inventory_empty"] is not True
        )
        or not artifact_present
        and any(
            retained[field] is not None
            for field in (
                "artifact_root_device",
                "artifact_root_inode",
                "artifact_root_mode",
                "artifact_root_owner_uid",
                "artifact_root_owner_gid",
                "artifact_root_inventory_empty",
            )
        )
        or retained["prepare_failure_state_class"]
        not in PREPARE_FAILURE_STATE_CLASSES
        or retained["prepare_failure_state_class"]
        != _prepare_failure_state_class(
            attempt_observed_exact=retained[
                "prepare_attempt_observed_exact"
            ],
            receipt_path_present=receipt_present,
            receipt_observed_exact=retained[
                "prepare_receipt_observed_exact"
            ],
        )
        or retained["scientific_occurrence_started"] is not False
        or retained["campaign_actual_measurement"] is not False
    ):
        _fail("PREPARE_FAILURE joins or conservative flags changed")
    return retained


def _build_prepare_result(
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    prepare_attempt: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": PREPARE_RESULT_SCHEMA,
        "external_root_id": authority["external_root_id"],
        "external_root_path": prepare_attempt["external_root_path"],
        "external_root_byte_count": len(external_root_raw),
        "external_root_sha256": hashlib.sha256(external_root_raw).hexdigest(),
        "external_root_mode": 0o400,
        "artifact_root": prepare_attempt["artifact_root"],
        "artifact_root_mode": 0o700,
        "c_probe_commit_id": authority["c_probe_commit_id"],
        "c_probe_tree_id": authority["c_probe_tree_id"],
        "prepare_attempt_id": prepare_attempt["prepare_attempt_id"],
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "tracked_and_index_clean": True,
        "untracked_files_in_authority": False,
        "one_shot": True,
    }
    return _self_id_document(
        PREPARE_RESULT_DOMAIN, "prepare_result_id", payload
    )


def validate_prepare_success_state(
    store: PrepareJournalStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    root_claim: ArtifactRootClaim,
    *,
    recover_receipt_durability: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(recover_receipt_durability) is not bool:
        _fail("prepare success durability policy changed")
    store.require_inventory(
        PREPARED_SUCCESS_NAMES, phase="PREPARE_SUCCESS_AUTHORITY"
    )
    expected_attempt = build_prepare_attempt_document(authority, external_root_raw)
    attempt_raw = store.read_exact(PREPARE_ATTEMPT_NAME)
    attempt = validate_prepare_attempt_document(
        loads_canonical_json(attempt_raw),
        authority,
        external_root_raw,
    )
    expected_receipt = build_prepare_receipt_document(
        expected_attempt, authority, external_root_raw, root_claim
    )
    receipt_raw = store.read_exact(PREPARE_RECEIPT_NAME)
    receipt = validate_prepare_receipt_document(
        loads_canonical_json(receipt_raw),
        expected_attempt,
        authority,
        external_root_raw,
        root_claim,
    )
    if canonical_json_bytes(receipt) != receipt_raw:
        _fail("PREPARE_RECEIPT bytes are not canonical exact")
    if recover_receipt_durability:
        try:
            store.stabilize_exact(PREPARE_RECEIPT_NAME, receipt_raw)
            store.require_inventory(
                PREPARED_SUCCESS_NAMES,
                phase="PREPARE_SUCCESS_DURABILITY_RECOVERED",
            )
        except BaseException as error:
            raise PrepareReceiptPublicationUncertain(
                "PREPARE_RECEIPT exact bytes failed durability recovery"
            ) from error
    else:
        store.require_inventory(
            PREPARED_SUCCESS_NAMES,
            phase="PREPARE_SUCCESS_READ_ONLY_FINAL",
        )
        if (
            store.read_exact(PREPARE_ATTEMPT_NAME) != attempt_raw
            or store.read_exact(PREPARE_RECEIPT_NAME) != receipt_raw
        ):
            _fail("prepare success bytes changed during read-only validation")
    return expected_attempt, expected_receipt


def _observe_prepare_external_root_raw(
    parent: PrepareParentChain, external_root_raw: bytes
) -> bytes | None:
    """Return one exact/prefix external-root observation, or None if absent."""

    name = Path(EXTERNAL_ROOT_RELATIVE_PATH).name
    parent.validate()
    try:
        os.stat(name, dir_fd=parent.final_fd, follow_symlinks=False)
    except FileNotFoundError:
        parent.validate()
        return None
    except BaseException as error:
        raise AuthorityError(
            "external-root presence could not be observed"
        ) from error
    try:
        retained = _read_regular_at(
            parent.final_fd,
            name,
            byte_cap=MAX_EXTERNAL_ROOT_BYTES,
            mode=0o400,
            allow_empty=True,
        )
        _prepare_retained_raw_fact(
            retained, external_root_raw, artifact="EXTERNAL_ROOT"
        )
        parent.validate()
        return retained
    except BaseException as error:
        raise AuthorityError(
            "external root is not one readable exact or strict-prefix issuance"
        ) from error


def _observe_prepare_artifact_root_state(
    parent: PrepareParentChain,
) -> dict[str, Any]:
    """Bind the live optional artifact-root identity and prove it is empty."""

    absent = {
        "artifact_root_path_present": False,
        "artifact_root_device": None,
        "artifact_root_inode": None,
        "artifact_root_mode": None,
        "artifact_root_owner_uid": None,
        "artifact_root_owner_gid": None,
        "artifact_root_inventory_empty": None,
    }
    name = Path(ARTIFACT_ROOT_RELATIVE_PATH).name
    parent.validate()
    try:
        os.stat(name, dir_fd=parent.final_fd, follow_symlinks=False)
    except FileNotFoundError:
        parent.validate()
        return absent
    except BaseException as error:
        raise AuthorityError(
            "artifact-root presence could not be observed"
        ) from error
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent.final_fd,
        )
        opened = os.fstat(descriptor)
        named = os.stat(name, dir_fd=parent.final_fd, follow_symlinks=False)
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid")
        if (
            any(getattr(opened, field) != getattr(named, field) for field in fields)
            or not stat.S_ISDIR(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o700
            or opened.st_nlink != 2
            or opened.st_uid != os.geteuid()
            or opened.st_gid != os.getegid()
        ):
            _fail("artifact root is not one private owned mode-0700 directory")
        with os.scandir(descriptor) as entries:
            if next(entries, None) is not None:
                raise ForeignArtifactError(
                    "artifact root is not empty at prepare-failure closure"
                )
        final = os.fstat(descriptor)
        final_named = os.stat(
            name, dir_fd=parent.final_fd, follow_symlinks=False
        )
        if any(
            getattr(opened, field) != getattr(final, field)
            or getattr(final, field) != getattr(final_named, field)
            for field in fields
        ):
            _fail("artifact-root identity changed during failure observation")
        parent.validate()
        return {
            "artifact_root_path_present": True,
            "artifact_root_device": final.st_dev,
            "artifact_root_inode": final.st_ino,
            "artifact_root_mode": stat.S_IMODE(final.st_mode),
            "artifact_root_owner_uid": final.st_uid,
            "artifact_root_owner_gid": final.st_gid,
            "artifact_root_inventory_empty": True,
        }
    except BaseException as error:
        if isinstance(error, AuthorityError):
            raise
        raise AuthorityError(
            "artifact root could not be bound as one empty owned directory"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _expected_prepare_receipt_raw_for_failure(
    prepare_attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    artifact_root_state: Mapping[str, Any],
) -> bytes:
    if artifact_root_state.get("artifact_root_path_present") is not True:
        _fail("retained PREPARE_RECEIPT lacks a live artifact-root claim")
    root_claim = ArtifactRootClaim(
        artifact_root_state["artifact_root_device"],
        artifact_root_state["artifact_root_inode"],
        artifact_root_state["artifact_root_mode"],
        artifact_root_state["artifact_root_owner_uid"],
        artifact_root_state["artifact_root_owner_gid"],
    )
    return canonical_json_bytes(
        build_prepare_receipt_document(
            prepare_attempt, authority, external_root_raw, root_claim
        )
    )


def validate_prepare_failure_state(
    store: PrepareJournalStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    names = store.inventory_names(phase="PREPARE_FAILURE_AUTHORITY")
    ordinary_names = frozenset(
        {PREPARE_ATTEMPT_NAME, PREPARE_FAILURE_NAME}
    )
    receipt_failure_names = frozenset(
        {
            PREPARE_ATTEMPT_NAME,
            PREPARE_RECEIPT_NAME,
            PREPARE_FAILURE_NAME,
        }
    )
    if names not in {ordinary_names, receipt_failure_names}:
        raise ForeignArtifactError("prepare failure inventory changed")
    partial_capable_names = frozenset(
        names & {PREPARE_ATTEMPT_NAME, PREPARE_RECEIPT_NAME}
    )
    bound_rows = store.require_inventory(
        names,
        phase="PREPARE_FAILURE_AUTHORITY_BOUND",
        allow_partial_names=partial_capable_names,
    )
    expected_attempt = build_prepare_attempt_document(authority, external_root_raw)
    attempt_raw = store.read_exact(PREPARE_ATTEMPT_NAME, allow_empty=True)
    _prepare_retained_raw_fact(
        attempt_raw,
        canonical_json_bytes(expected_attempt),
        artifact=PREPARE_ATTEMPT_NAME,
    )
    failure_raw = store.read_exact(PREPARE_FAILURE_NAME)
    failure = validate_prepare_failure_document(
        loads_canonical_json(failure_raw),
        expected_attempt,
    )
    receipt_present = PREPARE_RECEIPT_NAME in names
    if receipt_present != failure["prepare_receipt_path_present"]:
        _fail("PREPARE_FAILURE receipt path fact disagrees with inventory")
    artifact_root_state = _observe_prepare_artifact_root_state(store.parent)
    retained_external_root_raw = _observe_prepare_external_root_raw(
        store.parent, external_root_raw
    )
    receipt_raw: bytes | None = None
    expected_receipt_raw: bytes | None = None
    if receipt_present:
        receipt_raw = store.read_exact(PREPARE_RECEIPT_NAME, allow_empty=True)
        expected_receipt_raw = _expected_prepare_receipt_raw_for_failure(
            expected_attempt,
            authority,
            external_root_raw,
            artifact_root_state,
        )
        _prepare_retained_raw_fact(
            receipt_raw,
            expected_receipt_raw,
            artifact=PREPARE_RECEIPT_NAME,
        )
    observed_failure = build_prepare_failure_document(
        expected_attempt,
        prepare_attempt_raw=attempt_raw,
        prepare_receipt_raw=receipt_raw,
        expected_prepare_receipt_raw=expected_receipt_raw,
        retained_external_root_raw=retained_external_root_raw,
        external_root_raw=external_root_raw,
        artifact_root_state=artifact_root_state,
    )
    if failure != observed_failure:
        _fail("PREPARE_FAILURE disagrees with live retained state")
    captured_raw = {
        PREPARE_ATTEMPT_NAME: attempt_raw,
        PREPARE_FAILURE_NAME: failure_raw,
        **(
            {PREPARE_RECEIPT_NAME: receipt_raw}
            if receipt_raw is not None
            else {}
        ),
    }
    expected_bound_rows = tuple(
        {
            "name": name,
            "byte_count": len(captured_raw[name]),
            "sha256": hashlib.sha256(captured_raw[name]).hexdigest(),
            "partial_allowed": name in partial_capable_names,
        }
        for name in sorted(names)
    )
    if bound_rows != expected_bound_rows:
        raise AuthorityError(
            "prepare failure inventory rows disagree with classified bytes"
        )
    post_rows = store.require_inventory(
        names,
        phase="PREPARE_FAILURE_AUTHORITY_POST",
        allow_partial_names=partial_capable_names,
    )
    if post_rows != bound_rows:
        raise AuthorityError(
            "prepare failure artifact bytes changed during validation"
        )
    if (
        _observe_prepare_external_root_raw(store.parent, external_root_raw)
        != retained_external_root_raw
        or _observe_prepare_artifact_root_state(store.parent)
        != artifact_root_state
    ):
        raise AuthorityError(
            "prepare failure external or artifact root changed during validation"
        )
    final_rows = store.require_inventory(
        names,
        phase="PREPARE_FAILURE_AUTHORITY_FINAL",
        allow_partial_names=partial_capable_names,
    )
    if final_rows != bound_rows:
        raise AuthorityError(
            "prepare failure artifact bytes changed during final validation"
        )
    if (
        store.read_exact(PREPARE_ATTEMPT_NAME, allow_empty=True)
        != attempt_raw
    ):
        raise AuthorityError(
            "PREPARE_ATTEMPT bytes changed after bound failure validation"
        )
    if receipt_present and (
        store.read_exact(PREPARE_RECEIPT_NAME, allow_empty=True)
        != receipt_raw
    ):
        raise AuthorityError(
            "PREPARE_RECEIPT bytes changed after bound failure validation"
        )
    if store.read_exact(PREPARE_FAILURE_NAME) != failure_raw:
        raise AuthorityError(
            "PREPARE_FAILURE bytes changed after bound validation"
        )
    return failure


def _external_root_exact_if_present(
    parent: PrepareParentChain, external_root_raw: bytes
) -> bool:
    try:
        retained = _read_regular_at(
            parent.final_fd,
            Path(EXTERNAL_ROOT_RELATIVE_PATH).name,
            byte_cap=MAX_EXTERNAL_ROOT_BYTES,
            mode=0o400,
            allow_empty=True,
        )
    except (FileNotFoundError, PreflightError, OSError):
        return False
    return retained == external_root_raw


def _observe_artifact_root_presence(
    parent: PrepareParentChain, ownership: ArtifactRootOwnershipToken
) -> None:
    try:
        observed = os.stat(
            Path(ARTIFACT_ROOT_RELATIVE_PATH).name,
            dir_fd=parent.final_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        ownership.path_present = False
        ownership.path_matches_claim = False
        ownership.observed_device = None
        ownership.observed_inode = None
        return
    ownership.path_present = True
    ownership.observed_device = observed.st_dev
    ownership.observed_inode = observed.st_ino
    ownership.path_matches_claim = (
        ownership.claim is not None
        and observed.st_dev == ownership.claim.device
        and observed.st_ino == ownership.claim.inode
    )


def _recover_retained_prepare_failure_state(
    store: PrepareJournalStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    try:
        failure_raw = store.read_exact(PREPARE_FAILURE_NAME)
    except BaseException as error:
        raise PrepareFailurePublicationUncertain(
            "retained PREPARE_FAILURE bytes are unavailable"
        ) from error
    try:
        loads_canonical_json(failure_raw)
    except AuthorityError as error:
        raise PrepareFailurePublicationUncertain(
            "retained PREPARE_FAILURE is not canonical exact"
        ) from error
    retained = validate_prepare_failure_state(
        store, authority, external_root_raw
    )
    try:
        store.stabilize_exact(PREPARE_FAILURE_NAME, failure_raw)
    except BaseException as error:
        raise PrepareFailurePublicationUncertain(
            "exact PREPARE_FAILURE failed durability recovery"
        ) from error
    recovered = validate_prepare_failure_state(
        store, authority, external_root_raw
    )
    if recovered != retained:
        _fail("PREPARE_FAILURE changed across durability recovery")
    return recovered


def _validate_published_prepare_failure_state(
    store: PrepareJournalStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    failure: Mapping[str, Any],
) -> dict[str, Any]:
    """Retry only validation of one already durable, exact failure publication."""

    expected = dict(failure)

    def validate_once() -> dict[str, Any]:
        retained = validate_prepare_failure_state(
            store, authority, external_root_raw
        )
        if retained != expected:
            _fail("published PREPARE_FAILURE changed during validation")
        return retained

    try:
        return validate_once()
    except BaseException:
        try:
            return validate_once()
        except BaseException as recovery_error:
            raise PrepareFailurePublicationUncertain(
                "durable PREPARE_FAILURE failed postpublication validation "
                "recovery"
            ) from recovery_error


def _publish_prepare_failure_terminal(
    *,
    store: PrepareJournalStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    failure: Mapping[str, Any],
    cause: BaseException,
    prepare_attempt_raw: bytes,
    prepare_receipt_raw: bytes | None,
    retained_external_root_raw: bytes | None,
    artifact_root_state: Mapping[str, Any],
    expected_before_failure: frozenset[str],
    bound_rows: tuple[dict[str, Any], ...],
    partial_names: frozenset[str],
    allow_partial_attempt: bool,
) -> NoReturn:
    failure_raw = canonical_json_bytes(failure)
    publication = PublicationOwnershipToken(PREPARE_FAILURE_NAME)

    def validate_live_state_before_open() -> None:
        try:
            if (
                _observe_prepare_external_root_raw(
                    store.parent, external_root_raw
                )
                != retained_external_root_raw
                or _observe_prepare_artifact_root_state(store.parent)
                != artifact_root_state
            ):
                _fail("prepare roots changed before failure O_EXCL")
        except BaseException as classification_error:
            raise PrepareFailurePublicationUncertain(
                "prepare roots changed before PREPARE_FAILURE O_EXCL"
            ) from classification_error
        try:
            final_rows = store.require_inventory(
                expected_before_failure,
                phase="PREPARE_BEFORE_FAILURE_PUBLICATION_FINAL",
                allow_partial_names=partial_names,
            )
        except BaseException as inventory_error:
            try:
                if store.read_exact(
                    PREPARE_ATTEMPT_NAME,
                    allow_empty=allow_partial_attempt,
                ) != prepare_attempt_raw:
                    _fail("PREPARE_ATTEMPT changed before failure O_EXCL")
            except BaseException as attempt_error:
                raise PrepareFailurePublicationUncertain(
                    "PREPARE_ATTEMPT became unavailable before "
                    "PREPARE_FAILURE O_EXCL"
                ) from attempt_error
            if prepare_receipt_raw is not None:
                try:
                    if store.read_exact(
                        PREPARE_RECEIPT_NAME, allow_empty=True
                    ) != prepare_receipt_raw:
                        _fail("PREPARE_RECEIPT changed before failure O_EXCL")
                except BaseException as receipt_error:
                    raise PrepareReceiptPublicationUncertain(
                        "PREPARE_RECEIPT became unavailable before "
                        "PREPARE_FAILURE O_EXCL"
                    ) from receipt_error
                raise PrepareReceiptPublicationUncertain(
                    "prepare inventory rows became unavailable with an owned "
                    "PREPARE_RECEIPT before PREPARE_FAILURE O_EXCL"
                ) from inventory_error
            raise PrepareFailurePublicationUncertain(
                "prepare inventory rows became unavailable before "
                "PREPARE_FAILURE O_EXCL"
            ) from inventory_error
        if final_rows != bound_rows:
            final_by_name = {row["name"]: row for row in final_rows}
            bound_by_name = {row["name"]: row for row in bound_rows}
            if prepare_receipt_raw is not None and final_by_name.get(
                PREPARE_RECEIPT_NAME
            ) != bound_by_name.get(PREPARE_RECEIPT_NAME):
                raise PrepareReceiptPublicationUncertain(
                    "PREPARE_RECEIPT inventory row changed before "
                    "PREPARE_FAILURE O_EXCL"
                )
            raise PrepareFailurePublicationUncertain(
                "prepare inventory rows changed before PREPARE_FAILURE O_EXCL"
            )
        try:
            if (
                _observe_prepare_external_root_raw(
                    store.parent, external_root_raw
                )
                != retained_external_root_raw
                or _observe_prepare_artifact_root_state(store.parent)
                != artifact_root_state
            ):
                _fail("prepare roots changed before failure O_EXCL")
        except BaseException as classification_error:
            raise PrepareFailurePublicationUncertain(
                "prepare roots changed before PREPARE_FAILURE O_EXCL"
            ) from classification_error
        try:
            if store.read_exact(
                PREPARE_ATTEMPT_NAME,
                allow_empty=allow_partial_attempt,
            ) != prepare_attempt_raw:
                _fail("PREPARE_ATTEMPT changed before failure O_EXCL")
        except BaseException as attempt_error:
            raise PrepareFailurePublicationUncertain(
                "PREPARE_ATTEMPT changed before PREPARE_FAILURE O_EXCL"
            ) from attempt_error
        if prepare_receipt_raw is not None:
            try:
                if store.read_exact(
                    PREPARE_RECEIPT_NAME, allow_empty=True
                ) != prepare_receipt_raw:
                    _fail("PREPARE_RECEIPT changed before failure O_EXCL")
            except BaseException as receipt_error:
                raise PrepareReceiptPublicationUncertain(
                    "PREPARE_RECEIPT changed before PREPARE_FAILURE O_EXCL"
                ) from receipt_error

    try:
        store.write_once(
            PREPARE_FAILURE_NAME,
            failure_raw,
            token=publication,
            pre_open=validate_live_state_before_open,
        )
    except (
        PrepareFailurePublicationUncertain,
        PrepareReceiptPublicationUncertain,
    ):
        raise
    except FileExistsError as publication_error:
        raise PrepareFailurePublicationUncertain(
            "PREPARE_FAILURE O_EXCL ownership was lost"
        ) from publication_error
    except BaseException as publication_error:
        if not publication.path_created:
            raise PrepareFailurePublicationUncertain(
                "PREPARE_FAILURE publication failed before O_EXCL"
            ) from publication_error
        try:
            retained_raw = store.read_exact(
                PREPARE_FAILURE_NAME, allow_empty=True
            )
        except BaseException as recovery_error:
            raise PrepareFailurePublicationUncertain(
                "owned PREPARE_FAILURE bytes are unavailable"
            ) from recovery_error
        if retained_raw != failure_raw:
            if len(retained_raw) < len(failure_raw) and failure_raw.startswith(
                retained_raw
            ):
                message = "owned PREPARE_FAILURE is only a canonical prefix"
            else:
                message = "owned PREPARE_FAILURE bytes are not exact"
            raise PrepareFailurePublicationUncertain(
                message
            ) from publication_error
        try:
            store.stabilize_exact(PREPARE_FAILURE_NAME, failure_raw)
        except BaseException as recovery_error:
            raise PrepareFailurePublicationUncertain(
                "exact PREPARE_FAILURE failed durability recovery"
            ) from recovery_error
        retained = _validate_published_prepare_failure_state(
            store, authority, external_root_raw, failure
        )
        raise PrepareRunFailure(retained) from publication_error
    retained = _validate_published_prepare_failure_state(
        store, authority, external_root_raw, failure
    )
    raise PrepareRunFailure(retained) from cause


def _publish_prepare_failure(
    store: PrepareJournalStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    prepare_attempt: Mapping[str, Any],
    *,
    error: BaseException,
    root_ownership: ArtifactRootOwnershipToken,
    external_publication: PublicationOwnershipToken,
    external_root_exact: bool,
    allow_partial_attempt: bool,
    receipt_publication: PublicationOwnershipToken | None = None,
    receipt_publication_stage: str | None = None,
    receipt_observed_exact: bool = False,
    receipt_recovery_error: BaseException | None = None,
) -> NoReturn:
    if (
        not isinstance(error, BaseException)
        or type(root_ownership) is not ArtifactRootOwnershipToken
        or type(external_publication) is not PublicationOwnershipToken
        or external_publication.name != "EXTERNAL_ROOT"
        or type(external_root_exact) is not bool
        or type(allow_partial_attempt) is not bool
        or receipt_publication is not None
        and (
            type(receipt_publication) is not PublicationOwnershipToken
            or receipt_publication.name != PREPARE_RECEIPT_NAME
        )
    ):
        _fail("prepare failure publication arguments changed")
    # Historical publication stages/errors are deliberately not failure
    # authority.  Only the live bytes and live filesystem state below are.
    _ = (
        root_ownership,
        external_publication,
        external_root_exact,
        receipt_publication_stage,
        receipt_observed_exact,
        receipt_recovery_error,
    )
    names_before_failure = store.inventory_names(
        phase="PREPARE_FAILURE_RECEIPT_CLASSIFICATION"
    )
    receipt_path_owned = (
        receipt_publication is not None and receipt_publication.path_created
    )
    if (PREPARE_RECEIPT_NAME in names_before_failure) != receipt_path_owned:
        raise PrepareReceiptPublicationUncertain(
            "PREPARE_RECEIPT presence is not owned by this publication token"
        )
    expected_before_failure = frozenset(
        {
            PREPARE_ATTEMPT_NAME,
            *(
                {PREPARE_RECEIPT_NAME}
                if receipt_path_owned
                else set()
            ),
        }
    )
    partial_names = set()
    if allow_partial_attempt:
        partial_names.add(PREPARE_ATTEMPT_NAME)
    if receipt_path_owned:
        partial_names.add(PREPARE_RECEIPT_NAME)
    partial_names_frozen = frozenset(partial_names)
    try:
        bound_rows = store.require_inventory(
            expected_before_failure,
            phase="PREPARE_BEFORE_FAILURE_PUBLICATION",
            allow_partial_names=partial_names_frozen,
        )
    except BaseException as classification_error:
        uncertainty_type = (
            PrepareReceiptPublicationUncertain
            if receipt_path_owned
            else PrepareFailurePublicationUncertain
        )
        raise uncertainty_type(
            "prepare journal rows could not be bound before "
            "PREPARE_FAILURE O_EXCL"
        ) from classification_error
    try:
        retained_attempt = store.read_exact(
            PREPARE_ATTEMPT_NAME, allow_empty=allow_partial_attempt
        )
        attempt_observed_exact, _, _ = _prepare_retained_raw_fact(
            retained_attempt,
            canonical_json_bytes(prepare_attempt),
            artifact=PREPARE_ATTEMPT_NAME,
        )
        if not allow_partial_attempt and not attempt_observed_exact:
            _fail("PREPARE_ATTEMPT must be exact at this failure callsite")
    except BaseException as classification_error:
        raise PrepareFailurePublicationUncertain(
            "PREPARE_ATTEMPT could not be bound before PREPARE_FAILURE O_EXCL"
        ) from classification_error
    try:
        retained_external_root_raw = _observe_prepare_external_root_raw(
            store.parent, external_root_raw
        )
        artifact_root_state = _observe_prepare_artifact_root_state(store.parent)
    except BaseException as classification_error:
        raise PrepareFailurePublicationUncertain(
            "prepare roots could not be bound before PREPARE_FAILURE O_EXCL"
        ) from classification_error
    retained_receipt_raw: bytes | None = None
    expected_receipt_raw: bytes | None = None
    if receipt_path_owned:
        try:
            expected_receipt_raw = _expected_prepare_receipt_raw_for_failure(
                prepare_attempt,
                authority,
                external_root_raw,
                artifact_root_state,
            )
            retained_receipt_raw = store.read_exact(
                PREPARE_RECEIPT_NAME, allow_empty=True
            )
            _prepare_retained_raw_fact(
                retained_receipt_raw,
                expected_receipt_raw,
                artifact=PREPARE_RECEIPT_NAME,
            )
        except BaseException as classification_error:
            raise PrepareReceiptPublicationUncertain(
                "PREPARE_RECEIPT is not one readable exact or strict-prefix "
                "issuance before PREPARE_FAILURE O_EXCL"
            ) from classification_error
    failure = build_prepare_failure_document(
        prepare_attempt,
        prepare_attempt_raw=retained_attempt,
        prepare_receipt_raw=retained_receipt_raw,
        expected_prepare_receipt_raw=expected_receipt_raw,
        retained_external_root_raw=retained_external_root_raw,
        external_root_raw=external_root_raw,
        artifact_root_state=artifact_root_state,
    )
    classified_raw = {
        PREPARE_ATTEMPT_NAME: retained_attempt,
        **(
            {PREPARE_RECEIPT_NAME: retained_receipt_raw}
            if retained_receipt_raw is not None
            else {}
        ),
    }
    expected_bound_rows = tuple(
        {
            "name": name,
            "byte_count": len(classified_raw[name]),
            "sha256": hashlib.sha256(classified_raw[name]).hexdigest(),
            "partial_allowed": name in partial_names_frozen,
        }
        for name in sorted(expected_before_failure)
    )
    if bound_rows != expected_bound_rows:
        raise PrepareFailurePublicationUncertain(
            "prepare journal inventory rows disagree with classified bytes"
        )
    _publish_prepare_failure_terminal(
        store=store,
        authority=authority,
        external_root_raw=external_root_raw,
        failure=failure,
        cause=error,
        prepare_attempt_raw=retained_attempt,
        prepare_receipt_raw=retained_receipt_raw,
        retained_external_root_raw=retained_external_root_raw,
        artifact_root_state=artifact_root_state,
        expected_before_failure=expected_before_failure,
        bound_rows=bound_rows,
        partial_names=partial_names_frozen,
        allow_partial_attempt=allow_partial_attempt,
    )


def prepare_external_root_once(
    repository_root: Path,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes] | None = None,
    host_observer: Callable[[], Mapping[str, Any]] | None = None,
    require_running_source: bool = True,
    publication_checkpoint: Callable[[str, str, int], None] | None = None,
    external_root_checkpoint: Callable[[str, str, int], None] | None = None,
    deadline_ns: int | None = None,
) -> dict[str, Any]:
    started_ns = time.monotonic_ns()
    deadline_ns = (
        started_ns + PREPARE_TOTAL_CAP_SECONDS * 1_000_000_000
        if deadline_ns is None
        else deadline_ns
    )
    _require_before_deadline(deadline_ns, "prepare authority collection")
    authority = collect_post_c_probe_authority(
        repository_root,
        git_stdout=git_stdout,
        host_observer=host_observer,
        require_running_source=require_running_source,
    )
    _require_before_deadline(deadline_ns, "prepare artifact publication")
    repository_root = _canonical_repository_root(repository_root)
    invocation = authority["systemd_invocation_contract"]
    external_path = Path(invocation["external_root_path"])
    artifact_root = Path(invocation["artifact_root"])
    external_root_raw = canonical_json_bytes(authority)
    with _open_prepare_parent_chain(repository_root) as parent:
        if (
            external_path.parent != parent.final_path
            or artifact_root.parent != parent.final_path
        ):
            _fail("prepare paths left their exact private parent OFD")
        journal = PrepareJournalStore(
            parent, publication_checkpoint=publication_checkpoint
        )
        names = journal.inventory_names(phase="PREPARE_JOURNAL_ENTRY")
        expected_attempt = build_prepare_attempt_document(
            authority, external_root_raw
        )
        expected_attempt_raw = canonical_json_bytes(expected_attempt)
        root_ownership = ArtifactRootOwnershipToken()
        external_publication = PublicationOwnershipToken("EXTERNAL_ROOT")
        if names == PREPARED_SUCCESS_NAMES:
            root_claim: ArtifactRootClaim | None = None
            try:
                root_claim = _claim_artifact_root(parent, create=False)
                root_ownership.path_present = True
                root_ownership.observed_device = root_claim.device
                root_ownership.observed_inode = root_claim.inode
                root_ownership.claim = root_claim
                root_ownership.path_matches_claim = True
                with DurableArtifactStore(
                    artifact_root,
                    expected_device_inode=(root_claim.device, root_claim.inode),
                ) as artifact_store:
                    artifact_store.require_inventory(
                        frozenset(), phase="PREPARE_RETAINED_ROOT_EMPTY"
                    )
                if not _external_root_exact_if_present(
                    parent, external_root_raw
                ):
                    _fail("prepare receipt exists without exact external root")
                validate_prepare_success_state(
                    journal, authority, external_root_raw, root_claim
                )
            except BaseException as error:
                if root_claim is None:
                    raise PrepareReceiptPublicationUncertain(
                        "retained PREPARE_RECEIPT root claim is unavailable"
                    ) from error
                expected_receipt = build_prepare_receipt_document(
                    expected_attempt, authority, external_root_raw, root_claim
                )
                try:
                    receipt_exact = (
                        journal.read_exact(PREPARE_RECEIPT_NAME)
                        == canonical_json_bytes(expected_receipt)
                    )
                except BaseException:
                    receipt_exact = False
                if not receipt_exact:
                    raise PrepareReceiptPublicationUncertain(
                        "retained PREPARE_RECEIPT is not exact"
                    ) from error
                external_publication.path_created = True
                external_publication.completed = True
                root_ownership.path_created = True
                retained_receipt_token = PublicationOwnershipToken(
                    PREPARE_RECEIPT_NAME,
                    path_created=True,
                    completed=False,
                )
                _observe_artifact_root_presence(parent, root_ownership)
                _publish_prepare_failure(
                    journal,
                    authority,
                    external_root_raw,
                    expected_attempt,
                    error=error,
                    root_ownership=root_ownership,
                    external_publication=external_publication,
                    external_root_exact=True,
                    allow_partial_attempt=False,
                    receipt_publication=retained_receipt_token,
                    receipt_publication_stage=(
                        "RETAINED_PREPARE_RECEIPT_DURABILITY_RECOVERY"
                    ),
                    receipt_observed_exact=True,
                    receipt_recovery_error=error,
                )
            raise ReplayForbidden(
                "prepare identity already has an exact durable receipt"
            )
        if names in {
            frozenset({PREPARE_ATTEMPT_NAME, PREPARE_FAILURE_NAME}),
            frozenset(
                {
                    PREPARE_ATTEMPT_NAME,
                    PREPARE_RECEIPT_NAME,
                    PREPARE_FAILURE_NAME,
                }
            ),
        }:
            failure = _recover_retained_prepare_failure_state(
                journal, authority, external_root_raw
            )
            raise PrepareRunFailure(failure)
        if names == frozenset({PREPARE_ATTEMPT_NAME}):
            retained_attempt = journal.read_exact(
                PREPARE_ATTEMPT_NAME, allow_empty=True
            )
            if not expected_attempt_raw.startswith(retained_attempt):
                raise ForeignArtifactError(
                    "retained PREPARE_ATTEMPT is not an issuance prefix"
                )
            try:
                observed_root = os.stat(
                    artifact_root.name,
                    dir_fd=parent.final_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                root_ownership.path_present = True
                root_ownership.observed_device = observed_root.st_dev
                root_ownership.observed_inode = observed_root.st_ino
            interrupted = InterruptedError(
                errno.EINTR, "retained prepare attempt lacks a terminal"
            )
            _publish_prepare_failure(
                journal,
                authority,
                external_root_raw,
                expected_attempt,
                error=interrupted,
                root_ownership=root_ownership,
                external_publication=external_publication,
                external_root_exact=_external_root_exact_if_present(
                    parent, external_root_raw
                ),
                allow_partial_attempt=True,
            )
        if names:
            raise ForeignArtifactError(
                f"illegal prepare journal inventory: {sorted(names)!r}"
            )
        try:
            os.stat(
                artifact_root.name,
                dir_fd=parent.final_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        except OSError as error:
            raise PrepareRootCreationError(
                error.errno or errno.EIO,
                "artifact-root inspection failed before prepare attempt",
                claimed_device=None,
                claimed_inode=None,
            ) from error
        else:
            raise ForeignArtifactError(
                "artifact root pre-exists without a prepare journal attempt"
            )
        attempt_token = PublicationOwnershipToken(PREPARE_ATTEMPT_NAME)
        receipt_token: PublicationOwnershipToken | None = None
        try:
            journal.write_once(
                PREPARE_ATTEMPT_NAME,
                expected_attempt_raw,
                token=attempt_token,
            )
            journal.require_inventory(
                frozenset({PREPARE_ATTEMPT_NAME}),
                phase="PREPARE_ATTEMPT_PUBLISHED",
            )
            _require_before_deadline(deadline_ns, "artifact-root creation")
            root_claim = _claim_artifact_root(
                parent, create=True, ownership=root_ownership
            )
            with DurableArtifactStore(
                artifact_root,
                expected_device_inode=(root_claim.device, root_claim.inode),
            ) as artifact_store:
                artifact_store.require_inventory(
                    frozenset(), phase="PREPARE_NEW_ROOT_EMPTY"
                )
            _require_before_deadline(deadline_ns, "external-root publication")
            _publish_external_root_once(
                parent,
                external_root_raw,
                token=external_publication,
                checkpoint=external_root_checkpoint,
            )
            expected_receipt = build_prepare_receipt_document(
                expected_attempt, authority, external_root_raw, root_claim
            )
            expected_receipt_raw = canonical_json_bytes(expected_receipt)
            receipt_token = PublicationOwnershipToken(PREPARE_RECEIPT_NAME)
            _require_before_deadline(deadline_ns, "prepare receipt publication")
            try:
                journal.write_once(
                    PREPARE_RECEIPT_NAME,
                    expected_receipt_raw,
                    token=receipt_token,
                )
            except FileExistsError as error:
                raise PrepareReceiptPublicationUncertain(
                    "unowned PREPARE_RECEIPT path forbids PREPARE_FAILURE"
                ) from error
            except BaseException as error:
                if not receipt_token.path_created:
                    raise
                try:
                    validate_prepare_success_state(
                        journal, authority, external_root_raw, root_claim
                    )
                except BaseException as recovery_error:
                    try:
                        receipt_exact = (
                            journal.read_exact(
                                PREPARE_RECEIPT_NAME, allow_empty=True
                            )
                            == expected_receipt_raw
                        )
                    except BaseException:
                        receipt_exact = False
                    _observe_artifact_root_presence(parent, root_ownership)
                    _publish_prepare_failure(
                        journal,
                        authority,
                        external_root_raw,
                        expected_attempt,
                        error=error,
                        root_ownership=root_ownership,
                        external_publication=external_publication,
                        external_root_exact=_external_root_exact_if_present(
                            parent, external_root_raw
                        ),
                        allow_partial_attempt=False,
                        receipt_publication=receipt_token,
                        receipt_publication_stage=(
                            error.stage
                            if isinstance(error, DurableWriteError)
                            else "PREPARE_RECEIPT_WRITE_EXCEPTION"
                        ),
                        receipt_observed_exact=receipt_exact,
                        receipt_recovery_error=recovery_error,
                    )
                return _build_prepare_result(
                    authority,
                    external_root_raw,
                    expected_attempt,
                    expected_receipt,
                )
            try:
                validate_prepare_success_state(
                    journal, authority, external_root_raw, root_claim
                )
            except BaseException as recovery_error:
                try:
                    receipt_exact = (
                        journal.read_exact(PREPARE_RECEIPT_NAME)
                        == expected_receipt_raw
                    )
                except BaseException:
                    receipt_exact = False
                _observe_artifact_root_presence(parent, root_ownership)
                _publish_prepare_failure(
                    journal,
                    authority,
                    external_root_raw,
                    expected_attempt,
                    error=recovery_error,
                    root_ownership=root_ownership,
                    external_publication=external_publication,
                    external_root_exact=_external_root_exact_if_present(
                        parent, external_root_raw
                    ),
                    allow_partial_attempt=False,
                    receipt_publication=receipt_token,
                    receipt_publication_stage=(
                        "AFTER_PREPARE_RECEIPT_WRITE_COMPLETED"
                    ),
                    receipt_observed_exact=receipt_exact,
                    receipt_recovery_error=recovery_error,
                )
            return _build_prepare_result(
                authority,
                external_root_raw,
                expected_attempt,
                expected_receipt,
            )
        except PrepareReceiptPublicationUncertain:
            raise
        except PrepareFailurePublicationUncertain:
            raise
        except PrepareRunFailure:
            raise
        except BaseException as error:
            if receipt_token is not None and receipt_token.path_created:
                receipt_validation_error: BaseException | None = None
                try:
                    validate_prepare_success_state(
                        journal, authority, external_root_raw, root_claim
                    )
                except BaseException as caught_validation_error:
                    receipt_validation_error = caught_validation_error
                else:
                    return _build_prepare_result(
                        authority,
                        external_root_raw,
                        expected_attempt,
                        expected_receipt,
                    )
                try:
                    receipt_exact = (
                        journal.read_exact(
                            PREPARE_RECEIPT_NAME, allow_empty=True
                        )
                        == expected_receipt_raw
                    )
                except BaseException:
                    receipt_exact = False
                if receipt_validation_error is None:
                    _fail("prepare receipt validation error was not retained")
                _observe_artifact_root_presence(parent, root_ownership)
                _publish_prepare_failure(
                    journal,
                    authority,
                    external_root_raw,
                    expected_attempt,
                    error=error,
                    root_ownership=root_ownership,
                    external_publication=external_publication,
                    external_root_exact=_external_root_exact_if_present(
                        parent, external_root_raw
                    ),
                    allow_partial_attempt=False,
                    receipt_publication=receipt_token,
                    receipt_publication_stage=(
                        error.stage
                        if isinstance(error, DurableWriteError)
                        else "AFTER_PREPARE_RECEIPT_O_EXCL"
                    ),
                    receipt_observed_exact=receipt_exact,
                    receipt_recovery_error=receipt_validation_error,
                )
            if not attempt_token.path_created:
                raise
            _observe_artifact_root_presence(parent, root_ownership)
            _publish_prepare_failure(
                journal,
                authority,
                external_root_raw,
                expected_attempt,
                error=error,
                root_ownership=root_ownership,
                external_publication=external_publication,
                external_root_exact=_external_root_exact_if_present(
                    parent, external_root_raw
                ),
                allow_partial_attempt=not attempt_token.completed,
            )


def validate_prepared_authority(
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    *,
    artifact_store: "DurableArtifactStore | None" = None,
    recover_prepare_receipt_durability: bool = True,
) -> ArtifactRootClaim:
    if type(recover_prepare_receipt_durability) is not bool:
        _fail("prepared authority durability policy changed")
    authority = validate_external_root_document(authority)
    validate_live_toolchain_facts(
        authority["host_parent_fact"]["toolchain_facts"]
    )
    invocation = authority["systemd_invocation_contract"]
    repository_root = _canonical_repository_root(
        Path(invocation["repository_root"])
    )
    external_path = Path(invocation["external_root_path"])
    artifact_root = Path(invocation["artifact_root"])
    with _open_prepare_parent_chain(repository_root, create=False) as parent:
        if (
            external_path.parent != parent.final_path
            or artifact_root.parent != parent.final_path
            or not _external_root_exact_if_present(parent, external_root_raw)
        ):
            _fail("prepared authority paths or external root changed")
        root_claim = _claim_artifact_root(
            parent,
            create=False,
            recover_durability=recover_prepare_receipt_durability,
        )
        validate_prepare_success_state(
            PrepareJournalStore(parent),
            authority,
            external_root_raw,
            root_claim,
            recover_receipt_durability=(
                recover_prepare_receipt_durability
            ),
        )
    if artifact_store is not None:
        opened = os.fstat(artifact_store.root_fd)
        if (
            artifact_store.root != artifact_root
            or opened.st_dev != root_claim.device
            or opened.st_ino != root_claim.inode
        ):
            _fail("artifact store differs from prepare receipt root claim")
    return root_claim


def _validate_c_probe_git_authority(
    repository_root: Path,
    authority: Mapping[str, Any],
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes] | None = None,
) -> None:
    observe_git = _git_stdout if git_stdout is None else git_stdout
    commit_id = authority["c_probe_commit_id"]
    tree_id = authority["c_probe_tree_id"]
    resolved_commit = _decode_git_hex(
        observe_git(
            repository_root,
            ("rev-parse", "--verify", f"{commit_id}^{{commit}}"),
        ),
        length=40,
        label="resolved C_probe commit",
    )
    resolved_tree = _decode_git_hex(
        observe_git(
            repository_root,
            ("rev-parse", "--verify", f"{commit_id}^{{tree}}"),
        ),
        length=40,
        label="resolved C_probe tree",
    )
    if resolved_commit != commit_id or resolved_tree != tree_id:
        _fail("C_probe commit/tree authority changed")
    for fact_name in (
        "probe_source_fact",
        "failed_failure_freeze_source_fact",
    ):
        fact = authority[fact_name]
        output_raw = observe_git(
            repository_root,
            ("ls-tree", commit_id, "--", fact["relative_path"]),
        )
        output = output_raw.decode("utf-8", errors="strict").rstrip("\n")
        expected = (
            f"{fact['git_mode']} blob {fact['git_blob_id']}\t"
            f"{fact['relative_path']}"
        )
        if output != expected or output_raw != (output + "\n").encode("utf-8"):
            _fail("C_probe tree source row changed")
        blob = observe_git(
            repository_root, ("cat-file", "blob", fact["git_blob_id"])
        )
        if (
            len(blob) != fact["byte_count"]
            or hashlib.sha256(blob).hexdigest() != fact["sha256"]
            or _git_blob_id(blob) != fact["git_blob_id"]
        ):
            _fail("C_probe blob bytes changed")
        live = _read_regular_exact(
            repository_root / fact["relative_path"],
            byte_cap=2_000_000,
            mode=None,
        )
        if live != blob:
            _fail("live source differs from its C_probe blob")


def load_external_root_from_clean_environment(
    environ: Mapping[str, str],
    *,
    validate_live_sources: bool = True,
    git_stdout: Callable[[Path, Sequence[str]], bytes] | None = None,
) -> tuple[dict[str, Any], bytes]:
    if type(environ) is not dict:
        environ = dict(environ)
    if set(environ) != {
        EXTERNAL_ROOT_PATH_ENV,
        EXTERNAL_ROOT_SHA256_ENV,
        *STATIC_CLEAN_ENVIRONMENT,
    }:
        _fail("probe environment is not exact and clean")
    path_text = environ.get(EXTERNAL_ROOT_PATH_ENV)
    digest = environ.get(EXTERNAL_ROOT_SHA256_ENV)
    expected_env = expected_clean_environment(str(path_text), str(digest))
    if dict(environ) != expected_env:
        _fail("probe environment values drifted")
    path = Path(path_text)
    raw = _read_regular_exact(path, byte_cap=MAX_EXTERNAL_ROOT_BYTES, mode=0o400)
    if hashlib.sha256(raw).hexdigest() != digest:
        _fail("external root SHA256 disagrees with clean environment")
    document = loads_canonical_json(raw)
    authority = validate_external_root_document(document)
    # Replay all six TCB executables before the first live source/Git action.
    # validate_prepared_authority repeats this after the artifact-root join.
    validate_live_toolchain_facts(
        authority["host_parent_fact"]["toolchain_facts"]
    )
    invocation = authority["systemd_invocation_contract"]
    if invocation["external_root_path"] != str(path):
        _fail("external root path disagrees with its invocation contract")
    expected_artifact_root = (
        Path(invocation["repository_root"]) / ARTIFACT_ROOT_RELATIVE_PATH
    )
    expected_external_root = (
        Path(invocation["repository_root"]) / EXTERNAL_ROOT_RELATIVE_PATH
    )
    if (
        Path(invocation["artifact_root"]) != expected_artifact_root
        or path != expected_external_root
    ):
        _fail("external root or artifact path left its exact repository location")
    validate_systemd_run_command(
        build_systemd_run_command(invocation, external_root_sha256=digest),
        invocation,
        external_root_sha256=digest,
    )
    if validate_live_sources:
        repository_root = Path(invocation["repository_root"])
        _validate_live_source_fact(repository_root, authority["probe_source_fact"])
        _validate_live_source_fact(
            repository_root, authority["failed_failure_freeze_source_fact"]
        )
        if Path(__file__).resolve() != (
            repository_root / PROBE_SOURCE_RELATIVE_PATH
        ).resolve():
            _fail("running probe source is outside its C_probe repository root")
        _validate_c_probe_git_authority(
            repository_root, authority, git_stdout=git_stdout
        )
    return authority, raw


def load_external_root_for_outer(
    repository_root: Path,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes] | None = None,
    host_observer: Callable[[], Mapping[str, Any]] | None = None,
    require_running_source: bool = True,
) -> tuple[dict[str, Any], bytes]:
    """Validate the retained authority before the one allowed outer launch."""

    repository_root = _canonical_repository_root(repository_root)
    observe_git = _git_stdout if git_stdout is None else git_stdout
    observe_host = observe_host_parent_fact if host_observer is None else host_observer
    external_path = repository_root / EXTERNAL_ROOT_RELATIVE_PATH
    raw = _read_regular_exact(
        external_path, byte_cap=MAX_EXTERNAL_ROOT_BYTES, mode=0o400
    )
    authority = validate_external_root_document(loads_canonical_json(raw))
    # The external authority is available before any launch-side Git command,
    # so replay the ordered six-binary TCB first and repeat it at the durable
    # prepare-state join below.
    validate_live_toolchain_facts(
        authority["host_parent_fact"]["toolchain_facts"]
    )
    invocation = authority["systemd_invocation_contract"]
    if (
        invocation["repository_root"] != str(repository_root)
        or invocation["external_root_path"] != str(external_path)
        or invocation["artifact_root"]
        != str(repository_root / ARTIFACT_ROOT_RELATIVE_PATH)
    ):
        _fail("outer authority paths changed")
    _require_tracked_index_clean(repository_root, git_stdout=observe_git)
    head = _decode_git_hex(
        observe_git(repository_root, ("rev-parse", "--verify", "HEAD^{commit}")),
        length=40,
        label="live C_probe HEAD commit",
    )
    if head != authority["c_probe_commit_id"]:
        _fail("live HEAD is not the exact C_probe commit")
    _validate_c_probe_git_authority(
        repository_root, authority, git_stdout=observe_git
    )
    _validate_live_source_fact(repository_root, authority["probe_source_fact"])
    _validate_live_source_fact(
        repository_root, authority["failed_failure_freeze_source_fact"]
    )
    if require_running_source and Path(__file__).resolve() != (
        repository_root / PROBE_SOURCE_RELATIVE_PATH
    ).resolve():
        _fail("launch is not running the exact C_probe source path")
    if validate_host_parent_fact(observe_host()) != authority["host_parent_fact"]:
        _fail("host app.slice parent fact drifted after prepare")
    digest = hashlib.sha256(raw).hexdigest()
    validate_systemd_run_command(
        build_systemd_run_command(invocation, external_root_sha256=digest),
        invocation,
        external_root_sha256=digest,
    )
    artifact_root = Path(invocation["artifact_root"])
    with DurableArtifactStore(artifact_root) as store:
        validate_prepared_authority(authority, raw, artifact_store=store)
        store.require_inventory(
            frozenset(), phase="OUTER_LOADER_PREPARED_ROOT_EMPTY"
        )
    return authority, raw


class DurableArtifactStore:
    """One root OFD with exact phase inventories and fd-relative I/O."""

    def __init__(
        self,
        root: Path,
        *,
        publication_checkpoint: Callable[[str, str, int], None] | None = None,
        expected_device_inode: tuple[int, int] | None = None,
    ) -> None:
        if not root.is_absolute() or root.resolve() != root:
            _fail("preflight artifact root must be one canonical absolute path")
        self.root = root
        self._publication_checkpoint = publication_checkpoint
        metadata = os.lstat(root)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_nlink != 2
            or metadata.st_uid != os.geteuid()
            or metadata.st_gid != os.getegid()
        ):
            _fail("preflight artifact root must be owned mode-0700 nlink-2")
        self.root_fd = os.open(
            root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        opened = os.fstat(self.root_fd)
        if expected_device_inode is not None and (
            type(expected_device_inode) is not tuple
            or len(expected_device_inode) != 2
            or (opened.st_dev, opened.st_ino) != expected_device_inode
        ):
            os.close(self.root_fd)
            self.root_fd = -1
            _fail("artifact-root reopened identity differs from mkdir claim")
        self._root_identity = (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_nlink,
            opened.st_uid,
            opened.st_gid,
        )
        self._validate_root_identity()

    def _validate_root_identity(self) -> None:
        if self.root_fd < 0:
            _fail("preflight artifact root OFD is closed")
        opened = os.fstat(self.root_fd)
        try:
            named = os.lstat(self.root)
        except FileNotFoundError as error:
            raise AuthorityError("preflight artifact root path disappeared") from error
        fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_uid",
            "st_gid",
        )
        opened_identity = tuple(getattr(opened, field) for field in fields)
        named_identity = tuple(getattr(named, field) for field in fields)
        if (
            opened_identity != self._root_identity
            or named_identity != self._root_identity
            or not stat.S_ISDIR(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o700
            or opened.st_nlink != 2
        ):
            _fail("preflight artifact root path/OFD identity drifted")

    def _checkpoint(self, stage: str, name: str, descriptor: int) -> None:
        if self._publication_checkpoint is not None:
            self._publication_checkpoint(stage, name, descriptor)

    def close(self) -> None:
        if self.root_fd >= 0:
            os.close(self.root_fd)
            self.root_fd = -1

    def __enter__(self) -> "DurableArtifactStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def exists(self, name: str) -> bool:
        if name not in ROOT_ARTIFACT_NAMES:
            _fail("artifact name left the exact preflight namespace")
        self._validate_root_identity()
        try:
            os.stat(name, dir_fd=self.root_fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return True

    def read_exact(
        self,
        name: str,
        *,
        byte_cap: int = MAX_ARTIFACT_BYTES,
        allow_empty: bool = False,
    ) -> bytes:
        if (
            name not in ROOT_ARTIFACT_NAMES
            or type(byte_cap) is not int
            or byte_cap <= 0
        ):
            _fail("fd-relative artifact read arguments changed")
        self._validate_root_identity()
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=self.root_fd,
        )
        try:
            before = os.fstat(descriptor)
            named_before = os.stat(
                name, dir_fd=self.root_fd, follow_symlinks=False
            )
            identity_fields = (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_nlink",
                "st_size",
            )
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_size < 0
                or before.st_size > byte_cap
                or not allow_empty
                and before.st_size == 0
                or any(
                    getattr(before, field) != getattr(named_before, field)
                    for field in identity_fields
                )
            ):
                _fail("artifact is not one bounded mode-0400 regular file")
            remaining = before.st_size
            chunks: list[bytes] = []
            while remaining:
                chunk = os.read(descriptor, min(64 * 1024, remaining))
                if not chunk:
                    _fail("artifact ended before its fd-relative size")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                _fail("artifact grew while read through its root OFD")
            after = os.fstat(descriptor)
            named_after = os.stat(
                name, dir_fd=self.root_fd, follow_symlinks=False
            )
            if (
                any(
                    getattr(before, field) != getattr(after, field)
                    for field in identity_fields
                )
                or any(
                    getattr(after, field) != getattr(named_after, field)
                    for field in identity_fields
                )
            ):
                _fail("artifact identity changed during fd-relative read")
            raw = b"".join(chunks)
        finally:
            os.close(descriptor)
        self._validate_root_identity()
        return raw

    def stabilize_exact(self, name: str, raw: bytes) -> None:
        """Recover durability only for an already exact canonical artifact."""

        if (
            name not in ROOT_ARTIFACT_NAMES
            or type(raw) is not bytes
            or not raw
            or len(raw) > MAX_ARTIFACT_BYTES
        ):
            _fail("artifact stabilization input is not exact")
        self._validate_root_identity()
        _stabilize_exact_regular_at(
            self.root_fd,
            name,
            raw,
            byte_cap=MAX_ARTIFACT_BYTES,
        )
        self._validate_root_identity()

    def require_inventory(
        self,
        expected_names: frozenset[str],
        *,
        phase: str,
        allow_partial_names: frozenset[str] = frozenset(),
    ) -> tuple[dict[str, Any], ...]:
        if (
            type(expected_names) is not frozenset
            or not expected_names.issubset(ROOT_ARTIFACT_NAMES)
            or not allow_partial_names.issubset(expected_names)
            or type(phase) is not str
            or not phase
        ):
            _fail("artifact phase inventory contract changed")
        actual = self.inventory_names(phase=phase)
        if actual != expected_names:
            raise ForeignArtifactError(
                f"{phase} inventory mismatch: actual={sorted(actual)!r}"
            )
        rows: list[dict[str, Any]] = []
        for name in sorted(actual):
            raw = self.read_exact(
                name, allow_empty=name in allow_partial_names
            )
            rows.append(
                {
                    "name": name,
                    "byte_count": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "partial_allowed": name in allow_partial_names,
                }
            )
        if self.inventory_names(phase=f"{phase}_POST_READ") != expected_names:
            raise ForeignArtifactError(
                f"{phase} inventory changed during fd-relative readback"
            )
        self._validate_root_identity()
        return tuple(rows)

    def inventory_names(self, *, phase: str) -> frozenset[str]:
        if type(phase) is not str or not phase:
            _fail("artifact inventory phase is malformed")
        self._validate_root_identity()
        names: list[str] = []
        total_name_bytes = 0
        with os.scandir(self.root_fd) as entries:
            for entry in entries:
                if len(names) == MAX_ARTIFACT_INVENTORY_ENTRIES:
                    raise ForeignArtifactError(
                        f"{phase} artifact inventory exceeded its entry cap"
                    )
                name = entry.name
                if type(name) is not str:
                    raise ForeignArtifactError(
                        f"{phase} artifact inventory name is mistyped"
                    )
                total_name_bytes += len(name.encode("utf-8", errors="strict"))
                if total_name_bytes > MAX_ARTIFACT_INVENTORY_NAME_BYTES:
                    raise ForeignArtifactError(
                        f"{phase} artifact inventory exceeded its name-byte cap"
                    )
                names.append(name)
        actual = frozenset(names)
        foreign = actual - ROOT_ARTIFACT_NAMES
        if foreign:
            raise ForeignArtifactError(
                f"{phase} foreign artifact names: {sorted(foreign)!r}"
            )
        self._validate_root_identity()
        return actual

    def write_once(
        self,
        name: str,
        raw: bytes,
        *,
        token: PublicationOwnershipToken | None = None,
        pre_open: Callable[[], None] | None = None,
    ) -> None:
        if (
            name not in ROOT_ARTIFACT_NAMES
            or type(raw) is not bytes
            or pre_open is not None
            and not callable(pre_open)
        ):
            _fail("write-once artifact arguments changed")
        if not raw or len(raw) > MAX_ARTIFACT_BYTES:
            _fail("write-once artifact exceeded its byte contract")
        publication = PublicationOwnershipToken(name) if token is None else token
        if (
            type(publication) is not PublicationOwnershipToken
            or publication.name != name
            or publication.path_created
            or publication.completed
        ):
            _fail("publication ownership token was reused or mistyped")
        self._validate_root_identity()
        descriptor = -1
        stage = "BEFORE_OPEN"
        if pre_open is not None:
            pre_open()
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                0o400,
                dir_fd=self.root_fd,
            )
            publication.path_created = True
            stage = "AFTER_OPEN"
            os.fchmod(descriptor, 0o400)
            stage = "AFTER_INITIAL_FCHMOD"
            self._checkpoint(stage, name, descriptor)
            remaining = memoryview(raw)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError(errno.EIO, "durable write made no progress")
                remaining = remaining[written:]
            stage = "AFTER_FULL_WRITE"
            self._checkpoint(stage, name, descriptor)
            os.fsync(descriptor)
            stage = "AFTER_FILE_FSYNC"
            self._checkpoint(stage, name, descriptor)
            os.close(descriptor)
            descriptor = -1
            stage = "AFTER_CLOSE"
            self._checkpoint(stage, name, descriptor)
            os.fsync(self.root_fd)
            stage = "AFTER_ROOT_FSYNC"
            self._checkpoint(stage, name, descriptor)
        except FileExistsError:
            raise
        except BaseException as error:
            raise DurableWriteError(
                name,
                path_created=publication.path_created,
                stage=stage,
            ) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        try:
            readback = self.read_exact(name)
            if readback != raw:
                raise OSError(errno.EIO, "stable readback changed")
            stage = "AFTER_READBACK"
            self._checkpoint(stage, name, -1)
        except BaseException as error:
            raise DurableWriteError(
                name,
                path_created=publication.path_created,
                stage=stage,
            ) from error
        publication.completed = True


def _read_inventory_byte_snapshot(
    store: Any,
    names: frozenset[str],
    *,
    allow_partial_names: frozenset[str],
) -> tuple[tuple[dict[str, Any], ...], dict[str, bytes]]:
    """Reread every retained artifact and bind the bytes to inventory rows."""

    if (
        type(names) is not frozenset
        or type(allow_partial_names) is not frozenset
        or not allow_partial_names.issubset(names)
    ):
        _fail("inventory byte snapshot contract changed")
    rows: list[dict[str, Any]] = []
    raw_by_name: dict[str, bytes] = {}
    for name in sorted(names):
        raw = store.read_exact(
            name, allow_empty=name in allow_partial_names
        )
        raw_by_name[name] = raw
        rows.append(
            {
                "name": name,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "partial_allowed": name in allow_partial_names,
            }
        )
    return tuple(rows), raw_by_name


def outer_deadline_budget() -> dict[str, int]:
    return {
        "formal_total_cap_seconds": FORMAL_TOTAL_CAP_SECONDS,
        "formal_prework_reserve_seconds": FORMAL_PREWORK_RESERVE_SECONDS,
        "git_call_timeout_seconds": GIT_CALL_TIMEOUT_SECONDS,
        "git_process_total_bound_seconds": GIT_PROCESS_TOTAL_BOUND_SECONDS,
        "outer_prework_git_call_count": OUTER_PREWORK_GIT_CALL_COUNT,
        "inner_total_timeout_seconds": INNER_TOTAL_TIMEOUT_SECONDS,
        "unit_runtime_max_seconds": UNIT_RUNTIME_MAX_SECONDS,
        "unit_stop_timeout_seconds": UNIT_STOP_TIMEOUT_SECONDS,
        "outer_launch_timeout_seconds": OUTER_LAUNCH_TIMEOUT_SECONDS,
        "outer_process_total_bound_seconds": OUTER_PROCESS_TOTAL_BOUND_SECONDS,
        "outer_post_absence_seconds": OUTER_POST_ABSENCE_SECONDS,
        "formal_deadline_margin_seconds": FORMAL_DEADLINE_MARGIN_SECONDS,
        "outer_required_after_attempt_publication_seconds": (
            OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS
        ),
        "outer_required_after_process_seconds": (
            OUTER_REQUIRED_AFTER_PROCESS_SECONDS
        ),
    }


def validate_outer_deadline_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    required_actual_fields = {
        "formal_process_entry_monotonic_ns",
        "formal_deadline_monotonic_ns",
        "outer_attempt_issued_monotonic_ns",
        "remaining_before_launch_ns",
    }
    optional_actual_fields = {
        "remaining_after_attempt_publication_ns",
        "remaining_after_process_ns",
        "post_absence_deadline_monotonic_ns",
        "remaining_after_post_absence_ns",
        "remaining_after_inner_observation_ns",
        "remaining_before_terminal_publication_ns",
    }
    budget = outer_deadline_budget()
    if type(value) is not dict or set(value) != (
        set(budget) | required_actual_fields | optional_actual_fields
    ):
        _fail("outer deadline contract fields changed")
    if any(value[key] != expected for key, expected in budget.items()):
        _fail("outer deadline budget changed")
    if any(type(value[key]) is not int for key in required_actual_fields):
        _fail("outer absolute deadline values are mistyped")
    if any(
        value[key] is not None and type(value[key]) is not int
        for key in optional_actual_fields
    ):
        _fail("outer optional deadline values are mistyped")
    entry = value["formal_process_entry_monotonic_ns"]
    deadline = value["formal_deadline_monotonic_ns"]
    issued = value["outer_attempt_issued_monotonic_ns"]
    remaining = value["remaining_before_launch_ns"]
    minimum = OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS * 1_000_000_000
    if (
        entry < 0
        or deadline - entry
        != FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
        or not entry <= issued < deadline
        or remaining <= minimum
        or remaining != deadline - issued
    ):
        _fail("outer absolute deadline arithmetic changed")
    ordered_remaining_fields = (
        "remaining_after_attempt_publication_ns",
        "remaining_after_process_ns",
        "remaining_after_post_absence_ns",
        "remaining_after_inner_observation_ns",
        "remaining_before_terminal_publication_ns",
    )
    previous = remaining
    for key in ordered_remaining_fields:
        observed = value[key]
        if observed is None:
            continue
        if observed > previous or observed > deadline - entry:
            _fail("outer recorded remaining time increased")
        previous = observed
    post_deadline = value["post_absence_deadline_monotonic_ns"]
    after_attempt = value["remaining_after_attempt_publication_ns"]
    after_process = value["remaining_after_process_ns"]
    after_post = value["remaining_after_post_absence_ns"]
    after_inner = value["remaining_after_inner_observation_ns"]
    if after_process is not None and after_attempt is None:
        _fail("outer process completion lacks durable ATTEMPT timing")
    if post_deadline is not None and (
        after_process is None
        or post_deadline < entry
        or post_deadline
        > deadline - FORMAL_DEADLINE_MARGIN_SECONDS * 1_000_000_000
        or post_deadline
        != min(
            deadline
            - after_process
            + OUTER_POST_ABSENCE_SECONDS * 1_000_000_000,
            deadline
            - FORMAL_DEADLINE_MARGIN_SECONDS * 1_000_000_000,
        )
    ):
        _fail("outer post-absence deadline escaped its closure reserve")
    if after_post is not None and post_deadline is None:
        _fail("outer post-absence completion lacks its local deadline")
    if after_inner is not None and after_post is None:
        _fail("outer inner observation lacks post-absence timing")
    return dict(value)


def _sample_outer_remaining(
    deadline_ns: int,
    monotonic_ns: Callable[[], int],
    label: str,
) -> tuple[int, int]:
    if type(deadline_ns) is not int or deadline_ns <= 0:
        _fail(f"{label} deadline is malformed")
    now = monotonic_ns()
    if type(now) is not int or now < 0:
        _fail(f"{label} monotonic sample is malformed")
    return now, deadline_ns - now


def build_outer_launch_attempt_document(
    authority: Mapping[str, Any], external_root_raw: bytes
) -> dict[str, Any]:
    authority = validate_external_root_document(authority)
    digest = hashlib.sha256(external_root_raw).hexdigest()
    argv = build_systemd_run_command(
        authority["systemd_invocation_contract"],
        external_root_sha256=digest,
    )
    payload = {
        "schema": OUTER_LAUNCH_ATTEMPT_SCHEMA,
        "purpose": PURPOSE,
        "ordinal": PREFLIGHT_ORDINAL,
        "preflight_token": PREFLIGHT_TOKEN,
        "service_unit_name": SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        "target_token": TARGET_TOKEN,
        "target_unit_name": TARGET_SERVICE_UNIT_NAME,
        "target_lifecycle_authority": "SYSTEMD_USER_MANAGER_ONLY",
        "external_root_id": authority["external_root_id"],
        "external_root_byte_count": len(external_root_raw),
        "external_root_sha256": digest,
        "systemd_run_argv": list(argv),
        "systemd_run_argv_sha256": hashlib.sha256(
            canonical_json_bytes(list(argv))
        ).hexdigest(),
        "deadline_budget": outer_deadline_budget(),
        "one_shot": True,
    }
    return _self_id_document(
        OUTER_LAUNCH_ATTEMPT_DOMAIN, "outer_launch_attempt_id", payload
    )


def build_attempt_document(
    authority: Mapping[str, Any], external_root_raw: bytes
) -> dict[str, Any]:
    outer_attempt = build_outer_launch_attempt_document(authority, external_root_raw)
    payload = {
        "schema": ATTEMPT_SCHEMA,
        "purpose": PURPOSE,
        "ordinal": PREFLIGHT_ORDINAL,
        "preflight_token": PREFLIGHT_TOKEN,
        "service_unit_name": SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        "target_token": TARGET_TOKEN,
        "target_unit_name": TARGET_SERVICE_UNIT_NAME,
        "target_lifecycle_authority": "SYSTEMD_USER_MANAGER_ONLY",
        "external_root_id": authority["external_root_id"],
        "external_root_byte_count": len(external_root_raw),
        "external_root_sha256": hashlib.sha256(external_root_raw).hexdigest(),
        "c_probe_commit_id": authority["c_probe_commit_id"],
        "c_probe_tree_id": authority["c_probe_tree_id"],
        "probe_source_git_blob_id": authority["probe_source_fact"]["git_blob_id"],
        "outer_launch_attempt_id": outer_attempt["outer_launch_attempt_id"],
        "one_shot": True,
    }
    return _self_id_document(ATTEMPT_DOMAIN, "probe_attempt_id", payload)


def claim_attempt(
    store: DurableArtifactStore,
    attempt: Mapping[str, Any],
    *,
    token: PublicationOwnershipToken | None = None,
) -> PublicationOwnershipToken:
    names = store.inventory_names(phase="INNER_PRECLAIM")
    if ATTEMPT_NAME in names:
        raise ReplayForbidden("preflight ATTEMPT was already claimed")
    store.require_inventory(
        _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME),
        phase="INNER_PRECLAIM_EXACT",
    )
    publication = PublicationOwnershipToken(ATTEMPT_NAME) if token is None else token
    try:
        store.write_once(
            ATTEMPT_NAME, canonical_json_bytes(attempt), token=publication
        )
    except FileExistsError as error:
        raise ReplayForbidden("preflight ATTEMPT O_EXCL lost") from error
    store.require_inventory(
        _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME),
        phase="INNER_ATTEMPT_PUBLISHED",
    )
    return publication


def validate_retained_outer_launch_attempt(
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    names = store.inventory_names(phase="INNER_OUTER_ATTEMPT_AUTHORITY")
    expected_names = _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME)
    if names != expected_names:
        consumed = {
            _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME),
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME, RECEIPT_NAME
            ),
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME, FAILURE_NAME
            ),
        }
        if names in consumed:
            raise ReplayForbidden("inner preflight identity was already consumed")
        raise ForeignArtifactError(
            f"inner authority inventory is illegal: {sorted(names)!r}"
        )
    store.require_inventory(
        names, phase="INNER_OUTER_ATTEMPT_AUTHORITY_EXACT"
    )
    validate_prepared_authority(
        authority, external_root_raw, artifact_store=store
    )
    retained = loads_canonical_json(
        store.read_exact(OUTER_LAUNCH_ATTEMPT_NAME)
    )
    expected = build_outer_launch_attempt_document(authority, external_root_raw)
    if retained != expected:
        _fail("retained outer launch ATTEMPT is not its exact issuance")
    return expected


def _bounded_error(error: BaseException) -> tuple[str, str, int | None, str | None]:
    error_type = type(error).__name__[:128]
    message = str(error).replace("\x00", "?")[:1024]
    error_number = getattr(error, "errno", None)
    if type(error_number) is not int or error_number <= 0:
        error_number = None
    error_name = None if error_number is None else errno.errorcode.get(error_number)
    return error_type, message, error_number, error_name


def _error_fact(error: BaseException | None) -> dict[str, Any]:
    if error is None:
        return {
            "error_type": None,
            "message": None,
            "errno": None,
            "errno_name": None,
        }
    error_type, message, error_number, error_name = _bounded_error(error)
    return {
        "error_type": error_type,
        "message": message,
        "errno": error_number,
        "errno_name": error_name,
    }


def _validate_error_fact(value: Any, *, required: bool) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "error_type",
        "message",
        "errno",
        "errno_name",
    }:
        _fail("error fact fields changed")
    error_number = value["errno"]
    if error_number is not None and (
        type(error_number) is not int or error_number <= 0
    ):
        _fail("error fact errno changed")
    if value["errno_name"] != (
        None if error_number is None else errno.errorcode.get(error_number)
    ):
        _fail("error fact errno name changed")
    if required:
        if (
            type(value["error_type"]) is not str
            or not value["error_type"]
            or type(value["message"]) is not str
        ):
            _fail("required error fact is untyped")
    elif any(item is not None for item in value.values()):
        if (
            type(value["error_type"]) is not str
            or not value["error_type"]
            or type(value["message"]) is not str
        ):
            _fail("optional error fact is malformed")
    return dict(value)


def _output_fact(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or len(raw) > max(
        MAX_SUBPROCESS_STDOUT_BYTES, MAX_SUBPROCESS_STDERR_BYTES
    ):
        _fail("outer subprocess output left its byte cap")
    return {
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "base64": base64.b64encode(raw).decode("ascii"),
    }


def _validate_output_fact(value: Any, *, byte_cap: int) -> bytes:
    if (
        type(value) is not dict
        or set(value) != OUTPUT_FACT_FIELDS
        or type(value["byte_count"]) is not int
        or value["byte_count"] < 0
        or value["byte_count"] > byte_cap
        or not _is_lower_hex(value["sha256"], 64)
        or type(value["base64"]) is not str
    ):
        _fail("outer output fact fields or bounds changed")
    try:
        raw = base64.b64decode(value["base64"], validate=True)
    except (ValueError, binascii.Error) as error:
        raise AuthorityError("outer output fact base64 is malformed") from error
    if (
        len(raw) != value["byte_count"]
        or hashlib.sha256(raw).hexdigest() != value["sha256"]
        or base64.b64encode(raw).decode("ascii") != value["base64"]
    ):
        _fail("outer output fact bytes changed")
    return raw


def _validate_success_absence_fact(
    value: Any, authority: Mapping[str, Any]
) -> dict[str, Any]:
    expected_argv = list(_systemctl_absence_argv())
    expected_source = str(_source_absence_path(authority))
    expected_target = str(_target_absence_path(authority))
    if (
        type(value) is not dict
        or set(value) != ABSENCE_FACT_FIELDS
        or value["unit_absent"] is not True
        or value["target_absent"] is not True
        or value["source_unit_absent"] is not True
        or value["source_path_absent"] is not True
        or value["target_unit_absent"] is not True
        or value["target_path_absent"] is not True
        or type(value["poll_count"]) is not int
        or not 1 <= value["poll_count"] <= MAX_OUTER_OBSERVATION_POLLS
        or value["systemctl_argv"] != expected_argv
        or value["source_path"] != expected_source
        or value["target_path"] != expected_target
    ):
        _fail("outer success absence evidence changed")
    return dict(value)


def _validate_self_id(
    document: Any,
    *,
    schema: str,
    identity_field: str,
    domain: str,
) -> dict[str, Any]:
    if type(document) is not dict or document.get("schema") != schema:
        _fail(f"{schema} document is mistyped")
    identity = document.get(identity_field)
    if not _is_lower_hex(identity, 64):
        _fail(f"{schema} self-ID is malformed")
    payload = dict(document)
    del payload[identity_field]
    if identity != _domain_id(domain, payload):
        _fail(f"{schema} self-ID changed")
    return dict(document)


def validate_substage_record(
    document: Any, *, expected_index: int
) -> dict[str, Any]:
    if type(document) is not dict or set(document) != SUBSTAGE_FIELDS:
        _fail("substage record fields changed")
    retained = _validate_self_id(
        document,
        schema=SUBSTAGE_SCHEMA,
        identity_field="substage_record_id",
        domain=SUBSTAGE_DOMAIN,
    )
    status_text = retained["status"]
    if (
        type(expected_index) is not int
        or retained["index"] != expected_index
        or type(retained["substage"]) is not str
        or not retained["substage"]
        or status_text not in {"OK", "FAILED"}
        or type(retained["detail"]) is not dict
    ):
        _fail("substage record values changed")
    error_number = retained["errno"]
    if error_number is not None and (
        type(error_number) is not int or error_number <= 0
    ):
        _fail("substage errno is malformed")
    expected_errno_name = (
        None if error_number is None else errno.errorcode.get(error_number)
    )
    if retained["errno_name"] != expected_errno_name:
        _fail("substage errno name changed")
    if status_text == "OK":
        if any(
            retained[field] is not None
            for field in ("errno", "errno_name", "error_type", "message")
        ):
            _fail("successful substage carries error fields")
    elif (
        type(retained["error_type"]) is not str
        or not retained["error_type"]
        or type(retained["message"]) is not str
        or retained["detail"] != {}
    ):
        _fail("failed substage lacks typed error fields or carries detail")
    return retained


def validate_attempt_document(
    document: Any,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    if type(document) is not dict or set(document) != ATTEMPT_FIELDS:
        _fail("inner ATTEMPT fields changed")
    retained = _validate_self_id(
        document,
        schema=ATTEMPT_SCHEMA,
        identity_field="probe_attempt_id",
        domain=ATTEMPT_DOMAIN,
    )
    expected = build_attempt_document(authority, external_root_raw)
    if retained != expected:
        _fail("inner ATTEMPT/root/outer joins changed")
    return retained


def _require_exact_detail(
    value: Any, fields: frozenset[str], *, label: str
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        _fail(f"{label} detail fields changed")
    return dict(value)


def _validate_write_permission_detail(
    value: Any,
    *,
    label: str,
    required_open: bool | None = None,
    expected: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    retained = _require_exact_detail(value, WRITE_PERMISSION_FIELDS, label=label)
    opened = retained["opened_for_write"]
    if type(opened) is not bool or (
        required_open is not None and opened is not required_open
    ):
        _fail(f"{label} write-open result changed")
    if opened:
        if (
            retained["errno"] is not None
            or retained["errno_name"] is not None
            or any(
                type(retained[field]) is not int or retained[field] < 0
                for field in (
                    "device",
                    "inode",
                    "mode",
                    "owner_uid",
                    "owner_gid",
                )
            )
        ):
            _fail(f"{label} successful write evidence changed")
        if expected is not None and any(
            retained[field] != expected[field] for field in expected
        ):
            _fail(f"{label} write evidence lost its authority join")
    else:
        error_number = retained["errno"]
        if (
            type(error_number) is not int
            or error_number <= 0
            or retained["errno_name"] != errno.errorcode.get(error_number)
            or any(
                retained[field] is not None
                for field in ("device", "inode", "mode", "owner_uid", "owner_gid")
            )
        ):
            _fail(f"{label} failed write evidence changed")
    return retained


def _validate_full_target_removal_detail(
    value: Any,
    *,
    target_contract: Mapping[str, Any],
    expected_device: int | None,
    expected_inode: int | None,
) -> dict[str, Any]:
    retained = _require_exact_detail(
        value, TARGET_REMOVAL_DETAIL_FIELDS, label="target manager removal"
    )
    if (
        retained["removed"] is not True
        or retained["already_absent"] is not False
        or type(retained["owned_device"]) is not int
        or retained["owned_device"] < 0
        or type(retained["owned_inode"]) is not int
        or retained["owned_inode"] < 0
        or (
            expected_device is not None
            and retained["owned_device"] != expected_device
        )
        or (
            expected_inode is not None
            and retained["owned_inode"] != expected_inode
        )
        or retained["manager_stop_argv"] != target_contract["stop_argv"]
        or retained["manager_stop_environment"] != target_contract["environment"]
        or type(retained["manager_stop_returncode"]) is not int
        or retained["manager_stop_returncode"] != 0
        or _validate_output_fact(
            retained["manager_stop_stdout"],
            byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
        )
        != b""
        or _validate_output_fact(
            retained["manager_stop_stderr"],
            byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
        )
        != b""
        or type(retained["manager_final_properties"]) is not dict
        or not _target_manager_not_found(retained["manager_final_properties"])
        or type(retained["manager_poll_count"]) is not int
        or not 1 <= retained["manager_poll_count"] <= TARGET_MANAGER_MAX_POLLS
        or type(retained["probe_path_deletion_calls"]) is not int
        or retained["probe_path_deletion_calls"] != 0
        or retained["manager_absence_proven"] is not True
        or retained["claimed_inode_unlinked"] is not True
    ):
        _fail("target manager removal evidence changed")
    return retained


def _validate_success_substage_prefix(
    records: Sequence[Mapping[str, Any]],
    *,
    attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Validate every successful detail in one exact success-order prefix."""

    if len(records) > len(SUCCESS_SUBSTAGE_ORDER):
        _fail("success substage prefix is too long")
    if tuple(row["substage"] for row in records) != SUCCESS_SUBSTAGE_ORDER[
        : len(records)
    ] or any(row["status"] != "OK" for row in records):
        _fail("success substage prefix changed")
    host = validate_host_parent_fact(authority["host_parent_fact"])
    invocation = validate_systemd_invocation_contract(
        authority["systemd_invocation_contract"]
    )
    target_contract = invocation["target_lifecycle_contract"]
    uid = host["owner_uid"]
    gid = host["owner_gid"]
    app_membership = (
        f"/user.slice/user-{uid}.slice/user@{uid}.service/app.slice"
    )
    source_membership = f"{app_membership}/{SERVICE_UNIT_NAME}"
    target_membership = f"{app_membership}/{TARGET_CGROUP_NAME}"
    target_path = f"{host['app_slice_path']}/{TARGET_CGROUP_NAME}"
    details = {row["substage"]: dict(row["detail"]) for row in records}

    if "ATTEMPT_PUBLICATION" in details:
        detail = _require_exact_detail(
            details["ATTEMPT_PUBLICATION"],
            frozenset(
                {
                    "probe_attempt_id",
                    "o_excl_owned",
                    "canonical_durable_readback",
                }
            ),
            label="ATTEMPT_PUBLICATION",
        )
        if (
            detail["probe_attempt_id"] != attempt["probe_attempt_id"]
            or detail["o_excl_owned"] is not True
            or detail["canonical_durable_readback"] is not True
        ):
            _fail("ATTEMPT_PUBLICATION detail lost its ATTEMPT join")

    if "OUTER_CONTEXT" in details:
        context = _require_exact_detail(
            details["OUTER_CONTEXT"],
            frozenset(
                {
                    "external_root_id",
                    "external_root_sha256",
                    "service_type",
                    "delegate",
                    "scope",
                    "clean_environment",
                    "probe_process_entry_monotonic_ns",
                    "probe_started_monotonic_ns",
                    "probe_deadline_monotonic_ns",
                    "inner_total_timeout_ns",
                    "inner_git_call_count",
                    "git_process_total_bound_seconds",
                    "target_token",
                    "target_unit_name",
                    "target_lifecycle_authority",
                    "target_manager_call_timeout_seconds",
                    "target_manager_process_total_bound_seconds",
                    "target_manager_max_polls",
                    "toolchain_revalidated",
                    "umask",
                }
            ),
            label="OUTER_CONTEXT",
        )
        integer_fields = (
            "probe_process_entry_monotonic_ns",
            "probe_started_monotonic_ns",
            "probe_deadline_monotonic_ns",
            "inner_total_timeout_ns",
            "inner_git_call_count",
            "git_process_total_bound_seconds",
            "target_manager_call_timeout_seconds",
            "target_manager_process_total_bound_seconds",
            "target_manager_max_polls",
            "umask",
        )
        if (
            any(type(context[field]) is not int for field in integer_fields)
            or context["external_root_id"] != attempt["external_root_id"]
            or context["external_root_sha256"] != attempt["external_root_sha256"]
            or context["service_type"] != invocation["service_type"]
            or context["delegate"] is not invocation["delegate"]
            or context["scope"] is not invocation["scope"]
            or context["clean_environment"] is not True
            or context["probe_process_entry_monotonic_ns"]
            > context["probe_started_monotonic_ns"]
            or context["probe_started_monotonic_ns"]
            >= context["probe_deadline_monotonic_ns"]
            or context["probe_deadline_monotonic_ns"]
            - context["probe_process_entry_monotonic_ns"]
            != INNER_TOTAL_TIMEOUT_NS
            or context["inner_total_timeout_ns"] != INNER_TOTAL_TIMEOUT_NS
            or context["inner_git_call_count"] != INNER_GIT_CALL_COUNT
            or context["git_process_total_bound_seconds"]
            != GIT_PROCESS_TOTAL_BOUND_SECONDS
            or context["target_token"] != attempt["target_token"]
            or context["target_unit_name"] != attempt["target_unit_name"]
            or context["target_lifecycle_authority"]
            != attempt["target_lifecycle_authority"]
            or context["target_manager_call_timeout_seconds"]
            != TARGET_MANAGER_CALL_TIMEOUT_SECONDS
            or context["target_manager_process_total_bound_seconds"]
            != TARGET_MANAGER_PROCESS_TOTAL_BOUND_SECONDS
            or context["target_manager_max_polls"] != TARGET_MANAGER_MAX_POLLS
            or context["toolchain_revalidated"] is not True
            or context["umask"] != REQUIRED_UMASK
        ):
            _fail("OUTER_CONTEXT deadline or authority evidence changed")

    if "SERVICE_PLACEMENT_AND_NCA_PERMISSION" in details:
        service = _require_exact_detail(
            details["SERVICE_PLACEMENT_AND_NCA_PERMISSION"],
            SERVICE_DETAIL_FIELDS,
            label="SERVICE_PLACEMENT_AND_NCA_PERMISSION",
        )
        integer_fields = (
            "pid",
            "uid",
            "gid",
            "service_device",
            "service_inode",
            "service_owner_uid",
            "service_owner_gid",
            "service_mode",
        )
        if (
            any(type(service[field]) is not int or service[field] < 0 for field in integer_fields)
            or service["pid"] <= 0
            or service["uid"] != uid
            or service["gid"] != gid
            or service["membership_line"] != f"0::{source_membership}"
            or service["app_slice_membership"] != app_membership
            or service["source_membership"] != source_membership
            or service["target_membership"] != target_membership
            or service["nearest_common_ancestor"] != app_membership
            or service["service_path"]
            != f"{host['app_slice_path']}/{SERVICE_UNIT_NAME}"
            or service["service_device"] != host["app_slice_device"]
            or service["service_inode"] <= 0
            or service["service_owner_uid"] != uid
            or service["service_owner_gid"] != gid
            or service["service_mode"] != host["mode"]
            or service["service_procs"] != [service["pid"]]
            or service["app_slice_cgroup_procs_write_required"] is not True
            or service["service_type_from_outer_context"]
            != invocation["service_type"]
            or service["delegate_from_outer_context"] is not True
            or service["fixed_target_absent_before_create"] is not True
            or service["target_manager_absent_before_create"] is not True
            or type(service["target_manager_precreate_properties"]) is not dict
            or not _target_manager_not_found(
                service["target_manager_precreate_properties"]
            )
            or service["target_lifecycle_contract"] != target_contract
            or service["target_lifecycle_unique_authority"]
            != "SYSTEMD_USER_MANAGER_ONLY"
        ):
            _fail("SERVICE placement detail lost its authority join")
        nca_expected = {
            "device": host["cgroup_procs_device"],
            "inode": host["cgroup_procs_inode"],
            "mode": host["cgroup_procs_mode"],
            "owner_uid": host["cgroup_procs_owner_uid"],
            "owner_gid": host["cgroup_procs_owner_gid"],
        }
        nca_permission = _validate_write_permission_detail(
            service["nca_cgroup_procs_write"],
            label="NCA cgroup.procs",
            required_open=True,
            expected=nca_expected,
        )
        if service["app_slice_cgroup_procs_write"] != nca_permission:
            _fail("app.slice and NCA write evidence diverged")
        _validate_write_permission_detail(
            service["service_cgroup_procs_write"],
            label="service cgroup.procs",
            expected={
                "device": service["service_device"],
                "mode": host["cgroup_procs_mode"],
                "owner_uid": uid,
                "owner_gid": gid,
            },
        )

    if "TARGET_CREATE" in details:
        target = _require_exact_detail(
            details["TARGET_CREATE"],
            TARGET_CREATE_DETAIL_FIELDS,
            label="TARGET_CREATE",
        )
        if (
            target["target_name"] != TARGET_CGROUP_NAME
            or target["target_unit_name"] != attempt["target_unit_name"]
            or target["target_token"] != attempt["target_token"]
            or target["target_path"] != target_path
            or target["target_membership"] != target_membership
            or type(target["target_device"]) is not int
            or target["target_device"] < 0
            or target["target_device"] != host["app_slice_device"]
            or type(target["target_inode"]) is not int
            or target["target_inode"] <= 0
            or target["target_cgroup_type"] != "domain"
            or target["initial_cgroup_procs"] != []
            or target["manager_create_argv"] != target_contract["create_argv"]
            or target["manager_create_environment"] != target_contract["environment"]
            or type(target["manager_create_returncode"]) is not int
            or target["manager_create_returncode"] != 0
            or _validate_output_fact(
                target["manager_create_stdout"],
                byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
            )
            != b""
            or _validate_output_fact(
                target["manager_create_stderr"],
                byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
            )
            != b""
            or type(target["manager_properties"]) is not dict
            or not _target_manager_active(
                target["manager_properties"],
                expected_control_group=target_membership,
            )
            or type(target["manager_poll_count"]) is not int
            or not 1 <= target["manager_poll_count"] <= TARGET_MANAGER_MAX_POLLS
            or target["manager_owned_lifecycle"] is not True
            or type(target["probe_path_deletion_calls"]) is not int
            or target["probe_path_deletion_calls"] != 0
        ):
            _fail("TARGET_CREATE detail lost its target/manager join")
        _validate_write_permission_detail(
            target["target_cgroup_procs_write"],
            label="target cgroup.procs",
            required_open=True,
            expected={
                "device": target["target_device"],
                "mode": host["cgroup_procs_mode"],
                "owner_uid": uid,
                "owner_gid": gid,
            },
        )

    if "CLONE3_ATOMIC_BIRTH" in details:
        clone = _require_exact_detail(
            details["CLONE3_ATOMIC_BIRTH"],
            frozenset({"pid", "pidfd", "clone3_flags", "target_cgroup_fd"}),
            label="CLONE3_ATOMIC_BIRTH",
        )
        if (
            type(clone["pid"]) is not int
            or clone["pid"] <= 0
            or type(clone["pidfd"]) is not int
            or clone["pidfd"] < 0
            or clone["clone3_flags"] != ["CLONE_INTO_CGROUP", "CLONE_PIDFD"]
            or type(clone["target_cgroup_fd"]) is not int
            or clone["target_cgroup_fd"] < 0
        ):
            _fail("CLONE3_ATOMIC_BIRTH detail changed")

    if "CHILD_HANDSHAKE" in details:
        handshake = _require_exact_detail(
            details["CHILD_HANDSHAKE"],
            frozenset(
                {
                    "handshake_id",
                    "pid",
                    "ppid",
                    "membership_line",
                    "canonical_byte_count",
                    "canonical_sha256",
                }
            ),
            label="CHILD_HANDSHAKE",
        )
        clone = details["CLONE3_ATOMIC_BIRTH"]
        service = details["SERVICE_PLACEMENT_AND_NCA_PERMISSION"]
        handshake_payload = {
            "schema": HANDSHAKE_SCHEMA,
            "preflight_token": PREFLIGHT_TOKEN,
            "pid": handshake["pid"],
            "ppid": handshake["ppid"],
            "membership_line": handshake["membership_line"],
        }
        expected_id = _domain_id(HANDSHAKE_DOMAIN, handshake_payload)
        handshake_document = {**handshake_payload, "handshake_id": expected_id}
        handshake_raw = canonical_json_bytes(handshake_document)
        if (
            handshake["pid"] != clone["pid"]
            or handshake["ppid"] != service["pid"]
            or type(handshake["membership_line"]) is not str
            or not handshake["membership_line"].startswith("0::/")
            or handshake["handshake_id"] != expected_id
            or handshake["canonical_byte_count"] != len(handshake_raw)
            or handshake["canonical_sha256"]
            != hashlib.sha256(handshake_raw).hexdigest()
        ):
            _fail("CHILD_HANDSHAKE canonical identity or joins changed")

    if "PIDFD_AND_MEMBERSHIP" in details:
        child = _require_exact_detail(
            details["PIDFD_AND_MEMBERSHIP"],
            frozenset(
                {
                    "pid",
                    "pidfd",
                    "pidfd_device",
                    "pidfd_inode",
                    "fdinfo_pid",
                    "fdinfo_nspid",
                    "proc_starttime_ticks",
                    "membership_line",
                    "target_device",
                    "target_inode",
                    "pidfd_cloexec",
                }
            ),
            label="PIDFD_AND_MEMBERSHIP",
        )
        clone = details["CLONE3_ATOMIC_BIRTH"]
        target = details["TARGET_CREATE"]
        if (
            child["pid"] != clone["pid"]
            or child["pidfd"] != clone["pidfd"]
            or type(child["pidfd_device"]) is not int
            or child["pidfd_device"] < 0
            or type(child["pidfd_inode"]) is not int
            or child["pidfd_inode"] < 0
            or child["fdinfo_pid"] != clone["pid"]
            or type(child["fdinfo_nspid"]) is not list
            or not child["fdinfo_nspid"]
            or any(type(item) is not int or item <= 0 for item in child["fdinfo_nspid"])
            or child["fdinfo_nspid"][0] != clone["pid"]
            or type(child["proc_starttime_ticks"]) is not int
            or child["proc_starttime_ticks"] <= 0
            or child["membership_line"] != f"0::{target_membership}"
            or child["target_device"] != target["target_device"]
            or child["target_inode"] != target["target_inode"]
            or child["pidfd_cloexec"] is not True
        ):
            _fail("PIDFD_AND_MEMBERSHIP detail lost its child/target join")

    if "HANDSHAKE_MEMBERSHIP_CONSISTENCY" in details:
        consistency = _require_exact_detail(
            details["HANDSHAKE_MEMBERSHIP_CONSISTENCY"],
            frozenset({"membership_line", "independent_observations_agree"}),
            label="HANDSHAKE_MEMBERSHIP_CONSISTENCY",
        )
        if (
            consistency["membership_line"]
            != details["CHILD_HANDSHAKE"]["membership_line"]
            or consistency["membership_line"]
            != details["PIDFD_AND_MEMBERSHIP"]["membership_line"]
            or consistency["independent_observations_agree"] is not True
        ):
            _fail("handshake/PIDFD membership consistency changed")

    if "CHILD_RELEASE" in details:
        release = _require_exact_detail(
            details["CHILD_RELEASE"],
            frozenset({"ack_hex", "released"}),
            label="CHILD_RELEASE",
        )
        if release != {"ack_hex": "06", "released": True}:
            _fail("CHILD_RELEASE detail changed")

    if "CHILD_EXIT_ZERO" in details:
        exited = _require_exact_detail(
            details["CHILD_EXIT_ZERO"],
            frozenset({"pid", "si_code", "si_status", "exit_zero"}),
            label="CHILD_EXIT_ZERO",
        )
        if (
            exited["pid"] != details["CLONE3_ATOMIC_BIRTH"]["pid"]
            or exited["si_code"] != os.CLD_EXITED
            or exited["si_status"] != 0
            or exited["exit_zero"] is not True
        ):
            _fail("CHILD_EXIT_ZERO detail changed")

    if "CHILD_HANDLE_CLOSE" in details:
        if _require_exact_detail(
            details["CHILD_HANDLE_CLOSE"],
            frozenset({"child_handle_closed"}),
            label="CHILD_HANDLE_CLOSE",
        ) != {"child_handle_closed": True}:
            _fail("CHILD_HANDLE_CLOSE detail changed")

    if "TARGET_EMPTY" in details:
        if _require_exact_detail(
            details["TARGET_EMPTY"],
            frozenset({"cgroup_procs", "populated"}),
            label="TARGET_EMPTY",
        ) != {"cgroup_procs": [], "populated": 0}:
            _fail("TARGET_EMPTY detail changed")

    if "TARGET_REMOVE" in details:
        target = details["TARGET_CREATE"]
        _validate_full_target_removal_detail(
            details["TARGET_REMOVE"],
            target_contract=target_contract,
            expected_device=target["target_device"],
            expected_inode=target["target_inode"],
        )

    if "TARGET_ABSENT" in details:
        _validated_target_absence_detail(details["TARGET_ABSENT"])

    if "SERVICE_HANDLE_CLOSE" in details:
        if _require_exact_detail(
            details["SERVICE_HANDLE_CLOSE"],
            frozenset({"service_handles_closed"}),
            label="SERVICE_HANDLE_CLOSE",
        ) != {"service_handles_closed": True}:
            _fail("SERVICE_HANDLE_CLOSE detail changed")
    return details


def _target_postclaim_validation_marker(
    primary: Mapping[str, Any],
) -> tuple[int, int] | None:
    variants = {
        "TargetPostClaimValidationError": (
            errno.EPROTO,
            f"[Errno {errno.EPROTO}] TARGET_CREATE post-claim detail "
            "validation rejected continuous target device=",
        ),
        "TargetPostClaimDeadlineError": (
            errno.ETIMEDOUT,
            f"[Errno {errno.ETIMEDOUT}] TARGET_CREATE post-operation "
            "deadline crossed continuous target device=",
        ),
    }
    variant = variants.get(primary.get("error_type"))
    if variant is None:
        return None
    error_number, prefix = variant
    if (
        primary.get("substage") != "TARGET_CREATE"
        or primary.get("errno") != error_number
        or primary.get("errno_name") != errno.errorcode[error_number]
        or type(primary.get("message")) is not str
        or not primary["message"].startswith(prefix)
    ):
        return None
    values = primary["message"][len(prefix) :].split(" inode=", 1)
    if len(values) != 2 or any(not value.isdigit() for value in values):
        return None
    device, inode = (int(value) for value in values)
    if device < 0 or inode <= 0 or primary["message"] != (
        f"{prefix}{device} inode={inode}"
    ):
        return None
    return device, inode


def _clone_postacquire_validation_marker(
    primary: Mapping[str, Any],
) -> tuple[int, int] | None:
    variants = {
        "ClonePostAcquireValidationError": (
            errno.EPROTO,
            f"[Errno {errno.EPROTO}] CLONE3 post-acquire detail "
            "validation rejected child pid=",
        ),
        "ClonePostAcquireDeadlineError": (
            errno.ETIMEDOUT,
            f"[Errno {errno.ETIMEDOUT}] CLONE3 post-operation deadline "
            "crossed child pid=",
        ),
    }
    variant = variants.get(primary.get("error_type"))
    if variant is None:
        return None
    error_number, prefix = variant
    if (
        primary.get("substage") != "CLONE3_ATOMIC_BIRTH"
        or primary.get("errno") != error_number
        or primary.get("errno_name") != errno.errorcode[error_number]
        or type(primary.get("message")) is not str
        or not primary["message"].startswith(prefix)
    ):
        return None
    values = primary["message"][len(prefix) :].split(" pidfd=", 1)
    if len(values) != 2 or any(not value.isdigit() for value in values):
        return None
    pid, pidfd = (int(value) for value in values)
    if pid <= 0 or pidfd < 0 or primary["message"] != (
        f"{prefix}{pid} pidfd={pidfd}"
    ):
        return None
    return pid, pidfd


def _validate_cleanup_detail(
    row: Mapping[str, Any],
    *,
    details: Mapping[str, Mapping[str, Any]],
    primary: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> bool:
    """Validate one OK cleanup detail; return true only for full target removal."""

    if row["status"] == "FAILED":
        return False
    name = row["substage"]
    detail = row["detail"]
    target_contract = authority["systemd_invocation_contract"][
        "target_lifecycle_contract"
    ]
    clone = details.get("CLONE3_ATOMIC_BIRTH")
    target = details.get("TARGET_CREATE")
    target_marker = _target_postclaim_validation_marker(primary)
    clone_marker = _clone_postacquire_validation_marker(primary)
    if name == "CLEANUP_PIDFD_KILL":
        if type(detail) is not dict or detail not in (
            {"signal": "NONE", "already_reaped": True},
            {"signal": "SIGKILL", "pidfd_send_signal_errno": None},
            {
                "signal": "SIGKILL",
                "pidfd_send_signal_errno": errno.ESRCH,
            },
        ):
            _fail("CLEANUP_PIDFD_KILL detail changed")
    elif name == "CLEANUP_CHILD_REAP":
        partial_clone_child = clone is None and clone_marker is not None
        if type(detail) is not dict or (
            clone is None and not partial_clone_child
        ):
            _fail("CLEANUP_CHILD_REAP lacks its clone join")
        if detail.get("already_reaped") is True:
            if set(detail) != {"already_reaped", "pid"}:
                _fail("already-reaped cleanup detail changed")
        elif detail.get("already_reaped") is False:
            if (
                set(detail)
                != {"already_reaped", "pid", "si_code", "si_status"}
                or type(detail["si_code"]) is not int
                or type(detail["si_status"]) is not int
            ):
                _fail("cleanup reap observation changed")
        else:
            _fail("cleanup reap state changed")
        if (
            type(detail["pid"]) is not int
            or detail["pid"] <= 0
            or (
                clone is not None and detail["pid"] != clone["pid"]
            )
            or (
                clone is None
                and clone_marker is not None
                and detail["pid"] != clone_marker[0]
            )
        ):
            _fail("cleanup reap reidentified the child")
    elif name == "CLEANUP_CHILD_CLOSE":
        if detail != {"child_handle_closed": True}:
            _fail("CLEANUP_CHILD_CLOSE detail changed")
    elif name == "CLEANUP_TARGET_REMOVE":
        if type(detail) is dict and set(detail) == TARGET_REMOVAL_DETAIL_FIELDS:
            partial_create_claim = target is None and target_marker is not None
            if target is None and not partial_create_claim:
                _fail(
                    "full cleanup removal lacks a successful TARGET_CREATE claim"
                )
            _validate_full_target_removal_detail(
                detail,
                target_contract=target_contract,
                expected_device=(
                    target_marker[0]
                    if partial_create_claim
                    else target["target_device"]
                ),
                expected_inode=(
                    target_marker[1]
                    if partial_create_claim
                    else target["target_inode"]
                ),
            )
            return True
        no_op = _require_exact_detail(
            detail,
            frozenset(
                {"manager_stop_attempted", "reason", "probe_path_deletion_calls"}
            ),
            label="CLEANUP_TARGET_REMOVE no-op",
        )
        if (
            no_op["manager_stop_attempted"] is not False
            or no_op["reason"]
            not in {
                "MANAGER_ABSENCE_ALREADY_PROVEN",
                "NO_CONTINUOUS_MANAGER_OWNERSHIP_CLAIM",
            }
            or type(no_op["probe_path_deletion_calls"]) is not int
            or no_op["probe_path_deletion_calls"] != 0
        ):
            _fail("CLEANUP_TARGET_REMOVE no-op evidence changed")
        if (
            no_op["reason"] == "MANAGER_ABSENCE_ALREADY_PROVEN"
            and "TARGET_ABSENT" not in details
            and not (
                "SERVICE_PLACEMENT_AND_NCA_PERMISSION" in details
                and primary["substage"] == "TARGET_CREATE"
                and primary["error_type"] == "TimeoutError"
                and primary["errno"] == errno.ETIMEDOUT
                and primary["message"]
                == (
                    f"[Errno {errno.ETIMEDOUT}] TARGET_CREATE exhausted "
                    "the inner process absolute deadline"
                )
            )
        ):
            _fail("cleanup no-op claims unproven prior manager absence")
        if (
            no_op["reason"] == "NO_CONTINUOUS_MANAGER_OWNERSHIP_CLAIM"
            and "TARGET_CREATE" in details
            and primary["substage"] != "TARGET_REMOVE"
        ):
            _fail("cleanup no-op discarded a successful target claim")
    elif name == "CLEANUP_TARGET_ABSENT":
        _validated_target_absence_detail(detail)
    elif name == "CLEANUP_SERVICE_CLOSE":
        if detail != {"service_handles_closed": True}:
            _fail("CLEANUP_SERVICE_CLOSE detail changed")
    elif name == "CLEANUP_SERVICE_ALREADY_CLOSED":
        expected_absence = "TARGET_ABSENT" in details
        if detail != {
            "target_absence_preserved": expected_absence,
            "manager_absence_preserved": expected_absence,
            "probe_path_deletion_calls": 0,
        }:
            _fail("CLEANUP_SERVICE_ALREADY_CLOSED detail changed")
    else:
        _fail("unknown cleanup substage")
    return False


def _validate_failure_records(
    records: Sequence[Mapping[str, Any]],
    *,
    attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> tuple[Mapping[str, Any], dict[str, bool]]:
    if not records:
        _fail("inner FAILURE has no substage records")
    prefix_length = 0
    while (
        prefix_length < len(records)
        and prefix_length < len(SUCCESS_SUBSTAGE_ORDER)
        and records[prefix_length]["status"] == "OK"
        and records[prefix_length]["substage"]
        == SUCCESS_SUBSTAGE_ORDER[prefix_length]
    ):
        prefix_length += 1
    if prefix_length >= len(records):
        _fail("inner FAILURE lacks one primary failed record")
    primary = records[prefix_length]
    expected_primary = (
        SUCCESS_SUBSTAGE_ORDER[prefix_length]
        if prefix_length < len(SUCCESS_SUBSTAGE_ORDER)
        else None
    )
    if (
        primary["status"] != "FAILED"
        or (
            primary["substage"] != expected_primary
            and not (
                prefix_length == len(SUCCESS_SUBSTAGE_ORDER)
                and primary["substage"] in FAILURE_PRIMARY_AFTER_SUCCESS
            )
        )
    ):
        _fail("inner FAILURE primary sequence changed")
    prefix = records[:prefix_length]
    details = _validate_success_substage_prefix(
        prefix, attempt=attempt, authority=authority
    )
    cleanup = records[prefix_length + 1 :]
    cleanup_names = tuple(row["substage"] for row in cleanup)
    clone_marker = _clone_postacquire_validation_marker(primary)
    partial_clone_child = clone_marker is not None
    child_acquired = (
        "CLONE3_ATOMIC_BIRTH" in details or partial_clone_child
    )
    service_acquired = "SERVICE_PLACEMENT_AND_NCA_PERMISSION" in details
    service_closed = "SERVICE_HANDLE_CLOSE" in details
    expected_cleanup: list[str] = []
    if child_acquired:
        expected_cleanup.extend(
            (
                "CLEANUP_PIDFD_KILL",
                "CLEANUP_CHILD_REAP",
                "CLEANUP_CHILD_CLOSE",
            )
        )
    if service_closed:
        expected_cleanup.append("CLEANUP_SERVICE_ALREADY_CLOSED")
    elif service_acquired:
        ordinary_service_cleanup = (
            "CLEANUP_TARGET_REMOVE",
            "CLEANUP_TARGET_ABSENT",
            "CLEANUP_SERVICE_CLOSE",
        )
        if (
            primary["substage"] == "SERVICE_HANDLE_CLOSE"
            and cleanup_names
            == tuple((*expected_cleanup, "CLEANUP_SERVICE_ALREADY_CLOSED"))
        ):
            expected_cleanup.append("CLEANUP_SERVICE_ALREADY_CLOSED")
        else:
            expected_cleanup.extend(ordinary_service_cleanup)
    elif primary["substage"] == "SERVICE_PLACEMENT_AND_NCA_PERMISSION":
        legal = {
            (),
            (
                "CLEANUP_TARGET_REMOVE",
                "CLEANUP_TARGET_ABSENT",
                "CLEANUP_SERVICE_CLOSE",
            ),
        }
        if cleanup_names not in legal:
            _fail("SERVICE failure cleanup sequence changed")
        expected_cleanup = list(cleanup_names)
    if cleanup_names != tuple(expected_cleanup):
        _fail("inner FAILURE cleanup sequence changed")

    cleanup_by_name: dict[str, Mapping[str, Any]] = {}
    full_cleanup_removal = False
    for row in cleanup:
        if row["substage"] in cleanup_by_name:
            _fail("inner FAILURE repeats a cleanup substage")
        cleanup_by_name[row["substage"]] = row
        full_cleanup_removal = (
            _validate_cleanup_detail(
                row,
                details=details,
                primary=primary,
                authority=authority,
            )
            or full_cleanup_removal
        )

    primary_before_clone = (
        expected_primary is not None
        and SUCCESS_SUBSTAGE_ORDER.index(expected_primary)
        < SUCCESS_SUBSTAGE_ORDER.index("CLONE3_ATOMIC_BIRTH")
    )
    no_child = primary_before_clone
    normal_reap = "CHILD_EXIT_ZERO" in details
    cleanup_reap = (
        cleanup_by_name.get("CLEANUP_CHILD_REAP", {}).get("status") == "OK"
    )
    validated_clone = "CLONE3_ATOMIC_BIRTH" in details
    child_reaped = no_child or normal_reap or (
        validated_clone and cleanup_reap
    )

    normal_removal = "TARGET_REMOVE" in details
    cleanup_remove_ok = (
        cleanup_by_name.get("CLEANUP_TARGET_REMOVE", {}).get("status") == "OK"
    )
    cleanup_absence_ok = (
        cleanup_by_name.get("CLEANUP_TARGET_ABSENT", {}).get("status") == "OK"
    )
    validated_target = "TARGET_CREATE" in details
    precreate_deadline_absence = (
        "SERVICE_PLACEMENT_AND_NCA_PERMISSION" in details
        and primary["substage"] == "TARGET_CREATE"
        and primary["error_type"] == "TimeoutError"
        and primary["errno"] == errno.ETIMEDOUT
        and primary["message"]
        == (
            f"[Errno {errno.ETIMEDOUT}] TARGET_CREATE exhausted "
            "the inner process absolute deadline"
        )
    )
    target_absent = "TARGET_ABSENT" in details or (
        cleanup_remove_ok
        and cleanup_absence_ok
        and (validated_target or precreate_deadline_absence)
    )
    full_removal = normal_removal or (
        validated_target and full_cleanup_removal
    )
    return primary, {
        "child_reaped": child_reaped,
        "target_absent": target_absent,
        "target_identity_continuous": full_removal,
        "target_manager_stop_requested": full_removal,
        "target_manager_absence_proven": target_absent,
    }


def validate_receipt_document(
    document: Any,
    attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    authority = validate_external_root_document(authority)
    attempt = validate_attempt_document(
        attempt, authority, canonical_json_bytes(authority)
    )
    if type(document) is not dict or set(document) != RECEIPT_FIELDS:
        _fail("inner RECEIPT fields changed")
    retained = _validate_self_id(
        document,
        schema=RECEIPT_SCHEMA,
        identity_field="preflight_receipt_id",
        domain=RECEIPT_DOMAIN,
    )
    true_fields = (
        "source_is_exact_service_root",
        "nearest_common_ancestor_is_app_slice",
        "app_slice_cgroup_procs_write_required",
        "child_handshake_complete",
        "pidfd_identity_complete",
        "child_membership_exact",
        "child_exit_zero",
        "bounded_cleanup_complete",
        "target_absent",
    )
    if (
        retained["probe_attempt_id"] != attempt.get("probe_attempt_id")
        or retained["preflight_token"] != PREFLIGHT_TOKEN
        or retained["ordinal"] != PREFLIGHT_ORDINAL
        or retained["service_unit_name"] != SERVICE_UNIT_NAME
        or retained["target_cgroup_name"] != TARGET_CGROUP_NAME
        or retained["target_token"] != TARGET_TOKEN
        or retained["target_unit_name"] != TARGET_SERVICE_UNIT_NAME
        or retained["target_lifecycle_authority"]
        != "SYSTEMD_USER_MANAGER_ONLY"
        or retained["clone3_flags"]
        != ["CLONE_INTO_CGROUP", "CLONE_PIDFD"]
        or retained["target_manager_owned"] is not True
        or retained["target_manager_stop_complete"] is not True
        or retained["target_unit_absent"] is not True
        or retained["target_claimed_inode_unlinked"] is not True
        or type(retained["probe_path_deletion_calls"]) is not int
        or retained["probe_path_deletion_calls"] != 0
        or any(retained[field] is not True for field in true_fields)
        or type(retained["substage_records"]) is not list
        or len(retained["substage_records"]) != len(SUCCESS_SUBSTAGE_ORDER)
    ):
        _fail("inner RECEIPT joins or success flags changed")
    records = [
        validate_substage_record(row, expected_index=index)
        for index, row in enumerate(retained["substage_records"])
    ]
    if (
        tuple(row["substage"] for row in records) != SUCCESS_SUBSTAGE_ORDER
        or any(row["status"] != "OK" for row in records)
    ):
        _fail("inner RECEIPT success substage sequence changed")
    _validate_success_substage_prefix(
        records, attempt=attempt, authority=authority
    )
    return retained


def validate_failure_document(
    document: Any,
    attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    authority = validate_external_root_document(authority)
    attempt = validate_attempt_document(
        attempt, authority, canonical_json_bytes(authority)
    )
    if type(document) is not dict or set(document) != FAILURE_FIELDS:
        _fail("inner FAILURE fields changed")
    retained = _validate_self_id(
        document,
        schema=FAILURE_SCHEMA,
        identity_field="preflight_failure_id",
        domain=FAILURE_DOMAIN,
    )
    error_number = retained["errno"]
    if error_number is not None and (
        type(error_number) is not int or error_number <= 0
    ):
        _fail("inner FAILURE errno is malformed")
    if (
        retained["probe_attempt_id"] != attempt.get("probe_attempt_id")
        or retained["preflight_token"] != PREFLIGHT_TOKEN
        or retained["ordinal"] != PREFLIGHT_ORDINAL
        or retained["service_unit_name"] != SERVICE_UNIT_NAME
        or retained["target_cgroup_name"] != TARGET_CGROUP_NAME
        or retained["target_token"] != TARGET_TOKEN
        or retained["target_unit_name"] != TARGET_SERVICE_UNIT_NAME
        or retained["target_lifecycle_authority"]
        != "SYSTEMD_USER_MANAGER_ONLY"
        or retained["errno_name"]
        != (None if error_number is None else errno.errorcode.get(error_number))
        or type(retained["error_type"]) is not str
        or not retained["error_type"]
        or type(retained["message"]) is not str
        or type(retained["child_reaped"]) is not bool
        or type(retained["process_may_remain"]) is not bool
        or retained["process_may_remain"] != (not retained["child_reaped"])
        or type(retained["target_absent"]) is not bool
        or type(retained["target_may_remain"]) is not bool
        or retained["target_may_remain"] != (not retained["target_absent"])
        or type(retained["target_identity_continuous"]) is not bool
        or type(retained["target_manager_stop_requested"]) is not bool
        or type(retained["target_manager_absence_proven"]) is not bool
        or retained["target_manager_absence_proven"]
        != retained["target_absent"]
        or type(retained["probe_path_deletion_calls"]) is not int
        or retained["probe_path_deletion_calls"] != 0
        or retained["scientific_occurrence_started"] is not False
        or retained["campaign_actual_measurement"] is not False
        or type(retained["substage_records"]) is not list
        or not retained["substage_records"]
    ):
        _fail("inner FAILURE joins or flags changed")
    records = [
        validate_substage_record(row, expected_index=index)
        for index, row in enumerate(retained["substage_records"])
    ]
    primary, derived = _validate_failure_records(
        records, attempt=attempt, authority=authority
    )
    if (
        retained["failed_substage"] != primary["substage"]
        or retained["errno"] != primary["errno"]
        or retained["errno_name"] != primary["errno_name"]
        or retained["error_type"] != primary["error_type"]
        or retained["message"] != primary["message"]
        or retained["child_reaped"] != derived["child_reaped"]
        or retained["process_may_remain"] != (not derived["child_reaped"])
        or retained["target_absent"] != derived["target_absent"]
        or retained["target_may_remain"] != (not derived["target_absent"])
        or retained["target_identity_continuous"]
        != derived["target_identity_continuous"]
        or retained["target_manager_stop_requested"]
        != derived["target_manager_stop_requested"]
        or retained["target_manager_absence_proven"]
        != derived["target_manager_absence_proven"]
    ):
        _fail("inner FAILURE top-level state is not derived from its records")
    return retained


def _artifact_fact(name: str, raw: bytes, *, exact: bool) -> dict[str, Any]:
    return {
        "name": name,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_exact": exact,
    }


def observe_inner_launch_state(
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    *,
    outer_terminal_names: frozenset[str] = frozenset(),
    recover_receipt_durability: bool = True,
    recover_prepare_receipt_durability: bool = True,
) -> tuple[dict[str, Any], bytes | None]:
    """Validate one legal pre-outer-terminal inventory and its inner identity."""

    if outer_terminal_names not in {
        frozenset(),
        frozenset({OUTER_LAUNCH_RECEIPT_NAME}),
        frozenset(
            {OUTER_LAUNCH_RECEIPT_NAME, OUTER_LAUNCH_SUCCESS_SEAL_NAME}
        ),
        frozenset(
            {OUTER_LAUNCH_RECEIPT_NAME, OUTER_LAUNCH_FAILURE_NAME}
        ),
        frozenset(
            {
                OUTER_LAUNCH_RECEIPT_NAME,
                OUTER_LAUNCH_SUCCESS_SEAL_NAME,
                OUTER_LAUNCH_FAILURE_NAME,
            }
        ),
        frozenset({OUTER_LAUNCH_FAILURE_NAME}),
    } or (
        type(recover_receipt_durability) is not bool
        or type(recover_prepare_receipt_durability) is not bool
    ):
        _fail("inner observation outer-terminal allowance changed")
    legal = {
        _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME),
        _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME),
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME, RECEIPT_NAME
        ),
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME, FAILURE_NAME
        ),
    }
    all_names = store.inventory_names(phase="OUTER_INNER_TERMINAL_OBSERVATION")
    if not outer_terminal_names:
        names = all_names
    else:
        if not outer_terminal_names.issubset(all_names):
            raise ForeignArtifactError(
                "inner recovery observation lacks its exact outer terminal"
            )
        names = frozenset(all_names - outer_terminal_names)
    if names not in legal:
        raise ForeignArtifactError(
            f"illegal inner terminal inventory: {sorted(names)!r}"
        )
    validate_prepared_authority(
        authority,
        external_root_raw,
        artifact_store=store,
        recover_prepare_receipt_durability=(
            recover_prepare_receipt_durability
        ),
    )
    expected_outer = build_outer_launch_attempt_document(
        authority, external_root_raw
    )
    outer_raw = store.read_exact(OUTER_LAUNCH_ATTEMPT_NAME)
    if outer_raw != canonical_json_bytes(expected_outer):
        _fail("retained outer LAUNCH_ATTEMPT bytes changed")
    expected_attempt = build_attempt_document(authority, external_root_raw)
    rows = [_artifact_fact(OUTER_LAUNCH_ATTEMPT_NAME, outer_raw, exact=True)]
    attempt_exact = False
    attempt_raw: bytes | None = None
    if ATTEMPT_NAME in names:
        attempt_raw = store.read_exact(ATTEMPT_NAME, allow_empty=True)
        if attempt_raw == canonical_json_bytes(expected_attempt):
            validate_attempt_document(
                loads_canonical_json(attempt_raw), authority, external_root_raw
            )
            attempt_exact = True
        rows.append(_artifact_fact(ATTEMPT_NAME, attempt_raw, exact=attempt_exact))
    terminal_kind = "NONE"
    terminal_id: str | None = None
    terminal_raw: bytes | None = None
    if RECEIPT_NAME in names:
        if not attempt_exact:
            _fail("inner RECEIPT lacks its exact ATTEMPT")
        terminal_raw = store.read_exact(RECEIPT_NAME, allow_empty=True)
        terminal_exact = False
        try:
            receipt = validate_receipt_document(
                loads_canonical_json(terminal_raw),
                expected_attempt,
                authority,
            )
            if canonical_json_bytes(receipt) != terminal_raw:
                _fail("inner RECEIPT bytes are not canonical exact")
        except BaseException:
            terminal_kind = "RECEIPT_PARTIAL"
        else:
            terminal_exact = True
            if not recover_receipt_durability:
                terminal_kind = "RECEIPT"
                terminal_id = receipt["preflight_receipt_id"]
            else:
                try:
                    store.stabilize_exact(RECEIPT_NAME, terminal_raw)
                except BaseException:
                    terminal_kind = "RECEIPT_UNCERTAIN"
                else:
                    terminal_kind = "RECEIPT"
                    terminal_id = receipt["preflight_receipt_id"]
        rows.append(
            _artifact_fact(RECEIPT_NAME, terminal_raw, exact=terminal_exact)
        )
    elif FAILURE_NAME in names:
        terminal_raw = store.read_exact(FAILURE_NAME, allow_empty=True)
        terminal_exact = False
        try:
            failure = validate_failure_document(
                loads_canonical_json(terminal_raw),
                expected_attempt,
                authority,
            )
        except PreflightError:
            terminal_kind = "FAILURE_PARTIAL"
        else:
            if recover_receipt_durability:
                store.stabilize_exact(FAILURE_NAME, terminal_raw)
            terminal_kind = "FAILURE"
            terminal_id = failure["preflight_failure_id"]
            terminal_exact = True
        rows.append(
            _artifact_fact(FAILURE_NAME, terminal_raw, exact=terminal_exact)
        )
    elif ATTEMPT_NAME in names:
        terminal_kind = "ATTEMPT_ONLY" if attempt_exact else "ATTEMPT_PARTIAL"
    observation = {
        "state": terminal_kind,
        "inner_attempt_exact": attempt_exact,
        "inner_probe_attempt_id": (
            expected_attempt["probe_attempt_id"] if attempt_exact else None
        ),
        "inner_terminal_id": terminal_id,
        "artifact_inventory": sorted(rows, key=lambda row: row["name"]),
    }
    return observation, terminal_raw


def _validate_inner_observation_document(
    value: Any,
    *,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {
        "state",
        "inner_attempt_exact",
        "inner_probe_attempt_id",
        "inner_terminal_id",
        "artifact_inventory",
    }
    states = {
        "NONE",
        "ATTEMPT_ONLY",
        "ATTEMPT_PARTIAL",
        "RECEIPT",
        "RECEIPT_PARTIAL",
        "RECEIPT_UNCERTAIN",
        "FAILURE",
        "FAILURE_PARTIAL",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["state"] not in states
        or type(value["inner_attempt_exact"]) is not bool
        or type(value["artifact_inventory"]) is not list
    ):
        _fail("outer inner observation fields or state changed")
    inventory: dict[str, dict[str, Any]] = {}
    retained_rows: list[dict[str, Any]] = []
    for row in value["artifact_inventory"]:
        if (
            type(row) is not dict
            or set(row) != {
                "name",
                "byte_count",
                "sha256",
                "canonical_exact",
            }
            or row["name"]
            not in {
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                RECEIPT_NAME,
                FAILURE_NAME,
            }
            or row["name"] in inventory
            or type(row["byte_count"]) is not int
            or row["byte_count"] < 0
            or not _is_lower_hex(row["sha256"], 64)
            or type(row["canonical_exact"]) is not bool
        ):
            _fail("outer inner observation artifact fact changed")
        retained = dict(row)
        inventory[row["name"]] = retained
        retained_rows.append(retained)
    if retained_rows != sorted(retained_rows, key=lambda row: row["name"]):
        _fail("outer inner observation artifact order changed")

    authority = validate_external_root_document(authority)
    authority_raw = canonical_json_bytes(authority)
    expected_outer_raw = canonical_json_bytes(
        build_outer_launch_attempt_document(authority, authority_raw)
    )
    expected_attempt = build_attempt_document(authority, authority_raw)
    expected_attempt_raw = canonical_json_bytes(expected_attempt)
    outer_fact = inventory.get(OUTER_LAUNCH_ATTEMPT_NAME)
    if outer_fact != _artifact_fact(
        OUTER_LAUNCH_ATTEMPT_NAME, expected_outer_raw, exact=True
    ):
        _fail("outer inner observation lost its exact LAUNCH_ATTEMPT")

    state = value["state"]
    attempt_present = ATTEMPT_NAME in inventory
    attempt_exact = value["inner_attempt_exact"]
    expected_probe_id = (
        expected_attempt["probe_attempt_id"] if attempt_exact else None
    )
    if (
        value["inner_probe_attempt_id"] != expected_probe_id
        or attempt_exact
        and inventory.get(ATTEMPT_NAME)
        != _artifact_fact(ATTEMPT_NAME, expected_attempt_raw, exact=True)
        or attempt_present
        and inventory[ATTEMPT_NAME]["canonical_exact"] is not attempt_exact
    ):
        _fail("outer inner observation ATTEMPT identity changed")

    if state == "NONE":
        expected_names = {OUTER_LAUNCH_ATTEMPT_NAME}
        expected_terminal_id: str | None = None
        expected_attempt_exact = False
    elif state in {"ATTEMPT_ONLY", "ATTEMPT_PARTIAL"}:
        expected_names = {OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME}
        expected_terminal_id = None
        expected_attempt_exact = state == "ATTEMPT_ONLY"
    else:
        terminal_name = (
            RECEIPT_NAME if state.startswith("RECEIPT") else FAILURE_NAME
        )
        expected_names = {
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            terminal_name,
        }
        terminal_exact = state in {
            "RECEIPT",
            "RECEIPT_UNCERTAIN",
            "FAILURE",
        }
        if inventory.get(terminal_name, {}).get("canonical_exact") is not terminal_exact:
            _fail("outer inner observation terminal exactness changed")
        expected_terminal_id = value["inner_terminal_id"]
        if state in {"RECEIPT", "FAILURE"}:
            if not _is_lower_hex(expected_terminal_id, 64):
                _fail("outer inner observation terminal identity changed")
        elif expected_terminal_id is not None:
            _fail("outer partial or uncertain terminal invented an identity")
        expected_attempt_exact = (
            True if state.startswith("RECEIPT") else attempt_exact
        )
    if (
        set(inventory) != expected_names
        or attempt_exact is not expected_attempt_exact
        or value["inner_terminal_id"] != expected_terminal_id
    ):
        _fail("outer inner observation state disagrees with its inventory")
    return dict(value)


def _build_outer_launch_receipt(
    outer_attempt: Mapping[str, Any],
    result: BoundedProcessResult,
    inner: Mapping[str, Any],
    prelaunch_absence: Mapping[str, Any],
    postlaunch_absence: Mapping[str, Any],
    deadline_contract: Mapping[str, Any],
) -> dict[str, Any]:
    deadline_contract = validate_outer_deadline_contract(deadline_contract)
    payload = {
        "schema": OUTER_LAUNCH_RECEIPT_SCHEMA,
        "outer_launch_attempt_id": outer_attempt["outer_launch_attempt_id"],
        "preflight_token": PREFLIGHT_TOKEN,
        "ordinal": PREFLIGHT_ORDINAL,
        "service_unit_name": SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        "systemd_run_argv_sha256": outer_attempt["systemd_run_argv_sha256"],
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "output_limit_exceeded": result.output_limit_exceeded,
        "stdout": _output_fact(result.stdout),
        "stderr": _output_fact(result.stderr),
        "inner_observation": dict(inner),
        "prelaunch_absence": dict(prelaunch_absence),
        "postlaunch_absence": dict(postlaunch_absence),
        "deadline_contract": dict(deadline_contract),
        "unit_absent": postlaunch_absence.get("unit_absent") is True,
        "target_absent": postlaunch_absence.get("target_absent") is True,
        "source_unit_absent": (
            postlaunch_absence.get("source_unit_absent") is True
        ),
        "source_path_absent": (
            postlaunch_absence.get("source_path_absent") is True
        ),
        "target_unit_absent": (
            postlaunch_absence.get("target_unit_absent") is True
        ),
        "target_path_absent": (
            postlaunch_absence.get("target_path_absent") is True
        ),
        "scientific_occurrence_started": False,
        "campaign_actual_measurement": False,
    }
    return _self_id_document(
        OUTER_LAUNCH_RECEIPT_DOMAIN, "outer_launch_receipt_id", payload
    )


def validate_outer_launch_receipt_document(
    document: Any,
    *,
    outer_attempt: Mapping[str, Any],
    inner_observation: Mapping[str, Any],
    inner_terminal_raw: bytes,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(document) is not dict
        or set(document) != OUTER_LAUNCH_RECEIPT_FIELDS
    ):
        _fail("outer LAUNCH_RECEIPT fields changed")
    retained = _validate_self_id(
        document,
        schema=OUTER_LAUNCH_RECEIPT_SCHEMA,
        identity_field="outer_launch_receipt_id",
        domain=OUTER_LAUNCH_RECEIPT_DOMAIN,
    )
    inner_observation = _validate_inner_observation_document(
        inner_observation, authority=authority
    )
    stdout = _validate_output_fact(
        retained["stdout"], byte_cap=MAX_SUBPROCESS_STDOUT_BYTES
    )
    stderr = _validate_output_fact(
        retained["stderr"], byte_cap=MAX_SUBPROCESS_STDERR_BYTES
    )
    prelaunch_absence = _validate_success_absence_fact(
        retained["prelaunch_absence"], authority
    )
    postlaunch_absence = _validate_success_absence_fact(
        retained["postlaunch_absence"], authority
    )
    deadline_contract = validate_outer_deadline_contract(
        retained["deadline_contract"]
    )
    after_attempt = deadline_contract[
        "remaining_after_attempt_publication_ns"
    ]
    after_process = deadline_contract["remaining_after_process_ns"]
    post_deadline = deadline_contract["post_absence_deadline_monotonic_ns"]
    after_post = deadline_contract["remaining_after_post_absence_ns"]
    after_inner = deadline_contract["remaining_after_inner_observation_ns"]
    before_terminal = deadline_contract[
        "remaining_before_terminal_publication_ns"
    ]
    if (
        type(after_attempt) is not int
        or after_attempt
        <= OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS * 1_000_000_000
        or type(after_process) is not int
        or after_process
        <= OUTER_REQUIRED_AFTER_PROCESS_SECONDS * 1_000_000_000
        or type(post_deadline) is not int
        or type(after_post) is not int
        or after_post
        < FORMAL_DEADLINE_MARGIN_SECONDS * 1_000_000_000
        or deadline_contract["formal_deadline_monotonic_ns"] - after_post
        > post_deadline
        or type(after_inner) is not int
        or after_inner <= 0
        or type(before_terminal) is not int
        or before_terminal <= 0
    ):
        _fail("outer LAUNCH_RECEIPT deadline gates were not all satisfied")
    if (
        retained["outer_launch_attempt_id"]
        != outer_attempt.get("outer_launch_attempt_id")
        or retained["preflight_token"] != PREFLIGHT_TOKEN
        or retained["ordinal"] != PREFLIGHT_ORDINAL
        or retained["service_unit_name"] != SERVICE_UNIT_NAME
        or retained["target_cgroup_name"] != TARGET_CGROUP_NAME
        or retained["systemd_run_argv_sha256"]
        != outer_attempt.get("systemd_run_argv_sha256")
        or retained["returncode"] != 0
        or retained["timed_out"] is not False
        or retained["output_limit_exceeded"] is not False
        or stderr != b""
        or type(inner_terminal_raw) is not bytes
        or stdout != inner_terminal_raw + b"\n"
        or retained["inner_observation"] != inner_observation
        or inner_observation.get("state") != "RECEIPT"
        or retained["unit_absent"] is not True
        or retained["target_absent"] is not True
        or retained["source_unit_absent"] is not True
        or retained["source_path_absent"] is not True
        or retained["target_unit_absent"] is not True
        or retained["target_path_absent"] is not True
        or retained["scientific_occurrence_started"] is not False
        or retained["campaign_actual_measurement"] is not False
    ):
        _fail("outer LAUNCH_RECEIPT success joins or flags changed")
    expected = _build_outer_launch_receipt(
        outer_attempt,
        BoundedProcessResult(
            tuple(outer_attempt["systemd_run_argv"]),
            0,
            stdout,
            stderr,
            False,
            False,
        ),
        inner_observation,
        prelaunch_absence,
        postlaunch_absence,
        deadline_contract,
    )
    if retained != expected:
        _fail("outer LAUNCH_RECEIPT canonical reconstruction changed")
    return retained


def _build_outer_launch_success_seal(
    outer_attempt: Mapping[str, Any],
    receipt: Mapping[str, Any],
    receipt_raw: bytes,
    *,
    verified_monotonic_ns: int,
    remaining_after_publication_ns: int,
) -> dict[str, Any]:
    deadline_ns = receipt["deadline_contract"][
        "formal_deadline_monotonic_ns"
    ]
    if (
        type(receipt_raw) is not bytes
        or canonical_json_bytes(receipt) != receipt_raw
        or type(verified_monotonic_ns) is not int
        or type(remaining_after_publication_ns) is not int
        or remaining_after_publication_ns <= 0
        or remaining_after_publication_ns
        != deadline_ns - verified_monotonic_ns
        or remaining_after_publication_ns
        > receipt["deadline_contract"][
            "remaining_before_terminal_publication_ns"
        ]
    ):
        _fail("outer success-seal decision input changed")
    payload = {
        "schema": OUTER_LAUNCH_SUCCESS_SEAL_SCHEMA,
        "outer_launch_attempt_id": outer_attempt["outer_launch_attempt_id"],
        "preflight_token": PREFLIGHT_TOKEN,
        "ordinal": PREFLIGHT_ORDINAL,
        "outer_launch_receipt_id": receipt["outer_launch_receipt_id"],
        "outer_launch_receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "decision_stage": OUTER_RECEIPT_DECISION_STAGE,
        "verified_monotonic_ns": verified_monotonic_ns,
        "formal_deadline_monotonic_ns": deadline_ns,
        "remaining_after_launch_receipt_publication_ns": (
            remaining_after_publication_ns
        ),
        "inventory_before_success_seal": sorted(
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                RECEIPT_NAME,
                OUTER_LAUNCH_RECEIPT_NAME,
            )
        ),
        "scientific_occurrence_started": False,
        "campaign_actual_measurement": False,
    }
    return _self_id_document(
        OUTER_LAUNCH_SUCCESS_SEAL_DOMAIN,
        "outer_launch_success_seal_id",
        payload,
    )


def validate_outer_launch_success_seal_document(
    document: Any,
    *,
    outer_attempt: Mapping[str, Any],
    receipt: Mapping[str, Any],
    receipt_raw: bytes,
) -> dict[str, Any]:
    if (
        type(document) is not dict
        or set(document) != OUTER_LAUNCH_SUCCESS_SEAL_FIELDS
    ):
        _fail("outer LAUNCH_SUCCESS_SEAL fields changed")
    retained = _validate_self_id(
        document,
        schema=OUTER_LAUNCH_SUCCESS_SEAL_SCHEMA,
        identity_field="outer_launch_success_seal_id",
        domain=OUTER_LAUNCH_SUCCESS_SEAL_DOMAIN,
    )
    verified_ns = retained["verified_monotonic_ns"]
    deadline_ns = retained["formal_deadline_monotonic_ns"]
    remaining_ns = retained[
        "remaining_after_launch_receipt_publication_ns"
    ]
    expected_inventory = sorted(
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
        )
    )
    if (
        canonical_json_bytes(receipt) != receipt_raw
        or retained["outer_launch_attempt_id"]
        != outer_attempt.get("outer_launch_attempt_id")
        or retained["preflight_token"] != PREFLIGHT_TOKEN
        or retained["ordinal"] != PREFLIGHT_ORDINAL
        or retained["outer_launch_receipt_id"]
        != receipt.get("outer_launch_receipt_id")
        or retained["outer_launch_receipt_sha256"]
        != hashlib.sha256(receipt_raw).hexdigest()
        or retained["decision_stage"] != OUTER_RECEIPT_DECISION_STAGE
        or type(verified_ns) is not int
        or type(deadline_ns) is not int
        or deadline_ns
        != receipt["deadline_contract"]["formal_deadline_monotonic_ns"]
        or type(remaining_ns) is not int
        or remaining_ns <= 0
        or remaining_ns != deadline_ns - verified_ns
        or remaining_ns
        > receipt["deadline_contract"][
            "remaining_before_terminal_publication_ns"
        ]
        or retained["inventory_before_success_seal"] != expected_inventory
        or retained["scientific_occurrence_started"] is not False
        or retained["campaign_actual_measurement"] is not False
    ):
        _fail("outer LAUNCH_SUCCESS_SEAL joins or deadline decision changed")
    expected = _build_outer_launch_success_seal(
        outer_attempt,
        receipt,
        receipt_raw,
        verified_monotonic_ns=verified_ns,
        remaining_after_publication_ns=remaining_ns,
    )
    if retained != expected:
        _fail("outer LAUNCH_SUCCESS_SEAL canonical reconstruction changed")
    return retained


def _recover_outer_launch_receipt(
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    *,
    outer_terminal_names: frozenset[str] = frozenset(
        {OUTER_LAUNCH_RECEIPT_NAME}
    ),
) -> dict[str, Any]:
    validate_prepared_authority(
        authority, external_root_raw, artifact_store=store
    )
    outer_attempt = build_outer_launch_attempt_document(
        authority, external_root_raw
    )
    retained_outer = store.read_exact(OUTER_LAUNCH_ATTEMPT_NAME)
    if retained_outer != canonical_json_bytes(outer_attempt):
        _fail("outer receipt recovery ATTEMPT bytes changed")
    inner, inner_terminal_raw = observe_inner_launch_state(
        store,
        authority,
        external_root_raw,
        outer_terminal_names=outer_terminal_names,
    )
    if inner_terminal_raw is None:
        _fail("outer receipt recovery lacks inner terminal bytes")
    receipt_raw = store.read_exact(OUTER_LAUNCH_RECEIPT_NAME)
    receipt = validate_outer_launch_receipt_document(
        loads_canonical_json(receipt_raw),
        outer_attempt=outer_attempt,
        inner_observation=inner,
        inner_terminal_raw=inner_terminal_raw,
        authority=authority,
    )
    if canonical_json_bytes(receipt) != receipt_raw:
        _fail("outer receipt recovery bytes are not canonical exact")
    store.stabilize_exact(OUTER_LAUNCH_RECEIPT_NAME, receipt_raw)
    store.require_inventory(
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            *tuple(outer_terminal_names),
        ),
        phase="OUTER_LAUNCH_RECEIPT_RECOVERED",
    )
    return receipt


def _recover_outer_launch_success(
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    outer_terminals = frozenset(
        {OUTER_LAUNCH_RECEIPT_NAME, OUTER_LAUNCH_SUCCESS_SEAL_NAME}
    )
    receipt = _recover_outer_launch_receipt(
        store,
        authority,
        external_root_raw,
        outer_terminal_names=outer_terminals,
    )
    outer_attempt = build_outer_launch_attempt_document(
        authority, external_root_raw
    )
    receipt_raw = store.read_exact(OUTER_LAUNCH_RECEIPT_NAME)
    seal_raw = store.read_exact(OUTER_LAUNCH_SUCCESS_SEAL_NAME)
    seal = validate_outer_launch_success_seal_document(
        loads_canonical_json(seal_raw),
        outer_attempt=outer_attempt,
        receipt=receipt,
        receipt_raw=receipt_raw,
    )
    if canonical_json_bytes(seal) != seal_raw:
        _fail("outer LAUNCH_SUCCESS_SEAL bytes are not canonical exact")
    store.stabilize_exact(OUTER_LAUNCH_SUCCESS_SEAL_NAME, seal_raw)
    store.require_inventory(
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
            OUTER_LAUNCH_SUCCESS_SEAL_NAME,
        ),
        phase="OUTER_LAUNCH_SUCCESS_RECOVERED",
    )
    return receipt


def _build_outer_failure_components(
    *,
    process_adapter_error: BaseException | None = None,
    deadline_gate_error: BaseException | None = None,
    inner_observation_error: BaseException | None = None,
    postlaunch_absence_error: BaseException | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "process_adapter_error": _error_fact(process_adapter_error),
        "deadline_gate_error": _error_fact(deadline_gate_error),
        "inner_observation_error": _error_fact(inner_observation_error),
        "postlaunch_absence_error": _error_fact(
            postlaunch_absence_error
        ),
    }


def _validate_outer_failure_components(
    value: Any,
) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or set(value) != OUTER_FAILURE_COMPONENT_FIELDS:
        _fail("outer failure component fields changed")
    return {
        name: _validate_error_fact(value[name], required=False)
        for name in sorted(OUTER_FAILURE_COMPONENT_FIELDS)
    }


def _error_fact_present(value: Mapping[str, Any]) -> bool:
    return value.get("error_type") is not None


def _validate_inventory_before_launch_failure(value: Any) -> list[str]:
    legal = {
        tuple(sorted((OUTER_LAUNCH_ATTEMPT_NAME,))),
        tuple(sorted((OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME))),
        tuple(
            sorted(
                (OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME, RECEIPT_NAME)
            )
        ),
        tuple(
            sorted(
                (OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME, FAILURE_NAME)
            )
        ),
        tuple(
            sorted(
                (
                    OUTER_LAUNCH_ATTEMPT_NAME,
                    ATTEMPT_NAME,
                    RECEIPT_NAME,
                    OUTER_LAUNCH_RECEIPT_NAME,
                )
            )
        ),
        tuple(
            sorted(
                (
                    OUTER_LAUNCH_ATTEMPT_NAME,
                    ATTEMPT_NAME,
                    RECEIPT_NAME,
                    OUTER_LAUNCH_RECEIPT_NAME,
                    OUTER_LAUNCH_SUCCESS_SEAL_NAME,
                )
            )
        ),
    }
    if (
        type(value) is not list
        or any(type(name) is not str for name in value)
        or tuple(value) not in legal
    ):
        _fail("outer failure prepublication inventory snapshot changed")
    return list(value)


def _reconstruct_ordinary_deadline_error(
    deadline_contract: Mapping[str, Any],
) -> dict[str, Any]:
    deadline_contract = validate_outer_deadline_contract(deadline_contract)
    after_attempt = deadline_contract[
        "remaining_after_attempt_publication_ns"
    ]
    after_process = deadline_contract["remaining_after_process_ns"]
    post_deadline = deadline_contract["post_absence_deadline_monotonic_ns"]
    after_post = deadline_contract["remaining_after_post_absence_ns"]
    after_inner = deadline_contract["remaining_after_inner_observation_ns"]
    before_terminal = deadline_contract[
        "remaining_before_terminal_publication_ns"
    ]
    if (
        type(after_attempt) is not int
        or after_attempt
        <= OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS * 1_000_000_000
        or type(after_process) is not int
        or type(before_terminal) is not int
    ):
        _fail("ordinary outer failure timeline changed")
    reconstructed_error: BaseException | None = None
    process_gate = (
        after_process
        <= OUTER_REQUIRED_AFTER_PROCESS_SECONDS * 1_000_000_000
    )
    if process_gate:
        if any(
            value is not None
            for value in (post_deadline, after_post, after_inner)
        ):
            _fail("process deadline gate acquired a later observation")
        reconstructed_error = OSError(
            errno.ETIMEDOUT,
            "outer process left insufficient absence/closure time",
        )
    else:
        if type(post_deadline) is not int or type(after_post) is not int:
            _fail("ordinary outer failure lacks postlaunch timing")
        post_gate = (
            after_post
            < FORMAL_DEADLINE_MARGIN_SECONDS * 1_000_000_000
        )
        if post_gate:
            if after_inner is not None:
                _fail(
                    "post-absence deadline gate acquired an inner observation"
                )
            reconstructed_error = OSError(
                errno.ETIMEDOUT,
                "postlaunch absence consumed the closure reserve",
            )
        else:
            if type(after_inner) is not int:
                _fail("ordinary outer failure lacks inner-observation timing")
            if after_inner <= 0:
                reconstructed_error = OSError(
                    errno.ETIMEDOUT,
                    "inner observation exhausted the formal deadline",
                )
    if before_terminal <= 0:
        reconstructed_error = OSError(
            errno.ETIMEDOUT,
            "outer terminal publication gate exhausted the formal deadline",
        )
    return _error_fact(reconstructed_error)


def _derive_ordinary_outer_failure_reason(
    *,
    result: BoundedProcessResult | None,
    inner: Mapping[str, Any] | None,
    inner_terminal_raw: bytes | None,
    postlaunch_absence: Mapping[str, Any] | None,
    deadline_contract: Mapping[str, Any],
    failure_components: Mapping[str, Any],
    launch_error: Mapping[str, Any],
) -> str:
    components = _validate_outer_failure_components(failure_components)
    launch_error = _validate_error_fact(launch_error, required=False)
    process_error = components["process_adapter_error"]
    deadline_error = components["deadline_gate_error"]
    inner_error = components["inner_observation_error"]
    absence_error = components["postlaunch_absence_error"]
    process_error_present = _error_fact_present(process_error)
    deadline_error_present = _error_fact_present(deadline_error)
    inner_error_present = _error_fact_present(inner_error)
    absence_error_present = _error_fact_present(absence_error)
    if process_error_present is (result is not None):
        _fail("outer process result/error acquisition is not exact")
    deadline_contract = validate_outer_deadline_contract(deadline_contract)
    after_process = deadline_contract["remaining_after_process_ns"]
    post_deadline = deadline_contract["post_absence_deadline_monotonic_ns"]
    after_post = deadline_contract["remaining_after_post_absence_ns"]
    after_inner = deadline_contract["remaining_after_inner_observation_ns"]
    post_observation_attempted = (
        type(post_deadline) is int and type(after_post) is int
    )
    if post_observation_attempted:
        if absence_error_present is (postlaunch_absence is not None):
            _fail("outer postlaunch absence result/error is not exact")
        post_completed_ns = (
            deadline_contract["formal_deadline_monotonic_ns"] - after_post
        )
        if post_completed_ns > post_deadline:
            expected_absence_error = _error_fact(
                OSError(
                    errno.ETIMEDOUT,
                    "postlaunch absence observer exceeded its local deadline",
                )
            )
            if absence_error != expected_absence_error:
                _fail("outer local absence deadline error changed")
    elif absence_error_present or postlaunch_absence is not None:
        _fail("outer skipped absence observation retained a result or error")
    inner_observation_attempted = type(after_inner) is int
    if inner_observation_attempted:
        if inner_error_present is (inner is not None):
            _fail("outer inner observation result/error is not exact")
    elif inner_error_present or inner is not None:
        _fail("outer skipped inner observation retained a result or error")
    if inner_error_present and inner_terminal_raw is not None:
        _fail("outer failed inner observation retained terminal bytes")
    expected_launch_error = next(
        (
            fact
            for fact in (
                process_error,
                absence_error,
                inner_error,
                deadline_error,
            )
            if _error_fact_present(fact)
        ),
        _error_fact(None),
    )
    if launch_error != expected_launch_error:
        _fail("ordinary outer launch_error left its component precedence")
    expected_deadline_error = _reconstruct_ordinary_deadline_error(
        deadline_contract
    )
    if deadline_error != expected_deadline_error:
        _fail("outer deadline component disagrees with its exact timeline")
    if inner is not None and inner.get("state") == "RECEIPT":
        if type(inner_terminal_raw) is not bytes:
            _fail("outer RECEIPT observation lacks reconstructed terminal bytes")
    reasons: list[str] = []
    if process_error_present:
        reasons.append("PROCESS_ADAPTER_ERROR")
    if result is not None and result.returncode != 0:
        reasons.append("SYSTEMD_RUN_NONZERO")
    if result is not None and result.timed_out:
        reasons.append("SYSTEMD_RUN_TIMEOUT")
    if result is not None and result.output_limit_exceeded:
        reasons.append("SYSTEMD_RUN_OUTPUT_LIMIT")
    if result is not None and result.stderr:
        reasons.append("SYSTEMD_RUN_STDERR")
    if deadline_error_present:
        reasons.append("DEADLINE_GATE_FAILED")
    if inner_error_present:
        reasons.append("INNER_OBSERVATION_ERROR")
    elif inner is None or inner.get("state") != "RECEIPT":
        reasons.append("INNER_NOT_RECEIPT")
    elif (
        result is not None
        and result.stdout != inner_terminal_raw + b"\n"
    ):
        reasons.append("INNER_STDOUT_MISMATCH")
    if absence_error_present or postlaunch_absence is None:
        reasons.append("POSTLAUNCH_ABSENCE_UNPROVEN")
    elif (
        postlaunch_absence.get("unit_absent") is not True
        or postlaunch_absence.get("target_absent") is not True
    ):
        reasons.append("POSTLAUNCH_RESIDUAL")
    if not reasons:
        _fail("ordinary outer failure reconstructs complete success")
    return "+".join(reasons)


def _publication_recovery_raw_identity(
    raw: bytes | None,
) -> tuple[int | None, str | None]:
    if raw is None:
        return None, None
    if type(raw) is not bytes or len(raw) > MAX_ARTIFACT_BYTES:
        _fail("publication recovery raw identity input changed")
    return len(raw), hashlib.sha256(raw).hexdigest()


def _validate_publication_recovery_raw_identity(
    byte_count: Any, sha256: Any, *, label: str
) -> None:
    if byte_count is None and sha256 is None:
        return
    if (
        type(byte_count) is not int
        or byte_count < 0
        or byte_count > MAX_ARTIFACT_BYTES
        or not _is_lower_hex(sha256, 64)
    ):
        _fail(f"{label} recovery raw identity changed")


def _build_outer_launch_failure(
    outer_attempt: Mapping[str, Any],
    *,
    result: BoundedProcessResult | None,
    inner: Mapping[str, Any] | None,
    prelaunch_absence: Mapping[str, Any],
    postlaunch_absence: Mapping[str, Any] | None,
    error: BaseException | None,
    reason: str,
    deadline_contract: Mapping[str, Any],
    inventory_before_launch_failure: Sequence[str],
    attempt_observed_exact: bool = True,
    attempt_recovery_raw: bytes | None = None,
    receipt_publication: PublicationOwnershipToken | None = None,
    receipt_publication_stage: str | None = None,
    receipt_observed_exact: bool = False,
    receipt_recovery_raw: bytes | None = None,
    receipt_recovery_error: BaseException | None = None,
    receipt_decision_stage: str | None = None,
    receipt_verified_monotonic_ns: int | None = None,
    receipt_raw_sha256: str | None = None,
    remaining_after_launch_receipt_publication_ns: int | None = None,
    success_seal_publication: PublicationOwnershipToken | None = None,
    success_seal_publication_stage: str | None = None,
    success_seal_observed_exact: bool = False,
    success_seal_recovery_raw: bytes | None = None,
    success_seal_recovery_error: BaseException | None = None,
    process_adapter_error: BaseException | None = None,
    deadline_gate_error: BaseException | None = None,
    inner_observation_error: BaseException | None = None,
    postlaunch_absence_error: BaseException | None = None,
) -> dict[str, Any]:
    expected_attempt_raw = canonical_json_bytes(outer_attempt)
    if attempt_recovery_raw is None:
        if attempt_observed_exact is not True:
            _fail("partial outer attempt lacks retained raw identity")
        attempt_recovery_raw = expected_attempt_raw
    if type(attempt_observed_exact) is not bool:
        _fail("outer attempt exactness fact changed")
    if attempt_observed_exact:
        if attempt_recovery_raw != expected_attempt_raw:
            _fail("exact outer attempt recovery bytes changed")
    elif not (
        type(attempt_recovery_raw) is bytes
        and len(attempt_recovery_raw) < len(expected_attempt_raw)
        and expected_attempt_raw.startswith(attempt_recovery_raw)
    ):
        _fail("partial outer attempt is not a strict canonical prefix")
    if receipt_publication is not None and (
        type(receipt_publication) is not PublicationOwnershipToken
        or receipt_publication.name != OUTER_LAUNCH_RECEIPT_NAME
    ):
        _fail("outer receipt publication token changed")
    if success_seal_publication is not None and (
        type(success_seal_publication) is not PublicationOwnershipToken
        or success_seal_publication.name != OUTER_LAUNCH_SUCCESS_SEAL_NAME
    ):
        _fail("outer success-seal publication token changed")
    (
        attempt_recovery_raw_byte_count,
        attempt_recovery_raw_sha256,
    ) = _publication_recovery_raw_identity(attempt_recovery_raw)
    (
        receipt_recovery_raw_byte_count,
        receipt_recovery_raw_sha256,
    ) = _publication_recovery_raw_identity(receipt_recovery_raw)
    (
        success_seal_recovery_raw_byte_count,
        success_seal_recovery_raw_sha256,
    ) = _publication_recovery_raw_identity(success_seal_recovery_raw)
    deadline_contract = validate_outer_deadline_contract(deadline_contract)
    retained_inventory = _validate_inventory_before_launch_failure(
        sorted(inventory_before_launch_failure)
    )
    payload = {
        "schema": OUTER_LAUNCH_FAILURE_SCHEMA,
        "outer_launch_attempt_id": outer_attempt["outer_launch_attempt_id"],
        "preflight_token": PREFLIGHT_TOKEN,
        "ordinal": PREFLIGHT_ORDINAL,
        "service_unit_name": SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        "systemd_run_argv_sha256": outer_attempt["systemd_run_argv_sha256"],
        "failure_reason": reason[:512],
        "launch_error": _error_fact(error),
        "failure_components": _build_outer_failure_components(
            process_adapter_error=process_adapter_error,
            deadline_gate_error=deadline_gate_error,
            inner_observation_error=inner_observation_error,
            postlaunch_absence_error=postlaunch_absence_error,
        ),
        "launch_attempt_observed_exact": attempt_observed_exact,
        "launch_attempt_recovery_raw_byte_count": (
            attempt_recovery_raw_byte_count
        ),
        "launch_attempt_recovery_raw_sha256": (
            attempt_recovery_raw_sha256
        ),
        "returncode": None if result is None else result.returncode,
        "timed_out": None if result is None else result.timed_out,
        "output_limit_exceeded": (
            None if result is None else result.output_limit_exceeded
        ),
        "stdout": _output_fact(b"" if result is None else result.stdout),
        "stderr": _output_fact(b"" if result is None else result.stderr),
        "inner_observation": None if inner is None else dict(inner),
        "inventory_before_launch_failure": retained_inventory,
        "prelaunch_absence": dict(prelaunch_absence),
        "postlaunch_absence": (
            None if postlaunch_absence is None else dict(postlaunch_absence)
        ),
        "deadline_contract": dict(deadline_contract),
        "unit_absent": (
            None
            if postlaunch_absence is None
            else postlaunch_absence.get("unit_absent") is True
        ),
        "target_absent": (
            None
            if postlaunch_absence is None
            else postlaunch_absence.get("target_absent") is True
        ),
        "source_unit_absent": (
            None
            if postlaunch_absence is None
            else postlaunch_absence.get("source_unit_absent") is True
        ),
        "source_path_absent": (
            None
            if postlaunch_absence is None
            else postlaunch_absence.get("source_path_absent") is True
        ),
        "target_unit_absent": (
            None
            if postlaunch_absence is None
            else postlaunch_absence.get("target_unit_absent") is True
        ),
        "target_path_absent": (
            None
            if postlaunch_absence is None
            else postlaunch_absence.get("target_path_absent") is True
        ),
        "launch_receipt_path_created": (
            False if receipt_publication is None else receipt_publication.path_created
        ),
        "launch_receipt_publication_completion_claim": (
            None
            if reason == "OUTER_RECEIPT_DURABILITY_RECOVERY_FAILED"
            else (
                False
                if receipt_publication is None
                else receipt_publication.completed
            )
        ),
        "launch_receipt_publication_artifact": (
            None if receipt_publication is None else OUTER_LAUNCH_RECEIPT_NAME
        ),
        "launch_receipt_publication_stage_class": receipt_publication_stage,
        "launch_receipt_observed_exact": receipt_observed_exact,
        "launch_receipt_recovery_raw_byte_count": (
            receipt_recovery_raw_byte_count
        ),
        "launch_receipt_recovery_raw_sha256": (
            receipt_recovery_raw_sha256
        ),
        "launch_receipt_recovery_error": _error_fact(receipt_recovery_error),
        "launch_receipt_decision_stage": receipt_decision_stage,
        "launch_receipt_verified_monotonic_ns": (
            receipt_verified_monotonic_ns
        ),
        "launch_receipt_raw_sha256": receipt_raw_sha256,
        "remaining_after_launch_receipt_publication_ns": (
            remaining_after_launch_receipt_publication_ns
        ),
        "launch_success_seal_path_created": (
            False
            if success_seal_publication is None
            else success_seal_publication.path_created
        ),
        "launch_success_seal_publication_completion_claim": (
            None
            if reason == "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED"
            else (
                False
                if success_seal_publication is None
                else success_seal_publication.completed
            )
        ),
        "launch_success_seal_publication_stage_class": (
            success_seal_publication_stage
        ),
        "launch_success_seal_observed_exact": (
            success_seal_observed_exact
        ),
        "launch_success_seal_recovery_raw_byte_count": (
            success_seal_recovery_raw_byte_count
        ),
        "launch_success_seal_recovery_raw_sha256": (
            success_seal_recovery_raw_sha256
        ),
        "launch_success_seal_recovery_error": _error_fact(
            success_seal_recovery_error
        ),
        "scientific_occurrence_started": False,
        "campaign_actual_measurement": False,
    }
    return _self_id_document(
        OUTER_LAUNCH_FAILURE_DOMAIN, "outer_launch_failure_id", payload
    )


def validate_outer_launch_failure_document(
    document: Any,
    *,
    outer_attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(document) is not dict
        or set(document) != OUTER_LAUNCH_FAILURE_FIELDS
    ):
        _fail("outer LAUNCH_FAILURE fields changed")
    retained = _validate_self_id(
        document,
        schema=OUTER_LAUNCH_FAILURE_SCHEMA,
        identity_field="outer_launch_failure_id",
        domain=OUTER_LAUNCH_FAILURE_DOMAIN,
    )
    inner_observation = (
        None
        if retained["inner_observation"] is None
        else _validate_inner_observation_document(
            retained["inner_observation"], authority=authority
        )
    )
    inventory_before_failure = _validate_inventory_before_launch_failure(
        retained["inventory_before_launch_failure"]
    )
    _validate_error_fact(retained["launch_error"], required=False)
    failure_components = _validate_outer_failure_components(
        retained["failure_components"]
    )
    _validate_publication_recovery_raw_identity(
        retained["launch_attempt_recovery_raw_byte_count"],
        retained["launch_attempt_recovery_raw_sha256"],
        label="outer LAUNCH_ATTEMPT",
    )
    recovery_error = _validate_error_fact(
        retained["launch_receipt_recovery_error"],
        required=False,
    )
    seal_recovery_error = _validate_error_fact(
        retained["launch_success_seal_recovery_error"], required=False
    )
    _validate_publication_recovery_raw_identity(
        retained["launch_receipt_recovery_raw_byte_count"],
        retained["launch_receipt_recovery_raw_sha256"],
        label="outer LAUNCH_RECEIPT",
    )
    _validate_publication_recovery_raw_identity(
        retained["launch_success_seal_recovery_raw_byte_count"],
        retained["launch_success_seal_recovery_raw_sha256"],
        label="outer LAUNCH_SUCCESS_SEAL",
    )
    stdout = _validate_output_fact(
        retained["stdout"], byte_cap=MAX_SUBPROCESS_STDOUT_BYTES
    )
    stderr = _validate_output_fact(
        retained["stderr"], byte_cap=MAX_SUBPROCESS_STDERR_BYTES
    )
    validate_outer_deadline_contract(retained["deadline_contract"])
    prelaunch = _validate_success_absence_fact(
        retained["prelaunch_absence"], authority
    )
    postlaunch = retained["postlaunch_absence"]
    if postlaunch is not None and type(postlaunch) is not dict:
        _fail("outer LAUNCH_FAILURE postlaunch absence changed")
    if postlaunch is not None:
        postlaunch = _validate_success_absence_fact(postlaunch, authority)
    expected_unit_absent = (
        None if postlaunch is None else postlaunch.get("unit_absent") is True
    )
    expected_target_absent = (
        None if postlaunch is None else postlaunch.get("target_absent") is True
    )
    expected_source_unit_absent = (
        None
        if postlaunch is None
        else postlaunch.get("source_unit_absent") is True
    )
    expected_source_path_absent = (
        None
        if postlaunch is None
        else postlaunch.get("source_path_absent") is True
    )
    expected_target_unit_absent = (
        None
        if postlaunch is None
        else postlaunch.get("target_unit_absent") is True
    )
    expected_target_path_absent = (
        None
        if postlaunch is None
        else postlaunch.get("target_path_absent") is True
    )
    receipt_created = retained["launch_receipt_path_created"]
    result_present = retained["returncode"] is not None
    if (
        retained["outer_launch_attempt_id"]
        != outer_attempt.get("outer_launch_attempt_id")
        or retained["preflight_token"] != PREFLIGHT_TOKEN
        or retained["ordinal"] != PREFLIGHT_ORDINAL
        or retained["service_unit_name"] != SERVICE_UNIT_NAME
        or retained["target_cgroup_name"] != TARGET_CGROUP_NAME
        or retained["systemd_run_argv_sha256"]
        != outer_attempt.get("systemd_run_argv_sha256")
        or type(retained["failure_reason"]) is not str
        or not retained["failure_reason"]
        or type(retained["launch_attempt_observed_exact"]) is not bool
        or retained["launch_attempt_recovery_raw_byte_count"] is None
        or retained["launch_attempt_recovery_raw_sha256"] is None
        or result_present
        and (
            type(retained["returncode"]) is not int
            or type(retained["timed_out"]) is not bool
            or type(retained["output_limit_exceeded"]) is not bool
        )
        or not result_present
        and (
            retained["timed_out"] is not None
            or retained["output_limit_exceeded"] is not None
            or stdout != b""
            or stderr != b""
        )
        or retained["inner_observation"] != inner_observation
        or retained["inventory_before_launch_failure"]
        != inventory_before_failure
        or retained["unit_absent"] != expected_unit_absent
        or retained["target_absent"] != expected_target_absent
        or retained["source_unit_absent"] != expected_source_unit_absent
        or retained["source_path_absent"] != expected_source_path_absent
        or retained["target_unit_absent"] != expected_target_unit_absent
        or retained["target_path_absent"] != expected_target_path_absent
        or type(receipt_created) is not bool
        or (
            retained["launch_receipt_publication_completion_claim"]
            is not None
            and type(
                retained["launch_receipt_publication_completion_claim"]
            )
            is not bool
        )
        or type(retained["launch_receipt_observed_exact"]) is not bool
        or retained["launch_receipt_decision_stage"] is not None
        and type(retained["launch_receipt_decision_stage"]) is not str
        or retained["launch_receipt_verified_monotonic_ns"] is not None
        and type(retained["launch_receipt_verified_monotonic_ns"]) is not int
        or retained["launch_receipt_raw_sha256"] is not None
        and not _is_lower_hex(retained["launch_receipt_raw_sha256"], 64)
        or retained["remaining_after_launch_receipt_publication_ns"]
        is not None
        and type(
            retained["remaining_after_launch_receipt_publication_ns"]
        )
        is not int
        or type(retained["launch_success_seal_path_created"]) is not bool
        or (
            retained["launch_success_seal_publication_completion_claim"]
            is not None
            and type(
                retained[
                    "launch_success_seal_publication_completion_claim"
                ]
            )
            is not bool
        )
        or type(retained["launch_success_seal_observed_exact"]) is not bool
        or retained["scientific_occurrence_started"] is not False
        or retained["campaign_actual_measurement"] is not False
    ):
        _fail("outer LAUNCH_FAILURE joins or flags changed")
    if set(failure_components) != OUTER_FAILURE_COMPONENT_FIELDS:
        _fail("outer LAUNCH_FAILURE component schema changed")
    if receipt_created:
        if (
            retained["launch_receipt_publication_artifact"]
            != OUTER_LAUNCH_RECEIPT_NAME
            or type(retained["launch_receipt_publication_stage_class"])
            is not str
            or not retained["launch_receipt_publication_stage_class"]
        ):
            _fail("outer LAUNCH_FAILURE receipt publication fact changed")
    elif (
        retained["launch_receipt_publication_completion_claim"] is not False
        or retained["launch_receipt_publication_artifact"] is not None
        or retained["launch_receipt_publication_stage_class"] is not None
        or retained["launch_receipt_observed_exact"] is not False
        or retained["launch_receipt_recovery_raw_byte_count"] is not None
        or retained["launch_receipt_recovery_raw_sha256"] is not None
        or any(value is not None for value in recovery_error.values())
        or retained["launch_receipt_decision_stage"] is not None
        or retained["launch_receipt_verified_monotonic_ns"] is not None
        or retained["launch_receipt_raw_sha256"] is not None
        or retained["remaining_after_launch_receipt_publication_ns"]
        is not None
        or retained["launch_success_seal_path_created"] is not False
    ):
        _fail("outer LAUNCH_FAILURE carries an unowned receipt fact")
    seal_created = retained["launch_success_seal_path_created"]
    if seal_created:
        if (
            receipt_created is not True
            or type(retained["launch_success_seal_publication_stage_class"])
            is not str
            or not retained["launch_success_seal_publication_stage_class"]
        ):
            _fail("outer LAUNCH_FAILURE success-seal publication fact changed")
    elif (
        retained["launch_success_seal_publication_completion_claim"]
        is not False
        or retained["launch_success_seal_publication_stage_class"] is not None
        or retained["launch_success_seal_observed_exact"] is not False
        or retained["launch_success_seal_recovery_raw_byte_count"] is not None
        or retained["launch_success_seal_recovery_raw_sha256"] is not None
        or any(value is not None for value in seal_recovery_error.values())
    ):
        _fail("outer LAUNCH_FAILURE carries an unowned success-seal fact")
    return retained


_OUTER_SUCCESS_CONTEXT_FIELDS = (
    "returncode",
    "timed_out",
    "output_limit_exceeded",
    "stdout",
    "stderr",
    "inner_observation",
    "prelaunch_absence",
    "postlaunch_absence",
    "deadline_contract",
    "unit_absent",
    "target_absent",
    "source_unit_absent",
    "source_path_absent",
    "target_unit_absent",
    "target_path_absent",
)


def _outer_failure_result(
    failure: Mapping[str, Any], outer_attempt: Mapping[str, Any]
) -> BoundedProcessResult | None:
    stdout = _validate_output_fact(
        failure["stdout"], byte_cap=MAX_SUBPROCESS_STDOUT_BYTES
    )
    stderr = _validate_output_fact(
        failure["stderr"], byte_cap=MAX_SUBPROCESS_STDERR_BYTES
    )
    if failure["returncode"] is None:
        return None
    return BoundedProcessResult(
        tuple(outer_attempt["systemd_run_argv"]),
        failure["returncode"],
        stdout,
        stderr,
        failure["timed_out"],
        failure["output_limit_exceeded"],
    )


def _reconstruct_outer_receipt_from_failure(
    failure: Mapping[str, Any],
    *,
    outer_attempt: Mapping[str, Any],
    observed_inner: Mapping[str, Any],
    inner_terminal_raw: bytes,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    result = _outer_failure_result(failure, outer_attempt)
    postlaunch_absence = failure["postlaunch_absence"]
    if (
        result is None
        or type(postlaunch_absence) is not dict
        or failure["inner_observation"] != observed_inner
    ):
        _fail("outer receipt failure lost its reconstructed success context")
    expected = _build_outer_launch_receipt(
        outer_attempt,
        result,
        observed_inner,
        failure["prelaunch_absence"],
        postlaunch_absence,
        failure["deadline_contract"],
    )
    expected = validate_outer_launch_receipt_document(
        expected,
        outer_attempt=outer_attempt,
        inner_observation=observed_inner,
        inner_terminal_raw=inner_terminal_raw,
        authority=authority,
    )
    if any(
        failure[field] != expected[field]
        for field in _OUTER_SUCCESS_CONTEXT_FIELDS
    ):
        _fail("outer receipt failure success-context joins changed")
    return expected


def _outer_failure_components_are_empty(
    failure: Mapping[str, Any],
) -> bool:
    components = _validate_outer_failure_components(
        failure["failure_components"]
    )
    return not any(_error_fact_present(fact) for fact in components.values())


def _outer_receipt_postpublication_deadline_error() -> OSError:
    return OSError(
        errno.ETIMEDOUT,
        "outer LAUNCH_RECEIPT publication crossed the formal deadline",
    )


def _classify_retained_publication_bytes(
    store: DurableArtifactStore,
    name: str,
    expected_raw: bytes,
    *,
    label: str,
) -> tuple[bool, bytes]:
    try:
        retained_raw = store.read_exact(name, allow_empty=True)
    except BaseException as error:
        raise OuterReceiptPublicationUncertain(
            f"{label} bytes are unavailable for terminal classification"
        ) from error
    if retained_raw == expected_raw:
        return True, retained_raw
    if (
        len(retained_raw) < len(expected_raw)
        and expected_raw.startswith(retained_raw)
    ):
        return False, retained_raw
    raise OuterReceiptPublicationUncertain(
        f"{label} bytes are neither exact nor a strict canonical prefix"
    )


def _require_bound_publication_inventory(
    store: DurableArtifactStore,
    expected_names: frozenset[str],
    *,
    phase: str,
    name: str,
    classified_raw: bytes,
    observed_exact: bool,
    label: str,
) -> None:
    allow_partial_names = (
        frozenset() if observed_exact else frozenset({name})
    )
    try:
        rows = store.require_inventory(
            expected_names,
            phase=phase,
            allow_partial_names=allow_partial_names,
        )
    except BaseException as error:
        raise OuterReceiptPublicationUncertain(
            f"{label} inventory is unavailable before terminal publication"
        ) from error
    expected_row = {
        "name": name,
        "byte_count": len(classified_raw),
        "sha256": hashlib.sha256(classified_raw).hexdigest(),
        "partial_allowed": not observed_exact,
    }
    matching_rows = [row for row in rows if row["name"] == name]
    if matching_rows != [expected_row]:
        raise OuterReceiptPublicationUncertain(
            f"{label} bytes changed after terminal classification"
        )
    try:
        final_raw = store.read_exact(name, allow_empty=True)
    except BaseException as error:
        raise OuterReceiptPublicationUncertain(
            f"{label} final bytes are unavailable before terminal publication"
        ) from error
    if final_raw != classified_raw:
        raise OuterReceiptPublicationUncertain(
            f"{label} bytes changed after bound inventory readback"
        )


def _validate_outer_receipt_failure_publication_semantics(
    failure: Mapping[str, Any],
    *,
    reason: str,
    receipt_raw: bytes,
    retained_receipt_raw: bytes,
) -> None:
    stage = failure["launch_receipt_publication_stage_class"]
    completed = failure["launch_receipt_publication_completion_claim"]
    observed_exact = failure["launch_receipt_observed_exact"]
    recovery_error = _validate_error_fact(
        failure["launch_receipt_recovery_error"], required=False
    )
    recovery_raw_byte_count = failure[
        "launch_receipt_recovery_raw_byte_count"
    ]
    recovery_raw_sha256 = failure["launch_receipt_recovery_raw_sha256"]
    remaining_after = failure[
        "remaining_after_launch_receipt_publication_ns"
    ]
    decision_reasons = {
        "OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_FAILED",
        "OUTER_SUCCESS_SEAL_PUBLICATION_FAILED_BEFORE_O_EXCL",
        "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED",
    }
    if reason in decision_reasons:
        verified_ns = failure["launch_receipt_verified_monotonic_ns"]
        deadline_ns = failure["deadline_contract"][
            "formal_deadline_monotonic_ns"
        ]
        if (
            stage != OUTER_RECEIPT_DECISION_STAGE
            or completed is not True
            or observed_exact is not True
            or recovery_raw_byte_count is not None
            or recovery_raw_sha256 is not None
            or any(value is not None for value in recovery_error.values())
            or type(remaining_after) is not int
            or failure["launch_receipt_decision_stage"]
            != OUTER_RECEIPT_DECISION_STAGE
            or type(verified_ns) is not int
            or failure["launch_receipt_raw_sha256"]
            != hashlib.sha256(receipt_raw).hexdigest()
            or remaining_after != deadline_ns - verified_ns
            or remaining_after
            > failure["deadline_contract"][
                "remaining_before_terminal_publication_ns"
            ]
        ):
            _fail("outer receipt decision facts changed")
        if reason == "OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_FAILED":
            expected_error = _error_fact(
                _outer_receipt_postpublication_deadline_error()
            )
            expected_components = _build_outer_failure_components(
                deadline_gate_error=(
                    _outer_receipt_postpublication_deadline_error()
                )
            )
            if (
                remaining_after > 0
                or failure["launch_error"] != expected_error
                or failure["failure_components"] != expected_components
            ):
                _fail("outer receipt postpublication deadline facts changed")
        elif remaining_after <= 0:
            _fail("outer success-seal failure lacks a positive receipt decision")
        return
    if reason != "OUTER_RECEIPT_DURABILITY_RECOVERY_FAILED":
        _fail("receipt ownership used a non-receipt failure reason")
    if (
        recovery_raw_byte_count != len(retained_receipt_raw)
        or recovery_raw_sha256
        != hashlib.sha256(retained_receipt_raw).hexdigest()
    ):
        _fail("outer receipt recovery raw identity changed")
    if (
        remaining_after is not None
        or failure["launch_receipt_decision_stage"] is not None
        or failure["launch_receipt_verified_monotonic_ns"] is not None
        or failure["launch_receipt_raw_sha256"] is not None
        or not _error_fact_present(recovery_error)
        or failure["launch_error"] != recovery_error
    ):
        _fail("outer receipt recovery error or timeline changed")
    expected_stage = (
        OUTER_EXACT_BYTES_RECOVERY_STAGE
        if observed_exact
        else OUTER_STRICT_PREFIX_RECOVERY_STAGE
    )
    if stage != expected_stage or completed is not None:
        _fail("outer receipt recovery stage class or completion claim changed")


def _validate_outer_success_seal_failure_semantics(
    failure: Mapping[str, Any],
    *,
    reason: str,
    retained_seal_raw: bytes | None,
) -> None:
    path_created = failure["launch_success_seal_path_created"]
    completed = failure["launch_success_seal_publication_completion_claim"]
    stage = failure["launch_success_seal_publication_stage_class"]
    observed_exact = failure["launch_success_seal_observed_exact"]
    recovery_error = _validate_error_fact(
        failure["launch_success_seal_recovery_error"], required=False
    )
    recovery_raw_byte_count = failure[
        "launch_success_seal_recovery_raw_byte_count"
    ]
    recovery_raw_sha256 = failure[
        "launch_success_seal_recovery_raw_sha256"
    ]
    if reason == "OUTER_SUCCESS_SEAL_PUBLICATION_FAILED_BEFORE_O_EXCL":
        if (
            path_created is not False
            or completed is not False
            or stage is not None
            or observed_exact is not False
            or recovery_raw_byte_count is not None
            or recovery_raw_sha256 is not None
            or any(value is not None for value in recovery_error.values())
            or failure["launch_error"]["error_type"] is None
        ):
            _fail("pre-O_EXCL success-seal failure facts changed")
        return
    if reason != "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED":
        _fail("success-seal ownership used an unrelated failure reason")
    if (
        retained_seal_raw is None
        or recovery_raw_byte_count != len(retained_seal_raw)
        or recovery_raw_sha256
        != hashlib.sha256(retained_seal_raw).hexdigest()
    ):
        _fail("outer success-seal recovery raw identity changed")
    if (
        path_created is not True
        or completed is not None
        or observed_exact is not False
        or stage != OUTER_STRICT_PREFIX_RECOVERY_STAGE
        or not _error_fact_present(recovery_error)
        or failure["launch_error"] != recovery_error
    ):
        _fail("partial success-seal recovery facts changed")


def _validate_bounded_process_result(
    value: Any, *, expected_argv: tuple[str, ...]
) -> BoundedProcessResult:
    if (
        type(value) is not BoundedProcessResult
        or value.argv != expected_argv
        or type(value.returncode) is not int
        or type(value.stdout) is not bytes
        or len(value.stdout) > MAX_SUBPROCESS_STDOUT_BYTES
        or type(value.stderr) is not bytes
        or len(value.stderr) > MAX_SUBPROCESS_STDERR_BYTES
        or type(value.timed_out) is not bool
        or type(value.output_limit_exceeded) is not bool
    ):
        _fail("subprocess adapter returned a malformed bounded result")
    return value


def _validate_outer_launch_failure_state_impl(
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    *,
    recover_prepare_receipt_durability: bool = True,
) -> dict[str, Any]:
    if type(recover_prepare_receipt_durability) is not bool:
        _fail("outer failure prepare durability policy changed")
    names = store.inventory_names(phase="OUTER_FAILURE_AUTHORITY")
    legal = {
        _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME, OUTER_LAUNCH_FAILURE_NAME),
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            OUTER_LAUNCH_FAILURE_NAME,
        ),
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_FAILURE_NAME,
        ),
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            FAILURE_NAME,
            OUTER_LAUNCH_FAILURE_NAME,
        ),
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
            OUTER_LAUNCH_FAILURE_NAME,
        ),
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
            OUTER_LAUNCH_SUCCESS_SEAL_NAME,
            OUTER_LAUNCH_FAILURE_NAME,
        ),
    }
    if names not in legal:
        raise ForeignArtifactError("outer LAUNCH_FAILURE inventory changed")
    partial_capable_names = frozenset(
        names
        & {
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            FAILURE_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
            OUTER_LAUNCH_SUCCESS_SEAL_NAME,
        }
    )
    bound_rows = store.require_inventory(
        names,
        phase="OUTER_FAILURE_AUTHORITY_BOUND",
        allow_partial_names=partial_capable_names,
    )
    validate_prepared_authority(
        authority,
        external_root_raw,
        artifact_store=store,
        recover_prepare_receipt_durability=(
            recover_prepare_receipt_durability
        ),
    )
    outer_attempt = build_outer_launch_attempt_document(
        authority, external_root_raw
    )
    expected_outer_raw = canonical_json_bytes(outer_attempt)
    retained_outer_raw = store.read_exact(
        OUTER_LAUNCH_ATTEMPT_NAME, allow_empty=True
    )
    outer_attempt_exact = retained_outer_raw == expected_outer_raw
    if retained_outer_raw != expected_outer_raw and not expected_outer_raw.startswith(
        retained_outer_raw
    ):
        _fail("failure-state outer ATTEMPT bytes changed")
    failure_raw = store.read_exact(OUTER_LAUNCH_FAILURE_NAME)
    failure = validate_outer_launch_failure_document(
        loads_canonical_json(failure_raw),
        outer_attempt=outer_attempt,
        authority=authority,
    )
    if canonical_json_bytes(failure) != failure_raw:
        _fail("outer LAUNCH_FAILURE bytes are not canonical exact")
    if (
        failure["launch_attempt_recovery_raw_byte_count"]
        != len(retained_outer_raw)
        or failure["launch_attempt_recovery_raw_sha256"]
        != hashlib.sha256(retained_outer_raw).hexdigest()
    ):
        _fail("outer LAUNCH_ATTEMPT recovery raw identity changed")
    if failure["launch_attempt_observed_exact"] is not outer_attempt_exact:
        _fail("outer LAUNCH_ATTEMPT exactness fact changed")
    receipt_present = OUTER_LAUNCH_RECEIPT_NAME in names
    if receipt_present != failure["launch_receipt_path_created"]:
        _fail("outer failure receipt fact disagrees with inventory")
    seal_present = OUTER_LAUNCH_SUCCESS_SEAL_NAME in names
    if seal_present != failure["launch_success_seal_path_created"]:
        _fail("outer failure success-seal fact disagrees with inventory")
    if failure["inventory_before_launch_failure"] != sorted(
        names - {OUTER_LAUNCH_FAILURE_NAME}
    ):
        if (
            outer_attempt_exact
            and failure["deadline_contract"]["remaining_after_process_ns"]
            is None
        ):
            _fail("pre-process outer failure acquired a later inner artifact")
        _fail("outer failure prepublication inventory changed")
    reason = failure["failure_reason"]
    deadline_contract = failure["deadline_contract"]
    result = _outer_failure_result(failure, outer_attempt)
    optional_deadline_fields = (
        "remaining_after_attempt_publication_ns",
        "remaining_after_process_ns",
        "post_absence_deadline_monotonic_ns",
        "remaining_after_post_absence_ns",
        "remaining_after_inner_observation_ns",
        "remaining_before_terminal_publication_ns",
    )
    if (
        outer_attempt_exact
        and deadline_contract["remaining_after_process_ns"] is None
        and names
        != _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME, OUTER_LAUNCH_FAILURE_NAME
        )
    ):
        _fail("pre-process outer failure acquired a later inner artifact")
    if reason == "LAUNCH_ATTEMPT_PUBLICATION_FAILED":
        if (
            names
            != _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME, OUTER_LAUNCH_FAILURE_NAME
            )
            or receipt_present
            or result is not None
            or failure["inner_observation"] is not None
            or failure["postlaunch_absence"] is not None
            or failure["launch_error"]["error_type"] is None
            or not _outer_failure_components_are_empty(failure)
            or any(
                deadline_contract[field] is not None
                for field in optional_deadline_fields
            )
        ):
            _fail("outer ATTEMPT publication failure semantics changed")
    elif not outer_attempt_exact:
        _fail("partial outer ATTEMPT is not its exact publication failure")
    elif reason == "AFTER_ATTEMPT_DEADLINE_GATE_FAILED":
        expected_gate_error = _error_fact(
            OSError(
                errno.ETIMEDOUT,
                "durable LAUNCH_ATTEMPT left insufficient "
                "process/absence/closure time",
            )
        )
        if (
            names
            != _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME, OUTER_LAUNCH_FAILURE_NAME
            )
            or receipt_present
            or result is not None
            or failure["inner_observation"] is not None
            or failure["postlaunch_absence"] is not None
            or failure["launch_error"] != expected_gate_error
            or not _outer_failure_components_are_empty(failure)
            or type(
                deadline_contract["remaining_after_attempt_publication_ns"]
            )
            is not int
            or deadline_contract["remaining_after_attempt_publication_ns"]
            > OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS
            * 1_000_000_000
            or any(
                deadline_contract[field] is not None
                for field in (
                    "remaining_after_process_ns",
                    "post_absence_deadline_monotonic_ns",
                    "remaining_after_post_absence_ns",
                    "remaining_after_inner_observation_ns",
                )
            )
            or type(
                deadline_contract["remaining_before_terminal_publication_ns"]
            )
            is not int
        ):
            _fail("after-ATTEMPT deadline failure semantics changed")
    elif reason == "SYSTEMD_INVOCATION_VALIDATION_FAILED":
        if (
            names
            != _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME, OUTER_LAUNCH_FAILURE_NAME
            )
            or receipt_present
            or result is not None
            or failure["inner_observation"] is not None
            or failure["postlaunch_absence"] is not None
            or failure["launch_error"]["error_type"] is None
            or not _outer_failure_components_are_empty(failure)
            or type(
                deadline_contract["remaining_after_attempt_publication_ns"]
            )
            is not int
            or deadline_contract["remaining_after_attempt_publication_ns"]
            <= OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS
            * 1_000_000_000
            or any(
                deadline_contract[field] is not None
                for field in (
                    "remaining_after_process_ns",
                    "post_absence_deadline_monotonic_ns",
                    "remaining_after_post_absence_ns",
                    "remaining_after_inner_observation_ns",
                )
            )
            or type(
                deadline_contract["remaining_before_terminal_publication_ns"]
            )
            is not int
        ):
            _fail("systemd invocation validation failure semantics changed")
    elif reason in {
        "LAUNCH_RECEIPT_PUBLICATION_FAILED_BEFORE_O_EXCL",
        "OUTER_RECEIPT_DURABILITY_RECOVERY_FAILED",
        "OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_FAILED",
        "OUTER_SUCCESS_SEAL_PUBLICATION_FAILED_BEFORE_O_EXCL",
        "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED",
    }:
        expected_receipt_present = (
            reason
            in {
                "OUTER_RECEIPT_DURABILITY_RECOVERY_FAILED",
                "OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_FAILED",
                "OUTER_SUCCESS_SEAL_PUBLICATION_FAILED_BEFORE_O_EXCL",
                "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED",
            }
        )
        expected_seal_present = (
            reason == "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED"
        )
        expected_components = _build_outer_failure_components(
            deadline_gate_error=(
                _outer_receipt_postpublication_deadline_error()
                if reason
                == "OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_FAILED"
                else None
            )
        )
        expected_inventory = _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            *(
                (OUTER_LAUNCH_RECEIPT_NAME,)
                if expected_receipt_present
                else ()
            ),
            *(
                (OUTER_LAUNCH_SUCCESS_SEAL_NAME,)
                if expected_seal_present
                else ()
            ),
            OUTER_LAUNCH_FAILURE_NAME,
        )
        if (
            names != expected_inventory
            or receipt_present is not expected_receipt_present
            or seal_present is not expected_seal_present
            or failure["launch_error"]["error_type"] is None
            or failure["failure_components"] != expected_components
        ):
            _fail("outer receipt publication failure timeline changed")
        inner, inner_terminal_raw = observe_inner_launch_state(
            store,
            authority,
            external_root_raw,
            outer_terminal_names=(
                frozenset(
                    {
                        OUTER_LAUNCH_RECEIPT_NAME,
                        *(
                            (OUTER_LAUNCH_SUCCESS_SEAL_NAME,)
                            if expected_seal_present
                            else ()
                        ),
                        OUTER_LAUNCH_FAILURE_NAME,
                    }
                )
                if expected_receipt_present
                else frozenset({OUTER_LAUNCH_FAILURE_NAME})
            ),
            recover_receipt_durability=False,
            recover_prepare_receipt_durability=(
                recover_prepare_receipt_durability
            ),
        )
        if inner_terminal_raw is None:
            _fail("outer receipt publication failure lacks inner bytes")
        expected_receipt = _reconstruct_outer_receipt_from_failure(
            failure,
            outer_attempt=outer_attempt,
            observed_inner=inner,
            inner_terminal_raw=inner_terminal_raw,
            authority=authority,
        )
        if expected_receipt_present:
            receipt_raw = store.read_exact(
                OUTER_LAUNCH_RECEIPT_NAME,
                allow_empty=not failure["launch_receipt_observed_exact"],
            )
            expected_receipt_raw = canonical_json_bytes(expected_receipt)
            _validate_outer_receipt_failure_publication_semantics(
                failure,
                reason=reason,
                receipt_raw=expected_receipt_raw,
                retained_receipt_raw=receipt_raw,
            )
            if failure["launch_receipt_observed_exact"]:
                if receipt_raw != expected_receipt_raw:
                    _fail("exact outer receipt recovery bytes changed")
            elif (
                len(receipt_raw) >= len(expected_receipt_raw)
                or not expected_receipt_raw.startswith(receipt_raw)
            ):
                _fail("partial outer receipt is not a strict canonical prefix")
        if reason in {
            "OUTER_SUCCESS_SEAL_PUBLICATION_FAILED_BEFORE_O_EXCL",
            "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED",
        }:
            expected_seal = _build_outer_launch_success_seal(
                outer_attempt,
                expected_receipt,
                canonical_json_bytes(expected_receipt),
                verified_monotonic_ns=failure[
                    "launch_receipt_verified_monotonic_ns"
                ],
                remaining_after_publication_ns=failure[
                    "remaining_after_launch_receipt_publication_ns"
                ],
            )
            seal_raw = None
            if expected_seal_present:
                seal_raw = store.read_exact(
                    OUTER_LAUNCH_SUCCESS_SEAL_NAME,
                    allow_empty=not failure[
                        "launch_success_seal_observed_exact"
                    ],
                )
            _validate_outer_success_seal_failure_semantics(
                failure,
                reason=reason,
                retained_seal_raw=seal_raw,
            )
            if seal_raw is not None:
                expected_seal_raw = canonical_json_bytes(expected_seal)
                if failure["launch_success_seal_observed_exact"]:
                    if seal_raw != expected_seal_raw:
                        _fail("exact outer success-seal bytes changed")
                elif (
                    len(seal_raw) >= len(expected_seal_raw)
                    or not expected_seal_raw.startswith(seal_raw)
                ):
                    _fail(
                        "partial outer success seal is not a strict canonical prefix"
                    )
    else:
        if reason in OUTER_SPECIAL_FAILURE_REASONS or receipt_present:
            _fail("outer failure special reason or receipt ownership changed")
        process_recorded = (
            deadline_contract["remaining_after_process_ns"] is not None
        )
        observation_recorded = (
            deadline_contract["remaining_after_inner_observation_ns"]
            is not None
        )
        components = _validate_outer_failure_components(
            failure["failure_components"]
        )
        process_error_present = _error_fact_present(
            components["process_adapter_error"]
        )
        inner_observation_failed = _error_fact_present(
            components["inner_observation_error"]
        )
        if not process_recorded:
            _fail("ordinary outer failure lacks process completion")
        if result is None and not process_error_present:
            _fail("outer failure lost its process-result acquisition error")
        if inner_observation_failed and (
            not observation_recorded
            or failure["inner_observation"] is not None
        ):
            _fail("outer failure inner-observation error state changed")
        if (
            not observation_recorded
            and failure["inner_observation"] is not None
        ):
            _fail("pre-observation outer failure invented an inner observation")
        observed_terminal_raw: bytes | None = None
        if observation_recorded:
            try:
                observed_inner, observed_terminal_raw = observe_inner_launch_state(
                    store,
                    authority,
                    external_root_raw,
                    outer_terminal_names=frozenset(
                        {OUTER_LAUNCH_FAILURE_NAME}
                    ),
                    recover_receipt_durability=False,
                    recover_prepare_receipt_durability=(
                        recover_prepare_receipt_durability
                    ),
                )
            except BaseException:
                if not inner_observation_failed:
                    _fail(
                        "outer failure retained an unreplayable inner observation"
                    )
            else:
                if not inner_observation_failed:
                    expected_inner = observed_inner
                    retained_inner = failure["inner_observation"]
                    if (
                        retained_inner is not None
                        and retained_inner.get("state")
                        == "RECEIPT_UNCERTAIN"
                        and observed_inner["state"] == "RECEIPT"
                    ):
                        expected_inner = {
                            **observed_inner,
                            "state": "RECEIPT_UNCERTAIN",
                            "inner_terminal_id": None,
                        }
                    if retained_inner != expected_inner:
                        _fail(
                            "outer failure inner observation changed on replay"
                        )
        expected_reason = _derive_ordinary_outer_failure_reason(
            result=result,
            inner=failure["inner_observation"],
            inner_terminal_raw=(
                None if inner_observation_failed else observed_terminal_raw
            ),
            postlaunch_absence=failure["postlaunch_absence"],
            deadline_contract=deadline_contract,
            failure_components=components,
            launch_error=failure["launch_error"],
        )
        if reason != expected_reason:
            _fail("outer ordinary failure reason changed")
    final_rows = store.require_inventory(
        names,
        phase="OUTER_FAILURE_AUTHORITY_POST",
        allow_partial_names=partial_capable_names,
    )
    if final_rows != bound_rows:
        raise AuthorityError(
            "outer failure artifact bytes changed during validation"
        )
    reread_rows, _final_raw_by_name = _read_inventory_byte_snapshot(
        store,
        names,
        allow_partial_names=partial_capable_names,
    )
    if reread_rows != final_rows:
        raise AuthorityError(
            "outer failure artifact bytes changed after final inventory rows"
        )
    return failure


def validate_outer_launch_failure_state(
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    return _validate_outer_launch_failure_state_impl(
        store, authority, external_root_raw
    )


def _recover_retained_outer_launch_failure_state(
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    try:
        failure_raw = store.read_exact(OUTER_LAUNCH_FAILURE_NAME)
    except BaseException as error:
        raise OuterLaunchFailurePublicationUncertain(
            "retained outer LAUNCH_FAILURE bytes are unavailable"
        ) from error
    try:
        loads_canonical_json(failure_raw)
    except AuthorityError as error:
        raise OuterLaunchFailurePublicationUncertain(
            "retained outer LAUNCH_FAILURE is not canonical exact"
        ) from error
    retained = validate_outer_launch_failure_state(
        store, authority, external_root_raw
    )
    try:
        store.stabilize_exact(OUTER_LAUNCH_FAILURE_NAME, failure_raw)
    except BaseException as error:
        raise OuterLaunchFailurePublicationUncertain(
            "exact outer LAUNCH_FAILURE failed durability recovery"
        ) from error
    recovered = validate_outer_launch_failure_state(
        store, authority, external_root_raw
    )
    if recovered != retained:
        _fail("outer LAUNCH_FAILURE changed across durability recovery")
    return recovered


def _validate_published_outer_launch_failure_state(
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    failure: Mapping[str, Any],
) -> dict[str, Any]:
    """Retry only validation of one already durable, exact failure publication."""

    expected = dict(failure)

    def validate_once() -> dict[str, Any]:
        retained = validate_outer_launch_failure_state(
            store, authority, external_root_raw
        )
        if retained != expected:
            _fail("published outer LAUNCH_FAILURE changed during validation")
        return retained

    try:
        return validate_once()
    except BaseException:
        try:
            return validate_once()
        except BaseException as recovery_error:
            raise OuterLaunchFailurePublicationUncertain(
                "durable outer LAUNCH_FAILURE failed postpublication validation "
                "recovery"
            ) from recovery_error


class _OuterLaunchFailureCandidateStore:
    """Read-only view that joins one not-yet-published terminal candidate."""

    def __init__(
        self, store: DurableArtifactStore, failure_raw: bytes
    ) -> None:
        self._store = store
        self._failure_raw = failure_raw
        self.root = store.root
        self.root_fd = store.root_fd

    def inventory_names(self, *, phase: str) -> frozenset[str]:
        names = self._store.inventory_names(phase=phase)
        if OUTER_LAUNCH_FAILURE_NAME in names:
            raise ForeignArtifactError(
                "outer LAUNCH_FAILURE appeared before candidate O_EXCL"
            )
        return frozenset({*names, OUTER_LAUNCH_FAILURE_NAME})

    def read_exact(
        self,
        name: str,
        *,
        byte_cap: int = MAX_ARTIFACT_BYTES,
        allow_empty: bool = False,
    ) -> bytes:
        if name == OUTER_LAUNCH_FAILURE_NAME:
            if allow_empty or byte_cap != MAX_ARTIFACT_BYTES:
                _fail("outer failure candidate read contract changed")
            return self._failure_raw
        if byte_cap == MAX_ARTIFACT_BYTES:
            return self._store.read_exact(name, allow_empty=allow_empty)
        return self._store.read_exact(
            name, byte_cap=byte_cap, allow_empty=allow_empty
        )

    def require_inventory(
        self,
        expected_names: frozenset[str],
        *,
        phase: str,
        allow_partial_names: frozenset[str] = frozenset(),
    ) -> tuple[dict[str, Any], ...]:
        if (
            OUTER_LAUNCH_FAILURE_NAME not in expected_names
            or OUTER_LAUNCH_FAILURE_NAME in allow_partial_names
        ):
            _fail("outer failure candidate inventory contract changed")
        physical_names = frozenset(
            expected_names - {OUTER_LAUNCH_FAILURE_NAME}
        )
        physical_partial_names = frozenset(
            allow_partial_names - {OUTER_LAUNCH_FAILURE_NAME}
        )
        rows = list(
            self._store.require_inventory(
                physical_names,
                phase=phase,
                allow_partial_names=physical_partial_names,
            )
        )
        rows.append(
            {
                "name": OUTER_LAUNCH_FAILURE_NAME,
                "byte_count": len(self._failure_raw),
                "sha256": hashlib.sha256(self._failure_raw).hexdigest(),
                "partial_allowed": False,
            }
        )
        return tuple(sorted(rows, key=lambda row: row["name"]))

    def stabilize_exact(self, name: str, raw: bytes) -> None:
        if name == OUTER_LAUNCH_FAILURE_NAME:
            _fail("outer failure candidate view is read-only")
        self._store.stabilize_exact(name, raw)


def _publish_outer_launch_failure_terminal(
    *,
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    failure: Mapping[str, Any],
    cause: BaseException | None,
) -> NoReturn:
    failure_raw = canonical_json_bytes(failure)
    publication = PublicationOwnershipToken(OUTER_LAUNCH_FAILURE_NAME)

    def validate_live_state_before_open() -> None:
        candidate_store = _OuterLaunchFailureCandidateStore(
            store, failure_raw
        )
        try:
            retained = _validate_outer_launch_failure_state_impl(
                candidate_store,
                authority,
                external_root_raw,
                recover_prepare_receipt_durability=False,
            )
        except BaseException as validation_error:
            raise OuterLaunchFailurePublicationUncertain(
                "outer failure live state changed before LAUNCH_FAILURE "
                "O_EXCL"
            ) from validation_error
        if retained != dict(failure):
            raise OuterLaunchFailurePublicationUncertain(
                "outer failure candidate changed during pre-O_EXCL validation"
            )

    try:
        store.write_once(
            OUTER_LAUNCH_FAILURE_NAME,
            failure_raw,
            token=publication,
            pre_open=validate_live_state_before_open,
        )
    except OuterLaunchFailurePublicationUncertain:
        raise
    except FileExistsError as publication_error:
        raise OuterLaunchFailurePublicationUncertain(
            "outer LAUNCH_FAILURE O_EXCL ownership was lost"
        ) from publication_error
    except BaseException as publication_error:
        if not publication.path_created:
            raise OuterLaunchFailurePublicationUncertain(
                "outer LAUNCH_FAILURE publication failed before O_EXCL"
            ) from publication_error
        try:
            retained_raw = store.read_exact(
                OUTER_LAUNCH_FAILURE_NAME, allow_empty=True
            )
        except BaseException as recovery_error:
            raise OuterLaunchFailurePublicationUncertain(
                "owned outer LAUNCH_FAILURE bytes are unavailable"
            ) from recovery_error
        if retained_raw != failure_raw:
            if len(retained_raw) < len(failure_raw) and failure_raw.startswith(
                retained_raw
            ):
                message = (
                    "owned outer LAUNCH_FAILURE is only a canonical prefix"
                )
            else:
                message = "owned outer LAUNCH_FAILURE bytes are not exact"
            raise OuterLaunchFailurePublicationUncertain(
                message
            ) from publication_error
        try:
            store.stabilize_exact(OUTER_LAUNCH_FAILURE_NAME, failure_raw)
        except BaseException as recovery_error:
            raise OuterLaunchFailurePublicationUncertain(
                "exact outer LAUNCH_FAILURE failed durability recovery"
            ) from recovery_error
        retained = _validate_published_outer_launch_failure_state(
            store, authority, external_root_raw, failure
        )
        raise OuterLaunchFailure(retained) from publication_error
    retained = _validate_published_outer_launch_failure_state(
        store, authority, external_root_raw, failure
    )
    raise OuterLaunchFailure(retained) from cause


def _publish_outer_receipt_recovery_failure(
    *,
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    outer_attempt: Mapping[str, Any],
    result: BoundedProcessResult,
    inner: Mapping[str, Any],
    prelaunch_absence: Mapping[str, Any],
    postlaunch_absence: Mapping[str, Any],
    deadline_contract: Mapping[str, Any],
    receipt_publication: PublicationOwnershipToken,
    receipt_observed_exact: bool,
    receipt_retained_raw: bytes,
    recovery_error: BaseException,
) -> NoReturn:
    failure = _build_outer_launch_failure(
        outer_attempt,
        result=result,
        inner=inner,
        prelaunch_absence=prelaunch_absence,
        postlaunch_absence=postlaunch_absence,
        error=recovery_error,
        reason="OUTER_RECEIPT_DURABILITY_RECOVERY_FAILED",
        deadline_contract=deadline_contract,
        inventory_before_launch_failure=(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
        ),
        receipt_publication=receipt_publication,
        receipt_publication_stage=(
            OUTER_EXACT_BYTES_RECOVERY_STAGE
            if receipt_observed_exact
            else OUTER_STRICT_PREFIX_RECOVERY_STAGE
        ),
        receipt_observed_exact=receipt_observed_exact,
        receipt_recovery_raw=receipt_retained_raw,
        receipt_recovery_error=recovery_error,
    )
    before = _root_inventory(
        OUTER_LAUNCH_ATTEMPT_NAME,
        ATTEMPT_NAME,
        RECEIPT_NAME,
        OUTER_LAUNCH_RECEIPT_NAME,
    )
    _require_bound_publication_inventory(
        store,
        before,
        phase="OUTER_RECEIPT_RECOVERY_BEFORE_FAILURE",
        name=OUTER_LAUNCH_RECEIPT_NAME,
        classified_raw=receipt_retained_raw,
        observed_exact=receipt_observed_exact,
        label="outer LAUNCH_RECEIPT",
    )
    _publish_outer_launch_failure_terminal(
        store=store,
        authority=authority,
        external_root_raw=external_root_raw,
        failure=failure,
        cause=recovery_error,
    )


def _publish_outer_receipt_postpublication_deadline_failure(
    *,
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    outer_attempt: Mapping[str, Any],
    result: BoundedProcessResult,
    inner: Mapping[str, Any],
    prelaunch_absence: Mapping[str, Any],
    postlaunch_absence: Mapping[str, Any],
    deadline_contract: Mapping[str, Any],
    receipt_publication: PublicationOwnershipToken,
    receipt_raw: bytes,
    receipt_verified_monotonic_ns: int,
    remaining_after_publication_ns: int,
) -> NoReturn:
    deadline_error = _outer_receipt_postpublication_deadline_error()
    failure = _build_outer_launch_failure(
        outer_attempt,
        result=result,
        inner=inner,
        prelaunch_absence=prelaunch_absence,
        postlaunch_absence=postlaunch_absence,
        error=deadline_error,
        reason="OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_FAILED",
        deadline_contract=deadline_contract,
        inventory_before_launch_failure=(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
        ),
        receipt_publication=receipt_publication,
        receipt_publication_stage=OUTER_RECEIPT_DECISION_STAGE,
        receipt_observed_exact=True,
        receipt_decision_stage=OUTER_RECEIPT_DECISION_STAGE,
        receipt_verified_monotonic_ns=receipt_verified_monotonic_ns,
        receipt_raw_sha256=hashlib.sha256(receipt_raw).hexdigest(),
        remaining_after_launch_receipt_publication_ns=(
            remaining_after_publication_ns
        ),
        deadline_gate_error=deadline_error,
    )
    store.require_inventory(
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
        ),
        phase="OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_BEFORE_FAILURE",
    )
    _publish_outer_launch_failure_terminal(
        store=store,
        authority=authority,
        external_root_raw=external_root_raw,
        failure=failure,
        cause=deadline_error,
    )


def _publish_outer_success_seal_failure(
    *,
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    outer_attempt: Mapping[str, Any],
    result: BoundedProcessResult,
    inner: Mapping[str, Any],
    prelaunch_absence: Mapping[str, Any],
    postlaunch_absence: Mapping[str, Any],
    deadline_contract: Mapping[str, Any],
    receipt_publication: PublicationOwnershipToken,
    receipt_raw: bytes,
    receipt_verified_monotonic_ns: int,
    remaining_after_publication_ns: int,
    seal_publication: PublicationOwnershipToken | None,
    seal_observed_exact: bool,
    seal_retained_raw: bytes | None,
    error: BaseException,
    recovery_error: BaseException | None,
) -> NoReturn:
    seal_created = seal_publication is not None and seal_publication.path_created
    reason = (
        "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED"
        if seal_created
        else "OUTER_SUCCESS_SEAL_PUBLICATION_FAILED_BEFORE_O_EXCL"
    )
    primary_error = recovery_error if seal_created else error
    if primary_error is None:
        _fail("outer success-seal failure lacks its primary error")
    inventory_before = _root_inventory(
        OUTER_LAUNCH_ATTEMPT_NAME,
        ATTEMPT_NAME,
        RECEIPT_NAME,
        OUTER_LAUNCH_RECEIPT_NAME,
        *((OUTER_LAUNCH_SUCCESS_SEAL_NAME,) if seal_created else ()),
    )
    failure = _build_outer_launch_failure(
        outer_attempt,
        result=result,
        inner=inner,
        prelaunch_absence=prelaunch_absence,
        postlaunch_absence=postlaunch_absence,
        error=primary_error,
        reason=reason,
        deadline_contract=deadline_contract,
        inventory_before_launch_failure=tuple(inventory_before),
        receipt_publication=receipt_publication,
        receipt_publication_stage=OUTER_RECEIPT_DECISION_STAGE,
        receipt_observed_exact=True,
        receipt_decision_stage=OUTER_RECEIPT_DECISION_STAGE,
        receipt_verified_monotonic_ns=receipt_verified_monotonic_ns,
        receipt_raw_sha256=hashlib.sha256(receipt_raw).hexdigest(),
        remaining_after_launch_receipt_publication_ns=(
            remaining_after_publication_ns
        ),
        success_seal_publication=seal_publication,
        success_seal_publication_stage=(
            OUTER_STRICT_PREFIX_RECOVERY_STAGE if seal_created else None
        ),
        success_seal_observed_exact=seal_observed_exact,
        success_seal_recovery_raw=(
            seal_retained_raw if seal_created else None
        ),
        success_seal_recovery_error=recovery_error,
    )
    if seal_created:
        if seal_retained_raw is None:
            _fail("owned success-seal failure lacks classified retained bytes")
        _require_bound_publication_inventory(
            store,
            inventory_before,
            phase="OUTER_SUCCESS_SEAL_BEFORE_FAILURE",
            name=OUTER_LAUNCH_SUCCESS_SEAL_NAME,
            classified_raw=seal_retained_raw,
            observed_exact=seal_observed_exact,
            label="outer LAUNCH_SUCCESS_SEAL",
        )
    else:
        if seal_retained_raw is not None:
            _fail("pre-O_EXCL success-seal failure owns retained bytes")
        store.require_inventory(
            inventory_before,
            phase="OUTER_SUCCESS_SEAL_BEFORE_FAILURE",
        )
    _publish_outer_launch_failure_terminal(
        store=store,
        authority=authority,
        external_root_raw=external_root_raw,
        failure=failure,
        cause=primary_error,
    )


def _complete_outer_success_decision(
    *,
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    outer_attempt: Mapping[str, Any],
    receipt: Mapping[str, Any],
    receipt_raw: bytes,
    receipt_publication: PublicationOwnershipToken,
    result: BoundedProcessResult,
    inner: Mapping[str, Any],
    prelaunch_absence: Mapping[str, Any],
    postlaunch_absence: Mapping[str, Any],
    deadline_contract: Mapping[str, Any],
    deadline_ns: int,
    monotonic_ns: Callable[[], int],
) -> dict[str, Any]:
    verified_ns, remaining_ns = _sample_outer_remaining(
        deadline_ns,
        monotonic_ns,
        "outer LAUNCH_RECEIPT exact inventory decision",
    )
    if remaining_ns <= 0:
        _publish_outer_receipt_postpublication_deadline_failure(
            store=store,
            authority=authority,
            external_root_raw=external_root_raw,
            outer_attempt=outer_attempt,
            result=result,
            inner=inner,
            prelaunch_absence=prelaunch_absence,
            postlaunch_absence=postlaunch_absence,
            deadline_contract=deadline_contract,
            receipt_publication=receipt_publication,
            receipt_raw=receipt_raw,
            receipt_verified_monotonic_ns=verified_ns,
            remaining_after_publication_ns=remaining_ns,
        )
    seal = validate_outer_launch_success_seal_document(
        _build_outer_launch_success_seal(
            outer_attempt,
            receipt,
            receipt_raw,
            verified_monotonic_ns=verified_ns,
            remaining_after_publication_ns=remaining_ns,
        ),
        outer_attempt=outer_attempt,
        receipt=receipt,
        receipt_raw=receipt_raw,
    )
    seal_raw = canonical_json_bytes(seal)
    seal_publication = PublicationOwnershipToken(
        OUTER_LAUNCH_SUCCESS_SEAL_NAME
    )
    try:
        store.write_once(
            OUTER_LAUNCH_SUCCESS_SEAL_NAME,
            seal_raw,
            token=seal_publication,
        )
        store.require_inventory(
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                RECEIPT_NAME,
                OUTER_LAUNCH_RECEIPT_NAME,
                OUTER_LAUNCH_SUCCESS_SEAL_NAME,
            ),
            phase="OUTER_LAUNCH_SUCCESS_SEALED",
        )
        retained_seal_raw = store.read_exact(
            OUTER_LAUNCH_SUCCESS_SEAL_NAME
        )
        retained_seal = validate_outer_launch_success_seal_document(
            loads_canonical_json(retained_seal_raw),
            outer_attempt=outer_attempt,
            receipt=receipt,
            receipt_raw=receipt_raw,
        )
        if retained_seal != seal or retained_seal_raw != seal_raw:
            _fail("published outer success seal changed")
        store.require_inventory(
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                RECEIPT_NAME,
                OUTER_LAUNCH_RECEIPT_NAME,
                OUTER_LAUNCH_SUCCESS_SEAL_NAME,
            ),
            phase="OUTER_LAUNCH_SUCCESS_SEAL_VALIDATED",
        )
    except FileExistsError as error:
        raise OuterReceiptPublicationUncertain(
            "unowned LAUNCH_SUCCESS_SEAL path forbids success"
        ) from error
    except BaseException as error:
        if not seal_publication.path_created:
            _publish_outer_success_seal_failure(
                store=store,
                authority=authority,
                external_root_raw=external_root_raw,
                outer_attempt=outer_attempt,
                result=result,
                inner=inner,
                prelaunch_absence=prelaunch_absence,
                postlaunch_absence=postlaunch_absence,
                deadline_contract=deadline_contract,
                receipt_publication=receipt_publication,
                receipt_raw=receipt_raw,
                receipt_verified_monotonic_ns=verified_ns,
                remaining_after_publication_ns=remaining_ns,
                seal_publication=None,
                seal_observed_exact=False,
                seal_retained_raw=None,
                error=error,
                recovery_error=None,
            )
        if seal_publication.completed:
            raise OuterReceiptPublicationUncertain(
                "completed success decision seal failed postpublication "
                "validation"
            ) from error
        seal_exact_validated = False
        try:
            retained_seal_raw = store.read_exact(
                OUTER_LAUNCH_SUCCESS_SEAL_NAME, allow_empty=True
            )
            seal_observed_exact = retained_seal_raw == seal_raw
            if not seal_observed_exact:
                _fail("partial success seal is not exact")
            validate_outer_launch_success_seal_document(
                loads_canonical_json(retained_seal_raw),
                outer_attempt=outer_attempt,
                receipt=receipt,
                receipt_raw=receipt_raw,
            )
            seal_exact_validated = True
            store.stabilize_exact(OUTER_LAUNCH_SUCCESS_SEAL_NAME, seal_raw)
            store.require_inventory(
                _root_inventory(
                    OUTER_LAUNCH_ATTEMPT_NAME,
                    ATTEMPT_NAME,
                    RECEIPT_NAME,
                    OUTER_LAUNCH_RECEIPT_NAME,
                    OUTER_LAUNCH_SUCCESS_SEAL_NAME,
                ),
                phase="OUTER_LAUNCH_SUCCESS_SEAL_RECOVERED",
            )
        except BaseException as recovery_error:
            if seal_exact_validated:
                raise OuterReceiptPublicationUncertain(
                    "exact success decision seal could not complete durability "
                    "recovery"
                ) from recovery_error
            (
                seal_observed_exact,
                seal_retained_raw,
            ) = _classify_retained_publication_bytes(
                store,
                OUTER_LAUNCH_SUCCESS_SEAL_NAME,
                seal_raw,
                label="outer LAUNCH_SUCCESS_SEAL",
            )
            if seal_observed_exact:
                raise OuterReceiptPublicationUncertain(
                    "exact success decision seal appeared after a transient "
                    "recovery read failure"
                ) from recovery_error
            seal_publication_stage = (
                error.stage
                if isinstance(error, DurableWriteError)
                else OUTER_RECEIPT_POST_RETURN_STAGE
            )
            if seal_publication_stage not in {
                "AFTER_OPEN",
                "AFTER_INITIAL_FCHMOD",
            }:
                raise OuterReceiptPublicationUncertain(
                    "strict-prefix success decision seal left its early "
                    "publication stages"
                ) from recovery_error
            _publish_outer_success_seal_failure(
                store=store,
                authority=authority,
                external_root_raw=external_root_raw,
                outer_attempt=outer_attempt,
                result=result,
                inner=inner,
                prelaunch_absence=prelaunch_absence,
                postlaunch_absence=postlaunch_absence,
                deadline_contract=deadline_contract,
                receipt_publication=receipt_publication,
                receipt_raw=receipt_raw,
                receipt_verified_monotonic_ns=verified_ns,
                remaining_after_publication_ns=remaining_ns,
                seal_publication=seal_publication,
                seal_observed_exact=seal_observed_exact,
                seal_retained_raw=seal_retained_raw,
                error=error,
                recovery_error=recovery_error,
            )
    return dict(receipt)


def _publish_outer_launch_failure(
    *,
    store: DurableArtifactStore,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    outer_attempt: Mapping[str, Any],
    result: BoundedProcessResult | None,
    inner: Mapping[str, Any] | None,
    prelaunch_absence: Mapping[str, Any],
    postlaunch_absence: Mapping[str, Any] | None,
    error: BaseException | None,
    reason: str,
    deadline_contract: Mapping[str, Any],
    process_adapter_error: BaseException | None = None,
    deadline_gate_error: BaseException | None = None,
    inner_observation_error: BaseException | None = None,
    postlaunch_absence_error: BaseException | None = None,
) -> NoReturn:
    current_names = store.inventory_names(phase="OUTER_BEFORE_FAILURE")
    legal_before_failure = {
        _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME),
        _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME),
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME, RECEIPT_NAME
        ),
        _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME, FAILURE_NAME
        ),
    }
    if current_names not in legal_before_failure:
        raise ForeignArtifactError("outer failure inventory is not legal")
    failure = _build_outer_launch_failure(
        outer_attempt,
        result=result,
        inner=inner,
        prelaunch_absence=prelaunch_absence,
        postlaunch_absence=postlaunch_absence,
        error=error,
        reason=reason,
        deadline_contract=deadline_contract,
        inventory_before_launch_failure=sorted(current_names),
        process_adapter_error=process_adapter_error,
        deadline_gate_error=deadline_gate_error,
        inner_observation_error=inner_observation_error,
        postlaunch_absence_error=postlaunch_absence_error,
    )
    _publish_outer_launch_failure_terminal(
        store=store,
        authority=authority,
        external_root_raw=external_root_raw,
        failure=failure,
        cause=error,
    )


def run_outer_launch_once(
    *,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    store: DurableArtifactStore,
    process_adapter: SubprocessAdapter,
    absence_observer: OuterAbsenceObserver,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
    formal_process_entry_ns: int | None = None,
    deadline_ns: int | None = None,
) -> dict[str, Any]:
    """Consume the outer identity, launch once, and durably close its outcome."""

    observed_entry_ns = monotonic_ns()
    formal_process_entry_ns = (
        observed_entry_ns
        if formal_process_entry_ns is None
        else formal_process_entry_ns
    )
    deadline_ns = (
        formal_process_entry_ns + FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
        if deadline_ns is None
        else deadline_ns
    )
    if (
        type(formal_process_entry_ns) is not int
        or type(deadline_ns) is not int
        or formal_process_entry_ns > observed_entry_ns
        or deadline_ns - formal_process_entry_ns
        != FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
    ):
        _fail("formal launch absolute deadline contract changed")
    _entry_sample_ns, entry_remaining_ns = _sample_outer_remaining(
        deadline_ns, monotonic_ns, "outer launch entry"
    )
    if entry_remaining_ns <= 0:
        raise OSError(
            errno.ETIMEDOUT,
            "outer launch entry exhausted its absolute deadline",
        )
    authority = validate_external_root_document(authority)
    if loads_canonical_json(external_root_raw) != authority:
        _fail("outer launch authority bytes changed")
    invocation = authority["systemd_invocation_contract"]
    if store.root != Path(invocation["artifact_root"]):
        _fail("outer launch store left its exact artifact root")
    initial_names = store.inventory_names(phase="OUTER_PRELAUNCH_ROOT_EMPTY")
    if initial_names:
        success_inventory = _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
            OUTER_LAUNCH_SUCCESS_SEAL_NAME,
        )
        if initial_names == success_inventory:
            try:
                return _recover_outer_launch_success(
                    store, authority, external_root_raw
                )
            except BaseException as error:
                raise OuterReceiptPublicationUncertain(
                    "retained success seal is not exact enough to authorize "
                    "success"
                ) from error
        receipt_only_inventory = _root_inventory(
            OUTER_LAUNCH_ATTEMPT_NAME,
            ATTEMPT_NAME,
            RECEIPT_NAME,
            OUTER_LAUNCH_RECEIPT_NAME,
        )
        if initial_names == receipt_only_inventory:
            raise OuterReceiptPublicationUncertain(
                "outer receipt lacks its write-once success decision seal"
            )
        retained_closures = {
            _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME),
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME, OUTER_LAUNCH_FAILURE_NAME
            ),
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                OUTER_LAUNCH_FAILURE_NAME,
            ),
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                RECEIPT_NAME,
                OUTER_LAUNCH_FAILURE_NAME,
            ),
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                FAILURE_NAME,
                OUTER_LAUNCH_FAILURE_NAME,
            ),
        }
        retained_closures.add(
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                RECEIPT_NAME,
                OUTER_LAUNCH_RECEIPT_NAME,
                OUTER_LAUNCH_FAILURE_NAME,
            )
        )
        retained_closures.add(
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                RECEIPT_NAME,
                OUTER_LAUNCH_RECEIPT_NAME,
                OUTER_LAUNCH_SUCCESS_SEAL_NAME,
                OUTER_LAUNCH_FAILURE_NAME,
            )
        )
        if initial_names in retained_closures:
            if OUTER_LAUNCH_FAILURE_NAME in initial_names:
                failure = _recover_retained_outer_launch_failure_state(
                    store, authority, external_root_raw
                )
                raise OuterLaunchFailure(failure)
            raise ReplayForbidden("outer preflight identity was already consumed")
        raise ForeignArtifactError(
            f"outer prelaunch inventory is illegal: {sorted(initial_names)!r}"
        )
    store.require_inventory(
        frozenset(), phase="OUTER_PRELAUNCH_ROOT_EMPTY_EXACT"
    )
    validate_prepared_authority(
        authority, external_root_raw, artifact_store=store
    )
    prelaunch_absence = _validate_success_absence_fact(
        absence_observer.observe_absence(authority, deadline_ns=deadline_ns),
        authority,
    )
    outer_attempt_issued_ns, remaining_before_launch_ns = (
        _sample_outer_remaining(
            deadline_ns, monotonic_ns, "outer launch issuance"
        )
    )
    required_after_issuance_ns = (
        OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS * 1_000_000_000
    )
    if remaining_before_launch_ns <= required_after_issuance_ns:
        raise OSError(
            errno.ETIMEDOUT,
            "formal deadline lacks process/cleanup/absence margin",
        )
    outer_attempt = build_outer_launch_attempt_document(
        authority, external_root_raw
    )
    deadline_contract = {
        "formal_process_entry_monotonic_ns": formal_process_entry_ns,
        "formal_deadline_monotonic_ns": deadline_ns,
        "outer_attempt_issued_monotonic_ns": outer_attempt_issued_ns,
        "remaining_before_launch_ns": remaining_before_launch_ns,
        "remaining_after_attempt_publication_ns": None,
        "remaining_after_process_ns": None,
        "post_absence_deadline_monotonic_ns": None,
        "remaining_after_post_absence_ns": None,
        "remaining_after_inner_observation_ns": None,
        "remaining_before_terminal_publication_ns": None,
        **outer_attempt["deadline_budget"],
    }
    deadline_contract = validate_outer_deadline_contract(deadline_contract)
    expected_outer_attempt_raw = canonical_json_bytes(outer_attempt)
    attempt_token = PublicationOwnershipToken(OUTER_LAUNCH_ATTEMPT_NAME)
    try:
        store.write_once(
            OUTER_LAUNCH_ATTEMPT_NAME,
            expected_outer_attempt_raw,
            token=attempt_token,
        )
        store.require_inventory(
            _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME),
            phase="OUTER_LAUNCH_ATTEMPT_PUBLISHED",
        )
    except FileExistsError as error:
        raise ReplayForbidden("outer LAUNCH_ATTEMPT O_EXCL lost") from error
    except BaseException as error:
        if not attempt_token.path_created:
            raise
        try:
            retained_outer_attempt_raw = store.read_exact(
                OUTER_LAUNCH_ATTEMPT_NAME, allow_empty=True
            )
        except BaseException as recovery_error:
            raise AuthorityError(
                "owned outer LAUNCH_ATTEMPT bytes are unavailable for "
                "terminal classification"
            ) from recovery_error
        attempt_observed_exact = (
            retained_outer_attempt_raw == expected_outer_attempt_raw
        )
        if not attempt_observed_exact and not (
            len(retained_outer_attempt_raw) < len(expected_outer_attempt_raw)
            and expected_outer_attempt_raw.startswith(
                retained_outer_attempt_raw
            )
        ):
            raise AuthorityError(
                "owned outer LAUNCH_ATTEMPT bytes are neither exact nor a "
                "strict canonical prefix"
            ) from error
        failure = _build_outer_launch_failure(
            outer_attempt,
            result=None,
            inner=None,
            prelaunch_absence=prelaunch_absence,
            postlaunch_absence=None,
            error=error,
            reason="LAUNCH_ATTEMPT_PUBLICATION_FAILED",
            deadline_contract=deadline_contract,
            inventory_before_launch_failure=(OUTER_LAUNCH_ATTEMPT_NAME,),
            attempt_observed_exact=attempt_observed_exact,
            attempt_recovery_raw=retained_outer_attempt_raw,
        )
        allow_partial_attempt = (
            frozenset()
            if attempt_observed_exact
            else frozenset({OUTER_LAUNCH_ATTEMPT_NAME})
        )
        try:
            attempt_rows = store.require_inventory(
                _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME),
                phase="OUTER_ATTEMPT_RECOVERY_BEFORE_FAILURE",
                allow_partial_names=allow_partial_attempt,
            )
        except BaseException as inventory_error:
            raise AuthorityError(
                "owned outer LAUNCH_ATTEMPT inventory is unavailable before "
                "terminal publication"
            ) from inventory_error
        expected_attempt_row = {
            "name": OUTER_LAUNCH_ATTEMPT_NAME,
            "byte_count": len(retained_outer_attempt_raw),
            "sha256": hashlib.sha256(
                retained_outer_attempt_raw
            ).hexdigest(),
            "partial_allowed": not attempt_observed_exact,
        }
        if attempt_rows != (expected_attempt_row,):
            raise AuthorityError(
                "owned outer LAUNCH_ATTEMPT bytes changed after terminal "
                "classification"
            )
        try:
            final_outer_attempt_raw = store.read_exact(
                OUTER_LAUNCH_ATTEMPT_NAME, allow_empty=True
            )
        except BaseException as inventory_error:
            raise AuthorityError(
                "owned outer LAUNCH_ATTEMPT final bytes are unavailable "
                "before terminal publication"
            ) from inventory_error
        if final_outer_attempt_raw != retained_outer_attempt_raw:
            raise AuthorityError(
                "owned outer LAUNCH_ATTEMPT bytes changed after bound "
                "inventory readback"
            )
        _publish_outer_launch_failure_terminal(
            store=store,
            authority=authority,
            external_root_raw=external_root_raw,
            failure=failure,
            cause=error,
        )
    _after_attempt_ns, remaining_after_attempt_ns = _sample_outer_remaining(
        deadline_ns, monotonic_ns, "outer launch after ATTEMPT publication"
    )
    deadline_contract["remaining_after_attempt_publication_ns"] = (
        remaining_after_attempt_ns
    )
    deadline_contract = validate_outer_deadline_contract(deadline_contract)
    if remaining_after_attempt_ns <= required_after_issuance_ns:
        _terminal_gate_ns, terminal_remaining_ns = _sample_outer_remaining(
            deadline_ns,
            monotonic_ns,
            "outer failure publication after ATTEMPT deadline gate",
        )
        deadline_contract["remaining_before_terminal_publication_ns"] = (
            terminal_remaining_ns
        )
        deadline_contract = validate_outer_deadline_contract(deadline_contract)
        gate_error = OSError(
            errno.ETIMEDOUT,
            "durable LAUNCH_ATTEMPT left insufficient process/absence/closure time",
        )
        _publish_outer_launch_failure(
            store=store,
            authority=authority,
            external_root_raw=external_root_raw,
            outer_attempt=outer_attempt,
            result=None,
            inner=None,
            prelaunch_absence=prelaunch_absence,
            postlaunch_absence=None,
            error=gate_error,
            reason="AFTER_ATTEMPT_DEADLINE_GATE_FAILED",
            deadline_contract=deadline_contract,
        )
    external_digest = hashlib.sha256(external_root_raw).hexdigest()
    try:
        command = validate_systemd_run_command(
            outer_attempt["systemd_run_argv"],
            invocation,
            external_root_sha256=external_digest,
        )
    except BaseException as error:
        _terminal_gate_ns, terminal_remaining_ns = _sample_outer_remaining(
            deadline_ns, monotonic_ns, "outer invocation failure publication"
        )
        deadline_contract["remaining_before_terminal_publication_ns"] = (
            terminal_remaining_ns
        )
        _publish_outer_launch_failure(
            store=store,
            authority=authority,
            external_root_raw=external_root_raw,
            outer_attempt=outer_attempt,
            result=None,
            inner=None,
            prelaunch_absence=prelaunch_absence,
            postlaunch_absence=None,
            error=error,
            reason="SYSTEMD_INVOCATION_VALIDATION_FAILED",
            deadline_contract=deadline_contract,
        )
    result: BoundedProcessResult | None = None
    launch_error: BaseException | None = None
    try:
        result = _validate_bounded_process_result(
            process_adapter.run(
                command,
                timeout_seconds=OUTER_LAUNCH_TIMEOUT_SECONDS,
                stdout_cap=MAX_SUBPROCESS_STDOUT_BYTES,
                stderr_cap=MAX_SUBPROCESS_STDERR_BYTES,
                env=invocation["outer_launch_environment"],
                start_new_session=True,
            ),
            expected_argv=command,
        )
    except BaseException as error:
        result = None
        launch_error = error
    process_completed_ns, remaining_after_process_ns = _sample_outer_remaining(
        deadline_ns, monotonic_ns, "outer launch process completion"
    )
    deadline_contract["remaining_after_process_ns"] = (
        remaining_after_process_ns
    )
    deadline_gate_error: BaseException | None = None
    required_after_process_ns = (
        OUTER_REQUIRED_AFTER_PROCESS_SECONDS * 1_000_000_000
    )
    if remaining_after_process_ns <= required_after_process_ns:
        deadline_gate_error = OSError(
            errno.ETIMEDOUT,
            "outer process left insufficient absence/closure time",
        )
    postlaunch_absence: dict[str, Any] | None = None
    absence_error: BaseException | None = None
    if deadline_gate_error is None:
        post_absence_deadline_ns = min(
            process_completed_ns
            + OUTER_POST_ABSENCE_SECONDS * 1_000_000_000,
            deadline_ns
            - FORMAL_DEADLINE_MARGIN_SECONDS * 1_000_000_000,
        )
        deadline_contract["post_absence_deadline_monotonic_ns"] = (
            post_absence_deadline_ns
        )
        try:
            postlaunch_absence = _validate_success_absence_fact(
                absence_observer.observe_absence(
                    authority, deadline_ns=post_absence_deadline_ns
                ),
                authority,
            )
        except BaseException as error:
            absence_error = error
        post_absence_completed_ns, remaining_after_post_absence_ns = (
            _sample_outer_remaining(
                deadline_ns,
                monotonic_ns,
                "outer postlaunch absence completion",
            )
        )
        deadline_contract["remaining_after_post_absence_ns"] = (
            remaining_after_post_absence_ns
        )
        if post_absence_completed_ns > post_absence_deadline_ns:
            postlaunch_absence = None
            absence_error = OSError(
                errno.ETIMEDOUT,
                "postlaunch absence observer exceeded its local deadline",
            )
        if (
            remaining_after_post_absence_ns
            < FORMAL_DEADLINE_MARGIN_SECONDS * 1_000_000_000
        ):
            deadline_gate_error = OSError(
                errno.ETIMEDOUT,
                "postlaunch absence consumed the closure reserve",
            )
    inner: dict[str, Any] | None = None
    terminal_raw: bytes | None = None
    inner_error: BaseException | None = None
    if deadline_gate_error is None:
        try:
            inner, terminal_raw = observe_inner_launch_state(
                store, authority, external_root_raw
            )
        except ForeignArtifactError:
            raise
        except BaseException as error:
            inner_error = error
        _inner_completed_ns, remaining_after_inner_ns = _sample_outer_remaining(
            deadline_ns, monotonic_ns, "outer inner observation completion"
        )
        deadline_contract["remaining_after_inner_observation_ns"] = (
            remaining_after_inner_ns
        )
        if remaining_after_inner_ns <= 0:
            deadline_gate_error = OSError(
                errno.ETIMEDOUT,
                "inner observation exhausted the formal deadline",
            )
    _terminal_gate_ns, remaining_before_terminal_ns = _sample_outer_remaining(
        deadline_ns, monotonic_ns, "outer terminal publication gate"
    )
    deadline_contract["remaining_before_terminal_publication_ns"] = (
        remaining_before_terminal_ns
    )
    if remaining_before_terminal_ns <= 0:
        deadline_gate_error = OSError(
            errno.ETIMEDOUT,
            "outer terminal publication gate exhausted the formal deadline",
        )
    deadline_contract = validate_outer_deadline_contract(deadline_contract)
    success = (
        launch_error is None
        and absence_error is None
        and inner_error is None
        and deadline_gate_error is None
        and result is not None
        and result.returncode == 0
        and result.timed_out is False
        and result.output_limit_exceeded is False
        and result.stderr == b""
        and inner is not None
        and inner["state"] == "RECEIPT"
        and terminal_raw is not None
        and result.stdout == terminal_raw + b"\n"
        and postlaunch_absence is not None
        and postlaunch_absence.get("unit_absent") is True
        and postlaunch_absence.get("target_absent") is True
    )
    if success:
        assert result is not None and inner is not None
        assert postlaunch_absence is not None
        receipt = _build_outer_launch_receipt(
            outer_attempt,
            result,
            inner,
            prelaunch_absence,
            postlaunch_absence,
            deadline_contract,
        )
        assert terminal_raw is not None
        validate_outer_launch_receipt_document(
            receipt,
            outer_attempt=outer_attempt,
            inner_observation=inner,
            inner_terminal_raw=terminal_raw,
            authority=authority,
        )
        receipt_raw = canonical_json_bytes(receipt)
        receipt_token = PublicationOwnershipToken(OUTER_LAUNCH_RECEIPT_NAME)
        try:
            store.write_once(
                OUTER_LAUNCH_RECEIPT_NAME,
                receipt_raw,
                token=receipt_token,
            )
            store.require_inventory(
                _root_inventory(
                    OUTER_LAUNCH_ATTEMPT_NAME,
                    ATTEMPT_NAME,
                    RECEIPT_NAME,
                    OUTER_LAUNCH_RECEIPT_NAME,
                ),
                phase="OUTER_LAUNCH_RECEIPT_PUBLISHED",
            )
        except FileExistsError as error:
            raise OuterReceiptPublicationUncertain(
                "unowned outer receipt path forbids outer failure"
            ) from error
        except BaseException as error:
            if receipt_token.path_created:
                try:
                    recovered_receipt = _recover_outer_launch_receipt(
                        store, authority, external_root_raw
                    )
                except BaseException as recovery_error:
                    receipt_publication_stage = (
                        error.stage
                        if isinstance(error, DurableWriteError)
                        else OUTER_RECEIPT_POST_RETURN_STAGE
                    )
                    (
                        receipt_exact,
                        receipt_retained_raw,
                    ) = _classify_retained_publication_bytes(
                        store,
                        OUTER_LAUNCH_RECEIPT_NAME,
                        receipt_raw,
                        label="outer LAUNCH_RECEIPT",
                    )
                    if (
                        receipt_publication_stage
                        == OUTER_RECEIPT_POST_RETURN_STAGE
                    ):
                        if (
                            receipt_token.completed is not True
                            or receipt_exact is not True
                        ):
                            raise OuterReceiptPublicationUncertain(
                                "post-return outer receipt cannot be given a "
                                "terminal recovery classification"
                            ) from recovery_error
                    elif (
                        receipt_publication_stage
                        not in OUTER_RECEIPT_DURABLE_WRITE_FAILURE_STAGES
                    ):
                        raise OuterReceiptPublicationUncertain(
                            "outer receipt publication stage is not a typed "
                            "durability checkpoint"
                        ) from recovery_error
                    elif (
                        receipt_publication_stage
                        in OUTER_RECEIPT_EXACT_ONLY_FAILURE_STAGES
                        and receipt_exact is not True
                    ):
                        raise OuterReceiptPublicationUncertain(
                            "late outer receipt checkpoint lacks exact "
                            "canonical bytes"
                        ) from recovery_error
                    elif (
                        receipt_exact is not True
                        and receipt_publication_stage
                        not in {"AFTER_OPEN", "AFTER_INITIAL_FCHMOD"}
                    ):
                        raise OuterReceiptPublicationUncertain(
                            "strict-prefix outer receipt left its early "
                            "publication stages"
                        ) from recovery_error
                    _publish_outer_receipt_recovery_failure(
                        store=store,
                        authority=authority,
                        external_root_raw=external_root_raw,
                        outer_attempt=outer_attempt,
                        result=result,
                        inner=inner,
                        prelaunch_absence=prelaunch_absence,
                        postlaunch_absence=postlaunch_absence,
                        deadline_contract=deadline_contract,
                        receipt_publication=receipt_token,
                        receipt_observed_exact=receipt_exact,
                        receipt_retained_raw=receipt_retained_raw,
                        recovery_error=recovery_error,
                    )
                receipt_token.completed = True
                return _complete_outer_success_decision(
                    store=store,
                    authority=authority,
                    external_root_raw=external_root_raw,
                    outer_attempt=outer_attempt,
                    receipt=recovered_receipt,
                    receipt_raw=receipt_raw,
                    receipt_publication=receipt_token,
                    result=result,
                    inner=inner,
                    prelaunch_absence=prelaunch_absence,
                    postlaunch_absence=postlaunch_absence,
                    deadline_contract=deadline_contract,
                    deadline_ns=deadline_ns,
                    monotonic_ns=monotonic_ns,
                )
            publication_failure = _build_outer_launch_failure(
                outer_attempt,
                result=result,
                inner=inner,
                prelaunch_absence=prelaunch_absence,
                postlaunch_absence=postlaunch_absence,
                error=error,
                reason="LAUNCH_RECEIPT_PUBLICATION_FAILED_BEFORE_O_EXCL",
                deadline_contract=deadline_contract,
                inventory_before_launch_failure=(
                    OUTER_LAUNCH_ATTEMPT_NAME,
                    ATTEMPT_NAME,
                    RECEIPT_NAME,
                ),
            )
            store.require_inventory(
                _root_inventory(
                    OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME, RECEIPT_NAME
                ),
                phase="OUTER_RECEIPT_PRETOKEN_FAILURE",
            )
            _publish_outer_launch_failure_terminal(
                store=store,
                authority=authority,
                external_root_raw=external_root_raw,
                failure=publication_failure,
                cause=error,
            )
        return _complete_outer_success_decision(
            store=store,
            authority=authority,
            external_root_raw=external_root_raw,
            outer_attempt=outer_attempt,
            receipt=receipt,
            receipt_raw=receipt_raw,
            receipt_publication=receipt_token,
            result=result,
            inner=inner,
            prelaunch_absence=prelaunch_absence,
            postlaunch_absence=postlaunch_absence,
            deadline_contract=deadline_contract,
            deadline_ns=deadline_ns,
            monotonic_ns=monotonic_ns,
        )
    error = launch_error or absence_error or inner_error or deadline_gate_error
    failure_components = _build_outer_failure_components(
        process_adapter_error=launch_error,
        deadline_gate_error=deadline_gate_error,
        inner_observation_error=inner_error,
        postlaunch_absence_error=absence_error,
    )
    reason = _derive_ordinary_outer_failure_reason(
        result=result,
        inner=inner,
        inner_terminal_raw=terminal_raw,
        postlaunch_absence=postlaunch_absence,
        deadline_contract=deadline_contract,
        failure_components=failure_components,
        launch_error=_error_fact(error),
    )
    _publish_outer_launch_failure(
        store=store,
        authority=authority,
        external_root_raw=external_root_raw,
        outer_attempt=outer_attempt,
        result=result,
        inner=inner,
        prelaunch_absence=prelaunch_absence,
        postlaunch_absence=postlaunch_absence,
        error=error,
        reason=reason,
        deadline_contract=deadline_contract,
        process_adapter_error=launch_error,
        deadline_gate_error=deadline_gate_error,
        inner_observation_error=inner_error,
        postlaunch_absence_error=absence_error,
    )


def _substage_record(
    index: int,
    substage: str,
    status_text: str,
    detail: Mapping[str, Any],
    error: BaseException | None = None,
) -> dict[str, Any]:
    if status_text not in {"OK", "FAILED"}:
        _fail("substage status changed")
    if error is None:
        error_type = message = error_name = None
        error_number = None
    else:
        error_type, message, error_number, error_name = _bounded_error(error)
    payload = {
        "schema": SUBSTAGE_SCHEMA,
        "index": index,
        "substage": substage,
        "status": status_text,
        "errno": error_number,
        "errno_name": error_name,
        "error_type": error_type,
        "message": message,
        "detail": dict(detail),
    }
    return _self_id_document(SUBSTAGE_DOMAIN, "substage_record_id", payload)


@dataclass(slots=True)
class ServiceHandle:
    app_slice_fd: int
    service_fd: int
    app_slice_path: str
    service_path: str
    source_membership: str
    target_membership: str
    observation: dict[str, Any]


@dataclass(slots=True)
class TargetHandle:
    directory_fd: int
    name: str
    path: str
    membership: str
    device: int
    inode: int
    owned: bool = True
    manager_created: bool = True
    identity_continuous: bool = True
    stop_requested: bool = False
    manager_absence_proven: bool = False
    residual_possible: bool = False
    claimed_inode_unlinked: bool = False


@dataclass(slots=True)
class ChildHandle:
    pid: int
    pidfd: int
    parent_socket: socket.socket | None
    reaped: bool = False
    released: bool = False


class RuntimeAdapter(Protocol):
    def inspect_service(
        self, authority: Mapping[str, Any], deadline_ns: int
    ) -> tuple[ServiceHandle, dict[str, Any]]: ...
    def create_target(
        self, service: ServiceHandle, deadline_ns: int
    ) -> tuple[TargetHandle, dict[str, Any]]: ...
    def clone_child(
        self, target: TargetHandle, deadline_ns: int
    ) -> tuple[ChildHandle, dict[str, Any]]: ...
    def receive_handshake(self, child: ChildHandle, deadline_ns: int) -> dict[str, Any]: ...
    def inspect_child(self, child: ChildHandle, target: TargetHandle) -> dict[str, Any]: ...
    def release_child(self, child: ChildHandle) -> dict[str, Any]: ...
    def reap_exit_zero(self, child: ChildHandle, deadline_ns: int) -> dict[str, Any]: ...
    def kill_child(self, child: ChildHandle) -> dict[str, Any]: ...
    def reap_cleanup(self, child: ChildHandle, deadline_ns: int) -> dict[str, Any]: ...
    def target_empty(self, target: TargetHandle) -> dict[str, Any]: ...
    def remove_target(
        self,
        service: ServiceHandle,
        target: TargetHandle | None,
        deadline_ns: int,
    ) -> dict[str, Any]: ...
    def target_absent(
        self,
        service: ServiceHandle,
        target: TargetHandle | None,
        deadline_ns: int,
    ) -> dict[str, Any]: ...
    def close_child(self, child: ChildHandle) -> None: ...
    def close_service(self, service: ServiceHandle) -> None: ...


class _CloneArgs(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint64),
        ("pidfd", ctypes.c_uint64),
        ("child_tid", ctypes.c_uint64),
        ("parent_tid", ctypes.c_uint64),
        ("exit_signal", ctypes.c_uint64),
        ("stack", ctypes.c_uint64),
        ("stack_size", ctypes.c_uint64),
        ("tls", ctypes.c_uint64),
        ("set_tid", ctypes.c_uint64),
        ("set_tid_size", ctypes.c_uint64),
        ("cgroup", ctypes.c_uint64),
    ]


class _StatFs(ctypes.Structure):
    _fields_ = [
        ("f_type", ctypes.c_long),
        ("f_bsize", ctypes.c_long),
        ("f_blocks", ctypes.c_ulong),
        ("f_bfree", ctypes.c_ulong),
        ("f_bavail", ctypes.c_ulong),
        ("f_files", ctypes.c_ulong),
        ("f_ffree", ctypes.c_ulong),
        ("f_fsid", ctypes.c_int * 2),
        ("f_namelen", ctypes.c_long),
        ("f_frsize", ctypes.c_long),
        ("f_flags", ctypes.c_long),
        ("f_spare", ctypes.c_long * 4),
    ]


def _fstatfs_type_fd(descriptor: int) -> int:
    libc = ctypes.CDLL(None, use_errno=True)
    buffer = _StatFs()
    result = libc.fstatfs(descriptor, ctypes.byref(buffer))
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))
    return int(buffer.f_type)


def _single_threaded() -> bool:
    try:
        count = 0
        with os.scandir("/proc/self/task") as entries:
            for _entry in entries:
                count += 1
                if count > 1:
                    return False
        return count == 1
    except OSError:
        return False


def _read_text_at(directory_fd: int, name: str, cap: int = 64 * 1024) -> str:
    descriptor = os.open(
        name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd
    )
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(4096, cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > cap:
                raise OSError(errno.EOVERFLOW, f"{name} exceeded its read cap")
        return b"".join(chunks).decode("ascii", errors="strict")
    finally:
        os.close(descriptor)


def _proc_cgroup(pid: int) -> str:
    raw = _read_proc_text(Path(f"/proc/{pid}/cgroup"), 4096)
    rows = raw.splitlines()
    if len(rows) != 1 or not rows[0].startswith("0::/"):
        raise OSError(errno.EPROTO, "process lacks one cgroup-v2 membership row")
    return rows[0]


def _proc_starttime(pid: int) -> int:
    raw = _read_proc_text(Path(f"/proc/{pid}/stat"), 64 * 1024)
    close = raw.rfind(")")
    fields = raw[close + 2 :].split()
    if close <= 0 or len(fields) < 20 or not fields[19].isdigit():
        raise OSError(errno.EPROTO, "process stat lacks one starttime")
    return int(fields[19])


def _read_proc_text(path: Path, cap: int) -> str:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(4096, cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > cap:
                raise OSError(errno.EOVERFLOW, "proc observation exceeded its cap")
        return b"".join(chunks).decode("ascii", errors="strict")
    finally:
        os.close(descriptor)


def _nearest_common_ancestor(left: str, right: str) -> str:
    left_parts = PurePosixPath(left).parts
    right_parts = PurePosixPath(right).parts
    common: list[str] = []
    for left_part, right_part in zip(left_parts, right_parts):
        if left_part != right_part:
            break
        common.append(left_part)
    if not common:
        return "/"
    result = str(PurePosixPath(*common))
    return "/" if result == "." else result


def _open_write_permission(path: Path) -> dict[str, Any]:
    try:
        flags = os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open(path, flags)
    except OSError as error:
        return {
            "opened_for_write": False,
            "errno": error.errno,
            "errno_name": errno.errorcode.get(error.errno),
            "device": None,
            "inode": None,
            "mode": None,
            "owner_uid": None,
            "owner_gid": None,
        }
    else:
        try:
            opened = os.fstat(descriptor)
            named = os.stat(path, follow_symlinks=False)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != named.st_dev
                or opened.st_ino != named.st_ino
                or opened.st_mode != named.st_mode
            ):
                raise OSError(
                    errno.ESTALE, "write-permission path/OFD identity changed"
                )
            return {
                "opened_for_write": True,
                "errno": None,
                "errno_name": None,
                "device": opened.st_dev,
                "inode": opened.st_ino,
                "mode": stat.S_IMODE(opened.st_mode),
                "owner_uid": opened.st_uid,
                "owner_gid": opened.st_gid,
            }
        finally:
            os.close(descriptor)


def observe_host_parent_fact() -> dict[str, Any]:
    """Read-only exact app.slice fact used by post-C_probe prepare."""

    uid = os.geteuid()
    gid = os.getegid()
    mount_point = Path("/sys/fs/cgroup")
    app_slice_path = (
        mount_point
        / "user.slice"
        / f"user-{uid}.slice"
        / f"user@{uid}.service"
        / "app.slice"
    )
    mount_stat = os.stat(mount_point, follow_symlinks=False)
    app_stat = os.stat(app_slice_path, follow_symlinks=False)
    procs_stat = os.stat(app_slice_path / "cgroup.procs", follow_symlinks=False)
    runtime_dir = Path(f"/run/user/{uid}")
    user_bus = runtime_dir / "bus"
    runtime_stat = os.stat(runtime_dir, follow_symlinks=False)
    bus_stat = os.stat(user_bus, follow_symlinks=False)
    if (
        not stat.S_ISDIR(runtime_stat.st_mode)
        or runtime_stat.st_uid != uid
        or runtime_stat.st_gid != gid
        or stat.S_IMODE(runtime_stat.st_mode) != 0o700
        or not stat.S_ISSOCK(bus_stat.st_mode)
        or bus_stat.st_uid != uid
        or bus_stat.st_gid != gid
    ):
        raise OSError(
            errno.EACCES,
            "user runtime directory or bus socket ownership/type changed",
        )
    runtime_fd = os.open(
        runtime_dir,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        runtime_opened = os.fstat(runtime_fd)
        runtime_named = os.stat(runtime_dir, follow_symlinks=False)
        if _directory_identity(runtime_opened) != _directory_identity(
            runtime_named
        ):
            raise OSError(errno.ESTALE, "user runtime directory identity drifted")
    finally:
        os.close(runtime_fd)
    bus_fd = os.open(
        user_bus, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        bus_opened = os.fstat(bus_fd)
        bus_named = os.stat(user_bus, follow_symlinks=False)
        bus_fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid")
        if any(
            getattr(bus_opened, field) != getattr(bus_named, field)
            for field in bus_fields
        ):
            raise OSError(errno.ESTALE, "user bus socket identity drifted")
    finally:
        os.close(bus_fd)
    descriptor = os.open(
        app_slice_path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        if _fstatfs_type_fd(descriptor) != CGROUP2_SUPER_MAGIC:
            raise OSError(errno.EXDEV, "host parent is not cgroup2")
        document = {
            "schema": HOST_PARENT_SCHEMA,
            "mount_point": str(mount_point),
            "mount_device": mount_stat.st_dev,
            "mount_inode": mount_stat.st_ino,
            "app_slice_path": str(app_slice_path),
            "app_slice_device": app_stat.st_dev,
            "app_slice_inode": app_stat.st_ino,
            "owner_uid": app_stat.st_uid,
            "owner_gid": app_stat.st_gid,
            "mode": stat.S_IMODE(app_stat.st_mode),
            "controllers": sorted(
                _read_text_at(descriptor, "cgroup.controllers").split()
            ),
            "subtree_control": sorted(
                _read_text_at(descriptor, "cgroup.subtree_control").split()
            ),
            "cgroup_type": _read_text_at(descriptor, "cgroup.type").strip(),
            "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
            "cgroup_procs_device": procs_stat.st_dev,
            "cgroup_procs_inode": procs_stat.st_ino,
            "cgroup_procs_owner_uid": procs_stat.st_uid,
            "cgroup_procs_owner_gid": procs_stat.st_gid,
            "cgroup_procs_mode": stat.S_IMODE(procs_stat.st_mode),
            "runtime_dir_path": str(runtime_dir),
            "runtime_dir_device": runtime_stat.st_dev,
            "runtime_dir_inode": runtime_stat.st_ino,
            "runtime_dir_owner_uid": runtime_stat.st_uid,
            "runtime_dir_owner_gid": runtime_stat.st_gid,
            "runtime_dir_mode": stat.S_IMODE(runtime_stat.st_mode),
            "user_bus_path": str(user_bus),
            "user_bus_device": bus_stat.st_dev,
            "user_bus_inode": bus_stat.st_ino,
            "user_bus_owner_uid": bus_stat.st_uid,
            "user_bus_owner_gid": bus_stat.st_gid,
            "user_bus_mode": stat.S_IMODE(bus_stat.st_mode),
            "user_bus_file_type": "socket",
            "toolchain_facts": observe_toolchain_facts(),
        }
    finally:
        os.close(descriptor)
    return validate_host_parent_fact(document)


def _parse_target_manager_properties(
    raw: bytes, *, expected_keys: frozenset[str]
) -> dict[str, str]:
    if type(raw) is not bytes or not raw or len(raw) > TARGET_MANAGER_OUTPUT_CAP_BYTES:
        _fail("target manager property output left its byte bound")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise AuthorityError("target manager properties are not UTF-8") from error
    if not text.endswith("\n") or "\x00" in text:
        _fail("target manager property framing changed")
    properties: dict[str, str] = {}
    for line in text[:-1].split("\n"):
        if "=" not in line:
            _fail("target manager property row changed")
        key, value = line.split("=", 1)
        if key in properties:
            _fail("target manager property key repeated")
        properties[key] = value
    if type(expected_keys) is not frozenset or set(properties) != expected_keys:
        _fail("target manager property keyset changed")
    return properties


def _target_manager_not_found(properties: Mapping[str, Any]) -> bool:
    return dict(properties) == {
        "LoadState": "not-found",
        "ActiveState": "inactive",
        "SubState": "dead",
        "ControlGroup": "",
    }


def _target_manager_active(
    properties: Mapping[str, Any], *, expected_control_group: str
) -> bool:
    retained = dict(properties)
    if set(retained) != TARGET_MANAGER_ACTIVE_PROPERTY_KEYS:
        return False
    after_units = retained["After"].split()
    return (
        retained["LoadState"] == "loaded"
        and retained["ActiveState"] == "active"
        and retained["SubState"] == "exited"
        and retained["ControlGroup"] == expected_control_group
        and retained["BindsTo"].split() == [SERVICE_UNIT_NAME]
        and SERVICE_UNIT_NAME in after_units
        and retained["KillMode"] == "control-group"
        and retained["Type"] == TARGET_SERVICE_TYPE
        and retained["RemainAfterExit"] == "yes"
        and retained["Delegate"] == "yes"
        and retained["CollectMode"] == "inactive-or-failed"
        and retained["Slice"] == SERVICE_SLICE
        and retained["TimeoutStopUSec"]
        == f"{TARGET_UNIT_STOP_TIMEOUT_SECONDS}s"
    )


def _require_fixed_target_absent(app_slice_fd: int) -> dict[str, Any]:
    try:
        os.stat(
            TARGET_CGROUP_NAME,
            dir_fd=app_slice_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return {"fixed_target_absent_before_create": True}
    raise OSError(
        errno.EEXIST,
        "fixed atomic-birth target pre-exists and is foreign",
    )


class LinuxRuntimeAdapter:
    """Real x86_64 cgroup-v2/clone3 adapter; never used by fixture tests."""

    def __init__(
        self, process_adapter: SubprocessAdapter | None = None
    ) -> None:
        if os.uname().machine != "x86_64" or not _single_threaded():
            raise OSError(errno.ENOTSUP, "probe requires x86_64 and one thread")
        self.libc = ctypes.CDLL(None, use_errno=True)
        self.libc.syscall.restype = ctypes.c_long
        self.process_adapter = (
            DEFAULT_SUBPROCESS_ADAPTER
            if process_adapter is None
            else process_adapter
        )

    def _fstatfs_type(self, descriptor: int) -> int:
        return _fstatfs_type_fd(descriptor)

    @staticmethod
    def _target_contract(service: ServiceHandle) -> dict[str, Any]:
        contract = service.observation.get("target_lifecycle_contract")
        return validate_target_lifecycle_contract(contract, uid=os.geteuid())

    def _run_target_manager(
        self,
        service: ServiceHandle,
        argv_key: str,
        deadline_ns: int,
        *,
        require_empty_stdout: bool,
    ) -> BoundedProcessResult:
        contract = self._target_contract(service)
        if argv_key not in {
            "create_argv",
            "absence_show_argv",
            "active_show_argv",
            "stop_argv",
        }:
            _fail("target manager argv selector changed")
        argv = tuple(contract[argv_key])
        result = self.process_adapter.run(
            argv,
            timeout_seconds=_remaining_timeout_seconds(
                deadline_ns, cap=TARGET_MANAGER_CALL_TIMEOUT_SECONDS
            ),
            stdout_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
            stderr_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
            env=contract["environment"],
            start_new_session=False,
        )
        if (
            result.argv != argv
            or result.returncode != 0
            or result.timed_out
            or result.output_limit_exceeded
            or result.stderr
            or require_empty_stdout
            and result.stdout
        ):
            raise AuthorityError(
                f"target manager {argv_key} subprocess contract failed"
            )
        return result

    def _target_manager_absence_properties(
        self, service: ServiceHandle, deadline_ns: int
    ) -> dict[str, str]:
        result = self._run_target_manager(
            service,
            "absence_show_argv",
            deadline_ns,
            require_empty_stdout=False,
        )
        return _parse_target_manager_properties(
            result.stdout,
            expected_keys=TARGET_MANAGER_ABSENCE_PROPERTY_KEYS,
        )

    def _target_manager_active_properties(
        self, service: ServiceHandle, deadline_ns: int
    ) -> dict[str, str]:
        result = self._run_target_manager(
            service,
            "active_show_argv",
            deadline_ns,
            require_empty_stdout=False,
        )
        return _parse_target_manager_properties(
            result.stdout,
            expected_keys=TARGET_MANAGER_ACTIVE_PROPERTY_KEYS,
        )

    @staticmethod
    def _expected_memberships(uid: int) -> tuple[str, str, str]:
        app = f"/user.slice/user-{uid}.slice/user@{uid}.service/app.slice"
        source = f"{app}/{SERVICE_UNIT_NAME}"
        # The target deliberately is a direct sibling of the transient
        # service, matching the production birth shape.  The nearest common
        # ancestor is therefore app.slice, whose cgroup.procs write authority
        # is the exact permission gate missed by V180r12r3r2.
        target = f"{app}/{TARGET_CGROUP_NAME}"
        return app, source, target

    def inspect_service(
        self, authority: Mapping[str, Any], deadline_ns: int
    ) -> tuple[ServiceHandle, dict[str, Any]]:
        host = validate_host_parent_fact(authority["host_parent_fact"])
        invocation = validate_systemd_invocation_contract(
            authority["systemd_invocation_contract"]
        )
        target_contract = validate_target_lifecycle_contract(
            invocation["target_lifecycle_contract"], uid=os.geteuid()
        )
        uid = os.geteuid()
        gid = os.getegid()
        app_membership, source_membership, target_membership = (
            self._expected_memberships(uid)
        )
        membership_line = _proc_cgroup(os.getpid())
        if membership_line != f"0::{source_membership}":
            raise OSError(errno.EXDEV, "probe is not the exact app.slice service child")
        app_path = Path(host["app_slice_path"])
        expected_app_path = Path(host["mount_point"] + app_membership)
        if app_path != expected_app_path:
            raise OSError(errno.EXDEV, "host app.slice path disagrees with membership")
        service_path = app_path / SERVICE_UNIT_NAME
        app_stat = os.stat(app_path, follow_symlinks=False)
        mount_stat = os.stat(host["mount_point"], follow_symlinks=False)
        procs_stat = os.stat(app_path / "cgroup.procs", follow_symlinks=False)
        runtime_stat = os.stat(host["runtime_dir_path"], follow_symlinks=False)
        bus_stat = os.stat(host["user_bus_path"], follow_symlinks=False)
        live_host_values = {
            "mount_device": mount_stat.st_dev,
            "mount_inode": mount_stat.st_ino,
            "app_slice_device": app_stat.st_dev,
            "app_slice_inode": app_stat.st_ino,
            "owner_uid": app_stat.st_uid,
            "owner_gid": app_stat.st_gid,
            "mode": stat.S_IMODE(app_stat.st_mode),
            "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
            "cgroup_procs_device": procs_stat.st_dev,
            "cgroup_procs_inode": procs_stat.st_ino,
            "cgroup_procs_owner_uid": procs_stat.st_uid,
            "cgroup_procs_owner_gid": procs_stat.st_gid,
            "cgroup_procs_mode": stat.S_IMODE(procs_stat.st_mode),
            "runtime_dir_device": runtime_stat.st_dev,
            "runtime_dir_inode": runtime_stat.st_ino,
            "runtime_dir_owner_uid": runtime_stat.st_uid,
            "runtime_dir_owner_gid": runtime_stat.st_gid,
            "runtime_dir_mode": stat.S_IMODE(runtime_stat.st_mode),
            "user_bus_device": bus_stat.st_dev,
            "user_bus_inode": bus_stat.st_ino,
            "user_bus_owner_uid": bus_stat.st_uid,
            "user_bus_owner_gid": bus_stat.st_gid,
            "user_bus_mode": stat.S_IMODE(bus_stat.st_mode),
        }
        if (
            not stat.S_ISDIR(runtime_stat.st_mode)
            or not stat.S_ISSOCK(bus_stat.st_mode)
            or any(host[key] != value for key, value in live_host_values.items())
        ):
            raise OSError(errno.ESTALE, "host app.slice inode or ownership fact drifted")
        app_fd = os.open(
            app_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        try:
            if (
                self._fstatfs_type(app_fd) != CGROUP2_SUPER_MAGIC
                or sorted(_read_text_at(app_fd, "cgroup.controllers").split())
                != host["controllers"]
                or sorted(_read_text_at(app_fd, "cgroup.subtree_control").split())
                != host["subtree_control"]
                or _read_text_at(app_fd, "cgroup.type").strip() != host["cgroup_type"]
            ):
                raise OSError(errno.ESTALE, "host app.slice controller fact drifted")
        except BaseException:
            os.close(app_fd)
            raise
        try:
            _require_fixed_target_absent(app_fd)
        except BaseException:
            os.close(app_fd)
            raise
        try:
            service_fd = os.open(
                service_path,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
        except BaseException:
            os.close(app_fd)
            raise
        try:
            if self._fstatfs_type(service_fd) != CGROUP2_SUPER_MAGIC:
                raise OSError(errno.EXDEV, "transient service is not on cgroup2")
            service_stat = os.fstat(service_fd)
            service_procs = tuple(
                sorted(
                    int(row)
                    for row in _read_text_at(service_fd, "cgroup.procs").split()
                )
            )
            if service_procs != (os.getpid(),):
                raise OSError(errno.EBUSY, "service cgroup does not contain only the probe")
            nca = _nearest_common_ancestor(source_membership, target_membership)
            if nca != app_membership:
                raise OSError(errno.EXDEV, "source/target nearest common ancestor drifted")
            nca_permission = _open_write_permission(app_path / "cgroup.procs")
            if nca_permission["opened_for_write"] is not True:
                raise OSError(
                    int(nca_permission["errno"] or errno.EACCES),
                    "nearest-common-ancestor cgroup.procs is not writable",
                )
            service_permission = _open_write_permission(
                service_path / "cgroup.procs"
            )
            provisional_service = ServiceHandle(
                app_fd,
                service_fd,
                str(app_path),
                str(service_path),
                source_membership,
                target_membership,
                {"target_lifecycle_contract": target_contract},
            )
            manager_precreate = self._target_manager_absence_properties(
                provisional_service, deadline_ns
            )
            if not _target_manager_not_found(manager_precreate):
                raise OSError(
                    errno.EEXIST,
                    "target transient unit pre-exists or is not fully collected",
                )
            observation = {
                "pid": os.getpid(),
                "uid": uid,
                "gid": gid,
                "membership_line": membership_line,
                "app_slice_membership": app_membership,
                "source_membership": source_membership,
                "target_membership": target_membership,
                "nearest_common_ancestor": nca,
                "service_path": str(service_path),
                "service_device": service_stat.st_dev,
                "service_inode": service_stat.st_ino,
                "service_owner_uid": service_stat.st_uid,
                "service_owner_gid": service_stat.st_gid,
                "service_mode": stat.S_IMODE(service_stat.st_mode),
                "service_procs": list(service_procs),
                "nca_cgroup_procs_write": nca_permission,
                "app_slice_cgroup_procs_write": nca_permission,
                "app_slice_cgroup_procs_write_required": True,
                "service_cgroup_procs_write": service_permission,
                "service_type_from_outer_context": SERVICE_TYPE,
                "delegate_from_outer_context": True,
                "fixed_target_absent_before_create": True,
                "target_manager_absent_before_create": True,
                "target_manager_precreate_properties": manager_precreate,
                "target_lifecycle_contract": target_contract,
                "target_lifecycle_unique_authority": (
                    "SYSTEMD_USER_MANAGER_ONLY"
                ),
            }
            return (
                ServiceHandle(
                    app_fd,
                    service_fd,
                    str(app_path),
                    str(service_path),
                    source_membership,
                    target_membership,
                    observation,
                ),
                observation,
            )
        except BaseException:
            os.close(service_fd)
            os.close(app_fd)
            raise

    def create_target(
        self, service: ServiceHandle, deadline_ns: int
    ) -> tuple[TargetHandle, dict[str, Any]]:
        target_path = f"{service.app_slice_path}/{TARGET_CGROUP_NAME}"
        precreate = self._target_manager_absence_properties(
            service, deadline_ns
        )
        if not _target_manager_not_found(precreate):
            raise TargetCreationError(
                errno.EEXIST,
                "target manager unit was not absent immediately before create",
                target=None,
            )
        try:
            _require_fixed_target_absent(service.app_slice_fd)
        except OSError as error:
            raise TargetCreationError(
                error.errno or errno.EEXIST,
                "target cgroup path was not absent immediately before create",
                target=None,
            ) from error
        claimed = TargetHandle(
            -1,
            TARGET_CGROUP_NAME,
            target_path,
            service.target_membership,
            -1,
            -1,
            True,
            True,
            False,
            False,
            False,
            True,
        )
        create_result: BoundedProcessResult | None = None
        try:
            create_result = self._run_target_manager(
                service,
                "create_argv",
                deadline_ns,
                require_empty_stdout=True,
            )
            properties: dict[str, str] | None = None
            polls = 0
            while polls < TARGET_MANAGER_MAX_POLLS:
                polls += 1
                properties = self._target_manager_active_properties(
                    service, deadline_ns
                )
                if _target_manager_active(
                    properties,
                    expected_control_group=service.target_membership,
                ):
                    break
                if time.monotonic_ns() >= deadline_ns:
                    raise OSError(
                        errno.ETIMEDOUT,
                        "target manager create poll exhausted inner deadline",
                    )
                time.sleep(0.025)
            else:
                raise OSError(
                    errno.ETIMEDOUT,
                    "target manager create poll exceeded its count bound",
                )
            assert properties is not None
            descriptor = os.open(
                TARGET_CGROUP_NAME,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=service.app_slice_fd,
            )
            claimed.directory_fd = descriptor
            metadata = os.fstat(descriptor)
            named = os.stat(
                TARGET_CGROUP_NAME,
                dir_fd=service.app_slice_fd,
                follow_symlinks=False,
            )
            claimed.device = metadata.st_dev
            claimed.inode = metadata.st_ino
            claimed.identity_continuous = True
            claimed.residual_possible = False
            target_type = _read_text_at(descriptor, "cgroup.type").strip()
            final_properties = self._target_manager_active_properties(
                service, deadline_ns
            )
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_dev != named.st_dev
                or metadata.st_ino != named.st_ino
                or self._fstatfs_type(descriptor) != CGROUP2_SUPER_MAGIC
                or target_type != "domain"
                or _read_text_at(descriptor, "cgroup.procs").strip()
                or not _target_manager_active(
                    final_properties,
                    expected_control_group=service.target_membership,
                )
            ):
                raise OSError(
                    errno.ESTALE,
                    "manager target unit/path/OFD identity was not continuous",
                )
            permission = _open_write_permission(
                Path(service.app_slice_path) / TARGET_CGROUP_NAME / "cgroup.procs"
            )
            if permission["opened_for_write"] is not True:
                raise OSError(
                    int(permission["errno"] or errno.EACCES),
                    "manager target cgroup.procs is not writable",
                )
            detail = {
                "target_name": TARGET_CGROUP_NAME,
                "target_unit_name": TARGET_SERVICE_UNIT_NAME,
                "target_token": TARGET_TOKEN,
                "target_path": target_path,
                "target_membership": service.target_membership,
                "target_device": metadata.st_dev,
                "target_inode": metadata.st_ino,
                "target_cgroup_type": target_type,
                "target_cgroup_procs_write": permission,
                "initial_cgroup_procs": [],
                "manager_create_argv": list(create_result.argv),
                "manager_create_environment": self._target_contract(service)[
                    "environment"
                ],
                "manager_create_returncode": create_result.returncode,
                "manager_create_stdout": _output_fact(create_result.stdout),
                "manager_create_stderr": _output_fact(create_result.stderr),
                "manager_properties": final_properties,
                "manager_poll_count": polls,
                "manager_owned_lifecycle": True,
                "probe_path_deletion_calls": 0,
            }
            return claimed, detail
        except BaseException as error:
            claimed.identity_continuous = False
            claimed.residual_possible = True
            if claimed.directory_fd >= 0:
                os.close(claimed.directory_fd)
                claimed.directory_fd = -1
            error_number = getattr(error, "errno", None)
            raise TargetCreationError(
                error_number if type(error_number) is int else errno.EIO,
                "manager target creation or identity claim failed",
                target=claimed,
            ) from error

    @staticmethod
    def _poll_fd(descriptor: int, deadline_ns: int) -> None:
        poller = select.poll()
        poller.register(descriptor, select.POLLIN | select.POLLHUP | select.POLLERR)
        while True:
            remaining = deadline_ns - time.monotonic_ns()
            if remaining <= 0:
                raise OSError(errno.ETIMEDOUT, "bounded pidfd/handshake wait expired")
            timeout_ms = max(1, min(250, (remaining + 999_999) // 1_000_000))
            if poller.poll(timeout_ms):
                return

    def clone_child(
        self, target: TargetHandle, deadline_ns: int
    ) -> tuple[ChildHandle, dict[str, Any]]:
        parent_socket, child_socket = socket.socketpair(
            socket.AF_UNIX,
            socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC,
        )
        pidfd_cell = ctypes.c_int(-1)
        args = _CloneArgs()
        args.flags = CLONE_PIDFD | CLONE_INTO_CGROUP
        args.pidfd = ctypes.addressof(pidfd_cell)
        args.exit_signal = signal.SIGCHLD
        args.cgroup = target.directory_fd
        result = self.libc.syscall(
            CLONE3_SYSCALL_X86_64, ctypes.byref(args), ctypes.sizeof(args)
        )
        if result == 0:
            parent_socket.close()
            try:
                payload = {
                    "schema": HANDSHAKE_SCHEMA,
                    "preflight_token": PREFLIGHT_TOKEN,
                    "pid": os.getpid(),
                    "ppid": os.getppid(),
                    "membership_line": _proc_cgroup(os.getpid()),
                }
                handshake = _self_id_document(
                    HANDSHAKE_DOMAIN, "handshake_id", payload
                )
                raw = canonical_json_bytes(handshake)
                if child_socket.send(raw) != len(raw):
                    os._exit(125)
                if child_socket.recv(1) != b"\x06":
                    os._exit(126)
                os._exit(0)
            except BaseException:
                os._exit(127)
        child_socket.close()
        if result < 0:
            error_number = ctypes.get_errno()
            parent_socket.close()
            raise OSError(error_number, os.strerror(error_number))
        pid = int(result)
        pidfd = pidfd_cell.value
        if pidfd < 0:
            try:
                os.kill(pid, signal.SIGKILL)
            finally:
                while True:
                    waited, _status = os.waitpid(pid, os.WNOHANG)
                    if waited == pid:
                        break
                    if time.monotonic_ns() >= deadline_ns:
                        parent_socket.close()
                        raise OSError(
                            errno.ETIMEDOUT,
                            "clone3 child without pidfd did not reap by deadline",
                        )
                    time.sleep(0.005)
                parent_socket.close()
            raise OSError(errno.EPROTO, "clone3 omitted CLONE_PIDFD result")
        try:
            fcntl.fcntl(pidfd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        except BaseException:
            try:
                signal_result = self.libc.syscall(
                    PIDFD_SEND_SIGNAL_SYSCALL_X86_64,
                    pidfd,
                    signal.SIGKILL,
                    0,
                    0,
                )
                if signal_result != 0 and ctypes.get_errno() != errno.ESRCH:
                    os.kill(pid, signal.SIGKILL)
                self._poll_fd(pidfd, deadline_ns)
                if hasattr(os, "P_PIDFD"):
                    os.waitid(os.P_PIDFD, pidfd, os.WEXITED)
                else:
                    os.waitpid(pid, 0)
            finally:
                os.close(pidfd)
                parent_socket.close()
            raise
        return (
            ChildHandle(pid, pidfd, parent_socket),
            {
                "pid": pid,
                "pidfd": pidfd,
                "clone3_flags": ["CLONE_INTO_CGROUP", "CLONE_PIDFD"],
                "target_cgroup_fd": target.directory_fd,
            },
        )

    def receive_handshake(
        self, child: ChildHandle, deadline_ns: int
    ) -> dict[str, Any]:
        if child.parent_socket is None:
            raise OSError(errno.EBADF, "child handshake socket is closed")
        self._poll_fd(child.parent_socket.fileno(), deadline_ns)
        raw, _ancillary, flags, _address = child.parent_socket.recvmsg(
            MAX_HANDSHAKE_BYTES, 0
        )
        if not raw or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
            raise OSError(errno.EMSGSIZE, "child handshake was empty or truncated")
        document = loads_canonical_json(raw)
        if type(document) is not dict or set(document) != {
            "schema",
            "preflight_token",
            "pid",
            "ppid",
            "membership_line",
            "handshake_id",
        }:
            raise OSError(errno.EPROTO, "child handshake fields changed")
        payload = dict(document)
        identity = payload.pop("handshake_id")
        if (
            document["schema"] != HANDSHAKE_SCHEMA
            or document["preflight_token"] != PREFLIGHT_TOKEN
            or document["pid"] != child.pid
            or document["ppid"] != os.getpid()
            or identity != _domain_id(HANDSHAKE_DOMAIN, payload)
        ):
            raise OSError(errno.EPROTO, "child handshake identity changed")
        return {
            "handshake_id": identity,
            "pid": document["pid"],
            "ppid": document["ppid"],
            "membership_line": document["membership_line"],
            "canonical_byte_count": len(raw),
            "canonical_sha256": hashlib.sha256(raw).hexdigest(),
        }

    def inspect_child(
        self, child: ChildHandle, target: TargetHandle
    ) -> dict[str, Any]:
        pidfd_stat = os.fstat(child.pidfd)
        values: dict[str, str] = {}
        for line in _read_proc_text(
            Path(f"/proc/self/fdinfo/{child.pidfd}"), 64 * 1024
        ).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                values[key] = value.strip()
        if not values.get("Pid", "").isdigit():
            raise OSError(errno.EPROTO, "pidfd lacks one Pid identity")
        nspid = tuple(int(value) for value in values.get("NSpid", "").split())
        membership = _proc_cgroup(child.pid)
        if (
            int(values["Pid"]) != child.pid
            or not nspid
            or nspid[0] != child.pid
            or membership != f"0::{target.membership}"
        ):
            raise OSError(errno.EXDEV, "pidfd or atomic target membership changed")
        return {
            "pid": child.pid,
            "pidfd": child.pidfd,
            "pidfd_device": pidfd_stat.st_dev,
            "pidfd_inode": pidfd_stat.st_ino,
            "fdinfo_pid": int(values["Pid"]),
            "fdinfo_nspid": list(nspid),
            "proc_starttime_ticks": _proc_starttime(child.pid),
            "membership_line": membership,
            "target_device": target.device,
            "target_inode": target.inode,
            "pidfd_cloexec": bool(
                fcntl.fcntl(child.pidfd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
            ),
        }

    def release_child(self, child: ChildHandle) -> dict[str, Any]:
        if child.parent_socket is None or child.parent_socket.send(b"\x06") != 1:
            raise OSError(errno.EPIPE, "child release ACK failed")
        child.released = True
        return {"ack_hex": "06", "released": True}

    def _waitid(self, child: ChildHandle, deadline_ns: int) -> Any:
        self._poll_fd(child.pidfd, deadline_ns)
        if hasattr(os, "P_PIDFD"):
            result = os.waitid(os.P_PIDFD, child.pidfd, os.WEXITED)
        else:
            pid, status_value = os.waitpid(child.pid, 0)
            if pid != child.pid:
                raise OSError(errno.ECHILD, "waitpid reaped a foreign child")
            result = {
                "si_pid": pid,
                "si_code": os.CLD_EXITED if os.WIFEXITED(status_value) else os.CLD_KILLED,
                "si_status": (
                    os.WEXITSTATUS(status_value)
                    if os.WIFEXITED(status_value)
                    else os.WTERMSIG(status_value)
                ),
            }
        child.reaped = True
        return result

    @staticmethod
    def _wait_fields(result: Any) -> tuple[int, int, int]:
        if type(result) is dict:
            return result["si_pid"], result["si_code"], result["si_status"]
        return result.si_pid, result.si_code, result.si_status

    def reap_exit_zero(
        self, child: ChildHandle, deadline_ns: int
    ) -> dict[str, Any]:
        result = self._waitid(child, deadline_ns)
        pid, code, status_value = self._wait_fields(result)
        if pid != child.pid or code != os.CLD_EXITED or status_value != 0:
            raise OSError(errno.ECHILD, "handshake child did not exit exactly zero")
        return {
            "pid": pid,
            "si_code": code,
            "si_status": status_value,
            "exit_zero": True,
        }

    def kill_child(self, child: ChildHandle) -> dict[str, Any]:
        if child.reaped:
            return {"signal": "NONE", "already_reaped": True}
        result = self.libc.syscall(
            PIDFD_SEND_SIGNAL_SYSCALL_X86_64,
            child.pidfd,
            signal.SIGKILL,
            0,
            0,
        )
        if result != 0:
            error_number = ctypes.get_errno()
            if error_number != errno.ESRCH:
                raise OSError(error_number, os.strerror(error_number))
        return {
            "signal": "SIGKILL",
            "pidfd_send_signal_errno": None if result == 0 else errno.ESRCH,
        }

    def reap_cleanup(
        self, child: ChildHandle, deadline_ns: int
    ) -> dict[str, Any]:
        if child.reaped:
            return {"already_reaped": True, "pid": child.pid}
        result = self._waitid(child, deadline_ns)
        pid, code, status_value = self._wait_fields(result)
        if pid != child.pid:
            raise OSError(errno.ECHILD, "cleanup reaped a foreign child")
        return {
            "already_reaped": False,
            "pid": pid,
            "si_code": code,
            "si_status": status_value,
        }

    def target_empty(self, target: TargetHandle) -> dict[str, Any]:
        procs = tuple(
            int(row) for row in _read_text_at(target.directory_fd, "cgroup.procs").split()
        )
        events = dict(
            line.split(" ", 1)
            for line in _read_text_at(target.directory_fd, "cgroup.events").splitlines()
            if line
        )
        if procs or events.get("populated") != "0":
            raise OSError(errno.EBUSY, "target remained populated after child reap")
        return {"cgroup_procs": [], "populated": 0}

    def remove_target(
        self,
        service: ServiceHandle,
        target: TargetHandle | None,
        deadline_ns: int,
    ) -> dict[str, Any]:
        if (
            target is None
            or target.owned is not True
            or target.manager_created is not True
            or target.identity_continuous is not True
            or target.device < 0
            or target.inode < 0
            or target.directory_fd < 0
        ):
            if target is not None:
                target.identity_continuous = False
                target.residual_possible = True
            raise OSError(
                errno.EPERM,
                "manager stop forbidden without a continuous target claim",
            )
        try:
            properties = self._target_manager_active_properties(
                service, deadline_ns
            )
            named = os.stat(
                TARGET_CGROUP_NAME,
                dir_fd=service.app_slice_fd,
                follow_symlinks=False,
            )
            opened = os.fstat(target.directory_fd)
            if (
                not _target_manager_active(
                    properties,
                    expected_control_group=service.target_membership,
                )
                or not stat.S_ISDIR(named.st_mode)
                or named.st_dev != target.device
                or named.st_ino != target.inode
                or opened.st_dev != target.device
                or opened.st_ino != target.inode
            ):
                raise OSError(
                    errno.ESTALE,
                    "manager unit/path/OFD identity drifted before stop",
                )
        except BaseException as error:
            target.identity_continuous = False
            target.residual_possible = True
            if target.directory_fd >= 0:
                os.close(target.directory_fd)
                target.directory_fd = -1
            if isinstance(error, OSError) and error.errno == errno.ESTALE:
                raise
            raise OSError(
                errno.ESTALE,
                "target identity continuity could not be proven before stop",
            ) from error
        target.stop_requested = True
        try:
            stop_result = self._run_target_manager(
                service,
                "stop_argv",
                deadline_ns,
                require_empty_stdout=True,
            )
        except BaseException:
            target.residual_possible = True
            if target.directory_fd >= 0:
                os.close(target.directory_fd)
                target.directory_fd = -1
            raise
        last_properties: dict[str, str] | None = None
        polls = 0
        while polls < TARGET_MANAGER_MAX_POLLS:
            polls += 1
            last_properties = self._target_manager_absence_properties(
                service, deadline_ns
            )
            try:
                named_after_stop = os.stat(
                    TARGET_CGROUP_NAME,
                    dir_fd=service.app_slice_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                path_absent = True
            else:
                path_absent = False
                if (
                    named_after_stop.st_dev != target.device
                    or named_after_stop.st_ino != target.inode
                ):
                    target.identity_continuous = False
                    target.residual_possible = True
                    if target.directory_fd >= 0:
                        os.close(target.directory_fd)
                        target.directory_fd = -1
                    raise OSError(
                        errno.ESTALE,
                        "replacement appeared while manager stop was pending",
                    )
            if _target_manager_not_found(last_properties) and path_absent:
                opened_after_stop = os.fstat(target.directory_fd)
                if (
                    opened_after_stop.st_dev != target.device
                    or opened_after_stop.st_ino != target.inode
                    or opened_after_stop.st_nlink != 0
                ):
                    target.identity_continuous = False
                    target.residual_possible = True
                    os.close(target.directory_fd)
                    target.directory_fd = -1
                    raise OSError(
                        errno.ESTALE,
                        "manager reported absence without unlinking the claimed inode",
                    )
                target.claimed_inode_unlinked = True
                target.manager_absence_proven = True
                target.residual_possible = False
                if target.directory_fd >= 0:
                    os.close(target.directory_fd)
                    target.directory_fd = -1
                return {
                    "removed": True,
                    "already_absent": False,
                    "owned_device": target.device,
                    "owned_inode": target.inode,
                    "manager_stop_argv": list(stop_result.argv),
                    "manager_stop_environment": self._target_contract(service)[
                        "environment"
                    ],
                    "manager_stop_returncode": stop_result.returncode,
                    "manager_stop_stdout": _output_fact(stop_result.stdout),
                    "manager_stop_stderr": _output_fact(stop_result.stderr),
                    "manager_final_properties": last_properties,
                    "manager_poll_count": polls,
                    "probe_path_deletion_calls": 0,
                    "manager_absence_proven": True,
                    "claimed_inode_unlinked": True,
                }
            if time.monotonic_ns() >= deadline_ns:
                break
            time.sleep(0.025)
        target.residual_possible = True
        if target.directory_fd >= 0:
            os.close(target.directory_fd)
            target.directory_fd = -1
        raise OSError(
            errno.ETIMEDOUT,
            "target manager stop did not reach not-found plus path absence",
        )

    def target_absent(
        self,
        service: ServiceHandle,
        target: TargetHandle | None,
        deadline_ns: int,
    ) -> dict[str, Any]:
        if target is not None and (
            target.identity_continuous is not True
            or target.residual_possible is True
            or target.manager_absence_proven is not True
        ):
            raise OSError(
                errno.ESTALE,
                "target residual is possible despite fixed-name absence",
            )
        properties = self._target_manager_absence_properties(
            service, deadline_ns
        )
        try:
            os.stat(
                TARGET_CGROUP_NAME,
                dir_fd=service.app_slice_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            path_absent = True
        else:
            path_absent = False
        if not _target_manager_not_found(properties) or not path_absent:
            raise OSError(
                errno.EEXIST,
                "manager target unit or domain-separated path still exists",
            )
        return {
            "target_absent": True,
            "target_unit_absent": True,
            "target_path_absent": True,
            "manager_absence_proven": True,
            "manager_properties": properties,
            "manager_lifecycle_authority": "SYSTEMD_USER_MANAGER_ONLY",
            "probe_path_deletion_calls": 0,
        }

    def close_child(self, child: ChildHandle) -> None:
        if child.parent_socket is not None:
            child.parent_socket.close()
            child.parent_socket = None
        if child.pidfd >= 0:
            os.close(child.pidfd)
            child.pidfd = -1

    def close_service(self, service: ServiceHandle) -> None:
        if service.service_fd >= 0:
            os.close(service.service_fd)
            service.service_fd = -1
        if service.app_slice_fd >= 0:
            os.close(service.app_slice_fd)
            service.app_slice_fd = -1


def _validated_target_absence_detail(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    expected_fields = {
        "target_absent",
        "target_unit_absent",
        "target_path_absent",
        "manager_absence_proven",
        "manager_properties",
        "manager_lifecycle_authority",
        "probe_path_deletion_calls",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise OSError(errno.EPROTO, "target absence evidence fields changed")
    retained = dict(value)
    if (
        retained["target_absent"] is not True
        or retained["target_unit_absent"] is not True
        or retained["target_path_absent"] is not True
        or retained["manager_absence_proven"] is not True
        or type(retained["manager_properties"]) is not dict
        or not _target_manager_not_found(retained["manager_properties"])
        or retained["manager_lifecycle_authority"]
        != "SYSTEMD_USER_MANAGER_ONLY"
        or type(retained["probe_path_deletion_calls"]) is not int
        or retained["probe_path_deletion_calls"] != 0
    ):
        raise OSError(errno.EPROTO, "target absence evidence values changed")
    return retained


def _validated_target_removal_detail(
    target: TargetHandle, value: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        retained = _validate_full_target_removal_detail(
            value,
            target_contract=build_target_lifecycle_contract(os.geteuid()),
            expected_device=target.device,
            expected_inode=target.inode,
        )
    except PreflightError as error:
        raise OSError(
            errno.EPROTO, "target manager removal evidence is mistyped"
        ) from error
    if (
        target.manager_created is not True
        or target.identity_continuous is not True
        or target.stop_requested is not True
        or target.manager_absence_proven is not True
        or target.residual_possible is not False
        or target.claimed_inode_unlinked is not True
    ):
        raise OSError(errno.EPROTO, "target manager removal evidence changed")
    return retained


def _build_receipt(
    attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    *,
    target: TargetHandle,
) -> dict[str, Any]:
    if (
        target.manager_created is not True
        or target.identity_continuous is not True
        or target.stop_requested is not True
        or target.manager_absence_proven is not True
        or target.residual_possible is not False
        or target.claimed_inode_unlinked is not True
    ):
        _fail("inner RECEIPT lacks a completed manager target lifecycle")
    _validate_success_substage_prefix(
        records, attempt=attempt, authority=authority
    )
    payload = {
        "schema": RECEIPT_SCHEMA,
        "probe_attempt_id": attempt["probe_attempt_id"],
        "preflight_token": PREFLIGHT_TOKEN,
        "ordinal": PREFLIGHT_ORDINAL,
        "service_unit_name": SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        "target_token": TARGET_TOKEN,
        "target_unit_name": TARGET_SERVICE_UNIT_NAME,
        "target_lifecycle_authority": "SYSTEMD_USER_MANAGER_ONLY",
        "clone3_flags": ["CLONE_INTO_CGROUP", "CLONE_PIDFD"],
        "source_is_exact_service_root": True,
        "nearest_common_ancestor_is_app_slice": True,
        "app_slice_cgroup_procs_write_required": True,
        "child_handshake_complete": True,
        "pidfd_identity_complete": True,
        "child_membership_exact": True,
        "child_exit_zero": True,
        "bounded_cleanup_complete": True,
        "target_absent": True,
        "target_manager_owned": True,
        "target_manager_stop_complete": True,
        "target_unit_absent": True,
        "target_claimed_inode_unlinked": True,
        "probe_path_deletion_calls": 0,
        "substage_records": [dict(record) for record in records],
    }
    return _self_id_document(RECEIPT_DOMAIN, "preflight_receipt_id", payload)


def _build_failure(
    attempt: Mapping[str, Any],
    authority: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    *,
    primary_substage: str,
    primary_error: BaseException,
) -> dict[str, Any]:
    validated_records = [
        validate_substage_record(row, expected_index=index)
        for index, row in enumerate(records)
    ]
    primary, derived = _validate_failure_records(
        validated_records, attempt=attempt, authority=authority
    )
    error_type, message, error_number, error_name = _bounded_error(primary_error)
    if (
        primary["substage"] != primary_substage
        or primary["errno"] != error_number
        or primary["errno_name"] != error_name
        or primary["error_type"] != error_type
        or primary["message"] != message
    ):
        _fail("failure builder primary error disagrees with its record")
    payload = {
        "schema": FAILURE_SCHEMA,
        "probe_attempt_id": attempt["probe_attempt_id"],
        "preflight_token": PREFLIGHT_TOKEN,
        "ordinal": PREFLIGHT_ORDINAL,
        "service_unit_name": SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        "target_token": TARGET_TOKEN,
        "target_unit_name": TARGET_SERVICE_UNIT_NAME,
        "target_lifecycle_authority": "SYSTEMD_USER_MANAGER_ONLY",
        "failed_substage": primary_substage,
        "errno": error_number,
        "errno_name": error_name,
        "error_type": error_type,
        "message": message,
        "child_reaped": derived["child_reaped"],
        "process_may_remain": not derived["child_reaped"],
        "target_absent": derived["target_absent"],
        "target_may_remain": not derived["target_absent"],
        "target_identity_continuous": derived["target_identity_continuous"],
        "target_manager_stop_requested": derived[
            "target_manager_stop_requested"
        ],
        "target_manager_absence_proven": derived[
            "target_manager_absence_proven"
        ],
        "probe_path_deletion_calls": 0,
        "substage_records": [dict(record) for record in records],
        "scientific_occurrence_started": False,
        "campaign_actual_measurement": False,
    }
    return _self_id_document(FAILURE_DOMAIN, "preflight_failure_id", payload)


def run_probe_once(
    *,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
    store: DurableArtifactStore,
    runtime: RuntimeAdapter,
    environ: Mapping[str, str],
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
    process_entry_ns: int | None = None,
    deadline_ns: int | None = None,
) -> dict[str, Any]:
    """Consume one probe identity and return only after target absence."""

    authority = validate_external_root_document(authority)
    retained_authority = loads_canonical_json(external_root_raw)
    if retained_authority != authority:
        _fail("external root bytes disagree with supplied authority")
    external_sha = hashlib.sha256(external_root_raw).hexdigest()
    invocation = authority["systemd_invocation_contract"]
    expected_env = expected_clean_environment(
        invocation["external_root_path"], external_sha
    )
    if dict(environ) != expected_env:
        _fail("live clean environment disagrees with external root")
    validate_retained_outer_launch_attempt(store, authority, external_root_raw)
    attempt = build_attempt_document(authority, external_root_raw)
    started_ns = monotonic_ns()
    process_entry_ns = (
        started_ns if process_entry_ns is None else process_entry_ns
    )
    deadline_ns = (
        process_entry_ns + INNER_TOTAL_TIMEOUT_NS
        if deadline_ns is None
        else deadline_ns
    )
    if (
        type(process_entry_ns) is not int
        or type(deadline_ns) is not int
        or process_entry_ns > started_ns
        or deadline_ns - process_entry_ns != INNER_TOTAL_TIMEOUT_NS
        or deadline_ns <= started_ns
    ):
        raise OSError(errno.ETIMEDOUT, "inner absolute deadline is exhausted")
    records: list[dict[str, Any]] = []
    service: ServiceHandle | None = None
    target: TargetHandle | None = None
    child: ChildHandle | None = None
    # Target absence starts unknown/false, becomes true only after service
    # inspection proves the fixed sibling absent, and returns to false before
    # manager create issuance. Cleanup may set it true only through an
    # independent manager-unit plus path absence read.
    child_reaped = True
    target_is_absent = False
    target_manager_absence_proven = False
    service_handles_closed = False
    primary_substage = "INTERNAL"
    primary_error: BaseException | None = None
    attempt_publication = PublicationOwnershipToken(ATTEMPT_NAME)
    receipt_publication: PublicationOwnershipToken | None = None

    def stage(
        name: str, operation: Callable[[], Mapping[str, Any]]
    ) -> dict[str, Any]:
        nonlocal primary_substage, primary_error

        def fail(error: BaseException) -> None:
            nonlocal primary_substage, primary_error
            records.append(
                _substage_record(len(records), name, "FAILED", {}, error)
            )
            primary_substage = name
            primary_error = error

        try:
            if monotonic_ns() >= deadline_ns:
                raise OSError(
                    errno.ETIMEDOUT,
                    f"{name} exhausted the inner process absolute deadline",
                )
            result = operation()
            if monotonic_ns() >= deadline_ns:
                if (
                    name == "TARGET_CREATE"
                    and isinstance(target, TargetHandle)
                    and target.owned is True
                    and target.manager_created is True
                    and target.identity_continuous is True
                    and target.residual_possible is False
                    and type(target.device) is int
                    and target.device >= 0
                    and type(target.inode) is int
                    and target.inode > 0
                ):
                    raise TargetPostClaimDeadlineError(target)
                if (
                    name == "CLONE3_ATOMIC_BIRTH"
                    and isinstance(child, ChildHandle)
                    and type(child.pid) is int
                    and child.pid > 0
                    and type(child.pidfd) is int
                    and child.pidfd >= 0
                ):
                    raise ClonePostAcquireDeadlineError(child)
                raise OSError(
                    errno.ETIMEDOUT,
                    f"{name} crossed the inner process absolute deadline",
                )
        except BaseException as error:
            fail(error)
            raise
        try:
            detail = dict(result)
            candidate = _substage_record(len(records), name, "OK", detail)
            _validate_success_substage_prefix(
                [*records, candidate],
                attempt=attempt,
                authority=authority,
            )
        except BaseException as validation_error:
            marker: BaseException = validation_error
            if (
                isinstance(
                    validation_error, (AuthorityError, TypeError, ValueError)
                )
                and name == "TARGET_CREATE"
                and isinstance(target, TargetHandle)
                and target.owned is True
                and target.manager_created is True
                and target.identity_continuous is True
                and target.residual_possible is False
                and type(target.device) is int
                and target.device >= 0
                and type(target.inode) is int
                and target.inode > 0
            ):
                marker = TargetPostClaimValidationError(target)
            elif (
                isinstance(
                    validation_error, (AuthorityError, TypeError, ValueError)
                )
                and name == "CLONE3_ATOMIC_BIRTH"
                and isinstance(child, ChildHandle)
                and type(child.pid) is int
                and child.pid > 0
                and type(child.pidfd) is int
                and child.pidfd >= 0
            ):
                marker = ClonePostAcquireValidationError(child)
            fail(marker)
            if marker is validation_error:
                raise
            raise marker from validation_error
        records.append(candidate)
        return detail

    try:
        try:
            claim_attempt(
                store,
                attempt,
                token=attempt_publication,
            )
        except BaseException as error:
            if not attempt_publication.path_created:
                raise
            records.append(
                _substage_record(
                    len(records), "ATTEMPT_PUBLICATION", "FAILED", {}, error
                )
            )
            primary_substage = "ATTEMPT_PUBLICATION"
            primary_error = error
            raise
        records.append(
            _substage_record(
                len(records),
                "ATTEMPT_PUBLICATION",
                "OK",
                {
                    "probe_attempt_id": attempt["probe_attempt_id"],
                    "o_excl_owned": True,
                    "canonical_durable_readback": True,
                },
            )
        )
        stage(
            "OUTER_CONTEXT",
            lambda: {
                "external_root_id": authority["external_root_id"],
                "external_root_sha256": external_sha,
                "service_type": invocation["service_type"],
                "delegate": invocation["delegate"],
                "scope": invocation["scope"],
                    "clean_environment": True,
                    "probe_process_entry_monotonic_ns": process_entry_ns,
                    "probe_started_monotonic_ns": started_ns,
                    "probe_deadline_monotonic_ns": deadline_ns,
                    "inner_total_timeout_ns": INNER_TOTAL_TIMEOUT_NS,
                    "inner_git_call_count": INNER_GIT_CALL_COUNT,
                    "git_process_total_bound_seconds": (
                        GIT_PROCESS_TOTAL_BOUND_SECONDS
                    ),
                    "target_token": TARGET_TOKEN,
                    "target_unit_name": TARGET_SERVICE_UNIT_NAME,
                    "target_lifecycle_authority": (
                        "SYSTEMD_USER_MANAGER_ONLY"
                    ),
                    "target_manager_call_timeout_seconds": (
                        TARGET_MANAGER_CALL_TIMEOUT_SECONDS
                    ),
                    "target_manager_process_total_bound_seconds": (
                        TARGET_MANAGER_PROCESS_TOTAL_BOUND_SECONDS
                    ),
                    "target_manager_max_polls": TARGET_MANAGER_MAX_POLLS,
                    "toolchain_revalidated": True,
                    "umask": REQUIRED_UMASK,
            },
        )
        service_result: tuple[ServiceHandle, dict[str, Any]] | None = None

        def inspect_service() -> Mapping[str, Any]:
            nonlocal service, service_result
            service_result = runtime.inspect_service(authority, deadline_ns)
            service_candidate, detail = service_result
            service = (
                service_candidate
                if isinstance(service_candidate, ServiceHandle)
                else None
            )
            if (
                service is None
                or type(detail) is not dict
                or detail.get("fixed_target_absent_before_create") is not True
                or detail.get("target_manager_absent_before_create") is not True
            ):
                raise OSError(
                    errno.EPROTO,
                    "service inspection did not prove manager and path absence",
                )
            return detail

        stage("SERVICE_PLACEMENT_AND_NCA_PERMISSION", inspect_service)
        target_is_absent = True
        target_manager_absence_proven = True
        assert service is not None

        def create_target() -> Mapping[str, Any]:
            nonlocal target, target_is_absent
            nonlocal target_manager_absence_proven
            target_is_absent = False
            target_manager_absence_proven = False
            try:
                target_candidate, detail = runtime.create_target(
                    service, deadline_ns
                )
            except TargetCreationError as error:
                target = (
                    error.target
                    if isinstance(error.target, TargetHandle)
                    else None
                )
                raise
            target = (
                target_candidate
                if isinstance(target_candidate, TargetHandle)
                else None
            )
            if (
                target is None
                or target.owned is not True
                or target.manager_created is not True
                or target.identity_continuous is not True
                or target.residual_possible is not False
                or type(target.device) is not int
                or target.device < 0
                or type(target.inode) is not int
                or target.inode <= 0
            ):
                raise OSError(
                    errno.EPROTO,
                    "target create did not return one continuous manager claim",
                )
            return detail

        stage("TARGET_CREATE", create_target)
        assert target is not None

        def clone_child() -> Mapping[str, Any]:
            nonlocal child, child_reaped
            child_reaped = False
            child, detail = runtime.clone_child(target, deadline_ns)
            if not isinstance(child, ChildHandle):
                raise OSError(errno.EPROTO, "clone adapter omitted child ownership")
            return detail

        stage("CLONE3_ATOMIC_BIRTH", clone_child)
        assert child is not None
        handshake = stage(
            "CHILD_HANDSHAKE", lambda: runtime.receive_handshake(child, deadline_ns)
        )
        child_identity = stage(
            "PIDFD_AND_MEMBERSHIP", lambda: runtime.inspect_child(child, target)
        )
        def compare_membership() -> Mapping[str, Any]:
            if handshake.get("membership_line") != child_identity.get(
                "membership_line"
            ):
                raise OSError(
                    errno.EXDEV, "handshake and observer membership disagree"
                )
            return {
                "membership_line": child_identity["membership_line"],
                "independent_observations_agree": True,
            }

        stage("HANDSHAKE_MEMBERSHIP_CONSISTENCY", compare_membership)
        stage("CHILD_RELEASE", lambda: runtime.release_child(child))
        stage("CHILD_EXIT_ZERO", lambda: runtime.reap_exit_zero(child, deadline_ns))
        child_reaped = True
        stage(
            "CHILD_HANDLE_CLOSE",
            lambda: (
                runtime.close_child(child),
                {"child_handle_closed": True},
            )[1],
        )
        stage("TARGET_EMPTY", lambda: runtime.target_empty(target))
        def remove_target() -> Mapping[str, Any]:
            detail = runtime.remove_target(service, target, deadline_ns)
            return _validated_target_removal_detail(target, detail)

        stage("TARGET_REMOVE", remove_target)
        absent_detail = stage(
            "TARGET_ABSENT",
            lambda: _validated_target_absence_detail(
                runtime.target_absent(service, target, deadline_ns)
            ),
        )
        target_is_absent = True
        target_manager_absence_proven = True

        def close_service() -> Mapping[str, Any]:
            nonlocal service_handles_closed
            runtime.close_service(service)
            service_handles_closed = True
            return {"service_handles_closed": True}

        stage("SERVICE_HANDLE_CLOSE", close_service)
        try:
            receipt = _build_receipt(
                attempt, authority, records, target=target
            )
            validate_receipt_document(receipt, attempt, authority)
            receipt_raw = canonical_json_bytes(receipt)
            store.require_inventory(
                _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME),
                phase="INNER_BEFORE_RECEIPT_PUBLICATION",
            )
        except BaseException as error:
            records.append(
                _substage_record(
                    len(records), "RECEIPT_BUILD", "FAILED", {}, error
                )
            )
            primary_substage = "RECEIPT_BUILD"
            primary_error = error
            raise
        if monotonic_ns() >= deadline_ns:
            error = OSError(
                errno.ETIMEDOUT,
                "RECEIPT_PUBLICATION exhausted the inner process absolute "
                "deadline before O_EXCL",
            )
            records.append(
                _substage_record(
                    len(records), "RECEIPT_PUBLICATION", "FAILED", {}, error
                )
            )
            primary_substage = "RECEIPT_PUBLICATION"
            primary_error = error
            raise error
        receipt_publication = PublicationOwnershipToken(RECEIPT_NAME)
        try:
            store.write_once(
                RECEIPT_NAME,
                receipt_raw,
                token=receipt_publication,
            )
            store.require_inventory(
                _root_inventory(
                    OUTER_LAUNCH_ATTEMPT_NAME,
                    ATTEMPT_NAME,
                    RECEIPT_NAME,
                ),
                phase="INNER_RECEIPT_PUBLISHED",
            )
        except FileExistsError as error:
            raise ReceiptPublicationUncertain(
                "RECEIPT path exists; inner FAILURE publication is forbidden"
            ) from error
        except BaseException as error:
            if receipt_publication.path_created:
                try:
                    store.stabilize_exact(RECEIPT_NAME, receipt_raw)
                    store.require_inventory(
                        _root_inventory(
                            OUTER_LAUNCH_ATTEMPT_NAME,
                            ATTEMPT_NAME,
                            RECEIPT_NAME,
                        ),
                        phase="INNER_RECEIPT_RECOVERED",
                    )
                except BaseException as recovery_error:
                    raise ReceiptPublicationUncertain(
                        "RECEIPT O_EXCL occurred but exact durability "
                        "recovery did not complete"
                    ) from recovery_error
            else:
                records.append(
                    _substage_record(
                        len(records),
                        "RECEIPT_PUBLICATION",
                        "FAILED",
                        {},
                        error,
                    )
                )
                primary_substage = "RECEIPT_PUBLICATION"
                primary_error = error
                raise
        if monotonic_ns() >= deadline_ns:
            raise ReceiptPublicationUncertain(
                "exact RECEIPT publication completed at or after the inner "
                "process absolute deadline"
            )
        return receipt
    except ReceiptPublicationUncertain:
        raise
    except BaseException as error:
        if not attempt_publication.path_created:
            raise
        if receipt_publication is not None and receipt_publication.path_created:
            raise ReceiptPublicationUncertain(
                "RECEIPT ownership forbids inner FAILURE after later exception"
            ) from error
        if primary_error is None:
            primary_error = error
        if not any(
            row["status"] == "FAILED"
            and row["substage"] == primary_substage
            for row in records
        ):
            records.append(
                _substage_record(
                    len(records), primary_substage, "FAILED", {}, primary_error
                )
            )
        cleanup_deadline = deadline_ns
        primary_index = next(
            index
            for index, row in enumerate(records)
            if row["status"] == "FAILED"
            and row["substage"] == primary_substage
        )
        primary_record = records[primary_index]
        cleanup_success_details = _validate_success_substage_prefix(
            records[:primary_index], attempt=attempt, authority=authority
        )

        def cleanup_stage(
            name: str, operation: Callable[[], Mapping[str, Any]]
        ) -> Mapping[str, Any] | None:
            try:
                detail = dict(operation())
                candidate = _substage_record(
                    len(records), name, "OK", detail
                )
                _validate_cleanup_detail(
                    candidate,
                    details=cleanup_success_details,
                    primary=primary_record,
                    authority=authority,
                )
            except BaseException as cleanup_error:
                records.append(
                    _substage_record(
                        len(records), name, "FAILED", {}, cleanup_error
                    )
                )
                return None
            records.append(candidate)
            return detail

        child_cleanup_authorized = isinstance(child, ChildHandle) and (
            any(
                row["status"] == "OK"
                and row["substage"] == "CLONE3_ATOMIC_BIRTH"
                for row in records
            )
            or isinstance(
                primary_error,
                (
                    ClonePostAcquireValidationError,
                    ClonePostAcquireDeadlineError,
                ),
            )
        )
        if child_cleanup_authorized:
            assert child is not None
            cleanup_stage("CLEANUP_PIDFD_KILL", lambda: runtime.kill_child(child))
            reap_detail = cleanup_stage(
                "CLEANUP_CHILD_REAP",
                lambda: runtime.reap_cleanup(child, cleanup_deadline),
            )
            child_reaped = child.reaped or reap_detail is not None
            cleanup_stage(
                "CLEANUP_CHILD_CLOSE",
                lambda: (
                    runtime.close_child(child),
                    {"child_handle_closed": True},
                )[1],
            )
        if isinstance(service, ServiceHandle) and not service_handles_closed:
            if target_is_absent and target_manager_absence_proven:
                records.append(
                    _substage_record(
                        len(records),
                        "CLEANUP_TARGET_REMOVE",
                        "OK",
                        {
                            "manager_stop_attempted": False,
                            "reason": "MANAGER_ABSENCE_ALREADY_PROVEN",
                            "probe_path_deletion_calls": 0,
                        },
                    )
                )
            elif (
                isinstance(target, TargetHandle)
                and target.owned is True
                and target.manager_created is True
                and target.identity_continuous is True
                and target.residual_possible is False
                and (
                    any(
                        row["status"] == "OK"
                        and row["substage"] == "TARGET_CREATE"
                        for row in records
                    )
                    or isinstance(
                        primary_error,
                        (
                            TargetPostClaimValidationError,
                            TargetPostClaimDeadlineError,
                        ),
                    )
                )
            ):
                cleanup_stage(
                    "CLEANUP_TARGET_REMOVE",
                    lambda: _validated_target_removal_detail(
                        target,
                        runtime.remove_target(
                            service, target, cleanup_deadline
                        ),
                    ),
                )
            else:
                records.append(
                    _substage_record(
                        len(records),
                        "CLEANUP_TARGET_REMOVE",
                        "OK",
                        {
                            "manager_stop_attempted": False,
                            "reason": "NO_CONTINUOUS_MANAGER_OWNERSHIP_CLAIM",
                            "probe_path_deletion_calls": 0,
                        },
                    )
                )

            def cleanup_absence() -> Mapping[str, Any]:
                if isinstance(target, TargetHandle) and (
                    target.identity_continuous is not True
                    or target.residual_possible is True
                ):
                    raise OSError(
                        errno.ESTALE,
                        "target identity is discontinuous or residual is possible",
                    )
                return _validated_target_absence_detail(
                    runtime.target_absent(
                        service, target, cleanup_deadline
                    )
                )

            absent_detail = cleanup_stage(
                "CLEANUP_TARGET_ABSENT",
                cleanup_absence,
            )
            target_is_absent = (
                absent_detail is not None
                and absent_detail.get("target_absent") is True
            )
            target_manager_absence_proven = (
                target_is_absent
                and absent_detail is not None
                and absent_detail.get("manager_absence_proven") is True
            )
            target_is_absent = (
                target_is_absent and target_manager_absence_proven
            )
            cleanup_stage(
                "CLEANUP_SERVICE_CLOSE",
                lambda: (
                    runtime.close_service(service),
                    {"service_handles_closed": True},
                )[1],
            )
        elif service_handles_closed:
            records.append(
                _substage_record(
                    len(records),
                    "CLEANUP_SERVICE_ALREADY_CLOSED",
                    "OK",
                    {
                        "target_absence_preserved": target_is_absent,
                        "manager_absence_preserved": (
                            target_manager_absence_proven
                        ),
                        "probe_path_deletion_calls": 0,
                    },
                )
            )
        failure = _build_failure(
            attempt,
            authority,
            records,
            primary_substage=primary_substage,
            primary_error=primary_error,
        )
        validate_failure_document(failure, attempt, authority)
        store.require_inventory(
            _root_inventory(OUTER_LAUNCH_ATTEMPT_NAME, ATTEMPT_NAME),
            phase="INNER_BEFORE_FAILURE_PUBLICATION",
            allow_partial_names=frozenset({ATTEMPT_NAME}),
        )
        failure_publication = PublicationOwnershipToken(FAILURE_NAME)
        try:
            store.write_once(
                FAILURE_NAME,
                canonical_json_bytes(failure),
                token=failure_publication,
            )
        except FileExistsError as write_error:
            raise ReplayForbidden("preflight FAILURE O_EXCL lost") from write_error
        store.require_inventory(
            _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME,
                ATTEMPT_NAME,
                FAILURE_NAME,
            ),
            phase="INNER_FAILURE_PUBLISHED",
            allow_partial_names=frozenset({ATTEMPT_NAME}),
        )
        raise ProbeRunFailure(failure) from error


def _repository_root_from_running_source() -> Path:
    repository_root = Path(__file__).resolve().parents[1]
    expected = repository_root / PROBE_SOURCE_RELATIVE_PATH
    if expected.resolve() != Path(__file__).resolve():
        _fail("running source left its exact repository location")
    return _canonical_repository_root(repository_root)


def run_prepare_mode(
    *, process_entry_ns: int | None = None, deadline_ns: int | None = None
) -> dict[str, Any]:
    observed_ns = time.monotonic_ns()
    process_entry_ns = observed_ns if process_entry_ns is None else process_entry_ns
    deadline_ns = (
        process_entry_ns + PREPARE_TOTAL_CAP_SECONDS * 1_000_000_000
        if deadline_ns is None
        else deadline_ns
    )
    if (
        type(process_entry_ns) is not int
        or type(deadline_ns) is not int
        or process_entry_ns > observed_ns
        or deadline_ns - process_entry_ns
        != PREPARE_TOTAL_CAP_SECONDS * 1_000_000_000
    ):
        _fail("prepare process-entry deadline contract changed")
    _require_before_deadline(deadline_ns, "prepare runtime gate")
    result = prepare_external_root_once(
        _repository_root_from_running_source(),
        git_stdout=_deadline_git_observer(deadline_ns),
        deadline_ns=deadline_ns,
    )
    _require_before_deadline(deadline_ns, "prepare terminal serialization")
    return result


def run_launch_mode(
    *, process_entry_ns: int | None = None, deadline_ns: int | None = None
) -> dict[str, Any]:
    observed_ns = time.monotonic_ns()
    process_entry_ns = observed_ns if process_entry_ns is None else process_entry_ns
    deadline_ns = (
        process_entry_ns + FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
        if deadline_ns is None
        else deadline_ns
    )
    if (
        type(process_entry_ns) is not int
        or type(deadline_ns) is not int
        or process_entry_ns > observed_ns
        or deadline_ns - process_entry_ns
        != FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
    ):
        _fail("formal process-entry deadline contract changed")
    _require_before_deadline(deadline_ns, "formal runtime gate")
    repository_root = _repository_root_from_running_source()
    authority, external_raw = load_external_root_for_outer(
        repository_root,
        git_stdout=_deadline_git_observer(deadline_ns),
    )
    _require_before_deadline(deadline_ns, "outer prework")
    artifact_root = Path(
        authority["systemd_invocation_contract"]["artifact_root"]
    )
    with DurableArtifactStore(artifact_root) as store:
        return run_outer_launch_once(
            authority=authority,
            external_root_raw=external_raw,
            store=store,
            process_adapter=DEFAULT_SUBPROCESS_ADAPTER,
            absence_observer=SystemdCgroupAbsenceObserver(),
            formal_process_entry_ns=process_entry_ns,
            deadline_ns=deadline_ns,
        )


def run_probe_mode(
    *, process_entry_ns: int | None = None, deadline_ns: int | None = None
) -> dict[str, Any]:
    observed_ns = time.monotonic_ns()
    process_entry_ns = observed_ns if process_entry_ns is None else process_entry_ns
    deadline_ns = (
        process_entry_ns + INNER_TOTAL_TIMEOUT_NS
        if deadline_ns is None
        else deadline_ns
    )
    if (
        type(process_entry_ns) is not int
        or type(deadline_ns) is not int
        or process_entry_ns > observed_ns
        or deadline_ns - process_entry_ns != INNER_TOTAL_TIMEOUT_NS
    ):
        _fail("inner process-entry deadline contract changed")
    _require_before_deadline(deadline_ns, "inner runtime gate")
    authority, external_raw = load_external_root_from_clean_environment(
        dict(os.environ),
        git_stdout=_deadline_git_observer(deadline_ns),
    )
    _require_before_deadline(deadline_ns, "inner source replay")
    artifact_root = Path(
        authority["systemd_invocation_contract"]["artifact_root"]
    )
    with DurableArtifactStore(artifact_root) as store:
        return run_probe_once(
            authority=authority,
            external_root_raw=external_raw,
            store=store,
            runtime=LinuxRuntimeAdapter(),
            environ=dict(os.environ),
            process_entry_ns=process_entry_ns,
            deadline_ns=deadline_ns,
        )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments not in (["--prepare"], ["--launch"], ["--probe"]):
        sys.stderr.write(
            "exact invocation requires one of --prepare, --launch, or --probe\n"
        )
        return 2
    process_entry_ns = time.monotonic_ns()
    total_cap_seconds = {
        "--prepare": PREPARE_TOTAL_CAP_SECONDS,
        "--launch": FORMAL_TOTAL_CAP_SECONDS,
        "--probe": INNER_TOTAL_TIMEOUT_SECONDS,
    }[arguments[0]]
    deadline_ns = process_entry_ns + total_cap_seconds * 1_000_000_000
    try:
        validate_runtime_contract(arguments[0])
        _require_before_deadline(deadline_ns, "runtime contract validation")
        if arguments == ["--prepare"]:
            terminal = run_prepare_mode(
                process_entry_ns=process_entry_ns, deadline_ns=deadline_ns
            )
        elif arguments == ["--launch"]:
            terminal = run_launch_mode(
                process_entry_ns=process_entry_ns, deadline_ns=deadline_ns
            )
        else:
            terminal = run_probe_mode(
                process_entry_ns=process_entry_ns, deadline_ns=deadline_ns
            )
        sys.stdout.buffer.write(canonical_json_bytes(terminal) + b"\n")
        return 0
    except ReplayForbidden as error:
        sys.stderr.write(f"replay forbidden: {error}\n")
        return 3
    except ProbeRunFailure as error:
        sys.stderr.write(
            "preflight failure: "
            + str(error.failure_document.get("preflight_failure_id"))
            + "\n"
        )
        return 1
    except OuterLaunchFailure as error:
        sys.stderr.write(
            "outer launch failure: "
            + str(error.failure_document.get("outer_launch_failure_id"))
            + "\n"
        )
        return 1
    except OuterLaunchFailurePublicationUncertain as error:
        sys.stderr.write(
            "outer launch failure publication uncertain: " + str(error) + "\n"
        )
        return 2
    except PrepareRunFailure as error:
        sys.stderr.write(
            "prepare failure: "
            + str(error.failure_document.get("prepare_failure_id"))
            + "\n"
        )
        return 1
    except PrepareFailurePublicationUncertain as error:
        sys.stderr.write(
            "prepare failure publication uncertain: " + str(error) + "\n"
        )
        return 2
    except BaseException as error:
        error_type, message, error_number, error_name = _bounded_error(error)
        sys.stderr.write(
            f"preflight authority failure: {error_type}: {message}; "
            f"errno={error_number}; errno_name={error_name}\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
