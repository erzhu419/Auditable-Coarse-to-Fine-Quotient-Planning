"""Pure authority documents for the V42 ordinal-2 pre-formal upload.

The large five-control capsule is uploaded to a fresh, abandonable scratch
identity before the one-shot formal activation is published.  This module is
deliberately effect free: it defines the content-addressed plan, the local
attempt that must precede the upload SSH process, and the durable receipt that
selects one exact remote scratch tree for a later formal activation.

Formal activation documents and the effectful receiver live in successor
code.  A pre-formal receipt therefore authorizes no rename to the fixed root,
no systemd unit, and no execution of the trusted bootstrap launcher.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shlex
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = authority.SCHEMA_VERSION
PREFORMAL_UPLOAD_PLAN_SCHEMA = (
    "acfqp.v42_remote_ordinal2_preformal_upload_plan.v42r1"
)
PREFORMAL_UPLOAD_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_preformal_upload_attempt.v42r1"
)
PREFORMAL_UPLOAD_RECEIPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_preformal_upload_receipt.v42r1"
)
PREFORMAL_UPLOAD_OUTCOME_SCHEMA = (
    "acfqp.v42_remote_ordinal2_preformal_upload_outcome.v42r1"
)
PREFORMAL_NETWORK_START_SCHEMA = (
    "acfqp.v42_remote_ordinal2_preformal_network_start.v42r1"
)

PREFORMAL_UPLOAD_PLAN_ID_SENTINEL = "{acfqp_v42_preformal_upload_plan_id}"
PREFORMAL_UPLOAD_ATTEMPT_ID_SENTINEL = (
    "{acfqp_v42_preformal_upload_attempt_id}"
)
PREFORMAL_SCRATCH_PREFIX = ".acfqp-v42-remote-ordinal2-preformal-"
PREFORMAL_LEDGER_STAGE_PREFIX = (
    ".acfqp-v42-remote-ordinal2-transport-ledger-stage-"
)
PREFORMAL_LOCAL_CHAIN_ROOT_PREFIX = ".acfqp-v42-local-preformal-chain-"
PREFORMAL_LOCAL_ORDINAL_SLOT_PREFIX = "ordinal-"
FIXED_TRANSPORT_LEDGER_ROOT = authority.REMOTE_ROOT.parent / (
    ".acfqp-v42-remote-ordinal2-transport-ledger"
)
PREFORMAL_LOADER_SOURCE_RELATIVE = "scripts/v42_preformal_upload_loader.py"
PREFORMAL_RECEIVER_SOURCE_RELATIVE = "scripts/v42_preformal_upload_receiver.py"
PREFORMAL_ATTEMPT_NAME = "PREFORMAL_UPLOAD_ATTEMPT.json"
PREFORMAL_PLAN_NAME = "PREFORMAL_UPLOAD_PLAN.json"
PREFORMAL_STREAM_HEADER_NAME = "PREFORMAL_STREAM_HEADER.json"
PREFORMAL_RECEIPT_NAME = "PREFORMAL_UPLOAD_RECEIPT.json"
PREFORMAL_OUTCOME_NAME = "PREFORMAL_UPLOAD_OUTCOME.json"
PREFORMAL_NETWORK_START_NAME = "PREFORMAL_NETWORK_START.json"
PREFORMAL_KNOWN_HOSTS_NAME = "PINNED_KNOWN_HOSTS"

LOCAL_TRANSPORT_PARENT = Path("/home/erzhu419/mine_code")
LOCAL_SSH_EXECUTABLE = "/usr/bin/ssh"
LOCAL_SSH_SHA256 = (
    "a16f755ab475a277cf2569d0fb9a3f74c48d38dfc286dc95282f38522c9f09fe"
)
LOCAL_SSH_BYTE_COUNT = 846_888
LOCAL_SSH_MODE = 0o755
LOCAL_SSH_UID = 0
LOCAL_SSH_GID = 0
LOCAL_SSH_NLINK = 1
LOCAL_SSH_KEYGEN_EXECUTABLE = "/usr/bin/ssh-keygen"
LOCAL_SSH_KEYGEN_SHA256 = (
    "dce0dd73fb8656f918b799158d288d6a826386d603282174e74439314fc66827"
)
LOCAL_SSH_KEYGEN_BYTE_COUNT = 457_152
LOCAL_SSH_KEYGEN_MODE = 0o755
LOCAL_SSH_KEYGEN_UID = 0
LOCAL_SSH_KEYGEN_GID = 0
LOCAL_SSH_KEYGEN_NLINK = 1
LOCAL_IDENTITY_FILE = "/home/erzhu419/.ssh/id_ed25519"
LOCAL_IDENTITY_MODE = 0o600
LOCAL_IDENTITY_UID = 1000
LOCAL_IDENTITY_GID = 1000
LOCAL_IDENTITY_NLINK = 1
LOCAL_IDENTITY_BYTE_COUNT = 411
LOCAL_IDENTITY_PUBLIC_FINGERPRINT = (
    "SHA256:EfN9Om68N5vZ32F7Iy7IE3EQ5WW623rtnbSHWgQhLYw"
)
LOCAL_DISPATCH_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
}
REMOTE_ENDPOINT_HOST = "tf290q6n.zjz-service.cn"
REMOTE_ENDPOINT_PORT = 23035
PINNED_KNOWN_HOSTS_BYTES = (
    b"[tf290q6n.zjz-service.cn]:23035 ssh-ed25519 "
    b"AAAAC3NzaC1lZDI1NTE5AAAAICzyd1TdnWs1sYa80JsYWa374x91e/"
    b"YUv80n0ERWm6P7\n"
)
PINNED_HOST_KEY_FINGERPRINT = (
    "SHA256:JXuWH8T+QZ2lGACDGCfdAk9SnF7LLpH2U3v67lu6ouU"
)
PINNED_KNOWN_HOSTS_SHA256 = (
    "a764658af19a4f082f994c0f35062d47e8abc23510f7a77dfa7f12e2d8c6fec4"
)

REMOTE_PYTHON_INVOCATION = "/usr/bin/python3"
REMOTE_PYTHON_INVOCATION_LINK_TARGET = "python3.12"
REMOTE_PYTHON_REALPATH = "/usr/bin/python3.12"
REMOTE_PYTHON_SHA256 = (
    "1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118"
)
REMOTE_PYTHON_BYTE_COUNT = 8_020_928
REMOTE_PYTHON_VERSION = (3, 12, 3)
REMOTE_BASH_PATH = "/usr/bin/bash"
REMOTE_BASH_SHA256 = (
    "bc5945feb8bd26203ebfafea5ce1878bb2e32cb8fb50ab7ae395cfb1e1aaaef1"
)
REMOTE_BASH_BYTE_COUNT = 1_446_024
REMOTE_BASHRC_PATH = "/home/erzhu419/.bashrc"
REMOTE_BASHRC_SHA256 = (
    "55b107a5fba9cf1017ea3e0c77f3802732f01ba081af275d7f38e74ef0478dde"
)
REMOTE_BASHRC_BYTE_COUNT = 3_804
REMOTE_SUPPLEMENTARY_GROUPS = (4, 24, 27, 30, 46, 100, 114, 1000)
REMOTE_ZERO_CAPABILITY_FIELDS = (
    "CapInh",
    "CapPrm",
    "CapEff",
    "CapAmb",
)

MAXIMUM_CONTROL_BYTES = {
    authority.SOURCE_MANIFEST_NAME: 64 * 1024**2,
    authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME: 4 * 1024**2,
    authority.REMOTE_BOOTSTRAP_PYZ_NAME: 64 * 1024**2,
    authority.SOURCE_CAPSULE_NAME: 2 * 1024**3,
    authority.TRANSPORT_MANIFEST_NAME: 64 * 1024**2,
}
MAXIMUM_LOADER_BYTES = 16 * 1024
MAXIMUM_RECEIVER_BYTES = 4 * 1024**2
MAXIMUM_REMOTE_COMMAND_BYTES = 96 * 1024
MAXIMUM_PLAN_BYTES = 256 * 1024
MAXIMUM_ATTEMPT_BYTES = 128 * 1024
MAXIMUM_PREFORMAL_UPLOAD_ATTEMPTS = 8
MAXIMUM_FRAME_HEADER_BYTES = 64 * 1024
MAXIMUM_RECEIPT_STDOUT_BYTES = 256 * 1024
CONTROL_STREAM_CHUNK_BYTE_CAP = 1024 * 1024
MAXIMUM_NONARCHIVE_BUFFER_BYTES = (
    MAXIMUM_PLAN_BYTES
    + MAXIMUM_ATTEMPT_BYTES
    + MAXIMUM_CONTROL_BYTES[authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME]
    + MAXIMUM_CONTROL_BYTES[authority.SOURCE_MANIFEST_NAME]
    + MAXIMUM_CONTROL_BYTES[authority.TRANSPORT_MANIFEST_NAME]
    + MAXIMUM_CONTROL_BYTES[authority.REMOTE_BOOTSTRAP_PYZ_NAME]
)

PREFORMAL_STREAM_HEADER_SCHEMA = (
    "acfqp.v42_remote_ordinal2_preformal_stream_header.v42r1"
)
PREFORMAL_STREAM_MAGIC = "ACFQP_V42_PREFORMAL_STREAM_V1"
PREFORMAL_STREAM_FRAME_ORDER = (
    PREFORMAL_PLAN_NAME,
    PREFORMAL_ATTEMPT_NAME,
    authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
    authority.SOURCE_MANIFEST_NAME,
    authority.TRANSPORT_MANIFEST_NAME,
    authority.REMOTE_BOOTSTRAP_PYZ_NAME,
    authority.SOURCE_CAPSULE_NAME,
)

CONTROL_NAMES = tuple(
    sorted(
        (
            authority.SOURCE_MANIFEST_NAME,
            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            authority.REMOTE_BOOTSTRAP_PYZ_NAME,
            authority.SOURCE_CAPSULE_NAME,
            authority.TRANSPORT_MANIFEST_NAME,
        )
    )
)
CONTROL_CREATION_ORDER = (
    authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
    authority.SOURCE_CAPSULE_NAME,
    authority.SOURCE_MANIFEST_NAME,
    authority.TRANSPORT_MANIFEST_NAME,
    authority.REMOTE_BOOTSTRAP_PYZ_NAME,
)
PREFORMAL_OUTCOME_COMPLETE = "COMPLETE_RECEIPT"
PREFORMAL_OUTCOME_ABANDONED_FAILURE = "ABANDONED_FAILURE"
PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS = "ABANDONED_AMBIGUOUS"
PREFORMAL_OUTCOME_CLASSES = (
    PREFORMAL_OUTCOME_COMPLETE,
    PREFORMAL_OUTCOME_ABANDONED_FAILURE,
    PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS,
)
PREFORMAL_ABANDONMENT_REASON_LOCAL = "LOCAL_PRE_NETWORK_FAILURE"
PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS = (
    "POSTNETWORK_WITHOUT_EXACT_COMPLETE_RECEIPT"
)
PREFORMAL_ABANDONMENT_REASON_CODES = (
    PREFORMAL_ABANDONMENT_REASON_LOCAL,
    PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS,
)
REMOTE_SHARED_PARENT_MODE = 0o775
REMOTE_PRIVATE_DIRECTORY_MODE = 0o700
REMOTE_CONTROL_FILE_MODE = 0o400
REMOTE_SHARED_PARENT_PRIMARY_GID_PRINCIPALS = (authority.REMOTE_USER,)
REMOTE_SHARED_PARENT_EXPLICIT_GROUP_MEMBERS: tuple[str, ...] = ()

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_DOMAIN_PREFIX = "acfqp:v42-remote-ordinal2:"


class V42MaterializationTransportError(RuntimeError):
    """The pre-formal transport identity or durable attestation changed."""


def _fail(message: str) -> NoReturn:
    raise V42MaterializationTransportError(message)


def _content_id(domain: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\0" + canonical_json_bytes(payload)
    ).hexdigest()


def _canonical_document(
    raw_or_document: bytes | dict[str, Any], label: str
) -> dict[str, Any]:
    if type(raw_or_document) is bytes:
        try:
            document = loads_canonical_json(raw_or_document)
        except (TypeError, ValueError, UnicodeError) as error:
            raise V42MaterializationTransportError(
                f"{label} is not canonical JSON"
            ) from error
        if canonical_json_bytes(document) != raw_or_document:
            _fail(f"{label} bytes are not canonical")
    elif type(raw_or_document) is dict:
        try:
            document = loads_canonical_json(canonical_json_bytes(raw_or_document))
        except (TypeError, ValueError, UnicodeError) as error:
            raise V42MaterializationTransportError(
                f"{label} is not canonical JSON"
            ) from error
    else:
        _fail(f"{label} changed type")
    if type(document) is not dict:
        _fail(f"{label} is not an object")
    return document


def _hex64(value: object, label: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        _fail(f"{label} is not exact lowercase hex64")
    return value


def _hex40(value: object, label: str) -> str:
    if type(value) is not str or _HEX40.fullmatch(value) is None:
        _fail(f"{label} is not exact lowercase hex40")
    return value


def _artifact_fact(value: object, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"sha256", "byte_count"}:
        _fail(f"{label} schema changed")
    sha256 = _hex64(value.get("sha256"), f"{label} sha256")
    byte_count = value.get("byte_count")
    if type(byte_count) is not int or byte_count <= 0:
        _fail(f"{label} byte count changed")
    return {"sha256": sha256, "byte_count": byte_count}


def _control_facts(value: object) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != len(CONTROL_NAMES):
        _fail("pre-formal control fact count changed")
    result: list[dict[str, Any]] = []
    for expected_name, row in zip(CONTROL_NAMES, value, strict=True):
        if type(row) is not dict or set(row) != {
            "name",
            "sha256",
            "byte_count",
        }:
            _fail("pre-formal control fact schema changed")
        if row.get("name") != expected_name:
            _fail("pre-formal controls are not exact, sorted, and unique")
        byte_count = row.get("byte_count")
        if (
            type(byte_count) is not int
            or byte_count <= 0
            or byte_count > MAXIMUM_CONTROL_BYTES[expected_name]
        ):
            _fail("pre-formal control byte count changed or exceeds role cap")
        result.append(
            {
                "name": expected_name,
                "sha256": _hex64(
                    row.get("sha256"), f"{expected_name} sha256"
                ),
                "byte_count": byte_count,
            }
        )
    return result


def _bounded_raw(value: object, *, maximum: int, label: str) -> bytes:
    if type(value) is not bytes or not value or len(value) > maximum:
        _fail(f"{label} bytes changed type, emptiness, or cap")
    return value


def _verified_control_aggregate(
    value: object,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    if type(value) is not dict or set(value) != set(CONTROL_NAMES):
        _fail("pre-formal control raw inventory is not exact")
    controls = {
        name: _bounded_raw(
            value[name], maximum=MAXIMUM_CONTROL_BYTES[name], label=name
        )
        for name in CONTROL_NAMES
    }
    source = authority.verify_source_manifest_v42r1(
        controls[authority.SOURCE_MANIFEST_NAME]
    )
    transport = authority.verify_transport_manifest_v42r1(
        controls[authority.TRANSPORT_MANIFEST_NAME], source_manifest=source
    )
    local_attempt = authority.verify_local_materialization_attempt_v42r1(
        controls[authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME],
        source_manifest=source,
        transport_manifest=transport,
    )
    archive_raw = controls[authority.SOURCE_CAPSULE_NAME]
    pyz_raw = controls[authority.REMOTE_BOOTSTRAP_PYZ_NAME]
    pyz = transport["remote_bootstrap_pyz_artifact"]
    if (
        hashlib.sha256(archive_raw).hexdigest()
        != transport["source_archive_sha256"]
        or len(archive_raw) != transport["source_archive_byte_count"]
        or hashlib.sha256(pyz_raw).hexdigest() != pyz["pyz_sha256"]
        or len(pyz_raw) != pyz["pyz_byte_count"]
    ):
        _fail("pre-formal archive or pyz bytes differ from the transport manifest")
    facts = [
        {
            "name": name,
            "sha256": hashlib.sha256(controls[name]).hexdigest(),
            "byte_count": len(controls[name]),
        }
        for name in CONTROL_NAMES
    ]
    return source, transport, local_attempt, facts


def _committed_program_artifact(
    *,
    transport_manifest: dict[str, Any],
    relative_path: str,
    raw: object,
    maximum: int,
    label: str,
) -> dict[str, Any]:
    raw = _bounded_raw(raw, maximum=maximum, label=label)
    fact = next(
        (
            row
            for row in transport_manifest["transport_facts"]
            if row["relative_path"] == relative_path
        ),
        None,
    )
    if (
        fact is None
        or fact["byte_count"] != len(raw)
        or fact["sha256"] != hashlib.sha256(raw).hexdigest()
        or authority._git_blob_oid_sha1(raw) != fact["git_blob_oid"]  # noqa: SLF001
    ):
        _fail(f"{label} bytes differ from their committed transport fact")
    return {
        "relative_path": relative_path,
        "git_blob_oid": fact["git_blob_oid"],
        "sha256": fact["sha256"],
        "byte_count": fact["byte_count"],
    }


def _preformal_chain_id(local_materialization_attempt_id: str) -> str:
    return _content_id(
        _DOMAIN_PREFIX + "preformal-upload-chain",
        {
            "local_materialization_attempt_id": _hex64(
                local_materialization_attempt_id,
                "local materialization attempt ID",
            )
        },
    )


def _local_chain_paths(
    *, local_materialization_attempt_id: str, ordinal: int
) -> dict[str, str]:
    if type(ordinal) is not int or not 1 <= ordinal <= MAXIMUM_PREFORMAL_UPLOAD_ATTEMPTS:
        _fail("pre-formal local ordinal slot changed")
    chain_id = _preformal_chain_id(local_materialization_attempt_id)
    chain_root = LOCAL_TRANSPORT_PARENT / (
        PREFORMAL_LOCAL_CHAIN_ROOT_PREFIX + chain_id
    )
    slot_root = chain_root / f"{PREFORMAL_LOCAL_ORDINAL_SLOT_PREFIX}{ordinal:08d}"
    return {
        "chain_id": chain_id,
        "chain_root": str(chain_root),
        "ordinal_slot": str(slot_root),
        "known_hosts": str(slot_root / PREFORMAL_KNOWN_HOSTS_NAME),
        "plan": str(slot_root / PREFORMAL_PLAN_NAME),
        "attempt": str(slot_root / PREFORMAL_ATTEMPT_NAME),
        "stream_header": str(slot_root / PREFORMAL_STREAM_HEADER_NAME),
        "network_start": str(slot_root / PREFORMAL_NETWORK_START_NAME),
        "receipt": str(slot_root / PREFORMAL_RECEIPT_NAME),
        "outcome": str(slot_root / PREFORMAL_OUTCOME_NAME),
    }


def _ssh_client_contract(known_hosts_path: str) -> dict[str, Any]:
    return {
        "ssh_executable": LOCAL_SSH_EXECUTABLE,
        "ssh_executable_node_type": "REGULAR_FILE",
        "ssh_executable_mode": LOCAL_SSH_MODE,
        "ssh_executable_uid": LOCAL_SSH_UID,
        "ssh_executable_gid": LOCAL_SSH_GID,
        "ssh_executable_nlink": LOCAL_SSH_NLINK,
        "ssh_executable_sha256": LOCAL_SSH_SHA256,
        "ssh_executable_byte_count": LOCAL_SSH_BYTE_COUNT,
        "ssh_keygen_executable": LOCAL_SSH_KEYGEN_EXECUTABLE,
        "ssh_keygen_node_type": "REGULAR_FILE",
        "ssh_keygen_mode": LOCAL_SSH_KEYGEN_MODE,
        "ssh_keygen_uid": LOCAL_SSH_KEYGEN_UID,
        "ssh_keygen_gid": LOCAL_SSH_KEYGEN_GID,
        "ssh_keygen_nlink": LOCAL_SSH_KEYGEN_NLINK,
        "ssh_keygen_sha256": LOCAL_SSH_KEYGEN_SHA256,
        "ssh_keygen_byte_count": LOCAL_SSH_KEYGEN_BYTE_COUNT,
        "identity_file": LOCAL_IDENTITY_FILE,
        "identity_node_type": "REGULAR_FILE",
        "identity_mode": LOCAL_IDENTITY_MODE,
        "identity_uid": LOCAL_IDENTITY_UID,
        "identity_gid": LOCAL_IDENTITY_GID,
        "identity_nlink": LOCAL_IDENTITY_NLINK,
        "identity_byte_count": LOCAL_IDENTITY_BYTE_COUNT,
        "identity_public_fingerprint": LOCAL_IDENTITY_PUBLIC_FINGERPRINT,
        "identity_public_derivation_argv": [
            LOCAL_SSH_KEYGEN_EXECUTABLE,
            "-y",
            "-f",
            LOCAL_IDENTITY_FILE,
        ],
        "identity_public_output_byte_cap": 1024,
        "identity_public_derivation_output_encoding": (
            "OPENSSH_PUBLIC_KEY_TYPE_AND_BASE64_BLOB_LINE"
        ),
        "identity_public_trailing_comment_is_non_authoritative": True,
        "identity_public_key_type": "ssh-ed25519",
        "identity_public_blob_byte_count": 51,
        "identity_fingerprint_derivation": (
            "SHA256_PREFIX_PLUS_BASE64_NO_PADDING_OF_OPENSSH_PUBLIC_BLOB"
        ),
        "identity_fingerprint_rederived_immediately_before_marker_and_exec": True,
        "known_hosts_path": known_hosts_path,
        "known_hosts_sha256": PINNED_KNOWN_HOSTS_SHA256,
        "known_hosts_byte_count": len(PINNED_KNOWN_HOSTS_BYTES),
        "pinned_host_key_fingerprint": PINNED_HOST_KEY_FINGERPRINT,
        "endpoint_host": REMOTE_ENDPOINT_HOST,
        "endpoint_port": REMOTE_ENDPOINT_PORT,
        "remote_user": authority.REMOTE_USER,
        "dispatch_environment": LOCAL_DISPATCH_ENVIRONMENT,
        "ssh_child_exact_file_descriptors": [0, 1, 2],
        "ssh_child_stdin_stdout_stderr_must_not_be_tty": True,
        "ssh_child_close_fds_required": True,
        "sender_child_exec_platform": "LINUX_X86_64",
        "sender_child_descriptor_staging": {
            "executable_fd": 3,
            "exec_status_fd": 4,
            "close_range_first_fd": 5,
        },
        "sender_child_direct_syscalls_x86_64": {
            "execveat": 322,
            "close_range": 436,
            "execveat_flags": ["AT_EMPTY_PATH"],
        },
        "sender_parent_sigpipe_ignored_from_last_pre_marker_gate_through_reap": True,
        "sender_blockable_signals_masked_across_fork_and_child_handlers_reset_before_exec": True,
        "sender_python_trace_and_profile_hooks_forbidden_at_every_pre_fork_gate": True,
        "sender_child_clears_inherited_trace_and_profile_hooks_before_close_range": True,
        "sender_python_ctypes_libc_and_kernel_are_external_local_tcb": True,
        "private_key_bytes_or_hash_persisted": False,
        "same_uid_identity_path_replacement_excluded_from_claim": True,
        "same_uid_known_hosts_path_replacement_excluded_from_claim": True,
        "ssh_dynamic_loader_shared_libraries_nss_and_dns_are_external_host_tcb": True,
    }


def _remote_startup_tcb_contract() -> dict[str, Any]:
    return {
        "expected_hostname": authority.REMOTE_HOSTNAME,
        "resuid": [authority.REMOTE_UID] * 3,
        "resgid": [authority.REMOTE_GID] * 3,
        "supplementary_groups": list(REMOTE_SUPPLEMENTARY_GROUPS),
        "linux_capability_hex_by_name": {
            name: "0000000000000000" for name in REMOTE_ZERO_CAPABILITY_FIELDS
        },
        "python_invocation_path": REMOTE_PYTHON_INVOCATION,
        "python_invocation_node_type": "SYMLINK",
        "python_invocation_link_target": REMOTE_PYTHON_INVOCATION_LINK_TARGET,
        "python_invocation_mode": 0o777,
        "python_invocation_uid": 0,
        "python_invocation_gid": 0,
        "python_invocation_nlink": 1,
        "python_realpath": REMOTE_PYTHON_REALPATH,
        "python_realpath_node_type": "REGULAR_FILE",
        "python_realpath_mode": 0o755,
        "python_realpath_uid": 0,
        "python_realpath_gid": 0,
        "python_realpath_nlink": 1,
        "python_realpath_sha256": REMOTE_PYTHON_SHA256,
        "python_realpath_byte_count": REMOTE_PYTHON_BYTE_COUNT,
        "python_version": list(REMOTE_PYTHON_VERSION),
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
        "bash_path": REMOTE_BASH_PATH,
        "bash_node_type": "REGULAR_FILE",
        "bash_mode": 0o755,
        "bash_uid": 0,
        "bash_gid": 0,
        "bash_nlink": 1,
        "bash_sha256": REMOTE_BASH_SHA256,
        "bash_byte_count": REMOTE_BASH_BYTE_COUNT,
        "bashrc_path": REMOTE_BASHRC_PATH,
        "bashrc_node_type": "REGULAR_FILE",
        "bashrc_mode": 0o644,
        "bashrc_uid": authority.REMOTE_UID,
        "bashrc_gid": authority.REMOTE_GID,
        "bashrc_nlink": 1,
        "bashrc_sha256": REMOTE_BASHRC_SHA256,
        "bashrc_byte_count": REMOTE_BASHRC_BYTE_COUNT,
        "user_ssh_rc_state": "ABSENT",
        "system_ssh_rc_state": "ABSENT",
        "environment": {"LC_CTYPE": "C.UTF-8"},
        "exact_live_file_descriptors": [0, 1, 2],
        "stdin_stdout_stderr_must_not_be_tty": True,
        "stdlib_installation_is_external_host_tcb": True,
        "python_binary_hash_does_not_bind_stdlib": True,
        "all_facts_rechecked_before_first_project_namespace_mutation": True,
    }


def _stream_protocol_contract() -> dict[str, Any]:
    return {
        "magic": PREFORMAL_STREAM_MAGIC,
        "magic_encoding": "UTF8_PLUS_NUL",
        "header_schema": PREFORMAL_STREAM_HEADER_SCHEMA,
        "header_length_encoding": "UNSIGNED_BIG_ENDIAN_8_BYTES",
        "header_byte_cap": MAXIMUM_FRAME_HEADER_BYTES,
        "frame_count": len(PREFORMAL_STREAM_FRAME_ORDER),
        "frame_order": list(PREFORMAL_STREAM_FRAME_ORDER),
        "plan_body_byte_cap": MAXIMUM_PLAN_BYTES,
        "attempt_body_byte_cap": MAXIMUM_ATTEMPT_BYTES,
        "nonarchive_buffer_byte_cap": MAXIMUM_NONARCHIVE_BUFFER_BYTES,
        "receiver_source_precedes_magic_and_is_loader_count_delimited": True,
        "all_frame_headers_verified_before_first_project_namespace_mutation": True,
        "archive_is_final_body_and_streamed_with_chunk_cap": True,
        "archive_stream_chunk_byte_cap": CONTROL_STREAM_CHUNK_BYTE_CAP,
        "exact_eof_required_after_final_body": True,
    }


def _authorized_ssh_argv_template(
    *,
    known_hosts_path: str,
    loader_source_raw: bytes,
    receiver_artifact: dict[str, Any],
) -> list[str]:
    loader_source = loader_source_raw.decode("utf-8", errors="strict")
    loader_sha256 = hashlib.sha256(loader_source_raw).hexdigest()
    remote_arguments = [
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-c",
        loader_source,
        "--preformal-upload",
        loader_sha256,
        str(len(loader_source_raw)),
        receiver_artifact["sha256"],
        str(receiver_artifact["byte_count"]),
        PREFORMAL_UPLOAD_PLAN_ID_SENTINEL,
        PREFORMAL_UPLOAD_ATTEMPT_ID_SENTINEL,
    ]
    remote_command = "builtin exec -c " + " ".join(
        shlex.quote(part) for part in remote_arguments
    )
    if len(remote_command.encode("utf-8")) > MAXIMUM_REMOTE_COMMAND_BYTES:
        _fail("pre-formal remote command exceeds its single-argv cap")
    return [
        LOCAL_SSH_EXECUTABLE,
        "-T",
        "-F",
        "/dev/null",
        "-oBatchMode=yes",
        "-oPreferredAuthentications=publickey",
        "-oPasswordAuthentication=no",
        "-oKbdInteractiveAuthentication=no",
        "-oGSSAPIAuthentication=no",
        "-oHostbasedAuthentication=no",
        "-oIdentitiesOnly=yes",
        "-oIdentityAgent=none",
        "-oCertificateFile=none",
        "-oStrictHostKeyChecking=yes",
        "-oCheckHostIP=no",
        "-oCanonicalizeHostname=no",
        "-oHostKeyAlgorithms=ssh-ed25519",
        "-oUpdateHostKeys=no",
        "-oVerifyHostKeyDNS=no",
        f"-oUserKnownHostsFile={known_hosts_path}",
        "-oGlobalKnownHostsFile=/dev/null",
        "-oKnownHostsCommand=none",
        "-oControlMaster=no",
        "-oControlPath=none",
        "-oControlPersist=no",
        "-oProxyCommand=none",
        "-oProxyJump=none",
        "-oClearAllForwardings=yes",
        "-oForwardAgent=no",
        "-oForwardX11=no",
        "-oPermitLocalCommand=no",
        "-oRequestTTY=no",
        "-oConnectionAttempts=1",
        "-oNumberOfPasswordPrompts=0",
        "-oSendEnv=-*",
        "-oStdinNull=no",
        "-i",
        LOCAL_IDENTITY_FILE,
        "-p",
        str(REMOTE_ENDPOINT_PORT),
        "-l",
        authority.REMOTE_USER,
        "--",
        REMOTE_ENDPOINT_HOST,
        remote_command,
    ]


def _validate_exact_ssh_template(
    value: object,
    *,
    known_hosts_path: str,
    loader_source_raw: bytes,
    receiver_artifact: dict[str, Any],
) -> list[str]:
    expected = _authorized_ssh_argv_template(
        known_hosts_path=known_hosts_path,
        loader_source_raw=loader_source_raw,
        receiver_artifact=receiver_artifact,
    )
    if value != expected:
        _fail("pre-formal SSH argv template differs from the sole authority")
    return expected


def _program_artifact(value: object, *, relative_path: str, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "relative_path",
        "git_blob_oid",
        "sha256",
        "byte_count",
    }:
        _fail(f"{label} schema changed")
    if value.get("relative_path") != relative_path:
        _fail(f"{label} relative path changed")
    byte_count = value.get("byte_count")
    maximum = (
        MAXIMUM_LOADER_BYTES
        if relative_path == PREFORMAL_LOADER_SOURCE_RELATIVE
        else MAXIMUM_RECEIVER_BYTES
    )
    if type(byte_count) is not int or byte_count <= 0 or byte_count > maximum:
        _fail(f"{label} byte count changed or exceeds cap")
    return {
        "relative_path": relative_path,
        "git_blob_oid": _hex40(value.get("git_blob_oid"), f"{label} Git blob"),
        "sha256": _hex64(value.get("sha256"), f"{label} sha256"),
        "byte_count": byte_count,
    }


def _loader_source_from_ssh_template(
    value: object, *, receiver_artifact: dict[str, Any]
) -> bytes:
    if type(value) is not list or not value or type(value[-1]) is not str:
        _fail("pre-formal SSH argv template changed type")
    try:
        tokens = shlex.split(value[-1], posix=True)
    except ValueError as error:
        raise V42MaterializationTransportError(
            "pre-formal remote command is not canonical shell syntax"
        ) from error
    if len(tokens) != 16 or tokens[:8] != [
        "builtin",
        "exec",
        "-c",
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-c",
    ]:
        _fail("pre-formal remote command prefix or arity changed")
    loader_source_raw = tokens[8].encode("utf-8", errors="strict")
    expected_tail = [
        "--preformal-upload",
        hashlib.sha256(loader_source_raw).hexdigest(),
        str(len(loader_source_raw)),
        receiver_artifact["sha256"],
        str(receiver_artifact["byte_count"]),
        PREFORMAL_UPLOAD_PLAN_ID_SENTINEL,
        PREFORMAL_UPLOAD_ATTEMPT_ID_SENTINEL,
    ]
    if tokens[9:] != expected_tail:
        _fail("pre-formal remote command anchors changed")
    return loader_source_raw


def materialize_preformal_upload_ssh_argv_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> list[str]:
    plan = verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    result = [
        part.replace(
            PREFORMAL_UPLOAD_PLAN_ID_SENTINEL,
            plan["preformal_upload_plan_id"],
        ).replace(
            PREFORMAL_UPLOAD_ATTEMPT_ID_SENTINEL,
            attempt["preformal_upload_attempt_id"],
        )
        for part in plan["authorized_ssh_argv_template"]
    ]
    if any("{acfqp_v42_" in part for part in result):
        _fail("pre-formal SSH argv retained a transport sentinel")
    return result


def _expected_remote_paths(token: str) -> tuple[str, str]:
    parent = authority.REMOTE_ROOT.parent
    scratch = parent / f"{PREFORMAL_SCRATCH_PREFIX}{token}"
    ledger_stage = parent / f"{PREFORMAL_LEDGER_STAGE_PREFIX}{token}"
    if scratch.parent != authority.REMOTE_ROOT.parent or ledger_stage.parent != scratch.parent:
        _fail("pre-formal remote path parent changed")
    if authority.REMOTE_ROOT in scratch.parents or authority.REMOTE_ROOT in ledger_stage.parents:
        _fail("pre-formal path entered the fixed remote root")
    return str(scratch), str(ledger_stage)


def _verified_transport_context(
    *,
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
) -> dict[str, Any]:
    source, transport, local_attempt, control_facts = (
        _verified_control_aggregate(control_raw_by_name)
    )
    loader_artifact = _committed_program_artifact(
        transport_manifest=transport,
        relative_path=PREFORMAL_LOADER_SOURCE_RELATIVE,
        raw=loader_source_raw,
        maximum=MAXIMUM_LOADER_BYTES,
        label="pre-formal upload loader",
    )
    receiver_artifact = _committed_program_artifact(
        transport_manifest=transport,
        relative_path=PREFORMAL_RECEIVER_SOURCE_RELATIVE,
        raw=receiver_source_raw,
        maximum=MAXIMUM_RECEIVER_BYTES,
        label="pre-formal upload receiver",
    )
    return {
        "source": source,
        "transport": transport,
        "local_attempt": local_attempt,
        "control_facts": control_facts,
        "loader_source_raw": _loader_source_bytes(loader_source_raw),
        "loader_artifact": loader_artifact,
        "receiver_artifact": receiver_artifact,
    }


def _loader_source_bytes(value: object) -> bytes:
    raw = _bounded_raw(
        value, maximum=MAXIMUM_LOADER_BYTES, label="pre-formal upload loader"
    )
    try:
        decoded = raw.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise V42MaterializationTransportError(
            "pre-formal upload loader is not exact UTF-8"
        ) from error
    if (
        "\x00" in decoded
        or PREFORMAL_UPLOAD_PLAN_ID_SENTINEL in decoded
        or PREFORMAL_UPLOAD_ATTEMPT_ID_SENTINEL in decoded
        or "{acfqp_v42_" in decoded
    ):
        _fail("pre-formal upload loader contains a forbidden transport token")
    return raw


def _control_cap_facts() -> list[dict[str, Any]]:
    return [
        {"name": name, "maximum_byte_count": MAXIMUM_CONTROL_BYTES[name]}
        for name in CONTROL_NAMES
    ]


def _local_publication_contract(
    *,
    chain_root: str,
    ordinal_slot: str,
    ordinal: int,
    known_hosts_path: str,
    predecessor_outcome_path: str | None,
) -> dict[str, Any]:
    return {
        "chain_root_path": chain_root,
        "chain_root_creation": (
            "MKDIR_EXCLUSIVE_OR_EXACT_RECOVERY_NOFOLLOW_MODE_0700"
            if ordinal == 1
            else "EXACT_EXISTING_NOFOLLOW_MODE_0700"
        ),
        "ordinal_slot_path": ordinal_slot,
        "ordinal_slot_creation": (
            "MKDIR_EXCLUSIVE_OR_EXACT_PREFIX_RECOVERY_NOFOLLOW_MODE_0700"
        ),
        "ordinal_slot_is_independent_of_upload_token": True,
        "empty_ordinal_slot_is_unclaimed": True,
        "first_durable_plan_selects_ordinal_branch": True,
        "contiguous_ordinal_slots_required": True,
        "exactly_one_plan_allowed_per_ordinal_slot": True,
        "predecessor_outcome_path": predecessor_outcome_path,
        "predecessor_outcome_must_exist_and_be_fsynced_before_successor_slot": (
            ordinal > 1
        ),
        "publication_order": [
            PREFORMAL_PLAN_NAME,
            PREFORMAL_KNOWN_HOSTS_NAME,
            PREFORMAL_ATTEMPT_NAME,
            PREFORMAL_STREAM_HEADER_NAME,
            PREFORMAL_NETWORK_START_NAME,
        ],
        "same_identity_complete_pre_network_prefix_recovery_allowed": True,
        "pre_network_prefix_recovery_forbids_network_start_marker": True,
        "partial_or_corrupt_file_recovery_fails_closed": True,
        "known_hosts_path": known_hosts_path,
        "file_creation": "O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW",
        "file_mode": 0o400,
        "every_file_fsync_required": True,
        "root_fsync_required_after_every_publication": True,
        "parent_fsync_required_after_attempt_publication": True,
        "network_start_marker_is_final_pre_ssh_publication": True,
        "ssh_fork_exec_allowed_only_after_network_start_marker_and_parent_fsync": True,
        "network_start_marker_o_excl_forbids_same_slot_replay": True,
        "complete_postnetwork_publication_order": [
            PREFORMAL_RECEIPT_NAME,
            PREFORMAL_OUTCOME_NAME,
        ],
        "abandoned_postnetwork_publication_order": [PREFORMAL_OUTCOME_NAME],
        "receipt_and_outcome_are_o_excl_mode_0400_and_fsynced": True,
        "ordinal_slot_and_chain_root_fsynced_after_outcome": True,
    }


def _remote_receiver_contract() -> dict[str, Any]:
    return {
        "loader_must_verify_receiver_hash_and_count_before_compile": True,
        "plan_attempt_and_frame_headers_must_verify_before_first_project_namespace_mutation": True,
        "host_startup_tcb_and_exact_fd_set_must_verify_before_first_project_namespace_mutation": True,
        "scratch_and_ledger_must_be_absent_before_creation": True,
        "fixed_remote_root": str(authority.REMOTE_ROOT),
        "fixed_transport_ledger_root": str(FIXED_TRANSPORT_LEDGER_ROOT),
        "fixed_roots_must_be_absent_before_and_after_preformal_upload": True,
        "directory_creation": "MKDIR_EXCLUSIVE_NOFOLLOW_MODE_0700",
        "scratch_first_child_name": authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        "control_creation_order": list(CONTROL_CREATION_ORDER),
        "control_file_creation": "O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW",
        "control_file_mode": 0o400,
        "declared_lengths_must_equal_exact_control_facts": True,
        "frame_header_byte_cap": MAXIMUM_FRAME_HEADER_BYTES,
        "stream_chunk_byte_cap": CONTROL_STREAM_CHUNK_BYTE_CAP,
        "control_hash_count_and_stability_required_before_file_fsync": True,
        "each_control_fsync_required_before_next_control": True,
        "exact_final_inventories_required": True,
        "scratch_ledger_and_shared_parent_fsync_required": True,
        "same_token_retry_forbidden_after_any_remote_mutation": True,
        "success_exit_status": 0,
        "success_stdout_encoding": "ONE_CANONICAL_RECEIPT_JSON_THEN_EOF",
        "success_stdout_byte_cap": MAXIMUM_RECEIPT_STDOUT_BYTES,
        "success_stdout_extra_bytes_forbidden": True,
        "stderr_is_diagnostic_and_never_completion_authority": True,
        "complete_requires_exit_zero_exact_receipt_eof_and_contextual_verification": True,
        "postnetwork_nonzero_truncated_extra_or_missing_receipt_is_ambiguous": True,
        "typed_remote_failure_terminal_is_defined": False,
    }


def _program_artifact_from_embedded_loader(
    value: object, *, ssh_template: object, receiver_artifact: dict[str, Any]
) -> tuple[dict[str, Any], bytes]:
    artifact = _program_artifact(
        value,
        relative_path=PREFORMAL_LOADER_SOURCE_RELATIVE,
        label="loader artifact",
    )
    raw = _loader_source_bytes(
        _loader_source_from_ssh_template(
            ssh_template, receiver_artifact=receiver_artifact
        )
    )
    expected = {
        "relative_path": PREFORMAL_LOADER_SOURCE_RELATIVE,
        "git_blob_oid": authority._git_blob_oid_sha1(raw),  # noqa: SLF001
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
    }
    if artifact != expected:
        _fail("embedded loader bytes differ from the loader artifact")
    return artifact, raw


def _plan_document_from_normalized(
    *,
    source_commit: str,
    source_tree: str,
    source_manifest_id: str,
    transport_manifest_id: str,
    local_materialization_attempt_id: str,
    control_facts: list[dict[str, Any]],
    loader_artifact: dict[str, Any],
    loader_source_raw: bytes,
    receiver_artifact: dict[str, Any],
    upload_token: str,
    previous_outcome: dict[str, Any] | None,
) -> dict[str, Any]:
    source_commit = _hex40(source_commit, "source commit")
    source_tree = _hex40(source_tree, "source tree")
    source_manifest_id = _hex64(source_manifest_id, "source manifest ID")
    transport_manifest_id = _hex64(
        transport_manifest_id, "transport manifest ID"
    )
    local_materialization_attempt_id = _hex64(
        local_materialization_attempt_id, "local materialization attempt ID"
    )
    normalized_control_facts = _control_facts(control_facts)
    loader_artifact = _program_artifact(
        loader_artifact,
        relative_path=PREFORMAL_LOADER_SOURCE_RELATIVE,
        label="loader artifact",
    )
    receiver_artifact = _program_artifact(
        receiver_artifact,
        relative_path=PREFORMAL_RECEIVER_SOURCE_RELATIVE,
        label="receiver artifact",
    )
    loader_source_raw = _loader_source_bytes(loader_source_raw)
    upload_token = _hex64(upload_token, "pre-formal upload token")
    if previous_outcome is None:
        ordinal = 1
        previous_outcome_id = None
        upload_token_history = [upload_token]
    else:
        previous_outcome = _verify_preformal_upload_outcome_structure_v42r1(
            previous_outcome
        )
        if (
            previous_outcome["outcome_class"]
            not in {
                PREFORMAL_OUTCOME_ABANDONED_FAILURE,
                PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS,
            }
            or previous_outcome["successor_plan_allowed"] is not True
        ):
            _fail("only an abandoned pre-formal outcome may have a successor")
        for key, expected in (
            ("source_commit", source_commit),
            ("source_tree", source_tree),
            ("source_manifest_id", source_manifest_id),
            ("transport_manifest_id", transport_manifest_id),
            (
                "local_materialization_attempt_id",
                local_materialization_attempt_id,
            ),
        ):
            if previous_outcome[key] != expected:
                _fail("pre-formal successor changed its verified control lineage")
        if upload_token in previous_outcome["upload_token_history"]:
            _fail("pre-formal successor reused an earlier upload token")
        ordinal = previous_outcome["preformal_upload_ordinal"] + 1
        if ordinal > MAXIMUM_PREFORMAL_UPLOAD_ATTEMPTS:
            _fail("pre-formal upload retry budget exhausted")
        previous_outcome_id = previous_outcome["preformal_upload_outcome_id"]
        upload_token_history = [
            *previous_outcome["upload_token_history"],
            upload_token,
        ]
    scratch_root, ledger_stage_root = _expected_remote_paths(upload_token)
    local_paths = _local_chain_paths(
        local_materialization_attempt_id=local_materialization_attempt_id,
        ordinal=ordinal,
    )
    known_hosts_path = local_paths["known_hosts"]
    predecessor_outcome_path = (
        None
        if previous_outcome is None
        else previous_outcome["local_outcome_path"]
    )
    ssh_template = _authorized_ssh_argv_template(
        known_hosts_path=known_hosts_path,
        loader_source_raw=loader_source_raw,
        receiver_artifact=receiver_artifact,
    )
    if (
        sum(part.count(PREFORMAL_UPLOAD_PLAN_ID_SENTINEL) for part in ssh_template)
        != 1
        or sum(
            part.count(PREFORMAL_UPLOAD_ATTEMPT_ID_SENTINEL)
            for part in ssh_template
        )
        != 1
    ):
        _fail("pre-formal SSH argv sentinel multiplicity changed")
    payload = {
        "schema": PREFORMAL_UPLOAD_PLAN_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "source_manifest_id": source_manifest_id,
        "transport_manifest_id": transport_manifest_id,
        "local_materialization_attempt_id": local_materialization_attempt_id,
        "preformal_upload_ordinal": ordinal,
        "previous_preformal_upload_outcome_id": previous_outcome_id,
        "previous_preformal_upload_outcome": previous_outcome,
        "upload_token": upload_token,
        "upload_token_history": upload_token_history,
        "local_transport_parent": str(LOCAL_TRANSPORT_PARENT),
        "preformal_upload_chain_id": local_paths["chain_id"],
        "local_chain_root": local_paths["chain_root"],
        "local_ordinal_slot": local_paths["ordinal_slot"],
        "local_plan_path": local_paths["plan"],
        "local_attempt_path": local_paths["attempt"],
        "local_stream_header_path": local_paths["stream_header"],
        "local_network_start_path": local_paths["network_start"],
        "local_receipt_path": local_paths["receipt"],
        "local_outcome_path": local_paths["outcome"],
        "local_known_hosts_path": known_hosts_path,
        "remote_target_alias": authority.REMOTE_HOST_ALIAS,
        "expected_remote_hostname": authority.REMOTE_HOSTNAME,
        "fixed_remote_root": str(authority.REMOTE_ROOT),
        "fixed_transport_ledger_root": str(FIXED_TRANSPORT_LEDGER_ROOT),
        "preformal_scratch_root": scratch_root,
        "preformal_ledger_stage_root": ledger_stage_root,
        "control_facts": normalized_control_facts,
        "control_byte_caps": _control_cap_facts(),
        "expected_total_control_bytes": sum(
            fact["byte_count"] for fact in normalized_control_facts
        ),
        "scratch_first_child_name": authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        "control_creation_order": list(CONTROL_CREATION_ORDER),
        "loader_artifact": loader_artifact,
        "receiver_artifact": receiver_artifact,
        "ssh_client_contract": _ssh_client_contract(known_hosts_path),
        "authorized_ssh_argv_template": ssh_template,
        "local_publication_contract": _local_publication_contract(
            chain_root=local_paths["chain_root"],
            ordinal_slot=local_paths["ordinal_slot"],
            ordinal=ordinal,
            known_hosts_path=known_hosts_path,
            predecessor_outcome_path=predecessor_outcome_path,
        ),
        "stream_protocol_contract": _stream_protocol_contract(),
        "remote_startup_tcb_contract": _remote_startup_tcb_contract(),
        "remote_receiver_contract": _remote_receiver_contract(),
        "contextual_control_join_required_for_effectful_authorization": True,
        "preformal_identity_is_not_formal_execution_authority": True,
        "scratch_abandonment_requires_a_new_upload_token": True,
        "fixed_remote_root_effect_authorized": False,
        "systemd_effect_authorized": False,
        "trusted_bootstrap_effect_authorized": False,
    }
    return {
        **payload,
        "preformal_upload_plan_id": _content_id(
            _DOMAIN_PREFIX + "preformal-upload-plan", payload
        ),
    }


def _plan_from_context(
    *, context: dict[str, Any], upload_token: str, previous_outcome: dict[str, Any] | None
) -> dict[str, Any]:
    source = context["source"]
    transport = context["transport"]
    local_attempt = context["local_attempt"]
    return _plan_document_from_normalized(
        source_commit=source["source_commit"],
        source_tree=source["source_tree"],
        source_manifest_id=source["source_manifest_id"],
        transport_manifest_id=transport["transport_manifest_id"],
        local_materialization_attempt_id=local_attempt[
            "local_materialization_attempt_id"
        ],
        control_facts=context["control_facts"],
        loader_artifact=context["loader_artifact"],
        loader_source_raw=context["loader_source_raw"],
        receiver_artifact=context["receiver_artifact"],
        upload_token=upload_token,
        previous_outcome=previous_outcome,
    )


def _plan_matches_context(plan: dict[str, Any], context: dict[str, Any]) -> None:
    source = context["source"]
    transport = context["transport"]
    local_attempt = context["local_attempt"]
    expected = {
        "source_commit": source["source_commit"],
        "source_tree": source["source_tree"],
        "source_manifest_id": source["source_manifest_id"],
        "transport_manifest_id": transport["transport_manifest_id"],
        "local_materialization_attempt_id": local_attempt[
            "local_materialization_attempt_id"
        ],
        "control_facts": context["control_facts"],
        "loader_artifact": context["loader_artifact"],
        "receiver_artifact": context["receiver_artifact"],
    }
    if any(plan[key] != value for key, value in expected.items()):
        _fail("pre-formal upload plan differs from the verified control context")
    embedded_loader = _loader_source_from_ssh_template(
        plan["authorized_ssh_argv_template"],
        receiver_artifact=context["receiver_artifact"],
    )
    if embedded_loader != context["loader_source_raw"]:
        _fail("pre-formal upload plan embeds a different committed loader")


def _verified_predecessor_chain(
    *, context: dict[str, Any], predecessor_chain: object
) -> list[dict[str, dict[str, Any]]]:
    if (
        type(predecessor_chain) is not list
        or len(predecessor_chain) >= MAXIMUM_PREFORMAL_UPLOAD_ATTEMPTS
    ):
        _fail("pre-formal predecessor chain changed type or exceeded its cap")
    normalized: list[dict[str, dict[str, Any]]] = []
    prior_outcome: dict[str, Any] | None = None
    for index, row in enumerate(predecessor_chain, start=1):
        if type(row) is not dict or set(row) != {"plan", "attempt", "outcome"}:
            _fail("pre-formal predecessor chain row schema changed")
        plan = verify_preformal_upload_plan_v42r1(row.get("plan"))
        _plan_matches_context(plan, context)
        if (
            plan["preformal_upload_ordinal"] != index
            or plan["previous_preformal_upload_outcome"] != prior_outcome
            or plan["previous_preformal_upload_outcome_id"]
            != (
                None
                if prior_outcome is None
                else prior_outcome["preformal_upload_outcome_id"]
            )
        ):
            _fail("pre-formal predecessor chain is not contiguous and exact")
        attempt = verify_preformal_upload_attempt_v42r1(
            row.get("attempt"), plan=plan
        )
        outcome = verify_preformal_upload_outcome_v42r1(
            row.get("outcome"), plan=plan, attempt=attempt
        )
        if outcome["outcome_class"] not in {
            PREFORMAL_OUTCOME_ABANDONED_FAILURE,
            PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS,
        }:
            _fail("a complete pre-formal outcome cannot appear in a successor chain")
        normalized.append(
            {"plan": plan, "attempt": attempt, "outcome": outcome}
        )
        prior_outcome = outcome
    return normalized


def build_preformal_upload_plan_v42r1(
    *,
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    upload_token: str,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    context = _verified_transport_context(
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
    )
    normalized_chain = _verified_predecessor_chain(
        context=context,
        predecessor_chain=[] if predecessor_chain is None else predecessor_chain,
    )
    normalized_previous_outcome = (
        None if not normalized_chain else normalized_chain[-1]["outcome"]
    )
    return _plan_from_context(
        context=context,
        upload_token=upload_token,
        previous_outcome=normalized_previous_outcome,
    )


def verify_preformal_upload_plan_v42r1(
    raw_or_document: bytes | dict[str, Any],
) -> dict[str, Any]:
    """Verify self-contained shape and content identity, not external controls."""

    document = _canonical_document(raw_or_document, "pre-formal upload plan")
    receiver_artifact = _program_artifact(
        document.get("receiver_artifact"),
        relative_path=PREFORMAL_RECEIVER_SOURCE_RELATIVE,
        label="receiver artifact",
    )
    loader_artifact, loader_source_raw = _program_artifact_from_embedded_loader(
        document.get("loader_artifact"),
        ssh_template=document.get("authorized_ssh_argv_template"),
        receiver_artifact=receiver_artifact,
    )
    previous_outcome_value = document.get("previous_preformal_upload_outcome")
    previous_outcome = (
        None
        if previous_outcome_value is None
        else _verify_preformal_upload_outcome_structure_v42r1(
            previous_outcome_value
        )
    )
    expected = _plan_document_from_normalized(
        source_commit=document.get("source_commit"),
        source_tree=document.get("source_tree"),
        source_manifest_id=document.get("source_manifest_id"),
        transport_manifest_id=document.get("transport_manifest_id"),
        local_materialization_attempt_id=document.get(
            "local_materialization_attempt_id"
        ),
        control_facts=document.get("control_facts"),
        loader_artifact=loader_artifact,
        loader_source_raw=loader_source_raw,
        receiver_artifact=receiver_artifact,
        upload_token=document.get("upload_token"),
        previous_outcome=previous_outcome,
    )
    if document != expected:
        _fail("pre-formal upload plan identity changed")
    return document


def verify_preformal_upload_plan_against_controls_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_v42r1(raw_or_document)
    context = _verified_transport_context(
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
    )
    _plan_matches_context(plan, context)
    normalized_chain = _verified_predecessor_chain(
        context=context,
        predecessor_chain=[] if predecessor_chain is None else predecessor_chain,
    )
    if len(normalized_chain) != plan["preformal_upload_ordinal"] - 1:
        _fail("contextual verification did not receive the complete predecessor chain")
    normalized_outcome = (
        None if not normalized_chain else normalized_chain[-1]["outcome"]
    )
    if normalized_outcome != plan["previous_preformal_upload_outcome"]:
        _fail("plan embeds a different predecessor chain head")
    return plan


def _attempt_from_verified_plan(plan: dict[str, Any]) -> dict[str, Any]:
    plan_raw = canonical_json_bytes(plan)
    if len(plan_raw) > MAXIMUM_PLAN_BYTES:
        _fail("pre-formal upload plan exceeds the wire body cap")
    payload = {
        "schema": PREFORMAL_UPLOAD_ATTEMPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
        "preformal_upload_plan_byte_count": len(plan_raw),
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "local_materialization_attempt_id": plan[
            "local_materialization_attempt_id"
        ],
        "preformal_upload_ordinal": plan["preformal_upload_ordinal"],
        "previous_preformal_upload_outcome_id": plan[
            "previous_preformal_upload_outcome_id"
        ],
        "upload_token": plan["upload_token"],
        "upload_token_history": plan["upload_token_history"],
        "preformal_upload_chain_id": plan["preformal_upload_chain_id"],
        "local_chain_root": plan["local_chain_root"],
        "local_ordinal_slot": plan["local_ordinal_slot"],
        "local_plan_path": plan["local_plan_path"],
        "local_attempt_path": plan["local_attempt_path"],
        "local_stream_header_path": plan["local_stream_header_path"],
        "local_network_start_path": plan["local_network_start_path"],
        "local_receipt_path": plan["local_receipt_path"],
        "local_outcome_path": plan["local_outcome_path"],
        "local_known_hosts_path": plan["local_known_hosts_path"],
        "preformal_scratch_root": plan["preformal_scratch_root"],
        "preformal_ledger_stage_root": plan["preformal_ledger_stage_root"],
        "local_publication_order": plan["local_publication_contract"][
            "publication_order"
        ],
        "known_hosts_sha256": PINNED_KNOWN_HOSTS_SHA256,
        "known_hosts_byte_count": len(PINNED_KNOWN_HOSTS_BYTES),
        "network_effect_permitted_only_after_successful_publication_and_fsync": True,
        "attempt_file_must_be_o_excl_nofollow_mode_0400_and_fsynced": True,
        "network_start_marker_must_be_o_excl_nofollow_mode_0400_and_fsynced": True,
        "ordinal_slot_chain_root_and_parent_must_be_fsynced_before_ssh": True,
        "preformal_network_effect_started_at_publication": False,
        "fixed_remote_root_effect_started": False,
        "systemd_effect_started": False,
        "same_identity_complete_local_prefix_recovery_before_network_start_allowed": True,
        "same_network_attempt_retry_forbidden_after_network_start_publication": True,
        "retry_requires_typed_abandonment_and_new_upload_token": True,
    }
    document = {
        **payload,
        "preformal_upload_attempt_id": _content_id(
            _DOMAIN_PREFIX + "preformal-upload-attempt", payload
        ),
    }
    if len(canonical_json_bytes(document)) > MAXIMUM_ATTEMPT_BYTES:
        _fail("pre-formal upload attempt exceeds the wire body cap")
    return document


def build_preformal_upload_attempt_v42r1(
    *,
    plan: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    return _attempt_from_verified_plan(plan)


def verify_preformal_upload_attempt_v42r1(
    raw_or_document: bytes | dict[str, Any], *, plan: dict[str, Any]
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_v42r1(plan)
    document = _canonical_document(raw_or_document, "pre-formal upload attempt")
    expected = _attempt_from_verified_plan(plan)
    if document != expected:
        _fail("pre-formal upload attempt identity changed")
    return document


def verify_preformal_upload_attempt_against_controls_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    plan: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    return verify_preformal_upload_attempt_v42r1(
        raw_or_document, plan=plan
    )


def _stream_header_from_verified_documents(
    *, plan: dict[str, Any], attempt: dict[str, Any]
) -> dict[str, Any]:
    plan_raw = canonical_json_bytes(plan)
    attempt_raw = canonical_json_bytes(attempt)
    if len(plan_raw) > MAXIMUM_PLAN_BYTES or len(attempt_raw) > MAXIMUM_ATTEMPT_BYTES:
        _fail("pre-formal plan or attempt exceeds its stream frame cap")
    control_by_name = {fact["name"]: fact for fact in plan["control_facts"]}
    frames = [
        {
            "ordinal": 0,
            "role": "PLAN",
            "name": PREFORMAL_PLAN_NAME,
            "sha256": hashlib.sha256(plan_raw).hexdigest(),
            "byte_count": len(plan_raw),
        },
        {
            "ordinal": 1,
            "role": "ATTEMPT",
            "name": PREFORMAL_ATTEMPT_NAME,
            "sha256": hashlib.sha256(attempt_raw).hexdigest(),
            "byte_count": len(attempt_raw),
        },
    ]
    for ordinal, name in enumerate(PREFORMAL_STREAM_FRAME_ORDER[2:], start=2):
        fact = control_by_name[name]
        frames.append(
            {
                "ordinal": ordinal,
                "role": "CONTROL",
                "name": name,
                "sha256": fact["sha256"],
                "byte_count": fact["byte_count"],
            }
        )
    payload = {
        "schema": PREFORMAL_STREAM_HEADER_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "magic": PREFORMAL_STREAM_MAGIC,
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_attempt_id": attempt["preformal_upload_attempt_id"],
        "receiver_artifact": plan["receiver_artifact"],
        "frame_count": len(frames),
        "frames": frames,
        "body_encoding": "EXACT_CONCATENATION_WITHOUT_DELIMITERS",
        "exact_eof_required_after_final_body": True,
    }
    document = {
        **payload,
        "preformal_stream_header_id": _content_id(
            _DOMAIN_PREFIX + "preformal-stream-header", payload
        ),
    }
    if len(canonical_json_bytes(document)) > MAXIMUM_FRAME_HEADER_BYTES:
        _fail("pre-formal stream header exceeds its cap")
    return document


def build_preformal_upload_stream_header_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    return _stream_header_from_verified_documents(plan=plan, attempt=attempt)


def verify_preformal_upload_stream_header_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_v42r1(plan)
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    document = _canonical_document(raw_or_document, "pre-formal stream header")
    expected = _stream_header_from_verified_documents(
        plan=plan, attempt=attempt
    )
    if document != expected:
        _fail("pre-formal stream header changed")
    return document


def _network_start_from_verified_documents(
    *, plan: dict[str, Any], attempt: dict[str, Any]
) -> dict[str, Any]:
    stream_header = _stream_header_from_verified_documents(
        plan=plan, attempt=attempt
    )
    payload = {
        "schema": PREFORMAL_NETWORK_START_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_attempt_id": attempt["preformal_upload_attempt_id"],
        "preformal_stream_header_id": stream_header[
            "preformal_stream_header_id"
        ],
        "preformal_upload_chain_id": plan["preformal_upload_chain_id"],
        "preformal_upload_ordinal": plan["preformal_upload_ordinal"],
        "upload_token": plan["upload_token"],
        "local_chain_root": plan["local_chain_root"],
        "local_ordinal_slot": plan["local_ordinal_slot"],
        "local_network_start_path": plan["local_network_start_path"],
        "published_o_excl_nofollow_mode_0400_and_fsynced_before_ssh": True,
        "same_ordinal_slot_network_replay_forbidden": True,
        "absence_of_complete_receipt_after_publication_is_conservatively_ambiguous": True,
    }
    return {
        **payload,
        "preformal_network_start_id": _content_id(
            _DOMAIN_PREFIX + "preformal-network-start", payload
        ),
    }


def build_preformal_network_start_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    return _network_start_from_verified_documents(plan=plan, attempt=attempt)


def verify_preformal_network_start_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_v42r1(plan)
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    document = _canonical_document(raw_or_document, "pre-formal network start")
    expected = _network_start_from_verified_documents(
        plan=plan, attempt=attempt
    )
    if document != expected:
        _fail("pre-formal network start identity changed")
    return document


def _portable_parent_fact(value: object) -> dict[str, Any]:
    expected = {
        "path": str(authority.REMOTE_ROOT.parent),
        "node_type": "DIRECTORY",
        "mode": REMOTE_SHARED_PARENT_MODE,
        "uid": authority.REMOTE_UID,
        "gid": authority.REMOTE_GID,
        "world_writable": False,
        "primary_gid_principals": list(
            REMOTE_SHARED_PARENT_PRIMARY_GID_PRINCIPALS
        ),
        "explicit_group_members": list(
            REMOTE_SHARED_PARENT_EXPLICIT_GROUP_MEMBERS
        ),
    }
    if value != expected:
        _fail("pre-formal shared parent portable fact changed")
    return expected


def _portable_private_directory_fact(
    value: object, *, path: str, label: str
) -> dict[str, Any]:
    expected = {
        "path": path,
        "node_type": "DIRECTORY",
        "mode": REMOTE_PRIVATE_DIRECTORY_MODE,
        "uid": authority.REMOTE_UID,
        "gid": authority.REMOTE_GID,
    }
    if value != expected:
        _fail(f"{label} portable fact changed")
    return expected


def _portable_control_file_facts(
    value: object, *, plan: dict[str, Any]
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != len(CONTROL_NAMES):
        _fail("pre-formal portable control file fact count changed")
    expected = [
        {
            "name": fact["name"],
            "path": str(Path(plan["preformal_scratch_root"]) / fact["name"]),
            "node_type": "REGULAR_FILE",
            "mode": REMOTE_CONTROL_FILE_MODE,
            "uid": authority.REMOTE_UID,
            "gid": authority.REMOTE_GID,
            "sha256": fact["sha256"],
            "byte_count": fact["byte_count"],
        }
        for fact in plan["control_facts"]
    ]
    if value != expected:
        _fail("pre-formal portable control file facts changed")
    return expected


def _receipt_from_verified_documents(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    scratch_parent_fact: object,
    scratch_root_fact: object,
    ledger_stage_fact: object,
    observed_control_file_facts: object,
) -> dict[str, Any]:
    parent_fact = _portable_parent_fact(scratch_parent_fact)
    scratch_fact = _portable_private_directory_fact(
        scratch_root_fact,
        path=plan["preformal_scratch_root"],
        label="pre-formal scratch root",
    )
    ledger_fact = _portable_private_directory_fact(
        ledger_stage_fact,
        path=plan["preformal_ledger_stage_root"],
        label="pre-formal ledger stage",
    )
    control_file_facts = _portable_control_file_facts(
        observed_control_file_facts, plan=plan
    )
    stream_header = _stream_header_from_verified_documents(
        plan=plan, attempt=attempt
    )
    payload = {
        "schema": PREFORMAL_UPLOAD_RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_attempt_id": attempt["preformal_upload_attempt_id"],
        "preformal_stream_header_id": stream_header[
            "preformal_stream_header_id"
        ],
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "local_materialization_attempt_id": plan[
            "local_materialization_attempt_id"
        ],
        "preformal_upload_ordinal": plan["preformal_upload_ordinal"],
        "previous_preformal_upload_outcome_id": plan[
            "previous_preformal_upload_outcome_id"
        ],
        "upload_token": plan["upload_token"],
        "upload_token_history": plan["upload_token_history"],
        "preformal_upload_chain_id": plan["preformal_upload_chain_id"],
        "local_chain_root": plan["local_chain_root"],
        "local_ordinal_slot": plan["local_ordinal_slot"],
        "local_stream_header_path": plan["local_stream_header_path"],
        "local_receipt_path": plan["local_receipt_path"],
        "local_outcome_path": plan["local_outcome_path"],
        "preformal_scratch_root": plan["preformal_scratch_root"],
        "preformal_ledger_stage_root": plan["preformal_ledger_stage_root"],
        "fixed_transport_ledger_root": plan["fixed_transport_ledger_root"],
        "scratch_parent_fact": parent_fact,
        "scratch_root_fact": scratch_fact,
        "ledger_stage_fact": ledger_fact,
        "expected_control_facts": plan["control_facts"],
        "observed_control_file_facts": control_file_facts,
        "scratch_root_inventory": list(CONTROL_NAMES),
        "ledger_stage_inventory": [],
        "scratch_first_child_name": authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        "control_creation_order": list(CONTROL_CREATION_ORDER),
        "plan_attempt_headers_host_tcb_and_exact_fds_verified_before_first_project_namespace_mutation": True,
        "scratch_and_ledger_were_absent_before_exclusive_creation": True,
        "every_control_created_o_excl_nofollow_at_mode_0400": True,
        "every_control_streamed_with_exact_length_and_role_cap": True,
        "transient_nofollow_stability_and_alias_checks_passed": True,
        "every_control_file_fsynced_before_next_control": True,
        "scratch_root_directory_fsynced": True,
        "ledger_stage_directory_fsynced": True,
        "shared_parent_directory_fsynced": True,
        "portable_named_facts_only": True,
        "local_receipt_must_be_published_o_excl_mode_0400_and_fsynced_before_complete_outcome": True,
        "fixed_remote_root_state": "ABSENT",
        "fixed_transport_ledger_state": "ABSENT",
        "fixed_remote_root_effect_performed": False,
        "systemd_effect_performed": False,
        "trusted_bootstrap_effect_performed": False,
        "remote_parent_and_group_membership_must_be_rechecked_for_formal_activation": True,
        "receipt_selects_scratch_but_does_not_authorize_formal_activation": True,
    }
    return {
        **payload,
        "preformal_upload_receipt_id": _content_id(
            _DOMAIN_PREFIX + "preformal-upload-receipt", payload
        ),
    }


def build_preformal_upload_receipt_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    scratch_parent_fact: dict[str, Any],
    scratch_root_fact: dict[str, Any],
    ledger_stage_fact: dict[str, Any],
    observed_control_file_facts: list[dict[str, Any]],
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    return _receipt_from_verified_documents(
        plan=plan,
        attempt=attempt,
        scratch_parent_fact=scratch_parent_fact,
        scratch_root_fact=scratch_root_fact,
        ledger_stage_fact=ledger_stage_fact,
        observed_control_file_facts=observed_control_file_facts,
    )


def verify_preformal_upload_receipt_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_v42r1(plan)
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    document = _canonical_document(raw_or_document, "pre-formal upload receipt")
    expected = _receipt_from_verified_documents(
        plan=plan,
        attempt=attempt,
        scratch_parent_fact=document.get("scratch_parent_fact"),
        scratch_root_fact=document.get("scratch_root_fact"),
        ledger_stage_fact=document.get("ledger_stage_fact"),
        observed_control_file_facts=document.get(
            "observed_control_file_facts"
        ),
    )
    if document != expected:
        _fail("pre-formal upload receipt identity changed")
    return document


def verify_preformal_upload_receipt_against_controls_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    return verify_preformal_upload_receipt_v42r1(
        raw_or_document, plan=plan, attempt=attempt
    )


def _outcome_payload_from_verified_documents(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    outcome_class: str,
    receipt_id: str | None,
    abandonment_reason_code: str | None,
) -> dict[str, Any]:
    if outcome_class == PREFORMAL_OUTCOME_COMPLETE:
        if receipt_id is None or abandonment_reason_code is not None:
            _fail("complete pre-formal outcome requires only a verified receipt")
        successor_allowed = False
        scratch_abandoned = False
        receipt_observed = True
    elif outcome_class == PREFORMAL_OUTCOME_ABANDONED_FAILURE:
        if (
            receipt_id is not None
            or abandonment_reason_code != PREFORMAL_ABANDONMENT_REASON_LOCAL
        ):
            _fail("only a local pre-network failure may be non-ambiguous")
        successor_allowed = (
            plan["preformal_upload_ordinal"] < MAXIMUM_PREFORMAL_UPLOAD_ATTEMPTS
        )
        scratch_abandoned = True
        receipt_observed = False
    elif outcome_class == PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS:
        if (
            receipt_id is not None
            or abandonment_reason_code
            != PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS
        ):
            _fail("ambiguous pre-formal outcome has an invalid receipt or reason")
        successor_allowed = (
            plan["preformal_upload_ordinal"] < MAXIMUM_PREFORMAL_UPLOAD_ATTEMPTS
        )
        scratch_abandoned = True
        receipt_observed = False
    else:
        _fail("pre-formal upload outcome class changed")
    next_slot = (
        _local_chain_paths(
            local_materialization_attempt_id=plan[
                "local_materialization_attempt_id"
            ],
            ordinal=plan["preformal_upload_ordinal"] + 1,
        )["ordinal_slot"]
        if successor_allowed
        else None
    )
    payload = {
        "schema": PREFORMAL_UPLOAD_OUTCOME_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_attempt_id": attempt["preformal_upload_attempt_id"],
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "local_materialization_attempt_id": plan[
            "local_materialization_attempt_id"
        ],
        "preformal_upload_ordinal": plan["preformal_upload_ordinal"],
        "previous_preformal_upload_outcome_id": plan[
            "previous_preformal_upload_outcome_id"
        ],
        "upload_token": plan["upload_token"],
        "upload_token_history": plan["upload_token_history"],
        "preformal_upload_chain_id": plan["preformal_upload_chain_id"],
        "local_chain_root": plan["local_chain_root"],
        "local_ordinal_slot": plan["local_ordinal_slot"],
        "local_stream_header_path": plan["local_stream_header_path"],
        "local_network_start_path": plan["local_network_start_path"],
        "local_receipt_path": plan["local_receipt_path"],
        "local_outcome_path": plan["local_outcome_path"],
        "local_successor_ordinal_slot": next_slot,
        "outcome_class": outcome_class,
        "preformal_upload_receipt_id": receipt_id,
        "abandonment_reason_code": abandonment_reason_code,
        "complete_receipt_observed_and_verified": receipt_observed,
        "scratch_identity_permanently_abandoned": scratch_abandoned,
        "successor_plan_allowed": successor_allowed,
        "outcome_must_be_published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "complete_outcome_requires_durable_local_receipt_first": (
            outcome_class == PREFORMAL_OUTCOME_COMPLETE
        ),
        "ordinal_slot_and_chain_root_must_be_fsynced_after_outcome": True,
        "same_upload_token_retry_allowed": False,
        "remote_completion_claimed_when_receipt_absent": False,
        "fixed_remote_root_effect_authorized": False,
        "systemd_effect_authorized": False,
        "trusted_bootstrap_effect_authorized": False,
    }
    return {
        **payload,
        "preformal_upload_outcome_id": _content_id(
            _DOMAIN_PREFIX + "preformal-upload-outcome", payload
        ),
    }


def _verify_preformal_upload_outcome_structure_v42r1(
    raw_or_document: bytes | dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "pre-formal upload outcome")
    exact_keys = {
        "schema",
        "schema_version",
        "formal_identity",
        "global_execution_ordinal",
        "preformal_upload_plan_id",
        "preformal_upload_attempt_id",
        "source_commit",
        "source_tree",
        "source_manifest_id",
        "transport_manifest_id",
        "local_materialization_attempt_id",
        "preformal_upload_ordinal",
        "previous_preformal_upload_outcome_id",
        "upload_token",
        "upload_token_history",
        "preformal_upload_chain_id",
        "local_chain_root",
        "local_ordinal_slot",
        "local_stream_header_path",
        "local_network_start_path",
        "local_receipt_path",
        "local_outcome_path",
        "local_successor_ordinal_slot",
        "outcome_class",
        "preformal_upload_receipt_id",
        "abandonment_reason_code",
        "complete_receipt_observed_and_verified",
        "scratch_identity_permanently_abandoned",
        "successor_plan_allowed",
        "outcome_must_be_published_o_excl_nofollow_mode_0400_and_fsynced",
        "complete_outcome_requires_durable_local_receipt_first",
        "ordinal_slot_and_chain_root_must_be_fsynced_after_outcome",
        "same_upload_token_retry_allowed",
        "remote_completion_claimed_when_receipt_absent",
        "fixed_remote_root_effect_authorized",
        "systemd_effect_authorized",
        "trusted_bootstrap_effect_authorized",
        "preformal_upload_outcome_id",
    }
    if set(document) != exact_keys:
        _fail("pre-formal upload outcome schema changed")
    if (
        document.get("schema") != PREFORMAL_UPLOAD_OUTCOME_SCHEMA
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != authority.FORMAL_IDENTITY
        or document.get("global_execution_ordinal")
        != authority.GLOBAL_EXECUTION_ORDINAL
    ):
        _fail("pre-formal upload outcome authority changed")
    for key, label in (
        ("preformal_upload_plan_id", "pre-formal upload plan ID"),
        ("preformal_upload_attempt_id", "pre-formal upload attempt ID"),
        ("source_manifest_id", "source manifest ID"),
        ("transport_manifest_id", "transport manifest ID"),
        (
            "local_materialization_attempt_id",
            "local materialization attempt ID",
        ),
        ("upload_token", "pre-formal upload token"),
        ("preformal_upload_chain_id", "pre-formal upload chain ID"),
        ("preformal_upload_outcome_id", "pre-formal upload outcome ID"),
    ):
        _hex64(document.get(key), label)
    _hex40(document.get("source_commit"), "source commit")
    _hex40(document.get("source_tree"), "source tree")
    ordinal = document.get("preformal_upload_ordinal")
    history = document.get("upload_token_history")
    if (
        type(ordinal) is not int
        or not 1 <= ordinal <= MAXIMUM_PREFORMAL_UPLOAD_ATTEMPTS
        or type(history) is not list
        or len(history) != ordinal
    ):
        _fail("pre-formal upload outcome ordinal or token history changed")
    normalized_history = [
        _hex64(token, "pre-formal upload token history entry")
        for token in history
    ]
    if len(set(normalized_history)) != len(normalized_history) or normalized_history[-1] != document["upload_token"]:
        _fail("pre-formal upload token history is not fresh and ordered")
    local_paths = _local_chain_paths(
        local_materialization_attempt_id=document[
            "local_materialization_attempt_id"
        ],
        ordinal=ordinal,
    )
    if any(
        document.get(key) != expected
        for key, expected in (
            ("preformal_upload_chain_id", local_paths["chain_id"]),
            ("local_chain_root", local_paths["chain_root"]),
            ("local_ordinal_slot", local_paths["ordinal_slot"]),
            ("local_stream_header_path", local_paths["stream_header"]),
            ("local_network_start_path", local_paths["network_start"]),
            ("local_receipt_path", local_paths["receipt"]),
            ("local_outcome_path", local_paths["outcome"]),
        )
    ):
        _fail("pre-formal upload outcome local chain path changed")
    previous_id = document.get("previous_preformal_upload_outcome_id")
    if (ordinal == 1 and previous_id is not None) or (
        ordinal > 1
        and _hex64(previous_id, "previous pre-formal upload outcome ID")
        != previous_id
    ):
        _fail("pre-formal upload outcome predecessor changed")
    outcome_class = document.get("outcome_class")
    receipt_id = document.get("preformal_upload_receipt_id")
    reason = document.get("abandonment_reason_code")
    if outcome_class == PREFORMAL_OUTCOME_COMPLETE:
        if receipt_id is None:
            _fail("complete pre-formal outcome omitted its receipt")
        _hex64(receipt_id, "pre-formal upload receipt ID")
    elif receipt_id is not None:
        _fail("abandoned pre-formal outcome unexpectedly names a receipt")
    shadow_plan = {
        "preformal_upload_plan_id": document["preformal_upload_plan_id"],
        "source_commit": document["source_commit"],
        "source_tree": document["source_tree"],
        "source_manifest_id": document["source_manifest_id"],
        "transport_manifest_id": document["transport_manifest_id"],
        "local_materialization_attempt_id": document[
            "local_materialization_attempt_id"
        ],
        "preformal_upload_ordinal": ordinal,
        "previous_preformal_upload_outcome_id": previous_id,
        "upload_token": document["upload_token"],
        "upload_token_history": normalized_history,
        "preformal_upload_chain_id": local_paths["chain_id"],
        "local_chain_root": local_paths["chain_root"],
        "local_ordinal_slot": local_paths["ordinal_slot"],
        "local_stream_header_path": local_paths["stream_header"],
        "local_network_start_path": local_paths["network_start"],
        "local_receipt_path": local_paths["receipt"],
        "local_outcome_path": local_paths["outcome"],
    }
    shadow_attempt = {
        "preformal_upload_attempt_id": document[
            "preformal_upload_attempt_id"
        ]
    }
    expected = _outcome_payload_from_verified_documents(
        plan=shadow_plan,
        attempt=shadow_attempt,
        outcome_class=outcome_class,
        receipt_id=receipt_id,
        abandonment_reason_code=reason,
    )
    if document != expected:
        _fail("pre-formal upload outcome identity changed")
    return document


def build_preformal_upload_outcome_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    outcome_class: str,
    receipt: dict[str, Any] | None = None,
    abandonment_reason_code: str | None = None,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    if outcome_class == PREFORMAL_OUTCOME_COMPLETE:
        if receipt is None:
            _fail("complete pre-formal outcome omitted its receipt")
        receipt = verify_preformal_upload_receipt_v42r1(
            receipt, plan=plan, attempt=attempt
        )
        receipt_id = receipt["preformal_upload_receipt_id"]
    else:
        if receipt is not None:
            _fail("abandoned pre-formal outcome cannot carry a receipt")
        receipt_id = None
    return _outcome_payload_from_verified_documents(
        plan=plan,
        attempt=attempt,
        outcome_class=outcome_class,
        receipt_id=receipt_id,
        abandonment_reason_code=abandonment_reason_code,
    )


def verify_preformal_upload_outcome_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = verify_preformal_upload_plan_v42r1(plan)
    attempt = verify_preformal_upload_attempt_v42r1(attempt, plan=plan)
    document = _verify_preformal_upload_outcome_structure_v42r1(
        raw_or_document
    )
    if document["outcome_class"] == PREFORMAL_OUTCOME_COMPLETE:
        if receipt is None:
            _fail("complete pre-formal outcome verification requires receipt")
        receipt = verify_preformal_upload_receipt_v42r1(
            receipt, plan=plan, attempt=attempt
        )
        receipt_id = receipt["preformal_upload_receipt_id"]
    else:
        if receipt is not None:
            _fail("abandoned pre-formal outcome verification forbids receipt")
        receipt_id = None
    expected = _outcome_payload_from_verified_documents(
        plan=plan,
        attempt=attempt,
        outcome_class=document["outcome_class"],
        receipt_id=receipt_id,
        abandonment_reason_code=document["abandonment_reason_code"],
    )
    if document != expected:
        _fail("pre-formal upload outcome differs from its plan or attempt")
    return document


__all__ = [
    "CONTROL_CREATION_ORDER",
    "CONTROL_NAMES",
    "MAXIMUM_FRAME_HEADER_BYTES",
    "MAXIMUM_RECEIPT_STDOUT_BYTES",
    "PINNED_HOST_KEY_FINGERPRINT",
    "PINNED_KNOWN_HOSTS_BYTES",
    "PREFORMAL_ATTEMPT_NAME",
    "PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS",
    "PREFORMAL_ABANDONMENT_REASON_LOCAL",
    "PREFORMAL_KNOWN_HOSTS_NAME",
    "PREFORMAL_NETWORK_START_NAME",
    "PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS",
    "PREFORMAL_OUTCOME_ABANDONED_FAILURE",
    "PREFORMAL_OUTCOME_COMPLETE",
    "PREFORMAL_OUTCOME_NAME",
    "PREFORMAL_PLAN_NAME",
    "PREFORMAL_RECEIPT_NAME",
    "PREFORMAL_STREAM_FRAME_ORDER",
    "PREFORMAL_STREAM_HEADER_NAME",
    "PREFORMAL_STREAM_MAGIC",
    "PREFORMAL_UPLOAD_ATTEMPT_ID_SENTINEL",
    "PREFORMAL_UPLOAD_PLAN_ID_SENTINEL",
    "V42MaterializationTransportError",
    "build_preformal_network_start_v42r1",
    "build_preformal_upload_attempt_v42r1",
    "build_preformal_upload_outcome_v42r1",
    "build_preformal_upload_plan_v42r1",
    "build_preformal_upload_receipt_v42r1",
    "build_preformal_upload_stream_header_v42r1",
    "materialize_preformal_upload_ssh_argv_v42r1",
    "verify_preformal_network_start_v42r1",
    "verify_preformal_upload_attempt_against_controls_v42r1",
    "verify_preformal_upload_attempt_v42r1",
    "verify_preformal_upload_outcome_v42r1",
    "verify_preformal_upload_plan_against_controls_v42r1",
    "verify_preformal_upload_plan_v42r1",
    "verify_preformal_upload_receipt_against_controls_v42r1",
    "verify_preformal_upload_receipt_v42r1",
    "verify_preformal_upload_stream_header_v42r1",
]
