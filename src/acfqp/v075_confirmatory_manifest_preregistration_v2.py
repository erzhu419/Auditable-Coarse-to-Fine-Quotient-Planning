"""Strict pre-open manifest and final preregistration authority for V0-075.

This revision binds the complete production implementation closure, the
typed semantic-verifier registry, the public workload/caps, the exact public
signer registry, and one opaque environment commitment before target access.

The authority direction is acyclic::

    component Git blobs + semantic registry + public workload
        -> execution manifest
        -> signed final preregistration
        -> independent first-qualifying origin/main anchor

The manifest intentionally has no final-preregistration field or ID.  Neither
artifact opens an observer, receives a reveal, or authorizes target execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib
import inspect
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
from types import ModuleType
from typing import Any, Mapping, Protocol, runtime_checkable

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_private_environment_generation_profile_v1 as generation
from acfqp import v075_production_campaign_runner_v1 as production_runner
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.43.0"
PROFILE_KEY = "v075_confirmatory_manifest_preregistration_v2"

REPOSITORY_URL = (
    "git@github.com:erzhu419/"
    "Auditable-Coarse-to-Fine-Quotient-Planning.git"
)
TARGET_BRANCH = "main"
MANIFEST_REPOSITORY_PATH = "specs/V075_CONFIRMATORY_EXECUTION_MANIFEST.json"
FINAL_PREREGISTRATION_REPOSITORY_PATH = "specs/V075_FINAL_PREREGISTRATION.json"
DEPENDENCY_LOCK_REPOSITORY_PATH = "specs/V075_DEPENDENCY_LOCK.json"

EXACT_TEST_COMMAND = (
    "python3",
    "-m",
    "pytest",
    "-q",
    "-s",
    "tests/test_v075_campaign_authority_private_signer_runtime_v1.py",
    "tests/test_v075_production_semantic_authority_registry_v2.py",
    "tests/test_v075_tracked_source_authority_v1.py",
    "tests/test_v075_production_private_signer_runtime_v1.py",
    "tests/test_v075_occurrence_failure_lifecycle_authority_v1.py",
    "tests/test_v075_production_occurrence_plan_v1.py",
    "tests/test_v075_production_occurrence_ipc_v1.py",
    "tests/test_v075_batch_native_total_lift_authority_v1.py",
    "tests/test_v075_preopen_v2_authorities.py",
    "tests/test_v075_production_occurrence_authority_v1.py",
    "tests/test_v075_production_campaign_reconciliation_v1.py",
    "tests/test_v075_production_complete_bundle_endpoint_v1.py",
    "tests/test_v075_production_campaign_runner_v1.py",
    "tests/test_v075_manifest_preregistration_remote_main_anchor_v2.py",
)
DETERMINISTIC_ENVIRONMENT = (
    ("LC_ALL", "C.UTF-8"),
    ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1"),
    ("PYTHONDONTWRITEBYTECODE", "1"),
    ("PYTHONHASHSEED", "0"),
    ("TZ", "UTC"),
)


# This registry is deliberately static.  It is duplicated by the independent
# remote verifier and is never inferred from the current filesystem.
REQUIRED_COMPONENT_SPECS = (
    (
        "MANIFEST_AND_PREREGISTRATION_AUTHORITY_V2",
        "src/acfqp/v075_confirmatory_manifest_preregistration_v2.py",
    ),
    (
        "HISTORICAL_MANIFEST_AUTHORITY_V1_DEPENDENCY",
        "src/acfqp/v075_confirmatory_manifest_preregistration_v1.py",
    ),
    (
        "INDEPENDENT_REMOTE_MAIN_ANCHOR_VERIFIER_V2",
        "src/acfqp/v075_remote_main_anchor_verifier_v2.py",
    ),
    (
        "PRODUCTION_SEMANTIC_AUTHORITY_REGISTRY_V2",
        "src/acfqp/v075_production_semantic_authority_registry_v2.py",
    ),
    (
        "PRODUCTION_CAMPAIGN_RUNNER",
        "src/acfqp/v075_production_campaign_runner_v1.py",
    ),
    (
        "PRODUCTION_CAMPAIGN_RUNNER_TEST",
        "tests/test_v075_production_campaign_runner_v1.py",
    ),
    (
        "CAMPAIGN_AUTHORITY_PRIVATE_SIGNER_TEST",
        "tests/test_v075_campaign_authority_private_signer_runtime_v1.py",
    ),
    (
        "PRODUCTION_SEMANTIC_AUTHORITY_REGISTRY_V2_TEST",
        "tests/test_v075_production_semantic_authority_registry_v2.py",
    ),
    (
        "TRACKED_SOURCE_AUTHORITY_TEST",
        "tests/test_v075_tracked_source_authority_v1.py",
    ),
    (
        "OBSERVER_PRIVATE_SIGNER_RUNTIME_TEST",
        "tests/test_v075_production_private_signer_runtime_v1.py",
    ),
    (
        "OCCURRENCE_FAILURE_LIFECYCLE_AUTHORITY_TEST",
        "tests/test_v075_occurrence_failure_lifecycle_authority_v1.py",
    ),
    (
        "PRODUCTION_OCCURRENCE_PLAN_TEST",
        "tests/test_v075_production_occurrence_plan_v1.py",
    ),
    (
        "PRODUCTION_OCCURRENCE_IPC_TEST",
        "tests/test_v075_production_occurrence_ipc_v1.py",
    ),
    (
        "BATCH_NATIVE_TOTAL_LIFT_AUTHORITY_TEST",
        "tests/test_v075_batch_native_total_lift_authority_v1.py",
    ),
    (
        "PREOPEN_V2_AUTHORITIES_TEST",
        "tests/test_v075_preopen_v2_authorities.py",
    ),
    (
        "PRODUCTION_OCCURRENCE_AUTHORITY_TEST",
        "tests/test_v075_production_occurrence_authority_v1.py",
    ),
    (
        "PRODUCTION_CAMPAIGN_RECONCILIATION_TEST",
        "tests/test_v075_production_campaign_reconciliation_v1.py",
    ),
    (
        "PRODUCTION_COMPLETE_BUNDLE_ENDPOINT_TEST",
        "tests/test_v075_production_complete_bundle_endpoint_v1.py",
    ),
    (
        "MANIFEST_REMOTE_MAIN_ANCHOR_V2_TEST",
        "tests/test_v075_manifest_preregistration_remote_main_anchor_v2.py",
    ),
    (
        "PHASE3E_CANONICAL_IDENTITY",
        "src/acfqp/phase3e_ids.py",
    ),
    ("ACFQP_PACKAGE_INIT", "src/acfqp/__init__.py"),
    (
        "PUBLIC_CAMPAIGN_AUTHORITY",
        "src/acfqp/v075_public_campaign_authority_v1.py",
    ),
    (
        "PUBLIC_GRAPH_SEMANTICS",
        "src/acfqp/v075_public_graph_semantics_v1.py",
    ),
    (
        "PRIVATE_ENVIRONMENT_GENERATION_PROFILE",
        "src/acfqp/v075_private_environment_generation_profile_v1.py",
    ),
    (
        "PRODUCTION_PRIVATE_SIGNER_RUNTIME",
        "src/acfqp/v075_production_private_signer_runtime_v1.py",
    ),
    (
        "CAMPAIGN_AUTHORITY_PRIVATE_SIGNER_RUNTIME",
        "src/acfqp/v075_campaign_authority_private_signer_runtime_v1.py",
    ),
    (
        "PREOPEN_TARGET_AUTHORIZATION",
        "src/acfqp/v075_preopen_target_authorization_v1.py",
    ),
    (
        "REVEAL_VERIFYING_ATTESTATION_AUTHORITY_V2",
        "src/acfqp/v075_reveal_verifying_attestation_authority_v2.py",
    ),
    (
        "PREOPEN_TARGET_AUTHORIZATION_V2",
        "src/acfqp/v075_preopen_target_authorization_v2.py",
    ),
    (
        "HISTORICAL_REMOTE_ANCHOR_V1_DEPENDENCY",
        "src/acfqp/v075_remote_main_anchor_verifier_v1.py",
    ),
    (
        "REVEAL_VERIFYING_ATTESTATION_AUTHORITY",
        "src/acfqp/v075_reveal_verifying_attestation_authority_v1.py",
    ),
    (
        "PRIVATE_OBSERVER_BOUNDARY",
        "src/acfqp/v075_private_observer_boundary_v1.py",
    ),
    (
        "BATCHED_OBSERVER_AUTHORITY",
        "src/acfqp/v075_batched_observer_authority_v1.py",
    ),
    (
        "MULTISTAGE_OBSERVER_LIFECYCLE",
        "src/acfqp/v075_multistage_observer_lifecycle_v1.py",
    ),
    (
        "OCCURRENCE_FAILURE_LIFECYCLE_AUTHORITY",
        "src/acfqp/v075_occurrence_failure_lifecycle_authority_v1.py",
    ),
    (
        "PRODUCTION_OCCURRENCE_PLAN",
        "src/acfqp/v075_production_occurrence_plan_v1.py",
    ),
    (
        "PRODUCTION_OCCURRENCE_IPC",
        "src/acfqp/v075_production_occurrence_ipc_v1.py",
    ),
    (
        "OPERATIONAL_PLANNER_TRANSPORT",
        "src/acfqp/v075_operational_planner_transport_v1.py",
    ),
    (
        "PRODUCTION_OCCURRENCE_AUTHORITY",
        "src/acfqp/v075_production_occurrence_authority_v1.py",
    ),
    (
        "PRODUCTION_CAMPAIGN_RECONCILIATION",
        "src/acfqp/v075_production_campaign_reconciliation_v1.py",
    ),
    (
        "PRODUCTION_COMPLETE_BUNDLE_ENDPOINT",
        "src/acfqp/v075_production_complete_bundle_endpoint_v1.py",
    ),
    (
        "OCCURRENCE_CAS_TRANSPORT",
        "src/acfqp/v075_occurrence_cas_transport_v1.py",
    ),
    (
        "REGISTERED_OCCURRENCE_WORKER",
        "src/acfqp/v075_registered_occurrence_worker_v1.py",
    ),
    (
        "ROUTE_NATIVE_BACKEND_CORE",
        "src/acfqp/v075_route_native_backend_core_v1.py",
    ),
    (
        "BATCH_NATIVE_STATISTICAL_BACKEND",
        "src/acfqp/v075_batch_native_statistical_backend_v1.py",
    ),
    (
        "LEARNED_SUPPORT_QUOTIENT_PLANNERS",
        "src/acfqp/v075_learned_support_quotient_planners_v1.py",
    ),
    (
        "BATCH_NATIVE_TOTAL_LIFT_AUTHORITY",
        "src/acfqp/v075_batch_native_total_lift_authority_v1.py",
    ),
    (
        "TOTAL_LIFT_AUTHORITY",
        "src/acfqp/v075_total_lift_authority_v1.py",
    ),
    (
        "INTEGRATED_OCCURRENCE_PIPELINE",
        "src/acfqp/v075_integrated_occurrence_pipeline_v1.py",
    ),
    (
        "INTEGRATED_DIRECT_OCCURRENCE_PIPELINE",
        "src/acfqp/v075_integrated_direct_occurrence_pipeline_v1.py",
    ),
    (
        "ADAPTIVE_ACQUISITION_PROPOSAL_AUTHORITY",
        "src/acfqp/v075_adaptive_acquisition_proposal_authority_v1.py",
    ),
    (
        "ADAPTIVE_ACQUISITION_ROUND_BUNDLE_AUTHORITY",
        "src/acfqp/v075_adaptive_acquisition_round_bundle_authority_v1.py",
    ),
    (
        "FROZEN_SOURCE_PROPOSAL_ARCHIVE",
        "src/acfqp/v075_frozen_source_proposal_archive_v1.py",
    ),
    (
        "SOURCE_PRIOR_ADAPTER",
        "src/acfqp/v075_source_prior_adapter_v1.py",
    ),
    (
        "SOURCE_OFFLINE_WORK_MATERIALIZER",
        "src/acfqp/v075_source_offline_work_materializer_v1.py",
    ),
    (
        "PUBLIC_SOURCE_WORK_AUTHORITY",
        "src/acfqp/v075_public_source_work_authority_v1.py",
    ),
    (
        "TRACKED_SOURCE_AUTHORITY",
        "src/acfqp/v075_tracked_source_authority_v1.py",
    ),
    (
        "SOURCE_REPLAY_CONTROLLER",
        "scripts/replay_and_materialize_v075_source_work.py",
    ),
    (
        "SOURCE_COMPILATION_CONTROLLER",
        "scripts/compile_v075_public_source_artifacts.py",
    ),
    (
        "H2_GRAPH_TRANSITION_ENGINE",
        "src/acfqp/h2_graph_transition_engine_v1.py",
    ),
    (
        "RELATIONAL_GRAPH_CORE",
        "src/acfqp/relational_graph_core_v1.py",
    ),
    (
        "PARTIAL_SUPPORT_CONFIDENCE",
        "src/acfqp/partial_support_confidence_v1.py",
    ),
    (
        "SEQUENTIAL_BERNOULLI_ACQUISITION",
        "src/acfqp/sequential_bernoulli_acquisition_v1.py",
    ),
    (
        "OBSERVATION_SUPPORT_GRAPH_ACQUISITION",
        "src/acfqp/observation_support_graph_acquisition_v1.py",
    ),
    (
        "OBSERVATION_SUPPORT_CAMPAIGN",
        "src/acfqp/observation_support_campaign_v1.py",
    ),
    (
        "OBSERVATION_SUPPORT_COORDINATE_REFINEMENT",
        "src/acfqp/observation_support_coordinate_refinement_v1.py",
    ),
    (
        "OBSERVATION_SUPPORT_EXACT_EVALUATION",
        "src/acfqp/observation_support_exact_evaluation_v1.py",
    ),
    (
        "OBSERVATION_SUPPORT_GRAPH_MODEL",
        "src/acfqp/observation_support_graph_model_v1.py",
    ),
    (
        "OBSERVATION_SUPPORT_GROUPED_REPLAY",
        "src/acfqp/observation_support_grouped_replay_v1.py",
    ),
    (
        "OBSERVATION_SUPPORT_H2_CLOSURE",
        "src/acfqp/observation_support_h2_closure_v1.py",
    ),
    (
        "OBSERVATION_SUPPORT_PROMOTED_H2_CONSUMER",
        "src/acfqp/observation_support_promoted_h2_consumer_v1.py",
    ),
    (
        "OBSERVATION_SUPPORT_RELATIONAL_ADAPTER",
        "src/acfqp/observation_support_relational_adapter_v1.py",
    ),
    (
        "PARTIAL_SUPPORT_EXPANSION_AUTHORITY",
        "src/acfqp/partial_support_expansion_authority_v1.py",
    ),
    (
        "PARTIAL_SUPPORT_FAMILY_CONFIDENCE",
        "src/acfqp/partial_support_family_confidence_v1.py",
    ),
    (
        "PARTIAL_SUPPORT_ROBUST_PLANNER",
        "src/acfqp/partial_support_robust_planner_v1.py",
    ),
    (
        "TRANSITION_TUPLE_OBSERVER",
        "src/acfqp/transition_tuple_observer_v1.py",
    ),
    (
        "TRANSFER_GUIDED_ACQUISITION_PREREGISTRATION",
        "src/acfqp/transfer_guided_acquisition_preregistration_v1.py",
    ),
    (
        "VERIFIED_SOURCE_ARCHIVE",
        "src/acfqp/verified_source_acquisition_archive_v2.py",
    ),
    (
        "VERIFIED_SOURCE_ARCHIVE_INDEPENDENT_VERIFIER",
        "src/acfqp/verified_source_acquisition_archive_independent_verifier_v2.py",
    ),
    (
        "V072_SOURCE_RECONSTRUCTION_RECIPE",
        "src/acfqp/v072_source_reconstruction_recipe_v1.py",
    ),
    (
        "V072_VERIFIED_SOURCE_ARCHIVE_COMPONENT",
        "src/acfqp/v072_verified_source_archive_component_v1.py",
    ),
    (
        "V072_EXECUTION_ENVIRONMENT_AUTHORITY",
        "src/acfqp/v072_execution_environment_authority_v1.py",
    ),
    (
        "V072_EXECUTION_ENVIRONMENT_INDEPENDENT_VERIFIER",
        "src/acfqp/v072_execution_environment_independent_verifier_v1.py",
    ),
    (
        "V072_CONFIRMATORY_EXECUTION_MANIFEST",
        "src/acfqp/v072_confirmatory_execution_manifest_v1.py",
    ),
    (
        "V072_SOURCE_RECONSTRUCTION_RECIPE_ARTIFACT",
        "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json",
    ),
    (
        "RUNTIME_DEPENDENCY_LOCK",
        "specs/V075_DEPENDENCY_LOCK.json",
    ),
    (
        "FROZEN_SOURCE_ARCHIVE_ARTIFACT",
        "specs/V075_FROZEN_SOURCE_PROPOSAL_ARCHIVE.json",
    ),
    (
        "FROZEN_SOURCE_ARCHIVE_VERIFICATION",
        "specs/V075_FROZEN_SOURCE_PROPOSAL_ARCHIVE_VERIFICATION.json",
    ),
    (
        "SOURCE_PRIOR_ADAPTER_ARTIFACT",
        "specs/V075_SOURCE_PRIOR_ADAPTER.json",
    ),
    (
        "SOURCE_PRIOR_ADAPTER_VERIFICATION",
        "specs/V075_SOURCE_PRIOR_ADAPTER_VERIFICATION.json",
    ),
    (
        "SOURCE_OFFLINE_WORK_ARTIFACT",
        "specs/V075_SOURCE_OFFLINE_WORK_MATERIALIZATION.json",
    ),
    (
        "SOURCE_OFFLINE_WORK_VERIFICATION",
        "specs/V075_SOURCE_OFFLINE_WORK_MATERIALIZATION_VERIFICATION.json",
    ),
    (
        "VERIFIED_PUBLIC_SOURCE_WORK_BUNDLE",
        "specs/V075_VERIFIED_PUBLIC_SOURCE_WORK_BUNDLE.json",
    ),
    (
        "SOURCE_REPLAY_MATERIALIZATION_STATUS",
        "specs/V075_SOURCE_REPLAY_MATERIALIZATION_STATUS.json",
    ),
    ("PROJECT_BUILD_METADATA", "pyproject.toml"),
)

if (
    len(REQUIRED_COMPONENT_SPECS)
    != len({role for role, _path in REQUIRED_COMPONENT_SPECS})
    or len(REQUIRED_COMPONENT_SPECS)
    != len({path for _role, path in REQUIRED_COMPONENT_SPECS})
):
    raise RuntimeError("V0-075 V2 component registry is not one-to-one")


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
    "readiness": "acfqp:v075-confirmatory-readiness:v2",
}
FINAL_SIGNING_DOMAIN = b"acfqp:v075-final-preregistration-signing:v2"


class V075ManifestV2InvariantViolation(ValueError):
    """A V0-075 V2 public preregistration invariant failed."""


class V075ManifestV2NotReady(RuntimeError):
    """The complete public pre-open authority chain is not concrete."""


def _fail(message: str) -> None:
    raise V075ManifestV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ManifestV2InvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ManifestV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _git_oid(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) not in (40, 64)
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field_name} must be one full lowercase Git object ID")
    return value


def _safe_path(value: Any) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\\" in value
        or "\x00" in value
    ):
        _fail("repository path is malformed")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        _fail("repository path is unsafe or noncanonical")
    return value


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
        _fail(
            "Git inspection failed: "
            + process.stderr.decode("utf-8", errors="replace").strip()
        )
    return process.stdout.decode("utf-8").strip()


@dataclass(frozen=True, slots=True)
class V075ManifestComponentBlobV2:
    role: str
    repository_path: str
    git_blob_id: str
    bytes_sha256: str
    byte_count: int
    executable: bool

    def __post_init__(self) -> None:
        if (
            dict(REQUIRED_COMPONENT_SPECS).get(self.role)
            != _safe_path(self.repository_path)
            or type(self.byte_count) is not int
            or self.byte_count <= 0
            or type(self.executable) is not bool
        ):
            _fail("component role/path/metadata is not registered")
        _git_oid(self.git_blob_id, "component Git blob")
        _cid(self.bytes_sha256, "component bytes digest")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_manifest_component_blob.v2",
            "schema_version": SCHEMA_VERSION,
            "role": self.role,
            "repository_path": self.repository_path,
            "git_blob_id": self.git_blob_id,
            "bytes_sha256": self.bytes_sha256,
            "byte_count": self.byte_count,
            "executable": self.executable,
            "worktree_bytes_equal_index_blob": True,
            "target_accessed": False,
        }

    @property
    def component_id(self) -> str:
        return _hash("component_blob", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "component_id": self.component_id}


def collect_v075_manifest_component_blob_v2(
    repository_root: str | os.PathLike[str],
    *,
    role: str,
) -> V075ManifestComponentBlobV2:
    expected = dict(REQUIRED_COMPONENT_SPECS).get(role)
    if expected is None:
        _fail("component role is not registered")
    root = Path(repository_root).resolve(strict=True)
    candidate = root
    for part in PurePosixPath(expected).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            _fail("component path contains a symlink")
    metadata = candidate.stat()
    if not stat.S_ISREG(metadata.st_mode):
        _fail("component is not one regular file")
    raw = candidate.read_bytes()
    if not raw:
        _fail("component is empty")
    stage = _git(root, "ls-files", "--stage", "--", expected).splitlines()
    if len(stage) != 1 or "\t" not in stage[0]:
        _fail("component lacks one stage-zero index blob")
    prefix, indexed_path = stage[0].split("\t", 1)
    fields = prefix.split()
    if (
        indexed_path != expected
        or len(fields) != 3
        or fields[2] != "0"
        or fields[0] not in {"100644", "100755"}
    ):
        _fail("component index entry is malformed")
    blob_id = _git_oid(fields[1], "component indexed blob")
    blob = subprocess.run(
        ("git", "-C", str(root), "cat-file", "blob", blob_id),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if blob.returncode or blob.stdout != raw:
        _fail("component worktree bytes differ from the index blob")
    return V075ManifestComponentBlobV2(
        role,
        expected,
        blob_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
        fields[0] == "100755",
    )


_WORKLOAD_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConfirmatoryPublicWorkloadV2:
    """Exact public family, order, thresholds, and hard caps."""

    _issuer: object = field(repr=False, compare=False)
    family: public.V075PublicFamilyGenerationV1
    generation_profile: (
        generation.V075PrivateEnvironmentGenerationProfileV1
    )
    worker_registry: worker.V075ProductionWorkerRegistryDraftV1
    threshold_profile: worker.V075WorkerThresholdProfileV1
    cap_profile: worker.V075WorkerCapProfileV1
    runner_profile: (
        production_runner.V075ProductionCampaignRunnerProfileV1
    )
    _workload_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        exact_family = public.freeze_v075_public_family_generation_v1()
        if (
            self._issuer is not _WORKLOAD_ISSUER
            or type(self.family) is not public.V075PublicFamilyGenerationV1
            or self.family != exact_family
            or type(self.generation_profile)
            is not generation.V075PrivateEnvironmentGenerationProfileV1
            or self.generation_profile
            != generation.freeze_v075_private_environment_generation_profile_v1()
            or type(self.worker_registry)
            is not worker.V075ProductionWorkerRegistryDraftV1
            or self.worker_registry
            != worker.freeze_v075_worker_registry_draft_v1()
            or type(self.threshold_profile)
            is not worker.V075WorkerThresholdProfileV1
            or type(self.cap_profile) is not worker.V075WorkerCapProfileV1
            or type(self.runner_profile)
            is not production_runner.V075ProductionCampaignRunnerProfileV1
            or self.runner_profile
            != production_runner.freeze_v075_production_campaign_runner_profile_v1()
            or tuple(public.ARM_ORDER)
            != tuple(item.arm.value for item in self.worker_registry.registrations)
            or len(self.family.replicate_contexts) != 3
            or len(self.worker_registry.registrations) != 5
        ):
            _fail("public confirmatory workload is not the exact frozen profile")
        object.__setattr__(
            self,
            "_workload_id",
            _hash("workload", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_confirmatory_public_workload.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "family_generation": self.family.to_document(),
            "family_generation_id": self.family.generation_id,
            "context_ids": [
                item.context_id for item in self.family.replicate_contexts
            ],
            "context_count": 3,
            "arm_order": list(public.ARM_ORDER),
            "arm_count": 5,
            "logical_occurrence_denominator": 15,
            "occurrence_order": "CONTEXT_MAJOR_THEN_FROZEN_ARM_ORDER",
            "scientific_ordinals": list(range(15)),
            "transport_ordinals": list(range(1, 16)),
            "private_environment_generation_profile": (
                self.generation_profile.to_document()
            ),
            "private_environment_generation_profile_id": (
                self.generation_profile.profile_id
            ),
            "worker_registry": self.worker_registry.to_document(),
            "worker_registry_id": self.worker_registry.registry_id,
            "threshold_profile": self.threshold_profile.to_document(),
            "threshold_profile_id": (
                self.threshold_profile.threshold_profile_id
            ),
            "cap_profile": self.cap_profile.to_document(),
            "cap_profile_id": self.cap_profile.cap_profile_id,
            "runner_profile": self.runner_profile.to_document(),
            "runner_profile_id": self.runner_profile.profile_id,
            "target_law_serialized": False,
            "target_tape_serialized": False,
            "target_accessed": False,
            "target_execution_allowed": False,
        }

    @property
    def workload_id(self) -> str:
        return self._workload_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "workload_id": self.workload_id}


def freeze_v075_confirmatory_public_workload_v2(
) -> V075ConfirmatoryPublicWorkloadV2:
    return V075ConfirmatoryPublicWorkloadV2(
        _WORKLOAD_ISSUER,
        public.freeze_v075_public_family_generation_v1(),
        generation.freeze_v075_private_environment_generation_profile_v1(),
        worker.freeze_v075_worker_registry_draft_v1(),
        worker.V075WorkerThresholdProfileV1(),
        worker.V075WorkerCapProfileV1(),
        production_runner.freeze_v075_production_campaign_runner_profile_v1(),
    )


@dataclass(frozen=True, slots=True)
class V075ManifestSemanticBindingV2:
    """One registry-derived semantic verifier binding.

    Construction is private to :func:`bind_v075_semantic_registry_v2`; callers
    cannot promote module/function names into authority.
    """

    _issuer: object = field(repr=False, compare=False)
    ordinal: int
    role: str
    verifier_module: str
    verifier_function: str
    artifact_schemas: tuple[str, ...]
    artifact_domains: tuple[str, ...]
    prerequisite_roles: tuple[str, ...]
    role_spec_id: str
    verifier_component_id: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _SEMANTIC_ISSUER
            or type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.role) is not str
            or not self.role
            or type(self.verifier_module) is not str
            or not self.verifier_module.startswith("acfqp.")
            or type(self.verifier_function) is not str
            or not self.verifier_function.startswith("verify_")
            or type(self.artifact_schemas) is not tuple
            or type(self.artifact_domains) is not tuple
            or len(self.artifact_domains) != len(self.artifact_schemas)
            or type(self.prerequisite_roles) is not tuple
            or len(set(self.prerequisite_roles))
            != len(self.prerequisite_roles)
        ):
            _fail("semantic verifier binding is malformed")
        _cid(self.role_spec_id, "semantic role spec")
        _cid(self.verifier_component_id, "semantic verifier component")
        try:
            module = importlib.import_module(self.verifier_module)
            dispatcher = getattr(
                module,
                "verify_v075_production_semantic_authority_registry_v2",
            )
            verifier = module._SEMANTIC_VERIFIER_FUNCTIONS.get(  # noqa: SLF001
                self.verifier_function
            )
        except (ImportError, AttributeError) as error:
            raise V075ManifestV2InvariantViolation(
                "semantic verifier callable is absent"
            ) from error
        if (
            not callable(dispatcher)
            or inspect.iscoroutinefunction(dispatcher)
            or not callable(verifier)
            or inspect.iscoroutinefunction(verifier)
        ):
            _fail("semantic verifier is not one synchronous callable")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("semantic_binding", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_manifest_semantic_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "role": self.role,
            "verifier_module": self.verifier_module,
            "verifier_function": self.verifier_function,
            "artifact_schemas": list(self.artifact_schemas),
            "artifact_domains": list(self.artifact_domains),
            "prerequisite_roles": list(self.prerequisite_roles),
            "role_spec_id": self.role_spec_id,
            "verifier_component_id": self.verifier_component_id,
            "semantic_verifier_callable_verified": True,
            "string_status_sufficient": False,
            "target_accessed": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


_SEMANTIC_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ManifestSemanticRegistryBindingV2:
    _issuer: object = field(repr=False, compare=False)
    authority_registry_id: str
    authority_registry_verification_id: str
    role_bindings: tuple[V075ManifestSemanticBindingV2, ...]
    authority_registry_document: Mapping[str, Any]
    authority_registry_verification_document: Mapping[str, Any]
    artifact_semantic_replay_document: Mapping[str, Any]
    artifact_semantic_replay_id: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _SEMANTIC_ISSUER
            or type(self.role_bindings) is not tuple
            or not self.role_bindings
            or any(
                type(item) is not V075ManifestSemanticBindingV2
                for item in self.role_bindings
            )
            or tuple(item.ordinal for item in self.role_bindings)
            != tuple(range(len(self.role_bindings)))
            or len({item.role for item in self.role_bindings})
            != len(self.role_bindings)
            or len(
                {
                    (item.verifier_module, item.verifier_function)
                    for item in self.role_bindings
                }
            )
            != len(self.role_bindings)
            or type(self.authority_registry_document) is not dict
            or type(self.authority_registry_verification_document) is not dict
            or type(self.artifact_semantic_replay_document) is not dict
        ):
            _fail("semantic registry binding is incomplete or role-aliased")
        _cid(self.authority_registry_id, "semantic authority registry")
        _cid(
            self.authority_registry_verification_id,
            "semantic authority registry verification",
        )
        _cid(
            self.artifact_semantic_replay_id,
            "semantic artifact replay",
        )
        replay_payload = dict(self.artifact_semantic_replay_document)
        if (
            replay_payload.pop("artifact_semantic_replay_id", None)
            != self.artifact_semantic_replay_id
            or _hash("semantic_artifact_replay", replay_payload)
            != self.artifact_semantic_replay_id
        ):
            _fail("semantic artifact replay identity is invalid")
        if self.authority_registry_id == self.authority_registry_verification_id:
            _fail("semantic registry and verification identities alias")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("semantic_registry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_manifest_semantic_registry_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "authority_registry_id": self.authority_registry_id,
            "authority_registry_verification_id": (
                self.authority_registry_verification_id
            ),
            "authority_registry_document": dict(
                self.authority_registry_document
            ),
            "authority_registry_verification_document": dict(
                self.authority_registry_verification_document
            ),
            "artifact_semantic_replay_document": dict(
                self.artifact_semantic_replay_document
            ),
            "artifact_semantic_replay_id": (
                self.artifact_semantic_replay_id
            ),
            "role_bindings": [
                item.to_document() for item in self.role_bindings
            ],
            "role_count": len(self.role_bindings),
            "every_role_has_distinct_semantic_verifier": True,
            "string_status_sufficient": False,
            "target_accessed": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


def _component_for_module(
    components: tuple[V075ManifestComponentBlobV2, ...],
    module_name: str,
) -> V075ManifestComponentBlobV2:
    expected_path = "src/" + module_name.replace(".", "/") + ".py"
    matches = tuple(
        item for item in components if item.repository_path == expected_path
    )
    if len(matches) != 1:
        _fail("semantic verifier module is not one bound component")
    return matches[0]


def _verify_executed_module_component_closure(
    *,
    roots: tuple[ModuleType, ...],
    components: tuple[V075ManifestComponentBlobV2, ...],
) -> None:
    by_path = {item.repository_path: item for item in components}
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
            raise V075ManifestV2InvariantViolation(
                "executed semantic module source is unreadable"
            ) from error
        if digest != component.bytes_sha256:
            _fail(
                f"executed semantic module differs from bound blob: {name}"
            )
        queue.extend(
            value
            for value in vars(module).values()
            if isinstance(value, ModuleType)
            and getattr(value, "__name__", "").startswith("acfqp")
        )


def bind_v075_semantic_registry_v2(
    *,
    components: tuple[V075ManifestComponentBlobV2, ...],
    package_root: Path | None = None,
) -> V075ManifestSemanticRegistryBindingV2:
    """Recompute the typed semantic registry and bind every verifier callable.

    The V2 registry is a separately bound production component.  This adapter
    accepts no caller role list, verifier names, IDs, or status strings.
    """

    try:
        registry_module = importlib.import_module(
            "acfqp.v075_production_semantic_authority_registry_v2"
        )
        registry = (
            registry_module.freeze_v075_production_semantic_authority_registry_v2()
        )
        verification = (
            registry_module.verify_v075_production_semantic_authority_registry_v2(
                registry,
                package_root=package_root,
            )
        )
        registry_document = registry.to_document()
        verification_document = verification.to_document()
        registry_id = registry.registry_id
        verification_id = verification.verification_id
        role_specs = registry.role_specs
    except (
        AttributeError,
        ImportError,
        TypeError,
        ValueError,
    ) as error:
        raise V075ManifestV2InvariantViolation(
            "typed semantic authority registry V2 is unavailable or invalid"
        ) from error
    if (
        type(registry_document) is not dict
        or type(verification_document) is not dict
        or type(role_specs) is not tuple
        or not role_specs
        or verification_document.get("registry_id") != registry_id
        or verification_document.get("verification_id") != verification_id
        or len(verification_document.get("role_records", ()))
        != len(role_specs)
    ):
        _fail("semantic authority registry verification did not pass")
    bindings: list[V075ManifestSemanticBindingV2] = []
    for ordinal, spec in enumerate(role_specs):
        try:
            spec_document = spec.to_document()
            module_name = spec.semantic_verifier_module
            function_name = spec.semantic_verifier_id
            role = spec.role.value
            schemas = tuple(spec.artifact_schemas)
            domains = tuple(spec.artifact_domains)
            prerequisite_roles = tuple(
                item.value for item in spec.prerequisite_roles
            )
            role_spec_id = spec.spec_id
        except (AttributeError, TypeError, ValueError) as error:
            raise V075ManifestV2InvariantViolation(
                "semantic role spec is not the exact typed V2 schema"
            ) from error
        if (
            spec_document.get("ordinal") != ordinal
            or spec_document.get("role") != role
            or spec_document.get("semantic_verifier_module") != module_name
            or spec_document.get("verifier_function") != function_name
            or spec_document.get("spec_id") != role_spec_id
        ):
            _fail("semantic role spec properties differ from its document")
        component = _component_for_module(components, module_name)
        bindings.append(
            V075ManifestSemanticBindingV2(
                _SEMANTIC_ISSUER,
                ordinal,
                role,
                module_name,
                function_name,
                schemas,
                domains,
                prerequisite_roles,
                role_spec_id,
                component.component_id,
            )
        )
    if package_root is None:
        _fail("semantic artifact replay requires one repository package root")
    repository_root = package_root.parent.parent
    try:
        legacy_independent = importlib.import_module(
            "acfqp.v075_remote_main_anchor_verifier_v1"
        )
        tracked_source = importlib.import_module(
            "acfqp.v075_tracked_source_authority_v1"
        )
        commit_id = _git(repository_root, "rev-parse", "--verify", "HEAD")
        (
            dependency_lock_id,
            dependency_verification_id,
            dependency_canonical_sha256,
        ) = legacy_independent._verify_dependency_lock_at_commit(  # noqa: SLF001
            repository_root,
            commit_id,
        )
        source_bundle, source_verification = (
            tracked_source.verify_tracked_v075_source_authorities_v1(
                repository_root
            )
        )
    except (
        AttributeError,
        ImportError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        raise V075ManifestV2InvariantViolation(
            "serialized pretarget artifact semantic replay failed"
        ) from error
    artifact_replay_payload = {
        "schema": "acfqp.v075_manifest_semantic_artifact_replay.v2",
        "schema_version": SCHEMA_VERSION,
        "dependency_lock_id": dependency_lock_id,
        "dependency_lock_verification_id": dependency_verification_id,
        "dependency_lock_canonical_sha256": (
            dependency_canonical_sha256
        ),
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
    artifact_replay_id = _hash(
        "semantic_artifact_replay",
        artifact_replay_payload,
    )
    artifact_replay_document = {
        **artifact_replay_payload,
        "artifact_semantic_replay_id": artifact_replay_id,
    }
    _verify_executed_module_component_closure(
        roots=(
            importlib.import_module(__name__),
            registry_module,
            legacy_independent,
            tracked_source,
        ),
        components=components,
    )
    return V075ManifestSemanticRegistryBindingV2(
        _SEMANTIC_ISSUER,
        registry_id,
        verification_id,
        tuple(bindings),
        registry_document,
        verification_document,
        artifact_replay_document,
        artifact_replay_id,
    )


_MANIFEST_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConfirmatoryExecutionManifestV2:
    _issuer: object = field(repr=False, compare=False)
    components: tuple[V075ManifestComponentBlobV2, ...]
    semantic_registry: V075ManifestSemanticRegistryBindingV2
    workload: V075ConfirmatoryPublicWorkloadV2
    signer_registry: public.V075TrustedSignerRegistryV1
    opaque_environment_commitment: (
        public.V075OpaqueEnvironmentCommitmentV1
    )
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        exact_family = public.freeze_v075_public_family_generation_v1()
        if (
            self._issuer is not _MANIFEST_ISSUER
            or type(self.components) is not tuple
            or tuple(type(item) for item in self.components)
            != (V075ManifestComponentBlobV2,)
            * len(REQUIRED_COMPONENT_SPECS)
            or tuple(
                (item.role, item.repository_path) for item in self.components
            )
            != REQUIRED_COMPONENT_SPECS
            or type(self.semantic_registry)
            is not V075ManifestSemanticRegistryBindingV2
            or type(self.workload) is not V075ConfirmatoryPublicWorkloadV2
            or type(self.signer_registry)
            is not public.V075TrustedSignerRegistryV1
            or type(self.opaque_environment_commitment)
            is not public.V075OpaqueEnvironmentCommitmentV1
            or self.opaque_environment_commitment.family != exact_family
            or self.workload.family != exact_family
        ):
            _fail("execution manifest is incomplete or factory-bypassed")
        identity_roles = (
            tuple(item.component_id for item in self.components)
            + (
                self.semantic_registry.binding_id,
                self.semantic_registry.authority_registry_id,
                self.semantic_registry.authority_registry_verification_id,
                self.semantic_registry.artifact_semantic_replay_id,
                self.workload.workload_id,
                self.workload.runner_profile.profile_id,
                self.signer_registry.registry_id,
                self.opaque_environment_commitment.commitment_id,
            )
        )
        if len(identity_roles) != len(set(identity_roles)):
            _fail("manifest aliases incompatible identity roles")
        object.__setattr__(
            self,
            "_manifest_id",
            _hash("manifest", self._payload()),
        )
        raw = canonical_json_bytes(self.to_document())
        if b'"final_preregistration_id"' in raw:
            _fail("manifest contains a forbidden downstream authority field")

    def _payload(self) -> dict[str, Any]:
        component_documents = [
            item.to_document() for item in self.components
        ]
        return {
            "schema": "acfqp.v075_confirmatory_execution_manifest.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "repository_url": REPOSITORY_URL,
            "target_branch": TARGET_BRANCH,
            "component_blobs": component_documents,
            "component_registry_id": _hash(
                "component_registry",
                {"component_blobs": component_documents},
            ),
            "semantic_registry_binding": (
                self.semantic_registry.to_document()
            ),
            "semantic_registry_binding_id": (
                self.semantic_registry.binding_id
            ),
            "semantic_artifact_replay_id": (
                self.semantic_registry.artifact_semantic_replay_id
            ),
            "workload": self.workload.to_document(),
            "workload_id": self.workload.workload_id,
            "runner_profile_id": self.workload.runner_profile.profile_id,
            "family_generation_id": self.workload.family.generation_id,
            "context_ids": [
                item.context_id
                for item in self.workload.family.replicate_contexts
            ],
            "signer_registry_id": self.signer_registry.registry_id,
            "opaque_environment_commitment": (
                self.opaque_environment_commitment.to_document()
            ),
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment.commitment_id
            ),
            "exact_test_command": list(EXACT_TEST_COMMAND),
            "deterministic_environment": [
                {"name": name, "value": value}
                for name, value in DETERMINISTIC_ENVIRONMENT
            ],
            "binding_order": (
                "COMPONENTS_THEN_SEMANTICS_THEN_WORKLOAD_THEN_MANIFEST"
            ),
            "next_authority": "SIGNED_FINAL_THEN_REMOTE_MAIN_ANCHOR",
            "target_law_serialized": False,
            "target_tape_serialized": False,
            "private_key_serialized": False,
            "observer_opened": False,
            "target_accessed": False,
            "target_execution_allowed": False,
        }

    @property
    def manifest_id(self) -> str:
        return self._manifest_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


def freeze_v075_confirmatory_execution_manifest_v2(
    *,
    repository_root: str | os.PathLike[str],
    signer_registry: public.V075TrustedSignerRegistryV1,
    opaque_environment_commitment: (
        public.V075OpaqueEnvironmentCommitmentV1
    ),
) -> V075ConfirmatoryExecutionManifestV2:
    """Freeze one complete manifest from indexed public inputs only."""

    components = tuple(
        collect_v075_manifest_component_blob_v2(
            repository_root,
            role=role,
        )
        for role, _path in REQUIRED_COMPONENT_SPECS
    )
    root = Path(repository_root).resolve(strict=True)
    semantic_registry = bind_v075_semantic_registry_v2(
        components=components,
        package_root=root / "src" / "acfqp",
    )
    return V075ConfirmatoryExecutionManifestV2(
        _MANIFEST_ISSUER,
        components,
        semantic_registry,
        freeze_v075_confirmatory_public_workload_v2(),
        signer_registry,
        opaque_environment_commitment,
    )


def _final_unsigned_payload(
    manifest: V075ConfirmatoryExecutionManifestV2,
) -> dict[str, Any]:
    if type(manifest) is not V075ConfirmatoryExecutionManifestV2:
        _fail("final preregistration requires the exact typed manifest")
    registry = manifest.signer_registry
    workload = manifest.workload
    return {
        "schema": "acfqp.v075_final_preregistration.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "repository_url": REPOSITORY_URL,
        "target_branch": TARGET_BRANCH,
        "confirmatory_execution_manifest_id": manifest.manifest_id,
        "confirmatory_execution_manifest_bytes_sha256": (
            hashlib.sha256(manifest.canonical_bytes).hexdigest()
        ),
        "component_registry_id": manifest.to_document()[
            "component_registry_id"
        ],
        "semantic_registry_binding_id": (
            manifest.semantic_registry.binding_id
        ),
        "semantic_authority_registry_id": (
            manifest.semantic_registry.authority_registry_id
        ),
        "semantic_authority_registry_verification_id": (
            manifest.semantic_registry.authority_registry_verification_id
        ),
        "semantic_artifact_replay_id": (
            manifest.semantic_registry.artifact_semantic_replay_id
        ),
        "workload_id": workload.workload_id,
        "runner_profile_id": workload.runner_profile.profile_id,
        "family_generation_id": workload.family.generation_id,
        "context_ids": [
            item.context_id for item in workload.family.replicate_contexts
        ],
        "arm_order": list(public.ARM_ORDER),
        "logical_occurrence_denominator": 15,
        "threshold_profile_id": (
            workload.threshold_profile.threshold_profile_id
        ),
        "cap_profile_id": workload.cap_profile.cap_profile_id,
        "private_environment_generation_profile_id": (
            workload.generation_profile.profile_id
        ),
        "opaque_environment_commitment_id": (
            manifest.opaque_environment_commitment.commitment_id
        ),
        "signer_registry_id": registry.registry_id,
        "signer_registry": registry.to_document(),
        "campaign_authority_public_key_bytes": canonical_json_bytes(
            registry.campaign_authority_key.to_document()
        ).hex(),
        "observer_evidence_public_key_bytes": canonical_json_bytes(
            registry.observer_evidence_key.to_document()
        ).hex(),
        "campaign_authority_key_id": (
            registry.campaign_authority_key.key_id
        ),
        "observer_evidence_key_id": registry.observer_evidence_key.key_id,
        "exact_test_command": list(EXACT_TEST_COMMAND),
        "manifest_precedes_signed_final": True,
        "remote_main_anchor_id": None,
        "preopen_v2_migration_status": "NOT_READY",
        "observer_open_allowed": False,
        "registered_target_execution_allowed": False,
        "official_execution_allowed": False,
        "target_accessed": False,
    }


def final_preregistration_signing_bytes_v2(
    manifest: V075ConfirmatoryExecutionManifestV2,
) -> bytes:
    return (
        FINAL_SIGNING_DOMAIN
        + b"\x00"
        + canonical_json_bytes(_final_unsigned_payload(manifest))
    )


@dataclass(frozen=True, slots=True)
class V075FinalPreregistrationV2:
    _issuer: object = field(repr=False, compare=False)
    manifest: V075ConfirmatoryExecutionManifestV2
    campaign_authority_signature_hex: str
    _final_preregistration_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _MANIFEST_ISSUER
            or type(self.manifest)
            is not V075ConfirmatoryExecutionManifestV2
            or type(self.campaign_authority_signature_hex) is not str
            or not self.campaign_authority_signature_hex
            or not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
                public_key=(
                    self.manifest.signer_registry.campaign_authority_key
                ),
                message=final_preregistration_signing_bytes_v2(
                    self.manifest
                ),
                signature_hex=self.campaign_authority_signature_hex,
            )
        ):
            _fail("final preregistration campaign signature is invalid")
        object.__setattr__(
            self,
            "_final_preregistration_id",
            _hash("final_preregistration", self._payload()),
        )
        if (
            self.final_preregistration_id.encode("ascii")
            in self.manifest.canonical_bytes
            or b'"final_preregistration_id"'
            in self.manifest.canonical_bytes
        ):
            _fail("manifest-to-final identity direction is circular")

    def _payload(self) -> dict[str, Any]:
        return {
            **_final_unsigned_payload(self.manifest),
            "campaign_authority_signature_hex": (
                self.campaign_authority_signature_hex
            ),
            "campaign_authority_signature_verified": True,
        }

    @property
    def final_preregistration_id(self) -> str:
        return self._final_preregistration_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "final_preregistration_id": self.final_preregistration_id,
        }


def finalize_v075_preregistration_v2(
    *,
    manifest: V075ConfirmatoryExecutionManifestV2,
    campaign_authority_signature_hex: str,
) -> V075FinalPreregistrationV2:
    return V075FinalPreregistrationV2(
        _MANIFEST_ISSUER,
        manifest,
        campaign_authority_signature_hex,
    )


@runtime_checkable
class V075CampaignAuthorityFinalSignerProtocolV2(Protocol):
    def public_verification_key_v1(
        self,
    ) -> public.V075RSAPublicVerificationKeyV1: ...

    def sign_final_preregistration_v2(self, message: bytes) -> str: ...


def finalize_v075_preregistration_with_signer_v2(
    *,
    manifest: V075ConfirmatoryExecutionManifestV2,
    private_signer: V075CampaignAuthorityFinalSignerProtocolV2,
) -> V075FinalPreregistrationV2:
    """Sign in memory with the registry-bound production campaign signer."""

    if (
        type(manifest) is not V075ConfirmatoryExecutionManifestV2
        or not isinstance(
            private_signer,
            V075CampaignAuthorityFinalSignerProtocolV2,
        )
        or private_signer.public_verification_key_v1()
        != manifest.signer_registry.campaign_authority_key
    ):
        _fail("private finalizer signer is foreign or not registry-bound")
    message = final_preregistration_signing_bytes_v2(manifest)
    signature = private_signer.sign_final_preregistration_v2(message)
    if (
        private_signer.public_verification_key_v1()
        != manifest.signer_registry.campaign_authority_key
        or not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=manifest.signer_registry.campaign_authority_key,
            message=message,
            signature_hex=signature,
        )
    ):
        _fail("private finalizer signer returned an invalid signature")
    return finalize_v075_preregistration_v2(
        manifest=manifest,
        campaign_authority_signature_hex=signature,
    )


def finalize_v075_preregistration_with_private_signer_v2(
    *,
    manifest: V075ConfirmatoryExecutionManifestV2,
    private_signer: V075CampaignAuthorityFinalSignerProtocolV2,
) -> V075FinalPreregistrationV2:
    """Compatibility spelling for the strict protocol-driven finalizer."""

    return finalize_v075_preregistration_with_signer_v2(
        manifest=manifest,
        private_signer=private_signer,
    )


@dataclass(frozen=True, slots=True)
class V075ManifestReadinessV2:
    manifest_blockers: tuple[str, ...]
    production_open_blockers: tuple[str, ...]
    concrete_component_ids: tuple[str, ...]
    manifest_prerequisites_ready: bool
    production_open_ready: bool

    def __post_init__(self) -> None:
        if (
            type(self.manifest_blockers) is not tuple
            or self.manifest_blockers
            != tuple(sorted(set(self.manifest_blockers)))
            or type(self.production_open_blockers) is not tuple
            or self.production_open_blockers
            != tuple(sorted(set(self.production_open_blockers)))
            or self.manifest_prerequisites_ready
            is not (not self.manifest_blockers)
            or self.production_open_ready
            is not (
                not self.manifest_blockers
                and not self.production_open_blockers
            )
        ):
            _fail("V2 manifest readiness is inconsistent")
        for item in self.concrete_component_ids:
            _cid(item, "readiness component")

    def to_document(self) -> dict[str, Any]:
        payload = {
            "schema": "acfqp.v075_confirmatory_readiness.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "manifest_blockers": list(self.manifest_blockers),
            "production_open_blockers": list(
                self.production_open_blockers
            ),
            "concrete_component_ids": list(self.concrete_component_ids),
            "manifest_prerequisites_ready": (
                self.manifest_prerequisites_ready
            ),
            "production_open_ready": self.production_open_ready,
            "registered_observer_calls": 0,
            "target_accessed": False,
            "target_execution_allowed": False,
        }
        return {**payload, "readiness_id": _hash("readiness", payload)}


def current_v075_pretarget_readiness_v2(
    repository_root: str | os.PathLike[str],
) -> V075ManifestReadinessV2:
    components: list[V075ManifestComponentBlobV2] = []
    blockers: list[str] = []
    for role, _path in REQUIRED_COMPONENT_SPECS:
        try:
            components.append(
                collect_v075_manifest_component_blob_v2(
                    repository_root,
                    role=role,
                )
            )
        except (
            OSError,
            subprocess.SubprocessError,
            V075ManifestV2InvariantViolation,
        ):
            blockers.append(f"COMPONENT_NOT_CONCRETE:{role}")
    try:
        if len(components) == len(REQUIRED_COMPONENT_SPECS):
            bind_v075_semantic_registry_v2(
                components=tuple(components),
                package_root=(
                    Path(repository_root).resolve(strict=True)
                    / "src"
                    / "acfqp"
                ),
            )
    except V075ManifestV2InvariantViolation:
        blockers.append("SEMANTIC_REGISTRY_V2_NOT_CONCRETE")
    blockers.extend(
        (
            "OPAQUE_ENVIRONMENT_COMMITMENT_NOT_SUPPLIED",
            "PUBLIC_SIGNER_REGISTRY_NOT_SUPPLIED",
        )
    )
    return V075ManifestReadinessV2(
        tuple(sorted(set(blockers))),
        ("PREOPEN_V2_MIGRATION_NOT_READY",),
        tuple(item.component_id for item in components),
        not blockers,
        False,
    )


__all__ = [
    "DEPENDENCY_LOCK_REPOSITORY_PATH",
    "DETERMINISTIC_ENVIRONMENT",
    "DOMAIN_TAGS",
    "EXACT_TEST_COMMAND",
    "FINAL_PREREGISTRATION_REPOSITORY_PATH",
    "FINAL_SIGNING_DOMAIN",
    "MANIFEST_REPOSITORY_PATH",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REPOSITORY_URL",
    "REQUIRED_COMPONENT_SPECS",
    "SCHEMA_VERSION",
    "TARGET_BRANCH",
    "V075ConfirmatoryExecutionManifestV2",
    "V075ConfirmatoryPublicWorkloadV2",
    "V075CampaignAuthorityFinalSignerProtocolV2",
    "V075FinalPreregistrationV2",
    "V075ManifestComponentBlobV2",
    "V075ManifestReadinessV2",
    "V075ManifestSemanticBindingV2",
    "V075ManifestSemanticRegistryBindingV2",
    "V075ManifestV2InvariantViolation",
    "V075ManifestV2NotReady",
    "bind_v075_semantic_registry_v2",
    "collect_v075_manifest_component_blob_v2",
    "current_v075_pretarget_readiness_v2",
    "final_preregistration_signing_bytes_v2",
    "finalize_v075_preregistration_v2",
    "finalize_v075_preregistration_with_private_signer_v2",
    "finalize_v075_preregistration_with_signer_v2",
    "freeze_v075_confirmatory_execution_manifest_v2",
    "freeze_v075_confirmatory_public_workload_v2",
]
