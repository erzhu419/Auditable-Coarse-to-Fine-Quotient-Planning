from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
from pathlib import Path
import subprocess

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_confirmatory_manifest_preregistration_v2 as manifest
from acfqp import v075_production_campaign_runner_v1 as runner
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_remote_main_anchor_verifier_v2 as remote
from tests import (
    test_v075_manifest_preregistration_remote_main_anchor_v2 as anchor_fixture,
)
from tests import test_v075_preopen_target_authorization_v1 as preopen_v1_fixture
from tests.v075_signature_test_support import (
    make_public_key,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-public-namespace-v2-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _manifest_bytes(
    root: Path,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
) -> bytes:
    process = subprocess.run(
        (
            "git",
            "-C",
            str(root),
            "cat-file",
            "blob",
            anchor.manifest_blob_id,
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return process.stdout


def _commitment(
    root: Path,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
) -> public.V075OpaqueEnvironmentCommitmentV1:
    document = loads_canonical_json(_manifest_bytes(root, anchor))
    opaque = document["opaque_environment_commitment"]
    return public.V075OpaqueEnvironmentCommitmentV1(
        public.freeze_v075_public_family_generation_v1(),
        opaque["commitment_digest"],
    )


@pytest.fixture(scope="module")
def anchored_graph(tmp_path_factory):
    root = anchor_fixture._ready_repository(
        tmp_path_factory.mktemp("v075-public-namespace-v2")
    )
    anchor = remote.verify_v075_remote_main_anchor_independently_v2(root)
    commitment = _commitment(root, anchor)
    namespace = namespace_v2.freeze_v075_public_target_tape_namespace_v2(
        repository_root=root,
        anchor=anchor,
        environment_commitment=commitment,
    )
    return root, anchor, commitment, namespace


def test_exact_v2_namespace_binds_the_complete_public_identity_graph(
    anchored_graph,
) -> None:
    root, anchor, commitment, namespace = anchored_graph
    workload = manifest.freeze_v075_confirmatory_public_workload_v2()
    profile = runner.freeze_v075_production_campaign_runner_profile_v1()
    document = namespace.to_document()

    assert type(namespace) is namespace_v2.V075PublicTargetTapeNamespaceV2
    assert namespace.anchor == anchor
    assert namespace.workload == workload
    assert namespace.family == public.freeze_v075_public_family_generation_v1()
    assert namespace.runner_profile == profile
    assert namespace.environment_commitment == commitment
    assert namespace.signer_registry == anchor.signer_registry
    assert document["remote_main_anchor_id"] == anchor.anchor_id
    assert document["manifest_id"] == anchor.manifest_id
    assert (
        document["final_preregistration_id"]
        == anchor.final_preregistration_id
    )
    assert document["component_registry_id"] == anchor.component_registry_id
    assert (
        document["semantic_registry_binding_id"]
        == anchor.semantic_registry_binding_id
    )
    assert (
        document["semantic_artifact_replay_id"]
        == anchor.semantic_artifact_replay_id
    )
    assert document["workload_id"] == anchor.workload_id
    assert document["runner_profile_id"] == anchor.runner_profile_id
    assert (
        document["opaque_environment_commitment_id"]
        == anchor.opaque_environment_commitment_id
    )
    assert document["signer_registry_id"] == anchor.signer_registry.registry_id
    assert document["v1_external_claim_projection_present"] is False
    assert document["v1_external_claim_projection_accepted"] is False
    assert document["observer_open_authority"] is False
    assert document["observer_opened"] is False
    assert document["target_accessed"] is False
    assert document["target_law_serialized"] is False
    assert document["target_tape_serialized"] is False
    assert document["private_bytes_accepted"] is False

    replayed, verified = (
        namespace_v2.verify_v075_public_target_tape_namespace_bytes_v2(
            repository_root=root,
            anchor=anchor,
            environment_commitment=commitment,
            raw=namespace.canonical_bytes,
        )
    )
    assert replayed == namespace
    assert verified.namespace_id == namespace.target_tape_namespace_id
    assert verified.replayed_namespace_id == namespace.target_tape_namespace_id
    assert verified.runner_profile_id == profile.profile_id


def test_namespace_factory_accepts_no_v1_claim_or_caller_profile_channels(
) -> None:
    parameters = inspect.signature(
        namespace_v2.freeze_v075_public_target_tape_namespace_v2
    ).parameters
    assert tuple(parameters) == (
        "repository_root",
        "anchor",
        "environment_commitment",
    )
    forbidden = {
        "remote_main_claim",
        "final_preregistration_claim",
        "observer_profile_claim",
        "external_claim",
        "workload",
        "family",
        "runner_profile",
        "signer_registry",
        "private_salt",
        "private_environment",
        "target_law",
        "target_tape",
    }
    assert forbidden.isdisjoint(parameters)
    source = inspect.getsource(namespace_v2)
    assert "V075SignedExternalAuthorityClaimV1" not in source
    assert "derive_public_target_tape_namespace_v1" not in source
    assert "open_private_observer" not in source
    assert "secret_laws_for_commitment" not in source


def test_v1_anchor_cannot_cross_into_v2_namespace(anchored_graph) -> None:
    root, _anchor, commitment, _namespace = anchored_graph
    with pytest.raises(
        namespace_v2.V075PublicTargetTapeNamespaceV2InvariantViolation
    ):
        namespace_v2.freeze_v075_public_target_tape_namespace_v2(
            repository_root=root,
            anchor=preopen_v1_fixture._anchor(),
            environment_commitment=commitment,
        )


@pytest.mark.parametrize(
    "field",
    (
        "manifest_id",
        "final_preregistration_id",
        "workload_id",
        "semantic_registry_binding_id",
        "semantic_artifact_replay_id",
        "runner_profile_id",
    ),
)
def test_stale_or_cross_role_anchor_is_rejected(
    anchored_graph,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    root, anchor, commitment, _namespace = anchored_graph
    stale = replace(anchor, **{field: _id(f"stale-{field}")})
    monkeypatch.setattr(
        remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: anchor,
    )
    with pytest.raises(
        namespace_v2.V075PublicTargetTapeNamespaceV2InvariantViolation
    ):
        namespace_v2.freeze_v075_public_target_tape_namespace_v2(
            repository_root=root,
            anchor=stale,
            environment_commitment=commitment,
        )


def test_commitment_and_registry_transplants_are_rejected(
    anchored_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, anchor, commitment, _namespace = anchored_graph
    monkeypatch.setattr(
        remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: anchor,
    )
    wrong_commitment = public.V075OpaqueEnvironmentCommitmentV1(
        commitment.family,
        _id("wrong-commitment-digest"),
    )
    with pytest.raises(
        namespace_v2.V075PublicTargetTapeNamespaceV2InvariantViolation
    ):
        namespace_v2.freeze_v075_public_target_tape_namespace_v2(
            repository_root=root,
            anchor=anchor,
            environment_commitment=wrong_commitment,
        )

    wrong_registry = public.V075TrustedSignerRegistryV1(
        public.V075RSAPublicVerificationKeyV1(
            "CAMPAIGN_AUTHORITY",
            make_public_key("CAMPAIGN_AUTHORITY").modulus,
            public_exponent=65_539,
        ),
        make_public_key("OBSERVER_EVIDENCE"),
    )
    stale_anchor = replace(anchor, signer_registry=wrong_registry)
    with pytest.raises(
        namespace_v2.V075PublicTargetTapeNamespaceV2InvariantViolation
    ):
        namespace_v2.freeze_v075_public_target_tape_namespace_v2(
            repository_root=root,
            anchor=stale_anchor,
            environment_commitment=commitment,
        )


def test_stale_workload_and_runner_profile_are_rejected(
    anchored_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, anchor, commitment, _namespace = anchored_graph
    monkeypatch.setattr(
        remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: anchor,
    )

    exact_workload = manifest.freeze_v075_confirmatory_public_workload_v2()
    stale_workload = object.__new__(
        manifest.V075ConfirmatoryPublicWorkloadV2
    )
    for name in (
        "_issuer",
        "family",
        "generation_profile",
        "worker_registry",
        "threshold_profile",
        "cap_profile",
        "runner_profile",
    ):
        object.__setattr__(
            stale_workload,
            name,
            getattr(exact_workload, name),
        )
    object.__setattr__(stale_workload, "_workload_id", _id("stale-workload"))
    monkeypatch.setattr(
        manifest,
        "freeze_v075_confirmatory_public_workload_v2",
        lambda: stale_workload,
    )
    with pytest.raises(
        namespace_v2.V075PublicTargetTapeNamespaceV2InvariantViolation
    ):
        namespace_v2.freeze_v075_public_target_tape_namespace_v2(
            repository_root=root,
            anchor=anchor,
            environment_commitment=commitment,
        )

    monkeypatch.undo()
    monkeypatch.setattr(
        remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: anchor,
    )
    exact_profile = (
        runner.freeze_v075_production_campaign_runner_profile_v1()
    )
    stale_profile = object.__new__(
        runner.V075ProductionCampaignRunnerProfileV1
    )
    object.__setattr__(stale_profile, "_issuer", object())
    object.__setattr__(
        stale_profile,
        "max_workers",
        exact_profile.max_workers,
    )
    object.__setattr__(stale_profile, "_profile_id", _id("stale-runner"))
    monkeypatch.setattr(
        runner,
        "freeze_v075_production_campaign_runner_profile_v1",
        lambda: stale_profile,
    )
    with pytest.raises(
        namespace_v2.V075PublicTargetTapeNamespaceV2InvariantViolation
    ):
        namespace_v2.freeze_v075_public_target_tape_namespace_v2(
            repository_root=root,
            anchor=anchor,
            environment_commitment=commitment,
        )


def test_namespace_byte_mutation_and_unknown_fields_fail(
    anchored_graph,
) -> None:
    root, anchor, commitment, namespace = anchored_graph
    document = namespace.to_document()
    document["unknown"] = True
    with pytest.raises(
        namespace_v2.V075PublicTargetTapeNamespaceV2InvariantViolation
    ):
        namespace_v2.verify_v075_public_target_tape_namespace_bytes_v2(
            repository_root=root,
            anchor=anchor,
            environment_commitment=commitment,
            raw=canonical_json_bytes(document),
        )

    altered = namespace.to_document()
    altered["runner_profile_id"] = _id("altered-runner")
    with pytest.raises(
        namespace_v2.V075PublicTargetTapeNamespaceV2InvariantViolation
    ):
        namespace_v2.verify_v075_public_target_tape_namespace_bytes_v2(
            repository_root=root,
            anchor=anchor,
            environment_commitment=commitment,
            raw=canonical_json_bytes(altered),
        )
