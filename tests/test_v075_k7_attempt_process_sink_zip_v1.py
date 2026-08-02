from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_attempt_process_sink_v1 as sink_v1


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
RUNTIME_SOURCE = SOURCE_ROOT / "acfqp/v075_k7_atomic_pidfd_runtime_v1.py"


def test_disk_runtime_source_pin_retains_resolved_raw_digest() -> None:
    raw = RUNTIME_SOURCE.read_bytes()
    pin = sink_v1._PINNED_RUNTIME_CALLSITE  # noqa: SLF001
    assert pin is not None
    assert pin.function is runtime_v1.run_v075_k7_atomic_pidfd_runtime_v1
    assert pin.source_path == os.fspath(RUNTIME_SOURCE.resolve(strict=True))
    assert pin.source_sha256 == hashlib.sha256(raw).hexdigest()
    assert pin.source_byte_count == len(raw)


def test_strict_fresh_exec_pins_raw_runtime_member_from_proc_fd_zip(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "acfqp-source.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted((SOURCE_ROOT / "acfqp").rglob("*.py")):
            archive.write(path, path.relative_to(SOURCE_ROOT).as_posix())
    archive_raw = archive_path.read_bytes()
    archive_fd = os.memfd_create("acfqp-runtime-pin-zip", os.MFD_CLOEXEC)
    try:
        os.write(archive_fd, archive_raw)
        child_source = r'''
import json
import sys

archive = "/proc/self/fd/" + sys.argv[1]
sys.path.insert(0, archive)
from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime
from acfqp import v075_k7_attempt_process_sink_v1 as sink

pin = sink._PINNED_RUNTIME_CALLSITE
if pin is None or pin.function is not runtime.run_v075_k7_atomic_pidfd_runtime_v1:
    raise SystemExit(71)
sys.stdout.write(json.dumps(pin.provenance(), sort_keys=True))
'''
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                "-c",
                child_source,
                str(archive_fd),
            ],
            check=False,
            capture_output=True,
            env={"LANG": "C", "LC_ALL": "C", "TZ": "UTC"},
            pass_fds=(archive_fd,),
            text=True,
            timeout=60,
        )
    finally:
        os.close(archive_fd)
    assert completed.returncode == 0, completed.stderr
    document = json.loads(completed.stdout)
    runtime_raw = RUNTIME_SOURCE.read_bytes()
    assert document["runtime_source_path"] == (
        f"/proc/self/fd/{archive_fd}/acfqp/"
        "v075_k7_atomic_pidfd_runtime_v1.py"
    )
    assert document["runtime_source_sha256"] == hashlib.sha256(
        runtime_raw
    ).hexdigest()
    assert document["runtime_source_byte_count"] == len(runtime_raw)
    assert document["runtime_code_object_pinned"] is True
    assert document["runtime_globals_mapping_pinned"] is True
