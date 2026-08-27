"""Pure authority for V42 ordinal-2 materialization activation.

The pre-formal uploader leaves one exact five-control scratch directory and
one empty ledger-stage directory beside the still-absent formal root.  This
module selects that receipt, gates the selected host without mutating it, and
defines the one-shot activation chain.  It deliberately performs no I/O.

The irreversible filesystem protocol is:

``ledger-stage/ATTEMPT -> fixed-ledger`` (RENAME_NOREPLACE), then a durable
systemd service writes ``SERVICE_RECEIPT`` and ``PUBLISH_READY`` before the
service atomically renames the already-verified scratch directory to the
fixed five-control root.  Only a durable terminal plus the exact fixed root
authorizes the existing trusted bootstrap launcher.
"""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import re
import shlex
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_materialization_transport_v42r1 as preformal,
)
from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = authority.SCHEMA_VERSION
DOMAIN_PREFIX = "acfqp:v42-remote-ordinal2:"

PREACTIVATION_RESOURCE_PROBE_PLAN_SCHEMA = (
    "acfqp.v42_remote_ordinal2_preactivation_resource_probe_plan.v42r1"
)
PREACTIVATION_RESOURCE_RESULT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_preactivation_resource_result.v42r1"
)
MATERIALIZATION_ACTIVATION_PLAN_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_activation_plan.v42r1"
)
LOCAL_MATERIALIZATION_ACTIVATION_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_local_materialization_activation_attempt.v42r1"
)
MATERIALIZATION_ACTIVATION_NETWORK_START_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_activation_network_start.v42r1"
)
LOCAL_MATERIALIZATION_ACTIVATION_RECEIPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_local_materialization_activation_receipt.v42r1"
)
LOCAL_MATERIALIZATION_ACTIVATION_AMBIGUITY_SCHEMA = (
    "acfqp.v42_remote_ordinal2_local_materialization_activation_ambiguity.v42r1"
)
REMOTE_MATERIALIZATION_ACTIVATION_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_remote_materialization_activation_attempt.v42r1"
)
REMOTE_ACTIVATION_SERVICE_RECEIPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_activation_service_receipt.v42r1"
)
REMOTE_ACTIVATION_PUBLISH_READY_SCHEMA = (
    "acfqp.v42_remote_ordinal2_activation_publish_ready.v42r1"
)
REMOTE_MATERIALIZATION_TRANSPORT_TERMINAL_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_transport_terminal.v42r1"
)
REMOTE_MATERIALIZATION_ACTIVATION_FAILURE_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_activation_failure.v42r1"
)
MATERIALIZATION_ACTIVATION_CLASSIFICATION_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_activation_classification.v42r1"
)

LOCAL_ACTIVATION_CONTROL_ROOT_RELATIVE = (
    ".tmp/exact-freeze/v42-standard-2048-remote-ordinal2-activation-control"
)
LOCAL_ACTIVATION_PLAN_NAME = "MATERIALIZATION_ACTIVATION_PLAN.json"
LOCAL_ACTIVATION_ATTEMPT_NAME = "LOCAL_MATERIALIZATION_ACTIVATION_ATTEMPT.json"
LOCAL_ACTIVATION_NETWORK_START_NAME = "MATERIALIZATION_ACTIVATION_NETWORK_START.json"
LOCAL_ACTIVATION_RECEIPT_NAME = "MATERIALIZATION_ACTIVATION_RECEIPT.json"
LOCAL_ACTIVATION_AMBIGUITY_NAME = "MATERIALIZATION_ACTIVATION_AMBIGUITY.json"

REMOTE_ACTIVATION_ATTEMPT_NAME = "REMOTE_MATERIALIZATION_ACTIVATION_ATTEMPT.json"
REMOTE_ACTIVATION_SERVICE_SOURCE_NAME = "MATERIALIZATION_ACTIVATION_SERVICE.py"
REMOTE_ACTIVATION_SERVICE_RECEIPT_NAME = "REMOTE_ACTIVATION_SERVICE_RECEIPT.json"
REMOTE_ACTIVATION_READY_NAME = "REMOTE_ACTIVATION_PUBLISH_READY.json"
REMOTE_ACTIVATION_TERMINAL_NAME = "REMOTE_MATERIALIZATION_TRANSPORT_TERMINAL.json"
REMOTE_ACTIVATION_FAILURE_NAME = "REMOTE_MATERIALIZATION_ACTIVATION_FAILURE.json"

ACTIVATION_PLAN_ID_SENTINEL = "{acfqp_v42_materialization_activation_plan_id}"
RESOURCE_PROBE_PLAN_ID_SENTINEL = "{acfqp_v42_preactivation_resource_probe_plan_id}"
LOCAL_ACTIVATION_ATTEMPT_ID_SENTINEL = (
    "{acfqp_v42_local_materialization_activation_attempt_id}"
)
REMOTE_ACTIVATION_ATTEMPT_ID_SENTINEL = (
    "{acfqp_v42_remote_materialization_activation_attempt_id}"
)
REMOTE_TRANSPORT_TERMINAL_ID_SENTINEL = (
    "{acfqp_v42_remote_materialization_transport_terminal_id}"
)
SYSTEMD_INVOCATION_ID_SENTINEL = "{acfqp_v42_systemd_invocation_id}"
SYSTEMD_CONTROL_GROUP_SENTINEL = "{acfqp_v42_systemd_control_group}"

SYSTEMD_RUN = "/usr/bin/systemd-run"
SYSTEMD_RUN_SHA256 = (
    "dbc8b988a849d5c9d7ef2de7068a6f107021bc6c11e0d7864c73f373eef726a7"
)
SYSTEMD_RUN_BYTE_COUNT = 68_392
SYSTEMCTL = "/usr/bin/systemctl"
SYSTEMCTL_SHA256 = (
    "e0d3d0e9444da1b2b58c792c3f5028b69f049b77d5ca17b3ec0d09f89117225b"
)
SYSTEMCTL_BYTE_COUNT = 1_501_304
SYSTEMD_EXECUTABLE_MODE = 0o755
SYSTEMD_EXECUTABLE_UID = 0
SYSTEMD_EXECUTABLE_GID = 0
SYSTEMD_EXECUTABLE_NLINK = 1
SYSTEMD_RUNTIME_MAX_SECONDS = 7 * 24 * 60 * 60
SYSTEMD_UNIT_PREFIX = "acfqp-v42-o2-activation-"
SYSTEMD_CLIENT_ENVIRONMENT = {
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "LC_ALL": "C.UTF-8",
    "XDG_RUNTIME_DIR": "/run/user/1000",
}
SYSTEMD_SERVICE_ENVIRONMENT = {"LC_ALL": "C.UTF-8"}

MINIMUM_MEMORY_TOTAL_BYTES = authority.MINIMUM_MEMORY_TOTAL_BYTES
MINIMUM_MEMORY_AVAILABLE_BYTES = authority.MINIMUM_MEMORY_AVAILABLE_BYTES
MINIMUM_SWAP_FREE_BYTES = authority.MINIMUM_SWAP_FREE_BYTES
MINIMUM_FILESYSTEM_AVAILABLE_BYTES = authority.MINIMUM_FILESYSTEM_AVAILABLE_BYTES

RESOURCE_STAGES = ("READ_ONLY_PREACTIVATION_PROBE", "SYSTEMD_SERVICE_PREPUBLISH")
UNIT_STATES = ("ACTIVE", "ACTIVATING", "FAILED", "INACTIVE", "NOT_FOUND", "UNOBSERVABLE")
PATH_STATES = ("ABSENT", "EXACT_DIRECTORY", "PARTIAL", "NONREGULAR", "UNOBSERVABLE")

CLASSIFICATION_AMBIGUOUS = "AMBIGUOUS_PERMANENTLY_CLOSED"
CLASSIFICATION_IN_PROGRESS = "IN_PROGRESS_READ_ONLY_WAIT"
CLASSIFICATION_FAILURE = "COMPLETE_ACTIVATION_FAILURE"
CLASSIFICATION_SUCCESS = "COMPLETE_TRANSPORT_SUCCESS"

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")


class V42MaterializationActivationError(RuntimeError):
    """An activation authority document or DAG edge changed."""


def _fail(message: str) -> NoReturn:
    raise V42MaterializationActivationError(message)


def _content_id(domain: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\0" + canonical_json_bytes(payload)
    ).hexdigest()


def _canonical_document(value: bytes | dict[str, Any], label: str) -> dict[str, Any]:
    if type(value) is bytes:
        try:
            result = loads_canonical_json(value)
        except (TypeError, ValueError, UnicodeError) as error:
            raise V42MaterializationActivationError(
                f"{label} is not canonical JSON"
            ) from error
        if canonical_json_bytes(result) != value:
            _fail(f"{label} bytes are not canonical")
    elif type(value) is dict:
        try:
            result = loads_canonical_json(canonical_json_bytes(value))
        except (TypeError, ValueError, UnicodeError) as error:
            raise V42MaterializationActivationError(
                f"{label} is not canonical JSON"
            ) from error
    else:
        _fail(f"{label} changed type")
    if type(result) is not dict:
        _fail(f"{label} is not an object")
    return result


def _hex40(value: Any, label: str) -> str:
    if type(value) is not str or _HEX40.fullmatch(value) is None:
        _fail(f"{label} is not lowercase 40-hex")
    return value


def _hex64(value: Any, label: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        _fail(f"{label} is not lowercase 64-hex")
    return value


def _exact_keys(document: dict[str, Any], keys: set[str], label: str) -> None:
    if set(document) != keys:
        _fail(f"{label} schema changed")


def _artifact(raw: bytes, relative_path: str, *, cap: int) -> dict[str, Any]:
    if type(raw) is not bytes or not 0 < len(raw) <= cap:
        _fail("activation program artifact changed type or exceeded cap")
    if type(relative_path) is not str or not relative_path or relative_path.startswith("/"):
        _fail("activation program relative path changed")
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_oid": hashlib.sha1(  # noqa: S324 - Git object identity
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest(),
        "git_mode": "100644",
        "git_object_type": "blob",
        "file_mode": "0444",
        "committed_regular_file_required": True,
    }


def _selected_preformal_chain(
    *,
    preformal_plan: dict[str, Any],
    preformal_attempt: dict[str, Any],
    preformal_receipt: dict[str, Any],
    preformal_outcome: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    plan = preformal.verify_preformal_upload_plan_v42r1(preformal_plan)
    attempt = preformal.verify_preformal_upload_attempt_v42r1(
        preformal_attempt, plan=plan
    )
    receipt = preformal.verify_preformal_upload_receipt_v42r1(
        preformal_receipt, plan=plan, attempt=attempt
    )
    outcome = preformal.verify_preformal_upload_outcome_v42r1(
        preformal_outcome, plan=plan, attempt=attempt, receipt=receipt
    )
    if outcome["outcome_class"] != preformal.PREFORMAL_OUTCOME_COMPLETE:
        _fail("formal activation requires one complete pre-formal outcome")
    if outcome["preformal_upload_receipt_id"] != receipt["preformal_upload_receipt_id"]:
        _fail("pre-formal receipt/outcome join changed")
    if receipt["fixed_remote_root_effect_performed"] is not False:
        _fail("selected pre-formal receipt already claims a formal effect")
    return plan, attempt, receipt, outcome


def _resource_checks(
    *,
    memory_total_bytes: int,
    memory_available_bytes: int,
    swap_total_bytes: int,
    swap_free_bytes: int,
    filesystem_available_bytes: int,
    cgroup_memory_ancestry: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, bool]]:
    values = (
        memory_total_bytes,
        memory_available_bytes,
        swap_total_bytes,
        swap_free_bytes,
        filesystem_available_bytes,
    )
    if any(type(value) is not int or value < 0 for value in values):
        _fail("resource observation integer changed")
    if type(cgroup_memory_ancestry) is not list or not cgroup_memory_ancestry:
        _fail("cgroup ancestry changed type or is empty")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(cgroup_memory_ancestry):
        if type(row) is not dict or set(row) != {
            "cgroup_path", "memory_max_mode", "memory_max_bytes", "memory_current_bytes"
        }:
            _fail("cgroup ancestry row schema changed")
        path = row.get("cgroup_path")
        mode = row.get("memory_max_mode")
        maximum = row.get("memory_max_bytes")
        current = row.get("memory_current_bytes")
        if (
            type(path) is not str
            or not path.startswith("/")
            or path.startswith("//")
            or PurePosixPath(path).as_posix() != path
            or ".." in path.split("/")
        ):
            _fail("cgroup ancestry path changed")
        if normalized:
            previous = PurePosixPath(normalized[-1]["cgroup_path"])
            if previous == PurePosixPath("/") or PurePosixPath(path) != previous.parent:
                _fail("cgroup ancestry is not an exact parent chain")
        if mode == "MAX":
            valid = maximum is None and type(current) is int and current >= 0
        elif mode == "FINITE":
            valid = type(maximum) is int and maximum > 0 and type(current) is int and current >= 0
        elif mode == "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES":
            valid = index == len(cgroup_memory_ancestry) - 1 and path == "/" and maximum is None and current is None
        else:
            valid = False
        if not valid:
            _fail("cgroup ancestry semantics changed")
        normalized.append(dict(row))
    if normalized[-1]["cgroup_path"] != "/":
        _fail("cgroup ancestry omitted the root")
    finite = [row for row in normalized if row["memory_max_mode"] == "FINITE"]
    checks = {
        "memory_total_gate": memory_total_bytes >= MINIMUM_MEMORY_TOTAL_BYTES,
        "memory_available_gate": memory_available_bytes >= MINIMUM_MEMORY_AVAILABLE_BYTES,
        "memory_observation_consistent": memory_available_bytes <= memory_total_bytes,
        "swap_gate": swap_total_bytes == 0 or swap_free_bytes >= MINIMUM_SWAP_FREE_BYTES,
        "swap_observation_consistent": swap_free_bytes <= swap_total_bytes and (swap_total_bytes != 0 or swap_free_bytes == 0),
        "filesystem_available_gate": filesystem_available_bytes >= MINIMUM_FILESYSTEM_AVAILABLE_BYTES,
        "cgroup_memory_gate": all(
            row["memory_max_bytes"] >= MINIMUM_MEMORY_TOTAL_BYTES
            and row["memory_max_bytes"] - row["memory_current_bytes"] >= MINIMUM_MEMORY_AVAILABLE_BYTES
            for row in finite
        ),
        "cgroup_ancestry_reaches_root": normalized[-1]["cgroup_path"] == "/",
    }
    return normalized, checks


def _base_payload(schema: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
    }


def _transient_identity(
    value: object,
    *,
    path: str,
    node_type: str,
    mode: int,
    uid: int,
    gid: int,
    label: str,
    regular_size: int | None = None,
) -> dict[str, Any]:
    fields = {
        "path",
        "node_type",
        "st_dev",
        "st_ino",
        "mode",
        "uid",
        "gid",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    }
    if type(value) is not dict or set(value) != fields:
        _fail(f"{label} transient identity schema changed")
    if (
        value.get("path") != path
        or value.get("node_type") != node_type
        or value.get("mode") != mode
        or value.get("uid") != uid
        or value.get("gid") != gid
    ):
        _fail(f"{label} transient identity changed")
    for field in (
        "st_dev",
        "st_ino",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    ):
        if type(value.get(field)) is not int or value[field] < 0:
            _fail(f"{label} transient {field} changed")
    if node_type == "REGULAR_FILE":
        if value["st_nlink"] != 1 or value["st_size"] != regular_size:
            _fail(f"{label} regular-file identity changed")
    elif value["st_nlink"] < 1:
        _fail(f"{label} directory link count changed")
    return dict(value)


def build_selected_remote_snapshot_v42r1(
    *,
    preformal_receipt: dict[str, Any],
    parent_identity: dict[str, Any],
    scratch_identity: dict[str, Any],
    ledger_stage_identity: dict[str, Any],
    control_identities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize one pinned whole-tree observation of the selected receipt."""

    receipt = _canonical_document(preformal_receipt, "pre-formal receipt")
    parent_fact = receipt.get("scratch_parent_fact")
    scratch_fact = receipt.get("scratch_root_fact")
    ledger_fact = receipt.get("ledger_stage_fact")
    files = receipt.get("observed_control_file_facts")
    if (
        type(parent_fact) is not dict
        or type(scratch_fact) is not dict
        or type(ledger_fact) is not dict
        or type(files) is not list
    ):
        _fail("selected receipt omitted exact filesystem facts")
    normalized_parent = _transient_identity(
        parent_identity,
        path=parent_fact["path"],
        node_type="DIRECTORY",
        mode=parent_fact["mode"],
        uid=parent_fact["uid"],
        gid=parent_fact["gid"],
        label="shared parent",
    )
    normalized_scratch = _transient_identity(
        scratch_identity,
        path=scratch_fact["path"],
        node_type="DIRECTORY",
        mode=0o700,
        uid=scratch_fact["uid"],
        gid=scratch_fact["gid"],
        label="selected scratch",
    )
    normalized_ledger = _transient_identity(
        ledger_stage_identity,
        path=ledger_fact["path"],
        node_type="DIRECTORY",
        mode=0o700,
        uid=ledger_fact["uid"],
        gid=ledger_fact["gid"],
        label="selected ledger stage",
    )
    if type(control_identities) is not list or len(control_identities) != len(files):
        _fail("selected control identity inventory changed")
    normalized_controls: list[dict[str, Any]] = []
    for expected, observed in zip(files, control_identities, strict=True):
        if type(expected) is not dict:
            _fail("selected receipt control fact changed type")
        normalized_controls.append(
            {
                "name": expected["name"],
                "identity": _transient_identity(
                    observed,
                    path=expected["path"],
                    node_type="REGULAR_FILE",
                    mode=0o400,
                    uid=expected["uid"],
                    gid=expected["gid"],
                    regular_size=expected["byte_count"],
                    label=f"selected control {expected['name']}",
                ),
                "sha256": expected["sha256"],
                "byte_count": expected["byte_count"],
            }
        )
    if [row["name"] for row in normalized_controls] != list(preformal.CONTROL_NAMES):
        _fail("selected controls are not in canonical order")
    return {
        "shared_parent_identity": normalized_parent,
        "scratch_root_identity": normalized_scratch,
        "ledger_stage_identity": normalized_ledger,
        "control_identities": normalized_controls,
        "scratch_inventory": list(preformal.CONTROL_NAMES),
        "ledger_stage_inventory": [],
        "fixed_remote_root_state": "ABSENT",
        "fixed_transport_ledger_state": "ABSENT",
        "all_paths_observed_nofollow_from_pinned_parent": True,
        "all_file_bytes_hashed_from_pinned_descriptors": True,
        "whole_tree_first_last_snapshot_equal": True,
    }


def verify_selected_remote_snapshot_v42r1(
    value: object, *, preformal_receipt: dict[str, Any]
) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("selected remote snapshot changed type")
    controls = value.get("control_identities")
    expected = build_selected_remote_snapshot_v42r1(
        preformal_receipt=preformal_receipt,
        parent_identity=value.get("shared_parent_identity"),
        scratch_identity=value.get("scratch_root_identity"),
        ledger_stage_identity=value.get("ledger_stage_identity"),
        control_identities=(
            [row.get("identity") for row in controls]
            if type(controls) is list and all(type(row) is dict for row in controls)
            else []
        ),
    )
    if value != expected:
        _fail("selected remote snapshot identity changed")
    return expected


def _resource_plan_payload(
    *,
    selected: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    loader_artifact: dict[str, Any],
    receiver_artifact: dict[str, Any],
    service_artifact: dict[str, Any],
    driver_artifact: dict[str, Any],
    activation_authority_artifact: dict[str, Any],
    loader_source_raw: bytes,
) -> dict[str, Any]:
    plan, attempt, receipt, outcome = selected
    payload = {
        **_base_payload(PREACTIVATION_RESOURCE_PROBE_PLAN_SCHEMA),
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_attempt_id": attempt["preformal_upload_attempt_id"],
        "preformal_upload_receipt_id": receipt["preformal_upload_receipt_id"],
        "preformal_upload_outcome_id": outcome["preformal_upload_outcome_id"],
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "local_materialization_attempt_id": plan["local_materialization_attempt_id"],
        "control_facts": plan["control_facts"],
        "preformal_scratch_root": plan["preformal_scratch_root"],
        "preformal_ledger_stage_root": plan["preformal_ledger_stage_root"],
        "fixed_remote_root": plan["fixed_remote_root"],
        "fixed_transport_ledger_root": plan["fixed_transport_ledger_root"],
        "remote_target_alias": plan["remote_target_alias"],
        "expected_remote_hostname": plan["expected_remote_hostname"],
        "ssh_client_contract": plan["ssh_client_contract"],
        "remote_startup_tcb_contract": plan["remote_startup_tcb_contract"],
        "activation_loader_artifact": loader_artifact,
        "activation_receiver_artifact": receiver_artifact,
        "activation_service_artifact": service_artifact,
        "activation_driver_artifact": driver_artifact,
        "activation_authority_artifact": activation_authority_artifact,
        "minimum_memory_total_bytes": MINIMUM_MEMORY_TOTAL_BYTES,
        "minimum_memory_available_bytes": MINIMUM_MEMORY_AVAILABLE_BYTES,
        "minimum_swap_free_bytes_when_swap_exists": MINIMUM_SWAP_FREE_BYTES,
        "minimum_filesystem_available_bytes": MINIMUM_FILESYSTEM_AVAILABLE_BYTES,
        "resource_probe_stage": "READ_ONLY_PREACTIVATION_PROBE",
        "resource_probe_must_precede_local_activation_attempt": True,
        "resource_probe_performs_no_remote_mutation": True,
        "resource_probe_starts_no_remote_process_other_than_ssh_ingress": True,
        "resource_probe_does_not_consume_formal_identity": True,
        "complete_preformal_receipt_does_not_itself_authorize_activation": True,
    }
    remote_template = _resource_probe_remote_python_argv_template(
        loader_source_raw=loader_source_raw, resource_plan_payload=payload
    )
    original_ssh = plan["authorized_ssh_argv_template"]
    payload["authorized_resource_probe_remote_python_argv_template"] = remote_template
    payload["authorized_resource_probe_ssh_argv_template"] = [
        *original_ssh[:-1],
        "builtin exec -c " + " ".join(shlex.quote(item) for item in remote_template),
    ]
    payload["resource_probe_ssh_may_be_repeated_read_only"] = True
    payload["resource_probe_stdout_is_one_canonical_observation_then_eof"] = True
    return payload


def build_preactivation_resource_probe_plan_v42r1(
    *,
    preformal_plan: dict[str, Any],
    preformal_attempt: dict[str, Any],
    preformal_receipt: dict[str, Any],
    preformal_outcome: dict[str, Any],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    service_source_raw: bytes,
    driver_source_raw: bytes,
    activation_authority_source_raw: bytes,
    control_raw_by_name: dict[str, bytes],
) -> dict[str, Any]:
    selected = _selected_preformal_chain(
        preformal_plan=preformal_plan,
        preformal_attempt=preformal_attempt,
        preformal_receipt=preformal_receipt,
        preformal_outcome=preformal_outcome,
    )
    program_artifacts = (
        _artifact(
            loader_source_raw,
            "scripts/v42_materialization_activation_loader.py",
            cap=512 * 1024,
        ),
        _artifact(
            receiver_source_raw,
            "scripts/v42_materialization_activation_receiver.py",
            cap=4 * 1024**2,
        ),
        _artifact(
            service_source_raw,
            "scripts/v42_materialization_activation_service.py",
            cap=4 * 1024**2,
        ),
        _artifact(
            driver_source_raw,
            "scripts/run_v42_materialization_activation.py",
            cap=4 * 1024**2,
        ),
        _artifact(
            activation_authority_source_raw,
            (
                "src/acfqp/"
                "construction_k7_standard_2048_materialization_activation_v42r1.py"
            ),
            cap=4 * 1024**2,
        ),
    )
    _source, transport, _local = _verified_control_documents(
        resource_plan=selected[0], control_raw_by_name=control_raw_by_name
    )
    transport_by_path = {
        row["relative_path"]: row for row in transport["transport_facts"]
    }
    for artifact in program_artifacts:
        transport_fact = transport_by_path.get(artifact["relative_path"])
        if (
            type(transport_fact) is not dict
            or transport_fact.get("git_mode") != artifact["git_mode"]
            or transport_fact.get("git_object_type")
            != artifact["git_object_type"]
            or transport_fact.get("git_blob_oid") != artifact["git_blob_oid"]
            or transport_fact.get("byte_count") != artifact["byte_count"]
            or transport_fact.get("sha256") != artifact["sha256"]
        ):
            _fail(
                "activation program is not an exact selected-commit transport fact: "
                + artifact["relative_path"]
            )
    payload = _resource_plan_payload(
        selected=selected,
        loader_artifact=program_artifacts[0],
        receiver_artifact=program_artifacts[1],
        service_artifact=program_artifacts[2],
        driver_artifact=program_artifacts[3],
        activation_authority_artifact=program_artifacts[4],
        loader_source_raw=loader_source_raw,
    )
    return {
        **payload,
        "preactivation_resource_probe_plan_id": _content_id(
            DOMAIN_PREFIX + "preactivation-resource-probe-plan", payload
        ),
    }


def verify_preactivation_resource_probe_plan_v42r1(
    raw_or_document: bytes | dict[str, Any],
    **build_arguments: Any,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "preactivation resource probe plan")
    expected = build_preactivation_resource_probe_plan_v42r1(**build_arguments)
    if document != expected:
        _fail("preactivation resource probe plan identity changed")
    return document


def _require_document_identity(
    document: dict[str, Any], *, schema: str, identity_field: str, domain: str
) -> None:
    if (
        document.get("schema") != schema
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != authority.FORMAL_IDENTITY
        or document.get("global_execution_ordinal")
        != authority.GLOBAL_EXECUTION_ORDINAL
    ):
        _fail(f"{identity_field} authority header changed")
    claimed = _hex64(document.get(identity_field), identity_field)
    payload = dict(document)
    del payload[identity_field]
    if claimed != _content_id(domain, payload):
        _fail(f"{identity_field} content identity changed")


def _expected_python_observation(resource_plan: dict[str, Any]) -> dict[str, Any]:
    startup = resource_plan.get("remote_startup_tcb_contract")
    if type(startup) is not dict:
        _fail("remote startup TCB changed type")
    fields = (
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
    )
    if any(field not in startup for field in fields):
        _fail("remote startup Python TCB omitted a field")
    return {field: startup[field] for field in fields}


def _resource_result_payload(
    *,
    resource_plan: dict[str, Any],
    preformal_receipt: dict[str, Any],
    stage: str,
    observed_hostname: str,
    observed_user: str,
    observed_uid: int,
    observed_gid: int,
    observed_python: dict[str, Any],
    memory_total_bytes: int,
    memory_available_bytes: int,
    swap_total_bytes: int,
    swap_free_bytes: int,
    filesystem_available_bytes: int,
    cgroup_memory_ancestry: list[dict[str, Any]],
    selected_remote_snapshot: dict[str, Any],
) -> dict[str, Any]:
    if stage not in RESOURCE_STAGES:
        _fail("resource observation stage changed")
    expected_python = _expected_python_observation(resource_plan)
    if observed_python != expected_python:
        _fail("resource observer Python identity changed")
    if (
        observed_hostname != authority.REMOTE_HOSTNAME
        or observed_user != authority.REMOTE_USER
        or observed_uid != authority.REMOTE_UID
        or observed_gid != authority.REMOTE_GID
    ):
        _fail("resource observer host identity changed")
    snapshot = verify_selected_remote_snapshot_v42r1(
        selected_remote_snapshot, preformal_receipt=preformal_receipt
    )
    normalized_cgroup, checks = _resource_checks(
        memory_total_bytes=memory_total_bytes,
        memory_available_bytes=memory_available_bytes,
        swap_total_bytes=swap_total_bytes,
        swap_free_bytes=swap_free_bytes,
        filesystem_available_bytes=filesystem_available_bytes,
        cgroup_memory_ancestry=cgroup_memory_ancestry,
    )
    return {
        **_base_payload(PREACTIVATION_RESOURCE_RESULT_SCHEMA),
        "preactivation_resource_probe_plan_id": resource_plan[
            "preactivation_resource_probe_plan_id"
        ],
        "preformal_upload_receipt_id": resource_plan["preformal_upload_receipt_id"],
        "source_manifest_id": resource_plan["source_manifest_id"],
        "transport_manifest_id": resource_plan["transport_manifest_id"],
        "local_materialization_attempt_id": resource_plan[
            "local_materialization_attempt_id"
        ],
        "resource_observation_stage": stage,
        "observed_hostname": observed_hostname,
        "observed_user": observed_user,
        "observed_uid": observed_uid,
        "observed_gid": observed_gid,
        "observed_python": expected_python,
        "memory_total_bytes": memory_total_bytes,
        "memory_available_bytes": memory_available_bytes,
        "swap_total_bytes": swap_total_bytes,
        "swap_free_bytes": swap_free_bytes,
        "filesystem_available_bytes": filesystem_available_bytes,
        "cgroup_memory_ancestry": normalized_cgroup,
        "resource_gate_checks": checks,
        "all_resource_gates_passed": all(checks.values()),
        "selected_remote_snapshot": snapshot,
        "exact_live_file_descriptors": [0, 1, 2],
        "stdin_stdout_stderr_not_tty": True,
        "remote_mutation_performed": False,
        "fixed_root_effect_performed": False,
        "systemd_effect_performed": False,
        "trusted_bootstrap_effect_performed": False,
        "only_current_ssh_ingress_process_started": True,
        "additional_or_durable_remote_process_started": False,
        "read_only_observation_completed": True,
    }


def build_preactivation_resource_result_v42r1(
    *,
    resource_plan: dict[str, Any],
    preformal_receipt: dict[str, Any],
    stage: str,
    observed_hostname: str,
    observed_user: str,
    observed_uid: int,
    observed_gid: int,
    observed_python: dict[str, Any],
    memory_total_bytes: int,
    memory_available_bytes: int,
    swap_total_bytes: int,
    swap_free_bytes: int,
    filesystem_available_bytes: int,
    cgroup_memory_ancestry: list[dict[str, Any]],
    selected_remote_snapshot: dict[str, Any],
) -> dict[str, Any]:
    _require_document_identity(
        resource_plan,
        schema=PREACTIVATION_RESOURCE_PROBE_PLAN_SCHEMA,
        identity_field="preactivation_resource_probe_plan_id",
        domain=DOMAIN_PREFIX + "preactivation-resource-probe-plan",
    )
    payload = _resource_result_payload(
        resource_plan=resource_plan,
        preformal_receipt=preformal_receipt,
        stage=stage,
        observed_hostname=observed_hostname,
        observed_user=observed_user,
        observed_uid=observed_uid,
        observed_gid=observed_gid,
        observed_python=observed_python,
        memory_total_bytes=memory_total_bytes,
        memory_available_bytes=memory_available_bytes,
        swap_total_bytes=swap_total_bytes,
        swap_free_bytes=swap_free_bytes,
        filesystem_available_bytes=filesystem_available_bytes,
        cgroup_memory_ancestry=cgroup_memory_ancestry,
        selected_remote_snapshot=selected_remote_snapshot,
    )
    return {
        **payload,
        "preactivation_resource_result_id": _content_id(
            DOMAIN_PREFIX + "preactivation-resource-result", payload
        ),
    }


def verify_preactivation_resource_result_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    resource_plan: dict[str, Any],
    preformal_receipt: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "preactivation resource result")
    expected_payload = _resource_result_payload(
        resource_plan=resource_plan,
        preformal_receipt=preformal_receipt,
        stage=document.get("resource_observation_stage"),
        observed_hostname=document.get("observed_hostname"),
        observed_user=document.get("observed_user"),
        observed_uid=document.get("observed_uid"),
        observed_gid=document.get("observed_gid"),
        observed_python=document.get("observed_python"),
        memory_total_bytes=document.get("memory_total_bytes"),
        memory_available_bytes=document.get("memory_available_bytes"),
        swap_total_bytes=document.get("swap_total_bytes"),
        swap_free_bytes=document.get("swap_free_bytes"),
        filesystem_available_bytes=document.get("filesystem_available_bytes"),
        cgroup_memory_ancestry=document.get("cgroup_memory_ancestry"),
        selected_remote_snapshot=document.get("selected_remote_snapshot"),
    )
    expected = {
        **expected_payload,
        "preactivation_resource_result_id": _content_id(
            DOMAIN_PREFIX + "preactivation-resource-result", expected_payload
        ),
    }
    if document != expected:
        _fail("preactivation resource result identity changed")
    return document


def _verified_control_documents(
    *, resource_plan: dict[str, Any], control_raw_by_name: dict[str, bytes]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if type(control_raw_by_name) is not dict or set(control_raw_by_name) != set(
        preformal.CONTROL_NAMES
    ):
        _fail("activation control raw inventory changed")
    expected_facts = resource_plan.get("control_facts")
    if type(expected_facts) is not list:
        _fail("activation resource plan control facts changed")
    facts_by_name = {row.get("name"): row for row in expected_facts if type(row) is dict}
    if set(facts_by_name) != set(preformal.CONTROL_NAMES):
        _fail("activation resource plan control fact names changed")
    for name in preformal.CONTROL_NAMES:
        raw = control_raw_by_name[name]
        fact = facts_by_name[name]
        if (
            type(raw) is not bytes
            or len(raw) != fact.get("byte_count")
            or hashlib.sha256(raw).hexdigest() != fact.get("sha256")
        ):
            _fail(f"activation control raw changed: {name}")
    source = authority.verify_source_manifest_v42r1(
        control_raw_by_name[authority.SOURCE_MANIFEST_NAME]
    )
    transport = authority.verify_transport_manifest_v42r1(
        control_raw_by_name[authority.TRANSPORT_MANIFEST_NAME],
        source_manifest=source,
    )
    local_attempt = authority.verify_local_materialization_attempt_v42r1(
        control_raw_by_name[authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME],
        source_manifest=source,
        transport_manifest=transport,
    )
    if (
        source["source_manifest_id"] != resource_plan["source_manifest_id"]
        or transport["transport_manifest_id"]
        != resource_plan["transport_manifest_id"]
        or local_attempt["local_materialization_attempt_id"]
        != resource_plan["local_materialization_attempt_id"]
    ):
        _fail("activation controls do not join the selected pre-formal receipt")
    return source, transport, local_attempt


def _unit_name_template() -> str:
    return SYSTEMD_UNIT_PREFIX + ACTIVATION_PLAN_ID_SENTINEL + ".service"


def materialize_activation_unit_name_v42r1(activation_plan_id: str) -> str:
    return SYSTEMD_UNIT_PREFIX + _hex64(activation_plan_id, "activation plan id") + ".service"


def materialize_authorized_systemctl_argv_v42r1(
    *, activation_plan: dict[str, Any]
) -> list[str]:
    """Return the one read-only query authorized for the activation unit."""

    plan_id = _hex64(
        activation_plan.get("materialization_activation_plan_id"),
        "materialization activation plan id",
    )
    contract = activation_plan.get("systemd_service_contract")
    if type(contract) is not dict:
        _fail("systemd service contract changed")
    template = contract.get("authorized_systemctl_show_argv_template")
    if type(template) is not list or any(type(item) is not str for item in template):
        _fail("systemctl query template changed")
    result = [item.replace(ACTIVATION_PLAN_ID_SENTINEL, plan_id) for item in template]
    if any(ACTIVATION_PLAN_ID_SENTINEL in item for item in result):
        _fail("systemctl query template replacement was incomplete")
    return result


def _resource_probe_remote_python_argv_template(
    *, loader_source_raw: bytes, resource_plan_payload: dict[str, Any]
) -> list[str]:
    loader = resource_plan_payload["activation_loader_artifact"]
    receiver = resource_plan_payload["activation_receiver_artifact"]
    if _artifact(
        loader_source_raw,
        loader["relative_path"],
        cap=512 * 1024,
    ) != loader:
        _fail("resource probe loader no longer matches its plan")
    return [
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-c",
        loader_source_raw.decode("utf-8"),
        "--activation-resource-probe",
        loader["sha256"],
        str(loader["byte_count"]),
        receiver["sha256"],
        str(receiver["byte_count"]),
        RESOURCE_PROBE_PLAN_ID_SENTINEL,
        resource_plan_payload["preformal_upload_receipt_id"],
    ]


def materialize_authorized_resource_probe_argv_v42r1(
    *, resource_plan: dict[str, Any], remote_python: bool = False
) -> list[str]:
    plan_id = _hex64(
        resource_plan.get("preactivation_resource_probe_plan_id"),
        "preactivation resource probe plan id",
    )
    key = (
        "authorized_resource_probe_remote_python_argv_template"
        if remote_python
        else "authorized_resource_probe_ssh_argv_template"
    )
    template = resource_plan.get(key)
    if type(template) is not list or any(type(item) is not str for item in template):
        _fail("resource probe argv template changed")
    result = [item.replace(RESOURCE_PROBE_PLAN_ID_SENTINEL, plan_id) for item in template]
    if any(RESOURCE_PROBE_PLAN_ID_SENTINEL in item for item in result):
        _fail("resource probe argv replacement was incomplete")
    return result


def _activation_remote_python_argv_template(
    loader_source_raw: bytes, resource_plan: dict[str, Any]
) -> list[str]:
    artifact = resource_plan["activation_loader_artifact"]
    if _artifact(
        loader_source_raw,
        artifact["relative_path"],
        cap=512 * 1024,
    ) != artifact:
        _fail("activation loader no longer matches the resource plan")
    return [
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-c",
        loader_source_raw.decode("utf-8"),
        "--activation-ingress",
        artifact["sha256"],
        str(artifact["byte_count"]),
        resource_plan["activation_receiver_artifact"]["sha256"],
        str(resource_plan["activation_receiver_artifact"]["byte_count"]),
        ACTIVATION_PLAN_ID_SENTINEL,
        LOCAL_ACTIVATION_ATTEMPT_ID_SENTINEL,
    ]


def _classification_remote_python_argv_template(
    loader_source_raw: bytes, resource_plan: dict[str, Any]
) -> list[str]:
    result = _activation_remote_python_argv_template(
        loader_source_raw, resource_plan
    )
    mode_index = result.index("--activation-ingress")
    result[mode_index] = "--activation-classify"
    return result


def _activation_remote_command_template(loader_source_raw: bytes, resource_plan: dict[str, Any]) -> str:
    argv = _activation_remote_python_argv_template(loader_source_raw, resource_plan)
    return "builtin exec -c " + " ".join(shlex.quote(item) for item in argv)


def _authorized_ssh_template(
    *, preformal_plan: dict[str, Any], loader_source_raw: bytes, resource_plan: dict[str, Any]
) -> list[str]:
    original = preformal_plan.get("authorized_ssh_argv_template")
    if type(original) is not list or not original or any(type(item) is not str for item in original):
        _fail("selected pre-formal SSH template changed")
    return [*original[:-1], _activation_remote_command_template(loader_source_raw, resource_plan)]


def _systemd_contract(
    *, resource_plan: dict[str, Any], loader_source_raw: bytes
) -> dict[str, Any]:
    service = resource_plan["activation_service_artifact"]
    loader = resource_plan["activation_loader_artifact"]
    service_path = str(
        Path(resource_plan["fixed_transport_ledger_root"])
        / REMOTE_ACTIVATION_SERVICE_SOURCE_NAME
    )
    bootstrap_worker = [
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-c",
        loader_source_raw.decode("utf-8"),
        "--activation-service-bootstrap",
        loader["sha256"],
        str(loader["byte_count"]),
        service_path,
        service["sha256"],
        str(service["byte_count"]),
        REMOTE_ACTIVATION_ATTEMPT_ID_SENTINEL,
    ]
    clean_worker = [
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-c",
        loader_source_raw.decode("utf-8"),
        "--activation-service-clean",
        loader["sha256"],
        str(loader["byte_count"]),
        service_path,
        service["sha256"],
        str(service["byte_count"]),
        REMOTE_ACTIVATION_ATTEMPT_ID_SENTINEL,
        SYSTEMD_INVOCATION_ID_SENTINEL,
        SYSTEMD_CONTROL_GROUP_SENTINEL,
    ]
    argv = [
        SYSTEMD_RUN,
        "--user",
        "--quiet",
        "--no-ask-password",
        "--unit=" + _unit_name_template(),
        "--slice=app.slice",
        "--service-type=exec",
        "--property=Restart=no",
        "--property=UMask=0077",
        "--property=StandardInput=null",
        "--property=StandardOutput=null",
        "--property=StandardError=null",
        "--property=KillMode=control-group",
        "--property=RuntimeMaxSec=" + str(SYSTEMD_RUNTIME_MAX_SECONDS),
        "--working-directory=" + str(Path(resource_plan["fixed_remote_root"]).parent),
        *bootstrap_worker,
    ]
    forbidden = {"--wait", "--pipe", "--pty", "--scope", "--collect"}
    if forbidden.intersection(argv):
        _fail("systemd activation contract admitted a lifecycle-coupled option")
    return {
        "systemd_run": {
            "path": SYSTEMD_RUN,
            "sha256": SYSTEMD_RUN_SHA256,
            "byte_count": SYSTEMD_RUN_BYTE_COUNT,
            "mode": SYSTEMD_EXECUTABLE_MODE,
            "uid": SYSTEMD_EXECUTABLE_UID,
            "gid": SYSTEMD_EXECUTABLE_GID,
            "st_nlink": SYSTEMD_EXECUTABLE_NLINK,
        },
        "systemctl": {
            "path": SYSTEMCTL,
            "sha256": SYSTEMCTL_SHA256,
            "byte_count": SYSTEMCTL_BYTE_COUNT,
            "mode": SYSTEMD_EXECUTABLE_MODE,
            "uid": SYSTEMD_EXECUTABLE_UID,
            "gid": SYSTEMD_EXECUTABLE_GID,
            "st_nlink": SYSTEMD_EXECUTABLE_NLINK,
        },
        "client_environment": dict(SYSTEMD_CLIENT_ENVIRONMENT),
        "service_environment": dict(SYSTEMD_SERVICE_ENVIRONMENT),
        "unit_name_template": _unit_name_template(),
        "authorized_systemd_run_argv_template": argv,
        "authorized_service_bootstrap_argv_template": bootstrap_worker,
        "authorized_service_worker_argv_template": clean_worker,
        "authorized_systemctl_show_argv_template": [
            SYSTEMCTL,
            "--user",
            "--no-pager",
            "show",
            "--property=Id",
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
            "--property=FragmentPath",
            "--property=MainPID",
            "--property=InvocationID",
            "--property=ControlGroup",
            "--property=Type",
            "--property=StandardInput",
            "--property=StandardOutput",
            "--property=StandardError",
            "--property=Restart",
            "--property=UMask",
            "--property=KillMode",
            "--property=RuntimeMaxUSec",
            "--property=WorkingDirectory",
            "--property=Slice",
            _unit_name_template(),
        ],
        "activation_loader_sha256": loader["sha256"],
        "activation_service_source_path": service_path,
        "activation_service_sha256": service["sha256"],
        "activation_service_byte_count": service["byte_count"],
        "restart": "no",
        "stdio": "null",
        "collect": False,
        "pipe": False,
        "wait": False,
        "pty": False,
        "scope": False,
        "one_systemd_run_call_only": True,
        "service_bootstrap_execves_same_python_with_exact_service_environment": True,
        "unit_absence_never_proves_service_never_started": True,
    }


def _activation_plan_payload(
    *,
    preformal_plan: dict[str, Any],
    resource_plan: dict[str, Any],
    resource_result: dict[str, Any],
    local_materialization_attempt: dict[str, Any],
    loader_source_raw: bytes,
) -> dict[str, Any]:
    if resource_result.get("all_resource_gates_passed") is not True:
        _fail("activation plan requires a passing preactivation resource result")
    if resource_result.get("resource_observation_stage") != "READ_ONLY_PREACTIVATION_PROBE":
        _fail("activation plan requires the preactivation probe stage")
    if (
        resource_result.get("preactivation_resource_probe_plan_id")
        != resource_plan["preactivation_resource_probe_plan_id"]
        or resource_result.get("selected_remote_snapshot") is None
    ):
        _fail("activation resource result does not join its plan")
    trusted_outer = local_materialization_attempt.get("remote_bootstrap_outer_command")
    trusted_inner = local_materialization_attempt.get("remote_bootstrap_inner_command")
    if (
        type(trusted_outer) is not list
        or type(trusted_inner) is not list
        or any(type(item) is not str for item in [*trusted_outer, *trusted_inner])
    ):
        _fail("trusted bootstrap command schema changed")
    return {
        **_base_payload(MATERIALIZATION_ACTIVATION_PLAN_SCHEMA),
        "preactivation_resource_probe_plan_id": resource_plan[
            "preactivation_resource_probe_plan_id"
        ],
        "preactivation_resource_result_id": resource_result[
            "preactivation_resource_result_id"
        ],
        "preformal_upload_plan_id": resource_plan["preformal_upload_plan_id"],
        "preformal_upload_attempt_id": resource_plan["preformal_upload_attempt_id"],
        "preformal_upload_receipt_id": resource_plan["preformal_upload_receipt_id"],
        "preformal_upload_outcome_id": resource_plan["preformal_upload_outcome_id"],
        "source_commit": resource_plan["source_commit"],
        "source_tree": resource_plan["source_tree"],
        "source_manifest_id": resource_plan["source_manifest_id"],
        "transport_manifest_id": resource_plan["transport_manifest_id"],
        "local_materialization_attempt_id": resource_plan[
            "local_materialization_attempt_id"
        ],
        "control_facts": resource_plan["control_facts"],
        "selected_remote_snapshot": resource_result["selected_remote_snapshot"],
        "preformal_scratch_root": resource_plan["preformal_scratch_root"],
        "preformal_ledger_stage_root": resource_plan["preformal_ledger_stage_root"],
        "fixed_remote_root": resource_plan["fixed_remote_root"],
        "fixed_transport_ledger_root": resource_plan[
            "fixed_transport_ledger_root"
        ],
        "remote_target_alias": resource_plan["remote_target_alias"],
        "expected_remote_hostname": resource_plan["expected_remote_hostname"],
        "activation_loader_artifact": resource_plan["activation_loader_artifact"],
        "activation_receiver_artifact": resource_plan["activation_receiver_artifact"],
        "activation_service_artifact": resource_plan["activation_service_artifact"],
        "activation_driver_artifact": resource_plan["activation_driver_artifact"],
        "activation_authority_artifact": resource_plan[
            "activation_authority_artifact"
        ],
        "ssh_client_contract": resource_plan["ssh_client_contract"],
        "remote_startup_tcb_contract": resource_plan["remote_startup_tcb_contract"],
        "authorized_ssh_argv_template": _authorized_ssh_template(
            preformal_plan=preformal_plan,
            loader_source_raw=loader_source_raw,
            resource_plan=resource_plan,
        ),
        "authorized_remote_ingress_python_argv_template": (
            _activation_remote_python_argv_template(
                loader_source_raw, resource_plan
            )
        ),
        "authorized_read_only_classifier_remote_python_argv_template": (
            _classification_remote_python_argv_template(
                loader_source_raw, resource_plan
            )
        ),
        "authorized_read_only_classifier_ssh_argv_template": [
            *preformal_plan["authorized_ssh_argv_template"][:-1],
            "builtin exec -c "
            + " ".join(
                shlex.quote(item)
                for item in _classification_remote_python_argv_template(
                    loader_source_raw, resource_plan
                )
            ),
        ],
        "systemd_service_contract": _systemd_contract(
            resource_plan=resource_plan, loader_source_raw=loader_source_raw
        ),
        "trusted_bootstrap_outer_command": trusted_outer,
        "trusted_bootstrap_inner_command": trusted_inner,
        "terminal_must_be_durable_before_trusted_outer_exec": True,
        "activation_service_is_terminal_to_launcher_successor": True,
        "activation_service_must_reverify_terminal_id_and_bytes_immediately_before_exec": True,
        "trusted_bootstrap_outer_command_must_remain_byte_for_byte_unchanged": True,
        "transport_terminal_should_join_future_launcher_evidence_defense_in_depth": True,
        "current_frozen_launcher_consumes_transport_terminal_id": False,
        "formal_outer_exec_enabled_only_after_service_successor_join": True,
        "ordinary_ssh_with_pinned_login_shell_tcb": True,
        "shell_free": False,
        "capability_confined": False,
        "local_attempt_must_be_durable_before_network_start": True,
        "same_activation_identity_retry_forbidden": True,
        "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim": True,
        "read_only_classification_only_after_ambiguous_cut": True,
        "fixed_root_exact_inventory": list(preformal.CONTROL_NAMES),
        "ledger_stage_must_be_renamed_noreplace_before_systemd": True,
        "scratch_must_be_renamed_noreplace_to_fixed_root": True,
    }


def build_materialization_activation_plan_v42r1(
    *,
    preformal_plan: dict[str, Any],
    preformal_attempt: dict[str, Any],
    resource_plan: dict[str, Any],
    resource_result: dict[str, Any],
    preformal_receipt: dict[str, Any],
    preformal_outcome: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    service_source_raw: bytes,
    driver_source_raw: bytes,
    activation_authority_source_raw: bytes,
) -> dict[str, Any]:
    resource_plan = verify_preactivation_resource_probe_plan_v42r1(
        resource_plan,
        preformal_plan=preformal_plan,
        preformal_attempt=preformal_attempt,
        preformal_receipt=preformal_receipt,
        preformal_outcome=preformal_outcome,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        service_source_raw=service_source_raw,
        driver_source_raw=driver_source_raw,
        activation_authority_source_raw=activation_authority_source_raw,
        control_raw_by_name=control_raw_by_name,
    )
    result = verify_preactivation_resource_result_v42r1(
        resource_result,
        resource_plan=resource_plan,
        preformal_receipt=preformal_receipt,
    )
    _source, _transport, local_attempt = _verified_control_documents(
        resource_plan=resource_plan, control_raw_by_name=control_raw_by_name
    )
    payload = _activation_plan_payload(
        preformal_plan=preformal_plan,
        resource_plan=resource_plan,
        resource_result=result,
        local_materialization_attempt=local_attempt,
        loader_source_raw=loader_source_raw,
    )
    return {
        **payload,
        "materialization_activation_plan_id": _content_id(
            DOMAIN_PREFIX + "materialization-activation-plan", payload
        ),
    }


def verify_materialization_activation_plan_v42r1(
    raw_or_document: bytes | dict[str, Any], **build_arguments: Any
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "materialization activation plan")
    expected = build_materialization_activation_plan_v42r1(**build_arguments)
    if document != expected:
        _fail("materialization activation plan identity changed")
    return document


def materialize_authorized_ssh_argv_v42r1(
    *, activation_plan: dict[str, Any], local_activation_attempt_id: str
) -> list[str]:
    plan_id = _hex64(
        activation_plan.get("materialization_activation_plan_id"),
        "materialization activation plan id",
    )
    attempt_id = _hex64(local_activation_attempt_id, "local activation attempt id")
    template = activation_plan.get("authorized_ssh_argv_template")
    if type(template) is not list:
        _fail("activation SSH argv template changed type")
    result = [
        item.replace(ACTIVATION_PLAN_ID_SENTINEL, plan_id).replace(
            LOCAL_ACTIVATION_ATTEMPT_ID_SENTINEL, attempt_id
        )
        for item in template
    ]
    if any(
        ACTIVATION_PLAN_ID_SENTINEL in item
        or LOCAL_ACTIVATION_ATTEMPT_ID_SENTINEL in item
        for item in result
    ):
        _fail("activation SSH argv template replacement was incomplete")
    return result


def materialize_authorized_remote_ingress_argv_v42r1(
    *, activation_plan: dict[str, Any], local_activation_attempt_id: str
) -> list[str]:
    plan_id = _hex64(
        activation_plan.get("materialization_activation_plan_id"),
        "materialization activation plan id",
    )
    attempt_id = _hex64(local_activation_attempt_id, "local activation attempt id")
    template = activation_plan.get("authorized_remote_ingress_python_argv_template")
    if type(template) is not list or any(type(item) is not str for item in template):
        _fail("remote ingress Python argv template changed")
    result = [
        item.replace(ACTIVATION_PLAN_ID_SENTINEL, plan_id).replace(
            LOCAL_ACTIVATION_ATTEMPT_ID_SENTINEL, attempt_id
        )
        for item in template
    ]
    if any("{acfqp_v42_" in item for item in result):
        _fail("remote ingress argv template replacement was incomplete")
    return result


def materialize_authorized_classifier_argv_v42r1(
    *,
    activation_plan: dict[str, Any],
    local_activation_attempt_id: str,
    remote_python: bool = False,
) -> list[str]:
    plan_id = _hex64(
        activation_plan.get("materialization_activation_plan_id"),
        "materialization activation plan id",
    )
    attempt_id = _hex64(local_activation_attempt_id, "local activation attempt id")
    key = (
        "authorized_read_only_classifier_remote_python_argv_template"
        if remote_python
        else "authorized_read_only_classifier_ssh_argv_template"
    )
    template = activation_plan.get(key)
    if type(template) is not list or any(type(item) is not str for item in template):
        _fail("read-only classifier argv template changed")
    result = [
        item.replace(ACTIVATION_PLAN_ID_SENTINEL, plan_id).replace(
            LOCAL_ACTIVATION_ATTEMPT_ID_SENTINEL, attempt_id
        )
        for item in template
    ]
    if any("{acfqp_v42_" in item for item in result):
        _fail("read-only classifier argv replacement was incomplete")
    return result


def _local_activation_attempt_payload(
    activation_plan: dict[str, Any], *, local_effective_uid: int
) -> dict[str, Any]:
    if type(local_effective_uid) is not int or local_effective_uid < 0:
        _fail("local effective uid changed")
    plan_id = _hex64(
        activation_plan.get("materialization_activation_plan_id"),
        "materialization activation plan id",
    )
    local_root = str(
        preformal.LOCAL_TRANSPORT_PARENT
        / LOCAL_ACTIVATION_CONTROL_ROOT_RELATIVE
        / plan_id
    )
    return {
        **_base_payload(LOCAL_MATERIALIZATION_ACTIVATION_ATTEMPT_SCHEMA),
        "materialization_activation_plan_id": plan_id,
        "preactivation_resource_result_id": activation_plan[
            "preactivation_resource_result_id"
        ],
        "preformal_upload_receipt_id": activation_plan[
            "preformal_upload_receipt_id"
        ],
        "source_manifest_id": activation_plan["source_manifest_id"],
        "transport_manifest_id": activation_plan["transport_manifest_id"],
        "local_materialization_attempt_id": activation_plan[
            "local_materialization_attempt_id"
        ],
        "preformal_scratch_root": activation_plan["preformal_scratch_root"],
        "preformal_ledger_stage_root": activation_plan[
            "preformal_ledger_stage_root"
        ],
        "fixed_remote_root": activation_plan["fixed_remote_root"],
        "fixed_transport_ledger_root": activation_plan[
            "fixed_transport_ledger_root"
        ],
        "derived_systemd_unit_name": materialize_activation_unit_name_v42r1(
            plan_id
        ),
        "local_control_root": local_root,
        "local_attempt_path": str(Path(local_root) / LOCAL_ACTIVATION_ATTEMPT_NAME),
        "local_network_start_path": str(
            Path(local_root) / LOCAL_ACTIVATION_NETWORK_START_NAME
        ),
        "local_effective_uid": local_effective_uid,
        "expected_scratch_state": "EXACT_DIRECTORY",
        "expected_ledger_stage_state": "EXACT_DIRECTORY",
        "expected_fixed_remote_root_state": "ABSENT",
        "expected_fixed_transport_ledger_state": "ABSENT",
        "published_o_excl_nofollow_mode_0400": True,
        "local_attempt_and_parent_fsynced_before_network_start": True,
        "published_before_any_activation_ssh_or_systemd_effect": True,
        "network_effect_started_at_publication": False,
        "systemd_effect_started_at_publication": False,
        "fixed_root_effect_started_at_publication": False,
        "effect_may_start_only_after_separate_network_start_marker": True,
        "same_activation_identity_retry_forbidden_after_network_start": True,
        "postnetwork_followup_is_read_only_only": True,
        "formal_ssh_stdin_frame_order": [
            "MATERIALIZATION_ACTIVATION_PLAN",
            "LOCAL_MATERIALIZATION_ACTIVATION_ATTEMPT",
            "ACTIVATION_RECEIVER_SOURCE",
        ],
        "formal_ssh_stdin_raw_hash_is_not_embedded_to_avoid_self_reference": True,
    }


def build_local_materialization_activation_attempt_v42r1(
    *, activation_plan: dict[str, Any], local_effective_uid: int
) -> dict[str, Any]:
    _require_document_identity(
        activation_plan,
        schema=MATERIALIZATION_ACTIVATION_PLAN_SCHEMA,
        identity_field="materialization_activation_plan_id",
        domain=DOMAIN_PREFIX + "materialization-activation-plan",
    )
    payload = _local_activation_attempt_payload(
        activation_plan, local_effective_uid=local_effective_uid
    )
    return {
        **payload,
        "local_materialization_activation_attempt_id": _content_id(
            DOMAIN_PREFIX + "local-materialization-activation-attempt", payload
        ),
    }


def verify_local_materialization_activation_attempt_v42r1(
    raw_or_document: bytes | dict[str, Any], *, activation_plan: dict[str, Any]
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "local activation attempt")
    expected = build_local_materialization_activation_attempt_v42r1(
        activation_plan=activation_plan,
        local_effective_uid=document.get("local_effective_uid"),
    )
    if document != expected:
        _fail("local activation attempt identity changed")
    return document


def _network_start_payload(
    *, activation_plan: dict[str, Any], local_attempt: dict[str, Any]
) -> dict[str, Any]:
    argv = materialize_authorized_ssh_argv_v42r1(
        activation_plan=activation_plan,
        local_activation_attempt_id=local_attempt[
            "local_materialization_activation_attempt_id"
        ],
    )
    encoded = canonical_json_bytes(argv)
    return {
        **_base_payload(MATERIALIZATION_ACTIVATION_NETWORK_START_SCHEMA),
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "local_materialization_activation_attempt_id": local_attempt[
            "local_materialization_activation_attempt_id"
        ],
        "preformal_upload_receipt_id": activation_plan[
            "preformal_upload_receipt_id"
        ],
        "source_manifest_id": activation_plan["source_manifest_id"],
        "transport_manifest_id": activation_plan["transport_manifest_id"],
        "authorized_ssh_argv": argv,
        "authorized_ssh_argv_sha256": hashlib.sha256(encoded).hexdigest(),
        "authorized_ssh_argv_byte_count": len(encoded),
        "stdin_frame_order": local_attempt["formal_ssh_stdin_frame_order"],
        "stdin_is_canonical_framed_documents_and_receiver_then_eof": True,
        "published_o_excl_nofollow_mode_0400": True,
        "marker_and_parent_fsynced_immediately_before_single_popen": True,
        "network_effect_may_have_occurred_after_publication": True,
        "same_activation_ssh_invocation_retry_forbidden": True,
        "timeout_disconnect_nonzero_or_noncanonical_output_is_ambiguous": True,
    }


def build_materialization_activation_network_start_v42r1(
    *, activation_plan: dict[str, Any], local_attempt: dict[str, Any]
) -> dict[str, Any]:
    attempt = verify_local_materialization_activation_attempt_v42r1(
        local_attempt, activation_plan=activation_plan
    )
    payload = _network_start_payload(
        activation_plan=activation_plan, local_attempt=attempt
    )
    return {
        **payload,
        "materialization_activation_network_start_id": _content_id(
            DOMAIN_PREFIX + "materialization-activation-network-start", payload
        ),
    }


def verify_materialization_activation_network_start_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "activation network start")
    expected = build_materialization_activation_network_start_v42r1(
        activation_plan=activation_plan, local_attempt=local_attempt
    )
    if document != expected:
        _fail("activation network start identity changed")
    return document


def _verified_ingress_result(
    value: object,
    *,
    activation_plan: dict[str, Any],
    remote_attempt_id: str,
) -> dict[str, Any]:
    fields = {
        "schema",
        "materialization_activation_plan_id",
        "remote_materialization_activation_attempt_id",
        "systemd_run_returncode",
        "systemd_effect_may_have_occurred",
        "same_activation_identity_retry_forbidden",
        "read_only_followup_only",
    }
    if type(value) is not dict or set(value) != fields:
        _fail("activation ingress result schema changed")
    returncode = value.get("systemd_run_returncode")
    if (
        value.get("schema")
        != "acfqp.v42_remote_ordinal2_activation_ingress_result.v42r1"
        or value.get("materialization_activation_plan_id")
        != activation_plan["materialization_activation_plan_id"]
        or value.get("remote_materialization_activation_attempt_id")
        != _hex64(remote_attempt_id, "remote activation attempt id")
        or type(returncode) is not int
        or not -255 <= returncode <= 255
        or value.get("systemd_effect_may_have_occurred") is not True
        or value.get("same_activation_identity_retry_forbidden") is not True
        or value.get("read_only_followup_only") is not True
    ):
        _fail("activation ingress result semantics changed")
    return dict(value)


def build_local_materialization_activation_receipt_v42r1(
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
    remote_attempt_id: str,
    ingress_result: dict[str, Any],
) -> dict[str, Any]:
    local_attempt = verify_local_materialization_activation_attempt_v42r1(
        local_attempt, activation_plan=activation_plan
    )
    network_start = verify_materialization_activation_network_start_v42r1(
        network_start,
        activation_plan=activation_plan,
        local_attempt=local_attempt,
    )
    result = _verified_ingress_result(
        ingress_result,
        activation_plan=activation_plan,
        remote_attempt_id=remote_attempt_id,
    )
    payload = {
        **_base_payload(LOCAL_MATERIALIZATION_ACTIVATION_RECEIPT_SCHEMA),
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "local_materialization_activation_attempt_id": local_attempt[
            "local_materialization_activation_attempt_id"
        ],
        "materialization_activation_network_start_id": network_start[
            "materialization_activation_network_start_id"
        ],
        "remote_materialization_activation_attempt_id": remote_attempt_id,
        "exact_activation_ingress_result": result,
        "exact_canonical_response_and_eof_observed": True,
        "formal_execution_result_not_claimed": True,
        "same_activation_identity_retry_forbidden": True,
        "read_only_followup_only": True,
    }
    return {
        **payload,
        "local_materialization_activation_receipt_id": _content_id(
            DOMAIN_PREFIX + "local-materialization-activation-receipt", payload
        ),
    }


def verify_local_materialization_activation_receipt_v42r1(
    raw_or_document: bytes | dict[str, Any],
    **build_arguments: Any,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "local activation receipt")
    expected = build_local_materialization_activation_receipt_v42r1(
        ingress_result=document.get("exact_activation_ingress_result"),
        **build_arguments,
    )
    if document != expected:
        _fail("local activation receipt identity changed")
    return document


def build_local_materialization_activation_ambiguity_v42r1(
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
    reason_code: str,
) -> dict[str, Any]:
    local_attempt = verify_local_materialization_activation_attempt_v42r1(
        local_attempt, activation_plan=activation_plan
    )
    network_start = verify_materialization_activation_network_start_v42r1(
        network_start,
        activation_plan=activation_plan,
        local_attempt=local_attempt,
    )
    if reason_code not in {
        "SSH_OUTCOME_NOT_EXACT",
        "RECOVERED_POST_MARKER_WITHOUT_DURABLE_OUTCOME",
        "RECOVERED_EXTERNAL_NETWORK_CUT_WITHOUT_INNER_MARKER",
    }:
        _fail("local activation ambiguity reason changed")
    payload = {
        **_base_payload(LOCAL_MATERIALIZATION_ACTIVATION_AMBIGUITY_SCHEMA),
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "local_materialization_activation_attempt_id": local_attempt[
            "local_materialization_activation_attempt_id"
        ],
        "materialization_activation_network_start_id": network_start[
            "materialization_activation_network_start_id"
        ],
        "reason_code": reason_code,
        "classification": CLASSIFICATION_AMBIGUOUS,
        "network_or_systemd_effect_may_have_occurred": True,
        "same_activation_identity_retry_forbidden": True,
        "read_only_followup_only": True,
    }
    return {
        **payload,
        "local_materialization_activation_ambiguity_id": _content_id(
            DOMAIN_PREFIX + "local-materialization-activation-ambiguity", payload
        ),
    }


def verify_local_materialization_activation_ambiguity_v42r1(
    raw_or_document: bytes | dict[str, Any],
    **build_arguments: Any,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "local activation ambiguity")
    expected = build_local_materialization_activation_ambiguity_v42r1(
        reason_code=document.get("reason_code"), **build_arguments
    )
    if document != expected:
        _fail("local activation ambiguity identity changed")
    return document


def _remote_activation_attempt_payload(
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
    observed_remote_snapshot: dict[str, Any],
    observed_remote_ingress_argv: list[str],
    observed_hostname: str,
    observed_user: str,
    observed_uid: int,
    observed_gid: int,
) -> dict[str, Any]:
    if observed_remote_snapshot != activation_plan["selected_remote_snapshot"]:
        _fail("ingress remote snapshot changed from the selected resource probe")
    expected_remote_argv = materialize_authorized_remote_ingress_argv_v42r1(
        activation_plan=activation_plan,
        local_activation_attempt_id=local_attempt[
            "local_materialization_activation_attempt_id"
        ],
    )
    if observed_remote_ingress_argv != expected_remote_argv:
        _fail("remote ingress Python argv changed")
    if (
        observed_hostname != authority.REMOTE_HOSTNAME
        or observed_user != authority.REMOTE_USER
        or observed_uid != authority.REMOTE_UID
        or observed_gid != authority.REMOTE_GID
    ):
        _fail("remote ingress identity changed")
    return {
        **_base_payload(REMOTE_MATERIALIZATION_ACTIVATION_ATTEMPT_SCHEMA),
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "local_materialization_activation_attempt_id": local_attempt[
            "local_materialization_activation_attempt_id"
        ],
        "materialization_activation_network_start_id": network_start[
            "materialization_activation_network_start_id"
        ],
        "preformal_upload_receipt_id": activation_plan[
            "preformal_upload_receipt_id"
        ],
        "source_manifest_id": activation_plan["source_manifest_id"],
        "transport_manifest_id": activation_plan["transport_manifest_id"],
        "local_materialization_attempt_id": activation_plan[
            "local_materialization_attempt_id"
        ],
        "materialization_activation_plan": activation_plan,
        "local_materialization_activation_attempt": local_attempt,
        "materialization_activation_network_start": network_start,
        "observed_remote_snapshot": observed_remote_snapshot,
        "authorized_local_ssh_argv_from_verified_network_start": network_start[
            "authorized_ssh_argv"
        ],
        "observed_remote_ingress_python_argv": observed_remote_ingress_argv,
        "observed_hostname": observed_hostname,
        "observed_user": observed_user,
        "observed_uid": observed_uid,
        "observed_gid": observed_gid,
        "exact_live_file_descriptors": [0, 1, 2],
        "stdin_stdout_stderr_not_tty": True,
        "remote_startup_tcb_contract": activation_plan[
            "remote_startup_tcb_contract"
        ],
        "preformal_scratch_root": activation_plan["preformal_scratch_root"],
        "preformal_ledger_stage_root": activation_plan[
            "preformal_ledger_stage_root"
        ],
        "fixed_remote_root": activation_plan["fixed_remote_root"],
        "fixed_transport_ledger_root": activation_plan[
            "fixed_transport_ledger_root"
        ],
        "activation_service_artifact": activation_plan[
            "activation_service_artifact"
        ],
        "systemd_service_contract": activation_plan["systemd_service_contract"],
        "published_as_first_child_of_bound_empty_ledger_stage": True,
        "published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "service_source_written_o_excl_nofollow_mode_0400_and_fsynced_after_attempt": True,
        "ledger_stage_fsynced_before_rename": True,
        "ledger_stage_renamed_noreplace_to_fixed_ledger": True,
        "shared_parent_fsynced_before_systemd_run": True,
        "published_before_first_systemd_run_effect": True,
        "systemd_run_effect_started_at_publication": False,
        "fixed_root_publish_started_at_publication": False,
        "same_activation_identity_retry_forbidden": True,
    }


def build_remote_materialization_activation_attempt_v42r1(
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
    observed_remote_snapshot: dict[str, Any],
    observed_remote_ingress_argv: list[str],
    observed_hostname: str,
    observed_user: str,
    observed_uid: int,
    observed_gid: int,
) -> dict[str, Any]:
    local_attempt = verify_local_materialization_activation_attempt_v42r1(
        local_attempt, activation_plan=activation_plan
    )
    network_start = verify_materialization_activation_network_start_v42r1(
        network_start,
        activation_plan=activation_plan,
        local_attempt=local_attempt,
    )
    payload = _remote_activation_attempt_payload(
        activation_plan=activation_plan,
        local_attempt=local_attempt,
        network_start=network_start,
        observed_remote_snapshot=observed_remote_snapshot,
        observed_remote_ingress_argv=observed_remote_ingress_argv,
        observed_hostname=observed_hostname,
        observed_user=observed_user,
        observed_uid=observed_uid,
        observed_gid=observed_gid,
    )
    return {
        **payload,
        "remote_materialization_activation_attempt_id": _content_id(
            DOMAIN_PREFIX + "remote-materialization-activation-attempt", payload
        ),
    }


def verify_remote_materialization_activation_attempt_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote activation attempt")
    expected = build_remote_materialization_activation_attempt_v42r1(
        activation_plan=activation_plan,
        local_attempt=local_attempt,
        network_start=network_start,
        observed_remote_snapshot=document.get("observed_remote_snapshot"),
        observed_remote_ingress_argv=document.get(
            "observed_remote_ingress_python_argv"
        ),
        observed_hostname=document.get("observed_hostname"),
        observed_user=document.get("observed_user"),
        observed_uid=document.get("observed_uid"),
        observed_gid=document.get("observed_gid"),
    )
    if document != expected:
        _fail("remote activation attempt identity changed")
    return document


def materialize_authorized_systemd_argv_v42r1(
    *, activation_plan: dict[str, Any], remote_activation_attempt_id: str
) -> list[str]:
    plan_id = _hex64(
        activation_plan.get("materialization_activation_plan_id"),
        "materialization activation plan id",
    )
    attempt_id = _hex64(remote_activation_attempt_id, "remote activation attempt id")
    contract = activation_plan.get("systemd_service_contract")
    if type(contract) is not dict or type(
        contract.get("authorized_systemd_run_argv_template")
    ) is not list:
        _fail("systemd service contract changed")
    result = [
        item.replace(ACTIVATION_PLAN_ID_SENTINEL, plan_id).replace(
            REMOTE_ACTIVATION_ATTEMPT_ID_SENTINEL, attempt_id
        )
        for item in contract["authorized_systemd_run_argv_template"]
    ]
    if any(
        ACTIVATION_PLAN_ID_SENTINEL in item
        or REMOTE_ACTIVATION_ATTEMPT_ID_SENTINEL in item
        for item in result
    ):
        _fail("systemd argv template replacement was incomplete")
    return result


def materialize_authorized_service_argv_v42r1(
    *,
    activation_plan: dict[str, Any],
    remote_activation_attempt_id: str,
    systemd_invocation_id: str,
    systemd_control_group: str,
) -> list[str]:
    attempt_id = _hex64(remote_activation_attempt_id, "remote activation attempt id")
    contract = activation_plan.get("systemd_service_contract")
    if type(contract) is not dict or type(
        contract.get("authorized_service_worker_argv_template")
    ) is not list:
        _fail("systemd service worker contract changed")
    if type(systemd_invocation_id) is not str or re.fullmatch(
        r"[0-9a-f]{32}", systemd_invocation_id
    ) is None:
        _fail("systemd invocation ID changed")
    if type(systemd_control_group) is not str or not systemd_control_group.startswith("/"):
        _fail("systemd control group changed")
    result = [
        item.replace(REMOTE_ACTIVATION_ATTEMPT_ID_SENTINEL, attempt_id)
        .replace(SYSTEMD_INVOCATION_ID_SENTINEL, systemd_invocation_id)
        .replace(SYSTEMD_CONTROL_GROUP_SENTINEL, systemd_control_group)
        for item in contract["authorized_service_worker_argv_template"]
    ]
    if any("{acfqp_v42_" in item for item in result):
        _fail("service argv template replacement was incomplete")
    return result


def materialize_authorized_service_bootstrap_argv_v42r1(
    *, activation_plan: dict[str, Any], remote_activation_attempt_id: str
) -> list[str]:
    attempt_id = _hex64(remote_activation_attempt_id, "remote activation attempt id")
    contract = activation_plan.get("systemd_service_contract")
    if type(contract) is not dict or type(
        contract.get("authorized_service_bootstrap_argv_template")
    ) is not list:
        _fail("systemd service bootstrap contract changed")
    result = [
        item.replace(REMOTE_ACTIVATION_ATTEMPT_ID_SENTINEL, attempt_id)
        for item in contract["authorized_service_bootstrap_argv_template"]
    ]
    if any("{acfqp_v42_" in item for item in result):
        _fail("service bootstrap argv template replacement was incomplete")
    return result


def _verified_live_systemd_unit_properties(
    *,
    activation_plan: dict[str, Any],
    remote_attempt: dict[str, Any],
    systemd_unit_name: str,
    systemd_invocation_id: str,
    systemd_control_group: str,
    observed_main_pid: int,
    observed_systemd_unit_properties: dict[str, Any],
) -> dict[str, Any]:
    expected_unit = materialize_activation_unit_name_v42r1(
        activation_plan["materialization_activation_plan_id"]
    )
    if systemd_unit_name != expected_unit:
        _fail("systemd unit name changed")
    if type(observed_main_pid) is not int or observed_main_pid <= 1:
        _fail("systemd main PID changed")
    if (
        type(systemd_control_group) is not str
        or not systemd_control_group.startswith("/")
        or not systemd_control_group.endswith("/app.slice/" + expected_unit)
        or ".." in systemd_control_group.split("/")
    ):
        _fail("systemd control group changed")
    expected = {
        "Id": expected_unit,
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "running",
        "FragmentPath": f"/run/user/{authority.REMOTE_UID}/systemd/transient/{expected_unit}",
        "MainPID": observed_main_pid,
        "InvocationID": systemd_invocation_id,
        "ControlGroup": systemd_control_group,
        "Type": "exec",
        "bootstrap_argv_verified_by_tiny_loader_before_clean_exec": True,
        "StandardInput": "null",
        "StandardOutput": "null",
        "StandardError": "null",
        "Restart": "no",
        "UMask": "0077",
        "KillMode": "control-group",
        "RuntimeMaxUSec": "1w",
        "WorkingDirectory": str(Path(activation_plan["fixed_remote_root"]).parent),
        "Slice": "app.slice",
        "invocation_symlink_verified": True,
        "observed_via_pinned_systemctl_executable": True,
        "systemctl_argv": materialize_authorized_systemctl_argv_v42r1(
            activation_plan=activation_plan
        ),
    }
    if observed_systemd_unit_properties != expected:
        _fail("live systemd unit properties changed")
    return expected


def build_exact_five_live_snapshot_v42r1(
    *,
    preformal_receipt: dict[str, Any],
    root_path: str,
    root_identity: dict[str, Any],
    control_identities: list[dict[str, Any]],
) -> dict[str, Any]:
    receipt = _canonical_document(preformal_receipt, "pre-formal receipt")
    portable_files = receipt.get("observed_control_file_facts")
    if type(root_path) is not str or not root_path.startswith("/"):
        _fail("exact-five root path changed")
    if type(portable_files) is not list or len(portable_files) != len(preformal.CONTROL_NAMES):
        _fail("pre-formal receipt control facts changed")
    if type(control_identities) is not list or len(control_identities) != len(portable_files):
        _fail("exact-five transient control inventory changed")
    root = _transient_identity(
        root_identity,
        path=root_path,
        node_type="DIRECTORY",
        mode=0o700,
        uid=authority.REMOTE_UID,
        gid=authority.REMOTE_GID,
        label="exact-five root",
    )
    controls: list[dict[str, Any]] = []
    for name, portable, transient in zip(
        preformal.CONTROL_NAMES, portable_files, control_identities, strict=True
    ):
        if portable.get("name") != name:
            _fail("pre-formal receipt control order changed")
        controls.append(
            {
                "name": name,
                "path": str(Path(root_path) / name),
                "sha256": portable["sha256"],
                "byte_count": portable["byte_count"],
                "mode": 0o400,
                "uid": authority.REMOTE_UID,
                "gid": authority.REMOTE_GID,
                "identity": _transient_identity(
                    transient,
                    path=str(Path(root_path) / name),
                    node_type="REGULAR_FILE",
                    mode=0o400,
                    uid=authority.REMOTE_UID,
                    gid=authority.REMOTE_GID,
                    regular_size=portable["byte_count"],
                    label=f"exact-five control {name}",
                ),
            }
        )
    return {
        "root_path": root_path,
        "root_identity": root,
        "control_facts": controls,
        "exact_inventory": list(preformal.CONTROL_NAMES),
        "every_file_hashed_and_fsynced_through_one_pinned_descriptor": True,
        "root_directory_fsynced": True,
        "whole_tree_first_last_snapshot_equal": True,
        "no_symlink_hardlink_or_special_node": True,
    }


def verify_exact_five_live_snapshot_v42r1(
    value: object, *, preformal_receipt: dict[str, Any], root_path: str
) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("exact-five live snapshot changed type")
    controls = value.get("control_facts")
    expected = build_exact_five_live_snapshot_v42r1(
        preformal_receipt=preformal_receipt,
        root_path=root_path,
        root_identity=value.get("root_identity"),
        control_identities=(
            [row.get("identity") for row in controls]
            if type(controls) is list and all(type(row) is dict for row in controls)
            else []
        ),
    )
    if value != expected:
        _fail("exact-five live snapshot changed")
    return expected


def _service_resource_gate(
    *,
    activation_plan: dict[str, Any],
    stage: str,
    memory_total_bytes: int,
    memory_available_bytes: int,
    swap_total_bytes: int,
    swap_free_bytes: int,
    filesystem_available_bytes: int,
    cgroup_memory_ancestry: list[dict[str, Any]],
) -> dict[str, Any]:
    if stage not in ("SYSTEMD_SERVICE_RECEIPT_GATE", "SYSTEMD_SERVICE_PUBLISH_GATE"):
        _fail("systemd service resource stage changed")
    ancestry, checks = _resource_checks(
        memory_total_bytes=memory_total_bytes,
        memory_available_bytes=memory_available_bytes,
        swap_total_bytes=swap_total_bytes,
        swap_free_bytes=swap_free_bytes,
        filesystem_available_bytes=filesystem_available_bytes,
        cgroup_memory_ancestry=cgroup_memory_ancestry,
    )
    return {
        "stage": stage,
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "memory_total_bytes": memory_total_bytes,
        "memory_available_bytes": memory_available_bytes,
        "swap_total_bytes": swap_total_bytes,
        "swap_free_bytes": swap_free_bytes,
        "filesystem_available_bytes": filesystem_available_bytes,
        "cgroup_memory_ancestry": ancestry,
        "resource_gate_checks": checks,
        "all_resource_gates_passed": all(checks.values()),
        "observation_was_read_only": True,
    }


def build_remote_activation_service_receipt_v42r1(
    *,
    activation_plan: dict[str, Any],
    remote_attempt: dict[str, Any],
    observed_service_argv: list[str],
    observed_environment: dict[str, str],
    systemd_unit_name: str,
    systemd_invocation_id: str,
    systemd_control_group: str,
    observed_main_pid: int,
    observed_systemd_unit_properties: dict[str, Any],
    memory_total_bytes: int,
    memory_available_bytes: int,
    swap_total_bytes: int,
    swap_free_bytes: int,
    filesystem_available_bytes: int,
    cgroup_memory_ancestry: list[dict[str, Any]],
) -> dict[str, Any]:
    _require_document_identity(
        remote_attempt,
        schema=REMOTE_MATERIALIZATION_ACTIVATION_ATTEMPT_SCHEMA,
        identity_field="remote_materialization_activation_attempt_id",
        domain=DOMAIN_PREFIX + "remote-materialization-activation-attempt",
    )
    expected_argv = materialize_authorized_service_argv_v42r1(
        activation_plan=activation_plan,
        remote_activation_attempt_id=remote_attempt[
            "remote_materialization_activation_attempt_id"
        ],
        systemd_invocation_id=systemd_invocation_id,
        systemd_control_group=systemd_control_group,
    )
    if observed_service_argv != expected_argv:
        _fail("systemd service argv changed")
    if observed_environment != SYSTEMD_SERVICE_ENVIRONMENT:
        _fail("systemd service environment changed")
    if type(systemd_invocation_id) is not str or re.fullmatch(
        r"[0-9a-f]{32}", systemd_invocation_id
    ) is None:
        _fail("systemd invocation ID changed")
    live_unit = _verified_live_systemd_unit_properties(
        activation_plan=activation_plan,
        remote_attempt=remote_attempt,
        systemd_unit_name=systemd_unit_name,
        systemd_invocation_id=systemd_invocation_id,
        systemd_control_group=systemd_control_group,
        observed_main_pid=observed_main_pid,
        observed_systemd_unit_properties=observed_systemd_unit_properties,
    )
    gate = _service_resource_gate(
        activation_plan=activation_plan,
        stage="SYSTEMD_SERVICE_RECEIPT_GATE",
        memory_total_bytes=memory_total_bytes,
        memory_available_bytes=memory_available_bytes,
        swap_total_bytes=swap_total_bytes,
        swap_free_bytes=swap_free_bytes,
        filesystem_available_bytes=filesystem_available_bytes,
        cgroup_memory_ancestry=cgroup_memory_ancestry,
    )
    if gate["all_resource_gates_passed"] is not True:
        _fail("service receipt cannot publish after a failed resource gate")
    payload = {
        **_base_payload(REMOTE_ACTIVATION_SERVICE_RECEIPT_SCHEMA),
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "remote_materialization_activation_attempt_id": remote_attempt[
            "remote_materialization_activation_attempt_id"
        ],
        "preformal_upload_receipt_id": activation_plan[
            "preformal_upload_receipt_id"
        ],
        "source_manifest_id": activation_plan["source_manifest_id"],
        "transport_manifest_id": activation_plan["transport_manifest_id"],
        "systemd_unit_name": systemd_unit_name,
        "systemd_invocation_id": systemd_invocation_id,
        "systemd_control_group": systemd_control_group,
        "systemd_main_pid": observed_main_pid,
        "live_systemd_unit_properties": live_unit,
        "systemd_unit_properties_exact": True,
        "observed_service_argv": observed_service_argv,
        "observed_environment": observed_environment,
        "exact_live_file_descriptors": [0, 1, 2],
        "stdin_stdout_stderr_are_systemd_null_devices": True,
        "first_service_resource_gate": gate,
        "fixed_remote_root_state": "ABSENT",
        "scratch_state": "EXACT_DIRECTORY",
        "published_as_first_systemd_service_mutation": True,
        "published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "ledger_and_parent_fsynced_before_staging_or_fixed_root_effect": True,
        "published_before_publish_ready_or_fixed_root_rename": True,
        "same_service_identity_retry_forbidden": True,
    }
    return {
        **payload,
        "remote_activation_service_receipt_id": _content_id(
            DOMAIN_PREFIX + "remote-activation-service-receipt", payload
        ),
    }


def verify_remote_activation_service_receipt_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    activation_plan: dict[str, Any],
    remote_attempt: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "activation service receipt")
    gate = document.get("first_service_resource_gate")
    if type(gate) is not dict:
        _fail("activation service receipt omitted resource gate")
    expected = build_remote_activation_service_receipt_v42r1(
        activation_plan=activation_plan,
        remote_attempt=remote_attempt,
        observed_service_argv=document.get("observed_service_argv"),
        observed_environment=document.get("observed_environment"),
        systemd_unit_name=document.get("systemd_unit_name"),
        systemd_invocation_id=document.get("systemd_invocation_id"),
        systemd_control_group=document.get("systemd_control_group"),
        observed_main_pid=document.get("systemd_main_pid"),
        observed_systemd_unit_properties=document.get(
            "live_systemd_unit_properties"
        ),
        memory_total_bytes=gate.get("memory_total_bytes"),
        memory_available_bytes=gate.get("memory_available_bytes"),
        swap_total_bytes=gate.get("swap_total_bytes"),
        swap_free_bytes=gate.get("swap_free_bytes"),
        filesystem_available_bytes=gate.get("filesystem_available_bytes"),
        cgroup_memory_ancestry=gate.get("cgroup_memory_ancestry"),
    )
    if document != expected:
        _fail("activation service receipt identity changed")
    return document


def _same_inode_before_publish(
    before: dict[str, Any], after: dict[str, Any], *, label: str
) -> None:
    fields = (
        "node_type",
        "st_dev",
        "st_ino",
        "mode",
        "uid",
        "gid",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(before.get(field) != after.get(field) for field in fields):
        _fail(f"{label} changed before publish")


def _same_inode_after_rename(
    before: dict[str, Any], after: dict[str, Any], *, label: str
) -> None:
    # rename(2) legitimately updates the renamed directory inode's ctime.
    # Content bytes and directory entries are separately protected by exact
    # inventory/hash checks, so continuity across the rename is the stable
    # inode/storage identity excluding that kernel-updated timestamp.
    fields = (
        "node_type",
        "st_dev",
        "st_ino",
        "mode",
        "uid",
        "gid",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
    )
    if any(before.get(field) != after.get(field) for field in fields):
        _fail(f"{label} was not the same inode after rename")


def build_remote_activation_publish_ready_v42r1(
    *,
    activation_plan: dict[str, Any],
    remote_attempt: dict[str, Any],
    service_receipt: dict[str, Any],
    preformal_receipt: dict[str, Any],
    live_scratch_snapshot: dict[str, Any],
    memory_total_bytes: int,
    memory_available_bytes: int,
    swap_total_bytes: int,
    swap_free_bytes: int,
    filesystem_available_bytes: int,
    cgroup_memory_ancestry: list[dict[str, Any]],
) -> dict[str, Any]:
    receipt = verify_remote_activation_service_receipt_v42r1(
        service_receipt,
        activation_plan=activation_plan,
        remote_attempt=remote_attempt,
    )
    snapshot = verify_exact_five_live_snapshot_v42r1(
        live_scratch_snapshot,
        preformal_receipt=preformal_receipt,
        root_path=activation_plan["preformal_scratch_root"],
    )
    selected = activation_plan["selected_remote_snapshot"]
    _same_inode_before_publish(
        selected["scratch_root_identity"],
        snapshot["root_identity"],
        label="selected scratch root before publish",
    )
    for old, new in zip(
        selected["control_identities"], snapshot["control_facts"], strict=True
    ):
        if (
            old["name"] != new["name"]
            or old["sha256"] != new["sha256"]
            or old["byte_count"] != new["byte_count"]
        ):
            _fail("selected scratch control content changed before publish")
        _same_inode_before_publish(
            old["identity"], new["identity"], label=f"scratch control {old['name']}"
        )
    gate = _service_resource_gate(
        activation_plan=activation_plan,
        stage="SYSTEMD_SERVICE_PUBLISH_GATE",
        memory_total_bytes=memory_total_bytes,
        memory_available_bytes=memory_available_bytes,
        swap_total_bytes=swap_total_bytes,
        swap_free_bytes=swap_free_bytes,
        filesystem_available_bytes=filesystem_available_bytes,
        cgroup_memory_ancestry=cgroup_memory_ancestry,
    )
    if gate["all_resource_gates_passed"] is not True:
        _fail("publish ready cannot follow a failed second resource gate")
    payload = {
        **_base_payload(REMOTE_ACTIVATION_PUBLISH_READY_SCHEMA),
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "remote_materialization_activation_attempt_id": remote_attempt[
            "remote_materialization_activation_attempt_id"
        ],
        "remote_activation_service_receipt_id": receipt[
            "remote_activation_service_receipt_id"
        ],
        "preformal_upload_receipt_id": activation_plan[
            "preformal_upload_receipt_id"
        ],
        "source_manifest_id": activation_plan["source_manifest_id"],
        "transport_manifest_id": activation_plan["transport_manifest_id"],
        "second_service_resource_gate": gate,
        "live_scratch_snapshot": snapshot,
        "fixed_remote_root_state": "ABSENT",
        "scratch_and_fixed_root_share_one_pinned_parent": True,
        "all_scratch_files_hashed_and_fsynced_through_pinned_descriptors": True,
        "scratch_root_and_shared_parent_fsynced_before_ready": True,
        "ready_published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "ledger_and_shared_parent_fsynced_after_ready": True,
        "root_rename_noreplace_not_started_before_ready_durable": True,
        "failure_publication_forbidden_after_ready": True,
        "same_activation_identity_retry_forbidden": True,
    }
    return {
        **payload,
        "remote_activation_publish_ready_id": _content_id(
            DOMAIN_PREFIX + "remote-activation-publish-ready", payload
        ),
    }


def verify_remote_activation_publish_ready_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    activation_plan: dict[str, Any],
    remote_attempt: dict[str, Any],
    service_receipt: dict[str, Any],
    preformal_receipt: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "activation publish ready")
    gate = document.get("second_service_resource_gate")
    if type(gate) is not dict:
        _fail("activation publish ready omitted its second resource gate")
    expected = build_remote_activation_publish_ready_v42r1(
        activation_plan=activation_plan,
        remote_attempt=remote_attempt,
        service_receipt=service_receipt,
        preformal_receipt=preformal_receipt,
        live_scratch_snapshot=document.get("live_scratch_snapshot"),
        memory_total_bytes=gate.get("memory_total_bytes"),
        memory_available_bytes=gate.get("memory_available_bytes"),
        swap_total_bytes=gate.get("swap_total_bytes"),
        swap_free_bytes=gate.get("swap_free_bytes"),
        filesystem_available_bytes=gate.get("filesystem_available_bytes"),
        cgroup_memory_ancestry=gate.get("cgroup_memory_ancestry"),
    )
    if document != expected:
        _fail("activation publish ready identity changed")
    return document


def build_remote_materialization_transport_terminal_v42r1(
    *,
    activation_plan: dict[str, Any],
    remote_attempt: dict[str, Any],
    service_receipt: dict[str, Any],
    publish_ready: dict[str, Any],
    preformal_receipt: dict[str, Any],
    fixed_root_snapshot: dict[str, Any],
) -> dict[str, Any]:
    ready = verify_remote_activation_publish_ready_v42r1(
        publish_ready,
        activation_plan=activation_plan,
        remote_attempt=remote_attempt,
        service_receipt=service_receipt,
        preformal_receipt=preformal_receipt,
    )
    fixed = verify_exact_five_live_snapshot_v42r1(
        fixed_root_snapshot,
        preformal_receipt=preformal_receipt,
        root_path=activation_plan["fixed_remote_root"],
    )
    scratch = ready["live_scratch_snapshot"]
    _same_inode_after_rename(
        scratch["root_identity"], fixed["root_identity"], label="fixed remote root"
    )
    for before, after in zip(
        scratch["control_facts"], fixed["control_facts"], strict=True
    ):
        if (
            before["name"] != after["name"]
            or before["sha256"] != after["sha256"]
            or before["byte_count"] != after["byte_count"]
        ):
            _fail("fixed-root control bytes changed across rename")
        # Renaming the containing directory does not mutate ordinary control
        # file metadata; retain the strict immutable-file comparator here.
        _same_inode_before_publish(
            before["identity"], after["identity"], label=before["name"]
        )
    payload = {
        **_base_payload(REMOTE_MATERIALIZATION_TRANSPORT_TERMINAL_SCHEMA),
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "remote_materialization_activation_attempt_id": remote_attempt[
            "remote_materialization_activation_attempt_id"
        ],
        "remote_activation_service_receipt_id": service_receipt[
            "remote_activation_service_receipt_id"
        ],
        "remote_activation_publish_ready_id": ready[
            "remote_activation_publish_ready_id"
        ],
        "preformal_upload_receipt_id": activation_plan[
            "preformal_upload_receipt_id"
        ],
        "source_manifest_id": activation_plan["source_manifest_id"],
        "transport_manifest_id": activation_plan["transport_manifest_id"],
        "local_materialization_attempt_id": activation_plan[
            "local_materialization_attempt_id"
        ],
        "fixed_root_snapshot": fixed,
        "scratch_root_state": "ABSENT",
        "fixed_remote_root_state": "EXACT_DIRECTORY",
        "fixed_root_publish_method": "RENAMEAT2_NOREPLACE_SAME_PARENT",
        "root_rename_noreplace_completed": True,
        "shared_parent_fsync_completed_after_rename": True,
        "fixed_root_postpublish_pinned_whole_tree_reverify_completed": True,
        "terminal_published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "ledger_and_shared_parent_fsynced_after_terminal": True,
        "trusted_bootstrap_outer_command": activation_plan[
            "trusted_bootstrap_outer_command"
        ],
        "terminal_verified_by_service_before_exact_outer_exec": True,
        "terminal_id_and_canonical_bytes_reverified_by_same_service_context_before_exec": True,
        "trusted_bootstrap_outer_exec_started_at_terminal_publication": False,
        "durable_terminal_authorizes_same_service_context_next_step_exact_outer_exec": True,
        "downstream_launcher_evidence_terminal_id_join_is_defense_in_depth": True,
        "downstream_launcher_evidence_terminal_id_join_implemented": False,
        "formal_outer_exec_enabled_after_service_successor_join": True,
        "transport_classification": CLASSIFICATION_SUCCESS,
        "same_activation_identity_retry_forbidden": True,
    }
    return {
        **payload,
        "remote_materialization_transport_terminal_id": _content_id(
            DOMAIN_PREFIX + "remote-materialization-transport-terminal", payload
        ),
    }


def verify_remote_materialization_transport_terminal_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    activation_plan: dict[str, Any],
    remote_attempt: dict[str, Any],
    service_receipt: dict[str, Any],
    publish_ready: dict[str, Any],
    preformal_receipt: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "materialization transport terminal")
    expected = build_remote_materialization_transport_terminal_v42r1(
        activation_plan=activation_plan,
        remote_attempt=remote_attempt,
        service_receipt=service_receipt,
        publish_ready=publish_ready,
        preformal_receipt=preformal_receipt,
        fixed_root_snapshot=document.get("fixed_root_snapshot"),
    )
    if document != expected:
        _fail("materialization transport terminal identity changed")
    return document


ACTIVATION_FAILURE_STAGES = (
    "INGRESS_BEFORE_SYSTEMD_RUN",
    "SYSTEMD_ADMISSION_BEFORE_SERVICE_RECEIPT",
    "SERVICE_AFTER_RECEIPT_BEFORE_READY",
)


def build_remote_materialization_activation_failure_v42r1(
    *,
    activation_plan: dict[str, Any],
    remote_attempt: dict[str, Any],
    service_receipt: dict[str, Any] | None,
    failure_stage: str,
    failure_classification: str,
    failure_message: str,
) -> dict[str, Any]:
    _require_document_identity(
        remote_attempt,
        schema=REMOTE_MATERIALIZATION_ACTIVATION_ATTEMPT_SCHEMA,
        identity_field="remote_materialization_activation_attempt_id",
        domain=DOMAIN_PREFIX + "remote-materialization-activation-attempt",
    )
    if failure_stage not in ACTIVATION_FAILURE_STAGES:
        _fail("activation failure stage changed")
    if (service_receipt is None) != (
        failure_stage != "SERVICE_AFTER_RECEIPT_BEFORE_READY"
    ):
        _fail("activation failure/service receipt stage join changed")
    receipt_id: str | None
    if service_receipt is None:
        receipt_id = None
    else:
        receipt = verify_remote_activation_service_receipt_v42r1(
            service_receipt,
            activation_plan=activation_plan,
            remote_attempt=remote_attempt,
        )
        receipt_id = receipt["remote_activation_service_receipt_id"]
    if (
        type(failure_classification) is not str
        or not failure_classification
        or len(failure_classification.encode("utf-8")) > 256
        or type(failure_message) is not str
        or not failure_message
        or len(failure_message.encode("utf-8")) > 4096
    ):
        _fail("activation failure detail changed")
    payload = {
        **_base_payload(REMOTE_MATERIALIZATION_ACTIVATION_FAILURE_SCHEMA),
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "remote_materialization_activation_attempt_id": remote_attempt[
            "remote_materialization_activation_attempt_id"
        ],
        "remote_activation_service_receipt_id": receipt_id,
        "preformal_upload_receipt_id": activation_plan[
            "preformal_upload_receipt_id"
        ],
        "source_manifest_id": activation_plan["source_manifest_id"],
        "transport_manifest_id": activation_plan["transport_manifest_id"],
        "failure_stage": failure_stage,
        "failure_classification": failure_classification,
        "failure_message": failure_message,
        "publish_ready_state": "ABSENT",
        "fixed_remote_root_state": "ABSENT",
        "fixed_root_publish_started": False,
        "root_rename_noreplace_called": False,
        "trusted_bootstrap_outer_exec_started": False,
        "failure_published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "ledger_and_shared_parent_fsynced_after_failure": True,
        "same_activation_identity_retry_forbidden": True,
        "read_only_followup_only": True,
    }
    return {
        **payload,
        "remote_materialization_activation_failure_id": _content_id(
            DOMAIN_PREFIX + "remote-materialization-activation-failure", payload
        ),
    }


def verify_remote_materialization_activation_failure_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    activation_plan: dict[str, Any],
    remote_attempt: dict[str, Any],
    service_receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "materialization activation failure")
    expected = build_remote_materialization_activation_failure_v42r1(
        activation_plan=activation_plan,
        remote_attempt=remote_attempt,
        service_receipt=service_receipt,
        failure_stage=document.get("failure_stage"),
        failure_classification=document.get("failure_classification"),
        failure_message=document.get("failure_message"),
    )
    if document != expected:
        _fail("materialization activation failure identity changed")
    return document


def _classification_observation(value: object) -> dict[str, Any]:
    keys = {
        "fixed_remote_root_state",
        "preformal_scratch_root_state",
        "preformal_ledger_stage_state",
        "fixed_transport_ledger_state",
        "fixed_transport_ledger_inventory",
        "systemd_unit_state",
        "systemd_unit_properties_exact",
        "all_paths_observed_nofollow",
        "whole_tree_first_last_snapshot_equal",
    }
    if type(value) is not dict or set(value) != keys:
        _fail("activation classification observation schema changed")
    for field in (
        "fixed_remote_root_state",
        "preformal_scratch_root_state",
        "preformal_ledger_stage_state",
        "fixed_transport_ledger_state",
    ):
        if value[field] not in PATH_STATES:
            _fail("activation classification path state changed")
    if value["systemd_unit_state"] not in UNIT_STATES:
        _fail("activation classification unit state changed")
    inventory = value["fixed_transport_ledger_inventory"]
    if (
        type(inventory) is not list
        or any(type(name) is not str or not name for name in inventory)
        or inventory != sorted(set(inventory))
    ):
        _fail("activation classification ledger inventory changed")
    for field in (
        "systemd_unit_properties_exact",
        "all_paths_observed_nofollow",
        "whole_tree_first_last_snapshot_equal",
    ):
        if type(value[field]) is not bool:
            _fail("activation classification observation boolean changed")
    return dict(value)


def _expected_ledger_inventory(
    *,
    remote_attempt: dict[str, Any] | None,
    service_receipt: dict[str, Any] | None,
    publish_ready: dict[str, Any] | None,
    terminal: dict[str, Any] | None,
    failure: dict[str, Any] | None,
) -> list[str]:
    if remote_attempt is None:
        return []
    result = [REMOTE_ACTIVATION_ATTEMPT_NAME, REMOTE_ACTIVATION_SERVICE_SOURCE_NAME]
    if service_receipt is not None:
        result.append(REMOTE_ACTIVATION_SERVICE_RECEIPT_NAME)
    if publish_ready is not None:
        result.append(REMOTE_ACTIVATION_READY_NAME)
    if terminal is not None:
        result.append(REMOTE_ACTIVATION_TERMINAL_NAME)
    if failure is not None:
        result.append(REMOTE_ACTIVATION_FAILURE_NAME)
    return sorted(result)


def build_materialization_activation_classification_v42r1(
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
    preformal_receipt: dict[str, Any],
    remote_attempt: dict[str, Any] | None,
    service_receipt: dict[str, Any] | None,
    publish_ready: dict[str, Any] | None,
    terminal: dict[str, Any] | None,
    failure: dict[str, Any] | None,
    observation_before: dict[str, Any],
    observation_after: dict[str, Any],
) -> dict[str, Any]:
    local_attempt = verify_local_materialization_activation_attempt_v42r1(
        local_attempt, activation_plan=activation_plan
    )
    network_start = verify_materialization_activation_network_start_v42r1(
        network_start,
        activation_plan=activation_plan,
        local_attempt=local_attempt,
    )
    before = _classification_observation(observation_before)
    after = _classification_observation(observation_after)
    reason = "NO_REMOTE_ACTIVATION_ATTEMPT_OBSERVED_AFTER_NETWORK_CUT"
    classification = CLASSIFICATION_AMBIGUOUS
    remote_id: str | None = None
    receipt_id: str | None = None
    ready_id: str | None = None
    terminal_id: str | None = None
    failure_id: str | None = None

    if before != after or not after["whole_tree_first_last_snapshot_equal"]:
        reason = "REMOTE_STATE_CHANGED_DURING_READ_ONLY_CLASSIFICATION"
    elif not after["all_paths_observed_nofollow"]:
        reason = "REMOTE_STATE_WAS_NOT_OBSERVABLE_NOFOLLOW"
    elif terminal is not None and failure is not None:
        reason = "TERMINAL_AND_FAILURE_CONFLICT"
    else:
        if remote_attempt is not None:
            remote_attempt = verify_remote_materialization_activation_attempt_v42r1(
                remote_attempt,
                activation_plan=activation_plan,
                local_attempt=local_attempt,
                network_start=network_start,
            )
            remote_id = remote_attempt["remote_materialization_activation_attempt_id"]
        if service_receipt is not None:
            if remote_attempt is None:
                _fail("service receipt appeared without remote attempt")
            service_receipt = verify_remote_activation_service_receipt_v42r1(
                service_receipt,
                activation_plan=activation_plan,
                remote_attempt=remote_attempt,
            )
            receipt_id = service_receipt["remote_activation_service_receipt_id"]
        if publish_ready is not None:
            if remote_attempt is None or service_receipt is None:
                _fail("publish ready appeared without its predecessors")
            publish_ready = verify_remote_activation_publish_ready_v42r1(
                publish_ready,
                activation_plan=activation_plan,
                remote_attempt=remote_attempt,
                service_receipt=service_receipt,
                preformal_receipt=preformal_receipt,
            )
            ready_id = publish_ready["remote_activation_publish_ready_id"]
        if terminal is not None:
            if remote_attempt is None or service_receipt is None or publish_ready is None:
                _fail("transport terminal appeared without its predecessors")
            terminal = verify_remote_materialization_transport_terminal_v42r1(
                terminal,
                activation_plan=activation_plan,
                remote_attempt=remote_attempt,
                service_receipt=service_receipt,
                publish_ready=publish_ready,
                preformal_receipt=preformal_receipt,
            )
            terminal_id = terminal["remote_materialization_transport_terminal_id"]
        if failure is not None:
            if remote_attempt is None or publish_ready is not None or terminal is not None:
                _fail("typed activation failure appeared outside its safe branch")
            failure = verify_remote_materialization_activation_failure_v42r1(
                failure,
                activation_plan=activation_plan,
                remote_attempt=remote_attempt,
                service_receipt=service_receipt,
            )
            failure_id = failure["remote_materialization_activation_failure_id"]

        expected_inventory = _expected_ledger_inventory(
            remote_attempt=remote_attempt,
            service_receipt=service_receipt,
            publish_ready=publish_ready,
            terminal=terminal,
            failure=failure,
        )
        if after["fixed_transport_ledger_inventory"] != expected_inventory:
            reason = "FIXED_LEDGER_INVENTORY_IS_PARTIAL_EXTRA_OR_CONFLICTING"
        elif remote_attempt is None:
            if not (
                after["fixed_transport_ledger_state"] == "ABSENT"
                and after["preformal_ledger_stage_state"] == "EXACT_DIRECTORY"
            ):
                reason = "REMOTE_ATTEMPT_MISSING_WITH_CHANGED_LEDGER_STATE"
        elif after["fixed_transport_ledger_state"] != "EXACT_DIRECTORY":
            reason = "REMOTE_ATTEMPT_EXISTS_WITHOUT_EXACT_FIXED_LEDGER"
        elif terminal is not None:
            if (
                after["fixed_remote_root_state"] == "EXACT_DIRECTORY"
                and after["preformal_scratch_root_state"] == "ABSENT"
            ):
                classification = CLASSIFICATION_SUCCESS
                reason = "DURABLE_TERMINAL_AND_EXACT_FIXED_FIVE_CONTROLS"
            else:
                reason = "TERMINAL_EXISTS_WITHOUT_EXACT_FIXED_ROOT_STATE"
        elif failure is not None:
            if (
                after["fixed_remote_root_state"] == "ABSENT"
                and publish_ready is None
            ):
                classification = CLASSIFICATION_FAILURE
                reason = "TYPED_PRE_READY_FAILURE_AND_FIXED_ROOT_ABSENT"
            else:
                reason = "FAILURE_EXISTS_OUTSIDE_SAFE_PRE_READY_STATE"
        elif (
            after["systemd_unit_state"] in ("ACTIVE", "ACTIVATING")
            and after["systemd_unit_properties_exact"] is True
        ):
            classification = CLASSIFICATION_IN_PROGRESS
            reason = "EXACT_UNIT_ACTIVE_READ_ONLY_WAIT"
        elif after["systemd_unit_state"] in ("ACTIVE", "ACTIVATING"):
            reason = "ACTIVE_UNIT_PROPERTIES_CHANGED"
        elif publish_ready is not None:
            reason = "READY_OR_RENAME_WINDOW_WITHOUT_DURABLE_TERMINAL"
        elif service_receipt is not None:
            reason = "SERVICE_RECEIPT_WITHOUT_READY_OR_TYPED_FAILURE"
        else:
            reason = "REMOTE_ATTEMPT_WITHOUT_SERVICE_RECEIPT_OR_TYPED_FAILURE"

    payload = {
        **_base_payload(MATERIALIZATION_ACTIVATION_CLASSIFICATION_SCHEMA),
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "local_materialization_activation_attempt_id": local_attempt[
            "local_materialization_activation_attempt_id"
        ],
        "materialization_activation_network_start_id": network_start[
            "materialization_activation_network_start_id"
        ],
        "remote_materialization_activation_attempt_id": remote_id,
        "remote_activation_service_receipt_id": receipt_id,
        "remote_activation_publish_ready_id": ready_id,
        "remote_materialization_transport_terminal_id": terminal_id,
        "remote_materialization_activation_failure_id": failure_id,
        "classification": classification,
        "reason": reason,
        "observation": after,
        "read_only_remote_observation_only": True,
        "remote_mutation_performed_by_classifier": False,
        "only_read_only_ssh_ingress_and_systemctl_query_processes_started": True,
        "additional_durable_or_mutating_remote_process_started_by_classifier": False,
        "activation_retry_authorized": False,
        "read_only_classification_may_be_repeated": True,
        "unit_absence_does_not_prove_service_never_started": True,
    }
    return {
        **payload,
        "materialization_activation_classification_id": _content_id(
            DOMAIN_PREFIX + "materialization-activation-classification", payload
        ),
    }


def verify_materialization_activation_classification_v42r1(
    raw_or_document: bytes | dict[str, Any], **build_arguments: Any
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "activation classification")
    expected = build_materialization_activation_classification_v42r1(**build_arguments)
    if document != expected:
        _fail("activation classification identity changed")
    return document


__all__ = [name for name in globals() if name.endswith("_v42r1") or name.isupper()]
