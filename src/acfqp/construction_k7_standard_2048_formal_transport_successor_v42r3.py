"""Pure authority for the native V42r3 formal host-epoch probe.

The V42r2 activation successor is evidence consumed by this authority, not a
runtime dependency.  In particular, this module can be loaded on the formal
host from the frozen V42r1 source capsule plus its separately authenticated
bytes without importing any V42r2 module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from pathlib import PurePosixPath
import re
from typing import Any, NoReturn
import uuid

from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1
    as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "42.3.0"

CONTROLLER_SOURCE_MANIFEST_SCHEMA = (
    "acfqp.v42_formal_transport_successor_controller_source_manifest.v42r3"
)
NATIVE_ACTIVATION_BINDING_SCHEMA = (
    "acfqp.v42_formal_transport_successor_native_activation_binding.v42r3"
)
FORMAL_HOST_EPOCH_PROBE_PLAN_SCHEMA = (
    "acfqp.v42_formal_transport_successor_host_epoch_probe_plan.v42r3"
)
FORMAL_HOST_EPOCH_RECEIPT_SCHEMA = (
    "acfqp.v42_formal_transport_successor_host_epoch_receipt.v42r3"
)
FORMAL_HOST_EPOCH_TRANSPORT_OBSERVATION_SCHEMA = (
    "acfqp.v42_formal_transport_successor_host_epoch_transport_observation."
    "v42r3r1"
)
FORMAL_HOST_EPOCH_PROBE_ATTEMPT_SCHEMA = (
    "acfqp.v42_formal_transport_successor_host_epoch_probe_attempt.v42r3r1"
)
FORMAL_HOST_EPOCH_DISPATCH_FAILURE_SCHEMA = (
    "acfqp.v42_formal_transport_successor_host_epoch_dispatch_failure.v42r3r1"
)
EXTERNAL_LOCAL_STAGE0_ASSUMPTION_SCHEMA = (
    "acfqp.v42_formal_transport_external_local_stage0_assumption.v42r3"
)
EXTERNAL_SSH_INGRESS_ASSUMPTION_SCHEMA = (
    "acfqp.v42_formal_transport_external_ssh_ingress_assumption.v42r3"
)

CONTROLLER_SOURCE_MANIFEST_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:controller-source-manifest:v42r3"
)
NATIVE_ACTIVATION_BINDING_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:native-activation-binding:v42r3"
)
FORMAL_HOST_EPOCH_PROBE_PLAN_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:host-epoch-probe-plan:v42r3"
)
FORMAL_HOST_EPOCH_RECEIPT_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:host-epoch-receipt:v42r3"
)
FORMAL_HOST_EPOCH_TRANSPORT_OBSERVATION_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:host-epoch-transport-observation:"
    b"v42r3r1"
)
FORMAL_HOST_EPOCH_PROBE_ATTEMPT_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:host-epoch-probe-attempt:v42r3r1"
)
FORMAL_HOST_EPOCH_DISPATCH_FAILURE_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:host-epoch-dispatch-failure:"
    b"v42r3r1"
)
EXTERNAL_LOCAL_STAGE0_ASSUMPTION_DOMAIN = (
    b"acfqp:v42-formal-transport:external-local-stage0-assumption:v42r3"
)
EXTERNAL_SSH_INGRESS_ASSUMPTION_DOMAIN = (
    b"acfqp:v42-formal-transport:external-ssh-ingress-assumption:v42r3"
)

FORMAL_TRANSPORT_PLAN_SCHEMA = (
    "acfqp.v42_formal_transport_successor_plan.v42r3"
)
FORMAL_PREPARE_ATTEMPT_SCHEMA = (
    "acfqp.v42_formal_transport_successor_prepare_attempt.v42r3"
)
CROSS_VERSION_SCIENTIFIC_STATE_GATE_SCHEMA = (
    "acfqp.v42_formal_transport_successor_scientific_state_gate.v42r3"
)
FORMAL_LAUNCH_TRANSPORT_ATTEMPT_SCHEMA = (
    "acfqp.v42_formal_transport_successor_launch_transport_attempt.v42r3"
)
FORMAL_LAUNCH_ADMISSION_RECEIPT_SCHEMA = (
    "acfqp.v42_formal_transport_successor_launch_admission_receipt.v42r3"
)
FORMAL_SERVICE_WRAPPER_ATTESTATION_SCHEMA = (
    "acfqp.v42_formal_transport_successor_service_wrapper_attestation.v42r3"
)
FORMAL_READ_ONLY_INSPECTION_SCHEMA = (
    "acfqp.v42_formal_transport_successor_read_only_inspection.v42r3"
)
FORMAL_NETWORK_START_SCHEMA = (
    "acfqp.v42_formal_transport_successor_network_start.v42r3"
)
FORMAL_OPERATION_OUTCOME_SCHEMA = (
    "acfqp.v42_formal_transport_successor_operation_outcome.v42r3"
)
FORMAL_CLASSIFICATION_SCHEMA = (
    "acfqp.v42_formal_transport_successor_classification.v42r3"
)

FORMAL_TRANSPORT_PLAN_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:plan:v42r3"
)
FORMAL_PREPARE_ATTEMPT_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:prepare-attempt:v42r3"
)
CROSS_VERSION_SCIENTIFIC_STATE_GATE_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:scientific-state-gate:v42r3"
)
FORMAL_LAUNCH_TRANSPORT_ATTEMPT_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:launch-transport-attempt:v42r3"
)
FORMAL_LAUNCH_ADMISSION_RECEIPT_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:launch-admission-receipt:v42r3"
)
FORMAL_SERVICE_WRAPPER_ATTESTATION_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:service-wrapper-attestation:v42r3"
)
FORMAL_READ_ONLY_INSPECTION_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:read-only-inspection:v42r3"
)
FORMAL_NETWORK_START_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:network-start:v42r3"
)
FORMAL_OPERATION_OUTCOME_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:operation-outcome:v42r3"
)
FORMAL_CLASSIFICATION_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:classification:v42r3"
)

LOCAL_FORMAL_JOURNAL_ROOT = PurePosixPath(
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-local-formal-transport-ordinal2-v42r3r1"
)
REMOTE_FORMAL_JOURNAL_ROOT = PurePosixPath(
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-remote-ordinal2-formal-transport-v42r3r1"
)
LOCAL_KNOWN_HOSTS_NAME = "PINNED_KNOWN_HOSTS"

SYSTEMD_RUN = "/usr/bin/systemd-run"
SYSTEMD_UNIT_PREFIX = "acfqp-v42r3r1-remote-ordinal2-"
SYSTEMD_SLICE = "app.slice"
SYSTEMD_TIMEOUT_STOP_SECONDS = 30
SYSTEMD_RUNTIME_MAX_SECONDS = 606_300
SYSTEMD_CLIENT_ENVIRONMENT = {
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "LC_ALL": "C.UTF-8",
    "XDG_RUNTIME_DIR": "/run/user/1000",
}
FORMAL_SERVICE_ENVIRONMENT = {
    "HOME": "/home/erzhu419",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "LOGNAME": authority.REMOTE_USER,
    "PATH": "/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONCOERCECLOCALE": "0",
    "USER": authority.REMOTE_USER,
}
FORBIDDEN_SYSTEMD_OPTIONS = frozenset(
    {"--wait", "--pipe", "--pty", "--scope", "--collect", "--binds-to"}
)

OPERATION_PREPARE = "PREPARE"
OPERATION_LAUNCH = "LAUNCH"
OPERATIONS = (OPERATION_PREPARE, OPERATION_LAUNCH)

OUTCOME_PRE_NETWORK_FAILURE = "PRE_NETWORK_FAILURE"
OUTCOME_COMPLETE_EXACT_RECEIPT = "COMPLETE_EXACT_RECEIPT"
OUTCOME_POST_MARKER_AMBIGUOUS = "POST_MARKER_WITHOUT_EXACT_RECEIPT"
OUTCOME_CLASSES = (
    OUTCOME_PRE_NETWORK_FAILURE,
    OUTCOME_COMPLETE_EXACT_RECEIPT,
    OUTCOME_POST_MARKER_AMBIGUOUS,
)

CLASS_PRE_NETWORK_RETRYABLE = "PRE_NETWORK_FAILURE_RETRYABLE"
CLASS_PREPARE_COMPLETE = "PREPARE_COMPLETE_EXACT_RECEIPT"
CLASS_LAUNCH_ADMITTED = "LAUNCH_ADMITTED_INSPECTION_REQUIRED"
CLASS_IN_PROGRESS = "IN_PROGRESS_READ_ONLY_WAIT"
CLASS_AMBIGUOUS = "AMBIGUOUS_PERMANENTLY_CLOSED"

ARTIFACT_STATES = (
    "ABSENT",
    "REGULAR_FILE",
    "DIRECTORY",
    "NONREGULAR",
)

SERVICE_BOOTSTRAP_MODE = "--formal-launch-service-bootstrap-v42r3"
SERVICE_WRAPPER_MODE = "--formal-launch-service-wrapper-v42r3"

CONTROLLER_TCB_PATHS = (
    "scripts/__init__.py",
    "scripts/bootstrap_v42_formal_transport_successor_v42r3.py",
    "scripts/launch_v42_activation_successor_or_formal.py",
    "scripts/launch_v42_formal_transport_successor_v42r3.py",
    "scripts/launch_v42_preformal_upload_sender.py",
    "scripts/publish_v42_preformal_upload_journal.py",
    "scripts/run_v42_activation_successor_finalizer.py",
    "scripts/run_v42_materialization_activation.py",
    "scripts/run_v42_preformal_upload_sender.py",
    "scripts/run_v42_standard_2048_formal_transport_driver.py",
    "scripts/run_v42_standard_2048_formal_transport_native_successor_driver.py",
    "scripts/run_v42_standard_2048_formal_transport_successor_driver.py",
    "scripts/run_v42_standard_2048_remote_ordinal2.py",
    "scripts/v42_activation_successor_loader.py",
    "scripts/v42_activation_successor_receiver.py",
    "scripts/v42_standard_2048_formal_transport_loader_v42r3.py",
    "scripts/v42_standard_2048_formal_transport_receiver_v42r3.py",
    "src/acfqp/__init__.py",
    "src/acfqp/artifacts.py",
    "src/acfqp/build_coverage.py",
    "src/acfqp/construction_k7_domain_registry_extension_v42.py",
    "src/acfqp/construction_k7_standard_2048_activation_successor_v42r2.py",
    (
        "src/acfqp/"
        "construction_k7_standard_2048_formal_transport_successor_v42r3.py"
    ),
    "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
    (
        "src/acfqp/"
        "construction_k7_standard_2048_fresh_terminal_preregistration_v42.py"
    ),
    "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
    (
        "src/acfqp/"
        "construction_k7_standard_2048_materialization_activation_v42r1.py"
    ),
    (
        "src/acfqp/"
        "construction_k7_standard_2048_materialization_transport_v42r1.py"
    ),
    (
        "src/acfqp/"
        "construction_k7_standard_2048_process_supervision_v42r1.py"
    ),
    (
        "src/acfqp/"
        "construction_k7_standard_2048_remote_execution_authority_v42r1.py"
    ),
    "src/acfqp/core.py",
    "src/acfqp/enumeration.py",
    "src/acfqp/phase3e_ids.py",
)
if (
    CONTROLLER_TCB_PATHS != tuple(sorted(CONTROLLER_TCB_PATHS))
    or len(CONTROLLER_TCB_PATHS) != 33
    or len(set(CONTROLLER_TCB_PATHS)) != 33
):  # pragma: no cover - import-time frozen contract
    raise RuntimeError("V42r3 controller TCB inventory changed")

PROBE_LOADER_RELATIVE = (
    "scripts/v42_standard_2048_formal_transport_loader_v42r3.py"
)
LOCAL_BOOTSTRAP_RELATIVE = (
    "scripts/bootstrap_v42_formal_transport_successor_v42r3.py"
)
FORMAL_AUTHORITY_RELATIVE = (
    "src/acfqp/"
    "construction_k7_standard_2048_formal_transport_successor_v42r3.py"
)
PROBE_RECEIVER_RELATIVE = (
    "scripts/v42_standard_2048_formal_transport_receiver_v42r3.py"
)

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_CGROUP = re.compile(r"/(?:[A-Za-z0-9_.:@\\-]+/?)*")
_CONTROLLER = re.compile(r"[A-Za-z0-9_]+")
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

_NATIVE_INPUT_FIELDS = frozenset(
    {
        "formal_identity",
        "global_execution_ordinal",
        "activation_successor_source_manifest_id",
        "activation_successor_read_only_plan_id",
        "activation_successor_path_provenance_receipt_id",
        "activation_successor_classification_id",
        "activation_successor_read_only_snapshot_id",
        "activation_successor_final_evidence_index_id",
        "predecessor_materialization_activation_plan_id",
        "predecessor_activation_read_only_snapshot_tail_id",
        "predecessor_activation_classification_id",
        "predecessor_remote_materialization_transport_terminal_id",
        "preactivation_resource_result_id",
        "preactivation_observed_python",
        "preactivation_cgroup_memory_ancestry",
        "preactivation_memory_total_bytes",
        "preactivation_memory_available_bytes",
        "preactivation_all_resource_gates_passed",
        "preactivation_read_only_observation_completed",
        "preactivation_remote_mutation_performed",
        "source_commit",
        "source_tree",
        "source_manifest_id",
        "transport_manifest_id",
        "local_materialization_attempt_id",
        "remote_materialization_attempt_id",
        "materialization_terminal_id",
        "fixed_remote_root",
        "remote_source_root",
        "remote_target_alias",
        "expected_remote_hostname",
        "observed_remote_hostname",
        "observed_remote_user",
        "observed_remote_uid",
        "observed_remote_gid",
        "non_authoritative_compatibility_artifact_id",
        "legacy_activation_final_evidence_index_claimed",
        "legacy_snapshot_or_final_synthesized",
        "activation_effect_replay_authorized",
        "native_nested_path_evidence_complete",
    }
)

_PYTHON_OBSERVATION_FIELDS = frozenset(
    {
        "python_invocation_path",
        "python_invocation_node_type",
        "python_invocation_link_target",
        "python_invocation_mode",
        "python_invocation_uid",
        "python_invocation_gid",
        "python_invocation_nlink",
        "python_realpath",
        "python_realpath_node_type",
        "python_realpath_mode",
        "python_realpath_uid",
        "python_realpath_gid",
        "python_realpath_nlink",
        "python_realpath_sha256",
        "python_realpath_byte_count",
        "python_version",
        "python_isolated_flag",
        "python_no_site_flag",
        "python_dont_write_bytecode",
    }
)
_PYTHON_REALPATH_SHA256 = (
    "1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118"
)
_PYTHON_REALPATH_BYTE_COUNT = 8_020_928

_RUNTIME_FIELDS = frozenset(
    {
        "hostname",
        "user",
        "uid",
        "gid",
        "python_invocation",
        "python_realpath",
        "python_version",
        "python_isolated_flag",
        "python_no_site_flag",
        "python_dont_write_bytecode",
    }
)
_MANAGER_FIELDS = frozenset(
    {
        "kernel_boot_id",
        "linger_enabled",
        "linger_path",
        "user_manager_invocation_id",
        "user_manager_main_pid",
        "user_manager_control_group",
    }
)
_RESOURCE_FIELDS = frozenset(
    {
        "memory_total_bytes",
        "memory_available_bytes",
        "swap_total_bytes",
        "swap_free_bytes",
        "filesystem_available_bytes",
        "cgroup_mount_point",
        "cgroup_mount_filesystem_type",
        "cgroup_mount_root",
        "cgroup_controllers",
        "memory_limit_ancestry",
    }
)
_CGROUP_ROW_FIELDS = frozenset(
    {
        "cgroup_path",
        "memory_max_mode",
        "memory_max_bytes",
        "memory_current_bytes",
    }
)
_TOOL_FACT_FIELDS = frozenset(
    {"path", "sha256", "byte_count", "mode", "uid", "gid", "st_nlink"}
)
_TOOL_PATHS = {
    "env": "/usr/bin/env",
    "python": authority.REMOTE_PYTHON_REALPATH,
    "systemctl": "/usr/bin/systemctl",
    "systemd_run": "/usr/bin/systemd-run",
}


class V42FormalTransportSuccessorError(ValueError):
    """A V42r3 formal successor authority input changed."""


def _fail(message: str) -> NoReturn:
    raise V42FormalTransportSuccessorError(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + b"\0" + canonical_json_bytes(dict(payload))).hexdigest()


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
    except V42FormalTransportSuccessorError:
        raise
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42FormalTransportSuccessorError(
            label + " is not canonical JSON"
        ) from error
    if type(result) is not dict:
        _fail(label + " is not one JSON object")
    return result


def _mapping(value: Any, fields: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail(label + " changed type")
    result = _canonical_document(value, label)
    if set(result) != fields:
        _fail(label + " field set changed")
    return result


def _hex(value: Any, length: int, label: str) -> str:
    pattern = _HEX40 if length == 40 else _HEX64
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail(label + f" is not lowercase hex{length}")
    return value


def _uuid(value: Any, label: str) -> str:
    if type(value) is not str:
        _fail(label + " changed type")
    try:
        normalized = str(uuid.UUID(value))
    except (AttributeError, ValueError) as error:
        raise V42FormalTransportSuccessorError(
            label + " is not a canonical UUID"
        ) from error
    if normalized != value:
        _fail(label + " is not a canonical UUID")
    return value


def _absolute(value: Any, label: str) -> str:
    if type(value) is not str or not value or "\0" in value:
        _fail(label + " changed type, emptiness, or NUL")
    path = PurePosixPath(value)
    if not path.is_absolute() or str(path) != value or ".." in path.parts:
        _fail(label + " is not a canonical absolute POSIX path")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(label + " is not a positive integer")
    return value


def _base(schema: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
    }


def _verify_base(document: Mapping[str, Any], schema: str, label: str) -> None:
    if (
        document.get("schema") != schema
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != authority.FORMAL_IDENTITY
        or document.get("global_execution_ordinal")
        != authority.GLOBAL_EXECUTION_ORDINAL
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


def _verify_source_fact(value: Any, expected_relative: str | None = None) -> dict[str, Any]:
    fact = _mapping(value, _SOURCE_FACT_FIELDS, "controller source fact")
    relative = fact["relative_path"]
    if (
        type(relative) is not str
        or not relative
        or relative.startswith("/")
        or str(PurePosixPath(relative)) != relative
        or any(part in {"", ".", ".."} for part in PurePosixPath(relative).parts)
        or expected_relative is not None
        and relative != expected_relative
        or fact["git_mode"] != "100644"
        or fact["git_object_type"] != "blob"
    ):
        _fail("controller source fact path or Git kind changed")
    _hex(fact["git_blob_oid"], 40, "controller source Git blob")
    _hex(fact["sha256"], 64, "controller source SHA256")
    count = _positive_int(fact["byte_count"], "controller source byte count")
    if count > 8 * 1024**2:
        _fail("controller source byte count exceeded cap")
    return fact


def build_controller_source_manifest_v42r3(
    *, source_commit: str, source_tree: str,
    source_facts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind the exact sorted 33-file local controller TCB."""

    commit = _hex(source_commit, 40, "controller source commit")
    tree = _hex(source_tree, 40, "controller source tree")
    if type(source_facts) not in (list, tuple):
        _fail("controller source facts changed type")
    if len(source_facts) != len(CONTROLLER_TCB_PATHS):
        _fail("controller source fact inventory changed")
    facts = [
        _verify_source_fact(value, relative)
        for value, relative in zip(
            source_facts, CONTROLLER_TCB_PATHS, strict=True
        )
    ]
    payload = {
        **_base(CONTROLLER_SOURCE_MANIFEST_SCHEMA),
        "source_commit": commit,
        "source_tree": tree,
        "source_facts": facts,
    }
    return {
        **payload,
        "controller_source_manifest_id": _content_id(
            CONTROLLER_SOURCE_MANIFEST_DOMAIN, payload
        ),
    }


def verify_controller_source_manifest_v42r3(
    value: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "controller source manifest")
    expected = build_controller_source_manifest_v42r3(
        source_commit=document.get("source_commit"),
        source_tree=document.get("source_tree"),
        source_facts=document.get("source_facts"),
    )
    if document != expected:
        _fail("controller source manifest changed")
    return document


def _verify_python_observation(value: Any) -> dict[str, Any]:
    observed = _mapping(
        value, _PYTHON_OBSERVATION_FIELDS, "preactivation Python observation"
    )
    expected_fixed = {
        "python_invocation_path": authority.REMOTE_PYTHON,
        "python_invocation_node_type": "SYMLINK",
        "python_invocation_link_target": "python3.12",
        "python_invocation_mode": 0o777,
        "python_invocation_uid": 0,
        "python_invocation_gid": 0,
        "python_invocation_nlink": 1,
        "python_realpath": authority.REMOTE_PYTHON_REALPATH,
        "python_realpath_node_type": "REGULAR_FILE",
        "python_realpath_mode": 0o755,
        "python_realpath_uid": 0,
        "python_realpath_gid": 0,
        "python_realpath_nlink": 1,
        "python_realpath_sha256": _PYTHON_REALPATH_SHA256,
        "python_realpath_byte_count": _PYTHON_REALPATH_BYTE_COUNT,
        "python_version": list(authority.REMOTE_PYTHON_VERSION),
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
    }
    if observed != expected_fixed:
        _fail("preactivation Python 3.12.3 identity changed")
    return observed


def _verify_cgroup_ancestry(
    value: Any, *, expected_first: str | None, label: str,
) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        _fail(label + " changed type or is empty")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        row = _mapping(item, _CGROUP_ROW_FIELDS, label + " row")
        path = row["cgroup_path"]
        if (
            type(path) is not str
            or _CGROUP.fullmatch(path) is None
            or str(PurePosixPath(path)) != path
            or expected_first is not None
            and index == 0
            and path != expected_first
        ):
            _fail(label + " path changed")
        if rows and (
            rows[-1]["cgroup_path"] == "/"
            or PurePosixPath(path)
            != PurePosixPath(rows[-1]["cgroup_path"]).parent
        ):
            _fail(label + " is not an exact parent chain")
        mode = row["memory_max_mode"]
        maximum = row["memory_max_bytes"]
        current = row["memory_current_bytes"]
        if mode == "MAX":
            valid = maximum is None and type(current) is int and current >= 0
        elif mode == "FINITE":
            valid = (
                type(maximum) is int
                and maximum >= authority.MINIMUM_MEMORY_TOTAL_BYTES
                and type(current) is int
                and 0 <= current <= maximum
                and maximum - current
                >= authority.MINIMUM_MEMORY_AVAILABLE_BYTES
            )
        elif mode == "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES":
            valid = (
                index == len(value) - 1
                and path == "/"
                and maximum is None
                and current is None
            )
        else:
            valid = False
        if not valid:
            _fail(label + " memory gate changed")
        rows.append(row)
    if rows[-1]["cgroup_path"] != "/":
        _fail(label + " omitted the root")
    return rows


def _verify_native_inputs(value: Any) -> dict[str, Any]:
    native = _mapping(value, _NATIVE_INPUT_FIELDS, "native activation inputs")
    if (
        native["formal_identity"] != authority.FORMAL_IDENTITY
        or native["global_execution_ordinal"]
        != authority.GLOBAL_EXECUTION_ORDINAL
    ):
        _fail("native activation formal identity changed")
    for field in (
        "activation_successor_source_manifest_id",
        "activation_successor_read_only_plan_id",
        "activation_successor_path_provenance_receipt_id",
        "activation_successor_classification_id",
        "activation_successor_read_only_snapshot_id",
        "activation_successor_final_evidence_index_id",
        "predecessor_materialization_activation_plan_id",
        "predecessor_activation_read_only_snapshot_tail_id",
        "predecessor_activation_classification_id",
        "predecessor_remote_materialization_transport_terminal_id",
        "preactivation_resource_result_id",
        "source_manifest_id",
        "transport_manifest_id",
        "local_materialization_attempt_id",
        "remote_materialization_attempt_id",
        "materialization_terminal_id",
        "non_authoritative_compatibility_artifact_id",
    ):
        _hex(native[field], 64, field)
    _hex(native["source_commit"], 40, "native source commit")
    _hex(native["source_tree"], 40, "native source tree")
    _verify_python_observation(native["preactivation_observed_python"])
    native["preactivation_cgroup_memory_ancestry"] = _verify_cgroup_ancestry(
        native["preactivation_cgroup_memory_ancestry"],
        expected_first=None,
        label="preactivation cgroup memory ancestry",
    )
    total = native["preactivation_memory_total_bytes"]
    available = native["preactivation_memory_available_bytes"]
    if (
        type(total) is not int
        or total < authority.MINIMUM_MEMORY_TOTAL_BYTES
        or type(available) is not int
        or available < authority.MINIMUM_MEMORY_AVAILABLE_BYTES
        or available > total
    ):
        _fail("preactivation memory resource gate changed")
    fixed_root = _absolute(native["fixed_remote_root"], "fixed remote root")
    source_root = _absolute(native["remote_source_root"], "remote source root")
    if (
        fixed_root != str(authority.REMOTE_ROOT)
        or source_root != str(authority.REMOTE_SOURCE_ROOT)
        or PurePosixPath(source_root) != PurePosixPath(fixed_root) / "source"
        or native["remote_target_alias"] != authority.REMOTE_HOST_ALIAS
        or native["expected_remote_hostname"] != authority.REMOTE_HOSTNAME
        or native["observed_remote_hostname"] != authority.REMOTE_HOSTNAME
        or native["observed_remote_user"] != authority.REMOTE_USER
        or native["observed_remote_uid"] != authority.REMOTE_UID
        or native["observed_remote_gid"] != authority.REMOTE_GID
    ):
        _fail("native activation fixed path or remote identity changed")
    if (
        native["preactivation_all_resource_gates_passed"] is not True
        or native["preactivation_read_only_observation_completed"] is not True
        or native["preactivation_remote_mutation_performed"] is not False
        or native["legacy_activation_final_evidence_index_claimed"] is not False
        or native["legacy_snapshot_or_final_synthesized"] is not False
        or native["activation_effect_replay_authorized"] is not False
        or native["native_nested_path_evidence_complete"] is not True
    ):
        _fail("native activation gate, read-only, or replay claim changed")
    return native


def build_native_activation_binding_v42r3(
    *, native_activation_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize the verified V42r2 evidence projection without importing it."""

    native = _verify_native_inputs(native_activation_inputs)
    payload = {
        **_base(NATIVE_ACTIVATION_BINDING_SCHEMA),
        **{
            field: native[field]
            for field in sorted(_NATIVE_INPUT_FIELDS - {"remote_source_root"})
            if field not in {
                "formal_identity",
                "global_execution_ordinal",
                "preactivation_read_only_observation_completed",
                "preactivation_remote_mutation_performed",
            }
        },
        "fixed_source_root": native["remote_source_root"],
        (
            "legacy_document_claim_preactivation_read_only_observation_"
            "completed"
        ): native["preactivation_read_only_observation_completed"],
        (
            "legacy_document_claim_preactivation_remote_mutation_performed"
        ): native["preactivation_remote_mutation_performed"],
        "legacy_end_to_end_mutation_absence_adopted": False,
        "legacy_ssh_ingress_noninterference_is_external_assumption": True,
        (
            "native_identity_resource_and_path_projection_is_conditional_on_"
            "external_ingress_tcb"
        ): True,
    }
    return {
        **payload,
        "native_activation_binding_id": _content_id(
            NATIVE_ACTIVATION_BINDING_DOMAIN, payload
        ),
    }


def verify_native_activation_binding_v42r3(
    value: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "native activation binding")
    native = {
        field: (
            document.get("fixed_source_root")
            if field == "remote_source_root"
            else document.get(
                "legacy_document_claim_preactivation_read_only_observation_"
                "completed"
            )
            if field == "preactivation_read_only_observation_completed"
            else document.get(
                "legacy_document_claim_preactivation_remote_mutation_performed"
            )
            if field == "preactivation_remote_mutation_performed"
            else document.get(field)
        )
        for field in _NATIVE_INPUT_FIELDS
    }
    expected = build_native_activation_binding_v42r3(
        native_activation_inputs=native
    )
    if document != expected:
        _fail("native activation binding changed")
    return document


def build_external_local_stage0_assumption_v42r3(
    *, controller_source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Name the unproved external invoker premise for local stage-0 entry."""

    controller = verify_controller_source_manifest_v42r3(
        controller_source_manifest
    )
    facts = {row["relative_path"]: row for row in controller["source_facts"]}
    payload = {
        **_base(EXTERNAL_LOCAL_STAGE0_ASSUMPTION_SCHEMA),
        "controller_source_manifest_id": controller[
            "controller_source_manifest_id"
        ],
        "bootstrap_artifact": facts[LOCAL_BOOTSTRAP_RELATIVE],
        (
            "assumed_external_invoker_stable_reads_and_sha256_checks_"
            "bootstrap"
        ): True,
        (
            "assumed_external_invoker_executes_same_bytes_once_from_sealed_"
            "memfd"
        ): True,
        (
            "assumed_external_invoker_preserves_arguments_and_repository_root"
        ): True,
        "assumed_external_invoker_is_only_authorized_launcher_entry": True,
        (
            "assumed_external_invoker_supplies_benign_stdio_signal_rlimit_"
            "cwd_and_umask_state"
        ): True,
        (
            "stage1_requires_sealed_bootstrap_and_launcher_raw_match_manifest"
        ): True,
        "actual_stage0_execution_observed_or_attested": False,
        "root_owned_local_entry_broker_attestation_present": False,
        "assumption_observed_or_attested_by_campaign": False,
        "admission_is_conditional_on_external_local_invoker_fidelity": True,
    }
    return {
        **payload,
        "external_local_stage0_assumption_id": _content_id(
            EXTERNAL_LOCAL_STAGE0_ASSUMPTION_DOMAIN, payload
        ),
    }


def verify_external_local_stage0_assumption_v42r3(
    value: bytes | Mapping[str, Any], *,
    controller_source_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    document = _canonical_document(value, "external local stage0 assumption")
    fields = frozenset(
        {
            "schema", "schema_version", "formal_identity",
            "global_execution_ordinal", "controller_source_manifest_id",
            "bootstrap_artifact",
            (
                "assumed_external_invoker_stable_reads_and_sha256_checks_"
                "bootstrap"
            ),
            (
                "assumed_external_invoker_executes_same_bytes_once_from_"
                "sealed_memfd"
            ),
            (
                "assumed_external_invoker_preserves_arguments_and_"
                "repository_root"
            ),
            "assumed_external_invoker_is_only_authorized_launcher_entry",
            (
                "assumed_external_invoker_supplies_benign_stdio_signal_"
                "rlimit_cwd_and_umask_state"
            ),
            (
                "stage1_requires_sealed_bootstrap_and_launcher_raw_match_"
                "manifest"
            ),
            "actual_stage0_execution_observed_or_attested",
            "root_owned_local_entry_broker_attestation_present",
            "assumption_observed_or_attested_by_campaign",
            "admission_is_conditional_on_external_local_invoker_fidelity",
            "external_local_stage0_assumption_id",
        }
    )
    if set(document) != fields:
        _fail("external local stage0 assumption field set changed")
    _verify_base(
        document, EXTERNAL_LOCAL_STAGE0_ASSUMPTION_SCHEMA,
        "external local stage0 assumption",
    )
    _hex(
        document["controller_source_manifest_id"], 64,
        "external local stage0 controller manifest ID",
    )
    _verify_source_fact(document["bootstrap_artifact"], LOCAL_BOOTSTRAP_RELATIVE)
    true_fields = fields - {
        "schema", "schema_version", "formal_identity",
        "global_execution_ordinal", "controller_source_manifest_id",
        "bootstrap_artifact", "actual_stage0_execution_observed_or_attested",
        "root_owned_local_entry_broker_attestation_present",
        "assumption_observed_or_attested_by_campaign",
        "external_local_stage0_assumption_id",
    }
    if (
        any(document[field] is not True for field in true_fields)
        or document["actual_stage0_execution_observed_or_attested"] is not False
        or document["root_owned_local_entry_broker_attestation_present"]
        is not False
        or document["assumption_observed_or_attested_by_campaign"] is not False
    ):
        _fail("external local stage0 conditional premise changed")
    _verify_claimed_id(
        document,
        field="external_local_stage0_assumption_id",
        domain=EXTERNAL_LOCAL_STAGE0_ASSUMPTION_DOMAIN,
        label="external local stage0 assumption",
    )
    if controller_source_manifest is not None and document != (
        build_external_local_stage0_assumption_v42r3(
            controller_source_manifest=controller_source_manifest
        )
    ):
        _fail("external local stage0 assumption changed")
    return document


def build_external_ssh_ingress_assumption_v42r3() -> dict[str, Any]:
    """Name unproved ingress and writable remote-path noninterference."""

    payload = {
        **_base(EXTERNAL_SSH_INGRESS_ASSUMPTION_SCHEMA),
        "sshd_pam_login_shell_and_startup_hooks_are_external_tcb": True,
        (
            "assumed_external_ingress_executes_exact_authenticated_loader_"
            "command_once"
        ): True,
        (
            "assumed_external_ingress_preserves_stdin_frame_and_stdout_bytes"
        ): True,
        "assumed_external_ingress_does_not_forge_authenticated_receipts": True,
        (
            "assumed_external_ingress_does_not_modify_campaign_roots_target_"
            "unit_or_manager_state"
        ): True,
        (
            "assumed_no_concurrent_parent_writable_actor_replaces_campaign_"
            "paths_during_authenticated_remote_operation"
        ): True,
        "root_controlled_ingress_attestation_present": False,
        "root_owned_nonwritable_campaign_parent_attestation_present": False,
        "assumption_observed_or_attested_by_campaign": False,
        "admission_is_conditional_on_external_ssh_ingress_fidelity": True,
        "admission_is_conditional_on_remote_path_noninterference": True,
    }
    return {
        **payload,
        "external_ssh_ingress_assumption_id": _content_id(
            EXTERNAL_SSH_INGRESS_ASSUMPTION_DOMAIN, payload
        ),
    }


def verify_external_ssh_ingress_assumption_v42r3(
    value: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "external SSH ingress assumption")
    expected = build_external_ssh_ingress_assumption_v42r3()
    if document != expected:
        _fail("external SSH ingress assumption changed")
    return document


def build_formal_host_epoch_probe_plan_v42r3(
    *, controller_source_manifest: Mapping[str, Any],
    native_activation_binding: Mapping[str, Any],
    legacy_execution_source_manifest_id: str,
) -> dict[str, Any]:
    controller = verify_controller_source_manifest_v42r3(
        controller_source_manifest
    )
    binding = verify_native_activation_binding_v42r3(
        native_activation_binding
    )
    facts = {row["relative_path"]: row for row in controller["source_facts"]}
    local_stage0 = build_external_local_stage0_assumption_v42r3(
        controller_source_manifest=controller
    )
    ssh_ingress = build_external_ssh_ingress_assumption_v42r3()
    payload = {
        **_base(FORMAL_HOST_EPOCH_PROBE_PLAN_SCHEMA),
        "controller_source_manifest_id": controller[
            "controller_source_manifest_id"
        ],
        "probe_loader_artifact": facts[PROBE_LOADER_RELATIVE],
        "formal_authority_artifact": facts[FORMAL_AUTHORITY_RELATIVE],
        "probe_receiver_artifact": facts[PROBE_RECEIVER_RELATIVE],
        "legacy_execution_source_manifest_id": _hex(
            legacy_execution_source_manifest_id,
            64,
            "legacy execution source manifest ID",
        ),
        "native_activation_binding": binding,
        "external_local_stage0_assumption": local_stage0,
        "external_local_stage0_assumption_id": local_stage0[
            "external_local_stage0_assumption_id"
        ],
        "external_ssh_ingress_assumption": ssh_ingress,
        "external_ssh_ingress_assumption_id": ssh_ingress[
            "external_ssh_ingress_assumption_id"
        ],
        "authenticated_loader_and_receiver_probe_is_read_only": True,
        "authenticated_loader_and_receiver_remote_mutation_authorized": False,
        "end_to_end_remote_mutation_absence_claimed": False,
        "activation_effect_replay_authorized": False,
    }
    return {
        **payload,
        "formal_host_epoch_probe_plan_id": _content_id(
            FORMAL_HOST_EPOCH_PROBE_PLAN_DOMAIN, payload
        ),
    }


def verify_formal_host_epoch_probe_plan_v42r3(
    value: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "formal host epoch probe plan")
    fields = frozenset(
        {
            "schema",
            "schema_version",
            "formal_identity",
            "global_execution_ordinal",
            "controller_source_manifest_id",
            "probe_loader_artifact",
            "formal_authority_artifact",
            "probe_receiver_artifact",
            "legacy_execution_source_manifest_id",
            "native_activation_binding",
            "external_local_stage0_assumption",
            "external_local_stage0_assumption_id",
            "external_ssh_ingress_assumption",
            "external_ssh_ingress_assumption_id",
            "authenticated_loader_and_receiver_probe_is_read_only",
            "authenticated_loader_and_receiver_remote_mutation_authorized",
            "end_to_end_remote_mutation_absence_claimed",
            "activation_effect_replay_authorized",
            "formal_host_epoch_probe_plan_id",
        }
    )
    if set(document) != fields:
        _fail("formal host epoch probe plan field set changed")
    _verify_base(
        document, FORMAL_HOST_EPOCH_PROBE_PLAN_SCHEMA,
        "formal host epoch probe plan",
    )
    _hex(
        document["controller_source_manifest_id"], 64,
        "controller source manifest ID",
    )
    _verify_source_fact(document["probe_loader_artifact"], PROBE_LOADER_RELATIVE)
    _verify_source_fact(
        document["formal_authority_artifact"], FORMAL_AUTHORITY_RELATIVE
    )
    _verify_source_fact(
        document["probe_receiver_artifact"], PROBE_RECEIVER_RELATIVE
    )
    _hex(
        document["legacy_execution_source_manifest_id"], 64,
        "legacy execution source manifest ID",
    )
    verify_native_activation_binding_v42r3(
        document["native_activation_binding"]
    )
    local_stage0 = verify_external_local_stage0_assumption_v42r3(
        document["external_local_stage0_assumption"]
    )
    ssh_ingress = verify_external_ssh_ingress_assumption_v42r3(
        document["external_ssh_ingress_assumption"]
    )
    if (
        local_stage0["controller_source_manifest_id"]
        != document["controller_source_manifest_id"]
        or document["external_local_stage0_assumption_id"]
        != local_stage0["external_local_stage0_assumption_id"]
        or document["external_ssh_ingress_assumption_id"]
        != ssh_ingress["external_ssh_ingress_assumption_id"]
        or document["authenticated_loader_and_receiver_probe_is_read_only"]
        is not True
        or document[
            "authenticated_loader_and_receiver_remote_mutation_authorized"
        ] is not False
        or document["end_to_end_remote_mutation_absence_claimed"] is not False
        or document["activation_effect_replay_authorized"] is not False
    ):
        _fail("formal host epoch probe read-only or replay gate changed")
    _verify_claimed_id(
        document,
        field="formal_host_epoch_probe_plan_id",
        domain=FORMAL_HOST_EPOCH_PROBE_PLAN_DOMAIN,
        label="formal host epoch probe plan",
    )
    return document


def _verify_runtime(value: Any) -> dict[str, Any]:
    runtime = _mapping(value, _RUNTIME_FIELDS, "formal host runtime")
    if runtime != {
        "hostname": authority.REMOTE_HOSTNAME,
        "user": authority.REMOTE_USER,
        "uid": authority.REMOTE_UID,
        "gid": authority.REMOTE_GID,
        "python_invocation": authority.REMOTE_PYTHON,
        "python_realpath": authority.REMOTE_PYTHON_REALPATH,
        "python_version": list(authority.REMOTE_PYTHON_VERSION),
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
    }:
        _fail("formal host Python 3.12.3 runtime identity changed")
    return runtime


def _verify_manager(value: Any) -> dict[str, Any]:
    manager = _mapping(value, _MANAGER_FIELDS, "formal host manager binding")
    _uuid(manager["kernel_boot_id"], "kernel boot ID")
    _uuid(manager["user_manager_invocation_id"], "user-manager invocation ID")
    if (
        manager["linger_enabled"] is not True
        or manager["linger_path"]
        != f"/var/lib/systemd/linger/{authority.REMOTE_USER}"
        or type(manager["user_manager_main_pid"]) is not int
        or manager["user_manager_main_pid"] <= 1
        or type(manager["user_manager_control_group"]) is not str
        or _CGROUP.fullmatch(manager["user_manager_control_group"]) is None
        or not manager["user_manager_control_group"].startswith("/user.slice/")
    ):
        _fail("formal host manager epoch changed")
    return manager


def _verify_resources(
    value: Any, *, manager_control_group: str,
) -> dict[str, Any]:
    resources = _mapping(value, _RESOURCE_FIELDS, "formal resource observation")
    integer_fields = (
        "memory_total_bytes",
        "memory_available_bytes",
        "swap_total_bytes",
        "swap_free_bytes",
        "filesystem_available_bytes",
    )
    if any(type(resources[field]) is not int or resources[field] < 0 for field in integer_fields):
        _fail("formal resource observation integer changed")
    if (
        resources["memory_total_bytes"] < authority.MINIMUM_MEMORY_TOTAL_BYTES
        or resources["memory_available_bytes"]
        < authority.MINIMUM_MEMORY_AVAILABLE_BYTES
        or resources["memory_available_bytes"] > resources["memory_total_bytes"]
        or resources["swap_free_bytes"] > resources["swap_total_bytes"]
        or resources["swap_total_bytes"] == 0
        and resources["swap_free_bytes"] != 0
        or resources["swap_total_bytes"] != 0
        and resources["swap_free_bytes"] < authority.MINIMUM_SWAP_FREE_BYTES
        or resources["filesystem_available_bytes"]
        < authority.MINIMUM_FILESYSTEM_AVAILABLE_BYTES
        or resources["cgroup_mount_point"] != "/sys/fs/cgroup"
        or resources["cgroup_mount_filesystem_type"] != "cgroup2"
        or resources["cgroup_mount_root"] != "/"
    ):
        _fail("formal resource gate or cgroup2 mount changed")
    controllers = resources["cgroup_controllers"]
    if (
        type(controllers) is not list
        or not controllers
        or any(
            type(item) is not str or _CONTROLLER.fullmatch(item) is None
            for item in controllers
        )
        or controllers != sorted(set(controllers))
        or "memory" not in controllers
    ):
        _fail("formal cgroup controller inventory changed")
    resources["memory_limit_ancestry"] = _verify_cgroup_ancestry(
        resources["memory_limit_ancestry"],
        expected_first=manager_control_group,
        label="formal manager memory-limit ancestry",
    )
    return resources


def _verify_tool_fact(value: Any, expected_path: str, label: str) -> dict[str, Any]:
    fact = _mapping(value, _TOOL_FACT_FIELDS, label + " tool fact")
    if (
        _absolute(fact["path"], label + " path") != expected_path
        or type(fact["byte_count"]) is not int
        or not 0 < fact["byte_count"] <= 64 * 1024**2
        or fact["mode"] != 0o755
        or type(fact["mode"]) is not int
        or fact["uid"] != 0
        or type(fact["uid"]) is not int
        or fact["gid"] != 0
        or type(fact["gid"]) is not int
        or fact["st_nlink"] != 1
        or type(fact["st_nlink"]) is not int
    ):
        _fail(label + " tool storage identity changed")
    _hex(fact["sha256"], 64, label + " tool SHA256")
    return fact


def _verify_tools(value: Any) -> dict[str, dict[str, Any]]:
    tools = _mapping(value, frozenset(_TOOL_PATHS), "remote tool facts")
    return {
        name: _verify_tool_fact(tools[name], path, name)
        for name, path in _TOOL_PATHS.items()
    }


def build_formal_host_epoch_receipt_v42r3(
    *, probe_plan: Mapping[str, Any], observed_runtime: Mapping[str, Any],
    manager_binding: Mapping[str, Any], resource_observation: Mapping[str, Any],
    remote_tool_facts: Mapping[str, Any],
    formal_successor_journal_state: str,
) -> dict[str, Any]:
    plan = verify_formal_host_epoch_probe_plan_v42r3(probe_plan)
    runtime = _verify_runtime(observed_runtime)
    manager = _verify_manager(manager_binding)
    resources = _verify_resources(
        resource_observation,
        manager_control_group=manager["user_manager_control_group"],
    )
    tools = _verify_tools(remote_tool_facts)
    if formal_successor_journal_state != "ABSENT":
        _fail("formal successor journal was not absent at host probe")
    payload = {
        **_base(FORMAL_HOST_EPOCH_RECEIPT_SCHEMA),
        "formal_host_epoch_probe_plan_id": plan[
            "formal_host_epoch_probe_plan_id"
        ],
        "observed_runtime": runtime,
        "manager_binding": manager,
        "resource_observation": resources,
        "remote_tool_facts": tools,
        "formal_successor_journal_state_at_probe": "ABSENT",
        "all_formal_resource_gates_passed": True,
        "authenticated_loader_and_receiver_observation_was_read_only": True,
        "authenticated_loader_and_receiver_remote_mutation_performed": False,
        (
            "authenticated_loader_and_receiver_systemd_lifecycle_mutation_"
            "performed"
        ): False,
        "end_to_end_remote_mutation_absence_claimed": False,
        "end_to_end_systemd_mutation_absence_claimed": False,
        "activation_effect_replay_authorized": False,
    }
    return {
        **payload,
        "formal_host_epoch_receipt_id": _content_id(
            FORMAL_HOST_EPOCH_RECEIPT_DOMAIN, payload
        ),
    }


def verify_formal_host_epoch_receipt_v42r3(
    value: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "formal host epoch receipt")
    fields = frozenset(
        {
            "schema",
            "schema_version",
            "formal_identity",
            "global_execution_ordinal",
            "formal_host_epoch_probe_plan_id",
            "observed_runtime",
            "manager_binding",
            "resource_observation",
            "remote_tool_facts",
            "formal_successor_journal_state_at_probe",
            "all_formal_resource_gates_passed",
            "authenticated_loader_and_receiver_observation_was_read_only",
            "authenticated_loader_and_receiver_remote_mutation_performed",
            (
                "authenticated_loader_and_receiver_systemd_lifecycle_"
                "mutation_performed"
            ),
            "end_to_end_remote_mutation_absence_claimed",
            "end_to_end_systemd_mutation_absence_claimed",
            "activation_effect_replay_authorized",
            "formal_host_epoch_receipt_id",
        }
    )
    if set(document) != fields:
        _fail("formal host epoch receipt field set changed")
    _verify_base(
        document, FORMAL_HOST_EPOCH_RECEIPT_SCHEMA,
        "formal host epoch receipt",
    )
    _hex(
        document["formal_host_epoch_probe_plan_id"], 64,
        "formal host epoch probe plan ID",
    )
    _verify_runtime(document["observed_runtime"])
    manager = _verify_manager(document["manager_binding"])
    _verify_resources(
        document["resource_observation"],
        manager_control_group=manager["user_manager_control_group"],
    )
    _verify_tools(document["remote_tool_facts"])
    if (
        document["formal_successor_journal_state_at_probe"] != "ABSENT"
        or document["all_formal_resource_gates_passed"] is not True
        or document[
            "authenticated_loader_and_receiver_observation_was_read_only"
        ] is not True
        or document[
            "authenticated_loader_and_receiver_remote_mutation_performed"
        ] is not False
        or document[
            "authenticated_loader_and_receiver_systemd_lifecycle_mutation_"
            "performed"
        ] is not False
        or document["end_to_end_remote_mutation_absence_claimed"] is not False
        or document["end_to_end_systemd_mutation_absence_claimed"] is not False
        or document["activation_effect_replay_authorized"] is not False
    ):
        _fail("formal host receipt resource, read-only, or replay gate changed")
    _verify_claimed_id(
        document,
        field="formal_host_epoch_receipt_id",
        domain=FORMAL_HOST_EPOCH_RECEIPT_DOMAIN,
        label="formal host epoch receipt",
    )
    return document


def build_formal_host_epoch_probe_attempt_v42r3r1(
    *, probe_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Publish a conservative one-shot cut before any probe dispatch."""

    plan = verify_formal_host_epoch_probe_plan_v42r3(probe_plan)
    payload = {
        **_base(FORMAL_HOST_EPOCH_PROBE_ATTEMPT_SCHEMA),
        "formal_host_epoch_probe_plan_id": plan[
            "formal_host_epoch_probe_plan_id"
        ],
        "operation": "HOST_EPOCH_PROBE",
        "network_dispatch_started_at_publication": False,
        "formal_host_epoch_receipt_present_at_publication": False,
        "controller_same_probe_dispatch_replay_allowed": False,
        "authenticated_loader_and_receiver_remote_mutation_authorized": False,
        "controller_prepare_authorized_by_this_attempt": False,
    }
    return {
        **payload,
        "formal_host_epoch_probe_attempt_id": _content_id(
            FORMAL_HOST_EPOCH_PROBE_ATTEMPT_DOMAIN, payload
        ),
    }


def verify_formal_host_epoch_probe_attempt_v42r3r1(
    value: bytes | Mapping[str, Any], *, probe_plan: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "formal host epoch probe attempt")
    expected = build_formal_host_epoch_probe_attempt_v42r3r1(
        probe_plan=probe_plan
    )
    if document != expected:
        _fail("formal host epoch probe attempt changed")
    return document


_HOST_PROBE_FAILURE_FACT_FIELDS = frozenset(
    {
        "failure_type",
        "message_byte_count",
        "message_sha256",
        "message_prefix_byte_count",
        "message_prefix_hex",
    }
)


def _verify_host_probe_failure_fact(value: Any) -> dict[str, Any]:
    fact = _mapping(
        value, _HOST_PROBE_FAILURE_FACT_FIELDS, "formal host probe failure fact"
    )
    if (
        type(fact["failure_type"]) is not str
        or not 0 < len(fact["failure_type"]) <= 256
        or re.fullmatch(r"[\x20-\x7e]+", fact["failure_type"]) is None
        or type(fact["message_byte_count"]) is not int
        or not 0 <= fact["message_byte_count"] < 2**63
        or type(fact["message_prefix_byte_count"]) is not int
        or fact["message_prefix_byte_count"] < 0
        or type(fact["message_prefix_hex"]) is not str
        or len(fact["message_prefix_hex"])
        > 2 * _HOST_PROBE_CAPTURE_PREFIX_MAX_BYTES
        or len(fact["message_prefix_hex"]) % 2 != 0
        or re.fullmatch(r"[0-9a-f]*", fact["message_prefix_hex"]) is None
    ):
        _fail("formal host probe failure fact changed")
    _hex(fact["message_sha256"], 64, "formal host probe failure message")
    prefix = bytes.fromhex(fact["message_prefix_hex"])
    if (
        len(prefix) != fact["message_prefix_byte_count"]
        or len(prefix) != min(
            fact["message_byte_count"], _HOST_PROBE_CAPTURE_PREFIX_MAX_BYTES
        )
        or fact["message_byte_count"] <= len(prefix)
        and hashlib.sha256(prefix).hexdigest() != fact["message_sha256"]
    ):
        _fail("formal host probe failure message evidence changed")
    return fact


def build_formal_host_epoch_dispatch_failure_v42r3r1(
    *, probe_plan: Mapping[str, Any], probe_attempt: Mapping[str, Any],
    failure_fact: Mapping[str, Any],
) -> dict[str, Any]:
    plan = verify_formal_host_epoch_probe_plan_v42r3(probe_plan)
    attempt = verify_formal_host_epoch_probe_attempt_v42r3r1(
        probe_attempt, probe_plan=plan
    )
    failure = _verify_host_probe_failure_fact(failure_fact)
    payload = {
        **_base(FORMAL_HOST_EPOCH_DISPATCH_FAILURE_SCHEMA),
        "formal_host_epoch_probe_plan_id": plan[
            "formal_host_epoch_probe_plan_id"
        ],
        "formal_host_epoch_probe_attempt_id": attempt[
            "formal_host_epoch_probe_attempt_id"
        ],
        "failure_fact": failure,
        "network_dispatch_may_have_started": True,
        "child_observation_returned_to_probe_controller": False,
        "controller_same_probe_dispatch_replay_allowed": False,
        "controller_prepare_authorized_by_this_failure": False,
        "end_to_end_remote_mutation_absence_claimed": False,
        "external_local_and_ssh_assumptions_observed_or_attested": False,
        "remote_path_noninterference_observed_or_attested": False,
    }
    return {
        **payload,
        "formal_host_epoch_dispatch_failure_id": _content_id(
            FORMAL_HOST_EPOCH_DISPATCH_FAILURE_DOMAIN, payload
        ),
    }


def verify_formal_host_epoch_dispatch_failure_v42r3r1(
    value: bytes | Mapping[str, Any], *, probe_plan: Mapping[str, Any],
    probe_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "formal host epoch dispatch failure")
    expected = build_formal_host_epoch_dispatch_failure_v42r3r1(
        probe_plan=probe_plan,
        probe_attempt=probe_attempt,
        failure_fact=document.get("failure_fact"),
    )
    if document != expected:
        _fail("formal host epoch dispatch failure changed")
    return document


_HOST_PROBE_CAPTURE_PREFIX_MAX_BYTES = 4096
_HOST_PROBE_STDOUT_CAP_BYTES = 64 * 1024**2
_HOST_PROBE_STDERR_CAP_BYTES = 1024**2
_HOST_PROBE_CHILD_OBSERVATION_FIELDS = frozenset(
    {
        "exec_succeeded",
        "returncode",
        "timed_out",
        "stdin_expected_byte_count",
        "stdin_sent_byte_count",
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


def _probe_capture_prefix(
    fact: Mapping[str, Any], *, stream: str, retained_count: int,
) -> bytes:
    value = fact[f"{stream}_prefix_hex"]
    byte_count = fact[f"{stream}_prefix_byte_count"]
    if (
        type(value) is not str
        or len(value) > 2 * _HOST_PROBE_CAPTURE_PREFIX_MAX_BYTES
        or len(value) % 2 != 0
        or re.fullmatch(r"[0-9a-f]*", value) is None
        or type(byte_count) is not int
        or byte_count < 0
    ):
        _fail("formal host probe " + stream + " prefix changed")
    raw = bytes.fromhex(value)
    if (
        len(raw) != byte_count
        or byte_count != min(retained_count, _HOST_PROBE_CAPTURE_PREFIX_MAX_BYTES)
    ):
        _fail("formal host probe " + stream + " prefix length changed")
    return raw


def _verify_host_probe_child_observation(value: Any) -> tuple[dict[str, Any], bool]:
    fact = _mapping(
        value,
        _HOST_PROBE_CHILD_OBSERVATION_FIELDS,
        "formal host probe child observation",
    )
    for field in (
        "exec_succeeded",
        "timed_out",
        "stdin_complete",
        "stdout_overflow",
        "stdout_eof",
        "stderr_overflow",
        "stderr_eof",
    ):
        if type(fact[field]) is not bool:
            _fail("formal host probe child observation flag changed")
    returncode = fact["returncode"]
    if returncode is not None and (
        type(returncode) is not int or not -(2**31) <= returncode < 2**31
    ):
        _fail("formal host probe child return code changed")
    count_fields = (
        "stdin_expected_byte_count",
        "stdin_sent_byte_count",
        "stdout_retained_byte_count",
        "stdout_total_byte_count",
        "stderr_total_byte_count",
    )
    for field in count_fields:
        if type(fact[field]) is not int or not 0 <= fact[field] < 2**63:
            _fail("formal host probe child byte count changed")
    if (
        fact["stdin_sent_byte_count"] > fact["stdin_expected_byte_count"]
        or fact["stdin_complete"]
        and fact["stdin_sent_byte_count"] != fact["stdin_expected_byte_count"]
        or fact["stdout_retained_byte_count"]
        > fact["stdout_total_byte_count"]
        or fact["stdout_retained_byte_count"]
        != min(
            fact["stdout_total_byte_count"],
            _HOST_PROBE_STDOUT_CAP_BYTES + 1,
        )
        or fact["stdout_overflow"]
        is not (
            fact["stdout_total_byte_count"] > _HOST_PROBE_STDOUT_CAP_BYTES
        )
        or fact["stderr_overflow"]
        is not (
            fact["stderr_total_byte_count"] > _HOST_PROBE_STDERR_CAP_BYTES
        )
    ):
        _fail("formal host probe child stream cardinality changed")
    for field in (
        "stdout_retained_sha256", "stdout_sha256", "stderr_sha256"
    ):
        _hex(fact[field], 64, "formal host probe " + field)
    stdout_prefix = _probe_capture_prefix(
        fact,
        stream="stdout",
        retained_count=fact["stdout_retained_byte_count"],
    )
    stderr_prefix = _probe_capture_prefix(
        fact,
        stream="stderr",
        retained_count=fact["stderr_total_byte_count"],
    )
    if (
        fact["stdout_retained_byte_count"] <= len(stdout_prefix)
        and hashlib.sha256(stdout_prefix).hexdigest()
        != fact["stdout_retained_sha256"]
        or fact["stderr_total_byte_count"] <= len(stderr_prefix)
        and hashlib.sha256(stderr_prefix).hexdigest() != fact["stderr_sha256"]
        or not fact["stdout_overflow"]
        and (
            fact["stdout_retained_byte_count"]
            != fact["stdout_total_byte_count"]
            or fact["stdout_retained_sha256"] != fact["stdout_sha256"]
        )
        or fact["stderr_total_byte_count"] == 0
        and (
            fact["stderr_prefix_byte_count"] != 0
            or fact["stderr_sha256"] != hashlib.sha256(b"").hexdigest()
            or fact["stderr_overflow"]
        )
    ):
        _fail("formal host probe child stream digest changed")
    closed_exactly = bool(
        fact["exec_succeeded"]
        and fact["returncode"] == 0
        and not fact["timed_out"]
        and fact["stdin_complete"]
        and fact["stdin_sent_byte_count"]
        == fact["stdin_expected_byte_count"]
        and not fact["stdout_overflow"]
        and fact["stdout_eof"]
        and fact["stdout_total_byte_count"]
        == fact["stdout_retained_byte_count"]
        and fact["stderr_total_byte_count"] == 0
        and fact["stderr_eof"]
    )
    return fact, closed_exactly


def build_formal_host_epoch_transport_observation_v42r3r1(
    *, probe_plan: Mapping[str, Any], probe_attempt: Mapping[str, Any],
    child_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the controller-visible SSH closure before accepting a receipt."""

    plan = verify_formal_host_epoch_probe_plan_v42r3(probe_plan)
    attempt = verify_formal_host_epoch_probe_attempt_v42r3r1(
        probe_attempt, probe_plan=plan
    )
    child, closed_exactly = _verify_host_probe_child_observation(
        child_observation
    )
    payload = {
        **_base(FORMAL_HOST_EPOCH_TRANSPORT_OBSERVATION_SCHEMA),
        "formal_host_epoch_probe_plan_id": plan[
            "formal_host_epoch_probe_plan_id"
        ],
        "formal_host_epoch_probe_attempt_id": attempt[
            "formal_host_epoch_probe_attempt_id"
        ],
        "child_observation": child,
        "process_closed_exactly": closed_exactly,
        "network_dispatch_may_have_started": True,
        "controller_same_probe_dispatch_replay_allowed": False,
        "formal_host_epoch_receipt_authenticated_by_this_observation": False,
        "controller_prepare_authorized_by_this_observation": False,
        "authenticated_loader_and_receiver_probe_code_path_is_read_only": True,
        "authenticated_loader_and_receiver_remote_mutation_authorized": False,
        "end_to_end_remote_mutation_absence_claimed": False,
        "external_local_and_ssh_assumptions_observed_or_attested": False,
        "remote_path_noninterference_observed_or_attested": False,
    }
    return {
        **payload,
        "formal_host_epoch_transport_observation_id": _content_id(
            FORMAL_HOST_EPOCH_TRANSPORT_OBSERVATION_DOMAIN, payload
        ),
    }


def verify_formal_host_epoch_transport_observation_v42r3r1(
    value: bytes | Mapping[str, Any], *, probe_plan: Mapping[str, Any],
    probe_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(
        value, "formal host epoch transport observation"
    )
    expected = build_formal_host_epoch_transport_observation_v42r3r1(
        probe_plan=probe_plan,
        probe_attempt=probe_attempt,
        child_observation=document.get("child_observation"),
    )
    if document != expected:
        _fail("formal host epoch transport observation changed")
    return document


def verify_formal_host_epoch_transport_receipt_join_v42r3r1(
    *, transport_observation: bytes | Mapping[str, Any],
    probe_plan: Mapping[str, Any], probe_attempt: Mapping[str, Any],
    receipt_raw: bytes,
) -> dict[str, Any]:
    """Require the exact successful stdout stream to frame the retained receipt."""

    plan = verify_formal_host_epoch_probe_plan_v42r3(probe_plan)
    observation = verify_formal_host_epoch_transport_observation_v42r3r1(
        transport_observation,
        probe_plan=plan,
        probe_attempt=probe_attempt,
    )
    if not observation["process_closed_exactly"]:
        _fail("formal host receipt follows a nonexact transport observation")
    receipt = verify_formal_host_epoch_receipt_v42r3(receipt_raw)
    if receipt["formal_host_epoch_probe_plan_id"] != plan[
        "formal_host_epoch_probe_plan_id"
    ]:
        _fail("formal host receipt/probe plan join changed")
    framed = receipt_raw + b"\n"
    digest = hashlib.sha256(framed).hexdigest()
    child = observation["child_observation"]
    prefix = framed[:_HOST_PROBE_CAPTURE_PREFIX_MAX_BYTES]
    if (
        child["stdout_retained_byte_count"] != len(framed)
        or child["stdout_total_byte_count"] != len(framed)
        or child["stdout_retained_sha256"] != digest
        or child["stdout_sha256"] != digest
        or child["stdout_prefix_byte_count"] != len(prefix)
        or child["stdout_prefix_hex"] != prefix.hex()
    ):
        _fail("formal host transport stdout/receipt byte join changed")
    return receipt


def build_formal_transport_plan_v42r3(
    *, controller_source_manifest: Mapping[str, Any],
    native_activation_binding: Mapping[str, Any],
    host_epoch_probe_plan: Mapping[str, Any],
    host_epoch_receipt: Mapping[str, Any],
    legacy_execution_source_manifest_id: str,
    known_hosts_path: str,
    local_journal_root: str,
    remote_journal_root: str,
) -> dict[str, Any]:
    """Bind the frozen V42r3 controller, host epoch, and transport roots."""

    controller = verify_controller_source_manifest_v42r3(
        controller_source_manifest
    )
    binding = verify_native_activation_binding_v42r3(
        native_activation_binding
    )
    probe = verify_formal_host_epoch_probe_plan_v42r3(host_epoch_probe_plan)
    receipt = verify_formal_host_epoch_receipt_v42r3(host_epoch_receipt)
    verified_local_stage0 = verify_external_local_stage0_assumption_v42r3(
        probe["external_local_stage0_assumption"],
        controller_source_manifest=controller,
    )
    verified_ssh_ingress = verify_external_ssh_ingress_assumption_v42r3(
        probe["external_ssh_ingress_assumption"]
    )
    legacy_source_id = _hex(
        legacy_execution_source_manifest_id,
        64,
        "legacy execution source manifest ID",
    )
    local_root = _absolute(local_journal_root, "local V42r3 journal root")
    remote_root = _absolute(remote_journal_root, "remote V42r3 journal root")
    known_hosts = _absolute(known_hosts_path, "V42r3 known-hosts path")
    expected_local = str(LOCAL_FORMAL_JOURNAL_ROOT)
    expected_remote = str(REMOTE_FORMAL_JOURNAL_ROOT)
    expected_known_hosts = str(
        LOCAL_FORMAL_JOURNAL_ROOT / LOCAL_KNOWN_HOSTS_NAME
    )
    if (
        local_root != expected_local
        or remote_root != expected_remote
        or known_hosts != expected_known_hosts
    ):
        _fail("formal transport plan journal root changed")
    facts = {row["relative_path"]: row for row in controller["source_facts"]}
    if (
        probe["controller_source_manifest_id"]
        != controller["controller_source_manifest_id"]
        or probe["probe_loader_artifact"] != facts[PROBE_LOADER_RELATIVE]
        or probe["formal_authority_artifact"]
        != facts[FORMAL_AUTHORITY_RELATIVE]
        or probe["probe_receiver_artifact"]
        != facts[PROBE_RECEIVER_RELATIVE]
        or probe["native_activation_binding"] != binding
        or probe["legacy_execution_source_manifest_id"] != legacy_source_id
        or probe["external_local_stage0_assumption_id"]
        != verified_local_stage0["external_local_stage0_assumption_id"]
        or probe["external_ssh_ingress_assumption_id"]
        != verified_ssh_ingress["external_ssh_ingress_assumption_id"]
        or receipt["formal_host_epoch_probe_plan_id"]
        != probe["formal_host_epoch_probe_plan_id"]
    ):
        _fail("formal transport controller, native, or host-epoch join changed")
    runtime = receipt["observed_runtime"]
    manager = receipt["manager_binding"]
    if (
        runtime["hostname"] != binding["observed_remote_hostname"]
        or runtime["user"] != binding["observed_remote_user"]
        or runtime["uid"] != binding["observed_remote_uid"]
        or runtime["gid"] != binding["observed_remote_gid"]
    ):
        _fail("formal transport host receipt/native identity join changed")
    payload = {
        **_base(FORMAL_TRANSPORT_PLAN_SCHEMA),
        "controller_source_manifest_id": controller[
            "controller_source_manifest_id"
        ],
        "probe_loader_artifact": probe["probe_loader_artifact"],
        "formal_authority_artifact": probe["formal_authority_artifact"],
        "probe_receiver_artifact": probe["probe_receiver_artifact"],
        "native_activation_binding": binding,
        "native_activation_binding_id": binding[
            "native_activation_binding_id"
        ],
        "formal_host_epoch_probe_plan_id": probe[
            "formal_host_epoch_probe_plan_id"
        ],
        "host_epoch_receipt": receipt,
        "formal_host_epoch_receipt_id": receipt[
            "formal_host_epoch_receipt_id"
        ],
        "legacy_execution_source_manifest_id": legacy_source_id,
        "external_local_stage0_assumption": probe[
            "external_local_stage0_assumption"
        ],
        "external_local_stage0_assumption_id": probe[
            "external_local_stage0_assumption_id"
        ],
        "external_ssh_ingress_assumption": probe[
            "external_ssh_ingress_assumption"
        ],
        "external_ssh_ingress_assumption_id": probe[
            "external_ssh_ingress_assumption_id"
        ],
        "source_commit": binding["source_commit"],
        "source_tree": binding["source_tree"],
        "source_manifest_id": binding["source_manifest_id"],
        "transport_manifest_id": binding["transport_manifest_id"],
        "fixed_remote_root": binding["fixed_remote_root"],
        "fixed_source_root": binding["fixed_source_root"],
        "remote_target_alias": binding["remote_target_alias"],
        "expected_remote_hostname": binding["expected_remote_hostname"],
        "observed_remote_hostname": runtime["hostname"],
        "observed_remote_user": runtime["user"],
        "observed_remote_uid": runtime["uid"],
        "observed_remote_gid": runtime["gid"],
        "kernel_boot_id": manager["kernel_boot_id"],
        "user_manager_invocation_id": manager[
            "user_manager_invocation_id"
        ],
        "user_manager_main_pid": manager["user_manager_main_pid"],
        "user_manager_control_group": manager[
            "user_manager_control_group"
        ],
        "remote_tool_facts": receipt["remote_tool_facts"],
        "known_hosts_path": known_hosts,
        "local_journal_root": local_root,
        "remote_journal_root": remote_root,
        "formal_runtime_is_independent_of_ssh_lifetime": True,
        (
            "local_network_marker_precedes_each_authorized_prepare_or_launch_"
            "ssh_dispatch"
        ): True,
        "controller_same_effect_dispatch_replay_forbidden_after_marker": True,
        (
            "controller_authorizes_only_authenticated_inspection_after_marker"
        ): True,
        "unit_absence_never_proves_service_never_started": True,
        (
            "ssh_daemon_login_shell_pam_and_startup_hooks_are_external_tcb"
        ): True,
        (
            "authenticated_remote_source_boundary_begins_after_login_shell_"
            "at_loader"
        ): True,
        "pre_loader_effect_freedom_claimed": False,
        "root_owned_forced_command_entry_claimed": False,
        "host_epoch_drift_detection_uses_boundary_sampling": True,
        "atomic_host_epoch_lock_across_external_effect_claimed": False,
    }
    return {
        **payload,
        "formal_transport_plan_id": _content_id(
            FORMAL_TRANSPORT_PLAN_DOMAIN, payload
        ),
    }


_FORMAL_TRANSPORT_PLAN_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "global_execution_ordinal",
        "controller_source_manifest_id",
        "probe_loader_artifact",
        "formal_authority_artifact",
        "probe_receiver_artifact",
        "native_activation_binding",
        "native_activation_binding_id",
        "formal_host_epoch_probe_plan_id",
        "host_epoch_receipt",
        "formal_host_epoch_receipt_id",
        "legacy_execution_source_manifest_id",
        "external_local_stage0_assumption",
        "external_local_stage0_assumption_id",
        "external_ssh_ingress_assumption",
        "external_ssh_ingress_assumption_id",
        "source_commit",
        "source_tree",
        "source_manifest_id",
        "transport_manifest_id",
        "fixed_remote_root",
        "fixed_source_root",
        "remote_target_alias",
        "expected_remote_hostname",
        "observed_remote_hostname",
        "observed_remote_user",
        "observed_remote_uid",
        "observed_remote_gid",
        "kernel_boot_id",
        "user_manager_invocation_id",
        "user_manager_main_pid",
        "user_manager_control_group",
        "remote_tool_facts",
        "known_hosts_path",
        "local_journal_root",
        "remote_journal_root",
        "formal_runtime_is_independent_of_ssh_lifetime",
        (
            "local_network_marker_precedes_each_authorized_prepare_or_launch_"
            "ssh_dispatch"
        ),
        "controller_same_effect_dispatch_replay_forbidden_after_marker",
        "controller_authorizes_only_authenticated_inspection_after_marker",
        "unit_absence_never_proves_service_never_started",
        "ssh_daemon_login_shell_pam_and_startup_hooks_are_external_tcb",
        (
            "authenticated_remote_source_boundary_begins_after_login_shell_"
            "at_loader"
        ),
        "pre_loader_effect_freedom_claimed",
        "root_owned_forced_command_entry_claimed",
        "host_epoch_drift_detection_uses_boundary_sampling",
        "atomic_host_epoch_lock_across_external_effect_claimed",
        "formal_transport_plan_id",
    }
)


def verify_formal_transport_plan_v42r3(
    value: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "formal V42r3 transport plan")
    if set(document) != _FORMAL_TRANSPORT_PLAN_FIELDS:
        _fail("formal V42r3 transport plan field set changed")
    _verify_base(document, FORMAL_TRANSPORT_PLAN_SCHEMA, "formal transport plan")
    binding = verify_native_activation_binding_v42r3(
        document["native_activation_binding"]
    )
    receipt = verify_formal_host_epoch_receipt_v42r3(
        document["host_epoch_receipt"]
    )
    if (
        document["native_activation_binding_id"]
        != binding["native_activation_binding_id"]
        or document["formal_host_epoch_receipt_id"]
        != receipt["formal_host_epoch_receipt_id"]
        or document["formal_host_epoch_probe_plan_id"]
        != receipt["formal_host_epoch_probe_plan_id"]
    ):
        _fail("formal transport native or host-epoch identity changed")
    _hex(
        document["controller_source_manifest_id"],
        64,
        "controller source manifest ID",
    )
    _verify_source_fact(document["probe_loader_artifact"], PROBE_LOADER_RELATIVE)
    _verify_source_fact(
        document["formal_authority_artifact"], FORMAL_AUTHORITY_RELATIVE
    )
    _verify_source_fact(
        document["probe_receiver_artifact"], PROBE_RECEIVER_RELATIVE
    )
    _hex(
        document["legacy_execution_source_manifest_id"],
        64,
        "legacy execution source manifest ID",
    )
    local_stage0 = verify_external_local_stage0_assumption_v42r3(
        document["external_local_stage0_assumption"]
    )
    ssh_ingress = verify_external_ssh_ingress_assumption_v42r3(
        document["external_ssh_ingress_assumption"]
    )
    if (
        local_stage0["controller_source_manifest_id"]
        != document["controller_source_manifest_id"]
        or document["external_local_stage0_assumption_id"]
        != local_stage0["external_local_stage0_assumption_id"]
        or document["external_ssh_ingress_assumption_id"]
        != ssh_ingress["external_ssh_ingress_assumption_id"]
    ):
        _fail("formal transport external assumption join changed")
    direct_binding = {
        "source_commit": "source_commit",
        "source_tree": "source_tree",
        "source_manifest_id": "source_manifest_id",
        "transport_manifest_id": "transport_manifest_id",
        "fixed_remote_root": "fixed_remote_root",
        "fixed_source_root": "fixed_source_root",
        "remote_target_alias": "remote_target_alias",
        "expected_remote_hostname": "expected_remote_hostname",
    }
    if any(
        document[direct] != binding[nested]
        for direct, nested in direct_binding.items()
    ):
        _fail("formal transport source, transport, root, or target join changed")
    runtime = receipt["observed_runtime"]
    manager = receipt["manager_binding"]
    if (
        document["observed_remote_hostname"] != runtime["hostname"]
        or document["observed_remote_user"] != runtime["user"]
        or document["observed_remote_uid"] != runtime["uid"]
        or document["observed_remote_gid"] != runtime["gid"]
        or document["kernel_boot_id"] != manager["kernel_boot_id"]
        or document["user_manager_invocation_id"]
        != manager["user_manager_invocation_id"]
        or document["user_manager_main_pid"]
        != manager["user_manager_main_pid"]
        or document["user_manager_control_group"]
        != manager["user_manager_control_group"]
        or document["remote_tool_facts"] != receipt["remote_tool_facts"]
    ):
        _fail("formal transport live host identity or tool join changed")
    _verify_tools(document["remote_tool_facts"])
    if (
        document["local_journal_root"] != str(LOCAL_FORMAL_JOURNAL_ROOT)
        or document["remote_journal_root"] != str(REMOTE_FORMAL_JOURNAL_ROOT)
        or document["known_hosts_path"]
        != str(LOCAL_FORMAL_JOURNAL_ROOT / LOCAL_KNOWN_HOSTS_NAME)
        or any(
            document[field] is not True
            for field in (
                "formal_runtime_is_independent_of_ssh_lifetime",
                (
                    "local_network_marker_precedes_each_authorized_prepare_"
                    "or_launch_ssh_dispatch"
                ),
                "controller_same_effect_dispatch_replay_forbidden_after_marker",
                (
                    "controller_authorizes_only_authenticated_inspection_"
                    "after_marker"
                ),
                "unit_absence_never_proves_service_never_started",
                (
                    "ssh_daemon_login_shell_pam_and_startup_hooks_are_"
                    "external_tcb"
                ),
                (
                    "authenticated_remote_source_boundary_begins_after_"
                    "login_shell_at_loader"
                ),
                "host_epoch_drift_detection_uses_boundary_sampling",
            )
        )
        or document["pre_loader_effect_freedom_claimed"] is not False
        or document["root_owned_forced_command_entry_claimed"] is not False
        or document[
            "atomic_host_epoch_lock_across_external_effect_claimed"
        ] is not False
    ):
        _fail("formal transport frozen root or replay contract changed")
    _verify_claimed_id(
        document,
        field="formal_transport_plan_id",
        domain=FORMAL_TRANSPORT_PLAN_DOMAIN,
        label="formal transport plan",
    )
    return document


def _authority_plan_projection(
    formal_transport_plan: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str]:
    document = _canonical_document(formal_transport_plan, "authority plan")
    if document.get("schema") == FORMAL_TRANSPORT_PLAN_SCHEMA:
        plan = verify_formal_transport_plan_v42r3(document)
        binding = plan["native_activation_binding"]
        plan_id = plan["formal_transport_plan_id"]
    elif document.get("schema") == FORMAL_HOST_EPOCH_PROBE_PLAN_SCHEMA:
        plan = verify_formal_host_epoch_probe_plan_v42r3(document)
        binding = plan["native_activation_binding"]
        plan_id = plan["formal_host_epoch_probe_plan_id"]
    else:
        _fail("cross-version authority plan schema changed")
    return plan, binding, plan_id


_CROSS_VERSION_PHASES = {
    "PROBE_HOST_EPOCH": (
        frozenset({"POST_MATERIALIZATION_PREPARE"}),
        False,
    ),
    "PREPARE": (frozenset({"POST_MATERIALIZATION_PREPARE"}), True),
    "INSPECT_PREPARE": (
        frozenset(
            {
                "POST_MATERIALIZATION_PREPARE",
                "POST_PREPARE_AWAITING_LOCAL_LAUNCH",
                "POST_PREPARE_PRELAUNCH",
                "POST_LAUNCH",
            }
        ),
        False,
    ),
    "ADMIT_LAUNCH": (
        frozenset({"POST_PREPARE_AWAITING_LOCAL_LAUNCH"}),
        True,
    ),
    "SYSTEMD_ADMISSION": (frozenset({"POST_PREPARE_PRELAUNCH"}), True),
    "INSPECT_LAUNCH": (
        frozenset(
            {
                "POST_MATERIALIZATION_PREPARE",
                "POST_PREPARE_AWAITING_LOCAL_LAUNCH",
                "POST_PREPARE_PRELAUNCH",
                "POST_LAUNCH",
            }
        ),
        False,
    ),
    "SERVICE_BOOTSTRAP": (frozenset({"POST_PREPARE_PRELAUNCH"}), True),
    "SERVICE_WRAPPER": (frozenset({"POST_PREPARE_PRELAUNCH"}), True),
}


def verify_cross_version_scientific_state_gate_v42r3(
    *, formal_transport_plan: Mapping[str, Any], operation: str,
    legacy_scientific_phase: Mapping[str, Any], effect_authorized: bool,
) -> dict[str, Any]:
    """Join one verified legacy scientific phase to one V42r3 role."""

    plan, binding, plan_id = _authority_plan_projection(formal_transport_plan)
    if operation not in _CROSS_VERSION_PHASES or type(effect_authorized) is not bool:
        _fail("cross-version scientific-state operation changed")
    if not isinstance(legacy_scientific_phase, Mapping):
        _fail("legacy scientific phase changed type")
    phase = legacy_scientific_phase.get("phase")
    allowed_phases, expected_authorization = _CROSS_VERSION_PHASES[operation]
    if phase not in allowed_phases or effect_authorized is not expected_authorization:
        _fail("cross-version scientific phase/authorization combination changed")
    source = legacy_scientific_phase.get("source_manifest")
    if source is not None:
        if not isinstance(source, Mapping) or any(
            source.get(field) != binding[field]
            for field in ("source_commit", "source_tree", "source_manifest_id")
        ):
            _fail("legacy scientific source manifest differs from native binding")
    transport = legacy_scientific_phase.get("transport_manifest")
    if transport is not None and (
        not isinstance(transport, Mapping)
        or transport.get("transport_manifest_id")
        != binding["transport_manifest_id"]
    ):
        _fail("legacy scientific transport manifest differs from native binding")
    for field in (
        "local_materialization_attempt_id",
        "remote_materialization_attempt_id",
        "materialization_terminal_id",
    ):
        if field in legacy_scientific_phase and (
            legacy_scientific_phase[field] != binding[field]
        ):
            _fail("legacy scientific materialization join changed: " + field)
    payload = {
        **_base(CROSS_VERSION_SCIENTIFIC_STATE_GATE_SCHEMA),
        "authority_plan_id": plan_id,
        "legacy_execution_source_manifest_id": plan[
            "legacy_execution_source_manifest_id"
        ],
        "source_commit": binding["source_commit"],
        "source_tree": binding["source_tree"],
        "source_manifest_id": binding["source_manifest_id"],
        "transport_manifest_id": binding["transport_manifest_id"],
        "local_materialization_attempt_id": binding[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": binding[
            "remote_materialization_attempt_id"
        ],
        "materialization_terminal_id": binding["materialization_terminal_id"],
        "legacy_scientific_phase": phase,
        "operation": operation,
        "effect_authorized": effect_authorized,
        "cross_version_scientific_state_gate_passed": True,
    }
    return {
        **payload,
        "cross_version_scientific_state_gate_id": _content_id(
            CROSS_VERSION_SCIENTIFIC_STATE_GATE_DOMAIN, payload
        ),
    }


def _verify_cross_version_gate_document(
    value: bytes | Mapping[str, Any], *, formal_transport_plan: Mapping[str, Any],
    operation: str,
) -> dict[str, Any]:
    document = _canonical_document(value, "cross-version scientific-state gate")
    fields = frozenset(
        {
            "schema",
            "schema_version",
            "formal_identity",
            "global_execution_ordinal",
            "authority_plan_id",
            "legacy_execution_source_manifest_id",
            "source_commit",
            "source_tree",
            "source_manifest_id",
            "transport_manifest_id",
            "local_materialization_attempt_id",
            "remote_materialization_attempt_id",
            "materialization_terminal_id",
            "legacy_scientific_phase",
            "operation",
            "effect_authorized",
            "cross_version_scientific_state_gate_passed",
            "cross_version_scientific_state_gate_id",
        }
    )
    if set(document) != fields:
        _fail("cross-version scientific-state gate field set changed")
    _verify_base(
        document,
        CROSS_VERSION_SCIENTIFIC_STATE_GATE_SCHEMA,
        "cross-version scientific-state gate",
    )
    plan, binding, plan_id = _authority_plan_projection(formal_transport_plan)
    allowed, authorized = _CROSS_VERSION_PHASES.get(
        operation, (frozenset(), None)
    )
    if (
        document["authority_plan_id"] != plan_id
        or document["legacy_execution_source_manifest_id"]
        != plan["legacy_execution_source_manifest_id"]
        or document["operation"] != operation
        or document["legacy_scientific_phase"] not in allowed
        or document["effect_authorized"] is not authorized
        or document["cross_version_scientific_state_gate_passed"] is not True
        or any(
            document[field] != binding[field]
            for field in (
                "source_commit",
                "source_tree",
                "source_manifest_id",
                "transport_manifest_id",
                "local_materialization_attempt_id",
                "remote_materialization_attempt_id",
                "materialization_terminal_id",
            )
        )
    ):
        _fail("cross-version scientific-state gate join changed")
    _verify_claimed_id(
        document,
        field="cross_version_scientific_state_gate_id",
        domain=CROSS_VERSION_SCIENTIFIC_STATE_GATE_DOMAIN,
        label="cross-version scientific-state gate",
    )
    return document


def build_formal_prepare_attempt_v42r3(
    *, formal_transport_plan: Mapping[str, Any],
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    payload = {
        **_base(FORMAL_PREPARE_ATTEMPT_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "native_activation_binding_id": plan["native_activation_binding_id"],
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "remote_target_alias": plan["remote_target_alias"],
        "operation": OPERATION_PREPARE,
        "network_effect_started": False,
        (
            "controller_same_effect_dispatch_replay_forbidden_after_network_"
            "marker"
        ): True,
    }
    return {
        **payload,
        "formal_prepare_attempt_id": _content_id(
            FORMAL_PREPARE_ATTEMPT_DOMAIN, payload
        ),
    }


def verify_formal_prepare_attempt_v42r3(
    value: bytes | Mapping[str, Any], *,
    formal_transport_plan: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "formal prepare attempt")
    expected = build_formal_prepare_attempt_v42r3(
        formal_transport_plan=formal_transport_plan
    )
    if document != expected:
        _fail("formal prepare attempt changed")
    return document


def _legacy_prepare_projection(
    value: Mapping[str, Any], plan: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(value, Mapping):
        _fail("legacy scientific prepare receipt changed type")
    receipt = _canonical_document(value, "legacy scientific prepare receipt")
    result = {
        "prepare_receipt_id": _hex(
            receipt.get("prepare_receipt_id"), 64, "prepare receipt ID"
        ),
        "source_commit": _hex(
            receipt.get("source_commit"), 40, "prepare source commit"
        ),
        "source_tree": _hex(
            receipt.get("source_tree"), 40, "prepare source tree"
        ),
        "source_manifest_id": _hex(
            receipt.get("source_manifest_id"), 64, "prepare source manifest ID"
        ),
        "transport_manifest_id": _hex(
            receipt.get("transport_manifest_id"),
            64,
            "prepare transport manifest ID",
        ),
    }
    if any(result[field] != plan[field] for field in result if field != "prepare_receipt_id"):
        _fail("legacy prepare receipt differs from formal transport plan")
    return result


def _local_launch_projection(
    value: Mapping[str, Any], *, plan: Mapping[str, Any], prepare_receipt_id: str,
) -> dict[str, str]:
    if not isinstance(value, Mapping):
        _fail("legacy local launch attempt changed type")
    local = _canonical_document(value, "legacy local launch attempt")
    result = {
        "local_launch_attempt_id": _hex(
            local.get("local_launch_attempt_id"),
            64,
            "local launch attempt ID",
        ),
        "prepare_receipt_id": _hex(
            local.get("prepare_receipt_id"), 64, "local prepare receipt ID"
        ),
        "transport_target_alias": local.get("transport_target_alias"),
    }
    if (
        result["prepare_receipt_id"] != prepare_receipt_id
        or result["transport_target_alias"] != plan["remote_target_alias"]
    ):
        _fail("legacy local launch predecessor or target join changed")
    for field in (
        "source_commit",
        "source_tree",
        "source_manifest_id",
        "transport_manifest_id",
    ):
        if field in local and local[field] != plan[field]:
            _fail("legacy local launch source join changed: " + field)
    fixed = {
        "expected_remote_hostname": authority.REMOTE_HOSTNAME,
        "expected_remote_user": authority.REMOTE_USER,
        "expected_remote_uid": authority.REMOTE_UID,
        "launch_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "published_before_any_launch_transport_effect": True,
        "transport_effect_started": False,
        "same_identity_retry_forbidden_after_publication": True,
    }
    for field, expected in fixed.items():
        if field in local and local[field] != expected:
            _fail("legacy local launch fixed authority changed: " + field)
    return result


def unit_name_v42r3(local_launch_attempt_id: str) -> str:
    return SYSTEMD_UNIT_PREFIX + _hex(
        local_launch_attempt_id, 64, "local launch attempt ID"
    ) + ".service"


def build_formal_launch_transport_attempt_v42r3(
    *, formal_transport_plan: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    local_launch_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    receipt = _legacy_prepare_projection(prepare_receipt, plan)
    local = _local_launch_projection(
        local_launch_attempt,
        plan=plan,
        prepare_receipt_id=receipt["prepare_receipt_id"],
    )
    payload = {
        **_base(FORMAL_LAUNCH_TRANSPORT_ATTEMPT_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "prepare_receipt_id": receipt["prepare_receipt_id"],
        "local_launch_attempt_id": local["local_launch_attempt_id"],
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "unit_name": unit_name_v42r3(local["local_launch_attempt_id"]),
        "operation": OPERATION_LAUNCH,
        "network_effect_started": False,
        "systemd_admission_effect_started": False,
        (
            "controller_same_effect_dispatch_replay_forbidden_after_network_"
            "marker"
        ): True,
        "formal_execution_performed": False,
    }
    return {
        **payload,
        "formal_launch_transport_attempt_id": _content_id(
            FORMAL_LAUNCH_TRANSPORT_ATTEMPT_DOMAIN, payload
        ),
    }


_FORMAL_LAUNCH_TRANSPORT_ATTEMPT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "global_execution_ordinal",
        "formal_transport_plan_id",
        "prepare_receipt_id",
        "local_launch_attempt_id",
        "source_commit",
        "source_tree",
        "source_manifest_id",
        "transport_manifest_id",
        "unit_name",
        "operation",
        "network_effect_started",
        "systemd_admission_effect_started",
        (
            "controller_same_effect_dispatch_replay_forbidden_after_network_"
            "marker"
        ),
        "formal_execution_performed",
        "formal_launch_transport_attempt_id",
    }
)


def _verify_launch_transport_attempt_document(
    value: bytes | Mapping[str, Any], *, plan: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "formal launch transport attempt")
    if set(document) != _FORMAL_LAUNCH_TRANSPORT_ATTEMPT_FIELDS:
        _fail("formal launch transport attempt field set changed")
    _verify_base(
        document,
        FORMAL_LAUNCH_TRANSPORT_ATTEMPT_SCHEMA,
        "formal launch transport attempt",
    )
    local_id = _hex(
        document["local_launch_attempt_id"], 64, "local launch attempt ID"
    )
    _hex(document["prepare_receipt_id"], 64, "prepare receipt ID")
    if (
        document["formal_transport_plan_id"] != plan["formal_transport_plan_id"]
        or document["unit_name"] != unit_name_v42r3(local_id)
        or document["operation"] != OPERATION_LAUNCH
        or any(
            document[field] != plan[field]
            for field in (
                "source_commit",
                "source_tree",
                "source_manifest_id",
                "transport_manifest_id",
            )
        )
        or document["network_effect_started"] is not False
        or document["systemd_admission_effect_started"] is not False
        or document[
            "controller_same_effect_dispatch_replay_forbidden_after_network_marker"
        ]
        is not True
        or document["formal_execution_performed"] is not False
    ):
        _fail("formal launch transport attempt authority join changed")
    _verify_claimed_id(
        document,
        field="formal_launch_transport_attempt_id",
        domain=FORMAL_LAUNCH_TRANSPORT_ATTEMPT_DOMAIN,
        label="formal launch transport attempt",
    )
    return document


def verify_formal_launch_transport_attempt_v42r3(
    value: bytes | Mapping[str, Any], *,
    formal_transport_plan: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    local_launch_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    expected = build_formal_launch_transport_attempt_v42r3(
        formal_transport_plan=plan,
        prepare_receipt=prepare_receipt,
        local_launch_attempt=local_launch_attempt,
    )
    document = _verify_launch_transport_attempt_document(value, plan=plan)
    if document != expected:
        _fail("formal launch transport attempt changed")
    return document


def _decimal_count(value: Any, label: str) -> int:
    if (
        type(value) is not str
        or not value.isdecimal()
        or value != str(int(value))
        or int(value) <= 0
        or int(value) > 64 * 1024**2
    ):
        _fail(label + " changed")
    return int(value)


def _verify_service_bootstrap_argv(
    value: Sequence[str], *, plan: Mapping[str, Any], attempt_id: str,
) -> tuple[str, ...]:
    if (
        type(value) not in {list, tuple}
        or len(value) != 20
        or any(type(item) is not str or not item for item in value)
    ):
        _fail("formal service bootstrap argv changed type or length")
    argv = tuple(value)
    if (
        argv[:5] != (authority.REMOTE_PYTHON, "-I", "-S", "-B", "-c")
        or argv[6] != SERVICE_BOOTSTRAP_MODE
        or argv[17] != plan["formal_transport_plan_id"]
        or argv[18] != plan["legacy_execution_source_manifest_id"]
        or argv[19] != attempt_id
    ):
        _fail("formal service bootstrap identity or isolated flags changed")
    loader_raw = argv[5].encode("utf-8")
    loader_count = _decimal_count(argv[8], "bootstrap loader byte count")
    controller_count = _decimal_count(
        argv[10], "bootstrap controller byte count"
    )
    authority_count = _decimal_count(
        argv[12], "bootstrap authority byte count"
    )
    receiver_count = _decimal_count(
        argv[14], "bootstrap receiver byte count"
    )
    plan_count = _decimal_count(argv[16], "bootstrap plan byte count")
    del controller_count
    plan_raw = canonical_json_bytes(dict(plan))
    if (
        loader_count != len(loader_raw)
        or argv[7] != hashlib.sha256(loader_raw).hexdigest()
        or argv[7] != plan["probe_loader_artifact"]["sha256"]
        or loader_count != plan["probe_loader_artifact"]["byte_count"]
        or _hex(argv[9], 64, "bootstrap controller SHA256") != argv[9]
        or argv[11] != plan["formal_authority_artifact"]["sha256"]
        or authority_count != plan["formal_authority_artifact"]["byte_count"]
        or argv[13] != plan["probe_receiver_artifact"]["sha256"]
        or receiver_count != plan["probe_receiver_artifact"]["byte_count"]
        or argv[15] != hashlib.sha256(plan_raw).hexdigest()
        or plan_count != len(plan_raw)
    ):
        _fail("formal service bootstrap source or plan facts changed")
    return argv


def _service_wrapper_argv(
    bootstrap_argv: Sequence[str], *, invocation_id: str, control_group: str,
) -> tuple[str, ...]:
    bootstrap = list(bootstrap_argv)
    bootstrap[6] = SERVICE_WRAPPER_MODE
    return (*bootstrap, invocation_id, control_group)


def _systemd_run_argv_from_bootstrap(
    *, plan: Mapping[str, Any], attempt_id: str,
    service_bootstrap_argv: Sequence[str],
) -> tuple[str, ...]:
    bootstrap = _verify_service_bootstrap_argv(
        service_bootstrap_argv, plan=plan, attempt_id=attempt_id
    )
    return (
        SYSTEMD_RUN,
        "--user",
        "--quiet",
        "--no-ask-password",
        "--service-type=exec",
        "--unit=" + unit_name_v42r3(attempt_id),
        "--slice=" + SYSTEMD_SLICE,
        "--property=Restart=no",
        "--property=RemainAfterExit=yes",
        "--property=SuccessExitStatus=2",
        "--property=UMask=0077",
        "--property=KillMode=mixed",
        f"--property=TimeoutStopSec={SYSTEMD_TIMEOUT_STOP_SECONDS}s",
        f"--property=RuntimeMaxSec={SYSTEMD_RUNTIME_MAX_SECONDS}s",
        "--property=StandardInput=null",
        "--property=StandardOutput=null",
        "--property=StandardError=null",
        "--working-directory=" + plan["fixed_source_root"],
        "--",
        *bootstrap,
    )


def build_systemd_run_argv_v42r3(
    *, formal_transport_plan: Mapping[str, Any],
    local_launch_attempt: Mapping[str, Any],
    service_bootstrap_argv: Sequence[str],
) -> tuple[str, ...]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    if not isinstance(local_launch_attempt, Mapping):
        _fail("local launch attempt changed type")
    attempt_id = _hex(
        local_launch_attempt.get("local_launch_attempt_id"),
        64,
        "local launch attempt ID",
    )
    if (
        "transport_target_alias" in local_launch_attempt
        and local_launch_attempt["transport_target_alias"]
        != plan["remote_target_alias"]
    ):
        _fail("local launch target alias changed")
    return _systemd_run_argv_from_bootstrap(
        plan=plan,
        attempt_id=attempt_id,
        service_bootstrap_argv=service_bootstrap_argv,
    )


def verify_systemd_run_argv_v42r3(
    value: Sequence[str], *, formal_transport_plan: Mapping[str, Any],
    local_launch_attempt: Mapping[str, Any],
    service_bootstrap_argv: Sequence[str],
) -> tuple[str, ...]:
    expected = build_systemd_run_argv_v42r3(
        formal_transport_plan=formal_transport_plan,
        local_launch_attempt=local_launch_attempt,
        service_bootstrap_argv=service_bootstrap_argv,
    )
    if type(value) not in {list, tuple} or tuple(value) != expected:
        _fail("formal systemd-run whitelist changed")
    if any(
        item in FORBIDDEN_SYSTEMD_OPTIONS
        or any(item.startswith(option + "=") for option in FORBIDDEN_SYSTEMD_OPTIONS)
        or "bindsto" in item.lower().replace("-", "")
        for item in value
    ):
        _fail("formal systemd-run lifecycle coupling is forbidden")
    return expected


_UNIT_OBSERVATION_FIELDS = frozenset(
    {
        "Id",
        "LoadState",
        "ActiveState",
        "SubState",
        "Result",
        "InvocationID",
        "MainPID",
        "ControlGroup",
        "Type",
        "Restart",
        "RemainAfterExit",
        "SuccessExitStatus",
        "UMask",
        "KillMode",
        "TimeoutStopUSec",
        "RuntimeMaxUSec",
        "StandardInput",
        "StandardOutput",
        "StandardError",
        "WorkingDirectory",
        "Slice",
        "FragmentPath",
        "Environment",
        "LiveMainPIDArgv",
        "LiveMainPIDArgvSource",
    }
)


def _effect_manager_binding(
    value: Mapping[str, Any], *, plan: Mapping[str, Any], require_match: bool,
) -> tuple[dict[str, Any], bool]:
    manager = _verify_manager(value)
    expected = plan["host_epoch_receipt"]["manager_binding"]
    matches = manager == expected
    if require_match and not matches:
        _fail("formal effect user-manager epoch differs from host receipt")
    return manager, matches


def _loaded_unit_observation(
    value: Mapping[str, Any], *, plan: Mapping[str, Any], attempt_id: str,
    manager: Mapping[str, Any], service_bootstrap_argv: Sequence[str],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    unit = _mapping(value, _UNIT_OBSERVATION_FIELDS, "loaded systemd unit")
    invocation = _uuid(unit["InvocationID"], "unit invocation ID")
    expected_name = unit_name_v42r3(attempt_id)
    control_group = unit["ControlGroup"]
    if (
        unit["Id"] != expected_name
        or unit["LoadState"] != "loaded"
        or unit["ActiveState"] not in {"active", "activating"}
        or unit["SubState"] not in {"start", "running"}
        or type(unit["Result"]) is not str
        or type(unit["MainPID"]) is not int
        or unit["MainPID"] <= 1
        or type(control_group) is not str
        or _CGROUP.fullmatch(control_group) is None
        or not control_group.startswith(
            manager["user_manager_control_group"] + "/"
        )
        or not control_group.endswith("/" + expected_name)
        or unit["Type"] != "exec"
        or unit["Restart"] != "no"
        or unit["RemainAfterExit"] != "yes"
        or unit["SuccessExitStatus"] != "2"
        or unit["UMask"] != "0077"
        or unit["KillMode"] != "mixed"
        or unit["TimeoutStopUSec"] != "30s"
        or unit["RuntimeMaxUSec"] != "1w 25min"
        or unit["StandardInput"] != "null"
        or unit["StandardOutput"] != "null"
        or unit["StandardError"] != "null"
        or unit["WorkingDirectory"] != plan["fixed_source_root"]
        or unit["Slice"] != SYSTEMD_SLICE
        or unit["FragmentPath"]
        != (
            f"/run/user/{authority.REMOTE_UID}/systemd/transient/"
            + expected_name
        )
        or unit["Environment"] != ""
        or unit["LiveMainPIDArgvSource"] != "PROC_MAINPID_CMDLINE"
    ):
        _fail("loaded V42r3 systemd unit contract changed")
    wrapper = _service_wrapper_argv(
        service_bootstrap_argv,
        invocation_id=invocation,
        control_group=control_group,
    )
    if unit["LiveMainPIDArgv"] != list(wrapper):
        _fail("loaded V42r3 systemd unit live wrapper argv changed")
    return unit, wrapper


def build_launch_admission_receipt_v42r3(
    *, formal_transport_plan: Mapping[str, Any],
    launch_transport_attempt: Mapping[str, Any],
    manager_binding: Mapping[str, Any], unit_observation: Mapping[str, Any],
    systemd_run_argv: Sequence[str],
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    attempt = _verify_launch_transport_attempt_document(
        launch_transport_attempt, plan=plan
    )
    manager, _matches = _effect_manager_binding(
        manager_binding, plan=plan, require_match=True
    )
    if type(systemd_run_argv) not in {list, tuple}:
        _fail("admission systemd-run argv changed type")
    argv = tuple(systemd_run_argv)
    if argv.count("--") != 1:
        _fail("admission systemd-run separator changed")
    bootstrap = argv[argv.index("--") + 1 :]
    expected_argv = _systemd_run_argv_from_bootstrap(
        plan=plan,
        attempt_id=attempt["local_launch_attempt_id"],
        service_bootstrap_argv=bootstrap,
    )
    if argv != expected_argv:
        _fail("admission systemd-run whitelist changed")
    unit, wrapper = _loaded_unit_observation(
        unit_observation,
        plan=plan,
        attempt_id=attempt["local_launch_attempt_id"],
        manager=manager,
        service_bootstrap_argv=bootstrap,
    )
    payload = {
        **_base(FORMAL_LAUNCH_ADMISSION_RECEIPT_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "formal_launch_transport_attempt_id": attempt[
            "formal_launch_transport_attempt_id"
        ],
        "prepare_receipt_id": attempt["prepare_receipt_id"],
        "local_launch_attempt_id": attempt["local_launch_attempt_id"],
        "unit_name": attempt["unit_name"],
        "unit_invocation_id": unit["InvocationID"],
        "unit_main_pid": unit["MainPID"],
        "unit_control_group": unit["ControlGroup"],
        "manager_binding": manager,
        "systemd_run_argv": list(argv),
        "systemd_run_argv_sha256": hashlib.sha256(
            canonical_json_bytes(list(argv))
        ).hexdigest(),
        "systemd_client_environment": dict(SYSTEMD_CLIENT_ENVIRONMENT),
        "formal_service_environment": dict(FORMAL_SERVICE_ENVIRONMENT),
        "configured_exec_start_argv": list(bootstrap),
        "live_post_env_main_pid_argv": list(wrapper),
        "remote_tool_facts": plan["remote_tool_facts"],
        "systemd_admission_returncode": 0,
        "service_lifetime_is_independent_of_ssh": True,
        "controller_same_admission_dispatch_retry_forbidden": True,
        "formal_execution_result_not_claimed": True,
    }
    return {
        **payload,
        "formal_launch_admission_receipt_id": _content_id(
            FORMAL_LAUNCH_ADMISSION_RECEIPT_DOMAIN, payload
        ),
    }


_FORMAL_LAUNCH_ADMISSION_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "global_execution_ordinal",
        "formal_transport_plan_id",
        "formal_launch_transport_attempt_id",
        "prepare_receipt_id",
        "local_launch_attempt_id",
        "unit_name",
        "unit_invocation_id",
        "unit_main_pid",
        "unit_control_group",
        "manager_binding",
        "systemd_run_argv",
        "systemd_run_argv_sha256",
        "systemd_client_environment",
        "formal_service_environment",
        "configured_exec_start_argv",
        "live_post_env_main_pid_argv",
        "remote_tool_facts",
        "systemd_admission_returncode",
        "service_lifetime_is_independent_of_ssh",
        "controller_same_admission_dispatch_retry_forbidden",
        "formal_execution_result_not_claimed",
        "formal_launch_admission_receipt_id",
    }
)


def verify_launch_admission_receipt_v42r3(
    value: bytes | Mapping[str, Any], *,
    formal_transport_plan: Mapping[str, Any],
    launch_transport_attempt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    document = _canonical_document(value, "formal launch admission receipt")
    if set(document) != _FORMAL_LAUNCH_ADMISSION_RECEIPT_FIELDS:
        _fail("formal launch admission receipt field set changed")
    _verify_base(
        document,
        FORMAL_LAUNCH_ADMISSION_RECEIPT_SCHEMA,
        "formal launch admission receipt",
    )
    local_id = _hex(
        document["local_launch_attempt_id"], 64, "admission local attempt ID"
    )
    _hex(document["prepare_receipt_id"], 64, "admission prepare receipt ID")
    _hex(
        document["formal_launch_transport_attempt_id"],
        64,
        "formal launch transport attempt ID",
    )
    if launch_transport_attempt is not None:
        attempt = _verify_launch_transport_attempt_document(
            launch_transport_attempt, plan=plan
        )
        if any(
            document[field] != attempt[field]
            for field in (
                "formal_launch_transport_attempt_id",
                "prepare_receipt_id",
                "local_launch_attempt_id",
                "unit_name",
            )
        ):
            _fail("formal admission/launch attempt join changed")
    manager, _matches = _effect_manager_binding(
        document["manager_binding"], plan=plan, require_match=True
    )
    bootstrap = document["configured_exec_start_argv"]
    expected_argv = _systemd_run_argv_from_bootstrap(
        plan=plan,
        attempt_id=local_id,
        service_bootstrap_argv=bootstrap,
    )
    invocation = _uuid(
        document["unit_invocation_id"], "admission unit invocation ID"
    )
    control_group = document["unit_control_group"]
    expected_wrapper = _service_wrapper_argv(
        bootstrap,
        invocation_id=invocation,
        control_group=control_group,
    )
    if (
        document["formal_transport_plan_id"] != plan["formal_transport_plan_id"]
        or document["unit_name"] != unit_name_v42r3(local_id)
        or type(document["unit_main_pid"]) is not int
        or document["unit_main_pid"] <= 1
        or type(control_group) is not str
        or _CGROUP.fullmatch(control_group) is None
        or not control_group.startswith(
            manager["user_manager_control_group"] + "/"
        )
        or not control_group.endswith("/" + document["unit_name"])
        or document["systemd_run_argv"] != list(expected_argv)
        or document["systemd_run_argv_sha256"]
        != hashlib.sha256(canonical_json_bytes(list(expected_argv))).hexdigest()
        or document["systemd_client_environment"] != SYSTEMD_CLIENT_ENVIRONMENT
        or document["formal_service_environment"] != FORMAL_SERVICE_ENVIRONMENT
        or document["live_post_env_main_pid_argv"] != list(expected_wrapper)
        or document["remote_tool_facts"] != plan["remote_tool_facts"]
        or document["systemd_admission_returncode"] != 0
        or document["service_lifetime_is_independent_of_ssh"] is not True
        or document["controller_same_admission_dispatch_retry_forbidden"]
        is not True
        or document["formal_execution_result_not_claimed"] is not True
    ):
        _fail("formal launch admission receipt authority changed")
    _verify_claimed_id(
        document,
        field="formal_launch_admission_receipt_id",
        domain=FORMAL_LAUNCH_ADMISSION_RECEIPT_DOMAIN,
        label="formal launch admission receipt",
    )
    return document


def _verify_stdio_facts(
    value: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if type(value) not in {list, tuple} or len(value) != 3:
        _fail("formal service stdio inventory changed")
    result: list[dict[str, Any]] = []
    fields = frozenset({"descriptor", "target", "node_type", "isatty"})
    for descriptor, raw in enumerate(value):
        fact = _mapping(raw, fields, "formal service stdio fact")
        if fact != {
            "descriptor": descriptor,
            "target": "/dev/null",
            "node_type": "CHARACTER_DEVICE",
            "isatty": False,
        }:
            _fail("formal service stdio is not exact /dev/null")
        result.append(fact)
    return result


def build_service_wrapper_attestation_v42r3(
    *, formal_transport_plan: Mapping[str, Any],
    launch_transport_attempt: Mapping[str, Any],
    launch_admission_receipt: Mapping[str, Any],
    cross_version_scientific_state_gate: Mapping[str, Any],
    manager_binding: Mapping[str, Any], unit_observation: Mapping[str, Any],
    service_pid: int, service_cgroup: str,
    service_environment: Mapping[str, str],
    stdio_facts: Sequence[Mapping[str, Any]],
    live_file_descriptors: Sequence[int],
    live_tool_facts: Mapping[str, Any],
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    attempt = _verify_launch_transport_attempt_document(
        launch_transport_attempt, plan=plan
    )
    admission = verify_launch_admission_receipt_v42r3(
        launch_admission_receipt,
        formal_transport_plan=plan,
        launch_transport_attempt=attempt,
    )
    gate = _verify_cross_version_gate_document(
        cross_version_scientific_state_gate,
        formal_transport_plan=plan,
        operation="SERVICE_WRAPPER",
    )
    manager, _matches = _effect_manager_binding(
        manager_binding, plan=plan, require_match=True
    )
    bootstrap = admission["configured_exec_start_argv"]
    unit, wrapper = _loaded_unit_observation(
        unit_observation,
        plan=plan,
        attempt_id=attempt["local_launch_attempt_id"],
        manager=manager,
        service_bootstrap_argv=bootstrap,
    )
    if (
        type(service_pid) is not int
        or service_pid <= 1
        or service_pid != unit["MainPID"]
        or service_pid != admission["unit_main_pid"]
        or type(service_cgroup) is not str
        or service_cgroup != unit["ControlGroup"]
        or service_cgroup != admission["unit_control_group"]
        or unit["InvocationID"] != admission["unit_invocation_id"]
    ):
        _fail("formal service wrapper process or systemd identity changed")
    if (
        not isinstance(service_environment, Mapping)
        or dict(service_environment) != FORMAL_SERVICE_ENVIRONMENT
    ):
        _fail("formal service wrapper environment changed")
    stdio = _verify_stdio_facts(stdio_facts)
    if (
        type(live_file_descriptors) not in {list, tuple}
        or list(live_file_descriptors) != [0, 1, 2]
    ):
        _fail("formal service wrapper inherited an extra descriptor")
    tools = _verify_tools(live_tool_facts)
    if tools != plan["remote_tool_facts"]:
        _fail("formal service wrapper live tool facts changed")
    payload = {
        **_base(FORMAL_SERVICE_WRAPPER_ATTESTATION_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "formal_launch_transport_attempt_id": attempt[
            "formal_launch_transport_attempt_id"
        ],
        "formal_launch_admission_receipt_id": admission[
            "formal_launch_admission_receipt_id"
        ],
        "cross_version_scientific_state_gate_id": gate[
            "cross_version_scientific_state_gate_id"
        ],
        "prepare_receipt_id": attempt["prepare_receipt_id"],
        "local_launch_attempt_id": attempt["local_launch_attempt_id"],
        "unit_name": attempt["unit_name"],
        "unit_invocation_id": admission["unit_invocation_id"],
        "service_pid": service_pid,
        "service_cgroup": service_cgroup,
        "systemd_unit_observation": unit,
        "configured_exec_start_argv": list(bootstrap),
        "live_post_env_main_pid_argv": list(wrapper),
        "manager_binding": manager,
        "service_environment": dict(FORMAL_SERVICE_ENVIRONMENT),
        "stdio_facts": stdio,
        "exact_live_file_descriptors": [0, 1, 2],
        "remote_tool_facts": tools,
        "isolated_python_flags": ["-I", "-S", "-B"],
        "invocation_id_rejoined_to_systemd_unit": True,
        "service_cgroup_rejoined_to_systemd_unit": True,
        "all_three_stdio_descriptors_are_dev_null": True,
        "formal_runner_invocation_authorized": True,
        "formal_execution_performed": False,
    }
    return {
        **payload,
        "formal_service_wrapper_attestation_id": _content_id(
            FORMAL_SERVICE_WRAPPER_ATTESTATION_DOMAIN, payload
        ),
    }


_FORMAL_SERVICE_WRAPPER_ATTESTATION_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "global_execution_ordinal",
        "formal_transport_plan_id",
        "formal_launch_transport_attempt_id",
        "formal_launch_admission_receipt_id",
        "cross_version_scientific_state_gate_id",
        "prepare_receipt_id",
        "local_launch_attempt_id",
        "unit_name",
        "unit_invocation_id",
        "service_pid",
        "service_cgroup",
        "systemd_unit_observation",
        "configured_exec_start_argv",
        "live_post_env_main_pid_argv",
        "manager_binding",
        "service_environment",
        "stdio_facts",
        "exact_live_file_descriptors",
        "remote_tool_facts",
        "isolated_python_flags",
        "invocation_id_rejoined_to_systemd_unit",
        "service_cgroup_rejoined_to_systemd_unit",
        "all_three_stdio_descriptors_are_dev_null",
        "formal_runner_invocation_authorized",
        "formal_execution_performed",
        "formal_service_wrapper_attestation_id",
    }
)


def verify_service_wrapper_attestation_v42r3(
    value: bytes | Mapping[str, Any], *,
    formal_transport_plan: Mapping[str, Any],
    launch_transport_attempt: Mapping[str, Any] | None = None,
    launch_admission_receipt: Mapping[str, Any] | None = None,
    cross_version_scientific_state_gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    document = _canonical_document(value, "formal service wrapper attestation")
    if set(document) != _FORMAL_SERVICE_WRAPPER_ATTESTATION_FIELDS:
        _fail("formal service wrapper attestation field set changed")
    _verify_base(
        document,
        FORMAL_SERVICE_WRAPPER_ATTESTATION_SCHEMA,
        "formal service wrapper attestation",
    )
    local_id = _hex(
        document["local_launch_attempt_id"], 64, "wrapper local attempt ID"
    )
    for field in (
        "formal_launch_transport_attempt_id",
        "formal_launch_admission_receipt_id",
        "cross_version_scientific_state_gate_id",
        "prepare_receipt_id",
    ):
        _hex(document[field], 64, field)
    if launch_transport_attempt is not None:
        attempt = _verify_launch_transport_attempt_document(
            launch_transport_attempt, plan=plan
        )
        if any(
            document[field] != attempt[field]
            for field in (
                "formal_launch_transport_attempt_id",
                "prepare_receipt_id",
                "local_launch_attempt_id",
                "unit_name",
            )
        ):
            _fail("wrapper/launch attempt join changed")
    if launch_admission_receipt is not None:
        admission = verify_launch_admission_receipt_v42r3(
            launch_admission_receipt,
            formal_transport_plan=plan,
            launch_transport_attempt=launch_transport_attempt,
        )
        if (
            document["formal_launch_admission_receipt_id"]
            != admission["formal_launch_admission_receipt_id"]
            or document["unit_invocation_id"] != admission["unit_invocation_id"]
            or document["service_pid"] != admission["unit_main_pid"]
            or document["service_cgroup"] != admission["unit_control_group"]
        ):
            _fail("wrapper/admission receipt join changed")
    if cross_version_scientific_state_gate is not None:
        gate = _verify_cross_version_gate_document(
            cross_version_scientific_state_gate,
            formal_transport_plan=plan,
            operation="SERVICE_WRAPPER",
        )
        if (
            document["cross_version_scientific_state_gate_id"]
            != gate["cross_version_scientific_state_gate_id"]
        ):
            _fail("wrapper/cross-version gate join changed")
    manager, _matches = _effect_manager_binding(
        document["manager_binding"], plan=plan, require_match=True
    )
    unit, wrapper = _loaded_unit_observation(
        document["systemd_unit_observation"],
        plan=plan,
        attempt_id=local_id,
        manager=manager,
        service_bootstrap_argv=document["configured_exec_start_argv"],
    )
    stdio = _verify_stdio_facts(document["stdio_facts"])
    tools = _verify_tools(document["remote_tool_facts"])
    if (
        document["formal_transport_plan_id"] != plan["formal_transport_plan_id"]
        or document["unit_name"] != unit_name_v42r3(local_id)
        or document["unit_invocation_id"] != unit["InvocationID"]
        or document["service_pid"] != unit["MainPID"]
        or document["service_cgroup"] != unit["ControlGroup"]
        or document["live_post_env_main_pid_argv"] != list(wrapper)
        or document["service_environment"] != FORMAL_SERVICE_ENVIRONMENT
        or stdio != document["stdio_facts"]
        or document["exact_live_file_descriptors"] != [0, 1, 2]
        or tools != plan["remote_tool_facts"]
        or document["isolated_python_flags"] != ["-I", "-S", "-B"]
        or any(
            document[field] is not True
            for field in (
                "invocation_id_rejoined_to_systemd_unit",
                "service_cgroup_rejoined_to_systemd_unit",
                "all_three_stdio_descriptors_are_dev_null",
                "formal_runner_invocation_authorized",
            )
        )
        or document["formal_execution_performed"] is not False
    ):
        _fail("formal service wrapper attestation authority changed")
    _verify_claimed_id(
        document,
        field="formal_service_wrapper_attestation_id",
        domain=FORMAL_SERVICE_WRAPPER_ATTESTATION_DOMAIN,
        label="formal service wrapper attestation",
    )
    return document


_PREPARE_INSPECTION_ARTIFACTS = frozenset(
    {
        "scientific_prepare_receipt",
        "scientific_prepare_attempt",
        "scientific_prepare_failure",
        "formal_successor_journal",
    }
)
_LAUNCH_INSPECTION_ARTIFACTS = frozenset(
    {
        "formal_successor_journal",
        "launch_transport_attempt",
        "launch_admission_receipt",
        "service_wrapper_attestation",
        "scientific_launch_attempt",
        "scientific_launch_failure",
        "scientific_terminal",
    }
)


def _inspection_unit_observation(
    value: Mapping[str, Any], *, plan: Mapping[str, Any], attempt_id: str,
) -> dict[str, Any]:
    unit = _mapping(value, _UNIT_OBSERVATION_FIELDS, "inspected systemd unit")
    load_states = {"loaded", "not-found", "masked", "error"}
    active_states = {
        "active",
        "activating",
        "deactivating",
        "inactive",
        "failed",
        "unknown",
    }
    sub_states = {
        "start",
        "running",
        "exited",
        "dead",
        "failed",
        "auto-restart",
        "unknown",
    }
    if (
        unit["Id"] != unit_name_v42r3(attempt_id)
        or unit["LoadState"] not in load_states
        or unit["ActiveState"] not in active_states
        or unit["SubState"] not in sub_states
        or type(unit["Result"]) is not str
        or type(unit["MainPID"]) is not int
        or unit["MainPID"] < 0
        or type(unit["LiveMainPIDArgv"]) is not list
        or any(type(item) is not str for item in unit["LiveMainPIDArgv"])
        or type(unit["Environment"]) is not str
    ):
        _fail("inspected systemd unit state changed type or vocabulary")
    if unit["LoadState"] == "loaded":
        if (
            unit["Type"] != "exec"
            or unit["Restart"] != "no"
            or unit["RemainAfterExit"] != "yes"
            or unit["SuccessExitStatus"] != "2"
            or unit["UMask"] != "0077"
            or unit["KillMode"] != "mixed"
            or unit["TimeoutStopUSec"] != "30s"
            or unit["RuntimeMaxUSec"] != "1w 25min"
            or unit["StandardInput"] != "null"
            or unit["StandardOutput"] != "null"
            or unit["StandardError"] != "null"
            or unit["WorkingDirectory"] != plan["fixed_source_root"]
            or unit["Slice"] != SYSTEMD_SLICE
            or unit["FragmentPath"]
            != (
                f"/run/user/{authority.REMOTE_UID}/systemd/transient/"
                + unit_name_v42r3(attempt_id)
            )
            or unit["Environment"] != ""
        ):
            _fail("inspected loaded systemd service contract changed")
        if unit["InvocationID"]:
            _uuid(unit["InvocationID"], "inspected unit invocation ID")
        if unit["MainPID"] > 1:
            control_group = unit["ControlGroup"]
            if (
                not unit["InvocationID"]
                or type(control_group) is not str
                or _CGROUP.fullmatch(control_group) is None
                or not control_group.endswith("/" + unit_name_v42r3(attempt_id))
                or unit["LiveMainPIDArgvSource"] != "PROC_MAINPID_CMDLINE"
            ):
                _fail("inspected live systemd identity changed")
            live = list(unit["LiveMainPIDArgv"])
            if len(live) == 20 and live[6] == SERVICE_BOOTSTRAP_MODE:
                _verify_service_bootstrap_argv(
                    live, plan=plan, attempt_id=attempt_id
                )
            elif len(live) == 22 and live[6] == SERVICE_WRAPPER_MODE:
                if (
                    live[-2] != unit["InvocationID"]
                    or live[-1] != control_group
                ):
                    _fail("inspected wrapper runtime identity changed")
                bootstrap = live[:-2]
                bootstrap[6] = SERVICE_BOOTSTRAP_MODE
                _verify_service_bootstrap_argv(
                    bootstrap, plan=plan, attempt_id=attempt_id
                )
            else:
                _fail("inspected live systemd argv changed")
        elif (
            unit["LiveMainPIDArgv"]
            or unit["LiveMainPIDArgvSource"] != "UNAVAILABLE_NO_MAINPID"
        ):
            _fail("inspected exited service invented a live argv")
    elif (
        unit["LiveMainPIDArgv"]
        or unit["LiveMainPIDArgvSource"] != "ABSENT_UNIT"
        or unit["FragmentPath"] != ""
    ):
        _fail("inspected absent service invented a live argv or fragment")
    return unit


def build_read_only_inspection_v42r3(
    *, formal_transport_plan: Mapping[str, Any], operation: str,
    attempt_id: str, inspection_ordinal: int,
    manager_binding: Mapping[str, Any],
    unit_observation: Mapping[str, Any] | None,
    artifact_states: Mapping[str, str],
    recovered_documents: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    if operation not in OPERATIONS:
        _fail("read-only inspection operation changed")
    attempt = _hex(attempt_id, 64, "inspection attempt ID")
    if type(inspection_ordinal) is not int or inspection_ordinal < 1:
        _fail("read-only inspection ordinal changed")
    manager, matches = _effect_manager_binding(
        manager_binding, plan=plan, require_match=False
    )
    expected_states = (
        _PREPARE_INSPECTION_ARTIFACTS
        if operation == OPERATION_PREPARE
        else _LAUNCH_INSPECTION_ARTIFACTS
    )
    states = _mapping(
        artifact_states, expected_states, "read-only inspection artifact states"
    )
    if any(value not in ARTIFACT_STATES for value in states.values()):
        _fail("read-only inspection artifact state vocabulary changed")
    if not isinstance(recovered_documents, Mapping):
        _fail("read-only inspection recovered documents changed type")
    recovered = _canonical_document(
        recovered_documents, "read-only inspection recovered documents"
    )
    allowed_recovered = (
        {"scientific_prepare_receipt"}
        if operation == OPERATION_PREPARE
        else {
            "launch_transport_attempt",
            "launch_admission_receipt",
            "service_wrapper_attestation",
        }
    )
    if not set(recovered) <= allowed_recovered or any(
        type(value) is not dict for value in recovered.values()
    ):
        _fail("read-only inspection recovered document inventory changed")
    if "scientific_prepare_receipt" in recovered:
        if states["scientific_prepare_receipt"] != "REGULAR_FILE":
            _fail("inspection recovered a nonregular scientific prepare receipt")
        _legacy_prepare_projection(recovered["scientific_prepare_receipt"], plan)
    if "launch_transport_attempt" in recovered:
        if states["launch_transport_attempt"] != "REGULAR_FILE":
            _fail("inspection recovered a nonregular launch transport attempt")
        launch_attempt = _verify_launch_transport_attempt_document(
            recovered["launch_transport_attempt"], plan=plan
        )
    else:
        launch_attempt = None
    if "launch_admission_receipt" in recovered:
        if states["launch_admission_receipt"] != "REGULAR_FILE":
            _fail("inspection recovered a nonregular launch admission receipt")
        if launch_attempt is None:
            _fail("inspection admission omitted its recovered launch attempt")
        admission = verify_launch_admission_receipt_v42r3(
            recovered["launch_admission_receipt"],
            formal_transport_plan=plan,
            launch_transport_attempt=launch_attempt,
        )
    else:
        admission = None
    if "service_wrapper_attestation" in recovered:
        if states["service_wrapper_attestation"] != "REGULAR_FILE":
            _fail("inspection recovered a nonregular service wrapper attestation")
        if launch_attempt is None or admission is None:
            _fail("inspection wrapper omitted its recovered authority chain")
        wrapper_gate = verify_cross_version_scientific_state_gate_v42r3(
            formal_transport_plan=plan,
            operation="SERVICE_WRAPPER",
            legacy_scientific_phase={"phase": "POST_PREPARE_PRELAUNCH"},
            effect_authorized=True,
        )
        verify_service_wrapper_attestation_v42r3(
            recovered["service_wrapper_attestation"],
            formal_transport_plan=plan,
            launch_transport_attempt=launch_attempt,
            launch_admission_receipt=admission,
            cross_version_scientific_state_gate=wrapper_gate,
        )
    if operation == OPERATION_LAUNCH and any(
        (states[name] == "REGULAR_FILE") != (name in recovered)
        for name in (
            "launch_transport_attempt",
            "launch_admission_receipt",
            "service_wrapper_attestation",
        )
    ):
        _fail("inspection left a persisted formal authority document unverified")
    if operation == OPERATION_LAUNCH:
        if unit_observation is None:
            _fail("launch inspection omitted the systemd unit observation")
        unit = _inspection_unit_observation(
            unit_observation, plan=plan, attempt_id=attempt
        )
        if (
            admission is not None
            and unit["LoadState"] == "loaded"
            and unit["MainPID"] > 1
            and (
                unit["InvocationID"] != admission["unit_invocation_id"]
                or unit["MainPID"] != admission["unit_main_pid"]
                or unit["ControlGroup"] != admission["unit_control_group"]
            )
        ):
            _fail("inspection live unit differs from recovered admission")
    elif unit_observation is not None:
        _fail("prepare inspection unexpectedly included a systemd unit")
    else:
        unit = None
    normalized_manager = {**manager, "matches_host_epoch": matches}
    payload = {
        **_base(FORMAL_READ_ONLY_INSPECTION_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "operation": operation,
        "attempt_id": attempt,
        "inspection_ordinal": inspection_ordinal,
        "manager_binding": normalized_manager,
        "unit_observation": unit,
        "artifact_states": states,
        "recovered_documents": recovered,
        "authenticated_loader_and_receiver_remote_mutation_performed": False,
        (
            "authenticated_loader_and_receiver_systemd_lifecycle_mutation_"
            "performed"
        ): False,
        "authenticated_controller_same_effect_reissued": False,
        "end_to_end_remote_mutation_absence_claimed": False,
        "end_to_end_systemd_mutation_absence_claimed": False,
    }
    return {
        **payload,
        "formal_read_only_inspection_id": _content_id(
            FORMAL_READ_ONLY_INSPECTION_DOMAIN, payload
        ),
    }


_FORMAL_READ_ONLY_INSPECTION_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "global_execution_ordinal",
        "formal_transport_plan_id",
        "operation",
        "attempt_id",
        "inspection_ordinal",
        "manager_binding",
        "unit_observation",
        "artifact_states",
        "recovered_documents",
        "authenticated_loader_and_receiver_remote_mutation_performed",
        (
            "authenticated_loader_and_receiver_systemd_lifecycle_mutation_"
            "performed"
        ),
        "authenticated_controller_same_effect_reissued",
        "end_to_end_remote_mutation_absence_claimed",
        "end_to_end_systemd_mutation_absence_claimed",
        "formal_read_only_inspection_id",
    }
)


def verify_read_only_inspection_v42r3(
    value: bytes | Mapping[str, Any], *,
    formal_transport_plan: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "formal read-only inspection")
    if set(document) != _FORMAL_READ_ONLY_INSPECTION_FIELDS:
        _fail("formal read-only inspection field set changed")
    manager = document.get("manager_binding")
    if not isinstance(manager, Mapping) or set(manager) != _MANAGER_FIELDS | {
        "matches_host_epoch"
    }:
        _fail("formal inspection manager binding field set changed")
    raw_manager = {
        field: manager[field] for field in _MANAGER_FIELDS
    }
    expected = build_read_only_inspection_v42r3(
        formal_transport_plan=formal_transport_plan,
        operation=document.get("operation"),
        attempt_id=document.get("attempt_id"),
        inspection_ordinal=document.get("inspection_ordinal"),
        manager_binding=raw_manager,
        unit_observation=document.get("unit_observation"),
        artifact_states=document.get("artifact_states"),
        recovered_documents=document.get("recovered_documents"),
    )
    if document != expected:
        _fail("formal read-only inspection changed")
    return document


def build_network_start_v42r3(
    *, formal_transport_plan: Mapping[str, Any], operation: str,
    attempt_id: str,
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    if operation not in OPERATIONS:
        _fail("formal network-start operation changed")
    attempt = _hex(attempt_id, 64, "formal network-start attempt ID")
    payload = {
        **_base(FORMAL_NETWORK_START_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "operation": operation,
        "attempt_id": attempt,
        "network_effect_may_have_started": True,
        (
            "published_o_excl_nofollow_mode_0400_and_fsynced_before_"
            "authorized_dispatch"
        ): True,
        "controller_same_effect_dispatch_replay_forbidden": True,
        (
            "controller_authorizes_only_authenticated_inspection_after_"
            "publication"
        ): True,
    }
    return {
        **payload,
        "formal_network_start_id": _content_id(
            FORMAL_NETWORK_START_DOMAIN, payload
        ),
    }


def verify_network_start_v42r3(
    value: bytes | Mapping[str, Any], *,
    formal_transport_plan: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(value, "formal network-start marker")
    expected = build_network_start_v42r3(
        formal_transport_plan=formal_transport_plan,
        operation=document.get("operation"),
        attempt_id=document.get("attempt_id"),
    )
    if document != expected:
        _fail("formal network-start marker changed")
    return document


def build_operation_outcome_v42r3(
    *, formal_transport_plan: Mapping[str, Any], operation: str,
    attempt_id: str, outcome_class: str, receipt_raw: bytes | None,
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    if operation not in OPERATIONS or outcome_class not in OUTCOME_CLASSES:
        _fail("formal operation outcome class changed")
    attempt = _hex(attempt_id, 64, "formal operation attempt ID")
    if outcome_class == OUTCOME_COMPLETE_EXACT_RECEIPT:
        if type(receipt_raw) is not bytes or not 0 < len(receipt_raw) <= 64 * 1024**2:
            _fail("complete formal operation omitted its bounded exact receipt")
        receipt_fact: dict[str, Any] | None = {
            "byte_count": len(receipt_raw),
            "sha256": hashlib.sha256(receipt_raw).hexdigest(),
        }
    elif receipt_raw is not None:
        _fail("noncomplete formal operation cannot claim a receipt")
    else:
        receipt_fact = None
    marker_present = outcome_class != OUTCOME_PRE_NETWORK_FAILURE
    payload = {
        **_base(FORMAL_OPERATION_OUTCOME_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "operation": operation,
        "attempt_id": attempt,
        "outcome_class": outcome_class,
        "network_start_marker_present": marker_present,
        "receipt_fact": receipt_fact,
        "controller_same_effect_dispatch_replay_allowed": not marker_present,
        (
            "controller_authorizes_only_authenticated_read_only_inspection_"
            "after_marker"
        ): marker_present,
    }
    return {
        **payload,
        "formal_operation_outcome_id": _content_id(
            FORMAL_OPERATION_OUTCOME_DOMAIN, payload
        ),
    }


_FORMAL_OPERATION_OUTCOME_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "global_execution_ordinal",
        "formal_transport_plan_id",
        "operation",
        "attempt_id",
        "outcome_class",
        "network_start_marker_present",
        "receipt_fact",
        "controller_same_effect_dispatch_replay_allowed",
        (
            "controller_authorizes_only_authenticated_read_only_inspection_"
            "after_marker"
        ),
        "formal_operation_outcome_id",
    }
)


def verify_operation_outcome_v42r3(
    value: bytes | Mapping[str, Any], *,
    formal_transport_plan: Mapping[str, Any],
    operation: str | None = None, attempt_id: str | None = None,
    receipt_raw: bytes | None = None,
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    document = _canonical_document(value, "formal operation outcome")
    if set(document) != _FORMAL_OPERATION_OUTCOME_FIELDS:
        _fail("formal operation outcome field set changed")
    _verify_base(
        document, FORMAL_OPERATION_OUTCOME_SCHEMA, "formal operation outcome"
    )
    if (
        document["formal_transport_plan_id"] != plan["formal_transport_plan_id"]
        or document["operation"] not in OPERATIONS
        or operation is not None and document["operation"] != operation
        or document["outcome_class"] not in OUTCOME_CLASSES
        or attempt_id is not None and document["attempt_id"] != attempt_id
    ):
        _fail("formal operation outcome join changed")
    _hex(document["attempt_id"], 64, "formal operation outcome attempt ID")
    marker = document["outcome_class"] != OUTCOME_PRE_NETWORK_FAILURE
    fact = document["receipt_fact"]
    if document["outcome_class"] == OUTCOME_COMPLETE_EXACT_RECEIPT:
        receipt = _mapping(
            fact,
            frozenset({"byte_count", "sha256"}),
            "formal outcome receipt fact",
        )
        if (
            type(receipt["byte_count"]) is not int
            or not 0 < receipt["byte_count"] <= 64 * 1024**2
        ):
            _fail("formal outcome receipt byte count changed")
        _hex(receipt["sha256"], 64, "formal outcome receipt SHA256")
        if receipt_raw is not None and receipt != {
            "byte_count": len(receipt_raw),
            "sha256": hashlib.sha256(receipt_raw).hexdigest(),
        }:
            _fail("formal outcome exact receipt bytes changed")
    elif fact is not None or receipt_raw is not None:
        _fail("noncomplete formal outcome invented exact receipt bytes")
    if (
        document["network_start_marker_present"] is not marker
        or document["controller_same_effect_dispatch_replay_allowed"] is marker
        or document[
            "controller_authorizes_only_authenticated_read_only_inspection_"
            "after_marker"
        ] is not marker
    ):
        _fail("formal operation outcome replay semantics changed")
    _verify_claimed_id(
        document,
        field="formal_operation_outcome_id",
        domain=FORMAL_OPERATION_OUTCOME_DOMAIN,
        label="formal operation outcome",
    )
    return document


def classify_formal_operation_v42r3(
    *, formal_transport_plan: Mapping[str, Any], operation: str,
    attempt_id: str, marker_present: bool, exact_receipt_present: bool,
    inspection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    plan = verify_formal_transport_plan_v42r3(formal_transport_plan)
    if (
        operation not in OPERATIONS
        or type(marker_present) is not bool
        or type(exact_receipt_present) is not bool
    ):
        _fail("formal classifier inputs changed")
    attempt = _hex(attempt_id, 64, "formal classification attempt ID")
    reasons: list[str] = []
    if not marker_present:
        if exact_receipt_present or inspection is not None:
            _fail("pre-marker state cannot contain receipt or inspection evidence")
        classification = CLASS_PRE_NETWORK_RETRYABLE
        replay = True
    elif inspection is None:
        if exact_receipt_present:
            classification = (
                CLASS_PREPARE_COMPLETE
                if operation == OPERATION_PREPARE
                else CLASS_LAUNCH_ADMITTED
            )
        else:
            classification = CLASS_AMBIGUOUS
            reasons.append("MARKER_WITHOUT_EXACT_RECEIPT")
        replay = False
    else:
        checked = verify_read_only_inspection_v42r3(
            inspection, formal_transport_plan=plan
        )
        if (
            checked["operation"] != operation
            or checked["attempt_id"] != attempt
            or not marker_present
        ):
            _fail("formal classifier inspection join changed")
        states = checked["artifact_states"]
        if checked["manager_binding"]["matches_host_epoch"] is not True:
            classification = CLASS_AMBIGUOUS
            reasons.append("BOOT_OR_USER_MANAGER_DRIFT")
        elif any(
            value == "NONREGULAR"
            or value == "DIRECTORY" and name != "formal_successor_journal"
            or value == "REGULAR_FILE" and name == "formal_successor_journal"
            for name, value in states.items()
        ):
            classification = CLASS_AMBIGUOUS
            reasons.append("NONREGULAR_REMOTE_ARTIFACT")
        elif operation == OPERATION_PREPARE:
            if (
                states["scientific_prepare_receipt"] == "REGULAR_FILE"
                and "scientific_prepare_receipt"
                in checked["recovered_documents"]
                and states["scientific_prepare_attempt"] == "REGULAR_FILE"
                and states["scientific_prepare_failure"] == "ABSENT"
            ):
                classification = CLASS_PREPARE_COMPLETE
            else:
                classification = CLASS_AMBIGUOUS
                reasons.append(
                    "UNAUTHENTICATED_SCIENTIFIC_TERMINAL"
                    if states["scientific_prepare_failure"] == "REGULAR_FILE"
                    else "PREPARE_TERMINAL_NOT_EXACT"
                )
        else:
            unit = checked["unit_observation"]
            if (
                states["formal_successor_journal"] == "DIRECTORY"
                and states["launch_transport_attempt"] == "REGULAR_FILE"
                and "launch_transport_attempt" in checked["recovered_documents"]
                and states["launch_admission_receipt"] == "REGULAR_FILE"
                and "launch_admission_receipt" in checked["recovered_documents"]
                and states["scientific_terminal"] == "ABSENT"
                and states["scientific_launch_failure"] == "ABSENT"
                and unit["LoadState"] == "loaded"
                and unit["ActiveState"] in {"active", "activating"}
                and unit["SubState"] in {"start", "running"}
            ):
                classification = CLASS_IN_PROGRESS
            else:
                classification = CLASS_AMBIGUOUS
                reasons.append(
                    "UNAUTHENTICATED_SCIENTIFIC_TERMINAL"
                    if states["scientific_terminal"] == "REGULAR_FILE"
                    or states["scientific_launch_failure"] == "REGULAR_FILE"
                    else "LAUNCH_STATE_NOT_EXACT_OR_SUPERVISION_LOST"
                )
        replay = False
    payload = {
        **_base(FORMAL_CLASSIFICATION_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "operation": operation,
        "attempt_id": attempt,
        "network_start_marker_present": marker_present,
        "exact_transport_receipt_present": exact_receipt_present,
        "classification": classification,
        "reason_codes": reasons,
        "controller_same_effect_dispatch_replay_allowed": replay,
        (
            "controller_authorizes_only_authenticated_read_only_inspection_"
            "after_marker"
        ): marker_present,
        "unit_absence_used_as_never_started_proof": False,
    }
    return {
        **payload,
        "formal_transport_classification_id": _content_id(
            FORMAL_CLASSIFICATION_DOMAIN, payload
        ),
    }


# Compatibility spelling for callers retaining the old self-contained name.
verify_operation_outcome_self_contained_v42r3 = verify_operation_outcome_v42r3
