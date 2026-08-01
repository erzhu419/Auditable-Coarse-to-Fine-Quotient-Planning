"""Fail-closed private observer-evidence signer for V0-075 production.

The tracked repository contains only this loader and public verification
logic.  RSA factors and the private exponent must live in one canonical JSON
file under a caller-selected ``.acfqp-private`` directory.  If that directory
is inside the supplied Git work tree, Git must attest that the key file is
ignored and untracked.

The signer deliberately has no artifact serializer, path accessor, or key
export API.  Its only public operations are the two methods required by the
private-observer and reveal-attestation signer protocols.
"""

from __future__ import annotations

import configparser
import hashlib
import math
import os
from pathlib import Path
import stat
import subprocess
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
)
from acfqp import v075_public_campaign_authority_v1 as public


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_production_private_signer_runtime_v1"
PRIVATE_DIRECTORY_NAME = ".acfqp-private"
PRIVATE_KEY_FILE_SCHEMA = "acfqp.v075_rsa_private_signing_key.v1"
ALGORITHM = "RSASSA-PKCS1-v1_5-SHA256"
KEY_PURPOSE = "V075_OBSERVER_EVIDENCE_SIGNING_ONLY"
MAX_PRIVATE_KEY_FILE_BYTES = 64 * 1024
MAX_SIGNING_MESSAGE_BYTES = 16 * 1024 * 1024

PRODUCTION_PRIVATE_SIGNER_RUNTIME_IMPLEMENTED = True
PRIVATE_KEY_MATERIAL_SERIALIZED = False
TARGET_EXECUTION_OPENED = False
POSIX_SECURE_OPEN_REQUIRED = True
K7_SUBPROCESS_FREE_SIGNER_LOADER_IMPLEMENTED = True
K7_EXTERNAL_PRIVATE_ROOT_REQUIRED = True
K7_REPOSITORY_MARKER_NAME = ".git"
K7_REPOSITORY_MARKER_PROFILE = (
    "v075_k7_exact_git_directory_repository_marker_v1"
)

_DIGEST_INFO_PREFIX = bytes.fromhex(
    "3031300d060960864801650304020105000420"
)
_KEY_FIELDS = {
    "schema",
    "schema_version",
    "algorithm",
    "key_purpose",
    "key_role",
    "registered_signer_registry_id",
    "registered_public_key_id",
    "modulus_hex",
    "public_exponent",
    "prime_p_hex",
    "prime_q_hex",
    "private_exponent_hex",
}
_LOADER_ISSUER = object()


class V075ProductionPrivateSignerInvariantViolation(ValueError):
    """A private path, key file, public binding, or signature was invalid."""


def _fail(message: str) -> None:
    raise V075ProductionPrivateSignerInvariantViolation(message)


def _require_path(value: Any, label: str) -> Path:
    if not isinstance(value, Path) or not value.is_absolute():
        _fail(f"{label} must be one absolute pathlib.Path")
    if any(part in {".", ".."} for part in value.parts):
        _fail(f"{label} must not contain relative path components")
    return value


def _run_git(
    repository_root: Path,
    arguments: tuple[str, ...],
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ("git", "-C", os.fspath(repository_root), *arguments),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "private-key Git boundary verification failed"
        ) from error


def _verified_repository_root(repository_root: Path) -> Path:
    root = _require_path(repository_root, "repository root")
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "repository root is unavailable"
        ) from error
    result = _run_git(
        resolved,
        ("rev-parse", "--show-toplevel"),
    )
    if result.returncode != 0:
        _fail("repository root is not a readable Git work tree")
    try:
        reported = Path(
            os.fsdecode(result.stdout).strip()
        ).resolve(strict=True)
    except (OSError, UnicodeError) as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "Git returned an invalid work-tree root"
        ) from error
    if reported != resolved:
        _fail("repository root is not the exact Git work-tree root")
    return resolved


def _read_bounded_marker_file(
    *,
    directory_fd: int,
    name: str,
    maximum_bytes: int,
    label: str,
) -> bytes:
    """Read one regular, non-symlink marker relative to an open directory."""

    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    file_fd = -1
    try:
        file_fd = os.open(name, flags, dir_fd=directory_fd)
        before = os.fstat(file_fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > maximum_bytes
        ):
            _fail(f"{label} is not one bounded regular file")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(file_fd, min(remaining, 4096))
            if not chunk:
                _fail(f"{label} changed during verification")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(file_fd, 1):
            _fail(f"{label} grew during verification")
        after = os.fstat(file_fd)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            _fail(f"{label} changed during verification")
        return b"".join(chunks)
    except V075ProductionPrivateSignerInvariantViolation:
        raise
    except OSError as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            f"{label} is unavailable or traverses a symbolic link"
        ) from error
    finally:
        if file_fd >= 0:
            os.close(file_fd)


def _require_marker_directory(
    *,
    directory_fd: int,
    name: str,
    label: str,
) -> None:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    marker_fd = -1
    try:
        marker_fd = os.open(name, flags, dir_fd=directory_fd)
        if not stat.S_ISDIR(os.fstat(marker_fd).st_mode):
            _fail(f"{label} is not a directory")
    except V075ProductionPrivateSignerInvariantViolation:
        raise
    except OSError as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            f"{label} is unavailable or traverses a symbolic link"
        ) from error
    finally:
        if marker_fd >= 0:
            os.close(marker_fd)


def _validate_k7_git_head_marker(raw: bytes) -> None:
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        _fail("K7 repository HEAD marker is not canonical")
    value = raw[:-1]
    if value.startswith(b"ref: refs/heads/"):
        suffix = value[len(b"ref: refs/heads/") :]
        if (
            not suffix
            or suffix.startswith(b"/")
            or suffix.endswith(b"/")
            or b"//" in suffix
            or any(
                character
                not in b"abcdefghijklmnopqrstuvwxyz"
                b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                b"0123456789._/-"
                for character in suffix
            )
        ):
            _fail("K7 repository HEAD reference is invalid")
        return
    if len(value) not in {40, 64} or any(
        character not in b"0123456789abcdef" for character in value
    ):
        _fail("K7 repository HEAD marker is invalid")


def _validate_k7_git_config_marker(raw: bytes) -> None:
    try:
        text = raw.decode("utf-8")
        parser = configparser.RawConfigParser(
            interpolation=None,
            strict=True,
        )
        parser.read_string(text)
        repository_format = parser.get(
            "core",
            "repositoryformatversion",
        )
        bare = parser.getboolean("core", "bare")
    except (
        UnicodeError,
        configparser.Error,
        KeyError,
        ValueError,
    ) as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "K7 repository config marker is invalid"
        ) from error
    if repository_format != "0" or bare:
        _fail("K7 repository config is not a non-bare format-0 checkout")


def _verified_k7_repository_root_without_subprocess_v1(
    repository_root: Path,
) -> Path:
    """Verify the ordinary checkout marker shape using no-follow POSIX I/O.

    This intentionally supports the repository's registered, ordinary
    ``.git``-directory checkout shape.  Gitfiles, linked worktrees and
    symlinked marker components are rejected rather than interpreted.
    """

    if (
        not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_CLOEXEC")
    ):
        _fail("K7 repository verification requires POSIX no-follow I/O")
    root = _require_path(repository_root, "repository root")
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "K7 repository root is unavailable"
        ) from error
    if resolved != root:
        _fail("K7 repository root may not traverse symbolic links")

    directory_flags = (
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    root_fd = -1
    git_fd = -1
    try:
        root_fd = os.open(os.fspath(resolved), directory_flags)
        if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
            _fail("K7 repository root is not a directory")
        git_fd = os.open(
            K7_REPOSITORY_MARKER_NAME,
            directory_flags,
            dir_fd=root_fd,
        )
        if not stat.S_ISDIR(os.fstat(git_fd).st_mode):
            _fail("K7 repository marker is not an exact .git directory")
        head = _read_bounded_marker_file(
            directory_fd=git_fd,
            name="HEAD",
            maximum_bytes=4096,
            label="K7 repository HEAD marker",
        )
        config = _read_bounded_marker_file(
            directory_fd=git_fd,
            name="config",
            maximum_bytes=1024 * 1024,
            label="K7 repository config marker",
        )
        _require_marker_directory(
            directory_fd=git_fd,
            name="objects",
            label="K7 repository objects marker",
        )
        _require_marker_directory(
            directory_fd=git_fd,
            name="refs",
            label="K7 repository refs marker",
        )
        _validate_k7_git_head_marker(head)
        _validate_k7_git_config_marker(config)
    except V075ProductionPrivateSignerInvariantViolation:
        raise
    except OSError as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "K7 repository marker is unavailable or traverses a symbolic link"
        ) from error
    finally:
        if git_fd >= 0:
            os.close(git_fd)
        if root_fd >= 0:
            os.close(root_fd)
    return resolved


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _verify_untracked_private_location(
    *,
    repository_root: Path,
    private_root: Path,
    private_key_path: Path,
) -> None:
    try:
        resolved_private_root = private_root.resolve(strict=True)
        resolved_private_key = private_key_path.resolve(strict=True)
    except OSError as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "private key path is unavailable"
        ) from error
    if (
        resolved_private_root != private_root
        or resolved_private_key != private_key_path
    ):
        _fail("private key path may not traverse symbolic links")
    if private_root.name != PRIVATE_DIRECTORY_NAME:
        _fail("private key root must be named .acfqp-private")
    if private_key_path.parent != private_root:
        _fail("private key must be a direct child of its private root")

    if not _is_relative_to(private_root, repository_root):
        return
    if private_root != repository_root / PRIVATE_DIRECTORY_NAME:
        _fail("in-repository private root is not the registered private path")
    relative = private_key_path.relative_to(repository_root).as_posix()
    tracked = _run_git(
        repository_root,
        ("ls-files", "--error-unmatch", "--", relative),
    )
    if tracked.returncode == 0:
        _fail("private key file is tracked by Git")
    if tracked.returncode not in {1}:
        _fail("Git could not prove that the private key file is untracked")
    ignored = _run_git(
        repository_root,
        ("check-ignore", "--quiet", "--", relative),
    )
    if ignored.returncode != 0:
        _fail("in-repository private key file is not covered by Git ignore")


def _verify_k7_strictly_external_private_location_v1(
    *,
    repository_root: Path,
    private_root: Path,
    private_key_path: Path,
) -> None:
    """Accept only one direct private key outside the repository tree."""

    try:
        resolved_private_root = private_root.resolve(strict=True)
        resolved_private_key = private_key_path.resolve(strict=True)
    except OSError as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "K7 private key path is unavailable"
        ) from error
    if (
        resolved_private_root != private_root
        or resolved_private_key != private_key_path
    ):
        _fail("K7 private key path may not traverse symbolic links")
    if private_root.name != PRIVATE_DIRECTORY_NAME:
        _fail("K7 private key root must be named .acfqp-private")
    if private_key_path.parent != private_root:
        _fail("K7 private key must be a direct child of its private root")
    if _is_relative_to(private_root, repository_root) or _is_relative_to(
        repository_root,
        private_root,
    ):
        _fail("K7 private key root must be strictly outside the repository")


def _secure_read_private_key(
    *,
    private_root: Path,
    private_key_path: Path,
) -> bytes:
    if (
        not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "geteuid")
    ):
        _fail("production private keys require POSIX secure-open primitives")
    directory_flags = os.O_RDONLY
    directory_flags |= os.O_DIRECTORY
    directory_flags |= os.O_NOFOLLOW
    directory_flags |= os.O_CLOEXEC
    file_flags = os.O_RDONLY
    file_flags |= os.O_NOFOLLOW
    file_flags |= os.O_CLOEXEC

    directory_fd = -1
    file_fd = -1
    try:
        directory_fd = os.open(os.fspath(private_root), directory_flags)
        directory_status = os.fstat(directory_fd)
        if (
            not stat.S_ISDIR(directory_status.st_mode)
            or stat.S_IMODE(directory_status.st_mode) != 0o700
            or directory_status.st_uid != os.geteuid()
        ):
            _fail(
                "private key root must be an owner-only 0700 directory"
            )
        file_fd = os.open(
            private_key_path.name,
            file_flags,
            dir_fd=directory_fd,
        )
        before = os.fstat(file_fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) not in {0o400, 0o600}
            or before.st_nlink != 1
            or before.st_uid != os.geteuid()
            or before.st_size <= 0
            or before.st_size > MAX_PRIVATE_KEY_FILE_BYTES
        ):
            _fail(
                "private key file must be one owner-only regular file "
                "within the size cap"
            )
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(file_fd, min(remaining, 16 * 1024))
            if not chunk:
                _fail("private key file changed during its secure read")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(file_fd, 1):
            _fail("private key file grew during its secure read")
        after = os.fstat(file_fd)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            _fail("private key file changed during its secure read")
        return b"".join(chunks)
    except V075ProductionPrivateSignerInvariantViolation:
        raise
    except OSError as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "private key path or permissions failed closed"
        ) from error
    finally:
        if file_fd >= 0:
            os.close(file_fd)
        if directory_fd >= 0:
            os.close(directory_fd)


def _canonical_hex(value: Any, field: str, *, max_digits: int) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > max_digits
        or value != value.lower()
        or (len(value) > 1 and value.startswith("0"))
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field} is not canonical bounded lowercase hexadecimal")
    return value


def _load_key_document(raw: bytes) -> Mapping[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail("private key bytes are empty or mistyped")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, ValueError) as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "private key file is not canonical JSON"
        ) from error
    if type(document) is not dict or set(document) != _KEY_FIELDS:
        _fail("private key file schema or canonical encoding changed")
    try:
        replayed = canonical_json_bytes(document)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075ProductionPrivateSignerInvariantViolation(
            "private key file schema or canonical encoding changed"
        ) from error
    if replayed != raw:
        _fail("private key file schema or canonical encoding changed")
    return document


def _validate_private_key(
    *,
    document: Mapping[str, Any],
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> tuple[public.V075RSAPublicVerificationKeyV1, int]:
    if type(signer_registry) is not public.V075TrustedSignerRegistryV1:
        _fail("private signer requires the exact trusted signer registry")
    expected = signer_registry.observer_evidence_key
    if (
        document["schema"] != PRIVATE_KEY_FILE_SCHEMA
        or document["schema_version"] != SCHEMA_VERSION
        or document["algorithm"] != ALGORITHM
        or document["key_purpose"] != KEY_PURPOSE
        or document["key_role"] != "OBSERVER_EVIDENCE"
        or document["registered_signer_registry_id"]
        != signer_registry.registry_id
        or document["registered_public_key_id"] != expected.key_id
        or type(document["public_exponent"]) is not int
        or document["public_exponent"] != expected.public_exponent
    ):
        _fail("private key file does not match the registered public role")

    expected_modulus_hex = format(expected.modulus, "x")
    modulus_hex = _canonical_hex(
        document["modulus_hex"],
        "private key modulus",
        max_digits=len(expected_modulus_hex),
    )
    if modulus_hex != expected_modulus_hex:
        _fail("private key modulus does not match the registered public key")
    component_cap = len(expected_modulus_hex)
    first_hex = _canonical_hex(
        document["prime_p_hex"],
        "private key first factor",
        max_digits=component_cap,
    )
    second_hex = _canonical_hex(
        document["prime_q_hex"],
        "private key second factor",
        max_digits=component_cap,
    )
    exponent_hex = _canonical_hex(
        document["private_exponent_hex"],
        "private signing exponent",
        max_digits=component_cap,
    )
    first = int(first_hex, 16)
    second = int(second_hex, 16)
    private_exponent = int(exponent_hex, 16)
    if (
        first >= second
        or first <= 2
        or first % 2 == 0
        or second % 2 == 0
        or math.gcd(first, second) != 1
        or first * second != expected.modulus
        or not 1 < private_exponent < expected.modulus
    ):
        _fail("private RSA factors or exponent are invalid")
    lambda_n = math.lcm(first - 1, second - 1)
    if (
        math.gcd(expected.public_exponent, lambda_n) != 1
        or (
            expected.public_exponent * private_exponent
        )
        % lambda_n
        != 1
    ):
        _fail("private RSA exponent is not bound to the public exponent")
    return expected, private_exponent


class V075ProductionObserverEvidenceSignerV1:
    """Nonserializable in-memory implementation of both signer protocols."""

    __slots__ = ("_public_key", "_private_exponent")

    def __init__(
        self,
        issuer: object,
        public_key: public.V075RSAPublicVerificationKeyV1,
        private_exponent: int,
    ) -> None:
        if (
            issuer is not _LOADER_ISSUER
            or type(public_key)
            is not public.V075RSAPublicVerificationKeyV1
            or public_key.key_role != "OBSERVER_EVIDENCE"
            or type(private_exponent) is not int
            or not 1 < private_exponent < public_key.modulus
        ):
            _fail("private signer may only be constructed by its loader")
        object.__setattr__(self, "_public_key", public_key)
        object.__setattr__(self, "_private_exponent", private_exponent)

    def __repr__(self) -> str:
        return (
            "<V075ProductionObserverEvidenceSignerV1 "
            f"public_key_id={self._public_key.key_id} "
            "private_material=REDACTED>"
        )

    def __reduce_ex__(self, protocol: int) -> object:
        del protocol
        raise TypeError("V0-075 private signer serialization is forbidden")

    def public_verification_key_v1(
        self,
    ) -> public.V075RSAPublicVerificationKeyV1:
        return self._public_key

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        if (
            type(message) is not bytes
            or not message
            or len(message) > MAX_SIGNING_MESSAGE_BYTES
        ):
            _fail("observer signing message is empty, mistyped, or over cap")
        width = (self._public_key.modulus.bit_length() + 7) // 8
        digest_info = _DIGEST_INFO_PREFIX + hashlib.sha256(message).digest()
        padding_size = width - len(digest_info) - 3
        if padding_size < 8:
            _fail("registered RSA modulus is too short for SHA-256 signing")
        encoded = (
            b"\x00\x01"
            + b"\xff" * padding_size
            + b"\x00"
            + digest_info
        )
        signature_integer = pow(
            int.from_bytes(encoded, "big"),
            self._private_exponent,
            self._public_key.modulus,
        )
        signature_hex = signature_integer.to_bytes(width, "big").hex()
        if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=self._public_key,
            message=message,
            signature_hex=signature_hex,
        ):
            _fail("private signer self-verification failed")
        return signature_hex


def load_v075_production_observer_evidence_signer_v1(
    *,
    repository_root: Path,
    private_root: Path,
    private_key_path: Path,
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> V075ProductionObserverEvidenceSignerV1:
    """Load one registry-bound observer signer without exporting secrets."""

    repository = _verified_repository_root(repository_root)
    private_directory = _require_path(private_root, "private key root")
    key_path = _require_path(private_key_path, "private key path")
    _verify_untracked_private_location(
        repository_root=repository,
        private_root=private_directory,
        private_key_path=key_path,
    )
    raw = _secure_read_private_key(
        private_root=private_directory,
        private_key_path=key_path,
    )
    document = _load_key_document(raw)
    public_key, private_exponent = _validate_private_key(
        document=document,
        signer_registry=signer_registry,
    )
    signer = V075ProductionObserverEvidenceSignerV1(
        _LOADER_ISSUER,
        public_key,
        private_exponent,
    )
    challenge = (
        b"acfqp:v075-production-private-signer-load-challenge:v1"
        + b"\x00"
        + bytes.fromhex(signer_registry.registry_id)
    )
    signature = signer.sign_observer_evidence_v1(challenge)
    if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=public_key,
        message=challenge,
        signature_hex=signature,
    ):
        _fail("loaded private signer failed its registry-bound challenge")
    return signer


def load_v075_k7_subprocess_free_observer_evidence_signer_v1(
    *,
    repository_root: Path,
    private_root: Path,
    private_key_path: Path,
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> V075ProductionObserverEvidenceSignerV1:
    """Load K7's observer signer without invoking Git or any subprocess.

    This is an additive, deliberately narrower loader.  It accepts only the
    ordinary ``.git``-directory marker shape and requires the
    owner-only private directory to be disjoint from the repository tree.
    The historical Git-aware loader above remains unchanged.
    """

    repository = _verified_k7_repository_root_without_subprocess_v1(
        repository_root
    )
    private_directory = _require_path(private_root, "private key root")
    key_path = _require_path(private_key_path, "private key path")
    _verify_k7_strictly_external_private_location_v1(
        repository_root=repository,
        private_root=private_directory,
        private_key_path=key_path,
    )
    raw = _secure_read_private_key(
        private_root=private_directory,
        private_key_path=key_path,
    )
    document = _load_key_document(raw)
    public_key, private_exponent = _validate_private_key(
        document=document,
        signer_registry=signer_registry,
    )
    signer = V075ProductionObserverEvidenceSignerV1(
        _LOADER_ISSUER,
        public_key,
        private_exponent,
    )
    challenge = (
        b"acfqp:v075-production-private-signer-load-challenge:v1"
        + b"\x00"
        + bytes.fromhex(signer_registry.registry_id)
    )
    signature = signer.sign_observer_evidence_v1(challenge)
    if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=public_key,
        message=challenge,
        signature_hex=signature,
    ):
        _fail("loaded private signer failed its registry-bound challenge")
    return signer


__all__ = [
    "ALGORITHM",
    "KEY_PURPOSE",
    "K7_EXTERNAL_PRIVATE_ROOT_REQUIRED",
    "K7_REPOSITORY_MARKER_NAME",
    "K7_REPOSITORY_MARKER_PROFILE",
    "K7_SUBPROCESS_FREE_SIGNER_LOADER_IMPLEMENTED",
    "MAX_PRIVATE_KEY_FILE_BYTES",
    "MAX_SIGNING_MESSAGE_BYTES",
    "PRIVATE_DIRECTORY_NAME",
    "PRIVATE_KEY_FILE_SCHEMA",
    "PRIVATE_KEY_MATERIAL_SERIALIZED",
    "POSIX_SECURE_OPEN_REQUIRED",
    "PRODUCTION_PRIVATE_SIGNER_RUNTIME_IMPLEMENTED",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "V075ProductionObserverEvidenceSignerV1",
    "V075ProductionPrivateSignerInvariantViolation",
    "load_v075_k7_subprocess_free_observer_evidence_signer_v1",
    "load_v075_production_observer_evidence_signer_v1",
]
