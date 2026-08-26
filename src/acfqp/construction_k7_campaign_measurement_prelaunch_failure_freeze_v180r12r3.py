"""Freeze the consumed V180r12r3 pre-scientific measurement launch failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any


EXPECTED_CAMPAIGN_ATTEMPT_ID = (
    "457a889a690549ad5efaeb6d3f4799ec2a859068d93eac71730088f90889f967"
)
EXPECTED_LAUNCH_ATTEMPT_ID = (
    "26ab9ac75aa950418708dcdacf674673f22609e87df055b0b1d8d3d96e9f1ee9"
)
EXPECTED_LAUNCH_ATTEMPT_BYTE_COUNT = 1_944
EXPECTED_LAUNCH_ATTEMPT_SHA256 = (
    "72c0bae1bb862078de23a905d8a8c9c1742dfc4a1803d33c7eb6cef3b37cc64b"
)
EXPECTED_LAUNCH_FAILURE_ID = (
    "d120a3e442d3079040e2d635e1e1808990070eece5be44ae84e73d83a52398e8"
)
EXPECTED_LAUNCH_FAILURE_BYTE_COUNT = 8_957
EXPECTED_LAUNCH_FAILURE_SHA256 = (
    "b6d14be33a05ad03b8c1f54a01a5c6190db8127adc9c2a77c79fb026a420c055"
)
EXPECTED_CHILD_STDERR_BYTE_COUNT = 2_297
EXPECTED_CHILD_STDERR_SHA256 = (
    "8e4b4ac3c42aa32771886128dde29260c1cffa40fa2939dd37c5d0675ec0683f"
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "344511707dfc5e623e95e868d282d03182c359e6160fe04542adc2eebff55b7a"
)
EXPECTED_LAUNCH_RULE_ID = (
    "1700936d9145bfa7bcd858128548fd57f003ccf86a63dfdd43d6487f3aae4572"
)

_BASE = Path(__file__).resolve().parents[2] / ".tmp" / "exact-freeze"
_PRELAUNCH = "v180r12r3_campaign_measurement_prelaunch"
_ATTEMPT_RELATIVE_PATH = f"{_PRELAUNCH}/MEASUREMENT_LAUNCH_ATTEMPT.json"
_FAILURE_RELATIVE_PATH = (
    "v180r12r3_campaign_measurement_prelaunch_measurement_launch_failure.json"
)

_RETAINED_FILE_FACTS = (
    (
        "v180r12r3_campaign_measurement_prelaunch_external_root.json",
        3_901,
        "c8452c16b6b5eb3e44ec04545526558d1a9eeff285a09fbfa9a6d4c91adef195",
    ),
    (
        f"{_PRELAUNCH}/bootstrap.py",
        114_437,
        "6e74df6f0cdf296150bb413b82b01c658e2c3e577516e3f7707c9160a1680470",
    ),
    (
        f"{_PRELAUNCH}/launcher.py",
        158_529,
        "25da098ab9ac26c57f79e2a97c363efbbcc69417dc2a668251c1a42d19096dd3",
    ),
    (
        f"{_PRELAUNCH}/launch_manifest.json",
        46_288,
        "3d0fdcd2719168427bbb066ade57721c62262c9e1ce4752850f97a051314c314",
    ),
    (
        f"{_PRELAUNCH}/MATERIALIZATION_TERMINAL.json",
        5_477,
        "208999305db03091ca744e3e0ab758647cdcc3c3aaf59be48acf854dabc24537",
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
    "v180r12r3_campaign_measurement_prelaunch_failure.json",
    f"{_PRELAUNCH}/MEASUREMENT_LAUNCH_RECEIPT.json",
    f"{_PRELAUNCH}/VERIFICATION_LAUNCH_ATTEMPT.json",
    f"{_PRELAUNCH}/VERIFICATION_LAUNCH_RECEIPT.json",
    "v180r12r3_campaign_measurement_prelaunch_verification_launch_failure.json",
    "v180r12r3_campaign_measurement_cas",
    "v180r12r3_campaign_measurement_attempt.json",
    "v180r12r3_campaign_measurement",
    "v180r12r3_campaign_measurement_failure.json",
    "v180r12r3_campaign_measurement_verification.json",
    "v180r12r3_campaign_measurement_verification_failure.json",
    "v180r12r3_campaign_measurement_verification_replay.json",
)

_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_ISSUER = object()


class FrozenCampaignMeasurementPrelaunchFailureV180r12r3Error(ValueError):
    """Raised when the retained V180r12r3 failure boundary changed."""


@dataclass(frozen=True, slots=True)
class FrozenCampaignMeasurementPrelaunchFailureV180r12r3:
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
            _fail("frozen V180r12r3 failure object is foreign")

    def launch_attempt_document(self) -> dict[str, Any]:
        return _canonical_object(self.launch_attempt_bytes, "launch attempt")

    def launch_failure_document(self) -> dict[str, Any]:
        return _canonical_object(self.launch_failure_bytes, "launch failure")

    def __reduce__(self) -> None:
        raise TypeError("frozen V180r12r3 failure is not picklable")


def _fail(message: str) -> None:
    raise FrozenCampaignMeasurementPrelaunchFailureV180r12r3Error(message)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FrozenCampaignMeasurementPrelaunchFailureV180r12r3Error(
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
    _fail(f"forbidden V180r12r3 successor artifact exists: {relative_path}")


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
        and attempt.get("schema") == "acfqp.v180r12r3_prelaunch_launch_attempt.v1"
        and failure.get("schema") == "acfqp.v180r12r3_prelaunch_launch_failure.v1"
        and attempt.get("target") == failure.get("target") == "measurement"
        and failure.get("launch_attempt_id") == attempt_id
        and attempt.get("launch_rule_id")
        == failure.get("launch_rule_id")
        == EXPECTED_LAUNCH_RULE_ID
        and attempt.get("materialization_terminal_id")
        == EXPECTED_MATERIALIZATION_TERMINAL_ID
        and attempt.get("materialization_terminal_byte_count") == 5_477
        and attempt.get("materialization_terminal_sha256")
        == "208999305db03091ca744e3e0ab758647cdcc3c3aaf59be48acf854dabc24537"
        and attempt.get("launch_manifest_sha256")
        == "3d0fdcd2719168427bbb066ade57721c62262c9e1ce4752850f97a051314c314"
        and attempt.get("authorized_child_measurement_execution_attempted") is True
        and attempt.get("authorized_child_measurement_execution_completed") is False
        and attempt.get("scientific_occurrence_started") is False
        and failure.get("return_code") == 1
        and failure.get("timed_out") is False
        and failure.get("failure_type") == "V180r12r3PrelaunchLaunchError"
        and failure.get("failure_message")
        == "source-bound child did not reach its exact durable success state"
        and failure.get("attempt_lock_preserved") is True
        and failure.get("same_target_identity_rerun_forbidden") is True
        and failure.get("authorized_child_measurement_execution_attempted") is True
        and failure.get("authorized_child_measurement_execution_completed") is False
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
        raise FrozenCampaignMeasurementPrelaunchFailureV180r12r3Error(
            "retained child stderr is malformed"
        ) from error
    if not (
        len(stderr_raw) == EXPECTED_CHILD_STDERR_BYTE_COUNT
        and hashlib.sha256(stderr_raw).hexdigest() == EXPECTED_CHILD_STDERR_SHA256
        and "CampaignAttemptAuthorityV180R12R3" in stderr_text
        and "dataclasses.py" in stderr_text
        and "sys.modules.get(cls.__module__).__dict__" in stderr_text
        and "AttributeError: 'NoneType' object has no attribute '__dict__'"
        in stderr_text
        and "V180r12r3 six-process Git contract was incomplete" in stderr_text
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
        if not (
            row.get("campaign_attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
            and row.get("root_name")
            == f"v180r12r3-{EXPECTED_CAMPAIGN_ATTEMPT_ID}"
            and row.get("applicable") is True
            and row.get("ownership_acquired") is True
            and row.get("root_state") == "ABSENT"
            and row.get("supervisor_state") == "ABSENT"
            and row.get("worker_state") == "ABSENT"
            and row.get("residual_tree_or_process_possible") is False
            and row.get("kill_attempted") is False
            and row.get("remove_attempted") is False
            and row.get("error_type") is None
            and row.get("error_message") is None
        ):
            _fail("retained cgroup cleanup observation changed")
    return attempt_id, failure_id


def load_frozen_campaign_measurement_prelaunch_failure_v180r12r3(
    base: Path = _BASE,
) -> FrozenCampaignMeasurementPrelaunchFailureV180r12r3:
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
                f"v180r12r3-{EXPECTED_CAMPAIGN_ATTEMPT_ID}",
                dir_fd=cgroup_parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            _fail("retained V180r12r3 attempt cgroup exists")
    finally:
        os.close(cgroup_parent_fd)
    attempt_raw = retained[_ATTEMPT_RELATIVE_PATH]
    failure_raw = retained[_FAILURE_RELATIVE_PATH]
    attempt_id, failure_id = _require_failure_documents(attempt_raw, failure_raw)
    return FrozenCampaignMeasurementPrelaunchFailureV180r12r3(
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
    "FrozenCampaignMeasurementPrelaunchFailureV180r12r3",
    "FrozenCampaignMeasurementPrelaunchFailureV180r12r3Error",
    "load_frozen_campaign_measurement_prelaunch_failure_v180r12r3",
)
