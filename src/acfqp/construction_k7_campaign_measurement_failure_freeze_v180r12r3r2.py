"""Freeze the consumed V180r12r3r2 scientific-internal campaign failure.

The retained bytes prove a two-event prefix of the preregistered 625-event
schedule.  PROCESS_BIRTH_INTENT is durable only after cgroup topology creation
returns and before the supervisor-birth call in the pinned measurement runner.
The retained traceback proves PermissionError during that supervisor-birth
path; it does not identify one exact failing syscall and does not support a
cgroup-mkdir-failure claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any


FAILURE_CLAIM_BOUNDARY = (
    "PERMISSION_DENIED_DURING_SUPERVISOR_BIRTH_OR_CLONE_PATH;"
    "EXACT_FAILING_SYSCALL_UNPROVEN"
)
EXPECTED_SUCCESS_EVENT_COUNT = 625
EXPECTED_RETAINED_EVENT_COUNT = 2
EXPECTED_CAMPAIGN_ATTEMPT_ID = (
    "3de63370a50ba83d42ab45d5dc4a22fac9799bc2ab6bd1816d667e009b85292e"
)
EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID = (
    "6acbbba7d8754550f3f474df21433b6a41b1166847619559064f912d8f96fb2c"
)
EXPECTED_LAUNCH_ATTEMPT_ID = (
    "4e0a7ab35b5d1d8f0bd13a2c19d474d7fae871baf767f15e821f2fcf734e3c68"
)
EXPECTED_LAUNCH_ATTEMPT_BYTE_COUNT = 1_956
EXPECTED_LAUNCH_ATTEMPT_SHA256 = (
    "1319eb60cb2826a4e9947ce3b88bb5fdff982087f572c34cdf8b4b3e350ed57e"
)
EXPECTED_LAUNCH_FAILURE_ID = (
    "594c08d5932d0f7188b232485f6e9a08a0d4b041aa2c9f84aa0095d2b1591935"
)
EXPECTED_LAUNCH_FAILURE_BYTE_COUNT = 8_190
EXPECTED_LAUNCH_FAILURE_SHA256 = (
    "c4f1c7d1050b09a713df26e0761614e10b9eee998e192617611b9f3a88790be8"
)
EXPECTED_CHILD_STDERR_BYTE_COUNT = 1_846
EXPECTED_CHILD_STDERR_SHA256 = (
    "94d3bea2c73fc6fbb7115d2c820e0940cb49d0ae6d99d5ceda1e6affab645cf4"
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "455db3acf737a868af5934f6ee657f92d057faa15a882f294df68f18b03b0c4f"
)
EXPECTED_LAUNCH_RULE_ID = (
    "81800fcc4df38b93b0af3c430b324b060fe5d2a1bdec90bf2821685ca156c038"
)
EXPECTED_FAILURE_STATE_ID = (
    "1ff2239cd5ca71f588149e987cded8fe5b8dbf75e7d7098435fda0955fffd09d"
)
EXPECTED_EVENT_IDS = (
    "f7cb99e26ef03caaead41d987d031ad7636fe81216a34f2c4c36591abb6f0282",
    "356b136e203aa884f4a40352a4e62c20f9c92d855279e9396666c77485843c9e",
)
EXPECTED_PARTIAL_OBSERVATIONS_SHA256 = (
    "8e75f9a6f539fbd6ea85241b1f502f11a917337dc50c9e0451292ad9260076ad"
)
EXPECTED_CGROUP_FAILURE_OBSERVATION_SHA256 = (
    "c7d8a453677928addaf084348e0d5ef274fbbf5a26e6b586b36323176ea3e37f"
)
EXPECTED_MEASUREMENT_RUNNER_BYTE_COUNT = 259_113
EXPECTED_MEASUREMENT_RUNNER_SHA256 = (
    "097bf3308debb6ecd589ee4d6902b7b0f1753a64a6226ce8c6dd731f8167534e"
)
FAILURE_EVIDENCE_BASE_COMPONENT_COUNT_CAP = 64
FAILURE_EVIDENCE_BASE_TOTAL_BYTE_CAP = 4_096

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_BASE = _REPOSITORY_ROOT / ".tmp" / "exact-freeze"
_PRELAUNCH = "v180r12r3r2_campaign_measurement_prelaunch"
_OUTPUT = "v180r12r3r2_campaign_measurement"
_EVENTS = f"{_OUTPUT}/EVENTS"
_ATTEMPT_RELATIVE_PATH = f"{_PRELAUNCH}/MEASUREMENT_LAUNCH_ATTEMPT.json"
_LAUNCH_FAILURE_RELATIVE_PATH = (
    "v180r12r3r2_campaign_measurement_prelaunch_measurement_launch_failure.json"
)
_SCIENTIFIC_ATTEMPT_RELATIVE_PATH = "v180r12r3r2_campaign_measurement_attempt.json"
_MEASUREMENT_FAILURE_RELATIVE_PATH = "v180r12r3r2_campaign_measurement_failure.json"
_MATERIALIZATION_RELATIVE_PATH = f"{_PRELAUNCH}/MATERIALIZATION_TERMINAL.json"
_MANIFEST_RELATIVE_PATH = f"{_PRELAUNCH}/launch_manifest.json"
_EXTERNAL_ROOT_RELATIVE_PATH = (
    "v180r12r3r2_campaign_measurement_prelaunch_external_root.json"
)
_EVENT_RELATIVE_PATHS = (
    f"{_EVENTS}/000000.json",
    f"{_EVENTS}/000001.json",
)
_OBSERVATION_PREFIX = ".tmp/exact-freeze"


def _observation_path(relative_path: str) -> str:
    return f"{_OBSERVATION_PREFIX}/{relative_path}"


_MEASUREMENT_RUNNER_RELATIVE_PATH = (
    "scripts/run_v180r12r3r2_campaign_measurement.py"
)

_RETAINED_FILE_FACTS = (
    (
        _EXTERNAL_ROOT_RELATIVE_PATH,
        3_919,
        "b1f3b5c4ead6df6a48d6e6ac44138eef072f10d548b66b04ca5e4dd5ba6b9027",
    ),
    (
        f"{_PRELAUNCH}/bootstrap.py",
        119_203,
        "acb059ee42bd020b9097a8c093ff03072bb06cf6589444533dbeea93b56e8c47",
    ),
    (
        f"{_PRELAUNCH}/launcher.py",
        160_494,
        "44038b046846fae9af275c4653c0d0154ab238903cdde6d5c4a8bf0af31941ea",
    ),
    (
        _MANIFEST_RELATIVE_PATH,
        49_069,
        "9c49eeafe61c63edca3acc33db6f6c14f3dd4032ab6ac117aafebdbd7f4b0009",
    ),
    (
        _MATERIALIZATION_RELATIVE_PATH,
        5_503,
        "92fab45e0b3f3d734d339958619bcda2118c7bf62664e412ff5b973be5d92211",
    ),
    (
        _ATTEMPT_RELATIVE_PATH,
        EXPECTED_LAUNCH_ATTEMPT_BYTE_COUNT,
        EXPECTED_LAUNCH_ATTEMPT_SHA256,
    ),
    (
        _LAUNCH_FAILURE_RELATIVE_PATH,
        EXPECTED_LAUNCH_FAILURE_BYTE_COUNT,
        EXPECTED_LAUNCH_FAILURE_SHA256,
    ),
    (
        _SCIENTIFIC_ATTEMPT_RELATIVE_PATH,
        1_184,
        "6c19f4d0a6ae65f3276ae977cb38d58ff27731b0aa4f9180236c76b681a09536",
    ),
    (
        _MEASUREMENT_FAILURE_RELATIVE_PATH,
        6_890,
        "e829ae0dc47eb0885a4489d9d4a02effccc497542a078752d954437bfb9d10ee",
    ),
    (
        _EVENT_RELATIVE_PATHS[0],
        768,
        "64871a6d1d0257d8c8d2fc758cfac5362585648fba490fabdb07f6612ec207a2",
    ),
    (
        _EVENT_RELATIVE_PATHS[1],
        776,
        "9849baea4cf4ce15a17127ce06c6276c652666f55750ed538c0d25452c2aae3f",
    ),
)
_SOURCE_FILE_FACTS = (
    (
        _MEASUREMENT_RUNNER_RELATIVE_PATH,
        EXPECTED_MEASUREMENT_RUNNER_BYTE_COUNT,
        EXPECTED_MEASUREMENT_RUNNER_SHA256,
    ),
)
EXPECTED_RETAINED_FAILURE_TOTAL_BYTE_COUNT = sum(
    size for _relative, size, _digest in _RETAINED_FILE_FACTS
)
_RETAINED_FILE_FACT_BY_PATH = {
    relative: (size, digest)
    for relative, size, digest in _RETAINED_FILE_FACTS
}
_PRELAUNCH_EXACT_ENTRIES = frozenset(
    {
        "bootstrap.py",
        "launcher.py",
        "launch_manifest.json",
        "MATERIALIZATION_TERMINAL.json",
        "MEASUREMENT_LAUNCH_ATTEMPT.json",
    }
)
_OUTPUT_EXACT_ENTRIES = frozenset({"EVENTS"})
_EVENTS_EXACT_ENTRIES = frozenset({"000000.json", "000001.json"})
_REQUIRED_ABSENT_PATHS = (
    "v180r12r3r2_campaign_measurement_prelaunch_failure.json",
    f"{_PRELAUNCH}/MEASUREMENT_LAUNCH_RECEIPT.json",
    f"{_PRELAUNCH}/VERIFICATION_LAUNCH_ATTEMPT.json",
    f"{_PRELAUNCH}/VERIFICATION_LAUNCH_RECEIPT.json",
    "v180r12r3r2_campaign_measurement_prelaunch_verification_launch_failure.json",
    f"{_OUTPUT}/SUBJECT_RESULT.json.partial",
    f"{_OUTPUT}/SUBJECT_RESULT.json",
    f"{_OUTPUT}/EVIDENCE_INVENTORY.json",
    f"{_OUTPUT}/EXECUTION_CLOSURE.json",
    f"{_OUTPUT}/OS_RECEIPT.json",
    f"{_OUTPUT}/LEDGER_CLOSURE.json",
    f"{_OUTPUT}/TERMINAL.json",
    "v180r12r3r2_campaign_measurement_cas",
    "v180r12r3r2_campaign_measurement_verification.json",
    "v180r12r3r2_campaign_measurement_verification_failure.json",
    "v180r12r3r2_campaign_measurement_verification_replay.json",
)

_ATTEMPT_RECORD_DOMAIN = (
    "acfqp:construction-k7-campaign-attempt-record:v180r12r3r2e"
)
_EVENT_DOMAIN = "acfqp:construction-k7-campaign-ledger-event:v180r12r3r2e"
_FAILURE_STATE_DOMAIN = (
    "acfqp:construction-k7-campaign-failure-state-receipt:v180r12r3r2e"
)
_CAMPAIGN_ATTEMPT_DOMAIN = (
    "acfqp:construction-k7-campaign-measurement-attempt:v180r12r3r2"
)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_ISSUER = object()


class FrozenCampaignMeasurementFailureV180r12r3r2Error(ValueError):
    """Raised when the retained V180r12r3r2 failure boundary changed."""


@dataclass(frozen=True, slots=True)
class FrozenCampaignMeasurementFailureV180r12r3r2:
    _issuer: object = field(repr=False, compare=False)
    external_root_bytes: bytes = field(repr=False)
    materialization_terminal_bytes: bytes = field(repr=False)
    launch_manifest_bytes: bytes = field(repr=False)
    launch_attempt_bytes: bytes = field(repr=False)
    launch_failure_bytes: bytes = field(repr=False)
    scientific_attempt_bytes: bytes = field(repr=False)
    measurement_failure_bytes: bytes = field(repr=False)
    event_bytes: tuple[bytes, bytes] = field(repr=False)
    launch_attempt_id: str
    launch_failure_id: str
    campaign_attempt_id: str
    campaign_attempt_record_id: str
    failure_state_id: str
    event_ids: tuple[str, str]

    def __post_init__(self) -> None:
        _require_frozen_object_boundary(self)
        identities = _require_failure_documents(
            self.external_root_bytes,
            self.materialization_terminal_bytes,
            self.launch_manifest_bytes,
            self.launch_attempt_bytes,
            self.launch_failure_bytes,
            self.scientific_attempt_bytes,
            self.measurement_failure_bytes,
            self.event_bytes,
        )
        if not (
            self._issuer is _ISSUER
            and self.launch_attempt_id == identities["launch_attempt_id"]
            and self.launch_failure_id == identities["launch_failure_id"]
            and self.campaign_attempt_id == identities["campaign_attempt_id"]
            and self.campaign_attempt_record_id
            == identities["campaign_attempt_record_id"]
            and self.failure_state_id == identities["failure_state_id"]
            and self.event_ids == identities["event_ids"]
        ):
            _fail("frozen V180r12r3r2 failure object is foreign")

    def launch_attempt_document(self) -> dict[str, Any]:
        return _canonical_object(self.launch_attempt_bytes, "launch attempt")

    def launch_failure_document(self) -> dict[str, Any]:
        return _canonical_object(self.launch_failure_bytes, "launch failure")

    def scientific_attempt_document(self) -> dict[str, Any]:
        return _canonical_object(self.scientific_attempt_bytes, "scientific attempt")

    def measurement_failure_document(self) -> dict[str, Any]:
        return _canonical_object(self.measurement_failure_bytes, "measurement failure")

    def event_documents(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            _canonical_object(self.event_bytes[0], "event 000000"),
            _canonical_object(self.event_bytes[1], "event 000001"),
        )

    def __reduce__(self) -> None:
        raise TypeError("frozen V180r12r3r2 failure is not picklable")


def _fail(message: str) -> None:
    raise FrozenCampaignMeasurementFailureV180r12r3r2Error(message)


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _require_frozen_object_boundary(
    value: FrozenCampaignMeasurementFailureV180r12r3r2,
) -> None:
    if value._issuer is not _ISSUER:
        _fail("frozen V180r12r3r2 failure object is foreign")
    if type(value.event_bytes) is not tuple:
        _fail("frozen V180r12r3r2 event bytes tuple is foreign")
    if type(value.event_ids) is not tuple:
        _fail("frozen V180r12r3r2 event ID tuple is foreign")
    if len(value.event_bytes) != EXPECTED_RETAINED_EVENT_COUNT or any(
        type(raw) is not bytes for raw in value.event_bytes
    ):
        _fail("frozen V180r12r3r2 event bytes are foreign")
    if len(value.event_ids) != EXPECTED_RETAINED_EVENT_COUNT or any(
        type(identity) is not str for identity in value.event_ids
    ):
        _fail("frozen V180r12r3r2 event IDs are foreign")

    raw_rows = (
        (
            "external root",
            value.external_root_bytes,
            _EXTERNAL_ROOT_RELATIVE_PATH,
        ),
        (
            "materialization terminal",
            value.materialization_terminal_bytes,
            _MATERIALIZATION_RELATIVE_PATH,
        ),
        ("launch manifest", value.launch_manifest_bytes, _MANIFEST_RELATIVE_PATH),
        ("launch attempt", value.launch_attempt_bytes, _ATTEMPT_RELATIVE_PATH),
        (
            "launch failure",
            value.launch_failure_bytes,
            _LAUNCH_FAILURE_RELATIVE_PATH,
        ),
        (
            "scientific attempt",
            value.scientific_attempt_bytes,
            _SCIENTIFIC_ATTEMPT_RELATIVE_PATH,
        ),
        (
            "measurement failure",
            value.measurement_failure_bytes,
            _MEASUREMENT_FAILURE_RELATIVE_PATH,
        ),
        ("event 000000", value.event_bytes[0], _EVENT_RELATIVE_PATHS[0]),
        ("event 000001", value.event_bytes[1], _EVENT_RELATIVE_PATHS[1]),
    )
    if any(type(raw) is not bytes for _label, raw, _relative in raw_rows):
        _fail("frozen V180r12r3r2 raw bytes are foreign")

    scalar_id_rows = (
        (value.launch_attempt_id, EXPECTED_LAUNCH_ATTEMPT_ID),
        (value.launch_failure_id, EXPECTED_LAUNCH_FAILURE_ID),
        (value.campaign_attempt_id, EXPECTED_CAMPAIGN_ATTEMPT_ID),
        (
            value.campaign_attempt_record_id,
            EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
        ),
        (value.failure_state_id, EXPECTED_FAILURE_STATE_ID),
    )
    if any(type(observed) is not str for observed, _expected in scalar_id_rows):
        _fail("frozen V180r12r3r2 scalar IDs are foreign")
    if not (
        all(
            _is_sha256_hex(observed) and observed == expected
            for observed, expected in scalar_id_rows
        )
        and all(_is_sha256_hex(identity) for identity in value.event_ids)
        and value.event_ids == EXPECTED_EVENT_IDS
    ):
        _fail("frozen V180r12r3r2 IDs changed")

    total_byte_count = 0
    for label, raw, relative_path in raw_rows:
        expected_size, expected_sha256 = _RETAINED_FILE_FACT_BY_PATH[relative_path]
        total_byte_count += len(raw)
        if not (
            len(raw) == expected_size
            and hashlib.sha256(raw).hexdigest() == expected_sha256
        ):
            _fail(f"frozen V180r12r3r2 raw bytes changed: {label}")
    expected_object_byte_count = sum(
        _RETAINED_FILE_FACT_BY_PATH[relative][0]
        for _label, _raw, relative in raw_rows
    )
    if total_byte_count != expected_object_byte_count:
        _fail("frozen V180r12r3r2 object byte total changed")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"retained {label} bytes are foreign")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FrozenCampaignMeasurementFailureV180r12r3r2Error(
            f"retained {label} is not JSON"
        ) from error
    if type(value) is not dict or _canonical_bytes(value) != raw:
        _fail(f"retained {label} is not a canonical object")
    return value


def _domain_id(domain: str, payload: object) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + _canonical_bytes(payload)
    ).hexdigest()


def _self_id(
    document: dict[str, Any],
    identity_field: str,
    expected: str,
    *,
    domain: str | None = None,
) -> str:
    payload = dict(document)
    observed = payload.pop(identity_field, None)
    computed = (
        hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        if domain is None
        else _domain_id(domain, payload)
    )
    if observed != expected or observed != computed:
        _fail(f"retained {identity_field} changed")
    return observed


def _open_absolute_directory_no_symlink(path: Path) -> int:
    if type(path) is not type(_BASE):
        _fail("failure evidence base path is foreign")
    parts = path.parts
    encoded = os.fsencode(path)
    if not (
        path.is_absolute()
        and 0 < len(parts) - 1 <= FAILURE_EVIDENCE_BASE_COMPONENT_COUNT_CAP
        and len(encoded) <= FAILURE_EVIDENCE_BASE_TOTAL_BYTE_CAP
        and b"\x00" not in encoded
        and all(component not in {"", ".", ".."} for component in parts[1:])
    ):
        _fail("failure evidence base exceeds its bounded path caps")
    descriptor = os.open("/", os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC)
    try:
        for component in parts[1:]:
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


def _strict_relative_parts(relative_path: str) -> tuple[str, ...]:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or not path.parts or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        _fail("retained failure path is not a strict relative path")
    return path.parts


def _open_relative_parent(base_fd: int, relative_path: str) -> tuple[int, str]:
    parts = _strict_relative_parts(relative_path)
    descriptor = os.dup(base_fd)
    try:
        for component in parts[:-1]:
            successor = os.open(
                component,
                os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = successor
        return descriptor, parts[-1]
    except BaseException:
        os.close(descriptor)
        raise


def _open_relative_directory(base_fd: int, relative_path: str) -> int:
    parts = _strict_relative_parts(relative_path)
    descriptor = os.dup(base_fd)
    try:
        for component in parts:
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


def _stable_read(
    base_fd: int,
    relative_path: str,
    expected_size: int,
    expected_sha256: str,
    *,
    expected_mode: int,
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
            and stat.S_IMODE(before.st_mode) == expected_mode
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
    _fail(f"forbidden V180r12r3r2 artifact exists: {relative_path}")


def _require_inventory(
    base_fd: int,
    relative_path: str,
    expected_entries: frozenset[str],
    *,
    expected_mode: int,
    expected_nlink: int,
) -> None:
    descriptor = _open_relative_directory(base_fd, relative_path)
    try:
        before = os.fstat(descriptor)
        entries: set[str] = set()
        with os.scandir(descriptor) as iterator:
            for entry in iterator:
                if len(entries) >= len(expected_entries):
                    _fail(f"retained {relative_path} inventory exceeded its cap")
                entries.add(entry.name)
        after = os.fstat(descriptor)
        stable_fields = lambda value: (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_nlink,
            value.st_uid,
            value.st_gid,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )
        if not (
            stable_fields(before) == stable_fields(after)
            and stat.S_ISDIR(before.st_mode)
            and stat.S_IMODE(before.st_mode) == expected_mode
            and before.st_nlink == expected_nlink
            and entries == expected_entries
        ):
            _fail(f"retained {relative_path} directory inventory changed")
    finally:
        os.close(descriptor)


def _require_runner_causal_source(raw: bytes) -> None:
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FrozenCampaignMeasurementFailureV180r12r3r2Error(
            "pinned measurement runner is not UTF-8"
        ) from error
    event_zero = 'boundary="durable ATTEMPT_OPEN"'
    create = "cgroup, topology_receipt = adapter.create_cgroup(attempt_id)"
    register = "campaign.register_evidence_document(topology_receipt)"
    birth_plan = "birth_plan = campaign.success_event_plan[campaign.event_count]"
    launch = "child, supervisor_birth_receipt = adapter.launch_supervisor("
    markers = (event_zero, create, register, birth_plan, launch)
    positions = tuple(source.find(marker) for marker in markers)
    between_topology_and_birth = source[positions[2] : positions[3]]
    if not (
        source.count(
            f"SUCCESS_EVENT_COUNT = {EXPECTED_SUCCESS_EVENT_COUNT}"
        )
        == 1
        and all(position >= 0 for position in positions)
        and positions == tuple(sorted(set(positions)))
        and all(source.count(marker) == 1 for marker in markers)
        and "_append_next_event_v180r12r3r2(" in between_topology_and_birth
    ):
        _fail("pinned runner cgroup-to-supervisor-birth causal order changed")


def _require_streams(launch_failure: dict[str, Any]) -> None:
    stdout = launch_failure.get("child_stdout")
    stderr = launch_failure.get("child_stderr")
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
        raise FrozenCampaignMeasurementFailureV180r12r3r2Error(
            "retained child stderr is malformed"
        ) from error
    if not (
        len(stderr_raw) == EXPECTED_CHILD_STDERR_BYTE_COUNT
        and hashlib.sha256(stderr_raw).hexdigest() == EXPECTED_CHILD_STDERR_SHA256
        and "bootstrap_entrypoint_v180r12r3r2" in stderr_text
        and "run_one_shot_outer_v180r12r3r2" in stderr_text
        and "raise primary" in stderr_text
        and "PermissionError: [Errno 13] Permission denied" in stderr_text
        and "clone3" not in stderr_text
        and "mkdir" not in stderr_text
    ):
        _fail("retained supervisor-birth root-cause traceback changed")


def _require_outer_progress(
    launch_failure: dict[str, Any], campaign_attempt_id: str
) -> None:
    expected_progress = {
        "attempt": {
            "byte_count": EXPECTED_LAUNCH_ATTEMPT_BYTE_COUNT,
            "mode": 0o400,
            "presence": "REGULAR_FILE",
            "sha256": EXPECTED_LAUNCH_ATTEMPT_SHA256,
        },
        "evidence_inventory": {"presence": "ABSENT"},
        "execution_closure": {"presence": "ABSENT"},
        "launch_failure": {"presence": "ABSENT"},
        "ledger_closure": {"presence": "ABSENT"},
        "measurement_failure": {
            "byte_count": 6_890,
            "mode": 0o400,
            "presence": "REGULAR_FILE",
            "sha256": (
                "e829ae0dc47eb0885a4489d9d4a02effccc497542a078752d954437bfb9d10ee"
            ),
        },
        "os_receipt": {"presence": "ABSENT"},
        "output_root": {"mode": 0o700, "presence": "DIRECTORY"},
        "receipt": {"presence": "ABSENT"},
        "retained_replay": {"presence": "ABSENT"},
        "runtime_cas": {"presence": "ABSENT"},
        "terminal": {"presence": "ABSENT"},
        "verification": {"presence": "ABSENT"},
        "verification_failure": {"presence": "ABSENT"},
    }
    if launch_failure.get("progress_observations") != expected_progress:
        _fail("retained outer launch progress observations changed")
    cgroup_rows = launch_failure.get("measurement_cgroup_cleanup_observations")
    phases = ("BEFORE_POPEN", "CLEANUP", "AFTER_CHILD")
    if type(cgroup_rows) is not list or tuple(
        row.get("phase") if type(row) is dict else None for row in cgroup_rows
    ) != phases:
        _fail("retained outer cgroup observation phases changed")
    for row, phase in zip(cgroup_rows, phases):
        expected = {
            "applicable": True,
            "campaign_attempt_id": campaign_attempt_id,
            "error_message": None,
            "error_type": None,
            "kill_attempted": False,
            "kill_succeeded": False,
            "ownership_acquired": True,
            "phase": phase,
            "remove_attempted": False,
            "remove_succeeded": False,
            "residual_tree_or_process_possible": False,
            "root_device": None,
            "root_inode": None,
            "root_mode": None,
            "root_name": f"v180r12r3r2-{campaign_attempt_id}",
            "root_nlink": None,
            "root_populated": None,
            "root_process_count": None,
            "root_state": "ABSENT",
            "supervisor_state": "ABSENT",
            "wait_empty_attempted": False,
            "wait_empty_succeeded": False,
            "worker_state": "ABSENT",
        }
        if row != expected:
            _fail("retained outer cgroup cleanup observation changed")


def _require_failure_documents(
    external_root_raw: bytes,
    materialization_raw: bytes,
    manifest_raw: bytes,
    launch_attempt_raw: bytes,
    launch_failure_raw: bytes,
    scientific_attempt_raw: bytes,
    measurement_failure_raw: bytes,
    event_raws: tuple[bytes, bytes],
) -> dict[str, Any]:
    external_root = _canonical_object(external_root_raw, "external root")
    materialization = _canonical_object(
        materialization_raw, "materialization terminal"
    )
    manifest = _canonical_object(manifest_raw, "launch manifest")
    launch_attempt = _canonical_object(launch_attempt_raw, "launch attempt")
    launch_failure = _canonical_object(launch_failure_raw, "launch failure")
    scientific_attempt = _canonical_object(
        scientific_attempt_raw, "scientific attempt"
    )
    measurement_failure = _canonical_object(
        measurement_failure_raw, "measurement failure"
    )
    events = (
        _canonical_object(event_raws[0], "event 000000"),
        _canonical_object(event_raws[1], "event 000001"),
    )

    materialization_id = _self_id(
        materialization,
        "materialization_terminal_id",
        EXPECTED_MATERIALIZATION_TERMINAL_ID,
    )
    launch_attempt_id = _self_id(
        launch_attempt, "launch_attempt_id", EXPECTED_LAUNCH_ATTEMPT_ID
    )
    launch_failure_id = _self_id(
        launch_failure, "launch_failure_id", EXPECTED_LAUNCH_FAILURE_ID
    )
    campaign_attempt_record_id = _self_id(
        scientific_attempt,
        "campaign_attempt_record_id",
        EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
        domain=_ATTEMPT_RECORD_DOMAIN,
    )
    failure_state_id = _self_id(
        measurement_failure,
        "failure_state_id",
        EXPECTED_FAILURE_STATE_ID,
        domain=_FAILURE_STATE_DOMAIN,
    )
    event_ids = tuple(
        _self_id(event, "event_id", expected, domain=_EVENT_DOMAIN)
        for event, expected in zip(events, EXPECTED_EVENT_IDS)
    )

    frozen_context = manifest.get("frozen_authorization_context")
    if type(frozen_context) is not dict:
        _fail("retained manifest frozen authorization context changed")
    campaign_attempt_payload = {
        "schema": "acfqp.campaign_measurement_attempt.v180r12r3r2",
        "protocol_id": frozen_context.get("protocol_id"),
        "authorization_id": frozen_context.get("authorization_id"),
        "authorization_evidence_id": frozen_context.get(
            "authorization_evidence_id"
        ),
        "campaign_measurement_execution_slot_id": frozen_context.get(
            "campaign_measurement_execution_slot_id"
        ),
        "logical_occurrence_id": frozen_context.get("logical_occurrence_id"),
        "execution_nonce": frozen_context.get("execution_nonce"),
    }
    campaign_attempt_id = _domain_id(
        _CAMPAIGN_ATTEMPT_DOMAIN, campaign_attempt_payload
    )
    if not (
        campaign_attempt_id
        == frozen_context.get("campaign_attempt_id")
        == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and external_root.get("frozen_authorization_context") == frozen_context
        and external_root.get("c_pre_commit_id") == manifest.get("c_pre_commit_id")
        and materialization.get("schema")
        == "acfqp.v180r12r3r2_prelaunch_materialization_terminal.v1"
        and materialization.get("success") is True
        and materialization.get("construction_only") is True
        and materialization.get("campaign_actual_measurement") is False
        and materialization.get("scientific_occurrence_executed") is False
        and materialization.get("launch_manifest")
        == {
            "byte_count": len(manifest_raw),
            "relative_path": (
                ".tmp/exact-freeze/v180r12r3r2_campaign_measurement_prelaunch/"
                "launch_manifest.json"
            ),
            "sha256": hashlib.sha256(manifest_raw).hexdigest(),
        }
        and materialization.get("external_root", {}).get("byte_count")
        == len(external_root_raw)
        and materialization.get("external_root", {}).get("sha256")
        == hashlib.sha256(external_root_raw).hexdigest()
        and materialization.get("external_root", {}).get("immutable_mode")
        == "0400"
        and manifest.get("targets", {}).get("measurement")
        == {
            "byte_count": EXPECTED_MEASUREMENT_RUNNER_BYTE_COUNT,
            "relative_path": _MEASUREMENT_RUNNER_RELATIVE_PATH,
            "sha256": EXPECTED_MEASUREMENT_RUNNER_SHA256,
        }
    ):
        _fail("retained materialization/manifest/context join changed")

    if not (
        launch_attempt.get("schema")
        == "acfqp.v180r12r3r2_prelaunch_launch_attempt.v1"
        and launch_failure.get("schema")
        == "acfqp.v180r12r3r2_prelaunch_launch_failure.v1"
        and launch_attempt.get("target")
        == launch_failure.get("target")
        == "measurement"
        and launch_failure.get("launch_attempt_id") == launch_attempt_id
        and launch_attempt.get("launch_rule_id")
        == launch_failure.get("launch_rule_id")
        == EXPECTED_LAUNCH_RULE_ID
        and launch_attempt.get("materialization_terminal_id") == materialization_id
        and launch_attempt.get("materialization_terminal_byte_count")
        == len(materialization_raw)
        and launch_attempt.get("materialization_terminal_sha256")
        == hashlib.sha256(materialization_raw).hexdigest()
        and launch_attempt.get("launch_manifest_sha256")
        == hashlib.sha256(manifest_raw).hexdigest()
        and launch_attempt.get("scientific_occurrence_started") is False
        and launch_attempt.get("campaign_actual_measurement") is False
        and launch_attempt.get("authorized_child_measurement_execution_attempted")
        is True
        and launch_attempt.get("authorized_child_measurement_execution_completed")
        is False
        and launch_attempt.get("same_target_identity_rerun_forbidden") is True
        and launch_failure.get("return_code") == 1
        and launch_failure.get("timed_out") is False
        and launch_failure.get("failure_type")
        == "V180r12r3r2PrelaunchLaunchError"
        and launch_failure.get("failure_message")
        == "source-bound child did not reach its exact durable success state"
        and launch_failure.get("attempt_lock_preserved") is True
        and launch_failure.get("same_target_identity_rerun_forbidden") is True
        and launch_failure.get("authorized_child_measurement_execution_attempted")
        is True
        and launch_failure.get("authorized_child_measurement_execution_completed")
        is False
        and launch_failure.get("producer_free_verification_attempted") is False
        and launch_failure.get("producer_free_verification_completed") is False
        and launch_failure.get("campaign_actual_measurement") is False
        and launch_failure.get("success") is False
        and launch_failure.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and launch_failure.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and launch_failure.get("SCALAR_CALIBRATION_GATE") == "NOT_RUN"
        and launch_failure.get("BREAK_EVEN_GATE") == "NOT_RUN"
        and launch_failure.get("official_execution_allowed") is False
    ):
        _fail("retained launch attempt/failure boundary changed")
    _require_streams(launch_failure)
    _require_outer_progress(launch_failure, campaign_attempt_id)

    if not (
        scientific_attempt.get("schema")
        == "acfqp.campaign_attempt_record.v180r12r3r2"
        and scientific_attempt.get("attempt_id") == campaign_attempt_id
        and scientific_attempt.get("protocol_id")
        == frozen_context.get("protocol_id")
        and scientific_attempt.get("authorization_id")
        == frozen_context.get("authorization_id")
        and scientific_attempt.get("authorization_evidence_id")
        == frozen_context.get("authorization_evidence_id")
        and scientific_attempt.get("prelaunch_materialization_terminal_id")
        == materialization_id
        and scientific_attempt.get("prelaunch_launch_manifest_sha256")
        == hashlib.sha256(manifest_raw).hexdigest()
        and scientific_attempt.get("prelaunch_launch_rule_id")
        == EXPECTED_LAUNCH_RULE_ID
        and scientific_attempt.get("measurement_launch_attempt_id")
        == launch_attempt_id
        and scientific_attempt.get("one_shot_attempt_opened") is True
        and scientific_attempt.get("scope")
        == "TEN_TERMINAL_AGGREGATION_MEASURED_REPLAY_SUCCESSOR"
    ):
        _fail("retained scientific ATTEMPT authority join changed")

    common = (
        frozen_context.get("protocol_id"),
        frozen_context.get("authorization_id"),
        campaign_attempt_id,
    )
    event_zero, event_one = events
    if not (
        tuple(
            (
                event.get("protocol_id"),
                event.get("authorization_id"),
                event.get("attempt_id"),
            )
            for event in events
        )
        == (common, common)
        and event_zero.get("schema")
        == event_one.get("schema")
        == "acfqp.campaign_measurement_ledger_event.v180r12r3r2"
        and event_zero.get("sequence") == 0
        and event_one.get("sequence") == 1
        and event_zero.get("previous_event_id") is None
        and event_one.get("previous_event_id") == event_ids[0]
        and type(event_zero.get("monotonic_ns")) is int
        and type(event_one.get("monotonic_ns")) is int
        and 0 < event_zero["monotonic_ns"] < event_one["monotonic_ns"]
        and event_zero.get("phase") == "ATTEMPT"
        and event_zero.get("actor_role") == "OBSERVER"
        and event_zero.get("event_kind") == "ATTEMPT_OPEN"
        and event_zero.get("operation_id")
        == scientific_attempt.get("operation_id")
        and event_zero.get("payload")
        == {
            "auxiliary_values": [],
            "evidence_id": campaign_attempt_record_id,
            "measured_value": None,
            "outcome_code": "OPEN",
        }
        and event_one.get("phase") == "STAGE"
        and event_one.get("actor_role") == "OBSERVER"
        and event_one.get("event_kind") == "PROCESS_BIRTH_INTENT"
        and event_one.get("payload")
        == {
            "auxiliary_values": [],
            "evidence_id": None,
            "measured_value": None,
            "outcome_code": "INTENT",
        }
    ):
        _fail("retained two-event causal prefix changed")

    partial_observations = measurement_failure.get(
        "partial_artifact_observations"
    )
    cgroup_failure = measurement_failure.get("cgroup_failure_observation")
    if not (
        hashlib.sha256(_canonical_bytes(partial_observations)).hexdigest()
        == EXPECTED_PARTIAL_OBSERVATIONS_SHA256
        and hashlib.sha256(_canonical_bytes(cgroup_failure)).hexdigest()
        == EXPECTED_CGROUP_FAILURE_OBSERVATION_SHA256
        and measurement_failure.get("schema")
        == "acfqp.campaign_failure_state.v180r12r3r2"
        and measurement_failure.get("protocol_id") == common[0]
        and measurement_failure.get("authorization_id") == common[1]
        and measurement_failure.get("attempt_id") == common[2]
        and measurement_failure.get("failure_code")
        == "SUPERVISOR_BIRTH_FAILURE"
        and measurement_failure.get("phase") == "STAGE"
        and measurement_failure.get("operation_id")
        == event_one.get("operation_id")
        and measurement_failure.get("last_event_id") == event_ids[1]
        and measurement_failure.get("completed_event_count")
        == EXPECTED_RETAINED_EVENT_COUNT
        and EXPECTED_RETAINED_EVENT_COUNT < EXPECTED_SUCCESS_EVENT_COUNT
        and measurement_failure.get("message")
        == "PermissionError: (13, 'Permission denied')"
        and measurement_failure.get("message_sha256")
        == hashlib.sha256(
            measurement_failure["message"].encode("utf-8")
        ).hexdigest()
        and measurement_failure.get("process_may_remain") is False
        and measurement_failure.get("output_may_exist") is True
        and measurement_failure.get("same_identity_rerun_forbidden") is True
        and measurement_failure.get("successful_ledger_claimed") is False
        and measurement_failure.get("counter_records_issued") is False
        and measurement_failure.get("partial_artifact_observation_boundary")
        == "IMMEDIATELY_BEFORE_FAILURE_WRITE"
        and type(partial_observations) is list
        and len(partial_observations) == 17
        and type(cgroup_failure) is dict
        and cgroup_failure.get("kill_outcome") == "SUCCESS"
        and cgroup_failure.get("reap_outcome") == "NO_CHILD_HANDLE"
        and cgroup_failure.get("close_outcome") == "SUCCESS"
        and cgroup_failure.get("root_populated") == 0
        and cgroup_failure.get("root_process_count") == 0
        and cgroup_failure.get("supervisor_leaf_populated") == 0
        and cgroup_failure.get("supervisor_leaf_process_count") == 0
        and cgroup_failure.get("worker_leaf_populated") == 0
        and cgroup_failure.get("worker_leaf_process_count") == 0
        and cgroup_failure.get("pids_peak") == 0
    ):
        _fail("retained typed scientific failure boundary changed")

    observations_by_path = {
        row.get("relative_path"): row
        for row in partial_observations
        if type(row) is dict
    }
    if not (
        len(observations_by_path) == len(partial_observations)
        and observations_by_path[
            _observation_path(_SCIENTIFIC_ATTEMPT_RELATIVE_PATH)
        ].get("state")
        == "PRESENT"
        and observations_by_path[
            _observation_path(_SCIENTIFIC_ATTEMPT_RELATIVE_PATH)
        ].get("sha256")
        == hashlib.sha256(scientific_attempt_raw).hexdigest()
        and observations_by_path[_observation_path(_OUTPUT)].get(
            "directory_entries"
        )
        == ["EVENTS"]
        and observations_by_path[_observation_path(_EVENTS)].get(
            "directory_entries"
        )
        == ["000000.json", "000001.json"]
        and observations_by_path[_observation_path(_EVENT_RELATIVE_PATHS[0])].get(
            "sha256"
        )
        == hashlib.sha256(event_raws[0]).hexdigest()
        and observations_by_path[_observation_path(_EVENT_RELATIVE_PATHS[1])].get(
            "sha256"
        )
        == hashlib.sha256(event_raws[1]).hexdigest()
        and observations_by_path[
            _observation_path(_MEASUREMENT_FAILURE_RELATIVE_PATH)
        ].get("state")
        == "ABSENT"
    ):
        _fail("retained typed failure artifact joins changed")

    return {
        "launch_attempt_id": launch_attempt_id,
        "launch_failure_id": launch_failure_id,
        "campaign_attempt_id": campaign_attempt_id,
        "campaign_attempt_record_id": campaign_attempt_record_id,
        "failure_state_id": failure_state_id,
        "event_ids": event_ids,
    }


def _require_attempt_cgroup_absent() -> None:
    cgroup_parent = Path(
        "/sys/fs/cgroup/user.slice/user-1000.slice/"
        "user@1000.service/app.slice"
    )
    cgroup_parent_fd = _open_absolute_directory_no_symlink(cgroup_parent)
    try:
        try:
            os.stat(
                f"v180r12r3r2-{EXPECTED_CAMPAIGN_ATTEMPT_ID}",
                dir_fd=cgroup_parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            _fail("retained V180r12r3r2 attempt cgroup exists")
    finally:
        os.close(cgroup_parent_fd)


def _read_complete_failure_storage_boundary(base: Path) -> dict[str, bytes]:
    base_fd = _open_absolute_directory_no_symlink(base)
    try:
        _require_inventory(
            base_fd,
            _PRELAUNCH,
            _PRELAUNCH_EXACT_ENTRIES,
            expected_mode=0o700,
            expected_nlink=2,
        )
        _require_inventory(
            base_fd,
            _OUTPUT,
            _OUTPUT_EXACT_ENTRIES,
            expected_mode=0o700,
            expected_nlink=3,
        )
        _require_inventory(
            base_fd,
            _EVENTS,
            _EVENTS_EXACT_ENTRIES,
            expected_mode=0o700,
            expected_nlink=2,
        )
        retained = {
            relative: _stable_read(
                base_fd,
                relative,
                size,
                digest,
                expected_mode=0o400,
            )
            for relative, size, digest in _RETAINED_FILE_FACTS
        }
        if sum(len(raw) for raw in retained.values()) != (
            EXPECTED_RETAINED_FAILURE_TOTAL_BYTE_COUNT
        ):
            _fail("retained V180r12r3r2 total byte count changed")
        for relative in _REQUIRED_ABSENT_PATHS:
            _require_absent(base_fd, relative)
    finally:
        os.close(base_fd)
    _require_attempt_cgroup_absent()
    return retained


def load_frozen_campaign_measurement_failure_v180r12r3r2(
    base: Path = _BASE,
) -> FrozenCampaignMeasurementFailureV180r12r3r2:
    retained = _read_complete_failure_storage_boundary(base)

    repository_fd = _open_absolute_directory_no_symlink(_REPOSITORY_ROOT)
    try:
        source_rows = {
            relative: _stable_read(
                repository_fd,
                relative,
                size,
                digest,
                expected_mode=0o644,
            )
            for relative, size, digest in _SOURCE_FILE_FACTS
        }
    finally:
        os.close(repository_fd)
    _require_runner_causal_source(
        source_rows[_MEASUREMENT_RUNNER_RELATIVE_PATH]
    )

    event_bytes = (
        retained[_EVENT_RELATIVE_PATHS[0]],
        retained[_EVENT_RELATIVE_PATHS[1]],
    )
    identities = _require_failure_documents(
        retained[_EXTERNAL_ROOT_RELATIVE_PATH],
        retained[_MATERIALIZATION_RELATIVE_PATH],
        retained[_MANIFEST_RELATIVE_PATH],
        retained[_ATTEMPT_RELATIVE_PATH],
        retained[_LAUNCH_FAILURE_RELATIVE_PATH],
        retained[_SCIENTIFIC_ATTEMPT_RELATIVE_PATH],
        retained[_MEASUREMENT_FAILURE_RELATIVE_PATH],
        event_bytes,
    )
    value = FrozenCampaignMeasurementFailureV180r12r3r2(
        _issuer=_ISSUER,
        external_root_bytes=retained[_EXTERNAL_ROOT_RELATIVE_PATH],
        materialization_terminal_bytes=retained[_MATERIALIZATION_RELATIVE_PATH],
        launch_manifest_bytes=retained[_MANIFEST_RELATIVE_PATH],
        launch_attempt_bytes=retained[_ATTEMPT_RELATIVE_PATH],
        launch_failure_bytes=retained[_LAUNCH_FAILURE_RELATIVE_PATH],
        scientific_attempt_bytes=retained[_SCIENTIFIC_ATTEMPT_RELATIVE_PATH],
        measurement_failure_bytes=retained[_MEASUREMENT_FAILURE_RELATIVE_PATH],
        event_bytes=event_bytes,
        launch_attempt_id=identities["launch_attempt_id"],
        launch_failure_id=identities["launch_failure_id"],
        campaign_attempt_id=identities["campaign_attempt_id"],
        campaign_attempt_record_id=identities["campaign_attempt_record_id"],
        failure_state_id=identities["failure_state_id"],
        event_ids=identities["event_ids"],
    )
    _read_complete_failure_storage_boundary(base)
    return value


__all__ = (
    "EXPECTED_RETAINED_FAILURE_TOTAL_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_ATTEMPT_ID",
    "EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID",
    "EXPECTED_CHILD_STDERR_BYTE_COUNT",
    "EXPECTED_CHILD_STDERR_SHA256",
    "EXPECTED_EVENT_IDS",
    "EXPECTED_FAILURE_STATE_ID",
    "EXPECTED_LAUNCH_ATTEMPT_ID",
    "EXPECTED_LAUNCH_FAILURE_ID",
    "EXPECTED_RETAINED_EVENT_COUNT",
    "EXPECTED_SUCCESS_EVENT_COUNT",
    "FAILURE_CLAIM_BOUNDARY",
    "FAILURE_EVIDENCE_BASE_COMPONENT_COUNT_CAP",
    "FAILURE_EVIDENCE_BASE_TOTAL_BYTE_CAP",
    "FrozenCampaignMeasurementFailureV180r12r3r2",
    "FrozenCampaignMeasurementFailureV180r12r3r2Error",
    "load_frozen_campaign_measurement_failure_v180r12r3r2",
)
