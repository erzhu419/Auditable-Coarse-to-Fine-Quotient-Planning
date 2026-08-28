"""Stdlib-only read-only receiver for the native V42r2 activation successor.

The receiver observes five small canonical JSON documents through pinned
directory descriptors.  It never creates, removes, renames, truncates, or
changes a remote filesystem object.  In particular, the large source capsule
and bootstrap archive are inventoried by name but their contents are not read.
"""

from __future__ import annotations

import hashlib
import json
import os
import pwd
import socket
import stat


SCHEMA_VERSION = "42.2.0"
FORMAL_IDENTITY = (
    "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2"
)
GLOBAL_EXECUTION_ORDINAL = 2
REMOTE_UID = 1000
REMOTE_GID = 1000
FIXED_ROOT = "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2"
SOURCE_ROOT = FIXED_ROOT + "/source"

OBSERVATION_SCHEMA = (
    "acfqp.v42_activation_successor_read_only_observation.v42r2"
)
OBSERVATION_ID_DOMAIN = "acfqp:v42r2:activation-successor-read-only-observation"

SOURCE_MANIFEST_NAME = "EXECUTION_SOURCE_MANIFEST.json"
TRANSPORT_MANIFEST_NAME = "TRANSPORT_MANIFEST.json"
LOCAL_ATTEMPT_NAME = "LOCAL_MATERIALIZATION_ATTEMPT.json"
REMOTE_ATTEMPT_NAME = "MATERIALIZATION_ATTEMPT.json"
TERMINAL_NAME = ".V42_REMOTE_ORDINAL2_MATERIALIZATION_TERMINAL.json"

DOCUMENT_SPECS = (
    ("source_manifest", "fixed_root", SOURCE_MANIFEST_NAME, 64 * 1024**2),
    ("transport_manifest", "fixed_root", TRANSPORT_MANIFEST_NAME, 64 * 1024**2),
    ("local_materialization_attempt", "fixed_root", LOCAL_ATTEMPT_NAME, 4 * 1024**2),
    ("remote_materialization_attempt", "fixed_root", REMOTE_ATTEMPT_NAME, 4 * 1024**2),
    ("materialization_terminal", "source_root", TERMINAL_NAME, 4 * 1024**2),
)


class V42ActivationSuccessorReceiverError(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise V42ActivationSuccessorReceiverError(message)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate JSON object key")
        result[key] = value
    return result


def _reject_number(token: str) -> None:
    _fail("non-integer JSON number is forbidden: " + token)


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42ActivationSuccessorReceiverError(
            "value is not canonical JSON"
        ) from error


def _canonical_document(raw: bytes, label: str, maximum: int) -> dict[str, object]:
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        _fail(label + " byte envelope changed")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except V42ActivationSuccessorReceiverError:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise V42ActivationSuccessorReceiverError(
            label + " is not strict JSON"
        ) from error
    if type(value) is not dict or _canonical_bytes(value) != raw:
        _fail(label + " is not an exact canonical JSON object")
    return value


def _content_id(domain: str, payload: dict[str, object]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\0" + _canonical_bytes(payload)
    ).hexdigest()


def _identity(path: str, observed: os.stat_result, node_type: str) -> dict[str, object]:
    return {
        "path": path,
        "node_type": node_type,
        "st_dev": observed.st_dev,
        "st_ino": observed.st_ino,
        "mode": stat.S_IMODE(observed.st_mode),
        "uid": observed.st_uid,
        "gid": observed.st_gid,
        "st_nlink": observed.st_nlink,
        "st_size": observed.st_size,
        "st_mtime_ns": observed.st_mtime_ns,
        "st_ctime_ns": observed.st_ctime_ns,
    }


def _anchor_identity(observed: os.stat_result) -> dict[str, int]:
    return {
        "st_dev": observed.st_dev,
        "st_ino": observed.st_ino,
        "mode": stat.S_IMODE(observed.st_mode),
        "uid": observed.st_uid,
        "gid": observed.st_gid,
    }


def _open_lexical_directory_pins(
    path: str,
) -> tuple[list[int], list[str], list[dict[str, object]]]:
    if (
        type(path) is not str
        or not path.startswith("/")
        or path == "/"
        or os.path.normpath(path) != path
        or ".." in path.split("/")
    ):
        _fail("fixed remote root path changed")
    descriptors = [
        os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    ]
    names: list[str] = []
    rows: list[dict[str, object]] = [
        {"absolute_path": "/", "identity": _anchor_identity(os.fstat(descriptors[0]))}
    ]
    current = ""
    try:
        for component in (part for part in path.split("/") if part):
            parent = descriptors[-1]
            before = os.stat(component, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                _fail("fixed remote root lexical component is not a directory")
            descriptor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=parent,
            )
            opened = os.fstat(descriptor)
            if _anchor_identity(before) != _anchor_identity(opened):
                os.close(descriptor)
                _fail("fixed remote root lexical component changed during open")
            descriptors.append(descriptor)
            names.append(component)
            current += "/" + component
            rows.append(
                {"absolute_path": current, "identity": _anchor_identity(opened)}
            )
        return descriptors, names, rows
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _verify_lexical_directory_pins(
    descriptors: list[int], names: list[str], expected: list[dict[str, object]]
) -> list[dict[str, object]]:
    if len(descriptors) != len(names) + 1 or len(expected) != len(descriptors):
        _fail("fixed remote root lexical pin inventory changed")
    rows = [
        {"absolute_path": "/", "identity": _anchor_identity(os.fstat(descriptors[0]))}
    ]
    current = ""
    for index, component in enumerate(names):
        named = os.stat(component, dir_fd=descriptors[index], follow_symlinks=False)
        held = os.fstat(descriptors[index + 1])
        if (
            not stat.S_ISDIR(named.st_mode)
            or _anchor_identity(named) != _anchor_identity(held)
        ):
            _fail("fixed remote root lexical pin changed")
        current += "/" + component
        rows.append({"absolute_path": current, "identity": _anchor_identity(held)})
    if rows != expected:
        _fail("fixed remote root lexical chain changed during inspection")
    return rows


def _read_exact_document_at(
    directory_fd: int,
    *,
    directory_path: str,
    relative_name: str,
    maximum: int,
    expected_uid: int,
    expected_gid: int,
) -> dict[str, object]:
    absolute_path = directory_path + "/" + relative_name
    before = os.stat(relative_name, dir_fd=directory_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_uid != expected_uid
        or before.st_gid != expected_gid
        or before.st_nlink != 1
        or not 0 < before.st_size <= maximum
    ):
        _fail("successor evidence document storage changed: " + relative_name)
    descriptor = os.open(
        relative_name,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=directory_fd,
    )
    try:
        opened = os.fstat(descriptor)
        before_identity = _identity(absolute_path, before, "REGULAR_FILE")
        opened_identity = _identity(absolute_path, opened, "REGULAR_FILE")
        if opened_identity != before_identity:
            _fail("successor evidence document changed before open")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                _fail("successor evidence document ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("successor evidence document grew while read")
        after_fd = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.stat(relative_name, dir_fd=directory_fd, follow_symlinks=False)
    after_fd_identity = _identity(absolute_path, after_fd, "REGULAR_FILE")
    after_path_identity = _identity(absolute_path, after_path, "REGULAR_FILE")
    if (
        after_fd_identity != before_identity
        or after_path_identity != before_identity
    ):
        _fail("successor evidence document changed during read")
    raw = b"".join(chunks)
    document = _canonical_document(raw, relative_name, maximum)
    return {
        "absolute_path": absolute_path,
        "relative_name": relative_name,
        "identity_before": before_identity,
        "identity_opened": opened_identity,
        "identity_after": after_path_identity,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "document": document,
    }


def _inspect_pinned_root_read_only(
    fixed_root: str, *, expected_uid: int, expected_gid: int
) -> dict[str, object]:
    """Read the fixed five-document subset inside one stable pinned window."""

    if (
        type(expected_uid) is not int
        or expected_uid < 0
        or type(expected_gid) is not int
        or expected_gid < 0
    ):
        _fail("expected fixed-root owner changed")
    source_root = fixed_root + "/source"

    descriptors, names, lexical_before = _open_lexical_directory_pins(fixed_root)
    root_fd = descriptors[-1]
    source_fd: int | None = None
    try:
        root_before_stat = os.fstat(root_fd)
        if (
            not stat.S_ISDIR(root_before_stat.st_mode)
            or stat.S_IMODE(root_before_stat.st_mode) != 0o700
            or root_before_stat.st_uid != expected_uid
            or root_before_stat.st_gid != expected_gid
        ):
            _fail("fixed remote root is misowned or has unsafe mode")
        root_before = _identity(fixed_root, root_before_stat, "DIRECTORY")
        root_inventory_before = sorted(os.listdir(root_fd))
        if len(root_inventory_before) != len(set(root_inventory_before)):
            _fail("fixed remote root inventory contains duplicate names")

        source_before_stat = os.stat("source", dir_fd=root_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(source_before_stat.st_mode)
            or stat.S_IMODE(source_before_stat.st_mode) != 0o700
            or source_before_stat.st_uid != expected_uid
            or source_before_stat.st_gid != expected_gid
        ):
            _fail("fixed remote source root is misowned or has unsafe mode")
        source_fd = os.open(
            "source",
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=root_fd,
        )
        source_opened_stat = os.fstat(source_fd)
        source_before = _identity(source_root, source_before_stat, "DIRECTORY")
        source_opened = _identity(source_root, source_opened_stat, "DIRECTORY")
        if source_before != source_opened:
            _fail("fixed remote source root changed during open")
        source_inventory_before = sorted(os.listdir(source_fd))
        if len(source_inventory_before) != len(set(source_inventory_before)):
            _fail("fixed remote source inventory contains duplicate names")

        documents: dict[str, object] = {}
        for role, parent, relative_name, maximum in DOCUMENT_SPECS:
            selected_fd = root_fd if parent == "fixed_root" else source_fd
            selected_path = fixed_root if parent == "fixed_root" else source_root
            row = _read_exact_document_at(
                selected_fd,
                directory_path=selected_path,
                relative_name=relative_name,
                maximum=maximum,
                expected_uid=expected_uid,
                expected_gid=expected_gid,
            )
            row["parent"] = parent
            documents[role] = row

        source_inventory_after = sorted(os.listdir(source_fd))
        source_after_fd = os.fstat(source_fd)
        source_after_path = os.stat("source", dir_fd=root_fd, follow_symlinks=False)
        source_after = _identity(source_root, source_after_path, "DIRECTORY")
        if (
            source_inventory_after != source_inventory_before
            or _identity(source_root, source_after_fd, "DIRECTORY") != source_before
            or source_after != source_before
        ):
            _fail("fixed remote source root changed during inspection")

        root_inventory_after = sorted(os.listdir(root_fd))
        root_after_stat = os.fstat(root_fd)
        lexical_after = _verify_lexical_directory_pins(
            descriptors, names, lexical_before
        )
        root_after = _identity(fixed_root, root_after_stat, "DIRECTORY")
        if root_inventory_after != root_inventory_before or root_after != root_before:
            _fail("fixed remote root changed during inspection")
    finally:
        if source_fd is not None:
            os.close(source_fd)
        for descriptor in reversed(descriptors):
            os.close(descriptor)

    return {
        "fixed_root_lexical_chain_before": lexical_before,
        "fixed_root_lexical_chain_after": lexical_after,
        "fixed_root": {
            "path": fixed_root,
            "identity_before": root_before,
            "identity_opened": root_before,
            "identity_after": root_after,
            "inventory_before": root_inventory_before,
            "inventory_after": root_inventory_after,
        },
        "source_root": {
            "path": source_root,
            "identity_before": source_before,
            "identity_opened": source_opened,
            "identity_after": source_after,
            "inventory_before": source_inventory_before,
            "inventory_after": source_inventory_after,
        },
        "documents": documents,
        "single_pinned_before_after_window": True,
        "all_document_reads_nofollow_and_stable": True,
        "collected_subset_only_not_whole_tree": True,
        "large_binary_content_read": False,
    }


def observe(
    *,
    fixed_root: str = FIXED_ROOT,
    expected_uid: int = REMOTE_UID,
    expected_gid: int = REMOTE_GID,
) -> dict[str, object]:
    """Return a content-addressed observation without any filesystem write."""

    try:
        window = _inspect_pinned_root_read_only(
            fixed_root, expected_uid=expected_uid, expected_gid=expected_gid
        )
    except V42ActivationSuccessorReceiverError:
        raise
    except OSError as error:
        raise V42ActivationSuccessorReceiverError(
            "fixed successor evidence became unobservable"
        ) from error
    payload = {
        "schema": OBSERVATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "observed_hostname": socket.gethostname(),
        "observed_user": pwd.getpwuid(os.getuid()).pw_name,
        "observed_uid": os.getuid(),
        "observed_gid": os.getgid(),
        **window,
        "observed_document_count": len(DOCUMENT_SPECS),
        "remote_mutation_performed": False,
        "large_binary_content_read": False,
        "only_fixed_small_json_documents_read": True,
    }
    return {
        **payload,
        "activation_successor_read_only_observation_id": _content_id(
            OBSERVATION_ID_DOMAIN, payload
        ),
    }


__all__ = [
    "DOCUMENT_SPECS",
    "FIXED_ROOT",
    "OBSERVATION_SCHEMA",
    "SOURCE_ROOT",
    "V42ActivationSuccessorReceiverError",
    "observe",
]
