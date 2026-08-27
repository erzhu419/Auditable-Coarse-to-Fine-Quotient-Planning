"""Tiny stdlib-only loader for V42 materialization activation.

These committed bytes are embedded in the ordinary-SSH ingress command and in
the transient systemd service command.  No received or ledger-resident Python
is compiled until its exact byte count and SHA-256 have been checked.  The
loader itself performs no project filesystem mutation.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
import sys


_HEX64 = re.compile(r"[0-9a-f]{64}")
_MAXIMUM_PROGRAM_BYTES = 4 * 1024**2
_MAXIMUM_ENVELOPE_BYTES = 4 * 1024**2
_MAXIMUM_TRANSPORT_MANIFEST_BYTES = 16 * 1024**2
_REMOTE_UID = 1000
_REMOTE_GID = 1000
_REMOTE_ATTEMPT_NAME = "REMOTE_MATERIALIZATION_ACTIVATION_ATTEMPT.json"
_REMOTE_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_remote_materialization_activation_attempt.v42r1"
)
_FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2"
_SCHEMA_VERSION = "42.1.0"
_DOMAIN = "acfqp:v42-remote-ordinal2:remote-materialization-activation-attempt"


class _ActivationLoaderFailure(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise _ActivationLoaderFailure(message)


def _decimal(value: str, label: str) -> int:
    if not value or value.startswith("+"):
        _fail(label + " changed")
    try:
        parsed = int(value, 10)
    except ValueError as error:
        raise _ActivationLoaderFailure(label + " changed") from error
    if parsed < 0 or str(parsed) != value:
        _fail(label + " changed")
    return parsed


def _read_exact(descriptor: int, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = os.read(descriptor, min(remaining, 1024 * 1024))
        if not chunk:
            _fail("verified program source ended early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_to_eof(descriptor: int, maximum: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(1024 * 1024, maximum + 1 - total))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        total += len(chunk)
        if total > maximum:
            _fail("activation envelope exceeded its cap")


def _current_unified_cgroup() -> str:
    descriptor = os.open(
        "/proc/self/cgroup", os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    try:
        raw = _read_to_eof(descriptor, 4096)
    finally:
        os.close(descriptor)
    if (
        not raw.startswith(b"0::/")
        or raw.count(b"\n") != 1
        or not raw.endswith(b"\n")
    ):
        _fail("systemd service cgroup record changed")
    value = raw[3:-1].decode("ascii", errors="strict")
    if not value.startswith("/") or ".." in value.split("/"):
        _fail("systemd service cgroup path changed")
    return value


def _live_descriptors() -> tuple[int, ...]:
    scanner = os.open(
        "/proc/self/fd",
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        if scanner != 3:
            _fail("descriptor scanner was not the sole new descriptor")
        names = {int(name) for name in os.listdir(scanner)}
        if names != {0, 1, 2, scanner, scanner + 1}:
            _fail("inherited descriptor inventory changed")
        for descriptor in (0, 1, 2, scanner):
            os.fstat(descriptor)
        try:
            os.fstat(scanner + 1)
        except OSError as error:
            if error.errno != errno.EBADF:
                raise
        else:
            _fail("descriptor iterator remained live")
    finally:
        os.close(scanner)
    return (0, 1, 2)


def _require_runtime(source: str) -> None:
    if (
        sys.executable != "/usr/bin/python3"
        or os.path.realpath(sys.executable) != "/usr/bin/python3.12"
        or tuple(sys.version_info[:3]) != (3, 12, 3)
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
    ):
        _fail("isolated Python runtime changed")
    if sys.argv[0] != "-c" or len(sys.argv) not in (8, 10):
        _fail("loader argv schema changed")
    if sys.orig_argv != [
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-c",
        source,
        *sys.argv[1:],
    ]:
        _fail("loader original argv changed")
    if _live_descriptors() != (0, 1, 2):
        _fail("loader descriptor set changed")
    if any(os.isatty(descriptor) for descriptor in (0, 1, 2)):
        _fail("loader stdio unexpectedly refers to a terminal")


def _verify_self(source: str, expected_sha: str, expected_count_raw: str) -> None:
    raw = source.encode("utf-8", errors="strict")
    expected_count = _decimal(expected_count_raw, "loader byte count")
    if (
        _HEX64.fullmatch(expected_sha) is None
        or expected_count != len(raw)
        or hashlib.sha256(raw).hexdigest() != expected_sha
    ):
        _fail("loader source identity changed")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate activation ledger JSON key")
        result[key] = value
    return result


def _reject_number(token: str) -> None:
    _fail("non-integer activation ledger JSON number: " + token)


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
        raise _ActivationLoaderFailure("activation ledger value is not canonical") from error


def _component_identity(observed: os.stat_result) -> tuple[int, ...]:
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_uid,
        observed.st_gid,
    )


def _open_lexical_directory_pins(
    path: str,
) -> tuple[list[int], list[str], list[tuple[int, ...]]]:
    if not path.startswith("/") or ".." in path.split("/"):
        _fail("activation control root path changed")
    descriptors = [os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)]
    names: list[str] = []
    identities = [_component_identity(os.fstat(descriptors[0]))]
    try:
        for component in (item for item in path.split("/") if item):
            parent = descriptors[-1]
            before = os.stat(component, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                _fail("activation control root component changed type")
            descriptor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=parent,
            )
            opened = os.fstat(descriptor)
            if _component_identity(before) != _component_identity(opened):
                os.close(descriptor)
                _fail("activation control root changed during open")
            descriptors.append(descriptor)
            names.append(component)
            identities.append(_component_identity(opened))
        return descriptors, names, identities
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _verify_lexical_directory_pins(
    descriptors: list[int], names: list[str], identities: list[tuple[int, ...]]
) -> None:
    if (
        len(descriptors) != len(names) + 1
        or len(identities) != len(descriptors)
        or _component_identity(os.fstat(descriptors[0])) != identities[0]
    ):
        _fail("activation control root anchor changed")
    for index, component in enumerate(names):
        named = os.stat(
            component, dir_fd=descriptors[index], follow_symlinks=False
        )
        held = os.fstat(descriptors[index + 1])
        if (
            not stat.S_ISDIR(named.st_mode)
            or _component_identity(named) != identities[index + 1]
            or _component_identity(held) != identities[index + 1]
        ):
            _fail("activation control root lexical chain changed")


def _read_transport_manifest_from_plan(plan: dict[str, object]) -> dict[str, object]:
    facts = plan.get("control_facts")
    if type(facts) is not list:
        _fail("activation control facts changed type")
    candidates = [
        row
        for row in facts
        if type(row) is dict and row.get("name") == "TRANSPORT_MANIFEST.json"
    ]
    if len(candidates) != 1:
        _fail("activation transport control fact changed")
    fact = candidates[0]
    expected_count = fact.get("byte_count")
    expected_sha = fact.get("sha256")
    if (
        type(expected_count) is not int
        or not 0 < expected_count <= _MAXIMUM_TRANSPORT_MANIFEST_BYTES
        or type(expected_sha) is not str
        or _HEX64.fullmatch(expected_sha) is None
    ):
        _fail("activation transport control fact identity changed")
    opened: list[tuple[list[int], list[str], list[tuple[int, ...]]]] = []
    for key in ("preformal_scratch_root", "fixed_remote_root"):
        candidate = plan.get(key)
        if type(candidate) is not str:
            _fail("activation control root changed type")
        try:
            opened.append(_open_lexical_directory_pins(candidate))
        except FileNotFoundError:
            continue
    if len(opened) != 1:
        for descriptors, _names, _identities in opened:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
        _fail("activation transport manifest root state changed")
    descriptors, names, identities = opened[0]
    root_fd = descriptors[-1]
    try:
        _verify_lexical_directory_pins(descriptors, names, identities)
        before = os.stat(
            "TRANSPORT_MANIFEST.json", dir_fd=root_fd, follow_symlinks=False
        )
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o400
            or before.st_uid != _REMOTE_UID
            or before.st_gid != _REMOTE_GID
            or before.st_nlink != 1
            or before.st_size != expected_count
        ):
            _fail("activation transport manifest storage changed")
        descriptor = os.open(
            "TRANSPORT_MANIFEST.json",
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=root_fd,
        )
        try:
            opened_file = os.fstat(descriptor)
            if (opened_file.st_dev, opened_file.st_ino) != (
                before.st_dev,
                before.st_ino,
            ):
                _fail("activation transport manifest changed before open")
            raw = _read_exact(descriptor, expected_count)
            if os.read(descriptor, 1):
                _fail("activation transport manifest exceeded expected size")
            after_fd = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after_path = os.stat(
            "TRANSPORT_MANIFEST.json", dir_fd=root_fd, follow_symlinks=False
        )
        fields = (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
            "st_size", "st_mtime_ns", "st_ctime_ns",
        )
        if any(
            getattr(before, field) != getattr(after_fd, field)
            or getattr(before, field) != getattr(after_path, field)
            for field in fields
        ):
            _fail("activation transport manifest changed while read")
        _verify_lexical_directory_pins(descriptors, names, identities)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        _fail("activation transport manifest hash changed")
    try:
        document = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except _ActivationLoaderFailure:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise _ActivationLoaderFailure(
            "activation transport manifest is not strict JSON"
        ) from error
    if type(document) is not dict or _canonical_bytes(document) != raw:
        _fail("activation transport manifest is not canonical")
    identity = document.get("transport_manifest_id")
    if identity != plan.get("transport_manifest_id"):
        _fail("activation transport manifest plan join changed")
    payload = dict(document)
    payload.pop("transport_manifest_id", None)
    if identity != hashlib.sha256(
        b"acfqp:v42-remote-ordinal2:transport-manifest\0"
        + _canonical_bytes(payload)
    ).hexdigest():
        _fail("activation transport manifest content identity changed")
    return document


def _verify_program_transport_facts(
    plan: dict[str, object], actual_programs: tuple[tuple[str, bytes], ...]
) -> None:
    transport = _read_transport_manifest_from_plan(plan)
    rows = transport.get("transport_facts")
    if type(rows) is not list:
        _fail("activation transport facts changed type")
    by_path = {
        row.get("relative_path"): row for row in rows if type(row) is dict
    }
    if len(by_path) != len(rows):
        _fail("activation transport facts contain duplicate paths")
    for artifact_key, raw in actual_programs:
        artifact = plan.get(artifact_key)
        if type(artifact) is not dict:
            _fail("activation program artifact changed type")
        relative_path = artifact.get("relative_path")
        row = by_path.get(relative_path)
        actual_sha = hashlib.sha256(raw).hexdigest()
        actual_oid = hashlib.sha1(  # noqa: S324 - Git object identity
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest()
        if (
            type(row) is not dict
            or artifact.get("byte_count") != len(raw)
            or artifact.get("sha256") != actual_sha
            or artifact.get("git_blob_oid") != actual_oid
            or artifact.get("git_mode") != "100644"
            or artifact.get("git_object_type") != "blob"
            or row.get("byte_count") != len(raw)
            or row.get("sha256") != actual_sha
            or row.get("git_blob_oid") != actual_oid
            or row.get("git_mode") != "100644"
            or row.get("git_object_type") != "blob"
        ):
            _fail("activation program does not join exact transport fact")


def _read_ledger_file(path: str, maximum: int) -> bytes:
    before = os.lstat(path)
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_uid != _REMOTE_UID
        or before.st_gid != _REMOTE_GID
        or before.st_nlink != 1
        or not 0 < before.st_size <= maximum
    ):
        _fail("activation ledger attempt storage changed")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("activation ledger attempt changed before open")
        raw = _read_exact(descriptor, before.st_size)
        if os.read(descriptor, 1):
            _fail("activation ledger attempt has trailing bytes")
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
        or getattr(before, field) != getattr(final, field)
        for field in fields
    ):
        _fail("activation ledger attempt changed while read")
    return raw


def _remote_attempt_for_service(service_path: str, expected_id: str) -> dict[str, object]:
    attempt_path = os.path.join(os.path.dirname(service_path), _REMOTE_ATTEMPT_NAME)
    raw = _read_ledger_file(attempt_path, 4 * 1024**2)
    try:
        document = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except _ActivationLoaderFailure:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise _ActivationLoaderFailure("activation ledger attempt is not strict JSON") from error
    if type(document) is not dict or _canonical_bytes(document) != raw:
        _fail("activation ledger attempt is not canonical")
    identity = document.get("remote_materialization_activation_attempt_id")
    if (
        identity != expected_id
        or document.get("schema") != _REMOTE_ATTEMPT_SCHEMA
        or document.get("schema_version") != _SCHEMA_VERSION
        or document.get("formal_identity") != _FORMAL_IDENTITY
        or document.get("global_execution_ordinal") != 2
    ):
        _fail("activation ledger attempt identity changed")
    payload = dict(document)
    del payload["remote_materialization_activation_attempt_id"]
    expected = hashlib.sha256(
        _DOMAIN.encode("ascii") + b"\0" + _canonical_bytes(payload)
    ).hexdigest()
    if identity != expected:
        _fail("activation ledger attempt content ID changed")
    return document


def _materialize_service_template(
    template: object,
    *,
    remote_attempt_id: str,
    invocation_id: str | None = None,
    control_group: str | None = None,
) -> list[str]:
    if type(template) is not list or any(type(item) is not str for item in template):
        _fail("activation service argv template changed")
    replacements = {
        "{acfqp_v42_remote_materialization_activation_attempt_id}": remote_attempt_id,
    }
    if invocation_id is not None:
        replacements["{acfqp_v42_systemd_invocation_id}"] = invocation_id
    if control_group is not None:
        replacements["{acfqp_v42_systemd_control_group}"] = control_group
    result: list[str] = []
    for item in template:
        value = item
        for sentinel, replacement in replacements.items():
            value = value.replace(sentinel, replacement)
        result.append(value)
    if any("{acfqp_v42_" in item for item in result):
        _fail("activation service argv replacement was incomplete")
    return result


def _compile_entry(raw: bytes, *, filename: str, entry_name: str):
    code = compile(raw, filename, "exec", flags=0, dont_inherit=True, optimize=0)
    namespace = {
        "__builtins__": __builtins__,
        "__name__": filename.strip("<>").replace("-", "_"),
        "__file__": filename,
        "__package__": None,
    }
    exec(code, namespace, namespace)
    entry = namespace.get(entry_name)
    if not callable(entry):
        _fail("verified activation program entry changed")
    return entry


def _verified_plan_from_envelope(
    raw: bytes, *, mode: str, expected_plan_id: str
) -> dict[str, object]:
    try:
        envelope = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except _ActivationLoaderFailure:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise _ActivationLoaderFailure(
            "activation envelope is not strict JSON"
        ) from error
    if type(envelope) is not dict or _canonical_bytes(envelope) != raw:
        _fail("activation envelope is not canonical")
    if mode == "--activation-resource-probe":
        key = "resource_plan"
        identity = "preactivation_resource_probe_plan_id"
        schema = "acfqp.v42_remote_ordinal2_preactivation_resource_probe_plan.v42r1"
        domain = "acfqp:v42-remote-ordinal2:preactivation-resource-probe-plan"
    else:
        key = "activation_plan"
        identity = "materialization_activation_plan_id"
        schema = "acfqp.v42_remote_ordinal2_materialization_activation_plan.v42r1"
        domain = "acfqp:v42-remote-ordinal2:materialization-activation-plan"
    plan = envelope.get(key)
    if (
        type(plan) is not dict
        or plan.get("schema") != schema
        or plan.get(identity) != expected_plan_id
    ):
        _fail("activation envelope plan authority changed")
    payload = dict(plan)
    del payload[identity]
    if hashlib.sha256(
        domain.encode("ascii") + b"\0" + _canonical_bytes(payload)
    ).hexdigest() != expected_plan_id:
        _fail("activation envelope plan content ID changed")
    return plan


def _verify_current_python_tcb(plan: dict[str, object]) -> None:
    startup = plan.get("remote_startup_tcb_contract")
    if type(startup) is not dict:
        _fail("remote Python TCB contract changed")
    expected_count = startup.get("python_realpath_byte_count")
    expected_hash = startup.get("python_realpath_sha256")
    if (
        type(expected_count) is not int
        or not 0 < expected_count <= 16 * 1024**2
        or type(expected_hash) is not str
        or _HEX64.fullmatch(expected_hash) is None
        or os.readlink("/proc/self/exe") != startup.get("python_realpath")
    ):
        _fail("current Python identity contract changed")
    # /proc/self/exe is a kernel-owned magic link to the already executing
    # image; opening that link is intentional and is followed by exact fstat,
    # byte-count, and digest checks against the content-addressed plan.
    descriptor = os.open("/proc/self/exe", os.O_RDONLY | os.O_CLOEXEC)
    try:
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != startup.get("python_realpath_mode")
            or observed.st_uid != startup.get("python_realpath_uid")
            or observed.st_gid != startup.get("python_realpath_gid")
            or observed.st_nlink != startup.get("python_realpath_nlink")
            or observed.st_size != expected_count
        ):
            _fail("current Python storage changed")
        digest = hashlib.sha256()
        offset = 0
        while offset < expected_count:
            chunk = os.pread(
                descriptor, min(1024 * 1024, expected_count - offset), offset
            )
            if not chunk:
                _fail("current Python ended early")
            digest.update(chunk)
            offset += len(chunk)
        if os.pread(descriptor, 1, expected_count):
            _fail("current Python exceeded expected byte count")
        final = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(getattr(observed, field) != getattr(final, field) for field in fields):
        _fail("current Python changed while hashed")
    if digest.hexdigest() != expected_hash:
        _fail("current Python bytes changed")


def _read_service_source(path: str, expected_sha: str, expected_count: int) -> bytes:
    if not path.startswith("/home/erzhu419/mine_code/") or ".." in path.split("/"):
        _fail("activation service path changed")
    before = os.lstat(path)
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_uid != _REMOTE_UID
        or before.st_gid != _REMOTE_GID
        or before.st_nlink != 1
        or before.st_size != expected_count
    ):
        _fail("activation service storage changed")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("activation service changed before open")
        raw = _read_exact(descriptor, expected_count)
        if os.read(descriptor, 1):
            _fail("activation service has trailing bytes")
        after_fd = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.lstat(path)
    fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_uid",
        "st_gid",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after_fd, field)
        or getattr(before, field) != getattr(after_path, field)
        for field in fields
    ):
        _fail("activation service changed while read")
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        _fail("activation service hash changed")
    return raw


def _entry() -> int:
    source = sys.orig_argv[5] if len(sys.orig_argv) > 5 else ""
    _require_runtime(source)
    mode = sys.argv[1]
    expected_loader_sha = sys.argv[2]
    expected_loader_count_raw = sys.argv[3]
    _verify_self(source, expected_loader_sha, expected_loader_count_raw)
    if mode in ("--activation-ingress", "--activation-resource-probe", "--activation-classify"):
        expected_program_sha = sys.argv[4]
        expected_program_count = _decimal(sys.argv[5], "receiver byte count")
        plan_id = sys.argv[6]
        attempt_id = sys.argv[7]
        if (
            _HEX64.fullmatch(expected_program_sha) is None
            or _HEX64.fullmatch(plan_id) is None
            or _HEX64.fullmatch(attempt_id) is None
            or not 0 < expected_program_count <= _MAXIMUM_PROGRAM_BYTES
        ):
            _fail("activation ingress identity changed")
        program_raw = _read_exact(0, expected_program_count)
        if hashlib.sha256(program_raw).hexdigest() != expected_program_sha:
            _fail("activation receiver hash changed")
        envelope_raw = _read_to_eof(0, _MAXIMUM_ENVELOPE_BYTES)
        plan = _verified_plan_from_envelope(
            envelope_raw, mode=mode, expected_plan_id=plan_id
        )
        _verify_current_python_tcb(plan)
        _verify_program_transport_facts(
            plan,
            (
                ("activation_loader_artifact", source.encode("utf-8")),
                ("activation_receiver_artifact", program_raw),
            ),
        )
        entry = _compile_entry(
            program_raw,
            filename="<acfqp-v42-materialization-activation-receiver>",
            entry_name="main_v42r1",
        )
        result = entry(
            expected_plan_id=plan_id,
            expected_local_attempt_id=attempt_id,
            verified_envelope_raw=envelope_raw,
            verified_receiver_sha256=expected_program_sha,
            observed_remote_ingress_python_argv=list(sys.orig_argv),
            loader_mode=mode,
        )
    elif mode in ("--activation-service-bootstrap", "--activation-service-clean"):
        service_path = sys.argv[4]
        expected_program_sha = sys.argv[5]
        expected_program_count = _decimal(sys.argv[6], "service byte count")
        remote_attempt_id = sys.argv[7]
        if (
            _HEX64.fullmatch(expected_program_sha) is None
            or _HEX64.fullmatch(remote_attempt_id) is None
            or not 0 < expected_program_count <= _MAXIMUM_PROGRAM_BYTES
        ):
            _fail("activation service identity changed")
        program_raw = _read_service_source(
            service_path, expected_program_sha, expected_program_count
        )
        remote_attempt = _remote_attempt_for_service(
            service_path, remote_attempt_id
        )
        plan = remote_attempt.get("materialization_activation_plan")
        if type(plan) is not dict:
            _fail("activation ledger attempt omitted its plan")
        _verify_current_python_tcb(plan)
        _verify_program_transport_facts(
            plan,
            (
                ("activation_loader_artifact", source.encode("utf-8")),
                ("activation_service_artifact", program_raw),
            ),
        )
        if mode == "--activation-service-bootstrap":
            contract = plan.get("systemd_service_contract")
            if type(contract) is not dict:
                _fail("activation systemd service contract changed")
            expected_bootstrap = _materialize_service_template(
                contract.get("authorized_service_bootstrap_argv_template"),
                remote_attempt_id=remote_attempt_id,
            )
            if list(sys.orig_argv) != expected_bootstrap:
                _fail("systemd bootstrap argv differs from the verified plan")
            artifact = plan.get("activation_service_artifact")
            if (
                type(artifact) is not dict
                or service_path != contract.get("activation_service_source_path")
                or expected_program_sha != artifact.get("sha256")
                or expected_program_count != artifact.get("byte_count")
            ):
                _fail("systemd bootstrap service artifact changed")
            invocation_id = os.environ.get("INVOCATION_ID")
            if invocation_id is None or re.fullmatch(r"[0-9a-f]{32}", invocation_id) is None:
                _fail("systemd invocation ID changed")
            control_group = _current_unified_cgroup()
            expected_unit = (
                "acfqp-v42-o2-activation-"
                + str(plan.get("materialization_activation_plan_id"))
                + ".service"
            )
            if not control_group.endswith("/app.slice/" + expected_unit):
                _fail("systemd service cgroup unit changed")
            null_stat = os.stat("/dev/null", follow_symlinks=False)
            if not stat.S_ISCHR(null_stat.st_mode):
                _fail("/dev/null changed type")
            for descriptor in (0, 1, 2):
                observed = os.fstat(descriptor)
                if (
                    not stat.S_ISCHR(observed.st_mode)
                    or (observed.st_dev, observed.st_ino, observed.st_rdev)
                    != (null_stat.st_dev, null_stat.st_ino, null_stat.st_rdev)
                ):
                    _fail("systemd service stdio is not exact /dev/null")
            clean_argv = _materialize_service_template(
                contract.get("authorized_service_worker_argv_template"),
                remote_attempt_id=remote_attempt_id,
                invocation_id=invocation_id,
                control_group=control_group,
            )
            os.execve("/proc/self/exe", clean_argv, {"LC_ALL": "C.UTF-8"})
            _fail("systemd service environment normalization exec returned")
        invocation_id = sys.argv[8]
        control_group = sys.argv[9]
        if (
            os.environ != {"LC_ALL": "C.UTF-8"}
            or re.fullmatch(r"[0-9a-f]{32}", invocation_id) is None
            or not control_group.startswith("/")
            or ".." in control_group.split("/")
            or _current_unified_cgroup() != control_group
        ):
            _fail("clean systemd service runtime changed")
        null_stat = os.stat("/dev/null", follow_symlinks=False)
        for descriptor in (0, 1, 2):
            observed = os.fstat(descriptor)
            if (
                not stat.S_ISCHR(observed.st_mode)
                or (observed.st_dev, observed.st_ino, observed.st_rdev)
                != (null_stat.st_dev, null_stat.st_ino, null_stat.st_rdev)
            ):
                _fail("clean service stdio is not exact /dev/null")
        entry = _compile_entry(
            program_raw,
            filename="<acfqp-v42-materialization-activation-service>",
            entry_name="main_v42r1",
        )
        result = entry(
            remote_activation_attempt_id=remote_attempt_id,
            systemd_invocation_id=invocation_id,
            systemd_control_group=control_group,
        )
    else:
        _fail("activation loader mode changed")
    if type(result) is not int or not 0 <= result <= 255:
        _fail("verified activation program exit status changed")
    return result


if __name__ == "__main__":
    try:
        _status = _entry()
    except BaseException:
        os.write(2, b"acfqp v42 materialization activation loader rejected ingress\n")
        os._exit(71)
    os._exit(_status)
