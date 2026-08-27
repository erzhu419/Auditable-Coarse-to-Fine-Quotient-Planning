#!/bin/sh
'''exec' /usr/bin/env -i LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=/usr/bin:/bin /usr/bin/python3 -I -S -B "$(/usr/bin/readlink -f "$0")" "$@"
' '''
from __future__ import annotations

"""Production local driver for V42 ordinal-2 formal prepare and launch.

The driver accepts the exact retained activation evidence directory, rebuilds
the complete pre-formal -> activation -> fixed bootstrap DAG, obtains one
read-only host epoch receipt, and only then builds the formal transport plan.
Each effectful SSH operation has a durable local marker immediately before the
single direct pinned-executable child.  Once that marker may exist, this driver
will never replay the same effect; follow-up is read-only inspection only.
"""

import os
import sys


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
        or dict(os.environ)
        != {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": "/usr/bin:/bin"}
        or getattr(getattr(os, "__spec__", None), "origin", None)
        != "/usr/lib/python3.10/os.py"
    ):
        raise RuntimeError("formal driver isolated Python entry changed")
    live: list[int] = []
    for name in os.listdir("/proc/self/fd"):
        if name.isdigit():
            descriptor = int(name)
            try:
                os.fstat(descriptor)
            except OSError:
                continue
            live.append(descriptor)
    if sorted(live) != [0, 1, 2]:
        raise RuntimeError("formal driver inherited an extra file descriptor")


if __name__ == "__main__":
    _require_early_isolated_runtime()

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.machinery
import json
from pathlib import Path
import stat
from types import ModuleType
from typing import Any, NoReturn


_FIXED_PYTHON_REALPATH = "/usr/bin/python3.10"
_FIXED_PYTHON_BYTE_COUNT = 5_917_224
_FIXED_PYTHON_SHA256 = (
    "7d51cd6b48b521277f5caa4610a82126e315fa2be4df069823a8b1eeb5bd4a86"
)


def _verify_fixed_python_executable() -> None:
    if os.path.realpath("/proc/self/exe") != _FIXED_PYTHON_REALPATH:
        raise RuntimeError("formal driver current executable changed")
    named = os.lstat(_FIXED_PYTHON_REALPATH)
    descriptor = os.open(
        _FIXED_PYTHON_REALPATH,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
        | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o755
            or before.st_uid != 0
            or before.st_gid != 0
            or before.st_nlink != 1
            or before.st_size != _FIXED_PYTHON_BYTE_COUNT
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise RuntimeError("formal driver fixed Python identity changed")
        digest = hashlib.sha256()
        remaining = _FIXED_PYTHON_BYTE_COUNT
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise RuntimeError("formal driver fixed Python ended early")
            digest.update(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise RuntimeError("formal driver fixed Python grew during read")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = os.lstat(_FIXED_PYTHON_REALPATH)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if (
        digest.hexdigest() != _FIXED_PYTHON_SHA256
        or any(
            getattr(before, field) != getattr(after, field)
            or getattr(after, field) != getattr(final, field)
            for field in fields
        )
    ):
        raise RuntimeError("formal driver fixed Python bytes changed")


if __name__ == "__main__":
    _verify_fixed_python_executable()


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"


def _early_unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError("duplicate source-manifest JSON key")
        result[key] = value
    return result


def _early_canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")


def _early_read_regular(path: Path, maximum: int) -> bytes:
    if not path.is_absolute() or ".." in path.parts or not path.name:
        raise RuntimeError("early source artifact path changed")
    directory_flags = (
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    directory_descriptors = [os.open("/", directory_flags)]
    directory_states = [os.fstat(directory_descriptors[0])]
    descriptor = -1
    try:
        for component in path.parent.parts[1:]:
            named_directory = os.stat(
                component,
                dir_fd=directory_descriptors[-1],
                follow_symlinks=False,
            )
            successor = os.open(
                component, directory_flags, dir_fd=directory_descriptors[-1]
            )
            opened_directory = os.fstat(successor)
            if (
                not stat.S_ISDIR(opened_directory.st_mode)
                or (opened_directory.st_dev, opened_directory.st_ino)
                != (named_directory.st_dev, named_directory.st_ino)
            ):
                os.close(successor)
                raise RuntimeError("early source directory chain changed")
            directory_descriptors.append(successor)
            directory_states.append(opened_directory)
        named = os.stat(
            path.name,
            dir_fd=directory_descriptors[-1],
            follow_symlinks=False,
        )
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            dir_fd=directory_descriptors[-1],
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > maximum
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise RuntimeError("early source artifact identity changed: " + str(path))
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise RuntimeError("early source artifact ended early: " + str(path))
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise RuntimeError("early source artifact grew during read: " + str(path))
        after = os.fstat(descriptor)
        final = os.stat(
            path.name,
            dir_fd=directory_descriptors[-1],
            follow_symlinks=False,
        )
        for index, (opened, expected) in enumerate(
            zip(directory_descriptors, directory_states, strict=True)
        ):
            current = os.fstat(opened)
            if (
                current.st_dev, current.st_ino, current.st_mode,
                current.st_uid, current.st_gid
            ) != (
                expected.st_dev, expected.st_ino, expected.st_mode,
                expected.st_uid, expected.st_gid
            ):
                raise RuntimeError("early held source directory changed")
            if index:
                named_component = os.stat(
                    path.parent.parts[index],
                    dir_fd=directory_descriptors[index - 1],
                    follow_symlinks=False,
                )
                if (current.st_dev, current.st_ino) != (
                    named_component.st_dev, named_component.st_ino
                ):
                    raise RuntimeError("early named source directory changed")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        for opened in reversed(directory_descriptors):
            os.close(opened)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(final, field)
        for field in fields
    ):
        raise RuntimeError("early source artifact changed during read: " + str(path))
    return b"".join(chunks)


class _VerifiedSourceLoader:
    def __init__(
        self, finder: "_VerifiedSourceFinder", fullname: str, path: str,
        raw: bytes, package: bool,
    ) -> None:
        self.finder = finder
        self.fullname = fullname
        self.path = path
        self.raw = raw
        self.package = package
        self.exec_count = 0

    def create_module(self, spec: object) -> None:
        del spec
        return None

    def exec_module(self, module: object) -> None:
        if self.exec_count != 0:
            raise RuntimeError("verified repository module executed more than once")
        self.exec_count = 1
        namespace = vars(module)
        namespace["__file__"] = self.path
        namespace["__cached__"] = None
        exec(
            compile(self.raw, self.path, "exec", dont_inherit=True),
            namespace,
            namespace,
        )


class _VerifiedSourceFinder:
    def __init__(
        self,
        facts: dict[str, dict[str, object]],
        *,
        read_source: Callable[[str], bytes],
        pinned_root_chain: object,
    ) -> None:
        self.facts = facts
        self.sources: dict[str, bytes] = {}
        self.read_source = read_source
        self.pinned_root_chain = pinned_root_chain
        self.module_paths: dict[str, str] = {}
        self.created_loaders: dict[str, _VerifiedSourceLoader] = {}

    def _source(self, relative: str) -> bytes:
        cached = self.sources.get(relative)
        if cached is not None:
            return cached
        fact = self.facts[relative]
        source = self.read_source(relative)
        if (
            len(source) != fact["byte_count"]
            or hashlib.sha256(source).hexdigest() != fact["sha256"]
            or hashlib.sha1(
                b"blob " + str(len(source)).encode("ascii") + b"\0" + source
            ).hexdigest()
            != fact["git_blob_oid"]
        ):
            raise RuntimeError("manifested source bytes changed: " + relative)
        self.sources[relative] = source
        return source

    def find_spec(
        self, fullname: str, path: object = None, target: object = None
    ) -> object:
        del target
        if fullname == "acfqp" or fullname.startswith("acfqp."):
            prefix = "src/"
        elif fullname == "scripts" or fullname.startswith("scripts."):
            prefix = ""
        else:
            if path is None:
                stem = fullname.replace(".", "/")
                for base in (ROOT, SOURCE_ROOT):
                    if any(
                        os.path.lexists(base / candidate)
                        for candidate in (
                            stem + ".py", stem + ".pyc",
                            stem + "/__init__.py",
                            stem + "/__init__.pyc",
                        )
                    ):
                        raise ImportError(
                            "repository stdlib shadow rejected: " + fullname
                        )
            return None
        stem = prefix + fullname.replace(".", "/")
        module_relative = stem + ".py"
        package_relative = stem + "/__init__.py"
        if module_relative in self.facts:
            relative = module_relative
            package = False
        elif package_relative in self.facts:
            relative = package_relative
            package = True
        else:
            raise ImportError("unmanifested repository module: " + fullname)
        origin = str(ROOT / relative)
        if fullname in self.created_loaders:
            raise ImportError("verified repository module loader repeated: " + fullname)
        loader = _VerifiedSourceLoader(
            self, fullname, origin, self._source(relative), package
        )
        self.created_loaders[fullname] = loader
        self.module_paths[fullname] = relative
        spec = importlib.machinery.ModuleSpec(
            fullname, loader, origin=origin, is_package=package
        )
        if package:
            spec.submodule_search_locations = [str((ROOT / relative).parent)]
        return spec

    def verify_loaded(self) -> None:
        verifier = getattr(self.pinned_root_chain, "verify", None)
        if not callable(verifier):
            raise RuntimeError("verified repository root chain changed")
        verifier()
        if not sys.meta_path or sys.meta_path[0] is not self:
            raise RuntimeError("verified repository meta finder changed")
        actual_loaded: dict[str, str] = {}
        for name, module in tuple(sys.modules.items()):
            if not (
                name == "acfqp" or name.startswith("acfqp.")
                or name == "scripts" or name.startswith("scripts.")
            ):
                continue
            file_name = getattr(module, "__file__", None)
            loader = getattr(module, "__loader__", None)
            origin = getattr(getattr(module, "__spec__", None), "origin", None)
            if (
                type(file_name) is not str
                or file_name.endswith((".pyc", ".pyo"))
                or type(loader) is not _VerifiedSourceLoader
                or loader.finder is not self
                or loader.exec_count != 1
                or self.module_paths.get(name) != loader.path.removeprefix(
                    str(ROOT) + "/"
                )
                or origin != file_name
                or getattr(module, "__cached__", None) is not None
            ):
                raise RuntimeError("loaded repository module escaped verified bytes")
            actual_loaded[name] = self.module_paths[name]
        if (
            actual_loaded != _FORMAL_LOCAL_EXPECTED_LOADED_MODULES
            or set(self.created_loaders) != set(_FORMAL_LOCAL_EXPECTED_LOADED_MODULES)
        ):
            raise RuntimeError("formal driver loaded repository module inventory changed")


def _early_activation_evidence_root(argv: Sequence[str]) -> Path:
    matches: list[str] = []
    for index, value in enumerate(argv):
        if value == "--activation-evidence-root" and index + 1 < len(argv):
            matches.append(argv[index + 1])
        elif value.startswith("--activation-evidence-root="):
            matches.append(value.split("=", 1)[1])
    if len(matches) != 1:
        raise RuntimeError(
            "production formal driver requires one early activation evidence root"
        )
    root = Path(matches[0])
    if not root.is_absolute():
        raise RuntimeError("early activation evidence root is not absolute")
    return root


def _early_expected_activation_final_index_id(argv: Sequence[str]) -> str:
    option = "--expected-activation-final-evidence-index-id"
    matches: list[str] = []
    for index, value in enumerate(argv):
        if value == option and index + 1 < len(argv):
            matches.append(argv[index + 1])
        elif value.startswith(option + "="):
            matches.append(value.split("=", 1)[1])
    if (
        len(matches) != 1
        or len(matches[0]) != 64
        or any(character not in "0123456789abcdef" for character in matches[0])
    ):
        raise RuntimeError(
            "production formal driver requires one expected activation final index ID"
        )
    return matches[0]


_FROZEN_LAUNCHER_RELATIVE = "scripts/launch_v42_preformal_upload_sender.py"
_FROZEN_LAUNCHER_BYTE_COUNT = 61_999
_FROZEN_LAUNCHER_SHA256 = (
    "cb2839150adc1df8906604a7a7c9be3a6f7269085a555749050c849608ee9d8a"
)
_FROZEN_LAUNCHER_GIT_BLOB = "1da8eb02bd62a40a9e0c8472837d0a29a176539f"
_FORMAL_TRANSPORT_ONLY_TCB_PATHS = frozenset(
    {
        _FROZEN_LAUNCHER_RELATIVE,
        "scripts/publish_v42_preformal_upload_journal.py",
        "scripts/run_v42_materialization_activation.py",
        "scripts/v42_materialization_activation_loader.py",
        "scripts/v42_materialization_activation_receiver.py",
        "scripts/v42_materialization_activation_service.py",
        "scripts/run_v42_standard_2048_formal_transport_driver.py",
        "scripts/v42_standard_2048_formal_transport_receiver.py",
        "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
    }
)

_FORMAL_LOCAL_EXPECTED_LOADED_MODULES = {
    "acfqp": "src/acfqp/__init__.py",
    "acfqp.artifacts": "src/acfqp/artifacts.py",
    "acfqp.build_coverage": "src/acfqp/build_coverage.py",
    "acfqp.construction_k7_domain_registry_extension_v42": (
        "src/acfqp/construction_k7_domain_registry_extension_v42.py"
    ),
    "acfqp.construction_k7_standard_2048_formal_transport_v42r1": (
        "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py"
    ),
    "acfqp.construction_k7_standard_2048_fresh_terminal_preregistration_v42": (
        "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py"
    ),
    "acfqp.construction_k7_standard_2048_history_manifest_v42": (
        "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py"
    ),
    "acfqp.construction_k7_standard_2048_materialization_activation_v42r1": (
        "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py"
    ),
    "acfqp.construction_k7_standard_2048_materialization_transport_v42r1": (
        "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py"
    ),
    "acfqp.construction_k7_standard_2048_process_supervision_v42r1": (
        "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py"
    ),
    "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1": (
        "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py"
    ),
    "acfqp.core": "src/acfqp/core.py",
    "acfqp.enumeration": "src/acfqp/enumeration.py",
    "acfqp.phase3e_ids": "src/acfqp/phase3e_ids.py",
    "scripts": "scripts/__init__.py",
    "scripts.publish_v42_preformal_upload_journal": (
        "scripts/publish_v42_preformal_upload_journal.py"
    ),
    "scripts.run_v42_preformal_upload_sender": (
        "scripts/run_v42_preformal_upload_sender.py"
    ),
    "scripts.run_v42_standard_2048_remote_ordinal2": (
        "scripts/run_v42_standard_2048_remote_ordinal2.py"
    ),
}


def _frozen_launcher_primitives() -> dict[str, object]:
    path = ROOT / _FROZEN_LAUNCHER_RELATIVE
    raw = _early_read_regular(path, 1024**2)
    if (
        len(raw) != _FROZEN_LAUNCHER_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != _FROZEN_LAUNCHER_SHA256
        or hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest()
        != _FROZEN_LAUNCHER_GIT_BLOB
    ):
        raise RuntimeError("frozen preformal launcher primitive bytes changed")
    module_name = "_acfqp_frozen_preformal_launcher_primitives"
    if module_name in sys.modules:
        raise RuntimeError("frozen preformal launcher primitive module repeated")
    module = ModuleType(module_name)
    module.__file__ = str(path)
    module.__package__ = None
    module.__cached__ = None
    sys.modules[module_name] = module
    try:
        exec(
            compile(raw, str(path), "exec", dont_inherit=True),
            module.__dict__,
            module.__dict__,
        )
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    namespace = module.__dict__
    required = {
        "_run_fixed_git_v42r1", "_open_absolute_directory_chain",
        "_read_relative_tcb_file_v42r1", "GIT_VERSION_STDOUT",
    }
    if not required <= namespace.keys():
        raise RuntimeError("frozen preformal launcher primitive surface changed")
    return namespace


def _early_git_tree(
    *, source_commit: str, source_tree: str,
    primitives: Mapping[str, object],
) -> dict[str, tuple[str, str, str]]:
    run = primitives["_run_fixed_git_v42r1"]
    assert callable(run)
    if run("--version") != primitives["GIT_VERSION_STDOUT"]:
        raise RuntimeError("frozen pinned Git version output changed")
    arguments = (
        "-C", str(ROOT), "rev-parse",
        "HEAD^{commit}", "HEAD^{tree}",
    )
    anchors = run(*arguments).splitlines()
    expected_anchors = [source_commit.encode("ascii"), source_tree.encode("ascii")]
    if anchors != expected_anchors:
        raise RuntimeError("activated transport manifest is not current Git HEAD")
    listing = run(
        "-C", str(ROOT), "ls-tree", "-rz", "--full-tree",
        source_commit,
    )
    if run(*arguments).splitlines() != expected_anchors:
        raise RuntimeError("Git HEAD changed across selected-tree observation")
    result: dict[str, tuple[str, str, str]] = {}
    for row in listing.split(b"\0"):
        if not row:
            continue
        try:
            prefix, raw_path = row.split(b"\t", 1)
            mode, object_type, oid = prefix.decode("ascii").split(" ", 2)
            relative = raw_path.decode("utf-8", errors="strict")
        except (ValueError, UnicodeError) as error:
            raise RuntimeError("early Git tree row changed encoding") from error
        if relative in result or relative.startswith("/") or ".." in Path(relative).parts:
            raise RuntimeError("early Git tree path changed")
        result[relative] = (mode, object_type, oid)
    return result


def _install_verified_repository_importer(
    evidence_root: Path, expected_final_index_id: str,
) -> None:
    final_raw = _early_read_regular(
        evidence_root / "MATERIALIZATION_ACTIVATION_FINAL_EVIDENCE_INDEX.json",
        4 * 1024**2,
    )
    try:
        final_index = json.loads(
            final_raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_early_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                RuntimeError("nonfinite activation final-index number: " + token)
            ),
        )
    except (UnicodeError, ValueError, TypeError) as error:
        raise RuntimeError("early activation final index is not strict JSON") from error
    if type(final_index) is not dict or _early_canonical_bytes(final_index) != final_raw:
        raise RuntimeError("early activation final index is not canonical JSON")
    final_payload = dict(final_index)
    final_identifier = final_payload.pop(
        "materialization_activation_final_evidence_index_id", None
    )
    if (
        final_identifier != expected_final_index_id
        or hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:activation-final-evidence-index\0"
            + _early_canonical_bytes(final_payload)
        ).hexdigest()
        != final_identifier
        or final_index.get(
            "formal_evidence_bundle_complete_under_bounded_successor_claim"
        ) is not True
    ):
        raise RuntimeError("early activation final index identity changed")
    manifest_path = evidence_root / "EXECUTION_SOURCE_MANIFEST.json"
    raw = _early_read_regular(manifest_path, 64 * 1024**2)
    try:
        document = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_early_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                RuntimeError("nonfinite source-manifest number: " + token)
            ),
        )
    except (UnicodeError, ValueError, TypeError) as error:
        raise RuntimeError("early source manifest is not strict JSON") from error
    if type(document) is not dict or _early_canonical_bytes(document) != raw:
        raise RuntimeError("early source manifest is not canonical JSON")
    identifier = document.get("source_manifest_id")
    payload = dict(document)
    payload.pop("source_manifest_id", None)
    if (
        type(identifier) is not str
        or len(identifier) != 64
        or any(character not in "0123456789abcdef" for character in identifier)
        or hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:source-manifest\0"
            + _early_canonical_bytes(payload)
        ).hexdigest()
        != identifier
    ):
        raise RuntimeError("early source-manifest content ID changed")
    source_facts = document.get("source_facts")
    if type(source_facts) is not list or not source_facts:
        raise RuntimeError("early source-manifest facts changed")
    source_by_path: dict[str, dict[str, object]] = {}
    for fact in source_facts:
        if type(fact) is not dict or type(fact.get("relative_path")) is not str:
            raise RuntimeError("early source-manifest fact changed type")
        relative = fact["relative_path"]
        if relative in source_by_path or not relative.endswith(".py"):
            raise RuntimeError("early source-manifest fact changed inventory")
        source_by_path[relative] = fact
    transport_raw = _early_read_regular(
        evidence_root / "TRANSPORT_MANIFEST.json", 64 * 1024**2
    )
    try:
        transport = json.loads(
            transport_raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_early_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                RuntimeError("nonfinite transport-manifest number: " + token)
            ),
        )
    except (UnicodeError, ValueError, TypeError) as error:
        raise RuntimeError("early transport manifest is not strict JSON") from error
    if type(transport) is not dict or _early_canonical_bytes(transport) != transport_raw:
        raise RuntimeError("early transport manifest is not canonical JSON")
    transport_identifier = transport.get("transport_manifest_id")
    transport_payload = dict(transport)
    transport_payload.pop("transport_manifest_id", None)
    if (
        type(transport_identifier) is not str
        or len(transport_identifier) != 64
        or any(
            character not in "0123456789abcdef"
            for character in transport_identifier
        )
        or hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:transport-manifest\0"
            + _early_canonical_bytes(transport_payload)
        ).hexdigest()
        != transport_identifier
        or transport.get("execution_source_manifest_id") != identifier
        or transport.get("source_commit") != document.get("source_commit")
        or transport.get("source_tree") != document.get("source_tree")
    ):
        raise RuntimeError("early transport/source manifest join changed")
    primitives = _frozen_launcher_primitives()
    git_facts = _early_git_tree(
        source_commit=str(transport.get("source_commit")),
        source_tree=str(transport.get("source_tree")),
        primitives=primitives,
    )
    facts = transport.get("transport_facts")
    if type(facts) is not list or not facts:
        raise RuntimeError("early transport-manifest facts changed")
    python_facts: dict[str, dict[str, object]] = {}
    allowed_python_paths = set(source_by_path) | set(
        _FORMAL_TRANSPORT_ONLY_TCB_PATHS
    )
    for fact in facts:
        if type(fact) is not dict:
            raise RuntimeError("early transport-manifest fact changed type")
        relative = fact.get("relative_path")
        if (
            type(relative) is not str
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or type(fact.get("byte_count")) is not int
            or fact["byte_count"] < 0
            or type(fact.get("sha256")) is not str
            or type(fact.get("git_blob_oid")) is not str
        ):
            raise RuntimeError("early transport-manifest fact changed semantics")
        if relative.endswith(".py") and relative in allowed_python_paths:
            if relative in python_facts or fact["byte_count"] <= 0:
                raise RuntimeError("early Python transport fact is duplicated or empty")
            if git_facts.get(relative) != (
                fact.get("git_mode"), fact.get("git_object_type"),
                fact.get("git_blob_oid"),
            ):
                raise RuntimeError(
                    "early Python transport fact differs from Git HEAD: " + relative
                )
            python_facts[relative] = fact
    for relative, source_fact in source_by_path.items():
        if python_facts.get(relative) != source_fact:
            raise RuntimeError(
                "execution source fact is not an exact transport subset: "
                + relative
            )
    required = {
        "scripts/run_v42_standard_2048_formal_transport_driver.py",
        "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
        "scripts/run_v42_preformal_upload_sender.py",
        "scripts/run_v42_standard_2048_remote_ordinal2.py",
    }
    if not required <= python_facts.keys():
        raise RuntimeError("early transport manifest omitted the formal driver closure")
    live_driver = _early_read_regular(Path(__file__).resolve(strict=True), 4 * 1024**2)
    driver_fact = python_facts[
        "scripts/run_v42_standard_2048_formal_transport_driver.py"
    ]
    if (
        len(live_driver) != driver_fact["byte_count"]
        or hashlib.sha256(live_driver).hexdigest() != driver_fact["sha256"]
        or hashlib.sha1(
            b"blob " + str(len(live_driver)).encode("ascii") + b"\0"
            + live_driver
        ).hexdigest()
        != driver_fact["git_blob_oid"]
    ):
        raise RuntimeError("executing formal driver is outside the transport manifest")
    if any(
        name == "acfqp" or name.startswith("acfqp.")
        or name == "scripts" or name.startswith("scripts.")
        for name in sys.modules
    ):
        raise RuntimeError("repository module loaded before verified source importer")
    open_chain = primitives["_open_absolute_directory_chain"]
    read_relative = primitives["_read_relative_tcb_file_v42r1"]
    assert callable(open_chain) and callable(read_relative)
    pinned_root_chain = open_chain(ROOT, label="formal repository root")

    def read_source(relative: str) -> bytes:
        raw_source = read_relative(pinned_root_chain.descriptor, relative)
        pinned_root_chain.verify()
        return raw_source

    sys.dont_write_bytecode = True
    sys.meta_path.insert(
        0,
        _VerifiedSourceFinder(
            python_facts,
            read_source=read_source,
            pinned_root_chain=pinned_root_chain,
        ),
    )


if __name__ == "__main__":
    _install_verified_repository_importer(
        _early_activation_evidence_root(sys.argv[1:]),
        _early_expected_activation_final_index_id(sys.argv[1:]),
    )

if __name__ != "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))

from acfqp import (  # noqa: E402
    construction_k7_standard_2048_formal_transport_v42r1 as formal,
)
from acfqp import (  # noqa: E402
    construction_k7_standard_2048_materialization_activation_v42r1 as activation,
)
from acfqp import (  # noqa: E402
    construction_k7_standard_2048_materialization_transport_v42r1 as preformal,
)
from acfqp import (  # noqa: E402
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp import (  # noqa: E402
    construction_k7_standard_2048_fresh_terminal_preregistration_v42 as prereg,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json  # noqa: E402
from scripts import run_v42_preformal_upload_sender as frozen_sender  # noqa: E402
from scripts import run_v42_standard_2048_remote_ordinal2 as existing_runner  # noqa: E402


_PRODUCTION_SOURCE_FINDER = (
    sys.meta_path[0]
    if __name__ == "__main__" and type(sys.meta_path[0]) is _VerifiedSourceFinder
    else None
)
if _PRODUCTION_SOURCE_FINDER is not None:
    _PRODUCTION_SOURCE_FINDER.verify_loaded()


class V42FormalTransportDriverError(RuntimeError):
    pass


def _fail(message: str) -> NoReturn:
    raise V42FormalTransportDriverError(message)


PREFORMAL_PLAN_FILE = preformal.PREFORMAL_PLAN_NAME
PREFORMAL_ATTEMPT_FILE = preformal.PREFORMAL_ATTEMPT_NAME
PREFORMAL_RECEIPT_FILE = preformal.PREFORMAL_RECEIPT_NAME
PREFORMAL_OUTCOME_FILE = preformal.PREFORMAL_OUTCOME_NAME
PREACTIVATION_PLAN_FILE = "PREACTIVATION_RESOURCE_PROBE_PLAN.json"
PREACTIVATION_RESULT_FILE = "PREACTIVATION_RESOURCE_RESULT.json"
ACTIVATION_PLAN_FILE = activation.LOCAL_ACTIVATION_PLAN_NAME
ACTIVATION_ATTEMPT_FILE = activation.LOCAL_ACTIVATION_ATTEMPT_NAME
ACTIVATION_NETWORK_START_FILE = activation.LOCAL_ACTIVATION_NETWORK_START_NAME
REMOTE_ACTIVATION_ATTEMPT_FILE = activation.REMOTE_ACTIVATION_ATTEMPT_NAME
ACTIVATION_SERVICE_RECEIPT_FILE = activation.REMOTE_ACTIVATION_SERVICE_RECEIPT_NAME
ACTIVATION_READY_FILE = activation.REMOTE_ACTIVATION_READY_NAME
ACTIVATION_TERMINAL_FILE = activation.REMOTE_ACTIVATION_TERMINAL_NAME
ACTIVATION_EVIDENCE_ROOTS_FILE = "ACTIVATION_EVIDENCE_ROOTS.json"
ACTIVATION_FINAL_EVIDENCE_INDEX_FILE = (
    "MATERIALIZATION_ACTIVATION_FINAL_EVIDENCE_INDEX.json"
)
ACTIVATION_READ_ONLY_SNAPSHOT_PREFIX = "ACTIVATION_READ_ONLY_SNAPSHOT_"
BOOTSTRAP_TERMINAL_FILE = authority.MATERIALIZATION_TERMINAL_NAME
BOOTSTRAP_REMOTE_ATTEMPT_FILE = authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME
HOST_EPOCH_RECEIPT_FILE = "FORMAL_HOST_EPOCH_RECEIPT.json"
FORMAL_EVIDENCE_ASSEMBLY_FILE = "FORMAL_ACTIVATION_EVIDENCE_ASSEMBLY.json"
PREDECESSOR_CHAIN_FILE = "PREFORMAL_PREDECESSOR_CHAIN.json"

ACTIVATION_LOADER_RELATIVE = "scripts/v42_materialization_activation_loader.py"
ACTIVATION_RECEIVER_RELATIVE = "scripts/v42_materialization_activation_receiver.py"
ACTIVATION_SERVICE_RELATIVE = "scripts/v42_materialization_activation_service.py"
ACTIVATION_DRIVER_RELATIVE = "scripts/run_v42_materialization_activation.py"
ACTIVATION_AUTHORITY_RELATIVE = (
    "src/acfqp/"
    "construction_k7_standard_2048_materialization_activation_v42r1.py"
)

LAUNCH_CONTROL_NAME = "EXISTING_RUNNER_LAUNCH_CONTROL"
MAX_EVIDENCE_BYTES = 64 * 1024**2
STDERR_CAP = 1024**2


def _stable_read(path: Path, cap: int, *, mode: int | None = None) -> bytes:
    if not path.is_absolute():
        _fail(f"evidence path is not absolute: {path}")
    before_named = path.lstat()
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > cap
            or (before.st_dev, before.st_ino)
            != (before_named.st_dev, before_named.st_ino)
            or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
            or before.st_uid != os.geteuid()
        ):
            _fail(f"evidence file identity changed: {path}")
        chunks: list[bytes] = []
        count = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, cap + 1 - count))
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
            if count > cap:
                _fail(f"evidence file exceeds cap: {path}")
        after = os.fstat(descriptor)
        after_named = path.lstat()
    finally:
        os.close(descriptor)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(after_named, field)
        for field in fields
    ):
        _fail(f"evidence file changed during read: {path}")
    return b"".join(chunks)


def _document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42FormalTransportDriverError(f"{label} is not canonical JSON") from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} canonical bytes changed")
    return value


def _load_document(root: Path, name: str) -> tuple[dict[str, Any], bytes]:
    raw = _stable_read(root / name, MAX_EVIDENCE_BYTES)
    return _document(raw, name), raw


def _evidence_directory(path: Path, label: str) -> Path:
    try:
        observed = path.lstat()
    except FileNotFoundError as error:
        raise V42FormalTransportDriverError(f"{label} is absent") from error
    if (
        not path.is_absolute()
        or path.resolve(strict=True) != path
        or not stat.S_ISDIR(observed.st_mode)
        or observed.st_uid != os.geteuid()
    ):
        _fail(f"{label} is redirected, non-directory, or misowned")
    return path


@dataclass
class _EvidenceRootPin:
    path: Path
    label: str
    directory_chain: list[tuple[int, str | None, tuple[int, ...]]]
    root_state: tuple[int, ...]

    @classmethod
    def open(cls, path: Path, label: str) -> "_EvidenceRootPin":
        path = _evidence_directory(path, label)
        chain = _open_directory_chain(path)
        observed = os.fstat(chain[-1][0])
        if (
            stat.S_IMODE(observed.st_mode) != 0o700
            or observed.st_uid != os.geteuid()
            or observed.st_gid != os.getegid()
        ):
            for descriptor, _, _ in reversed(chain):
                os.close(descriptor)
            _fail(f"{label} ownership changed")
        result = cls(path, label, chain, _stat_state(observed))
        result.verify()
        return result

    @property
    def descriptor(self) -> int:
        return self.directory_chain[-1][0]

    def verify(self) -> None:
        _verify_directory_chain(self.directory_chain)
        if _stat_state(os.fstat(self.descriptor)) != self.root_state:
            _fail(f"{self.label} changed across evidence assembly")

    def inventory(self) -> list[str]:
        self.verify()
        result = sorted(os.listdir(self.descriptor))
        self.verify()
        return result

    def read(self, name: str, cap: int) -> bytes:
        self.verify()
        raw = _read_regular_at(self.descriptor, name, cap, mode=0o400)
        self.verify()
        return raw

    def close(self) -> None:
        for descriptor, _, _ in reversed(self.directory_chain):
            os.close(descriptor)
        self.directory_chain.clear()

    def identity(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "st_dev": self.root_state[0],
            "st_ino": self.root_state[1],
            "mode": stat.S_IMODE(self.root_state[2]),
            "uid": self.root_state[3],
            "gid": self.root_state[4],
        }


def _program_raw(relative: str) -> bytes:
    return _stable_read(ROOT / relative, 4 * 1024**2)


def _artifact(raw: bytes, relative: str) -> dict[str, Any]:
    return {
        "relative_path": relative,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _load_production_inputs(
    evidence_root: Path,
    *,
    expected_final_evidence_index_id: str | None = None,
    preformal_evidence_root: Path | None = None,
    resource_evidence_root: Path | None = None,
    control_evidence_root: Path | None = None,
) -> dict[str, Any]:
    """Assemble the raw production DAG from existing retained roots.

    ``evidence_root`` is exactly the activation classifier collector output.
    The three optional roots point directly at the earlier journals/control
    directory, so the 553-MiB capsule is read in place and never copied into a
    fabricated flat directory.
    """

    activation_pin = _EvidenceRootPin.open(
        evidence_root, "activation collector evidence root"
    )
    pins: dict[str, _EvidenceRootPin] = {str(evidence_root): activation_pin}
    try:
        index_raw = activation_pin.read(ACTIVATION_EVIDENCE_ROOTS_FILE, 4 * 1024**2)
        index = _document(index_raw, "activation evidence roots")
        expected_index_fields = {
            "schema", "activation_evidence_root", "control_evidence_root",
            "preformal_evidence_root", "resource_evidence_root",
            "controls_are_retained_by_stable_reference_not_hardlink_or_copy",
            "expected_exact_control_names", "control_reference_snapshot",
            "formal_loader_must_reverify_all_control_bytes_and_storage",
            "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim",
        }
        if (
            set(index) != expected_index_fields
            or index.get("schema")
            != "acfqp.v42_materialization_activation_evidence_roots.v42r1"
            or index.get("activation_evidence_root") != str(evidence_root)
            or index.get(
                "controls_are_retained_by_stable_reference_not_hardlink_or_copy"
            ) is not True
            or index.get("expected_exact_control_names")
            != list(preformal.CONTROL_NAMES)
            or index.get(
                "formal_loader_must_reverify_all_control_bytes_and_storage"
            ) is not True
            or index.get(
                "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim"
            ) is not True
        ):
            _fail("activation evidence roots index changed")

        def indexed_path(key: str, override: Path | None) -> Path:
            value = index.get(key)
            if type(value) is not str:
                _fail("activation evidence indexed path changed type")
            selected = Path(value)
            if not selected.is_absolute() or ".." in selected.parts:
                _fail("activation evidence indexed path changed")
            if override is not None and override != selected:
                _fail("explicit evidence root differs from collector index")
            return selected

        activation_root = evidence_root
        preformal_root = indexed_path(
            "preformal_evidence_root", preformal_evidence_root
        )
        resource_root = indexed_path(
            "resource_evidence_root", resource_evidence_root
        )
        control_root = indexed_path(
            "control_evidence_root", control_evidence_root
        )

        def pin(path: Path, label: str) -> _EvidenceRootPin:
            key = str(path)
            existing = pins.get(key)
            if existing is not None:
                return existing
            opened = _EvidenceRootPin.open(path, label)
            pins[key] = opened
            return opened

        preformal_pin = pin(preformal_root, "preformal evidence root")
        resource_pin = pin(resource_root, "resource evidence root")
        control_pin = pin(control_root, "preformal control root")
        documents: dict[str, Any] = {}
        raws: dict[str, bytes] = {}
        final_index_raw = activation_pin.read(
            ACTIVATION_FINAL_EVIDENCE_INDEX_FILE, 4 * 1024**2
        )
        final_index = _document(
            final_index_raw, ACTIVATION_FINAL_EVIDENCE_INDEX_FILE
        )
        if (
            expected_final_evidence_index_id is not None
            and final_index.get(
                "materialization_activation_final_evidence_index_id"
            )
            != expected_final_evidence_index_id
        ):
            _fail("activation final evidence index differs from expected identity")
        snapshot_names = [
            name
            for name in activation_pin.inventory()
            if name.startswith(ACTIVATION_READ_ONLY_SNAPSHOT_PREFIX)
            and name.endswith(".json")
            and len(name)
            == len(ACTIVATION_READ_ONLY_SNAPSHOT_PREFIX) + 8 + len(".json")
            and name[
                len(ACTIVATION_READ_ONLY_SNAPSHOT_PREFIX):-len(".json")
            ].isdigit()
        ]
        if not snapshot_names or len(snapshot_names) > 4096:
            _fail("activation read-only snapshot inventory changed")
        activation_snapshots: list[dict[str, Any]] = []
        activation_snapshot_raws: list[bytes] = []
        for ordinal, name in enumerate(sorted(snapshot_names), start=1):
            expected_name = (
                ACTIVATION_READ_ONLY_SNAPSHOT_PREFIX + f"{ordinal:08d}.json"
            )
            if name != expected_name:
                _fail("activation read-only snapshot ordinals changed")
            snapshot_raw = activation_pin.read(name, MAX_EVIDENCE_BYTES)
            activation_snapshot_raws.append(snapshot_raw)
            activation_snapshots.append(_document(snapshot_raw, name))
        roots_by_name: dict[str, _EvidenceRootPin] = {}
        for name in (
            PREFORMAL_PLAN_FILE, PREFORMAL_ATTEMPT_FILE, PREFORMAL_RECEIPT_FILE,
            PREFORMAL_OUTCOME_FILE,
        ):
            roots_by_name[name] = (
                activation_pin if name == PREFORMAL_RECEIPT_FILE else preformal_pin
            )
        for name in (PREACTIVATION_PLAN_FILE, PREACTIVATION_RESULT_FILE):
            roots_by_name[name] = resource_pin
        for name in (
            ACTIVATION_PLAN_FILE, ACTIVATION_ATTEMPT_FILE,
            ACTIVATION_NETWORK_START_FILE, REMOTE_ACTIVATION_ATTEMPT_FILE,
            ACTIVATION_SERVICE_RECEIPT_FILE, ACTIVATION_READY_FILE,
            ACTIVATION_TERMINAL_FILE, authority.SOURCE_MANIFEST_NAME,
            authority.TRANSPORT_MANIFEST_NAME,
            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            BOOTSTRAP_REMOTE_ATTEMPT_FILE, BOOTSTRAP_TERMINAL_FILE,
        ):
            roots_by_name[name] = activation_pin
        for name, root_pin in roots_by_name.items():
            raw = root_pin.read(name, MAX_EVIDENCE_BYTES)
            raws[name] = raw
            documents[name] = _document(raw, name)
        if PREDECESSOR_CHAIN_FILE in preformal_pin.inventory():
            predecessor_raw = preformal_pin.read(
                PREDECESSOR_CHAIN_FILE, MAX_EVIDENCE_BYTES
            )
            predecessor_chain = loads_canonical_json(predecessor_raw)
            if (
                type(predecessor_chain) is not list
                or canonical_json_bytes(predecessor_chain) != predecessor_raw
            ):
                _fail("preformal predecessor chain is not exact canonical JSON")
        else:
            predecessor_chain = []
        if control_pin.inventory() != list(preformal.CONTROL_NAMES):
            _fail("indexed preformal control inventory changed")
        controls = {
            name: control_pin.read(name, 2 * 1024**3)
            for name in preformal.CONTROL_NAMES
        }
        raws.update(controls)
        snapshot = index.get("control_reference_snapshot")
        if (
            type(snapshot) is not dict
            or snapshot.get("control_root") != str(control_root)
            or snapshot.get("exact_inventory") != list(preformal.CONTROL_NAMES)
            or snapshot.get("all_files_read_nofollow_from_pinned_root") is not True
            or snapshot.get("all_file_bytes_hashed_with_bounded_reads") is not True
            or snapshot.get("whole_root_first_last_snapshot_equal") is not True
            or type(snapshot.get("control_facts")) is not list
        ):
            _fail("activation control reference snapshot changed")
        snapshot_rows = {row.get("name"): row for row in snapshot["control_facts"]}
        if set(snapshot_rows) != set(preformal.CONTROL_NAMES):
            _fail("activation control reference fact inventory changed")
        for name, raw in controls.items():
            row = snapshot_rows[name]
            if (
                type(row) is not dict
                or row.get("path") != str(control_root / name)
                or row.get("mode") != 0o400
                or row.get("uid") != os.geteuid()
                or row.get("gid") != os.getegid()
                or row.get("st_nlink") != 1
                or row.get("byte_count") != len(raw)
                or row.get("sha256") != hashlib.sha256(raw).hexdigest()
            ):
                _fail("activation control reference fact changed: " + name)
        programs = {
            preformal.PREFORMAL_LOADER_SOURCE_RELATIVE: _program_raw(
                preformal.PREFORMAL_LOADER_SOURCE_RELATIVE
            ),
            preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE: _program_raw(
                preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE
            ),
            ACTIVATION_LOADER_RELATIVE: _program_raw(ACTIVATION_LOADER_RELATIVE),
            ACTIVATION_RECEIVER_RELATIVE: _program_raw(ACTIVATION_RECEIVER_RELATIVE),
            ACTIVATION_SERVICE_RELATIVE: _program_raw(ACTIVATION_SERVICE_RELATIVE),
            ACTIVATION_DRIVER_RELATIVE: _program_raw(ACTIVATION_DRIVER_RELATIVE),
            ACTIVATION_AUTHORITY_RELATIVE: _program_raw(
                ACTIVATION_AUTHORITY_RELATIVE
            ),
        }
        for root_pin in pins.values():
            root_pin.verify()
        root_identities = {
            label: selected.identity()
            for label, selected in (
                ("activation_collector", activation_pin),
                ("preformal", preformal_pin),
                ("resource", resource_pin),
                ("controls", control_pin),
            )
        }
        result = {
            "documents": documents,
            "raws": raws,
            "controls": controls,
            "programs": programs,
            "predecessor_chain": predecessor_chain,
            "evidence_roots": root_identities,
            "evidence_roots_index": index,
            "activation_final_evidence_index": final_index,
            "activation_final_evidence_index_raw": final_index_raw,
            "activation_read_only_snapshots": activation_snapshots,
            "activation_read_only_snapshot_raws": activation_snapshot_raws,
        }
    finally:
        for root_pin in reversed(list(pins.values())):
            root_pin.close()
    return result


def _verify_activation_collector_success(
    *, inputs: Mapping[str, Any], activation_plan: dict[str, Any],
    local_activation: dict[str, Any], network_start: dict[str, Any],
    preformal_receipt: dict[str, Any], remote_activation: dict[str, Any],
    service: dict[str, Any], ready: dict[str, Any],
    activation_terminal: dict[str, Any],
    remote_materialization: dict[str, Any],
    bootstrap_terminal: dict[str, Any],
) -> dict[str, Any]:
    """Require the collector's immutable successful read-only snapshot.

    A valid terminal DAG alone is insufficient: formal transport starts only
    from the exact snapshot selected by the collector's final evidence index.
    This also proves the terminal was observed through the no-mutation,
    before/after-stable classifier path.
    """

    snapshots = inputs.get("activation_read_only_snapshots")
    final_index = inputs.get("activation_final_evidence_index")
    docs = inputs["documents"]
    if type(snapshots) is not list or not snapshots or type(final_index) is not dict:
        _fail("activation collector final evidence is incomplete")
    final_fields = {
        "schema", "materialization_activation_plan_id",
        "activation_read_only_snapshot_id", "activation_classification_id",
        "remote_materialization_transport_terminal_id",
        "remote_materialization_attempt_id", "materialization_terminal_id",
        "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified",
        "bootstrap_terminal_exact_shared_materialization_ids_verified",
        "bootstrap_launcher_consumed_activation_transport_terminal_id",
        "downstream_launcher_terminal_id_join_remains_defense_in_depth",
        "formal_evidence_bundle_complete_under_bounded_successor_claim",
        "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim",
        "materialization_activation_final_evidence_index_id",
    }
    final_payload = dict(final_index)
    final_identifier = final_payload.pop(
        "materialization_activation_final_evidence_index_id", None
    )
    if (
        set(final_index) != final_fields
        or final_index.get("schema")
        != "acfqp.v42_materialization_activation_final_evidence_index.v42r1"
        or type(final_identifier) is not str
        or final_identifier
        != hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:activation-final-evidence-index\0"
            + canonical_json_bytes(final_payload)
        ).hexdigest()
        or final_index.get("materialization_activation_plan_id")
        != activation_plan["materialization_activation_plan_id"]
        or final_index.get("remote_materialization_transport_terminal_id")
        != activation_terminal["remote_materialization_transport_terminal_id"]
        or final_index.get("remote_materialization_attempt_id")
        != remote_materialization["remote_materialization_attempt_id"]
        or final_index.get("materialization_terminal_id")
        != bootstrap_terminal["materialization_terminal_id"]
        or final_index.get(
            "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified"
        ) is not True
        or final_index.get(
            "bootstrap_terminal_exact_shared_materialization_ids_verified"
        ) is not True
        or final_index.get(
            "bootstrap_launcher_consumed_activation_transport_terminal_id"
        ) is not False
        or final_index.get(
            "downstream_launcher_terminal_id_join_remains_defense_in_depth"
        ) is not True
        or final_index.get(
            "formal_evidence_bundle_complete_under_bounded_successor_claim"
        ) is not True
        or final_index.get(
            "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim"
        ) is not True
    ):
        _fail("activation collector final evidence index changed")

    previous_identifier: str | None = None
    selected: dict[str, Any] | None = None
    snapshot_fields = {
        "schema", "materialization_activation_plan_id", "snapshot_ordinal",
        "previous_snapshot_id", "observation", "classification",
        "remote_observation_only", "activation_effect_replay_authorized",
        "activation_read_only_snapshot_id",
    }
    for ordinal, snapshot in enumerate(snapshots, start=1):
        if type(snapshot) is not dict:
            _fail("activation read-only snapshot changed type")
        payload = dict(snapshot)
        identifier = payload.pop("activation_read_only_snapshot_id", None)
        if (
            set(snapshot) != snapshot_fields
            or snapshot.get("schema")
            != "acfqp.v42_materialization_activation_read_only_snapshot.v42r1"
            or snapshot.get("materialization_activation_plan_id")
            != activation_plan["materialization_activation_plan_id"]
            or snapshot.get("snapshot_ordinal") != ordinal
            or snapshot.get("previous_snapshot_id") != previous_identifier
            or snapshot.get("remote_observation_only") is not True
            or snapshot.get("activation_effect_replay_authorized") is not False
            or type(identifier) is not str
            or identifier
            != hashlib.sha256(
                b"acfqp:v42-remote-ordinal2:activation-read-only-snapshot\0"
                + canonical_json_bytes(payload)
            ).hexdigest()
        ):
            _fail("activation read-only snapshot chain changed")
        if identifier == final_index["activation_read_only_snapshot_id"]:
            if selected is not None:
                _fail("activation final snapshot identity is duplicated")
            selected = snapshot
        previous_identifier = identifier
    if selected is None or selected is not snapshots[-1]:
        _fail("activation final evidence index did not select the retained snapshot tail")

    observed = selected.get("observation")
    classification = selected.get("classification")
    observation_fields = {
        "schema", "materialization_activation_plan_id",
        "local_materialization_activation_attempt_id", "observation_before",
        "observation_after", "remote_documents", "fixed_root_evidence",
        "remote_mutation_performed",
        "only_read_only_ssh_ingress_and_systemctl_query_processes_started",
        "additional_durable_or_mutating_remote_process_started",
        "activation_retry_authorized",
    }
    if (
        type(observed) is not dict
        or set(observed) != observation_fields
        or observed.get("schema")
        != "acfqp.v42_remote_ordinal2_materialization_activation_read_only_observation.v42r1"
        or observed.get("materialization_activation_plan_id")
        != activation_plan["materialization_activation_plan_id"]
        or observed.get("local_materialization_activation_attempt_id")
        != local_activation["local_materialization_activation_attempt_id"]
        or observed.get("observation_before") != observed.get("observation_after")
        or observed.get("remote_mutation_performed") is not False
        or observed.get(
            "only_read_only_ssh_ingress_and_systemctl_query_processes_started"
        ) is not True
        or observed.get(
            "additional_durable_or_mutating_remote_process_started"
        ) is not False
        or observed.get("activation_retry_authorized") is not False
    ):
        _fail("activation collector observation changed effect semantics")
    remote_documents = observed.get("remote_documents")
    expected_remote_documents = {
        "remote_attempt": remote_activation,
        "service_receipt": service,
        "publish_ready": ready,
        "terminal": activation_terminal,
        "failure": None,
    }
    if remote_documents != expected_remote_documents:
        _fail("activation collector terminal documents changed")
    fixed = observed.get("fixed_root_evidence")
    if (
        type(fixed) is not dict
        or set(fixed)
        != {
            "inventory_before", "inventory_after", "documents",
            "collected_subset_only_not_whole_tree",
        }
        or fixed.get("inventory_before") != fixed.get("inventory_after")
        or fixed.get("collected_subset_only_not_whole_tree") is not True
        or type(fixed.get("documents")) is not dict
    ):
        _fail("activation collector fixed-root evidence changed")
    fixed_documents = fixed["documents"]
    expected_fixed_names = {
        authority.SOURCE_MANIFEST_NAME,
        authority.TRANSPORT_MANIFEST_NAME,
        authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        BOOTSTRAP_REMOTE_ATTEMPT_FILE,
        BOOTSTRAP_TERMINAL_FILE,
    }
    if (
        not expected_fixed_names <= fixed_documents.keys()
        or any(fixed_documents[name] != docs[name] for name in expected_fixed_names)
    ):
        _fail("activation collector fixed-root documents changed")
    rebuilt = activation.verify_materialization_activation_classification_v42r1(
        classification,
        activation_plan=activation_plan,
        local_attempt=local_activation,
        network_start=network_start,
        preformal_receipt=preformal_receipt,
        remote_attempt=remote_activation,
        service_receipt=service,
        publish_ready=ready,
        terminal=activation_terminal,
        failure=None,
        observation_before=observed["observation_before"],
        observation_after=observed["observation_after"],
    )
    if (
        rebuilt.get("classification") != activation.CLASSIFICATION_SUCCESS
        or rebuilt.get("reason")
        != "DURABLE_TERMINAL_AND_EXACT_FIXED_FIVE_CONTROLS"
        or rebuilt.get("materialization_activation_classification_id")
        != final_index["activation_classification_id"]
        or rebuilt.get("remote_materialization_transport_terminal_id")
        != activation_terminal["remote_materialization_transport_terminal_id"]
    ):
        _fail("activation collector did not retain exact successful classification")
    return rebuilt


def _verify_production_activation_chain(inputs: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    """Run every real activation and bootstrap verifier; no shape adapter."""

    docs = inputs["documents"]
    raws = inputs["raws"]
    controls = inputs["controls"]
    programs = inputs["programs"]
    chain = inputs["predecessor_chain"]
    plan = preformal.verify_preformal_upload_plan_against_controls_v42r1(
        docs[PREFORMAL_PLAN_FILE],
        control_raw_by_name=controls,
        loader_source_raw=programs[preformal.PREFORMAL_LOADER_SOURCE_RELATIVE],
        receiver_source_raw=programs[preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE],
        predecessor_chain=chain,
    )
    attempt = preformal.verify_preformal_upload_attempt_against_controls_v42r1(
        docs[PREFORMAL_ATTEMPT_FILE], plan=plan,
        control_raw_by_name=controls,
        loader_source_raw=programs[preformal.PREFORMAL_LOADER_SOURCE_RELATIVE],
        receiver_source_raw=programs[preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE],
        predecessor_chain=chain,
    )
    receipt = preformal.verify_preformal_upload_receipt_against_controls_v42r1(
        docs[PREFORMAL_RECEIPT_FILE], plan=plan, attempt=attempt,
        control_raw_by_name=controls,
        loader_source_raw=programs[preformal.PREFORMAL_LOADER_SOURCE_RELATIVE],
        receiver_source_raw=programs[preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE],
        predecessor_chain=chain,
    )
    outcome = preformal.verify_preformal_upload_outcome_v42r1(
        docs[PREFORMAL_OUTCOME_FILE], plan=plan, attempt=attempt, receipt=receipt
    )
    resource_plan = activation.verify_preactivation_resource_probe_plan_v42r1(
        docs[PREACTIVATION_PLAN_FILE],
        preformal_plan=plan, preformal_attempt=attempt,
        preformal_receipt=receipt, preformal_outcome=outcome,
        loader_source_raw=programs[ACTIVATION_LOADER_RELATIVE],
        receiver_source_raw=programs[ACTIVATION_RECEIVER_RELATIVE],
        service_source_raw=programs[ACTIVATION_SERVICE_RELATIVE],
        driver_source_raw=programs[ACTIVATION_DRIVER_RELATIVE],
        activation_authority_source_raw=programs[ACTIVATION_AUTHORITY_RELATIVE],
        control_raw_by_name=controls,
    )
    resource_result = activation.verify_preactivation_resource_result_v42r1(
        docs[PREACTIVATION_RESULT_FILE], resource_plan=resource_plan,
        preformal_receipt=receipt,
    )
    activation_plan = activation.verify_materialization_activation_plan_v42r1(
        docs[ACTIVATION_PLAN_FILE],
        preformal_plan=plan, preformal_attempt=attempt,
        resource_plan=resource_plan, resource_result=resource_result,
        preformal_receipt=receipt, preformal_outcome=outcome,
        control_raw_by_name=controls,
        loader_source_raw=programs[ACTIVATION_LOADER_RELATIVE],
        receiver_source_raw=programs[ACTIVATION_RECEIVER_RELATIVE],
        service_source_raw=programs[ACTIVATION_SERVICE_RELATIVE],
        driver_source_raw=programs[ACTIVATION_DRIVER_RELATIVE],
        activation_authority_source_raw=programs[ACTIVATION_AUTHORITY_RELATIVE],
    )
    local_activation = activation.verify_local_materialization_activation_attempt_v42r1(
        docs[ACTIVATION_ATTEMPT_FILE], activation_plan=activation_plan
    )
    network_start = activation.verify_materialization_activation_network_start_v42r1(
        docs[ACTIVATION_NETWORK_START_FILE], activation_plan=activation_plan,
        local_attempt=local_activation,
    )
    remote_activation = activation.verify_remote_materialization_activation_attempt_v42r1(
        docs[REMOTE_ACTIVATION_ATTEMPT_FILE], activation_plan=activation_plan,
        local_attempt=local_activation, network_start=network_start,
    )
    service = activation.verify_remote_activation_service_receipt_v42r1(
        docs[ACTIVATION_SERVICE_RECEIPT_FILE], activation_plan=activation_plan,
        remote_attempt=remote_activation,
    )
    ready = activation.verify_remote_activation_publish_ready_v42r1(
        docs[ACTIVATION_READY_FILE], activation_plan=activation_plan,
        remote_attempt=remote_activation, service_receipt=service,
        preformal_receipt=receipt,
    )
    activation_terminal = activation.verify_remote_materialization_transport_terminal_v42r1(
        raws[ACTIVATION_TERMINAL_FILE], activation_plan=activation_plan,
        remote_attempt=remote_activation, service_receipt=service,
        publish_ready=ready, preformal_receipt=receipt,
    )
    source = authority.verify_source_manifest_v42r1(
        raws[authority.SOURCE_MANIFEST_NAME]
    )
    transport = authority.verify_transport_manifest_v42r1(
        raws[authority.TRANSPORT_MANIFEST_NAME], source_manifest=source
    )
    local_materialization = authority.verify_local_materialization_attempt_v42r1(
        raws[authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME],
        source_manifest=source, transport_manifest=transport,
    )
    remote_materialization = authority.verify_remote_materialization_attempt_v42r1(
        raws[BOOTSTRAP_REMOTE_ATTEMPT_FILE],
        local_materialization_attempt=local_materialization,
        source_manifest=source, transport_manifest=transport,
    )
    bootstrap_terminal = authority.verify_materialization_terminal_v42r1(
        raws[BOOTSTRAP_TERMINAL_FILE],
        local_materialization_attempt=local_materialization,
        remote_materialization_attempt=remote_materialization,
        source_manifest=source, transport_manifest=transport,
    )
    if (
        activation_terminal["source_manifest_id"] != source["source_manifest_id"]
        or activation_terminal["transport_manifest_id"]
        != transport["transport_manifest_id"]
        or activation_terminal["local_materialization_attempt_id"]
        != local_materialization["local_materialization_attempt_id"]
        or activation_terminal["trusted_bootstrap_outer_command"]
        != local_materialization["remote_bootstrap_outer_command"]
        or activation_terminal["formal_outer_exec_enabled_after_service_successor_join"]
        is not True
        or bootstrap_terminal["source_manifest_id"]
        != activation_terminal["source_manifest_id"]
        or bootstrap_terminal["transport_manifest_id"]
        != activation_terminal["transport_manifest_id"]
    ):
        _fail("activation transport terminal/bootstrap materialization join changed")
    _verify_activation_collector_success(
        inputs=inputs, activation_plan=activation_plan,
        local_activation=local_activation, network_start=network_start,
        preformal_receipt=receipt, remote_activation=remote_activation,
        service=service, ready=ready, activation_terminal=activation_terminal,
        remote_materialization=remote_materialization,
        bootstrap_terminal=bootstrap_terminal,
    )
    core = formal.build_production_activation_core_v42r1(
        activation_terminal_id=activation_terminal[
            "remote_materialization_transport_terminal_id"
        ],
        preactivation_resource_result_id=resource_result[
            "preactivation_resource_result_id"
        ],
        source_commit=source["source_commit"], source_tree=source["source_tree"],
        source_manifest_id=source["source_manifest_id"],
        transport_manifest_id=transport["transport_manifest_id"],
        local_materialization_attempt_id=local_materialization[
            "local_materialization_attempt_id"
        ],
        remote_materialization_attempt_id=remote_materialization[
            "remote_materialization_attempt_id"
        ],
        materialization_terminal_id=bootstrap_terminal[
            "materialization_terminal_id"
        ],
        materialization_activation_final_evidence_index_id=inputs[
            "activation_final_evidence_index"
        ]["materialization_activation_final_evidence_index_id"],
    )
    return core, raws[ACTIVATION_TERMINAL_FILE]


def production_activation_validator_v42r1(
    *, inputs: Mapping[str, Any], host_epoch_receipt: Mapping[str, Any],
) -> tuple[bytes, Callable[[bytes], dict[str, Any]], dict[str, Any]]:
    """Return the only adapter accepted by this production driver."""

    core, terminal_raw = _verify_production_activation_chain(inputs)
    epoch = formal.verify_formal_host_epoch_receipt_v42r1(
        dict(host_epoch_receipt), activation_core=core
    )

    def validate(candidate_raw: bytes) -> dict[str, Any]:
        rebuilt_core, rebuilt_raw = _verify_production_activation_chain(inputs)
        if candidate_raw != terminal_raw or rebuilt_raw != terminal_raw or rebuilt_core != core:
            _fail("activation terminal bytes/core changed during production adapter call")
        return formal.production_activation_binding_v42r1(
            activation_core=rebuilt_core, host_epoch_receipt=epoch
        )

    return terminal_raw, validate, core


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _stat_state(value: os.stat_result) -> tuple[int, ...]:
    return tuple(
        getattr(value, field)
        for field in (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid",
            "st_size", "st_mtime_ns", "st_ctime_ns",
        )
    )


def _directory_identity(value: os.stat_result) -> tuple[int, ...]:
    """Return only stable directory identity fields.

    Publishing a child legitimately changes a directory's link count, size,
    and timestamps; those fields therefore cannot participate in the held-root
    identity.  The parent named-child rejoin below makes the remaining inode
    identity durable across processes.
    """

    return tuple(
        getattr(value, field)
        for field in (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid",
        )
    )


def _journal_root_identity(value: os.stat_result) -> dict[str, Any]:
    return {
        "schema": "acfqp.v42_formal_local_journal_root_identity.v42r1",
        "path": str(formal.LOCAL_FORMAL_JOURNAL_ROOT),
        "st_dev": value.st_dev,
        "st_ino": value.st_ino,
        "mode": stat.S_IMODE(value.st_mode),
        "uid": value.st_uid,
        "gid": value.st_gid,
    }


def _journal_anchor_name(suffix: str) -> str:
    root = formal.LOCAL_FORMAL_JOURNAL_ROOT
    if "/" in suffix or not suffix:
        _fail("formal journal anchor suffix changed")
    return "." + root.name + "." + suffix


def _open_directory_chain(path: Path) -> list[tuple[int, str | None, tuple[int, ...]]]:
    if not path.is_absolute() or ".." in path.parts:
        _fail("formal journal directory chain changed")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    result: list[tuple[int, str | None, tuple[int, ...]]] = [
        (descriptor, None, _directory_identity(os.fstat(descriptor)))
    ]
    try:
        for component in path.parts[1:]:
            before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                _fail("formal journal directory component changed type")
            successor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            opened = os.fstat(successor)
            if _directory_identity(before) != _directory_identity(opened):
                os.close(successor)
                _fail("formal journal directory component changed during open")
            result.append((successor, component, _directory_identity(opened)))
            descriptor = successor
        return result
    except BaseException:
        for opened, _, _ in reversed(result):
            os.close(opened)
        raise


def _verify_directory_chain(
    chain: Sequence[tuple[int, str | None, tuple[int, ...]]]
) -> None:
    for index, (descriptor, name, identity) in enumerate(chain):
        if _directory_identity(os.fstat(descriptor)) != identity:
            _fail("formal journal held directory component changed")
        if index:
            parent_descriptor = chain[index - 1][0]
            assert name is not None
            named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            if _directory_identity(named) != identity:
                _fail("formal journal named directory component changed")


def _read_regular_at(
    directory_fd: int, name: str, cap: int, *, mode: int
) -> bytes:
    named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
        | os.O_CLOEXEC,
        dir_fd=directory_fd,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > cap
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("formal journal anchored artifact changed")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("formal journal anchored artifact ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("formal journal anchored artifact grew during read")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if _stat_state(before) != _stat_state(after) or _stat_state(after) != _stat_state(final):
        _fail("formal journal anchored artifact changed during read")
    return b"".join(chunks)


@dataclass
class _JournalPin:
    descriptor: int
    parent_descriptor: int
    directory_chain: list[tuple[int, str | None, tuple[int, ...]]]
    root_state: tuple[int, ...]
    root_identity: dict[str, Any]
    closed: bool = False

    @classmethod
    def open(cls) -> "_JournalPin":
        root = formal.LOCAL_FORMAL_JOURNAL_ROOT
        directory_chain = _open_directory_chain(root.parent)
        parent_descriptor = directory_chain[-1][0]
        descriptor = os.open(
            root.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_descriptor,
        )
        observed = os.fstat(descriptor)
        named = os.stat(root.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISDIR(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o700
            or observed.st_uid != os.geteuid()
            or observed.st_gid != os.getegid()
            or (observed.st_dev, observed.st_ino) != (named.st_dev, named.st_ino)
            or root.resolve(strict=True) != root
        ):
            os.close(descriptor)
            for opened, _, _ in reversed(directory_chain):
                os.close(opened)
            _fail("formal journal root pin changed")
        identity = _journal_root_identity(observed)
        anchor = _journal_anchor_name("ROOT_IDENTITY.json")
        anchor_path = root.parent / anchor
        try:
            retained = _read_regular_at(
                parent_descriptor, anchor_path.name, 4096, mode=0o400
            )
        except FileNotFoundError:
            os.close(descriptor)
            for opened, _, _ in reversed(directory_chain):
                os.close(opened)
            _fail("formal journal root identity anchor is absent")
        if retained != canonical_json_bytes(identity):
            os.close(descriptor)
            for opened, _, _ in reversed(directory_chain):
                os.close(opened)
            _fail("formal journal root identity anchor changed")
        result = cls(
            descriptor=descriptor,
            parent_descriptor=parent_descriptor,
            directory_chain=directory_chain,
            root_state=_directory_identity(observed),
            root_identity=identity,
        )
        result.verify_root()
        return result

    def verify_root(self) -> None:
        if self.closed:
            _fail("formal journal root pin is closed")
        _verify_directory_chain(self.directory_chain)
        observed = os.fstat(self.descriptor)
        named = os.stat(
            formal.LOCAL_FORMAL_JOURNAL_ROOT.name,
            dir_fd=self.parent_descriptor,
            follow_symlinks=False,
        )
        if (
            _directory_identity(observed) != self.root_state
            or (observed.st_dev, observed.st_ino) != (named.st_dev, named.st_ino)
            or _journal_root_identity(observed) != self.root_identity
        ):
            _fail("formal journal root changed while pinned")
        anchor_raw = _read_regular_at(
            self.parent_descriptor,
            _journal_anchor_name("ROOT_IDENTITY.json"),
            4096,
            mode=0o400,
        )
        if anchor_raw != canonical_json_bytes(self.root_identity):
            _fail("formal journal root identity anchor changed while pinned")

    def exists(self, name: str) -> bool:
        self.verify_root()
        try:
            observed = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return False
        if not stat.S_ISREG(observed.st_mode):
            _fail("formal journal fixed name is nonregular")
        return True

    def parent_anchor_exists(self, name: str) -> bool:
        self.verify_root()
        try:
            observed = os.stat(
                name, dir_fd=self.parent_descriptor, follow_symlinks=False
            )
        except FileNotFoundError:
            return False
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o400
            or observed.st_uid != os.geteuid()
            or observed.st_gid != os.getegid()
            or observed.st_nlink != 1
        ):
            _fail("formal journal parent anchor changed")
        return True

    def publish(self, name: str, raw: bytes) -> tuple[int, ...]:
        self.verify_root()
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o400,
            dir_fd=self.descriptor,
        )
        try:
            os.fchmod(descriptor, 0o400)
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    _fail("formal journal publication made no progress")
                view = view[written:]
            os.fsync(descriptor)
            observed = os.fstat(descriptor)
            if (
                not stat.S_ISREG(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o400
                or observed.st_uid != os.geteuid()
                or observed.st_nlink != 1
                or observed.st_size != len(raw)
            ):
                _fail("formal journal published inode changed")
            state = _stat_state(observed)
        finally:
            os.close(descriptor)
        os.fsync(self.descriptor)
        named = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
        if _stat_state(named) != state:
            _fail("formal journal named inode differs after publication")
        self.verify_root()
        return state

    def publish_parent_anchor(self, name: str, raw: bytes) -> tuple[int, ...]:
        self.verify_root()
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            0o400,
            dir_fd=self.parent_descriptor,
        )
        try:
            os.fchmod(descriptor, 0o400)
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    _fail("formal journal parent anchor write made no progress")
                view = view[written:]
            os.fsync(descriptor)
            observed = os.fstat(descriptor)
            if (
                not stat.S_ISREG(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o400
                or observed.st_uid != os.geteuid()
                or observed.st_gid != os.getegid()
                or observed.st_nlink != 1
                or observed.st_size != len(raw)
            ):
                _fail("formal journal parent anchor inode changed")
            state = _stat_state(observed)
        finally:
            os.close(descriptor)
        os.fsync(self.parent_descriptor)
        named = os.stat(name, dir_fd=self.parent_descriptor, follow_symlinks=False)
        if _stat_state(named) != state:
            _fail("formal journal parent anchor named inode changed")
        self.verify_root()
        return state

    def verify_artifact(self, name: str, state: tuple[int, ...]) -> None:
        self.verify_root()
        observed = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
        if _stat_state(observed) != state:
            _fail("formal journal marker changed while effect was pending")

    def verify_parent_anchor(self, name: str, state: tuple[int, ...]) -> None:
        self.verify_root()
        observed = os.stat(
            name, dir_fd=self.parent_descriptor, follow_symlinks=False
        )
        if _stat_state(observed) != state:
            _fail("formal journal effect cut anchor changed")

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            os.close(self.descriptor)
            for opened, _, _ in reversed(self.directory_chain):
                os.close(opened)


def _ensure_journal_root() -> None:
    root = formal.LOCAL_FORMAL_JOURNAL_ROOT
    parent = root.parent
    observed_parent = parent.lstat()
    if (
        not stat.S_ISDIR(observed_parent.st_mode)
        or observed_parent.st_uid != os.geteuid()
        or parent.resolve(strict=True) != parent
    ):
        _fail("formal journal parent changed")
    created = False
    try:
        previous = os.umask(0o077)
        try:
            os.mkdir(root, 0o700)
            created = True
        finally:
            os.umask(previous)
        _fsync_directory(parent)
    except FileExistsError:
        pass
    observed = root.lstat()
    if (
        not stat.S_ISDIR(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o700
        or observed.st_uid != os.geteuid()
        or observed.st_gid != os.getegid()
        or root.resolve(strict=True) != root
    ):
        _fail("formal journal root changed")
    identity_raw = canonical_json_bytes(_journal_root_identity(observed))
    anchor_path = parent / _journal_anchor_name("ROOT_IDENTITY.json")
    if created:
        parent_pin = os.open(
            parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        try:
            descriptor = os.open(
                anchor_path.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                0o400,
                dir_fd=parent_pin,
            )
            try:
                os.fchmod(descriptor, 0o400)
                view = memoryview(identity_raw)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        _fail("formal journal root anchor write made no progress")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.fsync(parent_pin)
        finally:
            os.close(parent_pin)
    retained = _stable_read(anchor_path, 4096, mode=0o400)
    if retained != identity_raw:
        _fail("formal journal root identity differs from retained anchor")


def _publish_once(path: Path, raw: bytes) -> None:
    if path.parent != formal.LOCAL_FORMAL_JOURNAL_ROOT:
        _fail("formal journal publication escaped its fixed root")
    pin = _JournalPin.open()
    try:
        pin.publish(path.name, raw)
    finally:
        pin.close()


def _publish_or_verify(path: Path, raw: bytes) -> None:
    try:
        _publish_once(path, raw)
    except FileExistsError:
        retained = _stable_read(path, max(len(raw), 1), mode=0o400)
        if retained != raw:
            _fail(f"retained formal journal artifact changed: {path.name}")


def _effect_cut_present(
    *, operation: str, attempt_id: str, marker_path: Path
) -> bool:
    pin = _JournalPin.open()
    try:
        cut_name = _journal_anchor_name(
            "NETWORK_START." + operation + "." + attempt_id + ".json"
        )
        return pin.exists(marker_path.name) or pin.parent_anchor_exists(cut_name)
    finally:
        pin.close()


def _verify_driver_self(plan: Mapping[str, Any], driver_raw: bytes) -> None:
    live = _stable_read(Path(__file__).resolve(strict=True), 4 * 1024**2)
    fact = plan["driver_artifact"]
    if (
        live != driver_raw
        or len(live) != fact["byte_count"]
        or hashlib.sha256(live).hexdigest() != fact["sha256"]
        or fact["relative_path"] != formal.FORMAL_DRIVER_RELATIVE
    ):
        _fail("executing formal driver bytes do not join the plan")


def _strip_one_newline(raw: bytes, label: str) -> bytes:
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail(f"{label} stdout is not one canonical document plus newline")
    return raw[:-1]


def _prepare_formal_pinned_child(
    *, executable_fd: int, argv: tuple[str, ...], environment: dict[str, str],
    segments: tuple[bytes, ...], stdout_cap: int, stderr_cap: int,
    timeout_seconds: float,
) -> frozen_sender._PreparedPinnedChild:  # noqa: SLF001
    """Local adapter that lifts only stdout to the authority's 64 MiB cap."""

    if (
        type(stdout_cap) is not int
        or not 0 < stdout_cap <= max(
            formal.MAX_PREPARE_RECEIPT_BYTES, formal.MAX_INSPECTION_BYTES
        )
        or type(stderr_cap) is not int
        or not 0 < stderr_cap <= 1024**2
        or type(timeout_seconds) is not float
        or not 0.0 < timeout_seconds <= frozen_sender.SENDER_CHILD_TIMEOUT_SECONDS
    ):
        _fail("formal pinned child bounded resource contract changed")
    descriptors: list[int] = []
    try:
        stdin_read, stdin_write = frozen_sender._pipe_cloexec()  # noqa: SLF001
        descriptors.extend((stdin_read, stdin_write))
        stdout_read, stdout_write = frozen_sender._pipe_cloexec()  # noqa: SLF001
        descriptors.extend((stdout_read, stdout_write))
        stderr_read, stderr_write = frozen_sender._pipe_cloexec()  # noqa: SLF001
        descriptors.extend((stderr_read, stderr_write))
        status_read, status_write = frozen_sender._pipe_cloexec()  # noqa: SLF001
        descriptors.extend((status_read, status_write))
        prepared = frozen_sender._PreparedPinnedChild(  # noqa: SLF001
            executable_fd=executable_fd, argv=argv,
            environment=dict(environment), segments=segments,
            stdout_cap=stdout_cap, stderr_cap=stderr_cap,
            timeout_seconds=timeout_seconds,
            stdin_read=stdin_read, stdin_write=stdin_write,
            stdout_read=stdout_read, stdout_write=stdout_write,
            stderr_read=stderr_read, stderr_write=stderr_write,
            exec_status_read=status_read, exec_status_write=status_write,
        )
        prepared.verify_prepared()
        return prepared
    except BaseException:
        for descriptor in descriptors:
            frozen_sender._close_noexcept(descriptor)  # noqa: SLF001
        raise


def _dispatch_read_only(
    *, ssh_plan: Mapping[str, Any], argv: tuple[str, ...], ingress_raw: bytes,
    stdout_cap: int, timeout: float,
) -> frozen_sender._ChildObservation:  # noqa: SLF001
    pins = frozen_sender._open_local_dispatch_pins_v42r1(dict(ssh_plan))  # noqa: SLF001
    prepared: frozen_sender._PreparedPinnedChild | None = None  # noqa: SLF001
    try:
        fingerprint = frozen_sender._derive_identity_fingerprint_v42r1(  # noqa: SLF001
            plan=dict(ssh_plan), pins=pins
        )
        if fingerprint != ssh_plan["ssh_client_contract"]["identity_public_fingerprint"]:
            _fail("last read-only SSH identity fingerprint changed")
        prepared = _prepare_formal_pinned_child(
            executable_fd=pins.ssh.descriptor,
            argv=argv,
            environment=dict(preformal.LOCAL_DISPATCH_ENVIRONMENT),
            segments=(ingress_raw,), stdout_cap=stdout_cap,
            stderr_cap=STDERR_CAP, timeout_seconds=float(timeout),
        )
        pins.verify()
        return prepared.spawn_and_pump()
    finally:
        if prepared is not None:
            prepared.close()
        pins.close()


def _dispatch_effect_once(
    *, plan: dict[str, Any], operation: str, attempt_id: str,
    ingress_raw: bytes, marker_path: Path, stdout_cap: int, timeout: float,
) -> tuple[frozen_sender._ChildObservation | None, bool, BaseException | None]:  # noqa: SLF001
    journal_pin = _JournalPin.open()
    cut_name = _journal_anchor_name(
        "NETWORK_START." + operation + "." + attempt_id + ".json"
    )
    if (
        journal_pin.exists(marker_path.name)
        or journal_pin.parent_anchor_exists(cut_name)
    ):
        journal_pin.close()
        _fail("network marker already exists; same effect replay is forbidden")
    argv = formal.materialize_ssh_argv_v42r1(plan, operation)
    pins = frozen_sender._open_local_dispatch_pins_v42r1(plan)  # noqa: SLF001
    prepared: frozen_sender._PreparedPinnedChild | None = None  # noqa: SLF001
    sigpipe: frozen_sender._SigpipeIgnoreGuard | None = None  # noqa: SLF001
    marker_may_have_started = False
    observation = None
    failure: BaseException | None = None
    marker_state: tuple[int, ...] | None = None
    cut_state: tuple[int, ...] | None = None
    try:
        fingerprint = frozen_sender._derive_identity_fingerprint_v42r1(  # noqa: SLF001
            plan=plan, pins=pins
        )
        if fingerprint != plan["ssh_client_contract"]["identity_public_fingerprint"]:
            _fail("last effectful SSH identity fingerprint changed")
        prepared = _prepare_formal_pinned_child(
            executable_fd=pins.ssh.descriptor, argv=argv,
            environment=dict(preformal.LOCAL_DISPATCH_ENVIRONMENT),
            segments=(ingress_raw,), stdout_cap=stdout_cap,
            stderr_cap=STDERR_CAP, timeout_seconds=float(timeout),
        )
        sigpipe = frozen_sender._SigpipeIgnoreGuard.acquire()  # noqa: SLF001
        prepared.verify_prepared()
        pins.verify()
        sigpipe.verify()
        marker = formal.build_network_start_v42r1(
            plan=plan,
            operation=(
                formal.OPERATION_PREPARE
                if operation == "prepare_once"
                else formal.OPERATION_LAUNCH
            ),
            attempt_id=attempt_id,
        )
        # Set the conservative flag before O_EXCL: a Python asynchronous
        # exception can arrive immediately after the kernel creates the name.
        marker_may_have_started = True
        marker_raw = canonical_json_bytes(marker)
        # The parent cut comes first.  If an asynchronous exception lands
        # before the inner marker publication, the next process still sees a
        # durable no-replay boundary outside the journal root.
        cut_state = journal_pin.publish_parent_anchor(cut_name, marker_raw)
        marker_state = journal_pin.publish(marker_path.name, marker_raw)
        prepared.verify_prepared()
        pins.verify()
        sigpipe.verify()
        journal_pin.verify_artifact(marker_path.name, marker_state)
        journal_pin.verify_parent_anchor(cut_name, cut_state)
        observation = prepared.spawn_and_pump()
        sigpipe.verify()
        pins.verify()
        journal_pin.verify_artifact(marker_path.name, marker_state)
        journal_pin.verify_parent_anchor(cut_name, cut_state)
    except BaseException as error:
        failure = error
        if not marker_may_have_started:
            try:
                marker_may_have_started = (
                    journal_pin.exists(marker_path.name)
                    or journal_pin.parent_anchor_exists(cut_name)
                )
            except BaseException:
                marker_may_have_started = True
    finally:
        if prepared is not None:
            prepared.close()
        pins.close()
        if sigpipe is not None:
            try:
                sigpipe.close()
            except BaseException as error:
                if failure is None:
                    failure = error
        journal_pin.close()
    return observation, marker_may_have_started, failure


def _observation_closed_exactly(
    observation: frozen_sender._ChildObservation | None,  # noqa: SLF001
) -> bool:
    return bool(
        observation is not None
        and observation.exec_succeeded
        and observation.returncode == 0
        and not observation.timed_out
        and observation.stdin_complete
        and observation.stdin_sent_byte_count
        == observation.stdin_expected_byte_count
        and not observation.stdout_overflow
        and observation.stdout_eof
        and observation.stdout_total_byte_count == len(observation.stdout_raw)
        and observation.stderr_total_byte_count == 0
        and observation.stderr_eof
    )


def _probe_ssh_plan(core: Mapping[str, Any]) -> dict[str, Any]:
    known_hosts = str(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_KNOWN_HOSTS_NAME
    )
    return {
        "ssh_client_contract": preformal._ssh_client_contract(known_hosts),  # noqa: SLF001
        "production_activation_core_id": core["production_activation_core_id"],
    }


def _probe_host_epoch(
    *, core: dict[str, Any], receiver_raw: bytes, formal_authority_raw: bytes,
) -> dict[str, Any]:
    ssh_plan = _probe_ssh_plan(core)
    receiver_artifact = _artifact(receiver_raw, formal.FORMAL_RECEIVER_RELATIVE)
    authority_artifact = _artifact(
        formal_authority_raw, formal.FORMAL_AUTHORITY_RELATIVE
    )
    receiver_path = str(
        authority.REMOTE_SOURCE_ROOT / formal.FORMAL_RECEIVER_RELATIVE
    )
    remote_command = formal._remote_command(  # noqa: SLF001
        receiver_path, receiver_artifact, "--probe-host-epoch", "",
        core["source_manifest_id"], core["transport_manifest_id"],
    )
    # Probe mode has no plan ID argument.  Remove the exact two empty sentinel
    # arguments emitted by the ordinary plan command constructor.
    suffix = " --formal-transport-plan-id ''"
    if not remote_command.endswith(suffix):
        _fail("host epoch probe remote command template changed")
    remote_command = remote_command[: -len(suffix)]
    argv = tuple(
        formal._ssh_argv(  # noqa: SLF001
            known_hosts_path=ssh_plan["ssh_client_contract"]["known_hosts_path"],
            remote_command=remote_command,
        )
    )
    ingress = {
        "schema": "acfqp.v42_formal_transport_host_epoch_probe_ingress.v42r1",
        "schema_version": authority.SCHEMA_VERSION,
        "production_activation_core": core,
        "receiver_artifact": receiver_artifact,
        "formal_authority_artifact": authority_artifact,
    }
    observation = _dispatch_read_only(
        ssh_plan=ssh_plan, argv=argv, ingress_raw=canonical_json_bytes(ingress),
        stdout_cap=formal.MAX_INSPECTION_BYTES,
        timeout=formal.INSPECTION_TRANSPORT_TIMEOUT_SECONDS,
    )
    if not _observation_closed_exactly(observation):
        _fail("read-only host epoch probe did not close exactly")
    raw = _strip_one_newline(observation.stdout_raw, "host epoch probe")
    receipt = formal.verify_formal_host_epoch_receipt_v42r1(
        raw, activation_core=core
    )
    _publish_or_verify(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / HOST_EPOCH_RECEIPT_FILE, raw
    )
    return receipt


def _build_plan(
    *, inputs: Mapping[str, Any], host_epoch_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes]:
    activation_raw, validator, core = production_activation_validator_v42r1(
        inputs=inputs, host_epoch_receipt=host_epoch_receipt
    )
    receiver_raw = _program_raw(formal.FORMAL_RECEIVER_RELATIVE)
    driver_raw = _program_raw(formal.FORMAL_DRIVER_RELATIVE)
    authority_raw = _program_raw(formal.FORMAL_AUTHORITY_RELATIVE)
    source_manifest = authority.verify_source_manifest_v42r1(
        inputs["raws"][authority.SOURCE_MANIFEST_NAME]
    )
    transport_manifest = authority.verify_transport_manifest_v42r1(
        inputs["raws"][authority.TRANSPORT_MANIFEST_NAME],
        source_manifest=source_manifest,
    )
    facts = {
        row["relative_path"]: row
        for row in transport_manifest["transport_facts"]
    }
    for relative, raw in (
        (formal.FORMAL_RECEIVER_RELATIVE, receiver_raw),
        (formal.FORMAL_DRIVER_RELATIVE, driver_raw),
        (formal.FORMAL_AUTHORITY_RELATIVE, authority_raw),
    ):
        fact = facts.get(relative)
        if (
            type(fact) is not dict
            or fact.get("byte_count") != len(raw)
            or fact.get("sha256") != hashlib.sha256(raw).hexdigest()
        ):
            _fail(
                "formal TCB artifact is not in the activated transport manifest: "
                + relative
            )
    plan = formal.build_formal_transport_plan_v42r1(
        activation_terminal_raw=activation_raw,
        activation_terminal_validator=validator,
        receiver_source_raw=receiver_raw,
        driver_source_raw=driver_raw,
        formal_authority_source_raw=authority_raw,
    )
    _verify_driver_self(plan, driver_raw)
    if plan["activation_binding"]["activation_terminal_id"] != core["activation_terminal_id"]:
        _fail("production formal plan lost its activation terminal join")
    return plan, activation_raw, core, driver_raw


def _persist_plan_prefix(
    plan: dict[str, Any], activation_raw: bytes, *, inputs: Mapping[str, Any],
) -> None:
    _publish_or_verify(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_PLAN_NAME,
        canonical_json_bytes(plan),
    )
    _publish_or_verify(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_ACTIVATION_TERMINAL_NAME,
        activation_raw,
    )
    payload = {
        "schema": "acfqp.v42_formal_activation_evidence_assembly.v42r1",
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "activation_terminal_sha256": hashlib.sha256(activation_raw).hexdigest(),
        "activation_evidence_roots_index": inputs["evidence_roots_index"],
        "pinned_evidence_root_identities": inputs["evidence_roots"],
        "materialization_activation_final_evidence_index_id": inputs[
            "activation_final_evidence_index"
        ]["materialization_activation_final_evidence_index_id"],
        "all_split_roots_held_and_named_rejoined_across_complete_dag_load": True,
        "all_control_bytes_reverified_against_collector_snapshot": True,
        "final_success_snapshot_and_full_activation_bootstrap_dag_reverified": True,
        "same_uid_coordinated_replacement_of_root_and_all_sibling_anchors_is_excluded": True,
    }
    assembly = {
        **payload,
        "formal_activation_evidence_assembly_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:formal-activation-evidence-assembly\0"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    _publish_or_verify(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / FORMAL_EVIDENCE_ASSEMBLY_FILE,
        canonical_json_bytes(assembly),
    )


def _prepare_ingress(plan: dict[str, Any], attempt: dict[str, Any]) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "acfqp.v42_formal_transport_prepare_ingress.v42r1",
            "schema_version": authority.SCHEMA_VERSION,
            "formal_transport_plan": plan,
            "formal_prepare_attempt": attempt,
        }
    )


def _launch_ingress(
    plan: dict[str, Any], prepare_receipt: dict[str, Any],
    local_launch: dict[str, Any], transport_attempt: dict[str, Any],
) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "acfqp.v42_formal_transport_admit_launch_ingress.v42r1",
            "schema_version": authority.SCHEMA_VERSION,
            "formal_transport_plan": plan,
            "prepare_receipt": prepare_receipt,
            "local_launch_attempt": local_launch,
            "formal_launch_transport_attempt": transport_attempt,
        }
    )


def _publish_outcome(
    *, plan: dict[str, Any], operation: str, attempt_id: str,
    outcome_class: str, receipt_raw: bytes | None,
) -> dict[str, Any]:
    outcome = formal.build_operation_outcome_v42r1(
        plan=plan, operation=operation, attempt_id=attempt_id,
        outcome_class=outcome_class, receipt_raw=receipt_raw,
    )
    if outcome_class == formal.OUTCOME_PRE_NETWORK_FAILURE:
        prefix = "FORMAL_PREPARE_PRE_NETWORK_FAILURE" if operation == formal.OPERATION_PREPARE else "FORMAL_LAUNCH_PRE_NETWORK_FAILURE"
        pin = _JournalPin.open()
        try:
            ordinal = 1
            while True:
                name = f"{prefix}.{ordinal:08d}.json"
                if pin.exists(name):
                    ordinal += 1
                    continue
                try:
                    pin.publish(name, canonical_json_bytes(outcome))
                except FileExistsError:
                    ordinal += 1
                    continue
                break
        finally:
            pin.close()
        return outcome
    else:
        name = (
            formal.LOCAL_PREPARE_OUTCOME_NAME
            if operation == formal.OPERATION_PREPARE
            else formal.LOCAL_LAUNCH_OUTCOME_NAME
        )
    _publish_or_verify(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / name, canonical_json_bytes(outcome)
    )
    return outcome


def _retained_terminal_outcome(
    *, plan: dict[str, Any], operation: str, attempt_id: str,
) -> dict[str, Any] | None:
    outcome_path = formal.LOCAL_FORMAL_JOURNAL_ROOT / (
        formal.LOCAL_PREPARE_OUTCOME_NAME
        if operation == formal.OPERATION_PREPARE
        else formal.LOCAL_LAUNCH_OUTCOME_NAME
    )
    if not outcome_path.exists():
        return None
    raw = _stable_read(outcome_path, 4 * 1024**2, mode=0o400)
    outcome = formal.verify_operation_outcome_self_contained_v42r1(
        raw, plan=plan, operation=operation, attempt_id=attempt_id
    )
    marker_path = formal.LOCAL_FORMAL_JOURNAL_ROOT / (
        formal.LOCAL_PREPARE_NETWORK_START_NAME
        if operation == formal.OPERATION_PREPARE
        else formal.LOCAL_LAUNCH_NETWORK_START_NAME
    )
    # A conservatively closed outcome is itself the no-replay cut even if an
    # asynchronous exception prevented a named marker from being observed.
    if outcome["same_effect_replay_allowed"] is not False:
        _fail("terminal formal outcome unexpectedly authorizes replay")
    if outcome["network_start_marker_present"] is not True:
        _fail("fixed terminal outcome changed its post-marker semantics")
    del marker_path
    return outcome


def execute_prepare_once_v42r1(plan: dict[str, Any]) -> dict[str, Any]:
    attempt = formal.build_prepare_attempt_v42r1(plan)
    attempt_id = attempt["formal_prepare_attempt_id"]
    _publish_or_verify(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_PREPARE_ATTEMPT_NAME,
        canonical_json_bytes(attempt),
    )
    retained = _retained_terminal_outcome(
        plan=plan, operation=formal.OPERATION_PREPARE, attempt_id=attempt_id
    )
    if retained is not None:
        receipt = None
        try:
            receipt, _ = _retained_prepare(plan)
        except FileNotFoundError:
            receipt = None
        return {"attempt": attempt, "receipt": receipt, "outcome": retained}
    marker_path = (
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_PREPARE_NETWORK_START_NAME
    )
    if _effect_cut_present(
        operation="prepare_once", attempt_id=attempt_id,
        marker_path=marker_path,
    ):
        outcome = _publish_outcome(
            plan=plan, operation=formal.OPERATION_PREPARE,
            attempt_id=attempt_id,
            outcome_class=formal.OUTCOME_POST_MARKER_AMBIGUOUS,
            receipt_raw=None,
        )
        return {"attempt": attempt, "receipt": None, "outcome": outcome}
    observation, marker, failure = _dispatch_effect_once(
        plan=plan, operation="prepare_once", attempt_id=attempt_id,
        ingress_raw=_prepare_ingress(plan, attempt), marker_path=marker_path,
        stdout_cap=formal.MAX_PREPARE_RECEIPT_BYTES,
        timeout=formal.PREPARE_TRANSPORT_TIMEOUT_SECONDS,
    )
    receipt = None
    receipt_raw = None
    if failure is None and marker and _observation_closed_exactly(observation):
        assert observation is not None
        try:
            receipt_raw = _strip_one_newline(observation.stdout_raw, "prepare")
            receipt = authority.verify_prepare_receipt_v42(
                receipt_raw,
                fresh_terminal_preregistration_id=prereg.PREREGISTRATION_ID,
                history_freshness_manifest_id=prereg._freshness()[  # noqa: SLF001
                    "history_freshness_manifest_id"
                ],
                require_live_source=False,
            )
            if any(
                receipt[field] != plan[field]
                for field in (
                    "source_commit", "source_tree", "source_manifest_id",
                    "transport_manifest_id",
                )
            ):
                _fail("prepare receipt differs from formal transport plan")
        except BaseException:
            receipt = None
            receipt_raw = None
    if receipt is not None and receipt_raw is not None:
        _publish_or_verify(
            formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_PREPARE_RECEIPT_NAME,
            receipt_raw,
        )
        outcome_class = formal.OUTCOME_COMPLETE_EXACT_RECEIPT
    elif marker:
        outcome_class = formal.OUTCOME_POST_MARKER_AMBIGUOUS
    else:
        outcome_class = formal.OUTCOME_PRE_NETWORK_FAILURE
    outcome = _publish_outcome(
        plan=plan, operation=formal.OPERATION_PREPARE, attempt_id=attempt_id,
        outcome_class=outcome_class, receipt_raw=receipt_raw,
    )
    return {"attempt": attempt, "receipt": receipt, "outcome": outcome}


def _retained_prepare(plan: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    raw = _stable_read(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_PREPARE_RECEIPT_NAME,
        formal.MAX_PREPARE_RECEIPT_BYTES, mode=0o400,
    )
    receipt = authority.verify_prepare_receipt_v42(
        raw,
        fresh_terminal_preregistration_id=prereg.PREREGISTRATION_ID,
        history_freshness_manifest_id=prereg._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
        require_live_source=False,
    )
    if any(
        receipt[field] != plan[field]
        for field in (
            "source_commit", "source_tree", "source_manifest_id",
            "transport_manifest_id",
        )
    ):
        _fail("retained prepare receipt differs from formal plan")
    return receipt, raw


def execute_launch_admission_once_v42r1(plan: dict[str, Any]) -> dict[str, Any]:
    receipt, receipt_raw = _retained_prepare(plan)
    local_launch = existing_runner.issue_local_launch_attempt_once_v42r1(
        local_control_root=formal.LOCAL_FORMAL_JOURNAL_ROOT / LAUNCH_CONTROL_NAME,
        prepare_receipt_raw=receipt_raw,
    )
    _publish_or_verify(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_LAUNCH_ATTEMPT_NAME,
        canonical_json_bytes(local_launch),
    )
    transport_attempt = formal.build_launch_transport_attempt_v42r1(
        plan=plan, prepare_receipt=receipt, local_launch_attempt=local_launch
    )
    _publish_or_verify(
        formal.LOCAL_FORMAL_JOURNAL_ROOT
        / formal.LOCAL_LAUNCH_TRANSPORT_ATTEMPT_NAME,
        canonical_json_bytes(transport_attempt),
    )
    attempt_id = local_launch["local_launch_attempt_id"]
    retained = _retained_terminal_outcome(
        plan=plan, operation=formal.OPERATION_LAUNCH, attempt_id=attempt_id
    )
    if retained is not None:
        admission = None
        try:
            admission_raw = _stable_read(
                formal.LOCAL_FORMAL_JOURNAL_ROOT
                / formal.LOCAL_LAUNCH_ADMISSION_RECEIPT_NAME,
                formal.MAX_ADMISSION_RECEIPT_BYTES, mode=0o400,
            )
            admission = formal.verify_launch_admission_receipt_self_contained_v42r1(
                admission_raw, plan=plan,
                launch_transport_attempt=transport_attempt,
            )
        except FileNotFoundError:
            admission = None
        return {
            "local_launch_attempt": local_launch,
            "transport_attempt": transport_attempt,
            "admission_receipt": admission,
            "outcome": retained,
        }
    marker_path = (
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_LAUNCH_NETWORK_START_NAME
    )
    if _effect_cut_present(
        operation="admit_launch", attempt_id=attempt_id,
        marker_path=marker_path,
    ):
        outcome = _publish_outcome(
            plan=plan, operation=formal.OPERATION_LAUNCH,
            attempt_id=attempt_id,
            outcome_class=formal.OUTCOME_POST_MARKER_AMBIGUOUS,
            receipt_raw=None,
        )
        return {
            "local_launch_attempt": local_launch,
            "transport_attempt": transport_attempt,
            "admission_receipt": None,
            "outcome": outcome,
        }
    observation, marker, failure = _dispatch_effect_once(
        plan=plan, operation="admit_launch", attempt_id=attempt_id,
        ingress_raw=_launch_ingress(
            plan, receipt, local_launch, transport_attempt
        ),
        marker_path=marker_path, stdout_cap=formal.MAX_ADMISSION_RECEIPT_BYTES,
        timeout=formal.ADMISSION_TRANSPORT_TIMEOUT_SECONDS,
    )
    admission = None
    admission_raw = None
    if failure is None and marker and _observation_closed_exactly(observation):
        assert observation is not None
        try:
            admission_raw = _strip_one_newline(observation.stdout_raw, "admission")
            admission = formal.verify_launch_admission_receipt_self_contained_v42r1(
                admission_raw, plan=plan,
                launch_transport_attempt=transport_attempt,
            )
        except BaseException:
            admission = None
            admission_raw = None
    if admission is not None and admission_raw is not None:
        _publish_or_verify(
            formal.LOCAL_FORMAL_JOURNAL_ROOT
            / formal.LOCAL_LAUNCH_ADMISSION_RECEIPT_NAME,
            admission_raw,
        )
        outcome_class = formal.OUTCOME_COMPLETE_EXACT_RECEIPT
    elif marker:
        outcome_class = formal.OUTCOME_POST_MARKER_AMBIGUOUS
    else:
        outcome_class = formal.OUTCOME_PRE_NETWORK_FAILURE
    outcome = _publish_outcome(
        plan=plan, operation=formal.OPERATION_LAUNCH, attempt_id=attempt_id,
        outcome_class=outcome_class, receipt_raw=admission_raw,
    )
    return {
        "local_launch_attempt": local_launch,
        "transport_attempt": transport_attempt,
        "admission_receipt": admission,
        "outcome": outcome,
    }


def _inspection_ingress(
    *, plan: dict[str, Any], operation: str, attempt_id: str, ordinal: int,
) -> bytes:
    if operation == formal.OPERATION_PREPARE:
        return canonical_json_bytes(
            {
                "schema": "acfqp.v42_formal_transport_inspect_prepare_ingress.v42r1",
                "schema_version": authority.SCHEMA_VERSION,
                "formal_transport_plan": plan,
                "formal_prepare_attempt_id": attempt_id,
                "inspection_ordinal": ordinal,
            }
        )
    return canonical_json_bytes(
        {
            "schema": "acfqp.v42_formal_transport_inspect_launch_ingress.v42r1",
            "schema_version": authority.SCHEMA_VERSION,
            "formal_transport_plan": plan,
            "local_launch_attempt_id": attempt_id,
            "inspection_ordinal": ordinal,
        }
    )


def inspect_read_only_v42r1(
    *, plan: dict[str, Any], operation: str, attempt_id: str, ordinal: int,
) -> dict[str, Any]:
    key = "inspect_prepare" if operation == formal.OPERATION_PREPARE else "inspect_launch"
    observation = _dispatch_read_only(
        ssh_plan=plan,
        argv=formal.materialize_ssh_argv_v42r1(plan, key),
        ingress_raw=_inspection_ingress(
            plan=plan, operation=operation, attempt_id=attempt_id,
            ordinal=ordinal,
        ),
        stdout_cap=formal.MAX_INSPECTION_BYTES,
        timeout=formal.INSPECTION_TRANSPORT_TIMEOUT_SECONDS,
    )
    if not _observation_closed_exactly(observation):
        _fail("read-only formal inspection did not close exactly")
    raw = _strip_one_newline(observation.stdout_raw, "inspection")
    inspection = _document(raw, "formal read-only inspection")
    # Rebuild from every transported observation instead of trusting its ID.
    expected = formal.build_read_only_inspection_v42r1(
        plan=plan, operation=operation, attempt_id=attempt_id,
        inspection_ordinal=ordinal,
        manager_binding={
            key: inspection["manager_binding"][key]
            for key in (
                "kernel_boot_id", "linger_enabled",
                "user_manager_invocation_id", "user_manager_main_pid",
                "user_manager_control_group", "cgroup_contract_id",
            )
        },
        unit_observation=inspection.get("unit_observation"),
        artifact_states=inspection.get("artifact_states"),
        recovered_documents=inspection.get("recovered_documents"),
    )
    if inspection != expected:
        _fail("read-only formal inspection identity changed")
    path = formal.LOCAL_FORMAL_JOURNAL_ROOT / (
        formal.LOCAL_INSPECTION_PREFIX + f"{operation}.{ordinal:08d}.json"
    )
    _publish_once(path, raw)
    recovered = inspection["recovered_documents"]
    if "prepare_receipt" in recovered:
        receipt_raw = canonical_json_bytes(recovered["prepare_receipt"])
        receipt = authority.verify_prepare_receipt_v42(
            receipt_raw,
            fresh_terminal_preregistration_id=prereg.PREREGISTRATION_ID,
            history_freshness_manifest_id=prereg._freshness()[  # noqa: SLF001
                "history_freshness_manifest_id"
            ],
            require_live_source=False,
        )
        if any(
            receipt[field] != plan[field]
            for field in (
                "source_commit", "source_tree", "source_manifest_id",
                "transport_manifest_id",
            )
        ):
            _fail("recovered prepare receipt differs from formal plan")
        _publish_or_verify(
            formal.LOCAL_FORMAL_JOURNAL_ROOT
            / formal.LOCAL_PREPARE_RECEIPT_NAME,
            receipt_raw,
        )
    if "launch_admission_receipt" in recovered:
        receipt, _ = _retained_prepare(plan)
        local_raw = _stable_read(
            formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_LAUNCH_ATTEMPT_NAME,
            4 * 1024**2, mode=0o400,
        )
        local = authority.verify_local_launch_attempt_v42r1(
            local_raw, prepare_receipt=receipt
        )
        transport_attempt = formal.build_launch_transport_attempt_v42r1(
            plan=plan, prepare_receipt=receipt, local_launch_attempt=local
        )
        admission_raw = canonical_json_bytes(
            recovered["launch_admission_receipt"]
        )
        formal.verify_launch_admission_receipt_self_contained_v42r1(
            admission_raw, plan=plan,
            launch_transport_attempt=transport_attempt,
        )
        _publish_or_verify(
            formal.LOCAL_FORMAL_JOURNAL_ROOT
            / formal.LOCAL_LAUNCH_ADMISSION_RECEIPT_NAME,
            admission_raw,
        )
    return inspection


def classify_after_inspection_v42r1(
    *, plan: dict[str, Any], operation: str, attempt_id: str,
    ordinal: int, inspection: dict[str, Any],
) -> dict[str, Any]:
    marker_path = formal.LOCAL_FORMAL_JOURNAL_ROOT / (
        formal.LOCAL_PREPARE_NETWORK_START_NAME
        if operation == formal.OPERATION_PREPARE
        else formal.LOCAL_LAUNCH_NETWORK_START_NAME
    )
    marker_present = _effect_cut_present(
        operation=(
            "prepare_once"
            if operation == formal.OPERATION_PREPARE
            else "admit_launch"
        ),
        attempt_id=attempt_id,
        marker_path=marker_path,
    )
    exact_receipt = False
    try:
        if operation == formal.OPERATION_PREPARE:
            _retained_prepare(plan)
            exact_receipt = True
        else:
            receipt, _ = _retained_prepare(plan)
            local_raw = _stable_read(
                formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_LAUNCH_ATTEMPT_NAME,
                4 * 1024**2, mode=0o400,
            )
            local = authority.verify_local_launch_attempt_v42r1(
                local_raw, prepare_receipt=receipt
            )
            transport_attempt = formal.build_launch_transport_attempt_v42r1(
                plan=plan, prepare_receipt=receipt,
                local_launch_attempt=local,
            )
            admission_raw = _stable_read(
                formal.LOCAL_FORMAL_JOURNAL_ROOT
                / formal.LOCAL_LAUNCH_ADMISSION_RECEIPT_NAME,
                formal.MAX_ADMISSION_RECEIPT_BYTES, mode=0o400,
            )
            formal.verify_launch_admission_receipt_self_contained_v42r1(
                admission_raw, plan=plan,
                launch_transport_attempt=transport_attempt,
            )
            exact_receipt = True
    except (FileNotFoundError, V42FormalTransportDriverError):
        exact_receipt = False
    classification = formal.classify_formal_operation_v42r1(
        plan=plan, operation=operation, attempt_id=attempt_id,
        marker_present=marker_present, exact_receipt_present=exact_receipt,
        inspection=inspection,
    )
    path = formal.LOCAL_FORMAL_JOURNAL_ROOT / (
        f"FORMAL_CLASSIFICATION.{operation}.{ordinal:08d}.json"
    )
    raw = canonical_json_bytes(classification)
    _publish_once(path, raw)
    sys.stdout.buffer.write(raw + b"\n")
    sys.stdout.buffer.flush()
    return classification


def _load_epoch_or_probe(
    *, inputs: Mapping[str, Any], core: dict[str, Any], probe: bool,
) -> dict[str, Any]:
    path = formal.LOCAL_FORMAL_JOURNAL_ROOT / HOST_EPOCH_RECEIPT_FILE
    if path.exists():
        raw = _stable_read(path, formal.MAX_INSPECTION_BYTES, mode=0o400)
        return formal.verify_formal_host_epoch_receipt_v42r1(
            raw, activation_core=core
        )
    if not probe:
        _fail("formal host epoch receipt is absent; run --probe-host-epoch")
    return _probe_host_epoch(
        core=core,
        receiver_raw=_program_raw(formal.FORMAL_RECEIVER_RELATIVE),
        formal_authority_raw=_program_raw(formal.FORMAL_AUTHORITY_RELATIVE),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V42 production formal transport driver")
    parser.add_argument("--activation-evidence-root", required=True)
    parser.add_argument(
        "--expected-activation-final-evidence-index-id", required=True,
    )
    parser.add_argument("--preformal-evidence-root")
    parser.add_argument("--resource-evidence-root")
    parser.add_argument("--control-evidence-root")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--probe-host-epoch", action="store_true")
    modes.add_argument("--prepare-once", action="store_true")
    modes.add_argument("--admit-launch-once", action="store_true")
    modes.add_argument("--inspect-prepare", action="store_true")
    modes.add_argument("--inspect-launch", action="store_true")
    parser.add_argument("--inspection-ordinal", type=int, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if _PRODUCTION_SOURCE_FINDER is not None:
        _PRODUCTION_SOURCE_FINDER.verify_loaded()
    arguments = _parser().parse_args(argv)
    evidence_root = Path(arguments.activation_evidence_root)
    if not evidence_root.is_absolute():
        _fail("activation evidence root must be absolute")
    _ensure_journal_root()
    _publish_or_verify(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_KNOWN_HOSTS_NAME,
        preformal.PINNED_KNOWN_HOSTS_BYTES,
    )
    inputs = _load_production_inputs(
        evidence_root,
        expected_final_evidence_index_id=(
            arguments.expected_activation_final_evidence_index_id
        ),
        preformal_evidence_root=(
            None
            if arguments.preformal_evidence_root is None
            else Path(arguments.preformal_evidence_root)
        ),
        resource_evidence_root=(
            None
            if arguments.resource_evidence_root is None
            else Path(arguments.resource_evidence_root)
        ),
        control_evidence_root=(
            None
            if arguments.control_evidence_root is None
            else Path(arguments.control_evidence_root)
        ),
    )
    core, _terminal_raw = _verify_production_activation_chain(inputs)
    epoch = _load_epoch_or_probe(
        inputs=inputs, core=core, probe=arguments.probe_host_epoch
    )
    if arguments.probe_host_epoch:
        return 0
    plan, activation_raw, rebuilt_core, _driver_raw = _build_plan(
        inputs=inputs, host_epoch_receipt=epoch
    )
    if rebuilt_core != core:
        _fail("activation core changed between probe and plan construction")
    _persist_plan_prefix(plan, activation_raw, inputs=inputs)
    if arguments.prepare_once:
        result = execute_prepare_once_v42r1(plan)
        return 0 if result["receipt"] is not None else 2
    if arguments.admit_launch_once:
        result = execute_launch_admission_once_v42r1(plan)
        return 0 if result["admission_receipt"] is not None else 2
    if arguments.inspect_prepare:
        attempt = formal.build_prepare_attempt_v42r1(plan)
        inspection = inspect_read_only_v42r1(
            plan=plan, operation=formal.OPERATION_PREPARE,
            attempt_id=attempt["formal_prepare_attempt_id"],
            ordinal=arguments.inspection_ordinal,
        )
        classify_after_inspection_v42r1(
            plan=plan, operation=formal.OPERATION_PREPARE,
            attempt_id=attempt["formal_prepare_attempt_id"],
            ordinal=arguments.inspection_ordinal, inspection=inspection,
        )
        return 0
    local_raw = _stable_read(
        formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_LAUNCH_ATTEMPT_NAME,
        4 * 1024**2, mode=0o400,
    )
    receipt, _ = _retained_prepare(plan)
    local = authority.verify_local_launch_attempt_v42r1(
        local_raw, prepare_receipt=receipt
    )
    inspection = inspect_read_only_v42r1(
        plan=plan, operation=formal.OPERATION_LAUNCH,
        attempt_id=local["local_launch_attempt_id"],
        ordinal=arguments.inspection_ordinal,
    )
    classify_after_inspection_v42r1(
        plan=plan, operation=formal.OPERATION_LAUNCH,
        attempt_id=local["local_launch_attempt_id"],
        ordinal=arguments.inspection_ordinal, inspection=inspection,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
