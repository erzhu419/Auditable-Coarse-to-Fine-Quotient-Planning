"""Pure recovery-only authority for the retained V42r3r3 launch occurrence.

This authority cannot launch, retry, stop, reset, or otherwise mutate the
retained scientific occurrence.  It authenticates one new controller source
set, binds the exact retained post-marker occurrence, authorizes one bounded
read-only inspection transport, and records the only safe terminal result:
the retained effect stays permanently closed to replay.  A currently absent
unit or journal is deliberately never promoted to proof that the historical
launch did not execute.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from pathlib import PurePosixPath
import re
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_formal_transport_successor_v42r3
    as retained,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "42.3.4"
RECOVERY_OPERATION = "READ_ONLY_LAUNCH_RECOVERY"
RECOVERY_INSPECTION_ORDINAL = 1

RECOVERY_CLASS_AMBIGUOUS_PERMANENTLY_CLOSED = (
    "AMBIGUOUS_PERMANENTLY_CLOSED"
)
RECOVERY_REASON_RETAINED_POST_MARKER_WITHOUT_EXACT_RECEIPT = (
    "RETAINED_POST_MARKER_WITHOUT_EXACT_RECEIPT"
)
RECOVERY_REASON_INSPECTION_NOT_EXACT = "RECOVERY_INSPECTION_NOT_EXACT"
RECOVERY_REASON_LAUNCH_STATE_NOT_EXACT_OR_SUPERVISION_LOST = (
    "LAUNCH_STATE_NOT_EXACT_OR_SUPERVISION_LOST"
)

RETAINED_FORMAL_TRANSPORT_PLAN_ID = (
    "58b6f0a4dd4dc867259176d77ef55e287fe882c7534bb25fdee8dec939dcd411"
)
RETAINED_LOCAL_LAUNCH_ATTEMPT_ID = (
    "edc24ee9895e181676dcde59ace1659466a00ae0e7eab5dacd4c862c95410ec7"
)
RETAINED_FORMAL_LAUNCH_TRANSPORT_ATTEMPT_ID = (
    "68c57ecadb12de60a68dcf3ff7c3b71966a99c6c8937828c14d3ddd595e2614d"
)
RETAINED_FORMAL_LAUNCH_NETWORK_START_ID = (
    "2c311147c448ebb093f5660e0ceb5ebbd78db234b91089c077e8bbf4c463bfb8"
)
RETAINED_FORMAL_LAUNCH_OPERATION_OUTCOME_ID = (
    "501a308cac572821c96f36cac0710b0f7f69af2add0f6d1668b9cfd83333db7f"
)
RETAINED_CONTROLLER_SOURCE_MANIFEST_ID = (
    "750401e55e51ae8f5e94c77e2e56bf8eb12e3e5d61fe336b3c82067d1a42a7b1"
)
RETAINED_CONTROLLER_SOURCE_COMMIT = (
    "6f9678f7f71a57dfeef5459c27c5b48331001c0f"
)
RETAINED_CONTROLLER_SOURCE_TREE = (
    "6494ba9044a00168f1e67b149b92682766c7ecc3"
)
RETAINED_PREPARE_RECEIPT_ID = (
    "746b63dd73e453156c9749bfbf7f810fdedbac138471121db25ca4be59a301f7"
)
RETAINED_LOCAL_ROOT = PurePosixPath(
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-local-formal-transport-ordinal2-v42r3r3"
)
RETAINED_ROOT_IDENTITY_PATH = PurePosixPath(
    "/home/erzhu419/mine_code/"
    "..acfqp-v42-local-formal-transport-ordinal2-v42r3r3.ROOT_IDENTITY.json"
)
RETAINED_PARENT_NETWORK_START_PATH = PurePosixPath(
    "/home/erzhu419/mine_code/"
    "..acfqp-v42-local-formal-transport-ordinal2-v42r3r3.NETWORK_START."
    "LAUNCH."
    + RETAINED_LOCAL_LAUNCH_ATTEMPT_ID
    + ".json"
)
RETAINED_RAW_FACTS = {
    "root_identity": {
        "path": str(RETAINED_ROOT_IDENTITY_PATH),
        "byte_count": 248,
        "sha256": "60d22cbff0b23bc9fc1082235c6e58ad2ad598afdf25360c68ec9a5b021aa99f",
    },
    "controller_source_manifest": {
        "path": str(RETAINED_LOCAL_ROOT / "CONTROLLER_SOURCE_MANIFEST.json"),
        "byte_count": 9_358,
        "sha256": "48814dc8de42ffb410c349cd4a7063071cacf33c667e0489ebe17c3193d9a271",
    },
    "formal_transport_plan": {
        "path": str(RETAINED_LOCAL_ROOT / "FORMAL_TRANSPORT_PLAN.json"),
        "byte_count": 14_853,
        "sha256": "b54a834237f08bf76e769e42d4cfaab705e3a6491f82a344dac1f0c6370ab5f3",
    },
    "prepare_receipt": {
        "path": str(RETAINED_LOCAL_ROOT / "FORMAL_PREPARE_RECEIPT.json"),
        "byte_count": 1_382_013,
        "sha256": "3d809b78c95d127cd1c4be99974a759e24f2e758d39ca49fcfdd9c62a3f93720",
    },
    "local_launch_attempt": {
        "path": str(RETAINED_LOCAL_ROOT / "LOCAL_LAUNCH_ATTEMPT.json"),
        "byte_count": 1_067,
        "sha256": "0fb8c99e3338d6c689b55e194faf1021779ecbac5295f94ade47608cf6eeba05",
    },
    "formal_launch_transport_attempt": {
        "path": str(RETAINED_LOCAL_ROOT / "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json"),
        "byte_count": 1_201,
        "sha256": "0e03d51f649ccce5fb697a5a67ec3eb0ef57cd8344a9b214c0b5f67880fefeb1",
    },
    "inner_network_start": {
        "path": str(RETAINED_LOCAL_ROOT / "FORMAL_LAUNCH_NETWORK_START.json"),
        "byte_count": 736,
        "sha256": "f8bd2e347e6998df9f110d7d3b4447de175f14fd2c6303268aafd9432a3d16d8",
    },
    "parent_network_start": {
        "path": str(RETAINED_PARENT_NETWORK_START_PATH),
        "byte_count": 736,
        "sha256": "f8bd2e347e6998df9f110d7d3b4447de175f14fd2c6303268aafd9432a3d16d8",
    },
    "operation_outcome": {
        "path": str(RETAINED_LOCAL_ROOT / "FORMAL_LAUNCH_OPERATION_OUTCOME.json"),
        "byte_count": 735,
        "sha256": "fb4314f272240bf5cd5cd481210fadd4c7abe6ddad2d3ba2aab65444c8dec716",
    },
}

RECOVERY_BOOTSTRAP_RELATIVE = (
    "scripts/bootstrap_v42_formal_transport_recovery_v42r3r4.py"
)
RECOVERY_LAUNCHER_RELATIVE = (
    "scripts/launch_v42_formal_transport_recovery_v42r3r4.py"
)
RECOVERY_RECEIVER_RELATIVE = (
    "scripts/v42_standard_2048_formal_transport_recovery_receiver_v42r3r4.py"
)
RECOVERY_AUTHORITY_RELATIVE = (
    "src/acfqp/"
    "construction_k7_standard_2048_formal_transport_recovery_v42r3r4.py"
)
RETAINED_AUTHORITY_RELATIVE = (
    "src/acfqp/"
    "construction_k7_standard_2048_formal_transport_successor_v42r3.py"
)

RECOVERY_CONTROLLER_REQUIRED_PATHS = frozenset(
    {
        "scripts/__init__.py",
        RECOVERY_BOOTSTRAP_RELATIVE,
        RECOVERY_LAUNCHER_RELATIVE,
        RECOVERY_RECEIVER_RELATIVE,
        "src/acfqp/__init__.py",
        "src/acfqp/construction_k7_domain_registry_extension_v42.py",
        RECOVERY_AUTHORITY_RELATIVE,
        RETAINED_AUTHORITY_RELATIVE,
        (
            "src/acfqp/"
            "construction_k7_standard_2048_remote_execution_authority_v42r1.py"
        ),
        "src/acfqp/phase3e_ids.py",
    }
)
RECOVERY_CONTROLLER_MAX_SOURCE_FACTS = 64

RECOVERY_CONTROLLER_SOURCE_MANIFEST_SCHEMA = (
    "acfqp.v42_formal_transport_recovery_controller_source_manifest.v42r3r4"
)
RETAINED_LAUNCH_OCCURRENCE_SCHEMA = (
    "acfqp.v42_formal_transport_retained_launch_occurrence.v42r3r4"
)
RECOVERY_PLAN_SCHEMA = "acfqp.v42_formal_transport_recovery_plan.v42r3r4"
RECOVERY_INSPECTION_ATTEMPT_SCHEMA = (
    "acfqp.v42_formal_transport_recovery_inspection_attempt.v42r3r4"
)
BOUNDED_CHILD_TRANSPORT_OBSERVATION_SCHEMA = (
    "acfqp.v42_formal_transport_recovery_child_transport_observation.v42r3r4"
)
REMOTE_READ_ONLY_INSPECTION_SCHEMA = (
    "acfqp.v42r3r4_formal_launch_recovery_remote_inspection"
)
REMOTE_INSPECTION_JOIN_SCHEMA = (
    "acfqp.v42_formal_transport_recovery_remote_inspection_join.v42r3r4"
)
RECOVERY_CLASSIFICATION_SCHEMA = (
    "acfqp.v42_formal_transport_recovery_classification.v42r3r4"
)

RECOVERY_CONTROLLER_SOURCE_MANIFEST_DOMAIN = (
    b"acfqp:v42-formal-transport-recovery:controller-source-manifest:v42r3r4"
)
RETAINED_LAUNCH_OCCURRENCE_DOMAIN = (
    b"acfqp:v42-formal-transport-recovery:retained-launch-occurrence:v42r3r4"
)
RECOVERY_PLAN_DOMAIN = b"acfqp:v42-formal-transport-recovery:plan:v42r3r4"
RECOVERY_INSPECTION_ATTEMPT_DOMAIN = (
    b"acfqp:v42-formal-transport-recovery:inspection-attempt:v42r3r4"
)
BOUNDED_CHILD_TRANSPORT_OBSERVATION_DOMAIN = (
    b"acfqp:v42-formal-transport-recovery:child-transport-observation:v42r3r4"
)
REMOTE_READ_ONLY_INSPECTION_DOMAIN = (
    b"acfqp:v42r3r4-formal-launch-recovery:remote-inspection"
)
REMOTE_INSPECTION_JOIN_DOMAIN = (
    b"acfqp:v42-formal-transport-recovery:remote-inspection-join:v42r3r4"
)
RECOVERY_CLASSIFICATION_DOMAIN = (
    b"acfqp:v42-formal-transport-recovery:classification:v42r3r4"
)

RECOVERY_READ_ONLY_ACTIONS = (
    "READ_RETAINED_REMOTE_ARTIFACT_STATES",
    "READ_RETAINED_REMOTE_CANONICAL_DOCUMENTS_IF_REGULAR",
    "READ_USER_MANAGER_BINDING",
    "READ_EXACT_SYSTEMD_UNIT_PROPERTIES",
    "READ_PROC_MAINPID_CMDLINE_IF_PRESENT",
)
RECOVERY_TRANSPORT_STDOUT_CAP_BYTES = 64 * 1024**2
RECOVERY_TRANSPORT_STDERR_CAP_BYTES = 1024**2
RECOVERY_TRANSPORT_CAPTURE_PREFIX_BYTES = 4096
RECOVERY_TRANSPORT_MAX_STDIN_BYTES = 64 * 1024**2
RECOVERY_EXPECTED_REMOTE_STDOUT_FRAMING = "ONE_CANONICAL_JSON_DOCUMENT_PLUS_LF"
RECOVERY_EXPECTED_REMOTE_HOST_ALIAS = "jtl110gpu2"
RECOVERY_EXPECTED_REMOTE_HOSTNAME = "erzhu419-Super-Server"
RECOVERY_EXPECTED_REMOTE_UID = 1000
RECOVERY_EXPECTED_REMOTE_GID = 1000
RECOVERY_REMOTE_MODE = "--inspect-retained-launch-v42r3r4"
RECOVERY_REMOTE_INGRESS_SCHEMA = (
    "acfqp.v42r3r4_formal_launch_recovery_ingress"
)
RECOVERY_REMOTE_PYTHON_EXECUTABLE = "/usr/bin/python3"
RECOVERY_REMOTE_PYTHON_FLAGS = ("-I", "-S", "-B", "-c")
RECOVERY_TRANSPORT_EXECUTABLE = "/usr/bin/ssh"
RECOVERY_REMOTE_ENDPOINT_HOST = "tf290q6n.zjz-service.cn"
RECOVERY_REMOTE_ENDPOINT_PORT = 23035
RECOVERY_REMOTE_USER = "erzhu419"

RECOVERY_REMOTE_INSPECTION_ARTIFACTS = frozenset(
    {
        "launch_transport_attempt",
        "launch_admission_receipt",
        "service_wrapper_attestation",
    }
)
RECOVERY_REMOTE_RECOVERED_DOCUMENTS = frozenset(
    {
        "launch_transport_attempt",
        "launch_admission_receipt",
        "service_wrapper_attestation",
    }
)
RECOVERY_MANAGER_BINDING_FIELDS = frozenset(
    {
        "kernel_boot_id",
        "linger_enabled",
        "linger_path",
        "user_manager_invocation_id",
        "user_manager_main_pid",
        "user_manager_control_group",
    }
)
EXEC_START_PROPERTY_PRESENT_EMPTY = "PRESENT_EMPTY"
EXEC_START_PROPERTY_PRESENT_NONEMPTY = "PRESENT_NONEMPTY"
EXEC_START_PROPERTY_OMITTED_ONLY_FOR_NOT_FOUND_UNIT = (
    "OMITTED_ONLY_FOR_NOT_FOUND_UNIT"
)
RECOVERY_UNIT_OBSERVATION_FIELDS = frozenset(
    set(retained._UNIT_OBSERVATION_FIELDS)  # noqa: SLF001
    | {"ExecStartPropertyState"}
)
RECOVERY_REMOTE_FORMAL_ARTIFACT_FILENAMES = {
    "launch_transport_attempt": "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json",
    "launch_admission_receipt": "FORMAL_LAUNCH_ADMISSION_RECEIPT.json",
    "service_wrapper_attestation": "FORMAL_SERVICE_WRAPPER_ATTESTATION.json",
}
RECOVERY_MAX_REMOTE_JOURNAL_INVENTORY_ENTRIES = 64
RECOVERY_REMOTE_INITIAL_INVENTORY = frozenset(
    {
        "CONTROLLER_SOURCE_MANIFEST.json",
        "FORMAL_TRANSPORT_LOADER.py",
        "FORMAL_TRANSPORT_AUTHORITY.py",
        "FORMAL_TRANSPORT_RECEIVER.py",
        "FORMAL_TRANSPORT_PLAN.json",
        "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json",
    }
)
RECOVERY_REMOTE_ALLOWED_INVENTORY = RECOVERY_REMOTE_INITIAL_INVENTORY | {
    "FORMAL_LAUNCH_ADMISSION_RECEIPT.json",
    "FORMAL_SERVICE_WRAPPER_ATTESTATION.json",
}

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_SOURCE_FACT_FIELDS = frozenset(
    {
        "relative_path",
        "git_mode",
        "git_object_type",
        "git_blob_oid",
        "byte_count",
        "sha256",
    }
)
_CHILD_OBSERVATION_FIELDS = frozenset(
    {
        "exec_succeeded",
        "transport_observation_completed_without_local_error",
        "transport_materials_verified_after_child",
        "returncode",
        "timed_out",
        "stdin_expected_byte_count",
        "stdin_sent_byte_count",
        "stdin_sha256",
        "stdin_complete",
        "stdout_retained_byte_count",
        "stdout_retained_sha256",
        "stdout_prefix_byte_count",
        "stdout_prefix_hex",
        "stdout_total_byte_count",
        "stdout_sha256",
        "stdout_overflow",
        "stdout_eof",
        "stderr_prefix_byte_count",
        "stderr_prefix_hex",
        "stderr_total_byte_count",
        "stderr_sha256",
        "stderr_overflow",
        "stderr_eof",
    }
)

# Public aliases used by the sealed launcher and receiver without reaching into
# private implementation names.
RECOVERY_SOURCE_FACT_FIELDS = _SOURCE_FACT_FIELDS
RECOVERY_CHILD_OBSERVATION_FIELDS = _CHILD_OBSERVATION_FIELDS


class V42FormalTransportRecoveryError(ValueError):
    """A V42r3r4 recovery-only authority input changed."""


def _fail(message: str) -> NoReturn:
    raise V42FormalTransportRecoveryError(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain + b"\0" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _canonical_document(
    value: bytes | Mapping[str, Any], label: str,
) -> dict[str, Any]:
    try:
        if type(value) is bytes:
            if not 0 < len(value) <= 64 * 1024**2:
                _fail(label + " bytes changed emptiness or cap")
            result = loads_canonical_json(value)
            if canonical_json_bytes(result) != value:
                _fail(label + " bytes are not canonical")
        elif isinstance(value, Mapping):
            result = loads_canonical_json(canonical_json_bytes(dict(value)))
        else:
            _fail(label + " changed type")
    except V42FormalTransportRecoveryError:
        raise
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42FormalTransportRecoveryError(
            label + " is not canonical JSON"
        ) from error
    if type(result) is not dict:
        _fail(label + " is not one JSON object")
    return result


def _mapping(value: Any, fields: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail(label + " changed type")
    document = _canonical_document(value, label)
    if set(document) != fields:
        _fail(label + " field set changed")
    return document


def _hex(value: Any, length: int, label: str) -> str:
    pattern = _HEX40 if length == 40 else _HEX64
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail(label + f" is not lowercase hex{length}")
    return value


def _positive_int(value: Any, label: str, *, maximum: int) -> int:
    if type(value) is not int or not 0 < value <= maximum:
        _fail(label + " changed range or type")
    return value


def _base(schema: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": retained.authority.FORMAL_IDENTITY,
        "global_execution_ordinal": retained.authority.GLOBAL_EXECUTION_ORDINAL,
        "recovery_operation": RECOVERY_OPERATION,
    }


def _verify_base(document: Mapping[str, Any], schema: str, label: str) -> None:
    if any(
        document.get(field) != expected
        for field, expected in {
            "schema": schema,
            "schema_version": SCHEMA_VERSION,
            "formal_identity": retained.authority.FORMAL_IDENTITY,
            "global_execution_ordinal": retained.authority.GLOBAL_EXECUTION_ORDINAL,
            "recovery_operation": RECOVERY_OPERATION,
        }.items()
    ):
        _fail(label + " authority header changed")


def _verify_claimed_id(
    document: Mapping[str, Any], *, field: str, domain: bytes, label: str,
) -> None:
    claimed = _hex(document.get(field), 64, label + " ID")
    payload = dict(document)
    payload.pop(field, None)
    if claimed != _content_id(domain, payload):
        _fail(label + " content identity changed")


def _source_fact(value: Any) -> dict[str, Any]:
    fact = _mapping(value, _SOURCE_FACT_FIELDS, "recovery source fact")
    relative = fact["relative_path"]
    if (
        type(relative) is not str
        or not relative
        or relative.startswith("/")
        or str(PurePosixPath(relative)) != relative
        or any(part in {"", ".", ".."} for part in PurePosixPath(relative).parts)
        or fact["git_mode"] != "100644"
        or fact["git_object_type"] != "blob"
    ):
        _fail("recovery source fact path or Git kind changed")
    _hex(fact["git_blob_oid"], 40, "recovery source Git blob")
    _hex(fact["sha256"], 64, "recovery source SHA256")
    _positive_int(
        fact["byte_count"], "recovery source byte count", maximum=8 * 1024**2
    )
    return fact


def build_recovery_controller_source_manifest_v42r3r4(
    *, source_commit: str, source_tree: str,
    source_facts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind a sorted recovery TCB containing every mandatory source role."""

    commit = _hex(source_commit, 40, "recovery source commit")
    tree = _hex(source_tree, 40, "recovery source tree")
    if type(source_facts) not in {list, tuple}:
        _fail("recovery source facts changed type")
    if not (
        len(RECOVERY_CONTROLLER_REQUIRED_PATHS)
        <= len(source_facts)
        <= RECOVERY_CONTROLLER_MAX_SOURCE_FACTS
    ):
        _fail("recovery source fact inventory changed cardinality")
    facts = [_source_fact(value) for value in source_facts]
    paths = [fact["relative_path"] for fact in facts]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        _fail("recovery source facts are not exact sorted unique paths")
    if not RECOVERY_CONTROLLER_REQUIRED_PATHS <= set(paths):
        _fail("recovery source facts omitted a required TCB path")
    by_path = dict(zip(paths, facts, strict=True))
    payload = {
        **_base(RECOVERY_CONTROLLER_SOURCE_MANIFEST_SCHEMA),
        "source_commit": commit,
        "source_tree": tree,
        "source_facts": facts,
        "recovery_bootstrap_artifact": by_path[RECOVERY_BOOTSTRAP_RELATIVE],
        "recovery_launcher_artifact": by_path[RECOVERY_LAUNCHER_RELATIVE],
        "recovery_receiver_artifact": by_path[RECOVERY_RECEIVER_RELATIVE],
        "recovery_authority_artifact": by_path[RECOVERY_AUTHORITY_RELATIVE],
        "retained_authority_artifact": by_path[RETAINED_AUTHORITY_RELATIVE],
    }
    return {
        **payload,
        "recovery_controller_source_manifest_id": _content_id(
            RECOVERY_CONTROLLER_SOURCE_MANIFEST_DOMAIN, payload
        ),
    }


def verify_recovery_controller_source_manifest_v42r3r4(
    value: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "recovery controller source manifest")
    expected = build_recovery_controller_source_manifest_v42r3r4(
        source_commit=document.get("source_commit"),
        source_tree=document.get("source_tree"),
        source_facts=document.get("source_facts"),
    )
    if document != expected:
        _fail("recovery controller source manifest changed")
    return document


def _retained_raw_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("retained " + label + " must be supplied as exact bytes")
    expected = RETAINED_RAW_FACTS[label]
    if (
        len(raw) != expected["byte_count"]
        or hashlib.sha256(raw).hexdigest() != expected["sha256"]
    ):
        _fail("retained " + label + " raw fact changed")
    return _canonical_document(raw, "retained " + label)


def _retained_documents(
    *, root_identity_raw: bytes,
    retained_controller_source_manifest: bytes,
    formal_transport_plan: bytes,
    prepare_receipt: bytes,
    local_launch_attempt: bytes,
    formal_launch_transport_attempt: bytes,
    inner_network_start: bytes,
    parent_network_start: bytes,
    operation_outcome: bytes,
) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
]:
    root_identity = _retained_raw_document(root_identity_raw, "root_identity")
    if (
        set(root_identity)
        != {"schema", "schema_version", "path", "mode", "uid", "gid", "st_dev", "st_ino"}
        or root_identity["schema"]
        != "acfqp.v42_formal_successor_local_journal_root_identity.v42r3"
        or root_identity["schema_version"] != "42.3.0"
        or root_identity["path"] != str(RETAINED_LOCAL_ROOT)
        or root_identity["mode"] != 0o700
        or root_identity["uid"] != retained.authority.REMOTE_UID
        or root_identity["gid"] != retained.authority.REMOTE_GID
        or type(root_identity["st_dev"]) is not int
        or root_identity["st_dev"] <= 0
        or type(root_identity["st_ino"]) is not int
        or root_identity["st_ino"] <= 0
    ):
        _fail("retained root identity document changed")
    controller_raw = retained_controller_source_manifest
    controller_input = _retained_raw_document(
        controller_raw, "controller_source_manifest"
    )
    plan_raw = formal_transport_plan
    plan_input = _retained_raw_document(plan_raw, "formal_transport_plan")
    prepare_raw = prepare_receipt
    prepare_input = _retained_raw_document(prepare_raw, "prepare_receipt")
    local_raw = local_launch_attempt
    local_input = _retained_raw_document(local_raw, "local_launch_attempt")
    formal_attempt_raw = formal_launch_transport_attempt
    formal_attempt_input = _retained_raw_document(
        formal_attempt_raw, "formal_launch_transport_attempt"
    )
    inner_marker_input = _retained_raw_document(
        inner_network_start, "inner_network_start"
    )
    parent_marker_input = _retained_raw_document(
        parent_network_start, "parent_network_start"
    )
    outcome_input = _retained_raw_document(
        operation_outcome, "operation_outcome"
    )
    if inner_network_start != parent_network_start:
        _fail("retained inner and parent network-start bytes differ")
    try:
        controller = retained.verify_controller_source_manifest_v42r3(
            controller_input
        )
        plan = retained.verify_formal_transport_plan_v42r3(plan_input)
        prepare = retained.authority.verify_prepare_receipt_v42(
            prepare_input,
            fresh_terminal_preregistration_id=prepare_input.get(
                "fresh_terminal_preregistration_id"
            ),
            history_freshness_manifest_id=prepare_input.get(
                "history_freshness_manifest_id"
            ),
            require_live_source=False,
        )
        local = retained.authority.verify_local_launch_attempt_v42r1(
            local_input, prepare_receipt=prepare
        )
        launch = retained.verify_formal_launch_transport_attempt_v42r3(
            formal_attempt_input,
            formal_transport_plan=plan,
            prepare_receipt=prepare,
            local_launch_attempt=local,
        )
        marker = retained.verify_network_start_v42r3(
            inner_marker_input, formal_transport_plan=plan
        )
        outcome = retained.verify_operation_outcome_v42r3(
            outcome_input,
            formal_transport_plan=plan,
            operation=retained.OPERATION_LAUNCH,
            attempt_id=RETAINED_LOCAL_LAUNCH_ATTEMPT_ID,
        )
    except ValueError as error:
        raise V42FormalTransportRecoveryError(
            "retained V42r3r3 authority chain changed"
        ) from error
    exact = {
        "controller_source_manifest_id": RETAINED_CONTROLLER_SOURCE_MANIFEST_ID,
        "formal_transport_plan_id": RETAINED_FORMAL_TRANSPORT_PLAN_ID,
        "prepare_receipt_id": RETAINED_PREPARE_RECEIPT_ID,
        "local_launch_attempt_id": RETAINED_LOCAL_LAUNCH_ATTEMPT_ID,
        "formal_launch_transport_attempt_id": (
            RETAINED_FORMAL_LAUNCH_TRANSPORT_ATTEMPT_ID
        ),
        "formal_network_start_id": RETAINED_FORMAL_LAUNCH_NETWORK_START_ID,
        "formal_operation_outcome_id": RETAINED_FORMAL_LAUNCH_OPERATION_OUTCOME_ID,
    }
    documents = {
        "controller_source_manifest_id": controller[
            "controller_source_manifest_id"
        ],
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "prepare_receipt_id": prepare["prepare_receipt_id"],
        "local_launch_attempt_id": local["local_launch_attempt_id"],
        "formal_launch_transport_attempt_id": launch[
            "formal_launch_transport_attempt_id"
        ],
        "formal_network_start_id": marker["formal_network_start_id"],
        "formal_operation_outcome_id": outcome["formal_operation_outcome_id"],
    }
    if documents != exact:
        _fail("retained V42r3r3 occurrence identity changed")
    if (
        controller["source_commit"] != RETAINED_CONTROLLER_SOURCE_COMMIT
        or controller["source_tree"] != RETAINED_CONTROLLER_SOURCE_TREE
        or plan["controller_source_manifest_id"]
        != RETAINED_CONTROLLER_SOURCE_MANIFEST_ID
        or prepare["source_commit"] != plan["source_commit"]
        or prepare["source_tree"] != plan["source_tree"]
        or prepare["source_manifest_id"] != plan["source_manifest_id"]
        or prepare["transport_manifest_id"] != plan["transport_manifest_id"]
        or launch["formal_transport_plan_id"]
        != RETAINED_FORMAL_TRANSPORT_PLAN_ID
        or launch["local_launch_attempt_id"]
        != RETAINED_LOCAL_LAUNCH_ATTEMPT_ID
        or launch["operation"] != retained.OPERATION_LAUNCH
        or marker["formal_transport_plan_id"]
        != RETAINED_FORMAL_TRANSPORT_PLAN_ID
        or marker["attempt_id"] != RETAINED_LOCAL_LAUNCH_ATTEMPT_ID
        or marker["operation"] != retained.OPERATION_LAUNCH
        or outcome["formal_transport_plan_id"]
        != RETAINED_FORMAL_TRANSPORT_PLAN_ID
        or outcome["attempt_id"] != RETAINED_LOCAL_LAUNCH_ATTEMPT_ID
        or outcome["outcome_class"] != retained.OUTCOME_POST_MARKER_AMBIGUOUS
        or outcome["network_start_marker_present"] is not True
        or outcome["receipt_fact"] is not None
        or outcome["controller_same_effect_dispatch_replay_allowed"] is not False
    ):
        _fail("retained V42r3r3 post-marker replay semantics changed")
    if parent_marker_input != marker:
        _fail("retained parent marker canonical document changed")
    return root_identity, controller, plan, prepare, local, launch, marker, outcome


def build_retained_launch_occurrence_v42r3r4(
    *, root_identity_raw: bytes,
    retained_controller_source_manifest: bytes,
    formal_transport_plan: bytes,
    prepare_receipt: bytes,
    local_launch_attempt: bytes,
    formal_launch_transport_attempt: bytes,
    inner_network_start: bytes,
    parent_network_start: bytes,
    operation_outcome: bytes,
) -> dict[str, Any]:
    """Bind the exact frozen launch occurrence and its irreversible marker."""

    root_identity, controller, plan, prepare, local, launch, marker, outcome = (
        _retained_documents(
            root_identity_raw=root_identity_raw,
            retained_controller_source_manifest=(
                retained_controller_source_manifest
            ),
            formal_transport_plan=formal_transport_plan,
            prepare_receipt=prepare_receipt,
            local_launch_attempt=local_launch_attempt,
            formal_launch_transport_attempt=formal_launch_transport_attempt,
            inner_network_start=inner_network_start,
            parent_network_start=parent_network_start,
            operation_outcome=operation_outcome,
        )
    )
    payload = {
        **_base(RETAINED_LAUNCH_OCCURRENCE_SCHEMA),
        "retained_root_identity": root_identity,
        "retained_controller_source_manifest": controller,
        "formal_transport_plan": plan,
        "prepare_receipt": prepare,
        "local_launch_attempt": local,
        "formal_launch_transport_attempt": launch,
        "inner_network_start": marker,
        "parent_network_start": marker,
        "launch_operation_outcome": outcome,
        "retained_raw_facts": {
            label: dict(fact) for label, fact in RETAINED_RAW_FACTS.items()
        },
        "retained_root_identity_sha256": RETAINED_RAW_FACTS[
            "root_identity"
        ]["sha256"],
        "retained_controller_source_manifest_id": (
            RETAINED_CONTROLLER_SOURCE_MANIFEST_ID
        ),
        "retained_controller_source_commit": RETAINED_CONTROLLER_SOURCE_COMMIT,
        "retained_controller_source_tree": RETAINED_CONTROLLER_SOURCE_TREE,
        "retained_formal_transport_plan_id": RETAINED_FORMAL_TRANSPORT_PLAN_ID,
        "retained_prepare_receipt_id": RETAINED_PREPARE_RECEIPT_ID,
        "retained_local_launch_attempt_id": RETAINED_LOCAL_LAUNCH_ATTEMPT_ID,
        "retained_formal_launch_transport_attempt_id": (
            RETAINED_FORMAL_LAUNCH_TRANSPORT_ATTEMPT_ID
        ),
        "retained_formal_launch_network_start_id": (
            RETAINED_FORMAL_LAUNCH_NETWORK_START_ID
        ),
        "retained_formal_launch_operation_outcome_id": (
            RETAINED_FORMAL_LAUNCH_OPERATION_OUTCOME_ID
        ),
        "inner_and_parent_network_start_bytes_identical": True,
        "retained_network_start_marker_present": True,
        "retained_exact_transport_receipt_present": False,
        "retained_same_effect_dispatch_replay_allowed": False,
        "retained_new_scientific_execution_authorized": False,
        "retained_historical_execution_status": "UNKNOWN_NOT_INFERRED",
        "current_remote_absence_is_historical_never_started_proof": False,
    }
    return {
        **payload,
        "retained_launch_occurrence_id": _content_id(
            RETAINED_LAUNCH_OCCURRENCE_DOMAIN, payload
        ),
    }


def verify_retained_launch_occurrence_v42r3r4(
    value: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "retained launch occurrence")
    expected = build_retained_launch_occurrence_v42r3r4(
        root_identity_raw=canonical_json_bytes(document.get("retained_root_identity")),
        retained_controller_source_manifest=canonical_json_bytes(
            document.get("retained_controller_source_manifest")
        ),
        formal_transport_plan=canonical_json_bytes(
            document.get("formal_transport_plan")
        ),
        prepare_receipt=canonical_json_bytes(document.get("prepare_receipt")),
        local_launch_attempt=canonical_json_bytes(
            document.get("local_launch_attempt")
        ),
        formal_launch_transport_attempt=canonical_json_bytes(
            document.get("formal_launch_transport_attempt")
        ),
        inner_network_start=canonical_json_bytes(
            document.get("inner_network_start")
        ),
        parent_network_start=canonical_json_bytes(
            document.get("parent_network_start")
        ),
        operation_outcome=canonical_json_bytes(
            document.get("launch_operation_outcome")
        ),
    )
    if document != expected:
        _fail("retained launch occurrence changed")
    return document


def build_recovery_plan_v42r3r4(
    *, recovery_controller_source_manifest: Mapping[str, Any],
    retained_launch_occurrence: Mapping[str, Any],
) -> dict[str, Any]:
    manifest = verify_recovery_controller_source_manifest_v42r3r4(
        recovery_controller_source_manifest
    )
    occurrence = verify_retained_launch_occurrence_v42r3r4(
        retained_launch_occurrence
    )
    old_plan = occurrence["formal_transport_plan"]
    old_launch = occurrence["formal_launch_transport_attempt"]
    if (
        old_plan["remote_target_alias"] != RECOVERY_EXPECTED_REMOTE_HOST_ALIAS
        or old_plan["expected_remote_hostname"]
        != RECOVERY_EXPECTED_REMOTE_HOSTNAME
        or old_plan["observed_remote_hostname"]
        != RECOVERY_EXPECTED_REMOTE_HOSTNAME
        or old_plan["observed_remote_uid"] != RECOVERY_EXPECTED_REMOTE_UID
        or old_plan["observed_remote_gid"] != RECOVERY_EXPECTED_REMOTE_GID
    ):
        _fail("retained recovery target identity changed")
    ingress_template = {
        "schema": RECOVERY_REMOTE_INGRESS_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "retained_launch_occurrence_id": occurrence[
            "retained_launch_occurrence_id"
        ],
        "retained_formal_transport_plan": old_plan,
        "retained_formal_transport_plan_id": RETAINED_FORMAL_TRANSPORT_PLAN_ID,
        "retained_local_launch_attempt_id": RETAINED_LOCAL_LAUNCH_ATTEMPT_ID,
        "retained_remote_journal_root": old_plan["remote_journal_root"],
        "retained_systemd_unit_name": old_launch["unit_name"],
        "expected_remote_hostname": RECOVERY_EXPECTED_REMOTE_HOSTNAME,
        "expected_remote_uid": RECOVERY_EXPECTED_REMOTE_UID,
        "expected_remote_gid": RECOVERY_EXPECTED_REMOTE_GID,
        "recovery_inspection_ordinal": RECOVERY_INSPECTION_ORDINAL,
    }
    payload = {
        **_base(RECOVERY_PLAN_SCHEMA),
        "recovery_controller_source_manifest": manifest,
        "retained_launch_occurrence": occurrence,
        "recovery_controller_source_manifest_id": manifest[
            "recovery_controller_source_manifest_id"
        ],
        "retained_launch_occurrence_id": occurrence[
            "retained_launch_occurrence_id"
        ],
        "retained_formal_transport_plan_id": RETAINED_FORMAL_TRANSPORT_PLAN_ID,
        "retained_local_launch_attempt_id": RETAINED_LOCAL_LAUNCH_ATTEMPT_ID,
        "retained_remote_target_alias": old_plan["remote_target_alias"],
        "retained_expected_remote_hostname": old_plan[
            "expected_remote_hostname"
        ],
        "retained_remote_journal_root": old_plan["remote_journal_root"],
        "retained_systemd_unit_name": old_launch["unit_name"],
        "recovery_inspection_ordinal": RECOVERY_INSPECTION_ORDINAL,
        "authorized_remote_modes": [RECOVERY_REMOTE_MODE],
        "recovery_receiver_artifact": manifest[
            "recovery_receiver_artifact"
        ],
        "canonical_remote_ingress_template_without_recovery_plan_id": (
            ingress_template
        ),
        "transport_executable": RECOVERY_TRANSPORT_EXECUTABLE,
        "remote_endpoint_host": RECOVERY_REMOTE_ENDPOINT_HOST,
        "remote_endpoint_port": RECOVERY_REMOTE_ENDPOINT_PORT,
        "remote_user": RECOVERY_REMOTE_USER,
        "authorized_authenticated_remote_actions": list(
            RECOVERY_READ_ONLY_ACTIONS
        ),
        "authenticated_remote_filesystem_mutation_authorized": False,
        "authenticated_systemd_lifecycle_mutation_authorized": False,
        "retained_same_effect_dispatch_replay_allowed": False,
        "new_scientific_execution_authorized": False,
        "current_remote_absence_is_historical_never_started_proof": False,
        "external_local_and_ssh_assumptions_observed_or_attested": False,
        "end_to_end_remote_mutation_absence_claimed": False,
        "expected_remote_stdout_framing": (
            RECOVERY_EXPECTED_REMOTE_STDOUT_FRAMING
        ),
        "stdout_cap_bytes": RECOVERY_TRANSPORT_STDOUT_CAP_BYTES,
        "stderr_cap_bytes": RECOVERY_TRANSPORT_STDERR_CAP_BYTES,
        "capture_prefix_bytes": RECOVERY_TRANSPORT_CAPTURE_PREFIX_BYTES,
    }
    return {
        **payload,
        "recovery_plan_id": _content_id(RECOVERY_PLAN_DOMAIN, payload),
    }


def verify_recovery_plan_v42r3r4(
    value: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "recovery plan")
    expected = build_recovery_plan_v42r3r4(
        recovery_controller_source_manifest=document.get(
            "recovery_controller_source_manifest"
        ),
        retained_launch_occurrence=document.get("retained_launch_occurrence"),
    )
    if document != expected:
        _fail("recovery plan changed")
    return document


def build_recovery_transport_ingress_v42r3r4(
    *, recovery_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Reconstruct the sole canonical receiver stdin after the plan ID exists."""

    plan = verify_recovery_plan_v42r3r4(recovery_plan)
    template = plan[
        "canonical_remote_ingress_template_without_recovery_plan_id"
    ]
    return {
        "schema": template["schema"],
        "schema_version": template["schema_version"],
        "recovery_plan_id": plan["recovery_plan_id"],
        **{
            key: value
            for key, value in template.items()
            if key not in {"schema", "schema_version"}
        },
    }


def _recovery_remote_command_projection(
    *, recovery_plan: Mapping[str, Any], ingress_raw: bytes,
) -> dict[str, Any]:
    plan = verify_recovery_plan_v42r3r4(recovery_plan)
    receiver = plan["recovery_receiver_artifact"]
    return {
        "ordered_remote_python_argv_semantics": [
            {"literal": RECOVERY_REMOTE_PYTHON_EXECUTABLE},
            *({"literal": flag} for flag in RECOVERY_REMOTE_PYTHON_FLAGS),
            {
                "receiver_source": {
                    "sha256": receiver["sha256"],
                    "byte_count": receiver["byte_count"],
                }
            },
            {"literal": RECOVERY_REMOTE_MODE},
            {"receiver_source_sha256": receiver["sha256"]},
            {"receiver_source_byte_count_decimal": str(receiver["byte_count"])},
            {"canonical_ingress_sha256": hashlib.sha256(ingress_raw).hexdigest()},
            {"canonical_ingress_byte_count_decimal": str(len(ingress_raw))},
            {"recovery_plan_id": plan["recovery_plan_id"]},
        ],
        "transport_executable": RECOVERY_TRANSPORT_EXECUTABLE,
        "remote_endpoint_host": RECOVERY_REMOTE_ENDPOINT_HOST,
        "remote_endpoint_port": RECOVERY_REMOTE_ENDPOINT_PORT,
        "remote_user": RECOVERY_REMOTE_USER,
        "ssh_login_shell_exactness_attested": False,
    }


def build_recovery_inspection_attempt_v42r3r4(
    *, recovery_plan: Mapping[str, Any],
) -> dict[str, Any]:
    plan = verify_recovery_plan_v42r3r4(recovery_plan)
    ingress = build_recovery_transport_ingress_v42r3r4(recovery_plan=plan)
    ingress_raw = canonical_json_bytes(ingress)
    ingress_fact = {
        "byte_count": len(ingress_raw),
        "sha256": hashlib.sha256(ingress_raw).hexdigest(),
    }
    payload = {
        **_base(RECOVERY_INSPECTION_ATTEMPT_SCHEMA),
        "recovery_plan_id": plan["recovery_plan_id"],
        "retained_launch_occurrence_id": plan["retained_launch_occurrence_id"],
        "retained_local_launch_attempt_id": RETAINED_LOCAL_LAUNCH_ATTEMPT_ID,
        "recovery_inspection_ordinal": RECOVERY_INSPECTION_ORDINAL,
        "authorized_remote_mode": RECOVERY_REMOTE_MODE,
        "recovery_receiver_artifact": plan["recovery_receiver_artifact"],
        "canonical_remote_ingress": ingress,
        "canonical_remote_ingress_fact": ingress_fact,
        "remote_command_projection": _recovery_remote_command_projection(
            recovery_plan=plan, ingress_raw=ingress_raw
        ),
        "network_dispatch_started": False,
        "authenticated_remote_mutation_authorized": False,
        "authenticated_systemd_lifecycle_mutation_authorized": False,
        "retained_same_effect_dispatch_replay_allowed": False,
        "new_scientific_execution_authorized": False,
        "controller_same_recovery_dispatch_replay_allowed": False,
    }
    return {
        **payload,
        "recovery_inspection_attempt_id": _content_id(
            RECOVERY_INSPECTION_ATTEMPT_DOMAIN, payload
        ),
    }


def verify_recovery_inspection_attempt_v42r3r4(
    value: bytes | Mapping[str, Any], *, recovery_plan: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "recovery inspection attempt")
    expected = build_recovery_inspection_attempt_v42r3r4(
        recovery_plan=recovery_plan
    )
    if document != expected:
        _fail("recovery inspection attempt changed")
    return document


def _capture_prefix(
    fact: Mapping[str, Any], *, stream: str, retained_count: int,
) -> bytes:
    count = fact[f"{stream}_prefix_byte_count"]
    value = fact[f"{stream}_prefix_hex"]
    if (
        type(count) is not int
        or not 0 <= count <= RECOVERY_TRANSPORT_CAPTURE_PREFIX_BYTES
        or type(value) is not str
        or len(value) != 2 * count
        or re.fullmatch(r"[0-9a-f]*", value) is None
        or count
        != min(retained_count, RECOVERY_TRANSPORT_CAPTURE_PREFIX_BYTES)
    ):
        _fail("recovery child " + stream + " prefix changed")
    return bytes.fromhex(value)


def _verify_child_observation(value: Any) -> tuple[dict[str, Any], bool]:
    child = _mapping(
        value, _CHILD_OBSERVATION_FIELDS, "recovery child observation"
    )
    for field in (
        "exec_succeeded",
        "transport_observation_completed_without_local_error",
        "transport_materials_verified_after_child",
        "timed_out",
        "stdin_complete",
        "stdout_overflow",
        "stdout_eof",
        "stderr_overflow",
        "stderr_eof",
    ):
        if type(child[field]) is not bool:
            _fail("recovery child observation flag changed")
    returncode = child["returncode"]
    if returncode is not None and (
        type(returncode) is not int or not -(2**31) <= returncode < 2**31
    ):
        _fail("recovery child return code changed")
    if child["exec_succeeded"] is False and returncode is not None:
        _fail("recovery child invented a return code before exec")
    for field in (
        "stdin_expected_byte_count",
        "stdin_sent_byte_count",
        "stdout_retained_byte_count",
        "stdout_total_byte_count",
        "stderr_total_byte_count",
    ):
        if type(child[field]) is not int or not 0 <= child[field] < 2**63:
            _fail("recovery child byte count changed")
    if not 0 < child["stdin_expected_byte_count"] <= RECOVERY_TRANSPORT_MAX_STDIN_BYTES:
        _fail("recovery child stdin expected byte count changed")
    for field in (
        "stdin_sha256",
        "stdout_retained_sha256",
        "stdout_sha256",
        "stderr_sha256",
    ):
        _hex(child[field], 64, "recovery child " + field)
    stdout_prefix = _capture_prefix(
        child,
        stream="stdout",
        retained_count=child["stdout_retained_byte_count"],
    )
    stderr_prefix = _capture_prefix(
        child,
        stream="stderr",
        retained_count=child["stderr_total_byte_count"],
    )
    empty_sha = hashlib.sha256(b"").hexdigest()
    if (
        child["stdin_sent_byte_count"] > child["stdin_expected_byte_count"]
        or child["stdin_complete"]
        and child["stdin_sent_byte_count"]
        != child["stdin_expected_byte_count"]
        or child["stdout_retained_byte_count"]
        != min(
            child["stdout_total_byte_count"],
            RECOVERY_TRANSPORT_STDOUT_CAP_BYTES + 1,
        )
        or child["stdout_overflow"]
        is not (
            child["stdout_total_byte_count"]
            > RECOVERY_TRANSPORT_STDOUT_CAP_BYTES
        )
        or child["stderr_overflow"]
        is not (
            child["stderr_total_byte_count"]
            > RECOVERY_TRANSPORT_STDERR_CAP_BYTES
        )
        or child["stdout_retained_byte_count"] <= len(stdout_prefix)
        and hashlib.sha256(stdout_prefix).hexdigest()
        != child["stdout_retained_sha256"]
        or child["stderr_total_byte_count"] <= len(stderr_prefix)
        and hashlib.sha256(stderr_prefix).hexdigest() != child["stderr_sha256"]
        or not child["stdout_overflow"]
        and (
            child["stdout_retained_byte_count"]
            != child["stdout_total_byte_count"]
            or child["stdout_retained_sha256"] != child["stdout_sha256"]
        )
        or child["stdout_total_byte_count"] == 0
        and (
            child["stdout_prefix_byte_count"] != 0
            or child["stdout_sha256"] != empty_sha
        )
        or child["stderr_total_byte_count"] == 0
        and (
            child["stderr_prefix_byte_count"] != 0
            or child["stderr_sha256"] != empty_sha
            or child["stderr_overflow"]
        )
    ):
        _fail("recovery child stream cardinality or digest changed")
    closed_exactly = bool(
        child["exec_succeeded"]
        and child["transport_observation_completed_without_local_error"]
        and child["transport_materials_verified_after_child"]
        and child["returncode"] == 0
        and not child["timed_out"]
        and child["stdin_complete"]
        and child["stdin_sent_byte_count"]
        == child["stdin_expected_byte_count"]
        and not child["stdout_overflow"]
        and child["stdout_eof"]
        and child["stdout_total_byte_count"]
        == child["stdout_retained_byte_count"]
        and child["stderr_total_byte_count"] == 0
        and child["stderr_eof"]
    )
    return child, closed_exactly


def build_bounded_child_transport_observation_v42r3r4(
    *, recovery_plan: Mapping[str, Any],
    recovery_inspection_attempt: Mapping[str, Any],
    child_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist bounded process/stream facts before accepting remote output."""

    plan = verify_recovery_plan_v42r3r4(recovery_plan)
    attempt = verify_recovery_inspection_attempt_v42r3r4(
        recovery_inspection_attempt, recovery_plan=plan
    )
    child, closed_exactly = _verify_child_observation(child_observation)
    ingress_fact = attempt["canonical_remote_ingress_fact"]
    if (
        child["stdin_expected_byte_count"] != ingress_fact["byte_count"]
        or child["stdin_sha256"] != ingress_fact["sha256"]
    ):
        _fail("recovery child stdin differs from authorized canonical ingress")
    payload = {
        **_base(BOUNDED_CHILD_TRANSPORT_OBSERVATION_SCHEMA),
        "recovery_plan_id": plan["recovery_plan_id"],
        "recovery_inspection_attempt_id": attempt[
            "recovery_inspection_attempt_id"
        ],
        "child_observation": child,
        "authorized_remote_mode": attempt["authorized_remote_mode"],
        "recovery_receiver_artifact": attempt["recovery_receiver_artifact"],
        "canonical_remote_ingress_fact": ingress_fact,
        "remote_command_projection": attempt["remote_command_projection"],
        "process_closed_exactly": closed_exactly,
        "network_dispatch_may_have_started": True,
        "observation_persisted_before_remote_receipt_acceptance_required": True,
        "formal_remote_inspection_authenticated_by_this_observation": False,
        "retained_same_effect_dispatch_replay_allowed": False,
        "controller_same_recovery_dispatch_replay_allowed": False,
        "authenticated_remote_mutation_authorized": False,
        "authenticated_systemd_lifecycle_mutation_authorized": False,
        "end_to_end_remote_mutation_absence_claimed": False,
    }
    return {
        **payload,
        "bounded_child_transport_observation_id": _content_id(
            BOUNDED_CHILD_TRANSPORT_OBSERVATION_DOMAIN, payload
        ),
    }


def verify_bounded_child_transport_observation_v42r3r4(
    value: bytes | Mapping[str, Any], *, recovery_plan: Mapping[str, Any],
    recovery_inspection_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(
        value, "bounded child transport observation"
    )
    expected = build_bounded_child_transport_observation_v42r3r4(
        recovery_plan=recovery_plan,
        recovery_inspection_attempt=recovery_inspection_attempt,
        child_observation=document.get("child_observation"),
    )
    if document != expected:
        _fail("bounded child transport observation changed")
    return document


def _verify_recovery_unit_observation(
    value: Any, *, retained_plan: Mapping[str, Any],
) -> dict[str, Any]:
    unit = _mapping(
        value, RECOVERY_UNIT_OBSERVATION_FIELDS, "recovery unit observation"
    )
    exec_state = unit["ExecStartPropertyState"]
    old_unit = {
        field: unit[field]
        for field in retained._UNIT_OBSERVATION_FIELDS  # noqa: SLF001
    }
    try:
        retained._inspection_unit_observation(  # noqa: SLF001
            old_unit,
            plan=retained_plan,
            attempt_id=RETAINED_LOCAL_LAUNCH_ATTEMPT_ID,
        )
    except retained.V42FormalTransportSuccessorError as error:
        raise V42FormalTransportRecoveryError(
            "recovery unit authority changed"
        ) from error
    if (
        old_unit["LoadState"] == "loaded"
        and exec_state != EXEC_START_PROPERTY_PRESENT_NONEMPTY
        or old_unit["LoadState"] == "not-found"
        and exec_state
        not in {
            EXEC_START_PROPERTY_PRESENT_EMPTY,
            EXEC_START_PROPERTY_OMITTED_ONLY_FOR_NOT_FOUND_UNIT,
        }
        or old_unit["LoadState"] not in {"loaded", "not-found"}
        and exec_state != EXEC_START_PROPERTY_PRESENT_EMPTY
    ):
        _fail("recovery ExecStart property state changed")
    return unit


def _verify_recovered_remote_documents(
    *, recovered_documents: Any, artifact_states: Any,
    retained_occurrence: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    states = _mapping(
        artifact_states,
        RECOVERY_REMOTE_INSPECTION_ARTIFACTS,
        "recovery remote artifact states",
    )
    if any(value not in {"ABSENT", "REGULAR_FILE"} for value in states.values()):
        _fail("recovery remote artifact state vocabulary changed")
    if not isinstance(recovered_documents, Mapping):
        _fail("recovery recovered documents changed type")
    recovered = _canonical_document(
        recovered_documents, "recovery recovered documents"
    )
    if (
        not set(recovered) <= RECOVERY_REMOTE_RECOVERED_DOCUMENTS
        or any(type(value) is not dict for value in recovered.values())
        or any(
            (states[name] == "REGULAR_FILE") != (name in recovered)
            for name in RECOVERY_REMOTE_RECOVERED_DOCUMENTS
        )
    ):
        _fail("recovery recovered document inventory changed")
    plan = retained_occurrence["formal_transport_plan"]
    prepare = retained_occurrence["prepare_receipt"]
    local = retained_occurrence["local_launch_attempt"]
    try:
        if "launch_transport_attempt" in recovered:
            launch = retained.verify_formal_launch_transport_attempt_v42r3(
                recovered["launch_transport_attempt"],
                formal_transport_plan=plan,
                prepare_receipt=prepare,
                local_launch_attempt=local,
            )
        else:
            launch = None
        if "launch_admission_receipt" in recovered:
            if launch is None:
                _fail("recovered admission omitted launch attempt")
            admission = retained.verify_launch_admission_receipt_v42r3(
                recovered["launch_admission_receipt"],
                formal_transport_plan=plan,
                launch_transport_attempt=launch,
            )
        else:
            admission = None
        if "service_wrapper_attestation" in recovered:
            if launch is None or admission is None:
                _fail("recovered wrapper omitted its authority chain")
            gate = retained.verify_cross_version_scientific_state_gate_v42r3(
                formal_transport_plan=plan,
                operation="SERVICE_WRAPPER",
                legacy_scientific_phase={"phase": "POST_PREPARE_PRELAUNCH"},
                effect_authorized=True,
            )
            retained.verify_service_wrapper_attestation_v42r3(
                recovered["service_wrapper_attestation"],
                formal_transport_plan=plan,
                launch_transport_attempt=launch,
                launch_admission_receipt=admission,
                cross_version_scientific_state_gate=gate,
            )
    except retained.V42FormalTransportSuccessorError as error:
        raise V42FormalTransportRecoveryError(
            "recovered retained authority chain changed"
        ) from error
    return recovered, states


def build_remote_read_only_inspection_v42r3r4(
    *, recovery_plan: Mapping[str, Any],
    recovery_inspection_attempt: Mapping[str, Any],
    observed_remote_hostname: str,
    observed_remote_uid: int,
    observed_remote_gid: int,
    manager_binding: Mapping[str, Any],
    unit_observation: Mapping[str, Any],
    retained_remote_journal_state: str,
    retained_remote_journal_inventory: Sequence[str],
    artifact_states: Mapping[str, str],
    recovered_documents: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify the standalone receiver's exact r3r4 current-state receipt."""

    plan = verify_recovery_plan_v42r3r4(recovery_plan)
    attempt = verify_recovery_inspection_attempt_v42r3r4(
        recovery_inspection_attempt, recovery_plan=plan
    )
    if (
        observed_remote_hostname != RECOVERY_EXPECTED_REMOTE_HOSTNAME
        or observed_remote_uid != retained.authority.REMOTE_UID
        or observed_remote_gid != retained.authority.REMOTE_GID
    ):
        _fail("recovery observed remote identity changed")
    occurrence = plan["retained_launch_occurrence"]
    old_plan = occurrence["formal_transport_plan"]
    try:
        manager, _matches = retained._effect_manager_binding(  # noqa: SLF001
            manager_binding, plan=old_plan, require_match=False
        )
    except retained.V42FormalTransportSuccessorError as error:
        raise V42FormalTransportRecoveryError(
            "recovery manager binding changed"
        ) from error
    unit = _verify_recovery_unit_observation(
        unit_observation, retained_plan=old_plan
    )
    recovered, states = _verify_recovered_remote_documents(
        recovered_documents=recovered_documents,
        artifact_states=artifact_states,
        retained_occurrence=occurrence,
    )
    if type(retained_remote_journal_inventory) not in {list, tuple}:
        _fail("retained remote journal inventory changed type")
    inventory = list(retained_remote_journal_inventory)
    if (
        len(inventory) > RECOVERY_MAX_REMOTE_JOURNAL_INVENTORY_ENTRIES
        or inventory != sorted(inventory)
        or len(inventory) != len(set(inventory))
        or any(type(name) is not str for name in inventory)
        or not set(inventory) <= RECOVERY_REMOTE_ALLOWED_INVENTORY
    ):
        _fail("retained remote journal inventory changed")
    if retained_remote_journal_state == "ABSENT":
        if inventory or any(state != "ABSENT" for state in states.values()):
            _fail("absent retained journal invented artifacts")
    elif retained_remote_journal_state == "DIRECTORY":
        if (
            not RECOVERY_REMOTE_INITIAL_INVENTORY <= set(inventory)
            or "FORMAL_SERVICE_WRAPPER_ATTESTATION.json" in inventory
            and "FORMAL_LAUNCH_ADMISSION_RECEIPT.json" not in inventory
        ):
            _fail("retained journal directory inventory changed")
        for name, filename in RECOVERY_REMOTE_FORMAL_ARTIFACT_FILENAMES.items():
            if (states[name] == "REGULAR_FILE") != (filename in inventory):
                _fail("retained journal state/inventory join changed")
    else:
        _fail("retained remote journal state changed")
    payload = {
        **_base(REMOTE_READ_ONLY_INSPECTION_SCHEMA),
        "recovery_plan_id": plan["recovery_plan_id"],
        "retained_launch_occurrence_id": plan["retained_launch_occurrence_id"],
        "retained_formal_transport_plan_id": RETAINED_FORMAL_TRANSPORT_PLAN_ID,
        "retained_local_launch_attempt_id": RETAINED_LOCAL_LAUNCH_ATTEMPT_ID,
        "recovery_inspection_ordinal": RECOVERY_INSPECTION_ORDINAL,
        "retained_remote_journal_root": plan["retained_remote_journal_root"],
        "retained_systemd_unit_name": plan["retained_systemd_unit_name"],
        "observed_remote_hostname": observed_remote_hostname,
        "observed_remote_uid": observed_remote_uid,
        "observed_remote_gid": observed_remote_gid,
        "manager_binding": manager,
        "unit_observation": unit,
        "retained_remote_journal_state": retained_remote_journal_state,
        "retained_remote_journal_inventory": inventory,
        "artifact_states": states,
        "recovered_documents": recovered,
        "authenticated_body_remote_filesystem_mutation_performed": False,
        "systemd_lifecycle_mutation_performed": False,
        "same_effect_reissued": False,
        "end_to_end_absence_claimed": False,
    }
    return {
        **payload,
        "remote_inspection_id": _content_id(
            REMOTE_READ_ONLY_INSPECTION_DOMAIN, payload
        ),
    }


def verify_remote_read_only_inspection_v42r3r4(
    value: bytes | Mapping[str, Any], *, recovery_plan: Mapping[str, Any],
    recovery_inspection_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "remote read-only inspection")
    expected = build_remote_read_only_inspection_v42r3r4(
        recovery_plan=recovery_plan,
        recovery_inspection_attempt=recovery_inspection_attempt,
        observed_remote_hostname=document.get("observed_remote_hostname"),
        observed_remote_uid=document.get("observed_remote_uid"),
        observed_remote_gid=document.get("observed_remote_gid"),
        manager_binding=document.get("manager_binding"),
        unit_observation=document.get("unit_observation"),
        retained_remote_journal_state=document.get(
            "retained_remote_journal_state"
        ),
        retained_remote_journal_inventory=document.get(
            "retained_remote_journal_inventory"
        ),
        artifact_states=document.get("artifact_states"),
        recovered_documents=document.get("recovered_documents"),
    )
    if document != expected:
        _fail("remote read-only inspection changed")
    return document


def _stdout_matches_remote_document(
    child: Mapping[str, Any], remote_document: Mapping[str, Any],
) -> bool:
    raw = canonical_json_bytes(dict(remote_document)) + b"\n"
    prefix = raw[:RECOVERY_TRANSPORT_CAPTURE_PREFIX_BYTES]
    digest = hashlib.sha256(raw).hexdigest()
    return bool(
        len(raw) <= RECOVERY_TRANSPORT_STDOUT_CAP_BYTES
        and child["stdout_retained_byte_count"] == len(raw)
        and child["stdout_retained_sha256"] == digest
        and child["stdout_prefix_byte_count"] == len(prefix)
        and child["stdout_prefix_hex"] == prefix.hex()
        and child["stdout_total_byte_count"] == len(raw)
        and child["stdout_sha256"] == digest
        and child["stdout_overflow"] is False
        and child["stdout_eof"] is True
        and child["stderr_prefix_byte_count"] == 0
        and child["stderr_prefix_hex"] == ""
        and child["stderr_total_byte_count"] == 0
        and child["stderr_sha256"] == hashlib.sha256(b"").hexdigest()
        and child["stderr_overflow"] is False
        and child["stderr_eof"] is True
    )


def build_remote_inspection_join_v42r3r4(
    *, recovery_plan: Mapping[str, Any],
    recovery_inspection_attempt: Mapping[str, Any],
    bounded_child_transport_observation: Mapping[str, Any],
    remote_read_only_inspection: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate one exact standalone r3r4 inspection to bounded stdout."""

    plan = verify_recovery_plan_v42r3r4(recovery_plan)
    attempt = verify_recovery_inspection_attempt_v42r3r4(
        recovery_inspection_attempt, recovery_plan=plan
    )
    observation = verify_bounded_child_transport_observation_v42r3r4(
        bounded_child_transport_observation,
        recovery_plan=plan,
        recovery_inspection_attempt=attempt,
    )
    if observation["process_closed_exactly"] is not True:
        _fail("remote inspection transport did not close exactly")
    inspection = verify_remote_read_only_inspection_v42r3r4(
        remote_read_only_inspection,
        recovery_plan=plan,
        recovery_inspection_attempt=attempt,
    )
    if (
        inspection["authenticated_body_remote_filesystem_mutation_performed"]
        is not False
        or inspection["systemd_lifecycle_mutation_performed"] is not False
        or inspection["same_effect_reissued"] is not False
        or inspection["end_to_end_absence_claimed"] is not False
        or not _stdout_matches_remote_document(
            observation["child_observation"], inspection
        )
    ):
        _fail("remote inspection authority or exact stdout join changed")
    payload = {
        **_base(REMOTE_INSPECTION_JOIN_SCHEMA),
        "recovery_plan_id": plan["recovery_plan_id"],
        "recovery_inspection_attempt_id": attempt[
            "recovery_inspection_attempt_id"
        ],
        "bounded_child_transport_observation_id": observation[
            "bounded_child_transport_observation_id"
        ],
        "remote_inspection_id": inspection["remote_inspection_id"],
        "remote_read_only_inspection": inspection,
        "authenticated_remote_inspection_stdout_exactly_joined": True,
        "authenticated_body_remote_filesystem_mutation_performed": False,
        "systemd_lifecycle_mutation_performed": False,
        "same_effect_reissued": False,
        "retained_same_effect_dispatch_replay_allowed": False,
        "current_remote_absence_is_historical_never_started_proof": False,
        "external_local_and_ssh_assumptions_observed_or_attested": False,
        "end_to_end_remote_mutation_absence_claimed": False,
    }
    return {
        **payload,
        "remote_inspection_join_id": _content_id(
            REMOTE_INSPECTION_JOIN_DOMAIN, payload
        ),
    }


def verify_remote_inspection_join_v42r3r4(
    value: bytes | Mapping[str, Any], *, recovery_plan: Mapping[str, Any],
    recovery_inspection_attempt: Mapping[str, Any],
    bounded_child_transport_observation: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "remote inspection join")
    expected = build_remote_inspection_join_v42r3r4(
        recovery_plan=recovery_plan,
        recovery_inspection_attempt=recovery_inspection_attempt,
        bounded_child_transport_observation=bounded_child_transport_observation,
        remote_read_only_inspection=document.get("remote_read_only_inspection"),
    )
    if document != expected:
        _fail("remote inspection join changed")
    return document


def classify_recovery_v42r3r4(
    *, recovery_plan: Mapping[str, Any],
    recovery_inspection_attempt: Mapping[str, Any],
    bounded_child_transport_observation: Mapping[str, Any],
    remote_inspection_join: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Close the retained occurrence without inferring history from absence."""

    plan = verify_recovery_plan_v42r3r4(recovery_plan)
    attempt = verify_recovery_inspection_attempt_v42r3r4(
        recovery_inspection_attempt, recovery_plan=plan
    )
    observation = verify_bounded_child_transport_observation_v42r3r4(
        bounded_child_transport_observation,
        recovery_plan=plan,
        recovery_inspection_attempt=attempt,
    )
    reason_codes = [
        RECOVERY_REASON_RETAINED_POST_MARKER_WITHOUT_EXACT_RECEIPT
    ]
    current_unit_absent: bool | None = None
    current_formal_journal_absent: bool | None = None
    if remote_inspection_join is None:
        join_id = None
        exact_inspection = False
        reason_codes.append(RECOVERY_REASON_INSPECTION_NOT_EXACT)
    else:
        join = verify_remote_inspection_join_v42r3r4(
            remote_inspection_join,
            recovery_plan=plan,
            recovery_inspection_attempt=attempt,
            bounded_child_transport_observation=observation,
        )
        join_id = join["remote_inspection_join_id"]
        exact_inspection = True
        inspection = join["remote_read_only_inspection"]
        current_unit_absent = (
            inspection["unit_observation"]["LoadState"] == "not-found"
        )
        current_formal_journal_absent = (
            inspection["retained_remote_journal_state"] == "ABSENT"
        )
        old_manager = plan["retained_launch_occurrence"][
            "formal_transport_plan"
        ]["host_epoch_receipt"]["manager_binding"]
        if inspection["manager_binding"] != old_manager:
            reason_codes.append("BOOT_OR_USER_MANAGER_DRIFT")
        else:
            reason_codes.append(
                RECOVERY_REASON_LAUNCH_STATE_NOT_EXACT_OR_SUPERVISION_LOST
            )
    payload = {
        **_base(RECOVERY_CLASSIFICATION_SCHEMA),
        "recovery_plan_id": plan["recovery_plan_id"],
        "recovery_inspection_attempt_id": attempt[
            "recovery_inspection_attempt_id"
        ],
        "bounded_child_transport_observation_id": observation[
            "bounded_child_transport_observation_id"
        ],
        "remote_inspection_join_id": join_id,
        "retained_launch_occurrence_id": plan["retained_launch_occurrence_id"],
        "retained_network_start_marker_present": True,
        "retained_exact_transport_receipt_present": False,
        "authenticated_read_only_recovery_inspection_joined": exact_inspection,
        "classification": RECOVERY_CLASS_AMBIGUOUS_PERMANENTLY_CLOSED,
        "reason_codes": reason_codes,
        "retained_historical_execution_status": "UNKNOWN_NOT_INFERRED",
        "current_unit_absent": current_unit_absent,
        "current_formal_journal_absent": current_formal_journal_absent,
        "current_remote_absence_is_historical_never_started_proof": False,
        "retained_same_effect_dispatch_replay_allowed": False,
        "additional_recovery_dispatch_authorized": False,
        "new_scientific_execution_authorized": False,
        "authenticated_remote_mutation_authorized": False,
        "authenticated_systemd_lifecycle_mutation_authorized": False,
        "external_local_and_ssh_assumptions_observed_or_attested": False,
        "end_to_end_remote_mutation_absence_claimed": False,
    }
    return {
        **payload,
        "recovery_classification_id": _content_id(
            RECOVERY_CLASSIFICATION_DOMAIN, payload
        ),
    }


def verify_recovery_classification_v42r3r4(
    value: bytes | Mapping[str, Any], *, recovery_plan: Mapping[str, Any],
    recovery_inspection_attempt: Mapping[str, Any],
    bounded_child_transport_observation: Mapping[str, Any],
    remote_inspection_join: Mapping[str, Any] | None,
) -> dict[str, Any]:
    document = _canonical_document(value, "recovery classification")
    expected = classify_recovery_v42r3r4(
        recovery_plan=recovery_plan,
        recovery_inspection_attempt=recovery_inspection_attempt,
        bounded_child_transport_observation=bounded_child_transport_observation,
        remote_inspection_join=remote_inspection_join,
    )
    if document != expected:
        _fail("recovery classification changed")
    return document
