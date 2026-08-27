"""Execution authority for the V42 remote ordinal-2 successor.

This module deliberately does not mutate the retained V42 ordinal-1 authority.
It presents the small authority interface consumed by the frozen V42 producer
and independent verifier, but binds every document to a new formal identity,
new one-shot roots, a complete archive-derived source manifest, and the one
registered remote host.  The remote source tree need not contain ``.git``:
commit/tree identity is established by the locally-created deterministic
archive and every live byte is rechecked before execution.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import socket
import stat
import sys
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "42.1.0"
FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2"
PREDECESSOR_FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_ORDINAL_1"
PREDECESSOR_SOURCE_COMMIT = "c48f269b6293ad7a1d8f4e6ab5ff1b098357264b"
PREDECESSOR_SOURCE_TREE = "4744cc0638fbfa4cd677c0701f003ce01eed1a86"
GLOBAL_EXECUTION_ORDINAL = 2

REMOTE_HOST_ALIAS = "jtl110gpu2"
REMOTE_HOSTNAME = "erzhu419-Super-Server"
REMOTE_USER = "erzhu419"
REMOTE_UID = 1000
REMOTE_GID = 1000
REMOTE_PYTHON = "/usr/bin/python3"
REMOTE_PYTHON_REALPATH = "/usr/bin/python3.12"
REMOTE_PYTHON_VERSION = (3, 12, 3)
REMOTE_ROOT = Path("/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2")
REMOTE_SOURCE_ROOT = REMOTE_ROOT / "source"
SOURCE_CAPSULE_NAME = "SOURCE_CAPSULE.tar"
SOURCE_MANIFEST_NAME = "EXECUTION_SOURCE_MANIFEST.json"
TRANSPORT_MANIFEST_NAME = "TRANSPORT_MANIFEST.json"
REMOTE_BOOTSTRAP_PYZ_NAME = "REMOTE_BOOTSTRAP.pyz"
REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH = "/proc/self/fd/37"
REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_PATH = "/proc/self/fd/38"
REMOTE_BOOTSTRAP_RUNTIME_PYZ_FD = 37
REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_FD = 38
REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS = 15
PREPARE_HOST_ATTESTATION_NAME = "PREPARE_HOST_ATTESTATION.json"
LAUNCH_HOST_ATTESTATION_NAME = "LAUNCH_HOST_ATTESTATION.json"
LOCAL_LAUNCH_ATTEMPT_NAME = "LOCAL_LAUNCH_ATTEMPT.json"
LOCAL_MATERIALIZATION_ATTEMPT_NAME = "LOCAL_MATERIALIZATION_ATTEMPT.json"
REMOTE_MATERIALIZATION_ATTEMPT_NAME = "MATERIALIZATION_ATTEMPT.json"
MATERIALIZATION_FAILURE_NAME = "MATERIALIZATION_FAILURE.json"
MATERIALIZATION_TERMINAL_NAME = ".V42_REMOTE_ORDINAL2_MATERIALIZATION_TERMINAL.json"

# The ordinal-1 retention closure below is final and committed.  The retained
# non-zero sentinel guard remains part of verification so a future accidental
# reversion to a pre-freeze placeholder disables every formal path.
PREDECESSOR_RETENTION_READY = True
_PENDING_PREDECESSOR_HEX64 = "f" * 64
PREDECESSOR_RETENTION_SOURCE_COMMIT = "0e8cd2fcfe071df376a2b24a440b952963d4dddd"
PREDECESSOR_RETENTION_SOURCE_TREE = "e29f9f17268130ac0022932f7caa9c4c9dc4a42c"
PREDECESSOR_RETENTION_MANIFEST_ID = (
    "5ab73d90b63675fe4255c0bf6cd2116444a52b5b0009cd6cf822f4fbf7b6ce66"
)
PREDECESSOR_RETENTION_MANIFEST_SHA256 = (
    "f6ad2691bd3665ecb20274c3c43abe82dc0c119abf4976c2dd8311da7f9024f6"
)
PREDECESSOR_RETENTION_MANIFEST_BYTE_COUNT = 9_454
PREDECESSOR_INDEPENDENT_VERIFICATION_ID = (
    "6c088a5515a096ce363c7ab9a834d9ed9c22da87a63d4ed59d1d68e78167db3b"
)
PREDECESSOR_INDEPENDENT_VERIFICATION_SHA256 = (
    "f9290bbfe82c7e07b51f54d1022d818c7fe3bd4f11d770f4034c24366b66f373"
)
PREDECESSOR_INDEPENDENT_VERIFICATION_BYTE_COUNT = 3_124
PREDECESSOR_RUNNER_FAILURE_ID = (
    "c5ab25e29efef47c22d2ccbbaa5867f11b51e9fadaecab321e60fc3dc879d354"
)
PREDECESSOR_PREPARE_RECEIPT_ID = (
    "7fd00460ff58f4deacef516e40e3e2fc0f595e24a6db6f44d9baa25af638145c"
)
PREDECESSOR_RUNNER_ATTEMPT_ID = (
    "d42ed122534d87d60135a1c949872766d99ad15eaa1ac61dad6f3f040fddb58e"
)
PREDECESSOR_WORKER_START_ID = (
    "07a39b80b7e29b27af76a1e73ab9bd5df8728a69b07745dd31caa930ed046136"
)
PREDECESSOR_AUTHORITY_CONSUMPTION_ID = (
    "88946c26382cdcc9d8930fd30895df0cc98045e74445d9f3b4c8c3da2d6631b2"
)
PREDECESSOR_RETENTION_MANIFEST_RELATIVE = (
    "retained_evidence/v42_standard_2048_fresh_terminal_ordinal1_failure/"
    "RETENTION_MANIFEST.json"
)
PREDECESSOR_INDEPENDENT_VERIFICATION_RELATIVE = (
    "retained_evidence/v42_standard_2048_fresh_terminal_ordinal1_failure/"
    "INDEPENDENT_VERIFICATION.json"
)

# The two registered episodes execute concurrently under the frozen V42
# scientific contract.  These conservative gates prevent a second execution
# on a host resembling the memory-starved ordinal-1 environment.  A no-swap
# host is allowed only when the high-RAM gates pass; a configured swap device
# must retain the exact usable capacity of a conventional nominal 8-GiB swap
# area whose kernel-reported capacity is one 4096-byte metadata page smaller.
# The raw observation is never rounded: this threshold passes, one byte less
# fails.
MINIMUM_MEMORY_TOTAL_BYTES = 128 * 1024**3
MINIMUM_MEMORY_AVAILABLE_BYTES = 96 * 1024**3
MINIMUM_SWAP_FREE_BYTES = 8 * 1024**3 - 4096
MINIMUM_FILESYSTEM_AVAILABLE_BYTES = 16 * 1024**3

AUTHORITY_ROOT_RELATIVE = (
    ".tmp/exact-freeze/v42-standard-2048-remote-ordinal2-authority"
)
EVIDENCE_ROOT_RELATIVE = (
    ".tmp/exact-freeze/v42-standard-2048-remote-ordinal2-evidence"
)
PREPARE_RECEIPT_NAME = "PREPARE_RECEIPT.json"
PREPARE_ATTEMPT_JOURNAL_NAME = ".V42_REMOTE_ORDINAL2_PREPARE_ATTEMPT.json"
PREPARE_FAILURE_JOURNAL_NAME = ".V42_REMOTE_ORDINAL2_PREPARE_FAILURE.json"
LAUNCH_ATTEMPT_JOURNAL_NAME = ".V42_REMOTE_ORDINAL2_LAUNCH_ATTEMPT.json"
LAUNCH_FAILURE_JOURNAL_NAME = ".V42_REMOTE_ORDINAL2_LAUNCH_FAILURE.json"
ATTEMPT_NAME = "ATTEMPT.json"
WORKER_START_NAME = "WORKER_START.json"
AUTHORITY_CONSUMPTION_NAME = "AUTHORITY_CONSUMPTION.json"
CAMPAIGN_NAME = "CAMPAIGN.json"
VERIFICATION_NAME = "VERIFICATION.json"
TERMINAL_NAME = "TERMINAL.json"
FAILURE_NAME = "FAILURE.json"
SUPERVISOR_STDOUT_NAME = "SUPERVISOR_STDOUT.bin"
SUPERVISOR_STDERR_NAME = "SUPERVISOR_STDERR.bin"

# These names are deliberately outside the immutable Git-derived transport
# inventory.  The two directory prefixes must be absent from the committed
# source tree: they are populated only by the one-shot prepare/launch state
# machines after the capsule has been materialized.  Keeping the exceptions
# exact is important because the repository itself contains hundreds of
# committed ``.tmp/**`` artifacts which remain ordinary immutable transport
# members and must never be skipped wholesale.
_RESERVED_TRANSPORT_ROOT_FILES = frozenset(
    {
        MATERIALIZATION_TERMINAL_NAME,
        PREPARE_ATTEMPT_JOURNAL_NAME,
        PREPARE_FAILURE_JOURNAL_NAME,
        LAUNCH_ATTEMPT_JOURNAL_NAME,
        LAUNCH_FAILURE_JOURNAL_NAME,
    }
)
_MUTABLE_STATE_FILES_BY_ROOT = {
    AUTHORITY_ROOT_RELATIVE: {PREPARE_RECEIPT_NAME: 64 * 1024**2},
    EVIDENCE_ROOT_RELATIVE: {
        ATTEMPT_NAME: 4 * 1024**2,
        WORKER_START_NAME: 4 * 1024**2,
        AUTHORITY_CONSUMPTION_NAME: 4 * 1024**2,
        CAMPAIGN_NAME: 1024**3,
        VERIFICATION_NAME: 64 * 1024**2,
        TERMINAL_NAME: 4 * 1024**2,
        FAILURE_NAME: 4 * 1024**2,
        SUPERVISOR_STDOUT_NAME: 1024**3,
        SUPERVISOR_STDERR_NAME: 4 * 1024**2,
    },
}

SOURCE_MANIFEST_SCHEMA = "acfqp.v42_remote_ordinal2_source_manifest.v42r1"
TRANSPORT_MANIFEST_SCHEMA = "acfqp.v42_remote_ordinal2_transport_manifest.v42r1"
REMOTE_BOOTSTRAP_PYZ_ARTIFACT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_remote_bootstrap_pyz_artifact.v42r1"
)
REMOTE_BOOTSTRAP_RUNTIME_BINDING_SCHEMA = (
    "acfqp.v42_remote_ordinal2_remote_bootstrap_runtime_binding.v42r1"
)
REMOTE_BOOTSTRAP_LAUNCHER_EVIDENCE_SCHEMA = (
    "acfqp.v42_remote_ordinal2_remote_bootstrap_launcher_evidence.v42r1"
)
HOST_ATTESTATION_SCHEMA = "acfqp.v42_remote_ordinal2_host_attestation.v42r1"
PREDECESSOR_BINDING_SCHEMA = "acfqp.v42_remote_ordinal2_predecessor_binding.v42r1"
PREPARE_RECEIPT_SCHEMA = "acfqp.v42_remote_ordinal2_prepare_receipt.v42r1"
RUNNER_ATTEMPT_SCHEMA = "acfqp.v42_remote_ordinal2_runner_attempt.v42r1"
WORKER_START_SCHEMA = "acfqp.v42_remote_ordinal2_worker_start.v42r1"
AUTHORITY_CONSUMPTION_SCHEMA = (
    "acfqp.v42_remote_ordinal2_authority_consumption.v42r1"
)
SOURCE_BINDING_SCHEMA = "acfqp.v42_remote_ordinal2_source_binding.v42r1"
LOCAL_LAUNCH_ATTEMPT_SCHEMA = "acfqp.v42_remote_ordinal2_local_launch_attempt.v42r1"
LOCAL_MATERIALIZATION_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_local_materialization_attempt.v42r1"
)
REMOTE_MATERIALIZATION_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_remote_materialization_attempt.v42r1"
)
MATERIALIZATION_TERMINAL_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_terminal.v42r1"
)
MATERIALIZATION_FAILURE_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_failure.v42r1"
)

SOURCE_RESOLVER_VERSION = "PYTHON_STATIC_IMPORT_CLOSURE_V2_REMOTE_ORDINAL2"
SOURCE_CLOSURE_SCOPE = "COMMITTED_REPOSITORY_PYTHON_SOURCE_ONLY"
TRANSPORT_SCOPE = "ALL_COMMITTED_REGULAR_FILES_IN_DETERMINISTIC_USTAR"
TRANSPORT_ARCHIVE_FORMAT = "USTAR_REGULAR_ONLY_SORTED_MTIME0_UID0_GID0_V1"
MATERIALIZED_SOURCE_FILE_MODE = "0444"
REMOTE_BOOTSTRAP_PYZ_FORMAT = (
    "ZIP_STORED_SORTED_DOS1980_UNIX_REGULAR_0444_NO_EXTRA_NO_COMMENT_V1"
)
REMOTE_BOOTSTRAP_PYZ_FILE_MODE = "0400"
REMOTE_BOOTSTRAP_PYZ_MEMBER_MODE = "0444"

# These are the exact generated bytes admitted into the bootstrap archive.  In
# particular, the builder does not accept a caller-supplied digest for either
# generated member.  The stdlib-only main verifies the five fixed controls and
# the complete ZIP inventory before importing any application module from the
# archive.  It deliberately contains no transport-manifest ID or self hash, so
# the outer transport manifest can bind the finished pyz without a hash cycle.
REMOTE_BOOTSTRAP_GENERATED_EMPTY_PACKAGE_SHIM_BYTES = b""
# This exact outer program is supplied through ``python -c``.  Unlike a pyz
# main, it executes from interpreter argv rather than from the untrusted ZIP.
# It verifies the out-of-band transport/pyz anchors, reads all five controls
# through no-follow descriptors, validates the entire ZIP, and only then
# copies those verified bytes into sealed memfd 37.  Sealed canonical evidence
# is passed independently in memfd 38 before execing the inner interpreter.
REMOTE_BOOTSTRAP_TRUSTED_LAUNCHER_BYTES = r'''import fcntl
import hashlib
import io
import json
import os
import pwd
import socket
import stat
import sys
import zipfile

FORMAL_ROOT = "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2"
PYTHON = "/usr/bin/python3"
PYTHON_REALPATH = "/usr/bin/python3.12"
PYZ_NAME = "REMOTE_BOOTSTRAP.pyz"
PYZ_RUNTIME_PATH = "/proc/self/fd/37"
EVIDENCE_RUNTIME_PATH = "/proc/self/fd/38"
MODE_FORMAL = "--materialize-remote-capsule"
MODE_SELF_TEST = "--self-test-bootstrap-runtime"
CONTROL_NAMES = (
    "EXECUTION_SOURCE_MANIFEST.json",
    "LOCAL_MATERIALIZATION_ATTEMPT.json",
    PYZ_NAME,
    "SOURCE_CAPSULE.tar",
    "TRANSPORT_MANIFEST.json",
)
ARCHIVE_PATHS = (
    "__main__.py",
    "acfqp/__init__.py",
    "acfqp/construction_k7_domain_registry_extension_v42.py",
    "acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
    "acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
    "acfqp/phase3e_ids.py",
    "scripts/__init__.py",
    "scripts/bootstrap_v42_standard_2048_remote_ordinal2.py",
)
SEALS = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE


def fail(message):
    raise RuntimeError("V42 trusted bootstrap launcher: " + message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("duplicate JSON key")
        result[key] = value
    return result


def canonical_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")


def canonical(raw):
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=unique_object,
            parse_constant=lambda token: fail("nonfinite JSON"),
        )
    except (UnicodeError, ValueError, TypeError) as error:
        fail("invalid JSON: " + str(error))
    if canonical_bytes(value) != raw:
        fail("noncanonical JSON")
    return value


def content_id(domain, value):
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + canonical_bytes(value)).hexdigest()


def verify_id(document, key, domain):
    if type(document) is not dict or type(document.get(key)) is not str:
        fail("content document schema changed")
    payload = dict(document)
    observed = payload.pop(key)
    if observed != content_id(domain, payload):
        fail("content document identity changed")


def identity(observed):
    return (
        observed.st_dev, observed.st_ino, observed.st_mode, observed.st_uid,
        observed.st_gid, observed.st_nlink, observed.st_size,
        observed.st_mtime_ns, observed.st_ctime_ns,
    )


def directory_identity(observed):
    return (
        observed.st_dev, observed.st_ino, observed.st_mode,
        observed.st_uid, observed.st_gid,
    )


def open_root(root, expected_uid):
    if not root.startswith("/") or os.path.normpath(root) != root:
        fail("control root path changed")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open("/", flags)
    chain = [("/", directory_identity(os.fstat(descriptor)))]
    try:
        prefix = ""
        for component in root.split("/")[1:]:
            prefix += "/" + component
            before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                fail("control root ancestor is redirected")
            child = os.open(component, flags, dir_fd=descriptor)
            opened = os.fstat(child)
            if directory_identity(before) != directory_identity(opened):
                os.close(child)
                fail("control root ancestor changed while opening")
            chain.append((prefix, directory_identity(opened)))
            os.close(descriptor)
            descriptor = child
        root_observed = os.fstat(descriptor)
        if stat.S_IMODE(root_observed.st_mode) != 0o700 or root_observed.st_uid != expected_uid:
            fail("control root mode or owner changed")
        return descriptor, root_observed, tuple(chain)
    except BaseException:
        os.close(descriptor)
        raise


def read_at(root_fd, name, maximum, expected_uid):
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root_fd)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode) or stat.S_IMODE(before.st_mode) != 0o400
            or before.st_uid != expected_uid or before.st_nlink != 1
            or before.st_size > maximum
        ):
            fail("control file metadata changed")
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                fail("control file exceeds cap")
        after = os.fstat(descriptor)
        if identity(before) != identity(after) or total != before.st_size:
            fail("control file changed during read")
    finally:
        os.close(descriptor)
    final = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    if identity(before) != identity(final):
        fail("control file name changed during read")
    return b"".join(chunks), identity(before)


def verify_zip(raw, artifact):
    members = artifact.get("members")
    if type(members) is not list or tuple(row.get("archive_path") for row in members) != ARCHIVE_PATHS:
        fail("pyz member manifest changed")
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            infos = archive.infolist()
            if archive.comment != b"" or tuple(info.filename for info in infos) != ARCHIVE_PATHS:
                fail("pyz ZIP inventory changed")
            for info, row in zip(infos, members):
                if (
                    info.date_time != (1980, 1, 1, 0, 0, 0)
                    or info.compress_type != zipfile.ZIP_STORED or info.create_system != 3
                    or info.create_version != 20 or info.extract_version != 20
                    or info.flag_bits != 0 or info.extra != b"" or info.comment != b""
                    or info.internal_attr != 0
                    or info.external_attr >> 16 != stat.S_IFREG | 0o444
                ):
                    fail("pyz ZIP member metadata changed")
                member_raw = archive.read(info)
                if (
                    len(member_raw) != row.get("byte_count")
                    or hashlib.sha256(member_raw).hexdigest() != row.get("sha256")
                ):
                    fail("pyz ZIP member bytes changed")
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        fail("invalid pyz ZIP: " + str(error))


def write_all(descriptor, raw):
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            fail("memfd short write")
        view = view[written:]


def sealed_memfd(name, raw, target_fd):
    descriptor = os.memfd_create(name, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        os.fchmod(descriptor, 0o400)
        write_all(descriptor, raw)
        os.lseek(descriptor, 0, os.SEEK_SET)
        fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, SEALS)
        if fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != SEALS:
            fail("memfd seals changed")
        observed = os.fstat(descriptor)
        check = os.read(descriptor, len(raw) + 1)
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o400
            or observed.st_uid != os.geteuid() or observed.st_gid != os.getegid()
            or observed.st_nlink != 0
            or observed.st_size != len(raw) or check != raw
        ):
            fail("sealed memfd bytes changed")
        if descriptor != target_fd:
            os.dup2(descriptor, target_fd, inheritable=True)
        else:
            os.set_inheritable(descriptor, True)
        target = os.fstat(target_fd)
        os.lseek(target_fd, 0, os.SEEK_SET)
        target_raw = os.read(target_fd, len(raw) + 1)
        if (
            target.st_ino != observed.st_ino or target.st_dev != observed.st_dev
            or target.st_size != observed.st_size or target_raw != raw
            or fcntl.fcntl(target_fd, fcntl.F_GET_SEALS) != SEALS
            or stat.S_IMODE(target.st_mode) != 0o400
            or target.st_uid != os.geteuid() or target.st_gid != os.getegid()
            or os.get_inheritable(target_fd) is not True
        ):
            fail("fixed inherited memfd changed")
        os.lseek(target_fd, 0, os.SEEK_SET)
    finally:
        if descriptor != target_fd:
            os.close(descriptor)


def main():
    if len(sys.argv) != 6:
        fail("outer argument count changed")
    root, mode, expected_transport_id, expected_pyz_sha, expected_pyz_count = sys.argv[1:]
    if mode not in {MODE_FORMAL, MODE_SELF_TEST}:
        fail("outer mode changed")
    if len(expected_transport_id) != 64 or len(expected_pyz_sha) != 64:
        fail("outer content anchor changed")
    try:
        expected_pyz_count = int(expected_pyz_count)
    except ValueError:
        fail("outer pyz byte count changed")
    formal = mode == MODE_FORMAL
    if formal and (
        root != FORMAL_ROOT or socket.gethostname() != "erzhu419-Super-Server"
        or pwd.getpwuid(os.geteuid()).pw_name != "erzhu419" or os.geteuid() != 1000
        or os.getegid() != 1000
        or sys.executable != PYTHON or os.path.realpath(sys.executable) != PYTHON_REALPATH
        or tuple(sys.version_info[:3]) != (3, 12, 3)
    ):
        fail("formal outer host or Python changed")
    if sys.flags.isolated != 1 or sys.flags.no_site != 1 or sys.dont_write_bytecode is not True:
        fail("outer Python flags changed")
    expected_uid = 1000 if formal else os.geteuid()
    root_fd, root_before, chain_before = open_root(root, expected_uid)
    facts = {}
    try:
        if tuple(sorted(os.listdir(root_fd))) != CONTROL_NAMES:
            fail("outer five-control inventory changed")
        source_raw, facts[CONTROL_NAMES[0]] = read_at(root_fd, CONTROL_NAMES[0], 64 * 1024**2, expected_uid)
        local_raw, facts[CONTROL_NAMES[1]] = read_at(root_fd, CONTROL_NAMES[1], 4 * 1024**2, expected_uid)
        pyz_raw, facts[CONTROL_NAMES[2]] = read_at(root_fd, CONTROL_NAMES[2], 64 * 1024**2, expected_uid)
        capsule_raw, facts[CONTROL_NAMES[3]] = read_at(root_fd, CONTROL_NAMES[3], 2 * 1024**3, expected_uid)
        transport_raw, facts[CONTROL_NAMES[4]] = read_at(root_fd, CONTROL_NAMES[4], 64 * 1024**2, expected_uid)
        source = canonical(source_raw)
        local = canonical(local_raw)
        transport = canonical(transport_raw)
        launcher_source = sys.orig_argv[5]
        expected_actual_outer = [
            PYTHON, "-I", "-S", "-B", "-c", launcher_source, root, mode,
            expected_transport_id, expected_pyz_sha, str(expected_pyz_count),
        ]
        expected_formal_outer = [
            PYTHON, "-I", "-S", "-B", "-c", launcher_source, FORMAL_ROOT,
            MODE_FORMAL, expected_transport_id, expected_pyz_sha,
            str(expected_pyz_count),
        ]
        verify_id(source, "source_manifest_id", "acfqp:v42-remote-ordinal2:source-manifest")
        verify_id(transport, "transport_manifest_id", "acfqp:v42-remote-ordinal2:transport-manifest")
        verify_id(local, "local_materialization_attempt_id", "acfqp:v42-remote-ordinal2:local-materialization-attempt")
        artifact = transport.get("remote_bootstrap_pyz_artifact")
        verify_id(artifact, "remote_bootstrap_pyz_artifact_id", "acfqp:v42-remote-ordinal2:remote-bootstrap-pyz-artifact")
        if (
            transport.get("transport_manifest_id") != expected_transport_id
            or artifact.get("pyz_sha256") != expected_pyz_sha
            or artifact.get("pyz_byte_count") != expected_pyz_count
            or hashlib.sha256(pyz_raw).hexdigest() != expected_pyz_sha
            or len(pyz_raw) != expected_pyz_count
            or hashlib.sha256(capsule_raw).hexdigest() != transport.get("source_archive_sha256")
            or len(capsule_raw) != transport.get("source_archive_byte_count")
            or source.get("source_manifest_id") != transport.get("execution_source_manifest_id")
            or local.get("source_manifest_id") != source.get("source_manifest_id")
            or local.get("transport_manifest_id") != expected_transport_id
            or local.get("remote_bootstrap_pyz_sha256") != expected_pyz_sha
            or local.get("remote_bootstrap_pyz_byte_count") != expected_pyz_count
            or list(sys.orig_argv) != expected_actual_outer
            or local.get("remote_bootstrap_outer_command") != expected_formal_outer
        ):
            fail("outer dynamic anchor or control join changed")
        verify_zip(pyz_raw, artifact)
        if (
            local.get("remote_bootstrap_trusted_launcher_sha256")
            != hashlib.sha256(launcher_source.encode("utf-8")).hexdigest()
            or local.get("remote_bootstrap_trusted_launcher_byte_count")
            != len(launcher_source.encode("utf-8"))
        ):
            fail("trusted launcher bytes changed")
        inner_command = [
            PYTHON, "-I", "-S", "-B", PYZ_RUNTIME_PATH,
            MODE_FORMAL if formal else MODE_SELF_TEST,
            expected_transport_id, expected_pyz_sha, str(expected_pyz_count),
        ]
        if formal and local.get("remote_bootstrap_inner_command") != inner_command:
            fail("local attempt inner command differs from trusted launcher constants")
        evidence_payload = {
            "schema": "acfqp.v42_remote_ordinal2_remote_bootstrap_launcher_evidence.v42r1",
            "schema_version": "42.1.0",
            "formal_identity": "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2",
            "global_execution_ordinal": 2,
            "execution_mode": "FORMAL_MATERIALIZATION" if formal else "LOCAL_SELF_TEST",
            "source_manifest_id": source["source_manifest_id"],
            "transport_manifest_id": expected_transport_id,
            "local_materialization_attempt_id": local["local_materialization_attempt_id"],
            "remote_bootstrap_pyz_artifact_id": artifact["remote_bootstrap_pyz_artifact_id"],
            "remote_bootstrap_pyz_member_manifest_id": artifact["member_manifest_id"],
            "remote_bootstrap_pyz_sha256": expected_pyz_sha,
            "remote_bootstrap_pyz_byte_count": expected_pyz_count,
            "remote_bootstrap_pyz_fixed_path": root + "/" + PYZ_NAME,
            "remote_bootstrap_pyz_runtime_path": PYZ_RUNTIME_PATH,
            "remote_bootstrap_runtime_evidence_path": EVIDENCE_RUNTIME_PATH,
            "trusted_launcher_sha256": hashlib.sha256(launcher_source.encode("utf-8")).hexdigest(),
            "trusted_launcher_byte_count": len(launcher_source.encode("utf-8")),
            "observed_outer_python_command": list(sys.orig_argv),
            "authorized_inner_python_command": inner_command,
            "observed_outer_hostname": socket.gethostname(),
            "observed_outer_user": pwd.getpwuid(os.geteuid()).pw_name,
            "observed_outer_uid": os.geteuid(),
            "observed_outer_gid": os.getegid(),
            "observed_outer_python_invocation": sys.executable,
            "observed_outer_python_realpath": os.path.realpath(sys.executable),
            "observed_outer_python_version": list(sys.version_info[:3]),
            "outer_python_isolated_flag": sys.flags.isolated,
            "outer_python_no_site_flag": sys.flags.no_site,
            "outer_python_dont_write_bytecode": sys.dont_write_bytecode,
            "outer_five_control_verification_completed": True,
            "outer_pyz_nofollow_stable_hash_completed": True,
            "outer_lexical_chain": [
                {"absolute_path": path, "identity": list(observed_identity)}
                for path, observed_identity in chain_before
            ],
            "outer_root_identity": list(identity(root_before)),
            "outer_root_inventory": list(CONTROL_NAMES),
            "outer_five_control_identities": {
                name: list(observed_identity)
                for name, observed_identity in sorted(facts.items())
            },
            "runtime_pyz_memfd": 37,
            "runtime_evidence_memfd": 38,
            "required_memfd_seals": SEALS,
            "required_memfd_mode": "0400",
            "runtime_memfd_uid": os.geteuid(),
            "runtime_memfd_gid": os.getegid(),
            "runtime_memfds_inheritable_for_inner_exec": True,
            "fixed_identity_effect_started": False,
        }
        evidence = {
            **evidence_payload,
            "remote_bootstrap_launcher_evidence_id": content_id(
                "acfqp:v42-remote-ordinal2:remote-bootstrap-launcher-evidence", evidence_payload
            ),
        }
        evidence_raw = canonical_bytes(evidence)
        sealed_memfd("acfqp-v42-remote-bootstrap-pyz", pyz_raw, 37)
        sealed_memfd("acfqp-v42-remote-bootstrap-evidence", evidence_raw, 38)
        if identity(os.fstat(root_fd)) != identity(root_before) or tuple(sorted(os.listdir(root_fd))) != CONTROL_NAMES:
            fail("control root changed before inner exec")
        for name, before in facts.items():
            if identity(os.stat(name, dir_fd=root_fd, follow_symlinks=False)) != before:
                fail("control file changed before inner exec")
        final_fd, final_root, chain_after = open_root(root, expected_uid)
        try:
            if chain_after != chain_before or identity(final_root) != identity(root_before):
                fail("control root ancestor changed before inner exec")
        finally:
            os.close(final_fd)
    finally:
        os.close(root_fd)
    os.execve(PYTHON, inner_command, {})


main()
'''.encode("utf-8")

# The inner main executes only from the sealed memfd established above.  It
# removes the pyz entry before importing stdlib, validates both sealed FDs and
# the exact inner argv, and restores the verified memfd path only for the eight
# admitted application modules.
REMOTE_BOOTSTRAP_GENERATED_MAIN_BYTES = r'''import sys
_PYZ_RUNTIME_PATH = sys.path[0]
if _PYZ_RUNTIME_PATH != "/proc/self/fd/37":
    raise RuntimeError("V42 remote bootstrap inner pyz path changed")
del sys.path[0]

import fcntl
import hashlib
import importlib
import json
import os
import pwd
import socket
import stat

PYTHON = "/usr/bin/python3"
PYTHON_REALPATH = "/usr/bin/python3.12"
PYZ_RUNTIME_PATH = "/proc/self/fd/37"
EVIDENCE_RUNTIME_PATH = "/proc/self/fd/38"
MODE_FORMAL = "--materialize-remote-capsule"
MODE_SELF_TEST = "--self-test-bootstrap-runtime"
SEALS = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
MODULES = (
    ("__main__", "__main__.py"),
    ("acfqp", "acfqp/__init__.py"),
    ("acfqp.construction_k7_domain_registry_extension_v42", "acfqp/construction_k7_domain_registry_extension_v42.py"),
    ("acfqp.construction_k7_standard_2048_process_supervision_v42r1", "acfqp/construction_k7_standard_2048_process_supervision_v42r1.py"),
    ("acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1", "acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py"),
    ("acfqp.phase3e_ids", "acfqp/phase3e_ids.py"),
    ("scripts", "scripts/__init__.py"),
    ("scripts.bootstrap_v42_standard_2048_remote_ordinal2", "scripts/bootstrap_v42_standard_2048_remote_ordinal2.py"),
)


def fail(message):
    raise RuntimeError("V42 sealed bootstrap inner: " + message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("duplicate evidence JSON key")
        result[key] = value
    return result


def canonical_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")


def canonical(raw):
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=unique_object,
            parse_constant=lambda token: fail("nonfinite evidence JSON"),
        )
    except (UnicodeError, ValueError, TypeError) as error:
        fail("invalid evidence JSON: " + str(error))
    if canonical_bytes(value) != raw:
        fail("evidence JSON is not canonical")
    return value


def content_id(domain, value):
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + canonical_bytes(value)).hexdigest()


def read_sealed_fd(descriptor, maximum):
    observed = os.fstat(descriptor)
    if (
        not stat.S_ISREG(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o400
        or observed.st_uid != os.geteuid() or observed.st_gid != os.getegid()
        or observed.st_nlink != 0
        or os.get_inheritable(descriptor) is not True
        or observed.st_size > maximum
        or fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != SEALS
    ):
        fail("sealed runtime descriptor metadata changed")
    chunks = []
    total = 0
    while True:
        chunk = os.pread(
            descriptor, min(1024 * 1024, maximum + 1 - total), total
        )
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > maximum:
            fail("sealed runtime descriptor exceeds cap")
    after = os.fstat(descriptor)
    if (
        (observed.st_dev, observed.st_ino, observed.st_mode, observed.st_size)
        != (after.st_dev, after.st_ino, after.st_mode, after.st_size)
    ):
        fail("sealed runtime descriptor changed during read")
    return b"".join(chunks)


def stdlib_origins():
    return [
        {"module_name": name, "observed_origin": sys.modules[name].__spec__.origin}
        for name in ("pwd", "socket", "sys")
    ]


def loaded_origins():
    result = []
    for module_name, archive_path in MODULES:
        module = sys.modules.get(module_name)
        observed = None if module is None or module.__spec__ is None else module.__spec__.origin
        expected = PYZ_RUNTIME_PATH + "/" + archive_path
        if observed != expected or getattr(module, "__file__", None) != expected:
            fail("application module did not load from sealed memfd 37: " + module_name)
        result.append({
            "module_name": module_name,
            "archive_path": archive_path,
            "observed_origin": observed,
        })
    return result


def main():
    if len(sys.argv) != 5 or sys.argv[1] not in {MODE_FORMAL, MODE_SELF_TEST}:
        fail("inner argument schema changed")
    mode, expected_transport_id, expected_pyz_sha, expected_pyz_count = sys.argv[1:]
    try:
        expected_pyz_count = int(expected_pyz_count)
    except ValueError:
        fail("inner pyz byte count changed")
    evidence_raw = read_sealed_fd(38, 64 * 1024**2)
    evidence = canonical(evidence_raw)
    if type(evidence) is not dict or type(evidence.get("remote_bootstrap_launcher_evidence_id")) is not str:
        fail("launcher evidence schema changed")
    payload = dict(evidence)
    evidence_id = payload.pop("remote_bootstrap_launcher_evidence_id")
    if evidence_id != content_id(
        "acfqp:v42-remote-ordinal2:remote-bootstrap-launcher-evidence", payload
    ):
        fail("launcher evidence identity changed")
    pyz_raw = read_sealed_fd(37, 64 * 1024**2)
    if (
        evidence.get("execution_mode")
        != ("FORMAL_MATERIALIZATION" if mode == MODE_FORMAL else "LOCAL_SELF_TEST")
        or evidence.get("transport_manifest_id") != expected_transport_id
        or evidence.get("remote_bootstrap_pyz_sha256") != expected_pyz_sha
        or evidence.get("remote_bootstrap_pyz_byte_count") != expected_pyz_count
        or hashlib.sha256(pyz_raw).hexdigest() != expected_pyz_sha
        or len(pyz_raw) != expected_pyz_count
        or evidence.get("authorized_inner_python_command") != list(sys.orig_argv)
        or evidence.get("remote_bootstrap_pyz_runtime_path") != PYZ_RUNTIME_PATH
        or evidence.get("remote_bootstrap_runtime_evidence_path") != EVIDENCE_RUNTIME_PATH
        or evidence.get("runtime_pyz_memfd") != 37
        or evidence.get("runtime_evidence_memfd") != 38
        or evidence.get("required_memfd_seals") != SEALS
        or evidence.get("required_memfd_mode") != "0400"
        or evidence.get("runtime_memfd_uid") != os.geteuid()
        or evidence.get("runtime_memfd_gid") != os.getegid()
        or evidence.get("runtime_memfds_inheritable_for_inner_exec") is not True
        or evidence.get("outer_five_control_verification_completed") is not True
        or evidence.get("outer_pyz_nofollow_stable_hash_completed") is not True
        or evidence.get("fixed_identity_effect_started") is not False
    ):
        fail("inner sealed evidence or dynamic anchor changed")
    formal = mode == MODE_FORMAL
    if formal and (
        socket.gethostname() != "erzhu419-Super-Server"
        or pwd.getpwuid(os.geteuid()).pw_name != "erzhu419" or os.geteuid() != 1000
        or os.getegid() != 1000
        or sys.executable != PYTHON or os.path.realpath(sys.executable) != PYTHON_REALPATH
        or tuple(sys.version_info[:3]) != (3, 12, 3)
        or sys.flags.isolated != 1 or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
    ):
        fail("formal inner host or Python changed")
    sys.path.insert(0, PYZ_RUNTIME_PATH)
    bootstrap = importlib.import_module("scripts.bootstrap_v42_standard_2048_remote_ordinal2")
    remote_authority = importlib.import_module(
        "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1"
    )
    origins = loaded_origins()
    if not formal:
        result = {
            "schema": "acfqp.v42_remote_ordinal2_bootstrap_pyz_self_test.v42r1",
            "transport_manifest_id": expected_transport_id,
            "remote_bootstrap_pyz_sha256": expected_pyz_sha,
            "remote_bootstrap_pyz_byte_count": expected_pyz_count,
            "remote_bootstrap_launcher_evidence_id": evidence_id,
            "loaded_application_module_origins": origins,
            "trusted_outer_launcher_verified": True,
            "sealed_memfd_runtime_verified": True,
            "remote_materialization_attempt_published": False,
        }
        sys.stdout.buffer.write(canonical_bytes(result) + b"\n")
        return 0
    source, transport, local_attempt = (
        bootstrap.read_verified_remote_bootstrap_controls_for_runtime_v42r1(evidence)
    )
    binding = remote_authority.build_remote_bootstrap_runtime_binding_v42r1(
        transport,
        source_manifest=source,
        local_materialization_attempt=local_attempt,
        trusted_launcher_evidence=evidence,
        observed_hostname=socket.gethostname(),
        observed_user=pwd.getpwuid(os.geteuid()).pw_name,
        observed_uid=os.geteuid(),
        observed_python_invocation=sys.executable,
        observed_python_realpath=os.path.realpath(sys.executable),
        observed_python_version=tuple(sys.version_info[:3]),
        observed_inner_python_command=list(sys.orig_argv),
        python_isolated_flag=sys.flags.isolated,
        python_no_site_flag=sys.flags.no_site,
        python_dont_write_bytecode=sys.dont_write_bytecode,
        observed_remote_bootstrap_pyz_fixed_path=evidence["remote_bootstrap_pyz_fixed_path"],
        observed_remote_bootstrap_pyz_runtime_path=PYZ_RUNTIME_PATH,
        observed_remote_bootstrap_pyz_sha256=expected_pyz_sha,
        observed_remote_bootstrap_pyz_byte_count=expected_pyz_count,
        observed_member_manifest_id=evidence["remote_bootstrap_pyz_member_manifest_id"],
        runtime_pyz_memfd_seals=fcntl.fcntl(37, fcntl.F_GET_SEALS),
        runtime_evidence_memfd_seals=fcntl.fcntl(38, fcntl.F_GET_SEALS),
        runtime_pyz_memfd_mode="0400",
        runtime_evidence_memfd_mode="0400",
        runtime_pyz_memfd_uid=os.fstat(37).st_uid,
        runtime_pyz_memfd_gid=os.fstat(37).st_gid,
        runtime_evidence_memfd_uid=os.fstat(38).st_uid,
        runtime_evidence_memfd_gid=os.fstat(38).st_gid,
        runtime_memfds_inheritable=True,
        observed_stdlib_module_origins=stdlib_origins(),
        loaded_application_module_origins=origins,
    )
    bootstrap.install_remote_bootstrap_runtime_binding_v42r1(binding)
    return bootstrap.main([MODE_FORMAL])


if __name__ == "__main__":
    raise SystemExit(main())
'''.encode("utf-8")

REMOTE_BOOTSTRAP_STDLIB_MODULE_ORIGINS = (
    {"module_name": "pwd", "observed_origin": "built-in"},
    {
        "module_name": "socket",
        "observed_origin": "/usr/lib/python3.12/socket.py",
    },
    {"module_name": "sys", "observed_origin": "built-in"},
)

# The pyz is a transport bootstrap, not the scientific execution closure.  Its
# committed application members are drawn from the exact source manifest; the
# two empty package shims and stdlib-only __main__ are generated deterministically
# so importing ``acfqp`` cannot execute the repository's broad package initializer
# before the fixed manifest and pyz bytes have been verified.
REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS = (
    ("__main__.py", "__main__", "GENERATED_STDLIB_MAIN", None),
    ("acfqp/__init__.py", "acfqp", "GENERATED_EMPTY_PACKAGE_SHIM", None),
    (
        "acfqp/construction_k7_domain_registry_extension_v42.py",
        "acfqp.construction_k7_domain_registry_extension_v42",
        "COMMITTED_GIT_BLOB",
        "src/acfqp/construction_k7_domain_registry_extension_v42.py",
    ),
    (
        "acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
        "acfqp.construction_k7_standard_2048_process_supervision_v42r1",
        "COMMITTED_GIT_BLOB",
        "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
    ),
    (
        "acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
        "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1",
        "COMMITTED_GIT_BLOB",
        "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
    ),
    (
        "acfqp/phase3e_ids.py",
        "acfqp.phase3e_ids",
        "COMMITTED_GIT_BLOB",
        "src/acfqp/phase3e_ids.py",
    ),
    (
        "scripts/__init__.py",
        "scripts",
        "COMMITTED_GIT_BLOB",
        "scripts/__init__.py",
    ),
    (
        "scripts/bootstrap_v42_standard_2048_remote_ordinal2.py",
        "scripts.bootstrap_v42_standard_2048_remote_ordinal2",
        "COMMITTED_GIT_BLOB",
        "scripts/bootstrap_v42_standard_2048_remote_ordinal2.py",
    ),
)

FORMAL_REMOTE_SOURCE_ROOTS = (
    "src/acfqp/__init__.py",
    "src/acfqp/construction_k7_domain_registry_extension_v42.py",
    "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
    "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
    "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
    "src/acfqp/phase3e_ids.py",
    "src/acfqp/construction_k7_standard_2048_execution_authority_v42.py",
    "src/acfqp/construction_k7_standard_2048_fresh_terminal_campaign_v42.py",
    "src/acfqp/construction_k7_standard_2048_fresh_terminal_independent_verifier_v42.py",
    "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
    "src/acfqp/construction_k7_standard_2048_observation_proposed_program_v14.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_target_v35.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_independent_verifier_v35.py",
    "src/acfqp/construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14.py",
    "src/acfqp/domains/standard_2048.py",
    "src/acfqp/domains/g2048.py",
    "scripts/__init__.py",
    "scripts/bootstrap_v42_standard_2048_remote_ordinal2.py",
    "scripts/run_v42_standard_2048_remote_ordinal2.py",
    "scripts/supervise_v42_standard_2048_remote_ordinal2.py",
)

REQUIRED_REMOTE_SOURCE_PATHS = frozenset(FORMAL_REMOTE_SOURCE_ROOTS)
RUNTIME_FORBIDDEN_SOURCE_PATHS = frozenset(
    {
        "src/acfqp/construction_k7_standard_2048_execution_authority_v42.py",
        "scripts/run_v42_standard_2048_fresh_terminal_campaign.py",
        "scripts/supervise_v42_standard_2048_fresh_terminal_campaign.py",
    }
)

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")


class ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error(ValueError):
    """The remote ordinal-2 identity, source, or one-shot authority changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error(message)


def _content_id(domain: str, payload: dict[str, Any]) -> str:
    if type(domain) is not str or not domain:
        _fail("remote ordinal-2 content-ID domain changed")
    return hashlib.sha256(
        domain.encode("ascii") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _canonical_document(raw_or_document: bytes | dict[str, Any], label: str) -> dict[str, Any]:
    if type(raw_or_document) is bytes:
        try:
            document = loads_canonical_json(raw_or_document)
        except (TypeError, ValueError) as error:
            raise ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error(
                f"{label} is not canonical JSON"
            ) from error
        if canonical_json_bytes(document) != raw_or_document:
            _fail(f"{label} bytes are not canonical")
    elif type(raw_or_document) is dict:
        document = raw_or_document
    else:
        _fail(f"{label} changed type")
    if type(document) is not dict:
        _fail(f"{label} is not an object")
    return document


def _validate_relative_path(value: Any) -> str:
    if type(value) is not str or not value or "\x00" in value or "\\" in value:
        _fail("remote source relative path changed type or encoding")
    parsed = PurePosixPath(value)
    if (
        parsed.is_absolute()
        or parsed.as_posix() != value
        or any(part in {"", ".", ".."} for part in parsed.parts)
        or parsed.parts[0] == ".git"
    ):
        _fail(f"unsafe remote source relative path: {value!r}")
    return value


def build_source_manifest_v42r1(
    *,
    source_commit: str,
    source_tree: str,
    source_facts: list[dict[str, Any]],
    source_roots: list[str] | tuple[str, ...] = FORMAL_REMOTE_SOURCE_ROOTS,
    dynamic_import_sites: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Freeze only the statically resolved Python execution closure.

    The deterministic transport archive has a separate manifest below.  Keeping
    these two inventories separate prevents an unrelated Python file merely
    present in the archive from becoming an allowed runtime dependency.
    """

    if _HEX40.fullmatch(source_commit) is None or _HEX40.fullmatch(source_tree) is None:
        _fail("remote source commit or tree is not one full object ID")
    if type(source_facts) is not list or not source_facts:
        _fail("remote source manifest is empty")
    normalized: list[dict[str, Any]] = []
    previous = ""
    for fact in source_facts:
        if type(fact) is not dict or set(fact) != {
            "relative_path",
            "git_mode",
            "git_object_type",
            "git_blob_oid",
            "byte_count",
            "sha256",
        }:
            _fail("remote source fact schema changed")
        relative = _validate_relative_path(fact.get("relative_path"))
        if relative <= previous:
            _fail("remote source facts are not strictly path-sorted")
        previous = relative
        if (
            not relative.endswith(".py")
            or fact.get("git_mode") != "100644"
            or fact.get("git_object_type") != "blob"
            or _HEX40.fullmatch(str(fact.get("git_blob_oid"))) is None
            or type(fact.get("byte_count")) is not int
            or fact["byte_count"] <= 0
            or _HEX64.fullmatch(str(fact.get("sha256"))) is None
        ):
            _fail(f"remote source fact changed semantics: {relative}")
        normalized.append(dict(fact))
    roots = [_validate_relative_path(value) for value in source_roots]
    if roots != list(FORMAL_REMOTE_SOURCE_ROOTS):
        _fail("remote ordinal-2 formal source roots changed")
    paths = frozenset(fact["relative_path"] for fact in normalized)
    missing = sorted(REQUIRED_REMOTE_SOURCE_PATHS - paths)
    if missing:
        _fail("remote source manifest omitted required ordinal-2 files: " + ", ".join(missing))
    dynamic = [] if dynamic_import_sites is None else dynamic_import_sites
    if type(dynamic) is not list:
        _fail("remote ordinal-2 dynamic import inventory changed type")
    normalized_dynamic: list[dict[str, Any]] = []
    previous_dynamic: tuple[str, int, str] | None = None
    for site in dynamic:
        if (
            type(site) is not dict
            or set(site) != {"relative_path", "line", "call"}
            or type(site.get("relative_path")) is not str
            or site["relative_path"] not in paths
            or type(site.get("line")) is not int
            or site["line"] <= 0
            or site.get("call") not in {"__import__", "import_module", "spec_from_file_location"}
        ):
            _fail("remote ordinal-2 dynamic import fact changed")
        key = (site["relative_path"], site["line"], site["call"])
        if previous_dynamic is not None and key <= previous_dynamic:
            _fail("remote ordinal-2 dynamic import facts are not sorted and unique")
        previous_dynamic = key
        normalized_dynamic.append(dict(site))
    payload = {
        "schema": SOURCE_MANIFEST_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "predecessor_formal_identity": PREDECESSOR_FORMAL_IDENTITY,
        "predecessor_source_commit": PREDECESSOR_SOURCE_COMMIT,
        "predecessor_source_tree": PREDECESSOR_SOURCE_TREE,
        "predecessor_retention_source_commit": PREDECESSOR_RETENTION_SOURCE_COMMIT,
        "predecessor_retention_source_tree": PREDECESSOR_RETENTION_SOURCE_TREE,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "resolver_version": SOURCE_RESOLVER_VERSION,
        "source_roots": roots,
        "source_scope": SOURCE_CLOSURE_SCOPE,
        "stdlib_and_interpreter_sources_excluded": True,
        "external_python_distributions_excluded": True,
        "non_python_resources_excluded": True,
        "allowed_git_modes": ["100644"],
        "source_fact_count": len(normalized),
        "source_facts": normalized,
        "dynamic_import_sites": normalized_dynamic,
        "unmanifested_repository_module_allowed": False,
        "git_metadata_required_remotely": False,
    }
    return {
        **payload,
        "source_manifest_id": _content_id("acfqp:v42-remote-ordinal2:source-manifest", payload),
    }


def verify_source_manifest_v42r1(raw_or_document: bytes | dict[str, Any]) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 source manifest")
    if set(document) != {
        "schema",
        "schema_version",
        "formal_identity",
        "global_execution_ordinal",
        "predecessor_formal_identity",
        "predecessor_source_commit",
        "predecessor_source_tree",
        "predecessor_retention_source_commit",
        "predecessor_retention_source_tree",
        "source_commit",
        "source_tree",
        "resolver_version",
        "source_roots",
        "source_scope",
        "stdlib_and_interpreter_sources_excluded",
        "external_python_distributions_excluded",
        "non_python_resources_excluded",
        "allowed_git_modes",
        "source_fact_count",
        "source_facts",
        "dynamic_import_sites",
        "unmanifested_repository_module_allowed",
        "git_metadata_required_remotely",
        "source_manifest_id",
    }:
        _fail("remote ordinal-2 source manifest schema is not exact")
    expected = build_source_manifest_v42r1(
        source_commit=document.get("source_commit"),
        source_tree=document.get("source_tree"),
        source_facts=document.get("source_facts"),
        source_roots=document.get("source_roots"),
        dynamic_import_sites=document.get("dynamic_import_sites"),
    )
    if document != expected:
        _fail("remote ordinal-2 source manifest identity changed")
    return document


def build_remote_bootstrap_pyz_artifact_v42r1(
    *, members: list[dict[str, Any]], pyz_sha256: str, pyz_byte_count: int,
) -> dict[str, Any]:
    if (
        type(members) is not list
        or len(members) != len(REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS)
        or type(pyz_sha256) is not str
        or _HEX64.fullmatch(pyz_sha256) is None
        or type(pyz_byte_count) is not int
        or pyz_byte_count <= 0
    ):
        _fail("remote bootstrap pyz artifact fact changed")
    normalized: list[dict[str, Any]] = []
    for row, spec in zip(members, REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS):
        archive_path, module_name, member_kind, source_relative_path = spec
        if type(row) is not dict or set(row) != {
            "archive_path", "module_name", "member_kind", "source_relative_path",
            "git_blob_oid", "member_mode", "byte_count", "sha256",
        }:
            _fail("remote bootstrap pyz member schema changed")
        if (
            row.get("archive_path") != archive_path
            or row.get("module_name") != module_name
            or row.get("member_kind") != member_kind
            or row.get("source_relative_path") != source_relative_path
            or row.get("member_mode") != REMOTE_BOOTSTRAP_PYZ_MEMBER_MODE
            or type(row.get("byte_count")) is not int
            or row["byte_count"] < 0
            or _HEX64.fullmatch(str(row.get("sha256"))) is None
        ):
            _fail("remote bootstrap pyz member identity changed")
        if member_kind == "COMMITTED_GIT_BLOB":
            if _HEX40.fullmatch(str(row.get("git_blob_oid"))) is None:
                _fail("remote bootstrap committed member lost its Git blob identity")
        else:
            expected_generated = (
                REMOTE_BOOTSTRAP_GENERATED_MAIN_BYTES
                if member_kind == "GENERATED_STDLIB_MAIN"
                else REMOTE_BOOTSTRAP_GENERATED_EMPTY_PACKAGE_SHIM_BYTES
                if member_kind == "GENERATED_EMPTY_PACKAGE_SHIM"
                else None
            )
            if (
                expected_generated is None
                or row.get("git_blob_oid") is not None
                or row["byte_count"] != len(expected_generated)
                or row["sha256"]
                != hashlib.sha256(expected_generated).hexdigest()
            ):
                _fail("remote bootstrap generated member bytes or provenance changed")
        normalized.append(dict(row))
    member_payload = {
        "archive_format": REMOTE_BOOTSTRAP_PYZ_FORMAT,
        "member_mode": REMOTE_BOOTSTRAP_PYZ_MEMBER_MODE,
        "members": normalized,
    }
    member_manifest_id = _content_id(
        "acfqp:v42-remote-ordinal2:remote-bootstrap-pyz-members", member_payload
    )
    module_origins = [
        {"module_name": row["module_name"], "archive_path": row["archive_path"]}
        for row in normalized
    ]
    payload = {
        "schema": REMOTE_BOOTSTRAP_PYZ_ARTIFACT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "fixed_relative_name": REMOTE_BOOTSTRAP_PYZ_NAME,
        "archive_format": REMOTE_BOOTSTRAP_PYZ_FORMAT,
        "file_mode": REMOTE_BOOTSTRAP_PYZ_FILE_MODE,
        "member_mode": REMOTE_BOOTSTRAP_PYZ_MEMBER_MODE,
        "member_count": len(normalized),
        "members": normalized,
        "member_manifest_id": member_manifest_id,
        "pyz_byte_count": pyz_byte_count,
        "pyz_sha256": pyz_sha256,
        "application_module_origins": module_origins,
        "transport_manifest_embedded_in_pyz": False,
        "self_hash_embedded_in_pyz": False,
    }
    return {
        **payload,
        "remote_bootstrap_pyz_artifact_id": _content_id(
            "acfqp:v42-remote-ordinal2:remote-bootstrap-pyz-artifact", payload
        ),
    }


def verify_remote_bootstrap_pyz_artifact_v42r1(
    raw_or_document: bytes | dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote bootstrap pyz artifact")
    expected = build_remote_bootstrap_pyz_artifact_v42r1(
        members=document.get("members"),
        pyz_sha256=document.get("pyz_sha256"),
        pyz_byte_count=document.get("pyz_byte_count"),
    )
    if document != expected:
        _fail("remote bootstrap pyz artifact identity changed")
    return document


def build_transport_manifest_v42r1(
    *,
    source_manifest: dict[str, Any],
    transport_facts: list[dict[str, Any]],
    source_archive_sha256: str,
    source_archive_byte_count: int,
    remote_bootstrap_pyz_artifact: dict[str, Any],
) -> dict[str, Any]:
    """Bind every deterministic capsule member without widening imports."""

    source_manifest = verify_source_manifest_v42r1(source_manifest)
    remote_bootstrap_pyz_artifact = verify_remote_bootstrap_pyz_artifact_v42r1(
        remote_bootstrap_pyz_artifact
    )
    if (
        type(source_archive_sha256) is not str
        or _HEX64.fullmatch(source_archive_sha256) is None
        or type(source_archive_byte_count) is not int
        or source_archive_byte_count <= 0
        or type(transport_facts) is not list
        or not transport_facts
    ):
        _fail("remote ordinal-2 transport archive fact changed")
    normalized: list[dict[str, Any]] = []
    previous = ""
    for fact in transport_facts:
        if type(fact) is not dict or set(fact) != {
            "relative_path",
            "git_mode",
            "git_object_type",
            "git_blob_oid",
            "byte_count",
            "sha256",
        }:
            _fail("remote ordinal-2 transport member schema changed")
        relative = _validate_relative_path(fact.get("relative_path"))
        if relative <= previous:
            _fail("remote ordinal-2 transport members are not sorted and unique")
        previous = relative
        parsed_relative = PurePosixPath(relative)
        if relative in _RESERVED_TRANSPORT_ROOT_FILES or any(
            parsed_relative == PurePosixPath(reserved)
            or PurePosixPath(reserved) in parsed_relative.parents
            for reserved in _MUTABLE_STATE_FILES_BY_ROOT
        ):
            _fail(
                "remote ordinal-2 transport collides with reserved mutable state: "
                + relative
            )
        if (
            fact.get("git_mode") != "100644"
            or fact.get("git_object_type") != "blob"
            or _HEX40.fullmatch(str(fact.get("git_blob_oid"))) is None
            or type(fact.get("byte_count")) is not int
            or fact["byte_count"] < 0
            or _HEX64.fullmatch(str(fact.get("sha256"))) is None
        ):
            _fail(f"remote ordinal-2 transport member changed: {relative}")
        normalized.append(dict(fact))
    by_path = {fact["relative_path"]: fact for fact in normalized}
    source_by_path = {
        fact["relative_path"]: fact for fact in source_manifest["source_facts"]
    }
    for execution_fact in source_manifest["source_facts"]:
        transported = by_path.get(execution_fact["relative_path"])
        if transported != execution_fact:
            _fail("execution closure is not an exact subset of the transport capsule")
    for member in remote_bootstrap_pyz_artifact["members"]:
        if member["member_kind"] != "COMMITTED_GIT_BLOB":
            continue
        transported = by_path.get(member["source_relative_path"])
        if (
            transported is None
            or source_by_path.get(member["source_relative_path"]) != transported
            or transported["git_blob_oid"] != member["git_blob_oid"]
            or transported["byte_count"] != member["byte_count"]
            or transported["sha256"] != member["sha256"]
        ):
            _fail("remote bootstrap pyz member differs from its committed Git blob")
    payload = {
        "schema": TRANSPORT_MANIFEST_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "source_commit": source_manifest["source_commit"],
        "source_tree": source_manifest["source_tree"],
        "execution_source_manifest_id": source_manifest["source_manifest_id"],
        "transport_scope": TRANSPORT_SCOPE,
        "archive_format": TRANSPORT_ARCHIVE_FORMAT,
        "source_archive_sha256": source_archive_sha256,
        "source_archive_byte_count": source_archive_byte_count,
        "member_git_modes": ["100644"],
        "member_types": ["REGULAR_FILE"],
        "materialized_source_file_mode": MATERIALIZED_SOURCE_FILE_MODE,
        "member_count": len(normalized),
        "transport_facts": normalized,
        "links_or_special_files_allowed": False,
        "unmanifested_transport_member_allowed": False,
        "remote_bootstrap_pyz_artifact": remote_bootstrap_pyz_artifact,
    }
    return {
        **payload,
        "transport_manifest_id": _content_id(
            "acfqp:v42-remote-ordinal2:transport-manifest", payload
        ),
    }


def verify_transport_manifest_v42r1(
    raw_or_document: bytes | dict[str, Any], *, source_manifest: dict[str, Any]
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 transport manifest")
    if set(document) != {
        "schema",
        "schema_version",
        "formal_identity",
        "global_execution_ordinal",
        "source_commit",
        "source_tree",
        "execution_source_manifest_id",
        "transport_scope",
        "archive_format",
        "source_archive_sha256",
        "source_archive_byte_count",
        "member_git_modes",
        "member_types",
        "materialized_source_file_mode",
        "member_count",
        "transport_facts",
        "links_or_special_files_allowed",
        "unmanifested_transport_member_allowed",
        "remote_bootstrap_pyz_artifact",
        "transport_manifest_id",
    }:
        _fail("remote ordinal-2 transport manifest schema is not exact")
    expected = build_transport_manifest_v42r1(
        source_manifest=source_manifest,
        transport_facts=document.get("transport_facts"),
        source_archive_sha256=document.get("source_archive_sha256"),
        source_archive_byte_count=document.get("source_archive_byte_count"),
        remote_bootstrap_pyz_artifact=document.get("remote_bootstrap_pyz_artifact"),
    )
    if document != expected:
        _fail("remote ordinal-2 transport manifest identity changed")
    return document


def materialization_staging_name_v42r1(local_materialization_attempt_id: str) -> str:
    if _HEX64.fullmatch(str(local_materialization_attempt_id)) is None:
        _fail("remote ordinal-2 local materialization attempt ID changed")
    return ".source-materializing-" + local_materialization_attempt_id


def remote_bootstrap_outer_command_v42r1(
    transport_manifest: dict[str, Any],
) -> list[str]:
    pyz = verify_remote_bootstrap_pyz_artifact_v42r1(
        transport_manifest.get("remote_bootstrap_pyz_artifact")
    )
    transport_id = transport_manifest.get("transport_manifest_id")
    if _HEX64.fullmatch(str(transport_id)) is None:
        _fail("remote bootstrap outer command lost its transport anchor")
    return [
        REMOTE_PYTHON,
        "-I",
        "-S",
        "-B",
        "-c",
        REMOTE_BOOTSTRAP_TRUSTED_LAUNCHER_BYTES.decode("utf-8"),
        str(REMOTE_ROOT),
        "--materialize-remote-capsule",
        transport_id,
        pyz["pyz_sha256"],
        str(pyz["pyz_byte_count"]),
    ]


def remote_bootstrap_inner_command_v42r1(
    transport_manifest: dict[str, Any],
) -> list[str]:
    pyz = verify_remote_bootstrap_pyz_artifact_v42r1(
        transport_manifest.get("remote_bootstrap_pyz_artifact")
    )
    transport_id = transport_manifest.get("transport_manifest_id")
    if _HEX64.fullmatch(str(transport_id)) is None:
        _fail("remote bootstrap inner command lost its transport anchor")
    return [
        REMOTE_PYTHON,
        "-I",
        "-S",
        "-B",
        REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH,
        "--materialize-remote-capsule",
        transport_id,
        pyz["pyz_sha256"],
        str(pyz["pyz_byte_count"]),
    ]


def build_local_materialization_attempt_v42r1(
    *, source_manifest: dict[str, Any], transport_manifest: dict[str, Any]
) -> dict[str, Any]:
    source_manifest = verify_source_manifest_v42r1(source_manifest)
    transport_manifest = verify_transport_manifest_v42r1(
        transport_manifest, source_manifest=source_manifest
    )
    pyz = transport_manifest["remote_bootstrap_pyz_artifact"]
    launcher_sha256 = hashlib.sha256(
        REMOTE_BOOTSTRAP_TRUSTED_LAUNCHER_BYTES
    ).hexdigest()
    payload = {
        "schema": LOCAL_MATERIALIZATION_ATTEMPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "source_commit": source_manifest["source_commit"],
        "source_tree": source_manifest["source_tree"],
        "source_manifest_id": source_manifest["source_manifest_id"],
        "transport_manifest_id": transport_manifest["transport_manifest_id"],
        "source_archive_sha256": transport_manifest["source_archive_sha256"],
        "source_archive_byte_count": transport_manifest["source_archive_byte_count"],
        "remote_bootstrap_pyz_artifact_id": pyz[
            "remote_bootstrap_pyz_artifact_id"
        ],
        "remote_bootstrap_pyz_member_manifest_id": pyz["member_manifest_id"],
        "remote_bootstrap_pyz_sha256": pyz["pyz_sha256"],
        "remote_bootstrap_pyz_byte_count": pyz["pyz_byte_count"],
        "remote_bootstrap_pyz_fixed_path": str(
            REMOTE_ROOT / REMOTE_BOOTSTRAP_PYZ_NAME
        ),
        "remote_bootstrap_pyz_runtime_path": REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH,
        "remote_bootstrap_runtime_evidence_path": (
            REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_PATH
        ),
        "remote_bootstrap_trusted_launcher_sha256": launcher_sha256,
        "remote_bootstrap_trusted_launcher_byte_count": len(
            REMOTE_BOOTSTRAP_TRUSTED_LAUNCHER_BYTES
        ),
        "remote_bootstrap_outer_command": remote_bootstrap_outer_command_v42r1(
            transport_manifest
        ),
        "remote_bootstrap_inner_command": remote_bootstrap_inner_command_v42r1(
            transport_manifest
        ),
        "remote_bootstrap_runtime_pyz_memfd": REMOTE_BOOTSTRAP_RUNTIME_PYZ_FD,
        "remote_bootstrap_runtime_evidence_memfd": (
            REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_FD
        ),
        "remote_bootstrap_required_memfd_seals": (
            REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS
        ),
        "transport_target_alias": REMOTE_HOST_ALIAS,
        "remote_hostname": REMOTE_HOSTNAME,
        "remote_user": REMOTE_USER,
        "remote_uid": REMOTE_UID,
        "remote_python": REMOTE_PYTHON,
        "remote_root": str(REMOTE_ROOT),
        "remote_source_root": str(REMOTE_SOURCE_ROOT),
        "published_before_any_fixed_identity_transport_effect": True,
        "fixed_identity_transport_effect_started": False,
        "same_fixed_identity_transport_retry_forbidden_after_publication": True,
        "one_remote_materialization_attempt_authorized": True,
    }
    return {
        **payload,
        "local_materialization_attempt_id": _content_id(
            "acfqp:v42-remote-ordinal2:local-materialization-attempt", payload
        ),
    }


def verify_local_materialization_attempt_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(
        raw_or_document, "remote ordinal-2 local materialization attempt"
    )
    expected = build_local_materialization_attempt_v42r1(
        source_manifest=source_manifest, transport_manifest=transport_manifest
    )
    if document != expected:
        _fail("remote ordinal-2 local materialization attempt changed")
    return document


def build_remote_bootstrap_launcher_evidence_v42r1(
    *,
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
    local_materialization_attempt: dict[str, Any],
    observed_outer_python_command: list[str],
    authorized_inner_python_command: list[str],
    observed_outer_hostname: str,
    observed_outer_user: str,
    observed_outer_uid: int,
    observed_outer_gid: int,
    observed_outer_python_invocation: str,
    observed_outer_python_realpath: str,
    observed_outer_python_version: tuple[int, int, int],
    outer_python_isolated_flag: int,
    outer_python_no_site_flag: int,
    outer_python_dont_write_bytecode: bool,
    outer_five_control_verification_completed: bool,
    outer_pyz_nofollow_stable_hash_completed: bool,
    outer_lexical_chain: list[dict[str, Any]],
    outer_root_identity: list[int],
    outer_root_inventory: list[str],
    outer_five_control_identities: dict[str, list[int]],
    runtime_pyz_memfd: int,
    runtime_evidence_memfd: int,
    required_memfd_seals: int,
    required_memfd_mode: str,
    runtime_memfd_uid: int,
    runtime_memfd_gid: int,
    runtime_memfds_inheritable_for_inner_exec: bool,
    fixed_identity_effect_started: bool,
) -> dict[str, Any]:
    source_manifest = verify_source_manifest_v42r1(source_manifest)
    transport_manifest = verify_transport_manifest_v42r1(
        transport_manifest, source_manifest=source_manifest
    )
    local_attempt = verify_local_materialization_attempt_v42r1(
        local_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    pyz = transport_manifest["remote_bootstrap_pyz_artifact"]
    expected_chain_paths = ["/"]
    current = ""
    for component in REMOTE_ROOT.parts[1:]:
        current += "/" + component
        expected_chain_paths.append(current)
    expected_control_names = {
        SOURCE_MANIFEST_NAME,
        LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        REMOTE_BOOTSTRAP_PYZ_NAME,
        SOURCE_CAPSULE_NAME,
        TRANSPORT_MANIFEST_NAME,
    }
    identity_rows_valid = (
        type(outer_lexical_chain) is list
        and [row.get("absolute_path") for row in outer_lexical_chain]
        == expected_chain_paths
        and all(
            type(row) is dict
            and set(row) == {"absolute_path", "identity"}
            and type(row["identity"]) is list
            and len(row["identity"]) == 5
            and all(type(value) is int and value >= 0 for value in row["identity"])
            for row in outer_lexical_chain
        )
        and type(outer_root_identity) is list
        and len(outer_root_identity) == 9
        and all(type(value) is int and value >= 0 for value in outer_root_identity)
        and outer_lexical_chain[-1]["identity"] == outer_root_identity[:5]
        and outer_root_inventory == sorted(expected_control_names)
        and type(outer_five_control_identities) is dict
        and set(outer_five_control_identities) == expected_control_names
        and all(
            type(identity) is list
            and len(identity) == 9
            and all(type(value) is int and value >= 0 for value in identity)
            for identity in outer_five_control_identities.values()
        )
    )
    if (
        observed_outer_python_command
        != local_attempt["remote_bootstrap_outer_command"]
        or authorized_inner_python_command
        != local_attempt["remote_bootstrap_inner_command"]
        or observed_outer_hostname != REMOTE_HOSTNAME
        or observed_outer_user != REMOTE_USER
        or type(observed_outer_uid) is not int
        or observed_outer_uid != REMOTE_UID
        or type(observed_outer_gid) is not int
        or observed_outer_gid != REMOTE_GID
        or observed_outer_python_invocation != REMOTE_PYTHON
        or observed_outer_python_realpath != REMOTE_PYTHON_REALPATH
        or observed_outer_python_version != REMOTE_PYTHON_VERSION
        or type(outer_python_isolated_flag) is not int
        or outer_python_isolated_flag != 1
        or type(outer_python_no_site_flag) is not int
        or outer_python_no_site_flag != 1
        or outer_python_dont_write_bytecode is not True
        or outer_five_control_verification_completed is not True
        or outer_pyz_nofollow_stable_hash_completed is not True
        or not identity_rows_valid
        or runtime_pyz_memfd != REMOTE_BOOTSTRAP_RUNTIME_PYZ_FD
        or runtime_evidence_memfd != REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_FD
        or required_memfd_seals != REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS
        or required_memfd_mode != REMOTE_BOOTSTRAP_PYZ_FILE_MODE
        or runtime_memfd_uid != REMOTE_UID
        or runtime_memfd_gid != REMOTE_GID
        or runtime_memfds_inheritable_for_inner_exec is not True
        or fixed_identity_effect_started is not False
    ):
        _fail("trusted remote bootstrap launcher observation changed")
    payload = {
        "schema": REMOTE_BOOTSTRAP_LAUNCHER_EVIDENCE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "execution_mode": "FORMAL_MATERIALIZATION",
        "source_manifest_id": source_manifest["source_manifest_id"],
        "transport_manifest_id": transport_manifest["transport_manifest_id"],
        "local_materialization_attempt_id": local_attempt[
            "local_materialization_attempt_id"
        ],
        "remote_bootstrap_pyz_artifact_id": pyz[
            "remote_bootstrap_pyz_artifact_id"
        ],
        "remote_bootstrap_pyz_member_manifest_id": pyz["member_manifest_id"],
        "remote_bootstrap_pyz_sha256": pyz["pyz_sha256"],
        "remote_bootstrap_pyz_byte_count": pyz["pyz_byte_count"],
        "remote_bootstrap_pyz_fixed_path": str(
            REMOTE_ROOT / REMOTE_BOOTSTRAP_PYZ_NAME
        ),
        "remote_bootstrap_pyz_runtime_path": REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH,
        "remote_bootstrap_runtime_evidence_path": (
            REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_PATH
        ),
        "trusted_launcher_sha256": hashlib.sha256(
            REMOTE_BOOTSTRAP_TRUSTED_LAUNCHER_BYTES
        ).hexdigest(),
        "trusted_launcher_byte_count": len(
            REMOTE_BOOTSTRAP_TRUSTED_LAUNCHER_BYTES
        ),
        "observed_outer_python_command": observed_outer_python_command,
        "authorized_inner_python_command": authorized_inner_python_command,
        "observed_outer_hostname": observed_outer_hostname,
        "observed_outer_user": observed_outer_user,
        "observed_outer_uid": observed_outer_uid,
        "observed_outer_gid": observed_outer_gid,
        "observed_outer_python_invocation": observed_outer_python_invocation,
        "observed_outer_python_realpath": observed_outer_python_realpath,
        "observed_outer_python_version": list(observed_outer_python_version),
        "outer_python_isolated_flag": outer_python_isolated_flag,
        "outer_python_no_site_flag": outer_python_no_site_flag,
        "outer_python_dont_write_bytecode": outer_python_dont_write_bytecode,
        "outer_five_control_verification_completed": (
            outer_five_control_verification_completed
        ),
        "outer_pyz_nofollow_stable_hash_completed": (
            outer_pyz_nofollow_stable_hash_completed
        ),
        "outer_lexical_chain": outer_lexical_chain,
        "outer_root_identity": outer_root_identity,
        "outer_root_inventory": outer_root_inventory,
        "outer_five_control_identities": outer_five_control_identities,
        "runtime_pyz_memfd": runtime_pyz_memfd,
        "runtime_evidence_memfd": runtime_evidence_memfd,
        "required_memfd_seals": required_memfd_seals,
        "required_memfd_mode": required_memfd_mode,
        "runtime_memfd_uid": runtime_memfd_uid,
        "runtime_memfd_gid": runtime_memfd_gid,
        "runtime_memfds_inheritable_for_inner_exec": (
            runtime_memfds_inheritable_for_inner_exec
        ),
        "fixed_identity_effect_started": fixed_identity_effect_started,
    }
    return {
        **payload,
        "remote_bootstrap_launcher_evidence_id": _content_id(
            "acfqp:v42-remote-ordinal2:remote-bootstrap-launcher-evidence",
            payload,
        ),
    }


def verify_remote_bootstrap_launcher_evidence_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
    local_materialization_attempt: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(
        raw_or_document, "remote bootstrap trusted-launcher evidence"
    )
    version = document.get("observed_outer_python_version")
    if (
        type(version) is not list
        or len(version) != 3
        or any(type(value) is not int for value in version)
    ):
        _fail("trusted launcher Python version observation changed type")
    expected = build_remote_bootstrap_launcher_evidence_v42r1(
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
        local_materialization_attempt=local_materialization_attempt,
        observed_outer_python_command=document.get(
            "observed_outer_python_command"
        ),
        authorized_inner_python_command=document.get(
            "authorized_inner_python_command"
        ),
        observed_outer_hostname=document.get("observed_outer_hostname"),
        observed_outer_user=document.get("observed_outer_user"),
        observed_outer_uid=document.get("observed_outer_uid"),
        observed_outer_gid=document.get("observed_outer_gid"),
        observed_outer_python_invocation=document.get(
            "observed_outer_python_invocation"
        ),
        observed_outer_python_realpath=document.get(
            "observed_outer_python_realpath"
        ),
        observed_outer_python_version=tuple(version),
        outer_python_isolated_flag=document.get("outer_python_isolated_flag"),
        outer_python_no_site_flag=document.get("outer_python_no_site_flag"),
        outer_python_dont_write_bytecode=document.get(
            "outer_python_dont_write_bytecode"
        ),
        outer_five_control_verification_completed=document.get(
            "outer_five_control_verification_completed"
        ),
        outer_pyz_nofollow_stable_hash_completed=document.get(
            "outer_pyz_nofollow_stable_hash_completed"
        ),
        outer_lexical_chain=document.get("outer_lexical_chain"),
        outer_root_identity=document.get("outer_root_identity"),
        outer_root_inventory=document.get("outer_root_inventory"),
        outer_five_control_identities=document.get(
            "outer_five_control_identities"
        ),
        runtime_pyz_memfd=document.get("runtime_pyz_memfd"),
        runtime_evidence_memfd=document.get("runtime_evidence_memfd"),
        required_memfd_seals=document.get("required_memfd_seals"),
        required_memfd_mode=document.get("required_memfd_mode"),
        runtime_memfd_uid=document.get("runtime_memfd_uid"),
        runtime_memfd_gid=document.get("runtime_memfd_gid"),
        runtime_memfds_inheritable_for_inner_exec=document.get(
            "runtime_memfds_inheritable_for_inner_exec"
        ),
        fixed_identity_effect_started=document.get("fixed_identity_effect_started"),
    )
    if document != expected:
        _fail("remote bootstrap trusted-launcher evidence changed")
    return document


def build_remote_bootstrap_runtime_binding_v42r1(
    transport_manifest: dict[str, Any], *, source_manifest: dict[str, Any],
    local_materialization_attempt: dict[str, Any],
    trusted_launcher_evidence: dict[str, Any],
    observed_hostname: str, observed_user: str, observed_uid: int,
    observed_python_invocation: str, observed_python_realpath: str,
    observed_python_version: tuple[int, int, int], python_isolated_flag: int,
    python_no_site_flag: int, python_dont_write_bytecode: bool,
    observed_inner_python_command: list[str],
    observed_remote_bootstrap_pyz_fixed_path: str,
    observed_remote_bootstrap_pyz_runtime_path: str,
    observed_remote_bootstrap_pyz_sha256: str,
    observed_remote_bootstrap_pyz_byte_count: int,
    observed_member_manifest_id: str,
    runtime_pyz_memfd_seals: int,
    runtime_evidence_memfd_seals: int,
    runtime_pyz_memfd_mode: str,
    runtime_evidence_memfd_mode: str,
    runtime_pyz_memfd_uid: int,
    runtime_pyz_memfd_gid: int,
    runtime_evidence_memfd_uid: int,
    runtime_evidence_memfd_gid: int,
    runtime_memfds_inheritable: bool,
    observed_stdlib_module_origins: list[dict[str, str]],
    loaded_application_module_origins: list[dict[str, str]],
) -> dict[str, Any]:
    transport_manifest = verify_transport_manifest_v42r1(
        transport_manifest, source_manifest=source_manifest
    )
    pyz = transport_manifest["remote_bootstrap_pyz_artifact"]
    local_attempt = verify_local_materialization_attempt_v42r1(
        local_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    launcher_evidence = verify_remote_bootstrap_launcher_evidence_v42r1(
        trusted_launcher_evidence,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
        local_materialization_attempt=local_attempt,
    )
    expected_origins = [
        {
            **row,
            "observed_origin": REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH + "/"
            + row["archive_path"],
        }
        for row in pyz["application_module_origins"]
    ]
    if (
        observed_hostname != REMOTE_HOSTNAME
        or observed_user != REMOTE_USER
        or type(observed_uid) is not int
        or observed_uid != REMOTE_UID
        or observed_python_invocation != REMOTE_PYTHON
        or observed_python_realpath != REMOTE_PYTHON_REALPATH
        or observed_python_version != REMOTE_PYTHON_VERSION
        or observed_inner_python_command
        != local_attempt["remote_bootstrap_inner_command"]
        or type(python_isolated_flag) is not int
        or python_isolated_flag != 1
        or type(python_no_site_flag) is not int
        or python_no_site_flag != 1
        or python_dont_write_bytecode is not True
        or observed_remote_bootstrap_pyz_fixed_path
        != str(REMOTE_ROOT / REMOTE_BOOTSTRAP_PYZ_NAME)
        or observed_remote_bootstrap_pyz_runtime_path
        != REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH
        or observed_remote_bootstrap_pyz_sha256 != pyz["pyz_sha256"]
        or observed_remote_bootstrap_pyz_byte_count != pyz["pyz_byte_count"]
        or observed_member_manifest_id != pyz["member_manifest_id"]
        or runtime_pyz_memfd_seals != REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS
        or runtime_evidence_memfd_seals != REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS
        or runtime_pyz_memfd_mode != REMOTE_BOOTSTRAP_PYZ_FILE_MODE
        or runtime_evidence_memfd_mode != REMOTE_BOOTSTRAP_PYZ_FILE_MODE
        or runtime_pyz_memfd_uid != REMOTE_UID
        or runtime_evidence_memfd_uid != REMOTE_UID
        or runtime_pyz_memfd_gid != REMOTE_GID
        or runtime_evidence_memfd_gid != REMOTE_GID
        or runtime_memfds_inheritable is not True
        or observed_stdlib_module_origins
        != list(REMOTE_BOOTSTRAP_STDLIB_MODULE_ORIGINS)
        or loaded_application_module_origins != expected_origins
    ):
        _fail("observed remote bootstrap runtime differs from the fixed pyz identity")
    payload = {
        "schema": REMOTE_BOOTSTRAP_RUNTIME_BINDING_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "transport_manifest_id": transport_manifest["transport_manifest_id"],
        "local_materialization_attempt_id": local_attempt[
            "local_materialization_attempt_id"
        ],
        "transport_target_alias": REMOTE_HOST_ALIAS,
        "trusted_launcher_evidence": launcher_evidence,
        "trusted_launcher_evidence_id": launcher_evidence[
            "remote_bootstrap_launcher_evidence_id"
        ],
        "observed_hostname": observed_hostname,
        "observed_user": observed_user,
        "observed_uid": observed_uid,
        "observed_python_invocation": observed_python_invocation,
        "observed_python_realpath": observed_python_realpath,
        "observed_python_version": list(observed_python_version),
        "observed_inner_python_command": observed_inner_python_command,
        "python_isolated_flag": python_isolated_flag,
        "python_no_site_flag": python_no_site_flag,
        "python_dont_write_bytecode": python_dont_write_bytecode,
        "remote_bootstrap_pyz_fixed_path": observed_remote_bootstrap_pyz_fixed_path,
        "remote_bootstrap_pyz_runtime_path": (
            observed_remote_bootstrap_pyz_runtime_path
        ),
        "remote_bootstrap_runtime_evidence_path": (
            REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_PATH
        ),
        "remote_bootstrap_pyz_artifact_id": pyz[
            "remote_bootstrap_pyz_artifact_id"
        ],
        "remote_bootstrap_pyz_member_manifest_id": pyz["member_manifest_id"],
        "remote_bootstrap_pyz_sha256": observed_remote_bootstrap_pyz_sha256,
        "remote_bootstrap_pyz_byte_count": observed_remote_bootstrap_pyz_byte_count,
        "runtime_pyz_memfd": REMOTE_BOOTSTRAP_RUNTIME_PYZ_FD,
        "runtime_evidence_memfd": REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_FD,
        "runtime_pyz_memfd_seals": runtime_pyz_memfd_seals,
        "runtime_evidence_memfd_seals": runtime_evidence_memfd_seals,
        "runtime_pyz_memfd_mode": runtime_pyz_memfd_mode,
        "runtime_evidence_memfd_mode": runtime_evidence_memfd_mode,
        "runtime_pyz_memfd_uid": runtime_pyz_memfd_uid,
        "runtime_pyz_memfd_gid": runtime_pyz_memfd_gid,
        "runtime_evidence_memfd_uid": runtime_evidence_memfd_uid,
        "runtime_evidence_memfd_gid": runtime_evidence_memfd_gid,
        "runtime_memfds_inheritable": runtime_memfds_inheritable,
        "trusted_outer_launcher_verified_before_inner_application_import": True,
        "sealed_runtime_verified_before_inner_application_import": True,
        "observed_stdlib_module_origins": observed_stdlib_module_origins,
        "loaded_application_module_origins": loaded_application_module_origins,
        "all_application_modules_loaded_from_verified_pyz": True,
        "runtime_verified_before_remote_materialization_attempt": True,
    }
    return {
        **payload,
        "remote_bootstrap_runtime_binding_id": _content_id(
            "acfqp:v42-remote-ordinal2:remote-bootstrap-runtime-binding", payload
        ),
    }


def verify_remote_bootstrap_runtime_binding_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *, transport_manifest: dict[str, Any], source_manifest: dict[str, Any],
    local_materialization_attempt: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote bootstrap runtime binding")
    version = document.get("observed_python_version")
    if (
        type(version) is not list
        or len(version) != 3
        or any(type(value) is not int for value in version)
    ):
        _fail("remote bootstrap Python version observation changed type")
    expected = build_remote_bootstrap_runtime_binding_v42r1(
        transport_manifest,
        source_manifest=source_manifest,
        local_materialization_attempt=local_materialization_attempt,
        trusted_launcher_evidence=document.get("trusted_launcher_evidence"),
        observed_hostname=document.get("observed_hostname"),
        observed_user=document.get("observed_user"),
        observed_uid=document.get("observed_uid"),
        observed_python_invocation=document.get("observed_python_invocation"),
        observed_python_realpath=document.get("observed_python_realpath"),
        observed_python_version=tuple(version),
        observed_inner_python_command=document.get(
            "observed_inner_python_command"
        ),
        python_isolated_flag=document.get("python_isolated_flag"),
        python_no_site_flag=document.get("python_no_site_flag"),
        python_dont_write_bytecode=document.get("python_dont_write_bytecode"),
        observed_remote_bootstrap_pyz_fixed_path=document.get(
            "remote_bootstrap_pyz_fixed_path"
        ),
        observed_remote_bootstrap_pyz_runtime_path=document.get(
            "remote_bootstrap_pyz_runtime_path"
        ),
        observed_remote_bootstrap_pyz_sha256=document.get(
            "remote_bootstrap_pyz_sha256"
        ),
        observed_remote_bootstrap_pyz_byte_count=document.get(
            "remote_bootstrap_pyz_byte_count"
        ),
        observed_member_manifest_id=document.get(
            "remote_bootstrap_pyz_member_manifest_id"
        ),
        runtime_pyz_memfd_seals=document.get("runtime_pyz_memfd_seals"),
        runtime_evidence_memfd_seals=document.get(
            "runtime_evidence_memfd_seals"
        ),
        runtime_pyz_memfd_mode=document.get("runtime_pyz_memfd_mode"),
        runtime_evidence_memfd_mode=document.get(
            "runtime_evidence_memfd_mode"
        ),
        runtime_pyz_memfd_uid=document.get("runtime_pyz_memfd_uid"),
        runtime_pyz_memfd_gid=document.get("runtime_pyz_memfd_gid"),
        runtime_evidence_memfd_uid=document.get(
            "runtime_evidence_memfd_uid"
        ),
        runtime_evidence_memfd_gid=document.get(
            "runtime_evidence_memfd_gid"
        ),
        runtime_memfds_inheritable=document.get(
            "runtime_memfds_inheritable"
        ),
        observed_stdlib_module_origins=document.get(
            "observed_stdlib_module_origins"
        ),
        loaded_application_module_origins=document.get(
            "loaded_application_module_origins"
        ),
    )
    if document != expected:
        _fail("remote bootstrap runtime binding changed")
    return document


def build_remote_materialization_attempt_v42r1(
    *,
    local_materialization_attempt: dict[str, Any],
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
    remote_bootstrap_runtime_binding: dict[str, Any],
) -> dict[str, Any]:
    local_attempt = verify_local_materialization_attempt_v42r1(
        local_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    runtime_binding = verify_remote_bootstrap_runtime_binding_v42r1(
        remote_bootstrap_runtime_binding,
        transport_manifest=transport_manifest,
        source_manifest=source_manifest,
        local_materialization_attempt=local_attempt,
    )
    pyz = transport_manifest["remote_bootstrap_pyz_artifact"]
    payload = {
        "schema": REMOTE_MATERIALIZATION_ATTEMPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "local_materialization_attempt_id": local_attempt[
            "local_materialization_attempt_id"
        ],
        "source_commit": source_manifest["source_commit"],
        "source_tree": source_manifest["source_tree"],
        "source_manifest_id": source_manifest["source_manifest_id"],
        "transport_manifest_id": transport_manifest["transport_manifest_id"],
        "source_archive_sha256": transport_manifest["source_archive_sha256"],
        "source_archive_byte_count": transport_manifest["source_archive_byte_count"],
        "remote_bootstrap_pyz_artifact_id": pyz[
            "remote_bootstrap_pyz_artifact_id"
        ],
        "remote_bootstrap_pyz_member_manifest_id": pyz["member_manifest_id"],
        "remote_bootstrap_pyz_sha256": pyz["pyz_sha256"],
        "remote_bootstrap_pyz_byte_count": pyz["pyz_byte_count"],
        "remote_bootstrap_runtime_binding": runtime_binding,
        "remote_bootstrap_runtime_binding_id": runtime_binding[
            "remote_bootstrap_runtime_binding_id"
        ],
        "remote_root": str(REMOTE_ROOT),
        "remote_source_root": str(REMOTE_SOURCE_ROOT),
        "staging_relative_name": materialization_staging_name_v42r1(
            local_attempt["local_materialization_attempt_id"]
        ),
        "source_state_before_attempt": "ABSENT",
        "staging_state_before_attempt": "ABSENT",
        "published_before_extraction_or_source_publish_effect": True,
        "atomic_publish_method": "renameat2(RENAME_NOREPLACE)",
        "same_identity_materialization_retry_forbidden_after_publication": True,
    }
    return {
        **payload,
        "remote_materialization_attempt_id": _content_id(
            "acfqp:v42-remote-ordinal2:remote-materialization-attempt", payload
        ),
    }


def verify_remote_materialization_attempt_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    local_materialization_attempt: dict[str, Any],
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(
        raw_or_document, "remote ordinal-2 remote materialization attempt"
    )
    expected = build_remote_materialization_attempt_v42r1(
        local_materialization_attempt=local_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
        remote_bootstrap_runtime_binding=document.get(
            "remote_bootstrap_runtime_binding"
        ),
    )
    if document != expected:
        _fail("remote ordinal-2 remote materialization attempt changed")
    return document


def build_materialization_terminal_v42r1(
    *,
    local_materialization_attempt: dict[str, Any],
    remote_materialization_attempt: dict[str, Any],
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
) -> dict[str, Any]:
    local_attempt = verify_local_materialization_attempt_v42r1(
        local_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    remote_attempt = verify_remote_materialization_attempt_v42r1(
        remote_materialization_attempt,
        local_materialization_attempt=local_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    payload = {
        "schema": MATERIALIZATION_TERMINAL_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "local_materialization_attempt_id": local_attempt[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": remote_attempt[
            "remote_materialization_attempt_id"
        ],
        "source_commit": source_manifest["source_commit"],
        "source_tree": source_manifest["source_tree"],
        "source_manifest_id": source_manifest["source_manifest_id"],
        "transport_manifest_id": transport_manifest["transport_manifest_id"],
        "source_archive_sha256": transport_manifest["source_archive_sha256"],
        "source_archive_byte_count": transport_manifest["source_archive_byte_count"],
        "remote_bootstrap_pyz_artifact_id": remote_attempt[
            "remote_bootstrap_pyz_artifact_id"
        ],
        "remote_bootstrap_pyz_member_manifest_id": remote_attempt[
            "remote_bootstrap_pyz_member_manifest_id"
        ],
        "remote_bootstrap_pyz_sha256": remote_attempt["remote_bootstrap_pyz_sha256"],
        "remote_bootstrap_pyz_byte_count": remote_attempt[
            "remote_bootstrap_pyz_byte_count"
        ],
        "remote_bootstrap_runtime_binding_id": remote_attempt[
            "remote_bootstrap_runtime_binding_id"
        ],
        "loaded_application_module_origins": remote_attempt[
            "remote_bootstrap_runtime_binding"
        ]["loaded_application_module_origins"],
        "staging_relative_name": remote_attempt["staging_relative_name"],
        "published_source_relative_name": REMOTE_SOURCE_ROOT.name,
        "staged_transport_inventory_verified": True,
        "staged_execution_closure_verified": True,
        "terminal_embedded_before_atomic_publish": True,
        "atomic_publish_method": "renameat2(RENAME_NOREPLACE)",
        "source_target_state_before_publish": "ABSENT",
        "materialization_status": "COMPLETE_SUCCESS",
        "same_identity_materialization_retry_authorized": False,
    }
    return {
        **payload,
        "materialization_terminal_id": _content_id(
            "acfqp:v42-remote-ordinal2:materialization-terminal", payload
        ),
    }


def verify_materialization_terminal_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    local_materialization_attempt: dict[str, Any],
    remote_materialization_attempt: dict[str, Any],
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(
        raw_or_document, "remote ordinal-2 materialization terminal"
    )
    expected = build_materialization_terminal_v42r1(
        local_materialization_attempt=local_materialization_attempt,
        remote_materialization_attempt=remote_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    if document != expected:
        _fail("remote ordinal-2 materialization terminal changed")
    return document


def build_materialization_failure_v42r1(
    *,
    local_materialization_attempt: dict[str, Any],
    remote_materialization_attempt: dict[str, Any],
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
    failure_stage: str,
    failure_type: str,
    failure_message: str,
    source_state_after_failure: str,
    staging_state_after_failure: str,
    embedded_terminal_state_after_failure: str,
) -> dict[str, Any]:
    local_attempt = verify_local_materialization_attempt_v42r1(
        local_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    remote_attempt = verify_remote_materialization_attempt_v42r1(
        remote_materialization_attempt,
        local_materialization_attempt=local_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    if (
        type(failure_stage) is not str
        or not failure_stage
        or re.fullmatch(r"[A-Z0-9_]+", failure_stage) is None
        or type(failure_type) is not str
        or not failure_type
        or len(failure_type.encode("utf-8")) > 256
        or type(failure_message) is not str
        or len(failure_message.encode("utf-8")) > 4096
        or source_state_after_failure != "ABSENT"
        or staging_state_after_failure not in {"ABSENT", "DIRECTORY", "NON_DIRECTORY"}
        or embedded_terminal_state_after_failure
        not in {"ABSENT", "REGULAR_FILE", "NONREGULAR", "UNOBSERVABLE"}
    ):
        _fail("remote ordinal-2 materialization failure fields changed")
    if (
        staging_state_after_failure == "ABSENT"
        and embedded_terminal_state_after_failure != "ABSENT"
        or staging_state_after_failure == "NON_DIRECTORY"
        and embedded_terminal_state_after_failure != "UNOBSERVABLE"
        or staging_state_after_failure == "DIRECTORY"
        and embedded_terminal_state_after_failure == "UNOBSERVABLE"
    ):
        _fail("remote ordinal-2 materialization failure state join changed")
    payload = {
        "schema": MATERIALIZATION_FAILURE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "local_materialization_attempt_id": local_attempt[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": remote_attempt[
            "remote_materialization_attempt_id"
        ],
        "source_manifest_id": source_manifest["source_manifest_id"],
        "transport_manifest_id": transport_manifest["transport_manifest_id"],
        "failure_stage": failure_stage,
        "failure_type": failure_type,
        "failure_message": failure_message,
        "source_state_after_failure": source_state_after_failure,
        "staging_state_after_failure": staging_state_after_failure,
        "embedded_terminal_state_after_failure": embedded_terminal_state_after_failure,
        "source_publish_completed": False,
        "scientific_execution_started": False,
        "same_identity_materialization_retry_forbidden": True,
        "retry_authorized": False,
        "only_read_only_classification_allowed": True,
    }
    return {
        **payload,
        "materialization_failure_id": _content_id(
            "acfqp:v42-remote-ordinal2:materialization-failure", payload
        ),
    }


def verify_materialization_failure_v42r1(
    raw_or_document: bytes | dict[str, Any],
    *,
    local_materialization_attempt: dict[str, Any],
    remote_materialization_attempt: dict[str, Any],
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(
        raw_or_document, "remote ordinal-2 materialization failure"
    )
    expected = build_materialization_failure_v42r1(
        local_materialization_attempt=local_materialization_attempt,
        remote_materialization_attempt=remote_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
        failure_stage=document.get("failure_stage"),
        failure_type=document.get("failure_type"),
        failure_message=document.get("failure_message"),
        source_state_after_failure=document.get("source_state_after_failure"),
        staging_state_after_failure=document.get("staging_state_after_failure"),
        embedded_terminal_state_after_failure=document.get(
            "embedded_terminal_state_after_failure"
        ),
    )
    if document != expected:
        _fail("remote ordinal-2 materialization failure changed")
    return document


def build_local_launch_attempt_v42r1(
    *, prepare_receipt: dict[str, Any], transport_target_alias: str
) -> dict[str, Any]:
    if transport_target_alias != REMOTE_HOST_ALIAS:
        _fail("remote ordinal-2 local launch target alias changed")
    payload = {
        "schema": LOCAL_LAUNCH_ATTEMPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "source_commit": prepare_receipt["source_commit"],
        "source_tree": prepare_receipt["source_tree"],
        "source_manifest_id": prepare_receipt["source_manifest_id"],
        "transport_manifest_id": prepare_receipt["transport_manifest_id"],
        "predecessor_binding_id": prepare_receipt["predecessor_binding_id"],
        "transport_target_alias": transport_target_alias,
        "expected_remote_hostname": REMOTE_HOSTNAME,
        "expected_remote_user": REMOTE_USER,
        "expected_remote_uid": REMOTE_UID,
        "launch_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "published_before_any_launch_transport_effect": True,
        "transport_effect_started": False,
        "same_identity_retry_forbidden_after_publication": True,
    }
    return {
        **payload,
        "local_launch_attempt_id": _content_id(
            "acfqp:v42-remote-ordinal2:local-launch-attempt", payload
        ),
    }


def verify_local_launch_attempt_v42r1(
    raw_or_document: bytes | dict[str, Any], *, prepare_receipt: dict[str, Any]
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 local launch attempt")
    expected = build_local_launch_attempt_v42r1(
        prepare_receipt=prepare_receipt,
        transport_target_alias=document.get("transport_target_alias"),
    )
    if document != expected:
        _fail("remote ordinal-2 local launch attempt changed")
    return document


def build_predecessor_retention_binding_v42r1(
    *, retention_manifest_sha256: str, retention_manifest_byte_count: int,
    independent_verification_sha256: str, independent_verification_byte_count: int,
) -> dict[str, Any]:
    if (
        not PREDECESSOR_RETENTION_READY
        or PREDECESSOR_RETENTION_MANIFEST_ID == _PENDING_PREDECESSOR_HEX64
        or PREDECESSOR_INDEPENDENT_VERIFICATION_ID == _PENDING_PREDECESSOR_HEX64
    ):
        _fail("remote ordinal-2 formal authority disabled pending predecessor retention freeze")
    if (
        retention_manifest_sha256 != PREDECESSOR_RETENTION_MANIFEST_SHA256
        or retention_manifest_byte_count != PREDECESSOR_RETENTION_MANIFEST_BYTE_COUNT
        or independent_verification_sha256
        != PREDECESSOR_INDEPENDENT_VERIFICATION_SHA256
        or independent_verification_byte_count
        != PREDECESSOR_INDEPENDENT_VERIFICATION_BYTE_COUNT
    ):
        _fail("remote ordinal-2 predecessor retained file facts changed")
    payload = {
        "schema": PREDECESSOR_BINDING_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "predecessor_formal_identity": PREDECESSOR_FORMAL_IDENTITY,
        "predecessor_source_commit": PREDECESSOR_SOURCE_COMMIT,
        "predecessor_source_tree": PREDECESSOR_SOURCE_TREE,
        "predecessor_retention_source_commit": PREDECESSOR_RETENTION_SOURCE_COMMIT,
        "predecessor_retention_source_tree": PREDECESSOR_RETENTION_SOURCE_TREE,
        "predecessor_prepare_receipt_id": PREDECESSOR_PREPARE_RECEIPT_ID,
        "predecessor_runner_attempt_id": PREDECESSOR_RUNNER_ATTEMPT_ID,
        "predecessor_worker_start_id": PREDECESSOR_WORKER_START_ID,
        "predecessor_authority_consumption_id": PREDECESSOR_AUTHORITY_CONSUMPTION_ID,
        "predecessor_runner_failure_id": PREDECESSOR_RUNNER_FAILURE_ID,
        "predecessor_retention_manifest_id": PREDECESSOR_RETENTION_MANIFEST_ID,
        "predecessor_retention_manifest_sha256": retention_manifest_sha256,
        "predecessor_retention_manifest_byte_count": retention_manifest_byte_count,
        "predecessor_independent_verification_id": PREDECESSOR_INDEPENDENT_VERIFICATION_ID,
        "predecessor_independent_verification_sha256": independent_verification_sha256,
        "predecessor_independent_verification_byte_count": independent_verification_byte_count,
        "predecessor_campaign_absent": True,
        "predecessor_verification_absent": True,
        "predecessor_terminal_absent": True,
        "predecessor_scientific_success": False,
        "predecessor_same_identity_rerun_forbidden": True,
    }
    return {
        **payload,
        "predecessor_binding_id": _content_id(
            "acfqp:v42-remote-ordinal2:predecessor-binding", payload
        ),
    }


def verify_predecessor_retention_binding_v42r1(
    raw_or_document: bytes | dict[str, Any]
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 predecessor binding")
    expected = build_predecessor_retention_binding_v42r1(
        retention_manifest_sha256=document.get("predecessor_retention_manifest_sha256"),
        retention_manifest_byte_count=document.get("predecessor_retention_manifest_byte_count"),
        independent_verification_sha256=document.get(
            "predecessor_independent_verification_sha256"
        ),
        independent_verification_byte_count=document.get(
            "predecessor_independent_verification_byte_count"
        ),
    )
    if document != expected:
        _fail("remote ordinal-2 predecessor binding changed")
    return document


def build_host_attestation_v42r1(
    *,
    transport_target_alias: str,
    observed_hostname: str,
    observed_user: str,
    observed_uid: int,
    observed_python_invocation: str,
    observed_python_realpath: str,
    observed_python_version: tuple[int, int, int] | list[int],
    observed_source_root: str,
    memory_total_bytes: int,
    memory_available_bytes: int,
    swap_total_bytes: int,
    swap_free_bytes: int,
    cgroup_mount_filesystem_type: str,
    cgroup_mount_root: str,
    cgroup_unified_scope_path: str,
    cgroup_root_controllers: list[str] | tuple[str, ...],
    cgroup_memory_ancestry: list[dict[str, Any]],
    filesystem_available_bytes: int,
    attestation_stage: str,
) -> dict[str, Any]:
    integer_observations = (
        observed_uid,
        memory_total_bytes,
        memory_available_bytes,
        swap_total_bytes,
        swap_free_bytes,
        filesystem_available_bytes,
    )
    if any(type(value) is not int or value < 0 for value in integer_observations):
        _fail("remote ordinal-2 host integer observation changed")
    if (
        any(
            type(value) is not str
            for value in (
                transport_target_alias,
                observed_hostname,
                observed_user,
                observed_python_invocation,
                observed_python_realpath,
                observed_source_root,
                cgroup_mount_filesystem_type,
                cgroup_mount_root,
            )
        )
        or
        type(observed_python_version) not in (tuple, list)
        or len(observed_python_version) != 3
        or any(type(value) is not int or value < 0 for value in observed_python_version)
        or attestation_stage not in {"PREPARE", "LAUNCH"}
    ):
        _fail("remote ordinal-2 host attestation stage or Python version changed")
    scope = _validate_cgroup_scope_path(cgroup_unified_scope_path)
    mount_root = _validate_cgroup_scope_path(cgroup_mount_root)
    if (
        type(cgroup_root_controllers) not in (list, tuple)
        or any(
            type(value) is not str or re.fullmatch(r"[a-z0-9_]+", value) is None
            for value in cgroup_root_controllers
        )
    ):
        _fail("remote ordinal-2 cgroup controller inventory changed")
    controllers = list(cgroup_root_controllers)
    if controllers != sorted(set(controllers)) or "memory" not in controllers:
        _fail("remote ordinal-2 cgroup v2 memory controller is unavailable")
    expected_cgroup_paths = _cgroup_scope_to_root_paths(scope)
    if type(cgroup_memory_ancestry) is not list:
        _fail("remote ordinal-2 cgroup memory ancestry changed type")
    normalized_ancestry: list[dict[str, Any]] = []
    for index, entry in enumerate(cgroup_memory_ancestry):
        if type(entry) is not dict or set(entry) != {
            "cgroup_path",
            "memory_max_mode",
            "memory_max_bytes",
            "memory_current_bytes",
        }:
            _fail("remote ordinal-2 cgroup ancestry fact schema changed")
        if index >= len(expected_cgroup_paths) or entry.get("cgroup_path") != expected_cgroup_paths[index]:
            _fail("remote ordinal-2 cgroup ancestry is incomplete or reordered")
        mode = entry.get("memory_max_mode")
        maximum = entry.get("memory_max_bytes")
        current = entry.get("memory_current_bytes")
        if mode == "MAX":
            valid = maximum is None and type(current) is int and current >= 0
        elif mode == "FINITE":
            valid = (
                type(maximum) is int
                and maximum > 0
                and type(current) is int
                and current >= 0
            )
        elif mode == "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES":
            valid = (
                entry["cgroup_path"] == "/"
                and maximum is None
                and current is None
            )
        else:
            valid = False
        if not valid:
            _fail("remote ordinal-2 cgroup ancestry fact changed semantics")
        normalized_ancestry.append(dict(entry))
    if len(normalized_ancestry) != len(expected_cgroup_paths):
        _fail("remote ordinal-2 cgroup ancestry omitted an ancestor")
    if any(
        entry["memory_max_mode"] == "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES"
        for entry in normalized_ancestry[:-1]
    ):
        _fail("remote ordinal-2 non-root cgroup omitted memory controller files")
    finite = [
        entry
        for entry in normalized_ancestry
        if entry["memory_max_mode"] == "FINITE"
    ]
    minimum_finite_maximum = (
        None if not finite else min(entry["memory_max_bytes"] for entry in finite)
    )
    minimum_finite_headroom = (
        None
        if not finite
        else min(
            entry["memory_max_bytes"] - entry["memory_current_bytes"]
            for entry in finite
        )
    )
    checks = {
        "transport_target_alias_exact": transport_target_alias == REMOTE_HOST_ALIAS,
        "hostname_exact": observed_hostname == REMOTE_HOSTNAME,
        "user_exact": observed_user == REMOTE_USER,
        "uid_exact": observed_uid == REMOTE_UID,
        "python_invocation_exact": observed_python_invocation == REMOTE_PYTHON,
        "python_realpath_exact": observed_python_realpath == REMOTE_PYTHON_REALPATH,
        "python_version_exact": tuple(observed_python_version) == REMOTE_PYTHON_VERSION,
        "source_root_exact": observed_source_root == str(REMOTE_SOURCE_ROOT),
        "memory_total_gate": memory_total_bytes >= MINIMUM_MEMORY_TOTAL_BYTES,
        "memory_available_gate": memory_available_bytes >= MINIMUM_MEMORY_AVAILABLE_BYTES,
        "memory_observation_consistent": memory_available_bytes <= memory_total_bytes,
        "swap_gate": (
            swap_total_bytes == 0 or swap_free_bytes >= MINIMUM_SWAP_FREE_BYTES
        ),
        "swap_observation_consistent": (
            swap_free_bytes <= swap_total_bytes
            and (swap_total_bytes != 0 or swap_free_bytes == 0)
        ),
        "filesystem_available_gate": (
            filesystem_available_bytes >= MINIMUM_FILESYSTEM_AVAILABLE_BYTES
        ),
        "cgroup_v2_memory_ancestry_complete": (
            cgroup_mount_filesystem_type == "cgroup2"
            and mount_root == "/"
            and
            len(normalized_ancestry) == len(expected_cgroup_paths)
            and normalized_ancestry[-1]["cgroup_path"] == "/"
        ),
        "cgroup_memory_gate": all(
            entry["memory_max_bytes"] >= MINIMUM_MEMORY_TOTAL_BYTES
            and entry["memory_max_bytes"] - entry["memory_current_bytes"]
            >= MINIMUM_MEMORY_AVAILABLE_BYTES
            for entry in finite
        ),
    }
    payload = {
        "schema": HOST_ATTESTATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "attestation_stage": attestation_stage,
        "transport_target_alias": transport_target_alias,
        "expected_hostname": REMOTE_HOSTNAME,
        "observed_hostname": observed_hostname,
        "expected_user": REMOTE_USER,
        "observed_user": observed_user,
        "expected_uid": REMOTE_UID,
        "observed_uid": observed_uid,
        "expected_python_invocation": REMOTE_PYTHON,
        "observed_python_invocation": observed_python_invocation,
        "expected_python_realpath": REMOTE_PYTHON_REALPATH,
        "observed_python_realpath": observed_python_realpath,
        "expected_python_version": list(REMOTE_PYTHON_VERSION),
        "observed_python_version": list(observed_python_version),
        "expected_source_root": str(REMOTE_SOURCE_ROOT),
        "observed_source_root": observed_source_root,
        "memory_total_bytes": memory_total_bytes,
        "memory_available_bytes": memory_available_bytes,
        "swap_total_bytes": swap_total_bytes,
        "swap_free_bytes": swap_free_bytes,
        "cgroup_version": 2,
        "cgroup_mount_point": "/sys/fs/cgroup",
        "cgroup_mount_filesystem_type": cgroup_mount_filesystem_type,
        "cgroup_mount_root": mount_root,
        "cgroup_unified_scope_path": scope,
        "cgroup_root_controllers": controllers,
        "cgroup_memory_ancestry": normalized_ancestry,
        "minimum_finite_cgroup_memory_max_bytes": minimum_finite_maximum,
        "minimum_finite_cgroup_memory_headroom_bytes": minimum_finite_headroom,
        "filesystem_available_bytes": filesystem_available_bytes,
        "minimum_memory_total_bytes": MINIMUM_MEMORY_TOTAL_BYTES,
        "minimum_memory_available_bytes": MINIMUM_MEMORY_AVAILABLE_BYTES,
        "minimum_swap_free_bytes_when_swap_configured": MINIMUM_SWAP_FREE_BYTES,
        "minimum_filesystem_available_bytes": MINIMUM_FILESYSTEM_AVAILABLE_BYTES,
        "checks": checks,
        "resource_gate_passed": all(checks.values()),
    }
    return {
        **payload,
        "host_attestation_id": _content_id(
            "acfqp:v42-remote-ordinal2:host-attestation", payload
        ),
    }


def verify_host_attestation_v42r1(
    raw_or_document: bytes | dict[str, Any], *, expected_stage: str,
    require_pass: bool = True,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 host attestation")
    expected = build_host_attestation_v42r1(
        transport_target_alias=document.get("transport_target_alias"),
        observed_hostname=document.get("observed_hostname"),
        observed_user=document.get("observed_user"),
        observed_uid=document.get("observed_uid"),
        observed_python_invocation=document.get("observed_python_invocation"),
        observed_python_realpath=document.get("observed_python_realpath"),
        observed_python_version=document.get("observed_python_version"),
        observed_source_root=document.get("observed_source_root"),
        memory_total_bytes=document.get("memory_total_bytes"),
        memory_available_bytes=document.get("memory_available_bytes"),
        swap_total_bytes=document.get("swap_total_bytes"),
        swap_free_bytes=document.get("swap_free_bytes"),
        cgroup_mount_filesystem_type=document.get(
            "cgroup_mount_filesystem_type"
        ),
        cgroup_mount_root=document.get("cgroup_mount_root"),
        cgroup_unified_scope_path=document.get("cgroup_unified_scope_path"),
        cgroup_root_controllers=document.get("cgroup_root_controllers"),
        cgroup_memory_ancestry=document.get("cgroup_memory_ancestry"),
        filesystem_available_bytes=document.get("filesystem_available_bytes"),
        attestation_stage=document.get("attestation_stage"),
    )
    if document != expected or document.get("attestation_stage") != expected_stage:
        _fail("remote ordinal-2 host attestation identity changed")
    if require_pass and document.get("resource_gate_passed") is not True:
        _fail("remote ordinal-2 host or resource gate did not pass")
    return document


def _read_regular_nofollow_stable(
    path: Path, maximum: int | None = None
) -> tuple[bytes, os.stat_result]:
    if maximum is not None and (type(maximum) is not int or maximum < 0):
        _fail("remote stable-read byte cap changed")
    before = path.lstat()
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or maximum is not None
        and before.st_size > maximum
    ):
        _fail(f"remote live source is not regular: {path}")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (before.st_dev, before.st_ino, before.st_mode, before.st_size)
            != (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size)
        ):
            _fail(f"remote live source changed while opening: {path}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if maximum is not None and total > maximum:
                _fail(f"remote live source exceeded its stable-read cap: {path}")
            chunks.append(chunk)
        after_read = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_close = path.lstat()
    stable = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(opened, name) != getattr(after_read, name)
        or getattr(opened, name) != getattr(after_close, name)
        for name in stable
    ):
        _fail(f"remote live source changed during read: {path}")
    return b"".join(chunks), after_read


def _hash_regular_nofollow_stable(
    path: Path, maximum: int
) -> tuple[int, str, os.stat_result]:
    if type(maximum) is not int or maximum < 0:
        _fail("remote stable-hash byte cap changed")
    before = path.lstat()
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size > maximum
    ):
        _fail("remote stable-hash artifact is nonregular or oversized")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (before.st_dev, before.st_ino, before.st_mode, before.st_size)
            != (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size)
        ):
            _fail("remote stable-hash artifact changed while opening")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > maximum:
                _fail("remote stable-hash artifact exceeded its cap")
            digest.update(chunk)
        after_read = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_close = path.lstat()
    stable = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(opened, name) != getattr(after_read, name)
        or getattr(opened, name) != getattr(after_close, name)
        for name in stable
    ):
        _fail("remote stable-hash artifact changed during read")
    return total, digest.hexdigest(), after_read


_FIXED_CONTROL_STABLE_FIELDS = (
    "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
    "st_size", "st_mtime_ns", "st_ctime_ns",
)


def _fixed_control_identity(observed: os.stat_result) -> tuple[int, ...]:
    return tuple(
        getattr(observed, field) for field in _FIXED_CONTROL_STABLE_FIELDS
    )


def _verify_fixed_control_snapshot_unchanged_v42r1(
    snapshot: dict[str, Any],
) -> None:
    if (
        _fixed_control_identity(REMOTE_ROOT.lstat())
        != tuple(snapshot["root_identity"])
        or sorted(entry.name for entry in REMOTE_ROOT.iterdir())
        != snapshot["root_inventory"]
    ):
        _fail("fixed remote control root changed across authority verification")
    for name, expected in snapshot["control_identities"].items():
        if _fixed_control_identity((REMOTE_ROOT / name).lstat()) != tuple(expected):
            _fail("fixed remote control changed across authority verification")


_LEXICAL_DIRECTORY_IDENTITY_FIELDS = (
    "st_dev",
    "st_ino",
    "st_mode",
    "st_uid",
    "st_gid",
)


def _snapshot_fixed_remote_root_lexical_chain_v42r1() -> list[dict[str, Any]]:
    """Open every fixed-root component without following a redirect.

    Shared ancestor timestamps and sizes are deliberately excluded: unrelated
    sibling activity must not invalidate an otherwise unchanged chain.  Full
    metadata for the fixed root and everything below it is captured separately.
    """

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open("/", flags)
    rows: list[dict[str, Any]] = []
    try:
        prefix = ""
        opened = os.fstat(descriptor)
        rows.append(
            {
                "absolute_path": "/",
                "identity": [
                    getattr(opened, field)
                    for field in _LEXICAL_DIRECTORY_IDENTITY_FIELDS
                ],
            }
        )
        for component in REMOTE_ROOT.parts[1:]:
            prefix += "/" + component
            before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                _fail("fixed remote control root ancestor is redirected")
            child = os.open(component, flags, dir_fd=descriptor)
            try:
                opened = os.fstat(child)
                if any(
                    getattr(before, field) != getattr(opened, field)
                    for field in _LEXICAL_DIRECTORY_IDENTITY_FIELDS
                ):
                    _fail("fixed remote control root ancestor changed while opening")
                rows.append(
                    {
                        "absolute_path": prefix,
                        "identity": [
                            getattr(opened, field)
                            for field in _LEXICAL_DIRECTORY_IDENTITY_FIELDS
                        ],
                    }
                )
            except BaseException:
                os.close(child)
                raise
            os.close(descriptor)
            descriptor = child
        return rows
    finally:
        os.close(descriptor)


def _snapshot_remote_phase_tree_metadata_v42r1() -> list[dict[str, Any]]:
    """Capture the exact fixed-control/source tree without reading file bytes."""

    rows: list[dict[str, Any]] = []
    for current, directories, filenames in os.walk(
        REMOTE_ROOT, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        directories.sort()
        filenames.sort()
        current_observed = current_path.lstat()
        if not stat.S_ISDIR(current_observed.st_mode):
            _fail("remote phase tree contains a redirected directory")
        relative_current = current_path.relative_to(REMOTE_ROOT)
        rows.append(
            {
                "relative_path": (
                    "." if relative_current == Path(".") else relative_current.as_posix()
                ),
                "entry_type": "DIRECTORY",
                "identity": list(_fixed_control_identity(current_observed)),
                "child_names": sorted(directories + filenames),
            }
        )
        for name in directories:
            observed = (current_path / name).lstat()
            if not stat.S_ISDIR(observed.st_mode):
                _fail("remote phase tree contains a symlinked directory")
        for name in filenames:
            path = current_path / name
            observed = path.lstat()
            if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
                _fail("remote phase tree contains a nonregular or linked file")
            rows.append(
                {
                    "relative_path": path.relative_to(REMOTE_ROOT).as_posix(),
                    "entry_type": "REGULAR_FILE",
                    "identity": list(_fixed_control_identity(observed)),
                    "child_names": None,
                }
            )
    if not rows or rows[0]["relative_path"] != ".":
        _fail("remote phase tree snapshot is empty or changed root")
    return rows


def _require_exact_remote_source_root(root: Path) -> Path:
    if not root.is_absolute() or root != REMOTE_SOURCE_ROOT:
        _fail("remote ordinal-2 source root differs from the fixed absolute root")
    observed = root.lstat()
    if (
        not stat.S_ISDIR(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o700
        or observed.st_uid != REMOTE_UID
    ):
        _fail("remote ordinal-2 source root is misowned or has unsafe mode")
    if root.resolve(strict=True) != REMOTE_SOURCE_ROOT:
        _fail("remote ordinal-2 source root or ancestor is redirected")
    return root


def _select_live_verification_root_v42r1(
    root: Path, *, require_fixed_root: bool,
    pinned_root_descriptor: int | None,
) -> Path:
    """Select a fixed path or an already-open descriptor alias without resolve."""

    if pinned_root_descriptor is not None:
        expected_alias = Path(f"/proc/self/fd/{pinned_root_descriptor}")
        if require_fixed_root or root != expected_alias:
            _fail("pinned remote verification root alias changed")
        try:
            observed = os.fstat(pinned_root_descriptor)
        except OSError as error:
            raise ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error(
                "pinned remote verification descriptor became unobservable"
            ) from error
        if not stat.S_ISDIR(observed.st_mode):
            _fail("pinned remote verification descriptor is not a directory")
        return root
    return _require_exact_remote_source_root(root) if require_fixed_root else root.resolve()


def _git_blob_oid_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()  # noqa: S324 - Git SHA-1 object identity


def _verify_exact_mutable_state_root_v42r1(
    path: Path, *, allowed_files: dict[str, int], require_fixed_root: bool
) -> None:
    """Verify, but do not interpret, one narrowly reserved mutable subtree."""

    before = path.lstat()
    if (
        not stat.S_ISDIR(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o700
        or require_fixed_root
        and before.st_uid != REMOTE_UID
    ):
        _fail("remote mutable state root is redirected, misowned, or unsafe")
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    stable = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_uid",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    try:
        opened = os.fstat(descriptor)
        if any(getattr(before, field) != getattr(opened, field) for field in stable):
            _fail("remote mutable state root changed while opening")
        observed_names = os.listdir(descriptor)
        if len(observed_names) != len(set(observed_names)):
            _fail("remote mutable state root contains duplicate entries")
        pinned_root = Path(f"/proc/self/fd/{descriptor}")
        for name in observed_names:
            if name not in allowed_files:
                _fail("remote mutable state root has an unrecognized entry")
            _, _, observed = _hash_regular_nofollow_stable(
                pinned_root / name, allowed_files[name]
            )
            if (
                stat.S_IMODE(observed.st_mode) != 0o400
                or require_fixed_root
                and observed.st_uid != REMOTE_UID
            ):
                _fail("remote mutable state artifact is misowned or has unsafe mode")
        after = os.fstat(descriptor)
        after_path = path.lstat()
        if any(
            getattr(opened, field) != getattr(after, field)
            or getattr(opened, field) != getattr(after_path, field)
            for field in stable
        ):
            _fail("remote mutable state root changed during inventory")
    finally:
        os.close(descriptor)


def _snapshot_transport_tree_metadata_v42r1(
    root: Path,
) -> dict[str, tuple[int, int, int, int, int, int, int, int]]:
    """Capture one no-follow whole-tree identity/metadata boundary."""

    stable_fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size",
        "st_mtime_ns", "st_ctime_ns",
    )
    snapshot: dict[str, tuple[int, int, int, int, int, int, int, int]] = {}

    def observe(path: Path) -> None:
        try:
            observed = path.lstat()
        except OSError as error:
            raise ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error(
                "remote transport tree changed during metadata snapshot"
            ) from error
        relative = "." if path == root else path.relative_to(root).as_posix()
        fact = tuple(getattr(observed, field) for field in stable_fields)
        previous = snapshot.get(relative)
        if previous is not None and previous != fact:
            _fail("remote transport tree changed within metadata snapshot")
        snapshot[relative] = fact

    observe(root)
    for current, directories, filenames in os.walk(
        root, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        observe(current_path)
        if len(set(directories)) != len(directories) or len(set(filenames)) != len(
            filenames
        ):
            _fail("remote transport tree contains duplicate directory entries")
        for name in (*directories, *filenames):
            observe(current_path / name)
    return snapshot


def verify_live_transport_inventory_v42r1(
    root: Path, transport_manifest: dict[str, Any], source_manifest: dict[str, Any],
    *, require_fixed_root: bool = True,
    pinned_root_descriptor: int | None = None,
    local_materialization_attempt: bytes | dict[str, Any] | None = None,
    remote_materialization_attempt: bytes | dict[str, Any] | None = None,
    materialization_terminal: bytes | dict[str, Any] | None = None,
) -> None:
    source_manifest = verify_source_manifest_v42r1(source_manifest)
    manifest = verify_transport_manifest_v42r1(
        transport_manifest, source_manifest=source_manifest
    )
    verified_terminal: dict[str, Any] | None = None
    if any(
        value is not None
        for value in (
            local_materialization_attempt,
            remote_materialization_attempt,
            materialization_terminal,
        )
    ):
        if (
            local_materialization_attempt is None
            or remote_materialization_attempt is None
            or materialization_terminal is None
        ):
            _fail("remote materialization authority chain is incomplete")
        local_materialization_attempt = verify_local_materialization_attempt_v42r1(
            local_materialization_attempt,
            source_manifest=source_manifest,
            transport_manifest=manifest,
        )
        remote_materialization_attempt = verify_remote_materialization_attempt_v42r1(
            remote_materialization_attempt,
            local_materialization_attempt=local_materialization_attempt,
            source_manifest=source_manifest,
            transport_manifest=manifest,
        )
        verified_terminal = verify_materialization_terminal_v42r1(
            materialization_terminal,
            local_materialization_attempt=local_materialization_attempt,
            remote_materialization_attempt=remote_materialization_attempt,
            source_manifest=source_manifest,
            transport_manifest=manifest,
        )
    root = _select_live_verification_root_v42r1(
        root,
        require_fixed_root=require_fixed_root,
        pinned_root_descriptor=pinned_root_descriptor,
    )
    tree_before = _snapshot_transport_tree_metadata_v42r1(root)
    allowed = {fact["relative_path"]: fact for fact in manifest["transport_facts"]}
    allowed_directories: set[str] = set()
    for relative in allowed:
        parent = PurePosixPath(relative).parent
        while parent != PurePosixPath("."):
            allowed_directories.add(parent.as_posix())
            parent = parent.parent
    observed_paths: set[str] = set()
    mutable_root_files = {
        PREPARE_ATTEMPT_JOURNAL_NAME,
        PREPARE_FAILURE_JOURNAL_NAME,
        LAUNCH_ATTEMPT_JOURNAL_NAME,
        LAUNCH_FAILURE_JOURNAL_NAME,
    }
    mutable_state_roots = {
        Path(relative): allowed_files
        for relative, allowed_files in _MUTABLE_STATE_FILES_BY_ROOT.items()
    }
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_current = current_path.relative_to(root)
        for name in tuple(directories):
            path = current_path / name
            relative_path = path.relative_to(root)
            relative_directory = relative_path.as_posix()
            mutable_files = mutable_state_roots.get(relative_path)
            if mutable_files is not None:
                # The exact ordinal-2 mutable roots are the only pruned
                # subtrees.  Their parents and every committed sibling under
                # .tmp remain part of the ordinary manifest walk.
                if relative_directory in allowed_directories:
                    _fail("reserved mutable state collides with transport inventory")
                _verify_exact_mutable_state_root_v42r1(
                    path,
                    allowed_files=mutable_files,
                    require_fixed_root=require_fixed_root,
                )
                directories.remove(name)
                continue
            directory_observed = path.lstat()
            if (
                not stat.S_ISDIR(directory_observed.st_mode)
                or relative_directory not in allowed_directories
                or stat.S_IMODE(directory_observed.st_mode) != 0o700
                or require_fixed_root
                and directory_observed.st_uid != REMOTE_UID
            ):
                _fail(f"remote transport directory is unmanifested or unsafe: {path}")
        for name in filenames:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if relative_current == Path(".") and name == MATERIALIZATION_TERMINAL_NAME:
                if verified_terminal is None:
                    _fail("remote source has an unbound materialization terminal")
                raw, observed = _read_regular_nofollow_stable(path)
                if (
                    stat.S_IMODE(observed.st_mode) != 0o400
                    or require_fixed_root and observed.st_uid != REMOTE_UID
                    or raw != canonical_json_bytes(verified_terminal)
                ):
                    _fail("remote materialization terminal bytes or mode changed")
                continue
            if relative_current == Path(".") and name in mutable_root_files:
                _, _, observed = _hash_regular_nofollow_stable(path, 4 * 1024**2)
                if (
                    stat.S_IMODE(observed.st_mode) != 0o400
                    or require_fixed_root and observed.st_uid != REMOTE_UID
                ):
                    _fail("remote mutable journal is nonregular or has unsafe mode")
                continue
            if relative not in allowed:
                _fail(f"remote transport contains an unmanifested file: {relative}")
            observed_paths.add(relative)
    if observed_paths != set(allowed):
        missing = sorted(set(allowed) - observed_paths)
        _fail("remote transport is missing manifested files: " + ", ".join(missing[:8]))
    for relative, fact in allowed.items():
        raw, observed = _read_regular_nofollow_stable(root / relative)
        if (
            stat.S_IMODE(observed.st_mode) != int(MATERIALIZED_SOURCE_FILE_MODE, 8)
            or require_fixed_root and observed.st_uid != REMOTE_UID
        ):
            _fail(f"remote transport member mode changed: {relative}")
        if (
            len(raw) != fact["byte_count"]
            or hashlib.sha256(raw).hexdigest() != fact["sha256"]
            or _git_blob_oid_sha1(raw) != fact["git_blob_oid"]
        ):
            _fail(f"remote transport member bytes or Git blob identity changed: {relative}")
    tree_after = _snapshot_transport_tree_metadata_v42r1(root)
    if tree_after != tree_before:
        _fail("remote transport tree changed across full inventory verification")


def verify_fixed_transport_controls_v42r1() -> dict[str, Any]:
    """Re-read every fixed transported control with exact bytes, mode, and owner."""

    lexical_chain_before = _snapshot_fixed_remote_root_lexical_chain_v42r1()
    root_observed = REMOTE_ROOT.lstat()
    root_inventory = sorted(entry.name for entry in REMOTE_ROOT.iterdir())
    if (
        not stat.S_ISDIR(root_observed.st_mode)
        or stat.S_IMODE(root_observed.st_mode) != 0o700
        or root_observed.st_uid != REMOTE_UID
    ):
        _fail("fixed remote control root is redirected, misowned, or unsafe")
    source_raw, source_observed = _read_regular_nofollow_stable(
        REMOTE_ROOT / SOURCE_MANIFEST_NAME, 64 * 1024**2
    )
    transport_raw, transport_observed = _read_regular_nofollow_stable(
        REMOTE_ROOT / TRANSPORT_MANIFEST_NAME, 64 * 1024**2
    )
    local_raw, local_observed = _read_regular_nofollow_stable(
        REMOTE_ROOT / LOCAL_MATERIALIZATION_ATTEMPT_NAME, 4 * 1024**2
    )
    capsule_count, capsule_sha256, capsule_observed = _hash_regular_nofollow_stable(
        REMOTE_ROOT / SOURCE_CAPSULE_NAME, 2 * 1024**3
    )
    pyz_count, pyz_sha256, pyz_observed = _hash_regular_nofollow_stable(
        REMOTE_ROOT / REMOTE_BOOTSTRAP_PYZ_NAME, 64 * 1024**2
    )
    if any(
        stat.S_IMODE(observed.st_mode) != 0o400 or observed.st_uid != REMOTE_UID
        for observed in (
            source_observed,
            transport_observed,
            local_observed,
            capsule_observed,
            pyz_observed,
        )
    ):
        _fail("fixed transported control mode or owner changed")
    source_manifest = verify_source_manifest_v42r1(source_raw)
    transport_manifest = verify_transport_manifest_v42r1(
        transport_raw, source_manifest=source_manifest
    )
    if (
        capsule_count != transport_manifest["source_archive_byte_count"]
        or capsule_sha256 != transport_manifest["source_archive_sha256"]
        or pyz_count
        != transport_manifest["remote_bootstrap_pyz_artifact"]["pyz_byte_count"]
        or pyz_sha256
        != transport_manifest["remote_bootstrap_pyz_artifact"]["pyz_sha256"]
    ):
        _fail("fixed transported source capsule or bootstrap pyz bytes changed")
    local_attempt = verify_local_materialization_attempt_v42r1(
        local_raw,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    control_identities = {
        SOURCE_MANIFEST_NAME: _fixed_control_identity(source_observed),
        TRANSPORT_MANIFEST_NAME: _fixed_control_identity(transport_observed),
        LOCAL_MATERIALIZATION_ATTEMPT_NAME: _fixed_control_identity(local_observed),
        SOURCE_CAPSULE_NAME: _fixed_control_identity(capsule_observed),
        REMOTE_BOOTSTRAP_PYZ_NAME: _fixed_control_identity(pyz_observed),
    }
    snapshot = {
        "root_identity": list(_fixed_control_identity(root_observed)),
        "root_inventory": root_inventory,
        "control_identities": {
            name: list(identity) for name, identity in control_identities.items()
        },
    }
    _verify_fixed_control_snapshot_unchanged_v42r1(snapshot)
    if _snapshot_fixed_remote_root_lexical_chain_v42r1() != lexical_chain_before:
        _fail("fixed remote control ancestor changed across authority verification")
    return {
        "source_manifest": source_manifest,
        "transport_manifest": transport_manifest,
        "local_materialization_attempt": local_attempt,
        "source_manifest_raw": source_raw,
        "transport_manifest_raw": transport_raw,
        "local_materialization_attempt_raw": local_raw,
        "source_archive_byte_count": capsule_count,
        "source_archive_sha256": capsule_sha256,
        "remote_bootstrap_pyz_byte_count": pyz_count,
        "remote_bootstrap_pyz_sha256": pyz_sha256,
        "fixed_control_snapshot": snapshot,
    }


def verify_fixed_materialization_success_v42r1(
    root: Path, transport_manifest: dict[str, Any], source_manifest: dict[str, Any]
) -> dict[str, Any]:
    """Require the atomic-publish authority chain for the fixed formal source."""

    root = _require_exact_remote_source_root(root)
    controls = verify_fixed_transport_controls_v42r1()
    if (
        controls["source_manifest"] != source_manifest
        or controls["transport_manifest"] != transport_manifest
    ):
        _fail("fixed transported controls differ from requested materialization authority")
    local_attempt = controls["local_materialization_attempt"]
    remote_raw, remote_observed = _read_regular_nofollow_stable(
        REMOTE_ROOT / REMOTE_MATERIALIZATION_ATTEMPT_NAME, 4 * 1024**2
    )
    terminal_raw, terminal_observed = _read_regular_nofollow_stable(
        root / MATERIALIZATION_TERMINAL_NAME
    )
    if any(
        stat.S_IMODE(observed.st_mode) != 0o400 or observed.st_uid != REMOTE_UID
        for observed in (remote_observed, terminal_observed)
    ):
        _fail("fixed materialization authority mode or owner changed")
    remote_attempt = verify_remote_materialization_attempt_v42r1(
        remote_raw,
        local_materialization_attempt=local_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    terminal = verify_materialization_terminal_v42r1(
        terminal_raw,
        local_materialization_attempt=local_attempt,
        remote_materialization_attempt=remote_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    verify_live_materialized_source_closure_v42r1(
        root,
        transport_manifest,
        source_manifest,
        local_materialization_attempt=local_attempt,
        remote_materialization_attempt=remote_attempt,
        materialization_terminal=terminal,
    )
    if (
        _fixed_control_identity(
            (REMOTE_ROOT / REMOTE_MATERIALIZATION_ATTEMPT_NAME).lstat()
        )
        != _fixed_control_identity(remote_observed)
        or _fixed_control_identity((root / MATERIALIZATION_TERMINAL_NAME).lstat())
        != _fixed_control_identity(terminal_observed)
    ):
        _fail("fixed materialization attempt or terminal changed across verification")
    _verify_fixed_control_snapshot_unchanged_v42r1(
        controls["fixed_control_snapshot"]
    )
    return {
        "local_materialization_attempt_id": local_attempt[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": remote_attempt[
            "remote_materialization_attempt_id"
        ],
        "materialization_terminal_id": terminal["materialization_terminal_id"],
        "remote_bootstrap_runtime_binding": remote_attempt[
            "remote_bootstrap_runtime_binding"
        ],
        "remote_bootstrap_runtime_binding_id": remote_attempt[
            "remote_bootstrap_runtime_binding_id"
        ],
    }


def verify_remote_control_phase_inventory_v42r1(
    phase: str, *, prepare_receipt: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Require the exact top-level remote control inventory for one phase."""

    phase_extras = {
        "POST_MATERIALIZATION_PREPARE": frozenset(),
        "POST_PREPARE_AWAITING_LOCAL_LAUNCH": frozenset(
            {PREPARE_HOST_ATTESTATION_NAME}
        ),
        "POST_PREPARE_PRELAUNCH": frozenset(
            {PREPARE_HOST_ATTESTATION_NAME, LOCAL_LAUNCH_ATTEMPT_NAME}
        ),
        "POST_LAUNCH": frozenset(
            {
                PREPARE_HOST_ATTESTATION_NAME,
                LOCAL_LAUNCH_ATTEMPT_NAME,
                LAUNCH_HOST_ATTESTATION_NAME,
            }
        ),
    }
    if phase not in phase_extras:
        _fail("remote control phase changed")
    lexical_chain_before = _snapshot_fixed_remote_root_lexical_chain_v42r1()
    phase_tree_before = _snapshot_remote_phase_tree_metadata_v42r1()
    controls = verify_fixed_transport_controls_v42r1()
    source_manifest = controls["source_manifest"]
    transport_manifest = controls["transport_manifest"]
    materialization = verify_fixed_materialization_success_v42r1(
        REMOTE_SOURCE_ROOT, transport_manifest, source_manifest
    )
    base_names = {
        LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        SOURCE_CAPSULE_NAME,
        SOURCE_MANIFEST_NAME,
        TRANSPORT_MANIFEST_NAME,
        REMOTE_BOOTSTRAP_PYZ_NAME,
        REMOTE_MATERIALIZATION_ATTEMPT_NAME,
        REMOTE_SOURCE_ROOT.name,
    }
    expected_names = base_names | set(phase_extras[phase])
    if {entry.name for entry in REMOTE_ROOT.iterdir()} != expected_names:
        _fail("remote control phase inventory has an extra or missing entry")
    for name in phase_extras[phase]:
        path = REMOTE_ROOT / name
        observed = path.lstat()
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o400
            or observed.st_uid != REMOTE_UID
        ):
            _fail("remote phase control is nonregular, misowned, or unsafe")
    result = {**controls, **materialization, "phase": phase}
    if phase != "POST_MATERIALIZATION_PREPARE":
        if prepare_receipt is None:
            _fail("post-prepare remote control phase omitted its receipt")
        if (
            prepare_receipt.get("source_manifest") != source_manifest
            or prepare_receipt.get("transport_manifest") != transport_manifest
        ):
            _fail("post-prepare remote controls differ from the prepare receipt")
        prepare_host_raw, _ = _read_regular_nofollow_stable(
            REMOTE_ROOT / PREPARE_HOST_ATTESTATION_NAME, 4 * 1024**2
        )
        prepare_host = verify_host_attestation_v42r1(
            prepare_host_raw, expected_stage="PREPARE", require_pass=True
        )
        if prepare_host != prepare_receipt.get("prepare_host_attestation"):
            _fail("remote prepare host control differs from the prepare receipt")
        result["prepare_host_attestation"] = prepare_host
        if phase in {"POST_PREPARE_PRELAUNCH", "POST_LAUNCH"}:
            local_launch_raw, _ = _read_regular_nofollow_stable(
                REMOTE_ROOT / LOCAL_LAUNCH_ATTEMPT_NAME, 4 * 1024**2
            )
            local_launch = verify_local_launch_attempt_v42r1(
                local_launch_raw, prepare_receipt=prepare_receipt
            )
            result.update(
                {
                    "local_launch_attempt": local_launch,
                    "local_launch_attempt_raw": local_launch_raw,
                }
            )
    if phase == "POST_LAUNCH":
        launch_host_raw, _ = _read_regular_nofollow_stable(
            REMOTE_ROOT / LAUNCH_HOST_ATTESTATION_NAME, 4 * 1024**2
        )
        result["launch_host_attestation"] = verify_host_attestation_v42r1(
            launch_host_raw, expected_stage="LAUNCH", require_pass=True
        )
    if (
        {entry.name for entry in REMOTE_ROOT.iterdir()} != expected_names
        or _snapshot_fixed_remote_root_lexical_chain_v42r1()
        != lexical_chain_before
        or _snapshot_remote_phase_tree_metadata_v42r1() != phase_tree_before
    ):
        _fail("remote control phase or ancestor tree changed during verification")
    return result


def verify_predecessor_retention_ready_v42r1(root: Path) -> dict[str, Any]:
    if not PREDECESSOR_RETENTION_READY:
        _fail("remote ordinal-2 formal authority disabled pending predecessor retention freeze")
    retained_raw, _ = _read_regular_nofollow_stable(
        root / PREDECESSOR_RETENTION_MANIFEST_RELATIVE
    )
    verification_raw, _ = _read_regular_nofollow_stable(
        root / PREDECESSOR_INDEPENDENT_VERIFICATION_RELATIVE
    )
    binding = build_predecessor_retention_binding_v42r1(
        retention_manifest_sha256=hashlib.sha256(retained_raw).hexdigest(),
        retention_manifest_byte_count=len(retained_raw),
        independent_verification_sha256=hashlib.sha256(verification_raw).hexdigest(),
        independent_verification_byte_count=len(verification_raw),
    )
    retained = _canonical_document(retained_raw, "ordinal-1 retention manifest")
    verification = _canonical_document(
        verification_raw, "ordinal-1 retention independent verification"
    )
    if (
        retained.get("formal_identity") != PREDECESSOR_FORMAL_IDENTITY
        or retained.get("source_commit") != PREDECESSOR_SOURCE_COMMIT
        or retained.get("source_tree") != PREDECESSOR_SOURCE_TREE
        or retained.get("retention_manifest_id")
        != PREDECESSOR_RETENTION_MANIFEST_ID
        or retained.get("runner_failure_id") != PREDECESSOR_RUNNER_FAILURE_ID
        or retained.get("prepare_receipt_id") != PREDECESSOR_PREPARE_RECEIPT_ID
        or retained.get("runner_attempt_id") != PREDECESSOR_RUNNER_ATTEMPT_ID
        or retained.get("worker_start_id") != PREDECESSOR_WORKER_START_ID
        or retained.get("authority_consumption_id")
        != PREDECESSOR_AUTHORITY_CONSUMPTION_ID
        or retained.get("formal_campaign_artifact_present") is not False
        or retained.get("formal_verification_artifact_present") is not False
        or retained.get("formal_terminal_artifact_present") is not False
        or retained.get("scientific_success") is not False
        or retained.get("same_identity_rerun_forbidden") is not True
        or verification.get("formal_identity") != PREDECESSOR_FORMAL_IDENTITY
        or verification.get("retention_manifest_id")
        != PREDECESSOR_RETENTION_MANIFEST_ID
        or verification.get("independent_verification_id")
        != PREDECESSOR_INDEPENDENT_VERIFICATION_ID
        or verification.get("runner_failure_id") != PREDECESSOR_RUNNER_FAILURE_ID
        or verification.get("formal_campaign_artifact_absent") is not True
        or verification.get("formal_verification_artifact_absent") is not True
        or verification.get("formal_terminal_artifact_absent") is not True
        or verification.get("scientific_success") is not False
        or verification.get("same_identity_rerun_forbidden") is not True
    ):
        _fail("remote ordinal-2 predecessor failure closure changed")
    return binding


def _read_meminfo_bytes() -> dict[str, int]:
    raw, _ = _read_regular_nofollow_stable(Path("/proc/meminfo"))
    values: dict[str, int] = {}
    for line in raw.decode("ascii").splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] == "kB" and fields[0].endswith(":"):
            try:
                values[fields[0][:-1]] = int(fields[1]) * 1024
            except ValueError:
                _fail("remote /proc/meminfo contains a malformed integer")
    for required in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
        if required not in values:
            _fail("remote /proc/meminfo omitted " + required)
    return values


def _validate_cgroup_scope_path(value: Any) -> str:
    if (
        type(value) is not str
        or not value
        or "\\" in value
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        _fail("remote cgroup v2 unified scope path changed encoding")
    parsed = PurePosixPath(value)
    if (
        not parsed.is_absolute()
        or parsed.as_posix() != value
        or any(part in {"", ".", ".."} for part in parsed.parts[1:])
        or any(
            re.fullmatch(r"[A-Za-z0-9_.:@-]+", part) is None
            for part in parsed.parts[1:]
        )
    ):
        _fail("remote cgroup v2 unified scope path is noncanonical")
    return value


def _cgroup_scope_to_root_paths(scope: str) -> list[str]:
    current = PurePosixPath(_validate_cgroup_scope_path(scope))
    result: list[str] = []
    while True:
        result.append(current.as_posix())
        if current == PurePosixPath("/"):
            return result
        current = current.parent


def _read_exact_cgroup_scope(
    path: Path = Path("/proc/self/cgroup"),
) -> tuple[str, bytes]:
    raw, _ = _read_regular_nofollow_stable(path)
    if (
        len(raw) > 4096
        or raw.count(b"\n") != 1
        or not raw.endswith(b"\n")
        or any(byte < 0x20 or byte == 0x7F for byte in raw[:-1])
    ):
        _fail("remote /proc/self/cgroup is not one bounded canonical record")
    try:
        line = raw[:-1].decode("ascii")
    except UnicodeDecodeError as error:
        raise ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error(
            "remote /proc/self/cgroup is not ASCII"
        ) from error
    if line.count("::") != 1 or not line.startswith("0::"):
        _fail("remote process does not have one exact unified cgroup v2 entry")
    scope = _validate_cgroup_scope_path(line[3:])
    return scope, raw


def _parse_cgroup_decimal(raw: bytes, label: str) -> int:
    if (
        not raw.endswith(b"\n")
        or raw.endswith(b"\n\n")
        or re.fullmatch(rb"(?:0|[1-9][0-9]*)\n", raw) is None
    ):
        _fail(f"remote cgroup {label} is not one canonical decimal")
    value = int(raw[:-1])
    if value < 0:
        _fail(f"remote cgroup {label} is negative")
    return value


def _parse_cgroup_memory_max(raw: bytes) -> tuple[str, int | None]:
    if raw == b"max\n":
        return "MAX", None
    value = _parse_cgroup_decimal(raw, "memory.max")
    if value <= 0:
        _fail("remote cgroup finite memory.max is not positive")
    return "FINITE", value


def _read_cgroup_root_controllers(
    cgroup_root: Path = Path("/sys/fs/cgroup"),
) -> tuple[list[str], bytes]:
    raw, _ = _read_regular_nofollow_stable(cgroup_root / "cgroup.controllers")
    if len(raw) > 4096 or not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail("remote cgroup.controllers is not bounded canonical text")
    try:
        tokens = raw[:-1].decode("ascii").split(" ")
    except UnicodeDecodeError as error:
        raise ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error(
            "remote cgroup.controllers is not ASCII"
        ) from error
    if (
        not tokens
        or any(re.fullmatch(r"[a-z0-9_]+", token) is None for token in tokens)
        or len(tokens) != len(set(tokens))
        or "memory" not in tokens
    ):
        _fail("remote cgroup v2 root does not expose the memory controller")
    return sorted(tokens), raw


def _read_cgroup2_mount_observation(
    path: Path = Path("/proc/self/mountinfo"),
) -> tuple[str, str, bytes]:
    raw, _ = _read_regular_nofollow_stable(path)
    if len(raw) > 1024 * 1024 or not raw.endswith(b"\n"):
        _fail("remote /proc/self/mountinfo is oversized or noncanonical")
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error(
            "remote /proc/self/mountinfo is not ASCII"
        ) from error
    matches: list[tuple[str, str]] = []
    for line in lines:
        fields = line.split(" ")
        try:
            separator = fields.index("-")
        except ValueError:
            _fail("remote /proc/self/mountinfo record omitted its separator")
        if separator < 6 or len(fields) < separator + 3:
            _fail("remote /proc/self/mountinfo record is truncated")
        if fields[4] == "/sys/fs/cgroup":
            matches.append((fields[separator + 1], fields[3]))
    if len(matches) != 1:
        _fail("remote cgroup mount point is absent or ambiguous")
    filesystem_type, mount_root = matches[0]
    mount_root = _validate_cgroup_scope_path(mount_root)
    if filesystem_type != "cgroup2" or mount_root != "/":
        _fail("remote cgroup mount is not the exact unified cgroup2 root")
    return filesystem_type, mount_root, raw


def _read_cgroup_memory_observation(
    *,
    proc_self_cgroup: Path = Path("/proc/self/cgroup"),
    cgroup_root: Path = Path("/sys/fs/cgroup"),
) -> tuple[str, list[str], list[dict[str, Any]]]:
    scope, scope_raw_before = _read_exact_cgroup_scope(proc_self_cgroup)
    controllers, controllers_raw_before = _read_cgroup_root_controllers(cgroup_root)
    root_observed = cgroup_root.lstat()
    if (
        not stat.S_ISDIR(root_observed.st_mode)
        or cgroup_root.resolve(strict=True) != cgroup_root
    ):
        _fail("remote cgroup v2 mount root is redirected or non-directory")
    ancestry: list[dict[str, Any]] = []
    directory_observations: list[tuple[Path, os.stat_result]] = []
    root_files_absent = False
    for cgroup_path in _cgroup_scope_to_root_paths(scope):
        directory = (
            cgroup_root
            if cgroup_path == "/"
            else cgroup_root.joinpath(*PurePosixPath(cgroup_path).parts[1:])
        )
        observed = directory.lstat()
        if (
            not stat.S_ISDIR(observed.st_mode)
            or directory.resolve(strict=True) != directory
        ):
            _fail("remote cgroup v2 ancestry contains a redirect or non-directory")
        directory_observations.append((directory, observed))
        maximum_path = directory / "memory.max"
        current_path = directory / "memory.current"
        try:
            maximum_raw_before, _ = _read_regular_nofollow_stable(maximum_path)
        except FileNotFoundError:
            try:
                current_path.lstat()
            except FileNotFoundError:
                if cgroup_path != "/":
                    _fail("remote non-root cgroup omitted memory.max/current")
                root_files_absent = True
                ancestry.append(
                    {
                        "cgroup_path": "/",
                        "memory_max_mode": "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES",
                        "memory_max_bytes": None,
                        "memory_current_bytes": None,
                    }
                )
                continue
            _fail("remote cgroup memory.max/current are only partially present")
        try:
            current_raw_before, _ = _read_regular_nofollow_stable(current_path)
        except FileNotFoundError:
            _fail("remote cgroup memory.max/current are only partially present")
        maximum_raw_after, _ = _read_regular_nofollow_stable(maximum_path)
        current_raw_after, _ = _read_regular_nofollow_stable(current_path)
        if maximum_raw_after != maximum_raw_before:
            _fail("remote cgroup memory.max changed during attestation")
        mode, maximum = _parse_cgroup_memory_max(maximum_raw_before)
        current = max(
            _parse_cgroup_decimal(current_raw_before, "memory.current"),
            _parse_cgroup_decimal(current_raw_after, "memory.current"),
        )
        ancestry.append(
            {
                "cgroup_path": cgroup_path,
                "memory_max_mode": mode,
                "memory_max_bytes": maximum,
                "memory_current_bytes": current,
            }
        )
    scope_after, scope_raw_after = _read_exact_cgroup_scope(proc_self_cgroup)
    controllers_after, controllers_raw_after = _read_cgroup_root_controllers(
        cgroup_root
    )
    if (
        scope_after != scope
        or scope_raw_after != scope_raw_before
        or controllers_after != controllers
        or controllers_raw_after != controllers_raw_before
    ):
        _fail("remote cgroup scope or controller inventory changed during attestation")
    for directory, before in directory_observations:
        after = directory.lstat()
        if (
            before.st_dev,
            before.st_ino,
            before.st_mode,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
        ):
            _fail("remote cgroup ancestry changed during attestation")
    if root_files_absent:
        for path in (
            cgroup_root / "memory.max",
            cgroup_root / "memory.current",
        ):
            try:
                path.lstat()
            except FileNotFoundError:
                continue
            _fail("remote delegated cgroup root memory files appeared during attestation")
    return scope, controllers, ancestry


def observe_host_attestation_v42r1(
    root: Path, *, transport_target_alias: str, attestation_stage: str,
) -> dict[str, Any]:
    root = _require_exact_remote_source_root(root)
    meminfo = _read_meminfo_bytes()
    cgroup_filesystem_type, cgroup_mount_root, mountinfo_raw_before = (
        _read_cgroup2_mount_observation()
    )
    cgroup_scope, cgroup_controllers, cgroup_ancestry = (
        _read_cgroup_memory_observation()
    )
    _, _, mountinfo_raw_after = _read_cgroup2_mount_observation()
    if mountinfo_raw_after != mountinfo_raw_before:
        _fail("remote cgroup mount topology changed during attestation")
    filesystem = os.statvfs(REMOTE_ROOT.parent)
    return build_host_attestation_v42r1(
        transport_target_alias=transport_target_alias,
        observed_hostname=socket.gethostname(),
        observed_user=pwd.getpwuid(os.getuid()).pw_name,
        observed_uid=os.getuid(),
        observed_python_invocation=REMOTE_PYTHON,
        observed_python_realpath=str(Path(sys.executable).resolve(strict=True)),
        observed_python_version=(
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        ),
        observed_source_root=str(root),
        memory_total_bytes=meminfo["MemTotal"],
        memory_available_bytes=meminfo["MemAvailable"],
        swap_total_bytes=meminfo["SwapTotal"],
        swap_free_bytes=meminfo["SwapFree"],
        cgroup_mount_filesystem_type=cgroup_filesystem_type,
        cgroup_mount_root=cgroup_mount_root,
        cgroup_unified_scope_path=cgroup_scope,
        cgroup_root_controllers=cgroup_controllers,
        cgroup_memory_ancestry=cgroup_ancestry,
        filesystem_available_bytes=filesystem.f_bavail * filesystem.f_frsize,
        attestation_stage=attestation_stage,
    )


def verify_live_source_matches_manifest_v42(
    root: Path, manifest: dict[str, Any], *, require_fixed_root: bool = True,
    pinned_root_descriptor: int | None = None,
) -> None:
    manifest = verify_source_manifest_v42r1(manifest)
    root = _select_live_verification_root_v42r1(
        root,
        require_fixed_root=require_fixed_root,
        pinned_root_descriptor=pinned_root_descriptor,
    )
    allowed = {fact["relative_path"]: fact for fact in manifest["source_facts"]}
    for relative, fact in allowed.items():
        raw, observed = _read_regular_nofollow_stable(root / relative)
        if (
            stat.S_IMODE(observed.st_mode) != int(MATERIALIZED_SOURCE_FILE_MODE, 8)
            or require_fixed_root and observed.st_uid != REMOTE_UID
        ):
            _fail(f"remote source materialized mode changed: {relative}")
        if (
            len(raw) != fact["byte_count"]
            or hashlib.sha256(raw).hexdigest() != fact["sha256"]
            or _git_blob_oid_sha1(raw) != fact["git_blob_oid"]
        ):
            _fail(f"remote live source bytes or Git blob identity changed: {relative}")


def verify_live_materialized_source_closure_v42r1(
    root: Path, transport_manifest: dict[str, Any], source_manifest: dict[str, Any],
    *, require_fixed_root: bool = True,
    pinned_root_descriptor: int | None = None,
    local_materialization_attempt: bytes | dict[str, Any] | None = None,
    remote_materialization_attempt: bytes | dict[str, Any] | None = None,
    materialization_terminal: bytes | dict[str, Any] | None = None,
) -> None:
    """Close one whole-tree boundary around transport and Python source checks."""

    resolved_root = _select_live_verification_root_v42r1(
        root,
        require_fixed_root=require_fixed_root,
        pinned_root_descriptor=pinned_root_descriptor,
    )
    tree_before = _snapshot_transport_tree_metadata_v42r1(resolved_root)
    verify_live_transport_inventory_v42r1(
        resolved_root,
        transport_manifest,
        source_manifest,
        require_fixed_root=require_fixed_root,
        pinned_root_descriptor=pinned_root_descriptor,
        local_materialization_attempt=local_materialization_attempt,
        remote_materialization_attempt=remote_materialization_attempt,
        materialization_terminal=materialization_terminal,
    )
    verify_live_source_matches_manifest_v42(
        resolved_root,
        source_manifest,
        require_fixed_root=require_fixed_root,
        pinned_root_descriptor=pinned_root_descriptor,
    )
    tree_after = _snapshot_transport_tree_metadata_v42r1(resolved_root)
    if tree_after != tree_before:
        _fail("remote materialized source tree changed across transport/source closure")


def verify_runtime_repository_modules_in_manifest_v42(
    root: Path, manifest: dict[str, Any], *, require_fixed_root: bool = True
) -> tuple[str, ...]:
    manifest = verify_source_manifest_v42r1(manifest)
    root = _require_exact_remote_source_root(root) if require_fixed_root else root.resolve()
    allowed = {fact["relative_path"] for fact in manifest["source_facts"]}
    observed: set[str] = set()
    for module in tuple(sys.modules.values()):
        raw_file = getattr(module, "__file__", None)
        if type(raw_file) is not str:
            continue
        try:
            path = Path(raw_file).resolve(strict=True)
            relative = path.relative_to(root).as_posix()
        except (FileNotFoundError, OSError, ValueError):
            continue
        if relative.endswith((".pyc", ".pyo")):
            _fail(f"remote runtime loaded repository bytecode: {relative}")
        if relative in RUNTIME_FORBIDDEN_SOURCE_PATHS:
            _fail(f"remote runtime loaded a forbidden predecessor source: {relative}")
        if relative not in allowed:
            _fail(f"remote runtime loaded an unmanifested repository module: {relative}")
        observed.add(relative)
    return tuple(sorted(observed))


class _RemoteManifestImportGuardV42r1:
    def __init__(self, root: Path, allowed: frozenset[str]) -> None:
        self._root = root
        self._allowed = allowed

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> None:
        del path, target
        if fullname == "acfqp" or fullname.startswith("acfqp."):
            base = self._root / "src" / Path(*fullname.split("."))
        elif fullname == "scripts" or fullname.startswith("scripts."):
            base = self._root / Path(*fullname.split("."))
        else:
            return None
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            try:
                relative = candidate.relative_to(self._root).as_posix()
                observed = candidate.lstat()
            except FileNotFoundError:
                continue
            if relative in RUNTIME_FORBIDDEN_SOURCE_PATHS:
                _fail("remote import guard rejected a forbidden predecessor module: " + relative)
            if not stat.S_ISREG(observed.st_mode) or relative not in self._allowed:
                _fail("remote import guard rejected an unmanifested module: " + relative)
        return None


def install_runtime_repository_import_guard_v42(
    root: Path, manifest: dict[str, Any], *, require_fixed_root: bool = True
) -> object:
    manifest = verify_source_manifest_v42r1(manifest)
    resolved_root = (
        _require_exact_remote_source_root(root) if require_fixed_root else root.resolve()
    )
    guard = _RemoteManifestImportGuardV42r1(
        resolved_root,
        frozenset(fact["relative_path"] for fact in manifest["source_facts"]),
    )
    sys.meta_path.insert(0, guard)
    return guard


def build_remote_prepare_receipt_v42r1(
    *,
    source_manifest: dict[str, Any],
    transport_manifest: dict[str, Any],
    predecessor_retention_binding: dict[str, Any],
    prepare_host_attestation: dict[str, Any],
    fresh_terminal_preregistration_id: str,
    history_freshness_manifest_id: str,
    remote_bootstrap_sha256: str,
    remote_bootstrap_runtime_binding: dict[str, Any],
) -> dict[str, Any]:
    source_manifest = verify_source_manifest_v42r1(source_manifest)
    transport_manifest = verify_transport_manifest_v42r1(
        transport_manifest, source_manifest=source_manifest
    )
    predecessor_retention_binding = verify_predecessor_retention_binding_v42r1(
        predecessor_retention_binding
    )
    prepare_host_attestation = verify_host_attestation_v42r1(
        prepare_host_attestation, expected_stage="PREPARE", require_pass=True
    )
    bootstrap_facts = [
        fact
        for fact in source_manifest["source_facts"]
        if fact["relative_path"]
        == "scripts/bootstrap_v42_standard_2048_remote_ordinal2.py"
    ]
    if (
        type(remote_bootstrap_sha256) is not str
        or _HEX64.fullmatch(remote_bootstrap_sha256) is None
        or len(bootstrap_facts) != 1
        or remote_bootstrap_sha256 != bootstrap_facts[0]["sha256"]
    ):
        _fail("remote prepare bootstrap hash differs from its source-manifest fact")
    local_materialization_attempt = build_local_materialization_attempt_v42r1(
        source_manifest=source_manifest, transport_manifest=transport_manifest
    )
    remote_bootstrap_runtime_binding = verify_remote_bootstrap_runtime_binding_v42r1(
        remote_bootstrap_runtime_binding,
        transport_manifest=transport_manifest,
        source_manifest=source_manifest,
        local_materialization_attempt=local_materialization_attempt,
    )
    remote_materialization_attempt = build_remote_materialization_attempt_v42r1(
        local_materialization_attempt=local_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
        remote_bootstrap_runtime_binding=remote_bootstrap_runtime_binding,
    )
    materialization_terminal = build_materialization_terminal_v42r1(
        local_materialization_attempt=local_materialization_attempt,
        remote_materialization_attempt=remote_materialization_attempt,
        source_manifest=source_manifest,
        transport_manifest=transport_manifest,
    )
    payload = {
        "schema": PREPARE_RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "predecessor_formal_identity": PREDECESSOR_FORMAL_IDENTITY,
        "predecessor_source_commit": PREDECESSOR_SOURCE_COMMIT,
        "predecessor_source_tree": PREDECESSOR_SOURCE_TREE,
        "fresh_terminal_preregistration_id": fresh_terminal_preregistration_id,
        "history_freshness_manifest_id": history_freshness_manifest_id,
        "source_commit": source_manifest["source_commit"],
        "source_tree": source_manifest["source_tree"],
        "source_manifest": source_manifest,
        "source_manifest_id": source_manifest["source_manifest_id"],
        "transport_manifest": transport_manifest,
        "transport_manifest_id": transport_manifest["transport_manifest_id"],
        "source_archive_sha256": transport_manifest["source_archive_sha256"],
        "source_archive_byte_count": transport_manifest["source_archive_byte_count"],
        "local_materialization_attempt_id": local_materialization_attempt[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": remote_materialization_attempt[
            "remote_materialization_attempt_id"
        ],
        "materialization_terminal_id": materialization_terminal[
            "materialization_terminal_id"
        ],
        "remote_bootstrap_pyz_artifact_id": remote_materialization_attempt[
            "remote_bootstrap_pyz_artifact_id"
        ],
        "remote_bootstrap_pyz_member_manifest_id": remote_materialization_attempt[
            "remote_bootstrap_pyz_member_manifest_id"
        ],
        "remote_bootstrap_pyz_sha256": remote_materialization_attempt[
            "remote_bootstrap_pyz_sha256"
        ],
        "remote_bootstrap_pyz_byte_count": remote_materialization_attempt[
            "remote_bootstrap_pyz_byte_count"
        ],
        "remote_bootstrap_runtime_binding": remote_bootstrap_runtime_binding,
        "remote_bootstrap_runtime_binding_id": remote_bootstrap_runtime_binding[
            "remote_bootstrap_runtime_binding_id"
        ],
        "remote_bootstrap_sha256": remote_bootstrap_sha256,
        "prepare_host_attestation": prepare_host_attestation,
        "prepare_host_attestation_id": prepare_host_attestation["host_attestation_id"],
        "predecessor_retention_binding": predecessor_retention_binding,
        "predecessor_binding_id": predecessor_retention_binding[
            "predecessor_binding_id"
        ],
        "remote_host_alias": REMOTE_HOST_ALIAS,
        "remote_hostname": REMOTE_HOSTNAME,
        "remote_user": REMOTE_USER,
        "remote_python": REMOTE_PYTHON,
        "remote_python_realpath": REMOTE_PYTHON_REALPATH,
        "remote_python_version": list(REMOTE_PYTHON_VERSION),
        "remote_root": str(REMOTE_ROOT),
        "remote_source_root": str(REMOTE_SOURCE_ROOT),
        "authority_root_relative": AUTHORITY_ROOT_RELATIVE,
        "evidence_root_relative": EVIDENCE_ROOT_RELATIVE,
        "launch_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "outcome_or_tape_materialized": False,
        "formal_execution_performed": False,
        "same_identity_prepare_retry_forbidden": True,
        "predecessor_ordinal_rerun_forbidden": True,
    }
    return {
        **payload,
        "prepare_receipt_id": _content_id("acfqp:v42-remote-ordinal2:prepare-receipt", payload),
    }


def verify_prepare_receipt_v42(
    raw_or_document: bytes | dict[str, Any],
    *,
    fresh_terminal_preregistration_id: str,
    history_freshness_manifest_id: str,
    root: Path | None = None,
    require_live_source: bool = False,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 prepare receipt")
    source_manifest = verify_source_manifest_v42r1(document.get("source_manifest"))
    expected = build_remote_prepare_receipt_v42r1(
        source_manifest=source_manifest,
        transport_manifest=document.get("transport_manifest"),
        predecessor_retention_binding=document.get("predecessor_retention_binding"),
        prepare_host_attestation=document.get("prepare_host_attestation"),
        fresh_terminal_preregistration_id=fresh_terminal_preregistration_id,
        history_freshness_manifest_id=history_freshness_manifest_id,
        remote_bootstrap_sha256=document.get("remote_bootstrap_sha256"),
        remote_bootstrap_runtime_binding=document.get(
            "remote_bootstrap_runtime_binding"
        ),
    )
    if document != expected:
        _fail("remote ordinal-2 prepare receipt identity changed")
    if require_live_source:
        if root is None:
            _fail("remote live receipt verification requires a source root")
        live_binding = verify_predecessor_retention_ready_v42r1(root)
        if live_binding != document["predecessor_retention_binding"]:
            _fail("remote ordinal-2 live predecessor binding changed")
        verify_fixed_materialization_success_v42r1(
            root,
            document["transport_manifest"],
            source_manifest,
        )
    return document


def build_prepare_receipt_v42(*args: Any, **kwargs: Any) -> dict[str, Any]:
    del args, kwargs
    _fail("remote ordinal-2 receipt must be transported from local prepare")


def build_runner_attempt_v42(
    prepare_receipt: dict[str, Any], *, registered_episode_count: int,
    decision_cap_per_episode: int, launch_host_attestation: dict[str, Any],
    local_launch_attempt_id: str,
) -> dict[str, Any]:
    if type(local_launch_attempt_id) is not str or _HEX64.fullmatch(local_launch_attempt_id) is None:
        _fail("remote ordinal-2 local launch attempt ID changed")
    launch_host_attestation = verify_host_attestation_v42r1(
        launch_host_attestation, expected_stage="LAUNCH", require_pass=True
    )
    payload = {
        "schema": RUNNER_ATTEMPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "predecessor_formal_identity": PREDECESSOR_FORMAL_IDENTITY,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "fresh_terminal_preregistration_id": prepare_receipt["fresh_terminal_preregistration_id"],
        "history_freshness_manifest_id": prepare_receipt["history_freshness_manifest_id"],
        "source_commit": prepare_receipt["source_commit"],
        "source_tree": prepare_receipt["source_tree"],
        "source_manifest_id": prepare_receipt["source_manifest_id"],
        "transport_manifest_id": prepare_receipt["transport_manifest_id"],
        "local_materialization_attempt_id": prepare_receipt[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": prepare_receipt[
            "remote_materialization_attempt_id"
        ],
        "materialization_terminal_id": prepare_receipt[
            "materialization_terminal_id"
        ],
        "predecessor_binding_id": prepare_receipt["predecessor_binding_id"],
        "prepare_host_attestation_id": prepare_receipt[
            "prepare_host_attestation_id"
        ],
        "launch_host_attestation": launch_host_attestation,
        "launch_host_attestation_id": launch_host_attestation[
            "host_attestation_id"
        ],
        "local_launch_attempt_id": local_launch_attempt_id,
        "attempt_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "registered_episode_count": registered_episode_count,
        "decision_index_starts_at": 0,
        "decision_cap_per_episode": decision_cap_per_episode,
        "remote_host_alias": REMOTE_HOST_ALIAS,
        "remote_hostname": REMOTE_HOSTNAME,
        "remote_user": REMOTE_USER,
        "remote_uid": REMOTE_UID,
        "fixed_evidence_root_relative": EVIDENCE_ROOT_RELATIVE,
        "same_identity_rerun_forbidden": True,
        "predecessor_ordinal_rerun_forbidden": True,
        "outcome_fields_present": False,
    }
    return {
        **payload,
        "runner_attempt_id": _content_id("acfqp:v42-remote-ordinal2:runner-attempt", payload),
    }


def verify_runner_attempt_v42(
    raw_or_document: bytes | dict[str, Any],
    *,
    prepare_receipt: dict[str, Any],
    registered_episode_count: int,
    decision_cap_per_episode: int,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 runner attempt")
    expected = build_runner_attempt_v42(
        prepare_receipt,
        registered_episode_count=registered_episode_count,
        decision_cap_per_episode=decision_cap_per_episode,
        launch_host_attestation=document.get("launch_host_attestation"),
        local_launch_attempt_id=document.get("local_launch_attempt_id"),
    )
    if document != expected:
        _fail("remote ordinal-2 runner attempt changed")
    return document


def build_worker_start_v42(
    *, prepare_receipt: dict[str, Any], runner_attempt: dict[str, Any], worker_authorization_secret_sha256: str
) -> dict[str, Any]:
    if type(worker_authorization_secret_sha256) is not str or _HEX64.fullmatch(worker_authorization_secret_sha256) is None:
        _fail("remote ordinal-2 worker secret hash changed")
    payload = {
        "schema": WORKER_START_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "runner_attempt_id": runner_attempt["runner_attempt_id"],
        "source_commit": prepare_receipt["source_commit"],
        "source_tree": prepare_receipt["source_tree"],
        "source_manifest_id": prepare_receipt["source_manifest_id"],
        "worker_start_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "worker_authorization_secret_sha256": worker_authorization_secret_sha256,
        "remote_host_alias": REMOTE_HOST_ALIAS,
        "remote_hostname": REMOTE_HOSTNAME,
        "producer_process_isolated": True,
        "verifier_process_isolated": True,
        "isolated_python_flags": ["-I", "-S", "-B"],
        "same_identity_worker_restart_forbidden": True,
        "predecessor_ordinal_rerun_forbidden": True,
        "outcome_fields_present": False,
    }
    return {
        **payload,
        "worker_start_id": _content_id("acfqp:v42-remote-ordinal2:worker-start", payload),
    }


def verify_worker_start_v42(
    raw_or_document: bytes | dict[str, Any],
    *, prepare_receipt: dict[str, Any], runner_attempt: dict[str, Any], worker_authorization_secret_sha256: str
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 worker start")
    expected = build_worker_start_v42(
        prepare_receipt=prepare_receipt,
        runner_attempt=runner_attempt,
        worker_authorization_secret_sha256=worker_authorization_secret_sha256,
    )
    if document != expected:
        _fail("remote ordinal-2 worker start changed")
    return document


def build_authority_consumption_v42(
    *, prepare_receipt: dict[str, Any], runner_attempt: dict[str, Any], worker_start: dict[str, Any]
) -> dict[str, Any]:
    payload = {
        "schema": AUTHORITY_CONSUMPTION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "runner_attempt_id": runner_attempt["runner_attempt_id"],
        "worker_start_id": worker_start["worker_start_id"],
        "worker_authorization_secret_sha256": worker_start["worker_authorization_secret_sha256"],
        "consumption_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "consumed_by_role": "ISOLATED_REMOTE_FRESH_PRODUCER_PROCESS",
        "remote_hostname": REMOTE_HOSTNAME,
        "same_identity_authority_reissue_forbidden": True,
        "predecessor_ordinal_rerun_forbidden": True,
        "outcome_fields_present": False,
    }
    return {
        **payload,
        "authority_consumption_id": _content_id(
            "acfqp:v42-remote-ordinal2:authority-consumption", payload
        ),
    }


def verify_authority_consumption_v42(
    raw_or_document: bytes | dict[str, Any],
    *, prepare_receipt: dict[str, Any], runner_attempt: dict[str, Any], worker_start: dict[str, Any]
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 authority consumption")
    expected = build_authority_consumption_v42(
        prepare_receipt=prepare_receipt,
        runner_attempt=runner_attempt,
        worker_start=worker_start,
    )
    if document != expected:
        _fail("remote ordinal-2 authority consumption changed")
    return document


def _write_once(path: Path, raw: bytes) -> None:
    previous_umask = os.umask(0o077)
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o400,
        )
    finally:
        os.umask(previous_umask)
    try:
        os.fchmod(descriptor, 0o400)
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("remote ordinal-2 authority short write")
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    retained, observed = _read_regular_nofollow_stable(path)
    if retained != raw or stat.S_IMODE(observed.st_mode) != 0o400:
        _fail("remote ordinal-2 authority durable readback changed")
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def consume_supervisor_worker_authorization_v42(
    root: Path,
    *,
    worker_authorization_secret: bytes,
    fresh_terminal_preregistration_id: str,
    history_freshness_manifest_id: str,
    registered_episode_count: int,
    decision_cap_per_episode: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if type(worker_authorization_secret) is not bytes or len(worker_authorization_secret) != 32:
        _fail("remote ordinal-2 producer authorization is not 256 bits")
    authority_root = fixed_authority_root_v42(root)
    evidence_root = fixed_evidence_root_v42(root)
    receipt_raw, _ = _read_regular_nofollow_stable(authority_root / PREPARE_RECEIPT_NAME)
    attempt_raw, _ = _read_regular_nofollow_stable(evidence_root / ATTEMPT_NAME)
    worker_raw, _ = _read_regular_nofollow_stable(evidence_root / WORKER_START_NAME)
    receipt = verify_prepare_receipt_v42(
        receipt_raw,
        fresh_terminal_preregistration_id=fresh_terminal_preregistration_id,
        history_freshness_manifest_id=history_freshness_manifest_id,
        root=root,
        require_live_source=True,
    )
    attempt = verify_runner_attempt_v42(
        attempt_raw,
        prepare_receipt=receipt,
        registered_episode_count=registered_episode_count,
        decision_cap_per_episode=decision_cap_per_episode,
    )
    worker_start = verify_worker_start_v42(
        worker_raw,
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_authorization_secret_sha256=hashlib.sha256(worker_authorization_secret).hexdigest(),
    )
    consumption = build_authority_consumption_v42(
        prepare_receipt=receipt, runner_attempt=attempt, worker_start=worker_start
    )
    _write_once(evidence_root / AUTHORITY_CONSUMPTION_NAME, canonical_json_bytes(consumption))
    return receipt, attempt, worker_start, consumption


def verify_consumed_formal_authority_v42(
    root: Path,
    *,
    prepare_receipt: dict[str, Any],
    runner_attempt: dict[str, Any],
    worker_start: dict[str, Any],
    authority_consumption: dict[str, Any],
    fresh_terminal_preregistration_id: str,
    history_freshness_manifest_id: str,
    registered_episode_count: int,
    decision_cap_per_episode: int,
) -> None:
    root = root.resolve()
    expected = (
        (fixed_authority_root_v42(root) / PREPARE_RECEIPT_NAME, prepare_receipt),
        (fixed_evidence_root_v42(root) / ATTEMPT_NAME, runner_attempt),
        (fixed_evidence_root_v42(root) / WORKER_START_NAME, worker_start),
        (fixed_evidence_root_v42(root) / AUTHORITY_CONSUMPTION_NAME, authority_consumption),
    )
    for path, document in expected:
        raw, _ = _read_regular_nofollow_stable(path)
        if raw != canonical_json_bytes(document):
            _fail(f"remote ordinal-2 fixed authority bytes changed: {path.name}")
    receipt = verify_prepare_receipt_v42(
        prepare_receipt,
        fresh_terminal_preregistration_id=fresh_terminal_preregistration_id,
        history_freshness_manifest_id=history_freshness_manifest_id,
        root=root,
        require_live_source=True,
    )
    attempt = verify_runner_attempt_v42(
        runner_attempt,
        prepare_receipt=receipt,
        registered_episode_count=registered_episode_count,
        decision_cap_per_episode=decision_cap_per_episode,
    )
    worker = verify_worker_start_v42(
        worker_start,
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_authorization_secret_sha256=worker_start["worker_authorization_secret_sha256"],
    )
    verify_authority_consumption_v42(
        authority_consumption,
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_start=worker,
    )


def build_campaign_source_binding_v42(
    *,
    prepare_receipt: dict[str, Any],
    runner_attempt: dict[str, Any],
    worker_start: dict[str, Any],
    authority_consumption: dict[str, Any],
    fresh_terminal_preregistration_id: str,
    target_kernel_id: str,
    adaptive_expression_overlay_id: str,
    adaptive_expression_proof_id: str,
    adaptive_expression_model_id: str,
    planner_id: str,
) -> dict[str, Any]:
    payload = {
        "schema": SOURCE_BINDING_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
        "predecessor_formal_identity": PREDECESSOR_FORMAL_IDENTITY,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "runner_attempt_id": runner_attempt["runner_attempt_id"],
        "worker_start_id": worker_start["worker_start_id"],
        "authority_consumption_id": authority_consumption["authority_consumption_id"],
        "source_commit": prepare_receipt["source_commit"],
        "source_tree": prepare_receipt["source_tree"],
        "source_manifest_id": prepare_receipt["source_manifest_id"],
        "transport_manifest_id": prepare_receipt["transport_manifest_id"],
        "predecessor_binding_id": prepare_receipt["predecessor_binding_id"],
        "prepare_host_attestation_id": prepare_receipt[
            "prepare_host_attestation_id"
        ],
        "launch_host_attestation_id": runner_attempt[
            "launch_host_attestation_id"
        ],
        "local_launch_attempt_id": runner_attempt["local_launch_attempt_id"],
        "fresh_terminal_preregistration_id": fresh_terminal_preregistration_id,
        "target_kernel_id": target_kernel_id,
        "adaptive_expression_overlay_id": adaptive_expression_overlay_id,
        "adaptive_expression_proof_id": adaptive_expression_proof_id,
        "adaptive_expression_model_id": adaptive_expression_model_id,
        "planner_id": planner_id,
        "remote_host_alias": REMOTE_HOST_ALIAS,
        "remote_hostname": REMOTE_HOSTNAME,
        "remote_user": REMOTE_USER,
        "remote_uid": REMOTE_UID,
        "remote_python_realpath": REMOTE_PYTHON_REALPATH,
        "binding_frozen_before_first_registered_target_transition": True,
        "predecessor_ordinal_rerun_forbidden": True,
    }
    return {
        **payload,
        "source_binding_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_SOURCE_BINDING_V42_DOMAIN, payload
        ),
    }


def verify_campaign_source_binding_v42(
    raw_or_document: bytes | dict[str, Any], *, expected: dict[str, Any]
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "remote ordinal-2 source binding")
    if document != expected:
        _fail("remote ordinal-2 campaign source binding changed")
    return document


def fixed_authority_root_v42(root: Path) -> Path:
    return root.resolve() / AUTHORITY_ROOT_RELATIVE


def fixed_evidence_root_v42(root: Path) -> Path:
    return root.resolve() / EVIDENCE_ROOT_RELATIVE


def classify_artifact_bytes_v42(path: Path, expected: bytes | None) -> str:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return "ABSENT"
    if not stat.S_ISREG(observed.st_mode):
        return "NONREGULAR"
    raw = path.read_bytes()
    if expected is None:
        return "PRESENT_UNCHECKED"
    if raw == expected:
        return "EXACT"
    if expected.startswith(raw):
        return "STRICT_PREFIX"
    return "DIVERGENT"


__all__ = (
    "ATTEMPT_NAME",
    "AUTHORITY_CONSUMPTION_NAME",
    "AUTHORITY_ROOT_RELATIVE",
    "CAMPAIGN_NAME",
    "EVIDENCE_ROOT_RELATIVE",
    "FAILURE_NAME",
    "FORMAL_REMOTE_SOURCE_ROOTS",
    "FORMAL_IDENTITY",
    "GLOBAL_EXECUTION_ORDINAL",
    "LAUNCH_ATTEMPT_JOURNAL_NAME",
    "LAUNCH_FAILURE_JOURNAL_NAME",
    "LAUNCH_HOST_ATTESTATION_NAME",
    "LOCAL_LAUNCH_ATTEMPT_NAME",
    "LOCAL_LAUNCH_ATTEMPT_SCHEMA",
    "LOCAL_MATERIALIZATION_ATTEMPT_NAME",
    "MATERIALIZATION_FAILURE_NAME",
    "MATERIALIZATION_TERMINAL_NAME",
    "MATERIALIZED_SOURCE_FILE_MODE",
    "MINIMUM_FILESYSTEM_AVAILABLE_BYTES",
    "MINIMUM_MEMORY_AVAILABLE_BYTES",
    "MINIMUM_MEMORY_TOTAL_BYTES",
    "MINIMUM_SWAP_FREE_BYTES",
    "PREDECESSOR_FORMAL_IDENTITY",
    "PREDECESSOR_INDEPENDENT_VERIFICATION_ID",
    "PREDECESSOR_RETENTION_MANIFEST_ID",
    "PREDECESSOR_RETENTION_READY",
    "PREDECESSOR_RUNNER_FAILURE_ID",
    "PREDECESSOR_SOURCE_COMMIT",
    "PREPARE_ATTEMPT_JOURNAL_NAME",
    "PREPARE_FAILURE_JOURNAL_NAME",
    "PREPARE_HOST_ATTESTATION_NAME",
    "PREPARE_RECEIPT_NAME",
    "REMOTE_HOST_ALIAS",
    "REMOTE_HOSTNAME",
    "REMOTE_PYTHON",
    "REMOTE_PYTHON_REALPATH",
    "REMOTE_PYTHON_VERSION",
    "REMOTE_ROOT",
    "REMOTE_MATERIALIZATION_ATTEMPT_NAME",
    "REMOTE_SOURCE_ROOT",
    "REMOTE_UID",
    "REMOTE_USER",
    "RUNTIME_FORBIDDEN_SOURCE_PATHS",
    "SCHEMA_VERSION",
    "SOURCE_CAPSULE_NAME",
    "SOURCE_MANIFEST_NAME",
    "SUPERVISOR_STDERR_NAME",
    "SUPERVISOR_STDOUT_NAME",
    "TERMINAL_NAME",
    "TRANSPORT_MANIFEST_NAME",
    "VERIFICATION_NAME",
    "WORKER_START_NAME",
    "build_authority_consumption_v42",
    "build_campaign_source_binding_v42",
    "build_host_attestation_v42r1",
    "build_local_launch_attempt_v42r1",
    "build_local_materialization_attempt_v42r1",
    "build_materialization_failure_v42r1",
    "build_materialization_terminal_v42r1",
    "build_predecessor_retention_binding_v42r1",
    "build_remote_prepare_receipt_v42r1",
    "build_remote_materialization_attempt_v42r1",
    "build_runner_attempt_v42",
    "build_source_manifest_v42r1",
    "build_transport_manifest_v42r1",
    "build_worker_start_v42",
    "classify_artifact_bytes_v42",
    "consume_supervisor_worker_authorization_v42",
    "fixed_authority_root_v42",
    "fixed_evidence_root_v42",
    "install_runtime_repository_import_guard_v42",
    "materialization_staging_name_v42r1",
    "observe_host_attestation_v42r1",
    "verify_authority_consumption_v42",
    "verify_campaign_source_binding_v42",
    "verify_consumed_formal_authority_v42",
    "verify_live_source_matches_manifest_v42",
    "verify_live_materialized_source_closure_v42r1",
    "verify_live_transport_inventory_v42r1",
    "verify_fixed_materialization_success_v42r1",
    "verify_fixed_transport_controls_v42r1",
    "verify_host_attestation_v42r1",
    "verify_predecessor_retention_ready_v42r1",
    "verify_local_materialization_attempt_v42r1",
    "verify_local_launch_attempt_v42r1",
    "verify_materialization_failure_v42r1",
    "verify_materialization_terminal_v42r1",
    "verify_prepare_receipt_v42",
    "verify_runner_attempt_v42",
    "verify_remote_materialization_attempt_v42r1",
    "verify_remote_control_phase_inventory_v42r1",
    "verify_runtime_repository_modules_in_manifest_v42",
    "verify_source_manifest_v42r1",
    "verify_transport_manifest_v42r1",
    "verify_worker_start_v42",
)
