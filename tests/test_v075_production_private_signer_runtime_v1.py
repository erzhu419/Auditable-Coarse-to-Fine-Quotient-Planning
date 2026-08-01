from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import pickle
import shutil
import subprocess
import tempfile

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_production_private_signer_runtime_v1 as runtime
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_reveal_verifying_attestation_authority_v1 as reveal
from tests import v075_signature_test_support as signatures


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_path() -> Path:
    """Keep permission-sensitive cases on a native POSIX filesystem."""

    if os.name != "posix":
        pytest.skip("production private signer requires POSIX secure-open")
    value = Path(
        tempfile.mkdtemp(
            prefix="acfqp-v075-private-signer-test-",
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
        b"acfqp-unit-rsa-95"
    )
    second = signatures._derive_test_prime(  # type: ignore[attr-defined]
        b"acfqp-unit-rsa-97"
    )
    first, second = sorted((first, second))
    exponent = pow(
        65_537,
        -1,
        (first - 1) * (second - 1),
    )
    assert first * second == signatures.OBSERVER_RSA_MODULUS
    return first, second, exponent


def _key_document(
    registry: public.V075TrustedSignerRegistryV1,
) -> dict[str, object]:
    first, second, exponent = _private_components()
    key = registry.observer_evidence_key
    return {
        "schema": runtime.PRIVATE_KEY_FILE_SCHEMA,
        "schema_version": runtime.SCHEMA_VERSION,
        "algorithm": runtime.ALGORITHM,
        "key_purpose": runtime.KEY_PURPOSE,
        "key_role": "OBSERVER_EVIDENCE",
        "registered_signer_registry_id": registry.registry_id,
        "registered_public_key_id": key.key_id,
        "modulus_hex": format(key.modulus, "x"),
        "public_exponent": key.public_exponent,
        "prime_p_hex": format(first, "x"),
        "prime_q_hex": format(second, "x"),
        "private_exponent_hex": format(exponent, "x"),
    }


def _write_private_key(
    tmp_path: Path,
    document: dict[str, object],
    *,
    root_mode: int = 0o700,
    file_mode: int = 0o600,
    raw: bytes | None = None,
) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    private_root = tmp_path / runtime.PRIVATE_DIRECTORY_NAME
    private_root.mkdir(mode=0o700)
    private_root.chmod(root_mode)
    key_path = private_root / "observer-evidence-key.v1.json"
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
) -> runtime.V075ProductionObserverEvidenceSignerV1:
    return runtime.load_v075_production_observer_evidence_signer_v1(
        repository_root=repository_root,
        private_root=private_root,
        private_key_path=key_path,
        signer_registry=registry,
    )


def _load_k7_subprocess_free(
    *,
    registry: public.V075TrustedSignerRegistryV1,
    private_root: Path,
    key_path: Path,
    repository_root: Path = REPOSITORY_ROOT,
) -> runtime.V075ProductionObserverEvidenceSignerV1:
    return runtime.load_v075_k7_subprocess_free_observer_evidence_signer_v1(
        repository_root=repository_root,
        private_root=private_root,
        private_key_path=key_path,
        signer_registry=registry,
    )


def _write_k7_repository_marker(root: Path) -> Path:
    root.mkdir(parents=True)
    git = root / runtime.K7_REPOSITORY_MARKER_NAME
    git.mkdir()
    (git / "objects").mkdir()
    (git / "refs").mkdir()
    (git / "HEAD").write_bytes(b"ref: refs/heads/main\n")
    (git / "config").write_text(
        "[core]\n"
        "\trepositoryformatversion = 0\n"
        "\tfilemode = true\n"
        "\tbare = false\n",
        encoding="utf-8",
    )
    return root.resolve()


def test_loaded_signer_implements_both_private_protocols_and_signs(
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

    assert isinstance(signer, observer.V075ObserverEvidenceSignerProtocol)
    assert isinstance(signer, reveal.V075RevealEvidenceSignerProtocol)
    assert signer.public_verification_key_v1() == (
        registry.observer_evidence_key
    )
    message = b"acfqp:v075-production-signer-focused-test:v1"
    signature = signer.sign_observer_evidence_v1(message)
    assert public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=registry.observer_evidence_key,
        message=message,
        signature_hex=signature,
    )
    assert (
        observer._sign(  # type: ignore[attr-defined]
            signer=signer,
            expected_key=registry.observer_evidence_key,
            message=b"acfqp:v075-observer-boundary-protocol-test:v1",
        )
    )


def test_k7_subprocess_free_loader_never_calls_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path / "external-secrets",
        _key_document(registry),
    )

    def forbidden_subprocess(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("K7 signer loader must not spawn subprocesses")

    monkeypatch.setattr(runtime.subprocess, "run", forbidden_subprocess)
    signer = _load_k7_subprocess_free(
        registry=registry,
        private_root=private_root,
        key_path=key_path,
    )

    assert signer.public_verification_key_v1() == (
        registry.observer_evidence_key
    )
    message = b"acfqp:v075-k7-subprocess-free-loader-test:v1"
    assert public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=registry.observer_evidence_key,
        message=message,
        signature_hex=signer.sign_observer_evidence_v1(message),
    )


def test_k7_subprocess_free_loader_rejects_in_repository_private_root(
    tmp_path: Path,
) -> None:
    repository = _write_k7_repository_marker(tmp_path / "repository")
    registry = _registry()
    private_root, key_path = _write_private_key(
        repository,
        _key_document(registry),
    )

    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load_k7_subprocess_free(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
            repository_root=repository,
        )


@pytest.mark.parametrize("marker_kind", ("missing", "empty", "gitfile"))
def test_k7_subprocess_free_loader_rejects_fake_repository(
    tmp_path: Path,
    marker_kind: str,
) -> None:
    repository = tmp_path / f"fake-{marker_kind}"
    repository.mkdir()
    if marker_kind == "empty":
        (repository / runtime.K7_REPOSITORY_MARKER_NAME).mkdir()
    elif marker_kind == "gitfile":
        (repository / runtime.K7_REPOSITORY_MARKER_NAME).write_text(
            "gitdir: /untrusted/alternate/worktree\n",
            encoding="utf-8",
        )
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path / f"external-{marker_kind}",
        _key_document(registry),
    )

    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load_k7_subprocess_free(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
            repository_root=repository.resolve(),
        )


def test_k7_subprocess_free_loader_rejects_nonroot_repository(
    tmp_path: Path,
) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path / "external-nonroot",
        _key_document(registry),
    )

    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load_k7_subprocess_free(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
            repository_root=(REPOSITORY_ROOT / "src").resolve(),
        )


@pytest.mark.parametrize("marker_kind", ("git-directory", "head-file"))
def test_k7_subprocess_free_loader_rejects_symlinked_repository_markers(
    tmp_path: Path,
    marker_kind: str,
) -> None:
    repository = tmp_path / f"symlink-marker-{marker_kind}"
    if marker_kind == "git-directory":
        repository.mkdir()
        (repository / runtime.K7_REPOSITORY_MARKER_NAME).symlink_to(
            REPOSITORY_ROOT / runtime.K7_REPOSITORY_MARKER_NAME,
            target_is_directory=True,
        )
    else:
        _write_k7_repository_marker(repository)
        head = repository / runtime.K7_REPOSITORY_MARKER_NAME / "HEAD"
        head.unlink()
        head.symlink_to(
            REPOSITORY_ROOT
            / runtime.K7_REPOSITORY_MARKER_NAME
            / "HEAD"
        )
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path / f"external-symlink-{marker_kind}",
        _key_document(registry),
    )

    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load_k7_subprocess_free(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
            repository_root=repository.resolve(),
        )


def test_signer_has_no_secret_serializer_or_path_and_repr_is_redacted(
    tmp_path: Path,
) -> None:
    registry = _registry()
    document = _key_document(registry)
    private_root, key_path = _write_private_key(
        tmp_path,
        document,
    )
    signer = _load(
        registry=registry,
        private_root=private_root,
        key_path=key_path,
    )
    public_surface = json.dumps(
        {
            "repr": repr(signer),
            "public_key": signer.public_verification_key_v1().to_document(),
            "signature": signer.sign_observer_evidence_v1(
                b"acfqp:v075-no-secret-serialization-test:v1"
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
    assert not hasattr(signer, "__dict__")
    with pytest.raises(TypeError):
        pickle.dumps(signer)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("private_exponent_hex", "3"),
        ("prime_p_hex", "3"),
        ("key_role", "CAMPAIGN_AUTHORITY"),
        ("registered_signer_registry_id", "0" * 64),
        ("registered_public_key_id", "1" * 64),
        ("public_exponent", 3),
    ),
)
def test_private_key_tampering_fails_closed_without_echoing_secrets(
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
        runtime.V075ProductionPrivateSignerInvariantViolation
    ) as caught:
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )
    assert all(secret not in str(caught.value) for secret in secrets)


def test_noncanonical_unknown_and_malformed_secret_fields_fail(
    tmp_path: Path,
) -> None:
    registry = _registry()
    document = _key_document(registry)
    raw = b" " + canonical_json_bytes(document)
    private_root, key_path = _write_private_key(
        tmp_path / "noncanonical",
        document,
        raw=raw,
    )
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )

    unknown = dict(document)
    unknown["secret_comment"] = "must-be-rejected"
    private_root, key_path = _write_private_key(
        tmp_path / "unknown",
        unknown,
    )
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
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
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )


def test_registry_mismatch_fails_before_signing(tmp_path: Path) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path,
        _key_document(registry),
    )
    wrong_observer = public.V075RSAPublicVerificationKeyV1(
        "OBSERVER_EVIDENCE",
        registry.observer_evidence_key.modulus + 2,
    )
    wrong_registry = public.V075TrustedSignerRegistryV1(
        registry.campaign_authority_key,
        wrong_observer,
    )
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
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
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )


def test_symlink_hardlink_relative_and_nested_paths_fail_closed(
    tmp_path: Path,
) -> None:
    registry = _registry()
    private_root, key_path = _write_private_key(
        tmp_path,
        _key_document(registry),
    )
    symlink = private_root / "symlink.json"
    symlink.symlink_to(key_path)
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=symlink,
        )
    symlink.unlink()

    hardlink = private_root / "hardlink.json"
    os.link(key_path, hardlink)
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
        )
    hardlink.unlink()

    nested_root = tmp_path / "nested-parent" / runtime.PRIVATE_DIRECTORY_NAME
    nested_root.mkdir(parents=True, mode=0o700)
    nested_root.chmod(0o700)
    nested = nested_root / "nested"
    nested.mkdir(mode=0o700)
    nested_key = nested / "key.json"
    nested_key.write_bytes(canonical_json_bytes(_key_document(registry)))
    nested_key.chmod(0o600)
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load(
            registry=registry,
            private_root=nested_root.resolve(),
            key_path=nested_key.resolve(),
        )

    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        runtime.load_v075_production_observer_evidence_signer_v1(
            repository_root=REPOSITORY_ROOT,
            private_root=Path(runtime.PRIVATE_DIRECTORY_NAME),
            private_key_path=Path(
                runtime.PRIVATE_DIRECTORY_NAME
            )
            / "key.json",
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


def test_in_repository_private_file_must_be_ignored_and_untracked(
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
        registry.observer_evidence_key
    )

    _git(
        "add",
        "--force",
        key_path.relative_to(repository).as_posix(),
        cwd=repository,
    )
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load(
            registry=registry,
            private_root=private_root,
            key_path=key_path,
            repository_root=repository.resolve(),
        )


def test_wrong_private_directory_name_and_signing_inputs_fail(
    tmp_path: Path,
) -> None:
    registry = _registry()
    wrong_root = tmp_path / "private"
    wrong_root.mkdir(mode=0o700)
    key_path = wrong_root / "key.json"
    key_path.write_bytes(canonical_json_bytes(_key_document(registry)))
    key_path.chmod(0o600)
    with pytest.raises(runtime.V075ProductionPrivateSignerInvariantViolation):
        _load(
            registry=registry,
            private_root=wrong_root.resolve(),
            key_path=key_path.resolve(),
        )

    private_root, key_path = _write_private_key(
        tmp_path / "valid",
        _key_document(registry),
    )
    signer = _load(
        registry=registry,
        private_root=private_root,
        key_path=key_path,
    )
    for invalid in (b"", bytearray(b"not-bytes")):
        with pytest.raises(
            runtime.V075ProductionPrivateSignerInvariantViolation
        ):
            signer.sign_observer_evidence_v1(invalid)  # type: ignore[arg-type]


def test_runtime_source_has_no_key_generation_or_target_opening() -> None:
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    assert "generate_private" not in source
    assert "open_private_observer_v1" not in source
    assert "open_production_private_observer_v1" not in source
    assert runtime.TARGET_EXECUTION_OPENED is False
    assert runtime.PRIVATE_KEY_MATERIAL_SERIALIZED is False
