#!/usr/bin/env python3
"""Source-only production entry for V42 activation and formal transport.

The only supported process entry is::

    /usr/bin/env -i LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=/usr/bin:/bin \
      /usr/bin/python3 -I -S -B /absolute/path/to/this/file ...

Repository Python is compiled only from bytes joined to the retained five
controls, the selected committed HEAD/tree, and the transport manifest.  The
selected driver ``main`` is the sole call across the effect boundary.
"""

from __future__ import annotations

# This import is builtin.  The gate deliberately runs before any path-loaded
# stdlib module, so an unchecked matching-header ``*.pyc`` cannot participate
# in rejection of a malformed direct entry.
import sys as _early_sys


def _early_direct_entry_gate() -> None:
    expected_prefix = ["/usr/bin/python3", "-I", "-S", "-B"]
    file_name = globals().get("__file__")
    if (
        type(file_name) is not str
        or not file_name.startswith("/")
        or "\x00" in file_name
        or any(part in {"", ".", ".."} for part in file_name.split("/")[1:])
        or _early_sys.executable != "/usr/bin/python3"
        or tuple(_early_sys.version_info[:3]) != (3, 10, 12)
        or _early_sys.flags.isolated != 1
        or _early_sys.flags.no_site != 1
        or _early_sys.dont_write_bytecode is not True
        or _early_sys.gettrace() is not None
        or _early_sys.getprofile() is not None
        or type(_early_sys.argv) is not list
        or not _early_sys.argv
        or _early_sys.argv[0] != file_name
        or list(_early_sys.orig_argv) != [*expected_prefix, *_early_sys.argv]
    ):
        raise RuntimeError("unified launcher direct entry changed")


if __name__ == "__main__":
    try:
        _early_direct_entry_gate()
    except BaseException:
        _early_sys.stderr.write("acfqp v42 production launcher rejected\n")
        raise SystemExit(72)


from dataclasses import dataclass
import fcntl
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from types import MappingProxyType, ModuleType
from typing import Any, Callable, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
SCRIPT_PATH = ROOT / "scripts/launch_v42_activation_or_formal.py"

LOCAL_PYTHON = "/usr/bin/python3"
LOCAL_PYTHON_REALPATH = "/usr/bin/python3.10"
LOCAL_PYTHON_VERSION = (3, 10, 12)
EXACT_ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
}
EXACT_PYTHON_PATH = [
    "/usr/lib/python310.zip",
    "/usr/lib/python3.10",
    "/usr/lib/python3.10/lib-dynload",
]

SOURCE_MANIFEST_NAME = "EXECUTION_SOURCE_MANIFEST.json"
LOCAL_MATERIALIZATION_ATTEMPT_NAME = "LOCAL_MATERIALIZATION_ATTEMPT.json"
REMOTE_BOOTSTRAP_PYZ_NAME = "REMOTE_BOOTSTRAP.pyz"
SOURCE_CAPSULE_NAME = "SOURCE_CAPSULE.tar"
TRANSPORT_MANIFEST_NAME = "TRANSPORT_MANIFEST.json"
CONTROL_NAMES = tuple(sorted((
    SOURCE_MANIFEST_NAME,
    LOCAL_MATERIALIZATION_ATTEMPT_NAME,
    REMOTE_BOOTSTRAP_PYZ_NAME,
    SOURCE_CAPSULE_NAME,
    TRANSPORT_MANIFEST_NAME,
)))
MAXIMUM_CONTROL_BYTES = {
    SOURCE_MANIFEST_NAME: 64 * 1024**2,
    LOCAL_MATERIALIZATION_ATTEMPT_NAME: 4 * 1024**2,
    REMOTE_BOOTSTRAP_PYZ_NAME: 64 * 1024**2,
    SOURCE_CAPSULE_NAME: 2 * 1024**3,
    TRANSPORT_MANIFEST_NAME: 64 * 1024**2,
}
MAXIMUM_TCB_SOURCE_BYTES = 8 * 1024**2
MAXIMUM_EVIDENCE_BYTES = 4 * 1024**2
READ_CHUNK_BYTES = 1024 * 1024

FROZEN_LAUNCHER_RELATIVE = "scripts/launch_v42_preformal_upload_sender.py"
FROZEN_LAUNCHER_BYTE_COUNT = 61_522
FROZEN_LAUNCHER_SHA256 = (
    "126c5628d07c3d82977ccf9d4023846161b4f45b87842330c3e3b75abe638a77"
)
FROZEN_LAUNCHER_GIT_BLOB = "0f5a185642271dce244fc94dc72e9a59f5de40f9"
ACTIVATION_DRIVER_RELATIVE = "scripts/run_v42_materialization_activation.py"
FORMAL_DRIVER_RELATIVE = "scripts/run_v42_standard_2048_formal_transport_driver.py"

# These are transport TCB additions, not scientific runner-source additions.
# Every source_fact remains admitted separately and must be an exact identical
# transport_fact.  Extra transport Python outside this explicit union is not
# imported by this launcher.
TRANSPORT_ONLY_TCB_PATHS = frozenset({
    "scripts/__init__.py",
    "scripts/launch_v42_activation_or_formal.py",
    FROZEN_LAUNCHER_RELATIVE,
    "scripts/publish_v42_preformal_upload_journal.py",
    "scripts/run_v42_preformal_upload_sender.py",
    "scripts/v42_preformal_upload_loader.py",
    "scripts/v42_preformal_upload_receiver.py",
    ACTIVATION_DRIVER_RELATIVE,
    "scripts/v42_materialization_activation_loader.py",
    "scripts/v42_materialization_activation_receiver.py",
    "scripts/v42_materialization_activation_service.py",
    FORMAL_DRIVER_RELATIVE,
    "scripts/v42_standard_2048_formal_transport_receiver.py",
    "scripts/run_v42_standard_2048_remote_ordinal2.py",
    "src/acfqp/__init__.py",
    "src/acfqp/phase3e_ids.py",
    "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
})

EXPECTED_MODULES_BY_OPERATION = MappingProxyType({
    "activation": MappingProxyType({
        "acfqp": "src/acfqp/__init__.py",
        "acfqp.artifacts": "src/acfqp/artifacts.py",
        "acfqp.build_coverage": "src/acfqp/build_coverage.py",
        "acfqp.construction_k7_domain_registry_extension_v42":
            "src/acfqp/construction_k7_domain_registry_extension_v42.py",
        "acfqp.construction_k7_standard_2048_materialization_activation_v42r1":
            "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py",
        "acfqp.construction_k7_standard_2048_materialization_transport_v42r1":
            "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
        "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1":
            "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
        "acfqp.core": "src/acfqp/core.py",
        "acfqp.enumeration": "src/acfqp/enumeration.py",
        "acfqp.phase3e_ids": "src/acfqp/phase3e_ids.py",
        "scripts": "scripts/__init__.py",
        "scripts.publish_v42_preformal_upload_journal":
            "scripts/publish_v42_preformal_upload_journal.py",
        "scripts.run_v42_materialization_activation": ACTIVATION_DRIVER_RELATIVE,
        "scripts.run_v42_preformal_upload_sender":
            "scripts/run_v42_preformal_upload_sender.py",
    }),
    "formal": MappingProxyType({
        "acfqp": "src/acfqp/__init__.py",
        "acfqp.artifacts": "src/acfqp/artifacts.py",
        "acfqp.build_coverage": "src/acfqp/build_coverage.py",
        "acfqp.construction_k7_domain_registry_extension_v42":
            "src/acfqp/construction_k7_domain_registry_extension_v42.py",
        "acfqp.construction_k7_standard_2048_formal_transport_v42r1":
            "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
        "acfqp.construction_k7_standard_2048_fresh_terminal_preregistration_v42":
            "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
        "acfqp.construction_k7_standard_2048_history_manifest_v42":
            "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
        "acfqp.construction_k7_standard_2048_materialization_activation_v42r1":
            "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py",
        "acfqp.construction_k7_standard_2048_materialization_transport_v42r1":
            "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
        "acfqp.construction_k7_standard_2048_process_supervision_v42r1":
            "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
        "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1":
            "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
        "acfqp.core": "src/acfqp/core.py",
        "acfqp.enumeration": "src/acfqp/enumeration.py",
        "acfqp.phase3e_ids": "src/acfqp/phase3e_ids.py",
        "scripts": "scripts/__init__.py",
        "scripts.publish_v42_preformal_upload_journal":
            "scripts/publish_v42_preformal_upload_journal.py",
        "scripts.run_v42_preformal_upload_sender":
            "scripts/run_v42_preformal_upload_sender.py",
        "scripts.run_v42_standard_2048_formal_transport_driver":
            FORMAL_DRIVER_RELATIVE,
        "scripts.run_v42_standard_2048_remote_ordinal2":
            "scripts/run_v42_standard_2048_remote_ordinal2.py",
    }),
})

PREFORMAL_PLAN_NAME = "PREFORMAL_UPLOAD_PLAN.json"
ACTIVATION_ROOTS_NAME = "ACTIVATION_EVIDENCE_ROOTS.json"
ACTIVATION_FINAL_INDEX_NAME = (
    "MATERIALIZATION_ACTIVATION_FINAL_EVIDENCE_INDEX.json"
)
_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_FACT_FIELDS = {
    "relative_path", "git_mode", "git_object_type", "git_blob_oid",
    "byte_count", "sha256",
}


class V42ProductionLauncherError(RuntimeError):
    """The production entry or a pre-effect binding changed."""


def _fail(message: str) -> NoReturn:
    raise V42ProductionLauncherError(message)


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42ProductionLauncherError("canonical JSON encoding changed") from error


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("JSON object contains a duplicate key")
        result[key] = value
    return result


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _token: _fail(label + " contains nonfinite JSON"),
        )
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42ProductionLauncherError(label + " is not strict JSON") from error
    if type(document) is not dict or _canonical_json_bytes(document) != raw:
        _fail(label + " is not one canonical JSON object")
    return document


def _content_id(domain: str, document: dict[str, Any], key: str, label: str) -> str:
    identifier = document.get(key)
    payload = dict(document)
    payload.pop(key, None)
    if (
        type(identifier) is not str
        or _HEX64.fullmatch(identifier) is None
        or hashlib.sha256(
            domain.encode("ascii") + b"\0" + _canonical_json_bytes(payload)
        ).hexdigest() != identifier
    ):
        _fail(label + " content identity changed")
    return identifier


def _git_blob_oid(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - exact Git object identity
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _directory_state(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
    )


def _file_state(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
        value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns,
    )


def _absolute_path(value: str, label: str) -> Path:
    if type(value) is not str or not value or "\x00" in value:
        _fail(label + " changed type or emptiness")
    path = Path(value)
    if (
        not path.is_absolute()
        or path == Path(path.anchor)
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts[1:])
    ):
        _fail(label + " must be one lexical absolute non-root path")
    return path


@dataclass
class _DirectoryPin:
    path: Path
    names: list[str]
    descriptors: list[int]
    states: list[tuple[int, ...]]

    @property
    def descriptor(self) -> int:
        return self.descriptors[-1]

    @classmethod
    def open(cls, path: Path, label: str) -> "_DirectoryPin":
        _absolute_path(path.as_posix(), label)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptors = [os.open("/", flags)]
        names = [""]
        states = [_directory_state(os.fstat(descriptors[0]))]
        try:
            for component in path.parts[1:]:
                named = os.stat(
                    component, dir_fd=descriptors[-1], follow_symlinks=False
                )
                child = os.open(component, flags, dir_fd=descriptors[-1])
                opened = os.fstat(child)
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or _directory_state(named) != _directory_state(opened)
                ):
                    os.close(child)
                    _fail(label + " directory component changed while opening")
                descriptors.append(child)
                names.append(component)
                states.append(_directory_state(opened))
            result = cls(path, names, descriptors, states)
            result.verify()
            return result
        except BaseException:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
            raise

    def verify(self) -> None:
        if not (
            len(self.names) == len(self.descriptors) == len(self.states)
            and self.descriptors
        ):
            _fail("held directory pin structure changed")
        for index, (descriptor, expected) in enumerate(
            zip(self.descriptors, self.states, strict=True)
        ):
            observed = os.fstat(descriptor)
            if _directory_state(observed) != expected:
                _fail("held directory identity changed")
            if index:
                named = os.stat(
                    self.names[index],
                    dir_fd=self.descriptors[index - 1],
                    follow_symlinks=False,
                )
                if _directory_state(named) != expected:
                    _fail("named directory was replaced after pinning")

    def close(self) -> None:
        for descriptor in reversed(self.descriptors):
            os.close(descriptor)
        self.descriptors.clear()
        self.states.clear()
        self.names.clear()


@dataclass
class _RootGuard:
    path: Path
    parent: _DirectoryPin
    descriptor: int | None
    state: tuple[int, ...] | None

    @classmethod
    def capture(
        cls, path: Path, label: str, *, require_existing: bool
    ) -> "_RootGuard":
        parent = _DirectoryPin.open(path.parent, label + " parent")
        descriptor: int | None = None
        state: tuple[int, ...] | None = None
        try:
            try:
                named = os.stat(path.name, dir_fd=parent.descriptor, follow_symlinks=False)
            except FileNotFoundError:
                if require_existing:
                    _fail(label + " is absent")
            else:
                descriptor = os.open(
                    path.name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=parent.descriptor,
                )
                opened = os.fstat(descriptor)
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or stat.S_IMODE(opened.st_mode) != 0o700
                    or opened.st_uid != os.geteuid()
                    or opened.st_gid != os.getegid()
                    or _directory_state(opened) != _directory_state(named)
                ):
                    _fail(label + " directory metadata changed")
                state = _directory_state(opened)
            result = cls(path, parent, descriptor, state)
            result.verify()
            return result
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
            parent.close()
            raise

    def verify(self) -> None:
        self.parent.verify()
        try:
            named = os.stat(
                self.path.name,
                dir_fd=self.parent.descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            if self.state is not None or self.descriptor is not None:
                _fail("guarded root disappeared")
            return
        if self.state is None or self.descriptor is None:
            _fail("guarded prospective root appeared before dispatch")
        if (
            _directory_state(named) != self.state
            or _directory_state(os.fstat(self.descriptor)) != self.state
        ):
            _fail("guarded root was replaced after capture")

    def close(self) -> None:
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None
        self.parent.close()


def _read_stream(descriptor: int, maximum: int, *, retain: bool) -> tuple[bytes, str, int]:
    chunks: list[bytes] = []
    digest = hashlib.sha256()
    count = 0
    while True:
        remaining = maximum + 1 - count
        if remaining <= 0:
            _fail("bounded file exceeded its byte cap")
        chunk = os.read(descriptor, min(READ_CHUNK_BYTES, remaining))
        if not chunk:
            break
        digest.update(chunk)
        count += len(chunk)
        if retain:
            chunks.append(chunk)
        if count > maximum:
            _fail("bounded file exceeded its byte cap")
    return (b"".join(chunks) if retain else b"", digest.hexdigest(), count)


def _read_regular_at(
    parent_fd: int,
    name: str,
    maximum: int,
    *,
    expected_modes: frozenset[int],
    label: str,
) -> bytes:
    if (
        type(name) is not str or not name or name in {".", ".."}
        or "/" in name or "\x00" in name
    ):
        _fail(label + " basename changed")
    descriptor = -1
    try:
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) not in expected_modes
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_nlink != 1
            or not 0 < before.st_size <= maximum
            or _file_state(named) != _file_state(before)
        ):
            _fail(label + " metadata changed")
        raw, digest, count = _read_stream(descriptor, maximum, retain=True)
        middle = os.fstat(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        _discarded, digest2, count2 = _read_stream(descriptor, maximum, retain=False)
        final = os.fstat(descriptor)
        named2 = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            count != before.st_size or count2 != count or digest2 != digest
            or hashlib.sha256(raw).hexdigest() != digest
            or _file_state(before) != _file_state(middle)
            or _file_state(before) != _file_state(final)
            or _file_state(before) != _file_state(named2)
        ):
            _fail(label + " changed during stable readback")
        return raw
    except OSError as error:
        raise V42ProductionLauncherError(
            label + " could not be read through no-follow boundary"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_relative_source(root_fd: int, relative: str) -> bytes:
    parsed = PurePosixPath(relative)
    if (
        parsed.is_absolute() or parsed.as_posix() != relative
        or len(parsed.parts) < 2
        or any(part in {"", ".", ".."} for part in parsed.parts)
    ):
        _fail("TCB relative path changed")
    current = os.dup(root_fd)
    try:
        for component in parsed.parts[:-1]:
            named = os.stat(component, dir_fd=current, follow_symlinks=False)
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=current,
            )
            opened = os.fstat(child)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or _directory_state(opened) != _directory_state(named)
            ):
                os.close(child)
                _fail("TCB source directory changed")
            os.close(current)
            current = child
        return _read_regular_at(
            current, parsed.parts[-1], MAXIMUM_TCB_SOURCE_BYTES,
            expected_modes=frozenset({0o444, 0o644}),
            label="TCB source " + relative,
        )
    finally:
        os.close(current)


def _read_controls(control: _RootGuard) -> dict[str, bytes]:
    control.verify()
    if control.descriptor is None:
        _fail("control root is absent")
    if tuple(sorted(os.listdir(control.descriptor))) != CONTROL_NAMES:
        _fail("five-control inventory changed")
    result = {
        name: _read_regular_at(
            control.descriptor, name, MAXIMUM_CONTROL_BYTES[name],
            expected_modes=frozenset({0o400}), label="control " + name,
        )
        for name in CONTROL_NAMES
    }
    if tuple(sorted(os.listdir(control.descriptor))) != CONTROL_NAMES:
        _fail("five-control inventory changed across readback")
    control.verify()
    return result


@dataclass(frozen=True)
class _LaunchArguments:
    operation: str
    driver_argv: tuple[str, ...]
    preformal_root: Path | None
    control_root: Path | None
    resource_root: Path | None
    activation_root: Path
    expected_anchor: str


_FORMAL_MODES = (
    "--probe-host-epoch", "--prepare-once", "--admit-launch-once",
    "--inspect-prepare", "--inspect-launch",
)


def _parse_cli(argv: Sequence[str]) -> _LaunchArguments:
    values = list(argv)
    if values and values[0] in {"activation", "formal"}:
        values.insert(0, str(SCRIPT_PATH))
    if not values or values[0] != str(SCRIPT_PATH):
        _fail("launcher argv[0] changed")
    tail = values[1:]
    if len(tail) == 11 and tail[0] == "activation" and tail[1::2] == [
        "--preformal-evidence-root", "--control-root",
        "--resource-evidence-root", "--activation-evidence-root",
        "--expected-preformal-plan-id",
    ]:
        preformal = _absolute_path(tail[2], "preformal evidence root")
        control = _absolute_path(tail[4], "control root")
        resource = _absolute_path(tail[6], "resource evidence root")
        activation = _absolute_path(tail[8], "activation evidence root")
        anchor = tail[10]
        if _HEX64.fullmatch(anchor) is None:
            _fail("expected preformal plan ID is not lowercase hex64")
        driver = (
            "--orchestrate-from-retained",
            "--preformal-evidence-root", str(preformal),
            "--expected-preformal-plan-id", anchor,
            "--control-root", str(control),
            "--resource-evidence-root", str(resource),
            "--activation-evidence-root", str(activation),
        )
        return _LaunchArguments(
            "activation", driver, preformal, control, resource, activation, anchor
        )
    if len(tail) in {6, 8} and tail[0] == "formal" and tail[1] == "--activation-evidence-root" and tail[3] == "--expected-activation-final-evidence-index-id" and tail[5] in _FORMAL_MODES:
        activation = _absolute_path(tail[2], "activation evidence root")
        anchor = tail[4]
        if _HEX64.fullmatch(anchor) is None:
            _fail("expected activation final evidence index ID is not lowercase hex64")
        mode = tail[5]
        driver_values = [
            "--activation-evidence-root", str(activation),
            "--expected-activation-final-evidence-index-id", anchor, mode,
        ]
        if len(tail) == 8:
            if mode not in {"--inspect-prepare", "--inspect-launch"} or tail[6] != "--inspection-ordinal":
                _fail("inspection ordinal is allowed only in an inspection mode")
            try:
                ordinal = int(tail[7], 10)
            except ValueError as error:
                raise V42ProductionLauncherError("inspection ordinal changed") from error
            if str(ordinal) != tail[7] or not 1 <= ordinal <= 4096:
                _fail("inspection ordinal must be canonical and bounded")
            driver_values.extend(("--inspection-ordinal", str(ordinal)))
        return _LaunchArguments(
            "formal", tuple(driver_values), None, None, None, activation, anchor
        )
    _fail("launcher requires one exact activation or formal CLI")


def _live_descriptors() -> list[int]:
    result: list[int] = []
    for name in os.listdir("/proc/self/fd"):
        if not name.isdigit():
            continue
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        result.append(descriptor)
    return sorted(result)


def _verify_runtime(args: _LaunchArguments | None = None) -> _LaunchArguments:
    parsed = _parse_cli(sys.argv) if args is None else args
    if (
        Path(__file__) != SCRIPT_PATH
        or not Path(__file__).is_absolute()
        or Path(__file__).resolve(strict=True) != SCRIPT_PATH
        or SCRIPT_PATH.is_symlink()
        or sys.executable != LOCAL_PYTHON
        or os.path.realpath(sys.executable) != LOCAL_PYTHON_REALPATH
        or os.path.realpath("/proc/self/exe") != LOCAL_PYTHON_REALPATH
        or tuple(sys.version_info[:3]) != LOCAL_PYTHON_VERSION
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
        or sys.gettrace() is not None
        or sys.getprofile() is not None
        or list(sys.path) != EXACT_PYTHON_PATH
        or dict(os.environ) != EXACT_ENVIRONMENT
        or list(sys.orig_argv) != [LOCAL_PYTHON, "-I", "-S", "-B", *sys.argv]
        or getattr(getattr(os, "__spec__", None), "origin", None)
        != "/usr/lib/python3.10/os.py"
    ):
        _fail("launcher requires its exact isolated Python runtime")
    if _live_descriptors() != [0, 1, 2]:
        _fail("launcher inherited an extra file descriptor")
    return parsed


def _load_frozen_primitives(repo: _DirectoryPin) -> ModuleType:
    raw = _read_relative_source(repo.descriptor, FROZEN_LAUNCHER_RELATIVE)
    if (
        len(raw) != FROZEN_LAUNCHER_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != FROZEN_LAUNCHER_SHA256
        or _git_blob_oid(raw) != FROZEN_LAUNCHER_GIT_BLOB
    ):
        _fail("frozen preformal launcher primitive bytes changed")
    name = "_acfqp_v42_frozen_preformal_launcher_primitives"
    if name in sys.modules:
        _fail("frozen preformal launcher primitive module repeated")
    module = ModuleType(name)
    module.__file__ = str(ROOT / FROZEN_LAUNCHER_RELATIVE)
    module.__package__ = None
    module.__cached__ = None
    module.__acfqp_verified_raw__ = raw
    module.__acfqp_exec_count__ = 0
    sys.modules[name] = module
    try:
        module.__acfqp_exec_count__ = 1
        exec(
            compile(raw, module.__file__, "exec", dont_inherit=True, optimize=0),
            module.__dict__, module.__dict__,
        )
    except BaseException:
        sys.modules.pop(name, None)
        raise
    required = {
        "_run_fixed_git_v42r1", "_preimport_manifests_v42r1",
        "GIT_VERSION_STDOUT",
    }
    if not required <= set(module.__dict__):
        _fail("frozen preformal launcher primitive surface changed")
    if (
        module.__acfqp_exec_count__ != 1
        or module.__acfqp_verified_raw__ != raw
        or sys.modules.pop(name, None) is not module
        or name in sys.modules
    ):
        _fail("frozen preformal launcher primitive execution changed")
    repo.verify()
    return module


def _fact_map(document: dict[str, Any], key: str, label: str) -> dict[str, dict[str, Any]]:
    rows = document.get(key)
    if type(rows) is not list or not rows:
        _fail(label + " fact inventory changed")
    result: dict[str, dict[str, Any]] = {}
    previous = ""
    for row in rows:
        if type(row) is not dict or set(row) != _FACT_FIELDS:
            _fail(label + " fact schema changed")
        relative = row.get("relative_path")
        parsed = PurePosixPath(relative) if type(relative) is str else None
        if (
            type(relative) is not str or relative <= previous
            or parsed is None or parsed.is_absolute() or parsed.as_posix() != relative
            or any(part in {"", ".", ".."} for part in parsed.parts)
            or row.get("git_mode") != "100644"
            or row.get("git_object_type") != "blob"
            or type(row.get("git_blob_oid")) is not str
            or _HEX40.fullmatch(row["git_blob_oid"]) is None
            or type(row.get("byte_count")) is not int
            or row["byte_count"] < 0
            or type(row.get("sha256")) is not str
            or _HEX64.fullmatch(row["sha256"]) is None
        ):
            _fail(label + " fact semantics or ordering changed")
        previous = relative
        result[relative] = dict(row)
    return result


def _git_anchor(run: Callable[..., bytes], revision: str) -> bytes:
    raw = run("-C", str(ROOT), "rev-parse", "--verify", revision)
    if len(raw) != 41 or not raw.endswith(b"\n"):
        _fail("selected Git anchor output changed")
    return raw[:-1]


def _selected_git_inventory(
    run: Callable[..., bytes], *, source_commit: str, source_tree: str,
    paths: tuple[str, ...], version_stdout: bytes,
) -> dict[str, tuple[str, str, str]]:
    if run("--version") != version_stdout:
        _fail("fixed Git version output changed")
    expected_commit = source_commit.encode("ascii")
    expected_tree = source_tree.encode("ascii")
    if (
        _git_anchor(run, "HEAD^{commit}") != expected_commit
        or _git_anchor(run, "HEAD^{tree}") != expected_tree
    ):
        _fail("selected HEAD or tree differs from the control capsule")
    listing = run(
        "-C", str(ROOT), "ls-tree", "-rz", "--full-tree", source_commit,
        "--", *paths,
    )
    if (
        _git_anchor(run, "HEAD^{commit}") != expected_commit
        or _git_anchor(run, "HEAD^{tree}") != expected_tree
    ):
        _fail("selected HEAD or tree changed across Git inventory")
    records = listing.split(b"\0")
    if not records or records[-1] != b"":
        _fail("selected Git inventory framing changed")
    result: dict[str, tuple[str, str, str]] = {}
    for record in records[:-1]:
        try:
            header, relative_raw = record.split(b"\t", 1)
            mode_raw, kind_raw, oid_raw = header.split(b" ")
            relative = relative_raw.decode("utf-8", errors="strict")
            values = (
                mode_raw.decode("ascii"), kind_raw.decode("ascii"),
                oid_raw.decode("ascii"),
            )
        except (UnicodeError, ValueError) as error:
            raise V42ProductionLauncherError("selected Git inventory malformed") from error
        if relative in result:
            _fail("selected Git inventory contains a duplicate")
        result[relative] = values
    if set(result) != set(paths):
        _fail("selected commit omitted an exact launcher TCB source")
    return result


def _verified_tcb(
    *, repo: _DirectoryPin, source: dict[str, Any], transport: dict[str, Any],
    primitives: ModuleType,
) -> tuple[MappingProxyType, MappingProxyType]:
    source_facts = _fact_map(source, "source_facts", "execution source")
    transport_facts = _fact_map(transport, "transport_facts", "transport")
    if any(not relative.endswith(".py") for relative in source_facts):
        _fail("execution source fact inventory is not source-only Python")
    for relative, fact in source_facts.items():
        if transport_facts.get(relative) != fact:
            _fail("execution source fact is not an exact transport subset")
    allowed = frozenset(source_facts) | TRANSPORT_ONLY_TCB_PATHS
    if not allowed <= set(transport_facts):
        _fail("transport manifest omitted a launcher or driver TCB source")
    if any(
        transport_facts[relative]["byte_count"] <= 0
        or transport_facts[relative]["byte_count"] > MAXIMUM_TCB_SOURCE_BYTES
        for relative in allowed
    ):
        _fail("allowed Python TCB source changed its bounded byte envelope")
    paths = tuple(sorted(allowed))
    run = primitives.__dict__["_run_fixed_git_v42r1"]
    if not callable(run):
        _fail("frozen pinned Git surface changed")
    selected = _selected_git_inventory(
        run,
        source_commit=source["source_commit"], source_tree=source["source_tree"],
        paths=paths, version_stdout=primitives.__dict__["GIT_VERSION_STDOUT"],
    )
    raws: dict[str, bytes] = {}
    for relative in paths:
        fact = transport_facts[relative]
        if selected[relative] != (
            fact["git_mode"], fact["git_object_type"], fact["git_blob_oid"],
        ):
            _fail("selected Git TCB fact differs from transport manifest")
        raw = _read_relative_source(repo.descriptor, relative)
        if (
            len(raw) != fact["byte_count"]
            or hashlib.sha256(raw).hexdigest() != fact["sha256"]
            or _git_blob_oid(raw) != fact["git_blob_oid"]
        ):
            _fail("live launcher TCB bytes differ from selected committed HEAD")
        raws[relative] = raw
    repo.verify()
    return MappingProxyType(raws), MappingProxyType(
        {relative: transport_facts[relative] for relative in paths}
    )


class _VerifiedBytesLoader(importlib.abc.Loader):
    def __init__(
        self, finder: "_VerifiedFinder", fullname: str, relative: str,
        raw: bytes, package: bool,
    ) -> None:
        self.finder = finder
        self.fullname = fullname
        self.relative = relative
        self.raw = raw
        self.package = package
        self.absolute = str(ROOT / relative)
        self.exec_count = 0

    def create_module(self, _spec: object) -> None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        if (
            self.exec_count != 0 or module.__spec__ is None
            or module.__spec__.loader is not self
            or module.__spec__.origin != self.absolute
        ):
            _fail("verified byte loader entry changed")
        self.exec_count = 1
        module.__file__ = self.absolute
        module.__cached__ = None
        module.__loader__ = self
        module.__package__ = (
            self.fullname if self.package else self.fullname.rpartition(".")[0]
        )
        exec(
            compile(self.raw, self.absolute, "exec", dont_inherit=True, optimize=0),
            module.__dict__, module.__dict__,
        )


class _VerifiedFinder(importlib.abc.MetaPathFinder):
    def __init__(
        self, raws: MappingProxyType, repo: _DirectoryPin, *, operation: str
    ) -> None:
        if operation not in EXPECTED_MODULES_BY_OPERATION:
            _fail("verified finder operation changed")
        self.raws = raws
        self.repo = repo
        self.operation = operation
        self.expected = EXPECTED_MODULES_BY_OPERATION[operation]
        self.loaders: dict[str, _VerifiedBytesLoader] = {}
        self.module_paths: dict[str, str] = {}

    @staticmethod
    def _candidates(fullname: str) -> tuple[tuple[str, bool], ...]:
        if fullname == "acfqp":
            return (("src/acfqp/__init__.py", True),)
        if fullname.startswith("acfqp."):
            stem = "src/" + fullname.replace(".", "/")
        elif fullname == "scripts":
            return (("scripts/__init__.py", True),)
        elif fullname.startswith("scripts."):
            stem = fullname.replace(".", "/")
        else:
            return ()
        return ((stem + ".py", False), (stem + "/__init__.py", True))

    def _shadow_exists(self, fullname: str) -> bool:
        if "." in fullname or "/" in fullname or "\x00" in fullname:
            return False
        for prefix in ("", "src/"):
            for suffix in (".py", ".pyc", "/__init__.py", "/__init__.pyc"):
                try:
                    os.stat(
                        prefix + fullname + suffix,
                        dir_fd=self.repo.descriptor,
                        follow_symlinks=False,
                    )
                except (FileNotFoundError, NotADirectoryError):
                    continue
                return True
        return False

    def find_spec(
        self, fullname: str, _path: object = None, _target: object = None,
    ) -> object:
        candidates = self._candidates(fullname)
        if not candidates:
            if _path is None and self._shadow_exists(fullname):
                raise ImportError("repository stdlib shadow rejected: " + fullname)
            return None
        expected_relative = self.expected.get(fullname)
        if expected_relative is None:
            raise ImportError("unexpected repository module rejected: " + fullname)
        selected = [(relative, package) for relative, package in candidates if relative in self.raws]
        if len(selected) != 1 or selected[0][0] != expected_relative:
            raise ImportError("unmanifested or ambiguous repository module: " + fullname)
        relative, package = selected[0]
        loader = self.loaders.get(fullname)
        if loader is None:
            loader = _VerifiedBytesLoader(self, fullname, relative, self.raws[relative], package)
            self.loaders[fullname] = loader
            self.module_paths[fullname] = relative
        spec = importlib.util.spec_from_loader(
            fullname, loader, origin=loader.absolute, is_package=package
        )
        if spec is None:
            _fail("verified module spec construction failed")
        spec.cached = None
        if package:
            spec.submodule_search_locations = []
        return spec

    def verify(self, *, operation: str) -> None:
        self.repo.verify()
        if (
            operation != self.operation
            or self.expected is not EXPECTED_MODULES_BY_OPERATION[operation]
            or not sys.meta_path
            or sys.meta_path[0] is not self
        ):
            _fail("verified repository finder changed")
        expected = dict(EXPECTED_MODULES_BY_OPERATION[operation])
        observed: dict[str, str] = {}
        for name, module in tuple(sys.modules.items()):
            file_name = getattr(module, "__file__", None)
            if type(file_name) is not str:
                continue
            try:
                relative = Path(file_name).relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if name == "__main__" and relative == SCRIPT_PATH.relative_to(ROOT).as_posix():
                if file_name != str(SCRIPT_PATH) or getattr(module, "__cached__", None) is not None:
                    _fail("direct launcher origin changed")
                continue
            loader = getattr(module, "__loader__", None)
            if (
                file_name.endswith((".pyc", ".pyo"))
                or type(loader) is not _VerifiedBytesLoader
                or loader.finder is not self
                or loader.exec_count != 1
                or loader.relative != relative
                or loader.raw is not self.raws[relative]
                or self.loaders.get(name) is not loader
                or getattr(getattr(module, "__spec__", None), "origin", None) != file_name
                or getattr(getattr(module, "__spec__", None), "loader", None) is not loader
                or getattr(module, "__cached__", None) is not None
            ):
                _fail("repository module escaped verified source bytes")
            observed[name] = relative
        if (
            observed != expected
            or self.module_paths != expected
            or set(self.loaders) != set(expected)
        ):
            _fail("loaded repository module inventory changed")


def _driver_name(operation: str) -> str:
    return (
        "scripts.run_v42_materialization_activation"
        if operation == "activation"
        else "scripts.run_v42_standard_2048_formal_transport_driver"
    )


def _load_driver(
    operation: str, raws: MappingProxyType, repo: _DirectoryPin,
) -> tuple[ModuleType, _VerifiedFinder, tuple[str, ...]]:
    if any(
        name == root or name.startswith(root + ".")
        for name in sys.modules for root in ("acfqp", "scripts")
    ):
        _fail("repository module loaded before verified finder")
    initial_path = tuple(sys.path)
    finder = _VerifiedFinder(raws, repo, operation=operation)
    sys.meta_path.insert(0, finder)
    name = _driver_name(operation)
    try:
        driver = importlib.import_module(name)
    finally:
        # The formal driver intentionally inserts these paths when imported as
        # a library.  The verified finder was already first and mediates that
        # window; no repository path survives it.
        sys.path[:] = list(initial_path)
    if tuple(sys.path) != initial_path:
        _fail("repository import changed the isolated Python path")
    finder.verify(operation=operation)
    if not callable(getattr(driver, "main", None)) or driver.main.__module__ != name:
        _fail("selected driver main surface changed")
    return driver, finder, initial_path


@dataclass
class _GuardSet:
    guards: dict[str, _RootGuard]

    def capture(self, path: Path, label: str, *, require_existing: bool) -> _RootGuard:
        key = str(path)
        existing = self.guards.get(key)
        if existing is not None:
            if require_existing and existing.descriptor is None:
                _fail(label + " must already exist")
            return existing
        guard = _RootGuard.capture(path, label, require_existing=require_existing)
        self.guards[key] = guard
        return guard

    def verify(self) -> None:
        for guard in self.guards.values():
            guard.verify()

    def close(self) -> None:
        for guard in reversed(tuple(self.guards.values())):
            guard.close()
        self.guards.clear()


def _read_evidence(guard: _RootGuard, name: str, label: str) -> bytes:
    guard.verify()
    if guard.descriptor is None:
        _fail(label + " root is absent")
    return _read_regular_at(
        guard.descriptor, name, MAXIMUM_EVIDENCE_BYTES,
        expected_modes=frozenset({0o400}), label=label,
    )


def _capture_inputs(
    args: _LaunchArguments, guards: _GuardSet,
) -> tuple[_RootGuard, dict[str, bytes], dict[str, bytes]]:
    activation = guards.capture(
        args.activation_root, "activation evidence root",
        require_existing=args.operation == "formal",
    )
    anchors: dict[str, bytes] = {}
    if args.operation == "activation":
        assert args.preformal_root is not None
        assert args.control_root is not None
        assert args.resource_root is not None
        preformal = guards.capture(
            args.preformal_root, "preformal evidence root", require_existing=True
        )
        control = guards.capture(args.control_root, "control root", require_existing=True)
        guards.capture(
            args.resource_root, "resource evidence root", require_existing=False
        )
        raw = _read_evidence(preformal, PREFORMAL_PLAN_NAME, "preformal upload plan")
        plan = _canonical_document(raw, "preformal upload plan")
        observed = _content_id(
            "acfqp:v42-remote-ordinal2:preformal-upload-plan",
            plan, "preformal_upload_plan_id", "preformal upload plan",
        )
        if observed != args.expected_anchor:
            _fail("preformal plan differs from caller anchor")
        anchors[PREFORMAL_PLAN_NAME] = raw
    else:
        roots_raw = _read_evidence(activation, ACTIVATION_ROOTS_NAME, "activation roots index")
        roots = _canonical_document(roots_raw, "activation roots index")
        if (
            roots.get("schema") != "acfqp.v42_materialization_activation_evidence_roots.v42r1"
            or roots.get("activation_evidence_root") != str(args.activation_root)
            or roots.get("expected_exact_control_names") != list(CONTROL_NAMES)
            or roots.get("controls_are_retained_by_stable_reference_not_hardlink_or_copy") is not True
            or roots.get("formal_loader_must_reverify_all_control_bytes_and_storage") is not True
        ):
            _fail("activation evidence roots index changed")
        paths: dict[str, Path] = {}
        for key in (
            "preformal_evidence_root", "resource_evidence_root", "control_evidence_root"
        ):
            value = roots.get(key)
            if type(value) is not str:
                _fail("activation indexed evidence root changed type")
            paths[key] = _absolute_path(value, "activation indexed " + key)
            guards.capture(paths[key], "activation indexed " + key, require_existing=True)
        control = guards.guards[str(paths["control_evidence_root"])]
        final_raw = _read_evidence(
            activation, ACTIVATION_FINAL_INDEX_NAME, "activation final evidence index"
        )
        final = _canonical_document(final_raw, "activation final evidence index")
        observed = _content_id(
            "acfqp:v42-remote-ordinal2:activation-final-evidence-index",
            final, "materialization_activation_final_evidence_index_id",
            "activation final evidence index",
        )
        if (
            observed != args.expected_anchor
            or final.get("formal_evidence_bundle_complete_under_bounded_successor_claim") is not True
        ):
            _fail("activation final evidence index differs from caller anchor")
        anchors[ACTIVATION_ROOTS_NAME] = roots_raw
        anchors[ACTIVATION_FINAL_INDEX_NAME] = final_raw
    controls = _read_controls(control)
    return control, controls, anchors


def _verify_pins_and_fds(
    *, repo: _DirectoryPin, guards: _GuardSet,
) -> None:
    repo.verify()
    guards.verify()
    expected = {0, 1, 2}
    expected.update(repo.descriptors)
    for guard in guards.guards.values():
        expected.update(guard.parent.descriptors)
        if guard.descriptor is not None:
            expected.add(guard.descriptor)
    if set(_live_descriptors()) != expected:
        _fail("launcher-owned descriptor inventory changed")
    for descriptor in expected - {0, 1, 2}:
        if not fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
            _fail("launcher pin lost close-on-exec")


def _invoke_driver_once(driver: ModuleType, argv: tuple[str, ...]) -> int:
    status = driver.main(list(argv))
    if type(status) is not int or not 0 <= status <= 255:
        _fail("driver main returned an invalid process status")
    return status


def main() -> int:
    args = _verify_runtime()
    repo = _DirectoryPin.open(ROOT, "repository root")
    guards = _GuardSet({})
    try:
        primitives = _load_frozen_primitives(repo)
        control, controls, anchors = _capture_inputs(args, guards)
        preimport = primitives.__dict__["_preimport_manifests_v42r1"]
        if not callable(preimport):
            _fail("frozen manifest verifier surface changed")
        source, transport, _local = preimport(dict(controls))
        initial_raws, initial_facts = _verified_tcb(
            repo=repo, source=source, transport=transport, primitives=primitives
        )
        driver, finder, initial_path = _load_driver(args.operation, initial_raws, repo)

        # Last pre-effect gate.  Every mutable pathname, held descriptor,
        # control byte, caller anchor, HEAD/tree fact, verified source byte,
        # importer, runtime hook and fd is replayed before the single call.
        if _read_controls(control) != controls:
            _fail("five-control capsule changed before driver dispatch")
        if args.operation == "activation":
            assert args.preformal_root is not None
            preformal = guards.guards[str(args.preformal_root)]
            if _read_evidence(preformal, PREFORMAL_PLAN_NAME, "preformal upload plan") != anchors[PREFORMAL_PLAN_NAME]:
                _fail("preformal caller anchor changed before dispatch")
        else:
            if _read_evidence(guards.guards[str(args.activation_root)], ACTIVATION_ROOTS_NAME, "activation roots index") != anchors[ACTIVATION_ROOTS_NAME]:
                _fail("activation roots index changed before dispatch")
            if _read_evidence(guards.guards[str(args.activation_root)], ACTIVATION_FINAL_INDEX_NAME, "activation final evidence index") != anchors[ACTIVATION_FINAL_INDEX_NAME]:
                _fail("activation final caller anchor changed before dispatch")
        final_raws, final_facts = _verified_tcb(
            repo=repo, source=source, transport=transport, primitives=primitives
        )
        if dict(final_raws) != dict(initial_raws) or dict(final_facts) != dict(initial_facts):
            _fail("launcher TCB changed before driver dispatch")
        if (
            list(sys.path) != list(initial_path)
            or dict(os.environ) != EXACT_ENVIRONMENT
            or sys.gettrace() is not None
            or sys.getprofile() is not None
            or list(sys.orig_argv) != [LOCAL_PYTHON, "-I", "-S", "-B", *sys.argv]
        ):
            _fail("launcher runtime changed before driver dispatch")
        finder.verify(operation=args.operation)
        _verify_pins_and_fds(repo=repo, guards=guards)
        return _invoke_driver_once(driver, args.driver_argv)
    finally:
        guards.close()
        repo.close()


if __name__ == "__main__":
    try:
        _status = main()
    except BaseException:
        os.write(2, b"acfqp v42 production launcher rejected\n")
        os._exit(72)
    else:
        os._exit(_status)
