from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_preopen_target_authorization_v1 as preopen
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_remote_main_anchor_verifier_v1 as remote
from tests.test_v075_private_observer_boundary_v1 import _namespace
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-preopen-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _registry() -> public.V075TrustedSignerRegistryV1:
    return public.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )


def _commitment() -> public.V075OpaqueEnvironmentCommitmentV1:
    return public.V075OpaqueEnvironmentCommitmentV1(
        public.freeze_v075_public_family_generation_v1(),
        _id("opaque-digest"),
    )


def _anchor(
    *,
    final_id: str | None = None,
) -> remote.V075RemoteMainAnchorAttestationV1:
    commitment = _commitment()
    return remote.V075RemoteMainAnchorAttestationV1(
        remote._ISSUER,  # type: ignore[attr-defined]
        "1" * 40,
        "2" * 40,
        ("3" * 40,),
        "4" * 40,
        "5" * 40,
        _id("manifest"),
        _id("final") if final_id is None else final_id,
        public.freeze_v075_public_family_generation_v1().generation_id,
        commitment.commitment_id,
        _id("observer-profile"),
        _registry(),
        _id("component-registry"),
        _id("authority-registry"),
    )


def _attestation(
    anchor: remote.V075RemoteMainAnchorAttestationV1,
) -> preopen.V075PrivateRevealAttestationV1:
    external_id = _id("private-verification")
    message = preopen.private_reveal_attestation_signing_bytes_v1(
        anchor=anchor,
        private_verification_external_id=external_id,
    )
    return (
        preopen
        .verify_and_bind_v075_signed_private_reveal_attestation_v1(
            anchor=anchor,
            private_verification_external_id=external_id,
            observer_signature_hex=sign_test_message(
                message,
                key_role="OBSERVER_EVIDENCE",
            ),
        )
    )


def _walk_keys(value) -> tuple[str, ...]:
    if isinstance(value, dict):
        return tuple(value) + tuple(
            key
            for child in value.values()
            for key in _walk_keys(child)
        )
    if isinstance(value, list):
        return tuple(
            key for child in value for key in _walk_keys(child)
        )
    return ()


def test_signed_private_reveal_attestation_is_law_free_and_replayable() -> None:
    anchor = _anchor()
    attestation = _attestation(anchor)
    replayed = preopen.load_and_verify_v075_private_reveal_attestation_v1(
        raw=attestation.canonical_bytes,
        anchor=anchor,
    )
    assert replayed == attestation
    document = attestation.to_document()
    assert document["verification_result"] == "MATCH"
    assert document["private_reveal_semantically_verified"] is True
    assert document["secret_salt_serialized"] is False
    assert document["private_environment_serialized"] is False
    assert document["transition_law_serialized"] is False
    assert document["random_tape_serialized"] is False
    assert document["observer_open_performed"] is False
    assert document["observer_session_created"] is False
    keys = set(_walk_keys(document))
    assert {
        "secret_laws",
        "private_environment",
        "random_words",
        "kernel",
        "tape",
    }.isdisjoint(keys)


def test_reveal_signature_and_anchor_transplants_are_rejected() -> None:
    anchor = _anchor()
    attestation = _attestation(anchor)
    tampered = json.loads(attestation.canonical_bytes)
    tampered["private_verification_external_id"] = _id("changed")
    with pytest.raises(
        preopen.V075PreopenAuthorizationInvariantViolation,
        match="signature|transplanted|identity",
    ):
        preopen.load_and_verify_v075_private_reveal_attestation_v1(
            raw=canonical_json_bytes(tampered),
            anchor=anchor,
        )
    with pytest.raises(
        preopen.V075PreopenAuthorizationInvariantViolation,
        match="transplanted|signature",
    ):
        preopen.load_and_verify_v075_private_reveal_attestation_v1(
            raw=attestation.canonical_bytes,
            anchor=_anchor(final_id=_id("foreign-final")),
        )


def test_callers_cannot_mint_authorization_chain_types() -> None:
    anchor = _anchor()
    attestation = _attestation(anchor)
    with pytest.raises(
        preopen.V075PreopenAuthorizationInvariantViolation,
        match="signature",
    ):
        preopen.V075PrivateRevealAttestationV1(
            object(),
            anchor,
            attestation.private_verification_external_id,
            attestation.observer_signature_hex,
        )
    with pytest.raises(
        preopen.V075PreopenAuthorizationInvariantViolation,
        match="verifier-issued",
    ):
        preopen.V075TrackedPreopenBlobClosureV1(
            object(),
            anchor,
            _id("manifest-bytes"),
            _id("final-bytes"),
            (_id("component"),),
            (_id("authority"),),
        )
    with pytest.raises(
        preopen.V075PreopenAuthorizationInvariantViolation,
        match="identity graph",
    ):
        preopen.V075ObserverOpenAuthorizationV1(
            object(),
            anchor,
            object(),  # type: ignore[arg-type]
            anchor.signer_registry,
            _commitment(),
            attestation,
        )


def test_complete_typed_chain_still_records_actual_open_false() -> None:
    anchor = _anchor()
    commitment = _commitment()
    assert commitment.commitment_id == (
        anchor.opaque_environment_commitment_id
    )
    closure = preopen.V075TrackedPreopenBlobClosureV1(
        preopen._BLOB_CLOSURE_ISSUER,  # type: ignore[attr-defined]
        anchor,
        _id("manifest-bytes"),
        _id("final-bytes"),
        tuple(
            _id(f"component-{index}")
            for index, _item in enumerate(
                remote.REQUIRED_COMPONENT_SPECS
            )
        ),
        tuple(
            _id(f"authority-{index}")
            for index, _item in enumerate(
                remote.REQUIRED_AUTHORITY_ROLE_ORDER
            )
        ),
    )
    authorization = preopen.V075ObserverOpenAuthorizationV1(
        preopen._AUTHORIZATION_ISSUER,  # type: ignore[attr-defined]
        anchor,
        closure,
        anchor.signer_registry,
        commitment,
        _attestation(anchor),
    )
    document = authorization.to_document()
    assert document["authorization_ready"] is True
    assert document["all_committed_blob_semantic_verifiers_passed"] is True
    assert document["observer_open_performed"] is False
    assert document["observer_session_created"] is False
    assert document["target_law_read"] is False
    assert document["target_tape_read"] is False
    assert document["sentinel_created"] is False


def test_current_repository_remains_fail_closed_and_target_free() -> None:
    readiness = preopen.assess_v075_preopen_target_authorization_v1(
        repository_root=PROJECT_ROOT,
        private_reveal_attestation_bytes=b"{}",
    )
    document = readiness.to_document()
    assert readiness.ready is False
    assert readiness.authorization is None
    assert document["registered_target_execution_allowed"] is False
    assert document["official_execution_allowed"] is False
    assert document["observer_open_performed"] is False
    assert document["observer_session_created"] is False
    assert document["target_law_read"] is False
    assert document["target_tape_read"] is False
    assert document["sentinel_created"] is False
    with pytest.raises(preopen.V075PreopenAuthorizationNotReady):
        preopen.require_ready_v075_preopen_target_authorization_v1(
            readiness
        )


def test_production_assessor_accepts_no_law_tape_or_expected_identity() -> None:
    signature = inspect.signature(
        preopen.assess_v075_preopen_target_authorization_v1
    )
    assert tuple(signature.parameters) == (
        "repository_root",
        "private_reveal_attestation_bytes",
    )
    forbidden = {
        "law",
        "laws",
        "private_environment",
        "salt",
        "tape",
        "kernel",
        "observer",
        "namespace",
        "expected_id",
        "signer_registry",
        "commitment",
        "anchor",
    }
    assert forbidden.isdisjoint(signature.parameters)
    with pytest.raises(TypeError):
        preopen.assess_v075_preopen_target_authorization_v1(
            repository_root=PROJECT_ROOT,
            private_reveal_attestation_bytes=b"{}",
            law=object(),  # type: ignore[call-arg]
        )


def test_legacy_remote_open_authority_cannot_reach_open_or_closure_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy = remote.V075ProductionOpenAuthorityV1(
        remote._ISSUER,  # type: ignore[attr-defined]
        _anchor(),
    )
    assert legacy.to_document()["observer_open_allowed"] is False
    assert (
        legacy.to_document()["accepted_by_private_observer_boundary"]
        is False
    )
    namespace = _namespace("legacy-authority-bypass")
    monkeypatch.setattr(
        observer,
        "_open_private_observer_from_binding_v1",
        lambda **_kwargs: pytest.fail("observer open path was reached"),
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="reveal-attested pre-open authorization",
    ):
        observer.open_private_observer_v1(
            authority=legacy,  # type: ignore[arg-type]
            namespace=namespace,
            private_salt=object(),  # type: ignore[arg-type]
            private_environment=object(),  # type: ignore[arg-type]
            observer_signer=object(),  # type: ignore[arg-type]
            session_external_id=_id("must-not-open"),
        )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="reveal-attested pre-open authorization",
    ):
        observer.verify_private_observer_journal_closure_v1(
            closure=object(),  # type: ignore[arg-type]
            authority=legacy,  # type: ignore[arg-type]
            namespace=namespace,
            private_salt=object(),  # type: ignore[arg-type]
            private_environment=object(),  # type: ignore[arg-type]
        )


def test_module_has_no_observer_private_environment_or_kernel_dependency() -> None:
    source = Path(preopen.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert all(
        fragment not in name
        for name in imported
        for fragment in (
            "private_observer",
            "private_environment",
            "transition_engine",
            "batched_observer",
        )
    )
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    }
    assert {
        "open_private_observer_v1",
        "open_construction_private_observer_fixture_v1",
        "observe_v1",
        "generate_v075_private_environment_v1",
    }.isdisjoint(calls)


def test_authorization_semantic_replay_cannot_accept_claimed_status_only() -> None:
    signature = inspect.signature(
        preopen.verify_v075_observer_open_authorization_v1
    )
    assert tuple(signature.parameters) == (
        "repository_root",
        "private_reveal_attestation_bytes",
        "claimed_authorization_bytes",
    )
    forbidden = {
        "ready",
        "status",
        "authorization_id",
        "manifest_id",
        "final_preregistration_id",
        "component_registry_id",
        "authority_registry_id",
    }
    assert forbidden.isdisjoint(signature.parameters)
