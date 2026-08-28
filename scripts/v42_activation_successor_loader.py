"""Tiny stdlib-only loader for the V42r2 read-only activation successor.

The source bytes of this loader are the opaque ``python -c`` argument.  The
loader verifies itself, the received receiver bytes, the content-addressed
successor plan, and the exact Python argv before compiling the receiver.  Its
only receiver operation is the pinned read-only observation; neither program
contains a remote publication path.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import sys


SCHEMA_VERSION = "42.2.0"
PLAN_SCHEMA = "acfqp.v42_activation_successor_read_only_plan.v42r2"
INGRESS_SCHEMA = "acfqp.v42_activation_successor_read_only_ingress.v42r2"
PLAN_DOMAIN = b"acfqp:v42-remote-ordinal2:activation-successor:read-only-plan"
REMOTE_PYTHON = "/usr/bin/python3"
REMOTE_PYTHON_REALPATH = "/usr/bin/python3.12"
REMOTE_PYTHON_VERSION = (3, 12, 3)
FIXED_ROOT = "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2"
SOURCE_ROOT = FIXED_ROOT + "/source"
MODE = "--activation-successor-read-only"
_HEX64 = re.compile(r"[0-9a-f]{64}")
_MAXIMUM_PROGRAM_BYTES = 4 * 1024**2
_MAXIMUM_ENVELOPE_BYTES = 4 * 1024**2


class V42ActivationSuccessorLoaderError(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise V42ActivationSuccessorLoaderError(message)


def _decimal(value: str, label: str) -> int:
    if type(value) is not str or not value or value.startswith("+"):
        _fail(label + " changed")
    try:
        result = int(value, 10)
    except ValueError as error:
        raise V42ActivationSuccessorLoaderError(label + " changed") from error
    if result < 0 or str(result) != value:
        _fail(label + " changed")
    return result


def _read_exact(descriptor: int, count: int) -> bytes:
    if type(count) is not int or not 0 < count <= _MAXIMUM_PROGRAM_BYTES:
        _fail("receiver byte count changed")
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = os.read(descriptor, min(remaining, 1024 * 1024))
        if not chunk:
            _fail("receiver source ended early")
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
            _fail("successor ingress exceeded its cap")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate successor JSON key")
        result[key] = value
    return result


def _reject_number(token: str) -> None:
    _fail("non-integer successor JSON number: " + token)


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
        raise V42ActivationSuccessorLoaderError(
            "successor value is not canonical JSON"
        ) from error


def _canonical_document(raw: bytes, label: str) -> dict[str, object]:
    if type(raw) is not bytes or not 0 < len(raw) <= _MAXIMUM_ENVELOPE_BYTES:
        _fail(label + " byte envelope changed")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except V42ActivationSuccessorLoaderError:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise V42ActivationSuccessorLoaderError(label + " is not strict JSON") from error
    if type(value) is not dict or _canonical_bytes(value) != raw:
        _fail(label + " is not an exact canonical JSON object")
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


def _verify_runtime(source: str) -> None:
    if (
        sys.executable != REMOTE_PYTHON
        or os.path.realpath(sys.executable) != REMOTE_PYTHON_REALPATH
        or tuple(sys.version_info[:3]) != REMOTE_PYTHON_VERSION
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
        or sys.argv[0] != "-c"
        or len(sys.argv) != 8
        or sys.argv[1] != MODE
        or sys.orig_argv
        != [REMOTE_PYTHON, "-I", "-S", "-B", "-c", source, *sys.argv[1:]]
        or _live_descriptors() != (0, 1, 2)
        or any(os.isatty(descriptor) for descriptor in (0, 1, 2))
    ):
        _fail("isolated successor runtime changed")


def _verify_self(source: str, expected_sha: str, expected_count_raw: str) -> bytes:
    raw = source.encode("utf-8", errors="strict")
    if (
        _HEX64.fullmatch(expected_sha) is None
        or _decimal(expected_count_raw, "loader byte count") != len(raw)
        or hashlib.sha256(raw).hexdigest() != expected_sha
    ):
        _fail("successor loader source identity changed")
    return raw


def _verify_plan(
    plan: object,
    *, loader_raw: bytes,
    receiver_raw: bytes,
    expected_plan_id: str,
    expected_legacy_plan_id: str,
) -> dict[str, object]:
    if type(plan) is not dict:
        _fail("successor plan changed type")
    payload = dict(plan)
    claimed = payload.pop("activation_successor_read_only_plan_id", None)
    loader = plan.get("activation_successor_loader_artifact")
    receiver = plan.get("activation_successor_receiver_artifact")
    remote_template = plan.get("authorized_remote_python_argv_template")
    runtime = plan.get("remote_startup_tcb_contract")
    if (
        claimed != expected_plan_id
        or _HEX64.fullmatch(expected_plan_id) is None
        or claimed
        != hashlib.sha256(PLAN_DOMAIN + b"\0" + _canonical_bytes(payload)).hexdigest()
        or plan.get("schema") != PLAN_SCHEMA
        or plan.get("schema_version") != SCHEMA_VERSION
        or plan.get("legacy_materialization_activation_plan_id")
        != expected_legacy_plan_id
        or _HEX64.fullmatch(expected_legacy_plan_id) is None
        or plan.get("fixed_remote_root") != FIXED_ROOT
        or plan.get("remote_source_root") != SOURCE_ROOT
        or plan.get("remote_observation_only") is not True
        or plan.get("remote_mutation_authorized") is not False
        or plan.get("activation_effect_replay_authorized") is not False
        or plan.get("systemd_queries_or_effects_authorized") is not False
        or type(loader) is not dict
        or loader.get("byte_count") != len(loader_raw)
        or loader.get("sha256") != hashlib.sha256(loader_raw).hexdigest()
        or type(receiver) is not dict
        or receiver.get("byte_count") != len(receiver_raw)
        or receiver.get("sha256") != hashlib.sha256(receiver_raw).hexdigest()
        or type(remote_template) is not list
        or len(remote_template) != 13
        or remote_template[:5] != [REMOTE_PYTHON, "-I", "-S", "-B", "-c"]
        or remote_template[5] != loader_raw.decode("utf-8", errors="strict")
        or remote_template[6] != MODE
        or remote_template[7] != loader["sha256"]
        or remote_template[8] != str(loader["byte_count"])
        or remote_template[9] != receiver["sha256"]
        or remote_template[10] != str(receiver["byte_count"])
        or remote_template[11] != "{acfqp_v42_activation_successor_plan_id}"
        or remote_template[12] != "{acfqp_v42_legacy_activation_plan_id}"
        or type(runtime) is not dict
        or runtime.get("python_invocation_path") != REMOTE_PYTHON
        or runtime.get("python_realpath") != REMOTE_PYTHON_REALPATH
        or runtime.get("python_version") != list(REMOTE_PYTHON_VERSION)
        or runtime.get("python_isolated_flag") != 1
        or runtime.get("python_no_site_flag") != 1
        or runtime.get("python_dont_write_bytecode") is not True
        or runtime.get("exact_live_file_descriptors") != [0, 1, 2]
        or runtime.get("stdin_stdout_stderr_must_not_be_tty") is not True
    ):
        _fail("successor plan or executable binding changed")
    return plan


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            _fail("successor response write made no progress")
        view = view[written:]


def main(source: str) -> int:
    _verify_runtime(source)
    loader_raw = _verify_self(source, sys.argv[2], sys.argv[3])
    receiver_sha = sys.argv[4]
    receiver_count = _decimal(sys.argv[5], "receiver byte count")
    expected_plan_id = sys.argv[6]
    expected_legacy_plan_id = sys.argv[7]
    if _HEX64.fullmatch(receiver_sha) is None:
        _fail("receiver SHA-256 changed")
    receiver_raw = _read_exact(0, receiver_count)
    if hashlib.sha256(receiver_raw).hexdigest() != receiver_sha:
        _fail("receiver source identity changed")
    ingress = _canonical_document(
        _read_to_eof(0, _MAXIMUM_ENVELOPE_BYTES), "successor ingress"
    )
    plan = ingress.get("activation_successor_read_only_plan")
    if (
        set(ingress)
        != {"schema", "operation", "activation_successor_read_only_plan"}
        or ingress.get("schema") != INGRESS_SCHEMA
        or ingress.get("operation") != "READ_ONLY_OBSERVE_NESTED_TERMINAL"
    ):
        _fail("successor ingress contract changed")
    verified_plan = _verify_plan(
        plan,
        loader_raw=loader_raw,
        receiver_raw=receiver_raw,
        expected_plan_id=expected_plan_id,
        expected_legacy_plan_id=expected_legacy_plan_id,
    )
    namespace: dict[str, object] = {
        "__name__": "acfqp_v42_activation_successor_receiver",
        "__file__": "<verified-v42-activation-successor-receiver>",
        "__package__": None,
    }
    code = compile(
        receiver_raw,
        "<verified-v42-activation-successor-receiver>",
        "exec",
        dont_inherit=True,
        optimize=2,
    )
    exec(code, namespace, namespace)
    observe = namespace.get("observe")
    if not callable(observe):
        _fail("successor receiver surface changed")
    result = observe(
        fixed_root=verified_plan["fixed_remote_root"],
        expected_uid=1000,
        expected_gid=1000,
    )
    if type(result) is not dict or result.get("remote_mutation_performed") is not False:
        _fail("successor receiver result changed effect semantics")
    _write_all(1, _canonical_bytes(result) + b"\n")
    return 0


if __name__ == "__main__":
    try:
        _status = main(globals().get("__loader_source__", sys.orig_argv[5]))
    except BaseException:
        os.write(2, b"acfqp v42 activation successor loader rejected\n")
        os._exit(72)
    else:
        os._exit(_status)
