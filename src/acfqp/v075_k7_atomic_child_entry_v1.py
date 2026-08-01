"""Fresh-exec child entry for the atomic V0-075 K7 business route.

The module is imported only after a sealed deterministic source archive has
been inserted at the head of ``sys.path``.  It reconstructs the V0-105 profile
and request authorities, executes the V0-106 business body once, verifies that
every loaded ``acfqp`` module originated in that archive, and writes one
canonical child-owned frame to the parent-owned channel.

The frame does not claim a complete stdlib/native-extension graph, parent
supervision, shared-resource semantics, formal accounting, or a certificate.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_child_business_bundle_v1 as business_v1
from acfqp import v075_k7_successor_portable_replay_v1 as portable_v1
from acfqp import v075_signer_owning_sealed_observer_ipc_v1 as transport_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ATOMIC_CHILD_BUSINESS_FRAME_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.0"
PROFILE_KEY = "v075_k7_atomic_child_entry_v1"
FRAME_ROLE = "CHILD_OWNED_K7_BUSINESS"
ENTRY_MODULE = "acfqp.v075_k7_atomic_child_entry_v1"
ENTRY_SYMBOL = "run_v075_k7_atomic_child_entry_v1"
MAX_CHILD_FRAME_BYTES = 64 * 1024 * 1024
MAX_EXECUTED_BUSINESS_BUNDLE_BYTES = 48 * 1024 * 1024
MAX_CHILD_FRAME_NONBUSINESS_OVERHEAD_BYTES = (
    MAX_CHILD_FRAME_BYTES - MAX_EXECUTED_BUSINESS_BUNDLE_BYTES
)
CHILD_FAILURE_EXIT_CODE = 90
CHILD_INPUT_REPLAY_FAILURE_EXIT_CODE = 91
CHILD_BUSINESS_FAILURE_EXIT_CODE = 92
CHILD_FRAME_FAILURE_EXIT_CODE = 93
CHILD_OUTPUT_FAILURE_EXIT_CODE = 94

if V075_K7_ATOMIC_CHILD_BUSINESS_FRAME_V1_DOMAIN not in PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("atomic K7 child-frame domain is unregistered")


class V075K7AtomicChildEntryV1Error(RuntimeError):
    """The sealed child inputs, module graph, or business frame are invalid."""


def _fail(message: str) -> NoReturn:
    raise V075K7AtomicChildEntryV1Error(message)


def _emit_private_failure_detail(channel_fd: int, prefix: str, error: BaseException) -> None:
    """Emit only exception type and code locations; never exception text/state."""

    detail = prefix + ":TYPE=" + type(error).__name__ + ":TRACE=" + "|".join(
        str(frame.lineno) + "@" + frame.name
        for frame in traceback.extract_tb(error.__traceback__)
    )
    try:
        os.write(channel_fd, detail.encode("ascii", errors="backslashreplace"))
    except BaseException:
        pass


def _locks() -> dict[str, bool]:
    return {
        "complete_loaded_module_graph_verified": False,
        "shared_resource_semantics_verified": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "actual_projection_proof_issued": False,
        "formal_vector_authorized": False,
        "attempt_terminal_issued": False,
        "plan_certificate_issued": False,
        "infeasibility_certificate_issued": False,
        "official_execution_allowed": False,
    }


def _read_sealed(fd: int, *, cap: int, label: str) -> bytes:
    if type(fd) is not int or fd < 3:
        _fail(f"{label} descriptor is invalid")
    try:
        return transport_v1._read_sealed_fd(fd, cap=cap)  # noqa: SLF001
    except Exception as error:
        raise V075K7AtomicChildEntryV1Error(
            f"{label} descriptor failed sealed replay"
        ) from error


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_CHILD_FRAME_BYTES:
        _fail(f"{label} bytes are empty, mistyped, or over cap")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7AtomicChildEntryV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _loaded_acfqp_manifest(
    *, archive_fd: int, source_entries: tuple[tuple[str, str, int], ...]
) -> tuple[dict[str, Any], ...]:
    archive_origin = f"/proc/self/fd/{archive_fd}"
    by_path = {
        path: (digest, size) for path, digest, size in source_entries
    }
    rows: list[dict[str, Any]] = []
    for module_name, module in sorted(sys.modules.items()):
        if module_name != "acfqp" and not module_name.startswith("acfqp."):
            continue
        specification = getattr(module, "__spec__", None)
        origin = None if specification is None else specification.origin
        loader = getattr(module, "__loader__", None)
        if (
            type(origin) is not str
            or not origin.startswith(archive_origin + "/")
            or type(loader).__module__ != "zipimport"
            or getattr(loader, "archive", None) != archive_origin
        ):
            _fail("a loaded ACFQP module did not originate in the sealed archive")
        relative = origin[len(archive_origin) + 1 :]
        expected = by_path.get(relative)
        if relative.endswith("/__init__.py"):
            expected_module_name = relative[: -len("/__init__.py")].replace("/", ".")
        elif relative.endswith(".py"):
            expected_module_name = relative[:-3].replace("/", ".")
        else:  # pragma: no cover - source archive validation already forbids this
            expected_module_name = ""
        if expected is None:
            _fail("a loaded ACFQP module is absent from the source snapshot")
        if expected_module_name != module_name:
            _fail("a loaded ACFQP module name crossed its canonical source path")
        rows.append(
            {
                "module_name": module_name,
                "source_path": relative,
                "source_sha256": expected[0],
                "source_byte_count": expected[1],
                "loader_kind": "zipimport.zipimporter",
            }
        )
        if module_name == "acfqp" and tuple(getattr(module, "__path__", ())) != (
            archive_origin + "/acfqp",
        ):
            _fail("the ACFQP package search path escaped the sealed archive")
    if not rows or not any(row["module_name"] == ENTRY_MODULE for row in rows):
        _fail("the sealed child entry is absent from its loaded module graph")
    paths = [row["source_path"] for row in rows]
    names = [row["module_name"] for row in rows]
    if len(paths) != len(set(paths)) or len(names) != len(set(names)):
        _fail("the loaded ACFQP module graph is not one-to-one")
    return tuple(rows)


def _frame_payload(
    *,
    request_replay: portable_v1.V075K7SuccessorPortableRequestReplayV1,
    child_bundle: business_v1.V075K7ChildBusinessBundleV1,
    loaded_modules: tuple[dict[str, Any], ...],
    atomic_parent_execution_spec_id: str,
) -> dict[str, Any]:
    request = request_replay.request
    bundle_raw = child_bundle.canonical_bytes
    module_rows = [dict(row) for row in loaded_modules]
    return {
        "schema": "acfqp.v075_k7_atomic_child_business_frame.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frame_index": 1,
        "frame_role": FRAME_ROLE,
        "atomic_parent_execution_spec_id": atomic_parent_execution_spec_id,
        "entry_module": ENTRY_MODULE,
        "entry_symbol": ENTRY_SYMBOL,
        "source_archive_sha256": (
            request_replay.profile_closure.source_archive_sha256
        ),
        "source_archive_byte_count": (
            request_replay.profile_closure.source_archive_byte_count
        ),
        "source_snapshot_id": (
            request_replay.profile_closure.transport_profile.source_snapshot_id
        ),
        "runtime_id": request_replay.profile_closure.transport_profile.runtime_id,
        "portable_profile_closure_id": request_replay.profile_closure.closure_id,
        "portable_request_replay_id": request_replay.replay_id,
        "successor_profile_id": request.profile.profile_id,
        "request_id": request.request_id,
        "route_identity_id": request.route_identity.route_identity_id,
        "logical_occurrence_id": (
            request.occurrence_mapping.phase3e_logical_occurrence_id
        ),
        "child_business_bundle_id": child_bundle.bundle_id,
        "child_business_bundle_sha256": hashlib.sha256(bundle_raw).hexdigest(),
        "child_business_bundle": child_bundle.to_document(),
        "loaded_acfqp_modules": module_rows,
        "loaded_acfqp_module_count": len(module_rows),
        "loaded_acfqp_module_manifest_sha256": hashlib.sha256(
            canonical_json_bytes(module_rows)
        ).hexdigest(),
        "complete_loaded_acfqp_module_graph_verified": True,
        "loaded_acfqp_graph_claim_authority": "SEALED_CHILD_PROGRAM_SELF_CHECK",
        "parent_independent_loaded_graph_replay_performed": False,
        "all_loaded_acfqp_modules_from_sealed_archive": True,
        "live_workspace_acfqp_import_observed": False,
        "embedded_business_bundle_private_taint_scan_completed": True,
        "complete_outer_frame_private_taint_scan_completed": False,
        "private_taint_independently_replayed_by_parent": False,
        "parent_runtime_sandbox_verification_required": True,
        "business_payload_frozen_before_channel_close": True,
        **_locks(),
    }


def freeze_v075_k7_atomic_child_business_frame_v1(
    *,
    request_replay: portable_v1.V075K7SuccessorPortableRequestReplayV1,
    child_bundle: business_v1.V075K7ChildBusinessBundleV1,
    archive_fd: int,
    atomic_parent_execution_spec_id: str,
) -> bytes:
    """Freeze one child-owned frame after business and module-origin checks."""

    if type(request_replay) is not portable_v1.V075K7SuccessorPortableRequestReplayV1:
        _fail("atomic child frame requires one exact request replay")
    if type(child_bundle) is not business_v1.V075K7ChildBusinessBundleV1:
        _fail("atomic child frame requires one exact business bundle")
    if len(child_bundle.canonical_bytes) > MAX_EXECUTED_BUSINESS_BUNDLE_BYTES:
        _fail("business bundle exceeds the preregistered atomic wrapper budget")
    if (
        type(atomic_parent_execution_spec_id) is not str
        or len(atomic_parent_execution_spec_id) != 64
        or any(character not in "0123456789abcdef" for character in atomic_parent_execution_spec_id)
    ):
        _fail("atomic parent execution-spec ID is not one lowercase content ID")
    transport = request_replay.profile_closure.transport_profile
    before = tuple(sorted(name for name in sys.modules if name == "acfqp" or name.startswith("acfqp.")))
    rows = _loaded_acfqp_manifest(
        archive_fd=archive_fd,
        source_entries=transport.source_entries,
    )
    payload = _frame_payload(
        request_replay=request_replay,
        child_bundle=child_bundle,
        loaded_modules=rows,
        atomic_parent_execution_spec_id=atomic_parent_execution_spec_id,
    )
    raw = canonical_json_bytes(
        {
            **payload,
            "atomic_child_business_frame_id": content_id(
                V075_K7_ATOMIC_CHILD_BUSINESS_FRAME_V1_DOMAIN, payload
            ),
        }
    )
    after = tuple(sorted(name for name in sys.modules if name == "acfqp" or name.startswith("acfqp.")))
    replayed_rows = _loaded_acfqp_manifest(
        archive_fd=archive_fd,
        source_entries=transport.source_entries,
    )
    if before != after or rows != replayed_rows:
        _fail("an ACFQP module loaded after the module-graph cutoff")
    if len(raw) > MAX_CHILD_FRAME_BYTES:
        _fail("atomic child business frame exceeds its output cap")
    if len(raw) - len(child_bundle.canonical_bytes) > MAX_CHILD_FRAME_NONBUSINESS_OVERHEAD_BYTES:
        _fail("atomic child frame exceeds its preregistered wrapper overhead")
    return raw


def verify_v075_k7_atomic_child_business_frame_bytes_v1(
    *,
    raw: bytes,
    expected_request_replay: portable_v1.V075K7SuccessorPortableRequestReplayV1,
    expected_atomic_parent_execution_spec_id: str,
) -> dict[str, Any]:
    """Parent-side exact public replay of one frozen child-owned frame."""

    if type(expected_request_replay) is not portable_v1.V075K7SuccessorPortableRequestReplayV1:
        _fail("atomic child-frame replay requires one exact request replay")
    if (
        type(expected_atomic_parent_execution_spec_id) is not str
        or len(expected_atomic_parent_execution_spec_id) != 64
        or any(
            character not in "0123456789abcdef"
            for character in expected_atomic_parent_execution_spec_id
        )
    ):
        _fail("expected atomic parent execution-spec ID is invalid")
    document = _canonical_document(raw, "atomic child business frame")
    id_field = document.get("atomic_child_business_frame_id")
    payload = {key: value for key, value in document.items() if key != "atomic_child_business_frame_id"}
    if (
        set(document)
        != {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "frame_index", "frame_role", "atomic_parent_execution_spec_id",
            "entry_module", "entry_symbol",
            "source_archive_sha256", "source_archive_byte_count", "source_snapshot_id",
            "runtime_id", "portable_profile_closure_id", "portable_request_replay_id",
            "successor_profile_id", "request_id", "route_identity_id",
            "logical_occurrence_id", "child_business_bundle_id",
            "child_business_bundle_sha256", "child_business_bundle",
            "loaded_acfqp_modules", "loaded_acfqp_module_count",
            "loaded_acfqp_module_manifest_sha256",
            "complete_loaded_acfqp_module_graph_verified",
            "loaded_acfqp_graph_claim_authority",
            "parent_independent_loaded_graph_replay_performed",
            "all_loaded_acfqp_modules_from_sealed_archive",
            "live_workspace_acfqp_import_observed",
            "embedded_business_bundle_private_taint_scan_completed",
            "complete_outer_frame_private_taint_scan_completed",
            "private_taint_independently_replayed_by_parent",
            "parent_runtime_sandbox_verification_required",
            "business_payload_frozen_before_channel_close",
            "complete_loaded_module_graph_verified", "shared_resource_semantics_verified",
            "counter_records_issued", "work_vector_issued", "comparison_vector_issued",
            "actual_projection_proof_issued", "formal_vector_authorized",
            "attempt_terminal_issued", "plan_certificate_issued",
            "infeasibility_certificate_issued", "official_execution_allowed",
            "atomic_child_business_frame_id",
        }
        or id_field != content_id(V075_K7_ATOMIC_CHILD_BUSINESS_FRAME_V1_DOMAIN, payload)
    ):
        _fail("atomic child business frame schema or identity changed")
    replay = expected_request_replay
    request = replay.request
    transport = replay.profile_closure.transport_profile
    fixed_true = (
        "complete_loaded_acfqp_module_graph_verified",
        "all_loaded_acfqp_modules_from_sealed_archive",
        "embedded_business_bundle_private_taint_scan_completed",
        "parent_runtime_sandbox_verification_required",
        "business_payload_frozen_before_channel_close",
    )
    if (
        document["schema"] != "acfqp.v075_k7_atomic_child_business_frame.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or type(document["frame_index"]) is not int
        or document["frame_index"] != 1
        or document["frame_role"] != FRAME_ROLE
        or document["atomic_parent_execution_spec_id"]
        != expected_atomic_parent_execution_spec_id
        or document["entry_module"] != ENTRY_MODULE
        or document["entry_symbol"] != ENTRY_SYMBOL
        or document["source_archive_sha256"] != replay.profile_closure.source_archive_sha256
        or type(document["source_archive_byte_count"]) is not int
        or document["source_archive_byte_count"] != replay.profile_closure.source_archive_byte_count
        or document["source_snapshot_id"] != transport.source_snapshot_id
        or document["runtime_id"] != transport.runtime_id
        or document["portable_profile_closure_id"] != replay.profile_closure.closure_id
        or document["portable_request_replay_id"] != replay.replay_id
        or document["successor_profile_id"] != request.profile.profile_id
        or document["request_id"] != request.request_id
        or document["route_identity_id"] != request.route_identity.route_identity_id
        or document["logical_occurrence_id"] != request.occurrence_mapping.phase3e_logical_occurrence_id
        or any(document[name] is not True for name in fixed_true)
        or document["loaded_acfqp_graph_claim_authority"]
        != "SEALED_CHILD_PROGRAM_SELF_CHECK"
        or document["parent_independent_loaded_graph_replay_performed"] is not False
        or document["private_taint_independently_replayed_by_parent"] is not False
        or document["complete_outer_frame_private_taint_scan_completed"] is not False
        or document["live_workspace_acfqp_import_observed"] is not False
        or any(document[name] is not False for name in _locks())
    ):
        _fail("atomic child business frame crossed its request or fixed semantics")
    rows = document["loaded_acfqp_modules"]
    if (
        type(rows) is not list
        or not rows
        or type(document["loaded_acfqp_module_count"]) is not int
        or document["loaded_acfqp_module_count"] != len(rows)
        or document["loaded_acfqp_module_manifest_sha256"]
        != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
    ):
        _fail("loaded ACFQP module manifest is malformed")
    if any(type(row) is not dict for row in rows) or [
        row.get("module_name") for row in rows
    ] != sorted(row.get("module_name") for row in rows):
        _fail("loaded ACFQP module manifest order is noncanonical")
    by_path = {path: (digest, size) for path, digest, size in transport.source_entries}
    seen_names: set[str] = set()
    seen_paths: set[str] = set()
    for row in rows:
        if type(row) is not dict or set(row) != {
            "module_name", "source_path", "source_sha256", "source_byte_count", "loader_kind"
        }:
            _fail("loaded ACFQP module row is malformed")
        name = row["module_name"]
        path = row["source_path"]
        expected = by_path.get(path)
        expected_name = (
            path[: -len("/__init__.py")].replace("/", ".")
            if path.endswith("/__init__.py")
            else path[:-3].replace("/", ".")
            if path.endswith(".py")
            else ""
        )
        if (
            type(name) is not str
            or (name != "acfqp" and not name.startswith("acfqp."))
            or type(path) is not str
            or expected != (row["source_sha256"], row["source_byte_count"])
            or expected_name != name
            or row["loader_kind"] != "zipimport.zipimporter"
            or name in seen_names
            or path in seen_paths
        ):
            _fail("loaded ACFQP module row crossed the sealed source snapshot")
        seen_names.add(name)
        seen_paths.add(path)
    if ENTRY_MODULE not in seen_names:
        _fail("loaded ACFQP module manifest omits the child entry")
    bundle_document = document["child_business_bundle"]
    if type(bundle_document) is not dict:
        _fail("atomic child frame lacks one business bundle document")
    bundle_raw = canonical_json_bytes(bundle_document)
    verified_bundle = business_v1.verify_v075_k7_child_business_bundle_public_bytes_v1(
        raw=bundle_raw,
        expected_request_replay=replay,
    )
    if (
        document["child_business_bundle_id"] != verified_bundle.bundle_id
        or document["child_business_bundle_sha256"]
        != hashlib.sha256(bundle_raw).hexdigest()
    ):
        _fail("atomic child frame crossed its business bundle")
    return document


def run_v075_k7_atomic_child_entry_v1(
    *,
    archive_fd: int,
    transport_profile_fd: int,
    lifecycle_profile_fd: int,
    successor_profile_fd: int,
    request_fd: int,
    sealed_secret_fd: int,
    channel_fd: int,
    repository_root: str,
    signer_private_root: str,
    signer_private_key_path: str,
    atomic_parent_execution_spec_id: str,
) -> int:
    """Execute and emit one child frame; failures emit no diagnostic bytes."""

    descriptors = (
        archive_fd,
        transport_profile_fd,
        lifecycle_profile_fd,
        successor_profile_fd,
        request_fd,
        sealed_secret_fd,
        channel_fd,
    )
    if len(set(descriptors)) != len(descriptors) or min(descriptors) < 3:
        return CHILD_FAILURE_EXIT_CODE
    try:
        archive_raw = _read_sealed(
            archive_fd, cap=transport_v1.MAX_SOURCE_ARCHIVE_BYTES, label="source archive"
        )
        transport_raw = _read_sealed(
            transport_profile_fd,
            cap=portable_v1.MAX_PROFILE_DOCUMENT_BYTES,
            label="transport profile",
        )
        lifecycle_raw = _read_sealed(
            lifecycle_profile_fd,
            cap=portable_v1.MAX_PROFILE_DOCUMENT_BYTES,
            label="lifecycle profile",
        )
        successor_raw = _read_sealed(
            successor_profile_fd,
            cap=portable_v1.MAX_PROFILE_DOCUMENT_BYTES,
            label="successor profile",
        )
        request_raw = _read_sealed(
            request_fd, cap=portable_v1.MAX_REQUEST_BYTES, label="successor request"
        )
        closure = portable_v1.reconstruct_v075_k7_successor_portable_profile_closure_v1(
            source_archive_raw=archive_raw,
            transport_profile_raw=transport_raw,
            lifecycle_profile_raw=lifecycle_raw,
            successor_profile_raw=successor_raw,
        )
        replay = portable_v1.replay_v075_k7_successor_request_bytes_portable_v1(
            raw=request_raw,
            profile_closure=closure,
        )
    except BaseException as error:
        _emit_private_failure_detail(channel_fd, "CHILD_INPUT_REPLAY_FAILURE", error)
        try:
            os.close(channel_fd)
        except OSError:
            pass
        return CHILD_INPUT_REPLAY_FAILURE_EXIT_CODE
    try:
        bundle = business_v1.execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1(
            request_replay=replay,
            source_archive_fd=archive_fd,
            sealed_secret_fd=sealed_secret_fd,
            repository_root=repository_root,
            signer_private_root=Path(signer_private_root),
            signer_private_key_path=Path(signer_private_key_path),
        )
    except BaseException as error:
        _emit_private_failure_detail(channel_fd, "CHILD_BUSINESS_FAILURE", error)
        try:
            os.close(channel_fd)
        except OSError:
            pass
        return CHILD_BUSINESS_FAILURE_EXIT_CODE
    try:
        raw = freeze_v075_k7_atomic_child_business_frame_v1(
            request_replay=replay,
            child_bundle=bundle,
            archive_fd=archive_fd,
            atomic_parent_execution_spec_id=atomic_parent_execution_spec_id,
        )
    except BaseException as error:
        _emit_private_failure_detail(channel_fd, "CHILD_FRAME_FAILURE", error)
        try:
            os.close(channel_fd)
        except OSError:
            pass
        return CHILD_FRAME_FAILURE_EXIT_CODE
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(channel_fd, raw[offset:])
            if written <= 0:
                _fail("child channel write made no progress")
            offset += written
        os.close(channel_fd)
        return 0
    except BaseException:
        try:
            os.close(channel_fd)
        except OSError:
            pass
        return CHILD_OUTPUT_FAILURE_EXIT_CODE


__all__ = [
    "CHILD_FAILURE_EXIT_CODE",
    "CHILD_INPUT_REPLAY_FAILURE_EXIT_CODE",
    "CHILD_BUSINESS_FAILURE_EXIT_CODE",
    "CHILD_FRAME_FAILURE_EXIT_CODE",
    "CHILD_OUTPUT_FAILURE_EXIT_CODE",
    "ENTRY_MODULE",
    "ENTRY_SYMBOL",
    "FRAME_ROLE",
    "MAX_CHILD_FRAME_BYTES",
    "MAX_CHILD_FRAME_NONBUSINESS_OVERHEAD_BYTES",
    "MAX_EXECUTED_BUSINESS_BUNDLE_BYTES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075K7AtomicChildEntryV1Error",
    "freeze_v075_k7_atomic_child_business_frame_v1",
    "run_v075_k7_atomic_child_entry_v1",
    "verify_v075_k7_atomic_child_business_frame_bytes_v1",
]
