"""Freeze the consumed V180r12r3r1 pre-scientific measurement launch failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any


EXPECTED_CAMPAIGN_ATTEMPT_ID = (
    "cbffcb66d23630ef46fa014f9467d3ac3054b39dde32ec0b9de22bba41078040"
)
EXPECTED_LAUNCH_ATTEMPT_ID = (
    "eac1fc0f3ca572a736deaf9292101a1835a04ba5176c23e6b2bcceadc26b53c9"
)
EXPECTED_LAUNCH_ATTEMPT_BYTE_COUNT = 1_956
EXPECTED_LAUNCH_ATTEMPT_SHA256 = (
    "416dc788bf4406b15c5cd82ad627f707420d3c24c51c850efd13f8ca74905558"
)
EXPECTED_LAUNCH_FAILURE_ID = (
    "c2b957cf8556560696da92b959706bb7a74b2915df3776c6c28c65a266c1be60"
)
EXPECTED_LAUNCH_FAILURE_BYTE_COUNT = 9_307
EXPECTED_LAUNCH_FAILURE_SHA256 = (
    "74c6fe36e51ec703abfb3fc6e3d9f88e4f8644ccc0640892d9bef58da4473ff0"
)
EXPECTED_CHILD_STDERR_BYTE_COUNT = 2_467
EXPECTED_CHILD_STDERR_SHA256 = (
    "22d64a9a2df0b37a4780726f1b48e1cb41c376810d05200ffb5f2071f6ce833d"
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "8fe982f053c1a2577310f4452881ba4bdb9f9f95758c50c520a3a0a37c17ec11"
)
EXPECTED_LAUNCH_RULE_ID = (
    "7d337317b583520daeb335ff57e2b7814390472fa639d44a0974e0b3dab2c214"
)

_BASE = Path(__file__).resolve().parents[2] / ".tmp" / "exact-freeze"
_PRELAUNCH = "v180r12r3r1_campaign_measurement_prelaunch"
_ATTEMPT_RELATIVE_PATH = f"{_PRELAUNCH}/MEASUREMENT_LAUNCH_ATTEMPT.json"
_FAILURE_RELATIVE_PATH = (
    "v180r12r3r1_campaign_measurement_prelaunch_measurement_launch_failure.json"
)

_RETAINED_FILE_FACTS = (
    (
        "v180r12r3r1_campaign_measurement_prelaunch_external_root.json",
        3_919,
        "08dbcc07fee57acd48c5a419d4f73a9d4eaec37758ef8f8b3c0076e73dd8e1f0",
    ),
    (
        f"{_PRELAUNCH}/bootstrap.py",
        119_050,
        "0c9d85bce72b7abf2199e1b7aca21a7febb44c5a81b64908d04e9c7fde1b08c7",
    ),
    (
        f"{_PRELAUNCH}/launcher.py",
        160_494,
        "a50ab9b13f98442fe8695988c581a6be0e3bd9a19dfddfd4e27f03f24728325c",
    ),
    (
        f"{_PRELAUNCH}/launch_manifest.json",
        48_295,
        "e8843ae4b8194b65179de4ccb59133fa6791e6ad8817de28699349c6645e9766",
    ),
    (
        f"{_PRELAUNCH}/MATERIALIZATION_TERMINAL.json",
        5_503,
        "ceb58f7b09f1a1ac638f0f3e44c7919d1f0a3fde4a8b5172ee8d719755235cb6",
    ),
    (
        _ATTEMPT_RELATIVE_PATH,
        EXPECTED_LAUNCH_ATTEMPT_BYTE_COUNT,
        EXPECTED_LAUNCH_ATTEMPT_SHA256,
    ),
    (
        _FAILURE_RELATIVE_PATH,
        EXPECTED_LAUNCH_FAILURE_BYTE_COUNT,
        EXPECTED_LAUNCH_FAILURE_SHA256,
    ),
)

_PRELAUNCH_EXACT_ENTRIES = frozenset(
    {
        "bootstrap.py",
        "launcher.py",
        "launch_manifest.json",
        "MATERIALIZATION_TERMINAL.json",
        "MEASUREMENT_LAUNCH_ATTEMPT.json",
    }
)

_REQUIRED_ABSENT_PATHS = (
    "v180r12r3r1_campaign_measurement_prelaunch_failure.json",
    f"{_PRELAUNCH}/MEASUREMENT_LAUNCH_RECEIPT.json",
    f"{_PRELAUNCH}/VERIFICATION_LAUNCH_ATTEMPT.json",
    f"{_PRELAUNCH}/VERIFICATION_LAUNCH_RECEIPT.json",
    "v180r12r3r1_campaign_measurement_prelaunch_verification_launch_failure.json",
    "v180r12r3r1_campaign_measurement_cas",
    "v180r12r3r1_campaign_measurement_attempt.json",
    "v180r12r3r1_campaign_measurement",
    "v180r12r3r1_campaign_measurement_failure.json",
    "v180r12r3r1_campaign_measurement_verification.json",
    "v180r12r3r1_campaign_measurement_verification_failure.json",
    "v180r12r3r1_campaign_measurement_verification_replay.json",
)

_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_ISSUER = object()


class FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error(ValueError):
    """Raised when the retained V180r12r3r1 failure boundary changed."""


@dataclass(frozen=True, slots=True)
class FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1:
    _issuer: object = field(repr=False, compare=False)
    launch_attempt_bytes: bytes
    launch_failure_bytes: bytes
    launch_attempt_id: str
    launch_failure_id: str

    def __post_init__(self) -> None:
        attempt_id, failure_id = _require_failure_documents(
            self.launch_attempt_bytes, self.launch_failure_bytes
        )
        if not (
            self._issuer is _ISSUER
            and self.launch_attempt_id == attempt_id
            and self.launch_failure_id == failure_id
        ):
            _fail("frozen V180r12r3r1 failure object is foreign")

    def launch_attempt_document(self) -> dict[str, Any]:
        return _canonical_object(self.launch_attempt_bytes, "launch attempt")

    def launch_failure_document(self) -> dict[str, Any]:
        return _canonical_object(self.launch_failure_bytes, "launch failure")

    def __reduce__(self) -> None:
        raise TypeError("frozen V180r12r3r1 failure is not picklable")


def _fail(message: str) -> None:
    raise FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error(message)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error(
            f"retained {label} is not JSON"
        ) from error
    if type(value) is not dict or _canonical_bytes(value) != raw:
        _fail(f"retained {label} is not a canonical object")
    return value


def _open_absolute_directory_no_symlink(path: Path) -> int:
    if not path.is_absolute():
        _fail("failure evidence base must be absolute")
    descriptor = os.open("/", os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC)
    try:
        for component in path.parts[1:]:
            successor = os.open(
                component,
                os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = successor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_relative_parent(base_fd: int, relative_path: str) -> tuple[int, str]:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or not path.parts or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        _fail("retained failure path is not a strict relative path")
    descriptor = os.dup(base_fd)
    try:
        for component in path.parts[:-1]:
            successor = os.open(
                component,
                os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = successor
        return descriptor, path.parts[-1]
    except BaseException:
        os.close(descriptor)
        raise


def _stable_read(
    base_fd: int,
    relative_path: str,
    expected_size: int,
    expected_sha256: str,
) -> bytes:
    parent_fd, name = _open_relative_parent(base_fd, relative_path)
    try:
        descriptor = os.open(
            name, os.O_RDONLY | _O_NOFOLLOW | _O_CLOEXEC, dir_fd=parent_fd
        )
    finally:
        os.close(parent_fd)
    try:
        before = os.fstat(descriptor)
        if not (
            stat.S_ISREG(before.st_mode)
            and stat.S_IMODE(before.st_mode) == 0o400
            and before.st_nlink == 1
            and before.st_size == expected_size
        ):
            _fail(f"retained file facts changed: {relative_path}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, expected_size + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > expected_size:
                _fail(f"retained file exceeded exact size: {relative_path}")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable_fields = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    raw = b"".join(chunks)
    if (
        stable_fields(before) != stable_fields(after)
        or len(raw) != expected_size
        or hashlib.sha256(raw).hexdigest() != expected_sha256
    ):
        _fail(f"retained file bytes changed: {relative_path}")
    return raw


def _require_absent(base_fd: int, relative_path: str) -> None:
    try:
        parent_fd, name = _open_relative_parent(base_fd, relative_path)
    except FileNotFoundError:
        return
    try:
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
    finally:
        os.close(parent_fd)
    _fail(f"forbidden V180r12r3r1 successor artifact exists: {relative_path}")


def _require_prelaunch_inventory(base_fd: int) -> None:
    descriptor = os.open(
        _PRELAUNCH,
        os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC,
        dir_fd=base_fd,
    )
    try:
        observed = os.fstat(descriptor)
        entries: set[str] = set()
        with os.scandir(descriptor) as iterator:
            for entry in iterator:
                if len(entries) >= len(_PRELAUNCH_EXACT_ENTRIES):
                    _fail("retained prelaunch directory inventory exceeded its cap")
                entries.add(entry.name)
        if not (
            stat.S_ISDIR(observed.st_mode)
            and stat.S_IMODE(observed.st_mode) == 0o700
            and entries == _PRELAUNCH_EXACT_ENTRIES
        ):
            _fail("retained prelaunch directory inventory changed")
    finally:
        os.close(descriptor)


def _require_failure_documents(
    attempt_raw: bytes, failure_raw: bytes
) -> tuple[str, str]:
    attempt = _canonical_object(attempt_raw, "launch attempt")
    failure = _canonical_object(failure_raw, "launch failure")
    attempt_payload = dict(attempt)
    attempt_id = attempt_payload.pop("launch_attempt_id", None)
    failure_payload = dict(failure)
    failure_id = failure_payload.pop("launch_failure_id", None)
    if not (
        attempt_id == EXPECTED_LAUNCH_ATTEMPT_ID
        and attempt_id == hashlib.sha256(_canonical_bytes(attempt_payload)).hexdigest()
        and failure_id == EXPECTED_LAUNCH_FAILURE_ID
        and failure_id == hashlib.sha256(_canonical_bytes(failure_payload)).hexdigest()
        and attempt.get("schema") == "acfqp.v180r12r3r1_prelaunch_launch_attempt.v1"
        and failure.get("schema") == "acfqp.v180r12r3r1_prelaunch_launch_failure.v1"
        and attempt.get("target") == failure.get("target") == "measurement"
        and failure.get("launch_attempt_id") == attempt_id
        and attempt.get("launch_rule_id")
        == failure.get("launch_rule_id")
        == EXPECTED_LAUNCH_RULE_ID
        and attempt.get("materialization_terminal_id")
        == EXPECTED_MATERIALIZATION_TERMINAL_ID
        and attempt.get("materialization_terminal_byte_count") == 5_503
        and attempt.get("materialization_terminal_sha256")
        == "ceb58f7b09f1a1ac638f0f3e44c7919d1f0a3fde4a8b5172ee8d719755235cb6"
        and attempt.get("launch_manifest_sha256")
        == "e8843ae4b8194b65179de4ccb59133fa6791e6ad8817de28699349c6645e9766"
        and attempt.get("authorized_child_measurement_execution_attempted") is True
        and attempt.get("authorized_child_measurement_execution_completed") is False
        and attempt.get("scientific_occurrence_started") is False
        and attempt.get("campaign_actual_measurement") is False
        and attempt.get("same_target_identity_rerun_forbidden") is True
        and attempt.get("preauthorization_supervision") is True
        and attempt.get("producer_free_verification_attempted") is False
        and attempt.get("producer_free_verification_completed") is False
        and failure.get("return_code") == 1
        and failure.get("timed_out") is False
        and failure.get("failure_type") == "V180r12r3r1PrelaunchLaunchError"
        and failure.get("failure_message")
        == "source-bound child did not reach its exact durable success state"
        and failure.get("attempt_lock_preserved") is True
        and failure.get("same_target_identity_rerun_forbidden") is True
        and failure.get("authorized_child_measurement_execution_attempted") is True
        and failure.get("authorized_child_measurement_execution_completed") is False
        and failure.get("producer_free_verification_attempted") is False
        and failure.get("producer_free_verification_completed") is False
        and failure.get("preauthorization_supervision") is True
        and failure.get("success") is False
        and failure.get("campaign_actual_measurement") is False
        and failure.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and failure.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and failure.get("SCALAR_CALIBRATION_GATE") == "NOT_RUN"
        and failure.get("BREAK_EVEN_GATE") == "NOT_RUN"
        and failure.get("official_execution_allowed") is False
    ):
        _fail("retained launch attempt/failure identity or boundary changed")
    stdout = failure.get("child_stdout")
    stderr = failure.get("child_stderr")
    if not (
        stdout
        == {
            "byte_count": 0,
            "retained_prefix_hex": "",
            "retained_prefix_truncated": False,
            "sha256": hashlib.sha256(b"").hexdigest(),
        }
        and type(stderr) is dict
        and set(stderr)
        == {
            "byte_count",
            "retained_prefix_hex",
            "retained_prefix_truncated",
            "sha256",
        }
        and stderr["byte_count"] == EXPECTED_CHILD_STDERR_BYTE_COUNT
        and stderr["retained_prefix_truncated"] is False
        and stderr["sha256"] == EXPECTED_CHILD_STDERR_SHA256
    ):
        _fail("retained child streams changed")
    try:
        stderr_raw = bytes.fromhex(stderr["retained_prefix_hex"])
        stderr_text = stderr_raw.decode("utf-8")
    except (TypeError, ValueError, UnicodeDecodeError) as error:
        raise FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error(
            "retained child stderr is malformed"
        ) from error
    if not (
        len(stderr_raw) == EXPECTED_CHILD_STDERR_BYTE_COUNT
        and hashlib.sha256(stderr_raw).hexdigest() == EXPECTED_CHILD_STDERR_SHA256
        and "bootstrap_entrypoint_v180r12r3r1" in stderr_text
        and "revalidate_external_measurement_pre_attempt_v180r12r3r1"
        in stderr_text
        and "validate_verified_external_launch_context_v180r12r3r1"
        in stderr_text
        and '_fail("external replay document byte join changed")' in stderr_text
        and (
            "_acfqp_v180r12r3r1_precompiled_runner_measurement."
            "V180R12R3R1RuntimeError: external replay document byte join changed"
        )
        in stderr_text
    ):
        _fail("retained child root-cause traceback changed")
    progress = failure.get("progress_observations")
    if type(progress) is not dict or set(progress) != {
        "attempt",
        "evidence_inventory",
        "execution_closure",
        "launch_failure",
        "ledger_closure",
        "measurement_failure",
        "os_receipt",
        "output_root",
        "receipt",
        "retained_replay",
        "runtime_cas",
        "terminal",
        "verification",
        "verification_failure",
    }:
        _fail("retained launch progress schema changed")
    if progress["attempt"] != {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": EXPECTED_LAUNCH_ATTEMPT_BYTE_COUNT,
        "sha256": EXPECTED_LAUNCH_ATTEMPT_SHA256,
    } or any(
        row != {"presence": "ABSENT"}
        for name, row in progress.items()
        if name != "attempt"
    ):
        _fail("retained launch progress observations changed")
    cgroup_rows = failure.get("measurement_cgroup_cleanup_observations")
    if type(cgroup_rows) is not list or tuple(
        row.get("phase") if type(row) is dict else None for row in cgroup_rows
    ) != ("BEFORE_POPEN", "CLEANUP", "AFTER_CHILD"):
        _fail("retained cgroup observation phases changed")
    for row in cgroup_rows:
        expected_row = {
            "applicable": True,
            "campaign_attempt_id": EXPECTED_CAMPAIGN_ATTEMPT_ID,
            "error_message": None,
            "error_type": None,
            "kill_attempted": False,
            "kill_succeeded": False,
            "ownership_acquired": True,
            "phase": row["phase"],
            "remove_attempted": False,
            "remove_succeeded": False,
            "residual_tree_or_process_possible": False,
            "root_device": None,
            "root_inode": None,
            "root_mode": None,
            "root_name": f"v180r12r3r1-{EXPECTED_CAMPAIGN_ATTEMPT_ID}",
            "root_nlink": None,
            "root_populated": None,
            "root_process_count": None,
            "root_state": "ABSENT",
            "supervisor_state": "ABSENT",
            "wait_empty_attempted": False,
            "wait_empty_succeeded": False,
            "worker_state": "ABSENT",
        }
        if row != expected_row:
            _fail("retained cgroup cleanup observation changed")
    return attempt_id, failure_id


def load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1(
    base: Path = _BASE,
) -> FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1:
    base_fd = _open_absolute_directory_no_symlink(base)
    try:
        _require_prelaunch_inventory(base_fd)
        retained = {
            relative: _stable_read(base_fd, relative, size, digest)
            for relative, size, digest in _RETAINED_FILE_FACTS
        }
        for relative in _REQUIRED_ABSENT_PATHS:
            _require_absent(base_fd, relative)
    finally:
        os.close(base_fd)
    cgroup_parent = Path(
        "/sys/fs/cgroup/user.slice/user-1000.slice/"
        "user@1000.service/app.slice"
    )
    cgroup_parent_fd = _open_absolute_directory_no_symlink(cgroup_parent)
    try:
        try:
            os.stat(
                f"v180r12r3r1-{EXPECTED_CAMPAIGN_ATTEMPT_ID}",
                dir_fd=cgroup_parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            _fail("retained V180r12r3r1 attempt cgroup exists")
    finally:
        os.close(cgroup_parent_fd)
    attempt_raw = retained[_ATTEMPT_RELATIVE_PATH]
    failure_raw = retained[_FAILURE_RELATIVE_PATH]
    attempt_id, failure_id = _require_failure_documents(attempt_raw, failure_raw)
    return FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1(
        _issuer=_ISSUER,
        launch_attempt_bytes=attempt_raw,
        launch_failure_bytes=failure_raw,
        launch_attempt_id=attempt_id,
        launch_failure_id=failure_id,
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ATTEMPT_ID",
    "EXPECTED_CHILD_STDERR_BYTE_COUNT",
    "EXPECTED_CHILD_STDERR_SHA256",
    "EXPECTED_LAUNCH_ATTEMPT_BYTE_COUNT",
    "EXPECTED_LAUNCH_ATTEMPT_ID",
    "EXPECTED_LAUNCH_ATTEMPT_SHA256",
    "EXPECTED_LAUNCH_FAILURE_BYTE_COUNT",
    "EXPECTED_LAUNCH_FAILURE_ID",
    "EXPECTED_LAUNCH_FAILURE_SHA256",
    "FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1",
    "FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error",
    "load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1",
)
