#!/usr/bin/env python3
"""One-shot V180r12r4r3 atomic cgroup-birth readiness successor.

The probe is deliberately separate from the scientific campaign identity.  Its
unit name and token bind the consumed V180r12r4r2 inner/outer failure pair, the
frozen r4r2 source commit/tree and seven-artifact terminal closure, the bounded
delegation/property-evidence repair scope, ``purpose=PREFLIGHT``, and the exact
fresh ``ordinal=3``.  It never reuses the consumed r4r2 token, unit, path,
journal, or artifact root.  A
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
import re
import select
import signal
import socket
import stat
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, NoReturn, Protocol, Sequence


PREDECESSOR_INNER_FAILURE_ID = (
    "b021afb816f3406af885182682cfc2e619035ff7d5fedde0f51a3904e60005d8"
)
PREDECESSOR_OUTER_LAUNCH_FAILURE_ID = (
    "4bf2769cc0d5f90b9156e00f4679998fe837d616bfdf6d006661a461026307e0"
)
PREDECESSOR_FROZEN_SOURCE_COMMIT_ID = (
    "8359fa2fd93405dacbeaf4428e7c77cce16b2728"
)
PREDECESSOR_FROZEN_SOURCE_TREE_ID = (
    "38d140913c43fd6bcf61c4396d50547fcf5d995c"
)
PREDECESSOR_C_PROBE_COMMIT_ID = (
    "8359fa2fd93405dacbeaf4428e7c77cce16b2728"
)
PREDECESSOR_C_PROBE_TREE_ID = (
    "38d140913c43fd6bcf61c4396d50547fcf5d995c"
)
PREDECESSOR_PROBE_SOURCE_GIT_BLOB_ID = (
    "db3737003ca09d6bb371474ed560171c35612cb9"
)
PREDECESSOR_PROBE_SOURCE_BYTE_COUNT = 666000
PREDECESSOR_PROBE_SOURCE_SHA256 = (
    "bc9c0dfd65d717ca7bb6d65d19a28d883bec79940deaba292ebd46fc4787ce92"
)
PREDECESSOR_PREFLIGHT_ORDINAL = 2
PREDECESSOR_PREFLIGHT_TOKEN = (
    "e218c592abaeaaffd896448961be06b39c0a2c83ad5afcc907a4c6aeeaca2782"
)
PREDECESSOR_TARGET_TOKEN = (
    "3848dde96e9cb4c97512888bd0498f20b92057cf8343bf77040518cd70fed008"
)
PREDECESSOR_SERVICE_UNIT_NAME = (
    "acfqp-v180r12r4r2-preflight-" + PREDECESSOR_PREFLIGHT_TOKEN + ".service"
)
PREDECESSOR_TARGET_UNIT_NAME = (
    "app-acfqpv180r12r4r2target" + PREDECESSOR_TARGET_TOKEN + ".slice"
)
PREDECESSOR_EXTERNAL_ROOT_ID = (
    "30e874e89d45e76366dc2637ad7bef541d079d001f901517bde6241b83c95a26"
)
PREDECESSOR_OUTER_LAUNCH_ATTEMPT_ID = (
    "aa7de9ff9b38b17c10b25a06e4289c8760e992049dea7827fa2b935d380e8eab"
)
PREDECESSOR_PROBE_ATTEMPT_ID = (
    "1ebc28a12dbe9eb93c08851d315484207807aa89bd61b8e85c6256d414bc763b"
)
REPAIR_SCOPE = (
    "R4R2_HOST_PARENT_CONTROLLER_DRIFT_TO_EMPTY_CONTROLLER_DELEGATION_AND_"
    "FULL_PROPERTY_DIAGNOSTICS_PREFLIGHT_ONLY"
)
PURPOSE = "PREFLIGHT"
PREFLIGHT_ORDINAL = 3
TARGET_PURPOSE = "PREFLIGHT_TARGET"
TARGET_ORDINAL = 3

TOKEN_DOMAIN = "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-token:v1"
TARGET_TOKEN_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-target-token:v1"
)
EXTERNAL_ROOT_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-external-root:v1"
)
ATTEMPT_DOMAIN = "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-attempt:v1"
SUBSTAGE_DOMAIN = "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-substage:v1"
RECEIPT_DOMAIN = "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-receipt:v1"
FAILURE_DOMAIN = "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-failure:v1"
HANDSHAKE_DOMAIN = "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-handshake:v1"
OUTER_LAUNCH_ATTEMPT_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-outer-launch-attempt:v1"
)
OUTER_LAUNCH_RECEIPT_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-outer-launch-receipt:v1"
)
OUTER_LAUNCH_SUCCESS_SEAL_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-outer-launch-success-seal:v1"
)
OUTER_LAUNCH_FAILURE_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-outer-launch-failure:v1"
)
PREPARE_RESULT_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-prepare-result:v1"
)
PREPARE_ATTEMPT_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-prepare-attempt:v1"
)
PREPARE_RECEIPT_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-prepare-receipt:v1"
)
PREPARE_FAILURE_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-prepare-failure:v1"
)
TARGET_CONFORMANCE_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-target-conformance:v1"
)
TARGET_CREATE_DIAGNOSTIC_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-target-create-diagnostic:v1"
)
TARGET_CLEANUP_DIAGNOSTIC_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-target-cleanup-diagnostic:v1"
)
HOST_PARENT_PROPERTY_SNAPSHOT_DOMAIN = (
    "acfqp:v180r12r4r3:host-parent-property-snapshot:v1"
)
HOST_PARENT_CONFORMANCE_DIAGNOSTIC_DOMAIN = (
    "acfqp:v180r12r4r3:host-parent-conformance-diagnostic:v1"
)
HOST_PARENT_OBSERVATION_FAILURE_DOMAIN = (
    "acfqp:v180r12r4r3:host-parent-observation-failure:v1"
)
HOST_PARENT_IDENTITY_CONFORMANCE_DOMAIN = (
    "acfqp:v180r12r4r3:host-parent-identity-conformance:v1"
)
SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_DOMAIN = (
    "acfqp:v180r12r4r3:source-unit-conformance-diagnostic:v1"
)
ORDINARY_FAILURE_DIAGNOSTIC_DOMAIN = (
    "acfqp:v180r12r4r3:ordinary-failure-diagnostic:v1"
)
SAME_UID_MANAGER_CONCURRENCY_POLICY_DOMAIN = (
    "acfqp:v180r12r4r3:same-uid-manager-concurrency-policy:v1"
)
PREDECESSOR_ARTIFACT_FACT_DOMAIN = (
    "acfqp:v180r12r4r3:atomic-cgroup-birth-preflight-predecessor-artifact-fact:v1"
)

EXTERNAL_ROOT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_r4r3_external_root.v1"
INVOCATION_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_r4r3_systemd_invocation.v1"
TARGET_LIFECYCLE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_target_lifecycle.v1"
)
TARGET_CONFORMANCE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_target_conformance.v1"
)
TARGET_CREATE_DIAGNOSTIC_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_target_create_diagnostic.v1"
)
TARGET_CLEANUP_DIAGNOSTIC_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_target_cleanup_diagnostic.v1"
)
HOST_PARENT_PROPERTY_SNAPSHOT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_host_parent_property_snapshot.v1"
)
HOST_PARENT_CONFORMANCE_DIAGNOSTIC_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_host_parent_conformance_diagnostic.v1"
)
HOST_PARENT_OBSERVATION_FAILURE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_host_parent_observation_failure.v1"
)
HOST_PARENT_IDENTITY_CONFORMANCE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_host_parent_identity_conformance.v1"
)
SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_source_unit_conformance_diagnostic.v1"
)
ORDINARY_FAILURE_DIAGNOSTIC_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_ordinary_failure_diagnostic.v1"
)
SAME_UID_MANAGER_CONCURRENCY_POLICY_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_same_uid_manager_concurrency_policy.v1"
)
SAME_UID_MANAGER_CONCURRENCY_POLICY_STATUS = (
    "UNVERIFIED_THREAT_MODEL_EXCLUSION"
)
SAME_UID_MANAGER_CONCURRENCY_POLICY_PRINCIPAL = (
    "CONCURRENT_PROCESS_WITH_SAME_EFFECTIVE_UID"
)
SAME_UID_MANAGER_CONCURRENCY_POLICY_SURFACE = (
    "ANY_MUTATION_VIA_USER_MANAGER_OR_CGROUP_PATH_AFFECTING_EXACT_SOURCE_"
    "SERVICE_UNIT_OR_TARGET_SLICE_MANAGER_OBJECT_TRANSIENT_FRAGMENT_OR_"
    "CGROUP_PATH"
)
SAME_UID_MANAGER_CONCURRENCY_POLICY_WINDOW = (
    "OUTER_PRELAUNCH_ABSENCE_THROUGH_OUTER_TERMINAL_PUBLICATION"
)
MANAGER_STOP_IDENTITY_BINDING = (
    "UNIT_NAME_ONLY_NONATOMIC_UNDER_DECLARED_EXCLUSION"
)
MANAGER_STOP_NOT_DISPATCHED = "NOT_DISPATCHED"
MANAGER_STOP_IDENTITY_UNKNOWN = "UNKNOWN_NO_EXACT_INNER_TERMINAL"
PREDECESSOR_ARTIFACT_FACT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_predecessor_artifact_fact.v1"
)
TOOLCHAIN_EXECUTABLE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_toolchain_executable.v1"
)
HOST_PARENT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_r4r3_host_parent_fact.v1"
SOURCE_FACT_SCHEMA = "acfqp.git_source_fact_r4r3.v1"
ATTEMPT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_r4r3_attempt.v1"
SUBSTAGE_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_r4r3_substage.v1"
RECEIPT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_r4r3_receipt.v1"
FAILURE_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_r4r3_failure.v1"
HANDSHAKE_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_r4r3_handshake.v1"
OUTER_LAUNCH_ATTEMPT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_outer_launch_attempt.v1"
)
OUTER_LAUNCH_RECEIPT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_outer_launch_receipt.v1"
)
OUTER_LAUNCH_SUCCESS_SEAL_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_outer_launch_success_seal.v1"
)
OUTER_LAUNCH_FAILURE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_outer_launch_failure.v1"
)
PREPARE_RESULT_SCHEMA = "acfqp.atomic_cgroup_birth_preflight_r4r3_prepare_result.v1"
PREPARE_ATTEMPT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_prepare_attempt.v1"
)
PREPARE_RECEIPT_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_prepare_receipt.v1"
)
PREPARE_FAILURE_SCHEMA = (
    "acfqp.atomic_cgroup_birth_preflight_r4r3_prepare_failure.v1"
)

PROBE_SOURCE_RELATIVE_PATH = (
    "scripts/probe_v180r12r4r3_atomic_cgroup_birth_readiness.py"
)
PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH = (
    "scripts/probe_v180r12r4r2_atomic_cgroup_birth_readiness.py"
)
EXTERNAL_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4r3_atomic_birth_readiness_external_root.json"
)
ARTIFACT_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4r3_atomic_birth_readiness"
)
PREDECESSOR_ARTIFACT_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4r2_atomic_birth_readiness"
)
PREDECESSOR_TERMINAL_ARTIFACT_SPECS = (
    {
        "name": (
            "v180r12r4r2_atomic_birth_readiness_PREFLIGHT_ordinal-2_"
            "PREPARE_ATTEMPT.json"
        ),
        "relative_path": (
            ".tmp/exact-freeze/"
            "v180r12r4r2_atomic_birth_readiness_PREFLIGHT_ordinal-2_"
            "PREPARE_ATTEMPT.json"
        ),
        "byte_count": 1362,
        "git_mode": "100644",
        "git_blob_id": "8533ec0fab0061498a8ebcf5780d713a260ef815",
        "sha256": (
            "07432f3cdd7d68968f06ef67736ecb42b7a2ca6a18e6ff6f3a23182c8398ef51"
        ),
        "document_schema": (
            "acfqp.atomic_cgroup_birth_preflight_r4r2_prepare_attempt.v1"
        ),
        "identity_field": "prepare_attempt_id",
        "identity_domain": (
            "acfqp:v180r12r4r2:atomic-cgroup-birth-preflight-prepare-attempt:v1"
        ),
        "document_id": (
            "ad712662ddefe3075cb92237aa9dce113e0ab7bace64e35e86a76f684d4cbf7b"
        ),
    },
    {
        "name": (
            "v180r12r4r2_atomic_birth_readiness_PREFLIGHT_ordinal-2_"
            "PREPARE_RECEIPT.json"
        ),
        "relative_path": (
            ".tmp/exact-freeze/"
            "v180r12r4r2_atomic_birth_readiness_PREFLIGHT_ordinal-2_"
            "PREPARE_RECEIPT.json"
        ),
        "byte_count": 1439,
        "git_mode": "100644",
        "git_blob_id": "cac6131656f399000a3d369d7be24a0ae2188d3a",
        "sha256": (
            "60ca7831a1ee8f86bdf780762af2f51635157efe0569f0efae3ead592750ac5f"
        ),
        "document_schema": (
            "acfqp.atomic_cgroup_birth_preflight_r4r2_prepare_receipt.v1"
        ),
        "identity_field": "prepare_receipt_id",
        "identity_domain": (
            "acfqp:v180r12r4r2:atomic-cgroup-birth-preflight-prepare-receipt:v1"
        ),
        "document_id": (
            "32c42c3345b4b5ee95e0210abd17a75bea57138edfef5650933bc4599be0a9b9"
        ),
    },
    {
        "name": "v180r12r4r2_atomic_birth_readiness_external_root.json",
        "relative_path": (
            ".tmp/exact-freeze/"
            "v180r12r4r2_atomic_birth_readiness_external_root.json"
        ),
        "byte_count": 17723,
        "git_mode": "100644",
        "git_blob_id": "ed41dd4fb2299e97e1a2e6a8e4a5da271f5b1030",
        "sha256": (
            "c31cf9e73c71614352b47556e89184def9846762aa1b5f65d7388b994a1784fb"
        ),
        "document_schema": (
            "acfqp.atomic_cgroup_birth_preflight_r4r2_external_root.v1"
        ),
        "identity_field": "external_root_id",
        "identity_domain": (
            "acfqp:v180r12r4r2:atomic-cgroup-birth-preflight-external-root:v1"
        ),
        "document_id": PREDECESSOR_EXTERNAL_ROOT_ID,
    },
    {
        "name": "LAUNCH_ATTEMPT.json",
        "relative_path": (
            PREDECESSOR_ARTIFACT_ROOT_RELATIVE_PATH + "/LAUNCH_ATTEMPT.json"
        ),
        "byte_count": 2911,
        "git_mode": "100644",
        "git_blob_id": "49281ae8140f89061f85ef507d75f0b0ee504754",
        "sha256": (
            "8363c5203a40392b636bcd8c4e45c58491962d9287cb326534a292cfc39f9bf9"
        ),
        "document_schema": (
            "acfqp.atomic_cgroup_birth_preflight_r4r2_outer_launch_attempt.v1"
        ),
        "identity_field": "outer_launch_attempt_id",
        "identity_domain": (
            "acfqp:v180r12r4r2:atomic-cgroup-birth-preflight-outer-launch-attempt:v1"
        ),
        "document_id": (
            "aa7de9ff9b38b17c10b25a06e4289c8760e992049dea7827fa2b935d380e8eab"
        ),
    },
    {
        "name": "ATTEMPT.json",
        "relative_path": (
            PREDECESSOR_ARTIFACT_ROOT_RELATIVE_PATH + "/ATTEMPT.json"
        ),
        "byte_count": 1621,
        "git_mode": "100644",
        "git_blob_id": "c3e017d841ace3e9b8f9ba9fb704c5a410734866",
        "sha256": (
            "821b1ed994e8c3e9853089ad529cf1ef6aa4f5dd2641157beb61c5ce65c597ff"
        ),
        "document_schema": "acfqp.atomic_cgroup_birth_preflight_r4r2_attempt.v1",
        "identity_field": "probe_attempt_id",
        "identity_domain": (
            "acfqp:v180r12r4r2:atomic-cgroup-birth-preflight-attempt:v1"
        ),
        "document_id": (
            "1ebc28a12dbe9eb93c08851d315484207807aa89bd61b8e85c6256d414bc763b"
        ),
    },
    {
        "name": "FAILURE.json",
        "relative_path": (
            PREDECESSOR_ARTIFACT_ROOT_RELATIVE_PATH + "/FAILURE.json"
        ),
        "byte_count": 3733,
        "git_mode": "100644",
        "git_blob_id": "cb28effa230b84da745dbbeae8d7ade9f5d797da",
        "sha256": (
            "8cd573a8c47829a9cb1ec3d3a0b9b66995f2178d9bd74ae627bb37e85517517b"
        ),
        "document_schema": "acfqp.atomic_cgroup_birth_preflight_r4r2_failure.v1",
        "identity_field": "preflight_failure_id",
        "identity_domain": (
            "acfqp:v180r12r4r2:atomic-cgroup-birth-preflight-failure:v1"
        ),
        "document_id": PREDECESSOR_INNER_FAILURE_ID,
    },
    {
        "name": "LAUNCH_FAILURE.json",
        "relative_path": (
            PREDECESSOR_ARTIFACT_ROOT_RELATIVE_PATH + "/LAUNCH_FAILURE.json"
        ),
        "byte_count": 16732,
        "git_mode": "100644",
        "git_blob_id": "4173f6ba03d5683ed348f9c71d66351eed23574e",
        "sha256": (
            "33abb2f982ec9bfd49ee6c79ddb2e8834f7bdf9adcd883171d005a5cf93c58cf"
        ),
        "document_schema": (
            "acfqp.atomic_cgroup_birth_preflight_r4r2_outer_launch_failure.v1"
        ),
        "identity_field": "outer_launch_failure_id",
        "identity_domain": (
            "acfqp:v180r12r4r2:atomic-cgroup-birth-preflight-outer-launch-failure:v1"
        ),
        "document_id": PREDECESSOR_OUTER_LAUNCH_FAILURE_ID,
    },
)
ATTEMPT_NAME = "ATTEMPT.json"
RECEIPT_NAME = "RECEIPT.json"
FAILURE_NAME = "FAILURE.json"
OUTER_LAUNCH_ATTEMPT_NAME = "LAUNCH_ATTEMPT.json"
OUTER_LAUNCH_RECEIPT_NAME = "LAUNCH_RECEIPT.json"
OUTER_LAUNCH_SUCCESS_SEAL_NAME = "LAUNCH_SUCCESS_SEAL.json"
OUTER_LAUNCH_FAILURE_NAME = "LAUNCH_FAILURE.json"
PREPARE_ATTEMPT_NAME = (
    f"v180r12r4r3_atomic_birth_readiness_PREFLIGHT_ordinal-{PREFLIGHT_ORDINAL}_"
    "PREPARE_ATTEMPT.json"
)
PREPARE_RECEIPT_NAME = (
    f"v180r12r4r3_atomic_birth_readiness_PREFLIGHT_ordinal-{PREFLIGHT_ORDINAL}_"
    "PREPARE_RECEIPT.json"
)
PREPARE_FAILURE_NAME = (
    f"v180r12r4r3_atomic_birth_readiness_PREFLIGHT_ordinal-{PREFLIGHT_ORDINAL}_"
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
BUSCTL = "/usr/bin/busctl"
ENV_BINARY = "/usr/bin/env"
PYTHON_BINARY = "/usr/bin/python3"
GIT_BINARY = "/usr/bin/git"
TOOLCHAIN_EXECUTABLE_PATHS = (
    GIT_BINARY,
    SYSTEMD_RUN,
    SYSTEMCTL,
    BUSCTL,
    ENV_BINARY,
    PYTHON_BINARY,
)
SERVICE_SLICE = "app.slice"
SERVICE_TYPE = "exec"
TARGET_UNIT_TYPE = "slice"
TARGET_DESCRIPTION = "ACFQP V180r12r4r3 atomic-birth empty transient slice"
EXTERNAL_ROOT_PATH_ENV = (
    "ACFQP_V180R12R4R3_ATOMIC_BIRTH_EXTERNAL_ROOT_PATH"
)
EXTERNAL_ROOT_SHA256_ENV = (
    "ACFQP_V180R12R4R3_ATOMIC_BIRTH_EXTERNAL_ROOT_SHA256"
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
TARGET_MANAGER_STABLE_MISMATCH_POLLS = 2
TARGET_MANAGER_ABSENCE_PROPERTIES = (
    "LoadState",
    "ActiveState",
    "SubState",
    "ControlGroup",
    "BindsTo",
    "After",
    "Delegate",
    "CollectMode",
    "Slice",
    "Transient",
    "FragmentPath",
    "UnitFileState",
    "Job",
)
TARGET_MANAGER_ACTIVE_PROPERTIES = TARGET_MANAGER_ABSENCE_PROPERTIES
TARGET_MANAGER_ABSENCE_PROPERTY_KEYS = frozenset(
    TARGET_MANAGER_ABSENCE_PROPERTIES
)
TARGET_MANAGER_ACTIVE_PROPERTY_KEYS = frozenset(
    TARGET_MANAGER_ACTIVE_PROPERTIES
)
HOST_PARENT_PROPERTY_NAMES = (
    "fstatfs_type",
    "cgroup.controllers",
    "cgroup.subtree_control",
    "cgroup.type",
)
HOST_PARENT_PROPERTY_KEYS = frozenset(HOST_PARENT_PROPERTY_NAMES)
HOST_PARENT_IDENTITY_PROPERTY_NAMES = (
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
    "runtime_dir_file_type",
    "user_bus_device",
    "user_bus_inode",
    "user_bus_owner_uid",
    "user_bus_owner_gid",
    "user_bus_mode",
    "user_bus_file_type",
)
HOST_PARENT_IDENTITY_PROPERTY_KEYS = frozenset(
    HOST_PARENT_IDENTITY_PROPERTY_NAMES
)
HOST_PARENT_SNAPSHOT_PHASES = frozenset(
    {"PREPARE", "PRELAUNCH", "POSTLAUNCH", "INNER_ACTIVE"}
)
SOURCE_MANAGER_ACTIVE_PROPERTIES = (
    "LoadState",
    "ActiveState",
    "SubState",
    "ControlGroup",
    "Delegate",
    "DelegateControllers",
    "Slice",
    "Type",
    "CollectMode",
    "FragmentPath",
    "Transient",
)
SOURCE_MANAGER_ACTIVE_PROPERTY_KEYS = frozenset(
    SOURCE_MANAGER_ACTIVE_PROPERTIES
)
TARGET_MANAGER_OUTPUT_CAP_BYTES = 16 * 1024
INNER_GIT_CALL_COUNT = 8
PREPARE_GIT_CALL_COUNT = 7
OUTER_PREWORK_GIT_CALL_COUNT = 10
INNER_TOTAL_TIMEOUT_SECONDS = 70
INNER_TOTAL_TIMEOUT_NS = INNER_TOTAL_TIMEOUT_SECONDS * 1_000_000_000
UNIT_RUNTIME_MAX_SECONDS = 90
UNIT_STOP_TIMEOUT_SECONDS = 15
TARGET_CLEANUP_BUDGET_RESERVE_SECONDS = 10
OUTER_LAUNCH_TIMEOUT_SECONDS = 120
OUTER_POST_ABSENCE_SECONDS = 20
FORMAL_PREWORK_RESERVE_SECONDS = 75
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
    + TARGET_CLEANUP_BUDGET_RESERVE_SECONDS
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
        "predecessor_inner_failure_id",
        "predecessor_outer_launch_failure_id",
        "predecessor_frozen_source_commit_id",
        "predecessor_frozen_source_tree_id",
        "repair_scope",
        "purpose",
        "ordinal",
        "same_uid_manager_concurrency_policy_id",
    }
)
TARGET_LINEAGE_FIELDS = frozenset(
    {
        "predecessor_inner_failure_id",
        "predecessor_outer_launch_failure_id",
        "predecessor_frozen_source_commit_id",
        "predecessor_frozen_source_tree_id",
        "repair_scope",
        "purpose",
        "ordinal",
        "same_uid_manager_concurrency_policy_id",
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
        "property_snapshot",
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
        "delegation_enabled",
        "delegated_controllers",
        "source_active_show_argv",
        "source_expected_static_properties",
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
        "unit_type",
        "direct_child_of_app_slice",
        "transient",
        "delegate",
        "collect_mode",
        "lifecycle_authority",
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
        "binds_to_unit",
        "after_unit",
        "description",
        "transient_fragment_path",
        "environment",
        "create_argv",
        "create_job_path_pattern",
        "absence_show_argv",
        "active_show_argv",
        "stop_argv",
        "manager_call_timeout_seconds",
        "manager_process_total_bound_seconds",
        "manager_max_polls",
        "shared_inner_absolute_deadline_seconds",
    }
)
SAME_UID_MANAGER_CONCURRENCY_POLICY_FIELDS = frozenset(
    {
        "schema",
        "status",
        "principal",
        "surface",
        "window",
        "unconditional_same_uid_replacement_safety_claimed",
        "same_uid_manager_concurrency_policy_id",
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
OUTER_LAUNCH_ATTEMPT_FIELDS = frozenset(
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
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
        "external_root_id",
        "external_root_byte_count",
        "external_root_sha256",
        "systemd_run_argv",
        "systemd_run_argv_sha256",
        "deadline_budget",
        "one_shot",
        "outer_launch_attempt_id",
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
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
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
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
        "requested_manager_stop_identity_binding",
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
        "target_transient_instance_implicit_absence",
        "target_named_path_detached_and_manager_implicit_absence",
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
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
        "requested_manager_stop_identity_binding",
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
        "target_manager_implicit_absence_proven",
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
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
        "requested_manager_stop_identity_binding",
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
        "target_transient_instance_implicit_absence",
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
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
        "requested_manager_stop_identity_binding",
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
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
        "requested_manager_stop_identity_binding",
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
        "prelaunch_observation_diagnostic",
        "postlaunch_absence",
        "postlaunch_observation_diagnostic",
        "deadline_contract",
        "unit_absent",
        "target_absent",
        "source_unit_absent",
        "source_path_absent",
        "target_transient_instance_implicit_absence",
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
        "prelaunch_absence_error",
        "process_adapter_error",
        "deadline_gate_error",
        "inner_observation_error",
        "postlaunch_observation_error",
        "postlaunch_absence_error",
    }
)
OUTER_SPECIAL_FAILURE_REASONS = frozenset(
    {
        "LAUNCH_ATTEMPT_PUBLICATION_FAILED",
        "PRELAUNCH_ABSENCE_FAILED",
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
        "target_transient_instance_implicit_absence",
        "target_path_absent",
        "target_manager_implicit_absence",
        "target_manager_properties",
        "target_manager_show_argv",
        "target_manager_show_result",
        "transient_fragment_path",
        "transient_fragment_absent",
        "transient_fragment_stat_errno",
        "parent_absence_observation",
        "host_parent_conformance_diagnostic",
        "named_path_detached_and_manager_implicit_absence",
        "posix_inode_unlink_claimed",
        "poll_count",
        "systemctl_argv",
        "systemctl_result",
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
        "delegation_enabled_from_outer_context",
        "delegated_controllers_from_outer_context",
        "fixed_target_absent_before_create",
        "target_manager_implicit_absence_before_create",
        "target_manager_precreate_properties",
        "host_parent_identity_conformance_diagnostic",
        "host_parent_conformance_diagnostic",
        "source_unit_conformance_diagnostic",
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
        "initial_cgroup_events",
        "transient_fragment_path",
        "manager_create_argv",
        "manager_create_environment",
        "manager_create_returncode",
        "manager_create_job_path",
        "manager_create_stdout",
        "manager_create_stderr",
        "manager_properties",
        "manager_poll_count",
        "manager_owned_lifecycle",
        "manager_create_diagnostic",
        "probe_path_deletion_calls",
    }
)
TARGET_REMOVAL_DETAIL_FIELDS = frozenset(
    {
        "removed",
        "already_absent",
        "ownership_scope",
        "manager_unit_ownership_acquired",
        "full_target_path_ofd_conformance",
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
        "manager_implicit_absence_proven",
        "target_path_absent",
        "transient_fragment_absent",
        "transient_fragment_path",
        "transient_fragment_stat_errno",
        "parent_named_path_observation",
        "retained_ofd_detach_fact",
        "replacement_detected",
        "named_path_detached_and_manager_implicit_absence",
        "posix_inode_unlink_claimed",
        "cleanup_diagnostic",
    }
)
EXTERNAL_ROOT_FIELDS = frozenset(
    {
        "schema",
        "purpose",
        "ordinal",
        "predecessor_inner_failure_id",
        "predecessor_outer_launch_failure_id",
        "predecessor_frozen_source_commit_id",
        "predecessor_frozen_source_tree_id",
        "repair_scope",
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy",
        "predecessor_probe_source_fact",
        "predecessor_terminal_artifact_facts",
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
    """Target creation failed with its typed, replayable diagnostic trace."""

    def __init__(
        self,
        error_number: int,
        message: str,
        *,
        target: "TargetHandle | None",
        diagnostic: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(error_number, message)
        self.target = target
        self.diagnostic = None if diagnostic is None else dict(diagnostic)


class TargetRemovalError(OSError):
    """Owned-unit cleanup failed with a typed fail-closed diagnostic."""

    def __init__(
        self,
        error_number: int,
        message: str,
        *,
        diagnostic: Mapping[str, Any] | None,
    ) -> None:
        super().__init__(error_number, message)
        self.diagnostic = None if diagnostic is None else dict(diagnostic)


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


class CloneProvisionalContainmentError(OSError):
    """Parent-side clone setup failed after a concrete child was born."""

    def __init__(
        self,
        setup_error: BaseException,
        *,
        child_pid: int,
        child_pidfd: int,
        child_reaped: bool,
        resources_closed: bool,
        containment_errors: Sequence[BaseException],
    ) -> None:
        error_number = getattr(setup_error, "errno", None)
        if type(error_number) is not int or error_number <= 0:
            error_number = errno.EIO
        errors = tuple(containment_errors)
        containment_complete = child_reaped and resources_closed and not errors
        super().__init__(
            error_number,
            "CLONE3 parent setup failed after child birth; provisional "
            f"containment={'complete' if containment_complete else 'uncertain'} "
            f"pid={child_pid} pidfd={child_pidfd} "
            f"child_reaped={child_reaped} resources_closed={resources_closed} "
            f"setup_error={type(setup_error).__name__}",
        )
        self.child_pid = child_pid
        self.child_pidfd = child_pidfd
        self.child_reaped = child_reaped
        self.resources_closed = resources_closed
        self.containment_complete = containment_complete
        self.setup_error = setup_error
        self.containment_errors = errors


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


def build_same_uid_manager_concurrency_policy() -> dict[str, Any]:
    payload = {
        "schema": SAME_UID_MANAGER_CONCURRENCY_POLICY_SCHEMA,
        "status": SAME_UID_MANAGER_CONCURRENCY_POLICY_STATUS,
        "principal": SAME_UID_MANAGER_CONCURRENCY_POLICY_PRINCIPAL,
        "surface": SAME_UID_MANAGER_CONCURRENCY_POLICY_SURFACE,
        "window": SAME_UID_MANAGER_CONCURRENCY_POLICY_WINDOW,
        "unconditional_same_uid_replacement_safety_claimed": False,
    }
    return _self_id_document(
        SAME_UID_MANAGER_CONCURRENCY_POLICY_DOMAIN,
        "same_uid_manager_concurrency_policy_id",
        payload,
    )


def validate_same_uid_manager_concurrency_policy(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != SAME_UID_MANAGER_CONCURRENCY_POLICY_FIELDS
    ):
        _fail("same-UID manager concurrency policy fields changed")
    expected = build_same_uid_manager_concurrency_policy()
    if dict(value) != expected:
        _fail("same-UID manager concurrency exclusion was weakened or reclassified")
    return expected


def _same_uid_manager_concurrency_policy_join() -> dict[str, Any]:
    policy = build_same_uid_manager_concurrency_policy()
    return {
        "same_uid_manager_concurrency_policy_id": policy[
            "same_uid_manager_concurrency_policy_id"
        ],
        "same_uid_manager_concurrency_policy_status": policy["status"],
        "unconditional_same_uid_replacement_safety_claimed": policy[
            "unconditional_same_uid_replacement_safety_claimed"
        ],
    }


def preflight_lineage() -> dict[str, Any]:
    policy = build_same_uid_manager_concurrency_policy()
    return {
        "predecessor_inner_failure_id": PREDECESSOR_INNER_FAILURE_ID,
        "predecessor_outer_launch_failure_id": (
            PREDECESSOR_OUTER_LAUNCH_FAILURE_ID
        ),
        "predecessor_frozen_source_commit_id": (
            PREDECESSOR_FROZEN_SOURCE_COMMIT_ID
        ),
        "predecessor_frozen_source_tree_id": PREDECESSOR_FROZEN_SOURCE_TREE_ID,
        "repair_scope": REPAIR_SCOPE,
        "purpose": PURPOSE,
        "ordinal": PREFLIGHT_ORDINAL,
        "same_uid_manager_concurrency_policy_id": policy[
            "same_uid_manager_concurrency_policy_id"
        ],
    }


def derive_preflight_token(lineage: Mapping[str, Any]) -> str:
    if set(lineage) != LINEAGE_FIELDS or dict(lineage) != preflight_lineage():
        _fail("preflight token lineage is not its exact policy-bound authority")
    return _domain_id(TOKEN_DOMAIN, dict(lineage))


def target_lineage() -> dict[str, Any]:
    policy = build_same_uid_manager_concurrency_policy()
    return {
        "predecessor_inner_failure_id": PREDECESSOR_INNER_FAILURE_ID,
        "predecessor_outer_launch_failure_id": (
            PREDECESSOR_OUTER_LAUNCH_FAILURE_ID
        ),
        "predecessor_frozen_source_commit_id": (
            PREDECESSOR_FROZEN_SOURCE_COMMIT_ID
        ),
        "predecessor_frozen_source_tree_id": PREDECESSOR_FROZEN_SOURCE_TREE_ID,
        "repair_scope": REPAIR_SCOPE,
        "purpose": TARGET_PURPOSE,
        "ordinal": TARGET_ORDINAL,
        "same_uid_manager_concurrency_policy_id": policy[
            "same_uid_manager_concurrency_policy_id"
        ],
    }


def derive_target_token(lineage: Mapping[str, Any]) -> str:
    if set(lineage) != TARGET_LINEAGE_FIELDS or dict(lineage) != target_lineage():
        _fail("target token lineage is not its exact policy-bound authority")
    return _domain_id(TARGET_TOKEN_DOMAIN, dict(lineage))


PREFLIGHT_TOKEN = derive_preflight_token(preflight_lineage())
SERVICE_UNIT_NAME = f"acfqp-v180r12r4r3-preflight-{PREFLIGHT_TOKEN}.service"
TARGET_TOKEN = derive_target_token(target_lineage())
TARGET_SERVICE_UNIT_NAME = (
    f"app-acfqpv180r12r4r3target{TARGET_TOKEN}.slice"
)
TARGET_CGROUP_NAME = TARGET_SERVICE_UNIT_NAME
if (
    not TARGET_SERVICE_UNIT_NAME.startswith("app-")
    or not TARGET_SERVICE_UNIT_NAME.endswith(".slice")
    or TARGET_SERVICE_UNIT_NAME.count("-") != 1
):
    raise RuntimeError("target slice is not one direct app.slice child")


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
    property_snapshot = validate_host_parent_property_snapshot(
        value["property_snapshot"]
    )
    if (
        value["schema"] != HOST_PARENT_SCHEMA
        or value["mount_point"] != "/sys/fs/cgroup"
        or type(value["app_slice_path"]) is not str
        or not value["app_slice_path"].startswith("/sys/fs/cgroup/")
        or not value["app_slice_path"].endswith("/app.slice")
        or value["cgroup_type"] != "domain"
        or property_snapshot["phase"] != "PREPARE"
        or property_snapshot["app_slice_path"] != value["app_slice_path"]
        or property_snapshot["parsed_properties"]
        != {
            "fstatfs_type": CGROUP2_SUPER_MAGIC,
            "cgroup.controllers": value["controllers"],
            "cgroup.subtree_control": value["subtree_control"],
            "cgroup.type": value["cgroup_type"],
        }
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
    return {
        **dict(value),
        "toolchain_facts": toolchain_facts,
        "property_snapshot": property_snapshot,
    }


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
    policy = build_same_uid_manager_concurrency_policy()
    transient_fragment_path = (
        f"/run/user/{uid}/systemd/transient/{TARGET_SERVICE_UNIT_NAME}"
    )
    return {
        "schema": TARGET_LIFECYCLE_SCHEMA,
        "purpose": TARGET_PURPOSE,
        "ordinal": TARGET_ORDINAL,
        "target_token": TARGET_TOKEN,
        "unit_name": TARGET_SERVICE_UNIT_NAME,
        "cgroup_name": TARGET_CGROUP_NAME,
        "slice": SERVICE_SLICE,
        "unit_type": TARGET_UNIT_TYPE,
        "direct_child_of_app_slice": True,
        "transient": True,
        "delegate": False,
        "collect_mode": "inactive-or-failed",
        "lifecycle_authority": "SYSTEMD_USER_MANAGER_ONLY",
        "same_uid_manager_concurrency_policy_id": policy[
            "same_uid_manager_concurrency_policy_id"
        ],
        "same_uid_manager_concurrency_policy_status": policy["status"],
        "unconditional_same_uid_replacement_safety_claimed": policy[
            "unconditional_same_uid_replacement_safety_claimed"
        ],
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
        "binds_to_unit": SERVICE_UNIT_NAME,
        "after_unit": SERVICE_UNIT_NAME,
        "description": TARGET_DESCRIPTION,
        "transient_fragment_path": transient_fragment_path,
        "environment": environment,
        "create_argv": [
            BUSCTL,
            "--user",
            "--no-pager",
            f"--timeout={TARGET_MANAGER_CALL_TIMEOUT_SECONDS}s",
            "--allow-interactive-authorization=no",
            "call",
            "org.freedesktop.systemd1",
            "/org/freedesktop/systemd1",
            "org.freedesktop.systemd1.Manager",
            "StartTransientUnit",
            "ssa(sv)a(sa(sv))",
            TARGET_SERVICE_UNIT_NAME,
            "fail",
            "4",
            "Description",
            "s",
            TARGET_DESCRIPTION,
            "CollectMode",
            "s",
            "inactive-or-failed",
            "BindsTo",
            "as",
            "1",
            SERVICE_UNIT_NAME,
            "After",
            "as",
            "1",
            SERVICE_UNIT_NAME,
            "0",
        ],
        "create_job_path_pattern": (
            r'^o "/org/freedesktop/systemd1/job/[1-9][0-9]*"\n$'
        ),
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
        if type(argv) is list and SYSTEMD_RUN in argv:
            _fail("target lifecycle systemd-run service creation is forbidden")
        if value.get("unit_type") != "slice":
            _fail("target lifecycle must be a transient slice")
        if value.get("delegate") is not False:
            _fail("target slice must not claim unsupported delegation")
        _fail("target lifecycle contract drifted")
    return expected


def _source_active_show_argv() -> list[str]:
    return [
        SYSTEMCTL,
        "--user",
        "--no-pager",
        "show",
        *[
            f"--property={name}"
            for name in SOURCE_MANAGER_ACTIVE_PROPERTIES
        ],
        SERVICE_UNIT_NAME,
    ]


def _source_expected_static_properties(uid: int) -> dict[str, str]:
    if type(uid) is not int or uid < 0:
        _fail("source-unit expected property uid changed")
    return {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "running",
        "Delegate": "yes",
        "DelegateControllers": "",
        "Slice": SERVICE_SLICE,
        "Type": SERVICE_TYPE,
        "CollectMode": "inactive-or-failed",
        "FragmentPath": (
            f"/run/user/{uid}/systemd/transient/{SERVICE_UNIT_NAME}"
        ),
        "Transient": "yes",
    }


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
            "--property=Delegate=",
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
        "delegation_enabled": True,
        "delegated_controllers": [],
        "source_active_show_argv": _source_active_show_argv(),
        "source_expected_static_properties": (
            _source_expected_static_properties(os.geteuid())
        ),
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
        if type(options) is list and any(
            item.startswith("--property=Delegate=")
            and item != "--property=Delegate="
            for item in options
        ):
            _fail("nonempty Delegate controller assignment is forbidden")
        if value.get("delegation_enabled") is not True:
            _fail("empty-list delegation must remain enabled")
        if value.get("delegated_controllers") != []:
            _fail("delegated controller request must remain the empty list")
        if value.get("source_active_show_argv") != _source_active_show_argv():
            _fail("source-unit active property observation argv drifted")
        if value.get("source_expected_static_properties") != (
            _source_expected_static_properties(os.geteuid())
        ):
            _fail("source-unit expected property contract drifted")
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
    if any(
        item.startswith("--property=Delegate=")
        and item != "--property=Delegate="
        for item in actual
    ):
        _fail("nonempty Delegate controller assignment is forbidden")
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
    predecessor_probe_source_fact: Mapping[str, Any],
    predecessor_terminal_artifact_facts: Sequence[Mapping[str, Any]],
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
    predecessor_fact = validate_source_fact(
        predecessor_probe_source_fact,
        expected_relative_path=PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH,
    )
    predecessor_artifacts = validate_predecessor_terminal_artifact_facts(
        list(predecessor_terminal_artifact_facts)
    )
    if (
        predecessor_fact["git_blob_id"]
        != PREDECESSOR_PROBE_SOURCE_GIT_BLOB_ID
        or predecessor_fact["byte_count"]
        != PREDECESSOR_PROBE_SOURCE_BYTE_COUNT
        or predecessor_fact["sha256"] != PREDECESSOR_PROBE_SOURCE_SHA256
    ):
        _fail("predecessor probe source closure changed")
    host_fact = validate_host_parent_fact(host_parent_fact)
    invocation = validate_systemd_invocation_contract(systemd_invocation_contract)
    policy = build_same_uid_manager_concurrency_policy()
    if invocation["outer_launch_environment"] != expected_outer_launch_environment(
        host_fact["owner_uid"]
    ):
        _fail("outer launch environment uid disagrees with the host parent")
    lifecycle = invocation["target_lifecycle_contract"]
    if (
        lifecycle["same_uid_manager_concurrency_policy_id"]
        != policy["same_uid_manager_concurrency_policy_id"]
        or lifecycle["same_uid_manager_concurrency_policy_status"]
        != policy["status"]
        or lifecycle["unconditional_same_uid_replacement_safety_claimed"]
        is not False
        or lifecycle["manager_stop_identity_binding_contract"]
        != MANAGER_STOP_IDENTITY_BINDING
    ):
        _fail("target lifecycle lost its same-UID exclusion join")
    payload = {
        "schema": EXTERNAL_ROOT_SCHEMA,
        **preflight_lineage(),
        "same_uid_manager_concurrency_policy": policy,
        "predecessor_probe_source_fact": predecessor_fact,
        "predecessor_terminal_artifact_facts": predecessor_artifacts,
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
    policy = validate_same_uid_manager_concurrency_policy(
        value["same_uid_manager_concurrency_policy"]
    )
    if (
        value["same_uid_manager_concurrency_policy_id"]
        != policy["same_uid_manager_concurrency_policy_id"]
    ):
        _fail("external root policy ID join changed")
    expected = build_external_root_document(
        c_probe_commit_id=value["c_probe_commit_id"],
        c_probe_tree_id=value["c_probe_tree_id"],
        probe_source_fact=value["probe_source_fact"],
        predecessor_probe_source_fact=value["predecessor_probe_source_fact"],
        predecessor_terminal_artifact_facts=value[
            "predecessor_terminal_artifact_facts"
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


def _predecessor_artifact_fact(
    spec: Mapping[str, Any], document: Mapping[str, Any]
) -> dict[str, Any]:
    payload = {
        "schema": PREDECESSOR_ARTIFACT_FACT_SCHEMA,
        "name": spec["name"],
        "relative_path": spec["relative_path"],
        "git_mode": spec["git_mode"],
        "git_blob_id": spec["git_blob_id"],
        "byte_count": spec["byte_count"],
        "sha256": spec["sha256"],
        "document_schema": spec["document_schema"],
        "identity_field": spec["identity_field"],
        "document_id": document[spec["identity_field"]],
    }
    return _self_id_document(
        PREDECESSOR_ARTIFACT_FACT_DOMAIN,
        "predecessor_artifact_fact_id",
        payload,
    )


def observe_predecessor_terminal_artifact_facts(
    repository_root: Path,
) -> list[dict[str, Any]]:
    repository_root = _canonical_repository_root(repository_root)
    documents: dict[str, dict[str, Any]] = {}
    facts: list[dict[str, Any]] = []
    for spec in PREDECESSOR_TERMINAL_ARTIFACT_SPECS:
        raw = _read_regular_exact(
            repository_root / spec["relative_path"],
            byte_cap=MAX_ARTIFACT_BYTES,
            mode=None,
        )
        if (
            len(raw) != spec["byte_count"]
            or hashlib.sha256(raw).hexdigest() != spec["sha256"]
            or _git_blob_id(raw) != spec["git_blob_id"]
        ):
            _fail(f"predecessor {spec['name']} bytes changed")
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            _fail(f"predecessor {spec['name']} is not canonical")
        retained = _validate_self_id(
            document,
            schema=spec["document_schema"],
            identity_field=spec["identity_field"],
            domain=spec["identity_domain"],
        )
        if retained[spec["identity_field"]] != spec["document_id"]:
            _fail(f"predecessor {spec['name']} self-ID changed")
        documents[spec["name"]] = retained
        facts.append(_predecessor_artifact_fact(spec, retained))
    prepare_attempt = documents[
        "v180r12r4r2_atomic_birth_readiness_PREFLIGHT_ordinal-2_"
        "PREPARE_ATTEMPT.json"
    ]
    prepare_receipt = documents[
        "v180r12r4r2_atomic_birth_readiness_PREFLIGHT_ordinal-2_"
        "PREPARE_RECEIPT.json"
    ]
    external_root = documents[
        "v180r12r4r2_atomic_birth_readiness_external_root.json"
    ]
    launch_attempt = documents["LAUNCH_ATTEMPT.json"]
    attempt = documents["ATTEMPT.json"]
    failure = documents["FAILURE.json"]
    launch_failure = documents["LAUNCH_FAILURE.json"]
    specs_by_name = {
        str(spec["name"]): spec
        for spec in PREDECESSOR_TERMINAL_ARTIFACT_SPECS
    }
    common_inner = (launch_attempt, attempt, failure)
    expected_inner_inventory = [
        {
            "byte_count": spec["byte_count"],
            "canonical_exact": True,
            "name": spec["name"],
            "sha256": spec["sha256"],
        }
        for spec in (
            specs_by_name["ATTEMPT.json"],
            specs_by_name["FAILURE.json"],
            specs_by_name["LAUNCH_ATTEMPT.json"],
        )
    ]
    expected_inner_observation = {
        "artifact_inventory": expected_inner_inventory,
        "inner_attempt_exact": True,
        "inner_probe_attempt_id": PREDECESSOR_PROBE_ATTEMPT_ID,
        "inner_terminal_id": PREDECESSOR_INNER_FAILURE_ID,
        "inner_terminal_manager_stop_requested": False,
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
        "requested_manager_stop_identity_binding": MANAGER_STOP_NOT_DISPATCHED,
        "same_uid_manager_concurrency_policy_id": (
            failure["same_uid_manager_concurrency_policy_id"]
        ),
        "same_uid_manager_concurrency_policy_status": (
            SAME_UID_MANAGER_CONCURRENCY_POLICY_STATUS
        ),
        "state": "FAILURE",
        "unconditional_same_uid_replacement_safety_claimed": False,
    }
    records = failure.get("substage_records")
    predecessor_probe_fact = external_root.get("probe_source_fact")
    if (
        prepare_attempt.get("purpose") != "PREFLIGHT"
        or prepare_attempt.get("ordinal") != PREDECESSOR_PREFLIGHT_ORDINAL
        or prepare_attempt.get("preflight_token")
        != PREDECESSOR_PREFLIGHT_TOKEN
        or prepare_attempt.get("one_shot") is not True
        or prepare_attempt.get("artifact_root_absent_before_attempt") is not True
        or prepare_attempt.get("tracked_and_index_clean") is not True
        or prepare_attempt.get("untracked_files_in_authority") is not False
        or prepare_attempt.get("c_probe_commit_id")
        != PREDECESSOR_C_PROBE_COMMIT_ID
        or prepare_attempt.get("c_probe_tree_id")
        != PREDECESSOR_C_PROBE_TREE_ID
        or prepare_receipt.get("ordinal") != PREDECESSOR_PREFLIGHT_ORDINAL
        or prepare_receipt.get("preflight_token")
        != PREDECESSOR_PREFLIGHT_TOKEN
        or prepare_receipt.get("prepare_attempt_id")
        != prepare_attempt.get("prepare_attempt_id")
        or prepare_receipt.get("external_root_o_excl_owned") is not True
        or prepare_receipt.get("external_root_canonical_0400_durable") is not True
        or prepare_receipt.get("artifact_root_owned_0700") is not True
        or prepare_receipt.get("tracked_and_index_clean") is not True
        or prepare_receipt.get("untracked_files_in_authority") is not False
        or prepare_receipt.get("prepare_journal_relative_paths")
        != prepare_attempt.get("prepare_journal_relative_paths")
        or prepare_receipt.get("external_root_path")
        != prepare_attempt.get("external_root_path")
        or prepare_receipt.get("artifact_root")
        != prepare_attempt.get("artifact_root")
        or external_root.get("purpose") != "PREFLIGHT"
        or external_root.get("ordinal") != PREDECESSOR_PREFLIGHT_ORDINAL
        or external_root.get("preflight_token")
        != PREDECESSOR_PREFLIGHT_TOKEN
        or external_root.get("service_unit_name")
        != PREDECESSOR_SERVICE_UNIT_NAME
        or external_root.get("target_cgroup_name")
        != PREDECESSOR_TARGET_UNIT_NAME
        or external_root.get("c_probe_commit_id")
        != PREDECESSOR_C_PROBE_COMMIT_ID
        or external_root.get("c_probe_tree_id")
        != PREDECESSOR_C_PROBE_TREE_ID
        or type(predecessor_probe_fact) is not dict
        or predecessor_probe_fact.get("relative_path")
        != PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH
        or predecessor_probe_fact.get("git_mode") != "100644"
        or predecessor_probe_fact.get("git_blob_id")
        != PREDECESSOR_PROBE_SOURCE_GIT_BLOB_ID
        or predecessor_probe_fact.get("byte_count")
        != PREDECESSOR_PROBE_SOURCE_BYTE_COUNT
        or predecessor_probe_fact.get("sha256")
        != PREDECESSOR_PROBE_SOURCE_SHA256
        or any(
            document.get("external_root_id") != PREDECESSOR_EXTERNAL_ROOT_ID
            or document.get("external_root_byte_count")
            != specs_by_name[
                "v180r12r4r2_atomic_birth_readiness_external_root.json"
            ]["byte_count"]
            or document.get("external_root_sha256")
            != specs_by_name[
                "v180r12r4r2_atomic_birth_readiness_external_root.json"
            ]["sha256"]
            for document in (prepare_attempt, prepare_receipt, launch_attempt, attempt)
        )
        or any(
            document.get("ordinal") != PREDECESSOR_PREFLIGHT_ORDINAL
            or document.get("preflight_token") != PREDECESSOR_PREFLIGHT_TOKEN
            or document.get("service_unit_name")
            != PREDECESSOR_SERVICE_UNIT_NAME
            or document.get("target_cgroup_name")
            != PREDECESSOR_TARGET_UNIT_NAME
            or document.get("target_token") != PREDECESSOR_TARGET_TOKEN
            or document.get("target_unit_name")
            != PREDECESSOR_TARGET_UNIT_NAME
            or document.get("target_lifecycle_authority")
            != "SYSTEMD_USER_MANAGER_ONLY"
            for document in common_inner
        )
        or launch_failure.get("ordinal") != PREDECESSOR_PREFLIGHT_ORDINAL
        or launch_failure.get("preflight_token")
        != PREDECESSOR_PREFLIGHT_TOKEN
        or launch_failure.get("service_unit_name")
        != PREDECESSOR_SERVICE_UNIT_NAME
        or launch_failure.get("target_cgroup_name")
        != PREDECESSOR_TARGET_UNIT_NAME
        or launch_attempt.get("purpose") != "PREFLIGHT"
        or attempt.get("purpose") != "PREFLIGHT"
        or launch_attempt.get("one_shot") is not True
        or attempt.get("one_shot") is not True
        or launch_attempt.get("external_root_id")
        != PREDECESSOR_EXTERNAL_ROOT_ID
        or attempt.get("external_root_id") != PREDECESSOR_EXTERNAL_ROOT_ID
        or type(launch_attempt.get("external_root_byte_count")) is not int
        or launch_attempt.get("external_root_byte_count") <= 0
        or launch_attempt.get("external_root_byte_count")
        != attempt.get("external_root_byte_count")
        or not _is_lower_hex(launch_attempt.get("external_root_sha256"), 64)
        or launch_attempt.get("external_root_sha256")
        != attempt.get("external_root_sha256")
        or attempt.get("outer_launch_attempt_id")
        != PREDECESSOR_OUTER_LAUNCH_ATTEMPT_ID
        or launch_attempt.get("outer_launch_attempt_id")
        != PREDECESSOR_OUTER_LAUNCH_ATTEMPT_ID
        or launch_failure.get("outer_launch_attempt_id")
        != PREDECESSOR_OUTER_LAUNCH_ATTEMPT_ID
        or attempt.get("probe_attempt_id") != PREDECESSOR_PROBE_ATTEMPT_ID
        or failure.get("probe_attempt_id") != PREDECESSOR_PROBE_ATTEMPT_ID
        or launch_failure.get("outer_launch_attempt_id")
        != launch_attempt.get("outer_launch_attempt_id")
        or launch_failure.get("systemd_run_argv_sha256")
        != launch_attempt.get("systemd_run_argv_sha256")
        or failure.get("preflight_failure_id")
        != PREDECESSOR_INNER_FAILURE_ID
        or launch_failure.get("outer_launch_failure_id")
        != PREDECESSOR_OUTER_LAUNCH_FAILURE_ID
        or attempt.get("c_probe_commit_id")
        != PREDECESSOR_C_PROBE_COMMIT_ID
        or attempt.get("c_probe_tree_id") != PREDECESSOR_C_PROBE_TREE_ID
        or attempt.get("probe_source_git_blob_id")
        != PREDECESSOR_PROBE_SOURCE_GIT_BLOB_ID
        or failure.get("failed_substage")
        != "SERVICE_PLACEMENT_AND_NCA_PERMISSION"
        or failure.get("errno") != errno.ESTALE
        or failure.get("errno_name") != errno.errorcode[errno.ESTALE]
        or failure.get("error_type") != "OSError"
        or failure.get("message")
        != f"[Errno {errno.ESTALE}] host app.slice controller fact drifted"
        or type(records) is not list
        or len(records) != 3
        or [row.get("substage") for row in records]
        != [
            "ATTEMPT_PUBLICATION",
            "OUTER_CONTEXT",
            "SERVICE_PLACEMENT_AND_NCA_PERMISSION",
        ]
        or [row.get("status") for row in records] != ["OK", "OK", "FAILED"]
        or records[2].get("detail") != {}
        or records[2].get("errno") != errno.ESTALE
        or records[2].get("error_type") != "OSError"
        or failure.get("target_manager_stop_requested") is not False
        or failure.get("target_manager_implicit_absence_proven") is not False
        or failure.get("target_absent") is not False
        or failure.get("target_may_remain") is not True
        or failure.get("target_identity_continuous") is not False
        or failure.get("requested_manager_stop_identity_binding")
        != MANAGER_STOP_NOT_DISPATCHED
        or failure.get("scientific_occurrence_started") is not False
        or failure.get("campaign_actual_measurement") is not False
        or launch_failure.get("inner_observation")
        != expected_inner_observation
        or launch_failure.get("inventory_before_launch_failure")
        != ["ATTEMPT.json", "FAILURE.json", "LAUNCH_ATTEMPT.json"]
        or launch_failure.get("failure_reason")
        != "SYSTEMD_RUN_NONZERO+SYSTEMD_RUN_STDERR+INNER_NOT_RECEIPT"
        or launch_failure.get("returncode") != 1
        or launch_failure.get("timed_out") is not False
        or launch_failure.get("source_unit_absent") is not True
        or launch_failure.get("source_path_absent") is not True
        or launch_failure.get("target_absent") is not True
        or launch_failure.get("target_path_absent") is not True
        or launch_failure.get("unit_absent") is not True
        or launch_failure.get("target_transient_instance_implicit_absence")
        is not True
        or launch_failure.get("requested_manager_stop_identity_binding")
        != MANAGER_STOP_NOT_DISPATCHED
        or launch_failure.get("scientific_occurrence_started") is not False
        or launch_failure.get("campaign_actual_measurement") is not False
    ):
        _fail("predecessor terminal artifact joins changed")
    return facts


def validate_predecessor_terminal_artifact_facts(
    value: Any,
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != len(
        PREDECESSOR_TERMINAL_ARTIFACT_SPECS
    ):
        _fail("predecessor terminal artifact fact cardinality changed")
    retained: list[dict[str, Any]] = []
    for row, spec in zip(value, PREDECESSOR_TERMINAL_ARTIFACT_SPECS):
        fact = _validate_self_id(
            row,
            schema=PREDECESSOR_ARTIFACT_FACT_SCHEMA,
            identity_field="predecessor_artifact_fact_id",
            domain=PREDECESSOR_ARTIFACT_FACT_DOMAIN,
        )
        expected_payload = {
            "schema": PREDECESSOR_ARTIFACT_FACT_SCHEMA,
            "name": spec["name"],
            "relative_path": spec["relative_path"],
            "git_mode": spec["git_mode"],
            "git_blob_id": spec["git_blob_id"],
            "byte_count": spec["byte_count"],
            "sha256": spec["sha256"],
            "document_schema": spec["document_schema"],
            "identity_field": spec["identity_field"],
            "document_id": spec["document_id"],
        }
        expected = _self_id_document(
            PREDECESSOR_ARTIFACT_FACT_DOMAIN,
            "predecessor_artifact_fact_id",
            expected_payload,
        )
        if fact != expected:
            _fail(f"predecessor {spec['name']} fact changed")
        retained.append(fact)
    return retained


def validate_live_predecessor_terminal_artifacts(
    repository_root: Path, expected: Any
) -> None:
    retained = validate_predecessor_terminal_artifact_facts(expected)
    if observe_predecessor_terminal_artifact_facts(repository_root) != retained:
        _fail("live predecessor terminal artifact closure changed")


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

    @classmethod
    def _reap_after_supervision_failure(
        cls,
        process: subprocess.Popen[bytes],
        *,
        start_new_session: bool,
        streams: Sequence[Any],
    ) -> None:
        """Contain, reap, and close a child after any supervision failure."""

        wait_error: BaseException | None = None
        reaped = False
        try:
            cls._signal_process(process, signal.SIGTERM, start_new_session)
        except BaseException as error:
            wait_error = error
        try:
            process.wait(timeout=OUTER_TERMINATION_GRACE_SECONDS)
            reaped = True
        except subprocess.TimeoutExpired:
            try:
                cls._signal_process(process, signal.SIGKILL, start_new_session)
            except BaseException as error:
                if wait_error is None:
                    wait_error = error
            try:
                process.wait(timeout=OUTER_TERMINATION_GRACE_SECONDS)
                reaped = True
            except BaseException as error:
                if wait_error is None:
                    wait_error = error
        except BaseException as error:
            if wait_error is None:
                wait_error = error
            try:
                cls._signal_process(process, signal.SIGKILL, start_new_session)
                process.wait(timeout=OUTER_TERMINATION_GRACE_SECONDS)
                reaped = True
            except BaseException as cleanup_error:
                if wait_error is None:
                    wait_error = cleanup_error
        finally:
            # A new-session child may have descendants retaining the pipe
            # writers after the leader exits on TERM.  Kill the still-unique
            # process group before dropping our read ends.
            if start_new_session:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except BaseException as error:
                    if wait_error is None:
                        wait_error = error
            for stream in streams:
                if stream is None:
                    continue
                try:
                    stream.close()
                except BaseException as error:
                    if wait_error is None:
                        wait_error = error
        if not reaped:
            raise AuthorityError(
                "bounded subprocess supervision failure left an unreaped child"
            ) from wait_error
        if wait_error is not None:
            raise AuthorityError(
                "bounded subprocess containment or close was uncertain"
            ) from wait_error

    def _supervise_process(
        self,
        process: subprocess.Popen[bytes],
        *,
        command: tuple[str, ...],
        poller: Any,
        descriptors: dict[int, tuple[Any, bytearray, int]],
        stdout_buffer: bytearray,
        stderr_buffer: bytearray,
        timeout_seconds: int,
        start_new_session: bool,
    ) -> BoundedProcessResult:
        """Drain and reap one already-born child; callers contain all faults."""

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
                if (
                    event & (select.POLLHUP | select.POLLERR)
                    and descriptor in descriptors
                ):
                    # A final zero-length read on the next iteration closes it.
                    continue
        try:
            returncode = process.wait(timeout=0)
        except subprocess.TimeoutExpired as error:
            raise AuthorityError(
                "bounded subprocess exit status unavailable"
            ) from error
        return BoundedProcessResult(
            command,
            returncode,
            bytes(stdout_buffer),
            bytes(stderr_buffer),
            timed_out,
            output_limit,
        )

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
        streams = (process.stdout, process.stderr)
        poller: select.poll | None = None
        descriptors: dict[int, tuple[Any, bytearray, int]] = {}
        try:
            if process.stdout is None or process.stderr is None:
                raise RuntimeError("bounded subprocess pipe construction changed")
            stdout_buffer = bytearray()
            stderr_buffer = bytearray()
            descriptors = {
                process.stdout.fileno(): (
                    process.stdout, stdout_buffer, stdout_cap
                ),
                process.stderr.fileno(): (
                    process.stderr, stderr_buffer, stderr_cap
                ),
            }
            poller = select.poll()
            for descriptor in descriptors:
                os.set_blocking(descriptor, False)
                poller.register(
                    descriptor, select.POLLIN | select.POLLHUP | select.POLLERR
                )
        except BaseException as setup_error:
            if poller is not None:
                for descriptor in descriptors:
                    try:
                        poller.unregister(descriptor)
                    except BaseException:
                        pass
            try:
                self._reap_after_supervision_failure(
                    process,
                    start_new_session=start_new_session,
                    streams=streams,
                )
            except BaseException as cleanup_error:
                raise AuthorityError(
                    "bounded subprocess setup failure cleanup failed"
                ) from cleanup_error
            raise AuthorityError("bounded subprocess setup failed") from setup_error
        assert poller is not None
        try:
            return self._supervise_process(
                process,
                command=command,
                poller=poller,
                descriptors=descriptors,
                stdout_buffer=stdout_buffer,
                stderr_buffer=stderr_buffer,
                timeout_seconds=timeout_seconds,
                start_new_session=start_new_session,
            )
        except BaseException as supervision_error:
            for descriptor in tuple(descriptors):
                try:
                    poller.unregister(descriptor)
                except BaseException:
                    pass
            try:
                self._reap_after_supervision_failure(
                    process,
                    start_new_session=start_new_session,
                    streams=streams,
                )
            except BaseException as cleanup_error:
                raise AuthorityError(
                    "bounded subprocess supervision failure cleanup failed"
                ) from cleanup_error
            raise AuthorityError(
                "bounded subprocess supervision failed"
            ) from supervision_error


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


def _observe_outer_parent_absence(
    authority: Mapping[str, Any], *, phase: str
) -> dict[str, Any]:
    """Bind final named-path absence to the exact authoritative app.slice."""

    host = authority["host_parent_fact"]
    app_path = str(host["app_slice_path"])
    descriptor = os.open(
        app_path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        opened = os.fstat(descriptor)
        named = os.stat(app_path, follow_symlinks=False)
        source_errno: int | None = None
        try:
            os.stat(
                SERVICE_UNIT_NAME,
                dir_fd=descriptor,
                follow_symlinks=False,
            )
        except OSError as error:
            source_errno = error.errno
        target_observation = _observe_parent_named_path(
            descriptor, TARGET_CGROUP_NAME
        )
        observed_snapshot = observe_host_parent_property_snapshot(
            descriptor, phase=phase, app_slice_path=app_path
        )
        expected_snapshot = validate_host_parent_fact(host)[
            "property_snapshot"
        ]
        mismatch_rows = _property_mismatch_rows(
            expected_snapshot["parsed_properties"],
            observed_snapshot["parsed_properties"],
        )
        cause = (
            None
            if not mismatch_rows
            else OSError(
                errno.ESTALE,
                "host app.slice property mismatch: "
                + ",".join(row["field"] for row in mismatch_rows),
            )
        )
        host_diagnostic = build_host_parent_conformance_diagnostic(
            phase=phase,
            expected_snapshot=expected_snapshot,
            observed_snapshot=observed_snapshot,
            cause=cause,
        )
        if cause is not None:
            raise HostParentConformanceError(host_diagnostic) from cause
        return {
            "app_slice_path": app_path,
            "app_slice_named_device": named.st_dev,
            "app_slice_named_inode": named.st_ino,
            "app_slice_opened_device": opened.st_dev,
            "app_slice_opened_inode": opened.st_ino,
            "app_slice_mode": stat.S_IMODE(opened.st_mode),
            "app_slice_owner_uid": opened.st_uid,
            "app_slice_owner_gid": opened.st_gid,
            "app_slice_fstatfs_type": _fstatfs_type_fd(descriptor),
            "source_stat_errno": source_errno,
            "target_parent_observation": target_observation,
            "host_parent_conformance_diagnostic": host_diagnostic,
        }
    finally:
        os.close(descriptor)


class SystemdCgroupAbsenceObserver:
    """Prove source absence plus target implicit state and named detach."""

    def __init__(self, process_adapter: SubprocessAdapter | None = None) -> None:
        self.process_adapter = (
            DEFAULT_SUBPROCESS_ADAPTER
            if process_adapter is None
            else process_adapter
        )
        self.observation_count = 0

    def observe_absence(
        self, authority: Mapping[str, Any], *, deadline_ns: int
    ) -> Mapping[str, Any]:
        authority = validate_external_root_document(authority)
        self.observation_count += 1
        if self.observation_count not in {1, 2}:
            _fail("outer host-parent observation count exceeded pre/post phases")
        observation_phase = (
            "PRELAUNCH" if self.observation_count == 1 else "POSTLAUNCH"
        )
        _require_before_deadline(deadline_ns, "outer absence observation")
        systemctl_argv = _systemctl_absence_argv()
        target_manager_show_argv = tuple(
            build_target_lifecycle_contract(os.geteuid())[
                "absence_show_argv"
            ]
        )
        transient_fragment_path = build_target_lifecycle_contract(
            os.geteuid()
        )["transient_fragment_path"]
        source_path = _source_absence_path(authority)
        target_path = _target_absence_path(authority)
        polls = 0
        last_source_unit_absent = False
        last_source_path_absent = False
        last_target_path_absent = False
        last_target_manager_implicit_absence = False
        last_transient_fragment_absent = False
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
            units_absent = result.stdout == b""
            last_source_unit_absent = units_absent
            show_result = self.process_adapter.run(
                target_manager_show_argv,
                timeout_seconds=_remaining_timeout_seconds(
                    deadline_ns, cap=TARGET_MANAGER_CALL_TIMEOUT_SECONDS
                ),
                stdout_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
                stderr_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
                env=authority["systemd_invocation_contract"][
                    "outer_launch_environment"
                ],
            )
            if (
                show_result.argv != target_manager_show_argv
                or show_result.returncode != 0
                or show_result.timed_out
                or show_result.output_limit_exceeded
                or show_result.stderr
            ):
                raise AuthorityError(
                    "bounded target manager implicit-absence show failed"
                )
            target_manager_properties = _parse_target_manager_properties(
                show_result.stdout,
                expected_keys=TARGET_MANAGER_ABSENCE_PROPERTY_KEYS,
            )
            last_target_manager_implicit_absence = (
                _target_manager_implicit_absence(target_manager_properties)
            )
            parent_observation = _observe_outer_parent_absence(
                authority, phase=observation_phase
            )
            target_parent = parent_observation[
                "target_parent_observation"
            ]
            last_source_path_absent = (
                parent_observation["source_stat_errno"] == errno.ENOENT
                and SERVICE_UNIT_NAME
                not in target_parent["parent_inventory"]
            )
            last_target_path_absent = target_parent["name_absent"] is True
            fragment_observation = _observe_fragment_absence(
                transient_fragment_path
            )
            last_transient_fragment_absent = (
                fragment_observation["absent"] is True
            )
            if (
                last_source_unit_absent
                and last_source_path_absent
                and last_target_path_absent
                and last_target_manager_implicit_absence
                and last_transient_fragment_absent
            ):
                return {
                    "unit_absent": True,
                    "target_absent": True,
                    "source_unit_absent": True,
                    "source_path_absent": True,
                    "target_transient_instance_implicit_absence": True,
                    "target_path_absent": True,
                    "target_manager_implicit_absence": True,
                    "target_manager_properties": target_manager_properties,
                    "target_manager_show_argv": list(
                        target_manager_show_argv
                    ),
                    "target_manager_show_result": (
                        _bounded_process_result_fact(show_result)
                    ),
                    "transient_fragment_path": transient_fragment_path,
                    "transient_fragment_absent": True,
                    "transient_fragment_stat_errno": errno.ENOENT,
                    "parent_absence_observation": parent_observation,
                    "host_parent_conformance_diagnostic": (
                        parent_observation[
                            "host_parent_conformance_diagnostic"
                        ]
                    ),
                    "named_path_detached_and_manager_implicit_absence": True,
                    "posix_inode_unlink_claimed": False,
                    "poll_count": polls,
                    "systemctl_argv": list(systemctl_argv),
                    "systemctl_result": _bounded_process_result_fact(result),
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
            "target_transient_instance_implicit_absence="
            f"{last_target_manager_implicit_absence}; "
            f"source_path_absent={last_source_path_absent}; "
            f"target_path_absent={last_target_path_absent}; "
            "target_manager_implicit_absence="
            f"{last_target_manager_implicit_absence}; "
            "transient_fragment_absent="
            f"{last_transient_fragment_absent}",
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


def _grouped_current_c_probe_tree_rows(
    repository_root: Path,
    commit_id: str,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes],
) -> dict[str, tuple[str, str]]:
    expected_paths = {
        PROBE_SOURCE_RELATIVE_PATH,
        *(spec["relative_path"] for spec in PREDECESSOR_TERMINAL_ARTIFACT_SPECS),
    }
    return _grouped_tree_rows(
        repository_root,
        commit_id,
        expected_paths,
        git_stdout=git_stdout,
        label="current C_probe",
    )


def _grouped_predecessor_frozen_tree_rows(
    repository_root: Path,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes],
) -> dict[str, tuple[str, str]]:
    # The predecessor commit/tree freezes the predecessor source.  Its
    # terminal artifacts were produced later and are frozen as blobs in the
    # current C_probe tree, so asking the earlier tree for those paths would
    # make the successor impossible to prepare.
    expected_paths = {PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH}
    return _grouped_tree_rows(
        repository_root,
        PREDECESSOR_FROZEN_SOURCE_COMMIT_ID,
        expected_paths,
        git_stdout=git_stdout,
        label="frozen predecessor",
    )


def _grouped_tree_rows(
    repository_root: Path,
    commit_id: str,
    expected_paths: set[str],
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes],
    label: str,
) -> dict[str, tuple[str, str]]:
    raw = git_stdout(
        repository_root,
        ("ls-tree", commit_id, "--", *sorted(expected_paths)),
    )
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise AuthorityError(f"grouped {label} tree rows are not UTF-8") from error
    if not text.endswith("\n") or "\x00" in text:
        _fail(f"grouped {label} tree framing changed")
    rows: dict[str, tuple[str, str]] = {}
    for line in text[:-1].split("\n"):
        try:
            metadata, relative_path = line.split("\t", 1)
            git_mode, object_type, blob_id = metadata.split(" ", 2)
        except ValueError as error:
            raise AuthorityError(f"grouped {label} tree row changed") from error
        if (
            relative_path in rows
            or relative_path not in expected_paths
            or git_mode != "100644"
            or object_type != "blob"
            or not _is_lower_hex(blob_id, 40)
        ):
            _fail(f"grouped {label} tree identity changed")
        rows[relative_path] = (git_mode, blob_id)
    if set(rows) != expected_paths:
        _fail(f"grouped {label} tree omitted a required source/artifact path")
    return rows


def _collect_predecessor_frozen_grouped_closure(
    repository_root: Path,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes],
) -> dict[str, Any]:
    rows = _grouped_predecessor_frozen_tree_rows(
        repository_root, git_stdout=git_stdout
    )
    source_mode, source_blob_id = rows[
        PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH
    ]
    if (
        source_mode != "100644"
        or source_blob_id != PREDECESSOR_PROBE_SOURCE_GIT_BLOB_ID
    ):
        _fail("frozen predecessor probe source tree identity changed")
    source_blob = git_stdout(
        repository_root, ("cat-file", "blob", source_blob_id)
    )
    source_fact = validate_source_fact(
        {
            "schema": SOURCE_FACT_SCHEMA,
            "relative_path": PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH,
            "git_mode": source_mode,
            "git_blob_id": source_blob_id,
            "byte_count": len(source_blob),
            "sha256": hashlib.sha256(source_blob).hexdigest(),
        },
        expected_relative_path=PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH,
    )
    if (
        source_fact["byte_count"] != PREDECESSOR_PROBE_SOURCE_BYTE_COUNT
        or source_fact["sha256"] != PREDECESSOR_PROBE_SOURCE_SHA256
        or _read_regular_exact(
            repository_root / PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH,
            byte_cap=MAX_GIT_STDOUT_BYTES,
            mode=None,
        )
        != source_blob
    ):
        _fail("frozen predecessor probe source blob/live closure changed")
    return source_fact


def _collect_current_c_probe_grouped_closure(
    repository_root: Path,
    commit_id: str,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = _grouped_current_c_probe_tree_rows(
        repository_root, commit_id, git_stdout=git_stdout
    )
    probe_mode, probe_blob_id = rows[PROBE_SOURCE_RELATIVE_PATH]
    probe_blob = git_stdout(
        repository_root, ("cat-file", "blob", probe_blob_id)
    )
    if not probe_blob or len(probe_blob) > MAX_GIT_STDOUT_BYTES:
        _fail("current C_probe source blob exceeded its bound")
    probe_fact = validate_source_fact(
        {
            "schema": SOURCE_FACT_SCHEMA,
            "relative_path": PROBE_SOURCE_RELATIVE_PATH,
            "git_mode": probe_mode,
            "git_blob_id": probe_blob_id,
            "byte_count": len(probe_blob),
            "sha256": hashlib.sha256(probe_blob).hexdigest(),
        },
        expected_relative_path=PROBE_SOURCE_RELATIVE_PATH,
    )
    live_probe = _read_regular_exact(
        repository_root / PROBE_SOURCE_RELATIVE_PATH,
        byte_cap=MAX_GIT_STDOUT_BYTES,
        mode=None,
    )
    if live_probe != probe_blob or _git_blob_id(live_probe) != probe_blob_id:
        _fail("live current probe differs from grouped C_probe tree/blob")
    artifact_facts = observe_predecessor_terminal_artifact_facts(repository_root)
    for fact in artifact_facts:
        if rows[fact["relative_path"]] != (
            fact["git_mode"],
            fact["git_blob_id"],
        ):
            _fail("predecessor artifact differs from grouped C_probe tree")
    return probe_fact, artifact_facts


def collect_post_c_probe_authority(
    repository_root: Path,
    *,
    git_stdout: Callable[[Path, Sequence[str]], bytes] | None = None,
    host_observer: Callable[[], Mapping[str, Any]] | None = None,
    require_running_source: bool = True,
) -> dict[str, Any]:
    """Collect a source-pinned authority from an exact tracked-clean HEAD.

    Untracked paths are intentionally outside this authority.  The successor
    itself and its frozen predecessor source are nevertheless exact tracked
    blobs in the two explicitly bound commits.
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
    probe_fact, predecessor_artifact_facts = (
        _collect_current_c_probe_grouped_closure(
            repository_root,
            commit_id,
            git_stdout=observe_git,
        )
    )
    predecessor_fact = _collect_predecessor_frozen_grouped_closure(
        repository_root,
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
        predecessor_probe_source_fact=predecessor_fact,
        predecessor_terminal_artifact_facts=predecessor_artifact_facts,
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
    authority = validate_external_root_document(authority)
    policy = validate_same_uid_manager_concurrency_policy(
        authority["same_uid_manager_concurrency_policy"]
    )
    if (
        authority["same_uid_manager_concurrency_policy_id"]
        != policy["same_uid_manager_concurrency_policy_id"]
    ):
        _fail("PREPARE_RECEIPT authority policy join changed")
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
    policy = validate_same_uid_manager_concurrency_policy(
        authority["same_uid_manager_concurrency_policy"]
    )
    lifecycle = authority["systemd_invocation_contract"][
        "target_lifecycle_contract"
    ]
    if (
        authority["same_uid_manager_concurrency_policy_id"]
        != policy["same_uid_manager_concurrency_policy_id"]
        or lifecycle["same_uid_manager_concurrency_policy_id"]
        != policy["same_uid_manager_concurrency_policy_id"]
        or lifecycle["same_uid_manager_concurrency_policy_status"]
        != policy["status"]
        or lifecycle["unconditional_same_uid_replacement_safety_claimed"]
        is not False
        or lifecycle["manager_stop_identity_binding_contract"]
        != MANAGER_STOP_IDENTITY_BINDING
    ):
        _fail("prepared authority same-UID exclusion join changed")
    validate_live_toolchain_facts(
        authority["host_parent_fact"]["toolchain_facts"]
    )
    invocation = authority["systemd_invocation_contract"]
    repository_root = _canonical_repository_root(
        Path(invocation["repository_root"])
    )
    validate_live_predecessor_terminal_artifacts(
        repository_root,
        authority["predecessor_terminal_artifact_facts"],
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
    predecessor_commit = _decode_git_hex(
        observe_git(
            repository_root,
            (
                "rev-parse",
                "--verify",
                f"{PREDECESSOR_FROZEN_SOURCE_COMMIT_ID}^{{commit}}",
            ),
        ),
        length=40,
        label="resolved predecessor probe commit",
    )
    predecessor_tree = _decode_git_hex(
        observe_git(
            repository_root,
            (
                "rev-parse",
                "--verify",
                f"{PREDECESSOR_FROZEN_SOURCE_COMMIT_ID}^{{tree}}",
            ),
        ),
        length=40,
        label="resolved predecessor probe tree",
    )
    if (
        predecessor_commit != PREDECESSOR_FROZEN_SOURCE_COMMIT_ID
        or predecessor_tree != PREDECESSOR_FROZEN_SOURCE_TREE_ID
    ):
        _fail("predecessor probe commit/tree closure changed")
    grouped_rows = _grouped_current_c_probe_tree_rows(
        repository_root, commit_id, git_stdout=observe_git
    )
    probe_fact = authority["probe_source_fact"]
    if grouped_rows[PROBE_SOURCE_RELATIVE_PATH] != (
        probe_fact["git_mode"],
        probe_fact["git_blob_id"],
    ):
        _fail("current probe fact differs from grouped C_probe tree")
    probe_blob = observe_git(
        repository_root, ("cat-file", "blob", probe_fact["git_blob_id"])
    )
    if (
        len(probe_blob) != probe_fact["byte_count"]
        or hashlib.sha256(probe_blob).hexdigest() != probe_fact["sha256"]
        or _git_blob_id(probe_blob) != probe_fact["git_blob_id"]
        or _read_regular_exact(
            repository_root / PROBE_SOURCE_RELATIVE_PATH,
            byte_cap=MAX_GIT_STDOUT_BYTES,
            mode=None,
        )
        != probe_blob
    ):
        _fail("current probe grouped tree/blob/live closure changed")
    artifact_facts = validate_predecessor_terminal_artifact_facts(
        authority["predecessor_terminal_artifact_facts"]
    )
    for fact in artifact_facts:
        if grouped_rows[fact["relative_path"]] != (
            fact["git_mode"],
            fact["git_blob_id"],
        ):
            _fail("predecessor artifact differs from grouped C_probe tree")
    if observe_predecessor_terminal_artifact_facts(repository_root) != artifact_facts:
        _fail("predecessor artifact grouped tree/live closure changed")
    predecessor_fact = authority["predecessor_probe_source_fact"]
    frozen_rows = _grouped_predecessor_frozen_tree_rows(
        repository_root, git_stdout=observe_git
    )
    if frozen_rows[predecessor_fact["relative_path"]] != (
        predecessor_fact["git_mode"],
        predecessor_fact["git_blob_id"],
    ):
        _fail("predecessor probe tree source row changed")
    predecessor_blob = observe_git(
        repository_root,
        ("cat-file", "blob", predecessor_fact["git_blob_id"]),
    )
    if (
        len(predecessor_blob) != predecessor_fact["byte_count"]
        or hashlib.sha256(predecessor_blob).hexdigest()
        != predecessor_fact["sha256"]
        or _git_blob_id(predecessor_blob) != predecessor_fact["git_blob_id"]
        or _read_regular_exact(
            repository_root / predecessor_fact["relative_path"],
            byte_cap=MAX_GIT_STDOUT_BYTES,
            mode=None,
        )
        != predecessor_blob
    ):
        _fail("predecessor probe blob/live closure changed")


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
        validate_live_predecessor_terminal_artifacts(
            repository_root,
            authority["predecessor_terminal_artifact_facts"],
        )
        _validate_live_source_fact(repository_root, authority["probe_source_fact"])
        _validate_live_source_fact(
            repository_root, authority["predecessor_probe_source_fact"]
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
    validate_live_predecessor_terminal_artifacts(
        repository_root,
        authority["predecessor_terminal_artifact_facts"],
    )
    _validate_live_source_fact(repository_root, authority["probe_source_fact"])
    _validate_live_source_fact(
        repository_root, authority["predecessor_probe_source_fact"]
    )
    if require_running_source and Path(__file__).resolve() != (
        repository_root / PROBE_SOURCE_RELATIVE_PATH
    ).resolve():
        _fail("launch is not running the exact C_probe source path")
    # Do not sample or compare the live host parent here.  This loader runs
    # before the durable LAUNCH_ATTEMPT publication, so a dynamic host drift
    # observed here would escape without the one-shot outer terminal journal.
    # The PRELAUNCH observation in run_outer_launch_once performs the complete
    # property and OFD-identity join after LAUNCH_ATTEMPT exists.  Retain the
    # injectable argument for callers/tests, but deliberately never invoke it
    # at this pre-attempt static-authority boundary.
    if host_observer is not None and not callable(host_observer):
        _fail("outer host observer is not callable")
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
        **_same_uid_manager_concurrency_policy_join(),
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
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


def validate_outer_launch_attempt_document(
    document: Any,
    authority: Mapping[str, Any],
    external_root_raw: bytes,
) -> dict[str, Any]:
    if (
        type(document) is not dict
        or set(document) != OUTER_LAUNCH_ATTEMPT_FIELDS
    ):
        _fail("outer LAUNCH_ATTEMPT fields changed")
    retained = _validate_self_id(
        document,
        schema=OUTER_LAUNCH_ATTEMPT_SCHEMA,
        identity_field="outer_launch_attempt_id",
        domain=OUTER_LAUNCH_ATTEMPT_DOMAIN,
    )
    expected = build_outer_launch_attempt_document(authority, external_root_raw)
    if retained != expected:
        _fail("outer LAUNCH_ATTEMPT/root/policy joins changed")
    return retained


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
        **_same_uid_manager_concurrency_policy_join(),
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
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
    retained = validate_outer_launch_attempt_document(
        loads_canonical_json(store.read_exact(OUTER_LAUNCH_ATTEMPT_NAME)),
        authority,
        external_root_raw,
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
    value: Any,
    authority: Mapping[str, Any],
    *,
    expected_phase: str | None = None,
) -> dict[str, Any]:
    expected_argv = list(_systemctl_absence_argv())
    expected_source = str(_source_absence_path(authority))
    expected_target = str(_target_absence_path(authority))
    contract = build_target_lifecycle_contract(os.geteuid())
    expected_show_argv = contract["absence_show_argv"]
    expected_fragment_path = contract["transient_fragment_path"]
    if (
        type(value) is not dict
        or set(value) != ABSENCE_FACT_FIELDS
        or value["unit_absent"] is not True
        or value["target_absent"] is not True
        or value["source_unit_absent"] is not True
        or value["source_path_absent"] is not True
        or value["target_transient_instance_implicit_absence"] is not True
        or value["target_path_absent"] is not True
        or value["target_manager_implicit_absence"] is not True
        or type(value["target_manager_properties"]) is not dict
        or not _target_manager_implicit_absence(
            value["target_manager_properties"]
        )
        or value["target_manager_show_argv"] != expected_show_argv
        or value["transient_fragment_path"] != expected_fragment_path
        or value["transient_fragment_absent"] is not True
        or value["transient_fragment_stat_errno"] != errno.ENOENT
        or value[
            "named_path_detached_and_manager_implicit_absence"
        ]
        is not True
        or value["posix_inode_unlink_claimed"] is not False
        or type(value["poll_count"]) is not int
        or not 1 <= value["poll_count"] <= MAX_OUTER_OBSERVATION_POLLS
        or value["systemctl_argv"] != expected_argv
        or value["source_path"] != expected_source
        or value["target_path"] != expected_target
    ):
        _fail("outer success absence evidence changed")
    systemctl_result = _validate_bounded_process_result_fact(
        value["systemctl_result"]
    )
    if (
        systemctl_result is None
        or systemctl_result["argv"] != expected_argv
        or systemctl_result["returncode"] != 0
        or systemctl_result["timed_out"] is not False
        or systemctl_result["output_limit_exceeded"] is not False
        or _validate_output_fact(
            systemctl_result["stdout"], byte_cap=16 * 1024
        )
        != b""
        or _validate_output_fact(
            systemctl_result["stderr"], byte_cap=16 * 1024
        )
        != b""
    ):
        _fail("outer list-units absence result changed")
    show_result = _validate_bounded_process_result_fact(
        value["target_manager_show_result"]
    )
    if (
        show_result is None
        or not _exact_target_manager_result(
            show_result,
            argv_key="absence_show_argv",
            require_empty_stdout=False,
        )
    ):
        _fail("outer target manager show result changed")
    show_raw = _validate_output_fact(
        show_result["stdout"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
    )
    if _parse_target_manager_properties(
        show_raw, expected_keys=TARGET_MANAGER_ABSENCE_PROPERTY_KEYS
    ) != value["target_manager_properties"]:
        _fail("outer target manager properties lost raw-byte replay")
    host_diagnostic = validate_host_parent_conformance_diagnostic(
        value["host_parent_conformance_diagnostic"]
    )
    if (
        host_diagnostic["phase"] not in {"PRELAUNCH", "POSTLAUNCH"}
        or expected_phase is not None
        and host_diagnostic["phase"] != expected_phase
        or host_diagnostic["conformant"] is not True
    ):
        _fail("outer host-parent conformance phase or result changed")
    parent = value["parent_absence_observation"]
    host = authority["host_parent_fact"]
    if type(parent) is not dict or set(parent) != {
        "app_slice_path",
        "app_slice_named_device",
        "app_slice_named_inode",
        "app_slice_opened_device",
        "app_slice_opened_inode",
        "app_slice_mode",
        "app_slice_owner_uid",
        "app_slice_owner_gid",
        "app_slice_fstatfs_type",
        "source_stat_errno",
        "target_parent_observation",
        "host_parent_conformance_diagnostic",
    }:
        _fail("outer parent absence fields changed")
    target_parent = _validate_parent_named_path_observation(
        parent["target_parent_observation"]
    )
    if (
        parent["app_slice_path"] != host["app_slice_path"]
        or parent["app_slice_named_device"] != host["app_slice_device"]
        or parent["app_slice_named_inode"] != host["app_slice_inode"]
        or parent["app_slice_opened_device"] != host["app_slice_device"]
        or parent["app_slice_opened_inode"] != host["app_slice_inode"]
        or parent["app_slice_mode"] != host["mode"]
        or parent["app_slice_owner_uid"] != host["owner_uid"]
        or parent["app_slice_owner_gid"] != host["owner_gid"]
        or parent["app_slice_fstatfs_type"] != CGROUP2_SUPER_MAGIC
        or parent["source_stat_errno"] != errno.ENOENT
        or parent["host_parent_conformance_diagnostic"] != host_diagnostic
        or target_parent is None
        or SERVICE_UNIT_NAME in target_parent["parent_inventory"]
        or target_parent["name_absent"] is not True
    ):
        _fail("outer parent absence lost app.slice/path identity joins")
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
    else:
        if (
            type(retained["error_type"]) is not str
            or not retained["error_type"]
            or type(retained["message"]) is not str
        ):
            _fail("failed substage lacks typed error fields")
        typed_target_create_failure = (
            retained["substage"] == "TARGET_CREATE"
            and retained["error_type"] == "TargetCreationError"
        )
        row_error = {
            "error_type": retained["error_type"],
            "message": retained["message"],
            "errno": retained["errno"],
            "errno_name": retained["errno_name"],
        }
        if typed_target_create_failure:
            diagnostic = validate_target_create_diagnostic(
                retained["detail"]
            )
            if diagnostic["target_creation_error"] != row_error:
                _fail("TARGET_CREATE row lost its exact error join")
        elif (
            retained["substage"]
            in {"TARGET_REMOVE", "CLEANUP_TARGET_REMOVE"}
            and retained["error_type"] == "TargetRemovalError"
        ):
            diagnostic = validate_target_cleanup_diagnostic(
                retained["detail"]
            )
            if diagnostic["target_removal_error"] != row_error:
                _fail("TARGET_REMOVE row lost its exact error join")
        elif retained["detail"].get("schema") == (
            HOST_PARENT_CONFORMANCE_DIAGNOSTIC_SCHEMA
        ):
            diagnostic = validate_host_parent_conformance_diagnostic(
                retained["detail"]
            )
            if (
                retained["substage"]
                != "SERVICE_PLACEMENT_AND_NCA_PERMISSION"
                or diagnostic["conformant"] is not False
                or _error_fact(HostParentConformanceError(diagnostic))
                != row_error
            ):
                _fail("host-parent conformance row lost its wrapper join")
        elif retained["detail"].get("schema") == (
            HOST_PARENT_OBSERVATION_FAILURE_SCHEMA
        ):
            diagnostic = validate_host_parent_observation_failure(
                retained["detail"]
            )
            if (
                retained["substage"]
                != "SERVICE_PLACEMENT_AND_NCA_PERMISSION"
                or _error_fact(HostParentObservationError(diagnostic))
                != row_error
            ):
                _fail("host-parent observation row lost its wrapper join")
        elif retained["detail"].get("schema") == (
            HOST_PARENT_IDENTITY_CONFORMANCE_SCHEMA
        ):
            diagnostic = validate_host_parent_identity_conformance_diagnostic(
                retained["detail"]
            )
            if (
                retained["substage"]
                != "SERVICE_PLACEMENT_AND_NCA_PERMISSION"
                or diagnostic["conformant"] is not False
                or _error_fact(
                    HostParentIdentityConformanceError(diagnostic)
                )
                != row_error
            ):
                _fail("host-parent identity row lost its wrapper join")
        elif retained["detail"].get("schema") == (
            SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_SCHEMA
        ):
            diagnostic = validate_source_unit_conformance_diagnostic(
                retained["detail"]
            )
            if (
                retained["substage"]
                != "SERVICE_PLACEMENT_AND_NCA_PERMISSION"
                or diagnostic["conformant"] is not False
                or _error_fact(SourceUnitConformanceError(diagnostic))
                != row_error
            ):
                _fail("source-unit conformance row lost its wrapper join")
        else:
            ordinary = validate_ordinary_failure_diagnostic(
                retained["detail"]
            )
            if (
                ordinary["substage"] != retained["substage"]
                or ordinary["cause"] != row_error
            ):
                _fail("ordinary failure diagnostic lost its exact row join")
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
    expected_target_path: str,
    expected_target_membership: str,
    expected_create_diagnostic: Mapping[str, Any] | None,
) -> dict[str, Any]:
    retained = _require_exact_detail(
        value, TARGET_REMOVAL_DETAIL_FIELDS, label="target manager removal"
    )
    parent_observation = _validate_parent_named_path_observation(
        retained["parent_named_path_observation"]
    )
    full_conformance = retained["full_target_path_ofd_conformance"]
    if type(full_conformance) is not bool:
        _fail("target manager removal conformance scope changed")
    if full_conformance:
        identity_valid = (
            retained["ownership_scope"] == "UNIT_PATH_OFD"
            and type(retained["owned_device"]) is int
            and retained["owned_device"] >= 0
            and type(retained["owned_inode"]) is int
            and retained["owned_inode"] > 0
            and (
                expected_device is None
                or retained["owned_device"] == expected_device
            )
            and (
                expected_inode is None
                or retained["owned_inode"] == expected_inode
            )
            and retained["named_path_detached_and_manager_implicit_absence"] is True
            and type(retained["retained_ofd_detach_fact"]) is dict
        )
    else:
        identity_valid = (
            retained["ownership_scope"] == "UNIT_ONLY"
            and retained["owned_device"] is None
            and retained["owned_inode"] is None
            and expected_device is None
            and expected_inode is None
            and retained["named_path_detached_and_manager_implicit_absence"] is True
            and retained["retained_ofd_detach_fact"] is None
        )
    if (
        retained["removed"] is not True
        or retained["already_absent"] is not False
        or retained["manager_unit_ownership_acquired"] is not True
        or not identity_valid
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
        or not _target_manager_implicit_absence(retained["manager_final_properties"])
        or type(retained["manager_poll_count"]) is not int
        or not 1 <= retained["manager_poll_count"] <= TARGET_MANAGER_MAX_POLLS
        or type(retained["probe_path_deletion_calls"]) is not int
        or retained["probe_path_deletion_calls"] != 0
        or retained["manager_implicit_absence_proven"] is not True
        or retained["target_path_absent"] is not True
        or retained["transient_fragment_absent"] is not True
        or retained["transient_fragment_path"]
        != target_contract["transient_fragment_path"]
        or retained["transient_fragment_stat_errno"] != errno.ENOENT
        or parent_observation is None
        or parent_observation["name_absent"] is not True
        or retained["replacement_detected"] is not False
        or retained["posix_inode_unlink_claimed"] is not False
    ):
        _fail("target manager removal evidence changed")
    diagnostic = validate_target_cleanup_diagnostic(
        retained["cleanup_diagnostic"]
    )
    if (
        diagnostic["target_path"] != expected_target_path
        or diagnostic["target_membership"] != expected_target_membership
        or (
            expected_create_diagnostic is not None
            and diagnostic["prior_target_create_diagnostic"]
            != expected_create_diagnostic
        )
        or diagnostic["ownership_scope"] != retained["ownership_scope"]
        or diagnostic["target_device"] != retained["owned_device"]
        or diagnostic["target_inode"] != retained["owned_inode"]
        or diagnostic["manager_poll_count"] != retained["manager_poll_count"]
        or diagnostic["last_manager_properties"]
        != retained["manager_final_properties"]
        or diagnostic["manager_implicit_absence_proven"] is not True
        or diagnostic["target_path_absent"] is not True
        or diagnostic["transient_fragment_absent"] is not True
        or diagnostic["transient_fragment_path"]
        != retained["transient_fragment_path"]
        or diagnostic["parent_named_path_observation"]
        != retained["parent_named_path_observation"]
        or diagnostic["retained_ofd_detach_fact"]
        != retained["retained_ofd_detach_fact"]
        or diagnostic["replacement_detected"] is not False
        or diagnostic["posix_inode_unlink_claimed"] is not False
        or diagnostic["named_path_detached_and_manager_implicit_absence"]
        != retained["named_path_detached_and_manager_implicit_absence"]
        or diagnostic["same_uid_manager_concurrency_policy_id"]
        != target_contract["same_uid_manager_concurrency_policy_id"]
        or diagnostic["same_uid_manager_concurrency_policy_status"]
        != target_contract["same_uid_manager_concurrency_policy_status"]
        or diagnostic["unconditional_same_uid_replacement_safety_claimed"]
        is not False
        or diagnostic["manager_stop_identity_binding_contract"]
        != target_contract["manager_stop_identity_binding_contract"]
        or diagnostic["requested_manager_stop_identity_binding"]
        != MANAGER_STOP_IDENTITY_BINDING
    ):
        _fail("target cleanup diagnostic lost its removal-detail join")
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
                    "delegation_enabled",
                    "delegated_controllers",
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
            or context["delegation_enabled"]
            is not invocation["delegation_enabled"]
            or context["delegated_controllers"]
            != invocation["delegated_controllers"]
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
            or service["delegation_enabled_from_outer_context"] is not True
            or service["delegated_controllers_from_outer_context"] != []
            or service["fixed_target_absent_before_create"] is not True
            or service["target_manager_implicit_absence_before_create"] is not True
            or type(service["target_manager_precreate_properties"]) is not dict
            or not _target_manager_implicit_absence(
                service["target_manager_precreate_properties"]
            )
            or validate_host_parent_identity_conformance_diagnostic(
                service["host_parent_identity_conformance_diagnostic"]
            )["conformant"]
            is not True
            or validate_host_parent_conformance_diagnostic(
                service["host_parent_conformance_diagnostic"]
            )["conformant"]
            is not True
            or service["host_parent_conformance_diagnostic"]["phase"]
            != "INNER_ACTIVE"
            or validate_source_unit_conformance_diagnostic(
                service["source_unit_conformance_diagnostic"]
            )["conformant"]
            is not True
            or service["source_unit_conformance_diagnostic"][
                "delegation_enabled"
            ]
            is not True
            or service["source_unit_conformance_diagnostic"][
                "delegated_controllers"
            ]
            != []
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
        identity_diagnostic = (
            validate_host_parent_identity_conformance_diagnostic(
                service["host_parent_identity_conformance_diagnostic"]
            )
        )
        host_diagnostic = validate_host_parent_conformance_diagnostic(
            service["host_parent_conformance_diagnostic"]
        )
        source_diagnostic = validate_source_unit_conformance_diagnostic(
            service["source_unit_conformance_diagnostic"]
        )
        if (
            identity_diagnostic["phase"] != "INNER_ACTIVE"
            or identity_diagnostic["expected_properties"]
            != _expected_host_parent_identity_properties(host)
            or
            host_diagnostic["expected_snapshot"] != host["property_snapshot"]
            or source_diagnostic["expected_properties"]
            != _source_expected_properties(
                uid=uid, source_membership=source_membership
            )
        ):
            _fail("service property diagnostics lost authority joins")
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
            or type(target["initial_cgroup_events"]) is not dict
            or target["initial_cgroup_events"].get("populated") != "0"
            or any(
                type(key) is not str or type(value) is not str
                for key, value in target["initial_cgroup_events"].items()
            )
            or target["transient_fragment_path"]
            != target_contract["transient_fragment_path"]
            or target["manager_create_argv"] != target_contract["create_argv"]
            or target["manager_create_environment"] != target_contract["environment"]
            or type(target["manager_create_returncode"]) is not int
            or target["manager_create_returncode"] != 0
            or type(target["manager_create_job_path"]) is not str
            or _target_manager_create_job_path(
                _validate_output_fact(
                    target["manager_create_stdout"],
                    byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
                )
            )
            != target["manager_create_job_path"]
            or _validate_output_fact(
                target["manager_create_stderr"],
                byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
            )
            != b""
            or type(target["manager_properties"]) is not dict
            or not _target_manager_active(
                target["manager_properties"],
                expected_control_group=target_membership,
            ).conformant
            or type(target["manager_poll_count"]) is not int
            or not 1 <= target["manager_poll_count"] <= TARGET_MANAGER_MAX_POLLS
            or target["manager_owned_lifecycle"] is not True
            or validate_target_create_diagnostic(
                target["manager_create_diagnostic"],
                expected_target_membership=target_membership,
            )["full_target_path_ofd_conformance"]
            is not True
            or type(target["probe_path_deletion_calls"]) is not int
            or target["probe_path_deletion_calls"] != 0
        ):
            _fail("TARGET_CREATE detail lost its target/manager join")
        diagnostic = validate_target_create_diagnostic(
            target["manager_create_diagnostic"],
            expected_target_membership=target_membership,
        )
        if (
            diagnostic["target_device"] != target["target_device"]
            or diagnostic["target_inode"] != target["target_inode"]
            or diagnostic["manager_poll_count"] != target["manager_poll_count"]
            or diagnostic["last_property_map"] != target["manager_properties"]
            or diagnostic["manager_create_result"]["argv"]
            != target["manager_create_argv"]
            or diagnostic["manager_create_job_path"]
            != target["manager_create_job_path"]
        ):
            _fail("TARGET_CREATE diagnostic lost its success-detail join")
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
            expected_target_path=target["target_path"],
            expected_target_membership=target["target_membership"],
            expected_create_diagnostic=target["manager_create_diagnostic"],
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

    host = authority["host_parent_fact"]
    expected_target_path = (
        f"{host['app_slice_path']}/{TARGET_CGROUP_NAME}"
    )
    uid = host["owner_uid"]
    expected_target_membership = (
        f"/user.slice/user-{uid}.slice/user@{uid}.service/app.slice/"
        f"{TARGET_CGROUP_NAME}"
    )

    if row["status"] == "FAILED":
        if row["substage"] != "CLEANUP_TARGET_REMOVE":
            diagnostic = validate_ordinary_failure_diagnostic(row["detail"])
            if diagnostic["substage"] != row["substage"]:
                _fail("failed cleanup diagnostic lost its substage join")
            return False
        diagnostic = validate_target_cleanup_diagnostic(row["detail"])
        if (
            diagnostic["target_path"] != expected_target_path
            or diagnostic["target_membership"]
            != expected_target_membership
        ):
            _fail("failed cleanup reidentified target path or membership")
        outer = diagnostic["target_removal_error"]
        if (
            row["error_type"] != outer["error_type"]
            or row["message"] != outer["message"]
            or row["errno"] != outer["errno"]
            or row["errno_name"] != outer["errno_name"]
        ):
            _fail("failed cleanup record lost TargetRemovalError join")
        prior = diagnostic["prior_target_create_diagnostic"]
        target_detail = details.get("TARGET_CREATE")
        target_marker = _target_postclaim_validation_marker(primary)
        if target_detail is not None:
            if prior != target_detail.get("manager_create_diagnostic"):
                _fail("failed cleanup lost successful create diagnostic join")
        elif (
            primary.get("substage") == "TARGET_CREATE"
            and primary.get("error_type") == "TargetCreationError"
        ):
            if prior != primary.get("detail"):
                _fail("failed cleanup lost unit-only create diagnostic join")
        elif target_marker is not None:
            if (
                prior["full_target_path_ofd_conformance"] is not True
                or prior["target_device"] != target_marker[0]
                or prior["target_inode"] != target_marker[1]
            ):
                _fail("failed cleanup lost post-claim device/inode join")
        else:
            _fail("failed cleanup lacks a prior typed target claim")
        return False
    name = row["substage"]
    detail = row["detail"]
    target_contract = authority["systemd_invocation_contract"][
        "target_lifecycle_contract"
    ]
    clone = details.get("CLONE3_ATOMIC_BIRTH")
    target = details.get("TARGET_CREATE")
    target_marker = _target_postclaim_validation_marker(primary)
    target_create_diagnostic = (
        validate_target_create_diagnostic(
            primary["detail"],
            expected_target_membership=details.get(
                "SERVICE_PLACEMENT_AND_NCA_PERMISSION", {}
            ).get("target_membership"),
        )
        if primary.get("substage") == "TARGET_CREATE"
        and primary.get("error_type") == "TargetCreationError"
        else None
    )
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
            unit_only_create_claim = (
                target is None
                and target_create_diagnostic is not None
                and target_create_diagnostic[
                    "manager_unit_ownership_acquired"
                ]
                is True
            )
            if target is None and not partial_create_claim and not unit_only_create_claim:
                _fail(
                    "cleanup removal lacks a typed manager-unit ownership claim"
                )
            _validate_full_target_removal_detail(
                detail,
                target_contract=target_contract,
                expected_device=(
                    target_marker[0]
                    if partial_create_claim
                    else (
                        None
                        if unit_only_create_claim
                        else target["target_device"]
                    )
                ),
                expected_inode=(
                    target_marker[1]
                    if partial_create_claim
                    else (
                        None
                        if unit_only_create_claim
                        else target["target_inode"]
                    )
                ),
                expected_target_path=expected_target_path,
                expected_target_membership=expected_target_membership,
                expected_create_diagnostic=(
                    target_create_diagnostic
                    if unit_only_create_claim
                    else (
                        None
                        if partial_create_claim
                        else target["manager_create_diagnostic"]
                    )
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
    if primary["substage"] == "SERVICE_PLACEMENT_AND_NCA_PERMISSION":
        host = validate_host_parent_fact(authority["host_parent_fact"])
        schema = primary["detail"].get("schema")
        if schema == HOST_PARENT_CONFORMANCE_DIAGNOSTIC_SCHEMA:
            diagnostic = validate_host_parent_conformance_diagnostic(
                primary["detail"]
            )
            if (
                diagnostic["phase"] != "INNER_ACTIVE"
                or diagnostic["expected_snapshot"]
                != host["property_snapshot"]
                or diagnostic["observed_snapshot"]["app_slice_path"]
                != host["app_slice_path"]
            ):
                _fail("SERVICE host conformance diagnostic lost authority join")
        elif schema == HOST_PARENT_OBSERVATION_FAILURE_SCHEMA:
            diagnostic = validate_host_parent_observation_failure(
                primary["detail"]
            )
            if (
                diagnostic["phase"] != "INNER_ACTIVE"
                or diagnostic["app_slice_path"] != host["app_slice_path"]
            ):
                _fail("SERVICE host observation diagnostic lost authority join")
        elif schema == HOST_PARENT_IDENTITY_CONFORMANCE_SCHEMA:
            diagnostic = validate_host_parent_identity_conformance_diagnostic(
                primary["detail"]
            )
            if diagnostic["expected_properties"] != (
                _expected_host_parent_identity_properties(host)
            ):
                _fail("SERVICE host identity diagnostic lost authority join")
        elif schema == SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_SCHEMA:
            diagnostic = validate_source_unit_conformance_diagnostic(
                primary["detail"]
            )
            uid = host["owner_uid"]
            source_membership = (
                f"/user.slice/user-{uid}.slice/user@{uid}.service/app.slice/"
                f"{SERVICE_UNIT_NAME}"
            )
            if (
                diagnostic["source_membership"] != source_membership
                or diagnostic["expected_properties"]
                != _source_expected_properties(
                    uid=uid, source_membership=source_membership
                )
            ):
                _fail("SERVICE source diagnostic lost authority join")
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
    cleanup_remove_detail = cleanup_by_name.get(
        "CLEANUP_TARGET_REMOVE", {}
    ).get("detail")
    cleanup_manager_stop_ok = (
        cleanup_remove_ok
        and type(cleanup_remove_detail) is dict
        and set(cleanup_remove_detail) == TARGET_REMOVAL_DETAIL_FIELDS
        and cleanup_remove_detail.get("manager_implicit_absence_proven") is True
    )
    cleanup_absence_ok = (
        cleanup_by_name.get("CLEANUP_TARGET_ABSENT", {}).get("status") == "OK"
    )
    if (
        cleanup_by_name.get("CLEANUP_TARGET_REMOVE", {}).get("status")
        == "FAILED"
        and cleanup_absence_ok
    ):
        _fail("failed target cleanup cannot be reidentified as later absence")
    validated_target = "TARGET_CREATE" in details
    failed_create_diagnostic = (
        validate_target_create_diagnostic(
            primary["detail"],
            expected_target_membership=details.get(
                "SERVICE_PLACEMENT_AND_NCA_PERMISSION", {}
            ).get("target_membership"),
        )
        if primary["substage"] == "TARGET_CREATE"
        and primary["error_type"] == "TargetCreationError"
        else None
    )
    if failed_create_diagnostic is not None:
        outer = failed_create_diagnostic["target_creation_error"]
        if (
            primary["error_type"] != outer["error_type"]
            or primary["message"] != outer["message"]
            or primary["errno"] != outer["errno"]
            or primary["errno_name"] != outer["errno_name"]
        ):
            _fail("primary TARGET_CREATE lost TargetCreationError join")
    failed_primary_removal_diagnostic = (
        validate_target_cleanup_diagnostic(primary["detail"])
        if primary["substage"] == "TARGET_REMOVE"
        and primary["error_type"] == "TargetRemovalError"
        else None
    )
    if failed_primary_removal_diagnostic is not None:
        outer = failed_primary_removal_diagnostic["target_removal_error"]
        target_detail = details.get("TARGET_CREATE")
        if (
            primary["error_type"] != outer["error_type"]
            or primary["message"] != outer["message"]
            or primary["errno"] != outer["errno"]
            or primary["errno_name"] != outer["errno_name"]
            or target_detail is None
            or failed_primary_removal_diagnostic[
                "prior_target_create_diagnostic"
            ]
            != target_detail["manager_create_diagnostic"]
        ):
            _fail("primary TARGET_REMOVE lost TargetRemovalError/create join")
    unit_only_create_claim = (
        failed_create_diagnostic is not None
        and failed_create_diagnostic[
            "manager_unit_ownership_acquired"
        ]
        is True
    )
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
    target_absent = "TARGET_ABSENT" in details or cleanup_absence_ok
    full_removal = normal_removal or (
        full_cleanup_removal
        and cleanup_remove_detail.get(
            "full_target_path_ofd_conformance"
        )
        is True
    )
    failed_cleanup_remove_diagnostic = (
        validate_target_cleanup_diagnostic(cleanup_remove_detail)
        if cleanup_by_name.get("CLEANUP_TARGET_REMOVE", {}).get("status")
        == "FAILED"
        and type(cleanup_remove_detail) is dict
        else None
    )
    return primary, {
        "child_reaped": child_reaped,
        "target_absent": target_absent,
        "target_identity_continuous": full_removal,
        "target_manager_stop_requested": (
            normal_removal
            or cleanup_manager_stop_ok
            or failed_primary_removal_diagnostic is not None
            and failed_primary_removal_diagnostic[
                "manager_stop_requested"
            ]
            is True
            or failed_cleanup_remove_diagnostic is not None
            and failed_cleanup_remove_diagnostic[
                "manager_stop_requested"
            ]
            is True
        ),
        "target_manager_implicit_absence_proven": target_absent,
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
    policy_join = _same_uid_manager_concurrency_policy_join()
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
        or any(retained[key] != value for key, value in policy_join.items())
        or retained["manager_stop_identity_binding_contract"]
        != MANAGER_STOP_IDENTITY_BINDING
        or retained["requested_manager_stop_identity_binding"]
        != MANAGER_STOP_IDENTITY_BINDING
        or retained["clone3_flags"]
        != ["CLONE_INTO_CGROUP", "CLONE_PIDFD"]
        or retained["target_manager_owned"] is not True
        or retained["target_manager_stop_complete"] is not True
        or retained["target_transient_instance_implicit_absence"] is not True
        or retained["target_named_path_detached_and_manager_implicit_absence"] is not True
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
    policy_join = _same_uid_manager_concurrency_policy_join()
    requested_binding = (
        MANAGER_STOP_IDENTITY_BINDING
        if retained["target_manager_stop_requested"] is True
        else MANAGER_STOP_NOT_DISPATCHED
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
        or any(retained[key] != value for key, value in policy_join.items())
        or retained["manager_stop_identity_binding_contract"]
        != MANAGER_STOP_IDENTITY_BINDING
        or retained["requested_manager_stop_identity_binding"]
        != requested_binding
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
        or type(retained["target_manager_implicit_absence_proven"]) is not bool
        or retained["target_manager_implicit_absence_proven"]
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
        or retained["requested_manager_stop_identity_binding"]
        != (
            MANAGER_STOP_IDENTITY_BINDING
            if derived["target_manager_stop_requested"] is True
            else MANAGER_STOP_NOT_DISPATCHED
        )
        or retained["target_manager_implicit_absence_proven"]
        != derived["target_manager_implicit_absence_proven"]
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
    retained_outer = validate_outer_launch_attempt_document(
        loads_canonical_json(outer_raw), authority, external_root_raw
    )
    if retained_outer != expected_outer or outer_raw != canonical_json_bytes(expected_outer):
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
    inner_terminal_manager_stop_requested: bool | None = None
    requested_manager_stop_identity_binding = MANAGER_STOP_IDENTITY_UNKNOWN
    if terminal_kind == "RECEIPT":
        inner_terminal_manager_stop_requested = True
        requested_manager_stop_identity_binding = receipt[
            "requested_manager_stop_identity_binding"
        ]
    elif terminal_kind == "FAILURE":
        inner_terminal_manager_stop_requested = failure[
            "target_manager_stop_requested"
        ]
        requested_manager_stop_identity_binding = failure[
            "requested_manager_stop_identity_binding"
        ]
    observation = {
        "state": terminal_kind,
        **_same_uid_manager_concurrency_policy_join(),
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
        "inner_terminal_manager_stop_requested": (
            inner_terminal_manager_stop_requested
        ),
        "requested_manager_stop_identity_binding": (
            requested_manager_stop_identity_binding
        ),
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
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
        "inner_terminal_manager_stop_requested",
        "requested_manager_stop_identity_binding",
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
        or any(
            value[key] != expected
            for key, expected in _same_uid_manager_concurrency_policy_join().items()
        )
        or value["manager_stop_identity_binding_contract"]
        != MANAGER_STOP_IDENTITY_BINDING
        or type(value["inner_attempt_exact"]) is not bool
        or type(value["artifact_inventory"]) is not list
    ):
        _fail("outer inner observation fields or state changed")
    stop_requested = value["inner_terminal_manager_stop_requested"]
    requested_binding = value["requested_manager_stop_identity_binding"]
    if value["state"] == "RECEIPT":
        if (
            stop_requested is not True
            or requested_binding != MANAGER_STOP_IDENTITY_BINDING
        ):
            _fail("exact inner RECEIPT lost its name-stop exclusion join")
    elif value["state"] == "FAILURE":
        if type(stop_requested) is not bool or requested_binding != (
            MANAGER_STOP_IDENTITY_BINDING
            if stop_requested
            else MANAGER_STOP_NOT_DISPATCHED
        ):
            _fail("exact inner FAILURE lost its name-stop exclusion join")
    elif (
        stop_requested is not None
        or requested_binding != MANAGER_STOP_IDENTITY_UNKNOWN
    ):
        _fail("non-exact inner terminal invented a name-stop observation")
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
        **_same_uid_manager_concurrency_policy_join(),
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
        "requested_manager_stop_identity_binding": inner[
            "requested_manager_stop_identity_binding"
        ],
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
        "target_transient_instance_implicit_absence": (
            postlaunch_absence.get(
                "target_transient_instance_implicit_absence"
            )
            is True
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
    outer_attempt = validate_outer_launch_attempt_document(
        outer_attempt, authority, canonical_json_bytes(authority)
    )
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
        retained["prelaunch_absence"], authority, expected_phase="PRELAUNCH"
    )
    postlaunch_absence = _validate_success_absence_fact(
        retained["postlaunch_absence"], authority, expected_phase="POSTLAUNCH"
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
    policy_join = _same_uid_manager_concurrency_policy_join()
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
        or any(retained[key] != value for key, value in policy_join.items())
        or retained["manager_stop_identity_binding_contract"]
        != MANAGER_STOP_IDENTITY_BINDING
        or retained["requested_manager_stop_identity_binding"]
        != inner_observation["requested_manager_stop_identity_binding"]
        or retained["requested_manager_stop_identity_binding"]
        != MANAGER_STOP_IDENTITY_BINDING
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
        or retained["target_transient_instance_implicit_absence"] is not True
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
        **_same_uid_manager_concurrency_policy_join(),
        "manager_stop_identity_binding_contract": receipt[
            "manager_stop_identity_binding_contract"
        ],
        "requested_manager_stop_identity_binding": receipt[
            "requested_manager_stop_identity_binding"
        ],
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
    policy_join = _same_uid_manager_concurrency_policy_join()
    if (
        canonical_json_bytes(receipt) != receipt_raw
        or retained["outer_launch_attempt_id"]
        != outer_attempt.get("outer_launch_attempt_id")
        or retained["preflight_token"] != PREFLIGHT_TOKEN
        or retained["ordinal"] != PREFLIGHT_ORDINAL
        or any(retained[key] != value for key, value in policy_join.items())
        or any(outer_attempt.get(key) != value for key, value in policy_join.items())
        or any(receipt.get(key) != value for key, value in policy_join.items())
        or retained["manager_stop_identity_binding_contract"]
        != MANAGER_STOP_IDENTITY_BINDING
        or retained["manager_stop_identity_binding_contract"]
        != receipt.get("manager_stop_identity_binding_contract")
        or retained["manager_stop_identity_binding_contract"]
        != outer_attempt.get("manager_stop_identity_binding_contract")
        or retained["requested_manager_stop_identity_binding"]
        != receipt.get("requested_manager_stop_identity_binding")
        or retained["requested_manager_stop_identity_binding"]
        != MANAGER_STOP_IDENTITY_BINDING
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


def _outer_absence_diagnostic_substage(phase: str) -> str:
    if phase not in {"PRELAUNCH", "POSTLAUNCH"}:
        _fail("outer absence diagnostic phase changed")
    return f"OUTER_{phase}_ABSENCE"


def _build_outer_absence_observation_diagnostic(
    *,
    phase: str,
    absence: Mapping[str, Any] | None,
    observation_error: BaseException | None,
) -> dict[str, Any] | None:
    if absence is not None:
        diagnostic = absence.get("host_parent_conformance_diagnostic")
        if type(diagnostic) is not dict or observation_error is not None:
            _fail("outer successful absence lost its host diagnostic")
        return dict(diagnostic)
    if observation_error is None:
        return None
    diagnostic = getattr(observation_error, "diagnostic", None)
    if type(diagnostic) is dict and diagnostic.get("schema") in {
        HOST_PARENT_CONFORMANCE_DIAGNOSTIC_SCHEMA,
        HOST_PARENT_OBSERVATION_FAILURE_SCHEMA,
    }:
        return dict(diagnostic)
    return build_ordinary_failure_diagnostic(
        substage=_outer_absence_diagnostic_substage(phase),
        error=observation_error,
    )


def _validate_outer_absence_observation_diagnostic(
    value: Any,
    *,
    phase: str,
    authority: Mapping[str, Any],
    absence: Mapping[str, Any] | None,
    observation_error: Mapping[str, Any],
    allow_discarded_success: bool = False,
) -> dict[str, Any] | None:
    error_fact = _validate_error_fact(observation_error, required=False)
    error_present = _error_fact_present(error_fact)
    if value is None:
        if absence is not None or error_present or allow_discarded_success:
            _fail("outer attempted absence observation lost its diagnostic")
        return None
    if type(value) is not dict:
        _fail("outer absence observation diagnostic changed")
    host = validate_host_parent_fact(authority["host_parent_fact"])
    schema = value.get("schema")
    wrapper_error: dict[str, Any] | None = None
    if schema == HOST_PARENT_CONFORMANCE_DIAGNOSTIC_SCHEMA:
        diagnostic = validate_host_parent_conformance_diagnostic(value)
        if (
            diagnostic["phase"] != phase
            or diagnostic["expected_snapshot"] != host["property_snapshot"]
            or diagnostic["observed_snapshot"]["app_slice_path"]
            != host["app_slice_path"]
        ):
            _fail("outer host conformance diagnostic lost authority join")
        if diagnostic["conformant"]:
            if error_present:
                _fail("outer successful host diagnostic carries an error")
        else:
            wrapper_error = _error_fact(
                HostParentConformanceError(diagnostic)
            )
    elif schema == HOST_PARENT_OBSERVATION_FAILURE_SCHEMA:
        diagnostic = validate_host_parent_observation_failure(value)
        if (
            diagnostic["phase"] != phase
            or diagnostic["app_slice_path"] != host["app_slice_path"]
        ):
            _fail("outer host observation diagnostic lost authority join")
        wrapper_error = _error_fact(HostParentObservationError(diagnostic))
    elif schema == ORDINARY_FAILURE_DIAGNOSTIC_SCHEMA:
        diagnostic = validate_ordinary_failure_diagnostic(value)
        if diagnostic["substage"] != _outer_absence_diagnostic_substage(
            phase
        ):
            _fail("outer ordinary absence diagnostic lost its phase join")
        wrapper_error = diagnostic["cause"]
    else:
        _fail("outer absence diagnostic schema changed")
    if absence is not None:
        if (
            error_present
            or schema != HOST_PARENT_CONFORMANCE_DIAGNOSTIC_SCHEMA
            or diagnostic["conformant"] is not True
            or diagnostic
            != absence["host_parent_conformance_diagnostic"]
        ):
            _fail("outer successful absence diagnostic lost result join")
    elif wrapper_error is None:
        if not allow_discarded_success:
            _fail("outer discarded successful observation lacks deadline proof")
    elif wrapper_error != error_fact:
        _fail("outer absence diagnostic lost its exact wrapper error join")
    return dict(diagnostic)


def _build_outer_failure_components(
    *,
    prelaunch_absence_error: BaseException | None = None,
    process_adapter_error: BaseException | None = None,
    deadline_gate_error: BaseException | None = None,
    inner_observation_error: BaseException | None = None,
    postlaunch_observation_error: BaseException | None = None,
    postlaunch_absence_error: BaseException | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "prelaunch_absence_error": _error_fact(prelaunch_absence_error),
        "process_adapter_error": _error_fact(process_adapter_error),
        "deadline_gate_error": _error_fact(deadline_gate_error),
        "inner_observation_error": _error_fact(inner_observation_error),
        "postlaunch_observation_error": _error_fact(
            postlaunch_observation_error
        ),
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
    prelaunch_error = components["prelaunch_absence_error"]
    process_error = components["process_adapter_error"]
    deadline_error = components["deadline_gate_error"]
    inner_error = components["inner_observation_error"]
    post_observation_error = components[
        "postlaunch_observation_error"
    ]
    absence_error = components["postlaunch_absence_error"]
    prelaunch_error_present = _error_fact_present(prelaunch_error)
    process_error_present = _error_fact_present(process_error)
    deadline_error_present = _error_fact_present(deadline_error)
    inner_error_present = _error_fact_present(inner_error)
    post_observation_error_present = _error_fact_present(
        post_observation_error
    )
    absence_error_present = _error_fact_present(absence_error)
    if prelaunch_error_present:
        _fail("ordinary outer failure retained a prelaunch error")
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
            if postlaunch_absence is not None:
                _fail("late postlaunch absence result was not discarded")
        else:
            if post_observation_error_present is (
                postlaunch_absence is not None
            ):
                _fail("outer postlaunch observation result/error is not exact")
            if absence_error != post_observation_error:
                _fail("outer postlaunch absence result/error is not exact")
    elif absence_error_present or postlaunch_absence is not None:
        _fail("outer skipped absence observation retained a result or error")
    elif post_observation_error_present:
        _fail("outer skipped absence observation retained an observer error")
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
    prelaunch_absence: Mapping[str, Any] | None,
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
    prelaunch_observation_diagnostic: Mapping[str, Any] | None = None,
    postlaunch_observation_diagnostic: Mapping[str, Any] | None = None,
    prelaunch_absence_error: BaseException | None = None,
    process_adapter_error: BaseException | None = None,
    deadline_gate_error: BaseException | None = None,
    inner_observation_error: BaseException | None = None,
    postlaunch_observation_error: BaseException | None = None,
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
    if prelaunch_observation_diagnostic is None:
        prelaunch_observation_diagnostic = (
            _build_outer_absence_observation_diagnostic(
                phase="PRELAUNCH",
                absence=prelaunch_absence,
                observation_error=prelaunch_absence_error,
            )
        )
    if postlaunch_observation_diagnostic is None:
        postlaunch_observation_diagnostic = (
            _build_outer_absence_observation_diagnostic(
                phase="POSTLAUNCH",
                absence=postlaunch_absence,
                observation_error=postlaunch_observation_error,
            )
        )
    payload = {
        "schema": OUTER_LAUNCH_FAILURE_SCHEMA,
        "outer_launch_attempt_id": outer_attempt["outer_launch_attempt_id"],
        "preflight_token": PREFLIGHT_TOKEN,
        "ordinal": PREFLIGHT_ORDINAL,
        "service_unit_name": SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        **_same_uid_manager_concurrency_policy_join(),
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
        "requested_manager_stop_identity_binding": (
            inner["requested_manager_stop_identity_binding"]
            if inner is not None
            and inner.get("state") in {"RECEIPT", "FAILURE"}
            else MANAGER_STOP_IDENTITY_UNKNOWN
        ),
        "systemd_run_argv_sha256": outer_attempt["systemd_run_argv_sha256"],
        "failure_reason": reason[:512],
        "launch_error": _error_fact(error),
        "failure_components": _build_outer_failure_components(
            prelaunch_absence_error=prelaunch_absence_error,
            process_adapter_error=process_adapter_error,
            deadline_gate_error=deadline_gate_error,
            inner_observation_error=inner_observation_error,
            postlaunch_observation_error=postlaunch_observation_error,
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
        "prelaunch_absence": (
            None if prelaunch_absence is None else dict(prelaunch_absence)
        ),
        "prelaunch_observation_diagnostic": (
            None
            if prelaunch_observation_diagnostic is None
            else dict(prelaunch_observation_diagnostic)
        ),
        "postlaunch_absence": (
            None if postlaunch_absence is None else dict(postlaunch_absence)
        ),
        "postlaunch_observation_diagnostic": (
            None
            if postlaunch_observation_diagnostic is None
            else dict(postlaunch_observation_diagnostic)
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
        "target_transient_instance_implicit_absence": (
            None
            if postlaunch_absence is None
            else postlaunch_absence.get(
                "target_transient_instance_implicit_absence"
            )
            is True
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
    outer_attempt = validate_outer_launch_attempt_document(
        outer_attempt, authority, canonical_json_bytes(authority)
    )
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
    deadline_contract = validate_outer_deadline_contract(
        retained["deadline_contract"]
    )
    prelaunch = retained["prelaunch_absence"]
    if prelaunch is not None and type(prelaunch) is not dict:
        _fail("outer LAUNCH_FAILURE prelaunch absence changed")
    if prelaunch is not None:
        prelaunch = _validate_success_absence_fact(
            prelaunch, authority, expected_phase="PRELAUNCH"
        )
    postlaunch = retained["postlaunch_absence"]
    if postlaunch is not None and type(postlaunch) is not dict:
        _fail("outer LAUNCH_FAILURE postlaunch absence changed")
    if postlaunch is not None:
        postlaunch = _validate_success_absence_fact(
            postlaunch, authority, expected_phase="POSTLAUNCH"
        )
    post_deadline = deadline_contract["post_absence_deadline_monotonic_ns"]
    after_post = deadline_contract["remaining_after_post_absence_ns"]
    postlaunch_discarded_after_local_deadline = (
        type(post_deadline) is int
        and type(after_post) is int
        and deadline_contract["formal_deadline_monotonic_ns"] - after_post
        > post_deadline
    )
    _validate_outer_absence_observation_diagnostic(
        retained["prelaunch_observation_diagnostic"],
        phase="PRELAUNCH",
        authority=authority,
        absence=prelaunch,
        observation_error=failure_components["prelaunch_absence_error"],
    )
    _validate_outer_absence_observation_diagnostic(
        retained["postlaunch_observation_diagnostic"],
        phase="POSTLAUNCH",
        authority=authority,
        absence=postlaunch,
        observation_error=failure_components[
            "postlaunch_observation_error"
        ],
        allow_discarded_success=(
            postlaunch_discarded_after_local_deadline
        ),
    )
    reason = retained["failure_reason"]
    prelaunch_error_present = _error_fact_present(
        failure_components["prelaunch_absence_error"]
    )
    if reason == "LAUNCH_ATTEMPT_PUBLICATION_FAILED":
        if (
            prelaunch is not None
            or retained["prelaunch_observation_diagnostic"] is not None
            or prelaunch_error_present
        ):
            _fail("attempt publication failure acquired prelaunch evidence")
    elif reason == "PRELAUNCH_ABSENCE_FAILED":
        if (
            prelaunch is not None
            or retained["prelaunch_observation_diagnostic"] is None
            or not prelaunch_error_present
        ):
            _fail("prelaunch failure lost its typed observation outcome")
    elif (
        prelaunch is None
        or retained["prelaunch_observation_diagnostic"] is None
        or prelaunch_error_present
    ):
        _fail("post-attempt outer failure lost successful prelaunch proof")
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
    expected_target_transient_instance_implicit_absence = (
        None
        if postlaunch is None
        else postlaunch.get(
            "target_transient_instance_implicit_absence"
        )
        is True
    )
    expected_target_path_absent = (
        None
        if postlaunch is None
        else postlaunch.get("target_path_absent") is True
    )
    expected_requested_binding = (
        inner_observation["requested_manager_stop_identity_binding"]
        if inner_observation is not None
        and inner_observation["state"] in {"RECEIPT", "FAILURE"}
        else MANAGER_STOP_IDENTITY_UNKNOWN
    )
    policy_join = _same_uid_manager_concurrency_policy_join()
    receipt_created = retained["launch_receipt_path_created"]
    result_present = retained["returncode"] is not None
    if (
        retained["outer_launch_attempt_id"]
        != outer_attempt.get("outer_launch_attempt_id")
        or retained["preflight_token"] != PREFLIGHT_TOKEN
        or retained["ordinal"] != PREFLIGHT_ORDINAL
        or retained["service_unit_name"] != SERVICE_UNIT_NAME
        or retained["target_cgroup_name"] != TARGET_CGROUP_NAME
        or any(retained[key] != value for key, value in policy_join.items())
        or retained["manager_stop_identity_binding_contract"]
        != MANAGER_STOP_IDENTITY_BINDING
        or retained["requested_manager_stop_identity_binding"]
        != expected_requested_binding
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
        or retained["target_transient_instance_implicit_absence"]
        != expected_target_transient_instance_implicit_absence
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
    "target_transient_instance_implicit_absence",
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
    elif reason == "PRELAUNCH_ABSENCE_FAILED":
        components = _validate_outer_failure_components(
            failure["failure_components"]
        )
        prelaunch_error = components["prelaunch_absence_error"]
        if (
            names
            != _root_inventory(
                OUTER_LAUNCH_ATTEMPT_NAME, OUTER_LAUNCH_FAILURE_NAME
            )
            or receipt_present
            or result is not None
            or failure["inner_observation"] is not None
            or failure["prelaunch_absence"] is not None
            or failure["prelaunch_observation_diagnostic"] is None
            or failure["postlaunch_absence"] is not None
            or failure["postlaunch_observation_diagnostic"] is not None
            or not _error_fact_present(prelaunch_error)
            or failure["launch_error"] != prelaunch_error
            or any(
                _error_fact_present(fact)
                for name, fact in components.items()
                if name != "prelaunch_absence_error"
            )
            or type(
                deadline_contract["remaining_after_attempt_publication_ns"]
            )
            is not int
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
            _fail("prelaunch absence failure semantics changed")
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
                            "inner_terminal_manager_stop_requested": None,
                            "requested_manager_stop_identity_binding": (
                                MANAGER_STOP_IDENTITY_UNKNOWN
                            ),
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
    prelaunch_absence: Mapping[str, Any] | None,
    postlaunch_absence: Mapping[str, Any] | None,
    error: BaseException | None,
    reason: str,
    deadline_contract: Mapping[str, Any],
    prelaunch_observation_diagnostic: Mapping[str, Any] | None = None,
    postlaunch_observation_diagnostic: Mapping[str, Any] | None = None,
    prelaunch_absence_error: BaseException | None = None,
    process_adapter_error: BaseException | None = None,
    deadline_gate_error: BaseException | None = None,
    inner_observation_error: BaseException | None = None,
    postlaunch_observation_error: BaseException | None = None,
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
        prelaunch_observation_diagnostic=(
            prelaunch_observation_diagnostic
        ),
        postlaunch_observation_diagnostic=(
            postlaunch_observation_diagnostic
        ),
        prelaunch_absence_error=prelaunch_absence_error,
        process_adapter_error=process_adapter_error,
        deadline_gate_error=deadline_gate_error,
        inner_observation_error=inner_observation_error,
        postlaunch_observation_error=postlaunch_observation_error,
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
    outer_attempt_issued_ns, remaining_before_launch_ns = (
        _sample_outer_remaining(
            deadline_ns, monotonic_ns, "outer launch issuance"
        )
    )
    required_after_issuance_ns = (
        OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS * 1_000_000_000
    )
    prelaunch_absence: dict[str, Any] | None = None
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
            prelaunch_absence=None,
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
    try:
        prelaunch_absence = _validate_success_absence_fact(
            absence_observer.observe_absence(
                authority, deadline_ns=deadline_ns
            ),
            authority,
            expected_phase="PRELAUNCH",
        )
    except BaseException as error:
        _after_attempt_ns, remaining_after_attempt_ns = (
            _sample_outer_remaining(
                deadline_ns,
                monotonic_ns,
                "outer prelaunch observation failure",
            )
        )
        deadline_contract["remaining_after_attempt_publication_ns"] = (
            remaining_after_attempt_ns
        )
        _terminal_gate_ns, terminal_remaining_ns = _sample_outer_remaining(
            deadline_ns,
            monotonic_ns,
            "outer prelaunch failure publication",
        )
        deadline_contract["remaining_before_terminal_publication_ns"] = (
            terminal_remaining_ns
        )
        deadline_contract = validate_outer_deadline_contract(
            deadline_contract
        )
        diagnostic = _build_outer_absence_observation_diagnostic(
            phase="PRELAUNCH",
            absence=None,
            observation_error=error,
        )
        _publish_outer_launch_failure(
            store=store,
            authority=authority,
            external_root_raw=external_root_raw,
            outer_attempt=outer_attempt,
            result=None,
            inner=None,
            prelaunch_absence=None,
            postlaunch_absence=None,
            error=error,
            reason="PRELAUNCH_ABSENCE_FAILED",
            deadline_contract=deadline_contract,
            prelaunch_observation_diagnostic=diagnostic,
            prelaunch_absence_error=error,
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
    postlaunch_observation_diagnostic: dict[str, Any] | None = None
    postlaunch_observation_error: BaseException | None = None
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
                expected_phase="POSTLAUNCH",
            )
            postlaunch_observation_diagnostic = (
                _build_outer_absence_observation_diagnostic(
                    phase="POSTLAUNCH",
                    absence=postlaunch_absence,
                    observation_error=None,
                )
            )
        except BaseException as error:
            postlaunch_observation_error = error
            absence_error = error
            postlaunch_observation_diagnostic = (
                _build_outer_absence_observation_diagnostic(
                    phase="POSTLAUNCH",
                    absence=None,
                    observation_error=error,
                )
            )
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
        postlaunch_observation_error=postlaunch_observation_error,
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
        postlaunch_observation_diagnostic=(
            postlaunch_observation_diagnostic
        ),
        process_adapter_error=launch_error,
        deadline_gate_error=deadline_gate_error,
        inner_observation_error=inner_error,
        postlaunch_observation_error=postlaunch_observation_error,
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


def build_ordinary_failure_diagnostic(
    *, substage: str, error: BaseException
) -> dict[str, Any]:
    if type(substage) is not str or not substage:
        _fail("ordinary failure diagnostic substage changed")
    payload = {
        "schema": ORDINARY_FAILURE_DIAGNOSTIC_SCHEMA,
        "substage": substage,
        "cause": _error_fact(error),
    }
    return _self_id_document(
        ORDINARY_FAILURE_DIAGNOSTIC_DOMAIN,
        "ordinary_failure_diagnostic_id",
        payload,
    )


def validate_ordinary_failure_diagnostic(document: Any) -> dict[str, Any]:
    retained = _validate_self_id(
        document,
        schema=ORDINARY_FAILURE_DIAGNOSTIC_SCHEMA,
        identity_field="ordinary_failure_diagnostic_id",
        domain=ORDINARY_FAILURE_DIAGNOSTIC_DOMAIN,
    )
    if (
        set(retained)
        != {
            "schema",
            "substage",
            "cause",
            "ordinary_failure_diagnostic_id",
        }
        or type(retained["substage"]) is not str
        or not retained["substage"]
    ):
        _fail("ordinary failure diagnostic fields changed")
    _validate_error_fact(retained["cause"], required=True)
    return retained


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
    owned: bool = False
    manager_created: bool = False
    identity_continuous: bool = False
    stop_requested: bool = False
    manager_implicit_absence_proven: bool = False
    residual_possible: bool = False
    named_path_detached_and_manager_implicit_absence: bool = False
    manager_unit_ownership_acquired: bool = False
    full_target_path_ofd_conformance: bool = False
    create_diagnostic: dict[str, Any] | None = None


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


def _read_bytes_at(directory_fd: int, name: str, cap: int = 64 * 1024) -> bytes:
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
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _read_text_at(directory_fd: int, name: str, cap: int = 64 * 1024) -> str:
    return _read_bytes_at(directory_fd, name, cap).decode(
        "ascii", errors="strict"
    )


def _parse_host_parent_property_bytes(
    name: str, raw: bytes
) -> int | list[str] | str:
    if name not in HOST_PARENT_PROPERTY_KEYS or type(raw) is not bytes:
        _fail("host-parent property name or bytes changed")
    try:
        text = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError as error:
        raise AuthorityError("host-parent property bytes are not ASCII") from error
    if name == "fstatfs_type":
        stripped = text.strip()
        if not stripped.isdigit():
            _fail("host-parent fstatfs type is malformed")
        parsed_number = int(stripped)
        return parsed_number
    if name in {"cgroup.controllers", "cgroup.subtree_control"}:
        parsed = sorted(text.split())
        if parsed != sorted(set(parsed)) or any(not item for item in parsed):
            _fail("host-parent controller property is malformed")
        return parsed
    parsed_type = text.strip()
    if not parsed_type or len(parsed_type) > 128:
        _fail("host-parent cgroup.type is malformed")
    return parsed_type


def build_host_parent_property_snapshot(
    *,
    phase: str,
    app_slice_path: str,
    raw_properties: Mapping[str, bytes],
) -> dict[str, Any]:
    if (
        phase not in HOST_PARENT_SNAPSHOT_PHASES
        or type(app_slice_path) is not str
        or not Path(app_slice_path).is_absolute()
        or not app_slice_path.endswith("/app.slice")
        or set(raw_properties) != HOST_PARENT_PROPERTY_KEYS
    ):
        _fail("host-parent property snapshot inputs changed")
    raw_facts = {
        name: _output_fact(bytes(raw_properties[name]))
        for name in HOST_PARENT_PROPERTY_NAMES
    }
    parsed = {
        name: _parse_host_parent_property_bytes(
            name, bytes(raw_properties[name])
        )
        for name in HOST_PARENT_PROPERTY_NAMES
    }
    payload = {
        "schema": HOST_PARENT_PROPERTY_SNAPSHOT_SCHEMA,
        "phase": phase,
        "app_slice_path": app_slice_path,
        "raw_properties": raw_facts,
        "parsed_properties": parsed,
    }
    return _self_id_document(
        HOST_PARENT_PROPERTY_SNAPSHOT_DOMAIN,
        "host_parent_property_snapshot_id",
        payload,
    )


def validate_host_parent_property_snapshot(
    document: Any,
) -> dict[str, Any]:
    retained = _validate_self_id(
        document,
        schema=HOST_PARENT_PROPERTY_SNAPSHOT_SCHEMA,
        identity_field="host_parent_property_snapshot_id",
        domain=HOST_PARENT_PROPERTY_SNAPSHOT_DOMAIN,
    )
    if set(retained) != {
        "schema",
        "phase",
        "app_slice_path",
        "raw_properties",
        "parsed_properties",
        "host_parent_property_snapshot_id",
    }:
        _fail("host-parent property snapshot fields changed")
    raw_facts = retained["raw_properties"]
    if type(raw_facts) is not dict or set(raw_facts) != HOST_PARENT_PROPERTY_KEYS:
        _fail("host-parent raw property inventory changed")
    raw = {
        name: _validate_output_fact(raw_facts[name], byte_cap=64 * 1024)
        for name in HOST_PARENT_PROPERTY_NAMES
    }
    expected = build_host_parent_property_snapshot(
        phase=retained["phase"],
        app_slice_path=retained["app_slice_path"],
        raw_properties=raw,
    )
    if retained != expected:
        _fail("host-parent property snapshot raw/parsed/self-ID join changed")
    return retained


def build_host_parent_observation_failure(
    *,
    phase: str,
    app_slice_path: str,
    failed_property: str,
    raw_properties: Mapping[str, bytes],
    parsed_properties: Mapping[str, Any],
    cause: BaseException,
) -> dict[str, Any]:
    failed_index = (
        HOST_PARENT_PROPERTY_NAMES.index(failed_property)
        if failed_property in HOST_PARENT_PROPERTY_KEYS
        else -1
    )
    completed_names = frozenset(
        HOST_PARENT_PROPERTY_NAMES[:failed_index]
    )
    raw_names = frozenset(raw_properties)
    parsed_names = frozenset(parsed_properties)
    expected_app_slice_path = (
        f"/sys/fs/cgroup/user.slice/user-{os.geteuid()}.slice/"
        f"user@{os.geteuid()}.service/app.slice"
    )
    if (
        phase not in HOST_PARENT_SNAPSHOT_PHASES
        or type(app_slice_path) is not str
        or app_slice_path != expected_app_slice_path
        or failed_property not in HOST_PARENT_PROPERTY_KEYS
        or parsed_names != completed_names
        or raw_names
        not in {
            completed_names,
            frozenset((*completed_names, failed_property)),
        }
    ):
        _fail("host-parent partial observation inputs changed")
    failure_kind = "PARSE" if failed_property in raw_names else "READ"
    cause_fact = _error_fact(cause)
    if failure_kind == "PARSE":
        try:
            _parse_host_parent_property_bytes(
                failed_property, raw_properties[failed_property]
            )
        except BaseException as replay_error:
            if _error_fact(replay_error) != cause_fact:
                _fail("host-parent parse failure cause was reidentified")
        else:
            _fail("host-parent parse failure retained parseable bytes")
    payload = {
        "schema": HOST_PARENT_OBSERVATION_FAILURE_SCHEMA,
        "phase": phase,
        "app_slice_path": app_slice_path,
        "requested_properties": list(HOST_PARENT_PROPERTY_NAMES),
        "failed_property": failed_property,
        "failure_kind": failure_kind,
        "raw_properties": {
            name: _output_fact(raw_properties[name])
            for name in HOST_PARENT_PROPERTY_NAMES
            if name in raw_properties
        },
        "parsed_properties": dict(parsed_properties),
        "cause": cause_fact,
    }
    return _self_id_document(
        HOST_PARENT_OBSERVATION_FAILURE_DOMAIN,
        "host_parent_observation_failure_id",
        payload,
    )


def validate_host_parent_observation_failure(document: Any) -> dict[str, Any]:
    retained = _validate_self_id(
        document,
        schema=HOST_PARENT_OBSERVATION_FAILURE_SCHEMA,
        identity_field="host_parent_observation_failure_id",
        domain=HOST_PARENT_OBSERVATION_FAILURE_DOMAIN,
    )
    if set(retained) != {
        "schema",
        "phase",
        "app_slice_path",
        "requested_properties",
        "failed_property",
        "failure_kind",
        "raw_properties",
        "parsed_properties",
        "cause",
        "host_parent_observation_failure_id",
    }:
        _fail("host-parent observation failure fields changed")
    failed_property = retained["failed_property"]
    failed_index = (
        HOST_PARENT_PROPERTY_NAMES.index(failed_property)
        if failed_property in HOST_PARENT_PROPERTY_KEYS
        else -1
    )
    completed_names = frozenset(
        HOST_PARENT_PROPERTY_NAMES[:failed_index]
    )
    raw_names = (
        frozenset(retained["raw_properties"])
        if type(retained["raw_properties"]) is dict
        else frozenset()
    )
    parsed_names = (
        frozenset(retained["parsed_properties"])
        if type(retained["parsed_properties"]) is dict
        else frozenset()
    )
    expected_app_slice_path = (
        f"/sys/fs/cgroup/user.slice/user-{os.geteuid()}.slice/"
        f"user@{os.geteuid()}.service/app.slice"
    )
    if (
        retained["phase"] not in HOST_PARENT_SNAPSHOT_PHASES
        or type(retained["app_slice_path"]) is not str
        or retained["app_slice_path"] != expected_app_slice_path
        or retained["requested_properties"] != list(HOST_PARENT_PROPERTY_NAMES)
        or failed_property not in HOST_PARENT_PROPERTY_KEYS
        or retained["failure_kind"] not in {"READ", "PARSE"}
        or type(retained["raw_properties"]) is not dict
        or type(retained["parsed_properties"]) is not dict
        or parsed_names != completed_names
        or raw_names
        not in {
            completed_names,
            frozenset((*completed_names, failed_property)),
        }
    ):
        _fail("host-parent observation failure values changed")
    expected_failure_kind = (
        "PARSE" if failed_property in raw_names else "READ"
    )
    if retained["failure_kind"] != expected_failure_kind:
        _fail("host-parent observation failure kind changed")
    for name, parsed in retained["parsed_properties"].items():
        raw = _validate_output_fact(
            retained["raw_properties"][name], byte_cap=64 * 1024
        )
        if _parse_host_parent_property_bytes(name, raw) != parsed:
            _fail("host-parent partial raw/parsed join changed")
    for name in set(retained["raw_properties"]) - set(
        retained["parsed_properties"]
    ):
        _validate_output_fact(
            retained["raw_properties"][name], byte_cap=64 * 1024
        )
    cause = _validate_error_fact(retained["cause"], required=True)
    if expected_failure_kind == "PARSE":
        failed_raw = _validate_output_fact(
            retained["raw_properties"][failed_property],
            byte_cap=64 * 1024,
        )
        try:
            _parse_host_parent_property_bytes(failed_property, failed_raw)
        except BaseException as replay_error:
            if _error_fact(replay_error) != cause:
                _fail("host-parent parse cause lost raw-byte replay")
        else:
            _fail("host-parent parse failure retained parseable bytes")
    return retained


class HostParentObservationError(OSError):
    def __init__(self, diagnostic: Mapping[str, Any]) -> None:
        retained = validate_host_parent_observation_failure(diagnostic)
        cause = retained["cause"]
        super().__init__(
            int(cause["errno"] or errno.EIO),
            "host app.slice property observation failed at "
            + retained["failed_property"]
            + "; diagnostic_id="
            + retained["host_parent_observation_failure_id"],
        )
        self.diagnostic = retained


def observe_host_parent_property_snapshot(
    directory_fd: int, *, phase: str, app_slice_path: str
) -> dict[str, Any]:
    raw_properties: dict[str, bytes] = {}
    parsed_properties: dict[str, Any] = {}
    for name in HOST_PARENT_PROPERTY_NAMES:
        try:
            raw = (
                f"{_fstatfs_type_fd(directory_fd)}\n".encode("ascii")
                if name == "fstatfs_type"
                else _read_bytes_at(directory_fd, name)
            )
            raw_properties[name] = raw
            parsed_properties[name] = _parse_host_parent_property_bytes(
                name, raw
            )
        except BaseException as error:
            diagnostic = build_host_parent_observation_failure(
                phase=phase,
                app_slice_path=app_slice_path,
                failed_property=name,
                raw_properties=raw_properties,
                parsed_properties=parsed_properties,
                cause=error,
            )
            raise HostParentObservationError(diagnostic) from error
    return build_host_parent_property_snapshot(
        phase=phase,
        app_slice_path=app_slice_path,
        raw_properties=raw_properties,
    )


def _property_mismatch_rows(
    expected: Mapping[str, Any], observed: Mapping[str, Any]
) -> list[dict[str, Any]]:
    keys = sorted(set(expected) | set(observed))
    return [
        {
            "field": key,
            "expected": expected.get(key),
            "observed": observed.get(key),
        }
        for key in keys
        if expected.get(key) != observed.get(key)
    ]


def build_host_parent_conformance_diagnostic(
    *,
    phase: str,
    expected_snapshot: Mapping[str, Any],
    observed_snapshot: Mapping[str, Any],
    cause: BaseException | None,
) -> dict[str, Any]:
    expected = validate_host_parent_property_snapshot(expected_snapshot)
    observed = validate_host_parent_property_snapshot(observed_snapshot)
    if (
        expected["phase"] != "PREPARE"
        or observed["phase"] != phase
        or phase not in {"PRELAUNCH", "POSTLAUNCH", "INNER_ACTIVE"}
        or expected["app_slice_path"] != observed["app_slice_path"]
    ):
        _fail("host-parent conformance snapshot phases or path changed")
    mismatches = _property_mismatch_rows(
        expected["parsed_properties"], observed["parsed_properties"]
    )
    conformant = not mismatches
    cause_fact = _error_fact(cause)
    if conformant is (cause is not None):
        _fail("host-parent conformance cause matrix changed")
    if mismatches:
        expected_message = (
            f"[Errno {errno.ESTALE}] host app.slice property mismatch: "
            + ",".join(row["field"] for row in mismatches)
        )
        if cause_fact != {
            "error_type": "OSError",
            "message": expected_message,
            "errno": errno.ESTALE,
            "errno_name": errno.errorcode[errno.ESTALE],
        }:
            _fail("host-parent mismatch cause is not its exact typed cause")
    payload = {
        "schema": HOST_PARENT_CONFORMANCE_DIAGNOSTIC_SCHEMA,
        "phase": phase,
        "expected_snapshot": expected,
        "observed_snapshot": observed,
        "expected_properties": expected["parsed_properties"],
        "observed_properties": observed["parsed_properties"],
        "mismatch_rows": mismatches,
        "conformant": conformant,
        "cause": cause_fact,
    }
    return _self_id_document(
        HOST_PARENT_CONFORMANCE_DIAGNOSTIC_DOMAIN,
        "host_parent_conformance_diagnostic_id",
        payload,
    )


def validate_host_parent_conformance_diagnostic(
    document: Any,
) -> dict[str, Any]:
    retained = _validate_self_id(
        document,
        schema=HOST_PARENT_CONFORMANCE_DIAGNOSTIC_SCHEMA,
        identity_field="host_parent_conformance_diagnostic_id",
        domain=HOST_PARENT_CONFORMANCE_DIAGNOSTIC_DOMAIN,
    )
    if set(retained) != {
        "schema",
        "phase",
        "expected_snapshot",
        "observed_snapshot",
        "expected_properties",
        "observed_properties",
        "mismatch_rows",
        "conformant",
        "cause",
        "host_parent_conformance_diagnostic_id",
    }:
        _fail("host-parent conformance diagnostic fields changed")
    cause = _validate_error_fact(
        retained["cause"], required=retained["conformant"] is False
    )
    expected = validate_host_parent_property_snapshot(
        retained["expected_snapshot"]
    )
    observed = validate_host_parent_property_snapshot(
        retained["observed_snapshot"]
    )
    if (
        expected["phase"] != "PREPARE"
        or retained["phase"] not in {
            "PRELAUNCH",
            "POSTLAUNCH",
            "INNER_ACTIVE",
        }
        or observed["phase"] != retained["phase"]
        or expected["app_slice_path"] != observed["app_slice_path"]
        or retained["expected_properties"] != expected["parsed_properties"]
        or retained["observed_properties"] != observed["parsed_properties"]
        or retained["mismatch_rows"]
        != _property_mismatch_rows(
            expected["parsed_properties"], observed["parsed_properties"]
        )
        or retained["conformant"] is not (not retained["mismatch_rows"])
        or retained["phase"] != observed["phase"]
        or (retained["conformant"] and any(cause.values()))
    ):
        _fail("host-parent conformance diagnostic replay changed")
    if retained["mismatch_rows"]:
        expected_cause = {
            "error_type": "OSError",
            "message": (
                f"[Errno {errno.ESTALE}] host app.slice property mismatch: "
                + ",".join(
                    row["field"] for row in retained["mismatch_rows"]
                )
            ),
            "errno": errno.ESTALE,
            "errno_name": errno.errorcode[errno.ESTALE],
        }
        if cause != expected_cause:
            _fail("host-parent mismatch cause was reidentified")
    return retained


class HostParentConformanceError(OSError):
    def __init__(self, diagnostic: Mapping[str, Any]) -> None:
        retained = validate_host_parent_conformance_diagnostic(diagnostic)
        fields = ",".join(row["field"] for row in retained["mismatch_rows"])
        super().__init__(
            errno.ESTALE,
            f"host app.slice property conformance failed: {fields}; "
            "diagnostic_id="
            + retained["host_parent_conformance_diagnostic_id"],
        )
        self.diagnostic = retained


def _expected_host_parent_identity_properties(
    host_parent_fact: Mapping[str, Any],
) -> dict[str, int]:
    expected = {
        name: host_parent_fact[name]
        for name in HOST_PARENT_IDENTITY_PROPERTY_NAMES
        if name not in {"runtime_dir_file_type", "user_bus_file_type"}
    }
    expected.update(
        {
            "runtime_dir_file_type": stat.S_IFDIR,
            "user_bus_file_type": stat.S_IFSOCK,
        }
    )
    if (
        set(expected) != HOST_PARENT_IDENTITY_PROPERTY_KEYS
        or any(type(value) is not int for value in expected.values())
    ):
        _fail("host-parent expected identity properties changed")
    return expected


def build_host_parent_identity_conformance_diagnostic(
    *,
    phase: str,
    expected_properties: Mapping[str, Any],
    observed_properties: Mapping[str, Any],
    cause: BaseException | None,
) -> dict[str, Any]:
    expected = dict(expected_properties)
    observed = dict(observed_properties)
    if (
        phase != "INNER_ACTIVE"
        or not expected
        or set(expected) != set(observed)
        or set(expected) != HOST_PARENT_IDENTITY_PROPERTY_KEYS
        or any(type(key) is not str or not key for key in expected)
        or any(type(value) is not int for value in expected.values())
        or any(type(value) is not int for value in observed.values())
    ):
        _fail("host-parent identity conformance inputs changed")
    mismatches = _property_mismatch_rows(expected, observed)
    conformant = not mismatches
    if conformant is (cause is not None):
        _fail("host-parent identity cause matrix changed")
    cause_fact = _error_fact(cause)
    if mismatches:
        expected_cause = {
            "error_type": "OSError",
            "message": (
                f"[Errno {errno.ESTALE}] host app.slice identity mismatch: "
                + ",".join(row["field"] for row in mismatches)
            ),
            "errno": errno.ESTALE,
            "errno_name": errno.errorcode[errno.ESTALE],
        }
        if cause_fact != expected_cause:
            _fail("host-parent identity mismatch lost its exact cause")
    payload = {
        "schema": HOST_PARENT_IDENTITY_CONFORMANCE_SCHEMA,
        "phase": phase,
        "expected_properties_raw": _output_fact(
            canonical_json_bytes(expected)
        ),
        "observed_properties_raw": _output_fact(
            canonical_json_bytes(observed)
        ),
        "expected_properties": expected,
        "observed_properties": observed,
        "mismatch_rows": mismatches,
        "conformant": conformant,
        "cause": cause_fact,
    }
    return _self_id_document(
        HOST_PARENT_IDENTITY_CONFORMANCE_DOMAIN,
        "host_parent_identity_conformance_diagnostic_id",
        payload,
    )


def validate_host_parent_identity_conformance_diagnostic(
    document: Any,
) -> dict[str, Any]:
    retained = _validate_self_id(
        document,
        schema=HOST_PARENT_IDENTITY_CONFORMANCE_SCHEMA,
        identity_field="host_parent_identity_conformance_diagnostic_id",
        domain=HOST_PARENT_IDENTITY_CONFORMANCE_DOMAIN,
    )
    if set(retained) != {
        "schema",
        "phase",
        "expected_properties_raw",
        "observed_properties_raw",
        "expected_properties",
        "observed_properties",
        "mismatch_rows",
        "conformant",
        "cause",
        "host_parent_identity_conformance_diagnostic_id",
    }:
        _fail("host-parent identity conformance fields changed")
    expected = retained["expected_properties"]
    observed = retained["observed_properties"]
    if (
        retained["phase"] != "INNER_ACTIVE"
        or type(expected) is not dict
        or type(observed) is not dict
        or not expected
        or set(expected) != set(observed)
        or set(expected) != HOST_PARENT_IDENTITY_PROPERTY_KEYS
        or any(type(value) is not int for value in expected.values())
        or any(type(value) is not int for value in observed.values())
        or _validate_output_fact(
            retained["expected_properties_raw"], byte_cap=64 * 1024
        )
        != canonical_json_bytes(expected)
        or _validate_output_fact(
            retained["observed_properties_raw"], byte_cap=64 * 1024
        )
        != canonical_json_bytes(observed)
    ):
        _fail("host-parent identity raw/property join changed")
    mismatches = _property_mismatch_rows(expected, observed)
    cause = _validate_error_fact(
        retained["cause"], required=bool(mismatches)
    )
    if (
        retained["mismatch_rows"] != mismatches
        or retained["conformant"] is not (not mismatches)
    ):
        _fail("host-parent identity mismatch replay changed")
    expected_cause = (
        _error_fact(None)
        if not mismatches
        else {
            "error_type": "OSError",
            "message": (
                f"[Errno {errno.ESTALE}] host app.slice identity mismatch: "
                + ",".join(row["field"] for row in mismatches)
            ),
            "errno": errno.ESTALE,
            "errno_name": errno.errorcode[errno.ESTALE],
        }
    )
    if cause != expected_cause:
        _fail("host-parent identity cause was reidentified")
    return retained


class HostParentIdentityConformanceError(OSError):
    def __init__(self, diagnostic: Mapping[str, Any]) -> None:
        retained = validate_host_parent_identity_conformance_diagnostic(
            diagnostic
        )
        fields = ",".join(row["field"] for row in retained["mismatch_rows"])
        super().__init__(
            errno.ESTALE,
            f"host app.slice identity conformance failed: {fields}; "
            "diagnostic_id="
            + retained["host_parent_identity_conformance_diagnostic_id"],
        )
        self.diagnostic = retained


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
        property_snapshot = observe_host_parent_property_snapshot(
            descriptor,
            phase="PREPARE",
            app_slice_path=str(app_slice_path),
        )
        parsed_properties = property_snapshot["parsed_properties"]
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
            "controllers": parsed_properties["cgroup.controllers"],
            "subtree_control": parsed_properties["cgroup.subtree_control"],
            "cgroup_type": parsed_properties["cgroup.type"],
            "property_snapshot": property_snapshot,
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


def _source_expected_properties(
    *, uid: int, source_membership: str
) -> dict[str, str]:
    expected = _source_expected_static_properties(uid)
    expected["ControlGroup"] = source_membership
    if set(expected) != SOURCE_MANAGER_ACTIVE_PROPERTY_KEYS:
        _fail("source-unit expected property keyset changed")
    return expected


def _source_manager_result_failure_fact(
    result: Mapping[str, Any],
) -> dict[str, Any] | None:
    retained = _validate_bounded_process_result_fact(result)
    if retained is None:
        _fail("source-unit result failure proof omitted its result")
    stdout = _validate_output_fact(
        retained["stdout"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
    )
    stderr = _validate_output_fact(
        retained["stderr"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
    )
    if (
        retained["argv"] != _source_active_show_argv()
        or retained["returncode"] != 0
        or retained["timed_out"]
        or retained["output_limit_exceeded"]
        or stderr
    ):
        return _error_fact(
            AuthorityError("source-unit active property show contract failed")
        )
    try:
        _parse_target_manager_properties(
            stdout, expected_keys=SOURCE_MANAGER_ACTIVE_PROPERTY_KEYS
        )
    except BaseException as error:
        return _error_fact(error)
    return None


def build_source_unit_conformance_diagnostic(
    *,
    uid: int,
    source_membership: str,
    manager_show_result: BoundedProcessResult | None,
    observed_properties: Mapping[str, str] | None,
    cause: BaseException | None,
) -> dict[str, Any]:
    expected = _source_expected_properties(
        uid=uid, source_membership=source_membership
    )
    observed = (
        None
        if observed_properties is None
        else dict(observed_properties)
    )
    if observed is not None and (
        set(observed) != SOURCE_MANAGER_ACTIVE_PROPERTY_KEYS
        or any(
            type(key) is not str or type(value) is not str
            for key, value in observed.items()
        )
    ):
        _fail("source-unit observed properties changed")
    mismatch_rows = (
        [
            {"field": key, "expected": value, "observed": None}
            for key, value in sorted(expected.items())
        ]
        if observed is None
        else _property_mismatch_rows(expected, observed)
    )
    conformant = not mismatch_rows
    if conformant is (cause is not None):
        _fail("source-unit conformance cause matrix changed")
    cause_fact = _error_fact(cause)
    if observed is not None and mismatch_rows:
        expected_cause = {
            "error_type": "OSError",
            "message": (
                f"[Errno {errno.EPROTO}] source unit property mismatch: "
                + ",".join(row["field"] for row in mismatch_rows)
            ),
            "errno": errno.EPROTO,
            "errno_name": errno.errorcode[errno.EPROTO],
        }
        if cause_fact != expected_cause:
            _fail("source-unit mismatch cause is not its exact typed cause")
    result_fact = _bounded_process_result_fact(manager_show_result)
    if observed is None and result_fact is not None:
        expected_failure = _source_manager_result_failure_fact(result_fact)
        if expected_failure is None or cause_fact != expected_failure:
            _fail("source-unit missing observation lacks exact result failure")
    payload = {
        "schema": SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_SCHEMA,
        "source_unit_name": SERVICE_UNIT_NAME,
        "source_membership": source_membership,
        "manager_show_argv": _source_active_show_argv(),
        "manager_show_result": result_fact,
        "expected_properties": expected,
        "observed_properties": observed,
        "mismatch_rows": mismatch_rows,
        "delegation_enabled": (
            None if observed is None else observed.get("Delegate") == "yes"
        ),
        "delegated_controllers": (
            None
            if observed is None
            else sorted(observed.get("DelegateControllers", "").split())
        ),
        "conformant": conformant,
        "cause": cause_fact,
    }
    return _self_id_document(
        SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_DOMAIN,
        "source_unit_conformance_diagnostic_id",
        payload,
    )


def validate_source_unit_conformance_diagnostic(
    document: Any,
) -> dict[str, Any]:
    retained = _validate_self_id(
        document,
        schema=SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_SCHEMA,
        identity_field="source_unit_conformance_diagnostic_id",
        domain=SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_DOMAIN,
    )
    if set(retained) != {
        "schema",
        "source_unit_name",
        "source_membership",
        "manager_show_argv",
        "manager_show_result",
        "expected_properties",
        "observed_properties",
        "mismatch_rows",
        "delegation_enabled",
        "delegated_controllers",
        "conformant",
        "cause",
        "source_unit_conformance_diagnostic_id",
    }:
        _fail("source-unit conformance diagnostic fields changed")
    source_membership = retained["source_membership"]
    if (
        retained["source_unit_name"] != SERVICE_UNIT_NAME
        or type(source_membership) is not str
        or not source_membership.endswith("/" + SERVICE_UNIT_NAME)
        or retained["manager_show_argv"] != _source_active_show_argv()
    ):
        _fail("source-unit conformance identity changed")
    expected = _source_expected_properties(
        uid=os.geteuid(), source_membership=source_membership
    )
    if retained["expected_properties"] != expected:
        _fail("source-unit expected property map changed")
    result = _validate_bounded_process_result_fact(
        retained["manager_show_result"]
    )
    observed = retained["observed_properties"]
    if observed is not None:
        if (
            result is None
            or result["argv"] != _source_active_show_argv()
            or result["returncode"] != 0
            or result["timed_out"]
            or result["output_limit_exceeded"]
            or _validate_output_fact(
                result["stderr"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
            )
            != b""
        ):
            _fail("source-unit manager result changed")
        raw = _validate_output_fact(
            result["stdout"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
        )
        if _parse_target_manager_properties(
            raw, expected_keys=SOURCE_MANAGER_ACTIVE_PROPERTY_KEYS
        ) != observed:
            _fail("source-unit observed properties lost raw-byte join")
        expected_mismatches = _property_mismatch_rows(expected, observed)
        expected_enabled: bool | None = observed.get("Delegate") == "yes"
        expected_controllers: list[str] | None = sorted(
            observed.get("DelegateControllers", "").split()
        )
    else:
        expected_mismatches = [
            {"field": key, "expected": value, "observed": None}
            for key, value in sorted(expected.items())
        ]
        expected_enabled = None
        expected_controllers = None
        if result is not None:
            expected_failure = _source_manager_result_failure_fact(result)
            if expected_failure is None:
                _fail("source-unit successful result lost parsed properties")
    cause = _validate_error_fact(
        retained["cause"], required=retained["conformant"] is False
    )
    if (
        retained["mismatch_rows"] != expected_mismatches
        or retained["delegation_enabled"] is not expected_enabled
        or retained["delegated_controllers"] != expected_controllers
        or retained["conformant"] is not (not expected_mismatches)
        or retained["conformant"]
        and any(cause.values())
    ):
        _fail("source-unit conformance replay changed")
    if observed is None and result is not None and cause != expected_failure:
        _fail("source-unit result failure cause was reidentified")
    if observed is not None and expected_mismatches:
        expected_cause = {
            "error_type": "OSError",
            "message": (
                f"[Errno {errno.EPROTO}] source unit property mismatch: "
                + ",".join(
                    row["field"] for row in expected_mismatches
                )
            ),
            "errno": errno.EPROTO,
            "errno_name": errno.errorcode[errno.EPROTO],
        }
        if cause != expected_cause:
            _fail("source-unit mismatch cause was reidentified")
    return retained


class SourceUnitConformanceError(OSError):
    def __init__(self, diagnostic: Mapping[str, Any]) -> None:
        retained = validate_source_unit_conformance_diagnostic(diagnostic)
        fields = ",".join(row["field"] for row in retained["mismatch_rows"])
        super().__init__(
            errno.EPROTO,
            f"source unit property conformance failed: {fields}; "
            "diagnostic_id="
            + retained["source_unit_conformance_diagnostic_id"],
        )
        self.diagnostic = retained


def _target_manager_implicit_absence(properties: Mapping[str, Any]) -> bool:
    return dict(properties) == {
        "LoadState": "loaded",
        "ActiveState": "inactive",
        "SubState": "dead",
        "ControlGroup": "",
        "BindsTo": "",
        "After": SERVICE_SLICE,
        "Delegate": "no",
        "CollectMode": "inactive",
        "Slice": SERVICE_SLICE,
        "Transient": "no",
        "FragmentPath": "",
        "UnitFileState": "",
        "Job": "",
    }


@dataclass(frozen=True, slots=True)
class TargetManagerConformance:
    """Typed result; a mismatch is evidence, never a truthy/falsey shortcut."""

    expected_control_group: str
    expected_properties: dict[str, str]
    observed_properties: dict[str, str]
    mismatch_keys: tuple[str, ...]

    @property
    def conformant(self) -> bool:
        return not self.mismatch_keys

    def as_document(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_CONFORMANCE_SCHEMA,
            "expected_control_group": self.expected_control_group,
            "expected_properties": dict(self.expected_properties),
            "observed_properties": dict(self.observed_properties),
            "mismatch_keys": list(self.mismatch_keys),
            "conformant": self.conformant,
        }
        return _self_id_document(
            TARGET_CONFORMANCE_DOMAIN, "target_conformance_id", payload
        )


def _target_manager_expected_properties(
    expected_control_group: str,
) -> dict[str, str]:
    return {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "active",
        "ControlGroup": expected_control_group,
        "BindsTo": SERVICE_UNIT_NAME,
        "After": f"CONTAINS:{SERVICE_UNIT_NAME}",
        "Delegate": "no",
        "CollectMode": "inactive-or-failed",
        "Slice": SERVICE_SLICE,
        "Transient": "yes",
        "FragmentPath": build_target_lifecycle_contract(os.geteuid())[
            "transient_fragment_path"
        ],
        "UnitFileState": "transient",
        "Job": "",
    }


def _target_manager_mismatch_keys(
    properties: Mapping[str, Any], *, expected_control_group: str
) -> tuple[str, ...]:
    retained = dict(properties)
    mismatches = set(TARGET_MANAGER_ACTIVE_PROPERTY_KEYS - set(retained))
    mismatches.update(set(retained) - TARGET_MANAGER_ACTIVE_PROPERTY_KEYS)

    def mismatch(key: str, predicate: Callable[[str], bool]) -> None:
        value = retained.get(key)
        if type(value) is not str or not predicate(value):
            mismatches.add(key)

    mismatch("LoadState", lambda value: value == "loaded")
    mismatch("ActiveState", lambda value: value == "active")
    mismatch("SubState", lambda value: value == "active")
    mismatch("ControlGroup", lambda value: value == expected_control_group)
    mismatch("BindsTo", lambda value: value.split() == [SERVICE_UNIT_NAME])
    mismatch("After", lambda value: SERVICE_UNIT_NAME in value.split())
    mismatch("Delegate", lambda value: value == "no")
    mismatch("CollectMode", lambda value: value == "inactive-or-failed")
    mismatch("Slice", lambda value: value == SERVICE_SLICE)
    mismatch("Transient", lambda value: value == "yes")
    mismatch(
        "FragmentPath",
        lambda value: value
        == build_target_lifecycle_contract(os.geteuid())[
            "transient_fragment_path"
        ],
    )
    mismatch("UnitFileState", lambda value: value == "transient")
    mismatch("Job", lambda value: value == "")
    return tuple(sorted(mismatches))


def _target_manager_active(
    properties: Mapping[str, Any], *, expected_control_group: str
) -> TargetManagerConformance:
    if type(expected_control_group) is not str or not expected_control_group:
        _fail("target conformance expected control group changed")
    retained = dict(properties)
    if any(type(key) is not str or type(value) is not str for key, value in retained.items()):
        _fail("target conformance properties are not string pairs")
    return TargetManagerConformance(
        expected_control_group=expected_control_group,
        expected_properties=_target_manager_expected_properties(
            expected_control_group
        ),
        observed_properties=retained,
        mismatch_keys=_target_manager_mismatch_keys(
            retained, expected_control_group=expected_control_group
        ),
    )


def validate_target_manager_conformance_document(
    document: Any,
) -> dict[str, Any]:
    retained = _validate_self_id(
        document,
        schema=TARGET_CONFORMANCE_SCHEMA,
        identity_field="target_conformance_id",
        domain=TARGET_CONFORMANCE_DOMAIN,
    )
    if set(retained) != {
        "schema",
        "expected_control_group",
        "expected_properties",
        "observed_properties",
        "mismatch_keys",
        "conformant",
        "target_conformance_id",
    }:
        _fail("target conformance fields changed")
    expected = _target_manager_active(
        retained["observed_properties"],
        expected_control_group=retained["expected_control_group"],
    ).as_document()
    if retained != expected:
        _fail("target conformance result is not replay-exact")
    return retained


def _target_manager_is_static_terminal(
    properties: Mapping[str, Any],
) -> bool:
    """Reject only job-closed terminal maps, never start transitions."""

    if properties.get("Job") != "":
        return False
    state = (properties.get("ActiveState"), properties.get("SubState"))
    return state in {
        ("active", "active"),
        ("active", "exited"),
        ("failed", "failed"),
        ("inactive", "dead"),
    }


@dataclass(slots=True)
class TargetManagerPollTrace:
    poll_count: int = 0
    first_properties: dict[str, str] | None = None
    last_properties: dict[str, str] | None = None
    changed_property_maps: list[dict[str, Any]] | None = None
    raw_stdout_observations: list[dict[str, Any]] | None = None
    last_conformance: dict[str, Any] | None = None
    stable_mismatch: bool = False
    stable_mismatch_observation_count: int = 0

    def __post_init__(self) -> None:
        if self.changed_property_maps is None:
            self.changed_property_maps = []
        if self.raw_stdout_observations is None:
            self.raw_stdout_observations = []


class TargetManagerPollFailure(OSError):
    """Typed create-poll failure retaining all bounded observations."""

    def __init__(
        self,
        error_number: int,
        message: str,
        *,
        phase: str,
        trace: TargetManagerPollTrace,
        cause: BaseException,
    ) -> None:
        super().__init__(error_number, message)
        self.phase = phase
        self.trace = trace
        self.cause = cause


def _poll_raw_aggregate(
    observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = [dict(row) for row in observations]
    return {
        "observation_count": len(normalized),
        "total_byte_count": sum(int(row["byte_count"]) for row in normalized),
        "sha256": hashlib.sha256(canonical_json_bytes(normalized)).hexdigest(),
    }


def poll_target_manager_conformance(
    observe: Callable[[], BoundedProcessResult],
    *,
    expected_control_group: str,
    deadline_ns: int,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
    sleep: Callable[[float], None] = time.sleep,
    max_polls: int = TARGET_MANAGER_MAX_POLLS,
) -> tuple[TargetManagerConformance, TargetManagerPollTrace]:
    """Poll until exact conformance, failing promptly on a stable mismatch."""

    if type(max_polls) is not int or not 1 <= max_polls <= TARGET_MANAGER_MAX_POLLS:
        _fail("target manager poll bound changed")
    trace = TargetManagerPollTrace()
    previous: dict[str, str] | None = None
    stable_fingerprint: bytes | None = None
    stable_count = 0
    while trace.poll_count < max_polls:
        if monotonic_ns() >= deadline_ns:
            cause = OSError(errno.ETIMEDOUT, "target conformance deadline exhausted")
            raise TargetManagerPollFailure(
                errno.ETIMEDOUT,
                "target manager conformance exhausted its absolute deadline",
                phase="ACTIVE_CONFORMANCE_DEADLINE",
                trace=trace,
                cause=cause,
            ) from cause
        try:
            result = observe()
        except BaseException as error:
            number = getattr(error, "errno", None)
            raise TargetManagerPollFailure(
                number if type(number) is int and number > 0 else errno.EIO,
                "target manager active-show subprocess failed",
                phase="ACTIVE_SHOW_SUBPROCESS",
                trace=trace,
                cause=error,
            ) from error
        raw = result.stdout
        trace.poll_count += 1
        assert trace.raw_stdout_observations is not None
        trace.raw_stdout_observations.append(
            {
                "poll_index": trace.poll_count,
                **_output_fact(raw),
            }
        )
        try:
            properties = _parse_target_manager_properties(
                raw, expected_keys=TARGET_MANAGER_ACTIVE_PROPERTY_KEYS
            )
        except BaseException as error:
            number = getattr(error, "errno", None)
            raise TargetManagerPollFailure(
                number if type(number) is int and number > 0 else errno.EPROTO,
                "target manager active-show parse failed",
                phase="ACTIVE_SHOW_PARSE",
                trace=trace,
                cause=error,
            ) from error
        if trace.first_properties is None:
            trace.first_properties = dict(properties)
        elif previous != properties:
            assert previous is not None
            assert trace.changed_property_maps is not None
            trace.changed_property_maps.append(
                {
                    "poll_index": trace.poll_count,
                    "changed_keys": sorted(
                        key
                        for key in set(previous) | set(properties)
                        if previous.get(key) != properties.get(key)
                    ),
                    "properties": dict(properties),
                }
            )
        trace.last_properties = dict(properties)
        conformance = _target_manager_active(
            properties, expected_control_group=expected_control_group
        )
        trace.last_conformance = conformance.as_document()
        if conformance.conformant:
            return conformance, trace
        fingerprint = canonical_json_bytes(
            {
                "properties": properties,
                "mismatch_keys": list(conformance.mismatch_keys),
            }
        )
        if not _target_manager_is_static_terminal(properties):
            stable_fingerprint = None
            stable_count = 0
        elif fingerprint == stable_fingerprint:
            stable_count += 1
        else:
            stable_fingerprint = fingerprint
            stable_count = 1
        trace.stable_mismatch_observation_count = stable_count
        previous = dict(properties)
        if stable_count >= TARGET_MANAGER_STABLE_MISMATCH_POLLS:
            trace.stable_mismatch = True
            cause = OSError(
                errno.EPROTO,
                "stable target manager mismatch: "
                + ",".join(conformance.mismatch_keys),
            )
            raise TargetManagerPollFailure(
                errno.EPROTO,
                "target manager reached a stable nonconformant property map",
                phase="ACTIVE_CONFORMANCE_STABLE_MISMATCH",
                trace=trace,
                cause=cause,
            ) from cause
        if monotonic_ns() < deadline_ns:
            sleep(0.025)
    cause = OSError(errno.ETIMEDOUT, "target conformance poll bound exhausted")
    raise TargetManagerPollFailure(
        errno.ETIMEDOUT,
        "target manager conformance exceeded its poll-count bound",
        phase="ACTIVE_CONFORMANCE_POLL_BOUND",
        trace=trace,
        cause=cause,
    ) from cause


TARGET_CREATE_EXCEPTION_PHASES = frozenset(
    {
        "PRECREATE_ABSENCE",
        "MANAGER_CREATE",
        "ACTIVE_SHOW_SUBPROCESS",
        "ACTIVE_SHOW_PARSE",
        "ACTIVE_CONFORMANCE_STABLE_MISMATCH",
        "ACTIVE_CONFORMANCE_DEADLINE",
        "ACTIVE_CONFORMANCE_POLL_BOUND",
        "TARGET_PATH_OPEN",
        "TARGET_PATH_OFD_CONFORMANCE",
        "TARGET_PERMISSION",
    }
)
TARGET_CREATE_CONFORMANCE_STAGE_NAMES = (
    "manager_active_properties",
    "target_path_opened",
    "target_path_ofd_identity",
    "target_cgroup_procs_write",
)
TARGET_CREATE_CONFORMANCE_STAGE_KEYS = frozenset(
    TARGET_CREATE_CONFORMANCE_STAGE_NAMES
)


def _bounded_process_result_fact(
    result: BoundedProcessResult | None,
) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "argv": list(result.argv),
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "output_limit_exceeded": result.output_limit_exceeded,
        "stdout": _output_fact(result.stdout),
        "stderr": _output_fact(result.stderr),
    }


def _validate_bounded_process_result_fact(
    value: Any,
) -> dict[str, Any] | None:
    if value is None:
        return None
    if type(value) is not dict or set(value) != {
        "argv",
        "returncode",
        "timed_out",
        "output_limit_exceeded",
        "stdout",
        "stderr",
    }:
        _fail("target create subprocess result fields changed")
    if (
        type(value["argv"]) is not list
        or not value["argv"]
        or any(type(item) is not str or not item for item in value["argv"])
        or type(value["returncode"]) is not int
        or type(value["timed_out"]) is not bool
        or type(value["output_limit_exceeded"]) is not bool
    ):
        _fail("target create subprocess result values changed")
    _validate_output_fact(
        value["stdout"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
    )
    _validate_output_fact(
        value["stderr"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
    )
    return dict(value)


def build_target_create_diagnostic(
    *,
    target_membership: str,
    precreate_absence_show_result: BoundedProcessResult | None,
    precreate_manager_properties: Mapping[str, str] | None,
    precreate_manager_implicit_absence: bool | None,
    precreate_target_path_absent: bool | None,
    precreate_transient_fragment_absent: bool | None,
    precreate_transient_fragment_path: str | None,
    precreate_transient_fragment_stat_errno: int | None,
    precreate_parent_stat_errno: int | None,
    precreate_parent_openat_errno: int | None,
    precreate_parent_inventory: Sequence[str] | None,
    manager_create_result: BoundedProcessResult | None,
    manager_create_job_path: str | None,
    ownership_acquired: bool,
    trace: TargetManagerPollTrace,
    full_target_path_ofd_conformance: bool,
    target_device: int | None,
    target_inode: int | None,
    exception_phase: str | None,
    exception_cause: BaseException | None,
    target_creation_error: BaseException | None,
    conformance_stages: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    stages = (
        {
            name: full_target_path_ofd_conformance
            for name in TARGET_CREATE_CONFORMANCE_STAGE_NAMES
        }
        if conformance_stages is None
        else dict(conformance_stages)
    )
    if (
        set(stages) != TARGET_CREATE_CONFORMANCE_STAGE_KEYS
        or any(type(value) is not bool for value in stages.values())
        or full_target_path_ofd_conformance is not all(stages.values())
    ):
        _fail("target create conformance stage matrix changed")
    raw_observations = [
        dict(row) for row in (trace.raw_stdout_observations or [])
    ]
    payload = {
        "schema": TARGET_CREATE_DIAGNOSTIC_SCHEMA,
        "target_token": TARGET_TOKEN,
        "target_unit_name": TARGET_SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        "target_membership": target_membership,
        "precreate_absence_show_result": _bounded_process_result_fact(
            precreate_absence_show_result
        ),
        "precreate_manager_properties": (
            None
            if precreate_manager_properties is None
            else dict(precreate_manager_properties)
        ),
        "precreate_manager_implicit_absence": precreate_manager_implicit_absence,
        "precreate_target_path_absent": precreate_target_path_absent,
        "precreate_transient_fragment_absent": (
            precreate_transient_fragment_absent
        ),
        "precreate_transient_fragment_path": (
            precreate_transient_fragment_path
        ),
        "precreate_transient_fragment_stat_errno": (
            precreate_transient_fragment_stat_errno
        ),
        "precreate_parent_stat_errno": precreate_parent_stat_errno,
        "precreate_parent_openat_errno": precreate_parent_openat_errno,
        "precreate_parent_inventory": (
            None
            if precreate_parent_inventory is None
            else list(precreate_parent_inventory)
        ),
        "manager_create_result": _bounded_process_result_fact(
            manager_create_result
        ),
        "manager_create_job_path": manager_create_job_path,
        "manager_unit_ownership_acquired": ownership_acquired,
        "manager_poll_count": trace.poll_count,
        "first_property_map": (
            None
            if trace.first_properties is None
            else dict(trace.first_properties)
        ),
        "last_property_map": (
            None
            if trace.last_properties is None
            else dict(trace.last_properties)
        ),
        "changed_property_maps": [
            dict(row) for row in (trace.changed_property_maps or [])
        ],
        "raw_stdout_observations": raw_observations,
        "raw_stdout_aggregate": _poll_raw_aggregate(raw_observations),
        "last_conformance": (
            None
            if trace.last_conformance is None
            else dict(trace.last_conformance)
        ),
        "stable_mismatch": trace.stable_mismatch,
        "stable_mismatch_observation_count": (
            trace.stable_mismatch_observation_count
        ),
        "conformance_stages": stages,
        "full_target_path_ofd_conformance": (
            full_target_path_ofd_conformance
        ),
        "target_device": target_device,
        "target_inode": target_inode,
        "exception_phase": exception_phase,
        "exception_cause": _error_fact(exception_cause),
        "target_creation_error": _error_fact(target_creation_error),
    }
    return _self_id_document(
        TARGET_CREATE_DIAGNOSTIC_DOMAIN,
        "target_create_diagnostic_id",
        payload,
    )


def _exact_target_manager_result(
    result: dict[str, Any] | None, *, argv_key: str, require_empty_stdout: bool
) -> bool:
    if result is None:
        return False
    contract = build_target_lifecycle_contract(os.geteuid())
    stdout = _validate_output_fact(
        result["stdout"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
    )
    return (
        result["argv"] == contract[argv_key]
        and result["returncode"] == 0
        and result["timed_out"] is False
        and result["output_limit_exceeded"] is False
        and (
            _target_manager_create_job_path(stdout) is not None
            if argv_key == "create_argv"
            else not require_empty_stdout or stdout == b""
        )
        and _validate_output_fact(
            result["stderr"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
        )
        == b""
    )


def _replay_target_precreate_manager_result(
    result: dict[str, Any] | None,
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    """Replay the retained absence-show result into properties or one error.

    A present result is never an unknown observation.  Its bounded process
    contract either failed deterministically, its exact stdout failed the
    property parser deterministically, or it yields the one exact property
    map.  This prevents a valid absence proof from being re-IDed as an
    unobserved/unknown precreate half.
    """

    if result is None:
        return None, None
    if not _exact_target_manager_result(
        result, argv_key="absence_show_argv", require_empty_stdout=False
    ):
        return None, _error_fact(
            AuthorityError(
                "target manager precreate absence-show contract failed"
            )
        )
    raw = _validate_output_fact(
        result["stdout"], byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES
    )
    try:
        properties = _parse_target_manager_properties(
            raw, expected_keys=TARGET_MANAGER_ABSENCE_PROPERTY_KEYS
        )
    except BaseException as error:
        return None, _error_fact(error)
    return properties, None


def _target_manager_create_job_path(raw: bytes) -> str | None:
    if type(raw) is not bytes or len(raw) > TARGET_MANAGER_OUTPUT_CAP_BYTES:
        return None
    try:
        text = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError:
        return None
    pattern = build_target_lifecycle_contract(os.geteuid())[
        "create_job_path_pattern"
    ]
    if re.fullmatch(pattern, text) is None:
        return None
    return text.split('"', 2)[1]


def _replay_target_poll_trace(
    observations: Sequence[Mapping[str, Any]],
    *, expected_control_group: str,
) -> tuple[
    list[tuple[int, dict[str, str]]],
    list[dict[str, Any]],
    int,
    bool,
]:
    parsed: list[tuple[int, dict[str, str]]] = []
    parse_failed = False
    for position, row in enumerate(observations):
        raw = _validate_output_fact(
            {
                "byte_count": row["byte_count"],
                "sha256": row["sha256"],
                "base64": row["base64"],
            },
            byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
        )
        try:
            properties = _parse_target_manager_properties(
                raw, expected_keys=TARGET_MANAGER_ACTIVE_PROPERTY_KEYS
            )
        except PreflightError:
            if position != len(observations) - 1:
                _fail("target poll parse failure was not terminal")
            parse_failed = True
            break
        parsed.append((int(row["poll_index"]), properties))
    changes: list[dict[str, Any]] = []
    previous: dict[str, str] | None = None
    stable_fingerprint: bytes | None = None
    stable_count = 0
    stable = False
    for position, (poll_index, properties) in enumerate(parsed):
        if previous is not None and previous != properties:
            changes.append(
                {
                    "poll_index": poll_index,
                    "changed_keys": sorted(
                        key
                        for key in set(previous) | set(properties)
                        if previous.get(key) != properties.get(key)
                    ),
                    "properties": dict(properties),
                }
            )
        conformance = _target_manager_active(
            properties, expected_control_group=expected_control_group
        )
        if conformance.conformant:
            if position != len(parsed) - 1 or parse_failed:
                _fail("target poll retained observations after conformance")
            previous = dict(properties)
            continue
        fingerprint = canonical_json_bytes(
            {
                "properties": properties,
                "mismatch_keys": list(conformance.mismatch_keys),
            }
        )
        if not _target_manager_is_static_terminal(properties):
            stable_fingerprint = None
            stable_count = 0
        elif fingerprint == stable_fingerprint:
            stable_count += 1
        else:
            stable_fingerprint = fingerprint
            stable_count = 1
        if stable_count >= TARGET_MANAGER_STABLE_MISMATCH_POLLS:
            stable = True
            if position != len(parsed) - 1 or parse_failed:
                _fail("target poll retained observations after stable mismatch")
        previous = dict(properties)
    if parse_failed and not observations:
        _fail("target poll parse state changed")
    return parsed, changes, stable_count, stable


def validate_target_create_diagnostic(
    document: Any,
    *,
    expected_target_membership: str | None = None,
) -> dict[str, Any]:
    retained = _validate_self_id(
        document,
        schema=TARGET_CREATE_DIAGNOSTIC_SCHEMA,
        identity_field="target_create_diagnostic_id",
        domain=TARGET_CREATE_DIAGNOSTIC_DOMAIN,
    )
    expected_fields = {
        "schema",
        "target_token",
        "target_unit_name",
        "target_cgroup_name",
        "target_membership",
        "precreate_absence_show_result",
        "precreate_manager_properties",
        "precreate_manager_implicit_absence",
        "precreate_target_path_absent",
        "precreate_transient_fragment_absent",
        "precreate_transient_fragment_path",
        "precreate_transient_fragment_stat_errno",
        "precreate_parent_stat_errno",
        "precreate_parent_openat_errno",
        "precreate_parent_inventory",
        "manager_create_result",
        "manager_create_job_path",
        "manager_unit_ownership_acquired",
        "manager_poll_count",
        "first_property_map",
        "last_property_map",
        "changed_property_maps",
        "raw_stdout_observations",
        "raw_stdout_aggregate",
        "last_conformance",
        "stable_mismatch",
        "stable_mismatch_observation_count",
        "conformance_stages",
        "full_target_path_ofd_conformance",
        "target_device",
        "target_inode",
        "exception_phase",
        "exception_cause",
        "target_creation_error",
        "target_create_diagnostic_id",
    }
    if set(retained) != expected_fields:
        _fail("target create diagnostic fields changed")
    membership = retained["target_membership"]
    if (
        retained["target_token"] != TARGET_TOKEN
        or retained["target_unit_name"] != TARGET_SERVICE_UNIT_NAME
        or retained["target_cgroup_name"] != TARGET_CGROUP_NAME
        or type(membership) is not str
        or not membership.startswith("/")
        or (
            expected_target_membership is not None
            and membership != expected_target_membership
        )
    ):
        _fail("target create diagnostic lost its target identity")

    precreate_result = _validate_bounded_process_result_fact(
        retained["precreate_absence_show_result"]
    )
    precreate_result_exact = _exact_target_manager_result(
        precreate_result,
        argv_key="absence_show_argv",
        require_empty_stdout=False,
    )
    replayed_precreate_properties, precreate_result_failure = (
        _replay_target_precreate_manager_result(precreate_result)
    )
    precreate_properties = retained["precreate_manager_properties"]
    if precreate_properties != replayed_precreate_properties:
        _fail("precreate manager properties lost retained-result replay")
    if precreate_properties is not None:
        if (
            type(precreate_properties) is not dict
            or set(precreate_properties) != TARGET_MANAGER_ABSENCE_PROPERTY_KEYS
            or any(
                type(key) is not str or type(value) is not str
                for key, value in precreate_properties.items()
            )
        ):
            _fail("precreate manager properties changed")
    manager_not_found = retained["precreate_manager_implicit_absence"]
    if manager_not_found is not None and type(manager_not_found) is not bool:
        _fail("precreate manager absence tri-state changed")
    if manager_not_found is not (
        None
        if precreate_properties is None
        else _target_manager_implicit_absence(precreate_properties)
    ):
        _fail("precreate manager absence lost its property join")
    path_absent = retained["precreate_target_path_absent"]
    if path_absent is not None and type(path_absent) is not bool:
        _fail("precreate path absence tri-state changed")
    fragment_absent = retained["precreate_transient_fragment_absent"]
    fragment_path = retained["precreate_transient_fragment_path"]
    fragment_stat_errno = retained[
        "precreate_transient_fragment_stat_errno"
    ]
    stat_errno = retained["precreate_parent_stat_errno"]
    openat_errno = retained["precreate_parent_openat_errno"]
    parent_inventory = retained["precreate_parent_inventory"]
    if (
        fragment_absent is not None
        and type(fragment_absent) is not bool
        or fragment_path is not None
        and (type(fragment_path) is not str or not fragment_path)
        or fragment_stat_errno is not None
        and (type(fragment_stat_errno) is not int or fragment_stat_errno <= 0)
        or stat_errno is not None
        and type(stat_errno) is not int
        or openat_errno is not None
        and type(openat_errno) is not int
        or parent_inventory is not None
        and (
            type(parent_inventory) is not list
            or parent_inventory != sorted(set(parent_inventory))
            or any(type(name) is not str or not name for name in parent_inventory)
            or len(parent_inventory) > 4096
        )
    ):
        _fail("precreate path/fragment/parent-dirfd evidence changed")
    expected_path_absent = (
        None
        if parent_inventory is None
        else (
            stat_errno == errno.ENOENT
            and openat_errno == errno.ENOENT
            and TARGET_CGROUP_NAME not in parent_inventory
        )
    )
    if path_absent is not expected_path_absent:
        _fail("precreate named-path absence lost stat/openat/inventory joins")
    expected_fragment_path = build_target_lifecycle_contract(os.geteuid())[
        "transient_fragment_path"
    ]
    if fragment_path is None:
        expected_fragment_absent: bool | None = None
        if fragment_stat_errno is not None:
            _fail("precreate fragment errno lacks its exact path")
    else:
        if fragment_path != expected_fragment_path:
            _fail("precreate fragment path lost its target-unit join")
        expected_fragment_absent = fragment_stat_errno == errno.ENOENT
    if fragment_absent is not expected_fragment_absent:
        _fail("precreate fragment absence lost its stat join")

    create_result = _validate_bounded_process_result_fact(
        retained["manager_create_result"]
    )
    exact_create_result = _exact_target_manager_result(
        create_result, argv_key="create_argv", require_empty_stdout=True
    )
    create_job_path = retained["manager_create_job_path"]
    expected_job_path = (
        None
        if create_result is None
        else _target_manager_create_job_path(
            _validate_output_fact(
                create_result["stdout"],
                byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
            )
        )
    )
    if create_job_path != expected_job_path:
        _fail("target manager create job path lost its raw-byte join")
    owned = retained["manager_unit_ownership_acquired"]
    expected_owned = (
        precreate_result_exact
        and manager_not_found is True
        and path_absent is True
        and fragment_absent is True
        and fragment_path == expected_fragment_path
        and fragment_stat_errno == errno.ENOENT
        and stat_errno == errno.ENOENT
        and openat_errno == errno.ENOENT
        and exact_create_result
        and type(create_job_path) is str
    )
    if type(owned) is not bool or owned is not expected_owned:
        _fail("target manager ownership lost precreate/create joins")

    poll_count = retained["manager_poll_count"]
    observations = retained["raw_stdout_observations"]
    if (
        type(poll_count) is not int
        or not 0 <= poll_count <= TARGET_MANAGER_MAX_POLLS
        or type(observations) is not list
        or len(observations) != poll_count
    ):
        _fail("target create poll count or observation cardinality changed")
    for index, row in enumerate(observations, 1):
        if (
            type(row) is not dict
            or set(row) != {"poll_index", "byte_count", "sha256", "base64"}
            or row["poll_index"] != index
        ):
            _fail("target create raw stdout observation fields changed")
        _validate_output_fact(
            {
                "byte_count": row["byte_count"],
                "sha256": row["sha256"],
                "base64": row["base64"],
            },
            byte_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
        )
    if retained["raw_stdout_aggregate"] != _poll_raw_aggregate(observations):
        _fail("target create raw stdout aggregate changed")
    parsed, replayed_changes, replayed_stable_count, replayed_stable = (
        _replay_target_poll_trace(
            observations, expected_control_group=membership
        )
    )
    expected_first = None if not parsed else parsed[0][1]
    expected_last = None if not parsed else parsed[-1][1]
    first = retained["first_property_map"]
    last = retained["last_property_map"]
    if first != expected_first or last != expected_last:
        _fail("target create first/last property maps lost raw replay")
    for label, properties in (("first", first), ("last", last)):
        if properties is not None and any(
            type(key) is not str or type(value) is not str
            for key, value in properties.items()
        ):
            _fail(f"target create {label} property values changed")
    changes = retained["changed_property_maps"]
    if changes != replayed_changes:
        _fail("target create changed-property replay changed")
    if any(
        type(value) is not str
        for row in changes
        for value in row["properties"].values()
    ):
        _fail("target create changed-property values are not strings")

    last_conformance = retained["last_conformance"]
    expected_last_conformance = (
        None
        if last is None
        else _target_manager_active(
            last, expected_control_group=membership
        ).as_document()
    )
    if last_conformance != expected_last_conformance:
        _fail("last target conformance lost raw/property replay")
    if last_conformance is not None:
        validate_target_manager_conformance_document(last_conformance)
    stable = retained["stable_mismatch"]
    stable_count = retained["stable_mismatch_observation_count"]
    if (
        type(stable) is not bool
        or type(stable_count) is not int
        or stable_count != replayed_stable_count
        or stable is not replayed_stable
    ):
        _fail("target stable mismatch replay changed")

    full = retained["full_target_path_ofd_conformance"]
    stages = retained["conformance_stages"]
    device = retained["target_device"]
    inode = retained["target_inode"]
    if (
        type(stages) is not dict
        or set(stages) != TARGET_CREATE_CONFORMANCE_STAGE_KEYS
        or any(type(value) is not bool for value in stages.values())
        or type(full) is not bool
        or full is not all(stages.values())
        or (
        full
        and (
            owned is not True
            or last_conformance is None
            or last_conformance["conformant"] is not True
            or type(device) is not int
            or device < 0
            or type(inode) is not int
            or inode <= 0
        )
        or not full
        and (device is not None or inode is not None)
        )
    ):
        _fail("target path/OFD conformance boundary changed")

    phase = retained["exception_phase"]
    if phase is not None and phase not in TARGET_CREATE_EXCEPTION_PHASES:
        _fail("target create exception phase changed")
    cause = _validate_error_fact(
        retained["exception_cause"], required=phase is not None
    )
    outer_error = _validate_error_fact(
        retained["target_creation_error"], required=phase is not None
    )
    if phase is None:
        if precreate_result_failure is not None:
            _fail("successful target create retained failed precreate result")
        if (
            full is not True
            or stable
            or outer_error != _error_fact(None)
            or cause != _error_fact(None)
        ):
            _fail("successful target create terminal matrix changed")
    else:
        if precreate_result_failure is not None and (
            phase != "PRECREATE_ABSENCE"
            or cause != precreate_result_failure
        ):
            _fail("precreate result failure lost its exact phase/cause join")
        if (
            precreate_result_failure is None
            and precreate_result is not None
            and manager_not_found is False
            and (
                phase != "PRECREATE_ABSENCE"
                or cause
                != _error_fact(
                    OSError(
                        errno.EEXIST,
                        "target manager unit was not absent immediately before create",
                    )
                )
            )
        ):
            _fail("pre-existing manager unit lost its exact phase/cause join")
        if (
            full is not False
            or outer_error["error_type"] != "TargetCreationError"
            or not outer_error["message"]
        ):
            _fail("failed target create outer error matrix changed")
        expected_outer_text = (
            "target pre-create absence proof failed"
            if phase == "PRECREATE_ABSENCE"
            else (
                "manager target creation stopped before full path/OFD "
                "conformance"
            )
        )
        outer_number = outer_error["errno"]
        cause_number = cause["errno"]
        if phase == "PRECREATE_ABSENCE":
            expected_outer_number = (
                cause_number
                if type(cause_number) is int and cause_number > 0
                else errno.EEXIST
            )
        elif phase in {
            "ACTIVE_SHOW_PARSE",
            "ACTIVE_CONFORMANCE_STABLE_MISMATCH",
        }:
            expected_outer_number = errno.EPROTO
        elif phase in {
            "ACTIVE_CONFORMANCE_DEADLINE",
            "ACTIVE_CONFORMANCE_POLL_BOUND",
        }:
            expected_outer_number = errno.ETIMEDOUT
        else:
            expected_outer_number = (
                cause_number
                if type(cause_number) is int and cause_number > 0
                else errno.EIO
            )
        if (
            outer_number != expected_outer_number
            or outer_error["message"]
            != f"[Errno {outer_number}] {expected_outer_text}"
        ):
            _fail("target create outer errno/message matrix changed")
        if phase == "PRECREATE_ABSENCE" and (
            create_result is not None
            or owned
            or poll_count != 0
            or manager_not_found is True
            and path_absent is True
            and fragment_absent is True
        ):
            _fail("precreate failure carries post-create evidence")
        if phase == "MANAGER_CREATE" and (
            manager_not_found is not True
            or path_absent is not True
            or fragment_absent is not True
            or stat_errno != errno.ENOENT
            or openat_errno != errno.ENOENT
            or owned
            or poll_count != 0
            or exact_create_result
        ):
            _fail("manager-create failure lost its precreate boundary")
        if phase in {
            "ACTIVE_SHOW_SUBPROCESS",
            "ACTIVE_SHOW_PARSE",
            "ACTIVE_CONFORMANCE_STABLE_MISMATCH",
            "ACTIVE_CONFORMANCE_DEADLINE",
            "ACTIVE_CONFORMANCE_POLL_BOUND",
            "TARGET_PATH_OPEN",
            "TARGET_PATH_OFD_CONFORMANCE",
            "TARGET_PERMISSION",
        } and owned is not True:
            _fail("post-create failure lacks exact manager-unit ownership")
        expected_stage_prefix = {
            "PRECREATE_ABSENCE": 0,
            "MANAGER_CREATE": 0,
            "ACTIVE_SHOW_SUBPROCESS": 0,
            "ACTIVE_SHOW_PARSE": 0,
            "ACTIVE_CONFORMANCE_STABLE_MISMATCH": 0,
            "ACTIVE_CONFORMANCE_DEADLINE": 0,
            "ACTIVE_CONFORMANCE_POLL_BOUND": 0,
            "TARGET_PATH_OPEN": 1,
            "TARGET_PATH_OFD_CONFORMANCE": 2,
            "TARGET_PERMISSION": 3,
        }[phase]
        expected_stages = {
            name: index < expected_stage_prefix
            for index, name in enumerate(
                TARGET_CREATE_CONFORMANCE_STAGE_NAMES
            )
        }
        if stages != expected_stages:
            _fail("target conformance stage/exception phase matrix changed")
        parse_failed = poll_count > len(parsed)
        if (phase == "ACTIVE_SHOW_PARSE") is not parse_failed:
            _fail("active-show parse phase/raw replay changed")
        if phase == "ACTIVE_SHOW_PARSE" and outer_number != errno.EPROTO:
            _fail("active-show parse errno changed")
        if (
            phase == "ACTIVE_CONFORMANCE_STABLE_MISMATCH"
        ) is not stable:
            _fail("stable mismatch flag/count/phase equivalence changed")
        if phase == "ACTIVE_CONFORMANCE_STABLE_MISMATCH" and (
            outer_number != errno.EPROTO
            or cause["errno"] != errno.EPROTO
        ):
            _fail("stable mismatch errno/cause changed")
        if phase == "ACTIVE_CONFORMANCE_POLL_BOUND" and (
            poll_count != TARGET_MANAGER_MAX_POLLS
            or stable
            or outer_number != errno.ETIMEDOUT
            or cause["errno"] != errno.ETIMEDOUT
        ):
            _fail("poll-bound failure count changed")
        if phase == "ACTIVE_CONFORMANCE_DEADLINE" and (
            outer_number != errno.ETIMEDOUT
            or cause["errno"] != errno.ETIMEDOUT
        ):
            _fail("active-conformance deadline errno/cause changed")
        if phase in {
            "TARGET_PATH_OPEN",
            "TARGET_PATH_OFD_CONFORMANCE",
            "TARGET_PERMISSION",
        } and (
            last_conformance is None
            or last_conformance["conformant"] is not True
        ):
            _fail("path/OFD phase lacks full manager conformance")
    return retained


def make_target_creation_error(
    *,
    error_number: int,
    message: str,
    target: "TargetHandle | None",
    cause: BaseException,
    diagnostic_arguments: Mapping[str, Any],
) -> TargetCreationError:
    error = TargetCreationError(
        error_number, message, target=target, diagnostic=None
    )
    diagnostic = build_target_create_diagnostic(
        **dict(diagnostic_arguments),
        exception_cause=cause,
        target_creation_error=error,
    )
    validate_target_create_diagnostic(diagnostic)
    error.diagnostic = diagnostic
    return error


def validate_target_creation_error_join(error: TargetCreationError) -> None:
    if type(error.diagnostic) is not dict:
        _fail("TargetCreationError omitted its diagnostic")
    diagnostic = validate_target_create_diagnostic(error.diagnostic)
    if (
        _error_fact(error) != diagnostic["target_creation_error"]
        or _error_fact(error.__cause__) != diagnostic["exception_cause"]
    ):
        _fail("TargetCreationError errno/message/cause join changed")


TARGET_CLEANUP_EXCEPTION_PHASES = frozenset(
    {
        "PRESTOP_IDENTITY",
        "STOP_SUBPROCESS",
        "POSTSTOP_ABSENCE",
        "POSTSTOP_REPLACEMENT",
        "POSTSTOP_RETAINED_OFD_DETACH",
    }
)

PARENT_NAMED_PATH_OBSERVATION_FIELDS = frozenset(
    {
        "name",
        "stat_errno",
        "openat_errno",
        "named_device",
        "named_inode",
        "opened_device",
        "opened_inode",
        "parent_inventory",
        "name_absent",
        "name_present_identity_exact",
    }
)
RETAINED_OFD_DETACH_FACT_FIELDS = frozenset(
    {
        "device",
        "inode",
        "mode",
        "nlink",
        "fstatfs_type",
        "proc_fd_link",
        "proc_fd_link_errno",
        "deleted_marker",
        "cgroup_type_errno",
        "cgroup_events_errno",
        "cgroup_procs_errno",
        "conformant",
    }
)


def _validate_parent_named_path_observation(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if type(value) is not dict or set(value) != PARENT_NAMED_PATH_OBSERVATION_FIELDS:
        _fail("parent-dirfd named-path observation fields changed")
    retained = dict(value)
    inventory = retained["parent_inventory"]
    if (
        retained["name"] != TARGET_CGROUP_NAME
        or type(inventory) is not list
        or inventory != sorted(set(inventory))
        or len(inventory) > 4096
        or any(type(name) is not str or not name for name in inventory)
    ):
        _fail("parent-dirfd named-path inventory changed")
    for key in ("stat_errno", "openat_errno"):
        if retained[key] is not None and (
            type(retained[key]) is not int or retained[key] <= 0
        ):
            _fail("parent-dirfd named-path errno changed")
    for key in (
        "named_device",
        "named_inode",
        "opened_device",
        "opened_inode",
    ):
        if retained[key] is not None and (
            type(retained[key]) is not int or retained[key] < 0
        ):
            _fail("parent-dirfd named-path identity changed")
    absent = (
        retained["stat_errno"] == errno.ENOENT
        and retained["openat_errno"] == errno.ENOENT
        and TARGET_CGROUP_NAME not in inventory
        and all(
            retained[key] is None
            for key in (
                "named_device",
                "named_inode",
                "opened_device",
                "opened_inode",
            )
        )
    )
    present = (
        retained["stat_errno"] is None
        and retained["openat_errno"] is None
        and TARGET_CGROUP_NAME in inventory
        and type(retained["named_device"]) is int
        and type(retained["named_inode"]) is int
        and retained["named_device"] == retained["opened_device"]
        and retained["named_inode"] == retained["opened_inode"]
    )
    if (
        retained["name_absent"] is not absent
        or retained["name_present_identity_exact"] is not present
    ):
        _fail("parent-dirfd named-path result lost its observation joins")
    return retained


def _validate_retained_ofd_detach_fact(
    value: Any,
    *,
    target_path: str | None,
    target_device: int,
    target_inode: int,
) -> dict[str, Any] | None:
    if value is None:
        return None
    if type(value) is not dict or set(value) != RETAINED_OFD_DETACH_FACT_FIELDS:
        _fail("retained cgroup OFD detach fact fields changed")
    retained = dict(value)
    integer_fields = ("device", "inode", "mode", "nlink", "fstatfs_type")
    if any(type(retained[key]) is not int or retained[key] < 0 for key in integer_fields):
        _fail("retained cgroup OFD stat values changed")
    for key in (
        "proc_fd_link_errno",
        "cgroup_type_errno",
        "cgroup_events_errno",
        "cgroup_procs_errno",
    ):
        if retained[key] is not None and (
            type(retained[key]) is not int or retained[key] <= 0
        ):
            _fail("retained cgroup OFD errno changed")
    link = retained["proc_fd_link"]
    if link is not None and type(link) is not str:
        _fail("retained cgroup OFD proc-fd link changed")
    deleted_marker = (
        retained["proc_fd_link_errno"] is None
        and type(link) is str
        and (
            link == target_path + " (deleted)"
            if target_path is not None
            else link.endswith("/" + TARGET_CGROUP_NAME + " (deleted)")
        )
    )
    conformant = (
        retained["device"] == target_device
        and retained["inode"] == target_inode
        and stat.S_ISDIR(retained["mode"])
        and retained["nlink"] > 0
        and retained["fstatfs_type"] == CGROUP2_SUPER_MAGIC
        and deleted_marker
        and retained["cgroup_type_errno"] == errno.ENOENT
        and retained["cgroup_events_errno"] == errno.ENOENT
        and retained["cgroup_procs_errno"] == errno.ENOENT
    )
    if (
        retained["deleted_marker"] is not deleted_marker
        or retained["conformant"] is not conformant
    ):
        _fail("retained cgroup OFD detach result lost its joins")
    return retained


def build_target_cleanup_diagnostic(
    *,
    target: "TargetHandle",
    manager_stop_result: BoundedProcessResult | None,
    manager_stop_requested: bool,
    manager_poll_count: int,
    last_manager_properties: Mapping[str, str] | None,
    target_path_absent: bool | None,
    transient_fragment_absent: bool | None,
    transient_fragment_path: str | None,
    transient_fragment_stat_errno: int | None,
    parent_named_path_observation: Mapping[str, Any] | None,
    retained_ofd_detach_fact: Mapping[str, Any] | None,
    replacement_detected: bool,
    manager_implicit_absence_proven: bool,
    named_path_detached_and_manager_implicit_absence: bool,
    exception_phase: str | None,
    exception_cause: BaseException | None,
    target_removal_error: BaseException | None,
) -> dict[str, Any]:
    full = target.full_target_path_ofd_conformance is True
    payload = {
        "schema": TARGET_CLEANUP_DIAGNOSTIC_SCHEMA,
        **_same_uid_manager_concurrency_policy_join(),
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
        "requested_manager_stop_identity_binding": (
            MANAGER_STOP_IDENTITY_BINDING
            if manager_stop_requested is True
            else MANAGER_STOP_NOT_DISPATCHED
        ),
        "target_token": TARGET_TOKEN,
        "target_unit_name": TARGET_SERVICE_UNIT_NAME,
        "target_cgroup_name": TARGET_CGROUP_NAME,
        "target_membership": target.membership,
        "target_path": target.path,
        "ownership_scope": "UNIT_PATH_OFD" if full else "UNIT_ONLY",
        "manager_unit_ownership_acquired": (
            target.manager_unit_ownership_acquired
        ),
        "full_target_path_ofd_conformance": full,
        "target_device": target.device if full else None,
        "target_inode": target.inode if full else None,
        "prior_target_create_diagnostic": (
            None
            if target.create_diagnostic is None
            else dict(target.create_diagnostic)
        ),
        "manager_stop_result": _bounded_process_result_fact(
            manager_stop_result
        ),
        "manager_stop_requested": manager_stop_requested,
        "manager_poll_count": manager_poll_count,
        "last_manager_properties": (
            None
            if last_manager_properties is None
            else dict(last_manager_properties)
        ),
        "manager_implicit_absence_proven": manager_implicit_absence_proven,
        "target_path_absent": target_path_absent,
        "transient_fragment_absent": transient_fragment_absent,
        "transient_fragment_path": transient_fragment_path,
        "transient_fragment_stat_errno": transient_fragment_stat_errno,
        "parent_named_path_observation": (
            None
            if parent_named_path_observation is None
            else dict(parent_named_path_observation)
        ),
        "retained_ofd_detach_fact": (
            None
            if retained_ofd_detach_fact is None
            else dict(retained_ofd_detach_fact)
        ),
        "replacement_detected": replacement_detected,
        "named_path_detached_and_manager_implicit_absence": named_path_detached_and_manager_implicit_absence,
        "posix_inode_unlink_claimed": False,
        "exception_phase": exception_phase,
        "exception_cause": _error_fact(exception_cause),
        "target_removal_error": _error_fact(target_removal_error),
    }
    return _self_id_document(
        TARGET_CLEANUP_DIAGNOSTIC_DOMAIN,
        "target_cleanup_diagnostic_id",
        payload,
    )


def validate_target_cleanup_diagnostic(document: Any) -> dict[str, Any]:
    retained = _validate_self_id(
        document,
        schema=TARGET_CLEANUP_DIAGNOSTIC_SCHEMA,
        identity_field="target_cleanup_diagnostic_id",
        domain=TARGET_CLEANUP_DIAGNOSTIC_DOMAIN,
    )
    if set(retained) != {
        "schema",
        "same_uid_manager_concurrency_policy_id",
        "same_uid_manager_concurrency_policy_status",
        "unconditional_same_uid_replacement_safety_claimed",
        "manager_stop_identity_binding_contract",
        "requested_manager_stop_identity_binding",
        "target_token",
        "target_unit_name",
        "target_cgroup_name",
        "target_membership",
        "target_path",
        "ownership_scope",
        "manager_unit_ownership_acquired",
        "full_target_path_ofd_conformance",
        "target_device",
        "target_inode",
        "prior_target_create_diagnostic",
        "manager_stop_result",
        "manager_stop_requested",
        "manager_poll_count",
        "last_manager_properties",
        "manager_implicit_absence_proven",
        "target_path_absent",
        "transient_fragment_absent",
        "transient_fragment_path",
        "transient_fragment_stat_errno",
        "parent_named_path_observation",
        "retained_ofd_detach_fact",
        "replacement_detected",
        "named_path_detached_and_manager_implicit_absence",
        "posix_inode_unlink_claimed",
        "exception_phase",
        "exception_cause",
        "target_removal_error",
        "target_cleanup_diagnostic_id",
    }:
        _fail("target cleanup diagnostic fields changed")
    full = retained["full_target_path_ofd_conformance"]
    policy_join = _same_uid_manager_concurrency_policy_join()
    if (
        any(retained[key] != value for key, value in policy_join.items())
        or retained["manager_stop_identity_binding_contract"]
        != MANAGER_STOP_IDENTITY_BINDING
        or retained["target_token"] != TARGET_TOKEN
        or retained["target_unit_name"] != TARGET_SERVICE_UNIT_NAME
        or retained["target_cgroup_name"] != TARGET_CGROUP_NAME
        or type(retained["target_membership"]) is not str
        or not retained["target_membership"].startswith("/")
        or type(retained["target_path"]) is not str
        or not retained["target_path"].endswith("/" + TARGET_CGROUP_NAME)
        or retained["manager_unit_ownership_acquired"] is not True
        or type(full) is not bool
    ):
        _fail("target cleanup diagnostic lost its unit ownership")
    prior = validate_target_create_diagnostic(
        retained["prior_target_create_diagnostic"]
    )
    if (
        prior["manager_unit_ownership_acquired"] is not True
        or prior["target_token"] != retained["target_token"]
        or prior["target_unit_name"] != retained["target_unit_name"]
        or prior["target_cgroup_name"] != retained["target_cgroup_name"]
        or prior["target_membership"] != retained["target_membership"]
    ):
        _fail("target cleanup lost its prior create diagnostic join")
    if full:
        if (
            retained["ownership_scope"] != "UNIT_PATH_OFD"
            or type(retained["target_device"]) is not int
            or retained["target_device"] < 0
            or type(retained["target_inode"]) is not int
            or retained["target_inode"] <= 0
            or prior["full_target_path_ofd_conformance"] is not True
            or prior["target_device"] != retained["target_device"]
            or prior["target_inode"] != retained["target_inode"]
        ):
            _fail("full target cleanup identity fields changed")
    elif (
        retained["ownership_scope"] != "UNIT_ONLY"
        or retained["target_device"] is not None
        or retained["target_inode"] is not None
        or prior["full_target_path_ofd_conformance"] is not False
        or prior["exception_phase"] is None
    ):
        _fail("unit-only target cleanup identity fields changed")
    stop_result = _validate_bounded_process_result_fact(
        retained["manager_stop_result"]
    )
    poll_count = retained["manager_poll_count"]
    stop_requested = retained["manager_stop_requested"]
    expected_requested_binding = (
        MANAGER_STOP_IDENTITY_BINDING
        if stop_requested is True
        else MANAGER_STOP_NOT_DISPATCHED
    )
    if (
        type(stop_requested) is not bool
        or retained["requested_manager_stop_identity_binding"]
        != expected_requested_binding
        or type(poll_count) is not int
        or not 0 <= poll_count <= TARGET_MANAGER_MAX_POLLS
    ):
        _fail("target cleanup stop/poll boundary changed")
    exact_stop = _exact_target_manager_result(
        stop_result, argv_key="stop_argv", require_empty_stdout=True
    )
    properties = retained["last_manager_properties"]
    if properties is not None and (
        type(properties) is not dict
        or set(properties) != TARGET_MANAGER_ABSENCE_PROPERTY_KEYS
        or any(type(key) is not str or type(value) is not str for key, value in properties.items())
    ):
        _fail("target cleanup final manager properties changed")
    absence = retained["manager_implicit_absence_proven"]
    path_absent = retained["target_path_absent"]
    fragment_absent = retained["transient_fragment_absent"]
    fragment_path = retained["transient_fragment_path"]
    fragment_errno = retained["transient_fragment_stat_errno"]
    parent_observation = _validate_parent_named_path_observation(
        retained["parent_named_path_observation"]
    )
    retained_ofd = _validate_retained_ofd_detach_fact(
        retained["retained_ofd_detach_fact"],
        target_path=retained["target_path"],
        target_device=(retained["target_device"] if full else -1),
        target_inode=(retained["target_inode"] if full else -1),
    )
    # The exact target path was checked above; recompute every retained-OFD
    # predicate here before the outer removal detail joins that same document.
    if retained_ofd is not None:
        expected_suffix = "/" + TARGET_CGROUP_NAME + " (deleted)"
        link = retained_ofd["proc_fd_link"]
        suffix_ok = type(link) is str and link.endswith(expected_suffix)
        conformant = (
            retained_ofd["device"] == retained["target_device"]
            and retained_ofd["inode"] == retained["target_inode"]
            and stat.S_ISDIR(retained_ofd["mode"])
            and retained_ofd["nlink"] > 0
            and retained_ofd["fstatfs_type"] == CGROUP2_SUPER_MAGIC
            and suffix_ok
            and retained_ofd["deleted_marker"] is True
            and retained_ofd["cgroup_type_errno"] == errno.ENOENT
            and retained_ofd["cgroup_events_errno"] == errno.ENOENT
            and retained_ofd["cgroup_procs_errno"] == errno.ENOENT
        )
        if retained_ofd["conformant"] is not conformant:
            _fail("retained OFD detach lost its cleanup target join")
    if (
        type(absence) is not bool
        or path_absent is not None and type(path_absent) is not bool
        or fragment_absent is not None and type(fragment_absent) is not bool
        or fragment_path is not None
        and (type(fragment_path) is not str or not fragment_path)
        or fragment_errno is not None and (
            type(fragment_errno) is not int or fragment_errno <= 0
        )
        or type(retained["replacement_detected"]) is not bool
        or type(retained["named_path_detached_and_manager_implicit_absence"]) is not bool
        or retained["posix_inode_unlink_claimed"] is not False
    ):
        _fail("target cleanup absence facts changed")
    expected_path_absent = (
        None
        if parent_observation is None
        else parent_observation["name_absent"]
    )
    if path_absent is not expected_path_absent:
        _fail("target cleanup path absence lost its parent-dirfd join")
    if fragment_path is None:
        expected_fragment_absent: bool | None = None
        if fragment_errno is not None:
            _fail("target cleanup fragment errno lacks its exact path")
    else:
        if fragment_path != build_target_lifecycle_contract(os.geteuid())[
            "transient_fragment_path"
        ]:
            _fail("target cleanup fragment path lost its lifecycle join")
        expected_fragment_absent = fragment_errno == errno.ENOENT
    if fragment_absent is not expected_fragment_absent:
        _fail("target cleanup fragment absence lost its stat join")
    expected_manager_absence = (
        properties is not None
        and _target_manager_implicit_absence(properties)
    )
    if absence is not expected_manager_absence:
        _fail("target cleanup manager absence lost its property join")
    replacement = (
        full
        and parent_observation is not None
        and parent_observation["name_present_identity_exact"] is True
        and (
            parent_observation["named_device"],
            parent_observation["named_inode"],
        )
        != (retained["target_device"], retained["target_inode"])
    )
    if retained["replacement_detected"] is not replacement:
        _fail("target cleanup replacement result lost inode replay")
    named_detach = retained[
        "named_path_detached_and_manager_implicit_absence"
    ]
    expected_named_detach = (
        absence is True
        and exact_stop
        and properties is not None
        and _target_manager_implicit_absence(properties)
        and path_absent is True
        and fragment_absent is True
        and fragment_errno == errno.ENOENT
        and parent_observation is not None
        and parent_observation["name_absent"] is True
        and retained["replacement_detected"] is False
        and (
            retained_ofd is not None
            and retained_ofd["conformant"] is True
            if full
            else retained_ofd is None
        )
    )
    if named_detach is not expected_named_detach:
        _fail("target named-detach proof lost its bidirectional joins")
    phase = retained["exception_phase"]
    if phase is not None and phase not in TARGET_CLEANUP_EXCEPTION_PHASES:
        _fail("target cleanup exception phase changed")
    if (phase == "POSTSTOP_REPLACEMENT") is not replacement:
        _fail("target cleanup replacement phase lost its biconditional")
    retained_ofd_stage_reached = (
        full
        and exact_stop
        and expected_manager_absence
        and path_absent is True
        and fragment_absent is True
        and fragment_errno == errno.ENOENT
        and parent_observation is not None
        and parent_observation["name_absent"] is True
        and not replacement
    )
    expected_retained_ofd_failure = (
        retained_ofd_stage_reached
        and (
            retained_ofd is None
            or retained_ofd["conformant"] is False
        )
    )
    if (
        phase == "POSTSTOP_RETAINED_OFD_DETACH"
    ) is not expected_retained_ofd_failure:
        _fail("target cleanup retained-OFD phase lost its biconditional")
    if (
        phase is not None
        and phase != "POSTSTOP_RETAINED_OFD_DETACH"
        and retained_ofd is not None
    ):
        _fail("target cleanup retained-OFD fact escaped its exact phase")
    if (
        retained_ofd is not None
        and retained_ofd["conformant"] is False
        and phase != "POSTSTOP_RETAINED_OFD_DETACH"
    ):
        _fail("nonconformant retained OFD lost its exception phase")
    cause = _validate_error_fact(
        retained["exception_cause"], required=phase is not None
    )
    outer = _validate_error_fact(
        retained["target_removal_error"], required=phase is not None
    )
    if phase is None:
        if (
            absence is not True
            or stop_requested is not True
            or not exact_stop
            or poll_count < 1
            or properties is None
            or not _target_manager_implicit_absence(properties)
            or path_absent is not True
            or fragment_absent is not True
            or named_detach is not True
            or cause != _error_fact(None)
            or outer != _error_fact(None)
        ):
            _fail("successful target cleanup matrix changed")
    else:
        if (
            outer["error_type"] != "TargetRemovalError"
            or not outer["message"]
            or named_detach is not False
        ):
            _fail("failed target cleanup outer error matrix changed")
        expected_outer_message = (
            "owned target pre-stop identity failed"
            if phase == "PRESTOP_IDENTITY"
            else (
                "owned target unit stop subprocess failed"
                if phase == "STOP_SUBPROCESS"
                else (
                    "owned target cleanup failed after bounded name-based "
                    "stop request under declared exclusion"
                )
            )
        )
        cause_number = cause["errno"]
        expected_outer_number = (
            errno.ESTALE
            if phase == "PRESTOP_IDENTITY"
            else (
                cause_number
                if type(cause_number) is int and cause_number > 0
                else errno.EIO
            )
        )
        if (
            outer["errno"] != expected_outer_number
            or outer["message"]
            != f"[Errno {expected_outer_number}] {expected_outer_message}"
        ):
            _fail("target cleanup outer errno/message phase matrix changed")
        if phase == "PRESTOP_IDENTITY":
            if (
                stop_requested is not False
                or stop_result is not None
                or poll_count != 0
                or properties is not None
                or path_absent is not None
                or fragment_absent is not None
                or parent_observation is not None
                or retained_ofd is not None
                or named_detach is not False
            ):
                _fail("pre-stop identity failure matrix changed")
        elif phase == "STOP_SUBPROCESS":
            if (
                stop_requested is not True
                or
                stop_result is not None
                or poll_count != 0
                or properties is not None
                or path_absent is not None
                or fragment_absent is not None
                or parent_observation is not None
                or retained_ofd is not None
                or named_detach is not False
            ):
                _fail("stop-subprocess failure matrix changed")
        elif (
            stop_requested is not True
            or not exact_stop
            or not 1 <= poll_count <= TARGET_MANAGER_MAX_POLLS
        ):
            _fail("post-stop failure lacks its bounded name-stop result")
        if phase == "POSTSTOP_REPLACEMENT" and (
            full is not True
            or properties is None
            or path_absent is not False
            or retained["replacement_detected"] is not True
            or named_detach is not False
        ):
            _fail("post-stop replacement matrix changed")
        if phase == "POSTSTOP_RETAINED_OFD_DETACH" and (
            full is not True
            or properties is None
            or not _target_manager_implicit_absence(properties)
            or path_absent is not True
            or fragment_absent is not True
            or retained_ofd is not None
            and retained_ofd["conformant"] is not False
            or named_detach is not False
        ):
            _fail("post-stop retained-OFD detach matrix changed")
    return retained


def make_target_removal_error(
    *,
    error_number: int,
    message: str,
    cause: BaseException,
    diagnostic_arguments: Mapping[str, Any],
) -> TargetRemovalError:
    error = TargetRemovalError(error_number, message, diagnostic=None)
    diagnostic = build_target_cleanup_diagnostic(
        **dict(diagnostic_arguments),
        exception_cause=cause,
        target_removal_error=error,
    )
    validate_target_cleanup_diagnostic(diagnostic)
    error.diagnostic = diagnostic
    return error


def validate_target_removal_error_join(error: TargetRemovalError) -> None:
    if type(error.diagnostic) is not dict:
        _fail("TargetRemovalError omitted its diagnostic")
    diagnostic = validate_target_cleanup_diagnostic(error.diagnostic)
    if (
        _error_fact(error) != diagnostic["target_removal_error"]
        or _error_fact(error.__cause__) != diagnostic["exception_cause"]
    ):
        _fail("TargetRemovalError errno/message/cause join changed")


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


def _observe_parent_named_path(
    parent_fd: int, name: str
) -> dict[str, Any]:
    """Observe one name through stat, openat, and the retained parent OFD."""

    named: os.stat_result | None = None
    opened: os.stat_result | None = None
    stat_errno: int | None = None
    openat_errno: int | None = None
    descriptor = -1
    try:
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as error:
        stat_errno = error.errno
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        opened = os.fstat(descriptor)
    except OSError as error:
        openat_errno = error.errno
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    inventory = sorted(os.listdir(parent_fd))
    if (
        len(inventory) > 4096
        or inventory != sorted(set(inventory))
        or any(
            type(entry) is not str or not entry or len(entry.encode()) > 255
            for entry in inventory
        )
    ):
        raise OSError(errno.EOVERFLOW, "parent cgroup inventory left its bound")
    absent = (
        stat_errno == errno.ENOENT
        and openat_errno == errno.ENOENT
        and name not in inventory
    )
    present = (
        named is not None
        and opened is not None
        and stat_errno is None
        and openat_errno is None
        and name in inventory
        and (named.st_dev, named.st_ino) == (opened.st_dev, opened.st_ino)
    )
    return {
        "name": name,
        "stat_errno": stat_errno,
        "openat_errno": openat_errno,
        "named_device": None if named is None else named.st_dev,
        "named_inode": None if named is None else named.st_ino,
        "opened_device": None if opened is None else opened.st_dev,
        "opened_inode": None if opened is None else opened.st_ino,
        "parent_inventory": inventory,
        "name_absent": absent,
        "name_present_identity_exact": present,
    }


def _observe_fragment_absence(path: str) -> dict[str, Any]:
    try:
        os.stat(path, follow_symlinks=False)
    except OSError as error:
        return {
            "path": path,
            "stat_errno": error.errno,
            "absent": error.errno == errno.ENOENT,
        }
    return {"path": path, "stat_errno": None, "absent": False}


def _openat_observed_errno(directory_fd: int, name: str) -> int | None:
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory_fd,
        )
    except OSError as error:
        return error.errno
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return None


def _observe_retained_ofd_detach(target: TargetHandle) -> dict[str, Any]:
    opened = os.fstat(target.directory_fd)
    try:
        proc_fd_link = os.readlink(f"/proc/self/fd/{target.directory_fd}")
        proc_fd_link_errno: int | None = None
    except OSError as error:
        proc_fd_link = None
        proc_fd_link_errno = error.errno
    fact = {
        "device": opened.st_dev,
        "inode": opened.st_ino,
        "mode": opened.st_mode,
        "nlink": opened.st_nlink,
        "fstatfs_type": _fstatfs_type_fd(target.directory_fd),
        "proc_fd_link": proc_fd_link,
        "proc_fd_link_errno": proc_fd_link_errno,
        "deleted_marker": (
            proc_fd_link_errno is None
            and proc_fd_link == target.path + " (deleted)"
        ),
        "cgroup_type_errno": _openat_observed_errno(
            target.directory_fd, "cgroup.type"
        ),
        "cgroup_events_errno": _openat_observed_errno(
            target.directory_fd, "cgroup.events"
        ),
        "cgroup_procs_errno": _openat_observed_errno(
            target.directory_fd, "cgroup.procs"
        ),
        "conformant": False,
    }
    fact["conformant"] = (
        fact["device"] == target.device
        and fact["inode"] == target.inode
        and stat.S_ISDIR(fact["mode"])
        and fact["nlink"] > 0
        and fact["fstatfs_type"] == CGROUP2_SUPER_MAGIC
        and fact["deleted_marker"] is True
        and fact["cgroup_type_errno"] == errno.ENOENT
        and fact["cgroup_events_errno"] == errno.ENOENT
        and fact["cgroup_procs_errno"] == errno.ENOENT
    )
    return fact


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

    def _retained_ofd_detach_fact(
        self, target: TargetHandle
    ) -> dict[str, Any]:
        """Read the retained target OFD; isolated fixtures may emulate kernfs."""

        return _observe_retained_ofd_detach(target)

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
            or argv_key == "create_argv"
            and _target_manager_create_job_path(result.stdout) is None
            or argv_key != "create_argv"
            and require_empty_stdout
            and result.stdout
        ):
            raise AuthorityError(
                f"target manager {argv_key} subprocess contract failed"
            )
        return result

    def _target_manager_absence_properties(
        self, service: ServiceHandle, deadline_ns: int
    ) -> dict[str, str]:
        result = self._target_manager_absence_result(service, deadline_ns)
        return _parse_target_manager_properties(
            result.stdout,
            expected_keys=TARGET_MANAGER_ABSENCE_PROPERTY_KEYS,
        )

    def _target_manager_absence_result(
        self, service: ServiceHandle, deadline_ns: int
    ) -> BoundedProcessResult:
        return self._run_target_manager(
            service,
            "absence_show_argv",
            deadline_ns,
            require_empty_stdout=False,
        )

    def _target_manager_active_properties(
        self, service: ServiceHandle, deadline_ns: int
    ) -> dict[str, str]:
        result = self._target_manager_active_result(service, deadline_ns)
        return _parse_target_manager_properties(
            result.stdout,
            expected_keys=TARGET_MANAGER_ACTIVE_PROPERTY_KEYS,
        )

    def _target_manager_active_result(
        self, service: ServiceHandle, deadline_ns: int
    ) -> BoundedProcessResult:
        return self._run_target_manager(
            service,
            "active_show_argv",
            deadline_ns,
            require_empty_stdout=False,
        )

    @staticmethod
    def _expected_memberships(uid: int) -> tuple[str, str, str]:
        app = f"/user.slice/user-{uid}.slice/user@{uid}.service/app.slice"
        source = f"{app}/{SERVICE_UNIT_NAME}"
        # The target deliberately is a direct sibling of the transient
        # service, matching the production birth shape.  The nearest common
        # ancestor is therefore app.slice, whose cgroup.procs write authority
        # is the production birth shape retained through the consumed r4 probe.
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
            "runtime_dir_file_type": stat.S_IFMT(runtime_stat.st_mode),
            "user_bus_device": bus_stat.st_dev,
            "user_bus_inode": bus_stat.st_ino,
            "user_bus_owner_uid": bus_stat.st_uid,
            "user_bus_owner_gid": bus_stat.st_gid,
            "user_bus_mode": stat.S_IMODE(bus_stat.st_mode),
            "user_bus_file_type": stat.S_IFMT(bus_stat.st_mode),
        }
        expected_host_identity = _expected_host_parent_identity_properties(
            host
        )
        identity_mismatches = _property_mismatch_rows(
            expected_host_identity, live_host_values
        )
        identity_cause = (
            None
            if not identity_mismatches
            else OSError(
                errno.ESTALE,
                "host app.slice identity mismatch: "
                + ",".join(row["field"] for row in identity_mismatches),
            )
        )
        identity_diagnostic = (
            build_host_parent_identity_conformance_diagnostic(
                phase="INNER_ACTIVE",
                expected_properties=expected_host_identity,
                observed_properties=live_host_values,
                cause=identity_cause,
            )
        )
        if identity_cause is not None:
            raise HostParentIdentityConformanceError(
                identity_diagnostic
            ) from identity_cause
        app_fd = os.open(
            app_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        try:
            inner_host_snapshot = observe_host_parent_property_snapshot(
                app_fd,
                phase="INNER_ACTIVE",
                app_slice_path=str(app_path),
            )
            host_mismatches = _property_mismatch_rows(
                host["property_snapshot"]["parsed_properties"],
                inner_host_snapshot["parsed_properties"],
            )
            host_cause = (
                None
                if not host_mismatches
                else OSError(
                    errno.ESTALE,
                    "host app.slice property mismatch: "
                    + ",".join(row["field"] for row in host_mismatches),
                )
            )
            host_diagnostic = build_host_parent_conformance_diagnostic(
                phase="INNER_ACTIVE",
                expected_snapshot=host["property_snapshot"],
                observed_snapshot=inner_host_snapshot,
                cause=host_cause,
            )
            if host_cause is not None:
                raise HostParentConformanceError(host_diagnostic) from host_cause
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
            source_result: BoundedProcessResult | None = None
            source_properties: dict[str, str] | None = None
            source_cause: BaseException | None = None
            try:
                source_argv = tuple(invocation["source_active_show_argv"])
                source_result = self.process_adapter.run(
                    source_argv,
                    timeout_seconds=_remaining_timeout_seconds(
                        deadline_ns, cap=TARGET_MANAGER_CALL_TIMEOUT_SECONDS
                    ),
                    stdout_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
                    stderr_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
                    env=invocation["outer_launch_environment"],
                    start_new_session=False,
                )
                if (
                    source_result.argv != source_argv
                    or source_result.returncode != 0
                    or source_result.timed_out
                    or source_result.output_limit_exceeded
                    or source_result.stderr
                ):
                    raise AuthorityError(
                        "source-unit active property show contract failed"
                    )
                source_properties = _parse_target_manager_properties(
                    source_result.stdout,
                    expected_keys=SOURCE_MANAGER_ACTIVE_PROPERTY_KEYS,
                )
                source_mismatches = _property_mismatch_rows(
                    _source_expected_properties(
                        uid=uid, source_membership=source_membership
                    ),
                    source_properties,
                )
                if source_mismatches:
                    raise OSError(
                        errno.EPROTO,
                        "source unit property mismatch: "
                        + ",".join(
                            row["field"] for row in source_mismatches
                        ),
                    )
            except BaseException as error:
                source_cause = error
            source_diagnostic = build_source_unit_conformance_diagnostic(
                uid=uid,
                source_membership=source_membership,
                manager_show_result=source_result,
                observed_properties=source_properties,
                cause=source_cause,
            )
            if source_cause is not None:
                raise SourceUnitConformanceError(
                    source_diagnostic
                ) from source_cause
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
            if not _target_manager_implicit_absence(manager_precreate):
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
                "delegation_enabled_from_outer_context": True,
                "delegated_controllers_from_outer_context": [],
                "fixed_target_absent_before_create": True,
                "target_manager_implicit_absence_before_create": True,
                "target_manager_precreate_properties": manager_precreate,
                "host_parent_identity_conformance_diagnostic": (
                    identity_diagnostic
                ),
                "host_parent_conformance_diagnostic": host_diagnostic,
                "source_unit_conformance_diagnostic": source_diagnostic,
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
        empty_trace = TargetManagerPollTrace()
        precreate_result: BoundedProcessResult | None = None
        precreate_properties: dict[str, str] | None = None
        precreate_manager_implicit_absence: bool | None = None
        precreate_path_absent: bool | None = None
        precreate_fragment_absent: bool | None = None
        precreate_fragment_path: str | None = None
        precreate_fragment_stat_errno: int | None = None
        precreate_parent_stat_errno: int | None = None
        precreate_parent_openat_errno: int | None = None
        precreate_parent_inventory: list[str] | None = None
        manager_precreate_error: BaseException | None = None
        path_precreate_error: BaseException | None = None
        contract: dict[str, Any] | None = None

        # These two observations are intentionally independent.  A failed or
        # unparsable manager show must not erase the simultaneous path-side
        # observation (and vice versa), because either half is useful forensic
        # evidence but neither half alone can authorize ownership.
        try:
            contract = self._target_contract(service)
            absence_argv = tuple(contract["absence_show_argv"])
            precreate_result = self.process_adapter.run(
                absence_argv,
                timeout_seconds=_remaining_timeout_seconds(
                    deadline_ns, cap=TARGET_MANAGER_CALL_TIMEOUT_SECONDS
                ),
                stdout_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
                stderr_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
                env=contract["environment"],
                start_new_session=False,
            )
            if (
                precreate_result.argv != absence_argv
                or precreate_result.returncode != 0
                or precreate_result.timed_out
                or precreate_result.output_limit_exceeded
                or precreate_result.stderr
            ):
                raise AuthorityError(
                    "target manager precreate absence-show contract failed"
                )
            precreate_properties = _parse_target_manager_properties(
                precreate_result.stdout,
                expected_keys=TARGET_MANAGER_ABSENCE_PROPERTY_KEYS,
            )
            precreate_manager_implicit_absence = _target_manager_implicit_absence(
                precreate_properties
            )
            if not precreate_manager_implicit_absence:
                raise OSError(
                    errno.EEXIST,
                    "target manager unit was not absent immediately before create",
                )
        except BaseException as error:
            manager_precreate_error = error

        try:
            named_observation = _observe_parent_named_path(
                service.app_slice_fd, TARGET_CGROUP_NAME
            )
            precreate_path_absent = named_observation["name_absent"]
            precreate_parent_stat_errno = named_observation["stat_errno"]
            precreate_parent_openat_errno = named_observation["openat_errno"]
            precreate_parent_inventory = named_observation["parent_inventory"]
            assert contract is not None
            fragment_observation = _observe_fragment_absence(
                contract["transient_fragment_path"]
            )
            precreate_fragment_path = fragment_observation["path"]
            precreate_fragment_stat_errno = fragment_observation["stat_errno"]
            precreate_fragment_absent = fragment_observation["absent"]
            if not precreate_path_absent or not precreate_fragment_absent:
                path_precreate_error = OSError(
                    errno.EEXIST,
                    "fixed transient slice path or fragment pre-exists",
                )
        except BaseException as error:
            path_precreate_error = error

        if manager_precreate_error is not None or path_precreate_error is not None:
            cause = (
                manager_precreate_error
                if manager_precreate_error is not None
                else path_precreate_error
            )
            assert cause is not None
            error_number = getattr(cause, "errno", None) or errno.EEXIST
            outer = make_target_creation_error(
                error_number=error_number,
                message="target pre-create absence proof failed",
                target=None,
                cause=cause,
                diagnostic_arguments={
                    "target_membership": service.target_membership,
                    "precreate_absence_show_result": precreate_result,
                    "precreate_manager_properties": precreate_properties,
                    "precreate_manager_implicit_absence": (
                        precreate_manager_implicit_absence
                    ),
                    "precreate_target_path_absent": precreate_path_absent,
                    "precreate_transient_fragment_absent": (
                        precreate_fragment_absent
                    ),
                    "precreate_transient_fragment_path": (
                        precreate_fragment_path
                    ),
                    "precreate_transient_fragment_stat_errno": (
                        precreate_fragment_stat_errno
                    ),
                    "precreate_parent_stat_errno": (
                        precreate_parent_stat_errno
                    ),
                    "precreate_parent_openat_errno": (
                        precreate_parent_openat_errno
                    ),
                    "precreate_parent_inventory": precreate_parent_inventory,
                    "manager_create_result": None,
                    "manager_create_job_path": None,
                    "ownership_acquired": False,
                    "trace": empty_trace,
                    "full_target_path_ofd_conformance": False,
                    "target_device": None,
                    "target_inode": None,
                    "exception_phase": "PRECREATE_ABSENCE",
                },
            )
            raise outer from cause

        assert contract is not None

        claimed = TargetHandle(
            directory_fd=-1,
            name=TARGET_CGROUP_NAME,
            path=target_path,
            membership=service.target_membership,
            device=-1,
            inode=-1,
            owned=False,
            manager_created=False,
            identity_continuous=False,
            stop_requested=False,
            manager_implicit_absence_proven=False,
            residual_possible=False,
            named_path_detached_and_manager_implicit_absence=False,
            manager_unit_ownership_acquired=False,
            full_target_path_ofd_conformance=False,
        )
        create_result: BoundedProcessResult | None = None
        create_job_path: str | None = None
        trace = TargetManagerPollTrace()
        conformance_stages = {
            name: False for name in TARGET_CREATE_CONFORMANCE_STAGE_NAMES
        }
        phase = "MANAGER_CREATE"
        try:
            create_argv = tuple(contract["create_argv"])
            create_result = self.process_adapter.run(
                create_argv,
                timeout_seconds=_remaining_timeout_seconds(
                    deadline_ns, cap=TARGET_MANAGER_CALL_TIMEOUT_SECONDS
                ),
                stdout_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
                stderr_cap=TARGET_MANAGER_OUTPUT_CAP_BYTES,
                env=contract["environment"],
                start_new_session=False,
            )
            create_job_path = _target_manager_create_job_path(
                create_result.stdout
            )
            exact_create_result = (
                create_result.argv == create_argv
                and create_result.returncode == 0
                and create_result.timed_out is False
                and create_result.output_limit_exceeded is False
                and create_job_path is not None
                and create_result.stderr == b""
            )
            if not exact_create_result:
                raise AuthorityError(
                    "target manager create subprocess contract failed"
                )

            # This is the exact ownership boundary.  The unique unit name was
            # absent immediately before issuance and its synchronous create
            # returned exactly zero.  No path/OFD or property conformance is
            # claimed yet.
            claimed.manager_created = True
            claimed.manager_unit_ownership_acquired = True
            claimed.owned = True
            claimed.residual_possible = True

            phase = "ACTIVE_CONFORMANCE"
            conformance, trace = poll_target_manager_conformance(
                lambda: self._target_manager_active_result(
                    service, deadline_ns
                ),
                expected_control_group=service.target_membership,
                deadline_ns=deadline_ns,
            )
            properties = dict(conformance.observed_properties)
            conformance_stages["manager_active_properties"] = True

            phase = "TARGET_PATH_OPEN"
            descriptor = os.open(
                TARGET_CGROUP_NAME,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=service.app_slice_fd,
            )
            claimed.directory_fd = descriptor
            conformance_stages["target_path_opened"] = True
            phase = "TARGET_PATH_OFD_CONFORMANCE"
            metadata = os.fstat(descriptor)
            named = os.stat(
                TARGET_CGROUP_NAME,
                dir_fd=service.app_slice_fd,
                follow_symlinks=False,
            )
            target_type = _read_text_at(descriptor, "cgroup.type").strip()
            target_events = dict(
                line.split(" ", 1)
                for line in _read_text_at(
                    descriptor, "cgroup.events"
                ).splitlines()
                if line
            )

            if (
                not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_dev != named.st_dev
                or metadata.st_ino != named.st_ino
                or self._fstatfs_type(descriptor) != CGROUP2_SUPER_MAGIC
                or target_type != "domain"
                or _read_text_at(descriptor, "cgroup.procs").strip()
                or target_events.get("populated") != "0"
            ):
                raise OSError(
                    errno.ESTALE,
                    "manager target unit/path/OFD identity was not continuous",
                )
            conformance_stages["target_path_ofd_identity"] = True

            phase = "TARGET_PERMISSION"
            permission = _open_write_permission(
                Path(service.app_slice_path)
                / TARGET_CGROUP_NAME
                / "cgroup.procs"
            )
            if permission["opened_for_write"] is not True:
                raise OSError(
                    int(permission["errno"] or errno.EACCES),
                    "manager target cgroup.procs is not writable",
                )
            conformance_stages["target_cgroup_procs_write"] = True

            claimed.device = metadata.st_dev
            claimed.inode = metadata.st_ino
            claimed.identity_continuous = True
            claimed.residual_possible = False
            claimed.full_target_path_ofd_conformance = True
            diagnostic = build_target_create_diagnostic(
                target_membership=service.target_membership,
                precreate_absence_show_result=precreate_result,
                precreate_manager_properties=precreate_properties,
                precreate_manager_implicit_absence=precreate_manager_implicit_absence,
                precreate_target_path_absent=precreate_path_absent,
                precreate_transient_fragment_absent=(
                    precreate_fragment_absent
                ),
                precreate_transient_fragment_path=precreate_fragment_path,
                precreate_transient_fragment_stat_errno=(
                    precreate_fragment_stat_errno
                ),
                precreate_parent_stat_errno=precreate_parent_stat_errno,
                precreate_parent_openat_errno=precreate_parent_openat_errno,
                precreate_parent_inventory=precreate_parent_inventory,
                manager_create_result=create_result,
                manager_create_job_path=create_job_path,
                ownership_acquired=True,
                trace=trace,
                conformance_stages=conformance_stages,
                full_target_path_ofd_conformance=True,
                target_device=metadata.st_dev,
                target_inode=metadata.st_ino,
                exception_phase=None,
                exception_cause=None,
                target_creation_error=None,
            )
            validate_target_create_diagnostic(
                diagnostic,
                expected_target_membership=service.target_membership,
            )
            claimed.create_diagnostic = diagnostic
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
                "initial_cgroup_events": target_events,
                "transient_fragment_path": contract[
                    "transient_fragment_path"
                ],
                "manager_create_argv": list(create_result.argv),
                "manager_create_environment": contract["environment"],
                "manager_create_returncode": create_result.returncode,
                "manager_create_job_path": create_job_path,
                "manager_create_stdout": _output_fact(create_result.stdout),
                "manager_create_stderr": _output_fact(create_result.stderr),
                "manager_properties": properties,
                "manager_poll_count": trace.poll_count,
                "manager_owned_lifecycle": True,
                "manager_create_diagnostic": diagnostic,
                "probe_path_deletion_calls": 0,
            }
            return claimed, detail
        except TargetManagerPollFailure as error:
            phase = error.phase
            trace = error.trace
            cause: BaseException = error.cause
            error_number = error.errno or errno.EIO
        except BaseException as error:
            cause = error
            error_number = getattr(error, "errno", None) or errno.EIO

        if claimed.directory_fd >= 0:
            os.close(claimed.directory_fd)
            claimed.directory_fd = -1
        claimed.identity_continuous = False
        claimed.full_target_path_ofd_conformance = False
        claimed.device = -1
        claimed.inode = -1
        claimed.residual_possible = claimed.manager_unit_ownership_acquired
        outer = make_target_creation_error(
            error_number=error_number,
            message=(
                "manager target creation stopped before full path/OFD "
                "conformance"
            ),
            target=claimed,
            cause=cause,
            diagnostic_arguments={
                "target_membership": service.target_membership,
                "precreate_absence_show_result": precreate_result,
                "precreate_manager_properties": precreate_properties,
                "precreate_manager_implicit_absence": precreate_manager_implicit_absence,
                "precreate_target_path_absent": precreate_path_absent,
                "precreate_transient_fragment_absent": (
                    precreate_fragment_absent
                ),
                "precreate_transient_fragment_path": (
                    precreate_fragment_path
                ),
                "precreate_transient_fragment_stat_errno": (
                    precreate_fragment_stat_errno
                ),
                "precreate_parent_stat_errno": precreate_parent_stat_errno,
                "precreate_parent_openat_errno": precreate_parent_openat_errno,
                "precreate_parent_inventory": precreate_parent_inventory,
                "manager_create_result": create_result,
                "manager_create_job_path": create_job_path,
                "ownership_acquired": (
                    claimed.manager_unit_ownership_acquired
                ),
                "trace": trace,
                "conformance_stages": conformance_stages,
                "full_target_path_ofd_conformance": False,
                "target_device": None,
                "target_inode": None,
                "exception_phase": phase,
            },
        )
        claimed.create_diagnostic = dict(outer.diagnostic or {})
        raise outer from cause

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

    def _contain_provisional_clone(
        self,
        *,
        pid: int,
        pidfd: int,
        parent_socket: socket.socket,
        child_socket: socket.socket,
        setup_error: BaseException,
    ) -> CloneProvisionalContainmentError:
        """Kill, bounded-reap, and close a child not yet returned to run_probe."""

        containment_errors: list[BaseException] = []
        # Setup may fail only after the operation deadline has expired.  The
        # unit/outer margins reserve this fixed, independent cleanup grace.
        containment_deadline_ns = (
            time.monotonic_ns()
            + OUTER_TERMINATION_GRACE_SECONDS * 1_000_000_000
        )
        pidfd_signal_error: BaseException | None = None
        pidfd_signal_succeeded = False
        if pidfd >= 0:
            try:
                signal_result = self.libc.syscall(
                    PIDFD_SEND_SIGNAL_SYSCALL_X86_64,
                    pidfd,
                    signal.SIGKILL,
                    0,
                    0,
                )
                if signal_result == 0:
                    pidfd_signal_succeeded = True
                else:
                    signal_errno = ctypes.get_errno()
                    if type(signal_errno) is not int or signal_errno <= 0:
                        signal_errno = errno.EIO
                    pidfd_signal_error = OSError(
                        signal_errno, os.strerror(signal_errno)
                    )
            except BaseException as error:
                pidfd_signal_error = error

        child_reaped = False
        pidfd_reported_absence = (
            isinstance(pidfd_signal_error, OSError)
            and pidfd_signal_error.errno == errno.ESRCH
        )
        if not pidfd_signal_succeeded and not pidfd_reported_absence:
            pid_fallback_safe = False
            while True:
                try:
                    waited, _status = os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    child_reaped = True
                    break
                except InterruptedError:
                    continue
                except OSError as error:
                    if error.errno == errno.ECHILD:
                        child_reaped = True
                    else:
                        if pidfd_signal_error is not None:
                            containment_errors.append(pidfd_signal_error)
                        containment_errors.append(error)
                    break
                except BaseException as error:
                    if pidfd_signal_error is not None:
                        containment_errors.append(pidfd_signal_error)
                    containment_errors.append(error)
                    break
                if waited == pid:
                    child_reaped = True
                elif waited == 0:
                    # Still waitable means this exact direct child owns the PID.
                    pid_fallback_safe = True
                else:
                    containment_errors.append(
                        OSError(errno.ECHILD, "waitpid returned a different child")
                    )
                break
            if pid_fallback_safe:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError as error:
                    if error.errno != errno.ESRCH:
                        if pidfd_signal_error is not None:
                            containment_errors.append(pidfd_signal_error)
                        containment_errors.append(error)
                except BaseException as error:
                    if pidfd_signal_error is not None:
                        containment_errors.append(pidfd_signal_error)
                    containment_errors.append(error)

        while not child_reaped:
            try:
                waited, _status = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                child_reaped = True
                break
            except InterruptedError:
                continue
            except OSError as error:
                if error.errno == errno.ECHILD:
                    child_reaped = True
                else:
                    containment_errors.append(error)
                break
            except BaseException as error:
                containment_errors.append(error)
                break
            if waited == pid:
                child_reaped = True
                break
            if waited != 0:
                containment_errors.append(
                    OSError(errno.ECHILD, "waitpid returned a different child")
                )
                break
            if time.monotonic_ns() >= containment_deadline_ns:
                containment_errors.append(
                    OSError(
                        errno.ETIMEDOUT,
                        "provisional clone child did not reap by deadline",
                    )
                )
                break
            try:
                time.sleep(0.005)
            except BaseException as error:
                containment_errors.append(error)
                break

        resources_closed = True
        for resource in (child_socket, parent_socket):
            try:
                resource.close()
            except BaseException as error:
                containment_errors.append(error)
                resources_closed = False
        if pidfd >= 0:
            try:
                os.close(pidfd)
            except OSError as error:
                if error.errno != errno.EBADF:
                    containment_errors.append(error)
                    resources_closed = False
            except BaseException as error:
                containment_errors.append(error)
                resources_closed = False

        return CloneProvisionalContainmentError(
            setup_error,
            child_pid=pid,
            child_pidfd=pidfd,
            child_reaped=child_reaped,
            resources_closed=resources_closed,
            containment_errors=containment_errors,
        )

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
            try:
                parent_socket.close()
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
            os._exit(127)
        if result < 0:
            error_number = ctypes.get_errno()
            try:
                child_socket.close()
            finally:
                parent_socket.close()
            raise OSError(error_number, os.strerror(error_number))
        pid = int(result)
        pidfd = pidfd_cell.value
        try:
            child_socket.close()
            if pidfd < 0:
                raise OSError(errno.EPROTO, "clone3 omitted CLONE_PIDFD result")
            fcntl.fcntl(pidfd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        except BaseException as setup_error:
            containment_error = self._contain_provisional_clone(
                pid=pid,
                pidfd=pidfd,
                parent_socket=parent_socket,
                child_socket=child_socket,
                setup_error=setup_error,
            )
            cause = (
                containment_error.containment_errors[0]
                if containment_error.containment_errors
                else setup_error
            )
            raise containment_error from cause
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
            or target.manager_unit_ownership_acquired is not True
        ):
            if target is not None:
                target.residual_possible = True
            raise OSError(
                errno.EPERM,
                "manager stop forbidden without exact unique-unit ownership",
            )

        def fail_before_stop(error: BaseException, message: str) -> NoReturn:
            assert target is not None
            target.residual_possible = True
            outer = make_target_removal_error(
                error_number=errno.ESTALE,
                message=message,
                cause=error,
                diagnostic_arguments={
                    "target": target,
                    "manager_stop_result": None,
                    "manager_stop_requested": False,
                    "manager_poll_count": 0,
                    "last_manager_properties": None,
                    "target_path_absent": None,
                    "transient_fragment_absent": None,
                    "transient_fragment_path": None,
                    "transient_fragment_stat_errno": None,
                    "parent_named_path_observation": None,
                    "retained_ofd_detach_fact": None,
                    "replacement_detected": False,
                    "manager_implicit_absence_proven": False,
                    "named_path_detached_and_manager_implicit_absence": False,
                    "exception_phase": "PRESTOP_IDENTITY",
                },
            )
            raise outer from error

        has_full_path_claim = (
            target.full_target_path_ofd_conformance is True
            and target.identity_continuous is True
            and target.directory_fd >= 0
            and target.device >= 0
            and target.inode > 0
        )
        if target.full_target_path_ofd_conformance is not has_full_path_claim:
            error = OSError(
                errno.ESTALE,
                "target path/OFD claim fields are internally inconsistent",
            )
            fail_before_stop(error, "owned target pre-stop identity failed")
        if has_full_path_claim:
            try:
                before_stop = _observe_parent_named_path(
                    service.app_slice_fd, TARGET_CGROUP_NAME
                )
                opened = os.fstat(target.directory_fd)
            except BaseException as error:
                target.identity_continuous = False
                fail_before_stop(error, "owned target pre-stop identity failed")
            if (
                before_stop["name_present_identity_exact"] is not True
                or before_stop["named_device"] != target.device
                or before_stop["named_inode"] != target.inode
                or opened.st_dev != target.device
                or opened.st_ino != target.inode
                or self._fstatfs_type(target.directory_fd)
                != CGROUP2_SUPER_MAGIC
            ):
                target.identity_continuous = False
                error = OSError(
                    errno.ESTALE,
                    "full target path/OFD identity drifted before stop",
                )
                fail_before_stop(error, "owned target pre-stop identity failed")
        elif (
            target.directory_fd != -1
            or target.device != -1
            or target.inode != -1
            or target.identity_continuous is not False
        ):
            error = OSError(
                errno.ESTALE,
                "unit-only target retained an untyped path/OFD claim",
            )
            fail_before_stop(error, "owned target pre-stop identity failed")

        if not has_full_path_claim:
            # A successful StartTransientUnit request proves that the unique
            # name was accepted at that instant, but it does not pin a later
            # same-name instance.  Without a continuous target path/OFD this
            # process has no safe name-based stop authority: the original may
            # already have been collected and replaced.  Leave cleanup to the
            # source unit's BindsTo relationship and fail closed without
            # issuing systemctl stop.
            error = OSError(
                errno.ESTALE,
                "unit-only ownership cannot authorize a later name-based stop",
            )
            fail_before_stop(error, "owned target pre-stop identity failed")

        # The retained cgroup OFD and named inode observe the old path's
        # continuity immediately before this call.  systemctl still addresses
        # the unit by name and is non-atomic with respect to a same-UID manager
        # replacement; that unverified concurrency is an identity-bound claim
        # exclusion, not a safety result.  Property conformance is separate.
        target.stop_requested = True
        try:
            stop_result = self._run_target_manager(
                service,
                "stop_argv",
                deadline_ns,
                require_empty_stdout=True,
            )
        except BaseException as error:
            target.residual_possible = True
            outer = make_target_removal_error(
                error_number=getattr(error, "errno", None) or errno.EIO,
                message="owned target unit stop subprocess failed",
                cause=error,
                diagnostic_arguments={
                    "target": target,
                    "manager_stop_result": None,
                    "manager_stop_requested": True,
                    "manager_poll_count": 0,
                    "last_manager_properties": None,
                    "target_path_absent": None,
                    "transient_fragment_absent": None,
                    "transient_fragment_path": None,
                    "transient_fragment_stat_errno": None,
                    "parent_named_path_observation": None,
                    "retained_ofd_detach_fact": None,
                    "replacement_detected": False,
                    "manager_implicit_absence_proven": False,
                    "named_path_detached_and_manager_implicit_absence": False,
                    "exception_phase": "STOP_SUBPROCESS",
                },
            )
            raise outer from error

        def fail_after_stop(
            error: BaseException,
            *,
            phase: str,
            poll_count: int,
            last_properties: Mapping[str, str] | None,
            path_absent: bool | None,
            fragment_observation: Mapping[str, Any] | None,
            parent_observation: Mapping[str, Any] | None,
            retained_ofd_fact: Mapping[str, Any] | None,
            replacement_detected: bool,
        ) -> NoReturn:
            target.residual_possible = True
            outer = make_target_removal_error(
                error_number=getattr(error, "errno", None) or errno.EIO,
                message=(
                    "owned target cleanup failed after bounded name-based "
                    "stop request under declared exclusion"
                ),
                cause=error,
                diagnostic_arguments={
                    "target": target,
                    "manager_stop_result": stop_result,
                    "manager_stop_requested": True,
                    "manager_poll_count": poll_count,
                    "last_manager_properties": last_properties,
                    "target_path_absent": path_absent,
                    "transient_fragment_absent": (
                        None
                        if fragment_observation is None
                        else fragment_observation["absent"]
                    ),
                    "transient_fragment_path": (
                        None
                        if fragment_observation is None
                        else fragment_observation["path"]
                    ),
                    "transient_fragment_stat_errno": (
                        None
                        if fragment_observation is None
                        else fragment_observation["stat_errno"]
                    ),
                    "parent_named_path_observation": parent_observation,
                    "retained_ofd_detach_fact": retained_ofd_fact,
                    "replacement_detected": replacement_detected,
                    "manager_implicit_absence_proven": (
                        last_properties is not None
                        and _target_manager_implicit_absence(last_properties)
                    ),
                    "named_path_detached_and_manager_implicit_absence": False,
                    "exception_phase": phase,
                },
            )
            raise outer from error

        last_properties: dict[str, str] | None = None
        parent_observation: dict[str, Any] | None = None
        fragment_observation: dict[str, Any] | None = None
        polls = 0
        while polls < TARGET_MANAGER_MAX_POLLS:
            polls += 1
            try:
                last_properties = self._target_manager_absence_properties(
                    service, deadline_ns
                )
            except BaseException as error:
                fail_after_stop(
                    error,
                    phase="POSTSTOP_ABSENCE",
                    poll_count=polls,
                    last_properties=None,
                    path_absent=None,
                    fragment_observation=None,
                    parent_observation=None,
                    retained_ofd_fact=None,
                    replacement_detected=False,
                )
            try:
                parent_observation = _observe_parent_named_path(
                    service.app_slice_fd, TARGET_CGROUP_NAME
                )
                fragment_observation = _observe_fragment_absence(
                    self._target_contract(service)["transient_fragment_path"]
                )
            except BaseException as error:
                fail_after_stop(
                    error,
                    phase="POSTSTOP_ABSENCE",
                    poll_count=polls,
                    last_properties=last_properties,
                    path_absent=None,
                    fragment_observation=None,
                    parent_observation=None,
                    retained_ofd_fact=None,
                    replacement_detected=False,
                )
            path_absent = parent_observation["name_absent"]
            replacement_detected = (
                has_full_path_claim
                and parent_observation["name_present_identity_exact"] is True
                and (
                    parent_observation["named_device"],
                    parent_observation["named_inode"],
                )
                != (target.device, target.inode)
            )
            if replacement_detected:
                target.identity_continuous = False
                error = OSError(
                    errno.ESTALE,
                    "same-name target replacement inode appeared after stop",
                )
                fail_after_stop(
                    error,
                    phase="POSTSTOP_REPLACEMENT",
                    poll_count=polls,
                    last_properties=last_properties,
                    path_absent=False,
                    fragment_observation=fragment_observation,
                    parent_observation=parent_observation,
                    retained_ofd_fact=None,
                    replacement_detected=True,
                )
            if (
                parent_observation["name_absent"] is not True
                and parent_observation["name_present_identity_exact"] is not True
            ):
                error = OSError(
                    errno.ESTALE,
                    "parent-dirfd stat/openat/inventory observation diverged",
                )
                fail_after_stop(
                    error,
                    phase="POSTSTOP_ABSENCE",
                    poll_count=polls,
                    last_properties=last_properties,
                    path_absent=False,
                    fragment_observation=fragment_observation,
                    parent_observation=parent_observation,
                    retained_ofd_fact=None,
                    replacement_detected=False,
                )
            if (
                _target_manager_implicit_absence(last_properties)
                and path_absent
                and fragment_observation["absent"] is True
            ):
                retained_ofd_fact: dict[str, Any] | None = None
                if has_full_path_claim:
                    try:
                        retained_ofd_fact = self._retained_ofd_detach_fact(
                            target
                        )
                    except BaseException as error:
                        target.identity_continuous = False
                        fail_after_stop(
                            error,
                            phase="POSTSTOP_RETAINED_OFD_DETACH",
                            poll_count=polls,
                            last_properties=last_properties,
                            path_absent=True,
                            fragment_observation=fragment_observation,
                            parent_observation=parent_observation,
                            retained_ofd_fact=None,
                            replacement_detected=False,
                        )
                    if retained_ofd_fact["conformant"] is not True:
                        target.identity_continuous = False
                        error = OSError(
                            errno.ESTALE,
                            "retained cgroup OFD did not prove kernfs detach",
                        )
                        fail_after_stop(
                            error,
                            phase="POSTSTOP_RETAINED_OFD_DETACH",
                            poll_count=polls,
                            last_properties=last_properties,
                            path_absent=True,
                            fragment_observation=fragment_observation,
                            parent_observation=parent_observation,
                            retained_ofd_fact=retained_ofd_fact,
                            replacement_detected=False,
                        )
                target.named_path_detached_and_manager_implicit_absence = True
                if has_full_path_claim:
                    os.close(target.directory_fd)
                    target.directory_fd = -1
                target.manager_implicit_absence_proven = True
                target.residual_possible = False
                cleanup_diagnostic = build_target_cleanup_diagnostic(
                    target=target,
                    manager_stop_result=stop_result,
                    manager_stop_requested=True,
                    manager_poll_count=polls,
                    last_manager_properties=last_properties,
                    target_path_absent=True,
                    transient_fragment_absent=True,
                    transient_fragment_path=fragment_observation["path"],
                    transient_fragment_stat_errno=errno.ENOENT,
                    parent_named_path_observation=parent_observation,
                    retained_ofd_detach_fact=retained_ofd_fact,
                    replacement_detected=False,
                    manager_implicit_absence_proven=True,
                    named_path_detached_and_manager_implicit_absence=True,
                    exception_phase=None,
                    exception_cause=None,
                    target_removal_error=None,
                )
                validate_target_cleanup_diagnostic(cleanup_diagnostic)
                return {
                    "removed": True,
                    "already_absent": False,
                    "ownership_scope": (
                        "UNIT_PATH_OFD" if has_full_path_claim else "UNIT_ONLY"
                    ),
                    "manager_unit_ownership_acquired": True,
                    "full_target_path_ofd_conformance": has_full_path_claim,
                    "owned_device": target.device if has_full_path_claim else None,
                    "owned_inode": target.inode if has_full_path_claim else None,
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
                    "manager_implicit_absence_proven": True,
                    "target_path_absent": True,
                    "transient_fragment_absent": True,
                    "transient_fragment_path": fragment_observation["path"],
                    "transient_fragment_stat_errno": errno.ENOENT,
                    "parent_named_path_observation": parent_observation,
                    "retained_ofd_detach_fact": retained_ofd_fact,
                    "replacement_detected": False,
                    "named_path_detached_and_manager_implicit_absence": True,
                    "posix_inode_unlink_claimed": False,
                    "cleanup_diagnostic": cleanup_diagnostic,
                }
            if time.monotonic_ns() >= deadline_ns:
                break
            time.sleep(0.025)
        error = OSError(
            errno.ETIMEDOUT,
            "target stop did not prove implicit manager plus named/fragment absence",
        )
        fail_after_stop(
            error,
            phase="POSTSTOP_ABSENCE",
            poll_count=polls,
            last_properties=last_properties,
            path_absent=path_absent,
            fragment_observation=fragment_observation,
            parent_observation=parent_observation,
            retained_ofd_fact=None,
            replacement_detected=False,
        )
    def target_absent(
        self,
        service: ServiceHandle,
        target: TargetHandle | None,
        deadline_ns: int,
    ) -> dict[str, Any]:
        if target is not None and (
            target.residual_possible is True
            or target.manager_implicit_absence_proven is not True
        ):
            raise OSError(
                errno.ESTALE,
                "target residual is possible despite fixed-name absence",
            )
        properties = self._target_manager_absence_properties(
            service, deadline_ns
        )
        parent_observation = _observe_parent_named_path(
            service.app_slice_fd, TARGET_CGROUP_NAME
        )
        fragment_observation = _observe_fragment_absence(
            self._target_contract(service)["transient_fragment_path"]
        )
        if (
            not _target_manager_implicit_absence(properties)
            or parent_observation["name_absent"] is not True
            or fragment_observation["absent"] is not True
        ):
            raise OSError(
                errno.EEXIST,
                "manager target unit or domain-separated path still exists",
            )
        return {
            "target_absent": True,
            "target_transient_instance_implicit_absence": True,
            "target_path_absent": True,
            "transient_fragment_absent": True,
            "transient_fragment_path": fragment_observation["path"],
            "transient_fragment_stat_errno": errno.ENOENT,
            "parent_named_path_observation": parent_observation,
            "named_path_detached_and_manager_implicit_absence": True,
            "posix_inode_unlink_claimed": False,
            "manager_implicit_absence_proven": True,
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
        "target_transient_instance_implicit_absence",
        "target_path_absent",
        "transient_fragment_absent",
        "transient_fragment_path",
        "transient_fragment_stat_errno",
        "parent_named_path_observation",
        "named_path_detached_and_manager_implicit_absence",
        "posix_inode_unlink_claimed",
        "manager_implicit_absence_proven",
        "manager_properties",
        "manager_lifecycle_authority",
        "probe_path_deletion_calls",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise OSError(errno.EPROTO, "target absence evidence fields changed")
    retained = dict(value)
    if (
        retained["target_absent"] is not True
        or retained["target_transient_instance_implicit_absence"] is not True
        or retained["target_path_absent"] is not True
        or retained["transient_fragment_absent"] is not True
        or retained["transient_fragment_path"]
        != build_target_lifecycle_contract(os.geteuid())[
            "transient_fragment_path"
        ]
        or retained["transient_fragment_stat_errno"] != errno.ENOENT
        or (
            _validate_parent_named_path_observation(
                retained["parent_named_path_observation"]
            )
            or {}
        ).get("name_absent") is not True
        or retained["named_path_detached_and_manager_implicit_absence"] is not True
        or retained["posix_inode_unlink_claimed"] is not False
        or retained["manager_implicit_absence_proven"] is not True
        or type(retained["manager_properties"]) is not dict
        or not _target_manager_implicit_absence(retained["manager_properties"])
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
    full = target.full_target_path_ofd_conformance is True
    try:
        retained = _validate_full_target_removal_detail(
            value,
            target_contract=build_target_lifecycle_contract(os.geteuid()),
            expected_device=target.device if full else None,
            expected_inode=target.inode if full else None,
            expected_target_path=target.path,
            expected_target_membership=target.membership,
            expected_create_diagnostic=target.create_diagnostic,
        )
    except PreflightError as error:
        raise OSError(
            errno.EPROTO, "target manager removal evidence is mistyped"
        ) from error
    if (
        target.manager_created is not True
        or target.manager_unit_ownership_acquired is not True
        or target.stop_requested is not True
        or target.manager_implicit_absence_proven is not True
        or target.residual_possible is not False
        or (
            full
            and (
                target.identity_continuous is not True
                or target.named_path_detached_and_manager_implicit_absence is not True
            )
        )
        or (not full and target.named_path_detached_and_manager_implicit_absence is not True)
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
        or target.manager_unit_ownership_acquired is not True
        or target.full_target_path_ofd_conformance is not True
        or target.identity_continuous is not True
        or target.stop_requested is not True
        or target.manager_implicit_absence_proven is not True
        or target.residual_possible is not False
        or target.named_path_detached_and_manager_implicit_absence is not True
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
        **_same_uid_manager_concurrency_policy_join(),
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
        "requested_manager_stop_identity_binding": MANAGER_STOP_IDENTITY_BINDING,
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
        "target_transient_instance_implicit_absence": True,
        "target_named_path_detached_and_manager_implicit_absence": True,
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
        **_same_uid_manager_concurrency_policy_join(),
        "manager_stop_identity_binding_contract": MANAGER_STOP_IDENTITY_BINDING,
        "requested_manager_stop_identity_binding": (
            MANAGER_STOP_IDENTITY_BINDING
            if derived["target_manager_stop_requested"] is True
            else MANAGER_STOP_NOT_DISPATCHED
        ),
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
        "target_manager_implicit_absence_proven": derived[
            "target_manager_implicit_absence_proven"
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
    target_manager_implicit_absence_proven = False
    service_handles_closed = False
    primary_substage = "INTERNAL"
    primary_error: BaseException | None = None
    attempt_publication = PublicationOwnershipToken(ATTEMPT_NAME)
    receipt_publication: PublicationOwnershipToken | None = None

    def stage(
        name: str, operation: Callable[[], Mapping[str, Any]]
    ) -> dict[str, Any]:
        nonlocal primary_substage, primary_error

        def fail(error: BaseException) -> BaseException:
            nonlocal primary_substage, primary_error
            normalized_error = error
            try:
                if isinstance(error, TargetCreationError):
                    validate_target_creation_error_join(error)
                elif isinstance(error, TargetRemovalError):
                    validate_target_removal_error_join(error)
            except BaseException as validation_error:
                normalized_error = validation_error
            diagnostic = getattr(normalized_error, "diagnostic", None)
            detail = (
                dict(diagnostic)
                if type(diagnostic) is dict
                else build_ordinary_failure_diagnostic(
                    substage=name, error=normalized_error
                )
            )
            records.append(
                _substage_record(
                    len(records), name, "FAILED", detail, normalized_error
                )
            )
            primary_substage = name
            primary_error = normalized_error
            return normalized_error

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
                    and target.manager_unit_ownership_acquired is True
                    and target.full_target_path_ofd_conformance is True
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
            normalized_error = fail(error)
            if normalized_error is not error:
                raise normalized_error from error
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
                and target.manager_unit_ownership_acquired is True
                and target.full_target_path_ofd_conformance is True
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
            normalized_marker = fail(marker)
            if normalized_marker is not marker:
                raise normalized_marker from marker
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
                    len(records),
                    "ATTEMPT_PUBLICATION",
                    "FAILED",
                    build_ordinary_failure_diagnostic(
                        substage="ATTEMPT_PUBLICATION", error=error
                    ),
                    error,
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
                "delegation_enabled": invocation["delegation_enabled"],
                "delegated_controllers": invocation["delegated_controllers"],
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
                or detail.get("target_manager_implicit_absence_before_create") is not True
            ):
                raise OSError(
                    errno.EPROTO,
                    "service inspection did not prove manager and path absence",
                )
            return detail

        stage("SERVICE_PLACEMENT_AND_NCA_PERMISSION", inspect_service)
        target_is_absent = True
        target_manager_implicit_absence_proven = True
        assert service is not None

        def create_target() -> Mapping[str, Any]:
            nonlocal target, target_is_absent
            nonlocal target_manager_implicit_absence_proven
            target_is_absent = False
            target_manager_implicit_absence_proven = False
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
                or target.manager_unit_ownership_acquired is not True
                or target.full_target_path_ofd_conformance is not True
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
        target_manager_implicit_absence_proven = True

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
                    len(records),
                    "RECEIPT_BUILD",
                    "FAILED",
                    build_ordinary_failure_diagnostic(
                        substage="RECEIPT_BUILD", error=error
                    ),
                    error,
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
                    len(records),
                    "RECEIPT_PUBLICATION",
                    "FAILED",
                    build_ordinary_failure_diagnostic(
                        substage="RECEIPT_PUBLICATION", error=error
                    ),
                    error,
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
                        build_ordinary_failure_diagnostic(
                            substage="RECEIPT_PUBLICATION", error=error
                        ),
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
                    len(records),
                    primary_substage,
                    "FAILED",
                    build_ordinary_failure_diagnostic(
                        substage=primary_substage, error=primary_error
                    ),
                    primary_error,
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
                if isinstance(cleanup_error, TargetRemovalError):
                    validate_target_removal_error_join(cleanup_error)
                cleanup_diagnostic = getattr(cleanup_error, "diagnostic", None)
                failure_detail = (
                    dict(cleanup_diagnostic)
                    if type(cleanup_diagnostic) is dict
                    else build_ordinary_failure_diagnostic(
                        substage=name, error=cleanup_error
                    )
                )
                records.append(
                    _substage_record(
                        len(records),
                        name,
                        "FAILED",
                        failure_detail,
                        cleanup_error,
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
            if target_is_absent and target_manager_implicit_absence_proven:
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
                and target.manager_unit_ownership_acquired is True
                and (
                    any(
                        row["status"] == "OK"
                        and row["substage"] == "TARGET_CREATE"
                        for row in records
                    )
                    or isinstance(
                        primary_error,
                        (
                            TargetCreationError,
                            TargetRemovalError,
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
                    target.residual_possible is True
                    or target.manager_implicit_absence_proven is not True
                ):
                    raise OSError(
                        errno.ESTALE,
                        "target manager absence is unproven or residual is possible",
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
            target_manager_implicit_absence_proven = (
                target_is_absent
                and absent_detail is not None
                and absent_detail.get("manager_implicit_absence_proven") is True
            )
            target_is_absent = (
                target_is_absent and target_manager_implicit_absence_proven
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
                            target_manager_implicit_absence_proven
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
