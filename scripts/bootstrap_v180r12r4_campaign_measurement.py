#!/usr/bin/python3
"""Execute a V180r12r4 runner from an externally bound source snapshot.

The launch manifest and its digest are materialized outside this bootstrap after
the C_pre copy exists.  Mutation after that external snapshot is deliberately
outside this bootstrap's claim.  Before executing any ``acfqp`` code, the
bootstrap verifies and compiles the complete manifest-listed source closure and
the selected runner, then serves ``acfqp`` imports only from those in-memory
code objects.
"""

from __future__ import annotations

import hashlib
import importlib.abc
import importlib.util
import ast
import fcntl
import io
import json
import marshal
import os
from pathlib import Path, PurePosixPath
import re
import socket
import stat
import subprocess
import sys
import sysconfig
import time
import tokenize
import types


_SCHEMA = "acfqp.v180r12r4_source_bound_launch_manifest.v1"
_MANIFEST_SHA_ENV = "ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256"
_PREREG_COMMIT_ENV = "ACFQP_V180R12R4_PREREG_COMMIT"
_EXPECTED_EXECUTABLE = "/usr/bin/python3"
_EXPECTED_GIT_EXECUTABLE = "/usr/bin/git"
_EXPECTED_PYCACHE_PREFIX = "/dev/null/v180r12r4"
_MANIFEST_SHA_TEMPLATE = "__V180R12R4_MANIFEST_SHA256__"
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_BOOTSTRAP_BYTE_CAP = 1024 * 1024
_MANIFEST_BYTE_CAP = 16 * 1024 * 1024
_RUNNER_BYTE_CAP = 4 * 1024 * 1024
_EXECUTABLE_BYTE_CAP = 64 * 1024 * 1024
_SOURCE_FILE_BYTE_CAP = 8 * 1024 * 1024
_SOURCE_CLOSURE_FILE_CAP = 4096
_SOURCE_CLOSURE_TOTAL_BYTE_CAP = 128 * 1024 * 1024
_EXPECTED_FLAGS = {
    "isolated": 1,
    "no_site": 1,
    "no_user_site": 1,
    "ignore_environment": 1,
    "dont_write_bytecode": 1,
}
_ORIG_ARGV_PREFIX = [
    _EXPECTED_EXECUTABLE,
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={_EXPECTED_PYCACHE_PREFIX}",
]
_TARGET_RUNNER_PATHS = {
    "measurement": "scripts/run_v180r12r4_campaign_measurement.py",
    "verification": "scripts/verify_v180r12r4_campaign_measurement.py",
    "supervisor": "scripts/supervise_v180r12r4_campaign_measurement.py",
    "worker": "scripts/work_v180r12r4_campaign_measurement.py",
}
_RUNNER_MODULE_NAMES = {
    target: f"_acfqp_v180r12r4_precompiled_runner_{target}"
    for target in _TARGET_RUNNER_PATHS
}
_RUNNER_MODULE_METADATA_FIELDS = (
    "__name__",
    "__file__",
    "__package__",
    "__cached__",
    "__loader__",
    "__spec__",
)
_EXTERNAL_TARGETS = ("measurement", "verification")
_INTERNAL_TARGETS = ("supervisor", "worker")
_MEASURED_TARGETS = ("measurement", "supervisor", "worker")
_PRECOMPILED_BUNDLE_FD = 240
_INTERNAL_IPC_FD = 241
_INTERNAL_MAC_KEY_FD = 242
_INTERNAL_CONTEXT_FD = 243
_SUPERVISOR_REPOSITORY_ROOT_FD = 244
_SUPERVISOR_WORKER_CGROUP_FD = 245
_WORKER_TERMINAL_STAGE_FD = 246
_WORKER_VERIFICATION_STAGE_FD = 247
_WORKER_SUBJECT_RESULT_FD = 248
_SOCK_SEQPACKET_BUFFER_REQUEST_BYTES = 1 * 1024 * 1024
_SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES = (
    2 * _SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
)
_REQUIRED_MEMFD_SEALS = tuple(
    sorted(
        (
            fcntl.F_SEAL_SEAL,
            fcntl.F_SEAL_SHRINK,
            fcntl.F_SEAL_GROW,
            fcntl.F_SEAL_WRITE,
        )
    )
)
_REQUIRED_MEMFD_SEAL_MASK = sum(_REQUIRED_MEMFD_SEALS)
_PRECOMPILED_BUNDLE_SCHEMA = "acfqp.v180r12r4_precompiled_source_bundle.v1"
_INTERNAL_CONTEXT_SCHEMA = "acfqp.v180r12r4_internal_launch_context.v1"
_INTERNAL_CONTEXT_MAC_ALGORITHM = "BLAKE2S_KEYED_256"
_EXTERNAL_CONTEXT_FD = 249
_DELEGATED_CGROUP_PARENT_FD = 250
_CGROUP2_MOUNT_FD = 251
_SOURCE_SYSTEMD_SERVICE_FD = 252
_EXTERNAL_CONTEXT_BYTE_CAP = 2 * 1024 * 1024
_EXTERNAL_CONTEXT_SCHEMA = "acfqp.v180r12r4_external_launch_context.v1"
_VERIFIED_EXTERNAL_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_verified_external_launch_context.v1"
)
_PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN = (
    "acfqp:construction-k7-production-transient-service-token:v180r12r4"
)
_PRODUCTION_TRANSIENT_SERVICE_ROWS = {
    "measurement": (
        "36ed4564c6b1e77e08ee99aac354f4fc9bc5aaa67b3ac0f6bf16e69996d338bf",
        "acfqp-v180r12r4-measurement-"
        "36ed4564c6b1e77e08ee99aac354f4fc9bc5aaa67b3ac0f6bf16e69996d338bf.service",
    ),
    "verification": (
        "77ab2901813ffcf1c297ad6ed041b8f5147d390d2adb0f95dc978cce2b54e6be",
        "acfqp-v180r12r4-verification-"
        "77ab2901813ffcf1c297ad6ed041b8f5147d390d2adb0f95dc978cce2b54e6be.service",
    ),
}
_PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t1.v1"
)
_PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS = {
    "schema", "token_domain", "target", "token_input", "token",
    "unit_name", "unit_kind", "slice", "service_type", "delegate", "umask",
    "launcher_command", "systemd_run_argv",
}
_PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS = {
    "schema", "target", "token", "unit_name", "slice",
    "source_membership", "expected_source_membership", "self_pid",
    "self_pid_in_source_cgroup_procs", "cgroup_namespace_inode",
    "delegated_parent_fd_fact", "cgroup2_mount_fd_fact",
    "source_service_fd_fact", "nearest_common_ancestor_path",
    "nearest_common_ancestor_is_app_slice",
    "parent_cgroup_procs_o_wronly_openable",
    "planned_measurement_root_observation",
    "planned_measurement_root_absent", "t1_complete_before_child_popen",
}
_PLACEMENT_DIRECTORY_FD_FACT_FIELDS = {
    "fd", "role", "access", "path", "device", "inode", "mode",
    "owner_uid", "owner_gid", "nlink",
}
_ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA = (
    "acfqp.v180r12r4_atomic_cgroup_birth_preflight_receipt_interface.v1"
)
_FROZEN_AUTHORIZATION_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_frozen_authorization_context.v1"
)
_FROZEN_AUTHORIZATION_CONTEXT_FIELDS = (
    "schema", "protocol_id", "protocol_byte_count", "protocol_sha256",
    "authorization_id", "authorization_byte_count", "authorization_sha256",
    "authorization_evidence_id", "authorization_evidence_byte_count",
    "authorization_evidence_sha256", "campaign_measurement_execution_slot_id",
    "logical_occurrence_id", "execution_nonce", "campaign_attempt_id",
    "cgroup_parent_fact", "runtime_capability_fact",
)
_EXTERNAL_CONTEXT_FIELDS = (
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
    "inherited_fd_roles",
    "target_payload", "one_shot",
)
_CGROUP_PARENT_FACT_FIELDS = {
    "schema", "mount_point", "mount_fstype", "mount_device", "mount_inode",
    "mount_options", "parent_path", "parent_device", "parent_inode", "owner_uid",
    "owner_gid", "mode", "controllers", "subtree_control", "cgroup_type",
    "cgroup_namespace_inode", "cgroup_events_present", "memory_events_present",
    "pids_events_present", "cgroup_kill_present", "cgroup_procs_present",
    "memory_peak_present", "pids_peak_present", "self_membership",
}
_RUNTIME_CAPABILITY_FACT_FIELDS = {
    "schema", "machine_architecture", "single_threaded", "clone3_probe_errno",
    "clone3_syscall_recognized", "pidfd_send_signal_probe_errno",
    "pidfd_send_signal_recognized", "execveat_probe_errno", "execveat_recognized",
    "pidfd_wait_present", "landlock_abi", "uid", "gid",
    "effective_capability_mask", "admitted",
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
PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_pre_attempt_host_conformance.json"
)
PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA = (
    "acfqp.v180r12r4_pre_attempt_host_conformance.v1"
)
PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP = 65_536
_INTERNAL_FD_ROLE_MAP = {
    "supervisor": (
        (_PRECOMPILED_BUNDLE_FD, "PRECOMPILED_SOURCE_BUNDLE_MEMFD"),
        (_INTERNAL_IPC_FD, "OBSERVER_SUPERVISOR_SOCK_SEQPACKET"),
        (_INTERNAL_MAC_KEY_FD, "PARENT_TO_CHILD_MAC_KEY_MEMFD"),
        (_INTERNAL_CONTEXT_FD, "INTERNAL_LAUNCH_CONTEXT_MEMFD"),
        (_SUPERVISOR_REPOSITORY_ROOT_FD, "REPOSITORY_ROOT_O_PATH_DIRECTORY"),
        (_SUPERVISOR_WORKER_CGROUP_FD, "WORKER_CGROUP_DIRECTORY"),
    ),
    "worker": (
        (_PRECOMPILED_BUNDLE_FD, "PRECOMPILED_SOURCE_BUNDLE_MEMFD"),
        (_INTERNAL_IPC_FD, "SUPERVISOR_WORKER_SOCK_SEQPACKET"),
        (_INTERNAL_MAC_KEY_FD, "PARENT_TO_CHILD_MAC_KEY_MEMFD"),
        (_INTERNAL_CONTEXT_FD, "INTERNAL_LAUNCH_CONTEXT_MEMFD"),
        (_WORKER_TERMINAL_STAGE_FD, "TERMINAL_STAGE_READ_ONLY_MEMFD"),
        (_WORKER_VERIFICATION_STAGE_FD, "VERIFICATION_STAGE_READ_ONLY_MEMFD"),
        (_WORKER_SUBJECT_RESULT_FD, "SUBJECT_RESULT_WRITE_ONLY_FD"),
    ),
}
_INTERNAL_ACTOR_ROLE = {"supervisor": "SUPERVISOR", "worker": "WORKER"}
_INTERNAL_PARENT_ROLE = {"supervisor": "OBSERVER", "worker": "SUPERVISOR"}
_INTERNAL_FD_RULES = {
    "PRECOMPILED_SOURCE_BUNDLE_MEMFD": (
        "SEALED_MEMFD", "READ_ONLY", "0400", True
    ),
    "OBSERVER_SUPERVISOR_SOCK_SEQPACKET": (
        "SOCK_SEQPACKET", "READ_WRITE", None, False
    ),
    "SUPERVISOR_WORKER_SOCK_SEQPACKET": (
        "SOCK_SEQPACKET", "READ_WRITE", None, False
    ),
    "PARENT_TO_CHILD_MAC_KEY_MEMFD": (
        "SEALED_MEMFD", "READ_ONLY", "0400", True
    ),
    "INTERNAL_LAUNCH_CONTEXT_MEMFD": (
        "SEALED_MEMFD", "READ_ONLY", "0400", True
    ),
    "REPOSITORY_ROOT_O_PATH_DIRECTORY": (
        "DIRECTORY", "O_PATH", None, False
    ),
    "WORKER_CGROUP_DIRECTORY": (
        "DIRECTORY", "READ_ONLY", None, False
    ),
    "TERMINAL_STAGE_READ_ONLY_MEMFD": (
        "SEALED_MEMFD", "READ_ONLY", "0400", True
    ),
    "VERIFICATION_STAGE_READ_ONLY_MEMFD": (
        "SEALED_MEMFD", "READ_ONLY", "0400", True
    ),
    "SUBJECT_RESULT_WRITE_ONLY_FD": (
        "REGULAR_FILE", "WRITE_ONLY", "0600_PRECOMMIT", False
    ),
}
_INTERNAL_TARGET_CONTRACT = {
    "schema": "acfqp.v180r12r4_internal_bootstrap_target_contract.v1",
    "target_order": ["supervisor", "worker"],
    "initial_environment_keys": [_MANIFEST_SHA_ENV, "LC_CTYPE"],
    "injected_environment_key": _PREREG_COMMIT_ENV,
    "dynamic_identity_in_argv_or_environment": False,
    "context_schema": _INTERNAL_CONTEXT_SCHEMA,
    "context_mac_algorithm": _INTERNAL_CONTEXT_MAC_ALGORITHM,
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
    "precompiled_bundle_schema": _PRECOMPILED_BUNDLE_SCHEMA,
    "precompiled_before_campaign_attempt": True,
    "internal_target_reads_working_tree_source": False,
    "precompiled_runner_module_contract": {
        "module_type": "types.ModuleType",
        "target_order": list(_TARGET_RUNNER_PATHS),
        "target_rows": [
            {"target": target, "module_name": _RUNNER_MODULE_NAMES[target]}
            for target in _TARGET_RUNNER_PATHS
        ],
        "exact_metadata_fields": list(_RUNNER_MODULE_METADATA_FIELDS),
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
        _SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
    ),
    "sock_seqpacket_effective_min_bytes": (
        _SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
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
            "runner_relative_path": _TARGET_RUNNER_PATHS[target],
            "actor_role": _INTERNAL_ACTOR_ROLE[target],
            "parent_actor_role": _INTERNAL_PARENT_ROLE[target],
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
                    in {
                        "PARENT_TO_CHILD_MAC_KEY_MEMFD",
                        "INTERNAL_LAUNCH_CONTEXT_MEMFD",
                    },
                    "cloexec_at_runner_dispatch": role
                    not in {
                        "PARENT_TO_CHILD_MAC_KEY_MEMFD",
                        "INTERNAL_LAUNCH_CONTEXT_MEMFD",
                    },
                }
                for descriptor, role in _INTERNAL_FD_ROLE_MAP[target]
            ],
        }
        for target in _INTERNAL_TARGETS
    ],
    "inherited_descriptors_must_be_non_cloexec_at_bootstrap_exec": True,
    "bootstrap_entry_open_fd_inventory_is_exact": True,
    "key_and_context_descriptors_closed_before_runner_dispatch": True,
    "operational_descriptors_set_cloexec_before_runner_dispatch": True,
    "unlisted_internal_target_or_fd_role_forbidden": True,
}
_SOURCE_CLOSURE_REQUIRED_ROOTS = tuple(
    sorted(
        (
            "scripts/bootstrap_v180r12r4_campaign_measurement.py",
            "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py",
            "scripts/materialize_v180r12r4_campaign_measurement_prelaunch.py",
            _TARGET_RUNNER_PATHS["measurement"],
            "scripts/supervise_v180r12r4_campaign_measurement.py",
            _TARGET_RUNNER_PATHS["verification"],
            "scripts/work_v180r12r4_campaign_measurement.py",
            "src/acfqp/construction_accounting_registry_v6.py",
            "src/acfqp/construction_k7_domain_registry_extension_v180r12r4.py",
            "src/acfqp/construction_k7_domain_registry_extension_v180r12r4e.py",
            "src/acfqp/construction_k7_campaign_measurement_ledger_v180r12r4.py",
            "src/acfqp/construction_k7_campaign_measurement_protocol_v180r12r4.py",
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "execution_authorization_v180r12r4.py"
            ),
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "authorization_evidence_freeze_v180r12r4.py"
            ),
            "src/acfqp/construction_k7_campaign_measurement_supervisor_v180r12r4.py",
            "src/acfqp/construction_k7_campaign_measurement_worker_v180r12r4.py",
            "src/acfqp/construction_k7_campaign_measurement_finalizer_v180r12r4.py",
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
                "independent_verifier_v180r12r4.py"
            ),
            (
                "src/acfqp/construction_k7_ten_terminal_aggregation_"
                "production_evidence_freeze_v180r12r2.py"
            ),
        )
    )
)
_AUTHORIZATION_SELF_MODULE = (
    "acfqp."
    "construction_k7_campaign_measurement_execution_authorization_v180r12r4"
)
_AUTHORIZATION_EVIDENCE_MODULE = (
    "acfqp.construction_k7_campaign_measurement_"
    "authorization_evidence_freeze_v180r12r4"
)
_AUTHORIZATION_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_campaign_measurement_"
    "authorization_evidence_freeze_v180r12r4.py"
)
_WRAPPER_REDACTED_CONSTANT_NAMES = (
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
_WRAPPER_STRING_CONSTANT_NAMES = frozenset(
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
_WRAPPER_INTEGER_CONSTANT_NAMES = frozenset(
    {
        "EXPECTED_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
        "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
        "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
    }
)
_WRAPPER_REDACTED_STRING_LITERAL = (
    b'"0000000000000000000000000000000000000000000000000000000000000000"'
)
_WRAPPER_REDACTED_INTEGER_LITERAL = b"0"
_CLOSURE_KIND = (
    "EXACT_RAW_AUTHORIZATION_SOURCE_CLOSURE_PLUS_AUTH_SELF_AND_BOUND_RUNNERS"
)
_TOP_LEVEL_KEYS = {
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
_RAW_FACT_KEYS = {"relative_path", "byte_count", "sha256"}
_NORMALIZED_WRAPPER_FACT_KEYS = _RAW_FACT_KEYS | {
    "binding_kind",
    "redacted_constant_names",
}
_MODULE_FACT_KEYS = _RAW_FACT_KEYS | {"module", "is_package"}
_THIRD_PARTY_MODULE_FACT_KEYS = _MODULE_FACT_KEYS | {"source_root"}
_CLOSURE_KEYS = {
    "facts",
    "file_count",
    "total_byte_count",
    "facts_sha256",
}
_RUNTIME_KEYS = {
    "requested_executable",
    "resolved_executable",
    "executable_byte_count",
    "executable_sha256",
    "version",
    "version_info",
    "soabi",
    "base_sys_path",
    "orig_argv_prefix",
    "pycache_prefix",
    "flags",
}
_GIT_KEYS = {
    "requested_executable",
    "resolved_executable",
    "executable_mode",
    "executable_byte_count",
    "executable_sha256",
    "version_argv",
    "version_environment",
    "version_stdout",
    "runner_process_count",
    "runner_argv",
    "runner_environment_template",
}
_GIT_VERSION_ARGV = [_EXPECTED_GIT_EXECUTABLE, "--version"]
_GIT_VERSION_ENVIRONMENT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "LC_ALL": "C",
}
_GIT_SUBCOMMANDS = ("rev-parse", "log", "diff-tree", "log", "archive", "cat-file")
_FORBIDDEN_SITE_MODULES = frozenset({"site", "sitecustomize", "usercustomize"})
_STDLIB_MODULE_NAMES = frozenset(sys.stdlib_module_names)


def _require_exact_dict(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise RuntimeError(f"V180r12r4 {label} schema is not exact")
    return value


def _require_str(value: object, label: str) -> str:
    if type(value) is not str or not value:
        raise RuntimeError(f"V180r12r4 {label} is not a nonempty string")
    return value


def _require_sha256(value: object, label: str) -> str:
    text = _require_str(value, label)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise RuntimeError(f"V180r12r4 {label} is not lowercase SHA-256")
    return text


def _require_nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise RuntimeError(f"V180r12r4 {label} is not a nonnegative integer")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _require_source_bound_service_context_capture(
    cgroup_parent_fact: dict,
    runtime_capability_fact: dict,
) -> None:
    capture = {
        "capture_purpose": _SERVICE_CONTEXT_CAPTURE_PURPOSE,
        "cgroup_parent_fact": cgroup_parent_fact,
        "runtime_capability_fact": runtime_capability_fact,
        "schema": _SERVICE_CONTEXT_CAPTURE_SCHEMA,
    }
    raw = _canonical_json_bytes(capture) + b"\n"
    membership = cgroup_parent_fact.get("self_membership")
    parent_path = cgroup_parent_fact.get("parent_path")
    mount_point = cgroup_parent_fact.get("mount_point")
    if not (
        len(raw) == _SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest()
        == _SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256
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
        raise RuntimeError(
            "V180r12r4 frozen facts do not exact-join the source-bound "
            "service capture"
        )


def _validated_root(text: str, label: str) -> Path:
    root = Path(text)
    if not root.is_absolute() or str(root) != text:
        raise RuntimeError(f"V180r12r4 {label} must be an exact absolute path")
    try:
        metadata = os.lstat(root)
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise RuntimeError(f"V180r12r4 {label} is unavailable") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError(f"V180r12r4 {label} must be a nonsymlink directory")
    if resolved != root:
        raise RuntimeError(f"V180r12r4 {label} has a symlinked path component")
    return root


def _validated_relative_path(text: object, label: str) -> str:
    relative = _require_str(text, label)
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or str(pure) != relative
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise RuntimeError(f"V180r12r4 {label} is not a normalized relative path")
    return relative


def _stable_read(
    root: Path,
    relative: str,
    label: str,
    *,
    byte_cap: int,
    registered_size: int | None = None,
    expected_sha256: str | None = None,
) -> bytes:
    """Read one regular file beneath ``root`` without following symlinks."""

    if type(byte_cap) is not int or byte_cap <= 0:
        raise RuntimeError(f"V180r12r4 {label} byte cap is invalid")
    if registered_size is not None and (
        type(registered_size) is not int
        or registered_size < 0
        or registered_size > byte_cap
    ):
        raise RuntimeError(f"V180r12r4 {label} registered size exceeds its cap")
    if expected_sha256 is not None:
        expected_sha256 = _require_sha256(expected_sha256, f"{label} stream digest")
    relative = _validated_relative_path(relative, f"{label} relative path")
    parts = PurePosixPath(relative).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(root, directory_flags)
    try:
        for part in parts[:-1]:
            child = os.open(part, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(parts[-1], file_flags, dir_fd=descriptor)
    except OSError as error:
        raise RuntimeError(f"V180r12r4 {label} is unavailable or symlinked") from error
    finally:
        os.close(descriptor)

    try:
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(
                f"V180r12r4 {label} must be a singly linked regular file"
            )
        if before.st_size > byte_cap or (
            registered_size is not None and before.st_size != registered_size
        ):
            raise RuntimeError(
                f"V180r12r4 {label} size disagrees with its registered bound"
            )
        chunks: list[bytes] = []
        byte_count = 0
        digest = hashlib.sha256()
        while True:
            remaining = before.st_size - byte_count
            chunk = os.read(file_descriptor, min(1024 * 1024, remaining + 1))
            if not chunk:
                break
            byte_count += len(chunk)
            if byte_count > before.st_size or byte_count > byte_cap:
                raise RuntimeError(f"V180r12r4 {label} exceeded its read bound")
            digest.update(chunk)
            chunks.append(chunk)
        after = os.fstat(file_descriptor)
    finally:
        os.close(file_descriptor)

    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise RuntimeError(f"V180r12r4 {label} changed during stable read")
    raw = b"".join(chunks)
    if len(raw) != before.st_size:
        raise RuntimeError(f"V180r12r4 {label} byte count changed during stable read")
    if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
        raise RuntimeError(f"V180r12r4 {label} stream digest mismatch")
    return raw


def _relative_to_root(path_text: str, root: Path, label: str) -> str:
    path = Path(path_text)
    if not path.is_absolute() or str(path) != path_text:
        raise RuntimeError(f"V180r12r4 {label} must be an exact absolute path")
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"V180r12r4 {label} is outside its bound root") from error
    return _validated_relative_path(relative.as_posix(), f"{label} relative path")


def _verify_raw_fact(
    root: Path,
    fact: object,
    label: str,
    *,
    expected_relative_path: str | None = None,
    byte_cap: int,
) -> tuple[bytes, str]:
    fact = _require_exact_dict(fact, _RAW_FACT_KEYS, label)
    relative = _validated_relative_path(fact["relative_path"], f"{label} path")
    if expected_relative_path is not None and relative != expected_relative_path:
        raise RuntimeError(f"V180r12r4 {label} path changed")
    byte_count = _require_nonnegative_int(fact["byte_count"], f"{label} byte count")
    digest = _require_sha256(fact["sha256"], f"{label} digest")
    raw = _stable_read(
        root,
        relative,
        label,
        byte_cap=byte_cap,
        registered_size=byte_count,
        expected_sha256=digest,
    )
    if len(raw) != byte_count:
        raise RuntimeError(f"V180r12r4 {label} raw fact mismatch")
    return raw, relative


def _require_sanitized_environment() -> str:
    allowed = {_MANIFEST_SHA_ENV, "LC_CTYPE"}
    if set(os.environ) != allowed or os.environ.get("LC_CTYPE") != "C.UTF-8":
        raise RuntimeError("V180r12r4 bootstrap environment is not sanitized")
    return _require_sha256(
        os.environ.get(_MANIFEST_SHA_ENV), "launch manifest environment digest"
    )


def _normalize_authorization_evidence_wrapper(raw: bytes) -> bytes:
    """Redact exactly the twelve authorization wrapper literals by AST span."""

    try:
        tree = ast.parse(raw, filename=_AUTHORIZATION_EVIDENCE_RELATIVE_PATH)
    except (SyntaxError, ValueError) as error:
        raise RuntimeError("V180r12r4 wrapper AST is malformed") from error
    line_offsets = [0]
    for line in raw.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))
    wanted = set(_WRAPPER_REDACTED_CONSTANT_NAMES)
    assignments: dict[str, tuple[int, int, bytes]] = {}
    for statement in tree.body:
        name: str | None = None
        value: ast.expr | None = None
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            name = statement.targets[0].id
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            name = statement.target.id
            value = statement.value
        if name not in wanted:
            continue
        if name in assignments or value is None or not isinstance(value, ast.Constant):
            raise RuntimeError("V180r12r4 wrapper literal assignment changed")
        literal = value.value
        if name in _WRAPPER_STRING_CONSTANT_NAMES:
            if type(literal) is not str:
                raise RuntimeError("V180r12r4 wrapper string literal changed")
            replacement = _WRAPPER_REDACTED_STRING_LITERAL
            expected_token = tokenize.STRING
        elif name in _WRAPPER_INTEGER_CONSTANT_NAMES:
            if type(literal) is not int:
                raise RuntimeError("V180r12r4 wrapper integer literal changed")
            replacement = _WRAPPER_REDACTED_INTEGER_LITERAL
            expected_token = tokenize.NUMBER
        else:  # pragma: no cover - the two sets exactly partition the tuple.
            raise AssertionError
        positions = (
            value.lineno,
            value.col_offset,
            value.end_lineno,
            value.end_col_offset,
        )
        if not all(type(item) is int for item in positions):
            raise RuntimeError("V180r12r4 wrapper literal source span changed")
        start = line_offsets[value.lineno - 1] + value.col_offset
        end = line_offsets[value.end_lineno - 1] + value.end_col_offset
        if not (0 <= start < end <= len(raw)):
            raise RuntimeError("V180r12r4 wrapper literal source span is invalid")
        try:
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
        except (IndentationError, SyntaxError, tokenize.TokenError) as error:
            raise RuntimeError("V180r12r4 wrapper literal tokenization failed") from error
        if len(tokens) != 1 or tokens[0].type != expected_token:
            raise RuntimeError("V180r12r4 wrapper anchor is not one literal token")
        assignments[name] = (start, end, replacement)
    if set(assignments) != wanted or len(assignments) != 12:
        raise RuntimeError("V180r12r4 wrapper twelve-literal allowlist is incomplete")
    result = raw
    previous_start = len(raw)
    for start, end, replacement in sorted(
        assignments.values(), key=lambda item: item[0], reverse=True
    ):
        if end > previous_start:
            raise RuntimeError("V180r12r4 wrapper literal spans overlap")
        result = result[:start] + replacement + result[end:]
        previous_start = start
    return result


def _validated_raw_closure(value: object, label: str) -> list[dict]:
    closure = _require_exact_dict(value, _CLOSURE_KEYS, label)
    facts = closure["facts"]
    if type(facts) is not list or not facts:
        raise RuntimeError(f"V180r12r4 {label} facts are not a nonempty list")
    if len(facts) > _SOURCE_CLOSURE_FILE_CAP:
        raise RuntimeError(f"V180r12r4 {label} exceeds its file cap")
    checked: list[dict] = []
    for index, value in enumerate(facts):
        if type(value) is not dict:
            raise RuntimeError(f"V180r12r4 {label} fact {index} schema is not exact")
        relative_value = value.get("relative_path")
        expected_keys = (
            _NORMALIZED_WRAPPER_FACT_KEYS
            if relative_value == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH
            else _RAW_FACT_KEYS
        )
        fact = _require_exact_dict(value, expected_keys, f"{label} fact {index}")
        relative = _validated_relative_path(
            fact["relative_path"], f"{label} fact {index} path"
        )
        size = _require_nonnegative_int(
            fact["byte_count"], f"{label} fact {index} byte count"
        )
        if size > _SOURCE_FILE_BYTE_CAP:
            raise RuntimeError(f"V180r12r4 {label} fact {index} exceeds its file cap")
        checked_fact = {
            "relative_path": relative,
            "byte_count": size,
            "sha256": _require_sha256(
                fact["sha256"], f"{label} fact {index} digest"
            ),
        }
        if relative == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH:
            if (
                fact["binding_kind"]
                != "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
                or fact["redacted_constant_names"]
                != list(_WRAPPER_REDACTED_CONSTANT_NAMES)
            ):
                raise RuntimeError("V180r12r4 normalized wrapper fact changed")
            checked_fact.update(
                {
                    "binding_kind": fact["binding_kind"],
                    "redacted_constant_names": fact["redacted_constant_names"],
                }
            )
        checked.append(checked_fact)
    if [fact["relative_path"] for fact in checked] != sorted(
        {fact["relative_path"] for fact in checked}
    ):
        raise RuntimeError(f"V180r12r4 {label} facts are unsorted or duplicated")
    total = sum(fact["byte_count"] for fact in checked)
    if total > _SOURCE_CLOSURE_TOTAL_BYTE_CAP:
        raise RuntimeError(f"V180r12r4 {label} exceeds its aggregate byte cap")
    registered_count = _require_nonnegative_int(
        closure["file_count"], f"{label} file count"
    )
    registered_total = _require_nonnegative_int(
        closure["total_byte_count"], f"{label} total byte count"
    )
    registered_digest = _require_sha256(
        closure["facts_sha256"], f"{label} facts digest"
    )
    if not (
        registered_count == len(checked)
        and registered_total == total
        and registered_digest
        == hashlib.sha256(_canonical_json_bytes(checked)).hexdigest()
    ):
        raise RuntimeError(f"V180r12r4 {label} aggregate registration changed")
    return checked


def _validated_third_party_closure(value: object) -> list[dict]:
    label = "third-party source closure"
    closure = _require_exact_dict(value, _CLOSURE_KEYS, label)
    facts = closure["facts"]
    if type(facts) is not list or not facts:
        raise RuntimeError(f"V180r12r4 {label} facts are not a nonempty list")
    if len(facts) > _SOURCE_CLOSURE_FILE_CAP:
        raise RuntimeError(f"V180r12r4 {label} exceeds its file cap")
    checked: list[dict] = []
    for index, value in enumerate(facts):
        fact = _require_exact_dict(
            value, _THIRD_PARTY_MODULE_FACT_KEYS, f"{label} fact {index}"
        )
        module = _require_str(fact["module"], f"{label} fact {index} module")
        source_root = _require_str(
            fact["source_root"], f"{label} fact {index} source root"
        )
        relative = _validated_relative_path(
            fact["relative_path"], f"{label} fact {index} path"
        )
        size = _require_nonnegative_int(
            fact["byte_count"], f"{label} fact {index} byte count"
        )
        if size > _SOURCE_FILE_BYTE_CAP or type(fact["is_package"]) is not bool:
            raise RuntimeError(f"V180r12r4 {label} fact {index} exceeds its bound")
        checked.append(
            {
                "module": module,
                "is_package": fact["is_package"],
                "source_root": source_root,
                "relative_path": relative,
                "byte_count": size,
                "sha256": _require_sha256(
                    fact["sha256"], f"{label} fact {index} digest"
                ),
            }
        )
    if [fact["module"] for fact in checked] != sorted(
        {fact["module"] for fact in checked}
    ):
        raise RuntimeError(f"V180r12r4 {label} facts are unsorted or duplicated")
    total = sum(fact["byte_count"] for fact in checked)
    if total > _SOURCE_CLOSURE_TOTAL_BYTE_CAP:
        raise RuntimeError(f"V180r12r4 {label} exceeds its aggregate byte cap")
    registered_count = _require_nonnegative_int(
        closure["file_count"], f"{label} file count"
    )
    registered_total = _require_nonnegative_int(
        closure["total_byte_count"], f"{label} total byte count"
    )
    registered_digest = _require_sha256(
        closure["facts_sha256"], f"{label} facts digest"
    )
    if not (
        registered_count == len(checked)
        and registered_total == total
        and registered_digest
        == hashlib.sha256(_canonical_json_bytes(checked)).hexdigest()
    ):
        raise RuntimeError(f"V180r12r4 {label} aggregate registration changed")
    return checked


def _require_runtime_boundary(
    runtime_value: object,
    bootstrap_path: Path,
    target: str,
    repository_root: Path,
    c_pre_root: Path,
    manifest_path: Path,
) -> None:
    runtime = _require_exact_dict(runtime_value, _RUNTIME_KEYS, "runtime")
    if runtime["requested_executable"] != _EXPECTED_EXECUTABLE:
        raise RuntimeError("V180r12r4 requested interpreter changed")
    if sys.executable != _EXPECTED_EXECUTABLE:
        raise RuntimeError("V180r12r4 bootstrap requires /usr/bin/python3")
    if sys.pycache_prefix != _EXPECTED_PYCACHE_PREFIX or sys.dont_write_bytecode is not True:
        raise RuntimeError("V180r12r4 pycache boundary changed")
    actual_flags = {
        name: getattr(sys.flags, name) for name in _EXPECTED_FLAGS
    }
    manifest_flags = _require_exact_dict(
        runtime["flags"], set(_EXPECTED_FLAGS), "runtime flags"
    )
    if actual_flags != _EXPECTED_FLAGS or manifest_flags != _EXPECTED_FLAGS:
        raise RuntimeError("V180r12r4 runtime flags changed")
    if runtime["pycache_prefix"] != _EXPECTED_PYCACHE_PREFIX:
        raise RuntimeError("V180r12r4 runtime pycache prefix changed")

    expected_argv = [
        *_ORIG_ARGV_PREFIX,
        str(bootstrap_path),
        target,
        str(repository_root),
        str(c_pre_root),
        str(manifest_path),
    ]
    if runtime["orig_argv_prefix"] != _ORIG_ARGV_PREFIX or sys.orig_argv != expected_argv:
        raise RuntimeError("V180r12r4 exact original argv changed")
    if sys.argv != expected_argv[len(_ORIG_ARGV_PREFIX) :]:
        raise RuntimeError("V180r12r4 exact argv changed")

    base_sys_path = runtime["base_sys_path"]
    if (
        type(base_sys_path) is not list
        or not all(type(item) is str for item in base_sys_path)
        or sys.path != base_sys_path
    ):
        raise RuntimeError("V180r12r4 initial sys.path changed")
    if runtime["version"] != sys.version:
        raise RuntimeError("V180r12r4 interpreter version changed")
    version_info = runtime["version_info"]
    if type(version_info) is not list or version_info != list(sys.version_info):
        raise RuntimeError("V180r12r4 interpreter version info changed")
    if runtime["soabi"] != sysconfig.get_config_var("SOABI"):
        raise RuntimeError("V180r12r4 interpreter SOABI changed")

    resolved_text = _require_str(
        runtime["resolved_executable"], "resolved interpreter path"
    )
    resolved = Path(resolved_text)
    if not resolved.is_absolute() or str(resolved) != resolved_text:
        raise RuntimeError("V180r12r4 resolved interpreter path is not exact")
    try:
        actual_resolved = Path(sys.executable).resolve(strict=True)
    except OSError as error:
        raise RuntimeError("V180r12r4 interpreter cannot be resolved") from error
    if actual_resolved != resolved:
        raise RuntimeError("V180r12r4 resolved interpreter changed")
    interpreter_root = _validated_root("/", "interpreter filesystem root")
    interpreter_relative = _relative_to_root(
        str(resolved), interpreter_root, "resolved interpreter"
    )
    interpreter_raw = _stable_read(
        interpreter_root,
        interpreter_relative,
        "resolved interpreter",
        byte_cap=_EXECUTABLE_BYTE_CAP,
        registered_size=_require_nonnegative_int(
            runtime["executable_byte_count"], "interpreter byte count"
        ),
        expected_sha256=_require_sha256(
            runtime["executable_sha256"], "interpreter digest"
        ),
    )
    if (
        len(interpreter_raw)
        != runtime["executable_byte_count"]
    ):
        raise RuntimeError("V180r12r4 interpreter raw fact mismatch")

    dev_null = os.lstat("/dev/null")
    if (
        not stat.S_ISCHR(dev_null.st_mode)
        or os.major(dev_null.st_rdev) != 1
        or os.minor(dev_null.st_rdev) != 3
    ):
        raise RuntimeError("V180r12r4 /dev/null is not character device 1:3")


class _GitProcessAudit:
    def __init__(
        self,
        expected_argv: list[list[str]],
        expected_environment: dict[str, str],
    ) -> None:
        self._expected_argv = expected_argv
        self._expected_environment = expected_environment
        self._observed_count = 0

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        if event != "subprocess.Popen":
            return
        if self._observed_count >= len(self._expected_argv):
            raise RuntimeError("V180r12r4 foreign subprocess launch rejected")
        executable, argv, cwd, environment = arguments
        expected = self._expected_argv[self._observed_count]
        if not (
            executable == _EXPECTED_GIT_EXECUTABLE
            and argv == expected
            and cwd is None
            and environment == self._expected_environment
        ):
            raise RuntimeError(
                f"V180r12r4 Git process {self._observed_count} contract changed"
            )
        self._observed_count += 1

    def require_complete(self) -> None:
        if self._observed_count != len(self._expected_argv):
            raise RuntimeError("V180r12r4 six-process Git contract was incomplete")


def _validated_git_boundary(
    value: object,
    repository_root: Path,
    manifest_digest: str,
    commit_id: str,
) -> _GitProcessAudit:
    git = _require_exact_dict(value, _GIT_KEYS, "Git runtime")
    if git["requested_executable"] != _EXPECTED_GIT_EXECUTABLE:
        raise RuntimeError("V180r12r4 requested Git executable changed")
    resolved_text = _require_str(git["resolved_executable"], "resolved Git path")
    resolved = Path(resolved_text)
    try:
        actual_resolved = Path(_EXPECTED_GIT_EXECUTABLE).resolve(strict=True)
    except OSError as error:
        raise RuntimeError("V180r12r4 Git executable cannot be resolved") from error
    if not resolved.is_absolute() or str(resolved) != resolved_text or resolved != actual_resolved:
        raise RuntimeError("V180r12r4 resolved Git executable changed")
    size = _require_nonnegative_int(git["executable_byte_count"], "Git byte count")
    mode = _require_nonnegative_int(git["executable_mode"], "Git executable mode")
    filesystem_root = _validated_root("/", "Git filesystem root")
    relative = _relative_to_root(resolved_text, filesystem_root, "resolved Git executable")
    raw = _stable_read(
        filesystem_root,
        relative,
        "resolved Git executable",
        byte_cap=_EXECUTABLE_BYTE_CAP,
        registered_size=size,
        expected_sha256=_require_sha256(
            git["executable_sha256"], "Git executable digest"
        ),
    )
    metadata = os.lstat(resolved)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_mode != mode
    ):
        raise RuntimeError("V180r12r4 Git executable raw fact mismatch")

    if git["version_argv"] != _GIT_VERSION_ARGV:
        raise RuntimeError("V180r12r4 Git version argv changed")
    version_environment = _require_exact_dict(
        git["version_environment"], set(_GIT_VERSION_ENVIRONMENT), "Git version environment"
    )
    if version_environment != _GIT_VERSION_ENVIRONMENT:
        raise RuntimeError("V180r12r4 Git version environment changed")
    version_stdout = _require_str(git["version_stdout"], "Git version stdout")
    if len(version_stdout.encode("utf-8")) > 1024 or not version_stdout.endswith("\n"):
        raise RuntimeError("V180r12r4 Git version stdout exceeds its bound")
    try:
        completed = subprocess.run(
            _GIT_VERSION_ARGV,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            env=_GIT_VERSION_ENVIRONMENT,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError("V180r12r4 Git version verification failed") from error
    if not (
        completed.returncode == 0
        and completed.stderr == b""
        and completed.stdout == version_stdout.encode("utf-8")
    ):
        raise RuntimeError("V180r12r4 Git version identity changed")

    count = _require_nonnegative_int(git["runner_process_count"], "Git process count")
    argv_values = git["runner_argv"]
    if type(argv_values) is not list or count != 6 or len(argv_values) != count:
        raise RuntimeError("V180r12r4 Git process count changed")
    checked_argv: list[list[str]] = []
    for index, value in enumerate(argv_values):
        if (
            type(value) is not list
            or not all(type(item) is str and item and "\x00" not in item for item in value)
            or value[:3]
            != [_EXPECTED_GIT_EXECUTABLE, "-C", str(repository_root)]
            or len(value) < 4
            or value[3] != _GIT_SUBCOMMANDS[index]
        ):
            raise RuntimeError(f"V180r12r4 Git process {index} argv changed")
        checked_argv.append(value)

    environment_template = _require_exact_dict(
        git["runner_environment_template"],
        {
            _MANIFEST_SHA_ENV,
            _PREREG_COMMIT_ENV,
            "LC_CTYPE",
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_NOSYSTEM",
            "GIT_NO_REPLACE_OBJECTS",
            "GIT_OPTIONAL_LOCKS",
            "LC_ALL",
        },
        "Git runner environment template",
    )
    expected_template = {
        _MANIFEST_SHA_ENV: _MANIFEST_SHA_TEMPLATE,
        _PREREG_COMMIT_ENV: commit_id,
        "LC_CTYPE": "C.UTF-8",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
    }
    if environment_template != expected_template:
        raise RuntimeError("V180r12r4 Git runner environment template changed")
    expected_environment = dict(expected_template)
    expected_environment[_MANIFEST_SHA_ENV] = manifest_digest
    return _GitProcessAudit(checked_argv, expected_environment)


class _BoundSourceLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, records: dict[str, tuple[object, str, bool]]) -> None:
        self._records = records

    def find_spec(self, fullname: str, path=None, target=None):
        del path, target
        namespace = fullname.split(".", 1)[0]
        if namespace not in {"acfqp", "packaging", "tomli"}:
            return None
        if fullname not in self._records:
            raise ImportError(
                f"V180r12r4 unlisted bound module origin rejected: {fullname}"
            )
        _, source_path, is_package = self._records[fullname]
        return importlib.util.spec_from_loader(
            fullname,
            self,
            origin=source_path,
            is_package=is_package,
        )

    def create_module(self, spec):
        del spec
        return None

    def exec_module(self, module) -> None:
        code, source_path, is_package = self._records[module.__name__]
        module.__file__ = source_path
        module.__cached__ = None
        if is_package:
            module.__path__ = [str(Path(source_path).parent)]
        exec(code, module.__dict__)


class _BoundImportAudit:
    """Admit only stdlib or manifest-bound imports during runner execution."""

    def __init__(self, bound_names: frozenset[str]) -> None:
        self._bound_names = bound_names

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        if event != "import" or not arguments:
            return
        fullname = arguments[0]
        if type(fullname) is not str or not fullname:
            raise ImportError("V180r12r4 malformed import audit event rejected")
        root = fullname.split(".", 1)[0]
        if root in _FORBIDDEN_SITE_MODULES:
            raise ImportError("V180r12r4 site import machinery is forbidden")
        if root in {"acfqp", "packaging", "tomli"}:
            if fullname not in self._bound_names:
                raise ImportError(
                    f"V180r12r4 unlisted bound module origin rejected: {fullname}"
                )
            return
        if root not in _STDLIB_MODULE_NAMES:
            raise ImportError(
                f"V180r12r4 unlisted external import origin rejected: {fullname}"
            )


def _validated_frozen_authorization_context(value: object) -> dict:
    context = _require_exact_dict(
        value,
        set(_FROZEN_AUTHORIZATION_CONTEXT_FIELDS),
        "frozen authorization context",
    )
    if context["schema"] != _FROZEN_AUTHORIZATION_CONTEXT_SCHEMA:
        raise RuntimeError("V180r12r4 frozen authorization context schema changed")
    for key in (
        "protocol_id", "protocol_sha256", "authorization_id",
        "authorization_sha256", "authorization_evidence_id",
        "authorization_evidence_sha256", "campaign_measurement_execution_slot_id",
        "logical_occurrence_id", "execution_nonce", "campaign_attempt_id",
    ):
        _require_sha256(context[key], f"frozen authorization {key}")
    for key in (
        "protocol_byte_count", "authorization_byte_count",
        "authorization_evidence_byte_count",
    ):
        if _require_nonnegative_int(context[key], f"frozen authorization {key}") <= 0:
            raise RuntimeError(f"V180r12r4 frozen authorization {key} is not positive")
    cgroup = _require_exact_dict(
        context["cgroup_parent_fact"],
        _CGROUP_PARENT_FACT_FIELDS,
        "frozen cgroup parent fact",
    )
    capability = _require_exact_dict(
        context["runtime_capability_fact"],
        _RUNTIME_CAPABILITY_FACT_FIELDS,
        "frozen runtime capability fact",
    )
    if (
        cgroup["schema"] != "acfqp.v180r12r4_cgroup_parent_fact.v1"
        or capability["schema"]
        != "acfqp.v180r12r4_runtime_capability_fact.v1"
        or capability["admitted"] is not True
        or type(cgroup["owner_uid"]) is not int
        or type(cgroup["owner_gid"]) is not int
        or type(cgroup["mode"]) is not int
        or type(capability["uid"]) is not int
        or type(capability["gid"]) is not int
        or cgroup["owner_uid"] != capability["uid"]
        or cgroup["owner_gid"] != capability["gid"]
        or cgroup["mode"] & (stat.S_IWUSR | stat.S_IXUSR)
        != (stat.S_IWUSR | stat.S_IXUSR)
    ):
        raise RuntimeError("V180r12r4 frozen cgroup/runtime facts changed")
    _require_source_bound_service_context_capture(cgroup, capability)
    attempt_payload = {
        "schema": "acfqp.campaign_measurement_attempt.v180r12r4",
        "protocol_id": context["protocol_id"],
        "authorization_id": context["authorization_id"],
        "authorization_evidence_id": context["authorization_evidence_id"],
        "campaign_measurement_execution_slot_id": context[
            "campaign_measurement_execution_slot_id"
        ],
        "logical_occurrence_id": context["logical_occurrence_id"],
        "execution_nonce": context["execution_nonce"],
    }
    expected_attempt = hashlib.sha256(
        b"acfqp:construction-k7-campaign-measurement-attempt:v180r12r4\x00"
        + _canonical_json_bytes(attempt_payload)
    ).hexdigest()
    if context["campaign_attempt_id"] != expected_attempt:
        raise RuntimeError("V180r12r4 frozen campaign attempt identity changed")
    return context


def _validated_manifest(
    manifest: object,
    repository_root: Path,
    c_pre_root: Path,
    manifest_relative: str,
) -> dict:
    manifest = _require_exact_dict(manifest, _TOP_LEVEL_KEYS, "launch manifest")
    if manifest["schema"] != _SCHEMA:
        raise RuntimeError("V180r12r4 launch manifest schema changed")
    if manifest["repository_root"] != str(repository_root):
        raise RuntimeError("V180r12r4 manifest repository root changed")
    if manifest["c_pre_root"] != str(c_pre_root):
        raise RuntimeError("V180r12r4 manifest C_pre root changed")
    if manifest["manifest_relative_path"] != manifest_relative:
        raise RuntimeError("V180r12r4 manifest relative path changed")
    commit_id = manifest["c_pre_commit_id"]
    if type(commit_id) is not str or _COMMIT_PATTERN.fullmatch(commit_id) is None:
        raise RuntimeError("V180r12r4 C_pre commit ID changed")
    if manifest["authorization_source_closure_kind"] != _CLOSURE_KIND:
        raise RuntimeError("V180r12r4 authorization closure kind changed")
    source_conformance = _require_exact_dict(
        manifest["working_tree_source_conformance"],
        _SOURCE_CONFORMANCE_KEYS,
        "working-tree source conformance",
    )
    snapshots = source_conformance["snapshots"]
    if not (
        source_conformance["schema"]
        == "acfqp.v180r12r4_working_tree_source_conformance_diagnostic.v1"
        and source_conformance["phase"]
        == "BEFORE_PRELAUNCH_OUTPUT_AND_SCIENTIFIC_CAMPAIGN"
        and type(source_conformance["source_root_count"]) is int
        and source_conformance["source_root_count"] > 0
        and type(snapshots) is list
        and len(snapshots) == source_conformance["source_root_count"]
        and source_conformance["mismatch_count"] == 0
        and source_conformance["per_field_mismatches"] == []
        and source_conformance["unit_ownership_evaluated"] is False
        and source_conformance["full_source_conformance"] is True
        and source_conformance["cause"] is None
    ):
        raise RuntimeError("V180r12r4 working-tree source conformance changed")
    snapshot_paths: list[str] = []
    for index, snapshot in enumerate(snapshots):
        snapshot = _require_exact_dict(
            snapshot,
            _SOURCE_CONFORMANCE_SNAPSHOT_KEYS,
            f"working-tree source snapshot {index}",
        )
        expected = _require_exact_dict(
            snapshot["expected"],
            _SOURCE_CONFORMANCE_EXPECTED_KEYS,
            f"working-tree source expected {index}",
        )
        before = _require_exact_dict(
            snapshot["observed_before"],
            _SOURCE_CONFORMANCE_STAT_KEYS,
            f"working-tree source before {index}",
        )
        after = _require_exact_dict(
            snapshot["observed_after"],
            _SOURCE_CONFORMANCE_STAT_KEYS,
            f"working-tree source after {index}",
        )
        content = _require_exact_dict(
            snapshot["observed_content"],
            _SOURCE_CONFORMANCE_CONTENT_KEYS,
            f"working-tree source content {index}",
        )
        relative = _validated_relative_path(
            snapshot["relative_path"], f"working-tree source path {index}"
        )
        if not (
            before == after
            and snapshot["mismatch_fields"] == []
            and snapshot["conformant"] is True
            and expected["file_type"] == before["file_type"] == "REGULAR_FILE"
            and expected["mode"] == before["mode"]
            and expected["st_nlink"] == before["st_nlink"] == 1
            and expected["binding_kind"] == content["binding_kind"]
            and expected["byte_count"] == content["byte_count"]
            and expected["sha256"] == content["sha256"]
            and expected["git_blob_id"] == content["git_blob_id"]
            and content["physical_byte_count"] == before["st_size"]
        ):
            raise RuntimeError(
                f"V180r12r4 working-tree source snapshot {index} changed"
            )
        snapshot_paths.append(relative)
    closure = manifest["authorization_source_closure"]
    closure_paths = (
        [row.get("relative_path") for row in closure.get("facts", [])]
        if type(closure) is dict
        else []
    )
    if snapshot_paths != closure_paths or len(set(snapshot_paths)) != len(
        snapshot_paths
    ):
        raise RuntimeError("V180r12r4 source-conformance closure join changed")
    if manifest["authorization_self_module"] != _AUTHORIZATION_SELF_MODULE:
        raise RuntimeError("V180r12r4 authorization self module changed")
    if manifest["internal_target_contract"] != _INTERNAL_TARGET_CONTRACT:
        raise RuntimeError("V180r12r4 internal target contract changed")
    service_contract = manifest["production_systemd_service_contract"]
    invocation_templates = manifest["production_systemd_run_argv_templates"]
    preflight_interface = manifest[
        "atomic_cgroup_birth_preflight_receipt_interface"
    ]
    service_artifact_paths = manifest[
        "production_service_launch_artifact_paths"
    ]
    service_modes = manifest["production_service_launch_modes"]
    if not (
        type(service_contract) is dict
        and service_contract.get("schema")
        == "acfqp.v180r12r4_production_systemd_service_contracts.v1"
        and service_contract.get("token_domain")
        == _PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN
        and service_contract.get("target_order")
        == ["measurement", "verification"]
        and type(service_contract.get("target_rows")) is list
        and [row.get("target") for row in service_contract["target_rows"]]
        == ["measurement", "verification"]
        and all(
            (row.get("token"), row.get("unit_name"))
            == _PRODUCTION_TRANSIENT_SERVICE_ROWS[row["target"]]
            for row in service_contract["target_rows"]
        )
        and type(invocation_templates) is dict
        and set(invocation_templates) == {"measurement", "verification"}
        and all(type(value) is list and value for value in invocation_templates.values())
        and service_artifact_paths
        == {
            target: {
                "attempt": (
                    ".tmp/exact-freeze/"
                    "v180r12r4_campaign_measurement_prelaunch/"
                    f"{target.upper()}_SERVICE_LAUNCH_ATTEMPT.json"
                ),
                "receipt": (
                    ".tmp/exact-freeze/"
                    "v180r12r4_campaign_measurement_prelaunch/"
                    f"{target.upper()}_SERVICE_LAUNCH_RECEIPT.json"
                ),
                "failure": (
                    ".tmp/exact-freeze/"
                    f"v180r12r4_campaign_measurement_prelaunch_{target}_"
                    "service_launch_failure.json"
                ),
            }
            for target in ("measurement", "verification")
        }
        and service_modes
        == {
            "outer_dispatch": "dispatch",
            "retained_service_entry": "service-entry",
        }
        and preflight_interface
        == {
            "schema": _ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA,
            "receipt_id": "0" * 64,
            "receipt_byte_count": 0,
            "receipt_sha256": "0" * 64,
            "authority_accepted": False,
            "production_launch_authorized": False,
        }
    ):
        raise RuntimeError("V180r12r4 production systemd service contract changed")
    _validated_frozen_authorization_context(
        manifest["frozen_authorization_context"]
    )
    if manifest["working_tree_mutation_after_snapshot_in_scope"] is not False:
        raise RuntimeError("V180r12r4 post-snapshot mutation claim changed")
    return manifest


def _validate_manifest_resource_contract(
    manifest: dict, repository_root: Path
) -> tuple[list[dict], dict]:
    bootstrap = _require_exact_dict(
        manifest["bootstrap"], _RAW_FACT_KEYS, "bootstrap raw fact"
    )
    bootstrap_size = _require_nonnegative_int(
        bootstrap["byte_count"], "bootstrap byte count"
    )
    if bootstrap_size > _BOOTSTRAP_BYTE_CAP:
        raise RuntimeError("V180r12r4 bootstrap exceeds its independent byte cap")

    source_values = manifest["source_modules"]
    if type(source_values) is not list or not source_values:
        raise RuntimeError("V180r12r4 source module facts are not a nonempty list")
    if len(source_values) > _SOURCE_CLOSURE_FILE_CAP:
        raise RuntimeError("V180r12r4 source modules exceed their file cap")
    source_raw_by_path: dict[str, dict] = {}
    authorization_self_fact: dict | None = None
    evidence_wrapper_module_present = False
    for index, value in enumerate(source_values):
        fact = _require_exact_dict(value, _MODULE_FACT_KEYS, f"source module {index}")
        module = _require_str(fact["module"], f"source module {index} name")
        relative = _validated_relative_path(
            fact["relative_path"], f"source module {index} path"
        )
        size = _require_nonnegative_int(
            fact["byte_count"], f"source module {index} byte count"
        )
        if size > _SOURCE_FILE_BYTE_CAP or relative in source_raw_by_path:
            raise RuntimeError(f"V180r12r4 source module {index} exceeds its bound")
        raw_fact = {
            "relative_path": relative,
            "byte_count": size,
            "sha256": _require_sha256(
                fact["sha256"], f"source module {index} digest"
            ),
        }
        if module == _AUTHORIZATION_SELF_MODULE:
            authorization_self_fact = raw_fact
        else:
            source_raw_by_path[relative] = raw_fact
        if module == _AUTHORIZATION_EVIDENCE_MODULE:
            evidence_wrapper_module_present = True

    targets = _require_exact_dict(
        manifest["targets"], set(_TARGET_RUNNER_PATHS), "runner targets"
    )
    for name, expected_path in _TARGET_RUNNER_PATHS.items():
        fact = _require_exact_dict(targets[name], _RAW_FACT_KEYS, f"{name} runner")
        relative = _validated_relative_path(fact["relative_path"], f"{name} runner path")
        size = _require_nonnegative_int(fact["byte_count"], f"{name} runner byte count")
        if (
            relative != expected_path
            or size > _RUNNER_BYTE_CAP
            or relative in source_raw_by_path
        ):
            raise RuntimeError(f"V180r12r4 {name} runner exceeds its independent bound")
        source_raw_by_path[relative] = {
            "relative_path": relative,
            "byte_count": size,
            "sha256": _require_sha256(fact["sha256"], f"{name} runner digest"),
        }

    authorization_facts = _validated_raw_closure(
        manifest["authorization_source_closure"],
        "authorization source closure",
    )
    authorization_by_path = {
        fact["relative_path"]: fact for fact in authorization_facts
    }
    if tuple(authorization_by_path) != _SOURCE_CLOSURE_REQUIRED_ROOTS:
        raise RuntimeError("V180r12r4 required static source closure is not exact")
    for relative, fact in authorization_by_path.items():
        if relative == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH:
            raw = _stable_read(
                repository_root,
                relative,
                "authorization evidence wrapper",
                byte_cap=_SOURCE_FILE_BYTE_CAP,
            )
            normalized = _normalize_authorization_evidence_wrapper(raw)
            if not (
                fact.get("binding_kind") == "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
                and fact.get("redacted_constant_names")
                == list(_WRAPPER_REDACTED_CONSTANT_NAMES)
                and len(normalized) == fact["byte_count"]
                and hashlib.sha256(normalized).hexdigest() == fact["sha256"]
            ):
                raise RuntimeError(
                    "V180r12r4 normalized authorization wrapper fact mismatch"
                )
            continue
        _verify_raw_fact(
            repository_root,
            fact,
            f"required static source {relative}",
            expected_relative_path=relative,
            byte_cap=(
                _RUNNER_BYTE_CAP
                if relative.startswith("scripts/")
                else _SOURCE_FILE_BYTE_CAP
            ),
        )
        if relative.endswith(".py"):
            raw, _ = _verify_raw_fact(
                repository_root,
                fact,
                f"precompiled required static source {relative}",
                expected_relative_path=relative,
                byte_cap=(
                    _RUNNER_BYTE_CAP
                    if relative.startswith("scripts/")
                    else _SOURCE_FILE_BYTE_CAP
                ),
            )
            try:
                compile(
                    raw,
                    str(repository_root / relative),
                    "exec",
                    dont_inherit=True,
                    optimize=0,
                )
            except (SyntaxError, ValueError) as error:
                raise RuntimeError(
                    f"V180r12r4 required static source cannot be precompiled: {relative}"
                ) from error
    if authorization_self_fact is None:
        raise RuntimeError("V180r12r4 authorization self raw fact is absent")
    if not evidence_wrapper_module_present:
        raise RuntimeError("V180r12r4 authorization evidence wrapper is absent")

    third_party_facts = _validated_third_party_closure(
        manifest["third_party_source_closure"]
    )
    targets = manifest["targets"]
    total_file_count = len(source_values) + len(targets) + len(third_party_facts)
    total_byte_count = (
        sum(fact["byte_count"] for fact in source_values)
        + sum(fact["byte_count"] for fact in targets.values())
        + sum(fact["byte_count"] for fact in third_party_facts)
    )
    if (
        total_file_count > _SOURCE_CLOSURE_FILE_CAP
        or total_byte_count > _SOURCE_CLOSURE_TOTAL_BYTE_CAP
    ):
        raise RuntimeError("V180r12r4 combined source closure exceeds its cap")
    return third_party_facts, authorization_by_path[_AUTHORIZATION_EVIDENCE_RELATIVE_PATH]


def _compile_bound_sources(
    manifest: dict,
    repository_root: Path,
    normalized_wrapper_fact: dict,
) -> dict[str, tuple[object, str, bool]]:
    source_values = manifest["source_modules"]
    authorization_names = manifest["authorization_raw_source_modules"]
    if type(source_values) is not list or not source_values:
        raise RuntimeError("V180r12r4 source module facts are not a nonempty list")
    if (
        type(authorization_names) is not list
        or not all(type(name) is str for name in authorization_names)
        or authorization_names != sorted(set(authorization_names))
    ):
        raise RuntimeError("V180r12r4 authorization source module names changed")

    records: dict[str, tuple[object, str, bool]] = {}
    paths: set[str] = set()
    for index, value in enumerate(source_values):
        fact = _require_exact_dict(value, _MODULE_FACT_KEYS, f"source module {index}")
        module = _require_str(fact["module"], f"source module {index} name")
        is_package = fact["is_package"]
        if type(is_package) is not bool:
            raise RuntimeError(f"V180r12r4 source module {index} package flag changed")
        raw_fact = {key: fact[key] for key in _RAW_FACT_KEYS}
        raw, relative = _verify_raw_fact(
            repository_root,
            raw_fact,
            f"source module {module}",
            byte_cap=_SOURCE_FILE_BYTE_CAP,
        )
        if module == _AUTHORIZATION_EVIDENCE_MODULE:
            normalized = _normalize_authorization_evidence_wrapper(raw)
            if not (
                relative == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH
                and len(normalized) == normalized_wrapper_fact["byte_count"]
                and hashlib.sha256(normalized).hexdigest()
                == normalized_wrapper_fact["sha256"]
            ):
                raise RuntimeError(
                    "V180r12r4 normalized authorization wrapper fact mismatch"
                )
        pure = PurePosixPath(relative)
        if (
            (module != "acfqp" and not module.startswith("acfqp."))
            or not relative.startswith("src/acfqp/")
            or pure.suffix != ".py"
            or is_package != (pure.name == "__init__.py")
            or module in records
            or relative in paths
        ):
            raise RuntimeError(f"V180r12r4 source module {module} binding changed")
        expected_parts = ["acfqp", *module.split(".")[1:]]
        expected_relative = PurePosixPath("src", *expected_parts)
        if is_package:
            expected_relative /= "__init__.py"
        else:
            expected_relative = expected_relative.with_suffix(".py")
        if relative != expected_relative.as_posix():
            raise RuntimeError(f"V180r12r4 source module {module} path changed")
        source_path = str(repository_root / relative)
        try:
            code = compile(raw, source_path, "exec", dont_inherit=True, optimize=0)
        except (SyntaxError, ValueError) as error:
            raise RuntimeError(
                f"V180r12r4 source module {module} cannot be compiled"
            ) from error
        records[module] = (code, source_path, is_package)
        paths.add(relative)

    names = sorted(records)
    expected_names = sorted([*authorization_names, _AUTHORIZATION_SELF_MODULE])
    if (
        names != expected_names
        or _AUTHORIZATION_SELF_MODULE in authorization_names
        or "acfqp" not in records
        or _AUTHORIZATION_SELF_MODULE not in records
    ):
        raise RuntimeError("V180r12r4 authorization source closure is not exact")
    return records


def _compile_third_party_sources(
    facts: list[dict],
) -> dict[str, tuple[object, str, bool]]:
    records: dict[str, tuple[object, str, bool]] = {}
    roots: dict[str, Path] = {}
    paths: set[tuple[str, str]] = set()
    for index, fact in enumerate(facts):
        module = fact["module"]
        namespace = module.split(".", 1)[0]
        if namespace not in {"packaging", "tomli"}:
            raise RuntimeError(
                f"V180r12r4 foreign third-party namespace rejected: {module}"
            )
        root_text = fact["source_root"]
        root = roots.setdefault(
            root_text,
            _validated_root(root_text, f"third-party source root {root_text}"),
        )
        relative = fact["relative_path"]
        pure = PurePosixPath(relative)
        is_package = fact["is_package"]
        expected = PurePosixPath(*module.split("."))
        if is_package:
            expected /= "__init__.py"
        else:
            expected = expected.with_suffix(".py")
        if (
            relative != expected.as_posix()
            or pure.suffix != ".py"
            or is_package != (pure.name == "__init__.py")
            or module in records
            or (root_text, relative) in paths
        ):
            raise RuntimeError(
                f"V180r12r4 third-party source module {module} binding changed"
            )
        raw_fact = {key: fact[key] for key in _RAW_FACT_KEYS}
        raw, _ = _verify_raw_fact(
            root,
            raw_fact,
            f"third-party source module {module}",
            byte_cap=_SOURCE_FILE_BYTE_CAP,
        )
        source_path = str(root / relative)
        try:
            code = compile(raw, source_path, "exec", dont_inherit=True, optimize=0)
        except (SyntaxError, ValueError) as error:
            raise RuntimeError(
                f"V180r12r4 third-party source module {module} cannot be compiled"
            ) from error
        records[module] = (code, source_path, is_package)
        paths.add((root_text, relative))
    if "packaging" not in records or "tomli" not in records:
        raise RuntimeError("V180r12r4 required third-party source roots are absent")
    return records


def _compile_runners(
    manifest: dict,
    repository_root: Path,
    target: str,
) -> tuple[tuple[object, str], dict[str, tuple[object, str]]]:
    targets = _require_exact_dict(
        manifest["targets"], set(_TARGET_RUNNER_PATHS), "runner targets"
    )
    selected: tuple[object, str] | None = None
    compiled: dict[str, tuple[object, str]] = {}
    for name, expected_path in _TARGET_RUNNER_PATHS.items():
        fact = _require_exact_dict(targets[name], _RAW_FACT_KEYS, f"{name} runner")
        if fact["relative_path"] != expected_path:
            raise RuntimeError(f"V180r12r4 {name} runner path changed")
        raw, relative = _verify_raw_fact(
            repository_root,
            fact,
            f"{name} runner",
            expected_relative_path=expected_path,
            byte_cap=_RUNNER_BYTE_CAP,
        )
        source_path = str(repository_root / relative)
        try:
            code = compile(raw, source_path, "exec", dont_inherit=True, optimize=0)
        except (SyntaxError, ValueError) as error:
            raise RuntimeError(f"V180r12r4 {name} runner cannot be compiled") from error
        compiled[name] = (code, source_path)
        if name == target:
            selected = (code, source_path)
    if selected is None:  # pragma: no cover - target checked by the public API.
        raise RuntimeError("V180r12r4 selected runner is absent")
    return selected, compiled


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise RuntimeError("V180r12r4 sealed bundle write made no progress")
        view = view[written:]


def _read_descriptor(descriptor: int, *, byte_cap: int, label: str) -> bytes:
    if type(descriptor) is not int or descriptor < 3 or byte_cap <= 0:
        raise RuntimeError(f"V180r12r4 {label} descriptor or cap changed")
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode) or before.st_size < 0 or before.st_size > byte_cap:
        raise RuntimeError(f"V180r12r4 {label} is not one bounded regular file")
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = before.st_size
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            raise RuntimeError(f"V180r12r4 {label} ended before its exact size")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise RuntimeError(f"V180r12r4 {label} grew beyond its exact size")
    after = os.fstat(descriptor)
    compared = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size")
    if any(getattr(before, name) != getattr(after, name) for name in compared):
        raise RuntimeError(f"V180r12r4 {label} changed during bounded read")
    return b"".join(chunks)


def _require_sealed_read_only_memfd(
    descriptor: int,
    *,
    byte_cap: int,
    label: str,
    exact_byte_count: int | None = None,
) -> bytes:
    if not os.get_inheritable(descriptor):
        raise RuntimeError(f"V180r12r4 {label} was CLOEXEC at bootstrap entry")
    flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
    if flags & os.O_ACCMODE != os.O_RDONLY:
        raise RuntimeError(f"V180r12r4 {label} is not read-only")
    seals = fcntl.fcntl(descriptor, fcntl.F_GET_SEALS)
    if seals != _REQUIRED_MEMFD_SEAL_MASK:
        raise RuntimeError(f"V180r12r4 {label} seal set changed")
    metadata = os.fstat(descriptor)
    if stat.S_IMODE(metadata.st_mode) != 0o400:
        raise RuntimeError(f"V180r12r4 {label} immutable mode changed")
    raw = _read_descriptor(descriptor, byte_cap=byte_cap, label=label)
    if exact_byte_count is not None and len(raw) != exact_byte_count:
        raise RuntimeError(f"V180r12r4 {label} exact byte count changed")
    return raw


def _require_sealed_read_only_memfd_metadata(
    descriptor: int,
    *,
    exact_byte_count: int,
    label: str,
) -> None:
    """Validate a measured payload FD without consuming any payload byte."""

    if (
        type(descriptor) is not int
        or descriptor < 3
        or type(exact_byte_count) is not int
        or exact_byte_count < 0
    ):
        raise RuntimeError(f"V180r12r4 {label} descriptor or size changed")
    if not os.get_inheritable(descriptor):
        raise RuntimeError(f"V180r12r4 {label} was CLOEXEC at bootstrap entry")
    flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
    seals = fcntl.fcntl(descriptor, fcntl.F_GET_SEALS)
    metadata = os.fstat(descriptor)
    if not (
        flags & os.O_ACCMODE == os.O_RDONLY
        and seals == _REQUIRED_MEMFD_SEAL_MASK
        and stat.S_ISREG(metadata.st_mode)
        and metadata.st_nlink == 0
        and stat.S_IMODE(metadata.st_mode) == 0o400
        and metadata.st_size == exact_byte_count
    ):
        raise RuntimeError(f"V180r12r4 {label} immutable metadata changed")


def _create_precompiled_bundle(
    *,
    records: dict[str, tuple[object, str, bool]],
    runners: dict[str, tuple[object, str]],
    manifest_digest: str,
    commit_id: str,
    repository_root: Path,
    c_pre_root: Path,
    manifest_path: Path,
    install_descriptor: bool,
) -> tuple[bytes, str, tuple[dict, ...]]:
    """Build the exact application bundle and optionally install sealed FD240."""

    source_rows = []
    for module in sorted(records):
        code, source_path, is_package = records[module]
        if not isinstance(code, types.CodeType):
            raise RuntimeError("V180r12r4 precompiled source record is not code")
        marshalled = marshal.dumps(code)
        source_rows.append(
            {
                "module": module,
                "source_path": source_path,
                "is_package": is_package,
                "marshal_byte_count": len(marshalled),
                "marshal_sha256": hashlib.sha256(marshalled).hexdigest(),
                "marshal_hex": marshalled.hex(),
            }
        )
    target_rows = []
    for target in _MEASURED_TARGETS:
        code, source_path = runners[target]
        if not isinstance(code, types.CodeType):
            raise RuntimeError("V180r12r4 precompiled internal runner is not code")
        marshalled = marshal.dumps(code)
        target_rows.append(
            {
                "target": target,
                "source_path": source_path,
                "marshal_byte_count": len(marshalled),
                "marshal_sha256": hashlib.sha256(marshalled).hexdigest(),
                "marshal_hex": marshalled.hex(),
            }
        )
    document = {
        "schema": _PRECOMPILED_BUNDLE_SCHEMA,
        "manifest_sha256": manifest_digest,
        "c_pre_commit_id": commit_id,
        "repository_root": str(repository_root),
        "c_pre_root": str(c_pre_root),
        "manifest_path": str(manifest_path),
        "measured_target_contract": list(_MEASURED_TARGETS),
        "source_records": source_rows,
        "target_records": target_rows,
    }
    raw = _canonical_json_bytes(document)
    if not raw or len(raw) > _SOURCE_CLOSURE_TOTAL_BYTE_CAP:
        raise RuntimeError("V180r12r4 precompiled bundle exceeds its byte cap")
    digest = hashlib.sha256(raw).hexdigest()
    normalized_rows = _native_zero_precompiled_source_rows(
        source_rows=source_rows,
        target_rows=target_rows,
        repository_root=repository_root,
    )
    if install_descriptor:
        descriptor = os.memfd_create(
            "acfqp-v180r12r4-precompiled-bundle",
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        read_only = -1
        try:
            _write_all(descriptor, raw)
            os.fchmod(descriptor, 0o400)
            fcntl.fcntl(
                descriptor, fcntl.F_ADD_SEALS, _REQUIRED_MEMFD_SEAL_MASK
            )
            read_only = os.open(
                f"/proc/self/fd/{descriptor}", os.O_RDONLY | os.O_CLOEXEC
            )
            if (
                os.fstat(read_only).st_dev != os.fstat(descriptor).st_dev
                or os.fstat(read_only).st_ino != os.fstat(descriptor).st_ino
            ):
                raise RuntimeError(
                    "V180r12r4 read-only precompiled bundle identity changed"
                )
            os.dup2(read_only, _PRECOMPILED_BUNDLE_FD, inheritable=True)
        finally:
            if read_only >= 0 and read_only != _PRECOMPILED_BUNDLE_FD:
                os.close(read_only)
            if descriptor != _PRECOMPILED_BUNDLE_FD:
                os.close(descriptor)
    return raw, digest, normalized_rows


def _native_zero_precompiled_source_rows(
    *,
    source_rows: list[dict],
    target_rows: list[dict],
    repository_root: Path,
) -> tuple[dict, ...]:
    """Project the full sealed bundle onto the planning application axis."""

    rows: list[dict] = []
    root = repository_root.resolve()
    for supplied in source_rows:
        module = supplied["module"]
        # packaging/tomli remain bound by the full bundle digest as the exact
        # third-party trusted runtime boundary; they are not planning facts.
        if module != "acfqp" and not module.startswith("acfqp."):
            continue
        source = Path(supplied["source_path"])
        try:
            relative = source.relative_to(root).as_posix()
        except ValueError as error:
            raise RuntimeError(
                "V180r12r4 application module escaped repository root"
            ) from error
        if str(root / relative) != str(source):
            raise RuntimeError(
                "V180r12r4 application module source normalization changed"
            )
        rows.append(
            {
                "source_kind": "MODULE",
                "name": module,
                "source_path": relative,
                "is_package": supplied["is_package"],
                "marshal_byte_count": supplied["marshal_byte_count"],
                "marshal_sha256": supplied["marshal_sha256"],
            }
        )
    for supplied in target_rows:
        target = supplied["target"]
        expected_relative = _TARGET_RUNNER_PATHS.get(target)
        if target not in _MEASURED_TARGETS or expected_relative is None:
            raise RuntimeError("V180r12r4 measured target set changed")
        if supplied["source_path"] != str(root / expected_relative):
            raise RuntimeError("V180r12r4 measured target source binding changed")
        rows.append(
            {
                "source_kind": "TARGET",
                "name": target,
                "source_path": expected_relative,
                "is_package": False,
                "marshal_byte_count": supplied["marshal_byte_count"],
                "marshal_sha256": supplied["marshal_sha256"],
            }
        )
    rows.sort(key=lambda row: (row["source_kind"], row["name"]))
    coordinates = [(row["source_kind"], row["name"]) for row in rows]
    if (
        coordinates != sorted(set(coordinates))
        or {row["name"] for row in rows if row["source_kind"] == "TARGET"}
        != set(_MEASURED_TARGETS)
        or not any(row["source_kind"] == "MODULE" for row in rows)
    ):
        raise RuntimeError(
            "V180r12r4 native-zero application source summary changed"
        )
    return tuple(rows)


def _decode_marshaled_code(row: object, keys: set[str], label: str) -> object:
    row = _require_exact_dict(row, keys, label)
    byte_count = _require_nonnegative_int(row["marshal_byte_count"], f"{label} size")
    digest = _require_sha256(row["marshal_sha256"], f"{label} digest")
    encoded = _require_str(row["marshal_hex"], f"{label} bytes")
    try:
        raw = bytes.fromhex(encoded)
        code = marshal.loads(raw)
    except (ValueError, TypeError, EOFError) as error:
        raise RuntimeError(f"V180r12r4 {label} marshal bytes changed") from error
    if (
        len(raw) != byte_count
        or hashlib.sha256(raw).hexdigest() != digest
        or not isinstance(code, types.CodeType)
    ):
        raise RuntimeError(f"V180r12r4 {label} code identity changed")
    return code


def _load_precompiled_bundle(
    raw: bytes,
    *,
    target: str,
    manifest_digest: str,
    repository_root: str,
    c_pre_root: str,
    manifest_path: str,
) -> tuple[dict[str, tuple[object, str, bool]], object, str, dict]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("V180r12r4 precompiled bundle is not JSON") from error
    if _canonical_json_bytes(value) != raw:
        raise RuntimeError("V180r12r4 precompiled bundle is noncanonical")
    bundle = _require_exact_dict(
        value,
        {
            "schema",
            "manifest_sha256",
            "c_pre_commit_id",
            "repository_root",
            "c_pre_root",
            "manifest_path",
            "measured_target_contract",
            "source_records",
            "target_records",
        },
        "precompiled bundle",
    )
    commit_id = bundle["c_pre_commit_id"]
    if not (
        bundle["schema"] == _PRECOMPILED_BUNDLE_SCHEMA
        and bundle["manifest_sha256"] == manifest_digest
        and type(commit_id) is str
        and _COMMIT_PATTERN.fullmatch(commit_id) is not None
        and bundle["repository_root"] == repository_root
        and bundle["c_pre_root"] == c_pre_root
        and bundle["manifest_path"] == manifest_path
        and bundle["measured_target_contract"] == list(_MEASURED_TARGETS)
    ):
        raise RuntimeError("V180r12r4 precompiled bundle boundary changed")
    source_rows = bundle["source_records"]
    target_rows = bundle["target_records"]
    if type(source_rows) is not list or type(target_rows) is not list:
        raise RuntimeError("V180r12r4 precompiled bundle records changed")
    records: dict[str, tuple[object, str, bool]] = {}
    for index, row in enumerate(source_rows):
        code = _decode_marshaled_code(
            row,
            {
                "module",
                "source_path",
                "is_package",
                "marshal_byte_count",
                "marshal_sha256",
                "marshal_hex",
            },
            f"precompiled source {index}",
        )
        module = _require_str(row["module"], f"precompiled source {index} module")
        source_path = _require_str(
            row["source_path"], f"precompiled source {index} path"
        )
        is_package = row["is_package"]
        if (
            type(is_package) is not bool
            or module in records
            or not Path(source_path).is_absolute()
            or not source_path.startswith(repository_root + os.sep)
        ):
            raise RuntimeError("V180r12r4 precompiled source binding changed")
        records[module] = (code, source_path, is_package)
    if [row["module"] for row in source_rows] != sorted(records):
        raise RuntimeError("V180r12r4 precompiled source order changed")
    compiled_targets: dict[str, tuple[object, str]] = {}
    for index, row in enumerate(target_rows):
        code = _decode_marshaled_code(
            row,
            {
                "target",
                "source_path",
                "marshal_byte_count",
                "marshal_sha256",
                "marshal_hex",
            },
            f"precompiled target {index}",
        )
        name = _require_str(row["target"], f"precompiled target {index} name")
        source_path = _require_str(row["source_path"], f"precompiled target {index} path")
        if (
            name in compiled_targets
            or name not in _MEASURED_TARGETS
            or source_path != str(Path(repository_root) / _TARGET_RUNNER_PATHS[name])
        ):
            raise RuntimeError("V180r12r4 precompiled measured target binding changed")
        compiled_targets[name] = (code, source_path)
    if list(compiled_targets) != list(_MEASURED_TARGETS):
        raise RuntimeError("V180r12r4 precompiled measured target order changed")
    if target not in _INTERNAL_TARGETS:
        raise RuntimeError("V180r12r4 bundle dispatch target is not internal")
    code, source_path = compiled_targets[target]
    return records, code, source_path, bundle


def _internal_context_payload_keys() -> set[str]:
    return {
        "schema",
        "target",
        "actor_role",
        "parent_actor_role",
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "attempt_id",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
        "launch_operation_id",
        "repository_root",
        "c_pre_root",
        "manifest_path",
        "launch_manifest_sha256",
        "c_pre_commit_id",
        "precompiled_source_bundle_sha256",
        "runner_relative_path",
        "inherited_fd_roles",
        "target_payload",
        "one_shot",
        "context_mac_algorithm",
        "context_mac_direction",
    }


def _validate_operational_descriptor(
    descriptor: int,
    role: str,
    *,
    context: dict,
) -> None:
    if not os.get_inheritable(descriptor):
        raise RuntimeError(f"V180r12r4 internal {role} was CLOEXEC at exec")
    metadata = os.fstat(descriptor)
    flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
    if role.endswith("SOCK_SEQPACKET"):
        duplicate = socket.fromfd(descriptor, socket.AF_UNIX, socket.SOCK_SEQPACKET)
        try:
            if (
                duplicate.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
                != socket.SOCK_SEQPACKET
                or duplicate.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
                < _SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
                or duplicate.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
                < _SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
            ):
                raise RuntimeError(
                    "V180r12r4 internal IPC socket type or effective buffer changed"
                )
        finally:
            duplicate.close()
    elif role == "REPOSITORY_ROOT_O_PATH_DIRECTORY":
        if not stat.S_ISDIR(metadata.st_mode) or flags & os.O_PATH != os.O_PATH:
            raise RuntimeError("V180r12r4 supervisor repository root dirfd changed")
    elif role == "WORKER_CGROUP_DIRECTORY":
        if not stat.S_ISDIR(metadata.st_mode) or flags & os.O_ACCMODE != os.O_RDONLY:
            raise RuntimeError("V180r12r4 supervisor worker-cgroup dirfd changed")
    elif role in {
        "TERMINAL_STAGE_READ_ONLY_MEMFD",
        "VERIFICATION_STAGE_READ_ONLY_MEMFD",
    }:
        expected = context["target_payload"][
            "terminal_stage_byte_count"
            if role == "TERMINAL_STAGE_READ_ONLY_MEMFD"
            else "verification_stage_byte_count"
        ]
        _require_sealed_read_only_memfd_metadata(
            descriptor,
            label=role,
            exact_byte_count=expected,
        )
    elif role == "SUBJECT_RESULT_WRITE_ONLY_FD":
        if not (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_nlink == 1
            and metadata.st_size == 0
            and stat.S_IMODE(metadata.st_mode) == 0o600
            and flags & os.O_ACCMODE == os.O_WRONLY
        ):
            raise RuntimeError("V180r12r4 worker subject-result FD changed")
    elif role == "PRECOMPILED_SOURCE_BUNDLE_MEMFD":
        return
    else:  # key/context are consumed separately and never reach this helper.
        raise RuntimeError(f"V180r12r4 internal FD role is unsupported: {role}")


def _require_exact_internal_descriptor_inventory(target: str) -> None:
    expected = {0, 1, 2, *(fd for fd, _role in _INTERNAL_FD_ROLE_MAP[target])}
    observed: set[int] = set()
    for name in os.listdir("/proc/self/fd"):
        if not name.isdecimal():
            raise RuntimeError("V180r12r4 internal open-FD inventory is malformed")
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError:
            # /proc/self/fd may expose the directory FD used by listdir after
            # it has already been closed.  It is not an inherited descriptor.
            continue
        observed.add(descriptor)
    if observed != expected:
        raise RuntimeError(
            "V180r12r4 internal open-FD inventory changed: "
            f"expected={sorted(expected)!r}, observed={sorted(observed)!r}"
        )


def _require_exact_external_descriptor_inventory(target: str) -> None:
    expected_by_target = {
        "measurement": {0, 1, 2, 249, 250, 251, 252},
        "verification": {0, 1, 2, 249},
    }
    if target not in expected_by_target:
        raise RuntimeError("V180r12r4 external target changed")
    observed: set[int] = set()
    for name in os.listdir("/proc/self/fd"):
        if not name.isdecimal():
            raise RuntimeError("V180r12r4 external open-FD inventory is malformed")
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        observed.add(descriptor)
    if observed != expected_by_target[target]:
        raise RuntimeError(
            "V180r12r4 external open-FD inventory changed: "
            f"expected={sorted(expected_by_target[target])!r}, "
            f"observed={sorted(observed)!r}"
        )


def _consume_external_context_at_entry(
    *,
    target: str,
    repository_text: str,
    c_pre_text: str,
    manifest_text: str,
    manifest_digest: str,
) -> tuple[dict, str]:
    _require_exact_external_descriptor_inventory(target)
    raw = _require_sealed_read_only_memfd(
        _EXTERNAL_CONTEXT_FD,
        byte_cap=_EXTERNAL_CONTEXT_BYTE_CAP,
        label="external launch context",
    )
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("V180r12r4 external context is not JSON") from error
    if _canonical_json_bytes(value) != raw:
        raise RuntimeError("V180r12r4 external context is noncanonical")
    context = _require_exact_dict(
        value, set(_EXTERNAL_CONTEXT_FIELDS), "external launch context"
    )
    expected_actor = {"measurement": "OBSERVER", "verification": "VERIFIER"}
    expected_roles = {
        "measurement": [
            [249, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"],
            [250, "DELEGATED_CGROUP_PARENT_DIRECTORY"],
            [251, "CGROUP2_MOUNT_DIRECTORY"],
            [252, "SOURCE_SYSTEMD_SERVICE_DIRECTORY"],
        ],
        "verification": [[249, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"]],
    }
    expected_payload = {
        "measurement": {
            "delegated_cgroup_parent_fd": 250,
            "cgroup2_mount_fd": 251,
            "source_systemd_service_fd": 252,
        },
        "verification": {},
    }
    if not (
        context["schema"] == _EXTERNAL_CONTEXT_SCHEMA
        and context["target"] == target
        and context["actor_role"] == expected_actor[target]
        and context["repository_root"] == repository_text
        and context["c_pre_root"] == c_pre_text
        and context["prelaunch_launch_manifest_sha256"] == manifest_digest
        and context["inherited_fd_roles"] == expected_roles[target]
        and context["target_payload"] == expected_payload[target]
        and type(context["production_systemd_service_invocation"]) is dict
        and set(context["production_systemd_service_invocation"])
        == _PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS
        and context["production_systemd_service_invocation"].get("target")
        == target
        and (
            context["production_systemd_service_invocation"].get("token"),
            context["production_systemd_service_invocation"].get("unit_name"),
        )
        == _PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
        and context["production_systemd_service_invocation"].get("umask")
        == "0077"
        and type(context["production_runtime_placement_t1"]) is dict
        and set(context["production_runtime_placement_t1"])
        == _PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS
        and context["production_runtime_placement_t1"].get("schema")
        == _PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
        and context["production_runtime_placement_t1"].get("target") == target
        and context["production_runtime_placement_t1"].get("unit_name")
        == _PRODUCTION_TRANSIENT_SERVICE_ROWS[target][1]
        and context["production_runtime_placement_t1"].get(
            "self_pid_in_source_cgroup_procs"
        )
        is True
        and context["production_runtime_placement_t1"].get(
            "planned_measurement_root_absent"
        )
        is True
        and context["one_shot"] is True
    ):
        raise RuntimeError("V180r12r4 external context role/path/FD binding changed")
    if manifest_text != f"{c_pre_text}/launch_manifest.json":
        raise RuntimeError("V180r12r4 external manifest path changed")
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
    ):
        _require_sha256(context[key], "external context " + key)
    for key in (
        "prelaunch_materialization_terminal_byte_count",
        "current_launch_attempt_byte_count",
        "measurement_launch_attempt_byte_count",
        "protocol_byte_count",
        "authorization_byte_count",
        "authorization_evidence_byte_count",
    ):
        if _require_nonnegative_int(context[key], "external context " + key) <= 0:
            raise RuntimeError("V180r12r4 external context byte count is not positive")
    origin_ns = context["monotonic_origin_ns"]
    hard_deadline_ns = context["hard_deadline_ns"]
    campaign_deadline_ns = context["campaign_deadline_ns"]
    if not (
        type(origin_ns) is int
        and type(hard_deadline_ns) is int
        and type(campaign_deadline_ns) is int
        and 0 < origin_ns < campaign_deadline_ns < hard_deadline_ns
        and hard_deadline_ns - origin_ns == 14_400 * 1_000_000_000
        and hard_deadline_ns - campaign_deadline_ns == 600 * 1_000_000_000
    ):
        raise RuntimeError("V180r12r4 shared monotonic deadlines changed")
    commit = context["prereg_commit_id"]
    if (
        type(commit) is not str
        or len(commit) != 40
        or any(character not in "0123456789abcdef" for character in commit)
    ):
        raise RuntimeError("V180r12r4 external context C_pre commit changed")
    os.close(_EXTERNAL_CONTEXT_FD)
    if target == "measurement":
        cgroup = context["cgroup_parent_fact"]
        if type(cgroup) is not dict or set(cgroup) != _CGROUP_PARENT_FACT_FIELDS:
            raise RuntimeError("V180r12r4 external cgroup fact field set changed")
        parent = os.fstat(_DELEGATED_CGROUP_PARENT_FD)
        mount = os.fstat(_CGROUP2_MOUNT_FD)
        service = os.fstat(_SOURCE_SYSTEMD_SERVICE_FD)
        parent_flags = fcntl.fcntl(_DELEGATED_CGROUP_PARENT_FD, fcntl.F_GETFL)
        mount_flags = fcntl.fcntl(_CGROUP2_MOUNT_FD, fcntl.F_GETFL)
        service_flags = fcntl.fcntl(_SOURCE_SYSTEMD_SERVICE_FD, fcntl.F_GETFL)
        placement_t1 = context["production_runtime_placement_t1"]
        parent_fd_fact = placement_t1["delegated_parent_fd_fact"]
        mount_fd_fact = placement_t1["cgroup2_mount_fd_fact"]
        service_fd_fact = placement_t1["source_service_fd_fact"]
        if not (
            type(parent_fd_fact) is dict
            and type(mount_fd_fact) is dict
            and type(service_fd_fact) is dict
            and set(parent_fd_fact) == _PLACEMENT_DIRECTORY_FD_FACT_FIELDS
            and set(mount_fd_fact) == _PLACEMENT_DIRECTORY_FD_FACT_FIELDS
            and set(service_fd_fact) == _PLACEMENT_DIRECTORY_FD_FACT_FIELDS
        ):
            raise RuntimeError("V180r12r4 T1 directory-FD field set changed")
        if not (
            os.get_inheritable(_DELEGATED_CGROUP_PARENT_FD)
            and os.get_inheritable(_CGROUP2_MOUNT_FD)
            and os.get_inheritable(_SOURCE_SYSTEMD_SERVICE_FD)
            and stat.S_ISDIR(parent.st_mode)
            and parent_flags & os.O_ACCMODE == os.O_RDONLY
            and parent.st_dev == cgroup["parent_device"]
            and parent.st_ino == cgroup["parent_inode"]
            and parent.st_uid == cgroup["owner_uid"]
            and parent.st_gid == cgroup["owner_gid"]
            and stat.S_IMODE(parent.st_mode) == cgroup["mode"]
            and stat.S_ISDIR(mount.st_mode)
            and mount_flags & os.O_PATH == os.O_PATH
            and mount.st_dev == cgroup["mount_device"]
            and mount.st_ino == cgroup["mount_inode"]
            and stat.S_ISDIR(service.st_mode)
            and service_flags & os.O_ACCMODE == os.O_RDONLY
            and service.st_dev == parent.st_dev
            and parent_fd_fact["fd"] == _DELEGATED_CGROUP_PARENT_FD
            and parent_fd_fact["device"] == parent.st_dev
            and parent_fd_fact["inode"] == parent.st_ino
            and parent_fd_fact["path"] == cgroup["parent_path"]
            and mount_fd_fact["fd"] == _CGROUP2_MOUNT_FD
            and mount_fd_fact["device"] == mount.st_dev
            and mount_fd_fact["inode"] == mount.st_ino
            and mount_fd_fact["path"] == cgroup["mount_point"]
            and service_fd_fact["fd"] == _SOURCE_SYSTEMD_SERVICE_FD
            and service_fd_fact["device"] == service.st_dev
            and service_fd_fact["inode"] == service.st_ino
            and service_fd_fact["path"]
            == str(
                PurePosixPath(cgroup["parent_path"])
                / _PRODUCTION_TRANSIENT_SERVICE_ROWS[target][1]
            )
        ):
            raise RuntimeError("V180r12r4 external cgroup descriptors changed")
        os.set_inheritable(_DELEGATED_CGROUP_PARENT_FD, False)
        os.set_inheritable(_CGROUP2_MOUNT_FD, False)
        os.set_inheritable(_SOURCE_SYSTEMD_SERVICE_FD, False)
    return context, hashlib.sha256(raw).hexdigest()


def _freeze_json_value(value: object) -> object:
    if type(value) is dict:
        return types.MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if type(value) is list:
        return tuple(_freeze_json_value(item) for item in value)
    if value is None or type(value) in {str, int, bool}:
        return value
    raise RuntimeError("V180r12r4 external context contains a non-JSON value")


def _verify_external_context_against_manifest(
    context: dict,
    *,
    context_sha256: str,
    manifest: dict,
    manifest_digest: str,
) -> types.MappingProxyType:
    frozen = _validated_frozen_authorization_context(
        manifest["frozen_authorization_context"]
    )
    frozen_to_external = {
        "protocol_id": "protocol_id",
        "protocol_byte_count": "protocol_byte_count",
        "protocol_sha256": "protocol_sha256",
        "authorization_id": "authorization_id",
        "authorization_byte_count": "authorization_byte_count",
        "authorization_sha256": "authorization_sha256",
        "authorization_evidence_id": "authorization_evidence_id",
        "authorization_evidence_byte_count": "authorization_evidence_byte_count",
        "authorization_evidence_sha256": "authorization_evidence_sha256",
        "campaign_measurement_execution_slot_id": (
            "campaign_measurement_execution_slot_id"
        ),
        "logical_occurrence_id": "logical_occurrence_id",
        "execution_nonce": "execution_nonce",
        "campaign_attempt_id": "campaign_attempt_id",
        "cgroup_parent_fact": "cgroup_parent_fact",
        "runtime_capability_fact": "runtime_capability_fact",
    }
    if any(
        context[external_key] != frozen[frozen_key]
        for frozen_key, external_key in frozen_to_external.items()
    ):
        raise RuntimeError("V180r12r4 external context differs from manifest authority")
    if not (
        context["prereg_commit_id"] == manifest["c_pre_commit_id"]
        and context["prelaunch_launch_manifest_sha256"] == manifest_digest
    ):
        raise RuntimeError("V180r12r4 external context manifest provenance changed")
    target = context["target"]
    invocation = context["production_systemd_service_invocation"]
    template = list(manifest["production_systemd_run_argv_templates"][target])
    placeholder = (
        "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
        "__V180R12R4_MATERIALIZATION_TERMINAL_SHA256__"
    )
    actual_environment = (
        "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
        + context["prelaunch_materialization_terminal_sha256"]
    )
    if template.count(placeholder) != 1:
        raise RuntimeError("V180r12r4 systemd invocation template changed")
    template[template.index(placeholder)] = actual_environment
    if not (
        invocation.get("systemd_run_argv") == template
        and template.count("/usr/bin/env") == 1
        and invocation.get("launcher_command")
        == template[template.index("/usr/bin/env") :]
        and invocation.get("umask") == "0077"
    ):
        raise RuntimeError("V180r12r4 exact systemd invocation join changed")
    verified_values: dict[str, object] = {}
    for key in _EXTERNAL_CONTEXT_FIELDS:
        if key == "schema":
            value: object = _VERIFIED_EXTERNAL_CONTEXT_SCHEMA
        elif key in {
            "cgroup_parent_fact",
            "runtime_capability_fact",
            "production_systemd_service_invocation",
            "production_runtime_placement_t1",
            "target_payload",
        }:
            value = _freeze_json_value(context[key])
        elif key == "inherited_fd_roles":
            value = tuple(tuple(row) for row in context[key])
        else:
            value = context[key]
        verified_values[key] = value
    verified_values["external_launch_context_sha256"] = context_sha256
    verified_values["context_consumed_once"] = True
    return types.MappingProxyType(verified_values)


def _consume_internal_context(
    *,
    target: str,
    repository_root: str,
    c_pre_root: str,
    manifest_path: str,
    manifest_digest: str,
    bundle_raw: bytes,
    bundle: dict,
) -> types.MappingProxyType:
    key_raw = _require_sealed_read_only_memfd(
        _INTERNAL_MAC_KEY_FD,
        byte_cap=32,
        exact_byte_count=32,
        label="parent-to-child MAC key",
    )
    context_raw = _require_sealed_read_only_memfd(
        _INTERNAL_CONTEXT_FD,
        byte_cap=64 * 1024,
        label="internal launch context",
    )
    try:
        context_value = json.loads(context_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("V180r12r4 internal launch context is not JSON") from error
    if _canonical_json_bytes(context_value) != context_raw:
        raise RuntimeError("V180r12r4 internal launch context is noncanonical")
    context = _require_exact_dict(
        context_value,
        _internal_context_payload_keys() | {"context_mac"},
        "internal launch context",
    )
    payload = dict(context)
    supplied_mac = _require_sha256(payload.pop("context_mac"), "internal context MAC")
    expected_mac = hashlib.blake2s(
        _canonical_json_bytes(payload), key=key_raw, digest_size=32
    ).hexdigest()
    actor = _INTERNAL_ACTOR_ROLE[target]
    parent = _INTERNAL_PARENT_ROLE[target]
    expected_roles = [
        {"fd": descriptor, "role": role}
        for descriptor, role in _INTERNAL_FD_ROLE_MAP[target]
    ]
    ids = (
        context["protocol_id"],
        context["authorization_id"],
        context["authorization_evidence_id"],
        context["attempt_id"],
        context["campaign_measurement_execution_slot_id"],
        context["logical_occurrence_id"],
        context["execution_nonce"],
        context["prelaunch_materialization_terminal_id"],
        context["prelaunch_launch_rule_id"],
        context["measurement_launch_attempt_id"],
        context["launch_operation_id"],
    )
    target_payload = context["target_payload"]
    if target == "supervisor":
        target_payload_valid = type(target_payload) is dict and target_payload == {
            "repository_root_fd": _SUPERVISOR_REPOSITORY_ROOT_FD,
            "worker_cgroup_fd": _SUPERVISOR_WORKER_CGROUP_FD,
        }
    else:
        target_payload_valid = type(target_payload) is dict and target_payload == {
            "terminal_stage_byte_count": 199_755,
            "verification_stage_byte_count": 2_752,
            "subject_result_initial_byte_count": 0,
        }
    if not (
        supplied_mac == expected_mac
        and context["schema"] == _INTERNAL_CONTEXT_SCHEMA
        and context["target"] == target
        and context["actor_role"] == actor
        and context["parent_actor_role"] == parent
        and all(
            type(value) is str
            and len(value) == 64
            and _require_sha256(value, "context ID")
            for value in ids
        )
        and context["repository_root"] == repository_root
        and context["c_pre_root"] == c_pre_root
        and context["manifest_path"] == manifest_path
        and context["launch_manifest_sha256"] == manifest_digest
        and context["c_pre_commit_id"] == bundle["c_pre_commit_id"]
        and context["precompiled_source_bundle_sha256"]
        == hashlib.sha256(bundle_raw).hexdigest()
        and context["runner_relative_path"] == _TARGET_RUNNER_PATHS[target]
        and context["inherited_fd_roles"] == expected_roles
        and target_payload_valid
        and context["one_shot"] is True
        and context["context_mac_algorithm"] == _INTERNAL_CONTEXT_MAC_ALGORITHM
        and context["context_mac_direction"] == "PARENT_TO_CHILD_ONLY"
    ):
        raise RuntimeError("V180r12r4 internal launch context binding changed")

    for descriptor, role in _INTERNAL_FD_ROLE_MAP[target]:
        if role in {
            "PARENT_TO_CHILD_MAC_KEY_MEMFD",
            "INTERNAL_LAUNCH_CONTEXT_MEMFD",
        }:
            continue
        _validate_operational_descriptor(descriptor, role, context=context)
    os.close(_INTERNAL_MAC_KEY_FD)
    os.close(_INTERNAL_CONTEXT_FD)
    for descriptor, role in _INTERNAL_FD_ROLE_MAP[target]:
        if role not in {
            "PARENT_TO_CHILD_MAC_KEY_MEMFD",
            "INTERNAL_LAUNCH_CONTEXT_MEMFD",
        }:
            os.set_inheritable(descriptor, False)
    return types.MappingProxyType(
        {
            "schema": "acfqp.v180r12r4_verified_internal_launch_context.v1",
            "target": target,
            "actor_role": actor,
            "parent_actor_role": parent,
            "protocol_id": context["protocol_id"],
            "authorization_id": context["authorization_id"],
            "authorization_evidence_id": context["authorization_evidence_id"],
            "attempt_id": context["attempt_id"],
            "campaign_measurement_execution_slot_id": context[
                "campaign_measurement_execution_slot_id"
            ],
            "logical_occurrence_id": context["logical_occurrence_id"],
            "execution_nonce": context["execution_nonce"],
            "prelaunch_materialization_terminal_id": context[
                "prelaunch_materialization_terminal_id"
            ],
            "prelaunch_launch_rule_id": context["prelaunch_launch_rule_id"],
            "measurement_launch_attempt_id": context[
                "measurement_launch_attempt_id"
            ],
            "launch_operation_id": context["launch_operation_id"],
            "manifest_sha256": manifest_digest,
            "precompiled_source_bundle_sha256": context[
                "precompiled_source_bundle_sha256"
            ],
            "inherited_fd_roles": tuple(
                (row["fd"], row["role"]) for row in expected_roles
            ),
            "target_payload": types.MappingProxyType(dict(target_payload)),
            "parent_to_child_mac_key": key_raw,
            "parent_context_mac": supplied_mac,
            "context_consumed_once": True,
        }
    )


class _InternalNoSubprocessAudit:
    def __call__(self, event: str, arguments: tuple) -> None:
        del arguments
        if event == "subprocess.Popen":
            raise RuntimeError("V180r12r4 internal target subprocess is forbidden")

    @staticmethod
    def require_complete() -> None:
        return None


class _RunnerSecondaryObservation(RuntimeError):
    def __init__(self, observations: tuple[BaseException, ...]) -> None:
        if not observations or len(observations) > 8:
            raise ValueError("secondary observations must be nonempty")
        self.observations = observations
        summary = "; ".join(
            f"{_bounded_exception_type_name(error)}: "
            f"{_bounded_exception_message(error)}"
            for error in observations
        )
        super().__init__(f"V180r12r4 runner secondary observations: {summary}")


def _bounded_text(value: str, byte_cap: int) -> str:
    if type(value) is not str or type(byte_cap) is not int or byte_cap <= 0:
        return "<unavailable>"
    # Slice before encoding so an attacker-controlled giant string cannot force
    # an equally giant temporary allocation on this failure path.
    encoded = value[:byte_cap].encode("utf-8", "replace")[:byte_cap]
    return encoded.decode("utf-8", "ignore")


def _bounded_exception_type_name(error: BaseException) -> str:
    try:
        name = type.__getattribute__(type(error), "__name__")
    except BaseException:
        return "BaseException"
    return _bounded_text(name, 128)


def _bounded_exception_message(error: BaseException) -> str:
    try:
        arguments = BaseException.__getattribute__(error, "args")
    except BaseException:
        return "<unavailable>"
    if type(arguments) is not tuple:
        return "<unavailable>"
    rendered: list[str] = []
    for argument in arguments[:8]:
        if type(argument) is str:
            rendered.append(_bounded_text(argument, 1_024))
        elif type(argument) in {int, bool, float} or argument is None:
            rendered.append(_bounded_text(str(argument), 1_024))
        else:
            rendered.append(f"<{_bounded_exception_type_name(argument)}>")
    if len(arguments) > 8:
        rendered.append("<additional arguments omitted>")
    if len(rendered) == 1:
        return rendered[0]
    return _bounded_text("(" + ", ".join(rendered) + ")", 1_024)


def _raise_preserved_runner_primary(
    primary_error: BaseException,
    primary_traceback: object,
    secondary: BaseException | None,
) -> None:
    restored = BaseException.with_traceback(primary_error, primary_traceback)
    if secondary is not None:
        raise restored from secondary
    raise restored


def _execute_precompiled_runner(
    code: object,
    source_path: str,
    records: dict[str, tuple[object, str, bool]],
    git_audit: object,
    *,
    verified_internal_context: types.MappingProxyType,
) -> None:
    if type(verified_internal_context) is not types.MappingProxyType:
        raise RuntimeError(
            "V180r12r4 runner requires an exact verified context mapping"
        )
    target = verified_internal_context.get("target")
    if type(target) is not str or target not in _RUNNER_MODULE_NAMES:
        raise RuntimeError("V180r12r4 verified runner target changed")
    module_name = _RUNNER_MODULE_NAMES[target]
    module_registry = sys.modules
    if type(module_registry) is not dict:
        raise RuntimeError("V180r12r4 interpreter module registry changed")
    if module_name in module_registry:
        raise RuntimeError(
            "V180r12r4 target runner module was registered before dispatch"
        )

    namespaces = {"acfqp", "packaging", "tomli"}
    if any(name.split(".", 1)[0] in namespaces for name in sys.modules):
        raise RuntimeError("V180r12r4 bound source was imported before dispatch")
    loader = _BoundSourceLoader(records)
    original_meta_path = list(sys.meta_path)
    original_sys_path = list(sys.path)
    sys.meta_path.insert(0, loader)
    sys.addaudithook(git_audit)
    sys.addaudithook(_BoundImportAudit(frozenset(records)))
    sys.argv = [source_path]
    runner_module = types.ModuleType(module_name)
    expected_metadata = {
        "__name__": module_name,
        "__file__": source_path,
        "__package__": None,
        "__cached__": None,
        "__loader__": None,
        "__spec__": None,
    }
    runner_module.__dict__.update(expected_metadata)
    try:
        module_registry[module_name] = runner_module
        runner_namespace = runner_module.__dict__
        primary_error: BaseException | None = None
        primary_traceback = None
        try:
            exec(code, runner_namespace)
            if "bootstrap_entrypoint_v180r12r4" not in runner_namespace:
                raise RuntimeError(
                    "V180r12r4 runner bootstrap entrypoint is absent"
                )
            entrypoint = runner_namespace["bootstrap_entrypoint_v180r12r4"]
            if not callable(entrypoint):
                raise RuntimeError(
                    "V180r12r4 runner bootstrap entrypoint is not callable"
                )
            if entrypoint(verified_internal_context) is not None:
                raise RuntimeError(
                    "V180r12r4 runner bootstrap entrypoint return changed"
                )
        except BaseException as error:
            primary_error = error
            primary_traceback = BaseException.__getattribute__(
                error, "__traceback__"
            )

        secondary_errors: list[BaseException] = []

        def observe(check) -> None:
            try:
                check()
            except BaseException as error:
                secondary_errors.append(error)

        def check_meta_path() -> None:
            if sys.meta_path != [loader, *original_meta_path]:
                raise RuntimeError(
                    "V180r12r4 bound meta_path changed during dispatch"
                )

        def check_sys_path() -> None:
            if sys.path != original_sys_path:
                raise RuntimeError(
                    "V180r12r4 runner changed the sealed sys.path"
                )

        def check_runner_module() -> None:
            if sys.modules is not module_registry:
                raise RuntimeError(
                    "V180r12r4 runner replaced the interpreter module registry"
                )
            missing = object()
            registered = module_registry.get(module_name, missing)
            if registered is missing:
                raise RuntimeError(
                    "V180r12r4 target runner module registration was deleted"
                )
            if registered is not runner_module:
                raise RuntimeError(
                    "V180r12r4 target runner module registration was replaced"
                )
            for field_name in _RUNNER_MODULE_METADATA_FIELDS:
                observed_value = runner_namespace.get(field_name, missing)
                expected_value = expected_metadata[field_name]
                changed = (
                    observed_value is not None
                    if expected_value is None
                    else type(observed_value) is not str
                    or observed_value != expected_value
                )
                if changed:
                    raise RuntimeError(
                        "V180r12r4 target runner module metadata changed: "
                        + field_name
                    )

        def check_loaded_modules() -> None:
            for name, module in tuple(sys.modules.items()):
                if name.split(".", 1)[0] not in namespaces:
                    continue
                if (
                    name not in records
                    or getattr(module, "__loader__", None) is not loader
                ):
                    raise RuntimeError(
                        f"V180r12r4 non-bound source module loaded: {name}"
                    )
                _, expected_path, _ = records[name]
                if (
                    getattr(module, "__file__", None) != expected_path
                    or getattr(module, "__cached__", None) is not None
                ):
                    raise RuntimeError(
                        f"V180r12r4 bound source origin changed: {name}"
                    )

        observe(check_runner_module)
        observe(check_meta_path)
        observe(check_sys_path)
        observe(git_audit.require_complete)
        observe(check_loaded_modules)
        secondary = (
            _RunnerSecondaryObservation(tuple(secondary_errors))
            if secondary_errors
            else None
        )
        if primary_error is not None:
            _raise_preserved_runner_primary(
                primary_error, primary_traceback, secondary
            )
        if secondary is not None:
            raise secondary
    finally:
        active_registry = sys.modules
        if type(active_registry) is dict and active_registry is not module_registry:
            active_registry.pop(module_name, None)
        sys.modules = module_registry
        module_registry.pop(module_name, None)


def _execute_precompiled_runner_before_campaign_deadline(
    code: object,
    source_path: str,
    records: dict[str, tuple[object, str, bool]],
    git_audit: object,
    *,
    verified_internal_context: types.MappingProxyType,
) -> None:
    if time.clock_gettime_ns(time.CLOCK_MONOTONIC) >= verified_internal_context[
        "campaign_deadline_ns"
    ]:
        raise RuntimeError(
            "V180r12r4 bootstrap prework exhausted the shared campaign deadline"
        )
    _execute_precompiled_runner(
        code,
        source_path,
        records,
        git_audit,
        verified_internal_context=verified_internal_context,
    )


def _require_internal_runtime_boundary(
    *,
    target: str,
    repository_text: str,
    c_pre_text: str,
    manifest_text: str,
) -> tuple[str, str, str]:
    for value, label in (
        (repository_text, "repository root"),
        (c_pre_text, "C_pre root"),
        (manifest_text, "launch manifest"),
    ):
        path = PurePosixPath(value)
        if (
            type(value) is not str
            or not path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or path.as_posix() != value
        ):
            raise RuntimeError(f"V180r12r4 internal {label} path changed")
    bootstrap_path = f"{c_pre_text}/bootstrap.py"
    if (
        target not in _INTERNAL_TARGETS
        or sys.executable != _EXPECTED_EXECUTABLE
        or sys.pycache_prefix != _EXPECTED_PYCACHE_PREFIX
        or sys.dont_write_bytecode is not True
        or {name: getattr(sys.flags, name) for name in _EXPECTED_FLAGS}
        != _EXPECTED_FLAGS
        or sys.orig_argv
        != [
            *_ORIG_ARGV_PREFIX,
            bootstrap_path,
            target,
            repository_text,
            c_pre_text,
            manifest_text,
        ]
        or sys.argv
        != [bootstrap_path, target, repository_text, c_pre_text, manifest_text]
        or str(Path(__file__).absolute()) != bootstrap_path
        or manifest_text != f"{c_pre_text}/launch_manifest.json"
        or str(Path.cwd()) != repository_text
    ):
        raise RuntimeError("V180r12r4 internal runtime, argv, cwd, or path changed")
    return repository_text, c_pre_text, manifest_text


def _run_internal_target(
    *,
    target: str,
    repository_text: str,
    c_pre_text: str,
    manifest_text: str,
    manifest_digest: str,
) -> None:
    """Consume only sealed pre-attempt code/context; never read working-tree source."""

    repository_text, c_pre_text, manifest_text = _require_internal_runtime_boundary(
        target=target,
        repository_text=repository_text,
        c_pre_text=c_pre_text,
        manifest_text=manifest_text,
    )
    _require_exact_internal_descriptor_inventory(target)
    bundle_raw = _require_sealed_read_only_memfd(
        _PRECOMPILED_BUNDLE_FD,
        byte_cap=_SOURCE_CLOSURE_TOTAL_BYTE_CAP,
        label="precompiled source bundle",
    )
    records, runner_code, runner_path, bundle = _load_precompiled_bundle(
        bundle_raw,
        target=target,
        manifest_digest=manifest_digest,
        repository_root=repository_text,
        c_pre_root=c_pre_text,
        manifest_path=manifest_text,
    )
    verified_context = _consume_internal_context(
        target=target,
        repository_root=repository_text,
        c_pre_root=c_pre_text,
        manifest_path=manifest_text,
        manifest_digest=manifest_digest,
        bundle_raw=bundle_raw,
        bundle=bundle,
    )
    os.environ[_PREREG_COMMIT_ENV] = bundle["c_pre_commit_id"]
    if set(os.environ) != {_MANIFEST_SHA_ENV, _PREREG_COMMIT_ENV, "LC_CTYPE"}:
        raise RuntimeError("V180r12r4 internal runner environment injection changed")
    _execute_precompiled_runner(
        runner_code,
        runner_path,
        records,
        _InternalNoSubprocessAudit(),
        verified_internal_context=verified_context,
    )


def main() -> None:
    manifest_digest = _require_sanitized_environment()
    if len(sys.argv) != 5 or sys.argv[1] not in _TARGET_RUNNER_PATHS:
        raise RuntimeError(
            "V180r12r4 bootstrap API is target, repository root, C_pre root, manifest"
        )
    target, repository_text, c_pre_text, manifest_text = sys.argv[1:]
    if target in _INTERNAL_TARGETS:
        _run_internal_target(
            target=target,
            repository_text=repository_text,
            c_pre_text=c_pre_text,
            manifest_text=manifest_text,
            manifest_digest=manifest_digest,
        )
        return
    external_context, external_context_sha256 = _consume_external_context_at_entry(
        target=target,
        repository_text=repository_text,
        c_pre_text=c_pre_text,
        manifest_text=manifest_text,
        manifest_digest=manifest_digest,
    )
    repository_root = _validated_root(repository_text, "repository root")
    c_pre_root = _validated_root(c_pre_text, "C_pre root")
    manifest_relative = _relative_to_root(
        manifest_text, c_pre_root, "launch manifest"
    )
    manifest_path = c_pre_root / manifest_relative
    manifest_raw = _stable_read(
        c_pre_root,
        manifest_relative,
        "launch manifest",
        byte_cap=_MANIFEST_BYTE_CAP,
        expected_sha256=manifest_digest,
    )
    try:
        manifest_value = json.loads(manifest_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("V180r12r4 launch manifest is not canonical JSON") from error
    if _canonical_json_bytes(manifest_value) != manifest_raw:
        raise RuntimeError("V180r12r4 launch manifest bytes are not canonical")
    manifest = _validated_manifest(
        manifest_value, repository_root, c_pre_root, manifest_relative
    )
    verified_external_context = _verify_external_context_against_manifest(
        external_context,
        context_sha256=external_context_sha256,
        manifest=manifest,
        manifest_digest=manifest_digest,
    )
    third_party_facts, normalized_wrapper_fact = (
        _validate_manifest_resource_contract(manifest, repository_root)
    )

    bootstrap_fact = _require_exact_dict(
        manifest["bootstrap"], _RAW_FACT_KEYS, "bootstrap raw fact"
    )
    bootstrap_relative = _validated_relative_path(
        bootstrap_fact["relative_path"], "bootstrap path"
    )
    bootstrap_path = c_pre_root / bootstrap_relative
    if Path(__file__).absolute() != bootstrap_path or sys.argv[0] != str(bootstrap_path):
        raise RuntimeError("V180r12r4 executing bootstrap path changed")
    _verify_raw_fact(
        c_pre_root,
        bootstrap_fact,
        "executing bootstrap",
        expected_relative_path=bootstrap_relative,
        byte_cap=_BOOTSTRAP_BYTE_CAP,
    )
    _require_runtime_boundary(
        manifest["runtime"],
        bootstrap_path,
        target,
        repository_root,
        c_pre_root,
        manifest_path,
    )
    commit_id = manifest["c_pre_commit_id"]
    git_audit = _validated_git_boundary(
        manifest["git"], repository_root, manifest_digest, commit_id
    )

    records = _compile_bound_sources(
        manifest, repository_root, normalized_wrapper_fact
    )
    third_party_records = _compile_third_party_sources(third_party_facts)
    if set(records) & set(third_party_records):
        raise RuntimeError("V180r12r4 source namespace collision")
    records.update(third_party_records)
    (runner_code, runner_path), compiled_runners = _compile_runners(
        manifest, repository_root, target
    )
    bundle_raw, bundle_digest, native_zero_rows = _create_precompiled_bundle(
        records=records,
        runners=compiled_runners,
        manifest_digest=manifest_digest,
        commit_id=commit_id,
        repository_root=repository_root,
        c_pre_root=c_pre_root,
        manifest_path=manifest_path,
        install_descriptor=target == "measurement",
    )
    # These are bootstrap-derived, verified-only values.  They are absent from
    # caller-controlled FD249 and are rebuilt independently by measurement and
    # verification from the same manifest-bound compilation population.
    verified_external_context = types.MappingProxyType(
        {
            **{
                key: verified_external_context[key]
                for key in _EXTERNAL_CONTEXT_FIELDS
            },
            "precompiled_source_bundle_sha256": bundle_digest,
            "native_zero_precompiled_source_rows": tuple(
                types.MappingProxyType(dict(row)) for row in native_zero_rows
            ),
            "external_launch_context_sha256": verified_external_context[
                "external_launch_context_sha256"
            ],
            "context_consumed_once": True,
        }
    )
    if hashlib.sha256(bundle_raw).hexdigest() != bundle_digest:
        raise RuntimeError("V180r12r4 rebuilt precompiled bundle digest changed")
    if target == "measurement":
        os.set_inheritable(_PRECOMPILED_BUNDLE_FD, False)
    os.environ[_PREREG_COMMIT_ENV] = commit_id
    if set(os.environ) != {_MANIFEST_SHA_ENV, _PREREG_COMMIT_ENV, "LC_CTYPE"}:
        raise RuntimeError("V180r12r4 runner environment injection changed")
    _execute_precompiled_runner_before_campaign_deadline(
        runner_code,
        runner_path,
        records,
        git_audit,
        verified_internal_context=verified_external_context,
    )


if __name__ == "__main__":
    main()
