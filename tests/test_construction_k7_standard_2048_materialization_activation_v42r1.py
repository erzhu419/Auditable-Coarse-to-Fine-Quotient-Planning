from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any

import pytest

from acfqp import (
    construction_k7_standard_2048_materialization_activation_v42r1 as activation,
)
from acfqp import (
    construction_k7_standard_2048_materialization_transport_v42r1 as preformal,
)
from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from scripts import v42_materialization_activation_service as activation_service
from scripts import v42_materialization_activation_receiver as activation_receiver
from scripts import v42_materialization_activation_loader as activation_loader
from scripts import run_v42_materialization_activation as activation_driver
from tests.test_construction_k7_standard_2048_materialization_transport_v42r1 import (
    _attempt as _preformal_attempt,
)
from tests.test_construction_k7_standard_2048_materialization_transport_v42r1 import (
    _control_file_facts as _preformal_control_file_facts,
)
from tests.test_construction_k7_standard_2048_materialization_transport_v42r1 import (
    _context as _preformal_context,
)
from tests.test_construction_k7_standard_2048_materialization_transport_v42r1 import (
    _plan as _preformal_plan,
)
from tests.test_construction_k7_standard_2048_materialization_transport_v42r1 import (
    _parent_fact as _preformal_parent_fact,
)
from tests.test_construction_k7_standard_2048_materialization_transport_v42r1 import (
    _private_directory_fact as _preformal_private_directory_fact,
)
from tests.test_construction_k7_standard_2048_materialization_transport_v42r1 import (
    _receipt as _preformal_receipt,
)


_LOADER_RAW = b"# activation loader fixture\n"
_RECEIVER_RAW = b"# activation receiver fixture\n"
_SERVICE_RAW = b"# activation service fixture\n"
_DRIVER_RAW = b"# activation driver fixture\n"
_ACTIVATION_AUTHORITY_RAW = b"# activation authority fixture\n"

_ACTIVATION_PROGRAMS = {
    "scripts/v42_materialization_activation_loader.py": _LOADER_RAW,
    "scripts/v42_materialization_activation_receiver.py": _RECEIVER_RAW,
    "scripts/v42_materialization_activation_service.py": _SERVICE_RAW,
    "scripts/run_v42_materialization_activation.py": _DRIVER_RAW,
    (
        "src/acfqp/"
        "construction_k7_standard_2048_materialization_activation_v42r1.py"
    ): _ACTIVATION_AUTHORITY_RAW,
}


def _identity(
    path: str,
    *,
    inode: int,
    mode: int,
    size: int,
    node_type: str,
) -> dict[str, Any]:
    return {
        "path": path,
        "node_type": node_type,
        "st_dev": 7,
        "st_ino": inode,
        "mode": mode,
        "uid": authority.REMOTE_UID,
        "gid": authority.REMOTE_GID,
        "st_nlink": 1 if node_type == "REGULAR_FILE" else 2,
        "st_size": size,
        "st_mtime_ns": 1_000_000 + inode,
        "st_ctime_ns": 2_000_000 + inode,
    }


def _selected_preformal() -> dict[str, Any]:
    original = _preformal_context()["control_raw_by_name"]
    source = loads_canonical_json(original[authority.SOURCE_MANIFEST_NAME])
    transport_manifest = loads_canonical_json(
        original[authority.TRANSPORT_MANIFEST_NAME]
    )
    transport_facts = list(transport_manifest["transport_facts"])
    for relative_path, raw in _ACTIVATION_PROGRAMS.items():
        fact = {
            "relative_path": relative_path,
            "git_mode": "100644",
            "git_object_type": "blob",
            "git_blob_oid": hashlib.sha1(  # noqa: S324 - Git object identity
                f"blob {len(raw)}\0".encode("ascii") + raw
            ).hexdigest(),
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        transport_facts.append(fact)
    transport_manifest = authority.build_transport_manifest_v42r1(
        source_manifest=source,
        transport_facts=sorted(
            transport_facts, key=lambda row: row["relative_path"]
        ),
        source_archive_sha256=transport_manifest["source_archive_sha256"],
        source_archive_byte_count=transport_manifest["source_archive_byte_count"],
        remote_bootstrap_pyz_artifact=transport_manifest[
            "remote_bootstrap_pyz_artifact"
        ],
    )
    local_materialization_attempt = authority.build_local_materialization_attempt_v42r1(
        source_manifest=source, transport_manifest=transport_manifest
    )
    controls = dict(original)
    controls[authority.SOURCE_MANIFEST_NAME] = canonical_json_bytes(source)
    controls[authority.TRANSPORT_MANIFEST_NAME] = canonical_json_bytes(
        transport_manifest
    )
    controls[authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME] = canonical_json_bytes(
        local_materialization_attempt
    )
    context = {
        **_preformal_context(),
        "control_raw_by_name": controls,
    }
    plan = preformal.build_preformal_upload_plan_v42r1(
        **context,
        upload_token=hashlib.sha256(b"activation-preformal-token").hexdigest(),
    )
    attempt = preformal.build_preformal_upload_attempt_v42r1(
        plan=plan, **context
    )
    receipt = preformal.build_preformal_upload_receipt_v42r1(
        plan=plan,
        attempt=attempt,
        scratch_parent_fact=_preformal_parent_fact(),
        scratch_root_fact=_preformal_private_directory_fact(
            plan["preformal_scratch_root"]
        ),
        ledger_stage_fact=_preformal_private_directory_fact(
            plan["preformal_ledger_stage_root"]
        ),
        observed_control_file_facts=_preformal_control_file_facts(plan),
        **context,
    )
    outcome = preformal.build_preformal_upload_outcome_v42r1(
        plan=plan,
        attempt=attempt,
        receipt=receipt,
        outcome_class=preformal.PREFORMAL_OUTCOME_COMPLETE,
        **context,
    )
    return {
        "plan": plan,
        "attempt": attempt,
        "receipt": receipt,
        "outcome": outcome,
        "controls": controls,
    }


def _selected_snapshot(receipt: dict[str, Any]) -> dict[str, Any]:
    controls = receipt["observed_control_file_facts"]
    return activation.build_selected_remote_snapshot_v42r1(
        preformal_receipt=receipt,
        parent_identity=_identity(
            receipt["scratch_parent_fact"]["path"],
            inode=10,
            mode=receipt["scratch_parent_fact"]["mode"],
            size=4096,
            node_type="DIRECTORY",
        ),
        scratch_identity=_identity(
            receipt["scratch_root_fact"]["path"],
            inode=11,
            mode=0o700,
            size=4096,
            node_type="DIRECTORY",
        ),
        ledger_stage_identity=_identity(
            receipt["ledger_stage_fact"]["path"],
            inode=12,
            mode=0o700,
            size=4096,
            node_type="DIRECTORY",
        ),
        control_identities=[
            _identity(
                row["path"],
                inode=100 + index,
                mode=0o400,
                size=row["byte_count"],
                node_type="REGULAR_FILE",
            )
            for index, row in enumerate(controls)
        ],
    )


def _resource_values() -> dict[str, Any]:
    return {
        "memory_total_bytes": activation.MINIMUM_MEMORY_TOTAL_BYTES + 1024**3,
        "memory_available_bytes": activation.MINIMUM_MEMORY_AVAILABLE_BYTES + 1024**3,
        "swap_total_bytes": 0,
        "swap_free_bytes": 0,
        "filesystem_available_bytes": activation.MINIMUM_FILESYSTEM_AVAILABLE_BYTES
        + 1024**3,
        "cgroup_memory_ancestry": [
            {
                "cgroup_path": "/user.slice/user-1000.slice/app.scope",
                "memory_max_mode": "FINITE",
                "memory_max_bytes": activation.MINIMUM_MEMORY_TOTAL_BYTES + 2 * 1024**3,
                "memory_current_bytes": 1024**3,
            },
            {
                "cgroup_path": "/",
                "memory_max_mode": "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES",
                "memory_max_bytes": None,
                "memory_current_bytes": None,
            },
        ],
    }


def _python_observation(resource_plan: dict[str, Any]) -> dict[str, Any]:
    startup = resource_plan["remote_startup_tcb_contract"]
    return {
        key: startup[key]
        for key in (
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
    }


def _systemd_runtime(
    plan: dict[str, Any], remote_attempt: dict[str, Any]
) -> tuple[str, str, int, dict[str, Any]]:
    unit = activation.materialize_activation_unit_name_v42r1(
        plan["materialization_activation_plan_id"]
    )
    invocation = "1" * 32
    group = f"/user.slice/user-1000.slice/app.slice/{unit}"
    pid = 4242
    properties = {
        "Id": unit,
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "running",
        "FragmentPath": f"/run/user/{authority.REMOTE_UID}/systemd/transient/{unit}",
        "MainPID": pid,
        "InvocationID": invocation,
        "ControlGroup": group,
        "Type": "exec",
        "bootstrap_argv_verified_by_tiny_loader_before_clean_exec": True,
        "StandardInput": "null",
        "StandardOutput": "null",
        "StandardError": "null",
        "Restart": "no",
        "UMask": "0077",
        "KillMode": "control-group",
        "RuntimeMaxUSec": "1w",
        "WorkingDirectory": str(Path(plan["fixed_remote_root"]).parent),
        "Slice": "app.slice",
        "invocation_symlink_verified": True,
        "observed_via_pinned_systemctl_executable": True,
        "systemctl_argv": activation.materialize_authorized_systemctl_argv_v42r1(
            activation_plan=plan
        ),
    }
    return invocation, group, pid, properties


def _replace_strings(value: Any, old: str, new: str) -> Any:
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, list):
        return [_replace_strings(item, old, new) for item in value]
    if isinstance(value, dict):
        return {key: _replace_strings(item, old, new) for key, item in value.items()}
    return value


def _rehash(document: dict[str, Any], identity: str, domain: str) -> dict[str, Any]:
    payload = dict(document)
    payload.pop(identity, None)
    return {
        **payload,
        identity: hashlib.sha256(
            domain.encode("ascii") + b"\0" + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _live_identity(path: Path, node_type: str) -> dict[str, Any]:
    observed = path.lstat()
    return {
        "path": str(path),
        "node_type": node_type,
        "st_dev": observed.st_dev,
        "st_ino": observed.st_ino,
        "mode": observed.st_mode & 0o7777,
        "uid": observed.st_uid,
        "gid": observed.st_gid,
        "st_nlink": observed.st_nlink,
        "st_size": observed.st_size,
        "st_mtime_ns": observed.st_mtime_ns,
        "st_ctime_ns": observed.st_ctime_ns,
    }


def _offline_effect_fixture(parent: Path) -> dict[str, Any]:
    chain = _chain()
    old_parent = str(Path(chain["activation_plan"]["fixed_remote_root"]).parent)
    os.chmod(parent, 0o775)
    scratch = parent / Path(chain["activation_plan"]["preformal_scratch_root"]).name
    stage = parent / Path(chain["activation_plan"]["preformal_ledger_stage_root"]).name
    scratch.mkdir(mode=0o700)
    stage.mkdir(mode=0o700)
    for name, raw in chain["controls"].items():
        path = scratch / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
        try:
            os.write(descriptor, raw)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.chmod(path, 0o400)
    relocated_receipt = _replace_strings(chain["receipt"], old_parent, str(parent))
    relocated_receipt = _rehash(
        relocated_receipt,
        "preformal_upload_receipt_id",
        "acfqp:v42-remote-ordinal2:preformal-upload-receipt",
    )
    plan = _replace_strings(chain["activation_plan"], old_parent, str(parent))
    plan["preformal_upload_receipt_id"] = relocated_receipt[
        "preformal_upload_receipt_id"
    ]
    snapshot = activation.build_selected_remote_snapshot_v42r1(
        preformal_receipt=relocated_receipt,
        parent_identity=_live_identity(parent, "DIRECTORY"),
        scratch_identity=_live_identity(scratch, "DIRECTORY"),
        ledger_stage_identity=_live_identity(stage, "DIRECTORY"),
        control_identities=[
            _live_identity(scratch / row["name"], "REGULAR_FILE")
            for row in relocated_receipt["observed_control_file_facts"]
        ],
    )
    plan["selected_remote_snapshot"] = snapshot
    plan = _rehash(
        plan,
        "materialization_activation_plan_id",
        "acfqp:v42-remote-ordinal2:materialization-activation-plan",
    )
    local = activation.build_local_materialization_activation_attempt_v42r1(
        activation_plan=plan, local_effective_uid=os.geteuid()
    )
    network = activation.build_materialization_activation_network_start_v42r1(
        activation_plan=plan, local_attempt=local
    )
    ingress_argv = activation.materialize_authorized_remote_ingress_argv_v42r1(
        activation_plan=plan,
        local_activation_attempt_id=local[
            "local_materialization_activation_attempt_id"
        ],
    )
    remote = activation.build_remote_materialization_activation_attempt_v42r1(
        activation_plan=plan,
        local_attempt=local,
        network_start=network,
        observed_remote_snapshot=snapshot,
        observed_remote_ingress_argv=ingress_argv,
        observed_hostname=authority.REMOTE_HOSTNAME,
        observed_user=authority.REMOTE_USER,
        observed_uid=authority.REMOTE_UID,
        observed_gid=authority.REMOTE_GID,
    )
    return {
        "plan": plan,
        "local": local,
        "network": network,
        "remote": remote,
        "receipt": relocated_receipt,
        "scratch": scratch,
        "stage": stage,
        "fixed": Path(plan["fixed_remote_root"]),
        "ledger": Path(plan["fixed_transport_ledger_root"]),
        "service_raw": _SERVICE_RAW,
        "receiver_sha": hashlib.sha256(_RECEIVER_RAW).hexdigest(),
        "ingress_argv": ingress_argv,
    }


def _chain() -> dict[str, Any]:
    selected = _selected_preformal()
    resource_plan = activation.build_preactivation_resource_probe_plan_v42r1(
        preformal_plan=selected["plan"],
        preformal_attempt=selected["attempt"],
        preformal_receipt=selected["receipt"],
        preformal_outcome=selected["outcome"],
        loader_source_raw=_LOADER_RAW,
        receiver_source_raw=_RECEIVER_RAW,
        service_source_raw=_SERVICE_RAW,
        driver_source_raw=_DRIVER_RAW,
        activation_authority_source_raw=_ACTIVATION_AUTHORITY_RAW,
        control_raw_by_name=selected["controls"],
    )
    snapshot = _selected_snapshot(selected["receipt"])
    resource_result = activation.build_preactivation_resource_result_v42r1(
        resource_plan=resource_plan,
        preformal_receipt=selected["receipt"],
        stage="READ_ONLY_PREACTIVATION_PROBE",
        observed_hostname=authority.REMOTE_HOSTNAME,
        observed_user=authority.REMOTE_USER,
        observed_uid=authority.REMOTE_UID,
        observed_gid=authority.REMOTE_GID,
        observed_python=_python_observation(resource_plan),
        selected_remote_snapshot=snapshot,
        **_resource_values(),
    )
    plan = activation.build_materialization_activation_plan_v42r1(
        preformal_plan=selected["plan"],
        preformal_attempt=selected["attempt"],
        preformal_receipt=selected["receipt"],
        preformal_outcome=selected["outcome"],
        resource_plan=resource_plan,
        resource_result=resource_result,
        control_raw_by_name=selected["controls"],
        loader_source_raw=_LOADER_RAW,
        receiver_source_raw=_RECEIVER_RAW,
        service_source_raw=_SERVICE_RAW,
        driver_source_raw=_DRIVER_RAW,
        activation_authority_source_raw=_ACTIVATION_AUTHORITY_RAW,
    )
    local_attempt = activation.build_local_materialization_activation_attempt_v42r1(
        activation_plan=plan, local_effective_uid=authority.REMOTE_UID
    )
    network_start = activation.build_materialization_activation_network_start_v42r1(
        activation_plan=plan, local_attempt=local_attempt
    )
    remote_attempt = activation.build_remote_materialization_activation_attempt_v42r1(
        activation_plan=plan,
        local_attempt=local_attempt,
        network_start=network_start,
        observed_remote_snapshot=snapshot,
        observed_remote_ingress_argv=(
            activation.materialize_authorized_remote_ingress_argv_v42r1(
                activation_plan=plan,
                local_activation_attempt_id=local_attempt[
                    "local_materialization_activation_attempt_id"
                ],
            )
        ),
        observed_hostname=authority.REMOTE_HOSTNAME,
        observed_user=authority.REMOTE_USER,
        observed_uid=authority.REMOTE_UID,
        observed_gid=authority.REMOTE_GID,
    )
    invocation, group, main_pid, unit_properties = _systemd_runtime(
        plan, remote_attempt
    )
    service_receipt = activation.build_remote_activation_service_receipt_v42r1(
        activation_plan=plan,
        remote_attempt=remote_attempt,
        observed_service_argv=activation.materialize_authorized_service_argv_v42r1(
            activation_plan=plan,
            remote_activation_attempt_id=remote_attempt[
                "remote_materialization_activation_attempt_id"
            ],
            systemd_invocation_id=invocation,
            systemd_control_group=group,
        ),
        observed_environment=activation.SYSTEMD_SERVICE_ENVIRONMENT,
        systemd_unit_name=local_attempt["derived_systemd_unit_name"],
        systemd_invocation_id=invocation,
        systemd_control_group=group,
        observed_main_pid=main_pid,
        observed_systemd_unit_properties=unit_properties,
        **_resource_values(),
    )
    scratch_snapshot = activation.build_exact_five_live_snapshot_v42r1(
        preformal_receipt=selected["receipt"],
        root_path=plan["preformal_scratch_root"],
        root_identity=snapshot["scratch_root_identity"],
        control_identities=[row["identity"] for row in snapshot["control_identities"]],
    )
    ready = activation.build_remote_activation_publish_ready_v42r1(
        activation_plan=plan,
        remote_attempt=remote_attempt,
        service_receipt=service_receipt,
        preformal_receipt=selected["receipt"],
        live_scratch_snapshot=scratch_snapshot,
        **_resource_values(),
    )
    fixed_root = plan["fixed_remote_root"]
    fixed_snapshot = activation.build_exact_five_live_snapshot_v42r1(
        preformal_receipt=selected["receipt"],
        root_path=fixed_root,
        root_identity={**scratch_snapshot["root_identity"], "path": fixed_root},
        control_identities=[
            {
                **row["identity"],
                "path": str(Path(fixed_root) / row["name"]),
            }
            for row in scratch_snapshot["control_facts"]
        ],
    )
    terminal = activation.build_remote_materialization_transport_terminal_v42r1(
        activation_plan=plan,
        remote_attempt=remote_attempt,
        service_receipt=service_receipt,
        publish_ready=ready,
        preformal_receipt=selected["receipt"],
        fixed_root_snapshot=fixed_snapshot,
    )
    return {
        **selected,
        "resource_plan": resource_plan,
        "resource_result": resource_result,
        "snapshot": snapshot,
        "activation_plan": plan,
        "local_attempt": local_attempt,
        "network_start": network_start,
        "remote_attempt": remote_attempt,
        "service_receipt": service_receipt,
        "ready": ready,
        "terminal": terminal,
    }


def _bootstrap_success_documents(
    chain: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    source = loads_canonical_json(chain["controls"][authority.SOURCE_MANIFEST_NAME])
    transport = loads_canonical_json(
        chain["controls"][authority.TRANSPORT_MANIFEST_NAME]
    )
    local = loads_canonical_json(
        chain["controls"][authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME]
    )
    chain_paths = ["/"]
    current = ""
    for component in authority.REMOTE_ROOT.parts[1:]:
        current += "/" + component
        chain_paths.append(current)
    root_identity = [
        1,
        2,
        stat.S_IFDIR | 0o700,
        authority.REMOTE_UID,
        authority.REMOTE_GID,
        1,
        0,
        3,
        4,
    ]
    control_identity = [
        1,
        5,
        stat.S_IFREG | 0o400,
        authority.REMOTE_UID,
        authority.REMOTE_GID,
        1,
        1,
        3,
        4,
    ]
    launcher_evidence = authority.build_remote_bootstrap_launcher_evidence_v42r1(
        source_manifest=source,
        transport_manifest=transport,
        local_materialization_attempt=local,
        observed_outer_python_command=local["remote_bootstrap_outer_command"],
        authorized_inner_python_command=local["remote_bootstrap_inner_command"],
        observed_outer_hostname=authority.REMOTE_HOSTNAME,
        observed_outer_user=authority.REMOTE_USER,
        observed_outer_uid=authority.REMOTE_UID,
        observed_outer_gid=authority.REMOTE_GID,
        observed_outer_python_invocation=authority.REMOTE_PYTHON,
        observed_outer_python_realpath=authority.REMOTE_PYTHON_REALPATH,
        observed_outer_python_version=authority.REMOTE_PYTHON_VERSION,
        outer_python_isolated_flag=1,
        outer_python_no_site_flag=1,
        outer_python_dont_write_bytecode=True,
        outer_five_control_verification_completed=True,
        outer_pyz_nofollow_stable_hash_completed=True,
        outer_lexical_chain=[
            {"absolute_path": path, "identity": list(root_identity[:5])}
            for path in chain_paths
        ],
        outer_root_identity=list(root_identity),
        outer_root_inventory=sorted(preformal.CONTROL_NAMES),
        outer_five_control_identities={
            name: list(control_identity) for name in preformal.CONTROL_NAMES
        },
        runtime_pyz_memfd=authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_FD,
        runtime_evidence_memfd=authority.REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_FD,
        required_memfd_seals=authority.REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS,
        required_memfd_mode=authority.REMOTE_BOOTSTRAP_PYZ_FILE_MODE,
        runtime_memfd_uid=authority.REMOTE_UID,
        runtime_memfd_gid=authority.REMOTE_GID,
        runtime_memfds_inheritable_for_inner_exec=True,
        fixed_identity_effect_started=False,
    )
    pyz = transport["remote_bootstrap_pyz_artifact"]
    runtime_binding = authority.build_remote_bootstrap_runtime_binding_v42r1(
        transport,
        source_manifest=source,
        local_materialization_attempt=local,
        trusted_launcher_evidence=launcher_evidence,
        observed_hostname=authority.REMOTE_HOSTNAME,
        observed_user=authority.REMOTE_USER,
        observed_uid=authority.REMOTE_UID,
        observed_python_invocation=authority.REMOTE_PYTHON,
        observed_python_realpath=authority.REMOTE_PYTHON_REALPATH,
        observed_python_version=authority.REMOTE_PYTHON_VERSION,
        python_isolated_flag=1,
        python_no_site_flag=1,
        python_dont_write_bytecode=True,
        observed_inner_python_command=local["remote_bootstrap_inner_command"],
        observed_remote_bootstrap_pyz_fixed_path=str(
            authority.REMOTE_ROOT / authority.REMOTE_BOOTSTRAP_PYZ_NAME
        ),
        observed_remote_bootstrap_pyz_runtime_path=(
            authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH
        ),
        observed_remote_bootstrap_pyz_sha256=pyz["pyz_sha256"],
        observed_remote_bootstrap_pyz_byte_count=pyz["pyz_byte_count"],
        observed_member_manifest_id=pyz["member_manifest_id"],
        runtime_pyz_memfd_seals=authority.REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS,
        runtime_evidence_memfd_seals=authority.REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS,
        runtime_pyz_memfd_mode=authority.REMOTE_BOOTSTRAP_PYZ_FILE_MODE,
        runtime_evidence_memfd_mode=authority.REMOTE_BOOTSTRAP_PYZ_FILE_MODE,
        runtime_pyz_memfd_uid=authority.REMOTE_UID,
        runtime_pyz_memfd_gid=authority.REMOTE_GID,
        runtime_evidence_memfd_uid=authority.REMOTE_UID,
        runtime_evidence_memfd_gid=authority.REMOTE_GID,
        runtime_memfds_inheritable=True,
        observed_stdlib_module_origins=list(
            authority.REMOTE_BOOTSTRAP_STDLIB_MODULE_ORIGINS
        ),
        loaded_application_module_origins=[
            {
                **row,
                "observed_origin": (
                    authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH
                    + "/"
                    + row["archive_path"]
                ),
            }
            for row in pyz["application_module_origins"]
        ],
    )
    remote = authority.build_remote_materialization_attempt_v42r1(
        local_materialization_attempt=local,
        source_manifest=source,
        transport_manifest=transport,
        remote_bootstrap_runtime_binding=runtime_binding,
    )
    terminal = authority.build_materialization_terminal_v42r1(
        local_materialization_attempt=local,
        remote_materialization_attempt=remote,
        source_manifest=source,
        transport_manifest=transport,
    )
    return {
        authority.SOURCE_MANIFEST_NAME: source,
        authority.TRANSPORT_MANIFEST_NAME: transport,
        authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME: local,
        authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME: remote,
        authority.MATERIALIZATION_TERMINAL_NAME: terminal,
    }


def _observation(chain: dict[str, Any], *, stage: str) -> dict[str, Any]:
    names = [
        activation.REMOTE_ACTIVATION_ATTEMPT_NAME,
        activation.REMOTE_ACTIVATION_SERVICE_SOURCE_NAME,
    ]
    root = "ABSENT"
    scratch = "EXACT_DIRECTORY"
    unit = "INACTIVE"
    if stage in {"service", "ready", "terminal", "failure"}:
        names.append(activation.REMOTE_ACTIVATION_SERVICE_RECEIPT_NAME)
    if stage in {"ready", "terminal"}:
        names.append(activation.REMOTE_ACTIVATION_READY_NAME)
    if stage == "terminal":
        names.append(activation.REMOTE_ACTIVATION_TERMINAL_NAME)
        root = "EXACT_DIRECTORY"
        scratch = "ABSENT"
    if stage == "failure":
        names.append(activation.REMOTE_ACTIVATION_FAILURE_NAME)
    if stage == "active":
        unit = "ACTIVE"
    if stage == "local":
        names = []
    return {
        "fixed_remote_root_state": root,
        "preformal_scratch_root_state": scratch,
        "preformal_ledger_stage_state": (
            "EXACT_DIRECTORY" if stage == "local" else "ABSENT"
        ),
        "fixed_transport_ledger_state": (
            "ABSENT" if stage == "local" else "EXACT_DIRECTORY"
        ),
        "fixed_transport_ledger_inventory": sorted(names),
        "systemd_unit_state": unit,
        "systemd_unit_properties_exact": unit == "ACTIVE",
        "all_paths_observed_nofollow": True,
        "whole_tree_first_last_snapshot_equal": True,
    }


def _classify(
    chain: dict[str, Any],
    *,
    stage: str,
    remote: bool = True,
    service: bool = False,
    ready: bool = False,
    terminal: bool = False,
    failure: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    before = _observation(chain, stage=stage)
    return activation.build_materialization_activation_classification_v42r1(
        activation_plan=chain["activation_plan"],
        local_attempt=chain["local_attempt"],
        network_start=chain["network_start"],
        preformal_receipt=chain["receipt"],
        remote_attempt=chain["remote_attempt"] if remote else None,
        service_receipt=chain["service_receipt"] if service else None,
        publish_ready=chain["ready"] if ready else None,
        terminal=chain["terminal"] if terminal else None,
        failure=failure,
        observation_before=before,
        observation_after=before if after is None else after,
    )


def test_complete_activation_dag_round_trips_and_has_no_self_reference() -> None:
    chain = _chain()
    for document, identity in (
        (chain["resource_plan"], "preactivation_resource_probe_plan_id"),
        (chain["resource_result"], "preactivation_resource_result_id"),
        (chain["activation_plan"], "materialization_activation_plan_id"),
        (chain["local_attempt"], "local_materialization_activation_attempt_id"),
        (chain["network_start"], "materialization_activation_network_start_id"),
        (chain["remote_attempt"], "remote_materialization_activation_attempt_id"),
        (chain["service_receipt"], "remote_activation_service_receipt_id"),
        (chain["ready"], "remote_activation_publish_ready_id"),
        (chain["terminal"], "remote_materialization_transport_terminal_id"),
    ):
        raw = canonical_json_bytes(document)
        assert raw.count(document[identity].encode("ascii")) == 1
    assert activation.materialize_authorized_ssh_argv_v42r1(
        activation_plan=chain["activation_plan"],
        local_activation_attempt_id=chain["local_attempt"][
            "local_materialization_activation_attempt_id"
        ],
    ) == chain["network_start"]["authorized_ssh_argv"]
    assert "--collect" not in chain["activation_plan"]["systemd_service_contract"][
        "authorized_systemd_run_argv_template"
    ]
    assert "--pipe" not in chain["activation_plan"]["systemd_service_contract"][
        "authorized_systemd_run_argv_template"
    ]
    assert chain["activation_plan"][
        "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim"
    ] is True


def test_contextual_verifiers_reject_extra_type_order_path_and_rehashed_splice() -> None:
    chain = _chain()
    extra = copy.deepcopy(chain["resource_plan"])
    extra["extra"] = False
    payload = dict(extra)
    payload.pop("preactivation_resource_probe_plan_id")
    extra["preactivation_resource_probe_plan_id"] = hashlib.sha256(
        (activation.DOMAIN_PREFIX + "preactivation-resource-probe-plan").encode()
        + b"\0"
        + canonical_json_bytes(payload)
    ).hexdigest()
    with pytest.raises(activation.V42MaterializationActivationError):
        activation.verify_preactivation_resource_probe_plan_v42r1(
            extra,
            preformal_plan=chain["plan"],
            preformal_attempt=chain["attempt"],
            preformal_receipt=chain["receipt"],
            preformal_outcome=chain["outcome"],
            loader_source_raw=_LOADER_RAW,
            receiver_source_raw=_RECEIVER_RAW,
            service_source_raw=_SERVICE_RAW,
            driver_source_raw=_DRIVER_RAW,
            activation_authority_source_raw=_ACTIVATION_AUTHORITY_RAW,
            control_raw_by_name=chain["controls"],
        )
    wrong_order = copy.deepcopy(chain["snapshot"])
    wrong_order["control_identities"].reverse()
    with pytest.raises(activation.V42MaterializationActivationError):
        activation.verify_selected_remote_snapshot_v42r1(
            wrong_order, preformal_receipt=chain["receipt"]
        )
    wrong_path = copy.deepcopy(chain["terminal"]["fixed_root_snapshot"])
    wrong_path["root_identity"]["path"] += "-splice"
    with pytest.raises(activation.V42MaterializationActivationError):
        activation.verify_exact_five_live_snapshot_v42r1(
            wrong_path,
            preformal_receipt=chain["receipt"],
            root_path=chain["activation_plan"]["fixed_remote_root"],
        )


def test_resource_gate_is_before_formal_attempt_and_fails_closed_at_boundaries() -> None:
    chain = _chain()
    low = activation.build_preactivation_resource_result_v42r1(
        resource_plan=chain["resource_plan"],
        preformal_receipt=chain["receipt"],
        stage="READ_ONLY_PREACTIVATION_PROBE",
        observed_hostname=authority.REMOTE_HOSTNAME,
        observed_user=authority.REMOTE_USER,
        observed_uid=authority.REMOTE_UID,
        observed_gid=authority.REMOTE_GID,
        observed_python=_python_observation(chain["resource_plan"]),
        memory_total_bytes=activation.MINIMUM_MEMORY_TOTAL_BYTES - 1,
        memory_available_bytes=activation.MINIMUM_MEMORY_AVAILABLE_BYTES - 1,
        swap_total_bytes=1,
        swap_free_bytes=0,
        filesystem_available_bytes=activation.MINIMUM_FILESYSTEM_AVAILABLE_BYTES - 1,
        cgroup_memory_ancestry=_resource_values()["cgroup_memory_ancestry"],
        selected_remote_snapshot=chain["snapshot"],
    )
    assert low["all_resource_gates_passed"] is False
    arguments = {
        "preformal_plan": chain["plan"],
        "preformal_attempt": chain["attempt"],
        "preformal_receipt": chain["receipt"],
        "preformal_outcome": chain["outcome"],
        "resource_plan": chain["resource_plan"],
        "resource_result": low,
        "control_raw_by_name": chain["controls"],
        "loader_source_raw": _LOADER_RAW,
        "receiver_source_raw": _RECEIVER_RAW,
        "service_source_raw": _SERVICE_RAW,
        "driver_source_raw": _DRIVER_RAW,
        "activation_authority_source_raw": _ACTIVATION_AUTHORITY_RAW,
    }
    with pytest.raises(activation.V42MaterializationActivationError):
        activation.build_materialization_activation_plan_v42r1(**arguments)
    assert chain["resource_plan"]["resource_probe_does_not_consume_formal_identity"]
    assert chain["local_attempt"][
        "published_before_any_activation_ssh_or_systemd_effect"
    ]
    assert chain["resource_result"]["only_current_ssh_ingress_process_started"]
    assert not chain["resource_result"][
        "additional_or_durable_remote_process_started"
    ]


def test_resource_plan_rejects_activation_program_outside_selected_transport_facts() -> None:
    selected = _selected_preformal()
    arguments = {
        "preformal_plan": selected["plan"],
        "preformal_attempt": selected["attempt"],
        "preformal_receipt": selected["receipt"],
        "preformal_outcome": selected["outcome"],
        "loader_source_raw": _LOADER_RAW,
        "receiver_source_raw": _RECEIVER_RAW,
        "service_source_raw": _SERVICE_RAW,
        "driver_source_raw": _DRIVER_RAW,
        "activation_authority_source_raw": _ACTIVATION_AUTHORITY_RAW,
        "control_raw_by_name": selected["controls"],
    }
    activation.build_preactivation_resource_probe_plan_v42r1(**arguments)
    changed = dict(arguments)
    changed["receiver_source_raw"] = _RECEIVER_RAW + b"# uncommitted byte\n"
    with pytest.raises(
        activation.V42MaterializationActivationError,
        match="not an exact selected-commit transport fact",
    ):
        activation.build_preactivation_resource_probe_plan_v42r1(**changed)


def test_remote_receiver_rejects_self_consistent_plan_artifact_transport_splice() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        fixture = _offline_effect_fixture(Path(temporary))
        plan = copy.deepcopy(fixture["plan"])
        plan["activation_receiver_artifact"]["git_blob_oid"] = "f" * 40
        payload = dict(plan)
        del payload["materialization_activation_plan_id"]
        plan["materialization_activation_plan_id"] = activation._content_id(  # noqa: SLF001
            activation.DOMAIN_PREFIX + "materialization-activation-plan", payload
        )
        local = activation.build_local_materialization_activation_attempt_v42r1(
            activation_plan=plan, local_effective_uid=authority.REMOTE_UID
        )
        network = activation.build_materialization_activation_network_start_v42r1(
            activation_plan=plan, local_attempt=local
        )
        ingress_argv = activation.materialize_authorized_remote_ingress_argv_v42r1(
            activation_plan=plan,
            local_activation_attempt_id=local[
                "local_materialization_activation_attempt_id"
            ],
        )
        remote = activation.build_remote_materialization_activation_attempt_v42r1(
            activation_plan=plan,
            local_attempt=local,
            network_start=network,
            observed_remote_snapshot=plan["selected_remote_snapshot"],
            observed_remote_ingress_argv=ingress_argv,
            observed_hostname=authority.REMOTE_HOSTNAME,
            observed_user=authority.REMOTE_USER,
            observed_uid=authority.REMOTE_UID,
            observed_gid=authority.REMOTE_GID,
        )
        envelope = {
            "schema": "acfqp.v42_materialization_activation_ingress.v42r1",
            "operation": "ACTIVATE_SELECTED_COMPLETE_RECEIPT",
            "activation_plan": plan,
            "local_activation_attempt": local,
            "network_start": network,
            "remote_activation_attempt": remote,
            "service_source_utf8": fixture["service_raw"].decode("utf-8"),
        }
        with pytest.raises(
            RuntimeError, match="does not join exact transport fact"
        ):
            activation_receiver._verify_activation_envelope(  # noqa: SLF001
                envelope,
                expected_plan_id=plan["materialization_activation_plan_id"],
                expected_local_attempt_id=local[
                    "local_materialization_activation_attempt_id"
                ],
                verified_receiver_sha256=plan[
                    "activation_receiver_artifact"
                ]["sha256"],
                observed_remote_ingress_python_argv=ingress_argv,
            )
        with pytest.raises(
            RuntimeError, match="does not join exact transport fact"
        ):
            activation_loader._verify_program_transport_facts(  # noqa: SLF001
                plan,
                (("activation_receiver_artifact", _RECEIVER_RAW),),
            )
        service_plan = copy.deepcopy(fixture["plan"])
        service_plan["activation_service_artifact"]["git_blob_oid"] = "f" * 40
        with pytest.raises(
            RuntimeError, match="does not join exact transport fact"
        ):
            activation_service._verify_service_transport_fact(  # noqa: SLF001
                service_plan, fixture["service_raw"]
            )


@pytest.mark.parametrize(
    "ancestry",
    [
        [
            {
                "cgroup_path": "/user.slice/user-1000.slice/app.scope",
                "memory_max_mode": "MAX",
                "memory_max_bytes": None,
                "memory_current_bytes": 1024**3,
            },
            {
                "cgroup_path": "/",
                "memory_max_mode": "MAX",
                "memory_max_bytes": None,
                "memory_current_bytes": 1024**3,
            },
        ],
        [
            {
                "cgroup_path": "/",
                "memory_max_mode": "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES",
                "memory_max_bytes": None,
                "memory_current_bytes": None,
            }
        ],
    ],
)
def test_resource_gate_requires_at_least_one_applicable_finite_cgroup_limit(
    ancestry: list[dict[str, Any]],
) -> None:
    chain = _chain()
    result = activation.build_preactivation_resource_result_v42r1(
        resource_plan=chain["resource_plan"],
        preformal_receipt=chain["receipt"],
        stage="READ_ONLY_PREACTIVATION_PROBE",
        observed_hostname=authority.REMOTE_HOSTNAME,
        observed_user=authority.REMOTE_USER,
        observed_uid=authority.REMOTE_UID,
        observed_gid=authority.REMOTE_GID,
        observed_python=_python_observation(chain["resource_plan"]),
        selected_remote_snapshot=chain["snapshot"],
        memory_total_bytes=activation.MINIMUM_MEMORY_TOTAL_BYTES,
        memory_available_bytes=activation.MINIMUM_MEMORY_AVAILABLE_BYTES,
        swap_total_bytes=0,
        swap_free_bytes=0,
        filesystem_available_bytes=activation.MINIMUM_FILESYSTEM_AVAILABLE_BYTES,
        cgroup_memory_ancestry=ancestry,
    )
    assert result["resource_gate_checks"]["cgroup_memory_gate"] is False
    assert result["all_resource_gates_passed"] is False


def test_systemd_contract_forbids_lifecycle_coupling_and_binds_read_only_query() -> None:
    chain = _chain()
    contract = chain["activation_plan"]["systemd_service_contract"]
    argv = contract["authorized_systemd_run_argv_template"]
    assert not {"--wait", "--pipe", "--pty", "--scope", "--collect"}.intersection(
        argv
    )
    assert contract["wait"] is contract["pipe"] is contract["pty"] is False
    assert contract["scope"] is contract["collect"] is False
    query = activation.materialize_authorized_systemctl_argv_v42r1(
        activation_plan=chain["activation_plan"]
    )
    assert query[0] == activation.SYSTEMCTL
    assert chain["local_attempt"]["derived_systemd_unit_name"] in query
    assert activation.materialize_authorized_classifier_argv_v42r1(
        activation_plan=chain["activation_plan"],
        local_activation_attempt_id=chain["local_attempt"][
            "local_materialization_activation_attempt_id"
        ],
        remote_python=True,
    )[6] == "--activation-classify"


def test_classification_lattice_is_monotone_and_never_authorizes_retry() -> None:
    chain = _chain()
    local = _classify(chain, stage="local", remote=False)
    active = _classify(chain, stage="active")
    service = _classify(chain, stage="service", service=True)
    ready = _classify(chain, stage="ready", service=True, ready=True)
    success = _classify(
        chain, stage="terminal", service=True, ready=True, terminal=True
    )
    assert local["classification"] == activation.CLASSIFICATION_AMBIGUOUS
    assert active["classification"] == activation.CLASSIFICATION_IN_PROGRESS
    assert service["classification"] == activation.CLASSIFICATION_AMBIGUOUS
    assert ready["classification"] == activation.CLASSIFICATION_AMBIGUOUS
    assert success["classification"] == activation.CLASSIFICATION_SUCCESS
    assert all(
        document["activation_retry_authorized"] is False
        for document in (local, active, service, ready, success)
    )
    drift = _observation(chain, stage="active")
    drift["systemd_unit_properties_exact"] = False
    changed = activation.build_materialization_activation_classification_v42r1(
        activation_plan=chain["activation_plan"],
        local_attempt=chain["local_attempt"],
        network_start=chain["network_start"],
        preformal_receipt=chain["receipt"],
        remote_attempt=chain["remote_attempt"],
        service_receipt=None,
        publish_ready=None,
        terminal=None,
        failure=None,
        observation_before=drift,
        observation_after=drift,
    )
    assert changed["classification"] == activation.CLASSIFICATION_AMBIGUOUS
    assert changed["reason"] == "ACTIVE_UNIT_PROPERTIES_CHANGED"


def test_service_receipt_binds_live_unit_and_terminal_precedes_outer_exec() -> None:
    chain = _chain()
    receipt = chain["service_receipt"]
    assert receipt["systemd_unit_properties_exact"] is True
    assert receipt["live_systemd_unit_properties"]["MainPID"] == 4242
    tampered = copy.deepcopy(receipt)
    tampered["live_systemd_unit_properties"]["MainPID"] += 1
    payload = dict(tampered)
    payload.pop("remote_activation_service_receipt_id")
    tampered["remote_activation_service_receipt_id"] = hashlib.sha256(
        b"acfqp:v42-remote-ordinal2:remote-activation-service-receipt\0"
        + canonical_json_bytes(payload)
    ).hexdigest()
    with pytest.raises(activation.V42MaterializationActivationError):
        activation.verify_remote_activation_service_receipt_v42r1(
            tampered,
            activation_plan=chain["activation_plan"],
            remote_attempt=chain["remote_attempt"],
        )
    terminal = chain["terminal"]
    assert terminal["trusted_bootstrap_outer_exec_started_at_terminal_publication"] is False
    assert terminal[
        "durable_terminal_authorizes_same_service_context_next_step_exact_outer_exec"
    ] is True


def test_typed_failure_only_exists_before_ready_with_root_absent() -> None:
    chain = _chain()
    failure = activation.build_remote_materialization_activation_failure_v42r1(
        activation_plan=chain["activation_plan"],
        remote_attempt=chain["remote_attempt"],
        service_receipt=chain["service_receipt"],
        failure_stage="SERVICE_AFTER_RECEIPT_BEFORE_READY",
        failure_classification="RESOURCE_GATE_FAILED",
        failure_message="available memory fell below the fixed threshold",
    )
    classified = _classify(
        chain,
        stage="failure",
        service=True,
        failure=failure,
    )
    assert classified["classification"] == activation.CLASSIFICATION_FAILURE
    with pytest.raises(activation.V42MaterializationActivationError):
        activation.build_materialization_activation_classification_v42r1(
            activation_plan=chain["activation_plan"],
            local_attempt=chain["local_attempt"],
            network_start=chain["network_start"],
            preformal_receipt=chain["receipt"],
            remote_attempt=chain["remote_attempt"],
            service_receipt=chain["service_receipt"],
            publish_ready=chain["ready"],
            terminal=None,
            failure=failure,
            observation_before=_observation(chain, stage="failure"),
            observation_after=_observation(chain, stage="failure"),
        )


def test_classifier_turns_race_and_extra_ledger_entries_into_closed_ambiguity() -> None:
    chain = _chain()
    before = _observation(chain, stage="service")
    changed = copy.deepcopy(before)
    changed["systemd_unit_state"] = "FAILED"
    race = _classify(
        chain, stage="service", service=True, after=changed
    )
    assert race["classification"] == activation.CLASSIFICATION_AMBIGUOUS
    assert "CHANGED_DURING" in race["reason"]
    extra = copy.deepcopy(before)
    extra["fixed_transport_ledger_inventory"].append("UNKNOWN")
    extra["fixed_transport_ledger_inventory"].sort()
    ambiguous = activation.build_materialization_activation_classification_v42r1(
        activation_plan=chain["activation_plan"],
        local_attempt=chain["local_attempt"],
        network_start=chain["network_start"],
        preformal_receipt=chain["receipt"],
        remote_attempt=chain["remote_attempt"],
        service_receipt=chain["service_receipt"],
        publish_ready=None,
        terminal=None,
        failure=None,
        observation_before=extra,
        observation_after=extra,
    )
    assert ambiguous["classification"] == activation.CLASSIFICATION_AMBIGUOUS
    assert "PARTIAL_EXTRA_OR_CONFLICTING" in ambiguous["reason"]


def test_exact_five_rejects_hardlinks_and_same_bytes_new_inode_after_ready() -> None:
    chain = _chain()
    hardlink = copy.deepcopy(chain["terminal"]["fixed_root_snapshot"])
    hardlink["control_facts"][0]["identity"]["st_nlink"] = 2
    with pytest.raises(activation.V42MaterializationActivationError):
        activation.verify_exact_five_live_snapshot_v42r1(
            hardlink,
            preformal_receipt=chain["receipt"],
            root_path=chain["activation_plan"]["fixed_remote_root"],
        )
    replaced = copy.deepcopy(chain["terminal"]["fixed_root_snapshot"])
    replaced["control_facts"][0]["identity"]["st_ino"] += 1
    with pytest.raises(activation.V42MaterializationActivationError):
        activation.build_remote_materialization_transport_terminal_v42r1(
            activation_plan=chain["activation_plan"],
            remote_attempt=chain["remote_attempt"],
            service_receipt=chain["service_receipt"],
            publish_ready=chain["ready"],
            preformal_receipt=chain["receipt"],
            fixed_root_snapshot=replaced,
        )


def test_service_documents_are_byte_exact_with_the_pure_authority_builders() -> None:
    chain = _chain()
    invocation, group, pid, properties = _systemd_runtime(
        chain["activation_plan"], chain["remote_attempt"]
    )
    first_gate = activation_service._resource_gate(  # noqa: SLF001
        plan_id=chain["activation_plan"]["materialization_activation_plan_id"],
        stage="SYSTEMD_SERVICE_RECEIPT_GATE",
        values=_resource_values(),
    )
    receipt = activation_service._service_receipt(  # noqa: SLF001
        plan=chain["activation_plan"],
        remote=chain["remote_attempt"],
        invocation_id=invocation,
        control_group=group,
        gate=first_gate,
        observed_argv=activation.materialize_authorized_service_argv_v42r1(
            activation_plan=chain["activation_plan"],
            remote_activation_attempt_id=chain["remote_attempt"][
                "remote_materialization_activation_attempt_id"
            ],
            systemd_invocation_id=invocation,
            systemd_control_group=group,
        ),
        service_pid=pid,
        live_unit_properties=properties,
    )
    assert receipt == chain["service_receipt"]
    second_gate = activation_service._resource_gate(  # noqa: SLF001
        plan_id=chain["activation_plan"]["materialization_activation_plan_id"],
        stage="SYSTEMD_SERVICE_PUBLISH_GATE",
        values=_resource_values(),
    )
    ready = activation_service._ready(  # noqa: SLF001
        plan=chain["activation_plan"],
        remote=chain["remote_attempt"],
        receipt=receipt,
        gate=second_gate,
        scratch_snapshot=chain["ready"]["live_scratch_snapshot"],
    )
    assert ready == chain["ready"]
    terminal = activation_service._terminal(  # noqa: SLF001
        plan=chain["activation_plan"],
        remote=chain["remote_attempt"],
        receipt=receipt,
        ready=ready,
        fixed_snapshot=chain["terminal"]["fixed_root_snapshot"],
    )
    assert terminal == chain["terminal"]


def test_service_rejects_extra_descriptors_and_non_devnull_stdio() -> None:
    descriptor = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    try:
        with pytest.raises(activation_service._ActivationServiceFailure):  # noqa: SLF001
            activation_service._require_exact_devnull_stdio()  # noqa: SLF001
    finally:
        os.close(descriptor)


def test_service_rejects_bootstrap_to_clean_cgroup_membership_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = "/user.slice/user-1000.slice/app.slice/exact.service"
    monkeypatch.setattr(
        activation_service,
        "_current_unified_cgroup",
        lambda: "/user.slice/user-1000.slice/app.slice/different.service",
    )
    with pytest.raises(activation_service._ActivationServiceFailure):  # noqa: SLF001
        activation_service._require_current_unified_cgroup(expected)  # noqa: SLF001


def _ingress_result(chain: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "acfqp.v42_remote_ordinal2_activation_ingress_result.v42r1",
        "materialization_activation_plan_id": chain["activation_plan"][
            "materialization_activation_plan_id"
        ],
        "remote_materialization_activation_attempt_id": chain["remote_attempt"][
            "remote_materialization_activation_attempt_id"
        ],
        "systemd_run_returncode": 0,
        "systemd_effect_may_have_occurred": True,
        "same_activation_identity_retry_forbidden": True,
        "read_only_followup_only": True,
    }


def test_local_activation_receipt_and_ambiguity_are_typed_and_content_addressed() -> None:
    chain = _chain()
    receipt = activation.build_local_materialization_activation_receipt_v42r1(
        activation_plan=chain["activation_plan"],
        local_attempt=chain["local_attempt"],
        network_start=chain["network_start"],
        remote_attempt_id=chain["remote_attempt"][
            "remote_materialization_activation_attempt_id"
        ],
        ingress_result=_ingress_result(chain),
    )
    assert activation.verify_local_materialization_activation_receipt_v42r1(
        receipt,
        activation_plan=chain["activation_plan"],
        local_attempt=chain["local_attempt"],
        network_start=chain["network_start"],
        remote_attempt_id=chain["remote_attempt"][
            "remote_materialization_activation_attempt_id"
        ],
    ) == receipt
    ambiguity = activation.build_local_materialization_activation_ambiguity_v42r1(
        activation_plan=chain["activation_plan"],
        local_attempt=chain["local_attempt"],
        network_start=chain["network_start"],
        reason_code="SSH_OUTCOME_NOT_EXACT",
    )
    assert ambiguity["classification"] == activation.CLASSIFICATION_AMBIGUOUS
    assert ambiguity["same_activation_identity_retry_forbidden"] is True


def test_driver_resumes_exact_pre_marker_prefix_and_closes_post_marker_without_retry() -> None:
    chain = _chain()
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        journal = Path(temporary) / "journal"
        descriptor = activation_driver._secure_directory(str(journal))  # noqa: SLF001
        try:
            activation_driver._ensure_exact_pre_marker_prefix(  # noqa: SLF001
                descriptor,
                activation_plan=chain["activation_plan"],
                local_attempt=chain["local_attempt"],
            )
            first = sorted(os.listdir(descriptor))
            activation_driver._ensure_exact_pre_marker_prefix(  # noqa: SLF001
                descriptor,
                activation_plan=chain["activation_plan"],
                local_attempt=chain["local_attempt"],
            )
            assert sorted(os.listdir(descriptor)) == first
            activation_driver._write_once(  # noqa: SLF001
                descriptor,
                activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                chain["network_start"],
            )
            closed = activation_driver._existing_post_marker_outcome(  # noqa: SLF001
                descriptor,
                activation_plan=chain["activation_plan"],
                local_attempt=chain["local_attempt"],
                network_start=chain["network_start"],
            )
            assert closed["reason_code"] == "RECOVERED_POST_MARKER_WITHOUT_DURABLE_OUTCOME"
            assert activation_driver._existing_post_marker_outcome(  # noqa: SLF001
                descriptor,
                activation_plan=chain["activation_plan"],
                local_attempt=chain["local_attempt"],
                network_start=chain["network_start"],
            ) == closed
        finally:
            os.close(descriptor)


def test_driver_resumes_plan_only_prefix_and_rejects_tampered_outcome_storage() -> None:
    chain = _chain()
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        journal = Path(temporary) / "journal"
        descriptor = activation_driver._secure_directory(str(journal))  # noqa: SLF001
        try:
            activation_driver._write_once(  # noqa: SLF001
                descriptor,
                activation.LOCAL_ACTIVATION_PLAN_NAME,
                chain["activation_plan"],
            )
            activation_driver._ensure_exact_pre_marker_prefix(  # noqa: SLF001
                descriptor,
                activation_plan=chain["activation_plan"],
                local_attempt=chain["local_attempt"],
            )
            assert sorted(os.listdir(descriptor)) == sorted(
                (
                    activation.LOCAL_ACTIVATION_PLAN_NAME,
                    activation.LOCAL_ACTIVATION_ATTEMPT_NAME,
                )
            )
            activation_driver._write_once(  # noqa: SLF001
                descriptor,
                activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                chain["network_start"],
            )
            receipt = activation.build_local_materialization_activation_receipt_v42r1(
                activation_plan=chain["activation_plan"],
                local_attempt=chain["local_attempt"],
                network_start=chain["network_start"],
                remote_attempt_id=chain["remote_attempt"][
                    "remote_materialization_activation_attempt_id"
                ],
                ingress_result=_ingress_result(chain),
            )
            activation_driver._write_once(  # noqa: SLF001
                descriptor, activation.LOCAL_ACTIVATION_RECEIPT_NAME, receipt
            )
            alias = Path(temporary) / "receipt-hardlink"
            os.link(journal / activation.LOCAL_ACTIVATION_RECEIPT_NAME, alias)
            with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
                activation_driver._existing_post_marker_outcome(  # noqa: SLF001
                    descriptor,
                    activation_plan=chain["activation_plan"],
                    local_attempt=chain["local_attempt"],
                    network_start=chain["network_start"],
                )
        finally:
            os.close(descriptor)


def test_driver_requires_exact_selected_preformal_receipt_join() -> None:
    chain = _chain()
    activation_driver._verify_selected_preformal_receipt_join(  # noqa: SLF001
        activation_plan=chain["activation_plan"],
        preformal_receipt=chain["receipt"],
    )
    changed = copy.deepcopy(chain["receipt"])
    changed["preformal_upload_receipt_id"] = "f" * 64
    with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
        activation_driver._verify_selected_preformal_receipt_join(  # noqa: SLF001
            activation_plan=chain["activation_plan"], preformal_receipt=changed
        )


def test_driver_pinned_journal_rejects_named_root_swap() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        root = Path(temporary) / "journal"
        journal = activation_driver._secure_pinned_journal(str(root))  # noqa: SLF001
        moved = Path(temporary) / "moved-journal"
        os.rename(root, moved)
        root.mkdir(mode=0o700)
        try:
            with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
                journal.verify_named()
        finally:
            journal.close()
        with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
            activation_driver._secure_pinned_journal(str(root))  # noqa: SLF001


def test_driver_pinned_journal_rejects_named_parent_component_swap() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        parent = Path(temporary) / "parent"
        parent.mkdir(mode=0o700)
        root = parent / "journal"
        journal = activation_driver._secure_pinned_journal(str(root))  # noqa: SLF001
        moved = Path(temporary) / "moved-parent"
        os.rename(parent, moved)
        parent.mkdir(mode=0o700)
        try:
            with pytest.raises(
                activation_driver.V42MaterializationActivationDriverError,
                match="lexical chain changed",
            ):
                journal.verify_named()
        finally:
            journal.close()


def test_driver_external_network_cut_survives_inner_marker_unlink() -> None:
    chain = _chain()
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        root = Path(temporary) / "journal"
        journal = activation_driver._secure_pinned_journal(str(root))  # noqa: SLF001
        try:
            activation_driver._ensure_exact_pre_marker_prefix(  # noqa: SLF001
                journal.descriptor,
                activation_plan=chain["activation_plan"],
                local_attempt=chain["local_attempt"],
            )
            journal.publish_external_network_cut(chain["network_start"])
            activation_driver._write_once(  # noqa: SLF001
                journal.descriptor,
                activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                chain["network_start"],
            )
            os.unlink(
                activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                dir_fd=journal.descriptor,
            )
            os.fsync(journal.descriptor)
        finally:
            journal.close()
        reopened = activation_driver._secure_pinned_journal(str(root))  # noqa: SLF001
        try:
            assert reopened.read_external_network_cut(chain["network_start"]) is not None
            closed = activation_driver._close_external_cut_without_inner_marker(  # noqa: SLF001
                reopened.descriptor,
                activation_plan=chain["activation_plan"],
                local_attempt=chain["local_attempt"],
                network_start=chain["network_start"],
            )
            assert closed["same_activation_identity_retry_forbidden"] is True
            assert closed["reason_code"] == (
                "RECOVERED_EXTERNAL_NETWORK_CUT_WITHOUT_INNER_MARKER"
            )
        finally:
            reopened.close()


def test_driver_rejects_same_bytes_new_inode_for_published_marker() -> None:
    chain = _chain()
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        descriptor = activation_driver._secure_directory(  # noqa: SLF001
            str(Path(temporary) / "journal")
        )
        try:
            identity = activation_driver._write_once(  # noqa: SLF001
                descriptor,
                activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                chain["network_start"],
            )
            os.rename(
                activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                "old-marker",
                src_dir_fd=descriptor,
                dst_dir_fd=descriptor,
            )
            activation_driver._write_once(  # noqa: SLF001
                descriptor,
                activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                chain["network_start"],
            )
            with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
                activation_driver._read_document_at(  # noqa: SLF001
                    descriptor,
                    activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                    chain["network_start"],
                    expected_identity=identity,
                )
        finally:
            os.close(descriptor)


class _NoopDispatchPins:
    def verify(self) -> None:
        return None

    def close(self) -> None:
        return None


class _FaultingDispatchChild:
    def __init__(self, effect: Any) -> None:
        self._effect = effect

    def verify_prepared(self) -> None:
        return None

    def spawn_and_pump(self) -> Any:
        self._effect()
        raise RuntimeError("offline injected SSH disconnect")

    def close(self) -> None:
        return None


class _FaultingPreparedDispatch:
    def __init__(self, effect: Any) -> None:
        self.child = _FaultingDispatchChild(effect)
        self.pins = _NoopDispatchPins()

    def verify(self, _plan: dict[str, Any]) -> None:
        return None

    def close(self) -> None:
        self.child.close()
        self.pins.close()


def _activation_driver_fixture_programs(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, raw in (
        ("driver", _DRIVER_RAW),
        ("loader", _LOADER_RAW),
        ("receiver", _RECEIVER_RAW),
        ("service", _SERVICE_RAW),
    ):
        path = root / (name + ".py")
        path.write_bytes(raw)
        result[name] = str(path)
    return result


def test_execute_activation_marker_unlink_reentry_never_spawns_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _chain()
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        base = Path(temporary)
        monkeypatch.setattr(preformal, "LOCAL_TRANSPORT_PARENT", base)
        programs = _activation_driver_fixture_programs(base)
        monkeypatch.setattr(activation_driver, "__file__", programs["driver"])
        local = activation.build_local_materialization_activation_attempt_v42r1(
            activation_plan=chain["activation_plan"],
            local_effective_uid=authority.REMOTE_UID,
        )
        journal_root = Path(local["local_control_root"])
        journal_root.parent.mkdir(parents=True, mode=0o700)
        spawn_count = 0

        def effect() -> None:
            nonlocal spawn_count
            spawn_count += 1
            os.unlink(journal_root / activation.LOCAL_ACTIVATION_NETWORK_START_NAME)

        def factory(**_arguments: Any) -> _FaultingPreparedDispatch:
            return _FaultingPreparedDispatch(effect)

        arguments = {
            "activation_plan": chain["activation_plan"],
            "preformal_receipt": chain["receipt"],
            "loader_path": programs["loader"],
            "receiver_path": programs["receiver"],
            "service_path": programs["service"],
            "local_effective_uid": authority.REMOTE_UID,
            "prepared_dispatch_factory": factory,
        }
        first = activation_driver.execute_activation_v42r1(**arguments)
        second = activation_driver.execute_activation_v42r1(**arguments)
        assert first == second
        assert first["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert spawn_count == 1


def test_execute_activation_named_root_swap_reentry_never_spawns_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _chain()
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        base = Path(temporary)
        monkeypatch.setattr(preformal, "LOCAL_TRANSPORT_PARENT", base)
        programs = _activation_driver_fixture_programs(base)
        monkeypatch.setattr(activation_driver, "__file__", programs["driver"])
        local = activation.build_local_materialization_activation_attempt_v42r1(
            activation_plan=chain["activation_plan"],
            local_effective_uid=authority.REMOTE_UID,
        )
        journal_root = Path(local["local_control_root"])
        journal_root.parent.mkdir(parents=True, mode=0o700)
        moved = journal_root.with_name(journal_root.name + ".moved")
        spawn_count = 0

        def effect() -> None:
            nonlocal spawn_count
            spawn_count += 1
            os.rename(journal_root, moved)
            journal_root.mkdir(mode=0o700)

        def factory(**_arguments: Any) -> _FaultingPreparedDispatch:
            return _FaultingPreparedDispatch(effect)

        arguments = {
            "activation_plan": chain["activation_plan"],
            "preformal_receipt": chain["receipt"],
            "loader_path": programs["loader"],
            "receiver_path": programs["receiver"],
            "service_path": programs["service"],
            "local_effective_uid": authority.REMOTE_UID,
            "prepared_dispatch_factory": factory,
        }
        with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
            activation_driver.execute_activation_v42r1(**arguments)
        with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
            activation_driver.execute_activation_v42r1(**arguments)
        assert spawn_count == 1


def test_execute_activation_named_parent_swap_reentry_never_spawns_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _chain()
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        base = Path(temporary)
        monkeypatch.setattr(preformal, "LOCAL_TRANSPORT_PARENT", base)
        programs = _activation_driver_fixture_programs(base)
        monkeypatch.setattr(activation_driver, "__file__", programs["driver"])
        local = activation.build_local_materialization_activation_attempt_v42r1(
            activation_plan=chain["activation_plan"],
            local_effective_uid=authority.REMOTE_UID,
        )
        journal_root = Path(local["local_control_root"])
        journal_parent = journal_root.parent
        journal_parent.mkdir(parents=True, mode=0o700)
        moved_parent = journal_parent.with_name(journal_parent.name + ".moved")
        spawn_count = 0

        def effect() -> None:
            nonlocal spawn_count
            spawn_count += 1
            os.rename(journal_parent, moved_parent)
            journal_parent.mkdir(mode=0o700)
            journal_root.mkdir(mode=0o700)

        def factory(**_arguments: Any) -> _FaultingPreparedDispatch:
            return _FaultingPreparedDispatch(effect)

        arguments = {
            "activation_plan": chain["activation_plan"],
            "preformal_receipt": chain["receipt"],
            "loader_path": programs["loader"],
            "receiver_path": programs["receiver"],
            "service_path": programs["service"],
            "local_effective_uid": authority.REMOTE_UID,
            "prepared_dispatch_factory": factory,
        }
        with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
            activation_driver.execute_activation_v42r1(**arguments)
        with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
            activation_driver.execute_activation_v42r1(**arguments)
        assert spawn_count == 1


def test_production_orchestrator_builds_persists_and_resumes_without_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        base = Path(temporary)
        monkeypatch.setattr(preformal, "LOCAL_TRANSPORT_PARENT", base)
        chain = _chain()
        programs = _activation_driver_fixture_programs(base)
        authority_path = base / "activation-authority.py"
        authority_path.write_bytes(_ACTIVATION_AUTHORITY_RAW)
        programs["authority"] = str(authority_path)
        monkeypatch.setattr(activation_driver, "__file__", programs["driver"])
        context = _preformal_context()
        preformal_loader = base / "preformal-loader.py"
        preformal_receiver = base / "preformal-receiver.py"
        preformal_loader.write_bytes(context["loader_source_raw"])
        preformal_receiver.write_bytes(context["receiver_source_raw"])
        preformal_root = base / "preformal"
        control_root = base / "controls"
        preformal_root.mkdir(mode=0o700)
        control_root.mkdir(mode=0o700)
        for name, document in (
            (preformal.PREFORMAL_PLAN_NAME, chain["plan"]),
            (preformal.PREFORMAL_ATTEMPT_NAME, chain["attempt"]),
            (preformal.PREFORMAL_RECEIPT_NAME, chain["receipt"]),
            (preformal.PREFORMAL_OUTCOME_NAME, chain["outcome"]),
        ):
            path = preformal_root / name
            path.write_bytes(canonical_json_bytes(document))
            path.chmod(0o400)
        for name, raw in chain["controls"].items():
            path = control_root / name
            path.write_bytes(raw)
            path.chmod(0o400)
        activation_control_parent = (
            base / activation.LOCAL_ACTIVATION_CONTROL_ROOT_RELATIVE
        )
        activation_control_parent.mkdir(parents=True, mode=0o700)
        resource_calls = 0
        spawn_calls = 0
        classification_calls = 0

        def resource_dispatch(**arguments: Any) -> dict[str, Any]:
            nonlocal resource_calls
            resource_calls += 1
            resource_plan = arguments["plan"]
            return {
                "only_current_ssh_ingress_process_started": True,
                "additional_or_durable_remote_process_started": False,
                "remote_mutation_performed": False,
                "resource_observation_stage": "READ_ONLY_PREACTIVATION_PROBE",
                "observed_hostname": authority.REMOTE_HOSTNAME,
                "observed_user": authority.REMOTE_USER,
                "observed_uid": authority.REMOTE_UID,
                "observed_gid": authority.REMOTE_GID,
                "observed_python": _python_observation(resource_plan),
                "selected_remote_snapshot": chain["snapshot"],
                **_resource_values(),
            }

        def effect() -> None:
            nonlocal spawn_calls
            spawn_calls += 1

        def prepared_factory(**_arguments: Any) -> _FaultingPreparedDispatch:
            return _FaultingPreparedDispatch(effect)

        def classification_dispatch(**_arguments: Any) -> dict[str, Any]:
            nonlocal classification_calls
            classification_calls += 1
            terminal_stage = classification_calls > 1
            bootstrap_success = classification_calls > 2
            observation = _observation(
                chain, stage="terminal" if terminal_stage else "active"
            )
            bootstrap_documents: dict[str, dict[str, Any]] = {}
            if terminal_stage:
                complete_bootstrap = _bootstrap_success_documents(chain)
                bootstrap_documents = (
                    complete_bootstrap
                    if bootstrap_success
                    else {
                        name: complete_bootstrap[name]
                        for name in (
                            authority.SOURCE_MANIFEST_NAME,
                            authority.TRANSPORT_MANIFEST_NAME,
                            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
                        )
                    }
                )
            return {
                "remote_mutation_performed": False,
                "activation_retry_authorized": False,
                "additional_durable_or_mutating_remote_process_started": False,
                "observation_before": observation,
                    "observation_after": observation,
                    "remote_documents": {
                        "remote_attempt": chain["remote_attempt"],
                    "service_receipt": (
                        chain["service_receipt"] if terminal_stage else None
                    ),
                    "publish_ready": chain["ready"] if terminal_stage else None,
                    "terminal": chain["terminal"] if terminal_stage else None,
                    "failure": None,
                },
                "fixed_root_evidence": {
                    "inventory_before": (
                        sorted(set(preformal.CONTROL_NAMES) | set(bootstrap_documents))
                        if terminal_stage
                        else []
                    ),
                    "inventory_after": (
                        sorted(set(preformal.CONTROL_NAMES) | set(bootstrap_documents))
                        if terminal_stage
                        else []
                    ),
                    "documents": bootstrap_documents,
                    "collected_subset_only_not_whole_tree": True,
                },
            }

        arguments = {
            "preformal_evidence_root": str(preformal_root),
            "expected_preformal_plan_id": chain["plan"][
                "preformal_upload_plan_id"
            ],
            "control_root": str(control_root),
            "resource_evidence_root": str(base / "resource-evidence"),
            "activation_evidence_root": str(base / "activation-evidence"),
            "preformal_loader_path": str(preformal_loader),
            "preformal_receiver_path": str(preformal_receiver),
            "loader_path": programs["loader"],
            "receiver_path": programs["receiver"],
            "service_path": programs["service"],
            "activation_authority_path": programs["authority"],
            "resource_dispatch": resource_dispatch,
            "prepared_dispatch_factory": prepared_factory,
            "classification_dispatch": classification_dispatch,
        }
        first = activation_driver.orchestrate_activation_from_retained_v42r1(
            **arguments
        )
        second = activation_driver.orchestrate_activation_from_retained_v42r1(
            **arguments
        )
        evidence = Path(arguments["activation_evidence_root"])
        assert not (
            evidence / "MATERIALIZATION_ACTIVATION_FINAL_EVIDENCE_INDEX.json"
        ).exists()
        third = activation_driver.orchestrate_activation_from_retained_v42r1(
            **arguments
        )
        fourth = activation_driver.orchestrate_activation_from_retained_v42r1(
            **arguments
        )
        assert first["read_only_classification"]["classification"] == (
            "IN_PROGRESS_READ_ONLY_WAIT"
        )
        assert second["read_only_classification"]["classification"] == (
            "COMPLETE_TRANSPORT_SUCCESS"
        )
        assert third["read_only_classification"]["classification"] == (
            "COMPLETE_TRANSPORT_SUCCESS"
        )
        assert fourth["read_only_classification"] == third[
            "read_only_classification"
        ]
        assert first["materialization_activation_final_evidence_index_id"] is None
        assert second["materialization_activation_final_evidence_index_id"] is None
        assert re.fullmatch(
            r"[0-9a-f]{64}",
            third["materialization_activation_final_evidence_index_id"],
        )
        assert fourth["materialization_activation_final_evidence_index_id"] == third[
            "materialization_activation_final_evidence_index_id"
        ]
        assert resource_calls == 1
        assert spawn_calls == 1
        assert classification_calls == 3
        assert (evidence / preformal.PREFORMAL_PLAN_NAME).is_file()
        assert (evidence / "PREACTIVATION_RESOURCE_PROBE_PLAN.json").is_file()
        assert (evidence / "PREACTIVATION_RESOURCE_RESULT.json").is_file()
        assert (evidence / "ACTIVATION_EVIDENCE_ROOTS.json").is_file()
        snapshots = sorted(evidence.glob("ACTIVATION_READ_ONLY_SNAPSHOT_*.json"))
        assert len(snapshots) == 3
        first_snapshot = activation_driver._canonical_document(  # noqa: SLF001
            snapshots[0].read_bytes(), "first activation snapshot"
        )
        second_snapshot = activation_driver._canonical_document(  # noqa: SLF001
            snapshots[1].read_bytes(), "second activation snapshot"
        )
        third_snapshot = activation_driver._canonical_document(  # noqa: SLF001
            snapshots[2].read_bytes(), "third activation snapshot"
        )
        assert first_snapshot["previous_snapshot_id"] is None
        assert second_snapshot["previous_snapshot_id"] == first_snapshot[
            "activation_read_only_snapshot_id"
        ]
        assert third_snapshot["previous_snapshot_id"] == second_snapshot[
            "activation_read_only_snapshot_id"
        ]
        final_index = activation_driver._canonical_document(  # noqa: SLF001
            (
                evidence
                / "MATERIALIZATION_ACTIVATION_FINAL_EVIDENCE_INDEX.json"
            ).read_bytes(),
            "activation final evidence index",
        )
        assert final_index["activation_read_only_snapshot_id"] == third_snapshot[
            "activation_read_only_snapshot_id"
        ]
        assert final_index[
            "formal_evidence_bundle_complete_under_bounded_successor_claim"
        ] is True
        assert final_index[
            "bootstrap_launcher_consumed_activation_transport_terminal_id"
        ] is False
        assert final_index[
            "materialization_activation_final_evidence_index_id"
        ] == third["materialization_activation_final_evidence_index_id"]

        selected = third_snapshot
        regressed_observation = {
            "schema": "acfqp.v42_remote_ordinal2_materialization_activation_read_only_observation.v42r1",
            "materialization_activation_plan_id": chain["activation_plan"][
                "materialization_activation_plan_id"
            ],
            "local_materialization_activation_attempt_id": chain["local_attempt"][
                "local_materialization_activation_attempt_id"
            ],
            "observation_before": _observation(chain, stage="active"),
            "observation_after": _observation(chain, stage="active"),
            "remote_documents": {
                "remote_attempt": chain["remote_attempt"],
                "service_receipt": None,
                "publish_ready": None,
                "terminal": None,
                "failure": None,
            },
            "fixed_root_evidence": {
                "inventory_before": [],
                "inventory_after": [],
                "documents": {},
                "collected_subset_only_not_whole_tree": True,
            },
            "remote_mutation_performed": False,
            "only_read_only_ssh_ingress_and_systemctl_query_processes_started": True,
            "additional_durable_or_mutating_remote_process_started": False,
            "activation_retry_authorized": False,
        }
        persisted_arguments = {
            "evidence_root": str(evidence),
            "activation_plan": chain["activation_plan"],
            "local_attempt": chain["local_attempt"],
            "network_start": chain["network_start"],
            "preformal_receipt": chain["receipt"],
            "preformal_plan": chain["plan"],
            "preformal_attempt": chain["attempt"],
            "preformal_outcome": chain["outcome"],
            "resource_plan": chain["resource_plan"],
            "resource_result": chain["resource_result"],
            "control_root": str(control_root),
        }
        with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
            activation_driver._persist_read_only_classification_evidence(  # noqa: SLF001
                **persisted_arguments,
                observed=regressed_observation,
                classification=_classify(chain, stage="active"),
            )
        different_success = copy.deepcopy(selected["observation"])
        different_success["read_only_observation_nonce"] = "2" * 64
        with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
            activation_driver._persist_read_only_classification_evidence(  # noqa: SLF001
                **persisted_arguments,
                observed=different_success,
                classification=selected["classification"],
            )
        assert sorted(evidence.glob("ACTIVATION_READ_ONLY_SNAPSHOT_*.json")) == snapshots


def test_offline_receiver_service_effect_chain_publishes_terminal_before_outer() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        fixture = _offline_effect_fixture(Path(temporary))
        plan = fixture["plan"]
        remote = fixture["remote"]
        outer_events: list[tuple[list[str], dict[str, Any]]] = []
        service_results: list[dict[str, Any]] = []

        def systemd_runner(
            argv: list[str], environment: dict[str, str], executable_fact: dict[str, Any]
        ) -> int:
            assert "--wait" not in argv
            assert environment == activation.SYSTEMD_CLIENT_ENVIRONMENT
            assert executable_fact == plan["systemd_service_contract"]["systemd_run"]
            invocation = "1" * 32
            unit = activation.materialize_activation_unit_name_v42r1(
                plan["materialization_activation_plan_id"]
            )
            group = f"/user.slice/user-1000.slice/app.slice/{unit}"
            service_argv = activation.materialize_authorized_service_argv_v42r1(
                activation_plan=plan,
                remote_activation_attempt_id=remote[
                    "remote_materialization_activation_attempt_id"
                ],
                systemd_invocation_id=invocation,
                systemd_control_group=group,
            )

            def unit_observer(
                observed_plan: dict[str, Any],
                remote_attempt_id: str,
                invocation_id: str,
                control_group: str,
                service_pid: int,
            ) -> dict[str, Any]:
                assert observed_plan == plan
                assert remote_attempt_id == remote[
                    "remote_materialization_activation_attempt_id"
                ]
                assert invocation_id == invocation
                assert control_group == group
                return {
                    "Id": unit,
                    "LoadState": "loaded",
                    "ActiveState": "active",
                    "SubState": "running",
                    "FragmentPath": (
                        f"/run/user/{authority.REMOTE_UID}/systemd/transient/{unit}"
                    ),
                    "MainPID": service_pid,
                    "InvocationID": invocation,
                    "ControlGroup": group,
                    "Type": "exec",
                    "bootstrap_argv_verified_by_tiny_loader_before_clean_exec": True,
                    "StandardInput": "null",
                    "StandardOutput": "null",
                    "StandardError": "null",
                    "Restart": "no",
                    "UMask": "0077",
                    "KillMode": "control-group",
                    "RuntimeMaxUSec": "1w",
                    "WorkingDirectory": str(Path(plan["fixed_remote_root"]).parent),
                    "Slice": "app.slice",
                    "invocation_symlink_verified": True,
                    "observed_via_pinned_systemctl_executable": True,
                    "systemctl_argv": (
                        activation.materialize_authorized_systemctl_argv_v42r1(
                            activation_plan=plan
                        )
                    ),
                }

            def outer_exec(argv: list[str], observed_plan: dict[str, Any]) -> None:
                terminal_path = fixture["ledger"] / activation.REMOTE_ACTIVATION_TERMINAL_NAME
                assert terminal_path.is_file()
                terminal = activation_driver._canonical_document(  # noqa: SLF001
                    terminal_path.read_bytes(), "offline terminal"
                )
                assert argv == plan["trusted_bootstrap_outer_command"]
                assert observed_plan == plan
                outer_events.append((list(argv), terminal))

            result = activation_service.run_service_v42r1(
                remote_activation_attempt_id=remote[
                    "remote_materialization_activation_attempt_id"
                ],
                systemd_invocation_id=invocation,
                systemd_control_group=group,
                observed_service_argv=service_argv,
                resource_observer=lambda _parent: _resource_values(),
                unit_observer=unit_observer,
                outer_exec=outer_exec,
                fixed_ledger_override_for_offline_fixture=str(fixture["ledger"]),
                formal_runtime_checks=False,
            )
            service_results.append(result)
            return 0

        envelope = {
            "schema": "acfqp.v42_materialization_activation_ingress.v42r1",
            "operation": "ACTIVATE_SELECTED_COMPLETE_RECEIPT",
            "activation_plan": plan,
            "local_activation_attempt": fixture["local"],
            "network_start": fixture["network"],
            "remote_activation_attempt": remote,
            "service_source_utf8": fixture["service_raw"].decode("utf-8"),
        }
        ingress = activation_receiver.activate_selected_receipt_v42r1(
            envelope=envelope,
            expected_plan_id=plan["materialization_activation_plan_id"],
            expected_local_attempt_id=fixture["local"][
                "local_materialization_activation_attempt_id"
            ],
            verified_receiver_sha256=fixture["receiver_sha"],
            observed_remote_ingress_python_argv=fixture["ingress_argv"],
            systemd_runner=systemd_runner,
        )
        assert ingress["systemd_run_returncode"] == 0
        assert ingress["same_activation_identity_retry_forbidden"] is True
        assert len(service_results) == len(outer_events) == 1
        terminal = service_results[0]
        assert terminal == outer_events[0][1]
        assert terminal[
            "trusted_bootstrap_outer_exec_started_at_terminal_publication"
        ] is False
        assert not fixture["scratch"].exists()
        assert not fixture["stage"].exists()
        assert sorted(path.name for path in fixture["fixed"].iterdir()) == list(
            preformal.CONTROL_NAMES
        )
        assert sorted(path.name for path in fixture["ledger"].iterdir()) == sorted(
            (
                activation.REMOTE_ACTIVATION_ATTEMPT_NAME,
                activation.REMOTE_ACTIVATION_SERVICE_SOURCE_NAME,
                activation.REMOTE_ACTIVATION_SERVICE_RECEIPT_NAME,
                activation.REMOTE_ACTIVATION_READY_NAME,
                activation.REMOTE_ACTIVATION_TERMINAL_NAME,
            )
        )
        fixed_evidence = activation_receiver._read_optional_fixed_root_documents(  # noqa: SLF001
            plan, {"fixed_remote_root_state": "EXACT_DIRECTORY"}
        )
        assert fixed_evidence["inventory_before"] == fixed_evidence["inventory_after"]
        assert set(fixed_evidence["documents"]) == {
            authority.SOURCE_MANIFEST_NAME,
            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            authority.TRANSPORT_MANIFEST_NAME,
        }


def test_read_only_classification_evidence_is_o_excl_and_stably_replayed() -> None:
    chain = _chain()
    classification = _classify(
        chain, stage="terminal", service=True, ready=True, terminal=True
    )
    fixed_documents = {
        authority.SOURCE_MANIFEST_NAME: activation_driver._canonical_document(  # noqa: SLF001
            chain["controls"][authority.SOURCE_MANIFEST_NAME], "source manifest"
        ),
        authority.TRANSPORT_MANIFEST_NAME: activation_driver._canonical_document(  # noqa: SLF001
            chain["controls"][authority.TRANSPORT_MANIFEST_NAME],
            "transport manifest",
        ),
        authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME: (
            activation_driver._canonical_document(  # noqa: SLF001
                chain["controls"][authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME],
                "local materialization attempt",
            )
        ),
    }
    observed = {
        "schema": "acfqp.v42_remote_ordinal2_materialization_activation_read_only_observation.v42r1",
        "materialization_activation_plan_id": chain["activation_plan"][
            "materialization_activation_plan_id"
        ],
        "local_materialization_activation_attempt_id": chain["local_attempt"][
            "local_materialization_activation_attempt_id"
        ],
        "observation_before": _observation(chain, stage="terminal"),
        "observation_after": _observation(chain, stage="terminal"),
        "remote_documents": {
            "remote_attempt": chain["remote_attempt"],
            "service_receipt": chain["service_receipt"],
            "publish_ready": chain["ready"],
            "terminal": chain["terminal"],
            "failure": None,
        },
        "fixed_root_evidence": {
            "inventory_before": sorted(
                (*preformal.CONTROL_NAMES, authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME)
            ),
            "inventory_after": sorted(
                (*preformal.CONTROL_NAMES, authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME)
            ),
            "documents": fixed_documents,
            "collected_subset_only_not_whole_tree": True,
        },
        "remote_mutation_performed": False,
        "only_read_only_ssh_ingress_and_systemctl_query_processes_started": True,
        "additional_durable_or_mutating_remote_process_started": False,
        "activation_retry_authorized": False,
    }
    with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
        evidence_root = str(Path(temporary) / "evidence")
        control_root = Path(temporary) / "controls"
        control_root.mkdir(mode=0o700)
        for name, raw in chain["controls"].items():
            path = control_root / name
            path.write_bytes(raw)
            path.chmod(0o400)
        arguments = {
            "evidence_root": evidence_root,
            "activation_plan": chain["activation_plan"],
            "local_attempt": chain["local_attempt"],
            "network_start": chain["network_start"],
            "preformal_receipt": chain["receipt"],
            "preformal_plan": chain["plan"],
            "preformal_attempt": chain["attempt"],
            "preformal_outcome": chain["outcome"],
            "resource_plan": chain["resource_plan"],
            "resource_result": chain["resource_result"],
            "control_root": str(control_root),
            "observed": observed,
            "classification": classification,
        }
        activation_driver._persist_read_only_classification_evidence(  # noqa: SLF001
            **arguments
        )
        activation_driver._persist_read_only_classification_evidence(  # noqa: SLF001
            **arguments
        )
        root = Path(evidence_root)
        assert (root / preformal.PREFORMAL_PLAN_NAME).is_file()
        assert (root / preformal.PREFORMAL_ATTEMPT_NAME).is_file()
        assert (root / preformal.PREFORMAL_OUTCOME_NAME).is_file()
        assert (root / "PREACTIVATION_RESOURCE_PROBE_PLAN.json").is_file()
        assert (root / "PREACTIVATION_RESOURCE_RESULT.json").is_file()
        evidence_roots = activation_driver._canonical_document(  # noqa: SLF001
            (root / "ACTIVATION_EVIDENCE_ROOTS.json").read_bytes(),
            "activation evidence roots",
        )
        assert evidence_roots["control_evidence_root"] == str(control_root)
        assert evidence_roots["control_reference_snapshot"][
            "exact_inventory"
        ] == list(preformal.CONTROL_NAMES)
        for name in (
            activation.REMOTE_ACTIVATION_ATTEMPT_NAME,
            activation.REMOTE_ACTIVATION_SERVICE_RECEIPT_NAME,
            activation.REMOTE_ACTIVATION_READY_NAME,
            activation.REMOTE_ACTIVATION_TERMINAL_NAME,
            authority.SOURCE_MANIFEST_NAME,
            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            authority.TRANSPORT_MANIFEST_NAME,
        ):
            observed_stat = (root / name).lstat()
            assert stat.S_IMODE(observed_stat.st_mode) == 0o400
            assert observed_stat.st_nlink == 1
        alias = Path(temporary) / "terminal-alias"
        os.link(root / activation.REMOTE_ACTIVATION_TERMINAL_NAME, alias)
        with pytest.raises(activation_driver.V42MaterializationActivationDriverError):
            activation_driver._persist_read_only_classification_evidence(  # noqa: SLF001
                **arguments
            )


def test_systemd_runner_wait_is_bounded_kills_and_reaps_without_fd_leak() -> None:
    before = {
        int(name)
        for name in os.listdir("/proc/self/fd")
        if name.isdigit()
        and (lambda descriptor: _fd_live(descriptor))(int(name))
    }
    pid = os.fork()
    if pid == 0:
        try:
            import time

            time.sleep(60)
        finally:
            os._exit(0)
    status = activation_receiver._bounded_waitpid(pid, 0.01)  # noqa: SLF001
    assert os.WIFSIGNALED(status)
    with pytest.raises(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)
    after = {
        int(name)
        for name in os.listdir("/proc/self/fd")
        if name.isdigit()
        and (lambda descriptor: _fd_live(descriptor))(int(name))
    }
    assert after == before


def test_snapshot_cap_allows_idempotent_4096_tail_but_never_4097(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _chain()
    observation = {"stage": "stable-final"}
    classification = {"classification": "COMPLETE_TRANSPORT_SUCCESS"}
    latest = {
        "activation_read_only_snapshot_id": "1" * 64,
        "observation": observation,
        "classification": classification,
    }
    saturated = [{} for _ in range(4095)] + [latest]
    monkeypatch.setattr(
        activation_driver,
        "_read_snapshot_chain",
        lambda _directory_fd, *, activation_plan: saturated,
    )
    assert activation_driver._append_read_only_snapshot(  # noqa: SLF001
        -1,
        activation_plan=chain["activation_plan"],
        observed=observation,
        classification=classification,
    ) is latest
    with pytest.raises(
        activation_driver.V42MaterializationActivationDriverError,
        match="cannot append beyond",
    ):
        activation_driver._append_read_only_snapshot(  # noqa: SLF001
            -1,
            activation_plan=chain["activation_plan"],
            observed={"stage": "different"},
            classification=classification,
        )


def _fd_live(descriptor: int) -> bool:
    try:
        os.fstat(descriptor)
    except OSError:
        return False
    return True
