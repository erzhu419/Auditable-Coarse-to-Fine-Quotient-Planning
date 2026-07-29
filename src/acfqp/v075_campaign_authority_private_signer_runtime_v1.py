"""Fail-closed campaign-authority signer for V0-075 preregistration.

The tracked repository contains only public verification logic and this
loader.  The campaign-authority RSA factors and private exponent live in one
canonical JSON file named ``campaign-authority-key.v1.json`` under a
caller-selected owner-only ``.acfqp-private`` directory.  When that directory
is inside the supplied Git work tree, Git must attest that the file is both
ignored and untracked.

The loaded object deliberately exposes only the two operations required by
the V2 final-preregistration signing protocol.  It has no serializer, private
key or path accessor, and it self-verifies every emitted signature.
"""

from __future__ import annotations

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
PROFILE_KEY = "v075_campaign_authority_private_signer_runtime_v1"
PRIVATE_DIRECTORY_NAME = ".acfqp-private"
PRIVATE_KEY_FILE_NAME = "campaign-authority-key.v1.json"
PRIVATE_KEY_FILE_SCHEMA = (
    "acfqp.v075_campaign_authority_rsa_private_signing_key.v1"
)
ALGORITHM = "RSASSA-PKCS1-v1_5-SHA256"
KEY_PURPOSE = "V075_FINAL_PREREGISTRATION_V2_SIGNING_ONLY"
FINAL_SIGNING_DOMAIN = b"acfqp:v075-final-preregistration-signing:v2"
FINAL_PAYLOAD_SCHEMA = "acfqp.v075_final_preregistration.v2"
FINAL_PAYLOAD_SCHEMA_VERSION = "2.0.0"
FINAL_PAYLOAD_PROFILE_KEY = "v075_confirmatory_manifest_preregistration_v2"
MAX_PRIVATE_KEY_FILE_BYTES = 64 * 1024
MAX_SIGNING_MESSAGE_BYTES = 16 * 1024 * 1024

PRODUCTION_CAMPAIGN_AUTHORITY_SIGNER_RUNTIME_IMPLEMENTED = True
PRIVATE_KEY_MATERIAL_SERIALIZED = False
PRIVATE_KEY_PATH_EXPORTED = False
TARGET_EXECUTION_OPENED = False
POSIX_SECURE_OPEN_REQUIRED = True

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


class V075CampaignAuthorityPrivateSignerInvariantViolation(ValueError):
    """The private key boundary or a signing invariant failed closed."""


def _fail(message: str) -> None:
    raise V075CampaignAuthorityPrivateSignerInvariantViolation(message)


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
        raise V075CampaignAuthorityPrivateSignerInvariantViolation(
            "campaign private-key Git boundary verification failed"
        ) from error


def _verified_repository_root(repository_root: Path) -> Path:
    root = _require_path(repository_root, "repository root")
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise V075CampaignAuthorityPrivateSignerInvariantViolation(
            "repository root is unavailable"
        ) from error
    result = _run_git(resolved, ("rev-parse", "--show-toplevel"))
    if result.returncode != 0:
        _fail("repository root is not a readable Git work tree")
    try:
        reported = Path(os.fsdecode(result.stdout).strip()).resolve(
            strict=True
        )
    except (OSError, UnicodeError) as error:
        raise V075CampaignAuthorityPrivateSignerInvariantViolation(
            "Git returned an invalid work-tree root"
        ) from error
    if reported != resolved:
        _fail("repository root is not the exact Git work-tree root")
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
        raise V075CampaignAuthorityPrivateSignerInvariantViolation(
            "campaign private key path is unavailable"
        ) from error
    if (
        resolved_private_root != private_root
        or resolved_private_key != private_key_path
    ):
        _fail("campaign private key path may not traverse symbolic links")
    if private_root.name != PRIVATE_DIRECTORY_NAME:
        _fail("campaign private key root must be named .acfqp-private")
    if (
        private_key_path.parent != private_root
        or private_key_path.name != PRIVATE_KEY_FILE_NAME
    ):
        _fail("campaign private key must use its exact registered path")

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
        _fail("campaign private key file is tracked by Git")
    if tracked.returncode != 1:
        _fail("Git could not prove the campaign private key is untracked")
    ignored = _run_git(
        repository_root,
        ("check-ignore", "--quiet", "--", relative),
    )
    if ignored.returncode != 0:
        _fail("in-repository campaign private key is not Git-ignored")


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
        _fail("campaign private keys require POSIX secure-open primitives")
    directory_flags = (
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC

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
                "campaign private key root must be an owner-only "
                "0700 directory"
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
                "campaign private key file must be one owner-only "
                "regular file within the size cap"
            )
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(file_fd, min(remaining, 16 * 1024))
            if not chunk:
                _fail("campaign private key changed during its secure read")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(file_fd, 1):
            _fail("campaign private key grew during its secure read")
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
            _fail("campaign private key changed during its secure read")
        return b"".join(chunks)
    except V075CampaignAuthorityPrivateSignerInvariantViolation:
        raise
    except OSError as error:
        raise V075CampaignAuthorityPrivateSignerInvariantViolation(
            "campaign private key path or permissions failed closed"
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
        _fail("campaign private key bytes are empty or mistyped")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, ValueError) as error:
        raise V075CampaignAuthorityPrivateSignerInvariantViolation(
            "campaign private key file is not canonical JSON"
        ) from error
    if type(document) is not dict or set(document) != _KEY_FIELDS:
        _fail("campaign private key schema or canonical encoding changed")
    try:
        replayed = canonical_json_bytes(document)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075CampaignAuthorityPrivateSignerInvariantViolation(
            "campaign private key schema or canonical encoding changed"
        ) from error
    if replayed != raw:
        _fail("campaign private key schema or canonical encoding changed")
    return document


def _validate_private_key(
    *,
    document: Mapping[str, Any],
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> tuple[public.V075RSAPublicVerificationKeyV1, int]:
    if type(signer_registry) is not public.V075TrustedSignerRegistryV1:
        _fail("campaign signer requires the exact trusted signer registry")
    expected = signer_registry.campaign_authority_key
    if (
        document["schema"] != PRIVATE_KEY_FILE_SCHEMA
        or document["schema_version"] != SCHEMA_VERSION
        or document["algorithm"] != ALGORITHM
        or document["key_purpose"] != KEY_PURPOSE
        or document["key_role"] != "CAMPAIGN_AUTHORITY"
        or document["registered_signer_registry_id"]
        != signer_registry.registry_id
        or document["registered_public_key_id"] != expected.key_id
        or type(document["public_exponent"]) is not int
        or document["public_exponent"] != expected.public_exponent
    ):
        _fail(
            "campaign private key does not match the registered public role"
        )

    expected_modulus_hex = format(expected.modulus, "x")
    modulus_hex = _canonical_hex(
        document["modulus_hex"],
        "campaign private key modulus",
        max_digits=len(expected_modulus_hex),
    )
    if modulus_hex != expected_modulus_hex:
        _fail(
            "campaign private key modulus does not match the public key"
        )
    component_cap = len(expected_modulus_hex)
    first_hex = _canonical_hex(
        document["prime_p_hex"],
        "campaign private key first factor",
        max_digits=component_cap,
    )
    second_hex = _canonical_hex(
        document["prime_q_hex"],
        "campaign private key second factor",
        max_digits=component_cap,
    )
    exponent_hex = _canonical_hex(
        document["private_exponent_hex"],
        "campaign private signing exponent",
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
        _fail("campaign private RSA factors or exponent are invalid")
    lambda_n = math.lcm(first - 1, second - 1)
    if (
        math.gcd(expected.public_exponent, lambda_n) != 1
        or (
            expected.public_exponent * private_exponent
        )
        % lambda_n
        != 1
    ):
        _fail(
            "campaign private exponent is not bound to the public exponent"
        )
    return expected, private_exponent


def _validate_final_signing_message(
    *,
    message: Any,
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> bytes:
    if (
        type(message) is not bytes
        or not message
        or len(message) > MAX_SIGNING_MESSAGE_BYTES
    ):
        _fail(
            "final-preregistration signing message is empty, mistyped, "
            "or over cap"
        )
    prefix = FINAL_SIGNING_DOMAIN + b"\x00"
    if not message.startswith(prefix) or len(message) == len(prefix):
        _fail("campaign signer refuses a non-final-preregistration domain")
    payload_bytes = message[len(prefix) :]
    try:
        payload = loads_canonical_json(payload_bytes)
        replayed = canonical_json_bytes(payload)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075CampaignAuthorityPrivateSignerInvariantViolation(
            "final-preregistration signing payload is not canonical JSON"
        ) from error
    if replayed != payload_bytes or type(payload) is not dict:
        _fail("final-preregistration signing payload is not canonical JSON")
    expected_key = signer_registry.campaign_authority_key
    if (
        payload.get("schema") != FINAL_PAYLOAD_SCHEMA
        or payload.get("schema_version") != FINAL_PAYLOAD_SCHEMA_VERSION
        or payload.get("profile_key") != FINAL_PAYLOAD_PROFILE_KEY
        or payload.get("signer_registry_id") != signer_registry.registry_id
        or payload.get("signer_registry")
        != signer_registry.to_document()
        or payload.get("campaign_authority_key_id")
        != expected_key.key_id
        or payload.get("campaign_authority_public_key_bytes")
        != canonical_json_bytes(expected_key.to_document()).hex()
        or payload.get("observer_open_allowed") is not False
        or payload.get("registered_target_execution_allowed") is not False
        or payload.get("official_execution_allowed") is not False
        or payload.get("target_accessed") is not False
    ):
        _fail(
            "final-preregistration signing payload is not bound to the "
            "registered pre-open campaign authority"
        )
    return message


def _rsa_sign_and_verify(
    *,
    public_key: public.V075RSAPublicVerificationKeyV1,
    private_exponent: int,
    message: bytes,
) -> str:
    width = (public_key.modulus.bit_length() + 7) // 8
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
        private_exponent,
        public_key.modulus,
    )
    signature_hex = signature_integer.to_bytes(width, "big").hex()
    if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=public_key,
        message=message,
        signature_hex=signature_hex,
    ):
        _fail("campaign private signer self-verification failed")
    return signature_hex


class V075ProductionCampaignAuthoritySignerV1:
    """Nonserializable, registry-bound V2 final-preregistration signer."""

    __slots__ = ("_public_key", "_private_exponent", "_signer_registry")

    def __init__(
        self,
        issuer: object,
        public_key: public.V075RSAPublicVerificationKeyV1,
        private_exponent: int,
        signer_registry: public.V075TrustedSignerRegistryV1,
    ) -> None:
        if (
            issuer is not _LOADER_ISSUER
            or type(public_key)
            is not public.V075RSAPublicVerificationKeyV1
            or public_key.key_role != "CAMPAIGN_AUTHORITY"
            or type(private_exponent) is not int
            or not 1 < private_exponent < public_key.modulus
            or type(signer_registry)
            is not public.V075TrustedSignerRegistryV1
            or signer_registry.campaign_authority_key != public_key
        ):
            _fail("campaign private signer may only be built by its loader")
        object.__setattr__(self, "_public_key", public_key)
        object.__setattr__(self, "_private_exponent", private_exponent)
        object.__setattr__(self, "_signer_registry", signer_registry)

    def __repr__(self) -> str:
        return (
            "<V075ProductionCampaignAuthoritySignerV1 "
            f"public_key_id={self._public_key.key_id} "
            "private_material=REDACTED>"
        )

    def __reduce_ex__(self, protocol: int) -> object:
        del protocol
        raise TypeError(
            "V0-075 campaign private signer serialization is forbidden"
        )

    def public_verification_key_v1(
        self,
    ) -> public.V075RSAPublicVerificationKeyV1:
        return self._public_key

    def sign_final_preregistration_v2(self, message: bytes) -> str:
        checked_message = _validate_final_signing_message(
            message=message,
            signer_registry=self._signer_registry,
        )
        return _rsa_sign_and_verify(
            public_key=self._public_key,
            private_exponent=self._private_exponent,
            message=checked_message,
        )


def load_v075_production_campaign_authority_signer_v1(
    *,
    repository_root: Path,
    private_root: Path,
    private_key_path: Path,
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> V075ProductionCampaignAuthoritySignerV1:
    """Load one exact registry-bound campaign signer without exporting it."""

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
    signer = V075ProductionCampaignAuthoritySignerV1(
        _LOADER_ISSUER,
        public_key,
        private_exponent,
        signer_registry,
    )
    challenge = (
        b"acfqp:v075-campaign-private-signer-load-challenge:v1"
        + b"\x00"
        + bytes.fromhex(signer_registry.registry_id)
    )
    _rsa_sign_and_verify(
        public_key=public_key,
        private_exponent=private_exponent,
        message=challenge,
    )
    return signer


__all__ = [
    "ALGORITHM",
    "FINAL_PAYLOAD_PROFILE_KEY",
    "FINAL_PAYLOAD_SCHEMA",
    "FINAL_PAYLOAD_SCHEMA_VERSION",
    "FINAL_SIGNING_DOMAIN",
    "KEY_PURPOSE",
    "MAX_PRIVATE_KEY_FILE_BYTES",
    "MAX_SIGNING_MESSAGE_BYTES",
    "POSIX_SECURE_OPEN_REQUIRED",
    "PRIVATE_DIRECTORY_NAME",
    "PRIVATE_KEY_FILE_NAME",
    "PRIVATE_KEY_FILE_SCHEMA",
    "PRIVATE_KEY_MATERIAL_SERIALIZED",
    "PRIVATE_KEY_PATH_EXPORTED",
    "PRODUCTION_CAMPAIGN_AUTHORITY_SIGNER_RUNTIME_IMPLEMENTED",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "V075CampaignAuthorityPrivateSignerInvariantViolation",
    "V075ProductionCampaignAuthoritySignerV1",
    "load_v075_production_campaign_authority_signer_v1",
]
