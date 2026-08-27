"""Tiny trusted loader for the V42 pre-formal upload receiver.

This file is transported as a committed Git blob and embedded verbatim in the
single authorized SSH remote command.  It performs no filesystem mutation: it
validates its isolated Python ingress and the exact receiver bytes before the
receiver is compiled or executed.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys


_HEX64 = re.compile(r"[0-9a-f]{64}")
_MAXIMUM_RECEIVER_BYTES = 4 * 1024**2
_EXPECTED_ENVIRONMENT = {"LC_CTYPE": "C.UTF-8"}


class _LoaderFailure(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise _LoaderFailure(message)


def _exact_nonnegative_decimal(value: str, label: str) -> int:
    if not value or value != str(int(value)) or value.startswith("+"):
        _fail(label + " changed")
    return int(value)


def _read_exact(descriptor: int, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = os.read(descriptor, min(remaining, 1024 * 1024))
        if not chunk:
            _fail("receiver source ended early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _live_descriptor_numbers() -> list[int]:
    scanner = os.open(
        "/proc/self/fd",
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        if scanner != 3:
            _fail("loader descriptor scanner was not the sole new descriptor")
        try:
            names = {int(name) for name in os.listdir(scanner)}
        except (OSError, ValueError) as error:
            raise _LoaderFailure("loader descriptor scan failed") from error
        # CPython duplicates the supplied directory FD once for fdopendir and
        # closes that exact duplicate before os.listdir returns.  No arbitrary
        # EBADF entry is ignored: the observed set and the one closed iterator
        # descriptor are both exact parts of the registered runtime contract.
        if names != {0, 1, 2, scanner, scanner + 1}:
            _fail("loader descriptor directory inventory changed")
        for descriptor in (0, 1, 2, scanner):
            os.fstat(descriptor)
        try:
            os.fstat(scanner + 1)
        except OSError as error:
            if error.errno != 9:
                raise
        else:
            _fail("loader iterator descriptor unexpectedly remained live")
    finally:
        os.close(scanner)
    return [0, 1, 2]


def _entry() -> int:
    if sys.argv[0] != "-c" or len(sys.argv) != 8:
        _fail("loader argv changed")
    if sys.argv[1] != "--preformal-upload":
        _fail("loader mode changed")
    if len(sys.orig_argv) != 13:
        _fail("loader original argv arity changed")
    source = sys.orig_argv[5]
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
    source_raw = source.encode("utf-8", errors="strict")
    expected_loader_sha256 = sys.argv[2]
    expected_loader_count = _exact_nonnegative_decimal(
        sys.argv[3], "loader byte count"
    )
    expected_receiver_sha256 = sys.argv[4]
    expected_receiver_count = _exact_nonnegative_decimal(
        sys.argv[5], "receiver byte count"
    )
    plan_id = sys.argv[6]
    attempt_id = sys.argv[7]
    if any(
        _HEX64.fullmatch(value) is None
        for value in (
            expected_loader_sha256,
            expected_receiver_sha256,
            plan_id,
            attempt_id,
        )
    ):
        _fail("loader hash or identity changed")
    if (
        expected_loader_count != len(source_raw)
        or hashlib.sha256(source_raw).hexdigest() != expected_loader_sha256
    ):
        _fail("loader source identity changed")
    if not 0 < expected_receiver_count <= _MAXIMUM_RECEIVER_BYTES:
        _fail("receiver source count exceeds cap")
    if os.environ != _EXPECTED_ENVIRONMENT:
        _fail("loader environment changed")
    if _live_descriptor_numbers() != [0, 1, 2]:
        _fail("loader file descriptor set changed")
    receiver_raw = _read_exact(0, expected_receiver_count)
    if hashlib.sha256(receiver_raw).hexdigest() != expected_receiver_sha256:
        _fail("receiver source hash changed")
    code = compile(
        receiver_raw,
        "<acfqp-v42-preformal-upload-receiver>",
        "exec",
        flags=0,
        dont_inherit=True,
        optimize=0,
    )
    namespace = {
        "__builtins__": __builtins__,
        "__name__": "acfqp_v42_preformal_upload_receiver",
        "__file__": "<acfqp-v42-preformal-upload-receiver>",
        "__package__": None,
    }
    exec(code, namespace, namespace)
    receiver_main = namespace.get("main_v42r1")
    if not callable(receiver_main):
        _fail("receiver entry point changed")
    result = receiver_main(
        plan_id=plan_id,
        attempt_id=attempt_id,
        loader_sha256=expected_loader_sha256,
        loader_byte_count=expected_loader_count,
        receiver_sha256=expected_receiver_sha256,
        receiver_byte_count=expected_receiver_count,
    )
    if type(result) is not int or not 0 <= result <= 255:
        _fail("receiver exit status changed")
    return result


try:
    _status = _entry()
except BaseException:
    os.write(2, b"acfqp v42 preformal loader rejected ingress\n")
    os._exit(71)
else:
    os._exit(_status)
