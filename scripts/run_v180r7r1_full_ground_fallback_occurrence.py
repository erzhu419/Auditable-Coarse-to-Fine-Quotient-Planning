#!/usr/bin/env python3
"""Execute the fresh V180r7r1 fallback authorization exactly once."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import resource
import stat
from typing import Any, Mapping, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_domain_registry_extension_v180r7r1 as domains
from acfqp import (
    construction_k7_full_ground_fallback_execution_authorization_v180r7r1
    as authorization,
)
from acfqp import (
    construction_k7_full_ground_fallback_execution_authorization_evidence_freeze_v180r7r1
    as authorization_evidence,
)
from acfqp import (
    construction_k7_full_ground_fallback_production_terminal_finalizer_v180r7r1
    as finalizer,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
INPUT_ROOT = ROOT / ".tmp" / "recovery-eligible-retained-v1"
CAS_ROOT = BASE / "v180r7r1_full_ground_fallback_cas"
OUTPUT_ROOT = BASE / "v180r7r1_full_ground_fallback_output"
SUCCESS = BASE / "v180r7r1_full_ground_fallback_terminal_bundle.json"
FAILURE = BASE / "v180r7r1_full_ground_fallback_failure.json"
VERIFICATION = BASE / "v180r7r1_full_ground_fallback_verification.json"

_OLD_CAS_ROOT = BASE / "v180r7_full_ground_fallback_cas"
_OLD_OUTPUT_ROOT = BASE / "v180r7_full_ground_fallback_output"
_OLD_SUCCESS = BASE / "v180r7_full_ground_fallback_terminal_bundle.json"
_OLD_FAILURE = BASE / "v180r7_full_ground_fallback_failure.json"
_MAX_FAILURE_INVENTORY_ENTRIES = 1_024
_MAX_FAILURE_INVENTORY_BYTES = 64 * 1024 * 1024


class V180r7r1OccurrenceRunnerError(RuntimeError):
    """The fresh authorization or its one-shot filesystem boundary changed."""


class V180r7r1OccurrenceReplayForbidden(V180r7r1OccurrenceRunnerError):
    """An exact completed successor terminal must remain unchanged."""


def _fail(message: str) -> NoReturn:
    raise V180r7r1OccurrenceRunnerError(message)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_regular_symlink_free(path: Path) -> bytes:
    try:
        return source_runtime_v2._read_regular_symlink_free(path)  # noqa: SLF001
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise V180r7r1OccurrenceRunnerError(
            "runner input or terminal is absent, linked, or nonregular"
        ) from error


def _write_once(path: Path, raw: bytes) -> None:
    if type(raw) is not bytes or not raw:
        _fail("runner write-once bytes are absent")
    descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
        0o400,
    )
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V180r7r1 occurrence terminal short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _entry_state(path: Path) -> dict[str, Any]:
    if not os.path.lexists(path):
        return {"presence": "ABSENT", "byte_count": None, "sha256": None}
    item_stat = os.lstat(path)
    if stat.S_ISLNK(item_stat.st_mode):
        return {"presence": "SYMLINK", "byte_count": None, "sha256": None}
    if stat.S_ISDIR(item_stat.st_mode):
        return {"presence": "DIRECTORY", "byte_count": None, "sha256": None}
    if stat.S_ISREG(item_stat.st_mode):
        raw = _read_regular_symlink_free(path)
        return {
            "presence": "REGULAR_FILE",
            "byte_count": len(raw),
            "sha256": _sha256(raw),
        }
    return {"presence": "OTHER", "byte_count": None, "sha256": None}


def _output_progress_inventory(root: Path) -> dict[str, Any]:
    root_state = _entry_state(root)
    rows: list[dict[str, Any]] = []
    byte_count = 0
    if root_state["presence"] == "DIRECTORY":
        pending = [root]
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda item: item.name)
            children: list[Path] = []
            for entry in entries:
                path = Path(entry.path)
                state = _entry_state(path)
                row = {
                    "relative_path": path.relative_to(root).as_posix(),
                    **state,
                }
                rows.append(row)
                if len(rows) > _MAX_FAILURE_INVENTORY_ENTRIES:
                    _fail("runner failure inventory exceeds its entry cap")
                if state["presence"] == "REGULAR_FILE":
                    byte_count += state["byte_count"]
                    if byte_count > _MAX_FAILURE_INVENTORY_BYTES:
                        _fail("runner failure inventory exceeds its byte cap")
                elif state["presence"] == "DIRECTORY":
                    children.append(path)
            pending.extend(reversed(children))
    rows.sort(key=lambda row: row["relative_path"])
    return {
        "root": root_state,
        "entries": rows,
        "entry_count": len(rows),
        "regular_file_count": sum(
            row["presence"] == "REGULAR_FILE" for row in rows
        ),
        "regular_file_byte_count": byte_count,
        "symlink_count": sum(row["presence"] == "SYMLINK" for row in rows),
        "entries_sha256": _sha256(canonical_json_bytes(rows)),
        "inventory_complete_within_frozen_caps": True,
    }


def _failure_document(
    error: BaseException,
    *,
    authorization_id: str,
    protocol_id: str,
    slot_id: str,
    failed_phase: str,
) -> tuple[dict[str, Any], bytes]:
    message = str(error)
    if len(message.encode("utf-8")) > 64 * 1024:
        _fail("runner failure message exceeds its finite cap")
    payload = {
        "schema": "acfqp.full_ground_fallback_execution_failure.v180r7r1",
        "fallback_execution_authorization_id": authorization_id,
        "fallback_execution_protocol_id": protocol_id,
        "production_execution_slot_id": slot_id,
        "preserved_v180r7_authorization_id": (
            authorization.PRESERVED_V180R7_AUTHORIZATION_ID
        ),
        "preserved_v180r7_failure_id": authorization.PRESERVED_V180R7_FAILURE_ID,
        "failed_phase": failed_phase,
        "failure_type": f"{type(error).__module__}.{type(error).__qualname__}",
        "failure_message": message,
        "failure_message_sha256": _sha256(message.encode("utf-8")),
        "runtime_cas_state": _entry_state(CAS_ROOT),
        "output_progress_inventory": _output_progress_inventory(OUTPUT_ROOT),
        "terminal_state": _entry_state(SUCCESS),
        "verification_state": _entry_state(VERIFICATION),
        "old_v180r7_failure_state": _entry_state(_OLD_FAILURE),
        "old_v180r7_authorization_rerun": False,
        "same_authorization_rerun_forbidden": True,
        "failure_evidence_write_once_o_excl_required": True,
        "failure_evidence_file_fsync_required": True,
        "failure_evidence_directory_fsync_required": True,
        "fresh_fallback_execution_started": failed_phase
        in {"FRESH_PRODUCTION_OCCURRENCE", "DURABLE_TERMINAL_WRITE"},
        "scientific_success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "failure_id": domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_FAILURE_V180R7R1_DOMAIN,
            payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if len(raw) > 8 * 1024 * 1024:
        _fail("runner failure evidence exceeds its finite cap")
    return document, raw


def _write_failure_once(
    error: BaseException,
    *,
    authorization_id: str,
    protocol_id: str,
    slot_id: str,
    failed_phase: str,
) -> None:
    document, raw = _failure_document(
        error,
        authorization_id=authorization_id,
        protocol_id=protocol_id,
        slot_id=slot_id,
        failed_phase=failed_phase,
    )
    _write_once(FAILURE, raw)
    print("V180R7R1_FALLBACK_FAILURE", document["failure_id"], flush=True)


def _exact_completed_success_present(
    authorization_document: Mapping[str, Any],
) -> bool:
    try:
        raw = _read_regular_symlink_free(SUCCESS)
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            return False
        payload = dict(document)
        terminal_id = payload.pop("production_terminal_bundle_id", None)
        slot = authorization_document["production_execution_slot"]
        return (
            terminal_id
            == domains.extension_content_id_v180r7r1(
                domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_TERMINAL_V180R7R1_DOMAIN,
                payload,
            )
            and document.get("schema")
            == "acfqp.full_ground_fallback_production_terminal_bundle.v180r7r1"
            and document.get("fallback_execution_protocol_id")
            == authorization_document["fallback_execution_protocol_id"]
            and document.get("production_execution_slot") == slot
            and document.get("terminal_code") == "FULL_GROUND_FALLBACK"
            and OUTPUT_ROOT.is_dir()
            and CAS_ROOT.is_dir()
            and not os.path.lexists(FAILURE)
        )
    except (KeyError, OSError, TypeError, ValueError, V180r7r1OccurrenceRunnerError):
        return False


def _read_retained_input(
    filename: str,
    *,
    byte_count: int,
    sha256: str,
) -> bytes:
    raw = _read_regular_symlink_free(INPUT_ROOT / filename)
    if len(raw) != byte_count or _sha256(raw) != sha256:
        _fail(f"retained input changed: {filename}")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"retained input is not canonical: {filename}")
    return raw


def _set_address_space_cap() -> None:
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = authorization.ADDRESS_SPACE_HARD_CAP_BYTES
    if hard != resource.RLIM_INFINITY and hard < cap:
        _fail("address-space hard limit is below the frozen 24 GiB cap")
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    current = resource.getrlimit(resource.RLIMIT_AS)
    if current != (cap, cap):
        _fail("address-space limit did not equal the frozen cap")


def _old_failure_boundary_is_preserved() -> bool:
    return (
        not os.path.lexists(_OLD_CAS_ROOT)
        and _OLD_OUTPUT_ROOT.is_dir()
        and not os.path.lexists(_OLD_SUCCESS)
        and _OLD_FAILURE.is_file()
    )


def main() -> None:
    frozen_evidence = (
        authorization_evidence
        .freeze_full_ground_fallback_execution_authorization_evidence_v180r7r1()
    )
    if os.path.lexists(FAILURE):
        _fail("V180r7r1 failure evidence already exists; rerun forbidden")
    frozen = (
        authorization.freeze_full_ground_fallback_execution_authorization_v180r7r1()
    )
    authorization_document = frozen.to_document()
    slot = authorization_document["production_execution_slot"]
    protocol_id = authorization_document["fallback_execution_protocol_id"]
    slot_id = slot["production_execution_slot_id"]
    if frozen_evidence.authorization_id != frozen.authorization_id:
        _fail("post-prereg authorization evidence identity changed")
    if (
        os.path.lexists(SUCCESS)
        and _exact_completed_success_present(authorization_document)
    ):
        raise V180r7r1OccurrenceReplayForbidden(
            "exact V180r7r1 occurrence already completed; rerun forbidden"
        )
    failed_phase = "PREEXISTING_PROGRESS_CHECK"
    try:
        if any(
            os.path.lexists(path)
            for path in (CAS_ROOT, OUTPUT_ROOT, SUCCESS, VERIFICATION)
        ):
            _fail("V180r7r1 authorization already has partial progress")
        if not _old_failure_boundary_is_preserved():
            _fail("preserved V180r7 failure boundary changed")
        failed_phase = "AUTHORIZATION_REPLAY"
        if frozen.authorization_id != authorization.EXPECTED_AUTHORIZATION_ID:
            _fail("V180r7r1 authorization identity changed")
        authorization.replay_authorization_source_facts_v180r7r1(
            authorization_document
        )
        failed_phase = "RESOURCE_CAP_INSTALLATION"
        _set_address_space_cap()
        failed_phase = "RETAINED_INPUT_REPLAY"
        binding = _read_retained_input(
            "SOURCE_BUNDLE_BINDING.json",
            byte_count=authorization.EXPECTED_BINDING_BYTE_COUNT,
            sha256=authorization.EXPECTED_BINDING_SHA256,
        )
        snapshot = _read_retained_input(
            "REUSABLE_RAPM_SNAPSHOT.json",
            byte_count=authorization.EXPECTED_SNAPSHOT_BYTE_COUNT,
            sha256=authorization.EXPECTED_SNAPSHOT_SHA256,
        )
        transition = _read_retained_input(
            "PROOF_DEPENDENCY_TRANSITION.json",
            byte_count=authorization.EXPECTED_TRANSITION_BYTE_COUNT,
            sha256=authorization.EXPECTED_TRANSITION_SHA256,
        )
        failed_phase = "FRESH_PRODUCTION_OCCURRENCE"
        result = finalizer.run_full_ground_fallback_production_occurrence_v180r7r1(
            repository_root=ROOT,
            runtime_cas_root=CAS_ROOT,
            output_directory=OUTPUT_ROOT,
            binding_bytes=binding,
            snapshot_bytes=snapshot,
            transition_bytes=transition,
        )
        failed_phase = "DURABLE_TERMINAL_WRITE"
        _write_once(SUCCESS, result.canonical_bytes)
        print(
            "V180R7R1_FALLBACK_SUCCESS",
            result.production_terminal_bundle_id,
            len(result.canonical_bytes),
            _sha256(result.canonical_bytes),
            flush=True,
        )
    except V180r7r1OccurrenceReplayForbidden:
        raise
    except BaseException as error:
        _write_failure_once(
            error,
            authorization_id=frozen.authorization_id,
            protocol_id=protocol_id,
            slot_id=slot_id,
            failed_phase=failed_phase,
        )
        raise


if __name__ == "__main__":
    main()
