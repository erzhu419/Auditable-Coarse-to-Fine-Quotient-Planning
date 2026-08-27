#!/usr/bin/env python3
"""Remote ingress and read-only inspector for V42 ordinal-2 formal transport.

The two effectful modes are one shot.  ``--prepare-once`` delegates to the
existing audited formal prepare state machine.  ``--admit-launch`` publishes
the existing local launch attempt and admits a detached user systemd service.
The SSH process never waits for that service.  The service first re-enters
through ``--formal-launch-service-wrapper`` and verifies its InvocationID,
MainPID, cgroup, null stdio, clean environment, host epoch, and pinned tools
before invoking the existing seven-day formal runner.

The inspection modes perform no filesystem or systemd lifecycle mutation.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
from typing import Any, NoReturn, Sequence
import uuid


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from acfqp import (  # noqa: E402
    construction_k7_standard_2048_formal_transport_v42r1 as formal,
)
from acfqp import (  # noqa: E402
    construction_k7_standard_2048_fresh_terminal_preregistration_v42 as prereg,
)
from acfqp import (  # noqa: E402
    construction_k7_standard_2048_process_supervision_v42r1 as processio,
)
from acfqp import (  # noqa: E402
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json  # noqa: E402
from scripts import run_v42_preformal_upload_sender as frozen_sender  # noqa: E402
from scripts import run_v42_standard_2048_remote_ordinal2 as existing_runner  # noqa: E402


INGRESS_PREPARE_SCHEMA = "acfqp.v42_formal_transport_prepare_ingress.v42r1"
INGRESS_INSPECT_PREPARE_SCHEMA = (
    "acfqp.v42_formal_transport_inspect_prepare_ingress.v42r1"
)
INGRESS_ADMIT_SCHEMA = "acfqp.v42_formal_transport_admit_launch_ingress.v42r1"
INGRESS_INSPECT_LAUNCH_SCHEMA = (
    "acfqp.v42_formal_transport_inspect_launch_ingress.v42r1"
)
INGRESS_HOST_EPOCH_PROBE_SCHEMA = (
    "acfqp.v42_formal_transport_host_epoch_probe_ingress.v42r1"
)

MAX_INGRESS_BYTES = 80 * 1024**2
MAX_SYSTEMCTL_STDOUT = 256 * 1024
MAX_SYSTEMD_RUN_STREAM = 64 * 1024
COMMAND_TIMEOUT_SECONDS = 30.0
ADMISSION_HANDSHAKE_TIMEOUT_SECONDS = 60.0
CLEAN_WRAPPER_TRANSITION_TIMEOUT_SECONDS = 30.0
REMOTE_PLAN_NAME = formal.LOCAL_PLAN_NAME
_HEX64 = re.compile(r"[0-9a-f]{64}")
_INVOCATION32 = re.compile(r"[0-9a-f]{32}")

# The existing runner is almost 200 KiB, so passing its bytes in argv would
# consume a platform-dependent portion of ARG_MAX.  Instead the receiver pins
# its manifested source descriptor and lets this tiny stdlib-only trampoline
# consume it exactly once.  The trampoline hashes the held bytes, closes every
# descriptor above stderr, and only then compiles the runner.  Consequently no
# transport pin survives into the seven-day scientific process.
VERIFIED_RUNNER_FD_LOADER_SOURCE = r'''import hashlib
import importlib.machinery
import json
import os
import stat
import sys

fd = int(sys.argv[1])
expected_sha = sys.argv[2]
expected_count = int(sys.argv[3])
source_path = sys.argv[4]
runner_mode = sys.argv[5]
expected_manifest_id = sys.argv[6]
expected_environment = {"HOME": "/home/erzhu419", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "LOGNAME": "erzhu419", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONCOERCECLOCALE": "0", "USER": "erzhu419"}
if not (sys.executable == "/usr/bin/python3" and os.path.realpath(sys.executable) == "/usr/bin/python3.10" and os.path.realpath("/proc/self/exe") == "/usr/bin/python3.10" and tuple(sys.version_info[:3]) == (3, 10, 12) and sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode is True and sys.gettrace() is None and sys.getprofile() is None and sys.path == ["/usr/lib/python310.zip", "/usr/lib/python3.10", "/usr/lib/python3.10/lib-dynload"] and sys.orig_argv[:5] == ["/usr/bin/python3", "-I", "-S", "-B", "-c"] and len(sys.orig_argv) == len(sys.argv) + 5 and sys.orig_argv[6:] == sys.argv[1:] and dict(os.environ) == expected_environment):
    raise RuntimeError("formal runner loader isolated invocation changed")
initial_fds = []
for name in os.listdir("/proc/self/fd"):
    if not name.isdigit():
        raise RuntimeError("formal runner loader descriptor name changed")
    descriptor = int(name)
    try:
        os.fstat(descriptor)
    except OSError:
        continue
    initial_fds.append(descriptor)
if sorted(initial_fds) != sorted([0, 1, 2, fd]) or fd < 3 or any(os.isatty(descriptor) for descriptor in (0, 1, 2)):
    raise RuntimeError("formal runner loader inherited descriptor inventory changed")
null = os.stat("/dev/null", follow_symlinks=False)
for descriptor in (0, 1, 2):
    observed = os.fstat(descriptor)
    if not (stat.S_ISCHR(observed.st_mode) and observed.st_rdev == null.st_rdev and os.readlink("/proc/self/fd/" + str(descriptor)) == "/dev/null"):
        raise RuntimeError("formal runner loader stdio is not /dev/null")
before = os.fstat(fd)
os.lseek(fd, 0, os.SEEK_SET)
chunks = []
count = 0
digest = hashlib.sha256()
while count <= expected_count:
    chunk = os.read(fd, min(1024 * 1024, expected_count + 1 - count))
    if not chunk:
        break
    chunks.append(chunk)
    count += len(chunk)
    digest.update(chunk)
if count == expected_count:
    extra = os.read(fd, 1)
    if extra:
        count += 1
after = os.fstat(fd)
if (before.st_dev, before.st_ino, before.st_mode, before.st_uid, before.st_gid, before.st_nlink, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_mode, after.st_uid, after.st_gid, after.st_nlink, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
    raise RuntimeError("formal runner changed during held-descriptor read")
if count != expected_count or digest.hexdigest() != expected_sha:
    raise RuntimeError("formal runner held bytes changed")
raw = b"".join(chunks)
os.close(fd)
os.closerange(3, 1048576)
remaining_fds = []
for name in os.listdir("/proc/self/fd"):
    if name.isdigit():
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        remaining_fds.append(descriptor)
if sorted(remaining_fds) != [0, 1, 2]:
    raise RuntimeError("formal runner loader retained a non-stdio descriptor")
source_root = os.path.dirname(os.path.dirname(source_path))
control_root = os.path.dirname(source_root)

def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError("duplicate runner manifest JSON key")
        result[key] = value
    return result

def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8", errors="strict")

def read_regular(path, maximum, mode):
    named = os.lstat(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if not (stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode) == mode and before.st_uid == 1000 and before.st_gid == 1000 and before.st_nlink == 1 and 0 < before.st_size <= maximum and (before.st_dev, before.st_ino) == (named.st_dev, named.st_ino)):
            raise RuntimeError("runner source storage changed: " + path)
        parts = []
        remaining = before.st_size
        while remaining:
            part = os.read(descriptor, min(remaining, 1024 * 1024))
            if not part:
                raise RuntimeError("runner source ended early: " + path)
            parts.append(part)
            remaining -= len(part)
        if os.read(descriptor, 1):
            raise RuntimeError("runner source grew during read: " + path)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = os.lstat(path)
    fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, key) != getattr(after, key) or getattr(after, key) != getattr(final, key) for key in fields):
        raise RuntimeError("runner source changed while read: " + path)
    return b"".join(parts)

manifest_raw = read_regular(os.path.join(control_root, "EXECUTION_SOURCE_MANIFEST.json"), 64 * 1024**2, 0o400)
manifest = json.loads(manifest_raw.decode("utf-8", errors="strict"), object_pairs_hook=unique, parse_constant=lambda token: (_ for _ in ()).throw(RuntimeError("nonfinite runner manifest JSON")))
if type(manifest) is not dict or canonical_bytes(manifest) != manifest_raw:
    raise RuntimeError("runner source manifest is not canonical")
payload = dict(manifest)
manifest_id = payload.pop("source_manifest_id", None)
if manifest_id != expected_manifest_id or hashlib.sha256(b"acfqp:v42-remote-ordinal2:source-manifest\0" + canonical_bytes(payload)).hexdigest() != manifest_id:
    raise RuntimeError("runner source manifest identity changed")
facts = {}
for fact in manifest.get("source_facts", []):
    relative = fact.get("relative_path") if type(fact) is dict else None
    if type(relative) is not str or not relative.endswith(".py") or relative.startswith("/") or ".." in relative.split("/") or relative in facts or type(fact.get("byte_count")) is not int or not 0 < fact["byte_count"] <= 8 * 1024**2 or type(fact.get("sha256")) is not str or type(fact.get("git_blob_oid")) is not str:
        raise RuntimeError("runner source manifest fact changed")
    facts[relative] = fact

cache = {}
def verified_source(relative):
    if relative in cache:
        return cache[relative]
    fact = facts[relative]
    value = read_regular(os.path.join(source_root, relative), 8 * 1024**2, 0o444)
    blob = hashlib.sha1(b"blob " + str(len(value)).encode("ascii") + b"\0" + value).hexdigest()
    if len(value) != fact["byte_count"] or hashlib.sha256(value).hexdigest() != fact["sha256"] or blob != fact["git_blob_oid"]:
        raise RuntimeError("runner manifested dependency changed: " + relative)
    cache[relative] = value
    return value

runner_relative = os.path.relpath(source_path, source_root)
if runner_relative not in facts or verified_source(runner_relative) != raw:
    raise RuntimeError("held runner differs from execution source manifest")

created_loaders = {}

class Loader:
    def __init__(self, relative, package):
        self.relative = relative
        self.package = package
        self.origin = os.path.join(source_root, relative)
        self.exec_count = 0
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        if self.exec_count != 0:
            raise RuntimeError("runner verified dependency executed more than once")
        self.exec_count = 1
        namespace = vars(module)
        namespace["__file__"] = self.origin
        namespace["__cached__"] = None
        value = verified_source(self.relative)
        exec(compile(value, self.origin, "exec", dont_inherit=True), namespace, namespace)

class Finder:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "acfqp" or fullname.startswith("acfqp."):
            prefix = "src/"
        elif fullname == "scripts" or fullname.startswith("scripts."):
            prefix = ""
        else:
            if path is None:
                stem = fullname.replace(".", "/")
                for base in (source_root, os.path.join(source_root, "src")):
                    if any(os.path.lexists(os.path.join(base, candidate)) for candidate in (stem + ".py", stem + ".pyc", os.path.join(stem, "__init__.py"), os.path.join(stem, "__init__.pyc"))):
                        raise ImportError("repository stdlib shadow rejected: " + fullname)
            return None
        stem = prefix + fullname.replace(".", "/")
        module_relative = stem + ".py"
        package_relative = stem + "/__init__.py"
        if module_relative in facts:
            relative = module_relative
            package = False
        elif package_relative in facts:
            relative = package_relative
            package = True
        else:
            raise ImportError("unmanifested scientific repository module: " + fullname)
        loader = Loader(relative, package)
        if fullname in created_loaders:
            raise ImportError("runner verified module loader repeated: " + fullname)
        created_loaders[fullname] = loader
        spec = importlib.machinery.ModuleSpec(fullname, loader, origin=loader.origin, is_package=package)
        if package:
            spec.submodule_search_locations = [os.path.dirname(loader.origin)]
        return spec

sys.dont_write_bytecode = True
sys.meta_path.insert(0, Finder())
sys.argv = [source_path, runner_mode]
namespace = {"__name__": "_acfqp_verified_scientific_runner", "__file__": source_path, "__package__": None, "__cached__": None}
exec(compile(raw, source_path, "exec", dont_inherit=True), namespace, namespace)
expected_loaded = {
    "acfqp": "src/acfqp/__init__.py",
    "acfqp.artifacts": "src/acfqp/artifacts.py",
    "acfqp.build_coverage": "src/acfqp/build_coverage.py",
    "acfqp.construction_k7_domain_registry_extension_v42": "src/acfqp/construction_k7_domain_registry_extension_v42.py",
    "acfqp.construction_k7_standard_2048_fresh_terminal_preregistration_v42": "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
    "acfqp.construction_k7_standard_2048_history_manifest_v42": "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
    "acfqp.construction_k7_standard_2048_process_supervision_v42r1": "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
    "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1": "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
    "acfqp.core": "src/acfqp/core.py",
    "acfqp.enumeration": "src/acfqp/enumeration.py",
    "acfqp.phase3e_ids": "src/acfqp/phase3e_ids.py",
}
actual_loaded = {}
for name, module in sys.modules.items():
    file_name = getattr(module, "__file__", None)
    if type(file_name) is str and file_name.startswith(source_root + "/"):
        actual_loaded[name] = os.path.relpath(file_name, source_root)
if actual_loaded != expected_loaded or set(created_loaders) != set(expected_loaded):
    raise RuntimeError("formal runner loaded repository module inventory changed")
for name, relative in expected_loaded.items():
    module = sys.modules[name]
    loader = created_loaders[name]
    if not (getattr(module, "__loader__", None) is loader and getattr(getattr(module, "__spec__", None), "origin", None) == os.path.join(source_root, relative) and getattr(module, "__cached__", None) is None and loader.exec_count == 1):
        raise RuntimeError("formal runner dependency escaped verified source bytes")
entry = namespace.get("main")
if not callable(entry):
    raise RuntimeError("formal runner verified entry point changed")
raise SystemExit(entry())
'''

UNIT_SHOW_FIELDS = (
    "Id", "LoadState", "ActiveState", "SubState", "Result", "InvocationID",
    "MainPID", "ControlGroup", "Type", "Restart", "RemainAfterExit",
    "SuccessExitStatus", "UMask", "KillMode", "TimeoutStopUSec",
    "RuntimeMaxUSec", "StandardInput", "StandardOutput", "StandardError",
    "WorkingDirectory", "Slice", "FragmentPath", "ExecStart", "Environment",
)
MANAGER_SHOW_FIELDS = (
    "InvocationID", "MainPID", "ControlGroup", "LoadState", "ActiveState",
    "SubState",
)


class V42FormalTransportReceiverError(RuntimeError):
    pass


def _fail(message: str) -> NoReturn:
    raise V42FormalTransportReceiverError(message)


def _read_stdin() -> bytes:
    raw = sys.stdin.buffer.read(MAX_INGRESS_BYTES + 1)
    if not raw or len(raw) > MAX_INGRESS_BYTES:
        _fail("formal transport ingress is empty or exceeds its cap")
    return raw


def _canonical(raw: bytes, label: str) -> dict[str, Any]:
    try:
        result = loads_canonical_json(raw)
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42FormalTransportReceiverError(f"{label} is not canonical JSON") from error
    if type(result) is not dict or canonical_json_bytes(result) != raw:
        _fail(f"{label} canonical bytes changed")
    return result


def _ingress(schema: str, fields: set[str]) -> dict[str, Any]:
    document = _canonical(_read_stdin(), "formal transport ingress")
    if set(document) != {"schema", "schema_version", *fields}:
        _fail("formal transport ingress schema changed")
    if document.get("schema") != schema or document.get("schema_version") != "1.0.0":
        _fail("formal transport ingress version changed")
    return document


def _plan(value: object, expected_id: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("formal transport ingress plan changed type")
    plan = formal.verify_self_contained_formal_transport_plan_v42r1(value)
    if plan["formal_transport_plan_id"] != expected_id:
        _fail("formal transport command/plan ID join changed")
    return plan


def _stable_regular(path: Path, cap: int) -> tuple[bytes, os.stat_result]:
    descriptor = -1
    try:
        before_named = path.lstat()
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or (before.st_dev, before.st_ino) != (before_named.st_dev, before_named.st_ino)
            or before.st_size > cap
        ):
            _fail(f"unsafe or oversized remote artifact: {path}")
        chunks: list[bytes] = []
        count = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, cap + 1 - count))
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
            if count > cap:
                _fail(f"remote artifact exceeded cap during read: {path}")
        after = os.fstat(descriptor)
        after_named = path.lstat()
        stable = lambda observed: (
            observed.st_dev, observed.st_ino, observed.st_mode, observed.st_uid,
            observed.st_gid, observed.st_nlink, observed.st_size,
            observed.st_mtime_ns, observed.st_ctime_ns,
        )
        if stable(before) != stable(after) or (after.st_dev, after.st_ino) != (
            after_named.st_dev, after_named.st_ino
        ):
            _fail(f"remote artifact changed during read: {path}")
        return b"".join(chunks), after
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _verify_tool_fact(fact: dict[str, Any]) -> None:
    path = Path(fact["path"])
    raw, observed = _stable_regular(path, 64 * 1024**2)
    if (
        stat.S_IMODE(observed.st_mode) != fact["mode"]
        or observed.st_uid != fact["uid"]
        or observed.st_gid != fact["gid"]
        or observed.st_nlink != fact["st_nlink"]
        or len(raw) != fact["byte_count"]
        or hashlib.sha256(raw).hexdigest() != fact["sha256"]
    ):
        _fail(f"remote tool fact changed: {path}")


def _observe_tool_fact(path: str) -> dict[str, Any]:
    raw, observed = _stable_regular(Path(path), 64 * 1024**2)
    if (
        stat.S_IMODE(observed.st_mode) != 0o755
        or observed.st_uid != 0
        or observed.st_gid != 0
        or observed.st_nlink != 1
        or not raw
    ):
        _fail(f"remote tool live identity changed: {path}")
    return {
        "path": path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "mode": 0o755,
        "uid": 0,
        "gid": 0,
        "st_nlink": 1,
    }


def _verify_tools(plan: dict[str, Any]) -> dict[str, Any]:
    for key in sorted(plan["activation_binding"]["remote_tool_facts"]):
        pin = _open_tool_pin(plan, key)
        try:
            pin.verify()
        finally:
            pin.close()
    return dict(plan["activation_binding"]["remote_tool_facts"])


def _join_formal_transport_facts(
    transport_manifest: dict[str, Any],
    artifacts: Sequence[dict[str, Any]],
) -> None:
    facts = {
        fact["relative_path"]: fact
        for fact in transport_manifest["transport_facts"]
    }
    for artifact in artifacts:
        if type(artifact) is not dict:
            _fail("formal transport artifact changed type")
        fact = facts.get(artifact.get("relative_path"))
        if (
            type(fact) is not dict
            or fact.get("byte_count") != artifact.get("byte_count")
            or fact.get("sha256") != artifact.get("sha256")
        ):
            _fail("formal artifact differs from fixed transport manifest")


def _verify_program_self(plan: dict[str, Any]) -> None:
    python_pin = _open_tool_pin(plan, "python")
    try:
        python_pin.verify()
        current = os.stat("/proc/self/exe", follow_symlinks=True)
        pinned = os.fstat(python_pin.descriptor)
        if (current.st_dev, current.st_ino) != (pinned.st_dev, pinned.st_ino):
            _fail("current interpreter differs from the pinned Python executable")
    finally:
        python_pin.close()
    for path, artifact, label in (
        (Path(__file__), plan["receiver_artifact"], "formal receiver"),
        (Path(formal.__file__), plan["formal_authority_artifact"], "formal authority"),
    ):
        raw, observed = _stable_regular(path, 4 * 1024**2)
        if (
            len(raw) != artifact["byte_count"]
            or hashlib.sha256(raw).hexdigest() != artifact["sha256"]
            or path.resolve(strict=True)
            != authority.REMOTE_SOURCE_ROOT / artifact["relative_path"]
            or stat.S_IMODE(observed.st_mode) != 0o444
            or observed.st_uid != authority.REMOTE_UID
        ):
            _fail(f"{label} live bytes, origin, mode, or owner changed")


def _open_tool_pin(
    plan: dict[str, Any], key: str
) -> frozen_sender._PinnedLocalFile:  # noqa: SLF001
    facts = plan["activation_binding"]["remote_tool_facts"]
    if key not in facts:
        _fail("remote tool pin key changed")
    fact = facts[key]
    return frozen_sender._open_local_file_pin(  # noqa: SLF001
        path=fact["path"],
        mode=fact["mode"],
        uid=fact["uid"],
        gid=fact["gid"],
        nlink=fact["st_nlink"],
        byte_count=fact["byte_count"],
        sha256=fact["sha256"],
        label=f"remote {key} executable",
    )


def _kill_reap(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _run_bounded(
    argv: tuple[str, ...], *, environment: dict[str, str], stdout_cap: int,
    stderr_cap: int, timeout_seconds: float,
    executable_pin: frozen_sender._PinnedLocalFile | None = None,  # noqa: SLF001
) -> tuple[int, bytes, bytes]:
    if (
        not argv
        or any(type(item) is not str or not item for item in argv)
        or type(environment) is not dict
        or timeout_seconds <= 0
    ):
        _fail("bounded command contract changed")
    if executable_pin is not None:
        executable_pin.verify()
        executable = f"/proc/self/fd/{executable_pin.descriptor}"
        pass_fds = (executable_pin.descriptor,)
    else:
        executable = None
        pass_fds = ()
    process = subprocess.Popen(
        argv,
        executable=executable,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=authority.REMOTE_SOURCE_ROOT,
        env=environment,
        close_fds=True,
        pass_fds=pass_fds,
        start_new_session=True,
    )
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    caps = {"stdout": stdout_cap, "stderr": stderr_cap}
    for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe, selectors.EVENT_READ, name)
    deadline = time.monotonic() + timeout_seconds
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_reap(process)
                _fail("bounded remote tool command timed out")
            for key, _mask in selector.select(min(remaining, 0.25)):
                try:
                    chunk = os.read(key.fd, 64 * 1024)
                except (BlockingIOError, InterruptedError):
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                target = streams[key.data]
                target.extend(chunk)
                if len(target) > caps[key.data]:
                    _kill_reap(process)
                    _fail(f"bounded remote tool {key.data} exceeded cap")
        try:
            returncode = process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            _kill_reap(process)
            _fail("bounded remote tool exit was not observed")
        if executable_pin is not None:
            executable_pin.verify()
        return returncode, bytes(streams["stdout"]), bytes(streams["stderr"])
    except BaseException:
        if process.poll() is None:
            _kill_reap(process)
        raise
    finally:
        selector.close()
        for pipe in (process.stdout, process.stderr):
            if not pipe.closed:
                pipe.close()


def _parse_properties(raw: bytes, expected_fields: Sequence[str]) -> dict[str, str]:
    if not raw.endswith(b"\n") or b"\0" in raw:
        _fail("systemctl properties are not bounded newline text")
    try:
        lines = raw.decode("utf-8", errors="strict").splitlines()
    except UnicodeError as error:
        raise V42FormalTransportReceiverError(
            "systemctl properties are not UTF-8"
        ) from error
    result: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            _fail("systemctl property line changed")
        key, value = line.split("=", 1)
        if key in result:
            _fail("systemctl property was duplicated")
        result[key] = value
    if set(result) != set(expected_fields):
        _fail("systemctl property keyset changed")
    return result


def _systemctl_properties(
    *, plan: dict[str, Any], user: bool, unit: str, fields: Sequence[str]
) -> dict[str, str]:
    tool = plan["activation_binding"]["remote_tool_facts"]["systemctl"]["path"]
    argv = [tool]
    if user:
        argv.append("--user")
    argv.extend(("--no-pager", "show"))
    argv.extend(f"--property={field}" for field in fields)
    argv.append(unit)
    environment = dict(formal.SYSTEMD_CLIENT_ENVIRONMENT)
    pin = _open_tool_pin(plan, "systemctl")
    try:
        returncode, stdout, stderr = _run_bounded(
            tuple(argv),
            environment=environment,
            stdout_cap=MAX_SYSTEMCTL_STDOUT,
            stderr_cap=64 * 1024,
            timeout_seconds=COMMAND_TIMEOUT_SECONDS,
            executable_pin=pin,
        )
    finally:
        pin.close()
    if returncode != 0 or stderr:
        _fail("systemctl read-only show did not close exactly")
    return _parse_properties(stdout, fields)


def _canonical_uuid_from_systemd(value: str, label: str) -> str:
    if _INVOCATION32.fullmatch(value) is None:
        _fail(f"{label} changed")
    return str(uuid.UUID(value))


def _cgroup_ancestry(manager_control_group: str) -> list[dict[str, Any]]:
    current = PurePosixPath(manager_control_group)
    paths: list[str] = []
    while True:
        value = str(current)
        paths.append(value)
        if value == "/":
            break
        current = current.parent
    rows: list[dict[str, Any]] = []
    for path in paths:
        memory_path = Path("/sys/fs/cgroup") / path.lstrip("/") / "memory.max"
        raw, observed = _stable_regular(memory_path, 128)
        if stat.S_IMODE(observed.st_mode) & 0o022:
            _fail("cgroup memory.max is group/world writable")
        if not raw.endswith(b"\n"):
            _fail("cgroup memory.max changed encoding")
        token = raw[:-1]
        if token == b"max":
            mode = "MAX"
            maximum = None
        elif token.isdigit() and token == str(int(token)).encode("ascii"):
            mode = "FINITE"
            maximum = int(token)
        else:
            _fail("cgroup memory.max changed vocabulary")
        rows.append(
            {
                "cgroup_path": path,
                "memory_max_mode": mode,
                "memory_max_bytes": maximum,
            }
        )
    return rows


def _observe_manager(plan: dict[str, Any]) -> dict[str, Any]:
    boot_raw, _ = _stable_regular(Path("/proc/sys/kernel/random/boot_id"), 128)
    try:
        boot = boot_raw.decode("ascii").strip()
    except UnicodeError as error:
        raise V42FormalTransportReceiverError("kernel boot ID is not ASCII") from error
    if str(uuid.UUID(boot)) != boot or boot_raw != (boot + "\n").encode("ascii"):
        _fail("kernel boot ID changed encoding")
    linger = Path(f"/var/lib/systemd/linger/{authority.REMOTE_USER}")
    linger_raw, linger_observed = _stable_regular(linger, 1)
    if (
        linger_raw != b""
        or stat.S_IMODE(linger_observed.st_mode) != 0o644
        or linger_observed.st_uid != 0
        or linger_observed.st_gid != 0
    ):
        _fail("systemd linger authority changed")
    properties = _systemctl_properties(
        plan=plan,
        user=False,
        unit=f"user@{authority.REMOTE_UID}.service",
        fields=MANAGER_SHOW_FIELDS,
    )
    if (
        properties["LoadState"] != "loaded"
        or properties["ActiveState"] != "active"
        or properties["SubState"] != "running"
        or not properties["MainPID"].isdigit()
        or int(properties["MainPID"]) <= 1
    ):
        _fail("user manager is not one loaded active running service")
    invocation = _canonical_uuid_from_systemd(
        properties["InvocationID"], "user-manager invocation ID"
    )
    cgroup = properties["ControlGroup"]
    ancestry = _cgroup_ancestry(cgroup)
    return {
        "kernel_boot_id": boot,
        "linger_enabled": True,
        "user_manager_invocation_id": invocation,
        "user_manager_main_pid": int(properties["MainPID"]),
        "user_manager_control_group": cgroup,
        "cgroup_contract_id": formal.build_cgroup_contract_id_v42r1(
            manager_control_group=cgroup,
            memory_limit_ancestry=ancestry,
        ),
    }


def _host_epoch_probe() -> int:
    document = _ingress(
        INGRESS_HOST_EPOCH_PROBE_SCHEMA,
        {"production_activation_core", "receiver_artifact", "formal_authority_artifact"},
    )
    core = formal.verify_production_activation_core_v42r1(
        document["production_activation_core"]
    )
    for path, artifact, relative, label in (
        (Path(__file__), document["receiver_artifact"], formal.FORMAL_RECEIVER_RELATIVE, "receiver"),
        (Path(formal.__file__), document["formal_authority_artifact"], formal.FORMAL_AUTHORITY_RELATIVE, "formal authority"),
    ):
        if (
            type(artifact) is not dict
            or set(artifact) != {"relative_path", "byte_count", "sha256"}
            or artifact.get("relative_path") != relative
        ):
            _fail(f"host epoch probe {label} artifact changed")
        raw, observed = _stable_regular(path, 4 * 1024**2)
        if (
            path.resolve(strict=True) != authority.REMOTE_SOURCE_ROOT / relative
            or len(raw) != artifact.get("byte_count")
            or hashlib.sha256(raw).hexdigest() != artifact.get("sha256")
            or stat.S_IMODE(observed.st_mode) != 0o444
            or observed.st_uid != authority.REMOTE_UID
        ):
            _fail(f"host epoch probe {label} live identity changed")
    phase = authority.verify_remote_control_phase_inventory_v42r1(
        "POST_MATERIALIZATION_PREPARE"
    )
    _join_formal_transport_facts(
        phase["transport_manifest"],
        [document["receiver_artifact"], document["formal_authority_artifact"]],
    )
    if (
        phase["source_manifest"]["source_commit"] != core["source_commit"]
        or phase["source_manifest"]["source_tree"] != core["source_tree"]
        or phase["source_manifest"]["source_manifest_id"]
        != core["source_manifest_id"]
        or phase["transport_manifest"]["transport_manifest_id"]
        != core["transport_manifest_id"]
        or phase["local_materialization_attempt_id"]
        != core["local_materialization_attempt_id"]
        or phase["remote_materialization_attempt_id"]
        != core["remote_materialization_attempt_id"]
        or phase["materialization_terminal_id"]
        != core["materialization_terminal_id"]
    ):
        _fail("host epoch probe fixed materialization/core join changed")
    tools = {
        "env": _observe_tool_fact(formal.ENV),
        "python": _observe_tool_fact(authority.REMOTE_PYTHON_REALPATH),
        "systemctl": _observe_tool_fact(formal.SYSTEMCTL),
        "systemd_run": _observe_tool_fact(formal.SYSTEMD_RUN),
    }
    probe_plan = {"activation_binding": {"remote_tool_facts": tools}}
    manager = _observe_manager(probe_plan)
    ancestry = _cgroup_ancestry(manager["user_manager_control_group"])
    receipt = formal.build_formal_host_epoch_receipt_v42r1(
        activation_core=core,
        manager_binding=manager,
        memory_limit_ancestry=ancestry,
        remote_tool_facts=tools,
    )
    return _write_stdout(receipt)


def _require_live_epoch(plan: dict[str, Any]) -> dict[str, Any]:
    _verify_tools(plan)
    manager = _observe_manager(plan)
    expected = plan["activation_binding"]
    for field, value in manager.items():
        if expected[field] != value:
            _fail(f"activation/live host epoch drifted: {field}")
    return manager


def _verify_fixed_materialization(plan: dict[str, Any]) -> dict[str, Any]:
    if ROOT != authority.REMOTE_SOURCE_ROOT:
        _fail("formal transport receiver is not in the fixed source root")
    phase = authority.verify_remote_control_phase_inventory_v42r1(
        "POST_MATERIALIZATION_PREPARE"
    )
    binding = plan["activation_binding"]
    if (
        phase["source_manifest"]["source_commit"] != plan["source_commit"]
        or phase["source_manifest"]["source_tree"] != plan["source_tree"]
        or phase["source_manifest"]["source_manifest_id"]
        != plan["source_manifest_id"]
        or phase["transport_manifest"]["transport_manifest_id"]
        != plan["transport_manifest_id"]
        or phase["local_materialization_attempt_id"]
        != binding["local_materialization_attempt_id"]
        or phase["remote_materialization_attempt_id"]
        != binding["remote_materialization_attempt_id"]
        or phase["materialization_terminal_id"]
        != binding["materialization_terminal_id"]
    ):
        _fail("fixed materialization differs from formal transport plan")
    _join_formal_transport_facts(
        phase["transport_manifest"],
        [plan["receiver_artifact"], plan["formal_authority_artifact"]],
    )
    return phase


def _open_manifested_runner_pin(
    *, plan: dict[str, Any], source_manifest: dict[str, Any]
) -> frozen_sender._PinnedLocalFile:  # noqa: SLF001
    facts = [
        fact
        for fact in source_manifest["source_facts"]
        if fact["relative_path"] == formal.FORMAL_RUNNER_RELATIVE
    ]
    if len(facts) != 1:
        _fail("formal runner source fact is absent or ambiguous")
    fact = facts[0]
    return frozen_sender._open_local_file_pin(  # noqa: SLF001
        path=str(authority.REMOTE_SOURCE_ROOT / formal.FORMAL_RUNNER_RELATIVE),
        mode=0o444,
        uid=authority.REMOTE_UID,
        gid=authority.REMOTE_GID,
        nlink=1,
        byte_count=fact["byte_count"],
        sha256=fact["sha256"],
        label="manifested formal runner source",
    )


def _exec_existing_runner(
    *, plan: dict[str, Any], source_manifest: dict[str, Any], mode: str
) -> NoReturn:
    if mode not in {"--prepare-remote", "--launch-remote"}:
        _fail("formal runner mode changed")
    _verify_program_self(plan)
    authority.verify_live_source_matches_manifest_v42(
        authority.REMOTE_SOURCE_ROOT, source_manifest
    )
    python_pin = _open_tool_pin(plan, "python")
    runner_pin = _open_manifested_runner_pin(
        plan=plan, source_manifest=source_manifest
    )
    try:
        python_pin.verify()
        runner_pin.verify()
        # The source descriptor survives only into the tiny loader.  The
        # loader consumes verified bytes and closes the entire non-stdio FD
        # range before compiling the existing runner.
        runner_flags = fcntl.fcntl(runner_pin.descriptor, fcntl.F_GETFD)
        fcntl.fcntl(
            runner_pin.descriptor,
            fcntl.F_SETFD,
            runner_flags & ~fcntl.FD_CLOEXEC,
        )
        python_path = f"/proc/self/fd/{python_pin.descriptor}"
        argv = (
            authority.REMOTE_PYTHON,
            "-I", "-S", "-B", "-c", VERIFIED_RUNNER_FD_LOADER_SOURCE,
            str(runner_pin.descriptor),
            runner_pin.sha256,
            str(runner_pin.byte_count),
            str(authority.REMOTE_SOURCE_ROOT / formal.FORMAL_RUNNER_RELATIVE),
            mode,
            plan["source_manifest_id"],
        )
        environment = dict(formal.FORMAL_SERVICE_ENVIRONMENT)
        os.execve(python_path, argv, environment)
    except BaseException:
        runner_pin.close()
        python_pin.close()
        raise
    raise AssertionError("descriptor-bound formal runner exec returned")


def _unit(plan: dict[str, Any], attempt_id: str) -> dict[str, Any]:
    properties = _systemctl_properties(
        plan=plan,
        user=True,
        unit=formal.unit_name_v42r1(attempt_id),
        fields=UNIT_SHOW_FIELDS,
    )
    result: dict[str, Any] = dict(properties)
    try:
        result["MainPID"] = int(properties["MainPID"])
    except ValueError as error:
        raise V42FormalTransportReceiverError("unit MainPID is not decimal") from error
    if properties["InvocationID"]:
        result["InvocationID"] = _canonical_uuid_from_systemd(
            properties["InvocationID"], "unit invocation ID"
        )
    # ExecStart is retained in the systemctl keyset as an auxiliary observation
    # only.  Its human-facing C escaping is not an argv serialization (and the
    # verified loader intentionally contains newlines, quotes, and backslashes).
    # Exact running argv instead comes from the already rejoined MainPID's NUL
    # separated procfs bytes.
    result.pop("ExecStart")
    if result["LoadState"] == "loaded" and result["MainPID"] > 1:
        pid = result["MainPID"]
        raw, _ = _stable_regular(Path(f"/proc/{pid}/cmdline"), 1024 * 1024)
        if not raw or not raw.endswith(b"\0") or b"\0\0" in raw:
            _fail("live unit /proc MainPID cmdline changed encoding")
        try:
            exec_argv = [
                item.decode("utf-8", errors="strict")
                for item in raw[:-1].split(b"\0")
            ]
        except UnicodeError as error:
            raise V42FormalTransportReceiverError(
                "live unit /proc MainPID cmdline is not UTF-8"
            ) from error
        cgroup_raw, _ = _stable_regular(Path(f"/proc/{pid}/cgroup"), 64 * 1024)
        expected_cgroup = ("0::" + result["ControlGroup"] + "\n").encode("ascii")
        if cgroup_raw != expected_cgroup:
            _fail("live unit MainPID procfs cgroup/systemctl join changed")
        argv_source = "PROC_MAINPID_CMDLINE"
    elif result["LoadState"] == "loaded":
        exec_argv = []
        argv_source = "UNAVAILABLE_NO_MAINPID"
    else:
        exec_argv = []
        argv_source = "ABSENT_UNIT"
    result["LiveMainPIDArgv"] = exec_argv
    result["LiveMainPIDArgvSource"] = argv_source
    return result


def _await_clean_wrapper_unit(
    plan: dict[str, Any], attempt_id: str
) -> dict[str, Any]:
    """Read-only wait for env/bootstrap exec to become the clean wrapper.

    ``systemd-run --service-type=exec`` may return while MainPID is still the
    verified bootstrap.  The PID survives its clean exec, so every poll must
    retain the same InvocationID/MainPID/cgroup/transient fragment.  No unit
    lifecycle operation is permitted here.
    """

    deadline = time.monotonic() + CLEAN_WRAPPER_TRANSITION_TIMEOUT_SECONDS
    locked: dict[str, Any] | None = None
    bootstrap = list(
        formal._receiver_python_argv(  # noqa: SLF001
            plan=plan, mode="--formal-launch-service-bootstrap",
            attempt_id=attempt_id,
        )
    )
    while True:
        unit = _unit(plan, attempt_id)
        formal._unit_observation(  # noqa: SLF001
            unit, formal.unit_name_v42r1(attempt_id)
        )
        if (
            unit["LoadState"] != "loaded"
            or unit["ActiveState"] not in {"active", "activating"}
            or unit["SubState"] not in {"start", "running"}
            or not unit["InvocationID"]
            or unit["MainPID"] <= 1
            or not unit["ControlGroup"]
        ):
            _fail("formal service exited before clean wrapper admission")
        identity = {
            key: unit[key]
            for key in (
                "Id", "InvocationID", "MainPID", "ControlGroup",
                "FragmentPath", "Type", "Restart", "RemainAfterExit",
                "SuccessExitStatus", "UMask", "KillMode", "TimeoutStopUSec",
                "RuntimeMaxUSec", "StandardInput", "StandardOutput",
                "StandardError", "WorkingDirectory", "Slice", "Environment",
            )
        }
        if locked is None:
            locked = identity
        elif identity != locked:
            _fail("formal service identity drifted during bootstrap clean exec")
        clean = list(
            formal._receiver_python_argv(  # noqa: SLF001
                plan=plan, mode="--formal-launch-service-wrapper",
                attempt_id=attempt_id,
                runtime_invocation_id=unit["InvocationID"],
                runtime_control_group=unit["ControlGroup"],
            )
        )
        if unit["LiveMainPIDArgv"] == clean:
            return unit
        if unit["LiveMainPIDArgv"] != bootstrap:
            _fail("formal service entered an unauthorized argv during clean exec")
        if time.monotonic() >= deadline:
            _fail("formal service did not reach the clean wrapper before deadline")
        time.sleep(0.02)


def _self_id_exact(
    path: Path, *, cap: int, schema: str, id_key: str, domain: str,
    joins: dict[str, Any], formal_domain: bool,
) -> bool:
    try:
        raw, observed = _stable_regular(path, cap)
    except (FileNotFoundError, V42FormalTransportReceiverError):
        return False
    if stat.S_IMODE(observed.st_mode) != 0o400 or observed.st_uid != authority.REMOTE_UID:
        return False
    try:
        document = _canonical(raw, str(path))
    except V42FormalTransportReceiverError:
        return False
    if document.get("schema") != schema or any(document.get(key) != value for key, value in joins.items()):
        return False
    identifier = document.get(id_key)
    if type(identifier) is not str or _HEX64.fullmatch(identifier) is None:
        return False
    payload = dict(document)
    del payload[id_key]
    if formal_domain:
        expected = formal._content_id(domain, payload)  # noqa: SLF001
    else:
        expected = hashlib.sha256(
            domain.encode("ascii") + b"\0" + canonical_json_bytes(payload)
        ).hexdigest()
    return identifier == expected


def _artifact_state(path: Path, verifier: Any) -> str:
    try:
        path.lstat()
    except FileNotFoundError:
        return "ABSENT"
    try:
        return "EXACT" if verifier() else "PRESENT_INVALID"
    except BaseException:
        return "PRESENT_INVALID"


def _ledger_raw(path: Path, cap: int) -> bytes:
    raw, observed = _stable_regular(path, cap)
    if (
        stat.S_IMODE(observed.st_mode) != 0o400
        or observed.st_uid != authority.REMOTE_UID
    ):
        _fail("remote formal ledger artifact mode or owner changed")
    return raw


def _prepare_receipt(plan: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    path = authority.fixed_authority_root_v42(ROOT) / authority.PREPARE_RECEIPT_NAME
    raw, observed = _stable_regular(path, formal.MAX_PREPARE_RECEIPT_BYTES)
    if stat.S_IMODE(observed.st_mode) != 0o400 or observed.st_uid != authority.REMOTE_UID:
        _fail("remote prepare receipt mode or owner changed")
    history = prereg._freshness()  # noqa: SLF001
    receipt = authority.verify_prepare_receipt_v42(
        raw,
        fresh_terminal_preregistration_id=prereg.PREREGISTRATION_ID,
        history_freshness_manifest_id=history["history_freshness_manifest_id"],
        root=ROOT,
        require_live_source=True,
    )
    if any(
        receipt[field] != plan[field]
        for field in (
            "source_commit", "source_tree", "source_manifest_id",
            "transport_manifest_id",
        )
    ):
        _fail("prepare receipt differs from formal transport plan")
    return receipt, raw


def _verify_prepare_failure_chain(plan: dict[str, Any]) -> bool:
    attempt_path = ROOT / authority.PREPARE_ATTEMPT_JOURNAL_NAME
    failure_path = ROOT / authority.PREPARE_FAILURE_JOURNAL_NAME
    attempt = existing_runner._verify_collected_id_document(  # noqa: SLF001
        _ledger_raw(attempt_path, 1024**2),
        label="formal inspection prepare attempt",
        schema="acfqp.v42_remote_ordinal2_prepare_attempt_journal.v42r1",
        id_key="prepare_attempt_journal_id",
        domain="acfqp:v42-remote-ordinal2:prepare-journal",
        exact_payload_fields=frozenset(
            {
                "schema", "schema_version", "formal_identity",
                "global_execution_ordinal", "source_commit", "source_tree",
                "source_manifest_id", "transport_manifest_id",
                "remote_host_alias", "remote_hostname", "prepare_ordinal",
                "outcome_or_tape_materialized", "formal_execution_performed",
                "same_identity_prepare_retry_forbidden",
            }
        ),
    )
    if (
        attempt.get("source_commit") != plan["source_commit"]
        or attempt.get("source_tree") != plan["source_tree"]
        or attempt.get("source_manifest_id") != plan["source_manifest_id"]
        or attempt.get("transport_manifest_id") != plan["transport_manifest_id"]
        or attempt.get("remote_host_alias") != authority.REMOTE_HOST_ALIAS
        or attempt.get("remote_hostname") != authority.REMOTE_HOSTNAME
        or attempt.get("prepare_ordinal") != authority.GLOBAL_EXECUTION_ORDINAL
        or attempt.get("outcome_or_tape_materialized") is not False
        or attempt.get("formal_execution_performed") is not False
        or attempt.get("same_identity_prepare_retry_forbidden") is not True
    ):
        _fail("formal inspection prepare attempt changed plan or retry join")
    failure = existing_runner._verify_collected_id_document(  # noqa: SLF001
        _ledger_raw(failure_path, 4 * 1024**2),
        label="formal inspection prepare failure",
        schema="acfqp.v42_remote_ordinal2_prepare_failure_journal.v42r1",
        id_key="prepare_failure_journal_id",
        domain="acfqp:v42-remote-ordinal2:prepare-journal",
        exact_payload_fields=frozenset(
            {
                "schema", "schema_version", "formal_identity",
                "global_execution_ordinal", "prepare_attempt_journal_id",
                "failure_stage", "failure_type", "failure_message",
                "authority_root_state", "evidence_root_state",
                "prepare_receipt_state", "outcome_or_tape_materialized",
                "formal_execution_performed",
                "same_identity_prepare_retry_forbidden",
            }
        ),
    )
    if (
        failure.get("prepare_attempt_journal_id")
        != attempt["prepare_attempt_journal_id"]
        or failure.get("outcome_or_tape_materialized") is not False
        or failure.get("formal_execution_performed") is not False
        or failure.get("same_identity_prepare_retry_forbidden") is not True
    ):
        _fail("formal inspection prepare failure changed attempt or retry join")
    return True


def _artifact_states(
    *, plan: dict[str, Any], operation: str,
    attempt_id: str, prepare_receipt: dict[str, Any] | None,
) -> dict[str, str]:
    receipt_path = authority.fixed_authority_root_v42(ROOT) / authority.PREPARE_RECEIPT_NAME
    prepare_receipt_state = _artifact_state(
        receipt_path,
        lambda: _prepare_receipt(plan)[0] is not None,
    )
    prepare_failure_path = ROOT / authority.PREPARE_FAILURE_JOURNAL_NAME
    prepare_failure_state = _artifact_state(
        prepare_failure_path,
        lambda: _verify_prepare_failure_chain(plan),
    )
    remote_attempt_path = formal.REMOTE_FORMAL_JOURNAL_ROOT / formal.REMOTE_LAUNCH_TRANSPORT_ATTEMPT_NAME
    if prepare_receipt is None:
        expected_attempt = None
    else:
        try:
            local_raw, _ = _stable_regular(
                authority.REMOTE_ROOT / authority.LOCAL_LAUNCH_ATTEMPT_NAME,
                4 * 1024**2,
            )
        except FileNotFoundError:
            expected_attempt = None
        else:
            local = authority.verify_local_launch_attempt_v42r1(
                local_raw, prepare_receipt=prepare_receipt
            )
            expected_attempt = formal.build_launch_transport_attempt_v42r1(
                plan=plan, prepare_receipt=prepare_receipt,
                local_launch_attempt=local,
            )
    remote_attempt_state = _artifact_state(
        remote_attempt_path,
        lambda: expected_attempt is not None
        and _canonical(_stable_regular(remote_attempt_path, 1024**2)[0], "remote launch transport attempt")
        == expected_attempt,
    )
    joins = {"formal_transport_plan_id": plan["formal_transport_plan_id"]}
    if expected_attempt is not None:
        joins["formal_launch_transport_attempt_id"] = expected_attempt[
            "formal_launch_transport_attempt_id"
        ]
    admission_path = formal.REMOTE_FORMAL_JOURNAL_ROOT / formal.REMOTE_LAUNCH_ADMISSION_RECEIPT_NAME
    admission_state = _artifact_state(
        admission_path,
        lambda: expected_attempt is not None
        and formal.verify_launch_admission_receipt_self_contained_v42r1(
            _ledger_raw(admission_path, formal.MAX_ADMISSION_RECEIPT_BYTES),
            plan=plan,
            launch_transport_attempt=expected_attempt,
        )
        is not None,
    )
    wrapper_path = formal.REMOTE_FORMAL_JOURNAL_ROOT / formal.REMOTE_SERVICE_WRAPPER_ATTESTATION_NAME
    wrapper_state = _artifact_state(
        wrapper_path,
        lambda: expected_attempt is not None
        and formal.verify_service_wrapper_attestation_self_contained_v42r1(
            _ledger_raw(wrapper_path, 1024**2),
            plan=plan,
            launch_transport_attempt=expected_attempt,
        )
        is not None,
    )
    launch_journal_path = ROOT / authority.LAUNCH_ATTEMPT_JOURNAL_NAME
    failure_path = ROOT / authority.LAUNCH_FAILURE_JOURNAL_NAME
    terminal_path = authority.fixed_evidence_root_v42(ROOT) / authority.TERMINAL_NAME
    launch_journal_state = "ABSENT"
    failure_state = "ABSENT"
    terminal_state = "ABSENT"
    if any(path.exists() for path in (launch_journal_path, failure_path, terminal_path)):
        try:
            if prepare_receipt is None:
                _fail("runner artifact projection omitted prepare receipt")
            local_attempt_raw = _ledger_raw(
                authority.REMOTE_ROOT / authority.LOCAL_LAUNCH_ATTEMPT_NAME,
                4 * 1024**2,
            )
            local_attempt = authority.verify_local_launch_attempt_v42r1(
                local_attempt_raw, prepare_receipt=prepare_receipt
            )
            if local_attempt["local_launch_attempt_id"] != attempt_id:
                _fail("runner artifact projection launch attempt changed")
            raw_by_role: dict[str, bytes] = {}
            for role, path, cap in existing_runner._collection_sources(  # noqa: SLF001
                authority.REMOTE_SOURCE_ROOT, authority.REMOTE_ROOT
            ):
                try:
                    raw_by_role[role] = _stable_regular(path, cap)[0]
                except FileNotFoundError:
                    continue
            status = existing_runner._verify_collected_artifacts(  # noqa: SLF001
                raw_by_role,
                local_receipt_raw=canonical_json_bytes(prepare_receipt),
                receipt=prepare_receipt,
                local_attempt_raw=local_attempt_raw,
                local_attempt=local_attempt,
            )
            launch_journal_state = "EXACT" if "LAUNCH_ATTEMPT" in raw_by_role else "ABSENT"
            failure_state = "EXACT" if status == "COMPLETE_FAILURE" else (
                "PRESENT_INVALID" if "LAUNCH_FAILURE" in raw_by_role else "ABSENT"
            )
            if status == "COMPLETE_TERMINAL":
                terminal_doc = _canonical(raw_by_role["TERMINAL"], "runner terminal")
                terminal_state = (
                    "EXACT_SUCCESS"
                    if terminal_doc["scientific_success"] is True
                    else "EXACT_FAIL_CLOSED"
                )
            elif "TERMINAL" in raw_by_role:
                terminal_state = "PRESENT_INVALID"
        except BaseException:
            launch_journal_state = (
                "PRESENT_INVALID" if launch_journal_path.exists() else "ABSENT"
            )
            failure_state = "PRESENT_INVALID" if failure_path.exists() else "ABSENT"
            terminal_state = "PRESENT_INVALID" if terminal_path.exists() else "ABSENT"
    return {
        "prepare_receipt": prepare_receipt_state,
        "prepare_failure": prepare_failure_state,
        "remote_launch_transport_attempt": remote_attempt_state,
        "remote_launch_admission_receipt": admission_state,
        "service_wrapper_attestation": wrapper_state,
        "launch_attempt_journal": launch_journal_state,
        "runner_failure": failure_state,
        "scientific_terminal": terminal_state,
    }


def _write_stdout(document: dict[str, Any]) -> int:
    sys.stdout.buffer.write(canonical_json_bytes(document) + b"\n")
    sys.stdout.buffer.flush()
    return 0


def _prepare_once(plan_id: str) -> int:
    document = _ingress(
        INGRESS_PREPARE_SCHEMA,
        {"formal_transport_plan", "formal_prepare_attempt"},
    )
    plan = _plan(document["formal_transport_plan"], plan_id)
    formal.verify_prepare_attempt_v42r1(
        document["formal_prepare_attempt"], plan=plan
    )
    processio.require_isolated_python()
    _verify_program_self(plan)
    phase = _verify_fixed_materialization(plan)
    _require_live_epoch(plan)
    if any(
        path.exists()
        for path in (
            ROOT / authority.PREPARE_ATTEMPT_JOURNAL_NAME,
            ROOT / authority.PREPARE_FAILURE_JOURNAL_NAME,
            authority.fixed_authority_root_v42(ROOT),
        )
    ):
        _fail("formal prepare identity already has state; use read-only inspection")
    # Existing runner writes the exact prepare receipt to stdout.  Do not add
    # an envelope or a second mutable state machine around it.
    _exec_existing_runner(
        plan=plan, source_manifest=phase["source_manifest"], mode="--prepare-remote"
    )


def _inspect_prepare(plan_id: str) -> int:
    document = _ingress(
        INGRESS_INSPECT_PREPARE_SCHEMA,
        {"formal_transport_plan", "formal_prepare_attempt_id", "inspection_ordinal"},
    )
    plan = _plan(document["formal_transport_plan"], plan_id)
    _verify_program_self(plan)
    attempt_id = document["formal_prepare_attempt_id"]
    if type(attempt_id) is not str or _HEX64.fullmatch(attempt_id) is None:
        _fail("prepare inspection attempt ID changed")
    manager = _observe_manager(plan)
    states = _artifact_states(
        plan=plan, operation=formal.OPERATION_PREPARE,
        attempt_id=attempt_id, prepare_receipt=None,
    )
    recovered: dict[str, dict[str, Any]] = {}
    if states["prepare_receipt"] == "EXACT":
        recovered["prepare_receipt"], _ = _prepare_receipt(plan)
    inspection = formal.build_read_only_inspection_v42r1(
        plan=plan, operation=formal.OPERATION_PREPARE, attempt_id=attempt_id,
        inspection_ordinal=document["inspection_ordinal"],
        manager_binding=manager, unit_observation=None, artifact_states=states,
        recovered_documents=recovered,
    )
    return _write_stdout(inspection)


def _create_remote_journal(plan: dict[str, Any], attempt: dict[str, Any]) -> None:
    processio.create_one_shot_root(
        formal.REMOTE_FORMAL_JOURNAL_ROOT,
        expected_parent=formal.REMOTE_FORMAL_JOURNAL_ROOT.parent,
    )
    processio.write_once(
        formal.REMOTE_FORMAL_JOURNAL_ROOT / REMOTE_PLAN_NAME,
        canonical_json_bytes(plan),
    )
    processio.write_once(
        formal.REMOTE_FORMAL_JOURNAL_ROOT
        / formal.REMOTE_LAUNCH_TRANSPORT_ATTEMPT_NAME,
        canonical_json_bytes(attempt),
    )


def _admit_launch(plan_id: str) -> int:
    document = _ingress(
        INGRESS_ADMIT_SCHEMA,
        {
            "formal_transport_plan", "prepare_receipt", "local_launch_attempt",
            "formal_launch_transport_attempt",
        },
    )
    plan = _plan(document["formal_transport_plan"], plan_id)
    _verify_program_self(plan)
    processio.require_isolated_python()
    receipt, receipt_raw = _prepare_receipt(plan)
    supplied_receipt = _canonical(
        canonical_json_bytes(document["prepare_receipt"]), "supplied prepare receipt"
    )
    if supplied_receipt != receipt:
        _fail("supplied prepare receipt differs from fixed remote receipt")
    local = authority.verify_local_launch_attempt_v42r1(
        document["local_launch_attempt"], prepare_receipt=receipt
    )
    attempt = formal.build_launch_transport_attempt_v42r1(
        plan=plan, prepare_receipt=receipt, local_launch_attempt=local
    )
    if document["formal_launch_transport_attempt"] != attempt:
        _fail("formal launch transport attempt changed")
    authority.verify_remote_control_phase_inventory_v42r1(
        "POST_PREPARE_AWAITING_LOCAL_LAUNCH", prepare_receipt=receipt
    )
    manager = _require_live_epoch(plan)
    _create_remote_journal(plan, attempt)
    processio.write_once(
        authority.REMOTE_ROOT / authority.LOCAL_LAUNCH_ATTEMPT_NAME,
        canonical_json_bytes(local),
    )
    argv = formal.build_systemd_run_argv_v42r1(
        plan=plan, local_launch_attempt=local
    )
    systemd_pin = _open_tool_pin(plan, "systemd_run")
    try:
        returncode, stdout, stderr = _run_bounded(
            argv,
            environment=dict(formal.SYSTEMD_CLIENT_ENVIRONMENT),
            stdout_cap=MAX_SYSTEMD_RUN_STREAM,
            stderr_cap=MAX_SYSTEMD_RUN_STREAM,
            timeout_seconds=COMMAND_TIMEOUT_SECONDS,
            executable_pin=systemd_pin,
        )
    finally:
        systemd_pin.close()
    if returncode != 0 or stdout or stderr:
        _fail("systemd launch admission did not return exact quiet success")
    unit = _await_clean_wrapper_unit(plan, local["local_launch_attempt_id"])
    admission = formal.build_launch_admission_receipt_v42r1(
        plan=plan,
        launch_transport_attempt=attempt,
        manager_binding=manager,
        unit_observation=unit,
        systemd_run_argv=argv,
    )
    processio.write_once(
        formal.REMOTE_FORMAL_JOURNAL_ROOT
        / formal.REMOTE_LAUNCH_ADMISSION_RECEIPT_NAME,
        canonical_json_bytes(admission),
    )
    del receipt_raw
    return _write_stdout(admission)


def _inspect_launch(plan_id: str) -> int:
    document = _ingress(
        INGRESS_INSPECT_LAUNCH_SCHEMA,
        {"formal_transport_plan", "local_launch_attempt_id", "inspection_ordinal"},
    )
    plan = _plan(document["formal_transport_plan"], plan_id)
    _verify_program_self(plan)
    attempt_id = document["local_launch_attempt_id"]
    if type(attempt_id) is not str or _HEX64.fullmatch(attempt_id) is None:
        _fail("launch inspection attempt ID changed")
    manager = _observe_manager(plan)
    try:
        receipt, _ = _prepare_receipt(plan)
    except BaseException:
        receipt = None
    unit = _unit(plan, attempt_id)
    states = _artifact_states(
        plan=plan, operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id, prepare_receipt=receipt,
    )
    recovered: dict[str, dict[str, Any]] = {}
    if states["remote_launch_admission_receipt"] == "EXACT":
        if receipt is None:
            _fail("launch inspection exact admission omitted prepare receipt")
        local_raw = _ledger_raw(
            authority.REMOTE_ROOT / authority.LOCAL_LAUNCH_ATTEMPT_NAME,
            4 * 1024**2,
        )
        local = authority.verify_local_launch_attempt_v42r1(
            local_raw, prepare_receipt=receipt
        )
        expected_attempt = formal.build_launch_transport_attempt_v42r1(
            plan=plan, prepare_receipt=receipt, local_launch_attempt=local
        )
        admission_raw = _ledger_raw(
            formal.REMOTE_FORMAL_JOURNAL_ROOT
            / formal.REMOTE_LAUNCH_ADMISSION_RECEIPT_NAME,
            formal.MAX_ADMISSION_RECEIPT_BYTES,
        )
        recovered["launch_admission_receipt"] = (
            formal.verify_launch_admission_receipt_self_contained_v42r1(
                admission_raw, plan=plan,
                launch_transport_attempt=expected_attempt,
            )
        )
    inspection = formal.build_read_only_inspection_v42r1(
        plan=plan, operation=formal.OPERATION_LAUNCH, attempt_id=attempt_id,
        inspection_ordinal=document["inspection_ordinal"],
        manager_binding=manager, unit_observation=unit, artifact_states=states,
        recovered_documents=recovered,
    )
    return _write_stdout(inspection)


def _stdio_facts() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    null_observed = os.stat("/dev/null", follow_symlinks=False)
    for descriptor in range(3):
        observed = os.fstat(descriptor)
        target = os.readlink(f"/proc/self/fd/{descriptor}")
        if (
            not stat.S_ISCHR(observed.st_mode)
            or observed.st_rdev != null_observed.st_rdev
            or target != "/dev/null"
            or os.isatty(descriptor)
        ):
            _fail("formal service stdio is not exact /dev/null")
        result.append(
            {
                "descriptor": descriptor,
                "target": target,
                "node_type": "CHARACTER_DEVICE",
                "isatty": False,
            }
        )
    return result


def _live_file_descriptors() -> list[int]:
    try:
        names = os.listdir("/proc/self/fd")
    except OSError as error:
        raise V42FormalTransportReceiverError(
            "formal wrapper cannot enumerate live descriptors"
        ) from error
    result: list[int] = []
    for name in names:
        if not name.isdigit():
            _fail("formal wrapper descriptor name changed")
        descriptor = int(name)
        try:
            fcntl.fcntl(descriptor, fcntl.F_GETFD)
        except OSError as error:
            if error.errno == errno.EBADF:
                continue
            raise
        result.append(descriptor)
    return sorted(result)


def _self_cgroup() -> str:
    raw, _ = _stable_regular(Path("/proc/self/cgroup"), 64 * 1024)
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        _fail("service /proc/self/cgroup changed encoding")
    line = raw[:-1]
    if not line.startswith(b"0::"):
        _fail("formal service is not in one unified cgroup-v2 membership")
    try:
        return line[3:].decode("ascii", errors="strict")
    except UnicodeError as error:
        raise V42FormalTransportReceiverError("service cgroup is not ASCII") from error


def _service_bootstrap(plan_id: str, attempt_id: str) -> NoReturn:
    """Validate systemd runtime identity, then clean-exec the real wrapper."""

    processio.require_isolated_python()
    inherited = _live_file_descriptors()
    if inherited != [0, 1, 2]:
        _fail("formal service bootstrap inherited an extra file descriptor")
    _stdio_facts()
    if ROOT != authority.REMOTE_SOURCE_ROOT:
        _fail("formal service bootstrap is not in the fixed source root")
    plan_raw, _ = _stable_regular(
        formal.REMOTE_FORMAL_JOURNAL_ROOT / REMOTE_PLAN_NAME, 4 * 1024**2
    )
    plan = _plan(_canonical(plan_raw, "remote formal plan"), plan_id)
    _verify_program_self(plan)
    _verify_tools(plan)
    invocation_raw = os.environ.get("INVOCATION_ID")
    if type(invocation_raw) is not str or _INVOCATION32.fullmatch(invocation_raw) is None:
        _fail("formal service bootstrap INVOCATION_ID changed")
    invocation = str(uuid.UUID(invocation_raw))
    service_cgroup = _self_cgroup()
    unit = _unit(plan, attempt_id)
    if (
        unit["LoadState"] != "loaded"
        or unit["ActiveState"] != "active"
        or unit["SubState"] not in {"start", "running"}
        or unit["MainPID"] != os.getpid()
        or unit["InvocationID"] != invocation
        or unit["ControlGroup"] != service_cgroup
        or unit["LiveMainPIDArgv"]
        != list(
            formal._receiver_python_argv(  # noqa: SLF001
                plan=plan, mode="--formal-launch-service-bootstrap",
                attempt_id=attempt_id,
            )
        )
    ):
        _fail("formal service bootstrap/systemd live identity changed")
    invocation_path = Path(
        f"/run/user/{authority.REMOTE_UID}/systemd/units/invocation:"
        + formal.unit_name_v42r1(attempt_id)
    )
    if not invocation_path.is_symlink() or os.readlink(invocation_path) != invocation_raw:
        _fail("formal service bootstrap invocation symlink changed")
    clean_argv = formal._receiver_python_argv(  # noqa: SLF001
        plan=plan, mode="--formal-launch-service-wrapper", attempt_id=attempt_id,
        runtime_invocation_id=invocation, runtime_control_group=service_cgroup,
    )
    python_pin = _open_tool_pin(plan, "python")
    try:
        python_pin.verify()
        os.execve(
            f"/proc/self/fd/{python_pin.descriptor}",
            clean_argv,
            dict(formal.FORMAL_SERVICE_ENVIRONMENT),
        )
    except BaseException:
        python_pin.close()
        raise
    raise AssertionError("formal clean wrapper exec returned")


def _wrapper(
    plan_id: str, attempt_id: str, runtime_invocation_id: str,
    runtime_control_group: str,
) -> int:
    processio.require_isolated_python()
    inherited_descriptors = _live_file_descriptors()
    if inherited_descriptors != [0, 1, 2]:
        _fail("formal service wrapper inherited an extra file descriptor")
    if ROOT != authority.REMOTE_SOURCE_ROOT:
        _fail("formal service wrapper is not in the fixed source root")
    plan_raw, _ = _stable_regular(
        formal.REMOTE_FORMAL_JOURNAL_ROOT / REMOTE_PLAN_NAME, 4 * 1024**2
    )
    plan = _plan(_canonical(plan_raw, "remote formal plan"), plan_id)
    _verify_program_self(plan)
    live_tool_facts = _verify_tools(plan)
    receipt, _ = _prepare_receipt(plan)
    local_raw, _ = _stable_regular(
        authority.REMOTE_ROOT / authority.LOCAL_LAUNCH_ATTEMPT_NAME,
        4 * 1024**2,
    )
    local = authority.verify_local_launch_attempt_v42r1(
        local_raw, prepare_receipt=receipt
    )
    if local["local_launch_attempt_id"] != attempt_id:
        _fail("service wrapper local launch attempt ID changed")
    attempt_raw, _ = _stable_regular(
        formal.REMOTE_FORMAL_JOURNAL_ROOT
        / formal.REMOTE_LAUNCH_TRANSPORT_ATTEMPT_NAME,
        1024**2,
    )
    attempt = _canonical(attempt_raw, "remote launch transport attempt")
    expected_attempt = formal.build_launch_transport_attempt_v42r1(
        plan=plan, prepare_receipt=receipt, local_launch_attempt=local
    )
    if attempt != expected_attempt:
        _fail("service wrapper transport attempt changed")
    manager = _require_live_epoch(plan)
    unit = _unit(plan, attempt_id)
    service_pid = os.getpid()
    if unit["MainPID"] != service_pid:
        _fail("service wrapper PID differs from systemd MainPID")
    service_cgroup = _self_cgroup()
    if unit["ControlGroup"] != service_cgroup:
        _fail("service wrapper cgroup differs from systemd ControlGroup")
    invocation_path = Path(
        f"/run/user/{authority.REMOTE_UID}/systemd/units/invocation:"
        + formal.unit_name_v42r1(attempt_id)
    )
    if not invocation_path.is_symlink():
        _fail("service invocation symlink is absent")
    invocation_raw = os.readlink(invocation_path)
    invocation = _canonical_uuid_from_systemd(
        invocation_raw, "service invocation symlink"
    )
    if (
        unit["InvocationID"] != invocation
        or runtime_invocation_id != invocation
        or runtime_control_group != service_cgroup
    ):
        _fail("service invocation symlink/systemctl join changed")
    # Type=exec may enter this wrapper before the SSH ingress has completed
    # its systemctl rejoin and durable admission publication.  Wait only for
    # that exact append-only receipt.  Timeout is a closed launch; this wrapper
    # never enters the scientific runner without the durable handshake.
    admission_path = (
        formal.REMOTE_FORMAL_JOURNAL_ROOT
        / formal.REMOTE_LAUNCH_ADMISSION_RECEIPT_NAME
    )
    deadline = time.monotonic() + ADMISSION_HANDSHAKE_TIMEOUT_SECONDS
    admission: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        try:
            admission_raw, admission_observed = _stable_regular(
                admission_path, formal.MAX_ADMISSION_RECEIPT_BYTES
            )
        except FileNotFoundError:
            time.sleep(0.05)
            continue
        if (
            stat.S_IMODE(admission_observed.st_mode) != 0o400
            or admission_observed.st_uid != authority.REMOTE_UID
        ):
            _fail("formal admission receipt mode or owner changed")
        admission = formal.verify_launch_admission_receipt_self_contained_v42r1(
            admission_raw, plan=plan, launch_transport_attempt=attempt
        )
        break
    if admission is None:
        _fail("formal service wrapper timed out awaiting durable admission")
    if (
        admission["unit_invocation_id"] != invocation
        or admission["unit_main_pid"] != service_pid
        or admission["unit_control_group"] != service_cgroup
    ):
        _fail("formal admission receipt differs from live wrapper identity")
    stdio = _stdio_facts()
    environment = dict(os.environ)
    attestation = formal.build_service_wrapper_attestation_v42r1(
        plan=plan,
        launch_transport_attempt=attempt,
        manager_binding=manager,
        unit_observation=unit,
        service_pid=service_pid,
        service_cgroup=service_cgroup,
        service_environment=environment,
        stdio_facts=stdio,
        live_file_descriptors=inherited_descriptors,
        live_tool_facts=live_tool_facts,
    )
    processio.write_once(
        formal.REMOTE_FORMAL_JOURNAL_ROOT
        / formal.REMOTE_SERVICE_WRAPPER_ATTESTATION_NAME,
        canonical_json_bytes(attestation),
    )
    # The wrapper's attestation is durable before the first scientific launch
    # mutation.  The existing runner remains the sole scientific state machine.
    _exec_existing_runner(
        plan=plan,
        source_manifest=receipt["source_manifest"],
        mode="--launch-remote",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V42 formal transport remote ingress")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-once", action="store_true")
    modes.add_argument("--inspect-prepare", action="store_true")
    modes.add_argument("--admit-launch", action="store_true")
    modes.add_argument("--inspect-launch", action="store_true")
    modes.add_argument("--formal-launch-service-wrapper", action="store_true")
    modes.add_argument("--formal-launch-service-bootstrap", action="store_true")
    modes.add_argument("--probe-host-epoch", action="store_true")
    parser.add_argument("--formal-transport-plan-id")
    parser.add_argument("--local-launch-attempt-id")
    parser.add_argument("--runtime-invocation-id")
    parser.add_argument("--runtime-control-group")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.probe_host_epoch:
        if (
            arguments.formal_transport_plan_id is not None
            or arguments.local_launch_attempt_id is not None
            or arguments.runtime_invocation_id is not None
            or arguments.runtime_control_group is not None
        ):
            _fail("host epoch probe forbids formal attempt identifiers")
        return _host_epoch_probe()
    plan_id = arguments.formal_transport_plan_id
    if type(plan_id) is not str or _HEX64.fullmatch(plan_id) is None:
        _fail("formal transport plan ID changed")
    if arguments.formal_launch_service_bootstrap:
        if (
            type(arguments.local_launch_attempt_id) is not str
            or _HEX64.fullmatch(arguments.local_launch_attempt_id) is None
            or arguments.runtime_invocation_id is not None
            or arguments.runtime_control_group is not None
        ):
            _fail("formal service bootstrap argument contract changed")
        _service_bootstrap(plan_id, arguments.local_launch_attempt_id)
    if arguments.formal_launch_service_wrapper:
        if (
            type(arguments.local_launch_attempt_id) is not str
            or _HEX64.fullmatch(arguments.local_launch_attempt_id) is None
            or type(arguments.runtime_invocation_id) is not str
            or str(uuid.UUID(arguments.runtime_invocation_id))
            != arguments.runtime_invocation_id
            or type(arguments.runtime_control_group) is not str
        ):
            _fail("formal service wrapper omitted its local launch attempt ID")
        return _wrapper(
            plan_id, arguments.local_launch_attempt_id,
            arguments.runtime_invocation_id, arguments.runtime_control_group,
        )
    if (
        arguments.local_launch_attempt_id is not None
        or arguments.runtime_invocation_id is not None
        or arguments.runtime_control_group is not None
    ):
        _fail("only the formal service wrapper accepts a launch attempt argument")
    if arguments.prepare_once:
        return _prepare_once(plan_id)
    if arguments.inspect_prepare:
        return _inspect_prepare(plan_id)
    if arguments.admit_launch:
        return _admit_launch(plan_id)
    return _inspect_launch(plan_id)


if __name__ == "__main__":
    raise SystemExit(main())
