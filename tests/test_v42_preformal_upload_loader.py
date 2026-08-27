from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LOADER_PATH = ROOT / "scripts/v42_preformal_upload_loader.py"
RECEIVER_RAW = b"""\
def main_v42r1(**facts):
    required = {
        'plan_id', 'attempt_id', 'loader_sha256', 'loader_byte_count',
        'receiver_sha256', 'receiver_byte_count',
    }
    if set(facts) != required:
        return 72
    return 0
"""


def _command(receiver_raw: bytes = RECEIVER_RAW) -> list[str]:
    loader_raw = LOADER_PATH.read_bytes()
    return [
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-c",
        loader_raw.decode("utf-8"),
        "--preformal-upload",
        hashlib.sha256(loader_raw).hexdigest(),
        str(len(loader_raw)),
        hashlib.sha256(receiver_raw).hexdigest(),
        str(len(receiver_raw)),
        "1" * 64,
        "2" * 64,
    ]


def test_loader_verifies_then_executes_the_exact_receiver() -> None:
    completed = subprocess.run(
        _command(),
        input=RECEIVER_RAW,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={},
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout == b""
    assert completed.stderr == b""


def test_loader_rejects_short_receiver_before_compile() -> None:
    completed = subprocess.run(
        _command(),
        input=RECEIVER_RAW[:-1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={},
        check=False,
    )
    assert completed.returncode == 71
    assert completed.stdout == b""
    assert completed.stderr == b"acfqp v42 preformal loader rejected ingress\n"


def test_loader_rejects_one_hostile_inherited_descriptor() -> None:
    read_fd, write_fd = os.pipe()
    try:
        completed = subprocess.run(
            _command(),
            input=RECEIVER_RAW,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={},
            pass_fds=(read_fd,),
            check=False,
        )
    finally:
        os.close(read_fd)
        os.close(write_fd)
    assert completed.returncode == 71
    assert completed.stdout == b""
