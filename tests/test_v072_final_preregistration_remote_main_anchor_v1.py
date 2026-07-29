from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import inspect
from pathlib import Path
import subprocess

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import observation_support_campaign_v1 as source_campaign_v1
from acfqp import observation_support_graph_acquisition_v1 as acquisition_v1
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import verified_source_acquisition_archive_v2 as source_archive_v2
from acfqp import v072_confirmatory_execution_manifest_v1 as manifest_v1
from acfqp import v072_final_preregistration_authority_v1 as authority
from acfqp import v072_source_reconstruction_recipe_v1 as recipe_v1
from acfqp import (
    v072_remote_main_anchor_independent_verifier_v1 as independent,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _id(domain: str, payload: dict[str, object]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


def _fake_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(root), *arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(arguments)} failed: "
            + result.stderr.decode("utf-8", errors="replace")
        )
    return result.stdout.decode("utf-8", errors="strict").strip()


def _source_recipe_document() -> dict[str, object]:
    source_campaign_id = _fake_id("test-source-campaign")
    source_verification_id = _fake_id("test-source-verification")
    source_archive_id = _fake_id("test-source-archive")
    production_verification_id = _fake_id("test-production-verification")
    independent_attestation_id = _fake_id("test-source-attestation")
    component_id = _fake_id("test-source-component")
    output_ids = {
        "source_campaign_id": source_campaign_id,
        "source_campaign_verification_id": source_verification_id,
        "source_archive_id": source_archive_id,
        "production_archive_verification_id": production_verification_id,
        "independent_archive_attestation_id": (
            independent_attestation_id
        ),
        "source_archive_component_id": component_id,
    }
    def commitment(role: str, count: int, label: str) -> dict[str, object]:
        return {
            "role": role,
            "count": count,
            "ordered_merkle_root": _fake_id(label),
        }
    payload: dict[str, object] = {
        "schema": "acfqp.v072_source_reconstruction_recipe.v1",
        "schema_version": recipe_v1.SCHEMA_VERSION,
        "proposed_contract_version": recipe_v1.PROPOSED_CONTRACT_VERSION,
        "profile_key": recipe_v1.PROFILE_KEY,
        "reconstruction_inputs": {
            "constructor": recipe_v1.REGISTERED_CONSTRUCTOR,
            "verifier": recipe_v1.REGISTERED_VERIFIER,
            "max_workers": recipe_v1.RECONSTRUCTION_MAX_WORKERS,
            "registered_context_order": list(
                source_campaign_v1.REGISTERED_CONTEXT_ORDER
            ),
            "registered_context_documents": [
                item.to_document()
                for item in (
                    source_campaign_v1.observer
                    .registered_public_graph_contexts_v1()
                )
            ],
            "registered_checkpoints": list(
                source_campaign_v1.REGISTERED_CHECKPOINTS
            ),
            "registered_adjacent_pairs": [
                {
                    "context_key": key,
                    "checkpoint_pairs": [
                        list(pair) for pair in pairs
                    ],
                }
                for key, pairs in (
                    source_archive_v2.REGISTERED_ADJACENT_PAIRS.items()
                )
            ],
            "discovery_draw_count": acquisition_v1.DISCOVERY_DRAW_COUNT,
            "randomness_implementation": (
                source_campaign_v1.RANDOMNESS_IMPLEMENTATION
            ),
            "component_tree_digest": _fake_id("test-component-tree"),
            "test_command_manifest_id": _fake_id("test-command"),
            "runtime_dependency_lock_id": _fake_id(
                "test-dependency-lock"
            ),
            "interpreter_build_identity_id": _fake_id(
                "test-interpreter"
            ),
            "environment_independent_attestation_id": _fake_id(
                "test-environment-attestation"
            ),
        },
        "expected_output_ids": output_ids,
        "ordered_commitments": {
            "context_results": commitment(
                "CONTEXT_RESULT_IDS",
                0,
                "test-empty-context-root",
            ),
            "replayed_source_rows": commitment(
                "REPLAYED_SOURCE_ROW_IDS",
                1,
                "test-source-row-root",
            ),
            "archive_adjacent_pairs": commitment(
                "ARCHIVE_ADJACENT_PAIR_IDS",
                7,
                "test-adjacent-pair-root",
            ),
            "archive_trials": commitment(
                "ARCHIVE_TRIAL_IDS",
                1,
                "test-trial-root",
            ),
            "archive_feature_consensus": commitment(
                "ARCHIVE_FEATURE_CONSENSUS_IDS",
                1,
                "test-consensus-root",
            ),
            "family_manifest_id": {
                "kind": "NOT_AVAILABLE_IN_MECHANICS_FIXTURE",
            },
            "family_authority_id": {
                "kind": "NOT_AVAILABLE_IN_MECHANICS_FIXTURE",
            },
            "campaign_counters_id": {
                "kind": "NOT_AVAILABLE_IN_MECHANICS_FIXTURE",
            },
        },
        "compact_derived_artifacts": {
            "source_archive": {
                "archive_id": source_archive_id,
                "source_campaign_id": source_campaign_id,
                "source_campaign_verification_id": (
                    source_verification_id
                ),
            },
            "production_archive_verification": {
                "verification_id": production_verification_id,
                "archive_id": source_archive_id,
                "replayed_archive_id": source_archive_id,
            },
            "independent_archive_attestation": {
                "verification_id": independent_attestation_id,
                "archive_id": source_archive_id,
                "independently_recomputed_archive_id": source_archive_id,
            },
            "source_archive_component_summary": {
                "component_id": component_id,
                "archive_id": source_archive_id,
                "production_verification_id": (
                    production_verification_id
                ),
                "independent_archive_transform_attestation_id": (
                    independent_attestation_id
                ),
                "source_campaign_id": source_campaign_id,
                "source_campaign_verification_id": (
                    source_verification_id
                ),
            },
        },
        "source_graph_commitment_complete": False,
        "replay_ready": False,
        "replay_blocker": recipe_v1.INCOMPLETE_BLOCKER,
        "raw_observation_ids_persisted": False,
        "caller_supplied_expected_ids_accepted": False,
        "caller_supplied_runner_accepted": False,
        "new_observer_draws": 0,
        "max_canonical_recipe_bytes": (
            recipe_v1.MAX_CANONICAL_RECIPE_BYTES
        ),
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "recipe_id": _id(recipe_v1.RECIPE_DOMAIN, payload),
    }


def _final_documents() -> tuple[dict[str, object], dict[str, object]]:
    contexts = prereg.registered_heldout_public_contexts_v2()
    environment = prereg.frozen_heldout_environment_manifest_v1()
    recipe_document = _source_recipe_document()
    bindings: dict[str, object] = {
        "confirmatory_family_generation": (
            prereg.CONFIRMATORY_FAMILY_GENERATION
        ),
        "context_ids": [item.context_id for item in contexts],
        "law_ids": [item.law_id for item in environment.laws],
        "environment_manifest_id": environment.manifest_id,
        "source_reconstruction_recipe_repository_path": (
            manifest_v1.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
        ),
        "source_reconstruction_recipe_id": recipe_document["recipe_id"],
        "source_archive_id": _fake_id("test-source-archive"),
        "source_archive_verification_profile": (
            "verified_source_acquisition_archive_independent_verifier_v2"
        ),
        "source_archive_verification_attestation_id": _fake_id(
            "test-source-attestation"
        ),
        "arm_order": list(prereg.ARM_ORDER),
        "terminal_codes": list(prereg.TERMINAL_CODES),
        "confidence_profile_id": _fake_id("test-confidence-profile"),
        "checkpoint_cap_profile_id": _fake_id("test-checkpoint-profile"),
        "repository_url": manifest_v1.REPOSITORY_URL,
        "target_branch": manifest_v1.TARGET_BRANCH,
        "component_tree_digest": _fake_id("test-component-tree"),
        "exact_test_command": list(manifest_v1.EXACT_TEST_COMMAND),
        "deterministic_environment_settings": [
            {"name": name, "value": value}
            for name, value in manifest_v1.DETERMINISTIC_ENVIRONMENT_SETTINGS
        ],
        "test_command_manifest_id": _fake_id("test-command"),
        "runtime_dependency_lock_id": _fake_id("test-dependency-lock"),
        "interpreter_build_identity_id": _fake_id("test-interpreter"),
        "retired_development_ids_excluded": list(
            prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS
        ),
        "development_synthetic_module_excluded": (
            manifest_v1.DEVELOPMENT_SYNTHETIC_MODULE_PATH
        ),
        "final_preregistration_id_embedded": False,
        "future_binding_direction": (
            "FINAL_PREREGISTRATION_BINDS_MANIFEST_ID_ONE_WAY"
        ),
    }
    manifest_payload: dict[str, object] = {
        "schema": authority.FINAL_MANIFEST_SCHEMA,
        "schema_version": manifest_v1.SCHEMA_VERSION,
        "component_registry_id": _fake_id("test-component-registry"),
        "global_bindings": bindings,
        "final_preregistration_id_embedded": False,
    }
    manifest_document = {
        **manifest_payload,
        "manifest_id": _id(
            authority.FINAL_MANIFEST_DOMAIN,
            manifest_payload,
        ),
    }
    draft = (
        prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        .to_document()
    )
    draft.pop("preregistration_id")
    draft["confirmatory_execution_manifest_id"] = manifest_document[
        "manifest_id"
    ]
    draft["confirmatory_profile_finalized"] = True
    draft["anchor_commit_id"] = None
    draft["target_execution_allowed"] = False
    final_document = {
        **draft,
        "preregistration_id": _id(
            authority.FINAL_PREREGISTRATION_DOMAIN,
            draft,
        ),
    }
    return manifest_document, final_document


def _write_triple(
    clone: Path,
    manifest_document: dict[str, object],
    final_document: dict[str, object],
) -> None:
    recipe_path = (
        clone / authority.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    )
    manifest_path = clone / authority.FINAL_MANIFEST_REPOSITORY_PATH
    preregistration_path = (
        clone / authority.FINAL_PREREGISTRATION_REPOSITORY_PATH
    )
    recipe_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    preregistration_path.parent.mkdir(parents=True, exist_ok=True)
    recipe_path.write_bytes(
        canonical_json_bytes(_source_recipe_document())
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest_document))
    preregistration_path.write_bytes(canonical_json_bytes(final_document))


def _claim(
    clone: Path,
    remote: Path,
    manifest_document: dict[str, object],
    final_document: dict[str, object],
) -> authority.V072RemoteMainAnchorClaimV1:
    commit = _git(clone, "rev-parse", "HEAD")
    return authority.V072RemoteMainAnchorClaimV1(
        (
            authority.RemoteMainAnchorVerificationScopeV1
            .DEVELOPMENT_LOCAL_BARE_REMOTE_NONAUTHORIZING
        ),
        str(remote),
        "main",
        commit,
        _git(clone, "show", "-s", "--format=%T", commit),
        _git(clone, "show", "-s", "--format=%P", commit),
        _git(
            clone,
            "rev-parse",
            (
                f"{commit}:"
                f"{authority.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH}"
            ),
        ),
        _git(
            clone,
            "rev-parse",
            f"{commit}:{authority.FINAL_MANIFEST_REPOSITORY_PATH}",
        ),
        _git(
            clone,
            "rev-parse",
            (
                f"{commit}:"
                f"{authority.FINAL_PREREGISTRATION_REPOSITORY_PATH}"
            ),
        ),
        str(
            manifest_document["global_bindings"][
                "source_reconstruction_recipe_id"
            ]
        ),
        str(manifest_document["manifest_id"]),
        str(final_document["preregistration_id"]),
    )


def _repository_with_qualifying_commit(
    tmp_path: Path,
) -> tuple[
    Path,
    Path,
    dict[str, object],
    dict[str, object],
    authority.V072RemoteMainAnchorClaimV1,
]:
    remote = (tmp_path / "remote.git").resolve()
    clone = (tmp_path / "clone").resolve()
    subprocess.run(
        ("git", "init", "--bare", "--initial-branch=main", str(remote)),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    subprocess.run(
        ("git", "clone", str(remote), str(clone)),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    _git(clone, "config", "user.name", "V072 Test")
    _git(clone, "config", "user.email", "v072@example.invalid")
    (clone / ".gitignore").write_bytes((PROJECT_ROOT / ".gitignore").read_bytes())
    (clone / "README.md").write_text("base\n", encoding="utf-8")
    _git(clone, "add", ".gitignore", "README.md")
    _git(clone, "commit", "-m", "base")
    _git(clone, "push", "-u", "origin", "main")

    manifest_document, final_document = _final_documents()
    _write_triple(clone, manifest_document, final_document)
    ignored = subprocess.run(
        (
            "git",
            "-C",
            str(clone),
            "check-ignore",
            authority.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH,
            authority.FINAL_MANIFEST_REPOSITORY_PATH,
            authority.FINAL_PREREGISTRATION_REPOSITORY_PATH,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=15,
    )
    assert ignored.returncode == 1
    _git(
        clone,
        "add",
        authority.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH,
        authority.FINAL_MANIFEST_REPOSITORY_PATH,
        authority.FINAL_PREREGISTRATION_REPOSITORY_PATH,
    )
    _git(clone, "commit", "-m", "freeze final V072 triple")
    _git(clone, "push", "origin", "main")
    tree_paths = set(
        _git(clone, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    )
    assert authority.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH in tree_paths
    assert authority.FINAL_MANIFEST_REPOSITORY_PATH in tree_paths
    assert authority.FINAL_PREREGISTRATION_REPOSITORY_PATH in tree_paths
    return (
        remote,
        clone,
        manifest_document,
        final_document,
        _claim(
            clone,
            remote,
            manifest_document,
            final_document,
        ),
    )


def test_one_way_final_preregistration_logical_replay_is_nonauthorizing() -> None:
    manifest_document, final_document = _final_documents()
    attestation = authority.verify_v072_final_preregistration_documents_v1(
        manifest_document=manifest_document,
        final_preregistration_document=final_document,
    )
    assert attestation.manifest_id == manifest_document["manifest_id"]
    assert (
        attestation.final_preregistration_id
        == final_document["preregistration_id"]
    )
    assert attestation.one_way_binding_verified is True
    assert attestation.circular_identity_absent is True
    assert attestation.target_execution_allowed is False
    assert attestation.registered_observer_calls == 0
    assert final_document["confirmatory_execution_manifest_id"] == (
        manifest_document["manifest_id"]
    )
    assert "final_preregistration_id" not in manifest_document
    assert (
        "final_preregistration_id"
        not in manifest_document["global_bindings"]
    )
    assert final_document["preregistration_id"] not in canonical_json_bytes(
        manifest_document
    ).decode("utf-8")


def test_final_preregistration_rejects_profile_change_and_circular_id() -> None:
    manifest_document, final_document = _final_documents()
    changed_recipe_path = deepcopy(manifest_document)
    changed_recipe_path["global_bindings"][
        "source_reconstruction_recipe_repository_path"
    ] = "specs/UNREGISTERED_RECIPE.json"
    changed_manifest_payload = {
        key: value
        for key, value in changed_recipe_path.items()
        if key != "manifest_id"
    }
    changed_recipe_path["manifest_id"] = _id(
        authority.FINAL_MANIFEST_DOMAIN,
        changed_manifest_payload,
    )
    with pytest.raises(
        authority.V072FinalPreregistrationInvariantViolation,
        match="global authorities",
    ):
        authority.verify_v072_final_preregistration_documents_v1(
            manifest_document=changed_recipe_path,
            final_preregistration_document=final_document,
        )

    changed_schedule = deepcopy(final_document)
    changed_schedule["maximum_rounds"] = 3
    payload = {
        key: value
        for key, value in changed_schedule.items()
        if key != "preregistration_id"
    }
    changed_schedule["preregistration_id"] = _id(
        authority.FINAL_PREREGISTRATION_DOMAIN,
        payload,
    )
    with pytest.raises(authority.V072FinalPreregistrationInvariantViolation):
        authority.verify_v072_final_preregistration_documents_v1(
            manifest_document=manifest_document,
            final_preregistration_document=changed_schedule,
        )

    circular_manifest = deepcopy(manifest_document)
    circular_manifest["global_bindings"]["final_preregistration_id"] = (
        final_document["preregistration_id"]
    )
    circular_payload = {
        key: value
        for key, value in circular_manifest.items()
        if key != "manifest_id"
    }
    circular_manifest["manifest_id"] = _id(
        authority.FINAL_MANIFEST_DOMAIN,
        circular_payload,
    )
    with pytest.raises(authority.V072FinalPreregistrationInvariantViolation):
        authority.verify_v072_final_preregistration_documents_v1(
            manifest_document=circular_manifest,
            final_preregistration_document=final_document,
        )


@pytest.mark.parametrize(
    "attack",
    (
        "constructor",
        "context_order",
        "checkpoint",
        "randomness",
        "output_graph",
        "compact_graph",
        "merkle_role",
        "merkle_count",
        "merkle_root",
        "complete_blocker",
    ),
)
def test_independent_recipe_semantics_reject_reidentified_mutations(
    attack: str,
) -> None:
    document = deepcopy(_source_recipe_document())
    if attack == "constructor":
        document["reconstruction_inputs"]["constructor"] = "foreign"
    elif attack == "context_order":
        document["reconstruction_inputs"]["registered_context_order"].reverse()
    elif attack == "checkpoint":
        document["reconstruction_inputs"]["registered_checkpoints"] = []
    elif attack == "randomness":
        document["reconstruction_inputs"]["randomness_implementation"] = (
            "FOREIGN_RANDOMNESS"
        )
    elif attack == "output_graph":
        document["expected_output_ids"]["source_archive_id"] = "0" * 64
    elif attack == "compact_graph":
        document["compact_derived_artifacts"][
            "source_archive_component_summary"
        ]["archive_id"] = "0" * 64
    elif attack == "merkle_role":
        document["ordered_commitments"]["archive_trials"]["role"] = "FOREIGN"
    elif attack == "merkle_count":
        document["ordered_commitments"]["archive_adjacent_pairs"]["count"] = 6
    elif attack == "merkle_root":
        document["ordered_commitments"]["replayed_source_rows"][
            "ordered_merkle_root"
        ] = "not-an-id"
    else:
        document["source_graph_commitment_complete"] = True
        document["replay_ready"] = True
        document["replay_blocker"] = None
    payload = {
        key: value for key, value in document.items() if key != "recipe_id"
    }
    document["recipe_id"] = _id(recipe_v1.RECIPE_DOMAIN, payload)
    with pytest.raises(
        independent.IndependentRemoteMainAnchorVerificationViolation
    ):
        independent._verify_recipe_document_independently(document)


def test_incomplete_factories_remain_locked_with_zero_observer_calls() -> None:
    readiness = authority.inspect_v072_final_preregistration_readiness_v1(
        PROJECT_ROOT
    )
    assert readiness.final_manifest_id is None
    assert readiness.final_preregistration_id is None
    assert readiness.remote_main_anchor_id is None
    assert readiness.target_execution_allowed is False
    assert readiness.registered_observer_calls == 0
    assert (
        manifest_v1
        .SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER
    ) in (
        readiness.finalization_blockers
    )
    assert "FINAL_CONFIRMATORY_EXECUTION_MANIFEST_NOT_INSTANTIABLE" not in (
        readiness.finalization_blockers
    )
    assert "SEMANTIC_REMOTE_MAIN_PUSH_ANCHOR_NOT_VERIFIED" not in (
        readiness.finalization_blockers
    )
    with pytest.raises(authority.V072FinalPreregistrationLockedV1):
        authority.finalize_v072_final_preregistration_v1(PROJECT_ROOT)
    with pytest.raises(
        authority.V072FinalPreregistrationInvariantViolation,
        match="internally minted",
    ):
        authority.V072FinalPreregistrationV1(
            object(),
            object(),  # type: ignore[arg-type]
            {},
        )
    with pytest.raises(authority.V072FinalPreregistrationLockedV1):
        authority.mint_v072_remote_main_anchor_v1(
            repository_root=PROJECT_ROOT,
        )
    with pytest.raises(authority.V072FinalPreregistrationInvariantViolation):
        authority.V072RemoteMainAnchorV1(
            object(),
            object(),  # type: ignore[arg-type]
            "a" * 64,
        )
    assert authority.FINAL_PREREGISTRATION_ENABLED is True
    assert authority.REMOTE_MAIN_ANCHOR_AUTHORITY_ENABLED is True


def test_finalize_and_mint_signatures_accept_no_caller_ids_or_status() -> None:
    finalize_signature = inspect.signature(
        authority.finalize_v072_final_preregistration_v1
    )
    derive_signature = inspect.signature(
        authority.derive_v072_remote_main_anchor_claim_v1
    )
    mint_signature = inspect.signature(
        authority.mint_v072_remote_main_anchor_v1
    )
    assert tuple(finalize_signature.parameters) == ("repository_root",)
    assert tuple(derive_signature.parameters) == ("repository_root",)
    assert tuple(mint_signature.parameters) == (
        "repository_root",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in mint_signature.parameters.values()
    )
    forbidden = {
        "manifest_id",
        "final_preregistration_id",
        "attestation",
        "attestation_id",
        "status",
        "scope",
        "commit_id",
        "target_execution_allowed",
    }
    assert forbidden.isdisjoint(finalize_signature.parameters)
    assert forbidden.isdisjoint(derive_signature.parameters)
    assert forbidden.isdisjoint(mint_signature.parameters)
    assert "claim" not in mint_signature.parameters


def test_independent_verifier_replays_real_commit_tree_and_blobs(
    tmp_path: Path,
) -> None:
    remote, clone, _manifest, _final, claim = (
        _repository_with_qualifying_commit(tmp_path)
    )
    assert _git(clone, "remote", "get-url", "origin") == str(remote)
    attestation = (
        independent.verify_remote_main_anchor_claim_independently_v1(
            clone,
            claim,
        )
    )
    assert attestation.claim_id == claim.claim_id
    assert attestation.commit_id == claim.commit_id
    assert attestation.tree_id == claim.tree_id
    assert attestation.parent_commit_id == claim.parent_commit_id
    assert (
        attestation.source_reconstruction_recipe_blob_id
        == claim.source_reconstruction_recipe_blob_id
    )
    assert attestation.manifest_blob_id == claim.manifest_blob_id
    assert (
        attestation.final_preregistration_blob_id
        == claim.final_preregistration_blob_id
    )
    assert (
        attestation.source_reconstruction_recipe_id
        == claim.source_reconstruction_recipe_id
        == _source_recipe_document()["recipe_id"]
    )
    assert claim.to_document()[
        "source_reconstruction_recipe_repository_path"
    ] == "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"
    assert attestation.to_document()[
        "source_reconstruction_recipe_repository_path"
    ] == "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"
    assert attestation.canonical_blob_triple_verified is True
    assert attestation.first_qualifying_commit_verified is True
    assert attestation.executable_anchor_minted is False
    assert attestation.target_execution_allowed is False
    assert attestation.registered_observer_calls == 0
    with pytest.raises(
        authority.V072FinalPreregistrationLockedV1,
        match="derivation",
    ):
        authority.mint_v072_remote_main_anchor_v1(
            repository_root=clone,
        )


def test_production_replay_is_required_before_private_anchor_mint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _remote, clone, _manifest, _final, development_claim = (
        _repository_with_qualifying_commit(tmp_path)
    )
    _git(
        clone,
        "remote",
        "set-url",
        "origin",
        manifest_v1.REPOSITORY_URL,
    )
    _git(
        clone,
        "remote",
        "set-url",
        "--push",
        "origin",
        manifest_v1.REPOSITORY_URL,
    )
    production_claim = authority.derive_v072_remote_main_anchor_claim_v1(
        clone
    )
    assert production_claim.commit_id == development_claim.commit_id
    assert production_claim.verification_scope is (
        authority.RemoteMainAnchorVerificationScopeV1
        .REGISTERED_PRODUCTION_CANDIDATE
    )
    assert production_claim.repository_url == manifest_v1.REPOSITORY_URL
    attestation = independent.IndependentRemoteMainAnchorAttestationV1(
        production_claim.claim_id,
        production_claim.verification_scope,
        production_claim.repository_url,
        production_claim.commit_id,
        production_claim.tree_id,
        production_claim.parent_commit_id,
        production_claim.source_reconstruction_recipe_blob_id,
        production_claim.manifest_blob_id,
        production_claim.final_preregistration_blob_id,
        production_claim.source_reconstruction_recipe_id,
        production_claim.manifest_id,
        production_claim.final_preregistration_id,
        1,
    )
    calls: list[str] = []

    def replay(repository_root: Path, claim):
        calls.append("independent_production_replay")
        assert Path(repository_root) == clone
        assert claim == production_claim
        return attestation

    monkeypatch.setattr(
        independent,
        "verify_remote_main_anchor_claim_independently_v1",
        replay,
    )
    with pytest.raises(
        authority.V072FinalPreregistrationInvariantViolation,
        match="internal",
    ):
        authority.V072RemoteMainAnchorV1(
            object(),
            production_claim,
            attestation,
        )
    anchor = authority.mint_v072_remote_main_anchor_v1(
        repository_root=clone,
    )
    assert calls == ["independent_production_replay"]
    assert anchor.claim == production_claim
    assert anchor.independent_semantic_attestation is attestation
    assert anchor.independent_semantic_attestation_id == (
        attestation.verification_id
    )
    assert anchor.target_execution_allowed is True
    assert len(anchor.anchor_id) == 64


@pytest.mark.parametrize(
    "attack",
    (
        "dirty",
        "detached",
        "stale_origin_main",
        "wrong_origin",
        "multiple_parents",
    ),
)
def test_production_claim_derivation_rejects_local_git_attacks(
    tmp_path: Path,
    attack: str,
) -> None:
    remote, clone, _manifest, _final, _development_claim = (
        _repository_with_qualifying_commit(tmp_path)
    )
    if attack == "multiple_parents":
        _git(clone, "checkout", "-b", "side")
        (clone / "side.txt").write_text("side\n", encoding="utf-8")
        _git(clone, "add", "side.txt")
        _git(clone, "commit", "-m", "side")
        _git(clone, "checkout", "main")
        (clone / "main.txt").write_text("main\n", encoding="utf-8")
        _git(clone, "add", "main.txt")
        _git(clone, "commit", "-m", "main")
        _git(clone, "merge", "--no-ff", "side", "-m", "merge")
        _git(clone, "push", "origin", "main")
    _git(
        clone,
        "remote",
        "set-url",
        "origin",
        manifest_v1.REPOSITORY_URL,
    )
    _git(
        clone,
        "remote",
        "set-url",
        "--push",
        "origin",
        manifest_v1.REPOSITORY_URL,
    )
    if attack == "dirty":
        (clone / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    elif attack == "detached":
        _git(clone, "checkout", "--detach")
    elif attack == "stale_origin_main":
        _git(
            clone,
            "update-ref",
            "refs/remotes/origin/main",
            "HEAD^",
        )
    elif attack == "wrong_origin":
        _git(clone, "remote", "set-url", "origin", str(remote))
        _git(
            clone,
            "remote",
            "set-url",
            "--push",
            "origin",
            str(remote),
        )
    with pytest.raises(
        authority.V072FinalPreregistrationInvariantViolation
    ):
        authority.derive_v072_remote_main_anchor_claim_v1(clone)


def test_recipe_id_must_equal_manifest_global_binding(
    tmp_path: Path,
) -> None:
    remote, clone, manifest_document, final_document, _claim0 = (
        _repository_with_qualifying_commit(tmp_path)
    )
    changed_recipe = deepcopy(_source_recipe_document())
    changed_recipe["reconstruction_inputs"][
        "environment_independent_attestation_id"
    ] = _fake_id("changed-environment-attestation")
    changed_payload = {
        key: value
        for key, value in changed_recipe.items()
        if key != "recipe_id"
    }
    changed_recipe["recipe_id"] = _id(
        recipe_v1.RECIPE_DOMAIN,
        changed_payload,
    )
    recipe_path = authority.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    (clone / recipe_path).write_bytes(canonical_json_bytes(changed_recipe))
    _git(clone, "add", recipe_path)
    _git(clone, "commit", "-m", "attempt recipe substitution")
    _git(clone, "push", "origin", "main")
    changed_claim = replace(
        _claim(
            clone,
            remote,
            manifest_document,
            final_document,
        ),
        source_reconstruction_recipe_id=changed_recipe["recipe_id"],
    )
    with pytest.raises(
        independent.IndependentRemoteMainAnchorVerificationViolation,
        match="does not bind the committed recipe",
    ):
        independent.verify_remote_main_anchor_claim_independently_v1(
            clone,
            changed_claim,
        )


@pytest.mark.parametrize(
    "attack",
    (
        "detached",
        "dirty",
        "wrong_remote",
        "local_only",
        "stale_remote",
    ),
)
def test_independent_verifier_rejects_checkout_and_remote_attacks(
    tmp_path: Path,
    attack: str,
) -> None:
    remote, clone, _manifest, _final, claim = (
        _repository_with_qualifying_commit(tmp_path)
    )
    if attack == "detached":
        _git(clone, "checkout", "--detach", claim.commit_id)
    elif attack == "dirty":
        (
            clone
            / authority.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
        ).write_text("{}\n", encoding="utf-8")
    elif attack == "wrong_remote":
        other = (tmp_path / "other.git").resolve()
        subprocess.run(
            ("git", "init", "--bare", "--initial-branch=main", str(other)),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
        _git(clone, "remote", "set-url", "origin", str(other))
    elif attack == "local_only":
        (clone / "LOCAL_ONLY").write_text("not pushed\n", encoding="utf-8")
        _git(clone, "add", "LOCAL_ONLY")
        _git(clone, "commit", "-m", "local only")
    else:
        updater = (tmp_path / "updater").resolve()
        subprocess.run(
            ("git", "clone", str(remote), str(updater)),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
        _git(updater, "config", "user.name", "V072 Updater")
        _git(updater, "config", "user.email", "updater@example.invalid")
        (updater / "REMOTE_ONLY").write_text("new remote head\n", encoding="utf-8")
        _git(updater, "add", "REMOTE_ONLY")
        _git(updater, "commit", "-m", "advance remote")
        _git(updater, "push", "origin", "main")
    with pytest.raises(
        independent.IndependentRemoteMainAnchorVerificationViolation
    ):
        independent.verify_remote_main_anchor_claim_independently_v1(
            clone,
            claim,
        )


def test_parent_containing_final_id_cannot_be_reanchored(
    tmp_path: Path,
) -> None:
    remote, clone, manifest_document, final_document, _claim0 = (
        _repository_with_qualifying_commit(tmp_path)
    )
    (clone / "AFTER").write_text("after\n", encoding="utf-8")
    _git(clone, "add", "AFTER")
    _git(clone, "commit", "-m", "attempt later anchor")
    _git(clone, "push", "origin", "main")
    later_claim = _claim(
        clone,
        remote,
        manifest_document,
        final_document,
    )
    with pytest.raises(
        independent.IndependentRemoteMainAnchorVerificationViolation,
        match=(
            "parent contains IDs=.*source reconstruction recipe"
            ".*final preregistration"
        ),
    ):
        independent.verify_remote_main_anchor_claim_independently_v1(
            clone,
            later_claim,
        )


def test_remove_and_readd_cannot_mint_a_new_first_anchor(
    tmp_path: Path,
) -> None:
    remote, clone, manifest_document, final_document, _claim0 = (
        _repository_with_qualifying_commit(tmp_path)
    )
    _git(
        clone,
        "rm",
        authority.FINAL_MANIFEST_REPOSITORY_PATH,
        authority.FINAL_PREREGISTRATION_REPOSITORY_PATH,
    )
    _git(clone, "commit", "-m", "remove final manifest/preregistration")
    _git(clone, "push", "origin", "main")
    _write_triple(clone, manifest_document, final_document)
    _git(
        clone,
        "add",
        authority.FINAL_MANIFEST_REPOSITORY_PATH,
        authority.FINAL_PREREGISTRATION_REPOSITORY_PATH,
    )
    _git(clone, "commit", "-m", "readd final manifest/preregistration")
    _git(clone, "push", "origin", "main")
    readded_claim = _claim(
        clone,
        remote,
        manifest_document,
        final_document,
    )
    with pytest.raises(
        independent.IndependentRemoteMainAnchorVerificationViolation,
        match="previously added or removed IDs=.*final preregistration",
    ):
        independent.verify_remote_main_anchor_claim_independently_v1(
            clone,
            readded_claim,
        )


def test_recipe_remove_and_readd_is_reported_by_ancestry_replay(
    tmp_path: Path,
) -> None:
    remote, clone, manifest_document, final_document, _claim0 = (
        _repository_with_qualifying_commit(tmp_path)
    )
    recipe_path = authority.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    _git(clone, "rm", recipe_path)
    _git(clone, "commit", "-m", "remove source recipe")
    _git(clone, "push", "origin", "main")
    (
        clone / recipe_path
    ).write_bytes(canonical_json_bytes(_source_recipe_document()))
    _git(clone, "add", recipe_path)
    _git(clone, "commit", "-m", "readd source recipe")
    _git(clone, "push", "origin", "main")
    readded_claim = _claim(
        clone,
        remote,
        manifest_document,
        final_document,
    )
    with pytest.raises(
        independent.IndependentRemoteMainAnchorVerificationViolation,
        match=(
            "previously added or removed IDs="
            ".*source reconstruction recipe"
        ),
    ):
        independent.verify_remote_main_anchor_claim_independently_v1(
            clone,
            readded_claim,
        )
