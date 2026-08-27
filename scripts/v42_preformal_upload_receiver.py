"""Standalone stdlib-only receiver for the V42 pre-formal upload.

The trusted loader compiles these exact committed bytes under
``/usr/bin/python3 -I -S -B -c``.  Consequently this module must not import
``acfqp`` or any transported application code.  It validates the count-framed
wire stream, the remote safety projection of the content-addressed plan, the
startup TCB, and the five exact controls before creating an abandonable scratch
identity.  It never mutates the fixed formal root or starts the experiment.
"""

from __future__ import annotations

import grp
import hashlib
import json
import os
import pwd
import re
import socket
import stat
import sys


SCHEMA_VERSION = "42.1.0"
FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2"
GLOBAL_EXECUTION_ORDINAL = 2
REMOTE_HOST_ALIAS = "jtl110gpu2"
REMOTE_HOSTNAME = "erzhu419-Super-Server"
REMOTE_USER = "erzhu419"
REMOTE_UID = 1000
REMOTE_GID = 1000
REMOTE_PARENT = "/home/erzhu419/mine_code"
FIXED_REMOTE_ROOT = REMOTE_PARENT + "/.acfqp-v42-remote-ordinal2"
FIXED_TRANSPORT_LEDGER_ROOT = (
    REMOTE_PARENT + "/.acfqp-v42-remote-ordinal2-transport-ledger"
)
PREFORMAL_SCRATCH_PREFIX = ".acfqp-v42-remote-ordinal2-preformal-"
PREFORMAL_LEDGER_STAGE_PREFIX = (
    ".acfqp-v42-remote-ordinal2-transport-ledger-stage-"
)

PLAN_SCHEMA = "acfqp.v42_remote_ordinal2_preformal_upload_plan.v42r1"
ATTEMPT_SCHEMA = "acfqp.v42_remote_ordinal2_preformal_upload_attempt.v42r1"
HEADER_SCHEMA = "acfqp.v42_remote_ordinal2_preformal_stream_header.v42r1"
RECEIPT_SCHEMA = "acfqp.v42_remote_ordinal2_preformal_upload_receipt.v42r1"
SOURCE_SCHEMA = "acfqp.v42_remote_ordinal2_source_manifest.v42r1"
TRANSPORT_SCHEMA = "acfqp.v42_remote_ordinal2_transport_manifest.v42r1"
LOCAL_MATERIALIZATION_SCHEMA = (
    "acfqp.v42_remote_ordinal2_local_materialization_attempt.v42r1"
)
PYZ_ARTIFACT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_remote_bootstrap_pyz_artifact.v42r1"
)

PLAN_NAME = "PREFORMAL_UPLOAD_PLAN.json"
ATTEMPT_NAME = "PREFORMAL_UPLOAD_ATTEMPT.json"
HEADER_NAME = "PREFORMAL_STREAM_HEADER.json"
RECEIPT_NAME = "PREFORMAL_UPLOAD_RECEIPT.json"
SOURCE_NAME = "EXECUTION_SOURCE_MANIFEST.json"
LOCAL_NAME = "LOCAL_MATERIALIZATION_ATTEMPT.json"
PYZ_NAME = "REMOTE_BOOTSTRAP.pyz"
ARCHIVE_NAME = "SOURCE_CAPSULE.tar"
TRANSPORT_NAME = "TRANSPORT_MANIFEST.json"
LOADER_RELATIVE = "scripts/v42_preformal_upload_loader.py"
RECEIVER_RELATIVE = "scripts/v42_preformal_upload_receiver.py"

CONTROL_NAMES = tuple(sorted((SOURCE_NAME, LOCAL_NAME, PYZ_NAME, ARCHIVE_NAME, TRANSPORT_NAME)))
CONTROL_CREATION_ORDER = (
    LOCAL_NAME,
    ARCHIVE_NAME,
    SOURCE_NAME,
    TRANSPORT_NAME,
    PYZ_NAME,
)
FRAME_ORDER = (
    PLAN_NAME,
    ATTEMPT_NAME,
    LOCAL_NAME,
    SOURCE_NAME,
    TRANSPORT_NAME,
    PYZ_NAME,
    ARCHIVE_NAME,
)
MAGIC = b"ACFQP_V42_PREFORMAL_STREAM_V1\0"

MAXIMUM_CONTROL_BYTES = {
    SOURCE_NAME: 64 * 1024**2,
    LOCAL_NAME: 4 * 1024**2,
    PYZ_NAME: 64 * 1024**2,
    ARCHIVE_NAME: 2 * 1024**3,
    TRANSPORT_NAME: 64 * 1024**2,
}
MAXIMUM_PLAN_BYTES = 256 * 1024
MAXIMUM_ATTEMPT_BYTES = 128 * 1024
MAXIMUM_HEADER_BYTES = 64 * 1024
MAXIMUM_RECEIPT_BYTES = 256 * 1024
MAXIMUM_NONARCHIVE_BUFFER_BYTES = (
    MAXIMUM_PLAN_BYTES
    + MAXIMUM_ATTEMPT_BYTES
    + MAXIMUM_CONTROL_BYTES[LOCAL_NAME]
    + MAXIMUM_CONTROL_BYTES[SOURCE_NAME]
    + MAXIMUM_CONTROL_BYTES[TRANSPORT_NAME]
    + MAXIMUM_CONTROL_BYTES[PYZ_NAME]
)
STREAM_CHUNK_BYTES = 1024 * 1024
MAXIMUM_UPLOAD_ATTEMPTS = 8

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_DOMAIN = "acfqp:v42-remote-ordinal2:"


class _ReceiverFailure(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise _ReceiverFailure(message)


def _hex40(value: object, label: str) -> str:
    if type(value) is not str or _HEX40.fullmatch(value) is None:
        _fail(label + " changed")
    return value


def _hex64(value: object, label: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        _fail(label + " changed")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate JSON object key")
        result[key] = value
    return result


def _reject_number(token: str) -> None:
    _fail("non-integer JSON number is forbidden: " + token)


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as error:
        raise _ReceiverFailure("value is not canonical JSON") from error


def _canonical_document(raw: bytes, label: str) -> dict[str, object]:
    if type(raw) is not bytes:
        _fail(label + " bytes changed type")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except _ReceiverFailure:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise _ReceiverFailure(label + " is not strict JSON") from error
    if type(value) is not dict or _canonical_bytes(value) != raw:
        _fail(label + " is not canonical JSON object bytes")
    return value


def _content_id(domain: str, payload: dict[str, object]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\0" + _canonical_bytes(payload)
    ).hexdigest()


def _verify_document_id(
    document: dict[str, object], *, identity: str, domain: str, label: str
) -> str:
    observed = _hex64(document.get(identity), label + " identity")
    payload = dict(document)
    payload.pop(identity, None)
    if _content_id(domain, payload) != observed:
        _fail(label + " content identity changed")
    return observed


def _artifact(value: object, *, relative_path: str, label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != {
        "relative_path",
        "git_blob_oid",
        "sha256",
        "byte_count",
    }:
        _fail(label + " schema changed")
    if (
        value.get("relative_path") != relative_path
        or _HEX40.fullmatch(str(value.get("git_blob_oid"))) is None
        or _HEX64.fullmatch(str(value.get("sha256"))) is None
        or type(value.get("byte_count")) is not int
        or value["byte_count"] <= 0
    ):
        _fail(label + " fact changed")
    return dict(value)


def _expected_remote_tcb_contract() -> dict[str, object]:
    return {
        "expected_hostname": REMOTE_HOSTNAME,
        "resuid": [REMOTE_UID, REMOTE_UID, REMOTE_UID],
        "resgid": [REMOTE_GID, REMOTE_GID, REMOTE_GID],
        "supplementary_groups": [4, 24, 27, 30, 46, 100, 114, 1000],
        "linux_capability_hex_by_name": {
            "CapInh": "0000000000000000",
            "CapPrm": "0000000000000000",
            "CapEff": "0000000000000000",
            "CapAmb": "0000000000000000",
        },
        "python_invocation_path": "/usr/bin/python3",
        "python_invocation_node_type": "SYMLINK",
        "python_invocation_link_target": "python3.12",
        "python_invocation_mode": 0o777,
        "python_invocation_uid": 0,
        "python_invocation_gid": 0,
        "python_invocation_nlink": 1,
        "python_realpath": "/usr/bin/python3.12",
        "python_realpath_node_type": "REGULAR_FILE",
        "python_realpath_mode": 0o755,
        "python_realpath_uid": 0,
        "python_realpath_gid": 0,
        "python_realpath_nlink": 1,
        "python_realpath_sha256": (
            "1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118"
        ),
        "python_realpath_byte_count": 8_020_928,
        "python_version": [3, 12, 3],
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
        "bash_path": "/usr/bin/bash",
        "bash_node_type": "REGULAR_FILE",
        "bash_mode": 0o755,
        "bash_uid": 0,
        "bash_gid": 0,
        "bash_nlink": 1,
        "bash_sha256": (
            "bc5945feb8bd26203ebfafea5ce1878bb2e32cb8fb50ab7ae395cfb1e1aaaef1"
        ),
        "bash_byte_count": 1_446_024,
        "bashrc_path": "/home/erzhu419/.bashrc",
        "bashrc_node_type": "REGULAR_FILE",
        "bashrc_mode": 0o644,
        "bashrc_uid": REMOTE_UID,
        "bashrc_gid": REMOTE_GID,
        "bashrc_nlink": 1,
        "bashrc_sha256": (
            "55b107a5fba9cf1017ea3e0c77f3802732f01ba081af275d7f38e74ef0478dde"
        ),
        "bashrc_byte_count": 3_804,
        "user_ssh_rc_state": "ABSENT",
        "system_ssh_rc_state": "ABSENT",
        "environment": {"LC_CTYPE": "C.UTF-8"},
        "exact_live_file_descriptors": [0, 1, 2],
        "stdin_stdout_stderr_must_not_be_tty": True,
        "stdlib_installation_is_external_host_tcb": True,
        "python_binary_hash_does_not_bind_stdlib": True,
        "all_facts_rechecked_before_first_project_namespace_mutation": True,
    }


def _expected_stream_contract() -> dict[str, object]:
    return {
        "magic": "ACFQP_V42_PREFORMAL_STREAM_V1",
        "magic_encoding": "UTF8_PLUS_NUL",
        "header_schema": HEADER_SCHEMA,
        "header_length_encoding": "UNSIGNED_BIG_ENDIAN_8_BYTES",
        "header_byte_cap": MAXIMUM_HEADER_BYTES,
        "frame_count": len(FRAME_ORDER),
        "frame_order": list(FRAME_ORDER),
        "plan_body_byte_cap": MAXIMUM_PLAN_BYTES,
        "attempt_body_byte_cap": MAXIMUM_ATTEMPT_BYTES,
        "nonarchive_buffer_byte_cap": MAXIMUM_NONARCHIVE_BUFFER_BYTES,
        "receiver_source_precedes_magic_and_is_loader_count_delimited": True,
        "all_frame_headers_verified_before_first_project_namespace_mutation": True,
        "archive_is_final_body_and_streamed_with_chunk_cap": True,
        "archive_stream_chunk_byte_cap": STREAM_CHUNK_BYTES,
        "exact_eof_required_after_final_body": True,
    }


def _expected_receiver_contract() -> dict[str, object]:
    return {
        "loader_must_verify_receiver_hash_and_count_before_compile": True,
        "plan_attempt_and_frame_headers_must_verify_before_first_project_namespace_mutation": True,
        "host_startup_tcb_and_exact_fd_set_must_verify_before_first_project_namespace_mutation": True,
        "scratch_and_ledger_must_be_absent_before_creation": True,
        "fixed_remote_root": FIXED_REMOTE_ROOT,
        "fixed_transport_ledger_root": FIXED_TRANSPORT_LEDGER_ROOT,
        "fixed_roots_must_be_absent_before_and_after_preformal_upload": True,
        "directory_creation": "MKDIR_EXCLUSIVE_NOFOLLOW_MODE_0700",
        "scratch_first_child_name": LOCAL_NAME,
        "control_creation_order": list(CONTROL_CREATION_ORDER),
        "control_file_creation": "O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW",
        "control_file_mode": 0o400,
        "declared_lengths_must_equal_exact_control_facts": True,
        "frame_header_byte_cap": MAXIMUM_HEADER_BYTES,
        "stream_chunk_byte_cap": STREAM_CHUNK_BYTES,
        "control_hash_count_and_stability_required_before_file_fsync": True,
        "each_control_fsync_required_before_next_control": True,
        "exact_final_inventories_required": True,
        "scratch_ledger_and_shared_parent_fsync_required": True,
        "same_token_retry_forbidden_after_any_remote_mutation": True,
        "success_exit_status": 0,
        "success_stdout_encoding": "ONE_CANONICAL_RECEIPT_JSON_THEN_EOF",
        "success_stdout_byte_cap": MAXIMUM_RECEIPT_BYTES,
        "success_stdout_extra_bytes_forbidden": True,
        "stderr_is_diagnostic_and_never_completion_authority": True,
        "complete_requires_exit_zero_exact_receipt_eof_and_contextual_verification": True,
        "postnetwork_nonzero_truncated_extra_or_missing_receipt_is_ambiguous": True,
        "typed_remote_failure_terminal_is_defined": False,
    }


_PLAN_KEYS = {
    "authorized_ssh_argv_template",
    "contextual_control_join_required_for_effectful_authorization",
    "control_byte_caps",
    "control_creation_order",
    "control_facts",
    "expected_remote_hostname",
    "expected_total_control_bytes",
    "fixed_remote_root",
    "fixed_remote_root_effect_authorized",
    "fixed_transport_ledger_root",
    "formal_identity",
    "global_execution_ordinal",
    "loader_artifact",
    "local_attempt_path",
    "local_chain_root",
    "local_known_hosts_path",
    "local_materialization_attempt_id",
    "local_network_start_path",
    "local_ordinal_slot",
    "local_outcome_path",
    "local_plan_path",
    "local_publication_contract",
    "local_receipt_path",
    "local_stream_header_path",
    "local_transport_parent",
    "preformal_identity_is_not_formal_execution_authority",
    "preformal_ledger_stage_root",
    "preformal_scratch_root",
    "preformal_upload_chain_id",
    "preformal_upload_ordinal",
    "preformal_upload_plan_id",
    "previous_preformal_upload_outcome",
    "previous_preformal_upload_outcome_id",
    "receiver_artifact",
    "remote_receiver_contract",
    "remote_startup_tcb_contract",
    "remote_target_alias",
    "schema",
    "schema_version",
    "scratch_abandonment_requires_a_new_upload_token",
    "scratch_first_child_name",
    "source_commit",
    "source_manifest_id",
    "source_tree",
    "ssh_client_contract",
    "stream_protocol_contract",
    "systemd_effect_authorized",
    "transport_manifest_id",
    "trusted_bootstrap_effect_authorized",
    "upload_token",
    "upload_token_history",
}


def _verify_plan(
    raw: bytes,
    *,
    plan_id: str,
    loader_sha256: str,
    loader_byte_count: int,
    receiver_sha256: str,
    receiver_byte_count: int,
) -> dict[str, object]:
    plan = _canonical_document(raw, "pre-formal upload plan")
    if set(plan) != _PLAN_KEYS:
        _fail("pre-formal upload plan schema changed")
    observed_id = _verify_document_id(
        plan,
        identity="preformal_upload_plan_id",
        domain=_DOMAIN + "preformal-upload-plan",
        label="pre-formal upload plan",
    )
    if observed_id != _hex64(plan_id, "loader plan ID"):
        _fail("streamed plan differs from loader argv")
    if (
        plan.get("schema") != PLAN_SCHEMA
        or plan.get("schema_version") != SCHEMA_VERSION
        or plan.get("formal_identity") != FORMAL_IDENTITY
        or plan.get("global_execution_ordinal") != GLOBAL_EXECUTION_ORDINAL
        or plan.get("remote_target_alias") != REMOTE_HOST_ALIAS
        or plan.get("expected_remote_hostname") != REMOTE_HOSTNAME
        or plan.get("fixed_remote_root") != FIXED_REMOTE_ROOT
        or plan.get("fixed_transport_ledger_root") != FIXED_TRANSPORT_LEDGER_ROOT
    ):
        _fail("pre-formal plan remote authority changed")
    token = _hex64(plan.get("upload_token"), "upload token")
    ordinal = plan.get("preformal_upload_ordinal")
    history = plan.get("upload_token_history")
    if (
        type(ordinal) is not int
        or not 1 <= ordinal <= MAXIMUM_UPLOAD_ATTEMPTS
        or type(history) is not list
        or len(history) != ordinal
        or any(_HEX64.fullmatch(str(value)) is None for value in history)
        or len(set(history)) != len(history)
        or history[-1] != token
    ):
        _fail("pre-formal plan ordinal or token history changed")
    expected_scratch = REMOTE_PARENT + "/" + PREFORMAL_SCRATCH_PREFIX + token
    expected_ledger = REMOTE_PARENT + "/" + PREFORMAL_LEDGER_STAGE_PREFIX + token
    if (
        plan.get("preformal_scratch_root") != expected_scratch
        or plan.get("preformal_ledger_stage_root") != expected_ledger
    ):
        _fail("pre-formal remote scratch path changed")
    controls = plan.get("control_facts")
    caps = plan.get("control_byte_caps")
    if type(controls) is not list or type(caps) is not list:
        _fail("pre-formal control facts changed type")
    expected_controls: list[dict[str, object]] = []
    expected_caps: list[dict[str, object]] = []
    for name, fact in zip(CONTROL_NAMES, controls):
        if type(fact) is not dict or set(fact) != {
            "name",
            "sha256",
            "byte_count",
        }:
            _fail("pre-formal control fact schema changed")
        count = fact.get("byte_count")
        if (
            fact.get("name") != name
            or _HEX64.fullmatch(str(fact.get("sha256"))) is None
            or type(count) is not int
            or not 0 < count <= MAXIMUM_CONTROL_BYTES[name]
        ):
            _fail("pre-formal control fact changed")
        expected_controls.append(dict(fact))
        expected_caps.append(
            {"name": name, "maximum_byte_count": MAXIMUM_CONTROL_BYTES[name]}
        )
    if (
        len(controls) != len(CONTROL_NAMES)
        or controls != expected_controls
        or caps != expected_caps
        or plan.get("expected_total_control_bytes")
        != sum(fact["byte_count"] for fact in expected_controls)
        or plan.get("scratch_first_child_name") != LOCAL_NAME
        or plan.get("control_creation_order") != list(CONTROL_CREATION_ORDER)
    ):
        _fail("pre-formal control aggregate changed")
    loader = _artifact(
        plan.get("loader_artifact"),
        relative_path=LOADER_RELATIVE,
        label="loader artifact",
    )
    receiver = _artifact(
        plan.get("receiver_artifact"),
        relative_path=RECEIVER_RELATIVE,
        label="receiver artifact",
    )
    if (
        loader["sha256"] != _hex64(loader_sha256, "loader sha256")
        or loader["byte_count"] != loader_byte_count
        or receiver["sha256"] != _hex64(receiver_sha256, "receiver sha256")
        or receiver["byte_count"] != receiver_byte_count
    ):
        _fail("plan program artifact differs from loader verification")
    if (
        plan.get("remote_startup_tcb_contract")
        != _expected_remote_tcb_contract()
        or plan.get("stream_protocol_contract") != _expected_stream_contract()
        or plan.get("remote_receiver_contract") != _expected_receiver_contract()
    ):
        _fail("pre-formal remote safety contract changed")
    publication = plan.get("local_publication_contract")
    if (
        type(publication) is not dict
        or publication.get("publication_order")
        != [PLAN_NAME, "PINNED_KNOWN_HOSTS", ATTEMPT_NAME, HEADER_NAME, "PREFORMAL_NETWORK_START.json"]
        or publication.get("empty_ordinal_slot_is_unclaimed") is not True
        or publication.get("first_durable_plan_selects_ordinal_branch") is not True
    ):
        _fail("pre-formal local branch-selection contract changed")
    if any(
        plan.get(key) is not expected
        for key, expected in (
            ("contextual_control_join_required_for_effectful_authorization", True),
            ("preformal_identity_is_not_formal_execution_authority", True),
            ("scratch_abandonment_requires_a_new_upload_token", True),
            ("fixed_remote_root_effect_authorized", False),
            ("systemd_effect_authorized", False),
            ("trusted_bootstrap_effect_authorized", False),
        )
    ):
        _fail("pre-formal plan widened its authority")
    _hex40(plan.get("source_commit"), "source commit")
    _hex40(plan.get("source_tree"), "source tree")
    for key in (
        "source_manifest_id",
        "transport_manifest_id",
        "local_materialization_attempt_id",
        "preformal_upload_chain_id",
    ):
        _hex64(plan.get(key), key)
    return plan


def _attempt_from_plan(plan: dict[str, object]) -> dict[str, object]:
    plan_raw = _canonical_bytes(plan)
    payload = {
        "schema": ATTEMPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
        "preformal_upload_plan_byte_count": len(plan_raw),
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "local_materialization_attempt_id": plan["local_materialization_attempt_id"],
        "preformal_upload_ordinal": plan["preformal_upload_ordinal"],
        "previous_preformal_upload_outcome_id": plan["previous_preformal_upload_outcome_id"],
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
        "local_publication_order": plan["local_publication_contract"]["publication_order"],
        "known_hosts_sha256": "a764658af19a4f082f994c0f35062d47e8abc23510f7a77dfa7f12e2d8c6fec4",
        "known_hosts_byte_count": 113,
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
    return {
        **payload,
        "preformal_upload_attempt_id": _content_id(
            _DOMAIN + "preformal-upload-attempt", payload
        ),
    }


def _verify_attempt(
    raw: bytes, *, plan: dict[str, object], attempt_id: str
) -> dict[str, object]:
    attempt = _canonical_document(raw, "pre-formal upload attempt")
    expected = _attempt_from_plan(plan)
    if attempt != expected or attempt.get("preformal_upload_attempt_id") != _hex64(
        attempt_id, "loader attempt ID"
    ):
        _fail("pre-formal upload attempt differs from plan or loader argv")
    return attempt


def _header_from_documents(
    plan: dict[str, object], attempt: dict[str, object]
) -> dict[str, object]:
    plan_raw = _canonical_bytes(plan)
    attempt_raw = _canonical_bytes(attempt)
    control_by_name = {fact["name"]: fact for fact in plan["control_facts"]}
    frames: list[dict[str, object]] = [
        {
            "ordinal": 0,
            "role": "PLAN",
            "name": PLAN_NAME,
            "sha256": hashlib.sha256(plan_raw).hexdigest(),
            "byte_count": len(plan_raw),
        },
        {
            "ordinal": 1,
            "role": "ATTEMPT",
            "name": ATTEMPT_NAME,
            "sha256": hashlib.sha256(attempt_raw).hexdigest(),
            "byte_count": len(attempt_raw),
        },
    ]
    for ordinal, name in enumerate(FRAME_ORDER[2:], start=2):
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
        "schema": HEADER_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "magic": "ACFQP_V42_PREFORMAL_STREAM_V1",
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_attempt_id": attempt["preformal_upload_attempt_id"],
        "receiver_artifact": plan["receiver_artifact"],
        "frame_count": len(frames),
        "frames": frames,
        "body_encoding": "EXACT_CONCATENATION_WITHOUT_DELIMITERS",
        "exact_eof_required_after_final_body": True,
    }
    return {
        **payload,
        "preformal_stream_header_id": _content_id(
            _DOMAIN + "preformal-stream-header", payload
        ),
    }


def _read_exact(descriptor: int, count: int, label: str) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = os.read(descriptor, min(remaining, STREAM_CHUNK_BYTES))
        if not chunk:
            _fail(label + " ended early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _prevalidate_header(raw: bytes) -> dict[str, object]:
    header = _canonical_document(raw, "pre-formal stream header")
    _verify_document_id(
        header,
        identity="preformal_stream_header_id",
        domain=_DOMAIN + "preformal-stream-header",
        label="pre-formal stream header",
    )
    frames = header.get("frames")
    if (
        header.get("schema") != HEADER_SCHEMA
        or header.get("schema_version") != SCHEMA_VERSION
        or header.get("formal_identity") != FORMAL_IDENTITY
        or header.get("global_execution_ordinal") != GLOBAL_EXECUTION_ORDINAL
        or header.get("magic") != "ACFQP_V42_PREFORMAL_STREAM_V1"
        or header.get("frame_count") != len(FRAME_ORDER)
        or type(frames) is not list
        or len(frames) != len(FRAME_ORDER)
        or header.get("body_encoding") != "EXACT_CONCATENATION_WITHOUT_DELIMITERS"
        or header.get("exact_eof_required_after_final_body") is not True
    ):
        _fail("pre-formal stream header authority changed")
    aggregate = 0
    for ordinal, (name, frame) in enumerate(zip(FRAME_ORDER, frames)):
        cap = (
            MAXIMUM_PLAN_BYTES
            if ordinal == 0
            else MAXIMUM_ATTEMPT_BYTES
            if ordinal == 1
            else MAXIMUM_CONTROL_BYTES[name]
        )
        role = "PLAN" if ordinal == 0 else "ATTEMPT" if ordinal == 1 else "CONTROL"
        if (
            type(frame) is not dict
            or set(frame) != {"ordinal", "role", "name", "sha256", "byte_count"}
            or frame.get("ordinal") != ordinal
            or frame.get("role") != role
            or frame.get("name") != name
            or _HEX64.fullmatch(str(frame.get("sha256"))) is None
            or type(frame.get("byte_count")) is not int
            or not 0 < frame["byte_count"] <= cap
        ):
            _fail("pre-formal stream frame header changed")
        if ordinal < len(FRAME_ORDER) - 1:
            aggregate += frame["byte_count"]
    if aggregate > MAXIMUM_NONARCHIVE_BUFFER_BYTES:
        _fail("pre-formal non-archive buffer aggregate exceeds cap")
    return header


def _verify_control_documents(
    *,
    plan: dict[str, object],
    buffered: dict[str, bytes],
    archive_frame: dict[str, object],
    loader_sha256: str,
    loader_byte_count: int,
    receiver_sha256: str,
    receiver_byte_count: int,
) -> None:
    source = _canonical_document(buffered[SOURCE_NAME], "source manifest")
    transport = _canonical_document(
        buffered[TRANSPORT_NAME], "transport manifest"
    )
    local = _canonical_document(
        buffered[LOCAL_NAME], "local materialization attempt"
    )
    source_id = _verify_document_id(
        source,
        identity="source_manifest_id",
        domain=_DOMAIN + "source-manifest",
        label="source manifest",
    )
    transport_id = _verify_document_id(
        transport,
        identity="transport_manifest_id",
        domain=_DOMAIN + "transport-manifest",
        label="transport manifest",
    )
    local_id = _verify_document_id(
        local,
        identity="local_materialization_attempt_id",
        domain=_DOMAIN + "local-materialization-attempt",
        label="local materialization attempt",
    )
    if any(
        document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != FORMAL_IDENTITY
        or document.get("global_execution_ordinal") != GLOBAL_EXECUTION_ORDINAL
        for document in (source, transport, local)
    ) or (
        source.get("schema") != SOURCE_SCHEMA
        or transport.get("schema") != TRANSPORT_SCHEMA
        or local.get("schema") != LOCAL_MATERIALIZATION_SCHEMA
    ):
        _fail("control document authority changed")
    if (
        source_id != plan["source_manifest_id"]
        or transport_id != plan["transport_manifest_id"]
        or local_id != plan["local_materialization_attempt_id"]
        or transport.get("execution_source_manifest_id") != source_id
        or local.get("source_manifest_id") != source_id
        or local.get("transport_manifest_id") != transport_id
        or source.get("source_commit") != plan["source_commit"]
        or source.get("source_tree") != plan["source_tree"]
        or transport.get("source_commit") != plan["source_commit"]
        or transport.get("source_tree") != plan["source_tree"]
    ):
        _fail("control document lineage changed")
    if (
        transport.get("source_archive_sha256") != archive_frame["sha256"]
        or transport.get("source_archive_byte_count") != archive_frame["byte_count"]
        or local.get("source_archive_sha256") != archive_frame["sha256"]
        or local.get("source_archive_byte_count") != archive_frame["byte_count"]
    ):
        _fail("archive frame differs from manifests")
    artifact = transport.get("remote_bootstrap_pyz_artifact")
    if type(artifact) is not dict or artifact.get("schema") != PYZ_ARTIFACT_SCHEMA:
        _fail("remote bootstrap pyz artifact changed")
    artifact_id = _verify_document_id(
        artifact,
        identity="remote_bootstrap_pyz_artifact_id",
        domain=_DOMAIN + "remote-bootstrap-pyz-artifact",
        label="remote bootstrap pyz artifact",
    )
    pyz_digest = hashlib.sha256(buffered[PYZ_NAME]).hexdigest()
    if (
        artifact.get("pyz_sha256") != pyz_digest
        or artifact.get("pyz_byte_count") != len(buffered[PYZ_NAME])
        or local.get("remote_bootstrap_pyz_artifact_id") != artifact_id
        or local.get("remote_bootstrap_pyz_sha256") != pyz_digest
        or local.get("remote_bootstrap_pyz_byte_count") != len(buffered[PYZ_NAME])
    ):
        _fail("remote bootstrap pyz bytes differ from manifests")
    transport_facts = transport.get("transport_facts")
    if type(transport_facts) is not list:
        _fail("transport fact inventory changed type")
    by_path = {
        row.get("relative_path"): row
        for row in transport_facts
        if type(row) is dict and type(row.get("relative_path")) is str
    }
    for relative, artifact_fact, digest, count in (
        (
            LOADER_RELATIVE,
            plan["loader_artifact"],
            loader_sha256,
            loader_byte_count,
        ),
        (
            RECEIVER_RELATIVE,
            plan["receiver_artifact"],
            receiver_sha256,
            receiver_byte_count,
        ),
    ):
        fact = by_path.get(relative)
        if (
            type(fact) is not dict
            or fact.get("git_blob_oid") != artifact_fact["git_blob_oid"]
            or fact.get("sha256") != digest
            or fact.get("byte_count") != count
        ):
            _fail("program artifact differs from transport manifest")


def _read_and_verify_ingress_v42r1(
    descriptor: int,
    *,
    plan_id: str,
    attempt_id: str,
    loader_sha256: str,
    loader_byte_count: int,
    receiver_sha256: str,
    receiver_byte_count: int,
) -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, bytes],
    dict[str, object],
]:
    if _read_exact(descriptor, len(MAGIC), "stream magic") != MAGIC:
        _fail("pre-formal stream magic changed")
    header_count = int.from_bytes(
        _read_exact(descriptor, 8, "stream header length"), "big"
    )
    if not 0 < header_count <= MAXIMUM_HEADER_BYTES:
        _fail("pre-formal stream header length exceeds cap")
    header = _prevalidate_header(
        _read_exact(descriptor, header_count, "stream header")
    )
    frames = header["frames"]
    buffered: dict[str, bytes] = {}
    for frame in frames[:-1]:
        raw = _read_exact(
            descriptor, frame["byte_count"], "stream frame " + frame["name"]
        )
        if hashlib.sha256(raw).hexdigest() != frame["sha256"]:
            _fail("pre-formal stream frame hash changed")
        buffered[frame["name"]] = raw
    plan = _verify_plan(
        buffered[PLAN_NAME],
        plan_id=plan_id,
        loader_sha256=loader_sha256,
        loader_byte_count=loader_byte_count,
        receiver_sha256=receiver_sha256,
        receiver_byte_count=receiver_byte_count,
    )
    attempt = _verify_attempt(
        buffered[ATTEMPT_NAME], plan=plan, attempt_id=attempt_id
    )
    expected_header = _header_from_documents(plan, attempt)
    if header != expected_header:
        _fail("pre-formal stream header differs from plan and attempt")
    _verify_control_documents(
        plan=plan,
        buffered=buffered,
        archive_frame=frames[-1],
        loader_sha256=loader_sha256,
        loader_byte_count=loader_byte_count,
        receiver_sha256=receiver_sha256,
        receiver_byte_count=receiver_byte_count,
    )
    return plan, attempt, header, buffered, frames[-1]


def _build_receipt_v42r1(
    *,
    plan: dict[str, object],
    attempt: dict[str, object],
    header: dict[str, object],
    parent_fact: dict[str, object],
) -> dict[str, object]:
    scratch_fact = {
        "path": plan["preformal_scratch_root"],
        "node_type": "DIRECTORY",
        "mode": 0o700,
        "uid": REMOTE_UID,
        "gid": REMOTE_GID,
    }
    ledger_fact = {
        "path": plan["preformal_ledger_stage_root"],
        "node_type": "DIRECTORY",
        "mode": 0o700,
        "uid": REMOTE_UID,
        "gid": REMOTE_GID,
    }
    observed_control_facts = [
        {
            "name": fact["name"],
            "path": plan["preformal_scratch_root"] + "/" + fact["name"],
            "node_type": "REGULAR_FILE",
            "mode": 0o400,
            "uid": REMOTE_UID,
            "gid": REMOTE_GID,
            "sha256": fact["sha256"],
            "byte_count": fact["byte_count"],
        }
        for fact in plan["control_facts"]
    ]
    payload = {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_attempt_id": attempt["preformal_upload_attempt_id"],
        "preformal_stream_header_id": header["preformal_stream_header_id"],
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "local_materialization_attempt_id": plan["local_materialization_attempt_id"],
        "preformal_upload_ordinal": plan["preformal_upload_ordinal"],
        "previous_preformal_upload_outcome_id": plan["previous_preformal_upload_outcome_id"],
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
        "observed_control_file_facts": observed_control_facts,
        "scratch_root_inventory": list(CONTROL_NAMES),
        "ledger_stage_inventory": [],
        "scratch_first_child_name": LOCAL_NAME,
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
            _DOMAIN + "preformal-upload-receipt", payload
        ),
    }


def _stable_state(observed: os.stat_result) -> tuple[int, ...]:
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_uid,
        observed.st_gid,
        observed.st_nlink,
        observed.st_size,
        observed.st_mtime_ns,
        observed.st_ctime_ns,
    )


def _hash_regular_path(
    path: str,
    *,
    mode: int,
    uid: int,
    gid: int,
    nlink: int,
    byte_count: int,
    sha256: str,
    label: str,
) -> None:
    named_before = os.lstat(path)
    descriptor = os.open(
        path,
        os.O_RDONLY
        | os.O_NONBLOCK
        | os.O_NOCTTY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_uid != uid
            or before.st_gid != gid
            or before.st_nlink != nlink
            or before.st_size != byte_count
            or (named_before.st_dev, named_before.st_ino)
            != (before.st_dev, before.st_ino)
        ):
            _fail(label + " metadata changed")
        digest = hashlib.sha256()
        count = 0
        while True:
            chunk = os.read(descriptor, STREAM_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
            count += len(chunk)
        after = os.fstat(descriptor)
        named_after = os.lstat(path)
        if (
            count != byte_count
            or digest.hexdigest() != sha256
            or _stable_state(after) != _stable_state(before)
            or (named_after.st_dev, named_after.st_ino)
            != (after.st_dev, after.st_ino)
        ):
            _fail(label + " bytes or identity changed")
    finally:
        os.close(descriptor)


def _live_descriptor_numbers() -> list[int]:
    scanner = os.open(
        "/proc/self/fd",
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        if scanner != 3:
            _fail("receiver descriptor scanner was not the sole new descriptor")
        try:
            names = {int(name) for name in os.listdir(scanner)}
        except (OSError, ValueError) as error:
            raise _ReceiverFailure("receiver descriptor scan failed") from error
        if names != {0, 1, 2, scanner, scanner + 1}:
            _fail("receiver descriptor inventory changed")
        for descriptor in (0, 1, 2, scanner):
            os.fstat(descriptor)
        try:
            os.fstat(scanner + 1)
        except OSError as error:
            if error.errno != 9:
                raise
        else:
            _fail("receiver iterator descriptor remained live")
    finally:
        os.close(scanner)
    return [0, 1, 2]


def _bounded_proc_status() -> dict[str, str]:
    descriptor = os.open(
        "/proc/self/status",
        os.O_RDONLY
        | os.O_NONBLOCK
        | os.O_NOCTTY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC,
    )
    try:
        chunks: list[bytes] = []
        count = 0
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            count += len(chunk)
            if count > 1024 * 1024:
                _fail("proc status exceeds cap")
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    try:
        lines = b"".join(chunks).decode("ascii", errors="strict").splitlines()
    except UnicodeError as error:
        raise _ReceiverFailure("proc status encoding changed") from error
    result: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in result:
            _fail("proc status field repeated")
        result[key] = value.strip()
    return result


def _assert_absent_path(path: str, label: str) -> None:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return
    _fail(label + " must be absent")


def _verify_startup_tcb_v42r1() -> None:
    expected = _expected_remote_tcb_contract()
    if _live_descriptor_numbers() != [0, 1, 2]:
        _fail("receiver inherited descriptor set changed")
    if any(os.isatty(descriptor) for descriptor in (0, 1, 2)):
        _fail("receiver stdio unexpectedly uses a tty")
    if (
        socket.gethostname() != REMOTE_HOSTNAME
        or os.uname().nodename != REMOTE_HOSTNAME
        or pwd.getpwuid(os.geteuid()).pw_name != REMOTE_USER
        or os.getresuid() != (REMOTE_UID, REMOTE_UID, REMOTE_UID)
        or os.getresgid() != (REMOTE_GID, REMOTE_GID, REMOTE_GID)
        or sorted(os.getgroups()) != expected["supplementary_groups"]
        or dict(os.environ) != expected["environment"]
    ):
        _fail("receiver host principal or environment changed")
    status = _bounded_proc_status()
    capability_fields = expected["linux_capability_hex_by_name"]
    if any(status.get(name) != value for name, value in capability_fields.items()):
        _fail("receiver Linux capability set changed")
    invocation = os.lstat(expected["python_invocation_path"])
    invocation_after = os.lstat(expected["python_invocation_path"])
    if (
        not stat.S_ISLNK(invocation.st_mode)
        or stat.S_IMODE(invocation.st_mode) != expected["python_invocation_mode"]
        or invocation.st_uid != expected["python_invocation_uid"]
        or invocation.st_gid != expected["python_invocation_gid"]
        or invocation.st_nlink != expected["python_invocation_nlink"]
        or os.readlink(expected["python_invocation_path"])
        != expected["python_invocation_link_target"]
        or _stable_state(invocation_after) != _stable_state(invocation)
        or sys.executable != expected["python_invocation_path"]
        or os.path.realpath(sys.executable) != expected["python_realpath"]
    ):
        _fail("receiver Python invocation path changed")
    _hash_regular_path(
        expected["python_realpath"],
        mode=expected["python_realpath_mode"],
        uid=expected["python_realpath_uid"],
        gid=expected["python_realpath_gid"],
        nlink=expected["python_realpath_nlink"],
        byte_count=expected["python_realpath_byte_count"],
        sha256=expected["python_realpath_sha256"],
        label="receiver Python realpath",
    )
    if (
        list(sys.version_info[:3]) != expected["python_version"]
        or sys.flags.isolated != expected["python_isolated_flag"]
        or sys.flags.no_site != expected["python_no_site_flag"]
        or sys.dont_write_bytecode is not expected["python_dont_write_bytecode"]
    ):
        _fail("receiver Python runtime flags changed")
    _hash_regular_path(
        expected["bash_path"],
        mode=expected["bash_mode"],
        uid=expected["bash_uid"],
        gid=expected["bash_gid"],
        nlink=expected["bash_nlink"],
        byte_count=expected["bash_byte_count"],
        sha256=expected["bash_sha256"],
        label="receiver bash",
    )
    _hash_regular_path(
        expected["bashrc_path"],
        mode=expected["bashrc_mode"],
        uid=expected["bashrc_uid"],
        gid=expected["bashrc_gid"],
        nlink=expected["bashrc_nlink"],
        byte_count=expected["bashrc_byte_count"],
        sha256=expected["bashrc_sha256"],
        label="receiver bashrc",
    )
    _assert_absent_path("/home/erzhu419/.ssh/rc", "user ssh rc")
    _assert_absent_path("/etc/ssh/sshrc", "system ssh rc")
    if _live_descriptor_numbers() != [0, 1, 2]:
        _fail("receiver TCB verification leaked a descriptor")


def _directory_identity(
    descriptor: int,
    *,
    label: str,
    mode: int | None = None,
    uid: int | None = None,
    gid: int | None = None,
) -> tuple[int, int]:
    observed = os.fstat(descriptor)
    if not stat.S_ISDIR(observed.st_mode):
        _fail(label + " is not a directory")
    if mode is not None and stat.S_IMODE(observed.st_mode) != mode:
        _fail(label + " mode changed")
    if uid is not None and observed.st_uid != uid:
        _fail(label + " uid changed")
    if gid is not None and observed.st_gid != gid:
        _fail(label + " gid changed")
    if observed.st_nlink < 2:
        _fail(label + " link count changed")
    return observed.st_dev, observed.st_ino


def _directory_pin(
    *,
    parent_fd: int,
    name: str,
    descriptor: int,
    label: str,
    mode: int | None = None,
    uid: int | None = None,
    gid: int | None = None,
) -> dict[str, object]:
    identity = _directory_identity(
        descriptor, label=label, mode=mode, uid=uid, gid=gid
    )
    named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(named.st_mode) or (named.st_dev, named.st_ino) != identity:
        _fail(label + " named identity changed")
    return {
        "parent_fd": parent_fd,
        "name": name,
        "descriptor": descriptor,
        "identity": identity,
        "label": label,
        "mode": mode,
        "uid": uid,
        "gid": gid,
    }


def _verify_directory_pin(pin: dict[str, object]) -> None:
    identity = _directory_identity(
        pin["descriptor"],
        label=pin["label"],
        mode=pin["mode"],
        uid=pin["uid"],
        gid=pin["gid"],
    )
    named = os.stat(
        pin["name"], dir_fd=pin["parent_fd"], follow_symlinks=False
    )
    if (
        identity != pin["identity"]
        or not stat.S_ISDIR(named.st_mode)
        or (named.st_dev, named.st_ino) != pin["identity"]
    ):
        _fail(pin["label"] + " path identity changed")


def _open_remote_parent() -> tuple[int, list[dict[str, object]], int, dict[str, object]]:
    root_fd = os.open(
        "/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    pins: list[dict[str, object]] = []
    current_fd = root_fd
    try:
        for index, component in enumerate(("home", "erzhu419", "mine_code"), start=1):
            descriptor = -1
            try:
                descriptor = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=current_fd,
                )
                pin = _directory_pin(
                    parent_fd=current_fd,
                    name=component,
                    descriptor=descriptor,
                    label="remote parent component " + str(index),
                )
            except BaseException:
                if descriptor >= 0:
                    os.close(descriptor)
                raise
            pins.append(pin)
            current_fd = descriptor
        _directory_identity(
            current_fd,
            label="remote shared parent",
            mode=0o775,
            uid=REMOTE_UID,
            gid=REMOTE_GID,
        )
        principals = sorted(
            entry.pw_name for entry in pwd.getpwall() if entry.pw_gid == REMOTE_GID
        )
        explicit = sorted(grp.getgrgid(REMOTE_GID).gr_mem)
        if principals != [REMOTE_USER] or explicit != []:
            _fail("remote parent group principals changed")
        parent_fact = {
            "path": REMOTE_PARENT,
            "node_type": "DIRECTORY",
            "mode": 0o775,
            "uid": REMOTE_UID,
            "gid": REMOTE_GID,
            "world_writable": False,
            "primary_gid_principals": principals,
            "explicit_group_members": explicit,
        }
        return root_fd, pins, current_fd, parent_fact
    except BaseException:
        for pin in reversed(pins):
            os.close(pin["descriptor"])
        os.close(root_fd)
        raise


def _verify_remote_parent(
    pins: list[dict[str, object]], parent_fd: int
) -> None:
    for pin in pins:
        _verify_directory_pin(pin)
    _directory_identity(
        parent_fd,
        label="remote shared parent",
        mode=0o775,
        uid=REMOTE_UID,
        gid=REMOTE_GID,
    )
    if (
        sorted(entry.pw_name for entry in pwd.getpwall() if entry.pw_gid == REMOTE_GID)
        != [REMOTE_USER]
        or sorted(grp.getgrgid(REMOTE_GID).gr_mem) != []
    ):
        _fail("remote parent group principals changed during materialization")


def _assert_absent_at(parent_fd: int, name: str, label: str) -> None:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    _fail(label + " must be absent")


def _create_directory_at(
    parent_fd: int, name: str, *, label: str
) -> dict[str, object]:
    if not name or "/" in name or name in {".", ".."}:
        _fail(label + " basename changed")
    prior_umask = os.umask(0o077)
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
    finally:
        os.umask(prior_umask)
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        pin = _directory_pin(
            parent_fd=parent_fd,
            name=name,
            descriptor=descriptor,
            label=label,
            mode=0o700,
            uid=REMOTE_UID,
            gid=REMOTE_GID,
        )
        os.fsync(descriptor)
        os.fsync(parent_fd)
        _verify_directory_pin(pin)
        return pin
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _file_fact(observed: os.stat_result, count: int, label: str) -> None:
    if (
        not stat.S_ISREG(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o400
        or observed.st_uid != REMOTE_UID
        or observed.st_gid != REMOTE_GID
        or observed.st_nlink != 1
        or observed.st_size != count
    ):
        _fail(label + " file metadata changed")


def _pin_file_at(
    directory_fd: int,
    name: str,
    *,
    expected_sha256: str,
    expected_count: int,
    label: str,
) -> dict[str, object]:
    descriptor = os.open(
        name,
        os.O_RDONLY
        | os.O_NONBLOCK
        | os.O_NOCTTY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC,
        dir_fd=directory_fd,
    )
    try:
        before = os.fstat(descriptor)
        _file_fact(before, expected_count, label)
        named_before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (named_before.st_dev, named_before.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            _fail(label + " opened and named identities differ")
        digest = hashlib.sha256()
        count = 0
        while True:
            chunk = os.read(descriptor, STREAM_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
            count += len(chunk)
        after = os.fstat(descriptor)
        named_after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            digest.hexdigest() != expected_sha256
            or count != expected_count
            or _stable_state(after) != _stable_state(before)
            or (named_after.st_dev, named_after.st_ino)
            != (after.st_dev, after.st_ino)
        ):
            _fail(label + " readback changed")
        return {
            "directory_fd": directory_fd,
            "name": name,
            "descriptor": descriptor,
            "identity": (after.st_dev, after.st_ino),
            "state": _stable_state(after),
            "sha256": expected_sha256,
            "byte_count": expected_count,
            "label": label,
        }
    except BaseException:
        os.close(descriptor)
        raise


def _verify_file_pin(pin: dict[str, object]) -> None:
    descriptor = pin["descriptor"]
    os.lseek(descriptor, 0, os.SEEK_SET)
    before = os.fstat(descriptor)
    _file_fact(before, pin["byte_count"], pin["label"])
    named_before = os.stat(
        pin["name"], dir_fd=pin["directory_fd"], follow_symlinks=False
    )
    digest = hashlib.sha256()
    count = 0
    while True:
        chunk = os.read(descriptor, STREAM_CHUNK_BYTES)
        if not chunk:
            break
        digest.update(chunk)
        count += len(chunk)
    after = os.fstat(descriptor)
    named_after = os.stat(
        pin["name"], dir_fd=pin["directory_fd"], follow_symlinks=False
    )
    if (
        _stable_state(before) != pin["state"]
        or _stable_state(after) != pin["state"]
        or (named_before.st_dev, named_before.st_ino) != pin["identity"]
        or (named_after.st_dev, named_after.st_ino) != pin["identity"]
        or digest.hexdigest() != pin["sha256"]
        or count != pin["byte_count"]
    ):
        _fail(pin["label"] + " final identity changed")


def _open_new_control(
    directory_fd: int, name: str, label: str
) -> int:
    prior_umask = os.umask(0o077)
    try:
        return os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NONBLOCK
            | os.O_NOCTTY
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            0o400,
            dir_fd=directory_fd,
        )
    finally:
        os.umask(prior_umask)


def _write_all(descriptor: int, raw: bytes, label: str) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(descriptor, raw[offset:])
        if written <= 0:
            _fail(label + " write made no progress")
        offset += written


def _finish_created_control(
    *,
    directory_fd: int,
    name: str,
    writer_fd: int,
    expected_sha256: str,
    expected_count: int,
    label: str,
) -> dict[str, object]:
    before_fsync = os.fstat(writer_fd)
    _file_fact(before_fsync, expected_count, label)
    named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if (named.st_dev, named.st_ino) != (
        before_fsync.st_dev,
        before_fsync.st_ino,
    ):
        _fail(label + " created identity changed")
    pin = _pin_file_at(
        directory_fd,
        name,
        expected_sha256=expected_sha256,
        expected_count=expected_count,
        label=label,
    )
    try:
        writer_after_readback = os.fstat(writer_fd)
        if (writer_after_readback.st_dev, writer_after_readback.st_ino) != pin[
            "identity"
        ]:
            _fail(label + " created inode was replaced before file fsync")
        os.fsync(writer_fd)
        writer_after_fsync = os.fstat(writer_fd)
        if (writer_after_fsync.st_dev, writer_after_fsync.st_ino) != pin[
            "identity"
        ]:
            _fail(label + " created inode was replaced during file fsync")
        _verify_file_pin(pin)
        os.fsync(directory_fd)
        _verify_file_pin(pin)
        return pin
    except BaseException:
        os.close(pin["descriptor"])
        raise


def _create_control_from_bytes(
    *, directory_fd: int, name: str, raw: bytes, fact: dict[str, object]
) -> dict[str, object]:
    if len(raw) != fact["byte_count"] or hashlib.sha256(raw).hexdigest() != fact["sha256"]:
        _fail(name + " buffered bytes differ from plan")
    writer = _open_new_control(directory_fd, name, name)
    try:
        _write_all(writer, raw, name)
        return _finish_created_control(
            directory_fd=directory_fd,
            name=name,
            writer_fd=writer,
            expected_sha256=fact["sha256"],
            expected_count=fact["byte_count"],
            label=name,
        )
    finally:
        os.close(writer)


def _create_archive_from_stream(
    *,
    directory_fd: int,
    input_fd: int,
    name: str,
    fact: dict[str, object],
) -> dict[str, object]:
    writer = _open_new_control(directory_fd, name, name)
    try:
        digest = hashlib.sha256()
        remaining = fact["byte_count"]
        while remaining:
            chunk = os.read(input_fd, min(remaining, STREAM_CHUNK_BYTES))
            if not chunk:
                _fail("archive body ended early")
            _write_all(writer, chunk, name)
            digest.update(chunk)
            remaining -= len(chunk)
        if os.read(input_fd, 1) != b"":
            _fail("archive body has trailing stream bytes")
        if digest.hexdigest() != fact["sha256"]:
            _fail("archive body hash changed")
        return _finish_created_control(
            directory_fd=directory_fd,
            name=name,
            writer_fd=writer,
            expected_sha256=fact["sha256"],
            expected_count=fact["byte_count"],
            label=name,
        )
    finally:
        os.close(writer)


def _materialize_and_build_receipt_v42r1(
    *,
    input_fd: int,
    plan: dict[str, object],
    attempt: dict[str, object],
    header: dict[str, object],
    buffered: dict[str, bytes],
    archive_frame: dict[str, object],
) -> dict[str, object]:
    root_fd, parent_pins, parent_fd, parent_fact = _open_remote_parent()
    scratch_pin: dict[str, object] | None = None
    ledger_pin: dict[str, object] | None = None
    file_pins: list[dict[str, object]] = []
    try:
        _verify_remote_parent(parent_pins, parent_fd)
        fixed_name = FIXED_REMOTE_ROOT.rsplit("/", 1)[1]
        fixed_ledger_name = FIXED_TRANSPORT_LEDGER_ROOT.rsplit("/", 1)[1]
        scratch_name = plan["preformal_scratch_root"].rsplit("/", 1)[1]
        ledger_name = plan["preformal_ledger_stage_root"].rsplit("/", 1)[1]
        if (
            plan["preformal_scratch_root"] != REMOTE_PARENT + "/" + scratch_name
            or plan["preformal_ledger_stage_root"] != REMOTE_PARENT + "/" + ledger_name
        ):
            _fail("pre-formal directory basenames escaped parent")
        for name, label in (
            (fixed_name, "fixed remote root"),
            (fixed_ledger_name, "fixed transport ledger"),
            (scratch_name, "pre-formal scratch"),
            (ledger_name, "pre-formal ledger stage"),
        ):
            _assert_absent_at(parent_fd, name, label)
        scratch_pin = _create_directory_at(
            parent_fd, scratch_name, label="pre-formal scratch"
        )
        scratch_fd = scratch_pin["descriptor"]
        if os.listdir(scratch_fd) != []:
            _fail("pre-formal scratch was not born empty")
        facts = {fact["name"]: fact for fact in plan["control_facts"]}
        file_pins.append(
            _create_control_from_bytes(
                directory_fd=scratch_fd,
                name=LOCAL_NAME,
                raw=buffered[LOCAL_NAME],
                fact=facts[LOCAL_NAME],
            )
        )
        if sorted(os.listdir(scratch_fd)) != [LOCAL_NAME]:
            _fail("local attempt was not the first scratch child")
        if (
            archive_frame["name"] != ARCHIVE_NAME
            or archive_frame["sha256"] != facts[ARCHIVE_NAME]["sha256"]
            or archive_frame["byte_count"] != facts[ARCHIVE_NAME]["byte_count"]
        ):
            _fail("archive frame differs from plan")
        file_pins.append(
            _create_archive_from_stream(
                directory_fd=scratch_fd,
                input_fd=input_fd,
                name=ARCHIVE_NAME,
                fact=facts[ARCHIVE_NAME],
            )
        )
        if sorted(os.listdir(scratch_fd)) != sorted((LOCAL_NAME, ARCHIVE_NAME)):
            _fail("archive was not the second scratch child")
        for name in (SOURCE_NAME, TRANSPORT_NAME, PYZ_NAME):
            file_pins.append(
                _create_control_from_bytes(
                    directory_fd=scratch_fd,
                    name=name,
                    raw=buffered[name],
                    fact=facts[name],
                )
            )
        _assert_absent_at(parent_fd, ledger_name, "pre-formal ledger stage")
        ledger_pin = _create_directory_at(
            parent_fd, ledger_name, label="pre-formal ledger stage"
        )
        if os.listdir(ledger_pin["descriptor"]) != []:
            _fail("pre-formal ledger stage is not empty")
        if sorted(os.listdir(scratch_fd)) != list(CONTROL_NAMES):
            _fail("pre-formal scratch final inventory changed")
        identities = set()
        for pin in file_pins:
            os.fsync(pin["descriptor"])
            _verify_file_pin(pin)
            identities.add(pin["identity"])
        if len(identities) != len(file_pins):
            _fail("pre-formal control files alias one inode")
        os.fsync(scratch_fd)
        os.fsync(ledger_pin["descriptor"])
        os.fsync(parent_fd)
        _verify_directory_pin(scratch_pin)
        _verify_directory_pin(ledger_pin)
        _verify_remote_parent(parent_pins, parent_fd)
        if sorted(os.listdir(scratch_fd)) != list(CONTROL_NAMES):
            _fail("pre-formal scratch inventory changed after fsync")
        if os.listdir(ledger_pin["descriptor"]) != []:
            _fail("pre-formal ledger inventory changed after fsync")
        _assert_absent_at(parent_fd, fixed_name, "fixed remote root")
        _assert_absent_at(
            parent_fd, fixed_ledger_name, "fixed transport ledger"
        )
        for pin in file_pins:
            _verify_file_pin(pin)
        return _build_receipt_v42r1(
            plan=plan,
            attempt=attempt,
            header=header,
            parent_fact=parent_fact,
        )
    finally:
        for pin in reversed(file_pins):
            try:
                os.close(pin["descriptor"])
            except OSError:
                pass
        for pin in (ledger_pin, scratch_pin):
            if pin is not None:
                try:
                    os.close(pin["descriptor"])
                except OSError:
                    pass
        for pin in reversed(parent_pins):
            try:
                os.close(pin["descriptor"])
            except OSError:
                pass
        os.close(root_fd)


def _write_stdout_receipt(raw: bytes) -> None:
    if not 0 < len(raw) <= MAXIMUM_RECEIPT_BYTES:
        _fail("pre-formal receipt exceeds stdout cap")
    _write_all(1, raw, "receipt stdout")


def main_v42r1(
    *,
    plan_id: str,
    attempt_id: str,
    loader_sha256: str,
    loader_byte_count: int,
    receiver_sha256: str,
    receiver_byte_count: int,
) -> int:
    if (
        _HEX64.fullmatch(str(plan_id)) is None
        or _HEX64.fullmatch(str(attempt_id)) is None
        or _HEX64.fullmatch(str(loader_sha256)) is None
        or _HEX64.fullmatch(str(receiver_sha256)) is None
        or type(loader_byte_count) is not int
        or loader_byte_count <= 0
        or type(receiver_byte_count) is not int
        or not 0 < receiver_byte_count <= 4 * 1024**2
    ):
        _fail("receiver loader facts changed")
    _verify_startup_tcb_v42r1()
    plan, attempt, header, buffered, archive_frame = (
        _read_and_verify_ingress_v42r1(
            0,
            plan_id=plan_id,
            attempt_id=attempt_id,
            loader_sha256=loader_sha256,
            loader_byte_count=loader_byte_count,
            receiver_sha256=receiver_sha256,
            receiver_byte_count=receiver_byte_count,
        )
    )
    _verify_startup_tcb_v42r1()
    receipt = _materialize_and_build_receipt_v42r1(
        input_fd=0,
        plan=plan,
        attempt=attempt,
        header=header,
        buffered=buffered,
        archive_frame=archive_frame,
    )
    _write_stdout_receipt(_canonical_bytes(receipt))
    return 0
