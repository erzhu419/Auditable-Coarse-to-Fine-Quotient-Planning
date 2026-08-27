#!/usr/bin/env python3
"""Build and safely materialize the V42 remote ordinal-2 source capsule.

This program contains no network client.  ``--build-local-capsule`` reads one
exact committed Git tree and creates deterministic local transport artifacts.
``--materialize-remote-capsule`` is intended to be invoked explicitly on the
already-selected host after those exact files have been transported there.
Both public modes reverify the frozen ordinal-1 retention closure and fail
closed if its committed identities or live retained bytes differ.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile
from typing import Any, NoReturn, Sequence
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from acfqp import construction_k7_standard_2048_remote_execution_authority_v42r1 as authority
from acfqp import construction_k7_standard_2048_process_supervision_v42r1 as processio
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


LOCAL_CAPSULE_ROOT_RELATIVE = (
    ".tmp/exact-freeze/v42-standard-2048-remote-ordinal2-capsule"
)
MAXIMUM_CAPSULE_BYTES = 2 * 1024**3
MAXIMUM_MEMBER_BYTES = 512 * 1024**2
GIT_EXECUTABLE = "/usr/bin/git"
GIT_EXECUTABLE_REALPATH = "/usr/bin/git"
GIT_EXECUTABLE_SHA256 = (
    "587ef21868c948b883993e23209b86a72a6ddc06aab1545c697ffc31075acd4a"
)
GIT_EXECUTABLE_BYTE_COUNT = 3_710_360
GIT_VERSION_STDOUT = b"git version 2.34.1\n"
LOCAL_BUILD_PYTHON = "/usr/bin/python3"
LOCAL_BUILD_PYTHON_REALPATH = "/usr/bin/python3.10"
LOCAL_BUILD_PYTHON_VERSION = (3, 10, 12)
_HERMETIC_GIT_ENV = {
    "LC_ALL": "C",
    "LANG": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
}
_REMOTE_BOOTSTRAP_RUNTIME_BINDING: dict[str, Any] | None = None
_REMOTE_BOOTSTRAP_RUNTIME_BINDING_INSTALLATION_CLOSED = False


class V42RemoteOrdinal2BootstrapError(RuntimeError):
    """The committed capsule, transport manifest, or safe extraction changed."""


def _fail(message: str) -> NoReturn:
    raise V42RemoteOrdinal2BootstrapError(message)


def install_remote_bootstrap_runtime_binding_v42r1(
    binding: dict[str, Any],
) -> None:
    """Install the generated-main observation exactly once, before any effect."""

    global _REMOTE_BOOTSTRAP_RUNTIME_BINDING
    if (
        _REMOTE_BOOTSTRAP_RUNTIME_BINDING is not None
        or _REMOTE_BOOTSTRAP_RUNTIME_BINDING_INSTALLATION_CLOSED
    ):
        _fail("remote bootstrap runtime binding was already installed")
    if type(binding) is not dict:
        _fail("remote bootstrap runtime binding changed type")
    # Detach from the generated main's mutable object without broadening the
    # accepted JSON language.  Authority verification occurs after the fixed
    # five controls have been read again and before the remote attempt write.
    _REMOTE_BOOTSTRAP_RUNTIME_BINDING = loads_canonical_json(
        canonical_json_bytes(binding)
    )


def _run_hermetic_git_v42r1(
    root: Path, *arguments: str, input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        (GIT_EXECUTABLE, "--no-replace-objects", *arguments),
        cwd=root,
        env=dict(_HERMETIC_GIT_ENV),
        input=input_bytes,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git(root: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    completed = _run_hermetic_git_v42r1(
        root, *arguments, input_bytes=input_bytes
    )
    if completed.returncode != 0:
        _fail(
            "git "
            + " ".join(arguments)
            + " failed: "
            + completed.stderr.decode("utf-8", errors="replace")[:4096]
        )
    return completed.stdout


def _write_once(path: Path, raw: bytes, *, mode: int = 0o400) -> None:
    previous_umask = os.umask(0o077)
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            mode,
        )
    finally:
        os.umask(previous_umask)
    try:
        os.fchmod(descriptor, mode)
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V42 remote ordinal-2 bootstrap short write")
            view = view[written:]
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _create_one_shot_directory(path: Path, *, expected_parent: Path | None = None) -> None:
    if not path.is_absolute() or path == Path(path.anchor):
        _fail("capsule one-shot directory is not narrow and absolute")
    if expected_parent is not None and path.parent != expected_parent:
        _fail("capsule one-shot directory parent changed")
    parent = path.parent
    parent_observed = parent.lstat()
    if (
        not stat.S_ISDIR(parent_observed.st_mode)
        or parent.resolve(strict=True) != parent
    ):
        _fail("capsule one-shot parent is redirected or not a directory")
    previous_umask = os.umask(0o077)
    try:
        try:
            os.mkdir(path, 0o700)
        except FileExistsError as error:
            raise V42RemoteOrdinal2BootstrapError(
                "capsule identity already exists; same-identity retry is forbidden"
            ) from error
    finally:
        os.umask(previous_umask)
    os.chmod(path, 0o700)
    descriptor = os.open(
        parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_regular_nofollow_capped(path: Path, maximum: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > maximum
        ):
            _fail("transported capsule control artifact is nonregular or oversized")
        chunks: list[bytes] = []
        total = 0
        while True:
            remaining = maximum + 1 - total
            if remaining <= 0:
                _fail("transported capsule control artifact exceeds its byte cap")
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                _fail("transported capsule control artifact exceeds its byte cap")
        after = os.fstat(descriptor)
        stable = (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
            "st_size", "st_mtime_ns", "st_ctime_ns",
        )
        if any(getattr(before, field) != getattr(after, field) for field in stable):
            _fail("transported capsule control artifact changed during read")
    finally:
        os.close(descriptor)
    final = path.lstat()
    if any(getattr(before, field) != getattr(final, field) for field in stable):
        _fail("transported capsule control artifact name changed during read")
    return b"".join(chunks)


_CONTROL_STABLE_FIELDS = (
    "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
    "st_size", "st_mtime_ns", "st_ctime_ns",
)


def _control_identity(observed: os.stat_result) -> tuple[int, ...]:
    return tuple(getattr(observed, field) for field in _CONTROL_STABLE_FIELDS)


def _verify_formal_control_snapshot(root: Path, snapshot: dict[str, Any]) -> None:
    if (
        _control_identity(root.lstat()) != tuple(snapshot["root_identity"])
        or sorted(entry.name for entry in root.iterdir()) != snapshot["root_inventory"]
    ):
        _fail("formal remote control root changed across pre-attempt verification")
    for name, expected in snapshot["control_identities"].items():
        if _control_identity((root / name).lstat()) != tuple(expected):
            _fail("formal remote control changed across pre-attempt verification")


def _git_object_oid_sha1(kind: str, raw: bytes) -> str:
    if kind not in {"blob", "commit", "tree"}:
        _fail("capsule Git object kind is not admitted")
    return hashlib.sha1(  # noqa: S324 - exact Git SHA-1 object identity
        f"{kind} {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def _verify_fixed_git_executable_v42r1() -> tuple[int, ...]:
    executable = Path(GIT_EXECUTABLE)
    observed = executable.lstat()
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != 0
        or observed.st_gid != 0
        or observed.st_nlink != 1
        or stat.S_IMODE(observed.st_mode) != 0o755
        or os.path.realpath(GIT_EXECUTABLE) != GIT_EXECUTABLE_REALPATH
    ):
        _fail("fixed Git executable identity changed")
    raw = _read_regular_nofollow_capped(
        executable, GIT_EXECUTABLE_BYTE_COUNT
    )
    if (
        len(raw) != GIT_EXECUTABLE_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != GIT_EXECUTABLE_SHA256
    ):
        _fail("fixed Git executable bytes changed")
    completed = _run_hermetic_git_v42r1(Path("/"), "--version")
    if completed.returncode != 0 or completed.stdout != GIT_VERSION_STDOUT:
        _fail("fixed Git executable version changed")
    final = executable.lstat()
    if _control_identity(final) != _control_identity(observed):
        _fail("fixed Git executable changed across byte and version verification")
    return _control_identity(observed)


def _verify_git_common_directory_v42r1(root: Path) -> tuple[int, ...]:
    """Bind the selected repository to its one non-redirected common dir.

    The scientific source authority is the recorded 40-hex commit plus the
    independently rehashed commit/tree/blob graph below.  This gate therefore
    rejects repository-wide common-dir overlays without making a broader claim
    about the physical object-store layout of every Git implementation.
    """

    git_directory = root / ".git"
    commondir_redirect = git_directory / "commondir"
    before = git_directory.lstat()
    if (
        not stat.S_ISDIR(before.st_mode)
        or git_directory.resolve(strict=True) != git_directory
    ):
        _fail("capsule Git metadata directory is redirected")
    try:
        commondir_redirect.lstat()
    except FileNotFoundError:
        pass
    else:
        _fail("capsule Git repository has a common-directory redirect")
    common_directory_text = _git(
        root, "rev-parse", "--path-format=absolute", "--git-common-dir"
    ).decode("utf-8", errors="strict").strip()
    try:
        commondir_redirect.lstat()
    except FileNotFoundError:
        pass
    else:
        _fail("capsule Git common-directory redirect appeared during verification")
    after = git_directory.lstat()
    if (
        common_directory_text != str(git_directory)
        or _control_identity(after) != _control_identity(before)
    ):
        _fail("capsule Git common directory changed across verification")
    return _control_identity(before)


def _verify_hermetic_git_repository_v42r1(
    root: Path, *, source_commit: str,
) -> str:
    """Pin the local Git executable/repository and recompute commit/tree IDs."""

    if (
        not root.is_absolute()
        or root.resolve(strict=True) != root
        or not re.fullmatch(r"[0-9a-f]{40}", source_commit)
    ):
        _fail("capsule Git root or source commit is not exact")
    executable_identity = _verify_fixed_git_executable_v42r1()
    common_directory_identity = _verify_git_common_directory_v42r1(root)
    top = _git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    git_directory_text = _git(
        root, "rev-parse", "--absolute-git-dir"
    ).decode("utf-8").strip()
    object_format = _git(
        root, "rev-parse", "--show-object-format"
    ).decode("ascii").strip()
    git_directory = root / ".git"
    if (
        top != str(root)
        or git_directory_text != str(git_directory)
        or object_format != "sha1"
    ):
        _fail("capsule Git repository identity or object format changed")
    git_directory_observed = git_directory.lstat()
    if _control_identity(git_directory_observed) != common_directory_identity:
        _fail("capsule Git metadata directory changed during repository verification")
    for forbidden_overlay in (
        git_directory / "objects" / "info" / "alternates",
        git_directory / "info" / "grafts",
    ):
        try:
            forbidden_overlay.lstat()
        except FileNotFoundError:
            pass
        else:
            _fail("capsule Git repository has an object or history overlay")
    replace_refs = _git(
        root, "for-each-ref", "--format=%(refname)", "refs/replace"
    )
    if replace_refs != b"":
        _fail("capsule Git repository contains replacement refs")
    resolved_commit = _git(
        root, "rev-parse", "--verify", f"{source_commit}^{{commit}}"
    ).decode("ascii").strip()
    if resolved_commit != source_commit:
        _fail("capsule Git commit identity changed")
    commit_raw = _git(root, "cat-file", "commit", source_commit)
    if _git_object_oid_sha1("commit", commit_raw) != source_commit:
        _fail("capsule Git commit bytes do not recompute to their object ID")
    first_line, separator, _rest = commit_raw.partition(b"\n")
    if separator != b"\n" or re.fullmatch(rb"tree [0-9a-f]{40}", first_line) is None:
        _fail("capsule Git commit omitted one canonical tree header")
    source_tree = first_line[5:].decode("ascii")
    if _git(
        root, "rev-parse", f"{source_commit}^{{tree}}"
    ).decode("ascii").strip() != source_tree:
        _fail("capsule Git selected tree differs from its commit header")
    tree_raw = _git(root, "cat-file", "tree", source_tree)
    if _git_object_oid_sha1("tree", tree_raw) != source_tree:
        _fail("capsule Git tree bytes do not recompute to their object ID")
    if _verify_fixed_git_executable_v42r1() != executable_identity:
        _fail("fixed Git executable changed across repository verification")
    if _verify_git_common_directory_v42r1(root) != common_directory_identity:
        _fail("capsule Git common directory changed across repository verification")
    return source_tree


def _parse_raw_git_tree_v42r1(raw: bytes) -> list[tuple[str, str, str]]:
    """Parse one raw SHA-1 tree without trusting ``git ls-tree`` traversal."""

    if not raw or len(raw) > 64 * 1024**2:
        _fail("capsule Git tree object is empty or oversized")
    rows: list[tuple[str, str, str]] = []
    offset = 0
    previous_sort_key: bytes | None = None
    while offset < len(raw):
        space = raw.find(b" ", offset)
        nul = raw.find(b"\0", space + 1 if space >= 0 else offset)
        if space <= offset or nul <= space + 1 or nul + 21 > len(raw):
            _fail("capsule raw Git tree record is truncated")
        mode_raw = raw[offset:space]
        name_raw = raw[space + 1 : nul]
        object_raw = raw[nul + 1 : nul + 21]
        offset = nul + 21
        if mode_raw == b"100644":
            entry_type = "blob"
            sort_key = name_raw
        elif mode_raw == b"40000":
            entry_type = "tree"
            sort_key = name_raw + b"/"
        else:
            _fail("capsule Git tree contains a non-100644 or non-tree entry")
        if (
            previous_sort_key is not None
            and sort_key <= previous_sort_key
        ):
            _fail("capsule raw Git tree entries are not canonical and unique")
        previous_sort_key = sort_key
        if (
            not name_raw
            or b"/" in name_raw
            or b"\\" in name_raw
            or any(byte < 0x20 or byte == 0x7F for byte in name_raw)
        ):
            _fail("capsule Git tree component is unsafe")
        try:
            name = name_raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise V42RemoteOrdinal2BootstrapError(
                "capsule Git tree component is not UTF-8"
            ) from error
        if name in {".", ".."} or PurePosixPath(name).as_posix() != name:
            _fail("capsule Git tree component is noncanonical")
        rows.append((entry_type, name, object_raw.hex()))
    if offset != len(raw) or not rows:
        _fail("capsule raw Git tree has trailing bytes or no entries")
    return rows


def _committed_inventory(root: Path, source_commit: str) -> tuple[str, list[dict[str, str]]]:
    resolved = _git(root, "rev-parse", "--verify", f"{source_commit}^{{commit}}")
    if resolved.decode("ascii").strip() != source_commit:
        _fail("capsule source commit is abbreviated or changed")
    source_tree_text = _git(
        root, "rev-parse", f"{source_commit}^{{tree}}"
    ).decode("ascii").strip()
    if re.fullmatch(r"[0-9a-f]{40}", source_tree_text) is None:
        _fail("capsule source tree identity changed")
    entries: list[dict[str, str]] = []
    active_tree_oids: set[str] = set()

    def visit(tree_oid: str, prefix: tuple[str, ...]) -> None:
        if tree_oid in active_tree_oids or len(prefix) > 128:
            _fail("capsule Git tree graph cycles or exceeds its depth cap")
        active_tree_oids.add(tree_oid)
        try:
            raw_tree = _git(root, "cat-file", "tree", tree_oid)
            if _git_object_oid_sha1("tree", raw_tree) != tree_oid:
                _fail("capsule child Git tree bytes changed object identity")
            for entry_type, name, object_id in _parse_raw_git_tree_v42r1(raw_tree):
                relative_parts = (*prefix, name)
                relative = PurePosixPath(*relative_parts).as_posix()
                if entry_type == "tree":
                    visit(object_id, relative_parts)
                else:
                    entries.append(
                        {
                            "relative_path": relative,
                            "git_mode": "100644",
                            "git_object_type": "blob",
                            "git_blob_oid": object_id,
                        }
                    )
                    if len(entries) > 1_000_000:
                        _fail("capsule Git tree exceeds its regular-file count cap")
        finally:
            active_tree_oids.remove(tree_oid)

    visit(source_tree_text, ())
    entries.sort(key=lambda row: row["relative_path"])
    paths = [row["relative_path"] for row in entries]
    if not entries or len(paths) != len(set(paths)):
        _fail("capsule Git tree inventory is empty or contains duplicate paths")
    return source_tree_text, entries


def _read_blobs_batch(root: Path, object_ids: Sequence[str]) -> dict[str, bytes]:
    unique = tuple(sorted(set(object_ids)))
    request = b"".join(object_id.encode("ascii") + b"\n" for object_id in unique)
    completed = _run_hermetic_git_v42r1(
        root, "cat-file", "--batch", input_bytes=request
    )
    if completed.returncode != 0:
        _fail("git cat-file --batch failed while building the capsule")
    result: dict[str, bytes] = {}
    offset = 0
    for requested in unique:
        newline = completed.stdout.find(b"\n", offset)
        if newline < 0:
            _fail("capsule Git batch header is truncated")
        try:
            observed, kind, size_text = completed.stdout[offset:newline].decode("ascii").split()
            size = int(size_text)
        except (UnicodeDecodeError, ValueError) as error:
            raise V42RemoteOrdinal2BootstrapError(
                "capsule Git batch header is malformed"
            ) from error
        offset = newline + 1
        if observed != requested or kind != "blob" or size < 0 or size > MAXIMUM_MEMBER_BYTES:
            _fail("capsule Git batch object changed")
        raw = completed.stdout[offset : offset + size]
        offset += size
        if completed.stdout[offset : offset + 1] != b"\n":
            _fail("capsule Git batch object delimiter changed")
        offset += 1
        if authority._git_blob_oid_sha1(raw) != requested:  # noqa: SLF001
            _fail("capsule Git blob bytes do not recompute to their requested object ID")
        result[requested] = raw
    if offset != len(completed.stdout):
        _fail("capsule Git batch output has trailing bytes")
    return result


def _deterministic_ustar_bytes(
    entries: Sequence[dict[str, str]], blobs: dict[str, bytes]
) -> tuple[bytes, list[dict[str, Any]]]:
    stream = io.BytesIO()
    facts: list[dict[str, Any]] = []
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for entry in entries:
            raw = blobs[entry["git_blob_oid"]]
            member = tarfile.TarInfo(entry["relative_path"])
            member.type = tarfile.REGTYPE
            member.size = len(raw)
            member.mode = int(authority.MATERIALIZED_SOURCE_FILE_MODE, 8)
            member.uid = 0
            member.gid = 0
            member.uname = ""
            member.gname = ""
            member.mtime = 0
            archive.addfile(member, io.BytesIO(raw))
            facts.append(
                {
                    **entry,
                    "byte_count": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
    raw_archive = stream.getvalue()
    if not raw_archive or len(raw_archive) > MAXIMUM_CAPSULE_BYTES:
        _fail("deterministic source capsule is empty or exceeds its cap")
    return raw_archive, facts


def _deterministic_remote_bootstrap_pyz_bytes(
    entries: Sequence[dict[str, str]], blobs: dict[str, bytes],
    *, committed_bootstrap_constants: dict[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    """Build the self-contained fixed bootstrap from exact committed blobs."""

    by_path = {entry["relative_path"]: entry for entry in entries}
    members: list[dict[str, Any]] = []
    member_bytes: list[tuple[str, bytes]] = []
    for archive_path, module_name, member_kind, source_relative in (
        committed_bootstrap_constants["REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS"]
    ):
        if member_kind == "GENERATED_STDLIB_MAIN":
            raw = committed_bootstrap_constants[
                "REMOTE_BOOTSTRAP_GENERATED_MAIN_BYTES"
            ]
            git_blob_oid = None
        elif member_kind == "GENERATED_EMPTY_PACKAGE_SHIM":
            raw = committed_bootstrap_constants[
                "REMOTE_BOOTSTRAP_GENERATED_EMPTY_PACKAGE_SHIM_BYTES"
            ]
            git_blob_oid = None
        else:
            entry = by_path.get(source_relative)
            if entry is None:
                _fail("remote bootstrap committed member is absent from the Git tree")
            git_blob_oid = entry["git_blob_oid"]
            raw = blobs[git_blob_oid]
        members.append(
            {
                "archive_path": archive_path,
                "module_name": module_name,
                "member_kind": member_kind,
                "source_relative_path": source_relative,
                "git_blob_oid": git_blob_oid,
                "member_mode": authority.REMOTE_BOOTSTRAP_PYZ_MEMBER_MODE,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        member_bytes.append((archive_path, raw))
    if [name for name, _ in member_bytes] != sorted(name for name, _ in member_bytes):
        _fail("remote bootstrap pyz members are not in exact sorted order")
    stream = io.BytesIO()
    with zipfile.ZipFile(
        stream, mode="w", compression=zipfile.ZIP_STORED, allowZip64=False
    ) as archive:
        archive.comment = b""
        for archive_path, raw in member_bytes:
            info = zipfile.ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.flag_bits = 0
            info.external_attr = (stat.S_IFREG | 0o444) << 16
            info.internal_attr = 0
            info.extra = b""
            info.comment = b""
            archive.writestr(info, raw)
    raw_pyz = stream.getvalue()
    if not raw_pyz or len(raw_pyz) > 64 * 1024**2:
        _fail("remote bootstrap pyz is empty or exceeds its fixed cap")
    artifact = authority.build_remote_bootstrap_pyz_artifact_v42r1(
        members=members,
        pyz_sha256=hashlib.sha256(raw_pyz).hexdigest(),
        pyz_byte_count=len(raw_pyz),
    )
    return raw_pyz, artifact


_COMMITTED_BOOTSTRAP_CONSTANT_NAMES = frozenset(
    {
        "REMOTE_BOOTSTRAP_GENERATED_MAIN_BYTES",
        "REMOTE_BOOTSTRAP_GENERATED_EMPTY_PACKAGE_SHIM_BYTES",
        "REMOTE_BOOTSTRAP_TRUSTED_LAUNCHER_BYTES",
        "REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS",
        "REMOTE_BOOTSTRAP_PYZ_FORMAT",
        "REMOTE_BOOTSTRAP_PYZ_FILE_MODE",
        "REMOTE_BOOTSTRAP_PYZ_MEMBER_MODE",
        "REMOTE_BOOTSTRAP_PYZ_NAME",
        "REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH",
        "REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_PATH",
        "REMOTE_BOOTSTRAP_RUNTIME_PYZ_FD",
        "REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_FD",
        "REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS",
        "REMOTE_BOOTSTRAP_STDLIB_MODULE_ORIGINS",
    }
)


def _literal_committed_bootstrap_constant_v42r1(
    value: ast.expr, *, name: str,
) -> Any:
    """Evaluate only literals and an exact ``str.encode('utf-8')`` wrapper."""

    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "encode"
        and isinstance(value.func.value, ast.Constant)
        and type(value.func.value.value) is str
        and len(value.args) == 1
        and isinstance(value.args[0], ast.Constant)
        and value.args[0].value == "utf-8"
        and not value.keywords
    ):
        return value.func.value.value.encode("utf-8")
    try:
        return ast.literal_eval(value)
    except (TypeError, ValueError) as error:
        raise V42RemoteOrdinal2BootstrapError(
            f"committed remote bootstrap constant is not an admitted literal: {name}"
        ) from error


def _committed_bootstrap_constants_v42r1(raw_authority: bytes) -> dict[str, Any]:
    try:
        tree = ast.parse(raw_authority.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, SyntaxError) as error:
        raise V42RemoteOrdinal2BootstrapError(
            "committed remote authority is not exact parseable UTF-8"
        ) from error
    expressions: dict[str, ast.expr] = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if (
            not isinstance(target, ast.Name)
            or target.id not in _COMMITTED_BOOTSTRAP_CONSTANT_NAMES
        ):
            continue
        if target.id in expressions:
            _fail("committed remote bootstrap constant was assigned more than once")
        expressions[target.id] = statement.value
    if set(expressions) != set(_COMMITTED_BOOTSTRAP_CONSTANT_NAMES):
        _fail("committed remote authority omitted a bootstrap trust constant")
    return {
        name: _literal_committed_bootstrap_constant_v42r1(expression, name=name)
        for name, expression in expressions.items()
    }


def _execution_manifest_from_commit(
    root: Path, *, source_commit: str
) -> dict[str, Any]:
    # Reuse only the already-audited static resolver.  The returned ordinal-1
    # document is transformed into a new ordinal-2 schema and content domain;
    # it is never accepted as ordinal-2 authority directly.
    from acfqp import construction_k7_standard_2048_execution_authority_v42 as frozen

    def hermetic_frozen_git(
        frozen_root: Path, *arguments: str, allow_failure: bool = False,
    ) -> bytes:
        completed = _run_hermetic_git_v42r1(frozen_root, *arguments)
        if completed.returncode != 0:
            if allow_failure:
                return b""
            _fail(
                "hermetic frozen resolver Git command failed: "
                + completed.stderr.decode("utf-8", errors="replace")[:4096]
            )
        return completed.stdout

    def hermetic_commit_path_exists(
        frozen_root: Path, commit: str, relative_path: str,
    ) -> bool:
        completed = _run_hermetic_git_v42r1(
            frozen_root, "cat-file", "-e", f"{commit}:{relative_path}"
        )
        return completed.returncode == 0

    original_git = frozen._git  # noqa: SLF001
    original_exists = frozen._commit_path_exists  # noqa: SLF001
    frozen._git = hermetic_frozen_git  # type: ignore[attr-defined]  # noqa: SLF001
    frozen._commit_path_exists = hermetic_commit_path_exists  # type: ignore[attr-defined]  # noqa: SLF001
    try:
        base = frozen.build_source_manifest_from_commit_v42(
            root,
            source_commit=source_commit,
            source_roots=authority.FORMAL_REMOTE_SOURCE_ROOTS,
        )
    finally:
        frozen._git = original_git  # type: ignore[attr-defined]  # noqa: SLF001
        frozen._commit_path_exists = original_exists  # type: ignore[attr-defined]  # noqa: SLF001
    facts = [
        {
            "relative_path": fact["relative_path"],
            "git_mode": fact["git_mode"],
            "git_object_type": fact["git_object_type"],
            "git_blob_oid": fact["git_blob_id"],
            "byte_count": fact["byte_count"],
            "sha256": fact["sha256"],
        }
        for fact in base["source_facts"]
    ]
    dynamic = [dict(site) for site in base["dynamic_import_sites"]]
    # The resolver intentionally inventories dynamic import calls.  Record
    # spec_from_file_location too if a future committed root introduces one.
    by_path = {fact["relative_path"]: fact for fact in facts}
    for relative in sorted(by_path):
        raw = _git(root, "show", f"{source_commit}:{relative}")
        try:
            tree = ast.parse(raw.decode("utf-8"), filename=relative)
        except (UnicodeDecodeError, SyntaxError) as error:
            raise V42RemoteOrdinal2BootstrapError(
                "ordinal-2 execution closure contains unparsable Python"
            ) from error
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "spec_from_file_location"
            ):
                dynamic.append(
                    {
                        "relative_path": relative,
                        "line": node.lineno,
                        "call": "spec_from_file_location",
                    }
                )
    dynamic.sort(key=lambda row: (row["relative_path"], row["line"], row["call"]))
    return authority.build_source_manifest_v42r1(
        source_commit=base["source_commit"],
        source_tree=base["source_tree"],
        source_facts=facts,
        source_roots=list(authority.FORMAL_REMOTE_SOURCE_ROOTS),
        dynamic_import_sites=dynamic,
    )


def _is_exact_direct_script_main_v42r1(
    *,
    module_name: str,
    origin: object,
    file_name: object,
    bootstrap_path: Path,
) -> bool:
    """Recognize CPython's one native direct-script ``__main__`` shape."""

    return (
        module_name == "__main__"
        and origin is None
        and file_name == str(bootstrap_path)
    )


def _verify_live_build_tcb_matches_commit_v42r1(
    root: Path,
    *,
    source_manifest: dict[str, Any],
    blobs: dict[str, bytes],
) -> dict[str, Any]:
    """Reject a mixed live-generator/committed-payload capsule before effects."""

    source_by_path = {
        fact["relative_path"]: fact for fact in source_manifest["source_facts"]
    }
    resolved_root = root.resolve(strict=True)
    bootstrap_path = Path(__file__)
    if (
        not bootstrap_path.is_absolute()
        or bootstrap_path.resolve(strict=True) != bootstrap_path
    ):
        _fail("live bootstrap builder source is redirected")
    observed_rows: list[tuple[str, str, str]] = []
    for module_name, module in sorted(sys.modules.items()):
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        file_name = getattr(module, "__file__", None)
        # CPython deliberately gives a directly executed script a null
        # ``__main__.__spec__``.  The exact isolated argv is checked before
        # this function, and the entry source is checked below, so recognize
        # only that one native direct-script shape here.  The already-fixed
        # bootstrap path is added below as ``__bootstrap_entry__`` and receives
        # the same no-follow/hash/Git-fact checks as every imported module.
        # Imported modules must still expose both origin and file values.
        if _is_exact_direct_script_main_v42r1(
            module_name=module_name,
            origin=origin,
            file_name=file_name,
            bootstrap_path=bootstrap_path,
        ):
            continue
        candidates = [value for value in (origin, file_name) if type(value) is str]
        repo_relative: str | None = None
        exact_origin: str | None = None
        for candidate in candidates:
            if candidate in {"built-in", "frozen"} or candidate.startswith("<"):
                continue
            path = Path(candidate)
            try:
                relative = path.relative_to(resolved_root).as_posix()
            except ValueError:
                continue
            if path.suffix in {".pyc", ".pyo"}:
                _fail("live repository build TCB loaded bytecode instead of exact source")
            repo_relative = relative
            exact_origin = str(path)
            break
        if repo_relative is None:
            continue
        if origin != exact_origin or file_name != exact_origin:
            _fail("live build TCB module origin or __file__ is not exact")
        observed_rows.append((module_name, repo_relative, exact_origin))
    bootstrap_relative = bootstrap_path.relative_to(resolved_root).as_posix()
    if not any(row[1] == bootstrap_relative for row in observed_rows):
        observed_rows.append(("__bootstrap_entry__", bootstrap_relative, str(bootstrap_path)))
    if not observed_rows:
        _fail("live build TCB inventory is empty")
    seen_paths: set[str] = set()
    for _module_name, relative, exact_origin in sorted(observed_rows):
        fact = source_by_path.get(relative)
        if fact is None:
            _fail("live repository module is absent from the committed source closure")
        path = Path(exact_origin)
        observed_before = path.lstat()
        if (
            not stat.S_ISREG(observed_before.st_mode)
            or observed_before.st_nlink != 1
            or stat.S_IMODE(observed_before.st_mode) not in {0o444, 0o644}
        ):
            _fail("live build TCB source mode or link count changed")
        raw = _read_regular_nofollow_capped(path, MAXIMUM_MEMBER_BYTES)
        observed_after = path.lstat()
        if _control_identity(observed_before) != _control_identity(observed_after):
            _fail("live build TCB source changed across verification")
        committed = blobs.get(fact["git_blob_oid"])
        if (
            committed is None
            or raw != committed
            or len(raw) != fact["byte_count"]
            or hashlib.sha256(raw).hexdigest() != fact["sha256"]
            or authority._git_blob_oid_sha1(raw) != fact["git_blob_oid"]  # noqa: SLF001
        ):
            _fail("live build TCB bytes differ from the selected committed source")
        seen_paths.add(relative)
    required_tcb_paths = {
        "scripts/bootstrap_v42_standard_2048_remote_ordinal2.py",
        "src/acfqp/construction_k7_standard_2048_execution_authority_v42.py",
        "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
        "src/acfqp/phase3e_ids.py",
    }
    if not required_tcb_paths.issubset(seen_paths):
        _fail("live build TCB omitted a required generator or resolver module")
    authority_relative = (
        "src/acfqp/"
        "construction_k7_standard_2048_remote_execution_authority_v42r1.py"
    )
    authority_fact = source_by_path.get(authority_relative)
    if authority_fact is None:
        _fail("committed source closure omitted the remote authority")
    raw_authority = blobs.get(authority_fact["git_blob_oid"])
    if raw_authority is None:
        _fail("committed remote authority blob is unavailable")
    committed_constants = _committed_bootstrap_constants_v42r1(raw_authority)
    for name, expected in committed_constants.items():
        observed = getattr(authority, name, None)
        if type(observed) is not type(expected) or observed != expected:
            _fail("live remote bootstrap trust constant differs from its commit: " + name)
    return committed_constants


def build_capsule_from_commit_v42r1(
    root: Path,
    *,
    source_commit: str,
    capsule_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create one local deterministic capsule from committed Git objects."""

    root = root.resolve()
    git_executable_identity = _verify_fixed_git_executable_v42r1()
    git_common_directory_identity = _verify_git_common_directory_v42r1(root)
    authority.verify_predecessor_retention_ready_v42r1(root)
    independently_verified_tree = _verify_hermetic_git_repository_v42r1(
        root, source_commit=source_commit
    )
    source_manifest = _execution_manifest_from_commit(root, source_commit=source_commit)
    source_tree, entries = _committed_inventory(root, source_commit)
    if (
        source_tree != source_manifest["source_tree"]
        or source_tree != independently_verified_tree
    ):
        _fail("capsule source tree differs from execution closure source tree")
    blobs = _read_blobs_batch(root, [entry["git_blob_oid"] for entry in entries])
    committed_bootstrap_constants = _verify_live_build_tcb_matches_commit_v42r1(
        root, source_manifest=source_manifest, blobs=blobs
    )
    archive_raw, transport_facts = _deterministic_ustar_bytes(entries, blobs)
    repeated_raw, repeated_facts = _deterministic_ustar_bytes(entries, blobs)
    if archive_raw != repeated_raw or transport_facts != repeated_facts:
        _fail("source capsule construction is not deterministic")
    pyz_raw, pyz_artifact = _deterministic_remote_bootstrap_pyz_bytes(
        entries, blobs,
        committed_bootstrap_constants=committed_bootstrap_constants,
    )
    repeated_pyz_raw, repeated_pyz_artifact = (
        _deterministic_remote_bootstrap_pyz_bytes(
            entries,
            blobs,
            committed_bootstrap_constants=committed_bootstrap_constants,
        )
    )
    if pyz_raw != repeated_pyz_raw or pyz_artifact != repeated_pyz_artifact:
        _fail("remote bootstrap pyz construction is not deterministic")
    transport_manifest = authority.build_transport_manifest_v42r1(
        source_manifest=source_manifest,
        transport_facts=transport_facts,
        source_archive_sha256=hashlib.sha256(archive_raw).hexdigest(),
        source_archive_byte_count=len(archive_raw),
        remote_bootstrap_pyz_artifact=pyz_artifact,
    )
    local_materialization_attempt = authority.build_local_materialization_attempt_v42r1(
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    if _verify_fixed_git_executable_v42r1() != git_executable_identity:
        _fail("fixed Git executable changed across complete capsule construction")
    if (
        _verify_git_common_directory_v42r1(root)
        != git_common_directory_identity
    ):
        _fail("capsule Git common directory changed across complete construction")
    _create_one_shot_directory(capsule_root)
    # This is the first durable child of the local capsule root.  A transport
    # implementation must require and copy these exact bytes before touching
    # the fixed remote identity.
    _write_once(
        capsule_root / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        canonical_json_bytes(local_materialization_attempt),
    )
    _write_once(capsule_root / authority.SOURCE_CAPSULE_NAME, archive_raw)
    _write_once(
        capsule_root / authority.SOURCE_MANIFEST_NAME,
        canonical_json_bytes(source_manifest),
    )
    _write_once(
        capsule_root / authority.TRANSPORT_MANIFEST_NAME,
        canonical_json_bytes(transport_manifest),
    )
    _write_once(capsule_root / authority.REMOTE_BOOTSTRAP_PYZ_NAME, pyz_raw)
    return source_manifest, transport_manifest


def _open_relative_parent(root_fd: int, parts: tuple[str, ...]) -> int:
    descriptor = os.dup(root_fd)
    try:
        for part in parts:
            created = False
            previous_umask = os.umask(0o077)
            try:
                try:
                    os.mkdir(part, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                else:
                    created = True
            finally:
                os.umask(previous_umask)
            if created:
                # Persist each newly linked directory in its then-current
                # parent before descending.  The caller fsyncs the deepest
                # parent after publishing the member, closing the full nested
                # directory durability chain rather than only the leaf.
                os.fsync(descriptor)
            child = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def materialize_capsule_v42r1(
    *,
    archive_raw: bytes,
    source_manifest_raw: bytes,
    transport_manifest_raw: bytes,
    target_root: Path,
    require_fixed_target: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Safely extract one exact regular-only capsule into an absent root."""

    source_manifest = authority.verify_source_manifest_v42r1(source_manifest_raw)
    transport_manifest = authority.verify_transport_manifest_v42r1(
        transport_manifest_raw, source_manifest=source_manifest
    )
    if (
        len(archive_raw) != transport_manifest["source_archive_byte_count"]
        or hashlib.sha256(archive_raw).hexdigest()
        != transport_manifest["source_archive_sha256"]
        or len(archive_raw) > MAXIMUM_CAPSULE_BYTES
    ):
        _fail("transported capsule bytes changed")
    if require_fixed_target:
        _fail(
            "direct fixed-target extraction is forbidden; formal materialization "
            "requires attempts and atomic no-replace publish"
        )
    expected = transport_manifest["transport_facts"]
    members: list[tuple[tarfile.TarInfo, bytes]] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_raw), mode="r:") as archive:
            for index, member in enumerate(archive):
                if index >= len(expected):
                    _fail("capsule contains an extra member")
                fact = expected[index]
                parsed = PurePosixPath(member.name)
                if (
                    member.name != fact["relative_path"]
                    or parsed.is_absolute()
                    or any(part in {"", ".", ".."} for part in parsed.parts)
                    or not member.isreg()
                    or member.mode != int(authority.MATERIALIZED_SOURCE_FILE_MODE, 8)
                    or member.uid != 0
                    or member.gid != 0
                    or member.uname != ""
                    or member.gname != ""
                    or member.mtime != 0
                    or member.size != fact["byte_count"]
                    or member.linkname != ""
                    or member.pax_headers
                ):
                    _fail("capsule member metadata changed or became unsafe")
                extracted = archive.extractfile(member)
                if extracted is None:
                    _fail("capsule regular member has no readable payload")
                raw = extracted.read(MAXIMUM_MEMBER_BYTES + 1)
                if (
                    len(raw) != fact["byte_count"]
                    or hashlib.sha256(raw).hexdigest() != fact["sha256"]
                    or authority._git_blob_oid_sha1(raw) != fact["git_blob_oid"]  # noqa: SLF001
                ):
                    _fail("capsule member bytes changed")
                members.append((member, raw))
    except (tarfile.TarError, EOFError) as error:
        raise V42RemoteOrdinal2BootstrapError("capsule tar stream is malformed") from error
    if len(members) != len(expected):
        _fail("capsule member inventory is incomplete")

    _create_one_shot_directory(target_root, expected_parent=target_root.parent)
    root_fd = os.open(
        target_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        for member, raw in members:
            parts = PurePosixPath(member.name).parts
            parent_fd = _open_relative_parent(root_fd, tuple(parts[:-1]))
            try:
                previous_umask = os.umask(0o077)
                try:
                    descriptor = os.open(
                        parts[-1],
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | os.O_NOFOLLOW
                        | os.O_CLOEXEC,
                        int(authority.MATERIALIZED_SOURCE_FILE_MODE, 8),
                        dir_fd=parent_fd,
                    )
                finally:
                    os.umask(previous_umask)
                try:
                    os.fchmod(
                        descriptor, int(authority.MATERIALIZED_SOURCE_FILE_MODE, 8)
                    )
                    view = memoryview(raw)
                    while view:
                        written = os.write(descriptor, view)
                        if written <= 0:
                            raise OSError("capsule member short write")
                        view = view[written:]
                    os.fchmod(
                        descriptor, int(authority.MATERIALIZED_SOURCE_FILE_MODE, 8)
                    )
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        os.fsync(root_fd)
    finally:
        os.close(root_fd)
    authority.verify_live_materialized_source_closure_v42r1(
        target_root,
        transport_manifest,
        source_manifest,
        require_fixed_root=False,
    )
    return source_manifest, transport_manifest


def _require_isolated_local_build_runtime_v42r1() -> None:
    processio.require_isolated_python()
    script_path = Path(__file__)
    expected_command = [
        LOCAL_BUILD_PYTHON,
        "-I",
        "-S",
        "-B",
        str(script_path),
        "--build-local-capsule",
    ]
    if (
        not script_path.is_absolute()
        or script_path.resolve(strict=True) != script_path
        or sys.executable != LOCAL_BUILD_PYTHON
        or os.path.realpath(sys.executable) != LOCAL_BUILD_PYTHON_REALPATH
        or tuple(sys.version_info[:3]) != LOCAL_BUILD_PYTHON_VERSION
        or list(sys.orig_argv) != expected_command
    ):
        _fail("local capsule build Python invocation or source origin changed")


def _build_local() -> int:
    _require_isolated_local_build_runtime_v42r1()
    _verify_fixed_git_executable_v42r1()
    git_common_directory_identity = _verify_git_common_directory_v42r1(ROOT)
    authority.verify_predecessor_retention_ready_v42r1(ROOT)
    source_commit = _git(ROOT, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
    if (
        _verify_git_common_directory_v42r1(ROOT)
        != git_common_directory_identity
    ):
        _fail("capsule Git common directory changed while selecting HEAD")
    capsule_root = ROOT / LOCAL_CAPSULE_ROOT_RELATIVE
    source_manifest, transport_manifest = build_capsule_from_commit_v42r1(
        ROOT, source_commit=source_commit, capsule_root=capsule_root
    )
    sys.stdout.buffer.write(
        canonical_json_bytes(
            {
                "local_materialization_attempt_id": (
                    authority.build_local_materialization_attempt_v42r1(
                        source_manifest=source_manifest,
                        transport_manifest=transport_manifest,
                    )["local_materialization_attempt_id"]
                ),
                "source_manifest_id": source_manifest["source_manifest_id"],
                "transport_manifest_id": transport_manifest["transport_manifest_id"],
                "formal_execution_performed": False,
                "network_command_executed": False,
            }
        )
        + b"\n"
    )
    return 0


def _verify_formal_remote_root(root: Path, *, require_fixed_path: bool) -> None:
    if require_fixed_path and root != authority.REMOTE_ROOT:
        _fail("formal materialization root differs from the fixed remote identity")
    root_observed = root.lstat()
    if (
        not stat.S_ISDIR(root_observed.st_mode)
        or stat.S_IMODE(root_observed.st_mode) != 0o700
        or root_observed.st_uid != authority.REMOTE_UID
        or not root.is_absolute()
        or root.resolve(strict=True) != root
    ):
        _fail("fixed remote capsule root is redirected, misowned, or has unsafe mode")


_LEXICAL_COMPONENT_IDENTITY_FIELDS = (
    "st_dev", "st_ino", "st_uid", "st_gid",
)
_LEXICAL_ROOT_STABLE_FIELDS = (
    "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size",
    "st_mtime_ns", "st_ctime_ns",
)


def _lexical_component_identity(observed: os.stat_result) -> tuple[int, ...]:
    """Bind path identity without unrelated sibling-directory timestamps."""

    return (
        *(getattr(observed, field) for field in _LEXICAL_COMPONENT_IDENTITY_FIELDS),
        observed.st_mode,
    )


def _open_lexical_directory_chain_nofollow(
    root: Path,
) -> tuple[str, tuple[tuple[str, tuple[int, ...]], ...], int | None]:
    """Open one absolute directory from ``/`` without following any component."""

    if not root.is_absolute() or root.anchor != "/":
        _fail("materialization classifier root must be one absolute POSIX path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open("/", flags)
    except OSError:
        return "UNOBSERVABLE", (), None
    facts: list[tuple[str, tuple[int, ...]]] = []
    transfer_descriptor = False
    try:
        anchor = os.fstat(descriptor)
        facts.append(("/", _lexical_component_identity(anchor)))
        components = root.parts[1:]
        prefix = ""
        for index, component in enumerate(components):
            prefix += "/" + component
            final = index == len(components) - 1
            try:
                observed = os.stat(
                    component, dir_fd=descriptor, follow_symlinks=False
                )
            except FileNotFoundError:
                return ("ABSENT" if final else "UNOBSERVABLE"), tuple(facts), None
            except OSError:
                return "UNOBSERVABLE", tuple(facts), None
            fact = _lexical_component_identity(observed)
            facts.append((prefix, fact))
            if not stat.S_ISDIR(observed.st_mode):
                if final:
                    state = (
                        "SYMLINK"
                        if stat.S_ISLNK(observed.st_mode)
                        else "REGULAR_FILE"
                        if stat.S_ISREG(observed.st_mode)
                        else "NONREGULAR"
                    )
                else:
                    state = "REDIRECTED_ANCESTOR"
                return state, tuple(facts), None
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except OSError:
                return "CHANGED_DURING_CLASSIFICATION", tuple(facts), None
            opened = os.fstat(child)
            if _lexical_component_identity(observed) != _lexical_component_identity(
                opened
            ):
                os.close(child)
                return "CHANGED_DURING_CLASSIFICATION", tuple(facts), None
            os.close(descriptor)
            descriptor = child
        transfer_descriptor = True
        return "DIRECTORY", tuple(facts), descriptor
    finally:
        # Ownership passes to the caller only for the successful DIRECTORY case.
        if not transfer_descriptor:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _formal_control_paths(root: Path) -> tuple[Path, Path, Path, Path, Path]:
    return (
        root / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        root / authority.SOURCE_CAPSULE_NAME,
        root / authority.SOURCE_MANIFEST_NAME,
        root / authority.TRANSPORT_MANIFEST_NAME,
        root / authority.REMOTE_BOOTSTRAP_PYZ_NAME,
    )


def _read_formal_controls(
    root: Path,
) -> tuple[
    bytes, bytes, bytes, bytes, bytes,
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
]:
    root_before = root.lstat()
    root_inventory = sorted(entry.name for entry in root.iterdir())
    (
        local_attempt_path,
        capsule_path,
        source_manifest_path,
        transport_manifest_path,
        pyz_path,
    ) = _formal_control_paths(root)
    archive_raw = _read_regular_nofollow_capped(
        capsule_path, MAXIMUM_CAPSULE_BYTES
    )
    source_raw = _read_regular_nofollow_capped(
        source_manifest_path, 64 * 1024 * 1024
    )
    transport_raw = _read_regular_nofollow_capped(
        transport_manifest_path, 64 * 1024 * 1024
    )
    local_attempt_raw = _read_regular_nofollow_capped(
        local_attempt_path, 4 * 1024 * 1024
    )
    pyz_raw = _read_regular_nofollow_capped(pyz_path, 64 * 1024 * 1024)
    source_manifest = authority.verify_source_manifest_v42r1(source_raw)
    transport_manifest = authority.verify_transport_manifest_v42r1(
        transport_raw, source_manifest=source_manifest
    )
    if (
        len(archive_raw) != transport_manifest["source_archive_byte_count"]
        or hashlib.sha256(archive_raw).hexdigest()
        != transport_manifest["source_archive_sha256"]
        or len(pyz_raw)
        != transport_manifest["remote_bootstrap_pyz_artifact"]["pyz_byte_count"]
        or hashlib.sha256(pyz_raw).hexdigest()
        != transport_manifest["remote_bootstrap_pyz_artifact"]["pyz_sha256"]
    ):
        _fail("formal transported capsule or bootstrap pyz bytes changed")
    local_attempt = authority.verify_local_materialization_attempt_v42r1(
        local_attempt_raw,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    control_identities: dict[str, list[int]] = {}
    for control_path in (
        local_attempt_path,
        capsule_path,
        source_manifest_path,
        transport_manifest_path,
        pyz_path,
    ):
        observed = control_path.lstat()
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o400
            or observed.st_uid != authority.REMOTE_UID
        ):
            _fail("fixed transported capsule artifact is misowned or has unsafe mode")
        control_identities[control_path.name] = list(_control_identity(observed))
    snapshot = {
        "root_identity": list(_control_identity(root_before)),
        "root_inventory": root_inventory,
        "control_identities": control_identities,
    }
    _verify_formal_control_snapshot(root, snapshot)
    return (
        local_attempt_raw,
        archive_raw,
        source_raw,
        transport_raw,
        pyz_raw,
        local_attempt,
        source_manifest,
        transport_manifest,
        snapshot,
    )


def _snapshot_full_lexical_chain_nofollow(root: Path) -> list[dict[str, Any]]:
    if not root.is_absolute() or root.anchor != "/":
        _fail("bootstrap evidence root is not one absolute POSIX path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open("/", flags)
    rows = [
        {
            "absolute_path": "/",
            "identity": list(_control_identity(os.fstat(descriptor))[:5]),
        }
    ]
    try:
        prefix = ""
        for component in root.parts[1:]:
            prefix += "/" + component
            before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                _fail("bootstrap evidence root ancestor is redirected")
            child = os.open(component, flags, dir_fd=descriptor)
            opened = os.fstat(child)
            if _control_identity(before)[:5] != _control_identity(opened)[:5]:
                os.close(child)
                _fail("bootstrap evidence root ancestor changed while opening")
            rows.append(
                {
                    "absolute_path": prefix,
                    "identity": list(_control_identity(opened)[:5]),
                }
            )
            os.close(descriptor)
            descriptor = child
        return rows
    finally:
        os.close(descriptor)


def _verify_launcher_evidence_live_snapshot_v42r1(
    evidence: dict[str, Any],
    *,
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
    local_materialization_attempt: dict[str, Any],
    control_snapshot: dict[str, Any],
) -> dict[str, Any]:
    verified = authority.verify_remote_bootstrap_launcher_evidence_v42r1(
        evidence,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
        local_materialization_attempt=local_materialization_attempt,
    )
    if (
        verified["outer_lexical_chain"]
        != _snapshot_full_lexical_chain_nofollow(authority.REMOTE_ROOT)
        or verified["outer_root_identity"] != control_snapshot["root_identity"]
        or verified["outer_root_inventory"] != control_snapshot["root_inventory"]
        or verified["outer_five_control_identities"]
        != control_snapshot["control_identities"]
    ):
        _fail("fixed five-control snapshot changed across trusted-launcher exec")
    _verify_formal_control_snapshot(authority.REMOTE_ROOT, control_snapshot)
    return verified


def read_verified_remote_bootstrap_controls_for_runtime_v42r1(
    trusted_launcher_evidence: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Join the sealed outer observation to a fresh inner no-follow read."""

    (
        _local_raw,
        _archive_raw,
        _source_raw,
        _transport_raw,
        _pyz_raw,
        local_attempt,
        source_manifest,
        transport_manifest,
        snapshot,
    ) = _read_formal_controls(authority.REMOTE_ROOT)
    if snapshot["root_inventory"] != sorted(
        path.name for path in _formal_control_paths(authority.REMOTE_ROOT)
    ):
        _fail("inner runtime did not observe the exact fixed five controls")
    _verify_launcher_evidence_live_snapshot_v42r1(
        trusted_launcher_evidence,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
        local_materialization_attempt=local_attempt,
        control_snapshot=snapshot,
    )
    return source_manifest, transport_manifest, local_attempt


def _path_state(path: Path) -> str:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return "ABSENT"
    if stat.S_ISDIR(observed.st_mode):
        return "DIRECTORY"
    return "NON_DIRECTORY"


def _embedded_terminal_state(staging_root: Path) -> str:
    if _path_state(staging_root) == "ABSENT":
        return "ABSENT"
    if _path_state(staging_root) != "DIRECTORY":
        return "UNOBSERVABLE"
    path = staging_root / authority.MATERIALIZATION_TERMINAL_NAME
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return "ABSENT"
    if stat.S_ISREG(observed.st_mode):
        return "REGULAR_FILE"
    return "NONREGULAR"


def _materialization_classification_document(
    *, local_materialization_attempt_id: str,
    remote_materialization_attempt_id: str | None,
    materialization_terminal_id: str | None,
    materialization_failure_id: str | None,
    classification: str, classification_reason: str,
    changed_or_absent_remote_control_names: list[str],
    extra_remote_entry_names: list[str], remote_root_state: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v42_remote_ordinal2_materialization_classification.v42r1",
        "schema_version": authority.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "local_materialization_attempt_id": local_materialization_attempt_id,
        "remote_materialization_attempt_id": remote_materialization_attempt_id,
        "materialization_terminal_id": materialization_terminal_id,
        "materialization_failure_id": materialization_failure_id,
        "classification": classification,
        "classification_reason": classification_reason,
        "changed_or_absent_remote_control_names": (
            changed_or_absent_remote_control_names
        ),
        "extra_remote_entry_names": extra_remote_entry_names,
        "remote_root_state": remote_root_state,
        "remote_path_mutated_by_classifier": False,
        "process_started_by_classifier": False,
        "same_identity_transport_or_materialization_retry_authorized": False,
        "only_read_only_followup_allowed": True,
    }
    return {
        **payload,
        "materialization_classification_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:materialization-classification\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def materialize_fixed_remote_capsule_once_v42r1(
    *, remote_root: Path, source_root: Path, require_fixed_paths: bool = True,
    remote_bootstrap_runtime_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform the sole fixed materialization attempt without any transport."""

    global _REMOTE_BOOTSTRAP_RUNTIME_BINDING
    global _REMOTE_BOOTSTRAP_RUNTIME_BINDING_INSTALLATION_CLOSED
    if require_fixed_paths and remote_root != authority.REMOTE_ROOT:
        _fail("formal materialization root differs from the fixed identity")
    if require_fixed_paths and source_root != authority.REMOTE_SOURCE_ROOT:
        _fail("formal materialization source target differs from the fixed identity")
    if source_root.parent != remote_root or source_root.name != "source":
        _fail("formal materialization source target changed")
    if require_fixed_paths and remote_bootstrap_runtime_binding is not None:
        _fail("formal materialization accepts only the sealed-inner installed binding")
    if require_fixed_paths:
        # Consuming this one-shot authority is the first action after validating
        # the fixed lexical parameters.  Every later failure (including an
        # absent or unsafe remote root) permanently closes in-process re-entry.
        runtime_binding = _REMOTE_BOOTSTRAP_RUNTIME_BINDING
        _REMOTE_BOOTSTRAP_RUNTIME_BINDING = None
        _REMOTE_BOOTSTRAP_RUNTIME_BINDING_INSTALLATION_CLOSED = True
    else:
        runtime_binding = remote_bootstrap_runtime_binding
    if runtime_binding is None:
        _fail("verified generated-main runtime binding is absent")
    _verify_formal_remote_root(remote_root, require_fixed_path=require_fixed_paths)
    (
        _local_attempt_raw,
        archive_raw,
        source_raw,
        transport_raw,
        _pyz_raw,
        local_attempt,
        source_manifest,
        transport_manifest,
        control_snapshot,
    ) = _read_formal_controls(remote_root)
    staging_name = authority.materialization_staging_name_v42r1(
        local_attempt["local_materialization_attempt_id"]
    )
    staging_root = remote_root / staging_name
    allowed_initial = {path.name for path in _formal_control_paths(remote_root)}
    observed_initial = {path.name for path in remote_root.iterdir()}
    if observed_initial != allowed_initial:
        _fail("formal remote transport inventory has an extra, missing, or prior-attempt entry")
    if _path_state(source_root) != "ABSENT" or _path_state(staging_root) != "ABSENT":
        _fail("formal source or staging identity already exists; retry is forbidden")
    runtime_binding = authority.verify_remote_bootstrap_runtime_binding_v42r1(
        runtime_binding,
        transport_manifest=transport_manifest,
        source_manifest=source_manifest,
        local_materialization_attempt=local_attempt,
    )
    _verify_launcher_evidence_live_snapshot_v42r1(
        runtime_binding["trusted_launcher_evidence"],
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
        local_materialization_attempt=local_attempt,
        control_snapshot=control_snapshot,
    )
    remote_attempt = authority.build_remote_materialization_attempt_v42r1(
        local_materialization_attempt=local_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
        remote_bootstrap_runtime_binding=runtime_binding,
    )
    _verify_formal_control_snapshot(remote_root, control_snapshot)
    stage = "REMOTE_ATTEMPT_PUBLICATION"
    attempt_published = False
    try:
        # The first remote mutation made by formal materialization.
        processio.write_once(
            remote_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
            canonical_json_bytes(remote_attempt),
        )
        attempt_published = True
        stage = "STAGING_EXTRACTION"
        materialize_capsule_v42r1(
            archive_raw=archive_raw,
            source_manifest_raw=source_raw,
            transport_manifest_raw=transport_raw,
            target_root=staging_root,
            require_fixed_target=False,
        )
        stage = "STAGING_TERMINAL_PUBLICATION"
        terminal = authority.build_materialization_terminal_v42r1(
            local_materialization_attempt=local_attempt,
            remote_materialization_attempt=remote_attempt,
            source_manifest=source_manifest,
            transport_manifest=transport_manifest,
        )
        processio.write_once(
            staging_root / authority.MATERIALIZATION_TERMINAL_NAME,
            canonical_json_bytes(terminal),
        )
        authority.verify_live_materialized_source_closure_v42r1(
            staging_root,
            transport_manifest,
            source_manifest,
            require_fixed_root=False,
            local_materialization_attempt=local_attempt,
            remote_materialization_attempt=remote_attempt,
            materialization_terminal=terminal,
        )
        if _path_state(source_root) != "ABSENT":
            _fail("formal source target appeared before atomic no-replace publish")
        stage = "ATOMIC_SOURCE_PUBLISH"
        processio.rename_noreplace(remote_root, staging_name, source_root.name)
        # A post-disconnect observer can prove this success from the terminal
        # that moved atomically with the already-verified directory.
        authority.verify_fixed_materialization_success_v42r1(
            source_root, transport_manifest, source_manifest
        )
        return terminal
    except Exception as error:
        if attempt_published and _path_state(source_root) == "ABSENT":
            failure = authority.build_materialization_failure_v42r1(
                local_materialization_attempt=local_attempt,
                remote_materialization_attempt=remote_attempt,
                source_manifest=source_manifest,
                transport_manifest=transport_manifest,
                failure_stage=stage,
                failure_type=type(error).__name__,
                failure_message=processio.bounded_message(error),
                source_state_after_failure=_path_state(source_root),
                staging_state_after_failure=_path_state(staging_root),
                embedded_terminal_state_after_failure=_embedded_terminal_state(
                    staging_root
                ),
            )
            try:
                processio.write_once(
                    remote_root / authority.MATERIALIZATION_FAILURE_NAME,
                    canonical_json_bytes(failure),
                )
            except Exception as publication_error:
                raise V42RemoteOrdinal2BootstrapError(
                    processio.bounded_message(
                        f"materialization failed and typed failure publication failed: "
                        f"{type(publication_error).__name__}: {publication_error}"
                    )
                ) from error
        raise


def _classify_materialization_read_only_impl_v42r1(
    *,
    remote_root: Path,
    expected_local_attempt_raw: bytes,
    expected_archive_raw: bytes,
    expected_source_manifest_raw: bytes,
    expected_transport_manifest_raw: bytes,
    require_fixed_paths: bool = True,
    _owned_descriptors: list[int],
) -> dict[str, Any]:
    """Classify one synchronized root without creating, deleting, or rewriting it."""

    source_manifest = authority.verify_source_manifest_v42r1(
        expected_source_manifest_raw
    )
    transport_manifest = authority.verify_transport_manifest_v42r1(
        expected_transport_manifest_raw, source_manifest=source_manifest
    )
    if (
        len(expected_archive_raw) != transport_manifest["source_archive_byte_count"]
        or hashlib.sha256(expected_archive_raw).hexdigest()
        != transport_manifest["source_archive_sha256"]
    ):
        _fail("expected local capsule bytes changed")
    local_attempt = authority.verify_local_materialization_attempt_v42r1(
        expected_local_attempt_raw,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    expected_controls = {
        authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME: expected_local_attempt_raw,
        authority.SOURCE_CAPSULE_NAME: expected_archive_raw,
        authority.SOURCE_MANIFEST_NAME: expected_source_manifest_raw,
        authority.TRANSPORT_MANIFEST_NAME: expected_transport_manifest_raw,
        authority.REMOTE_BOOTSTRAP_PYZ_NAME: None,
    }
    if require_fixed_paths and remote_root != authority.REMOTE_ROOT:
        _fail("materialization classifier root differs from the fixed remote identity")
    if not remote_root.is_absolute():
        _fail("materialization classifier root must be lexical absolute")

    def closed_root_document(*, state: str, reason: str) -> dict[str, Any]:
        return _materialization_classification_document(
            local_materialization_attempt_id=local_attempt[
                "local_materialization_attempt_id"
            ],
            remote_materialization_attempt_id=None,
            materialization_terminal_id=None,
            materialization_failure_id=None,
            classification="AMBIGUOUS_PERMANENTLY_CLOSED",
            classification_reason=reason,
            changed_or_absent_remote_control_names=sorted(expected_controls),
            extra_remote_entry_names=[],
            remote_root_state=state,
        )

    initial_root_state, lexical_chain_before, root_descriptor = (
        _open_lexical_directory_chain_nofollow(remote_root)
    )
    if initial_root_state != "DIRECTORY":
        final_state, lexical_chain_after, final_descriptor = (
            _open_lexical_directory_chain_nofollow(remote_root)
        )
        if final_descriptor is not None:
            os.close(final_descriptor)
        if (
            final_state != initial_root_state
            or lexical_chain_after != lexical_chain_before
        ):
            return closed_root_document(
                state="CHANGED_DURING_CLASSIFICATION",
                reason="REMOTE_ROOT_CHANGED_DURING_LSTAT_ONLY_CLASSIFICATION",
            )
        return closed_root_document(
            state=initial_root_state,
            reason=(
                "FIXED_REMOTE_ROOT_ABSENT_AFTER_LOCAL_MATERIALIZATION_ATTEMPT"
                if initial_root_state == "ABSENT"
                else f"FIXED_REMOTE_ROOT_{initial_root_state}_AFTER_"
                "LOCAL_MATERIALIZATION_ATTEMPT"
            ),
        )
    if root_descriptor is None:
        return closed_root_document(
            state="UNOBSERVABLE",
            reason="REMOTE_ROOT_UNOBSERVABLE_DURING_LSTAT_ONLY_CLASSIFICATION",
        )
    _owned_descriptors.append(root_descriptor)
    initial_root = os.fstat(root_descriptor)
    expected_root_uid = authority.REMOTE_UID if require_fixed_paths else os.geteuid()
    unsafe_root_state: str | None = None
    if (
        stat.S_IMODE(initial_root.st_mode) != 0o700
        and initial_root.st_uid != expected_root_uid
    ):
        unsafe_root_state = "DIRECTORY_UNSAFE_MODE_AND_UID"
    elif stat.S_IMODE(initial_root.st_mode) != 0o700:
        unsafe_root_state = "DIRECTORY_UNSAFE_MODE"
    elif initial_root.st_uid != expected_root_uid:
        unsafe_root_state = "DIRECTORY_UNEXPECTED_UID"
    if unsafe_root_state is not None:
        final_state, lexical_chain_after, final_descriptor = (
            _open_lexical_directory_chain_nofollow(remote_root)
        )
        if final_descriptor is not None:
            final_root = os.fstat(final_descriptor)
            os.close(final_descriptor)
        else:
            final_root = None
        if (
            final_state != "DIRECTORY"
            or lexical_chain_after != lexical_chain_before
            or final_root is None
            or any(
                getattr(initial_root, field) != getattr(final_root, field)
                for field in _LEXICAL_ROOT_STABLE_FIELDS
            )
        ):
            return closed_root_document(
                state="CHANGED_DURING_CLASSIFICATION",
                reason="REMOTE_ROOT_CHANGED_DURING_LSTAT_ONLY_CLASSIFICATION",
            )
        return closed_root_document(
            state=unsafe_root_state,
            reason=(
                f"FIXED_REMOTE_ROOT_{unsafe_root_state}_AFTER_"
                "LOCAL_MATERIALIZATION_ATTEMPT"
            ),
        )
    scan_root = Path(f"/proc/self/fd/{root_descriptor}")
    staging_name = authority.materialization_staging_name_v42r1(
        local_attempt["local_materialization_attempt_id"]
    )
    allowed_remote_names = {
        *expected_controls,
        authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
        authority.MATERIALIZATION_FAILURE_NAME,
        "source",
        staging_name,
    }
    try:
        root_before = os.fstat(root_descriptor)
        observed_names_before = set(os.listdir(root_descriptor))
        remote_tree_before = authority._snapshot_transport_tree_metadata_v42r1(  # noqa: SLF001
            scan_root
        )
    except Exception:
        return closed_root_document(
            state="DIRECTORY",
            reason="REMOTE_ROOT_UNOBSERVABLE_DURING_INITIAL_SNAPSHOT",
        )
    tree_owner_mismatch = any(
        fact[3] != expected_root_uid for fact in remote_tree_before.values()
    )
    extra_names = sorted(observed_names_before - allowed_remote_names)
    mismatches: list[str] = []
    for name, expected_raw in expected_controls.items():
        path = scan_root / name
        try:
            raw = _read_regular_nofollow_capped(
                path,
                MAXIMUM_CAPSULE_BYTES
                if name == authority.SOURCE_CAPSULE_NAME
                else 64 * 1024 * 1024,
            )
        except (FileNotFoundError, OSError, V42RemoteOrdinal2BootstrapError):
            mismatches.append(name)
            continue
        if expected_raw is None:
            pyz = transport_manifest["remote_bootstrap_pyz_artifact"]
            matches_expected = (
                len(raw) == pyz["pyz_byte_count"]
                and hashlib.sha256(raw).hexdigest() == pyz["pyz_sha256"]
            )
        else:
            matches_expected = raw == expected_raw
        if not matches_expected:
            mismatches.append(name)
            continue
        observed = path.lstat()
        if (
            stat.S_IMODE(observed.st_mode) != 0o400
            or require_fixed_paths and observed.st_uid != authority.REMOTE_UID
        ):
            mismatches.append(name)

    remote_attempt: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None
    terminal: dict[str, Any] | None = None
    classification = "AMBIGUOUS_PERMANENTLY_CLOSED"
    reason = "REMOTE_CONTROL_INVENTORY_INCOMPLETE_OR_CHANGED"
    if extra_names:
        reason = "REMOTE_ROOT_HAS_UNRECOGNIZED_ENTRY"
    elif tree_owner_mismatch:
        reason = "REMOTE_ROOT_TREE_HAS_UNEXPECTED_OWNER"
    elif not mismatches:
        try:
            remote_attempt_raw = _read_regular_nofollow_capped(
                scan_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
                4 * 1024 * 1024,
            )
        except FileNotFoundError:
            reason = "REMOTE_ATTEMPT_NOT_OBSERVED_AFTER_LOCAL_TRANSPORT_ATTEMPT"
        except (OSError, V42RemoteOrdinal2BootstrapError, ValueError):
            reason = "REMOTE_ATTEMPT_INVALID_OR_UNREADABLE"
        else:
            try:
                remote_attempt_observed = (
                    scan_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME
                ).lstat()
                if (
                    stat.S_IMODE(remote_attempt_observed.st_mode) != 0o400
                    or require_fixed_paths
                    and remote_attempt_observed.st_uid != authority.REMOTE_UID
                ):
                    raise V42RemoteOrdinal2BootstrapError(
                        "remote materialization attempt mode or owner changed"
                    )
                remote_attempt = authority.verify_remote_materialization_attempt_v42r1(
                    remote_attempt_raw,
                    local_materialization_attempt=local_attempt,
                    source_manifest=source_manifest,
                    transport_manifest=transport_manifest,
                )
            except (OSError, ValueError, V42RemoteOrdinal2BootstrapError):
                remote_attempt = None
                reason = "REMOTE_ATTEMPT_INVALID_OR_UNREADABLE"
            if remote_attempt is not None:
                source_root = scan_root / "source"
                staging_root = scan_root / remote_attempt["staging_relative_name"]
                source_state = _path_state(source_root)
                try:
                    failure_raw = _read_regular_nofollow_capped(
                        scan_root / authority.MATERIALIZATION_FAILURE_NAME,
                        4 * 1024 * 1024,
                    )
                except FileNotFoundError:
                    failure = None
                except (OSError, V42RemoteOrdinal2BootstrapError, ValueError):
                    failure = None
                    reason = "MATERIALIZATION_FAILURE_INVALID_OR_UNREADABLE"
                else:
                    try:
                        failure_observed = (
                            scan_root / authority.MATERIALIZATION_FAILURE_NAME
                        ).lstat()
                        if (
                            stat.S_IMODE(failure_observed.st_mode) != 0o400
                            or require_fixed_paths
                            and failure_observed.st_uid != authority.REMOTE_UID
                        ):
                            raise V42RemoteOrdinal2BootstrapError(
                                "materialization failure mode or owner changed"
                            )
                        failure = authority.verify_materialization_failure_v42r1(
                            failure_raw,
                            local_materialization_attempt=local_attempt,
                            remote_materialization_attempt=remote_attempt,
                            source_manifest=source_manifest,
                            transport_manifest=transport_manifest,
                        )
                    except (OSError, ValueError, V42RemoteOrdinal2BootstrapError):
                        failure = None
                        reason = "MATERIALIZATION_FAILURE_INVALID_OR_UNREADABLE"
                if (
                    source_state == "DIRECTORY"
                    and failure is None
                    and reason != "MATERIALIZATION_FAILURE_INVALID_OR_UNREADABLE"
                ):
                    source_descriptor: int | None = None
                    try:
                        source_descriptor = os.open(
                            "source",
                            os.O_RDONLY
                            | os.O_DIRECTORY
                            | os.O_NOFOLLOW
                            | os.O_CLOEXEC,
                            dir_fd=root_descriptor,
                        )
                        source_observed = os.fstat(source_descriptor)
                        pinned_source_root = Path(
                            f"/proc/self/fd/{source_descriptor}"
                        )
                        terminal_raw = _read_regular_nofollow_capped(
                            pinned_source_root
                            / authority.MATERIALIZATION_TERMINAL_NAME,
                            4 * 1024 * 1024,
                        )
                        terminal_observed = (
                            pinned_source_root
                            / authority.MATERIALIZATION_TERMINAL_NAME
                        ).lstat()
                        if (
                            stat.S_IMODE(terminal_observed.st_mode) != 0o400
                            or stat.S_IMODE(source_observed.st_mode) != 0o700
                            or require_fixed_paths
                            and (
                                terminal_observed.st_uid != authority.REMOTE_UID
                                or source_observed.st_uid != authority.REMOTE_UID
                            )
                        ):
                            raise V42RemoteOrdinal2BootstrapError(
                                "published source or terminal mode/owner changed"
                            )
                        terminal = authority.verify_materialization_terminal_v42r1(
                            terminal_raw,
                            local_materialization_attempt=local_attempt,
                            remote_materialization_attempt=remote_attempt,
                            source_manifest=source_manifest,
                            transport_manifest=transport_manifest,
                        )
                        authority.verify_live_materialized_source_closure_v42r1(
                            pinned_source_root,
                            transport_manifest,
                            source_manifest,
                            require_fixed_root=False,
                            pinned_root_descriptor=source_descriptor,
                            local_materialization_attempt=local_attempt,
                            remote_materialization_attempt=remote_attempt,
                            materialization_terminal=terminal,
                        )
                        source_after = os.stat(
                            "source",
                            dir_fd=root_descriptor,
                            follow_symlinks=False,
                        )
                        if any(
                            getattr(source_observed, field)
                            != getattr(source_after, field)
                            for field in _LEXICAL_ROOT_STABLE_FIELDS
                        ):
                            raise V42RemoteOrdinal2BootstrapError(
                                "published source changed across pinned verification"
                            )
                    except Exception:
                        reason = "PUBLISHED_SOURCE_OR_EMBEDDED_TERMINAL_INVALID"
                    else:
                        expected_success_names = {
                            *expected_controls,
                            authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
                            "source",
                        }
                        if (
                            _path_state(staging_root) == "ABSENT"
                            and observed_names_before == expected_success_names
                        ):
                            classification = "COMPLETE_SUCCESS"
                            reason = "EMBEDDED_TERMINAL_AND_PUBLISHED_SOURCE_VERIFIED"
                        else:
                            reason = "PUBLISHED_SOURCE_ROOT_INVENTORY_IS_NOT_EXACT"
                    finally:
                        if source_descriptor is not None:
                            os.close(source_descriptor)
                elif source_state == "ABSENT" and failure is not None:
                    staging_state = _path_state(staging_root)
                    embedded_state = _embedded_terminal_state(staging_root)
                    expected_failure_names = {
                        *expected_controls,
                        authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
                        authority.MATERIALIZATION_FAILURE_NAME,
                    }
                    if staging_state != "ABSENT":
                        expected_failure_names.add(staging_root.name)
                    if (
                        failure["source_state_after_failure"] == source_state
                        and failure["staging_state_after_failure"] == staging_state
                        and failure["embedded_terminal_state_after_failure"]
                        == embedded_state
                        and observed_names_before == expected_failure_names
                        and (
                            staging_state != "DIRECTORY"
                            or (
                                stat.S_IMODE(staging_root.lstat().st_mode) == 0o700
                                and (
                                    not require_fixed_paths
                                    or staging_root.lstat().st_uid == authority.REMOTE_UID
                                )
                            )
                        )
                    ):
                        classification = "COMPLETE_FAILURE"
                        reason = "TYPED_REMOTE_FAILURE_AND_ROOT_INVENTORY_VERIFIED"
                    else:
                        reason = "TYPED_REMOTE_FAILURE_STATE_OR_ROOT_INVENTORY_CHANGED"
                elif reason != "MATERIALIZATION_FAILURE_INVALID_OR_UNREADABLE":
                    reason = "REMOTE_ATTEMPT_HAS_NO_UNAMBIGUOUS_TERMINAL_STATE"
    try:
        root_after = os.fstat(root_descriptor)
        observed_names_after = set(os.listdir(root_descriptor))
        remote_tree_after = authority._snapshot_transport_tree_metadata_v42r1(  # noqa: SLF001
            scan_root
        )
    except Exception:
        classification = "AMBIGUOUS_PERMANENTLY_CLOSED"
        reason = "REMOTE_ROOT_UNOBSERVABLE_DURING_FINAL_SNAPSHOT"
    else:
        if (
            observed_names_after != observed_names_before
            or remote_tree_after != remote_tree_before
            or any(
                getattr(root_before, field) != getattr(root_after, field)
                for field in _LEXICAL_ROOT_STABLE_FIELDS
            )
        ):
            classification = "AMBIGUOUS_PERMANENTLY_CLOSED"
            reason = "REMOTE_TREE_CHANGED_DURING_READ_ONLY_CLASSIFICATION"
    final_root_state, lexical_chain_after, final_descriptor = (
        _open_lexical_directory_chain_nofollow(remote_root)
    )
    if final_descriptor is not None:
        final_lexical_root = os.fstat(final_descriptor)
        os.close(final_descriptor)
    else:
        final_lexical_root = None
    if (
        final_root_state != "DIRECTORY"
        or lexical_chain_after != lexical_chain_before
        or final_lexical_root is None
        or any(
            getattr(root_before, field) != getattr(final_lexical_root, field)
            for field in _LEXICAL_ROOT_STABLE_FIELDS
        )
    ):
        classification = "AMBIGUOUS_PERMANENTLY_CLOSED"
        reason = "REMOTE_ROOT_OR_ANCESTOR_CHANGED_DURING_CLASSIFICATION"
    return _materialization_classification_document(
        local_materialization_attempt_id=local_attempt[
            "local_materialization_attempt_id"
        ],
        remote_materialization_attempt_id=(
            None
            if remote_attempt is None
            else remote_attempt["remote_materialization_attempt_id"]
        ),
        materialization_terminal_id=(
            None if terminal is None else terminal["materialization_terminal_id"]
        ),
        materialization_failure_id=(
            None if failure is None else failure["materialization_failure_id"]
        ),
        classification=classification,
        classification_reason=reason,
        changed_or_absent_remote_control_names=sorted(mismatches),
        extra_remote_entry_names=extra_names,
        remote_root_state="DIRECTORY",
    )


def classify_materialization_read_only_v42r1(
    *,
    remote_root: Path,
    expected_local_attempt_raw: bytes,
    expected_archive_raw: bytes,
    expected_source_manifest_raw: bytes,
    expected_transport_manifest_raw: bytes,
    require_fixed_paths: bool = True,
) -> dict[str, Any]:
    """Classify a mirror and always close every pinned descriptor on a race."""

    owned_descriptors: list[int] = []
    try:
        return _classify_materialization_read_only_impl_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=expected_local_attempt_raw,
            expected_archive_raw=expected_archive_raw,
            expected_source_manifest_raw=expected_source_manifest_raw,
            expected_transport_manifest_raw=expected_transport_manifest_raw,
            require_fixed_paths=require_fixed_paths,
            _owned_descriptors=owned_descriptors,
        )
    except Exception:
        if not owned_descriptors:
            raise
        source_manifest = authority.verify_source_manifest_v42r1(
            expected_source_manifest_raw
        )
        transport_manifest = authority.verify_transport_manifest_v42r1(
            expected_transport_manifest_raw, source_manifest=source_manifest
        )
        local_attempt = authority.verify_local_materialization_attempt_v42r1(
            expected_local_attempt_raw,
            source_manifest=source_manifest,
            transport_manifest=transport_manifest,
        )
        return _materialization_classification_document(
            local_materialization_attempt_id=local_attempt[
                "local_materialization_attempt_id"
            ],
            remote_materialization_attempt_id=None,
            materialization_terminal_id=None,
            materialization_failure_id=None,
            classification="AMBIGUOUS_PERMANENTLY_CLOSED",
            classification_reason=(
                "REMOTE_OBSERVATION_RACE_OR_IO_FAILURE_DURING_CLASSIFICATION"
            ),
            changed_or_absent_remote_control_names=sorted(
                {
                    authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
                    authority.SOURCE_CAPSULE_NAME,
                    authority.SOURCE_MANIFEST_NAME,
                    authority.TRANSPORT_MANIFEST_NAME,
                    authority.REMOTE_BOOTSTRAP_PYZ_NAME,
                }
            ),
            extra_remote_entry_names=[],
            remote_root_state="UNOBSERVABLE",
        )
    finally:
        for descriptor in owned_descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _materialize_remote() -> int:
    processio.require_isolated_python()
    terminal = materialize_fixed_remote_capsule_once_v42r1(
        remote_root=authority.REMOTE_ROOT,
        source_root=authority.REMOTE_SOURCE_ROOT,
        require_fixed_paths=True,
    )
    sys.stdout.buffer.write(canonical_json_bytes(terminal) + b"\n")
    return 0


def _classify_mirror(mirror_root: Path | None) -> int:
    if mirror_root is None:
        _fail("read-only materialization classification requires one mirror root")
    if not mirror_root.is_absolute():
        mirror_root = Path(os.path.abspath(mirror_root))
    local_root = ROOT / LOCAL_CAPSULE_ROOT_RELATIVE
    local_attempt_raw = _read_regular_nofollow_capped(
        local_root / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        4 * 1024 * 1024,
    )
    archive_raw = _read_regular_nofollow_capped(
        local_root / authority.SOURCE_CAPSULE_NAME, MAXIMUM_CAPSULE_BYTES
    )
    source_raw = _read_regular_nofollow_capped(
        local_root / authority.SOURCE_MANIFEST_NAME, 64 * 1024 * 1024
    )
    transport_raw = _read_regular_nofollow_capped(
        local_root / authority.TRANSPORT_MANIFEST_NAME, 64 * 1024 * 1024
    )
    classification = classify_materialization_read_only_v42r1(
        remote_root=mirror_root,
        expected_local_attempt_raw=local_attempt_raw,
        expected_archive_raw=archive_raw,
        expected_source_manifest_raw=source_raw,
        expected_transport_manifest_raw=transport_raw,
        require_fixed_paths=False,
    )
    sys.stdout.buffer.write(canonical_json_bytes(classification) + b"\n")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or safely materialize the fixed V42 remote ordinal-2 capsule"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build-local-capsule", action="store_true")
    modes.add_argument("--materialize-remote-capsule", action="store_true")
    modes.add_argument("--classify-materialization-mirror-read-only", action="store_true")
    parser.add_argument("--remote-mirror-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.build_local_capsule:
        if arguments.remote_mirror_root is not None:
            _fail("local capsule build accepts no remote mirror")
        return _build_local()
    if arguments.materialize_remote_capsule:
        if arguments.remote_mirror_root is not None:
            _fail("formal materialization accepts no local mirror")
        return _materialize_remote()
    return _classify_mirror(arguments.remote_mirror_root)


if __name__ == "__main__":
    raise SystemExit(main())
