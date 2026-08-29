#!/usr/bin/python3
"""Materialize the source-bound V180r12r4 prelaunch exactly once.

This stdlib-only construction step consumes an externally supplied immutable
root record.  That record chooses the exact preregistration commit (``C_pre``);
this program never infers or substitutes it from ``HEAD``.  The program then
checks the exact C_pre -> empty same-tree bridge -> wrapper-only literal commit
history, constructs a launch manifest from C_pre Git blobs plus the independently
normalized current wrapper, and writes the retained bootstrap, manifest, and
terminal with write-once durability.  It does not authorize or execute a
V180r12r4 scientific occurrence.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import sysconfig
import tarfile
import tokenize
from typing import Any, NoReturn, Sequence


EXTERNAL_ROOT_SCHEMA = "acfqp.v180r12r4_prelaunch_external_root.v1"
LAUNCH_MANIFEST_SCHEMA = "acfqp.v180r12r4_source_bound_launch_manifest.v1"
MATERIALIZATION_TERMINAL_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_materialization_terminal.v1"
)
MATERIALIZATION_FAILURE_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_materialization_failure.v1"
)

OUTPUT_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_prelaunch"
)
EXTERNAL_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_external_root.json"
)
BOOTSTRAP_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/bootstrap.py"
RETAINED_LAUNCHER_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/launcher.py"
LAUNCH_MANIFEST_RELATIVE_PATH = (
    f"{OUTPUT_ROOT_RELATIVE_PATH}/launch_manifest.json"
)
MATERIALIZATION_TERMINAL_RELATIVE_PATH = (
    f"{OUTPUT_ROOT_RELATIVE_PATH}/MATERIALIZATION_TERMINAL.json"
)
MATERIALIZATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_failure.json"
)

MATERIALIZER_RELATIVE_PATH = (
    "scripts/materialize_v180r12r4_campaign_measurement_prelaunch.py"
)
SOURCE_BOOTSTRAP_RELATIVE_PATH = (
    "scripts/bootstrap_v180r12r4_campaign_measurement.py"
)
SOURCE_LAUNCHER_RELATIVE_PATH = (
    "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py"
)
PROTOCOL_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_protocol_v180r12r4.py"
)
AUTHORIZATION_SELF_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_execution_authorization_v180r12r4.py"
)
AUTHORIZATION_SELF_MODULE = (
    "acfqp."
    "construction_k7_campaign_measurement_execution_authorization_v180r12r4"
)
AUTHORIZATION_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_campaign_measurement_"
    "authorization_evidence_freeze_v180r12r4.py"
)
AUTHORIZATION_EVIDENCE_MODULE = (
    "acfqp.construction_k7_campaign_measurement_"
    "authorization_evidence_freeze_v180r12r4"
)
PROTOCOL_FINAL_ANCHOR_NAMES = (
    "EXPECTED_PROTOCOL_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID",
    "LOGICAL_OCCURRENCE_ID",
    "EXECUTION_NONCE",
    "EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID",
    "EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID",
    "EXPECTED_PRELAUNCH_LAUNCH_RULE_ID",
)
AUTHORIZATION_FINAL_ANCHOR_NAMES = (
    "EXPECTED_PROTOCOL_ID",
    "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID",
)
MATERIALIZER_FINAL_ANCHOR_NAMES = (
    "EXPECTED_SOURCE_CLOSURE_RULE_ID",
    "EXPECTED_MATERIALIZATION_RULE_ID",
)
LAUNCHER_FINAL_ANCHOR_NAMES = (
    "EXPECTED_SOURCE_CLOSURE_RULE_ID",
    "EXPECTED_MATERIALIZATION_RULE_ID",
    "EXPECTED_LAUNCH_RULE_ID",
)
MANIFEST_SHA256_ENV = "ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256"
PREREG_COMMIT_ENV = "ACFQP_V180R12R4_PREREG_COMMIT"
TARGET_RUNNER_PATHS = {
    "measurement": "scripts/run_v180r12r4_campaign_measurement.py",
    "verification": "scripts/verify_v180r12r4_campaign_measurement.py",
    "supervisor": "scripts/supervise_v180r12r4_campaign_measurement.py",
    "worker": "scripts/work_v180r12r4_campaign_measurement.py",
}
RUNNER_MODULE_NAMES = {
    target: f"_acfqp_v180r12r4_precompiled_runner_{target}"
    for target in TARGET_RUNNER_PATHS
}
RUNNER_MODULE_METADATA_FIELDS = (
    "__name__",
    "__file__",
    "__package__",
    "__cached__",
    "__loader__",
    "__spec__",
)
EXTERNAL_TARGETS = ("measurement", "verification")
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
INTERNAL_CONTEXT_SCHEMA = "acfqp.v180r12r4_internal_launch_context.v1"
PRECOMPILED_BUNDLE_SCHEMA = (
    "acfqp.v180r12r4_precompiled_source_bundle.v1"
)
INTERNAL_CONTEXT_MAC_ALGORITHM = "BLAKE2S_KEYED_256"
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
INTERNAL_FD_RULES = {
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
    "injected_environment_key": PREREG_COMMIT_ENV,
    "dynamic_identity_in_argv_or_environment": False,
    "context_schema": INTERNAL_CONTEXT_SCHEMA,
    "context_mac_algorithm": INTERNAL_CONTEXT_MAC_ALGORITHM,
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
    "precompiled_bundle_schema": PRECOMPILED_BUNDLE_SCHEMA,
    "precompiled_before_campaign_attempt": True,
    "internal_target_reads_working_tree_source": False,
    "precompiled_runner_module_contract": {
        "module_type": "types.ModuleType",
        "target_order": list(TARGET_RUNNER_PATHS),
        "target_rows": [
            {"target": target, "module_name": RUNNER_MODULE_NAMES[target]}
            for target in TARGET_RUNNER_PATHS
        ],
        "exact_metadata_fields": list(RUNNER_MODULE_METADATA_FIELDS),
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
            "runner_relative_path": TARGET_RUNNER_PATHS[target],
            "actor_role": {"supervisor": "SUPERVISOR", "worker": "WORKER"}[target],
            "parent_actor_role": {"supervisor": "OBSERVER", "worker": "SUPERVISOR"}[target],
            "inherited_fd_roles": [
                {
                    "fd": descriptor,
                    "role": role,
                    "kind": INTERNAL_FD_RULES[role][0],
                    "access": INTERNAL_FD_RULES[role][1],
                    "mode": INTERNAL_FD_RULES[role][2],
                    "required_seals": (
                        ["F_SEAL_SEAL", "F_SEAL_SHRINK", "F_SEAL_GROW", "F_SEAL_WRITE"]
                        if INTERNAL_FD_RULES[role][3]
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
_AUTHORIZATION_SOURCE_FACT_IDENTITY_FIELDS = (
    "relative_path",
    "byte_count",
    "sha256",
)

SOURCE_CLOSURE_REQUIRED_ROOTS = tuple(
    sorted(
        (
            SOURCE_BOOTSTRAP_RELATIVE_PATH,
            SOURCE_LAUNCHER_RELATIVE_PATH,
            MATERIALIZER_RELATIVE_PATH,
            TARGET_RUNNER_PATHS["measurement"],
            "scripts/supervise_v180r12r4_campaign_measurement.py",
            TARGET_RUNNER_PATHS["verification"],
            "scripts/work_v180r12r4_campaign_measurement.py",
            "src/acfqp/construction_accounting_registry_v6.py",
            "src/acfqp/construction_k7_domain_registry_extension_v180r12r4.py",
            "src/acfqp/construction_k7_domain_registry_extension_v180r12r4e.py",
            "src/acfqp/construction_k7_campaign_measurement_ledger_v180r12r4.py",
            PROTOCOL_SOURCE_RELATIVE_PATH,
            AUTHORIZATION_SELF_RELATIVE_PATH,
            AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
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
                "independent_verifier_v180r12r4.py"
            ),
            (
                "src/acfqp/construction_k7_ten_terminal_aggregation_"
                "production_evidence_freeze_v180r12r2.py"
            ),
        )
    )
)
_PRELAUNCH_SPECIAL_GIT_BLOB_PATHS = (
    SOURCE_BOOTSTRAP_RELATIVE_PATH,
    SOURCE_LAUNCHER_RELATIVE_PATH,
    MATERIALIZER_RELATIVE_PATH,
)
_ORDINARY_SOURCE_ROOTS = tuple(
    path
    for path in SOURCE_CLOSURE_REQUIRED_ROOTS
    if path
    not in {
        *_PRELAUNCH_SPECIAL_GIT_BLOB_PATHS,
        AUTHORIZATION_SELF_RELATIVE_PATH,
        AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
    }
)

PYTHON_EXECUTABLE = "/usr/bin/python3"
GIT_EXECUTABLE = "/usr/bin/git"
PYCACHE_PREFIX = "/dev/null/v180r12r4"
EXTERNAL_ROOT_SHA256_ENV = "ACFQP_V180R12R4_EXTERNAL_ROOT_SHA256"
MANIFEST_SHA256_TEMPLATE = "__V180R12R4_MANIFEST_SHA256__"
MATERIALIZATION_TERMINAL_SHA256_TEMPLATE = (
    "__V180R12R4_MATERIALIZATION_TERMINAL_SHA256__"
)
ZERO_ID = "0" * 64
PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN = (
    "acfqp:construction-k7-production-transient-service-token:v180r12r4"
)
PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN = (
    "c8d74b0ae750955932b08df9de7a3566368ba20e94ccb16696037c0446577bb6"
)
PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME = (
    "acfqp-v180r12r4-measurement-"
    + PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN
    + ".service"
)
PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN = (
    "293c9c9fb1424204ccdba376bc48dd150d7d03139f7a263e6d5691abf61c20a3"
)
PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME = (
    "acfqp-v180r12r4-verification-"
    + PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN
    + ".service"
)
PRODUCTION_TRANSIENT_SERVICE_SLICE = "app.slice"
PRODUCTION_SERVICE_CONTRACT_SCHEMA = (
    "acfqp.v180r12r4_production_systemd_service_contracts.v1"
)
ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA = (
    "acfqp.v180r12r4_atomic_cgroup_birth_preflight_receipt_interface.v1"
)
ISOLATED_ARGV_PREFIX = (
    PYTHON_EXECUTABLE,
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={PYCACHE_PREFIX}",
)
AUTHORIZATION_SOURCE_CLOSURE_KIND = (
    "EXACT_RAW_AUTHORIZATION_SOURCE_CLOSURE_PLUS_AUTH_SELF_AND_BOUND_RUNNERS"
)
NORMALIZED_WRAPPER_BINDING_KIND = "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"

EXTERNAL_ROOT_BYTE_CAP = 1024 * 1024
BOOTSTRAP_BYTE_CAP = 1024 * 1024
LAUNCHER_BYTE_CAP = 1024 * 1024
MATERIALIZER_BYTE_CAP = 2 * 1024 * 1024
LAUNCH_MANIFEST_BYTE_CAP = 16 * 1024 * 1024
RUNNER_BYTE_CAP = 4 * 1024 * 1024
SOURCE_FILE_BYTE_CAP = 8 * 1024 * 1024
SOURCE_CLOSURE_FILE_CAP = 4096
SOURCE_CLOSURE_TOTAL_BYTE_CAP = 128 * 1024 * 1024
EXECUTABLE_BYTE_CAP = 64 * 1024 * 1024
GIT_ARCHIVE_BYTE_CAP = 256 * 1024 * 1024
GIT_COMMAND_TIMEOUT_SECONDS = 120
FAILURE_MESSAGE_BYTE_CAP = 4096

EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "e632515031d29fbe77f59dbe3bbe8255797a33c11142548279d319ba32166fb3"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "d9845516a7f71827dadca0b42dfd75ee272fe514cfcb9e598080bde254dc6034"
)
LAUNCHER_RULE_LITERAL_NAMES = (
    "EXPECTED_SOURCE_CLOSURE_RULE_ID",
    "EXPECTED_MATERIALIZATION_RULE_ID",
    "EXPECTED_LAUNCH_RULE_ID",
)
LAUNCHER_NORMALIZED_STATIC_RULE_SOURCE_BYTE_COUNT = 245_153
LAUNCHER_NORMALIZED_STATIC_RULE_SOURCE_SHA256 = (
    "31e6ab5927ac1ca2cd8011ea061b1bcd8dde2884856ae19af6cb61b847d43c71"
)

SOURCE_CLOSURE_RULE_DOCUMENT = {
    "schema": "acfqp.v180r12r4_prelaunch_source_closure_rule.v1",
    "required_static_root_paths": list(SOURCE_CLOSURE_REQUIRED_ROOTS),
    "ordinary_source_root_paths": list(_ORDINARY_SOURCE_ROOTS),
    "authorization_self_relative_path": AUTHORIZATION_SELF_RELATIVE_PATH,
    "authorization_self_excluded_from_recursive_closure": True,
    "recursive_rule": "STATIC_LOCAL_ACFQP_IMPORTS_PLUS_PARENT_PACKAGES",
    "runner_binding": "C_PRE_RAW_GIT_BLOBS",
    "ordinary_binding": "C_PRE_RAW_GIT_BLOBS",
    "authorization_self_binding": "C_PRE_RAW_GIT_BLOB",
    "wrapper_binding": NORMALIZED_WRAPPER_BINDING_KIND,
    "wrapper_redacted_constant_names": list(WRAPPER_REDACTED_CONSTANT_NAMES),
    "third_party_namespaces": ["packaging", "tomli"],
    "third_party_binding": "COMPLETE_LIVE_PY_SOURCE_NAMESPACE_SNAPSHOT",
    "prelaunch_special_git_blob_paths": list(_PRELAUNCH_SPECIAL_GIT_BLOB_PATHS),
    "authorization_source_closure_binding": (
        "EXACT_REQUIRED_STATIC_ROOTS_WITH_NORMALIZED_WRAPPER"
    ),
    "execution_loader_binding": "TRANSITIVE_LOCAL_IMPORT_CLOSURE",
    "working_tree_source_property_contract": (
        "ALL_REQUIRED_STATIC_ROOTS_REGULAR_SINGLE_LINK_GIT_MODE_MAPPED_"
        "STABLE_BYTES_SHA256_AND_GIT_BLOB"
    ),
    "working_tree_source_property_snapshot_fields": [
        "st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    ],
    "working_tree_source_conformance_precedes_prelaunch_output": True,
    "working_tree_source_mismatch_is_per_path_per_field": True,
}
MATERIALIZATION_RULE_DOCUMENT = {
    "schema": "acfqp.v180r12r4_prelaunch_materialization_rule.v1",
    "external_root_schema": EXTERNAL_ROOT_SCHEMA,
    "launch_manifest_schema": LAUNCH_MANIFEST_SCHEMA,
    "terminal_schema": MATERIALIZATION_TERMINAL_SCHEMA,
    "failure_schema": MATERIALIZATION_FAILURE_SCHEMA,
    "external_root_relative_path": EXTERNAL_ROOT_RELATIVE_PATH,
    "output_root_relative_path": OUTPUT_ROOT_RELATIVE_PATH,
    "bootstrap_relative_path": BOOTSTRAP_RELATIVE_PATH,
    "retained_launcher_relative_path": RETAINED_LAUNCHER_RELATIVE_PATH,
    "launch_manifest_relative_path": LAUNCH_MANIFEST_RELATIVE_PATH,
    "terminal_relative_path": MATERIALIZATION_TERMINAL_RELATIVE_PATH,
    "failure_relative_path": MATERIALIZATION_FAILURE_RELATIVE_PATH,
    "git_history_rule": "EXACT_C_PRE_EMPTY_SAME_TREE_BRIDGE_WRAPPER_ONLY_LITERAL_HEAD",
    "write_rule": "O_EXCL_O_NOFOLLOW_CLOEXEC_0700_DIR_0400_FILES_FSYNC_TERMINAL_LAST",
    "rerun_rule": "ANY_PROGRESS_OR_TERMINAL_OR_FAILURE_FORBIDS_SAME_IDENTITY_RERUN",
    "identity_cycle_rule": "MANIFEST_DIGEST_RECORDED_ONLY_AFTER_MANIFEST_SERIALIZATION",
    "construction_only": True,
    "preauthorization": True,
    "campaign_actual_measurement": False,
    "bootstrap_byte_cap": BOOTSTRAP_BYTE_CAP,
    "launcher_byte_cap": LAUNCHER_BYTE_CAP,
    "materializer_byte_cap": MATERIALIZER_BYTE_CAP,
    "external_root_byte_cap": EXTERNAL_ROOT_BYTE_CAP,
    "launch_manifest_byte_cap": LAUNCH_MANIFEST_BYTE_CAP,
    "runner_byte_cap": RUNNER_BYTE_CAP,
    "source_file_byte_cap": SOURCE_FILE_BYTE_CAP,
    "source_closure_file_cap": SOURCE_CLOSURE_FILE_CAP,
    "source_closure_total_byte_cap": SOURCE_CLOSURE_TOTAL_BYTE_CAP,
    "executable_byte_cap": EXECUTABLE_BYTE_CAP,
    "git_archive_byte_cap": GIT_ARCHIVE_BYTE_CAP,
    "git_command_timeout_seconds": GIT_COMMAND_TIMEOUT_SECONDS,
    "failure_message_byte_cap": FAILURE_MESSAGE_BYTE_CAP,
    "launcher_rule_literal_names": list(LAUNCHER_RULE_LITERAL_NAMES),
    "launcher_normalized_static_rule_source_byte_count": (
        LAUNCHER_NORMALIZED_STATIC_RULE_SOURCE_BYTE_COUNT
    ),
    "launcher_normalized_static_rule_source_sha256": (
        LAUNCHER_NORMALIZED_STATIC_RULE_SOURCE_SHA256
    ),
    "launcher_source_changes_outside_three_rule_literals_forbidden": True,
    "wrapper_authorization_and_evidence_six_fields_join_external_context_before_output": True,
    "authorization_self_source_fact_joins_c_pre_raw_blob_before_output": True,
    "authorization_source_closure_identity_rederived_before_output": True,
    "authorization_source_closure_fact_identity_fields": list(
        _AUTHORIZATION_SOURCE_FACT_IDENTITY_FIELDS
    ),
    "production_transient_service_token_domain": (
        PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN
    ),
    "production_measurement_transient_service_token": (
        PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN
    ),
    "production_measurement_transient_service_unit_name": (
        PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME
    ),
    "production_verification_transient_service_token": (
        PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN
    ),
    "production_verification_transient_service_unit_name": (
        PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME
    ),
    "production_transient_service_slice": PRODUCTION_TRANSIENT_SERVICE_SLICE,
    "production_service_is_service_not_scope": True,
    "production_service_type": "exec",
    "production_service_delegate": True,
    "atomic_cgroup_birth_preflight_receipt_interface_is_zero_authority": True,
    "working_tree_source_conformance_precedes_campaign_and_unit_ownership": True,
    "source_conformance_and_unit_ownership_are_distinct": True,
    "typed_source_conformance_diagnostic_retained_on_failure": True,
}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _zero_preflight_receipt_interface() -> dict[str, Any]:
    return {
        "schema": ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA,
        "receipt_id": ZERO_ID,
        "receipt_byte_count": 0,
        "receipt_sha256": ZERO_ID,
        "authority_accepted": False,
        "production_launch_authorized": False,
    }


def _production_systemd_service_contract() -> dict[str, Any]:
    base = {
        "failed_predecessor_freeze_id": (
            "296731d463b996bb4ff57133505babab9b5d7a3117d6fcdaa94b8ecb1e1050d0"
        ),
        "failed_inner_launch_failure_id": (
            "a08d14c74426ecc83a23d2851cced5f52f23fd8b99c11f9230846cb7df4ecd7a"
        ),
        "failed_outer_service_failure_id": (
            "975593a7652cd71314c203a27d87b7071e9b344d983dc2b72448e1627c45146c"
        ),
        "repair_scope": (
            "WORKING_TREE_SOURCE_MODE_CONFORMANCE_AND_TYPED_DIAGNOSTIC"
        ),
    }
    token_rows = {
        "measurement": (
            {**base, "purpose": "MEASUREMENT"},
            PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN,
            PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME,
        ),
        "verification": (
            {**base, "purpose": "VERIFICATION"},
            PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN,
            PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME,
        ),
    }
    rows: list[dict[str, Any]] = []
    for target in ("measurement", "verification"):
        token_input, token, unit_name = token_rows[target]
        observed_token = hashlib.sha256(
            PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN.encode("ascii")
            + b"\x00"
            + canonical_json_bytes(token_input)
        ).hexdigest()
        if observed_token != token:
            _fail("production transient-service lineage token changed")
        command_template = [
            "/usr/bin/env", "-i",
            "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
            + MATERIALIZATION_TERMINAL_SHA256_TEMPLATE,
            "LC_CTYPE=C.UTF-8", *ISOLATED_ARGV_PREFIX,
            "{repository_root}/" + RETAINED_LAUNCHER_RELATIVE_PATH,
            "service-entry", target, "{repository_root}",
        ]
        rows.append(
            {
                "target": target,
                "token_input": token_input,
                "token": token,
                "unit_name": unit_name,
                "outer_dispatch_cwd_template": "{repository_root}",
                "outer_dispatch_argv_template": [
                    "/usr/bin/env", "-i",
                    "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
                    + MATERIALIZATION_TERMINAL_SHA256_TEMPLATE,
                    "LC_CTYPE=C.UTF-8", *ISOLATED_ARGV_PREFIX,
                    "{repository_root}/" + RETAINED_LAUNCHER_RELATIVE_PATH,
                    "dispatch", target, "{repository_root}",
                ],
                "launcher_command_template": command_template,
                "service_working_directory_template": "{repository_root}",
                "systemd_run_argv_template": [
                    "/usr/bin/systemd-run", "--user", "--wait", "--collect",
                    "--pipe", "--quiet", "--no-ask-password",
                    "--unit=" + unit_name,
                    "--slice=" + PRODUCTION_TRANSIENT_SERVICE_SLICE,
                    "--service-type=exec", "--property=Delegate=yes",
                    "--property=UMask=0077",
                    "--working-directory={repository_root}",
                    *command_template,
                ],
            }
        )
    return {
        "schema": PRODUCTION_SERVICE_CONTRACT_SCHEMA,
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


def _production_systemd_run_argv_template(
    repository_root: Path, target: str
) -> list[str]:
    if target not in {"measurement", "verification"}:
        _fail("production systemd invocation target changed")
    unit_name = {
        "measurement": PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME,
        "verification": PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME,
    }[target]
    launcher = repository_root / RETAINED_LAUNCHER_RELATIVE_PATH
    if not launcher.is_absolute() or not repository_root.is_absolute():
        _fail("production systemd invocation paths are not absolute")
    return [
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
        "/usr/bin/env",
        "-i",
        "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
        + MATERIALIZATION_TERMINAL_SHA256_TEMPLATE,
        "LC_CTYPE=C.UTF-8",
        *ISOLATED_ARGV_PREFIX,
        str(launcher),
        "service-entry",
        target,
        str(repository_root),
    ]


SOURCE_CLOSURE_RULE_ID = EXPECTED_SOURCE_CLOSURE_RULE_ID
MATERIALIZATION_RULE_ID = EXPECTED_MATERIALIZATION_RULE_ID

_COMMIT_ID = re.compile(r"^[0-9a-f]{40}$")
_OBJECT_ID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class V180r12r4PrelaunchMaterializationError(RuntimeError):
    """The external root, source closure, topology, or one-shot write changed."""


class V180r12r4PrelaunchMaterializationReplayForbidden(
    V180r12r4PrelaunchMaterializationError
):
    """A prior attempt exists and the same materialization may not run again."""


class V180r12r4WorkingTreeSourceConformanceError(
    V180r12r4PrelaunchMaterializationError
):
    """A frozen source root has a typed working-tree property mismatch."""

    def __init__(self, message: str, diagnostic: dict[str, Any]) -> None:
        super().__init__(message)
        self.source_conformance_diagnostic = diagnostic


def _fail(message: str) -> NoReturn:
    raise V180r12r4PrelaunchMaterializationError(message)


def _require_rule_identities_frozen() -> None:
    """Fail before any durable path exists while preregistration IDs are sentinels."""

    if (
        SOURCE_CLOSURE_RULE_ID == "0" * 64
        or MATERIALIZATION_RULE_ID == "0" * 64
    ):
        _fail("prelaunch materialization rule identities remain zero sentinels")
    if not (
        _SHA256.fullmatch(SOURCE_CLOSURE_RULE_ID)
        and _SHA256.fullmatch(MATERIALIZATION_RULE_ID)
        and SOURCE_CLOSURE_RULE_ID
        == hashlib.sha256(canonical_json_bytes(SOURCE_CLOSURE_RULE_DOCUMENT)).hexdigest()
        and MATERIALIZATION_RULE_ID
        == hashlib.sha256(canonical_json_bytes(MATERIALIZATION_RULE_DOCUMENT)).hexdigest()
    ):
        _fail("prelaunch materialization rule identity binding changed")


def _require_exact_dict(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} schema is not exact")
    return value


def _require_nonempty_string(value: object, label: str) -> str:
    if type(value) is not str or not value or "\x00" in value:
        _fail(f"{label} is not one nonempty string")
    return value


def _require_sha256(value: object, label: str) -> str:
    text = _require_nonempty_string(value, label)
    if _SHA256.fullmatch(text) is None:
        _fail(f"{label} is not one lowercase SHA-256 digest")
    return text


def _require_commit(value: object, label: str) -> str:
    text = _require_nonempty_string(value, label)
    if _COMMIT_ID.fullmatch(text) is None:
        _fail(f"{label} is not one lowercase 40-hex commit ID")
    return text


def _require_object_id(value: object, label: str) -> str:
    text = _require_nonempty_string(value, label)
    if _OBJECT_ID.fullmatch(text) is None:
        _fail(f"{label} is not one lowercase Git object ID")
    return text


def _require_nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} is not one nonnegative integer")
    return value


def _validated_relative_path(value: object, label: str) -> str:
    text = _require_nonempty_string(value, label)
    pure = PurePosixPath(text)
    if (
        pure.is_absolute()
        or pure.as_posix() != text
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        _fail(f"{label} is not one normalized relative path")
    return text


def _validated_absolute_directory(value: object, label: str) -> Path:
    text = _require_nonempty_string(value, label)
    path = Path(text)
    if not path.is_absolute() or str(path) != text:
        _fail(f"{label} is not one exact absolute path")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as error:
            raise V180r12r4PrelaunchMaterializationError(
                f"{label} is unavailable"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            _fail(f"{label} has a symlinked path component")
    if not stat.S_ISDIR(os.lstat(path).st_mode) or path.resolve(strict=True) != path:
        _fail(f"{label} is not one nonsymlink directory")
    return path


def _stable_read_file(
    path: Path,
    *,
    label: str,
    byte_cap: int,
    required_mode: int | None = None,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> bytes:
    """Stream-read a stable, singly linked regular file without symlinks."""

    if not path.is_absolute():
        _fail(f"{label} path is not absolute")
    current = Path(path.anchor)
    for part in path.parts[1:-1]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as error:
            raise V180r12r4PrelaunchMaterializationError(
                f"{label} parent is unavailable"
            ) from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            _fail(f"{label} parent is symlinked or nondirectory")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise V180r12r4PrelaunchMaterializationError(
            f"{label} is unavailable or symlinked"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail(f"{label} must be one singly linked regular file")
        if required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode:
            _fail(f"{label} mode is not {required_mode:04o}")
        if before.st_size > byte_cap:
            _fail(f"{label} exceeds its byte cap")
        if expected_size is not None and before.st_size != expected_size:
            _fail(f"{label} byte count differs from its frozen fact")
        chunks: list[bytes] = []
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, byte_cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            digest.update(chunk)
            total += len(chunk)
            if total > byte_cap:
                _fail(f"{label} exceeded its streaming byte cap")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(before, name) != getattr(after, name) for name in stable_fields):
        _fail(f"{label} changed during its stable read")
    raw = b"".join(chunks)
    observed_digest = digest.hexdigest()
    if len(raw) != before.st_size:
        _fail(f"{label} changed length during its stable read")
    if expected_sha256 is not None and observed_digest != expected_sha256:
        _fail(f"{label} digest differs from its frozen fact")
    return raw


def _working_tree_source_conformance_v180r12r4(
    repository_root: Path,
    tree: dict[str, tuple[str, str]],
    blobs: dict[str, bytes],
) -> dict[str, Any]:
    """Snapshot every frozen source root and compare each material property."""

    snapshots: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_uid",
        "st_gid",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )

    for relative in SOURCE_CLOSURE_REQUIRED_ROOTS:
        git_mode, expected_blob_id = tree[relative]
        expected_raw = blobs[relative]
        expected_mode = 0o644 if git_mode == "100644" else 0o755
        path = repository_root / relative
        try:
            descriptor = os.open(
                path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
            )
        except OSError as error:
            diagnostic = {
                "schema": (
                    "acfqp.v180r12r4_working_tree_source_conformance_diagnostic.v1"
                ),
                "phase": "BEFORE_PRELAUNCH_OUTPUT_AND_SCIENTIFIC_CAMPAIGN",
                "source_root_count": len(SOURCE_CLOSURE_REQUIRED_ROOTS),
                "snapshots": snapshots,
                "mismatch_count": 1,
                "per_field_mismatches": [
                    {
                        "relative_path": relative,
                        "field": "presence",
                        "expected": "REGULAR_FILE",
                        "observed_before": "UNREADABLE_OR_SYMLINK",
                        "observed_after": "UNREADABLE_OR_SYMLINK",
                    }
                ],
                "unit_ownership_evaluated": False,
                "full_source_conformance": False,
                "cause": {
                    "type": type(error).__name__,
                    "message": "frozen source root is unavailable or symlinked",
                },
            }
            raise V180r12r4WorkingTreeSourceConformanceError(
                f"working-tree source conformance failed: {relative}:presence",
                diagnostic,
            ) from error
        try:
            before = os.fstat(descriptor)
            chunks: list[bytes] = []
            digest = hashlib.sha256()
            total = 0
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
                digest.update(chunk)
                total += len(chunk)
                if total > SOURCE_FILE_BYTE_CAP:
                    _fail("working-tree source root exceeds its byte cap")
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)

        raw = b"".join(chunks)
        physical_blob_id = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
        ).hexdigest()
        comparison_raw = raw
        binding_kind = "EXACT_C_PRE_GIT_BLOB"
        if relative == AUTHORIZATION_EVIDENCE_RELATIVE_PATH:
            comparison_raw, _wrapper_values = _normalize_wrapper(raw)
            binding_kind = NORMALIZED_WRAPPER_BINDING_KIND
        observed_blob_id = hashlib.sha1(
            b"blob "
            + str(len(comparison_raw)).encode("ascii")
            + b"\x00"
            + comparison_raw
        ).hexdigest()

        def property_snapshot(row: os.stat_result) -> dict[str, Any]:
            return {
                "file_type": (
                    "REGULAR_FILE" if stat.S_ISREG(row.st_mode) else "OTHER"
                ),
                "st_dev": row.st_dev,
                "st_ino": row.st_ino,
                "st_mode": row.st_mode,
                "mode": stat.S_IMODE(row.st_mode),
                "st_nlink": row.st_nlink,
                "st_uid": row.st_uid,
                "st_gid": row.st_gid,
                "st_size": row.st_size,
                "st_mtime_ns": row.st_mtime_ns,
                "st_ctime_ns": row.st_ctime_ns,
            }

        before_snapshot = property_snapshot(before)
        after_snapshot = property_snapshot(after)
        expected = {
            "file_type": "REGULAR_FILE",
            "git_mode": git_mode,
            "mode": expected_mode,
            "st_nlink": 1,
            "binding_kind": binding_kind,
            "byte_count": len(expected_raw),
            "sha256": hashlib.sha256(expected_raw).hexdigest(),
            "git_blob_id": expected_blob_id,
        }
        observed = {
            "binding_kind": binding_kind,
            "byte_count": len(comparison_raw),
            "sha256": hashlib.sha256(comparison_raw).hexdigest(),
            "git_blob_id": observed_blob_id,
            "physical_byte_count": len(raw),
            "physical_sha256": digest.hexdigest(),
            "physical_git_blob_id": physical_blob_id,
        }
        row_mismatches: list[dict[str, Any]] = []

        def compare(
            field: str,
            expected_value: Any,
            before_value: Any,
            after_value: Any,
        ) -> None:
            if before_value != expected_value or after_value != expected_value:
                row_mismatches.append(
                    {
                        "relative_path": relative,
                        "field": field,
                        "expected": expected_value,
                        "observed_before": before_value,
                        "observed_after": after_value,
                    }
                )

        compare(
            "file_type",
            expected["file_type"],
            before_snapshot["file_type"],
            after_snapshot["file_type"],
        )
        compare(
            "mode",
            expected_mode,
            before_snapshot["mode"],
            after_snapshot["mode"],
        )
        compare(
            "st_nlink",
            1,
            before_snapshot["st_nlink"],
            after_snapshot["st_nlink"],
        )
        compare(
            "byte_count",
            len(expected_raw),
            len(comparison_raw),
            len(comparison_raw),
        )
        compare(
            "sha256",
            expected["sha256"],
            observed["sha256"],
            observed["sha256"],
        )
        compare(
            "git_blob_id",
            expected_blob_id,
            observed_blob_id,
            observed_blob_id,
        )
        for field in stable_fields:
            if getattr(before, field) != getattr(after, field):
                row_mismatches.append(
                    {
                        "relative_path": relative,
                        "field": field,
                        "expected": "STABLE_BEFORE_AFTER",
                        "observed_before": getattr(before, field),
                        "observed_after": getattr(after, field),
                    }
                )
        snapshots.append(
            {
                "relative_path": relative,
                "expected": expected,
                "observed_before": before_snapshot,
                "observed_after": after_snapshot,
                "observed_content": observed,
                "mismatch_fields": sorted(
                    {row["field"] for row in row_mismatches}
                ),
                "conformant": not row_mismatches,
            }
        )
        mismatches.extend(row_mismatches)

    diagnostic = {
        "schema": (
            "acfqp.v180r12r4_working_tree_source_conformance_diagnostic.v1"
        ),
        "phase": "BEFORE_PRELAUNCH_OUTPUT_AND_SCIENTIFIC_CAMPAIGN",
        "source_root_count": len(SOURCE_CLOSURE_REQUIRED_ROOTS),
        "snapshots": snapshots,
        "mismatch_count": len(mismatches),
        "per_field_mismatches": sorted(
            mismatches, key=lambda row: (row["relative_path"], row["field"])
        ),
        "unit_ownership_evaluated": False,
        "full_source_conformance": not mismatches,
        "cause": (
            None
            if not mismatches
            else {
                "type": "WORKING_TREE_SOURCE_PROPERTY_MISMATCH",
                "message": "one or more frozen source properties differ",
            }
        ),
    }
    if mismatches:
        first = diagnostic["per_field_mismatches"][0]
        wrapper_content_drift = any(
            row["relative_path"] == AUTHORIZATION_EVIDENCE_RELATIVE_PATH
            and row["field"] in {"byte_count", "sha256", "git_blob_id"}
            for row in diagnostic["per_field_mismatches"]
        )
        raise V180r12r4WorkingTreeSourceConformanceError(
            (
                "literal HEAD changed wrapper bytes outside the twelve literals"
                if wrapper_content_drift
                else (
                    "working-tree source conformance failed: "
                    + first["relative_path"]
                    + ":"
                    + first["field"]
                )
            ),
            diagnostic,
        )
    return diagnostic


def _parse_canonical_json_object(raw: bytes, label: str) -> dict[str, Any]:
    duplicate = object()

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if type(key) is not str or key in result:
                raise ValueError(duplicate)
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs_hook,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise V180r12r4PrelaunchMaterializationError(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _raw_fact(relative_path: str, raw: bytes) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _closure(facts: list[dict[str, Any]], *, sort_key: str) -> dict[str, Any]:
    ordered = sorted(facts, key=lambda row: row[sort_key])
    if [row[sort_key] for row in ordered] != sorted(
        {row[sort_key] for row in ordered}
    ):
        _fail("source closure facts are duplicated")
    total = sum(_require_nonnegative_int(row["byte_count"], "source byte count") for row in ordered)
    if len(ordered) > SOURCE_CLOSURE_FILE_CAP or total > SOURCE_CLOSURE_TOTAL_BYTE_CAP:
        _fail("source closure exceeds its frozen cap")
    return {
        "facts": ordered,
        "file_count": len(ordered),
        "total_byte_count": total,
        "facts_sha256": hashlib.sha256(canonical_json_bytes(ordered)).hexdigest(),
    }


def _git_environment() -> dict[str, str]:
    return {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
    }


def _run_git(
    repository_root: Path,
    arguments: tuple[str, ...],
    label: str,
    *,
    byte_cap: int = GIT_ARCHIVE_BYTE_CAP,
) -> bytes:
    argv = (GIT_EXECUTABLE, "-C", str(repository_root), *arguments)
    try:
        completed = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
            env=_git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise V180r12r4PrelaunchMaterializationError(
            f"Git {label} failed"
        ) from error
    if completed.returncode != 0 or completed.stderr:
        _fail(f"Git {label} rejected the frozen boundary")
    if len(completed.stdout) > byte_cap:
        _fail(f"Git {label} exceeded its output byte cap")
    return completed.stdout


def _git_blob_fact_keys() -> set[str]:
    return {
        "relative_path",
        "git_mode",
        "git_blob_id",
        "byte_count",
        "sha256",
    }


def _validated_git_blob_fact(value: object, label: str) -> dict[str, Any]:
    fact = _require_exact_dict(value, _git_blob_fact_keys(), label)
    relative = _validated_relative_path(fact["relative_path"], f"{label} path")
    mode = _require_nonempty_string(fact["git_mode"], f"{label} mode")
    if mode not in {"100644", "100755"}:
        _fail(f"{label} mode is not a regular Git file mode")
    size = _require_nonnegative_int(fact["byte_count"], f"{label} byte count")
    if size > MATERIALIZER_BYTE_CAP:
        _fail(f"{label} exceeds its byte cap")
    return {
        "relative_path": relative,
        "git_mode": mode,
        "git_blob_id": _require_object_id(fact["git_blob_id"], f"{label} blob"),
        "byte_count": size,
        "sha256": _require_sha256(fact["sha256"], f"{label} digest"),
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


def _validated_frozen_authorization_context(
    value: object,
) -> dict[str, Any]:
    context = _require_exact_dict(
        value,
        set(FROZEN_AUTHORIZATION_CONTEXT_FIELDS),
        "frozen authorization context",
    )
    if context["schema"] != FROZEN_AUTHORIZATION_CONTEXT_SCHEMA:
        _fail("frozen authorization context schema changed")
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
        _require_sha256(context[key], f"frozen authorization {key}")
    for key in (
        "protocol_byte_count",
        "authorization_byte_count",
        "authorization_evidence_byte_count",
    ):
        if _require_nonnegative_int(context[key], f"frozen authorization {key}") <= 0:
            _fail(f"frozen authorization {key} must be positive")
    cgroup = _require_exact_dict(
        context["cgroup_parent_fact"],
        set(CGROUP_PARENT_FACT_FIELDS),
        "frozen cgroup parent fact",
    )
    runtime = _require_exact_dict(
        context["runtime_capability_fact"],
        set(RUNTIME_CAPABILITY_FACT_FIELDS),
        "frozen runtime capability fact",
    )
    if (
        cgroup.get("schema") != "acfqp.v180r12r4_cgroup_parent_fact.v1"
        or runtime.get("schema")
        != "acfqp.v180r12r4_runtime_capability_fact.v1"
        or runtime.get("admitted") is not True
        or cgroup.get("owner_uid") != runtime.get("uid")
        or cgroup.get("owner_gid") != runtime.get("gid")
        or type(cgroup.get("mode")) is not int
        or cgroup["mode"] & (stat.S_IWUSR | stat.S_IXUSR)
        != (stat.S_IWUSR | stat.S_IXUSR)
    ):
        _fail("frozen runtime or cgroup fact schema changed")
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
        + canonical_json_bytes(attempt_payload)
    ).hexdigest()
    if context["campaign_attempt_id"] != expected_attempt:
        _fail("frozen campaign attempt six-authority identity changed")
    return context


def load_external_root_v180r12r4(
    repository_root: Path,
    external_root_path: Path,
    expected_sha256: str,
) -> tuple[dict[str, Any], bytes]:
    """Load and validate the externally chosen immutable C_pre root."""

    repository_root = _validated_absolute_directory(
        str(repository_root), "repository root"
    )
    expected_sha256 = _require_sha256(expected_sha256, "external root digest")
    if (
        not external_root_path.is_absolute()
        or external_root_path != repository_root / EXTERNAL_ROOT_RELATIVE_PATH
    ):
        _fail("external root path differs from its frozen repository path")
    raw = _stable_read_file(
        external_root_path,
        label="external root record",
        byte_cap=EXTERNAL_ROOT_BYTE_CAP,
        required_mode=0o400,
        expected_sha256=expected_sha256,
    )
    document = _require_exact_dict(
        _parse_canonical_json_object(raw, "external root record"),
        _EXTERNAL_ROOT_KEYS,
        "external root record",
    )
    if not (
        document["schema"] == EXTERNAL_ROOT_SCHEMA
        and document["materialization_rule_id"] == MATERIALIZATION_RULE_ID
        and document["source_closure_rule_id"] == SOURCE_CLOSURE_RULE_ID
        and document["repository_root"] == str(repository_root)
        and document[
            "created_before_v180r12r4_authorized_measurement_execution"
        ]
        is True
        and document["v180r12r4_outcome_bytes_accessed"] is False
    ):
        _fail("external root record changed its frozen construction boundary")
    git_directory = _validated_absolute_directory(
        document["git_directory"], "external root Git directory"
    )
    if git_directory != repository_root / ".git":
        _fail("external root Git directory is not the repository-local .git")
    document["c_pre_commit_id"] = _require_commit(
        document["c_pre_commit_id"], "external C_pre commit"
    )
    document["c_pre_tree_id"] = _require_object_id(
        document["c_pre_tree_id"], "external C_pre tree"
    )
    document["bootstrap_git_blob"] = _validated_git_blob_fact(
        document["bootstrap_git_blob"], "external bootstrap Git blob"
    )
    document["launcher_git_blob"] = _validated_git_blob_fact(
        document["launcher_git_blob"], "external launcher Git blob"
    )
    document["materializer_git_blob"] = _validated_git_blob_fact(
        document["materializer_git_blob"], "external materializer Git blob"
    )
    if (
        document["bootstrap_git_blob"]["relative_path"]
        != SOURCE_BOOTSTRAP_RELATIVE_PATH
        or document["bootstrap_git_blob"]["byte_count"] > BOOTSTRAP_BYTE_CAP
        or document["launcher_git_blob"]["relative_path"]
        != SOURCE_LAUNCHER_RELATIVE_PATH
        or document["launcher_git_blob"]["byte_count"] > LAUNCHER_BYTE_CAP
        or document["materializer_git_blob"]["relative_path"]
        != MATERIALIZER_RELATIVE_PATH
        or document["materializer_git_blob"]["byte_count"] > MATERIALIZER_BYTE_CAP
    ):
        _fail("external bootstrap or materializer Git path changed")
    roots = _require_exact_dict(
        document["third_party_source_roots"],
        {"packaging", "tomli"},
        "external third-party source roots",
    )
    document["third_party_source_roots"] = {
        namespace: str(
            _validated_absolute_directory(
                roots[namespace], f"external {namespace} source root"
            )
        )
        for namespace in ("packaging", "tomli")
    }
    document["frozen_authorization_context"] = (
        _validated_frozen_authorization_context(
            document["frozen_authorization_context"]
        )
    )
    if document["atomic_cgroup_birth_preflight_receipt_interface"] != (
        _zero_preflight_receipt_interface()
    ):
        _fail(
            "atomic cgroup-birth preflight receipt interface is not the "
            "required zero-authority placeholder"
        )
    return document, raw


def _reject_git_history_overlays(git_directory: Path) -> None:
    forbidden = (
        git_directory / "objects/info/alternates",
        git_directory / "info/grafts",
        git_directory / "shallow",
        git_directory / "refs/replace",
    )
    if any(os.path.lexists(path) for path in forbidden):
        _fail("Git history overlays are forbidden")
    packed_refs = git_directory / "packed-refs"
    if os.path.lexists(packed_refs):
        raw = _stable_read_file(
            packed_refs,
            label="packed refs",
            byte_cap=16 * 1024 * 1024,
        )
        if any(
            line.partition(b" ")[2].startswith(b"refs/replace/")
            for line in raw.splitlines()
            if line and not line.startswith((b"#", b"^"))
        ):
            _fail("Git replace refs are forbidden")


def _parse_ls_tree(raw: bytes) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    for row in raw.split(b"\x00"):
        if not row:
            continue
        try:
            prefix, path_raw = row.split(b"\t", 1)
            mode_raw, kind_raw, object_raw = prefix.split(b" ")
            mode = mode_raw.decode("ascii")
            kind = kind_raw.decode("ascii")
            object_id = object_raw.decode("ascii")
            relative = path_raw.decode("utf-8")
        except (ValueError, UnicodeError) as error:
            raise V180r12r4PrelaunchMaterializationError(
                "Git tree listing is malformed"
            ) from error
        _validated_relative_path(relative, "Git tree path")
        if (
            relative in rows
            or kind != "blob"
            or mode not in {"100644", "100755"}
            or _OBJECT_ID.fullmatch(object_id) is None
        ):
            _fail("Git tree contains a duplicate or nonregular source entry")
        rows[relative] = (mode, object_id)
    return rows


def _archive_blobs(
    repository_root: Path,
    commit_id: str,
    paths: tuple[str, ...],
) -> dict[str, bytes]:
    if not paths or paths != tuple(sorted(set(paths))):
        _fail("Git archive source paths are empty, unsorted, or duplicated")
    raw = _run_git(
        repository_root,
        ("archive", "--format=tar", commit_id, "--", *paths),
        "C_pre source archive",
    )
    blobs: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            for member in archive.getmembers():
                if member.isdir():
                    continue
                if not member.isfile() or member.name in blobs:
                    _fail("C_pre source archive contains a foreign entry")
                extracted = archive.extractfile(member)
                if extracted is None:
                    _fail("C_pre source archive entry is unreadable")
                source = extracted.read(SOURCE_FILE_BYTE_CAP + 1)
                cap = (
                    MATERIALIZER_BYTE_CAP
                    if member.name == MATERIALIZER_RELATIVE_PATH
                    else LAUNCHER_BYTE_CAP
                    if member.name == SOURCE_LAUNCHER_RELATIVE_PATH
                    else BOOTSTRAP_BYTE_CAP
                    if member.name == SOURCE_BOOTSTRAP_RELATIVE_PATH
                    else SOURCE_FILE_BYTE_CAP
                )
                if len(source) != member.size or len(source) > cap:
                    _fail("C_pre source archive entry exceeds its frozen cap")
                blobs[member.name] = source
    except (tarfile.TarError, OSError) as error:
        raise V180r12r4PrelaunchMaterializationError(
            "C_pre source archive is malformed"
        ) from error
    if set(blobs) != set(paths):
        _fail("C_pre source archive omitted or added a source")
    return blobs


def _git_raw_blob(repository_root: Path, object_id: str, label: str, cap: int) -> bytes:
    raw = _run_git(
        repository_root,
        ("cat-file", "blob", object_id),
        label,
        byte_cap=cap,
    )
    if len(raw) > cap:
        _fail(f"{label} exceeded its frozen cap")
    return raw


def verify_git_boundary_v180r12r4(
    repository_root: Path,
    external_root: dict[str, Any],
) -> dict[str, Any]:
    """Verify exact C_pre -> empty bridge -> wrapper-only HEAD topology."""

    c_pre = external_root["c_pre_commit_id"]
    expected_tree = external_root["c_pre_tree_id"]
    git_directory = Path(external_root["git_directory"])
    _reject_git_history_overlays(git_directory)
    revision_raw = _run_git(
        repository_root,
        (
            "rev-parse",
            "--show-toplevel",
            "--absolute-git-dir",
            "--git-common-dir",
            f"{c_pre}^{{commit}}",
            f"{c_pre}^{{tree}}",
            "HEAD^{commit}",
            "HEAD^{tree}",
        ),
        "root and revisions",
        byte_cap=4096,
    )
    try:
        lines = revision_raw.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise V180r12r4PrelaunchMaterializationError(
            "Git root and revision output is non-ASCII"
        ) from error
    if len(lines) != 7:
        _fail("Git root and revision output changed")
    (
        top_level,
        observed_git,
        common_git,
        observed_c_pre,
        observed_tree,
        head,
        head_tree,
    ) = lines
    common_path = Path(common_git)
    if not common_path.is_absolute():
        common_path = repository_root / common_path
    if not (
        Path(top_level).resolve(strict=True) == repository_root
        and Path(observed_git).resolve(strict=True) == git_directory
        and common_path.resolve(strict=True) == git_directory
        and observed_c_pre == c_pre
        and observed_tree == expected_tree
        and _COMMIT_ID.fullmatch(head) is not None
        and _OBJECT_ID.fullmatch(head_tree) is not None
    ):
        _fail("Git root, C_pre, tree, or HEAD differs from the external root")

    chain_raw = _run_git(
        repository_root,
        (
            "log",
            "--first-parent",
            "--reverse",
            "--format=%H%x09%P%x09%T",
            f"{c_pre}..{head}",
        ),
        "exact bridge chain",
        byte_cap=4096,
    )
    try:
        chain_lines = chain_raw.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise V180r12r4PrelaunchMaterializationError(
            "Git bridge chain is non-ASCII"
        ) from error
    if len(chain_lines) != 2:
        _fail("Git history is not exactly C_pre -> bridge -> literal HEAD")
    rows: list[tuple[str, str, str]] = []
    previous = c_pre
    for line in chain_lines:
        fields = line.split("\t")
        if not (
            len(fields) == 3
            and _COMMIT_ID.fullmatch(fields[0]) is not None
            and fields[1] == previous
            and _OBJECT_ID.fullmatch(fields[2]) is not None
        ):
            _fail("Git bridge chain is merged or malformed")
        rows.append((fields[0], fields[1], fields[2]))
        previous = fields[0]
    bridge, literal = rows[0][0], rows[1][0]
    if not (
        rows[0][2] == expected_tree
        and rows[1][0] == head
        and rows[1][2] == head_tree
        and literal != bridge != c_pre
    ):
        _fail("Git empty bridge or literal HEAD identity changed")

    bridge_diff = _run_git(
        repository_root,
        ("diff-tree", "--no-commit-id", "--raw", "--no-renames", "-r", bridge),
        "empty bridge diff",
        byte_cap=4096,
    )
    if bridge_diff:
        _fail("Git bridge commit is not empty")
    literal_diff = _run_git(
        repository_root,
        ("diff-tree", "--no-commit-id", "--raw", "--no-renames", "-r", literal),
        "wrapper literal diff",
        byte_cap=4096,
    )
    try:
        literal_line = literal_diff.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise V180r12r4PrelaunchMaterializationError(
            "Git literal diff is non-UTF-8"
        ) from error
    match = re.fullmatch(
        r":100644 100644 ([0-9a-f]{40,64}) ([0-9a-f]{40,64}) M\t"
        + re.escape(AUTHORIZATION_EVIDENCE_RELATIVE_PATH),
        literal_line,
    )
    if match is None:
        _fail("Git literal HEAD must modify only the regular wrapper")
    return {
        "c_pre_commit_id": c_pre,
        "c_pre_tree_id": expected_tree,
        "empty_bridge_commit_id": bridge,
        "empty_bridge_tree_id": expected_tree,
        "literal_commit_id": literal,
        "literal_commit_tree_id": head_tree,
        "literal_wrapper_prior_blob_id": match.group(1),
        "literal_wrapper_blob_id": match.group(2),
    }


def _module_name_from_relative(relative_path: str) -> tuple[str, bool]:
    if not relative_path.startswith("src/acfqp/") or not relative_path.endswith(".py"):
        _fail("source module path is outside src/acfqp Python sources")
    path = PurePosixPath(relative_path).relative_to("src")
    is_package = path.name == "__init__.py"
    parts = list(path.parts[:-1])
    if not is_package:
        parts.append(path.stem)
    module = ".".join(parts)
    if not (
        module == "acfqp" or module.startswith("acfqp.")
    ) or not all(part.isidentifier() for part in module.split(".")):
        _fail("source module name is invalid")
    return module, is_package


def _absolute_import_base(
    current_module: str,
    current_is_package: bool,
    imported_module: str | None,
    level: int,
) -> str:
    if level == 0:
        return "" if imported_module is None else imported_module
    package = current_module if current_is_package else current_module.rpartition(".")[0]
    parts = package.split(".") if package else []
    if level > len(parts):
        return ""
    prefix = parts[: len(parts) - level + 1]
    if imported_module:
        prefix.extend(imported_module.split("."))
    return ".".join(prefix)


def _local_imports(
    module: str,
    is_package: bool,
    raw: bytes,
    available_names: frozenset[str],
) -> tuple[str, ...]:
    try:
        tree = ast.parse(raw, filename=module)
    except (SyntaxError, TypeError, ValueError) as error:
        raise V180r12r4PrelaunchMaterializationError(
            f"C_pre source module cannot be parsed: {module}"
        ) from error
    discovered: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                candidate = alias.name
                if candidate == "acfqp" or candidate.startswith("acfqp."):
                    if candidate not in available_names:
                        _fail(f"C_pre static import is absent: {candidate}")
                    discovered.add(candidate)
        elif isinstance(node, ast.ImportFrom):
            base = _absolute_import_base(
                module,
                is_package,
                node.module,
                node.level,
            )
            if base == "acfqp" or base.startswith("acfqp."):
                if base not in available_names:
                    _fail(f"C_pre static import base is absent: {base}")
                discovered.add(base)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    candidate = f"{base}.{alias.name}"
                    if candidate in available_names:
                        discovered.add(candidate)
    return tuple(sorted(discovered))


def _script_import_roots(
    raw: bytes,
    relative_path: str,
    available_names: frozenset[str],
) -> tuple[str, ...]:
    try:
        tree = ast.parse(raw, filename=relative_path)
    except (SyntaxError, TypeError, ValueError) as error:
        raise V180r12r4PrelaunchMaterializationError(
            f"C_pre script cannot be parsed: {relative_path}"
        ) from error
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in available_names:
                    roots.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            module = node.module
            if type(module) is not str or not module.startswith("acfqp"):
                continue
            if module in available_names:
                roots.add(module)
            for alias in node.names:
                candidate = f"{module}.{alias.name}"
                if candidate in available_names:
                    roots.add(candidate)
    return tuple(sorted(roots))


def _normalize_wrapper(raw: bytes) -> tuple[bytes, dict[str, str | int]]:
    try:
        tree = ast.parse(raw, filename=AUTHORIZATION_EVIDENCE_RELATIVE_PATH)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise V180r12r4PrelaunchMaterializationError(
            "authorization wrapper is not static UTF-8 Python"
        ) from error
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    wanted = set(WRAPPER_REDACTED_CONSTANT_NAMES)
    assignments: dict[str, tuple[int, int, bytes]] = {}
    values: dict[str, str | int] = {}
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
        if name in assignments or not isinstance(value, ast.Constant):
            _fail("authorization wrapper literal assignment changed")
        literal = value.value
        if name in _WRAPPER_STRING_CONSTANT_NAMES:
            if type(literal) is not str:
                _fail("authorization wrapper string literal changed")
            replacement = _WRAPPER_REDACTED_STRING_LITERAL
            expected_token = tokenize.STRING
        else:
            if name not in _WRAPPER_INTEGER_CONSTANT_NAMES or type(literal) is not int:
                _fail("authorization wrapper integer literal changed")
            replacement = _WRAPPER_REDACTED_INTEGER_LITERAL
            expected_token = tokenize.NUMBER
        positions = (value.lineno, value.col_offset, value.end_lineno, value.end_col_offset)
        if not all(type(item) is int for item in positions):
            _fail("authorization wrapper literal has no exact source span")
        start = offsets[value.lineno - 1] + value.col_offset
        end = offsets[value.end_lineno - 1] + value.end_col_offset
        if not 0 <= start < end <= len(raw):
            _fail("authorization wrapper literal span changed")
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
            raise V180r12r4PrelaunchMaterializationError(
                "authorization wrapper literal tokenization failed"
            ) from error
        if len(tokens) != 1 or tokens[0].type != expected_token:
            _fail("authorization wrapper anchor is not one literal token")
        assignments[name] = (start, end, replacement)
        values[name] = literal
    if set(assignments) != wanted or len(assignments) != 12:
        _fail("authorization wrapper twelve-literal allowlist changed")
    normalized = raw
    previous_start = len(raw)
    for start, end, replacement in sorted(
        assignments.values(), key=lambda item: item[0], reverse=True
    ):
        if end > previous_start:
            _fail("authorization wrapper literal spans overlap")
        normalized = normalized[:start] + replacement + normalized[end:]
        previous_start = start
    return normalized, values


def _require_boundary_wrapper_sentinels(values: dict[str, str | int]) -> None:
    if not all(
        value == ("0" * 64 if name in _WRAPPER_STRING_CONSTANT_NAMES else 0)
        for name, value in values.items()
    ):
        _fail("C_pre authorization wrapper did not retain all twelve sentinels")


def _require_literal_wrapper_values(values: dict[str, str | int]) -> None:
    for name, value in values.items():
        if name in _WRAPPER_STRING_CONSTANT_NAMES:
            if (
                type(value) is not str
                or _SHA256.fullmatch(value) is None
                or value == "0" * 64
            ):
                _fail("literal HEAD did not freeze every wrapper string identity")
        elif type(value) is not int or value <= 0:
            _fail("literal HEAD did not freeze every wrapper integer identity")


def _authorization_source_closure_identity_v180r12r4(
    authorization_facts: Sequence[dict[str, Any]],
) -> tuple[str, int, int]:
    """Rebuild the exact verifier-side source-closure identity formula."""

    if tuple(row.get("relative_path") for row in authorization_facts) != (
        SOURCE_CLOSURE_REQUIRED_ROOTS
    ):
        _fail("authorization source facts are not the exact frozen path sequence")
    source_facts = [
        {
            key: row[key]
            for key in _AUTHORIZATION_SOURCE_FACT_IDENTITY_FIELDS
        }
        for row in authorization_facts
    ]
    source_payload = {
        "schema": "acfqp.v180r12r4_authorization_source_closure.v1",
        "source_facts": source_facts,
        "source_fact_count": len(source_facts),
        "source_total_byte_count": sum(
            _require_nonnegative_int(row["byte_count"], "source byte count")
            for row in source_facts
        ),
        "required_static_roots": list(SOURCE_CLOSURE_REQUIRED_ROOTS),
        "transitive_local_import_closure_required": True,
        "authorization_self_normalized_by_evidence_freeze": True,
    }
    source_raw = canonical_json_bytes(source_payload)
    return hashlib.sha256(source_raw).hexdigest(), len(source_raw), len(source_facts)


def _require_literal_wrapper_authority_joins_v180r12r4(
    wrapper_values: dict[str, str | int],
    frozen_context: dict[str, Any],
    authorization_facts: Sequence[dict[str, Any]],
) -> None:
    """Reject a re-signed wrapper before the first output-root effect."""

    if not (
        wrapper_values["EXPECTED_AUTHORIZATION_ID"]
        == frozen_context["authorization_id"]
        and wrapper_values["EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT"]
        == frozen_context["authorization_byte_count"]
        and wrapper_values["EXPECTED_AUTHORIZATION_CANONICAL_SHA256"]
        == frozen_context["authorization_sha256"]
        and wrapper_values["EXPECTED_AUTHORIZATION_EVIDENCE_ID"]
        == frozen_context["authorization_evidence_id"]
        and wrapper_values["EXPECTED_CANONICAL_BYTE_COUNT"]
        == frozen_context["authorization_evidence_byte_count"]
        and wrapper_values["EXPECTED_CANONICAL_SHA256"]
        == frozen_context["authorization_evidence_sha256"]
    ):
        _fail("literal wrapper authorization/evidence context join changed")
    facts_by_path = {
        row["relative_path"]: row for row in authorization_facts
    }
    if len(facts_by_path) != len(authorization_facts):
        _fail("authorization source facts repeat before wrapper replay")
    authorization_fact = facts_by_path.get(AUTHORIZATION_SELF_RELATIVE_PATH)
    if authorization_fact is None or not (
        wrapper_values["EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT"]
        == authorization_fact["byte_count"]
        and wrapper_values["EXPECTED_AUTHORIZATION_SOURCE_SHA256"]
        == authorization_fact["sha256"]
    ):
        _fail("literal wrapper authorization source fact join changed")
    source_id, source_byte_count, source_file_count = (
        _authorization_source_closure_identity_v180r12r4(authorization_facts)
    )
    if not (
        wrapper_values["EXPECTED_SOURCE_CLOSURE_ID"] == source_id
        and wrapper_values["EXPECTED_SOURCE_CLOSURE_BYTE_COUNT"]
        == source_byte_count
        and wrapper_values["EXPECTED_SOURCE_CLOSURE_SHA256"] == source_id
        and wrapper_values["EXPECTED_SOURCE_CLOSURE_FILE_COUNT"]
        == source_file_count
    ):
        _fail("literal wrapper authorization source closure identity changed")


def _direct_literal_values(
    raw: bytes,
    names: Sequence[str],
    label: str,
) -> dict[str, Any]:
    """Extract one exact top-level Assign+Constant for every requested name."""

    try:
        tree = ast.parse(raw, filename=label)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise V180r12r4PrelaunchMaterializationError(
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


def _require_nonzero_rule_or_identity(value: object, label: str) -> str:
    identity = _require_sha256(value, label)
    if identity == "0" * 64:
        _fail(f"{label} remains a zero sentinel")
    return identity


def _bind_static_target(
    target: ast.expr,
    value: object,
    environment: dict[str, object],
) -> None:
    if isinstance(target, ast.Name):
        environment[target.id] = value
        return
    if isinstance(target, (ast.Tuple, ast.List)) and isinstance(
        value, (tuple, list)
    ):
        if len(target.elts) != len(value):
            _fail("C_pre launcher static comprehension target arity changed")
        for child, item in zip(target.elts, value, strict=True):
            _bind_static_target(child, item, environment)
        return
    _fail("C_pre launcher static comprehension target changed")


def _normalize_launcher_rule_source_v180r12r4(raw: bytes) -> bytes:
    """Redact only the three direct rule literals, then bind all other bytes."""

    try:
        tree = ast.parse(raw, filename="C_pre retained launcher source")
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise V180r12r4PrelaunchMaterializationError(
            "C_pre retained launcher is not static UTF-8 Python"
        ) from error
    line_offsets = [0]
    for line in raw.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))
    replacements: list[tuple[int, int]] = []
    observed: set[str] = set()
    for statement in tree.body:
        if not (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id in LAUNCHER_RULE_LITERAL_NAMES
        ):
            continue
        name = statement.targets[0].id
        value = statement.value
        if (
            name in observed
            or not isinstance(value, ast.Constant)
            or type(value.value) is not str
            or _SHA256.fullmatch(value.value) is None
            or value.end_lineno is None
            or value.end_col_offset is None
        ):
            _fail("C_pre launcher rule literal is duplicated or nonliteral")
        start = line_offsets[value.lineno - 1] + value.col_offset
        end = line_offsets[value.end_lineno - 1] + value.end_col_offset
        if not (0 <= start < end <= len(raw)):
            _fail("C_pre launcher rule literal span changed")
        replacements.append((start, end))
        observed.add(name)
    if observed != set(LAUNCHER_RULE_LITERAL_NAMES):
        _fail("C_pre launcher rule literal set is incomplete")
    normalized = raw
    replacement = b'"' + b"0" * 64 + b'"'
    for start, end in sorted(replacements, reverse=True):
        normalized = normalized[:start] + replacement + normalized[end:]
    if not (
        len(normalized) == LAUNCHER_NORMALIZED_STATIC_RULE_SOURCE_BYTE_COUNT
        and hashlib.sha256(normalized).hexdigest()
        == LAUNCHER_NORMALIZED_STATIC_RULE_SOURCE_SHA256
    ):
        _fail("C_pre launcher normalized static rule source changed")
    return normalized


class _RestrictedStaticLauncherEvaluator:
    """Evaluate only the pure AST forms used to build LAUNCH_RULE_DOCUMENT."""

    _EXPECTED_IMPORTS = (
        ("from", "__future__", 0, (("annotations", None),)),
        ("import", None, 0, (("fcntl", None),)),
        ("import", None, 0, (("hashlib", None),)),
        ("import", None, 0, (("json", None),)),
        ("import", None, 0, (("os", None),)),
        ("from", "pathlib", 0, (("Path", None), ("PurePosixPath", None))),
        ("import", None, 0, (("re", None),)),
        ("import", None, 0, (("resource", None),)),
        ("import", None, 0, (("selectors", None),)),
        ("import", None, 0, (("signal", None),)),
        ("import", None, 0, (("stat", None),)),
        ("import", None, 0, (("subprocess", None),)),
        ("import", None, 0, (("sys", None),)),
        ("import", None, 0, (("time", None),)),
        ("from", "typing", 0, (("Any", None), ("Mapping", None), ("NoReturn", None))),
    )
    _EXPECTED_POST_RULE_ASSIGNMENTS = (
        "LAUNCH_RULE_ID",
        "_MATERIALIZATION_REQUIRED_KEYS",
        "_EXTERNAL_ROOT_KEYS",
        "_GIT_BLOB_FACT_KEYS",
        "_RAW_FACT_KEYS",
        "_NORMALIZED_WRAPPER_FACT_KEYS",
        "_CLOSURE_KEYS",
        "_SOURCE_CONFORMANCE_KEYS",
        "_SOURCE_CONFORMANCE_SNAPSHOT_KEYS",
        "_SOURCE_CONFORMANCE_EXPECTED_KEYS",
        "_SOURCE_CONFORMANCE_STAT_KEYS",
        "_SOURCE_CONFORMANCE_CONTENT_KEYS",
        "_MANIFEST_KEYS",
        "_ATTEMPT_KEYS",
        "_TERMINAL_KEYS",
        "_LAUNCH_FAILURE_PUBLICATION_KEYS",
        "SERVICE_LAUNCH_ATTEMPT_DOMAIN",
        "SERVICE_LAUNCH_RECEIPT_DOMAIN",
        "SERVICE_LAUNCH_FAILURE_DOMAIN",
        "SYSTEMCTL_EXECUTABLE",
        "SERVICE_LAUNCH_PUBLICATION_STATES",
        "SERVICE_LAUNCH_PUBLICATION_STAGES",
        "__all__",
    )
    _EXPECTED_PRE_RULE_ASSIGNMENT_COUNT = 153
    _EXPECTED_PRE_RULE_ASSIGNMENT_NAMES_SHA256 = (
        "af67693d1781f0eda54796282f522d79765c196055be9ee1d883a68686159a4f"
    )

    def __init__(self, raw: bytes) -> None:
        try:
            tree = ast.parse(raw, filename="C_pre retained launcher source")
        except (SyntaxError, UnicodeDecodeError, ValueError) as error:
            raise V180r12r4PrelaunchMaterializationError(
                "C_pre retained launcher is not static UTF-8 Python"
            ) from error
        rule_statement_index = next(
            (
                index
                for index, statement in enumerate(tree.body)
                if isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id == "LAUNCH_RULE_DOCUMENT"
            ),
            None,
        )
        if rule_statement_index is None:
            _fail("C_pre launcher static rule document is absent")
        observed_imports: list[tuple[object, ...]] = []
        for statement in tree.body[: rule_statement_index + 1]:
            if isinstance(statement, ast.Import):
                observed_imports.append(
                    (
                        "import",
                        None,
                        0,
                        tuple((alias.name, alias.asname) for alias in statement.names),
                    )
                )
            elif isinstance(statement, ast.ImportFrom):
                observed_imports.append(
                    (
                        "from",
                        statement.module,
                        statement.level,
                        tuple((alias.name, alias.asname) for alias in statement.names),
                    )
                )
        if tuple(observed_imports) != self._EXPECTED_IMPORTS:
            _fail("C_pre launcher pre-rule import allowlist changed")
        imported_bindings = {
            alias[1] or alias[0].split(".", 1)[0]
            for _kind, _module, _level, aliases in observed_imports
            for alias in aliases
        }
        self._values: dict[str, object] = {}
        self._safe_post_rule_classes: set[str] = set()
        future_annotations = False
        observed_pre_rule_assignments: list[str] = []
        for index, statement in enumerate(tree.body[: rule_statement_index + 1]):
            if (
                index == 0
                and isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and type(statement.value.value) is str
            ):
                continue
            if isinstance(statement, ast.ImportFrom):
                if statement.module == "__future__":
                    if future_annotations or tuple(
                        alias.name for alias in statement.names
                    ) != ("annotations",):
                        _fail("C_pre launcher future-import grammar changed")
                    future_annotations = True
                continue
            if isinstance(statement, ast.Import):
                continue
            if not (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
            ):
                _fail("C_pre launcher pre-rule source is not straight-line static")
            name = statement.targets[0].id
            if name in self._values or name in imported_bindings:
                _fail("C_pre launcher static assignment is duplicated")
            # Interpret immediately with only values already bound in source
            # order.  Forward references and every pre-rule effectful statement
            # are therefore rejected without executing C_pre code.
            self._values[name] = self._evaluate(statement.value, {})
            observed_pre_rule_assignments.append(name)
        if not (
            len(observed_pre_rule_assignments)
            == self._EXPECTED_PRE_RULE_ASSIGNMENT_COUNT
            and hashlib.sha256(
                canonical_json_bytes(observed_pre_rule_assignments)
            ).hexdigest()
            == self._EXPECTED_PRE_RULE_ASSIGNMENT_NAMES_SHA256
        ):
            _fail("C_pre launcher pre-rule assignment schedule changed")
        if not future_annotations:
            _fail("C_pre launcher postponed annotations contract changed")
        observed_post_assignments: list[str] = []
        occupied_names = {*imported_bindings, *self._values}
        self._post_rule_known_names = occupied_names
        for statement in tree.body[rule_statement_index + 1 :]:
            if isinstance(statement, ast.FunctionDef):
                if statement.name in occupied_names:
                    _fail("C_pre launcher post-rule dependency is rebound")
                self._validate_import_inert_function(statement)
                occupied_names.add(statement.name)
                continue
            if isinstance(statement, ast.ClassDef):
                if statement.name in occupied_names:
                    _fail("C_pre launcher post-rule dependency is rebound")
                self._validate_import_inert_class(statement)
                self._safe_post_rule_classes.add(statement.name)
                occupied_names.add(statement.name)
                continue
            if (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id != "LAUNCH_RULE_DOCUMENT"
            ):
                name = statement.targets[0].id
                if name not in self._EXPECTED_POST_RULE_ASSIGNMENTS:
                    _fail("C_pre launcher post-rule assignment target changed")
                if name in observed_post_assignments:
                    _fail("C_pre launcher post-rule assignment is duplicated")
                if name == "LAUNCH_RULE_ID" and not (
                    isinstance(statement.value, ast.Name)
                    and statement.value.id == "EXPECTED_LAUNCH_RULE_ID"
                ):
                    _fail("C_pre launcher launch-rule identity alias changed")
                self._validate_import_inert_expression(statement.value)
                observed_post_assignments.append(name)
                occupied_names.add(name)
                continue
            if (
                isinstance(statement, ast.If)
                and isinstance(statement.test, ast.Compare)
                and isinstance(statement.test.left, ast.Name)
                and statement.test.left.id == "__name__"
                and len(statement.test.ops) == 1
                and isinstance(statement.test.ops[0], ast.Eq)
                and len(statement.test.comparators) == 1
                and isinstance(statement.test.comparators[0], ast.Constant)
                and statement.test.comparators[0].value == "__main__"
            ):
                if not (
                    len(statement.body) == 1
                    and isinstance(statement.body[0], ast.Expr)
                    and isinstance(statement.body[0].value, ast.Call)
                    and isinstance(statement.body[0].value.func, ast.Name)
                    and statement.body[0].value.func.id == "main"
                    and not statement.body[0].value.args
                    and not statement.body[0].value.keywords
                    and not statement.orelse
                ):
                    _fail("C_pre launcher main guard is not import-inert")
                continue
            _fail("C_pre launcher mutates or executes after static rule construction")
        if tuple(observed_post_assignments) != self._EXPECTED_POST_RULE_ASSIGNMENTS:
            _fail("C_pre launcher post-rule assignment schedule changed")

    def _validate_import_inert_function(self, statement: ast.FunctionDef) -> None:
        if statement.decorator_list:
            _fail("C_pre launcher post-rule decorator execution is forbidden")
        defaults = [
            *statement.args.defaults,
            *(value for value in statement.args.kw_defaults if value is not None),
        ]
        for value in defaults:
            self._validate_import_inert_expression(value)

    def _validate_import_inert_class(self, statement: ast.ClassDef) -> None:
        if statement.decorator_list or statement.keywords:
            _fail("C_pre launcher post-rule class execution surface changed")
        for base in statement.bases:
            if not (
                isinstance(base, ast.Name)
                and (
                    base.id == "RuntimeError"
                    or base.id in self._safe_post_rule_classes
                )
            ):
                _fail("C_pre launcher post-rule class base is not inert")
        for member in statement.body:
            if (
                isinstance(member, ast.Expr)
                and isinstance(member.value, ast.Constant)
                and type(member.value.value) is str
            ):
                continue
            if isinstance(member, ast.FunctionDef):
                self._validate_import_inert_function(member)
                continue
            if isinstance(member, ast.Pass):
                continue
            _fail("C_pre launcher post-rule class body is not import-inert")

    def _validate_import_inert_expression(self, node: ast.AST) -> None:
        """Accept expressions whose evaluation cannot call or mutate objects."""

        if isinstance(node, ast.Constant):
            if type(node.value) not in {str, bytes, int, bool, type(None)}:
                _fail("C_pre launcher post-rule constant type changed")
            return
        if isinstance(node, ast.Name):
            if node.id == "LAUNCH_RULE_DOCUMENT":
                _fail("C_pre launcher post-rule rule aliasing is forbidden")
            if node.id not in self._post_rule_known_names:
                _fail("C_pre launcher post-rule name is unbound in source order")
            return
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            for value in node.elts:
                self._validate_import_inert_expression(value)
            return
        if isinstance(node, ast.Dict):
            if any(key is None for key in node.keys):
                _fail("C_pre launcher post-rule dictionary unpacking is forbidden")
            for key, value in zip(node.keys, node.values, strict=True):
                self._validate_import_inert_expression(key)
                self._validate_import_inert_expression(value)
            return
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            self._validate_import_inert_expression(node.left)
            self._validate_import_inert_expression(node.right)
            return
        _fail("C_pre launcher post-rule expression is not import-inert")

    def value(self, name: str) -> object:
        if name not in self._values:
            _fail("C_pre launcher static rule dependency is absent or forward")
        return self._values[name]

    def _evaluate(
        self,
        node: ast.AST,
        environment: dict[str, object],
    ) -> object:
        if isinstance(node, ast.Constant):
            if type(node.value) not in {str, bytes, int, bool, type(None)}:
                _fail("C_pre launcher static constant type changed")
            return node.value
        if isinstance(node, ast.Name):
            if node.id in environment:
                return environment[node.id]
            return self.value(node.id)
        if isinstance(node, ast.Tuple):
            return tuple(self._evaluate(value, environment) for value in node.elts)
        if isinstance(node, ast.List):
            return [self._evaluate(value, environment) for value in node.elts]
        if isinstance(node, ast.Set):
            values = [self._evaluate(value, environment) for value in node.elts]
            try:
                return set(values)
            except TypeError as error:
                raise V180r12r4PrelaunchMaterializationError(
                    "C_pre launcher static set member is unhashable"
                ) from error
        if isinstance(node, ast.Dict):
            if any(key is None for key in node.keys):
                _fail("C_pre launcher static dictionary unpacking is forbidden")
            keys = [self._evaluate(key, environment) for key in node.keys]
            if any(type(key) is not str for key in keys) or len(keys) != len(
                set(keys)
            ):
                _fail("C_pre launcher static dictionary keys changed")
            return {
                key: self._evaluate(value, environment)
                for key, value in zip(keys, node.values, strict=True)
            }
        if isinstance(node, ast.Subscript):
            container = self._evaluate(node.value, environment)
            index = self._evaluate(node.slice, environment)
            if type(index) not in {str, int} or not isinstance(
                container, (dict, tuple, list)
            ):
                _fail("C_pre launcher static subscript grammar changed")
            try:
                return container[index]  # type: ignore[index]
            except (IndexError, KeyError, TypeError) as error:
                raise V180r12r4PrelaunchMaterializationError(
                    "C_pre launcher static subscript changed"
                ) from error
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or len(node.comparators) != 1 or not isinstance(
                node.ops[0], (ast.In, ast.NotIn)
            ):
                _fail("C_pre launcher static comparison grammar changed")
            left = self._evaluate(node.left, environment)
            right = self._evaluate(node.comparators[0], environment)
            if not isinstance(right, (set, frozenset, tuple, list, dict)):
                _fail("C_pre launcher static comparison denominator changed")
            try:
                result = left in right
            except TypeError as error:
                raise V180r12r4PrelaunchMaterializationError(
                    "C_pre launcher static comparison changed"
                ) from error
            return not result if isinstance(node.ops[0], ast.NotIn) else result
        if isinstance(node, ast.IfExp):
            condition = self._evaluate(node.test, environment)
            if type(condition) is not bool:
                _fail("C_pre launcher static conditional test changed")
            return self._evaluate(
                node.body if condition else node.orelse,
                environment,
            )
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            left = self._evaluate(node.left, environment)
            right = self._evaluate(node.right, environment)
            if type(left) is int and type(right) is int:
                return left * right
            _fail("C_pre launcher static multiplication operands changed")
        if isinstance(node, ast.JoinedStr):
            pieces: list[str] = []
            for value in node.values:
                if isinstance(value, ast.Constant) and type(value.value) is str:
                    pieces.append(value.value)
                elif (
                    isinstance(value, ast.FormattedValue)
                    and value.conversion == -1
                    and value.format_spec is None
                ):
                    item = self._evaluate(value.value, environment)
                    if type(item) not in {str, int}:
                        _fail("C_pre launcher static f-string value changed")
                    pieces.append(str(item))
                else:
                    _fail("C_pre launcher static f-string grammar changed")
            return "".join(pieces)
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "hexdigest"
                and not node.args
                and not node.keywords
                and isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Attribute)
                and isinstance(node.func.value.func.value, ast.Name)
                and node.func.value.func.value.id == "hashlib"
                and node.func.value.func.attr == "sha256"
                and len(node.func.value.args) == 1
                and not node.func.value.keywords
            ):
                digest_input = self._evaluate(node.func.value.args[0], environment)
                if type(digest_input) is not bytes:
                    _fail("C_pre launcher static SHA-256 input changed")
                return hashlib.sha256(digest_input).hexdigest()
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "re"
                and node.func.attr == "compile"
                and len(node.args) == 1
                and not node.keywords
            ):
                pattern = self._evaluate(node.args[0], environment)
                if type(pattern) is not str:
                    _fail("C_pre launcher static regex pattern changed")
                return ("re.compile", pattern)
            if not (
                isinstance(node.func, ast.Name)
                and node.func.id in {"frozenset", "list", "sorted"}
                and len(node.args) == 1
                and not node.keywords
            ):
                _fail("C_pre launcher static call is outside the allowlist")
            argument = self._evaluate(node.args[0], environment)
            try:
                if node.func.id == "frozenset":
                    return frozenset(argument)  # type: ignore[arg-type]
                if node.func.id == "list":
                    return list(argument)  # type: ignore[arg-type]
                return sorted(argument)  # type: ignore[arg-type]
            except (TypeError, ValueError) as error:
                raise V180r12r4PrelaunchMaterializationError(
                    "C_pre launcher static allowlisted call changed"
                ) from error
        if isinstance(node, ast.ListComp):
            if len(node.generators) != 1:
                _fail("C_pre launcher static comprehension denominator changed")
            generator = node.generators[0]
            if generator.is_async or generator.ifs:
                _fail("C_pre launcher static comprehension grammar changed")
            iterable = self._evaluate(generator.iter, environment)
            if not isinstance(iterable, (tuple, list)):
                _fail("C_pre launcher static comprehension input changed")
            result: list[object] = []
            for item in iterable:
                local = dict(environment)
                _bind_static_target(generator.target, item, local)
                result.append(self._evaluate(node.elt, local))
            return result
        _fail(
            "C_pre launcher rule document uses a non-static expression: "
            f"{type(node).__name__}"
        )


def _reconstructed_launcher_rule_v180r12r4(raw: bytes) -> dict[str, Any]:
    _normalize_launcher_rule_source_v180r12r4(raw)
    value = _RestrictedStaticLauncherEvaluator(raw).value("LAUNCH_RULE_DOCUMENT")
    if type(value) is not dict:
        _fail("C_pre launcher rule document is not one static dictionary")
    try:
        canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise V180r12r4PrelaunchMaterializationError(
            "C_pre launcher rule document is not canonical-JSON encodable"
        ) from error
    return value


def _require_c_pre_final_anchor_joins(
    blobs: dict[str, bytes],
    external_root: dict[str, Any],
) -> None:
    """Join all static final anchors before any output-root effect is possible."""

    protocol_values = _direct_literal_values(
        blobs[PROTOCOL_SOURCE_RELATIVE_PATH],
        PROTOCOL_FINAL_ANCHOR_NAMES,
        "C_pre campaign protocol source",
    )
    authorization_values = _direct_literal_values(
        blobs[AUTHORIZATION_SELF_RELATIVE_PATH],
        AUTHORIZATION_FINAL_ANCHOR_NAMES,
        "C_pre execution authorization source",
    )
    materializer_values = _direct_literal_values(
        blobs[MATERIALIZER_RELATIVE_PATH],
        MATERIALIZER_FINAL_ANCHOR_NAMES,
        "C_pre prelaunch materializer source",
    )
    launcher_values = _direct_literal_values(
        blobs[SOURCE_LAUNCHER_RELATIVE_PATH],
        LAUNCHER_FINAL_ANCHOR_NAMES,
        "C_pre retained launcher source",
    )

    protocol_ids = {
        name: _require_nonzero_rule_or_identity(
            protocol_values[name], f"C_pre protocol {name}"
        )
        for name in PROTOCOL_FINAL_ANCHOR_NAMES
        if name != "EXPECTED_CANONICAL_BYTE_COUNT"
    }
    if (
        _require_nonnegative_int(
            protocol_values["EXPECTED_CANONICAL_BYTE_COUNT"],
            "C_pre protocol canonical byte count",
        )
        <= 0
    ):
        _fail("C_pre protocol canonical byte count must be positive")
    for name in AUTHORIZATION_FINAL_ANCHOR_NAMES:
        _require_nonzero_rule_or_identity(
            authorization_values[name], f"C_pre authorization {name}"
        )
    for name in MATERIALIZER_FINAL_ANCHOR_NAMES:
        _require_nonzero_rule_or_identity(
            materializer_values[name], f"C_pre materializer {name}"
        )
    for name in LAUNCHER_FINAL_ANCHOR_NAMES:
        _require_nonzero_rule_or_identity(
            launcher_values[name], f"C_pre launcher {name}"
        )

    context = external_root["frozen_authorization_context"]
    computed_source_rule_id = hashlib.sha256(
        canonical_json_bytes(SOURCE_CLOSURE_RULE_DOCUMENT)
    ).hexdigest()
    computed_materialization_rule_id = hashlib.sha256(
        canonical_json_bytes(MATERIALIZATION_RULE_DOCUMENT)
    ).hexdigest()
    reconstructed_launcher_rule = _reconstructed_launcher_rule_v180r12r4(
        blobs[SOURCE_LAUNCHER_RELATIVE_PATH]
    )
    computed_launch_rule_id = hashlib.sha256(
        canonical_json_bytes(reconstructed_launcher_rule)
    ).hexdigest()
    if not (
        protocol_ids["EXPECTED_PROTOCOL_ID"] == context["protocol_id"]
        and protocol_values["EXPECTED_CANONICAL_BYTE_COUNT"]
        == context["protocol_byte_count"]
        and protocol_ids["EXPECTED_CANONICAL_SHA256"]
        == context["protocol_sha256"]
        and protocol_ids[
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"
        ]
        == context["campaign_measurement_execution_slot_id"]
        and protocol_ids["LOGICAL_OCCURRENCE_ID"]
        == context["logical_occurrence_id"]
        and protocol_ids["EXECUTION_NONCE"] == context["execution_nonce"]
        and authorization_values["EXPECTED_PROTOCOL_ID"]
        == protocol_ids["EXPECTED_PROTOCOL_ID"]
        and authorization_values[
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"
        ]
        == protocol_ids[
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"
        ]
        and materializer_values["EXPECTED_SOURCE_CLOSURE_RULE_ID"]
        == protocol_ids["EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID"]
        == launcher_values["EXPECTED_SOURCE_CLOSURE_RULE_ID"]
        == computed_source_rule_id
        == SOURCE_CLOSURE_RULE_ID
        == external_root["source_closure_rule_id"]
        and materializer_values["EXPECTED_MATERIALIZATION_RULE_ID"]
        == protocol_ids["EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID"]
        == launcher_values["EXPECTED_MATERIALIZATION_RULE_ID"]
        == computed_materialization_rule_id
        == MATERIALIZATION_RULE_ID
        == external_root["materialization_rule_id"]
        and launcher_values["EXPECTED_LAUNCH_RULE_ID"]
        == protocol_ids["EXPECTED_PRELAUNCH_LAUNCH_RULE_ID"]
        == computed_launch_rule_id
    ):
        _fail("C_pre protocol, authorization, and prelaunch final anchors disagree")


def _catalogue_from_c_pre(
    repository_root: Path,
    c_pre: str,
) -> tuple[dict[str, tuple[str, bool, bytes]], dict[str, tuple[str, str]], dict[str, bytes]]:
    tree_raw = _run_git(
        repository_root,
        ("ls-tree", "-r", "-z", "--full-tree", c_pre, "--", "src/acfqp", "scripts"),
        "C_pre source tree",
        byte_cap=16 * 1024 * 1024,
    )
    tree = _parse_ls_tree(tree_raw)
    required_special = {
        *SOURCE_CLOSURE_REQUIRED_ROOTS,
    }
    if not required_special <= set(tree):
        missing = sorted(required_special - set(tree))
        _fail(f"C_pre source tree omitted required paths: {missing!r}")
    python_paths = tuple(
        sorted(
            path
            for path in tree
            if path.startswith("src/acfqp/") and path.endswith(".py")
        )
    )
    archive_paths = tuple(sorted({*python_paths, *required_special}))
    blobs = _archive_blobs(repository_root, c_pre, archive_paths)
    catalogue: dict[str, tuple[str, bool, bytes]] = {}
    for relative in python_paths:
        module, is_package = _module_name_from_relative(relative)
        if module in catalogue:
            _fail("C_pre source module catalogue is duplicated")
        catalogue[module] = (relative, is_package, blobs[relative])
    if (
        not catalogue
        or len(catalogue) > SOURCE_CLOSURE_FILE_CAP
        or tuple(catalogue) != tuple(sorted(catalogue))
    ):
        _fail("C_pre source module catalogue exceeds its frozen cap")
    return catalogue, tree, blobs


def build_c_pre_source_closure_v180r12r4(
    repository_root: Path,
    external_root: dict[str, Any],
    topology: dict[str, Any],
) -> dict[str, Any]:
    """Build exact module, runner, wrapper, bootstrap, and materializer facts."""

    c_pre = external_root["c_pre_commit_id"]
    catalogue, tree, blobs = _catalogue_from_c_pre(repository_root, c_pre)
    working_tree_source_conformance = (
        _working_tree_source_conformance_v180r12r4(
            repository_root, tree, blobs
        )
    )
    _require_c_pre_final_anchor_joins(blobs, external_root)
    available = frozenset(catalogue)
    all_roots = SOURCE_CLOSURE_REQUIRED_ROOTS
    script_roots = tuple(path for path in all_roots if path.startswith("scripts/"))
    explicit_modules = {
        _module_name_from_relative(path)[0]
        for path in all_roots
        if path.startswith("src/acfqp/")
    }
    for relative in script_roots:
        explicit_modules.update(
            _script_import_roots(blobs[relative], relative, available)
        )
    if not explicit_modules <= available:
        _fail("C_pre source closure root is absent")
    pending = list(reversed(sorted(explicit_modules)))
    included: set[str] = set()
    while pending:
        module = pending.pop()
        if module in included:
            continue
        if len(included) >= SOURCE_CLOSURE_FILE_CAP:
            _fail("C_pre recursive source closure exceeds its file cap")
        included.add(module)
        relative, is_package, raw = catalogue[module]
        pending.extend(
            reversed(
                tuple(
                    name
                    for name in _local_imports(module, is_package, raw, available)
                    if name not in included
                )
            )
        )
        parts = module.split(".")
        for end in range(1, len(parts)):
            parent = ".".join(parts[:end])
            if parent not in catalogue:
                _fail("C_pre recursive source closure omitted a parent package")
            if parent not in included:
                pending.append(parent)
    included.discard(AUTHORIZATION_SELF_MODULE)
    if AUTHORIZATION_EVIDENCE_MODULE not in included:
        _fail("C_pre recursive source closure omitted the evidence wrapper")

    # The special prelaunch sources are independently bound by the external root.
    for key, relative, cap in (
        ("bootstrap_git_blob", SOURCE_BOOTSTRAP_RELATIVE_PATH, BOOTSTRAP_BYTE_CAP),
        ("launcher_git_blob", SOURCE_LAUNCHER_RELATIVE_PATH, LAUNCHER_BYTE_CAP),
        ("materializer_git_blob", MATERIALIZER_RELATIVE_PATH, MATERIALIZER_BYTE_CAP),
    ):
        fact = external_root[key]
        mode, object_id = tree[relative]
        raw = blobs[relative]
        if not (
            fact["git_mode"] == mode
            and fact["git_blob_id"] == object_id
            and fact["byte_count"] == len(raw) <= cap
            and fact["sha256"] == hashlib.sha256(raw).hexdigest()
        ):
            _fail(f"external {relative} fact differs from its C_pre Git blob")

    current_materializer = _stable_read_file(
        repository_root / MATERIALIZER_RELATIVE_PATH,
        label="current materializer source",
        byte_cap=MATERIALIZER_BYTE_CAP,
        expected_size=len(blobs[MATERIALIZER_RELATIVE_PATH]),
        expected_sha256=hashlib.sha256(blobs[MATERIALIZER_RELATIVE_PATH]).hexdigest(),
    )
    if current_materializer != blobs[MATERIALIZER_RELATIVE_PATH]:
        _fail("executing materializer differs from its C_pre Git blob")
    if Path(__file__).resolve(strict=True) != repository_root / MATERIALIZER_RELATIVE_PATH:
        _fail("executing materializer path differs from the repository binding")

    boundary_wrapper = blobs[AUTHORIZATION_EVIDENCE_RELATIVE_PATH]
    current_wrapper = _stable_read_file(
        repository_root / AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
        label="current literal wrapper source",
        byte_cap=SOURCE_FILE_BYTE_CAP,
    )
    committed_wrapper = _git_raw_blob(
        repository_root,
        topology["literal_wrapper_blob_id"],
        "literal wrapper blob",
        SOURCE_FILE_BYTE_CAP,
    )
    if current_wrapper != committed_wrapper:
        _fail("current wrapper bytes differ from the literal HEAD blob")
    boundary_normalized, boundary_values = _normalize_wrapper(boundary_wrapper)
    current_normalized, current_values = _normalize_wrapper(current_wrapper)
    _require_boundary_wrapper_sentinels(boundary_values)
    _require_literal_wrapper_values(current_values)
    if boundary_normalized != current_normalized:
        _fail("literal HEAD changed wrapper bytes outside the twelve literals")

    source_modules: list[dict[str, Any]] = []
    authorization_raw_names: list[str] = []
    for module in sorted({*included, AUTHORIZATION_SELF_MODULE}):
        relative, is_package, boundary_raw = catalogue[module]
        current_raw = _stable_read_file(
            repository_root / relative,
            label=f"current source module {module}",
            byte_cap=SOURCE_FILE_BYTE_CAP,
        )
        if module == AUTHORIZATION_EVIDENCE_MODULE:
            manifest_raw = current_raw
            if current_raw != current_wrapper:
                _fail("current wrapper source changed during closure replay")
        else:
            if current_raw != boundary_raw:
                _fail(f"current ordinary source differs from C_pre: {relative}")
            manifest_raw = boundary_raw
        source_modules.append(
            {
                "module": module,
                "is_package": is_package,
                **_raw_fact(relative, manifest_raw),
            }
        )
        if module != AUTHORIZATION_SELF_MODULE:
            authorization_raw_names.append(module)

    targets: dict[str, dict[str, Any]] = {}
    for target, relative in TARGET_RUNNER_PATHS.items():
        raw = blobs[relative]
        if len(raw) > RUNNER_BYTE_CAP:
            _fail(f"C_pre {target} runner exceeds its byte cap")
        current = _stable_read_file(
            repository_root / relative,
            label=f"current {target} runner",
            byte_cap=RUNNER_BYTE_CAP,
            expected_size=len(raw),
            expected_sha256=hashlib.sha256(raw).hexdigest(),
        )
        if current != raw:
            _fail(f"current {target} runner differs from C_pre")
        targets[target] = _raw_fact(relative, raw)

    authorization_facts: list[dict[str, Any]] = []
    for relative in SOURCE_CLOSURE_REQUIRED_ROOTS:
        boundary_raw = blobs[relative]
        current_raw = _stable_read_file(
            repository_root / relative,
            label=f"current required static source {relative}",
            byte_cap=(
                RUNNER_BYTE_CAP
                if relative.startswith("scripts/")
                else SOURCE_FILE_BYTE_CAP
            ),
        )
        if relative == AUTHORIZATION_EVIDENCE_RELATIVE_PATH:
            if current_raw != current_wrapper:
                _fail("current wrapper source changed during static-root replay")
            authorization_facts.append(
                {
                    **_raw_fact(relative, boundary_normalized),
                    "binding_kind": NORMALIZED_WRAPPER_BINDING_KIND,
                    "redacted_constant_names": list(WRAPPER_REDACTED_CONSTANT_NAMES),
                }
            )
        else:
            if current_raw != boundary_raw:
                _fail(f"current required static source differs from C_pre: {relative}")
            authorization_facts.append(_raw_fact(relative, boundary_raw))

    _require_literal_wrapper_authority_joins_v180r12r4(
        current_values,
        external_root["frozen_authorization_context"],
        authorization_facts,
    )

    if (
        len(source_modules) + len(targets) > SOURCE_CLOSURE_FILE_CAP
        or len(authorization_facts) != len(SOURCE_CLOSURE_REQUIRED_ROOTS)
    ):
        _fail("combined C_pre source closure exceeds its file cap")
    return {
        "bootstrap_raw": blobs[SOURCE_BOOTSTRAP_RELATIVE_PATH],
        "launcher_raw": blobs[SOURCE_LAUNCHER_RELATIVE_PATH],
        "materializer_raw_fact": _raw_fact(
            MATERIALIZER_RELATIVE_PATH, blobs[MATERIALIZER_RELATIVE_PATH]
        ),
        "source_modules": source_modules,
        "authorization_raw_source_modules": sorted(authorization_raw_names),
        "authorization_source_closure": _closure(
            authorization_facts, sort_key="relative_path"
        ),
        "targets": targets,
        "boundary_wrapper_normalized_fact": {
            **_raw_fact(AUTHORIZATION_EVIDENCE_RELATIVE_PATH, boundary_normalized),
            "binding_kind": NORMALIZED_WRAPPER_BINDING_KIND,
            "redacted_constant_names": list(WRAPPER_REDACTED_CONSTANT_NAMES),
        },
        "current_wrapper_raw_fact": _raw_fact(
            AUTHORIZATION_EVIDENCE_RELATIVE_PATH, current_wrapper
        ),
        "working_tree_source_conformance": working_tree_source_conformance,
    }


def _third_party_module_name(relative: PurePosixPath) -> tuple[str, bool]:
    is_package = relative.name == "__init__.py"
    parts = list(relative.parts[:-1])
    if not is_package:
        parts.append(relative.stem)
    if not parts or not all(part.isidentifier() for part in parts):
        _fail("third-party Python source path is not importable")
    return ".".join(parts), is_package


def build_third_party_source_closure_v180r12r4(
    external_root: dict[str, Any],
) -> dict[str, Any]:
    facts: list[dict[str, Any]] = []
    observed_modules: set[str] = set()
    total = 0
    for namespace in ("packaging", "tomli"):
        root = Path(external_root["third_party_source_roots"][namespace])
        namespace_root = root / namespace
        _validated_absolute_directory(str(namespace_root), f"{namespace} namespace root")
        candidates = sorted(namespace_root.rglob("*.py"))
        if not candidates:
            _fail(f"{namespace} source closure is empty")
        for path in candidates:
            relative = PurePosixPath(path.relative_to(root).as_posix())
            module, is_package = _third_party_module_name(relative)
            if module in observed_modules or not (
                module == namespace or module.startswith(f"{namespace}.")
            ):
                _fail("third-party source closure is duplicated or escaped")
            raw = _stable_read_file(
                path,
                label=f"third-party source {module}",
                byte_cap=SOURCE_FILE_BYTE_CAP,
            )
            total += len(raw)
            if (
                len(facts) >= SOURCE_CLOSURE_FILE_CAP
                or total > SOURCE_CLOSURE_TOTAL_BYTE_CAP
            ):
                _fail("third-party source closure exceeds its frozen cap")
            observed_modules.add(module)
            facts.append(
                {
                    "module": module,
                    "is_package": is_package,
                    "source_root": str(root),
                    **_raw_fact(relative.as_posix(), raw),
                }
            )
    return _closure(facts, sort_key="module")


def _resolved_regular_executable_fact(
    requested: str,
    label: str,
) -> tuple[Path, bytes, int]:
    requested_path = Path(requested)
    if not requested_path.is_absolute() or str(requested_path) != requested:
        _fail(f"requested {label} path changed")
    try:
        resolved = requested_path.resolve(strict=True)
    except OSError as error:
        raise V180r12r4PrelaunchMaterializationError(
            f"requested {label} cannot be resolved"
        ) from error
    raw = _stable_read_file(
        resolved,
        label=f"resolved {label}",
        byte_cap=EXECUTABLE_BYTE_CAP,
    )
    metadata = os.lstat(resolved)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        _fail(f"resolved {label} is not one singly linked regular file")
    return resolved, raw, metadata.st_mode


def build_runtime_tcb_fact_v180r12r4() -> dict[str, Any]:
    if sys.executable != PYTHON_EXECUTABLE:
        _fail("materializer requires exact /usr/bin/python3")
    expected_flags = {
        "isolated": 1,
        "no_site": 1,
        "no_user_site": 1,
        "ignore_environment": 1,
        "dont_write_bytecode": 1,
    }
    if (
        {name: getattr(sys.flags, name) for name in expected_flags} != expected_flags
        or sys.pycache_prefix != PYCACHE_PREFIX
        or sys.dont_write_bytecode is not True
    ):
        _fail("materializer isolated Python flags changed")
    dev_null = os.lstat("/dev/null")
    if not (
        stat.S_ISCHR(dev_null.st_mode)
        and os.major(dev_null.st_rdev) == 1
        and os.minor(dev_null.st_rdev) == 3
    ):
        _fail("/dev/null is not character device 1:3")
    resolved, raw, _mode = _resolved_regular_executable_fact(
        PYTHON_EXECUTABLE, "Python executable"
    )
    return {
        "requested_executable": PYTHON_EXECUTABLE,
        "resolved_executable": str(resolved),
        "executable_byte_count": len(raw),
        "executable_sha256": hashlib.sha256(raw).hexdigest(),
        "version": sys.version,
        "version_info": list(sys.version_info),
        "soabi": sysconfig.get_config_var("SOABI"),
        "base_sys_path": list(sys.path),
        "orig_argv_prefix": list(ISOLATED_ARGV_PREFIX),
        "pycache_prefix": PYCACHE_PREFIX,
        "flags": expected_flags,
    }


def _source_boundary_paths(source_plan: dict[str, Any]) -> tuple[str, ...]:
    paths = {
        fact["relative_path"]
        for fact in source_plan["authorization_source_closure"]["facts"]
    }
    paths.update(
        {
            AUTHORIZATION_SELF_RELATIVE_PATH,
            SOURCE_BOOTSTRAP_RELATIVE_PATH,
            SOURCE_LAUNCHER_RELATIVE_PATH,
            MATERIALIZER_RELATIVE_PATH,
        }
    )
    return tuple(sorted(paths))


def build_git_tcb_fact_v180r12r4(
    repository_root: Path,
    external_root: dict[str, Any],
    topology: dict[str, Any],
    source_plan: dict[str, Any],
) -> dict[str, Any]:
    resolved, raw, mode = _resolved_regular_executable_fact(
        GIT_EXECUTABLE, "Git executable"
    )
    version_argv = [GIT_EXECUTABLE, "--version"]
    version_environment = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "LC_ALL": "C",
    }
    try:
        completed = subprocess.run(
            version_argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            env=version_environment,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise V180r12r4PrelaunchMaterializationError(
            "Git version probe failed"
        ) from error
    if (
        completed.returncode != 0
        or completed.stderr
        or not completed.stdout.endswith(b"\n")
        or len(completed.stdout) > 1024
    ):
        _fail("Git version probe changed")
    try:
        version_stdout = completed.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise V180r12r4PrelaunchMaterializationError(
            "Git version output is non-UTF-8"
        ) from error

    c_pre = external_root["c_pre_commit_id"]
    head = topology["literal_commit_id"]
    paths = _source_boundary_paths(source_plan)
    prefix = [GIT_EXECUTABLE, "-C", str(repository_root)]
    runner_argv = [
        [
            *prefix,
            "rev-parse",
            "--show-toplevel",
            "--absolute-git-dir",
            "--git-common-dir",
            f"{c_pre}^{{commit}}",
            f"{c_pre}^{{tree}}",
            "HEAD^{commit}",
        ],
        [
            *prefix,
            "log",
            "--first-parent",
            "--reverse",
            "--format=%H%x09%P%x09%T",
            f"{c_pre}..{head}",
        ],
        [
            *prefix,
            "diff-tree",
            "--no-commit-id",
            "--raw",
            "--no-renames",
            "-r",
            head,
        ],
        [
            *prefix,
            "log",
            "--first-parent",
            "--format=%H",
            "--name-only",
            "--no-renames",
            f"{head}..{head}",
            "--",
            *paths,
        ],
        [*prefix, "archive", "--format=tar", c_pre, "--", *paths],
        [*prefix, "cat-file", "blob", topology["literal_wrapper_blob_id"]],
    ]
    return {
        "requested_executable": GIT_EXECUTABLE,
        "resolved_executable": str(resolved),
        "executable_mode": mode,
        "executable_byte_count": len(raw),
        "executable_sha256": hashlib.sha256(raw).hexdigest(),
        "version_argv": version_argv,
        "version_environment": version_environment,
        "version_stdout": version_stdout,
        "runner_process_count": 6,
        "runner_argv": runner_argv,
        "runner_environment_template": {
            MANIFEST_SHA256_ENV: MANIFEST_SHA256_TEMPLATE,
            PREREG_COMMIT_ENV: c_pre,
            "LC_CTYPE": "C.UTF-8",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        },
    }


def build_launch_manifest_v180r12r4(
    repository_root: Path,
    output_root: Path,
    external_root: dict[str, Any],
    topology: dict[str, Any],
    source_plan: dict[str, Any],
    third_party_closure: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    """Construct canonical bootstrap-compatible manifest bytes without a cycle."""

    manifest = {
        "schema": LAUNCH_MANIFEST_SCHEMA,
        "repository_root": str(repository_root),
        "c_pre_root": str(output_root),
        "manifest_relative_path": "launch_manifest.json",
        "c_pre_commit_id": external_root["c_pre_commit_id"],
        "bootstrap": _raw_fact("bootstrap.py", source_plan["bootstrap_raw"]),
        "runtime": build_runtime_tcb_fact_v180r12r4(),
        "git": build_git_tcb_fact_v180r12r4(
            repository_root, external_root, topology, source_plan
        ),
        "authorization_source_closure_kind": AUTHORIZATION_SOURCE_CLOSURE_KIND,
        "authorization_self_module": AUTHORIZATION_SELF_MODULE,
        "authorization_raw_source_modules": source_plan[
            "authorization_raw_source_modules"
        ],
        "authorization_source_closure": source_plan[
            "authorization_source_closure"
        ],
        "working_tree_source_conformance": source_plan[
            "working_tree_source_conformance"
        ],
        "source_modules": source_plan["source_modules"],
        "third_party_source_closure": third_party_closure,
        "targets": source_plan["targets"],
        "internal_target_contract": INTERNAL_TARGET_CONTRACT,
        "production_systemd_service_contract": (
            _production_systemd_service_contract()
        ),
        "production_systemd_run_argv_templates": {
            target: _production_systemd_run_argv_template(
                repository_root, target
            )
            for target in ("measurement", "verification")
        },
        "production_service_launch_artifact_paths": {
            target: {
                "attempt": (
                    f"{OUTPUT_ROOT_RELATIVE_PATH}/"
                    f"{target.upper()}_SERVICE_LAUNCH_ATTEMPT.json"
                ),
                "receipt": (
                    f"{OUTPUT_ROOT_RELATIVE_PATH}/"
                    f"{target.upper()}_SERVICE_LAUNCH_RECEIPT.json"
                ),
                "failure": (
                    ".tmp/exact-freeze/"
                    f"v180r12r4_campaign_measurement_prelaunch_{target}_"
                    "service_launch_failure.json"
                ),
            }
            for target in ("measurement", "verification")
        },
        "production_service_launch_modes": {
            "outer_dispatch": "dispatch",
            "retained_service_entry": "service-entry",
        },
        "atomic_cgroup_birth_preflight_receipt_interface": external_root[
            "atomic_cgroup_birth_preflight_receipt_interface"
        ],
        "frozen_authorization_context": external_root[
            "frozen_authorization_context"
        ],
        "working_tree_mutation_after_snapshot_in_scope": False,
    }
    raw = canonical_json_bytes(manifest)
    if len(raw) > LAUNCH_MANIFEST_BYTE_CAP:
        _fail("launch manifest exceeds its frozen byte cap")
    if MANIFEST_SHA256_TEMPLATE.encode("ascii") in raw:
        # The sentinel belongs only inside the Git environment template.  It is
        # intentionally not replaced with the manifest's self-digest.
        if raw.count(MANIFEST_SHA256_TEMPLATE.encode("ascii")) != 1:
            _fail("launch manifest digest sentinel count changed")
    else:
        _fail("launch manifest digest sentinel is absent")
    return manifest, raw


def _open_or_create_directory_at(parent_fd: int, name: str) -> tuple[int, bool]:
    if "/" in name or name in {"", ".", ".."}:
        _fail("directory component is malformed")
    created = False
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        created = True
        os.fsync(parent_fd)
    except FileExistsError:
        pass
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as error:
        raise V180r12r4PrelaunchMaterializationError(
            f"directory component is absent, linked, or nondirectory: {name}"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        _fail(f"directory component is nondirectory: {name}")
    if created:
        os.fchmod(descriptor, 0o700)
        os.fsync(descriptor)
    return descriptor, created


def _prepare_exact_freeze_parent(repository_root: Path) -> int:
    root_fd = os.open(
        repository_root,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    descriptor = root_fd
    try:
        for component in (".tmp", "exact-freeze"):
            child, _created = _open_or_create_directory_at(descriptor, component)
            if descriptor != root_fd:
                os.close(descriptor)
            descriptor = child
        os.close(root_fd)
        return descriptor
    except BaseException:
        if descriptor != root_fd:
            os.close(descriptor)
        os.close(root_fd)
        raise


def _entry_exists_at(directory_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise V180r12r4PrelaunchMaterializationError(
            f"cannot inspect prior materialization entry: {name}"
        ) from error
    return True


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    offset = 0
    while offset < len(view):
        written = os.write(descriptor, view[offset : offset + 1024 * 1024])
        if written <= 0:
            _fail("write-once file write made no progress")
        offset += written


def _write_file_once_at(
    directory_fd: int,
    name: str,
    raw: bytes,
) -> None:
    if "/" in name or name in {"", ".", ".."} or type(raw) is not bytes:
        _fail("write-once file request is malformed")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )
    descriptor = os.open(name, flags, 0o400, dir_fd=directory_fd)
    try:
        os.fchmod(descriptor, 0o400)
        _write_all(descriptor, raw)
        metadata = os.fstat(descriptor)
        if not (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_nlink == 1
            and stat.S_IMODE(metadata.st_mode) == 0o400
            and metadata.st_size == len(raw)
        ):
            _fail("write-once file metadata changed")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.fsync(directory_fd)


def _create_output_root(exact_freeze_fd: int) -> int:
    name = PurePosixPath(OUTPUT_ROOT_RELATIVE_PATH).name
    try:
        os.mkdir(name, 0o700, dir_fd=exact_freeze_fd)
    except FileExistsError as error:
        raise V180r12r4PrelaunchMaterializationReplayForbidden(
            "prelaunch materialization output root already exists; rerun forbidden"
        ) from error
    os.fsync(exact_freeze_fd)
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=exact_freeze_fd,
    )
    os.fchmod(descriptor, 0o700)
    os.fsync(descriptor)
    if stat.S_IMODE(os.fstat(descriptor).st_mode) != 0o700:
        os.close(descriptor)
        _fail("prelaunch materialization output root mode changed")
    return descriptor


def _bounded_error_text(error: BaseException) -> tuple[str, str]:
    error_type = type(error).__name__[:128]
    try:
        message = str(error)
    except BaseException:
        message = "UNFORMATTABLE_EXCEPTION"
    raw = message.encode("utf-8", errors="replace")[:FAILURE_MESSAGE_BYTE_CAP]
    while True:
        try:
            message = raw.decode("utf-8")
            break
        except UnicodeDecodeError:
            raw = raw[:-1]
    return error_type, message


def _observe_fixed_entry(path: Path, byte_cap: int) -> dict[str, Any]:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return {"presence": "ABSENT"}
    except OSError:
        return {"presence": "OBSERVATION_ERROR"}
    if stat.S_ISLNK(metadata.st_mode):
        return {"presence": "SYMLINK"}
    if stat.S_ISDIR(metadata.st_mode):
        return {
            "presence": "DIRECTORY",
            "mode": stat.S_IMODE(metadata.st_mode),
        }
    if not stat.S_ISREG(metadata.st_mode):
        return {"presence": "NONREGULAR"}
    observation: dict[str, Any] = {
        "presence": "REGULAR_FILE",
        "mode": stat.S_IMODE(metadata.st_mode),
        "byte_count": metadata.st_size,
    }
    if metadata.st_size <= byte_cap:
        try:
            raw = _stable_read_file(
                path,
                label=f"partial artifact {path.name}",
                byte_cap=byte_cap,
            )
        except BaseException as error:
            observation["read_error_type"] = type(error).__name__[:128]
        else:
            observation["sha256"] = hashlib.sha256(raw).hexdigest()
    else:
        observation["sha256"] = None
        observation["byte_cap_exceeded"] = True
    return observation


def observe_materialization_progress_v180r12r4(
    repository_root: Path,
) -> dict[str, Any]:
    output_root = repository_root / OUTPUT_ROOT_RELATIVE_PATH
    return {
        "output_root": _observe_fixed_entry(output_root, 0),
        "bootstrap": _observe_fixed_entry(
            repository_root / BOOTSTRAP_RELATIVE_PATH, BOOTSTRAP_BYTE_CAP
        ),
        "launcher": _observe_fixed_entry(
            repository_root / RETAINED_LAUNCHER_RELATIVE_PATH, LAUNCHER_BYTE_CAP
        ),
        "launch_manifest": _observe_fixed_entry(
            repository_root / LAUNCH_MANIFEST_RELATIVE_PATH,
            LAUNCH_MANIFEST_BYTE_CAP,
        ),
        "materialization_terminal": _observe_fixed_entry(
            repository_root / MATERIALIZATION_TERMINAL_RELATIVE_PATH,
            LAUNCH_MANIFEST_BYTE_CAP,
        ),
        "materialization_failure": _observe_fixed_entry(
            repository_root / MATERIALIZATION_FAILURE_RELATIVE_PATH,
            LAUNCH_MANIFEST_BYTE_CAP,
        ),
    }


def build_materialization_terminal_v180r12r4(
    *,
    repository_root: Path,
    external_root_path: Path,
    external_root_raw: bytes,
    external_root: dict[str, Any],
    topology: dict[str, Any],
    source_plan: dict[str, Any],
    third_party_closure: dict[str, Any],
    manifest_raw: bytes,
) -> tuple[dict[str, Any], bytes]:
    payload = {
        "schema": MATERIALIZATION_TERMINAL_SCHEMA,
        "materialization_rule_id": MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository_root),
        "external_root": {
            "absolute_path": str(external_root_path),
            "byte_count": len(external_root_raw),
            "sha256": hashlib.sha256(external_root_raw).hexdigest(),
            "immutable_mode": "0400",
        },
        "git_topology": topology,
        "bootstrap_source_git_blob": external_root["bootstrap_git_blob"],
        "launcher_source_git_blob": external_root["launcher_git_blob"],
        "materializer_source_git_blob": external_root["materializer_git_blob"],
        "retained_bootstrap": _raw_fact(
            BOOTSTRAP_RELATIVE_PATH, source_plan["bootstrap_raw"]
        ),
        "retained_launcher": _raw_fact(
            RETAINED_LAUNCHER_RELATIVE_PATH, source_plan["launcher_raw"]
        ),
        "launch_manifest": _raw_fact(
            LAUNCH_MANIFEST_RELATIVE_PATH, manifest_raw
        ),
        "production_transient_service_rows": [
            {
                "target": "measurement",
                "token": PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN,
                "unit_name": PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME,
            },
            {
                "target": "verification",
                "token": PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN,
                "unit_name": PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME,
            },
        ],
        "production_service_launch_artifact_paths": {
            target: {
                "attempt": (
                    f"{OUTPUT_ROOT_RELATIVE_PATH}/"
                    f"{target.upper()}_SERVICE_LAUNCH_ATTEMPT.json"
                ),
                "receipt": (
                    f"{OUTPUT_ROOT_RELATIVE_PATH}/"
                    f"{target.upper()}_SERVICE_LAUNCH_RECEIPT.json"
                ),
                "failure": (
                    ".tmp/exact-freeze/"
                    f"v180r12r4_campaign_measurement_prelaunch_{target}_"
                    "service_launch_failure.json"
                ),
            }
            for target in ("measurement", "verification")
        },
        "production_service_launch_modes": {
            "outer_dispatch": "dispatch",
            "retained_service_entry": "service-entry",
        },
        "atomic_cgroup_birth_preflight_receipt_interface": external_root[
            "atomic_cgroup_birth_preflight_receipt_interface"
        ],
        "materialization_terminal_relative_path": (
            MATERIALIZATION_TERMINAL_RELATIVE_PATH
        ),
        "materialization_failure_relative_path": (
            MATERIALIZATION_FAILURE_RELATIVE_PATH
        ),
        "authorization_source_closure_file_count": source_plan[
            "authorization_source_closure"
        ]["file_count"],
        "authorization_source_closure_total_byte_count": source_plan[
            "authorization_source_closure"
        ]["total_byte_count"],
        "authorization_source_closure_facts_sha256": source_plan[
            "authorization_source_closure"
        ]["facts_sha256"],
        "third_party_source_closure_file_count": third_party_closure["file_count"],
        "third_party_source_closure_total_byte_count": third_party_closure[
            "total_byte_count"
        ],
        "third_party_source_closure_facts_sha256": third_party_closure[
            "facts_sha256"
        ],
        "normalized_wrapper_fact": source_plan[
            "boundary_wrapper_normalized_fact"
        ],
        "current_literal_wrapper_raw_observation": source_plan[
            "current_wrapper_raw_fact"
        ],
        "working_tree_source_conformance": source_plan[
            "working_tree_source_conformance"
        ],
        "launch_manifest_digest_is_runtime_supplied_not_protocol_frozen": True,
        "launch_manifest_has_no_self_digest": True,
        "frozen_authorization_context_sha256": hashlib.sha256(
            canonical_json_bytes(external_root["frozen_authorization_context"])
        ).hexdigest(),
        "external_root_created_before_authorized_measurement_execution": True,
        "external_root_required_before_authorization_issuance": False,
        "materialization_terminal_written_last": True,
        "write_once_o_excl": True,
        "write_no_follow": True,
        "close_on_exec": True,
        "output_directory_mode": "0700",
        "output_file_mode": "0400",
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
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_execution_allowed": False,
        "success": True,
    }
    terminal_id = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    document = {**payload, "materialization_terminal_id": terminal_id}
    return document, canonical_json_bytes(document)


def build_materialization_failure_v180r12r4(
    *,
    repository_root: Path,
    external_root_path: Path,
    expected_external_root_sha256: str,
    failed_phase: str,
    error: BaseException,
) -> tuple[dict[str, Any], bytes]:
    error_type, message = _bounded_error_text(error)
    source_conformance_diagnostic = getattr(
        error, "source_conformance_diagnostic", None
    )
    if source_conformance_diagnostic is not None and type(
        source_conformance_diagnostic
    ) is not dict:
        _fail("source-conformance failure diagnostic is not one mapping")
    payload = {
        "schema": MATERIALIZATION_FAILURE_SCHEMA,
        "materialization_rule_id": MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository_root),
        "external_root_absolute_path": str(external_root_path),
        "expected_external_root_sha256": expected_external_root_sha256,
        "failed_phase": failed_phase,
        "failure_type": error_type,
        "failure_message": message,
        "source_conformance_diagnostic": source_conformance_diagnostic,
        "partial_artifact_observations": observe_materialization_progress_v180r12r4(
            repository_root
        ),
        "same_materialization_identity_rerun_forbidden": True,
        "partial_artifacts_preserved": True,
        "construction_only": True,
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "scientific_occurrence_executed": False,
        "v180r12r4_outcome_bytes_accessed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_execution_allowed": False,
        "success": False,
    }
    failure_id = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    document = {**payload, "materialization_failure_id": failure_id}
    return document, canonical_json_bytes(document)


def _require_materializer_process_boundary(
    repository_root: Path,
    external_root_path: Path,
    expected_sha256: str,
) -> None:
    expected_environment = {EXTERNAL_ROOT_SHA256_ENV, "LC_CTYPE"}
    if (
        set(os.environ) != expected_environment
        or os.environ.get("LC_CTYPE") != "C.UTF-8"
        or os.environ.get(EXTERNAL_ROOT_SHA256_ENV) != expected_sha256
    ):
        _fail("materializer environment is not exact and sanitized")
    script_path = repository_root / MATERIALIZER_RELATIVE_PATH
    expected_orig_argv = [
        *ISOLATED_ARGV_PREFIX,
        str(script_path),
        str(repository_root),
        str(external_root_path),
    ]
    expected_argv = [
        str(script_path),
        str(repository_root),
        str(external_root_path),
    ]
    if (
        sys.orig_argv != expected_orig_argv
        or sys.argv != expected_argv
        or Path.cwd().resolve(strict=True) != repository_root
        or Path(__file__).resolve(strict=True) != script_path
    ):
        _fail("materializer exact argv, cwd, or source path changed")
    # This also rejects missing isolation flags and binds /dev/null.
    build_runtime_tcb_fact_v180r12r4()


def _write_failure_if_absent(
    *,
    exact_freeze_fd: int,
    repository_root: Path,
    external_root_path: Path,
    expected_external_root_sha256: str,
    failed_phase: str,
    error: BaseException,
) -> None:
    failure_name = PurePosixPath(MATERIALIZATION_FAILURE_RELATIVE_PATH).name
    if _entry_exists_at(exact_freeze_fd, failure_name):
        return
    _document, raw = build_materialization_failure_v180r12r4(
        repository_root=repository_root,
        external_root_path=external_root_path,
        expected_external_root_sha256=expected_external_root_sha256,
        failed_phase=failed_phase,
        error=error,
    )
    _write_file_once_at(exact_freeze_fd, failure_name, raw)


def materialize_prelaunch_v180r12r4(
    repository_root: Path,
    external_root_path: Path,
    expected_external_root_sha256: str,
    *,
    enforce_process_boundary: bool = True,
) -> dict[str, Any]:
    """Perform the fixed one-shot prelaunch materialization.

    The returned document is exactly the retained terminal.  Any failure after
    the fixed path is resolved freezes typed sibling evidence and preserves all
    partial artifacts.  Existing progress, success, or failure forbids replay.
    """

    _require_rule_identities_frozen()
    repository_root = _validated_absolute_directory(
        str(repository_root), "repository root"
    )
    expected_external_root_sha256 = _require_sha256(
        expected_external_root_sha256, "external root environment digest"
    )
    if not external_root_path.is_absolute():
        _fail("external root path must be absolute")
    expected_external_path = repository_root / EXTERNAL_ROOT_RELATIVE_PATH
    if external_root_path != expected_external_path:
        _fail("external root path differs from its frozen sibling path")
    if enforce_process_boundary:
        _require_materializer_process_boundary(
            repository_root,
            external_root_path,
            expected_external_root_sha256,
        )

    exact_freeze_fd = _prepare_exact_freeze_parent(repository_root)
    output_name = PurePosixPath(OUTPUT_ROOT_RELATIVE_PATH).name
    failure_name = PurePosixPath(MATERIALIZATION_FAILURE_RELATIVE_PATH).name
    terminal_path = repository_root / MATERIALIZATION_TERMINAL_RELATIVE_PATH
    failed_phase = "PREEXISTING_PROGRESS_CHECK"
    try:
        if _entry_exists_at(exact_freeze_fd, failure_name):
            raise V180r12r4PrelaunchMaterializationReplayForbidden(
                "prelaunch materialization failure already exists; rerun forbidden"
            )
        if _entry_exists_at(exact_freeze_fd, output_name):
            if terminal_path.exists():
                raise V180r12r4PrelaunchMaterializationReplayForbidden(
                    "prelaunch materialization terminal already exists; rerun forbidden"
                )
            error = V180r12r4PrelaunchMaterializationReplayForbidden(
                "prelaunch materialization partial output exists; rerun forbidden"
            )
            _write_failure_if_absent(
                exact_freeze_fd=exact_freeze_fd,
                repository_root=repository_root,
                external_root_path=external_root_path,
                expected_external_root_sha256=expected_external_root_sha256,
                failed_phase=failed_phase,
                error=error,
            )
            raise error

        failed_phase = "EXTERNAL_ROOT_VALIDATION"
        external_root, external_root_raw = load_external_root_v180r12r4(
            repository_root,
            external_root_path,
            expected_external_root_sha256,
        )
        failed_phase = "GIT_TOPOLOGY_VALIDATION"
        topology = verify_git_boundary_v180r12r4(repository_root, external_root)
        failed_phase = "C_PRE_SOURCE_CLOSURE"
        source_plan = build_c_pre_source_closure_v180r12r4(
            repository_root, external_root, topology
        )
        failed_phase = "THIRD_PARTY_SOURCE_CLOSURE"
        third_party_closure = build_third_party_source_closure_v180r12r4(
            external_root
        )
        if (
            len(source_plan["source_modules"])
            + len(source_plan["targets"])
            + third_party_closure["file_count"]
            > SOURCE_CLOSURE_FILE_CAP
            or sum(row["byte_count"] for row in source_plan["source_modules"])
            + sum(row["byte_count"] for row in source_plan["targets"].values())
            + third_party_closure["total_byte_count"]
            > SOURCE_CLOSURE_TOTAL_BYTE_CAP
        ):
            _fail("combined bootstrap source closure exceeds its frozen cap")
        failed_phase = "LAUNCH_MANIFEST_CONSTRUCTION"
        _manifest, manifest_raw = build_launch_manifest_v180r12r4(
            repository_root,
            repository_root / OUTPUT_ROOT_RELATIVE_PATH,
            external_root,
            topology,
            source_plan,
            third_party_closure,
        )
        terminal, terminal_raw = build_materialization_terminal_v180r12r4(
            repository_root=repository_root,
            external_root_path=external_root_path,
            external_root_raw=external_root_raw,
            external_root=external_root,
            topology=topology,
            source_plan=source_plan,
            third_party_closure=third_party_closure,
            manifest_raw=manifest_raw,
        )

        failed_phase = "OUTPUT_ROOT_CREATE"
        output_fd = _create_output_root(exact_freeze_fd)
        try:
            failed_phase = "BOOTSTRAP_WRITE"
            _write_file_once_at(output_fd, "bootstrap.py", source_plan["bootstrap_raw"])
            failed_phase = "LAUNCHER_WRITE"
            _write_file_once_at(output_fd, "launcher.py", source_plan["launcher_raw"])
            failed_phase = "LAUNCH_MANIFEST_WRITE"
            _write_file_once_at(output_fd, "launch_manifest.json", manifest_raw)
            failed_phase = "PRETERMINAL_REPLAY"
            retained_bootstrap = _stable_read_file(
                repository_root / BOOTSTRAP_RELATIVE_PATH,
                label="retained bootstrap",
                byte_cap=BOOTSTRAP_BYTE_CAP,
                required_mode=0o400,
                expected_size=len(source_plan["bootstrap_raw"]),
                expected_sha256=hashlib.sha256(
                    source_plan["bootstrap_raw"]
                ).hexdigest(),
            )
            retained_manifest = _stable_read_file(
                repository_root / LAUNCH_MANIFEST_RELATIVE_PATH,
                label="retained launch manifest",
                byte_cap=LAUNCH_MANIFEST_BYTE_CAP,
                required_mode=0o400,
                expected_size=len(manifest_raw),
                expected_sha256=hashlib.sha256(manifest_raw).hexdigest(),
            )
            retained_launcher = _stable_read_file(
                repository_root / RETAINED_LAUNCHER_RELATIVE_PATH,
                label="retained launcher",
                byte_cap=LAUNCHER_BYTE_CAP,
                required_mode=0o400,
                expected_size=len(source_plan["launcher_raw"]),
                expected_sha256=hashlib.sha256(
                    source_plan["launcher_raw"]
                ).hexdigest(),
            )
            if (
                retained_bootstrap != source_plan["bootstrap_raw"]
                or retained_launcher != source_plan["launcher_raw"]
                or retained_manifest != manifest_raw
            ):
                _fail("retained prelaunch bytes changed before terminal write")
            failed_phase = "MATERIALIZATION_TERMINAL_WRITE"
            _write_file_once_at(output_fd, "MATERIALIZATION_TERMINAL.json", terminal_raw)
        finally:
            os.close(output_fd)
        failed_phase = "POSTTERMINAL_REPLAY"
        retained_terminal = _stable_read_file(
            terminal_path,
            label="retained materialization terminal",
            byte_cap=LAUNCH_MANIFEST_BYTE_CAP,
            required_mode=0o400,
            expected_size=len(terminal_raw),
            expected_sha256=hashlib.sha256(terminal_raw).hexdigest(),
        )
        if retained_terminal != terminal_raw:
            _fail("retained materialization terminal changed")
        return terminal
    except V180r12r4PrelaunchMaterializationReplayForbidden:
        raise
    except BaseException as error:
        _write_failure_if_absent(
            exact_freeze_fd=exact_freeze_fd,
            repository_root=repository_root,
            external_root_path=external_root_path,
            expected_external_root_sha256=expected_external_root_sha256,
            failed_phase=failed_phase,
            error=error,
        )
        raise
    finally:
        os.close(exact_freeze_fd)


def main() -> None:
    if len(sys.argv) != 3:
        _fail("materializer API is exact repository root and EXTERNAL_ROOT path")
    repository_root = Path(sys.argv[1])
    external_root_path = Path(sys.argv[2])
    expected_digest = _require_sha256(
        os.environ.get(EXTERNAL_ROOT_SHA256_ENV),
        "external root environment digest",
    )
    terminal = materialize_prelaunch_v180r12r4(
        repository_root,
        external_root_path,
        expected_digest,
        enforce_process_boundary=True,
    )
    print(
        json.dumps(
            {
                "materialization_terminal_id": terminal[
                    "materialization_terminal_id"
                ],
                "launch_manifest_sha256": terminal["launch_manifest"]["sha256"],
                "success": True,
            },
            sort_keys=True,
        ),
        flush=True,
    )


__all__ = (
    "AUTHORIZATION_FINAL_ANCHOR_NAMES",
    "BOOTSTRAP_RELATIVE_PATH",
    "EXTERNAL_ROOT_RELATIVE_PATH",
    "EXTERNAL_ROOT_SCHEMA",
    "EXTERNAL_ROOT_SHA256_ENV",
    "EXPECTED_MATERIALIZATION_RULE_ID",
    "EXPECTED_SOURCE_CLOSURE_RULE_ID",
    "LAUNCH_MANIFEST_RELATIVE_PATH",
    "LAUNCH_MANIFEST_SCHEMA",
    "LAUNCHER_BYTE_CAP",
    "LAUNCHER_FINAL_ANCHOR_NAMES",
    "MATERIALIZER_RELATIVE_PATH",
    "MATERIALIZATION_FAILURE_RELATIVE_PATH",
    "MATERIALIZATION_FAILURE_SCHEMA",
    "MATERIALIZATION_RULE_DOCUMENT",
    "MATERIALIZATION_RULE_ID",
    "MATERIALIZATION_TERMINAL_RELATIVE_PATH",
    "MATERIALIZATION_TERMINAL_SCHEMA",
    "MATERIALIZER_FINAL_ANCHOR_NAMES",
    "OUTPUT_ROOT_RELATIVE_PATH",
    "RETAINED_LAUNCHER_RELATIVE_PATH",
    "PROTOCOL_FINAL_ANCHOR_NAMES",
    "PROTOCOL_SOURCE_RELATIVE_PATH",
    "SOURCE_BOOTSTRAP_RELATIVE_PATH",
    "SOURCE_CLOSURE_RULE_DOCUMENT",
    "SOURCE_CLOSURE_RULE_ID",
    "SOURCE_CLOSURE_REQUIRED_ROOTS",
    "SOURCE_LAUNCHER_RELATIVE_PATH",
    "V180r12r4PrelaunchMaterializationError",
    "V180r12r4PrelaunchMaterializationReplayForbidden",
    "build_c_pre_source_closure_v180r12r4",
    "build_launch_manifest_v180r12r4",
    "build_materialization_failure_v180r12r4",
    "build_materialization_terminal_v180r12r4",
    "build_third_party_source_closure_v180r12r4",
    "load_external_root_v180r12r4",
    "materialize_prelaunch_v180r12r4",
    "observe_materialization_progress_v180r12r4",
    "verify_git_boundary_v180r12r4",
)


if __name__ == "__main__":
    main()
