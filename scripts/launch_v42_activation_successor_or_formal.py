#!/bin/sh
'''exec' /usr/bin/env -i LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=/usr/bin:/bin /usr/bin/python3 -I -S -B "$(/usr/bin/readlink -f "$0")" "$@"
' '''
from __future__ import annotations

"""Source-only entry for the V42r2 successor inspection and formal adapter.

The activated remote payload remains the frozen V42r1/942 tree.  This entry
therefore verifies a separate committed controller source manifest for the
new local successor TCB and never asks the V42r1 control capsule to authorize
new code.
"""

import argparse
from collections.abc import Sequence
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
SCRIPT_PATH = Path(__file__).resolve()
GIT = "/usr/bin/git"
GIT_SHA256 = (
    "587ef21868c948b883993e23209b86a72a6ddc06aab1545c697ffc31075acd4a"
)
GIT_BYTE_COUNT = 3_710_360
EXACT_ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
}


def _require_early_isolated_runtime() -> None:
    expected_script = os.path.realpath(__file__)
    if (
        sys.executable != "/usr/bin/python3"
        or os.path.realpath(sys.executable) != "/usr/bin/python3.10"
        or tuple(sys.version_info[:3]) != (3, 10, 12)
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
        or sys.gettrace() is not None
        or sys.getprofile() is not None
        or sys.orig_argv
        != [
            "/usr/bin/python3", "-I", "-S", "-B", expected_script,
            *sys.argv[1:],
        ]
        or sys.path
        != [
            "/usr/lib/python310.zip", "/usr/lib/python3.10",
            "/usr/lib/python3.10/lib-dynload",
        ]
        or dict(os.environ) != EXACT_ENVIRONMENT
        or getattr(getattr(os, "__spec__", None), "origin", None)
        != "/usr/lib/python3.10/os.py"
    ):
        raise RuntimeError("successor launcher isolated Python entry changed")


if __name__ == "__main__":
    _require_early_isolated_runtime()

TCB_PATHS = (
    "scripts/__init__.py",
    "scripts/launch_v42_activation_successor_or_formal.py",
    "scripts/launch_v42_preformal_upload_sender.py",
    "scripts/publish_v42_preformal_upload_journal.py",
    "scripts/run_v42_activation_successor_finalizer.py",
    "scripts/run_v42_materialization_activation.py",
    "scripts/run_v42_preformal_upload_sender.py",
    "scripts/run_v42_standard_2048_formal_transport_driver.py",
    "scripts/run_v42_standard_2048_formal_transport_successor_driver.py",
    "scripts/run_v42_standard_2048_remote_ordinal2.py",
    "scripts/v42_activation_successor_loader.py",
    "scripts/v42_activation_successor_receiver.py",
    "src/acfqp/__init__.py",
    "src/acfqp/artifacts.py",
    "src/acfqp/build_coverage.py",
    "src/acfqp/construction_k7_domain_registry_extension_v42.py",
    "src/acfqp/construction_k7_standard_2048_activation_successor_v42r2.py",
    "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
    "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
    "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
    "src/acfqp/core.py",
    "src/acfqp/enumeration.py",
    "src/acfqp/phase3e_ids.py",
)
CONTROLLER_SOURCE_MANIFEST_NAME = "ACTIVATION_SUCCESSOR_SOURCE_MANIFEST.json"
FINAL_INDEX_NAME = "ACTIVATION_SUCCESSOR_FINAL_EVIDENCE_INDEX.json"

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
FORMAL_MODES = (
    "--probe-host-epoch",
    "--prepare-once",
    "--admit-launch-once",
    "--inspect-prepare",
    "--inspect-launch",
)


class V42ActivationSuccessorLauncherError(RuntimeError):
    """The committed successor source boundary changed."""


def _fail(message: str) -> NoReturn:
    raise V42ActivationSuccessorLauncherError(message)


def _absolute(value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or not path.name:
        _fail(label + " path changed")
    return path


def _read_source(relative: str, cap: int = 8 * 1024**2) -> bytes:
    parsed = PurePosixPath(relative)
    if (
        parsed.is_absolute()
        or parsed.as_posix() != relative
        or any(part in {"", ".", ".."} for part in parsed.parts)
    ):
        _fail("successor source relative path changed")
    path = ROOT.joinpath(*parsed.parts)
    before = path.lstat()
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
        | os.O_CLOEXEC,
    )
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o644
            or opened.st_uid != os.geteuid()
            or opened.st_gid != os.getegid()
            or opened.st_nlink != 1
            or not 0 < opened.st_size <= cap
            or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
        ):
            _fail("successor source storage changed: " + relative)
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("successor source ended early: " + relative)
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("successor source grew while read: " + relative)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = path.lstat()
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(opened, field) != getattr(after, field)
        or getattr(after, field) != getattr(final, field)
        for field in fields
    ):
        _fail("successor source changed while read: " + relative)
    return b"".join(chunks)


def _run_git(*arguments: str) -> bytes:
    named = os.lstat(GIT)
    descriptor = os.open(GIT, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o755
            or opened.st_uid != 0
            or opened.st_gid != 0
            or opened.st_nlink != 1
            or opened.st_size != GIT_BYTE_COUNT
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("fixed Git executable storage changed")
        digest = hashlib.sha256()
        offset = 0
        while offset < opened.st_size:
            chunk = os.pread(
                descriptor, min(1024 * 1024, opened.st_size - offset), offset
            )
            if not chunk:
                _fail("fixed Git executable ended early")
            digest.update(chunk)
            offset += len(chunk)
        if digest.hexdigest() != GIT_SHA256:
            _fail("fixed Git executable bytes changed")
        after_read = os.fstat(descriptor)
        if any(
            getattr(opened, field) != getattr(after_read, field)
            for field in (
                "st_dev", "st_ino", "st_mode", "st_uid", "st_gid",
                "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns",
            )
        ):
            _fail("fixed Git executable changed while hashed")
        completed = subprocess.run(
            [GIT, "--no-replace-objects", *arguments],
            executable=f"/proc/self/fd/{descriptor}",
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
        after_exec = os.fstat(descriptor)
        final = os.lstat(GIT)
        if any(
            getattr(opened, field) != getattr(after_exec, field)
            or getattr(after_exec, field) != getattr(final, field)
            for field in (
                "st_dev", "st_ino", "st_mode", "st_uid", "st_gid",
                "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns",
            )
        ):
            _fail("fixed Git executable changed across query")
    finally:
        os.close(descriptor)
    if completed.returncode != 0 or completed.stderr:
        _fail("fixed Git query did not close exactly")
    return completed.stdout


def _git_anchor(revision: str) -> str:
    raw = _run_git("-C", str(ROOT), "rev-parse", "--verify", revision)
    if len(raw) != 41 or not raw.endswith(b"\n"):
        _fail("Git anchor output changed")
    value = raw[:-1].decode("ascii", errors="strict")
    if _HEX40.fullmatch(value) is None:
        _fail("Git anchor is not lowercase 40-hex")
    return value


def _git_inventory(commit: str) -> dict[str, tuple[str, str, str]]:
    listing = _run_git(
        "-C", str(ROOT), "ls-tree", "-rz", "--full-tree", commit,
        "--", *TCB_PATHS,
    )
    records = listing.split(b"\0")
    if not records or records[-1] != b"":
        _fail("successor Git inventory framing changed")
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
            raise V42ActivationSuccessorLauncherError(
                "successor Git inventory malformed"
            ) from error
        if relative in result:
            _fail("successor Git inventory contains a duplicate")
        result[relative] = values
    if set(result) != set(TCB_PATHS):
        _fail("selected commit omitted an exact successor TCB source")
    return result


def build_live_controller_source_manifest_v42r2(
    *, expected_commit: str, expected_tree: str,
) -> dict[str, Any]:
    if _HEX40.fullmatch(expected_commit) is None or _HEX40.fullmatch(expected_tree) is None:
        _fail("expected successor Git anchors changed")
    if (
        _git_anchor("HEAD^{commit}") != expected_commit
        or _git_anchor("HEAD^{tree}") != expected_tree
    ):
        _fail("selected HEAD/tree differs from successor caller anchor")
    selected = _git_inventory(expected_commit)
    facts: list[dict[str, Any]] = []
    for relative in TCB_PATHS:
        raw = _read_source(relative)
        mode, kind, oid = selected[relative]
        observed_oid = hashlib.sha1(  # noqa: S324 - Git blob identity
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest()
        if (mode, kind, oid) != ("100644", "blob", observed_oid):
            _fail("live successor source differs from selected Git blob")
        facts.append(
            {
                "relative_path": relative,
                "git_mode": mode,
                "git_object_type": kind,
                "git_blob_oid": oid,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if (
        _git_anchor("HEAD^{commit}") != expected_commit
        or _git_anchor("HEAD^{tree}") != expected_tree
    ):
        _fail("successor Git anchors changed across source verification")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))
    from acfqp import (  # noqa: PLC0415
        construction_k7_standard_2048_activation_successor_v42r2 as successor,
    )
    return successor.build_activation_successor_source_manifest_v42r2(
        source_commit=expected_commit,
        source_tree=expected_tree,
        source_facts=facts,
    )


def _read_stable_successor_source_manifest(evidence_root: Path) -> dict[str, Any]:
    root_before = evidence_root.lstat()
    descriptor = os.open(
        evidence_root,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        root_opened = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(root_opened.st_mode)
            or stat.S_IMODE(root_opened.st_mode) != 0o700
            or root_opened.st_uid != os.geteuid()
            or root_opened.st_gid != os.getegid()
            or (root_opened.st_dev, root_opened.st_ino)
            != (root_before.st_dev, root_before.st_ino)
        ):
            _fail("successor evidence root storage changed")
        named = os.stat(
            CONTROLLER_SOURCE_MANIFEST_NAME,
            dir_fd=descriptor,
            follow_symlinks=False,
        )
        opened = os.open(
            CONTROLLER_SOURCE_MANIFEST_NAME,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            dir_fd=descriptor,
        )
        try:
            before = os.fstat(opened)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_uid != os.geteuid()
                or before.st_gid != os.getegid()
                or before.st_nlink != 1
                or not 0 < before.st_size <= 8 * 1024**2
                or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
            ):
                _fail("successor source manifest storage changed")
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(opened, min(remaining, 1024 * 1024))
                if not chunk:
                    _fail("successor source manifest ended early")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(opened, 1):
                _fail("successor source manifest grew while read")
            after = os.fstat(opened)
        finally:
            os.close(opened)
        final = os.stat(
            CONTROLLER_SOURCE_MANIFEST_NAME,
            dir_fd=descriptor,
            follow_symlinks=False,
        )
        if any(
            getattr(before, field) != getattr(after, field)
            or getattr(after, field) != getattr(final, field)
            for field in (
                "st_dev", "st_ino", "st_mode", "st_uid", "st_gid",
                "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns",
            )
        ):
            _fail("successor source manifest changed while read")
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    try:
        document = json.loads(raw.decode("utf-8", errors="strict"))
        canonical = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (UnicodeError, TypeError, ValueError) as error:
        raise V42ActivationSuccessorLauncherError(
            "successor source manifest is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical != raw:
        _fail("successor source manifest canonical bytes changed")
    return document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V42 activation successor and formal source-only launcher"
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    inspect = commands.add_parser("successor")
    inspect.add_argument("--predecessor-activation-evidence-root", required=True)
    inspect.add_argument("--successor-evidence-root", required=True)
    inspect.add_argument("--expected-legacy-activation-plan-id", required=True)
    inspect.add_argument("--expected-controller-commit", required=True)
    inspect.add_argument("--expected-controller-tree", required=True)

    formal = commands.add_parser("formal")
    formal.add_argument("--predecessor-activation-evidence-root", required=True)
    formal.add_argument("--successor-evidence-root", required=True)
    formal.add_argument(
        "--expected-successor-final-evidence-index-id", required=True
    )
    formal.add_argument("--expected-controller-commit", required=True)
    formal.add_argument("--expected-controller-tree", required=True)
    modes = formal.add_mutually_exclusive_group(required=True)
    for mode in FORMAL_MODES:
        modes.add_argument(mode, action="store_true")
    formal.add_argument("--inspection-ordinal", type=int, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    predecessor = _absolute(
        arguments.predecessor_activation_evidence_root,
        "predecessor activation evidence root",
    )
    evidence = _absolute(arguments.successor_evidence_root, "successor evidence root")
    if predecessor.parent != evidence.parent or predecessor == evidence:
        _fail("successor evidence root is not a distinct sibling")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))
    if arguments.operation == "successor":
        if _HEX64.fullmatch(arguments.expected_legacy_activation_plan_id) is None:
            _fail("expected legacy activation plan ID changed")
        manifest = build_live_controller_source_manifest_v42r2(
            expected_commit=arguments.expected_controller_commit,
            expected_tree=arguments.expected_controller_tree,
        )
        from scripts import run_v42_activation_successor_finalizer as driver  # noqa: PLC0415
        result = driver.orchestrate_activation_successor_v42r2(
            predecessor_activation_evidence_root=predecessor,
            successor_evidence_root=evidence,
            expected_legacy_activation_plan_id=(
                arguments.expected_legacy_activation_plan_id
            ),
            controller_source_manifest=manifest,
        )
        os.write(
            1,
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8", errors="strict") + b"\n",
        )
        return 0
    if _HEX64.fullmatch(arguments.expected_successor_final_evidence_index_id) is None:
        _fail("expected successor final evidence index ID changed")
    retained_manifest = _read_stable_successor_source_manifest(evidence)
    live_manifest = build_live_controller_source_manifest_v42r2(
        expected_commit=arguments.expected_controller_commit,
        expected_tree=arguments.expected_controller_tree,
    )
    if retained_manifest != live_manifest:
        _fail("retained successor source manifest differs from live TCB")
    from scripts import (  # noqa: PLC0415
        run_v42_standard_2048_formal_transport_successor_driver as formal_driver,
    )
    mode = next(
        mode for mode in FORMAL_MODES
        if getattr(arguments, mode[2:].replace("-", "_"))
    )
    values = [
        "--predecessor-activation-evidence-root", str(predecessor),
        "--successor-evidence-root", str(evidence),
        "--expected-successor-final-evidence-index-id",
        arguments.expected_successor_final_evidence_index_id,
        mode,
    ]
    if mode in {"--inspect-prepare", "--inspect-launch"}:
        if not 1 <= arguments.inspection_ordinal <= 4096:
            _fail("inspection ordinal changed")
        values.extend(("--inspection-ordinal", str(arguments.inspection_ordinal)))
    elif arguments.inspection_ordinal != 1:
        _fail("inspection ordinal is accepted only in inspection mode")
    return formal_driver.main(values)


if __name__ == "__main__":
    if dict(os.environ) != EXACT_ENVIRONMENT:
        raise RuntimeError("successor launcher environment changed")
    raise SystemExit(main())
