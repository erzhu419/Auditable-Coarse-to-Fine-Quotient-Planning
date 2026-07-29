"""Independent Git-object verifier for the V0-072 remote-main anchor claim.

This verifier never runs ``fetch``, ``pull``, ``push``, or any registered
observer.  It checks a clean attached ``main`` checkout, the configured
``origin/main`` tracking ref, real commit/tree/blob objects, canonical source
recipe/manifest/preregistration bytes, the one-way identity dependency, and
absence of the recipe and final-preregistration IDs from earlier ancestry.

Passing produces a nonauthorizing semantic attestation.  The separate anchor
authority remains locked until the real final artifacts are available.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any
from urllib.parse import unquote, urlparse

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import observation_support_campaign_v1 as source_campaign_v1
from acfqp import observation_support_graph_acquisition_v1 as acquisition_v1
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import verified_source_acquisition_archive_v2 as source_archive_v2
from acfqp import v072_confirmatory_execution_manifest_v1 as manifest_v1
from acfqp import v072_execution_environment_authority_v1 as execution_env
from acfqp import (
    v072_execution_environment_independent_verifier_v1
    as execution_env_independent,
)
from acfqp import v072_final_preregistration_authority_v1 as anchor_schema
from acfqp import v072_source_reconstruction_recipe_v1 as recipe_v1


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_remote_main_anchor_independent_verifier_v1"
VERIFICATION_DOMAIN = (
    "acfqp:v072-remote-main-anchor-independent-attestation:v1"
)

_REQUIRED_MANIFEST_GLOBAL_BINDINGS = frozenset(
    {
        "confirmatory_family_generation",
        "context_ids",
        "law_ids",
        "environment_manifest_id",
        "source_reconstruction_recipe_repository_path",
        "source_reconstruction_recipe_id",
        "source_archive_id",
        "source_archive_verification_profile",
        "source_archive_verification_attestation_id",
        "arm_order",
        "terminal_codes",
        "confidence_profile_id",
        "checkpoint_cap_profile_id",
        "repository_url",
        "target_branch",
        "component_tree_digest",
        "exact_test_command",
        "deterministic_environment_settings",
        "test_command_manifest_id",
        "runtime_dependency_lock_id",
        "interpreter_build_identity_id",
        "retired_development_ids_excluded",
        "development_synthetic_module_excluded",
        "final_preregistration_id_embedded",
        "future_binding_direction",
    }
)


class IndependentRemoteMainAnchorVerificationViolation(ValueError):
    """The Git history, artifact bytes, or one-way identity graph failed."""


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
    except (TypeError, ValueError) as error:
        raise IndependentRemoteMainAnchorVerificationViolation(
            str(error)
        ) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + encoded
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IndependentRemoteMainAnchorVerificationViolation(
            f"{field_name} is not one lowercase SHA-256 content ID"
        ) from error


def _repository_root(value: str | os.PathLike[str]) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        raise IndependentRemoteMainAnchorVerificationViolation(
            "repository root must be absolute"
        )
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as error:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "repository root does not exist"
        ) from error
    if resolved != candidate or not resolved.is_dir():
        raise IndependentRemoteMainAnchorVerificationViolation(
            "repository root is noncanonical, symlinked, or not a directory"
        )
    return resolved


def _run_git(
    root: Path,
    *arguments: str,
    accepted_return_codes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ("git", "-C", os.fspath(root), *arguments),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "Git object replay could not complete"
        ) from error
    if result.returncode not in accepted_return_codes:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "Git object replay failed for " + " ".join(arguments)
        )
    return result


def _git_text(root: Path, *arguments: str) -> str:
    data = _run_git(root, *arguments).stdout
    try:
        return data.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "Git metadata is not canonical UTF-8"
        ) from error


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IndependentRemoteMainAnchorVerificationViolation(
                f"duplicate committed JSON key: {key}"
            )
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise IndependentRemoteMainAnchorVerificationViolation(
        f"non-finite committed JSON token: {value}"
    )


def _parse_canonical_json_blob(data: bytes, label: str) -> dict[str, Any]:
    try:
        document = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        IndependentRemoteMainAnchorVerificationViolation,
    ) as error:
        raise IndependentRemoteMainAnchorVerificationViolation(
            f"{label} blob is not strict JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != data:
        raise IndependentRemoteMainAnchorVerificationViolation(
            f"{label} blob bytes are not canonical JSON"
        )
    return document


def _verify_manifest_document_independently(
    document: dict[str, Any],
) -> str:
    expected_keys = {
        "schema",
        "schema_version",
        "component_registry_id",
        "global_bindings",
        "final_preregistration_id_embedded",
        "manifest_id",
    }
    bindings = document.get("global_bindings")
    if (
        set(document) != expected_keys
        or document.get("schema") != anchor_schema.FINAL_MANIFEST_SCHEMA
        or document.get("schema_version") != manifest_v1.SCHEMA_VERSION
        or document.get("final_preregistration_id_embedded") is not False
        or type(bindings) is not dict
        or set(bindings) != _REQUIRED_MANIFEST_GLOBAL_BINDINGS
        or bindings.get("final_preregistration_id_embedded") is not False
        or bindings.get("future_binding_direction")
        != "FINAL_PREREGISTRATION_BINDS_MANIFEST_ID_ONE_WAY"
        or "final_preregistration_id" in bindings
        or "preregistration_id" in bindings
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed execution manifest is not the frozen one-way schema"
        )
    _cid(document.get("component_registry_id"), "component registry")
    for field_name in (
        "source_reconstruction_recipe_id",
        "source_archive_id",
        "source_archive_verification_attestation_id",
        "environment_manifest_id",
        "confidence_profile_id",
        "checkpoint_cap_profile_id",
        "component_tree_digest",
        "test_command_manifest_id",
        "runtime_dependency_lock_id",
        "interpreter_build_identity_id",
    ):
        _cid(bindings.get(field_name), field_name)
    contexts = prereg.registered_heldout_public_contexts_v2()
    environment = prereg.frozen_heldout_environment_manifest_v1()
    if (
        bindings.get("repository_url") != manifest_v1.REPOSITORY_URL
        or bindings.get("target_branch") != manifest_v1.TARGET_BRANCH
        or bindings.get("source_reconstruction_recipe_repository_path")
        != anchor_schema.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
        or bindings.get("confirmatory_family_generation")
        != prereg.CONFIRMATORY_FAMILY_GENERATION
        or bindings.get("context_ids")
        != [item.context_id for item in contexts]
        or bindings.get("law_ids")
        != [item.law_id for item in environment.laws]
        or bindings.get("environment_manifest_id")
        != environment.manifest_id
        or bindings.get("arm_order") != list(prereg.ARM_ORDER)
        or bindings.get("terminal_codes") != list(prereg.TERMINAL_CODES)
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed manifest global authorities changed"
        )
    payload = {
        key: value for key, value in document.items() if key != "manifest_id"
    }
    manifest_id = _content_id(
        anchor_schema.FINAL_MANIFEST_DOMAIN,
        payload,
    )
    if document.get("manifest_id") != manifest_id:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed execution manifest ID differs from its bytes"
        )
    return manifest_id


def _verify_recipe_document_independently(
    document: dict[str, Any],
) -> str:
    expected_payload_keys = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "reconstruction_inputs",
        "expected_output_ids",
        "ordered_commitments",
        "compact_derived_artifacts",
        "source_graph_commitment_complete",
        "replay_ready",
        "replay_blocker",
        "raw_observation_ids_persisted",
        "caller_supplied_expected_ids_accepted",
        "caller_supplied_runner_accepted",
        "new_observer_draws",
        "max_canonical_recipe_bytes",
        "official_execution_allowed",
    }
    inputs = document.get("reconstruction_inputs")
    output_ids = document.get("expected_output_ids")
    commitments = document.get("ordered_commitments")
    artifacts = document.get("compact_derived_artifacts")
    expected_input_keys = {
        "constructor",
        "verifier",
        "max_workers",
        "registered_context_order",
        "registered_context_documents",
        "registered_checkpoints",
        "registered_adjacent_pairs",
        "discovery_draw_count",
        "randomness_implementation",
        "component_tree_digest",
        "test_command_manifest_id",
        "runtime_dependency_lock_id",
        "interpreter_build_identity_id",
        "environment_independent_attestation_id",
    }
    expected_output_keys = {
        "source_campaign_id",
        "source_campaign_verification_id",
        "source_archive_id",
        "production_archive_verification_id",
        "independent_archive_attestation_id",
        "source_archive_component_id",
    }
    expected_artifact_keys = {
        "source_archive",
        "production_archive_verification",
        "independent_archive_attestation",
        "source_archive_component_summary",
    }
    expected_commitment_roles = {
        "context_results": "CONTEXT_RESULT_IDS",
        "replayed_source_rows": "REPLAYED_SOURCE_ROW_IDS",
        "archive_adjacent_pairs": "ARCHIVE_ADJACENT_PAIR_IDS",
        "archive_trials": "ARCHIVE_TRIAL_IDS",
        "archive_feature_consensus": "ARCHIVE_FEATURE_CONSENSUS_IDS",
    }
    expected_commitment_keys = {
        *expected_commitment_roles,
        "family_manifest_id",
        "family_authority_id",
        "campaign_counters_id",
    }
    registered_contexts = (
        source_campaign_v1.observer.registered_public_graph_contexts_v1()
    )
    expected_adjacent_pairs = [
        {
            "context_key": key,
            "checkpoint_pairs": [list(pair) for pair in pairs],
        }
        for key, pairs in source_archive_v2.REGISTERED_ADJACENT_PAIRS.items()
    ]
    if (
        set(document) != {*expected_payload_keys, "recipe_id"}
        or document.get("schema")
        != "acfqp.v072_source_reconstruction_recipe.v1"
        or document.get("schema_version") != recipe_v1.SCHEMA_VERSION
        or document.get("proposed_contract_version")
        != recipe_v1.PROPOSED_CONTRACT_VERSION
        or document.get("profile_key") != recipe_v1.PROFILE_KEY
        or type(inputs) is not dict
        or set(inputs) != expected_input_keys
        or inputs.get("constructor") != recipe_v1.REGISTERED_CONSTRUCTOR
        or inputs.get("verifier") != recipe_v1.REGISTERED_VERIFIER
        or inputs.get("max_workers") != recipe_v1.RECONSTRUCTION_MAX_WORKERS
        or inputs.get("registered_context_order")
        != list(source_campaign_v1.REGISTERED_CONTEXT_ORDER)
        or inputs.get("registered_context_documents")
        != [item.to_document() for item in registered_contexts]
        or inputs.get("registered_checkpoints")
        != list(source_campaign_v1.REGISTERED_CHECKPOINTS)
        or inputs.get("registered_adjacent_pairs")
        != expected_adjacent_pairs
        or inputs.get("discovery_draw_count")
        != acquisition_v1.DISCOVERY_DRAW_COUNT
        or inputs.get("randomness_implementation")
        != source_campaign_v1.RANDOMNESS_IMPLEMENTATION
        or type(output_ids) is not dict
        or set(output_ids) != expected_output_keys
        or type(commitments) is not dict
        or set(commitments) != expected_commitment_keys
        or type(artifacts) is not dict
        or set(artifacts) != expected_artifact_keys
        or type(document.get("source_graph_commitment_complete")) is not bool
        or document.get("replay_ready")
        is not document.get("source_graph_commitment_complete")
        or document.get("raw_observation_ids_persisted") is not False
        or document.get("caller_supplied_expected_ids_accepted") is not False
        or document.get("caller_supplied_runner_accepted") is not False
        or document.get("new_observer_draws") != 0
        or document.get("max_canonical_recipe_bytes")
        != recipe_v1.MAX_CANONICAL_RECIPE_BYTES
        or document.get("official_execution_allowed") is not False
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed source reconstruction recipe schema changed"
        )
    for field_name in (
        "component_tree_digest",
        "test_command_manifest_id",
        "runtime_dependency_lock_id",
        "interpreter_build_identity_id",
        "environment_independent_attestation_id",
    ):
        _cid(inputs[field_name], f"source recipe {field_name}")
    for field_name in expected_output_keys:
        _cid(output_ids[field_name], f"source recipe {field_name}")
    for name, expected_role in expected_commitment_roles.items():
        commitment = commitments[name]
        if (
            type(commitment) is not dict
            or set(commitment) != {
                "role",
                "count",
                "ordered_merkle_root",
            }
            or commitment.get("role") != expected_role
            or type(commitment.get("count")) is not int
            or commitment["count"] < 0
        ):
            raise IndependentRemoteMainAnchorVerificationViolation(
                f"source recipe {name} commitment changed"
            )
        _cid(
            commitment.get("ordered_merkle_root"),
            f"source recipe {name} Merkle root",
        )
    if commitments["archive_adjacent_pairs"]["count"] != 7:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "source recipe adjacent-pair commitment count changed"
        )
    for name in (
        "replayed_source_rows",
        "archive_trials",
        "archive_feature_consensus",
    ):
        if commitments[name]["count"] <= 0:
            raise IndependentRemoteMainAnchorVerificationViolation(
                f"source recipe {name} commitment is empty"
            )
    archive_document = artifacts["source_archive"]
    production_document = artifacts["production_archive_verification"]
    independent_document = artifacts["independent_archive_attestation"]
    component_document = artifacts["source_archive_component_summary"]
    if (
        type(archive_document) is not dict
        or type(production_document) is not dict
        or type(independent_document) is not dict
        or type(component_document) is not dict
        or archive_document.get("archive_id")
        != output_ids["source_archive_id"]
        or archive_document.get("source_campaign_id")
        != output_ids["source_campaign_id"]
        or archive_document.get("source_campaign_verification_id")
        != output_ids["source_campaign_verification_id"]
        or production_document.get("verification_id")
        != output_ids["production_archive_verification_id"]
        or production_document.get("archive_id")
        != output_ids["source_archive_id"]
        or production_document.get("replayed_archive_id")
        != output_ids["source_archive_id"]
        or independent_document.get("verification_id")
        != output_ids["independent_archive_attestation_id"]
        or independent_document.get("archive_id")
        != output_ids["source_archive_id"]
        or independent_document.get("independently_recomputed_archive_id")
        != output_ids["source_archive_id"]
        or component_document.get("component_id")
        != output_ids["source_archive_component_id"]
        or component_document.get("archive_id")
        != output_ids["source_archive_id"]
        or component_document.get("production_verification_id")
        != output_ids["production_archive_verification_id"]
        or component_document.get(
            "independent_archive_transform_attestation_id"
        )
        != output_ids["independent_archive_attestation_id"]
        or component_document.get("source_campaign_id")
        != output_ids["source_campaign_id"]
        or component_document.get("source_campaign_verification_id")
        != output_ids["source_campaign_verification_id"]
        or {
            "archive",
            "production_verification",
            "independent_attestation",
        }
        & set(component_document)
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "source recipe compact artifact identity graph does not close"
        )
    complete = document["source_graph_commitment_complete"]
    if (
        complete
        and document.get("replay_blocker") is not None
    ) or (
        not complete
        and document.get("replay_blocker") != recipe_v1.INCOMPLETE_BLOCKER
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed source recipe readiness/blocker is inconsistent"
        )
    if complete:
        if commitments["context_results"]["count"] != len(
            source_campaign_v1.REGISTERED_CONTEXT_ORDER
        ):
            raise IndependentRemoteMainAnchorVerificationViolation(
                "complete source recipe omits context-result commitments"
            )
        for field_name in (
            "family_manifest_id",
            "family_authority_id",
            "campaign_counters_id",
        ):
            _cid(
                commitments[field_name],
                f"source recipe {field_name}",
            )
    elif (
        commitments["context_results"]["count"] != 0
        or any(
            type(commitments[field_name]) is not dict
            or commitments[field_name].get("kind")
            != "NOT_AVAILABLE_IN_MECHANICS_FIXTURE"
            for field_name in (
                "family_manifest_id",
                "family_authority_id",
                "campaign_counters_id",
            )
        )
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "incomplete source recipe hides partial source evidence"
        )
    payload = {
        key: value for key, value in document.items() if key != "recipe_id"
    }
    recipe_id = _content_id(recipe_v1.RECIPE_DOMAIN, payload)
    if document.get("recipe_id") != recipe_id:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed source reconstruction recipe ID differs from its bytes"
        )
    return recipe_id


def _verify_final_preregistration_document_independently(
    document: dict[str, Any],
    manifest_id: str,
) -> str:
    draft_document = (
        prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        .to_document()
    )
    if (
        draft_document.pop("preregistration_id")
        != prereg.DRAFT_PREREGISTRATION_ID
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "draft preregistration authority changed"
        )
    draft_document["confirmatory_execution_manifest_id"] = manifest_id
    draft_document["confirmatory_profile_finalized"] = True
    draft_document["anchor_commit_id"] = None
    draft_document["target_execution_allowed"] = False
    expected_keys = {*draft_document, "preregistration_id"}
    if (
        set(document) != expected_keys
        or document.get("schema")
        != anchor_schema.FINAL_PREREGISTRATION_SCHEMA
        or {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        != draft_document
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed final preregistration changed the frozen profile"
        )
    final_id = _content_id(
        anchor_schema.FINAL_PREREGISTRATION_DOMAIN,
        draft_document,
    )
    if document.get("preregistration_id") != final_id:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed final preregistration ID differs from its bytes"
        )
    return final_id


def _verify_production_tree_authorities_from_clean_checkout_v1(
    root: Path,
    *,
    recipe_document: dict[str, Any],
    manifest_document: dict[str, Any],
) -> None:
    """Rebuild byte-bound authorities from the clean anchor checkout.

    Recipe/manifest cross references alone cannot prove that their claimed
    component-tree digest describes the committed implementation.  Production
    scope has already established that ``root`` is a clean checkout of the
    exact ``HEAD == main == origin/main`` anchor commit, so the independent
    verifier can safely rebuild the registry and execution-environment
    authorities from those committed bytes.
    """

    try:
        registry = manifest_v1.freeze_internal_component_registry_v1(root)
        environment = execution_env.freeze_v072_execution_environment_authorities_v1(
            root
        )
        environment_attestation = (
            execution_env_independent
            .verify_execution_environment_authorities_independently_v1(
                root,
                environment,
            )
        )
    except ValueError as error:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "production anchor component/environment authority replay failed"
        ) from error

    bindings = manifest_document["global_bindings"]
    inputs = recipe_document["reconstruction_inputs"]
    if (
        registry.missing_roles
        or manifest_document["component_registry_id"] != registry.registry_id
        or bindings["component_tree_digest"]
        != registry.component_tree_digest
        or inputs["component_tree_digest"]
        != registry.component_tree_digest
        or bindings["test_command_manifest_id"]
        != environment.test_command_manifest.test_command_manifest_id
        or inputs["test_command_manifest_id"]
        != environment.test_command_manifest.test_command_manifest_id
        or bindings["runtime_dependency_lock_id"]
        != environment.runtime_dependency_lock.runtime_dependency_lock_id
        or inputs["runtime_dependency_lock_id"]
        != environment.runtime_dependency_lock.runtime_dependency_lock_id
        or bindings["interpreter_build_identity_id"]
        != environment.interpreter_build_identity.interpreter_build_identity_id
        or inputs["interpreter_build_identity_id"]
        != environment.interpreter_build_identity.interpreter_build_identity_id
        or inputs["environment_independent_attestation_id"]
        != environment_attestation.attestation_id
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed recipe/manifest authorities do not match the "
            "independently rebuilt anchor checkout"
        )


def _local_bare_remote_path(repository_url: str) -> Path | None:
    parsed = urlparse(repository_url)
    if parsed.scheme == "file":
        if parsed.netloc not in ("", "localhost"):
            return None
        return Path(unquote(parsed.path))
    if parsed.scheme:
        return None
    candidate = Path(repository_url)
    return candidate if candidate.is_absolute() else None


def _verify_local_bare_remote_main(
    claim: anchor_schema.V072RemoteMainAnchorClaimV1,
) -> None:
    remote_path = _local_bare_remote_path(claim.repository_url)
    if remote_path is None:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "development scope requires one absolute local bare remote URL"
        )
    try:
        resolved = remote_path.resolve(strict=True)
    except FileNotFoundError as error:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "local bare remote no longer exists"
        ) from error
    if resolved != remote_path or not resolved.is_dir():
        raise IndependentRemoteMainAnchorVerificationViolation(
            "local bare remote path is noncanonical or symlinked"
        )
    try:
        result = subprocess.run(
            (
                "git",
                "--git-dir",
                os.fspath(resolved),
                "rev-parse",
                "--verify",
                "refs/heads/main^{commit}",
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "local bare remote main could not be replayed"
        ) from error
    if (
        result.returncode != 0
        or result.stdout.decode("ascii", errors="strict").strip()
        != claim.commit_id
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "local bare remote main does not equal the claimed commit"
        )


@dataclass(frozen=True, slots=True)
class IndependentRemoteMainAnchorAttestationV1:
    claim_id: str
    verification_scope: (
        anchor_schema.RemoteMainAnchorVerificationScopeV1
    )
    repository_url: str
    commit_id: str
    tree_id: str
    parent_commit_id: str
    source_reconstruction_recipe_blob_id: str
    manifest_blob_id: str
    final_preregistration_blob_id: str
    source_reconstruction_recipe_id: str
    manifest_id: str
    final_preregistration_id: str
    prior_history_commit_count: int
    clean_attached_main_verified: bool = True
    origin_main_verified: bool = True
    git_object_graph_verified: bool = True
    canonical_blob_triple_verified: bool = True
    first_qualifying_commit_verified: bool = True
    executable_anchor_minted: bool = False
    target_execution_allowed: bool = False
    registered_observer_calls: int = 0
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.claim_id, "anchor claim")
        _cid(
            self.source_reconstruction_recipe_id,
            "attested source reconstruction recipe",
        )
        _cid(self.manifest_id, "attested manifest")
        _cid(
            self.final_preregistration_id,
            "attested final preregistration",
        )
        if (
            type(self.verification_scope)
            is not anchor_schema.RemoteMainAnchorVerificationScopeV1
            or type(self.prior_history_commit_count) is not int
            or self.prior_history_commit_count < 1
            or self.clean_attached_main_verified is not True
            or self.origin_main_verified is not True
            or self.git_object_graph_verified is not True
            or self.canonical_blob_triple_verified is not True
            or self.first_qualifying_commit_verified is not True
            or self.executable_anchor_minted is not False
            or self.target_execution_allowed is not False
            or self.registered_observer_calls != 0
        ):
            raise IndependentRemoteMainAnchorVerificationViolation(
                "independent anchor attestation is malformed or authorizing"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_remote_main_anchor_independent_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "claim_id": self.claim_id,
            "verification_scope": self.verification_scope.value,
            "repository_url": self.repository_url,
            "target_branch": "main",
            "commit_id": self.commit_id,
            "tree_id": self.tree_id,
            "parent_commit_id": self.parent_commit_id,
            "source_reconstruction_recipe_repository_path": (
                anchor_schema
                .SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
            ),
            "source_reconstruction_recipe_blob_id": (
                self.source_reconstruction_recipe_blob_id
            ),
            "manifest_blob_id": self.manifest_blob_id,
            "final_preregistration_blob_id": (
                self.final_preregistration_blob_id
            ),
            "source_reconstruction_recipe_id": (
                self.source_reconstruction_recipe_id
            ),
            "manifest_id": self.manifest_id,
            "final_preregistration_id": self.final_preregistration_id,
            "prior_history_commit_count": self.prior_history_commit_count,
            "clean_attached_main_verified": True,
            "origin_main_verified": True,
            "git_object_graph_verified": True,
            "canonical_blob_triple_verified": True,
            "first_qualifying_commit_verified": True,
            "executable_anchor_minted": False,
            "target_execution_allowed": False,
            "registered_observer_calls": 0,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def verify_remote_main_anchor_claim_independently_v1(
    repository_root: str | os.PathLike[str],
    claim: anchor_schema.V072RemoteMainAnchorClaimV1,
) -> IndependentRemoteMainAnchorAttestationV1:
    """Replay one untrusted claim against local Git objects only."""

    if type(claim) is not anchor_schema.V072RemoteMainAnchorClaimV1:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "independent verifier requires the exact untrusted claim type"
        )
    root = _repository_root(repository_root)
    if Path(_git_text(root, "rev-parse", "--show-toplevel")) != root:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "claimed path is not the Git worktree root"
        )
    if _run_git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "dirty worktree cannot substitute bytes for the anchor commit"
        )
    if _git_text(root, "symbolic-ref", "--quiet", "HEAD") != "refs/heads/main":
        raise IndependentRemoteMainAnchorVerificationViolation(
            "anchor verification requires an attached local main branch"
        )
    origin_fetch_url = _git_text(root, "remote", "get-url", "origin")
    origin_push_url = _git_text(
        root,
        "remote",
        "get-url",
        "--push",
        "origin",
    )
    if (
        origin_fetch_url != claim.repository_url
        or origin_push_url != claim.repository_url
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "origin fetch/push URL differs from the anchor binding"
        )
    object_format = _git_text(root, "rev-parse", "--show-object-format")
    expected_object_length = {"sha1": 40, "sha256": 64}.get(object_format)
    if expected_object_length is None or any(
        len(value) != expected_object_length
        for value in (
            claim.commit_id,
            claim.tree_id,
            claim.parent_commit_id,
            claim.source_reconstruction_recipe_blob_id,
            claim.manifest_blob_id,
            claim.final_preregistration_blob_id,
        )
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "claim IDs do not match the repository object format"
        )
    for ref_name in (
        "HEAD",
        "refs/heads/main",
        "refs/remotes/origin/main",
    ):
        if (
            _git_text(
                root,
                "rev-parse",
                "--verify",
                f"{ref_name}^{{commit}}",
            )
            != claim.commit_id
        ):
            raise IndependentRemoteMainAnchorVerificationViolation(
                f"{ref_name} is stale, local-only, or not the anchor commit"
            )
    if (
        claim.verification_scope
        is (
            anchor_schema.RemoteMainAnchorVerificationScopeV1
            .REGISTERED_PRODUCTION_CANDIDATE
        )
        and claim.repository_url != manifest_v1.REPOSITORY_URL
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "production candidate uses the wrong frozen repository URL"
        )
    if (
        claim.verification_scope
        is (
            anchor_schema.RemoteMainAnchorVerificationScopeV1
            .DEVELOPMENT_LOCAL_BARE_REMOTE_NONAUTHORIZING
        )
    ):
        _verify_local_bare_remote_main(claim)
    if _git_text(root, "cat-file", "-t", claim.commit_id) != "commit":
        raise IndependentRemoteMainAnchorVerificationViolation(
            "anchor commit object is missing"
        )
    if (
        _git_text(root, "show", "-s", "--format=%T", claim.commit_id)
        != claim.tree_id
        or _git_text(root, "cat-file", "-t", claim.tree_id) != "tree"
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "anchor tree binding differs from the commit object"
        )
    parents = _git_text(
        root,
        "show",
        "-s",
        "--format=%P",
        claim.commit_id,
    ).split()
    if parents != [claim.parent_commit_id]:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "anchor must have exactly the claimed single parent"
        )
    for object_id in (claim.parent_commit_id,):
        if _git_text(root, "cat-file", "-t", object_id) != "commit":
            raise IndependentRemoteMainAnchorVerificationViolation(
                "anchor parent commit object is missing"
            )
    recipe_blob_id = _git_text(
        root,
        "rev-parse",
        (
            f"{claim.commit_id}:"
            f"{claim.source_reconstruction_recipe_repository_path}"
        ),
    )
    manifest_blob_id = _git_text(
        root,
        "rev-parse",
        f"{claim.commit_id}:{claim.manifest_repository_path}",
    )
    preregistration_blob_id = _git_text(
        root,
        "rev-parse",
        (
            f"{claim.commit_id}:"
            f"{claim.final_preregistration_repository_path}"
        ),
    )
    if (
        recipe_blob_id != claim.source_reconstruction_recipe_blob_id
        or manifest_blob_id != claim.manifest_blob_id
        or preregistration_blob_id != claim.final_preregistration_blob_id
        or _git_text(root, "cat-file", "-t", recipe_blob_id) != "blob"
        or _git_text(root, "cat-file", "-t", manifest_blob_id) != "blob"
        or _git_text(root, "cat-file", "-t", preregistration_blob_id)
        != "blob"
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed recipe/manifest/preregistration blob binding changed"
        )
    recipe_bytes = _run_git(
        root,
        "cat-file",
        "blob",
        recipe_blob_id,
    ).stdout
    if len(recipe_bytes) > recipe_v1.MAX_CANONICAL_RECIPE_BYTES:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "committed source reconstruction recipe exceeds its byte cap"
        )
    manifest_bytes = _run_git(
        root,
        "cat-file",
        "blob",
        manifest_blob_id,
    ).stdout
    final_preregistration_bytes = _run_git(
        root,
        "cat-file",
        "blob",
        preregistration_blob_id,
    ).stdout
    recipe_document = _parse_canonical_json_blob(
        recipe_bytes,
        "source reconstruction recipe",
    )
    manifest_document = _parse_canonical_json_blob(
        manifest_bytes,
        "execution manifest",
    )
    final_document = _parse_canonical_json_blob(
        final_preregistration_bytes,
        "final preregistration",
    )
    recipe_id = _verify_recipe_document_independently(recipe_document)
    manifest_id = _verify_manifest_document_independently(
        manifest_document
    )
    final_preregistration_id = (
        _verify_final_preregistration_document_independently(
            final_document,
            manifest_id,
        )
    )
    recipe_inputs = recipe_document["reconstruction_inputs"]
    recipe_outputs = recipe_document["expected_output_ids"]
    manifest_bindings = manifest_document["global_bindings"]
    if (
        recipe_id != claim.source_reconstruction_recipe_id
        or manifest_bindings["source_reconstruction_recipe_id"]
        != recipe_id
        or manifest_bindings[
            "source_reconstruction_recipe_repository_path"
        ]
        != claim.source_reconstruction_recipe_repository_path
        or recipe_inputs["component_tree_digest"]
        != manifest_bindings["component_tree_digest"]
        or recipe_inputs["test_command_manifest_id"]
        != manifest_bindings["test_command_manifest_id"]
        or recipe_inputs["runtime_dependency_lock_id"]
        != manifest_bindings["runtime_dependency_lock_id"]
        or recipe_inputs["interpreter_build_identity_id"]
        != manifest_bindings["interpreter_build_identity_id"]
        or recipe_outputs["source_archive_id"]
        != manifest_bindings["source_archive_id"]
        or recipe_outputs["independent_archive_attestation_id"]
        != manifest_bindings[
            "source_archive_verification_attestation_id"
        ]
        or manifest_id != claim.manifest_id
        or final_preregistration_id != claim.final_preregistration_id
        or final_preregistration_id.encode("ascii") in manifest_bytes
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "anchor claim does not bind the committed recipe/manifest/"
            "preregistration triple"
        )
    if (
        claim.verification_scope
        is (
            anchor_schema.RemoteMainAnchorVerificationScopeV1
            .REGISTERED_PRODUCTION_CANDIDATE
        )
        and recipe_document["replay_ready"] is not True
    ):
        raise IndependentRemoteMainAnchorVerificationViolation(
            "production anchor candidate uses an incomplete source recipe"
        )
    if (
        claim.verification_scope
        is (
            anchor_schema.RemoteMainAnchorVerificationScopeV1
            .REGISTERED_PRODUCTION_CANDIDATE
        )
    ):
        _verify_production_tree_authorities_from_clean_checkout_v1(
            root,
            recipe_document=recipe_document,
            manifest_document=manifest_document,
        )
    parent_identity_hits: list[str] = []
    historical_identity_hits: list[str] = []
    for identity, label in (
        (recipe_id, "source reconstruction recipe"),
        (final_preregistration_id, "final preregistration"),
    ):
        parent_grep = _run_git(
            root,
            "grep",
            "-I",
            "-F",
            "-q",
            "-e",
            identity,
            claim.parent_commit_id,
            "--",
            accepted_return_codes=(0, 1),
        )
        if parent_grep.returncode == 0:
            parent_identity_hits.append(label)
        historical_changes = _git_text(
            root,
            "log",
            "--format=%H",
            "--fixed-strings",
            f"-S{identity}",
            claim.parent_commit_id,
            "--",
        )
        if historical_changes:
            historical_identity_hits.append(label)
    if parent_identity_hits or historical_identity_hits:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "anchor is not the first qualifying commit; parent contains IDs="
            + ",".join(parent_identity_hits)
            + "; ancestry previously added or removed IDs="
            + ",".join(historical_identity_hits)
        )
    history = tuple(
        item
        for item in _git_text(
            root,
            "rev-list",
            claim.parent_commit_id,
        ).splitlines()
        if item
    )
    if not history or history[0] != claim.parent_commit_id:
        raise IndependentRemoteMainAnchorVerificationViolation(
            "anchor ancestry could not be replayed"
        )
    return IndependentRemoteMainAnchorAttestationV1(
        claim.claim_id,
        claim.verification_scope,
        claim.repository_url,
        claim.commit_id,
        claim.tree_id,
        claim.parent_commit_id,
        claim.source_reconstruction_recipe_blob_id,
        claim.manifest_blob_id,
        claim.final_preregistration_blob_id,
        recipe_id,
        manifest_id,
        final_preregistration_id,
        len(history),
    )


__all__ = [
    "IndependentRemoteMainAnchorAttestationV1",
    "IndependentRemoteMainAnchorVerificationViolation",
    "PROFILE_KEY",
    "verify_remote_main_anchor_claim_independently_v1",
]
