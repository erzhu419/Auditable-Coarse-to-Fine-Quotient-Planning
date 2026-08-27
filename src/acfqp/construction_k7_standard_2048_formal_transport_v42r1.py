"""Pure authority for the V42 ordinal-2 formal prepare/launch transport.

This module deliberately performs no I/O.  It binds a separately validated
materialization-activation terminal to two one-shot SSH effects:

* the short remote ``prepare`` operation; and
* admission of the seven-day formal launch to a user systemd service.

SSH is only the admission transport.  The formal launch service is never
waited for, piped, attached to a tty, collected, scoped, or bound to the SSH
session.  Once a local network-start marker exists the same effect is never
replayed; only the read-only inspection protocol may advance classification.

The activation authority was developed independently from this successor.  A
caller must therefore supply an explicit validator adapter.  The adapter must
return the exact normalized protocol binding below.  This avoids guessing the
activation terminal schema or treating an unverified JSON object as a join.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import hashlib
from pathlib import Path, PurePosixPath
import re
import shlex
import uuid
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_materialization_transport_v42r1 as preformal,
)
from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = authority.SCHEMA_VERSION
DOMAIN_PREFIX = "acfqp:v42-remote-ordinal2:formal-transport:"

FORMAL_TRANSPORT_PLAN_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_transport_plan.v42r1"
)
FORMAL_PREPARE_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_prepare_attempt.v42r1"
)
FORMAL_LAUNCH_TRANSPORT_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_launch_transport_attempt.v42r1"
)
FORMAL_NETWORK_START_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_network_start.v42r1"
)
FORMAL_OPERATION_OUTCOME_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_operation_outcome.v42r1"
)
FORMAL_LAUNCH_ADMISSION_RECEIPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_launch_admission_receipt.v42r1"
)
FORMAL_SERVICE_WRAPPER_ATTESTATION_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_service_wrapper_attestation.v42r1"
)
FORMAL_READ_ONLY_INSPECTION_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_read_only_inspection.v42r1"
)
FORMAL_CLASSIFICATION_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_transport_classification.v42r1"
)
PRODUCTION_ACTIVATION_CORE_SCHEMA = (
    "acfqp.v42_remote_ordinal2_production_activation_core.v42r1"
)
FORMAL_HOST_EPOCH_RECEIPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_formal_host_epoch_receipt.v42r1"
)

ACTIVATION_TERMINAL_PROTOCOL = (
    "acfqp.v42_remote_ordinal2_activation_terminal_adapter.v1"
)

LOCAL_FORMAL_JOURNAL_ROOT = Path(
    "/home/erzhu419/mine_code/.acfqp-v42-local-formal-transport-ordinal2"
)
REMOTE_FORMAL_JOURNAL_ROOT = Path(
    "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2-formal-transport"
)
LOCAL_KNOWN_HOSTS_NAME = "PINNED_KNOWN_HOSTS"
LOCAL_PLAN_NAME = "FORMAL_TRANSPORT_PLAN.json"
LOCAL_ACTIVATION_TERMINAL_NAME = "ACTIVATION_TERMINAL.json"
LOCAL_PREPARE_ATTEMPT_NAME = "FORMAL_PREPARE_ATTEMPT.json"
LOCAL_PREPARE_NETWORK_START_NAME = "FORMAL_PREPARE_NETWORK_START.json"
LOCAL_PREPARE_RECEIPT_NAME = "REMOTE_PREPARE_RECEIPT.json"
LOCAL_PREPARE_OUTCOME_NAME = "FORMAL_PREPARE_OUTCOME.json"
LOCAL_LAUNCH_ATTEMPT_NAME = authority.LOCAL_LAUNCH_ATTEMPT_NAME
LOCAL_LAUNCH_TRANSPORT_ATTEMPT_NAME = "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json"
LOCAL_LAUNCH_NETWORK_START_NAME = "FORMAL_LAUNCH_NETWORK_START.json"
LOCAL_LAUNCH_ADMISSION_RECEIPT_NAME = "FORMAL_LAUNCH_ADMISSION_RECEIPT.json"
LOCAL_LAUNCH_OUTCOME_NAME = "FORMAL_LAUNCH_OUTCOME.json"
LOCAL_INSPECTION_PREFIX = "READ_ONLY_INSPECTION."

REMOTE_LAUNCH_TRANSPORT_ATTEMPT_NAME = "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json"
REMOTE_LAUNCH_ADMISSION_RECEIPT_NAME = "FORMAL_LAUNCH_ADMISSION_RECEIPT.json"
REMOTE_SERVICE_WRAPPER_ATTESTATION_NAME = "FORMAL_SERVICE_WRAPPER_ATTESTATION.json"

FORMAL_RECEIVER_RELATIVE = (
    "scripts/v42_standard_2048_formal_transport_receiver.py"
)
FORMAL_DRIVER_RELATIVE = (
    "scripts/run_v42_standard_2048_formal_transport_driver.py"
)
FORMAL_AUTHORITY_RELATIVE = (
    "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py"
)
FORMAL_RUNNER_RELATIVE = "scripts/run_v42_standard_2048_remote_ordinal2.py"

SYSTEMD_RUN = "/usr/bin/systemd-run"
SYSTEMCTL = "/usr/bin/systemctl"
ENV = "/usr/bin/env"
REMOTE_PYTHON = authority.REMOTE_PYTHON
SYSTEMD_UNIT_PREFIX = "acfqp-v42-remote-ordinal2-"
SYSTEMD_RUNTIME_MAX_SECONDS = 606_300
SYSTEMD_TIMEOUT_STOP_SECONDS = 30
SYSTEMD_SLICE = "app.slice"
SYSTEMD_CLIENT_ENVIRONMENT = {
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "LC_ALL": "C.UTF-8",
    "XDG_RUNTIME_DIR": "/run/user/1000",
}
FORMAL_SERVICE_ENVIRONMENT = {
    "HOME": "/home/erzhu419",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "LOGNAME": authority.REMOTE_USER,
    "PATH": "/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONCOERCECLOCALE": "0",
    "USER": authority.REMOTE_USER,
}

FORBIDDEN_SYSTEMD_OPTIONS = frozenset(
    {"--wait", "--pipe", "--pty", "--scope", "--collect"}
)

OPERATION_PREPARE = "PREPARE"
OPERATION_LAUNCH = "LAUNCH"
OPERATIONS = (OPERATION_PREPARE, OPERATION_LAUNCH)

OUTCOME_PRE_NETWORK_FAILURE = "PRE_NETWORK_FAILURE"
OUTCOME_COMPLETE_EXACT_RECEIPT = "COMPLETE_EXACT_RECEIPT"
OUTCOME_POST_MARKER_AMBIGUOUS = "POST_MARKER_WITHOUT_EXACT_RECEIPT"
OUTCOME_CLASSES = (
    OUTCOME_PRE_NETWORK_FAILURE,
    OUTCOME_COMPLETE_EXACT_RECEIPT,
    OUTCOME_POST_MARKER_AMBIGUOUS,
)

CLASS_PRE_NETWORK_RETRYABLE = "PRE_NETWORK_FAILURE_RETRYABLE"
CLASS_PREPARE_COMPLETE = "PREPARE_COMPLETE_EXACT_RECEIPT"
CLASS_LAUNCH_ADMITTED = "LAUNCH_ADMITTED_INSPECTION_REQUIRED"
CLASS_IN_PROGRESS = "IN_PROGRESS_READ_ONLY_WAIT"
CLASS_COMPLETE_SUCCESS = "COMPLETE_FORMAL_SUCCESS"
CLASS_COMPLETE_FAILURE = "COMPLETE_FORMAL_FAILURE"
CLASS_AMBIGUOUS = "AMBIGUOUS_PERMANENTLY_CLOSED"
CLASSIFICATIONS = (
    CLASS_PRE_NETWORK_RETRYABLE,
    CLASS_PREPARE_COMPLETE,
    CLASS_LAUNCH_ADMITTED,
    CLASS_IN_PROGRESS,
    CLASS_COMPLETE_SUCCESS,
    CLASS_COMPLETE_FAILURE,
    CLASS_AMBIGUOUS,
)

UNIT_LOAD_STATES = ("loaded", "not-found", "masked", "error")
UNIT_ACTIVE_STATES = (
    "active",
    "activating",
    "deactivating",
    "inactive",
    "failed",
    "unknown",
)
UNIT_SUB_STATES = (
    "start",
    "running",
    "exited",
    "dead",
    "failed",
    "auto-restart",
    "unknown",
)
ARTIFACT_STATES = (
    "ABSENT", "EXACT", "EXACT_SUCCESS", "EXACT_FAIL_CLOSED",
    "PRESENT_INVALID", "UNOBSERVABLE",
)

MAX_ACTIVATION_TERMINAL_BYTES = 4 * 1024**2
MAX_PREPARE_RECEIPT_BYTES = 64 * 1024**2
MAX_ADMISSION_RECEIPT_BYTES = 1024**2
MAX_INSPECTION_BYTES = MAX_PREPARE_RECEIPT_BYTES + 4 * 1024**2
# Prepare receipts carry the verified source/transport context and authority
# explicitly permits up to 64 MiB.  The transport remains bounded at that same
# authority cap rather than silently narrowing the accepted receipt language.
MAX_STDOUT_BYTES = MAX_PREPARE_RECEIPT_BYTES
MAX_STDERR_BYTES = 1024**2
PREPARE_TRANSPORT_TIMEOUT_SECONDS = 900.0
ADMISSION_TRANSPORT_TIMEOUT_SECONDS = 120.0
INSPECTION_TRANSPORT_TIMEOUT_SECONDS = 120.0

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_CGROUP = re.compile(r"/(?:[A-Za-z0-9_.:@\\-]+/?)*")

# This stdlib-only loader is the first project-specific code reached by SSH
# and systemd.  It holds and verifies the committed receiver bytes before
# compiling those bytes from memory.  Thus replacing the named receiver after
# the read cannot redirect this invocation.  The fixed materialized source
# closure remains the explicitly bounded TCB for the receiver's imports.
VERIFIED_RECEIVER_LOADER_SOURCE = r'''import hashlib
import importlib.machinery
import json
import os
import stat
import sys

path, expected_sha, expected_count_raw, expected_source_id, expected_transport_id = sys.argv[1:6]
expected_count = int(expected_count_raw)
source_root = os.path.dirname(os.path.dirname(path))
control_root = os.path.dirname(source_root)
receiver_arguments = sys.argv[6:]
if not receiver_arguments:
    raise RuntimeError("formal loader receiver mode is absent")
loader_mode = receiver_arguments[0]

def live_fds():
    result = []
    for name in os.listdir("/proc/self/fd"):
        if not name.isdigit():
            raise RuntimeError("formal loader descriptor name changed")
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        result.append(descriptor)
    return sorted(result)

expected_python_path = ["/usr/lib/python310.zip", "/usr/lib/python3.10", "/usr/lib/python3.10/lib-dynload"]
if not (sys.executable == "/usr/bin/python3" and os.path.realpath(sys.executable) == "/usr/bin/python3.10" and os.path.realpath("/proc/self/exe") == "/usr/bin/python3.10" and tuple(sys.version_info[:3]) == (3, 10, 12) and sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode is True and sys.gettrace() is None and sys.getprofile() is None and sys.path == expected_python_path and sys.orig_argv[:5] == ["/usr/bin/python3", "-I", "-S", "-B", "-c"] and len(sys.orig_argv) == len(sys.argv) + 5 and sys.orig_argv[6:] == sys.argv[1:]):
    raise RuntimeError("formal loader isolated Python invocation changed")
if live_fds() != [0, 1, 2] or any(os.isatty(descriptor) for descriptor in (0, 1, 2)):
    raise RuntimeError("formal loader stdio or descriptor inventory changed")
if loader_mode in ("--formal-launch-service-bootstrap", "--formal-launch-service-wrapper"):
    null = os.stat("/dev/null", follow_symlinks=False)
    for descriptor in (0, 1, 2):
        observed = os.fstat(descriptor)
        if not (stat.S_ISCHR(observed.st_mode) and observed.st_rdev == null.st_rdev and os.readlink("/proc/self/fd/" + str(descriptor)) == "/dev/null"):
            raise RuntimeError("formal service loader stdio is not /dev/null")
    if loader_mode == "--formal-launch-service-bootstrap":
        invocation = os.environ.get("INVOCATION_ID")
        if type(invocation) is not str or len(invocation) != 32 or any(character not in "0123456789abcdef" for character in invocation):
            raise RuntimeError("formal bootstrap loader invocation environment changed")
    else:
        expected_environment = {"HOME": "/home/erzhu419", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "LOGNAME": "erzhu419", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONCOERCECLOCALE": "0", "USER": "erzhu419"}
        if dict(os.environ) != expected_environment:
            raise RuntimeError("formal clean-wrapper loader environment changed")
else:
    if loader_mode not in ("--prepare-once", "--inspect-prepare", "--admit-launch", "--inspect-launch", "--probe-host-epoch") or dict(os.environ) != {"LC_CTYPE": "C.UTF-8"}:
        raise RuntimeError("formal SSH loader mode or clean environment changed")

def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError("duplicate formal loader JSON key")
        result[key] = value
    return result

def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8", errors="strict")

def read_regular(target, maximum, mode):
    named = os.lstat(target)
    descriptor = os.open(target, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if not (stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode) == mode and before.st_uid == 1000 and before.st_gid == 1000 and before.st_nlink == 1 and 0 < before.st_size <= maximum and (before.st_dev, before.st_ino) == (named.st_dev, named.st_ino)):
            raise RuntimeError("formal loader file identity changed: " + target)
        chunks = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise RuntimeError("formal loader file ended early: " + target)
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise RuntimeError("formal loader file grew during read: " + target)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = os.lstat(target)
    fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, field) != getattr(after, field) or getattr(after, field) != getattr(final, field) for field in fields):
        raise RuntimeError("formal loader file changed during read: " + target)
    return b"".join(chunks)

def document(name):
    raw = read_regular(os.path.join(control_root, name), 64 * 1024**2, 0o400)
    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=unique, parse_constant=lambda token: (_ for _ in ()).throw(RuntimeError("nonfinite formal loader JSON")))
    if type(value) is not dict or canonical_bytes(value) != raw:
        raise RuntimeError("formal loader control is not canonical: " + name)
    return value

source_manifest = document("EXECUTION_SOURCE_MANIFEST.json")
source_payload = dict(source_manifest)
source_identifier = source_payload.pop("source_manifest_id", None)
if source_identifier != expected_source_id or hashlib.sha256(b"acfqp:v42-remote-ordinal2:source-manifest\0" + canonical_bytes(source_payload)).hexdigest() != source_identifier:
    raise RuntimeError("formal loader source manifest identity changed")
transport_manifest = document("TRANSPORT_MANIFEST.json")
transport_payload = dict(transport_manifest)
transport_identifier = transport_payload.pop("transport_manifest_id", None)
if transport_identifier != expected_transport_id or hashlib.sha256(b"acfqp:v42-remote-ordinal2:transport-manifest\0" + canonical_bytes(transport_payload)).hexdigest() != transport_identifier or transport_manifest.get("execution_source_manifest_id") != source_identifier or transport_manifest.get("source_commit") != source_manifest.get("source_commit") or transport_manifest.get("source_tree") != source_manifest.get("source_tree"):
    raise RuntimeError("formal loader transport/source manifest join changed")

source_facts = {}
for fact in source_manifest.get("source_facts", []):
    relative = fact.get("relative_path") if type(fact) is dict else None
    if type(relative) is not str or not relative.endswith(".py") or relative in source_facts:
        raise RuntimeError("formal loader execution source fact changed")
    source_facts[relative] = fact
transport_only = {
    "scripts/v42_standard_2048_formal_transport_receiver.py",
    "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
}
allowed = set(source_facts) | transport_only
facts = {}
for fact in transport_manifest.get("transport_facts", []):
    relative = fact.get("relative_path") if type(fact) is dict else None
    if type(relative) is not str or relative.startswith("/") or ".." in relative.split("/") or relative in facts:
        raise RuntimeError("formal loader transport fact changed")
    if relative.endswith(".py") and relative in allowed:
        if type(fact.get("byte_count")) is not int or not 0 < fact["byte_count"] <= 4 * 1024**2 or type(fact.get("sha256")) is not str or type(fact.get("git_blob_oid")) is not str:
            raise RuntimeError("formal loader Python fact changed")
        facts[relative] = fact
for relative, fact in source_facts.items():
    if facts.get(relative) != fact:
        raise RuntimeError("formal loader source closure is not an exact transport subset")

cache = {}
def verified_source(relative):
    if relative in cache:
        return cache[relative]
    fact = facts[relative]
    raw = read_regular(os.path.join(source_root, relative), 4 * 1024**2, 0o444)
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if len(raw) != fact["byte_count"] or hashlib.sha256(raw).hexdigest() != fact["sha256"] or blob != fact["git_blob_oid"]:
        raise RuntimeError("formal loader manifested source changed: " + relative)
    cache[relative] = raw
    return raw

receiver_relative = os.path.relpath(path, source_root)
if receiver_relative != "scripts/v42_standard_2048_formal_transport_receiver.py" or receiver_relative not in facts:
    raise RuntimeError("formal receiver is absent from transport manifest")
raw = verified_source(receiver_relative)
if len(raw) != expected_count or hashlib.sha256(raw).hexdigest() != expected_sha:
    raise RuntimeError("formal receiver differs from plan artifact")

created_loaders = {}

class Loader:
    def __init__(self, fullname, relative, package):
        self.fullname = fullname
        self.relative = relative
        self.package = package
        self.origin = os.path.join(source_root, relative)
        self.exec_count = 0
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        if self.exec_count != 0:
            raise RuntimeError("formal verified module executed more than once")
        self.exec_count = 1
        namespace = vars(module)
        namespace["__file__"] = self.origin
        namespace["__cached__"] = None
        source = verified_source(self.relative)
        exec(compile(source, self.origin, "exec", dont_inherit=True), namespace, namespace)

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
            raise ImportError("unmanifested repository module: " + fullname)
        loader = Loader(fullname, relative, package)
        if fullname in created_loaders:
            raise ImportError("formal verified module loader repeated: " + fullname)
        created_loaders[fullname] = loader
        spec = importlib.machinery.ModuleSpec(fullname, loader, origin=loader.origin, is_package=package)
        if package:
            spec.submodule_search_locations = [os.path.dirname(loader.origin)]
        return spec

if any(name == "acfqp" or name.startswith("acfqp.") or name == "scripts" or name.startswith("scripts.") for name in sys.modules):
    raise RuntimeError("repository module loaded before formal verified importer")
sys.dont_write_bytecode = True
sys.meta_path.insert(0, Finder())
sys.argv = [path, *receiver_arguments]
namespace = {"__name__": "_acfqp_verified_formal_receiver", "__file__": path, "__package__": None, "__cached__": None}
exec(compile(raw, path, "exec", dont_inherit=True), namespace, namespace)
expected_loaded = {
    "acfqp": "src/acfqp/__init__.py",
    "acfqp.artifacts": "src/acfqp/artifacts.py",
    "acfqp.build_coverage": "src/acfqp/build_coverage.py",
    "acfqp.construction_k7_domain_registry_extension_v42": "src/acfqp/construction_k7_domain_registry_extension_v42.py",
    "acfqp.construction_k7_standard_2048_formal_transport_v42r1": "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
    "acfqp.construction_k7_standard_2048_fresh_terminal_preregistration_v42": "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
    "acfqp.construction_k7_standard_2048_history_manifest_v42": "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
    "acfqp.construction_k7_standard_2048_materialization_transport_v42r1": "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
    "acfqp.construction_k7_standard_2048_process_supervision_v42r1": "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
    "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1": "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
    "acfqp.core": "src/acfqp/core.py",
    "acfqp.enumeration": "src/acfqp/enumeration.py",
    "acfqp.phase3e_ids": "src/acfqp/phase3e_ids.py",
    "scripts": "scripts/__init__.py",
    "scripts.publish_v42_preformal_upload_journal": "scripts/publish_v42_preformal_upload_journal.py",
    "scripts.run_v42_preformal_upload_sender": "scripts/run_v42_preformal_upload_sender.py",
    "scripts.run_v42_standard_2048_remote_ordinal2": "scripts/run_v42_standard_2048_remote_ordinal2.py",
}
actual_loaded = {}
for name, module in sys.modules.items():
    file_name = getattr(module, "__file__", None)
    if type(file_name) is str and file_name.startswith(source_root + "/"):
        actual_loaded[name] = os.path.relpath(file_name, source_root)
if actual_loaded != expected_loaded or set(created_loaders) != set(expected_loaded):
    raise RuntimeError("formal receiver loaded repository module inventory changed")
for name, relative in expected_loaded.items():
    module = sys.modules[name]
    loader = created_loaders[name]
    if not (getattr(module, "__loader__", None) is loader and getattr(getattr(module, "__spec__", None), "origin", None) == os.path.join(source_root, relative) and getattr(module, "__cached__", None) is None and loader.exec_count == 1):
        raise RuntimeError("formal receiver module escaped verified source bytes")
entry = namespace.get("main")
if not callable(entry):
    raise RuntimeError("formal receiver verified entry point changed")
raise SystemExit(entry())
'''


class V42FormalTransportError(RuntimeError):
    """A formal transport authority, observation, or replay gate changed."""


ActivationTerminalValidator = Callable[[bytes], Mapping[str, Any]]


def _fail(message: str) -> NoReturn:
    raise V42FormalTransportError(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        (DOMAIN_PREFIX + domain).encode("ascii")
        + b"\0"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _canonical_document(
    value: bytes | Mapping[str, Any], label: str
) -> dict[str, Any]:
    if type(value) is bytes:
        try:
            result = loads_canonical_json(value)
        except (TypeError, ValueError, UnicodeError) as error:
            raise V42FormalTransportError(f"{label} is not canonical JSON") from error
        if canonical_json_bytes(result) != value:
            _fail(f"{label} bytes are not canonical")
    elif type(value) is dict:
        try:
            result = loads_canonical_json(canonical_json_bytes(value))
        except (TypeError, ValueError, UnicodeError) as error:
            raise V42FormalTransportError(f"{label} is not canonical JSON") from error
    else:
        _fail(f"{label} changed type")
    if type(result) is not dict:
        _fail(f"{label} is not an object")
    return result


def _hex(value: object, length: int, label: str) -> str:
    pattern = _HEX40 if length == 40 else _HEX64
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail(f"{label} is not lowercase hex{length}")
    return value


def _uuid(value: object, label: str) -> str:
    if type(value) is not str:
        _fail(f"{label} changed type")
    try:
        normalized = str(uuid.UUID(value))
    except (ValueError, AttributeError) as error:
        raise V42FormalTransportError(f"{label} is not a canonical UUID") from error
    if normalized != value:
        _fail(f"{label} is not a canonical UUID")
    return value


def _absolute(value: object, label: str) -> str:
    if type(value) is not str or "\0" in value:
        _fail(f"{label} changed type or contains NUL")
    path = PurePosixPath(value)
    if not path.is_absolute() or str(path) != value or ".." in path.parts:
        _fail(f"{label} is not canonical absolute POSIX path")
    return value


def _artifact(raw: bytes, relative_path: str, cap: int) -> dict[str, Any]:
    if type(raw) is not bytes or not 0 < len(raw) <= cap:
        _fail(f"{relative_path} bytes changed type, emptiness, or cap")
    if str(PurePosixPath(relative_path)) != relative_path or relative_path.startswith("/"):
        _fail("program artifact relative path changed")
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _tool_fact(value: object, expected_path: str, label: str) -> dict[str, Any]:
    fields = {"path", "sha256", "byte_count", "mode", "uid", "gid", "st_nlink"}
    if type(value) is not dict or set(value) != fields:
        _fail(f"{label} tool fact schema changed")
    if (
        _absolute(value.get("path"), f"{label} path") != expected_path
        or type(value.get("byte_count")) is not int
        or value["byte_count"] <= 0
        or type(value.get("mode")) is not int
        or value["mode"] != 0o755
        or value.get("uid") != 0
        or value.get("gid") != 0
        or value.get("st_nlink") != 1
    ):
        _fail(f"{label} tool identity changed")
    return {
        "path": expected_path,
        "sha256": _hex(value.get("sha256"), 64, f"{label} SHA256"),
        "byte_count": value["byte_count"],
        "mode": 0o755,
        "uid": 0,
        "gid": 0,
        "st_nlink": 1,
    }


def _activation_binding(value: object) -> dict[str, Any]:
    fields = {
        "protocol",
        "activation_terminal_id",
        "preactivation_resource_result_id",
        "source_commit",
        "source_tree",
        "source_manifest_id",
        "transport_manifest_id",
        "local_materialization_attempt_id",
        "remote_materialization_attempt_id",
        "materialization_terminal_id",
        "materialization_activation_final_evidence_index_id",
        "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified",
        "bootstrap_terminal_exact_shared_materialization_ids_verified",
        "bootstrap_launcher_consumed_activation_transport_terminal_id",
        "downstream_launcher_terminal_id_join_remains_defense_in_depth",
        "formal_evidence_bundle_complete_under_bounded_successor_claim",
        "same_uid_coordinated_replacement_of_named_activation_evidence_root_and_all_persistent_anchors_excluded_from_claim",
        "fixed_remote_root",
        "fixed_source_root",
        "remote_target_alias",
        "remote_hostname",
        "remote_user",
        "remote_uid",
        "kernel_boot_id",
        "linger_enabled",
        "linger_path",
        "user_manager_invocation_id",
        "user_manager_main_pid",
        "user_manager_control_group",
        "cgroup_contract_id",
        "remote_tool_facts",
        "fixed_root_publish_complete",
        "formal_prepare_authorized",
    }
    if type(value) is not dict or set(value) != fields:
        _fail("activation terminal adapter returned a nonexact binding")
    if (
        value.get("protocol") != ACTIVATION_TERMINAL_PROTOCOL
        or _hex(value.get("activation_terminal_id"), 64, "activation terminal ID")
        != value["activation_terminal_id"]
        or _hex(
            value.get("preactivation_resource_result_id"),
            64,
            "preactivation resource result ID",
        )
        != value["preactivation_resource_result_id"]
        or _hex(value.get("source_commit"), 40, "source commit")
        != value["source_commit"]
        or _hex(value.get("source_tree"), 40, "source tree")
        != value["source_tree"]
    ):
        _fail("activation terminal adapter identity changed")
    for field in (
        "source_manifest_id",
        "transport_manifest_id",
        "local_materialization_attempt_id",
        "remote_materialization_attempt_id",
        "materialization_terminal_id",
        "materialization_activation_final_evidence_index_id",
        "cgroup_contract_id",
    ):
        _hex(value.get(field), 64, field)
    if (
        _absolute(value.get("fixed_remote_root"), "fixed remote root")
        != str(authority.REMOTE_ROOT)
        or _absolute(value.get("fixed_source_root"), "fixed source root")
        != str(authority.REMOTE_SOURCE_ROOT)
        or value.get("remote_target_alias") != authority.REMOTE_HOST_ALIAS
        or value.get("remote_hostname") != authority.REMOTE_HOSTNAME
        or value.get("remote_user") != authority.REMOTE_USER
        or value.get("remote_uid") != authority.REMOTE_UID
        or value.get("linger_enabled") is not True
        or _absolute(value.get("linger_path"), "linger path")
        != f"/var/lib/systemd/linger/{authority.REMOTE_USER}"
        or type(value.get("user_manager_main_pid")) is not int
        or value["user_manager_main_pid"] <= 1
        or value.get("fixed_root_publish_complete") is not True
        or value.get("formal_prepare_authorized") is not True
        or value.get(
            "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified"
        ) is not True
        or value.get(
            "bootstrap_terminal_exact_shared_materialization_ids_verified"
        ) is not True
        or value.get(
            "bootstrap_launcher_consumed_activation_transport_terminal_id"
        ) is not False
        or value.get(
            "downstream_launcher_terminal_id_join_remains_defense_in_depth"
        ) is not True
        or value.get(
            "formal_evidence_bundle_complete_under_bounded_successor_claim"
        ) is not True
        or value.get(
            "same_uid_coordinated_replacement_of_named_activation_evidence_root_and_all_persistent_anchors_excluded_from_claim"
        ) is not True
    ):
        _fail("activation terminal adapter host or authorization changed")
    _uuid(value.get("kernel_boot_id"), "activation kernel boot ID")
    _uuid(
        value.get("user_manager_invocation_id"),
        "activation user-manager invocation ID",
    )
    control_group = value.get("user_manager_control_group")
    if (
        type(control_group) is not str
        or _CGROUP.fullmatch(control_group) is None
        or not control_group.startswith("/user.slice/")
    ):
        _fail("activation user-manager cgroup changed")
    tool_values = value.get("remote_tool_facts")
    if type(tool_values) is not dict or set(tool_values) != {
        "env", "python", "systemctl", "systemd_run"
    }:
        _fail("activation remote tool inventory changed")
    tools = {
        "env": _tool_fact(tool_values["env"], ENV, "env"),
        "python": _tool_fact(tool_values["python"], authority.REMOTE_PYTHON_REALPATH, "python"),
        "systemctl": _tool_fact(tool_values["systemctl"], SYSTEMCTL, "systemctl"),
        "systemd_run": _tool_fact(tool_values["systemd_run"], SYSTEMD_RUN, "systemd-run"),
    }
    return {**value, "remote_tool_facts": tools}


def validate_activation_terminal_protocol_v42r1(
    raw: bytes, *, validator: ActivationTerminalValidator
) -> dict[str, Any]:
    """Call the explicit activation adapter and normalize its exact result."""

    if type(raw) is not bytes or not 0 < len(raw) <= MAX_ACTIVATION_TERMINAL_BYTES:
        _fail("activation terminal bytes changed type, emptiness, or cap")
    if not callable(validator):
        _fail("activation terminal validator adapter is required")
    try:
        result = validator(raw)
    except V42FormalTransportError:
        raise
    except BaseException as error:
        raise V42FormalTransportError(
            "activation terminal validator adapter rejected the terminal"
        ) from error
    if type(result) is not dict:
        _fail("activation terminal validator adapter changed result type")
    return _activation_binding(result)


def build_production_activation_core_v42r1(
    *, activation_terminal_id: str, preactivation_resource_result_id: str,
    source_commit: str, source_tree: str, source_manifest_id: str,
    transport_manifest_id: str, local_materialization_attempt_id: str,
    remote_materialization_attempt_id: str, materialization_terminal_id: str,
    materialization_activation_final_evidence_index_id: str,
) -> dict[str, Any]:
    """Bind the fully verified activation/bootstrap chain before a host probe."""

    payload = {
        **_base(PRODUCTION_ACTIVATION_CORE_SCHEMA),
        "activation_terminal_id": _hex(
            activation_terminal_id, 64, "production activation terminal ID"
        ),
        "preactivation_resource_result_id": _hex(
            preactivation_resource_result_id, 64,
            "production preactivation resource result ID",
        ),
        "source_commit": _hex(source_commit, 40, "production source commit"),
        "source_tree": _hex(source_tree, 40, "production source tree"),
        "source_manifest_id": _hex(
            source_manifest_id, 64, "production source manifest ID"
        ),
        "transport_manifest_id": _hex(
            transport_manifest_id, 64, "production transport manifest ID"
        ),
        "local_materialization_attempt_id": _hex(
            local_materialization_attempt_id, 64,
            "production local materialization attempt ID",
        ),
        "remote_materialization_attempt_id": _hex(
            remote_materialization_attempt_id, 64,
            "production remote materialization attempt ID",
        ),
        "materialization_terminal_id": _hex(
            materialization_terminal_id, 64,
            "production bootstrap materialization terminal ID",
        ),
        "materialization_activation_final_evidence_index_id": _hex(
            materialization_activation_final_evidence_index_id, 64,
            "production activation final evidence index ID",
        ),
        "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified": True,
        "bootstrap_terminal_exact_shared_materialization_ids_verified": True,
        "bootstrap_launcher_consumed_activation_transport_terminal_id": False,
        "downstream_launcher_terminal_id_join_remains_defense_in_depth": True,
        "formal_evidence_bundle_complete_under_bounded_successor_claim": True,
        "same_uid_coordinated_replacement_of_named_activation_evidence_root_and_all_persistent_anchors_excluded_from_claim": True,
        "fixed_remote_root": str(authority.REMOTE_ROOT),
        "fixed_source_root": str(authority.REMOTE_SOURCE_ROOT),
        "remote_target_alias": authority.REMOTE_HOST_ALIAS,
        "remote_hostname": authority.REMOTE_HOSTNAME,
        "remote_user": authority.REMOTE_USER,
        "remote_uid": authority.REMOTE_UID,
        "fixed_root_publish_complete": True,
        "formal_prepare_authorized": True,
    }
    return {
        **payload,
        "production_activation_core_id": _content_id("activation-core", payload),
    }


def verify_production_activation_core_v42r1(
    raw_or_document: bytes | dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "production activation core")
    expected = build_production_activation_core_v42r1(
        activation_terminal_id=document.get("activation_terminal_id"),
        preactivation_resource_result_id=document.get(
            "preactivation_resource_result_id"
        ),
        source_commit=document.get("source_commit"),
        source_tree=document.get("source_tree"),
        source_manifest_id=document.get("source_manifest_id"),
        transport_manifest_id=document.get("transport_manifest_id"),
        local_materialization_attempt_id=document.get(
            "local_materialization_attempt_id"
        ),
        remote_materialization_attempt_id=document.get(
            "remote_materialization_attempt_id"
        ),
        materialization_terminal_id=document.get("materialization_terminal_id"),
        materialization_activation_final_evidence_index_id=document.get(
            "materialization_activation_final_evidence_index_id"
        ),
    )
    if document != expected:
        _fail("production activation core changed")
    return document


def build_formal_host_epoch_receipt_v42r1(
    *, activation_core: Mapping[str, Any], manager_binding: Mapping[str, Any],
    memory_limit_ancestry: Sequence[Mapping[str, Any]],
    remote_tool_facts: Mapping[str, Any],
) -> dict[str, Any]:
    core = verify_production_activation_core_v42r1(dict(activation_core))
    if type(manager_binding) is not dict:
        _fail("formal host epoch manager binding changed type")
    manager_fields = {
        "kernel_boot_id", "linger_enabled", "user_manager_invocation_id",
        "user_manager_main_pid", "user_manager_control_group",
        "cgroup_contract_id",
    }
    if set(manager_binding) != manager_fields:
        _fail("formal host epoch manager binding schema changed")
    boot = _uuid(manager_binding.get("kernel_boot_id"), "formal host boot ID")
    invocation = _uuid(
        manager_binding.get("user_manager_invocation_id"),
        "formal host user-manager invocation ID",
    )
    pid = manager_binding.get("user_manager_main_pid")
    control_group = manager_binding.get("user_manager_control_group")
    if (
        manager_binding.get("linger_enabled") is not True
        or type(pid) is not int
        or pid <= 1
        or type(control_group) is not str
        or _CGROUP.fullmatch(control_group) is None
        or not control_group.startswith("/user.slice/")
    ):
        _fail("formal host epoch manager observation changed")
    cgroup_contract = build_cgroup_contract_id_v42r1(
        manager_control_group=control_group,
        memory_limit_ancestry=memory_limit_ancestry,
    )
    if manager_binding.get("cgroup_contract_id") != cgroup_contract:
        _fail("formal host epoch cgroup contract join changed")
    if type(remote_tool_facts) is not dict or set(remote_tool_facts) != {
        "env", "python", "systemctl", "systemd_run"
    }:
        _fail("formal host epoch tool inventory changed")
    tools = {
        "env": _tool_fact(remote_tool_facts["env"], ENV, "host epoch env"),
        "python": _tool_fact(
            remote_tool_facts["python"], authority.REMOTE_PYTHON_REALPATH,
            "host epoch python",
        ),
        "systemctl": _tool_fact(
            remote_tool_facts["systemctl"], SYSTEMCTL, "host epoch systemctl"
        ),
        "systemd_run": _tool_fact(
            remote_tool_facts["systemd_run"], SYSTEMD_RUN,
            "host epoch systemd-run",
        ),
    }
    payload = {
        **_base(FORMAL_HOST_EPOCH_RECEIPT_SCHEMA),
        "production_activation_core_id": core["production_activation_core_id"],
        "activation_terminal_id": core["activation_terminal_id"],
        "materialization_terminal_id": core["materialization_terminal_id"],
        "materialization_activation_final_evidence_index_id": core[
            "materialization_activation_final_evidence_index_id"
        ],
        "same_uid_coordinated_replacement_of_named_activation_evidence_root_and_all_persistent_anchors_excluded_from_claim": core[
            "same_uid_coordinated_replacement_of_named_activation_evidence_root_and_all_persistent_anchors_excluded_from_claim"
        ],
        "source_manifest_id": core["source_manifest_id"],
        "transport_manifest_id": core["transport_manifest_id"],
        "kernel_boot_id": boot,
        "linger_enabled": True,
        "linger_path": f"/var/lib/systemd/linger/{authority.REMOTE_USER}",
        "user_manager_invocation_id": invocation,
        "user_manager_main_pid": pid,
        "user_manager_control_group": control_group,
        "memory_limit_ancestry": [dict(row) for row in memory_limit_ancestry],
        "cgroup_contract_id": cgroup_contract,
        "remote_tool_facts": tools,
        "observation_was_read_only": True,
        "remote_mutation_performed": False,
        "systemd_lifecycle_mutation_performed": False,
    }
    return {
        **payload,
        "formal_host_epoch_receipt_id": _content_id("host-epoch-receipt", payload),
    }


def verify_formal_host_epoch_receipt_v42r1(
    raw_or_document: bytes | dict[str, Any], *,
    activation_core: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "formal host epoch receipt")
    expected = build_formal_host_epoch_receipt_v42r1(
        activation_core=activation_core,
        manager_binding={
            key: document.get(key)
            for key in (
                "kernel_boot_id", "linger_enabled",
                "user_manager_invocation_id", "user_manager_main_pid",
                "user_manager_control_group", "cgroup_contract_id",
            )
        },
        memory_limit_ancestry=document.get("memory_limit_ancestry"),
        remote_tool_facts=document.get("remote_tool_facts"),
    )
    if document != expected:
        _fail("formal host epoch receipt changed")
    return document


def production_activation_binding_v42r1(
    *, activation_core: Mapping[str, Any], host_epoch_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    core = verify_production_activation_core_v42r1(dict(activation_core))
    epoch = verify_formal_host_epoch_receipt_v42r1(
        dict(host_epoch_receipt), activation_core=core
    )
    return _activation_binding(
        {
            "protocol": ACTIVATION_TERMINAL_PROTOCOL,
            "activation_terminal_id": core["activation_terminal_id"],
            "preactivation_resource_result_id": core[
                "preactivation_resource_result_id"
            ],
            "source_commit": core["source_commit"],
            "source_tree": core["source_tree"],
            "source_manifest_id": core["source_manifest_id"],
            "transport_manifest_id": core["transport_manifest_id"],
            "local_materialization_attempt_id": core[
                "local_materialization_attempt_id"
            ],
            "remote_materialization_attempt_id": core[
                "remote_materialization_attempt_id"
            ],
            "materialization_terminal_id": core["materialization_terminal_id"],
            "materialization_activation_final_evidence_index_id": core[
                "materialization_activation_final_evidence_index_id"
            ],
            "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified": core[
                "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified"
            ],
            "bootstrap_terminal_exact_shared_materialization_ids_verified": core[
                "bootstrap_terminal_exact_shared_materialization_ids_verified"
            ],
            "bootstrap_launcher_consumed_activation_transport_terminal_id": core[
                "bootstrap_launcher_consumed_activation_transport_terminal_id"
            ],
            "downstream_launcher_terminal_id_join_remains_defense_in_depth": core[
                "downstream_launcher_terminal_id_join_remains_defense_in_depth"
            ],
            "formal_evidence_bundle_complete_under_bounded_successor_claim": core[
                "formal_evidence_bundle_complete_under_bounded_successor_claim"
            ],
            "same_uid_coordinated_replacement_of_named_activation_evidence_root_and_all_persistent_anchors_excluded_from_claim": core[
                "same_uid_coordinated_replacement_of_named_activation_evidence_root_and_all_persistent_anchors_excluded_from_claim"
            ],
            "fixed_remote_root": core["fixed_remote_root"],
            "fixed_source_root": core["fixed_source_root"],
            "remote_target_alias": core["remote_target_alias"],
            "remote_hostname": core["remote_hostname"],
            "remote_user": core["remote_user"],
            "remote_uid": core["remote_uid"],
            "kernel_boot_id": epoch["kernel_boot_id"],
            "linger_enabled": epoch["linger_enabled"],
            "linger_path": epoch["linger_path"],
            "user_manager_invocation_id": epoch["user_manager_invocation_id"],
            "user_manager_main_pid": epoch["user_manager_main_pid"],
            "user_manager_control_group": epoch[
                "user_manager_control_group"
            ],
            "cgroup_contract_id": epoch["cgroup_contract_id"],
            "remote_tool_facts": epoch["remote_tool_facts"],
            "fixed_root_publish_complete": core["fixed_root_publish_complete"],
            "formal_prepare_authorized": core["formal_prepare_authorized"],
        }
    )


def _base(schema: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
    }


def _program_path(binding: Mapping[str, Any], relative: str) -> str:
    return str(PurePosixPath(binding["fixed_source_root"]) / relative)


def _remote_command(
    receiver_path: str, receiver_artifact: Mapping[str, Any], mode: str,
    plan_sentinel: str, source_manifest_id: str, transport_manifest_id: str,
) -> str:
    arguments = [
        REMOTE_PYTHON,
        "-I",
        "-S",
        "-B",
        "-c",
        VERIFIED_RECEIVER_LOADER_SOURCE,
        receiver_path,
        receiver_artifact["sha256"],
        str(receiver_artifact["byte_count"]),
        _hex(source_manifest_id, 64, "receiver loader source manifest ID"),
        _hex(transport_manifest_id, 64, "receiver loader transport manifest ID"),
        mode,
        "--formal-transport-plan-id",
        plan_sentinel,
    ]
    return "builtin exec -c " + " ".join(shlex.quote(part) for part in arguments)


def _ssh_argv(
    *, known_hosts_path: str, remote_command: str
) -> list[str]:
    return [
        preformal.LOCAL_SSH_EXECUTABLE,
        "-T",
        "-F",
        "/dev/null",
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
        f"-oUserKnownHostsFile={known_hosts_path}",
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
        "-i",
        preformal.LOCAL_IDENTITY_FILE,
        "-p",
        str(preformal.REMOTE_ENDPOINT_PORT),
        "-l",
        authority.REMOTE_USER,
        "--",
        preformal.REMOTE_ENDPOINT_HOST,
        remote_command,
    ]


def build_formal_transport_plan_v42r1(
    *,
    activation_terminal_raw: bytes,
    activation_terminal_validator: ActivationTerminalValidator,
    receiver_source_raw: bytes,
    driver_source_raw: bytes,
    formal_authority_source_raw: bytes,
    known_hosts_path: str | None = None,
) -> dict[str, Any]:
    binding = validate_activation_terminal_protocol_v42r1(
        activation_terminal_raw, validator=activation_terminal_validator
    )
    expected_known_hosts = str(LOCAL_FORMAL_JOURNAL_ROOT / LOCAL_KNOWN_HOSTS_NAME)
    known_hosts = expected_known_hosts if known_hosts_path is None else _absolute(
        known_hosts_path, "formal known-hosts"
    )
    if known_hosts != expected_known_hosts:
        _fail("formal known-hosts path is not the fixed absolute journal path")
    receiver = _artifact(receiver_source_raw, FORMAL_RECEIVER_RELATIVE, 4 * 1024**2)
    driver = _artifact(driver_source_raw, FORMAL_DRIVER_RELATIVE, 4 * 1024**2)
    formal_authority_artifact = _artifact(
        formal_authority_source_raw, FORMAL_AUTHORITY_RELATIVE, 4 * 1024**2
    )
    receiver_path = _program_path(binding, FORMAL_RECEIVER_RELATIVE)
    receiver_artifact = receiver
    sentinel = "{acfqp_v42_formal_transport_plan_id}"
    commands = {
        "prepare_once": _ssh_argv(
            known_hosts_path=known_hosts,
            remote_command=_remote_command(receiver_path, receiver, "--prepare-once", sentinel, binding["source_manifest_id"], binding["transport_manifest_id"]),
        ),
        "inspect_prepare": _ssh_argv(
            known_hosts_path=known_hosts,
            remote_command=_remote_command(receiver_path, receiver, "--inspect-prepare", sentinel, binding["source_manifest_id"], binding["transport_manifest_id"]),
        ),
        "admit_launch": _ssh_argv(
            known_hosts_path=known_hosts,
            remote_command=_remote_command(receiver_path, receiver, "--admit-launch", sentinel, binding["source_manifest_id"], binding["transport_manifest_id"]),
        ),
        "inspect_launch": _ssh_argv(
            known_hosts_path=known_hosts,
            remote_command=_remote_command(receiver_path, receiver, "--inspect-launch", sentinel, binding["source_manifest_id"], binding["transport_manifest_id"]),
        ),
    }
    payload = {
        **_base(FORMAL_TRANSPORT_PLAN_SCHEMA),
        "activation_terminal_fact": {
            "byte_count": len(activation_terminal_raw),
            "sha256": hashlib.sha256(activation_terminal_raw).hexdigest(),
        },
        "activation_binding": binding,
        "source_commit": binding["source_commit"],
        "source_tree": binding["source_tree"],
        "source_manifest_id": binding["source_manifest_id"],
        "transport_manifest_id": binding["transport_manifest_id"],
        "receiver_artifact": receiver,
        "driver_artifact": driver,
        "formal_authority_artifact": formal_authority_artifact,
        "local_journal_root": str(LOCAL_FORMAL_JOURNAL_ROOT),
        "remote_journal_root": str(REMOTE_FORMAL_JOURNAL_ROOT),
        "known_hosts_path": known_hosts,
        "ssh_client_contract": preformal._ssh_client_contract(known_hosts),  # noqa: SLF001
        "authorized_ssh_argv_templates": commands,
        "systemd_contract": {
            "unit_name_template": SYSTEMD_UNIT_PREFIX
            + "{acfqp_v42_local_launch_attempt_id}.service",
            "user": True,
            "service_type": "exec",
            "slice": SYSTEMD_SLICE,
            "restart": "no",
            "remain_after_exit": True,
            "success_exit_status": [0, 2],
            "umask": "0077",
            "kill_mode": "mixed",
            "timeout_stop_seconds": SYSTEMD_TIMEOUT_STOP_SECONDS,
            "runtime_max_seconds": SYSTEMD_RUNTIME_MAX_SECONDS,
            "standard_input": "null",
            "standard_output": "null",
            "standard_error": "null",
            "forbidden_options": sorted(FORBIDDEN_SYSTEMD_OPTIONS),
            "binds_to_ssh_session": False,
            "client_environment": dict(SYSTEMD_CLIENT_ENVIRONMENT),
            "service_environment": dict(FORMAL_SERVICE_ENVIRONMENT),
            "remote_tool_facts": binding["remote_tool_facts"],
        },
        "formal_runtime_is_independent_of_ssh_lifetime": True,
        "local_network_marker_precedes_each_ssh_effect": True,
        "same_effect_replay_forbidden_after_marker": True,
        "post_marker_progress_is_read_only_inspection_only": True,
        "unit_absence_never_proves_service_never_started": True,
        "activation_terminal_schema_is_owned_by_explicit_validator_adapter": True,
        "same_uid_coordinated_replacement_of_journal_root_and_sibling_anchor_is_excluded": True,
    }
    return {
        **payload,
        "formal_transport_plan_id": _content_id("plan", payload),
    }


def verify_formal_transport_plan_v42r1(
    raw_or_document: bytes | dict[str, Any],
    **build_arguments: Any,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "formal transport plan")
    expected = build_formal_transport_plan_v42r1(**build_arguments)
    if document != expected:
        _fail("formal transport plan changed")
    return document


def verify_self_contained_formal_transport_plan_v42r1(
    raw_or_document: bytes | dict[str, Any],
) -> dict[str, Any]:
    """Verify a transported plan without pretending to revalidate activation.

    The activation terminal itself remains owned by the explicit adapter used
    to build the plan.  This verifier checks the resulting normalized binding,
    every fixed local/remote path and executable contract, the four SSH
    templates, and the content ID.  Remote code additionally rejoins the
    normalized host epoch and fixed materialization live before mutation.
    """

    document = _canonical_document(raw_or_document, "transported formal plan")
    fields = {
        "schema", "schema_version", "formal_identity", "global_execution_ordinal",
        "activation_terminal_fact", "activation_binding", "source_commit",
        "source_tree", "source_manifest_id", "transport_manifest_id",
        "receiver_artifact", "driver_artifact", "formal_authority_artifact",
        "local_journal_root",
        "remote_journal_root", "known_hosts_path", "ssh_client_contract",
        "authorized_ssh_argv_templates", "systemd_contract",
        "formal_runtime_is_independent_of_ssh_lifetime",
        "local_network_marker_precedes_each_ssh_effect",
        "same_effect_replay_forbidden_after_marker",
        "post_marker_progress_is_read_only_inspection_only",
        "unit_absence_never_proves_service_never_started",
        "activation_terminal_schema_is_owned_by_explicit_validator_adapter",
        "same_uid_coordinated_replacement_of_journal_root_and_sibling_anchor_is_excluded",
        "formal_transport_plan_id",
    }
    if set(document) != fields:
        _fail("transported formal plan schema changed")
    identifier = document["formal_transport_plan_id"]
    payload = dict(document)
    del payload["formal_transport_plan_id"]
    if (
        document.get("schema") != FORMAL_TRANSPORT_PLAN_SCHEMA
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != authority.FORMAL_IDENTITY
        or document.get("global_execution_ordinal")
        != authority.GLOBAL_EXECUTION_ORDINAL
        or _hex(identifier, 64, "formal transport plan ID")
        != _content_id("plan", payload)
    ):
        _fail("transported formal plan identity changed")
    binding = _activation_binding(document["activation_binding"])
    terminal_fact = document["activation_terminal_fact"]
    if (
        type(terminal_fact) is not dict
        or set(terminal_fact) != {"byte_count", "sha256"}
        or type(terminal_fact.get("byte_count")) is not int
        or not 0 < terminal_fact["byte_count"] <= MAX_ACTIVATION_TERMINAL_BYTES
    ):
        _fail("transported activation terminal fact changed")
    _hex(terminal_fact.get("sha256"), 64, "activation terminal SHA256")
    if any(
        document[field] != binding[field]
        for field in (
            "source_commit", "source_tree", "source_manifest_id",
            "transport_manifest_id",
        )
    ):
        _fail("transported formal plan source join changed")
    for field, relative in (
        ("receiver_artifact", FORMAL_RECEIVER_RELATIVE),
        ("driver_artifact", FORMAL_DRIVER_RELATIVE),
        ("formal_authority_artifact", FORMAL_AUTHORITY_RELATIVE),
    ):
        artifact = document[field]
        if (
            type(artifact) is not dict
            or set(artifact) != {"relative_path", "byte_count", "sha256"}
            or artifact.get("relative_path") != relative
            or type(artifact.get("byte_count")) is not int
            or artifact["byte_count"] <= 0
        ):
            _fail(f"transported {field} changed")
        _hex(artifact.get("sha256"), 64, f"transported {field} SHA256")
    expected_known_hosts = str(LOCAL_FORMAL_JOURNAL_ROOT / LOCAL_KNOWN_HOSTS_NAME)
    if (
        document.get("local_journal_root") != str(LOCAL_FORMAL_JOURNAL_ROOT)
        or document.get("remote_journal_root") != str(REMOTE_FORMAL_JOURNAL_ROOT)
        or document.get("known_hosts_path") != expected_known_hosts
        or document.get("ssh_client_contract")
        != preformal._ssh_client_contract(expected_known_hosts)  # noqa: SLF001
    ):
        _fail("transported formal plan local or remote fixed path changed")
    sentinel = "{acfqp_v42_formal_transport_plan_id}"
    receiver_path = _program_path(binding, FORMAL_RECEIVER_RELATIVE)
    receiver_artifact = document["receiver_artifact"]
    expected_templates = {
        "prepare_once": _ssh_argv(
            known_hosts_path=expected_known_hosts,
            remote_command=_remote_command(receiver_path, receiver_artifact, "--prepare-once", sentinel, binding["source_manifest_id"], binding["transport_manifest_id"]),
        ),
        "inspect_prepare": _ssh_argv(
            known_hosts_path=expected_known_hosts,
            remote_command=_remote_command(receiver_path, receiver_artifact, "--inspect-prepare", sentinel, binding["source_manifest_id"], binding["transport_manifest_id"]),
        ),
        "admit_launch": _ssh_argv(
            known_hosts_path=expected_known_hosts,
            remote_command=_remote_command(receiver_path, receiver_artifact, "--admit-launch", sentinel, binding["source_manifest_id"], binding["transport_manifest_id"]),
        ),
        "inspect_launch": _ssh_argv(
            known_hosts_path=expected_known_hosts,
            remote_command=_remote_command(receiver_path, receiver_artifact, "--inspect-launch", sentinel, binding["source_manifest_id"], binding["transport_manifest_id"]),
        ),
    }
    if document.get("authorized_ssh_argv_templates") != expected_templates:
        _fail("transported formal SSH templates changed")
    expected_systemd = {
        "unit_name_template": SYSTEMD_UNIT_PREFIX
        + "{acfqp_v42_local_launch_attempt_id}.service",
        "user": True,
        "service_type": "exec",
        "slice": SYSTEMD_SLICE,
        "restart": "no",
        "remain_after_exit": True,
        "success_exit_status": [0, 2],
        "umask": "0077",
        "kill_mode": "mixed",
        "timeout_stop_seconds": SYSTEMD_TIMEOUT_STOP_SECONDS,
        "runtime_max_seconds": SYSTEMD_RUNTIME_MAX_SECONDS,
        "standard_input": "null",
        "standard_output": "null",
        "standard_error": "null",
        "forbidden_options": sorted(FORBIDDEN_SYSTEMD_OPTIONS),
        "binds_to_ssh_session": False,
        "client_environment": dict(SYSTEMD_CLIENT_ENVIRONMENT),
        "service_environment": dict(FORMAL_SERVICE_ENVIRONMENT),
        "remote_tool_facts": binding["remote_tool_facts"],
    }
    if document.get("systemd_contract") != expected_systemd or any(
        document.get(field) is not True
        for field in (
            "formal_runtime_is_independent_of_ssh_lifetime",
            "local_network_marker_precedes_each_ssh_effect",
            "same_effect_replay_forbidden_after_marker",
            "post_marker_progress_is_read_only_inspection_only",
            "unit_absence_never_proves_service_never_started",
            "activation_terminal_schema_is_owned_by_explicit_validator_adapter",
            "same_uid_coordinated_replacement_of_journal_root_and_sibling_anchor_is_excluded",
        )
    ):
        _fail("transported formal systemd or replay contract changed")
    return document


def build_cgroup_contract_id_v42r1(
    *, manager_control_group: str,
    memory_limit_ancestry: Sequence[Mapping[str, Any]],
) -> str:
    """Content-address the stable cgroup-v2 placement and memory ceilings."""

    if (
        type(manager_control_group) is not str
        or _CGROUP.fullmatch(manager_control_group) is None
        or not manager_control_group.startswith("/user.slice/")
        or type(memory_limit_ancestry) not in {list, tuple}
        or not memory_limit_ancestry
    ):
        _fail("cgroup contract inputs changed")
    normalized: list[dict[str, Any]] = []
    for row in memory_limit_ancestry:
        if type(row) is not dict or set(row) != {
            "cgroup_path", "memory_max_mode", "memory_max_bytes"
        }:
            _fail("cgroup limit ancestry row schema changed")
        path = row.get("cgroup_path")
        mode = row.get("memory_max_mode")
        maximum = row.get("memory_max_bytes")
        if type(path) is not str or _CGROUP.fullmatch(path) is None:
            _fail("cgroup limit ancestry path changed")
        if mode == "MAX":
            if maximum is not None:
                _fail("unlimited cgroup ceiling unexpectedly has bytes")
        elif mode == "FINITE":
            if type(maximum) is not int or maximum < authority.MINIMUM_MEMORY_TOTAL_BYTES:
                _fail("finite cgroup ceiling is mistyped or below the formal gate")
        else:
            _fail("cgroup memory ceiling mode changed")
        normalized.append(dict(row))
    if normalized[0]["cgroup_path"] != manager_control_group or normalized[-1]["cgroup_path"] != "/":
        _fail("cgroup limit ancestry does not span manager to root")
    payload = {
        "schema": "acfqp.v42_remote_ordinal2_formal_cgroup_contract.v42r1",
        "manager_control_group": manager_control_group,
        "memory_limit_ancestry": normalized,
    }
    return _content_id("cgroup-contract", payload)


def materialize_ssh_argv_v42r1(
    plan: Mapping[str, Any], operation: str
) -> tuple[str, ...]:
    if type(plan) is not dict or operation not in {
        "prepare_once", "inspect_prepare", "admit_launch", "inspect_launch"
    }:
        _fail("formal SSH operation changed")
    templates = plan.get("authorized_ssh_argv_templates")
    if type(templates) is not dict or set(templates) != {
        "prepare_once", "inspect_prepare", "admit_launch", "inspect_launch"
    }:
        _fail("formal SSH template inventory changed")
    template = templates[operation]
    if type(template) is not list or any(type(item) is not str for item in template):
        _fail("formal SSH template changed type")
    sentinel = "{acfqp_v42_formal_transport_plan_id}"
    result = tuple(
        item.replace(sentinel, plan["formal_transport_plan_id"])
        for item in template
    )
    if any("{acfqp_v42_" in item for item in result):
        _fail("formal SSH argv retained a sentinel")
    return result


def build_prepare_attempt_v42r1(plan: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        **_base(FORMAL_PREPARE_ATTEMPT_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "activation_terminal_id": plan["activation_binding"]["activation_terminal_id"],
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "remote_target_alias": authority.REMOTE_HOST_ALIAS,
        "operation": OPERATION_PREPARE,
        "network_effect_started": False,
        "same_effect_replay_forbidden_after_network_marker": True,
    }
    return {**payload, "formal_prepare_attempt_id": _content_id("prepare-attempt", payload)}


def verify_prepare_attempt_v42r1(
    value: bytes | dict[str, Any], *, plan: Mapping[str, Any]
) -> dict[str, Any]:
    document = _canonical_document(value, "formal prepare attempt")
    if document != build_prepare_attempt_v42r1(plan):
        _fail("formal prepare attempt changed")
    return document


def build_launch_transport_attempt_v42r1(
    *, plan: Mapping[str, Any], prepare_receipt: Mapping[str, Any],
    local_launch_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    local_id = _hex(
        local_launch_attempt.get("local_launch_attempt_id"), 64,
        "local launch attempt ID",
    )
    if (
        prepare_receipt.get("prepare_receipt_id")
        != local_launch_attempt.get("prepare_receipt_id")
        or prepare_receipt.get("source_commit") != plan["source_commit"]
        or prepare_receipt.get("source_tree") != plan["source_tree"]
        or prepare_receipt.get("source_manifest_id") != plan["source_manifest_id"]
        or prepare_receipt.get("transport_manifest_id") != plan["transport_manifest_id"]
        or local_launch_attempt.get("transport_target_alias") != authority.REMOTE_HOST_ALIAS
    ):
        _fail("formal launch transport predecessor join changed")
    payload = {
        **_base(FORMAL_LAUNCH_TRANSPORT_ATTEMPT_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "local_launch_attempt_id": local_id,
        "unit_name": unit_name_v42r1(local_id),
        "operation": OPERATION_LAUNCH,
        "network_effect_started": False,
        "systemd_admission_effect_started": False,
        "same_effect_replay_forbidden_after_network_marker": True,
        "formal_execution_performed": False,
    }
    return {
        **payload,
        "formal_launch_transport_attempt_id": _content_id(
            "launch-transport-attempt", payload
        ),
    }


def unit_name_v42r1(local_launch_attempt_id: str) -> str:
    return SYSTEMD_UNIT_PREFIX + _hex(
        local_launch_attempt_id, 64, "local launch attempt ID"
    ) + ".service"


def _receiver_python_argv(
    *, plan: Mapping[str, Any], mode: str, attempt_id: str,
    runtime_invocation_id: str | None = None,
    runtime_control_group: str | None = None,
) -> tuple[str, ...]:
    binding = plan["activation_binding"]
    result = (
        REMOTE_PYTHON, "-I", "-S", "-B", "-c",
        VERIFIED_RECEIVER_LOADER_SOURCE,
        _program_path(binding, FORMAL_RECEIVER_RELATIVE),
        plan["receiver_artifact"]["sha256"],
        str(plan["receiver_artifact"]["byte_count"]),
        plan["source_manifest_id"],
        plan["transport_manifest_id"],
        mode, "--formal-transport-plan-id", plan["formal_transport_plan_id"],
        "--local-launch-attempt-id", attempt_id,
    )
    if mode == "--formal-launch-service-bootstrap":
        if runtime_invocation_id is not None or runtime_control_group is not None:
            _fail("service bootstrap unexpectedly received runtime identity args")
        return result
    if mode != "--formal-launch-service-wrapper":
        _fail("formal service receiver mode changed")
    invocation = _uuid(runtime_invocation_id, "clean wrapper runtime invocation ID")
    if (
        type(runtime_control_group) is not str
        or _CGROUP.fullmatch(runtime_control_group) is None
    ):
        _fail("clean wrapper runtime cgroup changed")
    return (
        *result,
        "--runtime-invocation-id", invocation,
        "--runtime-control-group", runtime_control_group,
    )


def build_systemd_run_argv_v42r1(
    *, plan: Mapping[str, Any], local_launch_attempt: Mapping[str, Any]
) -> tuple[str, ...]:
    attempt_id = _hex(
        local_launch_attempt.get("local_launch_attempt_id"), 64,
        "local launch attempt ID",
    )
    binding = plan["activation_binding"]
    tools = binding["remote_tool_facts"]
    bootstrap_argv = _receiver_python_argv(
        plan=plan, mode="--formal-launch-service-bootstrap",
        attempt_id=attempt_id,
    )
    argv = (
        tools["systemd_run"]["path"],
        "--user",
        "--quiet",
        "--no-ask-password",
        "--service-type=exec",
        "--unit=" + unit_name_v42r1(attempt_id),
        "--slice=" + SYSTEMD_SLICE,
        "--property=Restart=no",
        "--property=RemainAfterExit=yes",
        "--property=SuccessExitStatus=2",
        "--property=UMask=0077",
        "--property=KillMode=mixed",
        f"--property=TimeoutStopSec={SYSTEMD_TIMEOUT_STOP_SECONDS}s",
        f"--property=RuntimeMaxSec={SYSTEMD_RUNTIME_MAX_SECONDS}s",
        "--property=StandardInput=null",
        "--property=StandardOutput=null",
        "--property=StandardError=null",
        "--working-directory=" + binding["fixed_source_root"],
        "--",
        *bootstrap_argv,
    )
    validate_systemd_run_argv_v42r1(
        argv, plan=plan, local_launch_attempt=local_launch_attempt
    )
    return argv


def validate_systemd_run_argv_v42r1(
    value: Sequence[str], *, plan: Mapping[str, Any],
    local_launch_attempt: Mapping[str, Any],
) -> tuple[str, ...]:
    if type(value) not in {list, tuple} or any(type(item) is not str for item in value):
        _fail("systemd-run argv changed type")
    actual = tuple(value)
    for forbidden in FORBIDDEN_SYSTEMD_OPTIONS:
        if forbidden in actual:
            _fail(f"formal launch lifecycle-coupled option is forbidden: {forbidden}")
    if any(item.startswith("--property=BindsTo=") for item in actual):
        _fail("formal launch service must not bind to the SSH session")
    attempt_id = _hex(
        local_launch_attempt.get("local_launch_attempt_id"), 64,
        "local launch attempt ID",
    )
    binding = plan["activation_binding"]
    tools = binding["remote_tool_facts"]
    bootstrap_argv = _receiver_python_argv(
        plan=plan, mode="--formal-launch-service-bootstrap",
        attempt_id=attempt_id,
    )
    expected = (
        tools["systemd_run"]["path"], "--user", "--quiet",
        "--no-ask-password", "--service-type=exec",
        "--unit=" + unit_name_v42r1(attempt_id),
        "--slice=" + SYSTEMD_SLICE,
        "--property=Restart=no", "--property=RemainAfterExit=yes",
        "--property=SuccessExitStatus=2", "--property=UMask=0077",
        "--property=KillMode=mixed",
        f"--property=TimeoutStopSec={SYSTEMD_TIMEOUT_STOP_SECONDS}s",
        f"--property=RuntimeMaxSec={SYSTEMD_RUNTIME_MAX_SECONDS}s",
        "--property=StandardInput=null", "--property=StandardOutput=null",
        "--property=StandardError=null",
        "--working-directory=" + binding["fixed_source_root"], "--",
        *bootstrap_argv,
    )
    if actual != expected:
        _fail("systemd-run argv or service environment changed")
    return actual


def build_network_start_v42r1(
    *, plan: Mapping[str, Any], operation: str, attempt_id: str
) -> dict[str, Any]:
    if operation not in OPERATIONS:
        _fail("formal network-start operation changed")
    _hex(attempt_id, 64, "formal network-start attempt ID")
    payload = {
        **_base(FORMAL_NETWORK_START_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "operation": operation,
        "attempt_id": attempt_id,
        "network_effect_may_have_started": True,
        "published_o_excl_nofollow_mode_0400_and_fsynced_before_ssh": True,
        "same_effect_replay_forbidden": True,
        "only_read_only_inspection_allowed_after_publication": True,
    }
    return {**payload, "formal_network_start_id": _content_id("network-start", payload)}


def build_operation_outcome_v42r1(
    *, plan: Mapping[str, Any], operation: str, attempt_id: str,
    outcome_class: str, receipt_raw: bytes | None,
) -> dict[str, Any]:
    if operation not in OPERATIONS or outcome_class not in OUTCOME_CLASSES:
        _fail("formal operation outcome class changed")
    _hex(attempt_id, 64, "formal operation attempt ID")
    if outcome_class == OUTCOME_COMPLETE_EXACT_RECEIPT:
        if type(receipt_raw) is not bytes or not receipt_raw:
            _fail("complete formal operation omitted its exact receipt")
        receipt_fact: dict[str, Any] | None = {
            "byte_count": len(receipt_raw),
            "sha256": hashlib.sha256(receipt_raw).hexdigest(),
        }
    elif receipt_raw is not None:
        _fail("noncomplete formal operation cannot claim a receipt")
    else:
        receipt_fact = None
    marker_present = outcome_class != OUTCOME_PRE_NETWORK_FAILURE
    payload = {
        **_base(FORMAL_OPERATION_OUTCOME_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "operation": operation,
        "attempt_id": attempt_id,
        "outcome_class": outcome_class,
        "network_start_marker_present": marker_present,
        "receipt_fact": receipt_fact,
        "same_effect_replay_allowed": not marker_present,
        "only_read_only_inspection_allowed": marker_present,
    }
    return {**payload, "formal_operation_outcome_id": _content_id("outcome", payload)}


def verify_operation_outcome_self_contained_v42r1(
    raw_or_document: bytes | dict[str, Any], *, plan: Mapping[str, Any],
    operation: str, attempt_id: str,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "formal operation outcome")
    identifier = document.get("formal_operation_outcome_id")
    if type(identifier) is not str:
        _fail("formal operation outcome omitted its ID")
    payload = dict(document)
    del payload["formal_operation_outcome_id"]
    if (
        document.get("schema") != FORMAL_OPERATION_OUTCOME_SCHEMA
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != authority.FORMAL_IDENTITY
        or document.get("global_execution_ordinal")
        != authority.GLOBAL_EXECUTION_ORDINAL
        or document.get("formal_transport_plan_id")
        != plan["formal_transport_plan_id"]
        or document.get("operation") != operation
        or document.get("attempt_id") != attempt_id
        or document.get("outcome_class") not in OUTCOME_CLASSES
        or type(document.get("network_start_marker_present")) is not bool
        or type(document.get("same_effect_replay_allowed")) is not bool
        or type(document.get("only_read_only_inspection_allowed")) is not bool
        or _hex(identifier, 64, "formal operation outcome ID")
        != _content_id("outcome", payload)
    ):
        _fail("formal operation outcome changed")
    marker = document["outcome_class"] != OUTCOME_PRE_NETWORK_FAILURE
    fact = document.get("receipt_fact")
    if document["outcome_class"] == OUTCOME_COMPLETE_EXACT_RECEIPT:
        if (
            type(fact) is not dict
            or set(fact) != {"byte_count", "sha256"}
            or type(fact.get("byte_count")) is not int
            or fact["byte_count"] <= 0
        ):
            _fail("complete formal outcome receipt fact changed")
        _hex(fact.get("sha256"), 64, "formal outcome receipt SHA256")
    elif fact is not None:
        _fail("noncomplete formal outcome invented a receipt fact")
    if (
        document["network_start_marker_present"] is not marker
        or document["same_effect_replay_allowed"] is marker
        or document["only_read_only_inspection_allowed"] is not marker
    ):
        _fail("formal operation outcome replay semantics changed")
    return document


def _manager_binding(value: object, plan: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "kernel_boot_id", "linger_enabled", "user_manager_invocation_id",
        "user_manager_main_pid", "user_manager_control_group", "cgroup_contract_id",
    }
    if type(value) is not dict or set(value) != fields:
        _fail("live user-manager binding schema changed")
    activation = plan["activation_binding"]
    normalized = {
        "kernel_boot_id": _uuid(value.get("kernel_boot_id"), "live kernel boot ID"),
        "linger_enabled": value.get("linger_enabled"),
        "user_manager_invocation_id": _uuid(
            value.get("user_manager_invocation_id"),
            "live user-manager invocation ID",
        ),
        "user_manager_main_pid": value.get("user_manager_main_pid"),
        "user_manager_control_group": value.get("user_manager_control_group"),
        "cgroup_contract_id": _hex(
            value.get("cgroup_contract_id"), 64, "live cgroup contract ID"
        ),
    }
    if (
        normalized["linger_enabled"] is not True
        or type(normalized["user_manager_main_pid"]) is not int
        or normalized["user_manager_main_pid"] <= 1
        or type(normalized["user_manager_control_group"]) is not str
        or _CGROUP.fullmatch(normalized["user_manager_control_group"]) is None
    ):
        _fail("live user-manager binding changed semantics")
    normalized["matches_activation"] = all(
        normalized[field] == activation[field]
        for field in fields
    )
    return normalized


def _unit_observation(value: object, expected_unit: str) -> dict[str, Any]:
    fields = {
        "Id", "LoadState", "ActiveState", "SubState", "Result",
        "InvocationID", "MainPID", "ControlGroup", "Type", "Restart",
        "RemainAfterExit", "SuccessExitStatus", "UMask", "KillMode",
        "TimeoutStopUSec", "RuntimeMaxUSec", "StandardInput",
        "StandardOutput", "StandardError", "WorkingDirectory", "Slice",
        "FragmentPath", "LiveMainPIDArgv", "LiveMainPIDArgvSource",
        "Environment",
    }
    if type(value) is not dict or set(value) != fields:
        _fail("systemd unit observation schema changed")
    if (
        value.get("Id") != expected_unit
        or value.get("LoadState") not in UNIT_LOAD_STATES
        or value.get("ActiveState") not in UNIT_ACTIVE_STATES
        or value.get("SubState") not in UNIT_SUB_STATES
        or type(value.get("Result")) is not str
        or type(value.get("MainPID")) is not int
        or value["MainPID"] < 0
        or type(value.get("LiveMainPIDArgv")) is not list
        or any(type(item) is not str for item in value["LiveMainPIDArgv"])
        or value.get("LiveMainPIDArgvSource") not in {
            "PROC_MAINPID_CMDLINE", "UNAVAILABLE_NO_MAINPID", "ABSENT_UNIT"
        }
        or type(value.get("Environment")) is not str
    ):
        _fail("systemd unit state changed type or vocabulary")
    if value["LoadState"] == "loaded":
        if value["InvocationID"]:
            _uuid(value["InvocationID"], "unit invocation ID")
        if (
            value.get("Type") != "exec"
            or value.get("Restart") != "no"
            or value.get("RemainAfterExit") != "yes"
            or value.get("SuccessExitStatus") != "2"
            or value.get("UMask") != "0077"
            or value.get("KillMode") != "mixed"
            or value.get("TimeoutStopUSec") != "30s"
            or value.get("RuntimeMaxUSec") != "1w 25min"
            or value.get("StandardInput") != "null"
            or value.get("StandardOutput") != "null"
            or value.get("StandardError") != "null"
            or value.get("WorkingDirectory") != str(authority.REMOTE_SOURCE_ROOT)
            or value.get("Slice") != SYSTEMD_SLICE
            or value.get("FragmentPath")
            != (
                f"/run/user/{authority.REMOTE_UID}/systemd/transient/"
                + expected_unit
            )
            or value.get("Environment") != ""
        ):
            _fail("loaded systemd unit properties differ from authority")
        if value["MainPID"] > 1:
            if value["LiveMainPIDArgvSource"] != "PROC_MAINPID_CMDLINE":
                _fail("live unit argv was not read from its rejoined MainPID")
        elif (
            value["LiveMainPIDArgv"]
            or value["LiveMainPIDArgvSource"] != "UNAVAILABLE_NO_MAINPID"
        ):
            _fail("exited unit invented an ExecStart argv")
    elif (
        value["LiveMainPIDArgv"]
        or value["LiveMainPIDArgvSource"] != "ABSENT_UNIT"
        or value.get("FragmentPath") != ""
    ):
        _fail("absent unit invented an ExecStart argv or fragment")
    return dict(value)


def build_launch_admission_receipt_v42r1(
    *, plan: Mapping[str, Any], launch_transport_attempt: Mapping[str, Any],
    manager_binding: dict[str, Any], unit_observation: dict[str, Any],
    systemd_run_argv: Sequence[str],
) -> dict[str, Any]:
    local_id = launch_transport_attempt["local_launch_attempt_id"]
    unit = unit_name_v42r1(local_id)
    manager = _manager_binding(manager_binding, plan)
    observed_unit = _unit_observation(unit_observation, unit)
    configured_exec = list(
        build_systemd_run_argv_v42r1(
            plan=plan,
            local_launch_attempt={"local_launch_attempt_id": local_id},
        )[
            build_systemd_run_argv_v42r1(
                plan=plan,
                local_launch_attempt={"local_launch_attempt_id": local_id},
            ).index("--")
            + 1 :
        ]
    )
    expected_live_argv = list(
        _receiver_python_argv(
            plan=plan, mode="--formal-launch-service-wrapper",
            attempt_id=local_id,
            runtime_invocation_id=observed_unit["InvocationID"],
            runtime_control_group=observed_unit["ControlGroup"],
        )
    )
    if (
        manager["matches_activation"] is not True
        or observed_unit["LoadState"] != "loaded"
        or observed_unit["ActiveState"] not in {"active", "activating"}
        or not observed_unit["InvocationID"]
        or observed_unit["MainPID"] <= 1
        or not observed_unit["ControlGroup"].endswith("/" + unit)
        or observed_unit["LiveMainPIDArgv"] != expected_live_argv
    ):
        _fail("systemd admission did not produce an exact durable unit identity")
    # Local launch attempt is not needed to recompute argv here: the receiver
    # has already verified it.  Bind the exact argv bytes in the receipt.
    if type(systemd_run_argv) not in {list, tuple} or any(
        type(item) is not str for item in systemd_run_argv
    ):
        _fail("admission systemd-run argv changed type")
    argv = list(systemd_run_argv)
    validate_systemd_run_argv_v42r1(
        argv,
        plan=plan,
        local_launch_attempt={"local_launch_attempt_id": local_id},
    )
    payload = {
        **_base(FORMAL_LAUNCH_ADMISSION_RECEIPT_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "formal_launch_transport_attempt_id": launch_transport_attempt[
            "formal_launch_transport_attempt_id"
        ],
        "prepare_receipt_id": launch_transport_attempt["prepare_receipt_id"],
        "local_launch_attempt_id": local_id,
        "unit_name": unit,
        "unit_invocation_id": observed_unit["InvocationID"],
        "unit_main_pid": observed_unit["MainPID"],
        "unit_control_group": observed_unit["ControlGroup"],
        "kernel_boot_id": manager["kernel_boot_id"],
        "user_manager_invocation_id": manager["user_manager_invocation_id"],
        "user_manager_main_pid": manager["user_manager_main_pid"],
        "user_manager_control_group": manager["user_manager_control_group"],
        "cgroup_contract_id": manager["cgroup_contract_id"],
        "systemd_run_argv": argv,
        "systemd_run_argv_sha256": hashlib.sha256(
            canonical_json_bytes(argv)
        ).hexdigest(),
        "systemd_client_environment": dict(SYSTEMD_CLIENT_ENVIRONMENT),
        "formal_service_environment": dict(FORMAL_SERVICE_ENVIRONMENT),
        "configured_exec_start_argv": configured_exec,
        "live_post_env_main_pid_argv": expected_live_argv,
        "remote_tool_facts": plan["activation_binding"]["remote_tool_facts"],
        "systemd_admission_returncode": 0,
        "service_lifetime_is_independent_of_ssh": True,
        "same_admission_retry_forbidden": True,
        "formal_execution_result_not_claimed": True,
    }
    return {
        **payload,
        "formal_launch_admission_receipt_id": _content_id(
            "launch-admission-receipt", payload
        ),
    }


def verify_launch_admission_receipt_self_contained_v42r1(
    raw_or_document: bytes | dict[str, Any], *, plan: Mapping[str, Any],
    launch_transport_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(
        raw_or_document, "formal launch admission receipt"
    )
    identifier = document.get("formal_launch_admission_receipt_id")
    if type(identifier) is not str:
        _fail("formal launch admission receipt omitted its ID")
    payload = dict(document)
    del payload["formal_launch_admission_receipt_id"]
    local_id = launch_transport_attempt["local_launch_attempt_id"]
    expected_argv = list(
        build_systemd_run_argv_v42r1(
            plan=plan,
            local_launch_attempt={"local_launch_attempt_id": local_id},
        )
    )
    expected_configured_exec = expected_argv[expected_argv.index("--") + 1 :]
    expected_live_argv = list(
        _receiver_python_argv(
            plan=plan, mode="--formal-launch-service-wrapper",
            attempt_id=local_id,
            runtime_invocation_id=document.get("unit_invocation_id"),
            runtime_control_group=document.get("unit_control_group"),
        )
    )
    activation = plan["activation_binding"]
    if (
        document.get("schema") != FORMAL_LAUNCH_ADMISSION_RECEIPT_SCHEMA
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_transport_plan_id")
        != plan["formal_transport_plan_id"]
        or document.get("formal_launch_transport_attempt_id")
        != launch_transport_attempt["formal_launch_transport_attempt_id"]
        or document.get("prepare_receipt_id")
        != launch_transport_attempt["prepare_receipt_id"]
        or document.get("local_launch_attempt_id") != local_id
        or document.get("unit_name") != unit_name_v42r1(local_id)
        or type(document.get("unit_main_pid")) is not int
        or document["unit_main_pid"] <= 1
        or type(document.get("unit_control_group")) is not str
        or not document["unit_control_group"].endswith(
            "/" + unit_name_v42r1(local_id)
        )
        or document.get("kernel_boot_id") != activation["kernel_boot_id"]
        or document.get("user_manager_invocation_id")
        != activation["user_manager_invocation_id"]
        or document.get("user_manager_main_pid")
        != activation["user_manager_main_pid"]
        or document.get("user_manager_control_group")
        != activation["user_manager_control_group"]
        or document.get("cgroup_contract_id") != activation["cgroup_contract_id"]
        or document.get("systemd_run_argv") != expected_argv
        or document.get("systemd_run_argv_sha256")
        != hashlib.sha256(canonical_json_bytes(expected_argv)).hexdigest()
        or document.get("systemd_client_environment")
        != SYSTEMD_CLIENT_ENVIRONMENT
        or document.get("formal_service_environment")
        != FORMAL_SERVICE_ENVIRONMENT
        or document.get("configured_exec_start_argv")
        != expected_configured_exec
        or document.get("live_post_env_main_pid_argv") != expected_live_argv
        or document.get("remote_tool_facts") != activation["remote_tool_facts"]
        or document.get("systemd_admission_returncode") != 0
        or document.get("service_lifetime_is_independent_of_ssh") is not True
        or document.get("same_admission_retry_forbidden") is not True
        or document.get("formal_execution_result_not_claimed") is not True
        or _uuid(document.get("unit_invocation_id"), "receipt unit invocation ID")
        != document["unit_invocation_id"]
        or _hex(identifier, 64, "formal launch admission receipt ID")
        != _content_id("launch-admission-receipt", payload)
    ):
        _fail("formal launch admission receipt changed")
    return document


def build_service_wrapper_attestation_v42r1(
    *, plan: Mapping[str, Any], launch_transport_attempt: Mapping[str, Any],
    manager_binding: dict[str, Any], unit_observation: dict[str, Any],
    service_pid: int, service_cgroup: str,
    service_environment: Mapping[str, str], stdio_facts: Sequence[Mapping[str, Any]],
    live_file_descriptors: Sequence[int], live_tool_facts: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the checks performed inside the detached Type=exec service."""

    manager = _manager_binding(manager_binding, plan)
    local_id = launch_transport_attempt["local_launch_attempt_id"]
    unit = unit_name_v42r1(local_id)
    observed_unit = _unit_observation(unit_observation, unit)
    invocation = _uuid(
        observed_unit["InvocationID"], "wrapper unit invocation ID"
    )
    systemd_argv = build_systemd_run_argv_v42r1(
        plan=plan,
        local_launch_attempt={"local_launch_attempt_id": local_id},
    )
    configured_exec = list(systemd_argv[systemd_argv.index("--") + 1 :])
    expected_live_argv = list(
        _receiver_python_argv(
            plan=plan, mode="--formal-launch-service-wrapper",
            attempt_id=local_id,
            runtime_invocation_id=observed_unit["InvocationID"],
            runtime_control_group=observed_unit["ControlGroup"],
        )
    )
    if (
        manager["matches_activation"] is not True
        or type(service_pid) is not int
        or service_pid <= 1
        or type(service_cgroup) is not str
        or _CGROUP.fullmatch(service_cgroup) is None
        or not service_cgroup.endswith("/" + unit)
        or not service_cgroup.startswith(manager["user_manager_control_group"] + "/")
        or observed_unit["LoadState"] != "loaded"
        or observed_unit["ActiveState"] != "active"
        or observed_unit["SubState"] not in {"start", "running"}
        or observed_unit["MainPID"] != service_pid
        or observed_unit["ControlGroup"] != service_cgroup
        or observed_unit["LiveMainPIDArgv"] != expected_live_argv
    ):
        _fail("service wrapper process, cgroup, or manager epoch changed")
    # ``env -i`` is the service's first executable, so the scientific Python
    # process receives only this exact environment.  InvocationID/MainPID are
    # rejoined independently through systemctl and the invocation symlink;
    # they are not smuggled through mutable inherited environment variables.
    expected_environment = dict(FORMAL_SERVICE_ENVIRONMENT)
    if type(service_environment) is not dict or dict(service_environment) != expected_environment:
        _fail("formal service wrapper environment is not exact")
    if (
        type(live_tool_facts) is not dict
        or dict(live_tool_facts)
        != plan["activation_binding"]["remote_tool_facts"]
    ):
        _fail("formal service wrapper live tool facts changed")
    if type(stdio_facts) not in {list, tuple} or len(stdio_facts) != 3:
        _fail("formal service wrapper stdio inventory changed")
    if type(live_file_descriptors) not in {list, tuple} or list(live_file_descriptors) != [0, 1, 2]:
        _fail("formal service wrapper inherited an extra file descriptor")
    normalized_stdio: list[dict[str, Any]] = []
    for descriptor, fact in enumerate(stdio_facts):
        if type(fact) is not dict or set(fact) != {
            "descriptor", "target", "node_type", "isatty"
        }:
            _fail("formal service wrapper stdio fact schema changed")
        if fact != {
            "descriptor": descriptor,
            "target": "/dev/null",
            "node_type": "CHARACTER_DEVICE",
            "isatty": False,
        }:
            _fail("formal service wrapper stdio is not exact /dev/null")
        normalized_stdio.append(dict(fact))
    payload = {
        **_base(FORMAL_SERVICE_WRAPPER_ATTESTATION_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "formal_launch_transport_attempt_id": launch_transport_attempt[
            "formal_launch_transport_attempt_id"
        ],
        "prepare_receipt_id": launch_transport_attempt["prepare_receipt_id"],
        "local_launch_attempt_id": local_id,
        "unit_name": unit,
        "unit_invocation_id": invocation,
        "service_pid": service_pid,
        "service_cgroup": service_cgroup,
        "systemd_unit_observation": observed_unit,
        "configured_exec_start_argv": configured_exec,
        "live_post_env_main_pid_argv": expected_live_argv,
        "kernel_boot_id": manager["kernel_boot_id"],
        "user_manager_invocation_id": manager["user_manager_invocation_id"],
        "user_manager_main_pid": manager["user_manager_main_pid"],
        "user_manager_control_group": manager["user_manager_control_group"],
        "cgroup_contract_id": manager["cgroup_contract_id"],
        "service_environment": expected_environment,
        "stdio_facts": normalized_stdio,
        "exact_live_file_descriptors": [0, 1, 2],
        "remote_tool_facts": dict(live_tool_facts),
        "isolated_python_flags": ["-I", "-S", "-B"],
        "invocation_id_rejoined_to_systemd_unit": True,
        "service_cgroup_rejoined_to_systemd_unit": True,
        "all_three_stdio_descriptors_are_dev_null": True,
        "formal_runner_invocation_authorized": True,
        "formal_execution_performed": False,
    }
    return {
        **payload,
        "formal_service_wrapper_attestation_id": _content_id(
            "service-wrapper-attestation", payload
        ),
    }


def verify_service_wrapper_attestation_self_contained_v42r1(
    raw_or_document: bytes | dict[str, Any], *, plan: Mapping[str, Any],
    launch_transport_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild a persisted wrapper attestation from all live observations."""

    document = _canonical_document(
        raw_or_document, "formal service wrapper attestation"
    )
    manager = {
        key: document.get(key)
        for key in (
            "kernel_boot_id", "user_manager_invocation_id",
            "user_manager_main_pid", "user_manager_control_group",
            "cgroup_contract_id",
        )
    }
    manager["linger_enabled"] = True
    expected = build_service_wrapper_attestation_v42r1(
        plan=plan,
        launch_transport_attempt=launch_transport_attempt,
        manager_binding=manager,
        unit_observation=document.get("systemd_unit_observation"),
        service_pid=document.get("service_pid"),
        service_cgroup=document.get("service_cgroup"),
        service_environment=document.get("service_environment"),
        stdio_facts=document.get("stdio_facts"),
        live_file_descriptors=document.get("exact_live_file_descriptors"),
        live_tool_facts=document.get("remote_tool_facts"),
    )
    if document != expected:
        _fail("formal service wrapper attestation changed")
    return document


def build_read_only_inspection_v42r1(
    *, plan: Mapping[str, Any], operation: str, attempt_id: str,
    inspection_ordinal: int, manager_binding: dict[str, Any],
    unit_observation: dict[str, Any] | None,
    artifact_states: Mapping[str, str],
    recovered_documents: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if operation not in OPERATIONS or type(inspection_ordinal) is not int or inspection_ordinal < 1:
        _fail("read-only inspection operation or ordinal changed")
    _hex(attempt_id, 64, "inspection attempt ID")
    manager = _manager_binding(manager_binding, plan)
    expected_artifacts = {
        "prepare_receipt", "prepare_failure", "remote_launch_transport_attempt",
        "remote_launch_admission_receipt", "service_wrapper_attestation",
        "launch_attempt_journal",
        "runner_failure", "scientific_terminal",
    }
    if type(artifact_states) is not dict or set(artifact_states) != expected_artifacts:
        _fail("read-only inspection artifact inventory changed")
    states = dict(artifact_states)
    if any(value not in ARTIFACT_STATES for value in states.values()):
        _fail("read-only inspection artifact state changed vocabulary")
    recovered = {} if recovered_documents is None else dict(recovered_documents)
    allowed_recovered = (
        {"prepare_receipt"}
        if operation == OPERATION_PREPARE
        else {"launch_admission_receipt"}
    )
    if (
        type(recovered_documents) not in {dict, type(None)}
        or not set(recovered) <= allowed_recovered
        or any(type(value) is not dict for value in recovered.values())
    ):
        _fail("read-only inspection recovered document inventory changed")
    if (
        "prepare_receipt" in recovered
        and states["prepare_receipt"] != "EXACT"
    ):
        _fail("inspection recovered a nonexact prepare receipt")
    if (
        "launch_admission_receipt" in recovered
        and states["remote_launch_admission_receipt"] != "EXACT"
    ):
        _fail("inspection recovered a nonexact launch admission receipt")
    # Round-trip every document through the canonical encoder before binding it
    # into the inspection content ID.
    recovered = {
        key: _canonical_document(canonical_json_bytes(value), key)
        for key, value in recovered.items()
    }
    if operation == OPERATION_LAUNCH:
        if unit_observation is None:
            _fail("launch inspection omitted the systemd unit observation")
        unit = _unit_observation(unit_observation, unit_name_v42r1(attempt_id))
        expected_systemd = build_systemd_run_argv_v42r1(
            plan=plan,
            local_launch_attempt={"local_launch_attempt_id": attempt_id},
        )
        expected_exec = list(expected_systemd[expected_systemd.index("--") + 1 :])
        if (
            unit["LoadState"] == "loaded"
            and unit["MainPID"] > 1
            and unit["LiveMainPIDArgv"]
            != list(
                _receiver_python_argv(
                    plan=plan, mode="--formal-launch-service-wrapper",
                    attempt_id=attempt_id,
                    runtime_invocation_id=unit["InvocationID"],
                    runtime_control_group=unit["ControlGroup"],
                )
            )
        ):
            _fail("read-only inspection live /proc MainPID argv changed")
    elif unit_observation is not None:
        _fail("prepare inspection unexpectedly included a launch unit")
    else:
        unit = None
    payload = {
        **_base(FORMAL_READ_ONLY_INSPECTION_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "operation": operation,
        "attempt_id": attempt_id,
        "inspection_ordinal": inspection_ordinal,
        "manager_binding": manager,
        "unit_observation": unit,
        "artifact_states": states,
        "recovered_documents": recovered,
        "remote_mutation_performed": False,
        "systemd_lifecycle_mutation_performed": False,
        "same_effect_reissued": False,
    }
    return {
        **payload,
        "formal_read_only_inspection_id": _content_id("inspection", payload),
    }


def classify_formal_operation_v42r1(
    *, plan: Mapping[str, Any], operation: str, attempt_id: str,
    marker_present: bool, exact_receipt_present: bool,
    inspection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if operation not in OPERATIONS or type(marker_present) is not bool or type(exact_receipt_present) is not bool:
        _fail("formal classifier inputs changed")
    _hex(attempt_id, 64, "classification attempt ID")
    reasons: list[str] = []
    if not marker_present:
        if exact_receipt_present or inspection is not None:
            _fail("pre-marker state cannot contain a receipt or remote inspection")
        classification = CLASS_PRE_NETWORK_RETRYABLE
        retry = True
    elif inspection is None:
        classification = (
            CLASS_PREPARE_COMPLETE
            if operation == OPERATION_PREPARE and exact_receipt_present
            else CLASS_LAUNCH_ADMITTED
            if operation == OPERATION_LAUNCH and exact_receipt_present
            else CLASS_AMBIGUOUS
        )
        retry = False
        if not exact_receipt_present:
            reasons.append("MARKER_WITHOUT_EXACT_RECEIPT")
    else:
        if (
            inspection.get("schema") != FORMAL_READ_ONLY_INSPECTION_SCHEMA
            or inspection.get("formal_transport_plan_id")
            != plan["formal_transport_plan_id"]
            or inspection.get("operation") != operation
            or inspection.get("attempt_id") != attempt_id
            or inspection.get("remote_mutation_performed") is not False
        ):
            _fail("formal classifier inspection join changed")
        manager = inspection["manager_binding"]
        states = inspection["artifact_states"]
        if manager.get("matches_activation") is not True:
            classification = CLASS_AMBIGUOUS
            reasons.append("BOOT_OR_USER_MANAGER_OR_CGROUP_DRIFT")
        elif "PRESENT_INVALID" in states.values():
            classification = CLASS_AMBIGUOUS
            reasons.append("PRESENT_INVALID_REMOTE_ARTIFACT")
        elif operation == OPERATION_PREPARE:
            if (
                states["prepare_receipt"] == "EXACT"
                and states["prepare_failure"] == "ABSENT"
            ):
                classification = CLASS_PREPARE_COMPLETE
            elif (
                states["prepare_failure"] == "EXACT"
                and states["prepare_receipt"] == "ABSENT"
            ):
                classification = CLASS_COMPLETE_FAILURE
            else:
                classification = CLASS_AMBIGUOUS
                reasons.append("PREPARE_TERMINAL_CONFLICT_OR_NOT_EXACT")
        else:
            reachable = (
                states["prepare_receipt"] == "EXACT"
                and states["prepare_failure"] == "ABSENT"
                and states["remote_launch_transport_attempt"] == "EXACT"
                and states["remote_launch_admission_receipt"] == "EXACT"
            )
            terminal_predecessors = (
                reachable
                and states["service_wrapper_attestation"] == "EXACT"
                and states["launch_attempt_journal"] == "EXACT"
            )
            if (
                states["scientific_terminal"] in {
                    "EXACT_SUCCESS", "EXACT_FAIL_CLOSED"
                }
                and states["runner_failure"] == "EXACT"
            ):
                classification = CLASS_AMBIGUOUS
                reasons.append("SCIENTIFIC_TERMINAL_AND_RUNNER_FAILURE_CONFLICT")
            elif states["scientific_terminal"] == "EXACT_SUCCESS":
                if terminal_predecessors and states["runner_failure"] == "ABSENT":
                    classification = CLASS_COMPLETE_SUCCESS
                else:
                    classification = CLASS_AMBIGUOUS
                    reasons.append("LAUNCH_TERMINAL_PREDECESSOR_CHAIN_NOT_EXACT")
            elif states["scientific_terminal"] == "EXACT_FAIL_CLOSED":
                if terminal_predecessors and states["runner_failure"] == "ABSENT":
                    classification = CLASS_COMPLETE_FAILURE
                    reasons.append("SCIENTIFIC_TERMINAL_FAIL_CLOSED")
                else:
                    classification = CLASS_AMBIGUOUS
                    reasons.append("LAUNCH_TERMINAL_PREDECESSOR_CHAIN_NOT_EXACT")
            elif states["runner_failure"] == "EXACT":
                if (
                    terminal_predecessors
                    and states["scientific_terminal"] == "ABSENT"
                ):
                    classification = CLASS_COMPLETE_FAILURE
                else:
                    classification = CLASS_AMBIGUOUS
                    reasons.append("LAUNCH_FAILURE_PREDECESSOR_CHAIN_NOT_EXACT")
            else:
                unit = inspection["unit_observation"]
                partial_wrapper_chain = (
                    states["service_wrapper_attestation"] == "ABSENT"
                    and states["launch_attempt_journal"] == "ABSENT"
                ) or (
                    states["service_wrapper_attestation"] == "EXACT"
                    and states["launch_attempt_journal"]
                    in {"ABSENT", "EXACT"}
                )
                if (
                    reachable
                    and partial_wrapper_chain
                    and states["scientific_terminal"] == "ABSENT"
                    and states["runner_failure"] == "ABSENT"
                    and unit["LoadState"] == "loaded"
                    and unit["ActiveState"] in {"active", "activating"}
                    and unit["SubState"] in {"start", "running"}
                ):
                    classification = CLASS_IN_PROGRESS
                else:
                    classification = CLASS_AMBIGUOUS
                    if terminal_predecessors:
                        reasons.append("SUPERVISION_LOST_WITHOUT_EXACT_TERMINAL")
                    else:
                        reasons.append(
                            "UNIT_ABSENT_OR_NONACTIVE_OR_PREDECESSOR_CHAIN_NOT_EXACT"
                        )
        retry = False
    payload = {
        **_base(FORMAL_CLASSIFICATION_SCHEMA),
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "operation": operation,
        "attempt_id": attempt_id,
        "network_start_marker_present": marker_present,
        "exact_transport_receipt_present": exact_receipt_present,
        "classification": classification,
        "reason_codes": reasons,
        "same_effect_replay_allowed": retry,
        "only_read_only_inspection_allowed": marker_present,
        "unit_absence_used_as_never_started_proof": False,
    }
    return {
        **payload,
        "formal_transport_classification_id": _content_id("classification", payload),
    }


__all__ = [
    "ACTIVATION_TERMINAL_PROTOCOL",
    "ADMISSION_TRANSPORT_TIMEOUT_SECONDS",
    "ARTIFACT_STATES",
    "CLASS_AMBIGUOUS",
    "CLASS_COMPLETE_FAILURE",
    "CLASS_COMPLETE_SUCCESS",
    "CLASS_IN_PROGRESS",
    "CLASS_LAUNCH_ADMITTED",
    "CLASS_PRE_NETWORK_RETRYABLE",
    "CLASS_PREPARE_COMPLETE",
    "FORMAL_DRIVER_RELATIVE",
    "FORMAL_RECEIVER_RELATIVE",
    "FORBIDDEN_SYSTEMD_OPTIONS",
    "INSPECTION_TRANSPORT_TIMEOUT_SECONDS",
    "LOCAL_FORMAL_JOURNAL_ROOT",
    "OPERATION_LAUNCH",
    "OPERATION_PREPARE",
    "OUTCOME_COMPLETE_EXACT_RECEIPT",
    "OUTCOME_POST_MARKER_AMBIGUOUS",
    "OUTCOME_PRE_NETWORK_FAILURE",
    "PREPARE_TRANSPORT_TIMEOUT_SECONDS",
    "REMOTE_FORMAL_JOURNAL_ROOT",
    "SYSTEMD_CLIENT_ENVIRONMENT",
    "SYSTEMD_RUNTIME_MAX_SECONDS",
    "V42FormalTransportError",
    "build_formal_transport_plan_v42r1",
    "build_cgroup_contract_id_v42r1",
    "build_launch_admission_receipt_v42r1",
    "build_launch_transport_attempt_v42r1",
    "build_network_start_v42r1",
    "build_operation_outcome_v42r1",
    "build_prepare_attempt_v42r1",
    "build_read_only_inspection_v42r1",
    "build_service_wrapper_attestation_v42r1",
    "build_systemd_run_argv_v42r1",
    "classify_formal_operation_v42r1",
    "materialize_ssh_argv_v42r1",
    "unit_name_v42r1",
    "validate_activation_terminal_protocol_v42r1",
    "validate_systemd_run_argv_v42r1",
    "verify_formal_transport_plan_v42r1",
    "verify_launch_admission_receipt_self_contained_v42r1",
    "verify_prepare_attempt_v42r1",
    "verify_self_contained_formal_transport_plan_v42r1",
]
