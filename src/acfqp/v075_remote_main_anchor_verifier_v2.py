"""Independent Git-object verifier for the V0-075 V2 pre-open boundary.

This module intentionally does not import the manifest/preregistration
implementation.  It independently parses canonical JSON from Git blobs,
replays every content identity and semantic verifier, verifies the signed
final preregistration, and locates the first qualifying ``origin/main``
commit.  The resulting authority remains non-opening until the separately
versioned pre-open V2 migration is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import importlib
from pathlib import Path, PurePosixPath
import stat
import subprocess
from types import ModuleType
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_private_environment_generation_profile_v1 as generation
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.43.0"
PROFILE_KEY = "v075_independent_remote_main_anchor_verifier_v2"
MANIFEST_PROFILE_KEY = "v075_confirmatory_manifest_preregistration_v2"

REPOSITORY_URL = (
    "git@github.com:erzhu419/"
    "Auditable-Coarse-to-Fine-Quotient-Planning.git"
)
TARGET_BRANCH = "main"
REMOTE_TRACKING_REF = "refs/remotes/origin/main"
LOCAL_BRANCH_REF = "refs/heads/main"
MANIFEST_REPOSITORY_PATH = "specs/V075_CONFIRMATORY_EXECUTION_MANIFEST.json"
FINAL_PREREGISTRATION_REPOSITORY_PATH = "specs/V075_FINAL_PREREGISTRATION.json"
EXACT_TEST_COMMAND = (
    "python3",
    "-m",
    "pytest",
    "-q",
    "-s",
    "tests/test_v075_production_campaign_profile_v2.py",
    "tests/test_v075_campaign_authority_private_signer_runtime_v1.py",
    "tests/test_v075_production_semantic_authority_registry_v2.py",
    "tests/test_v075_tracked_source_authority_v1.py",
    "tests/test_v075_production_private_signer_runtime_v1.py",
    "tests/test_v075_occurrence_failure_lifecycle_authority_v1.py",
    "tests/test_v075_production_occurrence_plan_v1.py",
    "tests/test_v075_production_occurrence_ipc_v1.py",
    "tests/test_v075_batch_native_total_lift_authority_v1.py",
    "tests/test_v075_preopen_v2_authorities.py",
    "tests/test_v075_public_target_tape_namespace_v2.py",
    "tests/test_v075_public_runtime_namespace_v2.py",
    "tests/test_v075_production_occurrence_authority_v1.py",
    "tests/test_v075_production_campaign_reconciliation_v1.py",
    "tests/test_v075_production_complete_bundle_endpoint_v1.py",
    "tests/test_v075_production_campaign_runner_v1.py",
    "tests/test_v075_manifest_preregistration_remote_main_anchor_v2.py",
)
DETERMINISTIC_ENVIRONMENT = (
    {"name": "LC_ALL", "value": "C.UTF-8"},
    {"name": "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "value": "1"},
    {"name": "PYTHONDONTWRITEBYTECODE", "value": "1"},
    {"name": "PYTHONHASHSEED", "value": "0"},
    {"name": "TZ", "value": "UTC"},
)


# Independent duplicate.  A mismatch with the producing implementation is a
# hard failure tested before any artifact may qualify.
REQUIRED_COMPONENT_SPECS = (
    ("MANIFEST_AND_PREREGISTRATION_AUTHORITY_V2", "src/acfqp/v075_confirmatory_manifest_preregistration_v2.py"),
    ("HISTORICAL_MANIFEST_AUTHORITY_V1_DEPENDENCY", "src/acfqp/v075_confirmatory_manifest_preregistration_v1.py"),
    ("INDEPENDENT_REMOTE_MAIN_ANCHOR_VERIFIER_V2", "src/acfqp/v075_remote_main_anchor_verifier_v2.py"),
    ("PRODUCTION_SEMANTIC_AUTHORITY_REGISTRY_V2", "src/acfqp/v075_production_semantic_authority_registry_v2.py"),
    ("PRODUCTION_CAMPAIGN_PROFILE_V2", "src/acfqp/v075_production_campaign_profile_v2.py"),
    ("PRODUCTION_CAMPAIGN_PROFILE_V2_TEST", "tests/test_v075_production_campaign_profile_v2.py"),
    ("PUBLIC_TARGET_TAPE_NAMESPACE_V2", "src/acfqp/v075_public_target_tape_namespace_v2.py"),
    ("PUBLIC_TARGET_TAPE_NAMESPACE_V2_TEST", "tests/test_v075_public_target_tape_namespace_v2.py"),
    ("PUBLIC_RUNTIME_NAMESPACE_V2_TEST", "tests/test_v075_public_runtime_namespace_v2.py"),
    ("PRODUCTION_CAMPAIGN_RUNNER", "src/acfqp/v075_production_campaign_runner_v1.py"),
    ("PRODUCTION_CAMPAIGN_RUNNER_TEST", "tests/test_v075_production_campaign_runner_v1.py"),
    ("CAMPAIGN_AUTHORITY_PRIVATE_SIGNER_TEST", "tests/test_v075_campaign_authority_private_signer_runtime_v1.py"),
    ("PRODUCTION_SEMANTIC_AUTHORITY_REGISTRY_V2_TEST", "tests/test_v075_production_semantic_authority_registry_v2.py"),
    ("TRACKED_SOURCE_AUTHORITY_TEST", "tests/test_v075_tracked_source_authority_v1.py"),
    ("OBSERVER_PRIVATE_SIGNER_RUNTIME_TEST", "tests/test_v075_production_private_signer_runtime_v1.py"),
    ("OCCURRENCE_FAILURE_LIFECYCLE_AUTHORITY_TEST", "tests/test_v075_occurrence_failure_lifecycle_authority_v1.py"),
    ("PRODUCTION_OCCURRENCE_PLAN_TEST", "tests/test_v075_production_occurrence_plan_v1.py"),
    ("PRODUCTION_OCCURRENCE_IPC_TEST", "tests/test_v075_production_occurrence_ipc_v1.py"),
    ("BATCH_NATIVE_TOTAL_LIFT_AUTHORITY_TEST", "tests/test_v075_batch_native_total_lift_authority_v1.py"),
    ("PREOPEN_V2_AUTHORITIES_TEST", "tests/test_v075_preopen_v2_authorities.py"),
    ("PRODUCTION_OCCURRENCE_AUTHORITY_TEST", "tests/test_v075_production_occurrence_authority_v1.py"),
    ("PRODUCTION_CAMPAIGN_RECONCILIATION_TEST", "tests/test_v075_production_campaign_reconciliation_v1.py"),
    ("PRODUCTION_COMPLETE_BUNDLE_ENDPOINT_TEST", "tests/test_v075_production_complete_bundle_endpoint_v1.py"),
    ("MANIFEST_REMOTE_MAIN_ANCHOR_V2_TEST", "tests/test_v075_manifest_preregistration_remote_main_anchor_v2.py"),
    ("BATCH_NATIVE_STATISTICAL_BACKEND_TEST_DEPENDENCY", "tests/test_v075_batch_native_statistical_backend_v1.py"),
    ("BATCH_NATIVE_TOTAL_LIFT_E2E_TEST_DEPENDENCY", "tests/test_v075_batch_native_total_lift_e2e_v1.py"),
    ("BATCHED_OBSERVER_AUTHORITY_TEST_DEPENDENCY", "tests/test_v075_batched_observer_authority_v1.py"),
    ("INTEGRATED_DIRECT_OCCURRENCE_PIPELINE_TEST_DEPENDENCY", "tests/test_v075_integrated_direct_occurrence_pipeline_v1.py"),
    ("INTEGRATED_OCCURRENCE_PIPELINE_TEST_DEPENDENCY", "tests/test_v075_integrated_occurrence_pipeline_v1.py"),
    ("PRIVATE_OBSERVER_BOUNDARY_TEST_DEPENDENCY", "tests/test_v075_private_observer_boundary_v1.py"),
    ("PREOPEN_TARGET_AUTHORIZATION_TEST_DEPENDENCY", "tests/test_v075_preopen_target_authorization_v1.py"),
    ("TOTAL_LIFT_AUTHORITY_TEST_DEPENDENCY", "tests/test_v075_total_lift_authority_v1.py"),
    ("SIGNATURE_TEST_SUPPORT", "tests/v075_signature_test_support.py"),
    ("PHASE3E_CANONICAL_IDENTITY", "src/acfqp/phase3e_ids.py"),
    ("ACFQP_PACKAGE_INIT", "src/acfqp/__init__.py"),
    ("PUBLIC_CAMPAIGN_AUTHORITY", "src/acfqp/v075_public_campaign_authority_v1.py"),
    ("PUBLIC_GRAPH_SEMANTICS", "src/acfqp/v075_public_graph_semantics_v1.py"),
    ("PRIVATE_ENVIRONMENT_GENERATION_PROFILE", "src/acfqp/v075_private_environment_generation_profile_v1.py"),
    ("PRODUCTION_PRIVATE_SIGNER_RUNTIME", "src/acfqp/v075_production_private_signer_runtime_v1.py"),
    ("CAMPAIGN_AUTHORITY_PRIVATE_SIGNER_RUNTIME", "src/acfqp/v075_campaign_authority_private_signer_runtime_v1.py"),
    ("PREOPEN_TARGET_AUTHORIZATION", "src/acfqp/v075_preopen_target_authorization_v1.py"),
    ("REVEAL_VERIFYING_ATTESTATION_AUTHORITY_V2", "src/acfqp/v075_reveal_verifying_attestation_authority_v2.py"),
    ("PREOPEN_TARGET_AUTHORIZATION_V2", "src/acfqp/v075_preopen_target_authorization_v2.py"),
    ("HISTORICAL_REMOTE_ANCHOR_V1_DEPENDENCY", "src/acfqp/v075_remote_main_anchor_verifier_v1.py"),
    ("REVEAL_VERIFYING_ATTESTATION_AUTHORITY", "src/acfqp/v075_reveal_verifying_attestation_authority_v1.py"),
    ("PRIVATE_OBSERVER_BOUNDARY", "src/acfqp/v075_private_observer_boundary_v1.py"),
    ("BATCHED_OBSERVER_AUTHORITY", "src/acfqp/v075_batched_observer_authority_v1.py"),
    ("MULTISTAGE_OBSERVER_LIFECYCLE", "src/acfqp/v075_multistage_observer_lifecycle_v1.py"),
    ("OCCURRENCE_FAILURE_LIFECYCLE_AUTHORITY", "src/acfqp/v075_occurrence_failure_lifecycle_authority_v1.py"),
    ("PRODUCTION_OCCURRENCE_PLAN", "src/acfqp/v075_production_occurrence_plan_v1.py"),
    ("PRODUCTION_OCCURRENCE_IPC", "src/acfqp/v075_production_occurrence_ipc_v1.py"),
    ("OPERATIONAL_PLANNER_TRANSPORT", "src/acfqp/v075_operational_planner_transport_v1.py"),
    ("PRODUCTION_OCCURRENCE_AUTHORITY", "src/acfqp/v075_production_occurrence_authority_v1.py"),
    ("PRODUCTION_CAMPAIGN_RECONCILIATION", "src/acfqp/v075_production_campaign_reconciliation_v1.py"),
    ("PRODUCTION_COMPLETE_BUNDLE_ENDPOINT", "src/acfqp/v075_production_complete_bundle_endpoint_v1.py"),
    ("OCCURRENCE_CAS_TRANSPORT", "src/acfqp/v075_occurrence_cas_transport_v1.py"),
    ("REGISTERED_OCCURRENCE_WORKER", "src/acfqp/v075_registered_occurrence_worker_v1.py"),
    ("ROUTE_NATIVE_BACKEND_CORE", "src/acfqp/v075_route_native_backend_core_v1.py"),
    ("BATCH_NATIVE_STATISTICAL_BACKEND", "src/acfqp/v075_batch_native_statistical_backend_v1.py"),
    ("LEARNED_SUPPORT_QUOTIENT_PLANNERS", "src/acfqp/v075_learned_support_quotient_planners_v1.py"),
    ("BATCH_NATIVE_TOTAL_LIFT_AUTHORITY", "src/acfqp/v075_batch_native_total_lift_authority_v1.py"),
    ("TOTAL_LIFT_AUTHORITY", "src/acfqp/v075_total_lift_authority_v1.py"),
    ("INTEGRATED_OCCURRENCE_PIPELINE", "src/acfqp/v075_integrated_occurrence_pipeline_v1.py"),
    ("INTEGRATED_DIRECT_OCCURRENCE_PIPELINE", "src/acfqp/v075_integrated_direct_occurrence_pipeline_v1.py"),
    ("ADAPTIVE_ACQUISITION_PROPOSAL_AUTHORITY", "src/acfqp/v075_adaptive_acquisition_proposal_authority_v1.py"),
    ("ADAPTIVE_ACQUISITION_ROUND_BUNDLE_AUTHORITY", "src/acfqp/v075_adaptive_acquisition_round_bundle_authority_v1.py"),
    ("FROZEN_SOURCE_PROPOSAL_ARCHIVE", "src/acfqp/v075_frozen_source_proposal_archive_v1.py"),
    ("SOURCE_PRIOR_ADAPTER", "src/acfqp/v075_source_prior_adapter_v1.py"),
    ("SOURCE_OFFLINE_WORK_MATERIALIZER", "src/acfqp/v075_source_offline_work_materializer_v1.py"),
    ("PUBLIC_SOURCE_WORK_AUTHORITY", "src/acfqp/v075_public_source_work_authority_v1.py"),
    ("TRACKED_SOURCE_AUTHORITY", "src/acfqp/v075_tracked_source_authority_v1.py"),
    ("SOURCE_REPLAY_CONTROLLER", "scripts/replay_and_materialize_v075_source_work.py"),
    ("SOURCE_COMPILATION_CONTROLLER", "scripts/compile_v075_public_source_artifacts.py"),
    ("H2_GRAPH_TRANSITION_ENGINE", "src/acfqp/h2_graph_transition_engine_v1.py"),
    ("RELATIONAL_GRAPH_CORE", "src/acfqp/relational_graph_core_v1.py"),
    ("PARTIAL_SUPPORT_CONFIDENCE", "src/acfqp/partial_support_confidence_v1.py"),
    ("SEQUENTIAL_BERNOULLI_ACQUISITION", "src/acfqp/sequential_bernoulli_acquisition_v1.py"),
    ("OBSERVATION_SUPPORT_GRAPH_ACQUISITION", "src/acfqp/observation_support_graph_acquisition_v1.py"),
    ("OBSERVATION_SUPPORT_CAMPAIGN", "src/acfqp/observation_support_campaign_v1.py"),
    ("OBSERVATION_SUPPORT_COORDINATE_REFINEMENT", "src/acfqp/observation_support_coordinate_refinement_v1.py"),
    ("OBSERVATION_SUPPORT_EXACT_EVALUATION", "src/acfqp/observation_support_exact_evaluation_v1.py"),
    ("OBSERVATION_SUPPORT_GRAPH_MODEL", "src/acfqp/observation_support_graph_model_v1.py"),
    ("OBSERVATION_SUPPORT_GROUPED_REPLAY", "src/acfqp/observation_support_grouped_replay_v1.py"),
    ("OBSERVATION_SUPPORT_H2_CLOSURE", "src/acfqp/observation_support_h2_closure_v1.py"),
    ("OBSERVATION_SUPPORT_PROMOTED_H2_CONSUMER", "src/acfqp/observation_support_promoted_h2_consumer_v1.py"),
    ("OBSERVATION_SUPPORT_RELATIONAL_ADAPTER", "src/acfqp/observation_support_relational_adapter_v1.py"),
    ("PARTIAL_SUPPORT_EXPANSION_AUTHORITY", "src/acfqp/partial_support_expansion_authority_v1.py"),
    ("PARTIAL_SUPPORT_FAMILY_CONFIDENCE", "src/acfqp/partial_support_family_confidence_v1.py"),
    ("PARTIAL_SUPPORT_ROBUST_PLANNER", "src/acfqp/partial_support_robust_planner_v1.py"),
    ("TRANSITION_TUPLE_OBSERVER", "src/acfqp/transition_tuple_observer_v1.py"),
    ("TRANSFER_GUIDED_ACQUISITION_PREREGISTRATION", "src/acfqp/transfer_guided_acquisition_preregistration_v1.py"),
    ("VERIFIED_SOURCE_ARCHIVE", "src/acfqp/verified_source_acquisition_archive_v2.py"),
    ("VERIFIED_SOURCE_ARCHIVE_INDEPENDENT_VERIFIER", "src/acfqp/verified_source_acquisition_archive_independent_verifier_v2.py"),
    ("V072_SOURCE_RECONSTRUCTION_RECIPE", "src/acfqp/v072_source_reconstruction_recipe_v1.py"),
    ("V072_VERIFIED_SOURCE_ARCHIVE_COMPONENT", "src/acfqp/v072_verified_source_archive_component_v1.py"),
    ("V072_EXECUTION_ENVIRONMENT_AUTHORITY", "src/acfqp/v072_execution_environment_authority_v1.py"),
    ("V072_EXECUTION_ENVIRONMENT_INDEPENDENT_VERIFIER", "src/acfqp/v072_execution_environment_independent_verifier_v1.py"),
    ("V072_CONFIRMATORY_EXECUTION_MANIFEST", "src/acfqp/v072_confirmatory_execution_manifest_v1.py"),
    ("V072_SOURCE_RECONSTRUCTION_RECIPE_ARTIFACT", "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"),
    ("RUNTIME_DEPENDENCY_LOCK", "specs/V075_DEPENDENCY_LOCK.json"),
    ("FROZEN_SOURCE_ARCHIVE_ARTIFACT", "specs/V075_FROZEN_SOURCE_PROPOSAL_ARCHIVE.json"),
    ("FROZEN_SOURCE_ARCHIVE_VERIFICATION", "specs/V075_FROZEN_SOURCE_PROPOSAL_ARCHIVE_VERIFICATION.json"),
    ("SOURCE_PRIOR_ADAPTER_ARTIFACT", "specs/V075_SOURCE_PRIOR_ADAPTER.json"),
    ("SOURCE_PRIOR_ADAPTER_VERIFICATION", "specs/V075_SOURCE_PRIOR_ADAPTER_VERIFICATION.json"),
    ("SOURCE_OFFLINE_WORK_ARTIFACT", "specs/V075_SOURCE_OFFLINE_WORK_MATERIALIZATION.json"),
    ("SOURCE_OFFLINE_WORK_VERIFICATION", "specs/V075_SOURCE_OFFLINE_WORK_MATERIALIZATION_VERIFICATION.json"),
    ("VERIFIED_PUBLIC_SOURCE_WORK_BUNDLE", "specs/V075_VERIFIED_PUBLIC_SOURCE_WORK_BUNDLE.json"),
    ("SOURCE_REPLAY_MATERIALIZATION_STATUS", "specs/V075_SOURCE_REPLAY_MATERIALIZATION_STATUS.json"),
    ("PROJECT_BUILD_METADATA", "pyproject.toml"),
)

if (
    len(REQUIRED_COMPONENT_SPECS)
    != len({role for role, _path in REQUIRED_COMPONENT_SPECS})
    or len(REQUIRED_COMPONENT_SPECS)
    != len({path for _role, path in REQUIRED_COMPONENT_SPECS})
):
    raise RuntimeError("independent V0-075 V2 component registry overlaps")


DOMAIN_TAGS = {
    "component_blob": "acfqp:v075-manifest-component-blob:v2",
    "component_registry": "acfqp:v075-manifest-component-registry:v2",
    "semantic_binding": "acfqp:v075-manifest-semantic-binding:v2",
    "semantic_registry": "acfqp:v075-manifest-semantic-registry:v2",
    "semantic_artifact_replay": (
        "acfqp:v075-manifest-semantic-artifact-replay:v2"
    ),
    "workload": "acfqp:v075-confirmatory-public-workload:v2",
    "manifest": "acfqp:v075-confirmatory-execution-manifest:v2",
    "final_preregistration": "acfqp:v075-final-preregistration:v2",
    "anchor": "acfqp:v075-independent-remote-main-anchor:v2",
}
RUNNER_PROFILE_DOMAIN = (
    "acfqp:v075-production-campaign-runner-profile:v2"
)
FINAL_SIGNING_DOMAIN = b"acfqp:v075-final-preregistration-signing:v2"


class V075RemoteMainAnchorV2InvariantViolation(ValueError):
    """A tracked blob, semantic replay, signature, or identity failed."""


class V075RemoteMainAnchorV2NotReady(RuntimeError):
    """No complete first-qualifying origin/main authority exists."""


def _fail(message: str) -> None:
    raise V075RemoteMainAnchorV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075RemoteMainAnchorV2InvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075RemoteMainAnchorV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _oid(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) not in (40, 64)
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field_name} must be one full lowercase Git object ID")
    return value


def _strict(value: Any, *, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} field set changed")
    try:
        canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise V075RemoteMainAnchorV2InvariantViolation(
            f"{label} is outside canonical JSON"
        ) from error
    return value


def _parse(raw: bytes, *, keys: set[str], label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > 32 * 1024 * 1024:
        _fail(f"{label} bytes are empty, mistyped, or over cap")
    try:
        value = loads_canonical_json(raw)
    except (Phase3EIdentityError, ValueError) as error:
        raise V075RemoteMainAnchorV2InvariantViolation(
            f"{label} is not canonical JSON"
        ) from error
    return _strict(value, keys=keys, label=label)


def _git(root: Path, *arguments: str) -> str:
    process = subprocess.run(
        ("git", "-C", str(root), *arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if process.returncode:
        raise V075RemoteMainAnchorV2NotReady(
            process.stderr.decode("utf-8", errors="replace").strip()
        )
    return process.stdout.decode("utf-8").strip()


def _read_blob(root: Path, commit_id: str, path: str) -> bytes | None:
    process = subprocess.run(
        ("git", "-C", str(root), "show", f"{commit_id}:{path}"),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if process.returncode:
        return None
    return process.stdout


def _tree_blob(
    root: Path,
    commit_id: str,
    path: str,
) -> tuple[str, str]:
    if (
        type(path) is not str
        or path.startswith("/")
        or "\\" in path
        or ".." in PurePosixPath(path).parts
    ):
        _fail("component path is unsafe")
    listing = _git(root, "ls-tree", commit_id, "--", path).splitlines()
    if len(listing) != 1 or "\t" not in listing[0]:
        _fail("component tree entry is absent or ambiguous")
    prefix, tree_path = listing[0].split("\t", 1)
    fields = prefix.split()
    if (
        tree_path != path
        or len(fields) != 3
        or fields[1] != "blob"
        or fields[0] not in {"100644", "100755"}
    ):
        _fail("component tree entry is not one regular blob")
    return _oid(fields[2], "component tree blob"), fields[0]


_COMPONENT_KEYS = {
    "schema", "schema_version", "role", "repository_path", "git_blob_id",
    "bytes_sha256", "byte_count", "executable",
    "worktree_bytes_equal_index_blob", "target_accessed", "component_id",
}


def _verify_components(
    root: Path,
    commit_id: str,
    value: Any,
) -> tuple[list[dict[str, Any]], str]:
    if type(value) is not list or len(value) != len(REQUIRED_COMPONENT_SPECS):
        _fail("component registry is incomplete")
    documents: list[dict[str, Any]] = []
    ids: list[str] = []
    for raw, (role, path) in zip(
        value, REQUIRED_COMPONENT_SPECS, strict=True
    ):
        item = _strict(raw, keys=_COMPONENT_KEYS, label="component")
        payload = dict(item)
        component_id = _cid(payload.pop("component_id"), "component")
        blob_id, mode = _tree_blob(root, commit_id, path)
        blob = _read_blob(root, commit_id, path)
        if (
            blob is None
            or item["schema"] != "acfqp.v075_manifest_component_blob.v2"
            or item["schema_version"] != SCHEMA_VERSION
            or item["role"] != role
            or item["repository_path"] != path
            or item["git_blob_id"] != blob_id
            or item["bytes_sha256"] != hashlib.sha256(blob).hexdigest()
            or item["byte_count"] != len(blob)
            or item["executable"] is not (mode == "100755")
            or item["worktree_bytes_equal_index_blob"] is not True
            or item["target_accessed"] is not False
            or _hash("component_blob", payload) != component_id
        ):
            _fail(f"component blob binding failed: {role}")
        documents.append(item)
        ids.append(component_id)
    if len(set(ids)) != len(ids):
        _fail("component identities alias")
    return documents, _hash(
        "component_registry", {"component_blobs": documents}
    )


def _expected_workload() -> dict[str, Any]:
    family = public.freeze_v075_public_family_generation_v1()
    profile = (
        generation.freeze_v075_private_environment_generation_profile_v1()
    )
    registry = worker.freeze_v075_worker_registry_draft_v1()
    threshold = worker.V075WorkerThresholdProfileV1()
    caps = worker.V075WorkerCapProfileV1()
    runner_payload = {
        "schema": "acfqp.v075_production_campaign_runner_profile.v2",
        "schema_version": "2.0.0",
        "proposed_contract_version": "1.45.0",
        "profile_key": "v075_production_campaign_profile_v2",
        "logical_occurrence_count": 15,
        "max_workers": 15,
        "executor": "THREAD_POOL_OVER_ISOLATED_OCCURRENCE_IPC",
        "parallelism_axis": "LOGICAL_OCCURRENCE_ONLY",
        "one_fresh_ipc_child_per_occurrence": True,
        "intra_occurrence_parallelism_allowed": False,
        "result_order": "IMMUTABLE_SCIENTIFIC_ORDER",
        "scientific_ordinals": list(range(15)),
        "transport_ordinals": list(range(1, 16)),
        "per_occurrence_algorithm_changed": False,
        "accuracy_reduction_allowed": False,
        "statistical_threshold_reduction_allowed": False,
        "draw_cap_reduction_allowed": False,
        "evidence_omission_allowed": False,
        "final_preregistration_binding_required": True,
        "target_execution_opened": False,
        "target_accessed": False,
        "official_execution_allowed": False,
    }
    runner_profile = {
        **runner_payload,
        "profile_id": hashlib.sha256(
            RUNNER_PROFILE_DOMAIN.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(runner_payload)
        ).hexdigest(),
    }
    payload = {
        "schema": "acfqp.v075_confirmatory_public_workload.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": MANIFEST_PROFILE_KEY,
        "family_generation": family.to_document(),
        "family_generation_id": family.generation_id,
        "context_ids": [
            item.context_id for item in family.replicate_contexts
        ],
        "context_count": 3,
        "arm_order": list(public.ARM_ORDER),
        "arm_count": 5,
        "logical_occurrence_denominator": 15,
        "occurrence_order": "CONTEXT_MAJOR_THEN_FROZEN_ARM_ORDER",
        "scientific_ordinals": list(range(15)),
        "transport_ordinals": list(range(1, 16)),
        "private_environment_generation_profile": profile.to_document(),
        "private_environment_generation_profile_id": profile.profile_id,
        "worker_registry": registry.to_document(),
        "worker_registry_id": registry.registry_id,
        "threshold_profile": threshold.to_document(),
        "threshold_profile_id": threshold.threshold_profile_id,
        "cap_profile": caps.to_document(),
        "cap_profile_id": caps.cap_profile_id,
        "runner_profile": runner_profile,
        "runner_profile_id": runner_profile["profile_id"],
        "target_law_serialized": False,
        "target_tape_serialized": False,
        "target_accessed": False,
        "target_execution_allowed": False,
    }
    document = {**payload, "workload_id": _hash("workload", payload)}
    normalized = loads_canonical_json(canonical_json_bytes(document))
    if type(normalized) is not dict:
        _fail("independent workload normalization failed")
    return normalized


_SEMANTIC_BINDING_KEYS = {
    "schema", "schema_version", "ordinal", "role", "producer_module",
    "verifier_module",
    "verifier_function", "artifact_schemas", "artifact_domains",
    "prerequisite_roles", "role_spec_id", "producer_component_id",
    "verifier_component_id",
    "semantic_verifier_callable_verified", "string_status_sufficient",
    "target_accessed", "binding_id",
}
_SEMANTIC_REGISTRY_BINDING_KEYS = {
    "schema", "schema_version", "authority_registry_id",
    "authority_registry_verification_id", "authority_registry_document",
    "authority_registry_verification_document",
    "artifact_semantic_replay_document", "artifact_semantic_replay_id",
    "role_bindings", "role_count",
    "every_role_has_distinct_semantic_verifier", "string_status_sufficient",
    "target_accessed", "binding_id",
}


def _verify_executed_module_blobs(
    *,
    roots: tuple[ModuleType, ...],
    components: list[dict[str, Any]],
) -> None:
    by_path = {
        item["repository_path"]: item for item in components
    }
    queue = list(roots)
    seen: set[str] = set()
    while queue:
        module = queue.pop()
        name = getattr(module, "__name__", None)
        if type(name) is not str or not name.startswith("acfqp"):
            continue
        if name in seen:
            continue
        seen.add(name)
        expected_path = (
            "src/acfqp/__init__.py"
            if name == "acfqp"
            else "src/" + name.replace(".", "/") + ".py"
        )
        component = by_path.get(expected_path)
        source_path = getattr(module, "__file__", None)
        if (
            component is None
            or type(source_path) is not str
            or not source_path.endswith(".py")
        ):
            _fail(
                f"executed semantic module is not component-bound: {name}"
            )
        try:
            digest = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
        except OSError as error:
            raise V075RemoteMainAnchorV2InvariantViolation(
                "executed semantic module source is unreadable"
            ) from error
        if digest != component["bytes_sha256"]:
            _fail(
                "executed semantic module differs from anchor blob: "
                f"{name}"
            )
        queue.extend(
            value
            for value in vars(module).values()
            if isinstance(value, ModuleType)
            and getattr(value, "__name__", "").startswith("acfqp")
        )


def _verify_semantic_registry(
    root: Path,
    commit_id: str,
    components: list[dict[str, Any]],
    value: Any,
) -> tuple[dict[str, Any], str, str]:
    item = _strict(
        value,
        keys=_SEMANTIC_REGISTRY_BINDING_KEYS,
        label="semantic registry binding",
    )
    try:
        module = importlib.import_module(
            "acfqp.v075_production_semantic_authority_registry_v2"
        )
        registry = (
            module.freeze_v075_production_semantic_authority_registry_v2()
        )
        audit = (
            module.verify_v075_production_semantic_authority_registry_v2(
                registry,
                package_root=root / "src" / "acfqp",
            )
        )
    except (ImportError, AttributeError, TypeError, ValueError) as error:
        raise V075RemoteMainAnchorV2InvariantViolation(
            "independent semantic verifier replay failed"
        ) from error
    registry_document = registry.to_document()
    audit_document = audit.to_document()
    role_bindings = item["role_bindings"]
    if (
        type(role_bindings) is not list
        or len(role_bindings) != len(registry.role_specs)
        or item["schema"]
        != "acfqp.v075_manifest_semantic_registry_binding.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["authority_registry_id"] != registry.registry_id
        or item["authority_registry_verification_id"]
        != audit.verification_id
        or item["authority_registry_document"] != registry_document
        or item["authority_registry_verification_document"]
        != audit_document
        or item["role_count"] != len(registry.role_specs)
        or item["every_role_has_distinct_semantic_verifier"] is not True
        or item["string_status_sufficient"] is not False
        or item["target_accessed"] is not False
        or getattr(
            module,
            "ARTIFACT_SEMANTIC_ATTESTATION_ALLOWED",
            None,
        )
        is not False
    ):
        _fail("semantic authority registry differs from independent replay")
    component_by_path = {
        component["repository_path"]: component
        for component in components
    }
    verifier_path = (
        "src/acfqp/v075_production_semantic_authority_registry_v2.py"
    )
    verifier_component = component_by_path.get(verifier_path)
    if verifier_component is None:
        _fail("semantic verifier implementation is not component-bound")
    seen_roles: set[str] = set()
    seen_dispatches: set[str] = set()
    binding_documents: list[dict[str, Any]] = []
    for ordinal, (raw, spec, record) in enumerate(
        zip(role_bindings, registry.role_specs, audit.role_records, strict=True)
    ):
        binding = _strict(
            raw,
            keys=_SEMANTIC_BINDING_KEYS,
            label="semantic role binding",
        )
        payload = dict(binding)
        binding_id = _cid(payload.pop("binding_id"), "semantic binding")
        module_name = spec.semantic_verifier_module
        dispatch_id = spec.semantic_verifier_id
        producer_module = spec.producer_module
        producer_path = (
            "src/" + producer_module.replace(".", "/") + ".py"
        )
        producer_component = component_by_path.get(producer_path)
        spec_document = spec.to_document()
        try:
            dispatcher = getattr(
                module,
                "verify_v075_production_semantic_authority_registry_v2",
            )
            verifier = module._SEMANTIC_VERIFIER_FUNCTIONS.get(  # noqa: SLF001
                dispatch_id
            )
        except AttributeError as error:
            raise V075RemoteMainAnchorV2InvariantViolation(
                "semantic dispatcher surface is absent"
            ) from error
        expected_prerequisites = [
            role.value for role in spec.prerequisite_roles
        ]
        if (
            not callable(dispatcher)
            or not callable(verifier)
            or record.role is not spec.role
            or producer_component is None
            or spec_document.get("producer_module") != producer_module
            or spec_document.get("implementation_repository_path")
            != producer_path
            or binding["schema"]
            != "acfqp.v075_manifest_semantic_binding.v2"
            or binding["schema_version"] != SCHEMA_VERSION
            or binding["ordinal"] != ordinal
            or binding["role"] != spec.role.value
            or binding["producer_module"] != producer_module
            or binding["verifier_module"] != module_name
            or binding["verifier_function"] != dispatch_id
            or binding["artifact_schemas"] != list(spec.artifact_schemas)
            or binding["artifact_domains"] != list(spec.artifact_domains)
            or binding["prerequisite_roles"] != expected_prerequisites
            or binding["role_spec_id"] != spec.spec_id
            or binding["producer_component_id"]
            != producer_component["component_id"]
            or binding["verifier_component_id"]
            != verifier_component["component_id"]
            or binding["producer_component_id"]
            == binding["verifier_component_id"]
            or binding["semantic_verifier_callable_verified"] is not True
            or binding["string_status_sufficient"] is not False
            or binding["target_accessed"] is not False
            or _hash("semantic_binding", payload) != binding_id
        ):
            _fail("semantic role binding failed independent replay")
        if binding["role"] in seen_roles or dispatch_id in seen_dispatches:
            _fail("semantic role or dispatcher is reused")
        seen_roles.add(binding["role"])
        seen_dispatches.add(dispatch_id)
        binding_documents.append(binding)
    payload = dict(item)
    binding_id = _cid(
        payload.pop("binding_id"),
        "semantic registry binding",
    )
    if _hash("semantic_registry", payload) != binding_id:
        _fail("semantic registry binding identity is invalid")
    replay = item["artifact_semantic_replay_document"]
    if type(replay) is not dict:
        _fail("semantic artifact replay document is absent")
    replay_payload = dict(replay)
    replay_id = _cid(
        replay_payload.pop("artifact_semantic_replay_id", None),
        "semantic artifact replay",
    )
    try:
        legacy_independent = importlib.import_module(
            "acfqp.v075_remote_main_anchor_verifier_v1"
        )
        tracked_source = importlib.import_module(
            "acfqp.v075_tracked_source_authority_v1"
        )
        dependency = legacy_independent._verify_dependency_lock_at_commit(  # noqa: SLF001
            root,
            commit_id,
        )
        source_bundle, source_verification = (
            tracked_source.verify_tracked_v075_source_authorities_v1(root)
        )
    except (
        AttributeError,
        ImportError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        raise V075RemoteMainAnchorV2InvariantViolation(
            "serialized pretarget artifact semantic replay failed"
        ) from error
    expected_replay_payload = {
        "schema": "acfqp.v075_manifest_semantic_artifact_replay.v2",
        "schema_version": SCHEMA_VERSION,
        "dependency_lock_id": dependency[0],
        "dependency_lock_verification_id": dependency[1],
        "dependency_lock_canonical_sha256": dependency[2],
        "dependency_verifier_module": (
            "acfqp.v075_remote_main_anchor_verifier_v1"
        ),
        "dependency_verifier_function": (
            "_verify_dependency_lock_at_commit"
        ),
        "tracked_source_bundle": source_bundle.to_document(),
        "tracked_source_bundle_id": source_bundle.bundle_id,
        "tracked_source_verification": source_verification.to_document(),
        "tracked_source_verification_id": (
            source_verification.verification_id
        ),
        "tracked_source_verifier_module": (
            "acfqp.v075_tracked_source_authority_v1"
        ),
        "tracked_source_verifier_function": (
            "verify_tracked_v075_source_authorities_v1"
        ),
        "serialized_artifact_roles": [
            "DEPENDENCY_LOCK",
            "SOURCE_ARCHIVE",
            "SOURCE_ARCHIVE_VERIFICATION",
            "SOURCE_WORK",
            "SOURCE_WORK_VERIFICATION",
            "SOURCE_REPLAY_STATUS",
            "PUBLIC_SOURCE_WORK_BUNDLE",
            "SOURCE_PRIOR_ADAPTER",
            "SOURCE_PRIOR_ADAPTER_VERIFICATION",
        ],
        "manifest_workload_final_replayed_by_remote_anchor": True,
        "caller_ids_or_statuses_accepted": False,
        "all_pretarget_serialized_artifacts_semantically_replayed": True,
        "target_accessed": False,
    }
    if (
        replay_payload != expected_replay_payload
        or item["artifact_semantic_replay_id"] != replay_id
        or _hash("semantic_artifact_replay", replay_payload) != replay_id
    ):
        _fail("semantic artifact replay differs from independent authorities")
    _verify_executed_module_blobs(
        roots=(
            importlib.import_module(__name__),
            module,
            legacy_independent,
            tracked_source,
        ),
        components=components,
    )
    return item, binding_id, replay_id


_MANIFEST_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "repository_url", "target_branch", "component_blobs",
    "component_registry_id", "semantic_registry_binding",
    "semantic_registry_binding_id", "semantic_artifact_replay_id",
    "workload", "workload_id", "runner_profile_id",
    "family_generation_id", "context_ids", "signer_registry_id",
    "opaque_environment_commitment", "opaque_environment_commitment_id",
    "exact_test_command", "deterministic_environment", "binding_order",
    "next_authority", "target_law_serialized", "target_tape_serialized",
    "private_key_serialized", "observer_opened", "target_accessed",
    "target_execution_allowed", "manifest_id",
}


def _verify_manifest(
    root: Path,
    commit_id: str,
    raw: bytes,
) -> dict[str, Any]:
    if b'"final_preregistration_id"' in raw:
        _fail("manifest circularly contains downstream authority text")
    item = _parse(raw, keys=_MANIFEST_KEYS, label="manifest")
    payload = dict(item)
    manifest_id = _cid(payload.pop("manifest_id"), "manifest")
    components, component_registry_id = _verify_components(
        root, commit_id, item["component_blobs"]
    )
    semantic, semantic_binding_id, semantic_artifact_replay_id = (
        _verify_semantic_registry(
            root,
            commit_id,
            components,
            item["semantic_registry_binding"],
        )
    )
    workload = _expected_workload()
    opaque = item["opaque_environment_commitment"]
    if type(opaque) is not dict:
        _fail("opaque environment commitment is not an object")
    try:
        commitment = public.V075OpaqueEnvironmentCommitmentV1(
            public.freeze_v075_public_family_generation_v1(),
            opaque["commitment_digest"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V075RemoteMainAnchorV2InvariantViolation(
            "opaque environment commitment is malformed"
        ) from error
    ids = (
        manifest_id,
        component_registry_id,
        semantic_binding_id,
        semantic["authority_registry_id"],
        semantic["authority_registry_verification_id"],
        semantic_artifact_replay_id,
        workload["workload_id"],
        workload["runner_profile_id"],
        commitment.commitment_id,
        item["signer_registry_id"],
    )
    for value in ids:
        _cid(value, "manifest identity")
    if (
        len(set(ids)) != len(ids)
        or item["schema"]
        != "acfqp.v075_confirmatory_execution_manifest.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != MANIFEST_PROFILE_KEY
        or item["repository_url"] != REPOSITORY_URL
        or item["target_branch"] != TARGET_BRANCH
        or item["component_registry_id"] != component_registry_id
        or item["semantic_registry_binding_id"] != semantic_binding_id
        or item["semantic_artifact_replay_id"]
        != semantic_artifact_replay_id
        or item["workload"] != workload
        or item["workload_id"] != workload["workload_id"]
        or item["runner_profile_id"] != workload["runner_profile_id"]
        or item["family_generation_id"] != workload["family_generation_id"]
        or item["context_ids"] != workload["context_ids"]
        or item["opaque_environment_commitment"] != commitment.to_document()
        or item["opaque_environment_commitment_id"]
        != commitment.commitment_id
        or item["exact_test_command"] != list(EXACT_TEST_COMMAND)
        or item["deterministic_environment"]
        != list(DETERMINISTIC_ENVIRONMENT)
        or item["binding_order"]
        != "COMPONENTS_THEN_SEMANTICS_THEN_WORKLOAD_THEN_MANIFEST"
        or item["next_authority"]
        != "SIGNED_FINAL_THEN_REMOTE_MAIN_ANCHOR"
        or item["target_law_serialized"] is not False
        or item["target_tape_serialized"] is not False
        or item["private_key_serialized"] is not False
        or item["observer_opened"] is not False
        or item["target_accessed"] is not False
        or item["target_execution_allowed"] is not False
        or _hash("manifest", payload) != manifest_id
    ):
        _fail("manifest semantic or identity replay failed")
    return item


_PUBLIC_KEY_KEYS = {
    "schema", "schema_version", "key_role", "algorithm", "modulus_hex",
    "public_exponent", "minimum_modulus_bits", "private_key_serialized",
    "key_id",
}
_SIGNER_REGISTRY_KEYS = {
    "schema", "schema_version", "campaign_authority_key_id",
    "observer_evidence_key_id", "private_keys_serialized",
    "registry_precedes_final_preregistration",
    "final_preregistration_must_bind_registry_id",
    "registry_contains_final_preregistration_id",
    "campaign_authority_key", "observer_evidence_key", "registry_id",
}


def _verify_public_key(
    value: Any,
    expected_role: str,
) -> public.V075RSAPublicVerificationKeyV1:
    item = _strict(value, keys=_PUBLIC_KEY_KEYS, label="RSA public key")
    try:
        modulus = int(item["modulus_hex"], 16)
        key = public.V075RSAPublicVerificationKeyV1(
            expected_role,
            modulus,
            item["public_exponent"],
        )
    except (TypeError, ValueError) as error:
        raise V075RemoteMainAnchorV2InvariantViolation(
            "RSA public key is malformed"
        ) from error
    if key.to_document() != item:
        _fail("RSA public key differs from independent reconstruction")
    return key


def _verify_signer_registry(
    value: Any,
    *,
    campaign_key_bytes_hex: Any,
    observer_key_bytes_hex: Any,
) -> public.V075TrustedSignerRegistryV1:
    item = _strict(
        value,
        keys=_SIGNER_REGISTRY_KEYS,
        label="signer registry",
    )
    campaign_key = _verify_public_key(
        item["campaign_authority_key"],
        "CAMPAIGN_AUTHORITY",
    )
    observer_key = _verify_public_key(
        item["observer_evidence_key"],
        "OBSERVER_EVIDENCE",
    )
    registry = public.V075TrustedSignerRegistryV1(
        campaign_key,
        observer_key,
    )
    try:
        campaign_bytes = bytes.fromhex(campaign_key_bytes_hex)
        observer_bytes = bytes.fromhex(observer_key_bytes_hex)
    except (TypeError, ValueError) as error:
        raise V075RemoteMainAnchorV2InvariantViolation(
            "pinned signer bytes are malformed"
        ) from error
    if (
        registry.to_document() != item
        or campaign_bytes
        != canonical_json_bytes(campaign_key.to_document())
        or observer_bytes
        != canonical_json_bytes(observer_key.to_document())
    ):
        _fail("signer registry or exact pinned public-key bytes changed")
    return registry


_FINAL_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "repository_url", "target_branch",
    "confirmatory_execution_manifest_id",
    "confirmatory_execution_manifest_bytes_sha256",
    "component_registry_id", "semantic_registry_binding_id",
    "semantic_authority_registry_id",
    "semantic_authority_registry_verification_id",
    "semantic_artifact_replay_id", "workload_id", "runner_profile_id",
    "family_generation_id", "context_ids", "arm_order",
    "logical_occurrence_denominator", "threshold_profile_id",
    "cap_profile_id", "private_environment_generation_profile_id",
    "opaque_environment_commitment_id", "signer_registry_id",
    "signer_registry", "campaign_authority_public_key_bytes",
    "observer_evidence_public_key_bytes", "campaign_authority_key_id",
    "observer_evidence_key_id", "exact_test_command",
    "manifest_precedes_signed_final", "remote_main_anchor_id",
    "preopen_v2_migration_status", "observer_open_allowed",
    "registered_target_execution_allowed", "official_execution_allowed",
    "target_accessed", "campaign_authority_signature_hex",
    "campaign_authority_signature_verified", "final_preregistration_id",
}


def _verify_final(
    raw: bytes,
    *,
    manifest: dict[str, Any],
    manifest_raw: bytes,
) -> tuple[dict[str, Any], public.V075TrustedSignerRegistryV1]:
    item = _parse(raw, keys=_FINAL_KEYS, label="final preregistration")
    registry = _verify_signer_registry(
        item["signer_registry"],
        campaign_key_bytes_hex=(
            item["campaign_authority_public_key_bytes"]
        ),
        observer_key_bytes_hex=(
            item["observer_evidence_public_key_bytes"]
        ),
    )
    unsigned = dict(item)
    final_id = _cid(
        unsigned.pop("final_preregistration_id"),
        "final preregistration",
    )
    signature = unsigned.pop("campaign_authority_signature_hex")
    unsigned.pop("campaign_authority_signature_verified")
    workload = manifest["workload"]
    semantic = manifest["semantic_registry_binding"]
    if (
        item["schema"] != "acfqp.v075_final_preregistration.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != MANIFEST_PROFILE_KEY
        or item["repository_url"] != REPOSITORY_URL
        or item["target_branch"] != TARGET_BRANCH
        or item["confirmatory_execution_manifest_id"]
        != manifest["manifest_id"]
        or item["confirmatory_execution_manifest_bytes_sha256"]
        != hashlib.sha256(manifest_raw).hexdigest()
        or item["component_registry_id"]
        != manifest["component_registry_id"]
        or item["semantic_registry_binding_id"]
        != manifest["semantic_registry_binding_id"]
        or item["semantic_authority_registry_id"]
        != semantic["authority_registry_id"]
        or item["semantic_authority_registry_verification_id"]
        != semantic["authority_registry_verification_id"]
        or item["semantic_artifact_replay_id"]
        != semantic["artifact_semantic_replay_id"]
        or item["workload_id"] != workload["workload_id"]
        or item["runner_profile_id"] != workload["runner_profile_id"]
        or item["family_generation_id"]
        != workload["family_generation_id"]
        or item["context_ids"] != workload["context_ids"]
        or item["arm_order"] != workload["arm_order"]
        or item["logical_occurrence_denominator"] != 15
        or item["threshold_profile_id"]
        != workload["threshold_profile_id"]
        or item["cap_profile_id"] != workload["cap_profile_id"]
        or item["private_environment_generation_profile_id"]
        != workload["private_environment_generation_profile_id"]
        or item["opaque_environment_commitment_id"]
        != manifest["opaque_environment_commitment_id"]
        or item["signer_registry_id"] != registry.registry_id
        or item["signer_registry_id"] != manifest["signer_registry_id"]
        or item["campaign_authority_key_id"]
        != registry.campaign_authority_key.key_id
        or item["observer_evidence_key_id"]
        != registry.observer_evidence_key.key_id
        or item["exact_test_command"] != list(EXACT_TEST_COMMAND)
        or item["manifest_precedes_signed_final"] is not True
        or item["remote_main_anchor_id"] is not None
        or item["preopen_v2_migration_status"] != "NOT_READY"
        or item["observer_open_allowed"] is not False
        or item["registered_target_execution_allowed"] is not False
        or item["official_execution_allowed"] is not False
        or item["target_accessed"] is not False
        or item["campaign_authority_signature_verified"] is not True
        or type(signature) is not str
        or not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=registry.campaign_authority_key,
            message=(
                FINAL_SIGNING_DOMAIN
                + b"\x00"
                + canonical_json_bytes(unsigned)
            ),
            signature_hex=signature,
        )
    ):
        _fail("signed final preregistration chain is invalid")
    final_payload = {
        **unsigned,
        "campaign_authority_signature_hex": signature,
        "campaign_authority_signature_verified": True,
    }
    if (
        _hash("final_preregistration", final_payload) != final_id
        or final_id.encode("ascii") in manifest_raw
        or b'"final_preregistration_id"' in manifest_raw
    ):
        _fail("final preregistration identity is invalid or circular")
    return item, registry


def _parents(root: Path, commit_id: str) -> tuple[str, ...]:
    text = _git(root, "show", "-s", "--format=%P", commit_id)
    return tuple(_oid(item, "parent commit") for item in text.split())


def _ancestors(root: Path, commit_id: str) -> tuple[str, ...]:
    text = _git(root, "rev-list", f"{commit_id}^@")
    return tuple(
        _oid(item, "ancestor commit")
        for item in text.splitlines()
        if item
    )


_ANCHOR_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075RemoteMainAnchorAttestationV2:
    _issuer: object = field(repr=False, compare=False)
    commit_id: str
    tree_id: str
    parent_commit_ids: tuple[str, ...]
    manifest_blob_id: str
    final_preregistration_blob_id: str
    manifest_id: str
    final_preregistration_id: str
    component_registry_id: str
    semantic_registry_binding_id: str
    semantic_artifact_replay_id: str
    workload_id: str
    runner_profile_id: str
    family_generation_id: str
    opaque_environment_commitment_id: str
    signer_registry: public.V075TrustedSignerRegistryV1
    _anchor_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ANCHOR_ISSUER
            or type(self.parent_commit_ids) is not tuple
            or type(self.signer_registry)
            is not public.V075TrustedSignerRegistryV1
        ):
            _fail("remote-main V2 attestation is verifier-issued only")
        for value in (
            self.commit_id,
            self.tree_id,
            self.manifest_blob_id,
            self.final_preregistration_blob_id,
            *self.parent_commit_ids,
        ):
            _oid(value, "anchor Git identity")
        ids = (
            self.manifest_id,
            self.final_preregistration_id,
            self.component_registry_id,
            self.semantic_registry_binding_id,
            self.semantic_artifact_replay_id,
            self.workload_id,
            self.runner_profile_id,
            self.family_generation_id,
            self.opaque_environment_commitment_id,
            self.signer_registry.registry_id,
        )
        for value in ids:
            _cid(value, "anchor content identity")
        if len(set(ids)) != len(ids):
            _fail("anchor aliases incompatible identities")
        object.__setattr__(
            self,
            "_anchor_id",
            _hash("anchor", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_independent_remote_main_anchor_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "repository_url": REPOSITORY_URL,
            "target_branch": TARGET_BRANCH,
            "remote_tracking_ref": REMOTE_TRACKING_REF,
            "commit_id": self.commit_id,
            "tree_id": self.tree_id,
            "parent_commit_ids": list(self.parent_commit_ids),
            "manifest_blob_id": self.manifest_blob_id,
            "final_preregistration_blob_id": (
                self.final_preregistration_blob_id
            ),
            "manifest_id": self.manifest_id,
            "final_preregistration_id": self.final_preregistration_id,
            "component_registry_id": self.component_registry_id,
            "semantic_registry_binding_id": (
                self.semantic_registry_binding_id
            ),
            "semantic_artifact_replay_id": (
                self.semantic_artifact_replay_id
            ),
            "workload_id": self.workload_id,
            "runner_profile_id": self.runner_profile_id,
            "family_generation_id": self.family_generation_id,
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment_id
            ),
            "signer_registry_id": self.signer_registry.registry_id,
            "campaign_authority_key_id": (
                self.signer_registry.campaign_authority_key.key_id
            ),
            "observer_evidence_key_id": (
                self.signer_registry.observer_evidence_key.key_id
            ),
            "head_local_main_origin_main_equal": True,
            "first_qualifying_commit_verified": True,
            "all_ancestors_lack_both_authority_paths": True,
            "component_blob_closure_verified": True,
            "every_registered_role_static_verifier_dispatched": True,
            "code_only_roles_static_surface_verified": True,
            "serialized_artifact_semantic_replay_complete": True,
            "final_signature_verified": True,
            "preopen_v2_migration_status": "NOT_READY",
            "observer_open_allowed": False,
            "target_accessed": False,
            "target_execution_allowed": False,
        }

    @property
    def anchor_id(self) -> str:
        return self._anchor_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "anchor_id": self.anchor_id}


@dataclass(frozen=True, slots=True)
class V075PreopenAuthorityV2MigrationBlocked:
    """A verified anchor that deliberately cannot open the V1 observer."""

    anchor: V075RemoteMainAnchorAttestationV2
    blocker: str = "PREOPEN_V2_MIGRATION_NOT_READY"

    def __post_init__(self) -> None:
        if (
            type(self.anchor) is not V075RemoteMainAnchorAttestationV2
            or self.blocker != "PREOPEN_V2_MIGRATION_NOT_READY"
        ):
            _fail("V2 migration blocker is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_preopen_authority_v2_blocked.v1",
            "schema_version": SCHEMA_VERSION,
            "remote_main_anchor_id": self.anchor.anchor_id,
            "blocker": self.blocker,
            "legacy_v1_projection_issued": False,
            "observer_open_allowed": False,
            "target_accessed": False,
            "target_execution_allowed": False,
        }


def verify_v075_remote_main_anchor_independently_v2(
    repository_root: str | Path,
) -> V075RemoteMainAnchorAttestationV2:
    """Derive authority solely from a complete tracked Git history."""

    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir() or not root.joinpath(".git").exists():
        raise V075RemoteMainAnchorV2NotReady(
            "repository root is not one Git worktree"
        )
    fetch_url = _git(root, "remote", "get-url", "origin")
    push_url = _git(root, "remote", "get-url", "--push", "origin")
    if fetch_url != REPOSITORY_URL or push_url != REPOSITORY_URL:
        raise V075RemoteMainAnchorV2NotReady(
            "origin fetch/push URLs are not the registered production remote"
        )
    remote_head = _oid(
        _git(root, "rev-parse", "--verify", REMOTE_TRACKING_REF),
        "origin/main",
    )
    local_head = _oid(
        _git(root, "rev-parse", "--verify", LOCAL_BRANCH_REF),
        "local main",
    )
    worktree_head = _oid(
        _git(root, "rev-parse", "--verify", "HEAD"),
        "HEAD",
    )
    if not (
        hmac.compare_digest(remote_head, local_head)
        and hmac.compare_digest(remote_head, worktree_head)
    ):
        raise V075RemoteMainAnchorV2NotReady(
            "HEAD, local main, and origin/main are not identical"
        )
    history = _git(
        root,
        "rev-list",
        "--reverse",
        "--topo-order",
        REMOTE_TRACKING_REF,
    ).splitlines()
    qualifying: tuple[
        str,
        bytes,
        bytes,
        dict[str, Any],
        dict[str, Any],
        public.V075TrustedSignerRegistryV1,
    ] | None = None
    for candidate in history:
        manifest_raw = _read_blob(
            root,
            candidate,
            MANIFEST_REPOSITORY_PATH,
        )
        final_raw = _read_blob(
            root,
            candidate,
            FINAL_PREREGISTRATION_REPOSITORY_PATH,
        )
        if manifest_raw is None or final_raw is None:
            continue
        try:
            manifest = _verify_manifest(root, candidate, manifest_raw)
            final, signer_registry = _verify_final(
                final_raw,
                manifest=manifest,
                manifest_raw=manifest_raw,
            )
        except V075RemoteMainAnchorV2InvariantViolation:
            continue
        qualifying = (
            _oid(candidate, "qualifying commit"),
            manifest_raw,
            final_raw,
            manifest,
            final,
            signer_registry,
        )
        break
    if qualifying is None:
        raise V075RemoteMainAnchorV2NotReady(
            "no complete qualifying origin/main commit exists"
        )
    (
        commit_id,
        manifest_raw,
        final_raw,
        manifest,
        final,
        signer_registry,
    ) = qualifying
    for ancestor in _ancestors(root, commit_id):
        if (
            _read_blob(root, ancestor, MANIFEST_REPOSITORY_PATH)
            is not None
            or _read_blob(
                root,
                ancestor,
                FINAL_PREREGISTRATION_REPOSITORY_PATH,
            )
            is not None
        ):
            _fail(
                "an ancestor already contains a manifest or final authority"
            )

    current_manifest_raw = _read_blob(
        root,
        remote_head,
        MANIFEST_REPOSITORY_PATH,
    )
    current_final_raw = _read_blob(
        root,
        remote_head,
        FINAL_PREREGISTRATION_REPOSITORY_PATH,
    )
    if (
        current_manifest_raw != manifest_raw
        or current_final_raw != final_raw
    ):
        _fail("origin/main authority blobs differ from the first qualifier")
    current_manifest = _verify_manifest(
        root,
        remote_head,
        current_manifest_raw,
    )
    current_final, current_registry = _verify_final(
        current_final_raw,
        manifest=current_manifest,
        manifest_raw=current_manifest_raw,
    )
    if (
        current_manifest != manifest
        or current_final != final
        or current_registry != signer_registry
    ):
        _fail("origin/main authority differs from the first qualifier")

    manifest_blob_id, _manifest_mode = _tree_blob(
        root,
        commit_id,
        MANIFEST_REPOSITORY_PATH,
    )
    final_blob_id, _final_mode = _tree_blob(
        root,
        commit_id,
        FINAL_PREREGISTRATION_REPOSITORY_PATH,
    )
    return V075RemoteMainAnchorAttestationV2(
        _ANCHOR_ISSUER,
        commit_id,
        _oid(
            _git(root, "show", "-s", "--format=%T", commit_id),
            "qualifying tree",
        ),
        _parents(root, commit_id),
        manifest_blob_id,
        final_blob_id,
        manifest["manifest_id"],
        final["final_preregistration_id"],
        manifest["component_registry_id"],
        manifest["semantic_registry_binding_id"],
        manifest["semantic_artifact_replay_id"],
        manifest["workload_id"],
        manifest["runner_profile_id"],
        manifest["family_generation_id"],
        manifest["opaque_environment_commitment_id"],
        signer_registry,
    )


def verify_v075_preopen_authority_v2_migration_blocked(
    repository_root: str | Path,
) -> V075PreopenAuthorityV2MigrationBlocked:
    return V075PreopenAuthorityV2MigrationBlocked(
        verify_v075_remote_main_anchor_independently_v2(
            repository_root
        )
    )


__all__ = [
    "FINAL_PREREGISTRATION_REPOSITORY_PATH",
    "LOCAL_BRANCH_REF",
    "MANIFEST_REPOSITORY_PATH",
    "PROFILE_KEY",
    "REMOTE_TRACKING_REF",
    "REPOSITORY_URL",
    "REQUIRED_COMPONENT_SPECS",
    "SCHEMA_VERSION",
    "TARGET_BRANCH",
    "V075PreopenAuthorityV2MigrationBlocked",
    "V075RemoteMainAnchorAttestationV2",
    "V075RemoteMainAnchorV2InvariantViolation",
    "V075RemoteMainAnchorV2NotReady",
    "verify_v075_preopen_authority_v2_migration_blocked",
    "verify_v075_remote_main_anchor_independently_v2",
]
