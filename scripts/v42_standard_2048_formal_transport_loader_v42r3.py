#!/usr/bin/env python3
"""Source-only loader for every V42r3 formal transport role.

The exact bytes of this file are supplied to ``/usr/bin/python3 -I -S -B -c``.
SSH roles use a length-delimited stdin frame carrying the controller manifest,
successor authority, receiver, and canonical ingress.  Detached service roles
read those exact sources from the independently published V42r3 journal.  All
segments are authenticated before project code is compiled.  Legacy imports
are served only from the already-materialized execution source manifest.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.machinery
import json
import os
import re
import stat
import struct
import sys
import types
from typing import Any, NoReturn, Sequence


FRAME_MAGIC = b"ACFQP-V42R3-FORMAL-HOST-PROBE\x00"
FRAME_SECTION_COUNT = 4
PROBE_MODE = "--probe-host-epoch-v42r3"
PREPARE_MODE = "--prepare-once-v42r3"
INSPECT_PREPARE_MODE = "--inspect-prepare-v42r3"
ADMIT_MODE = "--admit-launch-v42r3"
INSPECT_LAUNCH_MODE = "--inspect-launch-v42r3"
SERVICE_BOOTSTRAP_MODE = "--formal-launch-service-bootstrap-v42r3"
SERVICE_WRAPPER_MODE = "--formal-launch-service-wrapper-v42r3"
SCIENTIFIC_PREPARE_FD_MODE = "--scientific-prepare-fd-v42r3"
SCIENTIFIC_LAUNCH_FD_MODE = "--scientific-launch-fd-v42r3"
SSH_MODES = frozenset(
    {
        PROBE_MODE,
        PREPARE_MODE,
        INSPECT_PREPARE_MODE,
        ADMIT_MODE,
        INSPECT_LAUNCH_MODE,
    }
)
SERVICE_MODES = frozenset({SERVICE_BOOTSTRAP_MODE, SERVICE_WRAPPER_MODE})
SCIENTIFIC_FD_MODES = frozenset(
    {SCIENTIFIC_PREPARE_FD_MODE, SCIENTIFIC_LAUNCH_FD_MODE}
)
ALL_MODES = SSH_MODES | SERVICE_MODES | SCIENTIFIC_FD_MODES
# Compatibility name retained for the phase-1 launcher/tests.
MODE = PROBE_MODE
SCHEMA_VERSION = "42.3.0"
CONTROLLER_SOURCE_MANIFEST_SCHEMA = (
    "acfqp.v42_formal_transport_successor_controller_source_manifest.v42r3"
)
LOADER_RELATIVE = "scripts/v42_standard_2048_formal_transport_loader_v42r3.py"
RECEIVER_RELATIVE = (
    "scripts/v42_standard_2048_formal_transport_receiver_v42r3.py"
)
AUTHORITY_RELATIVE = (
    "src/acfqp/"
    "construction_k7_standard_2048_formal_transport_successor_v42r3.py"
)
AUTHORITY_MODULE = (
    "acfqp.construction_k7_standard_2048_formal_transport_successor_v42r3"
)
FIXED_REMOTE_ROOT = "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2"
FIXED_SOURCE_ROOT = FIXED_REMOTE_ROOT + "/source"
SOURCE_MANIFEST_PATH = FIXED_REMOTE_ROOT + "/EXECUTION_SOURCE_MANIFEST.json"
REMOTE_V42R3_JOURNAL_ROOT = (
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-remote-ordinal2-formal-transport-v42r3r2"
)
REMOTE_CONTROLLER_NAME = "CONTROLLER_SOURCE_MANIFEST.json"
REMOTE_LOADER_NAME = "FORMAL_TRANSPORT_LOADER.py"
REMOTE_AUTHORITY_NAME = "FORMAL_TRANSPORT_AUTHORITY.py"
REMOTE_RECEIVER_NAME = "FORMAL_TRANSPORT_RECEIVER.py"
REMOTE_PLAN_NAME = "FORMAL_TRANSPORT_PLAN.json"
MAX_CONTROLLER_BYTES = 8 * 1024**2
MAX_AUTHORITY_BYTES = 4 * 1024**2
MAX_RECEIVER_BYTES = 4 * 1024**2
MAX_INGRESS_BYTES = 8 * 1024**2
MAX_LEGACY_SOURCE_BYTES = 8 * 1024**2
MAX_LOADER_FAILURE_DIAGNOSTIC_BYTES = 4096
LOADER_FAILURE_MESSAGE_PREFIX_BYTES = 256
LOADER_FAILURE_TYPE_PREFIX_BYTES = 64
LOADER_FAILURE_FILENAME_PREFIX_BYTES = 64
LOADER_FAILURE_FUNCTION_PREFIX_BYTES = 32
LOADER_FAILURE_TRACEBACK_FRAMES = 6
LOADER_FAILURE_TRACEBACK_SCAN_FRAMES = 128
LOADER_FAILURE_MESSAGE_SCAN_CHARACTERS = 4096
LOADER_FAILURE_DIAGNOSTIC_SCHEMA = (
    "acfqp.v42r3r2_formal_loader_failure_diagnostic"
)
LOADER_FAILURE_DIAGNOSTIC_VERSION = "42.3.2"
GENERIC_LOADER_FAILURE = (
    b'{"diagnostic_builder_succeeded":false,'
    b'"diagnostic_scope":"DIAGNOSTIC_ONLY_NOT_FORMAL_RECEIPT",'
    b'"exception_module":{"prefix_byte_count":13,'
    b'"prefix_hex":"3c756e617661696c61626c653e","truncated":false},'
    b'"exception_qualname":{"prefix_byte_count":13,'
    b'"prefix_hex":"3c756e617661696c61626c653e","truncated":false},'
    b'"message":{"character_count":13,"prefix_byte_count":13,'
    b'"prefix_hex":"3c756e617661696c61626c653e",'
    b'"prefix_truncated":false,"scan_complete":true,'
    b'"scanned_byte_count":13,"scanned_character_count":13,'
    b'"scanned_sha256":"2aa53a73f8ccc3f2fc7dce145503ec3c9e4dad8db3adcec2471c9745a74ec11f"},'
    b'"schema":"acfqp.v42r3r2_formal_loader_failure_diagnostic",'
    b'"schema_version":"42.3.2","traceback_frames":[],'
    b'"traceback_frames_truncated":false,'
    b'"traceback_scan_truncated":false,'
    b'"traceback_scanned_frame_count":0}\n'
)
_CAPS = (
    MAX_CONTROLLER_BYTES,
    MAX_AUTHORITY_BYTES,
    MAX_RECEIVER_BYTES,
    MAX_INGRESS_BYTES,
)
_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_EXPECTED_ENVIRONMENT = {"LC_CTYPE": "C.UTF-8"}
_EXPECTED_SERVICE_ENVIRONMENT = {
    "HOME": "/home/erzhu419",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "LOGNAME": "erzhu419",
    "PATH": "/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONCOERCECLOCALE": "0",
    "USER": "erzhu419",
}
_EXPECTED_PYTHON_PATH = [
    "/usr/lib/python312.zip",
    "/usr/lib/python3.12",
    "/usr/lib/python3.12/lib-dynload",
]
PYTHON_INVOCATION_PATH = "/usr/bin/python3"
PYTHON_INVOCATION_TARGET = "python3.12"
PYTHON_REAL_PATH = "/usr/bin/python3.12"
PYTHON_PROC_EXE_PATH = "/proc/self/exe"
PYTHON_REAL_BYTE_COUNT = 8_020_928
PYTHON_REAL_SHA256 = (
    "1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118"
)
PYTHON_TCB_UID = 0
PYTHON_TCB_GID = 0


class V42FormalProbeLoaderError(RuntimeError):
    """The source-only formal probe loader rejected its ingress."""


def _fail(message: str) -> NoReturn:
    raise V42FormalProbeLoaderError(message)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")


def _diagnostic_exact_text(value: object) -> str:
    return value if type(value) is str else "<unavailable>"


def _diagnostic_text_prefix(value: object, cap: int) -> dict[str, object]:
    text = _diagnostic_exact_text(value)
    sampled = text[: cap + 1]
    sampled_raw = sampled.encode("utf-8", errors="backslashreplace")
    prefix = sampled_raw[:cap]
    return {
        "prefix_byte_count": len(prefix),
        "prefix_hex": prefix.hex(),
        "truncated": len(text) > len(sampled) or len(sampled_raw) > cap,
    }


def _diagnostic_exception_message(error: BaseException) -> str:
    try:
        arguments = object.__getattribute__(error, "args")
    except BaseException:
        return "<unavailable>"
    if type(arguments) is not tuple:
        return "<unavailable>"
    if not arguments:
        return ""
    if len(arguments) == 1 and type(arguments[0]) is str:
        return arguments[0]
    return "<non-string exception message unavailable>"


def _diagnostic_message(value: object) -> dict[str, object]:
    text = _diagnostic_exact_text(value)
    scanned_character_count = min(
        len(text), LOADER_FAILURE_MESSAGE_SCAN_CHARACTERS
    )
    scanned = text[:scanned_character_count]
    scanned_raw = scanned.encode("utf-8", errors="backslashreplace")
    prefix = scanned_raw[:LOADER_FAILURE_MESSAGE_PREFIX_BYTES]
    scan_complete = scanned_character_count == len(text)
    return {
        "character_count": len(text),
        "scan_complete": scan_complete,
        "scanned_character_count": scanned_character_count,
        "scanned_byte_count": len(scanned_raw),
        "scanned_sha256": hashlib.sha256(scanned_raw).hexdigest(),
        "prefix_byte_count": len(prefix),
        "prefix_hex": prefix.hex(),
        "prefix_truncated": (
            not scan_complete
            or len(scanned_raw) > LOADER_FAILURE_MESSAGE_PREFIX_BYTES
        ),
    }


def _loader_failure_diagnostic(error: BaseException) -> bytes:
    error_type = type(error)
    try:
        module = type.__getattribute__(error_type, "__module__")
        qualname = type.__getattribute__(error_type, "__qualname__")
    except BaseException:
        module = qualname = "<unavailable>"
    traceback_frames: list[dict[str, object]] = []
    traceback_scanned_frame_count = 0
    try:
        current = object.__getattribute__(error, "__traceback__")
    except BaseException:
        current = None
    while (
        current is not None
        and traceback_scanned_frame_count < LOADER_FAILURE_TRACEBACK_SCAN_FRAMES
    ):
        traceback_scanned_frame_count += 1
        code = current.tb_frame.f_code
        line_number = current.tb_lineno
        if type(line_number) is not int or not 0 <= line_number < 2**31:
            line_number = 0
        traceback_frames.append(
            {
                "filename": _diagnostic_text_prefix(
                    code.co_filename,
                    LOADER_FAILURE_FILENAME_PREFIX_BYTES,
                ),
                "function": _diagnostic_text_prefix(
                    code.co_name,
                    LOADER_FAILURE_FUNCTION_PREFIX_BYTES,
                ),
                "line_number": line_number,
            }
        )
        if len(traceback_frames) > LOADER_FAILURE_TRACEBACK_FRAMES:
            del traceback_frames[0]
        current = current.tb_next
    traceback_scan_truncated = current is not None
    document = {
        "schema": LOADER_FAILURE_DIAGNOSTIC_SCHEMA,
        "schema_version": LOADER_FAILURE_DIAGNOSTIC_VERSION,
        "diagnostic_scope": "DIAGNOSTIC_ONLY_NOT_FORMAL_RECEIPT",
        "diagnostic_builder_succeeded": True,
        "exception_module": _diagnostic_text_prefix(
            module, LOADER_FAILURE_TYPE_PREFIX_BYTES
        ),
        "exception_qualname": _diagnostic_text_prefix(
            qualname, LOADER_FAILURE_TYPE_PREFIX_BYTES
        ),
        "message": _diagnostic_message(_diagnostic_exception_message(error)),
        "traceback_scanned_frame_count": traceback_scanned_frame_count,
        "traceback_scan_truncated": traceback_scan_truncated,
        "traceback_frames": traceback_frames,
        "traceback_frames_truncated": (
            traceback_scan_truncated
            or traceback_scanned_frame_count > len(traceback_frames)
        ),
    }
    raw = _canonical_bytes(document) + b"\n"
    if len(raw) > MAX_LOADER_FAILURE_DIAGNOSTIC_BYTES:
        raise V42FormalProbeLoaderError("loader failure diagnostic exceeded cap")
    return raw


def _loader_failure_stderr(error: BaseException) -> bytes:
    try:
        return _loader_failure_diagnostic(error)
    except BaseException:
        return GENERIC_LOADER_FAILURE


def _unique_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate JSON key")
        result[key] = value
    return result


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                V42FormalProbeLoaderError("nonfinite JSON token: " + token)
            ),
        )
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42FormalProbeLoaderError(label + " is not canonical JSON") from error
    if type(value) is not dict or _canonical_bytes(value) != raw:
        _fail(label + " canonical bytes changed")
    return value


def _exact_count(value: str, cap: int, label: str) -> int:
    if not value or value.startswith("+"):
        _fail(label + " changed")
    try:
        result = int(value)
    except ValueError as error:
        raise V42FormalProbeLoaderError(label + " changed") from error
    if value != str(result) or not 0 < result <= cap:
        _fail(label + " changed")
    return result


def _artifact(relative_path: str, raw: bytes) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "git_mode": "100644",
        "git_object_type": "blob",
        "git_blob_oid": hashlib.sha1(  # noqa: S324 - Git object identity
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest(),
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_probe_frame_v42r3(
    *, controller_manifest_raw: bytes, authority_raw: bytes,
    receiver_raw: bytes, ingress_raw: bytes,
) -> bytes:
    """Build the only accepted four-section stdin frame."""

    sections = (
        controller_manifest_raw,
        authority_raw,
        receiver_raw,
        ingress_raw,
    )
    for raw, cap in zip(sections, _CAPS, strict=True):
        if type(raw) is not bytes or not 0 < len(raw) <= cap:
            _fail("probe frame section changed type or exceeded cap")
    return (
        FRAME_MAGIC
        + struct.pack(">QQQQ", *(len(raw) for raw in sections))
        + b"".join(sections)
    )


def _decode_probe_frame_bytes(raw: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    header_count = len(FRAME_MAGIC) + 8 * FRAME_SECTION_COUNT
    if type(raw) is not bytes or len(raw) < header_count:
        _fail("probe frame header ended early")
    if raw[: len(FRAME_MAGIC)] != FRAME_MAGIC:
        _fail("probe frame magic changed")
    lengths = struct.unpack(">QQQQ", raw[len(FRAME_MAGIC) : header_count])
    if any(count <= 0 or count > cap for count, cap in zip(lengths, _CAPS, strict=True)):
        _fail("probe frame length changed or exceeded cap")
    expected = header_count + sum(lengths)
    if len(raw) != expected:
        _fail("probe frame is truncated or has trailing bytes")
    cursor = header_count
    result: list[bytes] = []
    for count in lengths:
        result.append(raw[cursor : cursor + count])
        cursor += count
    return result[0], result[1], result[2], result[3]


def _read_exact(descriptor: int, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = os.read(descriptor, min(remaining, 1024 * 1024))
        if not chunk:
            _fail("probe frame ended early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_probe_frame() -> tuple[bytes, bytes, bytes, bytes]:
    header = _read_exact(0, len(FRAME_MAGIC) + 8 * FRAME_SECTION_COUNT)
    if header[: len(FRAME_MAGIC)] != FRAME_MAGIC:
        _fail("probe frame magic changed")
    lengths = struct.unpack(">QQQQ", header[len(FRAME_MAGIC) :])
    if any(count <= 0 or count > cap for count, cap in zip(lengths, _CAPS, strict=True)):
        _fail("probe frame length changed or exceeded cap")
    result = tuple(_read_exact(0, count) for count in lengths)
    if os.read(0, 1):
        _fail("probe frame retained trailing bytes")
    return result  # type: ignore[return-value]


def _live_descriptors() -> list[int]:
    result: list[int] = []
    for name in os.listdir("/proc/self/fd"):
        if not name.isdigit():
            _fail("probe loader descriptor name changed")
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError as error:
            # CPython's directory iterator closes its one transient descriptor
            # before listdir returns.  No still-live descriptor is ignored.
            if error.errno != 9:
                raise
            continue
        result.append(descriptor)
    return sorted(result)


def _verify_python_tcb() -> None:
    invocation_before = os.lstat(PYTHON_INVOCATION_PATH)
    target_before = os.readlink(PYTHON_INVOCATION_PATH)
    invocation_after = os.lstat(PYTHON_INVOCATION_PATH)
    if (
        _stable_tuple(invocation_before) != _stable_tuple(invocation_after)
        or not stat.S_ISLNK(invocation_before.st_mode)
        or stat.S_IMODE(invocation_before.st_mode) != 0o777
        or invocation_before.st_uid != PYTHON_TCB_UID
        or invocation_before.st_gid != PYTHON_TCB_GID
        or invocation_before.st_nlink != 1
        or target_before != PYTHON_INVOCATION_TARGET
        or invocation_before.st_size != len(PYTHON_INVOCATION_TARGET)
    ):
        _fail("formal probe Python invocation symlink changed")
    descriptor = os.open(
        PYTHON_REAL_PATH,
        os.O_RDONLY | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        named_before = os.lstat(PYTHON_REAL_PATH)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o755
            or before.st_uid != PYTHON_TCB_UID
            or before.st_gid != PYTHON_TCB_GID
            or before.st_nlink != 1
            or before.st_size != PYTHON_REAL_BYTE_COUNT
            or (before.st_dev, before.st_ino)
            != (named_before.st_dev, named_before.st_ino)
        ):
            _fail("formal probe Python executable identity changed")
        digest = hashlib.sha256()
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("formal probe Python executable ended early")
            digest.update(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("formal probe Python executable grew during read")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    named_after = os.lstat(PYTHON_REAL_PATH)
    if (
        digest.hexdigest() != PYTHON_REAL_SHA256
        or _stable_tuple(before) != _stable_tuple(after)
        or _stable_tuple(after) != _stable_tuple(named_after)
        or os.stat(PYTHON_PROC_EXE_PATH).st_dev != after.st_dev
        or os.stat(PYTHON_PROC_EXE_PATH).st_ino != after.st_ino
    ):
        _fail("formal probe Python executable bytes or live join changed")


def _stable_tuple(observed: os.stat_result) -> tuple[int, ...]:
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_uid,
        observed.st_gid,
        observed.st_nlink,
        observed.st_size,
        observed.st_mtime_ns,
        observed.st_ctime_ns,
    )


def _stdio_is_exact_null() -> bool:
    null = os.stat("/dev/null", follow_symlinks=False)
    for descriptor in (0, 1, 2):
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISCHR(observed.st_mode)
            or observed.st_rdev != null.st_rdev
            or os.readlink("/proc/self/fd/" + str(descriptor)) != "/dev/null"
            or os.isatty(descriptor)
        ):
            return False
    return True


def _verify_runtime(
    source: str, mode: str = PROBE_MODE, expected_extra_fd: int | None = None,
) -> None:
    environment = dict(os.environ)
    if mode in SSH_MODES or mode == SCIENTIFIC_PREPARE_FD_MODE:
        environment_exact = environment == _EXPECTED_ENVIRONMENT
        stdio_exact = not any(os.isatty(descriptor) for descriptor in (0, 1, 2))
    elif mode == SERVICE_BOOTSTRAP_MODE:
        invocation = environment.get("INVOCATION_ID")
        environment_exact = (
            type(invocation) is str
            and re.fullmatch(r"[0-9a-f]{32}", invocation) is not None
        )
        stdio_exact = _stdio_is_exact_null()
    elif mode in {SERVICE_WRAPPER_MODE, SCIENTIFIC_LAUNCH_FD_MODE}:
        environment_exact = environment == _EXPECTED_SERVICE_ENVIRONMENT
        stdio_exact = _stdio_is_exact_null()
    else:
        _fail("formal transport loader mode changed")
    if (
        sys.executable != "/usr/bin/python3"
        or os.path.realpath(sys.executable) != "/usr/bin/python3.12"
        or os.path.realpath(PYTHON_PROC_EXE_PATH) != "/usr/bin/python3.12"
        or tuple(sys.version_info[:3]) != (3, 12, 3)
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
        or sys.gettrace() is not None
        or sys.getprofile() is not None
        or getattr(getattr(os, "__spec__", None), "origin", None) != "frozen"
        or sys.path != _EXPECTED_PYTHON_PATH
        or not environment_exact
        or sys.orig_argv != [
            "/usr/bin/python3", "-I", "-S", "-B", "-c", source,
            *sys.argv[1:],
        ]
        or _live_descriptors()
        != sorted(
            [0, 1, 2]
            if expected_extra_fd is None
            else [0, 1, 2, expected_extra_fd]
        )
        or not stdio_exact
    ):
        _fail("formal probe loader isolated Python invocation changed")
    _verify_python_tcb()


def _stable_regular(path: str, cap: int, mode: int) -> bytes:
    named = os.lstat(path)
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_uid != 1000
            or before.st_gid != 1000
            or before.st_nlink != 1
            or not 0 < before.st_size <= cap
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("fixed source storage changed: " + path)
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("fixed source ended early: " + path)
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("fixed source grew during read: " + path)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = os.lstat(path)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(final, field)
        for field in fields
    ):
        _fail("fixed source changed while read: " + path)
    return b"".join(chunks)


def _legacy_source_facts(expected_manifest_id: str) -> dict[str, dict[str, Any]]:
    raw = _stable_regular(SOURCE_MANIFEST_PATH, 64 * 1024**2, 0o400)
    manifest = _canonical_document(raw, "fixed execution source manifest")
    payload = dict(manifest)
    identifier = payload.pop("source_manifest_id", None)
    if (
        identifier != expected_manifest_id
        or _HEX64.fullmatch(expected_manifest_id) is None
        or hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:source-manifest\0"
            + _canonical_bytes(payload)
        ).hexdigest() != identifier
    ):
        _fail("fixed execution source manifest identity changed")
    rows = manifest.get("source_facts")
    if type(rows) is not list or not rows:
        _fail("fixed execution source fact inventory changed")
    facts: dict[str, dict[str, Any]] = {}
    for row in rows:
        if type(row) is not dict:
            _fail("fixed execution source fact changed type")
        relative = row.get("relative_path")
        if (
            type(relative) is not str
            or relative.startswith("/")
            or ".." in relative.split("/")
            or not relative.endswith(".py")
            or relative in facts
            or type(row.get("byte_count")) is not int
            or not 0 < row["byte_count"] <= MAX_LEGACY_SOURCE_BYTES
            or _HEX64.fullmatch(str(row.get("sha256"))) is None
            or _HEX40.fullmatch(str(row.get("git_blob_oid"))) is None
        ):
            _fail("fixed execution source fact changed")
        facts[relative] = row
    return facts


def _controller_facts(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (
        document.get("schema") != CONTROLLER_SOURCE_MANIFEST_SCHEMA
        or document.get("schema_version") != SCHEMA_VERSION
    ):
        _fail("controller source manifest schema or version changed")
    rows = document.get("source_facts")
    if type(rows) is not list:
        _fail("controller source manifest fact inventory changed")
    result: dict[str, dict[str, Any]] = {}
    required_fields = {
        "relative_path", "git_mode", "git_object_type", "git_blob_oid",
        "byte_count", "sha256",
    }
    for row in rows:
        if (
            type(row) is not dict
            or set(row) != required_fields
            or row.get("git_mode") != "100644"
            or row.get("git_object_type") != "blob"
        ):
            _fail("controller source fact changed")
        relative = row.get("relative_path")
        if (
            type(relative) is not str
            or relative.startswith("/")
            or ".." in relative.split("/")
            or relative in result
            or _HEX40.fullmatch(str(row.get("git_blob_oid"))) is None
            or _HEX64.fullmatch(str(row.get("sha256"))) is None
            or type(row.get("byte_count")) is not int
            or row["byte_count"] <= 0
        ):
            _fail("controller source fact identity changed")
        result[relative] = row
    for relative in (LOADER_RELATIVE, AUTHORITY_RELATIVE, RECEIVER_RELATIVE):
        if relative not in result:
            _fail("controller source manifest omitted probe TCB")
    return result


def _verify_raw_fact(
    *, raw: bytes, relative: str, fact: dict[str, Any],
    expected_sha256: str, expected_count: int,
) -> None:
    expected = _artifact(relative, raw)
    if (
        fact != expected
        or expected["sha256"] != expected_sha256
        or expected["byte_count"] != expected_count
    ):
        _fail("transported probe source artifact changed: " + relative)


class _VerifiedSourceLoader:
    def __init__(
        self, *, fullname: str, relative: str, raw_reader: object,
        origin: str, package: bool,
    ) -> None:
        self.fullname = fullname
        self.relative = relative
        self.raw_reader = raw_reader
        self.origin = origin
        self.package = package
        self.exec_count = 0
        self.spec: importlib.machinery.ModuleSpec | None = None
        self.module: types.ModuleType | None = None

    def create_module(self, spec: object) -> None:
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        if self.exec_count != 0:
            _fail("verified repository module executed more than once")
        self.exec_count = 1
        self.module = module
        raw = self.raw_reader(self.relative)  # type: ignore[operator]
        namespace = vars(module)
        namespace["__file__"] = self.origin
        namespace["__cached__"] = None
        exec(
            compile(raw, self.origin, "exec", flags=0, dont_inherit=True, optimize=0),
            namespace,
            namespace,
        )

    def verify_module(self, module: types.ModuleType) -> None:
        spec = getattr(module, "__spec__", None)
        expected_package = (
            self.fullname if self.package else self.fullname.rpartition(".")[0]
        )
        path = getattr(module, "__path__", None)
        search_locations = getattr(spec, "submodule_search_locations", None)
        if (
            self.spec is None
            or type(module) is not types.ModuleType
            or module is not self.module
            or module.__name__ != self.fullname
            or getattr(module, "__file__", None) != self.origin
            or getattr(module, "__package__", None) != expected_package
            or getattr(module, "__loader__", None) is not self
            or spec is not self.spec
            or getattr(spec, "name", None) != self.fullname
            or getattr(spec, "loader", None) is not self
            or getattr(spec, "origin", None) != self.origin
            or search_locations != ([] if self.package else None)
            or self.package
            and (
                type(search_locations) is not list
                or path is not search_locations
                or path != []
            )
            or (not self.package and hasattr(module, "__path__"))
            or getattr(module, "__cached__", None) is not None
            or self.exec_count != 1
        ):
            _fail("verified repository module metadata changed: " + self.fullname)


def _project_module_names() -> frozenset[str]:
    return frozenset(
        name
        for name in sys.modules
        if name == "acfqp" or name.startswith("acfqp.")
        or name == "scripts" or name.startswith("scripts.")
    )


class _VerifiedSourceFinder:
    def __init__(
        self, *, legacy_facts: dict[str, dict[str, Any]],
        injected: dict[str, tuple[str, bytes]],
    ) -> None:
        self.legacy_facts = legacy_facts
        self.injected = injected
        self.created: dict[str, _VerifiedSourceLoader] = {}
        self.cache: dict[str, bytes] = {}
        self.baseline_project_modules = _project_module_names()

    def _legacy_raw(self, relative: str) -> bytes:
        if relative in self.cache:
            return self.cache[relative]
        fact = self.legacy_facts[relative]
        raw = _stable_regular(
            os.path.join(FIXED_SOURCE_ROOT, relative),
            MAX_LEGACY_SOURCE_BYTES,
            0o444,
        )
        if _artifact(relative, raw) != {
            key: fact[key]
            for key in (
                "relative_path", "git_mode", "git_object_type", "git_blob_oid",
                "byte_count", "sha256",
            )
        }:
            _fail("manifested legacy dependency changed: " + relative)
        self.cache[relative] = raw
        return raw

    def _raw(self, relative: str) -> bytes:
        for injected_relative, raw in self.injected.values():
            if relative == injected_relative:
                return raw
        return self._legacy_raw(relative)

    def find_spec(
        self, fullname: str, path: object = None, target: object = None,
    ) -> importlib.machinery.ModuleSpec | None:
        del target
        if not sys.meta_path or sys.meta_path[0] is not self:
            _fail("verified repository finder lost first meta-path authority")
        if fullname in self.injected:
            relative, _raw = self.injected[fullname]
            package = False
            origin = "<acfqp-v42r3-injected:/" + relative + ">"
        elif fullname == "acfqp" or fullname.startswith("acfqp."):
            stem = "src/" + fullname.replace(".", "/")
            module_relative = stem + ".py"
            package_relative = stem + "/__init__.py"
            if module_relative in self.legacy_facts:
                relative, package = module_relative, False
            elif package_relative in self.legacy_facts:
                relative, package = package_relative, True
            else:
                raise ImportError("unmanifested legacy repository module: " + fullname)
            origin = os.path.join(FIXED_SOURCE_ROOT, relative)
        elif fullname == "scripts" or fullname.startswith("scripts."):
            stem = fullname.replace(".", "/")
            module_relative = stem + ".py"
            package_relative = stem + "/__init__.py"
            if module_relative in self.legacy_facts:
                relative, package = module_relative, False
            elif package_relative in self.legacy_facts:
                relative, package = package_relative, True
            else:
                raise ImportError("unmanifested legacy repository module: " + fullname)
            origin = os.path.join(FIXED_SOURCE_ROOT, relative)
        else:
            if path is None:
                stem = fullname.replace(".", "/")
                for root in (FIXED_SOURCE_ROOT, FIXED_SOURCE_ROOT + "/src"):
                    candidates = (
                        stem + ".py", stem + ".pyc", stem + "/__init__.py",
                        stem + "/__init__.pyc",
                    )
                    if any(os.path.lexists(os.path.join(root, item)) for item in candidates):
                        raise ImportError("repository stdlib shadow rejected: " + fullname)
            return None
        if fullname in self.created:
            raise ImportError("verified repository module loader repeated: " + fullname)
        loader = _VerifiedSourceLoader(
            fullname=fullname, relative=relative,
            raw_reader=self._raw,
            origin=origin,
            package=package,
        )
        self.created[fullname] = loader
        spec = importlib.machinery.ModuleSpec(
            fullname, loader, origin=origin, is_package=package
        )
        if package:
            # The finder resolves every manifested child itself.  Exposing the
            # live package directory here would let another finder traverse it.
            spec.submodule_search_locations = []
        loader.spec = spec
        return spec

    def verify_loaded(self) -> None:
        if (
            not sys.meta_path
            or sys.meta_path[0] is not self
            or sum(item is self for item in sys.meta_path) != 1
            or _project_module_names()
            != self.baseline_project_modules | frozenset(self.created)
        ):
            _fail("verified repository importer or module inventory changed")
        for name, loader in self.created.items():
            module = sys.modules.get(name)
            if module is None:
                _fail("verified repository module escaped source bytes: " + name)
            loader.verify_module(module)


def _service_sections(source_raw: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    root = REMOTE_V42R3_JOURNAL_ROOT
    observed = os.lstat(root)
    if (
        not stat.S_ISDIR(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o700
        or observed.st_uid != 1000
        or observed.st_gid != 1000
        or os.path.realpath(root) != root
    ):
        _fail("formal successor service journal root changed")
    loader_raw = _stable_regular(
        os.path.join(root, REMOTE_LOADER_NAME), MAX_AUTHORITY_BYTES, 0o400
    )
    if loader_raw != source_raw:
        _fail("formal successor service loader differs from journal")
    return (
        _stable_regular(
            os.path.join(root, REMOTE_CONTROLLER_NAME), MAX_CONTROLLER_BYTES, 0o400
        ),
        _stable_regular(
            os.path.join(root, REMOTE_AUTHORITY_NAME), MAX_AUTHORITY_BYTES, 0o400
        ),
        _stable_regular(
            os.path.join(root, REMOTE_RECEIVER_NAME), MAX_RECEIVER_BYTES, 0o400
        ),
        _stable_regular(
            os.path.join(root, REMOTE_PLAN_NAME), MAX_INGRESS_BYTES, 0o400
        ),
    )


def _plan_from_ingress(mode: str, ingress: dict[str, Any]) -> dict[str, Any]:
    if mode in {PROBE_MODE, SERVICE_BOOTSTRAP_MODE, SERVICE_WRAPPER_MODE}:
        plan = ingress
    else:
        plan = ingress.get("formal_transport_plan")
        if type(plan) is not dict:
            _fail("formal transport ingress omitted its plan")
    return plan


def _execute_authenticated_sources(
    *, mode: str, controller: dict[str, Any], controller_facts: dict[str, dict[str, Any]],
    loader_raw: bytes, authority_raw: bytes, receiver_raw: bytes, ingress_raw: bytes,
    expected_plan_id: str, expected_legacy_source_manifest_id: str,
    attempt_id: str | None, runtime_invocation_id: str | None,
    runtime_control_group: str | None,
) -> int:
    legacy_facts = _legacy_source_facts(expected_legacy_source_manifest_id)
    if any(
        name == "acfqp" or name.startswith("acfqp.")
        or name == "scripts" or name.startswith("scripts.")
        for name in sys.modules
    ):
        _fail("repository module loaded before verified importer")
    finder = _VerifiedSourceFinder(
        legacy_facts=legacy_facts,
        injected={AUTHORITY_MODULE: (AUTHORITY_RELATIVE, authority_raw)},
    )
    sys.meta_path.insert(0, finder)
    sys.dont_write_bytecode = True
    finder.verify_loaded()
    authority_module = importlib.import_module(AUTHORITY_MODULE)
    verifier = getattr(
        authority_module, "verify_controller_source_manifest_v42r3", None
    )
    if not callable(verifier):
        _fail("successor authority controller verifier changed")
    verified_controller = verifier(controller)
    if verified_controller != controller:
        _fail("successor authority changed controller source manifest")
    receiver_origin = "<acfqp-v42r3-injected:/" + RECEIVER_RELATIVE + ">"
    receiver_namespace: dict[str, Any] = {
        "__builtins__": __builtins__,
        "__name__": "_acfqp_v42r3_formal_transport_receiver",
        "__file__": receiver_origin,
        "__package__": None,
        "__cached__": None,
    }
    exec(
        compile(
            receiver_raw, receiver_origin, "exec", flags=0,
            dont_inherit=True, optimize=0,
        ),
        receiver_namespace,
        receiver_namespace,
    )
    receiver_main = receiver_namespace.get("main_v42r3")
    if not callable(receiver_main):
        _fail("formal transport receiver entry point changed")
    # Every import performed while defining the receiver is already source
    # verified before any receiver mode can mutate remote state.
    finder.verify_loaded()
    status = receiver_main(
        mode=mode,
        ingress_raw=ingress_raw,
        loader_source_raw=loader_raw,
        authority_source_raw=authority_raw,
        receiver_source_raw=receiver_raw,
        controller_manifest=verified_controller,
        expected_plan_id=expected_plan_id,
        loader_artifact=controller_facts[LOADER_RELATIVE],
        authority_artifact=controller_facts[AUTHORITY_RELATIVE],
        receiver_artifact=controller_facts[RECEIVER_RELATIVE],
        attempt_id=attempt_id,
        runtime_invocation_id=runtime_invocation_id,
        runtime_control_group=runtime_control_group,
    )
    finder.verify_loaded()
    if type(status) is not int or not 0 <= status <= 255:
        _fail("formal transport receiver exit status changed")
    return status


def _scientific_fd_entry(source: str, mode: str) -> int:
    if len(sys.argv) != 16:
        _fail("scientific FD loader argv arity changed")
    try:
        runner_fd = int(sys.argv[4])
    except ValueError as error:
        raise V42FormalProbeLoaderError("scientific runner FD changed") from error
    if str(runner_fd) != sys.argv[4] or runner_fd < 3:
        _fail("scientific runner FD changed")
    _verify_runtime(source, mode, expected_extra_fd=runner_fd)
    source_raw = source.encode("utf-8", errors="strict")
    loader_count = _exact_count(sys.argv[3], MAX_AUTHORITY_BYTES, "loader byte count")
    runner_count = _exact_count(
        sys.argv[6], MAX_LEGACY_SOURCE_BYTES, "scientific runner byte count"
    )
    if (
        _HEX64.fullmatch(sys.argv[2]) is None
        or _HEX64.fullmatch(sys.argv[5]) is None
        or _HEX64.fullmatch(sys.argv[7]) is None
        or _HEX64.fullmatch(sys.argv[15]) is None
        or len(source_raw) != loader_count
        or hashlib.sha256(source_raw).hexdigest() != sys.argv[2]
    ):
        _fail("scientific FD loader identity changed")
    targets = tuple(os.readlink("/proc/self/fd/" + str(fd)) for fd in (0, 1, 2))
    if targets != tuple(sys.argv[8:11]):
        _fail("scientific runner stdio target changed before source read")
    stdout_before = os.fstat(1)
    expected_stdout = tuple(int(value) for value in sys.argv[11:15])
    if (
        expected_stdout
        != (
            stdout_before.st_dev,
            stdout_before.st_ino,
            stdout_before.st_mode,
            stdout_before.st_rdev,
        )
        or mode == SCIENTIFIC_PREPARE_FD_MODE
        and (targets[1] == "/dev/null" or any(os.isatty(fd) for fd in (0, 1, 2)))
        or mode == SCIENTIFIC_LAUNCH_FD_MODE
        and targets != ("/dev/null", "/dev/null", "/dev/null")
    ):
        _fail("scientific runner stdio role changed")
    before = os.fstat(runner_fd)
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o444
        or before.st_uid != 1000
        or before.st_gid != 1000
        or before.st_nlink != 1
        or before.st_size != runner_count
    ):
        _fail("scientific runner held descriptor identity changed")
    os.lseek(runner_fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = runner_count
    digest = hashlib.sha256()
    while remaining:
        chunk = os.read(runner_fd, min(remaining, 1024 * 1024))
        if not chunk:
            _fail("scientific runner source ended early")
        chunks.append(chunk)
        digest.update(chunk)
        remaining -= len(chunk)
    if os.read(runner_fd, 1):
        _fail("scientific runner source grew during read")
    after = os.fstat(runner_fd)
    if _stable_tuple(before) != _stable_tuple(after) or digest.hexdigest() != sys.argv[5]:
        _fail("scientific runner source or held descriptor changed")
    os.close(runner_fd)
    if _live_descriptors() != [0, 1, 2]:
        _fail("scientific runner loader retained a non-stdio descriptor")
    if tuple(os.readlink("/proc/self/fd/" + str(fd)) for fd in (0, 1, 2)) != targets:
        _fail("scientific runner stdio target changed during source read")
    stdout_after = os.fstat(1)
    if (
        stdout_after.st_dev,
        stdout_after.st_ino,
        stdout_after.st_mode,
        stdout_after.st_rdev,
    ) != expected_stdout:
        _fail("scientific runner stdout identity changed during source read")
    legacy_facts = _legacy_source_facts(sys.argv[7])
    runner_relative = "scripts/run_v42_standard_2048_remote_ordinal2.py"
    runner_raw = b"".join(chunks)
    runner_fact = legacy_facts.get(runner_relative)
    if type(runner_fact) is not dict or _artifact(runner_relative, runner_raw) != {
        key: runner_fact[key]
        for key in (
            "relative_path", "git_mode", "git_object_type", "git_blob_oid",
            "byte_count", "sha256",
        )
    }:
        _fail("scientific runner differs from execution source manifest")
    if any(
        name == "acfqp" or name.startswith("acfqp.")
        or name == "scripts" or name.startswith("scripts.")
        for name in sys.modules
    ):
        _fail("repository module loaded before scientific verified importer")
    finder = _VerifiedSourceFinder(legacy_facts=legacy_facts, injected={})
    sys.meta_path.insert(0, finder)
    sys.dont_write_bytecode = True
    finder.verify_loaded()
    runner_path = os.path.join(FIXED_SOURCE_ROOT, runner_relative)
    runner_namespace: dict[str, Any] = {
        "__builtins__": __builtins__,
        "__name__": "_acfqp_v42r3_verified_scientific_runner",
        "__file__": runner_path,
        "__package__": None,
        "__cached__": None,
    }
    exec(
        compile(
            runner_raw, runner_path, "exec", flags=0, dont_inherit=True, optimize=0
        ),
        runner_namespace,
        runner_namespace,
    )
    finder.verify_loaded()
    entry = runner_namespace.get("main")
    if not callable(entry):
        _fail("scientific runner entry point changed")
    runner_mode = (
        "--prepare-remote"
        if mode == SCIENTIFIC_PREPARE_FD_MODE
        else "--launch-remote"
    )
    sys.argv = [runner_path, runner_mode]
    status = entry()
    if type(status) is not int or not 0 <= status <= 255:
        _fail("scientific runner exit status changed")
    return status


def _entry() -> int:
    if sys.argv[0] != "-c" or len(sys.argv) < 2 or sys.argv[1] not in ALL_MODES:
        _fail("formal transport loader mode or argv changed")
    mode = sys.argv[1]
    source = sys.orig_argv[5] if len(sys.orig_argv) >= 6 else ""
    if mode in SCIENTIFIC_FD_MODES:
        return _scientific_fd_entry(source, mode)
    expected_arity = (
        14
        if mode in SSH_MODES
        else 15
        if mode == SERVICE_BOOTSTRAP_MODE
        else 17
    )
    if len(sys.argv) != expected_arity:
        _fail("formal transport loader argv arity changed")
    _verify_runtime(source, mode)
    source_raw = source.encode("utf-8", errors="strict")
    sha_values = (sys.argv[2], sys.argv[4], sys.argv[6], sys.argv[8], sys.argv[10])
    if any(_HEX64.fullmatch(value) is None for value in sha_values):
        _fail("formal probe artifact SHA256 changed")
    loader_count = _exact_count(sys.argv[3], MAX_AUTHORITY_BYTES, "loader byte count")
    controller_count = _exact_count(
        sys.argv[5], MAX_CONTROLLER_BYTES, "controller manifest byte count"
    )
    authority_count = _exact_count(
        sys.argv[7], MAX_AUTHORITY_BYTES, "authority byte count"
    )
    receiver_count = _exact_count(
        sys.argv[9], MAX_RECEIVER_BYTES, "receiver byte count"
    )
    ingress_count = _exact_count(
        sys.argv[11], MAX_INGRESS_BYTES, "formal ingress byte count"
    )
    expected_plan_id = sys.argv[12]
    expected_legacy_source_manifest_id = sys.argv[13]
    if (
        _HEX64.fullmatch(expected_plan_id) is None
        or _HEX64.fullmatch(expected_legacy_source_manifest_id) is None
        or len(source_raw) != loader_count
        or hashlib.sha256(source_raw).hexdigest() != sys.argv[2]
    ):
        _fail("formal transport loader identity changed")
    if mode in SSH_MODES:
        controller_raw, authority_raw, receiver_raw, ingress_raw = _read_probe_frame()
    else:
        controller_raw, authority_raw, receiver_raw, ingress_raw = _service_sections(
            source_raw
        )
    transported = (
        (controller_raw, sys.argv[4], controller_count),
        (authority_raw, sys.argv[6], authority_count),
        (receiver_raw, sys.argv[8], receiver_count),
        (ingress_raw, sys.argv[10], ingress_count),
    )
    if any(
        len(raw) != count or hashlib.sha256(raw).hexdigest() != expected_sha
        for raw, expected_sha, count in transported
    ):
        _fail("formal transport artifact fact changed")
    controller = _canonical_document(controller_raw, "controller source manifest")
    controller_facts = _controller_facts(controller)
    _verify_raw_fact(
        raw=source_raw, relative=LOADER_RELATIVE,
        fact=controller_facts[LOADER_RELATIVE], expected_sha256=sys.argv[2],
        expected_count=loader_count,
    )
    _verify_raw_fact(
        raw=authority_raw, relative=AUTHORITY_RELATIVE,
        fact=controller_facts[AUTHORITY_RELATIVE], expected_sha256=sys.argv[6],
        expected_count=authority_count,
    )
    _verify_raw_fact(
        raw=receiver_raw, relative=RECEIVER_RELATIVE,
        fact=controller_facts[RECEIVER_RELATIVE], expected_sha256=sys.argv[8],
        expected_count=receiver_count,
    )
    ingress = _canonical_document(ingress_raw, "formal transport ingress")
    plan = _plan_from_ingress(mode, ingress)
    identifier_field = (
        "formal_host_epoch_probe_plan_id"
        if mode == PROBE_MODE
        else "formal_transport_plan_id"
    )
    if (
        plan.get(identifier_field) != expected_plan_id
        or plan.get("legacy_execution_source_manifest_id")
        != expected_legacy_source_manifest_id
    ):
        _fail("formal transport plan/command/source join changed")
    attempt_id = None if mode in SSH_MODES else sys.argv[14]
    runtime_invocation_id = sys.argv[15] if mode == SERVICE_WRAPPER_MODE else None
    runtime_control_group = sys.argv[16] if mode == SERVICE_WRAPPER_MODE else None
    if attempt_id is not None and _HEX64.fullmatch(attempt_id) is None:
        _fail("formal service attempt ID changed")
    if mode == SERVICE_WRAPPER_MODE and (
        re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", runtime_invocation_id or "")
        is None
        or type(runtime_control_group) is not str
        or not runtime_control_group.startswith("/user.slice/")
    ):
        _fail("formal clean-wrapper runtime identity changed")
    return _execute_authenticated_sources(
        mode=mode,
        controller=controller,
        controller_facts=controller_facts,
        loader_raw=source_raw,
        authority_raw=authority_raw,
        receiver_raw=receiver_raw,
        ingress_raw=ingress_raw,
        expected_plan_id=expected_plan_id,
        expected_legacy_source_manifest_id=expected_legacy_source_manifest_id,
        attempt_id=attempt_id,
        runtime_invocation_id=runtime_invocation_id,
        runtime_control_group=runtime_control_group,
    )


if __name__ == "__main__" and sys.argv[0] == "-c":
    try:
        _status = _entry()
    except BaseException as _error:
        _failure_raw = _loader_failure_stderr(_error)
        try:
            _written = os.write(2, _failure_raw)
        except BaseException:
            os._exit(74)
        if _written != len(_failure_raw):
            os._exit(74)
        os._exit(73)
    else:
        os._exit(_status)
