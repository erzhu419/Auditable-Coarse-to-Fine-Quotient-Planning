from __future__ import annotations

from functools import lru_cache
import inspect
import json
import math
import os
from pathlib import Path
import pickle
import shutil
import subprocess
import tempfile

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_campaign_authority_private_signer_runtime_v1 as runtime
from acfqp import v075_public_campaign_authority_v1 as public
from tests import v075_signature_test_support as signatures


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_path() -> Path:
    """Keep permission-sensitive tests on a native POSIX filesystem."""

    if os.name != "posix":
        pytest.skip("campaign private signer requires POSIX secure-open")
    value = Path(
        tempfile.mkdtemp(
            prefix="acfqp-v075-campaign-signer-test-",
            dir="/tmp",
        )
    )
    try:
        yield value
    finally:
        shutil.rmtree(value)


def _registry() -> public.V075TrustedSignerRegistryV1:
    return public.V075TrustedSignerRegistryV1(
        signatures.make_public_key("CAMPAIGN_AUTHORITY"),
        signatures.make_public_key("OBSERVER_EVIDENCE"),
    )


@lru_cache(maxsize=1)
def _private_components() -> tuple[int, int, int]:
    first = signatures._derive_test_prime(  # type: ignore[attr-defined]
        b"acfqp-unit-rsa-62"
    )
    second = signatures._derive_test_prime(  # type: ignore[attr-defined]
        b"acfqp-unit-rsa-68"
    )
    first, second = sorted((first, second))
    exponent = pow(
        65_537,
        -1,
        math.lcm(first - 1, second - 1),
    )
    assert first * second == signatures.RSA_MODULUS
    return first, second, exponent


def _key_document(
    registry: public.V075TrustedSignerRegistryV1,
) -> dict[str, object]:
    first, second, exponent = _private_components()
    key = registry.campaign_authority_key
    return {
        "schema": runtime.PRIVATE_KEY_FILE_SCHEMA,
        "schema_version": runtime.SCHEMA_VERSION,
        "algorithm": runtime.ALGORITHM,
        "key_purpose": runtime.KEY_PURPOSE,
        "key_role": "CAMPAIGN_AUTHORITY",
        "registered_signer_registry_id": registry.registry_id,
        "registered_public_key_id": key.key_id,
        "modulus_hex": format(key.modulus, "x"),
        "public_exponent": key.public_exponent,
        "prime_p_hex": format(first, "x"),
        "prime_q_hex": format(second, "x"),
        "private_exponent_hex": format(exponent, "x"),
    }


def _final_payload(
    registry: public.V075TrustedSignerRegistryV1,
) -> dict[str, object]:
    key = registry.campaign_authority_key
    return {
        "schema": runtime.FINAL_PAYLOAD_SCHEMA,
        "schema_version": runtime.FINAL_PAYLOAD_SCHEMA_VERSION,
        "profile_key": runtime.FINAL_PAYLOAD_PROFILE_KEY,
        "signer_registry_id": registry.registry_id,
        "signer_registry": registry.to_document(),
        "campaign_authority_key_id": key.key_id,
        "campaign_authority_public_key_bytes": canonical_json_bytes(
            key.to_document()
        ).hex(),
        "confirmatory_execution_manifest_id": "0" * 64,
        "observer_open_allowed": False,
        "registered_target_execution_allowed": False,
        "official_execution_allowed": False,
        "target_accessed": False,
    }


def _signing_message(
    registry: public.V075TrustedSignerRegistryV1,
    *,
    payload: dict[str, object] | None = None,
) -> bytes:
    return (
        runtime.FINAL_SIGNING_DOMAIN
        + b"\x00"
        + canonical_json_bytes(
            _final_payload(registry) if payload is None else payload
        )
    )


def _write_private_key(
    tmp_path: Path,
    document: dict[str, object],
    *,
    root_mode: int = 0o700,
    file_mode: int = 0o600,
    raw: bytes | None = None,
    file_name: str = runtime.PRIVATE_KEY_FILE_NAME,
) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    private_root = tmp_path / runtime.PRIVATE_DIRECTORY_NAME
    private_root.mkdir(mode=0o700)
    private_root.chmod(root_mode)
    key_path = private_root / file_name
    key_path.write_bytes(
        canonical_json_bytes(document) if raw is None else raw
    )
    key_path.chmod(file_mode)
    return private_root.resolve(), key_path.resolve()


def _load(
    *,
    registry: public.V075TrustedSignerRegistryV1,
    private_root: Path,
    key_path: Path,
    repository_root: Path = REPOSITORY_ROOT,
) -> runtime.V075ProductionCampaignAuthoritySignerV1:
    return runtime.load_v075_production_campaign_authority_signer_v1(
        repository_root=repository_root,
        private_root=private_root,
        private_key_path=key_path,
        signer_registry=registry,
    )


def test_loaded_signer_has_exact_protocol_and_signs_only_v2_final(
    tmp_path: Path,
) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path,
        _key_document(registry),
    )
    signer = _load(
        registry=registry,
        private_root=private_root,
        key_path=key_path,
    )

    public_methods = {
        name
        for name, value in inspect.getmembers(
            type(signer),
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }
    assert public_methods == {
        "public_verification_key_v1",
        "sign_final_preregistration_v2",
    }
    assert signer.public_verification_key_v1() == (
        registry.campaign_authority_key
    )
    message = _signing_message(registry)
    signature = signer.sign_final_preregistration_v2(message)
    assert public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=registry.campaign_authority_key,
        message=message,
        signature_hex=signature,
    )


def test_signer_is_redacted_nonserializable_and_exports_no_path_or_key(
    tmp_path: Path,
) -> None:
    registry = _registry()
    document = _key_document(registry)
    private_root, key_path = _write_private_key(tmp_path, document)
    signer = _load(
        registry=registry,
        private_root=private_root,
        key_path=key_path,
    )
    public_surface = json.dumps(
        {
            "repr": repr(signer),
            "public_key": signer.public_verification_key_v1().to_document(),
            "signature": signer.sign_final_preregistration_v2(
                _signing_message(registry)
            ),
        },
        sort_keys=True,
    )
    for field in (
        "prime_p_hex",
        "prime_q_hex",
        "private_exponent_hex",
    ):
        assert str(document[field]) not in public_surface
    assert os.fspath(key_path) not in public_surface
    assert "REDACTED" in repr(signer)
    assert not hasattr(signer, "to_document")
    assert not hasattr(signer, "private_key")
    assert not hasattr(signer, "private_key_path")
    assert not hasattr(signer, "__dict__")
    with pytest.raises(TypeError):
        pickle.dumps(signer)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("private_exponent_hex", "3"),
        ("prime_p_hex", "3"),
        ("key_role", "OBSERVER_EVIDENCE"),
        ("key_purpose", "V075_OBSERVER_EVIDENCE_SIGNING_ONLY"),
        ("registered_signer_registry_id", "0" * 64),
        ("registered_public_key_id", "1" * 64),
        ("public_exponent", 3),
    ),
)
def test_private_key_tampering_fails_without_echoing_secrets(
    tmp_path: Path,
    field: str,
    replacement: object,
) -> None:
    registry = _registry()
    document = _key_document(registry)
    secrets = tuple(
        str(document[name])
        for name in (
            "prime_p_hex",
            "prime_q_hex",
            "private_exponent_hex",
        )
    )
    document[field] = replacement
    private_root, key_path = _write_private_key(tmp_path, document)
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ) as caught:
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )
    assert all(secret not in str(caught.value) for secret in secrets)
    assert os.fspath(key_path) not in str(caught.value)


def test_noncanonical_unknown_and_malformed_key_documents_fail(
    tmp_path: Path,
) -> None:
    registry = _registry()
    document = _key_document(registry)
    private_root, key_path = _write_private_key(
        tmp_path / "noncanonical",
        document,
        raw=b" " + canonical_json_bytes(document),
    )
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )

    unknown = dict(document)
    unknown["secret_comment"] = "reject"
    private_root, key_path = _write_private_key(
        tmp_path / "unknown",
        unknown,
    )
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )

    uppercase = dict(document)
    uppercase["prime_p_hex"] = str(uppercase["prime_p_hex"]).upper()
    private_root, key_path = _write_private_key(
        tmp_path / "uppercase",
        uppercase,
    )
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )


def test_registry_and_role_transplants_fail(tmp_path: Path) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path,
        _key_document(registry),
    )
    wrong_campaign = public.V075RSAPublicVerificationKeyV1(
        "CAMPAIGN_AUTHORITY",
        registry.campaign_authority_key.modulus + 2,
    )
    wrong_registry = public.V075TrustedSignerRegistryV1(
        wrong_campaign,
        registry.observer_evidence_key,
    )
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=wrong_registry,
            private_root=private_root,
            key_path=key_path,
        )


@pytest.mark.parametrize(
    ("root_mode", "file_mode"),
    ((0o755, 0o600), (0o700, 0o644)),
)
def test_nonprivate_permissions_fail_closed(
    tmp_path: Path,
    root_mode: int,
    file_mode: int,
) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path,
        _key_document(registry),
        root_mode=root_mode,
        file_mode=file_mode,
    )
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )


def test_symlink_hardlink_nested_wrong_name_and_relative_paths_fail(
    tmp_path: Path,
) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path,
        _key_document(registry),
    )
    symlink = private_root / "campaign-symlink.json"
    symlink.symlink_to(key_path)
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=symlink,
        )
    symlink.unlink()

    hardlink = private_root / "campaign-hardlink.json"
    os.link(key_path, hardlink)
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )
    hardlink.unlink()

    wrong_root, wrong_key = _write_private_key(
        tmp_path / "wrong-name",
        _key_document(registry),
        file_name="observer-evidence-key.v1.json",
    )
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=wrong_root,
            key_path=wrong_key,
        )

    nested_root = (
        tmp_path / "nested-parent" / runtime.PRIVATE_DIRECTORY_NAME
    )
    nested_root.mkdir(parents=True, mode=0o700)
    nested_root.chmod(0o700)
    nested = nested_root / "nested"
    nested.mkdir(mode=0o700)
    nested_key = nested / runtime.PRIVATE_KEY_FILE_NAME
    nested_key.write_bytes(
        canonical_json_bytes(_key_document(registry))
    )
    nested_key.chmod(0o600)
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=nested_root.resolve(),
            key_path=nested_key.resolve(),
        )

    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        runtime.load_v075_production_campaign_authority_signer_v1(
            repository_root=REPOSITORY_ROOT,
            private_root=Path(runtime.PRIVATE_DIRECTORY_NAME),
            private_key_path=(
                Path(runtime.PRIVATE_DIRECTORY_NAME)
                / runtime.PRIVATE_KEY_FILE_NAME
            ),
            signer_registry=registry,
        )


def _git(*arguments: str, cwd: Path) -> None:
    subprocess.run(
        ("git", *arguments),
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        check=True,
    )


def test_in_repository_key_must_be_ignored_and_untracked(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git("init", "--quiet", cwd=repository)
    (repository / ".gitignore").write_text(
        "/.acfqp-private/\n",
        encoding="utf-8",
    )
    registry = _registry()
    private_root, key_path = _write_private_key(
        repository,
        _key_document(registry),
    )
    signer = _load(
        registry=registry,
        private_root=private_root,
        key_path=key_path,
        repository_root=repository.resolve(),
    )
    assert signer.public_verification_key_v1() == (
        registry.campaign_authority_key
    )

    _git(
        "add",
        "--force",
        key_path.relative_to(repository).as_posix(),
        cwd=repository,
    )
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
            repository_root=repository.resolve(),
        )


def test_nonignored_in_repository_key_fails(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git("init", "--quiet", cwd=repository)
    registry = _registry()
    private_root, key_path = _write_private_key(
        repository,
        _key_document(registry),
    )
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
            repository_root=repository.resolve(),
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "domain",
        "noncanonical",
        "schema",
        "registry",
        "public_key_bytes",
        "observer_open",
        "execution_open",
        "target_accessed",
    ),
)
def test_signer_rejects_wrong_domain_or_payload_binding(
    tmp_path: Path,
    mutation: str,
) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path,
        _key_document(registry),
    )
    signer = _load(
        registry=registry,
        private_root=private_root,
        key_path=key_path,
    )
    payload = _final_payload(registry)
    if mutation == "domain":
        message = (
            b"acfqp:v075-observer-evidence:v1"
            + b"\x00"
            + canonical_json_bytes(payload)
        )
    elif mutation == "noncanonical":
        message = runtime.FINAL_SIGNING_DOMAIN + b"\x00 " + (
            canonical_json_bytes(payload)
        )
    else:
        if mutation == "schema":
            payload["schema"] = "acfqp.v075_final_preregistration.v1"
        elif mutation == "registry":
            payload["signer_registry_id"] = "f" * 64
        elif mutation == "public_key_bytes":
            payload["campaign_authority_public_key_bytes"] = "00"
        elif mutation == "observer_open":
            payload["observer_open_allowed"] = True
        elif mutation == "execution_open":
            payload["official_execution_allowed"] = True
        elif mutation == "target_accessed":
            payload["target_accessed"] = True
        message = _signing_message(registry, payload=payload)
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
    ):
        signer.sign_final_preregistration_v2(message)


def test_invalid_message_types_and_self_verify_failure_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path,
        _key_document(registry),
    )
    signer = _load(
        registry=registry,
        private_root=private_root,
        key_path=key_path,
    )
    for invalid in (b"", bytearray(b"not-bytes")):
        with pytest.raises(
            runtime.V075CampaignAuthorityPrivateSignerInvariantViolation
        ):
            signer.sign_final_preregistration_v2(  # type: ignore[arg-type]
                invalid
            )

    monkeypatch.setattr(
        runtime.public,
        "verify_rsa_pkcs1_v1_5_sha256_signature_v1",
        lambda **_kwargs: False,
    )
    with pytest.raises(
        runtime.V075CampaignAuthorityPrivateSignerInvariantViolation,
        match="self-verification failed",
    ):
        signer.sign_final_preregistration_v2(
            _signing_message(registry)
        )


def test_runtime_contains_no_key_generation_artifact_or_target_opening() -> None:
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    assert "generate_private" not in source
    assert "freeze_v075_confirmatory_execution_manifest_v2" not in source
    assert "finalize_v075_preregistration_v2" not in source
    assert "open_production_private_observer_v1" not in source
    assert runtime.TARGET_EXECUTION_OPENED is False
    assert runtime.PRIVATE_KEY_MATERIAL_SERIALIZED is False
    assert runtime.PRIVATE_KEY_PATH_EXPORTED is False
