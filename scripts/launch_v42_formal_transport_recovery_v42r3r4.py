from __future__ import annotations

"""Sealed, recovery-only controller for the retained V42r3r3 launch.

This controller has no probe, prepare, admission, service, or scientific-runner
entry point.  It authenticates the frozen local launch occurrence, consumes a
fresh one-shot read-only inspection ordinal, durably records the bounded child
transport observation, and only then interprets the remote inspection.  The
retained launch effect is permanently non-replayable regardless of the current
remote state.

The SSH login shell and writable path ancestors remain explicit unattested
external TCB.  The authenticated remote body itself is read-only.
"""

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import errno
import fcntl
import hashlib
import importlib
import importlib.abc
import importlib.machinery
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shlex
import signal
import stat
import subprocess
import sys
import types
import time
from typing import Any, NoReturn


LAUNCHER_RELATIVE = "scripts/launch_v42_formal_transport_recovery_v42r3r4.py"
BOOTSTRAP_RELATIVE = "scripts/bootstrap_v42_formal_transport_recovery_v42r3r4.py"
RECEIVER_RELATIVE = (
    "scripts/v42_standard_2048_formal_transport_recovery_receiver_v42r3r4.py"
)
AUTHORITY_RELATIVE = (
    "src/acfqp/"
    "construction_k7_standard_2048_formal_transport_recovery_v42r3r4.py"
)
AUTHORITY_MODULE = (
    "acfqp.construction_k7_standard_2048_formal_transport_recovery_v42r3r4"
)
BOOTSTRAP_ROOT_ARGUMENT = "--v42r3r4-recovery-bootstrap-repository-root"
SEALED_STAGE_FD = 3
SEALED_STAGE_PATH = "/proc/self/fd/3"
SEALED_BOOTSTRAP_FD = 4
_BOOTSTRAP_REPOSITORY_ROOT: str | None = None
if __name__ == "__main__":
    if (
        len(sys.argv) < 3
        or sys.argv[0] != SEALED_STAGE_PATH
        or sys.argv[1] != BOOTSTRAP_ROOT_ARGUMENT
        or not os.path.isabs(sys.argv[2])
        or os.path.realpath(sys.argv[2]) != sys.argv[2]
        or not os.path.isdir(sys.argv[2])
    ):
        raise RuntimeError(
            "V42r3r4 recovery launcher did not enter through pinned bootstrap"
        )
    _BOOTSTRAP_REPOSITORY_ROOT = sys.argv[2]
    del sys.argv[1:3]
    ROOT = Path(_BOOTSTRAP_REPOSITORY_ROOT)
else:
    ROOT = Path(__file__).resolve().parents[1]

EXACT_ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
}
LOCAL_DISPATCH_ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
}
GIT = "/usr/bin/git"
GIT_SHA256 = (
    "587ef21868c948b883993e23209b86a72a6ddc06aab1545c697ffc31075acd4a"
)
GIT_BYTE_COUNT = 3_710_360
PYTHON_REALPATH = "/usr/bin/python3.10"
PYTHON_VERSION = (3, 10, 12)

RETAINED_COMMIT = "6f9678f7f71a57dfeef5459c27c5b48331001c0f"
RETAINED_TREE = "6494ba9044a00168f1e67b149b92682766c7ecc3"
RETAINED_CONTROLLER_ID = (
    "750401e55e51ae8f5e94c77e2e56bf8eb12e3e5d61fe336b3c82067d1a42a7b1"
)
RETAINED_PLAN_ID = (
    "58b6f0a4dd4dc867259176d77ef55e287fe882c7534bb25fdee8dec939dcd411"
)
RETAINED_ATTEMPT_ID = (
    "edc24ee9895e181676dcde59ace1659466a00ae0e7eab5dacd4c862c95410ec7"
)
RETAINED_REMOTE_ROOT = (
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-remote-ordinal2-formal-transport-v42r3r3"
)
RETAINED_UNIT_NAME = (
    "acfqp-v42r3r3-remote-ordinal2-" + RETAINED_ATTEMPT_ID + ".service"
)
RETAINED_LOCAL_ROOT = Path(
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-local-formal-transport-ordinal2-v42r3r3"
)
RECOVERY_LOCAL_ROOT = Path(
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-local-formal-transport-ordinal2-recovery-v42r3r4"
)
KNOWN_HOSTS_NAME = "PINNED_KNOWN_HOSTS"

REMOTE_MODE = "--inspect-retained-launch-v42r3r4"
LOCAL_SSH_EXECUTABLE = "/usr/bin/ssh"
LOCAL_IDENTITY_FILE = "/home/erzhu419/.ssh/id_ed25519"
REMOTE_ENDPOINT_HOST = "tf290q6n.zjz-service.cn"
REMOTE_ENDPOINT_PORT = 23035
REMOTE_USER = "erzhu419"
EXPECTED_REMOTE_HOSTNAME = "erzhu419-Super-Server"
EXPECTED_REMOTE_UID = 1000
EXPECTED_REMOTE_GID = 1000

MAX_SOURCE_BYTES = 8 * 1024**2
MAX_ARTIFACT_BYTES = 64 * 1024**2
MAX_STDOUT_BYTES = 64 * 1024**2
MAX_STDERR_BYTES = 1024**2
MAX_REMOTE_COMMAND_BYTES = 96 * 1024
READ_ONLY_TIMEOUT_SECONDS = 120.0
SSH_SHA256 = "a16f755ab475a277cf2569d0fb9a3f74c48d38dfc286dc95282f38522c9f09fe"
SSH_BYTE_COUNT = 846_888
IDENTITY_SHA256 = (
    "2af5abfc65598239a452395bc57fc5814dcb9d85c99b1834b569c58a66f67643"
)
IDENTITY_BYTE_COUNT = 411
KNOWN_HOSTS_SHA256 = (
    "a764658af19a4f082f994c0f35062d47e8abc23510f7a77dfa7f12e2d8c6fec4"
)
KNOWN_HOSTS_BYTE_COUNT = 113
_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")

CONTROLLER_TCB_PATHS = (
    "scripts/__init__.py",
    BOOTSTRAP_RELATIVE,
    LAUNCHER_RELATIVE,
    RECEIVER_RELATIVE,
    AUTHORITY_RELATIVE,
    "src/acfqp/__init__.py",
    "src/acfqp/phase3e_ids.py",
    (
        "src/acfqp/"
        "construction_k7_standard_2048_formal_transport_successor_v42r3.py"
    ),
    (
        "src/acfqp/"
        "construction_k7_standard_2048_remote_execution_authority_v42r1.py"
    ),
    "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
    (
        "src/acfqp/"
        "construction_k7_standard_2048_materialization_transport_v42r1.py"
    ),
    (
        "src/acfqp/"
        "construction_k7_standard_2048_fresh_terminal_preregistration_v42.py"
    ),
    "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
    "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
    "src/acfqp/core.py",
    "src/acfqp/enumeration.py",
    "src/acfqp/artifacts.py",
    "src/acfqp/build_coverage.py",
    "src/acfqp/construction_k7_domain_registry_extension_v42.py",
)
CONTROLLER_TCB_PATHS = tuple(sorted(CONTROLLER_TCB_PATHS))

RETAINED_FILES = {
    "root_identity": (
        RETAINED_LOCAL_ROOT.parent
        / ("." + RETAINED_LOCAL_ROOT.name + ".ROOT_IDENTITY.json")
    ),
    "controller_source_manifest": RETAINED_LOCAL_ROOT
    / "CONTROLLER_SOURCE_MANIFEST.json",
    "formal_transport_plan": RETAINED_LOCAL_ROOT / "FORMAL_TRANSPORT_PLAN.json",
    "prepare_receipt": RETAINED_LOCAL_ROOT / "FORMAL_PREPARE_RECEIPT.json",
    "local_launch_attempt": RETAINED_LOCAL_ROOT / "LOCAL_LAUNCH_ATTEMPT.json",
    "formal_launch_transport_attempt": RETAINED_LOCAL_ROOT
    / "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json",
    "inner_network_start": RETAINED_LOCAL_ROOT
    / "FORMAL_LAUNCH_NETWORK_START.json",
    "parent_network_start": RETAINED_LOCAL_ROOT.parent
    / (
        "." + RETAINED_LOCAL_ROOT.name + ".NETWORK_START.LAUNCH."
        + RETAINED_ATTEMPT_ID + ".json"
    ),
    "operation_outcome": RETAINED_LOCAL_ROOT
    / "FORMAL_LAUNCH_OPERATION_OUTCOME.json",
}

RECOVERY_CONTROLLER_NAME = "RECOVERY_CONTROLLER_SOURCE_MANIFEST.json"
RETAINED_OCCURRENCE_NAME = "RETAINED_LAUNCH_OCCURRENCE.json"
RECOVERY_PLAN_NAME = "RETAINED_LAUNCH_RECOVERY_PLAN.json"
ATTEMPT_PREFIX = "RETAINED_LAUNCH_INSPECTION_ATTEMPT."
OBSERVATION_PREFIX = "RETAINED_LAUNCH_TRANSPORT_OBSERVATION."
REMOTE_INSPECTION_PREFIX = "RETAINED_LAUNCH_REMOTE_INSPECTION."
REMOTE_JOIN_PREFIX = "RETAINED_LAUNCH_REMOTE_INSPECTION_JOIN."
CLASSIFICATION_PREFIX = "RETAINED_LAUNCH_RECOVERY_CLASSIFICATION."
DISPATCH_FAILURE_PREFIX = "RETAINED_LAUNCH_DISPATCH_FAILURE."
AUTHENTICATION_FAILURE_PREFIX = "RETAINED_LAUNCH_AUTHENTICATION_FAILURE."


class V42FormalTransportRecoveryLauncherError(RuntimeError):
    """The V42r3r4 recovery controller rejected its evidence boundary."""


def _fail(message: str) -> NoReturn:
    raise V42FormalTransportRecoveryLauncherError(message)


_AUTHENTICATED_STAGE_SELF_RAW: bytes | None = None
_AUTHENTICATED_BOOTSTRAP_RAW: bytes | None = None
_EARLY_SEALED_MATERIALS_VERIFIED = False


def _live_descriptors() -> list[int]:
    result: list[int] = []
    for name in os.listdir("/proc/self/fd"):
        if not name.isdigit():
            _fail("recovery descriptor inventory changed")
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError as error:
            if error.errno != errno.EBADF:
                raise
            continue
        result.append(descriptor)
    return sorted(result)


def _read_sealed_source(descriptor: int, label: str) -> bytes:
    before = os.fstat(descriptor)
    seals = (
        fcntl.F_SEAL_SEAL
        | fcntl.F_SEAL_SHRINK
        | fcntl.F_SEAL_GROW
        | fcntl.F_SEAL_WRITE
    )
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_uid != os.geteuid()
        or before.st_gid != os.getegid()
        or before.st_nlink != 0
        or not 0 < before.st_size <= MAX_SOURCE_BYTES
        or fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != seals
    ):
        _fail("sealed " + label + " storage changed")
    raw = b""
    while len(raw) < before.st_size:
        chunk = os.pread(
            descriptor, min(1024 * 1024, before.st_size - len(raw)), len(raw)
        )
        if not chunk:
            _fail("sealed " + label + " ended early")
        raw += chunk
    after = os.fstat(descriptor)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if (
        any(getattr(before, field) != getattr(after, field) for field in fields)
        or fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != seals
    ):
        _fail("sealed " + label + " changed while read")
    return raw


def _require_early_isolated_runtime() -> None:
    global _AUTHENTICATED_BOOTSTRAP_RAW, _AUTHENTICATED_STAGE_SELF_RAW
    global _EARLY_SEALED_MATERIALS_VERIFIED
    user_arguments = list(sys.argv[1:])
    if (
        __name__ != "__main__"
        or _BOOTSTRAP_REPOSITORY_ROOT is None
        or __file__ != SEALED_STAGE_PATH
        or sys.argv[0] != SEALED_STAGE_PATH
        or sys.executable != "/usr/bin/python3"
        or os.path.realpath(sys.executable) != PYTHON_REALPATH
        or tuple(sys.version_info[:3]) != PYTHON_VERSION
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
        or sys.gettrace() is not None
        or sys.getprofile() is not None
        or sys.orig_argv != [
            "/usr/bin/python3", "-I", "-S", "-B", SEALED_STAGE_PATH,
            BOOTSTRAP_ROOT_ARGUMENT, _BOOTSTRAP_REPOSITORY_ROOT,
            *user_arguments,
        ]
        or sys.path != [
            "/usr/lib/python310.zip", "/usr/lib/python3.10",
            "/usr/lib/python3.10/lib-dynload",
        ]
        or dict(os.environ) != EXACT_ENVIRONMENT
        or Path.cwd() != ROOT
        or _live_descriptors() != [0, 1, 2, SEALED_STAGE_FD, SEALED_BOOTSTRAP_FD]
    ):
        raise RuntimeError("V42r3r4 recovery isolated Python entry changed")
    _AUTHENTICATED_STAGE_SELF_RAW = _read_sealed_source(
        SEALED_STAGE_FD, "recovery stage-1"
    )
    _AUTHENTICATED_BOOTSTRAP_RAW = _read_sealed_source(
        SEALED_BOOTSTRAP_FD, "recovery stage-0"
    )
    os.close(SEALED_BOOTSTRAP_FD)
    os.close(SEALED_STAGE_FD)
    if _live_descriptors() != [0, 1, 2]:
        _fail("recovery retained bootstrap descriptors")
    _EARLY_SEALED_MATERIALS_VERIFIED = True


if __name__ == "__main__":
    _require_early_isolated_runtime()


def _require_sealed_stage_materials() -> None:
    if (
        _EARLY_SEALED_MATERIALS_VERIFIED is not True
        or type(_AUTHENTICATED_STAGE_SELF_RAW) is not bytes
        or not _AUTHENTICATED_STAGE_SELF_RAW
        or type(_AUTHENTICATED_BOOTSTRAP_RAW) is not bytes
        or not _AUTHENTICATED_BOOTSTRAP_RAW
    ):
        _fail("recovery launcher lacks verified sealed materials")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_ARTIFACT_BYTES:
        _fail(label + " bytes changed")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise V42FormalTransportRecoveryLauncherError(
            label + " is not strict JSON"
        ) from error
    if type(value) is not dict or _canonical_json_bytes(value) != raw:
        _fail(label + " is not canonical JSON")
    return value


def _stable_regular(
    path: Path, cap: int, *, mode: int = 0o400,
    uid: int | None = None, gid: int | None = None,
) -> bytes:
    named = path.lstat()
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
        | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        expected_uid = os.geteuid() if uid is None else uid
        expected_gid = os.getegid() if gid is None else gid
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_uid != expected_uid
            or before.st_gid != expected_gid
            or before.st_nlink != 1
            or not 0 < before.st_size <= cap
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("stable file contract changed: " + str(path))
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("stable file ended early: " + str(path))
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("stable file grew while read: " + str(path))
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = path.lstat()
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(final, field)
        for field in fields
    ):
        _fail("stable file changed while read: " + str(path))
    return b"".join(chunks)


def _git(arguments: Sequence[str], *, cap: int = 64 * 1024**2) -> bytes:
    path = Path(GIT)
    named = path.lstat()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o755
            or before.st_uid != 0
            or before.st_gid != 0
            or before.st_nlink != 1
            or before.st_size != GIT_BYTE_COUNT
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("Git executable identity changed")
        digest = hashlib.sha256()
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(
                descriptor, min(1024 * 1024, before.st_size - offset), offset
            )
            if not chunk:
                _fail("Git executable ended early")
            digest.update(chunk)
            offset += len(chunk)
        if digest.hexdigest() != GIT_SHA256:
            _fail("Git executable digest changed")
        result = subprocess.run(
            [GIT, "--no-replace-objects", "-C", str(ROOT), *arguments],
            executable="/proc/self/fd/" + str(descriptor),
            pass_fds=(descriptor,),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_TERMINAL_PROMPT": "0",
            },
            cwd="/",
            check=False,
            timeout=60.0,
        )
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = path.lstat()
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if (
        any(
            getattr(before, field) != getattr(after, field)
            or getattr(after, field) != getattr(final, field)
            for field in fields
        )
        or result.returncode != 0
        or result.stderr
        or len(result.stdout) > cap
    ):
        _fail("Git query failed or exceeded its boundary")
    return result.stdout


def _git_anchor(expected_commit: str, expected_tree: str) -> None:
    if (
        _HEX40.fullmatch(expected_commit) is None
        or _HEX40.fullmatch(expected_tree) is None
    ):
        _fail("expected Git anchors changed")
    commit = _git(["rev-parse", "HEAD^{commit}"]).decode("ascii").strip()
    tree = _git(["rev-parse", "HEAD^{tree}"]).decode("ascii").strip()
    if commit != expected_commit or tree != expected_tree:
        _fail("current recovery Git anchors changed")


def _git_blob_oid(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - exact Git object identity
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _source_fact(relative: str, raw: bytes, blob_oid: str) -> dict[str, Any]:
    return {
        "relative_path": relative,
        "git_mode": "100644",
        "git_object_type": "blob",
        "git_blob_oid": blob_oid,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _verified_current_sources(
    expected_commit: str, expected_tree: str,
) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    _git_anchor(expected_commit, expected_tree)
    listing = _git(["ls-tree", "-rz", "--full-tree", expected_commit])
    entries: dict[str, tuple[str, str, str]] = {}
    for row in listing.split(b"\0"):
        if not row:
            continue
        try:
            header, name_raw = row.split(b"\t", 1)
            mode_raw, kind_raw, oid_raw = header.split(b" ", 2)
            name = name_raw.decode("utf-8", errors="strict")
            entries[name] = (
                mode_raw.decode("ascii"), kind_raw.decode("ascii"),
                oid_raw.decode("ascii"),
            )
        except (ValueError, UnicodeError) as error:
            raise V42FormalTransportRecoveryLauncherError(
                "Git source inventory framing changed"
            ) from error
    raws: dict[str, bytes] = {}
    facts: list[dict[str, Any]] = []
    for relative in CONTROLLER_TCB_PATHS:
        entry = entries.get(relative)
        if entry is None or entry[:2] != ("100644", "blob"):
            _fail("recovery TCB path absent from selected Git tree: " + relative)
        raw = _stable_regular(ROOT / relative, MAX_SOURCE_BYTES, mode=0o644)
        if _git_blob_oid(raw) != entry[2]:
            _fail("live recovery source differs from selected Git blob: " + relative)
        raws[relative] = raw
        facts.append(_source_fact(relative, raw, entry[2]))
    _require_sealed_stage_materials()
    if (
        raws.get(LAUNCHER_RELATIVE) != _AUTHENTICATED_STAGE_SELF_RAW
        or raws.get(BOOTSTRAP_RELATIVE) != _AUTHENTICATED_BOOTSTRAP_RAW
    ):
        _fail("sealed recovery stages differ from selected Git source bytes")
    observed_tree = _git(
        ["rev-parse", expected_commit + "^{tree}"]
    ).decode("ascii").strip()
    if observed_tree != expected_tree:
        _fail("selected recovery commit/tree join changed")
    return raws, facts


def _verify_retained_controller_git(controller_raw: bytes) -> dict[str, Any]:
    controller = _canonical_document(
        controller_raw, "retained controller source manifest"
    )
    if (
        controller.get("controller_source_manifest_id") != RETAINED_CONTROLLER_ID
        or controller.get("source_commit") != RETAINED_COMMIT
        or controller.get("source_tree") != RETAINED_TREE
        or type(controller.get("source_facts")) is not list
        or not controller["source_facts"]
    ):
        _fail("retained controller identity changed")
    tree = _git(["rev-parse", RETAINED_COMMIT + "^{tree}"]).decode("ascii").strip()
    if tree != RETAINED_TREE:
        _fail("retained controller commit/tree object changed")
    paths: set[str] = set()
    for fact in controller["source_facts"]:
        if (
            type(fact) is not dict
            or set(fact) != {
                "relative_path", "git_mode", "git_object_type", "git_blob_oid",
                "byte_count", "sha256",
            }
        ):
            _fail("retained controller source fact changed")
        relative = fact["relative_path"]
        if (
            type(relative) is not str
            or relative in paths
            or PurePosixPath(relative).is_absolute()
            or ".." in PurePosixPath(relative).parts
            or fact["git_mode"] != "100644"
            or fact["git_object_type"] != "blob"
            or _HEX40.fullmatch(fact["git_blob_oid"] or "") is None
            or type(fact["byte_count"]) is not int
            or not 0 < fact["byte_count"] <= MAX_SOURCE_BYTES
            or _HEX64.fullmatch(fact["sha256"] or "") is None
        ):
            _fail("retained controller source fact value changed")
        paths.add(relative)
        row = _git(["ls-tree", RETAINED_COMMIT, "--", relative]).decode(
            "utf-8", errors="strict"
        )
        expected_row = (
            "100644 blob " + fact["git_blob_oid"] + "\t" + relative + "\n"
        )
        if row != expected_row:
            _fail("retained controller Git path/blob join changed: " + relative)
        raw = _git(["cat-file", "blob", fact["git_blob_oid"]])
        if (
            len(raw) != fact["byte_count"]
            or hashlib.sha256(raw).hexdigest() != fact["sha256"]
            or _git_blob_oid(raw) != fact["git_blob_oid"]
        ):
            _fail("retained controller Git blob bytes changed: " + relative)
    return controller


def _retained_root_snapshot() -> tuple[tuple[str, str, int, int, str | None], ...]:
    root_state = RETAINED_LOCAL_ROOT.lstat()
    if (
        not stat.S_ISDIR(root_state.st_mode)
        or stat.S_IMODE(root_state.st_mode) != 0o700
        or root_state.st_uid != os.geteuid()
        or root_state.st_gid != os.getegid()
        or os.path.realpath(RETAINED_LOCAL_ROOT) != str(RETAINED_LOCAL_ROOT)
    ):
        _fail("retained r3r3 root identity changed")
    rows: list[tuple[str, str, int, int, str | None]] = [
        (".", "DIRECTORY", root_state.st_ino, root_state.st_size, None)
    ]
    for path in sorted(RETAINED_LOCAL_ROOT.rglob("*")):
        relative = path.relative_to(RETAINED_LOCAL_ROOT).as_posix()
        observed = path.lstat()
        if stat.S_ISDIR(observed.st_mode):
            if (
                stat.S_IMODE(observed.st_mode) != 0o700
                or observed.st_uid != os.geteuid()
                or observed.st_gid != os.getegid()
            ):
                _fail("retained r3r3 directory storage changed: " + relative)
            rows.append(
                (relative, "DIRECTORY", observed.st_ino, observed.st_size, None)
            )
        elif stat.S_ISREG(observed.st_mode):
            raw = _stable_regular(path, MAX_ARTIFACT_BYTES)
            rows.append(
                (
                    relative, "REGULAR_FILE", observed.st_ino, len(raw),
                    hashlib.sha256(raw).hexdigest(),
                )
            )
        else:
            _fail("retained r3r3 inventory contains a nonregular entry")
    for label, path in sorted(RETAINED_FILES.items()):
        if path.parent == RETAINED_LOCAL_ROOT:
            continue
        raw = _stable_regular(path, MAX_ARTIFACT_BYTES)
        state = path.lstat()
        rows.append(
            (
                "../" + label, "REGULAR_FILE", state.st_ino, len(raw),
                hashlib.sha256(raw).hexdigest(),
            )
        )
    return tuple(rows)


def _read_retained_artifacts() -> tuple[dict[str, bytes], tuple[Any, ...]]:
    before = _retained_root_snapshot()
    result: dict[str, bytes] = {}
    for label, path in RETAINED_FILES.items():
        result[label] = _stable_regular(path, MAX_ARTIFACT_BYTES)
    if hashlib.sha256(result["root_identity"]).hexdigest() != (
        "60d22cbff0b23bc9fc1082235c6e58ad2ad598afdf25360c68ec9a5b021aa99f"
    ):
        _fail("retained r3r3 root anchor bytes changed")
    if result["inner_network_start"] != result["parent_network_start"]:
        _fail("retained inner and parent launch markers differ")
    _verify_retained_controller_git(result["controller_source_manifest"])
    after = _retained_root_snapshot()
    if before != after:
        _fail("retained r3r3 root changed while read")
    return result, before


def _verify_retained_unchanged(snapshot: tuple[Any, ...]) -> None:
    if _retained_root_snapshot() != snapshot:
        _fail("retained r3r3 root changed across recovery operation")


def _anchor_name(root: Path) -> str:
    return "." + root.name + ".ROOT_IDENTITY.json"


@dataclass
class _RecoveryJournal:
    parent_fd: int
    root_fd: int
    root_state: os.stat_result
    anchor_raw: bytes
    closed: bool = False

    @classmethod
    def open_or_create(cls) -> "_RecoveryJournal":
        root = RECOVERY_LOCAL_ROOT
        if not root.is_absolute() or ".." in root.parts or not root.name:
            _fail("recovery local root path changed")
        parent_fd = os.open(
            root.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        created = False
        try:
            try:
                os.mkdir(root.name, 0o700, dir_fd=parent_fd)
                os.fsync(parent_fd)
                created = True
            except FileExistsError:
                pass
            root_fd = os.open(
                root.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
            state = os.fstat(root_fd)
            if (
                not stat.S_ISDIR(state.st_mode)
                or stat.S_IMODE(state.st_mode) != 0o700
                or state.st_uid != os.geteuid()
                or state.st_gid != os.getegid()
            ):
                _fail("recovery journal root storage changed")
            anchor = _canonical_json_bytes(
                {
                    "schema": (
                        "acfqp.v42_formal_transport_recovery_local_root_identity."
                        "v42r3r4"
                    ),
                    "schema_version": "42.3.4",
                    "path": str(root),
                    "st_dev": state.st_dev,
                    "st_ino": state.st_ino,
                    "mode": stat.S_IMODE(state.st_mode),
                    "uid": state.st_uid,
                    "gid": state.st_gid,
                }
            )
            journal = cls(parent_fd, root_fd, state, anchor)
            journal._publish_or_verify_parent_anchor(create=created)
            journal.verify_root()
            return journal
        except BaseException:
            try:
                os.close(locals().get("root_fd", -1))
            except OSError:
                pass
            os.close(parent_fd)
            raise

    def _publish_or_verify_parent_anchor(self, *, create: bool) -> None:
        name = _anchor_name(RECOVERY_LOCAL_ROOT)
        if not create:
            try:
                raw = _read_regular_at(
                    self.parent_fd, name, 4096, mode=0o400
                )
            except FileNotFoundError as error:
                raise V42FormalTransportRecoveryLauncherError(
                    "pre-existing recovery root lacks its exact identity anchor"
                ) from error
            if raw != self.anchor_raw:
                _fail("recovery root identity anchor changed")
            return
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                0o400,
                dir_fd=self.parent_fd,
            )
        except FileExistsError as error:
            raise V42FormalTransportRecoveryLauncherError(
                "fresh recovery root collided with a pre-existing anchor"
            ) from error
        try:
            _write_all(descriptor, self.anchor_raw)
            os.fsync(descriptor)
            state = os.fstat(descriptor)
            if stat.S_IMODE(state.st_mode) != 0o400 or state.st_nlink != 1:
                _fail("recovery root identity anchor storage changed")
        finally:
            os.close(descriptor)
        os.fsync(self.parent_fd)

    def verify_root(self) -> None:
        if self.closed:
            _fail("recovery journal pin is closed")
        state = os.fstat(self.root_fd)
        try:
            named = os.stat(
                RECOVERY_LOCAL_ROOT.name,
                dir_fd=self.parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError as error:
            raise V42FormalTransportRecoveryLauncherError(
                "recovery journal root name disappeared while pinned"
            ) from error
        fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink")
        if any(
            getattr(state, field) != getattr(self.root_state, field)
            or getattr(named, field) != getattr(self.root_state, field)
            for field in fields
        ):
            _fail("recovery journal root or named binding changed while pinned")
        if _read_regular_at(
            self.parent_fd, _anchor_name(RECOVERY_LOCAL_ROOT), 4096, mode=0o400
        ) != self.anchor_raw:
            _fail("recovery root anchor changed while pinned")

    def publish_once(self, name: str, raw: bytes) -> None:
        if (
            not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
            or type(raw) is not bytes
            or not 0 < len(raw) <= MAX_ARTIFACT_BYTES
        ):
            _fail("recovery journal publication contract changed")
        self.verify_root()
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                0o400,
                dir_fd=self.root_fd,
            )
        except FileExistsError as error:
            raise V42FormalTransportRecoveryLauncherError(
                "recovery one-shot artifact already exists: " + name
            ) from error
        try:
            _write_all(descriptor, raw)
            os.fsync(descriptor)
            state = os.fstat(descriptor)
            if (
                stat.S_IMODE(state.st_mode) != 0o400
                or state.st_uid != os.geteuid()
                or state.st_gid != os.getegid()
                or state.st_nlink != 1
                or state.st_size != len(raw)
            ):
                _fail("recovery published artifact storage changed")
        finally:
            os.close(descriptor)
        os.fsync(self.root_fd)
        if self.read(name, len(raw)) != raw:
            _fail("recovery artifact changed after publication")

    def publish_or_verify(self, name: str, raw: bytes) -> None:
        try:
            self.publish_once(name, raw)
        except V42FormalTransportRecoveryLauncherError as error:
            if "already exists" not in str(error) or self.read(name, len(raw)) != raw:
                raise

    def read(self, name: str, cap: int = MAX_ARTIFACT_BYTES) -> bytes:
        self.verify_root()
        return _read_regular_at(self.root_fd, name, cap, mode=0o400)

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            os.close(self.root_fd)
            os.close(self.parent_fd)

    def __enter__(self) -> "_RecoveryJournal":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _read_regular_at(directory_fd: int, name: str, cap: int, *, mode: int) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        _fail("relative artifact name changed")
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
        | os.O_CLOEXEC,
        dir_fd=directory_fd,
    )
    try:
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or stat.S_IMODE(state.st_mode) != mode
            or state.st_uid != os.geteuid()
            or state.st_gid != os.getegid()
            or state.st_nlink != 1
            or not 0 < state.st_size <= cap
        ):
            _fail("recovery journal artifact identity changed")
        chunks: list[bytes] = []
        remaining = state.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("recovery journal artifact ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("recovery journal artifact grew while read")
        after = os.fstat(descriptor)
        fields = (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
            "st_size", "st_mtime_ns", "st_ctime_ns",
        )
        if any(getattr(state, field) != getattr(after, field) for field in fields):
            _fail("recovery journal artifact changed while read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            _fail("recovery journal write made no progress")
        view = view[written:]


@dataclass
class _PinnedFile:
    descriptor: int
    path: Path
    state: os.stat_result
    sha256: str
    closed: bool = False

    @classmethod
    def open(
        cls, path: Path, *, mode: int, uid: int, gid: int,
        byte_count: int, sha256: str,
    ) -> "_PinnedFile":
        named = path.lstat()
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
            | os.O_CLOEXEC,
        )
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != mode
                or before.st_uid != uid
                or before.st_gid != gid
                or before.st_nlink != 1
                or before.st_size != byte_count
                or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
            ):
                _fail("pinned file storage changed: " + str(path))
            digest = hashlib.sha256()
            offset = 0
            while offset < byte_count:
                chunk = os.pread(
                    descriptor, min(1024 * 1024, byte_count - offset), offset
                )
                if not chunk:
                    _fail("pinned file ended early: " + str(path))
                digest.update(chunk)
                offset += len(chunk)
            if digest.hexdigest() != sha256:
                _fail("pinned file digest changed: " + str(path))
            pin = cls(descriptor, path, before, sha256)
            pin.verify()
            return pin
        except BaseException:
            os.close(descriptor)
            raise

    def verify(self) -> None:
        if self.closed:
            _fail("pinned file was closed")
        current = os.fstat(self.descriptor)
        named = self.path.lstat()
        fields = (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
            "st_size", "st_mtime_ns", "st_ctime_ns",
        )
        if any(
            getattr(current, field) != getattr(self.state, field)
            or getattr(named, field) != getattr(self.state, field)
            for field in fields
        ):
            _fail("pinned file changed: " + str(self.path))

    @property
    def proc_path(self) -> str:
        self.verify()
        return (
            "/proc/" + str(os.getpid()) + "/fd/" + str(self.descriptor)
        )

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            os.close(self.descriptor)


@dataclass(frozen=True)
class _ChildObservation:
    exec_succeeded: bool
    returncode: int | None
    timed_out: bool
    stdin_expected_byte_count: int
    stdin_sent_byte_count: int
    stdin_complete: bool
    stdout_raw: bytes
    stdout_total_byte_count: int
    stdout_sha256: str
    stdout_overflow: bool
    stdout_eof: bool
    stderr_prefix: bytes
    stderr_total_byte_count: int
    stderr_sha256: str
    stderr_overflow: bool
    stderr_eof: bool
    transport_observation_completed_without_local_error: bool = True


def _remote_command(
    receiver_raw: bytes, ingress_raw: bytes, *, recovery_plan_id: str,
) -> str:
    if _HEX64.fullmatch(recovery_plan_id) is None:
        _fail("recovery remote command plan ID changed")
    arguments = [
        "/usr/bin/python3", "-I", "-S", "-B", "-c",
        receiver_raw.decode("utf-8", errors="strict"),
        REMOTE_MODE,
        hashlib.sha256(receiver_raw).hexdigest(), str(len(receiver_raw)),
        hashlib.sha256(ingress_raw).hexdigest(), str(len(ingress_raw)),
        recovery_plan_id,
    ]
    command = "builtin exec -c " + " ".join(shlex.quote(item) for item in arguments)
    if len(command.encode("utf-8", errors="strict")) > MAX_REMOTE_COMMAND_BYTES:
        _fail("recovery remote command exceeded its fixed cap")
    return command


def _actual_remote_command_projection(
    receiver_raw: bytes, ingress_raw: bytes, *, recovery_plan_id: str,
) -> dict[str, Any]:
    if _HEX64.fullmatch(recovery_plan_id) is None:
        _fail("recovery command projection plan ID changed")
    return {
        "ordered_remote_python_argv_semantics": [
            {"literal": "/usr/bin/python3"},
            *({"literal": flag} for flag in ("-I", "-S", "-B", "-c")),
            {
                "receiver_source": {
                    "sha256": hashlib.sha256(receiver_raw).hexdigest(),
                    "byte_count": len(receiver_raw),
                }
            },
            {"literal": REMOTE_MODE},
            {"receiver_source_sha256": hashlib.sha256(receiver_raw).hexdigest()},
            {"receiver_source_byte_count_decimal": str(len(receiver_raw))},
            {"canonical_ingress_sha256": hashlib.sha256(ingress_raw).hexdigest()},
            {"canonical_ingress_byte_count_decimal": str(len(ingress_raw))},
            {"recovery_plan_id": recovery_plan_id},
        ],
        "transport_executable": LOCAL_SSH_EXECUTABLE,
        "remote_endpoint_host": REMOTE_ENDPOINT_HOST,
        "remote_endpoint_port": REMOTE_ENDPOINT_PORT,
        "remote_user": REMOTE_USER,
        "ssh_login_shell_exactness_attested": False,
    }


def _ssh_argv(
    *, known_hosts_proc_path: str, identity_proc_path: str,
    remote_command: str,
) -> tuple[str, ...]:
    if (
        not known_hosts_proc_path.startswith("/proc/")
        or "/fd/" not in known_hosts_proc_path
        or not identity_proc_path.startswith("/proc/")
        or "/fd/" not in identity_proc_path
        or not remote_command.startswith("builtin exec -c ")
    ):
        _fail("recovery SSH materialization inputs changed")
    return (
        LOCAL_SSH_EXECUTABLE,
        "-T", "-F", "/dev/null",
        "-oBatchMode=yes",
        "-oPreferredAuthentications=publickey",
        "-oPasswordAuthentication=no",
        "-oKbdInteractiveAuthentication=no",
        "-oGSSAPIAuthentication=no",
        "-oHostbasedAuthentication=no",
        "-oIdentitiesOnly=yes",
        "-oIdentityAgent=none",
        "-oCertificateFile=none",
        "-oStrictHostKeyChecking=yes",
        "-oCheckHostIP=no",
        "-oCanonicalizeHostname=no",
        "-oHostKeyAlgorithms=ssh-ed25519",
        "-oUpdateHostKeys=no",
        "-oVerifyHostKeyDNS=no",
        "-oUserKnownHostsFile=" + known_hosts_proc_path,
        "-oGlobalKnownHostsFile=/dev/null",
        "-oKnownHostsCommand=none",
        "-oControlMaster=no",
        "-oControlPath=none",
        "-oControlPersist=no",
        "-oProxyCommand=none",
        "-oProxyJump=none",
        "-oClearAllForwardings=yes",
        "-oForwardAgent=no",
        "-oForwardX11=no",
        "-oPermitLocalCommand=no",
        "-oRequestTTY=no",
        "-oConnectionAttempts=1",
        "-oNumberOfPasswordPrompts=0",
        "-oSendEnv=-*",
        "-oStdinNull=no",
        "-i", identity_proc_path,
        "-p", str(REMOTE_ENDPOINT_PORT),
        "-l", REMOTE_USER,
        "--", REMOTE_ENDPOINT_HOST,
        remote_command,
    )


def _spawn_and_pump(
    *, executable_proc_path: str, pass_fds: tuple[int, ...],
    argv: tuple[str, ...], stdin_raw: bytes,
    timeout_seconds: float = READ_ONLY_TIMEOUT_SECONDS,
) -> _ChildObservation:
    if (
        not executable_proc_path.startswith("/proc/")
        or "/fd/" not in executable_proc_path
        or not argv
        or argv[0] != LOCAL_SSH_EXECUTABLE
        or type(stdin_raw) is not bytes
        or not 0 < len(stdin_raw) <= MAX_ARTIFACT_BYTES
        or not 0.0 < timeout_seconds <= READ_ONLY_TIMEOUT_SECONDS
    ):
        _fail("recovery child resource contract changed")
    empty_sha = hashlib.sha256(b"").hexdigest()
    try:
        process = subprocess.Popen(
            argv,
            executable=executable_proc_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            pass_fds=pass_fds,
            cwd=ROOT,
            env=LOCAL_DISPATCH_ENVIRONMENT,
            start_new_session=True,
        )
    except OSError:
        return _ChildObservation(
            False, None, False, len(stdin_raw), 0, False, b"", 0,
            empty_sha, False, False, b"", 0, empty_sha, False, False,
        )
    sent = 0
    stdout = bytearray()
    stderr_prefix = bytearray()
    stdout_digest = hashlib.sha256()
    stderr_digest = hashlib.sha256()
    stdout_total = 0
    stderr_total = 0
    stdout_overflow = False
    stderr_overflow = False
    stdout_eof = False
    stderr_eof = False
    timed_out = False
    observation_completed = True
    returncode: int | None = None
    deadline = time.monotonic() + timeout_seconds
    drain_deadline: float | None = None
    selector: selectors.BaseSelector | None = None
    streams = (process.stdin, process.stdout, process.stderr)

    def kill_process_group() -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def close_registered_stdin() -> None:
        if selector is None:
            return
        for key in list(selector.get_map().values()):
            if key.data == "stdin":
                try:
                    selector.unregister(key.fileobj)
                except BaseException:
                    pass
                try:
                    key.fileobj.close()
                except BaseException:
                    pass

    try:
        if any(stream is None for stream in streams):
            raise RuntimeError("recovery child pipe construction changed")
        for stream in streams:
            assert stream is not None
            os.set_blocking(stream.fileno(), False)
        selector = selectors.DefaultSelector()
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            now = time.monotonic()
            remaining = deadline - now
            if remaining <= 0:
                if not timed_out:
                    timed_out = True
                    drain_deadline = now + 5.0
                    kill_process_group()
                    close_registered_stdin()
                if drain_deadline is not None and now >= drain_deadline:
                    break
                remaining = 0.1
            events = selector.select(min(max(remaining, 0.0), 0.25))
            if not events and timed_out and process.poll() is not None:
                # Drain any final bytes on the next nonblocking pass.
                events = [
                    (key, selectors.EVENT_READ)
                    for key in list(selector.get_map().values())
                    if key.data in {"stdout", "stderr"}
                ]
            for key, _mask in events:
                stream = key.fileobj
                if key.data == "stdin":
                    if sent == len(stdin_raw):
                        selector.unregister(stream)
                        stream.close()
                        continue
                    try:
                        count = os.write(stream.fileno(), stdin_raw[sent:sent + 65536])
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    if count <= 0:
                        _fail("recovery child stdin made no progress")
                    sent += count
                    if sent == len(stdin_raw):
                        selector.unregister(stream)
                        stream.close()
                else:
                    try:
                        chunk = os.read(stream.fileno(), 65536)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                        if key.data == "stdout":
                            stdout_eof = True
                        else:
                            stderr_eof = True
                        continue
                    if key.data == "stdout":
                        stdout_total += len(chunk)
                        stdout_digest.update(chunk)
                        room = MAX_STDOUT_BYTES + 1 - len(stdout)
                        if room > 0:
                            stdout.extend(chunk[:room])
                        if stdout_total > MAX_STDOUT_BYTES:
                            stdout_overflow = True
                    else:
                        stderr_total += len(chunk)
                        stderr_digest.update(chunk)
                        room = 4096 - len(stderr_prefix)
                        if room > 0:
                            stderr_prefix.extend(chunk[:room])
                        if stderr_total > MAX_STDERR_BYTES:
                            stderr_overflow = True
            if timed_out and process.poll() is None:
                kill_process_group()
        if selector.get_map():
            observation_completed = False
        try:
            returncode = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            observation_completed = False
            kill_process_group()
            try:
                returncode = process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                returncode = process.poll()
    except BaseException:
        observation_completed = False
        kill_process_group()
        try:
            returncode = process.wait(timeout=5)
        except BaseException:
            returncode = process.poll()
    finally:
        if selector is not None:
            selector.close()
        for stream in streams:
            if stream is None:
                continue
            try:
                stream.close()
            except BaseException:
                pass
        if process.poll() is None:
            observation_completed = False
            kill_process_group()
            try:
                process.wait(timeout=5)
            except BaseException:
                pass
    return _ChildObservation(
        exec_succeeded=True,
        returncode=returncode,
        timed_out=timed_out,
        stdin_expected_byte_count=len(stdin_raw),
        stdin_sent_byte_count=sent,
        stdin_complete=sent == len(stdin_raw),
        stdout_raw=bytes(stdout),
        stdout_total_byte_count=stdout_total,
        stdout_sha256=stdout_digest.hexdigest(),
        stdout_overflow=stdout_overflow,
        stdout_eof=stdout_eof,
        stderr_prefix=bytes(stderr_prefix),
        stderr_total_byte_count=stderr_total,
        stderr_sha256=stderr_digest.hexdigest(),
        stderr_overflow=stderr_overflow,
        stderr_eof=stderr_eof,
        transport_observation_completed_without_local_error=(
            observation_completed
        ),
    )


def _child_fact(
    observation: _ChildObservation, *, stdin_raw: bytes,
    transport_materials_verified_after_child: bool = True,
) -> dict[str, Any]:
    stdout_prefix = observation.stdout_raw[:4096]
    stderr_prefix = observation.stderr_prefix[:4096]
    return {
        "exec_succeeded": observation.exec_succeeded,
        "transport_observation_completed_without_local_error": (
            observation.transport_observation_completed_without_local_error
        ),
        "transport_materials_verified_after_child": (
            transport_materials_verified_after_child
        ),
        "returncode": observation.returncode,
        "timed_out": observation.timed_out,
        "stdin_expected_byte_count": observation.stdin_expected_byte_count,
        "stdin_sent_byte_count": observation.stdin_sent_byte_count,
        "stdin_sha256": hashlib.sha256(stdin_raw).hexdigest(),
        "stdin_complete": observation.stdin_complete,
        "stdout_retained_byte_count": len(observation.stdout_raw),
        "stdout_retained_sha256": hashlib.sha256(observation.stdout_raw).hexdigest(),
        "stdout_prefix_byte_count": len(stdout_prefix),
        "stdout_prefix_hex": stdout_prefix.hex(),
        "stdout_total_byte_count": observation.stdout_total_byte_count,
        "stdout_sha256": observation.stdout_sha256,
        "stdout_overflow": observation.stdout_overflow,
        "stdout_eof": observation.stdout_eof,
        "stderr_prefix_byte_count": len(stderr_prefix),
        "stderr_prefix_hex": stderr_prefix.hex(),
        "stderr_total_byte_count": observation.stderr_total_byte_count,
        "stderr_sha256": observation.stderr_sha256,
        "stderr_overflow": observation.stderr_overflow,
        "stderr_eof": observation.stderr_eof,
    }


def _closed_exactly(observation: _ChildObservation) -> bool:
    return bool(
        observation.exec_succeeded
        and observation.transport_observation_completed_without_local_error
        and observation.returncode == 0
        and not observation.timed_out
        and observation.stdin_complete
        and observation.stdin_sent_byte_count
        == observation.stdin_expected_byte_count
        and not observation.stdout_overflow
        and observation.stdout_eof
        and observation.stdout_total_byte_count == len(observation.stdout_raw)
        and observation.stderr_total_byte_count == 0
        and not observation.stderr_overflow
        and observation.stderr_eof
    )


class _VerifiedSourceLoader(importlib.abc.Loader):
    def __init__(
        self, *, fullname: str, relative: str, raw: bytes, package: bool,
    ) -> None:
        self.fullname = fullname
        self.relative = relative
        self.raw = raw
        self.package = package
        self.origin = "<acfqp-v42r3r4-recovery:/" + relative + ">"
        self.exec_count = 0

    def create_module(self, _spec: object) -> None:
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        if self.exec_count != 0:
            _fail("authenticated recovery module executed more than once")
        self.exec_count += 1
        namespace = vars(module)
        namespace["__file__"] = self.origin
        namespace["__cached__"] = None
        exec(
            compile(
                self.raw, self.origin, "exec", flags=0,
                dont_inherit=True, optimize=0,
            ),
            namespace,
            namespace,
        )

    def verify_module(self, module: types.ModuleType) -> None:
        if (
            self.exec_count != 1
            or module.__name__ != self.fullname
            or module.__loader__ is not self
            or module.__file__ != self.origin
            or module.__cached__ is not None
        ):
            _fail("authenticated recovery module identity changed")


class _VerifiedSourceFinder(importlib.abc.MetaPathFinder):
    def __init__(self, raws: Mapping[str, bytes]) -> None:
        self.raws = dict(raws)
        self.created: dict[str, _VerifiedSourceLoader] = {}

    def find_spec(
        self, fullname: str, _path: object = None, _target: object = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname == "acfqp":
            relative = "src/acfqp/__init__.py"
            package = True
        elif fullname.startswith("acfqp."):
            relative = "src/" + fullname.replace(".", "/") + ".py"
            package = False
        else:
            return None
        raw = self.raws.get(relative)
        if raw is None:
            raise ImportError("unmanifested recovery module: " + fullname)
        if fullname in self.created:
            raise ImportError("recovery module loader repeated: " + fullname)
        loader = _VerifiedSourceLoader(
            fullname=fullname, relative=relative, raw=raw, package=package
        )
        self.created[fullname] = loader
        spec = importlib.machinery.ModuleSpec(
            fullname, loader, origin=loader.origin, is_package=package
        )
        if package:
            spec.submodule_search_locations = []
        return spec

    def verify_loaded(self) -> None:
        if not sys.meta_path or sys.meta_path[0] is not self:
            _fail("authenticated recovery finder position changed")
        for name, loader in self.created.items():
            module = sys.modules.get(name)
            if module is None:
                _fail("authenticated recovery module disappeared")
            loader.verify_module(module)


_AUTHENTICATED_FINDER: _VerifiedSourceFinder | None = None


def _authority(current_raws: Mapping[str, bytes]) -> Any:
    global _AUTHENTICATED_FINDER
    if AUTHORITY_RELATIVE not in current_raws:
        _fail("authenticated recovery authority source is absent")
    existing = [
        name for name in sys.modules
        if name == "acfqp" or name.startswith("acfqp.")
    ]
    if existing:
        _fail("project module loaded before recovery source authentication")
    if _AUTHENTICATED_FINDER is not None:
        _fail("recovery verified importer installation repeated")
    finder = _VerifiedSourceFinder(current_raws)
    sys.meta_path.insert(0, finder)
    _AUTHENTICATED_FINDER = finder
    module = importlib.import_module(AUTHORITY_MODULE)
    finder.verify_loaded()
    return module


def _retained_occurrence(authority: Any, raws: Mapping[str, bytes]) -> dict[str, Any]:
    return authority.build_retained_launch_occurrence_v42r3r4(
        root_identity_raw=raws["root_identity"],
        retained_controller_source_manifest=raws["controller_source_manifest"],
        formal_transport_plan=raws["formal_transport_plan"],
        prepare_receipt=raws["prepare_receipt"],
        local_launch_attempt=raws["local_launch_attempt"],
        formal_launch_transport_attempt=raws[
            "formal_launch_transport_attempt"
        ],
        inner_network_start=raws["inner_network_start"],
        parent_network_start=raws["parent_network_start"],
        operation_outcome=raws["operation_outcome"],
    )


def _remote_ingress(
    *, recovery_plan: Mapping[str, Any], occurrence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v42r3r4_formal_launch_recovery_ingress",
        "schema_version": "42.3.4",
        "recovery_plan_id": recovery_plan["recovery_plan_id"],
        "retained_launch_occurrence_id": occurrence[
            "retained_launch_occurrence_id"
        ],
        "retained_formal_transport_plan": occurrence["formal_transport_plan"],
        "retained_formal_transport_plan_id": RETAINED_PLAN_ID,
        "retained_local_launch_attempt_id": RETAINED_ATTEMPT_ID,
        "retained_remote_journal_root": RETAINED_REMOTE_ROOT,
        "retained_systemd_unit_name": RETAINED_UNIT_NAME,
        "expected_remote_hostname": EXPECTED_REMOTE_HOSTNAME,
        "expected_remote_uid": EXPECTED_REMOTE_UID,
        "expected_remote_gid": EXPECTED_REMOTE_GID,
        "recovery_inspection_ordinal": 1,
    }


def _dispatch_failure_document(
    *, recovery_plan: Mapping[str, Any],
    inspection_attempt: Mapping[str, Any], error: BaseException,
    network_dispatch_may_have_started: bool,
) -> dict[str, Any]:
    if type(network_dispatch_may_have_started) is not bool:
        _fail("recovery dispatch failure boundary changed")
    failure_type = type(error).__module__ + "." + type(error).__qualname__
    message_raw = str(error).encode("utf-8", errors="backslashreplace")
    prefix = message_raw[:4096]
    payload = {
        "schema": "acfqp.v42_formal_transport_recovery_dispatch_failure.v42r3r4",
        "schema_version": "42.3.4",
        "formal_identity": "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2",
        "global_execution_ordinal": 2,
        "recovery_plan_id": recovery_plan["recovery_plan_id"],
        "recovery_inspection_attempt_id": inspection_attempt[
            "recovery_inspection_attempt_id"
        ],
        "failure_type": failure_type,
        "message_byte_count": len(message_raw),
        "message_sha256": hashlib.sha256(message_raw).hexdigest(),
        "message_prefix_byte_count": len(prefix),
        "message_prefix_hex": prefix.hex(),
        "network_dispatch_may_have_started": network_dispatch_may_have_started,
        "same_recovery_dispatch_replay_allowed": False,
        "retained_same_effect_dispatch_replay_allowed": False,
        "authenticated_remote_mutation_authorized": False,
    }
    return {
        **payload,
        "recovery_dispatch_failure_id": hashlib.sha256(
            b"acfqp:v42-formal-transport-recovery:dispatch-failure:v42r3r4\0"
            + _canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _authentication_failure_document(
    *, recovery_plan: Mapping[str, Any],
    inspection_attempt: Mapping[str, Any],
    bounded_observation: Mapping[str, Any], error: BaseException,
) -> dict[str, Any]:
    failure_type = type(error).__module__ + "." + type(error).__qualname__
    message_raw = str(error).encode("utf-8", errors="backslashreplace")
    prefix = message_raw[:4096]
    payload = {
        "schema": (
            "acfqp.v42_formal_transport_recovery_authentication_failure.v42r3r4"
        ),
        "schema_version": "42.3.4",
        "recovery_plan_id": recovery_plan["recovery_plan_id"],
        "recovery_inspection_attempt_id": inspection_attempt[
            "recovery_inspection_attempt_id"
        ],
        "bounded_child_transport_observation_id": bounded_observation[
            "bounded_child_transport_observation_id"
        ],
        "failure_type": failure_type,
        "message_byte_count": len(message_raw),
        "message_sha256": hashlib.sha256(message_raw).hexdigest(),
        "message_prefix_byte_count": len(prefix),
        "message_prefix_hex": prefix.hex(),
        "same_recovery_dispatch_replay_allowed": False,
        "retained_same_effect_dispatch_replay_allowed": False,
        "remote_inspection_authenticated": False,
    }
    return {
        **payload,
        "recovery_authentication_failure_id": hashlib.sha256(
            b"acfqp:v42-formal-transport-recovery:authentication-failure:v42r3r4\0"
            + _canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _inspection_file(prefix: str) -> str:
    return prefix + "00000001.json"


def _summary(
    *, manifest: Mapping[str, Any], occurrence: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v42_formal_transport_recovery_input_summary.v42r3r4",
        "schema_version": "42.3.4",
        "recovery_controller_source_manifest_id": manifest[
            "recovery_controller_source_manifest_id"
        ],
        "retained_launch_occurrence_id": occurrence[
            "retained_launch_occurrence_id"
        ],
        "recovery_plan_id": plan["recovery_plan_id"],
        "retained_formal_transport_plan_id": RETAINED_PLAN_ID,
        "retained_local_launch_attempt_id": RETAINED_ATTEMPT_ID,
        "retained_outcome": "POST_MARKER_WITHOUT_EXACT_RECEIPT",
        "retained_same_effect_dispatch_replay_allowed": False,
        "new_scientific_execution_authorized": False,
        "current_remote_absence_is_historical_never_started_proof": False,
        "network_operation_performed": False,
        "local_recovery_journal_mutated": False,
        "retained_r3r3_journal_mutated": False,
        "external_local_and_ssh_assumptions_observed_or_attested": False,
    }


def verify_recovery_inputs(
    *, expected_controller_commit: str, expected_controller_tree: str,
) -> tuple[
    Any, dict[str, bytes], dict[str, Any], dict[str, Any], dict[str, Any],
    tuple[Any, ...],
]:
    current_raws, source_facts = _verified_current_sources(
        expected_controller_commit, expected_controller_tree
    )
    authority = _authority(current_raws)
    manifest = authority.build_recovery_controller_source_manifest_v42r3r4(
        source_commit=expected_controller_commit,
        source_tree=expected_controller_tree,
        source_facts=source_facts,
    )
    manifest = authority.verify_recovery_controller_source_manifest_v42r3r4(
        manifest
    )
    retained_raws, retained_snapshot = _read_retained_artifacts()
    occurrence = _retained_occurrence(authority, retained_raws)
    occurrence = authority.verify_retained_launch_occurrence_v42r3r4(occurrence)
    plan = authority.build_recovery_plan_v42r3r4(
        recovery_controller_source_manifest=manifest,
        retained_launch_occurrence=occurrence,
    )
    plan = authority.verify_recovery_plan_v42r3r4(plan)
    _verify_retained_unchanged(retained_snapshot)
    return (
        authority, current_raws, manifest, occurrence, plan, retained_snapshot,
    )


def _execute_read_only_recovery(
    *, authority: Any, current_raws: Mapping[str, bytes],
    manifest: Mapping[str, Any], occurrence: Mapping[str, Any],
    plan: Mapping[str, Any], retained_snapshot: tuple[Any, ...],
) -> tuple[dict[str, Any], int]:
    with _RecoveryJournal.open_or_create() as journal:
        journal.publish_or_verify(
            RECOVERY_CONTROLLER_NAME, _canonical_json_bytes(dict(manifest))
        )
        journal.publish_or_verify(
            RETAINED_OCCURRENCE_NAME, _canonical_json_bytes(dict(occurrence))
        )
        journal.publish_or_verify(
            RECOVERY_PLAN_NAME, _canonical_json_bytes(dict(plan))
        )
        attempt = authority.build_recovery_inspection_attempt_v42r3r4(
            recovery_plan=plan
        )
        attempt_raw = _canonical_json_bytes(attempt)
        attempt = authority.verify_recovery_inspection_attempt_v42r3r4(
            attempt, recovery_plan=plan
        )
        ingress = authority.build_recovery_transport_ingress_v42r3r4(
            recovery_plan=plan
        )
        if ingress != _remote_ingress(
            recovery_plan=plan, occurrence=occurrence
        ):
            _fail("launcher and authority canonical recovery ingress changed")
        ingress_raw = _canonical_json_bytes(ingress)
        receiver_raw = current_raws[RECEIVER_RELATIVE]
        receiver_fact = attempt["recovery_receiver_artifact"]
        if (
            receiver_fact != manifest["recovery_receiver_artifact"]
            or receiver_fact["byte_count"] != len(receiver_raw)
            or receiver_fact["sha256"]
            != hashlib.sha256(receiver_raw).hexdigest()
            or attempt["authorized_remote_mode"] != REMOTE_MODE
            or attempt["canonical_remote_ingress"] != ingress
            or attempt["canonical_remote_ingress_fact"]
            != {
                "byte_count": len(ingress_raw),
                "sha256": hashlib.sha256(ingress_raw).hexdigest(),
            }
            or attempt["remote_command_projection"]
            != _actual_remote_command_projection(
                receiver_raw,
                ingress_raw,
                recovery_plan_id=plan["recovery_plan_id"],
            )
        ):
            _fail("recovery attempt transport authorization changed")
        command = _remote_command(
            receiver_raw,
            ingress_raw,
            recovery_plan_id=plan["recovery_plan_id"],
        )
        ssh_pin: _PinnedFile | None = None
        identity_pin: _PinnedFile | None = None
        known_hosts_pin: _PinnedFile | None = None
        network_dispatch_may_have_started = False
        observation: _ChildObservation | None = None
        pre_observation_error: BaseException | None = None
        post_child_material_error: BaseException | None = None
        attempt_persisted = False
        try:
            ssh_pin = _PinnedFile.open(
                Path(LOCAL_SSH_EXECUTABLE), mode=0o755, uid=0, gid=0,
                byte_count=SSH_BYTE_COUNT, sha256=SSH_SHA256,
            )
            identity_pin = _PinnedFile.open(
                Path(LOCAL_IDENTITY_FILE), mode=0o600,
                uid=os.geteuid(), gid=os.getegid(),
                byte_count=IDENTITY_BYTE_COUNT, sha256=IDENTITY_SHA256,
            )
            known_hosts_pin = _PinnedFile.open(
                RETAINED_LOCAL_ROOT / KNOWN_HOSTS_NAME, mode=0o400,
                uid=os.geteuid(), gid=os.getegid(),
                byte_count=KNOWN_HOSTS_BYTE_COUNT, sha256=KNOWN_HOSTS_SHA256,
            )
            ssh_proc_path = ssh_pin.proc_path
            identity_proc_path = identity_pin.proc_path
            known_hosts_proc_path = known_hosts_pin.proc_path
            argv = _ssh_argv(
                known_hosts_proc_path=known_hosts_proc_path,
                identity_proc_path=identity_proc_path,
                remote_command=command,
            )
            # Consume the sole recovery ordinal only after every local transport
            # material has been pinned and the exact argv has been built.
            journal.publish_once(_inspection_file(ATTEMPT_PREFIX), attempt_raw)
            attempt = authority.verify_recovery_inspection_attempt_v42r3r4(
                journal.read(_inspection_file(ATTEMPT_PREFIX)),
                recovery_plan=plan,
            )
            attempt_persisted = True
            network_dispatch_may_have_started = True
            observation = _spawn_and_pump(
                executable_proc_path=ssh_proc_path,
                pass_fds=(
                    ssh_pin.descriptor,
                    identity_pin.descriptor,
                    known_hosts_pin.descriptor,
                ),
                argv=argv,
                stdin_raw=ingress_raw,
            )
            try:
                ssh_pin.verify()
                identity_pin.verify()
                known_hosts_pin.verify()
            except BaseException as error:
                post_child_material_error = error
        except BaseException as error:
            if observation is None:
                pre_observation_error = error
            else:
                post_child_material_error = error
        finally:
            for pin in (known_hosts_pin, identity_pin, ssh_pin):
                if pin is not None:
                    try:
                        pin.close()
                    except BaseException as error:
                        if observation is None and pre_observation_error is None:
                            pre_observation_error = error
                        elif post_child_material_error is None:
                            post_child_material_error = error
        if observation is None:
            assert pre_observation_error is not None
            if not attempt_persisted:
                raise pre_observation_error
            failure = _dispatch_failure_document(
                recovery_plan=plan,
                inspection_attempt=attempt,
                error=pre_observation_error,
                network_dispatch_may_have_started=(
                    network_dispatch_may_have_started
                ),
            )
            journal.publish_once(
                _inspection_file(DISPATCH_FAILURE_PREFIX),
                _canonical_json_bytes(failure),
            )
            raise pre_observation_error
        if post_child_material_error is not None:
            failure = _dispatch_failure_document(
                recovery_plan=plan,
                inspection_attempt=attempt,
                error=post_child_material_error,
                network_dispatch_may_have_started=True,
            )
            journal.publish_once(
                _inspection_file(DISPATCH_FAILURE_PREFIX),
                _canonical_json_bytes(failure),
            )
        # The authority may compute exact-close here, but the controller does
        # not branch on it until the resulting fact is durable and reverified.
        bounded = authority.build_bounded_child_transport_observation_v42r3r4(
            recovery_plan=plan,
            recovery_inspection_attempt=attempt,
            child_observation=_child_fact(
                observation,
                stdin_raw=ingress_raw,
                transport_materials_verified_after_child=(
                    post_child_material_error is None
                ),
            ),
        )
        bounded_raw = _canonical_json_bytes(bounded)
        journal.publish_once(_inspection_file(OBSERVATION_PREFIX), bounded_raw)
        bounded = authority.verify_bounded_child_transport_observation_v42r3r4(
            journal.read(_inspection_file(OBSERVATION_PREFIX)),
            recovery_plan=plan,
            recovery_inspection_attempt=attempt,
        )
        if bounded["process_closed_exactly"] is not True:
            classification = authority.classify_recovery_v42r3r4(
                recovery_plan=plan,
                recovery_inspection_attempt=attempt,
                bounded_child_transport_observation=bounded,
                remote_inspection_join=None,
            )
            classification_raw = _canonical_json_bytes(classification)
            journal.publish_once(
                _inspection_file(CLASSIFICATION_PREFIX), classification_raw
            )
            authority.verify_recovery_classification_v42r3r4(
                journal.read(_inspection_file(CLASSIFICATION_PREFIX)),
                recovery_plan=plan,
                recovery_inspection_attempt=attempt,
                bounded_child_transport_observation=bounded,
                remote_inspection_join=None,
            )
            _verify_retained_unchanged(retained_snapshot)
            return classification, 2
        try:
            stdout_raw = observation.stdout_raw
            if not stdout_raw.endswith(b"\n") or stdout_raw.endswith(b"\n\n"):
                _fail("recovery remote stdout framing changed")
            remote = _canonical_document(
                stdout_raw[:-1], "recovery remote read-only inspection"
            )
            join = authority.build_remote_inspection_join_v42r3r4(
                recovery_plan=plan,
                recovery_inspection_attempt=attempt,
                bounded_child_transport_observation=bounded,
                remote_read_only_inspection=remote,
            )
        except BaseException as error:
            failure = _authentication_failure_document(
                recovery_plan=plan,
                inspection_attempt=attempt,
                bounded_observation=bounded,
                error=error,
            )
            journal.publish_once(
                _inspection_file(AUTHENTICATION_FAILURE_PREFIX),
                _canonical_json_bytes(failure),
            )
            classification = authority.classify_recovery_v42r3r4(
                recovery_plan=plan,
                recovery_inspection_attempt=attempt,
                bounded_child_transport_observation=bounded,
                remote_inspection_join=None,
            )
            journal.publish_once(
                _inspection_file(CLASSIFICATION_PREFIX),
                _canonical_json_bytes(classification),
            )
            classification = authority.verify_recovery_classification_v42r3r4(
                journal.read(_inspection_file(CLASSIFICATION_PREFIX)),
                recovery_plan=plan,
                recovery_inspection_attempt=attempt,
                bounded_child_transport_observation=bounded,
                remote_inspection_join=None,
            )
            _verify_retained_unchanged(retained_snapshot)
            return classification, 2
        journal.publish_once(
            _inspection_file(REMOTE_INSPECTION_PREFIX), stdout_raw[:-1]
        )
        journal.publish_once(
            _inspection_file(REMOTE_JOIN_PREFIX), _canonical_json_bytes(join)
        )
        join = authority.verify_remote_inspection_join_v42r3r4(
            journal.read(_inspection_file(REMOTE_JOIN_PREFIX)),
            recovery_plan=plan,
            recovery_inspection_attempt=attempt,
            bounded_child_transport_observation=bounded,
        )
        classification = authority.classify_recovery_v42r3r4(
            recovery_plan=plan,
            recovery_inspection_attempt=attempt,
            bounded_child_transport_observation=bounded,
            remote_inspection_join=join,
        )
        journal.publish_once(
            _inspection_file(CLASSIFICATION_PREFIX),
            _canonical_json_bytes(classification),
        )
        classification = authority.verify_recovery_classification_v42r3r4(
            journal.read(_inspection_file(CLASSIFICATION_PREFIX)),
            recovery_plan=plan,
            recovery_inspection_attempt=attempt,
            bounded_child_transport_observation=bounded,
            remote_inspection_join=join,
        )
        _verify_retained_unchanged(retained_snapshot)
        return classification, 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V42r3r4 recovery-only retained launch inspector"
    )
    parser.add_argument("--expected-controller-commit", required=True)
    parser.add_argument("--expected-controller-tree", required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify-inputs-only", action="store_true")
    modes.add_argument("--inspect-retained-launch-v42r3r4", action="store_true")
    parser.add_argument("--recovery-inspection-ordinal", type=int, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _require_sealed_stage_materials()
    arguments = _parser().parse_args(argv)
    if arguments.recovery_inspection_ordinal != 1:
        _fail("V42r3r4 recovery has exactly one preregistered inspection ordinal")
    if (
        _HEX40.fullmatch(arguments.expected_controller_commit) is None
        or _HEX40.fullmatch(arguments.expected_controller_tree) is None
    ):
        _fail("expected recovery controller Git identity changed")
    (
        authority, current_raws, manifest, occurrence, plan, snapshot,
    ) = verify_recovery_inputs(
        expected_controller_commit=arguments.expected_controller_commit,
        expected_controller_tree=arguments.expected_controller_tree,
    )
    if arguments.verify_inputs_only:
        result = _summary(manifest=manifest, occurrence=occurrence, plan=plan)
        exit_code = 0
    else:
        result, exit_code = _execute_read_only_recovery(
            authority=authority,
            current_raws=current_raws,
            manifest=manifest,
            occurrence=occurrence,
            plan=plan,
            retained_snapshot=snapshot,
        )
    raw = _canonical_json_bytes(result) + b"\n"
    _write_all(1, raw)
    return exit_code


if __name__ == "__main__":
    if dict(os.environ) != EXACT_ENVIRONMENT:
        raise RuntimeError("V42r3r4 recovery launcher environment changed")
    raise SystemExit(main())
